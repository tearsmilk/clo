#!/usr/bin/env python3
"""Kitchen kit: stone counter, thick cutting board with a grid of shallow cells and a handle sticking out of
the window, felt-lined walnut tool case, white plate whose well holds the result slots, arrow, small chef's
knife, plank sign, and cutting-board item icons (32x32 with volume, 16x16 flat). Used by gui_builder.py as `{"type": "kitchen", "part": ...}` layers; example
assets/examples/cutting_board/ (5x5 board, 3x2 tools, 3x2 result, references/kitchen.md).

Shading follows references/texture-shading.md: five tones per material from shading.ramp5 (index 0 outline,
1 shadow, 2 dark mid, 3 base, 4 light mid, 5 highlight), one light from the top-left, flat faces mostly one
tone, clusters instead of noise, no dithering. Objects on the counter are seen from the front-above like the
shop's buttons: light far edge and left side, base top face, darker front face (thickness), 1 px outline and
a hard projected shadow on the counter (down-right, one tone).

    python3 kitchen.py icon out.png [cutting_board32|cutting_board|knife]   item icon (+ a zoomed copy)
"""
import random
import sys
from PIL import Image, ImageDraw

from shop import _px, letters, text_size
from shading import ramp5


def _r5(hexc, **kw):
    return [tuple(c) + (255,) for c in ramp5(hexc, **kw)]


SOFT = 1.0                    # delicate shading: close middle tones (shading.ramp5 soft); metals keep contrast
STONE = _r5('#7b818c', soft=SOFT)        # cool grey counter
BOARD = _r5('#c4925a', soft=SOFT)        # light beech board
WALNUT = _r5('#6e4428', soft=SOFT)       # dark wood: tool case, knife handle
FELT = _r5('#3e7048', soft=SOFT)         # green felt lining
CERAMIC = _r5('#e6dcc6', soft=SOFT)      # white-cream glazed plate
GLAZE = _r5('#3f72a6', soft=SOFT)        # blue band on the plate brim
STEEL = _r5('#8f98a6')        # knife blade
BRASS = _r5('#b9862c')        # rivets, case corners

_CUT = {0: [], 1: [1], 2: [1], 3: [2, 1], 4: [3, 1, 1], 5: [3, 2, 1, 1], 6: [4, 2, 1, 1]}
N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


# ------------------------------------------------------------------ masks

def _cut(r):
    if r in _CUT:
        return _CUT[r]
    import math
    out = [round(r - math.sqrt(r * r - (r - k - 0.5) ** 2)) for k in range(r)]
    return [c for c in out if c > 0]


def rrect(x0, y0, x1, y1, r=3):
    """Rounded rectangle as a set of pixels (pixel-art corners from a cut table, not a soft circle)."""
    cut = _cut(r)
    pts = set()
    for y in range(y0, y1 + 1):
        k = y - y0 if y - y0 < len(cut) else (y1 - y if y1 - y < len(cut) else None)
        c = cut[k] if k is not None else 0
        pts.update((x, y) for x in range(x0 + c, x1 - c + 1))
    return pts


def edge(mask):
    return {p for p in mask if any((p[0] + dx, p[1] + dy) not in mask for dx, dy in N4)}


def _paint(img, pts, c):
    for x, y in pts:
        _px(img, x, y, c)


def _on_ground(img, x, y):
    return 0 <= x < img.width and 0 <= y < img.height and img.getpixel((x, y))[3] == 255


def projected_shadow(img, solid, dx=2, dy=2, c=None, soft=True):
    """Shadow of a solid on what is already drawn (the counter): one darker tone, offset down-right, and with
    soft=True a 1 px penumbra one step lighter round its far edge (delicate shading: one extra step, still
    crisp pixels). Pixels with nothing under them (outside the counter) get no shadow."""
    c = c or STONE[1]
    hard = set()
    for x, y in solid:
        q = (x + dx, y + dy)
        if q not in solid and _on_ground(img, *q):
            hard.add(q)
    if soft:
        pen = {(x + a, y + b) for x, y in hard for a, b in ((1, 0), (0, 1), (1, 1))} - hard - set(solid)
        for q in pen:
            if _on_ground(img, *q) and q[0] >= min(x for x, _ in solid) + dx:
                img.putpixel(q, STONE[2])
    for q in hard:
        img.putpixel(q, c)


