"""3D-модели рыбы в стиле FreshFood (пак на сервере: cod_3d, salmon_3d, tropical_fish_3d): мало боксов (тело 2–3, голова,
хвост и плавники — пластины), текстура 32x32 с плоскими яркими цветами (10–20 штук), 1 тексель = 0.5 юнита модели.
Никакой мелкой чешуи и градиентов — чистые заливки, тёмная полоса спины, светлое брюхо, пара пятен/полос, глаз 2 px.
Запуск: python3 fish_models3d.py SPRITES_DIR OUT_MODELS OUT_TEXTURES [preview.png]  (SPRITES — только список видов)"""
import sys, os, json, math, random
from PIL import Image, ImageDraw

SRC, OUT_M, OUT_T = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(OUT_M, exist_ok=True); os.makedirs(OUT_T, exist_ok=True)

KIND = {'pike': 'long', 'catfish': 'long', 'sturgeon': 'long', 'barracuda': 'long', 'eel': 'eel', 'burbot': 'long', 'beluga': 'long',
        'crystal_pike': 'long', 'ice_pike': 'long', 'swordfish': 'sword', 'farm_legend': 'long', 'marsh_king': 'long', 'tuna': 'standard',
        'pufferfish': 'round', 'mola': 'mola', 'moon_fish': 'round', 'flounder': 'flat', 'kraken_calf': 'kraken', 'sea_dragon': 'dragon',
        'goldfish': 'fancy', 'koi': 'standard', 'grouper': 'standard', 'bream': 'tall', 'crucian': 'tall', 'perch': 'tall', 'golden_carp': 'tall',
        'carp': 'tall', 'grayling': 'standard', 'clownfish': 'small', 'sardine': 'small', 'bleak': 'small', 'gudgeon': 'small', 'goby': 'small', 'ruffe': 'small'}
PATTERN = {'perch': 'stripes', 'mackerel': 'stripes', 'sea_bass': 'stripes', 'clownfish': 'bands', 'zander': 'stripes',
           'trout': 'spots', 'pike': 'spots', 'grouper': 'spots', 'koi': 'patches', 'crystal_pike': 'spots', 'ice_pike': 'spots',
           'pufferfish': 'spots', 'burbot': 'spots', 'azure_trout': 'spots', 'sturgeon': 'scutes', 'beluga': 'scutes', 'gudgeon': 'spots',
           'ruffe': 'spots', 'salmon': 'spots', 'tench': 'spots', 'marsh_king': 'stripes', 'tuna': 'line', 'herring': 'line', 'sardine': 'line'}

