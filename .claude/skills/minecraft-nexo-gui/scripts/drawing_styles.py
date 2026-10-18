#!/usr/bin/env python3
"""Drawing styles: restyle any finished sprite (house soft, vanilla, cel, flat, ink, PICO-8, Game Boy, ...) and a
set of demo objects drawn natively in the house style at 16x16 (k=1) and 32x32 (k=2, "HD") density.

PART 1 - the demo objects (references/drawing-styles.md, "Demo objects"). Each is BUILT FROM PARTS (modes.Parts:
every part on its own transparent canvas, kept as sprite + offset), so it can be composed (modes.compose), moved
or hidden (modes.override) and exported (layers.save_parts / layers.write_aseprite):
    sphere      glossy ball: highlight, reflection, terminator, bounce + rim light, projected shadow
    stone_cube  2:1 iso stone block: lit top, base left face, dark right face, chips, cracks, moss
    sword       diagonal sword: bevelled steel blade (fuller at k=2), gold guard, wrapped grip, pommel
    potion      round flask: glass walls, liquid with surface + bubbles, cork (+ twine and sparkles at k=2)
    house       2:1 iso timber cottage: plaster, timber posts, stone footing, tiled roof, chimney, door, windows
    tree        oak: clumped canopy lit from the top-left, bark, roots, ground shadow (+ apples, grass at k=2)

PART 2 - the style engine. stylize(img, style) remaps the colours of ANY RGBA sprite to a style: colours are
grouped into materials (by declared ramps, or by hue + adjacency), every colour gets a tone index inside its
material (0 line, 1 shadow .. 5 highlight, value order kept), the style maps tone indices onto its own ramps
(reduce: flat 1 tone, cel 2, 3, 4 / expand: shading synthesised for flat inputs), regenerates the outline
(none / black / dark per area / selective / double / lit / glow / broken), optionally adds ordered dithering
or ink hatching, and never writes semi-transparent pixels. 18 styles in STYLES (house_soft, soft_noline,
vanilla, high_contrast, pastel, cel, flat, sticker, lineart_ink, silhouette, sepia_old_map, neon_night, pico8,
sweetie16, endesga32, nes_like, gameboy, gameboy_dither); limited palettes in PALETTES.

API: CATALOG {name: builder(k, **opts) -> modes.Parts}; render(name, k=1, style=None, **opts) -> tight RGBA;
parts(name, k=1, style=None, **opts) -> [part dicts]; stylize(img, style, ramps=None, **opts) -> RGBA;
stylize_parts(items, style, ramps=None, **opts); analyse / targets (the two steps inside); check / style_ramps.

    python3 drawing_styles.py chart OUT.png [--hd]                 objects x styles chart (x4, HD x3)
    python3 drawing_styles.py render NAME OUT.png [--hd] [--style S] [--no-shadow]
    python3 drawing_styles.py parts NAME OUT_DIR [--hd] [--style S]  PNG per part + layers.json + .aseprite
    python3 drawing_styles.py stylize IN.png OUT.png STYLE [--kit MODULE] [--outline MODE] [--dither]
    python3 drawing_styles.py styles IN.png OUT.png [--kit MODULE]  one sprite in every style, labelled
    python3 drawing_styles.py outlines OUT.png [--hd]              the outline modes on three objects
    python3 drawing_styles.py check NAME [OUT.png] [--hd] [--style S]  shading.check with the style's ramps
    python3 drawing_styles.py list                                 objects, styles, outline modes
"""
import colorsys
import math
import os
import random
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kitchen import _r5, edge_ring, N4, WALNUT          # noqa: E402
from hub import GOLD, CREAM                              # noqa: E402
from shading import ramp5, pixel_perfect, sphere5        # noqa: E402
from modes import Parts, compose, override               # noqa: E402,F401 (override re-exported for parts)
import layers                                            # noqa: E402

# ------------------------------------------------------------------ house ramps (outline, shadow, dark, base, light, hi)
ORB = _r5('#3a7cc8', soft=0.15)         # glossy ball: keeps its contrast
STONE = _r5('#8c9098', soft=1)          # matte stone: cube, footing, chimney
MOSS = _r5('#6a9a3c', soft=0.7)
STEEL = _r5('#9aa6b8')                  # metal: standard (hard) contrast
GRIP = _r5('#5e3e2c', soft=1)           # leather wrap
GEM = _r5('#d0304a', soft=0.2)
PLASTER = _r5('#e8dcbe', soft=0.45)    # a wider ramp: the lit and shaded walls must separate
ROOF = _r5('#b44a3a', soft=0.8)
DOOR = _r5('#a0703e', soft=1)
GLASS = _r5('#9cc6e2', soft=0.5)
LEAVES = _r5('#4e9a3a', soft=0.7)
BARK = _r5('#6e4c30', soft=1)
APPLE = _r5('#d23a3a', soft=0.4)
GRASS = _r5('#64b040', soft=0.6)
FLOWER = _r5('#e8c03a', soft=0.5)
POTION = _r5('#c43c8e', soft=0.4)
CORK = _r5('#b8885a', soft=1)
SMOKE = _r5('#c4c6cc', soft=1)
SHADOW = _r5('#7c808c', soft=1)         # ground shadow: core [1], penumbra [2] - never outlined
TIMBER = WALNUT

LIGHT = (-0.55, -0.62, 0.56)            # top-left, the same light as shading.sphere5
N8 = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]


def P(im, x, y, c):
    if c is not None and 0 <= x < im.width and 0 <= y < im.height:
        im.putpixel((int(x), int(y)), c)


def ell(cx, cy, rx, ry=None):
    """Pixels whose centres lie in the ellipse (pixel-art discs: symmetric about cx, cy)."""
    ry = ry or rx
    return {(x, y) for y in range(int(cy - ry - 1), int(cy + ry + 2)) for x in range(int(cx - rx - 1), int(cx + rx + 2))
            if ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= 1}


def _lam(nx, ny):
    """Lambert term of a sphere normal at (nx, ny) for the top-left light."""
    r2 = nx * nx + ny * ny
    nz = math.sqrt(max(0.0, 1 - r2))
    ln = math.sqrt(sum(c * c for c in LIGHT))
    return (nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2]) / ln


class Sheet:
    """A drawing in progress: pixel -> (ramp, tone). Every pixel knows its material, so the outline can take
    the dark tone of the area it wraps (per area) and the softer shadow tone on the lit top / left side
    (selective) - the house outline."""

    def __init__(self):
        self.px = {}

    def put(self, x, y, ramp, t):
        self.px[(int(x), int(y))] = (ramp, t)

    def fill(self, pts, ramp, t):
        for p in pts:
            self.put(*p, ramp, t)

    def tone(self, p):
        v = self.px.get(p)
        return v[1] if v else None

    def ramp(self, p):
        v = self.px.get(p)
        return v[0] if v else None

    def shift(self, p, d, lo=1, hi=5):
        """Move a pixel d tones along its own ramp (clusters, chips, lit edges)."""
        if p in self.px:
            r, t = self.px[p]
            self.px[p] = (r, max(lo, min(hi, t + d)))

    def outline(self, lit=1, dark=0, solid=None, skip=()):
        """Selective outline per area round `solid` (default: everything drawn): ring pixels on the lit top /
        left side take tone `lit` of the ramp they wrap, the others tone `dark`. Ramps in `skip` (shadows) get
        no outline. 4-neighbour rings have no doubles."""
        solid = set(self.px) if solid is None else set(solid)
        for q in sorted(edge_ring(solid)):
            nb = [self.px[(q[0] + dx, q[1] + dy)][0] for dx, dy in N4 if (q[0] + dx, q[1] + dy) in solid]
            nb = [r for r in nb if not any(r is s for s in skip)]
            if not nb:
                continue
            r = max(nb, key=lambda x: sum(1 for y in nb if y is x))     # most common; ties: first in N4
            below = (q[0], q[1] + 1) in solid or (q[0] + 1, q[1]) in solid
            above = (q[0], q[1] - 1) in solid or (q[0] - 1, q[1]) in solid
            self.px[q] = (r, lit if below and not above else dark)

    def paint(self, im):
        for (x, y), (r, t) in self.px.items():
            P(im, x, y, r[t])


