#!/usr/bin/env python3
"""Main-menu kit in the house style: every destination is a raised slab of its own material sitting on a
slate counter (top face, 3 px front face, selective outline, soft contact shadow), with a volumetric picture
and a dark label plaque. Used by gui_builder.py as `{"type": "hub", "part": ...}` layers; example
assets/examples/main_menu/ (battle pass, profile with the player's own head, server choice, shop, settings,
wiki, social keys), references/main-menu.md.

House style = references/texture-shading.md "Delicate shading": soft five-tone ramps (shading.ramp5 soft=1)
for wood, stone, leather and cloth, standard contrasty ramps for metal, one light from the top-left, flat
faces mostly one tone, clusters instead of noise. Volume comes from thickness, cast shadows and parts that
sit ON other parts (plaques on slabs, a medallion on leather, a portrait hanging from a nail).

    python3 hub.py icon out.png head      16x16 stand-ins (head: preview of the player-head slot)
"""
import math
import random
import sys
from PIL import Image, ImageDraw

from kitchen import (_r5, _px, _paint, rrect, edge, edge_ring, raised, grain, sheen, counter, sign,
                     WALNUT, STEEL, N4)
from pixfont import draw_text, text_width, text_height
from shading import pixel_perfect
from safe import _STEEL5 as SAFE_STEEL   # the settings plate is brushed with safe.metal_plate

# ------------------------------------------------------------------ palettes (outline, shadow, dark, base, light, hi)
SLATE = _r5('#474d58', soft=1)          # the counter the slabs lie on
LEATHER = _r5('#55702e', soft=1)        # battle pass: olive leather
MAPLE = _r5('#d29a76', soft=1)          # profile: peach maple planks
DEEP = _r5('#5f5569', soft=1)           # server choice: purple deepslate
OBSIDIAN = _r5('#3a2c4c', soft=0.5)     # portal frame
PORTAL = _r5('#9a48e8', soft=0.4)       # portal surface (glows: keeps contrast)
VELVET = _r5('#2f5b40', soft=1)         # shop: dark green velvet
CLOTH = _r5('#4a72b8', soft=1)          # wiki: blue book cloth
ENAMEL = _r5('#24584f', soft=0.6)       # medallion centre
CANVAS = _r5('#8aa0ad', soft=1)         # portrait background
PLAQUE = _r5('#33292b', soft=1)         # label plaques
CREAM = _r5('#efe3c8', soft=1)          # plaque letters, stitches
GOLD = _r5('#d9a536')                   # metal: standard contrast
RED = _r5('#c8413a', soft=1)            # chest lid stripes
STEEL5 = _r5('#8a929e')                 # settings plate
DISCORD = _r5('#5865f2', soft=0.6)
YOUTUBE = _r5('#e0302e', soft=0.6)
TIKTOK = _r5('#2b2b33', soft=0.6)
TT_CYAN, TT_PINK, WHITE = (54, 214, 224, 255), (255, 63, 108, 255), (246, 246, 246, 255)

LIGHT = (-0.55, -0.62, 0.56)
_LN = math.sqrt(sum(c * c for c in LIGHT))


def _lit(nx, ny, nz):
    n = math.sqrt(nx * nx + ny * ny + nz * nz) or 1
    return (nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2]) / (n * _LN)


def _tone(v):                             # lighting -0..1 -> ramp index with compressed bands
    return 5 if v > 0.9 else 4 if v > 0.7 else 3 if v > 0.42 else 2 if v > 0.18 else 1


def slot_box(ox, oy, c, r, w, h):
    x0, y0 = ox + 7 + 18 * c, oy + 17 + 18 * r
    return x0, y0, x0 + 18 * w - 1, y0 + 18 * h - 1


def cast(img, solid, dx, dy, ramp):
    """Contact shadow of a part on the surface under it (that surface's own ramp): hard core + penumbra."""
    from kitchen import projected_shadow
    projected_shadow(img, solid, dx, dy, ramp=ramp)


# ------------------------------------------------------------------ the slab and its materials

