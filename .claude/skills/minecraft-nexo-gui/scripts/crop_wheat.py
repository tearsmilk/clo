"""Wheat growth stages 0-7 (32x32, side view, transparent), hand-structured pixel art.

Usage: python3 crop_wheat.py OUT_DIR   -> OUT_DIR/wheat_stage_0..7.png
Copy and change the ramps/STAGES/BLADES/STALKS tables to make other crops (oats, rye, rice, grass).

Plant = a clump of long arching leaf blades + upright stalks that carry ears from stage 4.
Depth comes from colour (back blades darker, front lighter), not outlines.
"""
import sys, random
from PIL import Image



def C(h):
    h = h.lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)


def ramp_mix(a, b, t):
    return [tuple(int(x + (y - x) * t) for x, y in zip(p, q)) for p, q in zip(a, b)]


GREEN = [C('#1f4a2c'), C('#2f6e3a'), C('#3e8948'), C('#5cb04a'), C('#8fd45e')]
OLIVE = [C('#4a4a22'), C('#6c7a2a'), C('#93a83a'), C('#bccb52'), C('#dde27e')]
STRAW = [C('#6a4420'), C('#9a6a30'), C('#c99a48'), C('#e6c068'), C('#f6e2a0')]
EAR_G = [C('#2f6e3a'), C('#4f9a3e'), C('#78bf4c'), C('#a8dc68'), C('#d2f08e')]
EAR_Y = [C('#6c7a2a'), C('#a0a832'), C('#c8c844'), C('#e4dc68'), C('#f6f0a0')]
EAR_GOLD = [C('#8a5418'), C('#c07a22'), C('#e8a832'), C('#fbcf4e'), C('#fff08a')]

# stage: leaf (count, length), stalks (height incl. ear), ear length, leaf colour, ear colour, droop
STAGES = [
    dict(leaves=3, ll=5,  stalk=0,  ear=0, leaf=GREEN, earc=None, ripe=0),
    dict(leaves=5, ll=9,  stalk=0,  ear=0, leaf=GREEN, earc=None, ripe=0),
    dict(leaves=7, ll=13, stalk=0,  ear=0, leaf=GREEN, earc=None, ripe=0),
    dict(leaves=8, ll=16, stalk=19, ear=0, leaf=GREEN, earc=None, ripe=0),
    dict(leaves=8, ll=16, stalk=23, ear=6, leaf=GREEN, earc=EAR_G, ripe=0),
    dict(leaves=8, ll=17, stalk=26, ear=8, leaf=ramp_mix(GREEN, OLIVE, 0.3), earc=ramp_mix(EAR_G, EAR_Y, 0.6), ripe=0.3),
    dict(leaves=8, ll=17, stalk=28, ear=9, leaf=ramp_mix(OLIVE, STRAW, 0.35), earc=ramp_mix(EAR_Y, EAR_GOLD, 0.6), ripe=0.7),
    dict(leaves=8, ll=17, stalk=29, ear=9, leaf=ramp_mix(OLIVE, STRAW, 0.85), earc=EAR_GOLD, ripe=1.0),
]
# leaf blades: base x, horizontal reach (sign = side), rise factor, depth (0 back .. 1 front)
BLADES = [(15, -9, 0.75, 0.2), (17, 9, 0.75, 0.2), (14, -12, 0.55, 0.5), (18, 12, 0.55, 0.5),
          (16, -5, 0.95, 0.8), (16, 6, 0.9, 0.8), (13, -14, 0.4, 1.0), (19, 14, 0.4, 1.0)]
# stalks: base x, lean at the top, height factor, depth
STALKS = [(16, 0, 1.0, 0.6), (13, -3, 0.93, 0.3), (19, 3, 0.95, 0.3), (10, -6, 0.84, 0.9), (22, 6, 0.86, 0.9)]


def bezier(p0, p1, p2, n=80):
    pts = []
    for k in range(n + 1):
        t = k / n
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
        p = (round(x), round(y))
        if not pts or pts[-1] != p:
            pts.append(p)
    return pts


def put(px, x, y, c):
    if 0 <= x < 32 and 0 <= y < 32 and c is not None:
        px[x, y] = c


