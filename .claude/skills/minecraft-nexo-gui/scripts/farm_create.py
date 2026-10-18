#!/usr/bin/env python3
"""'Create farm' menu (HD, 2 texture px per GUI px), from the user's reference: a dark stone-brick arch with
vines and green gem orbs, the title on the lintel, a window into the farm world (modes_hd farm parts) with a
carved stone sign ("Ферма - это твой маленький мир!"), a flagstone floor with lanterns, flowers and pumpkins,
and four coloured stone buttons. Used by gui_builder.py ("hd": 2) as {"type": "farm_create", "part": ...}.
Example: assets/examples/farm_create/menu.json.
"""
import math
import random

from PIL import Image

from kitchen import _r5, rrect, raised, edge_ring, WALNUT
from hub import GOLD, CREAM
from shading import pixel_perfect
from pixfont import draw_text, text_width
from modes import compose
from modes_hd import (K, P, fill, outline, disc, ball, hd_box, drop_shadow, farm_parts, twinkle, LEAF, PUMPKIN,
                      RED, WHEAT, STALK)
import materials

STONE = _r5('#4a4f5c', soft=0.6)          # the arch
FLOOR = _r5('#565b66', soft=0.8)
SIGN = _r5('#a7aab0', soft=1)
GEM = _r5('#3fc24a', soft=0.3)
VINE = _r5('#4f9a3a', soft=0.6)
BTN = {'green': _r5('#4caf3c', soft=0.5), 'blue': _r5('#3a86d0', soft=0.5),
       'orange': _r5('#e08a2a', soft=0.5), 'red': _r5('#c8363a', soft=0.5)}
N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