def raised(img, top, thick, ramp, shadow=True, lit_edges=True, shadow_off=(2, 2), front_grain=0.0, seed=1):
    """A slab seen from the front-above: `top` = top-face pixels; the front face is the top face pushed down
    `thick` px. The front face is banded like a rounded edge: base right under the lit nose, dark mid, shadow
    in the last row at the counter; front_grain adds dark streaks along it (long-grain wood). Returns
    (solid, inner top face). Draw details on the returned top face afterwards."""
    solid = set(top)
    for k in range(1, thick + 1):
        solid |= {(x, y + k) for x, y in top}
    if shadow:
        projected_shadow(img, solid, *shadow_off)
    out = edge(solid)
    front = solid - top
    face = top - out
    depth = {}
    for x, y in front - out:
        k = next(k for k in range(1, thick + 1) if (x, y - k) in top)
        depth[(x, y)] = k
        last = (x, y + 1) in out
        _px(img, x, y, ramp[1] if last else ramp[3] if k == 1 and thick > 3 else ramp[2])
    if front_grain:
        rnd = random.Random(seed)
        mid = sorted(p for p, k in depth.items() if 2 <= k <= thick - 2 and (p[0], p[1] + 1) not in out)
        for (x, y) in mid:
            if rnd.random() < front_grain:
                run = [(x + i, y) for i in range(rnd.randint(4, 12)) if (x + i, y) in depth]
                if len(run) >= 3:
                    _paint(img, run, ramp[1])
    _paint(img, face, ramp[3])
    if lit_edges:
        for x, y in face:
            if (x, y - 1) in out or (x - 1, y) in out:
                _px(img, x, y, ramp[4])            # far edge + left side catch the light
            elif (x, y + 1) in front:
                _px(img, x, y, ramp[4])            # front edge: protruding corner
            elif (x + 1, y) in out:
                _px(img, x, y, ramp[2])            # right side turns away
    for x, y in out:                               # selective outline: softer on the lit top / left side
        lit = ((x, y + 1) in solid or (x + 1, y) in solid) and not ((x, y - 1) in solid or (x - 1, y) in solid)
        _px(img, x, y, ramp[1] if lit else ramp[0])
    return solid, face


def grain(img, face, ramp, seed=1, density=0.05, vertical=False, light=0.3, length=(3, 12)):
    """Wood grain along the board: streaks of dark mid (some light mid), never single pixels; keep the
    density low - a flat face stays mostly one tone."""
    rnd = random.Random(seed)
    for (x, y) in sorted(face):
        if rnd.random() < density:
            ln = rnd.randint(*length)
            c = ramp[4] if rnd.random() < light else ramp[2]
            run = [(x, y + i) if vertical else (x + i, y) for i in range(ln)]
            run = [p for p in run if p in face]
            if len(run) >= 2:
                _paint(img, run, c)


def sheen(img, face, ramp, x0, y0, x1, y1, at=0.3, width=0.07, seed=1):
    """Soft sheen on a varnished top face: a diagonal band (light from the top-left) made of light-mid runs
    along the grain, so its edges are ragged like a real reflection on wood, with a few short highlight
    runs in its middle. One extra tone, no gradient fill."""
    rnd = random.Random(seed + 31)
    span = (x1 - x0) + (y1 - y0)
    for (x, y) in sorted(face):
        t = ((x - x0) + (y - y0)) / span
        dist = abs(t - at) / width
        if dist < 1 and rnd.random() < 0.17 * (1 - dist):
            run = [(x + i, y) for i in range(rnd.randint(3, 9)) if (x + i, y) in face]
            _paint(img, run, ramp[4])
            if dist < 0.3 and rnd.random() < 0.25 and len(run) >= 4:
                _paint(img, run[1:3], ramp[5])


# ------------------------------------------------------------------ counter

