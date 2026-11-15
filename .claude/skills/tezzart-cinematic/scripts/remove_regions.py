"""Remove stickers / captions / watermarks from a photo by inpainting boxes.
usage: python3 -I remove_regions.py <in.jpg> <out.jpg> x0,y0,x1,y1 [x0,y0,x1,y1 ...] [--text]
  boxes are in the photo's upright pixel coordinates (EXIF rotation applied).
  --text : inside each box, only mask very bright/very dark pixels (thin caption text on a plain wall).
Works great on plain backgrounds. For big stickers over structured areas (lines, edges), clone
texture from next to the area and redraw straight outlines instead (see SKILL.md, "Cleaning photos").
needs: pip install opencv-python-headless"""
import sys, numpy as np, cv2
from PIL import Image, ImageOps
src, out = sys.argv[1], sys.argv[2]
text_only = "--text" in sys.argv
boxes = [tuple(int(v) for v in b.split(",")) for b in sys.argv[3:] if b != "--text"]
a = np.asarray(ImageOps.exif_transpose(Image.open(src)).convert("RGB")).copy()
m = np.zeros(a.shape[:2], np.uint8)
for x0, y0, x1, y1 in boxes:
    if text_only:
        v = cv2.cvtColor(a[y0:y1, x0:x1], cv2.COLOR_RGB2HSV)[..., 2]
        m[y0:y1, x0:x1][(v > 200) | (v < 60)] = 255
    else:
        m[y0:y1, x0:x1] = 255
m = cv2.dilate(m, np.ones((9, 9), np.uint8))
a = cv2.inpaint(a, m, 9, cv2.INPAINT_TELEA)
Image.fromarray(a).save(out, quality=95); print("saved", out)
