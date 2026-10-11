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

Geometry (vanilla generic chest screen, verified against the chest container layout):
    window width 176, height 114 + rows*18
    container slot (col,row) outer box at x = 7 + col*18, y = 17 + row*18 (18x18, item at +1,+1)
    player inventory slot boxes at y = rows*18 + 30 (+18 per row), hotbar at rows*18 + 88
    (ChestMenu puts the items at 103 + (rows-4)*18 and 161 + (rows-4)*18)
    title text origin is (8, 6) and a glyph line's top sits at 13 - ascent,
    so ascent 13 + shift -8 puts the texture's top-left on the window's top-left.
See references/gui-geometry.md for the derivation and for non-chest containers.
"""
import json, math, os, random, sys
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pixfont import draw_text, text_width  # noqa: E402


def H(h, a=255):
    h = h.lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def mix(c, t, k):
    return tuple(int(c[i] + (t[i] - c[i]) * k) for i in range(3)) + (255,)


THEMES = {
    # name: (plank colours, seam, highlight, highlight2, shadow, shadow2, slot dark, slot light, slot inner, title colour)
    'oak':    (['#C49A5C', '#BC9355', '#C9A063', '#B58C4F'], '#8E6838', '#F3DFAE', '#E2C68C', '#5A3D1C', '#7A5530', '#3E2A12', '#FBEFCF', '#7C5A33', '#3A1A08'),
    'spruce': (['#7A5A3A', '#735436', '#806040', '#6C4F33'], '#4E3822', '#B8977A', '#9A7C60', '#2E2012', '#45311F', '#24170B', '#C9AE92', '#4A3524', '#F2E4D0'),
    'birch':  (['#D8C88E', '#D2C188', '#DDCD95', '#CCBA80'], '#A89660', '#FFF6D2', '#EFE3B0', '#7C6A3C', '#998652', '#54462A', '#FFFBEA', '#A8975F', '#3A2E14'),
    'stone':  (['#8E8E8E', '#878787', '#959595', '#828282'], '#6A6A6A', '#D8D8D8', '#BDBDBD', '#3C3C3C', '#565656', '#2A2A2A', '#F0F0F0', '#5E5E5E', '#202020'),
    'nether': (['#5A2226', '#542024', '#61262A', '#4E1D21'], '#3A1215', '#A85A5E', '#8A4448', '#1E0709', '#300D10', '#160405', '#C77A7E', '#3A1416', '#F6D9C0'),
    'dark':   (['#2C2F36', '#2A2D33', '#30333A', '#272A30'], '#1C1E22', '#5C616C', '#4A4F58', '#0E0F12', '#17191C', '#0A0B0D', '#6E7480', '#1F2126', '#E8E8F0'),
}


def window_size(rows):
    return 176, 114 + rows * 18


def slot_xy(col, row):
    return 7 + col * 18, 17 + row * 18


def inv_slot_xy(col, row, rows):
    return 7 + col * 18, rows * 18 + 30 + row * 18


def hotbar_xy(col, rows):
    return 7 + col * 18, rows * 18 + 88


def draw_panel(img, rows, theme, seed=7):
    """Planked panel with a chamfered black outline and 2px bevel, like vanilla windows."""
    planks, seam, hi, hi2, sh, sh2 = [H(c) for c in theme[0]], H(theme[1]), H(theme[2]), H(theme[3]), H(theme[4]), H(theme[5])
    rnd = random.Random(seed)
    W, Hh = window_size(rows)
    px = img.load()

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
            joint = (x + (row % 2) * 44) % 88 == 0
            if y % 7 == 6 or joint:
                px[x, y] = seam
            else:
                px[x, y] = planks[(row + x // 11) % 4] if rnd.random() > 0.08 else planks[rnd.randrange(4)]
    for y in range(Hh):
        for x in range(W):
            if not inside(x, y):
                continue
            if not all(inside(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                px[x, y] = (0, 0, 0, 255)
                continue
            d_tl, d_br = min(x, y), min(W - 1 - x, Hh - 1 - y)
            if d_tl in (1, 2) and d_tl <= d_br:
                px[x, y] = hi if d_tl == 1 else hi2
            elif d_br in (1, 2):
                px[x, y] = sh if d_br == 1 else sh2


def draw_slot(img, x0, y0, theme, size=18):
    dk, lt, inn = H(theme[6]), H(theme[7]), H(theme[8])
    d = ImageDraw.Draw(img)
    d.rectangle((x0, y0, x0 + size - 1, y0 + size - 1), fill=inn)
    d.line((x0, y0, x0 + size - 2, y0), fill=dk)
    d.line((x0, y0, x0, y0 + size - 2), fill=dk)
    d.line((x0 + 1, y0 + size - 1, x0 + size - 1, y0 + size - 1), fill=lt)
    d.line((x0 + size - 1, y0 + 1, x0 + size - 1, y0 + size - 1), fill=lt)


def load_icon(path, max_w, max_h, alpha_cut=110):
    """Fit an RGBA icon into max_w x max_h with a hard alpha edge (pixel-art friendly)."""
    ic = Image.open(path).convert('RGBA')
    bb = ic.getbbox()
    if bb:
        ic = ic.crop(bb)
    k = min(max_w / ic.width, max_h / ic.height)
    nw, nh = max(1, round(ic.width * k)), max(1, round(ic.height * k))
    # Pixel-art sources that only need integer downscaling stay crisp with NEAREST.
    resample = Image.NEAREST if (ic.width % nw == 0 and ic.height % nh == 0) else Image.LANCZOS
    ic = ic.resize((nw, nh), resample)
    ic.putalpha(ic.getchannel('A').point(lambda v: 255 if v > alpha_cut else 0))
    return ic


def draw_button(img, b, spec_dir, theme):
    style = b.get('style', 'sunburst')
    x0, y0 = slot_xy(b['x'], b['y'])
    w, h = b.get('w', 1) * 18, b.get('h', 1) * 18
    # inset by 1px so neighbouring buttons keep a 2px gap, like the reference GUIs
    x0, y0, w, h = x0 + 1, y0 + 1, w - 2, h - 2
    base = H(b.get('color', '#5DAA3A'))
    light, dark = mix(base, (255, 255, 255), 0.28), mix(base, (0, 0, 0), 0.35)
    tile = Image.new('RGBA', (w, h), base)
    td = ImageDraw.Draw(tile)
    if style == 'sunburst':
        cx, cy = w / 2, h * (0.42 if b.get('label') else 0.5)
        n = 16
        for i in range(n):
            a0 = i * 2 * math.pi / n
            a1 = a0 + math.pi / n
            R = 200
            td.polygon([(cx, cy), (cx + R * math.cos(a0), cy + R * math.sin(a0)), (cx + R * math.cos(a1), cy + R * math.sin(a1))], fill=light)
    elif style == 'gradient':
        for yy in range(h):
            td.line((0, yy, w, yy), fill=mix(light, dark, yy / max(1, h - 1)))
    # bevel + outline
    td.rectangle((0, 0, w - 1, h - 1), outline=H('#1E1408'))
    td.line((1, 1, w - 2, 1), fill=mix(light, (255, 255, 255), 0.45))
    td.line((1, 1, 1, h - 2), fill=mix(light, (255, 255, 255), 0.45))
    td.line((1, h - 2, w - 2, h - 2), fill=dark)
    td.line((w - 2, 1, w - 2, h - 2), fill=dark)
    label = (b.get('label') or '').upper()
    label_h = 9 if label else 0
    if b.get('icon'):
        ip = b['icon'] if os.path.isabs(b['icon']) else os.path.join(spec_dir, b['icon'])
        max_icon = b.get('icon_size') or min(w - 6, h - 5 - label_h)
        ic = load_icon(ip, max_icon, max_icon)
        ix = (w - ic.width) // 2
        iy = 2 + (h - 4 - label_h - ic.height) // 2
        shadow = Image.new('RGBA', ic.size, (0, 0, 0, 0))
        shadow.putalpha(ic.getchannel('A').point(lambda v: 90 if v else 0))
        tile.alpha_composite(shadow, (ix + 1, iy + 1))
        tile.alpha_composite(ic, (ix, iy))
    if label:
        tw = text_width(label)
        # Letters need their 1px gap plus the 1px outline on both sides; squeezing them merges the glyphs
        # into an unreadable blob, so refuse instead of drawing it. Rule of thumb: 8 letters per 3-slot button.
        if tw > w - 4:
            raise SystemExit(f"label '{label}' is {tw}px but button '{b['id']}' fits {w - 4}px "
                             f"(~{(w - 3) // 6} letters) - shorten the label or widen the button")
        # Minecraft-style 1px drop shadow keeps the 1px letter gaps open (a full outline would fill them)
        draw_text(tile, (w - tw) // 2, h - 9, label, (255, 255, 255, 255), shadow=mix(base, (0, 0, 0), 0.7))
    img.alpha_composite(tile, (x0, y0))


def strip_codes(t):
    """Drop &x / §x legacy colour codes and <tags> for preview text."""
    import re
    return re.sub(r'(&|§)[0-9a-fk-or]|<[^>]+>', '', t, flags=re.I)


def button_slots(b):
    return [(b['y'] + r) * 9 + b['x'] + c for r in range(b.get('h', 1)) for c in range(b.get('w', 1))]


def build(spec_path, out):
    spec = json.load(open(spec_path, encoding='utf-8'))
    sdir = os.path.dirname(os.path.abspath(spec_path))
    gid, ns, rows = spec['id'], spec.get('namespace', 'gui'), int(spec.get('rows', 6))
    assert 1 <= rows <= 6, 'rows must be 1..6'
    theme = THEMES[spec.get('theme', 'oak')] if isinstance(spec.get('theme', 'oak'), str) else spec['theme']
    W, Hh = window_size(rows)
    tex = Image.new('RGBA', (W, Hh), (0, 0, 0, 0))
    draw_panel(tex, rows, theme)

    used = set()
    for b in spec.get('buttons', []):
        s = button_slots(b)
        clash = used.intersection(s)
        if clash:
            raise SystemExit(f"button '{b['id']}' overlaps slots {sorted(clash)}")
        if b['x'] + b.get('w', 1) > 9 or b['y'] + b.get('h', 1) > rows:
            raise SystemExit(f"button '{b['id']}' does not fit a 9x{rows} grid")
        used.update(s)
    # plain slots for every container slot not covered by a button (unless hidden)
    if spec.get('draw_free_slots', True):
        for i in range(rows * 9):
            if i not in used:
                draw_slot(tex, *slot_xy(i % 9, i // 9), theme)
    for r in range(3):
        for c in range(9):
            draw_slot(tex, *inv_slot_xy(c, r, rows), theme)
    for c in range(9):
        draw_slot(tex, *hotbar_xy(c, rows), theme)
    for b in spec.get('buttons', []):
        draw_button(tex, b, sdir, theme)

    title_col = H(spec.get('title_color', theme[9]))
    if spec.get('title'):
        draw_text(tex, 8, 5, spec['title'].upper(), title_col)
    if spec.get('inventory_label', 'Инвентарь'):
        draw_text(tex, 8, rows * 18 + 20, spec.get('inventory_label', 'Инвентарь').upper(), mix(title_col, H(theme[0][0]), 0.25))

    for sub in ('texture', 'Nexo/glyphs', f'Nexo/pack/assets/{ns}/textures/gui', 'DeluxeMenus/gui_menus'):
        os.makedirs(os.path.join(out, sub), exist_ok=True)
    tex.save(os.path.join(out, 'texture', f'{gid}.png'))
    tex.save(os.path.join(out, f'Nexo/pack/assets/{ns}/textures/gui/{gid}.png'))

    # --- Nexo glyph: height = texture height keeps it 1:1; ascent 13 aligns the top edge ---
    ascent = 13 + int(spec.get('ascent_nudge', 0))
    glyph = (f"# Nexo glyph for the '{gid}' menu background. Texture is {W}x{Hh}, drawn 1:1.\n"
             f"{gid}:\n"
             f"  texture: {ns}:gui/{gid}\n"
             f"  ascent: {ascent}\n"
             f"  height: {Hh}\n")
    open(os.path.join(out, f'Nexo/glyphs/{gid}.yml'), 'w', encoding='utf-8').write(glyph)

    # --- DeluxeMenus menu ---
    shift = -8 + int(spec.get('shift_nudge', 0))
    back = W + 1  # glyph advance = drawn width + 1px spacing; shifting back lets plain text follow
    title_text = spec.get('title_text', '')
    menu_title = f"<white><shift:{shift}><glyph:{gid}>" + (f"<shift:-{back}><dark_gray>{title_text}" if title_text else '')
    lines = [
        f"# DeluxeMenus menu '{gid}' - generated by minecraft-nexo-gui",
        f"# Register in plugins/DeluxeMenus/config.yml under gui_menus: {gid}: {{file: {gid}.yml}}",
        f"# If the <glyph>/<shift> tags show as raw text, use PlaceholderAPI instead:",
        f"#   menu_title: '%nexo_shift_{shift}%%nexo_{gid}%'",
        f"menu_title: '{menu_title}'",
        "open_command:",
    ]
    for c in spec.get('open_commands', [gid]):
        lines.append(f"  - {c}")
    lines += [f"size: {rows * 9}", "items:"]
    for b in spec.get('buttons', []):
        slots = button_slots(b)
        lines += [f"  '{b['id']}':",
                  "    material: PAPER",
                  "    item_model: nexo:empty   # invisible - the glyph draws the button",
                  f"    slots: [{', '.join(map(str, slots))}]",
                  f"    display_name: '{b.get('name', b.get('label', b['id']))}'"]
        if b.get('lore'):
            lines.append("    lore:")
            lines += [f"      - '{l}'" for l in b['lore']]
        if b.get('hide_tooltip'):
            lines.append("    hide_tooltip: true")
        cmds = b.get('commands') or []
        if cmds:
            lines.append("    left_click_commands:")
            lines += [f"      - '{c}'" for c in cmds]
    open(os.path.join(out, f'DeluxeMenus/gui_menus/{gid}.yml'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')

    # --- previews ---
    S = int(spec.get('preview_scale', 4))
    big = tex.resize((W * S, Hh * S), Image.NEAREST)
    bgp = spec.get('preview_background')
    tt = spec.get('preview_tooltip')
    tip = None
    if tt:
        b = next(x for x in spec['buttons'] if x['id'] == tt)
        tlines = [(b.get('label') or b['id']).upper()] + [strip_codes(l).upper() for l in b.get('lore', [])]
        tw = max(text_width(l) for l in tlines) + 8
        th = len(tlines) * 10 + 6
        tip = Image.new('RGBA', (tw, th), H('#100010', 240))
        td = ImageDraw.Draw(tip)
        td.rectangle((1, 1, tw - 2, th - 2), outline=H('#2D0A63'))
        for i, l in enumerate(tlines):
            col = H('#FFFF55') if i == 0 else H('#AAAAAA')
            draw_text(tip, 4, 4 + i * 10, l, col, shadow=mix(col, (0, 0, 0), 0.75))
        tip = tip.resize((tw * S, th * S), Image.NEAREST)
    pad_r = (tip.width + 56) if tip else 40
    canvas = Image.new('RGBA', (W * S + 80 + pad_r, Hh * S + 80), H('#20161E'))
    if bgp:
        bgp = bgp if os.path.isabs(bgp) else os.path.join(sdir, bgp)
        bg = Image.open(bgp).convert('RGBA')
        k = max(canvas.width / bg.width, canvas.height / bg.height)
        bg = bg.resize((math.ceil(bg.width * k), math.ceil(bg.height * k))).crop((0, 0, canvas.width, canvas.height))
        bg = bg.filter(ImageFilter.GaussianBlur(8))
        bg.alpha_composite(Image.new('RGBA', bg.size, (16, 10, 20, 140)))
        canvas = bg
    canvas.alpha_composite(big, (40, 40))
    if tip:
        sx, sy = slot_xy(b['x'], b['y'])
        hl = Image.new('RGBA', (16 * S, 16 * S), (255, 255, 255, 80))
        canvas.alpha_composite(hl, (40 + (sx + 1) * S, 40 + (sy + 1) * S))
        canvas.alpha_composite(tip, (40 + W * S + 16, 40 + sy * S))
    canvas.convert('RGB').save(os.path.join(out, 'preview.png'))

    grid = big.copy()
    gd = ImageDraw.Draw(grid)
    for i in range(rows * 9):
        x, y = slot_xy(i % 9, i // 9)
        gd.rectangle((x * S, y * S, (x + 18) * S - 1, (y + 18) * S - 1), outline=(255, 0, 255, 255))
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
    print(json.dumps({'texture': f'{W}x{Hh}', 'ascent': ascent, 'height': Hh, 'shift': shift,
                      'buttons': {b['id']: button_slots(b) for b in spec.get('buttons', [])}}, ensure_ascii=False))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    build(sys.argv[1], sys.argv[2])
