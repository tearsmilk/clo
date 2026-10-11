#!/usr/bin/env python3
"""Mode-select kit ("Навигатор"): every game mode is a window into its own world, set in a slab of the mode's
material on the slate counter of the main menu; a signpost between the windows points to both, a header
plank names the menu, a calm "soon" plank waits in the bottom row. Used by gui_builder.py as
`{"type": "modes", "part": ...}` layers; example assets/examples/mode_select/, references/mode-select.md.

Blessed (Oneblock, PvP, fishing, quantum tech): a blackstone slab with a gilded window frame and a skull
keystone; inside, the void with ONE grass block floating in a beam of holy light, a sword stuck in it, a
fishing line hanging into the void, a quantum orb circling it, far-off oneblock islands of other players.
Farm (resources, quests, levels, your own shop): an oak slab under a red barn gable; inside, a sunny day
with a square Minecraft sun, blocky hills, rows of ripe wheat, a market stall with a striped awning and
XP orbs floating up from the field.

House style as in hub.py / kitchen.py: soft five-tone ramps (delicate shading), one light from the
top-left, selective outlines, contact shadows, flat faces mostly one tone, clusters instead of noise.
"""
import math
import random

from kitchen import _r5, _px, _paint, rrect, edge_ring, raised, grain, sheen, N4, WALNUT
from hub import SLATE, GOLD, CREAM, PLAQUE, slot_box, cast, sparkle
from shading import pixel_perfect

# ------------------------------------------------------------------ palettes (outline, shadow, dark, base, light, hi)
BLACKSTONE = _r5('#3d3540', soft=1)     # Blessed slab
OAK = _r5('#b8854a', soft=1)            # Farm slab
VOID = _r5('#2b2350', soft=0.4)         # the void (banded, darkest at the top)
BEAM = _r5('#e8c872', soft=0.6)         # holy light
GRASS = _r5('#5fa83a', soft=0.6)
DIRT = _r5('#8a5a3a', soft=0.6)
NETH = _r5('#6a5a8e')                   # the sword: netherite with a purple sheen (metal: contrast)
QUANT = _r5('#3ad6e0', soft=0.3)        # quantum orb
SKY = _r5('#7fc4ec', soft=1)
HILL = _r5('#4f9a48', soft=1)
FARMLAND = _r5('#6e4a30', soft=1)
WHEAT = _r5('#e0b040', soft=0.6)
STALK = _r5('#8fae3a', soft=0.6)
AWNING = _r5('#c8413a', soft=0.6)
XP = _r5('#9ae83a', soft=0.3)
BARN = _r5('#a8392e', soft=1)
BONE = _r5('#c9c3b6', soft=1)           # the skull keystone (wither skeleton: dark)
WITHER = _r5('#55545c', soft=1)
CLOCK = GOLD


def _scene_box(x0, y0, x1, y1, bottom=18):
    """The window in a 4x4 slab: 5 px of frame round it, `bottom` px left for the name plate."""
    return x0 + 5, y0 + 5, x1 - 5, y1 - bottom


def _bands(img, box, ramp, idx, rows):
    """Horizontal bands of ramp tones (no gradient): idx = tone per band, rows = band heights."""
    x0, y0, x1, y1 = box
    y = y0
    for t, h in zip(idx, rows):
        for yy in range(y, min(y1 + 1, y + h)):
            for x in range(x0, x1 + 1):
                _px(img, x, yy, ramp[t])
        y += h
    for yy in range(y, y1 + 1):
        for x in range(x0, x1 + 1):
            _px(img, x, yy, ramp[idx[-1]])


def window_frame(img, box, trim, under):
    """Sunk window: 1 px dark rim, a 1 px trim ring outside it (lit top / left, dark bottom / right), the
    frame's shadow on the top and left rows of the picture."""
    x0, y0, x1, y1 = box
    for x in range(x0 - 2, x1 + 3):
        for y in (y0 - 2, y1 + 2):
            _px(img, x, y, trim[4] if y == y0 - 2 else trim[2])
    for y in range(y0 - 2, y1 + 3):
        for x in (x0 - 2, x1 + 2):
            _px(img, x, y, trim[4] if x == x0 - 2 and y < y1 + 2 else trim[2])
    _px(img, x0 - 2, y0 - 2, trim[5])
    for x in range(x0 - 1, x1 + 2):
        _px(img, x, y0 - 1, trim[0])
        _px(img, x, y1 + 1, trim[0])
    for y in range(y0 - 1, y1 + 2):
        _px(img, x0 - 1, y, trim[0])
        _px(img, x1 + 1, y, trim[0])


