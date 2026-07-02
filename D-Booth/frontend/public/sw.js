const CACHE_VERSION = 'v1';
const CACHE_PREFIX = 'd-booth-';
const CACHE_NAME = `${CACHE_PREFIX}${CACHE_VERSION}`;

// Precache core assets
const PRECACHE_URLS = [
  '/',
  '/index.html',
  '/favicon.ico',
  '/manifest.json',
];

// Cache strategies
const CACHE_STRATEGIES = {
  STATIC_ASSETS: /^.*\.(js|css|png|jpg|jpeg|gif|webp|svg|ico|woff|woff2|ttf|eot)$/i,
  API_ENDPOINTS: /^\/api\//i,
  PHOTO_THUMBNAILS: /^.*\/thumbnails\//i,
};

// Install event: Precache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  );
});

// Activate event: Clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name.startsWith(CACHE_PREFIX) && name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch event: Apply different caching strategies
self.addEventListener('fetch', (event) => {
  const request = event.request;

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Skip cross-origin requests for now
  if (!request.url.startsWith(self.location.origin)) {
    return;
  }

  // Strategy 1: Cache First for static assets
  if (CACHE_STRATEGIES.STATIC_ASSETS.test(request.url)) {
    event.respondWith(cacheFirst(request));
    return;
  }

  // Strategy 2: Stale While Revalidate for photo thumbnails
  if (CACHE_STRATEGIES.PHOTO_THUMBNAILS.test(request.url)) {
    event.respondWith(staleWhileRevalidate(request));
    return;
  }

  // Strategy 3: Network First for API endpoints
  if (CACHE_STRATEGIES.API_ENDPOINTS.test(request.url)) {
    event.respondWith(networkFirst(request));
    return;
  }

  // Default: Network first for navigation requests
  if (request.mode === 'navigate') {
    event.respondWith(networkFirst(request));
  }
});

/**
 * Cache First strategy: Return from cache immediately, fetch and update cache in background
 */
async function cacheFirst(request) {
  const cache = await caches.open(CACHE_NAME);
  const cachedResponse = await cache.match(request);

  if (cachedResponse) {
    // Update cache in background
    fetch(request).then((networkResponse) => {
      cache.put(request, networkResponse.clone());
    });
    return cachedResponse;
  }

  // Fallback to network if not in cache
  try {
    const networkResponse = await fetch(request);
    cache.put(request, networkResponse.clone());
    return networkResponse;
  } catch (error) {
    return getOfflineFallback(request);
  }
}

/**
 * Network First strategy: Try network first, fall back to cache if offline
 */
async function networkFirst(request) {
  const cache = await caches.open(CACHE_NAME);

  try {
    const networkResponse = await fetch(request);
    cache.put(request, networkResponse.clone());
    return networkResponse;
  } catch (error) {
    const cachedResponse = await cache.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    return getOfflineFallback(request);
  }
}

/**
 * Stale While Revalidate strategy: Return cached data immediately, then update cache with network response
 */
async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE_NAME);
  const cachedResponse = await cache.match(request);

  // Fetch latest version in background
  const fetchPromise = fetch(request).then((networkResponse) => {
    cache.put(request, networkResponse.clone());
    return networkResponse;
  });

  // Return cached response immediately if available, otherwise wait for network
  return cachedResponse || fetchPromise;
}

/**
 * Get appropriate offline fallback response
 */
async function getOfflineFallback(request) {
  const cache = await caches.open(CACHE_NAME);

  // For navigation requests, return offline page
  if (request.mode === 'navigate') {
    const offlineResponse = await cache.match('/offline.html');
    if (offlineResponse) {
      return offlineResponse;
    }
    return new Response(`
      <!DOCTYPE html>
      <html lang="zh-CN">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>离线模式</title>
        <style>
          * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
          }
          body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
          }
          .container {
            text-align: center;
            padding: 2rem;
            max-width: 400px;
          }
          h1 {
            font-size: 3rem;
            margin-bottom: 1rem;
          }
          p {
            font-size: 1.2rem;
            margin-bottom: 2rem;
            opacity: 0.9;
          }
          .hint {
            font-size: 0.9rem;
            opacity: 0.7;
          }
        </style>
      </head>
      <body>
        <div class="container">
          <h1>📸</h1>
          <h2>当前处于离线模式</h2>
          <p>您仍然可以继续拍照，照片会在恢复网络后自动上传</p>
          <div class="hint">提示: 连接网络后数据会自动同步</div>
        </div>
      </body>
      </html>
    `, {
      status: 200,
      headers: {
        'Content-Type': 'text/html; charset=utf-8',
      },
    });
  }

  // For images, return empty placeholder
  if (request.destination === 'image') {
    return new Response('', { status: 204 });
  }

  return new Response(JSON.stringify({ error: 'Offline mode' }), {
    status: 503,
    headers: { 'Content-Type': 'application/json' },
  });
}

// Background Sync: Sync offline photos when back online
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-offline-photos') {
    event.waitUntil(syncOfflinePhotos());
  }
});

async function syncOfflinePhotos() {
  const clients = await self.clients.matchAll();
  clients.forEach((client) => {
    client.postMessage({ type: 'SYNC_OFFLINE_PHOTOS' });
  });
}
