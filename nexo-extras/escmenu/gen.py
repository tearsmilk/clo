"""Esc-меню (пауза) и экраны настроек в стиле фермы: деревянные кнопки, слайдеры, фоны и разделители.
HD: 2 px текстуры на 1 px интерфейса (nine_slice width/height задают логический размер)."""
import sys, os, json
sys.path.insert(0, os.path.expanduser('~/.claude/skills/minecraft-nexo-gui/scripts'))
from PIL import Image, ImageDraw
import art, pixfont
from art import rgba, step, base
import random

def planks(w, h, color, vertical=False, board=16, seed=1, span=(44, 72), grain=9):
    """Длинные доски: светлая кромка сверху, тёмный шов снизу, редкие прожилки, стыки со сдвигом."""
    if vertical: return planks(h, w, color, False, board, seed, span, grain).transpose(Image.Transpose.ROTATE_90)
    rnd = random.Random(seed)
    b0, lt, dk, dk2 = rgba(base(color)), rgba(step(color, 1)), rgba(step(color, -1)), rgba(step(color, -2))
    im = Image.new('RGBA', (w, h), b0); px = im.load()
    for row, y0 in enumerate(range(0, h, board)):
        y1 = min(h, y0 + board)
        for x in range(w):
            px[x, y0] = lt
            if y1 - 1 > y0: px[x, y1 - 1] = dk2
            if y1 - 2 > y0: px[x, y1 - 2] = dk
        for _ in range(max(1, w * (y1 - y0) // (board * grain))):
            gy = rnd.randint(y0 + 2, max(y0 + 2, y1 - 4)); gx = rnd.randint(0, w - 1)
            for x in range(gx, min(w, gx + rnd.randint(6, 14))):
                if x % 7: px[x, gy] = dk
        jx = (row * 29 + rnd.randint(0, 20)) % rnd.randint(*span)
        while jx < w:
            for y in range(y0 + 1, y1 - 2):
                px[jx, y] = dk2
                if jx + 1 < w: px[jx + 1, y] = lt
            jx += rnd.randint(*span)
    return im

OUT = sys.argv[1]
W_ = f'{OUT}/pack/assets/minecraft/textures/gui'
os.makedirs(f'{W_}/sprites/widget', exist_ok=True)
G = 2
WOOD, WOOD_LT, GREY = '#b86f50', '#c98258', '#7a6a62'
OUT_C, GOLD = '#3e2731', '#e3b24f'

def mcmeta(path, w, h, b):
    json.dump({"gui": {"scaling": {"type": "nine_slice", "width": w, "height": h,
              "border": {"left": b, "top": b, "right": b, "bottom": b}}}}, open(path + '.mcmeta', 'w'))

def wood_button(w, h, color, rim=None, inner_line=None, glow=None, pressed=False):
    """Кнопка: тёмный контур со срезанными углами, кант (свет сверху-слева), доски горизонтально."""
    rim = rim or color
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w - 1, h - 1), fill=rgba(OUT_C))
    # кант
    d.rectangle((G, G, w - 1 - G, h - 1 - G), fill=rgba(base(rim)))
    d.rectangle((G, G, w - 1 - G, 2 * G - 1), fill=rgba(step(rim, 1)))
    d.rectangle((G, G, 2 * G - 1, h - 1 - G), fill=rgba(step(rim, 1)))
    d.rectangle((G, h - 2 * G, w - 1 - G, h - 1 - G), fill=rgba(step(rim, -1)))
    d.rectangle((w - 2 * G, G, w - 1 - G, h - 1 - G), fill=rgba(step(rim, -1)))
    # тёмная внутренняя линия + доски
    d.rectangle((2 * G, 2 * G, w - 1 - 2 * G, h - 1 - 2 * G), fill=rgba(inner_line or step(color, -3)))
    pl = planks(w - 6 * G, h - 6 * G, color, board=(h - 6 * G) // 2, seed=5)
    im.paste(pl, (3 * G, 3 * G))
    if glow:   # тёплая подсветка по верхнему краю досок при наведении
        d.rectangle((3 * G, 3 * G, w - 1 - 3 * G, 3 * G + G - 1), fill=rgba(glow))
    for cx, cy in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):   # срезанные углы (1 GUI px)
        d.rectangle((cx - G + 1 if cx else 0, cy - G + 1 if cy else 0, cx if cx else G - 1, cy if cy else G - 1), fill=(0, 0, 0, 0))
    return im

