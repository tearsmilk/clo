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
    A header "tab" that sticks out above the window adds `top` px of canvas and raises ascent by the same;
    art that sticks out on the left (`canvas.left`) moves the shift left by the same (-8 - left).
See references/gui-geometry.md for the derivation and for non-chest containers.
"""
import json, math, os, random, re, sys
from PIL import Image, ImageDraw, ImageFilter, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pixfont import (draw_text, text_width, text_height, draw_block_text, block_text_size,  # noqa: E402
                     draw_material_text, material_text_size)
import pixelstyle  # noqa: E402
import sprites  # noqa: E402
import art  # noqa: E402
import props  # noqa: E402
import royal  # noqa: E402
import rustic  # noqa: E402
import shop  # noqa: E402
import safe  # noqa: E402
import scenes  # noqa: E402
import icons16  # noqa: E402

# x of the window's left edge inside the texture (> 0 when scene art sticks out on the left: spec canvas.left)
OX = 0


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
    # dark slate + gold trim (royal/fantasy kits): outline + thin gold line + bevelled body, rimmed slot wells,
    # gold corner brackets. Pair with header style 'bracket_tab', section_divider and hotbar_frame.
    # wooden board frame + old parchment + maroon wells (jobs / quest boards): header style 'sign',
    # layers bookmark / card / grid_frame, slots shown via slots_visible
    'rustic': dict(frame_style='rustic', slot_style='well', text='#371621', recess='#4d1b22',
                   slot_in='#4d1b22', slot_dk='#371621', slot_lt='#8c3f2b'),
    # brushed steel safe / vault (safe.py): rivets, light band under the client's Inventory label, steel wells
    'steel':  dict(frame_style='steel', slot_style='steel', text='#101219', recess='#191c24',
                   slot_in='#262a34', slot_dk='#101219', slot_lt='#76829a'),
    'royal':  dict(body='#2b3545', frame_style='royal', gold='#d9893f', gold_dk='#b55a41', outline='#1c1b2b',
                   slot_style='rim', slot_in='#2b3545', slot_dk='#1f2432', slot_lt='#3a4959', rim_hi='#859aa9',
                   rim_mid='#6c8294', rim_lo='#506275', text='#b3c2ca', recess='#1f2432'),
}


def window_size(rows):
    return 176, 114 + rows * 18


def slot_xy(col, row):
    return OX + 7 + col * 18, 17 + row * 18


def inv_slot_xy(col, row, rows):
    return OX + 7 + col * 18, rows * 18 + 30 + row * 18


def hotbar_xy(col, rows):
    return OX + 7 + col * 18, rows * 18 + 88


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


def draw_framed_panel(img, box, th):
    """Palette themes: dark outline with cut corners, 4px textured frame band, carved inner line, smooth body."""
    bx, by, W, Hh = box
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
    img.alpha_composite(band, (bx, by))


def draw_royal_panel(img, box, th):
    """Royal theme. A whole chest window uses royal.panel (measured: outline outside the window, gold line,
    grooves, 2px bottom outline); any other box gets a small slate plate with the same edge recipe."""
    bx, by, W, Hh = box
    if W == 176 and (Hh - 114) % 18 == 0 and 1 <= (Hh - 114) // 18 <= 6:
        return royal.panel(img, bx, by, (Hh - 114) // 18)
    d = ImageDraw.Draw(img)
    o, g, body = H(th['outline']), H(th['gold_dk']), H(th['body'])
    d.rectangle((bx, by, bx + W - 1, by + Hh - 1), fill=o)
    d.rectangle((bx + 1, by + 1, bx + W - 2, by + Hh - 2), fill=g)
    d.rectangle((bx + 2, by + 2, bx + W - 3, by + Hh - 3), fill=body)
    d.line((bx + 2, by + 2, bx + W - 3, by + 2), fill=H(th['rim_hi']))
    d.line((bx + 2, by + 3, bx + 2, by + Hh - 3), fill=H(th['rim_mid']))
    d.line((bx + 3, by + Hh - 3, bx + W - 3, by + Hh - 3), fill=H(th['slot_dk']))
    d.line((bx + W - 3, by + 3, bx + W - 3, by + Hh - 3), fill=H(th['slot_dk']))
    for cx, cy in ((0, 0), (W - 1, 0), (0, Hh - 1), (W - 1, Hh - 1)):
        img.putpixel((bx + cx, by + cy), (0, 0, 0, 0))
    for i, (ex, ln) in enumerate(((6, 18), (26, 9), (W - 25, 18), (W - 37, 8))):   # etched lines
        ey = by + 5 + (i % 2) * 2
        d.line((bx + ex, ey, bx + ex + ln, ey), fill=H(th['slot_dk']))
        d.line((bx + ex + 1, ey + 1, bx + ex + ln, ey + 1), fill=H(th['slot_lt']))


def draw_panel(img, box, th, seed=7):
    """Window body with a chamfered black outline and 2px bevel, like vanilla windows. box = (x, y, w, h)."""
    if th.get('frame_style') == 'rustic':      # frame 4px outside the window, parchment from 6px in
        bx, by, W, Hh = box
        rustic.frame(img, bx - 4, by - 4, W + 8, Hh + 6, t=10, seed=th.get('seed', 4))
        for bm in th.get('_bookmarks', []):    # bookmarks tuck under the parchment
            rustic.bookmark(img, bx + bm['x'], by + bm['y'], bm.get('w', 27), bm.get('h', 18), bm.get('icon'))
        rustic.parchment(img, bx + 6, by + 6, W - 12, Hh - 14, seed=th.get('seed', 7))
        return
    if th.get('frame_style') == 'royal':
        return draw_royal_panel(img, box, th)
    if th.get('frame_style') == 'steel':
        return safe.panel(img, box, th.get('_rows', 6), th.get('seed', 3))
    if 'frame' in th:
        return draw_framed_panel(img, box, th)
    rnd = random.Random(seed)
    bx, by, W, Hh = box
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
            px[bx + x, by + y] = c
    hi, hi2, sh, sh2 = H(th['hi']), H(th['hi2']), H(th['sh']), H(th['sh2'])
    for y in range(Hh):
        for x in range(W):
            if not inside(x, y):
                continue
            if not all(inside(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                px[bx + x, by + y] = (0, 0, 0, 255)
                continue
            d_tl, d_br = min(x, y), min(W - 1 - x, Hh - 1 - y)
            if d_tl in (1, 2) and d_tl <= d_br:
                px[bx + x, by + y] = hi if d_tl == 1 else hi2
            elif d_br in (1, 2):
                px[bx + x, by + y] = sh if d_br == 1 else sh2


def draw_rim_slot(img, x0, y0, th):
    """Raised rim around a recessed well (royal kits): light top/right rim, mid left, dark bottom rim, inner
    shadow top/left, lit inner bottom/right, light line above and dark gap below each slot."""
    if th.get('frame_style') == 'royal':
        return royal.rim_slot(img, x0, y0)
    d = ImageDraw.Draw(img)
    k, dk, lt = H(th['slot_in']), H(th['slot_dk']), H(th['slot_lt'])
    hi, mid, lo = H(th['rim_hi']), H(th['rim_mid']), H(th['rim_lo'])
    d.rectangle((x0, y0, x0 + 17, y0 + 17), fill=k)
    d.line((x0 + 1, y0, x0 + 16, y0), fill=lt)
    d.line((x0, y0 + 17, x0 + 17, y0 + 17), fill=dk)
    d.line((x0 + 1, y0 + 1, x0 + 1, y0 + 16), fill=mid)
    d.line((x0 + 2, y0 + 1, x0 + 16, y0 + 1), fill=hi)
    d.line((x0 + 16, y0 + 1, x0 + 16, y0 + 16), fill=hi)
    d.line((x0 + 2, y0 + 16, x0 + 15, y0 + 16), fill=lo)
    d.line((x0 + 2, y0 + 2, x0 + 15, y0 + 2), fill=dk)
    d.line((x0 + 2, y0 + 2, x0 + 2, y0 + 15), fill=dk)
    d.line((x0 + 3, y0 + 15, x0 + 15, y0 + 15), fill=lt)
    d.line((x0 + 15, y0 + 3, x0 + 15, y0 + 15), fill=lt)


def draw_slot(img, x0, y0, th, size=18):
    if th.get('slot_style') == 'well' and size == 18:
        return rustic.well_slot(img, x0, y0)
    if th.get('slot_style') == 'rim' and size == 18:
        return draw_rim_slot(img, x0, y0, th)
    if th.get('slot_style') == 'steel' and size == 18:
        return safe.slot(img, x0, y0)
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


def small_icon(src, sdir):
    """16px icon from 'sprite:<name>' (sprites.py), 'item:<recipe>:<ramp>...' (item_icons.py), 'shop:<kind>'
    (shop.py plaques) or a PNG path."""
    if src.startswith('sprite:'):
        return sprites.render(src[7:])
    if src.startswith('item:'):
        import item_icons
        return item_icons.render(src[5:]).image()
    if src.startswith('shop:'):                       # shop kit plaques: shop:back, shop:next:green, shop:alert
        return shop.render_icon(src[5:])
    if src.startswith('safe:'):                       # safe kit: safe:lamp, safe:lamp:red
        return safe.render_icon(src[5:])
    return load_icon(resolve(src, sdir), 16, 16)


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
                    x, y = OX + it['x'] + i, oy + it['y'] + j
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
    return OX + x, y, OX + x + w - 1, y + h - 1


def draw_layers(img, oy, layers, sdir, th):
    """Free-form scene art: backgrounds, awnings, posts, props and framed slots (all px or slot based)."""
    for L in layers:
        t = L['type']
        if 'if' in L and not L['if']:     # variants: {"if": "${picture}"} skips the layer when the value is empty
            continue
        if t == 'sprite':
            spr = sprites.render(L['name'], **L.get('opts', {}))
            if 'slot' in L:
                sx, sy = slot_xy(L['slot'] % 9, L['slot'] // 9)
                x, y = sx + (18 - spr.width) // 2, sy + (18 - spr.height) // 2
            else:
                x, y = OX + L['x'], L['y']
            if L.get('flip'):
                spr = spr.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            img.alpha_composite(spr, (x, y + oy))
            continue
        if t == 'text':                   # material lettering anywhere (relabel signs): x = centre if "center"
            mat = L.get('material', 'gold')
            mat = tuple(mat) if isinstance(mat, list) else mat
            sc, cond = L.get('scale', 1), L.get('condensed', 'bold')
            tw, _ = material_text_size(L['text'], sc, condensed=cond)
            tx = OX + L['x'] - (tw // 2 if L.get('center', True) else 0)
            draw_material_text(img, tx, oy + L['y'], L['text'], mat, scale=sc, condensed=cond)
            continue
        if t == 'shop':                   # market-stall kit (shop.py): stall, window, wells, group, button, ...
            draw_shop(img, oy, L, sdir)
            continue
        if t == 'safe':                   # steel safe kit (safe.py): door, hinge, keypad, display, wheel, ...
            draw_safe(img, oy, L)
            continue
        if t == 'nameplate':              # green ribbon label (rustic kit) centred on x
            rustic.nameplate(img, OX + L['x'], oy + L['y'], L['text'], L.get('min_w', 60))
            continue
        if t == 'bookmark':               # drawn by the rustic panel so it tucks under the parchment
            if th.get('frame_style') != 'rustic':
                rustic.bookmark(img, OX + L['x'], oy + L['y'], L.get('w', 27), L.get('h', 18), L.get('icon'))
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
        elif t == 'image':                # an artist's PNG at exactly the box size is pasted 1:1, else fitted
            src = Image.open(resolve(L['path'], sdir)).convert('RGBA')
            im = src if src.size == (w, h) else cover(resolve(L['path'], sdir), w, h, L.get('colors', 48))
            img.alpha_composite(im, (x0, y0))
        elif t == 'brackets':            # gold L brackets on the 4 corners of a box (window, section, picture)
            b, tk = L.get('size', 16), L.get('t', 5)
            for corner, (bx, by) in (('tl', (x0, y0)), ('tr', (x1 - b + 1, y0)), ('bl', (x0, y1 - b + 1)),
                                     ('br', (x1 - b + 1, y1 - b + 1))):
                img.alpha_composite(props.bracket(b, b, corner, t=tk), (bx, by))
        elif t == 'slot_bar':            # framed bar around a group of slots, each slot a dark recessed well
            pad = L.get('pad', 4)
            kind = L.get('kind', 'gold')
            inner = L.get('inner') or props.FRAME_KINDS.get(kind, props.FRAME_KINDS['gold'])['inner']
            fr = props.frame(w + 2 * pad, h + 2 * pad, kind, inner, L.get('rim'))
            art.drop_shadow(img, (x0 - pad, y0 - pad, x1 + pad, y1 + pad))
            img.alpha_composite(fr, (x0 - pad, y0 - pad))
            c0, r0, cw, ch = L['slots']
            for r in range(ch):
                for c in range(cw):
                    sx, sy = slot_xy(c0 + c, r0 + r)
                    img.alpha_composite(props.well(18, L.get('well', inner)), (sx, sy + oy))
        elif t == 'card':                 # framed picture (PNG or "scene:farm") with a ribbon nameplate (rustic kit)
            src = L.get('picture', 'scene:farm')
            if src.startswith('scene:'):
                pic = scenes.scene(src[6:], w - 6, h - 6, L.get('hero'), seed=L.get('seed', 1))
            else:                         # artist art at the inner size (box - 6) is used 1:1
                raw = Image.open(resolve(src, sdir)).convert('RGBA')
                pic = raw if raw.size == (w - 6, h - 6) else cover(resolve(src, sdir), w - 6, h - 6, L.get('colors', 48))
            rustic.card(img, x0, y0, w, h, pic, L.get('label'))
        elif t == 'patch':                # cover old text in a bought texture: each row filled with the colour
            sx = OX + L['from_x']         # found at column from_x (plank lines survive, letters vanish)
            for yy in range(y0, y1 + 1):
                c = img.getpixel((sx, yy))
                for xx in range(x0, x1 + 1):
                    img.putpixel((xx, yy), c)
        elif t == 'grid_frame':           # dark/tan/dark frame around a block of slots (rustic kit)
            c0, r0, cw, ch = L['slots']
            sx, sy = slot_xy(c0, r0)
            rustic.grid_frame(img, sx, sy + oy, cw, ch)
        elif t in props.PROPS:            # scene props sized to the box: wall, banner, pillar, rubble, ...
            opts = {k: v for k, v in L.items() if k not in ('type', 'box', 'slots', 'pad', 'above', 'flip')}
            im = props.render(t, w, h, **opts)
            if L.get('flip'):
                im = im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
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


def draw_shop(img, oy, L, sdir):
    """Shop kit parts. Positions are slots ([col, row, w, h]) or window px (x, y) like other layers."""
    p, ox = L['part'], OX
    if p == 'stall':
        shop.stall(img, ox, oy, L.get('sign', 'МАГАЗИН'), L.get('hanging', 'ОТКРЫТО'), L.get('sill_y'),
                   L.get('seed', 3), tuple(L.get('colors', ('red', 'white'))))
    elif p == 'window':
        c, r, w, h = L['slots']
        items = [small_icon(i, sdir) if i else None for i in L.get('items', [])]
        shop.shop_window(img, ox, oy, c, r, w, h, L.get('shelves', 2), L.get('seed', 1), L.get('poster'), items)
    elif p == 'wells':
        c, r, w, h = L['slots']
        shop.wells(img, ox, oy, c, r, w, h, L.get('frame', True))
        for i, ic in enumerate(L.get('icons', [])):          # icons baked into the wells (static categories)
            if ic:
                im = small_icon(ic, sdir)
                cc, rr = c + i % w, r + i // w
                img.alpha_composite(im, (ox + 8 + 18 * cc + (16 - im.width) // 2, oy + 18 + 18 * rr + (16 - im.height) // 2))
    elif p == 'group':
        c, r, w = L['slots'][:3]
        shop.slot_group(img, ox, oy, c, r, w, L.get('color', 'green'), L.get('glyph'))
    elif p == 'button':
        c, r, w, h = L['slots']
        sx, sy = ox + 7 + 18 * c, oy + 17 + 18 * r
        shop.button(img, sx + 2, sy, sx + 18 * w - 4, sy + 18 * h - 2, L.get('color', 'green'), L.get('text', ''))
    elif p == 'banner':
        shop.banner(img, ox + L.get('x', 88), oy + L['y'], L['text'], L.get('w'), L.get('seed', 2))
    elif p == 'badge':
        c, r = L['slot'] % 9, L['slot'] // 9
        shop.badge(img, ox + 8 + 18 * c, oy + 18 + 18 * r, L.get('text', ''), L.get('color', 'green'))
    elif p == 'icon':                   # a 16px plaque / item picture painted into the texture at a slot
        for sl in L.get('slot_list', [L.get('slot')]):
            im = small_icon(L['icon'], sdir)
            img.alpha_composite(im, (ox + 8 + 18 * (sl % 9) + (16 - im.width) // 2, oy + 18 + 18 * (sl // 9) + (16 - im.height) // 2))
    elif p == 'well':
        for sl in L.get('slot_list', [L.get('slot')]):
            shop.well(img, ox + 8 + 18 * (sl % 9), oy + 18 + 18 * (sl // 9))
    else:
        raise SystemExit(f"unknown shop part '{p}'")


def draw_safe(img, oy, L):
    """Safe kit parts. x / y / box are window px, slots are [col, row, ...] like other layers."""
    p, ox = L['part'], OX
    if p == 'body':                       # box volume: side + bottom faces and feet outside the window
        safe.body(img, ox, oy, 176, 114 + 18 * L.get('rows', 6), L.get('depth', 4), L.get('feet', True))
    elif p == 'open_door':               # the door swung open on the left (storage screen), before 'hinges'
        safe.open_door(img, ox, oy, L.get('x', -3), L.get('y0', 4), L.get('y1', 121), L.get('width', 44),
                       L.get('grow', 7), L.get('thick', 9), L.get('top_thick', 3))
    elif p == 'door':
        x0, y0, x1, y1 = L.get('box', [4, 4, 171, 121])
        safe.door(img, ox + x0, oy + y0, ox + x1, oy + y1, L.get('seed', 5))
    elif p == 'hinges':
        for y in L.get('ys', [16, 84]):
            safe.hinge(img, ox + L.get('x', -2), oy + y, L.get('h', 26), L.get('leaf', 12))
    elif p == 'bolts':                   # bars sticking out of the right side (spec canvas right >= length - 3)
        safe.bolts(img, ox + L.get('x', 171), [oy + y for y in L.get('ys', [30, 60, 90])], L.get('length', 10))
    elif p == 'bolt_slots':              # retracted: slots cut into the frame
        safe.bolt_receivers(img, ox + L.get('x', 170), [oy + y for y in L.get('ys', [30, 60, 90])])
    elif p == 'nameplate':
        safe.nameplate(img, ox + L.get('x', 88), oy + L['y'], L['text'], L.get('w'))
    elif p == 'plate':
        safe.small_plate(img, ox + L['x'], oy + L['y'], L['text'])
    elif p == 'display':
        c, r, n = L['slots'][:3]
        safe.display(img, ox, oy, c, r, n, L.get('lamps', []), L.get('lock'))
    elif p == 'keypad':
        c, r = L['slots'][:2]
        safe.keypad(img, ox, oy, c, r, L['labels'], {int(k): v for k, v in L.get('colors', {}).items()},
                    {int(k): v for k, v in L.get('glyphs', {}).items()})
    elif p == 'wheel':
        safe.wheel(img, ox + L['x'], oy + L['y'], L.get('r', 20), L.get('spokes', 4))
    elif p == 'keyhole':
        safe.keyhole(img, ox + L['x'], oy + L['y'])
    elif p == 'recess':
        x0, y0, x1, y1 = L['box']
        safe.recess(img, ox + x0, oy + y0, ox + x1, oy + y1)
    else:
        raise SystemExit(f"unknown safe part '{p}'")


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
    if style == 'none':                  # clickable area over scene art: no tile, just the icon (if any)
        ic = b.get('icon')
        if ic:
            spr = small_icon(ic, sdir)
            if b.get('icon_flip'):
                spr = spr.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            w, h = b.get('w', 1) * 18, b.get('h', 1) * 18
            img.alpha_composite(spr, (x0 + (w - spr.width) // 2, y0 + (h - spr.height) // 2))
        return
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
        is_sprite = icon_src.startswith(('sprite:', 'item:', 'shop:', 'safe:'))
        if is_sprite:
            spr = small_icon(icon_src, sdir)
            import tempfile
            tmp = os.path.join(tempfile.gettempdir(), f"nexo_gui_sprite_{re.sub(r'[^a-z0-9_]', '_', icon_src)}.png")
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
    if hd.get('style') == 'ribbon':
        bh = 7 * hd.get('size', 1) + 8
        return max(0, -hd.get('y', 9 - bh))
    if hd.get('style') == 'lettering':
        return max(0, -hd.get('y', 3))
    if hd.get('style') == 'bracket_tab':
        return -hd.get('top', -10) + 2
    if hd.get('style') == 'sign':
        return max(0, -hd.get('y', -16) + 8)
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
        draw_block_text(img, OX + (176 - bw) // 2, oy + 15 - bh, text, scale=hd.get('size', 3),
                        top=hd.get('top_color', '#D8D8D8'), bottom=hd.get('bottom_color', '#6E6A68'),
                        outline=hd.get('outline_color', '#111111'), depth=hd.get('depth', 0),
                        side=hd.get('side_color'))
        return
    if style == 'text':
        draw_text(img, OX + ((176 - tw) // 2 if hd.get('center', True) else 8), oy + 5, text,
                  H(hd.get('text_color', th['text'])), scale=sc)
        return
    if style == 'sign':                  # plank sign with crown, coins, pennants and crossed arrows (rustic kit)
        rustic.header(img, OX + 88 + hd.get('dx', 0), oy + hd.get('y', -16), text, w=hd.get('width', 96),
                      h=hd.get('height', 22))
        return
    if style == 'bracket_tab':           # royal tab across the top edge with '[' ']' gold brackets
        mat = hd.get('material', 'steel')
        sc = hd.get('size', 1)
        tw = material_text_size(text, sc)[0] if text and hd.get('font', 'material') == 'material' else \
            (text_width(text, scale=sc) if text else 0)
        pw = hd.get('width', max(96, tw + 24))
        ph = hd.get('height', 20 if sc == 1 else 26)
        top_y = hd.get('top', -10 if ph <= 20 else -13)
        royal.tab(img, OX, oy, (176 - pw) // 2, pw, top_y, ph)
        if text:
            tx = OX + (176 - pw) // 2 + (pw - tw) // 2
            body_top, body_h = oy + top_y + 5, ph - 10
            if hd.get('font', 'material') == 'material':
                ty = body_top + (body_h - (7 * sc + 3)) // 2
                draw_material_text(img, tx, ty, text, mat, scale=sc)
            else:
                ty = body_top + (body_h - 7 * sc) // 2
                draw_text(img, tx, ty, text, H(hd.get('text_color', '#e8eef5')), scale=sc, shadow=H('#1c1b2b'))
        return
    if style == 'ribbon':                # cloth ribbon with folded, V-cut tails (quest boards, castle scenes)
        sc = hd.get('size', 1)
        sp = hd.get('spacing', 1)
        tw = text_width(text, scale=sc, spacing=sp)
        bh = 7 * sc + 8
        rw = hd.get('width', tw + 2 * 14 + 48)
        rib = props.ribbon(rw, bh + 5, hd.get('color', '#c42f3c'))
        rx = OX + (176 - rw) // 2
        ry = oy + hd.get('y', 9 - bh)
        art.drop_shadow(img, (rx + 14, ry, rx + rw - 15, ry + bh - 1))
        img.alpha_composite(rib, (rx, ry))
        tcol = H(hd.get('text_color', '#FFFFFF'))
        if hd.get('font') == 'material':
            mw, _ = material_text_size(text, sc)
            draw_material_text(img, rx + (rw - mw) // 2, ry + (bh - 7 * sc - 3) // 2, text,
                               hd.get('material', 'gold'), scale=sc)
        else:
            draw_text(img, rx + (rw - tw) // 2, ry + (bh - 7 * sc) // 2, text, tcol, scale=sc, spacing=sp,
                      outline=art.outline_of(hd.get('color', '#c42f3c')))
        return
    if style == 'lettering':             # just the material letters, centred over the window top
        sc = hd.get('size', 2)
        mw, mh = material_text_size(text, sc)
        draw_material_text(img, OX + (176 - mw) // 2, oy + hd.get('y', 3), text, hd.get('material', 'gold'),
                           scale=sc)
        return
    pw = tw + 6 * sc + 2
    x0 = OX + (176 - pw) // 2
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
    return re.sub(r'(&|§)[0-9a-fk-or]|<(?!glyph:)[^>]+>', '', t, flags=re.I)


# ----------------------------------------------------------------------------- build

def write_nexo_items(spec, sdir, out, ns):
    """`nexo_items`: small icon items (quest cards, rewards, page arrows) that show up as REAL items in slots.
    Each gets a 16x16 texture (sprite or PNG) and a Nexo item entry; DeluxeMenus uses `material: nexo-<id>`."""
    items = spec.get('nexo_items', [])
    if not items:
        return
    tdir = os.path.join(out, f'Nexo/pack/assets/{ns}/textures/item/gui')
    os.makedirs(tdir, exist_ok=True)
    os.makedirs(os.path.join(out, 'Nexo/items'), exist_ok=True)
    lines = [f"# Icon items for the '{spec['id']}' menu - generated by minecraft-nexo-gui"]
    for it in items:
        src = it['icon']
        im = small_icon(src, sdir)
        canvas = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
        canvas.alpha_composite(im, ((16 - im.width) // 2, (16 - im.height) // 2))
        canvas.save(os.path.join(tdir, f"{it['id']}.png"))
        lines += [f"{it['id']}:", f"  itemname: \"{it.get('name', it['id'])}\"", "  material: PAPER",
                  "  excludeFromInventory: true", "  Pack:", f"    texture: {ns}:item/gui/{it['id']}"]
    open(os.path.join(out, f"Nexo/items/{spec['id']}_items.yml"), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')


def write_hint_glyphs(spec, out, ns):
    """`hint_glyphs: true`: mouse icons for tooltips (left/right click) as Nexo glyphs <ns>_lmb / <ns>_rmb.
    Use them in lore with PlaceholderAPI: '%nexo_<ns>_lmb% &7Вступить' (or <glyph:<ns>_lmb> where MiniMessage
    is parsed). Glyph height 8 sits on a text line."""
    tdir = os.path.join(out, f'Nexo/pack/assets/{ns}/textures/font/hints')
    os.makedirs(tdir, exist_ok=True)
    os.makedirs(os.path.join(out, 'Nexo/glyphs'), exist_ok=True)
    lines = ['# Tooltip hint glyphs - generated by minecraft-nexo-gui']
    custom = spec['hint_glyphs'] if isinstance(spec['hint_glyphs'], dict) else {}
    for key in ('lmb', 'rmb'):
        gid = f'{ns}_{key}'
        im = hint_icon(spec, key, sdir_of(spec))
        im.save(os.path.join(tdir, f'{gid}.png'))
        h = 8 if im.height >= 14 else im.height - 1        # 16px art -> exact half; small art ~native
        lines += [f'{gid}:', f'  texture: {ns}:font/hints/{gid}', f'  ascent: {min(h, 8)}', f'  height: {h}']
    open(os.path.join(out, f'Nexo/glyphs/{ns}_hints.yml'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')


def sdir_of(spec):
    return spec.get('_sdir', '.')


def hint_icon(spec, key, sdir):
    """Mouse hint icon: a PNG from `hint_glyphs: {"lmb": path, "rmb": path}` (cropped to its pixels) or ours."""
    custom = spec.get('hint_glyphs') if isinstance(spec.get('hint_glyphs'), dict) else {}
    if key in custom:
        im = Image.open(resolve(custom[key], sdir)).convert('RGBA')
        return im.crop(im.getbbox())
    return icons16.mouse('left' if key == 'lmb' else 'right')


def _subst(obj, var):
    """Replace ${name} in every string of a spec (variants)."""
    if isinstance(obj, dict):
        return {k: _subst(v, var) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_subst(v, var) for v in obj]
    if isinstance(obj, str):
        for k, v in var.items():
            if obj == '${' + k + '}' and not isinstance(v, str):
                return v
            obj = obj.replace('${' + k + '}', str(v))
        return obj
    return obj


def build(spec_path, out):
    """Build one menu, or one menu per entry of `variants` (same art, different picture/label/icon/commands):
    each variant's keys (plus `variant_defaults`) fill ${key} placeholders anywhere in the spec, plus ${id},
    ${index}, ${prev_id}, ${next_id}, ${prev_label}, ${next_label} (cyclic). Every variant gets OUT/<variant id>/ and everything is merged into OUT/_all/."""
    spec = json.load(open(spec_path, encoding='utf-8'))
    sdir = os.path.dirname(os.path.abspath(spec_path))
    variants = spec.pop('variants', None)
    defaults = spec.pop('variant_defaults', {})
    if not variants:
        return build_spec(spec, sdir, out)
    import shutil
    ids = [v['id'] for v in variants]
    n = len(variants)
    for i, v in enumerate(variants):
        prev, nxt = variants[i - 1], variants[(i + 1) % n]
        var = dict(defaults, **v, index=i, prev_id=prev['id'], next_id=nxt['id'],
                   prev_label=prev.get('label', prev['id']), next_label=nxt.get('label', nxt['id']))
        vs = _subst(json.loads(json.dumps(spec)), var)
        vs['id'] = f"{spec['id']}_{v['id']}"
        build_spec(vs, sdir, os.path.join(out, v['id']))
        for sub in ('Nexo', 'DeluxeMenus'):
            src = os.path.join(out, v['id'], sub)
            if os.path.isdir(src):
                shutil.copytree(src, os.path.join(out, '_all', sub), dirs_exist_ok=True)
    print(f"{len(variants)} variants -> {out}/<id>/ and merged into {out}/_all/")


def build_spec(spec, sdir, out):
    global OX
    spec['_sdir'] = sdir
    gid, ns, rows = spec['id'], spec.get('namespace', 'gui'), int(spec.get('rows', 6))
    assert 1 <= rows <= 6, 'rows must be 1..6'
    art.set_palette(spec.get('palette', 'endesga32'))
    tname = spec.get('theme', 'oak')
    th = dict(THEMES[tname]) if isinstance(tname, str) else dict(THEMES['oak'], **tname)
    th.update(spec.get('theme_overrides', {}))
    label_case = spec.get('label_case', 'keep')
    W, Hh = window_size(rows)
    cv = spec.get('canvas', {})                       # scene art may stick out of the 176px window
    OX = int(cv.get('left', 0))
    TW = OX + W + int(cv.get('right', 0))
    top = max(header_top(spec), int(cv.get('top', 0)))
    TH = Hh + top + int(cv.get('bottom', 0))
    if TW > 256 or TH > 256:
        raise SystemExit(f'texture {TW}x{TH} is over the 256x256 glyph limit - shrink canvas margins')
    tex = Image.new('RGBA', (TW, TH), (0, 0, 0, 0))
    if spec.get('background'):          # ready-made texture (bought pack): use it as is, only overlay layers
        bg = Image.open(resolve(spec['background'], sdir)).convert('RGBA')
        OX, top = spec['window_at']
        TW, TH = bg.size
        tex = bg.copy()
        for k, v in (('container_panel', False), ('draw_player_inventory', False), ('draw_free_slots', False),
                     ('preview_vanilla_under', True)):
            spec.setdefault(k, v)
    th['_bookmarks'] = [L for L in spec.get('layers', []) if L['type'] == 'bookmark']
    th['_rows'] = rows
    inv_y = top + rows * 18 + 23                      # top of a separate player-inventory panel
    inv_th = th
    if isinstance(spec.get('inventory_panel'), str):
        inv_th = dict(THEMES[spec['inventory_panel']])
    if spec.get('container_panel', True):
        draw_panel(tex, (OX, top, W, Hh), th)
    ro = spec.get('royal_ornaments')
    if ro:                               # banners, rails, crystals, streamers, key ornaments (measured kit)
        ro = ro if isinstance(ro, dict) else {}
        royal.ornaments(tex, OX, top, rows, banners=ro.get('banners', True), emblem=ro.get('emblem', True),
                        rails=ro.get('rails', True), crystals=ro.get('crystals', True),
                        meanders=ro.get('meanders', True))

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
    if spec.get('draw_free_slots', spec.get('container_panel', True)):   # scenes paint their own slots
        keep_slots |= {i for i in range(rows * 9) if i not in used}
    for i in sorted(keep_slots):
        x, y = slot_xy(i % 9, i // 9)
        draw_slot(tex, x, y + top, th)
    if spec.get('draw_player_inventory', True):
        if not spec.get('container_panel', True) or spec.get('inventory_panel'):
            draw_panel(tex, (OX, inv_y, W, Hh + top - inv_y), inv_th)
        for r in range(3):
            for c in range(9):
                x, y = inv_slot_xy(c, r, rows)
                draw_slot(tex, x, y + top, inv_th)
        for c in range(9):
            x, y = hotbar_xy(c, rows)
            draw_slot(tex, x, y + top, inv_th)
    sd = spec.get('section_divider')
    royal_kit = th.get('frame_style') == 'royal'
    if sd and royal_kit:
        royal.divider(tex, OX, top, rows, gem=(sd.get('gem', True) if isinstance(sd, dict) else True))
    elif sd:                             # gold bar + gem between the container rows and the player inventory
        sd = sd if isinstance(sd, dict) else {}
        dy = top + rows * 18 + 22 - 5
        over = sd.get('overhang', 4)
        tex.alpha_composite(props.divider(176 + 2 * over, 11, sd.get('color', th.get('gold', '#d9893f')),
                                          sd.get('gem', '#439950'), style='bar'), (OX - over, dy))
        if sd.get('brackets', True):
            for corner, bx in (('bl', OX - over - 1), ('br', OX + 176 + over - 13)):
                tex.alpha_composite(props.bracket(14, 9, corner, t=4), (bx, dy - 1))
                tex.alpha_composite(props.bracket(14, 9, 'tl' if corner == 'bl' else 'tr', t=4), (bx, dy + 3))
    hf = spec.get('hotbar_frame')
    if hf and royal_kit and spec.get('draw_player_inventory', True):
        royal.hotbar_frame(tex, OX, top, rows)
    elif hf and spec.get('draw_player_inventory', True):   # thin coloured frame with gold corners round the hotbar
        hf = hf if isinstance(hf, dict) else {}
        hx, hy = hotbar_xy(0, rows)
        hy += top
        d = ImageDraw.Draw(tex)
        d.rectangle((hx - 2, hy - 2, hx + 163, hy + 19), outline=H(hf.get('color', '#a83333')))
        gc = H(hf.get('corner', th.get('gold', '#d9893f')))
        for cx, cy, sx, sy in ((hx - 2, hy - 2, 1, 1), (hx + 163, hy - 2, -1, 1), (hx - 2, hy + 19, 1, -1),
                               (hx + 163, hy + 19, -1, -1)):
            d.line((cx, cy, cx + 4 * sx, cy), fill=gc)
            d.line((cx, cy, cx, cy + 4 * sy), fill=gc)
    if spec.get('corner_brackets'):     # gold L brackets on the window corners (royal kit, measured)
        royal.corner_brackets(tex, OX, top, rows)
    for b in spec.get('buttons', []):
        draw_button(tex, top, b, sdir, th, label_case, spec.get('icon_style'))
    # foreground layers (piles over the inventory corners...) must not cover the player's slots
    inv_box = (OX + 7, top + rows * 18 + 30, OX + 7 + 162, top + rows * 18 + 106)
    before = tex.crop(inv_box).tobytes()
    draw_layers(tex, top, [L for L in spec.get('layers', []) if L.get('above')], sdir, th)
    if spec.get('draw_player_inventory', True) and tex.crop(inv_box).tobytes() != before:
        print('warning: an "above" layer paints over the player inventory slots - keep foreground props on the '
              'panel border (y < 18*rows+30, x < 7 or x > 168)', file=sys.stderr)

    title_col = H(spec.get('title_color', th['text']))
    if spec.get('title') and not spec.get('header'):
        draw_text(tex, OX + 8, top + (7 if 'frame' in th else 5), spec['title'], title_col)
    draw_header(tex, top, spec, th)
    draw_decor(tex, top, spec.get('decor', []))

    # The client draws the "Инвентарь"/"Inventory" label itself at (8, 18r+20) on top of the glyph, so it is
    # never baked into the texture (that would double it). hide_inventory_label ships a lang override instead.
    hide_label = spec.get('hide_inventory_label', False)
    # Wherever the texture is transparent inside the window, the vanilla grey chest background shows through.
    win = tex.crop((OX, top, OX + W, top + Hh)).getchannel('A')
    corner = lambda x, y: min(x, W - 1 - x) + min(y, Hh - 1 - y) < 3     # vanilla corners are cut too
    holes = sum(1 for y in range(Hh) for x in range(W) if not win.getpixel((x, y)) and not corner(x, y))
    if spec.get('background'):
        holes = 0                        # the vanilla chest shows through on purpose (pack design)
    if holes and not spec.get('container_panel', True):
        print(f'warning: {holes} px inside the window are transparent - the vanilla chest background will show '
              f'there (check preview_holes.png)', file=sys.stderr)

    for sub in ('texture', 'Nexo/glyphs', f'Nexo/pack/assets/{ns}/textures/gui', 'DeluxeMenus/gui_menus'):
        os.makedirs(os.path.join(out, sub), exist_ok=True)
    write_nexo_items(spec, sdir, out, ns)
    if spec.get('hint_glyphs'):
        write_hint_glyphs(spec, out, ns)
    if hide_label:
        ldir = os.path.join(out, 'Nexo/pack/assets/minecraft/lang')
        os.makedirs(ldir, exist_ok=True)
        for lang in ('ru_ru', 'en_us', 'uk_ua'):
            json.dump({'container.inventory': ''}, open(os.path.join(ldir, f'{lang}.json'), 'w'))
    tex.save(os.path.join(out, 'texture', f'{gid}.png'))
    tex.save(os.path.join(out, f'Nexo/pack/assets/{ns}/textures/gui/{gid}.png'))

    # --- Nexo glyph: height = texture height keeps it 1:1; ascent 13 (+top) aligns the window top ---
    ascent = 13 + top + int(spec.get('ascent_nudge', 0))
    open(os.path.join(out, f'Nexo/glyphs/{gid}.yml'), 'w', encoding='utf-8').write(
        f"# Nexo glyph for the '{gid}' menu background. Texture is {TW}x{TH}, drawn 1:1.\n"
        f"{gid}:\n  texture: {ns}:gui/{gid}\n  ascent: {ascent}\n  height: {TH}\n")

    # --- DeluxeMenus menu ---
    shift = -8 - OX + int(spec.get('shift_nudge', 0))
    back = TW + 1 - OX
    title_text = spec.get('title_text', '')
    menu_title = f"<white><shift:{shift}><glyph:{gid}>" + (f"<shift:-{back}><dark_gray>{title_text}" if title_text else '')
    lines = [
        f"# DeluxeMenus menu '{gid}' - generated by minecraft-nexo-gui",
        f"# Register in plugins/DeluxeMenus/config.yml under gui_menus: {gid}: {{file: {gid}.yml}}",
        "# If the <glyph>/<shift> tags show as raw text, use PlaceholderAPI instead:",
        f"#   menu_title: '%nexo_shift_{shift}%%nexo_{gid}%'",
        f"menu_title: '{menu_title}'",
        "open_command:",
    ] + [f"  - {c}" for c in spec.get('open_commands', [gid])] + [f"size: {rows * 9}"]
    for k, v in spec.get('dm_menu', {}).items():   # raw menu-level DeluxeMenus keys (open_requirement, update...)
        lines.append(f"{k}: {json.dumps(v, ensure_ascii=False)}")
    if spec.get('on_open'):                  # DeluxeMenus actions run when the menu opens (reset a counter...)
        lines.append("open_commands:")
        lines += [f"  - '{c}'" for c in spec['on_open']]
    lines.append("items:")
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
        if b.get('right_commands'):
            lines.append("    right_click_commands:")
            lines += [f"      - '{c}'" for c in b['right_commands']]
        for k, v in b.get('dm', {}).items():  # raw DeluxeMenus keys: requirements, dynamic_amount, priority...
            lines.append(f"    {k}: {json.dumps(v, ensure_ascii=False)}")
    for it in spec.get('extra_items', []):   # raw DeluxeMenus items (real visible items in slots_visible etc.)
        lines.append(f"  '{it['id']}':")
        for k, v in it.items():
            if k not in ('id', 'preview', 'preview_flip'):
                lines.append(f"    {k}: {json.dumps(v, ensure_ascii=False)}")
    if not spec.get('buttons') and not spec.get('extra_items'):
        # a pure skin (storage, backpack): DeluxeMenus still needs an items section; the same title string
        # works for any plugin that lets you set an inventory title (chest shops, backpacks, vaults)
        lines[-1] = "items: {}   # skin only - reuse menu_title as the title of any 54-slot inventory"
    open(os.path.join(out, f'DeluxeMenus/gui_menus/{gid}.yml'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')

    # --- previews ---
    S = int(spec.get('preview_scale', 4))
    ptex = tex
    if spec.get('preview_vanilla_under'):    # in game the vanilla chest is drawn first, the glyph over it
        under = Image.new('RGBA', (TW, TH), (0, 0, 0, 0))
        vt = dict(THEMES['vanilla'])
        draw_panel(under, (OX, top, W, Hh), vt)
        for i in range(rows * 9):
            x, y = slot_xy(i % 9, i // 9)
            draw_slot(under, x, y + top, vt)
        for r in range(3):
            for c in range(9):
                x, y = inv_slot_xy(c, r, rows)
                draw_slot(under, x, y + top, vt)
        for c in range(9):
            x, y = hotbar_xy(c, rows)
            draw_slot(under, x, y + top, vt)
        under.alpha_composite(tex)
        ptex = under
    big = ptex.resize((TW * S, TH * S), Image.NEAREST)
    if hide_label is False and (spec.get('draw_player_inventory', True) or spec.get('background')) and \
            spec.get('inventory_label', 'Инвентарь'):
        # preview only: the label the client prints at (8, 18r+20)
        draw_text(big, (OX + 8) * S, (top + rows * 18 + 20) * S, spec.get('inventory_label', 'Инвентарь'),
                  H('#404040'), scale=S)
    tip, tb = None, None
    if spec.get('preview_tooltip'):
        tb = next(x for x in spec['buttons'] if x['id'] == spec['preview_tooltip'])
        tlines = [strip_codes(tb.get('name') or tb.get('label') or tb['id']).replace('\\n', ' ')] + \
                 [strip_codes(l) for l in tb.get('lore', [])]
        glyph_tok = re.compile(r'%nexo_([a-z0-9_]+)%|<glyph:([a-z0-9_]+)>')

        def glyph_img(name):
            for key in ('lmb', 'rmb'):
                if name.endswith('_' + key):
                    im = hint_icon(spec, key, sdir)
                    h = 8 if im.height >= 14 else im.height - 1
                    return im.resize((max(1, round(im.width * h / im.height)), h), Image.NEAREST)
            return None

        def line_w(l):
            w = 0
            parts = re.split(r'(%nexo_[a-z0-9_]+%|<glyph:[a-z0-9_]+>)', l)
            for p_ in parts:
                m = glyph_tok.fullmatch(p_) if p_ else None
                gi = glyph_img(m.group(1) or m.group(2)) if m else None
                w += (gi.width + 1) if gi else (text_width(p_) if p_ else 0)
            return w
        tw = max(line_w(l) for l in tlines) + 8
        th_ = len(tlines) * 10 + 6
        tip = Image.new('RGBA', (tw, th_), H('#100010', 240))
        ImageDraw.Draw(tip).rectangle((1, 1, tw - 2, th_ - 2), outline=H('#2D0A63'))
        for i, l in enumerate(tlines):
            col = H('#FFFF55') if i == 0 else H('#AAAAAA')
            x = 4
            for p_ in re.split(r'(%nexo_[a-z0-9_]+%|<glyph:[a-z0-9_]+>)', l):
                if not p_:
                    continue
                m = glyph_tok.fullmatch(p_)
                gi = glyph_img(m.group(1) or m.group(2)) if m else None
                if gi:
                    tip.alpha_composite(gi, (x, 4 + i * 10 - 1))
                    x += gi.width + 1
                else:
                    draw_text(tip, x, 4 + i * 10, p_, col, shadow=darken(col, 0.75))
                    x += text_width(p_)
        tip = tip.resize((tw * S, th_ * S), Image.NEAREST)
    pad_r = (tip.width + 56) if tip else 40
    canvas = Image.new('RGBA', (TW * S + 40 + pad_r, TH * S + 80), H('#20161E'))
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
        ic = small_icon(pv, sdir)
        if ic.width > 16 or ic.height > 16:
            ic = load_icon_img(ic, 16)
        if it.get('preview_flip'):
            ic = ic.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
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
        canvas.alpha_composite(tip, (40 + TW * S + 16, 40 + (sy + top) * S))
    canvas.convert('RGB').save(os.path.join(out, 'preview.png'))

    grid = big.copy()
    for i in range(rows * 9):
        x, y = slot_xy(i % 9, i // 9)
        y += top
        ImageDraw.Draw(grid).rectangle((x * S, y * S, (x + 18) * S - 1, (y + 18) * S - 1), outline=(255, 0, 255, 255))
        draw_text(grid, x * S + 3, y * S + 3, str(i), (255, 255, 255, 255), scale=2, outline=(0, 0, 0, 255))
    grid.convert('RGB').save(os.path.join(out, 'preview_grid.png'))
    if holes and not spec.get('container_panel', True):
        hv = tex.copy()
        hp = hv.load()
        for y in range(top, top + Hh):
            for x in range(OX, OX + W):
                if hp[x, y][3] == 0 and not corner(x - OX, y - top):
                    hp[x, y] = (255, 0, 255, 255)
        hv.resize((TW * S, TH * S), Image.NEAREST).save(os.path.join(out, 'preview_holes.png'))

    open(os.path.join(out, 'INSTALL.md'), 'w', encoding='utf-8').write(
        f"# Install '{gid}'\n\n"
        f"1. Copy `Nexo/` into `plugins/` (merges `glyphs/{gid}.yml` and `pack/assets/{ns}/textures/gui/{gid}.png`).\n"
        f"2. Copy `DeluxeMenus/gui_menus/{gid}.yml` into `plugins/DeluxeMenus/gui_menus/` and register it in `config.yml`.\n"
        f"3. `/nexo reload all` (rebuilds and resends the pack), then `/dm reload`.\n"
        f"4. Open with `/{spec.get('open_commands', [gid])[0]}`. If the art is off by a few pixels, adjust\n"
        f"   `shift_nudge` (horizontal) / `ascent_nudge` (vertical, + moves up) in the spec and rebuild,\n"
        f"   or edit `<shift:{shift}>` / `ascent: {ascent}` directly.\n"
        + (f"5. `Nexo/items/{gid}_items.yml` adds the icon items used in the menu (`material: nexo-<id>`); check one\n"
           f"   with `/nexo give <player> {spec['nexo_items'][0]['id']}`.\n" if spec.get('nexo_items') else '')
        + ("6. `Nexo/pack/assets/minecraft/lang/*.json` blanks the \"Inventory\" label of ALL chest menus (the art sits\n"
           "   where the client would print it). Leave these files out if other menus need the label; if the pack\n"
           "   already has lang files, merge the `container.inventory` key into them.\n" if hide_label else ''))
    print(json.dumps({'texture': f'{TW}x{TH}', 'ascent': ascent, 'height': TH, 'shift': shift,
                      'buttons': {b['id']: button_slots(b) for b in spec.get('buttons', [])}}, ensure_ascii=False))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    build(sys.argv[1], sys.argv[2])
