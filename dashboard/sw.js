// ============================================
// EcoFleet AI Advisor — Service Worker (PWA)
// ============================================

const CACHE_NAME = 'ecofleet-v1';

// Asset statici da pre-cacheare all'installazione
const PRECACHE_URLS = [
    './',
    './index.html',
    './app.js',
    './style.css',
    './manifest.json',
    './icons/icon-192.png',
    './icons/icon-512.png',
    // CDN libs
    'https://cdn.jsdelivr.net/npm/vue@2/dist/vue.js',
    'https://cdn.jsdelivr.net/npm/chart.js',
    'https://cdnjs.cloudflare.com/ajax/libs/microsoft-signalr/6.0.1/signalr.min.js',
    // Google Fonts
    'https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap'
];

// ── INSTALL ──────────────────────────────────
self.addEventListener('install', (event) => {
    console.log('[SW] Install');
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => cache.addAll(PRECACHE_URLS))
            .then(() => self.skipWaiting())
    );
});

// ── ACTIVATE ─────────────────────────────────
self.addEventListener('activate', (event) => {
    console.log('[SW] Activate');
    event.waitUntil(
        caches.keys().then((cacheNames) =>
            Promise.all(
                cacheNames
                    .filter((name) => name !== CACHE_NAME)
                    .map((name) => caches.delete(name))
            )
        ).then(() => self.clients.claim())
    );
});

// ── FETCH ────────────────────────────────────
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // Skip non-GET requests (SignalR WebSocket, POST, DELETE, etc.)
    if (request.method !== 'GET') return;

    // Skip SignalR negotiate / WebSocket upgrade
    if (url.pathname.includes('/negotiate') || url.pathname.includes('/signalr')) return;

    // ── API calls → Network-First ──
    if (url.pathname.startsWith('/api') || url.hostname !== location.hostname) {
        // Per le chiamate API e i CDN, proviamo prima la rete
        if (url.pathname.startsWith('/api')) {
            event.respondWith(networkFirst(request));
            return;
        }
    }

    // ── Static assets → Cache-First ──
    event.respondWith(cacheFirst(request));
});

// ── Strategie di caching ─────────────────────

/**
 * Cache-First: cerchiamo nel cache, se non c'è andiamo in rete
 * e salviamo la risposta nel cache per la prossima volta.
 */
async function cacheFirst(request) {
    const cached = await caches.match(request);
    if (cached) return cached;

    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, response.clone());
        }
        return response;
    } catch (err) {
        // Offline e non in cache → risposta di fallback
        return new Response('Offline', { status: 503, statusText: 'Offline' });
    }
}

/**
 * Network-First: proviamo la rete, se fallisce usiamo il cache.
 * La risposta di rete viene salvata nel cache per un futuro fallback.
 */
async function networkFirst(request) {
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, response.clone());
        }
        return response;
    } catch (err) {
        const cached = await caches.match(request);
        if (cached) return cached;
        return new Response(JSON.stringify({ error: 'Offline' }), {
            status: 503,
            headers: { 'Content-Type': 'application/json' }
        });
    }
}