def _text(img, cx, y, text, color, shadow, narrow=False):
    w = text_width(text, narrow=narrow) * K
    draw_text(img, cx - w // 2 + K // 2, y + K // 2, text, shadow, scale=K, narrow=narrow)
    draw_text(img, cx - w // 2, y, text, color, scale=K, narrow=narrow)


def arch(img, ox, oy, front_y=126, title='Создать ферму'):
    """Stone-brick arch round the whole container part: pillars past the window sides, a lintel with the title,
    an inner dark reveal, vines with leaves trailing down, green gem orbs on the lintel corners."""
    X0, X1 = (ox - 9) * K, (ox + 185) * K - 1
    Y0, YB = (oy - 10) * K, (oy + front_y + 6) * K
    wx0, wy0, wx1, wy1 = (ox + 6) * K, (oy + 15) * K, (ox + 170) * K - 1, (oy + 70) * K   # the picture opening
    band = {(x, y) for y in range(Y0, YB + 1) for x in range(X0, X1 + 1)}
    mask = band - {(x, y) for y in range(wy0, wy1 + 1) for x in range(wx0, wx1 + 1)}
    drop_shadow(img, mask, 4, 4, ())
    materials.fill(img, mask, 'deepslate_bricks', k=K)
    for (x, y) in mask:                                      # darker reveal round the opening (depth)
        d = min(abs(x - wx0 + 1), abs(x - wx1 - 1), abs(y - wy0 + 1), abs(y - wy1 - 1))
        if d < 4 and wx0 - 5 <= x <= wx1 + 5 and wy0 - 5 <= y <= wy1 + 5:
            P(img, x, y, STONE[1] if d < 2 else STONE[2])
    lx0, lx1 = (ox + 34) * K, (ox + 142) * K                 # lintel plate with the title
    plate = rrect(lx0, Y0 + 2, lx1, Y0 + 30, 4)
    raised(img, plate, 4, STONE, shadow_off=(3, 4))
    _text(img, (lx0 + lx1) // 2, Y0 + 9, title, CREAM[5], STONE[0])
    rnd = random.Random(7)
    for (gx, gy) in ((X0 + 14, Y0 + 16), (X1 - 14, Y0 + 16), (X0 + 14, Y0 + 44), (X1 - 14, Y0 + 44)):
        ball(img, gx, gy, 6.5, GEM)
        P(img, gx - 3, gy - 3, CREAM[5])
    vine_paths = [[(X0 + 24 + i * 2, Y0 + 6 + round(4 * math.sin(i * 0.4))) for i in range(60)],
                  [(X1 - 24 - i * 2, Y0 + 6 + round(4 * math.sin(i * 0.45 + 1))) for i in range(60)],
                  [(X0 + 10 + round(3 * math.sin(i * 0.3)), Y0 + 30 + i) for i in range(90)],
                  [(X1 - 10 + round(3 * math.sin(i * 0.33 + 2)), Y0 + 30 + i) for i in range(60)]]
    for path in vine_paths:
        for i, (x, y) in enumerate(path):
            P(img, x, y, VINE[2])
            P(img, x, y + 1, VINE[1])
            if i % 9 == 4:                                   # a leaf: pointed oval, lit top-left, midrib
                s = rnd.choice((-1, 1))
                cx, cy = x + 3 * s, y - 2
                leaf = disc(cx, cy, 3.6, 2.4)
                for (qx, qy) in leaf:
                    d = (qx - cx) * s + (qy - cy)
                    P(img, qx, qy, VINE[4] if d < -1 else VINE[3] if d < 2 else VINE[2])
                for t in range(-2, 3):
                    P(img, cx + t * s, cy + (t > 0), VINE[2])
                outline(img, leaf, VINE[1], VINE[0])
    return (wx0, wy0, wx1, wy1)


def picture(img, ox, oy, box=None, seed=5, sign_lines=('Ферма -', 'это твой', 'маленький', 'мир!')):
    """The farm world in the opening (modes_hd farm parts) and a carved stone sign on its right."""
    wx0, wy0, wx1, wy1 = box or ((ox + 6) * K, (oy + 15) * K, (ox + 170) * K - 1, (oy + 70) * K)
    W, H = wx1 - wx0 + 1, wy1 - wy0 + 1
    items = [it for it in farm_parts(W, H, seed) if it['name'] not in ('quest_board',)]
    compose(items, img, wx0, wy0, clip=(wx0, wy0, wx1, wy1), prefix='farm/')
    sx0, sy0 = wx1 - 140, wy0 + 6                            # the stone sign
    slab = rrect(sx0, sy0, sx0 + 128, sy0 + 88, 6)
    raised(img, slab, 4, SIGN, shadow_off=(4, 4), shadow_ramp=None)
    rnd = random.Random(3)
    for (x, y) in sorted(slab):                              # chips and cracks in the stone
        if rnd.random() < 0.02 and (x + 1, y) in slab:
            P(img, x, y, SIGN[2])
            P(img, x + 1, y, SIGN[2])
    inner = rrect(sx0 + 6, sy0 + 6, sx0 + 122, sy0 + 80, 4)
    for (x, y) in edge_ring(inner):                          # carved frame line
        P(img, x, y, SIGN[2] if (x < sx0 + 64 and y < sy0 + 44) else SIGN[4])
    ty = sy0 + 13
    for line in sign_lines:                                  # carved letters: dark groove, lit lower lip
        w = text_width(line) * K
        x = sx0 + 64 - w // 2
        draw_text(img, x, ty + 1, line, SIGN[5], scale=K)
        draw_text(img, x, ty, line, SIGN[1], scale=K)
        ty += 15


def floor(img, ox, oy, y0=71, y1=126, seed=2):
    """Flagstone floor between the picture and the buttons, lanterns on posts, flower pots, pumpkins."""
    X0, X1 = (ox + 6) * K, (ox + 170) * K - 1
    Y0, Y1 = y0 * K + oy * K, y1 * K + oy * K
    area = {(x, y) for y in range(Y0, Y1) for x in range(X0, X1 + 1)}
    materials.fill(img, area, 'cobbled_deepslate', k=K, bevel=False, outline=False)
    for x in range(X0, X1 + 1):                              # the picture's sill
        P(img, x, Y0, STONE[1])
        P(img, x, Y0 + 1, STONE[4])
    for (lx, side) in ((X0 + 30, 1), (X1 - 30, -1)):         # lanterns on posts
        for y in range(Y0 - 28, Y0 + 14):
            P(img, lx, y, WALNUT[4])
            P(img, lx + 1, y, WALNUT[2])
        lan = {(lx - 3 + i, Y0 - 38 + j) for i in range(8) for j in range(10)}
        for (x, y) in lan:
            i, j = x - lx + 3, y - Y0 + 38
            P(img, x, y, GOLD[5] if 2 <= i <= 5 and 2 <= j <= 7 else STONE[1] if j in (0, 9) else STONE[2])
        outline(img, lan, STONE[1], STONE[0])
        for t in range(0, 360, 30):
            P(img, round(lx + 1 + 9 * math.cos(math.radians(t))), round(Y0 - 33 + 8 * math.sin(math.radians(t))), GOLD[4])
    rnd = random.Random(seed)
    for (fx, kind) in ((X0 + 56, 'flowers'), (X1 - 60, 'flowers'), (X1 - 92, 'pumpkins')):
        if kind == 'flowers':                                # a pot with a bushy flower clump
            pot = {(fx + i, Y0 + 6 + j) for i in range(16) for j in range(9) if not (j > 5 and i in (0, 15))}
            for (x, y) in pot:
                P(img, x, y, (PUMPKIN[3] if x < fx + 11 else PUMPKIN[2]) if y > Y0 + 7 else PUMPKIN[4])
            outline(img, pot, PUMPKIN[1], PUMPKIN[0])
            bush = disc(fx + 7.5, Y0 - 2, 10, 8)
            bush = {p for p in bush if p[1] <= Y0 + 6}
            for (x, y) in bush:
                d = (x - fx - 7) + (y - Y0 + 2)
                P(img, x, y, VINE[4] if d < -5 else VINE[3] if d < 3 else VINE[2])
            outline(img, bush, VINE[1], VINE[0])
            for n in range(14):
                cx, cy = fx + 1 + rnd.randint(0, 14), Y0 - 9 + rnd.randint(0, 12)
                if (cx, cy) not in bush:
                    continue
                c = (RED, WHEAT, _r5('#d65aa8', soft=0.4), _r5('#f2f2f2', soft=1))[n % 4]
                for (dx, dy) in ((0, 0), (1, 0), (0, -1), (-1, 0), (0, 1)):
                    P(img, cx + dx, cy + dy, c[5] if (dx, dy) == (0, 0) else c[3])
        else:
            for (px_, py_) in ((fx, Y0 + 8), (fx + 12, Y0 + 9)):
                pts = disc(px_, py_, 5, 4)
                for (x, y) in pts:
                    c = PUMPKIN[4] if x < px_ - 1 else PUMPKIN[3] if x < px_ + 2 else PUMPKIN[2]
                    if (x - px_) in (-2, 2):
                        c = PUMPKIN[2]
                    P(img, x, y, c)
                outline(img, pts, PUMPKIN[1], PUMPKIN[0])
                fill(img, [(px_, py_ - 5), (px_, py_ - 6), (px_ + 1, py_ - 6)], STALK[3])


def button(img, ox, oy, c, r, w, h, text, color, narrow=False):
    """Coloured stone button over slots: a raised slab 1 px inside the slots, 3 px front face, lit bevel, a
    gloss band on the top half, white letters with a dark shadow."""
    ramp = BTN[color]
    x0, y0, x1, y1 = hd_box(ox, oy, c, r, w, h)
    solid, face = raised(img, rrect(x0 + 2, y0 + 2, x1 - 2, y1 - 6, 3), 4, ramp, shadow_off=(3, 4))
    for (x, y) in face:
        if y < (y0 + y1) // 2 - 4 and (x, y - 2) in face and (x - 2, y) in face:
            P(img, x, y, ramp[4])
    if text_width(text) * K > x1 - x0 - 12:
        narrow = True
    _text(img, (x0 + x1 + 1) // 2, (y0 + y1 - 4) // 2 - 7, text, CREAM[5], ramp[0], narrow)
    pixel_perfect(img, only={ramp[0]}, box=(x0, y0, x1 + 1, y1 + 1))
