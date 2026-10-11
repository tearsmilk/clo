#!/usr/bin/env python3
"""Decorative title letters in five steps (from a pixel-art lettering tutorial the user showed - blackletter
"B" by @ribbitknight; the art is a reference, the method is ours to reuse):

    1 shape      bold letter with character: broad-nib cuts (top-left and bottom-right corners of stroke
                 ends cut at 45 deg, like a calligraphy pen), strokes >= 3 px, counters >= 2 px
    2 outline    1 px ring in the LIGHTEST tone round the letter and round its counters - on a dark
                 background a light outline makes the letter glow instead of sinking
    3 gradient   vertical: light at the top, darker at the bottom, with a 2-row checker transition between
                 the bands (a lettering style - the checker stays in narrow transition rows, never all over)
    4 shadows    inner: the shadow tone just inside the outline on the top / left (the fill sits below a
                 raised rim lit from the top-left); outer: the letter + outline repeated `depth` px down-right
                 in the shadow tone, behind it - thickness, the letter stands off the background
    5 accent     ONE saturated accent colour (2 tones) used sparingly: cracks starting at the edge and running
                 into the stroke, drips falling from bottom edges over the outline, plus a light speckle
                 texture in the top band
Palette: five tones of one hue + one accent (the reference: #241245 #4a337b #734ca2 #8c6db0 #b6a8c8 + #dc3783).

    python3 lettering.py volume OUT.png TEXT [#hex] [scale]   clean 3D block letters (the default for titles)
    python3 lettering.py chart OUT.png [TEXT]     the tutorial's five steps side by side + a word
    python3 lettering.py word OUT.png TEXT        the tutorial look (stage 5) on a transparent background
"""
import random
import sys
from PIL import Image

from pixfont import _slab_mask


def _hex(c):
    c = c.lstrip('#')
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4)) + (255,)


# measured from the reference swatches: darkest, shadow, dark mid, base, light (outline) ...
GOTHIC = [_hex(c) for c in ('#241245', '#4a337b', '#734ca2', '#8c6db0', '#b6a8c8', '#d6cce4')]
BLOOD = [_hex(c) for c in ('#7d1745', '#dc3783')]          # accent: dark, light
N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
N8 = N4 + ((1, 1), (1, -1), (-1, 1), (-1, -1))


def shape(text, scale=3, gap=4, nib=True, weight=1):
    """Letter mask as a set of pixels: the slab capitals of pixfont at `scale`, vertical strokes made
    heavier by `weight` px on each side (thick stems, thinner horizontals - the contrast of a broad pen,
    what makes blackletter look heavy; counters shrink but keep >= 2 px), broad-nib cuts on the top-left and
    bottom-right corners of every solid stroke end."""
    m = _slab_mask(text, scale, gap + 2 * weight)
    mp = m.load()
    M = {(x, y) for y in range(m.height) for x in range(m.width) if mp[x, y]}
    if weight:
        stems = {(x, y) for x, y in M if all((x, y + j) in M for j in range(-scale, scale + 1))
                 or sum((x, y + j) in M for j in range(-2 * scale, 2 * scale + 1)) >= 3 * scale}
        grown = set(M)
        for x, y in stems:
            for i in range(1, weight + 1):
                grown |= {(x - i, y), (x + i, y)}
        M = {(x + weight, y) for x, y in grown}
    if not nib or scale < 2:
        return M
    k = scale - 1
    cut = set()
    for (x, y) in M:
        for sx, sy in ((1, 1), (-1, -1)):              # top-left corner (+1,+1 inward), bottom-right (-1,-1)
            if ((x - sx, y) in M) or ((x, y - sy) in M) or ((x - sx, y - sy) in M):
                continue
            if all((x + sx * i, y + sy * j) in M for i in range(k + 1) for j in range(k + 1)):
                cut |= {(x + sx * i, y + sy * j) for i in range(k) for j in range(k) if i + j < k}
    return M - cut


