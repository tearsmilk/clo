#!/usr/bin/env python3
"""Measure a reference GUI image instead of eyeballing it (use before rebuilding a menu "1 in 1").

    python3 ref_tools.py palette REF.png                 colours by frequency (hex, count) - reuse them exactly
    python3 ref_tools.py window REF.png                  find the chest window: slot pitch, first slot box,
                                                         window origin, rows, and the spec `canvas` margins
    python3 ref_tools.py charmap REF.png X0 Y0 X1 Y1     one letter per pixel + legend: read shapes, stripe
                                                         orders and exact offsets of frames, brackets, slots
    python3 ref_tools.py boxes REF.png [--min 12]        bounding boxes of the separate opaque parts outside the
                                                         window (banners, crystals, ornaments) in window coords
    python3 ref_tools.py compare REF.png OURS.png OUT.png   side-by-side + diff mask + % of equal pixels

Coordinates printed by `window`/`boxes` are window-relative (what spec `box` values use), so a layer can be
placed exactly where the reference has it. Measure positions, sizes, stripe orders and colours - then draw
the parts with the builder (own art), do not paste pixels from third-party images.
"""
import sys
from collections import Counter, deque
from PIL import Image, ImageChops

LETTERS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@$%&*+=?'


def load(p):
    return Image.open(p).convert('RGBA')


def hexc(c):
    return '#%02x%02x%02x' % c[:3]


def palette(p, n=40):
    im = load(p)
    c = Counter(px[:3] for px in im.getdata() if px[3] > 0)
    for col, k in c.most_common(n):
        print(f'{hexc(col)}  {k}')


def window(p):
    """Find the chest window from the slot grid: the top-left 18x18 block that repeats to the right (9 columns,
    or fewer for packs that only paint some slots) and at least once 18px below. Window = box - (7, 17) for a
    full row; for a narrower grid every column offset is listed (centred grids are the usual case)."""
    im = load(p)
    W, H = im.size
    raw = im.tobytes()
    stride = W * 4

    def block(x, y):
        return b''.join(raw[(y + j) * stride + x * 4:(y + j) * stride + (x + 18) * 4] for j in range(18))

    def run(x, y):
        b0 = block(x, y)
        if b0[3::4].count(0) > 100 or y + 36 > H or block(x, y + 18) != b0:
            return 0
        n = 1
        while x + 18 * (n + 1) <= W and block(x + 18 * n, y) == b0:
            n += 1
        return n

    best = None
    for y in range(0, H - 36):
        for x in range(0, W - 54):
            o = y * stride + x * 4
            first = raw[o:o + 72]
            if first[3::4].count(0) == 18 or raw[o + 72:o + 144] != first or raw[o + 144:o + 216] != first:
                continue
            n = run(x, y)
            if n >= 3 and (best is None or n > best[2]):
                best = (x, y, n)
        if best and best[2] == 9:
            break
    if not best:
        print('no grid of identical 18px slots found - read the slots with charmap')
        return
    gx, gy, n = best
    print(f'first slot box at ({gx}, {gy}), {n} columns wide')
    cands = range(0, 10 - n) if n < 9 else [0]
    for c0 in cands:
        wx = gx - 7 - 18 * c0
        tag = '  <- centred' if n < 9 and c0 == (9 - n) // 2 else ''
        print(f'  if it starts at column {c0}: window x = {wx}, canvas left {wx}, right {W - wx - 176}{tag}')
    print(f'  window y = {gy - 17} - 18*row (row of that first slot: try the one that puts the frame top at the'
          f' window top); art bbox {im.getbbox()}')
    print('if the grid is the PLAYER inventory (scene menus), the window top is gy - (18*rows + 30).')
    print('check with charmap: container rows at window y 17+18r, player inventory at 18*rows+30, hotbar at '
          '18*rows+88 - references are sometimes 1px off; keep the vanilla positions.')


def charmap(p, x0, y0, x1, y1):
    im = load(p)
    px = im.load()
    legend = {}
    for y in range(y0, y1):
        line = []
        for x in range(x0, x1):
            c = px[x, y]
            if c[3] == 0:
                line.append('.')
                continue
            k = hexc(c)
            if k not in legend:
                legend[k] = LETTERS[len(legend) % len(LETTERS)]
            line.append(legend[k])
        print(f'{y:4d} ' + ''.join(line))
    print('legend:', ', '.join(f'{v}={k}' for k, v in legend.items()))


def boxes(p, wx, wy, ww, wh, min_size=12):
    """Connected opaque parts outside the window rectangle (8-connected), window-relative."""
    im = load(p)
    px = im.load()
    W, H = im.size
    seen = set()
    out = []
    inside = lambda x, y: wx <= x < wx + ww and wy <= y < wy + wh
    for y in range(H):
        for x in range(W):
            if (x, y) in seen or px[x, y][3] == 0 or inside(x, y):
                continue
            q = deque([(x, y)])
            seen.add((x, y))
            xs, ys = [x], [y]
            while q:
                cx, cy = q.popleft()
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < W and 0 <= ny < H and (nx, ny) not in seen and px[nx, ny][3] and \
                                not inside(nx, ny):
                            seen.add((nx, ny))
                            q.append((nx, ny))
                            xs.append(nx)
                            ys.append(ny)
            if len(xs) >= min_size:
                out.append((min(xs) - wx, min(ys) - wy, max(xs) - min(xs) + 1, max(ys) - min(ys) + 1, len(xs)))
    for b in sorted(out, key=lambda b: (b[1], b[0])):
        print('box [x, y, w, h] = [%d, %d, %d, %d]  (%d px)' % b)


def compare(a, b, out):
    A, B = load(a), load(b)
    W, H = max(A.width, B.width), max(A.height, B.height)
    A2 = Image.new('RGBA', (W, H)); A2.paste(A, (0, 0))
    B2 = Image.new('RGBA', (W, H)); B2.paste(B, (0, 0))
    diff = ImageChops.difference(A2, B2).convert('L').point(lambda v: 255 if v > 24 else 0)
    same = 100 * (1 - diff.histogram()[255] / (W * H))
    k = 3
    canvas = Image.new('RGBA', (W * 3 * k + 40, H * k), (20, 16, 24, 255))
    canvas.alpha_composite(A2.resize((W * k, H * k), Image.NEAREST), (0, 0))
    canvas.alpha_composite(B2.resize((W * k, H * k), Image.NEAREST), (W * k + 20, 0))
    red = Image.new('RGBA', (W, H), (255, 0, 80, 255))
    ov = A2.copy()
    ov.paste(red, (0, 0), diff)
    canvas.alpha_composite(ov.resize((W * k, H * k), Image.NEAREST), (2 * W * k + 40, 0))
    canvas.save(out)
    print(f'{same:.1f}% of pixels match (diff in red, right)')


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    cmd = a[0]
    if cmd == 'palette':
        palette(a[1])
    elif cmd == 'window':
        window(a[1])
    elif cmd == 'charmap':
        charmap(a[1], *map(int, a[2:6]))
    elif cmd == 'boxes':
        args = [x for x in a[2:] if not x.startswith('--')]
        mn = int(a[a.index('--min') + 1]) if '--min' in a else 12
        if len(args) >= 4:
            boxes(a[1], *map(int, args[:4]), min_size=mn)
        else:
            sys.exit('boxes REF.png WX WY WW WH [--min N]  (window rect from `window`/charmap)')
    elif cmd == 'compare':
        compare(a[1], a[2], a[3])
    else:
        sys.exit(__doc__)
