"""Фон меню прокачки удочки (ZenFishing): 236x239 как остальные фоны (глиф шрифта zenfishing:menu, ascent 30),
GUI сундука 6 рядов начинается в точке (30, 17), слот (col,row) — x = 38 + col*18, y = 35 + row*18; инвентарь y = 157, хотбар y = 215.
Всё прозрачно, кроме вертикальной плашки на колонках 1..7 (от заголовка до хотбара). В плашке: лента-заголовок, гнездо удочки
(большая картинка 3x3 на слотах 12..14/21..23/30..32), кнопка «УЛУЧШИТЬ» на 3 слота (48–50) и гнёзда инвентаря/хотбара колонок 1..7 (предметы игрока скрыты пакетами через TakuFarmers ContainerSkin).
Запуск: MCFONT=<папка с mcfont.py> python3 upgrade_bg.py OUT.png"""
import sys, os
from PIL import Image, ImageDraw
sys.path.insert(0, os.environ.get('MCFONT', ''))
try: import mcfont
except Exception: mcfont = None

OUT = sys.argv[1]
W, H = 236, 239
GX, GY = 30, 17
def sx(col): return GX + 8 + col * 18
def sy(row): return GY + 18 + row * 18
INV_Y, HOT_Y = GY + 140, GY + 198

RIM, RIM_L, RIM_D, OUTLINE = (58, 172, 228), (120, 212, 245), (40, 136, 192), (14, 52, 88)
FILL, INNER = (14, 72, 116), (10, 58, 98)
SOCK, SOCK_L = (7, 31, 54), (28, 96, 140)
BTN, BTN_L, BTN_D, BTN_TXT = (242, 193, 78), (255, 228, 140), (170, 120, 30), (60, 36, 6)

img = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
# плашка: колонки 2..6 → x от sx(2)-5 до sx(7)+4 (слот 16 px + зазоры)
PX0, PX1 = sx(1) - 6, sx(7) + 16 + 5
PY0, PY1 = 0, H - 1
d.rounded_rectangle((PX0, PY0, PX1, PY1), radius=4, fill=OUTLINE + (255,))
d.rounded_rectangle((PX0 + 1, PY0 + 1, PX1 - 1, PY1 - 1), radius=3, fill=RIM + (255,))
d.rounded_rectangle((PX0 + 3, PY0 + 3, PX1 - 3, PY1 - 3), radius=2, fill=FILL + (255,))
d.line((PX0 + 3, PY0 + 1, PX1 - 3, PY0 + 1), fill=RIM_L + (255,)); d.line((PX0 + 1, PY0 + 3, PX0 + 1, PY1 - 3), fill=RIM_L + (255,))
d.line((PX0 + 3, PY1 - 2, PX1 - 3, PY1 - 2), fill=RIM_D + (255,)); d.line((PX1 - 2, PY0 + 3, PX1 - 2, PY1 - 3), fill=RIM_D + (255,))

def socket(x, y, w=16, h=16):
    d.rectangle((x - 1, y - 1, x + w, y + h), fill=SOCK + (255,))
    d.line((x - 1, y + h, x + w, y + h), fill=SOCK_L + (255,)); d.line((x + w, y - 1, x + w, y + h), fill=SOCK_L + (255,))
def panel(x0, y0, x1, y1):
    d.rectangle((x0, y0, x1, y1), fill=INNER + (255,)); d.rectangle((x0, y0, x1, y1), outline=OUTLINE + (255,))
def text(x, y, s, col='#ffffff', shadow=True):
    if mcfont: mcfont.draw(img, x, y, s, color=col, scale=1, shadow=shadow)
    else: d.text((x, y), s, fill=col)
def tw(s): return mcfont.width(s, 1) if mcfont else len(s) * 6

cx = (PX0 + PX1) // 2
# заголовок-лента
title = 'УДОЧКА'
d.rectangle((PX0 + 6, 5, PX1 - 6, 15), fill=OUTLINE + (255,)); d.rectangle((PX0 + 7, 6, PX1 - 7, 14), fill=RIM_D + (255,))
text(cx - tw(title) // 2, 6, title, '#dff6ff')
# удочка — большая картинка на слотах 12..14/21..23/30..32 (невидимые предметы с подсказкой удочки)
# большая удочка: ванильная текстура 16x16 ×3 = 48 px по центру блока 3x3 слота (cols 3..5, rows 1..3)
rod = Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'art', 'fishing_rod_vanilla.png')).convert('RGBA').resize((48, 48), Image.NEAREST)
bx, by = sx(3) + (54 - 48) // 2, sy(1) + (54 - 48) // 2
sh = Image.new('RGBA', rod.size, (0, 0, 0, 0)); sh.paste((4, 20, 40, 120), (0, 0), rod.split()[3])
img.alpha_composite(sh, (bx + 2, by + 2)); img.alpha_composite(rod, (bx, by))
# разделитель и подпись
d.line((PX0 + 8, sy(4) + 4, PX1 - 8, sy(4) + 4), fill=OUTLINE + (255,)); d.line((PX0 + 8, sy(4) + 5, PX1 - 8, sy(4) + 5), fill=RIM_D + (255,))
# кнопка «УЛУЧШИТЬ» — слоты 48,49,50 (row 5, cols 3..5)
bx0, by0, bx1, by1 = sx(3) - 1, sy(5) - 1, sx(5) + 16, sy(5) + 16
d.rectangle((bx0, by0, bx1, by1), fill=BTN_D + (255,))
d.rectangle((bx0 + 1, by0 + 1, bx1 - 1, by1 - 2), fill=BTN + (255,))
d.line((bx0 + 1, by0 + 1, bx1 - 1, by0 + 1), fill=BTN_L + (255,)); d.line((bx0 + 1, by0 + 1, bx0 + 1, by1 - 2), fill=BTN_L + (255,))
btn = 'УЛУЧШИТЬ'
text((bx0 + bx1) // 2 - tw(btn) // 2 + 1, by0 + 5, btn, '#3c2406', shadow=False)
# инвентарь и хотбар — ничего не рисуем: сплошная плашка (предметы игрока скрыты пакетами через TakuFarmers)
img.save(OUT); print('upgrade bg ok', img.size)
