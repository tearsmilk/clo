#!/usr/bin/env python3
"""Mode-select kit ("Навигатор"): the menu is a navigator's star chart; every game mode is an illustrated card
lying on it - a window into that mode's world filling its whole 4x4 area - with a ribbon carrying its name; a
gold compass rose between the cards points to both, a gold-framed plaque names the menu, an "uncharted"
plaque says what comes later. Used by gui_builder.py as `{"type": "modes", "part": ...}` layers; example
assets/examples/mode_select/, references/mode-select.md.

Every scene is BUILT FROM PARTS: blessed_parts() / farm_parts() return the parts bottom -> top (name, sprite,
x, y), compose() pastes them, a spec can move or hide any part ("scene": {"stall": {"x": 30}, "barn": null}),
and `python3 modes.py parts OUT/` exports every part as PNG + layers.json + a contact sheet + .aseprite with
one layer per part (layers.py); gui_builder.py --layers splits the whole menu the same way.

Blessed (Oneblock, PvP, fishing, quantum tech): the void with a violet nebula; a holy beam falls on ONE
floating grass block (dirt and roots hanging under it), a netherite sword stuck in it, a fishing line hanging
from a rod into the void, a glowing quantum cube on two orbits, far-off oneblocks of other players. Gilded
blackstone frame, wither-skull keystone, crimson ribbon.
Farm (resources, quests, levels, your own shop): a sunny afternoon; a square sun, blocky clouds, a far forest,
a red barn and a silo; a wheat field in perspective, a path to a market stall, a quest board with a "!", XP
orbs rising, big wheat stalks in front. Oak frame with leaves on the corners, wheat-sheaf keystone, green
ribbon.

Each scene has three depths (far: small, muted, hazy; middle: the main object; near: big saturated details)
and one light, the sun / beam from the top-left. Shading as in hub.py: five-tone ramps, selective outlines,
contact shadows, clusters, no gradients or dithering.

    python3 modes.py parts OUT_DIR       parts of both scenes: PNGs, layers.json, _sheet.png, .aseprite
"""
import json
import math
import os
import random
import sys

from PIL import Image

from kitchen import _r5, _px, _paint, rrect, edge_ring, raised, N4, WALNUT
from hub import GOLD, CREAM, slot_box, cast
from shading import pixel_perfect
import layers

# ------------------------------------------------------------------ palettes (outline, shadow, dark, base, light, hi)
CHART = _r5('#26304c', soft=1)          # the navigator's chart under everything
CHART2 = _r5('#1c2238', soft=1)         # plaques on the chart
BLACKSTONE = _r5('#3a3240', soft=1)
OAK = _r5('#b07a44', soft=1)
VOID = _r5('#272150', soft=0.3)
NEB = _r5('#8a46a0', soft=0.4)          # nebula
BEAM = _r5('#f0d27a', soft=0.3)
GRASS = _r5('#5fae3c', soft=0.5)
DIRT = _r5('#8c5c3a', soft=0.5)
NETH = _r5('#5e5078')                   # netherite with a purple sheen (metal: contrast)
QUANT = _r5('#38d8e8', soft=0.3)
SKY = _r5('#6fb6ea', soft=0.6)
FAR = _r5('#5c9484', soft=1)            # far forest: hazy blue-green
HILL = _r5('#4f9a48', soft=0.8)
FARMLAND = _r5('#6a4630', soft=0.8)
WHEAT = _r5('#e2b23e', soft=0.5)
STALK = _r5('#8aae3a', soft=0.5)
PATH = _r5('#b49668', soft=1)
RED = _r5('#c43c36', soft=0.6)
CARROT = _r5('#e8862a', soft=0.5)
BARN = _r5('#a63a30', soft=0.8)
SILO = _r5('#9aa0a8', soft=1)
XP = _r5('#9ae83a', soft=0.3)
WITHER = _r5('#4e4c56', soft=1)
LEAF = _r5('#4c9a3c', soft=0.6)
RIB_RED = _r5('#a8323a', soft=0.6)
RIB_GREEN = _r5('#3c8a48', soft=0.6)
PAPER = _r5('#e6d6b0', soft=1)

LIGHT_DIR = (-1, -1)                    # top-left
SHADOW_RAMPS = (WHEAT, FARMLAND, PATH, HILL, STALK, SKY, FAR)


def _put(im, x, y, c):
    if 0 <= x < im.width and 0 <= y < im.height and c is not None:
        im.putpixel((x, y), c)


def _outline(im, solid, lit_c, dark_c, lit_test=None):
    """Selective outline round a set of pixels: lit_c on the top / left side, dark_c elsewhere."""
    for p in edge_ring(solid):
        lit = lit_test(p) if lit_test else (((p[0], p[1] + 1) in solid or (p[0] + 1, p[1]) in solid)
                                            and not ((p[0], p[1] - 1) in solid or (p[0] - 1, p[1]) in solid))
        _put(im, p[0], p[1], lit_c if lit else dark_c)


def twinkle(im, x, y, core, arm):
    _put(im, x, y, core)
    for dx, dy in N4:
        _put(im, x + dx, y + dy, arm)


# ------------------------------------------------------------------ parts: build, override, compose
class Parts:
    """Collects the parts of one scene: each drawn on its own transparent canvas of the scene size, kept as a
    tight sprite + offset. shadow={'dx', 'dy', 'from_row'} casts the part's lower rows onto what is under
    it when composed (darker tone of the same ramp)."""

    def __init__(self, W, H):
        self.W, self.H, self.items = W, H, []

    def add(self, name, draw, shadow=None):
        im = Image.new('RGBA', (self.W, self.H), (0, 0, 0, 0))
        draw(im)
        bb = im.getbbox()
        if bb:
            it = {'name': name, 'sprite': im.crop(bb), 'x': bb[0], 'y': bb[1]}
            if shadow:
                it['shadow'] = shadow
            self.items.append(it)


def override(items, changes):
    """changes = {part: {"x": .., "y": .., "dx": .., "dy": ..} | null (hide)} from a spec's "scene"."""
    out = []
    for it in items:
        ch = (changes or {}).get(it['name'], {})
        if ch is None:
            continue
        it = dict(it)
        it['x'] = ch.get('x', it['x'] + ch.get('dx', 0))
        it['y'] = ch.get('y', it['y'] + ch.get('dy', 0))
        out.append(it)
    return out


