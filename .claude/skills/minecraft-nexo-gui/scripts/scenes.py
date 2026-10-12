"""Small illustrated scene cards (about 116 x 44) for job / category menus, drawn procedurally in banded pixel
art: sky with clouds and sparkles, hills, ground, and props per theme, with the job's tool as the hero in the
middle on a soft halo. Own drawings - no character art.

    scene(name, w=116, h=44, hero=None) -> RGBA
    names: farm, mine, pond, forest, hunt, forge, lab, library
"""
import math
import random
from PIL import Image, ImageDraw

import icons16


def C(h, a=255):
    h = h.lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def _bands(im, box, colors):
    x0, y0, x1, y1 = box
    d = ImageDraw.Draw(im)
    n = len(colors)
    for i, c in enumerate(colors):
        d.rectangle((x0, y0 + (y1 - y0 + 1) * i // n, x1, y0 + (y1 - y0 + 1) * (i + 1) // n - 1), fill=C(c))


def _outline(im, color):
    w, h = im.size
    src = im.copy().load()
    px = im.load()
    for y in range(h):
        for x in range(w):
            if src[x, y][3] == 0 and any(0 <= x + dx < w and 0 <= y + dy < h and src[x + dx, y + dy][3]
                                         for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                px[x, y] = C(color)
    return im


def sky(im, h_sky, top='#78abc4', mid='#96dadb', low='#c8eef0', seed=1, clouds=True):
    w = im.width
    _bands(im, (0, 0, w - 1, h_sky - 1), [top, mid, low])
    rnd = random.Random(seed)
    if clouds:
        d = ImageDraw.Draw(im)
        for cx in range(-6, w, 26):
            cx += rnd.randint(-4, 4)
            cy = rnd.randint(4, max(5, h_sky // 2))
            for (dx, dy, r) in ((0, 0, 4), (5, -2, 5), (11, 0, 4), (6, 2, 4)):
                d.ellipse((cx + dx - r, cy + dy - r // 2 - 1, cx + dx + r, cy + dy + r // 2 + 1), fill=C('#e0f1f6'))
            d.line((cx - 3, cy + 3, cx + 14, cy + 3), fill=C('#b8e4ea'))
    px = im.load()
    for _ in range(max(2, w // 40)):                                    # sparkles
        sx, sy = rnd.randint(4, w - 5), rnd.randint(2, max(3, h_sky - 6))
        for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            px[sx + dx, sy + dy] = C('#ffffff')


def hills(im, y_base, back='#4a8d83', front='#59ad7d', seed=2):
    w, h = im.size
    d = ImageDraw.Draw(im)
    rnd = random.Random(seed)
    for col, amp, off in ((back, 9, 0), (front, 6, 13)):
        pts = [(0, h)]
        for x in range(0, w + 1, 2):
            y = y_base - amp * (0.6 + 0.4 * math.sin(x / (14 + off) + seed + off)) + off * 0.25
            pts.append((x, y))
        pts.append((w, h))
        d.polygon(pts, fill=C(col))


def ground(im, y0, top='#60cd52', base='#42ad48', dark='#32904e', seed=3):
    w, h = im.size
    d = ImageDraw.Draw(im)
    d.rectangle((0, y0, w - 1, h - 1), fill=C(base))
    d.line((0, y0, w - 1, y0), fill=C(top))
    px = im.load()
    rnd = random.Random(seed)
    for x in range(0, w, 3):                                            # tufts
        tx = x + rnd.randint(0, 2)
        ty = y0 + rnd.randint(2, max(2, h - y0 - 2))
        if 0 <= tx < w and ty < h:
            px[tx, ty] = C(top)
            if ty + 1 < h:
                px[tx, ty + 1] = C(dark)


def fence(im, y0, height=9):
    w = im.width
    d = ImageDraw.Draw(im)
    for rail in (y0 + 2, y0 + height - 3):
        d.rectangle((0, rail, w - 1, rail + 1), fill=C('#bebcb7'))
        d.line((0, rail + 1, w - 1, rail + 1), fill=C('#7e7973'))
    for x in range(1, w, 5):
        d.rectangle((x, y0 + 1, x + 2, y0 + height), fill=C('#e8efed'))
        d.point((x + 1, y0), fill=C('#e8efed'))
        d.line((x + 2, y0 + 1, x + 2, y0 + height), fill=C('#bebcb7'))


def halo(im, cx, cy, r, color='#fff2ab'):
    """Banded light disc behind the hero: three rings blended over the scene (no gradient noise)."""
    for k, a in ((1.0, 60), (0.72, 90), (0.45, 120)):
        lay = Image.new('RGBA', im.size, (0, 0, 0, 0))
        rr = r * k
        ImageDraw.Draw(lay).ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=C(color, a))
        im.alpha_composite(lay)


def hero(im, name, cx, cy, scale=2):
    ic = icons16.icon(name)
    ic = ic.resize((16 * scale, 16 * scale), Image.NEAREST)
    sh = Image.new('RGBA', ic.size, (0, 0, 0, 0))
    sh.putalpha(ic.getchannel('A').point(lambda v: 90 if v else 0))
    im.alpha_composite(sh, (cx - 8 * scale + 2, cy - 8 * scale + 2))
    im.alpha_composite(ic, (cx - 8 * scale, cy - 8 * scale))


def _wheat_row(im, y_bottom, step=6):
    """A row of ripe wheat ears (tops of the 32px growth-stage sprite) standing behind a fence."""
    import crop_wheat
    stalk = crop_wheat.stage_img(7)
    top = stalk.crop((6, 2, 26, 17))
    for i, x in enumerate(range(-6, im.width, step)):
        im.alpha_composite(top, (x, y_bottom - top.height + (i % 2)))


def _tree(im, x, y_ground, h, seed):
    rnd = random.Random(seed)
    d = ImageDraw.Draw(im)
    d.rectangle((x - 1, y_ground - h // 2, x + 1, y_ground), fill=C('#6b2f25'))
    d.line((x - 1, y_ground - h // 2, x - 1, y_ground), fill=C('#8c3f2b'))
    cy = y_ground - h // 2 - 3
    for (dx, dy, r, c) in ((0, 0, 7, '#265c42'), (-4, 2, 5, '#3e8948'), (4, 1, 5, '#3e8948'), (0, -3, 5, '#63c74d')):
        d.ellipse((x + dx - r, cy + dy - r, x + dx + r, cy + dy + r), fill=C(c))


def scene(name, w=116, h=44, hero_icon=None, seed=1):
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    px = im.load()
    cx, cy = w // 2, h // 2 - 1
    if name == 'farm':
        sky(im, h - 14, seed=seed)
        hills(im, h - 16)
        _wheat_row(im, h - 12)
        fence(im, h - 18)
        ground(im, h - 9)
        hero_icon = hero_icon or 'hoe'
    elif name == 'mine':
        _bands(im, (0, 0, w - 1, h - 1), ['#262b44', '#3a4466', '#3a4466', '#5a6988'])
        rnd = random.Random(seed)
        for x in range(0, w, 9):                                        # stalactites
            l = rnd.randint(3, 9)
            d.polygon([(x, 0), (x + 6, 0), (x + 3, l)], fill=C('#5a6988'))
            d.line((x + 1, 0, x + 3, l - 1), fill=C('#8b9bb4'))
        for _ in range(14):                                             # ore spots
            ox, oy = rnd.randint(2, w - 4), rnd.randint(8, h - 12)
            col = rnd.choice(['#feae34', '#2ce8f5', '#63c74d', '#e43b44'])
            for ddx, ddy in ((0, 0), (1, 0), (0, 1)):
                px[ox + ddx, oy + ddy] = C(col)
            px[ox + 1, oy + 1] = C('#181425')
        d.rectangle((0, h - 8, w - 1, h - 1), fill=C('#5a6988'))       # floor + rail
        d.line((0, h - 8, w - 1, h - 8), fill=C('#8b9bb4'))
        for x in range(2, w, 6):
            d.rectangle((x, h - 5, x + 3, h - 4), fill=C('#733e39'))
        d.line((0, h - 6, w - 1, h - 6), fill=C('#c0cbdc'))
        d.line((0, h - 3, w - 1, h - 3), fill=C('#c0cbdc'))
        for lx in (12, w - 14):                                          # lanterns
            d.rectangle((lx, 8, lx + 4, 14), fill=C('#262b44'))
            d.rectangle((lx + 1, 9, lx + 3, 13), fill=C('#feae34'))
            halo(im, lx + 2, 11, 7, '#feae34')
        hero_icon = hero_icon or 'pickaxe'
    elif name == 'pond':
        sky(im, h - 18, seed=seed)
        hills(im, h - 18)
        _bands(im, (0, h - 15, w - 1, h - 1), ['#96dadb', '#78abc4', '#4a8d83'])
        rnd = random.Random(seed)
        for _ in range(10):
            rx, ry = rnd.randint(0, w - 8), rnd.randint(h - 13, h - 3)
            d.line((rx, ry, rx + rnd.randint(3, 7), ry), fill=C('#e0f1f6'))
        for rx in (4, 8, w - 10, w - 6):                                  # reeds
            d.line((rx, h - 22, rx, h - 12), fill=C('#3e8948'))
            d.rectangle((rx - 1, h - 24, rx + 1, h - 21), fill=C('#733e39'))
        for (lx, ly) in ((22, h - 6), (w - 30, h - 9)):                   # lily pads
            d.ellipse((lx, ly, lx + 6, ly + 3), fill=C('#3e8948'))
            d.point((lx + 3, ly), fill=C('#f6757a'))
        hero_icon = hero_icon or 'fishing_rod'
    elif name == 'forest':
        sky(im, h - 12, top='#78abc4', mid='#96dadb', low='#c8eef0', seed=seed)
        for i, x in enumerate(range(-4, w + 8, 13)):
            _tree(im, x, h - 9, 26 + (i % 3) * 4, seed + i)
        ground(im, h - 9, top='#63c74d', base='#3e8948', dark='#265c42')
        for lx in (8, w - 26):                                          # log pile
            for k in range(3):
                d.rectangle((lx + k * 5, h - 8 - (k % 2) * 3, lx + k * 5 + 4, h - 5 - (k % 2) * 3), fill=C('#8c3f2b'))
                d.ellipse((lx + k * 5, h - 8 - (k % 2) * 3, lx + k * 5 + 3, h - 5 - (k % 2) * 3), fill=C('#e4a672'))
        hero_icon = hero_icon or 'axe'
    elif name == 'hunt':
        sky(im, h - 12, top='#f77622', mid='#feae34', low='#fee761', seed=seed, clouds=False)
        hills(im, h - 12, back='#733e39', front='#3e2731')
        for i, x in enumerate(range(-2, w + 8, 17)):
            _tree(im, x, h - 9, 20 + (i % 2) * 6, seed + 9 + i)
        ground(im, h - 9, top='#3e8948', base='#265c42', dark='#193c3e')
        tx, ty = w - 22, h - 20                                          # target
        for r, c in ((7, '#ead4aa'), (5, '#e43b44'), (3, '#ead4aa'), (1, '#e43b44')):
            d.ellipse((tx - r, ty - r, tx + r, ty + r), fill=C(c))
        hero_icon = hero_icon or 'bow'
    elif name == 'forge':
        _bands(im, (0, 0, w - 1, h - 1), ['#3e2731', '#733e39', '#733e39'])
        for y in range(0, h - 8, 5):                                    # bricks
            for x in range((y // 5) % 2 * 5, w, 10):
                d.rectangle((x, y, x + 8, y + 3), fill=C('#a22633' if (x + y) % 3 else '#be4a2f'))
                d.line((x, y, x + 8, y), fill=C('#e43b44'))
        halo(im, cx, h - 12, 20, '#f77622')
        d.rectangle((0, h - 8, w - 1, h - 1), fill=C('#3e2731'))
        for (ax) in (14, w - 30):                                       # anvils
            d.rectangle((ax + 3, h - 15, ax + 12, h - 12), fill=C('#5a6988'))
            d.rectangle((ax + 6, h - 12, ax + 9, h - 9), fill=C('#3a4466'))
            d.rectangle((ax + 4, h - 9, ax + 11, h - 8), fill=C('#3a4466'))
            d.line((ax + 3, h - 15, ax + 12, h - 15), fill=C('#8b9bb4'))
        hero_icon = hero_icon or 'hammer'
    elif name == 'lab':
        _bands(im, (0, 0, w - 1, h - 1), ['#5a6988', '#8b9bb4', '#8b9bb4'])
        for y in range(0, h, 6):
            for x in range((y // 6) % 2 * 6, w, 12):
                d.rectangle((x, y, x + 10, y + 4), outline=C('#5a6988'))
        for sx in (4, w - 30):                                          # shelves with bottles
            d.rectangle((sx, 12, sx + 25, 13), fill=C('#733e39'))
            for k, col in enumerate(('#63c74d', '#2ce8f5', '#b55088', '#feae34')):
                bx = sx + 2 + k * 6
                d.rectangle((bx, 6, bx + 3, 11), fill=C('#e0f1f6'))
                d.rectangle((bx, 8, bx + 3, 11), fill=C(col))
                d.point((bx + 1, 5), fill=C('#733e39'))
        d.rectangle((0, h - 8, w - 1, h - 1), fill=C('#733e39'))       # table
        d.line((0, h - 8, w - 1, h - 8), fill=C('#b86f50'))
        hero_icon = hero_icon or 'potion'
    elif name == 'library':
        _bands(im, (0, 0, w - 1, h - 1), ['#3e2731', '#68386c', '#68386c'])
        for x in range(0, w, 14):                                       # bookshelves
            d.rectangle((x, 4, x + 12, h - 9), fill=C('#733e39'))
            for row in range(3):
                yy = 6 + row * ((h - 15) // 3)
                for b in range(5):
                    col = ('#a22633', '#124e89', '#3e8948', '#feae34', '#b55088')[(b + row + x) % 5]
                    d.rectangle((x + 1 + b * 2, yy, x + 2 + b * 2, yy + 6), fill=C(col))
        halo(im, cx, cy, 18, '#b55088')
        d.rectangle((0, h - 8, w - 1, h - 1), fill=C('#3e2731'))
        hero_icon = hero_icon or 'book'
    else:
        raise KeyError(name)
    halo(im, cx, cy, 15)
    hero(im, hero_icon, cx, cy)
    return im


NAMES = ['farm', 'mine', 'pond', 'forest', 'hunt', 'forge', 'lab', 'library']
