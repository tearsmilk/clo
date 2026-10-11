#!/usr/bin/env python3
"""Build a Nexo glyph GUI (chest menu) from a JSON spec.

Usage:
    python3 gui_builder.py spec.json OUT_DIR

Produces in OUT_DIR:
    texture/<id>.png                 1:1 GUI texture (1 px = 1 GUI px), the glyph image
    preview.png                      in-game style preview (nearest-neighbour upscale, optional tooltip)
    preview_grid.png                 same, with slot indices drawn - use it to check button rects
    Nexo/glyphs/<id>.yml             glyph definition (ascent/height already computed)
    Nexo/pack/assets/<ns>/textures/gui/<id>.png
    DeluxeMenus/gui_menus/<id>.yml   menu with invisible buttons (item_model: nexo:empty)
    INSTALL.md                       short install notes for this menu

Spec keys are documented in SKILL.md and references/spec-format.md.

Geometry (vanilla generic chest screen):
    window width 176, height 114 + rows*18
    container slot (col,row) outer box at x = 7 + col*18, y = 17 + row*18 (18x18, item at +1,+1)
    player inventory slot boxes at y = rows*18 + 30 (+18 per row), hotbar at rows*18 + 88
    (ChestMenu puts the items at 103 + (rows-4)*18 and 161 + (rows-4)*18)
    title text origin is (8, 6) and a glyph line's top sits at 13 - ascent,
    so ascent 13 + shift -8 puts the texture's top-left on the window's top-left.
    A header "tab" that sticks out above the window adds `top` px of canvas and raises ascent by the same.
See references/gui-geometry.md for the derivation and for non-chest containers.
"""
import json, math, os, random, re, sys
from PIL import Image, ImageDraw, ImageFilter, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pixfont import draw_text, text_width, text_height, draw_block_text, block_text_size  # noqa: E402
import pixelstyle  # noqa: E402
import sprites  # noqa: E402
import art  # noqa: E402


# ----------------------------------------------------------------------------- colours / themes

def H(h, a=255):
    if isinstance(h, tuple):
        return h
    h = h.lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def mix(c, t, k):
    c, t = H(c), H(t)
    return tuple(int(c[i] + (t[i] - c[i]) * k) for i in range(3)) + (255,)


def _steps(k):
    return max(1, round(k * 4))


def lighten(c, k):
    return art.step(H(c), _steps(k))       # walks the palette ramp (hue-shifted), not a mix with white


def darken(c, k):
    return art.step(H(c), -_steps(k))


# Each theme: window body + frame band + slot colours + text colours. Non-vanilla themes use ENDESGA-32 tones
# and a textured 4px frame band (planks/bricks/cobble) around a smooth body, like hand-made GUI kits.
THEMES = {
    # vanilla Minecraft window colours (C6C6C6 fill, white/555555 bevel, 8B8B8B slots) - kept exact
    'vanilla': dict(fill=['#C6C6C6'], seam=None, hi='#FFFFFF', hi2='#FFFFFF', sh='#555555', sh2='#555555',
                    slot_dk='#373737', slot_lt='#FFFFFF', slot_in='#8B8B8B', text='#404040', recess='#8B8B8B'),
    'oak':    dict(body='#ead4aa', frame='#b86f50', frame_tex='planks', slot_in='#c28569', slot_dk='#733e39',
                   slot_lt='#ffffff', text='#3e2731', recess='#733e39'),
    'spruce': dict(body='#b86f50', frame='#733e39', frame_tex='planks', slot_in='#733e39', slot_dk='#3e2731',
                   slot_lt='#e4a672', text='#ead4aa', recess='#3e2731'),
    'birch':  dict(body='#ead4aa', frame='#e4a672', frame_tex='planks', slot_in='#e4a672', slot_dk='#b86f50',
                   slot_lt='#ffffff', text='#3e2731', recess='#c28569'),
    'stone':  dict(body='#8b9bb4', frame='#5a6988', frame_tex='bricks', slot_in='#5a6988', slot_dk='#262b44',
                   slot_lt='#c0cbdc', text='#181425', recess='#3a4466'),
    'cobble': dict(body='#c0cbdc', frame='#8b9bb4', frame_tex='cobble', slot_in='#8b9bb4', slot_dk='#3a4466',
                   slot_lt='#ffffff', text='#262b44', recess='#5a6988'),
    'nether': dict(body='#3e2731', frame='#a22633', frame_tex='bricks', slot_in='#181425', slot_dk='#181425',
                   slot_lt='#733e39', text='#ead4aa', recess='#181425'),
    'dark':   dict(body='#262b44', frame='#3a4466', frame_tex='bricks', slot_in='#181425', slot_dk='#181425',
                   slot_lt='#5a6988', text='#c0cbdc', recess='#181425'),
    'meadow': dict(body='#ead4aa', frame='#3e8948', frame_tex='grass', slot_in='#e4a672', slot_dk='#b86f50',
                   slot_lt='#ffffff', text='#265c42', recess='#c28569'),
}


def window_size(rows):
    return 176, 114 + rows * 18


def slot_xy(col, row):
    return 7 + col * 18, 17 + row * 18


def inv_slot_xy(col, row, rows):
    return 7 + col * 18, rows * 18 + 30 + row * 18


def hotbar_xy(col, rows):
    return 7 + col * 18, rows * 18 + 88


# ----------------------------------------------------------------------------- primitives

def bevel_box(img, box, fill, outline=None, hi=None, sh=None, chamfer=0):
    """Rectangle with optional 1px outline and 1px light top-left / dark bottom-right bevel."""
    x0, y0, x1, y1 = box
    d = ImageDraw.Draw(img)
    d.rectangle(box, fill=H(fill))
    o = 1 if outline else 0
    if outline:
        d.rectangle(box, outline=H(outline))
    if hi:
        d.line((x0 + o, y0 + o, x1 - o - 1, y0 + o), fill=H(hi))
        d.line((x0 + o, y0 + o, x0 + o, y1 - o - 1), fill=H(hi))
    if sh:
        d.line((x0 + o + 1, y1 - o, x1 - o, y1 - o), fill=H(sh))
        d.line((x1 - o, y0 + o + 1, x1 - o, y1 - o), fill=H(sh))
    if chamfer and outline:
        for (cx, cy) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
            img.putpixel((cx, cy), (0, 0, 0, 0))


