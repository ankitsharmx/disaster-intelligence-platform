const CACHE_NAME = "apat-rakshak-v1";
const STATIC_ASSETS = [
  "/",
  "/manifest.json",
  "/favicon.ico",
  "/map",
  "/alerts",
  "/report",
  "/awareness",
];

// Install: Cache Shell & Core Navigation Assets
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

// Activate: Prune stale caches
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Fetch: Network-First for API and Emergency Data (Never cache emergency data indefinitely)
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // If request is to FastAPI backend or emergency overview, use NETWORK-FIRST
  if (url.pathname.includes("/api/") || url.pathname.includes("/overview")) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          return response;
        })
        .catch(() => {
          // If offline, attempt to serve last cached snapshot with stale header
          return caches.match(event.request).then((cached) => {
            if (cached) return cached;
            return new Response(
              JSON.stringify({ error: "offline", message: "You are currently offline. Showing cached baseline data." }),
              { headers: { "Content-Type": "application/json" } }
            );
          });
        })
    );
    return;
  }

  // Stale-While-Revalidate for static visual assets
  event.respondWith(
    caches.match(event.request).then((cached) => {
      const fetchPromise = fetch(event.request).then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200) {
          const clone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return networkResponse;
      });
      return cached || fetchPromise;
    })
  );
});

// Web Push Notification Handling
self.addEventListener("push", (event) => {
  let data = { title: "Emergency Disaster Alert", body: "New bulletin issued for your district." };
  if (event.data) {
    try {
      data = event.data.json();
    } catch {
      data = { title: "Emergency Disaster Alert", body: event.data.text() };
    }
  }

  const options = {
    body: data.body || data.message,
    icon: "/favicon.ico",
    badge: "/favicon.ico",
    vibrate: [200, 100, 200, 100, 200],
    data: {
      url: data.url || "/alerts",
    },
  };

  event.waitUntil(self.registration.showNotification(data.title, options));
});

// Notification Click Handler
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const targetUrl = event.notification.data?.url || "/alerts";
  event.waitUntil(
    clients.matchAll({ type: "window" }).then((windowClients) => {
      for (const client of windowClients) {
        if (client.url === targetUrl && "focus" in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(targetUrl);
      }
    })
  );
});
