"""Pixel-art rendering kit: a curated palette with shade ramps, hand-structured textures, frames, plates and
buttons. Everything the builder paints goes through here so menus look drawn, not generated.

Palette: ENDESGA 32 (free pixel-art palette by ENDESGA). Colours are organised into ramps (dark -> light) with
hue shifting built in: shadows drift to purple/blue, highlights to yellow. `step(c, n)` walks a colour n steps
along its ramp - use it instead of mixing with black/white, which gives muddy greys.
"""
import math, random
from PIL import Image, ImageDraw

ENDESGA32 = ['#be4a2f', '#d77643', '#ead4aa', '#e4a672', '#b86f50', '#733e39', '#3e2731', '#a22633',
             '#e43b44', '#f77622', '#feae34', '#fee761', '#63c74d', '#3e8948', '#265c42', '#193c3e',
             '#124e89', '#0099db', '#2ce8f5', '#ffffff', '#c0cbdc', '#8b9bb4', '#5a6988', '#3a4466',
             '#262b44', '#181425', '#ff0044', '#68386c', '#b55088', '#f6757a', '#e8b796', '#c28569']

RAMPS = [  # dark -> light
    ['#181425', '#3e2731', '#733e39', '#b86f50', '#e4a672', '#ead4aa'],              # wood / brown
    ['#3e2731', '#733e39', '#be4a2f', '#d77643', '#e4a672', '#ead4aa'],              # terracotta / tan
    ['#3e2731', '#733e39', '#c28569', '#e8b796', '#ead4aa'],                         # skin / sand
    ['#181425', '#3e2731', '#a22633', '#e43b44', '#f6757a', '#e8b796'],              # red
    ['#3e2731', '#a22633', '#ff0044', '#f6757a', '#ffffff'],                         # hot pink-red
    ['#3e2731', '#be4a2f', '#f77622', '#feae34', '#fee761', '#ffffff'],              # orange / gold
    ['#181425', '#193c3e', '#265c42', '#3e8948', '#63c74d', '#fee761'],              # green
    ['#181425', '#262b44', '#124e89', '#0099db', '#2ce8f5', '#ffffff'],              # blue / sky
    ['#181425', '#262b44', '#3a4466', '#5a6988', '#8b9bb4', '#c0cbdc', '#ffffff'],   # grey-blue / stone
    ['#181425', '#3e2731', '#68386c', '#b55088', '#f6757a', '#ead4aa'],              # purple / magenta
]

_enabled = True     # hue-shifted shading on
_strict = False     # True: snap every colour to ENDESGA 32


def set_palette(name):
    """'endesga32' (default): palette ramps for palette colours, hue-shifted shading for any other colour.
    'endesga32-strict': snap every colour to the palette. 'none': plain lighten/darken."""
    global _enabled, _strict
    _enabled = name not in (None, 'none', False)
    _strict = name == 'endesga32-strict'


def rgba(c, a=255):
    if isinstance(c, tuple):
        return c if len(c) == 4 else tuple(c) + (a,)
    c = c.lstrip('#')
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), a)


def _dist(a, b):
    # "redmean" perceptual distance - cheap and good enough for palette matching
    rm = (a[0] + b[0]) / 2
    dr, dg, db = a[0] - b[0], a[1] - b[1], a[2] - b[2]
    return math.sqrt((2 + rm / 256) * dr * dr + 4 * dg * dg + (2 + (255 - rm) / 256) * db * db)


_RAMPS_RGB = [[rgba(c) for c in r] for r in RAMPS]


def nearest(c):
    c = rgba(c)
    return min((rgba(p) for p in ENDESGA32), key=lambda p: _dist(c, p))


