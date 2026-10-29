"""Тултип «море» v3 — по образцу Simple Tooltips (Rare, синий): скруглённая светло-голубая рамка 2 px с тёмной обводкой,
тёмно-синяя заливка, внутренняя вписанная панель чуть темнее со своей скруглённой кромкой, без декора (v3.1).
Спрайты 160x160 (4x от логических 40x40), nine_slice border 12 (48 px); декор только в угловых тайлах — они не растягиваются.
Запуск: python3 make_sea_tooltip.py OUT_DIR [preview.png]  (MCFONT=путь к mcfont.py — шрифт Minecraft в превью)"""
import sys, os, math
from PIL import Image, ImageDraw

OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
S, B, SC = 160, 48, 4
def px(c, a=255): return c + (a,)
OUTLINE = (14, 52, 88)
RIM, RIM_L, RIM_D = (58, 172, 228), (120, 212, 245), (40, 136, 192)
FILL = (14, 72, 116)
INNER, INNER_RIM = (10, 58, 98), (8, 46, 80)
DECO = (36, 120, 170)

bg = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(bg)
d.rounded_rectangle((0, 0, S - 1, S - 1), radius=3 * SC, fill=px(FILL))
d.rounded_rectangle((3 * SC, 3 * SC, S - 1 - 3 * SC, S - 1 - 3 * SC), radius=2 * SC, fill=px(INNER_RIM))
d.rounded_rectangle((4 * SC, 4 * SC, S - 1 - 4 * SC, S - 1 - 4 * SC), radius=2 * SC, fill=px(INNER))

# без декора в углах (v3.1): чистая панель

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
