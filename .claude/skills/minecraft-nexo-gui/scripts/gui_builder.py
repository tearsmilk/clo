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


# ----------------------------------------------------------------------------- colours / themes

def H(h, a=255):
    if isinstance(h, tuple):
        return h
    h = h.lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def mix(c, t, k):
    c, t = H(c), H(t)
    return tuple(int(c[i] + (t[i] - c[i]) * k) for i in range(3)) + (255,)


def lighten(c, k): return mix(c, (255, 255, 255), k)
def darken(c, k): return mix(c, (0, 0, 0), k)


# Each theme: panel fill style + bevel + slot colours + text colours.
THEMES = {
    # vanilla Minecraft window colours (C6C6C6 fill, white/555555 bevel, 8B8B8B slots)
    'vanilla': dict(fill=['#C6C6C6'], seam=None, hi='#FFFFFF', hi2='#FFFFFF', sh='#555555', sh2='#555555',
                    slot_dk='#373737', slot_lt='#FFFFFF', slot_in='#8B8B8B', text='#404040', recess='#8B8B8B'),
    'oak':    dict(fill=['#C49A5C', '#BC9355', '#C9A063', '#B58C4F'], seam='#8E6838', hi='#F3DFAE', hi2='#E2C68C',
                   sh='#5A3D1C', sh2='#7A5530', slot_dk='#3E2A12', slot_lt='#FBEFCF', slot_in='#7C5A33', text='#3A1A08', recess='#6E4E2B'),
    'spruce': dict(fill=['#7A5A3A', '#735436', '#806040', '#6C4F33'], seam='#4E3822', hi='#B8977A', hi2='#9A7C60',
                   sh='#2E2012', sh2='#45311F', slot_dk='#24170B', slot_lt='#C9AE92', slot_in='#4A3524', text='#F2E4D0', recess='#3E2C1C'),
    'birch':  dict(fill=['#D8C88E', '#D2C188', '#DDCD95', '#CCBA80'], seam='#A89660', hi='#FFF6D2', hi2='#EFE3B0',
                   sh='#7C6A3C', sh2='#998652', slot_dk='#54462A', slot_lt='#FFFBEA', slot_in='#A8975F', text='#3A2E14', recess='#9A8854'),
    'stone':  dict(fill=['#8E8E8E', '#878787', '#959595', '#828282'], seam='#6A6A6A', hi='#D8D8D8', hi2='#BDBDBD',
                   sh='#3C3C3C', sh2='#565656', slot_dk='#2A2A2A', slot_lt='#F0F0F0', slot_in='#5E5E5E', text='#202020', recess='#4E4E4E'),
    'nether': dict(fill=['#5A2226', '#542024', '#61262A', '#4E1D21'], seam='#3A1215', hi='#A85A5E', hi2='#8A4448',
                   sh='#1E0709', sh2='#300D10', slot_dk='#160405', slot_lt='#C77A7E', slot_in='#3A1416', text='#F6D9C0', recess='#2A0C0E'),
    'dark':   dict(fill=['#2C2F36', '#2A2D33', '#30333A', '#272A30'], seam='#1C1E22', hi='#5C616C', hi2='#4A4F58',
                   sh='#0E0F12', sh2='#17191C', slot_dk='#0A0B0D', slot_lt='#6E7480', slot_in='#1F2126', text='#E8E8F0', recess='#16181C'),
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


def draw_panel(img, oy, rows, th, seed=7):
    """Window body with a chamfered black outline and 2px bevel, like vanilla windows."""
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
    """Procedural pixel textures for tile backgrounds."""
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
                  fill=lighten(base, 0.28))
    return im


def gradient(base, w, h):
    base = H(base)
    im = Image.new('RGBA', (w, h))
    d = ImageDraw.Draw(im)
    for yy in range(h):
        d.line((0, yy, w, yy), fill=mix(lighten(base, 0.28), darken(base, 0.35), yy / max(1, h - 1)))
    return im


def cover(path, w, h, colors=48):
    """Scale an illustration to cover w x h (centre crop) and posterize it to a pixel-art palette."""
    im = Image.open(path).convert('RGB')
    k = max(w / im.width, h / im.height)
    im = im.resize((max(w, math.ceil(im.width * k)), max(h, math.ceil(im.height * k))), Image.LANCZOS)
    l, t = (im.width - w) // 2, (im.height - h) // 2
    im = im.crop((l, t, l + w, t + h))
    return im.quantize(colors=colors, method=Image.MEDIANCUT).convert('RGBA')


def load_icon(path, max_w, max_h, alpha_cut=110):
    """Fit an RGBA icon into max_w x max_h with a hard alpha edge (pixel-art friendly)."""
    ic = Image.open(path).convert('RGBA')
    bb = ic.getbbox()
    if bb:
        ic = ic.crop(bb)
    k = min(max_w / ic.width, max_h / ic.height)
    nw, nh = max(1, round(ic.width * k)), max(1, round(ic.height * k))
    resample = Image.NEAREST if (ic.width % nw == 0 and ic.height % nh == 0) else Image.LANCZOS
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