def _shade_in(img, box, ramp_of, rows=2):
    """The frame's shadow inside the window: the top `rows` rows and the left column one / two tones down."""
    x0, y0, x1, y1 = box
    px = img.load()
    for y in range(y0, y0 + rows):
        for x in range(x0, x1 + 1):
            px[x, y] = _darker(px[x, y], ramp_of, 2 if y == y0 else 1)
    for y in range(y0 + rows, y1 + 1):
        px[x0, y] = _darker(px[x0, y], ramp_of, 1)


def _darker(c, ramps, k):
    for r in ramps:
        if c in r:
            i = r.index(c)
            return r[max(1, i - k)]
    return c


# ------------------------------------------------------------------ Blessed: the void with one block
def iso_block(img, cx, top, a=6, side=12):
    """A grass block in 2:1 isometric: top diamond (rows 2, 6, ... 4a-2 px wide, 2 px steps), lit left face,
    darker right face, grass hanging over the dirt in an uneven fringe, a lit front edge, selective outline.
    The diamond's widest rows span cx-2a .. cx+2a-1. Returns the set of its pixels."""
    diamond = set()
    for j in range(2 * a):
        k = j if j < a else 2 * a - 1 - j
        for x in range(cx - 2 * k - 2, cx + 2 * k + 2):
            diamond.add((x, top + j))
    pts = {p: 'top' for p in diamond}
    for x in range(cx - 2 * a, cx + 2 * a):
        y0 = max(y for (xx, y) in diamond if xx == x) + 1
        for y in range(y0, y0 + side):
            pts[(x, y)] = 'left' if x < cx else 'right'
    col_top = {}
    for (x, y), k in pts.items():
        if k != 'top':
            col_top[x] = min(col_top.get(x, y), y)
    rnd = random.Random(11)
    out = {}
    for (x, y), k in pts.items():
        if k == 'top':
            c = GRASS[3]
            if (x - 1, y) not in diamond or (x, y - 1) not in diamond:
                c = GRASS[4]                                 # lit far edges of the top
        else:
            lit = k == 'left'
            drip = 2 + (x * 7 % 5 == 0) + (x * 3 % 7 == 1)  # uneven grass fringe
            c = (GRASS if y - col_top[x] < drip else DIRT)[3 if lit else 2]
        out[(x, y)] = c
    for (x, y), c in sorted(out.items()):                   # clusters: blades on top, pebbles in the dirt
        r_ = rnd.random()
        if c == GRASS[3] and r_ < 0.1 and out.get((x + 1, y)) == GRASS[3]:
            out[(x, y)] = out[(x + 1, y)] = GRASS[2]
        elif c in (DIRT[3], DIRT[2]) and r_ < 0.08 and out.get((x, y + 1)) == c:
            out[(x, y)] = out[(x, y + 1)] = DIRT[2] if c == DIRT[3] else DIRT[1]
        elif c == DIRT[3] and r_ < 0.06 and out.get((x + 1, y)) == c:
            out[(x, y)] = out[(x + 1, y)] = DIRT[4]
    for y in range(col_top[cx - 1], col_top[cx - 1] + side):  # the front vertical edge: lit / shadow seam
        g = y - col_top[cx - 1] < 2
        out[(cx - 1, y)] = (GRASS if g else DIRT)[4]
        out[(cx, y)] = (GRASS if g else DIRT)[1]
    for p, c in out.items():
        _px(img, *p, c)
    solid = set(out)
    for p in edge_ring(solid):
        lit = p[0] < cx and p[1] < top + a + 1
        _px(img, *p, GRASS[1] if lit else DIRT[0])
    return solid