def counter(img, ox, oy, y0=-1, y_front=116, front=3, x0=-1, x1=176, seed=4):
    """Stone worktop under the whole container part: one flat base tone with granite clusters, a lit front
    edge, a darker front face and an outline. The player inventory below stays vanilla."""
    d = ImageDraw.Draw(img)
    X0, X1, Y0, YF = ox + x0, ox + x1, oy + y0, oy + y_front
    d.rectangle((X0, Y0, X1, YF + front), fill=STONE[3])
    rnd = random.Random(seed)
    shapes = (((0, 0), (1, 0)), ((0, 0), (0, 1)), ((0, 0), (1, 0), (1, 1)), ((0, 0), (1, 0), (2, 0)),
              ((0, 0), (0, 1), (1, 1)))
    for _ in range(int((X1 - X0) * (YF - Y0) * 0.006)):
        x, y = rnd.randint(X0 + 2, X1 - 3), rnd.randint(Y0 + 3, YF - 3)
        c = STONE[2] if rnd.random() < 0.65 else STONE[4]
        _paint(img, [(x + a, y + b) for a, b in rnd.choice(shapes)], c)
    d.line((X0, Y0, X1, Y0), fill=STONE[0])                    # back edge (gap to the wall)
    d.line((X0 + 1, Y0 + 1, X1 - 1, Y0 + 1), fill=STONE[2])    # AO along the back
    d.line((X0, YF, X1, YF), fill=STONE[4])                    # lit front edge
    d.rectangle((X0, YF + 1, X1, YF + front - 1), fill=STONE[2])
    d.line((X0, YF + front, X1, YF + front), fill=STONE[0])
    d.line((X0, Y0, X0, YF + front), fill=STONE[0])
    d.line((X1, Y0, X1, YF + front), fill=STONE[0])
    d.line((X0 + 1, Y0 + 1, X0 + 1, YF - 1), fill=STONE[4])    # lit left end


# ------------------------------------------------------------------ cutting board

def cells(img, x0, y0, n, m, ramp, floor=None, deep=False, wall_lit=None, wall_dark=None):
    """n x m slot cells as shallow recesses on the 18 px grid (x0, y0 = top-left slot frame): the slot frame
    line top/left is the shadowed wall, bottom/right the lit wall (like vanilla slots, in the material's
    tones). deep=True adds a soft self-cast shadow on the floor under the top/left wall (compartments)."""
    lit, dark = wall_lit or ramp[4], wall_dark or ramp[1]
    for r in range(m):
        for c in range(n):
            fx, fy = x0 + 18 * c, y0 + 18 * r
            if floor:
                ImageDraw.Draw(img).rectangle((fx + 1, fy + 1, fx + 16, fy + 16), fill=floor[3])
            for i in range(17):
                _px(img, fx + i, fy, dark)
                _px(img, fx, fy + i, dark)
                _px(img, fx + 1 + i, fy + 17, lit)
                _px(img, fx + 17, fy + 1 + i, lit)
            if deep:
                f = floor or ramp
                for i in range(1, 17):
                    _px(img, fx + i, fy + 1, f[2])
                    _px(img, fx + 1, fy + i, f[2])


