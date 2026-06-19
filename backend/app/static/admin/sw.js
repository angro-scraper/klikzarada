const CACHE_NAME = 'sacuvaj-hranu-pilot-v103';
const APP_SHELL = [
  '/',
  '/pocetna',
  '/ponude',
  '/problem-bacanja-hrane',
  '/partner/onboarding',
  '/partner/preuzimanje',
  '/offline',
  '/admin-assets/manifest.webmanifest',
  '/admin-assets/brand/logo-mark.svg',
  '/admin-assets/icons/icon-192.png',
  '/admin-assets/icons/icon-512.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)).catch(() => null));
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);

  // API i upload fajlove uvek prvo tražimo sa mreže da podaci budu sveži.
  if (url.pathname.startsWith('/products') || url.pathname.startsWith('/reservations') || url.pathname.startsWith('/stores') || url.pathname.startsWith('/seller-api') || url.pathname.startsWith('/payments') || url.pathname.startsWith('/pilot-live') || url.pathname.startsWith('/uploads')) {
    return;
  }

  event.respondWith(
    fetch(request)
      .then((response) => {
        const copy = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(request, copy)).catch(() => null);
        return response;
      })
      .catch(() => caches.match(request).then((cached) => cached || caches.match('/offline')))
  );
});