def well(w, h, inner='#3e2731'):
    """Углубление для слайдера: контур, тень сверху-слева, свет снизу-справа."""
    im = Image.new('RGBA', (w, h), rgba(step(inner, -1))); d = ImageDraw.Draw(im)
    d.rectangle((G, G, w - 1 - G, h - 1 - G), fill=rgba(base(inner)))
    d.rectangle((G, G, w - 1 - G, 2 * G - 1), fill=rgba(step(inner, -1)))
    d.rectangle((G, G, 2 * G - 1, h - 1 - G), fill=rgba(step(inner, -1)))
    d.rectangle((2 * G, h - 2 * G, w - 1 - G, h - 1 - G), fill=rgba(step(inner, 1)))
    d.rectangle((w - 2 * G, 2 * G, w - 1 - G, h - 1 - G), fill=rgba(step(inner, 1)))
    for cx, cy in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        d.rectangle((cx - G + 1 if cx else 0, cy - G + 1 if cy else 0, cx if cx else G - 1, cy if cy else G - 1), fill=(0, 0, 0, 0))
    return im

BW, BH = 200 * G, 20 * G
sp = f'{W_}/sprites/widget'
wood_button(BW, BH, WOOD).save(f'{sp}/button.png')
wood_button(BW, BH, WOOD_LT, rim=GOLD, inner_line='#8a4d2a', glow='#e4a070').save(f'{sp}/button_highlighted.png')
wood_button(BW, BH, GREY).save(f'{sp}/button_disabled.png')
for n in ('button', 'button_highlighted', 'button_disabled'): mcmeta(f'{sp}/{n}.png', 200, 20, 5)
# слайдеры (настройки): дорожка — углубление, ручка — узкая деревянная кнопка
well(BW, BH).save(f'{sp}/slider.png'); well(BW, BH, inner='#4a3038').save(f'{sp}/slider_highlighted.png')
wood_button(8 * G, BH, WOOD).save(f'{sp}/slider_handle.png')
wood_button(8 * G, BH, WOOD_LT, rim=GOLD, inner_line='#8a4d2a').save(f'{sp}/slider_handle_highlighted.png')
for n in ('slider', 'slider_highlighted'): mcmeta(f'{sp}/{n}.png', 200, 20, 4)
for n in ('slider_handle', 'slider_handle_highlighted'): mcmeta(f'{sp}/{n}.png', 8, 20, 3)

# фоны: тайл 32x32 GUI px (текстура 64x64), доски вертикально, тёмные
def bg(color, alpha, board=16, seed=3):
    t = planks(64, 64, color, vertical=True, board=board, seed=seed, span=(40, 64), grain=14)
    t.putalpha(alpha); return t
def sep(color):   # разделитель 32x2 GUI px: тёмная и светлая линия (балка)
    im = Image.new('RGBA', (64, 4), rgba(step(color, -3))); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 63, 1), fill=rgba(step(color, 1))); return im
bg('#5a3a2e', 225).save(f'{W_}/inworld_menu_background.png')
bg('#3e2731', 235, board=16, seed=7).save(f'{W_}/inworld_menu_list_background.png')
sep('#b86f50').save(f'{W_}/inworld_header_separator.png'); sep('#b86f50').save(f'{W_}/inworld_footer_separator.png')
bg('#6a4636', 255).save(f'{W_}/menu_background.png')
bg('#4a2e34', 255, seed=7).save(f'{W_}/menu_list_background.png')
sep('#b86f50').save(f'{W_}/header_separator.png'); sep('#b86f50').save(f'{W_}/footer_separator.png')

