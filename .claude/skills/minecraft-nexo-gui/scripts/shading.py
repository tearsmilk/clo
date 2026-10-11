#!/usr/bin/env python3
"""Texture shading helpers (references/texture-shading.md): five-tone ramps and a quality check.

    python3 shading.py ramp5 '#5a6578' [--hue-dark 0.03 --hue-light -0.02]
        Highlight / Light Midtone / Base / Dark Midtone / Shadow (+ outline), with hue and saturation shifts
    python3 shading.py demo chart.png
        5-stage shading chart (flat -> form shadow -> highlight + terminator -> reflection + bounce -> rim +
        projected shadow) on a gold sphere, a steel sphere, a glass pane, a steel cube and a steel cylinder
    python3 shading.py check texture.png [--tile] [--kit kitchen]
        flags what breaks the rules: semi-transparent pixels, too many tones per colour group, single-pixel
        noise, checker dithering used as a gradient, light direction, and with --tile the seam mismatch;
        --kit <module> counts every declared 5-tone ramp of that kit as one material (several woods / metals
        of similar hue in one texture), only colours outside the ramps are grouped by hue
"""
import colorsys
import math
import sys
from collections import Counter, defaultdict
from PIL import Image


def _rgb(c):
    c = c.lstrip('#')
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _hex(c):
    return '#%02x%02x%02x' % tuple(c[:3])


def ramp5(base, hue_dark=None, hue_light=None, outline=True):
    """Five tones around `base`: [shadow, dark mid, base, light mid, highlight] (+ outline first if outline).
    Shadows turn cooler (toward blue) and a bit more saturated, highlights warmer and less saturated - unless
    hue_dark / hue_light are given (fractions of the colour wheel, + = toward higher hue)."""
    r, g, b = [v / 255 for v in _rgb(base)]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)

    def toward(h0, target, k):
        dd = ((target - h0 + 0.5) % 1.0) - 0.5
        return (h0 + max(-k, min(k, dd))) % 1.0

    # (value, saturation factor, side): darks are fractions of the base value, lights move toward white
    steps = [(0.48, 1.15, 'dark'), (0.74, 1.07, 'dark'), (None, 1.0, None), (0.42, 0.82, 'light'),
             (0.8, 0.55, 'light')]
    out = []
    for k, ks, side in steps:
        hh, vv = h, v
        if side == 'dark':
            amt = 1 - k
            hh = (h + hue_dark * amt * 2) % 1 if hue_dark is not None else toward(h, 0.66, 0.06 * amt)
            vv = v * k
        elif side == 'light':
            hh = (h + hue_light * k) % 1 if hue_light is not None else toward(h, 0.13, 0.03 * k)
            vv = v + (1 - v) * k
        ss = max(0.0, min(1.0, s * ks))
        out.append(tuple(int(round(x * 255)) for x in colorsys.hsv_to_rgb(hh, ss, min(1.0, vv))))
    if outline:
        o = colorsys.hsv_to_rgb(toward(h, 0.66, 0.05), min(1, s * 1.2), max(0.04, v * 0.2))
        out.insert(0, tuple(int(round(x * 255)) for x in o))
    return out


def _lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def kit_ramps(name):
    """The five-tone ramps a kit module declares (lists of 6 colours: outline + 5 tones), e.g. 'kitchen'."""
    import importlib
    mod = importlib.import_module(name)
    out = []
    for k, v in vars(mod).items():
        if isinstance(v, list) and len(v) == 6 and all(isinstance(c, tuple) and len(c) >= 3 for c in v):
            out.append((k, [tuple(c[:3]) for c in v]))
    return out