# Плоские палитры: (спина, бок, брюхо, плавники). Яркие, светлые — в игре бока затеняются.
PAL = {
 'carp': ((222,150,48),(252,204,96),(255,240,190),(240,128,56)),
 'perch': ((70,150,60),(166,220,86),(250,242,180),(246,104,44)),
 'roach': ((80,120,190),(186,212,246),(255,255,255),(240,86,66)),
 'bream': ((160,124,70),(222,194,126),(255,246,214),(130,96,74)),
 'herring': ((48,110,180),(160,206,240),(255,255,255),(120,176,226)),
 'pike': ((60,124,56),(150,204,92),(238,242,186),(196,118,64)),
 'trout': ((96,136,96),(234,166,126),(255,232,214),(236,126,116)),
 'catfish': ((80,90,110),(160,170,180),(242,232,204),(140,130,130)),
 'mackerel': ((34,116,176),(130,214,234),(255,255,255),(70,146,206)),
 'zander': ((86,116,74),(196,206,136),(255,250,222),(120,128,96)),
 'sturgeon': ((80,100,120),(170,180,190),(250,246,232),(130,140,150)),
 'tuna': ((36,76,156),(118,168,226),(242,246,255),(252,214,66)),
 'clownfish': ((236,104,32),(255,154,54),(255,214,124),(255,136,44)),
 'pufferfish': ((206,166,64),(250,218,100),(255,250,222),(146,116,64)),
 'golden_carp': ((234,164,24),(255,214,64),(255,246,184),(255,174,44)),
 'swordfish': ((36,66,166),(96,146,236),(232,242,255),(66,86,206)),
 'marsh_king': ((66,116,76),(126,186,96),(222,232,174),(156,126,64)),
 'moon_fish': ((126,126,216),(196,206,255),(255,255,255),(224,224,255)),
 'farm_legend': ((66,136,116),(116,216,176),(242,255,246),(255,206,86)),
 'azure_trout': ((36,126,206),(96,196,252),(232,250,255),(66,166,244)),
 'crystal_pike': ((116,196,226),(196,242,255),(255,255,255),(156,224,255)),
 'kraken_calf': ((116,66,176),(176,116,236),(242,224,255),(136,86,206)),
 'crucian': ((176,146,64),(232,202,100),(255,246,204),(206,116,54)),
 'bleak': ((106,136,186),(206,226,248),(255,255,255),(176,196,226)),
 'gudgeon': ((126,116,84),(202,186,136),(252,246,224),(156,136,96)),
 'ruffe': ((126,126,84),(206,206,126),(252,252,214),(156,156,96)),
 'goby': ((116,96,64),(186,156,106),(242,232,204),(146,116,74)),
 'sardine': ((56,116,176),(176,216,244),(255,255,255),(126,176,226)),
 'tench': ((66,106,54),(136,176,86),(232,232,174),(116,116,64)),
 'chub': ((86,116,116),(186,206,196),(255,255,242),(226,116,74)),
 'burbot': ((96,86,54),(176,156,106),(242,232,204),(136,116,74)),
 'flounder': ((146,116,74),(206,176,126),(255,250,236),(176,146,96)),
 'grayling': ((86,96,156),(176,186,236),(250,250,255),(206,96,186)),
 'eel': ((66,86,54),(136,156,96),(232,232,184),(116,126,86)),
 'salmon': ((86,126,146),(236,146,116),(255,222,204),(206,116,96)),
 'barracuda': ((66,116,136),(176,216,226),(255,255,255),(126,166,186)),
 'sea_bass': ((76,96,116),(176,196,216),(255,255,255),(126,146,176)),
 'koi': ((250,250,250),(255,255,255),(255,255,255),(255,126,66)),
 'grouper': ((186,76,66),(244,136,96),(255,222,194),(206,96,76)),
 'beluga': ((96,106,126),(196,206,216),(255,255,255),(156,166,176)),
 'mola': ((96,116,146),(176,196,216),(242,246,250),(136,156,176)),
 'ice_pike': ((96,166,216),(176,234,255),(255,255,255),(136,206,244)),
 'goldfish': ((244,126,24),(255,176,46),(255,232,156),(255,146,46)),
 'sea_dragon': ((36,126,116),(76,206,176),(224,255,242),(255,196,66)),
}
def shade(c, k): return tuple(max(0, min(255, int(v * k))) for v in c)
def mix(a, b, t): return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))

# ── текстура 32x32 (1 тексель = 0.5 юнита). Регионы в текселях:
#   SIDE  (0,0)-(16,10)   бок тела (голова справа), TOP (0,10)-(16,14) спина, BOT (0,14)-(16,18) брюхо, FACE (16,0)-(20,10) торцы
#   TAIL  (20,0)-(32,12)  хвост-пластина, DORSAL (16,12)-(32,18) спинной, PECT (0,18)-(6,24) грудной, SAIL (6,18)-(32,32) большой плавник
R = {'side': (0, 0, 16, 10), 'top': (0, 10, 16, 14), 'bot': (0, 14, 16, 18), 'face': (16, 0, 20, 10),
     'tail': (20, 0, 32, 12), 'dorsal': (16, 12, 32, 18), 'pect': (0, 18, 6, 24), 'sail': (6, 18, 32, 32)}