# ── превью паузы (как в игре, GUI scale 2) ──
S = 2; PW, PH = 427 * S, 240 * S
pv = Image.new('RGBA', (PW, PH)); px = pv.load()
for y in range(PH):   # «мир» + тёмный градиент как в игре
    for x in range(PW):
        k = y / PH; px[x, y] = (int(80 * (1 - k) + 40 * k), int(140 * (1 - k) + 70 * k), int(60 * (1 - k) + 30 * k), 255)
pv.alpha_composite(Image.new('RGBA', (PW, PH), (16, 16, 16, 205)))
def place(img, lx, ly, text, dis=False):
    pv.alpha_composite(img.resize((img.width // G * S, img.height // G * S), Image.NEAREST), (lx * S, ly * S))
    pixfont.draw_text(pv, (lx + img.width // G // 2) * S - pixfont.text_width(text, scale=S) // 2, (ly + 6) * S, text, '#a0a0a0' if dis else '#ffffff', scale=S, shadow='#3f3f3f')
btn = Image.open(f'{sp}/button.png'); hl = Image.open(f'{sp}/button_highlighted.png'); dis = Image.open(f'{sp}/button_disabled.png')
half = lambda im: im.crop((0, 0, 98 * G, BH)).copy()
pixfont.draw_text(pv, PW // 2 - pixfont.text_width('Game Menu', scale=S) // 2, 40 * S, 'Game Menu', '#ffffff', scale=S, shadow='#3f3f3f')
cx = 427 // 2 - 100; y0 = 240 // 4 + 8
place(btn, cx, y0, 'Back to Game'); place(half(btn), cx, y0 + 24, 'Advancements'); place(half(hl), cx + 102, y0 + 24, 'Statistics')
place(half(dis), cx, y0 + 48, 'Give Feedback', True); place(half(btn), cx + 102, y0 + 48, 'Report Bugs')
place(half(btn), cx, y0 + 72, 'Options...'); place(half(btn), cx + 102, y0 + 72, 'Open to LAN')
place(btn, cx, y0 + 96, 'Save and Quit to Title')
pv.save(f'{OUT}/preview_pause.png')
# превью настроек в мире: фон, разделители, слайдер
op = Image.new('RGBA', (PW, PH)); bgim = Image.open(f'{W_}/inworld_menu_background.png').resize((32 * S, 32 * S), Image.NEAREST)
for y in range(0, PH, 32 * S):
    for x in range(0, PW, 32 * S): op.alpha_composite(bgim, (x, y))
lst = Image.open(f'{W_}/inworld_menu_list_background.png').resize((32 * S, 32 * S), Image.NEAREST)
for y in range(33 * S, (240 - 33) * S, 32 * S):
    for x in range(0, PW, 32 * S): op.alpha_composite(lst.crop((0, 0, 32 * S, min(32 * S, (240 - 33) * S - y))), (x, y))
hs = Image.open(f'{W_}/inworld_header_separator.png').resize((32 * S, 2 * S), Image.NEAREST)
for x in range(0, PW, 32 * S): op.alpha_composite(hs, (x, 33 * S)); op.alpha_composite(hs, (x, (240 - 33) * S))
pv = op
pixfont.draw_text(pv, PW // 2 - pixfont.text_width('Options', scale=S) // 2, 15 * S, 'Options', '#ffffff', scale=S, shadow='#3f3f3f')
sl = Image.open(f'{sp}/slider.png'); sh = Image.open(f'{sp}/slider_handle.png'); shh = Image.open(f'{sp}/slider_handle_highlighted.png')
place(half(sl), cx, 50, 'FOV: 90'); pv.alpha_composite(sh.resize((8 * S, 20 * S), Image.NEAREST), ((cx + 60) * S, 50 * S))
place(half(hl), cx + 102, 50, 'Realms Notifications'); place(half(btn), cx, 74, 'Skin Customization...'); place(half(btn), cx + 102, 74, 'Music & Sounds...')
place(half(btn), cx, 98, 'Video Settings...'); place(half(sl), cx + 102, 98, 'Difficulty'); pv.alpha_composite(shh.resize((8 * S, 20 * S), Image.NEAREST), ((cx + 102 + 30) * S, 98 * S))
place(btn, cx, 240 - 27, 'Done')
pv.save(f'{OUT}/preview_options.png')
print('ok')
