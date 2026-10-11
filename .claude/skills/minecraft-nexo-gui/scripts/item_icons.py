#!/usr/bin/env python3
"""16x16 item icons (food, drinks, crops, mob drops) in the style measured from a 62-icon food set.

What the measurements say (details and numbers in references/item-icons.md):
  * 16x16, only fully opaque pixels, usually a 1px empty margin; the item covers ~47% of the canvas
  * 6-12 colours per icon, taken from ramps of 6-9 steps per material (bread, chocolate, tomato, glass...)
  * a ramp runs from value ~20% to ~95%; saturation stays high through the mids and drops in the two
    lightest steps (cream highlights); fruit and warm food shift hue toward yellow in the lights
  * the outline is the darkest step of the material it wraps - never black (56 of 62 icons)
  * light from the top-left, 1-3 pixels of the lightest step as the highlight
  * glass is one shared light-blue ramp: light wall on the left, dark wall on the right and bottom,
    the empty part of a glass is transparent, the liquid has its own ramp
  * long things lie on the diagonal bottom-left -> top-right; flat food uses the full 16px width
  * variants are palette swaps of one shape (raw / cooked) or the same base with a topping on top

Use it from Python:
    from item_icons import Icon, RAMPS, ellipse, poly, capsule
    ic = Icon()
    ic.part('body', ellipse(2, 4, 13, 14), 'tomato')          # shaded with the ramp, outlined with its dark end
    ic.part('leaf', poly([(6, 2), (9, 1), (10, 4), (7, 5)]), 'leaf', light_only=True)
    ic.save('tomato.png', aseprite='tomato.aseprite')         # .aseprite keeps one layer per part

or render a ready recipe from the command line (one PNG per recipe, plus a preview sheet):
    python3 item_icons.py OUT_DIR jar:honey bottle:milk cup:apple fruit:apple bowl:pumpkin loaf:bread ...
    python3 item_icons.py --list                              # recipes and ramps
"""
import colorsys
import math
import os
import sys
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _rgb(c):
    if isinstance(c, str):
        c = c.lstrip('#')
        return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))
    return tuple(c[:3])


def make_ramp(base, n=7, hue_dark=-0.025, hue_light=0.035, dark=0.45, sat_top=0.32, main=0.55):
    """Ramp dark -> light with `base` as the main tone (at position `main`), shaped like the measured ramps:
    darks fall to `dark` x the base value with the hue turned by hue_dark (yellows: toward orange-brown,
    never olive - butter goes 44 -> 25 deg), lights rise to full value and then lose saturation (cream
    highlights: orange s 87% -> 29% at the top) with the hue turned by hue_light."""
    h, s, v = colorsys.rgb_to_hsv(*[x / 255 for x in _rgb(base)])
    if 0.08 < h < 0.2:
        hue_dark = min(hue_dark, -0.055)
    out = []
    for i in range(n):
        t = i / (n - 1)
        if t <= main:
            u = t / main
            vv = v * (dark + (1 - dark) * u)
            ss = min(1.0, s * (1.1 - 0.1 * u))
            hh = h + hue_dark * (1 - u)
        else:
            u = (t - main) / (1 - main)
            vv = min(1.0, v + (1 - v) * min(1.0, 1.6 * u))
            ss = s * (1 - (1 - sat_top) * u ** 1.2)
            hh = h + hue_light * u
        out.append(tuple(int(round(x * 255)) for x in colorsys.hsv_to_rgb(hh % 1.0, ss, vv)))
    return out