def make_texture(fid, pal, rnd):
    back, side, belly, fin = pal
    t = Image.new('RGBA', (32, 32), (0, 0, 0, 0)); d = ImageDraw.Draw(t); p = t.load()
    dark = shade(back, 0.7); fin_d = shade(fin, 0.72)
    # бок: 3 плоские полосы — спина (2), бок (5), брюхо (3)
    d.rectangle((0, 0, 15, 1), fill=back + (255,)); d.rectangle((0, 2, 15, 6), fill=side + (255,)); d.rectangle((0, 7, 15, 9), fill=belly + (255,))
    pat = PATTERN.get(fid)
    if pat == 'stripes':
        for x in (3, 6, 9, 12): d.line((x, 1, x, 7), fill=dark + (255,))
    elif pat == 'bands':
        for x in (4, 9): d.rectangle((x, 0, x + 1, 9), fill=(255, 255, 255, 255)); d.line((x - 1, 0, x - 1, 9), fill=dark + (255,)); d.line((x + 2, 0, x + 2, 9), fill=dark + (255,))
    elif pat == 'spots':
        for _ in range(6): x, y = rnd.randint(2, 12), rnd.randint(2, 6); p[x, y] = dark + (255,)
    elif pat == 'patches':
        d.rectangle((3, 1, 6, 5), fill=(226, 70, 44, 255)); d.rectangle((9, 3, 12, 7), fill=(226, 70, 44, 255)); p[7, 2] = (40, 40, 40, 255)
    elif pat == 'scutes':
        for x in range(2, 14, 3): p[x, 2] = mix(belly, (255, 255, 255), 0.5) + (255,)
    elif pat == 'line':
        d.line((0, 4, 13, 4), fill=mix(back, side, 0.5) + (255,))
    # глаз (у головы, справа) и жаберная линия
    p[13, 3] = (255, 255, 255, 255); p[14, 3] = (30, 30, 36, 255); p[13, 4] = (255, 255, 255, 255); p[14, 4] = (30, 30, 36, 255)
    d.line((11, 1, 11, 8), fill=mix(side, dark, 0.5) + (255,))
    # спина / брюхо / торцы
    d.rectangle((0, 10, 15, 13), fill=back + (255,)); d.line((0, 11, 15, 11), fill=mix(back, (255, 255, 255), 0.25) + (255,))
    d.rectangle((0, 14, 15, 17), fill=belly + (255,))
    d.rectangle((16, 0, 19, 2), fill=back + (255,)); d.rectangle((16, 3, 19, 6), fill=side + (255,)); d.rectangle((16, 7, 19, 9), fill=belly + (255,))
    p[17, 8] = dark + (255,); p[18, 8] = dark + (255,)   # рот
    # плавники: заливка + тёмный край + 2 луча
    def finbox(x0, y0, x1, y1, rays):
        d.rectangle((x0, y0, x1, y1), fill=fin + (255,)); d.rectangle((x0, y0, x1, y1), outline=fin_d + (255,))
        for r in rays: d.line(r, fill=fin_d + (255,))
    finbox(20, 0, 31, 11, [(20, 5, 31, 2), (20, 6, 31, 9)])
    finbox(16, 12, 31, 17, [(21, 12, 21, 17), (26, 12, 26, 17)])
    finbox(0, 18, 5, 23, [(2, 18, 2, 23)])
    finbox(6, 18, 31, 31, [(12, 18, 12, 31), (18, 18, 18, 31), (24, 18, 24, 31)])
    return t

# ── геометрия: хвост слева (x=0), голова справа; текстура 32 px → uv-единицы = px/2 ──
def uv(r, flip=False):
    x0, y0, x1, y1 = [v / 2 for v in r]
    return [x1, y0, x0, y1] if flip else [x0, y0, x1, y1]

def sub(r, a, b):
    """часть региона по ширине: доли a..b"""
    x0, y0, x1, y1 = r; w = x1 - x0
    return (x0 + w * a, y0, x0 + w * b, y1)