def draw_framed_panel(img, oy, rows, th):
    """Palette themes: dark outline with cut corners, 4px textured frame band, carved inner line, smooth body."""
    W, Hh = window_size(rows)
    fr = th['frame']
    band = Image.new('RGBA', (W, Hh), (0, 0, 0, 0))
    tex = art.texture(th.get('frame_tex') or 'planks', W, Hh, fr, seed=11)
    band.alpha_composite(tex)
    d = ImageDraw.Draw(band)
    # body
    d.rectangle((5, 5, W - 6, Hh - 6), fill=art.base(th['body']))
    d.line((5, 5, W - 6, 5), fill=art.step(th['body'], -2))          # carved inner edge (shadow top/left)
    d.line((5, 5, 5, Hh - 6), fill=art.step(th['body'], -2))
    d.line((6, 6, W - 7, 6), fill=art.step(th['body'], -1))
    d.line((6, Hh - 6, W - 6, Hh - 6), fill=art.step(th['body'], 1))  # lit bottom/right
    d.line((W - 6, 6, W - 6, Hh - 6), fill=art.step(th['body'], 1))
    # frame band bevel + outline with cut corners
    d.line((1, 1, W - 2, 1), fill=art.step(fr, 1))
    d.line((1, 1, 1, Hh - 2), fill=art.step(fr, 1))
    d.line((1, Hh - 2, W - 2, Hh - 2), fill=art.step(fr, -2))
    d.line((W - 2, 1, W - 2, Hh - 2), fill=art.step(fr, -2))
    d.line((4, 4, W - 5, 4), fill=art.step(fr, -2))
    d.line((4, 4, 4, Hh - 5), fill=art.step(fr, -2))
    o = art.outline_of(fr)
    d.rectangle((0, 0, W - 1, Hh - 1), outline=o)
    for cx, cy in ((0, 0), (W - 1, 0), (0, Hh - 1), (W - 1, Hh - 1)):
        band.putpixel((cx, cy), (0, 0, 0, 0))
    for cx, cy in ((1, 1), (W - 2, 1), (1, Hh - 2), (W - 2, Hh - 2)):
        band.putpixel((cx, cy), o)
    img.alpha_composite(band, (0, oy))


