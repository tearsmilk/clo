#!/usr/bin/env python3
"""Turn a TTF / OTF font into a clean pixel font: every glyph rasterised by AREA COVERAGE at an exact cap
height (rendered k times larger with antialiasing, each target pixel on when >= `threshold` of its k x k
block is covered), baseline on the pixel grid, then cleaned: lone pixels removed, 1 px pinholes filled.
Missing Cyrillic is built from the font's own Latin where the shapes match (lookalikes, mirrors, a capital
shrunk to x-height for lowercase) - the rest is reported as missing.

    python3 font_pixel.py FONT.otf OUT_DIR --cap 16 [--threshold 0.45] [--name title] [--ns hokaria]
    python3 font_pixel.py FONT.otf OUT_DIR --cells 16,32 [--method auto|mono|coverage]
        fixed-cell font textures (16x16 / 32x32 per character, the biggest cap height that fits a cell with
        marks and descenders; mono = FreeType's hinted 1-bit rasteriser - thinner, compare if a font
        looks broken with the default coverage)

OUT_DIR gets: glyphs/ (one PNG per character), font.json (metrics: advance, baseline, size), sheet.png +
preview.png (look at them), and a Minecraft bitmap-font provider for the resource pack -
pack/assets/<ns>/font/<name>.json + pack/assets/<ns>/textures/font/<name>.png - so the font can be used in
titles / lore with MiniMessage `<font:<ns>:<name>>Текст</font>`. `font_pixel.text_mask(font_dir, text)`
returns a set of pixels for lettering.volume(..., mask=...).

Fonts have licences: check the README / licence before using a converted font on a server (many free fonts
are "personal use only"; a server with a shop is commercial). Never commit third-party fonts or their
converted glyphs into the skill or the repo - keep them in the user's pack.
"""
import json
import os
import sys
from PIL import Image, ImageDraw, ImageFont

LATIN = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!?.,:;-+()&\'"/'
CYR_UP = 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ'
CYR_LOW = 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'
# Cyrillic from Latin: same shape, mirrored, or with a mark (rule, source)
FROM_LATIN = {
    'А': ('same', 'A'), 'В': ('same', 'B'), 'Е': ('same', 'E'), 'Ё': ('dots', 'E'), 'З': ('same', '3'),
    'И': ('mirror', 'N'), 'Й': ('breve', 'И'), 'К': ('same', 'K'), 'Н': ('same', 'H'),
    'О': ('same', 'O'), 'Р': ('same', 'P'), 'С': ('same', 'C'), 'Т': ('same', 'T'), 'У': ('same', 'Y'),
    'Х': ('same', 'X'), 'Э': ('mirror_bar', 'C'), 'Я': ('mirror', 'R'),
    'а': ('same', 'a'), 'е': ('same', 'e'), 'ё': ('dots', 'e'), 'о': ('same', 'o'), 'р': ('same', 'p'),
    'с': ('same', 'c'), 'у': ('same', 'y'), 'х': ('same', 'x'),
}


def _has(font, ch):
    miss = font.getmask('')
    m = font.getmask(ch)
    return m.getbbox() is not None and (m.size != miss.size or bytes(m) != bytes(miss))


def _rasterize_mono(font_small, ch, base, height):
    """One glyph with FreeType's own 1-bit rasteriser (hinted): often cleaner than coverage at small sizes."""
    adv = font_small.getlength(ch)
    W = int(adv) + 6
    im = Image.new('L', (W, height), 0)
    d = ImageDraw.Draw(im)
    d.fontmode = '1'
    d.text((2, base), ch, font=font_small, fill=255, anchor='ls')
    px = im.load()
    return {(x, y) for y in range(height) for x in range(W) if px[x, y] > 127}, max(1, round(adv))


