#!/usr/bin/env python3
"""Materials library: a five-tone ramp and a seamless tile for every block material, at two densities.

k=1 is vanilla GUI density (a block face is 16x16), k=2 is "HD" (32x32 for the same block). HD tiles are
drawn natively with more detail (wider bevels, 2 px joints, grain with knots, rivets, facets, pointed leaves,
fish-scale roof tiles, glints) - never upscaled. Every tile is built from LAYERS (base, structure, details,
overlays such as moss, ore, patina, cracks, blossoms), so parts() hands them out as modes.Parts items and an
artist can hide the moss or the ore. 207 materials in 10 families (`materials.py list`):
woods (planks, logs, log tops, stripped logs of 11 woods), stones (26 + polished / cut / bricks / tiles),
soils, metals (copper in 4 oxidation stages, raw ore blocks), gem blocks, ores (in stone or deepslate),
fabrics (16 wool dyes, leather, velvet, canvas, carpet), others (glass, liquids, gel, hay, bookshelf,
leaves with holes...), building (roof shingles / tiles / slate / thatch, iron bars, ladder), dyed blocks
(16 concrete, 16 terracotta). references/materials.md says how each one is drawn.

Shading follows references/texture-shading.md and references/pixel-art-craft.md: one ramp per material from
shading.ramp5 (index 0 outline, 1 shadow, 2 dark mid, 3 base, 4 light mid, 5 highlight; matte materials
soft, metals and gems contrasty), light from the top-left on every feature inside the tile (raised things:
lit top-left rim, dark bottom-right rim, cast shadow down-right; recesses: shadowed top-left wall, lit far
wall), clusters instead of noise, 1 px lines kept pixel-perfect across the wrap, no gradients, no
dithering, no semi-transparent pixels, the tile's average flat, every coordinate wrapping (seamless).

    from materials import render, parts, fill, fill_parts, ramp, tile, circle, CATALOG
    img = render('oak_planks', k=2)                    # 32x32 RGBA tile
    fill(canvas, rrect(0, 0, 47, 23, 4), 'cobblestone', k=1)   # texture + lit top/left + dark bottom/right + outline
    ramp('gold_block')                                 # [outline, shadow, dark, base, light, highlight] RGBA

    python3 materials.py chart OUT.png [--hd]          every tile, grouped by family, x4 (HD x3) + a 1:1 repeat,
                                                       plus fill() on a rounded slab and a circle
    python3 materials.py render NAME OUT.png [--hd]    one tile (--seed N, --base deepslate for ores,
                                                       --color '#hex' for a one-ramp material, --frame N)
    python3 materials.py parts NAME OUT_DIR [--hd]     its layers: PNGs + layers.json + _sheet.png + .aseprite
                                                       (slab:NAME / disc:NAME = fill() on a shape, as parts)
    python3 materials.py list                          the catalog by family
"""
import math
import os
import random
import sys
import zlib
from collections import Counter

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kitchen import _r5, rrect, N4                      # noqa: E402
from modes import Parts                                 # noqa: E402
import layers                                           # noqa: E402

O, SH, DK, BS, LT, HI = range(6)                       # tone indices into a ramp
N8 = ((-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1))

# ------------------------------------------------------------------ ramps
RAMPS = {}


def _ramp(key, hexc, soft=0.8, **kw):
    """Declare a ramp: RAMPS[key] and a module global R_<KEY> (so `shading.py check --kit materials` sees it)."""
    r = _r5(hexc, soft=soft, **kw)
    RAMPS[key] = r
    globals()['R_' + key.upper()] = r
    return r


def custom_ramp(hexc, soft=0.8, **kw):
    return _r5(hexc, soft=soft, **kw)


# woods: planks (matte, soft) and bark
for _k, _p, _b in (('oak', '#b48a52', '#6e5434'), ('spruce', '#7c5834', '#45301e'),
                   ('birch', '#d6c482', '#e4e2da'), ('jungle', '#b27a50', '#5e4a26'),
                   ('acacia', '#bc6232', '#6c6660'), ('dark_oak', '#56391f', '#3c2c1c'),
                   ('mangrove', '#7c3530', '#584434'), ('cherry', '#e2b2a6', '#40262e'),
                   ('crimson', '#7a3650', '#5a1c2c'), ('warped', '#2e7068', '#2e3a4e'),
                   ('bamboo', '#cdb24c', '#7a9a30')):
    _ramp(_k + '_planks', _p, soft=0.7)
    _ramp(_k + '_bark', _b, soft=0.6)
_ramp('birch_mark', '#3e3a36', soft=0.4)
_ramp('jungle_moss', '#5c8c2c', soft=0.6)
_ramp('crimson_glow', '#e0384a', soft=0.2)
_ramp('warped_glow', '#2ed0b0', soft=0.2)
_ramp('bamboo_node', '#a8b84a', soft=0.6)
# stones
for _k, _h, _s in (('stone', '#808284', 0.8), ('cobble', '#7c7c7e', 0.7), ('stone_brick', '#7e7c7c', 0.8),
                   ('granite', '#9e6c58', 0.7), ('diorite', '#cfcdca', 0.8), ('andesite', '#878988', 0.8),
                   ('deepslate', '#50505a', 0.7), ('tuff', '#6e6f64', 0.8), ('calcite', '#dcdcd4', 0.7),
                   ('blackstone', '#332d36', 0.6), ('sandstone', '#dacb92', 0.9), ('red_sandstone', '#ba6226', 0.8),
                   ('brick', '#9a4e3c', 0.7), ('mortar', '#aaa69c', 0.9), ('mud_brick', '#94724e', 0.8),
                   ('mud_mortar', '#5e4836', 0.8), ('prismarine', '#5aa08e', 0.6), ('prismarine2', '#4c8ca4', 0.6),
                   ('end_stone', '#dedca2', 0.9), ('purpur', '#aa7eaa', 0.8), ('quartz', '#e8e2d8', 0.9),
                   ('obsidian', '#24182e', 0.3), ('obsidian_glint', '#6c4c9e', 0.3), ('netherrack', '#723030', 0.6),
                   ('nether_brick', '#40202a', 0.6), ('basalt', '#4c4c54', 0.7), ('moss', '#567c34', 0.6)):
    _ramp(_k, _h, soft=_s)
# soils
for _k, _h, _s in (('dirt', '#7c5a3a', 0.8), ('grass', '#62a03c', 0.6), ('podzol', '#5c4222', 0.7),
                   ('needle', '#a46c2c', 0.6), ('mycelium', '#76627a', 0.8), ('spore', '#b0a0b4', 0.6),
                   ('sand', '#dccf9c', 0.9), ('red_sand', '#ba662c', 0.8), ('gravel', '#807876', 0.6),
                   ('gravel2', '#8c8e92', 0.6), ('clay', '#a0a6b2', 0.9), ('mud', '#3e3a3a', 0.6),
                   ('snow', '#e6ecf4', 0.7), ('ice', '#8eb6ec', 0.5), ('packed_ice', '#7ca0e2', 0.5),
                   ('soul_sand', '#523e32', 0.6), ('soul', '#7ad8e0', 0.3)):
    _ramp(_k, _h, soft=_s)
# metals (contrasty) and raw ore blocks
for _k, _h, _s in (('iron', '#c2c8ce', 0.0), ('gold', '#e8b42a', 0.0), ('copper', '#c46c4a', 0.0),
                   ('exposed_copper', '#a8806a', 0.2), ('weathered_copper', '#7a8a6a', 0.4),
                   ('patina', '#4ea68c', 0.5), ('netherite', '#46404a', 0.35), ('raw_iron', '#cca68a', 0.3),
                   ('raw_gold', '#dca232', 0.2), ('raw_copper', '#b8623c', 0.3)):
    _ramp(_k, _h, soft=_s)
# gems and ores
for _k, _h, _s in (('diamond', '#48d4cc', 0.15), ('emerald', '#24b85c', 0.15), ('amethyst', '#8c5cc8', 0.25),
                   ('lapis', '#2a48ae', 0.3), ('redstone', '#c41c12', 0.2), ('coal', '#2e2e34', 0.3),
                   ('iron_ore', '#d8b090', 0.3), ('gold_ore', '#f0c430', 0.1), ('copper_ore', '#d07a48', 0.2)):
    _ramp(_k, _h, soft=_s)
# fabrics: 16 wool dyes + others
WOOL_DYES = (('white', '#e2e6e6'), ('light_gray', '#9a9a96'), ('gray', '#4c5256'), ('black', '#26262c'),
             ('brown', '#7c5232'), ('red', '#a8302a'), ('orange', '#ec7a1c'), ('yellow', '#f2c834'),
             ('lime', '#76b82a'), ('green', '#566e20'), ('cyan', '#188e92'), ('light_blue', '#3aa8d2'),
             ('blue', '#3a44a2'), ('purple', '#7c36aa'), ('magenta', '#b64cac'), ('pink', '#e688a6'))
for _k, _h in WOOL_DYES:
    _ramp(_k + '_wool', _h, soft=0.45 if _k in ('blue', 'purple', 'magenta', 'pink', 'red') else 0.7)
for _k, _h, _s in (('leather', '#8c5632', 0.8), ('velvet', '#8c1e36', 0.6), ('canvas', '#c8b48c', 0.9),
                   ('carpet_red', '#a42c2c', 0.7), ('carpet_gold', '#d8a63a', 0.4), ('carpet_navy', '#2c366a', 0.7)):
    _ramp(_k, _h, soft=_s)
# others
for _k, _h, _s, _kw in (('glass', '#bcdde8', 0.3, {}), ('tinted_glass', '#3c3244', 0.4, {}),
                        ('water', '#3a66c6', 0.4, {}),
                        ('lava', '#e8641a', 0.0, {'hue_dark': -0.03, 'hue_light': 0.07}),
                        ('slime', '#7ac452', 0.4, {}), ('honey', '#e8a222', 0.3, {}),
                        ('hay', '#d8b030', 0.6, {}), ('hay_tie', '#7c3a24', 0.6, {}),
                        ('book_red', '#a02c2c', 0.5, {}), ('book_blue', '#2c4a8c', 0.5, {}),
                        ('book_green', '#3c7a3a', 0.5, {}), ('book_brown', '#7a4c2c', 0.5, {}),
                        ('book_purple', '#6a3a7c', 0.5, {}), ('book_cream', '#d8c8a0', 0.7, {}),
                        ('terracotta', '#a05c42', 0.9, {}), ('parchment', '#e2d2a8', 0.9, {}),
                        ('bone', '#ded6bc', 0.6, {}), ('oak_leaves', '#4a8a2c', 0.5, {}),
                        ('birch_leaves', '#7aa83c', 0.5, {}), ('spruce_leaves', '#3a6642', 0.5, {}),
                        ('cherry_leaves', '#e8a2c2', 0.5, {}), ('blossom_core', '#f4d24a', 0.3, {})):
    _ramp(_k, _h, soft=_s, **_kw)
BOOKS = ('book_red', 'book_blue', 'book_green', 'book_brown', 'book_purple', 'book_cream')
# extras: building materials, more soils and leaves, dyed blocks
for _k, _h, _s in (('farmland', '#5a3c26', 0.7), ('path', '#9c7c4e', 0.8), ('root', '#b48c5c', 0.6),
                   ('red_nether_brick', '#621a20', 0.6), ('thatch', '#b89648', 0.6), ('roof_clay', '#a84a36', 0.6),
                   ('roof_slate', '#4c5462', 0.6), ('shingle', '#8c6642', 0.7), ('glowstone', '#e8b44a', 0.15),
                   ('jungle_leaves', '#3c8a26', 0.5), ('acacia_leaves', '#6c9a2e', 0.5),
                   ('dark_oak_leaves', '#386c22', 0.5), ('mangrove_leaves', '#5a8e2c', 0.5),
                   ('azalea_leaves', '#5e8c36', 0.5), ('azalea_flower', '#c45ab4', 0.4)):
    _ramp(_k, _h, soft=_s)