def box(fr, to, part_a=0.0, part_b=1.0, rot=None, tex=None):
    """бокс тела: бока — доля региона side, верх/низ — top/bot, торцы — face"""
    s = sub(R['side'], part_a, part_b); tp = sub(R['top'], part_a, part_b); bt = sub(R['bot'], part_a, part_b)
    if tex: s = tp = bt = R[tex]
    faces = {'south': {'uv': uv(s), 'texture': '#0'}, 'north': {'uv': uv(s, True), 'texture': '#0'},
             'up': {'uv': uv(tp), 'texture': '#0'}, 'down': {'uv': uv(bt), 'texture': '#0'},
             'east': {'uv': uv(R['face']), 'texture': '#0'}, 'west': {'uv': uv(R['face'], True), 'texture': '#0'}}
    e = {'from': [round(v, 3) for v in fr], 'to': [round(v, 3) for v in to], 'faces': faces}
    if rot: e['rotation'] = rot
    return e

def plate(fr, to, part, rot=None):
    """пластина нулевой толщины (плавник): две грани"""
    x0, y0, z0 = fr; x1, y1, z1 = to; r = R[part]
    if abs(z1 - z0) < 1e-6: faces = {'south': {'uv': uv(r), 'texture': '#0'}, 'north': {'uv': uv(r, True), 'texture': '#0'}}
    elif abs(x1 - x0) < 1e-6: faces = {'east': {'uv': uv(r), 'texture': '#0'}, 'west': {'uv': uv(r, True), 'texture': '#0'}}
    else: faces = {'up': {'uv': uv(r), 'texture': '#0'}, 'down': {'uv': uv(r, True), 'texture': '#0'}}
    e = {'from': [round(v, 3) for v in fr], 'to': [round(v, 3) for v in to], 'faces': faces}
    if rot: e['rotation'] = rot
    return e

def body_generic(L=8.0, h=4.0, w=2.0, head=2.5, tail=3.5, cy=5.0, dorsal=1.5, head_h=None, forked=True):
    """тело: 2 бокса (туловище + голова), хвост-пластина, спинной, анальный, 2 грудных. Всё по 0.5 юнита."""
    els = []; hh = head_h or h * 0.8; x0 = tail; xb = x0 + L; xh = xb + head
    els.append(box((x0, cy - h / 2, 8 - w / 2), (xb, cy + h / 2, 8 + w / 2), 0.0, 0.7))
    els.append(box((xb, cy - hh / 2, 8 - w / 2 + 0.25), (xh, cy + hh / 2, 8 + w / 2 - 0.25), 0.7, 1.0))
    th = h * 0.9
    if forked:
        els.append(plate((0, cy, 8), (x0 + 0.5, cy + th / 2 + 0.5, 8), 'tail', rot={'origin': [x0 + 0.5, cy, 8], 'axis': 'z', 'angle': -22.5}))
        els.append(plate((0, cy - th / 2 - 0.5, 8), (x0 + 0.5, cy, 8), 'tail', rot={'origin': [x0 + 0.5, cy, 8], 'axis': 'z', 'angle': 22.5}))
    else:
        els.append(plate((0, cy - th / 2, 8), (x0 + 0.5, cy + th / 2, 8), 'tail'))
    els.append(plate((x0 + L * 0.3, cy + h / 2, 8), (x0 + L * 0.75, cy + h / 2 + dorsal, 8), 'dorsal'))
    els.append(plate((x0 + L * 0.25, cy - h / 2 - dorsal * 0.6, 8), (x0 + L * 0.5, cy - h / 2, 8), 'dorsal'))
    for sgn in (-1, 1):
        z = 8 + sgn * w / 2
        els.append(plate((xb - 1.5, cy - h / 2 + 0.25, z), (xb, cy - h / 2 + 1.75, z), 'pect', rot={'origin': [xb, cy - h / 2 + 1, z], 'axis': 'y', 'angle': 30 * sgn}))
    return els

def body_standard(): return body_generic(L=8.0, h=4.0, w=2.0, head=2.5, tail=3.5)
def body_tall(): return body_generic(L=7.5, h=5.5, w=2.5, head=2.5, tail=3.5, dorsal=2.0)
def body_small(): return body_generic(L=6.0, h=3.0, w=1.5, head=2.0, tail=3.0, cy=5.5)
def body_long(): return body_generic(L=9.5, h=3.0, w=2.0, head=3.0, tail=3.0, dorsal=1.0)
def body_eel():
    els = []; cy = 5.0
    for i, (a, b) in enumerate(((3, 7.5), (7.5, 12), (12, 16))):
        y = cy + (0.5 if i == 1 else 0)
        els.append(box((a, y - 1, 7), (b, y + 1, 9), i / 3, (i + 1) / 3))
    els.append(plate((0, cy - 1.5, 8), (3.5, cy + 1.5, 8), 'tail'))
    els.append(plate((5, cy + 1, 8), (13, cy + 2, 8), 'dorsal'))
    return els
