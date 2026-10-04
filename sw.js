const CACHE = "cropsignal-v29";
const ASSETS = ["/", "/index.html", "/dashboard.html", "/styles.css?v=3", "/model.css", "/app.js?v=23", "/knowledge-base.js?v=2", "/dashboard.js?v=8", "/manifest.webmanifest", "/vendor/tf.min.js?v=2", "/test-images/coffee-leaf-rust.jpg", "/audio/coffee-rust-sw.mp3", "/audio/uncertain-sw.mp3", "/audio/report-saved-sw.mp3", "/model-coffee-v1/model.json", "/model-coffee-v1/class_indices.json", "/model-coffee-v1/group1-shard1of1.bin"];
// Tunnels such as ngrok answer unknown clients with an HTML interstitial (status 200).
// Send the skip header and refuse to cache anything that is not the real file.
const request = url => new Request(url, {headers: {"ngrok-skip-browser-warning": "1"}});
const isValid = (response, url) => response.ok && !response.headers.get("ngrok-error-code") &&
  (/\.(js|css|json|mp3|jpg|bin|webmanifest)(\?|$)/.test(url) ? !(response.headers.get("content-type") || "").includes("text/html") : true);
async function fetchAndCache(cache, url) {
  const response = await fetch(request(url), {cache: "reload"});
  if (!isValid(response, url)) throw new Error("Unexpected response for " + url);
  await cache.put(url, response);
}
self.addEventListener("install", event => event.waitUntil((async () => {
  const cache = await caches.open(CACHE);
  // Page shell first: if any large asset fails, the app still opens offline.
  await Promise.all(ASSETS.map(url => fetchAndCache(cache, url).catch(() => {})));
  await self.skipWaiting();
})()));
self.addEventListener("activate", event => event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim())));
self.addEventListener("fetch", event => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET" || url.origin !== location.origin || url.pathname.startsWith("/api/")) return;
  // Match the complete request.  Query strings are used to version browser assets;
  // reducing them to a pathname can otherwise serve an old script indefinitely.
  event.respondWith((async () => {
    const cached = await caches.match(event.request);
    if (cached) return cached;
    try {
      const response = await fetch(new Request(event.request, {headers: {"ngrok-skip-browser-warning": "1"}}));
      if (isValid(response, event.request.url)) { const clone = response.clone(); caches.open(CACHE).then(cache => cache.put(event.request, clone)); }
      return response;
    } catch (error) {
      // Offline navigation (typed URL, home-screen icon, any path): serve the app shell.
      if (event.request.mode === "navigate") return (await caches.match("/index.html")) || (await caches.match("/"));
      throw error;
    }
  })());
});
