/**
 * Auth Store —— 鉴权状态与登录/登出/当前用户
 *
 * 仅提供骨架：token 持久化于 localStorage（由 lib/api.ts 的 tokenStorage 管理），
 * useAuth 负责 user 状态、登录动作、401 自动登出监听。
 *
 * 真实接入后端后，screens 通过 useAuth() 获取 user、判断登录态。
 */
import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from "react";
import { request, tokenStorage, loginForm, ApiError } from "../lib/api";

export interface AuthUser {
  id: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  is_verified: boolean;
  is_superuser: boolean;
  team_role?: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, full_name?: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    if (!tokenStorage.access) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const u = await request<AuthUser>("/auth/me", { noAuth: false });
      setUser(u);
    } catch {
      tokenStorage.clear();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
    const onUnauthorized = () => {
      setUser(null);
    };
    window.addEventListener("aibooth:unauthorized", onUnauthorized as EventListener);
    return () => window.removeEventListener("aibooth:unauthorized", onUnauthorized as EventListener);
  }, [refreshUser]);

  const login = useCallback(async (email: string, password: string) => {
    const tokens = await loginForm(email, password);
    tokenStorage.set(tokens.access_token, tokens.refresh_token);
    await refreshUser();
  }, [refreshUser]);

  const register = useCallback(async (email: string, password: string, full_name?: string) => {
    await request("/auth/register", {
      method: "POST",
      noAuth: true,
      body: { email, password, full_name },
    });
    await login(email, password);
  }, [login]);

  const logout = useCallback(() => {
    tokenStorage.clear();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export { ApiError };