# Ramps dark -> light. Measured ones (from the reference set) keep their steps; the others are built with
# make_ramp() so that they behave the same way (value range, saturation drop, hue shift).
RAMPS = {
    'bread':     ['#2e1c0e', '#552813', '#8a4a22', '#b2672d', '#cf8a3e', '#de9d46', '#f2c27a'],
    'toast':     ['#3f2e0e', '#4c3811', '#654b17', '#8c661e', '#a27924', '#bc8927', '#d8a748', '#f2be59'],
    'butter':    ['#76411b', '#aa7439', '#d8a040', '#e5bb48', '#ffd970', '#ffe9ae', '#fff5db'],
    'cheese':    ['#76411b', '#aa7439', '#d8a040', '#e5bb48', '#f2c855', '#ffd970', '#ffe9ae'],
    'pancake':   ['#624524', '#835e35', '#9d6629', '#d1893b', '#eb9c46', '#f2ad62', '#f2cd6a'],
    'fries':     ['#905308', '#b16a13', '#b59840', '#d5ac37', '#f0cd5a', '#ffeaa6'],
    'dough':     ['#96702f', '#b7953a', '#d6bd78', '#e5d29a', '#f2e4bf', '#fff8e4'],
    'chocolate': ['#1a120b', '#271c12', '#342314', '#412e1d', '#55381e', '#694525', '#895b33', '#a36936'],
    'honey':     ['#624524', '#a35a12', '#d7860f', '#f2b21c', '#fbd23c', '#ffe27a', '#ffeba1'],
    'tomato':    ['#380e0f', '#691f21', '#820b05', '#a50700', '#cc160e', '#ff3a31', '#ff7a6a'],
    'leaf':      ['#203411', '#3c4e1c', '#5e7025', '#78a32e', '#7fde3b', '#b6f27a'],
    'orange':    ['#862e23', '#b34716', '#d9591e', '#f2771e', '#f9911f', '#ffac1f', '#ffc45e', '#f2d8aa'],
    'meat_raw':  ['#865245', '#b77b6c', '#d79d8c', '#eab6a7', '#f4cfc2', '#fee5d2'],
    'meat':      ['#5a2d14', '#7f3e1c', '#b26032', '#c58254', '#d69663', '#deae87', '#f8d7be'],
    'sausage':   ['#2e0d09', '#5b1d12', '#8a301c', '#b34a2c', '#de6646', '#f08d6c'],
    'glass':     ['#5d8fc2', '#8badd0', '#b3cfec', '#d4e5f7', '#e9f3ff'],
    'cork':      ['#7c6f6b', '#a38e87', '#b7adaa', '#d8ccc9', '#f2f2f2'],
    'wood':      ['#1f1502', '#3a2508', '#5c3a10', '#7d5218', '#9c6a22'],
    'paper':     ['#3a3a3a', '#6b6b6b', '#9a9a9a', '#c4c4c4', '#ebe7e7'],
}
for _name, _base, _kw in (
        ('apple',    '#d8222a', {}),
        ('milk',     '#e4ebf2', {'dark': 0.62, 'sat_top': 0.2}),
        ('pumpkin',  '#e8761c', {}),
        ('carrot',   '#f07a12', {}),
        ('berry',    '#b8235a', {'hue_dark': 0.03}),
        ('blueberry', '#3b4fc4', {'hue_dark': 0.02, 'hue_light': -0.03}),
        ('grape',    '#7a2fa8', {}),
        ('wheat',    '#e0b040', {'hue_dark': -0.02}),
        ('egg',      '#e6cfa2', {'dark': 0.5, 'sat_top': 0.4}),
        ('corn',     '#f2c81e', {}),
        ('jam',      '#c8102e', {}),
        ('cream',    '#fff3d6', {'dark': 0.62}),
        ('potato',   '#c79a52', {}),
        ('fish',     '#8aa3b8', {'hue_light': 0.0}),
        ('salmon',   '#f08a62', {}),
        ('juice_apple', '#f2c84a', {}),
        ('soup_pumpkin', '#f08a1c', {}),
        ('soup_beet', '#b0223f', {}),
        ('cocoa',    '#9a5a2e', {'dark': 0.3}),
        ('melon',    '#e8455a', {}),
        ('lettuce',  '#8bc34a', {}),
        ('gold',     '#f2c230', {'hue_dark': -0.04, 'hue_light': 0.03}),
        ('iron',     '#b8c0c8', {'hue_dark': 0.02, 'hue_light': 0.0, 'sat_top': 0.2}),
):
    RAMPS[_name] = make_ramp(_base, **_kw)
RAMPS = {k: [_rgb(c) for c in v] for k, v in RAMPS.items()}


def ramp(r):
    return RAMPS[r] if isinstance(r, str) else [_rgb(c) for c in r]


