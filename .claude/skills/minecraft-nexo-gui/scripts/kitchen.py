#!/usr/bin/env python3
"""Kitchen kit: stone counter, cutting board with a grid of shallow cells and a handle sticking out of the
window, felt-lined walnut tool case, glazed ceramic dish with compartments, arrow, chef's knife, plank sign and
a 16x16 cutting-board item icon. Used by gui_builder.py as `{"type": "kitchen", "part": ...}` layers; example
assets/examples/cutting_board/ (5x5 board, 3x2 tools, 3x2 result, references/kitchen.md).

Shading follows references/texture-shading.md: five tones per material from shading.ramp5 (index 0 outline,
1 shadow, 2 dark mid, 3 base, 4 light mid, 5 highlight), one light from the top-left, flat faces mostly one
tone, clusters instead of noise, no dithering. Objects on the counter are seen from the front-above like the
shop's buttons: light far edge and left side, base top face, darker front face (thickness), 1 px outline and
a hard projected shadow on the counter (down-right, one tone).

    python3 kitchen.py icon out.png [--scale 16]      the 16x16 cutting-board item (+ a zoomed copy)
"""
import random
import sys
from PIL import Image, ImageDraw

from shop import _px, letters, text_size
from shading import ramp5


def _r5(hexc, **kw):
    return [tuple(c) + (255,) for c in ramp5(hexc, **kw)]


STONE = _r5('#7b818c')        # cool grey counter
BOARD = _r5('#c4925a')        # light beech board
WALNUT = _r5('#6e4428')       # dark wood: tool case, knife handle
FELT = _r5('#3e7048')         # green felt lining
CERAMIC = _r5('#e6dcc6')      # cream glaze inside the dish
GLAZE = _r5('#3f72a6')        # blue glaze on the dish rim
STEEL = _r5('#8f98a6')        # knife blade
BRASS = _r5('#b9862c')        # rivets, case corners

_CUT = {0: [], 1: [1], 2: [1], 3: [2, 1], 4: [3, 1, 1], 5: [3, 2, 1, 1], 6: [4, 2, 1, 1]}
N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


# ------------------------------------------------------------------ masks

def rrect(x0, y0, x1, y1, r=3):
    """Rounded rectangle as a set of pixels (pixel-art corners from a cut table, not a soft circle)."""
    cut = _CUT[min(r, 6)]
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


def projected_shadow(img, solid, dx=2, dy=2, c=None):
    """Hard shadow of a solid on what is already drawn (the counter): one darker tone, offset down-right.
    Pixels with nothing under them (outside the counter) get no shadow."""
    c = c or STONE[1]
    for x, y in solid:
        q = (x + dx, y + dy)
        if q not in solid and _on_ground(img, *q):
            img.putpixel(q, c)


def raised(img, top, thick, ramp, shadow=True, lit_edges=True):
    """A slab seen from the front-above: `top` = top-face pixels; the front face is the top face pushed down
    `thick` px. Returns (solid, inner top face). Draw details on the returned top face afterwards."""
    solid = set(top)
    for k in range(1, thick + 1):
        solid |= {(x, y + k) for x, y in top}
    if shadow:
        projected_shadow(img, solid)
    out = edge(solid)
    front = solid - top
    face = top - out
    _paint(img, front - out, ramp[2])
    for x, y in front - out:                       # last visible row of the front face: shadow
        if (x, y + 1) in out:
            _px(img, x, y, ramp[1])
    _paint(img, face, ramp[3])
    if lit_edges:
        for x, y in face:
            if (x, y - 1) in out or (x - 1, y) in out:
                _px(img, x, y, ramp[4])            # far edge + left side catch the light
            elif (x, y + 1) in front:
                _px(img, x, y, ramp[4])            # front edge: protruding corner
            elif (x + 1, y) in out:
                _px(img, x, y, ramp[2])            # right side turns away
    _paint(img, out, ramp[0])
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


# ------------------------------------------------------------------ counter

def counter(img, ox, oy, y0=-1, y_front=115, front=3, x0=-1, x1=176, seed=4):
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


def board(img, ox, oy, c0=0, r0=0, n=5, m=5, rim=(5, 3, 5, 3), thick=3, handle=22, handle_h=14, seed=2):
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
    solid, face = raised(img, top, thick, BOARD)   # face pushed down, the rest shows what is under the board
    grain(img, face, BOARD, seed=seed, density=0.016, length=(5, 14))
    rnd = random.Random(seed + 7)                  # knife marks: short diagonal scratches, fresh (light) / old
    for _ in range(14):
        x, y = rnd.randint(fx0 + 2, fx1 - 6), rnd.randint(fy0 + 2, fy1 - 6)
        ln, c = rnd.randint(3, 4), BOARD[4] if rnd.random() < 0.6 else BOARD[2]
        _paint(img, [(x + i, y + i) for i in range(ln)], c)
    # slot cells: shallow squares cut into the board
    cells(img, fx0, fy0, n, m, BOARD, wall_lit=BOARD[4], wall_dark=BOARD[1])
    for (x, y) in [(bx0 + 1, by0 + 2), (bx0 + 2, by0 + 1), (bx0 + 3, by0 + 1), (bx0 + 1, by0 + 3)]:
        _px(img, x, y, BOARD[5])                   # glint on the lit corner
    return solid


# ------------------------------------------------------------------ tool case and dish

