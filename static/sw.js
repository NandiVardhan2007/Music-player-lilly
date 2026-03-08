/* Lily Music — Service Worker v2 */
const CACHE = 'lily-v2';
const SHELL = ['/', '/static/index.html', '/static/manifest.json'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  // Network-first for API (streams, search, etc.)
  if (url.pathname.startsWith('/api/')) {
    e.respondWith(
      fetch(e.request)
        .then(res => res)
        .catch(() => new Response(JSON.stringify({error:'offline'}), {
          status: 503,
          headers: {'Content-Type': 'application/json'}
        }))
    );
    return;
  }

  // Cache-first for static shell
  e.respondWith(
    caches.match(e.request).then(cached => {
      if (cached) return cached;
      return fetch(e.request).then(res => {
        if (res.ok && e.request.method === 'GET') {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return res;
      }).catch(() => {
        // Return cached index for navigation
        if (e.request.mode === 'navigate') {
          return caches.match('/static/index.html');
        }
        return new Response('', {status: 503});
      });
    })
  );
});