def sword(img, x, y_tip_in, length=12):
    """A sword stuck point-down: blade from y_tip_in up `length` px, a crossguard, grip and pommel."""
    pts = {}
    gy = y_tip_in - length
    for yy in range(gy + 1, y_tip_in + 1):                 # blade: lit left edge, base, dark right edge
        pts[(x - 1, yy)] = NETH[5] if yy < y_tip_in - 2 else NETH[4]
        pts[(x, yy)] = NETH[4]
        pts[(x + 1, yy)] = NETH[2]
    pts[(x, y_tip_in + 1)] = NETH[3]
    for dx in range(-3, 4):                                # crossguard
        pts[(x + dx, gy)] = GOLD[4] if dx < 0 else GOLD[3]
        pts[(x + dx, gy - 1)] = GOLD[5] if dx < 0 else GOLD[4]
    for yy in range(gy - 5, gy - 1):                       # grip
        pts[(x, yy)] = WALNUT[3]
        pts[(x + 1, yy)] = WALNUT[2] if yy % 2 else WALNUT[1]
    pts[(x, gy - 6)] = GOLD[5]
    pts[(x + 1, gy - 6)] = GOLD[3]
    pts[(x, gy - 7)] = GOLD[4]
    pts[(x + 1, gy - 7)] = GOLD[2]
    solid = set(pts)
    for p in edge_ring(solid):
        _px(img, *p, NETH[0])
    for p, c in pts.items():
        _px(img, *p, c)
    return solid


