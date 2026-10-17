"""Сцена рыбацкого сарая 472x478 (2 px текстуры на 1 px интерфейса) из частей (art/parts, Figma AI):
стена из выцветших сине-зелёных досок с виньеткой и холодным светом фонарей -> балка -> столбы -> сети по верхним
углам -> фонари, буи, записки, связка рыбы, якорь -> камыш (задний план) -> ящик с рыбой, бухта верёвки ->
спасательный круг (передний план). Та же схема, что у амбара квестов, только синяя и рыбацкая."""
import sys, os
from PIL import Image, ImageFilter, ImageDraw, ImageChops

A = os.path.dirname(os.path.abspath(__file__)); OUT = sys.argv[1]
W, H = 472, 478
G = 2

def load(n, gw=None, gh=None):
    im = Image.open(f'{A}/art/parts/{n}.png').convert('RGBA')
    s = gw * G / im.width if gw else gh * G / im.height
    im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
    r, g, b, a = im.split(); a = a.point(lambda v: 255 if v > 110 else 0); im.putalpha(a)
    return im

scene = Image.new('RGBA', (W, H), (0, 0, 0, 255))
wall = Image.open(f'{A}/art/wall_full.png').convert('RGB')
tile = wall.resize((236, 236), Image.LANCZOS)
for y in range(0, H, 236):
    for x in range(0, W, 236): scene.paste(tile, (x, y))
# холодная виньетка к краям и низу
vig = Image.new('L', (W, H), 0); d = ImageDraw.Draw(vig)
for i in range(60):
    k = int(255 * (i / 60) ** 1.6)
    d.rectangle([i, i, W - 1 - i, H - 1 - i + 30], outline=k)
vig = vig.filter(ImageFilter.GaussianBlur(14))
dark = Image.new('RGBA', (W, H), (6, 14, 30, 255)); dark.putalpha(vig.point(lambda v: int((255 - v) * 0.6)))
scene.alpha_composite(dark)

def shadow(sprite, pos, off=(5, 6), alpha=110, blur=4):
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0)); m = sprite.split()[3]
    sh.paste(Image.new('RGBA', sprite.size, (4, 10, 22, alpha)), (pos[0] + off[0], pos[1] + off[1]), m)
    scene.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))
def contact(cx, bottom, w, h=8, alpha=130):
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ImageDraw.Draw(sh).ellipse([cx - w // 2, bottom - h // 2, cx + w // 2, bottom + h // 2], fill=(2, 6, 14, alpha))
    scene.alpha_composite(sh.filter(ImageFilter.GaussianBlur(3)))
def put(sprite, pos, sh=True, **kw):
    if sh: shadow(sprite, pos, **kw)
    scene.alpha_composite(sprite, pos)
def glow(cx, cy, r, color=(255, 200, 120), alpha=90):
    gl = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ImageDraw.Draw(gl).ellipse([cx - r, cy - r, cx + r, cy + r], fill=color + (alpha,))
    scene.alpha_composite(gl.filter(ImageFilter.GaussianBlur(r // 2)))

glow(52, 70, 70); glow(W - 52, 70, 70)
beam = load('beam', gw=236); beam = beam.resize((W, beam.height), Image.LANCZOS)
put(beam, (0, -2), off=(0, 6), alpha=140)
floor = beam.resize((W, 22), Image.LANCZOS); put(floor, (0, H - 22), off=(0, -5), alpha=120)
mid = beam.resize((W, 14), Image.LANCZOS); put(mid, (0, 262), off=(0, 6), alpha=140)
post = load('post', gh=245); post = post.resize((28, post.height), Image.LANCZOS)
r_, g_, b_, a_ = post.split(); post.putalpha(a_.point(lambda v: 255 if v > 110 else 0))
for x in (6, W - 6 - post.width): put(post, (x, -6), off=(8, 0), alpha=130, blur=6)
# сети по верхним углам
net = load('net', gw=70)
put(net, (30, 8), off=(3, 6), alpha=100); put(net.transpose(Image.FLIP_LEFT_RIGHT), (W - 30 - net.width, 8), off=(3, 6), alpha=100)
# фонари на столбах
lan = load('lantern', gh=38)
put(lan, (6 + post.width - 4, 12), off=(6, 8), alpha=120); put(lan, (W - 6 - post.width - lan.width + 4, 12), off=(6, 8), alpha=120)
# буй и связка рыбы на столбах, записки, якорь
buoy = load('buoy', gh=34); put(buoy, (W - 54, 86), off=(3, 5))
fl = load('fishline', gw=44); put(fl, (12, 86), off=(3, 5))
note = load('note', gh=20); put(note, (14, 56), off=(2, 4)); put(note, (W - 14 - note.width, 56), off=(2, 4))
anc = load('anchor', gh=46); put(anc, (W - 52, 150), off=(4, 5))
# низ: камыш (задний план)
reed = load('reeds', gh=60)
for x in (-8, 24, W - 24 - reed.width, W - 4 - reed.width):
    contact(x + reed.width // 2, H - 18, reed.width); put(reed, (x, H - 18 - reed.height + 6), off=(4, 5), alpha=90)
# ящик слева, бухта верёвки справа
crate = load('crate', gw=52); contact(2 + crate.width // 2, H - 16, crate.width); put(crate, (2, H - 16 - crate.height), off=(6, 4))
rope = load('rope', gw=46); contact(W - 8 - rope.width // 2, H - 14, rope.width); put(rope, (W - 8 - rope.width, H - 14 - rope.height), off=(6, 4))
# спасательный круг (передний план)
ring = load('lifebuoy', gw=38); contact(W - 40 - ring.width // 2, H - 10, ring.width); put(ring, (W - 40 - ring.width, H - 10 - ring.height), off=(5, 4))
buoy2 = load('buoy', gh=30); contact(44 + buoy2.width // 2, H - 10, buoy2.width); put(buoy2, (44, H - 10 - buoy2.height), off=(5, 4))

q = scene.convert('RGB').quantize(colors=96, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert('RGBA')
q.save(f'{OUT}/pier_hd.png')
os.makedirs(f'{OUT}/scene', exist_ok=True)
for n, b in {'scene_tl': (0, 0, 236, 240), 'scene_tr': (236, 0, 472, 240), 'scene_bl': (0, 240, 236, 478), 'scene_br': (236, 240, 472, 478)}.items():
    q.crop(b).save(f'{OUT}/scene/{n}.png')
print('scene ok', q.size)