def render(text, stage=5, ramp=GOTHIC, accent=BLOOD, scale=3, depth=2, nib=True, seed=1, pad=6, weight=None):
    """The letter(s) after `stage` steps, as an RGBA image with `pad` px of air."""
    if weight is None:                                # heavy stems need room: from scale 4 up (at 3 the
        weight = 1 if scale >= 4 else 0              # diagonals of М / Ж / Ю would vanish between them)
    M = shape(text, scale, nib=nib, weight=weight)
    xs, ys = [p[0] for p in M], [p[1] for p in M]
    W, H = max(xs) + 1 + 2 * pad + depth, max(ys) + 1 + 2 * pad + depth
    M = {(x + pad, y + pad) for x, y in M}
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    put = img.putpixel
    ring = {(x + dx, y + dy) for x, y in M for dx, dy in N8} - M
    body = M | (ring if stage >= 2 else set())
    if stage >= 4:                                       # outer shadow: the letter pushed down-right, behind
        ext = {(x + i, y + i) for x, y in body for i in range(1, depth + 1)} - body
        for p in ext:
            put(p, ramp[1])
    top, bot = min(y for _, y in M), max(y for _, y in M)

    def fill(x, y):
        if stage < 3:
            return 3
        t = (y - top) / max(1, bot - top)
        bands = (0.34, 0.68)                             # light / base / dark mid, checker rows between
        for b, (hi, lo) in zip(bands, ((4, 3), (3, 2))):
            yb = top + round(b * (bot - top))
            if yb - 1 <= y <= yb:
                return hi if (x + y) % 2 == 0 else lo
        return 4 if t < bands[0] else 3 if t < bands[1] else 2
    for (x, y) in M:
        i = fill(x, y)
        if stage >= 3 and i == 4 and y - top < 2:
            i = 4
        put((x, y), ramp[i])
    if stage >= 2:
        for p in ring:
            put(p, ramp[4])
    if stage >= 4:                                       # inner shadow under the lit rim (top / left)
        for (x, y) in M:
            if (x - 1, y) in ring or (x, y - 1) in ring:
                put((x, y), ramp[1] if (x, y - 1) in ring and (x - 1, y) in ring else ramp[2])
    if stage >= 5:
        rnd = random.Random(seed)
        edge = sorted(p for p in M if any((p[0] + dx, p[1] + dy) in ring for dx, dy in N4))
        for _ in range(max(3, len(M) // 110)):           # cracks: from an edge into the stroke, a dark
            x, y = rnd.choice(edge)                      # lower lip, a splatter cluster where they start
            for (sx, sy) in ((x, y), (x + 1, y), (x, y + 1)):
                if (sx, sy) in M or (sx, sy) in ring:
                    put((sx, sy), accent[1] if rnd.random() < 0.6 else accent[0])
            for _ in range(rnd.randint(4, 8)):
                if (x, y) not in M:
                    break
                put((x, y), accent[1])
                if (x + 1, y) in M and rnd.random() < 0.4:
                    put((x + 1, y), accent[1])
                if (x, y + 1) in M:
                    put((x, y + 1), accent[0])
                x += rnd.choice((-1, 0, 0, 1))
                y += 1
        bottoms = [p for p in M if (p[0], p[1] + 1) in ring]
        for _ in range(max(2, len(M) // 160)):           # drips over the outline and the outer shadow
            x, y = rnd.choice(bottoms)
            n = rnd.randint(2, 4 + depth)
            for j in range(1, n + 1):
                put((x, y + j), accent[1] if j < n else accent[0])
            put((x, y), accent[1])
        top_band = [p for p in M if p[1] - top < (bot - top) * 0.3 and (p[0] + 1, p[1]) in M]
        for _ in range(len(M) // 90):                    # light speckles (2 px) in the top band
            x, y = rnd.choice(top_band)
            put((x, y), ramp[5])
            put((x + 1, y), ramp[4])
    return img


def _holes(M, W, H):
    """Background pixels enclosed by the letter (counters of О, Б, Я ...)."""
    outside, todo = set(), [(x, y) for x in range(-1, W + 1) for y in (-1, H)] + \
        [(x, y) for y in range(-1, H + 1) for x in (-1, W)]
    while todo:
        p = todo.pop()
        if p in outside or p in M or not (-1 <= p[0] <= W and -1 <= p[1] <= H):
            continue
        outside.add(p)
        todo += [(p[0] + dx, p[1] + dy) for dx, dy in N4]
    return {(x, y) for x in range(W) for y in range(H)} - M - outside


def volume(text, ramp=GOTHIC, scale=3, depth=4, weight=1, accent=None, seed=1, pad=2, gap=None, font=None):
    """Volumetric title letters (3D block letters), clean:
    - shape: pixfont slab capitals at `scale`, grown by `weight` px all round (chunky, even strokes), convex
      corners rounded by 1 px - no nib cuts, no checker, nothing that reads as noise
    - front face: two flat bands (light top, base below) - a bevel: lit 1 px on every top / left-facing edge
      (highlight), dark 1 px on every bottom / right-facing edge (also round the counters)
    - extrusion `depth` px down-right (light from the top-left): the whole back in the darkest tone, a thin
      shadow-tone edge on the first layer of the right faces - the user asked twice for a darker back; a mid
      tone there flattens the letter and melts it into the face - shaded by which way each side faces, visible inside counters too
    - one outline round everything in the darkest tone; a small glint on the upper left of each letter
    - accent: None | 'sparkle' (tiny 4-point stars in the highlight tone) | 'cracks' (the tutorial's blood)"""
    if font:                                           # a converted pixel font (font_pixel.py): its own
        import font_pixel                              # shapes, no growing / smoothing
        M = font_pixel.text_mask(font, text, spacing=gap if gap is not None else 2)
        y_min = min(y for _, y in M)
        M = {(x, y - y_min) for x, y in M}
        weight = 0
    else:
        g = gap if gap is not None else scale + 2 * weight      # air between letters grows with the size
        m = _slab_mask(text, scale, g)
        mp = m.load()
        M = {(x, y) for y in range(m.height) for x in range(m.width) if mp[x, y]}
        holes = _holes(M, m.width, m.height)                   # counters: never filled by growing / smoothing
        for _ in range(weight):
            M = M | ({(x + dx, y + dy) for x, y in M for dx, dy in N8} - holes)
        near = {(x + dx, y + dy) for x, y in M for dx, dy in N8} - M - holes
        M |= {p for p in near if sum((p[0] + dx, p[1] + dy) in M for dx, dy in N8) >= 5}   # smooth stair notches
    corners = set()
    for (x, y) in (M if not font else ()):             # a real font keeps its sharp corners and spurs
        for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            if ((x + dx, y) not in M and (x, y + dy) not in M and (x + dx, y + dy) not in M
                    and (x - dx, y) in M and (x, y - dy) in M):
                corners.add((x, y))
    M -= corners
    off = pad + 1
    M = {(x + off, y + off) for x, y in M}
    def facing(x, y):                                  # smoothed outward normal of the edge at (x, y): a
        nx = ny = 0                                    # staircase diagonal gets ONE direction, not stripes
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if (x + dx, y + dy) not in M:
                    nx += dx
                    ny += dy
        return 'bottom' if ny > nx * 1.15 else 'right'
    E = {}
    for i in range(depth, 0, -1):                      # back to front: nearer layers win
        for (x, y) in M:
            q = (x + i, y + i)
            if q in M or (x + 1, y + 1) in M:
                continue
            E[q] = (facing(x, y), i)
    for q in list(E):
        if q in M:
            del E[q]
    solid = M | set(E)
    W = max(x for x, _ in solid) + off + 1
    H = max(y for _, y in solid) + off + 1
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    put = img.putpixel
    for q, (face, i) in E.items():
        back = (q[0] + 1, q[1] + 1) not in solid and i == depth
        # the back (the user: "the old look was better, just make the back darker"): the whole extrusion in
        # the darkest tone, only the first layer of the right faces keeps the shadow tone as a thin edge
        put(q, ramp[1] if (face == 'right' and i == 1) else ramp[0])
    top, bot = min(y for _, y in M), max(y for _, y in M)
    split = top + round(0.42 * (bot - top))
    for (x, y) in M:
        c = ramp[4] if y < split else ramp[3]
        if any((x + dx, y + dy) not in M for dx, dy in N4):
            nx = ny = 0                                 # bevel by the smoothed edge direction: up-left
            for dx in range(-2, 3):                     # lit, down-right dark, an edge running along the
                for dy in range(-2, 3):                 # light (up-right / down-left) stays plain - so a
                    if (x + dx, y + dy) not in M:       # staircase diagonal does not stripe
                        nx += dx
                        ny += dy
            d = (nx + ny) / (abs(nx) + abs(ny) or 1)
            c = ramp[5] if d < -0.35 else ramp[2] if d > 0.35 else c
        put((x, y), c)
    for p in {(x + dx, y + dy) for x, y in solid for dx, dy in N4} - solid:
        put(p, ramp[0])
    rnd = random.Random(seed)
    for (x, y) in sorted(M):                            # glints: a short bright run inside the top band
        if (x - 1, y) in M and (x, y - 1) in M and (x - 2, y) not in M and y < split - 1 and rnd.random() < 0.25:
            for j in range(2):
                if (x + 1, y + j) in M:
                    put((x + 1, y + j), ramp[5])
    if accent == 'sparkle':
        pts = sorted(p for p in M if (p[0] - 1, p[1]) not in M and (p[0], p[1] - 1) not in M)
        for (x, y) in rnd.sample(pts, min(3, len(pts))):
            cx, cy = x - 2, y - 2
            if 0 < cx < W - 1 and 0 < cy < H - 1 and img.getpixel((cx, cy))[3] == 0:
                put((cx, cy), ramp[5])
                for dx, dy in N4:
                    if img.getpixel((cx + dx, cy + dy))[3] == 0:
                        put((cx + dx, cy + dy), ramp[4])
    return img


def chunky(text, scale=2, weight=None, gap=None):
    """Chunky letter mask (the base of the arcade / bands styles): the bold small pixfont capitals (2-column
    stems, 1-row bars) scaled x`scale` - 4 px stems, 2 px bars at scale 2 - with convex corners rounded by
    1 px. Growing slab letters instead closed the counters of G, A, M (unreadable). Returns a pixel set."""
    from pixfont import _round_corners
    m = _slab_mask(text, 1, gap if gap is not None else 2, 'bold')
    m = m.resize((m.width * scale, m.height * scale), Image.NEAREST)
    m = _round_corners(m)
    mp = m.load()
    return {(x, y) for y in range(m.height) for x in range(m.width) if mp[x, y]}


def _canvas(pts, pad=1):
    xs, ys = [x for x, _ in pts], [y for _, y in pts]
    return Image.new('RGBA', (max(xs) + 1 + pad, max(ys) + 1 + pad), (0, 0, 0, 0))


ARCADE = {'gold': ('#ffd23f', '#f08a1c', '#e0401c', '#1a0e0a'),        # face, band, inner shadow, outline
          'sky': ('#8fe3ff', '#3f9fe0', '#2a5fb8', '#0c1630'),
          'mint': ('#a8f0a0', '#3fbf6a', '#1f8a4a', '#0a1e12'),
          'ruby': ('#ff9a8a', '#e04050', '#a01c3c', '#1e0a10')}


def arcade(text, palette='gold', scale=2, drop=1, gap=None, px=1):
    """Arcade title letters (the user's "GAME" reference): chunky letters, a light face, the bottom quarter
    in a warmer darker band, the same band as a 1-2 px inner shadow under every bar and over every counter
    (light from above), a 1 px near-black outline that is `drop` px thicker at the bottom (the letter
    stands on it). px = integer upscale AFTER styling (big "art pixels" like the reference)."""
    face, band, inner, out = [_hex(c) for c in (ARCADE.get(palette, palette) if isinstance(palette, str)
                                                  else palette)]
    M = {(x + 1, y + 1) for x, y in chunky(text, scale, gap=gap)}
    top, bot = min(y for _, y in M), max(y for _, y in M)
    split = bot - max(2, (bot - top + 1) // 4) + 1
    solid = M | {(x, y + k) for x, y in M for k in range(1, drop + 1)}
    ring = {(x + dx, y + dy) for x, y in solid for dx, dy in N8} - solid
    img = _canvas(solid | ring)
    for p in solid | ring:
        img.putpixel(p, out)
    for (x, y) in M:
        c = band if y >= split else face
        if y > top and (x, y - 1) not in M and any((x, yy) in M for yy in range(top, y - 1)):
            c = inner                                   # the row under a counter / an overhang: inner shadow
        img.putpixel((x, y), c)
    return img.resize((img.width * px, img.height * px), Image.NEAREST) if px > 1 else img


BANDS = {'sunset': ('#d2604a', '#a83660', '#6e3a72', '#3a1c34', '#e88a8a', '#f2c0a8'),  # top, mid, low,
         'ocean': ('#5ad0d0', '#3a86c8', '#4a4aa0', '#141a3a', '#9ae8f0', '#e0fbff'),   # outline, rim, glint
         'forest': ('#a8d04a', '#4aa050', '#2a6a5a', '#0e2218', '#c8f070', '#f0ffc0'),
         'royal': ('#f0c040', '#c86a28', '#8a2a3a', '#2a0e14', '#ffe08a', '#fff4d0')}


def bands(text, palette='sunset', scale=2, drop=2, gap=None, px=1):
    """Banded title letters (the user's pink-purple reference): chunky letters, the face cut into three
    hard horizontal bands (light top, mid, dark low - the same rows for the whole word), a 1 px rim of the
    rim tone down the right-facing edges, a glint pixel on each top-left corner, a dark outline and a `drop`
    px thickness under the letter in the outline tone."""
    t1, t2, t3, out, rim, glint = [_hex(c) for c in (BANDS.get(palette, palette) if isinstance(palette, str)
                                                    else palette)]
    M = {(x + 1, y + 1) for x, y in chunky(text, scale, gap=gap)}
    top, bot = min(y for _, y in M), max(y for _, y in M)
    h = bot - top + 1
    solid = M | {(x, y + k) for x, y in M for k in range(1, drop + 1)}
    ring = {(x + dx, y + dy) for x, y in solid for dx, dy in N8} - solid
    img = _canvas(solid | ring)
    for p in solid | ring:
        img.putpixel(p, out)
    for (x, y) in M:
        t = (y - top) / h
        c = t1 if t < 0.36 else t2 if t < 0.68 else t3
        if (x + 1, y) not in M and (x, y - 1) in M:
            c = rim                                     # rim down the right-facing edges
        img.putpixel((x, y), c)
    for (x, y) in M:                                     # glints on top-left corners
        if (x - 1, y) not in M and (x, y - 1) not in M and (x + 1, y) in M and (x, y + 1) in M:
            img.putpixel((x + 1, y + 1), glint) if (x + 1, y + 1) in M else None
    return img.resize((img.width * px, img.height * px), Image.NEAREST) if px > 1 else img


MAZE = {'snow': ('#f4f4f8', '#3e3e4a', '#c4c4d4', '#8a8a9a'),       # face, groove, corner chamfer, dead area
        'stone': ('#c9c2b4', '#2a2622', '#9a9286', '#6e675e'),
        'neon': ('#7ff0d8', '#101a24', '#3fa894', '#28606a')}


def maze(text, palette='snow', k=3, gutter=2):
    """Maze title letters (the user's square-block reference): every letter is a solid block filling its
    cell; its shape is cut in by 1 px grooves. Built from the 5x7 pixfont glyph: each empty unit of the cell
    becomes a groove running through the unit centres (k px per unit, so the groove is 1 px and joins its
    neighbours); a groove that reaches the cell edge opens there (slot); a lone empty corner unit becomes a
    light chamfer pixel; a big empty area open to the edge is filled with the dead-area tone."""
    from pixfont import _glyph
    face, groove, cham, dead = [_hex(c) for c in (MAZE.get(palette, palette) if isinstance(palette, str)
                                                 else palette)]
    glyphs = [_glyph(ch) for ch in text]
    cw = 5 * k
    ch_ = 7 * k
    W = len(glyphs) * (cw + gutter) + gutter
    img = Image.new('RGBA', (W, ch_ + 2 * gutter), (0, 0, 0, 0))
    for gi, rows in enumerate(glyphs):
        rows = rows[:7]
        ox, oy = gutter + gi * (cw + gutter), gutter
        if not any('#' in r for r in rows):
            continue
        for y in range(ch_):
            for x in range(cw):
                img.putpixel((ox + x, oy + y), face)
        bg = {(c, r) for r in range(7) for c in range(min(5, len(rows[r]))) if rows[r][c] != '#'}
        seen = set()
        for u in sorted(bg):
            if u in seen:
                continue
            comp, todo = set(), [u]
            while todo:
                p = todo.pop()
                if p in comp or p not in bg:
                    continue
                comp.add(p)
                todo += [(p[0] + dx, p[1] + dy) for dx, dy in N4]
            seen |= comp
            border = [p for p in comp if p[0] in (0, 4) or p[1] in (0, 6)]
            if len(comp) == 1 and border and next(iter(comp)) in ((0, 0), (4, 0), (0, 6), (4, 6)):
                cx, cy = border[0]
                img.putpixel((ox + (0 if cx == 0 else cw - 1), oy + (0 if cy == 0 else ch_ - 1)), cham)
                continue
            c0, c1 = min(c for c, _ in comp), max(c for c, _ in comp)
            r0, r1 = min(r for _, r in comp), max(r for _, r in comp)
            sides = {('l' if c0 == 0 else ''), ('r' if c1 == 4 else ''), ('t' if r0 == 0 else ''),
                     ('b' if r1 == 6 else '')} - {''}
            if len(sides) >= 2 and len(comp) >= 4:            # a big area open on two sides: dead tone
                for (c, r) in comp:
                    for y in range(k):
                        for x in range(k):
                            img.putpixel((ox + c * k + x, oy + r * k + y), dead)
                continue
            mid = k // 2                                      # ONE groove through the unit centres: toward
            horiz = (c1 - c0 >= r1 - r0) if not sides else bool(sides & {'l', 'r'})   # the opening if the
            if horiz:                                         # area is open, else along its long side
                yy = oy + round((r0 + r1) / 2 * k) + mid      # cell edge where the area does
                xa = ox + (0 if c0 == 0 else c0 * k + mid)
                xb = ox + (cw - 1 if c1 == 4 else c1 * k + mid)
                for x in range(xa, xb + 1):
                    img.putpixel((x, yy), groove)
            else:
                xx = ox + round((c0 + c1) / 2 * k) + mid
                ya = oy + (0 if r0 == 0 else r0 * k + mid)
                yb = oy + (ch_ - 1 if r1 == 6 else r1 * k + mid)
                for y in range(ya, yb + 1):
                    img.putpixel((xx, y), groove)
    return img


def styles_chart(path, k=3):
    """Every title style on the same words, for picking."""
    rows = [('arcade gold', arcade('ХОКАРИЯ', 'gold')), ('arcade sky', arcade('МЕНЮ', 'sky')),
            ('bands sunset', bands('МАГАЗИН', 'sunset')), ('bands ocean', bands('ВИКИ', 'ocean')),
            ('maze snow', maze('ХОКАРИЯ', 'snow')), ('volume', volume('ПРОФИЛЬ', scale=2, depth=3))]
    W = max(im.width for _, im in rows) + 20
    H = sum(im.height for _, im in rows) + 10 * (len(rows) + 1)
    bg = Image.new('RGBA', (W, H), (232, 228, 240, 255))
    y = 10
    for _, im in rows:
        bg.alpha_composite(im, ((W - im.width) // 2, y))
        y += im.height + 10
    bg.resize((W * k, H * k), Image.NEAREST).save(path)


def chart(path, letter='Б', word='МЕНЮ', k=4):
    """The five steps of one letter next to each other plus a finished word, on a dark background, x k."""
    stages = [render(letter, s, scale=4, depth=3) for s in range(1, 6)]
    w = render(word, 5, scale=3, depth=2)
    gap = 10
    W = sum(s.width for s in stages) + gap * 6
    H = max(s.height for s in stages) + w.height + gap * 3
    W = max(W, w.width + 2 * gap)
    bg = Image.new('RGBA', (W, H), (28, 22, 64, 255))
    x = gap
    for s in stages:
        bg.alpha_composite(s, (x, gap))
        x += s.width + gap
    bg.alpha_composite(w, ((W - w.width) // 2, gap * 2 + max(s.height for s in stages)))
    bg.resize((W * k, H * k), Image.NEAREST).save(path)


if __name__ == '__main__':
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] == 'chart':
        chart(a[1], *(a[2:3] or ['Б']))
        print('chart ->', a[1])
    elif len(a) >= 3 and a[0] == 'volume':
        from kitchen import _r5
        ramp = _r5(a[3]) if len(a) > 3 else GOTHIC
        volume(a[2], ramp, scale=int(a[4]) if len(a) > 4 else 3).save(a[1])
        print('volume ->', a[1])
    elif len(a) >= 3 and a[0] == 'word':
        render(a[2]).save(a[1])
        print('word ->', a[1])
    else:
        print(__doc__)