# ---------------------------------------------------------------- masks (sets of (x, y) on the 16x16 canvas)

def ellipse(x0, y0, x1, y1):
    cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0 + 1) / 2, (y1 - y0 + 1) / 2
    return {(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)
            if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0 + 0.6 / max(rx, ry)}


def rect(x0, y0, x1, y1):
    return {(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)}


def poly(pts):
    """Filled polygon (pixel centres inside, edges included)."""
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    out = set()
    for y in range(min(ys), max(ys) + 1):
        for x in range(min(xs), max(xs) + 1):
            if _inside(x, y, pts):
                out.add((x, y))
    for (ax, ay), (bx, by) in zip(pts, pts[1:] + pts[:1]):
        out |= line(ax, ay, bx, by)
    return out


def _inside(x, y, pts):
    c = False
    for (ax, ay), (bx, by) in zip(pts, pts[1:] + pts[:1]):
        if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
            c = not c
    return c


def line(x0, y0, x1, y1):
    n = max(abs(x1 - x0), abs(y1 - y0), 1)
    return {(round(x0 + (x1 - x0) * i / n), round(y0 + (y1 - y0) * i / n)) for i in range(n + 1)}


def capsule(x0, y0, x1, y1, r):
    """Thick rounded stroke - baguettes, sausages, carrots, bones on the diagonal."""
    out = set()
    L = math.hypot(x1 - x0, y1 - y0) or 1
    for y in range(16):
        for x in range(16):
            t = max(0, min(1, ((x - x0) * (x1 - x0) + (y - y0) * (y1 - y0)) / (L * L)))
            px, py = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            rr = r(t) if callable(r) else r
            if math.hypot(x - px, y - py) <= rr + 0.25:
                out.add((x, y))
    return out


def clip(mask):
    return {(x, y) for x, y in mask if 0 <= x < 16 and 0 <= y < 16}


# ---------------------------------------------------------------- shading

N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


def edge(mask):
    return {(x, y) for x, y in mask if any((x + dx, y + dy) not in mask for dx, dy in N4)}


def _dist(mask):
    d, front = {}, [p for p in mask if any((p[0] + dx, p[1] + dy) not in mask for dx, dy in N4)]
    for p in front:
        d[p] = 1
    while front:
        nxt = []
        for x, y in front:
            for dx, dy in N4:
                q = (x + dx, y + dy)
                if q in mask and q not in d:
                    d[q] = d[(x, y)] + 1
                    nxt.append(q)
        front = nxt
    return d


def _axis(mask):
    """Principal direction of a silhouette (unit vector) - texture strokes follow it."""
    n = len(mask)
    cx = sum(x for x, _ in mask) / n
    cy = sum(y for _, y in mask) / n
    sxx = sum((x - cx) ** 2 for x, _ in mask)
    syy = sum((y - cy) ** 2 for _, y in mask)
    sxy = sum((x - cx) * (y - cy) for x, y in mask)
    a = 0.5 * math.atan2(2 * sxy, sxx - syy)
    return math.cos(a), math.sin(a), (sxx + syy) and abs(sxx - syy) / (sxx + syy)


def _strokes(mask, seed, length=3):
    """Short strokes along the silhouette's long axis (round shapes: along the edge), values -1/0/+1.
    Measured: inside the reference icons 57-100% of neighbouring pixels differ in tone - the texture comes
    from 2-3 px dashes of the neighbouring ramp steps, not from noise."""
    import random
    rnd = random.Random(seed)
    ax, ay, elong = _axis(mask)
    d = _dist(mask)
    out = {}
    for p in sorted(mask, key=lambda q: (q[1], q[0])):
        if p in out:
            continue
        val = rnd.choice((-1, -1, 0, 1, 1))
        if elong > 0.35:                        # long item: strokes along the axis
            sx, sy = ax, ay
        else:                                   # round item: strokes along the edge (tangent of the distance)
            gx = d.get((p[0] + 1, p[1]), 0) - d.get((p[0] - 1, p[1]), 0)
            gy = d.get((p[0], p[1] + 1), 0) - d.get((p[0], p[1] - 1), 0)
            sx, sy = (-gy, gx) if (gx or gy) else (1, 0)
            nn = math.hypot(sx, sy)
            sx, sy = sx / nn, sy / nn
        for i in range(rnd.randint(2, length)):
            q = (round(p[0] + sx * i), round(p[1] + sy * i))
            if q in mask and q not in out:
                out[q] = val
    return out