def scene_void(img, box, seed=3):
    """The Blessed world: banded void, stars, two far-off oneblock islands, a holy beam onto ONE floating
    grass block with a sword stuck in it, a fishing line hanging into the void, a quantum orb circling."""
    x0, y0, x1, y1 = box
    W, H = x1 - x0 + 1, y1 - y0 + 1
    _bands(img, box, VOID, (1, 2, 2, 3), (H // 5, H // 4, H // 5, H))
    rnd = random.Random(seed)
    cx = x0 + W // 2
    top = y0 + H // 2 - 9
    # holy beam from above onto the block: widens in 2 px steps, a pale gold core, a lighter void rim
    for y in range(y0, top + 7):
        w = 5 + (y - y0) // 4
        for x in range(cx - w, cx + w):
            d = abs(x - cx + 0.5)
            _px(img, x, y, BEAM[4] if d < 1.5 else BEAM[3] if d < w - 1 else VOID[4])
    for (dx, dy) in ((-3, 4), (2, 9), (-1, 14), (3, 2)):    # motes drifting in the light
        _px(img, cx + dx, y0 + dy, CREAM[5])
    for (sx, sy) in ((x0 + 4, y0 + 4), (x0 + 13, y0 + 15), (x1 - 6, y0 + 3), (x1 - 3, y0 + 18), (x0 + 6, y1 - 6),
                     (x1 - 12, y1 - 3), (x0 + 19, y0 + 2), (x1 - 18, y0 + 9)):
        _px(img, sx, sy, VOID[5])
    for (sx, sy) in ((x0 + 9, y0 + 8), (x1 - 9, y1 - 11)):  # twinkles
        _px(img, sx, sy, CREAM[5])
        for dx, dy in N4:
            _px(img, sx + dx, sy + dy, VOID[4])
    for (ix, iy) in ((x0 + 7, y1 - 14), (x1 - 8, y0 + 12)):  # far-off oneblocks of other players
        _paint(img, [(ix, iy), (ix + 1, iy)], GRASS[2])
        _paint(img, [(ix, iy + 1), (ix + 1, iy + 1)], DIRT[1])
    solid = iso_block(img, cx, top)
    sword(img, cx, top + 5, length=11)
    # fishing: a rod lying over the block's left corner, the line hanging into the void, a bobber
    rx0, ry0 = cx - 11, top + 7
    for i in range(9):
        _px(img, rx0 - i, ry0 - i // 2 - 1, WALNUT[3] if i % 3 else WALNUT[2])
    lx = rx0 - 9
    for y in range(ry0 - 5, y1 - 7):
        _px(img, lx, y, BONE[3] if y % 3 else BONE[2])
    _paint(img, [(lx, y1 - 7), (lx + 1, y1 - 7)], AWNING[4])
    _paint(img, [(lx, y1 - 6), (lx + 1, y1 - 6)], AWNING[2])
    _paint(img, [(lx, y1 - 5), (lx + 1, y1 - 5)], CREAM[4])
    # quantum orb on an orbit round the block's right side
    ox_, oy_ = cx + 19, top + 14
    for a in range(0, 360, 6):
        x = round(ox_ + 7 * math.cos(math.radians(a)))
        y = round(oy_ + 3 * math.sin(math.radians(a)))
        if (x, y) not in solid:
            _px(img, x, y, QUANT[3] if 90 < a < 270 else QUANT[4])
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            _px(img, ox_ + dx, oy_ + dy, QUANT[5] if dx + dy < 0 else QUANT[4] if dx + dy == 0 else QUANT[2])
    for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
        _px(img, ox_ + dx, oy_ + dy, QUANT[2])
    _px(img, ox_ + 7, oy_, CREAM[5])                       # the electron
    for (dx, dy) in ((2, 2), (-3, 4), (1, 6)):             # crumbs falling from the block
        _px(img, cx + dx, top + 24 + dy, DIRT[2])


def skull(img, cx, y):
    """Wither-skeleton skull keystone (9x8) on the frame: dark bone, eye sockets, teeth, lit top-left."""
    rows = (".#######.",
            "#########",
            "#########",
            "##..#..##",
            "##..#..##",
            "#########",
            ".#.#.#.#.",
            ".#######.")
    pts = {(cx - 4 + i, y + j) for j, r in enumerate(rows) for i, ch in enumerate(r) if ch == '#'}
    holes = {(cx - 4 + i, y + j) for j, r in enumerate(rows) for i, ch in enumerate(r) if ch == '.'
             and 0 < j < 7}
    for (x, yy) in pts:
        c = WITHER[3]
        if yy == y or x == cx - 4:
            c = WITHER[4]
        elif yy >= y + 6 or x == cx + 4:
            c = WITHER[2]
        _px(img, x, yy, c)
    for p in holes:
        _px(img, *p, WITHER[0])
    for p in edge_ring(pts | holes):
        _px(img, *p, WITHER[0])


# ------------------------------------------------------------------ Farm: a sunny field
def scene_farm(img, box, seed=5):
    """The Farm world: banded sky, a square sun top-left (the light), flat blocky clouds, stepped hills,
    rows of ripe wheat on farmland getting taller toward the viewer, a market stall with a striped awning
    and crates, XP orbs rising from the field."""
    x0, y0, x1, y1 = box
    W, H = x1 - x0 + 1, y1 - y0 + 1
    hz = y0 + H * 2 // 5                                     # horizon
    _bands(img, (x0, y0, x1, hz), SKY, (3, 4, 4), (H // 8, H // 7, H))
    for dx in range(5):                                      # square sun with a light core
        for dy in range(5):
            _px(img, x0 + 4 + dx, y0 + 3 + dy, CREAM[5] if 0 < dx < 4 and 0 < dy < 4 else WHEAT[5])
    for (cx_, cy_, w) in ((x0 + 22, y0 + 5, 10), (x1 - 14, y0 + 9, 8)):   # blocky clouds
        for dx in range(w):
            _px(img, cx_ + dx, cy_, CREAM[5])
            _px(img, cx_ + dx, cy_ + 1, CREAM[4] if 1 < dx < w - 1 else SKY[4])
        for dx in range(2, w - 3):
            _px(img, cx_ + dx, cy_ - 1, CREAM[5])
    # hills: stepped blocks, back tone and front tone
    for x in range(x0, x1 + 1):
        hb = hz - 3 - (2 if (x - x0) // 6 % 3 == 1 else 4 if (x - x0) // 6 % 5 == 3 else 0)
        for y in range(hb, hz + 1):
            _px(img, x, y, HILL[4] if y == hb else HILL[3])
        hf = hz - (2 if (x - x0 + 3) // 7 % 2 else 0)
        for y in range(hf, hz + 3):
            _px(img, x, y, HILL[3] if y == hf else HILL[2])
    # field: farmland rows and wheat rows, taller toward the viewer
    y = hz + 3
    row = 0
    rnd = random.Random(seed)
    while y <= y1:
        hgt = 1 + row                                        # wheat height grows with the row
        for x in range(x0, x1 + 1):
            _px(img, x, y, FARMLAND[2] if row % 2 == 0 else FARMLAND[3])
        for yy in range(y + 1, min(y1 + 1, y + 1 + hgt + 1)):
            for x in range(x0, x1 + 1):
                _px(img, x, yy, STALK[2])
        step = 2 if row < 2 else 3
        for x in range(x0 + (row % 2), x1 + 1, step):        # wheat tufts: stalk + ear
            for k in range(hgt):
                _px(img, x, y + 1 + hgt - k, STALK[3] if k < hgt // 2 else WHEAT[3])
            _px(img, x, y + 1, WHEAT[4] if rnd.random() < 0.6 else WHEAT[5])
            if hgt > 2 and x + 1 <= x1:
                _px(img, x + 1, y + 2, WHEAT[2])
        y += hgt + 3
        row += 1
    sx = x1 - 19                                             # a dirt path from the viewer to the stall
    for y in range(hz + 3, y1 + 1):
        t = (y - hz - 3) / max(1, y1 - hz - 3)
        a = round(sx + 4 - t * 22)
        w = 3 + round(t * 6)
        for x in range(a, a + w):
            if x0 <= x <= x1:
                _px(img, x, y, FARMLAND[4] if x == a or y % 4 == 0 else FARMLAND[3])
    stall(img, sx, hz - 9)
    for (ox_, oy_) in ((x0 + 14, hz + 1), (x0 + 24, hz - 6), (x0 + 31, hz + 6)):   # XP orbs rising
        orb(img, ox_, oy_)


def orb(img, x, y):
    """XP orb: 3x3 lit ball with a 1 px glow cross."""
    for dx in range(3):
        for dy in range(3):
            _px(img, x + dx, y + dy, XP[5] if dx + dy == 0 else XP[4] if dx + dy < 3 else XP[2])
    for dx, dy in ((1, -1), (-1, 1), (3, 1), (1, 3)):
        _px(img, x + dx, y + dy, XP[1] if (dx, dy) in ((3, 1), (1, 3)) else XP[3])


def stall(img, x, y):
    """Market stall 19 px wide: two posts, a striped awning (lit top, scalloped edge), a counter with
    crates and goods, standing on the field."""
    pts = {}
    for j in range(5):                                       # awning
        for i in range(-1 + (j < 1), 20 - (j < 1)):
            stripe = ((i + 1) // 3) % 2 == 0
            r = AWNING if stripe else CREAM
            pts[(x + i, y + j)] = r[4] if j == 0 else r[3] if j < 4 else r[2]
    for i in range(-1, 20, 3):                               # scallops
        pts[(x + i, y + 5)] = (AWNING if ((i + 1) // 3) % 2 == 0 else CREAM)[2]
        pts[(x + i + 1, y + 5)] = (AWNING if ((i + 1) // 3) % 2 == 0 else CREAM)[2]
    for j in range(6, 19):                                   # posts
        pts[(x, y + j)] = WALNUT[3]
        pts[(x + 18, y + j)] = WALNUT[2]
    for j in range(6, 12):                                   # the shade under the awning, back wall
        for i in range(1, 18):
            pts[(x + i, y + j)] = WALNUT[1] if j == 6 else WALNUT[2]
    goods = [(3, CREAM[4]), (4, AWNING[3]), (6, WHEAT[4]), (7, WHEAT[3]), (11, XP[4]), (12, AWNING[4]),
             (14, WHEAT[5]), (15, WHEAT[3])]
    for i, c in goods:                                       # goods on the counter
        pts[(x + i, y + 11)] = c
        pts[(x + i, y + 10)] = c if i % 2 else WALNUT[2]
    for j in range(12, 19):                                  # counter front: planks
        for i in range(1, 18):
            pts[(x + i, y + j)] = WALNUT[4] if j == 12 else WALNUT[3] if (i % 6) else WALNUT[2]
    solid = set(pts)
    cast(img, solid, 2, 1, HILL)
    for p, c in pts.items():
        _px(img, *p, c)
    for p in edge_ring(solid):
        _px(img, *p, WALNUT[0])


def gable(img, cx, y, half=17):
    """Red barn gable sitting on the frame top: 2:1 roof slopes, lit left slope, white trim, round window."""
    pts = {}
    for j in range(half // 2 + 1):
        for i in range(-2 * j, 2 * j + 1):
            pts[(cx + i, y + j)] = BARN[4] if i < -2 * j + 2 else BARN[3] if i < 0 else BARN[2]
    for j in range(half // 2 + 1):
        pts[(cx - 2 * j, y + j)] = CREAM[5]
        pts[(cx - 2 * j - 1, y + j)] = CREAM[4]
        pts[(cx + 2 * j, y + j)] = CREAM[3]
        pts[(cx + 2 * j + 1, y + j)] = CREAM[2]
    wy = y + half // 4 + 1
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            pts[(cx + dx, wy + dy)] = WALNUT[1] if dx + dy < 0 else WALNUT[2]
    solid = set(pts)
    for p, c in pts.items():
        _px(img, *p, c)
    for p in edge_ring(solid):
        if p[1] <= y + half // 2:
            _px(img, *p, BARN[0])
    return solid


# ------------------------------------------------------------------ whole parts
GATES = {'blessed': (BLACKSTONE, GOLD, 'ruby'), 'farm': (OAK, WALNUT, 'mint')}


def gate(img, ox, oy, c, r, w, h, kind, name, seed=1):
    """One mode: a slab of the mode's material over its slots, a sunk window with the mode's world, the
    keystone (skull / barn gable) and the name in arcade letters on a dark plate under the window."""
    import lettering
    ramp, trim, palette = GATES[kind]
    x0, y0, x1, y1 = slot_box(ox, oy, c, r, w, h)
    top = rrect(x0 + 1, y0 + 1, x1 - 1, y1 - 4, 2)
    solid, face = raised(img, top, 3, ramp, shadow_off=(2, 2), shadow_ramp=SLATE, seed=seed)
    fx0, fy0, fx1, fy1 = x0 + 2, y0 + 2, x1 - 2, y1 - 5
    if kind == 'farm':
        grain(img, face, ramp, seed=seed, density=0.03, vertical=True, length=(5, 14))
        for sx in range(fx0 + 8, fx1, 9):                    # vertical planks
            for y in range(fy0, fy1 + 1):
                if (sx, y) in face:
                    _px(img, sx, y, ramp[2])
                if (sx + 1, y) in face:
                    _px(img, sx + 1, y, ramp[4])
    else:                                                    # blackstone: block seams and gold veins
        rnd = random.Random(seed)
        for (x, y) in sorted(face):
            if (y - fy0) % 9 == 8 or ((x - fx0 + (9 if (y - fy0) // 9 % 2 else 0)) % 18 == 17):
                _px(img, x, y, ramp[2])
            elif rnd.random() < 0.012:
                _paint(img, [p for p in ((x, y), (x + 1, y)) if p in face], GOLD[3] if rnd.random() < 0.4 else ramp[4])
    ring2 = {(x, y) for x, y in face if ((x, y - 2) not in solid or (x - 2, y) not in solid)
             and (x, y - 1) in face and (x - 1, y) in face}
    _paint(img, ring2, ramp[4])
    box = _scene_box(x0, y0, x1, y1, bottom=19)
    if kind == 'blessed':
        scene_void(img, box, seed)
        _shade_in(img, box, (VOID, BEAM, GRASS, DIRT))
    else:
        scene_farm(img, box, seed)
        _shade_in(img, box, (SKY, CREAM, WHEAT, HILL))
    window_frame(img, box, trim, ramp)
    cx = (x0 + x1 + 1) // 2
    if kind == 'blessed':
        skull(img, cx, box[1] - 6)
    else:
        gable(img, cx - 1, y0 - 4, half=17)
    # name plate: dark raised plate, arcade letters in the mode's colour
    word = lettering.arcade(name, palette, scale=1)
    py0 = box[3] + 3
    pw, ph = word.width + 4, word.height + 1
    plate = rrect(cx - pw // 2, py0, cx - pw // 2 + pw - 1, py0 + ph - 1, 2)
    raised(img, plate, 2, PLAQUE, shadow_off=(1, 1), shadow_ramp=ramp)
    img.alpha_composite(word, (cx - word.width // 2, py0 + 1))
    pixel_perfect(img, box=(x0, y0, x1 + 1, y1 + 1))


def signpost(img, ox, oy, col=4, r0=1, r1=4):
    """The navigator: a walnut post in the gap column with two arrow boards - left (red rune) to the first
    mode, right (green leaf) to the second - and a lantern hanging from its top."""
    x0, y0, x1, y1 = slot_box(ox, oy, col, r0, 1, r1 - r0 + 1)
    cx = (x0 + x1 + 1) // 2
    post = {(x, y) for y in range(y0 + 6, y1 - 1) for x in (cx - 1, cx)}
    cast(img, post, 2, 1, SLATE)
    for (x, y) in post:
        _px(img, x, y, WALNUT[3] if x < cx else WALNUT[2])
    for y in range(y1 - 3, y1):                              # foot block
        for x in range(cx - 3, cx + 3):
            _px(img, x, y, WALNUT[2] if y > y1 - 3 else WALNUT[3])
    for p in edge_ring(post | {(x, y) for y in range(y1 - 3, y1) for x in range(cx - 3, cx + 3)}):
        _px(img, *p, WALNUT[0])

    def board(yb, left, mark):
        pts = {}
        for j in range(5):
            span = range(cx - 9, cx + 8) if left else range(cx - 8, cx + 9)
            for x in span:
                tip = (x - (cx - 9)) if left else ((cx + 8) - x)
                if tip < 2 - min(j, 4 - j):
                    continue
                pts[(x, yb + j)] = OAK[4] if j == 0 else OAK[3] if j < 4 else OAK[2]
        solid = set(pts)
        cast(img, solid, 2, 2, SLATE)
        for p, c in pts.items():
            _px(img, *p, c)
        mx = cx - 4 if left else cx + 3
        _px(img, mx, yb + 2, mark[4])
        _px(img, mx + (1 if left else -1), yb + 2, mark[3])
        _px(img, mx, yb + 1, mark[3])
        _px(img, mx, yb + 3, mark[2])
        for p in edge_ring(solid):
            _px(img, *p, WALNUT[1] if p[1] < yb else WALNUT[0])
        _px(img, cx - 1, yb + 2, WALNUT[1])                  # nail
    board(y0 + 14, True, AWNING)
    board(y0 + 34, False, XP)
    # lantern on the top
    lx, ly = cx - 2, y0 + 1
    for dy in range(5):
        for dx in range(4):
            c = GOLD[5] if (1 <= dx <= 2 and 1 <= dy <= 3) else WALNUT[1]
            if dy == 0 or dy == 4:
                c = WITHER[3] if dx in (1, 2) else WITHER[2]
            _px(img, lx + dx, ly + dy, c)
    for dx, dy in ((-1, 2), (4, 2), (1, -1), (2, 5)):
        _px(img, lx + dx, ly + dy, GOLD[3])
    pixel_perfect(img, box=(x0, y0, x1 + 1, y1 + 1))


def soon(img, ox, oy, c, r, w, text='Скоро...'):
    """The 'coming soon' plank in the bottom row: a calm stone slab (low contrast - not a focus), a small
    gold clock and cream letters."""
    from hub import slab, lettering as letters
    from pixfont import text_width
    face, (x0, y0, x1, y1) = slab(img, ox, oy, c, r, w, 1, BLACKSTONE, 'flat', seed=7)
    tw = text_width(text)
    bx = (x0 + x1 + 1) // 2 - (tw + 11) // 2
    cy = y0 + 4
    disc = {(bx + i, cy + j) for j in range(7) for i in range(7) if (i - 3) ** 2 + (j - 3) ** 2 <= 10}
    cast(img, disc, 1, 1, BLACKSTONE)
    for (x, y) in disc:
        _px(img, x, y, CLOCK[4] if x + y < bx + cy + 5 else CLOCK[3])
    for (x, y) in edge_ring(disc):
        _px(img, x, y, CLOCK[1] if x + y < bx + cy + 6 else CLOCK[0])
    _paint(img, [(bx + 3, cy + 1), (bx + 3, cy + 2), (bx + 3, cy + 3), (bx + 4, cy + 3), (bx + 5, cy + 3)],
           BLACKSTONE[1])
    letters(img, bx + 11, y0 + 3, text, BLACKSTONE)
