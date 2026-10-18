#!/usr/bin/env python3
"""Buildings kit: original blocky buildings and little houses in a frontal view (the facade straight on, the
roof seen slightly from above, like the barn in modes_hd.py), at two densities: k=1 (vanilla GUI density, a
cottage is ~40 px wide) and k=2 ("HD", ~80 px, drawn natively with more detail - grain, nails, hinges,
individual tiles and flowers - never upscaled).

Every building is BUILT FROM PARTS (modes.Parts: each part on its own transparent canvas, kept as sprite +
offset): ground, path, foundation, walls, beams, windows, door, roof, chimney, smoke, sign, lanterns, flower
boxes, fence ... plus generated parts: '<part>_shadow' (the hard cast shadow a part throws on what is behind
it, one ramp step darker), 'snow' (caps, roof cover, icicles) and 'light' (the warm pools round lanterns and
windows at night). modes.compose builds the picture again, modes.override moves or hides parts, and
layers.save_parts / layers.write_aseprite export them. references/buildings.md says how each one is drawn.

Catalog (27): cottage, stone_house, log_cabin, birch_house, spruce_aframe, desert_house, igloo,
mushroom_house, treehouse, tower, windmill, watermill, lighthouse, castle_gate, castle_keep, chapel, tavern,
market_stall, forge, barn, well, tent, mine_entrance, portal_ruin, wizard_tower, guard_post, dock;
village(width, height, seed, k) composes several of them with ground, roads, trees, fences and lamps.

Options (every building): night=True (moonlit palette, warm lit windows, lantern / fire / portal light pools),
snow=True (snow caps, snow-covered roofs, icicles, snowy ground), size='s' | 'm' | 'l' (bays, storeys,
height), seed=N (stone layouts, flowers, smoke), ground=False (no grass island under it).

Shading follows references/texture-shading.md and references/pixel-art-craft.md: one five-tone ramp per
material (shading.ramp5: 0 outline, 1 shadow, 2 dark mid, 3 base, 4 light mid, 5 highlight; matte materials
soft, metal and glass contrasty), light from the top-left, a flat facade mostly one tone per material with
volume from the parts' different planes (lit roof slope / dark slope, proud beams, recessed windows),
selective outlines in each part's own dark tone (pixel-perfect), hard cast shadows and contact shadows,
clusters instead of noise, no gradients, no dithering, no semi-transparent pixels.

    from buildings import render, parts, village, CATALOG
    img = render('cottage', k=2, night=True)             # tight RGBA
    items = parts('windmill', k=1, snow=True)             # modes.Parts items, bottom -> top
    items = village(160, 90, seed=3, k=1)                 # a whole scene as parts

    python3 buildings.py chart OUT.png [--hd]             every building day / night / snow (HD: day / night),
                                                          labelled, x4 (HD x3), and a village by day and night
    python3 buildings.py render NAME OUT.png [--hd] [--night] [--snow] [--size s|m|l] [--seed N] [--no-ground]
    python3 buildings.py parts NAME OUT_DIR [--hd] [...]  PNG per part + layers.json + _sheet.png + .aseprite
    python3 buildings.py village OUT.png [--hd] [--night] [--snow] [--width W --height H --seed N]
    python3 buildings.py list
"""
import math
import os
import random
import sys
import zlib

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kitchen import _r5, edge_ring, N4                    # noqa: E402
from modes import Parts, compose, override                # noqa: E402,F401
from shading import pixel_perfect                         # noqa: E402
from hub import GOLD, CREAM                               # noqa: E402
import layers                                             # noqa: E402

O, SH, DK, BS, LT, HI = range(6)                          # tone indices into a ramp
N8 = ((-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1))

# ------------------------------------------------------------------ ramps (outline, shadow, dark, base, light, hi)
OAK = _r5('#b58a52', soft=0.8)            # oak planks
OAK_LOG = _r5('#6e5434', soft=0.8)        # oak bark
LOG_END = _r5('#c49a5e', soft=0.8)        # sawn log ends, end grain
SPRUCE = _r5('#7c5836', soft=0.8)         # spruce planks
SPRUCE_LOG = _r5('#4d3824', soft=0.8)
BIRCH = _r5('#d8c690', soft=0.9)          # birch planks
BIRCH_BARK = _r5('#e6e2d6', soft=1)       # white bark (black marks in BARK_MARK)
BARK_MARK = _r5('#3c3834', soft=1)
DARK_OAK = _r5('#553a24', soft=0.8)       # beams, timber frame, trims
COBBLE = _r5('#8c8c90', soft=0.7)
STONE = _r5('#94969c', soft=0.8)          # stone bricks
DEEP = _r5('#646470', soft=0.8)           # castle stone, deepslate
WALL_STONE = _r5('#7e8088', soft=0.8)     # curtain walls: a step darker than the towers in front
WIZ_STONE = _r5('#7c7488', soft=0.8)      # wizard tower: purple-grey stone
BARN_RED = _r5('#a63a30', soft=0.8)
SILO_GREY = _r5('#9aa0a8', soft=1)
IRON_ORE = _r5('#d8a888', soft=0.6)       # iron ore specks
MOSS = _r5('#5e8a36', soft=0.6)
SANDSTONE = _r5('#dcc68c', soft=0.9)
SAND = _r5('#e0cc94', soft=1)
TERRACOTTA = _r5('#b8683e', soft=0.7)
BRICK = _r5('#a85440', soft=0.7)
MORTAR = _r5('#b4aa9c', soft=1)
PLASTER = _r5('#e8dcc0', soft=1)
WHITEWASH = _r5('#e4e4dc', soft=1)        # lighthouse / windmill / chapel walls
SHINGLE = _r5('#7e4c30', soft=0.7)        # wooden shingles (dark warm brown)
CLAY = _r5('#bc4a38', soft=0.6)           # red clay tiles
SLATE = _r5('#56607a', soft=0.7)          # blue-grey slate
MOSSROOF = _r5('#5a7a44', soft=0.7)       # green-stained shingles
THATCH = _r5('#c8a050', soft=0.7)
SNOW = _r5('#e8f0f6', soft=1)
ICE = _r5('#8ccaea', soft=0.4)            # icicles, packed ice
MUSH = _r5('#c8302c', soft=0.5)           # mushroom cap
STEM = _r5('#e4d8be', soft=1)             # mushroom stem
LEAVES = _r5('#4c8c36', soft=0.6)
GRASS = _r5('#64a83e', soft=0.6)
DIRT = _r5('#8a5c3a', soft=0.7)
PATH = _r5('#ac8e60', soft=1)
GRAVEL = _r5('#8c8884', soft=1)
WATER = _r5('#3e78cc', soft=0.4)
GLASS = _r5('#5c98b8', soft=0.3)          # day windows: sky reflection
IRON = _r5('#8e939c')                     # metal: standard contrast
DARK_IRON = _r5('#4a4c56')                # lantern cages, brackets, rails
COPPER = _r5('#c06c40')
CLOTH = _r5('#b83c36', soft=0.7)          # red cloth: awnings, banners
CANVAS = _r5('#dccca4', soft=1)           # tents, sails, awning stripes
BLUE_CLOTH = _r5('#3c5ca8', soft=0.7)
GREEN_PAINT = _r5('#4a8048', soft=0.8)    # shutters
BLUE_PAINT = _r5('#4a78a8', soft=0.8)
RED_PAINT = _r5('#a84438', soft=0.8)
OBSIDIAN = _r5('#30264a', soft=0.5)
NETHERRACK = _r5('#8a3636', soft=0.6)
MAGIC = _r5('#4e3a8e', soft=0.6)          # wizard roof
ROPE = _r5('#b89a68', soft=1)
SMOKE = _r5('#c4c4c8', soft=1)
HAY = _r5('#d6b048', soft=0.6)
CARROT = _r5('#e8862a', soft=0.5)
SKY_DAY = _r5('#6cb2e6', soft=0.6)
SKY_NIGHT = _r5('#1e2448', soft=0.4)
CLOUD = _r5('#f2f0ea', soft=1)
HAZE = _r5('#7fa8b4', soft=1)             # far hills in haze
MOON = _r5('#efe6c8', soft=1)
SPRUCE_NEEDLES = _r5('#3c6e44', soft=0.6)
BIRCH_LEAVES = _r5('#78a83c', soft=0.6)
POPPY = _r5('#d8343a', soft=0.4)          # flowers
DANDELION = _r5('#eecc3a', soft=0.4)
CORNFLOWER = _r5('#4a72e0', soft=0.4)
PINK = _r5('#e888b0', soft=0.4)
GOLDR = [tuple(c) for c in GOLD]          # hub gold (metal)
CREAMR = [tuple(c) for c in CREAM]
# light sources: EMISSIVE - they keep their colours at night
GLOW = _r5('#f2b44a', soft=0.2)           # lit window / lantern light
FIRE = _r5('#f07828', soft=0.2)           # flames, forge mouth, lava
PORTAL = _r5('#a048e8', soft=0.3)         # nether portal
ARCANE = _r5('#5ad0e8', soft=0.3)         # wizard light
EMISSIVE_RAMPS = (GLOW, FIRE, PORTAL, ARCANE)
EMISSIVE = {c for r in EMISSIVE_RAMPS for c in r[1:]}
FLOWERS = (POPPY, DANDELION, CORNFLOWER, PINK)

BASE_RAMPS = {n: v for n, v in list(globals().items())
              if isinstance(v, list) and len(v) == 6 and all(isinstance(c, tuple) for c in v)}
_RAMP_OF = {}                                             # colour -> (ramp, index), for darker()
for _n, _r in BASE_RAMPS.items():
    for _i, _c in enumerate(_r):
        _RAMP_OF.setdefault(_c, (_r, _i))


def _cl(v):
    return max(0, min(255, int(round(v))))


# ------------------------------------------------------------------ night and light pools
# A colour map, not a filter: every ramp colour maps 1:1 onto a moonlit colour (darker, cooler, a little
# desaturated - value order kept, so the shading still reads), emissive colours stay; the pools round lights
# are two hard bands of a warm-lit version of the day colour (inner strong, outer half) - stepped, no blur.
_NIGHT_CACHE = {}


def night_c(c):
    if c in EMISSIVE or c[3] == 0:
        return c
    if c not in _NIGHT_CACHE:
        r, g, b = c[:3]
        L = 0.299 * r + 0.587 * g + 0.114 * b
        _NIGHT_CACHE[c] = (_cl(0.30 * r + 0.10 * L + 8), _cl(0.34 * g + 0.10 * L + 14),
                           _cl(0.44 * b + 0.16 * L + 36), 255)
    return _NIGHT_CACHE[c]


LIGHT_KINDS = {                                           # tint of the lit day colour, + add
    'lamp': ((1.0, 0.86, 0.58), (20, 8, 0)),
    'fire': ((1.04, 0.74, 0.46), (28, 6, 0)),
    'portal': ((0.82, 0.56, 1.0), (26, 0, 44)),
    'arcane': ((0.6, 0.86, 1.0), (0, 18, 40)),
}


def lit_c(c, kind='lamp', s=1.0):
    """Day colour c lit by a light of `kind` at night; s = 1 inner band, 0.5 outer band."""
    (tr, tg, tb), (ar, ag, ab) = LIGHT_KINDS[kind]
    w = (c[0] * tr + ar, c[1] * tg + ag, c[2] * tb + ab)
    n = night_c(c)
    return tuple(_cl(n[i] + (w[i] - n[i]) * s) for i in range(3)) + (255,)


# declare the night and lit ramps as module globals, so `shading.py check --kit buildings` counts them as the
# same material (one ramp each) instead of loose colours
for _n, _r in list(BASE_RAMPS.items()):
    if _r[3] in EMISSIVE:
        continue
    globals()[_n + '_NIGHT'] = [night_c(c) for c in _r]
    for _kind in LIGHT_KINDS:
        for _s, _tag in ((1.0, 'IN'), (0.5, 'OUT')):
            globals()[f'{_n}_{_kind.upper()}_{_tag}'] = [lit_c(c, _kind, _s) for c in _r]


DARK_LINES = {c for n, r in list(globals().items()) if isinstance(r, list) and len(r) == 6
              and all(isinstance(c, tuple) for c in r) for c in r[:2]}   # outline + shadow tones (and night ones)


def darker(c, n=1):
    """n ramp steps darker (never into the outline unless already in the shadow tone)."""
    if c in _RAMP_OF:
        r, i = _RAMP_OF[c]
        return r[0] if i <= 1 else r[max(1, i - n)]
    return (_cl(c[0] * 0.72), _cl(c[1] * 0.72), _cl(c[2] * 0.78), 255)


def lighter(c, n=1):
    if c in _RAMP_OF:
        r, i = _RAMP_OF[c]
        return r[min(5, i + n)]
    return c


# ------------------------------------------------------------------ pixels, shapes
def _crc(*a):
    return zlib.crc32(repr(a).encode())


class Layer(dict):
    """One part's pixels {(x, y): rgba} in scene coordinates (any sign), drawn before it becomes a sprite."""

    def put(self, x, y, c):
        if c is not None:
            self[(int(x), int(y))] = c

    def fill(self, pts, c):
        for p in pts:
            self.put(p[0], p[1], c)

    def keep(self, pts, c):
        """Put c only where nothing is drawn yet."""
        for p in pts:
            if p not in self:
                self.put(p[0], p[1], c)


def rect(x0, y0, x1, y1):
    """Inclusive pixel rectangle."""
    return {(x, y) for y in range(int(y0), int(y1) + 1) for x in range(int(x0), int(x1) + 1)}


def disc(cx, cy, r, ry=None):
    ry = ry or r
    return {(x, y) for y in range(int(cy - ry - 1), int(cy + ry + 2)) for x in range(int(cx - r - 1), int(cx + r + 2))
            if ((x + 0.5 - cx) / r) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= 1}


def edge(mask):
    return {p for p in mask if any((p[0] + dx, p[1] + dy) not in mask for dx, dy in N4)}


