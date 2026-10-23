"""Настоящие 3D-модели рыбы (формат блок-моделей Minecraft, как в Blockbench) + текстурный атлас 64x64 на каждый вид.
Тело — ступенчатые сегменты (голова, туловище, хвостовой стебель), плавники — тонкие пластины (спинной, грудные,
анальный, хвост). Типы тела: standard, long, round, flat, kraken, dragon. Палитра берётся из спрайта вида.
Запуск: python3 fish_models3d.py SPRITES_DIR OUT_MODELS OUT_TEXTURES [preview.png]"""
import sys, os, json, math, random
from PIL import Image, ImageDraw

SRC, OUT_M, OUT_T = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(OUT_M, exist_ok=True); os.makedirs(OUT_T, exist_ok=True)

KIND = {'pike': 'long', 'catfish': 'long', 'sturgeon': 'long', 'barracuda': 'long', 'eel': 'eel', 'burbot': 'long', 'beluga': 'long',
        'crystal_pike': 'long', 'ice_pike': 'long', 'swordfish': 'sword', 'farm_legend': 'long', 'marsh_king': 'long', 'tuna': 'standard',
        'pufferfish': 'round', 'mola': 'mola', 'moon_fish': 'round', 'flounder': 'flat', 'kraken_calf': 'kraken', 'sea_dragon': 'dragon',
        'goldfish': 'fancy', 'koi': 'standard', 'grouper': 'standard'}
PATTERN = {'perch': 'stripes', 'mackerel': 'stripes', 'sea_bass': 'stripes', 'clownfish': 'bands', 'zander': 'stripes',
           'trout': 'spots', 'pike': 'spots', 'grouper': 'spots', 'koi': 'patches', 'crystal_pike': 'spots', 'ice_pike': 'spots',
           'pufferfish': 'spots', 'burbot': 'spots', 'azure_trout': 'spots', 'sturgeon': 'scutes', 'beluga': 'scutes', 'gudgeon': 'spots'}

def palette(im):
    """Цвета по спрайту: спина (верхние ряды силуэта), бок, брюхо, плавники (хвостовая часть), глаз-акцент."""
    px = im.load(); W, H = im.size
    pts = [(x, y) for y in range(H) for x in range(W) if px[x, y][3] > 0]
    ys = [y for _, y in pts]; xs = [x for x, _ in pts]
    y0, y1, x0, x1 = min(ys), max(ys), min(xs), max(xs)
    def avg(sel):
        c = [px[x, y][:3] for x, y in pts if sel(x, y)]
        if not c: return (120, 120, 120)
        return tuple(sum(v[i] for v in c) // len(c) for i in range(3))
    back = avg(lambda x, y: y < y0 + (y1 - y0) * 0.3 and x0 + (x1 - x0) * 0.15 < x < x1 - (x1 - x0) * 0.25)
    side = avg(lambda x, y: y0 + (y1 - y0) * 0.3 <= y < y0 + (y1 - y0) * 0.7 and x0 + (x1 - x0) * 0.15 < x < x1 - (x1 - x0) * 0.25)
    belly = avg(lambda x, y: y >= y0 + (y1 - y0) * 0.72 and x0 + (x1 - x0) * 0.15 < x < x1 - (x1 - x0) * 0.25)
    fin = avg(lambda x, y: x > x1 - (x1 - x0) * 0.18)
    back = shade(back, 0.85); belly = mix(belly, (255, 255, 255), 0.2)
    return back, side, belly, fin

def shade(c, k): return tuple(max(0, min(255, int(v * k))) for v in c)
def mix(a, b, t): return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))

