"""Рыба на моделях FreshFood: геометрия и текстура берутся из пака (cod_3d — для всех, pufferfish_3d — для шарообразных),
меняются только цвета: тело → цвет вида, плавники/хвост/шипы → цвет плавников вида. Светлота пикселей FreshFood сохраняется,
поэтому остаются их крупные «пиксельные» границы и 8–10 цветов на рыбу.
Запуск: python3 fish_models_ff.py FRESHFOOD_DIR(cod_3d.json/png, pufferfish_3d.json/png) OUT_MODELS OUT_TEXTURES [preview.png]
Палитры видов — PAL из fish_models3d.py (спина, бок, брюхо, плавники); используются бок и плавники."""
import sys, os, json, re, colorsys, math
from PIL import Image, ImageDraw

FF, OUT_M, OUT_T = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(OUT_M, exist_ok=True); os.makedirs(OUT_T, exist_ok=True)
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, 'fish_models3d.py'), encoding='utf-8').read()
PAL = eval(re.search(r'PAL = (\{.*?\n\})', src, re.S).group(1))
ROUND = {'pufferfish', 'mola', 'moon_fish', 'kraken_calf'}   # на модели иглобрюха

def hls(c): return colorsys.rgb_to_hls(*[v / 255 for v in c])
def rgb(h, l, s): return tuple(int(round(v * 255)) for v in colorsys.hls_to_rgb(h, max(0, min(1, l)), max(0, min(1, s))))

def recolor(im, is_fin, body, fin):
    """каждый пиксель: берём светлоту исходника, оттенок и насыщенность — от цвета вида (тело или плавник)."""
    out = im.copy(); px = im.load(); po = out.load()
    # средняя светлота тела в исходнике — чтобы цвет вида лёг «в середину» его диапазона
    ls = [hls(px[x, y][:3])[1] for y in range(im.height) for x in range(im.width) if px[x, y][3] > 0 and not is_fin(x, y)]
    lm = sum(ls) / len(ls)
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if a == 0: continue
            h, l, s = hls((r, g, b))
            if l < 0.2 or (s < 0.15 and l > 0.95): continue        # глаз / чисто-белое — как есть
            th, tl, ts = hls(fin if is_fin(x, y) else body)
            nl = tl + (l - lm) * 0.9
            po[x, y] = rgb(th, nl, ts * (0.85 if l > 0.8 else 1.0)) + (a,)
    return out

cod = Image.open(f'{FF}/cod_3d.png').convert('RGBA'); cod_m = json.load(open(f'{FF}/cod_3d.json'))
puf = Image.open(f'{FF}/pufferfish_3d.png').convert('RGBA'); puf_m = json.load(open(f'{FF}/pufferfish_3d.json'))
cod_fin = lambda x, y: x >= 24                                           # right/left fin, fin_back, tail
puf_fin = lambda x, y: y >= 17 or (x >= 26 and y <= 5)                   # шипы и плавники

ids = sorted(k for k in PAL)
made = []
for fid in ids:
    back, side, belly, fin = PAL[fid]
    body = side
    if fid in ROUND: tex, m, isf = puf, puf_m, puf_fin
    else: tex, m, isf = cod, cod_m, cod_fin
    recolor(tex, isf, body, fin).save(f'{OUT_T}/{fid}.png')
    model = dict(m)
    model['credit'] = 'FreshFood ' + ('pufferfish_3d' if fid in ROUND else 'cod_3d') + ', перекраска ZenFishing fish_models_ff.py'
    model['textures'] = {'0': f'zenfishing:item/fish3d/{fid}', 'particle': f'zenfishing:item/fish3d/{fid}'}
    json.dump(model, open(f'{OUT_M}/{fid}.json', 'w'), separators=(',', ':'))
    made.append(fid)
print('models:', len(made))

