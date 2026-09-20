const CACHE_NAME = 'rectg-cache-v5';
const PRECACHE_URLS = [
    '/',
    '/index.html',
    '/manifest.json',
    '/favicon.png'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(PRECACHE_URLS))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('fetch', event => {
    if (!event.request.url.startsWith(self.location.origin)) return;

    const url = new URL(event.request.url);

    if (url.pathname === '/data.json' || event.request.mode === 'navigate') {
        event.respondWith(networkFirst(event.request));
        return;
    }

    if (isStaticAsset(url)) {
        event.respondWith(cacheFirst(event.request));
    }
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.filter(cacheName => cacheName !== CACHE_NAME)
                    .map(cacheName => caches.delete(cacheName))
            ).then(() => self.clients.claim());
        })
    );
});

async function networkFirst(request) {
    const cache = await caches.open(CACHE_NAME);
    try {
        const response = await fetch(request);
        if (response && response.status === 200 && response.type === 'basic') {
            cache.put(request, response.clone());
        }
        return response;
    } catch {
        return caches.match(request) || caches.match('/index.html');
    }
}

async function cacheFirst(request) {
    const cached = await caches.match(request);
    if (cached) return cached;

    const response = await fetch(request);
    if (response && response.status === 200 && response.type === 'basic') {
        const cache = await caches.open(CACHE_NAME);
        cache.put(request, response.clone());
    }
    return response;
}

function isStaticAsset(url) {
    if (url.pathname.startsWith('/@vite') || url.pathname.startsWith('/@fs/') || url.pathname.startsWith('/src/')) {
        return false;
    }

    return (
        url.pathname.startsWith('/_astro/') ||
        PRECACHE_URLS.includes(url.pathname) ||
        /\.(?:css|js|mjs|png|jpg|jpeg|webp|svg|ico|json|woff2?)$/i.test(url.pathname)
    );
}
