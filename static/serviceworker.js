// PWA Service Worker — кеширование и офлайн-режим

const CACHE_NAME = 'pwa-cache-v1';
const OFFLINE_URL = '/offline/';

const PRECACHE_URLS = [
    '/',
    OFFLINE_URL,
    '/manifest.json',
];

// === Install ===
self.addEventListener('install', event => {
    self.skipWaiting();  // активируемся сразу, не ждём закрытия вкладок
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => {
            return cache.addAll(PRECACHE_URLS);
        })
    );
});

// === Activate ===
self.addEventListener('activate', event => {
    event.waitUntil(
        (async () => {
            // Удаляем старые кеши
            const keys = await caches.keys();
            await Promise.all(
                keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
            );
            await self.clients.claim();  // начинаем управлять сразу
        })()
    );
});

// === Fetch ===
self.addEventListener('fetch', event => {
    const req = event.request;

    // Только GET
    if (req.method !== 'GET') return;

    // Пропускаем запросы к админке, webpush, API, сторонним доменам
    const url = new URL(req.url);
    if (url.origin !== self.location.origin) return;
    if (url.pathname.startsWith('/admin')) return;
    if (url.pathname.startsWith('/webpush')) return;
    if (url.pathname.startsWith('/api')) return;
    if (url.pathname.startsWith('/accounts')) return;  // если не хочешь кешировать логин

    // Стратегия: Network-first с fallback на кеш и офлайн-страницу
    event.respondWith(
        fetch(req)
            .then(response => {
                // Кешируем успешные ответы
                if (response && response.status === 200 && response.type === 'basic') {
                    const copy = response.clone();
                    caches.open(CACHE_NAME).then(cache => cache.put(req, copy));
                }
                return response;
            })
            .catch(() => {
                return caches.match(req).then(cached => {
                    if (cached) return cached;
                    // Если это запрос страницы (не картинки/скрипты) — офлайн-страница
                    if (req.mode === 'navigate') {
                        return caches.match(OFFLINE_URL);
                    }
                });
            })
    );
});