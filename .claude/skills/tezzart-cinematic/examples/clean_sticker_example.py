import sys, numpy as np, cv2
from PIL import Image, ImageOps
src, out = sys.argv[1], sys.argv[2]
a = np.asarray(ImageOps.exif_transpose(Image.open(src)).convert("RGB")).astype(np.float32)
rng = np.random.default_rng(3)
X0, X1, Y0, Y1 = 365, 592, 1862, 2200
SH = 240   # source columns for clones: x + SH
bot = lambda x: 1990 + 0.045 * (x - 570)          # mural bottom outline (measured)
col = lambda x: 1911.5 + 0.233 * (570 - x)        # collarbone line (measured slope)
# skin: per-column colour from just above the sticker, plus real paint texture from a clean skin patch
top = a[Y0 - 16:Y0 - 2, X0:X1].mean(0)                          # (w,3)
patch = a[1925:1975, 600:780].copy(); tex = patch - patch.mean((0, 1))
src_img = a.copy()
for i, x in enumerate(range(X0, X1)):
    yb = int(round(bot(x))); xs = x + SH; dy = int(round(bot(xs) - bot(x)))
    for y in range(Y0, Y1):
        if y < yb - 6:
            a[y, x] = top[i] + tex[(y - Y0) % 50, i if i < 180 else 359 - i] * 0.8
        else:   # real bottom outline + wall, cloned with the outline aligned to its slope
            a[y, x] = src_img[min(y + dy, a.shape[0] - 1), xs]
# clear any shirt-red picked up next to the outline
for i, x in enumerate(range(X0, X1)):
    for y in range(int(bot(x)) - 16, int(bot(x)) - 3):
        r, g, b = a[y, x]
        if r > 110 and g < 70 and r - g > 60: a[y, x] = top[i]
# outlines, drawn antialiased on a mask, then darkened
ink = np.array([38, 30, 30], np.float32)
m = np.zeros(a.shape[:2], np.float32)
for x in range(440, X1 + 4):   # collarbone, tapering as it fades out to the left
    t = (x - 440) / (X1 - 440); th = 1 + 5 * t
    cv2.circle(m, (x * 16, int(col(x) * 16)), int(th * 8), 1.0, -1, cv2.LINE_AA, shift=4)
m = cv2.GaussianBlur(m, (3, 3), 0)[..., None]
a = a * (1 - m) + ink * m
# granite door-frame column: clone from above
h = Y1 - Y0; a[Y0:Y1, 255:X0] = a[Y0 - h:Y0, 255:X0]
a = np.clip(a, 0, 255).astype(np.uint8)
# soften the seams
sm = np.zeros(a.shape[:2], np.uint8)
sm[Y0 - 2:Y0 + 2, 255:X1] = 255; sm[Y0:Y1, X0 - 2:X0 + 2] = 255; sm[Y0:int(bot(X1)) - 8, X1 - 2:X1 + 2] = 255
for x in range(X0, X1): sm[int(bot(x)) - 8:int(bot(x)) - 4, x] = 255
a = cv2.inpaint(a, sm, 4, cv2.INPAINT_TELEA)
# remove "Wednesday" caption from the plain wall
hsv = cv2.cvtColor(a, cv2.COLOR_RGB2HSV); m2 = np.zeros(a.shape[:2], np.uint8)
reg = (slice(2270, 2410), slice(690, 1060)); v = hsv[reg][..., 2]
m2[reg][(v > 200) | (v < 60)] = 255; m2 = cv2.dilate(m2, np.ones((9, 9), np.uint8))
a = cv2.inpaint(a, m2, 9, cv2.INPAINT_TELEA)
Image.fromarray(a).save(out, quality=95)