def ramp_of(c):
    """(ramp, index) for the palette colour closest to c, preferring ramps whose mid tones are close too."""
    c = rgba(c)
    best = None
    for r in _RAMPS_RGB:
        i = min(range(len(r)), key=lambda k: _dist(c, r[k]))
        d = _dist(c, r[i]) + 0.15 * _dist(c, r[len(r) // 2])
        if best is None or d < best[0]:
            best = (d, r, i)
    return best[1], best[2]


_PAL_SET = None


def _in_palette(c):
    global _PAL_SET
    if _PAL_SET is None:
        _PAL_SET = {rgba(p)[:3] for p in ENDESGA32}
    return tuple(c[:3]) in _PAL_SET


def _toward(h, target, amount):
    d = ((target - h + 0.5) % 1.0) - 0.5
    return max(-amount, min(amount, d))


def hue_step(c, n):
    """Pixel-artist shading for any colour: each step changes lightness ~0.09; darker steps drift toward
    blue-purple and gain saturation, lighter steps drift toward yellow and lose a little saturation."""
    import colorsys
    c = rgba(c)
    h, l, s = colorsys.rgb_to_hls(c[0] / 255, c[1] / 255, c[2] / 255)
    if n < 0:
        h = (h + _toward(h, 0.70, 0.03 * -n)) % 1
        s = min(1, s + 0.04 * -n)
    else:
        h = (h + _toward(h, 0.14, 0.025 * n)) % 1
        s = max(0, s - 0.02 * n)
    l = min(0.97, max(0.05, l + 0.09 * n))
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return (int(r * 255), int(g * 255), int(b * 255), 255)


def step(c, n):
    """Walk n steps along the colour's ramp (n>0 lighter, n<0 darker).
    Palette colours (and everything in strict mode) use the ENDESGA ramps; other colours use hue_step."""
    c = rgba(c)
    if n == 0:
        return base(c)
    if not _enabled:
        k = 0.12 * n
        t = (255, 255, 255) if k > 0 else (0, 0, 0)
        return tuple(int(c[i] + (t[i] - c[i]) * min(1, abs(k))) for i in range(3)) + (255,)
    if _strict or _in_palette(c):
        r, i = ramp_of(c)
        return r[max(0, min(len(r) - 1, i + n))]
    return hue_step(c, n)


def base(c):
    """Snap to the palette in strict mode; otherwise keep the user's colour."""
    return nearest(c) if (_enabled and _strict) else rgba(c)


def outline_of(c):
    """Outline colour: a very dark, cooler, more saturated version of c (never pure black)."""
    c = rgba(c)
    if _enabled and (_strict or _in_palette(c)):
        return step(c, -3)
    import colorsys
    h, l, s = colorsys.rgb_to_hls(c[0] / 255, c[1] / 255, c[2] / 255)
    h = (h + _toward(h, 0.72, 0.06)) % 1
    l = 0.10 + 0.12 * l
    s = max(0.3, min(1, s + 0.1))
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return (int(r * 255), int(g * 255), int(b * 255), 255)


# ----------------------------------------------------------------------------- textures

def tex_planks(w, h, color, vertical=False, board=6, seed=1, nails=True):
    """Wooden boards: light top edge, dark seam, grain streaks, staggered joints with nails."""
    if vertical:
        return tex_planks(h, w, color, False, board, seed, nails).transpose(Image.Transpose.ROTATE_90)
    rnd = random.Random(seed)
    b0, lt, dk, dk2, nail = base(color), step(color, 1), step(color, -1), step(color, -2), step(color, -3)
    im = Image.new('RGBA', (w, h), b0)
    px = im.load()
    for row, y0 in enumerate(range(0, h, board)):
        for x in range(w):
            if y0 < h:
                px[x, y0] = lt
            if y0 + board - 1 < h:
                px[x, y0 + board - 1] = dk2
        # grain streaks
        for _ in range(max(1, w // 9)):
            gy = y0 + rnd.randint(2, board - 3)
            gx = rnd.randint(0, w - 1)
            for x in range(gx, min(w, gx + rnd.randint(3, 6))):
                if gy < h:
                    px[x, gy] = dk
        # joints + nails
        span = rnd.randint(18, 30)
        jx = (row * 13 + rnd.randint(0, 9)) % span
        while jx < w:
            for y in range(y0, min(h, y0 + board - 1)):
                px[jx, y] = dk2
                if jx + 1 < w and y > y0:
                    px[jx + 1, y] = lt
            if nails and y0 + 2 < h:
                for nx in (jx - 2, jx + 3):
                    if 0 <= nx < w:
                        px[nx, y0 + 2] = nail
            jx += span
    return im


def tex_bricks(w, h, color, bw=8, bh=4, seed=1):
    """Stone/clay bricks: mortar lines, lit top-left pixels, shaded bottom-right, a few chips."""
    rnd = random.Random(seed)
    b0, lt, dk, mortar = base(color), step(color, 1), step(color, -1), step(color, -2)
    im = Image.new('RGBA', (w, h), b0)
    px = im.load()
    for y in range(h):
        row = y // (bh + 1)
        yy = y % (bh + 1)
        off = (bw // 2 + 1) * (row % 2)
        for x in range(w):
            xx = (x + off) % (bw + 1)
            if yy == bh or xx == bw:
                px[x, y] = mortar
            elif yy == 0 and xx < bw - 1:
                px[x, y] = lt
            elif yy == bh - 1 and xx > 0:
                px[x, y] = dk
            elif xx == bw - 1:
                px[x, y] = dk
            elif rnd.random() < 0.04:
                px[x, y] = dk
    return im


def tex_cobble(w, h, color, cell=6, seed=1):
    """Cobblestone: jittered cells with dark joints and a lit corner per stone."""
    rnd = random.Random(seed)
    pts = [(gx * cell + rnd.randint(0, cell - 1), gy * cell + rnd.randint(0, cell - 1))
           for gy in range(-1, h // cell + 2) for gx in range(-1, w // cell + 2)]
    b0, lt, dk, joint = base(color), step(color, 1), step(color, -1), step(color, -2)
    owner = [[min(range(len(pts)), key=lambda k: (pts[k][0] - x) ** 2 + (pts[k][1] - y) ** 2) for x in range(w)]
             for y in range(h)]
    im = Image.new('RGBA', (w, h), b0)
    px = im.load()
    for y in range(h):
        for x in range(w):
            o = owner[y][x]
            if (x + 1 < w and owner[y][x + 1] != o) or (y + 1 < h and owner[y + 1][x] != o):
                px[x, y] = joint
            else:
                cx, cy = pts[o]
                if x < cx and y < cy - 1:
                    px[x, y] = lt
                elif x > cx + 1 and y > cy:
                    px[x, y] = dk
    return im


def tex_grass(w, h, color, seed=1, flowers=False):
    """Top-down grass: base with little lit tufts on a jittered grid, dark roots under them."""
    rnd = random.Random(seed)
    b0, lt, lt2, dk = base(color), step(color, 1), step(color, 2), step(color, -1)
    im = Image.new('RGBA', (w, h), b0)
    px = im.load()
    for gy in range(0, h, 5):
        for gx in range(0, w, 5):
            x, y = gx + rnd.randint(0, 3), gy + rnd.randint(0, 3)
            tip = lt2 if rnd.random() < 0.15 else lt
            for (dx, dy, c) in ((0, 0, tip), (-1, 1, lt), (1, 1, lt), (0, 1, b0), (0, 2, dk)):
                if 0 <= x + dx < w and 0 <= y + dy < h:
                    px[x + dx, y + dy] = c
            if flowers and rnd.random() < 0.08 and 0 <= x + 2 < w and y < h:
                px[x + 2, y] = rgba(rnd.choice(['#ffffff', '#fee761', '#f6757a']))
    return im


def tex_cloth(w, h, color, fold=8):
    """Hanging cloth: vertical folds (shadow line + highlight line) and a darker hem."""
    b0, lt, dk, dk2 = base(color), step(color, 1), step(color, -1), step(color, -2)
    im = Image.new('RGBA', (w, h), b0)
    px = im.load()
    for y in range(h):
        for x in range(w):
            k = x % fold
            if k == 0:
                px[x, y] = dk
            elif k == 1:
                px[x, y] = lt
            if y >= h - 2:
                px[x, y] = dk2 if y == h - 1 else dk
    return im


def tex_dirt(w, h, color, seed=1):
    rnd = random.Random(seed)
    b0, lt, dk = base(color), step(color, 1), step(color, -1)
    im = Image.new('RGBA', (w, h), b0)
    px = im.load()
    for _ in range(w * h // 14):
        x, y = rnd.randrange(w), rnd.randrange(h)
        px[x, y] = dk
        if x + 1 < w and rnd.random() < 0.5:
            px[x + 1, y] = lt
    return im


def tex_sky(w, h, color):
    """Banded sky (no dithering): light band at the bottom, base in the middle, one step darker at the top."""
    im = Image.new('RGBA', (w, h))
    d = ImageDraw.Draw(im)
    bands = [step(color, -1), base(color), step(color, 1)]
    for i, c in enumerate(bands):
        d.rectangle((0, i * h // 3, w, (i + 1) * h // 3), fill=c)
    return im


def texture(name, w, h, color, seed=1):
    name = {'planks_h': 'planks', 'stone': 'cobble', 'noise': 'dirt'}.get(name, name)
    if name == 'planks':
        return tex_planks(w, h, color, seed=seed)
    if name == 'planks_v':
        return tex_planks(w, h, color, vertical=True, seed=seed)
    if name == 'bricks':
        return tex_bricks(w, h, color, seed=seed)
    if name == 'cobble':
        return tex_cobble(w, h, color, seed=seed)
    if name == 'grass':
        return tex_grass(w, h, color, seed=seed)
    if name == 'meadow':
        return tex_grass(w, h, color, seed=seed, flowers=True)
    if name == 'cloth':
        return tex_cloth(w, h, color)
    if name == 'dirt':
        return tex_dirt(w, h, color, seed=seed)
    if name == 'sky':
        return tex_sky(w, h, color)
    # simple repeats
    b0, lt = base(color), step(color, 1)
    im = Image.new('RGBA', (w, h), b0)
    px = im.load()
    for y in range(h):
        for x in range(w):
            if name == 'checker' and ((x // 4) + (y // 4)) % 2 == 0:
                px[x, y] = lt
            elif name == 'stripes' and (x // 3) % 2 == 0:
                px[x, y] = lt
            elif name == 'dots' and ((x % 6 == 0 and y % 6 == 0) or ((x + 3) % 6 == 0 and (y + 3) % 6 == 0)):
                px[x, y] = lt
    return im


# ----------------------------------------------------------------------------- shapes

def bevel(img, box, color, outline=True, lip=2, rim=True):
    """The 'drawn button' recipe: dark outline with cut corners, lit top/left rim, darker 2px bottom lip."""
    x0, y0, x1, y1 = box
    d = ImageDraw.Draw(img)
    c = base(color)
    if outline:
        o = outline_of(color)
        d.rectangle((x0 + 1, y0, x1 - 1, y1), fill=o)
        d.rectangle((x0, y0 + 1, x1, y1 - 1), fill=o)
        x0, y0, x1, y1 = x0 + 1, y0 + 1, x1 - 1, y1 - 1
    d.rectangle((x0, y0, x1, y1), fill=c)
    if rim:
        d.line((x0, y0, x1, y0), fill=step(color, 1))
        d.line((x0, y0, x0, y1 - lip), fill=step(color, 1))
    for k in range(lip):
        d.line((x0, y1 - k, x1, y1 - k), fill=step(color, -1 - (1 if k == 0 and lip > 1 else 0)))
    d.line((x1, y0 + 1, x1, y1 - lip), fill=step(color, -1))
    return (x0, y0, x1, y1)


def drop_shadow(img, box, alpha=90, off=1):
    x0, y0, x1, y1 = box
    sh = Image.new('RGBA', (x1 - x0 + 1, y1 - y0 + 1), (24, 20, 37, alpha))
    layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    layer.paste(sh, (x0 + off, y0 + off))
    img.alpha_composite(layer)


def plate(img, box, kind='wood', color=None):
    """UI-kit plate: outline with cut corners, textured face, lit top row, 2px darker bottom, nails/chips."""
    x0, y0, x1, y1 = box
    color = color or {'wood': '#b86f50', 'stone': '#8b9bb4', 'gold': '#feae34', 'dark': '#3a4466'}.get(kind, '#b86f50')
    drop_shadow(img, box)
    inner = bevel(img, box, color, lip=2)
    ix0, iy0, ix1, iy1 = inner
    w, h = ix1 - ix0 + 1, iy1 - iy0 - 2
    if w > 2 and h > 1:
        if kind == 'wood':
            face = tex_planks(w, h, color, board=max(3, h), nails=False)
        elif kind == 'stone':
            face = tex_cobble(w, h, color, cell=5)
        else:
            face = Image.new('RGBA', (w, h), base(color))
        img.alpha_composite(face, (ix0, iy0 + 1))
    d = ImageDraw.Draw(img)
    d.line((ix0, iy0, ix1, iy0), fill=step(color, 1))
    if kind == 'wood' and x1 - x0 > 12:
        my = (y0 + y1) // 2
        for nx in (x0 + 2, x1 - 3):
            d.rectangle((nx, my - 1, nx + 1, my), fill=step(color, -3))
            d.point((nx, my - 1), fill=step(color, -1))
    return inner
