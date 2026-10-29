"""Тултип «море» v2 — игровой подводный стиль с пузырьками.
Спрайты 160x160 (4x от логических 40x40), nine_slice border 12 (48 px). Фон: глубокая сине-бирюзовая вода с мягкими
световыми бликами и дизерингом; рама: светлое «стекло» 3 лог. px с тёмной обводкой и скруглёнными углами; в углах — пузырьки
(только в угловых тайлах nine-slice, чтобы не растягивались). Запуск: python3 make_sea_tooltip.py OUT_DIR [preview.png]"""
import sys, os, random, math
from PIL import Image, ImageDraw, ImageFilter

OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
S, B, SC = 160, 48, 4          # размер, бордер nine-slice, масштаб (1 лог. px = 4)
rnd = random.Random(7)

def px(c, a=255): return c + (a,)
DEEP, MID, LIGHT = (10, 36, 72), (16, 62, 110), (26, 96, 150)
GLASS, GLASS_L, GLASS_D, OUTLINE = (74, 196, 230), (190, 244, 255), (36, 130, 190), (6, 22, 48)

# ── фон ──
bg = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(bg); p = bg.load()
for y in range(S):
    k = y / (S - 1)
    c = tuple(int(DEEP[i] * (1 - k) + MID[i] * k) for i in range(3))
    for x in range(S):
        cc = c
        if (x // SC + y // SC) % 7 == 0 and (x // SC) % 3 == 0: cc = tuple(min(255, v + 6) for v in c)   # лёгкий дизер
        p[x, y] = px(cc, 236)
# мягкие световые лучи сверху (широкие прозрачные полосы), только в центральной зоне тянутся — они вертикальные, растяжение по Y безвредно
rays = Image.new('RGBA', (S, S), (0, 0, 0, 0)); rd = ImageDraw.Draw(rays)
for x0 in (30, 74, 118):
    rd.polygon([(x0, 0), (x0 + 14, 0), (x0 + 6, S), (x0 - 4, S)], fill=px(LIGHT, 40))
rays = rays.filter(ImageFilter.GaussianBlur(5))
bg.alpha_composite(rays)
# внутренняя тень у краёв (виньетка) — по рамке
vign = Image.new('RGBA', (S, S), (0, 0, 0, 0)); vd = ImageDraw.Draw(vign)
for i in range(0, 20, SC): vd.rectangle((i, i, S - 1 - i, S - 1 - i), outline=px((0, 0, 0), 26))
bg.alpha_composite(vign.filter(ImageFilter.GaussianBlur(3)))

# слабые пузырьки в углах фона (угловые тайлы не растягиваются; текст их почти не задевает — они бледные)
def faint(cx, cy, r):
    dd = ImageDraw.Draw(bg)
    dd.ellipse((cx - r, cy - r, cx + r, cy + r), outline=px((140, 220, 255), 70))
    dd.point((cx - r // 2, cy - r // 2), fill=px((255, 255, 255), 120))
for (ox, oy) in ((0, 0), (S - B, 0), (0, S - B), (S - B, S - B)):
    for (bx, by, br) in ((7, 8, 1.5), (10, 5, 1.0), (5, 10, 1.0)):
        faint(int(ox + bx * SC), int(oy + by * SC), int(br * SC))

# ── рама ──
fr = Image.new('RGBA', (S, S), (0, 0, 0, 0)); f = ImageDraw.Draw(fr)
def rrect(box, r, fill): f.rounded_rectangle(box, radius=r, fill=fill)
# снаружи внутрь (в логических px): 0 обводка, 1-2 стекло, 3 тёмная внутренняя кромка
rrect((0, 0, S - 1, S - 1), 3 * SC, px(OUTLINE))
rrect((SC, SC, S - 1 - SC, S - 1 - SC), 2 * SC, px(GLASS))
rrect((3 * SC, 3 * SC, S - 1 - 3 * SC, S - 1 - 3 * SC), SC, px(GLASS_D))
rrect((4 * SC, 4 * SC, S - 1 - 4 * SC, S - 1 - 4 * SC), SC, (0, 0, 0, 0))
# блик по верхней и левой грани стекла, тень по нижней и правой
f.rectangle((2 * SC, SC, S - 1 - 3 * SC, SC + SC - 1), fill=px(GLASS_L))
f.rectangle((SC, 2 * SC, SC + SC - 1, S - 1 - 3 * SC), fill=px(GLASS_L))
f.rectangle((3 * SC, S - 1 - 2 * SC, S - 1 - 2 * SC, S - 1 - SC), fill=px(GLASS_D))
f.rectangle((S - 1 - 2 * SC, 3 * SC, S - 1 - SC, S - 1 - 2 * SC), fill=px(GLASS_D))

def bubble(img, cx, cy, r, a=200):
    """пузырёк: полупрозрачная заливка, светлое кольцо, блик слева-сверху, 1-px тёмная обводка"""
    dd = ImageDraw.Draw(img)
    dd.ellipse((cx - r, cy - r, cx + r, cy + r), fill=px((120, 220, 255), 70), outline=px(OUTLINE, a))
    dd.ellipse((cx - r + SC, cy - r + SC, cx + r - SC, cy + r - SC), outline=px(GLASS_L, a))
    hl = max(SC, r // 3)
    dd.ellipse((cx - r // 2 - hl // 2, cy - r // 2 - hl // 2, cx - r // 2 + hl // 2, cy - r // 2 + hl // 2), fill=px((255, 255, 255), a))

# пузырьки в угловых тайлах (внутри B×B, не заходя на центр): у каждого угла своя группа
corners = {'tl': (0, 0), 'tr': (S - B, 0), 'bl': (0, S - B), 'br': (S - B, S - B)}
# пузырьки сидят на самой раме (внешние 0..5 лог. px), чтобы не перекрывать текст: (x, y) в лог. px от угла, r — радиус в лог. px
groups = {'tl': [(2.5, 2.5, 2.5), (7, 1.5, 1.2), (1.5, 7, 1.2)], 'tr': [(9.5, 2.5, 2.5), (4.5, 1.5, 1.2), (10.5, 7.5, 1.2)],
          'bl': [(2.5, 9.5, 2.5), (7, 10.5, 1.2), (1.5, 5, 1.2)], 'br': [(9.5, 9.5, 2.5), (4.5, 10.5, 1.2), (10.5, 4.5, 1.2)]}
for key, (ox, oy) in corners.items():
    for (bx, by, br) in groups[key]:
        bubble(fr, int(ox + bx * SC), int(oy + by * SC), int(br * SC))

bg.save(f'{OUT}/sea_background.png'); fr.save(f'{OUT}/sea_frame.png')
meta = '{"gui": {"scaling": {"type": "nine_slice", "width": 40, "height": 40, "border": 12}}}'
open(f'{OUT}/sea_background.png.mcmeta', 'w').write(meta); open(f'{OUT}/sea_frame.png.mcmeta', 'w').write(meta)
print('tooltip ok')

# ── превью ──
if len(sys.argv) > 2:
    def nine(img, w, h):
        out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        parts = {'tl': (0, 0, B, B), 'tr': (S - B, 0, S, B), 'bl': (0, S - B, B, S), 'br': (S - B, S - B, S, S),
                 't': (B, 0, S - B, B), 'b': (B, S - B, S - B, S), 'l': (0, B, B, S - B), 'r': (S - B, B, S, S - B), 'c': (B, B, S - B, S - B)}
        g = {k: img.crop(v) for k, v in parts.items()}
        out.alpha_composite(g['tl'], (0, 0)); out.alpha_composite(g['tr'], (w - B, 0)); out.alpha_composite(g['bl'], (0, h - B)); out.alpha_composite(g['br'], (w - B, h - B))
        out.alpha_composite(g['t'].resize((w - 2 * B, B)), (B, 0)); out.alpha_composite(g['b'].resize((w - 2 * B, B)), (B, h - B))
        out.alpha_composite(g['l'].resize((B, h - 2 * B)), (0, B)); out.alpha_composite(g['r'].resize((B, h - 2 * B)), (w - B, B))
        out.alpha_composite(g['c'].resize((w - 2 * B, h - 2 * B)), (B, B))
        return out
    sys.path.insert(0, os.environ.get('MCFONT', ''))
    try:
        import mcfont
        def text(img, x, y, t, col): mcfont.draw(img, x, y, t, color=col, scale=SC)
        def tw(t): return mcfont.width(t, SC)
    except Exception:
        from PIL import ImageFont
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 8 * SC)
        def text(img, x, y, t, col): ImageDraw.Draw(img).text((x, y), t, font=font, fill=col)
        def tw(t): return int(font.getlength(t))
    samples = [[('🎣 Удочка [ур. 12]', '#55ffff'), ('Опыт: 340/1164', '#aaaaaa'), ('Удача: +16% (2)', '#aaaaaa'), ('Клёв: +12% (2)', '#aaaaaa'), ('Свободных очков: 3', '#ffff55')],
               [('Золотой карп', '#aa00aa')], [('🕸 Рыболовная сеть', '#55ffff'), ('ПКМ по 4 блокам или воде — углы сети', '#aaaaaa'), ('Ловит рыбу сама, пока ты занят', '#aaaaaa')]]
    canvas = Image.new('RGBA', (1500, 300), (76, 110, 60, 255)); x0 = 20
    for lines in samples:
        w = max(2 * B + SC, max(tw(t) for t, _ in lines) + 2 * 6 * SC); h = max(2 * B + SC, (len(lines) * 10 + 2) * SC + 2 * 4 * SC)
        tip = Image.alpha_composite(nine(bg, w, h), nine(fr, w, h))
        for i, (t, c) in enumerate(lines): text(tip, 6 * SC, (5 + i * 10 + (2 if i else 0)) * SC, t, c)
        canvas.alpha_composite(tip, (x0, 20)); x0 += w + 20
    canvas.save(sys.argv[2]); print('preview ok')