def board(img, ox, oy, c0=0, r0=0, n=5, m=5, rim=(5, 3, 5, 2), thick=6, handle=22, handle_h=14, seed=2):
    """Cutting board under n x m slots (c0, r0 = first slot), a handle with a hanging hole sticking out of
    the window on the left (needs canvas left >= handle - 2), front face `thick` px, shadow on the counter."""
    fx0, fy0 = ox + 7 + 18 * c0, oy + 17 + 18 * r0
    fx1, fy1 = fx0 + 18 * n - 1, fy0 + 18 * m - 1
    L, R, T, B = rim
    bx0, by0, bx1, by1 = fx0 - L, fy0 - T, fx1 + R, fy1 + B
    top = rrect(bx0, by0, bx1, by1, 3)
    cy = (by0 + by1) // 2
    hx0 = bx0 - handle
    hy0, hy1 = cy - handle_h // 2, cy + handle_h // 2 - 1
    hand = rrect(hx0, hy0, bx0 + 3, hy1, 5)
    top |= hand
    hole = {(x, y) for y in range(cy - 2, cy + 2) for x in range(hx0 + 4, hx0 + 8)
            if not ((x in (hx0 + 4, hx0 + 7)) and (y in (cy - 2, cy + 1)))}
    top -= hole                                    # the hanging hole goes through: its far wall is the front
    solid, face = raised(img, top, thick, BOARD, shadow_off=(3, 2), front_grain=0.05, seed=seed)
    grain(img, face, BOARD, seed=seed, density=0.016, length=(5, 14))
    sheen(img, face, BOARD, bx0, by0, bx1, by1, seed=seed)
    ring2 = {(x, y) for x, y in face if ((x, y - 2) not in solid or (x - 2, y) not in solid)
             and (x, y - 1) in face and (x - 1, y) in face}
    _paint(img, ring2, BOARD[4])                   # 2 px bevel band on the lit edges: a rounded, thick edge
    rnd = random.Random(seed + 7)                  # knife marks: short diagonal scratches, fresh (light) / old
    for _ in range(10):
        x, y = rnd.randint(fx0 + 2, fx1 - 6), rnd.randint(fy0 + 2, fy1 - 6)
        ln, c = rnd.randint(3, 4), BOARD[4] if rnd.random() < 0.75 else BOARD[2]
        _paint(img, [(x + i, y + i) for i in range(ln)], c)
    # slot cells: shallow squares cut into the board - gentle walls (dark mid / light mid), a shadow pixel only
    # in the deepest inner corner
    cells(img, fx0, fy0, n, m, BOARD, wall_lit=BOARD[4], wall_dark=BOARD[2])
    for r in range(m):
        for c in range(n):
            _px(img, fx0 + 18 * c, fy0 + 18 * r, BOARD[1])
    for (x, y) in ([(bx0 + 3 + i, by0 + 1) for i in range(9)] + [(bx0 + 1, by0 + 3 + i) for i in range(6)]
                   + [(bx0 + 2, by0 + 2)]):
        _px(img, x, y, BOARD[5])                   # highlight along the lit corner of the edge
    return solid


# ------------------------------------------------------------------ tool case and plate

def tool_case(img, ox, oy, c0=6, r0=0, n=3, m=2, rim=4, thick=5, wall=3, seed=5):
    """Walnut tool box with depth under n x m slots: thick walls (rim with a lit bevel, a banded front face
    with grain), deep felt-lined compartments - the inner face of the far wall shows as a `wall` px strip at
    the top of each compartment, the felt gets a contact shadow under it and along the left wall -, the
    partitions show their top edges (lit nose, base, the side away from the light darker), brass corner caps
    and a brass hasp on the front, a soft shadow on the counter."""
    fx0, fy0 = ox + 7 + 18 * c0, oy + 17 + 18 * r0
    fx1, fy1 = fx0 + 18 * n - 1, fy0 + 18 * m - 1
    top = rrect(fx0 - rim, fy0 - rim, fx1 + rim, fy1 + rim - 1, 3)
    solid, face = raised(img, top, thick, WALNUT, shadow_off=(3, 2), front_grain=0.07, seed=seed)
    grain(img, face, WALNUT, seed=seed, density=0.05, light=0.25)
    ring2 = {(x, y) for x, y in face if ((x, y - 2) not in solid or (x - 2, y) not in solid)
             and (x, y - 1) in face and (x - 1, y) in face}
    _paint(img, ring2, WALNUT[4])                  # 2 px lit bevel on the far / left rim
    for r in range(m):
        for c in range(n):
            fx, fy = fx0 + 18 * c, fy0 + 18 * r
            ix0, iy0, ix1, iy1 = fx + 1, fy + 1, fx + 16, fy + 16
            ImageDraw.Draw(img).rectangle((ix0, iy0, ix1, iy1), fill=FELT[3])
            for k in range(wall):                  # inner face of the far wall: vertical wood, darker down
                c_ = WALNUT[1] if k == wall - 1 else WALNUT[2]
                for x in range(ix0, ix1 + 1):
                    _px(img, x, iy0 + k, c_)
                _px(img, ix0, iy0 + k, WALNUT[1])
            fy_ = iy0 + wall                       # felt: contact shadow under the far wall and the left wall
            for x in range(ix0, ix1 + 1):
                _px(img, x, fy_, FELT[1])
                _px(img, x, fy_ + 1, FELT[2])
            for y in range(fy_, iy1 + 1):
                _px(img, ix0, y, FELT[1])
                _px(img, ix0 + 1, y, FELT[2] if y > fy_ else FELT[1])
            for i in range(18):                    # partition / rim edges round the compartment
                _px(img, fx + i, fy, WALNUT[4])                     # far wall top: lit nose before the drop
                _px(img, fx + i, fy + 17, WALNUT[3])                # near wall top
            for i in range(1, 17):
                _px(img, fx, fy + i, WALNUT[2])                     # left wall top, its inner side in shadow
                _px(img, fx + 17, fy + i, WALNUT[4])                # right wall top, inner side lit
    x0, x1 = fx0 - rim, fx1 + rim
    yf = fy1 + rim                                 # first row of the front face
    for cx, sgn in ((x0, 1), (x1, -1)):            # brass corner caps over the front corners
        for j in range(thick - 1):
            for i in range(3):
                x = cx + sgn * i
                if (x, yf + j) in solid and (x, yf + j) not in edge(solid):
                    _px(img, x, yf + j, BRASS[4] if j == 0 else BRASS[2] if j == thick - 2 else BRASS[3])
        _px(img, cx + sgn, yf + 1, BRASS[5])
        for i in range(3):                         # the cap folds over the rim top
            x = cx + sgn * (i + 1)
            if (x, yf - 1) in face:
                _px(img, x, yf - 1, BRASS[3] if i else BRASS[4])
    lx = (fx0 + fx1) // 2 - 3                      # brass hasp: hinge plate on the rim, folding down the front
    for i in range(7):
        _px(img, lx + i, yf - 2, BRASS[0] if i in (0, 6) else BRASS[4])
        _px(img, lx + i, yf - 1, BRASS[0] if i in (0, 6) else BRASS[3])
    for j in range(thick - 1):
        for i in range(1, 6):
            c_ = BRASS[5] if (j, i) == (0, 2) else BRASS[4] if j == 0 else BRASS[2] if j == thick - 2 else BRASS[3]
            _px(img, lx + i, yf + j, c_)
        _px(img, lx, yf + j, BRASS[0])
        _px(img, lx + 6, yf + j, BRASS[0])
        _px(img, lx + 7, yf + j, WALNUT[1])        # contact shadow of the hasp on the wood
    _px(img, lx + 3, yf + 2, BRASS[0])             # the staple's slot
    _px(img, lx + 3, yf + 1, BRASS[0])
    return solid


