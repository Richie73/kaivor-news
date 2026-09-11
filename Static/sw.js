self.addEventListener('install', (e) => {
    e.waitUntil(
        caches.open('kaivor-news-v1').then((cache) => {
            return cache.addAll([
                '/',
                '/manifest.json'
            ]);
        })
    );
});

self.addEventListener('fetch', (e) => {
    e.respondWith(
        caches.match(e.request).then((cachedResponse) => {
            return cachedResponse || fetch(e.request);
        })
    );
});