def make_texture(fid, pal, rnd):
    """Атлас 64x64: 0..31 x 0..11 бок тела (A); 0..31 x 12..17 спина; 0..31 x 18..23 брюхо; 32..39 x 0..11 морда/торцы;
    0..13 x 24..39 хвост; 14..29 x 24..31 спинной плавник; 30..37 x 24..29 грудной; 40..63 x 0..15 плавник большой (дракон)."""
    back, side, belly, fin = pal
    t = Image.new('RGBA', (64, 64), (0, 0, 0, 0)); d = ImageDraw.Draw(t); p = t.load()
    outline = shade(back, 0.45)
    # бок: вертикальный градиент спина→бок→брюхо + чешуя
    for y in range(12):
        k = y / 11
        c = mix(back, side, k * 2) if k < 0.5 else mix(side, belly, (k - 0.5) * 2)
        for x in range(32):
            cc = c
            if (x + y) % 2 == 0 and 1 <= y <= 10: cc = shade(c, 0.88)   # чешуя
            if ((x // 2 + y) % 3 == 0) and 2 <= y <= 9: cc = shade(cc, 1.08)
            p[x, y] = cc + (255,)
    pat = PATTERN.get(fid)
    if pat == 'stripes':
        for x in range(6, 30, 5): d.line((x, 1, x + 1, 9), fill=shade(back, 0.6) + (255,), width=2)
    elif pat == 'bands':
        for x in (8, 17, 26): d.rectangle((x, 0, x + 2, 11), fill=(245, 245, 245, 255)); d.line((x - 1, 0, x - 1, 11), fill=outline + (255,)); d.line((x + 3, 0, x + 3, 11), fill=outline + (255,))
    elif pat == 'spots':
        for _ in range(16): x, y = rnd.randint(4, 29), rnd.randint(1, 8); p[x, y] = shade(back, 0.55) + (255,); p[min(31, x + 1), y] = shade(back, 0.65) + (255,)
    elif pat == 'patches':
        for _ in range(4):
            x, y = rnd.randint(3, 24), rnd.randint(0, 6); d.ellipse((x, y, x + rnd.randint(4, 8), y + rnd.randint(3, 5)), fill=(214, 60, 40, 255))
        x, y = rnd.randint(10, 24), rnd.randint(2, 7); d.ellipse((x, y, x + 3, y + 2), fill=(30, 30, 30, 255))
    elif pat == 'scutes':
        for x in range(4, 30, 3): p[x, 1] = shade(belly, 1.1) + (255,); p[x, 6] = shade(belly, 1.05) + (255,)
    # контур сверху/снизу, жаберная крышка и глаз у морды (морда — справа, x≈31)
    d.line((0, 0, 31, 0), fill=outline + (255,)); d.line((0, 11, 31, 11), fill=outline + (255,))
    d.line((24, 1, 24, 10), fill=shade(side, 0.75) + (255,))
    d.rectangle((27, 2, 29, 4), fill=(250, 250, 250, 255)); p[29, 3] = (20, 20, 20, 255); p[28, 4] = (20, 20, 20, 255); p[29, 4] = (20, 20, 20, 255)
    d.line((28, 8, 31, 7), fill=outline + (255,)); d.line((30, 8, 31, 9), fill=outline + (255,))   # рот
    # спина и брюхо
    for y in range(12, 18):
        for x in range(32): p[x, y] = shade(back, 0.9 + 0.1 * ((x + y) % 2)) + (255,)
    for y in range(18, 24):
        for x in range(32): p[x, y] = shade(belly, 0.95 + 0.05 * ((x + y) % 2)) + (255,)
    # торцы (морда спереди, срез сзади)
    for y in range(12):
        for x in range(32, 40): p[x, y] = mix(back, belly, y / 11) + (255,)
    d.rectangle((32, 0, 39, 11), outline=outline + (255,))
    # хвост: веер с лучами
    fd, fl = shade(fin, 0.8), shade(fin, 1.15)
    d.rectangle((0, 24, 13, 39), fill=fin + (255,))
    for y in range(24, 40, 2): d.line((0, y, 13, y + (1 if y % 4 else -1)), fill=fd + (255,))
    d.rectangle((0, 24, 13, 39), outline=outline + (255,))
    # спинной и грудной
    d.rectangle((14, 24, 29, 31), fill=fin + (255,)); 
    for x in range(15, 29, 3): d.line((x, 25, x + 1, 31), fill=fd + (255,))
    d.rectangle((14, 24, 29, 31), outline=outline + (255,))
    d.rectangle((30, 24, 37, 29), fill=fl + (255,), outline=outline + (255,))
    # большой плавник (дракон/парус)
    d.rectangle((40, 0, 63, 15), fill=fin + (255,))
    for x in range(42, 63, 4): d.line((x, 1, x + 2, 15), fill=fd + (255,))
    d.rectangle((40, 0, 63, 15), outline=outline + (255,))
    return t

# ── геометрия ──
UV = {'side': (0, 0, 32, 12), 'top': (0, 12, 32, 18), 'bottom': (0, 18, 32, 24), 'end': (32, 0, 40, 12),
      'tail': (0, 24, 14, 40), 'dorsal': (14, 24, 30, 32), 'pect': (30, 24, 38, 30), 'sail': (40, 0, 64, 16)}
def uv16(r, flip=False):
    x0, y0, x1, y1 = [v / 4 for v in r]   # атлас 64 px → 16 единиц
    return [x1, y0, x0, y1] if flip else [x0, y0, x1, y1]

CUR_L = [16.0]   # длина тела текущей модели (хвост x=0 … морда x=CUR_L): полоса текстуры растягивается на неё

def box(fr, to, tex='side', top='top', bottom='bottom', ends='end', rot=None, uv_part=None):
    """Параллелепипед вдоль X (хвост слева x=0 … голова справа x=CUR_L). Бока — часть полосы side по доле длины."""
    x0, y0, z0 = fr; x1, y1, z1 = to
    def strip(r):   # участок полосы по x: доля [x0/L, x1/L] от длины тела
        rx0, ry0, rx1, ry1 = r; w = rx1 - rx0; Lb = CUR_L[0]
        a, b = rx0 + w * min(1, x0 / Lb), rx0 + w * min(1, x1 / Lb)
        return (a, ry0, b, ry1)
    s = strip(UV[tex]) if uv_part is None else uv_part
    faces = {'south': {'uv': uv16(s), 'texture': '#0'}, 'north': {'uv': uv16(s, True), 'texture': '#0'},
             'up': {'uv': uv16(strip(UV[top])), 'texture': '#0'}, 'down': {'uv': uv16(strip(UV[bottom])), 'texture': '#0'},
             'east': {'uv': uv16(UV[ends]), 'texture': '#0'}, 'west': {'uv': uv16(UV[ends], True), 'texture': '#0'}}
    e = {'from': [round(x0, 3), round(y0, 3), round(z0, 3)], 'to': [round(x1, 3), round(y1, 3), round(z1, 3)], 'faces': faces}
    if rot: e['rotation'] = rot
    return e

def plate(fr, to, part, rot=None):
    """Тонкая пластина-плавник: обе широкие грани — регион part, торцы — полоска."""
    x0, y0, z0 = fr; x1, y1, z1 = to; r = UV[part]
    thin_x = (x1 - x0) < (z1 - z0)   # пластина в плоскости YZ (грудные) или XY
    f = {'south': {'uv': uv16(r), 'texture': '#0'}, 'north': {'uv': uv16(r, True), 'texture': '#0'},
         'east': {'uv': uv16(r), 'texture': '#0'}, 'west': {'uv': uv16(r, True), 'texture': '#0'},
         'up': {'uv': uv16((r[0], r[1], r[2], r[1] + 1)), 'texture': '#0'}, 'down': {'uv': uv16((r[0], r[3] - 1, r[2], r[3])), 'texture': '#0'}}
    e = {'from': [round(v, 3) for v in fr], 'to': [round(v, 3) for v in to], 'faces': f}
    if rot: e['rotation'] = rot
    return e

def body_standard(h=6.0, w=3.0, L=13.0, tail=3.0, segs=6, snub=0.55):
    """Тело из segs ступенчатых сегментов по профилю рыбы (пик высоты на 55% длины от хвоста), хвост раздвоенный,
    спинной плавник ступенчатым треугольником, грудные — маленькие пластины под углом."""
    cy = 8.0; els = []; CUR_L[0] = L
    def prof(t):   # t 0 (стебель) … 1 (морда): относительная высота
        if t < 0.55: return 0.32 + 0.68 * (t / 0.55) ** 0.9
        return 1 - (1 - snub) * ((t - 0.55) / 0.45) ** 1.6
    x = tail
    for i in range(segs):
        x0 = tail + (L - tail) * i / segs; x1 = tail + (L - tail) * (i + 1) / segs
        k = prof((i + 0.5) / segs); hh = h * k; ww = w * (0.45 + 0.55 * k)
        els.append(box((x0, cy - hh / 2, 8 - ww / 2), (x1 + 0.01, cy + hh / 2, 8 + ww / 2)))
    # раздвоенный хвост: две лопасти под углом
    th = h * 0.42
    els.append(plate((0, cy, 7.8), (tail + 0.4, cy + th, 8.2), 'tail', rot={'origin': [tail + 0.4, cy, 8], 'axis': 'z', 'angle': -22.5}))
    els.append(plate((0, cy - th, 7.8), (tail + 0.4, cy, 8.2), 'tail', rot={'origin': [tail + 0.4, cy, 8], 'axis': 'z', 'angle': 22.5}))
    # спинной плавник — три ступени
    bx0 = tail + (L - tail) * 0.35; bx1 = tail + (L - tail) * 0.62
    for j, (fx0, fx1, fh) in enumerate(((bx0, bx0 + (bx1 - bx0) * 0.4, h * 0.42), (bx0 + (bx1 - bx0) * 0.4, bx0 + (bx1 - bx0) * 0.75, h * 0.3), (bx0 + (bx1 - bx0) * 0.75, bx1, h * 0.16))):
        top = cy + h * prof(((fx0 + fx1) / 2 - tail) / (L - tail)) / 2
        els.append(plate((fx0, top - 0.1, 7.8), (fx1, top + fh, 8.2), 'dorsal'))
    # анальный плавник
    ax = tail + (L - tail) * 0.28; bot = cy - h * prof((ax - tail) / (L - tail)) / 2
    els.append(plate((ax, bot - h * 0.22, 7.8), (ax + 1.6, bot + 0.1, 8.2), 'dorsal'))
    # грудные: небольшие пластины у головы, отведены назад и вниз
    hx = tail + (L - tail) * 0.7; hw = w * (0.45 + 0.55 * prof(0.7)) / 2
    for sgn in (-1, 1):
        z = 8 + sgn * (hw - 0.1)
        els.append(plate((hx - 1.8, cy - 0.9, min(z, z + sgn * 0.4)), (hx, cy + 0.3, max(z, z + sgn * 0.4)), 'pect',
                         rot={'origin': [hx, cy, z], 'axis': 'y', 'angle': 22.5 * sgn}))
    return els

def body_long(): return body_standard(h=3.8, w=2.6, L=14.5, tail=2.2, segs=7, snub=0.45)
def body_eel():
    els = []; cy = 8.0; CUR_L[0] = 16.0
    for i, (x0, x1, h) in enumerate(((2, 6, 1.8), (6, 10, 2.2), (10, 13.5, 2.0), (13.5, 16, 1.6))):
        els.append(box((x0, cy - h / 2 + (0.4 if i % 2 else 0), 8 - h / 2), (x1 + 0.01, cy + h / 2 + (0.4 if i % 2 else 0), 8 + h / 2)))
    els.append(plate((0, cy - 1.2, 7.8), (2.3, cy + 1.2, 8.2), 'tail'))
    els.append(plate((5, cy + 1.1, 7.8), (13, cy + 2.0, 8.2), 'dorsal'))
    return els
def body_sword():
    els = body_standard(h=4.5, w=2.6, L=12.0, tail=2.5, segs=6, snub=0.4)
    els.append(box((12, 7.4, 7.5), (16, 8.6, 8.5), tex='end', top='end', bottom='end'))   # меч
    els.append(plate((6, 10.2, 7.75), (9, 13.5, 8.25), 'sail'))                           # высокий спинной
    return els
def body_round():
    els = []; cy = 8.0; CUR_L[0] = 13.0
    els.append(box((4, cy - 3.5, 5.5), (12, cy + 3.5, 10.5)))
    els.append(box((5, cy - 4.5, 6.5), (11, cy + 4.5, 9.5)))
    els.append(box((3, cy - 2.5, 6.5), (13, cy + 2.5, 9.5)))
    els.append(plate((0.5, cy - 2, 7.75), (3.3, cy + 2, 8.25), 'tail'))
    els.append(plate((6, cy + 4.4, 7.75), (9, cy + 6, 8.25), 'dorsal'))
    for s in (-1, 1): els.append(plate((9.5, cy - 0.5, 8 + s * 2.4 - (0.25 if s > 0 else 2.0)), (10.0, cy + 1, 8 + s * 2.4 + (2.0 if s > 0 else 0.25)), 'pect'))
    return els
def body_mola():
    els = []; cy = 8.0; CUR_L[0] = 13.0
    els.append(box((3, cy - 4, 6.8), (13, cy + 4, 9.2)))
    els.append(box((5, cy - 5, 7.2), (12, cy + 5, 8.8)))
    els.append(plate((7, cy + 4.9, 7.75), (10, cy + 8, 8.25), 'sail'))     # верхний плавник
    els.append(plate((7, cy - 8, 7.75), (10, cy - 4.9, 8.25), 'sail'))     # нижний
    els.append(plate((1.5, cy - 3, 7.75), (3.3, cy + 3, 8.25), 'tail'))
    return els
def body_flat():
    els = []; cy = 7.0; CUR_L[0] = 13.0
    els.append(box((3, cy - 0.8, 3.5), (13, cy + 0.8, 12.5)))
    els.append(box((5, cy - 1.0, 5), (12, cy + 1.0, 11)))
    els.append(plate((0.5, cy - 0.4, 6), (3.3, cy + 0.4, 10), 'tail'))
    return els
def body_kraken():
    els = []; cy = 10.5; CUR_L[0] = 11.0
    els.append(box((5, cy - 3, 5), (11, cy + 3.5, 11), tex='side', top='top', bottom='bottom'))
    els.append(box((6, cy + 3.4, 6), (10, cy + 5, 10)))
    rnd = random.Random(7)
    for i in range(8):
        ang = i * math.pi / 4; x = 8 + math.cos(ang) * 2.3; z = 8 + math.sin(ang) * 2.3
        els.append(box((x - 0.6, cy - 3 - 5 - rnd.random(), z - 0.6), (x + 0.6, cy - 2.9, z + 0.6), tex='bottom', top='bottom', bottom='bottom', ends='bottom',
                       rot={'origin': [x, cy - 3, z], 'axis': 'x' if i % 2 else 'z', 'angle': 22.5 * (1 if i % 4 < 2 else -1)}))
    return els
def body_dragon():
    els = body_standard(h=4.2, w=2.6, L=13.5, tail=2.6, segs=7, snub=0.5)
    els.append(plate((4, 10.0, 7.75), (10.5, 14.5, 8.25), 'sail'))      # парус
    els.append(plate((11.5, 10, 7.75), (13.5, 12.5, 8.25), 'sail'))      # рога-гребень
    for s in (-1, 1): els.append(plate((7, 6.0, 8 + s * 1.4 - (0.25 if s > 0 else 3.0)), (7.5, 8.5, 8 + s * 1.4 + (3.0 if s > 0 else 0.25)), 'sail'))
    return els
def body_fancy():
    els = body_standard(h=5.5, w=3.2, L=11.0, tail=4.0, segs=5, snub=0.6)
    els.append(plate((0, 4.5, 7.75), (4.3, 11.5, 8.25), 'sail'))   # пышный хвост
    return els

BUILD = {'standard': body_standard, 'long': body_long, 'eel': body_eel, 'sword': body_sword, 'round': body_round,
         'mola': body_mola, 'flat': body_flat, 'kraken': body_kraken, 'dragon': body_dragon, 'fancy': body_fancy}
DISPLAY = {"gui": {"rotation": [25, 35, 0], "translation": [0, 0, 0], "scale": [0.8, 0.8, 0.8]},
           "ground": {"rotation": [0, 0, 0], "translation": [0, 1, 0], "scale": [0.5, 0.5, 0.5]},
           "fixed": {"rotation": [0, -90, 0], "scale": [1, 1, 1]},
           "thirdperson_righthand": {"rotation": [0, 90, -25], "translation": [0, 2, 1], "scale": [0.6, 0.6, 0.6]},
           "thirdperson_lefthand": {"rotation": [0, -90, 25], "translation": [0, 2, 1], "scale": [0.6, 0.6, 0.6]},
           "firstperson_righthand": {"rotation": [0, -70, 20], "translation": [1, 2, 0], "scale": [0.65, 0.65, 0.65]},
           "firstperson_lefthand": {"rotation": [0, 70, -20], "translation": [1, 2, 0], "scale": [0.65, 0.65, 0.65]}}

made = []
for f in sorted(os.listdir(SRC)):
    if not f.endswith('.png'): continue
    fid = f[:-4]; im = Image.open(f'{SRC}/{f}').convert('RGBA')
    rnd = random.Random(hash(fid) & 0xffff)
    tex = make_texture(fid, palette(im), rnd); tex.save(f'{OUT_T}/{fid}.png')
    els = BUILD[KIND.get(fid, 'standard')]()
    model = {"credit": "ZenFishing fish_models3d.py", "texture_size": [64, 64],
             "textures": {"0": f"zenfishing:item/fish3d/{fid}", "particle": f"zenfishing:item/fish3d/{fid}"},
             "elements": els, "display": DISPLAY}
    json.dump(model, open(f'{OUT_M}/{fid}.json', 'w'), separators=(',', ':'))
    made.append(fid)
print('models:', len(made))

# ── превью: простой рендер боксов (ортографическая проекция, плоская заливка средним цветом грани) ──
if len(sys.argv) > 4:
    import numpy as np
    def render(fid, S=14, rot_y=35, rot_x=25):
        m = json.load(open(f'{OUT_M}/{fid}.json')); tex = Image.open(f'{OUT_T}/{fid}.png').convert('RGBA')
        ay, ax = math.radians(rot_y + 180), math.radians(rot_x)
        def proj(x, y, z):
            x, y, z = x - 8, y - 8, z - 8
            x, z = x * math.cos(ay) - z * math.sin(ay), x * math.sin(ay) + z * math.cos(ay)
            y, z = y * math.cos(ax) - z * math.sin(ax), y * math.sin(ax) + z * math.cos(ax)
            return (x * S + 160, -y * S + 160, z)
        img = Image.new('RGBA', (320, 320), (0, 0, 0, 0))
        faces = []
        for e in m['elements']:
            (x0, y0, z0), (x1, y1, z1) = e['from'], e['to']
            P = {'a': (x0, y0, z0), 'b': (x1, y0, z0), 'c': (x1, y1, z0), 'd': (x0, y1, z0), 'e': (x0, y0, z1), 'f': (x1, y0, z1), 'g': (x1, y1, z1), 'h': (x0, y1, z1)}
            # порядок углов грани: (uv0,uv1) → верх-лево … как рисует Minecraft (север смотрит на -z)
            order = {'north': 'cbad', 'south': 'hgfe', 'up': 'hgcd', 'down': 'abfe', 'east': 'gfbc', 'west': 'dhea'}
            shade_k = {'north': 0.8, 'south': 0.8, 'up': 1.0, 'down': 0.55, 'east': 0.65, 'west': 0.65}
            for name, quad in order.items():
                uv = e['faces'][name]['uv']; u0, v0, u1, v1 = [v * 4 for v in uv]
                pts = [proj(*P[k]) for k in quad]; depth = sum(p[2] for p in pts) / 4
                faces.append((depth, pts, (u0, v0, u1, v1), shade_k[name]))
        for _, pts, (u0, v0, u1, v1), k in sorted(faces, key=lambda t: -t[0]):
            (ax0, ay0, _), (bx, by, _), (cx, cy, _), (dx, dy, _) = pts   # a=(u0,v0) b=(u1,v0) c=(u1,v1) d=(u0,v1)
            ex, ey = bx - ax0, by - ay0; fx, fy = dx - ax0, dy - ay0
            det = ex * fy - ey * fx
            if abs(det) < 1e-6: continue
            # обратное отображение: (X,Y) выход → (u,v) текстуры
            inv = np.array([[fy, -fx], [-ey, ex]]) / det
            du, dv = (u1 - u0), (v1 - v0)
            A = [inv[0][0] * du, inv[0][1] * du, u0 - (inv[0][0] * ax0 + inv[0][1] * ay0) * du,
                 inv[1][0] * dv, inv[1][1] * dv, v0 - (inv[1][0] * ax0 + inv[1][1] * ay0) * dv]
            face = tex.transform((320, 320), Image.AFFINE, A, resample=Image.NEAREST)
            mask = Image.new('L', (320, 320), 0); ImageDraw.Draw(mask).polygon([(p[0], p[1]) for p in pts], fill=255)
            if k != 1.0:
                dark = Image.new('RGBA', (320, 320), (0, 0, 0, int(255 * (1 - k)))); face = Image.alpha_composite(face, dark)
            img.paste(face, (0, 0), mask)
        return img
    show = ['carp', 'perch', 'pike', 'swordfish', 'pufferfish', 'flounder', 'eel', 'koi', 'kraken_calf', 'sea_dragon', 'goldfish', 'clownfish']
    pv = Image.new('RGBA', (4 * 320, 3 * 320), (70, 90, 80, 255)); dr = ImageDraw.Draw(pv)
    for i, fid in enumerate(show):
        if fid in made: pv.alpha_composite(render(fid), ((i % 4) * 320, (i // 4) * 320)); dr.text(((i % 4) * 320 + 8, (i // 4) * 320 + 8), fid, fill=(255, 255, 255, 255))
    pv.save(sys.argv[4]); print('preview ok')
