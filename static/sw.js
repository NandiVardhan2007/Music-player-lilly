/* Lily Music — Service Worker v3 */
const CACHE = 'lily-v3';
const SHELL = ['/', '/static/index.html', '/static/manifest.json'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>clients.claim()));
});
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (url.pathname.startsWith('/api/')) {
    e.respondWith(fetch(e.request).catch(()=>new Response(JSON.stringify({error:'offline'}),{status:503,headers:{'Content-Type':'application/json'}})));
    return;
  }
  e.respondWith(caches.match(e.request).then(cached=>{
    if(cached) return cached;
    return fetch(e.request).then(res=>{
      if(res.ok&&e.request.method==='GET'){const c=res.clone();caches.open(CACHE).then(ca=>ca.put(e.request,c))}
      return res;
    }).catch(()=>e.request.mode==='navigate'?caches.match('/static/index.html'):new Response('',{status:503}));
  }));
});
