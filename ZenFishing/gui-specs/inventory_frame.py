"""Рама и колодцы инвентаря игрока в синей рыбацкой раме — дорисовываются на накладку после gui_builder.
Запуск из scripts/ скилла: python3 inventory_frame.py OVERLAY.png ..."""
import sys; sys.path.insert(0, '.')
from PIL import Image
import props, art
OX, OY, PAD, INNER, RIM = 30, 17, 4, '#14213a', '#4e9fd6'
for p in sys.argv[1:]:
    img = Image.open(p).convert('RGBA')
    for y0, rows in ((138, 3), (196, 1)):
        x0, y, w, h = OX + 7, OY + y0, 9 * 18, rows * 18
        fr = props.frame(w + 2 * PAD, h + 2 * PAD, 'wood', INNER, RIM)
        art.drop_shadow(img, (x0 - PAD, y - PAD, x0 + w - 1 + PAD, y + h - 1 + PAD)); img.alpha_composite(fr, (x0 - PAD, y - PAD))
        for r in range(rows):
            for c in range(9): img.alpha_composite(props.well(18, INNER), (x0 + 18 * c, y + 18 * r))
    px = img.load()
    if px[235, 238][3] == 0: px[235, 238] = (0, 0, 0, 1)
    img.save(p)
