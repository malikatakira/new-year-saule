"""Cut Santa and the sack from the beige sheet; make a 'smiling' Santa by flipping the mouth."""
import sys, numpy as np, cv2
from PIL import Image
from scipy import ndimage as ndi
SRC, OUT = sys.argv[1], sys.argv[2]
rgb = np.array(Image.open(SRC).convert('RGB')).astype(np.int16)
bg = rgb[5, 5]
near = np.abs(rgb - bg).sum(2) < 40
shadow = (np.abs(rgb[..., 0] - rgb[..., 1]) < 14) & (np.abs(rgb[..., 1] - rgb[..., 2]) < 18) & (rgb.sum(2) > 520)
lab, _ = ndi.label(near | shadow)
border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
alpha = cv2.GaussianBlur((~np.isin(lab, list(border))).astype(np.uint8) * 255, (3, 3), 0)
img = rgb.astype(np.uint8)

def save(arr, a, box, name):
    x0, y0, x1, y1 = box
    out = np.dstack([arr, a])[y0:y1, x0:x1].copy()
    out[out[..., 3] == 0, :3] = 0
    Image.fromarray(out).save(f'{OUT}/{name}.webp', quality=90, method=6)

SANTA = (100, 100, 540, 670); SACK = (545, 460, 885, 665)
a1 = alpha.copy(); a1[:, 540:] = 0
save(img, a1, SANTA, 'santa_sad')
a2 = alpha.copy(); a2[:, :545] = 0
save(img, a2, SACK, 'sack')

# smile: mouth pixels below the moustache, flipped upside down
x0, y0, x1, y1 = [int(v) for v in sys.argv[3:7]]
box = img[y0:y1, x0:x1].astype(np.int16)
red = (box[..., 0] - box[..., 1] > 50)
lab3, n3 = ndi.label(red)
sizes = ndi.sum(red, lab3, range(1, n3 + 1))
red = lab3 == int(np.argmax(sizes)) + 1
m = ndi.binary_fill_holes(ndi.binary_dilation(red, iterations=3))
happy = img.copy()
region = happy[y0:y1, x0:x1]
ys, xs = np.nonzero(m)
cx, top = x0 + xs.mean(), y0 + ys.min()
region[ndi.binary_dilation(m, iterations=2)] = (250, 248, 244)
# draw an open smile in the same style (black outline, dark red mouth, pink tongue), 4x supersampled
from PIL import ImageDraw
K = 4; w, h = 46, 24
pad = 6
lay = Image.new('RGBA', ((w + 2 * pad) * K, (h + 2 * pad) * K), (0, 0, 0, 0))
d = ImageDraw.Draw(lay)
bb = [pad * K, (pad - h) * K, (pad + w) * K, (pad + h) * K]          # ellipse; keep lower half
d.pieslice(bb, 0, 180, fill=(30, 14, 14, 255))
inner = [bb[0] + 3.2 * K, bb[1] + 3.2 * K, bb[2] - 3.2 * K, bb[3] - 3.2 * K]
d.pieslice(inner, 0, 180, fill=(140, 28, 36, 255))
d.ellipse([(pad + w * .3) * K, (pad + h * .42) * K, (pad + w * .7) * K, (pad + h * .86) * K], fill=(236, 110, 110, 255))
d.pieslice(bb, 0, 180, outline=(30, 14, 14, 255), width=int(3.2 * K))
lay = lay.resize((w + 2 * pad, h + 2 * pad), Image.LANCZOS)
hp = Image.fromarray(happy).convert('RGBA')
hp.alpha_composite(lay, (int(cx - w / 2 - pad), int(top + 2 - pad)))
happy = np.array(hp.convert('RGB'))
save(happy, a1, SANTA, 'santa_happy')
Image.fromarray(happy[220:380, 230:410]).resize((540, 480)).save(f'{OUT}/santa_happy_face.png')