def _darker(c):
    for r in SHADOW_RAMPS:
        if c in r:
            return r[max(1, r.index(c) - 2)]
    return c


def compose(items, img, ox=0, oy=0, clip=None, prefix=''):
    """Paste the parts in order at (ox + x, oy + y); clip = (x0, y0, x1, y1) keeps them inside a window. Each
    part is marked as its own layer for layers.py."""
    for it in items:
        sp = it['sprite']
        X, Y = ox + it['x'], oy + it['y']
        if clip:
            cx0, cy0, cx1, cy1 = clip
            a0, b0 = max(0, cx0 - X), max(0, cy0 - Y)
            a1, b1 = min(sp.width, cx1 + 1 - X), min(sp.height, cy1 + 1 - Y)
            if a1 <= a0 or b1 <= b0:
                continue
            sp, X, Y = sp.crop((a0, b0, a1, b1)), X + a0, Y + b0
        sh = it.get('shadow')
        if sh:
            spx, ipx = sp.load(), img.load()
            mask = {(x, y) for y in range(sp.height) for x in range(sp.width) if spx[x, y][3]}
            for (x, y) in mask:
                q = (x + sh['dx'], y + sh['dy'])
                if y >= sh.get('from_row', 0) and q not in mask:
                    gx, gy = X + q[0], Y + q[1]
                    if 0 <= gx < img.width and 0 <= gy < img.height and (not clip or (
                            clip[0] <= gx <= clip[2] and clip[1] <= gy <= clip[3])):
                        ipx[gx, gy] = _darker(ipx[gx, gy])
        img.alpha_composite(sp, (X, Y))
        layers.mark(prefix + it['name'])
    return img


# ------------------------------------------------------------------ shared objects
def iso_block(im, cx, top, a, side, top_ramp, side_ramp, fringe=True, outline=None, seed=11, lit_spot=None):
    """A block in 2:1 isometric: top diamond (rows 2, 6, ... 4a-2 px wide), lit left face, darker right face,
    an uneven fringe of the top material over the side material, lit / shadow front edge, selective
    outline. lit_spot = (dx, dy, rx, ry): a lighter patch on the top (a beam hitting it).
    Returns (solid, bottom y per column)."""
    diamond = set()
    for j in range(2 * a):
        k = j if j < a else 2 * a - 1 - j
        for x in range(cx - 2 * k - 2, cx + 2 * k + 2):
            diamond.add((x, top + j))
    out = {}
    col_top = {x: max(y for (xx, y) in diamond if xx == x) + 1 for x in range(cx - 2 * a, cx + 2 * a)}
    rnd = random.Random(seed)
    for (x, y) in diamond:
        c = top_ramp[3]
        if (x - 1, y) not in diamond or (x, y - 1) not in diamond:
            c = top_ramp[4]
        if lit_spot:
            dx, dy, rx, ry = lit_spot
            e = ((x - cx - dx) / rx) ** 2 + ((y - top - a - dy) / ry) ** 2
            c = top_ramp[5] if e < 0.3 else top_ramp[4] if e < 1 else c
        out[(x, y)] = c
    for x, y0 in col_top.items():
        lit = x < cx
        drip = 2 + (x * 7 % 5 == 0) + (x * 3 % 7 == 1) if fringe else 0
        for y in range(y0, y0 + side):
            r = top_ramp if y - y0 < drip else side_ramp
            out[(x, y)] = r[3 if lit else 2]
    for (x, y), c in sorted(out.items()):                  # clusters
        r_ = rnd.random()
        if c == top_ramp[3] and r_ < 0.1 and out.get((x + 1, y)) == top_ramp[3]:
            out[(x, y)] = out[(x + 1, y)] = top_ramp[2]
        elif c in (side_ramp[3], side_ramp[2]) and r_ < 0.09 and out.get((x, y + 1)) == c:
            out[(x, y)] = out[(x, y + 1)] = side_ramp[max(1, side_ramp.index(c) - 1)]
        elif c == side_ramp[3] and r_ < 0.06 and out.get((x + 1, y)) == c:
            out[(x, y)] = out[(x + 1, y)] = side_ramp[4]
    if cx - 1 in col_top:
        for y in range(col_top[cx - 1], col_top[cx - 1] + side):
            g = fringe and y - col_top[cx - 1] < 2
            out[(cx - 1, y)] = (top_ramp if g else side_ramp)[4]
            out[(cx, y)] = (top_ramp if g else side_ramp)[1]
    for p, c in out.items():
        _put(im, *p, c)
    solid = set(out)
    o_lit, o_dark = outline or (top_ramp[1], side_ramp[0])
    _outline(im, solid, o_lit, o_dark, lambda p: p[0] < cx and p[1] < top + a + 1)
    return solid, {x: y0 + side - 1 for x, y0 in col_top.items()}


def orb(im, x, y, ramp=None, trail=0):
    """Glowing orb (XP): 3x3 lit ball, a 1 px glow cross, an optional trail of dots below."""
    ramp = ramp or XP
    for dx in range(3):
        for dy in range(3):
            _put(im, x + dx, y + dy, ramp[5] if dx + dy == 0 else ramp[4] if dx + dy < 3 else ramp[2])
    for dx, dy in ((1, -1), (-1, 1), (3, 1), (1, 3)):
        _put(im, x + dx, y + dy, ramp[3] if dy < 1 or dx < 0 else ramp[1])
    for k in range(trail):
        _put(im, x + 1, y + 5 + k * 2, ramp[3 if k == 0 else 2])


def _mute(r):
    """A far-away version of a ramp: darker, toward the void."""
    return [r[0], r[0], r[1], r[1], r[2], r[3]]


# ------------------------------------------------------------------ Blessed: the void
def _nebula(x, y, W, H, bx, seed):
    n = (math.sin(x * 0.17 + 1.7 * math.sin(y * 0.13 + seed)) + 0.8 * math.sin(y * 0.27 - x * 0.1 + 2.0 + seed)
         + 0.5 * math.sin((x + 2 * y) * 0.12 + seed * 1.7))
    band = 1 - abs(y - H * 0.40) / (H * 0.55)
    near = max(0.0, 1 - abs(x - bx) / (W * 0.45))
    v = 0.32 * n + 0.9 * band + 0.75 * near - 0.55
    return 0 if v < 0.0 else 1 if v < 0.33 else 2 if v < 0.62 else 3 if v < 0.86 else 4


