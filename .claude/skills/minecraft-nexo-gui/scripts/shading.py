#!/usr/bin/env python3
"""Texture shading helpers (references/texture-shading.md): five-tone ramps and a quality check.

    python3 shading.py ramp5 '#5a6578' [--hue-dark 0.03 --hue-light -0.02] [--soft 1]
        Highlight / Light Midtone / Base / Dark Midtone / Shadow (+ outline), with hue and saturation shifts
    python3 shading.py demo chart.png
        5-stage shading chart (flat -> form shadow -> highlight + terminator -> reflection + bounce -> rim +
        projected shadow) on a gold sphere, a steel sphere, a glass pane, a steel cube and a steel cylinder
    python3 shading.py check texture.png [--tile] [--kit kitchen]
        flags what breaks the rules: semi-transparent pixels, too many tones per colour group, single-pixel
        noise, checker dithering used as a gradient, light direction, and with --tile the seam mismatch;
        --kit <module> counts every declared 5-tone ramp of that kit as one material (several woods / metals
        of similar hue in one texture), only colours outside the ramps are grouped by hue;
        line and form (references/pixel-art-craft.md): doubles in 1 px lines, jaggies on sprite silhouettes,
        tones in rings round the outline (pillow shading / banding), value spread
    python3 shading.py gray texture.png out.png [--scale 4]
        colour and greyscale side by side - the value test
    python3 shading.py craft chart.png
        bad / good pairs of references/pixel-art-craft.md: doubles, jaggies, inner / outer AA, pillow shading,
        banding, the value test, the eight outline styles
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


def ramp5(base, hue_dark=None, hue_light=None, outline=True, soft=0.0):
    """Five tones around `base`: [shadow, dark mid, base, light mid, highlight] (+ outline first if outline).
    Shadows turn cooler (toward blue) and a bit more saturated, highlights warmer and less saturated - unless
    hue_dark / hue_light are given (fractions of the colour wheel, + = toward higher hue).
    soft 0..1 = delicate shading: the three middle tones move close together (gentle transitions across a
    face, band compression) while shadow and highlight keep some range for definition; the hue shift stays."""
    r, g, b = [v / 255 for v in _rgb(base)]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)

    def toward(h0, target, k):
        dd = ((target - h0 + 0.5) % 1.0) - 0.5
        return (h0 + max(-k, min(k, dd))) % 1.0

    # (value, saturation factor, side): darks are fractions of the base value, lights move toward white;
    # the second set is the delicate one
    steps = [(0.48, 1.15, 'dark'), (0.74, 1.07, 'dark'), (None, 1.0, None), (0.42, 0.82, 'light'),
             (0.8, 0.55, 'light')]
    gentle = [(0.62, 1.1), (0.88, 1.04), (None, 1.0), (0.2, 0.9), (0.52, 0.66)]
    out = []
    for (k, ks, side), (kg, ksg) in zip(steps, gentle):
        hh, vv = h, v
        if side:
            amt0 = 1 - k if side == 'dark' else k
            k = k + (kg - k) * soft
            ks = ks + (ksg - ks) * soft
        if side == 'dark':
            hh = (h + hue_dark * amt0 * 2) % 1 if hue_dark is not None else toward(h, 0.66, 0.06 * amt0)
            vv = v * k
        elif side == 'light':
            hh = (h + hue_light * amt0) % 1 if hue_light is not None else toward(h, 0.13, 0.03 * amt0)
            vv = v + (1 - v) * k
        ss = max(0.0, min(1.0, s * ks))
        out.append(tuple(int(round(x * 255)) for x in colorsys.hsv_to_rgb(hh, ss, min(1.0, vv))))
    if outline:
        o = colorsys.hsv_to_rgb(toward(h, 0.66, 0.05), min(1, s * 1.2), max(0.04, v * (0.2 + 0.06 * soft)))
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


# ------------------------------------------------------------------ line and form checks
# From the pixel-art fundamentals in references/pixel-art-craft.md: doubles, jaggies, rings, value spread.
N8 = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]


def doubles(px, W, H):
    """L-corners in 1 px lines (the pixel-perfect rule): pixel P has a horizontal and a vertical neighbour of
    its own colour that touch each other diagonally, so the line stays connected without P. Skipped: pixels
    inside a 2x2 block of one colour (areas, not lines), pixels in the middle of a straight run or at a
    T-junction, right-angle corners (both arms go on straight) and 3 px L chips (texture clusters - the arms
    must go on). Returns the list of (x, y); pixel_perfect() removes them."""
    return [(x, y) for y in range(H) for x in range(W) if _is_double(px, W, H, x, y)]


def _is_double(px, W, H, x, y):
    """The doubles() test for one pixel; returns (h, v) of its L or None."""
    c = px[x, y]

    def same(qx, qy):
        return 0 <= qx < W and 0 <= qy < H and px[qx, qy] == c
    if c[3] != 255:
        return None
    nb = [(dx, dy) for dx, dy in N8 if same(x + dx, y + dy)]
    if not 2 <= len(nb) <= 3 or ((-1, 0) in nb and (1, 0) in nb) or ((0, -1) in nb and (0, 1) in nb):
        return None
    if any(all(same(x + i, y + j) for i in (0, sx) for j in (0, sy)) for sx in (-1, 1) for sy in (-1, 1)):
        return None
    hs = [d for d in nb if d[1] == 0]
    vs = [d for d in nb if d[0] == 0]
    if len(hs) != 1 or len(vs) != 1:
        return None
    h, v = hs[0][0], vs[0][1]
    if same(x + 2 * h, y) and same(x, y + 2 * v):
        return None
    A, B = (x + h, y), (x, y + v)
    if not all(any(same(q[0] + dx, q[1] + dy) and (q[0] + dx, q[1] + dy) not in ((x, y), A, B) for dx, dy in N8)
               for q in (A, B)):
        return None
    return h, v


def pixel_perfect(img, only=None, box=None, passes=3):
    """Remove doubles in place (Aseprite's pixel-perfect rule, applied to a finished image): each L-corner
    pixel of a 1 px line takes the colour of the region outside the corner (transparent for an outer
    outline). only = a set of RGBA colours to clean (e.g. the outline tones); default every dark line.
    box = (x0, y0, x1, y1) limits it to one part of a bigger picture. Pixels are fixed one by one in reading
    order (a doubled staircase becomes a clean diagonal), repeated while a pass still finds some."""
    W, H = img.size
    px = img.load()
    x0, y0, x1, y1 = box or (0, 0, W, H)
    total = 0
    for _ in range(passes):
        n = 0
        for y in range(max(0, y0), min(H, y1)):
            for x in range(max(0, x0), min(W, x1)):
                if only is not None and px[x, y] not in only:
                    continue
                hv = _is_double(px, W, H, x, y)
                if not hv:
                    continue
                h, v = hv
                out = [px[qx, qy] for qx, qy in ((x - h, y), (x, y - v), (x - h, y - v))
                       if 0 <= qx < W and 0 <= qy < H]
                out = [q for q in out if q != px[x, y]] or [(0, 0, 0, 0)]
                if only is None and out[0][3] == 255 and _lum(px[x, y]) >= 0.8 * _lum(out[0]):
                    continue                               # not a dark line
                px[x, y] = Counter(out).most_common(1)[0][0]
                n += 1
        total += n
        if not n:
            break
    return total


def _components(mask, W, H, min_px=12):
    seen, comps = set(), []
    for p in mask:
        if p in seen:
            continue
        stack, comp = [p], []
        seen.add(p)
        while stack:
            x, y = stack.pop()
            comp.append((x, y))
            for dx, dy in N8:
                q = (x + dx, y + dy)
                if q in mask and q not in seen:
                    seen.add(q)
                    stack.append(q)
        if len(comp) >= min_px:
            comps.append(comp)
    return comps


def _profile_jaggies(prof):
    """prof: outermost coordinate per row (or column) of one silhouette side, in order. The staircase is cut
    into monotone stretches; each step = (rows held, jump). A step whose slope is >= 2x or <= 0.5x BOTH
    neighbours, and is not part of a repeating pattern (2-1-2-1 is a clean straight line), is a jaggy - a
    curve should change its step lengths steadily (5-3-2-1-1-2-3-5). A lone 1 px nub or notch on a straight
    edge counts too. Returns the indices into prof where the bad runs start."""
    out = []
    runs = []                                          # [value, rows, start]
    for i, v in enumerate(prof):
        if runs and runs[-1][0] == v:
            runs[-1][1] += 1
        else:
            runs.append([v, 1, i])
    for k in range(1, len(runs) - 1):                  # a 1 px nub / notch on a straight edge
        a, b, c = runs[k - 1], runs[k], runs[k + 1]
        if b[1] == 1 and a[1] >= 2 and c[1] >= 2 and abs(a[0] - b[0]) == 1 and a[0] == c[0]:
            out.append(b[2])
    i = 0
    while i < len(runs) - 1:                           # monotone stretches of runs
        j = i
        sign = 0
        while j + 1 < len(runs):
            sg = 1 if runs[j + 1][0] > runs[j][0] else -1
            if sign and sg != sign:
                break
            sign = sg
            j += 1
        # a step held >= 6 rows or jumping >= 6 px is a straight edge meeting a corner, not part of a curve
        sl = [None if runs[k][1] >= 6 or abs(runs[k + 1][0] - runs[k][0]) >= 6
              else abs(runs[k + 1][0] - runs[k][0]) / runs[k][1] for k in range(i, j)]
        for k in range(1, len(sl) - 1):
            a, b, c = sl[k - 1], sl[k], sl[k + 1]
            if None in (a, b, c):
                continue
            ext = (b >= 2 * a and b >= 2 * c) or (b * 2 <= a and b * 2 <= c)
            periodic = (k >= 2 and sl[k - 2] == b) or (k + 2 < len(sl) and sl[k + 2] == b)
            if ext and not periodic:
                out.append(runs[i + k][2])
        i = j
    return out


def jaggies(px, W, H, min_size=20):
    """Jaggies on the outer silhouette of every sprite (8-connected opaque component at least min_size px
    wide and tall - on smaller ones 1 px guards, layer edges and stems are design, not jaggies): the left /
    right profile per row and the top / bottom profile per column. Returns [(x, y)]."""
    mask = {(x, y) for y in range(H) for x in range(W) if px[x, y][3] != 0}
    out = []
    for comp in _components(mask, W, H):
        xs_, ys_ = [x for x, _ in comp], [y for _, y in comp]
        if min(max(xs_) - min(xs_), max(ys_) - min(ys_)) < min_size:
            continue                                   # 16 px icons: 1 px guards, layers, stems are design
        rows, cols = defaultdict(list), defaultdict(list)
        for x, y in comp:
            rows[y].append(x)
            cols[x].append(y)
        ys, xs = sorted(rows), sorted(cols)
        for f in (min, max):
            prof = [f(rows[y]) for y in ys]
            out += [(prof[i], ys[i]) for i in _profile_jaggies(prof)]
            prof = [f(cols[x]) for x in xs]
            out += [(xs[i], prof[i]) for i in _profile_jaggies(prof)]
    return out


def rings(px, W, H, depth=3):
    """Tones that follow the outline: chessboard distance from transparency (outside the image counts as
    transparent), and for rings 1..depth (ring 0 = the outline) the share of the most common colour.
    Lit-from-one-side shading splits every ring into light and dark parts; pillow shading and banding make
    each ring one colour. Returns [(ring, pixels, share, colour, mean luminance)]."""
    INF = 10 ** 6
    dist = {}
    frontier = []
    for y in range(H):
        for x in range(W):
            if px[x, y][3] == 0:
                continue
            if any(not (0 <= x + dx < W and 0 <= y + dy < H) or px[x + dx, y + dy][3] == 0 for dx, dy in N8):
                dist[(x, y)] = 0
                frontier.append((x, y))
    d = 0
    while frontier and d < depth:
        d += 1
        nxt = []
        for x, y in frontier:
            for dx, dy in N8:
                q = (x + dx, y + dy)
                if 0 <= q[0] < W and 0 <= q[1] < H and px[q][3] != 0 and q not in dist:
                    dist[q] = d
                    nxt.append(q)
        frontier = nxt
    out = []
    for r in range(1, depth + 1):
        ring = [px[p][:3] for p, v in dist.items() if v == r]
        if len(ring) < 8:
            continue
        c, k = Counter(ring).most_common(1)[0]
        out.append((r, len(ring), round(k / len(ring), 2), c, round(sum(map(_lum, ring)) / len(ring))))
    return out


def gray(path, out, scale=4):
    """Colour and greyscale (luma) side by side, enlarged: the value test - if the grey half does not read,
    no colour choice will save it."""
    im = Image.open(path).convert('RGBA')
    W, H = im.size
    g = Image.new('RGBA', im.size)
    for y in range(H):
        for x in range(W):
            r, gg, b, a = im.getpixel((x, y))
            L = int(round(_lum((r, gg, b))))
            g.putpixel((x, y), (L, L, L, a))
    sheet = Image.new('RGBA', (W * 2 * scale + scale * 2, H * scale), (40, 40, 48, 255))
    sheet.alpha_composite(im.resize((W * scale, H * scale), Image.NEAREST), (0, 0))
    sheet.alpha_composite(g.resize((W * scale, H * scale), Image.NEAREST), (W * scale + scale * 2, 0))
    sheet.save(out)
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
            for step in range(3):                   # skip the outline: near-black, or much darker than the
                qx, qy = x - dx * step, y - dy * step   # next pixel inward (soft / selective outlines)
                if not (0 <= qx < W and 0 <= qy < H) or px[qx, qy][3] != 255:
                    break
                L = _lum(px[qx, qy])
                nx2, ny2 = qx - dx, qy - dy
                Ln = _lum(px[nx2, ny2]) if 0 <= nx2 < W and 0 <= ny2 < H and px[nx2, ny2][3] == 255 else L
                if L >= 30 and not (step == 0 and L < 0.62 * Ln):
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
    # line and form (references/pixel-art-craft.md)
    dbl = doubles(px, W, H)

    def dark_line(x, y):                               # an outline / crack / groove: darker than its sides
        o = [_lum(px[x + dx, y + dy]) for dx, dy in N8 if 0 <= x + dx < W and 0 <= y + dy < H
             and px[x + dx, y + dy][3] == 255 and px[x + dx, y + dy] != px[x, y]]
        return not o or _lum(px[x, y]) < 0.8 * sum(o) / len(o)
    dd = [p for p in dbl if dark_line(*p)]
    res['doubles'] = {'dark_lines': len(dd), 'other': len(dbl) - len(dd)}
    if len(dd) > max(3, len(opaque) // 2000):
        warn.append(f'{len(dd)} doubles in dark lines (L-corners in 1 px outlines / cracks, e.g. at {dd[:3]}) - '
                    'the line looks thick where it runs diagonally; remove the corner pixel')
    sprite = len(opaque) < 0.9 * W * H
    if sprite:
        jg = jaggies(px, W, H)
        res['jaggies'] = len(jg)
        if len(jg) > 2:
            warn.append(f'{len(jg)} jaggies on the silhouette (e.g. at {jg[:3]}) - look at them: on a curve the '
                        'step lengths should change steadily (5-3-2-1-1-2-3-5), no 3-1-3, no lone 1 px nub on '
                        'a straight edge (a deliberate feature is fine)')
        rg = rings(px, W, H)
        res['rings'] = [(r, n, sh) for r, n, sh, _, _ in rg]
        flat = [x for x in rg if x[2] >= 0.75]
        if len(flat) >= 2 and len({x[3] for x in flat}) >= 2:
            warn.append('tones follow the outline in rings (pillow shading / banding) - light from one side: '
                        'the top-left of each ring lighter than its bottom-right')
    lums = sorted(_lum(px[p]) for p in opaque)
    if lums:
        res['value_spread'] = round(lums[int(len(lums) * 0.95) - 1] - lums[int(len(lums) * 0.05)])
        if res['value_spread'] < 40:
            warn.append(f"value spread {res['value_spread']} - too little light/dark contrast; check it with "
                        '`shading.py gray`')
    res['warnings'] = warn
    if not quiet:
        print(f'{path}: {W}x{H}, {res["colours"]} colours, tones per group {res["tones_per_group"]}'
              + (f', kit ramps {res["kit"]["ramps_used"]}, {res["kit"]["outside"]} colours outside them'
                 if ramps else ''))
        print(f'  single pixels {res["single_pixel_ratio"]:.1%}, checker {res["checker_ratio"]:.1%}, '
              f'semi-transparent {semi}, edge luminance {res["edge_luminance"]}'
              + (f', seam {res["seam"]}' if tile else ''))
        print(f'  doubles {res["doubles"]}, value spread {res.get("value_spread")}'
              + (f', jaggies {res["jaggies"]}, rings {res["rings"]}' if sprite else ''))
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

# ------------------------------------------------------------------ pixel-art craft chart
def craft_chart(path, k=4):
    """Bad / good pairs from references/pixel-art-craft.md, labelled in Russian: doubles, jaggies, inner /
    outer anti-aliasing, pillow shading, banding, the value test and the eight outline styles."""
    from pixfont import draw_text, text_width
    CW, CH, LH = 46, 34, 9
    bg, ink = (52, 56, 68, 255), (226, 222, 210, 255)
    img = Image.new('RGBA', (CW * 8, (CH + LH) * 3), bg)
    pxl = img.load()
    fruit, leaf = ramp5('#c8402e'), ramp5('#4f9a3a')
    K = (0, 0, 0)

    def put(x, y, c):
        if 0 <= x < img.width and 0 <= y < img.height:
            pxl[x, y] = tuple(c[:3]) + (255,)

    def cell(col, row, label, base=None):
        x0, y0 = col * CW, row * (CH + LH)
        if base:
            for y in range(y0 + 1, y0 + CH - 1):
                for x in range(x0 + 1, x0 + CW - 1):
                    put(x, y, base)
        draw_text(img, x0 + (CW - text_width(label, narrow=True)) // 2, y0 + CH, label, ink, narrow=True)
        return x0, y0

    def runs_path(x, y, hs, vs, corner=False):
        pts = []
        for L in hs:                                         # horizontal runs, then one diagonal step down
            pts += [(x + i, y) for i in range(L)]
            x += L
            if corner:
                pts.append((x, y))                           # the double: an L instead of a diagonal
            y += 1
        for L in vs:
            pts += [(x, y + i) for i in range(L)]
            y += L
            if corner:
                pts.append((x, y))
            x += 1
        return pts

    # row 0: lines and anti-aliasing
    clean = ([6, 4, 3, 2, 1, 1], [1, 1, 2, 3, 4, 6])
    for col, (label, hs, vs, corner) in enumerate((('двойные', *clean, True), ('чисто', *clean, False),
                                                 ('зубцы', [6, 2, 4, 1, 3, 1], [1, 3, 1, 4, 2, 6], False),
                                                 ('плавно', *clean, False))):
        x0, y0 = cell(col, 0, label)
        for q in runs_path(x0 + 9, y0 + 4, hs, vs, corner):
            put(*q, ink)
    disc = {(x, y) for y in range(-9, 10) for x in range(-9, 10) if (x + .5) ** 2 + (y + .5) ** 2 <= 81}
    rim = {p for p in disc if any((p[0] + dx, p[1] + dy) not in disc for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))}
    steps = {p for p in rim if sum((p[0] + dx, p[1] + dy) in rim for dx, dy in N8) == 2 and
             any((p[0] + dx, p[1] + dy) in rim for dx, dy in ((1, 1), (-1, 1), (1, -1), (-1, -1)))}
    for col, (label, aa, back) in enumerate((('без AA', None, bg), ('внутр.', 'in', bg),
                                            ('внешн.', 'out', (139, 139, 139)), ('на тёмном', 'out', (16, 0, 16)))):
        x0, y0 = cell(col + 4, 0, label, back)
        cx, cy = x0 + CW // 2, y0 + CH // 2
        for (x, y) in disc:
            put(cx + x, cy + y, fruit[0] if (x, y) in rim else fruit[3])
        for (x, y) in steps:                                 # the pixel inside / outside each step corner
            ix, iy = x - (1 if x > 0 else -1), y - (1 if y > 0 else -1)
            ox, oy = x + (1 if x > 0 else -1), y + (1 if y > 0 else -1)
            if aa == 'in' and (ix, iy) in disc and (ix, iy) not in rim:
                put(cx + ix, cy + iy, fruit[2])
            if aa == 'out':                                  # blended toward slot grey - wrong elsewhere
                for q in ((ox, y), (x, oy)):
                    if q not in disc:
                        put(cx + q[0], cy + q[1], tuple((a + b) // 2 for a, b in zip(fruit[0], (139, 139, 139))))

    # row 1: shading - pillow vs light, banding vs broken bands, the value test
    def shade(col, label, tone):
        x0, y0 = cell(col, 1, label)
        cx, cy = x0 + CW // 2, y0 + CH // 2
        for (x, y) in disc:
            put(cx + x, cy + y, fruit[0] if (x, y) in rim else fruit[tone(x, y)])
    shade(0, 'подушка', lambda x, y: 2 if (x + .5) ** 2 + (y + .5) ** 2 > 42 else 3 if (x + .5) ** 2 + (y + .5) ** 2 > 14 else 4)
    shade(1, 'свет', lambda x, y: sphere5((x + .5) / 9, (y + .5) / 9, 3) or 3)
    ring_of = {}
    layer, d = set(disc), 0
    while layer:                                             # rings from the edge inward (8-neighbour erosion)
        inner = {p for p in layer if all((p[0] + dx, p[1] + dy) in layer for dx, dy in N8)}
        for p in layer - inner:
            ring_of[p] = d
        layer, d = inner, d + 1

    def band(x, y):                                          # banding: 1 px rings, same width all round
        r = ring_of[(x, y)]
        return 1 if r == 1 else 2 if r == 2 else 3 if r < 5 else 4

    def form(x, y):                                          # the shadow band widens toward the bottom-right
        r, a = ring_of[(x, y)], (x + y + 1) / 13
        w = max(0, round(1 + 2.5 * a))
        return 1 if 0 < r <= w // 2 + (a > 0.3) else 2 if r <= w else 4 if r <= 3 and a < -0.5 else 3
    shade(2, 'полосы', band)
    shade(3, 'сбиты', form)
    for col, (label, a, b) in enumerate((('один тон', (200, 60, 60), (64, 150, 64)),
                                         ('разный', (150, 40, 40), (120, 210, 110)))):
        x0, y0 = cell(col + 4, 1, label)
        for y in range(y0 + 4, y0 + CH - 4):
            for x in range(x0 + 6, x0 + CW - 6):
                c = a if x < x0 + CW // 2 else b
                if y >= y0 + CH // 2:
                    L = int(_lum(c))
                    c = (L, L, L)
                put(x, y, c)

    rnd = __import__('random').Random(3)
    for col, label in ((6, 'сироты'), (7, 'кластеры')):
        x0, y0 = cell(col, 1, label)
        for y in range(y0 + 4, y0 + CH - 4):
            for x in range(x0 + 5, x0 + CW - 5):
                put(x, y, leaf[3])
        for _ in range(26 if col == 6 else 9):
            x, y = x0 + rnd.randint(6, CW - 9), y0 + rnd.randint(5, CH - 7)
            c = leaf[4] if rnd.random() < 0.5 else leaf[2]
            for i in range(1 if col == 6 else rnd.randint(2, 4)):  # streaks along the grain, 2-4 px
                put(x + i, y, c)

    # row 2: the eight outline styles on one fruit with a leaf
    lf = {(x, y) for y in range(-14, -8) for x in range(0, 8) if ((x - 3.5) / 4) ** 2 + ((y + 11) / 2.4) ** 2 <= 1}
    styles = ('чёрный', 'двойной', 'тёмный', 'по зонам', 'светлый', 'выбор.', 'рваный', 'без')
    for col, label in enumerate(styles):
        x0, y0 = cell(col, 2, label)
        cx, cy = x0 + CW // 2 - 1, y0 + CH // 2 + 3
        body = {(x, y) for x, y in disc if (x + .5) ** 2 + (y + .5) ** 2 <= 64}
        for part, ramp in ((body, fruit), (lf, leaf)):
            for (x, y) in part:
                t = sphere5((x + .5) / 8, (y + .5) / 8, 3) if part is body else (4 if y < -11 else 3)
                put(cx + x, cy + y, ramp[t or 3])
        both = body | lf
        ring = {(x + dx, y + dy) for x, y in both for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))} - both
        for (x, y) in ring:
            lit = x + y < -2 if (x, y) not in lf else True
            own = leaf if any((x + dx, y + dy) in lf for dx, dy in N8) else fruit
            c = {'чёрный': K, 'двойной': K, 'тёмный': fruit[0], 'по зонам': own[0],
                 'светлый': own[4] if lit else own[0], 'выбор.': own[1] if lit else own[0],
                 'рваный': None if lit and x + y < -8 else own[0], 'без': None}[label]
            if c is not None:
                put(cx + x, cy + y, c)
        if label == 'двойной':                               # a light ring round the dark one (stickers, titles)
            ring2 = {(x + dx, y + dy) for x, y in ring for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))} - both - ring
            for (x, y) in ring2:
                put(cx + x, cy + y, (240, 236, 224))
    big = img.resize((img.width * k, img.height * k), Image.NEAREST)
    big.save(path)
    return path


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
        if '--soft' in a:
            kw['soft'] = float(a[a.index('--soft') + 1])
        names = ['outline', 'shadow', 'dark mid', 'base', 'light mid', 'highlight']
        for n, c in zip(names, ramp5(a[1], **kw)):
            print(f'{n:10s} {_hex(c)}')
    elif a[0] == 'demo':
        draw_demo(a[1])
        print('chart ->', a[1])
    elif a[0] == 'craft':
        print('craft chart ->', craft_chart(a[1]))
    elif a[0] == 'gray':
        print('value test ->', gray(a[1], a[2], int(a[a.index('--scale') + 1]) if '--scale' in a else 4))
    elif a[0] == 'check':
        kit = a[a.index('--kit') + 1] if '--kit' in a else None
        for p in [x for x in a[1:] if not x.startswith('--') and x != kit]:
            check(p, tile='--tile' in a, ramps=kit_ramps(kit) if kit else None)
    else:
        sys.exit(__doc__)
