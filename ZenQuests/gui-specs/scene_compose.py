"""Сборка HD-сцены амбара 472x270 (2 px текстуры на 1 px интерфейса) из отдельных частей:
стена (тайл) с виньеткой и тёплым светом фонарей -> балка -> столбы с тенью на стене -> гирлянды -> записки ->
кусты (задний план) -> бочка/мешок -> сено -> тыквы (передний план). У каждой части — мягкая тень на стене
и контактная тень снизу, свет сверху-слева."""
import sys, os
from PIL import Image, ImageFilter, ImageDraw, ImageChops

A = os.path.dirname(os.path.abspath(__file__)); OUT = sys.argv[1]
W, H = 472, 478          # всё окно: 239 GUI px (17 верх + 222)
G = 2                       # px текстуры на 1 px интерфейса

def load(n, gw=None, gh=None):
    im = Image.open(f'{A}/raw/{n}.png').convert('RGBA')
    if gw: s = gw * G / im.width
    else: s = gh * G / im.height
    im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
    # жёсткая альфа — пиксель-арт без полупрозрачных краёв
    r, g, b, a = im.split(); a = a.point(lambda v: 255 if v > 110 else 0); im.putalpha(a)
    return im

scene = Image.new('RGBA', (W, H), (0, 0, 0, 255))
# ── стена: тайл + виньетка ──
wall = Image.open(f'{A}/wall_full.png').convert('RGB')
tile = wall.resize((236, 236), Image.LANCZOS)
for y in range(0, H, 236):
    for x in range(0, W, 236): scene.paste(tile, (x, y))
vig = Image.new('L', (W, H), 0); d = ImageDraw.Draw(vig)
for i in range(60):                    # затемнение к краям и низу
    k = int(255 * (i / 60) ** 1.6)
    d.rectangle([i, i, W - 1 - i, H - 1 - i + 30], outline=k)
vig = vig.filter(ImageFilter.GaussianBlur(14))
dark = Image.new('RGBA', (W, H), (20, 10, 4, 255)); dark.putalpha(vig.point(lambda v: int((255 - v) * 0.55)))
scene.alpha_composite(dark)

def shadow(sprite, pos, off=(5, 6), alpha=110, blur=4):
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0)); m = sprite.split()[3]
    sh.paste(Image.new('RGBA', sprite.size, (15, 6, 2, alpha)), (pos[0] + off[0], pos[1] + off[1]), m)
    scene.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))

def contact(cx, bottom, w, h=8, alpha=130):
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ImageDraw.Draw(sh).ellipse([cx - w // 2, bottom - h // 2, cx + w // 2, bottom + h // 2], fill=(10, 4, 0, alpha))
    scene.alpha_composite(sh.filter(ImageFilter.GaussianBlur(3)))

def put(sprite, pos, sh=True, **kw):
    if sh: shadow(sprite, pos, **kw)
    scene.alpha_composite(sprite, pos)

def glow(cx, cy, r, color=(255, 190, 90), alpha=95):
    gl = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ImageDraw.Draw(gl).ellipse([cx - r, cy - r, cx + r, cy + r], fill=color + (alpha,))
    scene.alpha_composite(gl.filter(ImageFilter.GaussianBlur(r // 2)))

# ── свет фонарей на стене (до самих фонарей) ──
glow(52, 70, 70); glow(W - 52, 70, 70)
# ── верхняя балка ──
beam = load('beam', gw=236); beam = beam.resize((W, beam.height), Image.LANCZOS)
put(beam, (0, -2), off=(0, 6), alpha=140)
# ── пол внизу и балка-перекладина между доской квестов и инвентарём (GUI y 131..137) ──
floor = beam.resize((W, 22), Image.LANCZOS); put(floor, (0, H - 22), off=(0, -5), alpha=120)
mid = beam.resize((W, 14), Image.LANCZOS); put(mid, (0, 262), off=(0, 6), alpha=140)
# ── столбы ──
post = load('post', gh=245)
post = post.resize((28, post.height), Image.LANCZOS)                 # столб 14 GUI px шириной, во всю высоту
r_, g_, b_, a_ = post.split(); post.putalpha(a_.point(lambda v: 255 if v > 110 else 0))
for x in (6, W - 6 - post.width):
    put(post, (x, -6), off=(8, 0), alpha=130, blur=6)
# ── гирлянды по верхним углам, под балкой ──
gar = load('garland', gw=100)
put(gar, (34, 12), off=(3, 6), alpha=100); put(gar.transpose(Image.FLIP_LEFT_RIGHT), (W - 34 - gar.width, 12), off=(3, 6), alpha=100)
# ── фонари на столбах ──
lan = load('lantern', gh=36)
put(lan, (6 + post.width - 4, 10), off=(6, 8), alpha=120); put(lan, (W - 6 - post.width - lan.width + 4, 10), off=(6, 8), alpha=120)
# ── верёвка и серп на правом столбе, записки ──
rope = load('rope', gh=26); put(rope, (W - 56, 86), off=(3, 5))
sick = load('sickle', gh=28); put(sick, (26, 84), off=(3, 5))
note = load('note', gh=22); put(note, (14, 52), off=(2, 4)); put(note, (W - 14 - note.width, 52), off=(2, 4))
# ── низ: кусты (задний план) ──
bush = load('bush', gw=46)
for x in (-6, 40, W - 40 - bush.width, W - 6 - bush.width):
    contact(x + bush.width // 2, H - 20, bush.width + 10); put(bush, (x, H - 20 - bush.height + 6), off=(4, 5), alpha=90)
# ── бочка слева, мешок справа (средний план) ──
bar = load('barrel', gh=56); contact(2 + bar.width // 2, H - 18, bar.width); put(bar, (2, H - 18 - bar.height), off=(6, 4))
sack = load('sack', gh=48); contact(W - 8 - sack.width // 2, H - 18, sack.width); put(sack, (W - 8 - sack.width, H - 18 - sack.height), off=(6, 4))
# ── сено ──
hay = load('hay', gw=58)
contact(24 + hay.width // 2, H - 14, hay.width); put(hay, (24, H - 14 - hay.height), off=(6, 5))
contact(W - 24 - hay.width // 2, H - 14, hay.width); put(hay.transpose(Image.FLIP_LEFT_RIGHT), (W - 24 - hay.width, H - 14 - hay.height), off=(6, 5))
# ── тыквы (передний план) ──
pum = load('pumpkin', gw=32)
contact(40 + pum.width // 2, H - 10, pum.width); put(pum, (40, H - 10 - pum.height), off=(5, 4))
contact(W - 44 - pum.width // 2, H - 10, pum.width); put(pum, (W - 44 - pum.width, H - 10 - pum.height), off=(5, 4))

q = scene.convert('RGB').quantize(colors=96, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert('RGBA')
q.save(f'{OUT}/barn_hd.png')
os.makedirs(f'{OUT}/scene', exist_ok=True)
for n, b in {'scene_tl': (0, 0, 236, 136), 'scene_tr': (236, 0, 472, 136), 'scene_bl': (0, 136, 236, 270), 'scene_br': (236, 136, 472, 270)}.items():
    q.crop(b).save(f'{OUT}/scene/{n}.png')
print('scene ok', q.size)
