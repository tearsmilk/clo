"""Scene props for "illustrated" menus (castle walls, quest boards, shops): every prop is drawn procedurally at
1:1 pixels in the palette style of art.py, sized to a box, so it fits any layout.

    render(name, w, h, **opts) -> RGBA image of exactly w x h

  wall      stone-block wall with a lit coping ledge on top          color, coping, seed
  planks    wooden wall (vertical boards) with a top beam            color, seed
  pillar    stone column with capital and base                       color
  brazier   iron bowl with a fire (torch: thin pole + flame)         color, kind ('bowl'|'torch'|'lantern')
  banner    hanging cloth banner on a rod, folds, trim, V or swallow tail, optional emblem sprite
                                                                     color, trim, rod, tail, emblem
  ribbon    title ribbon: a band with folded tails (header style 'ribbon' uses it)   color
  rubble    pile of rounded boulders with leaves and flowers         color, leaves, flowers, seed, density
  hay       hay bales / sacks pile for farm scenes                   color, seed
  flourish  symmetric gold ornament (wings + swoops), for under titles   color, gem
  note      pinned parchment note with scribbles and a seal          color, seal, seed
  divider   ornamental line with arrow tips and a centre gem         color, gem
  frame     framed panel (gold/wood/stone/iron rim) - slot bars use it   kind, inner

Rules (references/design-guide.md): coloured dark outline around every shape, light from the top-left, colours
walk palette ramps via art.step, structure instead of noise.
"""
import math, random
from PIL import Image, ImageDraw

import art

step, base, outline_of, rgba = art.step, art.base, art.outline_of, art.rgba

GOLD = '#feae34'


# ----------------------------------------------------------------------------- helpers

def _outline(im, color=None, inside=False):
    """1px outline around the opaque shape. outside: drawn on transparent neighbours (needs 1px margin);
    inside: replaces the shape's own edge pixels. color None = dark cool shade of the touching pixel."""
    w, h = im.size
    src = im.copy().load()
    px = im.load()
    for y in range(h):
        for x in range(w):
            a = src[x, y][3]
            if inside:
                if not a:
                    continue
                edge = any(not (0 <= x + dx < w and 0 <= y + dy < h) or not src[x + dx, y + dy][3]
                           for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                if edge:
                    px[x, y] = rgba(color) if color else outline_of(src[x, y])
            elif not a:
                nb = [src[x + dx, y + dy] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                      if 0 <= x + dx < w and 0 <= y + dy < h and src[x + dx, y + dy][3]]
                if nb:
                    px[x, y] = rgba(color) if color else outline_of(min(nb, key=lambda c: sum(c[:3])))
    return im


def _shade_shape(im, color, light=1, dark=-1):
    """Top-left inner edge one step lighter, bottom-right inner edge one step darker."""
    w, h = im.size
    src = im.copy().load()
    px = im.load()
    for y in range(h):
        for x in range(w):
            if not src[x, y][3]:
                continue
            up = y == 0 or not src[x, y - 1][3]
            left = x == 0 or not src[x - 1, y][3]
            down = y == h - 1 or not src[x, y + 1][3]
            right = x == w - 1 or not src[x + 1, y][3]
            if (up or left) and not (down or right):
                px[x, y] = step(color, light)
            elif (down or right) and not (up or left):
                px[x, y] = step(color, dark)
    return im


def _bezier(p0, p1, p2, p3, n=60):
    for i in range(n + 1):
        t = i / n
        a, b, c, d = (1 - t) ** 3, 3 * t * (1 - t) ** 2, 3 * t * t * (1 - t), t ** 3
        yield (a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1])


def _stroke(mask, pts, width=2):
    d = ImageDraw.Draw(mask)
    for x, y in pts:
        if width <= 1:
            d.point((round(x), round(y)), fill=255)
        else:
            r = (width - 1) / 2
            d.rectangle((round(x - r), round(y - r), round(x - r) + width - 1, round(y - r) + width - 1), fill=255)