def plate(img, ox, oy, c0=6, r0=3, n=3, m=2, brim=5, thick=3):
    """Serving plate under n x m slots: white glazed brim with a blue band and a rolled lit edge, a sunken well
    (shadowed far wall, lit near wall) whose flat floor holds the slots - no grid, the whole well is the slot
    area; glossy streaks on the brim and the floor, the near underside and a shadow on the counter."""
    fx0, fy0 = ox + 7 + 18 * c0, oy + 17 + 18 * r0
    fx1, fy1 = fx0 + 18 * n - 1, fy0 + 18 * m - 1
    well = rrect(fx0 - 1, fy0 - 1, fx1 + 1, fy1 + 1, 4)
    top = rrect(fx0 - 1 - brim, fy0 - 1 - brim, fx1 + 1 + brim, fy1 + brim, brim + 4)
    solid, face = raised(img, top, thick, CERAMIC, shadow_off=(2, 2), lit_edges=False)
    layers, rest = [], set(face) - well             # brim rings from the outside in
    while rest:
        ring = {p for p in rest if any((p[0] + dx, p[1] + dy) not in rest and (p[0] + dx, p[1] + dy) not in well
                                       for dx, dy in N4)}
        if not ring:
            break
        layers.append(ring)
        rest -= ring
    cx, cy = (fx0 + fx1) / 2, (fy0 + fy1) / 2
    for i, ring in enumerate(layers):
        for (x, y) in ring:
            u = (x - cx) / (fx1 - fx0) + (y - cy) / (fy1 - fy0)          # -1 far-left .. 1 near-right
            if i == 0:
                c = CERAMIC[5] if u < 0.15 else CERAMIC[3]                   # rolled rim
            elif i == 2:
                c = GLAZE[4] if u < 0.15 else GLAZE[3]                       # blue band
            else:
                c = CERAMIC[4] if u < 0.45 else CERAMIC[3]                   # the brim turns away near-right
            _px(img, x, y, c)
    _paint(img, rest, CERAMIC[4])
    _paint(img, well, CERAMIC[3])
    wedge = edge(well)
    for (x, y) in well - wedge:          # concave well: the near / right slope faces the light - a 2 px band
        if any((x + a, y + b) not in well for a, b in ((0, 2), (2, 0), (0, 3), (3, 0))):
            _px(img, x, y, CERAMIC[4])
    for (x, y) in wedge:
        far = (x, y - 1) not in well or (x - 1, y) not in well
        _px(img, x, y, CERAMIC[2] if far else CERAMIC[5])
    x0b, y0b = fx0 - 1 - brim, fy0 - 1 - brim
    _paint(img, [(x0b + 6 + i, y0b + 2) for i in range(7)] + [(x0b + 2, y0b + 6 + i) for i in range(4)]
           + [(x0b + 3, y0b + 4), (x0b + 4, y0b + 3)], CERAMIC[5])          # glint on the brim
    _paint(img, [(fx1 - 3 - i, fy1 - 2 - i) for i in range(4)] + [(fx1 - 3 - i, fy1 - 1 - i) for i in range(3)],
           CERAMIC[5])                                                       # reflection on the floor
    return solid