def bbox(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def cols(mask):
    """{x: (top y, bottom y)} of a mask."""
    out = {}
    for x, y in mask:
        a, b = out.get(x, (y, y))
        out[x] = (min(a, y), max(b, y))
    return out


def outline(lay, mask, R, over=False, lit=None, dark=None):
    """Selective outline in the material's own tones: R[1] on the lit top / left side of the silhouette,
    R[0] on the shadow side and below. Pixels already drawn in the layer are kept unless over=True."""
    mask = set(mask)
    lit = R[SH] if lit is None else lit
    dark = R[O] if dark is None else dark
    if isinstance(lay, Layer):
        lay.ol = getattr(lay, 'ol', set()) | {lit, dark}
    for (x, y) in edge_ring(mask):
        if (x, y) in lay and not over:
            continue
        is_lit = ((x, y + 1) in mask or (x + 1, y) in mask) and not ((x, y - 1) in mask or (x - 1, y) in mask)
        lay[(x, y)] = lit if is_lit else dark
    return mask


def steady(vals):
    """Regularise a staircase (one integer edge position per row): within every monotone stretch the run
    lengths are re-ordered so they change steadily (1-1-2-2-3-4, never 2-1-3-1) - a clean curve with no
    jaggies (references/pixel-art-craft.md); start, end and total climb stay the same."""
    vals = [int(v) for v in vals]
    out, i = [], 0
    while i < len(vals):
        j, sign = i, 0
        while j + 1 < len(vals):
            d = vals[j + 1] - vals[j]
            if d and sign and (d > 0) != (sign > 0):
                break
            if d:
                sign = d
            j += 1
        seg = vals[i:j + 1]
        runs = []
        for v in seg:
            if runs and runs[-1][0] == v:
                runs[-1][1] += 1
            else:
                runs.append([v, 1])
        if len(runs) > 2:
            lens = [r[1] for r in runs[1:-1]]
            jumps = [runs[n + 1][0] - runs[n][0] for n in range(len(runs) - 1)]
            first = sum(lens[:len(lens) // 2]) <= sum(lens[len(lens) // 2:])
            lens.sort(reverse=not first)
            jumps.sort(key=abs, reverse=first)
            v, rebuilt = runs[0][0], [runs[0][0]] * runs[0][1]
            for n, ln in enumerate(lens + [runs[-1][1]]):
                v += jumps[n]
                rebuilt += [v] * ln
            seg = rebuilt
        out += seg
        i = j + 1
    return out[:len(vals)]


def dome_mask(cx, base, rx, ry, below=0):
    """The upper half of an ellipse standing on row `base` (exclusive), its left and right edges run
    through steady() so the curve's steps change evenly; `below` extra rows at full width under it."""
    rows = list(range(int(base - ry), int(base)))
    ws = [rx * math.sqrt(max(0.0, 1 - ((base - y - 0.5) / ry) ** 2)) for y in rows]
    xl = steady([round(cx - w) for w in ws])
    xr = steady([round(cx + w) for w in ws])
    m = set()
    for y, a, b in zip(rows, xl, xr):
        m |= {(x, y) for x in range(a, b)}
    for j in range(below):
        m |= {(x, int(base) + j) for x in range(xl[-1], xr[-1])} if rows else set()
    return m


def gable_top(cx, apex, slope=(1, 1)):
    """Top y of a symmetric gable at column x: apex 2 px wide between cx-1 and cx, `slope` = (run, rise):
    (1, 1) 45 deg, (2, 1) shallow, (1, 2) steep - integer steps keep the line clean (no jaggies)."""
    sx, sy = slope

    def f(x):
        d = x - cx if x >= cx else cx - 1 - x
        return apex + (d * sy) // sx
    return f


# ------------------------------------------------------------------ the scene builder
class Scene:
    """Collects the parts of one building (or a whole village) as Layers with a z order; finish() adds cast
    shadows, snow, night and light pools and returns modes.Parts items."""

    def __init__(self, k=1, night=False, snow=False, seed=0, size='m', ground=True):
        self.k, self.night, self.snow, self.seed, self.size, self.ground = k, night, snow, seed, size, ground
        self.parts, self.lights, self.prefix = [], [], ''
        self.ledges, self.fields = [], []
        self.zbase = 0                                    # village rows: everything of a nearer row on top

    def u(self, n):
        """GUI units -> pixels at this density (geometry only; details are drawn per density)."""
        return int(round(n * self.k))

    def kv(self, a, b):
        return a if self.k == 1 else b

    def rnd(self, *salt):
        return random.Random(_crc(self.seed, self.prefix, *salt))

    def add(self, name, lay, z=0, cast=None, snow=True, roof=False, raw=False):
        """cast = (dx, dy, steps): the part throws a hard shadow (swept along the offset) onto what is under
        it; snow=False keeps snow off it (smoke, ground); roof=True grows icicles from its lower edge;
        raw=True: its colours are final (a night sky) - the night map skips it."""
        if lay:
            self.parts.append({'name': self.prefix + name, 'lay': lay, 'z': z + self.zbase, 'cast': cast,
                               'snow': snow, 'roof': roof, 'n': len(self.parts), 'group': self.prefix, 'raw': raw})
        return lay

    def remove(self, name):
        self.parts = [p for p in self.parts if p['name'] != self.prefix + name]

    def lay(self, name, z=0, cast=None, snow=True, roof=False):
        """The named part's Layer (created on first use), so several features can draw into one part."""
        full = self.prefix + name
        for p in self.parts:
            if p['name'] == full:
                return p['lay']
        lay = Layer()
        self.parts.append({'name': full, 'lay': lay, 'z': z + self.zbase, 'cast': cast, 'snow': snow, 'roof': roof,
                           'n': len(self.parts), 'group': self.prefix, 'raw': False})
        return lay

    def light(self, x, y, r, kind='lamp'):
        self.lights.append((x, y, r, kind))

    def ledge(self, x0, x1, y):
        """A sill / box top where snow settles (snow pass)."""
        self.ledges.append((self.prefix, x0, x1, y))

    def field(self, mask):
        """A roof plane that snow covers (snow pass)."""
        self.fields.append((self.prefix, set(mask)))

    # -------------------------------------------------------------- finishing passes
    def finish(self):
        parts = sorted(self.parts, key=lambda p: (p['z'], p['n']))
        comp, owner = {}, {}
        out = []
        for p in parts:
            lay = p['lay']
            if p['cast']:
                dx, dy, steps = p['cast']
                n = max(abs(dx), abs(dy), 1)
                sh = Layer()
                for (x, y) in lay:
                    for s in range(1, n + 1):
                        q = (x + round(dx * s / n), y + round(dy * s / n))
                        if q not in lay and q in comp and comp[q] not in EMISSIVE and q not in sh:
                            sh[q] = darker(comp[q], steps)
                if sh:
                    out.append((p['name'] + '_shadow', sh, not p.get('raw')))
                    comp.update(sh)
            out.append((p['name'], lay, not p.get('raw')))
            comp.update(lay)
            for q in lay:
                owner[q] = p['name']
        if self.night and self.lights:
            best = {}
            for (lx, ly, r, kind) in self.lights:
                for (x, y) in disc(lx, ly, r, r * 0.9):
                    if (x, y) in comp and comp[(x, y)] not in EMISSIVE:
                        d = ((x + 0.5 - lx) / r) ** 2 + ((y + 0.5 - ly) / (r * 0.9)) ** 2
                        s = 1.0 if d < 0.3 else 0.5
                        if s > best.get((x, y), (0, None))[0]:
                            best[(x, y)] = (s, kind)
            glow = Layer()
            for q, (s, kind) in best.items():
                glow[q] = lit_c(comp[q], kind, s)
            out.append(((self.prefix or '') + 'light', glow, False))
        allpx = [q for _, lay, _ in out for q in lay]
        if not allpx:
            return [], (0, 0)
        x0, y0, x1, y1 = bbox(allpx)
        W, H = x1 - x0 + 1, y1 - y0 + 1
        P = Parts(W, H)
        night = self.night
        for name, lay, mapped in out:                     # mapped: night-map its colours (not raw / light)

            def draw(im, lay=lay, mapped=mapped):
                px = im.load()
                for (x, y), c in lay.items():
                    px[x - x0, y - y0] = night_c(c) if (night and mapped) else c
                ol = getattr(lay, 'ol', set())
                pixel_perfect(im, only=DARK_LINES | ol | {night_c(c) for c in ol})   # no L-corners in 1 px lines
            P.add(name, draw)
        self.origin = (x0, y0)
        _clean_seams(P.items, W, H)
        return P.items, (W, H)


def _lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def _clean_seams(items, W, H, passes=3):
    """Pixel-perfect across parts: every part is cleaned on its own, but an outline of one part can meet a
    line of another and make an L-corner. Find doubles in dark 1 px lines on the composite (shading.doubles
    plus the check's darker-than-its-sides test) and recolour the corner pixel in the topmost part that
    owns it with the colour outside the corner (transparent on the silhouette)."""
    from shading import doubles
    for _ in range(passes):
        img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        for it in items:
            img.alpha_composite(it['sprite'], (it['x'], it['y']))
        px = img.load()
        fixed = 0
        for (x, y) in doubles(px, W, H):
            c = px[x, y]
            o = [_lum(px[x + dx, y + dy]) for dx, dy in N8 if 0 <= x + dx < W and 0 <= y + dy < H
                 and px[x + dx, y + dy][3] == 255 and px[x + dx, y + dy] != c]
            if o and _lum(c) >= 0.8 * sum(o) / len(o):
                continue                                   # not a dark line
            hs = [dx for dx in (-1, 1) if 0 <= x + dx < W and px[x + dx, y] == c]
            vs = [dy for dy in (-1, 1) if 0 <= y + dy < H and px[x, y + dy] == c]
            if len(hs) != 1 or len(vs) != 1:
                continue
            h, v = hs[0], vs[0]
            out = [px[qx, qy] for qx, qy in ((x - h, y), (x, y - v), (x - h, y - v)) if 0 <= qx < W and 0 <= qy < H]
            out = [q for q in out if q != c] or [(0, 0, 0, 0)]
            new = max(set(out), key=out.count)
            for it in reversed(items):
                sx, sy = x - it['x'], y - it['y']
                sp = it['sprite']
                if 0 <= sx < sp.width and 0 <= sy < sp.height and sp.getpixel((sx, sy))[3]:
                    sp.putpixel((sx, sy), new)
                    fixed += 1
                    break
        if not fixed:
            break


# ------------------------------------------------------------------ textures (fill a mask, world-aligned)
def planks(S, lay, mask, R, y0=0, x0=0, vertical=False, seed=1, board=None, length=None, nails=True):
    """Boards with seams between them, staggered butt joints, a lit top edge per board and grain streaks
    (HD), a few lighter boards; vertical=True for doors, gables, barn walls (lit left edge per board)."""
    k = S.k
    bh = board or S.kv(3, 5)
    L = length or S.kv(11, 20)
    rnd = S.rnd('planks', seed)
    for (x, y) in mask:
        a, b = ((x - x0), (y - y0)) if vertical else ((y - y0), (x - x0))
        row, r = a // bh, a % bh
        off = (_crc(seed, row) % L)
        j = (b + off) % L
        tone = BS
        if r == bh - 1:
            tone = DK if k == 1 else SH
        elif j == 0 and not vertical:
            tone = DK if k == 1 else SH
        elif k == 2 and r == 0:
            tone = LT
        elif k == 2 and nails and j in (2,) and r == 2 and not vertical:
            tone = SH
        elif _crc(seed, row, (b + off) // L) % 5 == 0 and r < bh - 1:
            tone = LT if (k == 1 and r == 0) or (k == 2 and r == 1 and j % 7 < 4) else BS
        lay[(x, y)] = R[tone]
    if k == 2:                                            # grain: dark streaks along the boards, 3-6 px
        pts = sorted(mask)
        for (x, y) in pts:
            if lay.get((x, y)) == R[BS] and rnd.random() < 0.035:
                n = rnd.randint(3, 6)
                for i in range(n):
                    q = (x, y + i) if vertical else (x + i, y)
                    if lay.get(q) == R[BS]:
                        lay[q] = R[DK]
    return lay


def logs_h(S, lay, mask, R, y0=0, seed=2):
    """Stacked horizontal logs (log cabin): each log a horizontal cylinder - lit top, base, dark mid, a
    shadow gap; bark streaks and small lit chips at HD."""
    k = S.k
    lh = S.kv(3, 6)
    prof = (LT, BS, SH) if k == 1 else (LT, LT, BS, BS, DK, SH)
    rnd = S.rnd('logs', seed)
    for (x, y) in mask:
        lay[(x, y)] = R[prof[(y - y0) % lh]]
    if k == 2:
        for (x, y) in sorted(mask):
            r = (y - y0) % lh
            if r in (1, 2, 3) and rnd.random() < 0.05:
                c = R[DK] if r > 1 else R[BS]
                for i in range(rnd.randint(3, 6)):
                    if (x + i, y) in mask and (y - y0) % lh == r:
                        lay[(x + i, y)] = c
            elif r == 0 and rnd.random() < 0.03:
                for i in range(2):
                    if (x + i, y) in mask:
                        lay[(x + i, y)] = R[HI]
    return lay


def log_end(S, lay, cx, cy, R=OAK_LOG, E=LOG_END, small=False):
    """A sawn log end (cabin corners, beam ends): bark rim, end grain with a ring and a lit top-left."""
    k = S.k
    if k == 2 and small:
        pts = rect(cx - 2, cy - 2, cx + 1, cy + 1) - {(cx - 2, cy - 2), (cx + 1, cy - 2), (cx - 2, cy + 1), (cx + 1, cy + 1)}
        pts = {(int(x), int(y)) for x, y in pts}
        for (x, y) in pts:
            lay[(x, y)] = E[LT] if x + y < cx + cy - 1 else E[BS] if x + y < cx + cy + 1 else E[DK]
        return pts
    if k == 1:
        pts = {(cx, cy), (cx + 1, cy), (cx, cy + 1), (cx + 1, cy + 1)}
        lay.fill(pts, E[BS])
        lay.put(cx, cy, E[LT])
        lay.put(cx + 1, cy + 1, E[DK])
        return pts
    pts = disc(cx, cy, 3, 3)
    for (x, y) in pts:
        d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
        c = E[BS]
        if d > 2.3:
            c = R[DK] if x + y > cx + cy - 1 else R[BS]
        elif 1.0 < d < 1.8:
            c = E[DK]
        elif d <= 1.0:
            c = E[LT]
        lay[(x, y)] = c
    lay.put(int(cx) - 2, int(cy) - 2, E[HI])
    return pts


def log_v(S, lay, x0, x1, y0, y1, R=OAK_LOG, seed=3):
    """A vertical log / post: lit left column(s), base, dark right column; bark furrows at HD."""
    w = x1 - x0 + 1
    rnd = S.rnd('logv', seed, x0)
    for x in range(x0, x1 + 1):
        t = (x - x0 + 0.5) / w
        tone = LT if t < 0.34 else BS if t < 0.75 else DK
        if w >= 3 and x == x1:
            tone = SH if S.k == 2 else DK
        for y in range(y0, y1 + 1):
            lay[(x, y)] = R[tone]
    if S.k == 2 and w >= 3:
        for x in range(x0 + 1, x1):
            y = y0 + rnd.randint(0, 3)
            while y <= y1:
                n = rnd.randint(3, 6)
                for i in range(n):
                    if y + i <= y1:
                        lay[(x, y + i)] = R[DK] if lay[(x, y + i)] != R[DK] else R[SH]
                y += n + rnd.randint(4, 9)
    return rect(x0, y0, x1, y1)


def stones(S, lay, mask, R, seed=4, cell=None, R2=None, lit=True):
    """Cobblestone: an irregular jittered grid of stones (nearest-centre cells), 1 px dark joints, every
    stone lit on its top-left rim and dark on its bottom-right, tone varies stone to stone."""
    k = S.k
    cw, ch = cell or S.kv((4, 3), (7, 5))
    if not mask:
        return lay
    x0, y0, x1, y1 = bbox(mask)
    rnd = S.rnd('stones', seed, x0, y0)
    cen = []
    for j, gy in enumerate(range(y0 - ch, y1 + ch + 1, ch)):
        for gx in range(x0 - cw + (j % 2) * (cw // 2), x1 + cw + 1, cw):
            cen.append((gx + rnd.uniform(0.2, 0.8) * cw * 0.7, gy + rnd.uniform(0.2, 0.8) * ch * 0.6,
                        rnd.choice((0, 0, 0, 1, -1, 0, 1)) if k == 2 else rnd.choice((0, 0, 1, -1, 0))))
    grid = {}
    for i, (cx, cy, v) in enumerate(cen):
        grid.setdefault((int(cx // cw), int(cy // ch)), []).append(i)

    def cell_of(x, y):
        gx, gy = int(x // cw), int(y // ch)
        best, bi = 1e9, 0
        for a in (-1, 0, 1):
            for b in (-1, 0, 1):
                for i in grid.get((gx + a, gy + b), ()):
                    cx, cy, _ = cen[i]
                    d = ((x + 0.5 - cx) / cw) ** 2 + ((y + 0.5 - cy) / ch) ** 2
                    if d < best:
                        best, bi = d, i
        return bi
    cid = {p: cell_of(*p) for p in mask}
    for (x, y), i in cid.items():
        v = cen[i][2]
        rr = R2 if (R2 and v == -1) else R
        joint = cid.get((x + 1, y), i) != i or cid.get((x, y + 1), i) != i
        if joint:
            c = R[SH]
        else:
            up = cid.get((x, y - 1), i) != i or cid.get((x - 1, y), i) != i
            dn = cid.get((x + 1, y + 1), i) != i or cid.get((x + 2, y), i) != i or cid.get((x, y + 2), i) != i
            base = {0: BS, 1: BS, -1: DK}[v] if not (R2 and v == -1) else BS
            if up and lit:
                c = rr[HI] if (v == 1 and k == 2) else rr[LT]
            elif dn and k == 2:
                c = rr[DK] if base == BS else rr[SH]
            else:
                c = rr[base]
        lay[(x, y)] = c
    return lay


def bricks(S, lay, mask, R, Rm=MORTAR, y0=0, x0=0, seed=5, bw=None, bh=None, mortar_dark=False):
    """Running-bond bricks: mortar lines, each brick lit along its top (HD) and darker along its bottom, a
    few bricks a tone darker or lighter, the odd chip."""
    k = S.k
    bw = bw or S.kv(5, 9)
    bh = bh or S.kv(3, 5)
    for (x, y) in mask:
        row, r = (y - y0) // bh, (y - y0) % bh
        off = (row % 2) * (bw // 2)
        bi, j = (x - x0 + off) // bw, (x - x0 + off) % bw
        if r == bh - 1 or j == bw - 1:
            c = (R[SH] if mortar_dark else Rm[DK if k == 1 else BS])
            if not mortar_dark and k == 2 and r == bh - 1 and j == bw - 1:
                c = Rm[DK]
        else:
            v = _crc(seed, row, bi) % 9
            t = DK if v < 2 else LT if v == 8 else BS
            if k == 2 and r == 0:
                t = min(HI, t + 1)
            elif k == 2 and r == bh - 2:
                t = max(SH, t - 1)
            elif k == 1 and j == 0 and r == 0 and t == BS:
                t = LT
            c = R[t]
        lay[(x, y)] = c
    return lay


def ashlar(S, lay, mask, R, y0=0, x0=0, seed=6, bw=None, bh=None, cracks=True, moss=0.0):
    """Stone bricks / cut blocks: dark 1 px joints, lit top-left rim per block, dark bottom-right rim, tone
    variation per block, hairline cracks and moss tufts (HD)."""
    k = S.k
    bw = bw or S.kv(8, 14)
    bh = bh or S.kv(4, 7)
    rnd = S.rnd('ashlar', seed)
    for (x, y) in mask:
        row, r = (y - y0) // bh, (y - y0) % bh
        off = (row % 2) * (bw // 2)
        bi, j = (x - x0 + off) // bw, (x - x0 + off) % bw
        v = _crc(seed, row, bi) % 7
        base = DK if v == 0 else LT if v == 6 and k == 2 else BS
        if r == bh - 1 or j == bw - 1:
            c = R[SH]
        elif r == 0 or j == 0:
            c = R[min(HI, base + 1)]
        elif k == 2 and (r == bh - 2 or j == bw - 2):
            c = R[max(SH, base - 1)]
        else:
            c = R[base]
        lay[(x, y)] = c
    if k == 2 and cracks:
        for (x, y) in sorted(mask):
            if rnd.random() < 0.006 and lay.get((x, y)) == R[BS]:
                for i in range(rnd.randint(2, 4)):
                    q = (x + i, y + i // 2 + (i % 2))
                    if q in mask:
                        lay[q] = R[SH]
    if moss:
        for (x, y) in sorted(mask):
            if (x, y + 1) in mask and lay.get((x, y)) == R[SH] and rnd.random() < moss:
                for i in range(rnd.randint(1, S.kv(2, 4))):
                    if (x + i, y) in mask:
                        lay[(x + i, y)] = MOSS[LT if i == 0 else BS]
                        if k == 2 and (x + i, y + 1) in mask and rnd.random() < 0.5:
                            lay[(x + i, y + 1)] = MOSS[DK]
    return lay


def plaster(S, lay, mask, R, seed=7, patches=True):
    """Lime plaster / whitewash: one flat tone, a few soft stains (2-4 px clusters, HD) and the odd patch of
    bare brick near the bottom."""
    k = S.k
    rnd = S.rnd('plaster', seed)
    for p in mask:
        lay[p] = R[BS]
    if k == 2:
        for (x, y) in sorted(mask):
            if rnd.random() < 0.012:
                c = R[DK] if rnd.random() < 0.6 else R[LT]
                for (a, b) in ((0, 0), (1, 0), (0, 1), (2, 0))[:rnd.randint(2, 4)]:
                    if (x + a, y + b) in mask:
                        lay[(x + a, y + b)] = c
    if patches and mask:
        x0, y0, x1, y1 = bbox(mask)
        for (px, py) in ((x0 + S.u(3), y1 - S.u(5)), (x1 - S.u(8), y0 + S.u(4))):
            pm = {(x, y) for (x, y) in rect(px, py, px + S.u(5), py + S.u(2)) if (x, y) in mask
                  and abs(x - px - S.u(2.5)) + abs(y - py - S.u(1)) * 2 < S.u(3.6)}
            bricks(S, lay, pm, BRICK, MORTAR, y0=py, x0=px, seed=seed)
            for (x, y) in edge_ring(pm):
                if (x, y) in mask:
                    lay[(x, y)] = R[DK] if (x, y + 1) in pm or (x + 1, y) in pm else R[LT]
    return lay


def sandstone(S, lay, mask, R, y0=0, x0=0, seed=8):
    """Sandstone blocks: horizontal strata inside each block (a lit top stratum, a darker lower one), soft
    joints, a few pits (HD)."""
    k = S.k
    bh, bw = S.kv((4, 8), (8, 16))
    prof = (LT, BS, BS, DK) if k == 1 else (LT, LT, BS, BS, BS, DK, BS, SH)
    rnd = S.rnd('sand', seed)
    for (x, y) in mask:
        row, r = (y - y0) // bh, (y - y0) % bh
        off = (row % 2) * (bw // 2)
        j = (x - x0 + off) % bw
        t = prof[r]
        if j == bw - 1 and r < bh - 1:
            t = DK
        lay[(x, y)] = R[t]
    if k == 2:
        for (x, y) in sorted(mask):
            if lay[(x, y)] == R[BS] and rnd.random() < 0.02 and lay.get((x + 1, y)) == R[BS]:
                lay[(x, y)] = R[DK]
                lay[(x + 1, y)] = R[DK]
                if (x, y - 1) in mask and lay[(x, y - 1)] == R[BS]:
                    lay[(x, y - 1)] = R[LT]
    return lay


# ------------------------------------------------------------------ roofs
ROOF = {                         # style: ((course rows, tile width) at k=1, at k=2)
    'wood': ((2, 3), (4, 5)),
    'clay': ((3, 2), (4, 4)),
    'slate': ((2, 4), (3, 6)),
    'thatch': ((3, 1), (5, 1)),
}


def roof_px(S, R, a, rr, style='wood', t=0, seed=0):
    """Colour of one roof pixel: a = position along the courses, rr = rows from the course origin (down).
    wood / slate: staggered tiles, a lit top row and a shadow row per course (the butt of the course above);
    clay: barrel tiles in columns, lit left / dark right, rounded bottoms; thatch: straw strands, ragged
    bundle edges. t = tone offset (+1 lit slope, -1 slope turned away)."""
    k = S.k
    ch, tw = ROOF[style][k - 1]
    course, r = rr // ch, rr % ch

    def T(i):
        return R[max(SH, min(HI, i + t))]
    if style == 'clay':
        j = a % tw
        prof = (LT, DK) if k == 1 else (HI, LT, BS, DK)
        if r == ch - 1:
            return T(SH) if (k == 1 or j in (0, tw - 1)) else T(DK)
        if k == 1 and r == 0 and j == 0:
            return T(HI) if (a // tw + course) % 3 == 0 else T(LT)
        if k == 2 and r == 0 and j > 0:
            return T(prof[j] - 1) if j < tw - 1 else T(SH)
        return T(prof[j])
    off = (course % 2) * (tw // 2 + (1 if style == 'slate' else 0))
    j = (a + off) % tw
    tile = (a + off) // tw
    v = _crc(seed, course, tile) % 7
    if style == 'thatch':
        h = _crc(seed, course, a // (1 if k == 1 else 2)) % 9
        if r == ch - 1:
            return T(SH) if h < 5 else T(DK)
        if r == 0:
            return T(LT) if h % 3 else T(BS)
        return T(LT if h < 2 else DK if h > 6 else BS)
    if r == ch - 1:
        return T(SH if k == 2 else DK)
    if j == 0:
        return T(DK if k == 2 or r > 0 else DK)
    body = DK if v == 0 else LT if v >= 5 else BS
    if k == 2 and r == 0:
        body = min(HI, body + 1)
    return T(body)


def gable_roof(S, cx, eave_y, half, thick, R, slope=(1, 1), style='wood', trim=None, seed=0, name='roof',
               z=3, rim=True, solid=False, top_fn=None):
    """Front gable: the roof seen end-on as a thick inverted V - courses parallel to the slope, the left
    slope lit, the right slope a tone darker, a lit rim along the top edge, cut eave ends, a barge board
    (`trim` ramp) under it. Returns (layer, inner(x)) where inner(x) is the first row under roof + trim."""
    k = S.k
    sx, sy = slope
    apex = eave_y - (thick - 1) - ((half - 1) * sy) // sx
    top = top_fn or gable_top(cx, apex, slope)
    apex = top(cx)
    tw = S.kv(1, 2) if trim else 0
    lay = S.lay(name, z, cast=(S.u(1), S.u(1), 1), roof=True)
    band, tmask = set(), set()
    for x in range(cx - half, cx + half):
        yt = top(x)
        left = x < cx
        for y in range(yt, min(yt + thick, eave_y + 1)):
            rr = y - yt
            c = roof_px(S, R, x if left else -x, rr + S.kv(0, 1), style, t=0 if left else -1, seed=seed)
            if rr == 0 and rim:
                c = R[HI] if left else R[LT]
            lay[(x, y)] = c
            band.add((x, y))
        if trim and yt + thick + tw - 1 <= eave_y + tw:
            for i in range(tw):
                y = yt + thick + i
                if y <= eave_y + (1 if k == 2 else 0):
                    tmask.add((x, y))
                    lay[(x, y)] = trim[(LT if i == 0 else DK) if left else (BS if i == 0 else SH)]
    if sy > sx and not top_fn:                            # steep: courses run down the slope, measured across
        rows_ = {}                                        # it from the outer edge, tiles stacked along y
        for (x, y) in band:
            rows_.setdefault((y, x < cx), []).append(x)
        step_ = S.kv(3, 5)
        for (y, left), xs in rows_.items():
            edge_x = min(xs) if left else max(xs)
            n = len(xs)
            for x in xs:
                rr = (x - edge_x) if left else (edge_x - x)
                t = LT if rr < max(1, n // 3) else BS if rr < n - 1 else DK
                if (y - apex) % step_ == 0 and rr > 0:
                    t = DK if rr < n - 1 else SH            # the course lines, edge-on
                c = R[max(SH, min(HI, t - (0 if left else 1)))]
                if rr == 0 and rim:
                    c = R[HI] if left else R[LT]
                lay[(x, y)] = c
    if solid:                                             # a full triangle of roof (spires, tents, pyramids)
        for x in range(cx - half, cx + half):
            left = x < cx
            for y in range(top(x) + thick, eave_y + 1):
                if (x, y) not in band:
                    lay[(x, y)] = roof_px(S, R, x if left else -x, y - top(x) + S.kv(0, 1), style,
                                          t=0 if left else -1, seed=seed)
                    band.add((x, y))
    ends = [cx - half, cx + half - 1]
    for x in ends:
        for y in range(top(x) + 1, eave_y + 1):
            if (x, y) in band:
                lay[(x, y)] = R[LT] if x < cx else R[SH]
    if k == 2:                                             # ridge cap: a lit tile over the apex
        for (x, y) in ((cx - 2, apex - 1), (cx - 1, apex - 1), (cx, apex - 1), (cx + 1, apex - 1)):
            lay[(x, y)] = R[HI] if x < cx else R[BS]
            band.add((x, y))
    outline(lay, band | tmask, R)
    if sy <= sx or top_fn:
        S.field(band)                                     # steep slopes shed snow: caps only
    return lay, (lambda x: top(x) + thick + tw), top


def hip_roof(S, x0, x1, eave_y, h, R, style='wood', slope=(1, 1), fascia=None, seed=0, name='roof', z=3,
             ridge=True, ends=True):
    """Eave-front roof: the roof plane seen from the front-above as a trapezoid h rows tall whose bottom row
    is eave_y - courses parallel to the eave, hip ends (lit left, dark right), the tiles' butt ends or a
    `fascia` board along the bottom, ridge tiles along the top. slope=(run, rise) of the hip sides; (0, 1)
    gives straight gable ends. Returns (layer, {x: top y})."""
    k = S.k
    run, rise = slope
    fh = S.kv(1, 2)
    ch = ROOF[style][k - 1][0]
    ew = S.kv(2, 4)
    lay = S.lay(name, z, cast=(S.u(1), S.u(2), 1), roof=True)
    m, plane, tops = set(), set(), {}
    for j in range(h):
        y = eave_y - j
        d = (j * run) // rise if rise else 0
        xl, xr = x0 + d, x1 - d
        for x in range(xl, xr + 1):
            m.add((x, y))
            tops[x] = y
            if j < fh:
                if fascia:
                    c = fascia[DK if j == 0 else LT] if k == 2 else fascia[BS]
                else:
                    c = roof_px(S, R, x, ch - 1 - j % ch, style, t=-1, seed=seed) if j else R[SH]
                lay[(x, y)] = c
                continue
            rr = 100 * ch - 1 - (j - fh)
            t = 0
            if ends and x - xl < ew:
                t = 1
            elif ends and xr - x < ew:
                t = -1
            c = roof_px(S, R, x, rr, style, t=t, seed=seed)
            if ends and run and (x - xl == ew or xr - x == ew - 1) and k == 2:
                c = R[DK] if x - xl == ew else R[SH]       # the hip lines
            lay[(x, y)] = c
            plane.add((x, y))
    if ridge:
        ytop = eave_y - h + 1
        for x in range(x0, x1 + 1):
            if (x, ytop) in m:
                lay[(x, ytop)] = R[HI] if (x // S.kv(3, 5)) % 2 == 0 else R[LT]
                if k == 2 and (x, ytop + 1) in m:
                    lay[(x, ytop + 1)] = R[BS]
    outline(lay, m, R)
    S.field(plane)
    return lay, tops


# ------------------------------------------------------------------ openings
def _shape(style, x, y, w, h):
    """Outer mask of a window / door opening."""
    if style in ('arch', 'arch_door'):
        r = w // 2
        m = set()
        for (px, py) in rect(x, y, x + w - 1, y + h - 1):
            dy = py - (y + r)
            if dy >= 0:
                m.add((px, py))
            else:
                if ((px + 0.5 - (x + w / 2)) / (w / 2)) ** 2 + ((py + 0.5 - (y + r)) / r) ** 2 <= 1.0:
                    m.add((px, py))
        return m
    if style == 'round':
        return disc(x + w / 2, y + h / 2, w / 2, h / 2)
    if style == 'lancet':
        m = set()
        half = w / 2
        for j in range(h):
            hw = min(half, (j + 2) // 2 + (0.5 if w % 2 else 0))
            for px in range(x, x + w):
                if abs(px + 0.5 - (x + half)) <= hw:
                    m.add((px, y + j))
        return m
    return rect(x, y, x + w - 1, y + h - 1)


def _erode(m, n):
    for _ in range(n):
        m = {p for p in m if all((p[0] + dx, p[1] + dy) in m for dx, dy in N4)}
    return m


def window(S, x, y, w, h, frame=OAK, style='cross', sill=STONE, shutters=None, box=False, seed=0, lay=None,
           light=True, glass_ramp=None):
    """A window set in a wall: frame (lit top / left bars, dark bottom / right), glass recessed behind it
    (shadow row under the top bar, a diagonal reflection streak and glint by day; warm light with a bright
    core by night), muntins, a sill (snow settles on it), optional shutters (vertical boards, a Z brace at
    HD) and a flower box with flowers in front of the lowest panes. Styles: cross, single, tall, grid,
    arch, round, lancet, slit (no glass: a dark slot), dark (unglazed opening)."""
    k = S.k
    night = S.night
    lay = lay if lay is not None else S.lay('windows', 4, cast=(S.u(1), S.u(1), 1))
    f = S.kv(1, 2) if style not in ('slit', 'dark') else 0
    if style == 'round' and k == 1:
        f = 1
    outer = _shape(style, x, y, w, h)
    inner = _erode(outer, f) if f else set(outer)
    fr = outer - inner
    gx0, gy0, gx1, gy1 = bbox(inner) if inner else (x, y, x, y)
    mx, my = (gx0 + gx1) // 2, (gy0 + gy1) // 2
    G = glass_ramp or (GLOW if night else GLASS)
    if style == 'grid' and k == 2:
        bars = {(px, py) for (px, py) in inner if (px - gx0) % 4 == 3 or (py - gy0) % 5 == 4}
    elif style == 'cross' or (style == 'grid' and k == 1) or style == 'round':
        bars = {(px, py) for (px, py) in inner if px == mx or py == my}
    elif style == 'tall':
        bars = {(px, py) for (px, py) in inner if py == my}
    elif style in ('arch', 'lancet'):
        bars = {(px, py) for (px, py) in inner if px == mx or (k == 2 and py == my + 1)}
    else:
        bars = set()
    if style in ('slit', 'dark'):
        dark = DEEP if style == 'slit' else DARK_OAK
        for (px, py) in outer:
            lay[(px, py)] = (GLOW[DK] if py > y + h // 2 else GLOW[SH]) if night and style == 'dark' else dark[O]
        for (px, py) in outer:
            if (px, py - 1) not in outer or (px - 1, py) not in outer:
                lay[(px, py)] = dark[SH] if not night else dark[O]
        if style == 'slit' and k == 2:
            for px in range(x - 2, x + w + 2):
                lay[(px, y + h // 2)] = DEEP[O]
        if light and night and style == 'dark':
            S.light(x + w / 2, y + h / 2, max(w, h) * 0.5 + S.u(2))
        return outer
    for (px, py) in fr:
        t = (py < y + f or px < x + f) if style not in ('round', 'arch', 'lancet') else \
            ((px, py - 1) not in outer or (px - 1, py) not in outer) and not ((px, py + 1) not in outer
                                                                            or (px + 1, py) not in outer)
        b = (py > y + h - 1 - f or px > x + w - 1 - f) if style not in ('round', 'arch', 'lancet') else \
            ((px, py + 1) not in outer or (px + 1, py) not in outer) and not t
        lay[(px, py)] = frame[LT] if t and not b else frame[DK] if b and not t else frame[BS]
    if k == 2 and style not in ('round',):
        lay[(x, y)] = frame[HI] if style not in ('arch', 'lancet') else lay.get((x, y), frame[LT])
    panes = inner - bars
    for (px, py) in panes:
        up = (px, py - 1) not in panes
        lf = (px - 1, py) not in panes
        if night:
            c = G[BS] if up or (k == 2 and lf) else G[LT]
        else:
            c = (G[SH] if k == 2 else G[DK]) if up else G[DK] if (k == 2 and lf) else G[BS]
        lay[(px, py)] = c
    # day: a reflection streak per pane (lower-left -> upper-right); night: a bright core
    if not night:
        for (px, py) in panes:
            s = (px - gx0) + (gy1 - py)
            band = s % S.kv(7, 11)
            if band in S.kv((3,), (4, 5)) and (px, py - 1) in panes:
                lay[(px, py)] = G[LT]
            elif k == 2 and band == 7 and (px, py - 1) in panes:
                lay[(px, py)] = G[HI] if (px + py) % 3 else G[LT]
    else:
        core = {(px, py) for (px, py) in panes if abs(px + 0.5 - (gx0 + gx1 + 1) / 2) < (gx1 - gx0 + 1) * 0.28
                and abs(py + 0.5 - (gy0 + gy1 + 1) / 2) < (gy1 - gy0 + 1) * 0.3 and (px, py - 1) in panes}
        for p in core:
            lay[p] = G[HI]
    for (px, py) in bars:
        lay[(px, py)] = (frame[SH] if night else frame[BS]) if (px, py) not in fr else lay[(px, py)]
        if not night and k == 2 and px != mx and (px, py) in bars:
            lay[(px, py)] = frame[LT]
    if light and night:
        S.light(x + w / 2, y + h / 2, max(w, h) * 0.5 + S.u(1.8))
    solid = set(outer)
    if shutters:
        sw = max(S.kv(2, 3), w // 3)
        for side in (-1, 1):
            sx0 = x - sw if side < 0 else x + w
            sm = rect(sx0, y, sx0 + sw - 1, y + h - 1)
            for (px, py) in sm:
                i = px - sx0
                c = shutters[LT] if i == 0 else shutters[BS]
                if k == 2 and i == sw - 1:
                    c = shutters[DK]
                if py in (y, y + h - 1) and k == 2:
                    c = shutters[LT] if py == y else shutters[DK]
                lay[(px, py)] = c
            if k == 2:                                     # Z brace
                for j in range(h - 2):
                    px = sx0 + (sw - 1) - (j * sw) // max(1, h - 2)
                    lay[(px, y + 1 + j)] = shutters[LT] if side < 0 else shutters[BS]
            outline(lay, sm, shutters)
            solid |= sm
    outline(lay, outer, frame)
    if box:
        flower_box(S, x - S.kv(0, 1), y + h, w + S.kv(0, 2), seed=seed)
    elif sill:
        sh = S.kv(1, 2)
        sm = rect(x - 1, y + h, x + w, y + h + sh - 1)
        for (px, py) in sm:
            lay[(px, py)] = sill[LT] if py == y + h else sill[DK]
        if k == 2:
            lay[(x - 1, y + h)] = sill[HI]
        outline(lay, sm, sill, over=True)
        S.ledge(x - 1, x + w, y + h)
    return solid


def flower_box(S, x, y, w, seed=0):
    """A planter under a window: a plank box, soil, leaves and flowers rising in front of the lowest panes,
    trailing leaves over the box front (HD)."""
    k = S.k
    lay = S.lay('flowers', 5, cast=(S.u(1), S.u(1), 1))
    bh = S.kv(2, 4)
    box = rect(x, y, x + w - 1, y + bh - 1)
    for (px, py) in box:
        r = py - y
        lay[(px, py)] = DARK_OAK[LT] if r == 0 else DARK_OAK[DK] if r == bh - 1 else DARK_OAK[BS]
    if k == 2:
        for px in range(x + 3, x + w - 1, 5):
            lay[(px, y + 1)] = DARK_OAK[SH]
    rnd = S.rnd('flowers', seed, x)
    leaf_h = S.kv(1, 2)
    for px in range(x, x + w):
        for j in range(1, leaf_h + 1):
            if j == leaf_h and (px + seed) % 2:
                continue
            lay[(px, y - j)] = LEAVES[LT] if (px + j) % 3 == 0 else LEAVES[BS]
    step = S.kv(2, 3)
    heads = []
    for i, px in enumerate(range(x + (1 if k == 2 else 0), x + w - (1 if k == 2 else 0), step)):
        Rf = FLOWERS[(_crc(seed, x, i) + i) % len(FLOWERS)]
        hy = y - leaf_h - (1 if (i % 2 and k == 2) else 0)
        if k == 1:
            lay[(px, hy)] = Rf[LT]
            heads.append((px, hy))
        else:
            for (a, b), t in (((0, 0), HI), ((1, 0), LT), ((0, 1), LT), ((1, 1), BS)):
                lay[(px + a, hy - 1 + b)] = Rf[t]
            heads.append((px, hy - 1))
    if k == 2:
        for px in range(x + 1, x + w - 1, 4):
            if rnd.random() < 0.7:
                for j in range(rnd.randint(1, 3)):
                    lay[(px + (j % 2), y + 1 + j)] = LEAVES[BS if j else LT]
    outline(lay, set(lay) & (box | {(px, py) for (px, py) in lay if py < y}), DARK_OAK)
    S.ledge(x, x + w - 1, y - leaf_h)
    return box


def door(S, x, y, w, h, R=OAK, frame=DARK_OAK, style='plank', handle=None, glass=True, lay=None, light=False):
    """A door: casing (frame ramp) round the top and sides, the leaf recessed in it - vertical boards with a
    lit left edge, the casing's shadow along the top and left of the leaf, rails and hinges (HD), small
    panes at the top (Minecraft-style; lit at night) and a handle with a glint. style: plank, arch, double,
    round (mushroom house), open (a dark doorway)."""
    k = S.k
    lay = lay if lay is not None else S.lay('door', 4, cast=(S.u(1), S.u(1), 1))
    handle = handle or GOLDR
    f = S.kv(1, 2)
    shp = 'arch' if style in ('arch', 'round', 'open_arch') else 'rect'
    outer = _shape(shp, x, y, w, h)
    leaf = {(px, py) for (px, py) in outer if px >= x + f and px <= x + w - 1 - f and
            all((px, py - d) in outer for d in range(1, f + 1))}
    for (px, py) in outer - leaf:
        lit = px < x + w // 2
        lay[(px, py)] = frame[LT if lit else DK] if (px - 1, py) not in outer or (px + 1, py) not in outer or \
            (px, py - 1) not in outer else frame[BS]
    if style in ('open', 'open_arch'):
        lx0, ly0, lx1, ly1 = bbox(leaf)
        for (px, py) in leaf:                               # a dark interior; at night lamplight on its floor
            lay[(px, py)] = (GLOW[SH] if py < ly1 - (ly1 - ly0) // 3 else GLOW[DK]) if S.night else DARK_OAK[O]
        for (px, py) in leaf:
            if (px, py - 1) not in leaf or (px - 1, py) not in leaf:
                lay[(px, py)] = DARK_OAK[O] if S.night else DARK_OAK[SH]
        if S.night:
            S.light(x + w / 2, y + h * 0.8, max(w, h) * 0.45)
        outline(lay, outer, frame)
        return outer
    lx0, ly0, lx1, ly1 = bbox(leaf)
    bw = S.kv(2, 3)
    mid = (lx0 + lx1 + 1) // 2
    for (px, py) in leaf:
        j = (px - lx0) % bw
        c = R[BS]
        if j == bw - 1 and px != lx1:
            c = R[DK]
        if style == 'double' and px == mid - 1:
            c = R[SH]
        if (px, py - 1) not in leaf:
            c = R[DK]                                       # casing shadow along the top
        elif px == lx0:
            c = R[DK] if k == 2 else R[BS]
        elif px == lx0 + 1 and k == 2:
            c = R[LT]
        lay[(px, py)] = c
    if k == 2:                                             # rails: lit top row, dark bottom row
        for ry in (ly0 + (ly1 - ly0) // 3, ly0 + 2 * (ly1 - ly0) // 3 + 1):
            for px in range(lx0 + 1, lx1 + 1):
                if (px, ry) in leaf:
                    lay[(px, ry)] = R[LT]
                if (px, ry + 1) in leaf:
                    lay[(px, ry + 1)] = R[DK]
        for ry in (ly0 + (ly1 - ly0) // 3, ly0 + 2 * (ly1 - ly0) // 3 + 1):     # strap hinges on the left
            for i in range(3):
                if (lx0 + i, ry) in leaf:
                    lay[(lx0 + i, ry)] = DARK_IRON[LT if i == 0 else BS]
    if glass and style != 'round':
        gh = S.kv(2, 4)
        gy0 = ly0 + S.kv(1, 2)
        leaves = [(lx0, mid - 1), (mid, lx1)] if style == 'double' else [(lx0, lx1)]
        for (a, b) in leaves:
            gw = b - a + 1
            pw = S.kv(1, 2) if gw <= S.kv(4, 7) else S.kv(1, 3)
            cx_ = (a + b + 1) // 2
            for px in list(range(cx_ - pw - (1 if k == 2 else 0), cx_ - (1 if k == 2 else 0))) + \
                    list(range(cx_ + (0 if k == 1 else 0), cx_ + pw)):
                for py in range(gy0, gy0 + gh):
                    if (px, py) in leaf:
                        up = py == gy0
                        if S.night:
                            lay[(px, py)] = GLOW[BS] if up else GLOW[HI if (k == 2 and py == gy0 + 1) else LT]
                        else:
                            lay[(px, py)] = GLASS[SH] if up else GLASS[BS] if (px + py) % 3 else GLASS[LT]
            if S.night:
                S.light(cx_, gy0 + gh / 2, S.u(5))
    hx = lx1 - S.kv(1, 2) if style != 'double' else mid - 2
    hy = (ly0 + ly1) // 2 + S.kv(0, 1)
    if k == 1:
        lay[(hx, hy)] = handle[LT]
    else:
        lay[(hx, hy)] = handle[HI]
        lay[(hx + 1, hy)] = handle[BS]
        lay[(hx, hy + 1)] = handle[BS]
        lay[(hx + 1, hy + 1)] = handle[DK]
        if style == 'double':
            for (a, b) in ((mid + 1, hy), (mid + 2, hy), (mid + 1, hy + 1), (mid + 2, hy + 1)):
                lay[(a, b)] = handle[(HI, BS, BS, DK)[(a - mid - 1) + 2 * (b - hy)]]
    outline(lay, outer, frame)
    return outer


# ------------------------------------------------------------------ lights, chimneys, signs, props
def lantern(S, x, y, side=1, arm=None, name='lanterns', post=False):
    """A wall lantern on an iron bracket from (x, y) reaching `side`; the lantern hangs from the arm's end:
    an iron cage (lit left bar, dark right), glowing glass with a bright core, cap and base. Night: a warm
    light pool. post=True: a lamp post's head (no arm). Returns the glow centre."""
    k = S.k
    lay = S.lay(name, 6, cast=(S.u(1), S.u(1), 1))
    I = DARK_IRON
    arm = S.kv(3, 5) if arm is None else arm
    if not post:
        for i in range(arm):
            lay[(x + side * i, y)] = I[LT] if k == 1 else I[BS]
            if k == 2:
                lay[(x + side * i, y - 1)] = I[LT] if i else I[BS]
        if k == 2:
            lay[(x, y + 1)] = I[BS]
            lay[(x + side, y + 1)] = I[DK]
        lx = x + side * (arm - 1)
        ly = y + (1 if k == 1 else 1)
        for j in range(S.kv(1, 2)):
            lay[(lx, ly + j)] = I[DK]
        ly += S.kv(1, 2)
    else:
        lx, ly = x, y
    m = set()
    if k == 1:
        rows = ('.c.', 'cgc', 'cGc', 'bbb')
        x0 = lx - 1
    else:
        rows = ('..c..', '.ccc.', 'cCCCc', 'cgGgc', 'cGHGc', 'cgGgc', 'bbbbb')
        x0 = lx - 2
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch == '.':
                continue
            px, py = x0 + i, ly + j
            c = {'c': I[LT] if i < len(row) // 2 else I[DK] if i > len(row) // 2 else I[BS],
                 'C': I[BS], 'b': I[DK] if i else I[BS], 'g': GLOW[LT if not S.night else HI],
                 'G': GLOW[HI] if S.night or k == 1 else GLOW[LT], 'H': GLOW[HI]}[ch]
            if ch == 'g' and k == 1:
                c = GLOW[HI] if S.night else GLOW[LT]
            lay[(px, py)] = c
            m.add((px, py))
    outline(lay, m, I)
    cy = ly + len(rows) // 2
    if S.night:
        S.light(lx + 0.5, cy, S.u(10))
    return (lx, cy)


def torch(S, x, y, name='torches'):
    """A wall torch: a stick with a flame on top (fire ramp, emissive), a fire light pool at night."""
    k = S.k
    lay = S.lay(name, 6)
    if k == 1:
        for j in range(3):
            lay[(x, y + j)] = OAK_LOG[LT] if j else OAK_LOG[BS]
        lay[(x, y - 1)] = FIRE[HI]
        lay[(x, y - 2)] = FIRE[LT]
        m = rect(x, y - 2, x, y + 2)
    else:
        for j in range(6):
            lay[(x, y + j)] = OAK_LOG[LT]
            lay[(x + 1, y + j)] = OAK_LOG[DK]
        for (a, b, t) in ((0, -1, HI), (1, -1, LT), (0, -2, HI), (1, -2, BS), (0, -3, LT), (1, -4, BS), (0, -4, DK),
                          (-1, -1, BS), (2, -1, DK)):
            lay[(x + a, y + b)] = FIRE[t]
        m = set(lay) & (rect(x - 1, y - 4, x + 2, y + 5))
    outline(lay, m, OAK_LOG)
    if S.night:
        S.light(x + 0.5, y - S.kv(1, 2), S.u(11), 'fire')


def chimney(S, x0, w, y_top, y_bot, R=BRICK, kind='brick', z=-1, smoke=True, name='chimney', seed=0):
    """A chimney: a stack of bricks / stones (lit left column, dark right), a wider cap with a lit top, smoke
    rising and drifting right. z<0 puts it behind a gable roof (its foot is hidden by the roof band)."""
    k = S.k
    lay = S.lay(name, z, cast=(S.u(1), S.u(1), 1))
    cap_h = S.kv(1, 2)
    body = rect(x0, y_top + cap_h, x0 + w - 1, y_bot)
    if kind == 'brick':
        bricks(S, lay, body, R, MORTAR, y0=y_top + cap_h, x0=x0, bw=S.kv(3, 5), bh=S.kv(2, 3), seed=seed)
    else:
        stones(S, lay, body, R, cell=S.kv((3, 2), (4, 3)), seed=seed)
    for y in range(y_top + cap_h, y_bot + 1):
        lay[(x0, y)] = lighter(lay[(x0, y)])
        lay[(x0 + w - 1, y)] = darker(lay[(x0 + w - 1, y)])
    Rc = STONE if kind == 'brick' else R
    cap = rect(x0 - 1, y_top, x0 + w, y_top + cap_h - 1)
    for (px, py) in cap:
        lay[(px, py)] = Rc[LT] if py == y_top else Rc[DK]
        if k == 2 and py == y_top and px < x0 + w // 2:
            lay[(px, py)] = Rc[HI]
    if k == 2:
        for px in range(x0 + 1, x0 + w - 1):
            lay[(px, y_top)] = Rc[SH] if px > x0 + 1 else Rc[DK]   # the dark flue mouth
    outline(lay, body | cap, R)
    if smoke:
        puff(S, x0 + w // 2, y_top - 1, seed=seed)
    return body | cap


def puff(S, x, y, n=3, seed=0, name='smoke'):
    """Smoke: puffs growing as they rise and drift right, lit top-left, darker bottom-right rim, no outline
    (soft material); the lowest puff is the densest and drawn last."""
    lay = S.lay(name, 8, snow=False)
    rnd = S.rnd('smoke', seed, x)
    cx, cy = x + 0.5, y
    puffs = []
    for i in range(n):
        r = S.kv(1.1, 2.1) + i * S.kv(0.45, 0.85)
        cy -= r + S.kv(1.2, 2.2) + (r * 0.6 if i else 0)
        cx += S.kv(0.8, 1.6) + rnd.random() * S.kv(1.0, 1.8)
        puffs.append((cx, cy, r))
    for (cx, cy, r) in reversed(puffs):
        pts = disc(cx, cy, r)
        for (px, py) in pts:
            d = (px + 0.5 - cx) / r + (py + 0.5 - cy) / r
            t = HI if d < -0.7 else LT if d < 0.35 else BS
            if (px + 1, py + 1) not in pts and d > 0:
                t = DK
            lay[(px, py)] = SMOKE[t]


SIGN_ICONS = {                    # tiny painted pictograms; letters -> (ramp, tone)
    'mug': (("aa.", "abc", "bb."),
            (".ffff..", "fffffc.", "abbbab.", "abbbacc", "abbba.c", "abbbacc", "aaaaa..")),
    'anvil': (("aaa", ".a.", "aaa"),
              ("ddddddd", ".ddddd.", "..ddd..", "..ddd..", ".ddddd.", "ddddddd")),
    'coin': ((".g.", "ghg", ".g."),
             ("..ggg..", ".ghhhg.", "ghgggqg", "ghggqqg", "gggqqqg", ".gqqqg.", "..ggg..")),
    'potion': ((".c.", "pPp", "ppp"),
               ("...c...", "..cWc..", "..pPp..", ".ppPpp.", "pppppPp", "ppppppp", ".ppppp.")),
    'pick': (("ddd", ".w.", "w.."),
             (".ddddd.", "d..w..d", "...w...", "..w....", "..w....", ".w.....", ".w.....")),
    'bread': (("bbb", "bab"),
              (".bbbbb.", "bbabab.", "bbbbbbb", ".aaaaa.")),
}
_ICON_COL = {'a': (HAY, DK), 'b': (HAY, LT), 'c': (CREAMR, BS), 'f': (CREAMR, HI), 'd': (DARK_IRON, BS),
             'g': (GOLDR, BS), 'h': (GOLDR, HI), 'q': (GOLDR, DK), 'p': (PORTAL, BS), 'P': (PORTAL, HI),
             'W': (CREAMR, HI), 'w': (OAK, BS)}


def hanging_sign(S, x, y, side=1, icon='mug', R=SPRUCE, name='sign'):
    """A hanging sign on an iron bracket from the wall at (x, y): arm (+ a curl at HD), two chains, a plank
    board with a lit top-left edge and a painted pictogram."""
    k = S.k
    lay = S.lay(name, 6, cast=(S.u(1), S.u(1), 1))
    I = DARK_IRON
    arm = S.kv(8, 15)
    for i in range(arm):
        lay[(x + side * i, y)] = I[LT] if k == 1 else I[BS]
        if k == 2:
            lay[(x + side * i, y - 1)] = I[LT]
    if k == 2:                                            # a diagonal brace and a curl at the end
        for i in range(4):
            lay[(x + side * i, y + 4 - i)] = I[BS]
        e = x + side * (arm - 1)
        for (a, b) in ((0, -2), (side, -2), (side, -1)):
            lay[(e + a, y + b)] = I[DK]
    bw, bh = S.kv(7, 13), S.kv(5, 10)
    bx0 = x + side * S.kv(1, 2) if side > 0 else x - S.kv(1, 2) - bw + 1
    ch = S.kv(1, 2)
    for cxx in (bx0 + S.kv(1, 2), bx0 + bw - 1 - S.kv(1, 2)):
        for j in range(1, ch + 1):
            lay[(cxx, y + j)] = I[DK]
    by0 = y + ch + 1
    board = rect(bx0, by0, bx0 + bw - 1, by0 + bh - 1)
    for (px, py) in board:
        i, j = px - bx0, py - by0
        c = R[BS]
        if j == 0 or i == 0:
            c = R[LT]
        if j == bh - 1 or i == bw - 1:
            c = R[DK]
        if k == 2 and j == bh // 2 and 0 < i < bw - 1:
            c = R[DK]
        lay[(px, py)] = c
    rows = SIGN_ICONS[icon][k - 1]
    iw, ih = len(rows[0]), len(rows)
    ix, iy = bx0 + (bw - iw) // 2, by0 + (bh - ih) // 2 + (1 if k == 1 and bh - ih > 1 else 0)
    for j, row in enumerate(rows):
        for i, chh in enumerate(row):
            if chh in _ICON_COL:
                r, t = _ICON_COL[chh]
                lay[(ix + i, iy + j)] = r[t]
    outline(lay, board, R)


def fence(S, x0, x1, yb, R=OAK, name='fence', z=-2, h=None):
    """A Minecraft-like fence: posts (lit left column, dark right, lit top) every few pixels, two rails (lit
    top row, dark bottom), outlined in the wood's dark tone."""
    k = S.k
    lay = S.lay(name, z, cast=(S.u(1), 0, 1))
    h = h or S.kv(6, 11)
    pw = S.kv(2, 3)
    sp = S.kv(5, 9)
    posts = list(range(x0, x1 - pw + 2, sp))
    if posts[-1] != x1 - pw + 1:
        posts.append(x1 - pw + 1)
    m = set()
    rh = S.kv(1, 2)
    for ry in (yb - int(h * 0.72), yb - int(h * 0.32)):
        for px in range(x0, x1 + 1):
            for j in range(rh):
                lay[(px, ry + j)] = R[LT if j == 0 and k == 2 else BS] if rh > 1 else R[BS]
                if k == 2 and j == rh - 1:
                    lay[(px, ry + j)] = R[DK]
                m.add((px, ry + j))
    for px in posts:
        for py in range(yb - h + 1, yb + 1):
            for i in range(pw):
                c = R[LT] if i == 0 else R[DK] if i == pw - 1 else R[BS]
                if py == yb - h + 1:
                    c = R[HI] if i == 0 else R[LT]
                lay[(px + i, py)] = c
                m.add((px + i, py))
    outline(lay, m, R)
    return m


def barrel(S, x, yb, R=SPRUCE, name='props', hoops=DARK_IRON):
    """A barrel standing at (x, yb): bulging staves (lit left, dark right), iron hoops, a lit lid rim."""
    k = S.k
    lay = S.lay(name, 5, cast=(S.u(1), 0, 1))
    w, h = S.kv(5, 9), S.kv(6, 11)
    m = set()
    for j in range(h):
        bul = 1 if 1 < j < h - 2 else 0
        for i in range(-bul, w + bul):
            t = (i + bul + 0.5) / (w + 2 * bul)
            tone = LT if t < 0.3 else BS if t < 0.72 else DK
            if k == 2 and (i - 1) % 3 == 2 and 0 < j < h - 1:
                tone = max(SH, tone - 1)
            lay[(x + i, yb - h + 1 + j)] = R[tone]
            m.add((x + i, yb - h + 1 + j))
    for j in (S.kv(1, 2), h - S.kv(2, 3)):
        for i in range(-1, w + 1):
            if (x + i, yb - h + 1 + j) in m:
                lay[(x + i, yb - h + 1 + j)] = hoops[LT if i < w // 2 else DK]
    for i in range(w):
        lay[(x + i, yb - h + 1)] = R[HI if i < w // 2 else LT]
    outline(lay, m, R)
    return m


def crate(S, x, yb, w=None, R=OAK, name='props', fill=None):
    """A wooden crate (frame boards + a diagonal brace at HD), optionally heaped with produce (`fill` ramp)."""
    k = S.k
    lay = S.lay(name, 5, cast=(S.u(1), 0, 1))
    w = w or S.kv(5, 9)
    h = S.kv(4, 7)
    m = rect(x, yb - h + 1, x + w - 1, yb)
    for (px, py) in m:
        i, j = px - x, py - (yb - h + 1)
        c = R[BS]
        if j == 0:
            c = R[LT]
        elif j == h - 1 or i == w - 1:
            c = R[DK]
        elif i == 0:
            c = R[LT]
        elif k == 2 and (j - 1) == ((i - 1) * (h - 3)) // max(1, w - 3):
            c = R[LT]
        lay[(px, py)] = c
    if fill:
        for i in range(w):
            hh = S.kv(1, 2) + (1 if 0 < i < w - 1 and k == 2 else 0)
            for j in range(hh):
                t = HI if (i + j) % 3 == 0 and j == hh - 1 else LT if j == hh - 1 else BS
                if i == w - 1:
                    t = DK
                lay[(x + i, yb - h - j)] = fill[t]
                m.add((x + i, yb - h - j))
    outline(lay, m, R)
    return m


# ------------------------------------------------------------------ ground
def ground(S, x0, x1, gy, kind='grass', foot=None, paths=(), back=None, front=None, name='ground', shadow_len=None):
    """The island a building stands on: a top surface `back` rows behind the base line and `front` rows in
    front, a dirt front face with the grass (sand, snow) hanging over its edge; the building's hard cast
    shadow falls back-right on the surface, a contact shadow runs along its base, a path leads from each
    door to the front edge. kind: grass, sand, snow, stone, dirt (snow=True turns grass into snow)."""
    k = S.k
    if not S.ground:
        return None
    if S.snow:
        kind = 'snow'
    Rs = {'grass': GRASS, 'sand': SAND, 'snow': SNOW, 'stone': COBBLE, 'dirt': DIRT}[kind]
    Rf = SANDSTONE if kind == 'sand' else DIRT
    back = S.u(4) if back is None else back
    front = S.u(7) if front is None else front
    depth = S.kv(3, 6)
    lay = S.lay(name, -10, snow=False)
    rnd = S.rnd('ground', x0)
    ytop, yf = gy - back, gy + front
    cut = S.kv(1, 2)
    top = {(x, y) for (x, y) in rect(x0, ytop, x1, yf - 1)        # rounded back corners; the front corners
           if not ((x < x0 + cut or x > x1 - cut) and y == ytop) and    # run on into the dirt face
           not (k == 2 and (x == x0 or x == x1) and y == ytop + 1)}
    face = {(x, y) for (x, y) in rect(x0, yf, x1, yf + depth - 1)
            if not ((x < x0 + cut or x > x1 - cut) and y == yf + depth - 1)}
    for (x, y) in top:
        c = Rs[BS]
        if (x, y - 1) not in top or (x - 1, y) not in top:
            c = Rs[LT]
        elif (x + 1, y) not in top:
            c = Rs[DK]
        lay[(x, y)] = c
    if kind == 'stone':
        stones(S, lay, top, COBBLE, seed=5)
    else:
        for (x, y) in sorted(top):
            r = rnd.random()
            if lay[(x, y)] != Rs[BS]:
                continue
            if kind in ('grass', 'dirt') and r < S.kv(0.08, 0.07):
                n = 2
                for j in range(n):
                    if lay.get((x, y - j)) == Rs[BS]:
                        lay[(x, y - j)] = Rs[LT] if r < 0.05 else Rs[DK]
                if k == 2 and r < 0.005:
                    Rf_ = FLOWERS[int(r * 1000) % 4]
                    lay[(x, y - 1)] = Rf_[LT]
            elif kind in ('sand', 'snow') and r < 0.04:
                for i in range(S.kv(2, 4)):
                    if lay.get((x + i, y)) == Rs[BS]:
                        lay[(x + i, y)] = Rs[LT] if r < 0.02 else Rs[DK]
    if foot:
        fx0, fx1 = foot
        L = shadow_len if shadow_len is not None else S.u(6)
        for y in range(ytop, gy):
            for x in range(fx1 + 1, fx1 + 1 + L - (gy - 1 - y) // 2 * 0):
                if (x, y) in top:
                    lay[(x, y)] = Rs[DK] if kind != 'snow' else Rs[DK]
        for x in range(fx0, fx1 + 1):
            for j in range(S.kv(1, 2)):
                if (x, gy + j) in top:
                    lay[(x, gy + j)] = Rs[DK] if j == 0 else Rs[BS] if (x + j) % 3 else Rs[DK]
    for (px0, px1) in paths:
        for y in range(gy, yf):
            d = (y - gy) // S.kv(2, 3)
            a, b = px0 - d, px1 + d
            for x in range(a, b + 1):
                if (x, y) not in top:
                    continue
                c = PATH[BS] if kind != 'snow' else SNOW[DK]
                if x == a:
                    c = (PATH if kind != 'snow' else SNOW)[DK if kind != 'snow' else SH]
                elif x == b:
                    c = (PATH if kind != 'snow' else SNOW)[LT if kind != 'snow' else BS]
                elif kind != 'snow' and ((x * 7 + y * 3) % 11 == 0 or ((x - 1) * 7 + y * 3) % 11 == 0):
                    c = PATH[LT]
                elif kind != 'snow' and ((x * 5 + y * 7) % 13 == 0 or ((x - 1) * 5 + y * 7) % 13 == 0):
                    c = PATH[DK]
                lay[(x, y)] = c
    for (x, y) in face:
        j = y - yf
        c = Rf[BS]
        if j == depth - 1:
            c = Rf[SH]
        elif ((x // 2) * 7 + j * 5) % 9 == 0 and 0 < j < depth - 1:
            c = Rf[DK]                                     # pebbles and roots: 2 px clusters
        elif k == 2 and ((x // 2) * 3 + j * 11) % 17 == 0 and 0 < j < depth - 2:
            c = Rf[LT]
        if x == x0:
            c = Rf[LT] if j < depth - 1 else c
        elif x == x1:
            c = Rf[SH]
        lay[(x, y)] = c
    for x in range(x0, x1 + 1):                          # surface hanging over the front face, in 2 px runs
        n = 1 + (_crc(x0, x // 2) % (S.kv(2, 4)) if kind != 'stone' else 0)
        for j in range(n):
            if (x, yf + j) in face:
                lay[(x, yf + j)] = Rs[DK] if j else Rs[BS]
    outline(lay, top | face, Rf, lit=Rs[SH])
    return lay


# ------------------------------------------------------------------ snow pass
def snow_pass(S, group):
    """Snow on one building: caps on every top surface (above and into it, following slopes), roof planes
    mostly covered with a wavy lower edge and a shadow under it, snow on sills and boxes, icicles under the
    eaves. Tones: lit / flat tops highlight, slopes turned away a tone darker, a blue lip at the bottom."""
    k = S.k
    parts = [p for p in S.parts if p['group'] == group]
    comp = {}
    for p in sorted(parts, key=lambda p: (p['z'], p['n'])):
        comp.update(p['lay'])
    mask, roofs = set(), set()
    for p in parts:
        if p['snow']:
            mask |= set(p['lay'])
        if p['roof']:
            roofs |= set(p['lay'])
    lay = Layer()
    rnd = S.rnd('snow')
    cap, dep = S.kv(1, 2), S.kv(1, 2)
    tops = {}
    for (x, y) in mask:
        if (x, y - 1) not in mask:
            tops.setdefault(x, []).append(y)
    for x, ys in tops.items():
        for y in ys:
            nb = [yy for xx in (x - 1, x + 1) for yy in tops.get(xx, []) if abs(yy - y) <= 2]
            if not nb:
                continue                                   # a 1 px spike (post top, finial): no cap
            faces = 1 if min(tops.get(x + 1, [y]), key=lambda v: abs(v - y)) > y else \
                -1 if min(tops.get(x - 1, [y]), key=lambda v: abs(v - y)) > y else 0
            stp = max([abs(yy - y) for xx in (x - 1, x + 1) for yy in tops.get(xx, []) if abs(yy - y) <= 3] + [1])
            run = max(1, stp)                              # steep slope: runs as long as the step, no dots
            col = list(range(y - cap, y)) + [yy for yy in range(y, y + dep + (run - 1)) if (x, yy) in mask]
            for i, yy in enumerate(col):
                if i < run and (k == 2 or run > 1):
                    t = HI if faces <= 0 else LT
                elif i == 0:
                    t = HI if faces <= 0 else LT
                elif i >= len(col) - run and len(col) > run:
                    t = DK if k == 2 else BS
                else:
                    t = LT if faces <= 0 else BS
                lay[(x, yy)] = SNOW[t]
    for (x, y) in list(lay):                               # a shadow line under the snow, outside it only
        q = (x, y + 1)
        if q not in lay and q in mask and q in comp and lay[(x, y)] in SNOW:
            lay[q] = darker(comp[q], 1)
    for (g, fm) in S.fields:
        if g != group:
            continue
        cl = cols(fm)
        ph = rnd.random() * 6
        for x, (y0, y1) in cl.items():
            hgt = y1 - y0 + 1
            frac = 0.5 + 0.16 * math.sin(x * S.kv(0.55, 0.3) + ph) + 0.08 * math.sin(x * S.kv(1.3, 0.7) + 2 * ph)
            d = max(1, int(hgt * frac))
            for yy in range(y0, y0 + d):
                if (x, yy) in fm:
                    lay[(x, yy)] = SNOW[LT] if yy - y0 < d - 1 else SNOW[DK if k == 2 else BS]
            if k == 2 and (x, y0) in fm:
                lay[(x, y0)] = SNOW[HI]
            if (x, y0 + d) in fm and lay.get((x, y0 + d)) not in SNOW:
                lay[(x, y0 + d)] = darker(comp.get((x, y0 + d), SNOW[BS]), 1)
        for (x, y) in list(lay):                             # sparkle clusters on the cover
            if lay[(x, y)] == SNOW[LT] and (_crc(x, y, 'sp') % 23 == 0) and lay.get((x + 1, y)) == SNOW[LT]:
                lay[(x, y)] = lay[(x + 1, y)] = SNOW[HI]
    for (g, x0, x1, y) in S.ledges:
        if g != group:
            continue
        for x in range(x0, x1 + 1):
            lay[(x, y - 1)] = SNOW[HI if x < (x0 + x1) // 2 else LT]
            if k == 2 and x0 < x < x1:
                lay[(x, y - 2)] = SNOW[LT if x < (x0 + x1) // 2 else BS]
    if roofs:                                              # icicles from the lowest roof row
        ymax = {}
        for (x, y) in roofs:
            if (x, y + 1) not in roofs:
                ymax.setdefault(x, []).append(y)
        last = -99
        lowest = max(y for (_, y) in roofs)
        for x in sorted(ymax):
            for y in ymax[x]:
                if y < lowest - S.kv(1, 2) or x - last < S.kv(2, 3):
                    continue
                if _crc(S.seed, group, x) % 5 < 2:
                    continue
                last = x
                L = S.kv(1, 2) + _crc(group, x) % S.kv(2, 4)
                for j in range(1, L + 1):
                    lay[(x, y + j)] = ICE[HI if j == 1 else LT if j < L else BS]
                    if k == 2 and j < L // 2 + 1:
                        lay[(x + 1, y + j)] = ICE[BS]
    out = {p for p in lay if p not in mask}
    for (x, y) in edge_ring(out):
        if (x, y) not in mask and (x, y) not in lay:
            is_lit = (x, y + 1) in out or (x + 1, y) in out
            lay[(x, y)] = SNOW[DK] if is_lit and not ((x, y - 1) in out) else SNOW[SH]
    lay.ol = {SNOW[DK], SNOW[SH]}
    S.add('snow', lay, z=50, snow=False)


# ------------------------------------------------------------------ building helpers
def _sz(S, s, m, l):
    return {'s': s, 'm': m, 'l': l}[S.size]


def foundation(S, x0, x1, y0, y1, R=COBBLE, kind='stones', name='foundation', z=1, proud=1):
    """A plinth under the walls, `proud` px wider each side: stones / ashlar, a lit top ledge."""
    lay = S.lay(name, z)
    m = rect(x0 - proud, y0, x1 + proud, y1)
    if kind == 'stones':
        stones(S, lay, m, R, seed=x0)
    else:
        ashlar(S, lay, m, R, y0=y0, x0=x0, bw=S.kv(6, 10), bh=S.kv(3, 5), seed=x0)
    for x in range(x0 - proud, x1 + proud + 1):
        lay[(x, y0)] = R[HI] if (S.k == 2 and x < x0 + 2) else R[LT]
    outline(lay, m, R)
    S.ledge(x0 - proud, x0 - 1, y0)
    S.ledge(x1 + 1, x1 + proud, y0)
    return m


def beam_h(S, x0, x1, y, R=OAK_LOG, name='beams', ends=True, E=LOG_END):
    """A horizontal log beam (lit top row, base, dark bottom) with sawn ends showing at both sides."""
    lay = S.lay(name, 2, cast=(S.u(1), S.u(1), 1))
    bh = S.kv(2, 4)
    prof = (LT, DK) if S.k == 1 else (LT, BS, BS, DK)
    m = rect(x0, y, x1, y + bh - 1)
    for (x, yy) in m:
        lay[(x, yy)] = R[prof[yy - y]]
    if S.k == 2:
        rnd = S.rnd('beam', x0, y)
        for x in range(x0 + 2, x1 - 3):
            if rnd.random() < 0.08:
                for i in range(rnd.randint(2, 5)):
                    if x + i < x1 - 2:
                        lay[(x + i, y + 1 + (i // 3) % 2)] = R[DK]
    if ends:
        for ex in (x0, x1 - (S.kv(1, 5) if S.k == 2 else 1)):
            if S.k == 1:
                lay[(ex, y)] = E[LT]
                lay[(ex, y + 1)] = E[DK]
            else:
                m |= log_end(S, lay, ex + 2.5, y + 2, R, E)
    outline(lay, m, R)
    return m


def step(S, x0, x1, y0, y1, R=STONE, name='step'):
    """A stone step / threshold slab: lit top, darker front, outline."""
    lay = S.lay(name, 2)
    m = rect(x0, y0, x1, y1)
    for (x, y) in m:
        lay[(x, y)] = R[LT] if y == y0 else R[DK] if y == y1 else R[BS]
    if S.k == 2:
        lay[(x0, y0)] = R[HI]
    outline(lay, m, R)
    return m


def fits(a, b, w, gap, most=3):
    """How many openings of width w (with at least `gap` between them and the ends) fit in a..b."""
    n = max(1, (b - a + 1 - gap) // (w + gap))
    return min(most, n)


def spread(a, b, n, w):
    """n openings of width w spread evenly over columns a..b: their left x."""
    if n <= 0:
        return []
    gap = (b - a + 1 - n * w) / (n + 1)
    return [int(round(a + gap + i * (w + gap))) for i in range(n)]


# ------------------------------------------------------------------ the buildings
def cottage(S, cx, gy):
    """Oak cottage: cobblestone plinth, oak plank walls between oak log corner posts, a log beam with sawn
    ends, a front gable of vertical boards with a round attic window, a steep wooden-shingle roof with a
    dark barge board, a brick chimney with smoke, windows with green shutters and flower boxes, an oak door
    with panes, a wall lantern and a path to the door."""
    k, u = S.k, S.u
    hw = _sz(S, 12, 16, 20)
    x0, x1 = cx - u(hw), cx + u(hw) - 1
    fh = S.kv(3, 6)
    yf = gy - fh
    yw = yf - u(13)
    foundation(S, x0, x1, yf, gy - 1, COBBLE, proud=S.kv(1, 2))
    lay = S.lay('walls', 0)
    m = rect(x0, yw, x1, yf - 1)
    planks(S, lay, m, OAK, y0=yf, seed=2)
    pw = S.kv(2, 4)
    log_v(S, lay, x0, x0 + pw - 1, yw, yf - 1, OAK_LOG)
    log_v(S, lay, x1 - pw + 1, x1, yw, yf - 1, OAK_LOG)
    outline(lay, m, OAK)
    bh = S.kv(2, 4)
    beam_h(S, x0 - S.kv(1, 2), x1 + S.kv(1, 2), yw - bh, OAK_LOG)
    half = u(hw) + u(3)
    thick = S.kv(4, 8)
    roof, inner, top = gable_roof(S, cx, yw - bh + S.kv(0, 1), half, thick, SHINGLE, trim=DARK_OAK, seed=3)
    gl = S.lay('gable', 1)
    gm = {(x, y) for x in range(x0, x1 + 1) for y in range(inner(x) - 1, yw - bh)}
    planks(S, gl, gm, OAK, vertical=True, x0=x0, seed=4, board=S.kv(3, 5))
    for x in range(x0, x1 + 1):                            # the roof's shadow on the gable boards
        y = inner(x) - 1
        if (x, y) in gm:
            gl[(x, y)] = OAK[SH]
    outline(gl, gm, OAK)
    aw = S.kv(5, 9)
    window(S, cx - aw // 2 - (0 if k == 1 else 0), yw - bh - S.kv(7, 13), aw, aw,
           frame=DARK_OAK, style='round' if k == 2 else 'cross', sill=None)
    dw, dh = S.kv(6, 11), S.kv(10, 19)
    dx = cx - dw // 2
    door(S, dx, yf - dh, dw, dh, OAK, DARK_OAK)
    step(S, dx - 1, dx + dw, yf, yf + S.kv(1, 2) - 1, STONE)
    ww, wh = S.kv(6, 9), S.kv(6, 10)
    shut = GREEN_PAINT if k == 2 else None                 # shutters: an HD detail (no room at k=1)
    sw = max(S.kv(2, 3), ww // 3) if shut else 0
    lx = dx - S.kv(1, 2)
    for side in (-1, 1):
        a, b = (x0 + pw + 1, dx - S.kv(5, 2)) if side < 0 else (dx + dw + 1, x1 - pw - 1)
        n = fits(a + sw, b - sw, ww + 2 * sw, S.u(3), most=2)
        for i, wx in enumerate(spread(a + sw, b - sw, n, ww)):
            if S.size == 's' and side > 0:
                continue
            window(S, wx, yw + S.kv(3, 5), ww, wh, frame=DARK_OAK, shutters=shut, box=True, seed=i + side * 3)
    lantern(S, lx, yf - dh + S.kv(2, 3), side=-1, arm=S.kv(2, 4))
    if S.night:
        S.light(cx, gy + S.u(1.5), S.u(6))
    cxw = cx + u(hw * 0.5)
    chimney(S, cxw, S.kv(4, 7), top(cxw + S.kv(3, 6)) - S.kv(5, 9), top(cxw) + thick - 2, BRICK, seed=5)
    ground(S, x0 - u(5), x1 + u(9), gy, foot=(x0 - 2, x1 + 2), paths=[(dx, dx + dw - 1)])


def quoins(S, lay, x0, x1, y0, y1, R=STONE):
    """Corner stones up both wall edges: blocks alternating long / short, a tone lighter than the wall,
    lit top and left, dark joint under each block."""
    qh = S.kv(3, 5)
    for i, y in enumerate(range(y1, y0 - 1, -qh)):
        w = S.kv(3, 5) if i % 2 == 0 else S.kv(2, 3)
        for side in (0, 1):
            xa = x0 if side == 0 else x1 - w + 1
            for yy in range(max(y0, y - qh + 1), y + 1):
                for x in range(xa, xa + w):
                    c = R[LT]
                    if yy == y:
                        c = R[SH]
                    elif yy == y - qh + 1:
                        c = R[HI] if S.k == 2 else R[LT]
                    elif (side == 0 and x == xa + w - 1) or (side == 1 and x == xa):
                        c = R[DK]
                    lay[(x, yy)] = c


def lintel(S, x0, x1, y, R=STONE, keystone=True, name='lintels'):
    """A stone lintel over an opening: lit top row, dark bottom; a raised keystone in the middle (HD)."""
    lay = S.lay(name, 4, cast=(S.u(1), S.u(1), 1))
    lh = S.kv(1, 2)
    m = rect(x0, y - lh, x1, y - 1)
    for (x, yy) in m:
        lay[(x, yy)] = R[LT] if yy == y - lh else R[DK]
    if keystone and S.k == 2:
        mx = (x0 + x1) // 2
        for (x, yy) in rect(mx - 1, y - lh - 1, mx + 1, y - 1):
            lay[(x, yy)] = R[HI] if yy == y - lh - 1 else R[LT] if x < mx + 1 else R[BS]
            m.add((x, yy))
    outline(lay, m, R)
    return m


def stone_house(S, cx, gy):
    """Two-storey stone house: cobble plinth, stone-brick walls with light quoins up the corners, a string
    course between the floors, tall windows under stone lintels with keystones, an arched oak door under a
    voussoir arch, lanterns either side, a hipped slate roof with ridge tiles, two stone chimneys."""
    k, u = S.k, S.u
    hw = _sz(S, 13, 18, 23)
    floors = _sz(S, 1, 2, 2)
    bays = _sz(S, 3, 3, 5)
    x0, x1 = cx - u(hw), cx + u(hw) - 1
    fh = S.kv(2, 4)
    yf = gy - fh
    fl = u(12)
    yw = yf - fl * floors
    foundation(S, x0, x1, yf, gy - 1, COBBLE, proud=1)
    lay = S.lay('walls', 0)
    m = rect(x0, yw, x1, yf - 1)
    ashlar(S, lay, m, STONE, y0=yf, x0=x0, seed=7, moss=0.04 if k == 2 else 0)
    quoins(S, lay, x0, x1, yw, yf - 1, STONE)
    outline(lay, m, STONE)
    if floors > 1:
        sc = S.lay('string_course', 2, cast=(S.u(1), S.u(1), 1))
        ys = yf - fl
        sm = rect(x0 - 1, ys - S.kv(1, 2), x1 + 1, ys - 1)
        for (x, y) in sm:
            sc[(x, y)] = STONE[LT] if y == ys - S.kv(1, 2) else STONE[DK]
        outline(sc, sm, STONE)
        S.ledge(x0 - 1, x1 + 1, ys - S.kv(1, 2))
    ww = S.kv(5, 9)
    xs = spread(x0 + S.kv(3, 5), x1 - S.kv(3, 5), bays, ww)
    mid = bays // 2
    dw, dh = S.kv(7, 13), S.kv(10, 19)
    for f in range(floors):
        ybot = yf - f * fl
        for i, wx in enumerate(xs):
            if f == 0 and i == mid:
                continue
            wh = S.kv(7, 12) if f == 0 else S.kv(6, 11)
            wy = ybot - S.kv(3, 5) - wh
            window(S, wx, wy, ww, wh, frame=DARK_OAK, style='tall' if k == 1 else 'grid', sill=STONE, seed=i + f)
            lintel(S, wx - 1, wx + ww, wy)
    dx = xs[mid] + ww // 2 - dw // 2
    door(S, dx, yf - dh, dw, dh, OAK, STONE, style='arch')
    arch = S.lay('arch', 3)
    am = {p for p in edge_ring(_shape('arch', dx, yf - dh, dw, dh)) if p[1] < yf - dh + dw // 2 + 1}
    am |= {p for p in edge_ring(am | _shape('arch', dx, yf - dh, dw, dh)) if p[1] < yf - dh + dw // 2 - S.kv(1, 0)} \
        if k == 2 else set()
    for (x, y) in am:
        arch[(x, y)] = STONE[HI] if (x - dx) % S.kv(2, 3) == 0 else STONE[LT]
    outline(arch, am, STONE)
    step(S, dx - 1, dx + dw, yf, yf + S.kv(1, 2) - 1, STONE)
    for side in (-1, 1):                                  # lanterns hang off the corner quoins
        lantern(S, x0 - 1 if side < 0 else x1 + 1, yf - dh + S.kv(2, 4), side=side, arm=S.kv(2, 3))
    oh = u(3)
    rh = u(_sz(S, 9, 11, 12))
    roof, tops = hip_roof(S, x0 - oh, x1 + oh, yw + S.kv(1, 2), rh, SLATE, style='slate', seed=8)
    ytop = min(tops.values())
    for xc in (x0 + u(5), x1 - u(5) - S.kv(4, 6) + 1):
        chimney(S, xc, S.kv(4, 6), ytop - u(5), ytop + u(3), STONE, kind='stone', z=4, seed=xc)
    if S.night:
        S.light(cx, gy + S.u(1.5), S.u(6))
    ground(S, x0 - u(5), x1 + u(8), gy, foot=(x0 - 1, x1 + 1), paths=[(dx, dx + dw - 1)])


def log_cabin(S, cx, gy):
    """Log cabin: stacked horizontal logs with round sawn ends stacked at both corners, a log gable, a moss-
    green shingle roof with a dark trim, a tall cobblestone chimney built against the right wall (wide
    firebox, narrow stack), a spruce door, cross windows, a lantern and a firewood pile."""
    k, u = S.k, S.u
    hw = _sz(S, 10, 13, 17)
    x0, x1 = cx - u(hw), cx + u(hw) - 1
    fh = S.kv(2, 3)
    yf = gy - fh
    lh = S.kv(3, 6)
    nlogs = _sz(S, 4, 4, 5)
    yw = yf - lh * nlogs - S.kv(0, 0)
    foundation(S, x0, x1, yf, gy - 1, COBBLE, proud=0)
    lay = S.lay('walls', 0)
    m = rect(x0, yw, x1, yf - 1)
    logs_h(S, lay, m, OAK_LOG, y0=yf)
    outline(lay, m, OAK_LOG)
    half = u(hw) + u(3)
    thick = S.kv(4, 8)
    roof, inner, top = gable_roof(S, cx, yw + S.kv(0, 1), half, thick, MOSSROOF, trim=SPRUCE_LOG, seed=9)
    gl = S.lay('gable', 1)
    gm = {(x, y) for x in range(x0, x1 + 1) for y in range(inner(x) - 1, yw)}
    logs_h(S, gl, gm, OAK_LOG, y0=yf)
    outline(gl, gm, OAK_LOG)
    ends = S.lay('log_ends', 2)
    em = set()
    out = S.kv(2, 3)
    for j in range(nlogs + 3):
        yc = yf - lh * j - lh / 2 - (0.5 if k == 1 else 0)
        for xc in (x0 - out + (0 if k == 1 else 2.5), x1 + out - (1 if k == 1 else 2.5)):
            if yc - lh / 2 < inner(int(xc)) - 1 and j >= nlogs:
                continue
            if k == 1:
                em |= log_end(S, ends, int(xc), int(yc - 0.5))
            else:
                em |= log_end(S, ends, xc, yc + 0.5)
    outline(ends, em, OAK_LOG)
    dw, dh = S.kv(6, 10), S.kv(9, 17)
    dx = cx - dw // 2 - u(_sz(S, 0, 3, 4))
    door(S, dx, yf - dh, dw, dh, SPRUCE, SPRUCE_LOG)
    step(S, dx - 1, dx + dw, yf, yf + S.kv(0, 1), OAK)
    ww, wh = S.kv(5, 9), S.kv(5, 9)
    for wx in ([x0 + u(3)] if S.size == 's' else [x0 + u(3), dx + dw + u(3)]):
        window(S, wx, yw + S.kv(3, 6), ww, wh, frame=SPRUCE_LOG, sill=OAK)
    lantern(S, dx + dw + S.kv(0, 1), yf - dh + S.kv(2, 3), side=1, arm=S.kv(2, 3))
    # stone chimney against the right wall: wide firebox, a shoulder, a narrow stack past the roof
    ch = S.lay('chimney', 4, cast=(S.u(1), S.u(1), 1))
    cw1, cw2 = S.kv(7, 13), S.kv(4, 7)
    cxa = x1 + out - S.kv(1, 2)                            # against the wall, over the log ends
    sx0 = cxa + cw1 - cw2 - S.kv(1, 2)                     # the stack stands on the outer half
    ytop_c = top(x1) - u(5)
    shoulder = yw + u(3)
    cm = rect(cxa, shoulder, cxa + cw1 - 1, gy - 1) | rect(sx0, ytop_c, sx0 + cw2 - 1, shoulder - 1)
    st = S.kv(1, 2)                                        # the stepped shoulder
    for i in range(1, (sx0 - cxa) // st + 1):
        cm |= rect(cxa + i * st, shoulder - i * st, sx0 - 1, shoulder - (i - 1) * st - 1)
    stones(S, ch, cm, COBBLE, cell=S.kv((4, 3), (6, 4)), seed=11)
    for (x, y) in cm:
        if (x - 1, y) not in cm:
            ch[(x, y)] = COBBLE[LT]
        elif (x + 1, y) not in cm:
            ch[(x, y)] = COBBLE[DK]
        elif (x, y - 1) not in cm:
            ch[(x, y)] = COBBLE[LT]
    capm = rect(sx0 - 1, ytop_c - S.kv(1, 2), sx0 + cw2, ytop_c - 1)
    for (x, y) in capm:
        ch[(x, y)] = COBBLE[LT] if y == ytop_c - S.kv(1, 2) else COBBLE[DK]
    outline(ch, cm | capm, COBBLE)
    puff(S, sx0 + cw2 // 2, ytop_c - S.kv(2, 3), seed=4)
    # firewood pile on the left
    wp = S.lay('woodpile', 5, cast=(S.u(1), 0, 1))
    wm = set()
    r = S.kv(1, 3)
    px0 = x0 - out - S.kv(9, 16)
    for row, n in enumerate(_sz(S, (3, 2), (3, 2, 1), (4, 3, 2))):
        for i in range(n):
            xc = px0 + i * (2 * r if k == 2 else 2) + row * (r if k == 2 else 1)
            yc = gy - 1 - row * (2 * r if k == 2 else 2)
            if k == 1:
                wm |= log_end(S, wp, xc, yc - 1)
            else:
                wm |= log_end(S, wp, xc + r, yc - r + 0.5)
    outline(wp, wm, OAK_LOG)
    if S.night:
        S.light(dx + dw / 2, gy + S.u(1.5), S.u(6))
    ground(S, px0 - u(3), cxa + cw1 + u(5), gy, foot=(x0 - out, cxa + cw1), paths=[(dx, dx + dw - 1)])


def birch_log_v(S, lay, x0, x1, y0, y1, seed=0):
    """A birch post: white bark (lit left, grey right) with short black marks."""
    log_v(S, lay, x0, x1, y0, y1, BIRCH_BARK, seed=seed)
    rnd = S.rnd('birch', x0, seed)
    y = y0 + rnd.randint(1, 3)
    while y < y1:
        w = rnd.randint(1, x1 - x0 + 1)
        xa = x0 + rnd.randint(0, x1 - x0 + 1 - w)
        for x in range(xa, xa + w):
            lay[(x, y)] = BARK_MARK[BS if x > x0 else DK]
        y += rnd.randint(S.kv(3, 4), S.kv(5, 8))


def birch_house(S, cx, gy):
    """Birch house: pale birch-plank walls between white birch posts, a hipped red clay-tile roof, windows
    with blue shutters (HD) and flower boxes, a little porch roof over the door on birch posts, a brick
    chimney on the roof plane."""
    k, u = S.k, S.u
    hw = _sz(S, 13, 17, 21)
    x0, x1 = cx - u(hw), cx + u(hw) - 1
    fh = S.kv(2, 4)
    yf = gy - fh
    yw = yf - u(15)
    foundation(S, x0, x1, yf, gy - 1, STONE, kind='ashlar', proud=1)
    lay = S.lay('walls', 0)
    m = rect(x0, yw, x1, yf - 1)
    planks(S, lay, m, BIRCH, y0=yf, seed=12)
    pw = S.kv(2, 4)
    birch_log_v(S, lay, x0, x0 + pw - 1, yw, yf - 1, 1)
    birch_log_v(S, lay, x1 - pw + 1, x1, yw, yf - 1, 2)
    outline(lay, m, BIRCH)
    dw, dh = S.kv(6, 10), S.kv(9, 16)
    dx = cx - dw // 2
    door(S, dx, yf - dh, dw, dh, BIRCH, OAK)
    step(S, dx - 1, dx + dw, yf, yf + S.kv(1, 2) - 1, STONE)
    ww, wh = S.kv(6, 9), S.kv(6, 10)
    shut = BLUE_PAINT if k == 2 else None
    sw = max(S.kv(2, 3), ww // 3) if shut else 0
    for side in (-1, 1):
        a, b = (x0 + pw + 1, dx - u(3)) if side < 0 else (dx + dw + u(3), x1 - pw - 1)
        n = fits(a + sw, b - sw, ww + 2 * sw + S.kv(0, 2), S.u(3), most=2)
        for i, wx in enumerate(spread(a + sw, b - sw, n, ww)):
            window(S, wx, yw + S.kv(5, 8), ww, wh, frame=OAK, shutters=shut, box=True, seed=i + 5 * side)
    oh = u(3)
    roof, tops = hip_roof(S, x0 - oh, x1 + oh, yw + S.kv(1, 2), u(_sz(S, 9, 10, 11)), CLAY, style='clay', seed=13)
    ytop = min(tops.values())
    xc = x0 + u(6)
    chimney(S, xc, S.kv(4, 6), ytop - u(4), ytop + u(4), BRICK, z=4, seed=6)
    # porch: a small gable roof over the door on two birch posts
    py = yf - dh - S.kv(1, 2)
    phalf = dw // 2 + S.kv(3, 4)
    _, pin, ptop = gable_roof(S, dx + dw // 2, py, phalf, S.kv(2, 3), CLAY, style='clay', name='porch_roof', z=6,
                              trim=OAK, slope=(2, 1))
    posts = S.lay('porch_posts', 5, cast=(S.u(1), 0, 1))
    pwid = S.kv(1, 2)
    for xa in (dx + dw // 2 - phalf + S.kv(1, 2), dx + dw // 2 + phalf - S.kv(1, 2) - pwid):
        birch_log_v(S, posts, xa, xa + pwid - 1, py + 1, yf + S.kv(0, 1), xa)
        outline(posts, rect(xa, py + 1, xa + pwid - 1, yf + S.kv(0, 1)), BIRCH_BARK)
    lantern(S, dx + dw // 2, py + S.kv(1, 2), post=True) if k == 2 else None
    if S.night:
        S.light(cx, gy + S.u(1.5), S.u(6))
    ground(S, x0 - u(5), x1 + u(8), gy, foot=(x0 - 1, x1 + 1), paths=[(dx, dx + dw - 1)])


def spruce_aframe(S, cx, gy):
    """Spruce A-frame: a steep shingle roof reaching the ground with a dark log trim, a front of vertical
    spruce boards, a big gable window with mullions (warm at night), a small balcony rail under it, a door
    between two lanterns, a stone footing and an iron stove pipe with smoke."""
    k, u = S.k, S.u
    half = u(_sz(S, 13, 16, 20))
    thick = S.kv(5, 9)
    eave = gy - 1
    roof, inner, top = gable_roof(S, cx, eave, half, thick, SHINGLE, slope=(1, 2), trim=SPRUCE_LOG, seed=14)
    fh = S.kv(2, 3)
    yf = gy - fh
    fl = S.lay('foundation', 1)
    fm = {(x, y) for x in range(cx - half, cx + half) for y in range(yf, gy) if y >= inner(x)}
    stones(S, fl, fm, COBBLE, seed=3)
    for (x, y) in fm:
        if y == yf:
            fl[(x, y)] = COBBLE[LT]
    outline(fl, fm, COBBLE)
    gl = S.lay('walls', 0)
    gm = {(x, y) for x in range(cx - half, cx + half) for y in range(inner(x) - 1, yf)}
    planks(S, gl, gm, SPRUCE, vertical=True, x0=cx, seed=15, board=S.kv(3, 5))
    for x in range(cx - half, cx + half):
        if (x, inner(x) - 1) in gm:
            gl[(x, inner(x) - 1)] = SPRUCE[SH]
    outline(gl, gm, SPRUCE)
    # the big gable window: a triangle under the apex, mullions, a transom
    wl = S.lay('windows', 4, cast=(S.u(1), S.u(1), 1))
    ya = min(inner(x) for x in range(cx - half, cx + half)) + S.kv(2, 4)
    yb = yf - S.kv(13, 24)
    G = GLOW if S.night else GLASS
    tri = {(x, y) for x in range(cx - half, cx + half) for y in range(ya, yb + 1)
           if y >= inner(x) + S.kv(2, 4) and abs(x + 0.5 - cx) <= u(7)}
    glass = _erode(tri, S.kv(1, 2))
    fr = tri - glass
    gx0, gy0, gx1, gy1 = bbox(glass)
    bars = {(x, y) for (x, y) in glass if (x - cx) % S.kv(4, 6) == 0 or y == gy1 - S.kv(3, 6)}
    for (x, y) in fr:
        wl[(x, y)] = SPRUCE_LOG[LT] if x < cx else SPRUCE_LOG[DK]
    for (x, y) in glass - bars:
        up = (x, y - 1) not in glass or (x, y - 1) in bars
        if S.night:
            wl[(x, y)] = G[BS] if up else G[HI] if abs(x + 0.5 - cx) < u(3) and y > gy0 + u(3) else G[LT]
        else:
            s = (x - gx0) + (gy1 - y)
            wl[(x, y)] = G[SH] if up else G[LT] if s % S.kv(9, 13) in S.kv((4,), (5, 6)) else G[BS]
    for p in bars:
        wl[p] = SPRUCE_LOG[SH if S.night else BS]
    outline(wl, tri, SPRUCE_LOG)
    if S.night:
        S.light(cx, (gy0 + gy1) / 2, u(10))
    # balcony rail under the window
    bl = S.lay('balcony', 5, cast=(S.u(1), S.u(1), 1))
    by = yb + S.kv(2, 3)
    bm = set()
    bx0, bx1 = cx - u(8), cx + u(8) - 1
    for x in range(bx0, bx1 + 1):
        bl[(x, by)] = SPRUCE[LT]
        bm.add((x, by))
        if k == 2:
            bl[(x, by + 1)] = SPRUCE[DK]
            bm.add((x, by + 1))
        if (x - bx0) % S.kv(3, 4) == 0:
            for j in range(1, S.kv(4, 7)):
                bl[(x, by + j + (1 if k == 2 else 0))] = SPRUCE[BS]
                bm.add((x, by + j + (1 if k == 2 else 0)))
    floor_y = by + S.kv(4, 8)
    for x in range(bx0 - 1, bx1 + 2):
        for j in range(S.kv(1, 2)):
            bl[(x, floor_y + j)] = SPRUCE[LT if j == 0 else DK]
            bm.add((x, floor_y + j))
    outline(bl, bm, SPRUCE)
    S.ledge(bx0, bx1, by)
    dw, dh = S.kv(6, 10), S.kv(9, 17)
    dx = cx - dw // 2
    door(S, dx, yf - dh, dw, dh, SPRUCE, SPRUCE_LOG)
    for side in (-1, 1):
        lantern(S, dx - S.kv(1, 2) if side < 0 else dx + dw + S.kv(0, 1), yf - dh + S.kv(2, 4), side=side,
                arm=S.kv(2, 3))
    # stove pipe on the right slope
    pl = S.lay('chimney', -1, cast=(S.u(1), S.u(1), 1))
    px = cx + u(6)
    pw = S.kv(2, 3)
    pt = top(px) - u(6)
    pm = rect(px, pt, px + pw - 1, top(px) + thick)
    for (x, y) in pm:
        pl[(x, y)] = DARK_IRON[LT] if x == px else DARK_IRON[DK] if x == px + pw - 1 else DARK_IRON[BS]
    capm = rect(px - 1, pt - S.kv(1, 2), px + pw, pt - 1)
    for (x, y) in capm:
        pl[(x, y)] = DARK_IRON[LT] if y == pt - S.kv(1, 2) else DARK_IRON[DK]
    for y in (pt + u(3), pt + u(5)):
        for x in range(px, px + pw):
            pl[(x, y)] = IRON[LT] if x == px else IRON[BS]
    outline(pl, pm | capm, DARK_IRON)
    puff(S, px + pw // 2, pt - S.kv(2, 3), seed=7)
    if S.night:
        S.light(cx, gy + S.u(1.5), S.u(6))
    ground(S, cx - half - u(4), cx + half + u(6), gy, foot=(cx - half, cx + half - 1), paths=[(dx, dx + dw - 1)])


def awning(S, x0, x1, y, depth=None, R1=CLOTH, R2=CANVAS, name='awning', z=6, stripe=None):
    """A striped cloth awning seen from the front: lit top rows, stripes, a darker underside band, a
    scalloped edge."""
    k = S.k
    lay = S.lay(name, z, cast=(S.u(1), S.u(2), 1))
    d = depth or S.kv(3, 6)
    sw = stripe or S.kv(2, 4)
    m = set()
    for j in range(d):
        for x in range(x0 - (j * 1 if k == 2 else j // 2), x1 + 1 + (j * 1 if k == 2 else j // 2)):
            r = R1 if ((x - x0) // sw) % 2 == 0 else R2
            t = HI if j == 0 else LT if j < d // 2 else BS
            if j == d - 1:
                t = DK
            lay[(x, y + j)] = r[t]
            m.add((x, y + j))
    xa, xb = x0 - ((d - 1) if k == 2 else (d - 1) // 2), x1 + ((d - 1) if k == 2 else (d - 1) // 2)
    for x in range(xa, xb + 1):
        r = R1 if ((x - x0) // sw) % 2 == 0 else R2
        j = (x - xa) % sw
        if j not in (0,) or k == 1:
            lay[(x, y + d)] = r[DK]
            m.add((x, y + d))
            if k == 2 and 0 < j < sw - 1:
                lay[(x, y + d + 1)] = r[SH]
                m.add((x, y + d + 1))
    outline(lay, m, R1)
    S.ledge(xa, xb, y)
    return m


def pot(S, x, yb, R=TERRACOTTA, plant=None, name='pots'):
    """A clay pot (round belly, a rim, lit left / dark right), optionally with a cactus or a shrub."""
    k = S.k
    lay = S.lay(name, 5, cast=(S.u(1), 0, 1))
    w, h = S.kv(4, 7), S.kv(4, 7)
    m = set()
    for j in range(h):
        bul = 1 if (0 < j < h - 1 and k == 2) or (j in (1, 2) and k == 1) else 0
        for i in range(-bul, w + bul):
            t = (i + bul + 0.5) / (w + 2 * bul)
            tone = LT if t < 0.35 else BS if t < 0.7 else DK
            if j == 0:
                tone = HI if t < 0.5 else LT
            elif j == h - 1:
                tone = DK
            lay[(x + i, yb - h + 1 + j)] = R[tone]
            m.add((x + i, yb - h + 1 + j))
    if plant == 'cactus':
        cw, chh = S.kv(2, 3), S.kv(5, 9)
        cx0 = x + w // 2 - cw // 2
        for j in range(chh):
            for i in range(cw):
                lay[(cx0 + i, yb - h - j)] = LEAVES[LT if i == 0 else DK if i == cw - 1 else BS]
                m.add((cx0 + i, yb - h - j))
        ay = yb - h - chh // 2
        for (a, b) in ((-1, 0), (-2, 0), (-2, -1), (-2, -2)) if k == 2 else ((-1, 0), (-1, -1)):
            lay[(cx0 + a, ay + b)] = LEAVES[BS]
            m.add((cx0 + a, ay + b))
        if k == 2:
            for (a, b) in ((cw, -2), (cw + 1, -2), (cw + 1, -3), (cw + 1, -4)):
                lay[(cx0 + a, ay + b)] = LEAVES[DK]
                m.add((cx0 + a, ay + b))
            lay[(cx0 + 1, yb - h - chh)] = POPPY[LT]
        outline(lay, m, R)
        return m
    if plant:
        for (px, py) in disc(x + w / 2, yb - h - S.kv(1, 2), S.kv(2, 3.2), S.kv(1.5, 2.5)):
            if py < yb - h + 1:
                lay[(px, py)] = LEAVES[LT if px < x + w / 2 - 0.5 and py < yb - h - 1 else BS if px < x + w / 2 + 1
                                       else DK]
                m.add((px, py))
    outline(lay, m, R)
    return m


def desert_house(S, cx, gy):
    """Desert house: sandstone walls of layered blocks, a flat roof behind a cut-sandstone parapet with a
    painted terracotta band and stepped ends, a row of beam ends (vigas) under it, an arched doorway with a
    striped curtain, small unglazed windows under wooden lintels, a striped awning, clay pots with a
    cactus; sand ground."""
    k, u = S.k, S.u
    hw = _sz(S, 12, 16, 20)
    x0, x1 = cx - u(hw), cx + u(hw) - 1
    yf = gy - S.kv(1, 2)
    yw = yf - u(_sz(S, 12, 14, 14))
    lay = S.lay('walls', 0)
    m = rect(x0, yw, x1, yf - 1)
    sandstone(S, lay, m, SANDSTONE, y0=yf, x0=x0, seed=16)
    outline(lay, m, SANDSTONE)
    fl = S.lay('foundation', 1)
    fm = rect(x0 - 1, yf, x1 + 1, gy - 1)
    for (x, y) in fm:
        fl[(x, y)] = SANDSTONE[LT] if y == yf else SANDSTONE[DK]
    outline(fl, fm, SANDSTONE)
    # parapet with a painted band and stepped ends
    pl = S.lay('parapet', 2, cast=(S.u(1), S.u(1), 1))
    ph = S.kv(4, 8)
    yp = yw - ph
    pm = rect(x0 - 1, yp, x1 + 1, yw - 1)
    stepw = S.kv(5, 9)
    for xa in (x0 - 1, x1 + 2 - stepw, cx - stepw // 2):
        pm |= rect(xa, yp - S.kv(2, 3), xa + stepw - 1, yp - 1)
    for (x, y) in pm:
        c = SANDSTONE[BS]
        if (x, y - 1) not in pm:
            c = SANDSTONE[HI] if k == 2 and x < cx else SANDSTONE[LT]
        elif (x, y + 1) not in pm:
            c = SANDSTONE[DK]
        elif (x - 1, y) not in pm:
            c = SANDSTONE[LT]
        elif (x + 1, y) not in pm:
            c = SANDSTONE[DK]
        pl[(x, y)] = c
    by = yp + ph // 2 - (0 if k == 1 else 1)
    for x in range(x0, x1 + 1):                            # terracotta band, a zigzag at HD
        pl[(x, by)] = TERRACOTTA[BS]
        if k == 2:
            z = (x - x0) % 4
            pl[(x, by + 1)] = TERRACOTTA[DK]
            pl[(x, by - 1 + (z in (1, 2)) * 0)] = SANDSTONE[BS]
            if z == 0:
                pl[(x, by - 1)] = TERRACOTTA[LT]
            elif z == 2:
                pl[(x, by + 2)] = TERRACOTTA[DK]
    outline(pl, pm, SANDSTONE)
    S.ledge(x0 - 1, x1 + 1, yp)
    # vigas: beam ends poking out under the parapet
    vl = S.lay('beams', 3, cast=(S.u(1), S.u(1), 1))
    vm = set()
    for x in range(x0 + S.kv(2, 4), x1 - S.kv(2, 3), S.kv(5, 9)):
        if k == 1:
            vm |= log_end(S, vl, x, yw + 1, OAK_LOG, LOG_END)
        else:
            vm |= log_end(S, vl, x + 2, yw + 3, OAK_LOG, LOG_END, small=True)
    outline(vl, vm, OAK_LOG)
    # doorway: arched opening, striped curtain
    dw, dh = S.kv(7, 12), S.kv(10, 19)
    dx = cx - dw // 2 + u(_sz(S, 0, 4, 5))
    door(S, dx, yf - dh, dw, dh, OAK, SANDSTONE, style='open_arch')
    cl = S.lay('curtain', 5)
    cm = set()
    f = S.kv(1, 2)
    op = _erode(_shape('arch', dx, yf - dh, dw, dh), f)
    ox0, oy0, ox1, oy1 = bbox(op)
    clen = int((oy1 - oy0) * 0.55)
    for (x, y) in op:
        if y - oy0 <= clen - abs(x - (ox0 + ox1) / 2) * 0.3 * 0 - (1 if (x - ox0) % S.kv(2, 3) == 0 and y - oy0 == clen else 0):
            r = BLUE_CLOTH if ((x - ox0) // S.kv(2, 3)) % 2 == 0 else CANVAS
            t = LT if x < (ox0 + ox1) // 2 else BS
            if y - oy0 == clen:
                t = DK
            cl[(x, y)] = r[t]
            cm.add((x, y))
    S.remove('curtain') if not cm else None
    # windows: small unglazed openings with wooden lintels; one under an awning
    ww, wh = S.kv(4, 7), S.kv(4, 7)
    wxs = spread(x0 + S.kv(2, 4), dx - S.kv(3, 4), _sz(S, 1, 2, 2), ww)
    if S.size == 'l':
        wxs += [x1 - u(6) - ww]
    for i, wx in enumerate(wxs):
        wy = yw + S.kv(4, 7)
        window(S, wx, wy, ww, wh, style='dark', sill=None)
        ll = S.lay('lintels', 4, cast=(S.u(1), S.u(1), 1))
        lm = rect(wx - 1, wy - S.kv(1, 2), wx + ww, wy - 1)
        for (x, y) in lm:
            ll[(x, y)] = DARK_OAK[LT] if y == wy - S.kv(1, 2) else DARK_OAK[DK]
        outline(ll, lm, DARK_OAK)
        if i == 0:
            awning(S, wx - 1, wx + ww, wy - S.kv(3, 5), depth=S.kv(2, 4), R1=CLOTH, R2=CANVAS)
    pot(S, dx - S.kv(6, 10), yf + S.kv(1, 2), plant='cactus')
    pot(S, dx + dw + S.kv(1, 2), yf + S.kv(1, 2))
    if S.night:
        S.light(dx + dw / 2, gy + S.u(1.5), S.u(6))
    ground(S, x0 - u(5), x1 + u(8), gy, kind='sand', foot=(x0 - 1, x1 + 1), paths=[(dx + 1, dx + dw - 2)])


# ------------------------------------------------------------------ round forms
_L = (-0.55, -0.62, 0.56)
_LN = math.sqrt(sum(c * c for c in _L))


def dome_tone(nx, ny, cuts=(0.86, 0.6, 0.22, -0.08)):
    """Tone of a point on a ball / dome with normal (nx, ny, nz) lit from the top-left-front; compressed
    bands: narrow highlight and terminator, wide base and light."""
    nz = math.sqrt(max(0.0, 1 - nx * nx - ny * ny))
    lam = (_L[0] * nx + _L[1] * ny + _L[2] * nz) / _LN
    return HI if lam > cuts[0] else LT if lam > cuts[1] else BS if lam > cuts[2] else DK if lam > cuts[3] else SH


def cyl_tone(nx, cuts=(0.84, 0.55, 0.12, -0.2)):
    """Tone across a vertical cylinder (tower, stem, silo): nx -1 (left) .. 1 (right)."""
    nx = max(-1.0, min(1.0, nx))
    nz = math.sqrt(max(0.0, 1 - nx * nx))
    lam = (_L[0] * nx + 0.2 + _L[2] * nz) / _LN
    return HI if lam > cuts[0] else LT if lam > cuts[1] else BS if lam > cuts[2] else DK if lam > cuts[3] else SH


def foliage(S, lay, blobs, R=LEAVES, seed=0, outline_it=True):
    """A crown from overlapping blobs (cx, cy, rx, ry), back to front: each blob lit like a ball from the
    top-left, a darker contact line where a front blob overlaps the one behind (self-cast shadow), leaf
    clumps (2-3 px clusters, a tone lighter on the lit side, darker in the shade), outlined in the leaves'
    own dark tone."""
    k = S.k
    m = set()
    rnd = S.rnd('foliage', seed)
    for (cx, cy, rx, ry) in blobs:
        pts = disc(cx, cy, rx, ry)
        for (x, y) in pts:
            t = dome_tone((x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry)
            lay[(x, y)] = R[t]
        for (x, y) in edge_ring(pts):
            if (x, y) in m and (x > cx or y > cy) and (x, y) not in pts:
                lay[(x, y)] = R[SH]
        m |= pts
    for (x, y) in sorted(m):
        c = lay[(x, y)]
        if c in (R[SH], R[O]) or rnd.random() > S.kv(0.07, 0.06):
            continue
        t = R.index(c)
        t2 = min(HI, t + 1) if t >= LT else max(SH, t - 1) if t <= DK else (LT if rnd.random() < 0.5 else DK)
        for (a, b) in ((0, 0), (1, 0), (0, 1)) if k == 1 else ((0, 0), (1, 0), (0, 1), (1, 1), (2, 0))[:rnd.randint(3, 5)]:
            if (x + a, y + b) in m and lay[(x + a, y + b)] == c:
                lay[(x + a, y + b)] = R[t2]
    if outline_it:
        outline(lay, m, R)
    return m


def trunk(S, lay, x0, x1, y0, y1, R=OAK_LOG, roots=True, seed=0):
    """A tree trunk: a vertical log with a flared foot (roots spreading left and right)."""
    log_v(S, lay, x0, x1, y0, y1, R, seed=seed)
    m = rect(x0, y0, x1, y1)
    if roots:
        for i in range(1, S.kv(2, 4) + 1):
            for y in range(y1 - S.kv(2, 4) + i, y1 + 1):
                lay[(x0 - i, y)] = R[LT]
                lay[(x1 + i, y)] = R[DK]
                m |= {(x0 - i, y), (x1 + i, y)}
    return m


def tree(S, cx, gy, kind='oak', h=None, name='tree', z=0, seed=0):
    """A small tree for scenes: oak (round crown), birch (white trunk, lighter crown), spruce (stacked
    drooping tiers), with the ground contact on gy."""
    k, u = S.k, S.u
    lay = S.lay(name, z, cast=(u(2), 0, 1))
    rnd = S.rnd('tree', seed, cx)
    if kind == 'spruce':
        h = h or u(22)
        tw = S.kv(2, 3)
        tm = trunk(S, lay, cx - tw // 2, cx - tw // 2 + tw - 1, gy - u(5), gy - 1, SPRUCE_LOG, roots=False)
        outline(lay, tm, SPRUCE_LOG)
        L = Layer()
        m = set()
        tiers = 4
        for t in range(tiers):
            yb = gy - u(4) - t * (h - u(4)) // tiers
            half = u(9) - t * u(2)
            ht = (h - u(4)) // tiers + u(3)
            for j in range(ht):
                hw_ = int(half * (j + 1) / ht) + 1
                y = yb - ht + 1 + j
                for x in range(cx - hw_, cx + hw_):
                    rel = (x + 0.5 - cx) / max(1, hw_)
                    tt = LT if rel < -0.35 else BS if rel < 0.3 else DK
                    if j == ht - 1:
                        tt = DK if rel < 0.3 else SH          # the tier's drooping lower edge in shade
                    if j == 0 or (x == cx - hw_ and j % 2 == 0):
                        tt = min(HI, tt + 1)
                    L[(x, y)] = SPRUCE_NEEDLES[tt]
                    m.add((x, y))
        lay.update(L)
        outline(lay, m, SPRUCE_NEEDLES)
        return m | tm
    h = h or u(20)
    R = LEAVES if kind == 'oak' else BIRCH_LEAVES
    tw = S.kv(2, 4)
    if kind == 'birch':
        lay_ = lay
        birch_log_v(S, lay_, cx - tw // 2, cx - tw // 2 + tw - 1, gy - h // 2, gy - 1, seed)
        tm = rect(cx - tw // 2, gy - h // 2, cx - tw // 2 + tw - 1, gy - 1)
        outline(lay, tm, BIRCH_BARK)
    else:
        tm = trunk(S, lay, cx - tw // 2, cx - tw // 2 + tw - 1, gy - h // 2, gy - 1, OAK_LOG, seed=seed)
        outline(lay, tm, OAK_LOG)
    r = u(7) if kind == 'oak' else u(5.5)
    cy = gy - h + r
    blobs = [(cx - r * 0.55, cy + r * 0.35, r * 0.75, r * 0.65), (cx + r * 0.6, cy + r * 0.4, r * 0.7, r * 0.6),
             (cx, cy, r * 0.95, r * 0.8)]
    if kind == 'birch':
        blobs = [(cx - r * 0.3, cy + r * 0.5, r * 0.7, r * 0.7), (cx + r * 0.35, cy + r * 0.2, r * 0.7, r * 0.75),
                 (cx, cy - r * 0.3, r * 0.75, r * 0.7)]
    L = Layer()
    fm = foliage(S, L, blobs, R, seed=seed + cx)
    if kind == 'oak' and k == 2 and rnd.random() < 0.5:     # a few apples
        for _ in range(3):
            ax, ay = rnd.choice(sorted(fm))
            if L.get((ax, ay)) in (R[BS], R[DK]) and (ax + 1, ay + 1) in fm:
                L[(ax, ay)] = POPPY[LT]
                L[(ax + 1, ay)] = POPPY[BS]
                L[(ax, ay + 1)] = POPPY[BS]
                L[(ax + 1, ay + 1)] = POPPY[DK]
    lay.update(L)
    return fm | tm



def igloo(S, cx, gy):
    """Igloo: a dome of snow blocks (courses narrowing to the top, staggered joints a tone darker than the
    block they cut, the whole dome lit like a ball from the top-left), an entrance tunnel with a dark
    arched mouth (warm at night), a clear-ice window, a lantern on a post, packed-snow blocks; snow ground."""
    k, u = S.k, S.u
    R = u(_sz(S, 11, 14, 17))
    ry = int(R * 0.86)
    lay = S.lay('dome', 0, snow=False)
    dm = dome_mask(cx, gy, R, ry)
    ch = S.kv(3, 5)
    for (x, y) in dm:
        nx, ny = (x + 0.5 - cx) / R, (y + 0.5 - gy) / ry
        t = dome_tone(nx, ny, cuts=(0.9, 0.62, 0.3, 0.0))
        row = (gy - 1 - y) // ch
        r = (gy - 1 - y) % ch
        width = max(1, int(R * math.sqrt(max(0.05, 1 - ((gy - y) / ry) ** 2))))
        bw = max(S.kv(4, 6), int(width * 0.5))
        j = (x - cx + (row % 2) * bw // 2) % bw
        if r == ch - 1 or j == 0:                          # joints: two steps down, never lighter than DK
            t = DK if t >= LT else SH
        elif k == 2 and r == 0 and t >= LT:
            t = HI if t == HI or (j < bw // 2 and nx < 0) else t   # lit top lip of each block
        lay[(x, y)] = SNOW[t]
    outline(lay, dm, SNOW)
    # clear-ice window high on the left
    wx, wy = cx - u(6), gy - u(9)
    wl = S.lay('windows', 2)
    wm = rect(wx, wy, wx + S.kv(3, 6) - 1, wy + S.kv(3, 5) - 1)
    for (x, y) in wm:
        if S.night:
            wl[(x, y)] = GLOW[HI] if (x - wx + y - wy) < S.kv(2, 3) else GLOW[LT]
        else:
            wl[(x, y)] = ICE[HI] if (x - wx) + (y - wy) < S.kv(2, 3) else ICE[LT] if x - wx < S.kv(2, 3) else ICE[BS]
    outline(wl, wm, ICE)
    if S.night:
        S.light(wx + S.kv(1.5, 3), wy + S.kv(1.5, 2.5), u(6))
    # entrance tunnel
    tl = S.lay('tunnel', 3, snow=False)
    tx = cx + u(3)
    tr = u(6)
    tm = dome_mask(tx, gy, tr, tr * 0.95)
    for (x, y) in tm:
        t = dome_tone((x + 0.5 - tx) / tr, (y + 0.5 - gy) / (tr * 0.95), cuts=(0.88, 0.55, 0.25, -0.05))
        row = (gy - 1 - y) // ch
        j = (x - tx + (row % 2) * 2) % S.kv(4, 6)
        if (gy - 1 - y) % ch == ch - 1 or j == 0:
            t = DK if t >= LT else SH
        tl[(x, y)] = SNOW[t]
    mouth = {(x, y) for (x, y) in _shape('arch', tx - u(3), gy - u(5), u(6), u(5))}
    for (x, y) in mouth:
        if S.night:
            tl[(x, y)] = GLOW[DK] if y < gy - u(2) else GLOW[BS]
        else:
            tl[(x, y)] = DEEP[O] if (x, y - 1) in mouth else DEEP[SH]
    outline(tl, tm, SNOW)
    if S.night:
        S.light(tx, gy - u(1), u(7))
    # lantern on a post and snow blocks
    pl = S.lay('post', 4, cast=(u(1), 0, 1))
    px = cx - R - u(4)
    ph = u(11)
    pm = rect(px, gy - ph, px + S.kv(0, 1), gy - 1)
    for (x, y) in pm:
        pl[(x, y)] = SPRUCE[LT] if x == px else SPRUCE[DK]
    outline(pl, pm, SPRUCE)
    lantern(S, px, gy - ph - S.kv(1, 2), side=1, arm=S.kv(2, 4))
    bl = S.lay('blocks', 4, cast=(u(1), 0, 1))
    bm = set()
    for (bx, by, w, h) in ((cx + R + u(1), gy - S.kv(3, 6), S.kv(4, 7), S.kv(3, 6)),
                           (cx + R + u(5), gy - S.kv(3, 6), S.kv(4, 7), S.kv(3, 6)),
                           (cx + R + u(3), gy - S.kv(6, 12), S.kv(4, 7), S.kv(3, 6))):
        b = rect(bx, by, bx + w - 1, by + h - 1)
        for (x, y) in b:
            bl[(x, y)] = SNOW[HI] if y == by else SNOW[DK] if x == bx + w - 1 else SNOW[LT]
        bm |= b
    outline(bl, bm, SNOW)
    ground(S, cx - R - u(8), cx + R + u(11), gy, kind='snow', foot=(cx - R, cx + R + u(9)), paths=[(tx - u(2), tx + u(1))])


def mushroom_house(S, cx, gy):
    """Mushroom house: a fat cream stem as the walls (round, lit left, fibres at HD), a round door and round
    windows in wooden frames, a big red cap lit like a dome with white spots and a gill band underneath, a
    crooked chimney pipe with smoke, small mushrooms round the foot, a lantern; grass ground."""
    k, u = S.k, S.u
    sw = u(_sz(S, 8, 10, 12))
    sh = u(_sz(S, 14, 16, 19))
    lay = S.lay('walls', 0)
    sm = set()
    for y in range(gy - sh, gy):
        flare = (1 if y > gy - S.kv(3, 5) else 0) + (1 if y > gy - S.kv(2, 3) else 0) * (k == 2)
        for x in range(cx - sw - flare, cx + sw + flare):
            sm.add((x, y))
    rnd = S.rnd('stem')
    for (x, y) in sm:
        hw_ = sw + (1 if y > gy - S.kv(3, 5) else 0)
        lay[(x, y)] = STEM[cyl_tone((x + 0.5 - cx) / hw_)]
    if k == 2:
        for (x, y) in sorted(sm):
            if rnd.random() < 0.03 and lay[(x, y)] in (STEM[BS], STEM[LT]):
                for j in range(rnd.randint(3, 6)):
                    if (x, y + j) in sm:
                        lay[(x, y + j)] = darker(lay[(x, y + j)])
    outline(lay, sm, STEM)
    cr = u(_sz(S, 15, 18, 21))
    cry = u(_sz(S, 10, 12, 13))
    cy = gy - sh + u(2)
    gl = S.lay('gills', 1)
    gm = {(x, y) for (x, y) in disc(cx, cy, cr - S.kv(1, 2), S.kv(3, 5)) if y >= cy}
    for (x, y) in gm:
        a = (x - cx)
        gl[(x, y)] = STEM[SH] if (a % S.kv(2, 3) == 0) else STEM[DK]
    outline(gl, gm, STEM)
    cl = S.lay('roof', 3, cast=(u(1), u(2), 1), roof=True)
    cm = dome_mask(cx, cy, cr, cry, below=S.kv(1, 2))
    for (x, y) in cm:
        t = dome_tone((x + 0.5 - cx) / cr, (y + 0.5 - cy) / cry)
        if y >= cy:
            t = max(SH, min(t, DK))
        cl[(x, y)] = MUSH[t]
    spots = [(-0.55, -0.45, 0.22), (0.1, -0.75, 0.16), (0.55, -0.35, 0.2), (-0.15, -0.2, 0.15), (0.78, 0.0, 0.1),
             (-0.85, -0.05, 0.1)]
    for (sx, sy, sr) in spots:
        scx, scy = cx + sx * cr, cy + sy * cry
        rr = max(1.2, sr * cr)
        pts = disc(scx, scy, rr, rr * 0.75)
        for (x, y) in pts:
            if (x, y) in cm:
                t = dome_tone((x + 0.5 - cx) / cr, (y + 0.5 - cy) / cry)
                cl[(x, y)] = CREAMR[min(HI, t + 1)] if t >= BS else CREAMR[DK]
    for x in range(cx - cr, cx + cr):
        if (x, cy + S.kv(1, 2) - 1) in cm:
            cl[(x, cy + S.kv(1, 2) - 1)] = MUSH[SH]
    outline(cl, cm, MUSH)
    S.field({p for p in cm if p[1] < cy - cry // 3})
    dw, dh = S.kv(6, 10), S.kv(9, 15)
    dx = cx - dw // 2 - u(2)
    door(S, dx, gy - dh, dw, dh, OAK, DARK_OAK, style='round', glass=False)
    ws = S.kv(5, 8)
    window(S, cx + u(3), gy - sh + u(5), ws, ws, frame=OAK, style='round', sill=None)
    if S.size != 's':
        window(S, cx - sw + u(2), gy - sh + u(5), ws - S.kv(1, 2), ws - S.kv(1, 2), frame=OAK, style='round',
               sill=None)
    lantern(S, dx + dw + S.kv(0, 1), gy - dh + S.kv(1, 2), side=1, arm=S.kv(2, 3))
    # a crooked chimney pipe out of the cap
    pl = S.lay('chimney', 4, cast=(u(1), u(1), 1))
    px = cx + u(7)
    pw = S.kv(2, 3)
    ptop = cy - cry - u(1)
    pm = set()
    for y in range(ptop, cy - int(cry * 0.62)):
        off = 0 if y > ptop + u(3) else 1
        for i in range(pw):
            pm.add((px + i + off, y))
    for (x, y) in pm:
        pl[(x, y)] = DARK_IRON[LT] if (x - 1, y) not in pm else DARK_IRON[DK] if (x + 1, y) not in pm else DARK_IRON[BS]
    outline(pl, pm, DARK_IRON)
    puff(S, px + 1 + pw // 2, ptop - S.kv(1, 2), seed=9)
    # little mushrooms round the foot
    ml = S.lay('mushrooms', 5)
    mm = set()
    for i, (mx, R2) in enumerate(((cx - sw - u(4), MUSH), (cx + sw + u(3), DIRT), (cx + sw + u(7), MUSH))):
        hgt = S.kv(3, 5)
        for j in range(hgt):
            ml[(mx, gy - 1 - j)] = STEM[LT]
            mm.add((mx, gy - 1 - j))
            if k == 2:
                ml[(mx + 1, gy - 1 - j)] = STEM[DK]
                mm.add((mx + 1, gy - 1 - j))
        capw = S.kv(1, 3)
        for a in range(-capw, capw + 1 + (1 if k == 2 else 0)):
            ml[(mx + a, gy - hgt - 1)] = R2[LT if a < 0 else BS]
            mm.add((mx + a, gy - hgt - 1))
            if k == 2 and abs(a) < capw:
                ml[(mx + a, gy - hgt - 2)] = R2[HI if a < 0 else LT]
                mm.add((mx + a, gy - hgt - 2))
        if k == 2 and R2 is MUSH:
            ml[(mx, gy - hgt - 2)] = CREAMR[HI]
    outline(ml, mm, DIRT)
    if S.night:
        S.light(cx, gy + u(1.5), u(6))
    ground(S, cx - cr - u(4), cx + cr + u(7), gy, foot=(cx - sw, cx + sw), paths=[(dx, dx + dw - 1)])


def treehouse(S, cx, gy):
    """Treehouse: a big oak (flared trunk, two branches, a crown of lit leaf blobs behind and round the
    house), a plank cabin on a platform with a railing, braces under the platform, a small shingle roof,
    a window and a door, a ladder down the trunk, a lantern."""
    k, u = S.k, S.u
    tw = u(_sz(S, 5, 6, 7))
    th = u(_sz(S, 30, 34, 38))
    tx0 = cx - tw // 2
    crown = S.lay('crown_back', -2, cast=None)
    cr = u(_sz(S, 15, 18, 21))
    cy = gy - th - u(2)
    blobs = [(cx - cr * 0.7, cy + cr * 0.15, cr * 0.6, cr * 0.5), (cx + cr * 0.75, cy + cr * 0.1, cr * 0.6, cr * 0.5),
             (cx - cr * 0.2, cy - cr * 0.45, cr * 0.75, cr * 0.55), (cx + cr * 0.35, cy - cr * 0.3, cr * 0.7, cr * 0.55)]
    foliage(S, crown, blobs, LEAVES, seed=3)
    tl = S.lay('trunk', -1)
    tm = trunk(S, tl, tx0, tx0 + tw - 1, cy, gy - 1, OAK_LOG, seed=2)
    for side in (-1, 1):                                  # two branches up into the crown
        for i in range(u(8)):
            bx = (tx0 - 1 - i if side < 0 else tx0 + tw + i)
            by = cy + u(6) - i // 2 * 1 - (i // 2)
            for j in range(S.kv(2, 3)):
                tl[(bx, by + j)] = OAK_LOG[LT if j == 0 else DK]
                tm.add((bx, by + j))
    outline(tl, tm, OAK_LOG)
    # platform
    pw_ = u(_sz(S, 14, 17, 20))
    py = gy - th + u(14)
    pl = S.lay('platform', 2, cast=(u(1), u(1), 1))
    pm = rect(cx - pw_, py, cx + pw_ - 1, py + S.kv(1, 3))
    for (x, y) in pm:
        r = y - py
        pl[(x, y)] = OAK[LT] if r == 0 else OAK[DK] if r == S.kv(1, 3) else OAK[BS]
        if k == 2 and r == 1 and (x - cx) % 6 == 0:
            pl[(x, y)] = OAK[SH]
    for side in (-1, 1):                                  # braces from the trunk to the platform ends
        for i in range(u(9)):
            bx = tx0 - i if side < 0 else tx0 + tw - 1 + i
            by = py + S.kv(2, 4) + u(9) - i
            for j in range(S.kv(1, 2)):
                pl[(bx, by + j)] = DARK_OAK[BS if j == 0 else DK]
                pm.add((bx, by + j))
    outline(pl, pm, OAK)
    S.ledge(cx - pw_, cx + pw_ - 1, py)
    # cabin
    hw_ = u(_sz(S, 8, 10, 12))
    hx0, hx1 = cx - hw_ - u(2), cx + hw_ - 1 - u(2)
    hy = py - u(11)
    hl = S.lay('walls', 1)
    hm = rect(hx0, hy, hx1, py - 1)
    planks(S, hl, hm, OAK, y0=py, seed=17)
    log_v(S, hl, hx0, hx0 + S.kv(0, 1), hy, py - 1, OAK_LOG)
    log_v(S, hl, hx1 - S.kv(0, 1), hx1, hy, py - 1, OAK_LOG)
    outline(hl, hm, OAK)
    _, inner, top = gable_roof(S, (hx0 + hx1 + 1) // 2, hy + S.kv(0, 1), hw_ + u(3), S.kv(3, 6), SHINGLE,
                               trim=DARK_OAK, seed=18)
    gg = S.lay('gable', 2)
    gm = {(x, y) for x in range(hx0, hx1 + 1) for y in range(inner(x) - 1, hy)}
    planks(S, gg, gm, OAK, vertical=True, x0=hx0, seed=19)
    outline(gg, gm, OAK)
    dw, dh = S.kv(5, 8), S.kv(8, 15)
    door(S, hx0 + u(3), py - dh, dw, dh, OAK, DARK_OAK)
    window(S, hx1 - u(3) - S.kv(5, 8), hy + S.kv(2, 4), S.kv(5, 8), S.kv(5, 8), frame=DARK_OAK, sill=OAK)
    # railing
    rl = S.lay('railing', 5, cast=(u(1), u(1), 1))
    rm = set()
    ry = py - S.kv(4, 7)
    for x in list(range(cx - pw_, hx0 - 1)) + list(range(hx1 + 2, cx + pw_)):
        rl[(x, ry)] = OAK[LT]
        rm.add((x, ry))
        if (x - cx) % S.kv(3, 4) == 0:
            for y in range(ry + 1, py):
                rl[(x, y)] = OAK[BS]
                rm.add((x, y))
    outline(rl, rm, OAK)
    lantern(S, cx + pw_ - u(2), ry - S.kv(1, 2), side=1, arm=S.kv(1, 2))
    # front crown blobs over the trunk shoulders and the ladder
    lad = S.lay('ladder', 3)
    lm = set()
    lx = cx + tw // 2 - S.kv(1, 2)
    for y in range(py + S.kv(2, 4), gy):
        for x in (lx, lx + S.kv(3, 5)):
            lad[(x, y)] = OAK[LT] if x == lx else OAK[DK]
            lm.add((x, y))
        if (y - py) % S.kv(3, 4) == 0:
            for x in range(lx + 1, lx + S.kv(3, 5)):
                lad[(x, y)] = OAK[BS]
                lm.add((x, y))
    outline(lad, lm, OAK)
    front = S.lay('crown_front', 6)
    fb = [(cx - pw_ - u(1), py - u(4), cr * 0.35, cr * 0.3), (cx + pw_ + u(1), py - u(6), cr * 0.35, cr * 0.3)]
    foliage(S, front, fb, LEAVES, seed=5)
    if S.night:
        S.light(cx, py + u(1), u(7))
    ground(S, cx - cr - u(4), cx + cr + u(6), gy, foot=(tx0 - u(3), tx0 + tw + u(3)), shadow_len=u(8))


def tower(S, cx, gy, roof='battlements'):
    """Round stone tower: courses of stone blocks with joints getting closer toward the sides (the cylinder
    turning away), cylinder shading (lit left, dark right), arrow slits, an arched door with a torch, a
    corbelled parapet with merlons and a pennant on a pole (roof='cone': a conical slate roof)."""
    k, u = S.k, S.u
    R = u(_sz(S, 8, 10, 12))
    H = u(_sz(S, 36, 46, 58))
    yt = gy - H
    lay = S.lay('walls', 0)
    m = rect(cx - R, yt, cx + R - 1, gy - 1)
    ch = S.kv(3, 5)
    for (x, y) in m:
        nx = (x + 0.5 - cx) / R
        t = cyl_tone(nx)
        row, r = (gy - 1 - y) // ch, (gy - 1 - y) % ch
        ang = math.asin(max(-0.999, min(0.999, nx)))
        bwa = 0.62 if k == 1 else 0.5
        a = (ang / bwa + (row % 2) * 0.5)
        j = a - math.floor(a)
        jw = 1.0 / (R * bwa * max(0.25, math.cos(ang)))
        if r == ch - 1 or j < jw:
            t = max(SH, t - 1)
        elif r == 0 and k == 2 and t < HI:
            t = t + 1 if t >= BS else t
        lay[(x, y)] = STONE[t]
    if k == 2:
        rnd = S.rnd('tower')
        for (x, y) in sorted(m):
            if rnd.random() < 0.004 and y > yt + u(10):
                for i in range(rnd.randint(2, 4)):
                    if (x + i, y - i // 2) in m:
                        lay[(x + i, y - i // 2)] = MOSS[LT if i == 0 else BS]
    outline(lay, m, STONE)
    for (sy, sx) in ((yt + u(8), cx - u(3)), (yt + u(20), cx + u(2)), (yt + u(32), cx - u(2))):
        if sy < gy - u(14):
            window(S, sx, sy, S.kv(1, 2), S.kv(5, 9), style='slit', sill=None)
    dw, dh = S.kv(6, 10), S.kv(9, 16)
    door(S, cx - dw // 2, gy - dh, dw, dh, SPRUCE, DEEP, style='arch')
    torch(S, cx + dw // 2 + S.kv(2, 3), gy - dh + S.kv(2, 4))
    if roof == 'cone':
        hip_roof(S, cx - R - u(2), cx + R + u(1), yt + S.kv(1, 2), R + u(3), SLATE, style='slate', slope=(1, 1))
        return ground(S, cx - R - u(7), cx + R + u(8), gy, foot=(cx - R, cx + R - 1), paths=[(cx - dw // 2, cx + dw // 2)])
    # corbels and parapet
    pl = S.lay('parapet', 2, cast=(u(1), u(1), 1))
    ph = S.kv(4, 7)
    pm = rect(cx - R - S.kv(2, 3), yt - ph, cx + R - 1 + S.kv(2, 3), yt - 1)
    PR = R + S.kv(2, 3)
    for (x, y) in pm:
        nx = (x + 0.5 - cx) / PR
        t = cyl_tone(nx)
        if y == yt - ph:
            t = min(HI, t + 1)
        pl[(x, y)] = STONE[t]
    for i, x in enumerate(range(cx - R, cx + R, S.kv(3, 5))):        # corbels: little brackets under it
        for j in range(S.kv(1, 2)):
            pl[(x, yt + j)] = STONE[LT] if x < cx else STONE[DK]
            pl[(x + 1, yt + j)] = STONE[DK]
            pm |= {(x, yt + j), (x + 1, yt + j)}
    mw = S.kv(3, 5)
    mh = S.kv(3, 5)
    for x in range(cx - PR, cx + PR - mw + 1, mw * 2):
        mm = rect(x, yt - ph - mh, x + mw - 1, yt - ph - 1)
        for (px, py) in mm:
            t = cyl_tone((px + 0.5 - cx) / PR)
            pl[(px, py)] = STONE[min(HI, t + 1) if py == yt - ph - mh else t]
        pm |= mm
    outline(pl, pm, STONE)
    # pennant on a pole
    fl = S.lay('flag', 3, cast=None)
    fx = cx - 1
    fy = yt - ph - u(14)
    for y in range(fy, yt - ph):
        fl[(fx, y)] = DARK_OAK[LT]
        if k == 2:
            fl[(fx + 1, y)] = DARK_OAK[DK]
    fm = set()
    flen = u(9)
    for i in range(flen):
        hh = max(1, int((S.kv(5, 9)) * (1 - i / flen)) )
        wave = int(round(math.sin(i * 0.6) * S.kv(0.6, 1.2)))
        for j in range(hh):
            y = fy + S.kv(1, 1) + j + wave + (S.kv(5, 9) - hh) // 2
            fl[(fx + S.kv(1, 2) + i, y)] = CLOTH[LT if j == 0 else DK if j == hh - 1 else BS]
            fm.add((fx + S.kv(1, 2) + i, y))
    outline(fl, fm | {(fx, y) for y in range(fy, yt - ph)}, CLOTH)
    if S.night:
        S.light(cx, gy + u(1), u(6), 'fire')
    ground(S, cx - R - u(7), cx + R + u(8), gy, foot=(cx - R, cx + R - 1), paths=[(cx - dw // 2, cx + dw // 2)])


def sails(S, hx, hy, length, width, cross='x', name='sails', z=7):
    """Four lattice sails round a hub at (hx, hy): a spar per arm, a lattice of bars on one side with canvas
    in the cells (lit near the spar, darker at the far edge). cross='x' puts the arms on the diagonals
    (clean 45 deg pixel lines), '+' on the axes."""
    k = S.k
    lay = S.lay(name, z, cast=(S.u(1), S.u(1), 1))
    dirs = ((1, 1), (-1, 1), (-1, -1), (1, -1)) if cross == 'x' else ((1, 0), (0, 1), (-1, 0), (0, -1))
    f = 1.42 if cross == 'x' else 1.0
    Lu, Wu = int(length * f), max(2, int(width * f))
    r0 = int(S.u(4) * f)
    sp = S.kv(1, 2)
    step = int(S.kv(4, 5) * f)
    m = set()
    span = length + 2
    for (a, b) in dirs:
        for dy in range(-span, span + 1):
            for dx in range(-span, span + 1):
                al = a * dx + b * dy
                pe = -b * dx + a * dy
                if al < 1 or al > Lu:
                    continue
                p = (hx + dx, hy + dy)
                if 0 <= pe < sp:
                    lay[p] = DARK_OAK[LT if pe == 0 else DK]
                    m.add(p)
                elif sp <= pe <= Wu and al >= r0:
                    edge_ = pe >= Wu - (0 if k == 1 else 1) or al >= Lu - (0 if k == 1 else 1) or al <= r0 + (0 if k == 1 else 1)
                    bar = (al - r0) % step == 0
                    if edge_ or bar:
                        lay[p] = OAK[BS] if not edge_ else OAK[DK]
                    else:
                        lay[p] = CANVAS[LT] if pe < sp + Wu // 3 else CANVAS[BS] if pe < Wu - Wu // 4 else CANVAS[DK]
                    m.add(p)
    hub = disc(hx + 0.5, hy + 0.5, S.kv(1.6, 3.0))
    for (x, y) in hub:
        lay[(x, y)] = IRON[dome_tone((x + 0.5 - hx - 0.5) / S.kv(1.6, 3.0), (y + 0.5 - hy - 0.5) / S.kv(1.6, 3.0))]
    m |= hub
    outline(lay, m, DARK_OAK)
    pixel_perfect_layer(lay, {DARK_OAK[O], DARK_OAK[SH]})
    return m


def pixel_perfect_layer(lay, only):
    """shading.pixel_perfect on a Layer (doubles out of 1 px lines of the given colours)."""
    if not lay:
        return
    x0, y0, x1, y1 = bbox(list(lay))
    im = Image.new('RGBA', (x1 - x0 + 3, y1 - y0 + 3), (0, 0, 0, 0))
    px = im.load()
    for (x, y), c in lay.items():
        px[x - x0 + 1, y - y0 + 1] = c
    pixel_perfect(im, only=only)
    lay.clear()
    for y in range(im.height):
        for x in range(im.width):
            if px[x, y][3]:
                lay[(x + x0 - 1, y + y0 - 1)] = px[x, y]


def windmill(S, cx, gy, cross='x'):
    """Windmill: a tapering whitewashed tower on a cobblestone base, a door and small windows, a domed
    shingle cap, a hub with four lattice sails with canvas (cross='x' diagonal, '+' upright)."""
    k, u = S.k, S.u
    H = u(_sz(S, 28, 34, 40))
    rb, rt = u(_sz(S, 9, 11, 13)), u(_sz(S, 6, 7, 8))
    yt = gy - H
    bh = S.kv(4, 8)
    lay = S.lay('walls', 0)
    m = set()
    half_at = {}
    for y in range(yt, gy):
        half = rt + (rb - rt) * (y - yt) / H
        half_at[y] = half
        for x in range(int(round(cx - half)), int(round(cx + half))):
            m.add((x, y))
    body = {p for p in m if p[1] < gy - bh}
    base = m - body
    plaster(S, lay, body, WHITEWASH, seed=21, patches=False)
    for (x, y) in body:
        t = cyl_tone((x + 0.5 - cx) / half_at[y])
        lay[(x, y)] = WHITEWASH[t] if lay[(x, y)] == WHITEWASH[BS] else (WHITEWASH[max(SH, t - 1)])
    stones(S, lay, base, COBBLE, seed=22)
    for (x, y) in base:
        if y == gy - bh:
            lay[(x, y)] = COBBLE[LT]
    outline(lay, m, WHITEWASH, dark=DEEP[O])
    S.ledge(int(cx - half_at[gy - bh]) - 1, int(cx + half_at[gy - bh]), gy - bh)
    # cap: a dome of shingles
    cl = S.lay('roof', 3, cast=(u(1), u(1), 1), roof=True)
    cr, cry = rt + u(2), u(7)
    cm = dome_mask(cx, yt + S.kv(1, 2), cr, cry)
    for (x, y) in cm:
        t = dome_tone((x + 0.5 - cx) / cr, (y + 0.5 - yt) / cry)
        if (yt + S.kv(1, 2) - y) % S.kv(2, 3) == 0:
            t = max(SH, t - 1)
        cl[(x, y)] = SHINGLE[t]
    fin = rect(cx - 1, yt - cry - S.kv(1, 3), cx - 1 + S.kv(0, 1), yt - cry)
    for (x, y) in fin:
        cl[(x, y)] = DARK_IRON[LT if x == cx - 1 else DK]
    outline(cl, cm | fin, SHINGLE)
    S.field(cm)
    dw, dh = S.kv(5, 9), S.kv(8, 14)
    door(S, cx - dw // 2, gy - dh, dw, dh, SPRUCE, DARK_OAK)
    for i, wy in enumerate((yt + u(12), yt + u(20))):
        if wy + S.kv(4, 6) < gy - dh - u(2):
            window(S, cx - S.kv(2, 3) + (i * 2 - 1) * u(2), wy, S.kv(4, 6), S.kv(4, 7), frame=DARK_OAK,
                   style='single' if k == 1 else 'cross', sill=None)
    hx, hy = cx - 1 + (0 if k == 1 else 0), yt + u(3)
    sails(S, hx, hy, u(_sz(S, 20, 24, 28)), u(_sz(S, 5, 6, 7)), cross=cross)
    if S.night:
        S.light(cx, gy + u(1.5), u(6))
    ground(S, cx - rb - u(16), cx + rb + u(18), gy, foot=(cx - rb, cx + rb), paths=[(cx - dw // 2, cx + dw // 2 - 1)])


def water_wheel(S, wx, wy, R, name='wheel', z=5):
    """A water wheel: a wooden rim (lit top-left, dark bottom-right), eight spokes on the axes and
    diagonals (clean lines), paddles round the rim, an iron hub."""
    k = S.k
    lay = S.lay(name, z, cast=(S.u(1), 0, 1))
    m = set()
    rw = S.kv(1, 2)
    for (x, y) in disc(wx, wy, R):
        d = math.hypot(x + 0.5 - wx, y + 0.5 - wy)
        if d > R - rw - 0.3:
            ang = math.atan2(y + 0.5 - wy, x + 0.5 - wx)
            lit = -math.cos(ang) * 0.6 - math.sin(ang) * 0.7
            lay[(x, y)] = OAK[LT if lit > 0.35 else BS if lit > -0.3 else DK]
            m.add((x, y))
    cx_, cy_ = int(math.floor(wx)), int(math.floor(wy))
    for (a, b) in ((1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (-1, 1), (-1, -1), (1, -1)):
        n = int((R - rw) / (1.42 if a and b else 1))
        for i in range(1, n + 1):
            p = (cx_ + a * i, cy_ + b * i)
            if p not in m:
                lay[p] = DARK_OAK[BS if (a, b) in ((1, 0), (0, 1), (1, 1)) else LT]
                m.add(p)
    np_ = 12
    pl = S.kv(2, 4)
    for i in range(np_):
        ang = i * 2 * math.pi / np_ + 0.13
        for r in range(int(R - rw), int(R + pl)):
            for w_ in ((0,) if k == 1 else (0, 1)):
                x = wx + math.cos(ang) * (r + 0.5) - math.sin(ang) * w_
                y = wy + math.sin(ang) * (r + 0.5) + math.cos(ang) * w_
                p = (int(math.floor(x)), int(math.floor(y)))
                lit = -math.cos(ang) * 0.6 - math.sin(ang) * 0.7
                if p not in m or r >= R:
                    lay[p] = OAK[LT if lit > 0.3 and w_ == 0 else BS if lit > -0.3 else DK]
                    m.add(p)
    hub = disc(cx_ + 0.5, cy_ + 0.5, S.kv(1.5, 2.6))
    for (x, y) in hub:
        lay[(x, y)] = IRON[dome_tone((x - cx_) / S.kv(1.5, 2.6), (y - cy_) / S.kv(1.5, 2.6))]
    m |= hub
    outline(lay, m, DARK_OAK)
    pixel_perfect_layer(lay, {DARK_OAK[O], DARK_OAK[SH]})
    return m


def water(S, lay, mask, seed=0, flow='down'):
    """Water: base, lit ripple dashes and dark troughs as short horizontal clusters (2-5 px), never noise;
    flow='down' adds foam streaks along the current."""
    k = S.k
    rnd = S.rnd('water', seed)
    for p in mask:
        lay[p] = WATER[BS]
    for (x, y) in sorted(mask):
        r = rnd.random()
        if r < S.kv(0.07, 0.05):
            n = rnd.randint(2, S.kv(3, 5))
            c = WATER[LT] if r < 0.035 else WATER[DK]
            for i in range(n):
                if (x + i, y) in mask and lay[(x + i, y)] == WATER[BS]:
                    lay[(x + i, y)] = c
        elif r < 0.075 and k == 2 and flow == 'down':
            for i in range(rnd.randint(2, 4)):
                if (x, y + i) in mask:
                    lay[(x, y + i)] = WATER[HI]
    for (x, y) in mask:
        if (x, y - 1) not in mask:
            lay[(x, y)] = WATER[LT]


def watermill(S, cx, gy):
    """Water mill: a cobblestone ground floor and a timber-framed plaster upper floor (dark beams, braces at
    HD), a shingle roof, a door with flour sacks, a lantern; a big water wheel on the right turning in a
    stream that runs across the ground and spills over its front edge."""
    k, u = S.k, S.u
    hw = u(_sz(S, 11, 13, 16))
    x0, x1 = cx - hw - u(5), cx + hw - 1 - u(5)
    yf = gy
    y1 = yf - u(10)
    y2 = y1 - u(11)
    lay = S.lay('walls', 0)
    m1 = rect(x0, y1, x1, yf - 1)
    stones(S, lay, m1, COBBLE, seed=23)
    for x in range(x0, x1 + 1):
        lay[(x, y1)] = COBBLE[LT]
    m2 = rect(x0, y2, x1, y1 - 1)
    plaster(S, lay, m2, PLASTER, seed=24, patches=False)
    outline(lay, m1 | m2, COBBLE)
    bl = S.lay('beams', 1, cast=(u(1), u(1), 1))
    bm = set()
    bw = S.kv(1, 2)
    for x in (x0, (x0 + x1) // 2, x1 - bw + 1):
        for y in range(y2, y1):
            for i in range(bw):
                bl[(x + i, y)] = DARK_OAK[LT if i == 0 else DK]
                bm.add((x + i, y))
    for y in (y2, y1 - bw):
        for x in range(x0, x1 + 1):
            for i in range(bw):
                bl[(x, y + i)] = DARK_OAK[LT if i == 0 else DK]
                bm.add((x, y + i))
    if k == 2:
        for (xa, xb) in ((x0 + bw, (x0 + x1) // 2), ((x0 + x1) // 2 + bw, x1 - bw + 1)):
            n = y1 - bw - (y2 + bw)
            for j in range(n):
                x = xa + (j * (xb - xa)) // n
                for i in range(bw):
                    bl[(x + i, y2 + bw + j)] = DARK_OAK[BS if i == 0 else DK]
                    bm.add((x + i, y2 + bw + j))
    outline(bl, bm, DARK_OAK)
    oh = u(3)
    hip_roof(S, x0 - oh, x1 + oh, y2 + S.kv(1, 2), u(10), SHINGLE, style='wood', seed=25)
    ww = S.kv(5, 8)
    window(S, x0 + u(4), y2 + S.kv(3, 5), ww, S.kv(5, 8), frame=DARK_OAK, sill=OAK)
    window(S, x1 - u(4) - ww, y2 + S.kv(3, 5), ww, S.kv(5, 8), frame=DARK_OAK, sill=OAK)
    dw, dh = S.kv(6, 10), S.kv(8, 15)
    dx = x0 + u(5)
    door(S, dx, yf - dh, dw, dh, SPRUCE, DARK_OAK)
    lantern(S, dx + dw + S.kv(0, 1), yf - dh + S.kv(1, 2), side=1, arm=S.kv(2, 3))
    sk = S.lay('sacks', 5, cast=(u(1), 0, 1))
    sm = set()
    for i, sx in enumerate((dx + dw + u(4), dx + dw + u(4) + S.kv(4, 7))):
        pts = {(x, y) for (x, y) in disc(sx, gy - S.kv(2, 3.5), S.kv(2.2, 3.8), S.kv(2.4, 3.6)) if y < gy}
        for (x, y) in pts:
            t = dome_tone((x + 0.5 - sx) / S.kv(2.2, 3.8), (y + 0.5 - gy + S.kv(2, 3.5)) / S.kv(2.4, 3.6))
            sk[(x, y)] = CANVAS[t]
        ty = min(y for _, y in pts)
        sk[(sx - 1 if k == 2 else int(sx), ty - 1)] = CANVAS[BS]
        sk[(int(sx), ty)] = ROPE[DK]
        sm |= pts | {(int(sx), ty - 1)}
    outline(sk, sm, CANVAS)
    R = u(_sz(S, 12, 14, 16))
    wx, wy = x1 + u(3) + R * 0.55, gy - R * 0.62
    water_wheel(S, wx, wy, R)
    # the stream runs from the back of the island to its front edge under the wheel and spills over it; the
    # wheel's lowest paddles are under the water line, foam where they dip
    wl = S.lay('stream', 4, snow=False)
    sx0, sx1 = int(wx - R * 0.45), int(wx + R * 0.45)
    back, front = u(4), u(7)
    wline = gy + S.kv(1, 2)
    wheel = S.lay('wheel')
    for p in [p for p in wheel if p[1] > wline]:
        del wheel[p]
    sm2 = set()
    for y in range(gy - back, gy + front):
        d = (y - gy + back) // S.kv(3, 4)
        sm2 |= {(x, y) for x in range(sx0 - d, sx1 + d + 1)}
    yb = gy + front
    sm2 |= rect(sx0 - (front + back) // S.kv(3, 4) + 1, yb, sx1 + (front + back) // S.kv(3, 4) - 1,
                yb + S.kv(3, 6) - 1)
    water(S, wl, sm2, seed=3)
    for (x, y) in sm2:
        if y >= yb:
            wl[(x, y)] = WATER[HI] if (x * 3 + y) % 5 == 0 else WATER[LT] if (x + y) % 3 else WATER[BS]
    foam = S.lay('foam', 6, snow=False)
    for x in range(int(wx - R * 0.8), int(wx + R * 0.8) + 1):
        if (x, wline) in wheel or (x, wline - 1) in wheel or abs(x - wx) < R * 0.45:
            for j in range(S.kv(1, 2)):
                foam[(x, wline + j)] = SMOKE[HI] if (x + j) % 3 else WATER[HI]
    outline(wl, sm2, WATER)
    if S.snow:
        for (x, y) in sm2:
            if (x * 7 + y * 3) % 11 == 0 and y < gy:
                wl[(x, y)] = ICE[LT]
    if S.night:
        S.light(dx + dw / 2, gy + u(1.5), u(6))
    ground(S, x0 - u(5), int(wx + R + u(6)), gy, foot=(x0 - 1, x1 + 1), paths=[(dx, dx + dw - 1)])


# ------------------------------------------------------------------ castle pieces
def battlements(S, lay, x0, x1, y, R=STONE, mw=None, mh=None, ends=True):
    """Merlons along a wall top whose top row is y: blocks mw wide every 2*mw, lit top row and left
    column, dark right column. Returns their pixels."""
    k = S.k
    mw = mw or S.kv(3, 5)
    mh = mh or S.kv(3, 5)
    m = set()
    xs = list(range(x0, x1 - mw + 2, mw * 2))
    if ends and xs and xs[-1] != x1 - mw + 1:
        xs.append(x1 - mw + 1)
    for xa in xs:
        b = rect(xa, y - mh, xa + mw - 1, y - 1)
        for (x, yy) in b:
            t = BS
            if yy == y - mh:
                t = HI if k == 2 and x == xa else LT
            elif x == xa:
                t = LT
            elif x == xa + mw - 1:
                t = DK
            lay[(x, yy)] = R[t]
        m |= b
    return m


def banner(S, x, y, w, h, R=CLOTH, emblem=GOLDR, name='banners', z=5):
    """A hanging banner: a dark rod with lit ends, cloth lit on the left edge and dark on the right, fold
    lines (HD), a gold emblem, a swallow-tail bottom."""
    k = S.k
    lay = S.lay(name, z, cast=(S.u(1), S.u(1), 1))
    m = set()
    for i in range(-1, w + 1):
        lay[(x + i, y)] = DARK_OAK[LT if i < w // 2 else DK]
        m.add((x + i, y))
    tail = S.kv(2, 3)
    for j in range(1, h + 1):
        for i in range(w):
            if j > h - tail and abs(i + 0.5 - w / 2) < (j - (h - tail)) * (w / 2) / tail:
                continue
            t = BS
            if i == 0:
                t = LT
            elif i == w - 1:
                t = DK
            elif k == 2 and i in (w // 3, 2 * w // 3) and j > 1:
                t = DK if i == 2 * w // 3 else LT
            if j == 1:
                t = DK
            lay[(x + i, y + j)] = R[t]
            m.add((x + i, y + j))
    ex, ey = x + w // 2, y + h // 2 - S.kv(0, 1)
    pts = [(0, -1), (-1, 0), (0, 0), (1, 0), (0, 1)] if k == 1 else \
        [(0, -2), (-1, -1), (0, -1), (1, -1), (-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0), (-1, 1), (0, 1), (1, 1), (0, 2)]
    for (a, b) in pts:
        p = (ex + a - (1 if w % 2 == 0 and k == 1 else 0), ey + b)
        lay[p] = emblem[HI if a + b < -1 else LT if a + b < 1 else BS]
    outline(lay, m, R)
    return m


def portcullis(S, lay, opening, raised=0.45):
    """An iron portcullis in an arched opening: the dark passage behind, a grid of bars (lit left edge per
    bar), spikes along the bottom, raised `raised` of the way."""
    k = S.k
    x0, y0, x1, y1 = bbox(opening)
    for p in opening:
        lay[p] = DEEP[O] if p[1] > y0 + S.kv(1, 2) else DEEP[SH]
    if S.night:
        for (x, y) in opening:
            if y > y1 - (y1 - y0) // 3:
                lay[(x, y)] = GLOW[SH]
    bottom = y0 + int((y1 - y0) * (1 - raised))
    sp = S.kv(2, 3)
    hs = S.kv(3, 4)
    for (x, y) in opening:
        if y > bottom:
            continue
        if (x - x0) % sp == 0:
            lay[(x, y)] = DARK_IRON[LT] if k == 1 or (x - x0) % (2 * sp) == 0 else DARK_IRON[BS]
        elif (y - y0) % hs == 0:
            lay[(x, y)] = DARK_IRON[DK]
    for x in range(x0, x1 + 1):
        if (x - x0) % sp == 0 and (x, bottom + 1) in opening:
            lay[(x, bottom + 1)] = DARK_IRON[BS]


def square_tower(S, x0, x1, ytop, gy, R=STONE, name='tower', z=2, slits=2, seed=0):
    """A square castle tower: ashlar front face, a corbelled overhang and merlons on top, arrow slits;
    it casts a shadow on the wall to its right."""
    k, u = S.k, S.u
    lay = S.lay(name, z, cast=(u(3), 0, 1))
    m = rect(x0, ytop, x1, gy - 1)
    ashlar(S, lay, m, R, y0=gy, x0=x0, bw=S.kv(6, 10), bh=S.kv(3, 5), seed=seed, moss=0.03 if k == 2 else 0)
    for y in range(ytop, gy):
        lay[(x0, y)] = lighter(lay[(x0, y)])
    cy = ytop - S.kv(2, 3)
    cm = rect(x0 - S.kv(1, 2), cy, x1 + S.kv(1, 2), ytop - 1)
    for (x, y) in cm:
        lay[(x, y)] = R[LT] if y == cy else R[BS] if (x - x0) % S.kv(3, 4) else R[DK]
    mm = battlements(S, lay, x0 - S.kv(1, 2), x1 + S.kv(1, 2), cy, R)
    outline(lay, m | cm | mm, R)
    for i in range(slits):
        sy = ytop + u(6) + i * u(12)
        if sy + S.kv(5, 9) < gy - u(10):
            window(S, (x0 + x1) // 2, sy, S.kv(1, 2), S.kv(5, 9), style='slit', sill=None)
    return m | cm | mm


def castle_gate(S, cx, gy):
    """Castle gate: a gatehouse wall with merlons between two square towers (each casts a shadow on the
    wall), a pointed-arch gateway with dark voussoirs and a half-raised iron portcullis, red banners with a
    gold emblem, torches either side; a cobble road out of the gate."""
    k, u = S.k, S.u
    hw = u(_sz(S, 14, 17, 20))
    tw = u(_sz(S, 7, 8, 9))
    th = u(_sz(S, 32, 38, 44))
    wh = u(_sz(S, 22, 26, 30))
    wl = S.lay('wall', 0)
    wm = rect(cx - hw, gy - wh, cx + hw - 1, gy - 1)
    ashlar(S, wl, wm, WALL_STONE, y0=gy, x0=cx, bw=S.kv(8, 12), bh=S.kv(3, 5), seed=31)
    mm = battlements(S, wl, cx - hw + tw, cx + hw - 1 - tw, gy - wh, WALL_STONE)
    outline(wl, wm | mm, WALL_STONE)
    for side in (-1, 1):
        xa = cx - hw - tw // 2 if side < 0 else cx + hw - tw + tw // 2
        square_tower(S, xa, xa + tw - 1 + (1 if k == 2 else 0), gy - th, gy, STONE, name='tower_l' if side < 0 else 'tower_r',
                     seed=side + 40)
    gw, gh = u(_sz(S, 10, 12, 14)), u(_sz(S, 14, 17, 20))
    gl = S.lay('gate', 3)
    op = _shape('lancet', cx - gw // 2, gy - gh, gw, gh)
    portcullis(S, gl, op)
    ring = {p for p in edge_ring(op) if p[1] < gy}
    ring2 = {p for p in edge_ring(op | ring) if p[1] < gy} if k == 2 else set()
    for (x, y) in ring | ring2:
        gl[(x, y)] = DEEP[LT] if ((x + y) // S.kv(2, 3)) % 2 == 0 else DEEP[BS]
        if (x, y) in ring2 and x > cx:
            gl[(x, y)] = DEEP[DK]
    outline(gl, op | ring | ring2, DEEP)
    bw, bh = S.kv(4, 7), u(10)
    for side in (-1, 1):
        bx = cx - gw // 2 - u(3) - bw if side < 0 else cx + gw // 2 + u(3)
        banner(S, bx, gy - wh + S.kv(2, 3), bw, bh)
        torch(S, cx - gw // 2 - S.kv(3, 4) if side < 0 else cx + gw // 2 + S.kv(2, 3), gy - u(9))
    if S.night:
        S.light(cx, gy, u(8), 'fire')
    ground(S, cx - hw - tw - u(4), cx + hw + tw + u(6), gy, kind='grass', foot=(cx - hw - tw, cx + hw + tw),
           paths=[(cx - gw // 2, cx + gw // 2 - 1)])


def turret(S, lay, cx, ytop, ybot, r, R=STONE, roof=SLATE, seed=0):
    """A small round turret (bartizan) hung on a corner: cylinder-shaded stone, a corbel cone under it, a
    pointed slate cap. Draws into lay, returns pixels."""
    m = set()
    for y in range(ytop, ybot):
        for x in range(cx - r, cx + r):
            m.add((x, y))
            t = cyl_tone((x + 0.5 - cx) / r)
            if (ybot - 1 - y) % S.kv(3, 4) == S.kv(2, 3):
                t = max(SH, t - 1)
            lay[(x, y)] = R[t]
    for j in range(r):                                    # corbel cone
        for x in range(cx - r + j + 1, cx + r - j - 1):
            lay[(x, ybot + j)] = R[cyl_tone((x + 0.5 - cx) / r) - (1 if j % 2 else 0)]
            m.add((x, ybot + j))
    ch = int(r * S.kv(2.2, 2.0)) + 2
    for j in range(ch):
        hw_ = (r + 1) * (j + 1) / ch
        y = ytop - ch + j
        for x in range(int(round(cx - hw_)), int(round(cx + hw_))):
            t = LT if x < cx - 1 else BS if x < cx + 1 else DK
            if j == ch - 1:
                t = DK
            lay[(x, y)] = roof[t]
            m.add((x, y))
    return m


def castle_keep(S, cx, gy):
    """Castle keep: a massive square stone keep with a plinth, lancet windows, a big arched door up a flight
    of steps, merlons, round turrets with slate cones hung on the upper corners, a central flag turret and
    red banners."""
    k, u = S.k, S.u
    hw = u(_sz(S, 14, 17, 20))
    H = u(_sz(S, 36, 42, 48))
    x0, x1 = cx - hw, cx + hw - 1
    yt = gy - H
    lay = S.lay('walls', 0)
    m = rect(x0, yt, x1, gy - 1)
    ashlar(S, lay, m, STONE, y0=gy, x0=x0, bw=S.kv(8, 12), bh=S.kv(3, 5), seed=33, moss=0.03 if k == 2 else 0)
    quoins(S, lay, x0, x1, yt, gy - 1, STONE)
    pm = rect(x0 - 1, gy - S.kv(4, 7), x1 + 1, gy - 1)
    for (x, y) in pm:
        lay[(x, y)] = DEEP[LT] if y == gy - S.kv(4, 7) else DEEP[BS] if (x + y) % 7 else DEEP[DK]
    cm = rect(x0 - S.kv(1, 2), yt - S.kv(2, 3), x1 + S.kv(1, 2), yt - 1)
    for (x, y) in cm:
        lay[(x, y)] = STONE[LT] if y == yt - S.kv(2, 3) else STONE[BS] if (x - x0) % S.kv(3, 4) else STONE[DK]
    mm = battlements(S, lay, x0 - S.kv(1, 2), x1 + S.kv(1, 2), yt - S.kv(2, 3), STONE)
    outline(lay, m | pm | cm | mm, STONE)
    # flag turret in the middle, behind the merlons
    ft = S.lay('flag_turret', -1)
    fr = S.kv(4, 7)
    fm = turret(S, ft, cx, yt - u(10), yt - S.kv(3, 4), fr, STONE, SLATE)
    outline(ft, fm, STONE)
    fl = S.lay('flag', -2)
    fy = yt - u(10) - int(fr * S.kv(2.2, 2.0)) - u(9)
    for y in range(fy, yt - u(10) - int(fr * S.kv(2.2, 2.0)) + 1):
        fl[(cx - 1, y)] = DARK_OAK[LT]
    fmask = set()
    for i in range(u(7)):
        for j in range(S.kv(4, 7) - (i * S.kv(4, 7)) // (u(7) * 2)):
            wave = int(round(math.sin(i * 0.7) * S.kv(0.5, 1)))
            p = (cx + i, fy + 1 + j + wave)
            fl[p] = BLUE_CLOTH[LT if j == 0 else BS]
            fmask.add(p)
    outline(fl, fmask | {(cx - 1, y) for y in range(fy, fy + u(9))}, BLUE_CLOTH)
    # corner turrets
    tl = S.lay('turrets', 3, cast=(u(1), u(1), 1))
    tr_ = S.kv(4, 7)
    tm = set()
    for xc in (x0, x1 + 1):
        tm |= turret(S, tl, xc, yt - u(4), yt + u(8), tr_, STONE, SLATE, seed=xc)
    outline(tl, tm, STONE)
    # windows, door, steps, banners
    for (wx, wy) in ((x0 + u(7), yt + u(9)), (x1 - u(7) - S.kv(4, 7) + 1, yt + u(9)), (cx - S.kv(2, 3), yt + u(5))):
        window(S, wx, wy, S.kv(4, 7), S.kv(8, 13), frame=DEEP, style='lancet', sill=STONE)
    dw, dh = S.kv(8, 14), S.kv(12, 20)
    sh = S.kv(3, 5)
    door(S, cx - dw // 2, gy - sh - dh, dw, dh, SPRUCE, DEEP, style='arch', handle=IRON)
    st = S.lay('steps', 4)
    stm = set()
    for i in range(sh // S.kv(1, 2)):
        yy = gy - sh + i * S.kv(1, 2)
        w2 = dw // 2 + 1 + i * S.kv(1, 2)
        for x in range(cx - w2, cx + w2):
            for j in range(S.kv(1, 2)):
                st[(x, yy + j)] = STONE[LT if j == 0 else DK]
                stm.add((x, yy + j))
    outline(st, stm, STONE)
    for side in (-1, 1):
        banner(S, cx - dw // 2 - u(4) - S.kv(4, 6) if side < 0 else cx + dw // 2 + u(4), gy - sh - dh - u(2),
               S.kv(4, 6), u(12))
    if S.night:
        S.light(cx, gy - sh - dh // 2, u(9))
    ground(S, x0 - u(6), x1 + u(9), gy, foot=(x0 - 1, x1 + 1), paths=[(cx - dw // 2 - 1, cx + dw // 2)])


# ------------------------------------------------------------------ chapel, tavern, stall
def bell(S, lay, cx, y, w, R=GOLDR):
    """A bell: flared bronze-gold body lit like a dome (left lit, right dark), a lip, a clapper, a crown loop."""
    k = S.k
    h = w + S.kv(0, 1)
    m = set()
    for j in range(h):
        hw_ = w / 2 * (0.55 + 0.45 * (j / max(1, h - 1)) ** 2) + (0.5 if j == h - 1 else 0)
        for x in range(int(round(cx - hw_)), int(round(cx + hw_))):
            nx = (x + 0.5 - cx) / max(1, hw_)
            t = HI if nx < -0.55 and j < h - 1 else LT if nx < -0.1 else BS if nx < 0.45 else DK
            if j == h - 1:
                t = DK if nx < 0.3 else SH
            lay[(x, y + j)] = R[t]
            m.add((x, y + j))
    lay[(int(cx) - (1 if k == 2 else 0), y + h)] = DARK_IRON[BS]
    m.add((int(cx) - (1 if k == 2 else 0), y + h))
    for x in range(int(cx) - S.kv(1, 1), int(cx) + S.kv(0, 1)):
        lay[(x, y - 1)] = R[DK]
        m.add((x, y - 1))
    return m


def rose_window(S, cx, cy, r, name='windows'):
    """A round stained-glass window: a stone ring, glass in coloured wedges (red, blue, gold, green) round a
    gold centre, lead lines between them; lit warm at night."""
    lay = S.lay(name, 4, cast=(S.u(1), S.u(1), 1))
    outer = disc(cx, cy, r)
    glass = _erode(outer, S.kv(1, 2))
    cols_ = (CLOTH, BLUE_CLOTH, DANDELION, GREEN_PAINT)
    for (x, y) in outer - glass:
        lay[(x, y)] = STONE[LT] if (x + 0.5 - cx) + (y + 0.5 - cy) < 0 else STONE[DK]
    for (x, y) in glass:
        dx, dy = x + 0.5 - cx, y + 0.5 - cy
        d = math.hypot(dx, dy)
        a = (math.atan2(dy, dx) + math.pi) / (2 * math.pi)
        seg = int(a * 8)
        lead = abs(a * 8 - round(a * 8)) * d < 0.45
        if d < r * 0.32:
            c = GOLDR[HI if dx + dy < 0 else LT]
        elif lead:
            c = DARK_IRON[DK]
        else:
            R = cols_[seg % 4]
            t = LT if (dx + dy) < 0 else BS
            if S.night:
                t = HI if d < r * 0.6 else LT
            c = R[t]
        lay[(x, y)] = c
    outline(lay, outer, STONE)
    if S.night:
        S.light(cx, cy, r + S.u(3))
    return outer


def chapel(S, cx, gy):
    """Chapel: a whitewashed nave with a front gable and stone quoins, a slate roof with a stone trim, a
    stained-glass rose window, lancet windows, an arched double door up a step, and a bell tower rising
    from the gable: an open belfry with a gold bell and a steep slate spire with a gold cross."""
    k, u = S.k, S.u
    hw = u(_sz(S, 12, 15, 18))
    x0, x1 = cx - hw, cx + hw - 1
    yf = gy - S.kv(2, 4)
    yw = yf - u(_sz(S, 16, 18, 20))
    foundation(S, x0, x1, yf, gy - 1, STONE, kind='ashlar', proud=1)
    lay = S.lay('walls', 0)
    m = rect(x0, yw, x1, yf - 1)
    plaster(S, lay, m, WHITEWASH, seed=41, patches=False)
    quoins(S, lay, x0, x1, yw, yf - 1, STONE)
    outline(lay, m, WHITEWASH, dark=STONE[O])
    half = hw + u(2)
    thick = S.kv(4, 7)
    _, inner, top = gable_roof(S, cx, yw + S.kv(0, 1), half, thick, SLATE, style='slate', trim=STONE, seed=42)
    gl = S.lay('gable', 1)
    gm = {(x, y) for x in range(x0, x1 + 1) for y in range(inner(x) - 1, yw)}
    plaster(S, gl, gm, WHITEWASH, seed=43, patches=False)
    for x in range(x0, x1 + 1):
        if (x, inner(x) - 1) in gm:
            gl[(x, inner(x) - 1)] = WHITEWASH[DK]
    outline(gl, gm, WHITEWASH)
    rr = S.kv(4, 7)
    rose_window(S, cx, yw - S.kv(3, 5) - rr + S.kv(4, 6), rr)
    lw, lh = S.kv(4, 6), S.kv(9, 15)
    for side in (-1, 1):
        wx = x0 + u(4) if side < 0 else x1 - u(4) - lw + 1
        window(S, wx, yw + u(4), lw, lh, frame=STONE, style='lancet', sill=STONE)
    dw, dh = S.kv(8, 14), S.kv(11, 19)
    door(S, cx - dw // 2, yf - dh, dw, dh, SPRUCE, STONE, style='double')
    step(S, cx - dw // 2 - 1, cx + dw // 2, yf, yf + S.kv(1, 2) - 1, STONE)
    # bell tower out of the gable apex
    apex = top(cx)
    tl = S.lay('belfry', -1, cast=(u(1), u(1), 1))
    bw = S.kv(5, 9)
    bh_ = u(12)
    by1 = apex + u(2)
    by0 = by1 - bh_
    tm = rect(cx - bw, by0, cx + bw - 1, by1)
    plaster(S, tl, tm, WHITEWASH, seed=44, patches=False)
    for y in range(by0, by1 + 1):
        tl[(cx - bw, y)] = STONE[LT]
        tl[(cx + bw - 1, y)] = STONE[DK]
    op = _shape('arch', cx - bw + S.kv(2, 3), by0 + S.kv(2, 3), 2 * bw - 2 * S.kv(2, 3), bh_ - S.kv(5, 9))
    for p in op:
        tl[p] = DEEP[O] if p[1] > min(q[1] for q in op) + S.kv(0, 1) else DEEP[SH]
    bell(S, tl, cx, min(q[1] for q in op) + S.kv(1, 2), S.kv(4, 6))
    sill_y = by0 + bh_ - S.kv(3, 5)
    for x in range(cx - bw - 1, cx + bw + 1):
        tl[(x, sill_y)] = STONE[LT]
        if k == 2:
            tl[(x, sill_y + 1)] = STONE[DK]
    outline(tl, tm | rect(cx - bw - 1, sill_y, cx + bw, sill_y + S.kv(0, 1)), WHITEWASH, dark=STONE[O])
    S.ledge(cx - bw - 1, cx + bw, sill_y)
    _, _, stop_ = gable_roof(S, cx, by0 + S.kv(0, 1), bw + S.kv(1, 2), S.kv(3, 5), SLATE, slope=(1, 3), style='slate',
                             name='spire', z=0, seed=45, solid=True)
    sp_apex = stop_(cx)
    cr = S.lay('cross', 1)
    cy0 = sp_apex - S.kv(6, 11)
    crm = rect(cx - 1, cy0, cx - 1 + S.kv(0, 1), sp_apex - 1) | rect(cx - S.kv(2, 4), cy0 + S.kv(2, 3),
                                                                      cx + S.kv(1, 3) - (1 if k == 1 else 0),
                                                                      cy0 + S.kv(2, 4))
    for (x, y) in crm:
        cr[(x, y)] = GOLDR[LT if x < cx or y == cy0 else DK]
    outline(cr, crm, GOLDR)
    if S.night:
        S.light(cx, gy + u(1.5), u(6))
    ground(S, x0 - u(6), x1 + u(9), gy, foot=(x0 - 1, x1 + 1), paths=[(cx - dw // 2, cx + dw // 2 - 1)])


def tavern(S, cx, gy):
    """Tavern: a cobblestone ground floor with big warm windows, a jettied timber-framed plaster upper floor
    (joist ends under the overhang, posts, rails and braces), a steep front gable with shingles, a hanging
    sign with a mug, barrels and a lantern by the door."""
    k, u = S.k, S.u
    hw = u(_sz(S, 13, 16, 19))
    x0, x1 = cx - hw, cx + hw - 1
    y1 = gy - u(12)
    jet = S.kv(2, 3)
    y2 = y1 - u(13)
    lay = S.lay('walls', 0)
    m1 = rect(x0, y1, x1, gy - 1)
    stones(S, lay, m1, COBBLE, seed=51)
    outline(lay, m1, COBBLE)
    up = S.lay('upper', 2, cast=(u(1), u(2), 1))
    m2 = rect(x0 - jet, y2, x1 + jet, y1 - 1)
    plaster(S, up, m2, PLASTER, seed=52, patches=False)
    bw = S.kv(1, 2)
    posts = [x0 - jet, x0 - jet + (x1 - x0 + 2 * jet) // 3, x0 - jet + 2 * (x1 - x0 + 2 * jet) // 3, x1 + jet - bw + 1]
    for x in posts:
        for y in range(y2, y1):
            for i in range(bw):
                up[(x + i, y)] = DARK_OAK[LT if i == 0 else DK]
    for y in (y2, y1 - bw, (y2 + y1) // 2):
        for x in range(x0 - jet, x1 + jet + 1):
            for i in range(bw):
                up[(x, y + i)] = DARK_OAK[LT if i == 0 else DK]
    if k == 2:
        for a, b in zip(posts[:-1], posts[1:]):
            n = (y1 + y2) // 2 - (y2 + bw)
            for j in range(n):
                x = a + bw + (j * (b - a - bw)) // n
                for i in range(bw):
                    up[(x + i, y2 + bw + j)] = DARK_OAK[BS if i == 0 else DK]
    for x in range(x0 - jet, x1 + jet + 1, S.kv(3, 5)):     # joist ends under the jetty
        for i in range(S.kv(1, 2)):
            up[(x + i, y1)] = DARK_OAK[LT if i == 0 else DK]
            m2.add((x + i, y1))
    outline(up, m2, DARK_OAK)
    S.ledge(x0 - jet, x1 + jet, y1)
    half = hw + jet + u(3)
    _, inner, top = gable_roof(S, cx, y2 + S.kv(0, 1), half, S.kv(4, 8), SHINGLE, slope=(1, 1),
                               trim=DARK_OAK, seed=53)
    gl = S.lay('gable', 1)
    gm = {(x, y) for x in range(x0 - jet, x1 + jet + 1) for y in range(inner(x) - 1, y2)}
    plaster(S, gl, gm, PLASTER, seed=54, patches=False)
    for (x, y) in gm:
        if x == cx - 1 or x == cx or y == inner(x) - 1:
            gl[(x, y)] = DARK_OAK[LT if x < cx else DK] if y != inner(x) - 1 else PLASTER[DK]
    outline(gl, gm, PLASTER)
    gw_, gh_ = S.kv(4, 7), S.kv(5, 9)
    for gx in (cx - u(4) - gw_, cx + u(4)):
        window(S, gx, y2 - u(3) - gh_, gw_, gh_, frame=DARK_OAK, style='single' if k == 1 else 'cross', sill=None)
    ww = S.kv(6, 10)
    for wx in spread(x0 + u(1), x1 - u(1), 3, ww):
        window(S, wx, y2 + S.kv(3, 5), ww, S.kv(5, 11), frame=DARK_OAK, style='cross' if k == 1 else 'grid',
               box=(k == 2), seed=wx)
    dw, dh = S.kv(6, 11), S.kv(9, 17)
    dx = x0 + u(4)
    door(S, dx, gy - dh, dw, dh, OAK, DARK_OAK)
    big = S.kv(9, 16)
    window(S, x1 - u(4) - big, y1 + S.kv(3, 5), big, S.kv(6, 10), frame=DARK_OAK, style='cross' if k == 1 else 'grid',
           sill=OAK)
    hanging_sign(S, x0 - jet, y1 + S.kv(1, 2), side=-1, icon='mug')
    lantern(S, dx + dw + S.kv(0, 1), gy - dh + S.kv(1, 2), side=1, arm=S.kv(2, 3))
    barrel(S, x1 + u(2), gy - 1)
    if S.size != 's':
        barrel(S, x1 + u(2) + S.kv(6, 10), gy - 1)
    if S.night:
        S.light(dx + dw / 2, gy + u(1.5), u(6))
    ground(S, x0 - u(14), x1 + u(19), gy, foot=(x0 - jet, x1 + jet), paths=[(dx, dx + dw - 1)])


def market_stall(S, cx, gy):
    """Market stall: two posts under a striped awning with a scalloped edge, a shaded back wall, a plank
    counter with crates of apples, carrots and bread, a coin sign hanging from the awning, a lantern on a
    post and sacks; a cobble plaza."""
    k, u = S.k, S.u
    hw = u(_sz(S, 12, 15, 18))
    x0, x1 = cx - hw, cx + hw - 1
    ya = gy - u(27)
    bl = S.lay('back', 0)
    bm = rect(x0 + S.kv(1, 2), ya + u(2), x1 - S.kv(1, 2), gy - u(8))
    planks(S, bl, bm, SPRUCE, y0=gy, seed=61)
    for (x, y) in bm:
        if y < ya + u(6):
            bl[(x, y)] = darker(bl[(x, y)], 2)              # the awning's shade
    outline(bl, bm, SPRUCE)
    pl = S.lay('posts', 2, cast=(u(1), 0, 1))
    pm = set()
    pw = S.kv(2, 3)
    for xa in (x0, x1 - pw + 1):
        pm |= log_v(S, pl, xa, xa + pw - 1, ya, gy - 1, SPRUCE_LOG)
    outline(pl, pm, SPRUCE_LOG)
    cl = S.lay('counter', 3, cast=(u(1), 0, 1))
    cy = gy - u(9)
    cm = rect(x0 + pw, cy, x1 - pw, gy - 1)
    planks(S, cl, cm, OAK, vertical=True, x0=x0, seed=62, board=S.kv(4, 6))
    for x in range(x0 + pw - 1, x1 - pw + 2):
        cl[(x, cy)] = OAK[HI if k == 2 and x < cx else LT]
        if k == 2:
            cl[(x, cy + 1)] = OAK[DK]
            cm.add((x, cy + 1))
        cm.add((x, cy))
    outline(cl, cm, OAK)
    goods = (POPPY, CARROT, HAY)
    cw = (x1 - x0 - 2 * pw - S.kv(4, 6)) // 3
    for i, R in enumerate(goods):
        crate(S, x0 + pw + S.kv(1, 2) + i * (cw + S.kv(1, 1)), cy - 1, w=cw, R=OAK if i % 2 else SPRUCE, fill=R)
    awning(S, x0 - S.kv(1, 2), x1 + S.kv(1, 2), ya - S.kv(2, 3), depth=S.kv(5, 9), R1=CLOTH, R2=CANVAS,
           stripe=S.kv(3, 5))
    sg = S.lay('sign', 6, cast=(u(1), u(1), 1))
    sw_, sh_ = S.kv(7, 13), S.kv(5, 9)
    sx, sy = cx - sw_ // 2, ya + S.kv(5, 10) - S.kv(0, 1)
    smk = rect(sx, sy, sx + sw_ - 1, sy + sh_ - 1)
    for (x, y) in smk:
        sg[(x, y)] = OAK[LT] if (y == sy or x == sx) else OAK[DK] if (y == sy + sh_ - 1 or x == sx + sw_ - 1) else OAK[BS]
    for x in (sx + 1, sx + sw_ - 2):
        for y in range(ya + S.kv(3, 6), sy):
            sg[(x, y)] = ROPE[BS]
    rows = SIGN_ICONS['coin'][k - 1]
    ix, iy = sx + (sw_ - len(rows[0])) // 2, sy + (sh_ - len(rows)) // 2
    for j, row in enumerate(rows):
        for i, ch_ in enumerate(row):
            if ch_ in _ICON_COL:
                r_, t_ = _ICON_COL[ch_]
                sg[(ix + i, iy + j)] = r_[t_]
    outline(sg, smk, OAK)
    lp = S.lay('lamp_post', 4, cast=(u(1), 0, 1))
    lx = x1 + u(5)
    lpm = rect(lx, gy - u(18), lx + S.kv(0, 1), gy - 1)
    for (x, y) in lpm:
        lp[(x, y)] = DARK_IRON[LT if x == lx else DK]
    outline(lp, lpm, DARK_IRON)
    lantern(S, lx + S.kv(0, 0), gy - u(18) - S.kv(4, 7), post=True)
    sk = S.lay('sacks', 5, cast=(u(1), 0, 1))
    skm = set()
    sxx = x0 - u(5)
    pts = {(x, y) for (x, y) in disc(sxx, gy - S.kv(2, 3.5), S.kv(2.4, 4.0), S.kv(2.5, 3.8)) if y < gy}
    for (x, y) in pts:
        sk[(x, y)] = CANVAS[dome_tone((x + 0.5 - sxx) / S.kv(2.4, 4.0), (y + 0.5 - gy + S.kv(2, 3.5)) / S.kv(2.5, 3.8))]
    skm |= pts
    for (x, y) in pts:
        if y == min(q[1] for q in pts):
            sk[(x, y - 1)] = HAY[LT]
            skm.add((x, y - 1))
    outline(sk, skm, CANVAS)
    ground(S, x0 - u(9), x1 + u(9), gy, kind='stone', foot=(x0, x1), paths=())


# ------------------------------------------------------------------ towers with a light
def tapered(S, cx, yt, gy, rt, rb):
    """Pixels of a tapering round body and its half width per row."""
    m, hw = set(), {}
    H = gy - yt
    for y in range(yt, gy):
        h = rt + (rb - rt) * (y - yt) / H
        hw[y] = h
        m |= {(x, y) for x in range(int(round(cx - h)), int(round(cx + h)))}
    return m, hw


def lighthouse(S, cx, gy):
    """Lighthouse: a tapering tower in red and white bands (cylinder-shaded), small windows climbing it, an
    arched door, an iron gallery with a railing, a glazed lantern room with the lamp, a red dome with a
    finial; rocks round the foot. At night the lamp throws two beams."""
    k, u = S.k, S.u
    H = u(_sz(S, 36, 44, 52))
    rb, rt = u(9), u(6)
    yt = gy - H
    lay = S.lay('walls', 0)
    m, hw = tapered(S, cx, yt, gy, rt, rb)
    band = u(7)
    for (x, y) in m:
        R = RED_PAINT if ((gy - 1 - y) // band) % 2 == 1 else WHITEWASH
        t = cyl_tone((x + 0.5 - cx) / hw[y])
        if (gy - 1 - y) % band == band - 1 and k == 2:
            t = max(SH, t - 1)
        lay[(x, y)] = R[t]
    outline(lay, m, WHITEWASH, dark=RED_PAINT[O])
    for i, wy in enumerate(range(yt + u(6), gy - u(14), u(9))):
        window(S, cx - S.kv(1, 2) + (u(2) if i % 2 else -u(2)), wy, S.kv(2, 4), S.kv(3, 6), frame=DARK_IRON,
               style='single' if k == 2 else 'dark', sill=None)
    dw, dh = S.kv(5, 9), S.kv(8, 14)
    door(S, cx - dw // 2, gy - dh, dw, dh, SPRUCE, DARK_IRON, style='arch')
    # gallery + railing
    gl = S.lay('gallery', 2, cast=(u(1), u(1), 1))
    gw = rt + u(3)
    gm = rect(cx - gw, yt - S.kv(1, 2), cx + gw - 1, yt - 1)
    for (x, y) in gm:
        gl[(x, y)] = DARK_IRON[LT] if y == yt - S.kv(1, 2) else DARK_IRON[DK]
    for i in range(S.kv(1, 2)):
        for x in range(cx - gw + 1 + i, cx + gw - 1 - i):
            gl[(x, yt + i)] = DARK_IRON[SH]
            gm.add((x, yt + i))
    rh = S.kv(4, 6)
    for x in range(cx - gw, cx + gw):
        gl[(x, yt - S.kv(1, 2) - rh)] = DARK_IRON[LT]
        gm.add((x, yt - S.kv(1, 2) - rh))
        if (x - cx) % S.kv(2, 3) == 0:
            for y in range(yt - S.kv(1, 2) - rh + 1, yt - S.kv(1, 2)):
                gl[(x, y)] = DARK_IRON[BS]
                gm.add((x, y))
    outline(gl, gm, DARK_IRON)
    S.ledge(cx - gw, cx + gw - 1, yt - S.kv(1, 2))
    # lantern room
    ll = S.lay('lantern_room', 1)
    lw = rt - u(1)
    lh = u(8)
    ly0 = yt - S.kv(1, 2) - lh
    lm = rect(cx - lw, ly0, cx + lw - 1, yt - S.kv(1, 2) - 1)
    G = GLOW if S.night else GLASS
    for (x, y) in lm:
        mull = (x - (cx - lw)) % S.kv(3, 4) == 0 or x == cx + lw - 1
        if mull:
            ll[(x, y)] = DARK_IRON[LT if x < cx else DK]
        else:
            ll[(x, y)] = G[SH if y == ly0 else BS] if not S.night else G[LT if y == ly0 else HI]
    lc = (cx - 0.5, ly0 + lh / 2)
    for (x, y) in disc(lc[0] + 0.5, lc[1], S.kv(1.5, 2.6)):
        if (x, y) in lm and ll[(x, y)] not in (DARK_IRON[LT], DARK_IRON[DK]):
            ll[(x, y)] = GLOW[HI] if S.night else GLOW[LT]
    outline(ll, lm, DARK_IRON)
    # dome and finial
    dl = S.lay('roof', 3, cast=(u(1), u(1), 1), roof=True)
    dr, dry = lw + S.kv(1, 2), u(5)
    dm = dome_mask(cx, ly0, dr, dry)
    for (x, y) in dm:
        dl[(x, y)] = RED_PAINT[dome_tone((x + 0.5 - cx) / dr, (y + 0.5 - ly0) / dry)]
    fy = ly0 - dry
    fm = rect(cx - 1, fy - S.kv(3, 5), cx - 1 + S.kv(0, 1), fy - 1)
    for (x, y) in fm:
        dl[(x, y)] = DARK_IRON[LT if x == cx - 1 else DK]
    ball = disc(cx - 0.5 + S.kv(0, 0.5), fy - S.kv(3, 5) - S.kv(1, 1.5), S.kv(1.0, 1.6))
    for (x, y) in ball:
        dl[(x, y)] = GOLDR[LT if x < cx - 1 + S.kv(0, 1) else DK]
    outline(dl, dm | fm | ball, RED_PAINT)
    S.field(dm)
    if S.night:
        bl = S.lay('light_beams', 9, snow=False)
        L = u(_sz(S, 16, 20, 24))
        y0 = int(lc[1])
        for side in (-1, 1):
            for i in range(lw + 1, lw + L):
                hh = 1 + (i - lw) * 0.32
                x = int(cx - 1 - i) if side < 0 else int(cx + i)
                for y in range(int(round(y0 - hh)), int(round(y0 + hh)) + 1):
                    core = abs(y + 0.5 - y0) < hh * 0.38
                    bl[(x, y)] = GLOW[HI] if core else GLOW[LT]
        S.light(lc[0], lc[1], u(12))
        S.light(cx, gy + u(1.5), u(6))
    # rocks at the foot
    rk = S.lay('rocks', 5, cast=(u(1), 0, 1))
    rkm = set()
    for (rx, rr) in ((cx - rb - u(3), u(3.2)), (cx + rb + u(2), u(4)), (cx + rb + u(7), u(2.4))):
        pts = {(x, y) for (x, y) in disc(rx, gy, rr, rr * 0.8) if y < gy + S.kv(1, 2)}
        for (x, y) in pts:
            rk[(x, y)] = DEEP[dome_tone((x + 0.5 - rx) / rr, (y + 0.5 - gy) / (rr * 0.8))]
        rkm |= pts
    outline(rk, rkm, DEEP)
    ground(S, cx - rb - u(9), cx + rb + u(12), gy, kind='stone', foot=(cx - rb, cx + rb), paths=[(cx - dw // 2, cx + dw // 2 - 1)])


# ------------------------------------------------------------------ workshops and farms
def anvil(S, lay, x, yb):
    """An anvil on a log stump: dark iron, a lit top face and horn, the stump with an end-grain top."""
    k = S.k
    m = set()
    sw, shh = S.kv(4, 7), S.kv(3, 6)
    for (px, py) in rect(x, yb - shh + 1, x + sw - 1, yb):
        t = LT if px == x else DK if px == x + sw - 1 else BS
        lay[(px, py)] = OAK_LOG[t] if py > yb - shh + 1 else LOG_END[LT]
        m.add((px, py))
    rows = ('.hhhhhh.', 'HAAAAAAa', '..AAAA..', '..aaaa..', '.aaaaaa.') if k == 1 else \
        ('.HHHHHHHHHHH.', 'hAAAAAAAAAAAa', '.aAAAAAAAAAa.', '...AAAAAAa...', '...aAAAAAa...', '...aaaaaaa...',
         '..aaaaaaaaa..', '.aaaaaaaaaaa.')
    ax = x + sw // 2 - len(rows[0]) // 2
    ay = yb - shh - len(rows) + 1
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch == '.':
                continue
            c = {'H': IRON[HI], 'h': IRON[LT], 'A': DARK_IRON[LT] if i < len(row) // 3 else DARK_IRON[BS],
                 'a': DARK_IRON[DK]}[ch]
            lay[(ax + i, ay + j)] = c
            m.add((ax + i, ay + j))
    return m


def forge(S, cx, gy):
    """Blacksmith's forge: an open workshop under a lean-to shingle roof on two log posts, a dark stone back
    wall with tools hanging on it, a brick forge with a glowing mouth (fire, emissive) and a chimney with
    smoke through the roof, an anvil on a stump, a quench barrel, an anvil sign; firelight at night."""
    k, u = S.k, S.u
    hw = u(_sz(S, 14, 17, 20))
    x0, x1 = cx - hw, cx + hw - 1
    H = u(17)
    yt = gy - H
    bl = S.lay('back', 0)
    bm = rect(x0, yt, x1, gy - 1)
    stones(S, bl, bm, COBBLE, seed=71)
    for (x, y) in bm:
        bl[(x, y)] = darker(bl[(x, y)], 2 if y < yt + u(5) else 1)        # in the shade of the roof
    outline(bl, bm, COBBLE)
    tl = S.lay('tools', 1)
    tm = set()
    for i, tx in enumerate(range(x0 + u(14), x1 - u(4), S.kv(4, 6))):
        ty = yt + u(6)
        for j in range(S.kv(4, 7)):
            tl[(tx, ty + j)] = OAK[BS]
            tm.add((tx, ty + j))
        head = [(tx - 1, ty), (tx, ty), (tx + 1, ty)] if i % 2 == 0 else [(tx - 1, ty + S.kv(4, 7)), (tx + 1, ty + S.kv(4, 7))]
        if k == 2:
            head += [(tx - 1, ty + 1), (tx, ty - 1), (tx + 1, ty + 1)] if i % 2 == 0 else [(tx - 1, ty + 8), (tx + 1, ty + 8)]
        for p in head:
            tl[p] = IRON[LT] if p[0] < tx else IRON[DK]
            tm.add(p)
    outline(tl, tm, DARK_IRON)
    # the forge: brick block with an arched mouth
    fl = S.lay('furnace', 2, cast=(u(1), 0, 1))
    fw, fh = u(12), u(10)
    fx0 = x0 + u(1)
    fm = rect(fx0, gy - fh, fx0 + fw - 1, gy - 1)
    bricks(S, fl, fm, BRICK, MORTAR, y0=gy, x0=fx0, seed=72)
    for x in range(fx0, fx0 + fw):
        fl[(x, gy - fh)] = STONE[LT]
        fl[(x, gy - fh + S.kv(0, 1))] = STONE[LT if k == 1 else DK]
    mouth = _shape('arch', fx0 + u(3), gy - u(7), u(6), u(6))
    mx0, my0, mx1, my1 = bbox(mouth)
    for (x, y) in mouth:
        d = (y - my0) / max(1, my1 - my0)
        fl[(x, y)] = FIRE[HI] if d > 0.65 and abs(x + 0.5 - (mx0 + mx1 + 1) / 2) < (mx1 - mx0) * 0.3 else \
            FIRE[LT] if d > 0.4 else FIRE[BS] if d > 0.2 else FIRE[DK]
    for (x, y) in edge_ring(mouth):
        if y < gy and (x, y) in fm:
            fl[(x, y)] = BRICK[SH]
    outline(fl, fm, BRICK)
    # chimney rising from the forge through the roof
    chimney(S, fx0 + u(3), S.kv(5, 8), yt - u(9), gy - fh - 1, BRICK, z=1, seed=73)
    # lean-to roof on two posts
    pl = S.lay('posts', 3, cast=(u(1), 0, 1))
    pmk = set()
    pw = S.kv(2, 3)
    for xa in (x0 - u(1), x1 - pw + 1 + u(1)):
        pmk |= log_v(S, pl, xa, xa + pw - 1, yt + u(1), gy - 1, OAK_LOG)
    outline(pl, pmk, OAK_LOG)
    hip_roof(S, x0 - u(3), x1 + u(3), yt + S.kv(1, 2), u(6), SHINGLE, style='wood', slope=(2, 1), seed=74,
             fascia=DARK_OAK)
    # anvil, barrel, sign
    al = S.lay('anvil', 5, cast=(u(1), 0, 1))
    am = anvil(S, al, cx + u(2), gy + u(2))
    outline(al, am, DARK_IRON)
    barrel(S, x1 - u(7), gy + u(1))
    wl = S.lay('props')
    bx0 = x1 - u(7)
    for i in range(1, S.kv(4, 8) - 1):
        wl[(bx0 + i, gy + u(1) - S.kv(6, 11) + 1)] = WATER[LT if i < S.kv(2, 4) else BS]
    hanging_sign(S, x1 + u(1), yt + u(3), side=1, icon='anvil', R=SPRUCE)
    if S.night:
        S.light((mx0 + mx1) / 2, my1, u(16), 'fire')
    else:
        S.light((mx0 + mx1) / 2, my1, u(9), 'fire')
    ground(S, x0 - u(5), x1 + u(16), gy, kind='dirt', foot=(x0 - u(1), x1 + u(1)))


def gambrel_top(cx, eave_y, half, thick, d1):
    """Profile of a gambrel (barn) roof: a shallow upper pitch (2 across : 1 down) to d1 from the middle, a
    steep lower pitch (1 : 2) to the eaves."""
    lower = (half - 1 - d1) * 2
    apex = eave_y - (thick - 1) - lower - d1 // 2

    def f(x):
        d = x - cx if x >= cx else cx - 1 - x
        return apex + (d // 2 if d < d1 else d1 // 2 + (d - d1) * 2)
    return f


def barn(S, cx, gy):
    """Red barn and silo: vertical red planks with white corner boards, a gambrel roof (shallow upper and
    steep lower pitch) with a white trim, a hay loft door full of hay, big double doors with white X braces,
    a ribbed grey silo with a dome, hay bales; a weathervane at HD."""
    k, u = S.k, S.u
    hw = u(_sz(S, 13, 16, 19))
    x0, x1 = cx - hw, cx + hw - 1
    yw = gy - u(16)
    lay = S.lay('walls', 0)
    m = rect(x0, yw, x1, gy - 1)
    planks(S, lay, m, BARN_RED, vertical=True, x0=x0, seed=81, board=S.kv(3, 4))
    for y in range(yw, gy):
        for i in range(S.kv(1, 2)):
            lay[(x0 + i, y)] = CREAMR[LT if i == 0 else BS]
            lay[(x1 - i, y)] = CREAMR[DK if i == 0 else BS]
    outline(lay, m, BARN_RED)
    half = hw + u(2)
    thick = S.kv(3, 6)
    d1 = int(half * 0.55)
    topf = gambrel_top(cx, yw + S.kv(0, 1), half, thick, d1)
    _, inner, top = gable_roof(S, cx, yw + S.kv(0, 1), half, thick, SHINGLE, trim=CREAMR, seed=82, top_fn=topf)
    gl = S.lay('gable', 1)
    gm = {(x, y) for x in range(x0, x1 + 1) for y in range(inner(x) - 1, yw)}
    planks(S, gl, gm, BARN_RED, vertical=True, x0=x0, seed=83, board=S.kv(3, 4))
    outline(gl, gm, BARN_RED)
    # hay loft
    hl = S.lay('loft', 3, cast=(u(1), u(1), 1))
    lw, lhh = S.kv(6, 11), S.kv(6, 10)
    lx, ly = cx - lw // 2, inner(cx) + S.kv(2, 4)
    lm = rect(lx, ly, lx + lw - 1, ly + lhh - 1)
    rnd = S.rnd('hay')
    for (x, y) in lm:
        fr = x in (lx, lx + lw - 1) or y in (ly, ly + lhh - 1)
        if fr:
            hl[(x, y)] = CREAMR[LT if (x == lx or y == ly) else DK]
        else:
            hl[(x, y)] = HAY[SH] if y == ly + 1 else HAY[LT if rnd.random() < 0.3 else BS if rnd.random() < 0.7 else DK]
    for x in range(lx - 1, lx + lw + 1):                   # a hay tuft spilling over the sill and the beam
        hl[(x, ly + lhh)] = HAY[LT if x % 2 else BS]
        lm.add((x, ly + lhh))
    for y in range(ly - S.kv(3, 5), ly):
        hl[(cx - 1, y)] = DARK_OAK[LT]
        lm.add((cx - 1, y))
    outline(hl, lm, BARN_RED)
    # big doors with X braces
    dl = S.lay('door', 4, cast=(u(1), u(1), 1))
    dw, dh = u(14), u(12)
    dx = cx - dw // 2
    dm = rect(dx, gy - dh, dx + dw - 1, gy - 1)
    half_ = dw // 2
    bt = S.kv(1, 2)
    for (x, y) in dm:
        i, j = x - dx, y - (gy - dh)
        ii = i if i < half_ else i - half_
        on = ii < bt or ii >= half_ - bt or j < bt or j >= dh - bt
        diag = abs(ii - (j * (half_ - 1)) / (dh - 1)) < bt * 0.75 or abs((half_ - 1 - ii) - (j * (half_ - 1)) / (dh - 1)) < bt * 0.75
        if on or diag:
            dl[(x, y)] = CREAMR[LT if (ii < bt or j < bt) and not (ii >= half_ - bt) else BS if not diag else LT]
            if (ii >= half_ - bt or j >= dh - bt) and not (ii < bt):
                dl[(x, y)] = CREAMR[DK]
        else:
            dl[(x, y)] = BARN_RED[DK if (x - dx) % S.kv(3, 4) == 0 else BS]
    outline(dl, dm, BARN_RED)
    # silo
    sl = S.lay('silo', -1, cast=(u(2), 0, 1))
    sr = u(5)
    sxc = x1 + u(3) + sr
    sh = u(30)
    smk = rect(sxc - sr, gy - sh, sxc + sr - 1, gy - 1)
    for (x, y) in smk:
        t = cyl_tone((x + 0.5 - sxc) / sr)
        if (gy - 1 - y) % S.kv(4, 6) == 0:
            t = max(SH, t - 1)
        sl[(x, y)] = SILO_GREY[t]
    dmk = dome_mask(sxc, gy - sh, sr, sr * 0.8)
    for (x, y) in dmk:
        sl[(x, y)] = SILO_GREY[dome_tone((x + 0.5 - sxc) / sr, (y + 0.5 - gy + sh) / (sr * 0.8))]
    outline(sl, smk | dmk, SILO_GREY)
    S.field(dmk)
    # hay bales
    hb = S.lay('hay_bales', 5, cast=(u(1), 0, 1))
    hbm = set()
    for (bx, by) in ((x0 - u(8), gy - 1), (x0 - u(8) + S.kv(6, 11), gy - 1), (x0 - u(5), gy - 1 - S.kv(4, 7))):
        b = rect(bx, by - S.kv(4, 7) + 1, bx + S.kv(6, 11) - 1, by)
        for (x, y) in b:
            j = y - (by - S.kv(4, 7) + 1)
            t = LT if j == 0 else DK if j == S.kv(3, 6) else BS
            if (x - bx) in (S.kv(1, 2), S.kv(4, 8)):
                t = DK if j else BS                        # the twine bands
            hb[(x, y)] = HAY[t]
        hbm |= b
    outline(hb, hbm, HAY)
    if k == 2:                                             # weathervane: a little rooster on the apex
        wv = S.lay('vane', 4)
        ay = top(cx)
        wvm = set()
        for y in range(ay - 9, ay):
            wv[(cx - 1, y)] = DARK_IRON[BS]
            wvm.add((cx - 1, y))
        for (a, b) in ((-3, -12), (-2, -12), (-1, -12), (0, -12), (1, -12), (-2, -13), (-1, -13), (0, -13),
                       (1, -14), (1, -13), (2, -14), (-3, -11), (-4, -13)):
            wv[(cx + a, ay + b)] = DARK_IRON[LT if b < -12 else BS]
            wvm.add((cx + a, ay + b))
        outline(wv, wvm, DARK_IRON)
    ground(S, x0 - u(12), sxc + sr + u(6), gy, foot=(x0, sxc + sr), paths=[(dx + u(2), dx + dw - u(2) - 1)])


def well(S, cx, gy):
    """Well: a round cobblestone shaft (cylinder-shaded, a lit rim with dark water inside), two log posts, a
    small shingle roof, a crank with a rope and a bucket."""
    k, u = S.k, S.u
    R = u(_sz(S, 8, 9, 11))
    wh = u(8)
    lay = S.lay('shaft', 2)
    m = rect(cx - R, gy - wh, cx + R - 1, gy - 1)
    stones(S, lay, m, COBBLE, seed=91)
    for (x, y) in m:
        t = cyl_tone((x + 0.5 - cx) / R)
        if t <= DK:
            lay[(x, y)] = darker(lay[(x, y)], 1)
        elif t == HI and lay[(x, y)] == COBBLE[BS]:
            lay[(x, y)] = COBBLE[LT]
    ry = S.kv(2, 4)
    rim = {(x, y) for (x, y) in disc(cx, gy - wh, R + S.kv(0, 1), ry)}
    inside = {(x, y) for (x, y) in disc(cx, gy - wh, R - S.kv(1, 2), ry - S.kv(1, 1.5))}
    for (x, y) in rim:
        lay[(x, y)] = COBBLE[LT if (x + 0.5 - cx) < R * 0.3 else BS] if y < gy - wh else COBBLE[LT if x < cx else DK]
    for (x, y) in inside:
        lay[(x, y)] = WATER[SH] if y < gy - wh else WATER[DK]
        if y == gy - wh and x < cx - 1:
            lay[(x, y)] = WATER[BS]
    outline(lay, m | rim, COBBLE)
    pl = S.lay('posts', 1)
    pw = S.kv(2, 3)
    ph = u(20)
    pm = set()
    for xa in (cx - R + S.kv(0, 1), cx + R - pw - S.kv(0, 1)):
        pm |= log_v(S, pl, xa, xa + pw - 1, gy - wh - ph + u(8), gy - wh, SPRUCE_LOG)
    yc = gy - wh - u(6)
    for x in range(cx - R + pw, cx + R - pw):                # the crank axle
        pl[(x, yc)] = DARK_OAK[LT]
        if k == 2:
            pl[(x, yc + 1)] = DARK_OAK[DK]
        pm.add((x, yc))
    for j in range(S.kv(2, 3)):
        pl[(cx + R - pw + S.kv(1, 2), yc + j)] = DARK_IRON[BS]
        pm.add((cx + R - pw + S.kv(1, 2), yc + j))
    outline(pl, pm, SPRUCE_LOG)
    _, inner, top = gable_roof(S, cx, gy - wh - ph + u(8), R + u(3), S.kv(3, 6), SHINGLE, trim=DARK_OAK, seed=92,
                               slope=(1, 1), solid=True)
    rl = S.lay('rope', 4)
    rx = cx - S.kv(1, 2)
    for y in range(yc + 1, gy - wh - u(2)):
        rl[(rx, y)] = ROPE[BS if y % 2 else LT]
    bm = set()
    by = gy - wh - u(2)
    bw = S.kv(4, 6)
    for (x, y) in rect(rx - bw // 2, by, rx - bw // 2 + bw - 1, by + S.kv(3, 5)):
        rl[(x, y)] = OAK[LT if x == rx - bw // 2 else DK if x == rx - bw // 2 + bw - 1 else BS]
        if y == by + S.kv(1, 2):
            rl[(x, y)] = DARK_IRON[BS]
        bm.add((x, y))
    for x in range(rx - bw // 2 - 1, rx - bw // 2 + bw + 1):
        rl[(x, by - 1)] = DARK_IRON[LT] if abs(x - rx) > 1 else rl.get((x, by - 1), DARK_IRON[LT])
        bm.add((x, by - 1))
    outline(rl, bm, OAK)
    ground(S, cx - R - u(8), cx + R + u(10), gy, kind='grass', foot=(cx - R, cx + R - 1), paths=[(cx - u(3), cx + u(2))])


def campfire(S, x, yb, name='campfire'):
    """A campfire: a ring of stones, crossed logs, layered flames (fire ramp: a white-hot core, orange,
    red tips), sparks; firelight at night."""
    k, u = S.k, S.u
    lay = S.lay(name, 6)
    m = set()
    for i in range(-S.kv(4, 7), S.kv(4, 7) + 1, S.kv(2, 3)):
        for (a, b) in ((0, 0), (1, 0)) if k == 1 else ((0, 0), (1, 0), (0, -1), (1, -1)):
            lay[(x + i + a, yb + b)] = COBBLE[LT if b < 0 or k == 1 else BS]
            m.add((x + i + a, yb + b))
    for i in range(-S.kv(3, 6), S.kv(3, 6) + 1):
        y = yb - S.kv(1, 2) - abs(i) // 3
        lay[(x + i, y)] = OAK_LOG[LT if i < 0 else BS]
        m.add((x + i, y))
    fl = ('..H..', '.HLH.', 'HLBLH', 'LBDBL') if k == 1 else \
        ('....L....', '...LH.L..', '..LHHL.L.', '..LHHLL..', '.LHHHHL..', '.LHHHHHL.', 'LBHHHHLBL', 'BBLLLLBBB', '.DBBBBBD.')
    fy = yb - S.kv(1, 2) - len(fl)
    for j, row in enumerate(fl):
        for i, ch in enumerate(row):
            if ch != '.':
                lay[(x - len(row) // 2 + i, fy + j)] = FIRE[{'H': HI, 'L': LT, 'B': BS, 'D': DK}[ch]]
    if S.night:
        S.light(x, yb - S.kv(2, 4), u(16), 'fire')
    outline(lay, m, COBBLE)
    return m


def tent(S, cx, gy):
    """Camp: a canvas A-tent (seams, a lit left slope and a shaded right one, an open door flap with the
    dark inside, a flap tied back), a ridge pole, guy ropes to pegs, a campfire with a stone ring, a log seat
    and a bedroll."""
    u = S.u
    half = u(_sz(S, 10, 13, 16))
    tx = cx - u(8)
    lay = S.lay('tent', 2, cast=(u(2), 0, 1))
    apex = gy - half - u(2)
    top = gable_top(tx, apex, (1, 1))
    side = S.lay('tent_side', 1)                         # the right roof slope receding back-right: the
    dd = u(6)                                              # front's right edge swept by (s, -s/2)
    front_m = {(x, y) for x in range(tx - half, tx + half) for y in range(top(x), gy)}
    sm_ = set()
    for yy in range(apex, gy):
        for s_ in range(dd + 1):
            p_ = (tx + (yy - apex) + s_, yy - s_ // 2)
            if p_ not in front_m:
                sm_.add(p_)
    for (x, y) in sm_:
        side[(x, y)] = CANVAS[DK if (x + 2 * y) % S.kv(6, 10) else SH]
    for s_ in range(dd + 1):                               # the ridge pole along the top
        side[(tx + s_, apex - 1 - s_ // 2)] = OAK[LT if s_ % 2 else BS]
        sm_.add((tx + s_, apex - 1 - s_ // 2))
    outline(side, sm_, CANVAS)
    m = set()
    for x in range(tx - half, tx + half):
        for y in range(top(x), gy):
            m.add((x, y))
            left = x < tx
            d = abs(x + 0.5 - tx)
            t = LT if left else DK
            if d < S.kv(1, 2):
                t = HI if left else BS
            if (y - apex) % S.kv(5, 8) == 0 and y > apex + 1:
                t = max(SH, t - 1)                         # seams
            lay[(x, y)] = CANVAS[t]
    door_h = int(half * 0.85)
    dm = {(x, y) for (x, y) in m if y >= gy - door_h and abs(x + 0.5 - tx) < (y - (gy - door_h)) * 0.55 + 0.5}
    for (x, y) in dm:
        lay[(x, y)] = (GLOW[SH] if S.night else DARK_OAK[O]) if (x, y - 1) in dm else DARK_OAK[SH]
    for (x, y) in dm:                                      # the right flap tied back
        if x >= tx and abs(x + 0.5 - tx) > (y - (gy - door_h)) * 0.3 and y > gy - door_h * 0.6:
            lay[(x, y)] = CANVAS[BS if (x + y) % 3 else DK]
    rope_y = gy - door_h + S.kv(3, 5)
    lay[(tx + S.kv(2, 3), rope_y)] = ROPE[LT]
    outline(lay, m, CANVAS)
    pl = S.lay('pole', 3)
    for i in range(S.kv(2, 3)):
        pl[(tx - 1, apex - 1 - i)] = OAK[LT]
        pl[(tx, apex - 1 - i)] = OAK[DK]
    rl = S.lay('ropes', 1)
    for side in (-1, 1):
        sx0 = tx - half if side < 0 else tx + half - 1
        for i in range(1, u(6)):
            x = sx0 + side * i
            y = top(sx0) + u(2) + i
            if y < gy:
                rl[(x, y)] = ROPE[DK]
        px = sx0 + side * u(6)
        for j in range(S.kv(2, 3)):
            rl[(px, gy - 1 - j + S.kv(1, 1))] = OAK[BS]
    campfire(S, cx + u(14), gy + u(3))
    sl = S.lay('seat', 5, cast=(u(1), 0, 1))
    sx0 = cx + u(4)
    sm = rect(sx0, gy + u(4), sx0 + S.kv(6, 11), gy + u(4) + S.kv(2, 3))
    for (x, y) in sm:
        sl[(x, y)] = OAK_LOG[LT if y == gy + u(4) else BS if y < gy + u(4) + S.kv(1, 2) else DK]
    end = (sx0 + S.kv(6, 11), gy + u(4))
    for j in range(S.kv(3, 4)):
        sl[(end[0], end[1] + j)] = LOG_END[LT if j == 0 else BS]
    outline(sl, sm | {(end[0], end[1] + j) for j in range(S.kv(3, 4))}, OAK_LOG)
    bl = S.lay('bedroll', 4, cast=(u(1), 0, 1))
    bm = set()
    for (x, y) in rect(tx - half - u(1) - S.kv(6, 10), gy - S.kv(2, 4), tx - half - u(1), gy - 1):
        j = y - (gy - S.kv(2, 4))
        bl[(x, y)] = BLUE_CLOTH[LT if j == 0 else DK if j == S.kv(1, 3) else BS]
        if (x - tx + half) % S.kv(3, 5) == 0:
            bl[(x, y)] = ROPE[BS]
        bm.add((x, y))
    outline(bl, bm, BLUE_CLOTH)
    if S.night:
        S.light(tx, gy - u(3), u(5))
    ground(S, tx - half - u(13), cx + u(21), gy, kind='grass', foot=(tx - half, tx + half - 1 + dd), shadow_len=u(4))


def mine_entrance(S, cx, gy):
    """Mine entrance: a rocky hillside (stone and dirt with ore specks, a grassy top hanging over it), a
    timber frame round a dark tunnel, rails with sleepers running out of it toward the viewer, a minecart
    of ore, a lantern on the lintel, a pick sign."""
    k, u = S.k, S.u
    HR, HH = u(_sz(S, 22, 26, 30)), u(_sz(S, 18, 22, 25))
    hl = S.lay('hill', 0)
    hm = dome_mask(cx, gy, HR, HH)
    stones(S, hl, hm, COBBLE, R2=DIRT, cell=S.kv((5, 4), (8, 6)), seed=101)
    rnd = S.rnd('ore')
    for (x, y) in sorted(hm):
        if rnd.random() < S.kv(0.012, 0.006) and y > gy - HH + u(6):
            R = GOLDR if rnd.random() < 0.4 else IRON_ORE
            for (a, b) in ((0, 0), (1, 0), (0, 1)) if k == 1 else ((0, 0), (1, 0), (0, 1), (1, 1), (2, 1)):
                if (x + a, y + b) in hm:
                    hl[(x + a, y + b)] = R[LT if (a, b) == (0, 0) else BS]
    cl = cols(hm)
    for x, (y0, y1) in cl.items():                           # grass cap with an uneven fringe
        n = S.kv(2, 3) + _crc(x, 'g') % S.kv(2, 4)
        for j in range(n):
            if (x, y0 + j) in hm:
                hl[(x, y0 + j)] = GRASS[LT if j == 0 else BS if j < n - 1 else DK]
    for (x, y) in hm:                                      # the hill turns away to the right
        if x > cx + HR * 0.55 and hl[(x, y)] not in GRASS:
            hl[(x, y)] = darker(hl[(x, y)])
    outline(hl, hm, COBBLE, lit=GRASS[SH])
    S.field({(x, y) for (x, y) in hm if y < cl[x][0] + S.kv(3, 5)})
    # tunnel and frame
    tw, th = u(12), u(13)
    tx0 = cx - tw // 2
    tl = S.lay('tunnel', 1)
    tm = rect(tx0, gy - th, tx0 + tw - 1, gy - 1)
    for (x, y) in tm:
        tl[(x, y)] = DEEP[O] if y > gy - th + S.kv(1, 2) and x > tx0 + S.kv(0, 1) else DEEP[SH]
    if S.night:
        for (x, y) in tm:
            if y > gy - th // 2 and tx0 + 2 < x < tx0 + tw - 3:
                tl[(x, y)] = GLOW[SH]
    fr = S.lay('frame', 3, cast=(u(1), u(1), 1))
    fm = set()
    pw = S.kv(2, 3)
    for xa in (tx0 - pw, tx0 + tw):
        fm |= log_v(S, fr, xa, xa + pw - 1, gy - th, gy - 1, OAK_LOG)
    outline(fr, fm, OAK_LOG)
    beam_h(S, tx0 - pw - S.kv(1, 2), tx0 + tw + pw - 1 + S.kv(1, 2), gy - th - S.kv(2, 4))
    lantern(S, tx0 + tw // 2, gy - th, side=1, arm=1, name='lanterns')
    # rails toward the viewer
    rl = S.lay('rails', -5, snow=False)
    front = u(7)
    for y in range(gy - th // 2, gy + front):
        d = max(0, y - gy)
        half = S.kv(2, 3) + (d * S.kv(2, 3)) // S.kv(4, 5) + (0 if y >= gy else 0)
        inside = y < gy
        if (y - gy) % S.kv(2, 3) == 0:
            for x in range(cx - half - S.kv(1, 2), cx + half + S.kv(1, 2)):
                rl[(x, y)] = (SPRUCE[DK] if inside else SPRUCE[BS])
        for x in (cx - half - 1, cx + half):
            rl[(x, y)] = (IRON[DK] if inside else IRON[LT if x < cx else BS])
    # minecart
    mc = S.lay('minecart', 5, cast=(u(1), 0, 1))
    mx = cx + HR - u(5)
    my = gy + u(3)
    rows = ('.oooooo.', 'oGgOoGo.', 'iiiiiiii', 'iIIIIIIi', 'iIIIIIIi', '.iiiiii.', '.w....w.') if k == 1 else \
        ('...oGoo.....', '.oOoGgoOoo..', 'ooGgoOoogGo.', 'iiiiiiiiiiii', 'iIIIIIIIIIIi', 'iIhIIIIIIIIi', 'iIIIIIIIIIIi',
         'iIIIIIIIIIIi', '.iiiiiiiiii.', '.ww......ww.', '.ww......ww.')
    mcm = set()
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch == '.':
                continue
            c = {'o': COBBLE[BS], 'O': COBBLE[LT], 'G': GOLDR[HI], 'g': GOLDR[BS], 'i': DARK_IRON[DK],
                 'I': DARK_IRON[BS] if i > len(row) // 3 else DARK_IRON[LT], 'h': IRON[HI], 'w': DARK_IRON[SH]}[ch]
            p = (mx + i - len(row) // 2, my - len(rows) + j)
            mc[p] = c
            mcm.add(p)
    outline(mc, mcm, DARK_IRON)
    # sign on a post
    sp = S.lay('signpost', 4, cast=(u(1), 0, 1))
    spx = cx - HR + u(3)
    spm = set()
    for y in range(gy - u(9), gy):
        sp[(spx, y)] = OAK[LT]
        spm.add((spx, y))
    bw_, bh_ = S.kv(7, 11), S.kv(5, 9)
    bx, by = spx - bw_ // 2, gy - u(9) - bh_ + S.kv(1, 2)
    for (x, y) in rect(bx, by, bx + bw_ - 1, by + bh_ - 1):
        sp[(x, y)] = OAK[LT] if (x == bx or y == by) else OAK[DK] if (x == bx + bw_ - 1 or y == by + bh_ - 1) else OAK[BS]
        spm.add((x, y))
    rows = SIGN_ICONS['pick'][k - 1]
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch in _ICON_COL:
                r_, t_ = _ICON_COL[ch]
                sp[(bx + (bw_ - len(row)) // 2 + i, by + (bh_ - len(rows)) // 2 + j)] = r_[t_]
    outline(sp, spm, OAK)
    ground(S, cx - HR - u(4), cx + HR + u(6), gy, kind='dirt', foot=(cx - HR, cx + HR), shadow_len=u(4))


def obsidian(S, lay, x0, y0, bs, crying=False, seed=0):
    """One obsidian block: a lit top-left bevel, a dark bottom-right, dark clusters, a diagonal glint;
    crying obsidian weeps purple."""
    rnd = S.rnd('obs', x0, y0, seed)
    m = rect(x0, y0, x0 + bs - 1, y0 + bs - 1)
    for (x, y) in m:
        i, j = x - x0, y - y0
        t = BS
        if i == 0 or j == 0:
            t = LT
        elif i == bs - 1 or j == bs - 1:
            t = SH
        lay[(x, y)] = OBSIDIAN[t]
    for _ in range(S.kv(1, 3)):
        a, b = rnd.randint(1, bs - 3), rnd.randint(1, bs - 3)
        for (p, q) in ((0, 0), (1, 0), (0, 1)):
            lay[(x0 + a + p, y0 + b + q)] = OBSIDIAN[DK]
    g = rnd.randint(1, max(1, bs - 4))
    for i in range(S.kv(2, 3)):
        if 0 < g + i < bs - 1 and 0 < bs - 2 - i < bs - 1:
            lay[(x0 + g + i, y0 + bs - 2 - i - (bs // 3))] = OBSIDIAN[HI if i == 0 else LT]
    if crying:
        for (a, b) in ((1, 1), (2, 1), (1, 2), (bs - 3, 2), (bs - 3, 3), (bs - 3, 4)):
            if 0 < a < bs - 1 and 0 < b < bs - 1:
                lay[(x0 + a, y0 + b)] = PORTAL[LT if b < 2 else BS]
    return m


def portal_ruin(S, cx, gy):
    """Ruined nether portal: an obsidian frame (bevelled blocks with glints, a few crying, a few missing),
    a swirling portal surface (emissive bands), netherrack and gold blocks round the foot, broken mossy
    stone-brick walls; purple light at night."""
    k, u = S.k, S.u
    bs = S.kv(4, 8)
    nw, nh = 4, 5
    fx0 = cx - (nw * bs) // 2
    fy0 = gy - nh * bs
    pl = S.lay('portal', 1)
    inner = rect(fx0 + bs, fy0 + bs, fx0 + (nw - 1) * bs - 1, gy - bs - 1)
    ph = S.rnd('portal').random() * 6
    for (x, y) in inner:
        f = 0.9 if k == 1 else 0.5
        v = math.sin((x * 0.7 + math.sin(y * 0.45 * f + ph) * 2.2) * f) + 0.7 * math.sin((y * 0.55 - x * 0.25) * f + ph)
        t = DK if v < -0.6 else BS if v < 0.3 else LT if v < 1.1 else HI
        pl[(x, y)] = PORTAL[t]
    fl = S.lay('frame', 2)
    fm = set()
    missing = {(3, 0), (0, 0)} if S.size != 'l' else {(3, 0)}
    crying = {(0, 2), (3, 3)}
    for i in range(nw):
        for j in range(nh):
            if 0 < i < nw - 1 and 0 < j < nh - 1:
                continue
            if (i, j) in missing:
                continue
            fm |= obsidian(S, fl, fx0 + i * bs, fy0 + j * bs, bs, crying=(i, j) in crying, seed=i * 7 + j)
    outline(fl, fm, OBSIDIAN)
    # broken stone-brick walls either side
    wl = S.lay('ruins', 0)
    wm = set()
    for side in (-1, 1):
        xa = fx0 - u(9) if side < 0 else fx0 + nw * bs + u(1)
        for x in range(xa, xa + u(8)):
            hgt = u(5) + int(u(9) * abs(math.sin((x - xa) * 0.35 + side))) if side < 0 else u(4) + (x - xa) // 2
            for y in range(gy - hgt, gy):
                wm.add((x, y))
    ashlar(S, wl, wm, STONE, y0=gy, x0=fx0, bw=S.kv(6, 10), bh=S.kv(3, 5), seed=111, moss=0.15)
    outline(wl, wm, STONE)
    # netherrack and gold at the foot
    nl = S.lay('netherrack', 3)
    nm = set()
    for (nx, nwid, nhh) in ((fx0 - u(4), u(6), u(3)), (fx0 + nw * bs - u(2), u(7), u(2)), (fx0 + u(3), u(5), u(1))):
        b = {(x, y) for (x, y) in rect(nx, gy - nhh, nx + nwid - 1, gy - 1)}
        stones(S, nl, b, NETHERRACK, cell=S.kv((3, 2), (4, 3)), seed=nx)
        nm |= b
    gb = rect(fx0 + nw * bs + u(2), gy - S.kv(4, 7), fx0 + nw * bs + u(2) + S.kv(4, 7) - 1, gy - 1)
    for (x, y) in gb:
        i, j = x - min(p[0] for p in gb), y - min(p[1] for p in gb)
        nl[(x, y)] = GOLDR[LT if i == 0 or j == 0 else DK if i == S.kv(3, 6) or j == S.kv(3, 6) else BS]
        if S.k == 2 and (i, j) in ((2, 1), (3, 1), (1, 2)):
            nl[(x, y)] = GOLDR[HI]
    nm |= gb
    outline(nl, nm, NETHERRACK)
    if S.night:
        S.light(cx, gy - nh * bs / 2, u(16), 'portal')
    else:
        S.light(cx, gy - nh * bs / 2, u(8), 'portal')
    ground(S, fx0 - u(12), fx0 + nw * bs + u(12), gy, kind='dirt', foot=(fx0 - u(9), fx0 + nw * bs + u(9)))
    gl = S.lay('ground')
    if gl:                                                 # the nether spreads: a netherrack patch on the ground
        patch = {p for p in disc(cx, gy + u(1), nw * bs * 0.75, u(3)) if p in gl and p[1] >= gy - u(2)}
        stones(S, gl, patch, NETHERRACK, cell=S.kv((4, 2), (6, 4)), seed=7)
        for (x, y) in edge(patch):
            if (x, y - 1) not in patch:
                gl[(x, y)] = NETHERRACK[LT]


def wizard_tower(S, cx, gy):
    """Wizard tower: a slender tower of purple-grey stone (cylinder-shaded courses), round windows with an
    arcane cyan glow, a balcony ring, a tall crooked violet hat roof with gold stars and a moon, floating
    orbs and sparkles, crystals at the foot."""
    k, u = S.k, S.u
    R = u(_sz(S, 6, 7, 8))
    H = u(_sz(S, 34, 40, 46))
    yt = gy - H
    lay = S.lay('walls', 0)
    m = rect(cx - R, yt, cx + R - 1, gy - 1)
    ch = S.kv(3, 5)
    for (x, y) in m:
        nx = (x + 0.5 - cx) / R
        t = cyl_tone(nx)
        row, r = (gy - 1 - y) // ch, (gy - 1 - y) % ch
        a = (math.asin(max(-0.99, min(0.99, nx))) / 0.55 + (row % 2) * 0.5)
        if r == ch - 1 or a - math.floor(a) < 1.0 / (R * 0.55 * max(0.3, math.cos(math.asin(max(-0.99, min(0.99, nx)))))):
            t = max(SH, t - 1)
        lay[(x, y)] = WIZ_STONE[t]
    outline(lay, m, WIZ_STONE)
    for (wx, wy) in ((cx - S.kv(2, 3), yt + u(6)), (cx - S.kv(2, 3), yt + u(20))):
        window(S, wx, wy, S.kv(4, 6), S.kv(4, 6), frame=DARK_OAK, style='round', sill=None, glass_ramp=ARCANE,
               light=False)
        if S.night:
            S.light(wx + S.kv(2, 3), wy + S.kv(2, 3), u(5), 'arcane')
    # balcony
    bl = S.lay('balcony', 2, cast=(u(1), u(1), 1))
    by = yt + u(14)
    bw = R + u(3)
    bm = set()
    for x in range(cx - bw, cx + bw):
        for j in range(S.kv(1, 2)):
            bl[(x, by + j)] = DARK_OAK[LT if j == 0 else DK]
            bm.add((x, by + j))
        bl[(x, by - S.kv(4, 6))] = DARK_OAK[LT]
        bm.add((x, by - S.kv(4, 6)))
        if (x - cx) % S.kv(2, 3) == 0 and abs(x + 0.5 - cx) > R - 1:
            for y in range(by - S.kv(4, 6) + 1, by):
                bl[(x, y)] = DARK_OAK[BS]
                bm.add((x, y))
    outline(bl, bm, DARK_OAK)
    S.ledge(cx - bw, cx + bw - 1, by)
    dw, dh = S.kv(5, 8), S.kv(8, 14)
    door(S, cx - dw // 2, gy - dh, dw, dh, DARK_OAK, WIZ_STONE, style='arch', handle=GOLDR)
    # the hat
    rl = S.lay('roof', 3, cast=(u(1), u(1), 1), roof=True)
    hh = u(_sz(S, 22, 26, 30))
    brim = R + u(3)
    hm = set()
    xl = steady([round(cx - brim * ((j + 1) / hh) ** 0.9 + u(5) * (1 - (j + 1) / hh) ** 2.2) for j in range(hh)])
    xr = steady([round(cx + brim * ((j + 1) / hh) ** 0.9 + u(5) * (1 - (j + 1) / hh) ** 2.2) for j in range(hh)])
    for j in range(hh):
        f = (j + 1) / hh
        half = brim * f ** 0.9
        bend = int(round(u(5) * (1 - f) ** 2.2))
        y = yt + S.kv(1, 2) - hh + j
        for x in range(xl[j], max(xl[j] + 1, xr[j])):
            rel = (x + 0.5 - cx - bend) / max(1, half)
            t = LT if rel < -0.3 else BS if rel < 0.35 else DK
            if (yt - y) % S.kv(4, 6) == 0:
                t = max(SH, t - 1)
            rl[(x, y)] = MAGIC[t]
            hm.add((x, y))
    for x in range(cx - brim - S.kv(1, 2), cx + brim + S.kv(1, 2)):
        for j in range(S.kv(1, 2)):
            y = yt + S.kv(1, 2) + j
            rl[(x, y)] = MAGIC[LT if j == 0 and x < cx else BS if j == 0 else SH]
            hm.add((x, y))
    rnd = S.rnd('stars')
    for _ in range(_sz(S, 3, 4, 5)):
        x, y = rnd.choice(sorted(p for p in hm if p[1] < yt - u(3)))
        for (a, b) in ((0, 0),) if k == 1 else ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            if (x + a, y + b) in hm:
                rl[(x + a, y + b)] = GOLDR[HI if (a, b) == (0, 0) else LT]
    mx_, my_ = cx - u(2), yt - u(8)
    moon = disc(mx_, my_, S.kv(1.6, 2.6)) - disc(mx_ + S.kv(1, 1.4), my_ - S.kv(0.5, 0.8), S.kv(1.4, 2.2))
    for p in moon:
        if p in hm:
            rl[p] = CREAMR[HI]
    outline(rl, hm, MAGIC)
    S.field({p for p in hm if p[1] > yt - hh // 2})
    # orbs and sparkles
    ol = S.lay('orbs', 8, snow=False)
    for (ox, oy, r) in ((cx + brim + u(4), yt - u(12), S.kv(1.6, 2.6)), (cx - brim - u(3), yt - u(4), S.kv(1.2, 2.0))):
        pts = disc(ox, oy, r)
        for (x, y) in pts:
            ol[(x, y)] = ARCANE[dome_tone((x + 0.5 - ox) / r, (y + 0.5 - oy) / r)]
        outline(ol, pts, ARCANE)
        if S.night:
            S.light(ox, oy, u(6), 'arcane')
    for (sx, sy) in ((cx + brim + u(1), yt - u(18)), (cx - brim - u(6), yt - u(13)), (cx + u(9), yt + u(4))):
        ol[(sx, sy)] = CREAMR[HI]
        for (a, b) in N4:
            ol[(sx + a, sy + b)] = ARCANE[LT]
    # crystals at the foot
    cl = S.lay('crystals', 5, cast=(u(1), 0, 1))
    cm = set()
    for (x, hgt, R2) in ((cx - R - u(3), u(6), ARCANE), (cx - R - u(1), u(4), PORTAL), (cx + R + u(2), u(5), PORTAL)):
        w = S.kv(2, 4)
        for j in range(hgt):
            ww = max(1, min(w, (j * w) // max(1, S.kv(2, 3)) + 1))
            for i in range(ww):
                p = (x + i - ww // 2, gy - hgt + j)
                cl[p] = R2[HI if i == 0 and j < 2 else LT if i < ww / 2 else DK]
                cm.add(p)
    outline(cl, cm, MAGIC)
    ground(S, cx - brim - u(9), cx + brim + u(10), gy, foot=(cx - R, cx + R - 1), paths=[(cx - dw // 2, cx + dw // 2 - 1)])


def guard_post(S, cx, gy):
    """Guard post: a wooden watchtower - two log legs with X braces, a ladder, a plank platform with a
    breastwork, corner posts carrying a small hipped roof, a banner and a torch."""
    u = S.u
    lw = u(_sz(S, 8, 9, 10))
    py = gy - u(_sz(S, 24, 28, 32))
    ll = S.lay('legs', 0)
    pw = S.kv(2, 3)
    lm = set()
    for xa in (cx - lw, cx + lw - pw):
        lm |= log_v(S, ll, xa, xa + pw - 1, py, gy - 1, SPRUCE_LOG)
    sec = (2 * lw - 2 * pw)
    y = py + S.kv(2, 4)
    while y + sec <= gy - 1:
        for i in range(sec):
            for p in ((cx - lw + pw + i, y + i), (cx + lw - pw - 1 - i, y + i)):
                if p not in lm:
                    ll[p] = SPRUCE[BS if p[0] < cx else DK]
                    lm.add(p)
        y += sec
    outline(ll, lm, SPRUCE_LOG)
    pixel_perfect_layer(ll, {SPRUCE_LOG[O], SPRUCE_LOG[SH]})
    ld = S.lay('ladder', 1)
    ldm = set()
    lx = cx - S.kv(2, 3)
    for y in range(py, gy):
        for x in (lx, lx + S.kv(4, 6)):
            ld[(x, y)] = OAK[LT if x == lx else DK]
            ldm.add((x, y))
        if (y - py) % S.kv(3, 4) == 2:
            for x in range(lx + 1, lx + S.kv(4, 6)):
                ld[(x, y)] = OAK[BS]
                ldm.add((x, y))
    outline(ld, ldm, OAK)
    pl = S.lay('platform', 2, cast=(u(1), u(1), 1))
    hw_ = lw + u(4)
    pm = rect(cx - hw_, py - S.kv(1, 2), cx + hw_ - 1, py)
    for (x, y) in pm:
        pl[(x, y)] = SPRUCE[LT if y == py - S.kv(1, 2) else DK]
    bh = u(6)
    bwk = rect(cx - hw_, py - S.kv(1, 2) - bh, cx + hw_ - 1, py - S.kv(1, 2) - 1)
    planks(S, pl, bwk, SPRUCE, vertical=True, x0=cx, seed=121, board=S.kv(3, 4))
    for x in range(cx - hw_, cx + hw_):
        pl[(x, py - S.kv(1, 2) - bh)] = SPRUCE[LT]
    pm |= bwk
    cp = S.kv(1, 2)
    roof_y = py - S.kv(1, 2) - bh - u(8)
    for xa in (cx - hw_, cx + hw_ - cp):
        for y in range(roof_y, py - S.kv(1, 2) - bh):
            for i in range(cp):
                pl[(xa + i, y)] = SPRUCE_LOG[LT if i == 0 else DK]
                pm.add((xa + i, y))
    outline(pl, pm, SPRUCE)
    S.ledge(cx - hw_, cx + hw_ - 1, py - S.kv(1, 2) - bh)
    hip_roof(S, cx - hw_ - u(3), cx + hw_ + u(3) - 1, roof_y + S.kv(1, 2), u(7), SHINGLE, style='wood', seed=122)
    banner(S, cx + hw_ - u(1) - S.kv(4, 6), py + S.kv(1, 2), S.kv(4, 6), u(9), R=BLUE_CLOTH)
    torch(S, cx - hw_ + S.kv(2, 3), py - S.kv(1, 2) - bh - S.kv(3, 5))
    ground(S, cx - hw_ - u(6), cx + hw_ + u(8), gy, foot=(cx - lw, cx + lw - 1), shadow_len=u(5))


def boat(S, lay, x, wl_y, w, R=OAK):
    """A rowboat floating at water line wl_y, seen from the side: a curved hull (lit top strake, dark
    lower strakes), a gunwale, a seat, an oar; only the part above the water."""
    k = S.k
    m = set()
    h = S.kv(4, 7)
    for i in range(w):
        f = abs(i + 0.5 - w / 2) / (w / 2)
        top = wl_y - h + int(round((f ** 3) * -S.kv(2, 3)))
        bot = wl_y - int(round(f ** 2 * S.kv(2, 4)))
        for y in range(top, bot + 1):
            j = y - top
            t = LT if j == 0 else BS if j < (bot - top) // 2 + 1 else DK
            if k == 2 and j == 1:
                t = DK
            lay[(x + i, y)] = R[t]
            m.add((x + i, y))
    for i in range(w // 3, w // 3 + S.kv(2, 4)):
        lay[(x + i, wl_y - h - S.kv(0, 1))] = R[HI if k == 2 else LT]
        m.add((x + i, wl_y - h - S.kv(0, 1)))
    for i in range(S.kv(6, 11)):
        p = (x + w // 2 + i, wl_y - h - S.kv(1, 2) + i // 2)
        lay[p] = SPRUCE[LT if i % 2 else BS]
        m.add(p)
    return m


def dock(S, cx, gy):
    """Dock: a plank pier running from a sandy shore out over the water on posts (each post with a dark
    reflection), a rowboat moored to it with a rope, barrels and a crate, a lamp post at the end; water with
    ripple clusters."""
    u = S.u
    hw = u(_sz(S, 22, 26, 30))
    x0, x1 = cx - hw, cx + hw - 1
    back, front = u(6), u(16)
    gl = S.lay('ground', -10, snow=False)
    shore = {(x, y) for (x, y) in rect(x0, gy - back, x1, gy) if not ((x < x0 + 2 or x > x1 - 2) and y == gy - back)}
    for (x, y) in shore:
        gl[(x, y)] = SAND[LT if y == gy - back else BS if (x * 3 + y) % 11 else DK]
        if y == gy:
            gl[(x, y)] = SAND[DK]
    wat = rect(x0, gy + 1, x1, gy + front + S.kv(3, 6))
    water(S, gl, wat, seed=7, flow='still')
    for (x, y) in wat:
        if y >= gy + front:
            gl[(x, y)] = WATER[DK if y < gy + front + S.kv(2, 4) else SH]
    if S.snow:
        for (x, y) in shore:
            gl[(x, y)] = SNOW[LT if y == gy - back else BS]
    outline(gl, shore | wat, WATER, lit=SAND[SH])
    # pier: toward the viewer, boards across, posts on both sides
    pl = S.lay('pier', 2, cast=(u(1), u(1), 1))
    pw_ = u(_sz(S, 7, 8, 9))
    px0 = cx - u(10)
    pm = set()
    for y in range(gy - back + u(1), gy + front - u(2)):
        for x in range(px0, px0 + pw_):
            j = (y - gy) % S.kv(2, 3)
            c = OAK[LT] if j == 0 else OAK[BS]
            if x == px0:
                c = OAK[LT]
            elif x == px0 + pw_ - 1:
                c = OAK[DK]
            pl[(x, y)] = c
            pm.add((x, y))
    for y in range(gy + front - u(2), gy + front - u(2) + S.kv(1, 2)):
        for x in range(px0, px0 + pw_):
            pl[(x, y)] = OAK[DK]
            pm.add((x, y))
    posts = S.lay('posts', 1)
    psm = set()
    for y in range(gy + u(2), gy + front, u(5)):
        for xa in (px0 - S.kv(1, 2), px0 + pw_):
            for j in range(S.kv(3, 5)):
                for i in range(S.kv(1, 2)):
                    posts[(xa + i, y + j)] = SPRUCE_LOG[LT if i == 0 else DK]
                    psm.add((xa + i, y + j))
            for j in range(S.kv(2, 3)):                   # the reflection under it
                posts[(xa + (j % 2), y + S.kv(3, 5) + j)] = WATER[DK]
    outline(posts, psm, SPRUCE_LOG)
    outline(pl, pm, OAK)
    S.ledge(px0, px0 + pw_ - 1, gy)
    # boat moored to the right of the pier
    bl = S.lay('boat', 4, cast=(0, u(1), 1))
    bw = u(_sz(S, 14, 16, 18))
    bx = px0 + pw_ + u(4)
    bwl = gy + u(10)
    bm = boat(S, bl, bx, bwl, bw)
    outline(bl, bm, OAK)
    rf = S.lay('boat_water', 5, snow=False)
    for i in range(-1, bw + 1):
        rf[(bx + i, bwl + 1)] = WATER[HI if i % 3 else LT]
        rf[(bx + i + 1, bwl + 2)] = WATER[DK] if 0 < i < bw - 1 else rf.get((bx + i + 1, bwl + 2), WATER[BS])
    ropel = S.lay('rope', 5)
    for i in range(u(4)):
        ropel[(px0 + pw_ + i, bwl - S.kv(3, 5) + (i * i) // max(1, u(4)))] = ROPE[BS]
    # barrels, crate and a lamp at the shore end
    barrel(S, px0 + pw_ + u(2), gy - u(1))
    crate(S, px0 - u(9), gy - u(1), R=SPRUCE)
    lp = S.lay('lamp_post', 3, cast=(u(1), 0, 1))
    lx = px0 + pw_ - S.kv(2, 3)
    ly = gy + front - u(4)
    lpm = rect(lx, ly - u(12), lx + S.kv(0, 1), ly)
    for (x, y) in lpm:
        lp[(x, y)] = DARK_IRON[LT if x == lx else DK]
    outline(lp, lpm, DARK_IRON)
    lantern(S, lx, ly - u(12) - S.kv(4, 7), post=True)
    if S.night:
        S.light(px0 + pw_ // 2, ly, u(7))
    # a small reed patch on the shore
    rd = S.lay('reeds', 3)
    for i, x in enumerate(range(x1 - u(9), x1 - u(2), S.kv(2, 3))):
        hgt = S.kv(3, 6) + (i % 3)
        for j in range(hgt):
            rd[(x, gy + S.kv(1, 2) - j)] = LEAVES[LT if j > hgt - 3 else BS]
        if i % 2 == 0:
            rd[(x, gy + S.kv(1, 2) - hgt)] = DIRT[BS]


CATALOG = {
    'cottage': cottage,
    'stone_house': stone_house,
    'log_cabin': log_cabin,
    'birch_house': birch_house,
    'spruce_aframe': spruce_aframe,
    'desert_house': desert_house,
    'igloo': igloo,
    'mushroom_house': mushroom_house,
    'treehouse': treehouse,
    'tower': tower,
    'windmill': windmill,
    'watermill': watermill,
    'castle_gate': castle_gate,
    'castle_keep': castle_keep,
    'chapel': chapel,
    'tavern': tavern,
    'market_stall': market_stall,
    'lighthouse': lighthouse,
    'forge': forge,
    'barn': barn,
    'well': well,
    'tent': tent,
    'mine_entrance': mine_entrance,
    'portal_ruin': portal_ruin,
    'wizard_tower': wizard_tower,
    'guard_post': guard_post,
    'dock': dock,
}



# ------------------------------------------------------------------ village
VILLAGE_POOL = ('cottage', 'stone_house', 'tavern', 'birch_house', 'log_cabin', 'chapel', 'forge', 'barn',
                'windmill', 'mushroom_house', 'spruce_aframe')
VILLAGE_SMALL = ('well', 'market_stall', 'tent')


def sky(S, W, hz, seed=0):
    """Sky for a scene: day = three stepped blue bands (lighter toward the horizon) and flat blocky clouds
    with lit tops; night = deep blue bands, stars (a few with plus-shaped glints) and a moon with craters.
    Drawn as raw colours (the night map skips it)."""
    k, u = S.k, S.u
    lay = Layer()
    rnd = S.rnd('sky', seed)
    if not S.night:
        for y in range(hz):
            t = BS if y < hz * 0.4 else LT if y < hz * 0.78 else HI
            for x in range(W):
                lay[(x, y)] = SKY_DAY[t]
        for i in range(max(2, W // u(45))):
            x0 = rnd.randint(0, W - u(20))
            y0 = rnd.randint(u(3), max(u(4), int(hz * 0.5)))
            pts = set()
            for (bx, by, w, h) in ((0, u(2), u(18), u(4)), (u(4), 0, u(8), u(3)), (u(11), u(1), u(5), u(2))):
                pts |= rect(x0 + bx, y0 + by, x0 + bx + w - 1, y0 + by + h - 1)
            for (x, y) in pts:
                if 0 <= x < W:
                    lay[(x, y)] = CLOUD[HI] if (x, y - 1) not in pts else CLOUD[BS] if (x, y + 1) not in pts else CLOUD[LT]
        S.add('sky', lay, z=-3000, snow=False, raw=True)
        return
    for y in range(hz):
        t = SH if y < hz * 0.4 else DK if y < hz * 0.78 else BS
        for x in range(W):
            lay[(x, y)] = SKY_NIGHT[t]
    for _ in range(W * hz // (60 * k * k)):
        x, y = rnd.randrange(W), rnd.randrange(max(1, hz - u(6)))
        lay[(x, y)] = CREAMR[HI] if rnd.random() < 0.5 else SKY_NIGHT[HI]
    for _ in range(max(2, W // u(40))):
        x, y = rnd.randrange(u(4), W - u(4)), rnd.randrange(u(3), max(u(4), hz // 2))
        lay[(x, y)] = CREAMR[HI]
        for (a, b) in N4:
            lay[(x + a, y + b)] = SKY_NIGHT[HI]
    mx, my, mr = W - u(22), u(12), S.kv(4.5, 8.5)
    md = disc(mx, my, mr)
    for (x, y) in md:
        lay[(x, y)] = MOON[HI] if (x + 0.5 - mx) + (y + 0.5 - my) < -mr * 0.5 else MOON[LT]
    for (a, b, r) in ((-0.3, 0.1, 0.22), (0.25, -0.3, 0.16), (0.2, 0.35, 0.18)):
        for p in disc(mx + a * mr, my + b * mr, max(1.0, r * mr)):
            if p in md:
                lay[p] = MOON[BS]
    S.add('sky', lay, z=-3000, snow=False, raw=True)


def hills(S, W, hz, seed=0):
    """Two layers of far hills in haze along the horizon, with a line of tiny trees on the nearer one."""
    u = S.u
    lay = Layer()
    for x in range(W):
        h1 = u(9) + u(4) * math.sin(x / u(14) + seed) + u(2) * math.sin(x / u(5) + 2 * seed)
        h2 = u(5) + u(3) * math.sin(x / u(9) + 1 + seed)
        for y in range(int(hz - h1), hz):
            lay[(x, y)] = HAZE[LT if y == int(hz - h1) else BS]
        for y in range(int(hz - h2), hz):
            lay[(x, y)] = HAZE[BS if y == int(hz - h2) else DK]
    rnd = S.rnd('far trees', seed)
    x = 0
    while x < W:
        r = S.kv(2, 3.5) + rnd.random() * S.kv(1, 2)
        cy = hz - u(3) - rnd.random() * u(2)
        for p in disc(x, cy, r, r * 1.1):
            if p[1] < hz:
                lay[p] = HAZE[DK if p[0] + p[1] > x + cy else BS]
        x += int(r * 2) + rnd.randint(0, u(3))
    S.add('hills', lay, z=-2900, snow=False)


def field(S, W, H, hz, seed=0):
    """The village green from the horizon down: grass (snow) with blade clusters, a few darker patches and
    flower clumps; flat, no directional gradient."""
    k, u = S.k, S.u
    R = SNOW if S.snow else GRASS
    lay = Layer()
    rnd = S.rnd('field', seed)
    for y in range(hz, H):
        for x in range(W):
            lay[(x, y)] = R[BS]
    for _ in range(W * (H - hz) // (u(60) * u(10) // k)):
        cx, cy = rnd.randrange(W), rnd.randrange(hz + u(2), H)
        for p in disc(cx, cy, u(6) + rnd.random() * u(5), u(2) + rnd.random() * u(2)):
            if p in lay:
                lay[p] = R[DK] if not S.snow else R[LT]
    for (x, y) in sorted(lay):
        r = rnd.random()
        if r < S.kv(0.05, 0.04) and y > hz:
            for j in range(S.kv(1, 2)):
                if (x, y - j) in lay:
                    lay[(x, y - j)] = R[LT] if r < 0.025 else R[DK if lay[(x, y - j)] == R[BS] else SH]
        elif not S.snow and r < 0.0015 * (2 if k == 2 else 1):
            Rf = FLOWERS[int(r * 10000) % 4]
            for (a, b) in ((0, 0), (1, 0)) if k == 1 else ((0, 0), (1, 0), (0, 1), (1, 1), (3, 1)):
                lay[(x + a, y + b)] = Rf[LT if (a + b) == 0 else BS]
    for x in range(W):
        lay[(x, hz)] = R[DK]
    S.add('field', lay, z=-2800, snow=False)
    return lay


def road(S, W, y0, y1, seed=0):
    """A dirt road across the scene: worn base, a lit far bank and a dark near edge, pebble clusters, wheel
    ruts (HD)."""
    k = S.k
    R = SNOW if S.snow else PATH
    lay = Layer()
    rnd = S.rnd('road', seed)
    for y in range(y0, y1 + 1):
        for x in range(W):
            c = R[BS]
            if y == y0:
                c = R[DK]
            elif y == y1:
                c = R[LT]
            elif k == 2 and y in (y0 + (y1 - y0) // 3, y0 + 2 * (y1 - y0) // 3) and not S.snow:
                c = R[DK]
            lay[(x, y)] = c
    for (x, y) in sorted(lay):
        if y0 < y < y1 and rnd.random() < 0.03 and lay[(x, y)] == R[BS]:
            for i in range(S.kv(1, 2)):
                if (x + i, y) in lay:
                    lay[(x + i, y)] = (GRAVEL if not S.snow else SNOW)[LT]
            if (x, y + 1) in lay and y + 1 < y1:
                lay[(x, y + 1)] = (GRAVEL if not S.snow else SNOW)[DK]
    S.add('road', lay, z=-2700, snow=False)
    return lay


def footpath(S, lay, x0, x1, y0, y1):
    """A short footpath from a door to the road (into the given ground layer)."""
    R = SNOW if S.snow else PATH
    for y in range(min(y0, y1), max(y0, y1) + 1):
        for x in range(x0, x1 + 1):
            lay[(x, y)] = R[DK] if x == x0 else R[LT] if x == x1 else R[BS] if (x * 7 + y * 3) % 9 else R[DK]


def garden(S, x0, x1, y0, y1, seed=0):
    """A fenced vegetable patch: farmland rows with crops (wheat ears, carrot tops, cabbages) behind a
    fence along its front edge."""
    k = S.k
    lay = S.lay('garden', -5, snow=True)
    rnd = S.rnd('garden', seed)
    rows = list(range(y0, y1 + 1))
    crop = [HAY, LEAVES, BIRCH_LEAVES]
    for y in rows:
        r = (y - y0) % S.kv(3, 4)
        for x in range(x0, x1 + 1):
            if S.snow:
                lay[(x, y)] = SNOW[BS if r else DK]
                continue
            lay[(x, y)] = DIRT[SH] if r == 0 else DIRT[DK] if r == 1 else DIRT[BS]
    if not S.snow:
        for y in range(y0 + S.kv(1, 2), y1 + 1, S.kv(3, 4)):
            R = crop[(y // S.kv(3, 4)) % 3]
            for x in range(x0 + 1, x1, S.kv(2, 3)):
                h = S.kv(2, 3) + rnd.randint(0, 1)
                for j in range(h):
                    lay[(x, y - j)] = R[LT if j == h - 1 else BS if j else DK]
                if R is HAY and k == 2:
                    lay[(x + 1, y - h + 1)] = HAY[BS]
    outline(lay, rect(x0, y0, x1, y1), DIRT, lit=GRASS[SH] if not S.snow else SNOW[DK])
    fence(S, x0 - S.kv(1, 2), x1 + S.kv(1, 2), y1 + S.kv(1, 2), OAK, name='garden_fence', z=-4)


def lamp_post(S, x, gy, name='lamp_posts'):
    """A lamp post: an iron post with a lit base, the lantern on top (a light pool at night)."""
    u = S.u
    lay = S.lay(name, 4, cast=(u(1), 0, 1))
    m = rect(x, gy - u(14), x + S.kv(0, 1), gy - 1)
    for (px, py) in m:
        lay[(px, py)] = DARK_IRON[LT if px == x else DK]
    for i in range(-1, S.kv(2, 3)):
        lay[(x + i, gy - 1)] = DARK_IRON[BS]
        m.add((x + i, gy - 1))
    outline(lay, m, DARK_IRON)
    lantern(S, x, gy - u(14) - S.kv(4, 7), post=True, name=name + '_lamps')


def _measure(name, k, size):
    """Footprint of a building drawn without ground: (left, right) relative to its cx, and its door
    column range."""
    S = Scene(k, False, False, 0, size, False)
    CATALOG[name](S, 0, 0)
    pts = [p for prt in S.parts for p in prt['lay'] if not prt['name'].endswith(('smoke', 'light_beams'))]
    x0, y0, x1, y1 = bbox(pts)
    door_ = [p for prt in S.parts if prt['name'] == 'door' for p in prt['lay']]
    dr = (min(p[0] for p in door_), max(p[0] for p in door_)) if door_ else (-S.u(2), S.u(2))
    return x0, x1, dr


def village(width=160, height=100, seed=0, k=1, night=False, snow=False, names=None, **opts):
    """A village scene as parts (bottom -> top): sky, hills, field, road, a back row of buildings standing
    on the far side of the road with footpaths down to it, trees between them, a front row of smaller
    buildings, a fenced garden, lamp posts along the road; one light pool part at night. width / height are
    in GUI pixels (the canvas is width*k x height*k). names = the buildings to use (default: picked from
    VILLAGE_POOL by seed)."""
    S = Scene(k, night, snow, seed, 'm', False)
    u = S.u
    W, H = u(width), u(height)
    rnd = random.Random(_crc('village', seed))
    hz = int(H * 0.36)
    sky(S, W, hz, seed)
    hills(S, W, hz, seed)
    fl = field(S, W, H, hz, seed)
    gy_b = hz + u(16)
    ry0, ry1 = gy_b + u(3), gy_b + u(9)
    road(S, W, ry0, ry1, seed)
    gy_f = H - u(4)
    pool = list(names or VILLAGE_POOL)
    if not names:
        rnd.shuffle(pool)
    # back row: houses side by side with gaps for trees
    placed = []
    x = u(4) + rnd.randint(0, u(4))
    i = 0
    while i < len(pool) and x < W - u(20):
        nm = pool[i]
        size = 'm' if rnd.random() < 0.6 else 's'
        l, r, dr = _measure(nm, k, size)
        if x + (r - l) > W - u(2):
            i += 1
            continue
        cx = x - l
        placed.append(('b', nm, cx, size, dr))
        x += (r - l) + u(6) + rnd.randint(0, u(8))
        i += 1
    # trees behind / between the back row
    for j in range(max(3, W // u(28))):
        tx = rnd.randint(u(4), W - u(4))
        S.zbase = -2000 + j
        S.prefix = f'tree{j}/'
        tree(S, tx, gy_b - u(2) - rnd.randint(0, u(3)),
             kind=('spruce' if snow or rnd.random() < 0.3 else rnd.choice(('oak', 'oak', 'birch'))), seed=j)
    S.zbase = 0
    for n_, (row, nm, cx, size, dr) in enumerate(placed):
        S.prefix = f'{nm}{n_}/'
        S.size = size
        S.zbase = n_ * 100
        build(S, nm, cx, gy_b)
        footpath(S, fl, cx + dr[0], cx + dr[1], gy_b, ry0)
        _ground_shadow(S, fl, S.prefix, gy_b)
    # front row: small things and a garden, lamp posts along the road
    S.size = 'm'
    x = u(6) + rnd.randint(0, u(6))
    j = 0
    smalls = list(VILLAGE_SMALL)
    rnd.shuffle(smalls)
    S.zbase = 5000
    while x < W - u(30):
        if j % 2 == 0 and smalls:
            nm = smalls.pop()
            l, r, dr = _measure(nm, k, 'm')
            if x + (r - l) > W - u(4):
                break
            S.prefix = f'{nm}_front/'
            S.zbase = 5000 + j * 100
            build(S, nm, x - l, gy_f)
            _ground_shadow(S, fl, S.prefix, gy_f)
            x += (r - l) + u(8)
        else:
            gw = u(26) + rnd.randint(0, u(8))
            if x + gw > W - u(4):
                break
            S.prefix = f'garden{j}/'
            S.zbase = 5000 + j * 100
            garden(S, x, x + gw, gy_f - u(12), gy_f - u(4), seed=j)
            x += gw + u(10)
        j += 1
    S.prefix = ''
    S.zbase = 4000
    for lx in range(u(14) + rnd.randint(0, u(10)), W - u(6), u(46)):
        S.prefix = f'lamp{lx}/'
        lamp_post(S, lx, ry1 + u(2))
    S.prefix = ''
    S.zbase = 9000
    for j in range(2):
        tx = rnd.choice((rnd.randint(u(2), u(14)), rnd.randint(W - u(14), W - u(2))))
        S.prefix = f'near_tree{j}/'
        tree(S, tx, H - u(1), kind='spruce' if snow else 'oak', h=u(26), seed=50 + j)
        if snow:
            snow_pass(S, S.prefix)
    S.prefix = ''
    S.zbase = 0
    items, size_ = S.finish()
    out = []
    ox, oy = S.origin
    for it in items:                                       # keep the scene canvas: clip to W x H
        sp, x0, y0 = it['sprite'], it['x'] + ox, it['y'] + oy
        a0, b0 = max(0, -x0), max(0, -y0)
        a1, b1 = min(sp.width, W - x0), min(sp.height, H - y0)
        if a1 <= a0 or b1 <= b0:
            continue
        sp = sp.crop((a0, b0, a1, b1))
        bb = sp.getbbox()
        if not bb:
            continue
        out.append(dict(it, sprite=sp.crop(bb), x=x0 + a0 + bb[0], y=y0 + b0 + bb[1]))
    return out


def _ground_shadow(S, fl, group, gy):
    """A building's hard cast shadow on the village ground (back-right of its foot) and a contact shadow
    along its base."""
    u = S.u
    pts = [p for prt in S.parts if prt['group'] == group and not prt['name'].endswith(('smoke', 'light_beams'))
           for p in prt['lay'] if p[1] >= gy - u(3) and p[1] < gy]
    if not pts:
        return
    x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
    for y in range(gy - u(3), gy):
        for x in range(x1 + 1, x1 + u(6)):
            if (x, y) in fl:
                fl[(x, y)] = darker(fl[(x, y)], 1)
    for x in range(x0, x1 + 1):
        if (x, gy) in fl:
            fl[(x, gy)] = darker(fl[(x, gy)], 1)


# ------------------------------------------------------------------ API
def build(S, name, cx, gy, **opts):
    """Draw building `name` into scene S with its ground centre at (cx, gy); parts are prefixed with
    S.prefix. Adds the snow pass when S.snow."""
    CATALOG[name](S, cx, gy, **opts)
    if S.snow:
        snow_pass(S, S.prefix)


def parts(name, k=1, night=False, snow=False, size='m', seed=0, ground=True, **opts):
    """The building as modes.Parts items (name, sprite, x, y), bottom -> top, positions relative to the
    tight bounding box of all parts."""
    if name == 'village':
        return village(k=k, night=night, snow=snow, seed=seed, **opts)
    S = Scene(k, night, snow, seed, size, ground)
    build(S, name, 0, 0, **opts)
    items, size_ = S.finish()
    return items


def size_of(items):
    return (max(it['x'] + it['sprite'].width for it in items), max(it['y'] + it['sprite'].height for it in items))


def render(name, k=1, **opts):
    """The building as one tight RGBA image (parts composed in order)."""
    items = parts(name, k, **opts)
    W, H = size_of(items)
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    compose(items, img)
    bb = img.getbbox()
    return img.crop(bb) if bb else img


BG = (78, 84, 94, 255)
BG2 = (66, 71, 80, 255)
INK = (232, 228, 216, 255)
INK2 = (168, 174, 184, 255)


def _label(img, x, y, text, c):
    from pixfont import draw_text
    draw_text(img, x, y, text.replace('_', ' '), c)


def chart(path, hd=False):
    """Every building day | night (| snow at k=1), labelled, enlarged x4 (HD x3) on a neutral background,
    then a composed village by day and by night."""
    k = 2 if hd else 1
    z = 3 if hd else 4
    variants = [('day', {}), ('night', {'night': True})] + ([] if hd else [('snow', {'snow': True})])
    cells = []
    for name in CATALOG:
        ims = [render(name, k, **o) for _, o in variants]
        w = sum(im.width * z for im in ims) + 8 * (len(ims) - 1)
        h = max(im.height for im in ims) * z
        cell = Image.new('RGBA', (w + 16, h + 30), BG2)
        x = 8
        for (vn, _), im in zip(variants, ims):
            big = im.resize((im.width * z, im.height * z), Image.NEAREST)
            cell.alpha_composite(big, (x, 8 + h - big.height))
            x += big.width + 8
        _label(cell, 8, h + 14, f'{name}  ({" / ".join(v for v, _ in variants)})', INK)
        cells.append(cell)
    maxw = 1900 if not hd else 2000
    rows, cur, w = [], [], 10
    for c in cells:
        if w + c.width + 10 > maxw and cur:
            rows.append(cur)
            cur, w = [], 10
        cur.append(c)
        w += c.width + 10
    rows.append(cur)
    vk = [village(160 if not hd else 180, 100, seed=3, k=k, night=n) for n in (False, True)]
    vw, vh = (160 if not hd else 180) * k, 100 * k
    vz = 3
    vimgs = []
    for items in vk:
        im = Image.new('RGBA', (vw, vh), (0, 0, 0, 0))
        compose(items, im)
        vimgs.append(im.resize((vw * vz, vh * vz), Image.NEAREST))
    W = max(max(sum(c.width + 10 for c in r) + 10 for r in rows), sum(v.width + 10 for v in vimgs) + 10)
    H = 30 + sum(max(c.height for c in r) + 10 for r in rows) + 30 + max(v.height for v in vimgs) + 20
    img = Image.new('RGBA', (W, H), BG)
    _label(img, 10, 10, f'buildings.py - {len(CATALOG)} buildings, '
           f'{"HD k=2, x3" if hd else "k=1, x4"} - day / night' + ('' if hd else ' / snow'), INK)
    y = 30
    for r in rows:
        x = 10
        for c in r:
            img.alpha_composite(c, (x, y))
            x += c.width + 10
        y += max(c.height for c in r) + 10
    _label(img, 10, y + 8, f'village({vw // k}, 100, seed=3, k={k}) - day / night, x{vz}', INK)
    y += 30
    x = 10
    for v in vimgs:
        img.alpha_composite(v, (x, y))
        x += v.width + 10
    img.save(path)
    return img


def _opts(a):
    o = {}
    if '--night' in a:
        o['night'] = True
    if '--snow' in a:
        o['snow'] = True
    if '--no-ground' in a:
        o['ground'] = False
    for key in ('--size', '--seed', '--width', '--height'):
        if key in a:
            v = a[a.index(key) + 1]
            o[key[2:]] = v if key == '--size' else int(v)
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
        o = _opts(a)
        o.pop('width', None), o.pop('height', None)
        render(a[1], k, **o).save(a[2])
        print(a[1], '->', a[2])
    elif cmd == 'village':
        o = _opts(a)
        w, h = o.pop('width', 160), o.pop('height', 100)
        o.pop('size', None), o.pop('ground', None)
        items = village(w, h, k=k, **o)
        im = Image.new('RGBA', (w * k, h * k), (0, 0, 0, 0))
        compose(items, im)
        im.save(a[1])
        print('village ->', a[1], im.size, len(items), 'parts')
    elif cmd == 'parts':
        name, out = a[1], a[2]
        o = _opts(a)
        if name == 'village':
            w, h = o.pop('width', 160), o.pop('height', 100)
            o.pop('size', None), o.pop('ground', None)
            items, size = village(w, h, k=k, **o), (w * k, h * k)
        else:
            o.pop('width', None), o.pop('height', None)
            items = parts(name, k, **o)
            size = size_of(items)
        layers.save_parts(items, out, size=size)
        layers.write_aseprite(os.path.join(out, f'{name}.aseprite'), items, size)
        im = Image.new('RGBA', size, (0, 0, 0, 0))
        compose(items, im)
        im.save(os.path.join(out, f'{name}.png'))
        print(len(items), 'parts ->', out)
    elif cmd == 'list':
        for n, f in CATALOG.items():
            print(f'{n:15s} {(f.__doc__ or "").strip().splitlines()[0]}')
        print(f'{"village":15s} village(width, height, seed, k): a scene composed of several buildings')
    else:
        sys.exit(__doc__)
