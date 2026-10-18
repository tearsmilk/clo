#!/usr/bin/env python3
"""Nature kit: trees, plants, flowers, crops, rocks, props and terrain patches in a blocky-but-organic
Minecraft-like pixel style, at two densities: k=1 (vanilla GUI density - a block / item is 16x16, a tree
is 2-3 blocks tall) and k=2 ("HD", 32x32 density, drawn natively with more detail: leaf clumps with lit
rims, bark plates, petals, grains, rivets, glints - never upscaled).

Everything is BUILT FROM PARTS (modes.Parts items: each part on its own transparent canvas, kept as a tight
sprite + offset): a tree is ground, shadow, trunk, branches, leaves_back, leaf clusters leaves_1..n, fruit /
blossoms, snow, falling_leaves; '<part>_shadow' parts are the hard shadows a part casts on what is under it
(one ramp step darker), 'shadow' / 'light' parts darken / light the ground. modes.compose builds the picture
again, modes.override moves or hides a part, layers.save_parts / layers.write_aseprite export them.
scatter() composes whole ground strips (forest, plains, desert, snowy, swamp, cherry_grove) the same way.
references/nature.md says how each thing is drawn.

Catalog (76): trees oak, birch, spruce, jungle, acacia, dark_oak, cherry, palm, dead_tree, swamp_oak,
giant_red_mushroom, giant_brown_mushroom (season='spring' | 'summer' | 'autumn' | 'winter', size='s' | 'm' |
'l'); plants bush, berry_bush, rose_bush, tall_grass, fern, dead_bush, poppy, dandelion, cornflower,
blue_orchid, tulip_red / _orange / _white / _pink, allium, lily_of_the_valley, sunflower, red_mushroom,
brown_mushroom; crops wheat, carrots, potatoes, beetroots (age=0..3), pumpkin (carved=True), melon; desert
and water cactus, sugar_cane, bamboo, vines, lily_pad, pond, kelp, coral; rocks rock, mossy_boulder,
coal / iron / copper / gold / redstone / lapis / emerald / diamond _rock, log, stump; fire and light
campfire, soul_campfire, torch, soul_torch, lantern, soul_lantern, hanging_lantern (frame=N animates
flames); signs and fences sign, hanging_sign, fence, fence_gate (open=True, wood=...); props hay_bale,
barrel, crate, chest, beehive; lava_pool, snow_drift, ice_spikes. Every drawable takes seed=N and
ground=False (no island under it).

Shading follows references/texture-shading.md and references/pixel-art-craft.md: one five-tone ramp per
material (shading.ramp5: 0 outline, 1 shadow, 2 dark mid, 3 base, 4 light mid, 5 highlight; matte
materials soft, metal / gems / fire contrasty), light from the top-left, selective outlines in the
material's own dark tone (pixel-perfect), hard cast + contact shadows, clusters instead of noise, no
gradients, no dithering, no semi-transparent pixels.

    from nature import render, parts, scatter, CATALOG
    img = render('oak', k=2, season='autumn')          # tight RGBA
    items = parts('cherry', k=1)                       # modes.Parts items, bottom -> top
    items = scatter(160, 72, 'forest', seed=3, k=1)    # a ground strip as parts (canvas 160x72 * k)

    python3 nature.py chart OUT.png [--hd]             everything, the oak's four seasons, a scatter per biome
    python3 nature.py render NAME OUT.png [--hd] [--season S] [--seed N] [--size s|m|l] [--no-ground]
    python3 nature.py parts NAME OUT_DIR [--hd] [...]  PNG per part + layers.json + _sheet.png + .aseprite
    python3 nature.py scatter BIOME OUT.png [--hd] [--width W --height H --seed N]
    python3 nature.py list
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
from shading import pixel_perfect, doubles, _is_double, _lum   # noqa: E402
from collections import Counter                           # noqa: E402
import layers                                             # noqa: E402

O, SH, DK, BS, LT, HI = range(6)                          # tone indices into a ramp
N8 = ((-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1))
SEASONS = ('spring', 'summer', 'autumn', 'winter')

# ------------------------------------------------------------------ ramps (outline, shadow, dark, base, light, hi)
RAMPS = {}


def _ramp(key, hexc, soft=0.7, **kw):
    """Declare a ramp: RAMPS[key] and a module global KEY (so `shading.py check --kit nature` sees it)."""
    r = _r5(hexc, soft=soft, **kw)
    RAMPS[key] = r
    globals()[key.upper()] = r
    return r


def _ramp_hex(key, hexes):
    """A hand-set ramp (outline, shadow, dark, base, light, highlight) for emissive things: ramp5 turns the
    lights pale, fire and lava keep saturated yellow lights (hue shifted toward yellow, not toward white)."""
    r = [tuple(int(h.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4)) + (255,) for h in hexes]
    RAMPS[key] = r
    globals()[key.upper()] = r
    return r


# ground
_ramp('grass', '#62a83e', 0.6)
_ramp('grass_dry', '#a0a84a', 0.6)        # savanna / plains in late summer
_ramp('swamp_grass', '#5a7a3a', 0.6)
_ramp('dirt', '#8a5c3a', 0.7)
_ramp('podzol', '#6c4a2a', 0.7)
_ramp('mud', '#5a4838', 0.7)
_ramp('sand', '#e2cc92', 1.0)
_ramp('sandstone', '#cfb27a', 0.9)
_ramp('red_sand', '#c8783a', 0.8)
_ramp('snow', '#e8f0f6', 1.0)
_ramp('ice', '#8ccaea', 0.4)
_ramp('packed_ice', '#a6c4ee', 0.5)
_ramp('stone', '#8c8e94', 0.7)
_ramp('deepslate', '#585a64', 0.7)
_ramp('gravel', '#8c8884', 1.0)
_ramp('moss', '#5e9036', 0.6)
_ramp('farmland', '#6a4630', 0.8)
_ramp('farmland_wet', '#4e3424', 0.8)
_ramp('water', '#3e78cc', 0.4)
_ramp('water_swamp', '#4a7a6a', 0.5)
_ramp_hex('lava', ['#4a1408', '#8a240c', '#c8400e', '#f07020', '#ffa828', '#ffe060'])
_ramp('lava_crust', '#5a2a22', 0.6)
_ramp('pink_petals', '#f2a6c8', 0.5)
# bark, wood
_ramp('oak_bark', '#6e5434', 0.7)
_ramp('birch_bark', '#e8e4d8', 1.0)
_ramp('birch_mark', '#3c3834', 0.8)
_ramp('spruce_bark', '#4f3a26', 0.7)
_ramp('jungle_bark', '#66502a', 0.7)
_ramp('acacia_bark', '#6e6862', 0.8)
_ramp('acacia_wood', '#bc6232', 0.7)
_ramp('dark_oak_bark', '#40301e', 0.7)
_ramp('cherry_bark', '#4e2c34', 0.7)
_ramp('palm_bark', '#a08052', 0.8)
_ramp('dead_bark', '#6e6458', 0.8)
_ramp('log_end', '#c49a5e', 0.8)
_ramp('oak_plank', '#b48a52', 0.7)
_ramp('spruce_plank', '#7c5834', 0.7)
_ramp('birch_plank', '#d6c482', 0.8)
_ramp('dark_oak_plank', '#5a3c22', 0.7)
_ramp('chest_wood', '#a8743a', 0.7)
_ramp('hive_wood', '#c89a56', 0.7)
# leaves (summer) + seasonal variants
_ramp('oak_leaf', '#4c9638', 0.6)
_ramp('oak_leaf_spring', '#78c046', 0.6)
_ramp('oak_leaf_autumn', '#d8862a', 0.5)
_ramp('leaf_red', '#c4482c', 0.5)
_ramp('leaf_yellow', '#e2b436', 0.5)
_ramp('oak_leaf_winter', '#557a52', 0.8)
_ramp('birch_leaf', '#78aa3c', 0.6)
_ramp('birch_leaf_spring', '#a2cc56', 0.6)
_ramp('birch_leaf_autumn', '#e6c03a', 0.5)
_ramp('spruce_leaf', '#3a6a48', 0.6)
_ramp('spruce_leaf_spring', '#4a8050', 0.6)
_ramp('jungle_leaf', '#3a9a2c', 0.5)
_ramp('jungle_leaf_spring', '#5ab43a', 0.5)
_ramp('jungle_leaf_autumn', '#8ea42a', 0.5)
_ramp('acacia_leaf', '#7c9c2e', 0.6)
_ramp('acacia_leaf_autumn', '#c8a032', 0.5)
_ramp('dark_oak_leaf', '#2e6a2c', 0.6)
_ramp('dark_oak_leaf_spring', '#3e8436', 0.6)
_ramp('dark_oak_leaf_autumn', '#a85a2a', 0.5)
_ramp('cherry_leaf', '#f0a2c4', 0.5)
_ramp('cherry_leaf_autumn', '#e07a5a', 0.5)
_ramp('palm_leaf', '#5aa63a', 0.5)
_ramp('swamp_leaf', '#5a7a34', 0.6)
_ramp('winter_leaf', '#4e6e56', 0.8)
# mushrooms
_ramp('red_cap', '#c8302c', 0.5)
_ramp('brown_cap', '#a87850', 0.7)
_ramp('mush_stem', '#ddd0b2', 0.6)
_ramp('gills', '#c4a48a', 0.9)
_ramp('cream', '#f0e6cc', 1.0)
# plants and flowers
_ramp('plant', '#55a03c', 0.6)            # flower stems and leaves
_ramp('blade', '#6cb444', 0.6)            # tall grass
_ramp('fern', '#4a8c3e', 0.6)
_ramp('dry_plant', '#a07c48', 0.8)        # dead bush
_ramp('poppy', '#d83038', 0.4)
_ramp('dandelion', '#f0cc30', 0.4)
_ramp('cornflower', '#4a6ee0', 0.4)
_ramp('orchid', '#38aee8', 0.4)
_ramp('tulip_red', '#dc3a2e', 0.4)
_ramp('tulip_orange', '#ec8a26', 0.4)
_ramp('tulip_white', '#ecece4', 0.9)
_ramp('tulip_pink', '#ec8cb4', 0.4)
_ramp('allium', '#a85ad6', 0.4)
_ramp('lily_white', '#f2f2ea', 1.0)
_ramp('sunflower', '#f4c42a', 0.4)
_ramp('seeds', '#6a4422', 0.6)
_ramp('cocoa', '#a65a2a', 0.5)
_ramp('rose', '#c42838', 0.4)
_ramp('berry', '#c8283c', 0.3)
# crops
_ramp('wheat', '#e0b040', 0.5)
_ramp('stalk', '#8eb03c', 0.6)
_ramp('carrot', '#f07a14', 0.4)
_ramp('potato', '#c89a54', 0.6)
_ramp('beet', '#a82640', 0.4)
_ramp('crop_leaf', '#4e9c38', 0.6)
_ramp('pumpkin', '#e07a1c', 0.5)
_ramp('pumpkin_stem', '#6a7a2c', 0.6)
_ramp('melon', '#5a9c2a', 0.5)
_ramp('melon_stripe', '#3a6a22', 0.6)
_ramp('hay', '#d6b048', 0.6)
_ramp('hay_band', '#8a4a2c', 0.6)
# desert / water plants
_ramp('cactus', '#4f8e34', 0.5)
_ramp('cane', '#8ac84a', 0.6)
_ramp('bamboo', '#78ac2c', 0.5)
_ramp('vine', '#3e7e2c', 0.6)
_ramp('lily_pad', '#3e8e38', 0.6)
_ramp('kelp', '#5c8c2a', 0.6)
_ramp('reed', '#7e9a46', 0.7)
_ramp('cattail', '#6a4628', 0.7)
_ramp('lotus', '#f0a0c0', 0.5)
_ramp('kelp_bulb', '#b0b83a', 0.5)
_ramp('stone_lit', '#c09070', 0.6)
_ramp('cactus_flower', '#e870a8', 0.4)
_ramp('coral_tube', '#3a5ae6', 0.4)
_ramp('coral_brain', '#e868a8', 0.4)
_ramp('coral_bubble', '#a83ae0', 0.4)
_ramp('coral_fire', '#e03a3a', 0.4)
_ramp('coral_horn', '#e8cc3a', 0.4)
# metal, gems, fire, light (contrasty)
_ramp('iron', '#8e939c', 0.0)
_ramp('dark_iron', '#4a4c58', 0.0)
_ramp('gold', '#e8b830', 0.0)
_ramp('coal', '#34343c', 0.3)
_ramp('iron_ore', '#d8a888', 0.3)
_ramp('diamond', '#4ae0d8', 0.0)
_ramp('emerald', '#2ed060', 0.0)
_ramp('redstone', '#e02626', 0.1)
_ramp('lapis', '#2a4ccc', 0.1)
_ramp('copper', '#e07a4a', 0.2)
_ramp('copper_green', '#4aa88a', 0.4)
_ramp_hex('fire', ['#5a1808', '#a02c0c', '#d8501a', '#f48a24', '#ffc038', '#fff0a0'])
_ramp_hex('soul_fire', ['#06343e', '#0c6a80', '#1aa0c0', '#38d0e8', '#90f0f8', '#e8ffff'])
_ramp_hex('glow', ['#4a2a0a', '#8a5a1a', '#d08a2a', '#f4b440', '#ffd870', '#fff4c0'])
_ramp_hex('soul_glow', ['#06343e', '#0c6a80', '#20a8c8', '#4ad8ea', '#a0f4fa', '#eaffff'])
_ramp_hex('ember', ['#3a0a04', '#7a1a08', '#b8300c', '#e8501a', '#ff8a30', '#ffc860'])
_ramp('ash', '#6a6670', 1.0)
_ramp('smoke', '#c6c6cc', 1.0)
_ramp('honey', '#f2b21c', 0.3)
_ramp('bee', '#f2c42a', 0.3)
_ramp('bee_dark', '#3a2c22', 0.6)
_ramp('wing', '#dcecf4', 1.0)
_ramp('paper', '#e6d6b0', 1.0)
_ramp('rope', '#b89a68', 1.0)

# light sources keep their colours in shadow (cast shadows never darken them)
EMISSIVE = {c for r in (LAVA, FIRE, SOUL_FIRE, GLOW, SOUL_GLOW, EMBER) for c in r[1:]}  # noqa: F821
_RAMP_OF = {}
for _n, _r in RAMPS.items():
    for _i, _c in enumerate(_r):
        _RAMP_OF.setdefault(_c, (_r, _i))
OUTLINES = {r[O] for r in RAMPS.values()}
LINES = OUTLINES | {r[SH] for r in RAMPS.values()}      # 1 px lines kept pixel-perfect


def _cl(v):
    return max(0, min(255, int(round(v))))


def darker(c, n=1):
    """n ramp steps darker (the shadow tone stays the floor; the outline is never reached by shading)."""
    if c in _RAMP_OF:
        r, i = _RAMP_OF[c]
        return r[O] if i <= SH else r[max(SH, i - n)]
    return (_cl(c[0] * 0.72), _cl(c[1] * 0.72), _cl(c[2] * 0.8), 255)


def lighter(c, n=1):
    if c in _RAMP_OF:
        r, i = _RAMP_OF[c]
        return r[min(HI, max(SH, i) + n)]
    return c


def tone_of(c):
    return _RAMP_OF[c][1] if c in _RAMP_OF else None


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
        for p in pts:
            if p not in self:
                self.put(p[0], p[1], c)


def rect(x0, y0, x1, y1):
    """Inclusive pixel rectangle."""
    return {(x, y) for y in range(int(y0), int(y1) + 1) for x in range(int(x0), int(x1) + 1)}


def disc(cx, cy, r, ry=None):
    ry = ry or r
    return {(x, y) for y in range(int(math.floor(cy - ry - 1)), int(cy + ry + 2))
            for x in range(int(math.floor(cx - r - 1)), int(cx + r + 2))
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


def line(x0, y0, x1, y1):
    """A clean 1 px line (no doubles): Bresenham-like, one pixel per major-axis step."""
    n = max(abs(x1 - x0), abs(y1 - y0), 1)
    return [(int(round(x0 + (x1 - x0) * i / n)), int(round(y0 + (y1 - y0) * i / n))) for i in range(n + 1)]


def bezier(p0, p1, p2, n=None):
    """Points of a quadratic curve, one per pixel step (for stems, fronds, branches)."""
    n = n or int(max(abs(p2[0] - p0[0]), abs(p2[1] - p0[1]), 2) * 2)
    out = []
    for i in range(n + 1):
        t = i / n
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
        q = (int(round(x)), int(round(y)))
        if not out or out[-1] != q:
            out.append(q)
    return _thin(out)


def _thin(path):
    """Drop the corner pixel of every L in a 1 px path (pixel-perfect)."""
    out = []
    for p in path:
        out.append(p)
        while len(out) >= 3:
            a, b, c = out[-3], out[-2], out[-1]
            if abs(a[0] - c[0]) == 1 and abs(a[1] - c[1]) == 1 and (b[0] == a[0] or b[1] == a[1]):
                out.pop(-2)
            else:
                break
    return out


def outline(lay, mask, R, over=False, lit=None, dark=None, skip=None, lit_side=True):
    """Selective outline in the material's own tones round `mask`: R[SH] on the lit top / left side of the
    silhouette, R[O] on the shadow side and below. Pixels already in the layer are kept unless over=True;
    `skip` = pixels never outlined (where the part touches the ground or another part)."""
    mask = set(mask)
    lit = R[SH] if lit is None else lit
    dark = R[O] if dark is None else dark
    for (x, y) in edge_ring(mask):
        if ((x, y) in lay and not over) or (skip and (x, y) in skip):
            continue
        is_lit = ((x, y + 1) in mask or (x + 1, y) in mask) and not ((x, y - 1) in mask or (x - 1, y) in mask)
        if is_lit and not lit_side:
            continue
        lay[(x, y)] = lit if is_lit else dark
    return mask


def perfect_ring(mask):
    """The 4-neighbour outline ring of a mask without L-corner doubles (shading.pixel_perfect on it as one
    line), so it stays clean when its pixels are split between parts."""
    ring = edge_ring(set(mask))
    if not ring:
        return ring
    x0, y0, x1, y1 = bbox(ring)
    im = Image.new('RGBA', (x1 - x0 + 3, y1 - y0 + 3), (0, 0, 0, 0))
    px = im.load()
    for (x, y) in mask:
        if x0 <= x <= x1 and y0 <= y <= y1:
            px[x - x0 + 1, y - y0 + 1] = (200, 200, 200, 255)
    for (x, y) in ring:
        px[x - x0 + 1, y - y0 + 1] = (1, 2, 3, 255)
    pixel_perfect(im, only={(1, 2, 3, 255)})
    return {(x, y) for (x, y) in ring if px[x - x0 + 1, y - y0 + 1] == (1, 2, 3, 255)}


def sphere_tone(nx, ny, cuts=(0.86, 0.58, 0.2, -0.12)):
    """Tone index on a ball / dome at normalised (nx, ny), lit from the top-left-front; compressed bands
    (narrow highlight and terminator, wide base and light)."""
    r2 = nx * nx + ny * ny
    nz = math.sqrt(max(0.0, 1 - r2))
    lam = (-0.55 * nx - 0.62 * ny + 0.56 * nz) / 0.999
    return HI if lam > cuts[0] else LT if lam > cuts[1] else BS if lam > cuts[2] else DK if lam > cuts[3] else SH


def cyl_tone(nx, cuts=(1.1, 0.95, 0.45, 0.0)):
    """Tone across a vertical cylinder (trunk, stem, barrel): nx -1 (left) .. 1 (right)."""
    nx = max(-1.0, min(1.0, nx))
    nz = math.sqrt(max(0.0, 1 - nx * nx))
    lam = -0.62 * nx + 0.2 + 0.7 * nz
    return HI if lam > cuts[0] else LT if lam > cuts[1] else BS if lam > cuts[2] else DK if lam > cuts[3] else SH


def blob(rnd, n, wide=1.0, tall=1.0):
    """A compact random cluster of n pixels round (0, 0) (texture chips, leaf tufts)."""
    pts = {(0, 0)}
    while len(pts) < n:
        x, y = rnd.choice(sorted(pts))
        dx, dy = rnd.choice(((1, 0), (-1, 0), (0, 1), (0, -1)))
        if abs(x + dx) <= 3 * wide and abs(y + dy) <= 3 * tall:
            pts.add((x + dx, y + dy))
    return pts


# ------------------------------------------------------------------ the scene builder
def _dark_doubles(im, passes=3):
    """L-corners whose pixel is darker than its surroundings on average (the shading.check criterion for a
    dark line: texture strokes between two lighter tones) - the corner pixel takes the colour outside."""
    W, H = im.size
    px = im.load()
    for _ in range(passes):
        n = 0
        for (x, y) in doubles(px, W, H):
            o = [_lum(px[x + dx, y + dy]) for dx, dy in N8 if 0 <= x + dx < W and 0 <= y + dy < H
                 and px[x + dx, y + dy][3] == 255 and px[x + dx, y + dy] != px[x, y]]
            if o and _lum(px[x, y]) >= 0.8 * sum(o) / len(o):
                continue
            hv = _is_double(px, W, H, x, y)
            if not hv:
                continue
            h, v = hv
            out = [px[q] for q in ((x - h, y), (x, y - v), (x - h, y - v)) if 0 <= q[0] < W and 0 <= q[1] < H]
            out = [c for c in out if c != px[x, y]] or [(0, 0, 0, 0)]
            px[x, y] = Counter(out).most_common(1)[0][0]
            n += 1
        if not n:
            break


def _clean_layer(lay):
    """Pixel-perfect one part: L-corners in its 1 px outlines / shadow lines and in dark strokes of any
    colour (leaf marks, cracks) - the corner pixel takes the colour outside the corner."""
    if not lay:
        return
    x0, y0, x1, y1 = bbox(list(lay))
    im = Image.new('RGBA', (x1 - x0 + 1, y1 - y0 + 1), (0, 0, 0, 0))
    px = im.load()
    for (x, y), c in lay.items():
        px[x - x0, y - y0] = c
    before = im.copy()
    pixel_perfect(im, only=LINES)
    pixel_perfect(im)
    bp = before.load()
    for y in range(im.height):
        for x in range(im.width):
            if px[x, y] != bp[x, y]:
                if px[x, y][3] == 0:
                    lay.pop((x + x0, y + y0), None)
                else:
                    lay[(x + x0, y + y0)] = px[x, y]


class Scene:
    """Collects the parts of one drawable (or a whole scatter strip) as Layers with a z order; finish() adds
    the cast and ground shadows and returns modes.Parts items."""

    def __init__(self, k=1, seed=0, season='summer', ground=True):
        self.k, self.seed, self.season, self.ground = k, seed, season, ground
        self.parts, self.prefix, self.zbase = [], '', 0

    def u(self, n):
        """GUI units -> pixels at this density (geometry only; details are drawn per density)."""
        return int(round(n * self.k))

    def kv(self, a, b):
        return a if self.k == 1 else b

    def rnd(self, *salt):
        return random.Random(_crc(self.seed, self.prefix, *salt))

    def lay(self, name, z=0, cast=None):
        """The named part's Layer (created on first use), so several features can draw into one part.
        cast = (dx, dy, steps): the part throws a hard shadow (swept along the offset) on what is under it."""
        full = self.prefix + name
        for p in self.parts:
            if p['name'] == full:
                return p['lay']
        lay = Layer()
        self.parts.append({'name': full, 'lay': lay, 'z': z + self.zbase, 'cast': cast, 'shade': None,
                           'n': len(self.parts)})
        return lay

    def shade(self, name, mask, z=-50):
        """A shadow part: every pixel of `mask` ({(x, y): steps}) darkens what is under it when finished
        (ground shadows of trees and props, contact shadows)."""
        full = self.prefix + name
        for p in self.parts:
            if p['name'] == full:
                for q, s in mask.items():
                    o = p['shade'].get(q, 0)
                    p['shade'][q] = max(s, o) if s > 0 else min(s, o)
                return
        self.parts.append({'name': full, 'lay': Layer(), 'z': z + self.zbase, 'cast': None, 'shade': dict(mask),
                           'n': len(self.parts)})

    def glow(self, name, mask, z=-40):
        """A light pool: every pixel of `mask` ({(x, y): steps}) turns `steps` ramp tones lighter on what is
        under it (the ground round a fire or a lava pool) - hard stepped bands, no blur."""
        self.shade(name, {q: -s for q, s in mask.items()}, z=z)

    def remove(self, name):
        self.parts = [p for p in self.parts if p['name'] != self.prefix + name]

    def mask_of(self, *names):
        out = set()
        for p in self.parts:
            if p['name'] in [self.prefix + n for n in names]:
                out |= set(p['lay'])
        return out

    @staticmethod
    def _perfect(out, comp):
        """Pixel-perfect over the whole composite (L-corners that two parts make together - a cast shadow
        meeting a rim, a limb meeting the trunk): each fix goes into the topmost part owning that pixel."""
        if not comp:
            return
        x0, y0, x1, y1 = bbox(list(comp))
        im = Image.new('RGBA', (x1 - x0 + 1, y1 - y0 + 1), (0, 0, 0, 0))
        px = im.load()
        for (x, y), c in comp.items():
            px[x - x0, y - y0] = c
        before = im.copy()
        pixel_perfect(im, only=LINES)
        pixel_perfect(im)
        _dark_doubles(im)
        bp = before.load()
        for y in range(im.height):
            for x in range(im.width):
                if px[x, y] != bp[x, y]:
                    q = (x + x0, y + y0)
                    for name, lay in reversed(out):
                        if q in lay:
                            if px[x, y][3] == 0:
                                for _, l2 in out:
                                    l2.pop(q, None)
                            else:
                                lay[q] = px[x, y]
                            break

    def finish(self, size=None, clip=None):
        """-> (items, (W, H)). Without size the canvas is the tight box of all parts; with size=(W, H) the
        scene coordinates are canvas coordinates and everything outside is clipped."""
        parts = sorted(self.parts, key=lambda p: (p['z'], p['n']))
        comp = {}
        out = []
        for p in parts:
            lay = p['lay']
            if p['shade'] is not None:
                sh = Layer()
                for q, s in p['shade'].items():
                    if q in comp and comp[q] not in EMISSIVE:
                        sh[q] = darker(comp[q], s) if s > 0 else lighter(comp[q], -s)
                if sh:
                    out.append((p['name'], sh))
                    comp.update(sh)
                continue
            _clean_layer(lay)
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
                    out.append((p['name'] + '_shadow', sh))
                    comp.update(sh)
            if lay:
                out.append((p['name'], lay))
                comp.update(lay)
        self._perfect(out, comp)
        if size:
            W, H = size
            x0 = y0 = 0
        else:
            allpx = [q for _, lay in out for q in lay]
            if not allpx:
                return [], (0, 0)
            x0, y0, x1, y1 = bbox(allpx)
            W, H = x1 - x0 + 1, y1 - y0 + 1
        P = Parts(W, H)
        for name, lay in out:
            def draw(im, lay=lay):
                px = im.load()
                for (x, y), c in lay.items():
                    X, Y = x - x0, y - y0
                    if 0 <= X < W and 0 <= Y < H:
                        px[X, Y] = c
            P.add(name, draw)
        self.origin = (x0, y0)
        return P.items, (W, H)


# ------------------------------------------------------------------ ground patch
GROUND = {'grass': (GRASS, DIRT), 'dry': (GRASS_DRY, DIRT), 'swamp': (SWAMP_GRASS, MUD),     # noqa: F821
          'dirt': (DIRT, DIRT), 'podzol': (PODZOL, DIRT), 'mud': (MUD, MUD),                  # noqa: F821
          'sand': (SAND, SANDSTONE), 'red_sand': (RED_SAND, SANDSTONE), 'snow': (SNOW, DIRT),  # noqa: F821
          'stone': (STONE, STONE), 'gravel': (GRAVEL, STONE), 'farmland': (FARMLAND, DIRT),    # noqa: F821
          'seabed': (SAND, SANDSTONE), 'moss': (MOSS, DIRT)}                                    # noqa: F821


def ground_kind(S, kind):
    return 'snow' if S.season == 'winter' and kind in ('grass', 'dry', 'podzol', 'dirt', 'moss') else kind


def surface(S, lay, top, kind, seed=0):
    """Texture of a ground top face (seen from slightly above): base tone, a lit far edge, clusters along
    the rows (grass tufts, sand ripples, snow sparkle, pebbles) - no noise, no gradient."""
    Rs = GROUND[kind][0]
    k = S.k
    rnd = S.rnd('surface', kind, seed)
    for (x, y) in top:
        c = Rs[BS]
        if (x, y - 1) not in top or (x - 1, y) not in top:
            c = Rs[LT]
        lay[(x, y)] = c
    pts = sorted(top)
    rnd.shuffle(pts)
    n = int(len(pts) * S.kv(0.07, 0.06))
    for (x, y) in pts[:n]:
        if (x, y - 1) not in top or (x, y + 1) not in top:
            continue
        if kind in ('grass', 'dry', 'swamp', 'moss'):          # tufts: a lit blade over a dark root
            L = S.kv(2, rnd.randint(2, 3))
            for i in range(L):
                if (x + i, y) in top:
                    lay[(x + i, y)] = Rs[LT] if i < L - 1 else Rs[BS]
                if (x + i, y + 1) in top and i < L - 1:
                    lay[(x + i, y + 1)] = Rs[DK]
        elif kind in ('sand', 'red_sand', 'seabed'):           # ripples: short dark strokes with a lit lip
            L = rnd.randint(2, S.kv(3, 5))
            for i in range(L):
                if (x + i, y) in top:
                    lay[(x + i, y)] = Rs[DK]
                if (x + i + 1, y - 1) in top and i < L - 1:
                    lay[(x + i + 1, y - 1)] = Rs[LT]
        elif kind == 'snow':                                   # soft dents with a blue shadow, sparkles
            if rnd.random() < 0.3:
                lay[(x, y)] = Rs[HI]
                if (x + 1, y) in top:
                    lay[(x + 1, y)] = Rs[HI]
            else:
                for i in range(S.kv(2, 3)):
                    if (x + i, y) in top:
                        lay[(x + i, y)] = Rs[DK] if i else Rs[BS]
        else:                                                  # dirt, stone, gravel: pebbles / clods
            for (a, b) in ((0, 0), (1, 0)) if k == 1 else ((0, 0), (1, 0), (0, 1), (1, 1)):
                if (x + a, y + b) in top:
                    lay[(x + a, y + b)] = Rs[DK] if b or a else Rs[LT]
            if (x + 2, y + 1) in top:
                lay[(x + 2, y + 1)] = Rs[DK]


def ground_patch(S, x0, x1, gy, kind='grass', back=None, front=None, depth=None, name='ground', z=-100):
    """The little island a drawable stands on: a top face `back` rows behind the base line gy and `front`
    rows in front of it (seen from slightly above), a front face of the soil below with the top material
    hanging over its edge in an uneven fringe; rounded ends. Returns the top-face pixels."""
    k = S.k
    kind = ground_kind(S, kind)
    Rs, Rf = GROUND[kind]
    back = S.u(2) if back is None else back
    front = S.u(4) if front is None else front
    depth = S.kv(3, 6) if depth is None else depth
    lay = S.lay(name, z)
    rnd = S.rnd('ground', x0, x1)
    ytop, yf = gy - back, gy + front
    cut = S.kv(2, 3)
    top = set()
    for (x, y) in rect(x0, ytop, x1, yf - 1):
        e = min(x - x0, x1 - x)
        r = min(y - ytop, yf - 1 - y)
        if e + r * 2 < cut:
            continue
        top.add((x, y))
    surface(S, lay, top, kind, seed=x0)
    face = set()
    for x in range(x0, x1 + 1):
        e = min(x - x0, x1 - x)
        d = depth - (1 if e < S.kv(1, 2) else 0) - (1 if e < S.kv(2, 4) and k == 2 else 0)
        for j in range(d):
            face.add((x, yf + j))
    for (x, y) in face:
        j = y - yf
        t = BS if j < depth - S.kv(1, 2) else DK
        if x - x0 < S.kv(1, 2):
            t = LT
        lay[(x, y)] = Rf[t]
    if Rf is not Rs or kind in ('stone', 'snow'):              # the top material hangs over the face
        for x in range(x0, x1 + 1):
            drip = S.kv(1, 2) + (rnd.random() < 0.35) * S.kv(1, 2)
            for j in range(drip):
                if (x, yf + j) in face:
                    lay[(x, yf + j)] = Rs[DK] if j == drip - 1 else Rs[BS]
        for (x, y) in sorted(face):                             # stones / roots in the soil
            if y - yf >= S.kv(2, 4) and rnd.random() < S.kv(0.08, 0.05) and (x + 1, y) in face:
                lay[(x, y)] = Rf[LT]
                lay[(x + 1, y)] = Rf[DK]
    outline(lay, top | face, Rf, lit=Rs[DK])
    return top


def ground_shadow(S, x0, x1, gy, rows=None, name='shadow', contact=None, steps=1):
    """The shadow a standing object throws on the ground: light from the top-left, so it falls to the right
    along the surface - a flat lens from x0 to x1 round the base line gy (hard edge, one tone), plus an
    optional contact line (x0, x1) right under the base two steps darker (ambient occlusion)."""
    rows = rows or S.kv(2, 4)
    m = {}
    cx, rx = (x0 + x1) / 2, max(1.0, (x1 - x0 + 1) / 2)
    for x in range(x0, x1 + 1):
        t = (x + 0.5 - cx) / rx
        h = max(1, int(round(rows * math.sqrt(max(0.0, 1 - t * t)) + 0.3)))
        for j in range(h):
            m[(x, gy - h // 2 + j)] = steps
    if contact:
        for x in range(contact[0], contact[1] + 1):
            m[(x, gy)] = steps + 1
    S.shade(name, m)


# ------------------------------------------------------------------ trees: trunk, bark, branches
def _spans(m):
    """{y: (left x, right x)} of a mask."""
    out = {}
    for x, y in m:
        a, b = out.get(y, (x, x))
        out[y] = (min(a, x), max(b, x))
    return out


def bark(S, lay, m, R, style='furrow', seed=0, hi=True):
    """Bark on a trunk / limb mask. Every row is shaded like a cylinder (lit left, base, dark right, a narrow
    shadow on the far edge), then the style draws its texture as clusters along the grain:
      furrow  - vertical dashed furrows one step darker, a lit ridge left of each (oak, spruce, dark oak)
      birch   - white bark with black horizontal dashes and eye marks
      smooth  - fine horizontal lenticel strokes (cherry)
      rings   - horizontal ring scars every few rows, lit on top (palm)
      plates  - irregular plates outlined by darker cracks (acacia, dead wood)"""
    k = S.k
    rnd = S.rnd('bark', style, seed)
    sp = _spans(m)
    for (x, y) in m:
        xl, xr = sp[y]
        w = xr - xl + 1
        nx = ((x - xl) + 0.5) / w * 2 - 1
        t = cyl_tone(nx)
        if t == HI and (not hi or k == 1 or w < 6):
            t = LT
        if w <= 2:
            t = LT if x == xl else DK
        lay[(x, y)] = R[t]
    ys = sorted(sp)
    if style in ('furrow', 'plates'):
        nf = max(1, int(sum(sp[y][1] - sp[y][0] + 1 for y in ys) / len(ys) / S.kv(2.4, 3.2)))
        fr = [(i + 0.5 + rnd.uniform(-0.25, 0.25)) / nf for i in range(nf)]
        for f in fr:
            y = ys[0] + rnd.randint(0, S.kv(2, 4))
            while y <= ys[-1]:
                run = rnd.randint(S.kv(2, 3), S.kv(5, 9))
                wob = rnd.choice((-1, 0, 0, 1)) if k == 2 else 0
                for j in range(run):
                    yy = y + j
                    if yy not in sp:
                        break
                    xl, xr = sp[yy]
                    w = xr - xl + 1
                    if w < 3:
                        continue
                    x = xl + int(f * w) + (wob if j > run // 2 else 0)
                    if not xl < x < xr:
                        continue
                    c = lay[(x, yy)]
                    t = tone_of(c)
                    lay[(x, yy)] = R[max(SH, t - 2)] if t > SH else R[O]
                    if k == 2 and (x - 1, yy) in m and x - 1 > xl and t >= BS:
                        lay[(x - 1, yy)] = R[min(HI if hi else LT, t + 1)]
                y += run + rnd.randint(1, S.kv(2, 3))
        if style == 'plates':                                  # cross cracks between the furrows
            for _ in range(len(ys) // S.kv(4, 5)):
                yy = rnd.choice(ys)
                xl, xr = sp[yy]
                for x in range(xl + 1, xr):
                    if rnd.random() < 0.6:
                        t = tone_of(lay[(x, yy)])
                        lay[(x, yy)] = R[max(SH, t - 1)]
    elif style == 'birch':
        for y in ys:
            if rnd.random() < S.kv(0.22, 0.18):
                xl, xr = sp[y]
                w = xr - xl + 1
                a = xl + rnd.randint(0, max(0, w // 2))
                L = rnd.randint(1, max(1, w - (a - xl)))
                for x in range(a, a + L):
                    if (x, y) in m:
                        lay[(x, y)] = BIRCH_MARK[DK if x < xl + w // 2 else SH]   # noqa: F821
                        if k == 2 and (x, y + 1) in m and rnd.random() < 0.5:
                            lay[(x, y + 1)] = BIRCH_MARK[SH]                      # noqa: F821
    elif style == 'smooth':
        for y in ys[1::S.kv(3, 4)]:
            xl, xr = sp[y]
            a = xl + rnd.randint(1, 2)
            for x in range(a, min(xr, a + rnd.randint(1, S.kv(2, 4)))):
                t = tone_of(lay[(x, y)])
                lay[(x, y)] = R[max(SH, t - 1)]
    elif style == 'rings':
        for y in ys:
            if (y - ys[0]) % S.kv(3, 5) == 0:
                xl, xr = sp[y]
                for x in range(xl, xr + 1):
                    t = tone_of(lay[(x, y)])
                    lay[(x, y)] = R[max(SH, t - 1)]
                    if (x, y - 1) in m and x < (xl + xr) / 2 and k == 2:
                        lay[(x, y - 1)] = R[min(LT, t + 1)]


def trunk(S, cx, y_top, gy, w_bot, w_top, R, name='trunk', z=5, roots=None, seed=0, lean=None, style='furrow',
          cast=None):
    """A trunk from the ground line gy up to y_top: width w_bot -> w_top, lean(t) shifts it sideways (t = 0 at
    the top, 1 at the ground), a flared foot with roots gripping the ground. Shaded with bark(). Returns the
    mask."""
    k = S.k
    lay = S.lay(name, z, cast=cast)
    m = set()
    H = max(1, gy - y_top)
    for y in range(y_top, gy + 1):
        t = (y - y_top) / H
        w = w_top + (w_bot - w_top) * t
        off = lean(t) if lean else 0
        xl = int(round(cx + off - w / 2))
        for x in range(xl, xl + max(1, int(round(w)))):
            m.add((x, y))
    bark(S, lay, m, R, style=style, seed=seed)
    if roots is not False:
        roots_ = globals()['roots']
        roots_(S, lay, int(round(cx + (lean(1) if lean else 0))), gy, int(round(w_bot)), R, m, n=roots, seed=seed)
    outline(lay, m, R, skip={(x, gy + 1) for x in range(-999, 999)})
    return m


def limb(S, lay, path, w0, w1, R, m=None, shade=True):
    """A branch along a 1 px path, thickness w0 -> w1 (pixels). Adds to mask m (several limbs share one
    mask and are shaded together with shade_wood, so where they join there is no seam)."""
    m = set() if m is None else m
    n = len(path)
    for i, (x, y) in enumerate(path):
        w = w0 + (w1 - w0) * i / max(1, n - 1)
        r = max(0.5, w / 2)
        if w < 1.5:
            m.add((x, y))
        else:
            m |= disc(x + 0.5 - (0.5 if int(round(w)) % 2 == 0 else 0), y + 0.5, r)
    if shade:
        shade_wood(S, lay, m, R)
    return m


def shade_wood(S, lay, m, R, grain=True, seed=0):
    """Thin wooden forms (limbs, twigs, stems, poles): lit on the top / left edge, dark on the bottom / right
    edge, base inside; HD adds short bark streaks along the length."""
    rnd = S.rnd('wood', seed, len(m))
    for (x, y) in m:
        up, lf = (x, y - 1) not in m, (x - 1, y) not in m
        dn, rt = (x, y + 1) not in m, (x + 1, y) not in m
        t = BS
        if (up or lf) and not (dn or rt):
            t = LT
        elif (dn or rt) and not (up or lf):
            t = DK
        lay[(x, y)] = R[t]
    if grain and S.k == 2:
        inner = sorted(p for p in m if all((p[0] + dx, p[1] + dy) in m for dx, dy in N4))
        for (x, y) in inner:
            if rnd.random() < 0.08:
                lay[(x, y)] = R[DK]
                if (x + 1, y + 1) in inner:
                    lay[(x + 1, y + 1)] = R[DK]


def roots(S, lay, cx, gy, w, R, m, n=None, seed=0):
    """Roots gripping the ground at the foot of a trunk (w = trunk width at the base): short curved limbs
    spreading left and right along the surface, lit on top, with dark crevices between them."""
    k = S.k
    rnd = S.rnd('roots', seed)
    xl, xr = cx - w // 2, cx - w // 2 + w - 1
    rm = set()
    for side in (-1, 1):
        for i in range(n or S.kv(1, 2)):
            x0 = xl + 1 if side < 0 else xr - 1
            L = S.kv(3, 6) - i * S.kv(1, 2) + rnd.randint(0, 1)
            h = S.kv(3, 5) - i
            path = bezier((x0, gy - h), (x0 + side * L // 2, gy - h // 2), (x0 + side * L, gy))
            limb(S, lay, path, S.kv(2, 3), 1, R, rm, shade=False)
    rm -= m
    for (x, y) in rm:
        t = LT if x < cx else DK
        if (x, y - 1) not in rm and (x, y - 1) not in m and x < cx:
            t = HI if k == 2 and rnd.random() < 0.3 else LT
        elif (x, y + 1) not in rm and y < gy:
            t = SH
        lay[(x, y)] = R[t]
    for (x, y) in rm:                                        # crevice where a root leaves the trunk
        if (x + (1 if x < cx else -1), y) in m and (x, y - 1) in m:
            lay[(x, y)] = R[SH]
    m |= rm
    return m


# ------------------------------------------------------------------ trees: leaf crown
def lumpy(S, cx, cy, rx, ry, rnd, bump=None, flat_bottom=0.0):
    """An ellipse whose edge is a ring of leaf bumps (a scalloped, leafy silhouette); the bottom bumps are
    smaller (leaves hang, the underside is flatter)."""
    b = bump or S.kv(1.7, 2.7)
    m = disc(cx, cy, rx, ry)
    n = max(6, int(2 * math.pi * max(rx, ry) / (b * 1.7)))
    a0 = rnd.uniform(0, 1)
    for i in range(n):
        a = 2 * math.pi * (i + a0) / n + rnd.uniform(-0.12, 0.12)
        s = math.sin(a)
        rr = b * rnd.uniform(0.85, 1.15) * (0.75 if s > 0.45 else 1.0)
        if s > 0.6 and flat_bottom and rnd.random() < flat_bottom:
            continue
        m |= disc(cx + math.cos(a) * (rx - rr * 0.35), cy + s * (ry - rr * 0.35), rr, rr * 0.9)
    return m


def _lam(nx, ny):
    """Light on a foliage ball: mostly from the side (top-left), little from the front, so the middle of
    a puff is base, the top-left light, the bottom-right dark."""
    r2 = nx * nx + ny * ny
    nz = math.sqrt(max(0.0, 1 - min(1.0, r2)))
    return -0.6 * nx - 0.75 * ny + 0.3 * nz


def _leaf_tone(lam):
    return HI if lam > 0.88 else LT if lam > 0.42 else BS if lam > 0.0 else DK if lam > -0.4 else SH


_MARKS1 = ({(0, 0): 1, (1, 0): 1, (1, 1): -1}, {(0, 0): 1, (1, 0): 0, (0, 1): -1}, {(0, 0): 1, (1, 0): 1},
           {(1, 0): 1, (0, 1): 1, (1, 1): -1})
_MARKS2 = ({(0, 0): 1, (1, 0): 1, (2, 0): 0, (0, 1): 1, (1, 1): 0, (2, 1): -1, (1, 2): -1},
           {(1, 0): 1, (2, 0): 1, (0, 1): 1, (1, 1): 0, (2, 1): 0, (3, 1): -1, (1, 2): -1, (2, 2): -1},
           {(0, 0): 1, (1, 0): 1, (1, 1): 0, (2, 1): -1},
           {(1, 0): 1, (0, 1): 1, (1, 1): 1, (2, 1): 0, (1, 2): 0, (2, 2): -1},
           {(0, 0): 1, (0, 1): 0, (1, 1): 1, (1, 2): -1, (2, 2): -1})


def leaf_marks(S, tone, m, rnd, step=None, hi_ok=True, dark_only=False):
    """Leaf texture: small leaf shapes on a jittered grid (2-3 px k=1, 4-8 px HD), each a step lighter on its
    top-left (a leaf catching the light) and a step darker underneath (its own shadow) - clusters, never
    single-pixel noise. Marks stay off the edge of the mask."""
    k = S.k
    step = step or S.kv(3, 4.5)
    x0, y0, x1, y1 = bbox(m)
    y = y0 + rnd.uniform(0, step)
    row = 0
    marks = _MARKS1 if k == 1 else _MARKS2
    while y <= y1:
        x = x0 + (step / 2 if row % 2 else 0) + rnd.uniform(0, 1)
        while x <= x1:
            px, py = int(x + rnd.uniform(-1, 1)), int(y + rnd.uniform(-0.8, 0.8))
            if (px, py) in m and all((px + dx, py + dy) in m for dx, dy in N8):
                t0 = tone[(px, py)]
                mk = rnd.choice(marks)
                for (a, b), d in mk.items():
                    q = (px + a, py + b)
                    if q not in m or not all((q[0] + dx, q[1] + dy) in m for dx, dy in N4):
                        continue
                    if dark_only and d > 0:
                        d = 0
                    t = t0 + d
                    if t > LT and not (hi_ok and t0 >= LT):
                        t = LT
                    tone[q] = max(SH, min(HI, t))
            x += step * rnd.uniform(0.85, 1.2)
        y += step * 0.75
        row += 1


def crown(S, clumps, R, name='leaves', z=20, holes=2, seed=0, ramps=None, bump=None, texture='broad',
          cast=True, back_ramp=None):
    """A leaf crown from clumps [(cx, cy, rx, ry, depth)]: depth 0 = the back mass (the shaded inside of the
    crown, one step darker, no highlight), depth >= 1 = front puffs, each its own part (leaves_1..n), drawn
    top -> bottom so a lower puff sits in front of the one above: its lit top rim stands against the dark
    underside of the puff behind - the scalloped layering that reads as foliage. Each puff is lit as a ball
    and by its place in the whole crown (top-left lightest), with a leaf-bump silhouette and leaf marks.
    See-through holes are cut in the back mass between puffs (the limbs show through), their upper edge in
    the leaves' shadow. One selective outline round the whole crown. ramps = one ramp per puff, cycled
    (autumn mixes). Returns (union mask, [visible mask of each puff], {part: mask})."""
    k = S.k
    rnd = S.rnd('crown', name, seed)
    gx0 = min(c[0] - c[2] for c in clumps)
    gx1 = max(c[0] + c[2] for c in clumps)
    gy0 = min(c[1] - c[3] for c in clumps)
    gy1 = max(c[1] + c[3] for c in clumps)
    gcx, gcy, grx, gry = (gx0 + gx1) / 2, (gy0 + gy1) / 2, (gx1 - gx0) / 2, (gy1 - gy0) / 2
    back = [c for c in clumps if c[4] == 0]
    front = sorted([c for c in clumps if c[4] > 0], key=lambda c: (c[4], c[1]))
    groups = ([(name + '_back', back, 0)] if back else []) + [(f'{name}_{i + 1}', [c], i + 1)
                                                              for i, c in enumerate(front)]
    rb = bump or S.kv(1.6, 2.5)
    masks, lays = {}, {}
    union = set()
    for (pname, cl, depth) in groups:
        lay = S.lay(pname, z + depth, cast=(S.kv(1, 2), S.kv(1, 2), 1) if (cast and depth) else None)
        Rg = R if not (ramps and depth) else ramps[(depth - 1) % len(ramps)]
        if depth == 0 and back_ramp:
            Rg = back_ramp
        m = set()
        shapes = []
        for (cx, cy, rx, ry, d) in cl:
            mm = lumpy(S, cx, cy, rx, ry, rnd, bump=rb)
            shapes.append(((cx, cy, rx, ry), mm))
            m |= mm
        tone = {}
        for (x, y) in m:
            best = -9
            for (cx, cy, rx, ry), mm in shapes:
                if (x, y) in mm:
                    lam_l = _lam((x + 0.5 - cx) / (rx + rb * 0.6), (y + 0.5 - cy) / (ry + rb * 0.6))
                    lam_g = _lam((x + 0.5 - gcx) / (grx + 1), (y + 0.5 - gcy) / (gry + 1))
                    best = max(best, (0.55 * lam_l + 0.45 * lam_g) if depth else (0.3 * lam_l + 0.7 * lam_g - 0.25))
            t = _leaf_tone(best)
            tone[(x, y)] = min(BS, t) if depth == 0 else t
        if depth:                                       # the puff's rims: lit top-left lip, dark underside
            for (x, y) in m:
                if (x, y - 1) not in m and (x, y - 1) in union and tone[(x, y)] < HI:
                    tone[(x, y)] = min(LT if tone[(x, y)] < LT else HI, tone[(x, y)] + 1)
                elif (x, y + 1) not in m and (x, y + 1) in union:
                    tone[(x, y)] = max(SH, tone[(x, y)] - 1)
        leaf_marks(S, tone, m, rnd, hi_ok=bool(depth), dark_only=(depth == 0))
        if texture == 'needle':
            for (x, y), t in list(tone.items()):
                if t >= BS and rnd.random() < 0.1 and (x + 1, y) in m:
                    tone[(x + 1, y)] = min(LT, t + 1)
        for p, t in tone.items():
            lay[p] = Rg[t]
        masks[pname] = m
        lays[pname] = (lay, Rg, depth)
        union |= m
    order = list(lays)
    visible = {}
    for i, pn in enumerate(order):
        later = set().union(*[masks[q] for q in order[i + 1:]]) if i + 1 < len(order) else set()
        visible[pn] = masks[pn] - later
    # see-through holes in the back mass where it shows between puffs
    if back and holes:
        bn = name + '_back'
        d = S.kv(2, 3)
        cand = sorted(p for p in visible[bn] if p[1] > gcy - gry * 0.1 and
                      all((p[0] + a, p[1] + b) in union for a in (-d - 1, 0, d + 1) for b in (-d, 0, d)))
        rnd.shuffle(cand)
        made = []
        for p in cand:
            if len(made) >= holes:
                break
            if any(abs(p[0] - q[0]) + abs(p[1] - q[1]) < S.kv(7, 12) for q in made):
                continue
            hole = {(p[0] + a, p[1] + b) for a, b in blob(rnd, S.kv(rnd.choice((2, 3, 4)), rnd.randint(5, 9)),
                                                            wide=1.5, tall=0.8)}
            hole &= visible[bn]
            if len(hole) < S.kv(2, 4) or not all((x + a, y + b) in union for (x, y) in hole for a, b in N8):
                continue
            made.append(p)
            lay, Rg, _ = lays[bn]
            for q in hole:
                lay.pop(q, None)
                masks[bn].discard(q)
                visible[bn].discard(q)
            for (x, y) in hole:
                q = (x, y - 1)
                if q in lay and q not in hole:
                    lay[q] = Rg[O]
            union -= hole
    # one selective outline round the whole crown, each ring pixel in the part it wraps; the ring is made
    # pixel-perfect as one line first (its pixels go to different parts)
    for (x, y) in sorted(perfect_ring(union)):
        own = None
        for pn in reversed(order):
            if any((x + dx, y + dy) in masks[pn] for dx, dy in N4):
                own = pn
                break
        if own is None:
            continue
        lay, Rg, d = lays[own]
        inside = [(x + dx, y + dy) for dx, dy in N4 if (x + dx, y + dy) in union]
        is_lit = ((x, y + 1) in union or (x + 1, y) in union) and not ((x, y - 1) in union or (x - 1, y) in union)
        if len(inside) >= 3:
            continue                                     # a notch inside the silhouette (a hole): leave it open
        lay[(x, y)] = Rg[SH] if is_lit else Rg[O]
    return union, [visible[pn] for pn in order], masks


def stamp_fruit(S, lay, x, y, R, kind='apple', leaf=None):
    """A small fruit / flower stamped at (x, y) (its top-left): apple (lit ball with a stem), blossom (five
    petals round a yellow eye), pod (cocoa: a ribbed oval), coconut, berry."""
    k = S.k
    pts = {}
    if kind == 'apple':
        if k == 1:
            pts = {(0, 0): HI, (1, 0): BS, (0, 1): BS, (1, 1): DK}
        else:
            pts = {(1, 0): LT, (2, 0): BS, (0, 1): LT, (1, 1): HI, (2, 1): BS, (3, 1): DK, (0, 2): BS, (1, 2): BS,
                   (2, 2): DK, (3, 2): SH, (1, 3): DK, (2, 3): SH}
            lay[(x + 2, y - 1)] = SEEDS[BS]                    # noqa: F821  stem
        for (a, b), t in pts.items():
            lay[(x + a, y + b)] = R[t]
    elif kind == 'blossom':
        eye = DANDELION                                        # noqa: F821
        if k == 1:
            for (a, b), t in {(1, 0): HI, (0, 1): HI, (2, 1): LT, (1, 2): BS}.items():
                lay[(x + a, y + b)] = R[t]
            lay[(x + 1, y + 1)] = eye[LT]
        else:
            for (a, b), t in {(1, 0): HI, (2, 0): LT, (0, 1): HI, (1, 1): LT, (3, 1): LT, (0, 2): LT, (3, 2): BS,
                              (1, 3): BS, (2, 3): DK}.items():
                lay[(x + a, y + b)] = R[t]
            lay[(x + 1, y + 2)] = eye[HI]
            lay[(x + 2, y + 2)] = eye[BS]
            lay[(x + 2, y + 1)] = eye[LT]
    elif kind == 'pod':
        w, h = S.kv(2, 3), S.kv(3, 5)
        for a in range(w):
            for b in range(h):
                t = LT if a == 0 else BS if a < w - 1 else DK
                if b == h - 1:
                    t = DK
                if k == 2 and b % 2 == 1 and a == 1:
                    t = DK
                lay[(x + a, y + b)] = R[t]
        lay[(x + w // 2, y - 1)] = (leaf or R)[BS]
    elif kind == 'coconut':
        r = S.kv(1.6, 2.8)
        for (a, b) in disc(x + r, y + r, r):
            lay[(a, b)] = R[sphere_tone((a + 0.5 - x - r) / r, (b + 0.5 - y - r) / r)]
    elif kind == 'berry':
        lay[(x, y)] = R[LT]
        if k == 2:
            lay[(x + 1, y)] = R[BS]
            lay[(x, y + 1)] = R[BS]
            lay[(x + 1, y + 1)] = R[DK]


def scatter_on(S, lay, mask, R, kind, n, seed=0, avoid_edge=1, where=None):
    """n fruits / blossoms spread evenly over a crown mask (not on its outline)."""
    rnd = S.rnd('fruit', kind, seed)
    inner = [p for p in sorted(mask) if all((p[0] + dx * avoid_edge, p[1] + dy * avoid_edge) in mask
                                            for dx, dy in N4)]
    if where:
        inner = [p for p in inner if where(p)]
    rnd.shuffle(inner)
    placed = []
    gap = S.kv(4, 7)
    for p in inner:
        if len(placed) >= n:
            break
        if all(abs(p[0] - q[0]) + abs(p[1] - q[1]) >= gap for q in placed):
            placed.append(p)
            stamp_fruit(S, lay, p[0], p[1], R, kind)
    return placed


def snow_cap(S, masks, name='snow', z=60, depth=None, seed=0, under=False):
    """Snow resting on every upward-facing surface: masks = the visible masks of the things it falls on, in
    draw order (back -> front: crown puffs, limbs, caps, rocks). A pixel gets snow when the one above it is
    sky or belongs to something behind; the cap is `depth` px (thicker on flat runs, thinner on slopes),
    lit top row, base body, a blue shaded lower edge, a lip that piles up above flat runs, and a light
    blue-grey outline above. Part 'snow'."""
    if isinstance(masks, set):
        masks = [masks]
    lay = S.lay(name, z)
    rnd = S.rnd('snow', seed)
    depth = depth or S.kv(2, 3)
    union = set().union(*masks) if masks else set()
    m = set()
    for i, mm in enumerate(masks):
        later = set().union(*masks[i + 1:]) if i + 1 < len(masks) else set()
        tops = {(x, y) for (x, y) in mm if (x, y - 1) not in mm and (under or (x, y - 1) not in later)}
        for (x, y) in sorted(tops):
            flat = ((x - 1, y) in tops) + ((x + 1, y) in tops)
            d = depth - (1 if flat == 0 else 0) + (1 if flat == 2 and rnd.random() < 0.3 else 0)
            for j in range(max(1, d)):
                if (x, y + j) in mm:
                    m.add((x, y + j))
    for (x, y) in m:
        top = (x, y - 1) not in m
        bottom = (x, y + 1) not in m
        t = BS
        if top:
            t = HI
        elif bottom:
            t = DK
        lay[(x, y)] = SNOW[t]                                     # noqa: F821
    for (x, y) in sorted(m):                                      # a lip piles up above flat runs
        if all((x + i, y) in m and (x + i, y - 1) not in m and (x + i, y - 1) not in union for i in range(-1, 3)) \
                and rnd.random() < 0.25 and (x - 1, y - 1) not in lay:
            lay[(x, y - 1)] = lay[(x + 1, y - 1)] = SNOW[LT]      # noqa: F821
    snowy = set(lay)
    for (x, y) in edge_ring(snowy):
        if (x, y + 1) in snowy and (x, y) not in union:
            lay[(x, y)] = SNOW[SH]                                # noqa: F821  outline above the snow
    return snowy


def falling(S, lay, x0, x1, y0, y1, Rs, n, seed=0, kind='leaf'):
    """Leaves / petals in the air: small tilted flecks (2-3 px k=1, 4-5 px HD) lit on top."""
    rnd = S.rnd('falling', seed)
    for i in range(n):
        x = rnd.randint(x0, x1)
        y = rnd.randint(y0, y1)
        R = rnd.choice(Rs)
        if S.k == 1:
            pts = {(0, 0): LT, (1, 0): LT} if rnd.random() < 0.5 else {(0, 0): BS, (1, 0): BS}
        else:
            pts = rnd.choice(({(1, 0): HI, (0, 1): LT, (1, 1): BS, (2, 1): DK},
                              {(0, 0): LT, (1, 0): BS, (1, 1): BS, (2, 1): DK},
                              {(0, 0): HI, (1, 0): LT, (2, 0): BS, (1, 1): DK}))
        for (a, b), t in pts.items():
            lay[(x + a, y + b)] = R[t]


# ------------------------------------------------------------------ trees
LEAF_SEASONS = {   # kind: {season: ramp or [ramps for the front clusters (mixed autumn colours)]}
    'oak': {'spring': OAK_LEAF_SPRING, 'summer': OAK_LEAF, 'autumn': [OAK_LEAF_AUTUMN, LEAF_RED, LEAF_YELLOW],  # noqa
            'winter': OAK_LEAF_WINTER},                                                                     # noqa
    'birch': {'spring': BIRCH_LEAF_SPRING, 'summer': BIRCH_LEAF, 'autumn': [BIRCH_LEAF_AUTUMN, LEAF_YELLOW],  # noqa
              'winter': WINTER_LEAF},                                                                        # noqa
    'spruce': {'spring': SPRUCE_LEAF_SPRING, 'summer': SPRUCE_LEAF, 'autumn': SPRUCE_LEAF,                # noqa
               'winter': SPRUCE_LEAF},                                                                       # noqa
    'jungle': {'spring': JUNGLE_LEAF_SPRING, 'summer': JUNGLE_LEAF, 'autumn': JUNGLE_LEAF_AUTUMN,         # noqa
               'winter': WINTER_LEAF},                                                                       # noqa
    'acacia': {'spring': ACACIA_LEAF, 'summer': ACACIA_LEAF, 'autumn': ACACIA_LEAF_AUTUMN,                # noqa
               'winter': WINTER_LEAF},                                                                       # noqa
    'dark_oak': {'spring': DARK_OAK_LEAF_SPRING, 'summer': DARK_OAK_LEAF,                                 # noqa
                 'autumn': [DARK_OAK_LEAF_AUTUMN, OAK_LEAF_AUTUMN], 'winter': WINTER_LEAF},                  # noqa
    'cherry': {'spring': CHERRY_LEAF, 'summer': CHERRY_LEAF, 'autumn': [CHERRY_LEAF_AUTUMN, LEAF_RED],      # noqa
               'winter': CHERRY_LEAF},                                                                       # noqa
    'palm': {'spring': PALM_LEAF, 'summer': PALM_LEAF, 'autumn': PALM_LEAF, 'winter': PALM_LEAF},         # noqa
    'swamp': {'spring': SWAMP_LEAF, 'summer': SWAMP_LEAF, 'autumn': [SWAMP_LEAF, OAK_LEAF_AUTUMN],         # noqa
              'winter': WINTER_LEAF},                                                                        # noqa
}


def leaf_ramps(kind, season):
    v = LEAF_SEASONS[kind][season]
    if isinstance(v[0], list):
        return v[0], v
    return v, None


SIZES = {'s': 0.8, 'm': 1.0, 'l': 1.22}


def _tree_extras(S, cx, gy, union, vis, x_left, x_right, top, kind, R, ramps, fruit=None, blossom=None,
                 n_fruit=None, litter_ramps=None, shadow=True):
    """What every leafy tree shares: fruit / blossoms (summer / spring), falling leaves (autumn), snow
    (winter), and the shadow the crown throws on the ground to the right."""
    k, u = S.k, S.u
    season = S.season
    lay = S.lay('fruit', 40)
    if season == 'summer' and fruit:
        scatter_on(S, lay, union, fruit[0], fruit[1], n_fruit or S.kv(4, 6), seed=cx,
                   where=lambda p: p[1] > top + u(3))
    if season == 'spring' and blossom:
        scatter_on(S, lay, union, blossom, 'blossom', n_fruit or S.kv(6, 9), seed=cx + 1)
    if season == 'autumn':
        fl = S.lay('falling_leaves', 70)
        falling(S, fl, x_left - u(2), x_right + u(4), gy - u(14), gy - u(3), litter_ramps or ramps or [R],
                S.kv(4, 7), seed=cx)
    if season == 'winter':
        snow_cap(S, [S.mask_of('branches')] + vis, seed=cx)
    if shadow:
        ground_shadow(S, cx - u(3), x_right + u(5), gy, contact=(cx - u(3), cx + u(3)), steps=2)


def oak(S, cx, gy, size='m', kind='oak', vines=False, **_):
    """Oak: a sturdy furrowed trunk forking into three limbs, a round crown of puffs over a dark back mass
    (holes show the limbs); apples in summer, white blossoms in spring, orange / red / yellow puffs and
    falling leaves in autumn, snow on every puff in winter."""
    k, u = S.k, S.u
    sc = SIZES.get(size, 1.0)
    rnd = S.rnd('oak', cx)
    ccy = gy - u(27 * sc)                                       # crown centre
    R, ramps = leaf_ramps(kind, S.season)
    br = S.lay('branches', 8)
    bm = set()
    for (sx, sy, ex, ey, w0) in ((-1, -12, -11, 0, 2.5), (1, -14, 10, -2, 2.5), (0, -16, -4, -8, 2), (0, -17, 4, -9, 2)):
        x0, y0, ex, ey = cx + u(sx * sc), gy + u(sy * sc), cx + u(ex * sc), ccy + u(ey * sc)
        path = bezier((x0, y0), ((x0 + ex) // 2, y0 - u(2)), (ex, ey))
        limb(S, br, path, u(w0), S.kv(1, 2), OAK_BARK, bm, shade=False)                   # noqa: F821
    shade_wood(S, br, bm, OAK_BARK)                                                       # noqa: F821
    outline(br, bm, OAK_BARK)                                                             # noqa: F821
    trunk(S, cx, ccy, gy, u(5), u(3.5), OAK_BARK, seed=cx)                               # noqa: F821

    def J(a):
        return u(a * sc) + rnd.randint(-1, 1)

    def U(a):
        return u(a * sc)
    clumps = [(cx + J(0), ccy + J(-1), U(15), U(10.5), 0),
              (cx + J(-6), ccy + J(-7), U(6.5), U(5), 1), (cx + J(5), ccy + J(-8), U(6), U(4.5), 1),
              (cx + J(-12), ccy + J(-1), U(4.5), U(4.5), 2), (cx + J(0), ccy + J(-2), U(6), U(4.5), 2),
              (cx + J(12), ccy + J(-2), U(4.5), U(4.5), 2),
              (cx + J(-8), ccy + J(5), U(5.5), U(4), 3), (cx + J(5), ccy + J(6), U(6), U(4), 3),
              (cx + J(13), ccy + J(5), U(3.5), U(3), 3)]
    union, vis, masks = crown(S, clumps, R, ramps=ramps, seed=cx, holes=S.kv(2, 3))
    top = min(y for _, y in union)
    x0, _, x1, _ = bbox(union)
    _tree_extras(S, cx, gy, union, vis, x0, x1, top, kind, R, ramps,
                 fruit=(RED_CAP, 'apple') if kind == 'oak' else None, blossom=CREAM)                  # noqa: F821
    return {'ground': 'grass'}


def vines(S, lay, starts, R, seed=0, leafy=1.0):
    """Hanging vine strands from (x, y, length) starts: a 1 px stem that sways (no doubles), leaves every
    2-3 px alternating left / right - lit leaves on the left, darker on the right, HD leaves 2-3 px."""
    k = S.k
    rnd = S.rnd('vines', seed)
    m = set()
    for (x, y, L) in starts:
        ph = rnd.uniform(0, 6)
        prev = None
        side = rnd.choice((-1, 1))
        for j in range(L):
            xx = x + int(round(math.sin(j * S.kv(0.25, 0.45) + ph) * S.kv(0.55, 1.2)))
            if prev and prev[0] != xx and (xx, y + j - 1) not in m:
                pass
            lay[(xx, y + j)] = R[LT if j == 0 else BS if (j % 4 or k == 1) else DK]
            m.add((xx, y + j))
            prev = (xx, y + j)
            if j % S.kv(3, 3) == 1 and rnd.random() < 0.85 * leafy:
                side = -side
                lx = xx + side
                lay[(lx, y + j)] = R[LT if side < 0 else DK]
                m.add((lx, y + j))
                if k == 1:                                          # a leaf is 2 px: a tip above it
                    lay[(lx, y + j - 1)] = R[LT if side < 0 else DK]
                    m.add((lx, y + j - 1))
                if k == 2:                                          # HD leaf: 2x2, lit top row
                    lay[(lx + side, y + j)] = R[LT if side < 0 else BS]
                    lay[(lx, y + j)] = R[LT if side < 0 else BS]
                    lay[(lx, y + j + 1)] = R[BS if side < 0 else DK]
                    lay[(lx + side, y + j + 1)] = R[BS if side < 0 else DK]
                    m |= {(lx + side, y + j), (lx, y + j + 1), (lx + side, y + j + 1)}
        if k == 2 and L > 4:                                         # a curled tip
            lay[(xx + 1, y + L)] = R[DK]
    return m


def _limbs(S, specs, R, name='branches', z=8, cast=None, sc=1.0):
    """Several limbs [((x0, y0), (cx, cy), (x1, y1), w0, w1)] shaded together, outlined once."""
    lay = S.lay(name, z, cast=cast)
    bm = set()
    for (p0, p1, p2, w0, w1) in specs:
        limb(S, lay, bezier(p0, p1, p2), w0, w1, R, bm, shade=False)
    shade_wood(S, lay, bm, R)
    outline(lay, bm, R)
    return bm


def birch(S, cx, gy, size='m', **_):
    """Birch: a slender white trunk with black dashes and eye marks, thin white limbs, a tall oval crown of
    small light-green puffs; catkin-pale blossoms in spring, golden in autumn, snow in winter."""
    k, u = S.k, S.u
    sc = SIZES.get(size, 1.0)
    rnd = S.rnd('birch', cx)
    ccy = gy - u(31 * sc)
    R, ramps = leaf_ramps('birch', S.season)
    U = lambda a: u(a * sc)                                             # noqa: E731
    _limbs(S, [((cx, gy - U(13)), (cx - U(3), gy - U(16)), (cx - U(7), ccy + U(3)), S.kv(2, 3), 1),
               ((cx, gy - U(16)), (cx + U(3), gy - U(19)), (cx + U(6), ccy + U(1)), S.kv(2, 3), 1),
               ((cx, gy - U(19)), (cx - U(1), ccy), (cx - U(3), ccy - U(6)), S.kv(2, 3), 1)], BIRCH_BARK)  # noqa
    trunk(S, cx, ccy - U(4), gy, u(3.4), u(2.6), BIRCH_BARK, style='birch', seed=cx, roots=1)          # noqa

    def J(a):
        return u(a * sc) + rnd.randint(-1, 1)
    clumps = [(cx + J(0), ccy + J(0), U(10), U(14), 0),
              (cx + J(0), ccy + J(-11), U(5), U(4.5), 1),
              (cx + J(-5), ccy + J(-6), U(5), U(4.5), 2), (cx + J(5), ccy + J(-6), U(5), U(4.5), 2),
              (cx + J(-6), ccy + J(0), U(5), U(4.5), 3), (cx + J(5), ccy + J(1), U(5.5), U(4.5), 3),
              (cx + J(-4), ccy + J(7), U(5), U(4), 4), (cx + J(5), ccy + J(8), U(4.5), U(4), 4),
              (cx + J(0), ccy + J(12), U(4), U(3), 5)]
    union, vis, masks = crown(S, clumps, R, ramps=ramps, seed=cx, holes=S.kv(2, 3), bump=S.kv(1.4, 2.2))
    x0, y0, x1, _ = bbox(union)
    _tree_extras(S, cx, gy, union, vis, x0, x1, y0, 'birch', R, ramps, blossom=BIRCH_LEAF_SPRING)     # noqa
    return {'ground': 'grass'}


def spruce(S, cx, gy, size='m', **_):
    """Spruce: a cone of drooping needle tiers - each tier a skirt lit on its left, dark on its right, its
    lower edge a fringe of hanging needle tips that casts a shadow on the tier below; needle strokes
    slant down and outward; a short furrowed trunk under the lowest tier; snow on every tier in winter."""
    k, u = S.k, S.u
    sc = SIZES.get(size, 1.0)
    rnd = S.rnd('spruce', cx)
    R, _ = leaf_ramps('spruce', S.season)
    Hh = u(54 * sc)
    yb0 = gy - u(5)
    top = gy - Hh
    trunk(S, cx, yb0 - u(10), gy, u(3.6), u(2.6), SPRUCE_BARK, seed=cx, roots=1)                       # noqa
    n = S.kv(6, 7) if sc >= 1 else S.kv(5, 6)
    hw0 = u(13 * sc)
    step = (yb0 - top - u(5)) / n
    vis = []
    tiers = []
    for i in range(n):
        t = i / n
        yb = int(round(yb0 - i * step))
        th = int(round(step * 1.75)) + u(2)
        hw = max(u(3), int(round(hw0 * (1 - t * 0.78))))
        lay = S.lay(f'tier_{i + 1}', 20 + i, cast=(S.kv(1, 2), S.kv(1, 2), 1))
        m = set()
        tone = {}
        tipw = S.kv(3, 4)
        for x in range(cx - hw - 1, cx + hw + 1):
            d = abs(x + 0.5 - cx) / hw
            if d > 1:
                continue
            # the skirt: top rises toward the centre (convex), the bottom droops at the ends
            ytop = yb - th + int(round(th * 0.85 * d ** 1.3))
            tip = 1 + ((x - cx + 50 * tipw) % tipw == 0) * S.kv(1, 2) + (rnd.random() < 0.3)
            ybot = yb + int(round(d * d * S.kv(2, 3))) + tip - 1
            for y in range(ytop, ybot + 1):
                m.add((x, y))
        for (x, y) in m:
            nx = (x + 0.5 - cx) / hw
            ny = (y - (yb - th / 2)) / (th / 2)
            lam = -0.75 * nx - 0.35 * ny + 0.1 - 0.15 * (i == 0)
            tt = LT if lam > 0.42 else BS if lam > -0.05 else DK if lam > -0.5 else SH
            if (x, y + 1) not in m:
                tt = max(SH, tt - 1)                             # needle tips at the lower edge
            if (x, y - 1) not in m:
                tt = min(HI if nx < -0.3 else LT, tt + 1)
            tone[(x, y)] = tt
        # needle strokes: short lines slanting down and outward
        cells = sorted(m)
        rnd.shuffle(cells)
        for (x, y) in cells[:int(len(cells) * S.kv(0.08, 0.07))]:
            side = -1 if x < cx else 1
            L = S.kv(2, 3)
            tt = tone[(x, y)]
            c2 = min(LT, tt + 1) if tt <= BS and x < cx else max(SH, tt - 1)
            for j in range(L):
                q = (x + side * j, y + j)
                if q in m and (q[0], q[1] + 1) in m:
                    tone[q] = c2
        for p_, tt in tone.items():
            lay[p_] = R[tt]
        outline(lay, m, R)
        tiers.append(m)
    lead = S.lay('leader', 20 + n)                                # the leader: a narrow spike on top
    lm = set()
    for j in range(u(5)):
        w = 1 if j < u(5) * 0.5 else S.kv(2, 3)
        for i in range(w):
            lm.add((cx - w // 2 + i, top + j))
    for (x, y) in lm:
        lead[(x, y)] = R[LT if x < cx else BS]
    outline(lead, lm, R)
    allm = [set(lay) for lay in [p['lay'] for p in S.parts if p['name'].startswith(S.prefix + 'tier_')]]
    vis = []
    for i, mm in enumerate(allm):
        later = set().union(*allm[i + 1:]) if i + 1 < len(allm) else set()
        vis.append(mm - later)
    vis.append(lm)
    union = set().union(*allm) | lm
    x0, y0, x1, _ = bbox(union)
    if S.season == 'winter':
        snow_cap(S, vis, seed=cx, depth=S.kv(2, 3), under=True)
    if S.season == 'spring':                                    # fresh light tips on the lit side
        lay = S.lay('new_growth', 40)
        for (x, y) in sorted(union):
            if (x, y + 1) not in union and x < cx and rnd.random() < 0.3:
                lay[(x, y)] = SPRUCE_LEAF_SPRING[HI]                   # noqa: F821
    ground_shadow(S, cx - u(3), x1 + u(4), gy, contact=(cx - u(3), cx + u(3)), steps=2)
    return {'ground': 'podzol' if S.season != 'winter' else 'snow'}


def jungle(S, cx, gy, size='m', **_):
    """Jungle tree: a tall thick trunk with vertical ridges, moss patches, buttress roots and cocoa pods, a
    wide flat crown of big puffs with vines hanging from it, small leaf clumps on side branches."""
    k, u = S.k, S.u
    sc = SIZES.get(size, 1.0)
    rnd = S.rnd('jungle', cx)
    R, ramps = leaf_ramps('jungle', S.season)
    U = lambda a: u(a * sc)                                             # noqa: E731
    ccy = gy - U(50)
    _limbs(S, [((cx - 1, gy - U(26)), (cx - U(5), gy - U(28)), (cx - U(9), gy - U(31)), S.kv(2, 4), 1),
               ((cx + 1, gy - U(19)), (cx + U(5), gy - U(20)), (cx + U(9), gy - U(24)), S.kv(2, 4), 1),
               ((cx, ccy + U(6)), (cx - U(6), ccy + U(3)), (cx - U(12), ccy + U(1)), S.kv(3, 5), 1),
               ((cx, ccy + U(5)), (cx + U(6), ccy + U(2)), (cx + U(12), ccy), S.kv(3, 5), 1)], JUNGLE_BARK)  # noqa
    tm = trunk(S, cx, ccy, gy, u(6.5), u(5), JUNGLE_BARK, seed=cx, roots=S.kv(2, 3))                  # noqa
    ml = S.lay('moss', 7)                                                # moss on the shaded, damp side
    for (x, y) in sorted(tm):
        if (x + 1, y) not in tm and rnd.random() < 0.18 and y > ccy + U(4):
            for j in range(rnd.randint(2, S.kv(3, 6))):
                if (x, y + j) in tm:
                    ml[(x, y + j)] = MOSS[DK if j % 2 else BS]                 # noqa: F821
                if k == 2 and (x - 1, y + j) in tm and j > 0:
                    ml[(x - 1, y + j)] = MOSS[BS]                             # noqa: F821
    pods = S.lay('fruit', 41)
    for (px_, py_) in ((cx - u(4), gy - U(14)), (cx + u(3), gy - U(33))):
        stamp_fruit(S, pods, px_ - S.kv(1, 2) if px_ < cx else px_, py_, COCOA, 'pod', leaf=STALK)   # noqa
    union = set()
    vis = []

    def J(a):
        return u(a * sc) + rnd.randint(-1, 1)
    for nm, (ox, oy), cl in (('leaves_low_l', (cx - U(10), gy - U(32)), [(0, 0, 5, 3.5, 0), (-1, -1, 4, 3, 1), (2, 1, 3.5, 2.5, 2)]),
                             ('leaves_low_r', (cx + U(10), gy - U(25)), [(0, 0, 5, 3.5, 0), (1, -1, 4, 3, 1), (-2, 1, 3.5, 2.5, 2)])):
        un, vv, _ = crown(S, [(ox + U(a), oy + U(b), U(rx), U(ry), d) for a, b, rx, ry, d in cl], R, name=nm,
                          z=18, holes=0, seed=ox, bump=S.kv(1.3, 2.0))
        union |= un
        vis += vv
    clumps = [(cx + J(0), ccy + J(0), U(19), U(8), 0),
              (cx + J(-8), ccy + J(-5), U(7), U(4.5), 1), (cx + J(7), ccy + J(-6), U(8), U(4.5), 1),
              (cx + J(-15), ccy + J(0), U(5.5), U(4), 2), (cx + J(0), ccy + J(-1), U(7), U(4.5), 2),
              (cx + J(15), ccy + J(-1), U(5.5), U(4), 2),
              (cx + J(-9), ccy + J(4), U(6), U(3.5), 3), (cx + J(8), ccy + J(4), U(6.5), U(3.5), 3)]
    un, vv, _ = crown(S, clumps, R, ramps=ramps, seed=cx, holes=S.kv(2, 3), z=22)
    union |= un
    vis += vv
    vl = S.lay('vines', 45)
    bot = cols(un)
    starts = []
    for x in range(min(bot), max(bot) + 1, S.kv(4, 6)):
        if x in bot and abs(x - cx) > u(4) and rnd.random() < 0.7:
            starts.append((x + rnd.randint(-1, 1), bot[x][1] - 1, rnd.randint(U(5), U(14))))
    vines(S, vl, starts, VINE, seed=cx)                                                                 # noqa
    x0, y0, x1, _ = bbox(union)
    _tree_extras(S, cx, gy, union, vis, x0, x1, y0, 'jungle', R, ramps, blossom=CREAM)                # noqa
    return {'ground': 'grass'}


def acacia(S, cx, gy, size='m', **_):
    """Acacia: a grey leaning trunk that forks into two slanted limbs, each carrying a flat, wide canopy of
    low puffs (savanna umbrella) - the higher canopy lit, the lower one in its shadow."""
    k, u = S.k, S.u
    sc = SIZES.get(size, 1.0)
    rnd = S.rnd('acacia', cx)
    R, ramps = leaf_ramps('acacia', S.season)
    U = lambda a: u(a * sc)                                             # noqa: E731
    fx, fy = cx + U(3), gy - U(13)
    lt = lambda t: U(3) * (1 - t) ** 1.5                                # noqa: E731  lean toward the fork
    trunk(S, cx, fy, gy, u(4.4), u(3.4), ACACIA_BARK, seed=cx, roots=1, lean=lt, style='plates')     # noqa
    ca = (cx - U(9), gy - U(25))
    cb = (cx + U(10), gy - U(32))
    _limbs(S, [((fx - 1, fy + 1), (fx - U(3), fy - U(6)), (ca[0] + U(2), ca[1] + U(1)), S.kv(3, 5), S.kv(2, 3)),
               ((fx, fy + 1), (fx + U(2), fy - U(10)), (cb[0] - U(1), cb[1] + U(1)), S.kv(3, 5), S.kv(2, 3)),
               ((fx + U(1), fy - U(8)), (fx + U(5), fy - U(10)), (fx + U(9), fy - U(11)), S.kv(2, 3), 1)],
           ACACIA_BARK)                                                                                  # noqa
    union, vis = set(), []
    for nm, (ox, oy), rx in (('leaves_low', ca, 11), ('leaves', cb, 13)):
        cl = [(ox, oy, U(rx), U(3.5), 0),
              (ox - U(rx * 0.45), oy - U(1.5), U(rx * 0.45), U(2.6), 1),
              (ox + U(rx * 0.4), oy - U(1.8), U(rx * 0.5), U(2.6), 1),
              (ox - U(rx * 0.05), oy + U(0.5), U(rx * 0.5), U(2.4), 2),
              (ox + U(rx * 0.7), oy + U(0.8), U(rx * 0.3), U(2), 2)]
        un, vv, _ = crown(S, cl, R, ramps=ramps, name=nm, z=20 if nm == 'leaves_low' else 30, holes=1, seed=ox,
                          bump=S.kv(1.3, 2.0))
        union |= un
        vis += vv
    x0, y0, x1, _ = bbox(union)
    _tree_extras(S, cx, gy, union, vis, x0, x1, y0, 'acacia', R, ramps, blossom=LEAF_YELLOW)          # noqa
    return {'ground': 'dry'}


def dark_oak(S, cx, gy, size='m', **_):
    """Dark oak: a short, very thick trunk (two logs wide) with heavy roots, a low, wide, dense crown of
    dark puffs, small brown mushrooms in its shade."""
    k, u = S.k, S.u
    sc = SIZES.get(size, 1.0)
    rnd = S.rnd('dark_oak', cx)
    R, ramps = leaf_ramps('dark_oak', S.season)
    U = lambda a: u(a * sc)                                             # noqa: E731
    ccy = gy - U(24)
    _limbs(S, [((cx - U(2), gy - U(9)), (cx - U(8), gy - U(11)), (cx - U(14), ccy + U(3)), S.kv(3, 6), S.kv(2, 3)),
               ((cx + U(2), gy - U(10)), (cx + U(8), gy - U(12)), (cx + U(14), ccy + U(2)), S.kv(3, 6), S.kv(2, 3))],
           DARK_OAK_BARK)                                                                                 # noqa
    trunk(S, cx, ccy, gy, u(9), u(7.5), DARK_OAK_BARK, seed=cx, roots=S.kv(2, 3))                      # noqa

    def J(a):
        return u(a * sc) + rnd.randint(-1, 1)
    clumps = [(cx + J(0), ccy + J(-1), U(20), U(10), 0),
              (cx + J(-9), ccy + J(-7), U(7), U(4.5), 1), (cx + J(3), ccy + J(-8), U(7.5), U(4.5), 1),
              (cx + J(14), ccy + J(-5), U(5.5), U(4), 1),
              (cx + J(-17), ccy + J(-1), U(5), U(4), 2), (cx + J(-5), ccy + J(-2), U(6.5), U(4.5), 2),
              (cx + J(8), ccy + J(-1), U(6.5), U(4.5), 2), (cx + J(18), ccy + J(1), U(4.5), U(4), 2),
              (cx + J(-12), ccy + J(5), U(6), U(4), 3), (cx + J(1), ccy + J(5), U(6.5), U(4), 3),
              (cx + J(13), ccy + J(5), U(6), U(3.5), 3)]
    union, vis, masks = crown(S, clumps, R, ramps=ramps, seed=cx, holes=S.kv(2, 3))
    x0, y0, x1, _ = bbox(union)
    _tree_extras(S, cx, gy, union, vis, x0, x1, y0, 'dark_oak', R, ramps, blossom=CREAM)              # noqa
    if S.season != 'winter':
        ml = S.lay('mushrooms', 50)
        small_mushroom(S, ml, cx - u(9), gy, BROWN_CAP)                                                 # noqa
        small_mushroom(S, ml, cx + u(8), gy + S.kv(1, 2), BROWN_CAP, small=True)                       # noqa
    return {'ground': 'podzol'}


def cherry(S, cx, gy, size='m', **_):
    """Cherry blossom: a dark plum-brown trunk with lenticel stripes that leans and spreads into wide arching
    limbs, a broad crown of pink puffs with blossom tufts hanging under its edge; petals drift down and lie
    on the ground (spring), pink and green in summer, coral-red in autumn, snow on the pink in winter."""
    k, u = S.k, S.u
    sc = SIZES.get(size, 1.0)
    rnd = S.rnd('cherry', cx)
    R, ramps = leaf_ramps('cherry', S.season)
    U = lambda a: u(a * sc)                                             # noqa: E731
    ccy = gy - U(27)
    lt = lambda t: -U(2) * math.sin(t * math.pi)                        # noqa: E731
    _limbs(S, [((cx - 1, gy - U(11)), (cx - U(9), gy - U(15)), (cx - U(15), ccy + U(4)), S.kv(3, 5), 1),
               ((cx, gy - U(13)), (cx + U(8), gy - U(17)), (cx + U(14), ccy + U(2)), S.kv(3, 5), 1),
               ((cx, gy - U(15)), (cx - U(1), ccy + U(2)), (cx + U(2), ccy - U(6)), S.kv(2, 4), 1)], CHERRY_BARK)  # noqa
    trunk(S, cx, ccy + U(3), gy, u(4.6), u(3.4), CHERRY_BARK, seed=cx, style='smooth', lean=lt)        # noqa

    def J(a):
        return u(a * sc) + rnd.randint(-1, 1)
    clumps = [(cx + J(0), ccy + J(-1), U(18), U(9), 0),
              (cx + J(-7), ccy + J(-6), U(7), U(4.5), 1), (cx + J(5), ccy + J(-7), U(7), U(4.5), 1),
              (cx + J(-15), ccy + J(0), U(5.5), U(4.5), 2), (cx + J(-2), ccy + J(-1), U(6.5), U(4.5), 2),
              (cx + J(13), ccy + J(-1), U(6), U(4.5), 2),
              (cx + J(-10), ccy + J(5), U(6), U(3.5), 3), (cx + J(4), ccy + J(5), U(6.5), U(3.5), 3),
              (cx + J(17), ccy + J(4), U(4), U(3), 3)]
    union, vis, masks = crown(S, clumps, R, ramps=ramps, seed=cx, holes=S.kv(2, 3))
    hang = S.lay('blossom_tufts', 36)                                   # blossom clusters under the crown
    bot = cols(union)
    Rt = ramps[0] if ramps else R
    hm = set()
    xs = sorted(bot)
    i = 0
    while i < len(xs):
        x = xs[i]
        if abs(x - cx) > u(3) and rnd.random() < 0.5:
            r = S.kv(1.2, 1.9)
            hm |= {q for q in disc(x + r, bot[x][1] + r * 0.6, r, r * 0.9) if q not in union}
            i += S.kv(3, 5)
        i += 1
    for (x, y) in hm:
        t = LT if ((x - 1, y) not in hm and (x, y - 1) not in hm) else BS if (x, y + 1) in hm else DK
        hang[(x, y)] = Rt[t]
    outline(hang, hm, Rt, skip=union)
    x0, y0, x1, _ = bbox(union)
    _tree_extras(S, cx, gy, union, vis, x0, x1, y0, 'cherry', R, ramps,
                 blossom=LILY_WHITE, litter_ramps=[CHERRY_LEAF, PINK_PETALS])                           # noqa
    if S.season == 'spring':
        fl = S.lay('falling_petals', 70)
        falling(S, fl, x0 - u(3), x1 + u(3), y0 + u(8), gy - u(3), [CHERRY_LEAF, PINK_PETALS], S.kv(6, 10),  # noqa
                seed=cx + 3)
    return {'ground': 'grass', 'petals': S.season in ('spring', 'summer')}


def palm(S, cx, gy, size='m', **_):
    """Palm: a curved ringed trunk, a burst of long arching fronds (a lit midrib with leaflets hanging from
    both sides, the far fronds darker), a cluster of coconuts under the crown."""
    k, u = S.k, S.u
    sc = SIZES.get(size, 1.0)
    rnd = S.rnd('palm', cx)
    R = PALM_LEAF                                                                                      # noqa
    U = lambda a: u(a * sc)                                             # noqa: E731
    Ht = U(36)
    bend = U(8)
    lt = lambda t: bend * (1 - t) ** 2                                  # noqa: E731
    trunk(S, cx, gy - Ht, gy, u(4.6), u(3.4), PALM_BARK, seed=cx, roots=1, lean=lt, style='rings')     # noqa
    tx, ty = cx + bend, gy - Ht
    fr_back = S.lay('fronds_back', 18)
    fr = S.lay('fronds', 30, cast=(S.kv(1, 2), S.kv(1, 2), 1))
    for back, lay, angs in ((True, fr_back, (-150, -100, -60, -25)), (False, fr, (-178, -135, -40, 5, 200, -15))):
        fm = set()
        for a in angs:
            L = U(rnd.uniform(15, 19)) if not back else U(rnd.uniform(11, 14))
            ar = math.radians(a)
            ex, ey = tx + L * math.cos(ar), ty + L * math.sin(ar) + L * 0.35
            mx, my = tx + L * 0.5 * math.cos(ar), ty + L * 0.5 * math.sin(ar) - U(3)
            path = bezier((tx, ty), (mx, my), (ex, ey))
            n = len(path)
            side_dir = 1 if ex > tx else -1
            for i, (x, y) in enumerate(path):
                f = i / max(1, n - 1)
                lay[(x, y)] = R[LT if not back else BS]
                fm.add((x, y))
                if i < S.kv(2, 3):
                    continue
                Lf = int(round((1 - f) * S.kv(3.5, 7) + 1))
                if i % S.kv(1, 2) == 0:
                    for j in range(1, Lf + 1):                        # leaflets hang down from the midrib
                        for sd, tt in ((-1, BS), (1, DK)):
                            q = (x + sd * side_dir * (j // 2), y + j)
                            if q not in fm:
                                lay[q] = R[tt if not back else max(SH, tt - 1)]
                                fm.add(q)
            lay[path[-1]] = R[BS]
        if back:
            outline(lay, fm, R, dark=R[O], lit=R[SH])
        else:
            outline(lay, fm, R)
    nut = S.lay('coconuts', 24)
    for (dx, dy) in ((-2, 1), (1, 2), (-1, 3)):
        stamp_fruit(S, nut, tx + u(dx) - S.kv(1, 2), ty + u(dy) - S.kv(1, 2), SEEDS, 'coconut')         # noqa
    outline(nut, set(nut), SEEDS)                                                                      # noqa
    union = set(fr) | set(fr_back)
    x0, y0, x1, _ = bbox(union)
    if S.season == 'winter':
        snow_cap(S, [set(fr_back), set(fr)], seed=cx, depth=S.kv(1, 2))
    ground_shadow(S, cx - u(2), x1 + u(3), gy, contact=(cx - u(3), cx + u(3)), steps=2)
    return {'ground': 'sand'}


def dead_tree(S, cx, gy, size='m', **_):
    """Dead tree: a weathered grey trunk with plate cracks and a dark hollow, bare limbs splitting into
    twigs (recursive, thinner at every fork); snow lines the limbs in winter."""
    k, u = S.k, S.u
    sc = SIZES.get(size, 1.0)
    rnd = S.rnd('dead', cx)
    U = lambda a: u(a * sc)                                             # noqa: E731
    top = gy - U(24)
    lt = lambda t: U(1.5) * math.sin(t * 3.0)                           # noqa: E731
    specs = []

    def grow(x, y, ang, L, w, depth):
        a = math.radians(ang)
        ex, ey = x + L * math.cos(a), y + L * math.sin(a)
        mx, my = x + L * 0.5 * math.cos(a) + rnd.uniform(-1, 1) * S.k, y + L * 0.5 * math.sin(a)
        specs.append(((x, y), (mx, my), (ex, ey), w, max(1, w * 0.6)))
        if depth > 0:
            for d in (-1, 1):
                grow(ex, ey, ang + d * rnd.uniform(22, 38), L * rnd.uniform(0.55, 0.72), max(1, w * 0.6), depth - 1)
    grow(cx, top + U(3), -125, U(10), S.kv(3, 5), 2)
    grow(cx + 1, top + U(1), -60, U(11), S.kv(3, 5), 2)
    grow(cx - 1, gy - U(13), -165, U(7), S.kv(2, 3), 1)
    bm = _limbs(S, [((int(a[0]), int(a[1])), b, (int(c[0]), int(c[1])), w0, w1) for a, b, c, w0, w1 in specs],
                DEAD_BARK)                                                                              # noqa
    tm = trunk(S, cx, top, gy, u(5), u(3.4), DEAD_BARK, seed=cx, style='plates', lean=lt, roots=S.kv(2, 2))  # noqa
    lay = S.lay('trunk')
    hx, hy = cx, gy - U(12)                                          # the hollow: dark oval, lit lower lip
    for (x, y) in disc(hx, hy, S.kv(1.2, 2.2), S.kv(1.8, 3.2)):
        if (x, y) in tm:
            lay[(x, y)] = DEAD_BARK[O] if y < hy + S.kv(0.5, 1) else DEAD_BARK[SH]                      # noqa
    for x in range(int(hx - S.kv(1, 2)), int(hx + S.kv(1, 2)) + 1):
        if (x, int(hy + S.kv(2, 3))) in tm:
            lay[(x, int(hy + S.kv(2, 3)))] = DEAD_BARK[LT]                                               # noqa
    if S.season == 'winter':
        snow_cap(S, [bm, tm], seed=cx, depth=S.kv(1, 2))
    x0, y0, x1, _ = bbox(bm | tm)
    ground_shadow(S, cx - u(3), x1 + u(3), gy, contact=(cx - u(3), cx + u(3)), steps=2)
    return {'ground': 'dirt' if S.season != 'winter' else 'snow'}


def swamp_oak(S, cx, gy, size='m', **_):
    """Swamp oak: the oak's shape in olive swamp leaves with vines hanging from every puff."""
    oak(S, cx, gy, size=size, kind='swamp')
    rnd = S.rnd('swamp', cx)
    union = S.mask_of(*[p['name'][len(S.prefix):] for p in S.parts if p['name'].startswith(S.prefix + 'leaves')])
    bot = cols(union)
    starts = []
    for x in range(min(bot), max(bot) + 1, S.kv(3, 5)):
        if x in bot and abs(x - cx) > S.u(3) and rnd.random() < 0.75:
            starts.append((x, bot[x][1] - 1, rnd.randint(S.u(4), S.u(12))))
    vines(S, S.lay('vines', 45), starts, VINE, seed=cx)                                              # noqa
    return {'ground': 'swamp'}