# ------------------------------------------------------------------ arrow, knife, sign

ARROW = ("...#..",
         "...##.",
         "######",
         "...##.",
         "...#..")


def arrow(img, x, y, fill=None):
    """Right-pointing arrow (6x5 + outline) painted on the counter: x, y = top-left of the shape."""
    fill = fill or CERAMIC
    m = {(x + i, y + j) for j, row in enumerate(ARROW) for i, ch in enumerate(row) if ch == '#'}
    ring = {(px + dx, py + dy) for px, py in m for dx in (-1, 0, 1) for dy in (-1, 0, 1)} - m
    projected_shadow(img, m | ring, 1, 1)
    _paint(img, ring, STONE[0])
    for (px, py) in m:
        _px(img, px, py, fill[4] if (px, py - 1) not in m or py - y < 2 else fill[3])


def knife(img, x, y, blade=20, handle=14, bh=5):
    """Small chef's knife lying on the counter, tip at the left (x), spine at y, blade `bh` px tall; the handle
    may stick out of the window on the right. Lit spine, base face, dark grind line, bright edge, steel
    bolster, walnut handle with two brass rivets. Keep it small next to the slots (blade ~ one slot)."""
    pts = {}
    tip = max(4, blade // 3)
    for i in range(blade):                                     # spine straight at y, the belly curves up to
        h = bh if i >= tip else 1 + round((bh - 1) * (i / tip) ** 0.55)   # the tip at the spine
        for k in range(h):
            c = (STEEL[4] if k == 0 else STEEL[5] if k == h - 1 else STEEL[2] if k == h - 2 and h > 3
                 else STEEL[3])
            pts[(x + i, y + k)] = c
    bx = x + blade
    for i in range(2):                                         # bolster, a bit taller than the blade
        for j in range(y - 1, y + bh + 1):
            pts[(bx + i, j)] = STEEL[4] if j == y - 1 else STEEL[2] if j >= y + bh - 1 else STEEL[3]
    hx = bx + 2
    hh = max(3, bh - 2)
    for i in range(handle):
        for j in range(y + 1, y + 1 + hh):
            c = WALNUT[4] if j == y + 1 else WALNUT[2] if j == y + hh else WALNUT[3]
            pts[(hx + i, j)] = c
    for rx in (hx + 3, hx + handle - 4):                       # brass rivets
        pts[(rx, y + 1 + hh // 2)] = BRASS[5]
    solid = set(pts)
    projected_shadow(img, solid | edge_ring(solid), 1, 2)
    _paint(img, edge_ring(solid), STEEL[0])
    for (px, py), c in pts.items():
        _px(img, px, py, c)
    for (px, py) in solid:                                     # handle outline in the handle's own dark tone
        if px >= hx:
            for dx, dy in N4:
                q = (px + dx, py + dy)
                if q not in solid:
                    _px(img, q[0], q[1], WALNUT[0])


def edge_ring(m):
    return {(px + dx, py + dy) for px, py in m for dx, dy in N4} - set(m)


def sign(img, cx, y, text, pad=6):
    """Light plank sign with burnt-in letters, standing on the back edge of the counter."""
    tw, th = text_size(text)
    w, h = tw + 2 * pad, th + 6
    x0 = cx - w // 2
    top = rrect(x0, y, x0 + w - 1, y + h - 1, 2)
    solid, face = raised(img, top, 2, BOARD)
    grain(img, face, BOARD, seed=11, density=0.04, light=0.4)
    for nx in (x0 + 2, x0 + w - 3):
        _px(img, nx, y + h // 2, STEEL[1])
        _px(img, nx, y + h // 2 - 1, STEEL[4])
    letters(img, cx - tw // 2, y + 4, text, BOARD[4], BOARD[4])          # lit lower edge of the burn
    letters(img, cx - tw // 2, y + 3, text, BOARD[0], BOARD[1])


# ------------------------------------------------------------------ 16x16 item icon

_BOARD_ICON = (                  # O outline, S shadow, D dark mid, B base, L light mid, H highlight
    "......OOOO......",
    ".....OLLLLO.....",
    ".....OLSSDO.....",
    ".....OLBBDO.....",
    "..OOOOLBBDOOOO..",
    ".OLLLLLBBBLLLLO.",
    "OLHHBBBBBBBBBBDO",
    "OLHBBDDDDBBBBBDO",
    "OLBBBBBBBBBBBBDO",
    "OLBBBBBBBDDDDBDO",
    "OLBDDDBBBBBBBBDO",
    "OLBBBBBBBBBBBBDO",
    "OLBBBBBDDDDBBBDO",
    "OLLLLLLLLLLLLLDO",
    ".ODDDDDDDDDDDSO.",
    "..OOOOOOOOOOOO..",
)


def icon_board():
    """16x16 cutting board item: a paddle board lying with the handle away from the viewer (hanging hole in
    it), lit far edge and left side, grain streaks, 1 px front face, outline in the wood's darkest tone."""
    tones = dict(zip('OSDBLH', BOARD))
    img = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    for y, row in enumerate(_BOARD_ICON):
        for x, ch in enumerate(row):
            if ch in tones:
                img.putpixel((x, y), tones[ch])
    return img


def icon_knife():
    """16x16 chef's knife on the diagonal (handle bottom-left, tip top-right): lit spine, base face, dark grind
    line and a bright edge, steel bolster, walnut handle with two brass rivets."""
    img = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    pts = {}
    for y in range(16):
        for x in range(16):
            s_, d_ = x + y, x - y                     # s across the knife (15 = spine), d along it
            if -3 <= d_ <= 13:                        # blade, the belly narrows toward the tip
                w = 3 if d_ < 7 else 2 if d_ < 11 else 1
                if 15 <= s_ <= 15 + w:
                    k = s_ - 15
                    pts[(x, y)] = (STEEL[4] if k == 0 else STEEL[5] if k == w else
                                   STEEL[2] if k == w - 1 and w > 1 else STEEL[3])
            elif -5 <= d_ <= -4 and 14 <= s_ <= 19:   # bolster
                pts[(x, y)] = STEEL[4] if s_ <= 15 else STEEL[2] if s_ >= 18 else STEEL[3]
            elif -14 <= d_ <= -6 and 15 <= s_ <= 17:  # handle
                pts[(x, y)] = WALNUT[4] if s_ == 15 else WALNUT[2] if s_ == 17 else WALNUT[3]
    for d_ in (-12, -8):                              # rivets
        x, y = (16 + d_) // 2, (16 - d_) // 2
        if (x, y) in pts:
            pts[(x, y)] = BRASS[5]
    for (x, y), c in pts.items():
        img.putpixel((x, y), c)
    for (x, y) in edge_ring(set(pts)):
        if 0 <= x < 16 and 0 <= y < 16:
            img.putpixel((x, y), WALNUT[0] if x - y <= -6 else STEEL[0])
    return img


def icon_board32(T=4):
    """32x32 cutting board item with volume: a paddle board lying at 45 deg (handle up-right with a hanging
    hole), seen from above with its T px thickness below - 1:1 diagonals stay clean in pixel art. Top face:
    rounded lit edge band, juice groove, long grain along the board; sides: the left-front one lit (base),
    the right-front one dark, a contact shadow row at the bottom; outline in the wood's darkest tone."""
    import math
    r2 = math.sqrt(2)

    def box(p, q, pc, qc, hp, hq, rr):            # rounded box sdf in board units (p along, q across)
        a_, b_ = abs(p - pc) - hp + rr, abs(q - qc) - hq + rr
        return math.hypot(max(a_, 0), max(b_, 0)) + min(max(a_, b_), 0) - rr

    def sdf(bx, by):                               # base position (height 0) -> distance in pixels
        by -= 2.5
        p, q = (bx - by) / r2, (bx + by) / r2
        body = box(p, q, -3.0, 22.6, 8.6, 6.0, 2.2)
        hand = box(p, q, 9.6, 22.6, 4.6, 2.0, 2.0)
        hole = math.hypot(p - 10.8, q - 22.6) - 1.5
        return max(min(body, hand), -hole), p, q

    def in_hole(sx, sy):                           # the hanging hole as seen on the top face
        by = sy + 0.5 + T - 2.5
        p, q = (sx + 0.5 - by) / r2, (sx + 0.5 + by) / r2
        return math.hypot(p - 10.8, q - 22.6) < 1.5

    kind = {}
    for sy in range(32):
        for sx in range(32):
            for h in range(T, -1, -1):             # the highest solid layer under this pixel
                d, p, q = sdf(sx + 0.5, sy + 0.5 + h)
                if d <= 0:
                    kind[(sx, sy)] = (h, d, p, q)
                    break

    def grad(bx, by):
        e = 0.05
        gx = sdf(bx + e, by)[0] - sdf(bx - e, by)[0]
        gy = sdf(bx, by + e)[0] - sdf(bx, by - e)[0]
        n = math.hypot(gx, gy) or 1
        return gx / n, gy / n

    img = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    for (sx, sy), (h, d, p, q) in kind.items():
        nx, ny = grad(sx + 0.5, sy + 0.5 + h)
        lit = -nx - ny                             # > 0: the edge faces the top-left light
        if h == T:
            c = BOARD[3]
            if d > -1.1:
                c = BOARD[4] if lit > 0.3 else BOARD[3] if lit > -0.3 else BOARD[2]
            elif -3.2 < d <= -2.2 and p < 5.0:     # juice groove: dark far wall, lit near wall
                c = BOARD[2] if lit > -0.2 else BOARD[4]
            elif d <= -3.2 and any(abs(q - g) < 0.36 and a0 < p < a1 for g, a0, a1 in
                                   ((20.5, -9.0, -1.0), (22.6, -4.0, 3.0), (25.0, -8.0, -3.5))):
                c = BOARD[2]                       # long grain: clean 45 deg lines
        else:
            if in_hole(sx, sy):
                c = BOARD[1]                       # far inner wall of the hole, seen through it
            else:
                c = BOARD[3] if nx < ny else BOARD[2]           # left-front side lit, right-front side dark
                if h == 0:
                    c = BOARD[2] if nx < ny else BOARD[1]       # contact shadow at the bottom
                elif h == T - 1 and nx < ny:
                    c = BOARD[4]                   # the rounded nose under the lit edge
        img.putpixel((sx, sy), c)
    for (x, y) in edge_ring(set(kind)):            # selective outline: softer on the lit top / left side
        if 0 <= x < 32 and 0 <= y < 32:
            lit = ((x, y + 1) in kind or (x + 1, y) in kind) and not ((x, y - 1) in kind or (x - 1, y) in kind)
            img.putpixel((x, y), BOARD[1] if lit else BOARD[0])
    for (sx, sy), (h, d, p, q) in kind.items():   # highlight along the far-left corner of the edge
        if h == T and d > -1.1 and p < -6.0 and q < 19.5:
            img.putpixel((sx, sy), BOARD[5])
    return img


ICONS = {'cutting_board': icon_board, 'cutting_board32': icon_board32, 'knife': icon_knife}


def render_icon(name):
    return ICONS[name]()


if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == 'icon':
        name = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith('--') else 'cutting_board'
        im = render_icon(name)
        im.save(sys.argv[2])
        im.resize((256, 256), Image.NEAREST).save(sys.argv[2].replace('.png', '_zoom.png'))
        print('saved', sys.argv[2])
    else:
        print(__doc__)
