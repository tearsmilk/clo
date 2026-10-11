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


def volume(text, ramp=GOTHIC, scale=3, depth=4, weight=1, accent=None, seed=1, pad=2, gap=None):
    """Volumetric title letters (3D block letters), clean:
    - shape: pixfont slab capitals at `scale`, grown by `weight` px all round (chunky, even strokes), convex
      corners rounded by 1 px - no nib cuts, no checker, nothing that reads as noise
    - front face: two flat bands (light top, base below) - a bevel: lit 1 px on every top / left-facing edge
      (highlight), dark 1 px on every bottom / right-facing edge (also round the counters)
    - extrusion `depth` px down-right (light from the top-left): right-facing side faces dark mid, bottom
      faces shadow, the back edge darkest - shaded by which way each side faces, visible inside counters too
    - one outline round everything in the darkest tone; a small glint on the upper left of each letter
    - accent: None | 'sparkle' (tiny 4-point stars in the highlight tone) | 'cracks' (the tutorial's blood)"""
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
    for (x, y) in M:
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
        put(q, ramp[0] if back else ramp[1] if face == 'bottom' else ramp[2])
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
