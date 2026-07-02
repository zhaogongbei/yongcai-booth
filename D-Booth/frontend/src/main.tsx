import { createRoot } from "react-dom/client";
import App from "./app/App.tsx";
import "./styles/index.css";

// Register Service Worker for offline support
if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js')
      .then((registration) => {
        console.log('ServiceWorker registration successful with scope: ', registration.scope);

        // Listen for background sync events
        registration.addEventListener('sync', (event: Event) => {
          const syncEvent = event as Event & { tag?: string };
          if (syncEvent.tag === 'sync-offline-photos') {
            console.log('Syncing offline photos...');
          }
        });
      })
      .catch((err) => {
        console.log('ServiceWorker registration failed: ', err);
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
  
