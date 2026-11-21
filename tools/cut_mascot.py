"""Split the SHU mascot (purple alien) into body / eyes layers at 2x, mouth painted over."""
import sys, json, numpy as np, cv2
from PIL import Image
from scipy import ndimage as ndi
SRC, OUT = sys.argv[1], sys.argv[2]
K = 2
im = Image.open(SRC).convert('RGBA')
im = im.resize((im.width * K, im.height * K), Image.LANCZOS)
a = np.array(im).astype(np.int16)
rgb, al = a[..., :3], a[..., 3]
H, W = al.shape
dark = (rgb.sum(2) < 200) & (al > 200)
lab, n = ndi.label(dark)
sizes = ndi.sum(dark, lab, range(1, n + 1))
eyes = np.zeros((H, W), bool)
for idx in np.argsort(sizes)[-2:]:
    eyes |= lab == idx + 1
# grow each eye over its darker rim (anything clearly darker than skin next to the eye)
rim = (rgb.sum(2) < 420) & (al > 200)
eyes = ndi.binary_fill_holes(ndi.binary_dilation(eyes, iterations=4))
grow = ndi.binary_dilation(eyes, iterations=10) & rim
eyes = ndi.binary_fill_holes(eyes | grow)
eyes = ndi.binary_dilation(eyes, iterations=3)
# mouth: darker-than-skin pixels in a box under the eyes
y0, y1, x0, x1 = 113 * K, 131 * K, 104 * K, 140 * K
box = rgb[y0:y1, x0:x1].astype(float)
lum = box.mean(2)
m = lum < np.percentile(lum, 70) - 18
m = ndi.binary_opening(m, iterations=1)
mouth = np.zeros((H, W), bool); mouth[y0:y1, x0:x1] = m
mouth = ndi.binary_dilation(mouth, iterations=3)
paint = ((eyes | mouth) & (al > 0)).astype(np.uint8) * 255
paint = cv2.dilate(paint, np.ones((5, 5), np.uint8))
img8 = rgb.astype(np.uint8)
body = cv2.inpaint(img8[..., ::-1].copy(), paint, 12, cv2.INPAINT_TELEA)[..., ::-1]
alpha8 = al.astype(np.uint8)
def save(arr, alpha, name):
    o = np.dstack([arr, alpha]).astype(np.uint8); o[o[..., 3] == 0, :3] = 0
    Image.fromarray(o).save(f'{OUT}/{name}.webp', quality=92, method=6)
save(body, alpha8, 'mascot_body')
ea = cv2.GaussianBlur((eyes * 255).astype(np.uint8), (3, 3), 0)
save(img8, np.minimum(ea, alpha8), 'mascot_eyes')
save(img8, alpha8, 'mascot_full')
ys, xs = np.nonzero(mouth)
el, er = [], []
lab2, _ = ndi.label(eyes)
cs = ndi.center_of_mass(eyes, lab2, [1, 2])
meta = dict(W=W, H=H, mouth_cx=float(xs.mean()), mouth_top=float(ys.min()), mouth_w=float(xs.max() - xs.min()),
            eyes=[[round(c[1], 1), round(c[0], 1)] for c in sorted(cs, key=lambda c: c[1])])
print(json.dumps(meta))
Image.fromarray(np.dstack([body, alpha8]).astype(np.uint8)).crop((100, 100, 380, 300)).resize((560, 400)).save(f'{OUT}/chk_body.png')
