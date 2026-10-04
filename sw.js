const CACHE = "cropsignal-v23";
const ASSETS = ["/", "/index.html", "/dashboard.html", "/styles.css?v=3", "/model.css", "/app.js?v=18", "/knowledge-base.js?v=2", "/dashboard.js?v=6", "/manifest.webmanifest", "/vendor/tf.min.js?v=2", "/test-images/coffee-leaf-rust.jpg", "/audio/coffee-rust-sw.mp3", "/audio/uncertain-sw.mp3", "/audio/report-saved-sw.mp3", "/model-coffee-v1/model.json", "/model-coffee-v1/class_indices.json", "/model-coffee-v1/group1-shard1of1.bin"];
self.addEventListener("install", event => event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(ASSETS))));
self.addEventListener("activate", event => event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim())));
self.addEventListener("fetch", event => {
  if (event.request.method !== "GET" || new URL(event.request.url).pathname.startsWith("/api/")) return;
  // Match the complete request.  Query strings are used to version browser assets;
  // reducing them to a pathname can otherwise serve an old script indefinitely.
  event.respondWith(caches.match(event.request).then(cached => cached || fetch(event.request).then(response => {
    const clone = response.clone(); caches.open(CACHE).then(cache => cache.put(event.request, clone)); return response;
  })));
});