def _chips(sh, face, ramp, n, d, rnd, shape='h', avoid=()):
    """n texture clusters (2-3 px, never single pixels) shifted d tones inside `face`, not touching each other
    or the face border. shape 'h' = horizontal streak, 'l' = 2:1 iso streak down-right, 'r' = up-right."""
    face = set(face)
    used = set(avoid)
    cand = sorted(face)
    tries = 0
    while n > 0 and tries < 400:
        tries += 1
        x, y = cand[rnd.randrange(len(cand))]
        ln = rnd.choice((2, 2, 3))
        if shape == 'h':
            pts = [(x + i, y) for i in range(ln)]
        elif shape == 'l':
            pts = [(x + i, y + (i + 1) // 2) for i in range(ln)]
        else:
            pts = [(x + i, y - (i + 1) // 2) for i in range(ln)]
        if rnd.random() < 0.35:
            pts.append((pts[0][0] + 1, pts[0][1] + 1))
        if not all(p in face and all((p[0] + a, p[1] + b) in face for a, b in N4) for p in pts):
            continue
        if any((p[0] + a, p[1] + b) in used for p in pts for a, b in N8 + [(0, 0)]):
            continue
        for p in pts:
            if sh.ramp(p) is ramp:
                sh.shift(p, d)
        used.update(pts)
        n -= 1
    return used


def _crack(sh, x, y, steps, ramp, t=1):
    """A dark 1 px crack walking down: steps = [(dx, dy), ...] (diagonal steps keep it free of doubles)."""
    pts = [(x, y)]
    for dx, dy in steps:
        x, y = x + dx, y + dy
        pts.append((x, y))
    for p in pts:
        if sh.ramp(p) is ramp:
            sh.put(*p, ramp, t)
    return pts


def _ground_shadow(cx, cy, rx, ry, k=1):
    """Projected shadow on the ground: a hard core (SHADOW[1]) and a penumbra one step lighter (SHADOW[2]) as
    a crescent round its far (right) end - one extra step, no blur. Returns {pixel: colour}."""
    core = ell(cx, cy, rx, ry)
    pen = ell(cx + k, cy, rx + 0.5 * k, ry) - core
    out = {p: SHADOW[2] for p in pen if p[0] > cx}
    out.update({p: SHADOW[1] for p in core})
    return out


# ------------------------------------------------------------------ 1. sphere
def _ball_tone(nx, ny, k):
    """Tone index on a glossy ball, light from the top-left: a small highlight, a wide lit cap, base, dark mid,
    a narrow terminator, the shadow side lifted by bounce light, a rim light on the lower-right edge (k=2)."""
    r2 = nx * nx + ny * ny
    lam = _lam(nx, ny)
    if math.hypot(nx + 0.36, (ny + 0.4) * 1.2) < (0.2 if k == 1 else 0.15):
        return 5
    if k == 2 and math.hypot(nx + 0.06, ny + 0.02) < 0.06:
        return 5                                                   # a small reflection next to the highlight
    if lam > 0.7:
        return 4
    if lam > 0.3:
        return 3
    if lam > 0.02:
        return 2
    if lam > -0.2:
        return 1                                                   # terminator: narrow and darkest
    if k == 2 and r2 > 0.86 and ny > 0.2 and nx > -0.2:
        return 3                                                   # rim light
    return 2                                                       # bounce light lifts the shadow


def sphere(k=1, shadow=True, **_):
    """Glossy ball: highlight (+ reflection at k=2), lit cap, base, dark mid, a narrow terminator, the shadow
    lifted by bounce light, a rim light (k=2), a selective outline and a projected shadow down-right."""
    S = 16 * k
    Pt = Parts(S, S)
    cx, cy, r = (7.5, 7.5, 5.5) if k == 1 else (15.0, 14.0, 10.9)
    ball = ell(cx, cy, r)

    def shade(im):
        if shadow:
            for p, c in _ground_shadow(cx + 1.5 * k, cy + r + 0.5 * k, r * 0.9, 1.3 * k, k).items():
                P(im, *p, c)

    def body(im):
        sh = Sheet()
        for (x, y) in ball:
            sh.put(x, y, ORB, _ball_tone((x + 0.5 - cx) / r, (y + 0.5 - cy) / r, k))
        sh.outline(1, 0)
        sh.paint(im)
        pixel_perfect(im, only={ORB[1]})                # the narrow terminator: a clean 1 px band

    Pt.add('shadow', shade)
    Pt.add('ball', body)
    return Pt


# ------------------------------------------------------------------ 2. stone cube (2:1 iso)
def _cube_faces(cx, top, a, side):
    """Pixel sets of a 2:1 iso block: top diamond (rows 2, 6, .. 4a-2 px wide), left and right faces."""
    topf = set()
    for j in range(2 * a):
        kk = j if j < a else 2 * a - 1 - j
        topf |= {(x, top + j) for x in range(cx - 2 * kk - 1, cx + 2 * kk + 1)}
    col_top = {}
    for (x, y) in topf:
        col_top[x] = max(col_top.get(x, -1), y + 1)
    left, right = set(), set()
    for x, y0 in col_top.items():
        for y in range(y0, y0 + side):
            (left if x < cx else right).add((x, y))
    return topf, left, right


def stone_cube(k=1, shadow=True, moss=True, seed=7, **_):
    """A stone block in 2:1 isometric: lit top (light mid, highlight on the near-left edge), base left face,
    dark-mid right face, AO on the bottom rows, chips (clusters along each face), dark cracks, a moss patch on
    the far corner hanging over the left face, selective outline, a short cast shadow to the right."""
    a, side = 4 * k, 7 * k
    W, H = 16 * k + 3 * k, 16 * k + 2 * k
    cx, top = 8 * k, 1
    topf, left, right = _cube_faces(cx, top, a, side)
    rnd = random.Random(seed + k)
    Pt = Parts(W, H)

    def shade(im):
        if not shadow:
            return
        for x in range(cx - k, cx + 2 * a):
            yb = top + 2 * a + side - 1 - max(0, x - cx) // 2 + 2
            far = x >= cx + 2 * a - 2 * k
            for d in range(k):
                P(im, x, yb + d, SHADOW[2] if far else SHADOW[1])

    def block(im):
        sh = Sheet()
        sh.fill(topf, STONE, 4)
        sh.fill(left, STONE, 3)
        sh.fill(right, STONE, 2)
        for (x, y) in topf:                                          # near edges catch the light
            if (x, y + 1) not in topf and x < cx:
                sh.put(x, y, STONE, 5)
            elif (x, y + 1) not in topf and x < cx + 2 * k:
                sh.put(x, y, STONE, 5)
        bottom = {}
        for (x, y) in left | right:
            bottom[x] = max(bottom.get(x, 0), y)
        for x, y in bottom.items():                                  # contact with the ground: AO
            for d in range(k):
                sh.put(x, y - d, STONE, 2 if x < cx else 1)
        for y in range(min(yy for xx, yy in left if xx == cx - 1), bottom[cx - 1] - k + 1):
            sh.put(cx - 1, y, STONE, 4)                              # the lit front edge
        inner_t = {p for p in topf if all((p[0] + a_, p[1] + b_) in topf for a_, b_ in N8)}
        inner_l = {p for p in left if p[1] < bottom[p[0]] - k and p[0] < cx - 1}
        inner_r = {p for p in right if p[1] < bottom[p[0]] - k}
        used = set()
        used |= _chips(sh, inner_t, STONE, 2 * k, -1, rnd, 'h')
        used |= _chips(sh, inner_t, STONE, k, 1, rnd, 'h', used)
        used |= _chips(sh, inner_l, STONE, 2 * k + 1, -1, rnd, 'l')
        used |= _chips(sh, inner_l, STONE, k + 1, 1, rnd, 'l', used)
        used |= _chips(sh, inner_r, STONE, 2 * k + 1, -1, rnd, 'r')
        used |= _chips(sh, inner_r, STONE, k, 1, rnd, 'r', used)
        if k == 1:                                                   # cracks: dark, diagonal steps
            _crack(sh, cx - 5, top + 9, [(1, 1), (0, 1), (1, 1)], STONE, 1)
            _crack(sh, cx + 4, top + 9, [(-1, 1), (0, 1)], STONE, 1)
        else:
            c = _crack(sh, cx - 11, top + 18, [(1, 1), (1, 1), (0, 1), (1, 1), (1, 1), (0, 1), (-1, 1)], STONE, 1)
            for (x, y) in c[1:5]:
                if sh.ramp((x - 1, y)) is STONE and sh.tone((x - 1, y)) == 3:
                    sh.put(x - 1, y, STONE, 4)                       # lit lip on the crack's upper side
            _crack(sh, cx + 9, top + 16, [(-1, 1), (-1, 1), (0, 1), (1, 1), (0, 1)], STONE, 0)
            _crack(sh, cx + 1, top + 5, [(1, 0), (1, 1), (1, 0)], STONE, 2)
        if moss:                                                     # moss on the far-left corner
            mx, my = cx - 2 * a + 2 * k, top + a - k
            patch = {(x, y) for (x, y) in ell(mx + 0.5 * k, my + 0.5 * k, 2.6 * k, 1.5 * k) if (x, y) in topf}
            for (x, y) in sorted(patch):
                sh.put(x, y, MOSS, 4 if (x + 1, y - 1) not in patch or (x, y - 1) not in patch else 3)
            for x in range(cx - 2 * a + 1, cx - 2 * a + 1 + 3 * k):
                y0 = min(yy for xx, yy in left if xx == x)
                hang = (2, 1, 1)[(x - cx) % 3] if k == 1 else (3, 2, 4, 3, 2, 1)[(x - cx) % 6]
                for d in range(hang):
                    sh.put(x, y0 + d, MOSS, 3 if d < hang - 1 else 2)
            if k == 2:
                for (x, y) in ((mx, my - 1), (mx + 3, my), (mx + 5, my + 1)):
                    if (x, y) in topf:
                        sh.put(x, y, MOSS, 5)
                        sh.put(x + 1, y, MOSS, 4)
        sh.outline(1, 0)
        sh.paint(im)

    Pt.add('shadow', shade)
    Pt.add('block', block)
    return Pt


# ------------------------------------------------------------------ 3. sword (diagonal, bottom-left -> top-right)
def sword(k=1, **_):
    """Sword on the diagonal. Pixels are addressed in blade coordinates: s = x + y - c (across, constant along
    each clean 45-degree line) and t = x - y (along). The upper-left bevel faces the light, the lower-right one
    turns away; the selective outline closes it. k=2 adds a fuller, a rim light on the shadow edge, reflection
    streaks, a curved guard with a gem and a round pommel."""
    S = 16 * k
    Pt = Parts(S, S)
    c = S - 1
    if k == 1:
        tip, guard, grip0, pom = 13, (-5, -4), -9, -11
        half = 1
    else:
        tip, guard, grip0, pom = 27, (-11, -9), -19, -24
        half = 2

    def st(x, y):
        return x + y - c, x - y

    def blade(im):
        sh = Sheet()
        for y in range(S):
            for x in range(S):
                s, t = st(x, y)
                if t <= guard[1] or abs(s) > half:
                    continue
                if t > tip - abs(s) * (2 if k == 1 else 3):
                    continue
                if k == 1:
                    tone = {-1: 4, 0: 3, 1: 2}[s]
                else:
                    tone = {-2: 5, -1: 4, 0: 4, 1: 2, 2: 3}[s]       # lit edge, bevel, ridge, shadow bevel, rim
                    if t < 8 and s in (0, 1):                        # fuller: dark groove, lit lower wall
                        tone = 1 if s == 0 else 3
                    if t in (13, 14, 21) and s in (-1, 0, 1):        # reflection streaks across the blade
                        tone = min(5, tone + 1)
                sh.put(x, y, STEEL, tone)
        if k == 1:
            for p in ((7, 7), (8, 6)):
                sh.put(*p, STEEL, 5)                                 # glint on the lit bevel
        sh.outline(1, 0)
        sh.paint(im)

    def hilt_guard(im):
        sh = Sheet()
        g0, g1 = guard
        w = 3 if k == 1 else 6
        for y in range(S):
            for x in range(S):
                s, t = st(x, y)
                bend = 0 if k == 1 else (1 if abs(s) >= w - 1 else 0)
                if g0 + bend <= t <= g1 + bend and abs(s) <= w:
                    tone = 4 if s < -1 else 3 if s <= 1 else 2
                    if t == g1 + bend and s < 1:
                        tone = 5 if k == 2 and s < -2 else max(tone, 4)
                    if t == g0 + bend:
                        tone = min(tone, 2 if s > 0 else 3)
                    sh.put(x, y, GOLD, tone)
        if k == 2:                                                   # a gem in the middle of the guard
            gx, gy = (c + (g0 + 1)) // 2, (c - (g0 + 1)) // 2
            for (dx, dy), tn in (((0, 0), 4), ((1, 0), 3), ((0, 1), 3), ((1, 1), 2)):
                sh.put(gx + dx - 1, gy + dy, GEM, tn)
            sh.put(gx - 1, gy, GEM, 5)
        sh.outline(1, 0)
        sh.paint(im)

    def grip(im):
        sh = Sheet()
        hw = 0 if k == 1 else 1
        for y in range(S):
            for x in range(S):
                s, t = st(x, y)
                if grip0 <= t < guard[0] and abs(s) <= hw:
                    band = ((t - grip0) // (2 if k == 1 else 3)) % 2
                    tone = (3 if band else 2) if k == 1 else ({-1: 4, 0: 3, 1: 2}[s] - (1 if band else 0))
                    sh.put(x, y, GRIP, max(1, tone))
        sh.outline(1, 0)
        sh.paint(im)

    def pommel(im):
        sh = Sheet()
        if k == 1:
            px0, py0 = (c + pom) // 2, (c - pom) // 2
            for (dx, dy), tn in (((0, 0), 4), ((1, 0), 3), ((0, 1), 3), ((1, 1), 2)):
                sh.put(px0 + dx, py0 + dy - 1, GOLD, tn)
        else:
            px0, py0 = (c + pom) / 2 + 0.5, (c - pom) / 2 - 0.5
            ball = ell(px0, py0, 2.2)
            for (x, y) in ball:
                lam = _lam((x + 0.5 - px0) / 2.2, (y + 0.5 - py0) / 2.2)
                sh.put(x, y, GOLD, 5 if lam > 0.85 else 4 if lam > 0.5 else 3 if lam > 0.1 else 2)
        sh.outline(1, 0)
        sh.paint(im)

    Pt.add('grip', grip)
    Pt.add('blade', blade)
    Pt.add('guard', hilt_guard)
    Pt.add('pommel', pommel)
    return Pt


# ------------------------------------------------------------------ 4. potion
def potion(k=1, sparkle=True, **_):
    """Round flask (item-icon rules, references/item-icons.md): glass walls light on the left, dark on the
    right and bottom, the empty part transparent, the liquid lit top-left with a light surface line, a bubble
    and a glint; a cork; at k=2 a meniscus ellipse, a caustic, twine round the neck and two sparkles."""
    S = 16 * k
    Pt = Parts(S, S)
    if k == 1:
        bx, by, rx, ry = 8.0, 10.0, 4.7, 4.9
        neck = (6, 9, 4, 4)                      # x0, x1, y0, y1
        lip = (5, 10, 3)
        cork = (6, 9, 1, 2)
        surf = 8
    else:
        bx, by, rx, ry = 16.0, 20.5, 9.6, 9.8
        neck = (12, 19, 7, 11)
        lip = (10, 21, 5, 6)
        cork = (12, 19, 1, 4)
        surf = 16
    body = ell(bx, by, rx, ry)
    neck_px = {(x, y) for x in range(neck[0], neck[1] + 1) for y in range(neck[2], neck[3] + 1)}
    if k == 1:
        lip_px = {(x, lip[2]) for x in range(lip[0], lip[1] + 1)}
    else:
        lip_px = {(x, y) for x in range(lip[0], lip[1] + 1) for y in range(lip[2], lip[3] + 1)}
    glass_solid = body | neck_px | lip_px
    walls = {p for p in glass_solid if any((p[0] + a, p[1] + b) not in glass_solid for a, b in N4)}
    if k == 2:                                       # 2 px glass at the bottom and the neck sides
        walls |= {(x, y) for (x, y) in body if (x, y + 2) not in body}
        walls |= {(x, y) for (x, y) in neck_px if x in (neck[0] + 1, neck[1] - 1)}
    walls |= lip_px
    inside = glass_solid - walls
    liquid = {p for p in inside if p[1] >= surf}

    def liquid_part(im):
        sh = Sheet()
        xs = [x for x, _ in liquid]
        yb = max(y for _, y in liquid)
        for (x, y) in liquid:
            nx, ny = (x + 0.5 - bx) / rx, (y + 0.5 - by) / ry
            lam = _lam(nx, ny * 0.8)
            t = 4 if lam > 0.72 else 3 if lam > 0.32 else 2
            if y == yb or (x, y + 1) not in liquid and lam < 0.5:
                t = 1
            sh.put(x, y, POTION, t)
        row = sorted(x for x, y in liquid if y == surf)
        for x in row:                                                # surface line: light, highlight at left
            sh.put(x, surf, POTION, 5 if x < row[0] + max(2, len(row) // 3) else 4)
        if k == 2:                                                   # meniscus: second light row, curved
            row2 = sorted(x for x, y in liquid if y == surf + 1)
            for x in row2[2:-3]:
                sh.put(x, surf + 1, POTION, 4)
            for (x, y) in liquid:                                    # caustic: light gathered at the bottom
                if ((x + 0.5 - (bx + 3)) / 3.2) ** 2 + ((y + 0.5 - (by + 6)) / 1.6) ** 2 <= 1:
                    sh.put(x, y, POTION, 4)
            for (x, y, r_) in ((bx - 3, by + 1, 1), (bx + 2, by - 2, 0), (bx - 1, by + 5, 0)):
                if r_:                                               # a ring bubble
                    for p in ((x, y - 1), (x - 1, y), (x + 1, y), (x, y + 1)):
                        sh.put(*p, POTION, 5 if p[1] < y or p[0] < x else 4)
                else:
                    sh.put(x, y, POTION, 5)
                    sh.put(x + 1, y, POTION, 4)
        else:
            sh.put(min(xs) + 3, surf + 2, POTION, 5)                 # one bubble (a 2 px cluster)
            sh.put(min(xs) + 3, surf + 3, POTION, 5)
        sh.paint(im)

    def glass(im):
        sh = Sheet()
        top_y = min(y for _, y in body)
        for (x, y) in walls:
            if (x, y) in lip_px:
                t = 5 if x < lip[0] + 2 * k else 4 if x < (lip[0] + lip[1]) / 2 else 3
            elif (x, y) in neck_px:
                t = 4 if x < (neck[0] + neck[1]) / 2 else 2
            else:
                left = x + 0.5 < bx
                t = 4 if left else 2
                if y > by + ry * 0.55:
                    t = 2 if left else 1
                if left and y < by - ry * 0.1:
                    t = 5 if (k == 1 and top_y + 1 <= y <= top_y + 3) or (k == 2 and y < by - ry * 0.3) else 4
            sh.put(x, y, GLASS, t)
        if k == 2:                                                   # a window glint on the right shoulder
            for p in ((int(bx + rx * 0.5), int(by - ry * 0.55)), (int(bx + rx * 0.5) + 1, int(by - ry * 0.55) + 1)):
                if p in liquid or p in inside:
                    sh.put(*p, GLASS, 5)
            for y in range(int(by - ry * 0.5), int(by + ry * 0.2)):   # a long reflection streak on the left
                x = int(bx - rx * 0.62 + (y - by) ** 2 / (ry * 3.5))
                if (x, y) in inside:
                    sh.put(x, y, GLASS, 5 if y < by - ry * 0.25 else 4)
        sh.outline(1, 0, solid=set(sh.px) | inside)
        sh.paint(im)

    def cork_part(im):
        sh = Sheet()
        x0, x1, y0, y1 = cork
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                t = 4 if x < x0 + 2 * k else 3 if x < x1 - k + 1 else 2
                if y == y0:
                    t = 5 if x < x0 + k else 4 if x < x1 - k + 1 else 3
                sh.put(x, y, CORK, t)
        if k == 2:
            for (x, y) in ((x0 + 3, y0 + 2), (x0 + 5, y0 + 3), (x0 + 2, y0 + 3)):
                sh.put(x, y, CORK, 2)                                # pores
            sh.put(x0 + 4, y0 + 2, CORK, 2)
        sh.outline(1, 0)
        sh.paint(im)

    def twine(im):                                              # a twisted cord round the neck, loose end
        sh = Sheet()
        y = neck[2] + 2
        for x in range(neck[0] - 1, neck[1] + 2):
            sh.put(x, y, CREAM, (4 if x % 2 else 3) if x < neck[1] - 1 else (3 if x % 2 else 2))
        for d, (dx, dy) in enumerate(((1, 1), (2, 2), (2, 3))):
            sh.put(neck[1] + dx, y + dy, CREAM, 3 if d < 1 else 2)
        sh.outline(1, 0)
        sh.paint(im)

    def sparkles(im):
        for (x, y, big) in ((26, 7, True), (5, 9, False)):
            P(im, x, y, CREAM[5])
            for dx, dy in N4:
                P(im, x + dx, y + dy, POTION[4])
            if big:
                for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)):
                    P(im, x + dx, y + dy, POTION[3])

    Pt.add('liquid', liquid_part)
    Pt.add('glass', glass)
    Pt.add('cork', cork_part)
    if k == 2:
        Pt.add('twine', twine)
        if sparkle:
            Pt.add('sparkles', sparkles)
    return Pt


# ------------------------------------------------------------------ 5. house (2:1 iso timber cottage)
class _HouseGeo:
    """Per-column geometry of the iso cottage: a lit left wall (door, window), a shaded right wall under the
    gable, a roof plane facing up-left whose ridge runs parallel to the left wall, and the roof's thickness
    along both gable edges (barge boards). Slopes: walls, eave and ridge 2:1; the front gable edge 3 px up per
    2 px (a regular 2-1 staircase), the back one 1:2 - every edge a clean pixel-art line."""

    def __init__(self, k):
        self.k = k
        self.LW, self.RW, self.HW = 10 * k, 8 * k, 11 * k
        self.cx, self.gy = (13, 24) if k == 1 else (26, 49)
        self.L0 = self.cx - self.LW
        self.R1 = self.cx + self.RW - 1
        self.top_front = self.gy - self.HW + 1
        self.x_a = self.cx + self.RW // 2 - 1
        self.y_a = self.top_front - 6 * k
        self.x_lo = self.L0 - 2 * k
        self.ov = k                                  # how far the roof edge hangs over the gable line

    def bot(self, x):
        cx = self.cx
        return self.gy - ((cx - 1 - x) // 2 if x < cx else (x - cx) // 2)

    def top(self, x):
        return self.bot(x) - self.HW + 1

    def gable(self, x):
        i = x - self.cx
        if i < self.RW // 2:
            return self.top_front - (3 * (i + 1)) // 2
        return self.y_a + (i - self.RW // 2 + 1) // 2

    def ridge(self, x):
        return self.y_a - (self.x_a - x) // 2

    def eave(self, x):
        return self.gy - (self.cx - 1 - x) // 2 - self.HW + 1 + self.k

    def plane(self):
        """{x: (top, bottom)} of the visible roof plane."""
        out = {}
        e0 = self.eave(self.x_lo)
        for x in range(self.x_lo, self.x_a + 1):
            t = self.ridge(x)
            if x < self.x_lo + self.RW // 2:
                t = max(t, e0 - (3 * (x - self.x_lo)) // 2 - self.k)
            b = self.eave(x) if x < self.cx else self.gable(x) + self.ov
            out[x] = (t, b)
        return out


def house(k=1, shadow=True, smoke=True, seed=3, **_):
    """A little timber cottage in 2:1 iso: cream plaster between dark timber posts, a stone footing, an oak door
    and a window on the lit left wall, a gable window and a tie beam on the shaded right wall, a red tiled
    roof (tile rows along the eave, a lit ridge cap, barge boards in shade), a stone chimney with its contact
    shadow on the tiles; a soft eave shadow on the walls (one step), a cast shadow to the right. k=2 adds stone
    courses, a brace post, framed windows with mullions, a flower box, a door with planks and a step, tile
    gaps, bricks, a smoke puff and grass tufts."""
    g = _HouseGeo(k)
    W, H = 24 * k, g.gy + 3 * k
    Pt = Parts(W, H)
    cx, gy, L0, R1 = g.cx, g.gy, g.L0, g.R1
    foot = 2 * k
    plane = g.plane()

    def shade(im):
        if not shadow:
            return
        for x in range(cx, R1 + 3 * k + 1):
            yb = gy - (x - cx) // 2
            for d in range(2, k + 2):
                P(im, x, yb + d, SHADOW[1] if x <= R1 + k else SHADOW[2])
            if x > R1:                                              # the roof's shadow past the back corner
                for d in range(-k, 2):
                    P(im, x, yb + d, SHADOW[1] if x <= R1 + k else SHADOW[2])

    def walls(im):
        sh = Sheet()
        for x in range(L0, R1 + 1):
            left = x < cx
            for y in range(g.top(x), g.bot(x) + 1):
                fy = g.bot(x) - y                                   # height above the ground
                if fy < foot:
                    t = (3 if fy == foot - 1 else 2) if left else (2 if fy == foot - 1 else 1)
                    sh.put(x, y, STONE, t)
                elif fy < foot + k:
                    sh.put(x, y, TIMBER, (3 if fy == foot else 4) if left else 2)   # sill beam
                else:
                    sh.put(x, y, PLASTER, 3 if left else 2)
            if not left:                                            # gable over the right wall + its tie beam
                for y in range(g.gable(x), g.top(x)):
                    sh.put(x, y, PLASTER, 2)
                for d in range(k):
                    sh.put(x, g.top(x) + d, TIMBER, 2 if d == 0 else 1)
        for x in range(L0, cx):                                     # soft eave shadow: one step, no outline
            e = g.eave(x)
            sh.put(x, e + 1, PLASTER, 2)
            if k == 2 and (x // 3) % 2 == 0:
                sh.put(x, e + 2, PLASTER, 2)
        posts = [(L0, 3), (cx - 1, 4), (cx, 2), (R1, 1)] if k == 1 else \
            [(L0, 4), (L0 + 1, 3), (cx - 2, 4), (cx - 1, 4), (cx, 2), (cx + 1, 1), (R1 - 1, 2), (R1, 1),
             (cx - 11, 4), (cx - 10, 3)]
        for x, t in posts:                                          # timber posts
            for y in range(g.top(x), g.bot(x) - foot - k + 1):
                if sh.ramp((x, y)) is PLASTER or sh.ramp((x, y)) is TIMBER:
                    sh.put(x, y, TIMBER, t)
        if k == 2:
            for x in range(L0, R1 + 1):                             # two stone courses in the footing: a
                left = x < cx                                       # mortar line between them, lit stone
                b = g.bot(x)                                        # tops (no vertical joints: they would
                sh.put(x, b - 1, STONE, 2 if left else 1)           # make L-corners on the 2:1 lines)
                if left:
                    sh.put(x, b - foot + 1, STONE, 4)                       # lit top of the footing
                    if (x + (b % 2) * 3) % 6 in (0, 1):
                        sh.put(x, b - 2, STONE, 4)                          # lit top of a lower stone
        # windows
        if k == 1:
            wx = cx - 8
            wb = g.bot(wx) - foot - k - 1                             # sill row
            for (dx, dy), t in (((0, -2), 5), ((1, -2), 4), ((0, -1), 4), ((1, -1), 3)):
                sh.put(wx + dx, wb + dy, GLASS, t)
            for dx in (0, 1):
                sh.put(wx + dx, wb, TIMBER, 3)
            rx = cx + 4
            rb = g.bot(rx) - foot - k - 1
            for (dx, dy), t in (((0, -2), 3), ((1, -2), 3), ((0, -1), 2), ((1, -1), 2)):
                sh.put(rx + dx, rb + dy, GLASS, t)
            for dx in (0, 1):
                sh.put(rx + dx, rb, TIMBER, 1)
            vx = g.x_a
            for dx in (0, 1):                                       # attic vent under the apex
                sh.put(vx + dx, g.gable(vx) + g.ov + 2, TIMBER, 1)
        else:
            wx = cx - 17                                            # framed window with a cross mullion
            wb = g.bot(wx) - foot - k - 1
            for dy in range(-7, 1):
                for dx in range(-1, 5):
                    x, y = wx + dx, wb + dy
                    if dy in (-7, 0) or dx in (-1, 4):
                        sh.put(x, y, TIMBER, 4 if dy == -7 or dx == -1 else 3 if dy == 0 else 2)
                    elif dx == 2 or dy == -3:
                        sh.put(x, y, TIMBER, 3)
                    else:
                        sh.put(x, y, GLASS, 5 if (dx, dy) in ((0, -6), (1, -6), (0, -5)) else
                               4 if dx + (dy + 6) < 3 else 3 if dy < -3 or dx < 2 else 2)
            rx = cx + 6
            rb = g.bot(rx) - foot - k - 1
            for dy in range(-6, 1):
                for dx in range(-1, 5):
                    x, y = rx + dx, rb + dy
                    if dy in (-6, 0) or dx in (-1, 4):
                        sh.put(x, y, TIMBER, 2 if dy == -6 or dx == -1 else 1)
                    elif dx == 1 or dy == -3:
                        sh.put(x, y, TIMBER, 1)
                    else:
                        sh.put(x, y, GLASS, 3 if (dx == 0 and dy < -3) else 2)
            vx = g.x_a - 1                                          # round attic vent
            vy = g.gable(g.x_a) + g.ov + 3
            for (dx, dy), t in (((1, 0), 0), ((2, 0), 0), ((1, 1), 0), ((2, 1), 1), ((0, 0), 1), ((0, 1), 1),
                                ((3, 0), 1), ((3, 1), 1), ((1, -1), 1), ((2, -1), 1), ((1, 2), 2), ((2, 2), 2)):
                sh.put(vx + dx, vy + dy, TIMBER, t)
        sh.outline(1, 0)
        sh.paint(im)

    def door(im):
        sh = Sheet()
        if k == 1:
            dx0 = cx - 4
            for x in (dx0, dx0 + 1):
                b = g.bot(x)
                for y in range(b - 5, b + 1):
                    sh.put(x, y, DOOR, 1 if y == b - 5 else 3 if x == dx0 else 2)
            sh.put(dx0 + 1, g.bot(dx0) - 2, GOLD, 4)
        else:
            dx0 = cx - 8                                            # 4 px leaf in a timber frame
            for x in range(dx0 - 1, dx0 + 5):
                b = g.bot(x)
                for y in range(b - 12, b + 1):
                    if x in (dx0 - 1, dx0 + 4) or y == b - 12:
                        sh.put(x, y, TIMBER, 4 if x == dx0 - 1 or y == b - 12 else 2)
                        continue
                    i = x - dx0
                    t = 3 if i in (0, 2) else 2                     # planks
                    if y == b - 11:
                        t = 1                                       # the lintel's shadow
                    elif y in (b - 7, b - 2):
                        t = 2 if i < 3 else 1                       # battens
                    if i == 3:
                        t = min(t, 2)
                    sh.put(x, y, DOOR, t)
            sh.put(dx0 + 2, g.bot(dx0 + 2) - 5, GOLD, 5)
            sh.put(dx0 + 2, g.bot(dx0 + 2) - 4, GOLD, 2)
        sh.paint(im)

    def step(im):                                               # a stone slab in front of the door
        sh = Sheet()
        dx0 = cx - 8
        for x in range(dx0 - 2, dx0 + 6):
            b = g.bot(x) + 1
            sh.put(x, b, STONE, 4 if x < dx0 + 3 else 3)
            sh.put(x, b + 1, STONE, 2)
        sh.outline(1, 0)
        sh.paint(im)

    def roof(im):
        sh = Sheet()
        per, ph = (3, 0) if k == 1 else (4, 1)
        for x, (t, b) in plane.items():
            for y in range(t, b + 1):
                tone = 4
                if (g.eave(x) - y) % per == ph and y > t + k:
                    tone = 3                                        # tile rows along the eave
                sh.put(x, y, ROOF, tone)
            for d in range(k):
                sh.put(x, t + d, ROOF, 5 if d == 0 else 4)          # ridge cap
            if x < cx:
                sh.put(x, b, ROOF, 2)                               # the eave's edge
                if k == 2:
                    sh.put(x, b - 1, ROOF, 3)
            else:
                for d in range(k):
                    sh.put(x, b - d, ROOF, 2 if d == 0 else 3)      # front barge board, in shade
        for x in range(g.x_a + 1, R1 + 2 * k + 1):                  # back barge board (+ overhang)
            gt = g.gable(min(x, R1)) + max(0, x - R1) // 2
            for d in range(k):
                sh.put(x, gt + d, ROOF, 2 if d == 0 else 1)
        if k == 2:                                                  # staggered gaps between the tiles: a short
            for (x, y), (r, tone) in list(sh.px.items()):           # mark in the middle of a tile row, never
                if x >= cx - 1 or tone != 4:                        # touching the row lines (no L-corners)
                    continue
                row = (g.eave(x) - y) // per
                if (g.eave(x) - y) % per == 3 and (x + row * 3) % 6 == 0 and y > plane[x][0] + k:
                    sh.put(x, y, ROOF, 3)
        sh.outline(1, 0)
        sh.paint(im)

    cw = 3 * k
    chx = cx - 7 * k

    def chimney(im):
        sh = Sheet()
        top = g.ridge(chx) - 2 * k
        for x in range(chx, chx + cw):
            yb = g.ridge(x) + 2 * k
            for y in range(top, yb + 1):
                t = 3 if x < chx + k else 2 if x < chx + cw - k else 1
                if k == 2 and y > top + 2:
                    rowi = (y - top - 3) // 2
                    if (y - top - 3) % 2 == 1 or (x - chx + rowi * 3) % 6 == 0:
                        t = max(1, t - 1)                           # brick courses and joints
                sh.put(x, y, STONE, t)
        for x in range(chx - (k - 1), chx + cw + (k - 1)):          # cap
            sh.put(x, top, STONE, 4 if x < chx + cw - k else 2)
            if k == 2:
                sh.put(x, top + 1, STONE, 2 if chx <= x < chx + cw - 1 else 3)
        sh.outline(1, 0)
        sh.paint(im)

    def chimney_shadow(im):                                     # contact shadow of the chimney on the tiles
        for x in range(chx + cw, chx + cw + 2 * k):
            yb = g.ridge(x) + 2 * k
            for y in range(yb - 2 * k, yb + 1):
                if plane.get(x) and plane[x][0] + k <= y <= plane[x][1] - k:
                    P(im, x, y, ROOF[3] if x < chx + cw + k else ROOF[3])

    def smoke_part(im):
        top = g.ridge(chx) - 2 * k
        for (sx, sy, r) in ((chx + 8, top + 3.5, 2.2), (chx + 14, top + 2.0, 1.8)):
            pts = ell(sx, sy, r * 1.4, r)
            pts = {p for p in pts if p[1] >= 1}
            sh = Sheet()
            for (x, y) in pts:
                sh.put(x, y, SMOKE, 4 if (x + 0.5 - sx) * 0.7 + (y + 0.5 - sy) < -0.4 else 3)
            sh.outline(2, 1)
            sh.paint(im)

    def grass(im):
        rnd2 = random.Random(seed)
        for x in range(L0 + 1, cx - 9, 4):
            b = g.bot(x)
            h = rnd2.choice((2, 3))
            sh = Sheet()
            for i in range(h):
                sh.put(x, b - i, GRASS, 4 if i == h - 1 else 3)
            sh.put(x + 1, b, GRASS, 2)
            sh.put(x - 1, b, GRASS, 3)
            sh.paint(im)

    def flowers(im):
        wx = cx - 17
        wb = g.bot(wx) - foot - k - 1
        sh = Sheet()
        for dx in range(-1, 5):
            sh.put(wx + dx, wb + 1, TIMBER, 3 if dx < 3 else 2)
            sh.put(wx + dx, wb + 2, TIMBER, 2 if dx < 3 else 1)
        for dx in (0, 1, 2, 3):
            sh.put(wx + dx, wb, LEAVES, 4 if dx < 2 else 3)
        for dx, col in ((-1, APPLE), (1, FLOWER), (3, APPLE)):
            sh.put(wx + dx, wb - 1, col, 5 if col is FLOWER else 4)
            sh.put(wx + dx + 1, wb - 1, col, 3)
        sh.outline(1, 0)
        sh.paint(im)

    Pt.add('shadow', shade)
    Pt.add('walls', walls)
    Pt.add('door', door)
    if k == 2:
        Pt.add('step', step)
    Pt.add('roof', roof)
    Pt.add('chimney_shadow', chimney_shadow)
    Pt.add('chimney', chimney)
    if k == 2:
        Pt.add('flowers', flowers)
        Pt.add('grass', grass)
        if smoke:
            Pt.add('smoke', smoke_part)
    return Pt


# ------------------------------------------------------------------ 6. tree
def tree(k=1, shadow=True, apples=True, seed=5, **_):
    """An oak: a canopy of round clumps, each lit from the top-left like a ball (tone by its own normal), the
    clumps in front casting a soft shadow on the ones behind, leaf clusters (never single pixels), a trunk
    with bark streaks shaded under the canopy, flared roots, a ground shadow. k=2: more clumps, leaf-shaped
    clusters, a branch in a gap, apples, grass tufts."""
    S = 24 * k
    Pt = Parts(S, S)
    rnd = random.Random(seed + k)
    if k == 1:
        clumps = [(12.0, 9.5, 7.2, 6.2), (6.5, 11.5, 4.4, 3.8), (17.8, 11.2, 4.8, 4.0), (8.5, 5.5, 4.6, 4.0),
                  (15.2, 5.0, 4.4, 3.8), (12.0, 13.0, 4.2, 2.6)]
        trunk_x, trunk_w, trunk_top, ground = 10, 4, 12, 21
    else:
        clumps = [(24.0, 19.0, 14.5, 12.5), (12.5, 23.5, 8.6, 7.4), (35.5, 22.5, 9.4, 7.8), (16.5, 11.0, 9.0, 7.6),
                  (30.5, 10.0, 8.8, 7.4), (23.5, 6.5, 7.2, 5.6), (8.5, 17.0, 5.4, 4.6), (40.0, 15.0, 5.6, 4.8),
                  (24.0, 27.0, 8.4, 4.8)]
        trunk_x, trunk_w, trunk_top, ground = 20, 8, 25, 43
    owner = {}
    for i, (ccx, ccy, rx, ry) in enumerate(clumps):
        for p in ell(ccx, ccy, rx, ry):
            owner[p] = i
    canopy = set(owner)

    def shade(im):
        if shadow:
            sx = trunk_x + trunk_w / 2 + 2.5 * k
            for p, c in _ground_shadow(sx, ground + 0.5, 8.0 * k, 1.4 * k, k).items():
                P(im, *p, c)

    def trunk(im):
        sh = Sheet()
        for y in range(trunk_top - 2 * k, ground + 1):
            for i in range(trunk_w):
                x = trunk_x + i
                t = 4 if i < k else 3 if i < trunk_w - k else 2
                if k == 2 and i == trunk_w - 3:
                    t = 2
                sh.put(x, y, BARK, t)
        for i in range(k):                                             # flared roots
            for (x, y), t in (((trunk_x - 1 - i, ground - i), 3), ((trunk_x + trunk_w + i, ground - i), 2)):
                sh.put(x, y, BARK, t)
            sh.put(trunk_x - 1 - i, ground, BARK, 3)
            sh.put(trunk_x + trunk_w + i, ground, BARK, 2)
        if k == 2:
            for (x, y) in ((trunk_x - 3, ground), (trunk_x + trunk_w + 2, ground)):
                sh.put(x, y, BARK, 3 if x < trunk_x else 2)
        for _ in range(3 * k):                                        # bark streaks: vertical clusters
            x = trunk_x + rnd.randrange(1, trunk_w - 1)
            y = rnd.randrange(trunk_top + k, ground - 2 * k)
            for d in range(rnd.choice((2, 3)) * k):
                if (x, y + d) in sh.px:
                    sh.shift((x, y + d), -1)
        if k == 2:                                                    # a knot
            for (dx, dy), t in (((0, 0), 1), ((1, 0), 2), ((0, 1), 2), ((-1, 0), 4)):
                sh.put(trunk_x + 3 + dx, ground - 8 + dy, BARK, t)
        for y in range(trunk_top - 2 * k, trunk_top + 2 * k):         # the canopy's shadow on the trunk
            for i in range(trunk_w):
                sh.put(trunk_x + i, y, BARK, 1 if y < trunk_top + k else 2)
        if k == 2:                                                    # a branch reaching into the canopy
            for d in range(8):
                for w_ in range(2):
                    sh.put(trunk_x + trunk_w + d - 1, trunk_top - 3 - d // 2 - w_, BARK, 2 if w_ == 0 else 3)
        sh.outline(1, 0)
        sh.paint(im)

    def leaves(im):
        sh = Sheet()
        for (x, y), i in owner.items():
            ccx, ccy, rx, ry = clumps[i]
            nx, ny = (x + 0.5 - ccx) / rx, (y + 0.5 - ccy) / ry
            lam = _lam(nx, ny)
            t = 5 if lam > 0.93 else 4 if lam > 0.66 else 3 if lam > 0.3 else 2 if lam > -0.05 else 1
            if t == 5 and k == 1:
                t = 4
            sh.put(x, y, LEAVES, t)
        for (x, y), i in owner.items():                               # front clumps shade the ones behind
            for dx, dy in ((0, -1), (-1, -1), (0, -2)) if k == 2 else ((0, -1), (-1, -1)):
                j = owner.get((x + dx, y + dy))
                if j is not None and j > i and sh.tone((x, y)) is not None:
                    sh.put(x, y, LEAVES, max(1, min(sh.tone((x, y)), 2 if dy == -2 else 1)))
                    break
        interior = {p for p in canopy if all((p[0] + a, p[1] + b) in canopy for a, b in N8)}
        lit = {p for p in interior if sh.tone(p) >= 4}
        mid = {p for p in interior if sh.tone(p) == 3}
        dark = {p for p in interior if sh.tone(p) == 2}
        used = _chips(sh, lit, LEAVES, 4 * k * k, 1, rnd, 'r')
        used |= _chips(sh, mid, LEAVES, 4 * k * k, 1, rnd, 'r', used)
        used |= _chips(sh, mid, LEAVES, 3 * k * k, -1, rnd, 'l', used)
        used |= _chips(sh, dark, LEAVES, 2 * k * k, -1, rnd, 'h', used)
        sh.outline(1, 0)
        sh.paint(im)

    def fruit(im):
        sh = Sheet()
        for (x, y) in ((14, 16), (32, 14), (21, 25), (38, 24), (9, 22)):
            for (dx, dy), t in (((0, 0), 5), ((1, 0), 3), ((0, 1), 3), ((1, 1), 2), ((-1, 0), 4), ((-1, 1), 3),
                                ((0, 2), 2), ((-1, 2), 2), ((1, 2), 1)):
                sh.put(x + dx, y + dy, APPLE, t)
            sh.put(x, y - 1, BARK, 2)
        sh.outline(1, 0)
        sh.paint(im)

    def grass(im):
        for (x, h) in ((trunk_x - 6, 3), (trunk_x - 3, 4), (trunk_x + trunk_w + 3, 3), (trunk_x + trunk_w + 7, 2)):
            sh = Sheet()
            for i in range(h):
                sh.put(x, ground - i, GRASS, 4 if i == h - 1 else 3)
            sh.put(x - 1, ground, GRASS, 2)
            sh.put(x + 1, ground - 1, GRASS, 3)
            sh.put(x + 1, ground, GRASS, 2)
            sh.paint(im)

    Pt.add('shadow', shade)
    Pt.add('trunk', trunk)
    Pt.add('leaves', leaves)
    if k == 2:
        if apples:
            Pt.add('apples', fruit)
        Pt.add('grass', grass)
    return Pt


CATALOG = {'sphere': sphere, 'stone_cube': stone_cube, 'sword': sword, 'potion': potion, 'house': house,
           'tree': tree}




# ================================================================== PART 2: the style engine
def _rgb(c):
    if isinstance(c, str):
        c = c.lstrip('#')
        return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    return tuple(c[:3])


def _lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def _hsv(c):
    return colorsys.rgb_to_hsv(*[v / 255 for v in c[:3]])


def _from_hsv(h, s, v):
    return tuple(int(round(x * 255)) for x in colorsys.hsv_to_rgb(h % 1.0, max(0.0, min(1.0, s)),
                                                                   max(0.0, min(1.0, v))))


def _mix(a, b, t):
    return tuple(int(round(x + (y - x) * t)) for x, y in zip(a[:3], b[:3]))


_LAB = {}


def _lab(c):
    c = tuple(c[:3])
    if c not in _LAB:
        def lin(u):
            u /= 255
            return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4
        r, g, b = map(lin, c)
        x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.9505
        y = 0.2126 * r + 0.7152 * g + 0.0722 * b
        z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.089

        def f(t):
            return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
        _LAB[c] = (116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z)))
    return _LAB[c]


def _de(a, b):
    la, lb = _lab(a), _lab(b)
    return math.sqrt(sum((p - q) ** 2 for p, q in zip(la, lb)))


# Source tone index (0 line, 1 shadow, 2 dark mid, 3 base, 4 light mid, 5 highlight) -> offset from the style's
# base tone. Fewer tones = neighbouring source tones share a style tone; the order never inverts.
TONE_OFFSETS = {
    5: {1: -2, 2: -1, 3: 0, 4: 1, 5: 2},
    4: {1: -1, 2: -1, 3: 0, 4: 1, 5: 2},
    3: {1: -1, 2: -1, 3: 0, 4: 1, 5: 1},
    2: {1: -1, 2: -1, 3: 0, 4: 0, 5: 0},
    1: {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
}
# with dithering a source tone that falls between two style tones becomes an ordered 50 % mix of both
DITHER_OFFSETS = {
    3: {1: -1, 2: -0.5, 3: 0, 4: 0.5, 5: 1},
    2: {1: -1, 2: -0.5, 3: 0, 4: 0, 5: 0.5},
    4: {1: -1.5, 2: -1, 3: 0, 4: 1, 5: 1.5},
    5: {1: -2, 2: -1, 3: 0, 4: 1, 5: 2},
    1: {1: -0.5, 2: 0, 3: 0, 4: 0, 5: 0.5},
}
BAYER4 = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))

# Limited palettes: ramps dark -> light (hand-picked like pixel artists use them) + the ink (outline) colour.
PALETTES = {
    'pico8': {'ink': '000000', 'ramps': [
        ['5f574f', 'c2c3c7', 'fff1e8'], ['1d2b53', '83769c', 'c2c3c7', 'fff1e8'],
        ['1d2b53', '83769c', '29adff', 'c2c3c7', 'fff1e8'], ['1d2b53', '008751', '00e436', 'ffec27'],
        ['7e2553', 'ff004d', 'ff77a8', 'ffccaa'], ['7e2553', 'ab5236', 'ffa300', 'ffec27', 'fff1e8'],
        ['7e2553', 'ab5236', 'ffa300', 'ffccaa'], ['1d2b53', '7e2553', '83769c', 'ff77a8', 'ffccaa'],
        ['ab5236', 'ffccaa', 'fff1e8'], ['1d2b53', '5f574f', 'c2c3c7']]},
    'sweetie16': {'ink': '1a1c2c', 'ramps': [
        ['5d275d', 'b13e53', 'ef7d57', 'ffcd75', 'f4f4f4'], ['29366f', '257179', '38b764', 'a7f070'],
        ['29366f', '3b5dc9', '41a6f6', '73eff7', 'f4f4f4'], ['333c57', '566c86', '94b0c2', 'f4f4f4'],
        ['29366f', '5d275d', 'b13e53', 'ef7d57'], ['29366f', '257179', '41a6f6', '73eff7'],
        ['b13e53', 'ef7d57', 'ffcd75', 'f4f4f4']]},
    'endesga32': {'ink': '181425', 'ramps': [
        ['3e2731', 'a22633', 'e43b44', 'f6757a', 'e8b796'], ['733e39', 'be4a2f', 'd77643', 'feae34', 'fee761'],
        ['b86f50', 'f77622', 'feae34', 'fee761', 'ffffff'], ['3e2731', '733e39', 'b86f50', 'e4a672', 'ead4aa'],
        ['733e39', 'c28569', 'e8b796', 'ead4aa'], ['193c3e', '265c42', '3e8948', '63c74d', 'fee761'],
        ['262b44', '124e89', '0099db', '2ce8f5', 'ffffff'], ['262b44', '3a4466', '5a6988', '8b9bb4', 'c0cbdc', 'ffffff'],
        ['262b44', '68386c', 'b55088', 'f6757a', 'e8b796'], ['68386c', 'a22633', 'ff0044', 'f6757a']]},
    'nes': {'ink': '000000', 'ramps': [
        ['7c7c7c', 'bcbcbc', 'f8f8f8'], ['0000bc', '0058f8', '6888fc', 'b8b8f8'], ['0000fc', '0078f8', '3cbcfc', 'a4e4fc'],
        ['4428bc', '6844fc', '9878f8', 'd8b8f8'], ['940084', 'd800cc', 'f878f8', 'f8b8f8'],
        ['a80020', 'e40058', 'f85898', 'f8a4c0'], ['a81000', 'f83800', 'f87858', 'f0d0b0'],
        ['881400', 'e45c10', 'fca044', 'fce0a8'], ['503000', 'ac7c00', 'f8b800', 'f8d878'],
        ['007800', '00b800', 'b8f818', 'd8f878'], ['006800', '00a800', '58d854', 'b8f8b8'],
        ['005800', '00a844', '58f898', 'b8f8d8'], ['004058', '008888', '00e8d8', '00fcfc']]},
    'gameboy': {'ink': '081820', 'ramps': [['081820', '346856', '88c070', 'e0f8d0']]},
    'sepia': {'ink': '2b1d12', 'neutral': 0, 'ramps': [
        ['5b3f27', '8a6440', 'b89466', 'dcc191', 'f1e2bb'], ['6a2f1f', '9c4a30', 'c27552', 'dca582', 'f1e2bb'],
        ['3f4a2a', '67704a', '959a6e', 'c7c49a', 'f1e2bb'], ['33454a', '587274', '8aa09a', 'bfc9b4', 'f1e2bb']]},
}
for _p in PALETTES.values():
    _p['ink'] = _rgb(_p['ink'])
    _p['ramps'] = [sorted((_rgb(c) for c in r), key=_lum) for r in _p['ramps']]

NEON_HUES = (0.97, 0.08, 0.15, 0.30, 0.50, 0.58, 0.75, 0.87)
OUTLINES = ('none', 'black', 'dark', 'selective', 'double', 'lit', 'glow', 'broken')


class Style:
    """A drawing style: where the colours come from (palette 'own' = the sprite's own hues rebuilt as ramp5
    ramps, or a limited palette from PALETTES), how many tones a material keeps, the outline mode, and
    special modes ('ink' hatching, 'silhouette', 'neon' glow)."""

    def __init__(self, name, doc, palette='own', tones=5, soft=1.0, outline='selective', sat=1.0, ink=None,
                 paper=None, dither=False, mode=None, adjust=None, identity=False, expand=True, use=''):
        self.name, self.doc, self.palette, self.tones, self.soft = name, doc, palette, tones, soft
        self.outline, self.sat, self.dither, self.mode, self.adjust = outline, sat, dither, mode, adjust
        self.ink = _rgb(ink) if ink else (PALETTES[palette]['ink'] if palette in PALETTES else (28, 24, 32))
        self.paper = _rgb(paper) if paper else (251, 246, 234)
        self.identity, self.expand, self.use = identity, expand, use

    def copy(self, **kw):
        st = Style.__new__(Style)
        st.__dict__.update(self.__dict__)
        for key, v in kw.items():
            if v is not None:
                setattr(st, key, _rgb(v) if key in ('ink', 'paper') else v)
        return st


def _pastel(r):
    """Pastel ramp: lifted, desaturated, lavender-leaning shadows, a soft coloured outline (not near-black)."""
    r = [tuple(c[:3]) for c in r]
    h, s, v = _hsv(r[1])
    r[0] = _from_hsv(h + 0.02, min(1, s * 1.1), v * 0.62)
    return r


def _contrast(r):
    """High contrast: deeper shadow and outline, whiter highlight."""
    r = [tuple(c[:3]) for c in r]
    for i, k in ((0, 0.55), (1, 0.78), (2, 0.9)):
        h, s, v = _hsv(r[i])
        r[i] = _from_hsv(h, min(1, s * 1.08), v * k)
    r[4] = _mix(r[4], (255, 255, 255), 0.12)
    r[5] = _mix(r[5], (255, 255, 255), 0.45)
    return r


def _pastel_base(c):
    h, s, v = _hsv(c)
    return _from_hsv(h, min(s * 0.62, 0.5), 0.66 + 0.3 * v)


STYLES = {}


def _add_style(st):
    STYLES[st.name] = st


for _st in (
    Style('house_soft', 'our delicate 5-tone house style: close mid tones, metals keep contrast, selective '
          'outline', identity=True, use='everything in this skill; GUI art next to the kits'),
    Style('soft_noline', 'house 5 tones without an outline - value and colour carry the form', outline='none',
          identity=True, use='tiles, terrain, big background areas, things behind glass'),
    Style('vanilla', 'Minecraft-like: 5 firmer tones, a little more saturation, the dark tone of the material '
          'as outline everywhere', soft=0.35, sat=1.1, outline='dark', use='resource-pack items and blocks '
          'that sit next to vanilla ones'),
    Style('high_contrast', 'standard ramps stretched: deep shadows, white glints, strong saturation',
          soft=0.0, sat=1.22, outline='dark', adjust=_contrast, use='tiny icons, focal items, rare drops, '
          'anything that must pop on a busy screen'),
    Style('pastel', 'lifted, desaturated colours, lavender shadows, soft coloured outline', tones=4,
          outline='dark', adjust=_pastel, use='cute / cosy servers, seasonal events, kids-friendly menus'),
    Style('cel', 'cartoon cel shading: one lit tone and one shadow tone per material + outline', tones=2,
          soft=0.2, outline='dark', use='mascots, characters, comic-style banners'),
    Style('flat', 'no shading: one tone per material + the outline and inner lines', tones=1, soft=0.3,
          outline='dark', expand=False, use='UI glyphs, map markers, small status icons, logos'),
    Style('sticker', '3 tones and a double outline (dark + light outer ring) - reads on any background',
          tones=3, soft=0.4, outline='double', use='titles and badges over the world, buttons on busy art'),
    Style('lineart_ink', 'engraved map / ink drawing in 2 colours: ink lines on paper, hatching for shade',
          mode='ink', outline='black', ink='2b211c', paper='f2e8d2', expand=False,
          use='quest books, maps, lore pages, blueprints, "sketch" previews'),
    Style('silhouette', 'one flat colour (+ a lighter ground shadow)', mode='silhouette', outline='none',
          ink='2e2a3a', expand=False, use='locked / undiscovered items, "?" slots, shadows of bosses'),
    Style('sepia_old_map', 'aged parchment tones: sepia ramps with faded rust / olive / teal washes, brown ink',
          palette='sepia', tones=4, outline='dark', use='treasure maps, old-world lore, the navigator menu'),
    Style('neon_night', 'dark night bodies with glowing neon edges, a glow halo and glints', mode='neon',
          outline='glow', expand=False, use='night events, cyber / tech servers, Halloween, glowing rares'),
    Style('pico8', 'PICO-8 16 colours, 4 tones per material, black outline where the ramp has no darker step',
          palette='pico8', tones=4, outline='dark', use='retro mini-games, arcade lobbies'),
    Style('sweetie16', 'Sweetie 16 (GrafxKid): warm reds to yellows, cool blues, 4 tones', palette='sweetie16',
          tones=4, outline='dark', use='a friendly retro look with a modern palette'),
    Style('endesga32', 'Endesga 32: rich 32-colour palette, 5 tones, dark outline', palette='endesga32',
          tones=5, outline='dark', use='a whole new pack that needs a coherent rich palette'),
    Style('nes_like', 'NES-like: 3 colours per material from the NES palette, black outline', palette='nes',
          tones=3, outline='black', use='8-bit throwback events, retro arcade menus'),
    Style('gameboy', 'Game Boy: 4 greens for everything, darkest green outline', palette='gameboy', tones=3,
          outline='black', use='nostalgia events, monochrome "handheld" screens'),
    Style('gameboy_dither', 'Game Boy with deliberate ordered dithering for in-between tones',
          palette='gameboy', tones=3, outline='black', dither=True, use='the retro look where a checker '
          'texture is wanted on purpose'),
):
    _add_style(_st)


# ------------------------------------------------------------------ analysis: materials and tone indices
class Analysis:
    """Colours grouped into materials. info[rgb] = (group, tone index 0..5, may be fractional for auto groups);
    groups[g] = {'colours', 'base', 'base_idx', 'ramp' (declared) | None, 'metal', 'flat', 'no_outline'}."""

    def __init__(self):
        self.info, self.groups = {}, {}


def _norm_ramps(ramps):
    """ramps: a kit module name ('modes_hd'), [(name, [colours])], {name: [colours]} or [[colours], ...]."""
    if not ramps:
        return []
    if isinstance(ramps, str):
        import shading
        return [(n, [tuple(c[:3]) for c in r]) for n, r in shading.kit_ramps(ramps)]
    if isinstance(ramps, dict):
        ramps = list(ramps.items())
    out = []
    for i, r in enumerate(ramps):
        if isinstance(r, tuple) and len(r) == 2 and isinstance(r[0], str):
            out.append((r[0], [_rgb(c) for c in r[1]]))
        else:
            out.append((f'ramp{i}', [_rgb(c) for c in r]))
    return out


def _colours(images):
    """Pixel count per colour, count of inner pixels (not on a silhouette edge) per colour, adjacency counts."""
    from collections import Counter
    cnt, inner, adj = Counter(), Counter(), Counter()
    for im in images:
        im = im.convert('RGBA')
        W, H = im.size
        px = im.load()
        for y in range(H):
            for x in range(W):
                c = px[x, y]
                if c[3] < 128:
                    continue
                cnt[c[:3]] += 1
                if all(0 <= x + dx < W and 0 <= y + dy < H and px[x + dx, y + dy][3] >= 128 for dx, dy in N4):
                    inner[c[:3]] += 1
                for dx, dy in ((1, 0), (0, 1)):
                    if x + dx < W and y + dy < H:
                        d = px[x + dx, y + dy]
                        if d[3] >= 128 and d[:3] != c[:3]:
                            adj[tuple(sorted((c[:3], d[:3])))] += 1
    return cnt, inner, adj


def _compatible(a, b):
    ha, sa, va = _hsv(a)
    hb, sb, vb = _hsv(b)
    na, nb = sa < 0.16 or va < 0.14, sb < 0.16 or vb < 0.14
    if na and nb:
        return True
    if na != nb:
        return min(sa, sb) < 0.16 and max(sa, sb) < 0.28 and abs(_lum(a) - _lum(b)) < 70
    dh = abs(ha - hb)
    dh = min(dh, 1 - dh)
    return dh < 0.055 and abs(sa - sb) < 0.45


def _auto_indices(cols, cnt):
    order = sorted(cols, key=_lum)
    if _lum(order[-1]) < 30:
        return {c: 0 for c in order}, order[-1]
    idx = {}
    rest = order
    total = sum(cnt[c] for c in order)
    if len(order) >= 3:
        d = order[0]
        tail = order[1:]
        acc, med = 0, _lum(tail[-1])
        for c in tail:
            acc += cnt[c]
            if acc >= sum(cnt[q] for q in tail) / 2:
                med = _lum(c)
                break
        if _lum(d) < 0.6 * med and cnt[d] < 0.4 * total:
            idx[d] = 0
            rest = tail
    acc, base = 0, rest[-1]
    tot = sum(cnt[c] for c in rest)
    for c in rest:
        acc += cnt[c]
        if acc >= tot / 2:
            base = c
            break
    Lb = _lum(base)
    darks = [c for c in rest if _lum(c) < Lb]
    lights = [c for c in rest if _lum(c) > Lb]
    idx[base] = 3
    for c in rest:
        if c != base and _lum(c) == Lb:
            idx[c] = 3
    if len(darks) == 1:
        idx[darks[0]] = 2 if _lum(darks[0]) > 0.72 * Lb else 1
    else:
        for i, c in enumerate(darks):
            idx[c] = 1 + i / (len(darks) - 1)
    if len(lights) == 1:
        c = lights[0]
        idx[c] = 4 if (_lum(c) - Lb) / max(1, 255 - Lb) < 0.5 else 5
    else:
        for i, c in enumerate(lights):
            idx[c] = 4 + i / (len(lights) - 1)
    return idx, base


def analyse(images, ramps=None, no_outline=()):
    """Group the colours of one or more images into materials and give each colour a tone index.
    ramps: declared ramps (see _norm_ramps) - a colour from a 6-colour ramp (outline + 5 tones, shading.ramp5)
    is that material at that index; other colours are grouped by hue and adjacency (union-find) and indexed
    by value inside the group. no_outline: group names (ramp names) or colours never outlined (ground
    shadows)."""
    cnt, inner, adj = _colours(images)
    an = Analysis()
    known = {}
    for name, r in _norm_ramps(ramps):
        if len(r) == 6:
            for i, c in enumerate(r):
                known.setdefault(c, (name, i))
    groups = {}
    for c in cnt:
        if c in known:
            g, i = known[c]
            groups.setdefault(g, {'colours': [], 'ramp': dict(_norm_ramps(ramps))[g]})['colours'].append(c)
            an.info[c] = (g, i)
    rest = [c for c in cnt if c not in known]
    parent = {c: c for c in rest}

    def find(c):
        while parent[c] != c:
            parent[c] = parent[parent[c]]
            c = parent[c]
        return c
    for (a, b), n in sorted(adj.items(), key=lambda kv: -kv[1]):
        if a in parent and b in parent and _compatible(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb
    auto = {}
    for c in rest:
        auto.setdefault(find(c), []).append(c)
    for n, cols in enumerate(sorted(auto.values(), key=lambda cs: -sum(cnt[c] for c in cs))):
        g = f'auto{n}'
        idx, _ = _auto_indices(cols, cnt)
        groups[g] = {'colours': cols, 'ramp': None}
        for c in cols:
            an.info[c] = (g, idx[c])
    no = set(no_outline or ())
    for g, G in groups.items():
        cols = G['colours']
        used, used_in = {}, {}
        for c in cols:
            i = an.info[c][1]
            used[i] = used.get(i, 0) + cnt[c]
            used_in[i] = used_in.get(i, 0) + inner[c]
        fills = {i: n for i, n in used.items() if i >= 1}
        if G['ramp']:                                   # base: tone 3 unless the material barely uses it
            body = {i: n for i, n in used_in.items() if i >= 1 and n} or fills   # edges hold the outline tones
            tot = sum(body.values()) or 1
            G['base_idx'] = 3 if body.get(3, 0) >= 0.08 * tot or not body else max(body, key=body.get)
            G['base'] = G['ramp'][G['base_idx']]
            ln = [_lum(G['ramp'][i]) for i in range(1, 6)]
        else:
            G['base_idx'] = 3
            G['base'] = next((c for c in cols if an.info[c][1] == 3), cols[0])
            ln = [_lum(c) for c in cols if an.info[c][1] >= 1] or [0]
        G['metal'] = (max(ln) - min(ln)) / 255 > 0.53 and len(fills) >= 4
        G['flat'] = len({round(i) for i in fills}) < 3 and sum(fills.values()) >= 12
        G['count'] = sum(used.values())
        G['no_outline'] = g in no or any(c in no for c in cols)
        G['lines'] = used.get(0, 0)
        G['tones'] = sorted(fills)
        lum_of = {}
        for c in cols:
            i = an.info[c][1]
            if i >= 1:
                lum_of.setdefault(i, []).append(_lum(G['ramp'][int(i)] if G['ramp'] else c))
        G['lum_of'] = sorted((i, sum(v) / len(v)) for i, v in lum_of.items())
    an.groups = groups
    return an


# ------------------------------------------------------------------ targets: what each material becomes
class Target:
    """A material in a style: its colour list, a function from source tone index to a position in it, and
    the outline / lit outline / light / line colours."""

    def __init__(self, cols, pos, outline, lit_outline, light, line, lo=0, glow=None, halo=None):
        self.cols, self.pos_of, self.outline, self.lit_outline = cols, pos, outline, lit_outline
        self.light, self.line, self.lo = light, line, lo
        self.glow_lit = cols[-1]                         # 'glow' outline: bright rim + a darker halo outside
        self.glow = glow or light
        self.halo = halo or cols[min(len(cols) - 1, max(lo, 2))]

    def colour(self, idx, x=0, y=0, dither=False):
        if idx <= 0:
            return self.line
        p = self.pos_of(idx)
        n = len(self.cols)
        p = max(self.lo, min(n - 1, p))
        f = p - math.floor(p)
        if f < 1e-6:
            return self.cols[int(p)]
        if dither:
            th = (BAYER4[y % 4][x % 4] + 0.5) / 16
            return self.cols[min(n - 1, int(math.floor(p)) + (1 if f > th else 0))]
        return self.cols[int(round(p))]


def _offset(st, idx, base_idx):
    """Offset of a source index (fractional allowed) from the material's base, in style tones."""
    table = (DITHER_OFFSETS if st.dither else TONE_OFFSETS)[st.tones]
    i = 3 + (idx - base_idx)
    i = max(1.0, min(5.0, i))
    lo, hi = int(math.floor(i)), int(math.ceil(i))
    if lo == hi:
        return table[lo]
    a, b = table[lo], table[hi]
    v = a + (b - a) * (i - lo)
    return v if st.dither else (math.floor(v + 0.5) if v < 0 else math.ceil(v - 0.5))


def _target(G, st):
    base_idx = G['base_idx']
    if st.palette == 'own':
        if st.identity and G['ramp']:
            cols = list(G['ramp'])
        else:
            B = G['base']
            plain = G['no_outline']                    # ground shadows keep their value in every style
            if st.adjust is _pastel and not plain:
                B = _pastel_base(B)
            h, s, v = _hsv(B)
            B = _from_hsv(h, s * (1 if plain else st.sat), v)
            soft = 0.0 if (G['metal'] and st.soft >= 0.3) else st.soft
            if st.identity:
                soft = 0.0 if G['metal'] else 1.0
            cols = [tuple(c) for c in ramp5('#%02x%02x%02x' % B, soft=soft)]
            if st.adjust and not plain:
                cols = st.adjust(cols)

        def pos(idx):
            return 3 + _offset(st, idx, base_idx)
        return Target(cols, pos, cols[0], cols[1], cols[4], cols[0], lo=1, glow=cols[4], halo=cols[2])
    pal = PALETTES[st.palette]
    tones = [c for c in G['colours']]
    best, score = None, None
    offs = [_offset(st, i, base_idx) for i in G['tones']] or [0]
    need = int(math.ceil(max(offs) - min(offs))) + 1
    cand = pal['ramps']
    if 'neutral' in pal and _hsv(G['base'])[1] < 0.16:
        cand = [pal['ramps'][pal['neutral']]]                   # greys become the palette's main ramp
    for r in cand:
        sc = 0
        for c in tones:
            sc += min(_de(c, q) for q in r)
        sc /= max(1, len(tones))
        sc += 2 * min(_de(G['base'], q) for q in r) + 14 * max(0, need - len(r))
        if score is None or sc < score:
            best, score = r, sc
    r = best
    n = len(r)
    Lb0 = _lum(G['base'])
    near = [i for i in range(n) if abs(_lum(r[i]) - Lb0) <= 35] or list(range(n))   # value first, then hue
    anchor = min(near, key=lambda i: _de(G['base'], r[i]) + 0.25 * abs(_lab(G['base'])[0] - _lab(r[i])[0]))
    lo_need, hi_need = max(-1, min(offs)), min(1, max(offs))   # make room for the neighbours of the base;
    if n >= 1 + hi_need - lo_need:                              # the extremes may collapse into the ends
        anchor = max(anchor, int(math.ceil(-lo_need)))
        anchor = min(anchor, n - 1 - int(math.ceil(hi_need)))
    anchor = int(max(0, min(n - 1, anchor)))

    lums = [_lum(c) for c in r]
    Lb = _src_lum(G, base_idx)
    table = (DITHER_OFFSETS if st.dither else TONE_OFFSETS)[st.tones]
    lo_off, hi_off = min(table.values()), max(table.values())

    def pos(idx):
        """Half the tone index (keeps faces apart), half the real value difference measured on the palette
        ramp (a soft material does not jump across a coarse palette's big value steps)."""
        d_i = _offset(st, idx, base_idx)
        d_v = _ramp_pos(lums, lums[anchor] + (_src_lum(G, idx) - Lb) * 1.15) - anchor
        d = max(lo_off, min(hi_off, (d_i + d_v) / 2))
        if not st.dither:
            d = math.copysign(math.floor(abs(d) + 0.55), d)
        return anchor + d
    used = [max(0, min(n - 1, pos(i))) for i in G['tones']] or [anchor]
    mn = int(math.floor(min(used)))
    ink = pal['ink']
    if st.outline == 'black':
        outline = ink
    else:
        outline = r[mn - 1] if mn >= 1 and _lum(r[mn - 1]) < 0.72 * _lum(r[mn]) else ink
        if mn >= 2 and _lum(r[0]) < 0.72 * _lum(r[mn]):
            outline = r[0]
    lit_outline = r[mn - 1] if mn >= 1 else outline
    light = r[min(n - 1, anchor + 1)]
    return Target(r, pos, outline, lit_outline, light, outline, halo=r[max(0, anchor - 1)])


def _src_lum(G, idx):
    """Source luminance of a tone index in a material (interpolated; synthesised tones extrapolate)."""
    pts = G['lum_of'] or [(3, _lum(G['base']))]
    if len(pts) == 1:
        return pts[0][1] * (1 + 0.12 * (idx - pts[0][0]))
    for (i0, l0), (i1, l1) in zip(pts, pts[1:]):
        if i0 <= idx <= i1:
            return l0 + (l1 - l0) * (idx - i0) / ((i1 - i0) or 1)
    (i0, l0), (i1, l1) = (pts[0], pts[1]) if idx < pts[0][0] else (pts[-2], pts[-1])
    return l0 + (l1 - l0) * (idx - i0) / ((i1 - i0) or 1)


def _ramp_pos(lums, L):
    """Fractional position of luminance L on a ramp sorted dark -> light."""
    n = len(lums)
    if n == 1:
        return 0.0
    if L <= lums[0]:
        return (L - lums[0]) / max(1.0, lums[1] - lums[0])
    for j in range(n - 1):
        if L <= lums[j + 1]:
            return j + (L - lums[j]) / max(1.0, lums[j + 1] - lums[j])
    return n - 1 + (L - lums[-1]) / max(1.0, lums[-1] - lums[-2])


def _neon_target(G, st):
    h, s, v = _hsv(G['base'])
    if s < 0.15:
        h = 0.5
    h = min(NEON_HUES, key=lambda q: min(abs(q - h), 1 - abs(q - h)))
    body = [_from_hsv(h, 0.55, 0.08), _from_hsv(h, 0.55, 0.1), _from_hsv(h, 0.6, 0.16), _from_hsv(h, 0.6, 0.24),
            _from_hsv(h, 0.62, 0.35), _from_hsv(h, 0.4, 1.0)]
    base_idx = G['base_idx']

    def pos(idx):
        return max(1, min(5, 3 + (idx - base_idx)))
    t = Target(body, pos, _from_hsv(h, 0.85, 1.0), _from_hsv(h, 0.35, 1.0), body[4], _from_hsv(h, 0.8, 0.78), lo=1,
               glow=_from_hsv(h, 0.85, 1.0), halo=_from_hsv(h, 0.9, 0.42))
    t.glow_lit = _from_hsv(h, 0.35, 1.0)
    return t


def targets(an, st):
    out = {}
    for g, G in an.groups.items():
        if st.mode == 'neon':
            out[g] = _neon_target(G, st)
        else:
            out[g] = _target(G, st)
    return out


# ------------------------------------------------------------------ stylize
def _most(seq):
    """Most common item; ties go to the one seen first (deterministic, unlike max over a set of strings)."""
    return max(seq, key=lambda v: (seq.count(v), -seq.index(v)))


def _exterior(solid, W, H):
    """Transparent pixels connected to the border (holes inside a sprite are not exterior)."""
    ext = set()
    stack = [(x, y) for x in range(-1, W + 1) for y in (-1, H)] + [(x, y) for y in range(H) for x in (-1, W)]
    seen = set(stack)
    while stack:
        p = stack.pop()
        ext.add(p)
        for dx, dy in N4:
            q = (p[0] + dx, p[1] + dy)
            if -1 <= q[0] <= W and -1 <= q[1] <= H and q not in seen and q not in solid:
                seen.add(q)
                stack.append(q)
    return ext


def _ink_value(G, i):
    """Engraving value of a pixel: its tone inside the material, shifted by how dark the material is (a dark
    wood is hatched even where it is lit, a cream wall stays paper). >= 3 paper, 2..3 light hatch, 1..2 dense
    hatch, < 1 solid ink."""
    m = max(-2.0, min(0.5, (_lum(G['base']) - 150) / 60))
    return 3 + (i - G['base_idx']) + m


def _hatch(v, x, y, k):
    """Ink or paper for an engraving value v at (x, y): k=1 horizontal lines on the shadow side only (calm at
    16 px), k=2 diagonal hatching for the half-tones and cross-hatching for the shadows."""
    if v >= 3:
        return False
    if v < 1:
        return True
    if k == 1:                                          # 16 px: only the shadow side is hatched
        return v < 2 and y % 2 == 0
    if v >= 2:
        return (x + y) % 3 == 0
    return (x + y) % 3 == 0 or (x - y) % 3 == 0


def _stylize_one(img, st, an, tg, origin=(0, 0), k=1, add_missing=True, outer=True):
    """Restyle one RGBA image with an analysis + targets. Returns (image, (dx, dy)): dx, dy <= 0 when the
    canvas had to grow for an outline outside the silhouette."""
    img = img.convert('RGBA')
    W0, H0 = img.size
    pad = 2
    W, H = W0 + 2 * pad, H0 + 2 * pad
    src = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    src.paste(img, (pad, pad))
    spx = src.load()
    solid = {(x, y) for y in range(H) for x in range(W) if spx[x, y][3] >= 128}
    ox, oy = origin[0] - pad, origin[1] - pad
    out = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    if not solid:
        return img.copy(), (0, 0)
    opx = out.load()
    info = an.info
    ext = _exterior(solid, W, H)
    border = [(x, y) for x in range(W0) for y in (0, H0 - 1)] + [(x, y) for y in range(H0) for x in (0, W0 - 1)]
    full_bleed = sum(1 for (x, y) in border if (x + pad, y + pad) in solid) >= 0.9 * len(border)
    if full_bleed:                                      # a scene / tile: the canvas edge is not a silhouette
        ext = {q for q in ext if pad <= q[0] < pad + W0 and pad <= q[1] < pad + H0}
        outer = False
    ring = {p for p in solid if any((p[0] + dx, p[1] + dy) in ext for dx, dy in N4)}

    def grp(p):
        return info.get(spx[p][:3], (None, 3))

    def lit_face(p, inside=True):
        if inside:
            up = (p[0], p[1] - 1) in ext or (p[0] - 1, p[1]) in ext
            dn = (p[0], p[1] + 1) in ext or (p[0] + 1, p[1]) in ext
        else:
            dn = (p[0], p[1] + 1) in solid or (p[0] + 1, p[1]) in solid
            up = (p[0], p[1] - 1) in solid or (p[0] - 1, p[1]) in solid
            return dn and not up
        return up and not dn

    # does the source already have an outline? (ring darker than what is inside it)
    ol = tot = 0
    for p in ring:
        g, i = grp(p)
        if g is None or an.groups[g]['no_outline']:
            continue
        tot += 1
        if an.groups[g]['ramp']:                        # declared ramp: outline tones are 0 and 1
            ol += i <= 1
            continue
        inn = [q for q in ((p[0] + dx, p[1] + dy) for dx, dy in N4) if q in solid and q not in ring]
        if i == 0 or (inn and _lum(spx[p]) < 0.82 * min(_lum(spx[q]) for q in inn)):
            ol += 1
    has_ol = tot > 0 and ol >= 0.5 * tot

    # expansion: flat materials get lit / shaded edges and a highlight synthesised
    expand = {}
    if st.expand and st.tones >= 3 and st.mode is None:
        for p in solid:
            g, i = grp(p)
            if g is None or not an.groups[g]['flat'] or an.groups[g]['no_outline'] or i < 1 or round(i) != 3:
                continue
            if has_ol and p in ring:
                continue

            def same(q):
                gq, iq = grp(q) if q in solid else (None, 0)
                return gq == g and iq >= 1 and not (has_ol and q in ring)
            up = not same((p[0], p[1] - 1)) or not same((p[0] - 1, p[1]))
            dn = not same((p[0], p[1] + 1)) or not same((p[0] + 1, p[1]))
            if up and not dn:
                expand[p] = 4
            elif dn and not up:
                expand[p] = 2
        lit = sorted((p for p, v in expand.items() if v == 4), key=lambda p: (p[0] + p[1], p[1]))
        for g in sorted({grp(p)[0] for p in lit}):                  # a highlight just inside the top-left lit edge
            cand = [p for p in lit if grp(p)[0] == g and (p[0] + 1, p[1] + 1) in solid
                    and grp((p[0] + 1, p[1] + 1))[0] == g]
            if cand:
                q = (cand[0][0] + 1, cand[0][1] + 1)
                if q not in expand:
                    expand[q] = 5

    def fill_colour(p, g, i):
        T = tg[g]
        G = an.groups[g]
        X, Y = p[0] + ox, p[1] + oy
        if st.mode == 'silhouette':
            return _mix(st.ink, (255, 255, 255), 0.22) if G['no_outline'] else st.ink
        if st.mode == 'ink':
            if i <= 0:
                return st.ink
            if G['no_outline']:
                return st.ink if (Y % 2 == 0 and i <= 1.5) else st.paper
            return st.ink if _hatch(_ink_value(G, i), X, Y, k) else st.paper
        if st.mode == 'neon' and G['no_outline']:
            return (18, 12, 30)
        return T.colour(i, X, Y, st.dither)

    for p in solid:
        g, i = grp(p)
        if g is None:
            opx[p] = spx[p]
            continue
        i = expand.get(p, i)
        opx[p] = fill_colour(p, g, i) + (255,)

    if st.tones == 1 or st.mode == 'ink':              # keep 1 px dark features (grooves, cracks, seams)
        for p in solid - ring:
            g, i = grp(p)
            if g is None or an.groups[g]['no_outline'] or i <= 0 or i > (2 if st.mode == 'ink' else 1.5):
                continue
            L = _lum(spx[p])
            ratio = 0.86 if st.mode == 'ink' else 0.78
            for a_, b_ in (((-1, 0), (1, 0)), ((0, -1), (0, 1)), ((-1, -1), (1, 1)), ((1, -1), (-1, 1))):
                q1, q2 = (p[0] + a_[0], p[1] + a_[1]), (p[0] + b_[0], p[1] + b_[1])
                if q1 in solid and q2 in solid and L < ratio * min(_lum(spx[q1]), _lum(spx[q2])):
                    opx[p] = (st.ink if st.mode == 'ink' else tg[g].line) + (255,)
                    break

    if st.mode == 'ink':                                # ink lines where two light materials meet
        for p in solid:
            g, i = grp(p)
            if g is None or i <= 0 or an.groups[g]['no_outline'] or _ink_value(an.groups[g], i) < 2:
                continue
            for q in ((p[0] + 1, p[1]), (p[0], p[1] + 1)):
                if q in solid:
                    gq, iq = grp(q)
                    if gq != g and iq > 0 and gq is not None and not an.groups[gq]['no_outline'] \
                            and _ink_value(an.groups[gq], iq) >= 2:
                        opx[p] = st.ink + (255,)
                        break

    def area(p):
        inn = [q for q in ((p[0] + dx, p[1] + dy) for dx, dy in N4) if q in solid and q not in ring]
        gs = [grp(q)[0] for q in inn if grp(q)[0] is not None and not an.groups[grp(q)[0]]['no_outline']]
        if not gs:
            g = grp(p)[0]
            return g, inn
        return _most(gs), inn

    def ring_colour(p, g, inside, inn):
        T = tg[g]
        mode = st.outline
        if mode == 'none':
            if inn:
                cs = [opx[q][:3] for q in inn]
                return _most(cs)
            return opx[p][:3] if inside else None
        if mode == 'black' or st.mode == 'ink':
            return st.ink
        if st.mode == 'silhouette':
            return st.ink
        if mode == 'glow' or st.mode == 'neon':
            return T.glow_lit if lit_face(p, inside) else T.glow
        if mode in ('dark', 'double'):
            return T.outline
        if mode == 'selective':
            return T.lit_outline if lit_face(p, inside) else T.outline
        if mode == 'lit':
            return T.light if lit_face(p, inside) else T.outline
        if mode == 'broken':
            nx = sum(dx for dx, dy in N8 if ((p[0] + dx, p[1] + dy) in ext) == inside)
            ny = sum(dy for dx, dy in N8 if ((p[0] + dx, p[1] + dy) in ext) == inside)
            if not inside:
                nx, ny = -nx, -ny
            nn = math.hypot(nx, ny) or 1
            if (-nx - ny) / nn / math.sqrt(2) > 0.8:
                if inside and inn:
                    return opx[inn[0]][:3]
                return None
            return T.outline
        return T.outline

    new_ring = set()
    recoloured = set()
    if has_ol:
        for p in ring:
            g, i = grp(p)
            if g is None:
                continue
            if an.groups[g]['no_outline']:
                continue
            ga, inn = area(p)
            if an.groups[ga]['no_outline']:
                continue
            c = ring_colour(p, ga, True, inn)
            if c is not None:
                opx[p] = c + (255,)
                recoloured.add(p)
    elif add_missing and st.outline != 'none' and st.mode != 'silhouette':
        for q in sorted(edge_ring(solid)):
            if q not in ext:
                continue
            inn = [p for p in ((q[0] + dx, q[1] + dy) for dx, dy in N4) if p in solid]
            gs = [grp(p)[0] for p in inn if grp(p)[0] is not None and not an.groups[grp(p)[0]]['no_outline']]
            if not gs:
                continue
            g = _most(gs)
            c = ring_colour(q, g, False, [])
            if c is not None:
                opx[q] = c + (255,)
                new_ring.add(q)
    if outer and (st.outline in ('double', 'glow') or st.mode == 'neon'):
        _outer_ring(out, an, tg, st, src)
    if (new_ring or recoloured) and st.outline != 'none':    # clean doubles in the (re)drawn outline only
        _ring_perfect(out, new_ring | recoloured)
    if (st.palette != 'own' and st.mode is None) or st.mode == 'neon':   # a coarse palette can merge two lines into an
        lines = {tg[g].line + (255,) for g in an.groups}    # L-corner: clean those inner lines too
        _ring_perfect(out, {p for p in solid - ring if opx[p] in lines})
    bb = out.getbbox()
    x0 = min(pad, bb[0]) if bb else pad
    y0 = min(pad, bb[1]) if bb else pad
    x1 = max(pad + W0, bb[2]) if bb else pad + W0
    y1 = max(pad + H0, bb[3]) if bb else pad + H0
    res = out.crop((x0, y0, x1, y1))
    return res, (x0 - pad, y0 - pad)


def _ring_perfect(img, ring):
    """shading.pixel_perfect restricted to the outline pixels: L-corners where outlines of one colour meet
    are removed; every other pixel of the same colours (inner lines) is left alone."""
    px = img.load()
    keep = {(x, y): px[x, y] for y in range(img.height) for x in range(img.width) if (x, y) not in ring}
    pixel_perfect(img, only={px[p] for p in ring})
    for p, c in keep.items():
        if px[p] != c:
            px[p] = c


def _outer_ring(out, an, tg, st, src):
    """The second ring outside the silhouette: a light paper ring (double) or a dark neon halo (glow)."""
    opx, spx = out.load(), src.load()
    W, H = out.size
    solid = {(x, y) for y in range(H) for x in range(W) if opx[x, y][3]}
    ext = _exterior(solid, W, H)
    for q in sorted(edge_ring(solid)):
        if q not in ext or not (0 <= q[0] < W and 0 <= q[1] < H):
            continue
        gs = []
        for dx, dy in N4 + tuple(N8):
            p = (q[0] + dx, q[1] + dy)
            for r in (0, 1):
                pp = (p[0] + dx * r, p[1] + dy * r)
                if 0 <= pp[0] < W and 0 <= pp[1] < H and spx[pp][3] >= 128:
                    g = an.info.get(spx[pp][:3], (None,))[0]
                    if g is not None:
                        gs.append(g)
        gs = [g for g in gs if not an.groups[g]['no_outline']]
        if not gs:
            continue
        g = _most(gs)
        if st.mode == 'neon' or st.outline == 'glow':
            c = tg[g].halo
        else:
            c = st.paper
        opx[q] = c + (255,)


def _style(style, **kw):
    st = STYLES[style] if isinstance(style, str) else style
    over = {key: kw.get(key) for key in ('outline', 'dither', 'tones', 'ink', 'paper') if kw.get(key) is not None}
    return st.copy(**over) if over else st


def stylize(img, style, ramps=None, no_outline=(), k=1, analysis=None, **opts):
    """Restyle ANY finished RGBA sprite. style: a name from STYLES or a Style. ramps: the kit's declared ramps
    (a module name like 'modes_hd', or [(name, ramp)]) for an exact material / tone mapping; without them the
    colours are grouped by hue + adjacency. opts: outline (one of OUTLINES), dither, tones, ink, paper.
    Returns a new RGBA image (no semi-transparent pixels); when an outline had to be added outside a
    silhouette touching the border the canvas grows and img.info['offset'] says by how much."""
    st = _style(style, **opts)
    an = analysis or analyse([img], ramps, no_outline)
    tg = targets(an, st)
    res, off = _stylize_one(img, st, an, tg, k=k)
    res.info['offset'] = off
    return res


def stylize_parts(items, style, ramps=None, no_outline=(), k=1, **opts):
    """Restyle a parts list (modes.Parts items) consistently: one analysis over all parts, each part restyled
    on its own (its own outline kept where it had one, never added inside the picture), the second ring of
    'double' / 'glow' outlines added once round the whole picture as a part 'outline_outer'."""
    st = _style(style, **opts)
    an = analyse([it['sprite'] for it in items], ramps, no_outline)
    tg = targets(an, st)
    out = []
    for it in items:
        sp, (dx, dy) = _stylize_one(it['sprite'], st, an, tg, origin=(it['x'], it['y']), k=k, add_missing=False,
                                    outer=False)
        out.append(dict(it, sprite=sp, x=it['x'] + dx, y=it['y'] + dy))
    if out and (st.outline in ('double', 'glow') or st.mode == 'neon'):
        x0 = min(it['x'] for it in items) - 2
        y0 = min(it['y'] for it in items) - 2
        x1 = max(it['x'] + it['sprite'].width for it in items) + 2
        y1 = max(it['y'] + it['sprite'].height for it in items) + 2
        src = Image.new('RGBA', (x1 - x0, y1 - y0), (0, 0, 0, 0))
        for it in items:
            src.alpha_composite(it['sprite'], (it['x'] - x0, it['y'] - y0))
        sty = Image.new('RGBA', src.size, (0, 0, 0, 0))
        for it in out:
            sty.alpha_composite(it['sprite'], (it['x'] - x0, it['y'] - y0))
        ring = sty.copy()
        _outer_ring(ring, an, tg, st, src)
        diff = Image.new('RGBA', src.size, (0, 0, 0, 0))
        rp, sp_, dp = ring.load(), sty.load(), diff.load()
        for y in range(src.height):
            for x in range(src.width):
                if rp[x, y] != sp_[x, y]:
                    dp[x, y] = rp[x, y]
        bb = diff.getbbox()
        if bb:
            out.insert(0, {'name': 'outline_outer', 'sprite': diff.crop(bb), 'x': x0 + bb[0], 'y': y0 + bb[1]})
    return out


# ================================================================== API: render / parts / charts
STYLE_OPTS = ('outline', 'dither', 'tones', 'ink', 'paper')
NO_OUTLINE = ('SHADOW',)                    # ground shadows: never outlined, mapped to the style's shadow tones
CHART_STYLES = ('house_soft', 'soft_noline', 'vanilla', 'high_contrast', 'pastel', 'cel', 'flat', 'sticker',
                'lineart_ink', 'silhouette', 'sepia_old_map', 'neon_night', 'pico8', 'sweetie16', 'endesga32',
                'nes_like', 'gameboy', 'gameboy_dither')


def kit_ramps():
    """The 6-colour ramps this module declares (name, [rgb]) - the exact material map for its own objects."""
    out, seen = [], set()
    for n, v in globals().items():
        if isinstance(v, list) and len(v) == 6 and all(isinstance(c, tuple) and len(c) >= 3 for c in v):
            key = tuple(tuple(c[:3]) for c in v)
            if key not in seen:
                seen.add(key)
                out.append((n, list(key)))
    return out


def _split(opts):
    so = {key: opts.pop(key) for key in list(opts) if key in STYLE_OPTS}
    return opts, so


def parts(name, k=1, style=None, **opts):
    """Parts of a catalog object bottom -> top (dicts: name, sprite, x, y), restyled when style is given.
    Positions are in the object's canvas; a style with an outer ring may shift them to stay >= 0."""
    obj, so = _split(dict(opts))
    Pt = CATALOG[name](k=k, **obj)
    items = Pt.items
    if style:
        items = stylize_parts(items, style, ramps=kit_ramps(), no_outline=NO_OUTLINE, k=k, **so)
        mx = min(0, min(it['x'] for it in items))
        my = min(0, min(it['y'] for it in items))
        if mx or my:
            items = [dict(it, x=it['x'] - mx, y=it['y'] - my) for it in items]
    return items


def _canvas_size(items):
    return (max(it['x'] + it['sprite'].width for it in items), max(it['y'] + it['sprite'].height for it in items))


def render(name, k=1, style=None, **opts):
    """A catalog object as one tight RGBA image (composed from its parts), optionally in a style."""
    items = parts(name, k, style, **opts)
    canvas = Image.new('RGBA', _canvas_size(items), (0, 0, 0, 0))
    compose(items, canvas)
    return canvas.crop(canvas.getbbox())


def _label(img, x, y, text, colour=(226, 222, 210, 255)):
    from pixfont import draw_text
    draw_text(img, x, y, text.replace('_', ' '), colour)


def _text_w(text):
    from pixfont import text_width
    return text_width(text.replace('_', ' '))


BG = (52, 54, 64, 255)
CELL = (138, 138, 142, 255)                 # neutral mid grey (the slot grey family)


def chart(out, k=1, styles=CHART_STYLES, names=None, scale=None):
    """Rows = objects, columns = styles; every cell the object enlarged (x4, HD x3) on a neutral grey."""
    names = names or list(CATALOG)
    scale = scale or (4 if k == 1 else 3)
    ims = {(n, s): render(n, k, s) for n in names for s in styles}
    cw = max(im.width for im in ims.values()) * scale + 10
    ch_ = {n: max(ims[(n, s)].height for s in styles) * scale + 10 for n in names}
    lw = max(_text_w(n) for n in names) + 14
    W = lw + len(styles) * (cw + 4) + 6
    H = 22 + sum(ch_[n] + 4 for n in names) + 4
    sheet = Image.new('RGBA', (W, H), BG)
    for j, s in enumerate(styles):
        x = lw + j * (cw + 4)
        _label(sheet, x + (cw - _text_w(s)) // 2, 8, s)
    y = 22
    for n in names:
        _label(sheet, 6, y + ch_[n] // 2 - 4, n)
        for j, s in enumerate(styles):
            x = lw + j * (cw + 4)
            sheet.paste(Image.new('RGBA', (cw, ch_[n]), CELL), (x, y))
            im = ims[(n, s)]
            big = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
            sheet.alpha_composite(big, (x + (cw - big.width) // 2, y + (ch_[n] - big.height) // 2))
        y += ch_[n] + 4
    sheet.save(out)
    return out


def styles_sheet(img, out, ramps=None, scale=None, styles=CHART_STYLES):
    """One sprite (any kit) in every style, labelled."""
    img = img.convert('RGBA')
    scale = scale or max(2, min(8, 96 // max(img.size)))
    cells = []
    for s in ('source',) + tuple(styles):
        im = img if s == 'source' else stylize(img, s, ramps=ramps)
        big = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
        w = max(big.width, _text_w(s)) + 10
        cell = Image.new('RGBA', (w, big.height + 22), BG)
        cell.paste(Image.new('RGBA', (w, big.height + 8), CELL), (0, 0))
        cell.alpha_composite(big, ((w - big.width) // 2, 4))
        _label(cell, (w - _text_w(s)) // 2, big.height + 11, s)
        cells.append(cell)
    cols = 7
    rows = [cells[i:i + cols] for i in range(0, len(cells), cols)]
    W = max(sum(c.width + 4 for c in r) for r in rows) + 4
    H = sum(max(c.height for c in r) + 4 for r in rows) + 4
    sheet = Image.new('RGBA', (W, H), BG)
    y = 4
    for r in rows:
        x = 4
        for c in r:
            sheet.paste(c, (x, y))
            x += c.width + 4
        y += max(c.height for c in r) + 4
    sheet.save(out)
    return out


def outlines_sheet(out, k=1, names=('sphere', 'sword', 'house'), base='vanilla'):
    """The outline modes side by side on a few objects (style `base`, outline overridden)."""
    scale = 4 if k == 1 else 3
    ims = {(n, m): render(n, k, base, outline=m) for n in names for m in OUTLINES}
    cw = max(im.width for im in ims.values()) * scale + 10
    ch_ = max(im.height for im in ims.values()) * scale + 10
    W = len(OUTLINES) * (cw + 4) + 4
    H = 22 + len(names) * (ch_ + 4) + 4
    sheet = Image.new('RGBA', (W, H), BG)
    for j, m in enumerate(OUTLINES):
        _label(sheet, 4 + j * (cw + 4) + (cw - _text_w(m)) // 2, 8, m)
    for i, n in enumerate(names):
        for j, m in enumerate(OUTLINES):
            x, y = 4 + j * (cw + 4), 22 + i * (ch_ + 4)
            sheet.paste(Image.new('RGBA', (cw, ch_), CELL), (x, y))
            im = ims[(n, m)]
            big = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
            sheet.alpha_composite(big, (x + (cw - big.width) // 2, y + (ch_ - big.height) // 2))
    sheet.save(out)
    return out


def style_ramps(name, k=1, style=None, **opts):
    """The colours each material of a catalog object takes in a style, as [(material, [colours])] - pass them
    to shading.check(ramps=...) so a multi-material picture is judged per material (like --kit)."""
    if not style:
        return kit_ramps()
    obj, so = _split(dict(opts))
    items = CATALOG[name](k=k, **obj).items
    st = _style(style, **so)
    an = analyse([it['sprite'] for it in items], kit_ramps(), NO_OUTLINE)
    tg = targets(an, st)
    out = []
    for g, T in tg.items():
        cols = list(T.cols) + [T.outline, T.lit_outline, T.light, T.line, T.glow_lit, T.glow, T.halo]
        if st.mode in ('ink', 'silhouette'):
            cols = [st.ink, st.paper, _mix(st.ink, (255, 255, 255), 0.22)]
        if st.outline == 'double':
            cols.append(st.paper)
        out.append((g, list(dict.fromkeys(tuple(c[:3]) for c in cols))))
    return out


def check(name, k=1, style=None, path=None, quiet=False, **opts):
    """Render a catalog object (in a style) and run shading.check on it with the style's material ramps."""
    import shading
    import tempfile
    path = path or os.path.join(tempfile.mkdtemp(), f'{name}_{style or "house"}_k{k}.png')
    render(name, k, style, **opts).save(path)
    return shading.check(path, ramps=style_ramps(name, k, style, **opts), quiet=quiet)


def export_parts(name, out_dir, k=1, style=None, **opts):
    """PNG per part + layers.json + _sheet.png (layers.save_parts), the composite, a x4 zoom and a layered
    .aseprite; checks that the parts rebuild the picture."""
    items = parts(name, k, style, **opts)
    size = _canvas_size(items)
    meta = layers.save_parts(items, out_dir, size)
    canvas = Image.new('RGBA', size, (0, 0, 0, 0))
    compose(items, canvas)
    rebuilt = layers.compose(meta, out_dir)
    assert rebuilt.tobytes() == canvas.tobytes(), 'parts do not rebuild the picture'
    tag = f'{name}{"_hd" if k == 2 else ""}{"_" + style if style else ""}'
    canvas.save(os.path.join(out_dir, f'{tag}.png'))
    canvas.resize((size[0] * 4, size[1] * 4), Image.NEAREST).save(os.path.join(out_dir, f'{tag}_x4.png'))
    layers.write_aseprite(os.path.join(out_dir, f'{tag}.aseprite'), items, size)
    return meta


def _flag(a, name, default=None):
    if name in a:
        i = a.index(name)
        v = a[i + 1] if i + 1 < len(a) else default
        del a[i:i + 2]
        return v
    return default


def main(argv):
    a = list(argv)
    hd = '--hd' in a
    if hd:
        a.remove('--hd')
    k = 2 if hd else 1
    style = _flag(a, '--style')
    kit = _flag(a, '--kit')
    outline = _flag(a, '--outline')
    dither = True if '--dither' in a else None
    if dither:
        a.remove('--dither')
    no_shadow = '--no-shadow' in a
    if no_shadow:
        a.remove('--no-shadow')
    if not a or a[0] in ('-h', '--help'):
        print(__doc__)
        return 0
    cmd = a[0]
    so = {key: v for key, v in (('outline', outline), ('dither', dither)) if v is not None}
    if cmd == 'list':
        print('objects:', ', '.join(CATALOG))
        print('styles: ')
        for n, st in STYLES.items():
            print(f'  {n:15s} {st.doc}')
        print('outline modes:', ', '.join(OUTLINES))
    elif cmd == 'chart' and len(a) == 2:
        chart(a[1], k)
        print('chart ->', a[1])
    elif cmd == 'render' and len(a) == 3:
        render(a[1], k, style, shadow=not no_shadow, **so).save(a[2])
        print(a[1], '->', a[2])
    elif cmd == 'parts' and len(a) == 3:
        meta = export_parts(a[1], a[2], k, style, shadow=not no_shadow, **so)
        print(f'{a[1]}: {len(meta["layers"])} parts -> {a[2]}/')
    elif cmd == 'stylize' and len(a) == 4:
        stylize(Image.open(a[1]), a[3], ramps=kit, k=k, **so).save(a[2])
        print(a[1], '->', a[2], f'({a[3]})')
    elif cmd == 'styles' and len(a) == 3:
        styles_sheet(Image.open(a[1]), a[2], ramps=kit)
        print('styles ->', a[2])
    elif cmd == 'check' and len(a) in (2, 3):
        res = check(a[1], k, style, path=a[2] if len(a) == 3 else None, shadow=not no_shadow, **so)
        return 1 if res['warnings'] else 0
    elif cmd == 'outlines' and len(a) == 2:
        outlines_sheet(a[1], k)
        print('outlines ->', a[1])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