def _rasterize(font_big, ch, k, threshold, base_big, height):
    """One glyph at target size: coverage per k x k block. base_big = baseline y in the big canvas."""
    adv = font_big.getlength(ch)
    W = int(adv / k) + 6
    big = Image.new('L', (W * k, height * k), 0)
    d = ImageDraw.Draw(big)
    d.text((2 * k, base_big), ch, font=font_big, fill=255, anchor='ls')
    small = big.resize((W, height), Image.BOX)              # mean of each k x k block = coverage
    px = small.load()
    on = {(x, y) for y in range(height) for x in range(W) if px[x, y] >= threshold * 255}
    return on, max(1, round(adv / k))


def clean(on, smooth=False):
    """Remove lone pixels, fill pinholes (a pixel off with all four neighbours on). smooth=True (big sizes)
    also fills 1 px notches in an edge (3 of 4 neighbours on) and cuts 1 px bumps (1 neighbour) - the
    serrated edges coverage leaves on curves."""
    n4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
    on = {p for p in on if any((p[0] + dx, p[1] + dy) in on for dx, dy in n4 + ((1, 1), (-1, -1), (1, -1), (-1, 1)))}
    xs = [x for x, _ in on] or [0]
    ys = [y for _, y in on] or [0]
    need = 3 if smooth else 4
    for y in range(min(ys), max(ys) + 1):
        for x in range(min(xs), max(xs) + 1):
            if (x, y) not in on and sum((x + dx, y + dy) in on for dx, dy in n4) >= need:
                on.add((x, y))
    if smooth:
        on = {p for p in on if sum((p[0] + dx, p[1] + dy) in on for dx, dy in n4) >= 2}
    return on


def _mirror(on):
    xs = [x for x, _ in on]
    a, b = min(xs), max(xs)
    return {(a + b - x, y) for x, y in on}


# ------------------------------------------------------------------ Cyrillic from the font's own parts
# Generic recipes: the missing capitals are put together from parts of the font's Latin glyphs (stems, bars,
# bowls, arms), so stroke weight, flares and spurs stay the font's own. They work on any Latin font with
# a stem on the left of H / B / F / K / P / U; check the preview and fix single letters by hand if needed.

def _rows(G):
    out = {}
    for x, y in G:
        out.setdefault(y, []).append(x)
    return {y: sorted(v) for y, v in out.items()}


def _runs(xs):
    runs, start = [], xs[0]
    for a, b in zip(xs, xs[1:] + [None]):
        if b != a + 1:
            runs.append((start, a))
            start = b
    return runs


def _box(G):
    xs, ys = [x for x, _ in G], [y for _, y in G]
    return min(xs), min(ys), max(xs), max(ys)


def _stem_right(G):
    """Right edge of the left stem: median end of the first run over the middle rows."""
    x0, y0, x1, y1 = _box(G)
    r = _rows(G)
    ends = [_runs(r[y])[0][1] for y in range(y0 + 2, y1 - 2) if y in r]
    return max(set(ends), key=lambda v: (ends.count(v), -v))   # the most common edge: arms / bars do not move it


def _right_stem_left(G):
    x0, y0, x1, y1 = _box(G)
    r = _rows(G)
    st = [_runs(r[y])[-1][0] for y in range(y0 + 2, y1 - 2) if y in r]
    return max(set(st), key=lambda v: (st.count(v), v))


def _shift(G, dx, dy=0):
    return {(x + dx, y + dy) for x, y in G}


def _norm(G):
    x0 = min(x for x, _ in G)
    return _shift(G, -x0)


def _soft_sign(B):                                      # Ь: B without its upper bowl
    x0, y0, x1, y1 = _box(B)
    sr = _stem_right(B)
    r = _rows(B)
    solid = [y for y in range(y0 + 2, y1 - 1) if y in r and len(_runs(r[y])) == 1 and len(r[y]) > sr + 3]
    if not solid:
        return B
    waist = min(solid, key=lambda y: abs(y - (y0 + y1) / 2))   # the join between the bowls
    while waist - 1 in solid:
        waist -= 1
    return {(x, y) for x, y in B if y >= waist or x <= sr + 1}


def _stem_left(G):
    x0, y0, x1, y1 = _box(G)
    r = _rows(G)
    st = [r[y][0] for y in range(y0 + 2, y1 - 2) if y in r]
    return max(set(st), key=lambda v: (st.count(v), v))


