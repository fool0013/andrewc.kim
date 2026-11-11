import argparse
import html
import http.server
import os
import re
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
from functools import partial
from pathlib import Path

from PIL import Image, ImageChops
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_for_filename, TextLexer

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
IMG = Path(__file__).resolve().parent.parent / "img"
DPR = 2

def edge_png(url, w, h, out, wait=1500):
    prof = tempfile.mkdtemp(prefix="shoot-")
    try:
        subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                        f"--user-data-dir={prof}", f"--force-device-scale-factor={DPR}",
                        f"--window-size={w},{h}", f"--virtual-time-budget={wait}",
                        f"--screenshot={out}", url],
                       check=True, capture_output=True, timeout=120)
    finally:
        shutil.rmtree(prof, ignore_errors=True)
    if not Path(out).exists():
        sys.exit("edge didn't write a screenshot")

def edge_png_realtime(url, w, h, out, wait_ms, clicks=()):
    import base64, json, socket, time, urllib.request
    import websocket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    prof = tempfile.mkdtemp(prefix="shoot-")
    proc = subprocess.Popen([EDGE, "--headless=new", "--hide-scrollbars", "--no-first-run",
                             f"--user-data-dir={prof}", f"--remote-debugging-port={port}",
                             "--remote-allow-origins=*", f"--force-device-scale-factor={DPR}",
                             f"--window-size={w},{h}", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ws = None
    try:
        for _ in range(100):
            try:
                targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=1))
                page = next(t for t in targets if t.get("type") == "page")
                break
            except Exception:
                time.sleep(0.1)
        else:
            sys.exit("edge devtools never came up")
        ws = websocket.create_connection(page["webSocketDebuggerUrl"], suppress_origin=True, timeout=60)
        n = 0

        def cmd(method, **params):
            nonlocal n
            n += 1
            ws.send(json.dumps({"id": n, "method": method, "params": params}))
            while True:
                msg = json.loads(ws.recv())
                if msg.get("id") == n:
                    if "error" in msg:
                        sys.exit(f"{method}: {msg['error']}")
                    return msg.get("result", {})

        cmd("Page.enable")
        cmd("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=DPR, mobile=False)
        cmd("Page.navigate", url=url)
        time.sleep(wait_ms / 1000)
        for x, y in clicks:
            for kind in ("mousePressed", "mouseReleased"):
                cmd("Input.dispatchMouseEvent", type=kind, x=x, y=y, button="left", clickCount=1)
            time.sleep(1.5)
        shot = cmd("Page.captureScreenshot", format="png")
        Path(out).write_bytes(base64.b64decode(shot["data"]))
    finally:
        if ws:
            ws.close()
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(prof, ignore_errors=True)

def trim(path, pad=0):
    im = Image.open(path).convert("RGB")
    box = ImageChops.difference(im, Image.new("RGB", im.size, "white")).getbbox()
    if box:
        im = im.crop((0, 0, im.width, min(im.height, box[3] + pad)))
    return im

def save(im, name, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"{name}.png"
    im.save(dest, optimize=True)
    w, h = im.size
    print(f"wrote {dest}  ({w}x{h} px, {dest.stat().st_size // 1024} kb)")
    print(f'  html: width="{w // DPR}" height="{h // DPR}"')

def shoot_code(a):
    src = Path(a.file).read_text(encoding="utf-8").splitlines()
    lo, hi = (int(x) for x in a.lines.split("-")) if a.lines else (1, len(src))
    raw = [l.expandtabs(4) for l in src[lo - 1:hi]]
    try:
        lexer = get_lexer_for_filename(a.file, stripnl=False)
    except Exception:
        lexer = TextLexer(stripnl=False)
    fmt = HtmlFormatter(style=a.style, noclasses=True, nowrap=True)
    out = highlight("\n".join(raw), lexer, fmt).split("\n")[:len(raw)]
    rows = []
    for n, (line, h) in enumerate(zip(raw, out), lo):
        ind = len(line) - len(line.lstrip(" "))
        m = re.match(r"(<span[^>]*>)( +)", h)
        if h.startswith(" " * ind):
            h = h[ind:]
        elif m and len(m.group(2)) >= ind:
            h = m.group(1) + h[m.end(1) + ind:]
        else:
            ind = 0
        num = "" if a.nolines else f'<span class="n">{n}</span>'
        rows.append(f'<div class="r">{num}'
                    f'<span class="c" style="padding-left:{ind + 4}ch;text-indent:-4ch">{h or " "}</span></div>')
    label = html.escape(a.label or Path(a.file).name)
    page = f"""<!doctype html><meta charset="utf-8"><style>
html,body{{margin:0;background:
.box{{margin:0;border:1px solid
.hd{{font:13px/1 Consolas,monospace;color:
.code{{font:13px/20px Consolas,"Courier New",monospace;padding:10px 0}}
.r{{display:grid;grid-template-columns:{"1fr" if a.nolines else f"{len(str(hi))}ch 1fr"};column-gap:12px;padding:0 12px}}
.n{{color:
.c{{white-space:pre-wrap;word-break:break-word}}
</style><div class="box"><div class="hd">{label}</div><div class="code">{"".join(rows)}</div></div>"""
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "code.html"
        f.write_text(page, encoding="utf-8")
        png = Path(td) / "shot.png"
        edge_png(f.as_uri(), a.width, 60 + len(raw) * 40 + 200, png)
        im = trim(png)
    save(im, a.name, Path(a.out) if a.out else IMG)

class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

def shoot_page(a):
    w, h = (int(x) for x in a.size.split("x"))
    with tempfile.TemporaryDirectory() as td:
        png = Path(td) / "shot.png"
        if a.serve:
            handler = partial(_Quiet, directory=a.serve)
            with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
                threading.Thread(target=srv.serve_forever, daemon=True).start()
                url = f"http://localhost:{srv.server_address[1]}/{a.target.lstrip('/')}"
                edge_png(url, w, h, png, a.wait)
                srv.shutdown()
        elif a.realtime:
            clicks = [tuple(int(v) for v in c.split(",")) for c in a.click]
            edge_png_realtime(a.target, w, h, png, a.wait, clicks)
        else:
            edge_png(a.target, w, h, png, a.wait)
        im = Image.open(png).convert("RGB")
        im.load()
    save(im, a.name, Path(a.out) if a.out else IMG)

ap = argparse.ArgumentParser()
sub = ap.add_subparsers(dest="cmd", required=True)
c = sub.add_parser("code")
c.add_argument("file")
c.add_argument("--lines", help="e.g. 174-194")
c.add_argument("--label", help="path shown in the header, e.g. careclock/js/fda.js")
c.add_argument("--name", required=True)
c.add_argument("--style", default="bw", help="pygments style: bw (black/white), default, friendly, ...")
c.add_argument("--width", type=int, default=760)
c.add_argument("--nolines", action="store_true", help="no line numbers (terminal output, diffs)")
c.add_argument("--out", help="output dir (default: img/)")
p = sub.add_parser("page")
p.add_argument("target", help="url, or a path under --serve")
p.add_argument("--serve", help="serve this folder on localhost and shoot TARGET from it")
p.add_argument("--name", required=True)
p.add_argument("--size", default="1280x800")
p.add_argument("--wait", type=int, default=3000, help="ms of page time before the shot")
p.add_argument("--realtime", action="store_true", help="real-time wait with gpu on (games, webgl, canvas)")
p.add_argument("--click", action="append", default=[], help="x,y in css px to click before the shot (realtime only)")
p.add_argument("--out", help="output dir (default: img/)")
a = ap.parse_args()
shoot_code(a) if a.cmd == "code" else shoot_page(a)
