"""3D-модель «Книга квестов»: раскрытая книга — две обложки под углом, стопки страниц, корешок, закладка.
Текстура 64x64 рисуется процедурно (оранжево-красная кожа с золотым тиснением, кремовые страницы со строчками).
Запуск: python3 quest_book_model.py OUT_MODEL.json OUT_TEXTURE.png [preview.png]"""
import sys, json, math
from PIL import Image, ImageDraw
OUT_M, OUT_T = sys.argv[1], sys.argv[2]

# ── текстура ──
t = Image.new('RGBA', (64, 64), (0, 0, 0, 0)); d = ImageDraw.Draw(t); p = t.load()
RED, RED_D, RED_L, GOLD, GOLD_D = (196, 58, 30), (140, 36, 20), (224, 96, 48), (240, 188, 70), (170, 120, 30)
CREAM, CREAM_D, LINE = (244, 232, 200), (222, 206, 170), (150, 130, 100)
# обложка снаружи 32x24 (0,0): кожа с зерном, золотая рамка и эмблема-свиток
for y in range(24):
    for x in range(32):
        c = RED if (x * 7 + y * 3) % 5 else RED_D
        if (x + y) % 9 == 0: c = RED_L
        p[x, y] = c + (255,)
d.rectangle((1, 1, 30, 22), outline=GOLD + (255,)); d.rectangle((3, 3, 28, 20), outline=GOLD_D + (255,))
d.rectangle((12, 8, 19, 15), outline=GOLD + (255,)); d.line((14, 10, 17, 10), fill=GOLD + (255,)); d.line((14, 12, 17, 12), fill=GOLD + (255,)); d.line((14, 14, 16, 14), fill=GOLD + (255,))
# обложка изнутри 32x24 (32,0): тёмно-красная
for y in range(24):
    for x in range(32, 64): p[x, y] = (RED_D if (x + y) % 2 else (120, 30, 16)) + (255,)
# страницы сверху 32x24 (0,24): кремовые со строчками
for y in range(24, 48):
    for x in range(32): p[x, y] = (CREAM if (x + y) % 7 else CREAM_D) + (255,)
for y in range(27, 46, 3): d.line((4, y, 27, y), fill=LINE + (255,))
d.rectangle((0, 24, 31, 47), outline=CREAM_D + (255,))
# торец страниц 32x6 (32,24): полоски
for y in range(24, 30):
    for x in range(32, 64): p[x, y] = (CREAM_D if y % 2 else CREAM) + (255,)
# корешок 8x24 (32,32): золотые полосы на красном
for y in range(32, 56):
    for x in range(32, 40): p[x, y] = (RED_D if y % 8 < 6 else GOLD) + (255,)
# закладка 4x24 (40,32)
for y in range(32, 56):
    for x in range(40, 44): p[x, y] = ((230, 180, 60) if x % 2 else (200, 150, 40)) + (255,)
t.save(OUT_T)

def uv(x0, y0, x1, y1, flip=False):
    r = [x0 / 4, y0 / 4, x1 / 4, y1 / 4]
    return [r[2], r[1], r[0], r[3]] if flip else r
COVER_OUT, COVER_IN, PAGES, PAGE_EDGE, SPINE, MARK = (0, 0, 32, 24), (32, 0, 64, 24), (0, 24, 32, 48), (32, 24, 64, 30), (32, 32, 40, 56), (40, 32, 44, 56)

def box(fr, to, up_, down_, sides, ends=None, rot=None):
    ends = ends or sides
    e = {'from': fr, 'to': to, 'faces': {
        'up': {'uv': uv(*up_), 'texture': '#0'}, 'down': {'uv': uv(*down_), 'texture': '#0'},
        'north': {'uv': uv(*sides), 'texture': '#0'}, 'south': {'uv': uv(*sides, flip=True), 'texture': '#0'},
        'east': {'uv': uv(*ends), 'texture': '#0'}, 'west': {'uv': uv(*ends, flip=True), 'texture': '#0'}}}
    if rot: e['rotation'] = rot
    return e

els = []
# книга лежит раскрытой: корешок вдоль Z в центре (x=8), обложки раскрыты влево/вправо и слегка приподняты
A = 15   # угол подъёма половинок (градусы, кратно 7.5)
els.append(box([7.0, 0.0, 1.5], [9.0, 1.4, 14.5], SPINE, SPINE, SPINE, (32, 32, 36, 56)))                        # корешок
for sgn in (-1, 1):
    x0, x1 = (0.5, 7.2) if sgn < 0 else (8.8, 15.5)
    rot = {'origin': [8.0, 0.2, 8.0], 'axis': 'z', 'angle': -A * sgn}
    els.append(box([x0, 0.0, 1.5], [x1, 0.8, 14.5], COVER_IN, COVER_OUT, (0, 20, 32, 24), (0, 20, 32, 24), rot))  # обложка
    px0, px1 = (x0 + 0.6, x1 - 0.1) if sgn < 0 else (x0 + 0.1, x1 - 0.6)
    els.append(box([px0, 0.8, 2.2], [px1, 2.6, 13.8], PAGES, PAGES, PAGE_EDGE, PAGE_EDGE, rot))                   # страницы
