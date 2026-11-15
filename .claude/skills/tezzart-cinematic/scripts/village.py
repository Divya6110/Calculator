"""Original procedural establishing shot: a seaside village at dawn — sea, sun glitter,
windmill on the hill, a sailing ship on the horizon, gulls, drifting clouds, dust motes.
scene(t) -> PIL RGB 1080x1920.  (generic pirate-adventure mood; no copyrighted characters/places)"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1080, 1920
HZ = 1180                       # horizon line
rng = np.random.default_rng(11)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)

def lerp(a, b, t): return a + (b - a) * t

# ---- sky (static) ----
stops = [(0, (14, 16, 44)), (520, (52, 42, 96)), (860, (150, 82, 112)), (1060, (238, 136, 92)), (HZ, (255, 196, 140))]
sky = np.zeros((H, W, 3), np.float32)
for i in range(len(stops) - 1):
    (y0, c0), (y1, c1) = stops[i], stops[i + 1]
    t = np.clip((yy[:, :1] - y0) / (y1 - y0), 0, 1)
    m = (yy[:, :1] >= y0) & (yy[:, :1] < y1 + 1)
    sky = np.where(m[..., None], np.array(c0) + (np.array(c1) - np.array(c0)) * t[..., None], sky)
# stars fading toward horizon
st = np.zeros((H, W), np.float32)
for _ in range(260):
    x, y = rng.integers(0, W), rng.integers(0, 700)
    st[y, x] = rng.uniform(0.3, 1.0) * (1 - y / 700)
st = np.asarray(Image.fromarray((st * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8)), np.float32) / 255 * 2.5
sky = sky + st[..., None] * 255 * 0.6

# ---- clouds layer (RGBA, wider than frame, scrolls) ----
def clouds_layer():
    im = Image.new("RGBA", (1700, 1100), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for _ in range(26):
        cx, cy = rng.integers(0, 1700), rng.integers(250, 1000)
        w, h = rng.integers(160, 520), rng.integers(24, 70)
        warm = (cy - 250) / 750
        col = (int(lerp(90, 255, warm)), int(lerp(70, 160, warm)), int(lerp(120, 130, warm)), int(rng.integers(70, 150)))
        d.ellipse((cx - w, cy - h, cx + w, cy + h), fill=col)
    return im.filter(ImageFilter.GaussianBlur(22))
CLOUDS = clouds_layer()

# ---- island + village + windmill (static silhouette, with lit windows) ----
def island_layer():
    im = Image.new("RGBA", (1400, 420), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    pts = [(0, 420)]
    for x in range(0, 1401, 20):
        h = 120 + 150 * math.exp(-((x - 330) / 260) ** 2) + 60 * math.exp(-((x - 760) / 140) ** 2) + 12 * math.sin(x / 37)
        if x > 700: h *= max(0, 1 - (x - 700) / 220)
        pts.append((x, 420 - h))
    pts.append((1400, 420)); d.polygon(pts, fill=(46, 28, 52, 255))
    # houses on the slope
    for hx in [150, 205, 262, 318, 390, 450, 520, 600, 680, 740]:
        base = 420 - (120 + 150 * math.exp(-((hx - 330) / 260) ** 2) + 60 * math.exp(-((hx - 760) / 140) ** 2)) + 18
        w = rng.integers(34, 52); h = rng.integers(26, 40)
        d.rectangle((hx, base - h, hx + w, base), fill=(38, 22, 44, 255))
        d.polygon([(hx - 6, base - h), (hx + w / 2, base - h - 22), (hx + w + 6, base - h)], fill=(34, 20, 40, 255))
        for _ in range(rng.integers(0, 3)):
            wx = hx + rng.integers(6, w - 10); wy = base - h + rng.integers(6, h - 12)
            d.rectangle((wx, wy, wx + 6, wy + 7), fill=(255, 196, 110, 255))
    # windmill tower on the hill top
    tx, ty = 330, 420 - 270 + 6
    d.polygon([(tx - 20, ty), (tx + 20, ty), (tx + 11, ty - 95), (tx - 11, ty - 95)], fill=(36, 20, 42, 255))
    return im, (tx, ty - 95)
ISLAND, HUB = island_layer()

def windmill_blades(angle):
    im = Image.new("RGBA", (260, 260), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c = 130
    for k in range(4):
        a = angle + k * math.pi / 2
        ex, ey = c + 115 * math.cos(a), c + 115 * math.sin(a)
        px, py = -math.sin(a) * 12, math.cos(a) * 12
        d.polygon([(c, c), (ex, ey), (ex + px, ey + py), (c + px * 0.3, c + py * 0.3)], fill=(34, 20, 40, 255))
    d.ellipse((c - 7, c - 7, c + 7, c + 7), fill=(30, 18, 36, 255))
    return im

# ---- ship silhouette (generic brig) ----
def ship_layer():
    im = Image.new("RGBA", (240, 230), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.polygon([(10, 180), (230, 180), (205, 214), (35, 214)], fill=(26, 16, 30, 255))      # hull
    d.polygon([(200, 180), (238, 166), (230, 182)], fill=(26, 16, 30, 255))                 # bow
    for mx, top in [(85, 30), (150, 50)]:
        d.rectangle((mx - 2, top, mx + 2, 182), fill=(26, 16, 30, 255))
        d.polygon([(mx - 42, top + 22), (mx + 40, top + 18), (mx + 46, top + 70), (mx - 46, top + 74)], fill=(232, 196, 160, 255))
        d.polygon([(mx - 50, top + 84), (mx + 48, top + 80), (mx + 54, top + 140), (mx - 54, top + 146)], fill=(220, 180, 146, 255))
    d.polygon([(85, 30), (85, 8), (110, 16)], fill=(150, 40, 46, 255))                         # pennant
    return im
SHIP = ship_layer()

def gull(phase, s=1.0):
    im = Image.new("RGBA", (60, 30), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    f = math.sin(phase) * 9
    d.line([(4, 15 - f), (18, 12), (30, 17)], fill=(30, 20, 34, 255), width=3, joint="curve")
    d.line([(30, 17), (42, 12), (56, 15 - f)], fill=(30, 20, 34, 255), width=3, joint="curve")
    return im.resize((int(60 * s), int(30 * s)), Image.BICUBIC)

# ---- sea glitter texture ----
GL = rng.random((900, 2400)).astype(np.float32)
GL = np.asarray(Image.fromarray((GL * 255).astype(np.uint8)).resize((2400, 900), Image.BILINEAR).filter(ImageFilter.BoxBlur(1)), np.float32) / 255
SEA_Y = yy[HZ:, :] - HZ; SEA_X = xx[HZ:, :]
depth = SEA_Y / (H - HZ)
sea_base = (np.array([86, 52, 82], np.float32) * (1 - depth[..., None]) + np.array([12, 14, 30], np.float32) * depth[..., None])

MOTES = [(rng.uniform(0, W), rng.uniform(300, 1700), rng.uniform(1.5, 4), rng.uniform(0, 6.28)) for _ in range(70)]

def scene(t):
    sun_x, sun_y = 770, 1150 - 40 * t                      # sun rising
    img = sky.copy()
    # sun glow + disc
    r = np.sqrt((xx - sun_x) ** 2 + (yy - sun_y) ** 2)
    glow = np.exp(-(r / 380) ** 2) * 0.55 + np.exp(-(r / 120) ** 2) * 0.6
    img = img + glow[..., None] * np.array([255, 190, 120], np.float32)
    disc = np.clip((78 - r) / 3, 0, 1)
    img = img * (1 - disc[..., None]) + disc[..., None] * np.array([255, 238, 205], np.float32)
    # god rays
    ang = np.arctan2(yy - sun_y, xx - sun_x)
    rays = (np.sin(ang * 14 + t * 0.25) * 0.5 + 0.5) ** 6 * np.exp(-(r / 900)) * (yy < HZ)
    img = img + rays[..., None] * np.array([255, 200, 150], np.float32) * 0.22
    # sea
    sx = int(t * 40) % 1200
    g = GL[:H - HZ, sx:sx + W]
    width = 40 + depth * 420
    col = np.exp(-((SEA_X - sun_x) / width) ** 2)
    sparkle = np.clip((g - 0.62) * 4, 0, 1) * col * (1.2 - depth * 0.6)
    sheen = np.clip(np.sin(SEA_Y * 0.9 - t * 4 + g * 6) * 0.5 + 0.5, 0, 1) * 0.08
    sea = sea_base + (sparkle[..., None] * np.array([255, 214, 160]) + sheen[..., None] * np.array([120, 80, 110]))
    sea = sea + col[..., None] * np.array([90, 50, 40]) * (1 - depth[..., None]) * 0.8
    img[HZ:] = sea
    out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("RGBA")
    # clouds drift
    out.alpha_composite(CLOUDS.crop((int(300 - 22 * t), 0, int(300 - 22 * t) + W, 1100)), (0, 0))
    # island & windmill (slow parallax)
    ix = int(-260 + 8 * t)
    out.alpha_composite(ISLAND, (ix, HZ - 420 + 4))
    bl = windmill_blades(t * 0.9)
    out.alpha_composite(bl, (ix + HUB[0] - 130, HZ - 420 + 4 + HUB[1] - 130))
    # ship on the horizon, bobbing
    bob = math.sin(t * 2.1) * 3
    out.alpha_composite(SHIP.resize((168, 161), Image.BICUBIC), (int(640 + 9 * t), int(HZ - 146 + bob)))
    # gulls
    for k, (gx, gy, sp, s) in enumerate([(120, 640, 70, 1.3), (230, 700, 64, 1.0), (40, 760, 76, 0.85), (900, 520, -50, 0.9)]):
        out.alpha_composite(gull(t * 9 + k * 1.7, s), (int(gx + sp * t) % (W + 100) - 50, int(gy + math.sin(t * 1.5 + k) * 10)))
    # dust motes
    d = ImageDraw.Draw(out)
    for (mx, my, ms, ph) in MOTES:
        x = (mx + 14 * t + 10 * math.sin(t + ph)) % W; y = my - 18 * t
        a = int(110 * (0.5 + 0.5 * math.sin(t * 2 + ph)))
        d.ellipse((x - ms, y - ms, x + ms, y + ms), fill=(255, 220, 170, a))
    return out.convert("RGB")
