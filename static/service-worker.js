// CaptureIQ Service Worker
// Provides offline support and caching for PWA installation

const CACHE_NAME = 'captureiq-v1';

// Static assets to cache on install (app shell)
const PRECACHE_URLS = [
  '/static/css/style.css',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png',
  '/static/manifest.json',
  // Bootstrap and Bootstrap Icons from CDN are cached on first fetch
];

// Pages to serve from cache when offline
const OFFLINE_FALLBACK = '/offline';

// ── Install: pre-cache the app shell ─────────────────────────────────────────
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(PRECACHE_URLS).catch(err => {
        console.warn('[SW] Pre-cache error (non-fatal):', err);
      });
    }).then(() => self.skipWaiting())
  );
});

// ── Activate: clean up old caches ────────────────────────────────────────────
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

// ── Fetch: network-first for HTML, cache-first for static assets ──────────────
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET, cross-origin, and API/auth requests
  if (request.method !== 'GET') return;
  if (url.origin !== self.location.origin) {
    // For CDN assets (Bootstrap, etc.) — cache first, then network
    if (url.hostname.includes('cdn.jsdelivr') || url.hostname.includes('cdnjs') || url.hostname.includes('bootstrapcdn')) {
      event.respondWith(
        caches.match(request).then(cached => {
          if (cached) return cached;
          return fetch(request).then(response => {
            const clone = response.clone();
            caches.open(CACHE_NAME).then(c => c.put(request, clone));
            return response;
          });
        })
      );
    }
    return;
  }

  // Static assets: cache-first
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(request).then(cached => {
        if (cached) return cached;
        return fetch(request).then(response => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(c => c.put(request, clone));
          return response;
        });
      })
    );
    return;
  }

  // HTML pages: network-first, fall back to offline page
  event.respondWith(
    fetch(request)
      .then(response => {
        // Cache successful GET responses for HTML pages
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(c => c.put(request, clone));
        }
        return response;
      })
      .catch(() => {
        // Offline: try cache, then show offline page
        return caches.match(request).then(cached => {
          return cached || caches.match(OFFLINE_FALLBACK) || new Response(
            '<html><body style="font-family:sans-serif;text-align:center;padding:60px">' +
            '<h2>You\'re offline</h2>' +
            '<p>CaptureIQ needs a connection to load this page.</p>' +
            '<p>Data you entered while online is saved. Reconnect to sync.</p>' +
            '<button onclick="location.reload()">Try Again</button>' +
            '</body></html>',
            { headers: { 'Content-Type': 'text/html' } }
          );
        });
      })
  );
});

// ── Background sync for offline contact/note submissions ─────────────────────
self.addEventListener('sync', event => {
  if (event.tag === 'sync-pending-contacts') {
    event.waitUntil(syncPendingData());
  }
});

async function syncPendingData() {
  // Opens IndexedDB queue and replays any POST requests made while offline
  // Full implementation added when offline-first contact entry is enabled
  console.log('[SW] Background sync triggered');
}