def tool_case(img, ox, oy, c0=6, r0=0, n=3, m=2, rim=4, thick=3):
    """Walnut case with felt-lined compartments under n x m slots, brass corners, shadow on the counter."""
    fx0, fy0 = ox + 7 + 18 * c0, oy + 17 + 18 * r0
    fx1, fy1 = fx0 + 18 * n - 1, fy0 + 18 * m - 1
    top = rrect(fx0 - rim, fy0 - rim, fx1 + rim, fy1 + rim - 1, 3)
    solid, face = raised(img, top, thick, WALNUT)
    grain(img, face, WALNUT, seed=5, density=0.06, light=0.2)
    cells(img, fx0, fy0, n, m, WALNUT, floor=FELT, deep=True, wall_lit=WALNUT[4], wall_dark=WALNUT[1])
    lx, ly = (fx0 + fx1) // 2 - 2, fy1 + rim                # brass latch on the front face
    for i in range(6):
        for j in range(4):
            c = BRASS[0] if i in (0, 5) or j == 3 else BRASS[5] if (i, j) == (1, 0) else BRASS[4] if j == 0 else BRASS[3]
            _px(img, lx + i, ly + j, c)
    return solid


def dish(img, ox, oy, c0=6, r0=3, n=3, m=2, rim=4, thick=3):
    """Ceramic dish with n x m compartments: blue glazed rim, cream glaze inside, a glossy glint on the lower
    right wall of each compartment (a concave surface lit from the top-left), shadow on the counter."""
    fx0, fy0 = ox + 7 + 18 * c0, oy + 17 + 18 * r0
    fx1, fy1 = fx0 + 18 * n - 1, fy0 + 18 * m - 1
    top = rrect(fx0 - rim, fy0 - rim, fx1 + rim, fy1 + rim - 1, 4)
    solid, face = raised(img, top, thick, GLAZE)
    cells(img, fx0, fy0, n, m, CERAMIC, floor=CERAMIC, deep=True, wall_lit=CERAMIC[5], wall_dark=CERAMIC[1])
    for r in range(m):
        for c in range(n):
            gx, gy = fx0 + 18 * c + 14, fy0 + 18 * r + 12
            _paint(img, [(gx, gy), (gx, gy + 1), (gx - 1, gy + 2)], CERAMIC[5])
    _paint(img, [(fx0 - rim + 3, fy0 - rim + 1), (fx0 - rim + 4, fy0 - rim + 1), (fx0 - rim + 5, fy0 - rim + 1),
                 (fx0 - rim + 1, fy0 - rim + 3), (fx0 - rim + 1, fy0 - rim + 4)], GLAZE[5])
    return solid


# ------------------------------------------------------------------ arrow, knife, sign

ARROW = ("....#...",
         "....##..",
         "#######.",
         "########",
         "#######.",
         "....##..",
         "....#...")


def arrow(img, x, y, fill=None):
    """Right-pointing arrow (8x7 + outline) painted on the counter: x, y = top-left of the shape."""
    fill = fill or CERAMIC
    m = {(x + i, y + j) for j, row in enumerate(ARROW) for i, ch in enumerate(row) if ch == '#'}
    ring = {(px + dx, py + dy) for px, py in m for dx in (-1, 0, 1) for dy in (-1, 0, 1)} - m
    projected_shadow(img, m | ring, 1, 1)
    _paint(img, ring, STONE[0])
    for (px, py) in m:
        _px(img, px, py, fill[4] if (px, py - 1) not in m or py - y < 3 else fill[3])


def knife(img, x, y, blade=36, handle=26):
    """Chef's knife lying on the counter, tip at the left (x), spine at y; the handle may stick out of the
    window on the right. Blade: lit spine, base face with a polished band, bright edge; walnut handle with
    brass rivets."""
    pts = {}
    for i in range(blade):                                     # spine straight at y, the belly curves up to
        h = 7 if i >= 12 else 1 + round(6 * (i / 12) ** 0.55)  # the tip at the spine
        for k in range(h):
            j = y + k
            c = (STEEL[4] if k == 0 else STEEL[5] if k == h - 1 else STEEL[2] if k == h - 2 and h > 3
                 else STEEL[4] if k == 2 and 6 < i < blade - 4 else STEEL[3])
            pts[(x + i, j)] = c
    bx = x + blade
    for i in range(3):                                         # bolster, a bit taller than the blade
        for j in range(y - 1, y + 8):
            pts[(bx + i, j)] = STEEL[4] if j == y - 1 else STEEL[2] if j > y + 5 else STEEL[3]
    hx = bx + 3
    for i in range(handle):
        for j in range(y + 1, y + 6):
            c = WALNUT[4] if j == y + 1 else WALNUT[2] if j == y + 5 else WALNUT[3]
            pts[(hx + i, j)] = c
    for rx in (hx + 4, hx + handle // 2, hx + handle - 5):    # brass rivets
        pts[(rx, y + 3)] = BRASS[5]
        pts[(rx + 1, y + 3)] = BRASS[3]
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


ICONS = {'cutting_board': icon_board, 'knife': icon_knife}


def render_icon(name):
    return ICONS[name]()


if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == 'icon':
        name = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith('--') else 'cutting_board'
        im = render_icon(name)
        im.save(sys.argv[2])
        im.resize((256, 256), Image.NEAREST).save(sys.argv[2].replace('.png', '_x16.png'))
        print('saved', sys.argv[2])
    else:
        print(__doc__)