def _metal(mask, color=GOLD, outline=None):
    """Colour a stroke mask as polished metal: lit top pixels, base body, darker underside, dark outline."""
    w, h = mask.size
    m = mask.load()
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    px = im.load()
    for y in range(h):
        for x in range(w):
            if not m[x, y]:
                continue
            up = y == 0 or not m[x, y - 1]
            down = y == h - 1 or not m[x, y + 1]
            px[x, y] = step(color, 1) if up else (step(color, -1) if down else base(color))
    return _outline(im, outline or step(color, -4) if art._enabled else '#3e2731')


# ----------------------------------------------------------------------------- walls

def tex_stonewall(w, h, color, bw=11, bh=5, seed=3):
    """Castle wall: staggered stone blocks, each block a slightly different tone of the ramp, lit top edge,
    shaded bottom/right, dark mortar, a few chips and cracks."""
    rnd = random.Random(seed)
    mortar = step(color, -2)
    im = Image.new('RGBA', (w, h), mortar)
    px = im.load()
    row = 0
    for y0 in range(0, h, bh + 1):
        off = (bw // 2 + 1) * (row % 2) + rnd.randint(-1, 1)
        x0 = -off
        while x0 < w:
            bwi = bw + rnd.choice((0, 0, 0, -2, 2))
            r = rnd.random()
            c = step(color, 1) if r < 0.10 else (step(color, -1) if r < 0.28 else base(color))
            lt, dk = step(c, 1) if c != base(color) else step(color, 1), step(color, -1) if c != step(color, -1) else mortar
            for y in range(y0, min(h, y0 + bh)):
                for x in range(max(0, x0), min(w, x0 + bwi)):
                    if y == y0 and x < x0 + bwi - 1:
                        px[x, y] = lt
                    elif y == y0 + bh - 1 or x == x0 + bwi - 1:
                        px[x, y] = dk
                    else:
                        px[x, y] = c
            if rnd.random() < 0.25:                                   # chip / crack
                cx, cy = x0 + rnd.randint(2, max(2, bwi - 3)), y0 + rnd.randint(1, max(1, bh - 2))
                for dx, dy in ((0, 0), (1, 0), (1, 1)) if rnd.random() < 0.5 else ((0, 0), (0, 1)):
                    if 0 <= cx + dx < w and 0 <= cy + dy < h:
                        px[cx + dx, cy + dy] = dk
            x0 += bwi + 1
        row += 1
    return im


def wall(w, h, color='#3a4466', coping=True, seed=3, **_):
    im = tex_stonewall(w, h, color, seed=seed)
    if coping:                                                       # cap stones along the top
        d = ImageDraw.Draw(im)
        cap = step(color, 1)
        d.rectangle((0, 0, w - 1, 4), fill=cap)
        d.line((0, 0, w - 1, 0), fill=step(color, 2))
        d.line((0, 4, w - 1, 4), fill=step(color, -2))
        d.line((0, 5, w - 1, 5), fill=step(color, -1))
        for x in range(7, w, 16):
            d.line((x, 1, x, 3), fill=step(color, -1))
            if x + 1 < w:
                d.line((x + 1, 1, x + 1, 3), fill=step(color, 2))
    return im


def planks(w, h, color='#b86f50', seed=2, **_):
    im = art.tex_planks(w, h, color, vertical=True, board=7, seed=seed, nails=False)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w - 1, 4), fill=step(color, -1))            # top beam
    d.line((0, 0, w - 1, 0), fill=step(color, 1))
    d.line((0, 4, w - 1, 4), fill=step(color, -3))
    return im


def pillar(w, h, color='#5a6988', **_):
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cap, shaft = 5, 2
    d.rectangle((1, 1, w - 2, cap), fill=base(color))                          # capital
    d.rectangle((shaft + 1, cap + 1, w - shaft - 2, h - 5), fill=base(color))  # shaft
    d.rectangle((1, h - 4, w - 2, h - 2), fill=base(color))                    # base
    for y in range(cap + 6, h - 5, 7):                                         # block joints
        d.line((shaft + 1, y, w - shaft - 2, y), fill=step(color, -2))
        d.line((shaft + 1, y + 1, w - shaft - 2, y + 1), fill=step(color, 1))
    d.line((shaft + 2, cap + 1, shaft + 2, h - 5), fill=step(color, 1))
    d.line((w - shaft - 3, cap + 1, w - shaft - 3, h - 5), fill=step(color, -1))
    d.line((1, cap, w - 2, cap), fill=step(color, -2))
    _shade_shape(im, color)
    return _outline(im, step(color, -3) if art._enabled else '#181425', inside=True)


