"""Render MYEZ App Store screenshots as HTML/CSS in headless Chrome.

Each slide: a real, unedited app capture shown inside a realistic iPhone Pro Max frame
(titanium edge, bezel, Dynamic Island, side buttons) with a clean 9:41 status bar replacing
the captured one, on a brand field, with a Geist headline. The capture's pixels are never
altered, only cropped (status bar / sheet chrome) and scaled.

Usage: python -I render_frames.py <raw_dir> <out_dir>
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

CHROME = r"C:/Program Files/Google/Chrome/Application/chrome.exe"
FONTS = Path(r"C:/Users/SynAckITPC/Documents/AI/sc-s70-u4b/SmartCompareApp/assets/fonts")
W, H = 1320, 2868
SRC_W, SRC_H = 1320, 2868          # capture size (iPhone 6.9")
STATUS_SRC = 165                   # status-bar band height in capture pixels

FIELDS = {
    "mint": dict(bg="#EAF6F0", ink="#000000", sub="#3E5C50"),
    "grove": dict(bg="#063D2E", ink="#FFFFFF", sub="#A7C4B8"),
}

SLIDES = [
    dict(name="01_two_products", src="9a3c6a57-image.png", crop=165, field="mint",
         head=["Two products.", "@vs", "One clear pick."], sub="Snap, paste a link or type to compare.",
         show_until=2440),
    dict(name="02_pros_and_cons", src="57e30fdb-image.png", crop=236, field="grove",
         head=["Pros and cons", "for both sides"], sub="Not just for the winner.",
         show_until=2400),
    dict(name="03_reviews", src="c693307a-image.png", crop=236, field="mint",
         head=["Owner reviews,", "summed up"], sub="What owners say, in a few lines.",
         show_until=2085),
    dict(name="04_type_two", src="6eea9a31-image.png", crop=165, field="grove",
         head=["Type any", "two products"], sub="Perfume, phones, skincare and more.",
         show_until=2420),
    dict(name="05_popular", src="7754414e-image.png", crop=165, field="mint",
         head=["Start from a", "popular comparison"], sub="Prices shown in Bahraini Dinar.",
         show_until=2500),
]
PHONE_W = 1180
HEAD_PX = 112

STATUS_ICONS = """
<svg class="sb-right" viewBox="0 0 330 60" xmlns="http://www.w3.org/2000/svg">
  <g fill="#000">
    <rect x="0" y="36" width="15" height="20" rx="4"/>
    <rect x="22" y="27" width="15" height="29" rx="4"/>
    <rect x="44" y="17" width="15" height="39" rx="4"/>
    <rect x="66" y="6" width="15" height="50" rx="4"/>
  </g>
  <g fill="none" stroke="#000" stroke-linecap="round">
    <path d="M118 22 a44 44 0 0 1 62 0" stroke-width="9"/>
    <path d="M128 33 a29 29 0 0 1 42 0" stroke-width="9"/>
  </g>
  <circle cx="149" cy="47" r="7" fill="#000"/>
  <rect x="208" y="9" width="96" height="44" rx="13" fill="none" stroke="#000" stroke-opacity=".38" stroke-width="5"/>
  <rect x="215" y="16" width="82" height="30" rx="8" fill="#000"/>
  <path d="M310 24 v14 a7 7 0 0 0 0 -14 z" fill="#000" fill-opacity=".45"/>
</svg>"""


def font_face(name, file, weight):
    url = (FONTS / file).as_uri()
    return "@font-face{font-family:%s;src:url('%s') format('truetype');font-weight:%d;}" % (name, url, weight)


def slide_html(s, raw_dir):
    f = FIELDS[s["field"]]
    pw = PHONE_W
    k = pw / 1120.0                          # frame proportions designed at 1120 px
    edge, bezel = round(12 * k), round(20 * k)
    screen_w = pw - 2 * (edge + bezel)
    scale = screen_w / SRC_W
    status_h = STATUS_SRC * scale
    r_body = round(205 * k)
    r_bezel = r_body - edge
    r_screen = r_bezel - bezel
    img_url = (Path(raw_dir) / s["src"]).resolve().as_uri()
    img_h = SRC_H * scale
    img_top = status_h - s["crop"] * scale   # shift so the cropped band sits under our status bar
    screen_h = SRC_H * scale

    lines = []
    for line in s["head"]:
        if line == "@vs":
            lines.append('<div class="vs"><span>vs</span></div>')
        else:
            lines.append('<div class="h">%s</div>' % line)

    island_w, island_h = 0.287 * screen_w, 0.083 * screen_w * 1.0
    phone_top = round(H - (edge + bezel) - (status_h + (s["show_until"] - s["crop"]) * scale))
    n_text = sum(1 for l in s["head"] if l != "@vs")
    copy_h = n_text * HEAD_PX * 1.02 + (138 if "@vs" in s["head"] else 0) + 34 + 60
    copy_top = max(150, round(phone_top - 120 - copy_h))
    s = dict(s, phone_top=phone_top, copy_top=copy_top)
    return """<!doctype html><html><head><meta charset="utf-8"><style>