def shade(mask, r, light=(-1.0, -1.15), base=0.64, contrast=0.12, rim=0.12, texture=0.16, highlight=3,
          outline=True, flat=False, seed=1):
    """Shade a silhouette with a ramp the way the reference icons are shaded (measured on 16 one-material
    icons): outline = darkest step; first ring inside ~0.5 of the ramp on the shadow side, ~0.6 on the lit
    side; deeper pixels ~0.55-0.67; texture = short strokes of +-1 step; the lightest step only on the
    `highlight` best-lit pixels. Light comes from the top-left; flat=True weakens the relief (slices, plates)."""
    r = ramp(r)
    n = len(r)
    mask = set(mask)
    if not mask:
        return {}
    d = _dist(mask)
    rimset = edge(mask) if outline else set()
    R = max(2.0, min(4.0, max(d.values()) * 0.8))
    h = {p: math.sqrt(max(0.0, 1 - (1 - min(dd, R) / R) ** 2)) for p, dd in d.items()}
    L = (light[0], light[1], 0.9)
    ln = math.sqrt(sum(c * c for c in L))
    st = _strokes(mask, seed) if texture else {}
    lo = 1 if outline else 0
    top = n - 2 if highlight else n - 1           # lightest step reserved for the highlight
    out, score = {}, {}
    for (x, y) in mask:
        if (x, y) in rimset:
            out[(x, y)] = r[0]
            continue
        gx = (h.get((x + 1, y), 0) - h.get((x - 1, y), 0)) / 2
        gy = (h.get((x, y + 1), 0) - h.get((x, y - 1), 0)) / 2
        if flat:
            gx, gy = gx * 0.4, gy * 0.4
        nx, ny, nz = -gx, -gy, 0.55
        nn = math.sqrt(nx * nx + ny * ny + nz * nz)
        I = (nx * L[0] + ny * L[1] + nz * L[2]) / (nn * ln)      # ~0.3 (shadow side) .. ~1 (lit side)
        v = base + contrast * (I - 0.6) / 0.4
        if d[(x, y)] == 2 and outline:
            v -= rim
        v += texture * st.get((x, y), 0)
        score[(x, y)] = I + 0.05 * st.get((x, y), 0) - 0.001 * (x + y)
        k = lo + int(round(max(0.0, min(1.0, v)) * (top - lo)))
        out[(x, y)] = r[max(lo, min(top, k))]
    if highlight:
        best = sorted((p for p in score if d[p] >= (2 if outline else 1)), key=lambda p: -score[p])[:highlight]
        for p in best:
            out[p] = r[-1]
    return out


# ---------------------------------------------------------------- icon with layers

