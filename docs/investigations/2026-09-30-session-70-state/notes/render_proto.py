"""SATISFIABILITY PROTOTYPE for the U4b render script (scratchpad only).

Renders the four MYEZ launcher files from the 2048 master into an output dir,
deterministically, and prints the measurements the spec relies on.

Usage: python render_proto.py <master.png> <out_dir> [--check]
"""
import hashlib
import math
import os
import sys

from PIL import Image

MASTER_SHA256 = "70b2f8264d7eb07dbfe7627d332d991dc68429f3440615751bf99eacc05a4b41"
TILE_WHITE = (255, 255, 255)
CANVAS = 1024
# Android adaptive icon: 108 dp canvas, 66 dp safe-zone circle (diameter).
SAFE_RADIUS = CANVAS * 33 / 108  # 312.888... px
ADAPTIVE_MARGIN = 8  # px inside the safe circle
SPLASH_INK_WIDTH_FRACTION = 0.30
FAVICON = 48


def color_to_alpha_over_white(img):
    """Exact inverse of 'composite over white' for an opaque RGBA/RGB image.

    alpha = max_c(255 - C_c); F_c = 255 - (255 - C_c) * 255 / alpha (rounded).
    Compositing the result back over white reproduces C within 1 per channel.
    Pixels that are already transparent in the source stay transparent.
    """
    src = img.convert("RGBA")
    w, h = src.size
    sp = src.load()
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    op = out.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = sp[x, y]
            if a == 0:
                continue
            # the tile is opaque white; flatten partial source alpha onto white first
            if a < 255:
                r = (r * a + 255 * (255 - a) + 127) // 255
                g = (g * a + 255 * (255 - a) + 127) // 255
                b = (b * a + 255 * (255 - a) + 127) // 255
            d = max(255 - r, 255 - g, 255 - b)
            if d == 0:
                continue
            fr = 255 - ((255 - r) * 255 + d // 2) // d
            fg = 255 - ((255 - g) * 255 + d // 2) // d
            fb = 255 - ((255 - b) * 255 + d // 2) // d
            op[x, y] = (fr, fg, fb, d)
    return out


def flatten_on_white(img):
    base = Image.new("RGBA", img.size, TILE_WHITE + (255,))
    base.alpha_composite(img.convert("RGBA"))
    return base.convert("RGB")


def ink_extent(mark):
    """Max distance (px) of any non-transparent pixel centre from the canvas centre."""
    w, h = mark.size
    cx, cy = (w - 1) / 2, (h - 1) / 2
    a = mark.getchannel("A").load()
    best = 0.0
    for y in range(h):
        for x in range(w):
            if a[x, y] > 0:
                d = math.hypot(x - cx, y - cy)
                if d > best:
                    best = d
    return best


def place_scaled(mark, scale):
    """Scale the full-canvas mark about its centre onto a transparent CANVAS square."""
    size = max(1, round(mark.size[0] * scale))
    scaled = mark.resize((size, size), Image.LANCZOS)
    out = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    off = (CANVAS - size) // 2
    out.alpha_composite(scaled, (off, off)) if off >= 0 else None
    return out


def save(img, path):
    img.save(path, format="PNG", optimize=False, compress_level=9)


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def main(argv):
    master_path, out_dir = argv[1], argv[2]
    got = sha(master_path)
    if got != MASTER_SHA256:
        print("master sha mismatch", got)
        return 2
    master = Image.open(master_path)
    master.load()
    assert master.mode == "RGBA" and master.size == (2048, 2048)

    # 1) iOS icon: flatten the transparent corners onto tile white, 2048 -> 1024.
    icon = flatten_on_white(master).resize((CANVAS, CANVAS), Image.LANCZOS)

    # 2) the mark alone (white tile removed exactly), full 2048 canvas.
    mark2048 = color_to_alpha_over_white(master)
    r2048 = ink_extent(mark2048)

    # 3) adaptive foreground: fit the mark (scaled about the tile centre) inside
    #    the 66 dp safe circle minus a margin.
    scale_a = (SAFE_RADIUS - ADAPTIVE_MARGIN) / r2048
    adaptive = place_scaled(mark2048, scale_a)

    # 4) splash: the mark at SPLASH_INK_WIDTH_FRACTION of the canvas width.
    bbox = mark2048.getchannel("A").getbbox()
    ink_w = bbox[2] - bbox[0]
    scale_s = SPLASH_INK_WIDTH_FRACTION * CANVAS / ink_w
    splash = place_scaled(mark2048, scale_s)

    # 5) favicon: the full rounded tile (transparent corners kept), 48 px.
    favicon = master.resize((FAVICON, FAVICON), Image.LANCZOS)

    os.makedirs(out_dir, exist_ok=True)
    outs = {"icon.png": icon, "adaptive-icon.png": adaptive, "splash-icon.png": splash, "favicon.png": favicon}
    for name, im in outs.items():
        save(im, os.path.join(out_dir, name))
    print("r2048=%.3f ink_bbox=%s ink_w=%d scale_a=%.6f scale_s=%.6f" % (r2048, bbox, ink_w, scale_a, scale_s))
    for name in outs:
        p = os.path.join(out_dir, name)
        im = Image.open(p)
        a = im.getchannel("A") if "A" in im.getbands() else None
        print(name, im.mode, im.size, sha(p), os.path.getsize(p), "alpha_bbox=" + str(a.getbbox() if a else None))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
