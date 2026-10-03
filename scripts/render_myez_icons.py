"""Render the MYEZ launcher art from the committed master (session 70 U4b).

Input: ``docs/brand/myez-icon-master-2048.png`` -- Ahmed's original 2048x2048
RGBA master (decision D4): a full-bleed white rounded tile carrying the black
MY/EZ wordmark and the emerald #10B981 dot. Its SHA-256 is pinned below; any
other input exits 2 before anything is rendered.

Outputs, the four files ``SmartCompareApp/app.json`` points at:

  * ``SmartCompareApp/assets/icon.png`` -- 1024x1024 RGB: the master flattened
    onto the tile white (the transparent corners become white, a full-bleed
    square; iOS applies its own mask), then 2048 -> 1024.
  * ``SmartCompareApp/assets/adaptive-icon.png`` -- 1024x1024 RGBA: the mark
    alone (the white tile removed exactly) scaled about the tile centre so
    every inked pixel lies inside the Android 66 dp safe circle, 8 px margin.
  * ``SmartCompareApp/assets/splash-icon.png`` -- 1024x1024 RGBA: the same mark
    with its ink width at 30 % of the canvas.
  * ``SmartCompareApp/assets/favicon.png`` -- 48x48 RGBA: the rounded tile with
    its transparent corners (``web.favicon``).

plus the manifest ``docs/brand/myez-icons.manifest.json``: the master SHA-256,
the Pillow version, the parameters, and per output the file SHA-256, the
SHA-256 of the decoded pixels (``Image.tobytes()`` in the file's own mode),
width, height and mode. JSON, sorted keys, 2-space indent, LF, no timestamps.

The two transparent renders carry the ink as colour-to-alpha over a REMOVED
white tile: they are correct only over #ffffff, which is what
``android.adaptiveIcon.backgroundColor`` and ``splash.backgroundColor`` say.
The composition keeps the master's own offset (the ink sits 32 px right of the
tile centre by design); nothing is re-centred.

Usage, from the repo root with the pinned venv:

    python scripts/render_myez_icons.py              # render + write manifest
    python scripts/render_myez_icons.py --check      # render in memory, compare
    python scripts/render_myez_icons.py --out-dir D  # dry render, no manifest

``--check`` writes nothing. It compares each committed file's mode, size and
decoded pixels with a fresh render (pixel equality, robust to zlib byte
differences across platforms) and the committed manifest, parsed as JSON, with
a freshly computed one whose file SHA-256s are those of the committed bytes.
Exit 0 = reproducible, 1 = a mismatch (each one listed), 2 = a precondition
failed (master SHA-256 or header, or an unpinned Pillow without
``--any-pillow``).

Pure stdlib + Pillow; no network, no randomness, no timestamps.
Spec: docs/investigations/2026-09-30-session-70-state/U4B_ICONS_DEPS_SPEC.md
section 4 (and its binding review corrections 9 and 10).
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import struct
import sys
from pathlib import Path

import PIL
from PIL import Image

REPO = Path(__file__).resolve().parents[1]

MASTER_REL = "docs/brand/myez-icon-master-2048.png"
MASTER_SHA256 = "70b2f8264d7eb07dbfe7627d332d991dc68429f3440615751bf99eacc05a4b41"
MASTER_SIZE = 2048
MANIFEST_REL = "docs/brand/myez-icons.manifest.json"
RENDERER_REL = "scripts/render_myez_icons.py"
ASSETS_REL = "SmartCompareApp/assets"

ICON = "icon.png"
ADAPTIVE = "adaptive-icon.png"
SPLASH = "splash-icon.png"
FAVICON_NAME = "favicon.png"
OUTPUT_NAMES = (ADAPTIVE, FAVICON_NAME, ICON, SPLASH)

# = requirements-dev.txt; another Pillow needs --any-pillow (a deliberate
# re-baseline -- the manifest records the version actually used).
PINNED_PILLOW = "12.3.0"

CANVAS = 1024
TILE_WHITE = (255, 255, 255)
# Android adaptive icon: the 66 dp safe circle on the 108 dp canvas.
SAFE_RADIUS = CANVAS * 33 / 108  # 312.888... px
ADAPTIVE_MARGIN = 8  # px inside the safe circle
SPLASH_INK_WIDTH_FRACTION = 0.30  # ink width / canvas width on the splash
FAVICON = 48
RESAMPLE = Image.Resampling.LANCZOS

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
COLOR_TYPE = {"RGB": 2, "RGBA": 6}


class PreconditionError(Exception):
    """An input or environment check failed; nothing was rendered."""


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def png_chunks(data: bytes) -> list[tuple[str, bytes]]:
    """(type, payload) of every chunk; the CRC is skipped, not verified."""
    if data[:8] != PNG_SIGNATURE:
        raise ValueError("not a PNG (bad signature)")
    chunks = []
    pos = 8
    while pos + 8 <= len(data):
        (length,) = struct.unpack(">I", data[pos : pos + 4])
        kind = data[pos + 4 : pos + 8].decode("latin-1")
        chunks.append((kind, data[pos + 8 : pos + 8 + length]))
        pos += 12 + length
        if kind == "IEND":
            break
    return chunks


def read_ihdr(data: bytes) -> tuple[int, int, int, int, int]:
    """(width, height, bit depth, colour type, interlace) of a PNG."""
    chunks = png_chunks(data)
    if not chunks or chunks[0][0] != "IHDR":
        raise ValueError("the first chunk is not IHDR")
    width, height, depth, color, _comp, _filt, interlace = struct.unpack(
        ">IIBBBBB", chunks[0][1][:13]
    )
    return width, height, depth, color, interlace


def load_master() -> Image.Image:
    path = REPO / MASTER_REL
    if not path.is_file():
        raise PreconditionError(f"master missing: {MASTER_REL}")
    data = path.read_bytes()
    got = sha256_hex(data)
    if got != MASTER_SHA256:
        raise PreconditionError(
            f"master SHA-256 mismatch: expected {MASTER_SHA256}, got {got}"
        )
    header = read_ihdr(data)
    if header != (MASTER_SIZE, MASTER_SIZE, 8, 6, 0):
        raise PreconditionError(
            f"master IHDR is {header}, expected 2048x2048 8-bit RGBA, not interlaced"
        )
    master = Image.open(io.BytesIO(data))
    master.load()
    if master.mode != "RGBA" or master.size != (MASTER_SIZE, MASTER_SIZE):
        raise PreconditionError(f"master decodes as {master.mode} {master.size}")
    return master


def remove_tile_white(master: Image.Image) -> Image.Image:
    """The exact inverse of "composite over white", integer arithmetic.

    Per pixel (r, g, b, a): a == 0 stays transparent; a partial alpha is first
    flattened onto white; d = max(255 - c) is the new alpha (d == 0, the tile
    white, disappears) and F_c = 255 - round((255 - c) * 255 / d). Compositing
    the result back over white reproduces the flattened master within 1 per
    channel -- and ONLY over white.
    """
    src = master.tobytes()
    out = bytearray(len(src))  # zero = (0, 0, 0, 0), transparent
    for i in range(0, len(src), 4):
        a = src[i + 3]
        if a == 0:
            continue
        r, g, b = src[i], src[i + 1], src[i + 2]
        if a < 255:
            white = 255 * (255 - a)
            r = (r * a + white + 127) // 255
            g = (g * a + white + 127) // 255
            b = (b * a + white + 127) // 255
        d = max(255 - r, 255 - g, 255 - b)
        if d == 0:
            continue
        half = d // 2
        out[i] = 255 - ((255 - r) * 255 + half) // d
        out[i + 1] = 255 - ((255 - g) * 255 + half) // d
        out[i + 2] = 255 - ((255 - b) * 255 + half) // d
        out[i + 3] = d
    return Image.frombytes("RGBA", master.size, bytes(out))


def ink_radius(mark: Image.Image) -> float:
    """Max distance of any alpha > 0 pixel centre from the canvas centre.

    Within one row the distance grows with |x - centre|, so the farthest inked
    pixel of a row is its first or its last one: only those are measured.
    """
    width, height = mark.size
    centre_x = (width - 1) / 2
    centre_y = (height - 1) / 2
    alpha = mark.getchannel("A").tobytes()
    best = 0.0
    for y in range(height):
        row = alpha[y * width : (y + 1) * width]
        last = len(row.rstrip(b"\x00")) - 1
        if last < 0:
            continue
        first = width - len(row.lstrip(b"\x00"))
        dy = y - centre_y
        for x in (first, last):
            best = max(best, math.hypot(x - centre_x, dy))
    return best


def place_scaled(mark: Image.Image, scale: float) -> Image.Image:
    """The full-canvas mark scaled about its centre onto a transparent canvas."""
    size = round(mark.size[0] * scale)
    scaled = mark.resize((size, size), RESAMPLE)
    out = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    offset = (CANVAS - size) // 2
    out.alpha_composite(scaled, (offset, offset))
    return out


def render(master: Image.Image) -> dict[str, Image.Image]:
    """The four outputs, keyed by file name (spec section 4.3)."""
    base = Image.new("RGBA", master.size, TILE_WHITE + (255,))
    base.alpha_composite(master)
    icon = base.convert("RGB").resize((CANVAS, CANVAS), RESAMPLE)

    mark = remove_tile_white(master)

    adaptive_scale = (SAFE_RADIUS - ADAPTIVE_MARGIN) / ink_radius(mark)
    adaptive = place_scaled(mark, adaptive_scale)

    left, _top, right, _bottom = mark.getchannel("A").getbbox()
    splash_scale = SPLASH_INK_WIDTH_FRACTION * CANVAS / (right - left)
    splash = place_scaled(mark, splash_scale)

    favicon = master.resize((FAVICON, FAVICON), RESAMPLE)

    return {ICON: icon, ADAPTIVE: adaptive, SPLASH: splash, FAVICON_NAME: favicon}


def encode_png(img: Image.Image) -> bytes:
    """PNG bytes with chunks IHDR, IDAT..., IEND only; never palette/interlaced."""
    img.info.clear()  # no text, gamma, ICC or dpi chunk can ride along
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=False, compress_level=9)
    data = buf.getvalue()
    kinds = [kind for kind, _payload in png_chunks(data)]
    if kinds[0] != "IHDR" or kinds[-1] != "IEND" or set(kinds[1:-1]) != {"IDAT"}:
        raise AssertionError(f"unexpected PNG chunks {kinds}")
    width, height, depth, color, interlace = read_ihdr(data)
    expected = (img.size[0], img.size[1], 8, COLOR_TYPE[img.mode], 0)
    if (width, height, depth, color, interlace) != expected:
        raise AssertionError(f"unexpected IHDR {(width, height, depth, color)}")
    return data


def output_rel(name: str) -> str:
    return f"{ASSETS_REL}/{name}"


def build_manifest(images: dict[str, Image.Image], file_sha256: dict[str, str]) -> dict:
    outputs = {}
    for name in OUTPUT_NAMES:
        img = images[name]
        outputs[output_rel(name)] = {
            "height": img.size[1],
            "mode": img.mode,
            "pixels_sha256": sha256_hex(img.tobytes()),
            "sha256": file_sha256[name],
            "width": img.size[0],
        }
    return {
        "master": {"path": MASTER_REL, "sha256": MASTER_SHA256},
        "outputs": outputs,
        "params": {
            "adaptive_margin_px": ADAPTIVE_MARGIN,
            "canvas": CANVAS,
            "favicon_px": FAVICON,
            "safe_radius_px": round(SAFE_RADIUS, 3),
            "splash_ink_width_fraction": SPLASH_INK_WIDTH_FRACTION,
            "tile_white": "#{:02x}{:02x}{:02x}".format(*TILE_WHITE),
        },
        "pillow": PIL.__version__,
        "renderer": RENDERER_REL,
    }


def manifest_text(manifest: dict) -> str:
    return json.dumps(manifest, sort_keys=True, indent=2) + "\n"


def write_outputs(images: dict[str, Image.Image], out_dir: Path) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    file_sha256 = {}
    for name in OUTPUT_NAMES:
        data = encode_png(images[name])
        (out_dir / name).write_bytes(data)
        file_sha256[name] = sha256_hex(data)
        img = images[name]
        size = f"{img.size[0]}x{img.size[1]}"
        print(f"{name} {img.mode} {size} {file_sha256[name]}")
    return file_sha256


def check(images: dict[str, Image.Image]) -> list[str]:
    """Every difference between the committed files and a fresh render."""
    problems = []
    file_sha256 = {}
    for name in OUTPUT_NAMES:
        rel = output_rel(name)
        path = REPO / rel
        if not path.is_file():
            problems.append(f"{rel}: missing")
            file_sha256[name] = "missing"
            continue
        data = path.read_bytes()
        file_sha256[name] = sha256_hex(data)
        on_disk = Image.open(io.BytesIO(data))
        on_disk.load()
        fresh = images[name]
        if on_disk.mode != fresh.mode:
            problems.append(f"{rel}: mode {on_disk.mode} != render {fresh.mode}")
        elif on_disk.size != fresh.size:
            problems.append(f"{rel}: size {on_disk.size} != render {fresh.size}")
        elif on_disk.tobytes() != fresh.tobytes():
            problems.append(f"{rel}: pixels differ from a fresh render")
        else:
            size = f"{fresh.size[0]}x{fresh.size[1]}"
            print(f"{name} {fresh.mode} {size} pixels match")
    path = REPO / MANIFEST_REL
    expected = build_manifest(images, file_sha256)
    if not path.is_file():
        problems.append(f"{MANIFEST_REL}: missing")
    elif json.loads(path.read_text(encoding="utf-8")) != expected:
        problems.append(f"{MANIFEST_REL}: differs from a freshly computed manifest")
    else:
        print(f"{Path(MANIFEST_REL).name} matches")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check", action="store_true", help="render in memory and compare"
    )
    mode.add_argument("--out-dir", type=Path, help="dry render into DIR (no manifest)")
    parser.add_argument(
        "--any-pillow", action="store_true", help=f"allow Pillow != {PINNED_PILLOW}"
    )
    args = parser.parse_args(argv)

    if PIL.__version__ != PINNED_PILLOW and not args.any_pillow:
        print(
            f"Pillow {PIL.__version__} is not the pinned {PINNED_PILLOW}; "
            "pass --any-pillow to re-baseline deliberately",
            file=sys.stderr,
        )
        return 2
    try:
        master = load_master()
    except PreconditionError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    images = render(master)

    if args.check:
        problems = check(images)
        for problem in problems:
            print(f"MISMATCH {problem}")
        return 1 if problems else 0
    if args.out_dir is not None:
        write_outputs(images, args.out_dir)
        return 0
    file_sha256 = write_outputs(images, REPO / ASSETS_REL)
    text = manifest_text(build_manifest(images, file_sha256))
    with open(REPO / MANIFEST_REL, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    print(f"{Path(MANIFEST_REL).name} {sha256_hex(text.encode('utf-8'))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
