"""Рама и колодцы инвентаря игрока в стиле доски квестов — дорисовываются на накладку после gui_builder
(в спеках draw_player_inventory: false). Запуск из scripts/ скилла: python3 inventory_frame.py OVERLAY.png ..."""
import sys; sys.path.insert(0, '.')
from PIL import Image
import props, art
OX, OY, PAD, INNER = 30, 17, 4, '#3e2731'
for p in sys.argv[1:]:
    img = Image.open(p).convert('RGBA')
    for y0, rows in ((138, 3), (196, 1)):                       # 9x3 инвентарь и хотбар (6-рядный сундук)
        x0, y, w, h = OX + 7, OY + y0, 9 * 18, rows * 18
        fr = props.frame(w + 2 * PAD, h + 2 * PAD, 'wood', INNER)
        art.drop_shadow(img, (x0 - PAD, y - PAD, x0 + w - 1 + PAD, y + h - 1 + PAD)); img.alpha_composite(fr, (x0 - PAD, y - PAD))
        for r in range(rows):
            for c in range(9): img.alpha_composite(props.well(18, INNER), (x0 + 18 * c, y + 18 * r))
    px = img.load()
    if px[235, 238][3] == 0: px[235, 238] = (0, 0, 0, 1)        # якорь ширины глифа
    img.save(p)
