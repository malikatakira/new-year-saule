"""Cut Santa faces and sack stages from the white sheet; put faces on the full-body Santa."""
import sys, numpy as np, cv2
from PIL import Image
from scipy import ndimage as ndi
SHEET, BODY_SRC, OUT = sys.argv[1:4]
a = np.array(Image.open(SHEET).convert('RGB')).astype(np.int16)
def cut(box, largest=False):
    x0, y0, x1, y1 = box
    c = a[y0 - 4:y1 + 4, x0 - 4:x1 + 4]
    near = c.min(2) > 238
    lab, _ = ndi.label(near)
    edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    fg = ~np.isin(lab, list(edge))
    if largest:
        l2, n2 = ndi.label(fg); sz = ndi.sum(fg, l2, range(1, n2 + 1)); fg = l2 == int(np.argmax(sz)) + 1
    al = cv2.GaussianBlur(fg.astype(np.uint8) * 255, (3, 3), 0)
    im = np.dstack([c.astype(np.uint8), al]); im[al == 0, :3] = 0
    return Image.fromarray(im)
SACKS = {'sack0': (36, 376, 291, 534), 'sack1': (346, 373, 737, 593), 'sack2': (25, 771, 285, 964),
         'sack3': (290, 719, 505, 964), 'sack4': (516, 735, 732, 964)}
for k, b in SACKS.items():
    cut(b).save(f'{OUT}/{k}.webp', quality=90, method=6)
FACES = {'joy': (18, 73, 202, 282), 'wow': (199, 73, 384, 281)}
body = Image.open(BODY_SRC).convert('RGBA')
ba = np.array(body); ba[:205, :, 3] = 0
body = Image.fromarray(ba)
sx, sy, sc = [float(v) for v in sys.argv[4:7]]
for k, b in FACES.items():
    f = cut(b, True); f = f.resize((round(f.width * sc), round(f.height * sc)), Image.LANCZOS)
    out = body.copy(); out.alpha_composite(f, (round(sx), round(sy)))
    out.save(f'{OUT}/santa_{k}.webp', quality=90, method=6)
