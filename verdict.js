addEventListener("load", () => setTimeout(() => {
    const v = document.getElementById("verdict");
    if (!v) return;
    const nav = performance.getEntriesByType("navigation")[0];
    const ms = Math.round(nav ? nav.loadEventStart : performance.now());
    const bytes = (nav && (nav.transferSize || nav.encodedBodySize)) ||
        new Blob([document.documentElement.outerHTML]).size;
    const ok = ms <= 1000;
    v.textContent = `${ok ? "accepted" : "time limit exceeded"}, ${ms} ms, ${Math.max(1, Math.round(bytes / 1024))} kb`;
    v.className = ok ? "ac" : "tle";
}, 0));