def draw_panel(img, oy, rows, th, seed=7):
    """Window body with a chamfered black outline and 2px bevel, like vanilla windows."""
    if 'frame' in th:
        return draw_framed_panel(img, oy, rows, th)
    rnd = random.Random(seed)
    W, Hh = window_size(rows)
    px = img.load()
    fill = [H(c) for c in th['fill']]
    seam = H(th['seam']) if th['seam'] else None

    def inside(x, y):
        if x < 0 or y < 0 or x >= W or y >= Hh:
            return False
        for cx, cy in ((0, 0), (W - 1, 0), (0, Hh - 1), (W - 1, Hh - 1)):
            if abs(x - cx) + abs(y - cy) < 3:
                return False
        return True

    for y in range(Hh):
        row = y // 7
        for x in range(W):
            if not inside(x, y):
                continue
            if len(fill) == 1:
                c = fill[0]
            elif seam and (y % 7 == 6 or (x + (row % 2) * 44) % 88 == 0):
                c = seam
            else:
                c = fill[(row + x // 11) % len(fill)] if rnd.random() > 0.08 else fill[rnd.randrange(len(fill))]
            px[x, y + oy] = c
    hi, hi2, sh, sh2 = H(th['hi']), H(th['hi2']), H(th['sh']), H(th['sh2'])
    for y in range(Hh):
        for x in range(W):
            if not inside(x, y):
                continue
            if not all(inside(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                px[x, y + oy] = (0, 0, 0, 255)
                continue
            d_tl, d_br = min(x, y), min(W - 1 - x, Hh - 1 - y)
            if d_tl in (1, 2) and d_tl <= d_br:
                px[x, y + oy] = hi if d_tl == 1 else hi2
            elif d_br in (1, 2):
                px[x, y + oy] = sh if d_br == 1 else sh2


def draw_slot(img, x0, y0, th, size=18):
    d = ImageDraw.Draw(img)
    d.rectangle((x0, y0, x0 + size - 1, y0 + size - 1), fill=H(th['slot_in']))
    d.line((x0, y0, x0 + size - 2, y0), fill=H(th['slot_dk']))
    d.line((x0, y0, x0, y0 + size - 2), fill=H(th['slot_dk']))
    d.line((x0 + 1, y0 + size - 1, x0 + size - 1, y0 + size - 1), fill=H(th['slot_lt']))
    d.line((x0 + size - 1, y0 + 1, x0 + size - 1, y0 + size - 1), fill=H(th['slot_lt']))


# ----------------------------------------------------------------------------- backgrounds

def pattern(name, base, w, h, seed=1):
    """Pixel textures for tile backgrounds (hand-structured, see art.py)."""
    return art.texture(name, w, h, base, seed=seed)


def _old_pattern(name, base, w, h, seed=1):
    """Previous noise-based textures (kept for reference)."""
    rnd = random.Random(seed)
    base = H(base)
    lt, dk = lighten(base, 0.18), darken(base, 0.18)
    im = Image.new('RGBA', (w, h), base)
    p = im.load()
    for y in range(h):
        for x in range(w):
            c = base
            if name == 'planks_v':          # vertical boards like the "Профиль" tile
                k = x % 6
                c = lt if k in (1, 2) else (dk if k == 5 else base)
                if (y + (x // 6) * 7) % 23 == 0:
                    c = dk
            elif name == 'planks_h':
                k = y % 6
                c = lt if k in (1,) else (dk if k == 5 else base)
                if (x + (y // 6) * 9) % 29 == 0:
                    c = dk
            elif name == 'bricks':
                r = y // 5
                if y % 5 == 4 or (x + (r % 2) * 5) % 10 == 0:
                    c = dk
                elif rnd.random() < 0.15:
                    c = lt
            elif name == 'stone':           # cobble-ish blotches
                v = (math.sin(x * 0.9 + seed) + math.sin(y * 1.1 + seed * 2) + math.sin((x + y) * 0.45)) / 3
                c = lt if v > 0.35 else (dk if v < -0.35 else base)
                if rnd.random() < 0.06:
                    c = darken(base, 0.3)
            elif name == 'grass':
                r = rnd.random()
                c = lt if r < 0.18 else (dk if r < 0.36 else base)
            elif name == 'checker':
                c = lt if ((x // 4) + (y // 4)) % 2 == 0 else base
            elif name == 'stripes':
                c = lt if (x // 3) % 2 == 0 else base
            elif name == 'dots':
                c = lt if (x % 6 == 0 and y % 6 == 0) or ((x + 3) % 6 == 0 and (y + 3) % 6 == 0) else base
            elif name == 'noise':
                r = rnd.random()
                c = lt if r < 0.1 else (dk if r < 0.2 else base)
            p[x, y] = c
    return im


def sunburst(base, w, h, cy_frac=0.42):
    base = H(base)
    im = Image.new('RGBA', (w, h), base)
    d = ImageDraw.Draw(im)
    cx, cy = w / 2, h * cy_frac
    for i in range(16):
        a0 = i * 2 * math.pi / 16
        a1 = a0 + math.pi / 16
        R = 400
        d.polygon([(cx, cy), (cx + R * math.cos(a0), cy + R * math.sin(a0)), (cx + R * math.cos(a1), cy + R * math.sin(a1))],
                  fill=mix(base, art.step(base, 1), 0.45))     # half a ramp step: rays read as light, not as a new hue
    return im


def gradient(base, w, h):
    """Banded 'gradient' (pixel art has no smooth gradients): soft light band on top, base, soft shade below."""
    base = H(base)
    im = Image.new('RGBA', (w, h), base)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w, max(1, h // 3) - 1), fill=mix(base, art.step(base, 1), 0.5))
    d.rectangle((0, h - max(1, h // 3), w, h), fill=mix(base, art.step(base, -1), 0.5))
    return im


def cover(path, w, h, colors=48):
    """Scale an illustration to cover w x h (centre crop) and posterize it to a pixel-art palette."""
    im = Image.open(path).convert('RGB')
    k = max(w / im.width, h / im.height)
    im = im.resize((max(w, math.ceil(im.width * k)), max(h, math.ceil(im.height * k))), Image.LANCZOS)
    l, t = (im.width - w) // 2, (im.height - h) // 2
    im = im.crop((l, t, l + w, t + h))
    return im.quantize(colors=colors, method=Image.MEDIANCUT).convert('RGBA')


def load_icon_img(ic, size):
    k = size / max(ic.size)
    return ic.resize((max(1, round(ic.width * k)), max(1, round(ic.height * k))), Image.NEAREST)


def load_icon(path, max_w, max_h, alpha_cut=110):
    """Fit an RGBA icon into max_w x max_h with a hard alpha edge (pixel-art friendly)."""
    ic = Image.open(path).convert('RGBA')
    bb = ic.getbbox()
    if bb:
        ic = ic.crop(bb)
    k = min(max_w / ic.width, max_h / ic.height)
    if k >= 1:                       # small hand-made sprite: keep it crisp, only whole-number upscales
        k = math.floor(k)
    nw, nh = max(1, round(ic.width * k)), max(1, round(ic.height * k))
    resample = Image.NEAREST if (k >= 1 or (ic.width % nw == 0 and ic.height % nh == 0)) else Image.LANCZOS
    ic = ic.resize((nw, nh), resample)
    ic.putalpha(ic.getchannel('A').point(lambda v: 255 if v > alpha_cut else 0))
    return ic



def plate(img, box, kind='wood', color=None):
    """Rounded plate like pixel UI kits: black outline, cut corners, light top row, 2px darker bottom,
    nails at both ends (wood) or chips (stone). box = (x0, y0, x1, y1) inclusive."""
    x0, y0, x1, y1 = box
    base = H(color or ('#D9895A' if kind == 'wood' else '#9A968C'))
    d = ImageDraw.Draw(img)
    d.rectangle((x0 + 1, y0, x1 - 1, y1), fill=(0, 0, 0, 255))
    d.rectangle((x0, y0 + 1, x1, y1 - 1), fill=(0, 0, 0, 255))
    d.rectangle((x0 + 1, y0 + 1, x1 - 1, y1 - 1), fill=base)
    d.line((x0 + 2, y0 + 1, x1 - 2, y0 + 1), fill=lighten(base, 0.3))
    d.line((x0 + 1, y1 - 1, x1 - 1, y1 - 1), fill=darken(base, 0.35))
    if y1 - y0 > 7:
        d.line((x0 + 1, y1 - 2, x1 - 1, y1 - 2), fill=darken(base, 0.18))
    if kind == 'wood':
        my = (y0 + y1) // 2
        for nx in (x0 + 2, x1 - 3):
            d.rectangle((nx, my - 1, nx + 1, my), fill=darken(base, 0.45))
    else:
        rnd = random.Random(x0 * 31 + y0)
        for _ in range(max(1, (x1 - x0) // 10)):
            cx, cy = rnd.randint(x0 + 3, x1 - 3), rnd.randint(y0 + 2, y1 - 3)
            d.point((cx, cy), fill=lighten(base, 0.2))
            d.point((cx + 1, cy + 1), fill=darken(base, 0.25))


# Decoration sprites (drawn in px coordinates on top of the texture)
DECOR = {
    'sparkle': (["...#...", "...#...", "..###..", "#######", "..###..", "...#...", "...#..."], {'#': '#FFF3B0'}),
    'sparkle_small': ([".#.", "###", ".#."], {'#': '#FFF3B0'}),
    'star': (["..#..", ".###.", "#####", ".###.", "..#.."], {'#': '#FFE27A'}),
    'cloud': (["....###......", "..##WWW#.###.", ".#WWWWWW#WWW#", "#WWWWWWWWWWWW#", "#LLWWWWWWWLLL#", ".##LLLLLLLL##."],
              {'#': '#9CC9EE', 'W': '#FFFFFF', 'L': '#CFE6F8'}),
    'moon': (["..###..", ".#OOO#.", "#OOOOD#", "#OOODD#", "#ODODD#", ".#ODD#.", "..###.."],
             {'#': '#3C4A7A', 'O': '#DDE6FF', 'D': '#A9B8E6'}),
    'leaf': (["...##", "..#G#", ".#GG#", "#GG#.", "##..."], {'#': '#24601A', 'G': '#5DAA3A'}),
}


def draw_decor(img, oy, items):
    for it in items:
        rows, pal = DECOR[it['type']]
        col = it.get('color')
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                if ch in pal:
                    c = H(col) if (col and ch in '#') and it['type'].startswith(('sparkle', 'star')) else H(pal[ch])
                    x, y = it['x'] + i, oy + it['y'] + j
                    if 0 <= x < img.width and 0 <= y < img.height:
                        img.putpixel((x, y), c)



# ----------------------------------------------------------------------------- scene layers

def layer_box(L):
    """Pixel box (x0, y0, x1, y1) of a layer from `slots: [col,row,w,h]` (+pad) or `box: [x,y,w,h]` in px."""
    if 'slots' in L:
        c, r, w, h = L['slots']
        x0, y0 = slot_xy(c, r)
        p = L.get('pad', 0)
        return x0 - p, y0 - p, x0 + w * 18 - 1 + p, y0 + h * 18 - 1 + p
    x, y, w, h = L['box']
    return x, y, x + w - 1, y + h - 1


def draw_layers(img, oy, layers, sdir, th):
    """Free-form scene art: backgrounds, awnings, posts, props and framed slots (all px or slot based)."""
    for L in layers:
        t = L['type']
        if t == 'sprite':
            spr = sprites.render(L['name'], **L.get('opts', {}))
            if 'slot' in L:
                sx, sy = slot_xy(L['slot'] % 9, L['slot'] // 9)
                x, y = sx + (18 - spr.width) // 2, sy + (18 - spr.height) // 2
            else:
                x, y = L['x'], L['y']
            img.alpha_composite(spr, (x, y + oy))
            continue
        if t != 'slot_frame':
            x0, y0, x1, y1 = layer_box(L)
            y0, y1 = y0 + oy, y1 + oy
            w, h = x1 - x0 + 1, y1 - y0 + 1
        if t == 'rect':
            if L.get('pattern'):
                tile = pattern(L['pattern'], L.get('color', '#808080'), w, h, seed=L.get('seed', 1))
            else:
                tile = Image.new('RGBA', (w, h), H(L.get('color', '#808080')))
            img.alpha_composite(tile, (x0, y0))
            if L.get('outline'):
                ImageDraw.Draw(img).rectangle((x0, y0, x1, y1), outline=H(L['outline']))
            if L.get('bevel'):
                c = H(L.get('color', '#808080'))
                d = ImageDraw.Draw(img)
                o = 1 if L.get('outline') else 0
                d.line((x0 + o, y0 + o, x1 - o, y0 + o), fill=lighten(c, 0.25))
                d.line((x0 + o, y1 - o, x1 - o, y1 - o), fill=darken(c, 0.3))
        elif t == 'awning':
            img.alpha_composite(sprites.awning(w, h, tuple(L.get('colors', ('#C2453A', '#F2E4C8'))),
                                               L.get('stripe', 9), L.get('scallop', 4)), (x0, y0))
        elif t == 'post':
            img.alpha_composite(sprites.post(w, h, L.get('color', '#8A5A2E')), (x0, y0))
        elif t == 'image':
            im = cover(resolve(L['path'], sdir), w, h, L.get('colors', 48))
            img.alpha_composite(im, (x0, y0))
        elif t == 'slot_frame':          # a framed, highlighted item slot (quest steps, reward, input)
            for idx in L.get('slot_list', [L.get('slot')]):
                sx, sy = slot_xy(idx % 9, idx // 9)
                sy += oy
                fc = H(L.get('color', '#FBF3DC'))
                d = ImageDraw.Draw(img)
                d.rectangle((sx - 2, sy - 2, sx + 19, sy + 19), fill=H(L.get('outline', '#1E1408')))
                d.rectangle((sx - 1, sy - 1, sx + 18, sy + 18), fill=fc)
                inner = dict(th)
                if L.get('inner'):
                    ic = H(L['inner'])
                    inner.update(slot_in=ic, slot_dk=darken(ic, 0.45), slot_lt=lighten(ic, 0.3))
                draw_slot(img, sx, sy, inner)
        else:
            raise SystemExit(f"unknown layer type '{t}'")


# ----------------------------------------------------------------------------- buttons

def resolve(path, sdir):
    return path if os.path.isabs(path) else os.path.join(sdir, path)


def tile_frame(tile, base, outline=None, frame=None):
    """Drawn-button frame: dark outline with cut corners, lit top/left rim, 2px darker bottom lip, dark right edge."""
    w, h = tile.size
    d = ImageDraw.Draw(tile)
    o = H(outline) if outline else art.outline_of(base)
    d.rectangle((0, 0, w - 1, h - 1), outline=o)
    k = 1
    if frame:                                        # light inner border (cream/white frame like reference kits)
        d.rectangle((1, 1, w - 2, h - 2), outline=H(frame))
        k = 2
    d.line((k, k, w - 1 - k, k), fill=art.step(base, 1))
    d.line((k, k, k, h - 2 - k), fill=art.step(base, 1))
    d.line((w - 1 - k, k + 1, w - 1 - k, h - 1 - k), fill=art.step(base, -1))
    d.line((k, h - 1 - k, w - 1 - k, h - 1 - k), fill=art.step(base, -2))
    if h > 12:
        d.line((k + 1, h - 2 - k, w - 2 - k, h - 2 - k), fill=art.step(base, -1))
    for cx, cy in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        tile.putpixel((cx, cy), (0, 0, 0, 0))


def fit_label(label, maxw, spacings=(2, 1)):
    """Pick letter spacing: 2px reads best with an outline, fall back to 1px; None if it does not fit."""
    for sp in spacings:
        if text_width(label, spacing=sp) <= maxw:
            return sp
    return None


def draw_button(img, oy, b, sdir, th, label_case, spec_icon_style=None):
    style = b.get('style', 'sunburst')
    x0, y0 = slot_xy(b['x'], b['y'])
    y0 += oy
    w, h = b.get('w', 1) * 18, b.get('h', 1) * 18
    inset = b.get('inset', 1)              # 1px gap to neighbours; 0 = tiles touch (bento look)
    x0, y0, w, h = x0 + inset, y0 + inset, w - 2 * inset, h - 2 * inset
    base = art.base(H(b.get('color', '#63c74d')))

    # background
    if style == 'sunburst':
        tile = sunburst(base, w, h, 0.42 if b.get('label') else 0.5)
    elif style == 'gradient':
        tile = gradient(base, w, h)
    elif style == 'pattern':
        tile = pattern(b.get('pattern', 'noise'), base, w, h, seed=sum(map(ord, b['id'])))
    elif style == 'image':
        tile = cover(resolve(b['image'], sdir), w, h, b.get('colors', 48))
    else:  # flat / button
        tile = Image.new('RGBA', (w, h), base)
        if style == 'button' and h >= 12:            # two-tone body: lighter upper band like a real button
            ImageDraw.Draw(tile).rectangle((0, 0, w, h // 2 - 1), fill=art.step(base, 1))

    if b.get('disabled'):                # grey out the background only; the icon becomes a coloured line-art
        g = ImageOps.grayscale(tile.convert('RGB')).convert('RGBA')
        tile = Image.blend(g, Image.new('RGBA', g.size, (40, 40, 40, 255)), 0.35)
        base = art.base('#5a6988')
    tile_frame(tile, base, b.get('outline'), b.get('frame'))

    # label geometry
    label = b.get('label') or ''
    case = b.get('label_case', label_case)
    if case == 'upper':
        label = label.upper()
    label = label.replace('\\n', '\n')
    lstyle = b.get('label_style', 'outline')
    lpos = b.get('label_pos', 'bottom')
    label_zone, spacing = 0, 1
    if label:
        # widest text each style allows: outline needs 1px per side, plates add their own padding
        maxw = w - {'plaque': 9, 'wood': 11, 'stone': 11, 'bar': 6}.get(lstyle, 4)
        sp = fit_label(label, maxw, (2, 1) if lstyle in ('outline', 'shadow') else (1,))
        if sp is None:
            raise SystemExit(f"label '{label}' is {text_width(label)}px but button '{b['id']}' fits {maxw}px - "
                             f"shorten it, split it into two lines with \\n, or widen the button")
        spacing = sp
        tht = text_height(label)
        label_zone = tht + (6 if lstyle in ('plaque', 'bar', 'wood', 'stone') else 3)
        if b.get('icon') and label_zone > h - 4:
            raise SystemExit(f"label '{label}' is too tall for button '{b['id']}' ({h}px high)")

    # icon (optionally inside a framed box)
    if b.get('icon'):
        m = 1 if w <= 18 or h <= 18 else 2          # small 1x1 buttons: let the icon fill the slot
        top_free = m + (label_zone if lpos == 'top' else 0)
        # outlined labels may overlap the bottom of the icon (like quick-menu tiles), so icons can be bigger
        overlap = 4 if (label_zone and lstyle == 'outline' and lpos == 'bottom') else 0
        avail_h = h - 2 * m - label_zone - (2 if label_zone else 0) + overlap
        avail_w = w - 2 * m
        fpad = 3 if b.get('icon_frame') else 0
        size = b.get('icon_size') or min(avail_w, avail_h) - 2 * fpad
        icon_src = b['icon']
        is_sprite = icon_src.startswith('sprite:')
        if is_sprite:
            spr = sprites.render(icon_src[7:])
            import tempfile
            tmp = os.path.join(tempfile.gettempdir(), f"nexo_gui_sprite_{icon_src[7:]}.png")
            spr.save(tmp)
            b = dict(b, icon=tmp)
        style_opts = dict(spec_icon_style or {}, **(b.get('icon_style') or {}))
        auto = art._enabled and not is_sprite and spec_icon_style is None and not b.get('icon_style')
        if auto:                                     # clean pixel icon (own colours, coloured outline, top-left light)
            style_opts = {'colors': 12}
        if style_opts.get('palette') == 'auto':
            style_opts['palette'] = art.ENDESGA32
        if (not is_sprite and style_opts.get('enabled', bool(style_opts))) or b.get('disabled'):
            sil = style_opts.get('silhouette_color', '#feae34') if b.get('disabled') else None
            ic = pixelstyle.stylize(Image.open(resolve(b['icon'], sdir)), size=size,
                                    colors=style_opts.get('colors', 10), outline=style_opts.get('outline', 'auto'),
                                    light=style_opts.get('light', True), palette=style_opts.get('palette'),
                                    extrude_depth=0 if sil else style_opts.get('extrude', 0),
                                    sparkle=style_opts.get('sparkle', False) or b.get('sparkle', False),
                                    silhouette_color=sil)
            if ic.width > size + 4 or ic.height > size + 4:   # extrude/sparkle grow the canvas; keep it inside
                ic.thumbnail((size + 4, size + 4), Image.NEAREST)
        else:
            ic = load_icon(resolve(b['icon'], sdir), size, size)
        bw, bh = ic.width + 2 * fpad, ic.height + 2 * fpad
        bx = (w - bw) // 2
        by = top_free + max(0, (avail_h - bh) // 2)
        if b.get('icon_frame'):
            fc = art.base(H(b.get('icon_frame_color', art.step(base, -1))))
            art.bevel(tile, (bx, by, bx + bw - 1, by + bh - 1), fc, lip=1)
        shadow = Image.new('RGBA', ic.size, (0, 0, 0, 0))
        shadow.putalpha(ic.getchannel('A').point(lambda v: 80 if v else 0))
        tile.alpha_composite(shadow, (bx + fpad + 1, by + fpad + 1))
        tile.alpha_composite(ic, (bx + fpad, by + fpad))

    # label
    if label:
        tw, tht = text_width(label, spacing=spacing), text_height(label)
        tcol = H(b.get('label_color', '#FFFFFF'))
        if lstyle == 'plaque':           # dark plate with a light rim, like the reference menus
            pw, ph = tw + 7, tht + 6
            px0 = (w - pw) // 2
            py0 = (h - ph) // 2 if not b.get('icon') and h < 40 else ((h - ph - 4) if lpos == 'bottom' else 3)
            pc = art.base(H(b.get('plaque_color', art.step(base, -2))))
            art.drop_shadow(tile, (px0, py0, px0 + pw - 1, py0 + ph - 1))
            art.bevel(tile, (px0, py0, px0 + pw - 1, py0 + ph - 1), pc, lip=1)
            draw_text(tile, px0 + 3, py0 + 3, label, tcol, shadow=art.step(pc, -2), align='center')
        elif lstyle in ('wood', 'stone'):  # pixel UI-kit plates with nails / chips
            pw, ph = tw + 9, min(tht + 7, h - 4)
            px0 = (w - pw) // 2
            py0 = (h - ph) // 2 if not b.get('icon') and h < 40 else ((h - ph - 4) if lpos == 'bottom' else 2)
            pcol = b.get('plaque_color') or ('#b86f50' if lstyle == 'wood' else '#8b9bb4')
            art.plate(tile, (px0, py0, px0 + pw - 1, py0 + ph - 1), lstyle, pcol)
            draw_text(tile, px0 + 5, py0 + max(1, (ph - 1 - 7) // 2), label, tcol, shadow=art.step(pcol, -2),
                      align='center')
        elif lstyle == 'bar':            # full-width band
            ph = tht + 5
            py0 = (h - ph - 3) if lpos == 'bottom' else 2
            if not b.get('icon') and not b.get('image') and h < 24:
                py0 = (h - ph) // 2
            pc = art.base(H(b.get('plaque_color', art.step(base, -2))))
            dd = ImageDraw.Draw(tile)
            dd.rectangle((2, py0, w - 3, py0 + ph - 1), fill=pc)
            dd.line((2, py0, w - 3, py0), fill=art.step(pc, -1))
            draw_text(tile, (w - tw) // 2, py0 + 3, label, tcol, shadow=art.step(pc, -2), align='center')
        else:                            # 'outline' (default) or 'shadow'
            if not b.get('icon'):
                ty = (h - 2 - (tht - (2 if tht % 10 == 9 else 0))) // 2   # centre on capitals above the lip
            else:
                ty = (h - tht - 5) if lpos == 'bottom' else 3
            if lstyle == 'shadow':
                draw_text(tile, (w - tw) // 2, ty, label, tcol, shadow=art.step(base, -2), align='center', spacing=spacing)
            else:
                draw_text(tile, (w - tw) // 2, ty, label, tcol, outline=art.outline_of(base), align='center',
                          spacing=spacing)

    img.alpha_composite(tile, (x0, y0))


def header_top(spec):
    """Extra canvas rows needed above the window for a header that sticks out."""
    hd = spec.get('header') or {}
    if hd.get('style') == 'block':
        txt = hd['text'] if hd.get('case') == 'keep' else hd['text'].upper()
        return max(0, block_text_size(txt, hd.get('size', 3))[1] + hd.get('depth', 0) - 15)
    if hd.get('size', 1) == 2:
        return 10
    return 8 if hd.get('style') == 'tab' else 0


def draw_header(img, oy, spec, th):
    """Title plaque. size 1: small caps plate inside the 17px top strip (with rivets);
    size 2: double-size letters on a tab that sticks out above the window (needs header_top rows)."""
    hd = spec.get('header')
    if not hd:
        return
    text = hd['text'] if hd.get('case') == 'keep' else hd['text'].upper()
    style = hd.get('style', 'plaque')
    sc = 2 if hd.get('size', 1) == 2 else 1
    col = H(hd.get('color', '#4A4A4A' if spec.get('theme', 'oak') == 'vanilla' else '#5A3D1C'))
    tcol = H(hd.get('text_color', '#F0F0F0'))
    tw = text_width(text, scale=sc)
    if style == 'block':                 # Minecraft-logo lettering sticking out above the window
        bw, bh = block_text_size(text, hd.get('size', 3))
        bh += hd.get('depth', 0)
        draw_block_text(img, (176 - bw) // 2, oy + 15 - bh, text, scale=hd.get('size', 3),
                        top=hd.get('top_color', '#D8D8D8'), bottom=hd.get('bottom_color', '#6E6A68'),
                        outline=hd.get('outline_color', '#111111'), depth=hd.get('depth', 0),
                        side=hd.get('side_color'))
        return
    if style == 'text':
        draw_text(img, (176 - tw) // 2 if hd.get('center', True) else 8, oy + 5, text,
                  H(hd.get('text_color', th['text'])), scale=sc)
        return
    pw = tw + 6 * sc + 2
    x0 = (176 - pw) // 2
    if sc == 2:
        y1 = oy + 15
        y0 = y1 - (7 * sc + 7)
    elif style == 'tab':
        y0, y1 = 0, oy + 13
    else:
        y0, y1 = oy + 3, oy + 15
    kind = hd.get('plate', 'wood' if spec.get('theme', 'oak') != 'vanilla' else 'dark')
    pcol = hd.get('color') if hd.get('color') else None
    art.plate(img, (x0, y0, x0 + pw - 1, y1), kind, pcol)
    pc = art.base(pcol or {'wood': '#b86f50', 'stone': '#8b9bb4', 'dark': '#3a4466', 'gold': '#feae34'}[kind])
    ty = y0 + ((y1 - y0 - 1) - 7 * sc) // 2
    draw_text(img, x0 + 3 * sc + 1, ty, text, tcol, scale=sc, shadow=art.step(pc, -3))
    if hd.get('rivets', True):
        ry = (y0 + y1) // 2 - 2
        for rx in (x0 - 7, x0 + pw + 2):
            art.drop_shadow(img, (rx, ry, rx + 4, ry + 4))
            art.bevel(img, (rx, ry, rx + 4, ry + 4), '#8b9bb4', lip=1)


def button_slots(b):
    return [(b['y'] + r) * 9 + b['x'] + c for r in range(b.get('h', 1)) for c in range(b.get('w', 1))]


def strip_codes(t):
    """Drop &x / §x legacy colour codes and <tags> for preview text."""
    return re.sub(r'(&|§)[0-9a-fk-or]|<[^>]+>', '', t, flags=re.I)


# ----------------------------------------------------------------------------- build

def build(spec_path, out):
    spec = json.load(open(spec_path, encoding='utf-8'))
    sdir = os.path.dirname(os.path.abspath(spec_path))
    gid, ns, rows = spec['id'], spec.get('namespace', 'gui'), int(spec.get('rows', 6))
    assert 1 <= rows <= 6, 'rows must be 1..6'
    art.set_palette(spec.get('palette', 'endesga32'))
    tname = spec.get('theme', 'oak')
    th = dict(THEMES[tname]) if isinstance(tname, str) else dict(THEMES['oak'], **tname)
    th.update(spec.get('theme_overrides', {}))
    label_case = spec.get('label_case', 'keep')
    W, Hh = window_size(rows)
    top = header_top(spec)
    tex = Image.new('RGBA', (W, Hh + top), (0, 0, 0, 0))
    draw_panel(tex, top, rows, th)

    used = set()
    for b in spec.get('buttons', []):
        s = button_slots(b)
        if b['x'] + b.get('w', 1) > 9 or b['y'] + b.get('h', 1) > rows:
            raise SystemExit(f"button '{b['id']}' does not fit a 9x{rows} grid")
        clash = used.intersection(s)
        if clash:
            raise SystemExit(f"button '{b['id']}' overlaps slots {sorted(clash)}")
        used.update(s)

    # recessed group panels (drawn under buttons): darker inset area with inverted bevel
    for pnl in spec.get('panels', []):
        x0, y0 = slot_xy(pnl['x'], pnl['y'])
        x1, y1 = x0 + pnl['w'] * 18 - 1, y0 + pnl['h'] * 18 - 1
        pad = pnl.get('pad', 1)
        c = art.base(H(pnl.get('color', th['recess']))) if 'frame' in th else H(pnl.get('color', th['recess']))
        bevel_box(tex, (x0 - pad, top + y0 - pad, x1 + pad, top + y1 + pad), c,
                  outline=None, hi=darken(c, 0.3), sh=lighten(c, 0.3))   # carved: dark top/left, lit bottom/right

    draw_layers(tex, top, [L for L in spec.get('layers', []) if not L.get('above')], sdir, th)

    keep_slots = set(spec.get('slots_visible', []))
    if spec.get('draw_free_slots', True):
        keep_slots |= {i for i in range(rows * 9) if i not in used}
    for i in sorted(keep_slots):
        x, y = slot_xy(i % 9, i // 9)
        draw_slot(tex, x, y + top, th)
    if spec.get('draw_player_inventory', True):
        for r in range(3):
            for c in range(9):
                x, y = inv_slot_xy(c, r, rows)
                draw_slot(tex, x, y + top, th)
        for c in range(9):
            x, y = hotbar_xy(c, rows)
            draw_slot(tex, x, y + top, th)
    for b in spec.get('buttons', []):
        draw_button(tex, top, b, sdir, th, label_case, spec.get('icon_style'))
    draw_layers(tex, top, [L for L in spec.get('layers', []) if L.get('above')], sdir, th)

    title_col = H(spec.get('title_color', th['text']))
    if spec.get('title') and not spec.get('header'):
        draw_text(tex, 8, top + (7 if 'frame' in th else 5), spec['title'], title_col)
    draw_header(tex, top, spec, th)
    draw_decor(tex, top, spec.get('decor', []))
    inv_label = spec.get('inventory_label', 'Инвентарь')
    if inv_label and spec.get('draw_player_inventory', True):
        draw_text(tex, 8, top + rows * 18 + 20, inv_label, title_col)

    for sub in ('texture', 'Nexo/glyphs', f'Nexo/pack/assets/{ns}/textures/gui', 'DeluxeMenus/gui_menus'):
        os.makedirs(os.path.join(out, sub), exist_ok=True)
    tex.save(os.path.join(out, 'texture', f'{gid}.png'))
    tex.save(os.path.join(out, f'Nexo/pack/assets/{ns}/textures/gui/{gid}.png'))

    # --- Nexo glyph: height = texture height keeps it 1:1; ascent 13 (+top) aligns the window top ---
    ascent = 13 + top + int(spec.get('ascent_nudge', 0))
    TH = Hh + top
    open(os.path.join(out, f'Nexo/glyphs/{gid}.yml'), 'w', encoding='utf-8').write(
        f"# Nexo glyph for the '{gid}' menu background. Texture is {W}x{TH}, drawn 1:1.\n"
        f"{gid}:\n  texture: {ns}:gui/{gid}\n  ascent: {ascent}\n  height: {TH}\n")

    # --- DeluxeMenus menu ---
    shift = -8 + int(spec.get('shift_nudge', 0))
    back = W + 1
    title_text = spec.get('title_text', '')
    menu_title = f"<white><shift:{shift}><glyph:{gid}>" + (f"<shift:-{back}><dark_gray>{title_text}" if title_text else '')
    lines = [
        f"# DeluxeMenus menu '{gid}' - generated by minecraft-nexo-gui",
        f"# Register in plugins/DeluxeMenus/config.yml under gui_menus: {gid}: {{file: {gid}.yml}}",
        "# If the <glyph>/<shift> tags show as raw text, use PlaceholderAPI instead:",
        f"#   menu_title: '%nexo_shift_{shift}%%nexo_{gid}%'",
        f"menu_title: '{menu_title}'",
        "open_command:",
    ] + [f"  - {c}" for c in spec.get('open_commands', [gid])] + [f"size: {rows * 9}", "items:"]
    for b in spec.get('buttons', []):
        slots = button_slots(b)
        lines += [f"  '{b['id']}':"]
        if b.get('material'):
            lines.append(f"    material: {b['material']}")
        else:
            lines += ["    material: PAPER", "    item_model: nexo:empty   # invisible - the glyph draws the button"]
        dn = b.get('name') or (b.get('label') or b['id']).replace('\\n', ' ').replace('\n', ' ')
        lines += [f"    slots: [{', '.join(map(str, slots))}]", f"    display_name: '{dn}'"]
        if b.get('lore'):
            lines.append("    lore:")
            lines += [f"      - '{l}'" for l in b['lore']]
        if b.get('hide_tooltip'):
            lines.append("    hide_tooltip: true")
        if b.get('commands'):
            lines.append("    left_click_commands:")
            lines += [f"      - '{c}'" for c in b['commands']]
    for it in spec.get('extra_items', []):   # raw DeluxeMenus items (real visible items in slots_visible etc.)
        lines.append(f"  '{it['id']}':")
        for k, v in it.items():
            if k not in ('id', 'preview'):
                lines.append(f"    {k}: {json.dumps(v, ensure_ascii=False)}")
    open(os.path.join(out, f'DeluxeMenus/gui_menus/{gid}.yml'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')

    # --- previews ---
    S = int(spec.get('preview_scale', 4))
    big = tex.resize((W * S, TH * S), Image.NEAREST)
    tip, tb = None, None
    if spec.get('preview_tooltip'):
        tb = next(x for x in spec['buttons'] if x['id'] == spec['preview_tooltip'])
        tlines = [strip_codes(tb.get('name') or tb.get('label') or tb['id']).replace('\\n', ' ')] + \
                 [strip_codes(l) for l in tb.get('lore', [])]
        tw = max(text_width(l) for l in tlines) + 8
        th_ = len(tlines) * 10 + 6
        tip = Image.new('RGBA', (tw, th_), H('#100010', 240))
        ImageDraw.Draw(tip).rectangle((1, 1, tw - 2, th_ - 2), outline=H('#2D0A63'))
        for i, l in enumerate(tlines):
            col = H('#FFFF55') if i == 0 else H('#AAAAAA')
            draw_text(tip, 4, 4 + i * 10, l, col, shadow=darken(col, 0.75))
        tip = tip.resize((tw * S, th_ * S), Image.NEAREST)
    pad_r = (tip.width + 56) if tip else 40
    canvas = Image.new('RGBA', (W * S + 40 + pad_r, TH * S + 80), H('#20161E'))
    bgp = spec.get('preview_background')
    if bgp:
        bg = Image.open(resolve(bgp, sdir)).convert('RGBA')
        k = max(canvas.width / bg.width, canvas.height / bg.height)
        bg = bg.resize((math.ceil(bg.width * k), math.ceil(bg.height * k))).crop((0, 0, canvas.width, canvas.height))
        bg = bg.filter(ImageFilter.GaussianBlur(8))
        bg.alpha_composite(Image.new('RGBA', bg.size, (16, 10, 20, 140)))
        canvas = bg
    # preview-only: draw stand-ins for real items (extra_items with "preview": "sprite:name" or a PNG path)
    for it in spec.get('extra_items', []):
        pv = it.get('preview')
        if not pv:
            continue
        ic = sprites.render(pv[7:]) if pv.startswith('sprite:') else load_icon(resolve(pv, sdir), 16, 16)
        if ic.width > 16 or ic.height > 16:
            ic = load_icon_img(ic, 16)
        for sl in ([it['slot']] if 'slot' in it else it.get('slots', [])):
            sx, sy = slot_xy(sl % 9, sl // 9)
            ox, oyy = sx + 1 + (16 - ic.width) // 2, sy + 1 + top + (16 - ic.height) // 2
            big.alpha_composite(ic.resize((ic.width * S, ic.height * S), Image.NEAREST), (ox * S, oyy * S))
            if it.get('amount', 1) > 1:
                draw_text(big, (sx + 17 - text_width(str(it['amount']))) * S, (sy + top + 10) * S, str(it['amount']),
                          (255, 255, 255, 255), scale=S, shadow=(62, 62, 62, 255))
    canvas.alpha_composite(big, (40, 40))
    if tip:
        sx, sy = slot_xy(tb['x'], tb['y'])
        canvas.alpha_composite(Image.new('RGBA', (16 * S, 16 * S), (255, 255, 255, 80)), (40 + (sx + 1) * S, 40 + (sy + 1 + top) * S))
        canvas.alpha_composite(tip, (40 + W * S + 16, 40 + (sy + top) * S))
    canvas.convert('RGB').save(os.path.join(out, 'preview.png'))

    grid = big.copy()
    for i in range(rows * 9):
        x, y = slot_xy(i % 9, i // 9)
        y += top
        ImageDraw.Draw(grid).rectangle((x * S, y * S, (x + 18) * S - 1, (y + 18) * S - 1), outline=(255, 0, 255, 255))
        draw_text(grid, x * S + 3, y * S + 3, str(i), (255, 255, 255, 255), scale=2, outline=(0, 0, 0, 255))
    grid.convert('RGB').save(os.path.join(out, 'preview_grid.png'))

    open(os.path.join(out, 'INSTALL.md'), 'w', encoding='utf-8').write(
        f"# Install '{gid}'\n\n"
        f"1. Copy `Nexo/` into `plugins/` (merges `glyphs/{gid}.yml` and `pack/assets/{ns}/textures/gui/{gid}.png`).\n"
        f"2. Copy `DeluxeMenus/gui_menus/{gid}.yml` into `plugins/DeluxeMenus/gui_menus/` and register it in `config.yml`.\n"
        f"3. `/nexo reload all` (rebuilds and resends the pack), then `/dm reload`.\n"
        f"4. Open with `/{spec.get('open_commands', [gid])[0]}`. If the art is off by a few pixels, adjust\n"
        f"   `shift_nudge` (horizontal) / `ascent_nudge` (vertical, + moves up) in the spec and rebuild,\n"
        f"   or edit `<shift:{shift}>` / `ascent: {ascent}` directly.\n")
    print(json.dumps({'texture': f'{W}x{TH}', 'ascent': ascent, 'height': TH, 'shift': shift,
                      'buttons': {b['id']: button_slots(b) for b in spec.get('buttons', [])}}, ensure_ascii=False))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    build(sys.argv[1], sys.argv[2])
