// Tivù Player: tiene in memoria l'app (si apre anche senza rete) e le librerie del lettore. I canali non passano di qui.
const C = "tivu-v5";
const SHELL = ["./", "./index.html", "./manifest.webmanifest", "./icon.svg", "./icon-192.png", "./icon-512.png", "./lista.m3u"];
self.addEventListener("install", e => { e.waitUntil(caches.open(C).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())); });
self.addEventListener("activate", e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== C).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener("fetch", e => {
  const r = e.request; if (r.method !== "GET") return;
  const u = new URL(r.url);
  if (u.origin === location.origin && u.pathname.includes("/dec/")) return;   // il decodificatore (32 MB) resta nella cache normale del browser
  if (u.origin === location.origin) {   // l'app: prima la rete (aggiornamenti subito), senza rete la copia salvata
    // prima la rete (aggiornamenti subito); se la rete e' lenta (oltre 3 s) o assente, la copia salvata. La risposta dalla
    // rete, quando arriva, aggiorna comunque la copia per la volta successiva.
    const net = fetch(r).then(x => { if (x.ok) { const cp = x.clone(); caches.open(C).then(c => c.put(r, cp)); } return x; });
    const saved = () => caches.match(r).then(x => x || (r.mode === "navigate" ? caches.match("./index.html") : undefined));
    e.respondWith(new Promise(res => {
      let done = false; const fin = x => { if (!done && x) { done = true; res(x); } };
      const t = setTimeout(() => saved().then(fin), 3000);
      net.then(x => { clearTimeout(t); fin(x); }).catch(() => { clearTimeout(t); saved().then(x => x ? fin(x) : fin(Response.error())); });
    }));
    e.waitUntil(net.catch(() => {}));
  } else if (u.hostname === "cdn.jsdelivr.net" || u.hostname === "fonts.googleapis.com" || u.hostname === "fonts.gstatic.com") {
    e.respondWith(caches.match(r).then(x => x || fetch(r).then(y => { if (y.ok || y.type === "opaque") { const cp = y.clone(); caches.open(C).then(c => c.put(r, cp)); } return y; })));
  }
});