def _flame(fw, fh):
    """Teardrop fire: deep-red rim, orange body, yellow inner, pale core; flickering tip."""
    im = Image.new('RGBA', (fw, fh), (0, 0, 0, 0))
    px = im.load()
    cx = (fw - 1) / 2
    layers = [('#be4a2f', 1.0), ('#f77622', 0.78), ('#feae34', 0.52), ('#fee761', 0.28)]
    for col, k in layers:
        for y in range(fh):
            t = y / max(1, fh - 1)                       # 0 top .. 1 bottom
            half = (fw / 2) * k * (math.sin(t * math.pi * 0.62 + 0.25) ** 1.3)
            top = 1 - k
            if t < top * 0.9:
                continue
            for x in range(fw):
                if abs(x - cx) <= half:
                    px[x, y] = rgba(col)
    if fw >= 5:                                          # little tongue to the side of the tip
        px[int(cx) + 1, 0] = rgba('#f77622')
    return im


def brazier(w, h, color='#3a4466', kind='bowl', **_):
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if kind == 'torch':
        px0 = w // 2 - 1
        d.rectangle((px0, h // 2, px0 + 2, h - 1), fill=rgba('#733e39'))
        d.line((px0, h // 2, px0, h - 1), fill=rgba('#b86f50'))
        d.rectangle((px0 - 1, h // 2 - 1, px0 + 3, h // 2 + 1), fill=rgba('#3a4466'))
        fl = _flame(min(w, 7), h // 2)
        im.alpha_composite(fl, ((w - fl.width) // 2, 0))
        return im
    if kind == 'lantern':
        lw = min(w, 9)
        x0 = (w - lw) // 2
        d.rectangle((x0 + 2, 0, x0 + lw - 3, 1), fill=rgba('#262b44'))
        d.rectangle((x0, 2, x0 + lw - 1, h - 1), fill=rgba('#262b44'))
        d.rectangle((x0 + 1, 4, x0 + lw - 2, h - 3), fill=rgba('#feae34'))
        d.rectangle((x0 + 2, 5, x0 + lw - 3, h - 4), fill=rgba('#fee761'))
        d.line((x0 + lw // 2, 4, x0 + lw // 2, h - 3), fill=rgba('#262b44'))
        d.line((x0, 3, x0 + lw - 1, 3), fill=rgba('#5a6988'))
        return im
    bowl_h = max(4, h // 3)
    by = h - bowl_h
    d.rectangle((0, by, w - 1, by + 1), fill=base(color))                     # rim
    d.line((0, by, w - 1, by), fill=step(color, 1))
    d.rectangle((1, by + 2, w - 2, h - 2), fill=step(color, -1))              # bowl
    d.rectangle((w // 2 - 1, h - 1, w // 2, h - 1), fill=step(color, -1))
    fl = _flame(max(3, w - 2), by + 1)
    im.alpha_composite(fl, ((w - fl.width) // 2, 0))
    d.rectangle((0, by, w - 1, by + 1), fill=base(color))
    d.line((0, by, w - 1, by), fill=step(color, 1))
    d.point((2, by + 3), fill=rgba('#f77622'))                                # glow on the bowl
    return im


# ----------------------------------------------------------------------------- cloth

def banner(w, h, color='#a22633', trim=GOLD, rod='#3e2731', tail='point', emblem=None, **_):
    """Hanging banner: rod with knobs, cloth with vertical folds, gold inner trim, V (point) or swallow tail."""
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    px = im.load()
    x0, x1 = 2, w - 3
    cw = x1 - x0 + 1
    cx = (x0 + x1) / 2
    notch = max(3, cw // 2)
    top = 3

    def bottom(x):
        t = abs(x - cx) / (cw / 2)
        return (h - 2 - notch * t) if tail == 'point' else (h - 2 - notch * (1 - t))

    fold = max(4, cw // 4)
    for x in range(x0, x1 + 1):
        for y in range(top, int(bottom(x)) + 1):
            k = (x - x0) % fold
            c = base(color)
            if k == fold - 1:
                c = step(color, -1)
            elif k == 0 and x > x0:
                c = step(color, 1)
            if y < top + 2:                                   # cloth wrapped over the rod
                c = step(color, -2) if y == top else step(color, -1)
            px[x, y] = c
    # gold trim 2px inside the edges
    for x in range(x0 + 2, x1 - 1):
        yb = int(bottom(x)) - 2
        if yb > top + 3:
            px[x, yb] = rgba(trim)
    for y in range(top + 3, h):
        for x in (x0 + 2, x1 - 2):
            if y <= int(bottom(x)) - 2:
                px[x, y] = rgba(trim)
    if emblem:
        import sprites
        e = sprites.render(emblem)
        if e.width > cw - 6:
            e = e.resize((cw - 6, max(1, round(e.height * (cw - 6) / e.width))), Image.NEAREST)
        im.alpha_composite(e, (int(cx - e.width / 2 + 0.5), top + 6))
    _outline(im, outline_of(color))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 1, w - 1, 3), fill=rgba(rod))                             # rod with knobs
    d.line((1, 1, w - 2, 1), fill=step(rod, 2))
    for kx in (0, w - 2):
        d.rectangle((kx, 0, kx + 1, 4), fill=rgba(trim))
        d.point((kx, 0), fill=step(trim, 1))
    return im


def ribbon(w, h, color='#c42f3c', tail=14, drop=5, **_):
    """Title ribbon: a front band (h - drop tall) with two darker tails behind it, cut with a V at the ends,
    and dark fold triangles where the band turns under."""
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    px = im.load()
    bh = h - drop
    th = bh - 2
    dark = art.hue_step(color, -1)            # gentle steps even for palette colours (ramps jump too far here)
    darker = art.hue_step(color, -2)
    o = outline_of(color)
    mid = drop + (th - 1) / 2
    for side in (0, 1):                                       # tails (behind the band)
        for y in range(drop, drop + th):
            cut = round(4 * (1 - abs(y - mid) / (th / 2)))     # V notch, deepest in the middle
            for x in range(max(0, cut), tail + 4):
                xx = x if side == 0 else w - 1 - x
                c = dark
                if y == drop + 1:
                    c = base(color)
                elif y >= drop + th - 2:
                    c = darker
                px[xx, y] = c
        for k in range(drop):                                  # fold triangle under the band end
            for j in range(k + 1):
                x = tail + j if side == 0 else w - 1 - tail - j
                px[x, bh + k - drop + 2 if bh + k - drop + 2 < h else h - 1] = darker
    for y in range(0, bh):                                    # front band
        for x in range(tail, w - tail):
            c = base(color)
            if y == 1:
                c = art.hue_step(color, 1)
            elif y >= bh - 2:
                c = dark
            elif y == 2 * bh // 3 and (x - tail) % 23 not in (0, 1, 2, 11):
                c = dark
            px[x, y] = c
        if 0 < y < bh - 1:                                    # ends curl back
            px[tail, y] = dark
            px[w - tail - 1, y] = dark
    return _outline(im, o, inside=True)


# ----------------------------------------------------------------------------- piles

def _blob(rx, ry, color, seed):
    rnd = random.Random(seed)
    w, h = 2 * rx + 1, 2 * ry + 1
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    px = im.load()
    for y in range(h):
        for x in range(w):
            dx, dy = (x - rx) / (rx + 0.5), (y - ry) / (ry + 0.5)
            if dx * dx + dy * dy <= 1.0:
                px[x, y] = base(color)
    # lit cap top-left, shadow bottom-right
    for y in range(h):
        for x in range(w):
            if not px[x, y][3]:
                continue
            dx, dy = (x - rx) / (rx + 0.5), (y - ry) / (ry + 0.5)
            k = -0.65 * dx - 0.75 * dy
            if k > 0.55:
                px[x, y] = step(color, 2) if k > 0.85 and rnd.random() < 0.6 else step(color, 1)
            elif k < -0.45:
                px[x, y] = step(color, -1)
    if rx > 4 and rnd.random() < 0.5:                       # a crack
        cx, cy = rx + rnd.randint(-2, 2), ry + rnd.randint(-1, 1)
        for i in range(3):
            if 0 <= cx + i < w and 0 <= cy + i // 2 < h and px[cx + i, cy + i // 2][3]:
                px[cx + i, cy + i // 2] = step(color, -1)
    return im


LEAF = ["...##", "..#G#", ".#Gg#", "#Gg#.", "#g#.."]
FLOWER = [".p.", "pyp", ".p."]


def _sprite(rows, pal):
    im = Image.new('RGBA', (len(rows[0]), len(rows)), (0, 0, 0, 0))
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch in pal:
                im.putpixel((x, y), rgba(pal[ch]))
    return im


def rubble(w, h, color='#5a6988', leaves='#3e8948', flowers='#f6757a', seed=5, density=1.0, **_):
    """Pile of rounded boulders (back rows first, each with its own outline so stones read separately),
    with leaf sprigs and small flowers tucked between them."""
    rnd = random.Random(seed)
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    o = outline_of(color)
    rows = []
    y = 3
    while y < h + 4:
        rows.append(y)
        y += rnd.randint(4, 6)
    spots = []
    for ri, cy in enumerate(rows):
        x = rnd.randint(-4, 3)
        while x < w + 4:
            rx, ry = rnd.randint(5, 9), rnd.randint(4, 6)
            if ri == 0 and rnd.random() > 0.75 * density:
                x += rx * 2
                continue
            tone = color if rnd.random() < 0.7 else (step(color, -1) if rnd.random() < 0.6 else step(color, 1))
            b = _blob(rx, ry, tone, rnd.randint(0, 9999))
            layer = Image.new('RGBA', (b.width + 2, b.height + 2), (0, 0, 0, 0))
            layer.alpha_composite(b, (1, 1))
            _outline(layer, o)
            im.alpha_composite(layer, (x - rx - 1, cy - ry - 1))
            spots.append((x, cy - ry))
            x += int(rx * 1.6) + rnd.randint(0, 3)
    if leaves:
        leaf = _outline(_pad(_sprite(LEAF, {'#': step(leaves, -2), 'G': step(leaves, 1), 'g': base(leaves)})),
                        step(leaves, -3) if art._enabled else '#193c3e')
        leaf_r = leaf.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        for (x, y) in spots:                                       # sprigs: 3 leaves fanned out from a joint
            if rnd.random() < 0.22 * density:
                for dx, dy, lf in ((-5, -1, leaf), (1, -1, leaf_r), (-2, -4, leaf if rnd.random() < 0.5 else leaf_r)):
                    im.alpha_composite(lf, (max(0, min(w - lf.width, x + dx)), max(0, min(h - lf.height, y + dy))))
    if flowers:
        fl = _sprite(FLOWER, {'p': flowers, 'y': '#fee761'})
        for (x, y) in spots:
            if rnd.random() < 0.12:
                im.alpha_composite(fl, (max(0, min(w - 3, x + rnd.randint(-3, 3))), max(0, min(h - 3, y + 1))))
    return im


def _pad(im, p=1):
    out = Image.new('RGBA', (im.width + 2 * p, im.height + 2 * p), (0, 0, 0, 0))
    out.alpha_composite(im, (p, p))
    return out


def hay(w, h, color='#feae34', seed=4, **_):
    """Farm pile: hay bales (rounded straw blocks with streaks and twine), back row first."""
    rnd = random.Random(seed)
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    for row, (y_off, bh_rng) in enumerate(((h - 22, (10, 12)), (h - 12, (11, 13)))):
        x = rnd.randint(-8, -2) + row * 7
        while x < w:
            bw, bh = rnd.randint(17, 22), rnd.randint(*bh_rng)
            if row == 0 and rnd.random() < 0.35:
                x += bw
                continue
            bale = Image.new('RGBA', (bw + 2, bh + 2), (0, 0, 0, 0))
            bp = bale.load()
            for yy in range(1, bh + 1):
                for xx in range(1, bw + 1):
                    if (xx in (1, bw) and yy in (1, bh)):
                        continue
                    c = base(color)
                    if yy == 1 or xx == 1:
                        c = step(color, 1)
                    elif yy >= bh - 1 or xx == bw:
                        c = step(color, -1)
                    elif (xx * 7 + yy * 13 + rnd.randint(0, 3)) % 9 == 0:
                        c = step(color, -1)                     # straw stalk ends
                    elif (xx * 5 + yy * 11) % 17 == 0:
                        c = step(color, 1)
                    bp[xx, yy] = c
            for tx in (1 + bw // 4, bw - bw // 4):               # twine bands
                for yy in range(1, bh + 1):
                    if bp[tx, yy][3]:
                        bp[tx, yy] = rgba('#733e39') if yy > 1 else rgba('#b86f50')
            _outline(bale, outline_of(color))
            im.alpha_composite(bale, (x, max(0, y_off + rnd.randint(-1, 1))))
            x += bw + rnd.randint(-2, 2)
    return im


# ----------------------------------------------------------------------------- ornaments

def _feather(size, root, tip, width, color):
    """One tapered feather (filled), coloured as metal with its own outline so stacked feathers stay readable."""
    mask = Image.new('L', size, 0)
    d = ImageDraw.Draw(mask)
    (x0, y0), (x1, y1) = root, tip
    L = math.hypot(x1 - x0, y1 - y0) or 1
    nx, ny = -(y1 - y0) / L, (x1 - x0) / L                    # normal
    bow = 0.22 * L                                             # feathers bulge upward
    pts_a, pts_b = [], []
    for i in range(13):
        t = i / 12
        cx, cy = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t - bow * math.sin(math.pi * t)
        r = width * (1 - t) ** 0.7 / 2
        pts_a.append((cx + nx * r, cy + ny * r))
        pts_b.append((cx - nx * r, cy - ny * r))
    d.polygon(pts_a + pts_b[::-1], fill=255)
    return _metal(mask, color)


def flourish(w, h, color=GOLD, gem='#e43b44', **_):
    """Symmetric ornament: a peak at the centre, swoops down to both sides ending in feathered wings that rise
    up and out (the "winged crest" under quest/shop titles)."""
    half = (w + 1) // 2
    cx = half - 1
    root = (round(half * 0.30), round(h * 0.66))
    swoop = Image.new('L', (half, h), 0)
    _stroke(swoop, _bezier((cx, 2), (cx - half * 0.22, h - 2), (half * 0.52, h - 1), root), 2)
    left = _metal(swoop, color)
    # wing: long feathers first (behind), shorter ones on top
    for (ang, k, wd) in ((168, 1.0, 5), (148, 0.86, 5), (126, 0.66, 4), (104, 0.46, 3)):
        a = math.radians(ang)
        L = min(root[0] + 2, h) * 1.25 * k
        tip = (root[0] + L * math.cos(a), root[1] - L * math.sin(a))
        left.alpha_composite(_feather((half, h), root, tip, wd, color))
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    im.alpha_composite(left, (0, 0))
    im.alpha_composite(left.transpose(Image.Transpose.FLIP_LEFT_RIGHT), (w - half, 0))
    if gem:
        g = _sprite(["..#..", ".#R#.", "#RrR#", ".#r#.", "..#.."],
                    {'#': step(color, -2), 'R': gem, 'r': step(gem, -1)})
        im.alpha_composite(g, (w // 2 - 2, 0))
    return im


def note(w, h, color='#ead4aa', seal='#a22633', seed=1, **_):
    """Pinned parchment: uneven edges, folded corner, scribbled lines, wax seal, pin."""
    rnd = random.Random(seed)
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((1, 2, w - 2, h - 2), fill=base(color))
    d.line((w - 2, 3, w - 2, h - 2), fill=step(color, -1))
    d.line((2, h - 2, w - 2, h - 2), fill=step(color, -1))
    for y in range(2, h - 1, 3):                                     # torn edge bites
        if rnd.random() < 0.3:
            im.putpixel((1 if rnd.random() < 0.5 else w - 2, y), (0, 0, 0, 0))
    ink = '#733e39' if art._enabled else '#5a3a28'
    y = 5
    while y < h - (6 if seal else 3):
        lw = rnd.randint(max(2, (w - 6) // 2), w - 6)
        x = 3
        while x < 3 + lw:
            seg = rnd.randint(2, 4)
            d.line((x, y, min(3 + lw, x + seg - 1), y), fill=rgba(ink))
            x += seg + 1
        y += 2 if rnd.random() < 0.7 else 3
    if seal and h > 10:
        d.rectangle((w - 7, h - 6, w - 5, h - 4), fill=rgba(seal))
        d.point((w - 7, h - 6), fill=step(seal, 1))
    # folded corner (bottom-left)
    im.putpixel((1, h - 2), (0, 0, 0, 0))
    im.putpixel((2, h - 2), step(color, -2))
    im.putpixel((1, h - 3), step(color, -2))
    out = _outline(im.crop((0, 1, w, h)), '#3e2731', inside=True)
    full = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    full.alpha_composite(out, (0, 1))
    # pin
    ImageDraw.Draw(full).rectangle((w // 2 - 1, 0, w // 2, 1), fill=rgba('#e43b44'))
    full.putpixel((w // 2 - 1, 0), rgba('#f6757a'))
    return full


def divider(w, h=7, color=GOLD, gem='#e43b44', **_):
    mask = Image.new('L', (w, h), 0)
    d = ImageDraw.Draw(mask)
    cy = h // 2
    d.line((4, cy, w - 5, cy), fill=255)
    for x0, sgn in ((1, 1), (w - 2, -1)):                            # arrow tips pointing outward
        d.polygon([(x0, cy), (x0 + 3 * sgn, cy - 2), (x0 + 3 * sgn, cy + 2)], fill=255)
    for x in (w // 4, 3 * w // 4):                                   # beads
        d.rectangle((x - 1, cy - 1, x + 1, cy + 1), fill=255)
    im = _metal(mask, color)
    if gem:
        g = _sprite([".###.", "#RRr#", "#Rrr#", ".###."], {'#': step(color, -2), 'R': gem, 'r': step(gem, -1)})
        im.alpha_composite(g, (w // 2 - 2, cy - 2))
    return im


FRAME_KINDS = {
    'gold':  dict(rim=GOLD, inner='#262b44'),
    'wood':  dict(rim='#b86f50', inner='#3e2731'),
    'stone': dict(rim='#8b9bb4', inner='#262b44'),
    'iron':  dict(rim='#c0cbdc', inner='#3a4466'),
}


def frame(w, h, kind='gold', inner=None, rim=None, **_):
    """Framed panel: dark outline (cut corners), 2px rim lit top-left / dark bottom-right, dark inner line,
    flat inner fill."""
    k = FRAME_KINDS.get(kind, FRAME_KINDS['gold'])
    rim = rim or k['rim']
    inner = inner or k['inner']
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    o = step(rim, -4) if art._enabled else rgba('#3e2731')
    d.rectangle((0, 0, w - 1, h - 1), fill=o)
    d.rectangle((1, 1, w - 2, h - 2), fill=base(rim))
    d.line((1, 1, w - 2, 1), fill=step(rim, 1))
    d.line((1, 1, 1, h - 2), fill=step(rim, 1))
    d.line((2, h - 2, w - 2, h - 2), fill=step(rim, -1))
    d.line((w - 2, 2, w - 2, h - 2), fill=step(rim, -1))
    d.rectangle((3, 3, w - 4, h - 4), fill=step(rim, -3) if art._enabled else rgba('#3e2731'))
    d.rectangle((4, 4, w - 5, h - 5), fill=base(inner))
    for cx, cy in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        im.putpixel((cx, cy), (0, 0, 0, 0))
    return im


def well(size=18, inner='#262b44'):
    """A dark recessed slot square (for slot bars): outline, shadowed top-left, lit bottom-right."""
    im = Image.new('RGBA', (size, size), rgba(step(inner, -1)))
    d = ImageDraw.Draw(im)
    d.rectangle((1, 1, size - 2, size - 2), fill=base(inner))
    d.line((1, 1, size - 2, 1), fill=step(inner, -1))
    d.line((1, 1, 1, size - 2), fill=step(inner, -1))
    d.line((2, size - 2, size - 2, size - 2), fill=step(inner, 1))
    d.line((size - 2, 2, size - 2, size - 2), fill=step(inner, 1))
    return im


PROPS = {'wall': wall, 'planks': planks, 'pillar': pillar, 'brazier': brazier, 'banner': banner, 'ribbon': ribbon,
         'rubble': rubble, 'hay': hay, 'flourish': flourish, 'note': note, 'divider': divider, 'frame': frame}


def render(name, w, h, **opts):
    return PROPS[name](w, h, **opts)