class Icon:
    """Parts are stacked bottom -> top; each is its own layer in the .aseprite output."""

    def __init__(self, size=16):
        self.size = size
        self.layers = []          # (name, {xy: rgb})

    def part(self, name, mask, r, **kw):
        px = shade(clip(mask), r, **kw)
        self.layers.append((name, px))
        return px

    def pixels(self, name, px):
        """Raw pixels {xy: colour} as a layer (details: seeds, crumbs, glints)."""
        self.layers.append((name, {p: _rgb(c) for p, c in px.items()}))

    def line(self, name, pts, colour):
        self.pixels(name, {p: colour for p in pts})

    def outline_all(self, colour_of=None):
        """Outline the union of all layers with the darkest neighbour colour (merges touching parts)."""
        img = self.image()
        px = img.load()
        add = {}
        for y in range(16):
            for x in range(16):
                if px[x, y][3]:
                    continue
                nb = [px[x + dx, y + dy] for dx, dy in N4 if 0 <= x + dx < 16 and 0 <= y + dy < 16
                      and px[x + dx, y + dy][3]]
                if nb:
                    c = min(nb, key=lambda c: sum(c[:3]))
                    add[(x, y)] = colour_of(c) if colour_of else c[:3]
        self.layers.insert(0, ('outline', add))

    def image(self):
        img = Image.new('RGBA', (self.size, self.size), (0, 0, 0, 0))
        px = img.load()
        for _, layer in self.layers:
            for (x, y), c in layer.items():
                if 0 <= x < self.size and 0 <= y < self.size:
                    px[x, y] = tuple(c[:3]) + (255,)
        return img

    def save(self, path, aseprite=None):
        self.image().save(path)
        if aseprite:
            import tempfile
            import aseprite_tools
            tmp = tempfile.mkdtemp()
            files = []
            for i, (name, layer) in enumerate(self.layers):
                im = Image.new('RGBA', (self.size, self.size), (0, 0, 0, 0))
                for (x, y), c in layer.items():
                    if 0 <= x < self.size and 0 <= y < self.size:
                        im.putpixel((x, y), tuple(c[:3]) + (255,))
                f = os.path.join(tmp, f'{i:02d}.png')
                im.save(f)
                files.append((f, name))
            aseprite_tools.layers(aseprite, files)


def swap(img, src, dst):
    """Palette swap: every pixel of ramp `src` -> same step of ramp `dst` (raw -> cooked, colour variants).
    Ramps of different length are matched by relative position."""
    s, t = ramp(src), ramp(dst)
    img = img.convert('RGBA').copy()
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            c = px[x, y]
            if c[3] and c[:3] in s:
                i = s.index(c[:3])
                px[x, y] = t[round(i * (len(t) - 1) / (len(s) - 1))] + (255,)
    return img


# ---------------------------------------------------------------- recipes

def _glass_walls(ic, body, top_open=True):
    """Glass container: light wall left, dark wall right + bottom, transparent inside."""
    g = ramp('glass')
    e = edge(body)
    xs = [x for x, _ in body]
    cx = (min(xs) + max(xs)) / 2
    ymax = max(y for _, y in body)
    walls = {}
    for (x, y) in e:
        if y == ymax:
            walls[(x, y)] = g[0]
        elif x < cx:
            walls[(x, y)] = g[3] if y % 3 else g[4]
        else:
            walls[(x, y)] = g[0] if x == max(xx for xx, yy in e if yy == y) else g[1]
    ic.pixels('glass', walls)
    return body - e


def _liquid(ic, inside, level, r, name='liquid'):
    """Liquid in a glass: lit left, darker right and bottom, a light surface line, one white glint."""
    r = ramp(r)
    n = len(r)
    ys = [y for _, y in inside]
    top = min(ys) + level
    liq = {p for p in inside if p[1] >= top}
    if not liq:
        return liq
    xs = [x for x, _ in liq]
    x0, x1, y1 = min(xs), max(xs), max(y for _, y in liq)
    px = {}
    for (x, y) in liq:
        t = (x - x0) / max(1, x1 - x0)
        i = n - 3 if t < 0.3 else n - 4 if t < 0.75 else n - 5
        if y == y1:
            i -= 1
        if y == top:
            i = n - 2 if t < 0.75 else n - 3
        px[(x, y)] = r[max(0, min(n - 1, i))]
    for dy in (2, 3):                               # glint on the glass, left side under the surface
        if (x0 + 1, top + dy) in liq:
            px[(x0 + 1, top + dy)] = ramp('glass')[4]
    ic.pixels(name, px)
    return liq


def bottle(liquid='milk', cork='cork'):
    ic = Icon()
    body = ellipse(4, 6, 11, 15) | rect(4, 9, 11, 15)
    neck = rect(6, 2, 9, 6)
    inside = _glass_walls(ic, body | neck)
    _liquid(ic, inside - neck, 1, liquid)
    ic.part('cork', rect(6, 0, 9, 2), cork, highlight=1)
    return ic


def jar(content='honey', lid='cork'):
    ic = Icon()
    body = rect(3, 5, 12, 15)
    body -= {(3, 5), (12, 5), (3, 15), (12, 15)}
    inside = _glass_walls(ic, body)
    _liquid(ic, inside, 2, content, 'content')
    ic.part('lid', rect(4, 2, 11, 4), lid, highlight=2)
    return ic