# закладка свисает с правой половины
els.append(box([11.0, 2.55, 9.0], [12.2, 2.75, 16.0], MARK, MARK, (40, 32, 44, 33), (40, 32, 41, 56), {'origin': [8.0, 0.2, 8.0], 'axis': 'z', 'angle': -A}))

model = {"credit": "ZenQuests quest_book_model.py", "texture_size": [64, 64],
         "textures": {"0": "zenquests:item/quest_book", "particle": "zenquests:item/quest_book"}, "elements": els,
         "display": {"gui": {"rotation": [55, 25, 0], "translation": [0, 1, 0], "scale": [0.85, 0.85, 0.85]},
                     "ground": {"rotation": [0, 0, 0], "translation": [0, 1, 0], "scale": [0.5, 0.5, 0.5]},
                     "fixed": {"rotation": [90, 0, 0], "scale": [1, 1, 1]},
                     "head": {"rotation": [0, 0, 0], "translation": [0, 14, 0], "scale": [1, 1, 1]},
                     # в руках: книга повёрнута страницами к лицу (наклон к камере), крупнее
                     "thirdperson_righthand": {"rotation": [-75, 0, 0], "translation": [0, 3.5, 1.5], "scale": [0.75, 0.75, 0.75]},
                     "thirdperson_lefthand": {"rotation": [-75, 0, 0], "translation": [0, 3.5, 1.5], "scale": [0.75, 0.75, 0.75]},
                     "firstperson_righthand": {"rotation": [70, -15, 0], "translation": [1, -1, -1.5], "scale": [0.85, 0.85, 0.85]},
                     "firstperson_lefthand": {"rotation": [70, 15, 0], "translation": [-1, -1, -1.5], "scale": [0.85, 0.85, 0.85]}}}
json.dump(model, open(OUT_M, 'w'), separators=(',', ':'))
print('book ok')

if len(sys.argv) > 3:   # превью (тот же рендер, что у рыбы, с учётом rotation элементов)
    import numpy as np
    tex = t
    def rotp(pt, rot):
        if not rot: return pt
        ox, oy, oz = rot['origin']; a = math.radians(rot['angle']); x, y, z = pt[0] - ox, pt[1] - oy, pt[2] - oz
        if rot['axis'] == 'z': x, y = x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)
        elif rot['axis'] == 'x': y, z = y * math.cos(a) - z * math.sin(a), y * math.sin(a) + z * math.cos(a)
        else: x, z = x * math.cos(a) + z * math.sin(a), -x * math.sin(a) + z * math.cos(a)
        return (x + ox, y + oy, z + oz)
    S = 16; ay, ax = math.radians(25 + 180), math.radians(55)
    def proj(pt):
        x, y, z = pt[0] - 8, pt[1] - 8, pt[2] - 8
        x, z = x * math.cos(ay) - z * math.sin(ay), x * math.sin(ay) + z * math.cos(ay)
        y, z = y * math.cos(ax) - z * math.sin(ax), y * math.sin(ax) + z * math.cos(ax)
        return (x * S + 160, -y * S + 160, z)
    img = Image.new('RGBA', (320, 320), (70, 90, 80, 255)); faces = []
    for e in els:
        (x0, y0, z0), (x1, y1, z1) = e['from'], e['to']; rot = e.get('rotation')
        P = {k: proj(rotp(v, rot)) for k, v in {'a': (x0, y0, z0), 'b': (x1, y0, z0), 'c': (x1, y1, z0), 'd': (x0, y1, z0), 'e': (x0, y0, z1), 'f': (x1, y0, z1), 'g': (x1, y1, z1), 'h': (x0, y1, z1)}.items()}
        order = {'north': 'cbad', 'south': 'hgfe', 'up': 'hgcd', 'down': 'abfe', 'east': 'gfbc', 'west': 'dhea'}; sk = {'north': 0.8, 'south': 0.8, 'up': 1.0, 'down': 0.55, 'east': 0.65, 'west': 0.65}
        for n, quad in order.items():
            u = e['faces'][n]['uv']; pts = [P[k] for k in quad]; faces.append((sum(q[2] for q in pts) / 4, pts, [v * 4 for v in u], sk[n]))
    for _, pts, (u0, v0, u1, v1), k in sorted(faces, key=lambda f: -f[0]):
        (ax0, ay0, _), (bx, by, _), (cx, cy, _), (dx, dy, _) = pts
        ex, ey, fx, fy = bx - ax0, by - ay0, dx - ax0, dy - ay0; det = ex * fy - ey * fx
        if abs(det) < 1e-6: continue
        inv = np.array([[fy, -fx], [-ey, ex]]) / det; du, dv = u1 - u0, v1 - v0
        A_ = [inv[0][0] * du, inv[0][1] * du, u0 - (inv[0][0] * ax0 + inv[0][1] * ay0) * du, inv[1][0] * dv, inv[1][1] * dv, v0 - (inv[1][0] * ax0 + inv[1][1] * ay0) * dv]
        face = tex.transform((320, 320), Image.AFFINE, A_, resample=Image.NEAREST)
        mask = Image.new('L', (320, 320), 0); ImageDraw.Draw(mask).polygon([(q[0], q[1]) for q in pts], fill=255)
        if k != 1.0: face = Image.alpha_composite(face, Image.new('RGBA', (320, 320), (0, 0, 0, int(255 * (1 - k)))))
        img.paste(face, (0, 0), mask)
    img.save(sys.argv[3]); print('preview ok')