def _texture(img, face, ramp, kind, box, seed):
    x0, y0, x1, y1 = box
    rnd = random.Random(seed)
    if kind == 'leather':                 # pebbled grain + a stitched border
        for (x, y) in sorted(face):
            if rnd.random() < 0.018:
                _paint(img, [p for p in ((x, y), (x + 1, y)) if p in face], ramp[2])
            elif rnd.random() < 0.008:
                _paint(img, [p for p in ((x, y), (x, y + 1)) if p in face], ramp[4])
        k = 3
        path = ([(x, y0 + k) for x in range(x0 + k, x1 - k + 1)] + [(x1 - k, y) for y in range(y0 + k + 1, y1 - k + 1)]
                + [(x, y1 - k) for x in range(x1 - k - 1, x0 + k - 1, -1)]
                + [(x0 + k, y) for y in range(y1 - k - 1, y0 + k, -1)])
        for i, p in enumerate(path):
            if i % 4 < 2 and p in face:
                _px(img, p[0], p[1], ramp[5] if (p[1] == y0 + k or p[0] == x0 + k) else ramp[4])
            elif i % 4 == 2 and p in face:
                _px(img, p[0], p[1], ramp[2])             # the stitch hole
    elif kind == 'planks':                # vertical planks with seams, grain along them, a varnish sheen
        grain(img, face, ramp, seed=seed, density=0.03, vertical=True, length=(5, 16))
        for sx in range(x0 + 9, x1, 9):
            for y in range(y0, y1 + 1):
                if (sx, y) in face:
                    _px(img, sx, y, ramp[2])
                if (sx + 1, y) in face:
                    _px(img, sx + 1, y, ramp[4])
        sheen(img, face, ramp, x0, y0, x1, y1, at=0.28, width=0.08, seed=seed)
    elif kind == 'stone':                 # chips and a few cracks with a lit lower lip
        for (x, y) in sorted(face):
            r_ = rnd.random()
            if r_ < 0.012:
                _paint(img, [p for p in ((x, y), (x + 1, y), (x, y + 1)) if p in face], ramp[2])
            elif r_ < 0.018:
                _paint(img, [p for p in ((x, y), (x + 1, y)) if p in face], ramp[4])
        for _ in range(3):
            x, y = rnd.randint(x0 + 4, x1 - 8), rnd.randint(y0 + 4, y1 - 8)
            for _ in range(rnd.randint(4, 8)):
                if (x, y) in face:
                    _px(img, x, y, ramp[1])
                    if (x + 1, y + 1) in face:
                        _px(img, x + 1, y + 1, ramp[4])
                x += 1
                y += rnd.choice((0, 0, 1, -1))
    elif kind == 'velvet':
        sheen(img, face, ramp, x0, y0, x1, y1, at=0.35, width=0.12, seed=seed)
    elif kind == 'cloth':                 # woven threads: short horizontal streaks
        for (x, y) in sorted(face):
            if y % 2 == 0 and rnd.random() < 0.03:
                _paint(img, [p for p in ((x + i, y) for i in range(3)) if p in face],
                       ramp[2] if rnd.random() < 0.6 else ramp[4])
    elif kind == 'steel':
        import safe
        safe.metal_plate(img, x0 + 1, y0 + 1, x1 - 1, y1 - 1, base=0.55, grad=0.12, sheen=0.3, seed=seed,
                         edge=0.06, brushed=0.04, sheen_at=0.25)


def slab(img, ox, oy, c, r, w, h, ramp, kind='flat', thick=3, seed=1):
    """A raised slab exactly over slots (c, r, w, h), 1 px inside them (2 px gaps between neighbours):
    soft shadow on the counter, front face, selective outline, 2 px lit bevel on the far / left edge,
    material texture. Returns (face pixels, face box)."""
    x0, y0, x1, y1 = slot_box(ox, oy, c, r, w, h)
    top = rrect(x0 + 1, y0 + 1, x1 - 1, y1 - 1 - thick, 2)
    solid, face = raised(img, top, thick, ramp, shadow_off=(2, 2), shadow_ramp=SLATE, seed=seed)
    box = (x0 + 2, y0 + 2, x1 - 2, y1 - 2 - thick)
    _texture(img, face, ramp, kind, box, seed)
    if kind != 'steel':
        ring2 = {(x, y) for x, y in face if ((x, y - 2) not in solid or (x - 2, y) not in solid)
                 and (x, y - 1) in face and (x - 1, y) in face}
        _paint(img, ring2, ramp[4])
    else:
        from safe import METAL
        for x, y in face:
            if (x, y - 1) not in face or (x - 1, y) not in face:
                _px(img, x, y, METAL[13])
    return face, box