def shade_for(ramp, depth, k=0):
    # back = darker steps, front = lighter
    i = 1 + round(depth * 2) + k
    return ramp[max(0, min(len(ramp) - 1, i))]


def draw_blade(px, base_x, reach, rise, length, ramp, depth, droop):
    # arching blade: goes up, then bends outward and droops at the tip
    p0 = (base_x, 31)
    p2 = (base_x + reach * length / 17, 31 - length * rise)
    p1 = (base_x + reach * length / 17 * 0.25, 31 - length * (rise + 0.35 + 0.1 * droop))
    pts = bezier(p0, p1, p2)
    n = len(pts)
    for j, (x, y) in enumerate(pts):
        c = shade_for(ramp, depth, 1 if j > n * 0.6 else 0)   # lighter towards the tip
        put(px, x, y, c)
        if j < n * 0.3:                                     # thicker base
            put(px, x + (1 if reach > 0 else -1), y, shade_for(ramp, depth, -1))
    tx, ty = pts[-1]
    put(px, tx, ty, ramp[-1] if depth > 0.6 else ramp[-2])  # bright tip


def draw_ear(px, x, top, length, ramp, ripe, side):
    """3px-wide ear of alternating grains: lit left grains, shaded right grains, tip + awns."""
    for r in range(length):
        y = top + r
        off = side if (ripe > 0.6 and r < 3) else 0          # ripe ears droop at the tip
        cx = x + off
        put(px, cx, y, ramp[2])
        if r % 2 == 0:
            put(px, cx - 1, y, ramp[4] if r < length - 2 else ramp[3])
            put(px, cx + 1, y, ramp[1])
        else:
            put(px, cx - 1, y, ramp[3])
            put(px, cx + 1, y, ramp[2])
    put(px, x + (side if ripe > 0.6 else 0), top - 1, ramp[3])   # tip grain
    if ripe > 0.2:                                              # awns: thin bristles growing out of the ear
        tipx = x + (side if ripe > 0.6 else 0)
        length = 2 + round(ripe * 2)
        for dx in ((-1, 0, 1) if ripe > 0.5 else (-1, 1)):
            for k in range(1, length + 1):
                ax = tipx + dx * ((k + 1) // 2)
                put(px, ax, top - 1 - k, ramp[4] if k < length else ramp[3])
        # side bristles from the upper grains
        for r in (1, 3):
            put(px, tipx - 2, top + r - 1, ramp[3])
            put(px, tipx + 2, top + r - 1, ramp[3])


def stage_img(i):
    st = STAGES[i]
    im = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    px = im.load()
    stalk_ramp = ramp_mix(st['leaf'], STRAW, 0.2 + 0.6 * st['ripe']) if st['ripe'] else st['leaf']
    # back-to-front: blades by depth, stalks interleaved
    items = [('b', b) for b in BLADES[:st['leaves']]]
    if st['stalk']:
        items += [('s', s) for s in STALKS[:5 if i >= 5 else 3]]
    items.sort(key=lambda it: it[1][3])
    for kind, it in items:
        if kind == 'b':
            bx, reach, rise, depth = it
            draw_blade(px, bx, reach, rise, st['ll'] * (0.7 + 0.3 * rise), st['leaf'], depth, st['ripe'])
        else:
            sx, lean, hf, depth = it
            h = round(st['stalk'] * hf)
            pts = bezier((sx, 31), (sx, 31 - h * 0.6), (sx + lean * (0.5 + 0.5 * st['ripe']), 31 - h))
            ear_len = st['ear']
            ear_top = 31 - h
            for (x, y) in pts:
                if ear_len and y < ear_top + ear_len:
                    continue
                put(px, x, y, shade_for(stalk_ramp, depth, 0))
            if ear_len:
                tx = pts[-1][0]
                draw_ear(px, tx, ear_top + 1, ear_len, st['earc'], st['ripe'], 1 if lean >= 0 else -1)
            else:
                tx, ty = pts[-1]
                put(px, tx, ty, stalk_ramp[-1])
    return im


if __name__ == '__main__':
    OUT = sys.argv[1]
    for i in range(8):
        stage_img(i).save(f'{OUT}/wheat_stage_{i}.png')
    print('ok')
