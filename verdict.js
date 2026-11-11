addEventListener("load", () => setTimeout(() => {
    const v = document.getElementById("verdict");
    if (!v) return;
    const nav = performance.getEntriesByType("navigation")[0];
    const ms = Math.round(nav ? nav.loadEventStart : performance.now());
    const size = (r) => r.transferSize || r.encodedBodySize || r.decodedBodySize || 0;
    const doc = nav ? size(nav) : 0;
    const sub = performance.getEntriesByType("resource").reduce((a, r) => a + size(r), 0);
    const bytes = doc + sub || new Blob([document.documentElement.outerHTML]).size;
    const ok = ms <= 1000;
    v.textContent = `${ok ? "accepted" : "time limit exceeded"}, ${ms} ms, ${Math.max(1, Math.round(bytes / 1024))} kb`;
    v.className = ok ? "ac" : "tle";
}, 0));
