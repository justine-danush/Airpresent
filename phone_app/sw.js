self.addEventListener('install', event => { self.skipWaiting(); event.waitUntil(caches.open('airpresent-v4').then(cache => cache.addAll(['/', '/index.html', '/style.css', '/app.js', '/manifest.json']))); });
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
self.addEventListener('fetch', event => event.respondWith(caches.match(event.request).then(cached => cached || fetch(event.request))));
