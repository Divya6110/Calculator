"""TEZZART cinematic renderer — photos/clips/scenes + beat-synced trailer titles + logo end card.

usage:
  python3 -I cinematic_render.py <project.json> <out.mp4>
  python3 -I cinematic_render.py <project.json> <preview_dir> --preview 1.5,2.6,13.4

Everything about one video lives in project.json (see ../examples/luffy_mural.json and SKILL.md).
Paths inside the JSON are resolved relative to the JSON file. "@skill/..." resolves inside this skill.
"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__)); SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)

CFG_PATH, OUT = sys.argv[1], sys.argv[2]
PREVIEW = [float(v) for v in sys.argv[4].split(",")] if len(sys.argv) > 4 and sys.argv[3] == "--preview" else None
CFG = json.load(open(CFG_PATH)); BASE = os.path.dirname(os.path.abspath(CFG_PATH))
def P(p): return os.path.join(SKILL, p[7:]) if p.startswith("@skill/") else (p if os.path.isabs(p) else os.path.join(BASE, p))

W, H = CFG.get("size", [1080, 1920]); FPS = CFG.get("fps", 30)
DUR = CFG["duration"]; NFR = int(round(DUR * FPS))

def eo(t): t = min(max(t, 0), 1); return 1 - (1 - t) ** 3
def eio(t):
    t = min(max(t, 0), 1); return 4 * t ** 3 if t < .5 else 1 - (-2 * t + 2) ** 3 / 2

# ---------------- sources ----------------
SRC = {}
for name, s in CFG["sources"].items():
    if s["type"] == "photo":
        SRC[name] = ImageOps.exif_transpose(Image.open(P(s["path"]))).convert("RGB")
    elif s["type"] == "scene":
        import importlib; SRC[name] = importlib.import_module(s.get("module", "village"))

class Vid:
    """sequential frame reader for a video source, starting at shot in-point."""
    def __init__(self, path, tin):
        self.size = None
        pr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:stream_side_data=rotation",
                             "-of", "json", path], capture_output=True, text=True)
        st = json.loads(pr.stdout)["streams"][0]; w, h = st["width"], st["height"]
        rot = abs(int(next((d.get("rotation", 0) for d in st.get("side_data_list", []) if "rotation" in d), 0)))
        self.w, self.h = (h, w) if rot in (90, 270) else (w, h)
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", str(tin), "-i", path, "-vf", f"fps={FPS}",
                                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        self.i = -1; self.last = None
    def get(self, idx):
        while self.i < idx:
            b = self.p.stdout.read(self.w * self.h * 3)
            if len(b) < self.w * self.h * 3: break
            self.last = Image.frombuffer("RGB", (self.w, self.h), b); self.i += 1
        return self.last

SHOTS = CFG["shots"]; readers = {}

def window(img, cam):
    cx, cy, w = cam; h = w * H / W; iw, ih = img.size
    w = min(w, iw); h = min(h, ih)
    cx = min(max(cx, w / 2), iw - w / 2); cy = min(max(cy, h / 2), ih - h / 2)
    return img.resize((W, H), Image.BICUBIC, box=(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), reducing_gap=2.0)

def shot_frame(si, t):
    sh = SHOTS[si]; s = CFG["sources"][sh["src"]]; a, b = sh["start"], sh["end"]
    k = eio((t - a) / (b - a))
    if s["type"] == "photo": img = SRC[sh["src"]]
    elif s["type"] == "scene": img = SRC[sh["src"]].scene(t - a)
    else:
        if si not in readers: readers[si] = Vid(P(s["path"]), sh.get("in", 0))
        img = readers[si].get(int(round((t - a) * FPS)))
    f0 = sh.get("from") or [img.width / 2, img.height / 2, img.width]; f1 = sh.get("to") or f0
    return window(img, [u + (v - u) * k for u, v in zip(f0, f1)])

# ---------------- look: film grade ----------------
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
r2 = ((xx - W / 2) / (W / 2)) ** 2 * 0.8 + ((yy - H / 2) / (H / 2)) ** 2
VIG = (1 - 0.38 * np.clip(r2, 0, 1.6) ** 1.3)[..., None].astype(np.float32)
RNG = np.random.default_rng(7)

def grade(x):
    lum = (0.299 * x[..., 0] + 0.587 * x[..., 1] + 0.114 * x[..., 2])[..., None]
    s = x * x * (3 - 2 * x); x = 0.65 * x + 0.35 * s                    # gentle S-curve
    x = 0.025 + x * 0.965                                               # lifted film blacks
    x = x + (1 - lum) * np.array([-0.012, 0.0, 0.022], np.float32)      # cool shadows
    x = x * (1 + lum * np.array([0.045, 0.012, -0.035], np.float32))    # warm highlights
    g = (0.299 * x[..., 0] + 0.587 * x[..., 1] + 0.114 * x[..., 2])[..., None]
    x = (g + (x - g) * 1.06) * VIG
    n = RNG.standard_normal((H // 2, W // 2), dtype=np.float32)
    return np.clip(x + np.repeat(np.repeat(n, 2, 0), 2, 1)[..., None] * 0.018, 0, 1)

FLASHES = CFG.get("flashes", [])   # [time, amount 0..1, decay seconds]
FADE_IN, FADE_OUT = CFG.get("fade_in", 0.45), CFG.get("fade_out", 0.28)
LEAK = CFG.get("light_leak")       # [start, end] warm light leak drifting across (e.g. the reveal)

def light(t, x):
    amt = 0.0
    for c, a, d in FLASHES:
        if c - 0.04 <= t < c + d:
            amt = max(amt, a * (1 - min(1, (t - c) / d)) ** 4 if t >= c else a * (t - c + 0.04) / 0.04)
    if amt > 0: x = x + (np.array([1.0, 0.95, 1.0], np.float32) - x) * amt
    if LEAK and LEAK[0] <= t < LEAK[1]:
        L = LEAK[1] - LEAK[0]; k = math.sin(math.pi * (t - LEAK[0]) / L) * 0.22; cx = W * (0.15 + 0.7 * (t - LEAK[0]) / L)
        leak = np.exp(-(((xx - cx) / (W * 0.45)) ** 2 + ((yy - H * 0.25) / (H * 0.4)) ** 2))[..., None]
        x = 1 - (1 - x) * (1 - leak * k * np.array([1.0, 0.75, 0.95], np.float32))
    f = 1.0
    if FADE_IN and t < FADE_IN: f = eo(t / FADE_IN)
    if FADE_OUT and t > DUR - FADE_OUT: f = max(0, (DUR - t) / FADE_OUT)
    return x * f

# ---------------- titles: trailer style (the look TEZZART approved) ----------------
FONT = P(CFG.get("font", "@skill/assets/fonts/BebasNeue.ttf"))
MAXW = CFG.get("title_max_width", 960)

def text_mask(txt, size, track):
    def draw(sz):
        f = ImageFont.truetype(FONT, sz); ws = [f.getlength(c) for c in txt]
        tw = int(sum(ws) + track * (len(txt) - 1)); asc, desc = f.getmetrics(); pad = 60
        m = Image.new("L", (tw + 2 * pad, asc + desc + 2 * pad), 0); d = ImageDraw.Draw(m); x = pad
        for c, w in zip(txt, ws): d.text((x, pad), c, font=f, fill=255); x += w + track
        bb = m.getbbox(); return m.crop((bb[0] - pad, bb[1] - pad, bb[2] + pad, bb[3] + pad)), bb[2] - bb[0]
    m, cw = draw(size)
    if cw > MAXW: m, _ = draw(int(size * MAXW / cw))
    return m

class Title:
    def __init__(self, txt, size, track=6, small=False):
        m = text_mask(txt, size, track); self.mask = m; w, h = m.size
        g = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
        top, mid, bot = (np.array([255, 255, 255]), np.array([236, 232, 246]), np.array([200, 196, 220])) if small else \
                        (np.array([255, 255, 255]), np.array([214, 218, 232]), np.array([128, 134, 160]))   # brushed silver
        fill = np.where(g < 0.5, top + (mid - top) * (g / 0.5), mid + (bot - mid) * ((g - 0.5) / 0.5))
        body = Image.fromarray(np.broadcast_to(fill, (h, w, 3)).astype(np.uint8), "RGB").convert("RGBA"); body.putalpha(m)
        shadow = Image.new("RGBA", m.size, (0, 0, 0, 0)); shadow.putalpha(m.filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.75)))
        glow = Image.new("RGBA", m.size, (210, 200, 255, 0)); glow.putalpha(m.filter(ImageFilter.GaussianBlur(26)).point(lambda v: int(v * 0.45)))
        self.img = Image.new("RGBA", m.size, (0, 0, 0, 0))
        self.img.alpha_composite(shadow, (0, 8)); self.img.alpha_composite(glow); self.img.alpha_composite(body)
        self.red = Image.new("RGBA", m.size, (255, 40, 70, 0)); self.red.putalpha(m.point(lambda v: int(v * 0.85)))
        self.cyan = Image.new("RGBA", m.size, (40, 210, 255, 0)); self.cyan.putalpha(m.point(lambda v: int(v * 0.85)))
        self.mnp = np.asarray(m, np.float32) / 255

def scaled(im, s): return im if abs(s - 1) < 1e-3 else im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BICUBIC)
def with_alpha(im, a):
    if a >= 0.999: return im
    im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * a))); return im

E, SLAMS = [], []   # E: (Title, in, out, cx, cy, kind); SLAMS: (time, strength) → camera shake
for T in CFG.get("titles", []):
    small = T["style"] == "rise"; track = T.get("track", 22 if small else 8)
    if "parts" in T:   # one line whose words land on separate hits, e.g. "MONKEY" then "D."
        parts = [Title(p["text"], T["size"], track, small) for p in T["parts"]]
        gap = int(T["size"] * 0.25); tot = sum(p.mask.width - 120 for p in parts) + gap * (len(parts) - 1)
        x = W / 2 - tot / 2
        for el, p in zip(parts, T["parts"]):
            cw = el.mask.width - 120
            E.append((el, p["in"], T["out"], x + cw / 2, T["y"], T["style"])); x += cw + gap
            if T["style"] == "slam": SLAMS.append((p["in"], T.get("strength", 0.6)))
    else:
        E.append((Title(T["text"], T["size"], track, small), T["in"], T["out"], W / 2, T["y"], T["style"]))
        if T["style"] == "slam": SLAMS.append((T["in"], T.get("strength", 1.0)))
END = CFG.get("end_card")
if END and END.get("text"):
    E.append((Title(END["text"], END.get("text_size", 58), END.get("track", 28), True), END["text_in"], DUR + 1, W / 2, END.get("text_y", 300), "rise"))

def draw_text(frame, t):
    for el, tin, tout, cx, cy, kind in E:
        if not (tin <= t < tout): continue
        dt = t - tin
        out = 1 - eo((t - (tout - 0.16)) / 0.16) if t > tout - 0.16 else 1.0
        ex = 1 + 0.08 * (1 - out)
        if kind == "slam":
            p = eo(dt / 0.18); s = (1.0 + 0.45 * (1 - p) + 0.03 * min(1, dt / 2.0)) * ex; a = min(1, dt / 0.05) * out
            img = scaled(el.img, s); blur = 7 * (1 - p) + 6 * (1 - out)
            if blur > 0.5: img = img.filter(ImageFilter.GaussianBlur(blur))
            sp = 22 * (1 - eo(dt / 0.32)); x0, y0 = int(cx - img.width / 2), int(cy - img.height / 2)
            if sp > 1:   # red/cyan split that settles
                frame.alpha_composite(with_alpha(scaled(el.red, s), 0.7 * a), (x0 + int(sp), y0))
                frame.alpha_composite(with_alpha(scaled(el.cyan, s), 0.7 * a), (x0 - int(sp), y0))
            if 0.15 < dt < 0.85:   # shine sweep after landing
                c = (dt - 0.15) / 0.7 * 1.6 - 0.3; mh, mw = el.mnp.shape
                gx = np.arange(mw, dtype=np.float32)[None, :] / mw; gy = np.arange(mh, dtype=np.float32)[:, None] / mh
                band = np.exp(-((gx - c + 0.25 * gy) / 0.06) ** 2) * el.mnp
                sh = Image.new("RGBA", (mw, mh), (255, 255, 255, 0)); sh.putalpha(Image.fromarray((band * 230).astype(np.uint8)))
                sh = scaled(sh, s)
                if sh.size == img.size: img = img.copy(); img.alpha_composite(sh)
            frame.alpha_composite(with_alpha(img, a), (x0, y0))
        else:   # rise: drift up out of a blur
            p = eo(dt / 0.45); s = (1.0 + 0.025 * min(1, dt / 2.5)) * ex
            img = scaled(el.img, s); blur = 8 * (1 - p) + 6 * (1 - out)
            if blur > 0.5: img = img.filter(ImageFilter.GaussianBlur(blur))
            frame.alpha_composite(with_alpha(img, p * out), (int(cx - img.width / 2), int(cy - img.height / 2 + 24 * (1 - p))))

def shake(t):
    dx = dy = 0.0
    for c, st in SLAMS:
        d = t - c
        if 0 <= d < 0.3:
            amp = 16 * st * math.exp(-d / 0.07); dx += amp * math.sin(d * 95); dy += amp * math.cos(d * 70)
    return dx, dy

CARDS = CFG.get("cards", [])   # [start, end] windows: letterbox bars + darkening behind titles
BAND = np.exp(-((yy - H * 0.5) / (H * 0.30)) ** 2)[..., None]; BAR_H = CFG.get("letterbox", 230)
def card_amt(t):
    d = 0.0
    for a, b in CARDS:
        if a <= t < b: d = max(d, (eo((t - a) / 0.35) if a > 0 else 1.0) * (1 - eo((t - (b - 0.2)) / 0.2) if t > b - 0.2 else 1))
    return d

# ---------------- frame ----------------
def render(t):
    act = [i for i, s in enumerate(SHOTS) if s["start"] <= t < s["end"]] or [len(SHOTS) - 1]
    if len(act) == 1: x = np.asarray(shot_frame(act[0], t), np.float32) / 255
    else:   # cross-dissolve over the overlap
        i, j = act[0], act[-1]; a0, b0 = SHOTS[j]["start"], SHOTS[i]["end"]; k = eio((t - a0) / (b0 - a0))
        x = (np.asarray(shot_frame(i, t), np.float32) * (1 - k) + np.asarray(shot_frame(j, t), np.float32) * k) / 255
    raw = x; x = grade(x)
    cur = SHOTS[act[-1]]
    if CFG["sources"][cur["src"]].get("grade", True) is False:   # e.g. the logo keeps its brand colours
        k = eio((t - cur["start"]) / 0.22); x = x * (1 - 0.8 * k) + raw * 0.8 * k
    d = card_amt(t)
    if d > 0: x = x * (1 - 0.55 * d * BAND)
    x = light(t, x)
    if d > 0 and int(BAR_H * d): bh = int(BAR_H * d); x[:bh] = 0; x[H - bh:] = 0
    fr = Image.fromarray((np.clip(x, 0, 1) * 255 + 0.5).astype(np.uint8)).convert("RGBA")
    draw_text(fr, t); fr = fr.convert("RGB")
    dx, dy = shake(t)
    if abs(dx) + abs(dy) > 0.5:
        m = 24; fr = fr.resize((W, H), Image.BICUBIC, box=(m + dx, m + dy, W - m + dx, H - m + dy))
    return fr

if PREVIEW:
    os.makedirs(OUT, exist_ok=True)
    for t in PREVIEW:
        readers.clear(); render(t).save(f"{OUT}/f_{t:05.2f}.jpg", quality=88)
    print("preview frames in", OUT); sys.exit()

audio = P(CFG["audio"]) if CFG.get("audio") else None
cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"]
if audio: cmd += ["-i", audio, "-map", "0:v", "-map", "1:a", "-c:a", "copy", "-shortest"]
cmd += ["-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT]
enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
for n in range(NFR):
    t = n / FPS
    for si in list(readers):
        if SHOTS[si]["end"] < t - 0.1: readers.pop(si).p.kill()
    enc.stdin.write(render(t).tobytes())
    if n % 90 == 0: print(f"frame {n}/{NFR}", flush=True)
enc.stdin.close(); enc.wait(); print("done", OUT)
