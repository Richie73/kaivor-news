const CACHE = 'kaivor-news-fp093-offline-v1';
const SHELL = [
  '/manifest.webmanifest',
  '/icons/kaivor-news-192-v4.png',
  '/icons/kaivor-news-512-v4.png'
];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE).map(key => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});
self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith('/api/')) return;
  if (request.mode === 'navigate') {
    // FP093: network-first, but keep the last good page. The old
    // fallback (caches.match('/')) could never hit — nothing ever
    // put '/' in the cache — so offline the app showed the
    // browser's error page. Now a successful navigation is stored
    // under its own URL, and an offline open serves the exact page
    // asked for, or the homepage when that page was never cached.
    event.respondWith(
      fetch(request).then(response => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(CACHE).then(cache => cache.put(request, copy));
        }
        return response;
      }).catch(() => caches.match(request).then(cached => cached || caches.match('/')))
    );
    return;
  }
  event.respondWith(fetch(request).catch(() => caches.match(request)));
});
