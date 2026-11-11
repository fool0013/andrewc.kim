const whynum = document.getElementById("whynum");
const banner = document.getElementById("banner");
const tank = document.getElementById("tank");
const ctx = tank.getContext("2d");
const still = matchMedia("(prefers-reduced-motion: reduce)");
const MERGE = 900;
const POP = 200;

let school = [];
let raf = 0;
let running = false;
let on = false;

function rand(a, b) {
    return a + Math.random() * (b - a);
}

function fit() {
    const r = devicePixelRatio || 1;
    tank.width = Math.round(innerWidth * r);
    tank.height = Math.round(innerHeight * r);
    tank.style.width = innerWidth + "px";
    tank.style.height = innerHeight + "px";
    ctx.setTransform(r, 0, 0, r, 0, 0);
}

function stock(n) {
    const box = banner.getBoundingClientRect();
    const now = performance.now();
    const out = [];
    for (let i = 0; i < n; i++) {
        const dir = Math.random() < 0.5 ? -1 : 1;
        out.push({
            x: rand(box.left + 20, box.right - 20),
            y: rand(box.top + 10, box.bottom - 10),
            dx: rand(0.5, 1.8) * dir,
            dy: rand(-0.4, 0.4),
            size: rand(20, 46),
            hue: Math.floor(rand(0, 360)),
            born: still.matches ? -1e7 : now + 320 + rand(0, 900)
        });
    }
    return out;
}

function turn(f) {
    const way = f.dx > 0 ? 1 : -1;
    f.dx = rand(0.4, 2.2) * (Math.random() < 0.12 ? -way : way);
    f.dy = f.dx * rand(-0.35, 0.35) * (Math.random() < 0.5 ? -1 : 1);
}

function wander(f) {
    f.x += f.dx;
    f.y += f.dy;
    if (f.x < 10) f.dx = Math.abs(f.dx);
    if (f.x > innerWidth - 10) f.dx = -Math.abs(f.dx);
    if (f.y < 10) f.dy = Math.abs(f.dy);
    if (f.y > innerHeight - 10) f.dy = -Math.abs(f.dy);
    if (Math.random() < 0.006) turn(f);
}

function twos(f, t) {
    const half = f.size * 0.26;
    const k = t < 0.45 ? 0 : (t - 0.45) / 0.55;
    const gap = half * (1 - k * 0.92);
    ctx.save();
    ctx.translate(-gap, 0);
    ctx.fillText("2", 0, 0);
    ctx.restore();
    ctx.save();
    ctx.translate(gap, 0);
    ctx.scale(Math.cos(Math.PI * k), 1);
    ctx.fillText("2", 0, 0);
    ctx.restore();
}

function paint(now) {
    ctx.clearRect(0, 0, innerWidth, innerHeight);
    for (const f of school) {
        const age = now - f.born;
        if (age < 0) continue;
        ctx.save();
        ctx.fillStyle = "hsl(" + f.hue + " 52% 45%)";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.translate(f.x, f.y);
        if (age < MERGE) {
            f.x += f.dx * 0.25;
            f.y += f.dy * 0.25;
            ctx.font = f.size + 'px "Times New Roman", Times, serif';
            twos(f, age / MERGE);
        } else {
            if (!still.matches) wander(f);
            const pop = age < MERGE + POP ? 1 + 0.4 * (1 - (age - MERGE) / POP) : 1;
            ctx.font = f.size * pop + 'px "Times New Roman", Times, serif';
            ctx.fillText(f.dx > 0 ? "><>" : "<><", 0, 0);
        }
        ctx.restore();
    }
}

function loop(now) {
    if (!running) return;
    paint(now);
    raf = requestAnimationFrame(loop);
}

function start() {
    fit();
    school = stock(16);
    if (still.matches) {
        paint(performance.now());
        return;
    }
    running = true;
    cancelAnimationFrame(raf);
    raf = requestAnimationFrame(loop);
}

function stop() {
    running = false;
    cancelAnimationFrame(raf);
    school = [];
    ctx.clearRect(0, 0, innerWidth, innerHeight);
}

whynum.addEventListener("click", () => {
    on = !on;
    whynum.setAttribute("aria-pressed", String(on));
    banner.classList.toggle("flipped", on);
    tank.hidden = !on;
    if (on) start();
    else stop();
});

addEventListener("resize", () => {
    if (on) fit();
});