def body_sword():
    els = body_generic(L=7.5, h=3.5, w=2.0, head=2.5, tail=3.0, dorsal=1.0)
    els.append(box((13.5, 4.5, 7.5), (16, 5.5, 8.5), tex='face'))                       # меч
    els.append(plate((6, 6.75, 8), (9.5, 10.5, 8), 'sail'))                              # высокий спинной
    return els
def body_round():
    els = []; cy = 5.5
    els.append(box((3.5, cy - 3, 5.5), (10.5, cy + 3, 10.5), 0.0, 0.75))
    els.append(box((10.5, cy - 2, 6.5), (12.5, cy + 2, 9.5), 0.75, 1.0))
    els.append(plate((0.5, cy - 2, 8), (3.5, cy + 2, 8), 'tail'))
    els.append(plate((5, cy + 3, 8), (8.5, cy + 4.5, 8), 'dorsal'))
    for s in (-1, 1): els.append(plate((9, cy - 0.5, 8 + s * 2.5), (11, cy + 1, 8 + s * 2.5), 'pect', rot={'origin': [11, cy, 8 + s * 2.5], 'axis': 'y', 'angle': 22.5 * s}))
    return els
def body_mola():
    els = []; cy = 6.0
    els.append(box((3, cy - 4, 7), (11, cy + 4, 9), 0.0, 1.0))
    els.append(plate((6, cy + 4, 8), (9, cy + 8, 8), 'sail')); els.append(plate((6, cy - 8, 8), (9, cy - 4, 8), 'sail'))
    els.append(plate((1.5, cy - 3, 8), (3, cy + 3, 8), 'tail'))
    return els
def body_flat():
    els = []; cy = 4.0
    els.append(box((3, cy - 0.5, 4), (12, cy + 0.5, 12), 0.0, 1.0))
    els.append(plate((0.5, cy, 5.5), (3, cy, 10.5), 'tail'))
    return els
def body_kraken():
    els = []; cy = 9.0
    els.append(box((5, cy - 3, 5), (11, cy + 3.5, 11), 0.0, 1.0))
    for i in range(8):
        ang = i * math.pi / 4; x = 8 + math.cos(ang) * 2.2; z = 8 + math.sin(ang) * 2.2
        els.append(box((x - 0.5, cy - 3 - 5, z - 0.5), (x + 0.5, cy - 3, z + 0.5), tex='bot', rot={'origin': [x, cy - 3, z], 'axis': 'x' if i % 2 else 'z', 'angle': 22.5 * (1 if i % 4 < 2 else -1)}))
    return els
def body_dragon():
    els = body_generic(L=8.0, h=3.5, w=2.0, head=2.5, tail=3.0, dorsal=1.0)
    els.append(plate((4.5, 6.75, 8), (10.5, 10.5, 8), 'sail'))
    els.append(plate((11.5, 6.5, 8), (13.5, 9, 8), 'sail'))
    return els
def body_fancy():
    els = body_generic(L=6.0, h=4.5, w=2.5, head=2.0, tail=4.5, forked=False)
    els.append(plate((0, 1.5, 8), (4.5, 8.5, 8), 'sail'))
    return els

BUILD = {'standard': body_standard, 'tall': body_tall, 'small': body_small, 'long': body_long, 'eel': body_eel, 'sword': body_sword,
         'round': body_round, 'mola': body_mola, 'flat': body_flat, 'kraken': body_kraken, 'dragon': body_dragon, 'fancy': body_fancy}
