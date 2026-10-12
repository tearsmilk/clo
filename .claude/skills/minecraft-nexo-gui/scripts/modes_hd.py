#!/usr/bin/env python3
"""Mode-select kit in HD ("32x32" pixel density: 2 texture px per GUI px), built from parts.

The art is drawn on a canvas twice the GUI size; gui_builder.py ("hd": 2) cuts it into glyph tiles of at
most 256x256 and joins them in the title with shifts (references/mode-select.md, "HD menus"). Every part is
drawn natively at this density - nothing is upscaled - so a part has twice the detail of the 1x kit
(modes.py): grass blades and flowers on the oneblock, a chest on it, a fuller in the sword, a reel on the
rod, three orbits round the quantum cube; a barn with a gambrel roof, shingles and a hay loft, a ribbed
silo, a fence, a stall with apples, carrots and bread, a quest board with notes, chickens, pumpkins, wheat
ears with grains and awns.

Layout parts (all in GUI units, K = 2 inside): scroll (the star chart unrolled between two wooden rods that
stick out past the window), gate (an illustrated card), compass, title (volumetric gold letters breaking
out over the top rod), soon. Scenes: blessed_parts() / farm_parts() return parts bottom -> top for
modes.compose(); a spec moves or hides parts with "scene".

    python3 modes_hd.py parts OUT_DIR      HD scene parts: PNGs, layers.json, _sheet.png, .aseprite
"""
import math
import os
import random
import sys

from PIL import Image

from kitchen import _r5, edge_ring, rrect, raised, N4, WALNUT
from hub import GOLD, CREAM
from shading import pixel_perfect
import layers
from modes import (Parts, override, compose, CHART, CHART2, BLACKSTONE, OAK, VOID, NEB, BEAM, GRASS, DIRT, NETH,
                   QUANT, SKY, FAR, HILL, FARMLAND, WHEAT, STALK, PATH, RED, CARROT, BARN, SILO, XP, WITHER, LEAF,
                   PAPER)

K = 2                                    # texture px per GUI px
N8 = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
PUMPKIN = _r5('#e07a1c', soft=0.5)
BREAD = _r5('#c88a48', soft=0.6)
CHICK = _r5('#eeeae0', soft=1)
STONE = _r5('#8a8e96', soft=0.8)
FOG = _r5('#9cb8c8', soft=1)             # far mountains in haze


def P(im, x, y, c):
    if c is not None and 0 <= x < im.width and 0 <= y < im.height:
        im.putpixel((int(x), int(y)), c)


def fill(im, pts, c):
    for p in pts:
        P(im, *p, c)


def outline(im, solid, lit_c, dark_c, lit=None):
    """Selective outline: lit_c where the outside pixel faces the light (top / left), dark_c elsewhere."""
    for p in edge_ring(solid):
        is_lit = lit(p) if lit else (((p[0], p[1] + 1) in solid or (p[0] + 1, p[1]) in solid)
                                     and not ((p[0], p[1] - 1) in solid or (p[0] - 1, p[1]) in solid))
        P(im, *p, lit_c if is_lit else dark_c)


def disc(cx, cy, r, ry=None):
    ry = ry or r
    return {(x, y) for y in range(int(cy - ry - 1), int(cy + ry + 2)) for x in range(int(cx - r - 1), int(cx + r + 2))
            if ((x + 0.5 - cx) / r) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= 1}


def ball(im, cx, cy, r, ramp, out=None):
    """A lit ball: tones by the angle to the top-left light, highlight dot, outline from the ramp's dark end."""
    pts = disc(cx, cy, r)
    for (x, y) in pts:
        nx, ny = (x + 0.5 - cx) / r, (y + 0.5 - cy) / r
        lam = -0.6 * nx - 0.7 * ny
        P(im, x, y, ramp[5] if lam > 0.75 else ramp[4] if lam > 0.3 else ramp[3] if lam > -0.25 else ramp[2])
    outline(im, pts, ramp[1], out or ramp[0])
    return pts


def twinkle(im, x, y, core, arm, big=False):
    P(im, x, y, core)
    for dx, dy in N4:
        P(im, x + dx, y + dy, arm)
    if big:
        for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)):
            P(im, x + dx, y + dy, arm)
        for dx, dy in ((1, 1), (-1, -1), (1, -1), (-1, 1)):
            P(im, x + dx, y + dy, None)


# ------------------------------------------------------------------ the iso block (HD)
def iso_block(im, cx, top, a, side, top_ramp, side_ramp, fringe=(3, 5), outline_c=None, seed=11, lit_spot=None,
              texture=True):
    """A block in 2:1 isometric: top diamond 4a px wide (2 px steps), lit left face, darker right face, the top
    material hanging over the side in an uneven fringe (base + 0..var px), clusters on every face, a lit
    front edge, a selective outline. lit_spot = (dx, dy, rx, ry) brightens part of the top (a beam).
    Returns (solid, {x: bottom y}, top-face pixels)."""
    rnd = random.Random(seed)
    diamond = set()
    for j in range(2 * a):
        k = j if j < a else 2 * a - 1 - j
        for x in range(cx - 2 * k - 2, cx + 2 * k + 2):
            diamond.add((x, top + j))
    col_top = {x: max(y for (xx, y) in diamond if xx == x) + 1 for x in range(cx - 2 * a, cx + 2 * a)}
    out = {}
    for (x, y) in diamond:
        c = top_ramp[3]
        if (x - 1, y) not in diamond or (x, y - 1) not in diamond:
            c = top_ramp[4]
        if lit_spot:
            dx, dy, rx, ry = lit_spot
            e = ((x - cx - dx) / rx) ** 2 + ((y - top - a - dy) / ry) ** 2
            if e < 1:
                c = top_ramp[5] if e < 0.3 else top_ramp[4]
        out[(x, y)] = c
    base, var = fringe
    for x, y0 in col_top.items():
        lit = x < cx
        drip = base + (rnd.randint(0, var) if var else 0) if base else 0
        for y in range(y0, y0 + side):
            r = top_ramp if y - y0 < drip else side_ramp
            c = r[3 if lit else 2]
            if r is top_ramp and y - y0 == drip - 1 and rnd.random() < 0.5:
                c = r[2 if lit else 1]                        # the fringe's lower edge in shadow
            out[(x, y)] = c
    if texture:
        for (x, y), c in sorted(out.items()):
            r_ = rnd.random()
            if c in (side_ramp[3], side_ramp[2]):
                d = side_ramp[max(1, side_ramp.index(c) - 1)]
                if r_ < 0.05 and all(out.get(q) == c for q in ((x + 1, y), (x, y + 1), (x + 1, y + 1))):
                    for q in ((x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)):
                        out[q] = d                             # pebble 2x2 with a lit corner
                    out[(x, y)] = side_ramp[min(5, side_ramp.index(c) + 1)]
                elif r_ < 0.09 and out.get((x + 1, y)) == c:
                    out[(x, y)] = out[(x + 1, y)] = d
            elif c == top_ramp[3] and r_ < 0.07 and out.get((x + 1, y)) == c:
                out[(x, y)] = out[(x + 1, y)] = top_ramp[2]
    for y in range(col_top[cx - 1], col_top[cx - 1] + side):  # front edge: lit seam + shadow seam
        g = base and y - col_top[cx - 1] < base
        out[(cx - 1, y)] = (top_ramp if g else side_ramp)[4]
        out[(cx, y)] = (top_ramp if g else side_ramp)[1]
    for p, c in out.items():
        P(im, *p, c)
    solid = set(out)
    o_lit, o_dark = outline_c or (top_ramp[1], side_ramp[0])
    outline(im, solid, o_lit, o_dark, lambda p: p[0] < cx and p[1] < top + a + 1)
    return solid, {x: y0 + side - 1 for x, y0 in col_top.items()}, diamond


def _mute(r):
    return [r[0], r[0], r[1], r[1], r[2], r[3]]


# ------------------------------------------------------------------ Blessed (HD)
def _neb(x, y, W, H, bx, seed):
    n = (math.sin(x * 0.085 + 1.7 * math.sin(y * 0.065 + seed)) + 0.8 * math.sin(y * 0.135 - x * 0.05 + 2.0 + seed)
         + 0.5 * math.sin((x + 2 * y) * 0.06 + seed * 1.7) + 0.25 * math.sin(x * 0.31 + y * 0.23))
    band = 1 - abs(y - H * 0.40) / (H * 0.55)
    near = max(0.0, 1 - abs(x - bx) / (W * 0.45))
    v = 0.32 * n + 0.9 * band + 0.75 * near - 0.55
    return 0 if v < -0.05 else 1 if v < 0.25 else 2 if v < 0.5 else 3 if v < 0.7 else 4 if v < 0.88 else 5


