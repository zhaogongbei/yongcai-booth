import { useEffect, useRef, useState, useCallback } from 'react';

/**
 * WebSocket connection state
 */
export type WebSocketState = 'connecting' | 'connected' | 'disconnecting' | 'disconnected' | 'error';

/**
 * WebSocket message
 */
export interface WebSocketMessage<T = any> {
  type?: string;
  data: T;
  timestamp?: number;
}

/**
 * WebSocket options
 */
export interface UseWebSocketOptions<T = any> {
  /** Whether to connect immediately on mount (default: true) */
  autoConnect?: boolean;
  /** Whether to automatically reconnect on disconnect (default: true) */
  autoReconnect?: boolean;
  /** Maximum number of reconnection attempts (default: 5, 0 = infinite) */
  maxReconnectAttempts?: number;
  /** Delay between reconnection attempts in milliseconds (default: 3000) */
  reconnectDelay?: number;
  /** Exponential backoff multiplier (default: 1.5) */
  reconnectBackoff?: number;
  /** Maximum reconnection delay in milliseconds (default: 30000) */
  maxReconnectDelay?: number;
  /** WebSocket protocols */
  protocols?: string | string[];
  /** Callback when connection opens */
  onOpen?: (event: Event) => void;
  /** Callback when connection closes */
  onClose?: (event: CloseEvent) => void;
  /** Callback when message is received */
  onMessage?: (message: T) => void;
  /** Callback when error occurs */
  onError?: (event: Event) => void;
  /** Message parser (default: JSON.parse) */
  parseMessage?: (data: string) => T;
  /** Message serializer (default: JSON.stringify) */
  serializeMessage?: (data: T) => string;
  /** Heartbeat interval in milliseconds (0 = disabled, default: 30000) */
  heartbeatInterval?: number;
  /** Heartbeat message to send */
  heartbeatMessage?: string | (() => string);
}

/**
 * WebSocket hook return value
 */
export interface UseWebSocketReturn<T = any> {
  /** Current WebSocket connection state */
  state: WebSocketState;
  /** Last received message */
  lastMessage: T | null;
  /** Message history */
  messages: T[];
  /** Send a message */
  send: (data: T | string) => void;
  /** Connect to WebSocket */
  connect: () => void;
  /** Disconnect from WebSocket */
  disconnect: () => void;
  /** Reconnect to WebSocket */
  reconnect: () => void;
  /** Clear message history */
  clearMessages: () => void;
  /** Number of reconnection attempts made */
  reconnectAttempts: number;
}

/**
 * WebSocket connection management hook
 *
 * Provides a robust WebSocket connection with automatic reconnection,
 * heartbeat, message history, and comprehensive state management.
 *
 * @param url - WebSocket URL (ws:// or wss://)
 * @param options - Configuration options
 * @returns WebSocket state and control methods
 *
 * @example
 * ```tsx
 * // Basic usage
 * function ChatRoom() {
 *   const ws = useWebSocket<ChatMessage>('ws://localhost:8080/chat', {
 *     onMessage: (message) => {
 *       console.log('Received:', message);
 *     },
 *   });
 *
 *   const sendMessage = () => {
 *     ws.send({ type: 'chat', text: 'Hello!' });
 *   };
 *
 *   return (
 *     <div>
 *       <div>Status: {ws.state}</div>
 *       <button onClick={sendMessage} disabled={ws.state !== 'connected'}>
 *         Send Message
 *       </button>
 *       <div>
 *         {ws.messages.map((msg, i) => (
 *           <div key={i}>{msg.text}</div>
 *         ))}
 *       </div>
 *     </div>
 *   );
 * }
 *
 * // With authentication token
 * function SecureChat() {
 *   const token = useAuthToken();
 *   const ws = useWebSocket(`wss://api.example.com/ws?token=${token}`, {
 *     autoReconnect: true,
 *     maxReconnectAttempts: 10,
 *     heartbeatInterval: 30000,
 *     heartbeatMessage: () => JSON.stringify({ type: 'ping' }),
 *   });
 *
 *   return <div>Connected: {ws.state === 'connected'}</div>;
 * }
 *
 * // Manual connection control
 * function ControlledWebSocket() {
 *   const ws = useWebSocket('ws://localhost:8080', {
 *     autoConnect: false,
 *   });
 *
 *   return (
 *     <div>
 *       <button onClick={ws.connect}>Connect</button>
 *       <button onClick={ws.disconnect}>Disconnect</button>
 *       <button onClick={ws.reconnect}>Reconnect</button>
 *     </div>
 *   );
 * }
 * ```
 */
