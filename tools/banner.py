import sys
from pathlib import Path

from PIL import Image, ImageOps

W, H = 1120, 640
OUT = Path(__file__).resolve().parent.parent / "assets" / "banner.jpg"

def crop(im):
    im = ImageOps.exif_transpose(im).convert("RGB")
    return ImageOps.fit(im, (W, H), Image.LANCZOS, centering=(0.5, 0.45))

if __name__ == "__main__":
    OUT.parent.mkdir(exist_ok=True)
    crop(Image.open(sys.argv[1])).save(OUT, "JPEG", quality=88, optimize=True, progressive=True)
    print("wrote", OUT)