def blessed_parts(W=124, H=120, seed=3):
    Pt = Parts(W, H)
    bx, top, A, SIDE = W // 2, 46, 14, 22
    tones = (VOID[1], VOID[2], VOID[3], NEB[2], NEB[3], NEB[4])

    def void(im):
        for y in range(H):
            for x in range(W):
                P(im, x, y, tones[_neb(x, y, W, H, bx, seed)])

    def stars(im):
        rnd = random.Random(seed)
        for _ in range(90):
            x, y = rnd.randrange(W), rnd.randrange(H)
            if _neb(x, y, W, H, bx, seed) < 2:
                P(im, x, y, CREAM[3] if rnd.random() < 0.5 else NEB[4] if rnd.random() < 0.6 else CREAM[5])
        for (x, y) in ((10, 12), (104, 92), (26, 78), (116, 40)):
            twinkle(im, x, y, CREAM[5], NEB[4], big=True)
        for (x, y) in ((44, 8), (88, 104), (8, 104)):
            twinkle(im, x, y, CREAM[5], NEB[4])

    def far_islands(im):
        for (cx, ty, a, sd, tree) in ((20, 22, 4, 6, True), (100, 64, 3, 5, False), (84, 10, 2, 3, False)):
            g, d = _mute(GRASS), _mute(DIRT)
            solid, bottom, _ = iso_block(im, cx, ty, a, sd, g, d, fringe=(1, 1), outline_c=(VOID[1], VOID[0]),
                                         seed=cx, texture=False)
            for x, yb in bottom.items():
                h = (0, 1, 2, 1, 0, 2, 1)[(x * 3) % 7] if abs(x - cx) < 2 * a - 2 else 0
                for k in range(1, h + 1):
                    P(im, x, yb + k, d[1])
            if tree:
                for k in range(4):
                    P(im, cx - 1, ty + a - 2 - k, _mute(WALNUT)[3])
                for (x, y) in disc(cx - 1, ty - 4, 3.2, 2.6):
                    P(im, x, y, g[4] if x + y < cx + ty - 6 else g[3])

    def god_rays(im):
        for ang, ln in ((-0.62, 40), (-0.33, 46), (0.33, 46), (0.62, 40)):
            for t in range(4, ln):
                if t % 9 < 6:
                    P(im, round(bx + math.sin(ang) * t), round(t * math.cos(ang) * 0.95), NEB[4] if t % 9 < 4 else NEB[3])

    def beam(im):
        for y in range(0, top + 16):
            for x in range(bx - 30, bx + 30):
                d = abs(x - bx + 0.5)
                c = (CREAM[5] if d < 1 + y // 16 else BEAM[5] if d < 3 + y // 8 else BEAM[4] if d < 6 + y // 5
                     else BEAM[3] if d < 8 + y // 4 else NEB[4] if d < 9 + y // 4 else None)
                P(im, x, y, c)
        rnd = random.Random(seed + 7)
        for _ in range(14):                                  # motes drifting in the light
            y = rnd.randint(2, top - 2)
            x = bx + rnd.randint(-(5 + y // 5), 5 + y // 5)
            P(im, x, y, CREAM[5])

    def quantum(im):                                         # a tech cube on three orbits = an atom
        qx, qy = bx + 40, 26
        for tilt, ph in ((0.0, 40), (1.05, 160), (-1.05, 280)):
            pts = []
            for t in range(0, 360, 2):
                ex, ey = 17 * math.cos(math.radians(t)), 5.5 * math.sin(math.radians(t))
                pts.append((round(qx + ex * math.cos(tilt) - ey * math.sin(tilt)),
                            round(qy + ex * math.sin(tilt) + ey * math.cos(tilt)), t))
            for x, y, t in pts:
                if math.sin(math.radians(t)) <= 0:
                    P(im, x, y, QUANT[2])
            ex_, ey_, _ = pts[ph // 2]
            for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
                P(im, ex_ + dx, ey_ + dy, CREAM[5] if (dx, dy) == (0, 0) else QUANT[5])
            for dx, dy in ((-1, 0), (2, 1), (0, -1), (1, 2)):
                P(im, ex_ + dx, ey_ + dy, QUANT[3])
            fronts = [(x, y) for x, y, t in pts if math.sin(math.radians(t)) > 0]
            fill(im, fronts, None)
            iso_cache.append(fronts)
        solid, _, top_face = iso_block(im, qx, qy - 8, 4, 7, QUANT, QUANT, fringe=(0, 0),
                                       outline_c=(QUANT[1], QUANT[0]), texture=False)
        for (x, y) in top_face:                              # glowing panel lines on the top
            if (x - qx) % 6 == 0 and abs(y - (qy - 4)) < 3:
                P(im, x, y, CREAM[5])
        for y in range(qy - 2, qy + 5):                      # panel lines on the faces
            P(im, qx - 5, y, QUANT[5])
            P(im, qx + 4, y, QUANT[3])
        for fronts in iso_cache:
            for (x, y) in fronts:
                if (x, y) not in solid:
                    P(im, x, y, QUANT[4])
        twinkle(im, qx - 20, qy + 12, CREAM[5], QUANT[4], big=True)
        twinkle(im, qx + 18, qy - 12, CREAM[5], QUANT[4])

    iso_cache = []

    def island(im):
        solid, bottom, face = iso_block(im, bx, top, A, SIDE, GRASS, DIRT, fringe=(4, 4), lit_spot=(0, 0, 18, 6.5),
                                        seed=seed)
        rnd = random.Random(seed + 3)
        for (x, y) in sorted(face):                          # blades and flowers on the top
            r_ = rnd.random()
            if r_ < 0.05 and (x, y - 1) in face:
                P(im, x, y, GRASS[2])
                P(im, x, y - 1, GRASS[4] if im.getpixel((x, y - 1)) != GRASS[5] else GRASS[5])
            elif r_ < 0.065:
                P(im, x, y, WHEAT[5] if rnd.random() < 0.5 else RED[4])
                P(im, x, y + 1, GRASS[1])
        for (x, y) in ((bx - 18, top + 22 + 6), (bx + 16, top + 24 + 8), (bx - 6, top + 30 + 10)):
            fill(im, [(x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1), (x + 2, y + 1)], STONE[3])
            P(im, x, y, STONE[4])
            P(im, x + 2, y + 1, STONE[2])
        for x, yb in bottom.items():                         # dirt hanging under the floating block
            off = abs(x - bx) / (2 * A)
            h = int((1 - off) * 9 + (x * 7 % 5) - 1) if off < 0.92 else 0
            for k in range(1, h + 1):
                c = DIRT[2 if x < bx else 1] if k < h - 1 else DIRT[1]
                if (x * 3 + k) % 7 == 0:
                    c = DIRT[3] if x < bx else DIRT[2]
                P(im, x, yb + k, c)
            if h > 0:
                P(im, x, yb + h + 1, DIRT[0])
        for (rx, ln, s) in ((bx - 14, 16, -1), (bx + 6, 20, 1), (bx + 20, 12, 1)):   # roots
            x = rx
            for k in range(1, ln):
                if k % 4 == 0:
                    x += s
                P(im, x, bottom[rx] + 6 + k, WALNUT[2] if k % 3 else WALNUT[3])
            P(im, x + s, bottom[rx] + 6 + ln, WALNUT[2])
        for (dx, dy) in ((-6, 20), (4, 26), (-2, 34), (10, 22), (-12, 30)):    # crumbs falling into the void
            P(im, bx + dx, bottom[bx] + dy, DIRT[2])
            P(im, bx + dx + 1, bottom[bx] + dy, DIRT[1])
        # a small chest on the back-right of the top, its shadow on the grass
        chx, chy = bx + 12, top + 7
        ch = {(chx + i, chy + j) for i in range(10) for j in range(8)}
        for (x, y) in ch:
            P(im, x + 2, y + 1, GRASS[2]) if (x + 2, y + 1) not in ch else None
        for (x, y) in ch:
            j = y - chy
            P(im, x, y, WALNUT[4] if j == 0 else WALNUT[3] if j < 3 else WALNUT[1] if j == 3 else WALNUT[3]
              if x < chx + 8 else WALNUT[2])
        fill(im, [(chx + 4, chy + 3), (chx + 5, chy + 3), (chx + 4, chy + 4), (chx + 5, chy + 4)], GOLD[4])
        P(im, chx + 5, chy + 4, GOLD[2])
        outline(im, ch, WALNUT[1], WALNUT[0])

    def sword(im):
        x, y_in, L = bx - 1, top + 15, 30
        pts = {}
        gy = y_in - L
        for yy in range(gy + 2, y_in + 1):                   # blade with a fuller
            pts[(x - 2, yy)] = NETH[5] if yy < y_in - 6 else NETH[4]
            pts[(x - 1, yy)] = NETH[4]
            pts[(x, yy)] = NETH[3] if gy + 4 < yy < y_in - 4 else NETH[4]
            pts[(x + 1, yy)] = NETH[3]
            pts[(x + 2, yy)] = NETH[2]
        for dx in range(-7, 8):                              # guard: curved ends, a gem
            yy = gy + (1 if abs(dx) > 5 else 0)
            pts[(x + dx, yy)] = GOLD[5] if dx < 0 else GOLD[4]
            pts[(x + dx, yy + 1)] = GOLD[4] if dx < 0 else GOLD[2]
            if abs(dx) < 6:
                pts[(x + dx, yy - 1)] = GOLD[4] if dx < 0 else GOLD[3]
        for (dx, dy, c) in ((-1, -1, RED[5]), (0, -1, RED[4]), (1, -1, RED[3]), (-1, 0, RED[4]), (0, 0, RED[3]),
                            (1, 0, RED[2])):
            pts[(x + dx, gy + dy)] = c
        for yy in range(gy - 10, gy - 1):                    # wrapped grip
            for dx in (-1, 0, 1):
                wrap = (yy + dx) % 3 == 0
                pts[(x + dx, yy)] = (WALNUT[4] if dx < 0 else WALNUT[3] if dx == 0 else WALNUT[2]) if not wrap else WALNUT[1]
        for (dx, dy) in ((-2, -12), (-1, -12), (0, -12), (1, -12), (2, -12), (-1, -13), (0, -13), (1, -13),
                         (-2, -11), (-1, -11), (0, -11), (1, -11), (2, -11), (-1, -14), (0, -14), (1, -14)):
            pts[(x + dx, gy + dy)] = GOLD[5] if dx + dy < -13 else GOLD[4] if dx < 1 else GOLD[2]
        pts[(x, gy - 12)] = RED[4]
        for k in range(1, 6):                                # the sword's shadow on the grass, down-right
            q = (x + 2 + k, y_in + k // 2)
            if q not in pts:
                P(im, *q, GRASS[2])
        for p, c in pts.items():
            P(im, *p, c)
        for p in edge_ring(set(pts)):
            if p[1] <= y_in:
                P(im, *p, NETH[0])

    def fishing(im):                                         # a rod leaning on the block, a line into the void
        x0, y0 = bx - 22, top + 13
        rod = []
        for i in range(30):
            t = i / 29
            rod.append((round(x0 - 26 * t), round(y0 - 22 * t + 6 * t * t)))
        for i, (x, y) in enumerate(rod):
            P(im, x, y, WALNUT[4] if i % 5 else WALNUT[3])
            if i < 16:
                P(im, x, y + 1, WALNUT[2])
            if i < 6:
                P(im, x + 1, y + 1, WALNUT[1])
        for (dx, dy, c) in ((-3, -1, STONE[4]), (-2, -1, STONE[3]), (-3, 0, STONE[3]), (-2, 0, STONE[2]),
                            (-3, 1, STONE[2]), (-2, 1, STONE[1])):  # reel
            P(im, x0 + dx, y0 + dy, c)
        lx, ly = rod[-1]
        by = H - 26
        for y in range(ly + 1, by):                          # the line, a slight sag outward
            t = (y - ly) / (by - ly)
            P(im, round(lx - 2 * math.sin(t * math.pi)), y, CREAM[3] if y % 5 else CREAM[2])
        bob = {(lx - 2 + i, by + j) for i in range(5) for j in range(6) if not ((i in (0, 4)) and j in (0, 5))}
        for (x, y) in bob:
            j = y - by
            P(im, x, y, (RED[5] if x < lx else RED[4] if x < lx + 1 else RED[3]) if j < 3 else
              (CREAM[5] if x < lx else CREAM[4] if x < lx + 1 else CREAM[3]))
        outline(im, bob, RED[1], RED[0])
        P(im, lx, by - 2, CREAM[2])
        twinkle(im, lx + 7, by + 3, CREAM[5], NEB[4])

    Pt.add('void', void)
    Pt.add('stars', stars)
    Pt.add('far_islands', far_islands)
    Pt.add('god_rays', god_rays)
    Pt.add('beam', beam)
    Pt.add('quantum', quantum)
    Pt.add('island', island)
    Pt.add('sword', sword)
    Pt.add('fishing', fishing)
    return Pt.items


# ------------------------------------------------------------------ Farm (HD)
def farm_parts(W=124, H=120, seed=5):
    Pt = Parts(W, H)
    hz = 50
    vpx = W * 0.42

    def sky(im):
        for y in range(hz + 1):
            c = SKY[3] if y < 12 else SKY[4] if y < 30 else SKY[5]
            for x in range(W):
                P(im, x, y, c)

    def sun(im):                                             # Minecraft's square sun: core, rim, a glow square
        cx, cy = 15, 14
        for dx in range(-9, 9):
            for dy in range(-9, 9):
                m = max(abs(dx + 0.5), abs(dy + 0.5))
                c = CREAM[5] if m < 5 else WHEAT[5] if m < 6.5 else SKY[5] if m < 8.5 and (dx + dy) % 2 == 0 else None
                if m >= 6.5 and m < 8.5:
                    c = SKY[5]
                P(im, cx + dx, cy + dy, c)
        fill(im, [(cx - 3, cy - 3), (cx - 2, cy - 3), (cx - 3, cy - 2)], (255, 255, 255, 255))

    def clouds(im):                                          # flat blocky clouds: lit top, shaded underside
        for (x0, y0, blocks) in ((34, 9, ((0, 2, 26, 5), (6, 0, 12, 3))), (78, 18, ((0, 2, 20, 4), (4, 0, 9, 3))),
                                 (104, 6, ((0, 1, 14, 4),))):
            pts = set()
            for (bx_, by_, w, h) in blocks:
                pts |= {(x0 + bx_ + i, y0 + by_ + j) for i in range(w) for j in range(h)}
            for (x, y) in pts:
                c = CREAM[5] if (x, y - 1) not in pts else CREAM[3] if (x, y + 1) not in pts else CREAM[4]
                P(im, x, y, c)

    def mountains(im):                                       # far hills in haze, two layers
        for x in range(W):
            h1 = 10 + 6 * math.sin(x * 0.07 + 1) + 3 * math.sin(x * 0.19)
            h2 = 6 + 4 * math.sin(x * 0.11 + 3)
            for y in range(round(hz - h1), hz - 4):
                P(im, x, y, FOG[4] if y == round(hz - h1) else FOG[3])
            for y in range(round(hz - 4 - h2), hz - 2):
                P(im, x, y, FOG[3] if y == round(hz - 4 - h2) else FOG[2])

    def forest(im):                                          # a line of trees: round canopies, trunks, lit tops
        rnd = random.Random(seed)
        x = -3
        while x < W + 4:
            r = rnd.randint(4, 6)
            cy = hz - 6 - rnd.randint(0, 4)
            for k in range(cy + r - 2, hz + 1):
                P(im, x, k, FAR[1])
            for (px_, py_) in disc(x, cy, r, r * 0.85):
                d = (px_ - x) + (py_ - cy)
                P(im, px_, py_, FAR[4] if d < -r * 0.6 else FAR[3] if d < r * 0.5 else FAR[2])
            x += rnd.randint(6, 9)
        for x in range(W):
            P(im, x, hz - 1, FAR[2])
            P(im, x, hz, FAR[1])

    def barn(im):                                            # gambrel roof, shingles, plank walls, X doors, hay loft
        x0, yb = 12, hz + 6                                  # left, ground line
        w = 30
        cx = x0 + w // 2
        pts = {}
        wall_top = yb - 16
        for y in range(wall_top, yb):
            for x in range(x0, x0 + w):
                c = BARN[3] if x < x0 + w - 4 else BARN[2]
                if (x - x0) % 4 == 0:
                    c = BARN[2] if x < x0 + w - 4 else BARN[1]
                pts[(x, y)] = c
        for j in range(12):                                  # roof: steep lower slopes, flatter top
            half = w // 2 + 1 - (j // 2 if j < 6 else 3 + (j - 6))
            yy = wall_top - 1 - j
            for x in range(cx - half, cx + half + 1):
                c = BARN[1] if x > cx else BARN[2]
                if yy % 3 == 0:
                    c = BARN[0] if x > cx else BARN[1]       # shingle rows
                pts[(x, yy)] = c
            pts[(cx - half, yy)] = CREAM[4]
            pts[(cx + half, yy)] = CREAM[2]
        for (dx, dy) in ((-4, 0), (4, 0)):                   # hay loft door with hay
            pass
        for y in range(wall_top - 9, wall_top - 2):
            for x in range(cx - 3, cx + 3):
                pts[(x, y)] = WHEAT[4] if (x + y) % 3 else WHEAT[3]
        for x in range(cx - 4, cx + 4):
            pts[(x, wall_top - 10)] = CREAM[4]
        for y in range(wall_top - 10, wall_top - 1):
            pts[(cx - 4, y)] = CREAM[4]
            pts[(cx + 3, y)] = CREAM[3]
        dx0, dw, dh = cx - 6, 12, 11                         # big double door with X braces
        for y in range(yb - dh, yb):
            for x in range(dx0, dx0 + dw):
                i, j = x - dx0, y - (yb - dh)
                half = dw // 2
                ii = i if i < half else i - half
                on = i in (0, half - 1, half, dw - 1) or j in (0, dh - 1) or ii == j * (half - 1) // (dh - 1) \
                    or ii == (half - 1) - j * (half - 1) // (dh - 1)
                pts[(x, y)] = CREAM[4] if on and x < cx + 3 else CREAM[3] if on else BARN[1]
        for y in range(wall_top, yb):                        # corner trim
            pts[(x0, y)] = CREAM[4]
            pts[(x0 + w - 1, y)] = CREAM[2]
        for x in range(x0, x0 + w):
            pts[(x, wall_top)] = CREAM[3]
        silo_x = x0 + w + 2                                  # ribbed silo with a dome
        for y in range(yb - 24, yb):
            for x in range(silo_x, silo_x + 9):
                c = SILO[4] if x < silo_x + 2 else SILO[3] if x < silo_x + 6 else SILO[2]
                if (y - yb) % 5 == 0:
                    c = SILO[2] if x < silo_x + 6 else SILO[1]
                pts[(x, y)] = c
        for (x, y) in disc(silo_x + 4.5, yb - 24, 4.5, 3):
            if y <= yb - 24:
                pts[(x, y)] = SILO[5] if x < silo_x + 4 else SILO[3]
        for p, c in pts.items():
            P(im, *p, c)
        outline(im, set(pts), FAR[1], FAR[0])

    def fence(im):
        y = hz + 7
        for x in range(0, 60):
            if x % 7 == 0:
                for k in range(-6, 1):
                    P(im, x, y + k, OAK[4] if k > -6 else OAK[5])
                    P(im, x + 1, y + k, OAK[2])
            else:
                P(im, x, y - 4, OAK[4])
                P(im, x, y - 3, OAK[2])
                P(im, x, y - 1, OAK[3])
                P(im, x, y, OAK[2])

    def field(im):                                           # furrows radiating from a vanishing point
        for y in range(hz + 1, H):
            d = y - hz
            for x in range(W):
                s = (x - vpx) / (d + 4)
                k = math.floor(s * 2.4)
                fx = s * 2.4 - k
                if d < 6:
                    c = WHEAT[4] if k % 2 == 0 else WHEAT[3]
                elif k % 2 == 0:                             # wheat: lit left edge, ears, shaded right edge
                    c = WHEAT[4] if fx < 0.2 else WHEAT[2] if fx > 0.82 else WHEAT[3]
                    if d > 10 and (y * 2 + int(fx * 9)) % 6 == 0:
                        c = WHEAT[5]
                    elif d > 16 and (y + int(fx * 7)) % 6 == 3:
                        c = WHEAT[2]
                else:
                    c = FARMLAND[2] if d < 26 else FARMLAND[1]
                    if fx > 0.75 and d > 12:
                        c = FARMLAND[3]                      # the lit far side of the furrow
                P(im, x, y, c)

    def path(im):                                            # dirt path to the stall, stones, grass edges
        rnd = random.Random(seed + 2)
        for y in range(hz + 8, H):
            d = y - hz
            cxp = 92 - (d - 8) * 0.42 + 3 * math.sin(d * 0.12)
            half = 2 + d * 0.15
            l, r = round(cxp - half), round(cxp + half)
            for x in range(l, r + 1):
                c = PATH[3]
                if x == l:
                    c = PATH[4]
                elif x == r:
                    c = PATH[2]
                elif rnd.random() < 0.06:
                    c = PATH[2]
                P(im, x, y, c)
            if d > 20 and rnd.random() < 0.25:
                sx = rnd.randint(l + 1, max(l + 1, r - 2))
                fill(im, [(sx, y), (sx + 1, y)], STONE[3])
                P(im, sx, y - 1, STONE[4])

    def stall(im):                                           # market stall with goods, sign, lantern
        x0, yt, w = 76, hz - 26, 44
        yb = hz + 20
        pts = {}
        for j in range(10):                                  # awning: stripes, lit top, fold shadows
            for i in range(-2 + (j < 2), w + 2 - (j < 2)):
                stripe = ((i + 2) // 6) % 2 == 0
                r = RED if stripe else CREAM
                c = r[5] if j < 2 else r[4] if j < 4 else r[3] if j < 8 else r[2]
                if (i + 2) % 6 == 5:
                    c = r[2] if j > 1 else r[3]
                pts[(x0 + i, yt + j)] = c
        for i in range(-2, w + 2):                           # scallops
            k = (i + 2) % 6
            stripe = ((i + 2) // 6) % 2 == 0
            r = RED if stripe else CREAM
            for j in range(10, 10 + (2 if k in (1, 2, 3, 4) else 1 if k in (0, 5) else 0)):
                pts[(x0 + i, yt + j)] = r[2]
        for j in range(10, yb - yt):                         # posts
            for i in (0, 1, 2):
                pts[(x0 + i, yt + j)] = WALNUT[4] if i == 0 else WALNUT[3]
            for i in (w - 3, w - 2, w - 1):
                pts[(x0 + i, yt + j)] = WALNUT[2] if i < w - 1 else WALNUT[1]
        for j in range(11, 26):                              # shaded back wall
            for i in range(3, w - 3):
                pts[(x0 + i, yt + j)] = WALNUT[1] if j < 14 else WALNUT[2] if (i % 7) else WALNUT[1]
        sx, sy = x0 + w // 2 - 6, yt + 13                    # hanging sign with a coin
        for j in range(7):
            for i in range(12):
                pts[(sx + i, sy + j)] = OAK[4] if j == 0 else OAK[3] if i < 11 else OAK[2]
        for (dx, dy) in disc(sx + 6, sy + 3.5, 2.6):
            pts[(dx, dy)] = GOLD[5] if dx + dy < sx + sy + 9 else GOLD[3]
        pts[(sx + 3, sy - 1)] = WALNUT[2]
        pts[(sx + 8, sy - 1)] = WALNUT[2]
        ly = yt + 11                                         # lantern on the left post
        for j in range(6):
            for i in range(5):
                pts[(x0 + 3 + i, ly + 2 + j)] = (GOLD[5] if 1 <= i <= 3 and 1 <= j <= 4 else WITHER[3])
        cy = yt + 26                                          # counter with goods
        for i in range(3, w - 3):
            pts[(x0 + i, cy)] = OAK[5]
            pts[(x0 + i, cy + 1)] = OAK[3]
        for j in range(cy + 2, yb):
            for i in range(3, w - 3):
                c = OAK[3] if (j - cy) % 5 else OAK[2]
                if i % 9 == 0:
                    c = OAK[2]
                pts[(x0 + i, j)] = c
        for p, c in pts.items():
            P(im, *p, c)
        solid = set(pts)
        rnd = random.Random(seed)
        for k, (gx, kind) in enumerate(((x0 + 6, 'apple'), (x0 + 17, 'carrot'), (x0 + 29, 'bread'))):
            for i in range(11):                              # a crate
                for j in range(5):
                    P(im, gx + i - 1, cy - 4 + j, WALNUT[3] if j < 4 else WALNUT[2])
                    solid.add((gx + i - 1, cy - 4 + j))
            for n in range(3):
                x, y = gx + 1 + n * 3, cy - 6 + (n % 2)
                if kind == 'apple':
                    for (px_, py_) in disc(x + 1, y + 1, 1.7):
                        P(im, px_, py_, RED[5] if px_ + py_ < x + y + 1 else RED[4] if px_ + py_ < x + y + 3 else RED[3])
                        solid.add((px_, py_))
                    P(im, x + 1, y - 1, WALNUT[2])
                elif kind == 'carrot':
                    for d in range(4):
                        P(im, x + 1, y + d, CARROT[4] if d < 2 else CARROT[3])
                        P(im, x + 2, y + d, CARROT[2])
                        solid |= {(x + 1, y + d), (x + 2, y + d)}
                    fill(im, [(x + 1, y - 1), (x + 2, y - 2), (x, y - 2)], LEAF[4])
                else:
                    for i in range(4):
                        for j in range(3):
                            P(im, x + i, y + j, BREAD[5] if j == 0 else BREAD[4] if i < 3 else BREAD[3])
                            solid.add((x + i, y + j))
                    P(im, x + 1, y, BREAD[2])
        outline(im, solid, WALNUT[1], WALNUT[0])

    def barrel(im):
        x0, y0 = 66, hz + 8
        pts = {}
        for j in range(12):
            bulge = 1 if 2 < j < 9 else 0
            for i in range(-bulge, 9 + bulge):
                c = OAK[4] if i < 2 else OAK[3] if i < 6 else OAK[2]
                if j in (2, 9):
                    c = STONE[3] if i < 6 else STONE[2]
                pts[(x0 + i, y0 + j)] = c
        for i in range(9):
            pts[(x0 + i, y0)] = OAK[5]
        for p, c in pts.items():
            P(im, *p, c)
        outline(im, set(pts), WALNUT[1], WALNUT[0])

    def quest_board(im):                                     # posts, a little roof, pinned notes, a "!"
        x0, y0 = 5, hz + 12
        pts = {}
        for j in range(30):
            pts[(x0 + 2, y0 + j)] = WALNUT[4]
            pts[(x0 + 3, y0 + j)] = WALNUT[3]
            pts[(x0 + 22, y0 + j)] = WALNUT[3]
            pts[(x0 + 23, y0 + j)] = WALNUT[2]
        for j in range(3, 19):
            for i in range(0, 26):
                c = OAK[3] if (j - 3) % 5 else OAK[2]
                if i > 23:
                    c = OAK[2]
                pts[(x0 + i, y0 + j)] = c
        for i in range(-2, 28):                              # roof
            pts[(x0 + i, y0)] = BARN[4]
            pts[(x0 + i, y0 + 1)] = BARN[3]
            pts[(x0 + i, y0 + 2)] = BARN[1]
        for (nx, ny, w, h) in ((3, 6, 7, 9), (12, 5, 6, 7), (19, 8, 5, 8)):
            for i in range(w):
                for j in range(h):
                    c = PAPER[5] if j == 0 or i == 0 else PAPER[4]
                    if j > 1 and j % 2 == 0 and 0 < i < w - 1:
                        c = PAPER[2]                         # lines of text
                    pts[(x0 + nx + i, y0 + ny + j)] = c
            pts[(x0 + nx + w // 2, y0 + ny)] = RED[4]
        for p, c in pts.items():
            P(im, *p, c)
        outline(im, set(pts), WALNUT[1], WALNUT[0])
        ex, ey = x0 + 11, y0 - 16                            # the floating "!"
        mark = {(ex + i, ey + j) for i in range(3) for j in list(range(8)) + [10, 11]}
        mark -= {(ex, ey + 7), (ex + 2, ey + 7)}
        for (x, y) in mark:
            P(im, x, y, CREAM[5] if x == ex and y < ey + 3 else WHEAT[5] if x == ex else WHEAT[4] if x == ex + 1 else WHEAT[3])
        outline(im, mark, WALNUT[1], WALNUT[0])

    def pumpkins(im):
        for (x, y) in ((36, hz + 30), (44, hz + 34)):
            pts = disc(x, y, 4, 3)
            for (px_, py_) in pts:
                c = PUMPKIN[4] if px_ < x - 1 else PUMPKIN[3] if px_ < x + 2 else PUMPKIN[2]
                if (px_ - x) in (-2, 1):
                    c = PUMPKIN[2]                           # ribs
                P(im, px_, py_, c)
            outline(im, pts, PUMPKIN[1], PUMPKIN[0])
            fill(im, [(x, y - 4), (x, y - 5), (x + 1, y - 5)], STALK[3])

    def chickens(im):
        for (x, y, f) in ((56, hz + 24, 1), (64, hz + 32, -1)):
            pts = {}
            for i in range(6):
                for j in range(5):
                    if not (i in (0, 5) and j in (0, 4)):
                        pts[(x + i * f, y + j)] = CHICK[4] if j < 2 else CHICK[3] if j < 4 else CHICK[2]
            for j in range(-3, 1):                           # head
                for i in (4, 5, 6):
                    pts[(x + i * f, y + j)] = CHICK[4]
            pts[(x + 5 * f, y - 4)] = RED[4]                 # comb
            pts[(x + 6 * f, y - 4)] = RED[3]
            pts[(x + 7 * f, y - 2)] = WHEAT[4]               # beak
            pts[(x + 6 * f, y - 2)] = WITHER[0]              # eye
            pts[(x + 6 * f, y)] = RED[3]                     # wattle
            for (dx, dy) in ((2, 5), (2, 6), (4, 5), (4, 6)):
                pts[(x + dx * f, y + dy)] = CARROT[3]
            for p, c in pts.items():
                P(im, *p, c)
            outline(im, set(pts), CHICK[1], CHICK[0])

    def xp(im):
        for (x, y, tr) in ((46, hz - 6, 3), (58, hz + 4, 2), (30, hz + 14, 2), (70, hz - 10, 1)):
            for (px_, py_) in disc(x, y, 2.6):
                P(im, px_, py_, XP[5] if px_ + py_ < x + y - 1 else XP[4] if px_ + py_ < x + y + 2 else XP[2])
            P(im, x - 1, y - 1, CREAM[5])
            for dx, dy in ((0, -4), (0, 4), (-4, 0), (4, 0)):
                P(im, x + dx - (dx > 0), y + dy - (dy > 0), XP[3])
            for k in range(tr):
                P(im, x, y + 6 + k * 3, XP[3 if k == 0 else 2])

    def wheat_front(im):                                     # big near stalks: ears with grains, awns, leaves
        rnd = random.Random(seed + 9)
        for x in range(1, W, 4):
            hgt = 18 + rnd.randint(0, 6)
            lean = rnd.choice((-1, 0, 0, 1))
            base = H - 1
            stem = []
            for k in range(hgt - 9):
                sx = x + (lean if k > (hgt - 9) // 2 else 0)
                stem.append((sx, base - k))
                P(im, sx, base - k, STALK[3] if k % 4 else STALK[4])
            if rnd.random() < 0.5:                           # a leaf
                lx, ly = stem[len(stem) // 3]
                d = rnd.choice((-1, 1))
                for k in range(4):
                    P(im, lx + d * (k + 1), ly - k // 2, STALK[4] if k < 2 else STALK[3])
            ex, ey = x + lean, base - hgt
            for j in range(10):
                w = 2 if j in (0, 9) else 3
                for i in range(w):
                    c = WHEAT[5] if i == 0 else WHEAT[4] if i == 1 else WHEAT[2]
                    if j % 2 == 1:
                        c = WHEAT[4] if i == 0 else WHEAT[3] if i == 1 else WHEAT[2]
                    P(im, ex - 1 + i, ey + j, c)
            for k in range(4):                               # awns
                P(im, ex - 2 - k // 2, ey - 1 - k, WHEAT[4])
                P(im, ex + 2 + k // 2, ey - 1 - k, WHEAT[3])
                P(im, ex, ey - 1 - k, WHEAT[5])

    Pt.add('sky', sky)
    Pt.add('sun', sun)
    Pt.add('clouds', clouds)
    Pt.add('mountains', mountains)
    Pt.add('forest', forest)
    Pt.add('barn', barn)
    Pt.add('field', field)
    Pt.add('fence', fence)
    Pt.add('path', path)
    Pt.add('quest_board', quest_board)
    Pt.add('pumpkins', pumpkins)
    Pt.add('barrel', barrel)
    Pt.add('stall', stall, shadow={'dx': 4, 'dy': 2, 'from_row': 40})
    Pt.add('chickens', chickens)
    Pt.add('xp', xp)
    Pt.add('wheat_front', wheat_front)
    return Pt.items


SCENES = {'blessed': blessed_parts, 'farm': farm_parts}


# ------------------------------------------------------------------ layout parts (GUI units in, HD pixels out)
GOLDV = _r5('#e0a83a')                   # title gold: metal, keeps its contrast


def hd_box(ox, oy, c, r, w, h):
    """Slot box in HD pixels: (x0, y0, x1, y1) for slots (c, r, w, h); ox / oy = window origin in GUI px."""
    x0, y0 = (ox + 7 + 18 * c) * K, (oy + 17 + 18 * r) * K
    return x0, y0, x0 + 18 * w * K - 1, y0 + 18 * h * K - 1


def _darker(c, ramps):
    for r in ramps:
        if c in r:
            return r[max(1, r.index(c) - 2)]
    return c


def drop_shadow(img, solid, dx, dy, ramps):
    """Shadow of a set of pixels on what is already drawn: the surface's own darker tone, offset down-right."""
    px = img.load()
    for (x, y) in solid:
        q = (x + dx, y + dy)
        if q not in solid and 0 <= q[0] < img.width and 0 <= q[1] < img.height and px[q][3]:
            px[q] = _darker(px[q], ramps)


def _rod(img, x0, x1, yc, seed=1):
    """A wooden scroll rod (cylinder lying across): lit top band, base, dark underside, grain streaks, gold
    end caps with a knob; outlined."""
    rnd = random.Random(seed)
    pts = {}
    for x in range(x0, x1 + 1):
        for j in range(-6, 7):
            c = WALNUT[5] if j == -4 else WALNUT[4] if j < -1 else WALNUT[3] if j < 3 else WALNUT[2] if j < 5 else WALNUT[1]
            pts[(x, yc + j)] = c
    for _ in range((x1 - x0) // 6):                          # grain along the rod
        x, j = rnd.randint(x0 + 2, x1 - 10), rnd.choice((-1, 0, 1, 2))
        for i in range(rnd.randint(4, 9)):
            pts[(x + i, yc + j)] = WALNUT[2]
    for side in (-1, 1):                                     # gold caps + knobs
        cx = x0 if side < 0 else x1
        for i in range(6):
            x = cx + side * (-i)
            for j in range(-8, 9):
                lit = j < -2
                pts[(x, yc + j)] = GOLD[5] if j == -6 else GOLD[4] if lit else GOLD[3] if j < 4 else GOLD[2]
        for (x, y) in disc(cx + side * 5, yc, 5, 6):
            d = (x - cx - side * 5) + (y - yc)
            pts[(x, y)] = GOLD[5] if d < -4 else GOLD[4] if d < 0 else GOLD[3] if d < 4 else GOLD[2]
    solid = set(pts)
    drop_shadow(img, solid, 3, 4, (CHART,))
    for p, c in pts.items():
        P(img, *p, c)
    outline(img, solid, WALNUT[1], WALNUT[0])
    return solid


def scroll(img, ox, oy, front_y=126, seed=4):
    """The star chart unrolled between two wooden rods that stick out past the window on both sides: navy
    paper with deckle edges beyond the window, a dashed grid, constellations, a gold double border, an
    engraved ship and a sea serpent in the bottom corners, the paper curling into each rod."""
    rnd = random.Random(seed)
    X0, X1 = ox * K, (ox + 176) * K - 1                       # the window in HD px
    Y0, YB = (oy - 1) * K, (oy + front_y) * K                  # paper top / bottom rod centre
    paper = set()
    for y in range(Y0, YB + 1):                              # deckle edge: wanders slowly, no 1 px nubs
        l = X0 - 5 - round(1 + math.sin(y * 0.11) + 0.6 * math.sin(y * 0.29 + 1))
        r = X1 + 5 + round(1 + math.sin(y * 0.13 + 2) + 0.6 * math.sin(y * 0.31))
        for x in range(l, r + 1):
            paper.add((x, y))
    drop_shadow(img, paper, 4, 4, ())                        # no surface under it: nothing to darken
    for (x, y) in paper:
        P(img, x, y, CHART[3])
    for (x, y) in paper:                                     # deckle edge: lit left, shaded right
        if (x - 1, y) not in paper:
            P(img, x, y, CHART[4])
        elif (x + 1, y) not in paper:
            P(img, x, y, CHART[2])
    for y in range(Y0 + 30, YB - 14, 24):                    # grid, dashed
        for x in range(X0 + 8, X1 - 7):
            if (x // 3) % 3 != 2:
                P(img, x, y, CHART[4])
    for x in range(X0 + 18, X1 - 8, 36):
        for y in range(Y0 + 14, YB - 14):
            if (y // 3) % 3 != 2:
                P(img, x, y, CHART[4])
    for _ in range(140):
        x, y = rnd.randint(X0 + 10, X1 - 10), rnd.randint(Y0 + 16, YB - 16)
        P(img, x, y, CHART[5] if rnd.random() < 0.3 else CHART[4])
    for k, c in ((7, GOLD[2]), (10, GOLD[1])):               # gold double border with corner diamonds
        for x in range(X0 + k, X1 - k + 1):
            P(img, x, Y0 + 8 + k, c)
            P(img, x, YB - 8 - k, c)
        for y in range(Y0 + 8 + k, YB - 8 - k + 1):
            P(img, X0 + k, y, c)
            P(img, X1 - k, y, c)
    for (cx, cy) in ((X0 + 8, Y0 + 17), (X1 - 8, Y0 + 17), (X0 + 8, YB - 17), (X1 - 8, YB - 17)):
        for (x, y) in {(cx + dx, cy + dy) for dx in range(-3, 4) for dy in range(-3, 4) if abs(dx) + abs(dy) <= 3}:
            P(img, x, y, GOLD[4] if x + y < cx + cy else GOLD[2])
    for y in range(Y0, Y0 + 4):                              # paper curling out of the top rod
        for x in range(X0 - 6, X1 + 7):
            if (x, y) in paper:
                P(img, x, y, CHART[1] if y < Y0 + 2 else CHART[2])
    for y in range(YB - 9, YB - 5):                          # ... and into the bottom rod
        for x in range(X0 - 6, X1 + 7):
            if (x, y) in paper:
                P(img, x, y, CHART[4] if y == YB - 9 else CHART[2])
    _ship(img, X0 + 22, YB - 34)
    _serpent(img, X1 - 64, YB - 30)
    _rod(img, X0 - 22, X1 + 22, Y0 - 2, seed)
    _rod(img, X0 - 22, X1 + 22, YB, seed + 1)


def _ship(img, x, y):
    """Engraved ship (line art in the chart's light tones, gold flag): hull, mast, two sails, waves."""
    ink, hi = CHART[5], CHART[4]
    for i in range(26):                                      # hull
        P(img, x + i, y + 14 + (1 if i < 3 or i > 22 else 0) + (1 if i < 1 or i > 24 else 0), ink)
        P(img, x + 2 + i * 22 // 26, y + 18, hi)
    for i in range(16):
        P(img, x + 11, y - 1 + i, ink)                       # mast
    for j in range(10):                                      # sails
        P(img, x + 12 + j // 2, y + j, ink)
        P(img, x + 12 + j // 2 + 1, y + j + 1, hi)
        P(img, x + 10 - j // 2, y + 3 + j, ink)
    for j in range(5):
        P(img, x + 12 + 5, y + 10 - j, ink)
        P(img, x + 10 - 5, y + 13 - j, ink)
    fill(img, [(x + 12, y - 2), (x + 13, y - 2), (x + 14, y - 1), (x + 12, y - 1), (x + 13, y - 1)], GOLD[3])
    for i in range(-4, 32):                                  # waves
        P(img, x + i, y + 20 + (1 if (i // 3) % 2 else 0), hi)


def _serpent(img, x, y):
    """Engraved sea serpent: three humps, a head with an eye, a curled tail, waves."""
    ink, hi = CHART[5], CHART[4]
    for (hx, r) in ((8, 5), (22, 6), (37, 5)):
        for t in range(0, 181, 12):
            P(img, round(x + hx + r * math.cos(math.radians(t))), round(y + 12 - r * math.sin(math.radians(t))), ink)
        P(img, x + hx, y + 12 - r - 2, hi)                   # fins
        P(img, x + hx - 1, y + 12 - r - 1, hi)
    for i in range(6):                                       # head + jaw
        P(img, x + 44 + i, y + 6 - i // 2, ink)
        P(img, x + 44 + i, y + 9 - i // 3, ink)
    P(img, x + 48, y + 5, GOLD[4])                           # the eye
    for t in range(0, 270, 20):                              # curled tail
        P(img, round(x + 1 + 3 * math.cos(math.radians(t))), round(y + 9 + 3 * math.sin(math.radians(t))), ink)
    for i in range(-2, 56):                                  # waves
        P(img, x + i, y + 14 + (1 if (i // 3) % 2 else 0), hi)


def card(img, ox, oy, c, r, w, h, kind, seed=1, scene=None):
    """One mode card in HD: a 4 px thick card with its shadow on the chart, the scene from its parts (124x120
    at 4x4 slots), a 10 px frame - material band with texture, a 2 px trim fillet lit top-left, a dark line
    - corner pieces and a keystone."""
    base = BLACKSTONE if kind == 'blessed' else OAK
    trim = GOLD if kind == 'blessed' else WALNUT
    x0, y0, x1, y1 = hd_box(ox, oy, c, r, w, h)
    solid, face = raised(img, rrect(x0 + 2, y0 + 2, x1 - 2, y1 - 6, 4), 4, base, shadow_off=(4, 4), shadow_ramp=CHART,
                         seed=seed)
    rnd = random.Random(seed)
    for (x, y) in sorted(face):                              # material texture on the band
        r_ = rnd.random()
        if kind == 'blessed':
            if r_ < 0.03:
                fill(img, [p for p in ((x, y), (x + 1, y)) if p in face], base[2])
            elif r_ < 0.036:
                fill(img, [p for p in ((x, y), (x + 1, y)) if p in face], GOLD[3])
        else:
            if (x + (y // 13) * 3) % 11 == 0 and r_ < 0.7:
                P(img, x, y, base[2])                        # grain
    layers.mark(f'{kind}/card')
    sx0, sy0, sx1, sy1 = x0 + 10, y0 + 10, x1 - 10, y0 + 129
    items = override(SCENES[kind](sx1 - sx0 + 1, sy1 - sy0 + 1, seed), scene)
    compose(items, img, sx0, sy0, clip=(sx0, sy0, sx1, sy1), prefix=f'{kind}/')
    for x in range(sx0 - 1, sx1 + 2):
        P(img, x, sy0 - 1, base[0])
        P(img, x, sy1 + 1, base[0])
    for y in range(sy0 - 1, sy1 + 2):
        P(img, sx0 - 1, y, base[0])
        P(img, sx1 + 1, y, base[0])
    for k, (lt, dk) in enumerate(((trim[5], trim[2]), (trim[4], trim[1]))):
        e = 3 - k
        for x in range(sx0 - e, sx1 + e + 1):
            P(img, x, sy0 - e, lt)
            P(img, x, sy1 + e, dk)
        for y in range(sy0 - e, sy1 + e + 1):
            P(img, sx0 - e, y, lt if y < sy1 + e else dk)
            P(img, sx1 + e, y, dk if y > sy0 - e else lt)
    layers.mark(f'{kind}/frame')
    corners = ((sx0 - 2, sy0 - 2), (sx1 + 2, sy0 - 2), (sx0 - 2, sy1 + 2), (sx1 + 2, sy1 + 2))
    cx = (x0 + x1 + 1) // 2
    if kind == 'blessed':
        for (qx, qy) in corners:
            _boss(img, qx, qy)
        layers.mark(f'{kind}/corners')
        _skull(img, cx, y0 - 8)
    else:
        for i, (qx, qy) in enumerate(corners):
            _leaves(img, qx, qy, 1 if i % 2 == 0 else -1, seed + i)
        layers.mark(f'{kind}/corners')
        _sheaf(img, cx, y0 - 12)
    layers.mark(f'{kind}/keystone')
    pixel_perfect(img, only={base[0], WALNUT[0], WITHER[0], LEAF[0], GOLD[0]}, box=(x0 - 4, y0 - 14, x1 + 6, y1 + 6))
    layers.mark(f'{kind}/cleanup')


def _boss(img, cx, cy):
    """Gold corner boss (11x11) with a faceted red gem."""
    pts = {(cx + dx, cy + dy) for dx in range(-5, 6) for dy in range(-5, 6) if abs(dx) + abs(dy) <= 6}
    drop_shadow(img, pts, 2, 2, (CHART, BLACKSTONE))
    for (x, y) in pts:
        d = (x - cx) + (y - cy)
        P(img, x, y, GOLD[5] if d < -4 else GOLD[4] if d < 0 else GOLD[3] if d < 3 else GOLD[2])
    for (x, y) in {(cx + dx, cy + dy) for dx in range(-2, 3) for dy in range(-2, 3) if abs(dx) + abs(dy) <= 2}:
        d = (x - cx) + (y - cy)
        P(img, x, y, RED[5] if d < -1 else RED[4] if d < 1 else RED[2])
    P(img, cx - 1, cy - 1, CREAM[5])
    outline(img, pts, GOLD[1], GOLD[0])


def _skull(img, cx, y):
    """Wither-skeleton skull keystone (21x20): rounded cranium lit top-left, deep eye sockets with violet glow,
    nose cavity, cheekbones, a row of teeth; shadow on the frame."""
    cran = disc(cx, y + 9, 10, 9.5)
    cran = {p for p in cran if p[1] <= y + 14}
    jaw = {(x, yy) for x in range(cx - 7, cx + 8) for yy in range(y + 14, y + 20)
           if not (yy == y + 19 and abs(x - cx) > 5)}
    pts = cran | jaw
    drop_shadow(img, pts, 2, 3, (BLACKSTONE, CHART, GOLD))
    for (x, yy) in pts:
        nx, ny = (x - cx) / 10, (yy - y - 9) / 10
        lam = -0.6 * nx - 0.7 * ny
        P(img, x, yy, WITHER[5] if lam > 0.6 else WITHER[4] if lam > 0.15 else WITHER[3] if lam > -0.3 else WITHER[2])
    for ex in (cx - 5, cx + 4):                              # sockets
        for (x, yy) in disc(ex + 0.5, y + 11, 3.2, 2.8):
            P(img, x, yy, WITHER[0])
        fill(img, [(ex, y + 11), (ex + 1, y + 11), (ex, y + 12)], NEB[3])
        P(img, ex, y + 11, NEB[5])
    fill(img, [(cx - 1, y + 14), (cx, y + 14), (cx - 1, y + 15), (cx, y + 15)], WITHER[1])   # nose
    for x in range(cx - 6, cx + 7):                          # teeth
        P(img, x, y + 17, WITHER[1] if (x - cx) % 2 == 0 else WITHER[4])
        P(img, x, y + 18, WITHER[1] if (x - cx) % 2 == 0 else WITHER[3])
    outline(img, pts, WITHER[1], WITHER[0])


def _leaves(img, cx, cy, fx, seed):
    """Oak leaves spilling over a frame corner: several pointed leaves with a midrib, lit top-left."""
    rnd = random.Random(seed)
    allp = set()
    for k in range(5):
        ang = math.radians(rnd.choice((-160, -120, -60, -20, 30, 70, 110, 150)) + k * 7)
        lx, ly = cx + fx * round(math.cos(ang) * 5), cy + round(math.sin(ang) * 5)
        pts = set()
        for t in range(-6, 7):
            wdt = 2.6 * (1 - (t / 7) ** 2)
            for s in range(-3, 4):
                if abs(s) <= wdt:
                    pts.add((lx + round(t * math.cos(ang) * fx - s * math.sin(ang) * fx * 0),
                             ly + round(t * math.sin(ang) + s)))
        for p in pts:
            d = (p[0] - lx) * fx + (p[1] - ly)
            P(img, *p, LEAF[4] if d < -2 else LEAF[3] if d < 2 else LEAF[2])
        for t in range(-4, 5):
            P(img, lx + round(t * math.cos(ang) * fx), ly + round(t * math.sin(ang)), LEAF[2])
        allp |= pts
    outline(img, allp, LEAF[1], LEAF[0])


def _sheaf(img, cx, y):
    """Wheat sheaf keystone (19x24): fanned ears on top, a red band with a knot, stalks spreading below."""
    pts = {}
    for k, ang in enumerate((-40, -20, 0, 20, 40)):          # ears fanned out
        a = math.radians(ang)
        for t in range(0, 11):
            x = cx + round(math.sin(a) * (12 - t))
            yy = y + round(12 - math.cos(a) * (12 - t))
            for s in (0, 1):
                pts[(x + s, yy)] = WHEAT[5] if s == 0 and t % 2 == 0 else WHEAT[4] if s == 0 else WHEAT[3]
        tipx, tipy = cx + round(math.sin(a) * 13), y + round(12 - math.cos(a) * 13)
        pts[(tipx, tipy)] = WHEAT[4]
    for j in range(13, 24):                                  # stalks spreading downward
        half = 2 + (j - 13) // 2
        for i in range(-half, half + 1):
            pts[(cx + i, y + j)] = STALK[4] if i < -1 else STALK[3] if i < 2 else STALK[2]
    for i in range(-4, 5):
        pts[(cx + i, y + 14)] = RED[4] if i < 0 else RED[3]
        pts[(cx + i, y + 15)] = RED[3] if i < 0 else RED[2]
    for (dx, dy) in ((1, 16), (2, 17), (1, 17)):
        pts[(cx + dx, y + dy)] = RED[3]
    drop_shadow(img, set(pts), 2, 3, (OAK, CHART, WALNUT))
    for p, c in pts.items():
        P(img, *p, c)
    outline(img, set(pts), WALNUT[1], WALNUT[0])


def compass(img, ox, oy, col=4, r0=1, r1=4):
    """Gold compass rose (HD) in the gap column: a ring with ticks, 8 main points split into lit / dark halves
    (red north), 8 small points, a gem centre, a dashed meridian above and below."""
    x0, y0, x1, y1 = hd_box(ox, oy, col, r0, 1, r1 - r0 + 1)
    cx, cy = (x0 + x1 + 1) // 2, (y0 + y1 + 1) // 2
    pts = {}
    for y in range(y0 - 18, y1 + 14):
        if (y // 3) % 2 == 0 and abs(y - cy) > 30:
            pts[(cx, y)] = GOLD[2]
    for t in range(0, 360, 2):
        for rr, c in ((12.5, GOLD[3]), (13.5, GOLD[2])):
            pts[(round(cx + rr * math.cos(math.radians(t))), round(cy + rr * math.sin(math.radians(t))))] = c
    for t in range(0, 360, 30):
        pts[(round(cx + 11 * math.cos(math.radians(t))), round(cy + 11 * math.sin(math.radians(t))))] = GOLD[4]

    def point(ang, L, wdt, lit_c, dark_c):
        a = math.radians(ang)
        dx, dy = math.cos(a), math.sin(a)
        nx, ny = -dy, dx
        for k10 in range(0, L * 10 + 1, 4):
            k = k10 / 10
            half = wdt * (1 - k / L)
            for s10 in range(-int(half * 10), int(half * 10) + 1, 4):
                s = s10 / 10
                x, yy = round(cx + dx * k + nx * s), round(cy + dy * k + ny * s)
                lit = (s * (nx * -1 + ny * -1)) > 0 or (abs(s) < 0.3 and dx + dy < 0)
                pts[(x, yy)] = lit_c if lit else dark_c
    for ang in (45, 135, 225, 315):
        point(ang, 10, 3.2, GOLD[3], GOLD[1])
    for ang, L in ((0, 16), (180, 16), (90, 28), (270, 28)):
        point(ang, L, 4.5, GOLD[5], GOLD[2])
    for (x, yy), c in list(pts.items()):                     # red north tip
        if yy < cy - 17 and abs(x - cx) <= 3:
            pts[(x, yy)] = RED[4] if x <= cx else RED[2]
    for (x, yy) in disc(cx, cy, 3):
        pts[(x, yy)] = CREAM[5] if x + yy < cx + cy - 1 else QUANT[4] if x + yy < cx + cy + 2 else QUANT[2]
    rose = {p for p in pts if abs(p[1] - cy) <= 29}
    drop_shadow(img, rose, 2, 3, (CHART,))
    for p, c in pts.items():
        P(img, *p, c)
    outline(img, rose, GOLD[1], GOLD[0])
    pixel_perfect(img, only={GOLD[0], GOLD[1]}, box=(cx - 20, cy - 32, cx + 21, cy + 33))


def title(img, cx, y, text, scale=4):
    """Volumetric gold letters (lettering.volume - the style the user liked: dense face, dark back) with
    sparkles, breaking out over the top rod; their shadow falls on the rod and the chart."""
    import lettering
    word = lettering.volume(text, GOLDV, scale=scale, depth=5, accent='sparkle')
    pixel_perfect(word, only={word.getpixel((x, y)) for x in range(word.width) for y in range(word.height)
                              if word.getpixel((x, y))[3] and word.getpixel((x, y))[:3] == GOLDV[0][:3]})
    x0 = cx - word.width // 2
    wp = word.load()
    solid = {(x0 + x, y + yy) for yy in range(word.height) for x in range(word.width) if wp[x, yy][3]}
    drop_shadow(img, solid, 4, 5, (CHART, WALNUT, GOLD))
    img.alpha_composite(word, (x0, y))


def soon(img, ox, oy, c, r, w, text='Скоро...'):
    """'Coming soon' as uncharted territory (HD): a dark plaque with a dashed gold border, a clock, dim letters."""
    from pixfont import draw_text, text_width
    x0, y0, x1, y1 = hd_box(ox, oy, c, r, w, 1)
    solid, face = raised(img, rrect(x0 + 2, y0 + 2, x1 - 2, y1 - 5, 3), 3, CHART2, shadow_off=(2, 3), shadow_ramp=CHART)
    for x, y in face:
        border = any((x + a, y + b) not in face for a, b in ((2, 0), (-2, 0), (0, 2), (0, -2)))
        inner = any((x + a, y + b) not in face for a, b in N4)
        if border and not inner and ((x + y) // 3) % 2 == 0:
            P(img, x, y, GOLD[2])
    tw = text_width(text) * 2
    bx = (x0 + x1 + 1) // 2 - (tw + 22) // 2
    cyc = (y0 + y1 - 3) // 2
    dsk = disc(bx + 8, cyc, 7.5)
    for (x, y) in dsk:
        d = math.hypot(x + 0.5 - bx - 8, y + 0.5 - cyc)
        P(img, x, y, GOLD[4] if d > 6 and x + y < bx + cyc + 8 else GOLD[2] if d > 6 else CREAM[3])
    for (dx, dy) in ((0, -5), (5, 0), (0, 5), (-5, 0)):
        P(img, bx + 8 + dx, cyc + dy, CHART2[1])
    for k in range(5):
        P(img, bx + 8, cyc - k, CHART2[0])
    for k in range(4):
        P(img, bx + 8 + k, cyc, CHART2[0])
    outline(img, dsk, GOLD[1], GOLD[0])
    draw_text(img, bx + 22, cyc - 7, text, CREAM[2], scale=2, shadow=CHART2[0])


# ------------------------------------------------------------------ export
def export_parts(out_dir):
    import json
    for name, fn in SCENES.items():
        items = fn()
        W, H = 124, 120
        d = os.path.join(out_dir, name)
        meta = layers.save_parts(items, d, (W, H))
        for L, it in zip(meta['layers'], items):
            if it.get('shadow'):
                L['shadow'] = it['shadow']
        json.dump(meta, open(os.path.join(d, 'layers.json'), 'w'), ensure_ascii=False, indent=1)
        canvas = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        rec = layers.start(canvas)
        compose(items, canvas)
        layers.stop()
        rebuilt = compose([dict(it, sprite=Image.open(os.path.join(d, L['file'])).convert('RGBA'))
                           for L, it in zip(meta['layers'], items)], Image.new('RGBA', (W, H), (0, 0, 0, 0)))
        assert canvas.tobytes() == rebuilt.tobytes(), f'{name}: parts do not rebuild the scene'
        rebuilt.save(os.path.join(out_dir, f'{name}.png'))
        rebuilt.resize((W * 4, H * 4), Image.NEAREST).save(os.path.join(out_dir, f'{name}_x4.png'))
        layers.write_aseprite(os.path.join(out_dir, f'{name}.aseprite'), rec.items, (W, H))
        print(f'{name}: {len(items)} parts -> {d}/')


if __name__ == '__main__':
    a = sys.argv[1:]
    if len(a) == 2 and a[0] == 'parts':
        export_parts(a[1])
    else:
        print(__doc__)