def _mix(a, b, t):
    a, b = [int(a[i:i + 2], 16) for i in (1, 3, 5)], [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return '#%02x%02x%02x' % tuple(round(x + (y - x) * t) for x, y in zip(a, b))


for _k, _h in WOOL_DYES:
    _ramp(_k + '_concrete', _h, soft=0.75)
    _t = _mix(_h, '#a05c42', 0.45)
    _ramp(_k + '_terracotta', _mix(_t, '#000000', 0.12), soft=0.75)


def _c(i):
    return max(0, min(5, i))


# ------------------------------------------------------------------ the tile canvas
def _wd(a, b, S):
    d = abs(a - b) % S
    return min(d, S - d)


def _sw(d, S):
    """Signed wrapped difference in [-S/2, S/2)."""
    return ((d + S / 2) % S) - S / 2


def _seed(*parts):
    return zlib.crc32(':'.join(str(p) for p in parts).encode())


class Tile:
    """A seamless S x S tile (S = 16k) drawn in named layers; every coordinate wraps round the edges."""

    def __init__(self, k=1, seed=0, ramps=()):
        self.k, self.S, self.seed = k, 16 * k, seed
        self.rnd = random.Random(seed)
        self.layers = []
        self.ramps = list(ramps)
        self._lut = None
        self.layer('base')

    def add_ramps(self, *rs):
        self.ramps.extend(rs)
        self._lut = None

    @property
    def lut(self):
        if self._lut is None:
            self._lut = {}
            for R in reversed(self.ramps):
                for i, c in enumerate(R):
                    self._lut[c] = (R, i)
        return self._lut

    def layer(self, name):
        for n, d in self.layers:
            if n == name:
                self.cur = d
                return d
        self.cur = {}
        self.layers.append((name, self.cur))
        return self.cur

    def w(self, x, y):
        return (int(x) % self.S, int(y) % self.S)

    def put(self, x, y, c):
        p = self.w(x, y)
        if c is None:
            self.cur.pop(p, None)
        else:
            self.cur[p] = c

    def get(self, x, y):
        p = self.w(x, y)
        for _, d in reversed(self.layers):
            if p in d:
                return d[p]
        return None

    def shift(self, x, y, d, lo=1, hi=5):
        """Move the colour under (x, y) d steps along its own ramp (into the current layer)."""
        c = self.get(x, y)
        if c is None or c not in self.lut:
            return
        R, i = self.lut[c]
        self.put(x, y, R[max(lo, min(hi, i + d))])

    def tone(self, x, y):
        c = self.get(x, y)
        return self.lut.get(c, (None, None))[1] if c else None

    def ramp_at(self, x, y):
        c = self.get(x, y)
        return self.lut.get(c, (None, None))[0] if c else None

    def composed(self):
        out = {}
        for _, d in self.layers:
            out.update(d)
        return out

    def owner(self, p):
        for _, d in reversed(self.layers):
            if p in d:
                return d
        return None

    def rect(self, x0, y0, w, h, c):
        for y in range(y0, y0 + h):
            for x in range(x0, x0 + w):
                self.put(x, y, c)

    def transpose(self):
        """Swap x and y in every layer: top edges become left edges, so the top-left light still holds."""
        for _, d in self.layers:
            items = list(d.items())
            d.clear()
            d.update({(y, x): c for (x, y), c in items})

    def image(self, hide=()):
        im = Image.new('RGBA', (self.S, self.S), (0, 0, 0, 0))
        px = im.load()
        for n, d in self.layers:
            if n in hide:
                continue
            for p, c in d.items():
                px[p] = c
        return im


# ------------------------------------------------------------------ shared helpers
def field(t, freqs, off=0, aniso=(1, 1)):
    """Seamless value noise: for every (f, a) a random lattice of 2f x 2f cells per tile (wrapping, offset
    at random so octaves do not line up), smoothstep-interpolated, weighted a; rank-normalised to 0..1 so
    thresholds are area fractions. aniso=(ax, ay) scales the cell count along x / y: (0.34, 1) gives
    horizontally stretched shapes (strata, slate), (1, 0.34) vertical ones (fibres)."""
    S = t.S
    rnd = random.Random(t.seed * 31 + 7 + off)
    vals = {(x, y): 0.0 for y in range(S) for x in range(S)}
    for f, a in freqs:
        gx, gy = max(1, round(2 * f * aniso[0])), max(1, round(2 * f * aniso[1]))
        lat = [[rnd.random() for _ in range(gx)] for _ in range(gy)]
        ox, oy = rnd.uniform(0, S), rnd.uniform(0, S)
        for y in range(S):
            fy = ((y + oy) % S) / S * gy
            j0 = int(fy)
            ty = fy - j0
            ty = ty * ty * (3 - 2 * ty)
            r0, r1 = lat[j0 % gy], lat[(j0 + 1) % gy]
            for x in range(S):
                fx = ((x + ox) % S) / S * gx
                i0 = int(fx)
                tx = fx - i0
                tx = tx * tx * (3 - 2 * tx)
                i1 = (i0 + 1) % gx
                i0 %= gx
                top = r0[i0] + (r0[i1] - r0[i0]) * tx
                bot = r1[i0] + (r1[i1] - r1[i0]) * tx
                vals[(x, y)] += a * (top + (bot - top) * ty)
    order = sorted(vals, key=lambda p: (vals[p], p))
    n = len(order)
    return {p: i / n for i, p in enumerate(order)}


def voronoi(t, grid, jitter=0.85, sx=1.0, sy=1.0, off=0):
    """Cells on the torus from a jittered grid of seeds: (seeds, owner, d1, d2) - d2 - d1 small = a joint."""
    S = t.S
    rnd = random.Random(t.seed * 17 + 3 + off)
    gx, gy = grid if isinstance(grid, tuple) else (grid, grid)
    pts = [((i + 0.5 + rnd.uniform(-jitter, jitter) / 2) * S / gx, (j + 0.5 + rnd.uniform(-jitter, jitter) / 2) * S / gy)
           for j in range(gy) for i in range(gx)]
    own, d1, d2 = {}, {}, {}
    for y in range(S):
        for x in range(S):
            ds = sorted(((_wd(x + 0.5, px, S) * sx) ** 2 + (_wd(y + 0.5, py, S) * sy) ** 2, i)
                        for i, (px, py) in enumerate(pts))
            own[(x, y)] = ds[0][1]
            d1[(x, y)], d2[(x, y)] = math.sqrt(ds[0][0]), math.sqrt(ds[1][0])
    return pts, own, d1, d2


def spots(t, n, min_d, avoid=(), tries=600, rnd=None):
    """Up to n points on the torus at least min_d apart (and from `avoid`)."""
    S, rnd = t.S, rnd or t.rnd
    taken, out = list(avoid), []
    for _ in range(tries):
        if len(out) >= n:
            break
        p = (rnd.randrange(S), rnd.randrange(S))
        if all(_wd(p[0], q[0], S) ** 2 + _wd(p[1], q[1], S) ** 2 >= min_d ** 2 for q in taken):
            taken.append(p)
            out.append(p)
    return out


def blob(rnd, n, wide=1.0, tall=1.0):
    """A compact random cluster of n pixels round (0, 0)."""
    pts = {(0, 0)}
    while len(pts) < n:
        cand = sorted({(x + dx, y + dy) for x, y in pts for dx, dy in N4} - pts)
        pts.add(min(cand, key=lambda q: (q[0] / wide) ** 2 + (q[1] / tall) ** 2 + rnd.random() * 1.8))
    return pts


def lump(t, pts, ox, oy, R, base=BS, rim=1, hi=0, cast=0, shade_in=None):
    """A raised cluster lit from the top-left: lit rim on the top / left, dark rim on the bottom / right,
    `hi` highlight pixels at the top-left, and `cast` = shadow steps on what lies under it down-right."""
    s = set(pts)
    for (x, y) in s:
        tl = (x - 1, y) not in s or (x, y - 1) not in s
        br = (x + 1, y) not in s or (x, y + 1) not in s
        i = base
        if tl and not br:
            i = base + rim
        elif br and not tl:
            i = base - rim
        if shade_in:
            i += shade_in(x, y)
        t.put(ox + x, oy + y, R[_c(i)])
    if hi:
        for (x, y) in sorted(s, key=lambda p: (p[0] + p[1], p[1]))[:hi]:
            if (x + 1, y) in s or (x, y + 1) in s:
                t.put(ox + x, oy + y, R[_c(base + 2)])
    if cast:
        for (x, y) in s:
            for q in ((x + 1, y), (x, y + 1), (x + 1, y + 1)):
                if q not in s:
                    t.shift(ox + q[0], oy + q[1], -cast)


def pit(t, pts, ox, oy, R, base=BS):
    """A recess lit from the top-left: shadowed top-left wall, dark floor, lit far (bottom-right) wall."""
    s = set(pts)
    for (x, y) in s:
        tl = (x - 1, y) not in s or (x, y - 1) not in s
        br = (x + 1, y) not in s or (x, y + 1) not in s
        i = base - 2 if tl else base if br else base - 1
        t.put(ox + x, oy + y, R[_c(i)])


def streak(t, x, y, n, c, dx=1, dy=0):
    for i in range(n):
        t.put(x + dx * i, y + dy * i, c)


def wander(t, x, y, n, c, main=(0, 1), side=0.35, rnd=None, lip=None):
    """A 1 px crack / furrow: steps along `main`, sometimes diagonally - never an L-corner (no doubles).
    lip = tone shift for the pixel on its lit far side (right of a vertical crack, below a horizontal one)."""
    rnd = rnd or t.rnd
    pts = []
    mx, my = main
    for _ in range(n):
        pts.append((x, y))
        if rnd.random() < side:
            s = rnd.choice((-1, 1))
            x, y = x + mx + (s if mx == 0 else 0), y + my + (s if my == 0 else 0)
        else:
            x, y = x + mx, y + my
    S = t.S
    if lip:
        ps = {t.w(*p) for p in pts}
        for (px, py) in pts:
            q = (px + 1, py) if mx == 0 else (px, py + 1)
            if t.w(*q) not in ps:
                t.shift(*q, lip)
    for p in pts:
        t.put(*p, c)
    return pts


def clean(t, keep=(), passes=2):
    """Orphan pixels (no same-coloured 8-neighbour) take the commonest colour of their 4 neighbours -
    texture is clusters, not noise. Colours in `keep` (glints) stay."""
    keep = set(keep)
    for _ in range(passes):
        comp = t.composed()
        changes = {}
        for p, c in comp.items():
            if c in keep:
                continue
            x, y = p
            if any(comp.get(t.w(x + dx, y + dy)) == c for dx, dy in N8):
                continue
            n4 = [comp.get(t.w(x + dx, y + dy)) for dx, dy in N4]
            n4 = [q for q in n4 if q is not None]
            if n4:
                changes[p] = Counter(n4).most_common(1)[0][0]
        if not changes:
            break
        idx = {id(d): i for i, (_, d) in enumerate(t.layers)}
        for p, c in changes.items():
            d = t.owner(p)
            if d is None:
                continue
            x, y = p
            src = [t.owner(t.w(x + dx, y + dy)) for dx, dy in N4 if comp.get(t.w(x + dx, y + dy)) == c]
            src = [q for q in src if q is not None and idx[id(q)] > idx[id(d)]]
            (src[0] if src else d)[p] = c


def fix_doubles(img, only, box=None, passes=6):
    """Like shading.pixel_perfect, but it cannot oscillate: each L-corner pixel of a 1 px line takes the
    commonest neighbouring colour that does not leave a double at that spot (a configuration that keeps
    flipping between two doubles is settled). Returns the number of pixels changed."""
    from shading import _is_double
    W, H = img.size
    px = img.load()
    x0, y0, x1, y1 = box or (0, 0, W, H)
    total = 0
    for _ in range(passes):
        n = 0
        for y in range(y0, y1):
            for x in range(x0, x1):
                c = px[x, y]
                if c not in only or not _is_double(px, W, H, x, y):
                    continue
                nb = Counter(px[x + dx, y + dy] for dx, dy in N8 if 0 <= x + dx < W and 0 <= y + dy < H
                             and px[x + dx, y + dy] != c)
                for cand, _ in nb.most_common():
                    px[x, y] = cand
                    if not _is_double(px, W, H, x, y):
                        break
                else:
                    px[x, y] = c
                    continue
                n += 1
        total += n
        if not n:
            break
    return total


def perfect(t, only=None):
    """Clean 1 px dark lines (shading.pixel_perfect) on the tile as it repeats: the tile is laid 3x3, the
    middle copy is cleaned with its real neighbours round it, the fixes go back into the layer that owns
    each pixel. only = colours to clean (default: every tone of the tile's ramps)."""
    S = t.S
    comp = t.composed()
    im = t.image()
    big = Image.new('RGBA', (3 * S, 3 * S), (0, 0, 0, 0))
    for j in range(3):
        for i in range(3):
            big.paste(im, (i * S, j * S))
    only = only or {c for R in t.ramps for c in R}
    if not fix_doubles(big, only, box=(S, S, 2 * S, 2 * S)):
        return
    px = big.load()
    idx = {id(d): i for i, (_, d) in enumerate(t.layers)}
    for y in range(S):
        for x in range(S):
            c = px[S + x, S + y]
            if c != comp.get((x, y)):
                if c[3] == 0:
                    for _, d in t.layers:
                        d.pop((x, y), None)
                    continue
                d = t.owner((x, y))
                if d is None:
                    continue
                # the new colour came from a neighbour: if that neighbour lives on a higher layer (moss over
                # stone), the fix goes there, so hiding that layer hides the fix too
                src = [t.owner(t.w(x + dx, y + dy)) for dx, dy in N8 if comp.get(t.w(x + dx, y + dy)) == c]
                src = [q for q in src if q is not None and idx[id(q)] > idx[id(d)]]
                (src[0] if src else d)[(x, y)] = c


def bevel_cell(t, x0, y0, w, h, R, base=BS, rim=1, joint=SH, k=1, lit_corner=None):
    """A flat block face (brick, panel, tile) of w x h at (x0, y0) incl. its joint on the right and bottom:
    lit top row and left column, dark bottom row and right column inside, the joint in `joint` tone.
    At k=2 the joint is 2 px: shadowed upper / left row (cast by the face above), then the lighter recess."""
    jw = k
    fw, fh = w - jw, h - jw
    for y in range(fh):
        for x in range(fw):
            i = base
            if y < k and x < fw - y - 1 and not (x >= fw - k):
                i = base + rim
            elif x < k and y < fh - x - 1:
                i = base + rim
            elif y >= fh - k or x >= fw - k:
                i = base - rim
            t.put(x0 + x, y0 + y, R[_c(i)])
    if lit_corner:
        t.put(x0, y0, R[_c(base + 2)])
    for y in range(h):
        for x in range(w):
            if x >= fw or y >= fh:
                if k == 1:
                    c = R[joint] if isinstance(joint, int) else joint
                else:
                    inner = (x == fw and y < fh) or (y == fh and x < fw) or (x == fw and y == fh)
                    c = R[_c(joint - 1)] if inner else R[joint]
                t.put(x0 + x, y0 + y, c)


# ------------------------------------------------------------------ woods
def g_planks(t, R, grain=1.0, light_grain=0.2, knots=1, seam=None, wavy=0.35, vertical=False, nodes=False,
             dots=0, joints=(0.18, 0.68, 0.40, 0.88)):
    """Four boards: lit top edge, dark seam at the bottom, grain streaks along the board, one staggered end
    joint per board (dark gap, lit end grain after it); HD adds a second lit row, a rounded dark lower edge,
    wavy long grain, knots and nail holes."""
    S, k, rnd = t.S, t.k, t.rnd
    hb = S // 4
    seam_c = R[seam if seam is not None else (O if k == 2 else SH)]
    t.layer('boards')
    for b in range(4):
        y0 = b * hb
        for j in range(hb):
            c = R[LT] if j == 0 else seam_c if j == hb - 1 else R[DK] if (k == 2 and j == hb - 2) else R[BS]
            for x in range(S):
                t.put(x, y0 + j, c)
        if k == 2:
            x = rnd.randrange(S)
            for _ in range(3):
                n = rnd.randint(4, 9)
                streak(t, x, y0 + 1, n, R[LT])
                x += n + rnd.randint(3, 8)
            x = rnd.randrange(S)                             # the lit edge catches a few highlights
            for _ in range(2):
                n = rnd.randint(2, 4)
                streak(t, x, y0, n, R[HI])
                x += n + rnd.randint(6, 12)
            x = rnd.randrange(S)
            for _ in range(2):
                n = rnd.randint(3, 7)
                streak(t, x, y0 + hb - 2, n, R[BS])
                x += n + rnd.randint(5, 10)
    t.layer('grain')
    rows = list(range(1, hb - 1)) if k == 1 else list(range(2, hb - 2))
    for b in range(4):
        y0 = b * hb
        n = max(1, round((2.5 if k == 1 else 5) * grain))
        x = rnd.randrange(S)
        for _ in range(n):
            L = rnd.randint(2, 4) if k == 1 else rnd.randint(4, 11)
            r = rnd.choice(rows)
            c = R[LT] if rnd.random() < light_grain and r != rows[-1] else R[DK]
            xx = x
            for i in range(L):
                t.put(xx, y0 + r, R[SH] if (k == 2 and c == R[DK] and L >= 8 and L // 3 <= i < L // 3 + 2) else c)
                xx += 1
                if k == 2 and i == L // 2 and rnd.random() < wavy:
                    r2 = r + rnd.choice((-1, 1))
                    if r2 in rows:
                        r = r2
            x += L + rnd.randint(1, 4 if k == 1 else 6)
        if k == 2 and dots:
            for _ in range(dots):
                dx = rnd.randrange(S)
                streak(t, dx, y0 + rnd.choice(rows[1:-1]), 2, R[SH])
    t.layer('joints')
    for b in range(4):
        y0 = b * hb
        jx = int(joints[b % len(joints)] * S + rnd.randint(-k, k))
        for j in range(hb - 1):
            t.put(jx, y0 + j, seam_c if k == 2 else R[SH])
            if 1 <= j <= hb - 2 - (k == 2):
                t.put(jx + 1, y0 + j, R[LT])
                t.put(jx - 1, y0 + j, R[DK])
        if nodes:                                          # bamboo: a lit ring beside every node
            t.put(jx + 2, y0 + 1, R[LT])
        if k == 2 and not nodes:
            for nx, ny in ((jx - 3, y0 + 2), (jx + 3, y0 + hb - 4)):
                t.put(nx, ny, R[O])
                t.put(nx + 1, ny, R[SH])
                t.put(nx, ny + 1, R[SH])
                t.put(nx + 1, ny + 1, R[LT])
    if k == 2 and knots:
        t.layer('knots')
        for i in range(knots):
            b = (1 + 2 * i) % 4
            kx, ky = rnd.randrange(S), b * hb + 3
            for dx in range(-4, 5):                        # grain bending round the knot
                t.put(kx + dx, ky - 1 if abs(dx) < 3 else ky - 0, R[DK] if abs(dx) > 1 else R[BS])
                t.put(kx + dx, ky + 2 if abs(dx) < 3 else ky + 1, R[DK] if abs(dx) > 1 else R[BS])
            for dx, dy, c in ((-1, 0, R[DK]), (0, 0, R[SH]), (1, 0, R[SH]), (2, 0, R[DK]), (-1, 1, R[DK]),
                              (0, 1, R[O]), (1, 1, R[SH]), (2, 1, R[LT]), (-2, 0, R[LT]), (-2, 1, R[BS])):
                t.put(kx + dx, ky + dy, c)
    clean(t, keep=(R[LT],))
    if vertical:
        t.transpose()


def g_bark(t, R, furrows=4, amp=1, plates=0.25, streaks=0.5, deep=None, light=0.5, overlay=None, R2=None):
    """Vertical bark: furrows wander down the trunk (only diagonal steps, so the 1 px lines stay clean);
    the ridge left of a furrow turns away (dark), the ridge right of it faces the light (lit); horizontal
    plate cracks break the ridges; short vertical streaks texture them."""
    S, k, rnd = t.S, t.k, t.rnd
    deep = R[deep if deep is not None else (O if k == 2 else SH)]
    t.layer('bark')
    for y in range(S):
        for x in range(S):
            t.put(x, y, R[BS])
    nf = furrows * (1 if k == 1 else 2) - (1 if k == 2 else 0)
    paths = []
    for i in range(nf):
        x0 = (i + 0.5 + rnd.uniform(-0.25, 0.25)) * S / nf
        f, ph, a = rnd.choice((1, 2)), rnd.uniform(0, 2 * math.pi), amp * k * rnd.uniform(0.6, 1.0)
        xs = [round(x0 + a * math.sin(2 * math.pi * f * y / S + ph)) for y in range(S)]
        for y in range(S):                                 # no jumps over 1 px between rows
            d = xs[y] - xs[y - 1]
            if abs(d) > 1:
                xs[y] = xs[y - 1] + (1 if d > 0 else -1)
        paths.append(xs)
    t.layer('streaks')
    for _ in range(int(S * S * 0.035 * streaks)):
        x, y = rnd.randrange(S), rnd.randrange(S)
        n = rnd.randint(2, 3) if k == 1 else rnd.randint(3, 6)
        c = R[LT] if rnd.random() < light * 0.5 else R[DK]
        streak(t, x, y, n, c, 0, 1)
    t.layer('furrows')
    for xs in paths:
        gap = rnd.randrange(S)
        glen = rnd.randint(1, 2) * k if rnd.random() < plates * 2 else 0
        for y in range(S):
            x = xs[y]
            if glen and (y - gap) % S < glen:
                t.put(x, y, R[DK])                         # a bridge between two plates
                continue
            t.put(x, y, deep)
            if k == 2 and rnd.random() < 0.5 and xs[y - 1] == x:
                t.put(x - 1, y, R[SH])                     # the furrow widens: shadowed left wall
            t.put(x + 1, y, R[LT] if rnd.random() < 0.8 else R[BS])
            if t.get(x - 1, y) not in (R[SH], deep):
                t.put(x - 1, y, R[DK])
    for _ in range(int(plates * 4 * k)):                    # plate cracks across a ridge
        x, y = rnd.randrange(S), rnd.randrange(S)
        n = rnd.randint(2, 3) * k
        for i in range(n):
            if t.get(x + i, y) in (deep,):
                break
            t.put(x + i, y, R[SH])
            t.put(x + i, y + 1, R[LT])
    if overlay:
        overlay(t)
    clean(t, keep=(R[LT], deep))


def g_birch_bark(t, R, M):
    """White bark: faint vertical streaks; dark horizontal lenticel dashes with tapered ends, a light lip
    under each; HD adds a few dark knot scars (eyes)."""
    S, k, rnd = t.S, t.k, t.rnd
    t.add_ramps(M)
    t.layer('bark')
    for y in range(S):
        for x in range(S):
            t.put(x, y, R[BS])
    for _ in range(int(S * S * 0.03)):
        x, y = rnd.randrange(S), rnd.randrange(S)
        streak(t, x, y, rnd.randint(2, 3) * k, R[DK] if rnd.random() < 0.6 else R[HI], 0, 1)
    t.layer('marks')
    for (x, y) in spots(t, 10 if k == 1 else 14, 2.8 * k):
        w = rnd.randint(2, 6) * k if k == 1 else rnd.randint(3, 11)
        hgt = (1 if rnd.random() < 0.7 else 2) if k == 1 else rnd.choice((1, 2, 2, 3))
        for j in range(hgt):
            inset = 1 if (hgt == 2 and j == 0 and w > 3) else 0
            for i in range(inset, w - inset):
                end = i in (inset, w - inset - 1)
                t.put(x + i, y + j, M[DK] if end and w > 2 else M[SH] if j == 0 else M[O])
        for i in range(1, w - 1):
            t.shift(x + i, y + hgt, 1)
    if k == 2:
        for (x, y) in spots(t, 2, 10, rnd=random.Random(t.seed + 5)):
            for dx, dy, c in ((0, 0, M[SH]), (1, 0, M[O]), (2, 0, M[SH]), (-1, 1, M[DK]), (0, 1, M[O]),
                              (1, 1, M[O]), (2, 1, M[O]), (3, 1, M[DK]), (0, 2, M[SH]), (1, 2, M[O]),
                              (2, 2, M[SH]), (1, -1, M[DK]), (1, 3, M[DK])):
                t.put(x + dx, y + dy, c)
    clean(t, keep=(R[HI],))


def g_stem(t, R, G):
    """Nether stem: dark furrowed body with glowing veins running down it (the vein core in the glow's
    light tones, its edges in base / dark glow)."""
    t.add_ramps(G)
    g_bark(t, R, furrows=4, amp=1, plates=0.15, streaks=0.4, light=0.2)
    S, k, rnd = t.S, t.k, t.rnd
    t.layer('glow')
    nv = 2 if k == 1 else 3
    for i in range(nv):
        x0 = (i + 0.3 + rnd.uniform(-0.2, 0.2)) * S / nv
        f, ph = rnd.choice((1, 2)), rnd.uniform(0, 6.3)
        start, n = rnd.randrange(S), rnd.randint(S // 3, S * 2 // 3)
        prev = None
        for j in range(n):
            y = start + j
            x = round(x0 + k * 0.8 * math.sin(2 * math.pi * f * y / S + ph))
            if prev is not None and abs(x - prev) > 1:
                x = prev + (1 if x > prev else -1)
            prev = x
            end = j < k or j >= n - k
            if k == 1:
                t.put(x, y, G[BS] if end else G[LT])
            else:
                t.put(x, y, G[BS] if end else G[HI] if j % 7 in (2, 3) else G[LT])
                t.put(x + 1, y, G[DK] if end else G[BS])
    clean(t, keep=(G[HI], G[LT]))


def g_bamboo_block(t, R, Rn):
    """Bundled bamboo stalks: each a column with a lit left side, base, dark right side and a dark gap;
    nodes as a dark ring with a lit ring above, staggered from stalk to stalk."""
    S, k, rnd = t.S, t.k, t.rnd
    t.add_ramps(Rn)
    t.layer('stalks')
    widths = (5, 5, 6) if k == 1 else (8, 7, 9, 8)
    x = 0
    for si, w in enumerate(widths):
        for i in range(w):
            for y in range(S):
                c = (R[SH] if i == w - 1 else R[LT] if i == 0 else R[HI] if (i == 1 and k == 2) else
                     R[DK] if i == w - 2 else R[BS])
                t.put(x + i, y, c)
        t.layer('nodes')
        ny = (si * 7 * k + rnd.randint(0, 3 * k)) % S
        for ny_ in (ny, (ny + S // 2 + rnd.randint(-k, k)) % S) if k == 2 else (ny,):
            for i in range(w - 1):
                t.put(x + i, ny_, Rn[DK] if i else Rn[BS])
                t.put(x + i, ny_ - 1, Rn[LT] if i < w - 2 else Rn[BS])
                if k == 2:
                    t.put(x + i, ny_ + 1, R[DK] if i else R[BS])
        t.layer('stalks')
        x += w
    t.layer('streaks')
    for _ in range(4 * k):
        sx = rnd.randrange(S)
        if t.get(sx, 0) in (R[BS],):
            streak(t, sx, rnd.randrange(S), rnd.randint(3, 5) * k, R[LT], 0, 1)


def g_log_top(t, Rw, Rb, ring=None, crack=True):
    """End grain: rounded-square growth rings (1 px dark ring lines, the bands between them alternating
    light / base wood, a little wobble), a dark pith, a short radial check crack at HD, the bark as a
    border (1 px; HD 2 px with a lit inner row on the top / left)."""
    S, k, rnd = t.S, t.k, t.rnd
    t.add_ramps(Rb)
    w = ring or (2.4 if k == 1 else 3.2)
    c = (S - 1) / 2
    f = field(t, [(1, 1.0), (2, 0.5)])
    t.layer('rings')
    for y in range(S):
        for x in range(S):
            dx, dy = x - c, y - c
            d = max(abs(dx), abs(dy)) * 0.7 + math.hypot(dx, dy) * 0.3 + (f[(x, y)] - 0.5) * (0.5 if k == 1 else 0.9)
            if d < 0.9 * k:
                col = Rw[SH]
            elif d < 1.6 * k:
                col = Rw[DK]
            else:
                q = (d - 1.6 * k) / w
                col = Rw[DK] if (q - int(q)) * w < (0.95 if k == 1 else 1.05) else (Rw[LT] if int(q) % 2 == 0 else Rw[BS])
            t.put(x, y, col)
    if crack and k == 2:
        t.layer('crack')
        x, y = int(c) + 2, int(c) + 1
        for i in range(S // 4):
            t.put(x, y, Rw[SH])
            if t.get(x + 1, y) != Rw[SH]:
                t.shift(x + 1, y, 1)
            x += 1
            y += 1 if i % 2 else 0
    t.layer('bark')
    for y in range(S):
        for x in range(S):
            e = min(x, y, S - 1 - x, S - 1 - y)
            if e < k:
                side_lit = (x == e or y == e) and not (S - 1 - x == e or S - 1 - y == e)
                if e == 0:
                    col = Rb[BS] if side_lit else Rb[SH]
                else:
                    col = Rb[LT] if side_lit else Rb[DK]
                t.put(x, y, col)
    clean(t, keep=(Rw[SH],))


# ------------------------------------------------------------------ stones
def g_stone(t, R, dark=0.18, light=0.12, freqs=None, dents=True, cracks=None, chips=None, name='stone'):
    """Smooth stone: mottled patches from seamless noise - dents (dark, a shadowed top-left rim) and raised
    patches (light, casting a dark pixel down-right) - plus scattered chips (small lumps lit on the
    top-left with a shadow under them); HD adds highlights on the raised patches and hairline cracks."""
    S, k, rnd = t.S, t.k, t.rnd
    fr = freqs or ([(2, 1.0), (3, 0.7), (5, 0.45)] + ([(8, 0.3)] if k == 2 else []))
    f = field(t, fr)
    t.layer(name)
    for p, v in f.items():
        t.put(*p, R[DK] if v < dark else R[LT] if v > 1 - light else R[BS])
    clean(t)
    t.layer(name + '_relief')
    comp = t.composed()
    for (x, y), c in comp.items():
        up, lf = comp[t.w(x, y - 1)], comp[t.w(x - 1, y)]
        if dents and c == R[DK] and (up != R[DK] or lf != R[DK]) and comp[t.w(x, y + 1)] == R[DK] \
                and comp[t.w(x + 1, y)] == R[DK]:
            t.put(x, y, R[SH])
        elif c == R[BS] and (up == R[LT] or lf == R[LT]) and (k == 2 or rnd.random() < 0.6):
            t.put(x, y, R[DK])
    if k == 2:
        for (x, y), c in comp.items():
            if c == R[LT] and comp[t.w(x - 1, y)] != R[LT] and comp[t.w(x, y - 1)] != R[LT] \
                    and comp[t.w(x + 1, y)] == R[LT] and rnd.random() < 0.5:
                t.put(x, y, R[HI])
                t.put(x + 1, y, R[HI])
    n_chips = (4 if k == 1 else 9) if chips is None else chips
    if n_chips:
        t.layer(name + '_chips')
        for (x, y) in spots(t, n_chips, 4 * k):
            b = blob(rnd, rnd.randint(2, 3) if k == 1 else rnd.randint(4, 8), wide=1.6)
            lump(t, b, x, y, R, rnd.choice((DK, DK, LT)), cast=1)
    n_cracks = (0 if k == 1 else 2) if cracks is None else cracks
    for i in range(n_cracks):
        x, y = rnd.randrange(S), rnd.randrange(S)
        wander(t, x, y, rnd.randint(3, 6) * k, R[SH], main=(1, 0) if i % 2 else (0, 1), lip=1)
    clean(t, keep=(R[HI], R[SH]))


def g_speckled(t, R, groups, base_field=(0.12, 0.1), cracks=0):
    """Igneous / grainy stone: a calm g_stone base plus clusters of mineral grains; groups =
    [(ramp, tone, count per 16x16, size range, 'bump' | 'pit' | 'flat', highlight px)]."""
    S, k, rnd = t.S, t.k, t.rnd
    for g in groups:
        if g[0] is not R:
            t.add_ramps(g[0])
    g_stone(t, R, dark=base_field[0], light=base_field[1], dents=True)
    t.layer('grains')
    taken = []
    for (Rg, tone, n, size, mode, hi) in groups:
        cnt = int(n * k * k * 0.75) if k == 2 else n
        md = 2.4 * k if k == 1 else 3.2
        for (x, y) in spots(t, cnt, md, avoid=taken):
            taken.append((x, y))
            m = rnd.randint(*size) * (k * k if k == 2 and size[1] > 2 else k)
            b = blob(rnd, max(1, m), wide=1.3)
            if mode == 'bump':
                lump(t, b, x, y, Rg, tone, hi=hi if k == 2 else 0, cast=1 if k == 2 else 0)
            elif mode == 'pit':
                pit(t, b, x, y, Rg, tone)
            else:
                for (bx, by) in b:
                    t.put(x + bx, y + by, Rg[tone])
    for i in range(cracks * k):
        wander(t, rnd.randrange(S), rnd.randrange(S), rnd.randint(4, 7) * k, R[SH], main=(1, 0) if i % 2 else (0, 1), lip=1)
    clean(t, keep=[r[HI] for r in t.ramps])


def g_cobble(t, R, grid=3, R2=None, tones=(DK, BS, BS, LT), joint=SH, hi=True, chips=True, mossy=None, deep=False):
    """Cobbles: seamless Voronoi stones with dark joints; every stone rounded by the light (lit top-left
    rim and cap, dark bottom-right rim), its own tone (and some from a second ramp), a glint on the bigger
    ones; HD: 2 px joints with an outline core, chips and cracks inside the stones."""
    S, k, rnd = t.S, t.k, t.rnd
    if R2:
        t.add_ramps(R2)
    seeds, own, d1, d2 = voronoi(t, grid, jitter=0.9, sx=1.0, sy=1.12)
    tone = {i: rnd.choice(tones) for i in range(len(seeds))}
    rmp = {i: (R2 if R2 and rnd.random() < 0.35 else R) for i in range(len(seeds))}
    J = set()
    for (x, y), o in own.items():
        if own[t.w(x + 1, y)] != o or own[t.w(x, y + 1)] != o:
            J.add((x, y))
        elif k == 2 and d2[(x, y)] - d1[(x, y)] < 1.3:
            J.add((x, y))
    t.layer('stones')
    size = Counter(own.values())
    r0 = S / grid / 2
    for (x, y), o in own.items():
        if (x, y) in J:
            continue
        Rr, b = rmp[o], tone[o]
        sx_, sy_ = seeds[o]
        rx, ry = _sw(x + 0.5 - sx_, S) / r0, _sw(y + 0.5 - sy_, S) / r0
        lam = -(0.62 * rx + 0.78 * ry)
        tl = t.w(x - 1, y) in J or own[t.w(x - 1, y)] != o or t.w(x, y - 1) in J or own[t.w(x, y - 1)] != o
        br = t.w(x + 1, y) in J or t.w(x, y + 1) in J
        if k == 1:                                     # small stones: flat face, lit top-left rim, dark lower rim
            i = b + 1 if tl and not br else b - 1 if br and not tl and size[o] > 7 else b
        else:
            i = b + (1 if lam > 0.5 else -1 if lam < -0.55 else 0)
            if tl:
                i = max(i, b + 1) if lam > -0.3 else b
            if br:
                i = min(i, b - 1)
        t.put(x, y, Rr[_c(max(1, i))])
    t.layer('joints')
    for (x, y) in J:
        core = k == 1 or d2[(x, y)] - d1[(x, y)] < 0.55
        if k == 1:
            meet = len({own[t.w(x + dx, y + dy)] for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1))}) >= 3
            t.put(x, y, R[_c(joint - 1)] if meet else R[joint])
        else:
            t.put(x, y, R[O] if core else R[SH])
    if deep:
        for (x, y) in J:
            if k == 1 and rnd.random() < 0.5:
                t.put(x, y, R[O])
    if hi or chips:
        t.layer('detail')
        for o, (sx_, sy_) in enumerate(seeds):
            if size[o] < (10 if k == 1 else 36):
                continue
            Rr, b = rmp[o], tone[o]
            hx, hy = int(sx_ - r0 * 0.35), int(sy_ - r0 * 0.4)
            if hi and own.get(t.w(hx, hy)) == o and t.w(hx, hy) not in J and b >= BS:
                t.put(hx, hy, Rr[_c(b + 2)])
                t.put(hx + 1, hy, Rr[_c(b + 1 + (k == 2))])
                if k == 2:
                    t.put(hx, hy + 1, Rr[_c(b + 1)])
            if chips and k == 2 and rnd.random() < 0.6:
                cx, cy = int(sx_ + rnd.randint(-2, 3)), int(sy_ + rnd.randint(0, 3))
                pts = [(cx, cy), (cx + 1, cy), (cx + 2, cy + 1)]
                if all(own.get(t.w(*p)) == o and t.w(*p) not in J for p in pts):
                    for p in pts:
                        t.put(*p, Rr[_c(b - 1)])
                    t.shift(cx + 1, cy + 1, 1)
    if mossy:
        moss(t, mossy, J, amount=0.22)
    clean(t, keep=[r[HI] for r in t.ramps] + ([r[LT] for r in t.ramps] if k == 2 else []))


def moss(t, M, J=None, amount=0.3, hang=True):
    """Moss grows in the joints and over the tops of stones: clumps with a lit top-left rim, a dark lower
    rim, a few light tips, hanging strands at HD and a cast shadow on the stone under them."""
    S, k, rnd = t.S, t.k, t.rnd
    t.add_ramps(M)
    f = field(t, [(1, 1.0), (2, 0.7), (3, 0.5)] + ([(5, 0.3)] if k == 2 else []), off=91)
    J = J or set()
    near = {}
    for (x, y) in J:
        for dy in range(-2 * k, k + 1):
            for dx in range(-k, k + 1):
                near[t.w(x + dx, y + dy)] = 1
    pts = {p for p, v in f.items() if v > 1 - amount * (1.5 if p in near else 0.35)}
    pts = {p for p in pts if sum(t.w(p[0] + dx, p[1] + dy) in pts for dx, dy in N8) >= 3}
    t.layer('moss')
    for (x, y) in pts:
        up = t.w(x, y - 1) not in pts or t.w(x - 1, y) not in pts
        dn = t.w(x, y + 1) not in pts or t.w(x + 1, y) not in pts
        i = LT if up and not dn else DK if dn and not up else BS
        if i == BS and rnd.random() < 0.12:
            i = LT
        t.put(x, y, M[i])
    for (x, y) in pts:
        for q in ((x + 1, y + 1), (x, y + 1)):
            if t.w(*q) not in pts:
                t.shift(*q, -1)
    if hang and k == 2:
        for (x, y) in sorted(pts):
            if t.w(x, y + 1) not in pts and rnd.random() < 0.18:
                for j in range(1, rnd.randint(2, 4)):
                    t.put(x, y + j, M[DK] if j > 1 else M[BS])
                t.shift(x + 1, y + 1, -1)


def g_bricks(t, R, Rm=None, rows=2, length=16, offset=8, var=(BS,), joint=SH, texture=0.6, chips=0.5,
             mossy=None, cracked=0, specks=0, rim=1):
    """Running-bond bricks: each brick face lit on its top row and left column, dark on its bottom row and
    right column, a stone / clay texture inside; joints on the right and bottom of every brick (one joint
    between neighbours, so the tile repeats); HD: 2 px joints with the shadowed row on top."""
    S, k, rnd = t.S, t.k, t.rnd
    Rm = Rm or R
    if Rm is not R:
        t.add_ramps(Rm)
    bh, L, off = S // rows, length * k, offset * k
    t.layer('bricks')
    faces = []
    for r in range(rows):
        y0 = r * bh
        x0 = (r * off) % L
        for bx in range(x0 - L, S, L):
            b = rnd.choice(var)
            bevel_cell(t, bx, y0, L, bh, R, base=b, rim=rim, joint=joint, k=k)
            faces.append((bx, y0, L - k, bh - k, b))
    if Rm is not R:
        for (x, y), c in list(t.cur.items()):
            if c in (R[joint], R[_c(joint - 1)]):
                inner = c == R[_c(joint - 1)]
                t.cur[(x, y)] = Rm[DK] if inner or k == 1 else Rm[BS]
    t.layer('texture')
    for (bx, by, w, h, b) in faces:
        for _ in range(int(w * h * 0.02 * texture) + 1 if w - 2 * k - 1 >= 2 * k else 0):
            x, y = bx + rnd.randint(2 * k, w - 2 * k - 1), by + rnd.randint(k + 1, max(k + 1, h - 2 * k))
            m = blob(rnd, rnd.randint(2, 3) * k)
            for (px, py) in m:
                if 0 < px + x - bx < w - k and 0 < py + y - by < h - k:
                    t.put(x + px, y + py, R[_c(b - 1)] if rnd.random() < 0.7 else R[_c(b + 1)])
        if rnd.random() < chips:                         # a chipped corner
            cx, cy = (bx + w - 1, by + h - 1) if rnd.random() < 0.6 else (bx, by + h - 1)
            for (px, py) in ((0, 0), (-1 if cx > bx else 1, 0), (0, -1)) if k == 2 else ((0, 0),):
                t.put(cx + px, cy + py, Rm[DK] if Rm is not R else R[SH])
        for _ in range(specks):
            x, y = bx + rnd.randint(1, w - 2), by + rnd.randint(1, h - 2)
            streak(t, x, y, k + 1, R[_c(b - 2)])
    if cracked:
        t.layer('cracks')
        for i in range(cracked * (1 if k == 1 else 2)):
            bx, by, w, h, b = faces[(i * 3 + 1) % len(faces)]
            x = bx + rnd.randint(2, w - 3)
            wander(t, x, by, h - k, R[O] if k == 2 else R[SH], main=(0, 1), side=0.5, lip=1)
            if k == 2:
                x2 = bx + rnd.randint(2, w - 6)
                wander(t, x2, by + h // 2, rnd.randint(4, 7), R[SH], main=(1, 0), side=0.4, lip=1)
    if mossy:
        J = {p for p, c in t.composed().items() if c in (R[joint], R[_c(joint - 1)], Rm[DK], Rm[BS]) and
             Rm is R or (c in (Rm[DK], Rm[BS]) and Rm is not R)}
        J = {p for p, c in t.composed().items() if c in (R[joint], R[_c(joint - 1)])} if Rm is R else J
        moss(t, mossy, J, amount=0.24)
    clean(t, keep=[r[HI] for r in t.ramps] + [R[SH], R[O]])


def g_panel(t, R, grid=1, joint=SH, inner=None, sheen=False, glint=True):
    """Polished blocks (quartz, purpur): grid x grid flat tiles with a lit top / left bevel, a dark bottom /
    right bevel and a joint; `inner` draws on each face (veins, a recessed centre)."""
    S, k, rnd = t.S, t.k, t.rnd
    c = S // grid
    t.layer('tiles')
    for j in range(grid):
        for i in range(grid):
            bevel_cell(t, i * c, j * c, c, c, R, joint=joint, k=k, lit_corner=glint)
    if inner:
        t.layer('inner')
        for j in range(grid):
            for i in range(grid):
                inner(t, i * c, j * c, c - k, c - k)
    clean(t, keep=(R[HI],))


def g_strata(t, R, bands=(3, 5), streaks=0.6, pits=0, wave=1, top_lit=True):
    """Sedimentary layers (sandstone, deepslate): horizontal bands with wavy, seamless boundaries (lit row
    on top of each band, dark row at its bottom), long streaks along the bedding, a few pits."""
    S, k, rnd = t.S, t.k, t.rnd
    ys, y = [], 0
    while y < S - bands[0] * k:
        ys.append(y)
        y += rnd.randint(*bands) * k
    waves = [(rnd.choice((1, 2)), rnd.uniform(0, 6.3), rnd.choice((0, 1)) * wave * k) for _ in ys]
    t.layer('bands')
    tones = [rnd.choice((BS, BS, DK, LT)) if i else BS for i in range(len(ys))]
    for x in range(S):
        bnd = [(y0 + round(a * math.sin(2 * math.pi * f * x / S + ph))) for y0, (f, ph, a) in zip(ys, waves)]
        for i, b0 in enumerate(bnd):
            b1 = bnd[i + 1] if i + 1 < len(bnd) else bnd[0] + S
            base = tones[i]
            for y in range(b0, b1):
                j = y - b0
                tt = (base + 1 if (j < k and top_lit) else base - 1 if j >= b1 - b0 - k else base)
                t.put(x, y, R[_c(tt)])
    t.layer('streaks')
    for _ in range(int(S * streaks * (0.8 if k == 1 else 1.4))):
        x, y = rnd.randrange(S), rnd.randrange(S)
        n = rnd.randint(3, 6) * k
        tone = t.tone(x, y)
        if tone is None:
            continue
        c = R[_c(tone - 1)] if rnd.random() < 0.6 else R[_c(tone + 1)]
        streak(t, x, y, n, c)
    for _ in range(pits * k):
        x, y = rnd.randrange(S), rnd.randrange(S)
        pit(t, blob(rnd, rnd.randint(2, 4) * k), x, y, R, t.tone(x, y) or BS)
    clean(t, keep=(R[HI],))


def g_deepslate(t, R):
    """Slate: wavy horizontal cleavage - long dark streaks with a lit row under each, broken lit flakes."""
    S, k, rnd = t.S, t.k, t.rnd
    t.layer('slate')
    f = field(t, [(1, 1.0), (2, 0.7), (3, 0.5)] + ([(5, 0.3)] if k == 2 else []), aniso=(0.34, 1))
    for p, v in f.items():
        t.put(*p, R[DK] if v < 0.22 else R[LT] if v > 0.86 else R[BS])
    clean(t)
    t.layer('cleavage')
    for i in range(5 * k):
        x, y = rnd.randrange(S), (i * S // (5 * k) + rnd.randint(0, 2)) % S
        n = rnd.randint(5, 10) * k
        for j in range(n):
            if j and rnd.random() < 0.15:
                y += rnd.choice((-1, 1))
                x += 1
            t.put(x + j, y, R[SH] if k == 1 or j % 9 else R[O])
            t.put(x + j, y + 1, R[LT] if rnd.random() < 0.7 else R[BS])
    clean(t, keep=(R[SH], R[LT], R[O]))


def g_pitted(t, R, n=7, size=(2, 4)):
    """End stone: a pale, calm base pocked with round pits of several sizes - each a recess with a
    shadowed top-left wall, a dark floor and a lit far wall."""
    S, k, rnd = t.S, t.k, t.rnd
    g_stone(t, R, name='end_stone', dark=0.12, light=0.1, dents=False, chips=0, cracks=0)
    t.layer('pits')
    for (x, y) in spots(t, n if k == 1 else 2 * n - 2, 3.4 * k):
        m = rnd.randint(*size) if k == 1 else rnd.randint(size[0] * 2 + 1, size[1] * 3)
        pit(t, blob(rnd, m, wide=1.3), x, y, R, BS)
    clean(t, keep=(R[SH], R[LT]))


def g_lumps(t, R, grid=4, R2=None, contrast=1, joint=SH, glints=True, tones=(DK, BS, BS, LT), r2=0.3, flecks=False):
    """Knobbly lumps (netherrack, raw ore blocks): small Voronoi bumps, each lit on its top-left, dark on
    its bottom-right, with dark gaps; HD adds a cap highlight."""
    S, k, rnd = t.S, t.k, t.rnd
    if R2:
        t.add_ramps(R2)
    seeds, own, d1, d2 = voronoi(t, grid * (1 if k == 1 else 1) + (k - 1) * 2, jitter=0.95)
    tone = {i: rnd.choice(tones) for i in range(len(seeds))}
    rmp = {i: (R2 if R2 and not flecks and rnd.random() < r2 else R) for i in range(len(seeds))}
    t.layer('lumps')
    r0 = S / (grid + (k - 1) * 2) / 2
    for (x, y), o in own.items():
        gap = own[t.w(x + 1, y)] != o or own[t.w(x, y + 1)] != o
        Rr, b = rmp[o], tone[o]
        if gap:
            t.put(x, y, R[joint] if (k == 1 or d2[(x, y)] - d1[(x, y)] < 0.7) else R[_c(joint + 1)])
            continue
        sx_, sy_ = seeds[o]
        rx, ry = _sw(x + 0.5 - sx_, S) / r0, _sw(y + 0.5 - sy_, S) / r0
        lam = -(0.62 * rx + 0.78 * ry)
        i = b + (contrast if lam > 0.35 else -contrast if lam < -0.4 else 0)
        t.put(x, y, Rr[_c(max(1, i))])
    if flecks and R2:                                        # a second mineral as flecks on some lumps
        t.layer('flecks')
        for o, (sx_, sy_) in enumerate(seeds):
            if rnd.random() < r2:
                b = blob(rnd, rnd.randint(2, 3) if k == 1 else rnd.randint(3, 6), wide=1.4)
                fx, fy = int(sx_) + rnd.randint(-k, k), int(sy_) + rnd.randint(-k, k)
                if all(own.get(t.w(fx + i, fy + j)) == o for i, j in b):
                    lump(t, b, fx, fy, R2, BS, hi=1 if k == 2 else 0)
    if glints and k == 2:
        t.layer('glints')
        for o, (sx_, sy_) in enumerate(seeds):
            if tone[o] >= BS:
                hx, hy = int(sx_ - r0 * 0.4), int(sy_ - r0 * 0.45)
                if own.get(t.w(hx, hy)) == o and own.get(t.w(hx + 1, hy)) == o:
                    t.put(hx, hy, rmp[o][HI])
                    t.put(hx + 1, hy, rmp[o][_c(tone[o] + 1)])
    clean(t, keep=[r[HI] for r in t.ramps])


def g_facets(t, R, grid=3, joint=SH, glints=2, frame=False, R2=None):
    """Crystal / coal facets: Voronoi cells, each split through its centre into two flat facets whose
    tones follow the light (the facet facing the top-left light, the one turned away), dark joints, glints
    on the lit facets; HD adds twinkles."""
    S, k, rnd = t.S, t.k, t.rnd
    seeds, own, d1, d2 = voronoi(t, grid + (k - 1) * 1, jitter=0.95, off=5)
    ang = {i: rnd.uniform(0, math.pi) for i in range(len(seeds))}
    if R2:
        t.add_ramps(R2)
    cr = {i: (R2 if R2 and rnd.random() < 0.45 else R) for i in range(len(seeds))}
    t.layer('facets')
    lit_px = []
    for (x, y), o in own.items():
        if own[t.w(x + 1, y)] != o or own[t.w(x, y + 1)] != o or (k == 2 and d2[(x, y)] - d1[(x, y)] < 0.9):
            t.put(x, y, R[joint] if k == 1 or d2[(x, y)] - d1[(x, y)] < 0.45 else R[_c(joint + 1)])
            continue
        sx_, sy_ = seeds[o]
        rx, ry = _sw(x + 0.5 - sx_, S), _sw(y + 0.5 - sy_, S)
        nx, ny = math.cos(ang[o]), math.sin(ang[o])
        side = 1 if rx * nx + ry * ny >= 0 else -1
        lam = -(0.62 * nx + 0.78 * ny) * side             # facet normal tilted toward its side
        i = LT if lam > 0.35 else BS if lam > -0.25 else DK
        if (own[t.w(x - 1, y)] != o or own[t.w(x, y - 1)] != o) and i < LT:
            i += 1
        t.put(x, y, cr[o][i])
        if i == LT and cr[o] is R:
            lit_px.append((x, y))
    t.layer('glints')
    for (x, y) in rnd.sample(lit_px, min(len(lit_px), glints * k * k)) if lit_px else ():
        if t.get(x + 1, y) == R[LT]:
            t.put(x, y, R[HI])
            t.put(x + 1, y, R[HI])
    clean(t, keep=(R[HI],))


# ------------------------------------------------------------------ soils
def g_dirt(t, R, clods=1.0, pebbles=1.0, R2=None):
    """Earth: small tone variations without strong contrast - dark clods (recessed, shadowed top-left),
    light pebbles lit from the top-left with a dark pixel under them, a few deep holes."""
    S, k, rnd = t.S, t.k, t.rnd
    g_stone(t, R, name='dirt', dark=0.14, light=0.08, freqs=[(2, 1.0), (3, 0.8), (5, 0.5)] + ([(7, 0.3)] if k == 2 else []))
    t.layer('clods')
    taken = []
    for (x, y) in spots(t, int(7 * clods * k * k), 3 * k):
        taken.append((x, y))
        m = blob(rnd, rnd.randint(2, 4) * k, wide=1.4)
        lump(t, m, x, y, R, DK, rim=1)
    for (x, y) in spots(t, int(5 * pebbles * k * k), 3 * k, avoid=taken):
        Rr = R2 if R2 and rnd.random() < 0.5 else R
        if k == 1:
            t.put(x, y, Rr[LT])
            t.put(x + 1, y, Rr[LT])
            t.put(x + 1, y + 1, R[SH])
        else:
            lump(t, blob(rnd, rnd.randint(3, 5), wide=1.3), x, y, Rr, LT, hi=1, cast=2)
    for (x, y) in spots(t, 2 * k, 5 * k, avoid=taken):
        pit(t, {(0, 0), (1, 0)} if k == 1 else blob(rnd, 4, wide=1.5), x, y, R, DK)
    clean(t, keep=(R[HI], R[SH]) + ((R2[LT], R2[HI]) if R2 else ()))


def blades(t, R, density=1.0, tall=(2, 3), lit=0.55):
    """Grass seen from above: tufts on a jittered grid - lit blades with a light tip, dark blades between
    them and a shadowed root pixel."""
    S, k, rnd = t.S, t.k, t.rnd
    step = 3 if k == 1 else 4
    for gy in range(0, S, step):
        for gx in range(0, S, step):
            if rnd.random() > density:
                continue
            x, y = gx + rnd.randint(0, step - 1), gy + rnd.randint(0, step - 1)
            n = rnd.randint(*tall) * (1 if k == 1 else 2) - (1 if k == 2 else 0)
            litb = rnd.random() < lit
            lean = rnd.choice((0, 0, 1, -1)) if k == 2 else 0
            for j in range(n):
                xx = x + (lean if j >= n // 2 + 1 else 0)
                c = (R[HI] if (j == 0 and k == 2 and litb and rnd.random() < 0.3) else R[LT]) if litb else R[DK]
                t.put(xx, y + j, c)
            t.put(x, y + n, R[DK])
            if k == 2:
                t.put(x + 1, y + n, R[DK])


def g_grass_top(t, R):
    """Grass seen from above: a mottled green with tufts of blades (lit blades and tips, dark blades
    between, a shadowed root)."""
    S, k = t.S, t.k
    g_stone(t, R, name='grass', dark=0.2, light=0.14, freqs=[(2, 1.0), (3, 0.8), (5, 0.5)], dents=False, chips=0, cracks=0)
    t.layer('blades')
    blades(t, R, density=0.7 if k == 1 else 0.95, tall=(1, 2) if k == 1 else (2, 3))
    clean(t, keep=(R[HI], R[LT], R[SH]))


def g_grass_side(t, R, G):
    """Dirt with grass hanging over the top edge: the grass cap is lit on its top row, its uneven fringe
    ends in a dark pixel and casts a shadow on the dirt below; a few blades poke out above the fringe."""
    S, k, rnd = t.S, t.k, t.rnd
    t.add_ramps(G)
    g_dirt(t, R)
    t.layer('grass')
    base = 3 * k
    prev = base
    depth = []
    for x in range(S):
        d = base + rnd.choice((0, 0, 1, 1, 2, 3)) * (1 if k == 1 else 2) - (rnd.random() < 0.25)
        if x and abs(d - prev) > 2 * k:
            d = prev + (2 * k if d > prev else -2 * k)
        depth.append(max(k + 1, d))
        prev = d
    depth[-1] = min(depth[-1], depth[0] + k)
    for x in range(S):
        d = depth[x]
        for y in range(d):
            c = G[LT] if y < k else G[DK] if y == d - 1 else G[BS]
            if k == 2 and y == 1 and rnd.random() < 0.3:
                c = G[HI]
            t.put(x, y, c)
        if k == 2 and rnd.random() < 0.35:
            t.put(x, rnd.randint(2, max(2, d - 3)), G[DK])
        t.shift(x, d, -2)
        if x + 1 < S and depth[x + 1] < d:
            t.shift(x + 1, d - 1, -1)
    clean(t, keep=(G[HI], G[LT], R[SH]))


def g_needles(t, R, N, n=12):
    """Podzol: dark forest soil strewn with needles (short diagonal 1 px strokes, lit / dark)."""
    S, k, rnd = t.S, t.k, t.rnd
    t.add_ramps(N)
    g_dirt(t, R, clods=0.6, pebbles=0.3)
    t.layer('needles')
    for (x, y) in spots(t, n if k == 1 else n + 4, 2.2 * k):
        L = rnd.randint(2, 3) if k == 1 else rnd.randint(3, 5)
        dx = rnd.choice((1, -1))
        steep = k == 2 and rnd.random() < 0.5                    # 2:1 slopes at HD, not only 45 degrees
        litn = rnd.random() < 0.55
        px_, py_ = x, y
        for i in range(L):
            t.put(px_, py_, N[LT] if litn else N[BS] if i < L - 1 else N[DK])
            if steep:
                px_ += dx * (i % 2)
                py_ += 1
            else:
                px_ += dx
                py_ += 1 if (k == 1 or i % 2 == 0) else 0
        t.shift(px_ + 1, py_ + 1, -1)
    clean(t, keep=(N[LT], N[BS], N[DK]))


def g_mycelium(t, R, Sp):
    S, k, rnd = t.S, t.k, t.rnd
    t.add_ramps(Sp)
    g_stone(t, R, name='mycelium', dark=0.2, light=0.1, freqs=[(1, 1.0), (2, 0.8), (4, 0.5)], dents=True)
    t.layer('spores')
    for (x, y) in spots(t, 9 * k * k, 2.6 * k):
        if k == 1:
            t.put(x, y, Sp[LT])
            t.put(x + 1, y, Sp[LT])
            t.put(x + 1, y + 1, Sp[BS])
        else:
            lump(t, blob(rnd, rnd.randint(2, 4), wide=1.5), x, y, Sp, BS, hi=1, cast=1)
    clean(t, keep=(Sp[HI],))


def g_sand(t, R, grains=1.0):
    """Sand: fine grains in 2 px clusters, light ones lit from the top-left, dark ones with a shadow pixel
    - small variations, low contrast."""
    S, k, rnd = t.S, t.k, t.rnd
    g_stone(t, R, name='sand', dark=0.12, light=0.12, freqs=[(2, 1.0), (3, 0.7), (5, 0.5)], dents=False)
    t.layer('grains')
    for (x, y) in spots(t, int(14 * grains * k * k), 2.0 * k):
        r_ = rnd.random()
        if r_ < 0.45:
            t.put(x, y, R[DK])
            t.put(x + 1, y, R[DK] if k == 1 else R[SH])
        elif r_ < 0.85:
            t.put(x, y, R[LT])
            t.put(x + 1, y, R[LT])
            if k == 2:
                t.put(x, y - 1, R[HI])
        else:
            t.put(x, y, R[SH])
            t.put(x, y + 1, R[DK])
    clean(t, keep=(R[HI], R[SH]))


def g_clay(t, R):
    S, k, rnd = t.S, t.k, t.rnd
    g_stone(t, R, name='clay', dark=0.2, light=0.18, freqs=[(1, 1.0), (2, 0.8), (3, 0.4)], dents=True)
    t.layer('marks')
    for (x, y) in spots(t, 3 * k, 5 * k):
        streak(t, x, y, rnd.randint(2, 4) * k, R[DK])
        streak(t, x, y + 1, rnd.randint(2, 4) * k, R[LT])
    clean(t)


def g_mud(t, R):
    """Wet mud: dark lumps and puddles whose wet tops catch long horizontal reflections (light mid with a
    highlight core), the wet edge under them dark."""
    S, k, rnd = t.S, t.k, t.rnd
    g_stone(t, R, name='mud', dark=0.25, light=0.0, freqs=[(1, 1.0), (2, 0.8), (3, 0.6)], dents=True)
    t.layer('wet')
    for (x, y) in spots(t, 5 * k, 3.5 * k):
        n = rnd.randint(3, 5) * k
        streak(t, x, y, n, R[LT])
        if k == 2:
            streak(t, x + 1, y, max(2, n // 2), R[HI])
            streak(t, x + 2, y - 1, max(2, n - 4), R[LT])
        streak(t, x - 1, y + 1, n, R[DK])
    clean(t, keep=(R[HI], R[LT]))


def g_snow(t, R):
    """Snow: soft drifts - wide light-mid tops, dark-mid (cool blue) hollows on their lower side, a few
    sparkles."""
    S, k, rnd = t.S, t.k, t.rnd
    f = field(t, [(2, 1.0), (3, 0.7), (5, 0.4)] + ([(8, 0.25)] if k == 2 else []), aniso=(1, 0.7))
    t.layer('snow')
    for p, v in f.items():
        t.put(*p, R[DK] if v < 0.16 else R[LT] if v > 0.6 else R[BS])
    clean(t)
    comp = t.composed()
    t.layer('drift')
    for (x, y), c in comp.items():
        if c == R[LT] and comp[t.w(x, y + 1)] == R[BS] and rnd.random() < 0.7:
            t.put(x, y + 1, R[DK])
    t.layer('sparkle')
    for (x, y) in spots(t, 3 * k, 5 * k):
        if comp[t.w(x, y)] == R[LT]:
            t.put(x, y, R[HI])
            if k == 2:
                t.put(x + 1, y, R[HI])
    clean(t, keep=(R[HI],))


def g_ice(t, R, streaks=1.0, cracks=0, cells=False):
    """Ice: clear blue with long diagonal light streaks (/), darker deep patches and a few frozen bubbles;
    packed ice (cells=True) shows the frozen grain boundaries as light lines; cracks are white fractures
    with a dark lower edge."""
    S, k, rnd = t.S, t.k, t.rnd
    f = field(t, [(1, 1.0), (2, 0.7), (3, 0.4)])
    t.layer('ice')
    for p, v in f.items():
        t.put(*p, (R[SH] if (k == 2 and v < 0.03) else R[DK]) if v < 0.2 else R[LT] if v > 0.86 else R[BS])
    clean(t, keep=(R[SH],))
    if cells:
        seeds, own, d1, d2 = voronoi(t, 3 + k, jitter=0.9, off=2)
        t.layer('grain')
        for (x, y), o in own.items():
            if own[t.w(x + 1, y)] != o or own[t.w(x, y + 1)] != o:
                t.put(x, y, R[LT])
                t.shift(x + 1, y + 1, -1)
    t.layer('streaks')
    for i in range(int(3 * streaks * k)):
        x, y = rnd.randrange(S), rnd.randrange(S)
        L = rnd.randint(3, 5) * k
        for j in range(L):
            t.put(x + j, y - j, R[HI] if j < L - k else R[LT])
            if k == 2 and j < L - 2:
                t.put(x + j + 1, y - j, R[LT])
        if k == 2:
            for j in range(L // 2):
                t.put(x + j + 3, y - j + 1, R[LT])
    if k == 2:
        for (x, y) in spots(t, 3, 8):
            for dx, dy, c in ((0, 0, R[HI]), (1, 0, R[LT]), (0, 1, R[LT]), (1, 1, R[DK])):
                t.put(x + dx, y + dy, c)
    if cracks:
        t.layer('cracks')
        for i in range(cracks * k):
            x, y = rnd.randrange(S), rnd.randrange(S)
            pts = wander(t, x, y, rnd.randint(5, 9) * k, R[HI], main=(1, 1) if i % 2 else (1, -1), side=0.0)
            for (px, py) in pts:
                t.shift(px, py + 1, -2) if t.get(px, py + 1) != R[HI] else None
            bx, by = pts[len(pts) // 2]
            wander(t, bx, by + 1, rnd.randint(2, 4) * k, R[HI], main=(0, 1), side=0.5)
    clean(t, keep=(R[HI], R[LT], R[DK]))


def g_soul_sand(t, R, Sl):
    """Soul sand: dark grainy sand with swirled hollows - each a pit with a faint soul-blue glimmer at its
    lit lip."""
    S, k, rnd = t.S, t.k, t.rnd
    t.add_ramps(Sl)
    g_sand(t, R, grains=0.7)
    t.layer('hollows')
    for (x, y) in spots(t, 4 * k, 6 * k):
        w, h = (3, 2) if k == 1 else (rnd.randint(4, 6), 3)
        m = {(i, j) for i in range(w) for j in range(h) if not (j == 0 and i in (0, w - 1) and k == 2)}
        pit(t, m, x, y, R, BS)
        t.put(x + w - 1, y + h, Sl[DK])
        if k == 2:
            t.put(x + w - 2, y + h, Sl[BS])
    clean(t, keep=(Sl[DK], Sl[BS], R[SH]))


# ------------------------------------------------------------------ metals
def g_metal(t, R, plates=2, rivets=True, brushed=0.6, sheen=True, patina=0.0, P=None, stripes=False):
    """Metal block: one block-face panel (lit top / left bevel, dark bottom / right bevel, the joint on the
    right and bottom so tiles sit side by side), split into plates by seams; brushed streaks, a diagonal
    sheen band (light mid with a highlight core, ragged), rivets in the plate corners; patina (a second
    ramp) grows from the seams and joints first."""
    S, k, rnd = t.S, t.k, t.rnd
    t.layer('plate')
    ph = S // plates
    for p_ in range(plates):
        bevel_cell(t, 0, p_ * ph, S, ph, R, joint=SH, k=k, lit_corner=True)
    t.layer('brushed')
    for _ in range(int(S * brushed * (0.6 if k == 1 else 1.1))):
        x, y = rnd.randrange(2 * k, S - 3 * k), rnd.randrange(S)
        if (y % ph) < 2 * k or (y % ph) > ph - 3 * k:
            continue
        n = rnd.randint(2, 4) * k
        streak(t, x, y, min(n, S - 2 * k - x), R[DK] if rnd.random() < 0.55 else R[LT])
    if sheen:
        t.layer('sheen')
        w = 2 * k
        for y in range(S):
            if (y % ph) < k or (y % ph) >= ph - k:
                continue
            c0 = S - 1 - y + rnd.choice((0, 0, 1)) - S // 6
            for x in range(c0 - w, c0 + w + 1):
                if k <= x < S - 2 * k:
                    core = abs(x - c0) < (1 if k == 1 else 2)
                    t.put(x, y, R[HI] if core and k == 2 else R[LT])
            c1 = c0 + S // 2 + 1
            for x in range(c1 - k, c1 + 1):
                if k <= x < S - 2 * k and k == 2:
                    t.put(x, y, R[LT])
    if stripes:
        t.layer('stripes')
        for p_ in range(plates):
            y = p_ * ph + ph // 2 - k // 2
            for x in range(k + 1, S - 2 * k):
                t.put(x, y, R[DK])
                if k == 2:
                    t.put(x, y + 1, R[LT])
    if rivets:
        t.layer('rivets')
        for p_ in range(plates):
            y0 = p_ * ph
            for (rx, ry) in ((2 * k, y0 + 2 * k), (S - 3 * k - (k == 2), y0 + 2 * k),
                             (2 * k, y0 + ph - 3 * k - (k == 2)), (S - 3 * k - (k == 2), y0 + ph - 3 * k - (k == 2))):
                if k == 1:
                    t.put(rx, ry, R[HI])
                    t.put(rx + 1, ry + 1, R[DK])
                else:
                    for dx, dy, c in ((0, 0, R[HI]), (1, 0, R[LT]), (0, 1, R[LT]), (1, 1, R[DK]), (2, 1, R[SH]),
                                      (1, 2, R[SH]), (2, 2, R[SH])):
                        t.put(rx + dx, ry + dy, c)
    if patina and P:
        t.add_ramps(P)
        verdigris(t, R, P, patina)
    clean(t, keep=(R[HI], R[LT], R[DK]) + ((P[LT], P[HI]) if P else ()))


def verdigris(t, R, P, amount):
    """Patina over a metal: grows from joints and seams (dark tones) outward; the metal's tone maps to the
    same tone of the patina ramp, so plates and bevels still read; matte - no highlight."""
    S, k, rnd = t.S, t.k, t.rnd
    f = field(t, [(1, 1.0), (2, 0.8), (3, 0.6), (5, 0.4)] + ([(7, 0.3)] if k == 2 else []), off=77)
    comp = t.composed()
    seam = {p for p, c in comp.items() if c in (R[SH], R[O])}
    dist = {}
    for (x, y) in comp:
        dist[(x, y)] = min((max(abs(_sw(x - sx, S)), abs(_sw(y - sy, S))) for sx, sy in seam
                            if abs(_sw(x - sx, S)) < 4 * k and abs(_sw(y - sy, S)) < 4 * k), default=9)
    t.layer('patina')
    for p, c in comp.items():
        v = f[p] + (0.45 if dist[p] <= k else 0.25 if dist[p] <= 2 * k else 0)
        if v > 1.2 - amount * 1.2:
            i = R.index(c) if c in R else BS
            t.put(*p, P[{O: O, SH: SH, DK: DK, BS: BS, LT: LT, HI: LT}[i]])
    clean(t)
    if amount > 0.5:
        for _ in range(3 * k):                              # drips down from the seams
            x, y = rnd.randrange(S), rnd.randrange(S)
            if t.get(x, y) in P:
                streak(t, x, y, rnd.randint(2, 4) * k, P[DK], 0, 1)


def g_oxidized(t, P, R):
    """Fully oxidised copper: the panel in matte patina, darker drip streaks, a little copper left in the
    deepest joints."""
    t.add_ramps(R)
    g_metal(t, P, plates=2, rivets=True, brushed=0.3, sheen=False)
    S, k, rnd = t.S, t.k, t.rnd
    t.layer('drips')
    for _ in range(5 * k):
        x, y = rnd.randrange(k, S - 2 * k), rnd.randrange(S)
        streak(t, x, y, rnd.randint(2, 5) * k, P[DK], 0, 1)
        if rnd.random() < 0.5:
            t.put(x + 1, y, P[LT])
    clean(t, keep=(P[LT], P[HI]))


# ------------------------------------------------------------------ gems
def g_cut_gems(t, R, cut='brilliant', glints=True):
    """Gem block: a grid of cut stones. brilliant = 2x2 pyramids (top / left facets lit, right / bottom
    dark, a table with a highlight); emerald = elongated octagonal step cuts in a running bond."""
    S, k, rnd = t.S, t.k, t.rnd
    t.layer('cuts')
    if cut == 'brilliant':
        cells = [(i * S // 2, j * S // 2, S // 2, S // 2) for j in range(2) for i in range(2)]
    else:
        cells = []
        for r in range(2):
            x0 = 0 if r == 0 else S // 4
            cells += [(x0 - S + i * S, r * S // 2, S, S // 2) for i in range(2)] if r else [(0, 0, S, S // 2)]
    for (x0, y0, w, h) in cells:
        fw, fh = w - k, h - k
        bw = 2 * k if cut == 'brilliant' else (2 * k if k == 2 else 1)
        cutc = k if cut != 'brilliant' else 0
        for y in range(h):
            for x in range(w):
                if x >= fw or y >= fh:
                    t.put(x0 + x, y0 + y, R[SH] if k == 1 or (x == w - 1 or y == h - 1) else R[DK])
                    continue
                if cutc and min(x, fw - 1 - x) + min(y, fh - 1 - y) < cutc:
                    t.put(x0 + x, y0 + y, R[SH])            # octagon corners
                    continue
                e_t, e_l, e_b, e_r = y, x, fh - 1 - y, fw - 1 - x
                m = min(e_t, e_l, e_b, e_r)
                if m < bw:
                    if m == e_t:
                        i = HI if (k == 2 and e_t == 0) else LT
                    elif m == e_l:
                        i = LT
                    elif m == e_r:
                        i = DK
                    else:
                        i = SH if k == 2 and e_b == 0 else DK
                else:
                    i = BS
                t.put(x0 + x, y0 + y, R[i])
        if glints:
            gx, gy = x0 + bw + 1, y0 + bw + (1 if cut == 'brilliant' else 0)
            for j in range(2 if k == 1 else 4):
                t.put(gx + j, gy + (0 if k == 1 else 0) - (j if cut == 'brilliant' and k == 2 and False else 0), R[HI] if j < 2 * k - 1 else R[LT])
            if k == 2:
                t.put(gx, gy + 1, R[LT])
                for j in range(3):                          # a diagonal reflection across the table
                    t.put(x0 + fw - bw - 3 - j, y0 + fh - bw - 2 + j - 2, R[LT])
    if k == 2 and glints:
        t.layer('twinkle')
        x, y = S // 2 - 6, S // 2 - 6
        for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            t.put(x + dx, y + dy, R[HI])
    clean(t, keep=(R[HI], R[LT]))


def g_inlay(t, R, F=None, flecks=6, veins=True, frame=True):
    """Lapis / redstone blocks: a framed panel; inside, a mottled stone (or dust) with flecks of a second
    material (pyrite gold, glowing dust) as small lit clusters."""
    S, k, rnd = t.S, t.k, t.rnd
    if F:
        t.add_ramps(F)
    t.layer('panel')
    bevel_cell(t, 0, 0, S, S, R, joint=SH, k=k, lit_corner=True)
    f = field(t, [(2, 1.0), (3, 0.7), (4, 0.5)] + ([(6, 0.3)] if k == 2 else []))
    t.layer('mottle')
    for (x, y), v in f.items():
        if 2 * k <= x < S - 2 * k and 2 * k <= y < S - 2 * k:
            if v < 0.2:
                t.put(x, y, R[DK])
            elif v > 0.84:
                t.put(x, y, R[LT])
    clean(t)
    if veins:
        t.layer('veins')
        for i in range(k + 1):
            x, y = rnd.randrange(3 * k, S - 3 * k), 2 * k + rnd.randrange(S // 3)
            for j in range(rnd.randint(5, 8) * k):
                if not (2 * k <= x < S - 2 * k and 2 * k <= y < S - 2 * k):
                    break
                t.put(x, y, R[LT])
                x += rnd.choice((0, 1, 1))
                y += 1
    t.layer('flecks')
    for (x, y) in spots(t, flecks * k * (2 if k == 2 else 1), 3.2 * k):
        if not (2 * k <= x < S - 3 * k and 2 * k <= y < S - 3 * k):
            continue
        Fr = F or R
        if k == 1:
            t.put(x, y, Fr[HI])
            t.put(x + 1, y, Fr[BS])
            t.put(x, y + 1, Fr[BS])
            t.put(x + 1, y + 1, R[SH])
        else:                                                    # a nugget: 2x2 core and a tail
            shape = {(0, 0): HI, (1, 0): LT, (0, 1): LT, (1, 1): BS}
            tail = rnd.choice(((2, 1), (1, 2), (-1, 1), (2, 0)))
            shape[tail] = DK if tail[0] > 0 or tail[1] > 1 else LT
            for (dx, dy), i_ in shape.items():
                t.put(x + dx, y + dy, Fr[i_])
            for (dx, dy) in shape:
                for q in ((dx + 1, dy), (dx, dy + 1)):
                    if q not in shape:
                        t.put(x + q[0], y + q[1], R[SH])
    clean(t, keep=(R[HI],) + ((F[HI], F[LT]) if F else ()))


def g_studs(t, R, grid=3):
    """Redstone block: a framed panel studded with glowing dots in a grid - each dot a small dome (highlight
    and light mid on the top-left, dark on the bottom-right) with a hard shadow down-right."""
    S, k, rnd = t.S, t.k, t.rnd
    t.layer('panel')
    bevel_cell(t, 0, 0, S, S, R, base=DK, joint=SH, k=k, lit_corner=False)
    t.layer('mottle')
    f = field(t, [(2, 1.0), (4, 0.5)])
    for (x, y), v in f.items():
        if 2 * k <= x < S - 2 * k and 2 * k <= y < S - 2 * k and v > 0.8:
            t.put(x, y, R[BS])
    clean(t)
    t.layer('studs')
    sp = (S - 2 * k) // grid
    d = 2 * k
    for j in range(grid):
        for i in range(grid):
            x0 = k + sp * i + (sp - d) // 2
            y0 = k + sp * j + (sp - d) // 2
            if k == 1:
                pts = {(0, 0): HI, (1, 0): LT, (0, 1): LT, (1, 1): BS}
            else:
                pts = {(1, 0): LT, (2, 0): BS, (0, 1): LT, (1, 1): HI, (2, 1): LT, (3, 1): BS, (0, 2): BS,
                       (1, 2): LT, (2, 2): BS, (3, 2): DK, (1, 3): DK, (2, 3): DK}
            for (dx, dy), i_ in pts.items():
                t.put(x0 + dx, y0 + dy, R[i_])
            for (dx, dy) in pts:
                for q in ((dx + 1, dy), (dx, dy + 1), (dx + 1, dy + 1)):
                    if q not in pts:
                        t.put(x0 + q[0], y0 + q[1], R[SH])
    clean(t, keep=(R[HI], R[LT], R[BS], R[SH]))


# ------------------------------------------------------------------ ores
ORES = {
    #           ramp, clusters (k=1), size (k=1 px), style
    'coal': ('coal', 4, (4, 7), 'chunk'), 'iron': ('iron_ore', 4, (4, 6), 'blob'),
    'gold': ('gold_ore', 4, (4, 6), 'blob'), 'copper': ('copper_ore', 4, (4, 7), 'blob'),
    'diamond': ('diamond', 4, (4, 6), 'blob'), 'emerald': ('emerald', 3, None, 'gem'),
    'lapis': ('lapis', 5, (3, 5), 'blob'), 'redstone': ('redstone', 5, (3, 5), 'dust'),
}
_EMERALD = {1: ['.X.', 'XXX', 'XXX', '.X.'],
            2: ['..X..', '.XXX.', 'XXXXX', 'XXXXX', 'XXXXX', '.XXX.', '..X..']}


def g_ore(t, ore, base='stone'):
    """An ore: the host stone (stone or deepslate) plus clusters of the mineral - each a raised lump in the
    ore's ramp (lit top-left rim, highlight, dark bottom-right rim; HD: two or three nuggets per cluster)
    set into the stone with a selective rim in the stone's darks (dark mid on the top / left, shadow on the
    bottom / right). Emeralds are cut rhombi (lit left facet, dark right facet, a glint)."""
    S, k, rnd = t.S, t.k, t.rnd
    rk, n, size, style = ORES[ore]
    Ro, Rs = RAMPS[rk], RAMPS[base]
    t.add_ramps(Ro, Rs)
    if base == 'deepslate':
        g_deepslate(t, Rs)
    else:
        g_stone(t, Rs, chips=2 * k, cracks=0)
    t.layer('ore')
    for (x, y) in spots(t, n + (k - 1) * (n // 2 + 1), (4.2 if k == 1 else 6.5)):
        if style == 'gem':
            rows = _EMERALD[k]
            b = {(i, j) for j, r in enumerate(rows) for i, ch in enumerate(r) if ch == 'X'}
            mid = (len(rows[0]) - 1) / 2
            for (i, j) in b:
                i_ = LT if i < mid else BS if i == mid else DK
                if j == len(rows) - 1 or (j >= len(rows) - 2 and i > mid):
                    i_ = min(i_, DK) if i >= mid else BS
                t.put(x + i, y + j, Ro[i_])
            t.put(x + int(mid), y + 1, Ro[HI])
            if k == 2:
                t.put(x + int(mid) - 1, y + 2, Ro[HI])
        else:
            if k == 1:
                b = blob(rnd, rnd.randint(*size), wide=1.3)
                parts_ = [(b, 0, 0)]
            else:
                parts_ = []
                for m in range(rnd.choice((2, 2, 3))):
                    bb = blob(rnd, rnd.randint(size[0] + 2, size[1] + 5), wide=1.3)
                    parts_.append((bb, rnd.randint(-3, 3) if m else 0, rnd.randint(-2, 3) if m else 0))
                b = set()
                for bb, dx, dy in parts_:
                    b |= {(i + dx, j + dy) for i, j in bb}
            base_t = LT if style == 'dust' else BS
            for bb, dx, dy in parts_:
                lump(t, {(i + dx, j + dy) for i, j in bb}, x, y, Ro, base_t, hi=1 if k == 1 else 2)
            if ore == 'copper':
                i, j = sorted(b)[len(b) // 2]
                t.put(x + i, y + j, RAMPS['patina'][LT])
                if k == 2:
                    t.put(x + i + 1, y + j, RAMPS['patina'][BS])
        for (i, j) in b:
            for (q, lit) in (((i - 1, j), True), ((i, j - 1), True), ((i + 1, j), False), ((i, j + 1), False),
                             ((i + 1, j + 1), False)):
                if q not in b and t.get(x + q[0], y + q[1]) not in Ro:
                    t.put(x + q[0], y + q[1], Rs[DK] if lit else Rs[SH] if style != 'chunk' else Rs[O])
    clean(t, keep=(Ro[HI], Ro[LT], Rs[SH], Rs[DK], RAMPS['patina'][LT]))


# ------------------------------------------------------------------ fabrics
def g_wool(t, R):
    """Wool: fleece of little curls - each an arc lit on its upper left and dark on its lower right, on a
    jittered grid so they overlap like fibres (wider colour groups, no single-pixel noise)."""
    S, k, rnd = t.S, t.k, t.rnd
    t.layer('wool')
    f = field(t, [(1, 1.0), (2, 0.6)])
    for p, v in f.items():
        t.put(*p, R[DK] if v < (0.06 if k == 1 else 0.1) else R[BS])
    t.layer('curls')
    if k == 1:
        stamps = [((0, 0, LT), (1, 0, LT), (1, 1, DK), (2, 1, SH)),
                  ((1, 0, LT), (2, 0, LT), (0, 1, DK), (1, 1, DK)),
                  ((0, 0, LT), (0, 1, LT), (1, 1, DK), (1, 2, DK)),
                  ((0, 0, LT), (1, 0, LT), (2, 1, DK))]
        step = 3
    else:
        stamps = [((1, 0, LT), (2, 0, LT), (0, 1, LT), (0, 2, LT), (3, 1, DK), (3, 2, DK), (1, 3, DK), (2, 3, SH),
                   (1, 1, HI)),
                  ((1, 0, LT), (2, 0, LT), (3, 1, LT), (0, 1, LT), (0, 2, DK), (1, 3, DK), (2, 3, DK)),
                  ((0, 0, LT), (1, 0, LT), (2, 1, LT), (2, 2, DK), (1, 3, DK), (0, 3, DK)),
                  ((2, 0, LT), (1, 0, LT), (0, 1, LT), (0, 2, DK), (1, 3, DK), (2, 3, DK), (3, 2, DK))]
        step = 4
    for gy in range(0, S, step):
        for gx in range(0, S, step):
            x, y = gx + rnd.randint(0, step - 1), gy + rnd.randint(0, step - 1)
            for dx, dy, i in rnd.choice(stamps):
                if i == HI and rnd.random() < 0.6:
                    i = LT
                t.put(x + dx, y + dy, R[i])
    clean(t, keep=(R[HI],))


def g_leather(t, R):
    """Leather: a broken network of fine creases (dark line, lit lip on its lower side), worn light patches,
    darker scuffed patches."""
    S, k, rnd = t.S, t.k, t.rnd
    f = field(t, [(1, 1.0), (2, 0.7), (3, 0.4)])
    t.layer('hide')
    for p, v in f.items():
        t.put(*p, R[DK] if v < 0.18 else R[LT] if v > 0.88 else R[BS])
    clean(t)
    seeds, own, d1, d2 = voronoi(t, 3 + (k - 1), jitter=0.95, sx=1.0, sy=1.4, off=3)
    br = field(t, [(2, 1.0), (4, 0.6)], off=9)
    t.layer('creases')
    for (x, y), o in own.items():
        if (own[t.w(x + 1, y)] != o or own[t.w(x, y + 1)] != o) and br[(x, y)] > 0.45:
            t.put(x, y, R[SH] if br[(x, y)] > 0.75 else R[DK])
            if own[t.w(x, y + 1)] == o:
                t.shift(x, y + 1, 1)
    if k == 2:
        for (x, y) in spots(t, 6, 5):
            t.put(x, y, R[SH])
            t.put(x + 1, y, R[DK])
    clean(t, keep=(R[SH], R[LT]))


def g_velvet(t, R):
    """Velvet: a deep pile with crushed diagonal sheen bands (ragged light mid with short highlight runs in
    the middle) and dark folds - fabric shading in wide groups, no gradient."""
    S, k, rnd = t.S, t.k, t.rnd
    nf = field(t, [(2, 1.0), (3, 0.6)], off=4)
    t.layer('pile')
    vals = {}
    for y in range(S):
        for x in range(S):
            vals[(x, y)] = math.sin(2 * math.pi * (x + y) / S) * 0.8 + (nf[(x, y)] - 0.5) * 1.6
    order = sorted(vals, key=vals.get)
    rank = {p: i / len(order) for i, p in enumerate(order)}
    for p, v in rank.items():
        t.put(*p, R[SH] if v < 0.08 else R[DK] if v < 0.3 else R[LT] if v > 0.82 else R[BS])
    clean(t)
    t.layer('sheen')
    for (x, y), v in rank.items():
        if v > 0.93 and rnd.random() < 0.6:
            streak(t, x, y, 2, R[HI], 1, -1)
    t.layer('nap')
    for _ in range(int(S * 1.2)):
        x, y = rnd.randrange(S), rnd.randrange(S)
        i = t.tone(x, y)
        if i in (BS, LT):
            streak(t, x, y, k + 1, R[i - 1], 0, 1)
    clean(t, keep=(R[HI],))


def g_canvas(t, R):
    """Canvas: a coarse plain weave. k=1: every 2x2 cell is a crossing - lit knot, two base threads, a dark
    gap; HD: 4x4 crossings where the over-thread alternates (a horizontal pill lit on its top, a vertical
    one lit on its left). Slub threads (a lighter or darker run) and a few thick spots break the grid."""
    S, k, rnd = t.S, t.k, t.rnd
    t.layer('weave')
    if k == 1:
        cell = [[LT, LT, BS, DK], [BS, BS, BS, DK], [BS, DK, LT, LT], [BS, DK, BS, BS]]
        for y in range(S):
            for x in range(S):
                t.put(x, y, R[cell[y % 4][x % 4]])
    else:
        H = [[LT, LT, LT, BS], [BS, BS, BS, DK], [BS, BS, DK, DK], [DK, DK, DK, SH]]
        V = [[LT, BS, BS, DK], [LT, BS, BS, DK], [LT, BS, DK, DK], [BS, DK, DK, SH]]
        for cy in range(0, S, 4):
            for cx in range(0, S, 4):
                pat = H if ((cx // 4) + (cy // 4)) % 2 == 0 else V
                for j in range(4):
                    for i in range(4):
                        t.put(cx + i, cy + j, R[pat[j][i]])
    t.layer('slubs')
    for i in range(3 * k):
        horiz = i % 2 == 0
        x, y = rnd.randrange(0, S, 2 * k), rnd.randrange(0, S, 2 * k)
        d = rnd.choice((-1, 1))
        for n in range(rnd.randint(3, 6) * k):
            p = (x + n, y) if horiz else (x, y + n)
            tt = t.tone(*p)
            if tt is not None and tt != SH:
                t.put(*p, R[_c(tt + d)])


def g_carpet(t, R, G, N):
    """Patterned rug: a gold diamond lattice on a red field (lit upper edge, dark lower edge on every gold
    line), a navy medallion with a cream / gold centre in each diamond, short pile marks in the red."""
    S, k, rnd = t.S, t.k, t.rnd
    t.add_ramps(G, N)
    h = S // 2
    t.layer('field')
    for y in range(S):
        for x in range(S):
            t.put(x, y, R[BS])
    for _ in range(int(S * 0.8)):
        x, y = rnd.randrange(S), rnd.randrange(S)
        streak(t, x, y, 2, R[DK] if rnd.random() < 0.6 else R[LT], 0, 1)
    t.layer('lattice')
    for y in range(S):
        for x in range(S):
            d = abs(_sw(x - h + 0.5, S) - 0) + abs(_sw(y + 0.5, S))
            e = (abs(_sw(x + 0.5, S)) + abs(_sw(y + 0.5 - h, S)))
            for dd in (d, e):
                if h - k <= dd < h + k * (1 if k == 1 else 1):
                    up = dd < h
                    t.put(x, y, G[LT] if (up and k == 2) or k == 1 else G[DK])
    for y in range(S):
        for x in range(S):
            if t.get(x, y) in (G[LT], G[DK]) and t.get(x, y + 1) == R[BS]:
                t.put(x, y + 1, R[SH])
    t.layer('medallion')
    for (cx, cy) in ((h, h), (0, 0)):
        r = 3 * k
        for y in range(-r, r + 1):
            for x in range(-r, r + 1):
                d = abs(x) + abs(y)
                if d <= r:
                    if d == r:
                        c = N[SH] if (x > 0 or y > 0) else N[DK]
                    elif d == r - 1:
                        c = N[LT] if (x <= 0 and y <= 0) else N[BS]
                    else:
                        c = N[BS]
                    if k == 2 and d == 3:
                        c = N[DK]
                    if d <= (1 if k == 1 else 2):
                        c = G[HI] if (x, y) == (0, 0) or (k == 2 and d == 1 and x <= 0 and y <= 0) else G[BS]
                        if k == 2 and d == 2 and (x > 0 or y > 0) and x + y > 0:
                            c = G[DK]
                    t.put(cx + x - (1 if k == 1 else 0) + (0 if cx else 0), cy + y, c)
    clean(t, keep=(G[HI], R[LT]))


# ------------------------------------------------------------------ others
def g_glass(t, R, tint=None):
    """Glass pane: a light frame (lit top / left, darker bottom / right), the clear middle left empty (the
    world shows through - no semi-transparent pixels), diagonal streaks of highlight in the upper left and
    a short one in the lower right. tint = a ramp that fills the pane as smoky glass instead (opaque: dark
    clouds, lighter wisps). fill() hides the frame, so a filled shape is one pane with streaks."""
    S, k, rnd = t.S, t.k, t.rnd
    if tint:
        t.add_ramps(tint)
        t.layer('tint')
        f = field(t, [(1, 1.0), (2, 0.6), (3, 0.3)])
        for (x, y), v in f.items():
            t.put(x, y, tint[DK] if v < 0.55 else tint[BS] if v < 0.9 else tint[LT])
        clean(t)
    t.layer('frame')
    for y in range(S):
        for x in range(S):
            e = min(x, y, S - 1 - x, S - 1 - y)
            if e >= k:
                continue
            lit = (x == e or y == e) and not (S - 1 - x == e or S - 1 - y == e)
            if (x, y) in ((S - 1, 0), (0, S - 1)):
                c = R[BS]
            elif e == 0:
                c = R[HI] if lit else R[DK]
            else:
                c = R[LT] if lit else R[BS]
            t.put(x, y, c)
    t.layer('streaks')
    hi = R[HI] if not tint else tint[HI]
    lt = R[LT] if not tint else tint[LT]
    for (x0, y0, n, c) in ((3, 7, 4, hi), (3, 10, 2, lt), (10, 13, 3, lt)) if k == 1 else \
            ((5, 14, 9, hi), (6, 15, 8, lt), (5, 20, 4, hi), (20, 27, 6, lt), (22, 27, 3, hi)):
        for i in range(n):
            t.put(x0 + i, y0 - i, c)


def g_water(t, R, frame=0):
    """Water: horizontally stretched swells - light crests with a highlight run on top, dark troughs under
    them; frame shifts the waves (8 frames loop)."""
    S, k, rnd = t.S, t.k, t.rnd
    waves = []
    r2 = random.Random(t.seed)
    for f, a in ((1, 1.0), (2, 0.7), (3, 0.5), (4, 0.35)) + (((6, 0.25),) if k == 2 else ()):
        for _ in range(2):
            fx, fy = r2.randint(-1, 1), r2.choice((f, -f))
            waves.append((fx, fy, a, r2.uniform(0, 6.3), r2.choice((-1, 1))))
    vals = {(x, y): sum(a * math.sin(2 * math.pi * (fx * x + fy * y) / S + ph + d * frame * 2 * math.pi / 8 * (abs(fx) > 0 or 1))
                        for fx, fy, a, ph, d in waves) for y in range(S) for x in range(S)}
    order = sorted(vals, key=vals.get)
    rank = {p: i / len(order) for i, p in enumerate(order)}
    t.layer('water')
    for p, v in rank.items():
        t.put(*p, R[DK] if v < 0.22 else R[LT] if v > 0.84 else R[BS])
    clean(t)
    t.layer('crests')
    comp = t.composed()
    for (x, y), c in comp.items():
        if c == R[LT] and comp[t.w(x, y - 1)] != R[LT] and comp[t.w(x + 1, y)] == R[LT] and comp[t.w(x - 1, y)] == R[LT]:
            t.put(x, y, R[HI])
        if c == R[DK] and (rank[(x, y)] < (0.035 if k == 2 else 0.0) or
                           (comp[t.w(x, y - 1)] == R[BS] and rank[(x, y)] < 0.08)):
            t.put(x, y, R[SH])
    clean(t, keep=(R[HI],))


def g_lava(t, R, frame=0):
    """Lava: molten channels glow from orange through yellow to a pale core; dark crust plates float on it
    (lit top-left rim on each plate). Saturated and contrasty - lava is a light source."""
    S, k, rnd = t.S, t.k, t.rnd
    f = field(t, [(1, 1.0), (2, 0.8), (3, 0.6)] + ([(5, 0.35)] if k == 2 else []), off=frame * 13)
    t.layer('melt')
    for p, v in f.items():
        t.put(*p, R[SH] if v < 0.2 else R[DK] if v < 0.3 else R[BS] if v < 0.62 else R[LT] if v < 0.86 else R[HI])
    clean(t)
    comp = t.composed()
    t.layer('crust')
    for (x, y), c in comp.items():
        if c == R[SH] and (comp[t.w(x - 1, y)] != R[SH] or comp[t.w(x, y - 1)] != R[SH]):
            t.put(x, y, R[DK])
        if c == R[SH] and comp[t.w(x + 1, y)] == R[SH] and comp[t.w(x, y + 1)] == R[SH] and (x * 7 + y * 3) % 11 == 0:
            t.put(x, y, R[O])
    clean(t, keep=(R[HI],))


def g_gel(t, R, bubbles=True, drips=False, swirl=False):
    """Slime / honey block: a glossy shell (lit top / left rim, a glint, darker bottom / right) around a
    denser inner cube seen through it (dark, lit on its own top-left edge); honey drips from the shell."""
    S, k, rnd = t.S, t.k, t.rnd
    t.layer('shell')
    for y in range(S):
        for x in range(S):
            e = min(x, y, S - 1 - x, S - 1 - y)
            lit = (x == e or y == e) and not (S - 1 - x == e or S - 1 - y == e)
            if e < k:
                c = R[LT] if lit else R[DK]
            else:
                c = R[BS]
            t.put(x, y, c)
    a, b = 4 * k, S - 4 * k
    t.layer('core')
    for y in range(a, b):
        for x in range(a, b):
            e = min(x - a, y - a, b - 1 - x, b - 1 - y)
            lit = (x - a == e or y - a == e) and not (b - 1 - x == e or b - 1 - y == e)
            c = R[DK]
            if e < k:
                c = R[BS] if lit else R[SH]
            t.put(x, y, c)
    if drips:
        for i in range(3 + k):
            x = a + 1 + rnd.randrange(b - a - 3)
            n = rnd.randint(1, 3) * k
            for j in range(n):
                t.put(x, a + j, R[BS])
                if k == 2:
                    t.put(x + 1, a + j, R[BS] if j < n - 1 else R[DK])
            t.put(x, a + n, R[LT])
    t.layer('gloss')
    for (x, y, n) in ((k + 1, k + 1, 2 * k), ):
        streak(t, x, y, n, R[HI])
        streak(t, x, y + 1, max(1, n - k), R[HI] if k == 2 else R[LT], 1, 0) if k == 2 else t.put(x, y + 1, R[HI])
    t.put(S - k - 2, S - k - 2, R[LT])
    if k == 2:
        t.put(a + 2, a + 2, R[BS])
        t.put(a + 3, a + 2, R[BS])
        t.put(a + 2, a + 3, R[BS])
    if swirl:                                              # honey: a slow lit swirl in the core
        for i in range(2 * k + 1):
            t.put(a + k + i, b - k - 2 - i // 2, R[BS])
    if bubbles and k == 2:
        for (x, y) in ((S - 7, 4), (5, S - 8), (S - 6, S - 12)):
            for dx, dy, c in ((0, 0, R[LT]), (1, 0, R[LT]), (0, 1, R[LT]), (1, 1, R[DK])):
                t.put(x + dx, y + dy, c)
    clean(t, keep=(R[HI], R[LT], R[BS]))


def g_hay(t, R, T):
    """Hay bale side: vertical straw (light and dark strands of mixed length), two binding ties across it -
    each lit on its top row, dark below, the straw pinched and shadowed under it."""
    S, k, rnd = t.S, t.k, t.rnd
    t.add_ramps(T)
    t.layer('straw')
    for x in range(S):
        y = rnd.randrange(S)
        while y < S + S:
            n = rnd.randint(2, 5) * k
            r_ = rnd.random()
            c = R[LT] if r_ < 0.3 else R[DK] if r_ < 0.55 else R[BS]
            if k == 2 and r_ < 0.06:
                c = R[HI]
            streak(t, x, y, n, c, 0, 1)
            y += n
    t.layer('ties')
    for ty in (S // 4 - k, 3 * S // 4 - k):
        for x in range(S):
            for j in range(2 * k):
                t.put(x, ty + j, T[LT] if j == 0 else T[DK] if j == 2 * k - 1 else T[BS])
            t.put(x, ty - 1, R[DK] if x % 3 else R[BS])
            t.put(x, ty + 2 * k, R[SH] if (x + ty) % 4 else R[DK])
            if k == 2 and x % 5 == 0:
                t.put(x, ty + 1, T[DK])
    clean(t, keep=(R[HI], R[LT], R[DK], R[BS], T[DK]))


def g_bookshelf(t, Rw):
    """Bookshelf: two shelves of book spines on oak boards - books of six ramps and several heights
    (lit left side, dark right side, a gold or cream band, a title block at HD), the dark back of the shelf
    showing over the shorter ones, each book shadowing its right neighbour's gap."""
    S, k, rnd = t.S, t.k, t.rnd
    Gd = RAMPS['carpet_gold']
    books = [RAMPS[b] for b in BOOKS]
    t.add_ramps(Gd, *books)
    t.layer('shelf')
    zones = []
    if k == 1:
        rows = {0: LT, 7: LT, 8: DK, 15: DK}
        zones = [(1, 6), (9, 6)]
    else:
        rows = {0: LT, 1: BS, 14: LT, 15: BS, 16: DK, 30: DK, 31: SH}
        zones = [(2, 12), (17, 13)]
    for y in range(S):
        for x in range(S):
            if y in rows:
                t.put(x, y, Rw[rows[y]])
            else:
                t.put(x, y, Rw[O] if k == 1 or x % 7 else Rw[SH])
    t.layer('grain')
    for y in rows:
        if rows[y] in (LT, BS) and k == 2:
            x = rnd.randrange(S)
            streak(t, x, y, 5, Rw[BS] if rows[y] == LT else Rw[DK])
    t.layer('books')
    for (y0, hz) in zones:
        x = 0
        while x < S:
            w = rnd.choice((2, 2, 3)) if k == 1 else rnd.choice((3, 3, 4, 5))
            w = min(w, S - x)
            if w <= 0:
                break
            gap = rnd.random() < 0.12
            if gap:
                x += w
                continue
            Rb = rnd.choice(books)
            h = hz - rnd.choice((0, 0, 1, 2)) * k
            top = y0 + hz - h
            for j in range(h):
                for i in range(w):
                    tone = LT if (i == 0 and w > 1) else DK if i == w - 1 and w > 1 else BS
                    t.put(x + i, top + j, Rb[tone])
            band_y = top + 2
            if h > 3 * k:
                for i in range(w):
                    t.put(x + i, band_y, Gd[LT] if (i == 0 and k == 2) else Gd[BS])
                    if k == 2:
                        t.put(x + i, band_y + 1, Gd[BS] if i < w - 1 else Gd[DK])
                        t.put(x + i, top + h - 3, Gd[BS] if i < w - 1 else Gd[DK])
            if k == 2 and w >= 3 and h > 9:                    # a title label between the bands
                for j in range(3):
                    for i in range(1, w - 1):
                        t.put(x + i, top + 6 + j, RAMPS['book_cream'][LT if j == 0 else BS])
            t.put(x + w, y0 + hz - 1, Rw[O]) if t.get(x + w, y0 + hz - 1) == Rw[SH] else None
            x += w
    clean(t, keep=[b[HI] for b in books] + [Gd[LT], Gd[BS], Gd[DK]] + [b[LT] for b in books] + [b[DK] for b in books]
          + [b[BS] for b in books])


def g_terracotta(t, R):
    """Terracotta: fired clay - broad gentle blotches (matte, low contrast) and a few tiny pores."""
    S, k, rnd = t.S, t.k, t.rnd
    g_stone(t, R, name='clay', dark=0.22, light=0.18, freqs=[(1, 1.0), (2, 0.7), (3, 0.5)], dents=False)
    t.layer('pores')
    for (x, y) in spots(t, 3 * k, 5 * k):
        t.put(x, y, R[SH])
        t.put(x + 1, y, R[DK])
        t.put(x + 1, y + 1, R[LT])
    clean(t, keep=(R[SH], R[LT]))


def g_parchment(t, R):
    """Parchment: cream with short horizontal fibres (light and dark), faint stains, a few dark flecks."""
    S, k, rnd = t.S, t.k, t.rnd
    g_stone(t, R, name='paper', dark=0.14, light=0.12, freqs=[(1, 1.0), (2, 0.7), (3, 0.4)], dents=False)
    t.layer('fibres')
    for _ in range(int(S * 0.9)):
        x, y = rnd.randrange(S), rnd.randrange(S)
        streak(t, x, y, rnd.randint(2, 4) * k, R[LT] if rnd.random() < 0.5 else R[DK])
    for (x, y) in spots(t, 2 * k, 6 * k):
        t.put(x, y, R[SH])
        t.put(x + 1, y, R[DK])
    clean(t, keep=(R[SH],))


def g_bone(t, R):
    """Bone block side: ivory with long vertical fibres, pores along them (small pits) and a fine crack."""
    S, k, rnd = t.S, t.k, t.rnd
    f = field(t, [(1, 1.0), (2, 0.6), (3, 0.4)], aniso=(1, 0.34))
    t.layer('bone')
    for p, v in f.items():
        t.put(*p, R[DK] if v < 0.2 else R[LT] if v > 0.8 else R[BS])
    clean(t)
    t.layer('fibres')
    for x in range(0, S, 3 * k):
        xx = x + rnd.randint(0, k)
        y = rnd.randrange(S)
        for _ in range(2):
            n = rnd.randint(4, 8) * k
            streak(t, xx, y, n, R[DK], 0, 1)
            streak(t, xx + 1, y, n, R[LT], 0, 1)
            y += n + rnd.randint(2, 5) * k
    t.layer('pores')
    for (x, y) in spots(t, 4 * k, 4 * k):
        pit(t, {(0, 0), (0, 1)} if k == 1 else {(0, 0), (1, 0), (0, 1), (1, 1), (0, 2), (1, 2)}, x, y, R, BS)
    clean(t, keep=(R[SH], R[LT]))


def g_moss(t, R):
    """Moss block: dense springy clumps - small lumps lit on the top-left with dark gaps between, light tips."""
    g_lumps(t, R, grid=5, contrast=1, joint=SH, glints=True, tones=(DK, BS, BS, LT))


_LEAF_HD = [                                       # '1' leaf, 'r' midrib - pointed leaves at four angles
    ['..1..', '.111.', '11r11', '11r11', '11r11', '.1r1.', '..1..'],
    ['11....', '1r11..', '.1r11.', '.11r1.', '..11r1', '...111'],
    ['....11', '..11r1', '.11r1.', '.1r11.', '1r11..', '111...'],
]
_LEAF_HD.append([''.join(r[i] for r in _LEAF_HD[0]) for i in range(5)])          # horizontal = transposed


def _leaf(rnd, k, needle=False):
    """One leaf as {(x, y): tone offset}. k=1: a 5-7 px blob (lit top-left rim, dark bottom-right rim);
    HD: a pointed leaf from _LEAF_HD (the half above / left of the midrib lit, the other half base, a dark
    rim on the bottom-right, the midrib one step down) or a spruce needle tuft (a 3 px diagonal stroke:
    lit upper side, base core, dark lower side)."""
    if k == 1:
        b = blob(rnd, rnd.randint(3, 5), wide=0.7, tall=1.5) if needle else blob(rnd, rnd.randint(5, 7), wide=1.25)
        out = {}
        for (x, y) in b:
            tl = (x - 1, y) not in b or (x, y - 1) not in b
            br = (x + 1, y) not in b or (x, y + 1) not in b
            out[(x, y)] = 1 if tl and not br else -1 if br and not tl else 0
        return out
    if needle:                                   # a tuft of needles: a narrow upright clump
        b = blob(rnd, rnd.randint(7, 11), wide=0.6, tall=1.7)
        out = {}
        for (x, y) in b:
            tl = (x - 1, y) not in b or (x, y - 1) not in b
            br = (x + 1, y) not in b or (x, y + 1) not in b
            out[(x, y)] = 1 if tl and not br else -1 if br and not tl else 0
        return out
    rows = rnd.choice(_LEAF_HD)
    pts = {(x, y): ch for y, r in enumerate(rows) for x, ch in enumerate(r) if ch != '.'}
    rib = {p for p, ch in pts.items() if ch == 'r'}
    out = {}
    for (x, y) in pts:
        if (x, y) in rib:
            out[(x, y)] = -1
            continue
        col = [ry for (rx, ry) in rib if rx == x]
        row = [rx for (rx, ry) in rib if ry == y]
        lit = (y < min(col)) if col else (x < min(row)) if row else (x + y < len(rows))
        br = (x + 1, y) not in pts or (x, y + 1) not in pts
        tl = (x - 1, y) not in pts or (x, y - 1) not in pts
        out[(x, y)] = (1 if lit else 0) - (1 if br and not tl else 0)
    return out


def g_leaves(t, R, kind='broad', R2=None, density=1.0, cover=None):
    """Leaves with holes. Leaves overlap in two passes - deeper, darker ones first, then the top ones -
    each lit on its top-left half / rim and dark on its bottom-right rim, each casting a one-step shadow
    down-right on the leaves under it; gaps are filled until ~`cover` of the tile is leaf, the rest stays
    transparent. kind: broad (oak, birch), needle (spruce: small upright needle tufts, darker and
    bluer), blossom (cherry: pink leaves and five-petal flowers with a yellow eye)."""
    S, k, rnd = t.S, t.k, t.rnd
    cover = cover or (0.8 if k == 1 else 0.74)
    if R2:
        t.add_ramps(R2)
    t.layer('leaves')
    covered = set()
    needle = kind == 'needle'

    def put_leaf(x, y, shape, base):
        for (i, j) in shape:                          # cast shadow first, on what is already there
            q = t.w(x + i + 1, y + j + 1)
            if q in covered and (i + 1, j + 1) not in shape:
                t.shift(*q, -1, lo=1)
        for (i, j), off in shape.items():
            t.put(x + i, y + j, R[_c(max(1, base + off))])
            covered.add(t.w(x + i, y + j))

    step = (2 if needle else 3) if k == 1 else (4 if needle else 6)
    for layer_base, dens in (((DK, BS), 0.55 * density), ((BS, BS, LT), 0.75 * density)):
        cells = [(gx, gy) for gy in range(0, S, step) for gx in range(0, S, step)]
        rnd.shuffle(cells)
        for (gx, gy) in cells:
            if rnd.random() > dens:
                continue
            x, y = gx + rnd.randint(0, step - 1), gy + rnd.randint(0, step - 1)
            put_leaf(x, y, _leaf(rnd, k, needle), rnd.choice(layer_base))
    for _ in range(300):                                     # close the big gaps, keep small holes
        if len(covered) >= cover * S * S:
            break
        free = [(x, y) for y in range(S) for x in range(S) if (x, y) not in covered
                and sum(t.w(x + dx, y + dy) not in covered for dx, dy in N8) >= 7]
        if not free:
            break
        x, y = rnd.choice(free)
        shape = _leaf(rnd, k, needle)
        cx = sorted(shape)[len(shape) // 2]
        put_leaf(x - cx[0], y - cx[1], shape, rnd.choice((DK, BS)))
    if kind == 'blossom' and R2:
        t.layer('blossoms')
        for (x, y) in spots(t, 5 * k, 4 * k):
            if k == 1:
                for dx, dy, i in ((0, -1, HI), (-1, 0, HI), (1, 0, LT), (0, 1, LT)):
                    t.put(x + dx, y + dy, R[i])
                t.put(x, y, R2[LT])
            else:
                for dx, dy, c in ((0, -2, R[HI]), (1, -2, R[LT]), (-2, -1, R[HI]), (-1, -1, R[LT]), (0, -1, R[LT]),
                                  (1, -1, R[LT]), (2, -1, R[BS]), (-2, 0, R[LT]), (-1, 0, R[LT]), (0, 0, R2[HI]),
                                  (1, 0, R2[BS]), (2, 0, R[BS]), (-1, 1, R[BS]), (0, 1, R2[DK]), (1, 1, R[DK]),
                                  (2, 1, R[DK]), (-1, 2, R[DK]), (0, 2, R[DK]), (1, 2, R[SH])):
                    t.put(x + dx, y + dy, c)
    clean(t, keep=(R[HI],) + ((R2[LT], R2[HI], R2[BS], R2[DK]) if R2 else ()))


# ------------------------------------------------------------------ building extras
def _bevel_ring(t, R, joint=SH):
    """A block-face bevel over whatever texture is there: the top / left band one step lighter, the bottom /
    right band one step darker, the joint on the right and bottom (HD: the shadowed row first)."""
    S, k = t.S, t.k
    fw = S - k
    t.layer('bevel')
    for y in range(S):
        for x in range(S):
            if x >= fw or y >= fw:
                inner = k == 2 and (x == fw or y == fw)
                t.put(x, y, R[_c(joint - 1)] if inner else R[joint])
            elif (y < k or x < k) and not (x >= fw - k and y >= k) and not (y >= fw - k and x >= k):
                t.shift(x, y, 1)
            elif y >= fw - k or x >= fw - k:
                t.shift(x, y, -1)


def g_polished(t, R, groups=None, R2=None):
    """Polished stone: the stone's own grains, calmer, cut into a block face (bevel ring + joint), with a
    few diagonal polish streaks on the upper left."""
    S, k, rnd = t.S, t.k, t.rnd
    if groups:
        g_speckled(t, R, [(g[0], g[1], max(1, g[2] // 2)) + g[3:] for g in groups], base_field=(0.08, 0.06))
    else:
        g_stone(t, R, dark=0.1, light=0.08, chips=k, cracks=0)
    _bevel_ring(t, R)
    t.layer('polish')
    for (x0, y0, n) in ((3, 5, 3),) if k == 1 else ((5, 11, 5), (7, 12, 3)):
        for i in range(n):
            t.put(x0 + i, y0 - i, R[HI] if i < n - 1 else R[LT])


def g_chiseled(t, R):
    """Chiseled stone: a block face with a carved square ring (shadowed top / left wall, lit far wall) and a
    round boss in the middle (lit top-left, dark bottom-right, a highlight)."""
    S, k, rnd = t.S, t.k, t.rnd
    g_stone(t, R, dark=0.12, light=0.08, chips=0, cracks=0)
    _bevel_ring(t, R)
    t.layer('carving')
    a, b = 3 * k, S - 4 * k
    for y in range(a, b + 1):
        for x in range(a, b + 1):
            if x in (a, b) or y in (a, b):
                t.put(x, y, R[SH] if (x == a or y == a) and not (x == b or y == b) else R[LT])
    for y in range(a + 1, b):
        for x in range(a + 1, b):
            if x == a + 1 or y == a + 1:
                t.shift(x, y, -1)
    c = (S - k) / 2
    boss = {(x, y) for y in range(S) for x in range(S) if (x + 0.5 - c) ** 2 + (y + 0.5 - c) ** 2 <= (2.6 * k) ** 2}
    lump(t, boss, 0, 0, R, BS, hi=k, cast=1)


def g_farmland(t, R):
    """Tilled soil seen from above: moist dark dirt in raised ridges (lit top row) and furrows (a shadow row,
    then the darker floor), clods along the ridges."""
    S, k, rnd = t.S, t.k, t.rnd
    g_dirt(t, R, clods=0.6, pebbles=0.4)
    t.layer('furrows')
    for r in range(4):
        y0 = r * S // 4
        for x in range(S):
            w = 1 if (x * 3 + r * 5) % 11 < 2 else 0
            t.put(x, y0 + w, R[LT])
            if k == 2:
                t.put(x, y0 + w + 1, R[LT] if (x + r) % 5 else R[BS])
            t.put(x, y0 + S // 4 - k - 1 + w, R[SH])
            if k == 2:
                t.put(x, y0 + S // 4 - 2 + w, R[DK])


def g_roots(t, R, Rr):
    """Rooted dirt: dirt with pale roots wandering down through it (a lit root line, a dark pixel on its
    right where it shades the soil)."""
    S, k, rnd = t.S, t.k, t.rnd
    t.add_ramps(Rr)
    g_dirt(t, R)
    t.layer('roots')
    for i in range(2 + k):
        x, y = rnd.randrange(S), rnd.randrange(S)
        pts = wander(t, x, y, rnd.randint(6, 10) * k, Rr[LT], main=(0, 1), side=0.45)
        for (px, py) in (pts[len(pts) * 2 // 3:] if k == 2 else ()):
            t.put(px, py, Rr[BS])
        for (px, py) in pts:
            if t.get(px + 1, py) not in (Rr[BS], Rr[LT]):
                t.shift(px + 1, py, -1)
    clean(t, keep=(Rr[LT], Rr[BS], R[SH]))


def g_stripped(t, R):
    """Stripped log side: bare wood with long vertical fibres (light and dark runs), two shallow grooves."""
    g_bark(t, R, furrows=2, amp=0.5, plates=0.0, streaks=1.6, deep=DK, light=0.7)


def g_concrete(t, R):
    """Concrete: a flat, smooth colour - faint broad patches and a few tiny pores, nothing else."""
    S, k, rnd = t.S, t.k, t.rnd
    f = field(t, [(4, 1.0), (6, 0.6)] + ([(10, 0.4)] if t.k == 2 else []))
    t.layer('concrete')
    for p, v in f.items():
        t.put(*p, R[DK] if v < 0.09 else R[LT] if v > 0.96 else R[BS])
    clean(t)
    t.layer('pores')
    for (x, y) in spots(t, k, 8 * k):
        t.put(x, y, R[DK])
        t.put(x + 1, y, R[DK])
    clean(t)


def g_bars(t, R):
    """Iron bars: round vertical bars (highlight and light on the left, dark on the right) held by two
    flat cross bands; the rest is open (transparent)."""
    S, k, rnd = t.S, t.k, t.rnd
    t.layer('bars')
    bw = 2 * k
    for x0 in (S // 4 - k, 3 * S // 4 - k):
        for y in range(S):
            for i in range(bw):
                t.put(x0 + i, y, R[(HI, DK) [i] if k == 1 else (LT, HI, BS, DK)[i]])
    t.layer('bands')
    for y0 in (2 * k, S - 4 * k):
        for x in range(S):
            for j in range(k + 1 if k == 2 else 2):
                t.put(x, y0 + j, R[LT] if j == 0 else R[SH] if j == (k if k == 2 else 1) else R[BS])
        for x0 in (S // 4 - k, 3 * S // 4 - k):           # rivets where band and bar cross
            t.put(x0, y0, R[HI])


def g_ladder(t, R):
    """Ladder: two side rails and four rungs of wood (lit top / left, dark bottom / right, a nail at each
    end); everything else open."""
    S, k, rnd = t.S, t.k, t.rnd
    t.layer('rails')
    for x0 in (k, S - 3 * k):
        for y in range(S):
            for i in range(2 * k):
                t.put(x0 + i, y, R[LT] if i == 0 else R[DK] if i == 2 * k - 1 else R[BS])
    t.layer('rungs')
    for r in range(4):
        y0 = r * S // 4 + k
        for x in range(k, S - k):
            for j in range(2 * k):
                t.put(x, y0 + j, R[LT] if j == 0 else R[DK] if j == 2 * k - 1 else R[BS])
            t.put(x, y0 + 2 * k, R[SH]) if 3 * k <= x < S - 3 * k else None
        for x0 in (k + (k - 1), S - 2 * k - 1):
            t.put(x0, y0 + k - 1 + (k == 1), R[O])


def g_shingles(t, R, style='wood', h=4, w=4):
    """Roofing seen face-on, rows overlapping downward: each row starts in the shadow of the row above
    (shadow row, HD + a dark row), the shingle faces are lit on the left, dark on the right, their lower
    edge dark; style 'wood' = rectangular shingles of varied width and tone with vertical grain, 'scale' =
    fish-scale tiles with round bottoms (clay, slate)."""
    S, k, rnd = t.S, t.k, t.rnd
    grain = style == 'wood'
    if style == 'scale' and k == 1:
        style, h = 'wood', 4                         # 16 px is too small for a round bottom: staggered tiles
    hh, ww = h * k, w * k
    rows = S // hh
    owner, local, tone = {}, {}, {}
    sid = 0
    wrapped = []
    for r in reversed(range(rows)):
        y0 = r * hh
        x = (ww // 2) * (r % 2)
        while x < S:
            wd = ww if style == 'scale' else ww + (rnd.choice((-k, 0, 0, k)) if grain else 0)
            sid += 1
            tone[sid] = rnd.choice((BS, BS, DK, LT) if grain else (BS, BS, BS, DK, LT))
            depth = hh + (ww // 2 if style == 'scale' else k)
            for j in range(depth):
                for i in range(wd):
                    if style == 'scale' and j >= hh:
                        if (i + 0.5 - wd / 2) ** 2 + (j - hh + 0.5) ** 2 > (wd / 2) ** 2:
                            continue
                    p = t.w(x + i, y0 + j)
                    owner[p], local[p] = sid, (i, j, wd)
                    if y0 + j >= S:
                        wrapped.append((p, sid, (i, j, wd)))
            x += wd
    for p, o, loc in wrapped:                         # the bottom row hangs over row 0 across the wrap
        owner[p], local[p] = o, loc
    t.layer('roof')
    for (x, y), o in owner.items():
        i, j, wd = local[(x, y)]
        up, dn = owner.get(t.w(x, y - 1)), owner.get(t.w(x, y + 1))
        lf, rt = owner.get(t.w(x - 1, y)), owner.get(t.w(x + 1, y))
        b = tone[o]
        if up != o:
            c = SH
        elif k == 2 and owner.get(t.w(x, y - 2)) != o:
            c = DK
        elif dn != o:
            c = (LT if i < wd // 2 else DK) if style == 'scale' else DK
        elif lf != o:
            c = b + 1
        elif rt != o:
            c = b - 1
        else:
            c = b
        if style == 'scale' and dn != o and (rt != o or lf != o):
            c = SH
        t.put(x, y, R[_c(c)])
    if grain:
        t.layer('grain')
        for _ in range(int(S * 0.6 * k)):
            x, y = rnd.randrange(S), rnd.randrange(S)
            o = owner[(x, y)]
            if all(owner.get(t.w(x, y + j)) == o for j in range(k + 1)) and t.tone(x, y) in (BS, LT, DK):
                streak(t, x, y, k + 1, R[_c(t.tone(x, y) - 1)], 0, 1)
    clean(t, keep=(R[LT], R[SH]))


def g_thatch(t, R):
    """Thatch: rows of straw bundles - strands of light, base and dark run down each row and hang over the
    next by a ragged 1-2 px, each row starts in the shadow of the one above."""
    S, k, rnd = t.S, t.k, t.rnd
    hh = 4 * k
    t.layer('straw')
    for r in reversed(range(S // hh)):
        y0 = r * hh
        for x in range(S):
            ln = hh + rnd.choice((0, 1, 1, 2)) * k
            c = rnd.choice((LT, BS, BS, DK))
            for j in range(ln):
                tone = SH if j == 0 else (DK if (k == 2 and j == 1) else c)
                if j >= hh:
                    tone = c - 1 if c > DK else c
                t.put(x, y0 + j, R[_c(tone)])
            if k == 2 and c == LT and rnd.random() < 0.3:
                t.put(x, y0 + 2, R[HI])
    clean(t, keep=(R[HI], R[SH]))


# ------------------------------------------------------------------ the catalog
MATERIALS = {}                     # name -> {family, gen, ramps (keys), params, main}
FAMILIES = (('wood', 'Woods: planks, logs, log tops, stripped logs'), ('stone', 'Stones'), ('soil', 'Soils'),
            ('metal', 'Metals'), ('gem', 'Gem blocks'), ('ore', 'Ores'), ('fabric', 'Fabrics'),
            ('other', 'Others'), ('build', 'Building: roofs, bars, ladder'), ('dyed', 'Dyed blocks: concrete, terracotta'))


def _mat(name, family, gen, ramps, main=None, fill_hide=(), edge=(SH, O), **params):
    """edge = (tone of the outline on the lit top / left, tone elsewhere) used by fill()."""
    MATERIALS[name] = {'family': family, 'gen': gen, 'ramps': list(ramps), 'params': params,
                       'main': main or ramps[0], 'fill_hide': fill_hide, 'edge': edge}


WOODS = {
    #           planks params                                     bark params
    'oak': (dict(grain=1.0, light_grain=0.2, knots=1), dict(furrows=4, amp=1, plates=0.3)),
    'spruce': (dict(grain=1.3, light_grain=0.1, knots=1, dots=2), dict(furrows=5, amp=0.6, plates=0.5)),
    'birch': (dict(grain=0.6, light_grain=0.4, knots=0, dots=3), None),
    'jungle': (dict(grain=1.5, light_grain=0.35, knots=0, wavy=0.6), dict(furrows=4, amp=1, plates=0.4)),
    'acacia': (dict(grain=1.1, light_grain=0.45, knots=1), dict(furrows=3, amp=1.4, plates=0.6, light=0.8)),
    'dark_oak': (dict(grain=1.2, light_grain=0.55, knots=1), dict(furrows=4, amp=1, plates=0.4, light=0.3)),
    'mangrove': (dict(grain=1.3, light_grain=0.3, knots=0, wavy=0.8), dict(furrows=6, amp=0.5, plates=0.1, streaks=1.2)),
    'cherry': (dict(grain=0.7, light_grain=0.5, knots=0), dict(furrows=2, amp=0.5, plates=0.7, streaks=0.3, light=0.9)),
    'crimson': (dict(grain=1.0, light_grain=0.3, knots=0, wavy=0.7), None),
    'warped': (dict(grain=1.0, light_grain=0.3, knots=0, wavy=0.7), None),
    'bamboo': (dict(grain=1.4, light_grain=0.3, knots=0, vertical=True, nodes=True, wavy=0.0,
                    joints=(0.3, 0.75, 0.1, 0.55)), None),
}


def _jungle_moss(t):
    M = RAMPS['jungle_moss']
    t.add_ramps(M)
    t.layer('moss')
    for (x, y) in spots(t, 2 * t.k, 6 * t.k):
        lump(t, blob(t.rnd, (3 if t.k == 1 else 9), wide=0.8, tall=1.4), x, y, M, BS, hi=t.k - 1, cast=1)


def _cherry_lenticels(t):
    R = RAMPS['cherry_bark']
    t.layer('lenticels')
    for (x, y) in spots(t, 6 * t.k, 3 * t.k):
        streak(t, x, y, 2 * t.k + t.rnd.randint(0, t.k), R[HI] if t.k == 2 else R[LT])
        streak(t, x, y + 1, 2 * t.k, R[SH])


for _w, (_pp, _bp) in WOODS.items():
    _mat(f'{_w}_planks', 'wood', g_planks, [f'{_w}_planks'], **_pp)
    if _w == 'birch':
        _mat('birch_log', 'wood', g_birch_bark, ['birch_bark', 'birch_mark'])
    elif _w in ('crimson', 'warped'):
        _mat(f'{_w}_stem', 'wood', g_stem, [f'{_w}_bark', f'{_w}_glow'])
    elif _w == 'bamboo':
        _mat('bamboo_block', 'wood', g_bamboo_block, ['bamboo_bark', 'bamboo_node'])
    else:
        ov = {'jungle': _jungle_moss, 'cherry': _cherry_lenticels}.get(_w)
        _mat(f'{_w}_log', 'wood', g_bark, [f'{_w}_bark'], overlay=ov, **_bp)
    top = {'crimson': 'crimson_stem_top', 'warped': 'warped_stem_top', 'bamboo': 'bamboo_block_top'}.get(_w, f'{_w}_log_top')
    _mat(top, 'wood', g_log_top, [f'{_w}_planks', f'{_w}_bark'])


def _quartz_inner(t, x0, y0, w, h):
    R = RAMPS['quartz']
    k, rnd = t.k, t.rnd
    for i in range(1 + k):
        wander(t, x0 + rnd.randint(2 * k, w - 3 * k), y0 + 2 * k, rnd.randint(3, 6) * k, R[DK], main=(1, 1), side=0.0)


def _purpur_inner(t, x0, y0, w, h):
    R = RAMPS['purpur']
    k = t.k
    for i in range(k + 1, w - k - 1):
        if (i + x0) % (3 * k) == 0:
            t.put(x0 + i, y0 + h - k - 1 - (k - 1), R[DK])


_stone_tbl = [
    ('stone', g_stone, ['stone'], {}),
    ('cobblestone', g_cobble, ['cobble', 'gravel2'], {}),
    ('mossy_cobblestone', g_cobble, ['cobble', 'gravel2', 'moss'], {'mossy': 'moss'}),
    ('stone_bricks', g_bricks, ['stone_brick'], {'rows': 2, 'length': 16, 'offset': 8, 'chips': 0.4}),
    ('mossy_stone_bricks', g_bricks, ['stone_brick', 'moss'], {'rows': 2, 'length': 16, 'offset': 8, 'mossy': 'moss'}),
    ('cracked_stone_bricks', g_bricks, ['stone_brick'], {'rows': 2, 'length': 16, 'offset': 8, 'cracked': 2, 'chips': 0.9}),
    ('granite', g_speckled, ['granite'], {'groups': 'granite'}),
    ('diorite', g_speckled, ['diorite', 'stone'], {'groups': 'diorite'}),
    ('andesite', g_speckled, ['andesite'], {'groups': 'andesite'}),
    ('deepslate', g_deepslate, ['deepslate'], {}),
    ('cobbled_deepslate', g_cobble, ['deepslate'], {'grid': 4, 'deep': True, 'tones': (DK, BS, BS, LT)}),
    ('tuff', g_speckled, ['tuff'], {'groups': 'tuff'}),
    ('calcite', g_speckled, ['calcite'], {'groups': 'calcite'}),
    ('blackstone', g_speckled, ['blackstone'], {'groups': 'blackstone', 'cracks': 1}),
    ('sandstone', g_strata, ['sandstone'], {'bands': (3, 5), 'pits': 2}),
    ('red_sandstone', g_strata, ['red_sandstone'], {'bands': (3, 5), 'pits': 2}),
    ('bricks', g_bricks, ['brick', 'mortar'], {'rows': 4, 'length': 8, 'offset': 4, 'var': (DK, BS, BS, LT), 'specks': 1}),
    ('mud_bricks', g_bricks, ['mud_brick', 'mud_mortar'], {'rows': 4, 'length': 8, 'offset': 4, 'var': (BS, BS, LT), 'texture': 1.0}),
    ('prismarine', g_facets, ['prismarine', 'prismarine2'], {'grid': 4, 'glints': 1, 'R2': 'prismarine2'}),
    ('end_stone', g_pitted, ['end_stone'], {}),
    ('purpur', g_panel, ['purpur'], {'grid': 2, 'inner': _purpur_inner}),
    ('quartz', g_panel, ['quartz'], {'grid': 1, 'inner': _quartz_inner}),
    ('obsidian', g_facets, ['obsidian'], {'grid': 3, 'glints': 1, 'joint': O}),
    ('netherrack', g_lumps, ['netherrack'], {'grid': 5}),
    ('nether_bricks', g_bricks, ['nether_brick'], {'rows': 4, 'length': 8, 'offset': 4, 'joint': O, 'var': (BS, BS, LT)}),
    ('basalt', g_bark, ['basalt'], {'furrows': 4, 'amp': 0.5, 'plates': 0.6, 'streaks': 0.6, 'light': 0.6}),
]
for _n, _g, _r, _p in _stone_tbl:
    _mat(_n, 'stone', _g, _r, **_p)

_SPECK = {
    'granite': lambda: [(RAMPS['granite'], DK, 7, (2, 3), 'pit', 0), (RAMPS['granite'], LT, 6, (2, 3), 'bump', 1),
                        (RAMPS['granite'], SH, 3, (1, 2), 'flat', 0)],
    'diorite': lambda: [(RAMPS['stone'], BS, 5, (2, 4), 'bump', 0), (RAMPS['stone'], DK, 3, (1, 2), 'flat', 0),
                        (RAMPS['diorite'], HI, 3, (1, 2), 'flat', 0)],
    'andesite': lambda: [(RAMPS['andesite'], DK, 9, (1, 2), 'flat', 0), (RAMPS['andesite'], LT, 7, (1, 2), 'bump', 1)],
    'tuff': lambda: [(RAMPS['tuff'], BS, 7, (1, 2), 'pit', 0), (RAMPS['tuff'], LT, 5, (1, 2), 'bump', 1)],
    'calcite': lambda: [(RAMPS['calcite'], DK, 4, (2, 4), 'flat', 0), (RAMPS['calcite'], HI, 3, (1, 2), 'flat', 0)],
    'blackstone': lambda: [(RAMPS['blackstone'], LT, 6, (1, 3), 'bump', 1), (RAMPS['blackstone'], SH, 5, (1, 2), 'flat', 0)],
}

for _n, _g, _r, _p in (
        ('dirt', g_dirt, ['dirt', 'gravel'], {'R2': 'gravel'}),
        ('grass_top', g_grass_top, ['grass'], {}),
        ('grass_side', g_grass_side, ['dirt', 'grass'], {}),
        ('podzol', g_needles, ['podzol', 'needle'], {}),
        ('mycelium', g_mycelium, ['mycelium', 'spore'], {}),
        ('sand', g_sand, ['sand'], {}),
        ('red_sand', g_sand, ['red_sand'], {}),
        ('gravel', g_cobble, ['gravel', 'gravel2'], {'grid': 4, 'joint': SH, 'tones': (DK, BS, LT, LT), 'chips': False}),
        ('clay', g_clay, ['clay'], {}),
        ('mud', g_mud, ['mud'], {}),
        ('snow', g_snow, ['snow'], {}),
        ('ice', g_ice, ['ice'], {}),
        ('packed_ice', g_ice, ['packed_ice'], {'cells': True, 'streaks': 0.5}),
        ('soul_sand', g_soul_sand, ['soul_sand', 'soul'], {})):
    _mat(_n, 'soil', _g, _r, **_p)

for _n, _g, _r, _p in (
        ('iron_block', g_metal, ['iron'], {'plates': 2, 'stripes': True}),
        ('gold_block', g_metal, ['gold'], {'plates': 2}),
        ('copper_block', g_metal, ['copper'], {'plates': 2}),
        ('exposed_copper', g_metal, ['exposed_copper', 'patina'], {'plates': 2, 'patina': 0.07, 'P': 'patina'}),
        ('weathered_copper', g_metal, ['weathered_copper', 'patina'], {'plates': 2, 'patina': 0.6, 'P': 'patina'}),
        ('oxidized_copper', g_oxidized, ['patina', 'copper'], {}),
        ('netherite_block', g_metal, ['netherite'], {'plates': 2, 'stripes': True}),
        ('raw_iron_block', g_lumps, ['raw_iron'], {'grid': 4, 'contrast': 1}),
        ('raw_gold_block', g_lumps, ['raw_gold', 'raw_iron'], {'grid': 4, 'R2': 'dirt'}),
        ('raw_copper_block', g_lumps, ['raw_copper', 'patina'], {'grid': 4, 'R2': 'patina', 'r2': 0.35, 'flecks': True})):
    _mat(_n, 'metal', _g, _r, **_p)

for _n, _g, _r, _p in (
        ('diamond_block', g_cut_gems, ['diamond'], {'cut': 'brilliant'}),
        ('emerald_block', g_cut_gems, ['emerald'], {'cut': 'emerald'}),
        ('amethyst_block', g_facets, ['amethyst'], {'grid': 3, 'glints': 2}),
        ('lapis_block', g_inlay, ['lapis', 'gold'], {'F': 'gold', 'flecks': 5}),
        ('redstone_block', g_studs, ['redstone'], {}),
        ('coal_block', g_facets, ['coal'], {'grid': 4, 'glints': 1, 'joint': O})):
    _mat(_n, 'gem', _g, _r, **_p)

for _o in ORES:
    _mat(f'{_o}_ore', 'ore', g_ore, [ORES[_o][0], 'stone'], main=ORES[_o][0], ore=_o)

for _d, _h in WOOL_DYES:
    _mat(f'{_d}_wool', 'fabric', g_wool, [f'{_d}_wool'])
for _n, _g, _r, _p in (
        ('leather', g_leather, ['leather'], {}),
        ('velvet', g_velvet, ['velvet'], {}),
        ('canvas', g_canvas, ['canvas'], {}),
        ('carpet', g_carpet, ['carpet_red', 'carpet_gold', 'carpet_navy'], {})):
    _mat(_n, 'fabric', _g, _r, **_p)

for _n, _g, _r, _p in (
        ('glass', g_glass, ['glass'], {'fill_hide': ('frame',), 'edge': (HI, DK)}),
        ('tinted_glass', g_glass, ['tinted_glass', 'glass'], {'tint': 'tinted_glass', 'fill_hide': ('frame',),
                                                             'edge': (HI, O)}),
        ('water', g_water, ['water'], {}),
        ('lava', g_lava, ['lava'], {}),
        ('slime', g_gel, ['slime'], {}),
        ('honey', g_gel, ['honey'], {}),
        ('hay_bale', g_hay, ['hay', 'hay_tie'], {}),
        ('bookshelf', g_bookshelf, ['oak_planks'], {}),
        ('terracotta', g_terracotta, ['terracotta'], {}),
        ('parchment', g_parchment, ['parchment'], {}),
        ('bone_block', g_bone, ['bone'], {}),
        ('cracked_ice', g_ice, ['ice'], {'cracks': 3, 'streaks': 0.6}),
        ('moss_block', g_moss, ['moss'], {}),
        ('oak_leaves', g_leaves, ['oak_leaves'], {}),
        ('birch_leaves', g_leaves, ['birch_leaves'], {'density': 1.05}),
        ('spruce_leaves', g_leaves, ['spruce_leaves'], {'kind': 'needle'}),
        ('cherry_leaves', g_leaves, ['cherry_leaves', 'blossom_core'], {'kind': 'blossom', 'R2': 'blossom_core'})):
    _mat(_n, 'other', _g, _r, **_p)

for _n, _g, _r, _p in (
        ('jungle_leaves', g_leaves, ['jungle_leaves'], {'density': 1.1}),
        ('acacia_leaves', g_leaves, ['acacia_leaves'], {'density': 0.9}),
        ('dark_oak_leaves', g_leaves, ['dark_oak_leaves'], {'density': 1.15}),
        ('mangrove_leaves', g_leaves, ['mangrove_leaves'], {}),
        ('azalea_leaves', g_leaves, ['azalea_leaves'], {}),
        ('flowering_azalea_leaves', g_leaves, ['azalea_leaves', 'azalea_flower'],
         {'kind': 'blossom', 'R2': 'azalea_flower'}),
        ('glowstone', g_facets, ['glowstone'], {'grid': 4, 'glints': 3, 'joint': DK})):
    _mat(_n, 'other', _g, _r, **_p)

for _w in ('oak', 'spruce', 'birch', 'jungle', 'acacia', 'dark_oak', 'mangrove', 'cherry', 'crimson', 'warped'):
    _mat(f'stripped_{_w}_{"stem" if _w in ("crimson", "warped") else "log"}', 'wood', g_stripped, [f'{_w}_planks'])

for _n, _g, _r, _p in (
        ('smooth_stone', g_polished, ['stone'], {}),
        ('polished_granite', g_polished, ['granite'], {'groups': 'granite'}),
        ('polished_diorite', g_polished, ['diorite', 'stone'], {'groups': 'diorite'}),
        ('polished_andesite', g_polished, ['andesite'], {'groups': 'andesite'}),
        ('polished_blackstone', g_polished, ['blackstone'], {'groups': 'blackstone'}),
        ('polished_deepslate', g_polished, ['deepslate'], {}),
        ('chiseled_stone_bricks', g_chiseled, ['stone_brick'], {}),
        ('deepslate_bricks', g_bricks, ['deepslate'], {'rows': 4, 'length': 8, 'offset': 4, 'joint': O, 'var': (BS, BS, LT)}),
        ('deepslate_tiles', g_bricks, ['deepslate'], {'rows': 4, 'length': 4, 'offset': 0, 'joint': O,
                                                      'var': (DK, BS, BS, LT), 'chips': 0.3, 'rim': 0}),
        ('end_stone_bricks', g_bricks, ['end_stone'], {'rows': 4, 'length': 8, 'offset': 4, 'var': (BS, BS, LT)}),
        ('quartz_bricks', g_bricks, ['quartz'], {'rows': 4, 'length': 8, 'offset': 4, 'texture': 0.2, 'chips': 0.1}),
        ('quartz_pillar', g_bricks, ['quartz'], {'rows': 1, 'length': 4, 'offset': 0, 'texture': 0.2, 'chips': 0.0}),
        ('cut_sandstone', g_bricks, ['sandstone'], {'rows': 2, 'length': 16, 'offset': 0, 'chips': 0.2}),
        ('red_nether_bricks', g_bricks, ['red_nether_brick'], {'rows': 4, 'length': 8, 'offset': 4, 'joint': O,
                                                               'var': (BS, BS, LT)})):
    _mat(_n, 'stone', _g, _r, **_p)

for _n, _g, _r, _p in (
        ('coarse_dirt', g_dirt, ['dirt', 'gravel'], {'R2': 'gravel', 'pebbles': 1.8, 'clods': 0.6}),
        ('rooted_dirt', g_roots, ['dirt', 'root'], {}),
        ('farmland', g_farmland, ['farmland'], {}),
        ('dirt_path', g_sand, ['path'], {})):
    _mat(_n, 'soil', _g, _r, **_p)

for _n, _g, _r, _p in (
        ('wood_shingles', g_shingles, ['shingle'], {'style': 'wood'}),
        ('clay_roof_tiles', g_shingles, ['roof_clay'], {'style': 'scale'}),
        ('slate_roof', g_shingles, ['roof_slate'], {'style': 'scale', 'h': 3, 'w': 4}),
        ('thatch', g_thatch, ['thatch'], {}),
        ('iron_bars', g_bars, ['iron'], {'edge': (HI, O)}),
        ('ladder', g_ladder, ['oak_planks'], {})):
    _mat(_n, 'build', _g, _r, **_p)

for _d, _h in WOOL_DYES:
    _mat(f'{_d}_concrete', 'dyed', g_concrete, [f'{_d}_concrete'])
for _d, _h in WOOL_DYES:
    _mat(f'{_d}_terracotta', 'dyed', g_terracotta, [f'{_d}_terracotta'])


# ------------------------------------------------------------------ API
def _resolve(v):
    return RAMPS[v] if isinstance(v, str) and v in RAMPS else v


def tile(name, k=1, **opts):
    """Build a material's Tile (layers kept). opts: seed, color='#hex' (wool / terracotta / any one-ramp
    material: a new ramp from that colour), base='deepslate' (ores), frame (water, lava)."""
    if name not in MATERIALS:
        raise KeyError(f'unknown material {name!r}; see `materials.py list`')
    spec = MATERIALS[name]
    params = dict(spec['params'])
    seed = opts.pop('seed', 0)
    color = opts.pop('color', None)
    params.update(opts)
    ramps = [RAMPS[r] for r in spec['ramps']]
    if color:
        ramps[0] = custom_ramp(color, soft=0.9 if spec['family'] in ('fabric', 'soil') else 0.7)
    t = Tile(k, _seed(name, k, seed), ramps)
    gen = spec['gen']
    args = [] if gen is g_ore else [ramps[0]]
    if gen in (g_birch_bark, g_stem, g_bamboo_block, g_log_top, g_grass_side, g_needles, g_mycelium,
               g_soul_sand, g_hay, g_oxidized, g_roots):
        args.append(ramps[1])
    if gen is g_carpet:
        args += ramps[1:3]
    if gen in (g_speckled, g_polished) and params.get('groups'):
        params['groups'] = _SPECK[params['groups']]()
        if color:
            params['groups'] = [(ramps[0] if g[0] is RAMPS[spec['ramps'][0]] else g[0],) + g[1:] for g in params['groups']]
    for key in ('R2', 'P', 'F', 'tint', 'mossy'):
        if key in params:
            params[key] = _resolve(params[key])
    if gen is g_cobble and 'R2' not in params and len(ramps) > 1 and not params.get('mossy') is ramps[1]:
        params['R2'] = ramps[1]
    gen(t, *args, **params)
    perfect(t)
    return t


def render(name, k=1, tight=False, **opts):
    """The material's tile as RGBA, 16k x 16k. A tile is not cropped by default: a transparent margin (ladder,
    bars, leaves) is part of the repeat; tight=True crops to the opaque pixels (a sprite, not a tile)."""
    im = tile(name, k, **opts).image()
    return im.crop(im.getbbox()) if tight and im.getbbox() else im


def parts(name, k=1, **opts):
    """The tile's layers as parts (modes.Parts items: name, sprite, x, y), bottom -> top."""
    t = tile(name, k, **opts)
    P = Parts(t.S, t.S)
    for ln, d in t.layers:
        if not d:
            continue

        def draw(im, d=d):
            px = im.load()
            for p, c in d.items():
                px[p] = c
        P.add(f'{name}/{ln}', draw)
    return P.items


def ramp(name):
    """The material's main ramp: [outline, shadow, dark mid, base, light mid, highlight] (RGBA)."""
    if name in RAMPS:
        return RAMPS[name]
    return RAMPS[MATERIALS[name]['main']]


def ramps(name):
    return [RAMPS[r] for r in MATERIALS[name]['ramps']]


# Block faces: tiles that carry their own joints / frame / bevel at the tile edge (bricks, panels, metal and
# gem blocks, glass, gel blocks, log ends, polished stone, bookshelf, the grass side). They repeat as a grid
# of blocks - by design - so shading.py check --tile reports their edges and ends; every other tile is a
# seamless texture (drawn on a torus: every coordinate wraps).
FACE_GENS = (g_bricks, g_panel, g_metal, g_oxidized, g_cut_gems, g_inlay, g_studs, g_gel, g_glass, g_log_top,
             g_polished, g_chiseled, g_bookshelf, g_grass_side, g_ladder, g_bars)


def is_face(name):
    return MATERIALS[name]['gen'] in FACE_GENS


CATALOG = {}
for _name in MATERIALS:
    CATALOG[_name] = (lambda n: (lambda k=1, **o: render(n, k, **o)))(_name)


# ------------------------------------------------------------------ fill: paint any mask with a material
def _mask_set(mask):
    if isinstance(mask, Image.Image):
        a = mask.getchannel('A') if mask.mode in ('RGBA', 'LA') else mask.convert('L')
        px = a.load()
        return {(x, y) for y in range(a.height) for x in range(a.width) if px[x, y] > 127}
    return set(mask)


def _lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def _smooth(pts):
    """Drop the corner pixels that would make an L in the 1 px outline (the pixel-perfect rule applied to
    the mask's edge ring), so rounded corners step cleanly."""
    from shading import doubles
    ring = {p for p in pts if any((p[0] + dx, p[1] + dy) not in pts for dx, dy in N4)}
    if not ring:
        return pts
    x0, y0 = min(x for x, _ in ring) - 1, min(y for _, y in ring) - 1
    x1, y1 = max(x for x, _ in ring) + 2, max(y for _, y in ring) + 2
    im = Image.new('RGBA', (x1 - x0, y1 - y0), (0, 0, 0, 0))
    px = im.load()
    for (x, y) in ring:
        px[x - x0, y - y0] = (0, 0, 0, 255)
    bad = {(x + x0, y + y0) for x, y in doubles(px, im.width, im.height)}
    return pts - bad


def _depth(pts, cap):
    """Distance (4-neighbour steps) from outside the mask, capped."""
    d = {}
    front = [p for p in pts if any((p[0] + dx, p[1] + dy) not in pts for dx, dy in N4)]
    for p in front:
        d[p] = 1
    for lvl in range(2, cap + 1):
        nxt = []
        for (x, y) in front:
            for dx, dy in N4:
                q = (x + dx, y + dy)
                if q in pts and q not in d:
                    d[q] = lvl
                    nxt.append(q)
        front = nxt
    return d


def _facing(pts, x, y, reach):
    """+1 if the nearest edge is up / left (lit), -1 if down / right, 0 if tied."""
    def run(dx, dy):
        for i in range(1, reach + 2):
            if (x + dx * i, y + dy * i) not in pts:
                return i
        return reach + 2
    u, l, dn, r = run(0, -1), run(-1, 0), run(0, 1), run(1, 0)
    a, b = min(u, l), min(dn, r)
    if a < b:
        return 1
    if b < a:
        return -1
    return 1 if (u + l) <= (dn + r) else -1


def fill_layers(mask, name, k=1, bevel=True, outline=True, origin=None, **opts):
    """fill() as layers {texture, bevel, outline}: dicts {(x, y): RGBA}."""
    pts = _mask_set(mask)
    if not pts:
        return {'texture': {}, 'bevel': {}, 'outline': {}}
    if outline and bevel:
        pts = _smooth(pts)
    t = tile(name, k, **opts)
    tim = t.image(hide=MATERIALS[name]['fill_hide']).load()
    S = t.S
    ox, oy = origin or (min(x for x, _ in pts), min(y for _, y in pts))
    lut = t.lut
    main = ramps(name)[0] if not opts.get('color') else t.ramps[0]
    tex = {}
    for (x, y) in pts:
        c = tim[(x - ox) % S, (y - oy) % S]
        if c[3]:
            tex[(x, y)] = c
    bev, out = {}, {}
    if bevel:
        depth = _depth(pts, 1 + k + 1)
        for p, d in depth.items():
            x, y = p
            if d == 1 and outline:
                lit = _facing(pts, x, y, 1) > 0
                e_lit, e_dark = MATERIALS[name]['edge']
                out[p] = main[e_lit] if lit else main[e_dark]
            elif 2 <= d <= 1 + k and p in tex:
                f = _facing(pts, x, y, k + 1)
                c = tex[p]
                if c in lut:
                    R, i = lut[c]
                    step = f if not (k == 2 and d == 2 and f > 0) else 2
                    if k == 2 and d == 3 and f < 0:
                        continue
                    nc = R[max(1, min(5, i + step))]
                    if d == 2 and f > 0 and _lum(nc) < _lum(main[BS]):
                        nc = main[LT]                       # the lit rim reads even on a dark texel
                    elif d == 2 and f < 0 and _lum(nc) > _lum(main[BS]):
                        nc = main[DK]
                    bev[p] = nc
    L = {'texture': tex, 'bevel': bev, 'outline': out}
    _perfect_layers(L, {c for R in t.ramps for c in R})
    return L


def _perfect_layers(L, only):
    """pixel_perfect on the painted result of fill(): the bevel shifts and the outline can make new
    L-corners with the texture's lines; fixes go back into the layer that shows the pixel."""
    allp = {}
    for ln in ('texture', 'bevel', 'outline'):
        allp.update({p: (ln, c) for p, c in L[ln].items()})
    if not allp:
        return
    x0, y0 = min(x for x, _ in allp) - 1, min(y for _, y in allp) - 1
    x1, y1 = max(x for x, _ in allp) + 2, max(y for _, y in allp) + 2
    im = Image.new('RGBA', (x1 - x0, y1 - y0), (0, 0, 0, 0))
    px = im.load()
    for (x, y), (ln, c) in allp.items():
        px[x - x0, y - y0] = c
    if not fix_doubles(im, only):
        return
    for (x, y), (ln, c) in allp.items():
        n = px[x - x0, y - y0]
        if n != c:
            if n[3] == 0:
                for d in L.values():
                    d.pop((x, y), None)
            else:
                L[ln][(x, y)] = n


def fill(img, mask, name, k=1, bevel=True, outline=True, origin=None, **opts):
    """Paint any pixel mask (a set of (x, y) or an image whose alpha / value > 127 is inside) with a
    material: the seamless texture (anchored at the mask's top-left, or `origin`), a lit band on the
    top / left (+1 tone, HD: +2 then +1), a darker band on the bottom / right, and a selective outline in
    the material's own darks (shadow tone on the lit side, outline tone elsewhere). Transparent texels
    (glass, leaves) stay transparent inside. Returns the set of painted pixels."""
    L = fill_layers(mask, name, k, bevel, outline, origin, **opts)
    px = img.load()
    done = set()
    for lname in ('texture', 'bevel', 'outline'):
        for (x, y), c in L[lname].items():
            if 0 <= x < img.width and 0 <= y < img.height:
                px[x, y] = c
                done.add((x, y))
    return done


def fill_parts(mask, name, k=1, **kw):
    """fill() as parts (texture, bevel, outline) for modes.compose / layers.save_parts."""
    L = fill_layers(mask, name, k, **kw)
    allp = set().union(*[set(d) for d in L.values()]) or {(0, 0)}
    W, H = max(x for x, _ in allp) + 1, max(y for _, y in allp) + 1
    P = Parts(W, H)
    for ln in ('texture', 'bevel', 'outline'):
        d = L[ln]
        if d:
            def draw(im, d=d):
                px = im.load()
                for p, c in d.items():
                    px[p] = c
            P.add(f'{name}/{ln}', draw)
    return P.items


def circle(cx, cy, r):
    """A pixel-art disc mask (for fill)."""
    return {(x, y) for y in range(int(cy - r) - 1, int(cy + r) + 2) for x in range(int(cx - r) - 1, int(cx + r) + 2)
            if (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 <= r * r}


# ------------------------------------------------------------------ chart
BG = (54, 57, 64, 255)
BG2 = (44, 46, 52, 255)
INK = (222, 220, 210, 255)
INK2 = (150, 154, 162, 255)
SAMPLES = ('oak_planks', 'cobblestone', 'stone_bricks', 'gold_block', 'diamond_block', 'red_wool', 'glass',
           'bricks', 'oxidized_copper', 'grass_top')


def _checker(w, h, cell):
    im = Image.new('RGBA', (w, h), (104, 108, 116, 255))
    px = im.load()
    for y in range(h):
        for x in range(w):
            if (x // cell + y // cell) % 2:
                px[x, y] = (122, 126, 134, 255)
    return im


def label(img, x, y, text, c):
    """pixfont text with real underscores (the font has none): words, then a 4 px line on the baseline."""
    from pixfont import draw_text, text_width
    for i, w in enumerate(text.split('_')):
        if i:
            for d in range(4):
                img.putpixel((x + d, y + 7), c)
            x += 5
        draw_text(img, x, y, w, c)
        x += text_width(w) + 1


def chart(path, hd=False, names=None):
    from pixfont import draw_text, text_width
    k = 2 if hd else 1
    z = 3 if hd else 4
    S = 16 * k
    rep = 4 if not hd else 3
    cw = S * z + 6 + S * rep // (1 if not hd else 1)
    cw = max(cw, 120)
    ch = S * z + 16
    cols = 8 if not hd else 6
    names = names or list(MATERIALS)
    blocks = []
    for fam, title in FAMILIES:
        ns = [n for n in names if MATERIALS[n]['family'] == fam]
        if ns:
            blocks.append((title, ns))
    rows_h = sum(14 + ((len(ns) + cols - 1) // cols) * (ch + 6) for _, ns in blocks)
    # fill samples: a rounded slab and a circle for a few materials
    sw, sh_ = 44 * k, 22 * k
    cr = 11 * k
    samp_h = (sh_ + 12 * k) * 2 + 40
    W = 12 + cols * (cw + 8)
    H = 30 + rows_h + 20 + samp_h * 1
    img = Image.new('RGBA', (W, H), BG)
    draw_text(img, 10, 8, f'materials.py - {len(names)} materials, {"HD k=2 (32x32), x3" if hd else "k=1 (16x16), x4"}'
              ' + a 1:1 repeat', INK)
    y = 26
    for title, ns in blocks:
        draw_text(img, 10, y, title, (240, 200, 110, 255))
        y += 14
        for i, n in enumerate(ns):
            cx, cy = 10 + (i % cols) * (cw + 8), y + (i // cols) * (ch + 6)
            im = render(n, k)
            img.paste(_checker(S * z, S * z, 4 * z), (cx, cy))
            big = im.resize((S * z, S * z), Image.NEAREST)
            img.alpha_composite(big, (cx, cy))
            rp = _checker(S * rep, S * rep, 4)
            for j in range(rep):
                for i2 in range(rep):
                    rp.alpha_composite(im, (i2 * S, j * S))
            img.alpha_composite(rp, (cx + S * z + 6, cy))
            label(img, cx, cy + S * z + 4, n, INK2)
        y += ((len(ns) + cols - 1) // cols) * (ch + 6)
    # samples: fill() on a rounded slab and a circle, enlarged
    y += 6
    label(img, 10, y, 'fill(): a rounded slab and a circle - texture, lit top / left band, dark bottom / right band, '
                      'selective outline; hard contact shadow on the backdrop', (240, 200, 110, 255))
    y += 14
    zz = 3 if not hd else 2
    one = (sw + cr * 2 + 14 * k, sh_ + 10 * k)
    per = max(1, (W - 20) // (one[0] * zz))
    rows_s = (len(SAMPLES) + per - 1) // per
    canvas = Image.new('RGBA', (one[0] * per + 4, one[1] * rows_s + 4), BG)
    for i, n in enumerate(SAMPLES):
        x0, y0 = 4 + (i % per) * one[0], 4 + (i // per) * one[1]
        slab = rrect(x0, y0, x0 + sw - 1, y0 + sh_ - 1, 4 * k)
        disc_ = circle(x0 + sw + 4 * k + cr, y0 + cr, cr)
        for m in (slab, disc_):
            for (x, yy) in m:                      # hard contact shadow down-right on the backdrop
                q = (x + k, yy + k)
                if q not in m and 0 <= q[0] < canvas.width and 0 <= q[1] < canvas.height:
                    canvas.putpixel(q, BG2)
            fill(canvas, m, n, k)
    big = canvas.resize((canvas.width * zz, canvas.height * zz), Image.NEAREST)
    if y + big.height + 10 > img.height:
        img2 = Image.new('RGBA', (W, y + big.height + 10), BG)
        img2.paste(img, (0, 0))
        img = img2
    img.alpha_composite(big, (10, y))
    img = img.crop((0, 0, W, y + big.height + 10))
    img.save(path)
    return img


def _opts(a):
    o = {}
    for key in ('--seed', '--base', '--color', '--frame'):
        if key in a:
            v = a[a.index(key) + 1]
            o[key[2:]] = int(v) if key in ('--seed', '--frame') else v
    return o


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    hd = '--hd' in a
    k = 2 if hd else 1
    cmd = a[0]
    if cmd == 'chart':
        chart(a[1], hd)
        print('chart ->', a[1])
    elif cmd == 'render':
        render(a[1], k, **_opts(a)).save(a[2])
        print(a[1], '->', a[2])
    elif cmd == 'parts':
        name, out = a[1], a[2]
        S = 16 * k
        if ':' in name:                                  # slab:NAME / disc:NAME = fill() on a shape, as parts
            shape, name = name.split(':', 1)
            m = rrect(0, 0, 44 * k - 1, 22 * k - 1, 4 * k) if shape == 'slab' else circle(11 * k, 11 * k, 11 * k)
            items = fill_parts(m, name, k, **_opts(a))
            size = (max(x for x, _ in m) + 1, max(y for _, y in m) + 1)
        else:
            items, size = parts(name, k, **_opts(a)), (S, S)
        layers.save_parts(items, out, size=size)
        layers.write_aseprite(os.path.join(out, f'{name}.aseprite'), items, size)
        print(len(items), 'parts ->', out)
    elif cmd == 'list':
        for fam, title in FAMILIES:
            print(f'{title}:')
            print('  ' + ', '.join(n for n in MATERIALS if MATERIALS[n]['family'] == fam))
    else:
        sys.exit(__doc__)