export function useWebSocket<T = any>(
  url: string,
  options: UseWebSocketOptions<T> = {}
): UseWebSocketReturn<T> {
  const {
    autoConnect = true,
    autoReconnect = true,
    maxReconnectAttempts = 5,
    reconnectDelay = 3000,
    reconnectBackoff = 1.5,
    maxReconnectDelay = 30000,
    protocols,
    onOpen,
    onClose,
    onMessage,
    onError,
    parseMessage = JSON.parse,
    serializeMessage = JSON.stringify,
    heartbeatInterval = 30000,
    heartbeatMessage = '{"type":"ping"}',
  } = options;

  const [state, setState] = useState<WebSocketState>('disconnected');
  const [lastMessage, setLastMessage] = useState<T | null>(null);
  const [messages, setMessages] = useState<T[]>([]);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatTimerRef = useRef<NodeJS.Timeout | null>(null);
  const mountedRef = useRef(true);
  const urlRef = useRef(url);

  // Update URL ref when it changes
  useEffect(() => {
    urlRef.current = url;
  }, [url]);

  // Cleanup on unmount
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (heartbeatTimerRef.current) {
        clearTimeout(heartbeatTimerRef.current);
      }
    };
  }, []);

  /**
   * Start heartbeat mechanism
   */
  const startHeartbeat = useCallback(() => {
    if (heartbeatInterval <= 0) return;

    if (heartbeatTimerRef.current) {
      clearTimeout(heartbeatTimerRef.current);
    }

    heartbeatTimerRef.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        const message =
          typeof heartbeatMessage === 'function' ? heartbeatMessage() : heartbeatMessage;
        wsRef.current.send(message);
      }
    }, heartbeatInterval);
  }, [heartbeatInterval, heartbeatMessage]);

  /**
   * Stop heartbeat mechanism
   */
  const stopHeartbeat = useCallback(() => {
    if (heartbeatTimerRef.current) {
      clearInterval(heartbeatTimerRef.current);
      heartbeatTimerRef.current = null;
    }
  }, []);

  /**
   * Connect to WebSocket
   */
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    if (mountedRef.current) {
      setState('connecting');
    }

    try {
      const ws = new WebSocket(urlRef.current, protocols);

      ws.onopen = (event) => {
        if (mountedRef.current) {
          setState('connected');
          setReconnectAttempts(0);
        }

        startHeartbeat();
        onOpen?.(event);
      };

      ws.onclose = (event) => {
        if (mountedRef.current) {
          setState('disconnected');
        }

        stopHeartbeat();
        onClose?.(event);

        // Auto-reconnect if enabled and not a clean close
        if (autoReconnect && !event.wasClean && mountedRef.current) {
          if (maxReconnectAttempts === 0 || reconnectAttempts < maxReconnectAttempts) {
            const delay = Math.min(
              reconnectDelay * Math.pow(reconnectBackoff, reconnectAttempts),
              maxReconnectDelay
            );

            reconnectTimerRef.current = setTimeout(() => {
              setReconnectAttempts((prev) => prev + 1);
              connect();
            }, delay);
          } else {
            if (mountedRef.current) {
              setState('error');
            }
          }
        }
      };

      ws.onmessage = (event) => {
        try {
          const parsed =
            typeof event.data === 'string' ? parseMessage(event.data) : event.data;

          if (mountedRef.current) {
            setLastMessage(parsed);
            setMessages((prev) => [...prev, parsed]);
          }

          onMessage?.(parsed);
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      ws.onerror = (event) => {
        if (mountedRef.current) {
          setState('error');
        }
        onError?.(event);
      };

      wsRef.current = ws;
    } catch (err) {
      console.error('Failed to create WebSocket:', err);
      if (mountedRef.current) {
        setState('error');
      }
    }
  }, [
    protocols,
    autoReconnect,
    maxReconnectAttempts,
    reconnectAttempts,
    reconnectDelay,
    reconnectBackoff,
    maxReconnectDelay,
    parseMessage,
    onOpen,
    onClose,
    onMessage,
    onError,
    startHeartbeat,
    stopHeartbeat,
  ]);

  /**
   * Disconnect from WebSocket
   */
  const disconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }

    stopHeartbeat();

    if (wsRef.current) {
      if (mountedRef.current) {
        setState('disconnecting');
      }

      wsRef.current.close(1000, 'Client disconnect');
      wsRef.current = null;

      if (mountedRef.current) {
        setState('disconnected');
      }
    }
  }, [stopHeartbeat]);

  /**
   * Reconnect to WebSocket
   */
  const reconnect = useCallback(() => {
    disconnect();
    setReconnectAttempts(0);
    setTimeout(() => {
      connect();
    }, 100);
  }, [disconnect, connect]);

  /**
   * Send a message
   */
  const send = useCallback(
    (data: T | string) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        const message = typeof data === 'string' ? data : serializeMessage(data);
        wsRef.current.send(message);
      } else {
        console.warn('WebSocket is not connected. Message not sent:', data);
      }
    },
    [serializeMessage]
  );

  /**
   * Clear message history
   */
  const clearMessages = useCallback(() => {
    setMessages([]);
    setLastMessage(null);
  }, []);

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect]); // Only run on mount/unmount

  return {
    state,
    lastMessage,
    messages,
    send,
    connect,
    disconnect,
    reconnect,
    clearMessages,
    reconnectAttempts,
  };
}