def check(path, tile=False, quiet=False, ramps=None):
    """ramps = [(name, [6 colours]), ...] (kit_ramps): colours from a declared ramp are one material each and
    pass the tone count by construction; only colours outside every ramp are grouped by hue and counted."""
    im = Image.open(path).convert('RGBA')
    W, H = im.size
    px = im.load()
    opaque = [(x, y) for y in range(H) for x in range(W) if px[x, y][3] == 255]
    semi = sum(1 for y in range(H) for x in range(W) if 0 < px[x, y][3] < 255)
    res = {'size': (W, H), 'semi_transparent': semi}
    warn = []
    if semi:
        warn.append(f'{semi} semi-transparent pixels (no soft edges / anti-aliasing in pixel art)')
    cols = Counter(px[x, y][:3] for x, y in opaque)
    res['colours'] = len(cols)
    # tones per colour group: greys together, saturated colours by 30 deg hue bins
    groups = defaultdict(set)
    known = {c: n for n, r in (ramps or ()) for c in r}
    if ramps:
        used = Counter(known[c] for c in cols if c in known)
        res['kit'] = {'ramps_used': dict(used), 'outside': sum(1 for c in cols if c not in known)}
    for c in cols:
        if c in known:
            continue
        h, s, v = colorsys.rgb_to_hsv(*[q / 255 for q in c])
        if v < 0.16:
            continue                       # outlines / near-black do not count as tones
        key = 'grey' if s < 0.14 else f'hue{int(h * 12) * 30}'
        groups[key].add(c)
    res['tones_per_group'] = {k: len(v) for k, v in sorted(groups.items(), key=lambda kv: -len(kv[1]))}
    for k, v in groups.items():
        if len(v) > 7:
            warn.append(f'{len(v)} tones in colour group {k} - aim for 5 per material (+ outline)')
    # single-pixel noise: no same-coloured pixel among the 8 neighbours
    lone = 0
    for x, y in opaque:
        c = px[x, y]
        same = False
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if (dx or dy) and 0 <= x + dx < W and 0 <= y + dy < H and px[x + dx, y + dy] == c:
                    same = True
                    break
            if same:
                break
        lone += not same
    res['single_pixel_ratio'] = round(lone / max(1, len(opaque)), 3)
    if res['single_pixel_ratio'] > 0.08:
        warn.append(f"{res['single_pixel_ratio']:.0%} single pixels - use clusters (streaks, chips) instead of noise")
    # checker dithering: 3x3 windows a b a / b a b / a b a (a dithered AREA - a single 1 px diagonal line
    # also makes 2x2 a b / b a windows, but that is clean line art, not dithering)
    chk = tot = 0
    for y in range(H - 2):
        for x in range(W - 2):
            win = [px[x + i, y + j] for j in range(3) for i in range(3)]
            if all(c[3] == 255 for c in win):
                tot += 1
                a, b = win[0], win[1]
                if a != b and all(win[k] == (a if k % 2 == 0 else b) for k in range(9)):
                    chk += 1
    res['checker_ratio'] = round(chk / max(1, tot), 3)
    if res['checker_ratio'] > 0.03:
        warn.append(f"{res['checker_ratio']:.0%} checker 3x3 windows - dithered gradient; use stepped bands")
    # light direction, measured on the outer silhouette only (recesses are lit the other way on purpose):
    # for every pixel next to transparency, step inward past the outline and record the first real tone
    sides = {k: [] for k in ('top', 'bottom', 'left', 'right')}
    for x, y in opaque:
        for k, (dx, dy) in (('top', (0, -1)), ('bottom', (0, 1)), ('left', (-1, 0)), ('right', (1, 0))):
            nx_, ny_ = x + dx, y + dy
            if 0 <= nx_ < W and 0 <= ny_ < H and px[nx_, ny_][3] != 0:
                continue
            for step in range(3):
                qx, qy = x - dx * step, y - dy * step
                if not (0 <= qx < W and 0 <= qy < H) or px[qx, qy][3] != 255:
                    break
                L = _lum(px[qx, qy])
                if L >= 30:
                    sides[k].append(L)
                    break
    mean = {k: (sum(v) / len(v) if v else None) for k, v in sides.items()}
    res['edge_luminance'] = {k: (round(v) if v else None) for k, v in mean.items()}
    if mean['top'] and mean['bottom'] and mean['top'] < mean['bottom']:
        warn.append('top-facing edges are darker than bottom-facing ones - light should come from the top')
    if mean['left'] and mean['right'] and mean['left'] < mean['right'] * 0.9:
        warn.append('left-facing edges are darker than right-facing ones - check the light direction')
    if tile:
        def diff(p, q):
            return sum(abs(a - b) for a, b in zip(p[:3], q[:3])) / 3
        lr = sum(diff(px[0, y], px[W - 1, y]) for y in range(H)) / H
        tb = sum(diff(px[x, 0], px[x, H - 1]) for x in range(W)) / W
        inner = sum(diff(px[x, y], px[x + 1, y]) for y in range(H) for x in range(W - 1)) / max(1, H * (W - 1))
        res['seam'] = {'left_right': round(lr, 1), 'top_bottom': round(tb, 1), 'inner_neighbour': round(inner, 1)}
        if lr > inner * 1.6 or tb > inner * 1.6:
            warn.append('tile edges do not match - the seam will show when tiled')
        top_l = sum(_lum(px[x, y]) for y in range(H // 4) for x in range(W)) / (W * max(1, H // 4))
        bot_l = sum(_lum(px[x, y]) for y in range(H - H // 4, H) for x in range(W)) / (W * max(1, H // 4))
        if abs(top_l - bot_l) > 18:
            warn.append('the tile is brighter at one end - a directional gradient stripes a repeated tile')
    res['warnings'] = warn
    if not quiet:
        print(f'{path}: {W}x{H}, {res["colours"]} colours, tones per group {res["tones_per_group"]}'
              + (f', kit ramps {res["kit"]["ramps_used"]}, {res["kit"]["outside"]} colours outside them'
                 if ramps else ''))
        print(f'  single pixels {res["single_pixel_ratio"]:.1%}, checker {res["checker_ratio"]:.1%}, '
              f'semi-transparent {semi}, edge luminance {res["edge_luminance"]}'
              + (f', seam {res["seam"]}' if tile else ''))
        for w in warn:
            print('  warning:', w)
        if not warn:
            print('  ok')
    return res



# ------------------------------------------------------------------ light anatomy on primitives
# Tone indices into a ramp5() list: 0 outline, 1 shadow, 2 dark mid, 3 base, 4 light mid, 5 highlight.
# Concepts (references/texture-shading.md): main light from the top-left; highlight (specular spot) and a
# small reflection; light side; base; TERMINATOR = the narrow darkest band where light turns into shadow;
# volume (form) shadow, lifted by BOUNCE light from the ground; RIM light = thin light edge on the shadow
# side; projected shadow on the ground - hard edge. Bands are compressed: highlight / terminator / rim are
# narrow, base and light are wide, so the steps do not read as rings.
LIGHT = (-0.55, -0.62, 0.56)


def _norm(v):
    n = math.sqrt(sum(c * c for c in v))
    return tuple(c / n for c in v)


def sphere5(nx, ny, stage=5, light=LIGHT):
    """Tone index on a sphere at normalised position (nx, ny); stage 1 flat .. 5 full anatomy."""
    r2 = nx * nx + ny * ny
    if r2 > 1:
        return None
    if stage <= 1:
        return 3
    nz = math.sqrt(1 - r2)
    lx, ly, lz = _norm(light)
    lam = nx * lx + ny * ly + nz * lz
    if stage >= 3 and math.hypot(nx - lx * 0.55, ny - ly * 0.55) < 0.17:
        return 5                                              # highlight
    if stage >= 4 and math.hypot(nx - lx * 0.3, ny - ly * 0.3) < 0.07:
        return 5                                              # reflection next to the highlight
    if stage >= 5 and r2 > 0.8 and lam < 0.05 and (nx + ny) > 0.4:
        return 4                                              # rim light on the shadow edge
    if lam > 0.62:
        return 4
    if lam > 0.22:
        return 3
    if stage >= 3 and lam > 0.02:
        return 1                                              # terminator: narrow and darkest
    if stage >= 4 and (nx * 0.4 + ny) > 0.55:
        return 3 if stage >= 5 and r2 > 0.9 else 2            # bounce light lifts the bottom of the shadow
    return 2 if stage >= 3 else 1


def cylinder5(side, stage=5, chrome=False):
    """Tone index across a vertical cylinder, side -1 (lit edge) .. 1 (far edge). chrome: a dark reflection
    band in the middle instead of a soft terminator."""
    if stage <= 1:
        return 3
    if chrome and stage >= 3:
        if side < -0.6:
            return 4
        if side < -0.38:
            return 5
        if side < -0.1:
            return 4
        if side < 0.2:
            return 1                                          # reflection of the dark surroundings
        if side < 0.6:
            return 3
        return 4 if stage >= 4 else 3                         # bounce
    if side < -0.4:
        return 4 if stage < 3 or not (-0.62 < side < -0.5) else 5
    if side < 0.1:
        return 3
    if stage >= 3 and side < 0.3:
        return 1                                              # terminator
    if stage >= 5 and side > 0.82:
        return 3                                              # rim / bounce at the far edge
    return 2


def draw_demo(path, k=5):
    """The 5-stage shading chart (flat -> form shadow -> highlight + terminator -> reflection + bounce -> rim +
    projected shadow) for a gold sphere, a steel sphere, a glass pane, a steel cube and a steel cylinder."""
    cell = 28
    gold, steel = ramp5('#c8901e'), ramp5('#7d8aa0')
    glass = ramp5('#9fc4dc')
    img = Image.new('RGBA', (cell * 5, cell * 5), (64, 72, 86, 255))
    pxl = img.load()

    def put(x, y, c):
        if 0 <= x < img.width and 0 <= y < img.height:
            pxl[x, y] = tuple(c[:3]) + (255,)

    def shadow(cx, cy, w):                                   # projected shadow: hard edge, one dark tone
        for y in range(cy, cy + 3):
            for x in range(cx - w, cx + w + 1):
                if ((x - cx) / (w + 0.5)) ** 2 + ((y - cy - 1) / 1.6) ** 2 <= 1:
                    put(x, y, (40, 46, 56))

    for row, ramp in ((0, gold), (1, steel)):
        for st in range(1, 6):
            cx, cy, r = st * cell - cell // 2, row * cell + 13, 10
            if st == 5:
                shadow(cx + 3, cy + r - 1, 9)
            for y in range(cy - r - 1, cy + r + 2):
                for x in range(cx - r - 1, cx + r + 2):
                    nx, ny = (x - cx + 0.5) / r, (y - cy + 0.5) / r
                    t = sphere5(nx, ny, st)
                    if t is not None:
                        edge = math.hypot(nx, ny) > 1 - 1.2 / r
                        put(x, y, ramp[0] if edge else ramp[t])
    for st in range(1, 6):                                   # glass pane: pale fill, outline, diagonal streaks
        x0, y0 = (st - 1) * cell + 4, 2 * cell + 4
        for y in range(y0, y0 + 20):
            for x in range(x0, x0 + 20):
                e = x in (x0, x0 + 19) or y in (y0, y0 + 19)
                t = 3
                if st >= 2 and not e:
                    t = 4 if (y - y0) < 3 or (x - x0) < 3 else 2 if (y - y0) > 16 or (x - x0) > 16 else 3
                if st >= 4 and not e:
                    dd = (x - x0) + (y - y0)
                    if 12 <= dd <= 14 or 18 <= dd <= 19:
                        t = 5 if st >= 5 and dd in (13, 18) else 4
                if st >= 3 and not e and (x - x0, y - y0) in ((2, 2), (3, 2), (2, 3)):
                    t = 5
                put(x, y, glass[1] if e else glass[t])
    for st in range(1, 6):                                   # steel cube: one tone per face, lit edges, AO
        cx, y0 = (st - 1) * cell + 14, 3 * cell + 3
        if st == 5:
            shadow(cx + 3, y0 + 21, 10)
        pts = {}
        for y in range(y0, y0 + 22):
            for x in range(cx - 10, cx + 11):
                dx, dy = x - cx, y - y0
                if abs(dx) * 0.5 <= dy <= 10 - abs(dx) * 0.5:
                    pts[(x, y)] = ('top', dx, dy)
                elif 10 - abs(dx) * 0.5 < dy <= 21 - abs(dx) * 0.5:
                    pts[(x, y)] = ('left' if dx < 0 else 'right', dx, dy)
        for (x, y), (face, dx, dy) in pts.items():
            edge = any((x + ex, y + ey) not in pts for ex, ey in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if st == 1:
                t = 3
            else:
                t = {'top': 4, 'left': 3, 'right': 2}[face]
                if face == 'top' and st >= 3 and dx < 0 and abs(dy - abs(dx) * 0.5) < 0.6:
                    t = 5                                          # lit upper-left edge of the top face
                if face != 'top' and st >= 3 and dy - (10 - abs(dx) * 0.5) < 1:
                    t = 5 if face == 'left' else 3                 # where the side faces meet the top
                if face == 'left' and st >= 3 and dx == -1:
                    t = 4                                          # lit vertical front edge
                u = -dx / 10 if face == 'left' else dx / 10       # 0 front edge .. 1 outer edge
                w = (dy - (10 - abs(dx) * 0.5)) / 11              # 0 top .. 1 bottom of the side face
                if st >= 4 and face == 'left' and abs(u - (0.75 - 0.5 * w)) < 0.08:
                    t = 4                                          # reflection stripe
                if st >= 5 and face == 'left' and abs(u - (0.45 - 0.5 * w)) < 0.04:
                    t = 5
                if st >= 4 and face == 'right' and abs(u - (0.7 - 0.5 * w)) < 0.08:
                    t = 3
                if st >= 5 and face != 'top' and w > 0.86:
                    t = max(1, t - 1)                              # ambient occlusion at the ground
            put(x, y, steel[0] if edge else steel[t])
    for st in range(1, 6):                                   # steel cylinder: cap ellipse, chrome body
        cx, y0 = (st - 1) * cell + 14, 4 * cell + 3
        if st == 5:
            shadow(cx + 3, y0 + 21, 9)
        pts = {}
        for y in range(y0, y0 + 23):
            for x in range(cx - 9, cx + 10):
                dx = (x - cx + 0.5) / 8.5
                if abs(dx) > 1:
                    continue
                cap_y = y0 + 3 + 3 * math.sqrt(max(0.0, 1 - dx * dx))         # front edge of the top ellipse
                bot_y = y0 + 18 + 3 * math.sqrt(max(0.0, 1 - dx * dx))
                if (y - y0 - 3) ** 2 / 9 + dx * dx <= 1 and y <= cap_y:
                    pts[(x, y)] = ('cap', dx, y)
                elif y0 + 3 <= y <= bot_y:
                    pts[(x, y)] = ('body', dx, y)
        for (x, y), (part, dx, yy) in pts.items():
            edge = any((x + ex, y + ey) not in pts for ex, ey in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if part == 'cap':
                t = 3 if st == 1 else 4
                front = y >= y0 + 3 + 3 * math.sqrt(max(0.0, 1 - dx * dx)) - 0.8
                if st >= 3 and front:
                    t = 5 if dx < 0.3 else 3                       # lit rim of the cap
            else:
                t = cylinder5(dx, st, chrome=True)
                if st >= 5 and y >= y0 + 17 + 3 * math.sqrt(max(0.0, 1 - dx * dx)):
                    t = max(1, t - 1)                              # ambient occlusion at the ground
            put(x, y, steel[0] if edge else steel[t])
    img.resize((img.width * k, img.height * k), Image.NEAREST).save(path)

if __name__ == '__main__':
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if a[0] == 'ramp5':
        kw = {}
        if '--hue-dark' in a:
            kw['hue_dark'] = float(a[a.index('--hue-dark') + 1])
        if '--hue-light' in a:
            kw['hue_light'] = float(a[a.index('--hue-light') + 1])
        names = ['outline', 'shadow', 'dark mid', 'base', 'light mid', 'highlight']
        for n, c in zip(names, ramp5(a[1], **kw)):
            print(f'{n:10s} {_hex(c)}')
    elif a[0] == 'demo':
        draw_demo(a[1])
        print('chart ->', a[1])
    elif a[0] == 'check':
        kit = a[a.index('--kit') + 1] if '--kit' in a else None
        for p in [x for x in a[1:] if not x.startswith('--') and x != kit]:
            check(p, tile='--tile' in a, ramps=kit_ramps(kit) if kit else None)
    else:
        sys.exit(__doc__)