def cup(liquid='juice_apple', straw='leaf'):
    ic = Icon()
    body = poly([(3, 4), (12, 4), (11, 15), (4, 15)])
    inside = _glass_walls(ic, body)
    _liquid(ic, inside - {p for p in inside if p[1] == 4}, 4, liquid)
    if straw:
        s = ramp(straw)
        ic.pixels('straw', {(9, 1): s[3], (10, 0): s[4], (9, 2): s[2], (9, 3): s[2], (8, 5): s[1], (8, 6): s[1]})
    return ic


def mug(liquid='cocoa', foam='cream'):
    ic = Icon()
    body = rect(2, 5, 11, 15) - {(2, 15), (11, 15)}
    handle = {(12, 7), (13, 7), (14, 8), (14, 9), (14, 10), (14, 11), (13, 12), (12, 12)}
    inside = _glass_walls(ic, body)
    ic.pixels('handle', {p: ramp('glass')[0 if p[0] == 14 else 1] for p in handle})
    _liquid(ic, inside, 1, liquid)
    ic.part('foam', ellipse(1, 2, 12, 6) | {(3, 7), (9, 7), (9, 8)}, foam, highlight=2)
    return ic


def bowl(soup='soup_pumpkin', garnish='leaf', bowl='wood'):
    """Soup / stew: the soup surface shows above a wooden bowl seen from the front."""
    ic = Icon()
    ic.part('soup', ellipse(1, 3, 14, 11), soup, flat=True, base=0.78, highlight=3, light=(-0.6, -1.3))
    front = {p for p in ellipse(0, 1, 15, 14) if p[1] >= 8} | rect(4, 14, 11, 15)
    ic.part('bowl', front, bowl, base=0.55, highlight=0)
    b = ramp(bowl)
    ic.pixels('rim', {(x, 9): b[-1] if x < 6 else b[-2] for x in range(1, 15)})
    if garnish:
        g = ramp(garnish)
        ic.pixels('garnish', {(6, 6): g[2], (7, 5): g[3], (8, 5): g[4], (8, 6): g[3], (9, 7): g[2], (10, 6): g[1]})
    return ic


def fruit(r='apple', leaf='leaf', stem='wood', shape=(2, 3, 13, 15), top='stem'):
    """Round fruit / vegetable. top='stem' (apple, pear, orange) or 'calyx' (tomato, strawberry: a green star)."""
    ic = Icon()
    body = ellipse(*shape)
    cx = (shape[0] + shape[2]) // 2
    if shape[2] - shape[0] >= 10:                  # small dip at the top
        body -= {(cx, shape[1]), (cx + 1, shape[1])}
    ic.part('body', body, r, highlight=2)
    if top == 'calyx':
        g = ramp(leaf)
        y = shape[1]
        star = {(cx - 2, y + 1): g[1], (cx - 1, y): g[2], (cx, y): g[3], (cx + 1, y): g[3], (cx + 2, y): g[2],
                (cx + 3, y + 1): g[1], (cx, y - 1): g[2], (cx + 1, y - 1): g[3], (cx, y + 1): g[1],
                (cx + 1, y + 1): g[2], (cx + 1, y - 2): g[0], (cx - 3, y + 1): g[0], (cx + 4, y + 1): g[0]}
        ic.pixels('calyx', star)
        return ic
    if stem:
        s = ramp(stem)
        ic.pixels('stem', {(cx, shape[1] - 1): s[2], (cx, shape[1] - 2): s[1], (cx - 1, shape[1] - 3): s[0]})
    if leaf:
        ic.part('leaf', poly([(cx + 1, shape[1] - 2), (cx + 4, shape[1] - 3), (cx + 5, shape[1] - 2),
                              (cx + 2, shape[1])]), leaf, highlight=1)
    return ic


def tomato(r='tomato', leaf='leaf'):
    return fruit(r, leaf, shape=(1, 4, 14, 14), top='calyx')