# как у FreshFood: вид сбоку-сверху, крупно
DISPLAY = {"gui": {"rotation": [30, 45, 0], "translation": [0, 1.5, 0], "scale": [1.1, 1.1, 1.1]},
           "ground": {"rotation": [0, 0, 0], "translation": [0, 2, 0], "scale": [0.6, 0.6, 0.6]},
           "fixed": {"rotation": [0, -90, 0], "translation": [0, 2, 0], "scale": [1.1, 1.1, 1.1]},
           "thirdperson_righthand": {"rotation": [0, 90, -20], "translation": [0, 3, 1], "scale": [0.7, 0.7, 0.7]},
           "thirdperson_lefthand": {"rotation": [0, -90, 20], "translation": [0, 3, 1], "scale": [0.7, 0.7, 0.7]},
           "firstperson_righthand": {"rotation": [0, -70, 15], "translation": [1, 3, 0], "scale": [0.7, 0.7, 0.7]},
           "firstperson_lefthand": {"rotation": [0, 70, -15], "translation": [1, 3, 0], "scale": [0.7, 0.7, 0.7]}}

made = []
for f in sorted(os.listdir(SRC)):
    if not f.endswith('.png') or f.startswith('_'): continue
    fid = f[:-4]
    rnd = random.Random(hash(fid) & 0xffff)
    pal = PAL.get(fid, ((120, 140, 170), (190, 210, 230), (250, 250, 250), (160, 180, 210)))
    make_texture(fid, pal, rnd).save(f'{OUT_T}/{fid}.png')
    model = {"credit": "ZenFishing fish_models3d.py (FreshFood style)", "texture_size": [32, 32],
             "textures": {"0": f"zenfishing:item/fish3d/{fid}", "particle": f"zenfishing:item/fish3d/{fid}"},
             "elements": BUILD[KIND.get(fid, 'standard')](), "display": DISPLAY}
    json.dump(model, open(f'{OUT_M}/{fid}.json', 'w'), separators=(',', ':'))
    made.append(fid)
print('models:', len(made))

# ── превью: рендер боксов, затенение как в игре ──
if len(sys.argv) > 4:
    import numpy as np
    def render(fid, S=16, rot_y=45, rot_x=30):
        m = json.load(open(f'{OUT_M}/{fid}.json')); tex = Image.open(f'{OUT_T}/{fid}.png').convert('RGBA')
        ay, ax = math.radians(rot_y + 180), math.radians(rot_x)
        def rotp(pt, rot):
            if not rot: return pt
            ox, oy, oz = rot['origin']; a = math.radians(rot['angle']); x, y, z = pt[0] - ox, pt[1] - oy, pt[2] - oz
            if rot['axis'] == 'z': x, y = x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)
            elif rot['axis'] == 'y': x, z = x * math.cos(a) + z * math.sin(a), -x * math.sin(a) + z * math.cos(a)
            else: y, z = y * math.cos(a) - z * math.sin(a), y * math.sin(a) + z * math.cos(a)
            return (x + ox, y + oy, z + oz)
        def proj(x, y, z):
            x, y, z = x - 8, y - 6, z - 8
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
    close = ['carp', 'perch', 'pike', 'clownfish', 'goldfish', 'tuna', 'sea_dragon', 'koi']
    cl = Image.new('RGBA', (4 * 320, 2 * 320), (54, 72, 92, 255)); dcl = ImageDraw.Draw(cl)
    for i, fid in enumerate(close):
        if fid in made: cl.alpha_composite(render(fid), ((i % 4) * 320, (i // 4) * 320)); dcl.text(((i % 4) * 320 + 8, (i // 4) * 320 + 8), fid, fill=(255, 255, 255, 255))
    cl.save(sys.argv[4].replace('.png', '_close.png'))
    cols = 8; rows = (len(made) + cols - 1) // cols; T = 200
    pv = Image.new('RGBA', (cols * T, rows * T), (54, 72, 92, 255)); dr = ImageDraw.Draw(pv)
    for i, fid in enumerate(made):
        pv.alpha_composite(render(fid).resize((T, T), Image.LANCZOS), ((i % cols) * T, (i // cols) * T)); dr.text(((i % cols) * T + 6, (i // cols) * T + 6), fid, fill=(255, 255, 255, 255))
    pv.save(sys.argv[4]); print('preview ok')
