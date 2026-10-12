"""Prepare App Store iPhone screenshots from real device captures.

Usage (venv python, -I):
  python -I prep_screenshots.py <captures_dir> <out_dir>

For every .png/.jpg/.jpeg in <captures_dir> (sorted by name) it writes two portrait PNGs:
  <out_dir>/iphone_6.9_1320x2868/<name>.png  (iPhone with Dynamic Island, large display)
  <out_dir>/iphone_6.3_1206x2622/<name>.png  (iPhone with Dynamic Island, medium display = the REQUIRED size)
Each output is RGB (alpha stripped onto white), scaled to cover the target and centre-cropped.
It refuses a landscape capture and warns when the aspect differs from the target by more
than 1 % (more than a few rows would be cropped). It then re-opens every output and checks
size, mode and the absence of an alpha band. Sizes: Apple screenshot specifications
(https://developer.apple.com/help/app-store-connect/reference/app-information/screenshot-specifications).
"""
import os
import sys

from PIL import Image

TARGETS = {
    "iphone_6.9_1320x2868": (1320, 2868),
    "iphone_6.3_1206x2622": (1206, 2622),
}
EXTS = (".png", ".jpg", ".jpeg")


def flatten(img):
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.split()[-1])
        return bg
    return img.convert("RGB")


def cover_crop(img, tw, th):
    w, h = img.size
    scale = max(tw / w, th / h)
    nw, nh = round(w * scale), round(h * scale)
    img = img.resize((nw, nh), Image.LANCZOS)
    left = (nw - tw) // 2
    top = (nh - th) // 2
    return img.crop((left, top, left + tw, top + th))


def main(src, dst):
    files = sorted(f for f in os.listdir(src) if f.lower().endswith(EXTS))
    if not files:
        print("no captures found in", src)
        return 2
    rc = 0
    for f in files:
        with Image.open(os.path.join(src, f)) as im:
            im.load()
            w, h = im.size
            if w > h:
                print("REFUSED landscape:", f, w, h)
                rc = 1
                continue
            base = flatten(im)
        for folder, (tw, th) in TARGETS.items():
            drift = abs((w / h) - (tw / th)) / (tw / th)
            if drift > 0.01:
                print("WARN aspect drift %.2f%% for %s -> %s" % (drift * 100, f, folder))
            out_dir = os.path.join(dst, folder)
            os.makedirs(out_dir, exist_ok=True)
            out = os.path.join(out_dir, os.path.splitext(f)[0] + ".png")
            cover_crop(base, tw, th).save(out, "PNG", optimize=True)
            with Image.open(out) as chk:
                ok = chk.size == (tw, th) and chk.mode == "RGB" and "A" not in chk.getbands()
            print("%s %s src=%dx%d out=%dx%d mode=RGB alpha=no %s"
                  % ("OK  " if ok else "FAIL", folder, w, h, tw, th, f))
            if not ok:
                rc = 1
    return rc


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