def giant_mushroom(S, cx, gy, size='m', kind='red', **_):
    """Giant mushroom: a thick cream stem (cylinder-shaded, fibrous streaks, a ring), a cap lit as a dome -
    red with white spots that follow the curve, or a broad flat brown cap - with the gills in shadow under
    its rim; snow on the cap in winter."""
    k, u = S.k, S.u
    sc = SIZES.get(size, 1.0)
    rnd = S.rnd('mushroom', kind, cx)
    U = lambda a: u(a * sc)                                             # noqa: E731
    red = kind == 'red'
    R = RED_CAP if red else BROWN_CAP                                                                 # noqa
    ch = U(19) if red else U(21)                                         # cap rim height above ground
    rx = U(14) if red else U(19)
    ry = U(11) if red else U(5)
    sw = u(8) if red else u(7)
    st = S.lay('stem', 5)
    sm = set()
    for y in range(gy - ch, gy + 1):
        t = (y - (gy - ch)) / ch
        w = sw * (1 + 0.25 * t * t)
        for x in range(int(round(cx - w / 2)), int(round(cx - w / 2 + w))):
            sm.add((x, y))
    sp = _spans(sm)
    for (x, y) in sm:
        xl, xr = sp[y]
        st[(x, y)] = MUSH_STEM[cyl_tone(((x - xl) + 0.5) / (xr - xl + 1) * 2 - 1)]                     # noqa
    if red:                                                              # a skirt ring under the cap
        ry_ = gy - ch + U(6)
        for x in range(sp[ry_][0] - 1, sp[ry_][1] + 2):
            for j in range(S.kv(2, 3)):
                sm.add((x, ry_ + j))
                st[(x, ry_ + j)] = MUSH_STEM[HI if j == 0 and x < cx else LT if j == 0 else DK if x > cx else BS]  # noqa
    for x in range(sp[gy][0] - S.kv(1, 2), sp[gy][1] + S.kv(2, 3)):    # the bulb at the foot
        for j in range(S.kv(2, 3)):
            if (x, gy - j) not in sm:
                sm.add((x, gy - j))
                st[(x, gy - j)] = MUSH_STEM[LT if x < cx else DK]                                        # noqa
    sp = _spans(sm)
    for (x, y) in sorted(sm):                                             # fibres along the stem
        if rnd.random() < S.kv(0.06, 0.05) and y < gy - 2:
            for j in range(rnd.randint(2, S.kv(3, 6))):
                if (x, y + j) in sm:
                    st[(x, y + j)] = darker(st[(x, y + j)])
    for y in range(gy - ch, gy - ch + S.kv(3, 5)):                       # the cap's shadow on the stem top
        for x in range(*(lambda a: (a[0], a[1] + 1))(sp[y])):
            st[(x, y)] = MUSH_STEM[DK if x < cx + sw / 3 else SH]                                   # noqa
    outline(st, sm, MUSH_STEM, skip={(x, gy + 1) for x in range(-999, 999)})                          # noqa
    cap = S.lay('cap', 20, cast=(S.kv(1, 2), S.kv(1, 2), 1))
    yc = gy - ch
    cm = set()
    for (x, y) in disc(cx, yc, rx, ry):
        if y <= yc + S.kv(1, 2):
            cm.add((x, y))
    if not red:                                                          # a flat cap: a low dome on a wide brim
        cm |= {(x, y) for (x, y) in disc(cx, yc, rx, S.kv(2.2, 3.5))}
    for (x, y) in cm:
        nx, ny = (x + 0.5 - cx) / rx, (y + 0.5 - (yc + S.kv(1, 2))) / (ry + S.kv(1, 2))
        t = sphere_tone(nx, ny, cuts=(0.9, 0.62, 0.25, -0.05))
        if (x, y + 1) not in cm:
            t = max(SH, min(t, DK))
        cap[(x, y)] = R[t]
    gl = S.lay('gills', 19)
    gm = set()
    for x in range(cx - rx + S.kv(1, 2), cx + rx - S.kv(1, 2)):
        d = abs(x + 0.5 - cx) / rx
        for j in range(1, S.kv(2, 3) + (1 if d < 0.6 else 0)):
            gm.add((x, yc + S.kv(1, 2) + j))
    for (x, y) in gm:
        gl[(x, y)] = GILLS[DK if (x % S.kv(2, 3) == 0) else BS] if x < cx + rx * 0.3 else GILLS[SH]   # noqa
    outline(gl, gm, GILLS, skip=cm)                                                                  # noqa
    if red:
        spots = S.lay('spots', 25)
        pts = []
        for _ in range(60):
            a = rnd.uniform(-math.pi * 0.95, -math.pi * 0.05)
            r = rnd.uniform(0.25, 0.85)
            x, y = cx + math.cos(a) * rx * r, yc + S.kv(1, 2) + math.sin(a) * ry * r
            if all(math.hypot(x - q[0], y - q[1]) > S.kv(5, 8) for q in pts):
                pts.append((x, y))
            if len(pts) >= S.kv(7, 9):
                break
        for (x, y) in pts:
            nx = (x - cx) / rx
            w = S.kv(2.2, 3.6) * (1 - 0.5 * abs(nx))
            h = S.kv(1.4, 2.4) * (1 - 0.3 * abs(nx))
            for (a, b) in disc(x, y, w / 2 + 0.3, h / 2 + 0.2):
                if (a, b) in cm and (a, b + 1) in cm:
                    lit = cap[(a, b)] in (R[HI], R[LT], R[BS])
                    spots[(a, b)] = CREAM[HI if lit and (a - 1, b) not in spots else LT if lit else DK]   # noqa
    if not red:                                                          # speckles on the brown cap
        for (x, y) in sorted(cm):
            if rnd.random() < S.kv(0.05, 0.04) and (x + 1, y) in cm and (x, y + 2) in cm and (x, y - 1) in cm:
                t = tone_of(cap[(x, y)])
                cap[(x, y)] = R[max(SH, t - 1)]
                cap[(x + 1, y)] = R[max(SH, t - 1)] if k == 2 else cap[(x + 1, y)]
                if (x - 1, y - 1) in cm and t < HI:
                    cap[(x - 1, y - 1)] = R[min(HI, t + 1)]
    outline(cap, cm, R)
    if S.season == 'winter':
        snow_cap(S, [cm], seed=cx, depth=S.kv(2, 3))
    ground_shadow(S, cx - u(2), cx + rx + u(4), gy, contact=(cx - sw // 2 - 1, cx + sw // 2 + 1), steps=2)
    return {'ground': 'grass' if red else 'podzol'}


def small_mushroom(S, lay, x, gy, R, small=False):
    """A small mushroom stamped into a layer: a cream stem and a dome cap lit from the top-left (red caps get
    two white spots). x = stem left, gy = ground."""
    k = S.k
    sh = (S.kv(2, 3) if small else S.kv(3, 5))
    sw = S.kv(1, 2)
    m = set()
    for j in range(sh):
        for i in range(sw):
            lay[(x + i, gy - j)] = MUSH_STEM[LT if i == 0 else BS]                                    # noqa
            m.add((x + i, gy - j))
    r = (S.kv(2, 3.5) if not small else S.kv(1.6, 2.6))
    ccx, ccy = x + sw / 2, gy - sh + 0.5
    cm = {(a, b) for (a, b) in disc(ccx, ccy, r, r * 0.8) if b <= ccy}
    top_y = min(b for _, b in cm)
    for (a, b) in cm:
        if k == 1:                                     # 16 px: lit top row, base, dark brim
            t = LT if b == top_y else DK if (a, b + 1) not in cm else BS
        else:
            t = sphere_tone((a + 0.5 - ccx) / r, (b + 0.5 - ccy + r * 0.3) / r)
        lay[(a, b)] = R[t]
    if R is RED_CAP and k == 2:                                                                       # noqa
        lay[(int(ccx) - 1, int(ccy) - 2)] = CREAM[HI]                                                   # noqa
        lay[(int(ccx) + 1, int(ccy) - 1)] = CREAM[LT]                                                   # noqa
    m |= cm
    outline(lay, m, R, skip={(q, gy + 1) for q in range(x - 9, x + 9)})
    return m


# ------------------------------------------------------------------ plants: stems, leaves, blooms
def stem(S, lay, x, gy, h, R=None, lean=0, curve=0, m=None):
    """A flower stem from the ground (x, gy) up h px: 1 px at k=1 (base tone, darker low down), 2 px HD (lit
    left, dark right). Returns the path (top = path[-1]) and adds to mask m."""
    R = R or PLANT                                                                                  # noqa
    m = set() if m is None else m
    path = bezier((x, gy), (x + curve, gy - h / 2), (x + lean, gy - h))
    for i, (px_, py_) in enumerate(path):
        low = i < len(path) * 0.3
        if S.k == 1:
            lay[(px_, py_)] = R[DK if low else BS]
            m.add((px_, py_))
        else:
            lay[(px_, py_)] = R[BS if low else LT]
            lay[(px_ + 1, py_)] = R[SH if low else DK]
            m |= {(px_, py_), (px_ + 1, py_)}
    return path, m


def leaf(S, lay, x, y, side, R=None, size=1.0, up=0.6, m=None):
    """A leaf growing from (x, y) toward side (-1 left, 1 right) and up: a pointed lens - its upper half a step
    lighter (lit), its lower half and the far tip darker; a midrib at HD. k=1: 3-4 px."""
    R = R or PLANT                                                                                  # noqa
    m = set() if m is None else m
    L = max(2, int(round(S.kv(3.4, 7.5) * size)))
    pts = {}
    if S.k == 1:                                   # a 1 px stroke, lit (or base on the shaded side), one
        for i in range(1, L + 1):                  # shadow pixel under its middle
            pts[(x + side * i, int(round(y - i * up)))] = LT if side < 0 else BS
        mid = (x + side * (L // 2 + 1), int(round(y - (L // 2 + 1) * up)) + 1)
        if mid not in pts:
            pts[mid] = DK
        for q, t in pts.items():
            lay[q] = R[t]
        m |= set(pts)
        return m
    for i in range(1, L + 1):
        cx_ = x + side * i
        cy_ = y - i * up
        hw = 0 if S.k == 1 and (i == L or i == 1) else (1 if S.k == 1 else max(0, round(1.8 * math.sin(math.pi * i / (L + 0.6)))))
        for j in range(-hw, hw + 1):
            q = (cx_, int(round(cy_ + j)))
            lit = side < 0
            t = (LT if lit else BS) if j < 0 else (BS if lit else DK) if j == 0 else DK
            if S.k == 1:
                t = LT if (j < 0 or (hw == 0 and lit)) else (BS if j == 0 else DK)
            if S.k == 2 and j == 0 and 1 < i < L - 1:
                t = BS if lit else DK                                  # midrib
            pts[q] = t
    for q, t in pts.items():
        lay[q] = R[t]
    m |= set(pts)
    return m


def bloom(S, lay, cx, cy, R, n, pr, ring, squash=0.8, eye=None, er=0, rot=0.0, m=None, eye_tone=None):
    """A flower head facing the viewer, tilted up: n petals round (cx, cy) on a ring, the far (upper) petals
    drawn first so the near ones overlap them; each petal lit as a small ball (top-left light, its lower
    right rim darker - the crease between petals); an eye disc in its own ramp. Returns the mask."""
    m = set() if m is None else m
    angs = sorted((2 * math.pi * i / n + rot for i in range(n)), key=lambda a: math.sin(a))
    for a in angs:
        px_, py_ = cx + math.cos(a) * ring, cy + math.sin(a) * ring * squash
        pts = disc(px_, py_, pr, pr * squash * 1.08)
        for (x, y) in pts:
            g = sphere_tone((x + 0.5 - cx) / (ring + pr), (y + 0.5 - cy) / ((ring + pr) * squash))
            if S.k == 1:                          # 16 px: the head is one lit ball (petals by the outline)
                t = g
            else:
                t = sphere_tone((x + 0.5 - px_) / pr, (y + 0.5 - py_) / (pr * squash * 1.08), cuts=(0.95, 0.5, 0.1, -0.3))
                t = max(SH, min(HI, round((t + g) / 2)))
            lay[(x, y)] = R[t]
        m |= pts
    if eye and er:
        for (x, y) in disc(cx, cy, er, er * squash):
            t = eye_tone if eye_tone is not None else sphere_tone((x + 0.5 - cx) / er, (y + 0.5 - cy) / (er * squash))
            lay[(x, y)] = eye[t]
            m.add((x, y))
    return m


def _flower(S, cx, gy, h, head, leaves=((0.35, -1, 1.0), (0.55, 1, 0.9)), R=None, lean=0, curve=0, name='flower'):
    """Stem + leaves + a head drawn by head(lay, x, y) at the stem's top; outlined per part."""
    R = R or PLANT                                                                                  # noqa
    st = S.lay('stem', 5)
    path, sm = stem(S, st, cx, gy, h, R, lean=lean, curve=curve)
    lm = set()
    lv = S.lay('leaves', 6)
    for (f, side, size) in leaves:
        px_, py_ = path[int(len(path) * f)]
        leaf(S, lv, px_ + (1 if side > 0 and S.k == 2 else 0), py_, side, R, size=size, m=lm)
    outline(lv, lm, R, skip=sm | {(q, gy + 1) for q in range(cx - 40, cx + 40)})
    outline(st, sm, R, skip=lm | {(q, gy + 1) for q in range(cx - 40, cx + 40)})
    hd = S.lay(name, 10)
    hm = head(hd, *path[-1])
    return path, hm


def _head_outline(S, lay, m, R, dark=None):
    outline(lay, m, R, dark=dark)


def poppy(S, cx, gy, **_):
    """Poppy: four round red petals in a shallow cup round a black-green seed eye, two leaves."""
    k = S.k

    def head(lay, x, y):
        m = bloom(S, lay, x + S.kv(0, 1), y - S.kv(2, 4), POPPY, 5, S.kv(1.6, 2.9), S.kv(1.2, 2.4), squash=0.8,    # noqa
                  eye=STALK, er=S.kv(0.8, 1.4), eye_tone=SH, rot=0.3)                                                # noqa
        _head_outline(S, lay, m, POPPY)                                                                       # noqa
        return m
    _flower(S, cx, gy, S.kv(8, 16), head, lean=S.kv(0, 1))
    _small_shadow(S, cx, gy)
    return {'ground': 'grass', 'ground_opts': {}}


def dandelion(S, cx, gy, **_):
    """Dandelion: a dense yellow puff of tiny rays (lit top-left, ragged rim), a low rosette of toothed
    leaves."""
    def head(lay, x, y):
        m = bloom(S, lay, x, y - S.kv(2, 3), DANDELION, 9, S.kv(1.1, 1.9), S.kv(1.4, 2.8), squash=0.75,       # noqa
                  eye=DANDELION, er=S.kv(1.2, 2.0), rot=0.2)                                                   # noqa
        _head_outline(S, lay, m, DANDELION)                                                                 # noqa
        return m
    _flower(S, cx, gy, S.kv(7, 13), head, leaves=((0.12, -1, 1.1), (0.15, 1, 1.0)))
    _small_shadow(S, cx, gy)
    return {'ground': 'grass'}


def cornflower(S, cx, gy, **_):
    """Cornflower: a ragged ring of small blue florets round a dark-blue eye on a tall thin stem."""
    def head(lay, x, y):
        m = bloom(S, lay, x, y - S.kv(2, 3), CORNFLOWER, 8, S.kv(1.0, 1.7), S.kv(1.6, 3.0), squash=0.8,       # noqa
                  eye=CORNFLOWER, er=S.kv(0.9, 1.5), eye_tone=SH, rot=0.4)                                     # noqa
        _head_outline(S, lay, m, CORNFLOWER)                                                                # noqa
        return m
    _flower(S, cx, gy, S.kv(9, 18), head, leaves=((0.3, -1, 0.9), (0.5, 1, 0.8)), curve=S.kv(1, 1))
    _small_shadow(S, cx, gy)
    return {'ground': 'grass'}


def blue_orchid(S, cx, gy, **_):
    """Blue orchid: five sky-blue star petals with a white heart, arching stem (swamps)."""
    def head(lay, x, y):
        m = bloom(S, lay, x, y - S.kv(2, 3), ORCHID, 5, S.kv(1.3, 2.4), S.kv(1.4, 2.6), squash=0.85,         # noqa
                  eye=LILY_WHITE, er=S.kv(0.7, 1.2), eye_tone=HI, rot=-1.57)                                   # noqa
        _head_outline(S, lay, m, ORCHID)                                                                    # noqa
        return m
    _flower(S, cx, gy, S.kv(8, 15), head, curve=S.kv(-2, -3), lean=S.kv(1, 2))
    _small_shadow(S, cx, gy)
    return {'ground': 'grass'}


def tulip(S, cx, gy, color='red', **_):
    """Tulip: a closed cup of three pointed petals - the left one lit, the middle base with a bright edge,
    the right one in shade - on a straight stem with two long blade leaves."""
    k = S.k
    R = {'red': TULIP_RED, 'orange': TULIP_ORANGE, 'white': TULIP_WHITE, 'pink': TULIP_PINK}[color]   # noqa

    def head(lay, x, y):
        w, h = S.kv(5, 9), S.kv(5, 10)
        x0 = x - w // 2 + (1 if k == 2 else 0)
        m = set()
        for j in range(h):
            f = j / (h - 1)
            half = (w / 2) * (0.75 + 0.25 * math.sin(math.pi * min(1, f * 1.3)))
            if j == h - 1:
                half -= 1
            for i in range(w):
                d = (i + 0.5 - w / 2)
                if abs(d) <= half:
                    m.add((x0 + i, y - h + j))
        tips = set()
        for i in range(w):                                     # pointed petal tips on top
            if i in (0, w // 2, w - 1):
                tips.add((x0 + i, y - h - 1))
                if k == 2:
                    tips.add((x0 + i + (1 if i == 0 else -1 if i == w - 1 else 0), y - h - 2) if i != w // 2 else (x0 + i, y - h - 2))
        m |= tips
        for (px_, py_) in m:
            i = px_ - x0
            t = LT if i < w / 3 else BS if i < 2 * w / 3 else DK
            if i < w / 3 and py_ < y - h + 2:
                t = HI
            if py_ >= y - S.kv(2, 3) and i >= w / 3:
                t = max(SH, t - 1)
            if k == 2 and i in (w // 3, 2 * w // 3) and py_ > y - h + 1:
                t = max(SH, t - 1)                             # petal seams
            lay[(px_, py_)] = R[t]
        _head_outline(S, lay, m, R)
        return m
    _flower(S, cx, gy, S.kv(8, 15), head, leaves=((0.15, -1, 1.2), (0.25, 1, 1.1)))
    _small_shadow(S, cx, gy)
    return {'ground': 'grass'}


def allium(S, cx, gy, **_):
    """Allium: a purple ball of tiny star florets (lighter florets on the lit side, darker gaps) on a tall
    bare stem, strap leaves at the foot."""
    k = S.k
    rnd = S.rnd('allium', cx)

    def head(lay, x, y):
        r = S.kv(2.6, 5.2)
        hx, hy = x + 0.5, y - r + 0.5
        m = disc(hx, hy, r)
        for (px_, py_) in m:
            lay[(px_, py_)] = ALLIUM[sphere_tone((px_ + 0.5 - hx) / r, (py_ + 0.5 - hy) / r)]                   # noqa
        for (px_, py_) in sorted(m):                           # florets: small crosses one step lighter
            if rnd.random() < S.kv(0.12, 0.1) and all((px_ + a, py_ + b) in m for a, b in N4):
                t = tone_of(lay[(px_, py_)])
                lay[(px_, py_)] = ALLIUM[min(HI, t + 1)]                                                        # noqa
                if k == 2:
                    for a, b in N4:
                        if rnd.random() < 0.5:
                            lay[(px_ + a, py_ + b)] = ALLIUM[min(HI, t + 1)]                                    # noqa
        rim = {p for p in edge_ring(m)}
        for (px_, py_) in sorted(rim):                        # a ragged rim: florets stick out
            if rnd.random() < 0.25:
                lay[(px_, py_)] = ALLIUM[BS if px_ < hx else DK]                                                # noqa
                m = m | {(px_, py_)}
        _head_outline(S, lay, m, ALLIUM)                                                                      # noqa
        return m
    _flower(S, cx, gy, S.kv(10, 20), head, leaves=((0.06, -1, 1.3), (0.08, 1, 1.2)))
    _small_shadow(S, cx, gy)
    return {'ground': 'grass'}


def lily_of_the_valley(S, cx, gy, **_):
    """Lily of the valley: two broad upright leaves, an arching stem with white bells hanging in a row
    (each bell lit on the left, a dark mouth with a flared rim)."""
    k = S.k
    lv = S.lay('leaves', 6)
    lm = set()
    for (dx, side, hh) in ((-1, -1, S.kv(9, 18)), (1, 1, S.kv(7, 14))):   # broad leaves: tall lenses
        for j in range(hh):
            f = j / hh
            w = max(1, int(round(S.kv(2.2, 4.4) * math.sin(math.pi * min(0.98, f * 0.95 + 0.05)))))
            x0 = cx + dx + (side * int(f * S.kv(2, 4)))
            for i in range(w):
                q = (x0 + (i if side > 0 else -i), gy - j)
                t = (LT if side < 0 else BS) if i < w / 2 else (BS if side < 0 else DK)
                lv[q] = PLANT[t]                                                                       # noqa
                lm.add(q)
    outline(lv, lm, PLANT, skip={(q, gy + 1) for q in range(cx - 40, cx + 40)})                        # noqa
    st = S.lay('stem', 7)
    path = bezier((cx, gy - S.kv(2, 4)), (cx + S.kv(1, 2), gy - S.kv(14, 28)), (cx + S.kv(6, 12), gy - S.kv(9, 18)))
    sm = set()
    for q in path:
        st[q] = PLANT[DK]                                                                              # noqa
        sm.add(q)
    hd = S.lay('flower', 10)
    hm = set()
    for f in (0.55, 0.7, 0.85, 1.0):
        bx, by = path[min(len(path) - 1, int(len(path) * f))]
        if k == 1:
            bell = {(0, 1): HI, (1, 1): LT, (0, 2): LT, (1, 2): DK}
        else:
            bell = {(0, 1): LT, (1, 1): HI, (2, 1): LT, (-1, 2): LT, (0, 2): HI, (1, 2): LT, (2, 2): BS,
                    (-1, 3): BS, (0, 3): LT, (1, 3): BS, (2, 3): DK, (-1, 4): DK, (0, 4): SH, (1, 4): SH, (2, 4): DK}
        for (a, b), t in bell.items():
            hd[(bx + a, by + b)] = LILY_WHITE[t]                                                       # noqa
            hm.add((bx + a, by + b))
    outline(hd, hm, LILY_WHITE, skip=sm)                                                               # noqa
    _small_shadow(S, cx, gy, w=S.kv(4, 8))
    return {'ground': 'grass'}


def sunflower(S, cx, gy, **_):
    """Sunflower: two blocks tall - a thick stem with big heart leaves, a heavy head turned a little to the
    right: a ring of pointed yellow petals round a brown seed disc with a spiral of lighter seeds."""
    k = S.k
    rnd = S.rnd('sunflower', cx)
    h = S.kv(24, 48)
    st = S.lay('stem', 5)
    path, sm = stem(S, st, cx, gy, h, STALK, curve=S.kv(1, 2), lean=S.kv(1, 2))                       # noqa
    if k == 1:
        for (x, y) in path[:-2]:
            st[(x + 1, y)] = STALK[DK]                                                                # noqa
            sm.add((x + 1, y))
    lv = S.lay('leaves', 6)
    lm = set()
    for (f, side, size) in ((0.3, -1, 1.5), (0.5, 1, 1.4), (0.72, -1, 1.1)):
        px_, py_ = path[int(len(path) * f)]
        leaf(S, lv, px_ + (1 if side > 0 else 0), py_, side, STALK, size=size, up=0.35, m=lm)          # noqa
    outline(lv, lm, STALK, skip=sm)                                                                    # noqa
    outline(st, sm, STALK, skip=lm | {(q, gy + 1) for q in range(cx - 40, cx + 40)})                  # noqa
    hd = S.lay('flower', 10)
    hx, hy = path[-1][0] + S.kv(1, 2), path[-1][1] - S.kv(3, 6)
    m = bloom(S, hd, hx, hy, SUNFLOWER, 14, S.kv(1.4, 2.6), S.kv(3.6, 7.4), squash=0.95, rot=0.1)      # noqa
    er = S.kv(3.0, 6.0)
    for (x, y) in disc(hx + 0.5, hy + 0.5, er, er * 0.95):
        t = sphere_tone((x - hx) / er, (y - hy) / er, cuts=(0.95, 0.7, 0.2, -0.2))
        hd[(x, y)] = SEEDS[max(SH, t - 1)]                                                             # noqa
        m.add((x, y))
    for i in range(S.kv(6, 22)):                                    # seeds in a spiral
        a = i * 2.4
        r = er * 0.85 * math.sqrt((i + 0.5) / S.kv(6, 22))
        q = (int(round(hx + 0.5 + math.cos(a) * r)), int(round(hy + 0.5 + math.sin(a) * r)))
        if q in m:
            hd[q] = SEEDS[LT if (q[0] - hx) + (q[1] - hy) < 0 else BS]                                 # noqa
    outline(hd, m, SUNFLOWER)                                                                          # noqa
    _small_shadow(S, cx, gy, w=S.kv(6, 12))
    return {'ground': 'grass'}


def _small_shadow(S, cx, gy, w=None):
    w = w or S.kv(3, 6)
    ground_shadow(S, cx - 1, cx + w, gy, rows=S.kv(1, 2), contact=(cx - 1, cx + S.kv(1, 2)), steps=1)


def tall_grass(S, cx, gy, size='m', R=None, n=None, h=None, **_):
    """Tall grass: a bunch of blades fanning out from one tuft - back blades darker, front blades lit, each a
    tapering curve (2 -> 1 px, HD 3 -> 1 with a lit edge), tips bending away from the centre."""
    k = S.k
    R = R or BLADE                                                                                 # noqa
    rnd = S.rnd('grass', cx)
    sc = SIZES.get(size, 1.0)
    n = n or S.kv(8, 13)
    h = h or S.kv(14, 28) * sc
    blades = []
    for i in range(n):
        f = (i + 0.5) / n * 2 - 1
        hh = h * (0.55 + 0.45 * (1 - abs(f)) ) * rnd.uniform(0.8, 1.05)
        depth = rnd.choice((0, 1, 1, 2))
        blades.append((depth, f, hh))
    blades.sort(key=lambda b: b[0])
    for idx, (depth, f, hh) in enumerate(blades):
        lay = S.lay(['blades_back', 'blades', 'blades_front'][depth], 4 + depth)
        x0 = cx + int(round(f * S.kv(3, 6)))
        tipx = x0 + int(round(f * hh * 0.55)) + rnd.randint(-1, 1)
        path = bezier((x0, gy), (x0 + int(f * hh * 0.1), gy - hh * 0.6), (tipx, gy - int(hh)))
        n_ = len(path)
        for j, (x, y) in enumerate(path):
            w = S.kv(2, 3) if j < n_ * 0.35 else S.kv(1, 2) if j < n_ * 0.75 else 1
            for i in range(w):
                t = [DK, BS, LT][depth]
                if w > 1 and i == w - 1:
                    t = max(SH, t - 1)
                if k == 2 and i == 0 and depth == 2 and j > n_ * 0.2:
                    t = HI if j % 5 else LT
                if j < 2:
                    t = max(SH, t - 1)
                lay[(x + i, y)] = R[t]
    for nm in ('blades_back', 'blades', 'blades_front'):
        lay = S.lay(nm)
        outline(lay, set(lay), R, lit_side=False,
                skip={(q, gy + 1) for q in range(cx - 60, cx + 60)}) if k == 2 else None
    _small_shadow(S, cx, gy, w=S.kv(5, 10))
    return {'ground': 'grass'}


def fern(S, cx, gy, size='m', **_):
    """Fern: five fronds arching up and out from one crown - each a 1 px rachis (a quadratic arch whose tip
    droops) with paired leaflets angled toward the tip and shrinking along it; the upper / left leaflets lit,
    the lower / right ones dark; back fronds darker, front fronds lit."""
    k = S.k
    rnd = S.rnd('fern', cx)
    sc = SIZES.get(size, 1.0)
    H = S.kv(13, 26) * sc
    fr = [(-0.45, 0.8, 0), (0.5, 0.75, 0), (0.0, 1.0, 1), (-1.0, 0.5, 2), (1.0, 0.45, 2)]
    for (reach, hgt, depth) in fr:
        lay = S.lay(['fronds_back', 'fronds', 'fronds_front'][depth], 4 + depth)
        h = H * hgt * rnd.uniform(0.92, 1.05)
        rx = reach * H * 0.7
        tip = (cx + rx, gy - h * (0.78 if abs(reach) > 0.3 else 0.95))
        ctrl = (cx + rx * 0.15, gy - h * 1.25)
        path = bezier((cx, gy - 1), ctrl, tip)
        n_ = len(path)
        base_t = [DK, BS, LT][depth]
        m = set()
        for j, (x, y) in enumerate(path):
            lay[(x, y)] = FERN[max(SH, base_t - 1)]                                                      # noqa
            m.add((x, y))
        for j in range(2, n_ - 1, 2):
            (x, y), (x2, y2) = path[j], path[min(n_ - 1, j + 2)]
            dx, dy = x2 - x, y2 - y
            ln = math.hypot(dx, dy) or 1
            dx, dy = dx / ln, dy / ln
            Lf = max(1, int(round((1 - j / n_) * S.kv(2.6, 5.5) + 0.3)))
            for sd in (-1, 1):
                nx_, ny_ = -dy * sd, dx * sd
                vx, vy = nx_ + 0.7 * dx, ny_ + 0.7 * dy
                vl = math.hypot(vx, vy)
                if vl < 1e-6:
                    continue
                vx, vy = vx / vl, vy / vl
                upper = vy < 0 or (abs(vy) < 0.2 and vx < 0)
                for i in range(1, Lf + 1):
                    q = (int(round(x + vx * i)), int(round(y + vy * i)))
                    if q in m:
                        continue
                    t = base_t if upper else max(SH, base_t - 1)
                    if k == 2 and i == Lf and upper:
                        t = min(HI if depth == 2 else LT, t + 1)
                    lay[q] = FERN[t]                                                                       # noqa
                    m.add(q)
    for nm in ('fronds_back', 'fronds', 'fronds_front'):
        lay = S.lay(nm)
        outline(lay, set(lay), FERN, skip={(q, gy + 1) for q in range(cx - 60, cx + 60)})                # noqa
    _small_shadow(S, cx, gy, w=S.kv(6, 12))
    return {'ground': 'grass'}


def bush(S, cx, gy, size='m', berries=False, kind='oak', **_):
    """Bush: a low mound of leaf puffs over a dark back mass (oak leaves), lit top-left; with berries=True
    red berries in clusters (sweet berry bush). Seasons like the trees."""
    k, u = S.k, S.u
    sc = SIZES.get(size, 1.0)
    rnd = S.rnd('bush', cx)
    R, ramps = leaf_ramps(kind, S.season)
    U = lambda a: u(a * sc)                                             # noqa: E731
    cy = gy - U(5)

    def J(a):
        return u(a * sc) + rnd.randint(-1, 1) * (k == 2)
    clumps = [(cx + J(0), cy + J(0), U(9), U(5.5), 0),
              (cx + J(-4), cy + J(-2), U(5), U(3.6), 1), (cx + J(4), cy + J(-2), U(4.5), U(3.4), 1),
              (cx + J(-6), cy + J(2), U(4), U(3), 2), (cx + J(1), cy + J(2), U(5), U(3.2), 2),
              (cx + J(7), cy + J(2), U(3.5), U(2.8), 2)]
    union, vis, masks = crown(S, clumps, R, ramps=ramps, seed=cx, holes=0, bump=S.kv(1.3, 2.1))
    if berries and S.season in ('summer', 'autumn'):
        lay = S.lay('berries', 40)
        scatter_on(S, lay, union, BERRY, 'berry', S.kv(5, 8), seed=cx)                                 # noqa
    if S.season == 'spring':
        scatter_on(S, S.lay('blossoms', 40), union, CREAM, 'blossom', S.kv(3, 5), seed=cx)            # noqa
    if S.season == 'winter':
        snow_cap(S, vis, seed=cx)
    x0, _, x1, _ = bbox(union)
    ground_shadow(S, cx - U(4), x1 + U(3), gy, rows=S.kv(2, 3), steps=2)
    return {'ground': 'grass'}


def rose_bush(S, cx, gy, **_):
    """Rose bush: a tall leafy shrub (dark green puffs) dotted with red roses - each rose a lit ball with a
    darker spiral of petals and a light outer petal rim."""
    k, u = S.k, S.u
    rnd = S.rnd('rose', cx)
    cy = gy - u(9)
    clumps = [(cx, cy, u(8), u(9), 0),
              (cx - u(3), cy - u(5), u(4.5), u(3.5), 1), (cx + u(3), cy - u(4), u(4.5), u(3.5), 1),
              (cx - u(4), cy + u(1), u(4.5), u(3.5), 2), (cx + u(4), cy + u(1), u(4), u(3.5), 2),
              (cx - u(1), cy + u(6), u(5), u(3), 3)]
    R, ramps = leaf_ramps('dark_oak', S.season if S.season != 'autumn' else 'summer')
    union, vis, masks = crown(S, clumps, R, seed=cx, holes=0, bump=S.kv(1.3, 2.0))
    lay = S.lay('roses', 40)
    inner = [p for p in sorted(union) if all((p[0] + a * S.kv(2, 3), p[1] + b * S.kv(2, 3)) in union for a, b in N4)]
    rnd.shuffle(inner)
    placed = []
    for p in inner:
        if len(placed) >= S.kv(5, 7):
            break
        if all(abs(p[0] - q[0]) + abs(p[1] - q[1]) >= S.kv(5, 8) for q in placed):
            placed.append(p)
            r = S.kv(1.4, 2.6)
            pts = disc(p[0] + 0.5, p[1] + 0.5, r)
            for (x, y) in pts:
                lay[(x, y)] = ROSE[sphere_tone((x - p[0]) / r, (y - p[1]) / r)]                       # noqa
            if k == 2:                                                 # the spiral
                for (a, b) in ((0, 0), (1, 0), (1, 1), (0, 1), (-1, 1)):
                    lay[(p[0] + a, p[1] + b)] = ROSE[SH if (a, b) != (0, 0) else DK]                   # noqa
            else:
                lay[(p[0] + 1, p[1] + 1)] = ROSE[SH]                                                    # noqa
    if S.season == 'winter':
        snow_cap(S, vis, seed=cx)
    ground_shadow(S, cx - u(4), cx + u(12), gy, rows=S.kv(2, 3), steps=2)
    return {'ground': 'grass'}


def dead_bush(S, cx, gy, **_):
    """Dead bush: a tangle of dry twigs forking up and out from the sand, lit on top."""
    rnd = S.rnd('deadbush', cx)
    specs = []

    def grow(x, y, ang, L, depth):
        a = math.radians(ang)
        ex, ey = x + L * math.cos(a), y + L * math.sin(a)
        specs.append(((int(x), int(y)), (x + L * 0.5 * math.cos(a), y + L * 0.5 * math.sin(a) - 1), (int(ex), int(ey)),
                      1 if S.k == 1 else 2, 1))
        if depth:
            for d in (-1, 1):
                grow(ex, ey, ang + d * rnd.uniform(25, 40), L * 0.6, depth - 1)
    for ang in (-125, -100, -78, -52):
        grow(cx, gy, ang + rnd.uniform(-8, 8), S.kv(6, 12) * rnd.uniform(0.85, 1.1), 1 if S.k == 1 else 2)
    _limbs(S, specs, DRY_PLANT, name='twigs', z=5)                                                     # noqa
    _small_shadow(S, cx, gy, w=S.kv(6, 12))
    return {'ground': 'sand'}


# ------------------------------------------------------------------ blocks seen front-above (oblique)
def box_faces(x0, gy, w, h, d):
    """Pixel masks of a block in oblique view: the front face (w x h, bottom row on gy), the top face going
    back up-right by d px and the right side face - {'front', 'top', 'side'}. Total size (w + d) x (h + d)."""
    front = rect(x0, gy - h + 1, x0 + w - 1, gy)
    top, side = set(), set()
    for i in range(1, d + 1):
        for x in range(x0 + i, x0 + w + i):
            top.add((x, gy - h + 1 - i))
        for y in range(gy - h + 1 - i, gy - i + 1):
            side.add((x0 + w - 1 + i, y))
    side -= top
    return {'front': front, 'top': top, 'side': side}


def box_shade(lay, faces, Rf, Rt=None, Rs=None, rim=True):
    """Flat faces in three tones (top lit, front base, side dark) with lit front-top / front-left edges and
    a dark lower edge - the volume comes from the faces, not from gradients."""
    Rt, Rs = Rt or Rf, Rs or Rf
    for p in faces['top']:
        lay[p] = Rt[LT]
    for p in faces['front']:
        lay[p] = Rf[BS]
    for p in faces['side']:
        lay[p] = Rs[DK]
    if rim:
        fx0 = min(x for x, _ in faces['front'])
        fy0 = min(y for _, y in faces['front'])
        for (x, y) in faces['front']:
            if y == fy0:
                lay[(x, y)] = Rf[LT]
            elif x == fx0:
                lay[(x, y)] = Rf[LT]
        for (x, y) in faces['top']:
            if (x, y + 1) in faces['front']:
                lay[(x, y)] = Rt[HI]


# ------------------------------------------------------------------ crops
def farm_bed(S, x0, x1, gy, wet=True, name='farmland', z=0):
    """A tilled bed seen from slightly above: ridges along the row (lit tops) and dark furrows between them,
    moist soil a tone darker, a front edge of soil; plants stand on the ridges."""
    k = S.k
    R = FARMLAND_WET if wet else FARMLAND                                                            # noqa
    lay = S.lay(name, z)
    rnd = S.rnd('bed', x0)
    back, front = S.u(3), S.u(3)
    top = {(x, y) for x in range(x0, x1 + 1) for y in range(gy - back, gy + front)
           if not ((x in (x0, x1)) and y in (gy - back, gy + front - 1))}
    rows = S.kv(2, 3)
    for (x, y) in top:
        j = (y - (gy - back)) % rows
        t = LT if j == 0 else DK if j == rows - 1 else BS
        lay[(x, y)] = R[t]
    for (x, y) in sorted(top):                                     # clods: a lit pair over a dark pair
        if rnd.random() < 0.05 and (x + 1, y) in top and (x, y + 1) in top and (x + 1, y + 1) in top:
            lay[(x, y)] = lay[(x + 1, y)] = R[HI if k == 2 else LT]
            if k == 2:
                lay[(x, y + 1)] = lay[(x + 1, y + 1)] = R[DK]
    face = {(x, y) for x in range(x0, x1 + 1) for y in range(gy + front, gy + front + S.kv(2, 4))
            if not (x in (x0, x1) and y == gy + front + S.kv(2, 4) - 1)}
    for (x, y) in face:
        lay[(x, y)] = R[DK if y > gy + front else BS] if x > x0 else R[LT]
    outline(lay, top | face, R, lit=R[DK])
    return top


def _crop_plant(S, lay, x, gy, crop, age, rnd, m, back=False):
    """One crop plant at (x, gy): wheat stalks with grain ears and awns, carrot fronds with an orange
    shoulder, a bushy potato with a pale tuber peeking out, beetroot leaves with red veins over a red root."""
    k = S.k
    dk = 1 if back else 0

    def put(q, R, t):
        lay[q] = R[max(SH, t - dk)]
        m.add(q)
    if crop == 'wheat':
        hh = int(S.kv(4, 8) + age * S.kv(2, 4)) + rnd.randint(0, 1)
        for sx in ((0,) if k == 1 else (0, 3)):
            lean = rnd.choice((-1, 0, 1)) if age >= 2 else 0
            path = bezier((x + sx, gy), (x + sx, gy - hh * 0.6), (x + sx + lean, gy - hh))
            for i, q in enumerate(path):
                ripe = age >= 3
                put(q, WHEAT if ripe and i > len(path) * 0.5 else STALK,                             # noqa
                    DK if i < len(path) * 0.3 else BS)
            if age >= 2:
                ex, ey = path[-1]
                R = WHEAT if age >= 3 else STALK                                                       # noqa
                eh = S.kv(3, 6)
                for j in range(eh):
                    kern = (j // 2) % 2 == 0                        # kernels: 2-row blocks, alternating
                    if k == 1:
                        put((ex, ey + j), R, LT)
                        put((ex + 1, ey + j), R, BS)
                    else:
                        put((ex - 1, ey + j), R, LT if kern else BS)
                        put((ex, ey + j), R, HI if kern else LT)
                        put((ex + 1, ey + j), R, BS if kern else DK)
                put((ex, ey - 1), R, LT)
                if k == 2:
                    put((ex - 1, ey - 2), R, BS)
                    put((ex + 2, ey - 2), R, DK)
    elif crop == 'carrot':
        hh = S.kv(3, 6) + age * S.kv(1, 2)
        for ang in (-0.8, -0.3, 0.2, 0.7):
            path = bezier((x, gy - 1), (x + ang * hh * 0.3, gy - hh * 0.7), (x + int(ang * hh * 0.7), gy - hh))
            for i, q in enumerate(path):
                put(q, CROP_LEAF, LT if ang < 0 else BS)                                                # noqa
                if k == 2 and i > 1:
                    put((q[0] + 1, q[1]), CROP_LEAF, BS if ang < 0 else DK)                             # noqa
        if age >= 2:
            for i in range(S.kv(2, 4)):
                put((x - S.kv(1, 2) + i, gy), CARROT, BS if k == 1 else LT if i == 0 else BS)            # noqa
            if k == 2:
                put((x - 1, gy + 1), CARROT, DK)                                                         # noqa
                put((x, gy + 1), CARROT, DK)                                                             # noqa
    elif crop == 'potato':
        r = S.kv(1.5, 3.2) + age * S.kv(0.25, 0.5)
        cy = gy - r
        pts = disc(x + 0.5, cy, r * 1.1, r * 0.9)
        for q in pts:
            t = sphere_tone((q[0] + 0.5 - x - 0.5) / (r * 1.1), (q[1] + 0.5 - cy) / (r * 0.9),
                            cuts=(0.95, 0.5, 0.0, -0.6) if k == 1 else (0.86, 0.58, 0.2, -0.12))
            put(q, CROP_LEAF, t)                                                                        # noqa
        if k == 2:
            for q in sorted(pts):
                if rnd.random() < 0.12 and q[1] < cy and (q[0] + 1, q[1]) in pts:
                    put(q, CROP_LEAF, HI)                                                               # noqa
                    put((q[0] + 1, q[1]), CROP_LEAF, LT)                                                # noqa
        if age >= 3 and rnd.random() < 0.6:
            q = (x + rnd.randint(-1, 1), int(cy - r * 0.5))
            put(q, LILY_WHITE, HI)                                                                     # noqa
        if age >= 2:
            for i in range(S.kv(2, 3)):
                put((x + S.kv(1, 2) + i, gy), POTATO, BS if k == 1 else LT if i == 0 else BS)            # noqa
    elif crop == 'beet':
        hh = S.kv(4, 8) + age * S.kv(1, 2)
        for side in (-1, 1, 0):
            px_, py_ = x, gy - 1
            for i in range(hh if side == 0 else hh - 1):
                q = (px_ + int(round(side * i * 0.45)), py_ - i)
                put(q, BEET, BS if i < hh // 2 else DK)                                                 # noqa
                for w in range(1, S.kv(2, 3)):
                    if i > hh * 0.35:
                        put((q[0] - w, q[1]), CROP_LEAF, LT if side <= 0 else BS)                      # noqa
                        put((q[0] + w, q[1]), CROP_LEAF, BS if side <= 0 else DK)                      # noqa
        if age >= 2:
            for (a, b), t in (((-1, 0), LT), ((0, 0), BS), ((1, 0), DK), ((0, 1), DK)):
                put((x + a, gy + b), BEET, t)                                                           # noqa


def crop_row(S, cx, gy, crop='wheat', age=3, size='m', **_):
    """A row of crops on a tilled bed (two rows of plants, the back one a step darker): wheat, carrot,
    potato or beet; age 0..3 (sprout -> ripe)."""
    k, u = S.k, S.u
    rnd = S.rnd('crops', crop, cx)
    n = {'s': 6, 'm': 8, 'l': 11}.get(size, 8)
    sp = u(4.5)
    x0 = cx - n * sp // 2
    farm_bed(S, x0 - u(2), x0 + n * sp + u(1), gy, z=0)
    for row, (dy, back) in enumerate(((-u(2), True), (u(1), False))):
        lay = S.lay('plants_back' if back else 'plants', 5 + row)
        m = set()
        for i in range(n):
            _crop_plant(S, lay, x0 + i * sp + (sp // 2 if back else 0) + rnd.randint(0, 1), gy + dy, crop,
                        max(0, min(3, age)), rnd, m, back=back)
        for q in sorted(m) if k == 2 else ():                  # top edges catch the light
            if (q[0], q[1] - 1) not in m and lay[q] not in (BEET[BS], BEET[DK]):                   # noqa
                lay[q] = lighter(lay[q])
        R = {'wheat': STALK if age < 3 else WHEAT, 'carrot': CROP_LEAF, 'potato': CROP_LEAF, 'beet': CROP_LEAF}[crop]  # noqa
        outline(lay, m, R, skip=S.mask_of('farmland'))
    return {'ground': 'grass', 'ground_opts': {'back': u(2), 'front': u(5)}}


def pumpkin(S, cx, gy, carved=False, **_):
    """Pumpkin: a squat round fruit with deep curved ribs (each lobe lit on its left, the grooves a step
    darker), lit top-left, a woody stem in a dimple, a curling vine with a leaf on the ground."""
    k, u = S.k, S.u
    rnd = S.rnd('pumpkin', cx)
    lay = S.lay('pumpkin', 5)
    rx, ry = u(7.5), u(6)
    cy = gy - ry + 0.5
    m = disc(cx + 0.5, cy, rx, ry)
    for (x, y) in m:
        nx, ny = (x + 0.5 - cx - 0.5) / rx, (y + 0.5 - cy) / ry
        t = sphere_tone(nx, ny, cuts=(0.9, 0.55, 0.12, -0.25))
        lobe = (nx + 1) * 2.5                                     # five lobes across
        f = lobe - math.floor(lobe)
        if f < 0.16 and abs(nx) < 0.92:
            t = max(SH, t - 1)                                     # groove
        elif f < 0.34 and t < HI:
            t = min(HI, t + 1)                                     # the lit left side of a lobe
        lay[(x, y)] = PUMPKIN[t]                                                                       # noqa
    top = min(y for _, y in m)
    for x in range(cx - u(1), cx + u(2)):                          # the dimple round the stem
        if (x, top + 1) in m:
            lay[(x, top + 1)] = PUMPKIN[DK]                                                            # noqa
    outline(lay, m, PUMPKIN, skip={(q, gy + 1) for q in range(cx - 40, cx + 40)})                     # noqa
    st = S.lay('stem', 8)
    sm = set()
    for j in range(S.kv(3, 5)):
        for i in range(S.kv(2, 3)):
            q = (cx + i - (j > S.kv(1, 3)), top - j + 1)
            st[q] = PUMPKIN_STEM[LT if i == 0 else BS if i == 1 else DK]                               # noqa
            sm.add(q)
    outline(st, sm, PUMPKIN_STEM, skip=m)                                                              # noqa
    vl = S.lay('vine', 3)
    vm = set()
    path = bezier((cx + rx - u(1), gy), (cx + rx + u(3), gy - u(3)), (cx + rx + u(5), gy))
    for q in path:
        vl[q] = PUMPKIN_STEM[BS]                                                                       # noqa
        vm.add(q)
    vm |= leaf(S, vl, cx - rx + u(1), gy - S.kv(1, 2), -1, CROP_LEAF, size=0.8, up=0.5)                # noqa
    outline(vl, vm, CROP_LEAF, skip=m)                                                                 # noqa
    if carved:
        face = S.lay('face', 9)
        for (fx, fy, w, h) in ((-4, -6, 2, 2), (2, -6, 2, 2), (-4, -2, 7, 1), (-3, -1, 5, 1)):
            for i in range(u(w)):
                for j in range(u(h)):
                    face[(cx + u(fx) + i, gy + u(fy) + j)] = GLOW[HI if j == 0 else LT]                # noqa
    if S.season == 'winter':
        snow_cap(S, [m], seed=cx)
    ground_shadow(S, cx - rx + u(2), cx + rx + u(4), gy, rows=S.kv(2, 3), steps=2)
    return {'ground': 'grass'}


def melon(S, cx, gy, **_):
    """Melon: a block-shaped melon seen front-above - light green rind with dark wavy stripes running down
    the front and radiating on the top, the top lit, the side in shade, a short stalk."""
    k, u = S.k, S.u
    rnd = S.rnd('melon', cx)
    w, h, d = u(12), u(11), u(4)
    x0 = cx - (w + d) // 2
    lay = S.lay('melon', 5)
    f = box_faces(x0, gy, w, h, d)
    box_shade(lay, f, MELON)                                                                            # noqa
    for (x, y) in f['front'] | f['side']:                           # wavy stripes
        rel = (x - x0) if (x, y) in f['front'] else (w + (x - x0 - w) * 0.8)
        wav = math.sin((y - gy) * (0.9 / k) + rel * 0.3) * 0.8
        if x == x0 or y == gy - h + 1:
            continue
        if int(rel + wav) % S.kv(4, 6) in (0,) or (k == 2 and int(rel + wav) % 6 == 1):
            c = lay[(x, y)]
            lay[(x, y)] = MELON_STRIPE[DK if (x, y) in f['front'] else SH]                              # noqa
            if (x, y) in f['front'] and x > x0 and rnd.random() < 0.3:
                lay[(x, y)] = MELON_STRIPE[BS]                                                          # noqa
    tx, ty = x0 + w // 2 + d // 2, gy - h - d // 2 + 1
    for (x, y) in f['top']:
        a = math.atan2(y - ty, (x - tx) * 0.5)
        if int(a * S.kv(2.0, 3.0) + 10) % 2 == 0 and (x, y + 1) not in f['front']:
            lay[(x, y)] = MELON_STRIPE[BS]                                                              # noqa
    solid = set().union(*f.values())
    st = S.lay('stalk', 8)
    for j in range(S.kv(2, 3)):
        st[(tx, ty - j)] = PUMPKIN_STEM[BS if j else DK]                                               # noqa
        st[(tx + 1, ty - j)] = PUMPKIN_STEM[DK]                                                        # noqa
    outline(lay, solid, MELON_STRIPE, skip={(q, gy + 1) for q in range(cx - 40, cx + 40)})             # noqa
    ground_shadow(S, x0 + u(2), x0 + w + d + u(4), gy, rows=S.kv(2, 3), steps=2)
    return {'ground': 'grass'}


# ------------------------------------------------------------------ desert and water plants
def cactus(S, cx, gy, size='m', arms=True, flower=None, **_):
    """Cactus: a column of stacked blocks with vertical ribs (each rib lit on its left, the grooves dark, the
    whole column shaded like a cylinder), spine pairs (a pale tip over a dark root) on the ribs, a flat lit top;
    a blocky arm; a pink flower on top in spring."""
    k, u = S.k, S.u
    sc = SIZES.get(size, 1.0)
    rnd = S.rnd('cactus', cx)
    w = u(9)
    H = u(32 * sc)
    lay = S.lay('cactus', 5, cast=(S.kv(1, 2), 0, 1))
    x0 = cx - w // 2
    m = rect(x0, gy - H + 1, x0 + w - 1, gy)
    am = set()
    if arms:
        ay = gy - u(14 * sc)
        aw = u(5)
        am |= rect(x0 - u(5), ay - aw + 1, x0 - 1, ay)              # the elbow going left
        am |= rect(x0 - u(5), ay - u(10), x0 - u(5) + aw - 1, ay)   # and up
        am -= m
    allm = m | am
    rib = S.kv(3, 4)
    for (x, y) in allm:
        if (x, y) in m:
            nx = ((x - x0) + 0.5) / w * 2 - 1
            xr = x - x0
        else:
            ax0 = x0 - u(5)
            nx = ((x - ax0) + 0.5) / aw * 2 - 1 if y < gy - u(14 * sc) - aw + 1 else ((x - ax0) + 0.5) / u(5) * 2 - 1
            xr = x - ax0
        t = cyl_tone(nx, cuts=(1.12, 0.92, 0.42, -0.02))
        f = xr % rib
        if f == rib - 1:
            t = max(SH, t - 1)                                         # groove
        elif f == 0 and t < HI:
            t = min(LT if t < LT else HI, t + 1)                      # lit rib edge
        lay[(x, y)] = CACTUS[t]                                                                       # noqa
    for part in (m, am):                                                # block seams and the lit tops
        if not part:
            continue
        x0_, y0_, x1_, y1_ = bbox(part)
        for x in range(x0_, x1_ + 1):
            if (x, y0_) in part:
                lay[(x, y0_)] = CACTUS[HI if x < (x0_ + x1_) / 2 else LT]                            # noqa
                if (x, y0_ + 1) in part:
                    lay[(x, y0_ + 1)] = CACTUS[LT if x < (x0_ + x1_) / 2 else BS]                    # noqa
        if part is m:
            for yy in range(gy - u(16 * sc), y0_, -u(16 * sc)):
                for x in range(x0_, x1_ + 1):
                    lay[(x, yy)] = darker(lay[(x, yy)])
    for (x, y) in sorted(allm):                                         # spine pairs on the ribs
        xr = (x - x0) if (x, y) in m else (x - (x0 - u(5)))
        if xr % rib == 1 and (y * 7 + x * 3) % S.kv(7, 6) == 0 and (x, y + 1) in allm and (x, y - 2) in allm:
            lay[(x, y)] = CREAM[HI if x < cx else LT]                                                   # noqa
            lay[(x, y + 1)] = CACTUS[SH]                                                                # noqa
            if k == 2:
                lay[(x - 1, y - 1)] = CREAM[LT]                                                         # noqa
    outline(lay, allm, CACTUS, skip={(q, gy + 1) for q in range(cx - 60, cx + 60)})                 # noqa
    if flower or (flower is None and S.season == 'spring'):
        fl = S.lay('flower', 20)
        fm = bloom(S, fl, cx + 0.5, gy - H - S.kv(0.5, 1), CACTUS_FLOWER, 5, S.kv(1.2, 2.2), S.kv(1.2, 2.2),   # noqa
                   squash=0.7, eye=DANDELION, er=S.kv(0.6, 1.1), eye_tone=LT)                            # noqa
        outline(fl, fm, CACTUS_FLOWER, skip=allm)                                                      # noqa
    if S.season == 'winter':
        snow_cap(S, [allm], seed=cx)
    ground_shadow(S, x0, x0 + w + u(8), gy, contact=(x0 - 1, x0 + w), steps=2)
    return {'ground': 'sand'}


def _segmented(S, lay, x, gy, h, w, R, node, m, leafy=None, seed=0):
    """A segmented stalk (sugar cane, bamboo) from (x, gy) up h px, w px wide: shaded like a cylinder,
    a node every `node` px (a dark ring under a lit swelling)."""
    for y in range(gy - h + 1, gy + 1):
        j = (gy - y) % node
        for i in range(w):
            t = LT if i < max(1, w // 3) else BS if i < w - max(1, w // 3) else DK
            if j == 0:
                t = max(SH, t - 2)                                       # the node ring
            elif j == 1:
                t = min(HI, t + 1)                                       # the swelling above it
            lay[(x + i, y)] = R[t]
            m.add((x + i, y))


def sugar_cane(S, cx, gy, size='m', **_):
    """Sugar cane: three pale-green segmented canes of different heights (lit left, dark right, nodes with
    a lit swelling), long thin leaves arching out from some nodes."""
    k, u = S.k, S.u
    sc = SIZES.get(size, 1.0)
    rnd = S.rnd('cane', cx)
    lay = S.lay('canes', 5)
    lv = S.lay('leaves', 6)
    m, lm = set(), set()
    for (dx, hh) in ((-u(4), 30), (0, 38), (u(4), 24)):
        h = u(hh * sc)
        w = S.kv(2, 4)
        node = S.kv(5, 9)
        _segmented(S, lay, cx + dx, gy, h, w, CANE, node, m)                                          # noqa
        for y in range(gy - node, gy - h + node, -node * 2):
            side = rnd.choice((-1, 1))
            path = bezier((cx + dx + (w if side > 0 else -1), y), (cx + dx + side * u(4), y - u(4)),
                          (cx + dx + side * u(7), y + u(1)))
            for i, q in enumerate(path):
                lv[q] = CANE[LT if side < 0 else BS] if i < len(path) * 0.6 else CANE[DK]              # noqa
                lm.add(q)
                if k == 2 and i < len(path) * 0.5:
                    lv[(q[0], q[1] + 1)] = CANE[DK]                                                    # noqa
                    lm.add((q[0], q[1] + 1))
    outline(lay, m, CANE, skip={(q, gy + 1) for q in range(cx - 60, cx + 60)})                        # noqa
    outline(lv, lm, CANE, skip=m)                                                                      # noqa
    _small_shadow(S, cx - u(4), gy, w=u(14))
    return {'ground': 'grass'}


def bamboo(S, cx, gy, size='m', **_):
    """Bamboo: tall jointed stalks (a dark ring and a lit ridge at every node), narrow pointed leaves in
    drooping fans at the top and on short twigs at a few nodes."""
    k, u = S.k, S.u
    sc = SIZES.get(size, 1.0)
    rnd = S.rnd('bamboo', cx)
    lay = S.lay('stalks', 5)
    lv = S.lay('leaves', 7)
    m, lm = set(), set()

    def leaf_fan(x, y, n, side0):
        for i in range(n):
            ang = math.radians(rnd.uniform(15, 55)) * (1 if (i % 2) else -1)
            side = side0 if i % 2 == 0 else -side0
            L = S.kv(5, 10) * rnd.uniform(0.8, 1.1)
            ex, ey = x + side * L * math.cos(abs(ang)), y + L * math.sin(abs(ang)) * 0.6
            path = bezier((x, y), ((x + ex) / 2, y - S.kv(1, 2)), (ex, ey))
            for j, q in enumerate(path):
                lv[q] = BAMBOO[LT if side < 0 else BS] if j < len(path) - 1 else BAMBOO[DK]             # noqa
                lm.add(q)
                if k == 2 and 1 < j < len(path) - 2:
                    lv[(q[0], q[1] + 1)] = BAMBOO[DK if side > 0 else BS]                             # noqa
                    lm.add((q[0], q[1] + 1))
    for (dx, hh) in ((-u(3), 40), (u(2), 48)):
        h = u(hh * sc)
        w = S.kv(3, 5)
        node = S.kv(7, 12)
        _segmented(S, lay, cx + dx, gy, h, w, BAMBOO, node, m)                                         # noqa
        top = gy - h + 1
        leaf_fan(cx + dx + w // 2, top + 1, S.kv(4, 6), -1)
        for y in range(gy - node * 3, top + node, -node * 2):
            if rnd.random() < 0.6:
                side = rnd.choice((-1, 1))
                leaf_fan(cx + dx + (w if side > 0 else -1), y, S.kv(2, 3), side)
    outline(lay, m, BAMBOO, skip={(q, gy + 1) for q in range(cx - 60, cx + 60)})                      # noqa
    outline(lv, lm, BAMBOO, skip=m)                                                                    # noqa
    _small_shadow(S, cx - u(3), gy, w=u(10))
    return {'ground': 'podzol'}


def vines_item(S, cx, gy, size='m', **_):
    """Vines: a curtain of strands hanging from a top edge (for walls, caves, branches): swaying stems,
    leaves alternating sides, lit on the left; no ground."""
    u = S.u
    rnd = S.rnd('vineitem', cx)
    sc = SIZES.get(size, 1.0)
    lay = S.lay('vines', 5)
    starts = [(cx + u(i * 3), gy - u(32 * sc), int(u(rnd.uniform(14, 32) * sc))) for i in range(-3, 4)]
    vines(S, lay, starts, VINE, seed=cx, leafy=1.0)                                                   # noqa
    return {'ground': None}


def water_patch(S, cx, gy, rx, ry, R=None, name='water', z=0, ripples=2, seed=0, shore=None):
    """A flat water surface seen from slightly above (an ellipse): the far edge darker (shore shadow), a
    wide base, a band of sky reflection, broken ripple arcs (light) round a centre, short light glints on
    the left, a lit lip on the near edge; shore = (ramp) a 1-2 px bank round it. Returns the mask."""
    R = R or WATER                                                                                     # noqa
    k = S.k
    rnd = S.rnd('water', cx, seed)
    lay = S.lay(name, z)
    cy = gy - ry
    m = disc(cx + 0.5, cy + 0.5, rx, ry)
    for (x, y) in m:
        ny = (y + 0.5 - cy) / ry
        t = LT if ny < -0.45 else BS if ny < 0.5 else DK          # sky reflected at the far edge
        lay[(x, y)] = R[t]
    for i in range(ripples):                                   # ripple arcs round a point left of centre
        px_, py_ = cx - rx * 0.25 + rnd.uniform(-rx * 0.15, rx * 0.15), cy + ry * 0.05
        for rr in ((S.kv(3.0, 4.4) * (i + 1),) if k == 1 else (S.kv(2.2, 4.4) * (i + 1), S.kv(3.6, 7.2) * (i + 1))):
            for a10 in range(0, 360, 3):
                a = math.radians(a10)
                if 200 < a10 < 340 or rnd.random() < 0.3:
                    continue
                q = (int(round(px_ + math.cos(a) * rr)), int(round(py_ + math.sin(a) * rr * 0.4)))
                if q in m and all((q[0] + dx, q[1] + dy) in m for dx, dy in N4):
                    lay[q] = R[HI if a10 > 120 and a10 < 200 else LT]
    for _ in range(S.kv(3, 6)):                                # glints on the lit side
        x = int(cx - rx * rnd.uniform(0.2, 0.75))
        y = int(cy + ry * rnd.uniform(-0.3, 0.3))
        L = rnd.randint(2, S.kv(3, 5))
        if all((x + i, y) in m for i in range(L)):
            for i in range(L):
                lay[(x + i, y)] = R[HI]
    if shore:
        ring = edge_ring(m)
        ring2 = edge_ring(m | ring)
        for (x, y) in ring | (ring2 if k == 2 else set()):
            above = y < cy
            lay[(x, y)] = shore[DK if above else LT if x < cx else BS]
        for (x, y) in ring:
            if y < cy and (x, y + 1) in m:
                lay[(x, y + 1)] = R[SH]                          # the bank's shadow on the far water
        m = m | ring | (ring2 if k == 2 else set())
    return m


def lily_pad(S, cx, gy, flower=True, **_):
    """Lily pad on a patch of water: a flat round leaf with a V notch, veins radiating from the centre, lit
    on its left, a dark rim where it lies on the water; a pink lotus bud on it."""
    k, u = S.k, S.u
    water_patch(S, cx, gy, u(11), u(4), ripples=1, seed=cx, shore=None, z=0)
    lay = S.lay('pad', 5)
    rx, ry = u(6.5), u(2.6)
    pcx, pcy = cx - u(1) + 0.5, gy - u(4) + 0.5
    m = {(x, y) for (x, y) in disc(pcx, pcy, rx, ry)}
    notch = {(x, y) for (x, y) in m if x > pcx and abs(y + 0.5 - pcy) < (x + 0.5 - pcx) * 0.35 + 0.3}
    m -= notch
    for (x, y) in m:
        t = LT if x < pcx - rx * 0.3 else BS if x < pcx + rx * 0.4 else DK
        if (x, y + 1) not in m:
            t = max(SH, t - 1)
        lay[(x, y)] = LILY_PAD[t]                                                                   # noqa
    if k == 2:
        for a in range(0, 360, 45):
            ar = math.radians(a)
            for r in range(2, int(rx) - 1):
                q = (int(round(pcx + math.cos(ar) * r)), int(round(pcy + math.sin(ar) * r * ry / rx)))
                if q in m and (q[0], q[1] + 1) in m and (q[0], q[1] - 1) in m:
                    lay[q] = LILY_PAD[DK if q[0] > pcx else BS]                                     # noqa
    outline(lay, m, LILY_PAD)                                                                       # noqa
    if flower:
        fl = S.lay('lotus', 8)
        fm = bloom(S, fl, pcx - u(2), pcy - S.kv(1, 2), LOTUS, 5, S.kv(1.1, 2.0), S.kv(1.0, 2.0), squash=0.7,   # noqa
                   eye=DANDELION, er=S.kv(0.6, 1.0), eye_tone=LT, rot=-1.57)                       # noqa
        outline(fl, fm, LOTUS, skip=m)                                                              # noqa
    return {'ground': None}


def pond(S, cx, gy, size='m', **_):
    """Pond: a water patch with a sandy-grassy bank, ripples and glints, reeds and a cattail on the left
    bank, a lily pad floating near the front."""
    k, u = S.k, S.u
    sc = SIZES.get(size, 1.0)
    rnd = S.rnd('pond', cx)
    rx, ry = u(20 * sc), u(5.5 * sc)
    wm = water_patch(S, cx, gy, rx, ry, ripples=S.kv(1, 2), seed=cx, shore=SAND, z=0)                 # noqa
    pad = S.lay('lily_pad', 5)
    pm = set()
    px_, py_ = cx + rx * 0.35, gy - ry * 0.55
    for (x, y) in disc(px_, py_, S.kv(2.6, 5.0), S.kv(1.2, 2.2)):
        if not (x > px_ and abs(y + 0.5 - py_) < (x + 0.5 - px_) * 0.4):
            pad[(x, y)] = LILY_PAD[LT if x < px_ - 1 else BS if x < px_ + 1 else DK]                   # noqa
            pm.add((x, y))
    outline(pad, pm, LILY_PAD)                                                                       # noqa
    reeds = S.lay('reeds', 8)
    rm = set()
    for i in range(S.kv(5, 7)):
        x = int(cx - rx + u(1) + i * S.kv(2, 3))
        yb = int(gy - ry - ry * 0.6 + abs(i - 3) * S.kv(0, 1))
        h = u(rnd.uniform(7, 13))
        lean = rnd.choice((-1, 0, 1)) * S.kv(1, 2)
        path = bezier((x, yb), (x, yb - h * 0.6), (x + lean, yb - h))
        for j, q in enumerate(path):
            reeds[q] = REED[LT if i % 2 else BS]                                                      # noqa
            rm.add(q)
            if k == 2 and j < len(path) * 0.7:
                reeds[(q[0] + 1, q[1])] = REED[DK]                                                    # noqa
                rm.add((q[0] + 1, q[1]))
        if i in (1, 4):                                               # cattails: a brown club on a reed
            tx, ty = path[int(len(path) * 0.8)]
            for j in range(S.kv(3, 6)):
                for w in range(S.kv(2, 3)):
                    reeds[(tx + w - S.kv(0, 1), ty + j)] = CATTAIL[LT if w == 0 else BS if j < S.kv(2, 4) else DK]  # noqa
                    rm.add((tx + w - S.kv(0, 1), ty + j))
    outline(reeds, rm, REED, skip=wm)                                                                 # noqa
    if S.season == 'winter':                                        # frozen: ice sheet over the water
        ice = S.lay('ice', 3)
        for q in wm:
            c = S.lay('water').get(q)
            if c in WATER:                                                                          # noqa
                t = tone_of(c)
                ice[q] = ICE[min(HI, t + 1)]                                                         # noqa
    return {'ground': 'grass', 'ground_opts': {'back': ry * 2 + u(1), 'front': u(3)}}


def kelp(S, cx, gy, size='m', **_):
    """Kelp: wavy olive strands rising from the seabed - blade leaves alternating sides along a 2 px stem
    (lit on the left), round air bladders at the leaf joints."""
    k, u = S.k, S.u
    sc = SIZES.get(size, 1.0)
    rnd = S.rnd('kelp', cx)
    for si, (dx, hh) in enumerate(((-u(4), 30), (u(1), 38), (u(5), 22))):
        lay = S.lay(f'strand_{si + 1}', 5 + si)
        m = set()
        h = u(hh * sc)
        ph = rnd.uniform(0, 6)
        for j in range(h):
            x = cx + dx + int(round(math.sin(j * 0.18 / k + ph) * S.kv(1.5, 3)))
            y = gy - j
            for i in range(S.kv(1, 2)):
                lay[(x + i, y)] = KELP[BS if i == 0 else DK]                                         # noqa
                m.add((x + i, y))
            if j % S.kv(4, 7) == 2 and j < h - 2:
                side = 1 if (j // S.kv(4, 7)) % 2 else -1
                L = S.kv(3, 6)
                for i in range(1, L + 1):
                    q = (x + (S.kv(1, 2) if side > 0 else 0) + side * (i - 1), y - i // 2)
                    lay[q] = KELP[LT if side < 0 else BS]                                            # noqa
                    m.add(q)
                    if k == 2 and i < L:
                        lay[(q[0], q[1] + 1)] = KELP[DK]                                             # noqa
                        m.add((q[0], q[1] + 1))
                b = (x + (S.kv(1, 2) if side > 0 else -1), y + 1)
                lay[b] = KELP_BULB[LT]                                                               # noqa
                m.add(b)
                if k == 2:
                    lay[(b[0], b[1] + 1)] = KELP_BULB[DK]                                            # noqa
                    m.add((b[0], b[1] + 1))
        outline(lay, m, KELP, skip={(q, gy + 1) for q in range(cx - 60, cx + 60)})                  # noqa
    return {'ground': 'seabed'}


def coral(S, cx, gy, **_):
    """Coral reef cluster: blue tube coral (open-topped tubes, a dark mouth and a lit rim), a pink brain
    coral dome with maze grooves, a red fan with lattice veins, yellow horn coral antlers, purple bubble
    coral - each in its own saturated ramp, lit top-left."""
    k, u = S.k, S.u
    rnd = S.rnd('coral', cx)
    fan = S.lay('fan_coral', 3)                                       # back: a fan (radial ribs + arcs)
    fm = set()
    fx, fy = cx - u(7), gy
    R_ = u(10)
    for (x, y) in disc(fx + 0.5, fy + 0.5, R_, R_ * 0.95):
        if y > fy:
            continue
        dx, dy = x + 0.5 - fx, fy - y + 0.5
        r = math.hypot(dx, dy)
        a = math.degrees(math.atan2(dy, dx))
        if a < 25 or a > 155:
            continue
        rib = abs(((a - 25) % S.kv(18, 13)) - S.kv(9, 6.5)) > S.kv(7.5, 5.2)
        arc = int(r) % S.kv(3, 4) == 0 and r > u(3)
        if rib or arc or r < u(2.5):
            fm.add((x, y))
    for (x, y) in fm:
        lit = x < fx - u(1) and y < fy - u(4)
        fan[(x, y)] = CORAL_FIRE[LT if lit else BS if x < fx + u(3) else DK]                       # noqa
    outline(fan, fm, CORAL_FIRE, skip={(q, gy + 1) for q in range(cx - 60, cx + 60)})               # noqa
    br = S.lay('brain_coral', 6)                                       # middle: a brain coral dome
    bx, by, rr = cx + u(8), gy, u(6)
    bm = {(x, y) for (x, y) in disc(bx + 0.5, by + 0.5, rr, rr * 0.8) if y <= by}
    for (x, y) in bm:
        t = sphere_tone((x + 0.5 - bx) / rr, (y + 0.5 - by + rr * 0.3) / (rr * 0.8))
        g = (x + 0.5 - bx) * 0.9 + math.sin((y + 0.5) * 1.1 / k + (x - bx) * 0.35 / k) * 2.2 * k
        if int(math.floor(g)) % S.kv(3, 4) == 0 and (x, y - 1) in bm:
            t = max(SH, t - 1)                                         # maze grooves
        br[(x, y)] = CORAL_BRAIN[t]                                                                   # noqa
    outline(br, bm, CORAL_BRAIN, skip={(q, gy + 1) for q in range(cx - 60, cx + 60)})               # noqa
    tb = S.lay('tube_coral', 8)                                        # front: tubes
    tm = set()
    for (dx, h) in ((-3, 9), (0, 12), (3, 6)):
        x0 = cx + u(dx) - u(1)
        w = S.kv(2, 4)
        for y in range(gy - u(h), gy + 1):
            for i in range(w):
                tb[(x0 + i, y)] = CORAL_TUBE[LT if i == 0 else BS if i < w - 1 else DK]               # noqa
                tm.add((x0 + i, y))
        for i in range(-1, w + 1):                                      # the lip with a dark mouth
            tb[(x0 + i, gy - u(h) - 1)] = CORAL_TUBE[HI if i < w // 2 else LT]                        # noqa
            tm.add((x0 + i, gy - u(h) - 1))
        for i in range(w - (1 if k == 1 else 2)):
            tb[(x0 + i + (0 if k == 1 else 1), gy - u(h))] = CORAL_TUBE[O]                            # noqa
    outline(tb, tm, CORAL_TUBE, skip={(q, gy + 1) for q in range(cx - 60, cx + 60)})               # noqa
    hn = S.lay('horn_coral', 9)                                        # horn coral antlers
    hm = set()
    hx = cx + u(15)
    specs = [((hx, gy), (hx, gy - u(4)), (hx - u(2), gy - u(8)), S.kv(2, 3), 1),
             ((hx, gy - u(3)), (hx + u(2), gy - u(5)), (hx + u(3), gy - u(9)), S.kv(2, 3), 1),
             ((hx - u(1), gy - u(6)), (hx - u(3), gy - u(6)), (hx - u(4), gy - u(9)), 1, 1)]
    for (p0, p1, p2, w0, w1) in specs:
        limb(S, hn, bezier(p0, p1, p2), w0, w1, CORAL_HORN, hm, shade=False)                          # noqa
    shade_wood(S, hn, hm, CORAL_HORN, grain=False)                                                   # noqa
    outline(hn, hm, CORAL_HORN, skip={(q, gy + 1) for q in range(cx - 60, cx + 60)})               # noqa
    bb = S.lay('bubble_coral', 10)                                     # bubbles at the foot
    bbm = set()
    for (dx, dy, r) in ((-12, 0, 1.6), (-10, -2, 1.3), (-4, 0, 1.4), (9, 0, 1.3)):
        rr = u(r)
        for (x, y) in disc(cx + u(dx) + 0.5, gy + u(dy) - rr + 1, rr):
            bb[(x, y)] = CORAL_BUBBLE[sphere_tone((x - cx - u(dx)) / rr, (y - gy - u(dy) + rr - 1) / rr)]  # noqa
            bbm.add((x, y))
    outline(bb, bbm, CORAL_BUBBLE)                                                                   # noqa
    return {'ground': 'seabed'}


# ------------------------------------------------------------------ rocks
def poly_fill(poly):
    """Pixels whose centres lie inside a polygon."""
    m = set()
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    for y in range(int(math.floor(min(ys))) - 1, int(max(ys)) + 2):
        for x in range(int(math.floor(min(xs))) - 1, int(max(xs)) + 2):
            c = False
            for (ax, ay), (bx, by) in zip(poly, poly[1:] + poly[:1]):
                if (ay > y + 0.5) != (by > y + 0.5) and x + 0.5 < (bx - ax) * (y + 0.5 - ay) / (by - ay) + ax:
                    c = not c
            if c:
                m.add((x, y))
    return m


def boulder(S, lay, cx, gy, rx, H, R, rnd, front=0.3):
    """A chunky low-poly boulder: a jittered polygon on the ground line, cut into flat facets fanned from a
    peak left of centre plus a front face low down; each facet one tone by the way it faces (up-left
    lightest, right darkest), a lit ridge on the lighter side of every facet edge, a dark crack or two, chips.
    Returns the mask."""
    j = lambda v: v * rnd.uniform(0.9, 1.1)                                 # noqa: E731
    verts = [(cx - rx, gy + 0.5), (cx - j(rx * 0.97), gy - j(H * 0.42)), (cx - j(rx * 0.62), gy - j(H * 0.86)),
             (cx - j(rx * 0.12), gy - H), (cx + j(rx * 0.42), gy - j(H * 0.88)), (cx + j(rx * 0.86), gy - j(H * 0.5)),
             (cx + rx, gy + 0.5)]
    m = poly_fill(verts)
    peak = (cx - rx * 0.12 + rnd.uniform(-1, 1) * S.k, gy - H * 0.62)
    angs = [math.atan2(v[1] - peak[1], v[0] - peak[0]) for v in verts]
    fy = gy - H * front
    face = {}
    tones = {}
    for (x, y) in m:
        if y + 0.5 > fy + (x - cx) * 0.12:
            face[(x, y)] = 'front'
            continue
        a = math.atan2(y + 0.5 - peak[1], x + 0.5 - peak[0])
        best = 0
        for i in range(len(verts) - 1):
            a0, a1 = angs[i], angs[i + 1]
            if a0 > a1:
                a1 += 2 * math.pi
            aa = a if a >= a0 else a + 2 * math.pi
            if a0 <= aa <= a1:
                best = i
                break
        face[(x, y)] = best
    for i in range(len(verts) - 1):
        mx, my = (verts[i][0] + verts[i + 1][0]) / 2, (verts[i][1] + verts[i + 1][1]) / 2
        dx, dy = mx - peak[0], my - peak[1]
        ln = math.hypot(dx, dy) or 1
        lam = -0.62 * dx / ln - 0.78 * dy / ln + 0.15
        tones[i] = HI if lam > 0.85 else LT if lam > 0.45 else BS if lam > 0.0 else DK if lam > -0.45 else SH
    tones['front'] = BS
    for p in m:
        t = tones[face[p]]
        if face[p] == 'front' and p[0] > cx + rx * 0.35:
            t = DK
        lay[p] = R[t]
    for (x, y) in m:                                                 # ridges on the lighter side of edges
        for (dx, dy) in ((1, 0), (0, 1), (-1, 0), (0, -1)):
            q = (x + dx, y + dy)
            if q in m and face[q] != face[(x, y)]:
                tp, tq = tones[face[(x, y)]], tones[face[q]]
                if tp > tq and tp < HI:
                    lay[(x, y)] = R[tp + 1]
    for _ in range(S.kv(1, 2)):                                      # cracks on the front
        x = int(cx + rnd.uniform(-rx * 0.5, rx * 0.3))
        y = int(fy + 1)
        for i in range(S.kv(3, 6)):
            if (x, y) in m and (x, y + 1) in m:
                lay[(x, y)] = R[SH]
                if S.k == 2 and (x - 1, y) in m:
                    lay[(x - 1, y)] = R[min(HI, tone_of(lay[(x - 1, y)]) + 1)] if (x - 1, y) not in face or face[(x - 1, y)] == 'front' else lay[(x - 1, y)]
            x += rnd.choice((-1, 0, 1))
            y += 1
    for p in sorted(m):                                              # chips
        if rnd.random() < S.kv(0.03, 0.025) and (p[0] + 1, p[1]) in m and (p[0], p[1] + 1) in m:
            t = tone_of(lay[p])
            lay[p] = R[max(SH, t - 1)]
            if S.k == 2:
                lay[(p[0] + 1, p[1])] = R[max(SH, t - 1)]
    return m


def moss_on(S, lay, m, rnd, amount=1.0, R=None):
    """Moss on the upper surfaces of a mask: a cushion following the top - thick on the flat crown, thin on
    the slopes - lit top row, base body, a darker lower edge with short drips down the sides."""
    R = R or MOSS                                                                                      # noqa
    c = cols(m)
    xs = sorted(c)
    out = set()
    for x in xs:
        yt = c[x][0]
        slope = max(abs(c.get(x - 1, c[x])[0] - yt), abs(c.get(x + 1, c[x])[0] - yt))
        d = S.kv(2, 4) * amount - slope * 0.8 + rnd.random() * S.kv(1, 2)
        d = int(round(max(1, d)))
        if rnd.random() < 0.12:
            d += S.kv(2, 5)                                               # a drip
        for j in range(d):
            if (x, yt + j) in m:
                lay[(x, yt + j)] = R[LT if j == 0 else DK if j == d - 1 else BS]
                out.add((x, yt + j))
    for (x, y) in sorted(out):                                            # tufts on the lit side
        if (x, y - 1) not in out and (x, y - 1) not in m and rnd.random() < 0.15 and x < sum(xs) / len(xs):
            lay[(x, y)] = R[HI]
    return out


def rock(S, cx, gy, size='m', mossy=False, ore=None, base='stone', **_):
    """Rock / boulder: a blocky faceted silhouette, each facet one flat tone by its tilt (lit top-left, dark
    bottom-right), lit ridges, cracks and chips; mossy=True adds a moss cap with drips and grass tufts; ore=
    'coal' | 'iron' | 'gold' | 'diamond' | 'emerald' | 'redstone' | 'lapis' | 'copper' adds ore clusters
    (lit gem nuggets with a dark rim and glints); base='deepslate' for a dark rock."""
    k, u = S.k, S.u
    sc = SIZES.get(size, 1.0)
    rnd = S.rnd('rock', cx, ore, mossy)
    R = STONE if base == 'stone' else DEEPSLATE                                                       # noqa
    rx, ry = u(9 * sc), u(12 * sc)
    lay = S.lay('rock', 5)
    m = boulder(S, lay, cx, gy, rx, ry, R, rnd)
    small = S.lay('pebble', 6)                                           # a smaller stone leaning on it
    sm = boulder(S, small, cx + rx - u(1), gy, u(4 * sc), u(5 * sc), R, rnd)
    outline(small, sm, R, skip={(q, gy + 1) for q in range(cx - 80, cx + 80)})
    outline(lay, m, R, skip={(q, gy + 1) for q in range(cx - 80, cx + 80)} | sm)
    m = m | sm
    rx += u(3)
    if ore:
        oR = {'coal': COAL, 'iron': IRON_ORE, 'gold': GOLD, 'diamond': DIAMOND, 'emerald': EMERALD,      # noqa
              'redstone': REDSTONE, 'lapis': LAPIS, 'copper': COPPER}[ore]                              # noqa
        ol = S.lay('ore', 8)
        inner = [p for p in sorted(m) if all((p[0] + a * S.kv(2, 3), p[1] + b * S.kv(2, 3)) in m for a, b in N4)]
        rnd.shuffle(inner)
        placed = []
        for p in inner:
            if len(placed) >= S.kv(4, 6):
                break
            if any(abs(p[0] - q[0]) + abs(p[1] - q[1]) < S.kv(4, 7) for q in placed):
                continue
            placed.append(p)
            b = blob(rnd, S.kv(rnd.randint(3, 5), rnd.randint(6, 11)), wide=1.2)
            pts = {(p[0] + a, p[1] + c) for a, c in b} & m
            for (x, y) in pts:
                tl = (x - 1, y) not in pts or (x, y - 1) not in pts
                br = (x + 1, y) not in pts or (x, y + 1) not in pts
                t = HI if tl and not br else DK if br and not tl else BS
                ol[(x, y)] = oR[t]
            for (x, y) in edge_ring(pts) & m:                           # the nugget's dark socket
                if (x - 1, y) in pts or (x, y - 1) in pts:
                    ol[(x, y)] = R[SH]
            if ore == 'copper' and k == 2:
                for (x, y) in list(pts)[:2]:
                    ol[(x, y)] = COPPER_GREEN[BS]                                                     # noqa
    if mossy:
        ml = S.lay('moss', 9)
        mm = moss_on(S, ml, m, rnd, amount=1.6)
        outline(ml, mm, MOSS, skip=m)                                                                 # noqa
        gl = S.lay('grass_tufts', 10)
        for x in (cx - rx + u(1), cx + rx - u(2)):
            for i in range(S.kv(3, 4)):
                for j in range(rnd.randint(2, S.kv(3, 6))):
                    gl[(int(x) + i - 1, gy - j)] = BLADE[LT if i == 0 else BS]                       # noqa
    if S.season == 'winter':
        snow_cap(S, [m], seed=cx)
    ground_shadow(S, cx - rx + u(3), cx + rx + u(4), gy, rows=S.kv(2, 3), contact=(cx - rx + u(1), cx + rx - 1), steps=2)
    return {'ground': 'grass' if mossy else 'gravel' if ore else 'grass'}


def log(S, cx, gy, size='m', mossy=True, R=None, kind='oak', **_):
    """Fallen log: a lying trunk shaded like a horizontal cylinder (lit top, dark underside), bark furrows
    running along it, the near end sawn (end grain with growth rings and a crack, lit), moss and a small
    mushroom on top."""
    k, u = S.k, S.u
    sc = SIZES.get(size, 1.0)
    rnd = S.rnd('log', cx)
    R = R or {'oak': OAK_BARK, 'birch': BIRCH_BARK, 'spruce': SPRUCE_BARK, 'dark_oak': DARK_OAK_BARK}[kind]  # noqa
    L = u(26 * sc)
    r = u(4.5)
    x0 = cx - L // 2
    lay = S.lay('log', 5)
    m = rect(x0, gy - 2 * r + 1, x0 + L - 1, gy)
    for (x, y) in m:
        ny = ((y - (gy - 2 * r + 1)) + 0.5) / (2 * r) * 2 - 1
        t = cyl_tone(ny * 0.9, cuts=(1.1, 0.95, 0.45, 0.0))
        lay[(x, y)] = R[t]
    for y in range(gy - 2 * r + 2, gy):                                 # furrows along the log
        x = x0 + rnd.randint(0, u(3))
        while x < x0 + L:
            run = rnd.randint(S.kv(3, 5), S.kv(7, 12))
            if rnd.random() < S.kv(0.35, 0.3):
                for i in range(run):
                    if (x + i, y) in m:
                        t = tone_of(lay[(x + i, y)])
                        lay[(x + i, y)] = R[max(SH, t - 2)]
                        if k == 2 and (x + i, y - 1) in m and t >= BS:
                            lay[(x + i, y - 1)] = R[min(HI, t + 1)]
            x += run + rnd.randint(2, 5)
    if kind == 'birch':
        bark(S, lay, set(), R, style='birch')
    outline(lay, m, R, skip={(q, gy + 1) for q in range(cx - 80, cx + 80)})
    end = S.lay('end_grain', 6)
    em = set()
    ecx, ecy = x0 - S.kv(0, 1), gy - r + 0.5
    for (x, y) in disc(ecx, ecy, r * 0.55, r):
        em.add((x, y))
    for (x, y) in em:
        d = math.hypot((x + 0.5 - ecx) / (r * 0.55), (y + 0.5 - ecy) / r)
        ring = int(d * S.kv(3, 5)) % 2
        t = LT if ring == 0 else BS
        if d > 0.86:
            t = DK
        if x + 0.5 > ecx + r * 0.2 and d > 0.5:
            t = max(SH, t - 1)
        end[(x, y)] = LOG_END[t]                                                                     # noqa
    for j in range(S.kv(1, 3)):                                          # a radial crack
        end[(int(ecx), int(ecy) - j)] = LOG_END[SH]                                                  # noqa
    outline(end, em, LOG_END)                                                                        # noqa
    if mossy and S.season != 'winter':
        ml = S.lay('moss', 8)
        tm = {(x, y) for (x, y) in m if x0 + L * 0.35 < x < x0 + L * 0.9}
        mm = moss_on(S, ml, tm, rnd, amount=0.8)
        outline(ml, mm, MOSS, skip=m | em)                                                           # noqa
        mu = S.lay('mushroom', 9)
        small_mushroom(S, mu, int(x0 + L * 0.7), gy - 2 * r, BROWN_CAP, small=True)                  # noqa
    if S.season == 'winter':
        snow_cap(S, [m, em], seed=cx)
    ground_shadow(S, x0, x0 + L + u(4), gy, rows=S.kv(2, 3), contact=(x0, x0 + L), steps=2)
    return {'ground': 'grass'}


def stump(S, cx, gy, kind='oak', **_):
    """Tree stump: a short furrowed trunk with roots, its sawn top seen from above (growth rings, a crack, the
    bark rim), moss on the shaded side."""
    k, u = S.k, S.u
    R = {'oak': OAK_BARK, 'birch': BIRCH_BARK, 'spruce': SPRUCE_BARK, 'dark_oak': DARK_OAK_BARK}[kind]  # noqa
    w = u(10)
    h = u(7)
    tm = trunk(S, cx, gy - h, gy, w, w - S.kv(1, 2), R, seed=cx, roots=S.kv(2, 3),
               style='birch' if kind == 'birch' else 'furrow')
    top = S.lay('top', 8)
    ry = S.kv(2.2, 4.2)
    tcx, tcy = cx - 0.5 + (0 if w % 2 else 0.5), gy - h + 0.5
    em = {(x, y) for (x, y) in disc(tcx, tcy, w / 2, ry)}
    for (x, y) in em:
        d = math.hypot((x + 0.5 - tcx) / (w / 2), (y + 0.5 - tcy) / ry)
        t = LT if int(d * S.kv(3, 5)) % 2 == 0 else BS
        if d > 0.8:
            t = BS if y < tcy else DK
        if x + 0.5 > tcx + w * 0.25:
            t = max(SH, t - 1)
        top[(x, y)] = (LOG_END if d <= 0.8 else R)[t]                                                # noqa
    for j in range(S.kv(2, 4)):
        top[(int(tcx) + j, int(tcy))] = LOG_END[SH]                                                  # noqa
    outline(top, em, R, skip=tm)
    if kind != 'birch' and S.season != 'winter':
        ml = S.lay('moss', 9)
        rnd = S.rnd('stumpmoss', cx)
        for (x, y) in sorted(tm):
            if x > cx + w // 4 and y > gy - h + S.kv(2, 3) and rnd.random() < 0.35:
                ml[(x, y)] = MOSS[BS if (x + y) % 2 else DK]                                         # noqa
    if S.season == 'winter':
        snow_cap(S, [em], seed=cx)
    ground_shadow(S, cx - w // 2, cx + w + u(3), gy, rows=S.kv(2, 3), contact=(cx - w // 2 - 2, cx + w // 2 + 2), steps=2)
    return {'ground': 'grass'}


# ------------------------------------------------------------------ fire and light
def flame(S, lay, cx, yb, h, w, R=None, seed=0, frame=0, m=None):
    """One flame tongue standing on (cx, yb): a pointed, wavering teardrop - white-hot core low in the middle,
    yellow, orange body, red edges and tip (fire is emissive and keeps its contrast). frame shifts the
    waver for animation."""
    R = R or FIRE                                                                                      # noqa
    m = set() if m is None else m
    rnd = S.rnd('flame', seed, frame)
    ph = rnd.uniform(0, 6) + frame * 1.3
    pts = {}
    for j in range(h):
        f = j / max(1, h - 1)                                           # 0 at the base, 1 at the tip
        half = (w / 2) * (math.sin(math.pi * min(1.0, 0.25 + f * 0.95)) if f < 0.3 else (1 - f) ** 0.9 * 1.25)
        off = math.sin(f * 4 + ph) * f * w * 0.35
        for x in range(int(math.floor(cx + off - half)), int(math.ceil(cx + off + half))):
            d = abs(x + 0.5 - (cx + off)) / max(0.5, half)
            t = HI if d < 0.35 and f < 0.45 else LT if d < 0.65 and f < 0.75 else BS if d < 0.9 else DK
            if f > 0.85:
                t = min(t, DK)
            pts[(x, yb - j)] = t
    for q, t in pts.items():
        lay[q] = R[t]
    m |= set(pts)
    return m


def campfire(S, cx, gy, soul=False, frame=0, smoke=True, **_):
    """Campfire: a ring of small stones, two crossed logs (lit tops, end grain on the near ends), glowing
    embers in the middle, three flame tongues (the middle one tallest), a warm light pool on the ground and
    smoke puffs; soul=True burns blue."""
    k, u = S.k, S.u
    rnd = S.rnd('campfire', cx)
    Rf = SOUL_FIRE if soul else FIRE                                                                   # noqa
    lg = S.lay('logs', 3)
    lm = set()
    lg_back = line(cx - u(5), gy - u(5), cx + u(6), gy - u(5))              # a log lying behind
    limb(S, lg, lg_back, S.kv(3, 5), S.kv(3, 5), OAK_BARK, lm, shade=False)                        # noqa
    for sgn in (-1, 1):                                                 # two crossed logs leaning in
        path = line(cx - sgn * u(7), gy - u(1), cx + sgn * u(4), gy - u(8))
        limb(S, lg, path, S.kv(3, 5), S.kv(3, 4), OAK_BARK, lm, shade=False)                         # noqa
    shade_wood(S, lg, lm, OAK_BARK)                                                                   # noqa
    for sgn in (-1, 1):                                                 # end grain on the near ends
        ex, ey = cx - sgn * u(7), gy - u(1)
        for (x, y) in disc(ex + 0.5, ey + 0.5, S.kv(1.5, 2.5)):
            lg[(x, y)] = LOG_END[LT if x <= ex else BS]                                                 # noqa
            lm.add((x, y))
    outline(lg, lm, OAK_BARK, skip={(q, gy + 1) for q in range(cx - 60, cx + 60)})                   # noqa
    st = S.lay('stones', 9)                                             # a ring of stones in front
    sm = set()
    for i, dx in enumerate((-9, -5, -1, 3, 7, 10)):
        rr = S.kv(1.5, 2.8) * (1.15 if i % 2 else 0.95)
        cxs = cx + u(dx)
        pts = disc(cxs + 0.5, gy - rr + 1.5, rr * 1.2, rr)
        for (x, y) in pts:
            st[(x, y)] = STONE[sphere_tone((x - cxs) / (rr * 1.2), (y - gy + rr - 1) / rr)]               # noqa
        sm |= pts
    outline(st, sm, STONE, skip={(q, gy + 2) for q in range(cx - 60, cx + 60)})                      # noqa
    em = S.lay('embers', 4)
    for x in range(cx - u(4), cx + u(4)):
        for j in range(S.kv(2, 3)):
            em[(x, gy - u(1) - j)] = EMBER[HI if (x + j) % 3 == 0 else LT if (x + j) % 3 == 1 else BS]   # noqa
    fl = S.lay('flames', 8)
    fm = set()
    flame(S, fl, cx - u(3), gy - u(2), u(7), u(4), Rf, seed=1, frame=frame, m=fm)
    flame(S, fl, cx + u(3), gy - u(2), u(6), u(4), Rf, seed=2, frame=frame, m=fm)
    flame(S, fl, cx, gy - u(2), u(11), u(6), Rf, seed=3, frame=frame, m=fm)
    if smoke:
        sk = S.lay('smoke', 9)
        for i, (dx, dy, r) in enumerate(((1, -15, 1.6), (-1, -19, 2.0), (2, -24, 1.4))):
            rr = u(r)
            pcx, pcy = cx + u(dx) + frame % 2, gy + u(dy) - frame
            pm = disc(pcx + 0.5, pcy + 0.5, rr)
            for (x, y) in pm:
                sk[(x, y)] = SMOKE[sphere_tone((x - pcx) / rr, (y - pcy) / rr, cuts=(0.95, 0.5, 0.0, -0.4))]  # noqa
            outline(sk, pm, SMOKE, lit=SMOKE[DK], dark=SMOKE[SH])                                       # noqa
    S.glow('light', {(x, y): 1 for (x, y) in disc(cx + 0.5, gy + 0.5, u(14), u(4))})
    return {'ground': 'grass' if not soul else 'sand'}


def torch(S, cx, gy, soul=False, frame=0, **_):
    """Torch stuck in the ground: a lit-left wooden stick, a charred head, a small flame, a light pool."""
    k, u = S.k, S.u
    st = S.lay('stick', 5)
    w, h = S.kv(2, 4), u(10)
    m = rect(cx - w // 2, gy - h + 1, cx - w // 2 + w - 1, gy)
    for (x, y) in m:
        i = x - (cx - w // 2)
        st[(x, y)] = OAK_PLANK[LT if i == 0 else DK if i == w - 1 else BS]                              # noqa
    for x in range(cx - w // 2, cx - w // 2 + w):                       # the charred head
        for j in range(S.kv(2, 3)):
            st[(x, gy - h + 1 + j)] = COAL[LT if x == cx - w // 2 else BS]                             # noqa
    outline(st, m, OAK_PLANK, skip={(q, gy + 1) for q in range(cx - 30, cx + 30)})                    # noqa
    fl = S.lay('flame', 8)
    flame(S, fl, cx - (0.5 if k == 1 else 0), gy - h, u(5), S.kv(3, 5), SOUL_FIRE if soul else FIRE, seed=cx, frame=frame)  # noqa
    pool = {(x, y): 1 for (x, y) in disc(cx + 0.5, gy + 0.5, u(7), u(2.5))}
    S.glow('light', pool)
    return {'ground': 'grass'}


def lantern(S, cx, gy, soul=False, hanging=False, **_):
    """Lantern: a dark iron cage (lit left bars, a cap with a handle loop, a base plate) round glowing glass
    (a white-hot core in the light ramp); standing on the ground or hanging from a chain."""
    k, u = S.k, S.u
    Rg = SOUL_GLOW if soul else GLOW                                                                   # noqa
    R = DARK_IRON                                                                                      # noqa
    lay = S.lay('lantern', 6)
    w, h = S.kv(6, 12), S.kv(7, 13)
    yb = gy - (u(12) if hanging else 0)
    x0 = cx - w // 2
    m = set()
    body = rect(x0, yb - h + 1, x0 + w - 1, yb)
    for (x, y) in body:
        i, j = x - x0, y - (yb - h + 1)
        glass = 0 < i < w - 1 and 1 < j < h - 1
        if glass:
            d = abs(i + 0.5 - w / 2) / (w / 2)
            t = HI if d < 0.35 and j < h * 0.7 else LT if d < 0.7 else BS
            lay[(x, y)] = Rg[t]
        else:
            lay[(x, y)] = R[LT if i == 0 or j == 0 else DK if i == w - 1 or j == h - 1 else BS]
        m.add((x, y))
    if k == 2:                                                        # a bar across the glass
        for x in range(x0 + 1, x0 + w - 1):
            lay[(x, yb - h // 2)] = R[BS]
    for x in range(x0 + 1, x0 + w - 1):                               # cap
        lay[(x, yb - h)] = R[LT if x < cx else BS]
        m.add((x, yb - h))
    for (a, b) in ((0, 1), (-1, 2), (1, 2), (0, 2)) if k == 1 else ((-1, 1), (0, 1), (-2, 2), (1, 2), (-2, 3), (1, 3), (-1, 4), (0, 4)):
        q = (cx + a - (0 if k == 1 else 0), yb - h - b)
        lay[q] = R[LT if a < 0 else BS]
        m.add(q)
    if hanging:
        for j in range(yb - h - S.kv(3, 5), gy - u(20), -1):
            q = (cx - (j % 2 if k == 2 else 0), j)
            lay[q] = R[LT if j % 2 else DK]
            m.add(q)
    outline(lay, m, R)
    if not hanging:
        S.glow('light', {(x, y): 1 for (x, y) in disc(cx + 0.5, gy + 0.5, u(8), u(2.5))})
        ground_shadow(S, cx, cx + w, gy, rows=S.kv(1, 2), steps=1)
    return {'ground': 'grass' if not hanging else None}


# ------------------------------------------------------------------ signs, fences
def planks_face(S, lay, m, R, horizontal=True, seed=0, board=None):
    """Plank texture on a face: boards (a seam line one step darker every `board` px, a lit row under it),
    grain streaks along the boards, nail pairs at HD."""
    k = S.k
    rnd = S.rnd('planks', seed)
    board = board or S.kv(3, 5)
    x0, y0, x1, y1 = bbox(m)
    for (x, y) in m:
        r = (y - y0) if horizontal else (x - x0)
        t = BS
        if r % board == board - 1:
            t = DK
        elif r % board == 0:
            t = LT
        lay[(x, y)] = R[t]
    for (x, y) in sorted(m):
        if rnd.random() < S.kv(0.05, 0.05) and tone_of(lay[(x, y)]) == BS:
            L = rnd.randint(2, S.kv(3, 6))
            for i in range(L):
                q = (x + i, y) if horizontal else (x, y + i)
                if q in m and tone_of(lay[q]) == BS:
                    lay[q] = R[DK]


def sign(S, cx, gy, wood='oak', lines=3, **_):
    """Standing sign: a plank board on a post - lit top / left edges, a dark bottom edge, boards with
    grain, engraved text lines (dark strokes with a lit lower lip), nails at HD; it casts a shadow."""
    k, u = S.k, S.u
    rnd = S.rnd('sign', cx)
    R = {'oak': OAK_PLANK, 'spruce': SPRUCE_PLANK, 'birch': BIRCH_PLANK, 'dark_oak': DARK_OAK_PLANK}[wood]  # noqa
    post = S.lay('post', 4)
    pw = S.kv(2, 4)
    pm = rect(cx - pw // 2, gy - u(14), cx - pw // 2 + pw - 1, gy)
    for (x, y) in pm:
        post[(x, y)] = R[LT if x == cx - pw // 2 else DK if x == cx - pw // 2 + pw - 1 else BS]
    outline(post, pm, R, skip={(q, gy + 1) for q in range(cx - 30, cx + 30)})
    bd = S.lay('board', 6, cast=(S.kv(1, 2), S.kv(1, 2), 1))
    bw, bh = u(16), u(9)
    x0, y0 = cx - bw // 2, gy - u(17)
    bm = rect(x0, y0, x0 + bw - 1, y0 + bh - 1)
    planks_face(S, bd, bm, R, board=S.kv(3, 4), seed=cx)
    for (x, y) in bm:
        if y == y0 or x == x0:
            bd[(x, y)] = R[HI if y == y0 else LT]
        elif y == y0 + bh - 1 or x == x0 + bw - 1:
            bd[(x, y)] = R[SH]
    for i in range(lines):                                         # engraved text lines
        y = y0 + S.kv(2, 3) + i * S.kv(2, 4)
        if y >= y0 + bh - 2:
            break
        x = x0 + S.kv(2, 3)
        while x < x0 + bw - S.kv(3, 4):
            L = rnd.randint(S.kv(1, 2), S.kv(3, 6))
            for j in range(L):
                if x + j < x0 + bw - S.kv(2, 3):
                    bd[(x + j, y)] = R[SH]
                    if k == 2:
                        bd[(x + j, y + 1)] = R[LT]
            x += L + S.kv(1, 2)
    if k == 2:
        for (x, y) in ((x0 + 2, y0 + 2), (x0 + bw - 3, y0 + 2), (x0 + 2, y0 + bh - 3), (x0 + bw - 3, y0 + bh - 3)):
            bd[(x, y)] = DARK_IRON[LT]                                                                    # noqa
    outline(bd, bm, R)
    ground_shadow(S, cx - u(1), cx + u(9), gy, rows=S.kv(1, 2), contact=(cx - pw, cx + pw), steps=2)
    return {'ground': 'grass'}


def hanging_sign(S, cx, gy, wood='spruce', **_):
    """Hanging sign: a board on two chains from an iron bracket on a post (light post, plank board with
    text strokes, chain links alternating lit / dark)."""
    k, u = S.k, S.u
    rnd = S.rnd('hsign', cx)
    R = {'oak': OAK_PLANK, 'spruce': SPRUCE_PLANK, 'birch': BIRCH_PLANK, 'dark_oak': DARK_OAK_PLANK}[wood]  # noqa
    post = S.lay('post', 4)
    pw = S.kv(3, 5)
    px0 = cx - u(9)
    pm = rect(px0, gy - u(26), px0 + pw - 1, gy)
    for (x, y) in pm:
        post[(x, y)] = SPRUCE_BARK[LT if x == px0 else DK if x == px0 + pw - 1 else BS]                   # noqa
    outline(post, pm, SPRUCE_BARK, skip={(q, gy + 1) for q in range(cx - 40, cx + 40)})               # noqa
    arm = S.lay('bracket', 5)
    am = rect(px0, gy - u(25), cx + u(9), gy - u(25) + S.kv(1, 2))
    for (x, y) in am:
        arm[(x, y)] = DARK_IRON[LT if y == gy - u(25) else DK]                                          # noqa
    outline(arm, am, DARK_IRON, skip=pm)                                                               # noqa
    ch = S.lay('chains', 6)
    bw, bh = u(14), u(8)
    x0, y0 = cx - bw // 2 + u(1), gy - u(17)
    cm = set()
    for xx in (x0 + S.kv(2, 3), x0 + bw - S.kv(3, 4)):
        for y in range(gy - u(24) + 1, y0):
            ch[(xx, y)] = DARK_IRON[LT if (y % 2) else DK]                                             # noqa
            cm.add((xx, y))
    bd = S.lay('board', 7, cast=(S.kv(1, 2), S.kv(1, 2), 1))
    bm = rect(x0, y0, x0 + bw - 1, y0 + bh - 1)
    planks_face(S, bd, bm, R, board=S.kv(4, 4), seed=cx)
    for (x, y) in bm:
        if y == y0 or x == x0:
            bd[(x, y)] = R[HI if y == y0 else LT]
        elif y == y0 + bh - 1 or x == x0 + bw - 1:
            bd[(x, y)] = R[SH]
    for i in range(2):
        y = y0 + S.kv(2, 3) + i * S.kv(3, 4)
        x = x0 + S.kv(2, 3)
        while x < x0 + bw - S.kv(3, 4):
            L = rnd.randint(S.kv(1, 2), S.kv(3, 5))
            for j in range(L):
                if x + j < x0 + bw - S.kv(2, 3):
                    bd[(x + j, y)] = R[SH]
            x += L + S.kv(1, 2)
    outline(bd, bm, R)
    ground_shadow(S, px0, px0 + u(6), gy, rows=S.kv(1, 2), contact=(px0 - 1, px0 + pw), steps=2)
    return {'ground': 'grass'}


WOODS = {'oak': (OAK_PLANK, OAK_BARK), 'spruce': (SPRUCE_PLANK, SPRUCE_BARK), 'birch': (BIRCH_PLANK, BIRCH_BARK),   # noqa
         'dark_oak': (DARK_OAK_PLANK, DARK_OAK_BARK)}                                                  # noqa


def fence_post(S, lay, x, gy, h, R, m):
    w = S.kv(4, 6)
    pm = rect(x, gy - h + 1, x + w - 1, gy)
    for (px_, py_) in pm:
        i = px_ - x
        t = LT if i == 0 else DK if i == w - 1 else BS
        if py_ == gy - h + 1:
            t = HI if i < w - 1 else LT                                   # the sawn top
        elif py_ == gy - h + 2 and S.k == 2:
            t = LT if i < w - 1 else DK
        if S.k == 2 and i == 2 and (py_ * 3) % 7 == 0:
            t = DK                                                        # grain
        lay[(px_, py_)] = R[t]
    m |= pm
    return pm


def fence(S, cx, gy, wood='oak', sections=2, **_):
    """Fence: posts (lit left, dark right, a light sawn top) joined by two rails (lit top edge, dark bottom
    edge); rails cast a shadow on the ground behind; nails at HD."""
    k, u = S.k, S.u
    R = WOODS[wood][0]
    span = u(16)
    x0 = cx - sections * span // 2
    rails = S.lay('rails', 4, cast=(u(1), u(1), 1))
    rm = set()
    posts = S.lay('posts', 6)
    pm = set()
    pw = S.kv(4, 6)
    for i in range(sections + 1):
        fence_post(S, posts, x0 + i * span, gy, u(16), R, pm)
    for (yy, hh) in ((gy - u(12), S.kv(2, 3)), (gy - u(6), S.kv(2, 3))):
        for x in range(x0 + pw, x0 + sections * span):
            for j in range(hh):
                t = LT if j == 0 else DK if j == hh - 1 else BS
                rails[(x, yy + j)] = R[t]
                rm.add((x, yy + j))
        if k == 2:
            for i in range(sections + 1):
                px_ = x0 + i * span
                for xx in (px_ + pw + 1, px_ - 2):
                    if (xx, yy + 1) in rm:
                        rails[(xx, yy + 1)] = DARK_IRON[LT]                                             # noqa
    outline(rails, rm, R, skip=pm)
    outline(posts, pm, R, skip={(q, gy + 1) for q in range(x0 - 40, x0 + sections * span + 40)})
    ground_shadow(S, x0, x0 + sections * span + pw + u(2), gy, rows=S.kv(1, 2), steps=1)
    if S.season == 'winter':
        snow_cap(S, [rm, pm], seed=cx, depth=S.kv(1, 2))
    return {'ground': 'grass'}


def fence_gate(S, cx, gy, wood='oak', open=False, **_):
    """Fence gate between two posts: a frame of two rails and end stiles with a diagonal brace (closed), or
    the two halves swung toward the viewer (open: narrow foreshortened panels at the posts)."""
    k, u = S.k, S.u
    R = WOODS[wood][0]
    span = u(20)
    x0 = cx - span // 2
    pw = S.kv(4, 6)
    posts = S.lay('posts', 6)
    pm = set()
    fence_post(S, posts, x0, gy, u(16), R, pm)
    fence_post(S, posts, x0 + span, gy, u(16), R, pm)
    gate = S.lay('gate', 5, cast=(u(1), u(1), 1))
    gm = set()
    yt, yb = gy - u(13), gy - u(3)
    if not open:
        for x in range(x0 + pw, x0 + span):
            for yy in (yt, yb):
                for j in range(S.kv(2, 3)):
                    gate[(x, yy + j)] = R[LT if j == 0 else DK if j == S.kv(1, 2) else BS]
                    gm.add((x, yy + j))
        for xx in (x0 + pw + S.kv(1, 2), x0 + span // 2 + pw // 2 - 1, x0 + span - S.kv(2, 3)):
            for y in range(yt, yb + S.kv(2, 3)):
                for i in range(S.kv(2, 3)):
                    gate[(xx + i, y)] = R[LT if i == 0 else BS]
                    gm.add((xx + i, y))
        for q in line(x0 + pw + S.kv(2, 3), yb, x0 + span // 2 + pw // 2 - 2, yt + S.kv(2, 3)):
            gate[q] = R[LT]
            gate[(q[0] + 1, q[1])] = R[DK]
            gm |= {q, (q[0] + 1, q[1])}
    else:
        for (xp, d) in ((x0 + pw, 1), (x0 + span - 1, -1)):
            for i in range(S.kv(4, 7)):
                x = xp + d * i
                for y in range(yt + i // 2, yb + S.kv(2, 3) + i // 3):
                    gate[(x, y)] = R[(LT if d > 0 else DK) if i == 0 else BS]
                    gm.add((x, y))
    outline(gate, gm, R, skip=pm)
    outline(posts, pm, R, skip={(q, gy + 1) for q in range(x0 - 40, x0 + span + 40)})
    ground_shadow(S, x0, x0 + span + pw + u(2), gy, rows=S.kv(1, 2), steps=1)
    return {'ground': 'grass'}


# ------------------------------------------------------------------ props
def hay_bale(S, cx, gy, **_):
    """Hay bale: a block of straw seen front-above - straw strands along the front (lit and dark dashes),
    cut ends on the top, two dark twine bands wrapping front and top, the side in shade."""
    k, u = S.k, S.u
    rnd = S.rnd('hay', cx)
    w, h, d = u(12), u(10), u(4)
    x0 = cx - (w + d) // 2
    lay = S.lay('hay_bale', 5)
    f = box_faces(x0, gy, w, h, d)
    box_shade(lay, f, HAY)                                                                            # noqa
    for face, horiz in (('front', True), ('side', True), ('top', False)):
        for (x, y) in sorted(f[face]):
            if rnd.random() < S.kv(0.14, 0.12):
                L = rnd.randint(2, S.kv(3, 5))
                t0 = tone_of(lay[(x, y)])
                c = HAY[max(SH, t0 - 1)] if rnd.random() < 0.6 else HAY[min(HI, t0 + 1)]           # noqa
                for i in range(L):
                    q = (x + i, y) if horiz else (x + i // 2, y - i // 2)
                    if q in f[face]:
                        lay[q] = c
    for bx in (x0 + w // 4, x0 + w - w // 4 - S.kv(1, 2)):           # twine bands
        for i in range(S.kv(1, 2)):
            for (x, y) in f['front']:
                if x == bx + i:
                    lay[(x, y)] = HAY_BAND[LT if i == 0 else BS]                                        # noqa
            for j in range(1, d + 1):
                lay[(bx + i + j, gy - h + 1 - j)] = HAY_BAND[HI if i == 0 else LT]                      # noqa
    solid = set().union(*f.values())
    outline(lay, solid, HAY, skip={(q, gy + 1) for q in range(cx - 40, cx + 40)})                     # noqa
    if S.season == 'winter':
        snow_cap(S, [solid], seed=cx)
    ground_shadow(S, x0 + u(2), x0 + w + d + u(4), gy, rows=S.kv(2, 3), contact=(x0, x0 + w), steps=2)
    return {'ground': 'grass'}


def barrel(S, cx, gy, wood='spruce', **_):
    """Barrel: an upright, bulging cylinder of staves (seams one step darker, lit left, dark right), two iron
    hoops with a lit rim, the lid seen from above - an ellipse of boards with a dark rim."""
    k, u = S.k, S.u
    R = WOODS[wood][0]
    lay = S.lay('barrel', 5)
    w, h = u(12), u(14)
    yt = gy - h + 1
    m = set()
    for y in range(yt, gy + 1):
        f = (y - yt) / h
        bul = int(round(math.sin(math.pi * f) * S.kv(1, 2)))
        for x in range(cx - w // 2 - bul, cx + w // 2 + bul):
            m.add((x, y))
    sp = _spans(m)
    for (x, y) in m:
        xl, xr = sp[y]
        nx = ((x - xl) + 0.5) / (xr - xl + 1) * 2 - 1
        t = cyl_tone(nx)
        if (x - cx) % S.kv(3, 4) == 0 and abs(nx) < 0.85:
            t = max(SH, t - 1)                                             # stave seams
        lay[(x, y)] = R[t]
    for hy in (yt + u(3), gy - u(3)):
        for j in range(S.kv(1, 2)):
            xl, xr = sp[hy + j]
            for x in range(xl, xr + 1):
                nx = ((x - xl) + 0.5) / (xr - xl + 1) * 2 - 1
                lay[(x, hy + j)] = DARK_IRON[min(HI, cyl_tone(nx) + (1 if j == 0 else 0))]              # noqa
    lid = {(x, y) for (x, y) in disc(cx, yt + 0.5, w / 2, S.kv(2, 3.5)) if y <= yt}
    for (x, y) in lid:
        d = abs(x + 0.5 - cx) / (w / 2)
        lay[(x, y)] = R[LT if (x - cx) % S.kv(3, 4) else BS] if d < 0.8 else R[DK]
    m |= lid
    outline(lay, m, R, skip={(q, gy + 1) for q in range(cx - 40, cx + 40)})
    if S.season == 'winter':
        snow_cap(S, [m], seed=cx)
    ground_shadow(S, cx - w // 2 + u(1), cx + w // 2 + u(5), gy, rows=S.kv(2, 3), contact=(cx - w // 2, cx + w // 2), steps=2)
    return {'ground': 'grass'}


def crate(S, cx, gy, wood='oak', **_):
    """Wooden crate: a block seen front-above - a frame of light boards round each face, darker inset boards,
    a diagonal brace on the front, nails at the corners."""
    k, u = S.k, S.u
    R = WOODS[wood][0]
    w, h, d = u(12), u(11), u(4)
    x0 = cx - (w + d) // 2
    lay = S.lay('crate', 5)
    f = box_faces(x0, gy, w, h, d)
    box_shade(lay, f, R)
    fr = S.kv(2, 3)
    fx0, fy0 = x0, gy - h + 1
    for (x, y) in f['front']:
        i, j = x - fx0, y - fy0
        if fr <= i < w - fr and fr <= j < h - fr:
            t = DK if (i - fr) % S.kv(3, 4) == S.kv(2, 3) else BS
            if (j - fr) == 0:
                t = SH                                                     # the frame's shadow on the inset
            lay[(x, y)] = R[t]
        elif j == 0 or i == 0:
            lay[(x, y)] = R[HI if j == 0 else LT]
        elif j == h - 1 or i == w - 1:
            lay[(x, y)] = R[DK]
        else:
            lay[(x, y)] = R[LT]
    for q in line(fx0 + fr, gy - fr, fx0 + w - fr - 1, fy0 + fr):
        lay[q] = R[LT]
        if (q[0], q[1] + 1) in f['front'] and k == 2:
            lay[(q[0], q[1] + 1)] = R[DK]
    for (x, y) in f['top']:
        i = x - fx0 - (gy - h + 1 - y)
        if i % S.kv(4, 6) == 0:
            lay[(x, y)] = R[BS]
    if k == 2:
        for (x, y) in ((fx0 + 1, fy0 + 1), (fx0 + w - 2, fy0 + 1), (fx0 + 1, gy - 1), (fx0 + w - 2, gy - 1)):
            lay[(x, y)] = DARK_IRON[LT]                                                                 # noqa
    solid = set().union(*f.values())
    outline(lay, solid, R, skip={(q, gy + 1) for q in range(cx - 40, cx + 40)})
    if S.season == 'winter':
        snow_cap(S, [solid], seed=cx)
    ground_shadow(S, x0 + u(2), x0 + w + d + u(4), gy, rows=S.kv(2, 3), contact=(x0, x0 + w), steps=2)
    return {'ground': 'grass'}


def chest(S, cx, gy, wood='chest', **_):
    """Chest: a block with a lid (its seam a dark line a third of the way down, a lit lip under it), metal
    corner fittings, a gold latch in the middle of the seam; planks on the faces."""
    k, u = S.k, S.u
    R = CHEST_WOOD if wood == 'chest' else WOODS[wood][0]                                             # noqa
    w, h, d = u(12), u(10), u(4)
    x0 = cx - (w + d) // 2
    lay = S.lay('chest', 5)
    f = box_faces(x0, gy, w, h, d)
    box_shade(lay, f, R)
    fy0 = gy - h + 1
    seam = fy0 + h // 3
    for (x, y) in f['front'] | f['side']:
        if y == seam - ((x - x0 - w + 1) if (x, y) in f['side'] else 0):
            lay[(x, y)] = R[O]
        elif y == seam + 1 - ((x - x0 - w + 1) if (x, y) in f['side'] else 0):
            lay[(x, y)] = R[LT if (x, y) in f['front'] else BS]
        elif (x, y) in f['front'] and (y - fy0) % S.kv(3, 4) == 0 and y > seam + 1:
            lay[(x, y)] = R[DK]
    for (x, y) in f['front']:                                          # corner fittings
        if (x - x0 < S.kv(1, 2) or x0 + w - 1 - x < S.kv(1, 2)) and (y - fy0 < S.kv(2, 3) or gy - y < S.kv(2, 3) or abs(y - seam) <= S.kv(0, 1)):
            lay[(x, y)] = IRON[LT if x - x0 < S.kv(1, 2) else BS]                                      # noqa
    lt = S.lay('latch', 6)
    lw, lh = S.kv(2, 4), S.kv(3, 5)
    lm = rect(x0 + w // 2 - lw // 2, seam - 1, x0 + w // 2 - lw // 2 + lw - 1, seam - 1 + lh - 1)
    for (x, y) in lm:
        lt[(x, y)] = GOLD[HI if (x, y) == (min(a for a, _ in lm), min(b for _, b in lm)) else LT if x == min(a for a, _ in lm) else BS]  # noqa
    outline(lt, lm, GOLD)                                                                              # noqa
    solid = set().union(*f.values())
    outline(lay, solid, R, skip={(q, gy + 1) for q in range(cx - 40, cx + 40)})
    if S.season == 'winter':
        snow_cap(S, [solid], seed=cx)
    ground_shadow(S, x0 + u(2), x0 + w + d + u(4), gy, rows=S.kv(2, 3), contact=(x0, x0 + w), steps=2)
    return {'ground': 'grass'}


def bee(S, lay, x, y, R=None, flip=False):
    """A tiny bee: striped body (yellow / dark), a pale wing on top, at k=1 4x3, HD 7x5."""
    k = S.k
    f = -1 if flip else 1
    if k == 1:
        pts = {(0, 1): BEE[LT], (1, 1): BEE_DARK[BS], (2, 1): BEE[BS], (3, 1): BEE_DARK[DK],              # noqa
               (1, 0): WING[HI], (2, 0): WING[LT]}                                                         # noqa
    else:
        pts = {}
        for i in range(6):
            for j in range(3):
                stripe = i in (2, 4)
                pts[(i, 2 + j)] = (BEE_DARK if stripe else BEE)[LT if j == 0 else BS if j == 1 else DK]    # noqa
        pts[(6, 3)] = BEE_DARK[DK]                                                                         # noqa
        for (a, b) in ((1, 0), (2, 0), (3, 0), (1, 1), (2, 1), (3, 1), (4, 1)):
            pts[(a, b)] = WING[HI if b == 0 else LT]                                                       # noqa
        pts[(0, 3)] = BEE_DARK[BS]                                                                          # noqa
    for (a, b), c in pts.items():
        lay[(x + f * a, y + b)] = c


def beehive(S, cx, gy, **_):
    """Beehive: a wooden hive block seen front-above (board seams, lit top with planks), a dark entrance slot
    with honey dripping from its lower lip, a honeycomb patch, bees buzzing round it."""
    k, u = S.k, S.u
    rnd = S.rnd('hive', cx)
    w, h, d = u(12), u(11), u(4)
    x0 = cx - (w + d) // 2
    lay = S.lay('hive', 5)
    f = box_faces(x0, gy, w, h, d)
    box_shade(lay, f, HIVE_WOOD)                                                                        # noqa
    fy0 = gy - h + 1
    for (x, y) in f['front']:
        if (y - fy0) % S.kv(4, 5) == 0 and y > fy0:
            lay[(x, y)] = HIVE_WOOD[DK]                                                                 # noqa
        elif (y - fy0) % S.kv(4, 5) == 1 and y > fy0 + 1:
            lay[(x, y)] = HIVE_WOOD[LT]                                                                 # noqa
    ey = fy0 + h // 2
    for x in range(x0 + S.kv(3, 5), x0 + w - S.kv(3, 5)):                 # the entrance
        for j in range(S.kv(2, 3)):
            lay[(x, ey + j)] = HIVE_WOOD[O] if j < S.kv(1, 2) else HIVE_WOOD[SH]                         # noqa
    hn = S.lay('honey', 6)
    hm = set()
    for x in range(x0 + S.kv(3, 5), x0 + w - S.kv(3, 5)):
        hn[(x, ey + S.kv(2, 3))] = HONEY[LT if x < cx else BS]                                           # noqa
        hm.add((x, ey + S.kv(2, 3)))
        if rnd.random() < 0.35:
            L = rnd.randint(1, S.kv(2, 4))
            for j in range(1, L + 1):
                hn[(x, ey + S.kv(2, 3) + j)] = HONEY[BS if j < L else HI]                                # noqa
                hm.add((x, ey + S.kv(2, 3) + j))
    for (x, y) in f['top']:
        i = x - x0 - (fy0 - y)
        if i % S.kv(3, 5) == 0:
            lay[(x, y)] = HIVE_WOOD[BS]                                                                 # noqa
    solid = set().union(*f.values())
    outline(lay, solid, HIVE_WOOD, skip={(q, gy + 1) for q in range(cx - 40, cx + 40)})               # noqa
    bees = S.lay('bees', 30)
    for (dx, dy, fl) in ((-10, -15, False), (9, -18, True), (12, -8, True)):
        bee(S, bees, cx + u(dx), gy + u(dy), flip=fl)
    if S.season == 'winter':
        snow_cap(S, [solid], seed=cx)
    ground_shadow(S, x0 + u(2), x0 + w + d + u(4), gy, rows=S.kv(2, 3), contact=(x0, x0 + w), steps=2)
    return {'ground': 'grass'}


# ------------------------------------------------------------------ lava, snow, ice, small mushrooms
def lava_pool(S, cx, gy, size='m', frame=0, **_):
    """Lava pool: an oval of molten lava (bright cores, orange body, red edges) with dark crust plates whose
    edges glow, bubbles, a stone rim, and the glow it throws on the stone round it (lit bands, stepped)."""
    k, u = S.k, S.u
    sc = SIZES.get(size, 1.0)
    rnd = S.rnd('lava', cx, frame)
    rx, ry = u(15 * sc), u(4.5 * sc)
    lay = S.lay('lava', 2)
    cy = gy - ry
    m = disc(cx + 0.5, cy + 0.5, rx, ry)
    for (x, y) in m:
        n = math.sin(x * 0.5 / k + frame) + math.sin(y * 0.9 / k + x * 0.2 / k)
        t = HI if n > 1.2 else LT if n > 0.2 else BS if n > -0.9 else DK
        lay[(x, y)] = LAVA[t]                                                                           # noqa
    crust = S.lay('crust', 3)
    cm = set()
    for _ in range(S.kv(4, 6)):
        p = rnd.choice(sorted(m))
        b = {(p[0] + a, p[1] + c) for a, c in blob(rnd, S.kv(rnd.randint(3, 6), rnd.randint(8, 16)), wide=1.8, tall=0.6)}
        b &= m
        for (x, y) in b:
            crust[(x, y)] = LAVA_CRUST[LT if (x, y - 1) not in b else BS if (x + 1, y) in b else DK]   # noqa
            cm.add((x, y))
        for q in edge_ring(b) & m:
            crust[q] = LAVA[HI]                                                                          # noqa
    for _ in range(S.kv(2, 3)):                                          # bubbles
        p = rnd.choice(sorted(m - cm))
        crust[p] = LAVA[HI]                                                                              # noqa
        crust[(p[0] + 1, p[1])] = LAVA[LT]                                                               # noqa
    rim = S.lay('rim', 1)
    rm = set()
    ring = edge_ring(m)
    ring2 = edge_ring(m | ring) if k == 2 else set()
    for (x, y) in ring | ring2:
        rim[(x, y)] = STONE_LIT[LT if y < cy else BS] if (x, y) in ring else STONE[BS]                    # noqa
        rm.add((x, y))
    S.glow('glow', {(x, y): 1 for (x, y) in disc(cx + 0.5, cy + 0.5, rx + u(6), ry + u(3))})
    return {'ground': 'stone', 'ground_opts': {'back': ry * 2 + u(3), 'front': u(4)}}


def snow_drift(S, cx, gy, size='m', **_):
    """Snow drift: a wind-shaped mound - a crisp lit crest on the left, a long base, cool blue shade on the
    lee side, sparkle glints, a few dry blades poking through."""
    k, u = S.k, S.u
    sc = SIZES.get(size, 1.0)
    rnd = S.rnd('drift', cx)
    lay = S.lay('drift', 5)
    rx, ry = u(15 * sc), u(9 * sc)
    m = set()
    for x in range(cx - rx, cx + rx + 1):
        f = (x - (cx - rx)) / (2 * rx)
        hgt = ry * (math.sin(math.pi * min(1, f * 1.25)) ** 0.7 if f < 0.4 else (1 - (f - 0.4) / 0.6) ** 1.3)
        for y in range(int(gy - hgt), gy + 1):
            m.add((x, y))
    c = cols(m)
    for (x, y) in m:
        yt = c[x][0]
        slope = c.get(x + 1, c[x])[0] - yt
        crest = cx - rx + int(2 * rx * 0.4)
        t = LT if x < crest else BS
        if y - yt < S.kv(1, 2):
            t = HI if x <= crest else LT
        if x > crest and y - yt >= S.kv(1, 2):
            t = DK if (y - yt) < (x - crest) * 0.6 + u(2) else BS      # the lee slope in blue shade
        if y >= gy - S.kv(0, 1):
            t = DK
        lay[(x, y)] = SNOW[t]                                                                           # noqa
    for (x, y) in sorted(m):
        if rnd.random() < S.kv(0.02, 0.015) and tone_of(lay[(x, y)]) >= BS:
            lay[(x, y)] = SNOW[HI]                                                                     # noqa
    outline(lay, m, SNOW, skip={(q, gy + 1) for q in range(cx - 60, cx + 60)})                       # noqa
    bl = S.lay('blades', 6)
    for x in (cx - rx + u(4), cx + rx - u(5)):
        for i in range(3):
            for j in range(rnd.randint(2, S.kv(4, 7))):
                bl[(x + i * S.kv(1, 2), c.get(x + i, (gy, gy))[0] - j)] = DRY_PLANT[LT if i == 0 else BS]  # noqa
    return {'ground': 'snow'}


def ice_spikes(S, cx, gy, size='m', **_):
    """Ice spikes: tall faceted spires of packed ice - lit left face, base front, dark right face, pale
    streaks running up each spire, sharp tips - on snow."""
    k, u = S.k, S.u
    sc = SIZES.get(size, 1.0)
    rnd = S.rnd('ice', cx)
    for i, (dx, h, w) in enumerate(((-7, 24, 5), (8, 18, 4.5), (0, 40, 7))):
        lay = S.lay(f'spike_{i + 1}', 5 + i, cast=(u(1), 0, 1))
        H, W = u(h * sc), u(w)
        x0 = cx + u(dx)
        m = set()
        for y in range(gy - H, gy + 1):
            f = (gy - y) / H
            half = W / 2 * (1 - f) ** 0.85
            for x in range(int(math.floor(x0 - half)), int(math.ceil(x0 + half))):
                m.add((x, y))
        sp = _spans(m)
        for (x, y) in m:
            xl, xr = sp[y]
            r = (x - xl + 0.5) / (xr - xl + 1)
            t = LT if r < 0.34 else BS if r < 0.67 else DK
            if r < 0.15 and (x, y - 1) in m:
                t = HI
            if (x, y - 1) not in m:
                t = min(HI, t + 1)                                       # the facet edges catch the light
            lay[(x, y)] = PACKED_ICE[t]                                                                # noqa
        for _ in range(S.kv(2, 4)):                                      # streaks up the spire
            y = rnd.randint(gy - H // 2, gy - 1)
            xl, xr = sp[y]
            x = rnd.randint(xl, max(xl, xr - 1))
            for j in range(rnd.randint(S.kv(3, 5), S.kv(6, 12))):
                if (x, y - j) in m:
                    t = tone_of(lay[(x, y - j)])
                    lay[(x, y - j)] = PACKED_ICE[min(HI, t + 1)]                                         # noqa
        outline(lay, m, PACKED_ICE, skip={(q, gy + 1) for q in range(cx - 60, cx + 60)})              # noqa
    ground_shadow(S, cx - u(4), cx + u(16), gy, rows=S.kv(2, 3), steps=1)
    return {'ground': 'snow'}


def mushrooms(S, cx, gy, kind='red', **_):
    """Small mushrooms: a group of two or three (cream stems, dome caps lit top-left, red ones with white
    spots), the smaller ones in front."""
    k, u = S.k, S.u
    R = RED_CAP if kind == 'red' else BROWN_CAP                                                       # noqa
    lay = S.lay('mushrooms', 5)
    small_mushroom(S, lay, cx - u(3), gy - S.kv(0, 1), R)
    small_mushroom(S, lay, cx + u(2), gy, R, small=True)
    if kind == 'brown':
        small_mushroom(S, lay, cx - u(6), gy, R, small=True)
    _small_shadow(S, cx - u(2), gy, w=u(7))
    return {'ground': 'podzol' if kind == 'brown' else 'grass'}


# ------------------------------------------------------------------ API
CATALOG = {}


def _register():
    CATALOG.update({
        'oak': oak, 'birch': birch, 'spruce': spruce, 'jungle': jungle, 'acacia': acacia, 'dark_oak': dark_oak,
        'cherry': cherry, 'palm': palm, 'dead_tree': dead_tree, 'swamp_oak': swamp_oak,
        'giant_red_mushroom': lambda S, cx, gy, **o: giant_mushroom(S, cx, gy, kind='red', **o),
        'giant_brown_mushroom': lambda S, cx, gy, **o: giant_mushroom(S, cx, gy, kind='brown', **o),
        'bush': bush, 'berry_bush': lambda S, cx, gy, **o: bush(S, cx, gy, berries=True, **o),
        'tall_grass': tall_grass, 'fern': fern, 'dead_bush': dead_bush,
        'poppy': poppy, 'dandelion': dandelion, 'cornflower': cornflower, 'blue_orchid': blue_orchid,
        'tulip_red': lambda S, cx, gy, **o: tulip(S, cx, gy, color='red', **o),
        'tulip_orange': lambda S, cx, gy, **o: tulip(S, cx, gy, color='orange', **o),
        'tulip_white': lambda S, cx, gy, **o: tulip(S, cx, gy, color='white', **o),
        'tulip_pink': lambda S, cx, gy, **o: tulip(S, cx, gy, color='pink', **o),
        'allium': allium, 'lily_of_the_valley': lily_of_the_valley, 'sunflower': sunflower,
        'rose_bush': rose_bush,
        'wheat': lambda S, cx, gy, **o: crop_row(S, cx, gy, crop='wheat', **o),
        'carrots': lambda S, cx, gy, **o: crop_row(S, cx, gy, crop='carrot', **o),
        'potatoes': lambda S, cx, gy, **o: crop_row(S, cx, gy, crop='potato', **o),
        'beetroots': lambda S, cx, gy, **o: crop_row(S, cx, gy, crop='beet', **o),
        'pumpkin': pumpkin, 'melon': melon,
        'cactus': cactus, 'sugar_cane': sugar_cane, 'bamboo': bamboo, 'vines': vines_item, 'lily_pad': lily_pad,
        'pond': pond, 'kelp': kelp, 'coral': coral,
        'rock': rock, 'mossy_boulder': lambda S, cx, gy, **o: rock(S, cx, gy, mossy=True, **o),
        'coal_rock': lambda S, cx, gy, **o: rock(S, cx, gy, ore='coal', **o),
        'iron_rock': lambda S, cx, gy, **o: rock(S, cx, gy, ore='iron', **o),
        'copper_rock': lambda S, cx, gy, **o: rock(S, cx, gy, ore='copper', **o),
        'gold_rock': lambda S, cx, gy, **o: rock(S, cx, gy, ore='gold', **o),
        'redstone_rock': lambda S, cx, gy, **o: rock(S, cx, gy, ore='redstone', **o),
        'lapis_rock': lambda S, cx, gy, **o: rock(S, cx, gy, ore='lapis', **o),
        'emerald_rock': lambda S, cx, gy, **o: rock(S, cx, gy, ore='emerald', **o),
        'diamond_rock': lambda S, cx, gy, **o: rock(S, cx, gy, ore='diamond', base='deepslate', **o),
        'log': log, 'stump': stump,
        'campfire': campfire, 'soul_campfire': lambda S, cx, gy, **o: campfire(S, cx, gy, soul=True, **o),
        'torch': torch, 'soul_torch': lambda S, cx, gy, **o: torch(S, cx, gy, soul=True, **o),
        'lantern': lantern, 'soul_lantern': lambda S, cx, gy, **o: lantern(S, cx, gy, soul=True, **o),
        'hanging_lantern': lambda S, cx, gy, **o: lantern(S, cx, gy, hanging=True, **o),
        'sign': sign, 'hanging_sign': hanging_sign, 'fence': fence, 'fence_gate': fence_gate,
        'hay_bale': hay_bale, 'barrel': barrel, 'crate': crate, 'chest': chest, 'beehive': beehive,
        'lava_pool': lava_pool, 'snow_drift': snow_drift, 'ice_spikes': ice_spikes,
        'red_mushroom': lambda S, cx, gy, **o: mushrooms(S, cx, gy, kind='red', **o),
        'brown_mushroom': lambda S, cx, gy, **o: mushrooms(S, cx, gy, kind='brown', **o),
    })


def build(S, name, cx, gy, **opts):
    """Draw `name` into S with its base on (cx, gy); then ambient occlusion where it meets the ground: the
    pixels of its lowest rows that rest on the ground line turn a step darker (contact shadow)."""
    n0 = len(S.parts)
    info = CATALOG[name](S, cx, gy, **opts) or {}
    new = [p for p in S.parts[n0:] if p['shade'] is None and p['lay']]
    allpx = set().union(*[set(p['lay']) for p in new]) if new else set()
    for p in new:
        lay = p['lay']
        for (x, y), c in list(lay.items()):
            if gy - S.kv(0, 1) <= y <= gy and (x, y + 1) not in allpx and c not in EMISSIVE:
                lay[(x, y)] = darker(c)
    return info


def parts(name, k=1, season='summer', seed=0, ground=True, size='m', **opts):
    """The drawable as modes.Parts items (name, sprite, x, y), bottom -> top, positions relative to the tight
    bounding box of all parts."""
    if name in BIOMES:
        return scatter(opts.get('width', 160), opts.get('height', 80), name, seed, k)
    S = Scene(k, seed, season, ground)
    info = build(S, name, 0, 0, size=size, **opts)
    if ground and info.get('ground'):
        pts = [q for p in S.parts for q in (p['shade'] or p['lay'])]
        x0, y0, x1, _ = bbox(pts)
        go = dict(info.get('ground_opts', {}))
        if -y0 < S.u(22):                                   # small things stand on a small patch
            go.setdefault('back', S.u(1))
            go.setdefault('front', S.u(2))
            go.setdefault('depth', S.kv(2, 4))
            m = S.u(1)
        else:
            m = S.u(2)
        ground_patch(S, x0 - m, x1 + m, 0, info['ground'], **go)
    items, _ = S.finish()
    return items


def size_of(items):
    return (max(it['x'] + it['sprite'].width for it in items), max(it['y'] + it['sprite'].height for it in items))


def render(name, k=1, **opts):
    """The drawable as one tight RGBA image (parts composed in order)."""
    items = parts(name, k, **opts)
    W, H = size_of(items)
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    compose(items, img)
    bb = img.getbbox()
    return img.crop(bb) if bb else img


# ------------------------------------------------------------------ scatter: biome ground strips
# rows: (depth 0 back .. 1 front, gap between things in GUI px, skip chance, [(name, weight, opts)])
BIOMES = {
    'forest': {'ground': 'grass', 'season': 'summer', 'litter': None, 'rows': [
        (0.0, -9, 0.0, [('oak', 3, {}), ('birch', 2, {}), ('dark_oak', 1, {'size': 's'}), ('oak', 1, {'size': 's'})]),
        (0.45, 3, 0.15, [('bush', 3, {}), ('fern', 3, {}), ('log', 1, {'size': 's'}), ('stump', 1, {}),
                         ('brown_mushroom', 1, {}), ('mossy_boulder', 1, {'size': 's'}), ('berry_bush', 1, {})]),
        (0.9, 2, 0.25, [('tall_grass', 4, {'size': 's'}), ('fern', 1, {'size': 's'}), ('poppy', 1, {}),
                        ('dandelion', 1, {}), ('lily_of_the_valley', 1, {}), ('red_mushroom', 1, {})])]},
    'plains': {'ground': 'grass', 'season': 'summer', 'litter': None, 'rows': [
        (0.0, 26, 0.3, [('oak', 2, {}), ('bush', 1, {}), ('oak', 1, {'size': 's'})]),
        (0.45, 4, 0.3, [('tall_grass', 3, {}), ('sunflower', 2, {}), ('rock', 1, {'size': 's'}), ('bush', 1, {'size': 's'}),
                        ('rose_bush', 1, {})]),
        (0.9, 2, 0.2, [('tall_grass', 3, {'size': 's'}), ('poppy', 2, {}), ('dandelion', 2, {}), ('cornflower', 2, {}),
                       ('tulip_red', 1, {}), ('tulip_orange', 1, {}), ('tulip_white', 1, {}), ('allium', 1, {})])]},
    'desert': {'ground': 'sand', 'season': 'summer', 'litter': 'pebbles', 'oasis': True, 'rows': [
        (0.0, 18, 0.3, [('cactus', 3, {}), ('dead_bush', 1, {}), ('rock', 1, {'size': 's'})]),
        (0.45, 10, 0.3, [('cactus', 2, {'size': 's'}), ('dead_bush', 3, {}), ('rock', 1, {'size': 's'})]),
        (0.9, 8, 0.45, [('dead_bush', 3, {}), ('cactus', 1, {'size': 's', 'arms': False})])]},
    'snowy': {'ground': 'snow', 'season': 'winter', 'litter': None, 'rows': [
        (0.0, -3, 0.0, [('spruce', 4, {}), ('spruce', 2, {'size': 's'}), ('ice_spikes', 1, {'size': 's'})]),
        (0.45, 6, 0.25, [('snow_drift', 2, {'size': 's'}), ('rock', 1, {'size': 's'}), ('bush', 1, {'size': 's'}),
                         ('spruce', 1, {'size': 's'})]),
        (0.9, 6, 0.4, [('snow_drift', 1, {'size': 's'}), ('dead_bush', 1, {}), ('stump', 1, {'kind': 'spruce'})])]},
    'swamp': {'ground': 'swamp', 'season': 'summer', 'litter': None, 'puddles': True, 'rows': [
        (0.0, 3, 0.0, [('swamp_oak', 4, {}), ('swamp_oak', 1, {'size': 's'})]),
        (0.45, 5, 0.3, [('sugar_cane', 2, {'size': 's'}), ('brown_mushroom', 1, {}), ('fern', 2, {}),
                        ('giant_brown_mushroom', 1, {'size': 's'}), ('log', 1, {'size': 's'})]),
        (0.9, 3, 0.35, [('blue_orchid', 3, {}), ('tall_grass', 2, {'size': 's', 'R': None}), ('red_mushroom', 1, {}),
                        ('fern', 1, {'size': 's'})])]},
    'cherry_grove': {'ground': 'grass', 'season': 'spring', 'litter': 'petals', 'rows': [
        (0.0, -4, 0.0, [('cherry', 4, {}), ('cherry', 1, {'size': 's'}), ('birch', 1, {'size': 's'})]),
        (0.45, 4, 0.25, [('bush', 1, {}), ('allium', 2, {}), ('tulip_pink', 2, {}), ('fern', 1, {}),
                         ('tall_grass', 2, {'size': 's'})]),
        (0.9, 2, 0.25, [('tulip_pink', 2, {}), ('tulip_white', 1, {}), ('allium', 1, {}), ('lily_of_the_valley', 1, {}),
                        ('tall_grass', 2, {'size': 's'})])]},
}
_EXT = {}


def extent(name, k=1, season='summer', **opts):
    """(left, top, right) of a drawable relative to its base point, without ground (cached)."""
    key = (name, k, season, tuple(sorted((a, str(b)) for a, b in opts.items())))
    if key not in _EXT:
        S = Scene(k, 0, season, False)
        build(S, name, 0, 0, **opts)
        pts = [q for p in S.parts for q in p['lay']]
        x0, y0, x1, _ = bbox(pts)
        _EXT[key] = (x0, y0, x1)
    return _EXT[key]


def ground_strip(S, W, ytop, yface, H, kind, seed=0, name='ground'):
    """The ground of a scatter: a top face seen from slightly above (rows ytop..yface-1, the far edge lit,
    clusters by material) over a front face of soil (the top material hanging over its edge, stones in the
    soil, darker toward the bottom), straight ends at the canvas edges."""
    kind = ground_kind(S, kind)
    Rs, Rf = GROUND[kind]
    lay = S.lay(name, -100)
    rnd = S.rnd('strip', kind)
    top = rect(0, ytop, W - 1, yface - 1)
    surface(S, lay, top, kind, seed=seed)
    for x in range(W):
        lay[(x, ytop - 1)] = Rs[SH]                                     # the far edge (outline, lit side)
    face = rect(0, yface, W - 1, H - 1)
    for (x, y) in face:
        j = y - yface
        lay[(x, y)] = Rf[BS if j < (H - yface) * 0.6 else DK]
    for x in range(W):
        drip = S.kv(1, 2) + (rnd.random() < 0.35) * S.kv(1, 2)
        for j in range(drip):
            lay[(x, yface + j)] = Rs[DK] if j == drip - 1 else Rs[BS]
    for (x, y) in sorted(face):
        if y - yface >= S.kv(3, 5) and rnd.random() < S.kv(0.04, 0.03) and (x + 1, y) in face:
            lay[(x, y)] = Rf[LT]
            lay[(x + 1, y)] = Rf[SH]
    return top


def litter(S, top, kind, seed=0):
    """Small things lying on the ground: pink petals (cherry grove), fallen leaves, pebbles - 2-4 px clusters
    lit on top."""
    lay = S.lay('litter', -90)
    rnd = S.rnd('litter', kind, seed)
    pts = sorted(top)
    rnd.shuffle(pts)
    n = int(len(pts) * S.kv(0.012, 0.008))
    for (x, y) in pts[:n]:
        if kind == 'petals':
            R = PINK_PETALS                                                                          # noqa
            for (a, b), t in (((0, 0), LT), ((1, 0), LT), ((0, 1), BS), ((1, 1), BS)) if S.k == 1 else \
                    (((0, 0), HI), ((1, 0), LT), ((2, 0), BS), ((0, 1), LT), ((1, 1), BS), ((2, 1), DK)):
                if (x + a, y + b) in top:
                    lay[(x + a, y + b)] = R[t]
        elif kind == 'leaves':
            R = rnd.choice((OAK_LEAF_AUTUMN, LEAF_RED, LEAF_YELLOW))                                 # noqa
            for (a, b), t in (((0, 0), LT), ((1, 0), DK)) if S.k == 1 else (((0, 0), LT), ((1, 0), BS), ((1, 1), DK), ((2, 1), DK)):
                if (x + a, y + b) in top:
                    lay[(x + a, y + b)] = R[t]
        elif kind == 'pebbles':
            R = SANDSTONE                                                                            # noqa
            for (a, b), t in (((0, 0), LT), ((1, 0), DK)) if S.k == 1 else (((0, 0), LT), ((1, 0), BS), ((0, 1), BS), ((1, 1), SH)):
                if (x + a, y + b) in top:
                    lay[(x + a, y + b)] = R[t]


def puddle(S, cx, gy, rx, ry, seed=0, pads=1):
    """A swamp pool on the ground: murky water with a muddy bank, a lily pad or two."""
    k = S.k
    rnd = S.rnd('puddle', cx, seed)
    wm = water_patch(S, cx, gy, rx, ry, R=WATER_SWAMP, name='pool', z=-80, ripples=1, seed=cx, shore=MUD)   # noqa
    if pads:
        lay = S.lay('lily_pads', -79)
        for i in range(pads):
            px_ = cx + rnd.uniform(-rx * 0.5, rx * 0.4)
            py_ = gy - ry + rnd.uniform(-ry * 0.2, ry * 0.3)
            pm = set()
            for (x, y) in disc(px_, py_, S.kv(2.2, 4.2), S.kv(1.1, 2.0)):
                if (x, y) in wm and not (x > px_ and abs(y + 0.5 - py_) < (x + 0.5 - px_) * 0.4):
                    lay[(x, y)] = LILY_PAD[LT if x < px_ - 1 else BS if x < px_ + 1 else DK]       # noqa
                    pm.add((x, y))
            outline(lay, pm, LILY_PAD)                                                              # noqa
    return wm


def layout(width=160, height=80, biome='forest', seed=0, season=None):
    """The arrangement of a scatter in GUI units (density-independent, so k=1 and HD show the same scene):
    [(name, opts, cx, gy)] sorted back -> front, plus the pools [(kind, cx, gy, rx, ry, pads)]."""
    B = BIOMES[biome]
    season = season or B['season']
    rnd = random.Random(_crc('scatter', biome, seed))
    yface = height - 6
    ytop = height - 24
    placed, pools = [], []
    if B.get('puddles'):
        x = rnd.randint(8, 30)
        while x < width - 20:
            rx = rnd.randint(10, 18)
            pools.append(('puddle', x + rx, ytop + rnd.randint(9, 13), rx, rnd.uniform(2.5, 3.5), rnd.randint(0, 2)))
            x += 2 * rx + rnd.randint(25, 50)
    if B.get('oasis') and width >= 120:
        rx = 16
        ox = width - rx - rnd.randint(6, 16)
        pools.append(('oasis', ox, ytop + 12, rx, 3.5, 0))
        placed.append(('palm', {}, ox - 10, ytop + 5))
        placed.append(('palm', {'size': 's'}, ox + 12, ytop + 4))
        placed.append(('sugar_cane', {'size': 's'}, ox - rx - 3, ytop + 11))
    for (depth, gap, skip, cands) in B['rows']:
        gy_row = ytop + 3 + int(depth * (yface - ytop - 7))
        x = rnd.randint(-4, 6)
        guard = 0
        row = []
        while x < width + 4 and guard < 200:
            guard += 1
            tot = sum(c[1] for c in cands)
            r = rnd.uniform(0, tot)
            for name, wt, opts in cands:
                r -= wt
                if r <= 0:
                    break
            opts = {a: b for a, b in opts.items() if b is not None}
            x0, y0, x1 = extent(name, 1, season, **opts)
            cx = x - x0
            gy = gy_row + rnd.randint(-1, 1)
            near_palm = any(p[0] == 'palm' and abs(p[2] - cx) < 20 for p in placed)
            if not near_palm and (rnd.random() >= skip or (depth == 0 and not row and x > width * 0.4)) \
                    and gy + y0 > -12:
                row.append((name, opts, cx, gy))
            x = cx + x1 + gap + rnd.randint(0, 4)
        placed += row
    placed.sort(key=lambda p: (p[3], p[2]))
    return placed, pools, ytop, yface


def scatter(width=160, height=80, biome='forest', seed=0, k=1, season=None):
    """A ground strip with a natural arrangement of the kit's things for a biome - forest, plains, desert,
    snowy, swamp, cherry_grove - as modes.Parts items on a canvas of (width * k) x (height * k): the ground
    (+ litter, pools), then every thing back to front (each thing's parts prefixed 'name_i/'), their ground
    shadows on what is behind them. Three rows: tall things at the back, mid-size in the middle, small ones in
    front; spacing from each thing's measured width; a seeded random choice by weight. The arrangement is
    planned in GUI units (layout()), so k=1 and HD draw the same scene."""
    B = BIOMES[biome]
    season = season or B['season']
    S = Scene(k, seed, season, ground=False)
    W, H = width * k, height * k
    placed, pools, ytop, yface = layout(width, height, biome, seed, season)
    top = ground_strip(S, W, ytop * k, yface * k, H, B['ground'], seed)
    if B.get('litter') or season == 'autumn':
        litter(S, top, 'leaves' if season == 'autumn' else B['litter'], seed)
    for (kind, cx, gy, rx, ry, pads) in pools:
        if kind == 'puddle':
            puddle(S, cx * k, gy * k, rx * k, ry * k, seed=cx, pads=pads)
        else:
            water_patch(S, cx * k, gy * k, rx * k, ry * k, name='oasis', z=-80, ripples=1, seed=seed, shore=SAND)  # noqa
    for i, (name, opts, cx, gy) in enumerate(placed):
        S.prefix = f'{name}_{i + 1}/'
        S.zbase = 1000 * (i + 1)
        build(S, name, cx * k, gy * k, **opts)
    S.prefix, S.zbase = '', 0
    items, _ = S.finish(size=(W, H))
    return items


_register()


# ------------------------------------------------------------------ chart, CLI
BG = (78, 84, 94, 255)
BG2 = (66, 71, 80, 255)
INK = (232, 228, 216, 255)
GROUPS = [
    ('trees (summer)', ['oak', 'birch', 'spruce', 'jungle', 'acacia', 'dark_oak', 'cherry', 'palm', 'dead_tree',
                        'swamp_oak', 'giant_red_mushroom', 'giant_brown_mushroom']),
    ('plants and flowers', ['bush', 'berry_bush', 'rose_bush', 'tall_grass', 'fern', 'dead_bush', 'poppy', 'dandelion',
                            'cornflower', 'blue_orchid', 'tulip_red', 'tulip_orange', 'tulip_white', 'tulip_pink',
                            'allium', 'lily_of_the_valley', 'sunflower', 'red_mushroom', 'brown_mushroom']),
    ('crops', ['wheat', 'carrots', 'potatoes', 'beetroots', 'pumpkin', 'melon']),
    ('desert and water', ['cactus', 'sugar_cane', 'bamboo', 'vines', 'lily_pad', 'pond', 'kelp', 'coral']),
    ('rocks and wood', ['rock', 'mossy_boulder', 'coal_rock', 'iron_rock', 'copper_rock', 'gold_rock', 'redstone_rock',
                        'lapis_rock', 'emerald_rock', 'diamond_rock', 'log', 'stump']),
    ('fire, light, signs, fences', ['campfire', 'soul_campfire', 'torch', 'soul_torch', 'lantern', 'soul_lantern',
                                    'hanging_lantern', 'sign', 'hanging_sign', 'fence', 'fence_gate']),
    ('props, lava, snow, ice', ['hay_bale', 'barrel', 'crate', 'chest', 'beehive', 'lava_pool', 'snow_drift',
                                'ice_spikes']),
]


def _label(img, x, y, text, c=INK):
    from pixfont import draw_text
    draw_text(img, x, y, text.replace('_', ' '), c)


def _cells(entries, z):
    """[(label, image)] -> [(label, enlarged image)]."""
    return [(label, im.resize((im.width * z, im.height * z), Image.NEAREST)) for label, im in entries]


def _flow(cells, maxw):
    """Rows of cells no wider than maxw; every cell in a row gets the row's height and its picture stands on
    the row's base line (the ground lines line up)."""
    from pixfont import text_width
    rows, cur, w = [], [], 10
    for label, big in cells:
        cw = max(big.width, text_width(label.replace('_', ' ')) + 4) + 16
        if w + cw + 10 > maxw and cur:
            rows.append(cur)
            cur, w = [], 10
        cur.append((label, big, cw))
        w += cw + 10
    if cur:
        rows.append(cur)
    out = []
    for r in rows:
        hh = max(big.height for _, big, _ in r)
        row = []
        for label, big, cw in r:
            cell = Image.new('RGBA', (cw, hh + 30), BG2)
            cell.alpha_composite(big, ((cw - big.width) // 2, 8 + hh - big.height))
            _label(cell, 8, hh + 14, label)
            row.append(cell)
        out.append(row)
    return out


def chart(path, hd=False):
    """Everything in the catalog (grouped, labelled, enlarged x4 / HD x3) on a neutral background, the four
    seasons of an oak, and one scatter() per biome."""
    k = 2 if hd else 1
    z = 3 if hd else 4
    maxw = 2600 if hd else 2200
    blocks = []
    for title, names in GROUPS:
        blocks.append((title, _flow(_cells([(n, render(n, k)) for n in names], z), maxw)))
    seasons = [(f'oak - {s}', render('oak', k, season=s)) for s in SEASONS]
    seasons += [(f'cherry - {s}', render('cherry', k, season=s)) for s in ('spring', 'autumn', 'winter')]
    seasons += [('spruce - winter', render('spruce', k, season='winter')),
                ('birch - autumn', render('birch', k, season='autumn'))]
    blocks.insert(1, ('the four seasons of an oak (+ cherry, spruce, birch)', _flow(_cells(seasons, z), maxw)))
    sw, sh = 160, 80
    sc = []
    for b in BIOMES:
        items = scatter(sw, sh, b, seed=3, k=k)
        im = Image.new('RGBA', (sw * k, sh * k), (0, 0, 0, 0))
        compose(items, im)
        sc.append((f'scatter({sw}, {sh}, {b!r}, seed=3, k={k})', im))
    blocks.append(('scatter() per biome', _flow(_cells(sc, 2 if hd else 3), maxw)))
    W = max(sum(c.width + 10 for c in r) + 10 for _, rows in blocks for r in rows)
    H = 30 + sum(24 + sum(max(c.height for c in r) + 10 for r in rows) for _, rows in blocks) + 10
    img = Image.new('RGBA', (W, H), BG)
    n = len(CATALOG)
    _label(img, 10, 10, f'nature.py - {n} drawables + scatter() for {len(BIOMES)} biomes, '
           f'{"HD k=2, x3" if hd else "k=1, x4"}')
    y = 30
    for title, rows in blocks:
        _label(img, 10, y + 6, title)
        y += 24
        for r in rows:
            x = 10
            for c in r:
                img.alpha_composite(c, (x, y))
                x += c.width + 10
            y += max(c.height for c in r) + 10
    img.save(path)
    return img


def _opts(a):
    o = {}
    if '--no-ground' in a:
        o['ground'] = False
    for key in ('--season', '--seed', '--size', '--width', '--height', '--wood', '--kind', '--age', '--frame'):
        if key in a:
            v = a[a.index(key) + 1]
            o[key[2:]] = int(v) if v.lstrip('-').isdigit() else v
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
    elif cmd == 'scatter':
        o = _opts(a)
        w, h = o.pop('width', 160), o.pop('height', 80)
        items = scatter(w, h, a[1], seed=o.get('seed', 0), k=k, season=o.get('season'))
        im = Image.new('RGBA', (w * k, h * k), (0, 0, 0, 0))
        compose(items, im)
        im.save(a[2])
        print('scatter', a[1], '->', a[2], im.size, len(items), 'parts')
    elif cmd == 'parts':
        name, out = a[1], a[2]
        o = _opts(a)
        if name in BIOMES:
            w, h = o.pop('width', 160), o.pop('height', 80)
            items, size = scatter(w, h, name, seed=o.get('seed', 0), k=k, season=o.get('season')), (w * k, h * k)
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
            doc = (f.__doc__ or '').strip().splitlines()
            print(f'{n:22s} {doc[0] if doc else ""}')
        print(f'{"scatter":22s} scatter(width, height, biome, seed, k): ' + ', '.join(BIOMES))
    else:
        sys.exit(__doc__)
