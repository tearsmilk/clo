import sys, os, numpy as np
sys.path.insert(0, os.path.expanduser('~/.claude/skills/minecraft-nexo-gui/scripts'))
from PIL import Image, ImageDraw
import pixelstyle
NAMES = {
 's1': ['carp','perch','roach','bream','herring','pike','trout','catfish','mackerel','zander','sturgeon','tuna','clownfish','pufferfish','golden_carp','swordfish'],
 's2': ['marsh_king','moon_fish','farm_legend','azure_trout','crystal_pike','kraken_calf','crucian','bleak','gudgeon','ruffe','goby','sardine','tench','chub','burbot','flounder'],
 's3': ['grayling','eel','salmon','barracuda','sea_bass','koi','beluga','mola','ice_pike','goldfish','sea_dragon','grouper'],
}
out = {}
for sheet, names in NAMES.items():
    im = Image.open(f'dl/{sheet}.png').convert('RGBA'); W, H = im.size; cw, ch = W // 4, H // 4
    a = np.array(im).astype(int); d = np.abs(a[...,0]-255) + a[...,1] + np.abs(a[...,2]-255)
    alpha = np.where(d > 140, 255, 0).astype(np.uint8)
    rgba = np.array(im); rgba[...,3] = alpha
    full = Image.fromarray(rgba)
    for i, n in enumerate(names):
        r, c = divmod(i, 4)
        cell = full.crop((c*cw, r*ch, (c+1)*cw, (r+1)*ch))
        # оставить главный силуэт + куски рядом с ним (блёстки), убрать обрезки соседних рыб
        from scipy import ndimage
        m = np.array(cell)[..., 3] > 0
        lab, nc = ndimage.label(ndimage.binary_dilation(m, iterations=3))
        if nc > 1:
            sizes = ndimage.sum(m, lab, range(1, nc + 1)); main = int(np.argmax(sizes)) + 1
            sl = ndimage.find_objects(lab)[main - 1]; y0, y1, x0, x1 = sl[0].start - 18, sl[0].stop + 18, sl[1].start - 18, sl[1].stop + 18
            keep = np.zeros_like(m)
            for k in range(1, nc + 1):
                ks = ndimage.find_objects(lab)[k - 1]
                if k == main or (ks[0].start >= y0 and ks[0].stop <= y1 and ks[1].start >= x0 and ks[1].stop <= x1): keep |= (lab == k)
            arr = np.array(cell); arr[..., 3] = np.where(keep & m, 255, 0); cell = Image.fromarray(arr)
        bb = cell.getbbox()
        if bb is None: print('EMPTY', n); continue
        sp = cell.crop(bb)
        ico = pixelstyle.fit(sp, 60) if hasattr(pixelstyle, 'fit') else sp.resize((30, 30))
        canvas = Image.new('RGBA', (64, 64), (0,0,0,0)); canvas.alpha_composite(ico, ((64-ico.width)//2, (64-ico.height)//2))
        canvas = pixelstyle.quantize(canvas, 48) if hasattr(pixelstyle, 'quantize') else canvas
        canvas.save(f'x64/{n}.png'); out[n] = canvas
# превью: сетка 8 колонок, 4x зум, подписи
names = list(out); cols = 8; rows = (len(names)+cols-1)//cols; S = 2; cellw, cellh = 64*S+8, 64*S+22
pv = Image.new("RGBA", (cols*cellw, rows*cellh), (28, 36, 52, 255)); dr = ImageDraw.Draw(pv)
for i, n in enumerate(names):
    r, c = divmod(i, cols); x, y = c*cellw+4, r*cellh+4
    pv.alpha_composite(out[n].resize((64*S, 64*S), Image.NEAREST), (x, y)); dr.text((x, y+64*S+4), n, fill=(220,220,220,255))
pv.save('preview64.png'); print(len(out), 'icons')
