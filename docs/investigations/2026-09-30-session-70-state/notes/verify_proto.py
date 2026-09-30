"""Verify prototype outputs and build a contact sheet (scratchpad only)."""
import math
import sys

from PIL import Image, ImageDraw

OUT = sys.argv[1]
MASTER = "C:/Users/SynAckITPC/Downloads/MYEZ-icon-white-2048.png"
SAFE_R = 1024 * 33 / 108
VIEW_R = 1024 * 36 / 108

icon = Image.open(OUT + "/icon.png")
ad = Image.open(OUT + "/adaptive-icon.png")
sp = Image.open(OUT + "/splash-icon.png")
fav = Image.open(OUT + "/favicon.png")

# icon facts
ip = icon.load()
print("icon corners", [ip[p] for p in [(0, 0), (1023, 0), (0, 1023), (1023, 1023)]])
em = sum(1 for y in range(0, 1024) for x in range(0, 1024)
         if (lambda c: c[1] > c[0] + 60 and c[1] > c[2] + 20)(ip[x, y]))
blk = sum(1 for y in range(0, 1024) for x in range(0, 1024) if max(ip[x, y]) < 40)
print("icon emerald px", em, "near-black px", blk)


def max_r(im):
    a = im.getchannel("A").load()
    w, h = im.size
    c = (w - 1) / 2
    best = 0
    for y in range(h):
        for x in range(w):
            if a[x, y] > 0:
                best = max(best, math.hypot(x - c, y - c))
    return best


print("adaptive max alpha radius", round(max_r(ad), 2), "safe", round(SAFE_R, 2))
print("splash max alpha radius", round(max_r(sp), 2))
for name, im in (("adaptive", ad), ("splash", sp)):
    a = im.getchannel("A")
    hist = a.histogram()
    print(name, "alpha0 px", hist[0], "alpha255 px", hist[255], "bbox", a.getbbox(),
          "corners", [im.getpixel(p) for p in [(0, 0), (1023, 1023)]])

# round trip: adaptive over white vs flattened master resized with same geometry is not
# pixel-identical by construction (different resample order), so measure the mark itself:
# composite splash over white and compare its ink colour stats.
white = Image.new("RGBA", (1024, 1024), (255, 255, 255, 255))
comp = white.copy()
comp.alpha_composite(sp)
cp = comp.convert("RGB").load()
em2 = [cp[x, y] for y in range(1024) for x in range(1024) if cp[x, y][1] > cp[x, y][0] + 60]
print("splash-over-white emerald sample", em2[len(em2) // 2] if em2 else None, "count", len(em2))

# contact sheet
sheet = Image.new("RGB", (4 * 420 + 50, 470), (200, 200, 200))
d = ImageDraw.Draw(sheet)
t1 = icon.resize((400, 400))
m = Image.new("L", (400, 400), 0)
ImageDraw.Draw(m).rounded_rectangle((0, 0, 399, 399), radius=90, fill=255)
sheet.paste(t1, (10, 10), m)
t2 = Image.new("RGBA", (1024, 1024), (255, 255, 255, 255))
t2.alpha_composite(ad)
t2 = t2.convert("RGB")
cm = Image.new("L", (1024, 1024), 0)
ImageDraw.Draw(cm).ellipse((512 - VIEW_R, 512 - VIEW_R, 512 + VIEW_R, 512 + VIEW_R), fill=255)
t2c = Image.new("RGB", (1024, 1024), (200, 200, 200))
t2c.paste(t2, (0, 0), cm)
dd = ImageDraw.Draw(t2c)
dd.ellipse((512 - SAFE_R, 512 - SAFE_R, 512 + SAFE_R, 512 + SAFE_R), outline=(255, 0, 0), width=3)
sheet.paste(t2c.resize((400, 400)), (430, 10))
phone = Image.new("RGB", (390, 844), (255, 255, 255))
spr = Image.new("RGBA", (1024, 1024), (255, 255, 255, 255))
spr.alpha_composite(sp)
spr = spr.convert("RGB").resize((390, 390))
phone.paste(spr, (0, (844 - 390) // 2))
phone = phone.resize((195, 422))
sheet.paste(phone, (850 + 100, 10))
d.rectangle((950, 10, 950 + 195, 10 + 422), outline=(0, 0, 0))
sheet.paste(fav.convert("RGBA").resize((192, 192), Image.NEAREST), (1290, 10), fav.convert("RGBA").resize((192, 192), Image.NEAREST))
sheet.paste(fav, (1290, 220), fav)
sheet.save(OUT + "/../contact_" + OUT.rstrip("/").split("/")[-1] + ".png")
print("sheet ok")
