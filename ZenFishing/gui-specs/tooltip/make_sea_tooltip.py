"""Тултип «море» v3 — по образцу Simple Tooltips (Rare, синий): скруглённая светло-голубая рамка 2 px с тёмной обводкой,
тёмно-синяя заливка, внутренняя вписанная панель чуть темнее со своей скруглённой кромкой, завитки-волны и пузырьки в углах.
Спрайты 160x160 (4x от логических 40x40), nine_slice border 12 (48 px); декор только в угловых тайлах — они не растягиваются.
Запуск: python3 make_sea_tooltip.py OUT_DIR [preview.png]  (MCFONT=путь к mcfont.py — шрифт Minecraft в превью)"""
import sys, os, math
from PIL import Image, ImageDraw

OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
S, B, SC = 160, 48, 4
def px(c, a=255): return c + (a,)
OUTLINE = (6, 30, 56)
RIM, RIM_L, RIM_D = (44, 150, 206), (120, 206, 240), (28, 110, 164)
FILL = (14, 72, 116)
INNER, INNER_RIM = (10, 58, 98), (8, 46, 80)
DECO = (36, 120, 170)

bg = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(bg)
d.rounded_rectangle((0, 0, S - 1, S - 1), radius=3 * SC, fill=px(FILL))
d.rounded_rectangle((3 * SC, 3 * SC, S - 1 - 3 * SC, S - 1 - 3 * SC), radius=2 * SC, fill=px(INNER_RIM))
d.rounded_rectangle((4 * SC, 4 * SC, S - 1 - 4 * SC, S - 1 - 4 * SC), radius=2 * SC, fill=px(INNER))

def swirl(img, cx, cy, r, col, turns=1.6, flip=1):
    dd = ImageDraw.Draw(img); pts = []; n = 40
    for i in range(n):
        t = i / (n - 1); a = t * turns * 2 * math.pi * flip; rr = r * (0.15 + 0.85 * t)
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    dd.line(pts, fill=px(col, 200), width=SC)
def bubble(img, cx, cy, r, col):
    dd = ImageDraw.Draw(img)
    dd.ellipse((cx - r, cy - r, cx + r, cy + r), outline=px(col, 220), width=SC)
    dd.rectangle((cx - r // 2, cy - r // 2, cx - r // 2 + SC - 1, cy - r // 2 + SC - 1), fill=px((200, 240, 255), 230))

# декор в углах внутренней панели: завиток ближе к углу, пузырёк рядом
for (ox, oy, fx, fy) in ((0, 0, 1, 1), (S - B, 0, -1, 1), (0, S - B, 1, -1), (S - B, S - B, -1, -1)):
    cx = ox + (7 * SC if fx > 0 else B - 7 * SC); cy = oy + (7 * SC if fy > 0 else B - 7 * SC)
    swirl(bg, cx, cy, 2.2 * SC, DECO, flip=fx * fy)
    bubble(bg, ox + (10 * SC if fx > 0 else B - 10 * SC), oy + (5 * SC if fy > 0 else B - 5 * SC), SC, DECO)

fr = Image.new('RGBA', (S, S), (0, 0, 0, 0)); f = ImageDraw.Draw(fr)
f.rounded_rectangle((0, 0, S - 1, S - 1), radius=3 * SC, fill=px(OUTLINE))
f.rounded_rectangle((SC, SC, S - 1 - SC, S - 1 - SC), radius=2 * SC, fill=px(RIM))
f.rounded_rectangle((3 * SC, 3 * SC, S - 1 - 3 * SC, S - 1 - 3 * SC), radius=SC, fill=(0, 0, 0, 0))
f.rectangle((3 * SC, SC, S - 1 - 3 * SC, 2 * SC - 1), fill=px(RIM_L))
f.rectangle((SC, 3 * SC, 2 * SC - 1, S - 1 - 3 * SC), fill=px(RIM_L))
f.rectangle((3 * SC, S - 2 * SC, S - 1 - 3 * SC, S - 1 - SC), fill=px(RIM_D))
f.rectangle((S - 2 * SC, 3 * SC, S - 1 - SC, S - 1 - 3 * SC), fill=px(RIM_D))

bg.save(f'{OUT}/sea_background.png'); fr.save(f'{OUT}/sea_frame.png')
meta = '{"gui": {"scaling": {"type": "nine_slice", "width": 40, "height": 40, "border": 12}}}'
open(f'{OUT}/sea_background.png.mcmeta', 'w').write(meta); open(f'{OUT}/sea_frame.png.mcmeta', 'w').write(meta)
print('tooltip ok')

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
               [('Золотой карп', '#aa00aa')], [('🕸 Рыболовная сеть', '#55ffff'), ('ПКМ по 4 блокам или воде', '#aaaaaa'), ('Ловит рыбу сама', '#aaaaaa')]]
    canvas = Image.new('RGBA', (1240, 300), (196, 196, 196, 255)); x0 = 20
    for lines in samples:
        w = max(2 * B + SC, max(tw(t) for t, _ in lines) + 2 * 6 * SC); h = max(2 * B + SC, (len(lines) * 10 + 2) * SC + 2 * 4 * SC)
        tip = Image.alpha_composite(nine(bg, w, h), nine(fr, w, h))
        for i, (t, c) in enumerate(lines): text(tip, 6 * SC, (5 + i * 10 + (2 if i else 0)) * SC, t, c)
        canvas.alpha_composite(tip, (x0, 20)); x0 += w + 20
    canvas.save(sys.argv[2]); print('preview ok')