%s%s%s
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:%dpx;height:%dpx;overflow:hidden;background:%s}
body{position:relative;font-family:Geist,sans-serif;-webkit-font-smoothing:antialiased}
.copy{position:absolute;left:104px;top:%dpx;right:104px}
.h{font-weight:700;font-size:%dpx;line-height:1.02;letter-spacing:-0.035em;color:%s}
.vs{margin:18px 0 22px}
.vs span{display:inline-block;font-weight:700;font-size:58px;line-height:1;letter-spacing:.02em;
  color:#fff;background:#10B981;border-radius:999px;padding:16px 40px 20px}
.sub{margin-top:34px;font-weight:400;font-size:46px;line-height:1.3;color:%s}
.phone{position:absolute;left:%dpx;top:%dpx;width:%dpx;height:%dpx}
.body{position:absolute;inset:0;border-radius:%dpx;
  background:linear-gradient(115deg,#5b5b60 0%%,#2a2a2d 18%%,#45454a 48%%,#1f1f22 78%%,#4d4d52 100%%);
  box-shadow:0 60px 120px rgba(0,0,0,.28),0 18px 40px rgba(0,0,0,.18)}
.bezel{position:absolute;inset:%dpx;border-radius:%dpx;background:#050505}
.screen{position:absolute;inset:%dpx;border-radius:%dpx;overflow:hidden;background:#fff}
.screen img{position:absolute;left:0;top:%.1fpx;width:%.1fpx;height:%.1fpx}
.sb{position:absolute;left:0;top:0;width:100%%;height:%.1fpx;background:#fff}
.time{position:absolute;left:%.1fpx;top:%.1fpx;font-family:Geist;font-weight:600;font-size:%.1fpx;color:#000;letter-spacing:-0.01em}
.sb-right{position:absolute;right:%.1fpx;top:%.1fpx;width:%.1fpx;height:auto}
.island{position:absolute;left:50%%;top:%.1fpx;width:%.1fpx;height:%.1fpx;transform:translateX(-50%%);
  background:#000;border-radius:999px}
.btn{position:absolute;background:linear-gradient(90deg,#2a2a2d,#5a5a5f);border-radius:6px}
</style></head><body>
<div class="copy">%s<div class="sub">%s</div></div>
<div class="phone">
  <div class="btn" style="left:-%dpx;top:%dpx;width:%dpx;height:%dpx"></div>
  <div class="btn" style="left:-%dpx;top:%dpx;width:%dpx;height:%dpx"></div>
  <div class="btn" style="left:-%dpx;top:%dpx;width:%dpx;height:%dpx"></div>
  <div class="btn" style="right:-%dpx;top:%dpx;width:%dpx;height:%dpx"></div>
  <div class="body"></div>
  <div class="bezel" style="inset:%dpx"></div>
  <div class="screen" style="inset:%dpx">
    <img src="%s">
    <div class="sb"><div class="time">9:41</div>%s</div>
    <div class="island"></div>
  </div>
</div>
</body></html>""" % (
        font_face("Geist", "Geist-Bold.ttf", 700), font_face("Geist", "Geist-SemiBold.ttf", 600),
        font_face("Geist", "Geist-Regular.ttf", 400),
        W, H, f["bg"], s["copy_top"], HEAD_PX, f["ink"], f["sub"],
        (W - pw) // 2, s["phone_top"], pw, round(screen_h + 2 * (edge + bezel)),
        r_body, edge, r_bezel, edge + bezel, r_screen,
        img_top, screen_w, img_h,
        status_h,
        screen_w * 0.105, status_h * 0.36, screen_w * 0.043,
        screen_w * 0.055, status_h * 0.37, screen_w * 0.215,
        status_h * 0.17, island_w, island_h,
        "".join(lines), s["sub"],
        round(6 * k), round(420 * k), round(8 * k), round(110 * k),
        round(6 * k), round(590 * k), round(8 * k), round(180 * k),
        round(6 * k), round(800 * k), round(8 * k), round(180 * k),
        round(6 * k), round(640 * k), round(8 * k), round(280 * k),
        edge, edge + bezel, img_url, STATUS_ICONS,
    )


def render(html, out_png):
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as fh:
        fh.write(html)
        page = fh.name
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--force-device-scale-factor=1", "--allow-file-access-from-files",
                    "--window-size=%d,%d" % (W, H), "--screenshot=" + out_png,
                    Path(page).as_uri()], check=True, capture_output=True, timeout=120)
    os.unlink(page)
    im = Image.open(out_png).convert("RGB")
    if im.size != (W, H):
        raise SystemExit("unexpected render size %s for %s" % (im.size, out_png))
    im.save(out_png, "PNG", optimize=True)


def main(raw_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for s in SLIDES:
        out = os.path.abspath(os.path.join(out_dir, s["name"] + ".png"))
        render(slide_html(s, raw_dir), out)
        with Image.open(out) as chk:
            print(out, chk.size, chk.mode)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
