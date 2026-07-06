import { createRoot } from "react-dom/client";
import App from "./app/App.tsx";
import "./styles/index.css";

// Register Service Worker for offline support
if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {
      // Offline support is optional; the app remains usable without registration.
    });
  });

  // Listen for online/offline events
  window.addEventListener('online', () => {
    console.log('Network connection restored');
    // Notify application to sync offline data
    const event = new CustomEvent('network-restored');
    window.dispatchEvent(event);
  });

  window.addEventListener('offline', () => {
    console.log('Network connection lost');
    const event = new CustomEvent('network-lost');
    window.dispatchEvent(event);
  });
}

createRoot(document.getElementById("root")!).render(<App />);
  