def _top_bar(G, x_from, x_to, rows=2, skip=1):
    _, y0, _, _ = _box(G)
    return {(x, y) for y in range(y0 + skip, y0 + skip + rows) for x in range(x_from, x_to + 1)}


def _tail(G, rows=3):
    x0, y0, x1, y1 = _box(G)
    return {(x1, y1 + 1), (x1 - 1, y1 + 1), (x1, y1 + 2), (x1 - 1, y1 + 2)} | ({(x1, y1 + 3)} if rows > 2 else set())


def cyrillic_from_parts(g):
    """g: char -> pixel set of the Latin glyphs at one size. Returns char -> pixel set for the missing capitals."""
    out = {}
    g = {c: _norm(v) for c, v in g.items() if v}         # every part starts at x = 0
    need = lambda *cs: all(c in g and g[c] for c in cs)
    try:
        if need('F'):                                       # Г: F without the middle arm
            F = g['F']
            x0, y0, x1, y1 = _box(F)
            sr = _stem_right(F)
            r = _rows(F)
            bar = 0
            while y0 + bar in r and r[y0 + bar][-1] > sr + 2:
                bar += 1
            sl = _stem_left(F)
            out['Г'] = {(x, y) for x, y in F if sl <= x <= sr or y < y0 + max(bar, 2) or y > y1 - 3}
    except (ValueError, IndexError, KeyError):   # a part not found at this size: skip the letter
        pass
    try:
        if need('H'):                                       # П: H without the crossbar, with a top bar
            H = g['H']
            x0, y0, x1, y1 = _box(H)
            sr, rs = _stem_right(H), _right_stem_left(H)
            P = {(x, y) for x, y in H if x <= sr or x >= rs or (y > y1 - 2 and not (sr + 1 < x < rs - 1))}
            P |= _top_bar(H, x0, x1 - 1, rows=3, skip=0)
            out['П'] = P
            bx0, _, bx1, by1 = _box(P)                      # Д: П on a base with feet
            D = {(x, y) for x, y in P if y < by1 - 1}
            D |= {(x, y) for y in (by1 - 1, by1) for x in range(bx0 - 1, bx1 + 2)}
            D |= {(bx0 - 1, by1 + 1), (bx0 - 1, by1 + 2), (bx1 + 1, by1 + 1), (bx1 + 1, by1 + 2)}
            out['Д'] = _norm(D)
            L = set()                                       # Л: the left leg of П bends out to the left
            mid = (y0 + by1) // 2
            for x, y in P:
                if x <= sr + 1 and y > mid:
                    L.add((x - (y - mid + 2) // 3, y))
                else:
                    L.add((x, y))
            out['Л'] = _norm(L)
            # М: blackletter M is an uncial "m" that Russian readers take for "т" - two stems of H moved
            # apart (H's gap is too narrow for a V) joined by a V: left diagonal 2 px, right 1 px (broad pen)
            wide = 4
            left = {(x, y) for x, y in H if x <= sr or (y > y1 - 2 and x <= sr + 1)}
            right = _shift({(x, y) for x, y in H if x >= rs or (y > y1 - 2 and x >= rs - 1)}, wide)
            stems = left | right
            a_, b_ = sr + 1, rs + wide - 1
            cx, vb = (a_ + b_) / 2, y0 + round((y1 - y0) * 0.55)
            V = set()
            for y in range(y0 + 1, vb + 1):
                t = (y - y0 - 1) / max(1, vb - y0 - 1)
                xl = round(a_ + (cx - a_) * t)
                xr = round(b_ - (b_ - cx) * t)
                V |= {(xl, y), (xl + 1, y), (xr, y)}
            out['М'] = stems | V
    except (ValueError, IndexError, KeyError):   # a part not found at this size: skip the letter
        pass
    try:
        if need('B'):
            Sg = _soft_sign(g['B'])
            out['Ь'] = Sg
            x0, y0, x1, y1 = _box(Sg)
            out['Б'] = Sg | _top_bar(Sg, x0, x1 - 1, rows=2, skip=1)
            a = 3
            out['Ъ'] = _shift(Sg, a) | {(x, y) for y in (y0 + 1, y0 + 2) for x in range(0, a + 2)}
            if need('I'):
                out['Ы'] = Sg | _shift(_norm(g['I']), x1 + 2)
    except (ValueError, IndexError, KeyError):   # a part not found at this size: skip the letter
        pass
    try:
        if need('K'):                                       # Ж: mirrored K arms + stem + K arms
            K = g['K']
            sr = _stem_right(K)
            arms = _norm({(x, y) for x, y in K if x > sr})
            stem = {(x, y) for x, y in K if x <= sr}
            aw = max(x for x, _ in arms)
            out['Ж'] = {(aw - x, y) for x, y in arms} | _shift(stem, aw + 1) | _shift(arms, aw + 2 + sr)
    except (ValueError, IndexError, KeyError):   # a part not found at this size: skip the letter
        pass
    try:
        if need('U'):
            U = g['U']
            x0, y0, x1, y1 = _box(U)
            sr, rs = _stem_right(U), _right_stem_left(U)
            Sh = U | _shift({(x, y) for x, y in U if x > sr}, x1 - sr)
            out['Ш'] = Sh
            out['Щ'] = Sh | _tail(Sh)
            out['Ц'] = U | _tail(U)
            mid = (y0 + y1) // 2 + 1                        # Ч: left stem stops at the middle, joined by a bar
            Ch = {(x, y) for x, y in U if x >= rs - 1 or y <= mid}
            Ch |= {(x, y) for y in (mid - 1, mid) for x in range(x0 + 1, rs)}
            out['Ч'] = Ch
    except (ValueError, IndexError, KeyError):   # a part not found at this size: skip the letter
        pass
    try:
        if need('P'):                                       # Ф: bowls of P on both sides of its stem
            P = g['P']
            sr = _stem_right(P)
            r = _rows(P)
            bowl_bot = max(y for y in r if r[y][-1] > sr + 1)
            bowl = _norm({(x, y) for x, y in P if x > sr and y <= bowl_bot})
            stem = _norm({(x, y) for x, y in P if x <= sr + 1})
            bw = max(x for x, _ in bowl)
            sw = max(x for x, _ in stem)
            out['Ф'] = {(bw - x, y) for x, y in bowl} | _shift(stem, bw) | _shift(bowl, bw + sw - 1)
    except (ValueError, IndexError, KeyError):   # a part not found at this size: skip the letter
        pass
    try:
        if need('I', 'O'):                                  # Ю: stem, short bar, O
            I_ = _norm(g['I'])
            iw = max(x for x, _ in I_)
            x0, y0, x1, y1 = _box(I_)
            mid = (y0 + y1) // 2
            out['Ю'] = I_ | {(x, y) for y in (mid, mid + 1) for x in (iw + 1, iw + 2)} | _shift(_norm(g['O']), iw + 2)
    except (ValueError, IndexError, KeyError):   # a part not found at this size: skip the letter
        pass
    return out


def build(font_path, cap=16, threshold=0.45, k=8, chars=LATIN + CYR_UP + CYR_LOW, _small=True, method='coverage'):
    probe = ImageFont.truetype(font_path, 400)
    hb = probe.getbbox('H', anchor='ls')
    cap_ratio = (hb[3] - hb[1]) / 400                        # cap height / font size
    size_big = round(cap * k / cap_ratio)
    font_big = ImageFont.truetype(font_path, size_big)
    font_small = ImageFont.truetype(font_path, max(4, round(cap / cap_ratio)))
    asc, desc = font_big.getmetrics()
    above = max(cap + 4, round(asc / k) + 1)
    height = above + max(4, round(desc / k) + 1)
    base_big = above * k
    xb = font_big.getbbox('x', anchor='ls')
    xh = round((xb[3] - xb[1]) / k)
    glyphs, missing, built = {}, [], []
    for ch in chars:
        if _has(font_big, ch):
            if method == 'mono':
                on, adv = _rasterize_mono(font_small, ch, above, height)
            else:
                on, adv = _rasterize(font_big, ch, k, threshold, base_big, height)
            glyphs[ch] = (clean(on, smooth=cap >= 18), adv)
    for ch, (rule, src) in FROM_LATIN.items():
        if ch in glyphs or ch not in chars or src not in glyphs:
            continue
        on, adv = glyphs[src]
        on = set(on)
        top = min(y for _, y in on)
        xs = [x for x, _ in on]
        mid = (min(xs) + max(xs)) // 2
        if rule in ('mirror', 'mirror_bar'):
            on = _mirror(on)
        if rule == 'mirror_bar':                              # Э: a bar to the bowl's middle
            ym = (top + above) // 2
            on |= {(x, ym) for x in range(mid - 2, max(xs) - 1)} | {(x, ym - 1) for x in range(mid - 1, max(xs) - 1)}
        if rule == 'dots':
            on |= {(mid - 2, top - 3), (mid - 2, top - 2), (mid + 1, top - 3), (mid + 1, top - 2)}
        if rule == 'breve':
            on |= {(mid - 2, top - 3), (mid - 1, top - 2), (mid, top - 2), (mid + 1, top - 3)}
        glyphs[ch] = (on, adv)
        built.append(ch)
    for ch, on in cyrillic_from_parts({c: v[0] for c, v in glyphs.items()}).items():
        if ch in chars and ch not in glyphs:
            glyphs[ch] = (on, max(x for x, _ in on) + 2)
            built.append(ch)
    if _small and any(c in chars for c in CYR_LOW):     # lowercase Cyrillic = the capitals drawn at x-height
        sm = build(font_path, cap=xh, threshold=threshold, k=k, chars=LATIN + CYR_UP, _small=False, method=method)
        dy = above - sm['baseline']
        for up, low in zip(CYR_UP, CYR_LOW):
            if low in glyphs or low not in chars or up not in sm['glyphs']:
                continue
            on, adv = sm['glyphs'][up]
            glyphs[low] = ({(x, y + dy) for x, y in on}, adv)
            built.append(low)
    for up, low in zip(CYR_UP, CYR_LOW):                     # a small letter that could not be built at
        if low in chars and low not in glyphs and up in glyphs:   # x-height: use the capital
            glyphs[low] = glyphs[up]
            built.append(low)
    missing = [c for c in chars if c not in glyphs]
    return {'glyphs': glyphs, 'height': height, 'baseline': above, 'cap': cap, 'x_height': xh,
            'built': built, 'missing': missing}


def save(font, out, name='title', ns='hokaria'):
    os.makedirs(os.path.join(out, 'glyphs'), exist_ok=True)
    meta = {'height': font['height'], 'baseline': font['baseline'], 'cap': font['cap'],
            'x_height': font['x_height'], 'chars': {}}
    for ch, (on, adv) in font['glyphs'].items():
        if not on:
            continue
        x0, x1 = min(x for x, _ in on), max(x for x, _ in on)
        im = Image.new('L', (x1 - x0 + 1, font['height']), 0)
        for x, y in on:
            if 0 <= y < font['height']:
                im.putpixel((x - x0, y), 255)
        fn = f'u{ord(ch):04x}.png'
        im.save(os.path.join(out, 'glyphs', fn))
        meta['chars'][ch] = {'file': fn, 'width': x1 - x0 + 1, 'advance': x1 - x0 + 2}
    json.dump(meta, open(os.path.join(out, 'font.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    # Minecraft bitmap provider: equal cells, 16 per row; the client trims each glyph to its pixels
    chars = [c for c in meta['chars']]
    cw = max(m['width'] for m in meta['chars'].values()) + 1
    ch_ = font['height']
    rows = [chars[i:i + 16] for i in range(0, len(chars), 16)]
    sheet = Image.new('RGBA', (cw * 16, ch_ * len(rows)), (0, 0, 0, 0))
    for r, row in enumerate(rows):
        for c, chr_ in enumerate(row):
            g = Image.open(os.path.join(out, 'glyphs', meta['chars'][chr_]['file']))
            white = Image.new('RGBA', g.size, (255, 255, 255, 255))
            sheet.paste(white, (c * cw, r * ch_), g)
    tdir = os.path.join(out, 'pack', 'assets', ns, 'textures', 'font')
    fdir = os.path.join(out, 'pack', 'assets', ns, 'font')
    os.makedirs(tdir, exist_ok=True)
    os.makedirs(fdir, exist_ok=True)
    sheet.save(os.path.join(tdir, f'{name}.png'))
    sheet.save(os.path.join(out, 'sheet.png'))
    provider = {'providers': [
        {'type': 'space', 'advances': {' ': max(3, font['cap'] // 3)}},
        {'type': 'bitmap', 'file': f'{ns}:font/{name}.png', 'ascent': font['baseline'] - 1, 'height': ch_,
         'chars': [''.join(row).ljust(16, '\u0000') for row in rows]}]}
    json.dump(provider, open(os.path.join(fdir, f'{name}.json'), 'w', encoding='utf-8'), ensure_ascii=False,
              indent=1)


def fit_width(G, maxw):
    """Make a glyph at most maxw px wide by dropping columns that repeat a neighbour (counters, bars)."""
    G = set(G)
    while G and max(x for x, _ in G) - min(x for x, _ in G) + 1 > maxw:
        x0, x1 = min(x for x, _ in G), max(x for x, _ in G)
        cols = {x: frozenset(y for xx, y in G if xx == x) for x in range(x0, x1 + 1)}
        mid = (x0 + x1) / 2
        cand = [x for x in range(x0 + 1, x1) if cols[x] == cols[x - 1] or cols[x] == cols[x + 1]]
        if not cand:
            break
        drop = min(cand, key=lambda x: abs(x - mid))
        G = {(x if x < drop else x - 1, y) for x, y in G if x != drop}
    return G


def fit_cell(font_path, cell, method='coverage', chars=LATIN + CYR_UP + CYR_LOW):
    """The biggest cap height whose glyphs (with marks above and descenders) fit a cell x cell texture."""
    for cap in range(round(cell * 0.75), 3, -1):
        f = build(font_path, cap=cap, chars=chars, method=method)
        B = f['baseline']
        tops = [min(y for _, y in on) for on, _ in f['glyphs'].values() if on]
        bots = [max(y for _, y in on) for on, _ in f['glyphs'].values() if on]
        above, below = B - min(tops), max(bots) - B + 1
        if above + below <= cell:
            f['cell'] = cell
            f['cell_baseline'] = above + (cell - above - below) // 2
            return f
    raise SystemExit('no cap height fits the cell')


def save_cells(font, out, name='title', ns='hokaria'):
    """Fixed-cell font texture (cell x cell per character, 16 per row) + Minecraft bitmap provider + preview.
    height = cell (1:1 with GUI pixels); set "height" lower in the JSON for a finer (HD) font at a smaller size."""
    cell, B = font['cell'], font['cell_baseline']
    chars = [c for c, (on, _) in font['glyphs'].items() if on]
    rows = [chars[i:i + 16] for i in range(0, len(chars), 16)]
    sheet = Image.new('RGBA', (cell * 16, cell * len(rows)), (0, 0, 0, 0))
    squeezed = []
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            on, _ = font['glyphs'][ch]
            if max(x for x, _ in on) - min(x for x, _ in on) + 1 > cell:
                on = fit_width(on, cell)
                squeezed.append(ch)
            x0 = min(x for x, _ in on)
            for x, y in on:
                yy = y - font['baseline'] + B
                if 0 <= yy < cell and 0 <= x - x0 < cell:
                    sheet.putpixel((c * cell + x - x0, r * cell + yy), (255, 255, 255, 255))
    tdir = os.path.join(out, 'pack', 'assets', ns, 'textures', 'font')
    fdir = os.path.join(out, 'pack', 'assets', ns, 'font')
    os.makedirs(tdir, exist_ok=True)
    os.makedirs(fdir, exist_ok=True)
    fname = f'{name}_{cell}'
    sheet.save(os.path.join(tdir, fname + '.png'))
    sheet.save(os.path.join(out, f'sheet_{cell}.png'))
    provider = {'providers': [
        {'type': 'space', 'advances': {' ': max(3, font['cap'] // 3)}},
        {'type': 'bitmap', 'file': f'{ns}:font/{fname}.png', 'ascent': B, 'height': cell,
         'chars': [''.join(row).ljust(16, '\u0000') for row in rows]}]}
    json.dump(provider, open(os.path.join(fdir, fname + '.json'), 'w', encoding='utf-8'), ensure_ascii=False,
              indent=1)
    big = Image.new('RGBA', sheet.size, (28, 22, 64, 255))
    grid = Image.new('RGBA', sheet.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(grid)
    for i in range(17):
        gd.line((i * cell, 0, i * cell, sheet.height), fill=(60, 52, 110, 255))
    for j in range(len(rows) + 1):
        gd.line((0, j * cell, sheet.width, j * cell), fill=(60, 52, 110, 255))
    big.alpha_composite(grid)
    big.alpha_composite(sheet)
    k = max(1, 512 // cell)
    big.resize((big.width * k // 2, big.height * k // 2), Image.NEAREST).save(os.path.join(out, f'preview_cells_{cell}.png'))
    return squeezed


def load(font_dir):
    meta = json.load(open(os.path.join(font_dir, 'font.json'), encoding='utf-8'))
    meta['_dir'] = font_dir
    return meta


def text_mask(font_dir, text, spacing=1):
    """Pixels of `text` set in a converted font (lines split by \\n) - feed it to lettering.volume(mask=)."""
    meta = load(font_dir) if isinstance(font_dir, str) else font_dir
    space = max(4, meta['cap'] // 2)                    # word space: half a cap, words must not run together
    on, y0 = set(), 0
    for line in text.split('\n'):
        x = 0
        for ch in line:
            m = meta['chars'].get(ch)
            if ch == ' ' or not m:
                x += space
                continue
            g = Image.open(os.path.join(meta['_dir'], 'glyphs', m['file'])).load()
            for yy in range(meta['height']):
                for xx in range(m['width']):
                    if g[xx, yy]:
                        on.add((x + xx, y0 + yy))
            x += m['width'] + spacing
        y0 += meta['height']
    return on


def preview(font_dir, path, lines=None, k=4):
    lines = lines or ['ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz 0123456789',
                      'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ', 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя']
    meta = load(font_dir)
    masks = [text_mask(meta, l) for l in lines]
    W = max((max(x for x, _ in m) + 1) for m in masks if m) + 8
    H = meta['height'] * len(lines) + 8
    im = Image.new('RGBA', (W, H), (28, 22, 64, 255))
    for i, m in enumerate(masks):
        for x, y in m:
            im.putpixel((x + 4, y + 4 + i * meta['height']), (235, 228, 245, 255))
    im.resize((W * k, H * k), Image.NEAREST).save(path)


if __name__ == '__main__':
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)

    def opt(name, default):
        return type(default)(a[a.index(name) + 1]) if name in a else default
    if '--cells' in a:                                       # fixed-cell font textures, e.g. --cells 16,32
        for cell in [int(c) for c in a[a.index('--cells') + 1].split(',')]:
            method = opt('--method', 'auto')
            method = 'coverage' if method == 'auto' else method      # coverage read better at 16 too
            f = fit_cell(a[0], cell, method)
            sq = save_cells(f, a[1], opt('--name', 'title'), opt('--ns', 'hokaria'))
            print(f"cell {cell}: cap {f['cap']}, method {method}, glyphs {len(f['glyphs'])}, "
                  f"missing {''.join(f['missing']) or '-'}, narrowed to fit {''.join(sq) or '-'}")
    else:
        f = build(a[0], cap=opt('--cap', 16), threshold=opt('--threshold', 0.45))
        save(f, a[1], opt('--name', 'title'), opt('--ns', 'hokaria'))
        preview(a[1], os.path.join(a[1], 'preview.png'))
        print(f"glyphs: {len(f['glyphs'])}, built from Latin: {''.join(f['built'])}")
        print(f"missing: {''.join(f['missing']) or '-'}")