def plaque(img, cx, y, text, under, narrow=False, pad=4, max_w=None):
    """Dark label plaque with light raised letters and two brass nails, lying on a slab (`under` = the slab's
    ramp, for the shadow). A plaque keeps >= 3 px of slab round it: if the text does not fit `max_w`, the
    letters switch to the narrow face. Returns its height."""
    if max_w and not narrow and text_width(text) + 2 * pad + 4 > max_w:
        narrow = True
    tw = text_width(text, narrow=narrow)
    th = text_height(text)
    w, h = tw + 2 * pad + 4, th + 5
    x0 = cx - w // 2
    top = rrect(x0, y, x0 + w - 1, y + h - 1, 2)
    raised(img, top, 2, PLAQUE, shadow_off=(1, 2), shadow_ramp=under)
    draw_text(img, cx - tw // 2, y + 3, text, CREAM[4], shadow=PLAQUE[0], align='center', narrow=narrow)
    for nx in (x0 + 2, x0 + w - 3):
        _px(img, nx, y + h // 2, GOLD[4])
        _px(img, nx, y + h // 2 + 1, GOLD[2])
    return h + 2


def lettering(img, x, y, text, ramp, narrow=False):
    """Light raised letters straight on a slab (one-row tiles): cream with the slab's dark tone under them -
    dark letters cut into blue cloth or steel do not read at 1:1."""
    draw_text(img, x, y, text, CREAM[4], shadow=ramp[0], narrow=narrow)


# ------------------------------------------------------------------ pictures

def coin(img, x, y, under):
    """Gold coin lying flat: 7x3 face with a rim ring and a glint, 2 px edge, shadow on the slab."""
    face = {(x + i, y + j) for j, (a, b) in enumerate(((2, 4), (0, 6), (0, 6), (2, 4))) for i in range(a, b + 1)}
    solid = face | {(px, py + k) for px, py in face for k in (1, 2)}
    cast(img, solid, 1, 1, under)
    for p in solid - face:
        _px(img, *p, GOLD[2] if (p[0], p[1] + 1) in solid else GOLD[1])
    for p in face:
        _px(img, *p, GOLD[3] if p in edge(face) else GOLD[4])
    _px(img, x + 2, y + 1, GOLD[5])
    _px(img, x + 3, y + 1, GOLD[5])
    for p in edge_ring(solid):
        lit = (p[0], p[1] + 1) in solid and (p[0], p[1] - 1) not in solid
        _px(img, *p, GOLD[1] if lit else GOLD[0])


def medallion(img, cx, cy, R, under):
    """Gold medallion: a rounded ring (lit like a torus), a sunken enamel centre with a reflection and the
    ring's shadow inside, an embossed sword on the diagonal; cast shadow on the slab."""
    disc = {(x, y) for y in range(cy - R, cy + R + 1) for x in range(cx - R, cx + R + 1)
            if (x + 0.5 - cx - 0.5) ** 2 + (y + 0.5 - cy - 0.5) ** 2 <= R * R}
    cast(img, disc, 2, 2, under)
    ri = R - 4
    for (x, y) in disc:
        dx, dy = x - cx, y - cy
        rr = math.hypot(dx, dy)
        if rr > ri:                                       # ring: torus normal
            u = max(-1.0, min(1.0, (rr - (ri + R) / 2) / ((R - ri) / 2)))
            ca, sa = (dx / rr, dy / rr) if rr else (0, 0)
            t = _tone(_lit(ca * u, sa * u, math.sqrt(max(0.0, 1 - u * u))))
            _px(img, x, y, GOLD[t])
        else:
            _px(img, x, y, ENAMEL[3])
    for (x, y) in disc:                                   # ring shadow inside the recess, reflection streak
        dx, dy = x - cx, y - cy
        rr = math.hypot(dx, dy)
        if ri - 2 < rr <= ri and (dx + dy) < 0:
            _px(img, x, y, ENAMEL[1] if rr > ri - 1 else ENAMEL[2])
        elif ri - 4 < rr <= ri - 2 and dx + dy > ri * 0.9:
            _px(img, x, y, ENAMEL[4])
    # sword from bottom-left (pommel) to top-right (tip)
    d = (1 / math.sqrt(2), -1 / math.sqrt(2))
    n = (1 / math.sqrt(2), 1 / math.sqrt(2))
    L = ri - 1
    pts = {}
    for y in range(cy - R, cy + R + 1):
        for x in range(cx - R, cx + R + 1):
            px_, py_ = x + 0.5 - cx - 0.5, y + 0.5 - cy - 0.5
            t = px_ * d[0] + py_ * d[1]
            s = px_ * n[0] + py_ * n[1]
            if -2.5 <= t <= L and abs(s) <= (1.45 if t < L - 3 else 1.45 * (L - t) / 3 + 0.2):
                pts[(x, y)] = STEEL[5] if s < -0.55 else STEEL[2] if s > 0.6 else STEEL[4]
            elif -4.0 <= t < -2.5 and abs(s) <= 4.6:
                pts[(x, y)] = GOLD[4] if s < 0 else GOLD[2]
            elif -L + 2.2 <= t < -4.0 and abs(s) <= 0.75:
                pts[(x, y)] = WALNUT[3] if s < 0 else WALNUT[2]
            elif math.hypot(t + L - 1.0, s) <= 1.7:
                pts[(x, y)] = GOLD[4]
    solid = set(pts)
    for p in edge_ring(solid):
        if p in disc and math.hypot(p[0] - cx, p[1] - cy) <= ri:
            _px(img, *p, ENAMEL[0])
    for p in {(x + 1, y + 1) for x, y in solid} - solid - edge_ring(solid):
        if p in disc and math.hypot(p[0] - cx, p[1] - cy) <= ri - 1:
            _px(img, *p, ENAMEL[1])
    for p, c in pts.items():
        _px(img, *p, c)
    for p in edge_ring(disc):                             # outline: softer on the lit side
        lit = (p[0] + p[1]) < (cx + cy)
        _px(img, *p, GOLD[1] if lit else GOLD[0])
    pixel_perfect(img, box=(cx - R - 1, cy - R - 1, cx + R + 2, cy + R + 2))   # clean 1 px rings, no doubles


def portrait(img, ox, oy, slot, under):
    """Picture frame round one slot (the player's own head item shows in it): walnut moulding with a gold
    fillet, a soft backdrop, hung on a nail by a cord. `slot` = slot index."""
    c, r = slot % 9, slot // 9
    sx, sy, sx1, sy1 = slot_box(ox, oy, c, r, 1, 1)
    x0, y0, x1, y1 = sx - 7, sy - 7, sx1 + 7, sy1 + 7
    nx, ny = (x0 + x1) // 2, y0 - 18                       # the nail
    for (ax, ay) in ((x0 + 3, y0), (x1 - 3, y0)):          # cord, 1 px, drawn before the frame
        steps = max(abs(ax - nx), abs(ay - ny))
        for i in range(steps + 1):
            x = round(nx + (ax - nx) * i / steps)
            y = round(ny + (ay - ny) * i / steps)
            _px(img, x, y, WALNUT[2])
            _px(img, x + 1, y + 1, under[2])
    _px(img, nx, ny, STEEL[4])
    _px(img, nx, ny - 1, STEEL[5])
    _px(img, nx + 1, ny, STEEL[1])
    top = rrect(x0, y0, x1, y1, 1)
    solid, face = raised(img, top, 2, WALNUT, shadow_off=(2, 2), shadow_ramp=under, lit_edges=True)
    win = {(x, y) for y in range(sy - 1, sy1 + 2) for x in range(sx - 1, sx1 + 2)}
    fil = edge_ring(win)
    for p in face:
        if p in fil:
            _px(img, *p, GOLD[4] if (p[0] < sx or p[1] < sy) else GOLD[2])
    for (x, y) in win:                                     # the picture: soft backdrop, the frame's shadow
        c_ = CANVAS[3]
        if y <= sy or x <= sx - 0:
            c_ = CANVAS[2]
        elif (x - sx) + (y - sy) < 9:
            c_ = CANVAS[4]
        _px(img, x, y, c_)


def portal(img, x0, y0, w, h, under, seed=3):
    """Nether-portal frame of obsidian blocks with a glowing swirled surface sunk inside and sparks round it."""
    x1, y1 = x0 + w - 1, y0 + h - 1
    top = rrect(x0, y0, x1, y1, 1)
    solid, face = raised(img, top, 2, OBSIDIAN, shadow_off=(2, 2), shadow_ramp=under)
    k = 5
    inner = {(x, y) for y in range(y0 + k, y1 - k + 1) for x in range(x0 + k, x1 - k + 1)}
    rnd = random.Random(seed)
    for (x, y) in face - inner:                            # block seams every 6 px, purple specks
        if ((x - x0) % 6 == 0 and (y < y0 + k or y > y1 - k)) or ((y - y0) % 6 == 0 and (x < x0 + k or x > x1 - k)):
            _px(img, x, y, OBSIDIAN[1])
        elif rnd.random() < 0.05:
            _px(img, x, y, OBSIDIAN[4] if rnd.random() < 0.7 else PORTAL[2])
    for (x, y) in inner:
        v = math.sin((x - x0) * 0.62 + (y - y0) * 0.21 + 1.8 * math.sin((y - y0) * 0.33 + (x - x0) * 0.08))
        i = 5 if v > 0.86 else 4 if v > 0.35 else 3 if v > -0.45 else 2
        _px(img, x, y, PORTAL[i])
    for (x, y) in inner:                                   # sunk: the frame's shadow on the far / left side
        if y == y0 + k or x == x0 + k:
            _px(img, x, y, PORTAL[1])
        elif y == y1 - k or x == x1 - k:
            _px(img, x, y, PORTAL[4])
    for (sx, sy) in ((x0 - 3, y0 + 6), (x1 + 3, y0 + 14), (x0 - 2, y1 - 8), (x1 + 2, y1 - 2)):
        _px(img, sx, sy, PORTAL[5])
        for dx, dy in N4:
            _px(img, sx + dx, sy + dy, PORTAL[3])


def chest(img, cx, y, under):
    """Small market chest: walnut body with a brass latch and corners, a red-and-cream striped lid."""
    x0, x1 = cx - 9, cx + 8
    lid = rrect(x0, y, x1, y + 5, 2)
    body = {(x, yy) for yy in range(y + 6, y + 12) for x in range(x0, x1 + 1)}
    solid = lid | body
    cast(img, solid, 2, 1, under)
    for (x, yy) in body:
        c_ = WALNUT[3] if yy < y + 11 else WALNUT[2]
        if yy == y + 6:
            c_ = WALNUT[1]                                 # the lid's shadow on the body
        _px(img, x, yy, c_)
    for (x, yy) in lid:
        stripe = ((x - x0) // 3) % 2 == 0
        ramp = RED if stripe else CREAM
        c_ = ramp[4] if yy == y else ramp[3] if yy < y + 4 else ramp[2]
        _px(img, x, yy, c_)
    for (x, yy) in ((x0, y + 7), (x1, y + 7), (x0, y + 10), (x1, y + 10)):
        _px(img, x, yy, GOLD[3])
    lx = cx - 1
    for j in range(4):
        _px(img, lx, y + 5 + j, GOLD[4] if j < 2 else GOLD[2])
        _px(img, lx + 1, y + 5 + j, GOLD[3] if j < 3 else GOLD[1])
    for p in edge_ring(solid):
        lit = (p[0], p[1] + 1) in solid and (p[0], p[1] - 1) not in solid
        _px(img, *p, WALNUT[1] if lit else WALNUT[0])


def sparkle(img, x, y, ramp=GOLD):
    _px(img, x, y, ramp[5])
    for dx, dy in N4:
        _px(img, x + dx, y + dy, ramp[4])
    for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)):
        _px(img, x + dx, y + dy, ramp[3])


def book(img, x, y, under):
    """Small open book lying on the slab: two cream pages with text lines, a dark gutter, the blue cover
    showing under the pages, the page stack as a front face, shadow on the slab. 13x9."""
    pages = {(x + i, y + j) for j in range(6) for i in range(13) if i != 6 or j > 0}
    stack = {(x + i, y + 6) for i in range(13)}
    cover = {(x + i, y + 7) for i in range(-1, 14)}
    solid = pages | stack | cover
    cast(img, solid, 1, 1, under)
    for (px, py) in pages:
        c_ = CREAM[4] if py == y or (px - x) in (0, 12) else CREAM[3]
        if px == x + 6:
            c_ = CREAM[1]                                  # the gutter
        _px(img, px, py, c_)
    for j in (2, 4):                                       # text lines
        for i in list(range(1, 5)) + list(range(8, 12)):
            _px(img, x + i, y + j, CREAM[2] if (i + j) % 5 else CREAM[1])
    _paint(img, stack, CREAM[2])
    _paint(img, cover, CLOTH[1])
    for p in edge_ring(solid):
        lit = (p[0], p[1] + 1) in solid and (p[0], p[1] - 1) not in solid
        _px(img, *p, CLOTH[1] if lit else CLOTH[0])


def header(img, cx, y, text, under):
    """Header sign: a thick walnut plank with gold title letters (pixfont material lettering in the GOLD
    ramp) and brass nails, sticking out above the window; shadow on the counter."""
    from pixfont import draw_material_text, material_text_size
    gold = (GOLD[0], GOLD[2], GOLD[3], GOLD[4], GOLD[5])
    tw, th = material_text_size(text, 2)
    w, h = tw + 22, th + 5
    x0 = cx - w // 2
    top = rrect(x0, y, x0 + w - 1, y + h - 1, 3)
    solid, face = raised(img, top, 3, WALNUT, shadow_off=(2, 2), shadow_ramp=under, front_grain=0.05, seed=9)
    grain(img, face, WALNUT, seed=9, density=0.04, light=0.25)
    ring2 = {(px, py) for px, py in face if ((px, py - 2) not in solid or (px - 2, py) not in solid)
             and (px, py - 1) in face and (px - 1, py) in face}
    _paint(img, ring2, WALNUT[4])
    draw_material_text(img, cx - tw // 2, y + 3, text, gold, scale=2)
    for nx in (x0 + 4, x0 + w - 5):
        _px(img, nx, y + h // 2, GOLD[5])
        _px(img, nx + 1, y + h // 2, GOLD[3])
        _px(img, nx, y + h // 2 + 1, GOLD[2])
        _px(img, nx + 1, y + h // 2 + 1, GOLD[1])


GLYPHS = {
    'discord': ("..#.....#..",
                ".#########.",
                "###########",
                "##..###..##",
                "##..###..##",
                "###########",
                ".##.....##."),
    'youtube': ("##....",
                "####..",
                "######",
                "####..",
                "##...."),
    'tiktok': ("...##..",
               "...###.",
               "...#.##",
               "...#...",
               ".###...",
               "####...",
               ".##...."),
}
KEYS = {'discord': DISCORD, 'youtube': YOUTUBE, 'tiktok': TIKTOK}


def key(img, ox, oy, slot, brand):
    """1x1 social key: a raised key in the brand colour (front face, outline, shadow) with a white logo."""
    c, r = slot % 9, slot // 9
    face, (x0, y0, x1, y1) = slab(img, ox, oy, c, r, 1, 1, KEYS[brand], 'flat')
    g = GLYPHS[brand]
    gw, gh = len(g[0]), len(g)
    gx, gy = (x0 + x1 + 1 - gw) // 2, (y0 + y1 + 1 - gh) // 2
    pts = [(gx + i, gy + j) for j, row in enumerate(g) for i, ch in enumerate(row) if ch == '#']
    if brand == 'tiktok':
        _paint(img, [(x - 1, y - 1) for x, y in pts], TT_CYAN)
        _paint(img, [(x + 1, y + 1) for x, y in pts], TT_PINK)
    else:
        _paint(img, [(x + 1, y + 1) for x, y in pts if (x + 1, y + 1) not in pts], KEYS[brand][1])
    _paint(img, pts, WHITE)


# ------------------------------------------------------------------ whole tiles

MATERIALS = {'leather': LEATHER, 'planks': MAPLE, 'stone': DEEP, 'velvet': VELVET, 'cloth': CLOTH,
             'steel': STEEL5}


def tile(img, ox, oy, c, r, w, h, material, label='', art=None, narrow=False, seed=1, head_slot=None):
    """One destination: slab + picture + label. art: medallion | portrait | portal | chest | book | None.
    Tall tiles get a plaque at the bottom; one-row tiles get engraved letters (with a book for 'book')."""
    ramp = MATERIALS[material]
    face, (x0, y0, x1, y1) = slab(img, ox, oy, c, r, w, h, ramp, material, seed=seed)
    cx = (x0 + x1 + 1) // 2
    if h == 1:
        tw = text_width(label, narrow=narrow)
        if art == 'book':
            bx = cx - (tw + 16) // 2
            book(img, bx, y0 + 2, ramp)
            lettering(img, bx + 16, y0 + 3, label, ramp, narrow)
        else:
            dark = ramp if material != 'steel' else STEEL5
            lettering(img, cx - tw // 2, y0 + 3, label, dark, narrow)
        return
    ph = text_height(label) + 7 if label else 0
    py = y1 - ph - 1
    area = (x0, y0, x1, py - 2)                          # picture area above the plaque
    ax = (area[0] + area[2] + 1) // 2
    ay = (area[1] + area[3] + 1) // 2
    if art == 'medallion':
        R = min(15, (area[3] - area[1]) // 2 - 2)
        medallion(img, ax, ay, R, ramp)
        for (kx, ky) in ((x0 + 2, ay + R - 6), (x1 - 9, y0 + 3), (x1 - 8, ay + R - 3)):
            coin(img, kx, ky, ramp)
    elif art == 'portrait':
        portrait(img, ox, oy, head_slot, ramp)
    elif art == 'portal':
        portal(img, ax - 15, area[1] + 2, 30, area[3] - area[1] - 2, ramp)
    elif art == 'chest':
        chest(img, ax, ay - 5, ramp)
        sparkle(img, x0 + 7, ay - 3)
        sparkle(img, x1 - 7, ay + 1)
    if label:
        plaque(img, cx, py, label, ramp, narrow=narrow, max_w=x1 - x0 + 1 - 6)


# ------------------------------------------------------------------ 16x16 preview stand-ins

def icon_head():
    """Generic player head (preview only - in game the slot shows the player's real head)."""
    hair, skin, eye, mouth = _r5('#5a3a22', soft=1), _r5('#d59c74', soft=1), (40, 60, 120, 255), _r5('#9a5a44')
    img = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    for y in range(1, 15):
        for x in range(1, 15):
            c_ = skin[3]
            if y <= 4 or (y <= 6 and x in (1, 2, 13, 14)):
                c_ = hair[3] if y > 1 else hair[4]
            if y == 8 and x in (4, 5, 10, 11):
                c_ = eye if x in (5, 10) else WHITE
            if y == 11 and 6 <= x <= 9:
                c_ = mouth[2]
            if x == 14 or y == 14:
                c_ = skin[2] if c_ == skin[3] else hair[2]
            img.putpixel((x, y), c_)
    for x in range(1, 15):
        img.putpixel((x, 0), hair[0])
        img.putpixel((x, 15), skin[0])
    for y in range(1, 15):
        img.putpixel((0, y), hair[0] if y < 6 else skin[0])
        img.putpixel((15, y), hair[0] if y < 6 else skin[0])
    return img


ICONS = {'head': icon_head}


def render_icon(name):
    return ICONS[name]()


if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == 'icon':
        im = render_icon(sys.argv[3] if len(sys.argv) > 3 else 'head')
        im.save(sys.argv[2])
        im.resize((256, 256), Image.NEAREST).save(sys.argv[2].replace('.png', '_zoom.png'))
    else:
        print(__doc__)