# ----------------------------------------------------------------------------- buttons

def resolve(path, sdir):
    return path if os.path.isabs(path) else os.path.join(sdir, path)


def draw_button(img, oy, b, sdir, th, label_case, spec_icon_style=None):
    style = b.get('style', 'sunburst')
    x0, y0 = slot_xy(b['x'], b['y'])
    y0 += oy
    w, h = b.get('w', 1) * 18, b.get('h', 1) * 18
    inset = b.get('inset', 1)              # 1px gap to neighbours; 0 = tiles touch (bento look)
    x0, y0, w, h = x0 + inset, y0 + inset, w - 2 * inset, h - 2 * inset
    base = H(b.get('color', '#5DAA3A'))
    outline = H(b.get('outline', '#1E1408'))

    # background
    if style == 'sunburst':
        tile = sunburst(base, w, h, 0.42 if b.get('label') else 0.5)
    elif style == 'gradient':
        tile = gradient(base, w, h)
    elif style == 'pattern':
        tile = pattern(b.get('pattern', 'noise'), base, w, h, seed=hash(b['id']) & 0xff)
    elif style == 'image':
        tile = cover(resolve(b['image'], sdir), w, h, b.get('colors', 48))
    else:  # flat
        tile = Image.new('RGBA', (w, h), base)

    # frame: outline + inner light/dark bevel (or a coloured inner frame for "card" looks)
    td = ImageDraw.Draw(tile)
    td.rectangle((0, 0, w - 1, h - 1), outline=outline)
    if b.get('frame'):
        td.rectangle((1, 1, w - 2, h - 2), outline=H(b['frame']))
    else:
        td.line((1, 1, w - 2, 1), fill=lighten(base, 0.45))
        td.line((1, 1, 1, h - 2), fill=lighten(base, 0.45))
        td.line((1, h - 2, w - 2, h - 2), fill=darken(base, 0.35))
        td.line((w - 2, 1, w - 2, h - 2), fill=darken(base, 0.35))

    if b.get('disabled'):                # grey out the background only; the icon becomes a coloured line-art
        g = ImageOps.grayscale(tile.convert('RGB')).convert('RGBA')
        tile = Image.blend(g, Image.new('RGBA', g.size, (40, 40, 40, 255)), 0.35)
        td = ImageDraw.Draw(tile)

    # label geometry
    label = b.get('label') or ''
    case = b.get('label_case', label_case)
    if case == 'upper':
        label = label.upper()
    label = label.replace('\\n', '\n')
    lstyle = b.get('label_style', 'shadow')
    lpos = b.get('label_pos', 'bottom')
    label_zone = 0
    if label:
        tw, tht = text_width(label), text_height(label)
        maxw = w - {'plaque': 8, 'wood': 11, 'stone': 11}.get(lstyle, 4)
        if tw > maxw:
            raise SystemExit(f"label '{label}' is {tw}px but button '{b['id']}' fits {maxw}px - shorten it, "
                             f"split it into two lines with \\n, or widen the button")
        label_zone = tht + (6 if lstyle in ('plaque', 'bar', 'wood', 'stone') else 3)
        if b.get('icon') and label_zone > h - 4:
            raise SystemExit(f"label '{label}' is too tall for button '{b['id']}' ({h}px high)")

    # icon (optionally inside a framed box)
    if b.get('icon'):
        m = 1 if w <= 18 or h <= 18 else 3          # small 1x1 buttons: let the icon fill the slot
        top_free = m + (label_zone if lpos == 'top' else 0)
        avail_h = h - 2 * m - label_zone
        avail_w = w - 2 * m
        fpad = 3 if b.get('icon_frame') else 0
        size = b.get('icon_size') or min(avail_w, avail_h) - 2 * fpad
        style_opts = dict(spec_icon_style or {}, **(b.get('icon_style') or {}))
        if style_opts.get('enabled', bool(style_opts)) or b.get('disabled'):
            sil = style_opts.get('silhouette_color', '#E08A2E') if b.get('disabled') else None
            ic = pixelstyle.stylize(Image.open(resolve(b['icon'], sdir)), size=size,
                                    colors=style_opts.get('colors', 10), outline=style_opts.get('outline', 'auto'),
                                    light=style_opts.get('light', True), palette=style_opts.get('palette'),
                                    extrude_depth=0 if sil else style_opts.get('extrude', 0),
                                    sparkle=style_opts.get('sparkle', False) or b.get('sparkle', False),
                                    silhouette_color=sil)
            if ic.width > size or ic.height > size:      # extrude/sparkle grow the canvas; keep it inside
                ic.thumbnail((size + 4, size + 4), Image.NEAREST)
        else:
            ic = load_icon(resolve(b['icon'], sdir), size, size)
        bw, bh = ic.width + 2 * fpad, ic.height + 2 * fpad
        bx = (w - bw) // 2
        by = top_free + (avail_h - bh) // 2
        if b.get('icon_frame'):
            fc = H(b.get('icon_frame_color', darken(base, 0.25)))
            bevel_box(tile, (bx, by, bx + bw - 1, by + bh - 1), fc, outline=darken(fc, 0.55),
                      hi=lighten(fc, 0.25), sh=darken(fc, 0.3))
        shadow = Image.new('RGBA', ic.size, (0, 0, 0, 0))
        shadow.putalpha(ic.getchannel('A').point(lambda v: 90 if v else 0))
        tile.alpha_composite(shadow, (bx + fpad + 1, by + fpad + 1))
        tile.alpha_composite(ic, (bx + fpad, by + fpad))

    # label
    if label:
        tw, tht = text_width(label), text_height(label)
        tcol = H(b.get('label_color', '#FFFFFF'))
        if lstyle == 'plaque':           # dark plate with a light rim, like the reference menus
            pw, ph = tw + 6, tht + 5
            px0 = (w - pw) // 2
            py0 = (h - ph) // 2 if not b.get('icon') and h < 40 else ((h - ph - 3) if lpos == 'bottom' else 3)
            pc = H(b.get('plaque_color', darken(base, 0.62)))
            bevel_box(tile, (px0, py0, px0 + pw - 1, py0 + ph - 1), pc, outline=darken(pc, 0.5),
                      hi=lighten(pc, 0.22), chamfer=1)
            draw_text(tile, px0 + 3, py0 + 3, label, tcol, shadow=darken(pc, 0.6), align='center')
        elif lstyle in ('wood', 'stone'):  # pixel UI-kit plates with nails / chips
            pw, ph = tw + 10, min(tht + 6, h - 2)
            px0 = (w - pw) // 2
            py0 = (h - ph) // 2 if not b.get('icon') and h < 40 else ((h - ph - 2) if lpos == 'bottom' else 2)
            plate(tile, (px0, py0, px0 + pw - 1, py0 + ph - 1), lstyle, b.get('plaque_color'))
            pc = H(b.get('plaque_color') or ('#D9895A' if lstyle == 'wood' else '#9A968C'))
            draw_text(tile, px0 + 5, py0 + (ph - 7) // 2 - (1 if ph >= tht + 6 else 0), label, H(b.get('label_color', '#FFFFFF')),
                      shadow=darken(pc, 0.55), align='center')
        elif lstyle == 'bar':            # full-width band
            ph = tht + 5
            py0 = (h - ph - 1) if lpos == 'bottom' else 1
            if not b.get('icon') and not b.get('image') and h < 24:
                py0 = (h - ph) // 2
            pc = H(b.get('plaque_color', darken(base, 0.45)))
            ImageDraw.Draw(tile).rectangle((1, py0, w - 2, py0 + ph - 1), fill=pc)
            ImageDraw.Draw(tile).line((1, py0, w - 2, py0), fill=darken(pc, 0.4))
            draw_text(tile, (w - tw) // 2, py0 + 3, label, tcol, shadow=darken(pc, 0.6), align='center')
        else:                            # text with Minecraft drop shadow
            if not b.get('icon'):
                ty = (h - (tht - (2 if tht % 10 == 9 else 0))) // 2   # centre on capitals, ignore descender rows
            else:
                ty = (h - tht - 3) if lpos == 'bottom' else 3
            draw_text(tile, (w - tw) // 2, ty, label, tcol, shadow=darken(base, 0.7), align='center')

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
    bevel_box(img, (x0, y0, x0 + pw - 1, y1), col, outline=(0, 0, 0, 255), hi=lighten(col, 0.3), sh=darken(col, 0.4))
    ty = y0 + ((y1 - y0 + 1) - 7 * sc) // 2
    draw_text(img, x0 + 3 * sc + 1, ty, text, tcol, scale=sc, shadow=darken(col, 0.6))
    if hd.get('rivets', True):
        ry = (y0 + y1) // 2 - 2
        for rx in (x0 - 7, x0 + pw + 2):
            bevel_box(img, (rx, ry, rx + 4, ry + 4), darken(col, 0.2), outline=(0, 0, 0, 255), hi=lighten(col, 0.2))


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
        c = H(pnl.get('color', th['recess']))
        bevel_box(tex, (x0 - pad, top + y0 - pad, x1 + pad, top + y1 + pad), c,
                  outline=None, hi=darken(c, 0.45), sh=lighten(c, 0.35))

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

    title_col = H(spec.get('title_color', th['text']))
    if spec.get('title') and not spec.get('header'):
        draw_text(tex, 8, top + 5, spec['title'], title_col)
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
            if k != 'id':
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