def loaf(r='bread'):
    ic = Icon()
    body = ellipse(1, 4, 14, 13) | rect(2, 9, 13, 13)
    ic.part('loaf', body, r, highlight=3)
    c = ramp(r)
    cuts = {}
    for x0 in (3, 7, 11):                           # diagonal scores: dark cut, light lip under it
        for k in range(3):
            cuts[(x0 + k, 8 - k)] = c[1]
            cuts[(x0 + k, 9 - k)] = c[-2]
    ic.pixels('cuts', cuts)
    return ic


def long_item(r='bread', width=2.2, x0=2, y0=13, x1=13, y1=2, scores=True):
    """Baguette / sausage / carrot / bone lying on the diagonal."""
    ic = Icon()
    ic.part('body', capsule(x0, y0, x1, y1, width), r, highlight=2)
    if scores:
        c = ramp(r)
        sc = {}
        for t in (0.3, 0.5, 0.7):
            cx, cy = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            sc.update({(round(cx) - 1, round(cy)): c[2], (round(cx), round(cy) - 1): c[2],
                       (round(cx), round(cy)): c[-2]})
        ic.pixels('scores', sc)
    return ic


def carrot(r='carrot', leaf='leaf'):
    ic = Icon()
    ic.part('root', capsule(3, 13, 10, 5, lambda t: 0.6 + 2.2 * t), r, highlight=2)
    c = ramp(r)
    ic.pixels('rings', {(5, 10): c[2], (6, 11): c[2], (7, 8): c[2], (8, 9): c[2]})
    ic.part('leaves', poly([(10, 4), (12, 0), (13, 2)]) | poly([(10, 4), (15, 3), (14, 5)]), leaf, highlight=1)
    return ic


def stack(r='pancake', topping=None, layers=3):
    """Pancakes: flat discs 3 rows each (light band, mid band, dark line) and a top face; topping drips."""
    ic = Icon()
    c = ramp(r)
    n = len(c)
    px = {}
    y = 14
    for i in range(layers):
        for x in range(16):
            if 1 <= x <= 14:
                px[(x, y)] = c[0]
                px[(x, y - 2)] = c[0] if x in (1, 14) else c[n - 2] if x < 5 else c[n - 3]
            px[(x, y - 1)] = c[0] if x in (0, 15) else c[n - 4] if x < 11 else c[max(1, n - 5)]
        y -= 3
    ic.pixels('layers', px)
    ic.part('top', ellipse(0, y - 3, 15, y + 1), r, flat=True, base=0.8, highlight=3)
    if topping:
        drip = ellipse(3, y - 2, 12, y + 1) | {(3, y + 2), (3, y + 3), (12, y + 2), (12, y + 3), (12, y + 4),
                                               (8, y + 2), (8, y + 3)}
        ic.part('topping', drip, topping, highlight=2, base=0.72)
    return ic


def slice_(r='cheese', holes=True):
    """Cheese wedge: light top face, mid front face with holes, outline from the ramp's dark end."""
    ic = Icon()
    c = ramp(r)
    top = poly([(1, 9), (12, 3), (14, 6)])
    front = poly([(1, 10), (14, 7), (14, 12), (1, 13)])
    ic.part('front', front, r, flat=True, base=0.5, highlight=0, outline=False, texture=0.06)
    ic.part('top', top - front, r, flat=True, base=0.86, highlight=2, outline=False, light=(-0.4, -1.6),
            texture=0.06)
    if holes:
        hp = {}
        for hx, hy in ((4, 11), (9, 10), (12, 9)):
            hp.update({(hx, hy): c[1], (hx + 1, hy): c[2], (hx, hy + 1): c[2], (hx + 1, hy + 1): c[-2]})
        hp.update({(7, 7): c[2], (8, 7): c[-1]})
        ic.pixels('holes', hp)
    ic.outline_all(lambda col: c[0])
    return ic


def drumstick(r='meat', bone='egg'):
    ic = Icon()
    ic.part('bone', capsule(3, 12, 6, 9, 1.0) | ellipse(1, 12, 3, 14) | ellipse(3, 13, 5, 15), bone, highlight=1)
    ic.part('meat', ellipse(5, 1, 14, 11) | capsule(5, 10, 9, 6, 2.2), r, highlight=3)
    return ic