def blessed_parts(W=62, H=60, seed=3):
    P = Parts(W, H)
    bx, top = W // 2, 22
    tones = (VOID[1], VOID[2], VOID[3], NEB[2], NEB[3])

    def void(im):
        for y in range(H):
            for x in range(W):
                _put(im, x, y, tones[_nebula(x, y, W, H, bx, seed)])

    def stars(im):
        rnd = random.Random(seed)
        for _ in range(26):
            x, y = rnd.randrange(W), rnd.randrange(H)
            if _nebula(x, y, W, H, bx, seed) < 2:
                _put(im, x, y, CREAM[4] if rnd.random() < 0.6 else NEB[4])
        twinkle(im, 6, 7, CREAM[5], NEB[4])
        twinkle(im, W - 8, H - 13, CREAM[5], NEB[4])

    def far_islands(im):
        iso_block(im, 9, 12, 2, 3, _mute(GRASS), _mute(DIRT), fringe=False, outline=(VOID[1], VOID[0]))
        iso_block(im, W - 25, 5, 1, 2, _mute(GRASS), _mute(DIRT), fringe=False, outline=(VOID[1], VOID[0]))

    def god_rays(im):
        for side in (-1, 1):
            for y in range(0, top - 2):
                if y % 6 < 4:
                    _put(im, bx + side * (10 + y // 2), y, NEB[4])

    def beam(im):                                          # clean staircases: each band widens 1 px every n rows
        for y in range(0, top + 8):
            for x in range(bx - 14, bx + 14):
                d = abs(x - bx + 0.5)
                c = (CREAM[5] if d < 1 + y // 12 else BEAM[5] if d < 2 + y // 6 else BEAM[4] if d < 4 + y // 4
                     else NEB[4] if d < 5 + y // 4 else None)
                _put(im, x, y, c)

    def quantum(im):                                       # a glowing cube on two orbits = an atom
        qx, qy = bx + 21, top - 1
        for tilt, ph in ((0.5, 0), (-0.5, 140)):
            pts = []
            for t in range(0, 360, 3):
                ex, ey = 7 * math.cos(math.radians(t)), 2.4 * math.sin(math.radians(t))
                pts.append((round(qx + ex * math.cos(tilt) - ey * math.sin(tilt)),
                            round(qy + ex * math.sin(tilt) + ey * math.cos(tilt)), t))
            for x, y, t in pts:
                _put(im, x, y, QUANT[4] if math.sin(math.radians(t)) > 0 else QUANT[2])
            ex_, ey_, _ = pts[(ph // 3 + 20) % len(pts)]       # the electron
            for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
                _put(im, ex_ + dx, ey_ + dy, CREAM[5] if (dx, dy) == (0, 0) else QUANT[5])
        iso_block(im, qx, qy - 4, 2, 4, QUANT, QUANT, fringe=False, outline=(QUANT[1], QUANT[0]))
        _put(im, qx - 2, qy - 2, CREAM[5])
        twinkle(im, qx - 8, qy + 7, CREAM[5], QUANT[4])

    def island(im):
        solid, bottom = iso_block(im, bx, top, 7, 11, GRASS, DIRT, lit_spot=(0, 0, 9, 3.4))
        for x, yb in bottom.items():                       # dirt hanging under the floating block
            hang = (0, 1, 3, 2, 4, 1, 2, 5, 2, 1, 3, 0, 2, 4)[(x * 5) % 14] if abs(x - bx) < 12 else 0
            for k in range(1, hang + 1):
                _put(im, x, yb + k, DIRT[2 if x < bx else 1] if k < hang else DIRT[1])
            if hang:
                _put(im, x, yb + hang + 1, DIRT[0])
        for rx, ln in ((bx - 6, 7), (bx + 4, 9)):           # roots
            for k in range(1, ln):
                _put(im, rx + (k // 3) * (1 if rx > bx else -1), bottom[rx] + k, WALNUT[2] if k % 3 else WALNUT[3])
        for (dx, dy) in ((-3, 8), (2, 12), (-1, 16), (5, 10)):   # crumbs falling into the void
            _put(im, bx + dx, bottom[bx] + dy, DIRT[2])

    def sword(im):
        _sword(im, bx, top + 6, 13)

    def fishing(im):                                       # rod on the block, line into the void, bobber
        rx, ry = bx - 9, top + 5
        rod = [(rx - i, ry - i // 2) for i in range(12)]
        for i, p in enumerate(rod):                        # 2 px thick at the grip, lit top / dark underside
            _put(im, *p, WALNUT[4] if i % 4 == 1 else WALNUT[3])
            if i < 7:
                _put(im, p[0], p[1] + 1, WALNUT[1])
        _put(im, rx - 1, ry + 1, SILO[3])
        lx, ly = rod[-1]
        for y in range(ly + 1, H - 9):
            _put(im, lx - 1, y, CREAM[3] if y % 4 else CREAM[2])
        for (dx, dy, c) in ((-2, 0, RED[0]), (-1, 0, RED[4]), (0, 0, RED[3]), (1, 0, RED[0]),
                            (-2, 1, RED[0]), (-1, 1, CREAM[5]), (0, 1, CREAM[3]), (1, 1, RED[0]),
                            (-1, 2, RED[0]), (0, 2, RED[0])):
            _put(im, lx + dx, H - 9 + dy, c)

    P.add('void', void)
    P.add('stars', stars)
    P.add('far_islands', far_islands)
    P.add('god_rays', god_rays)
    P.add('beam', beam)
    P.add('quantum', quantum)
    P.add('island', island)
    P.add('sword', sword)
    P.add('fishing', fishing)
    return P.items


def _sword(im, x, y_in, length):
    """Netherite sword stuck point-down at (x, y_in): 3 px blade (lit left edge, base, dark right edge), gold
    guard with a gem, wrapped grip, pommel; outlined."""
    pts = {}
    gy = y_in - length
    for yy in range(gy + 1, y_in + 1):
        pts[(x - 1, yy)] = NETH[5] if yy < y_in - 3 else NETH[4]
        pts[(x, yy)] = NETH[4] if yy % 5 else NETH[3]
        pts[(x + 1, yy)] = NETH[2]
    for dx in range(-4, 5):
        pts[(x + dx, gy)] = GOLD[4] if dx < 0 else GOLD[3]
        pts[(x + dx, gy - 1)] = GOLD[5] if dx < 0 else GOLD[4]
    pts[(x, gy)] = RED[4]
    pts[(x, gy - 1)] = RED[5]
    for yy in range(gy - 6, gy - 1):
        pts[(x, yy)] = WALNUT[3] if yy % 2 else WALNUT[4]
        pts[(x + 1, yy)] = WALNUT[2] if yy % 2 else WALNUT[1]
    for (dx, dy, c) in ((0, -7, GOLD[5]), (1, -7, GOLD[3]), (0, -8, GOLD[4]), (1, -8, GOLD[2])):
        pts[(x + dx, gy + dy)] = c
    for p, c in pts.items():
        _put(im, *p, c)
    for p in edge_ring(set(pts)):
        if p[1] <= y_in:
            _put(im, *p, NETH[0])


# ------------------------------------------------------------------ Farm: a sunny afternoon
def farm_parts(W=62, H=60, seed=5):
    P = Parts(W, H)
    hz = 24
    vpx = W * 0.40

    def sky(im):
        for y in range(hz + 1):
            c = SKY[3] if y < 7 else SKY[4] if y < 17 else SKY[5]
            for x in range(W):
                _put(im, x, y, c)

    def sun(im):                                           # square sun + its glow ring
        for dx in range(-1, 8):
            for dy in range(-1, 8):
                ring = dx in (-1, 7) or dy in (-1, 7)
                if ring and (dx, dy) in ((-1, -1), (7, -1), (-1, 7), (7, 7)):
                    continue
                _put(im, 4 + dx, 3 + dy, SKY[5] if ring else CREAM[5] if 1 <= dx <= 5 and 1 <= dy <= 5
                     else WHEAT[5])

    def clouds(im):                                        # blocky: lit top, shaded bottom
        for (cx, cy, w) in ((20, 5, 12), (42, 9, 9), (55, 4, 6)):
            for dx in range(w):
                _put(im, cx + dx, cy, CREAM[5])
                _put(im, cx + dx, cy + 1, CREAM[4])
                _put(im, cx + dx, cy + 2, SKY[4] if dx in (0, w - 1) else CREAM[3])
            for dx in range(2, w - 3):
                _put(im, cx + dx, cy - 1, CREAM[5])

    def forest(im):                                        # far forest: blocky canopies in haze
        for x in range(W):
            t = (x // 5) % 4
            hgt = (4, 6, 3, 5)[t] + ((x // 5) % 3 == 1)
            for y in range(hz - hgt, hz + 1):
                _put(im, x, y, FAR[4] if y == hz - hgt else FAR[3] if y < hz - 1 else FAR[2])

    def meadow(im):
        for x in range(W):
            _put(im, x, hz, HILL[4])
            _put(im, x, hz + 1, HILL[3])

    def field(im):                                         # furrows radiating from a vanishing point
        for y in range(hz + 2, H):
            d = y - hz
            for x in range(W):
                s = (x - vpx) / (d + 2.5)
                k = math.floor(s * 2.6)
                if d < 4:
                    c = WHEAT[4] if k % 2 == 0 else WHEAT[3]      # haze: the far field melts into one tone
                elif k % 2 == 0:
                    fx = s * 2.6 - k
                    c = WHEAT[4] if fx < 0.25 else WHEAT[2] if fx > 0.8 else WHEAT[3]
                    if (y * 3 + int(fx * 7)) % 5 == 0 and d > 8:
                        c = WHEAT[5]
                else:
                    c = FARMLAND[2] if d < 14 else FARMLAND[1]
                _put(im, x, y, c)

    def path(im):                                          # to the stall, in perspective
        for y in range(hz + 3, H):
            d = y - hz
            cxp, half = 47 - (d - 3) * 0.55, 1 + d * 0.16
            for x in range(round(cxp - half), round(cxp + half) + 1):
                rut = half * 0.3 < abs(x - cxp) < half * 0.5
                _put(im, x, y, PATH[4] if x == round(cxp - half) else PATH[2] if rut else PATH[3])

    P.add('sky', sky)
    P.add('sun', sun)
    P.add('clouds', clouds)
    P.add('forest', forest)
    P.add('barn', lambda im: _barn(im, 7, hz - 12))
    P.add('meadow', meadow)
    P.add('field', field)
    P.add('path', path)
    P.add('stall', lambda im: _stall(im, 40, hz - 12), shadow={'dx': 2, 'dy': 1, 'from_row': 14})
    P.add('quest_board', lambda im: _quest_board(im, 5, hz + 4))
    P.add('xp', lambda im: [orb(im, x, y, trail=t) for (x, y, t) in ((23, hz - 3, 2), (31, hz + 3, 2),
                                                                    (17, hz + 10, 1))])
    P.add('wheat_front', lambda im: _wheat_front(im, W, H, seed))
    return P.items


def _wheat_front(im, W, H, seed):
    """Big wheat stalks along the bottom edge (near depth: bigger, brighter), ears with grains and awns."""
    rnd = random.Random(seed)
    for x in range(1, W, 3):
        hgt = 8 + rnd.randint(0, 4)
        lean = rnd.choice((0, 0, 1))
        base = H - 1
        for k in range(hgt - 4):
            _put(im, x + (lean if k > hgt // 2 else 0), base - k, STALK[3] if k % 3 else STALK[4])
        ex, ey = x + lean, base - hgt + 1
        for j in range(5):
            _put(im, ex, ey + j, WHEAT[5] if j % 2 == 0 else WHEAT[4])
            _put(im, ex + 1, ey + j, WHEAT[3] if j % 2 == 0 else WHEAT[2])
        _put(im, ex, ey - 1, WHEAT[5])
        _put(im, ex - 1, ey - 2, WHEAT[4])
        _put(im, ex + 2, ey - 1, WHEAT[4])


def _barn(im, x, y):
    """Small red barn with a white X door and trim, a grey silo; far, so outlined in the haze tones."""
    pts = {}
    for j in range(6):                                       # gable roof
        for i in range(7 - j, 8 + j):
            pts[(x + i, y + j)] = BARN[2] if i > 7 else BARN[3]
    for j in range(6, 13):                                   # front wall
        for i in range(1, 14):
            pts[(x + i, y + j)] = BARN[3] if i < 10 else BARN[2]
    for j in range(8, 13):                                   # door with a white X
        for i in range(5, 10):
            on = (i - 5) == (j - 8) or (i - 5) == 4 - (j - 8) or i in (5, 9) or j == 8
            pts[(x + i, y + j)] = CREAM[4] if on else BARN[1]
    for j in range(6):
        pts[(x + 7 - j, y + j)] = CREAM[4]
        pts[(x + 7 + j, y + j)] = CREAM[3]
    pts[(x + 7, y + 3)] = BARN[1]                            # hay-loft window
    for j in range(1, 13):                                   # silo
        for i in range(15, 19):
            pts[(x + i, y + j)] = SILO[4] if i == 15 else SILO[3] if i < 18 else SILO[2]
    for i in range(15, 19):
        pts[(x + i, y)] = SILO[4]
    for p, c in pts.items():
        _put(im, *p, c)
    _outline(im, set(pts), FAR[1], FAR[0])


def _stall(im, x, y):
    """Market stall 20 px wide: posts, striped awning (lit top, scalloped edge), shade under it, crates of
    apples, carrots and bread on the counter, a hanging coin sign."""
    pts = {}
    for j in range(5):                                       # awning
        for i in range(-1 + (j == 0), 21 - (j == 0)):
            r = RED if ((i + 1) // 3) % 2 == 0 else CREAM
            pts[(x + i, y + j)] = r[5] if j == 0 else r[4] if j == 1 else r[3] if j < 4 else r[2]
    for i in range(-1, 21):                                  # scalloped edge
        if (i + 1) % 3 != 2:
            pts[(x + i, y + 5)] = (RED if ((i + 1) // 3) % 2 == 0 else CREAM)[2]
    for j in range(5, 20):                                   # posts
        pts[(x, y + j)] = WALNUT[4]
        pts[(x + 19, y + j)] = WALNUT[2]
    for j in range(6, 12):                                   # shade under the awning, back wall
        for i in range(1, 19):
            pts[(x + i, y + j)] = WALNUT[1] if j < 8 else WALNUT[2]
    for (i0, rr) in ((2, RED), (7, CARROT), (12, WHEAT)):   # crates of goods
        for i in range(i0, i0 + 5):
            pts[(x + i, y + 10)] = rr[4] if (i - i0) % 2 == 0 else rr[3]
            pts[(x + i, y + 11)] = rr[3] if (i - i0) % 2 == 0 else rr[2]
            pts[(x + i, y + 12)] = WALNUT[4]
            pts[(x + i, y + 13)] = WALNUT[3]
    for j in range(14, 20):                                  # counter front: planks
        for i in range(1, 19):
            pts[(x + i, y + j)] = WALNUT[4] if j == 14 else WALNUT[3] if (i % 6) else WALNUT[2]
    for (dx, dy, c) in ((16, 6, WALNUT[3]), (16, 7, GOLD[4]), (17, 7, GOLD[3]), (16, 8, GOLD[3]),
                        (17, 8, GOLD[2])):                    # hanging coin sign
        pts[(x + dx, y + dy)] = c
    for p, c in pts.items():
        _put(im, *p, c)
    _outline(im, set(pts), WALNUT[1], WALNUT[0])


def _quest_board(im, x, y):
    """Quest board: two posts, a board with two pinned notes, a yellow "!" floating above."""
    pts = {}
    for j in range(0, 13):
        pts[(x + 1, y + j)] = WALNUT[3]
        pts[(x + 9, y + j)] = WALNUT[2]
    for j in range(1, 8):
        for i in range(0, 11):
            pts[(x + i, y + j)] = OAK[4] if j == 1 else OAK[3] if i < 9 else OAK[2]
    for (i0, j0) in ((2, 3), (6, 2)):
        for i in range(3):
            for j in range(4):
                pts[(x + i0 + i, y + j0 + j)] = PAPER[4] if j == 0 or i == 0 else PAPER[3]
        pts[(x + i0 + 1, y + j0)] = RED[4]
    for p, c in pts.items():
        _put(im, *p, c)
    _outline(im, set(pts), WALNUT[1], WALNUT[0])
    ex, ey = x + 5, y - 9
    mark = {(ex + i, ey + j) for i in (0, 1) for j in list(range(5)) + [6]}
    for (mx, my) in mark:
        _put(im, mx, my, WHEAT[5] if mx == ex else WHEAT[3])
    _outline(im, mark, WALNUT[1], WALNUT[0])


SCENES = {'blessed': blessed_parts, 'farm': farm_parts}


# ------------------------------------------------------------------ the card, the ribbon, the keystones
CARDS = {
    'blessed': dict(base=BLACKSTONE, trim=GOLD, ribbon=RIB_RED, letters='gold'),
    'farm': dict(base=OAK, trim=WALNUT, ribbon=RIB_GREEN, letters='gold'),
}


def gate(img, ox, oy, c, r, w, h, kind, name=None, seed=1, scene=None):
    """One mode card over slots (c, r, w, h): a 2 px thick card with its shadow on the chart, the scene built
    from its parts filling the card (scene = per-part overrides), a 3 px frame (dark inner line, trim
    fillet lit top-left), corner pieces, a keystone on top; a ribbon with the name across the bottom only
    if `name` is given (the user's menu has none: the picture and the tooltip name the mode)."""
    spec = CARDS[kind]
    base, trim = spec['base'], spec['trim']
    x0, y0, x1, y1 = slot_box(ox, oy, c, r, w, h)
    raised(img, rrect(x0 + 1, y0 + 1, x1 - 1, y1 - 3, 2), 2, base, shadow_off=(2, 2), shadow_ramp=CHART, seed=seed)
    layers.mark(f'{kind}/card')
    sx0, sy0, sx1, sy1 = x0 + 5, y0 + 5, x1 - 5, y1 - 7
    items = override(SCENES[kind](sx1 - sx0 + 1, sy1 - sy0 + 1, seed), scene)
    compose(items, img, sx0, sy0, clip=(sx0, sy0, sx1, sy1), prefix=f'{kind}/')
    for x in range(sx0 - 1, sx1 + 2):                        # inner dark line round the picture
        _px(img, x, sy0 - 1, base[0])
        _px(img, x, sy1 + 1, base[0])
    for y in range(sy0 - 1, sy1 + 2):
        _px(img, sx0 - 1, y, base[0])
        _px(img, sx1 + 1, y, base[0])
    for x in range(sx0 - 2, sx1 + 3):                        # trim fillet: lit top / left, dark bottom / right
        _px(img, x, sy0 - 2, trim[4])
        _px(img, x, sy1 + 2, trim[2])
    for y in range(sy0 - 2, sy1 + 3):
        _px(img, sx0 - 2, y, trim[4] if y < sy1 + 2 else trim[2])
        _px(img, sx1 + 2, y, trim[2] if y > sy0 - 2 else trim[4])
    _px(img, sx0 - 2, sy0 - 2, trim[5])
    layers.mark(f'{kind}/frame')
    corners = ((sx0 - 2, sy0 - 2), (sx1 + 2, sy0 - 2), (sx0 - 2, sy1 + 2), (sx1 + 2, sy1 + 2))
    if kind == 'blessed':
        for (cx_, cy_) in corners:
            _boss(img, cx_, cy_)
        layers.mark(f'{kind}/corners')
        _skull(img, (x0 + x1 + 1) // 2, y0 - 3)
    else:
        for i, (cx_, cy_) in enumerate(corners):
            _leaves(img, cx_, cy_, 1 if i % 2 == 0 else -1, seed + i)
        layers.mark(f'{kind}/corners')
        _sheaf(img, (x0 + x1 + 1) // 2, y0 - 4)
    layers.mark(f'{kind}/keystone')
    if name:
        _ribbon(img, (x0 + x1 + 1) // 2, sy1 - 8, name, spec['ribbon'], spec['letters'])
    pixel_perfect(img, only={base[0], spec['ribbon'][0], WALNUT[0], WALNUT[1], NETH[0], LEAF[0], LEAF[1], DIRT[0],
                             GRASS[1], WITHER[0], GOLD[0], GOLD[1], FAR[0], QUANT[0]},
                  box=(x0 - 4, y0 - 6, x1 + 5, y1 + 3))
    layers.mark(f'{kind}/ribbon' if name else f'{kind}/cleanup')


def _boss(img, cx, cy):
    """Gold corner boss with a red gem."""
    pts = {(cx + dx, cy + dy) for dx in range(-2, 3) for dy in range(-2, 3) if abs(dx) + abs(dy) <= 3}
    for (x, y) in pts:
        d = (x - cx) + (y - cy)
        _px(img, x, y, GOLD[4] if d < 0 else GOLD[3] if d == 0 else GOLD[2])
    _px(img, cx, cy, RED[4])
    _px(img, cx + 1, cy, RED[2])
    for p in edge_ring(pts):
        _px(img, *p, GOLD[1] if p[0] + p[1] < cx + cy else GOLD[0])


def _skull(img, cx, y):
    """Wither-skeleton skull keystone (11x10) with glowing violet eyes, on the frame top."""
    rows = ("..#######..",
            ".#########.",
            "###########",
            "###########",
            "##ee###ee##",
            "##ee###ee##",
            "#####.#####",
            ".#########.",
            "..#.#.#.#..",
            "..#######..")
    pts = {(cx - 5 + i, y + j) for j, row in enumerate(rows) for i, ch in enumerate(row) if ch == '#'}
    eyes = {(cx - 5 + i, y + j) for j, row in enumerate(rows) for i, ch in enumerate(row) if ch == 'e'}
    cast(img, pts | eyes, 1, 1, BLACKSTONE)
    for (x, yy) in pts:
        c = WITHER[4] if yy <= y + 1 or x <= cx - 4 else WITHER[2] if yy >= y + 7 or x >= cx + 4 else WITHER[3]
        _px(img, x, yy, c)
    for (x, yy) in eyes:
        _px(img, x, yy, NEB[5] if yy == y + 4 and (x - cx) in (-3, 2) else NEB[3])
    _px(img, cx, y + 6, WITHER[0])
    for p in edge_ring(pts | eyes):
        _px(img, *p, WITHER[1] if p[0] < cx and p[1] < y + 5 else WITHER[0])


def _leaves(img, cx, cy, fx, seed):
    """A cluster of oak leaves spilling over a frame corner."""
    rnd = random.Random(seed)
    pts = {}
    for dx in range(-3, 4):
        for dy in range(-3, 4):
            if dx * dx + dy * dy <= 9 + rnd.randint(-3, 2):
                pts[(cx + dx * fx, cy + dy)] = LEAF[4] if dx + dy < -1 else LEAF[3] if dx + dy < 2 else LEAF[2]
    for p in list(pts):
        if rnd.random() < 0.15:
            pts[p] = LEAF[2]
    cast(img, set(pts), 1, 1, OAK)
    for p, c in pts.items():
        _px(img, *p, c)
    for p in edge_ring(set(pts)):
        _px(img, *p, LEAF[1] if p[0] + p[1] < cx + cy else LEAF[0])


def _sheaf(img, cx, y):
    """Wheat sheaf keystone: a bundle of stalks tied with a red band, ears fanned on top."""
    pts = {}
    for j in range(11):
        half = 4 - j // 2 if j < 6 else 1 + (j - 6) // 2
        for i in range(-half, half + 1):
            if j < 5:
                pts[(cx + i, y + j)] = WHEAT[5] if (i + j) % 2 == 0 else WHEAT[4] if i < 0 else WHEAT[3]
            else:
                pts[(cx + i, y + j)] = STALK[4] if i < 0 else STALK[3] if i == 0 else STALK[2]
    for i in range(-2, 3):
        pts[(cx + i, y + 6)] = RED[4] if i < 0 else RED[3]
    for i in (-4, -2, 0, 2, 4):                              # ear tips fanning out
        pts[(cx + i + (i > 0) - (i < 0), y - 1)] = WHEAT[5] if i <= 0 else WHEAT[4]
    cast(img, set(pts), 1, 1, OAK)
    for p, c in pts.items():
        _px(img, *p, c)
    for p in edge_ring(set(pts)):
        _px(img, *p, WALNUT[1] if p[1] < y + 5 and p[0] < cx else WALNUT[0])


def _ribbon(img, cx, y, text, rib, palette):
    """Ribbon with the name: a band (lit top row, shaded bottom row) with arcade letters, two tails folded
    behind it with notched ends, the fold in the shadow tone."""
    import lettering
    word = lettering.arcade(text, palette, scale=1)
    w, h = word.width + 8, word.height + 3
    x0, x1 = cx - w // 2, cx - w // 2 + w - 1
    pts = {}
    for side in (-1, 1):                                     # tails, 3 px lower, behind the band
        tx0 = x0 - 7 if side < 0 else x1 + 1
        for i in range(7):
            for j in range(3, h + 3):
                outer = i if side < 0 else 6 - i                # 0 at the free end
                if outer < 2 and abs(j - (h + 5) / 2) < 2 - outer + 0.5:
                    continue                                      # the notch
                pts[(tx0 + i, y + j)] = rib[2] if j > 3 else rib[3]
        fx = x0 - 1 if side < 0 else x1 + 1                  # the fold
        for j in range(h, h + 3):
            pts[(fx, y + j)] = rib[1]
            pts[(fx - side, y + j)] = rib[1]
    for i in range(w):
        for j in range(h):
            pts[(x0 + i, y + j)] = rib[4] if j == 0 else rib[2] if j == h - 1 else rib[3]
    cast(img, set(pts), 1, 2, CHART)
    for p, c in pts.items():
        _px(img, *p, c)
    for p in edge_ring(set(pts)):
        _px(img, *p, rib[0])
    img.alpha_composite(word, (cx - word.width // 2, y + 2))


# ------------------------------------------------------------------ the chart, the compass, the title, soon
def chart(img, ox, oy, y0=-1, front_y=127, front=3, seed=4):
    """The navigator's star chart under the container part: navy paper, faint dashed latitude / longitude
    lines, a few constellations, a gold double border with ticks, a lit front edge and a front face."""
    X0, X1, Y0, YF = ox - 1, ox + 176, oy + y0, oy + front_y
    for y in range(Y0, YF + 1):
        for x in range(X0, X1 + 1):
            _px(img, x, y, CHART[3])
    for y in range(Y0 + 6, YF - 2, 12):                      # latitudes / longitudes, dashed
        for x in range(X0 + 5, X1 - 4):
            if (x // 2) % 3 != 2:
                _px(img, x, y, CHART[4])
    for x in range(X0 + 9, X1 - 4, 18):
        for y in range(Y0 + 5, YF - 4):
            if (y // 2) % 3 != 2:
                _px(img, x, y, CHART[4])
    rnd = random.Random(seed)
    for _ in range(40):
        x, y = rnd.randint(X0 + 6, X1 - 6), rnd.randint(Y0 + 6, YF - 6)
        _px(img, x, y, CHART[5] if rnd.random() < 0.3 else CHART[4])
    for (ax, ay, bx_, by) in ((X0 + 12, YF - 10, X0 + 22, YF - 16), (X0 + 22, YF - 16, X0 + 31, YF - 9),
                              (X1 - 32, YF - 14, X1 - 18, YF - 9)):
        n = max(abs(bx_ - ax), abs(by - ay))
        for i in range(n + 1):
            _px(img, round(ax + (bx_ - ax) * i / n), round(ay + (by - ay) * i / n), CHART[4])
        for (sx, sy) in ((ax, ay), (bx_, by)):
            twinkle(img, sx, sy, CREAM[4], CHART[5])
    for k, c in ((2, GOLD[2]), (4, GOLD[1])):                # gold double border
        for x in range(X0 + k, X1 - k + 1):
            _px(img, x, Y0 + k, c)
            _px(img, x, YF - k, c)
        for y in range(Y0 + k, YF - k + 1):
            _px(img, X0 + k, y, c)
            _px(img, X1 - k, y, c)
    for x in range(X0 + 8, X1 - 6, 6):                       # ticks between the lines
        _px(img, x, Y0 + 3, GOLD[2])
        _px(img, x, YF - 3, GOLD[2])
    for x in range(X0, X1 + 1):                              # lit front edge + front face
        _px(img, x, YF, CHART[4])
        for k in range(1, front + 1):
            _px(img, x, YF + k, CHART[1] if k == front else CHART[2])
    for y in range(Y0, YF + front + 2):
        _px(img, X0, y, CHART[0])
        _px(img, X1, y, CHART[0])
    for x in range(X0, X1 + 1):
        _px(img, x, Y0, CHART[0])
        _px(img, x, YF + front + 1, CHART[0])


def compass(img, ox, oy, col=4, r0=1, r1=4):
    """Gold compass rose in the gap column between two cards: 4 long points split into lit / dark halves (a red
    north tip), 4 short diagonal points, a ring, a cream centre, a dashed meridian above and below, small
    arrowheads east and west toward the cards."""
    x0, y0, x1, y1 = slot_box(ox, oy, col, r0, 1, r1 - r0 + 1)
    cx, cy = (x0 + x1 + 1) // 2, (y0 + y1 + 1) // 2
    pts = {}
    for y in range(y0 - 12, y1 + 8):                         # meridian
        if (y // 2) % 2 == 0 and abs(y - cy) > 14:
            pts[(cx, y)] = GOLD[2]
    for t in range(0, 360, 3):                               # ring
        x, y = round(cx + 6.5 * math.cos(math.radians(t))), round(cy + 6.5 * math.sin(math.radians(t)))
        pts[(x, y)] = GOLD[2] if (t // 15) % 2 else GOLD[3]
    for (dx, dy) in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        for k in range(1, 6):
            pts[(cx + dx * k, cy + dy * k)] = GOLD[3] if dx + dy <= 0 else GOLD[2]
    for (dx, dy, L) in ((0, -1, 12), (0, 1, 12), (1, 0, 8), (-1, 0, 8)):
        nx, ny = -dy, dx
        for k in range(L + 1):
            half = 2.4 * (1 - k / L)
            for s in range(-int(half + 0.5), int(half + 0.5) + 1):
                lit = s * (nx * LIGHT_DIR[0] + ny * LIGHT_DIR[1]) > 0 or (s == 0 and dx + dy < 0)
                pts[(cx + dx * k + nx * s, cy + dy * k + ny * s)] = GOLD[4] if lit else GOLD[2]
    for k in range(9, 13):
        for s in (-1, 0, 1):
            if (cx + s, cy - k) in pts:
                pts[(cx + s, cy - k)] = RED[4] if s <= 0 else RED[2]
    for (dx, dy) in ((0, 0), (-1, 0), (0, -1), (-1, -1)):
        pts[(cx + dx, cy + dy)] = CREAM[5] if (dx, dy) == (-1, -1) else CREAM[3]
    rose = {p for p in pts if abs(p[1] - cy) <= 13}
    cast(img, rose, 1, 1, CHART)
    for p, c in pts.items():
        _px(img, *p, c)
    for p in edge_ring(rose):
        _px(img, *p, GOLD[0])
    for side in (-1, 1):                                     # arrowheads toward the cards
        ax = cx + side * 10
        for k in range(3):
            for j in range(-k, k + 1):
                _px(img, ax + side * (2 - k), cy + j, GOLD[3] if j <= 0 else GOLD[2])
    pixel_perfect(img, only={GOLD[0]}, box=(cx - 14, y0 - 12, cx + 15, y1 + 8))


def title(img, cx, y, text):
    """Gold-framed navy plaque with gold material letters and two gold studs."""
    from pixfont import draw_material_text, material_text_size
    gold = (GOLD[0], GOLD[2], GOLD[3], GOLD[4], GOLD[5])
    tw, th = material_text_size(text, 2)
    w, h = tw + 18, th + 7
    x0 = cx - w // 2
    solid, face = raised(img, rrect(x0, y, x0 + w - 1, y + h - 1, 3), 3, CHART2, shadow_off=(2, 2),
                         shadow_ramp=CHART)
    for x, yy in face:                                       # gold fillet 1 px inside the face's edge
        inner = all((x + a, yy + b) in face for a, b in ((2, 0), (-2, 0), (0, 2), (0, -2)))
        near = all((x + a, yy + b) in face for a, b in N4)
        if near and not inner:
            lit = (x - 2, yy) not in face or (x, yy - 2) not in face
            _px(img, x, yy, GOLD[4] if lit else GOLD[2])
    draw_material_text(img, cx - tw // 2, y + 4, text, gold, scale=2)
    pixel_perfect(img, only={GOLD[0]}, box=(x0, y, x0 + w, y + h))
    for nx in (x0 + 4, x0 + w - 5):
        _px(img, nx, y + h // 2, GOLD[5])
        _px(img, nx, y + h // 2 + 1, GOLD[2])


def soon(img, ox, oy, c, r, w, text='Скоро...'):
    """'Coming soon' as uncharted territory: a dark plaque with a dashed gold border, a dim clock and dim
    letters - low contrast on purpose, there is nothing to go to yet."""
    from pixfont import draw_text, text_width
    x0, y0, x1, y1 = slot_box(ox, oy, c, r, w, 1)
    solid, face = raised(img, rrect(x0 + 1, y0 + 1, x1 - 1, y1 - 3, 2), 2, CHART2, shadow_off=(1, 2),
                         shadow_ramp=CHART)
    for x, y in face:
        border = any((x + a, y + b) not in face for a, b in N4)
        if border and ((x + y) // 2) % 2 == 0:
            _px(img, x, y, GOLD[1])
    tw = text_width(text)
    bx = (x0 + x1 + 1) // 2 - (tw + 10) // 2
    cy = y0 + 4
    disc = {(bx + i, cy + j) for j in range(7) for i in range(7) if (i - 3) ** 2 + (j - 3) ** 2 <= 10}
    for (x, y) in disc:
        _px(img, x, y, GOLD[3] if x + y < bx + cy + 5 else GOLD[2])
    for (x, y) in edge_ring(disc):
        _px(img, x, y, GOLD[1] if x + y < bx + cy + 6 else GOLD[0])
    _paint(img, [(bx + 3, cy + 1), (bx + 3, cy + 2), (bx + 3, cy + 3), (bx + 4, cy + 3)], CHART2[1])
    draw_text(img, bx + 10, y0 + 3, text, CREAM[2], shadow=CHART2[0])


# ------------------------------------------------------------------ export
def export_parts(out_dir, scale=1):
    """Every scene's parts: OUT/<scene>/NN_part.png + layers.json + _sheet.png, OUT/<scene>.aseprite (one layer
    per part) and OUT/<scene>.png rebuilt FROM the exported parts (proves the parts make the scene)."""
    for name, fn in SCENES.items():
        items = fn()
        W, H = 62, 60
        d = os.path.join(out_dir, name)
        meta = layers.save_parts(items, d, (W, H))
        for L, it in zip(meta['layers'], items):
            if it.get('shadow'):
                L['shadow'] = it['shadow']
        json.dump(meta, open(os.path.join(d, 'layers.json'), 'w'), ensure_ascii=False, indent=1)
        direct = compose(items, Image.new('RGBA', (W, H), (0, 0, 0, 0)))
        rebuilt = compose([dict(it, sprite=Image.open(os.path.join(d, L['file'])).convert('RGBA'))
                           for L, it in zip(meta['layers'], items)], Image.new('RGBA', (W, H), (0, 0, 0, 0)))
        assert direct.tobytes() == rebuilt.tobytes(), f'{name}: parts do not rebuild the scene'
        rebuilt.save(os.path.join(out_dir, f'{name}.png'))
        rebuilt.resize((W * 6, H * 6), Image.NEAREST).save(os.path.join(out_dir, f'{name}_x6.png'))
        canvas = Image.new('RGBA', (W, H), (0, 0, 0, 0))      # .aseprite: shadows baked into their part's layer
        rec = layers.start(canvas)
        compose(items, canvas)
        layers.stop()
        layers.write_aseprite(os.path.join(out_dir, f'{name}.aseprite'), rec.items, (W, H))
        print(f'{name}: {len(items)} parts -> {d}/')


if __name__ == '__main__':
    a = sys.argv[1:]
    if len(a) == 2 and a[0] == 'parts':
        export_parts(a[1])
    else:
        print(__doc__)
