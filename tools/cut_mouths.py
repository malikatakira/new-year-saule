import sys, json, numpy as np
from PIL import Image
from scipy import ndimage as ndi
SRC, OUT = sys.argv[1], sys.argv[2]
a = np.array(Image.open(SRC).convert('RGB')).astype(np.int16)
# crop box (no nose, no captions) + nose centre-x / bottom-y from the sheet
M = {
  'open':   dict(box=(135, 168, 422, 324), nose=(280, 167)),
  'o':      dict(box=(695, 158, 812, 309), nose=(754, 157)),
  'i':      dict(box=(95, 406, 465, 496),  nose=(284, 405)),
  'closed': dict(box=(138, 603, 430, 672), nose=(284, 602)),
}
SC = 0.5
meta = {}
for k, m in M.items():
    x0, y0, x1, y1 = m['box']
    c = a[y0:y1, x0:x1]
    white = c.min(2) > 225
    lab, _ = ndi.label(white)
    edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    bg = np.isin(lab, list(edge))
    # drop any stray orange nose remains
    orange = (c[..., 0] > 200) & (c[..., 1] > 80) & (c[..., 1] < 170) & (c[..., 2] < 90)
    alpha = ~bg & ~ndi.binary_dilation(orange, iterations=3)
    # thicken outlines so they match the hero line weight after downscaling
    dark = (c.max(2) < 70) & alpha
    thick = ndi.binary_dilation(dark, iterations=3)
    rgb = c.copy(); rgb[thick] = (25, 12, 14)
    alpha = alpha | thick
    alpha = ndi.binary_fill_holes(alpha) & (alpha | ~bg)
    # drop the little chin mark under the mouth
    lab2, n2 = ndi.label(alpha)
    sizes = ndi.sum(alpha, lab2, range(1, n2 + 1))
    main = int(np.argmax(sizes)) + 1
    mb = ndi.find_objects(lab2)[main - 1][0].stop
    for j, sl in enumerate(ndi.find_objects(lab2)):
        if sl[0].start >= mb - 2: alpha[lab2 == j + 1] = False
    img = Image.fromarray(np.dstack([rgb.astype(np.uint8), (alpha * 255).astype(np.uint8)]))
    w, h = img.size
    img = img.resize((round(w * SC), round(h * SC)), Image.LANCZOS)
    img.save(f'{OUT}/mouth_{k}.png')
    meta[k] = dict(w=img.size[0], h=img.size[1], ax=(m['nose'][0] - x0) * SC, ay=(m['nose'][1] - y0) * SC)
json.dump(meta, open(f'{OUT}/mouths.json', 'w'), indent=1)
print(meta)