def pie(r='bread', filling='berry'):
    ic = Icon()
    dish = ellipse(0, 6, 15, 14)
    ic.part('crust', dish, r, highlight=0)
    ic.part('filling', ellipse(2, 7, 13, 11), filling, highlight=2)
    c = ramp(r)
    lattice = {}
    for x in range(3, 13):
        lattice[(x, 9)] = c[-2]
    for x in (5, 8, 11):
        for y in range(7, 12):
            if (x, y) in ellipse(2, 7, 13, 11):
                lattice[(x, y)] = c[-3]
    ic.pixels('lattice', lattice)
    return ic


def egg(r='egg'):
    ic = Icon()
    ic.part('egg', ellipse(4, 5, 11, 14) | ellipse(5, 2, 10, 10), r, highlight=2)
    return ic


def bundle(r='wheat', tie='wood'):
    """Sheaf of wheat: three grain ears on top, stalks tied in the middle, fanning out at the bottom."""
    ic = Icon()
    c = ramp(r)
    st = {}
    for a, b, d in (((8, 7), (8, 11), (8, 15)), ((5, 8), (7, 11), (5, 15)), ((11, 8), (9, 11), (11, 15))):
        for p in line(*a, *b) | line(*b, *d):
            st[p] = c[3] if p[0] <= 8 else c[2]
    ic.pixels('stalks', st)
    ic.part('ear_l', capsule(3, 2, 5, 7, 1.2), r, highlight=1, outline=False, texture=0.3, seed=3)
    ic.part('ear_r', capsule(13, 2, 11, 7, 1.2), r, highlight=1, outline=False, texture=0.3, seed=5)
    ic.part('ear_c', capsule(8, 1, 8, 6, 1.4), r, highlight=2, outline=False, texture=0.3, seed=7)
    t = ramp(tie)
    ic.pixels('tie', {(x, 11): t[3] if x < 8 else t[2] for x in range(6, 11)} |
              {(x, 12): t[1] for x in range(6, 11)})
    ic.outline_all(lambda col: c[0])
    return ic


RECIPES = {
    'bottle': bottle, 'jar': jar, 'cup': cup, 'mug': mug, 'bowl': bowl, 'fruit': fruit, 'loaf': loaf,
    'long': long_item, 'carrot': carrot, 'stack': stack, 'slice': slice_, 'drumstick': drumstick, 'pie': pie,
    'egg': egg, 'bundle': bundle, 'tomato': tomato,
}


def render(spec):
    """'jar:honey' / 'stack:toast:honey' / 'fruit:apple' -> Icon (args after the recipe name are ramps)."""
    name, *args = spec.split(':')
    return RECIPES[name](*args)


def sheet(images, k=6, cols=8, bg=(139, 139, 139, 255)):
    rows = (len(images) + cols - 1) // cols
    c = Image.new('RGBA', (cols * (16 * k + 8) + 8, rows * (16 * k + 8) + 8), (60, 60, 70, 255))
    for i, im in enumerate(images):
        x, y = 8 + (i % cols) * (16 * k + 8), 8 + (i // cols) * (16 * k + 8)
        c.paste(Image.new('RGBA', (16 * k, 16 * k), bg), (x, y))
        c.alpha_composite(im.resize((16 * k, 16 * k), Image.NEAREST), (x, y))
    return c


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a or a[0] == '--list':
        print('recipes:', ', '.join(RECIPES))
        print('ramps:  ', ', '.join(RAMPS))
        sys.exit(0 if a else __doc__)
    out, specs = a[0], [s for s in a[1:] if not s.startswith('--')]
    os.makedirs(out, exist_ok=True)
    ims = []
    for s in specs:
        ic = render(s)
        fn = s.replace(':', '_')
        ic.save(os.path.join(out, fn + '.png'),
                aseprite=os.path.join(out, fn + '.aseprite') if '--aseprite' in a else None)
        ims.append(ic.image())
    sheet(ims).save(os.path.join(out, '_sheet.png'))
    print(len(ims), 'icons ->', out)