if len(sys.argv) > 4:
    import numpy as np
    def render(fid, S=16, rot_y=45, rot_x=30):
        m = json.load(open(f'{OUT_M}/{fid}.json')); tex = Image.open(f'{OUT_T}/{fid}.png').convert('RGBA')
        ay, ax = math.radians(rot_y), math.radians(rot_x)
        def rotp(pt, rot):
            if not rot: return pt
            ox, oy, oz = rot['origin']; a = math.radians(rot['angle']); x, y, z = pt[0] - ox, pt[1] - oy, pt[2] - oz
            if rot['axis'] == 'z': x, y = x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)
            elif rot['axis'] == 'y': x, z = x * math.cos(a) + z * math.sin(a), -x * math.sin(a) + z * math.cos(a)
            else: y, z = y * math.cos(a) - z * math.sin(a), y * math.sin(a) + z * math.cos(a)
            return (x + ox, y + oy, z + oz)
        def proj(x, y, z):
            x, y, z = x - 8, y - 4, z - 8
            x, z = x * math.cos(ay) - z * math.sin(ay), x * math.sin(ay) + z * math.cos(ay)
            y, z = y * math.cos(ax) - z * math.sin(ax), y * math.sin(ax) + z * math.cos(ax)
            return (x * S + 160, -y * S + 160, z)
        img = Image.new('RGBA', (320, 320), (0, 0, 0, 0)); faces = []
        for e in m['elements']:
            (x0, y0, z0), (x1, y1, z1) = e['from'], e['to']; rot = e.get('rotation')
            P = {'a': (x0, y0, z0), 'b': (x1, y0, z0), 'c': (x1, y1, z0), 'd': (x0, y1, z0), 'e': (x0, y0, z1), 'f': (x1, y0, z1), 'g': (x1, y1, z1), 'h': (x0, y1, z1)}
            order = {'north': 'cbad', 'south': 'hgfe', 'up': 'hgcd', 'down': 'abfe', 'east': 'gfbc', 'west': 'dhea'}
            shade_k = {'north': 0.8, 'south': 0.8, 'up': 1.0, 'down': 0.6, 'east': 0.7, 'west': 0.7}
            for name, quad in order.items():
                if name not in e['faces']: continue
                u0, v0, u1, v1 = [v * 2 for v in e['faces'][name]['uv']]
                pts = [proj(*rotp(P[k], rot)) for k in quad]; depth = sum(p[2] for p in pts) / 4
                faces.append((depth, pts, (u0, v0, u1, v1), shade_k[name]))
        for _, pts, (u0, v0, u1, v1), k in sorted(faces, key=lambda t: -t[0]):
            (ax0, ay0, _), (bx, by, _), (cx, cy, _), (dx, dy, _) = pts
            ex, ey = bx - ax0, by - ay0; fx, fy = dx - ax0, dy - ay0; det = ex * fy - ey * fx
            if abs(det) < 1e-6: continue
            inv = np.array([[fy, -fx], [-ey, ex]]) / det; du, dv = (u1 - u0), (v1 - v0)
            A = [inv[0][0] * du, inv[0][1] * du, u0 - (inv[0][0] * ax0 + inv[0][1] * ay0) * du,
                 inv[1][0] * dv, inv[1][1] * dv, v0 - (inv[1][0] * ax0 + inv[1][1] * ay0) * dv]
            face = tex.transform((320, 320), Image.AFFINE, A, resample=Image.NEAREST)
            mask = Image.new('L', (320, 320), 0); ImageDraw.Draw(mask).polygon([(p[0], p[1]) for p in pts], fill=255)
            if k != 1.0: face = Image.alpha_composite(face, Image.new('RGBA', (320, 320), (0, 0, 0, int(255 * (1 - k)))))
            img.paste(face, (0, 0), mask)
        return img
    close = ['carp', 'perch', 'pike', 'clownfish', 'goldfish', 'tuna', 'pufferfish', 'koi']
    cl = Image.new('RGBA', (4 * 320, 2 * 320), (54, 72, 92, 255)); dcl = ImageDraw.Draw(cl)
    for i, fid in enumerate(close):
        cl.alpha_composite(render(fid), ((i % 4) * 320, (i // 4) * 320)); dcl.text(((i % 4) * 320 + 8, (i // 4) * 320 + 8), fid, fill=(255, 255, 255, 255))
    cl.save(sys.argv[4].replace('.png', '_close.png'))
    cols = 8; rows = (len(made) + cols - 1) // cols; T = 200
    pv = Image.new('RGBA', (cols * T, rows * T), (54, 72, 92, 255)); dr = ImageDraw.Draw(pv)
    for i, fid in enumerate(made):
        pv.alpha_composite(render(fid).resize((T, T), Image.LANCZOS), ((i % cols) * T, (i // cols) * T)); dr.text(((i % cols) * T + 6, (i // cols) * T + 6), fid, fill=(255, 255, 255, 255))
    pv.save(sys.argv[4]); print('preview ok')
