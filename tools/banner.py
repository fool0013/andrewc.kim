import sys
from decimal import Decimal, getcontext
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

W, H = 1120, 640
OUT = Path(__file__).resolve().parent.parent / "assets" / "banner.jpg"
rng = np.random.default_rng(13)

def digits(n):
    getcontext().prec = n + 20
    one = Decimal(1)

    def arctan(x):
        total = term = one / x
        k = 0
        xx = x * x
        while term:
            k += 1
            term /= -xx
            total += term / (2 * k + 1)
        return total

    pi = 16 * arctan(Decimal(5)) - 4 * arctan(Decimal(239))
    return np.array([int(c) for c in str(pi).replace(".", "")[:n]], dtype=np.int64)


def glyphs(g):
    try:
        font = ImageFont.truetype("times.ttf", int(g * 0.8))
    except OSError:
        font = ImageFont.load_default()
    out = np.zeros((10, g, g), dtype=np.float32)
    for d in range(10):
        im = Image.new("L", (g, g), 0)
        ImageDraw.Draw(im).text((g / 2, g / 2), str(d), font=font, fill=255, anchor="mm")
        out[d] = np.asarray(im, dtype=np.float32) / 255
    return out


def placeholder():
    ss = 3
    w, h = W * ss, H * ss
    hor = 0.40 * h
    f = 0.9 * w
    cam = 1.6
    tilt = np.float32(np.deg2rad(23))
    dg = digits(997)
    gl = glyphs(64)
    g = gl.shape[1]

    sky_lo = np.array([0.38, 0.60, 0.75], dtype=np.float32)
    sky_hi = np.array([0.88, 0.94, 0.96], dtype=np.float32)
    deep = np.array([0.04, 0.18, 0.29], dtype=np.float32)
    lit = np.array([0.19, 0.49, 0.56], dtype=np.float32)
    foam = np.array([0.91, 0.97, 0.98], dtype=np.float32)
    haze = np.array([0.88, 0.94, 0.96], dtype=np.float32)

    out = np.zeros((h, w, 3), dtype=np.float32)
    xs = np.arange(w, dtype=np.float32)[None, :]

    for y0 in range(0, h, 192):
        y1 = min(y0 + 192, h)
        ys = np.arange(y0, y1, dtype=np.float32)[:, None]
        t = np.clip(ys / hor, 0, 1)[..., None]
        sky = (1 - t) * sky_lo + t * sky_hi

        z = cam * f / np.maximum(ys - hor, 0.1)
        x = (xs - 0.58 * w) * z / f
        u = x * np.cos(tilt) - z * np.sin(tilt)
        v = x * np.sin(tilt) + z * np.cos(tilt)

        uw = u + 0.22 * np.sin(v * 1.35 + 0.4) + 0.11 * np.sin(v * 0.47 - 1.1)
        iu = np.floor(uw).astype(np.int32)
        iv = np.floor(v).astype(np.int32)
        d = dg[(iv * 31 + iu) % dg.size]
        px = np.clip(((uw - iu) * g).astype(np.int32), 0, g - 1)
        py = np.clip(((v - iv) * g).astype(np.int32), 0, g - 1)
        ink = (gl[d, py, px] * 0.8)[..., None]

        ripple = (0.46 * np.sin(v * 2.1 + uw * 0.7)
                  + 0.32 * np.sin(v * 0.9 - uw * 1.9 + 2.1)
                  + 0.22 * np.sin(v * 5.3 + uw * 3.1 - 0.8))
        water = deep + (lit - deep) * (0.5 + 0.3 * ripple)[..., None]
        water += (np.clip(np.sin(v * 4.3 + uw * 1.1), 0, 1) ** 4)[..., None] * 0.09
        sea = water * (1 - ink) + foam * ink

        fog = (1 - np.exp(-z / 11.0))[..., None]
        sea = sea * (1 - fog) + haze * fog

        out[y0:y1] = np.where(ys[..., None] > hor, sea, sky)

    im = Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))
    return im.resize((W, H), Image.LANCZOS)

def crop(im):
    im = ImageOps.exif_transpose(im).convert("RGB")
    return ImageOps.fit(im, (W, H), Image.LANCZOS, centering=(0.5, 0.5))

def film(im):
    a = np.asarray(im).astype(np.float64) / 255
    lum = a @ np.array([0.299, 0.587, 0.114])
    a = 0.84 * a + 0.16 * lum[..., None]
    a = 0.06 + 0.90 * a
    a = a * np.array([0.98, 1.00, 1.04]) + np.array([0.0, 0.008, 0.022])
    hi = np.clip((lum - 0.6) / 0.4, 0, 1)[..., None]
    a = a * (1 - 0.22 * hi) + np.array([0.96, 0.99, 1.0]) * 0.22 * hi

    ys, xs = np.mgrid[0:H, 0:W]
    leak = np.exp(-(((xs - W * 1.02) / (W * 0.22)) ** 2 + ((ys - H * 0.15) / (H * 0.55)) ** 2))
    a += leak[..., None] * np.array([0.09, 0.05, 0.0])

    r = np.hypot((xs - W / 2) / (W / 2), (ys - H / 2) / (H / 2))
    a *= (1 - 0.13 * np.clip(r - 0.55, 0, 1) ** 1.6)[..., None]

    g = rng.normal(0, 1, (H, W))
    g = np.asarray(Image.fromarray(((g * 40) + 128).clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6)))
    a += ((g.astype(np.float64) - 128) / 40 * 0.03)[..., None]
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))

if __name__ == "__main__":
    src = crop(Image.open(sys.argv[1])) if len(sys.argv) > 1 else placeholder()
    OUT.parent.mkdir(exist_ok=True)
    film(src).save(OUT, "JPEG", quality=86, optimize=True, progressive=True)
    print("wrote", OUT)
