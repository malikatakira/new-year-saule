"""Cut the two heroes out of the beige sheet and split each into layers:
body (eyes + mouth painted over with fur), eyes (transparent PNG).
Coordinates are in the 1024x765 source image."""
import sys, json
import numpy as np, cv2
from PIL import Image
from scipy import ndimage as ndi

SRC, OUT = sys.argv[1], sys.argv[2]
rgb = np.array(Image.open(SRC).convert('RGB')).astype(np.int16)
H, W, _ = rgb.shape
bg = np.array([245, 239, 230])

# background = pixels close to beige OR soft grey shadow, connected to the border
near = np.abs(rgb - bg).sum(2) < 40
shadow = (np.abs(rgb[..., 0] - rgb[..., 1]) < 14) & (np.abs(rgb[..., 1] - rgb[..., 2]) < 18) & (rgb.sum(2) > 520)
cand = near | shadow
lab, _ = ndi.label(cand)
border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
bgmask = np.isin(lab, list(border))
alpha = (~bgmask).astype(np.uint8) * 255
alpha = cv2.GaussianBlur(alpha, (3, 3), 0)

HEROES = {
    'red':   dict(box=(80, 100, 520, 680), eyes=[(222, 293, 298, 356), (322, 291, 400, 355)],
                  mouth=(270, 360, 354, 404)),
    'green': dict(box=(520, 110, 960, 680), eyes=[(650, 290, 718, 356), (739, 290, 806, 356)],
                  mouth=(678, 356, 782, 400)),
}

img8 = rgb.astype(np.uint8)
meta = {}
for name, h in HEROES.items():
    feat = np.zeros((H, W), bool)
    # mouth: anything not fur-coloured inside the box, holes filled, grown a bit
    x0, y0, x1, y1 = h['mouth']
    box = rgb[y0:y1, x0:x1]
    r, g, b = box[..., 0], box[..., 1], box[..., 2]
    if name == 'red':
        fur = (r > 170) & (g < 90) & (b < 100)
    else:
        fur = (g > 120) & (r < 150) & (b < 90)
    m = ~fur
    m = ndi.binary_opening(m, iterations=1)
    m = ndi.binary_fill_holes(ndi.binary_closing(m, iterations=3))
    feat[y0:y1, x0:x1] |= m
    mouth_mask = ndi.binary_dilation(feat, iterations=4)

    eye_mask = np.zeros((H, W), bool)
    for (ex0, ey0, ex1, ey1) in h['eyes']:
        yy, xx = np.mgrid[0:H, 0:W]
        cx, cy, rx, ry = (ex0 + ex1) / 2, (ey0 + ey1) / 2, (ex1 - ex0) / 2 + 6, (ey1 - ey0) / 2 + 5
        eye_mask |= ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1
    # tighten to non-fur + fill, so eyelashes come along but not too much fur
    eb = eye_mask.copy()
    rr, gg, bb = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    furall = ((rr > 170) & (gg < 90) & (bb < 100)) if name == 'red' else ((gg > 120) & (rr < 150) & (bb < 90))
    eye_feat = ndi.binary_fill_holes(eb & ~furall)
    eye_feat = ndi.binary_dilation(eye_feat, iterations=2) & eb

    # protect the nose: orange blob + its outline stay in the body layer
    rr_, gg_, bb_ = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    orange = (rr_ > 200) & (gg_ > 70) & (gg_ < 170) & (bb_ < 90)
    mx0, my0, mx1, my1 = h['mouth']
    win = np.zeros((H, W), bool); win[my0 - 30:my0 + 10, mx0:mx1] = True
    nlab, _ = ndi.label(orange & win)
    sizes = ndi.sum(np.ones_like(nlab), nlab, range(1, nlab.max() + 1))
    nose = nlab == (int(np.argmax(sizes)) + 1)
    nose = ndi.binary_fill_holes(ndi.binary_dilation(nose, iterations=4))
    eye_feat &= ~nose
    mouth_mask &= ~nose
    paint = ((mouth_mask | ndi.binary_dilation(eye_feat, iterations=5)) & ~nose).astype(np.uint8) * 255
    # fill nose with fur colour while inpainting so its dark outline does not bleed, then restore it
    furpx = img8[(furall) & ndi.binary_dilation(nose, iterations=40)]
    src = img8.copy(); src[ndi.binary_dilation(nose, iterations=2)] = np.median(furpx, 0).astype(np.uint8)
    body = cv2.inpaint(src[..., ::-1].copy(), paint, 9, cv2.INPAINT_TELEA)[..., ::-1].copy()
    body[nose] = img8[nose]
    # put some fur grain back so the patch is not a smooth blob
    rng = np.random.default_rng(1)
    noise = rng.normal(0, 9, (H, W, 1))
    noise = cv2.GaussianBlur(noise.astype(np.float32), (3, 3), 0)[..., None]
    pm = (paint > 0)[..., None]
    body = np.where(pm, np.clip(body.astype(np.float32) + noise, 0, 255), body).astype(np.uint8)

    X0, Y0, X1, Y1 = h['box']
    a = alpha.copy()
    # keep only this hero's pixels (split the sheet down the middle)
    if name == 'red':
        a[:, 512:] = 0
    else:
        a[:, :512] = 0
    body_rgba = np.dstack([body, a])[Y0:Y1, X0:X1]
    Image.fromarray(body_rgba).save(f'{OUT}/{name}_body.png')
    Image.fromarray(np.dstack([img8, a])[Y0:Y1, X0:X1]).save(f'{OUT}/{name}_full.png')

    ea = np.where(eye_feat, 255, 0).astype(np.uint8)
    ea = cv2.GaussianBlur(ea, (3, 3), 0)
    eyes_rgba = np.dstack([img8, ea])[Y0:Y1, X0:X1]
    Image.fromarray(eyes_rgba).save(f'{OUT}/{name}_eyes.png')

    ys, xs = np.nonzero(feat)
    nys, nxs = np.nonzero(nose)
    meta[name] = dict(
        w=X1 - X0, h=Y1 - Y0,
        mouth=dict(cx=float(xs.mean() - X0), cy=float(ys.mean() - Y0),
                   w=float(xs.max() - xs.min()), h=float(ys.max() - ys.min())),
        nose=dict(cx=float(nxs.mean() - X0), cy=float(nys.mean() - Y0), bottom=float(nys.max() - Y0)),
        eyes=[dict(cx=(e[0] + e[2]) / 2 - X0, cy=(e[1] + e[3]) / 2 - Y0) for e in h['eyes']],
    )
json.dump(meta, open(f'{OUT}/heroes.json', 'w'), indent=1)
print(json.dumps(meta, indent=1))
