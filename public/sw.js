const STATIC_CACHE = "kundali-static-v1";
const DYNAMIC_CACHE = "kundali-dynamic-v1";

const STATIC_ASSETS = [
  "/",
  "/offline.html",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/manifest.webmanifest",
];

const STATIC_PATTERNS = [/_next\/static\//, /^\/icons\//];

// Install: pre-cache static assets
self.addEventListener("install", (event) => {
  console.log("Service Worker installing...");
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => {
      console.log("Caching static assets");
      return cache.addAll(STATIC_ASSETS).catch((err) => {
        console.warn("Some static assets failed to cache:", err);
      });
    })
  );
  self.skipWaiting();
});

// Activate: clean up old caches
self.addEventListener("activate", (event) => {
  console.log("Service Worker activating...");
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter(
            (cacheName) =>
              cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE
          )
          .map((cacheName) => {
            console.log("Deleting old cache:", cacheName);
            return caches.delete(cacheName);
          })
      );
    })
  );
  self.clients.claim();
});

// Fetch: cache-first for static, network-first for others (never cache API).
// Only same-origin GET requests are ever cached — cross-origin calls (e.g.
// Supabase auth/REST) and non-GET methods pass straight through, both to
// avoid caching sensitive responses and because Cache.put() throws on
// non-GET requests.
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  if (request.method !== "GET" || url.origin !== self.location.origin) {
    return; // default browser handling, no SW interception
  }

  // Never cache API responses
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(fetch(request));
    return;
  }

  // Cache-first for static assets
  const isStatic = STATIC_PATTERNS.some((pattern) =>
    pattern.test(url.pathname)
  );

  if (isStatic) {
    event.respondWith(
      caches.match(request).then((response) => {
        return response || fetch(request).then((fetchResponse) => {
          const cache = caches.open(STATIC_CACHE);
          cache.then((c) => c.put(request, fetchResponse.clone()));
          return fetchResponse;
        });
      })
    );
    return;
  }

  // Network-first for everything else
  event.respondWith(
    fetch(request)
      .then((response) => {
        if (!response || response.status !== 200 || response.type === "error") {
          return response;
        }
        const cache = caches.open(DYNAMIC_CACHE);
        cache.then((c) => c.put(request, response.clone()));
        return response;
      })
      .catch(async () => {
        return (
          (await caches.match(request)) ||
          (await caches.match("/offline.html")) ||
          new Response("Offline", {
            status: 503,
            statusText: "Service Unavailable",
          })
        );
      })
  );
});
