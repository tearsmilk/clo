"""Turn any RGBA picture (AI icon, cut-out, rough sprite) into a clean pixel-art icon.

Rules distilled from good pixel-art icon sets (item sheets, food/harvest sets, Minecraft-style mob drops,
"Redstone Labs"-style extruded icons):
  * one fixed size (16, 24 or 32 px) with hard edges - no semi-transparent pixels
  * few colours per icon (6-10), optionally snapped to a shared palette so a whole set matches
  * a 1px outline that is a darker, slightly cooler version of the colour it touches - not pure black
  * light from the top-left: 1px highlight on top/left inner edges, cool shadow on bottom/right inner edges
  * optional extras: 4-point sparkles for rare items, an extruded 3D side, a single-colour silhouette for
    locked/disabled buttons

    stylize(img, size=24, colors=8, outline='auto', light=True, palette=None,
            extrude=0, sparkle=False, silhouette=None) -> RGBA image
"""
import colorsys
from PIL import Image


def _rgb(c):
    if isinstance(c, str):
        c = c.lstrip('#')
        return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))
    return tuple(c[:3])


def shade(rgb, light_delta, hue_shift=0.0, sat_delta=0.0):
    """Lighten/darken in HLS with an optional hue shift (pixel artists shift shadows cool, highlights warm)."""
    r, g, b = [v / 255 for v in rgb[:3]]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    h = (h + hue_shift) % 1.0
    l = min(1, max(0, l + light_delta))
    s = min(1, max(0, s + sat_delta))
    return tuple(int(round(v * 255)) for v in colorsys.hls_to_rgb(h, l, s))


def _toward(h, target, amount):
    """Rotate hue h toward target (both 0..1) by at most `amount`."""
    d = ((target - h + 0.5) % 1.0) - 0.5
    return max(-amount, min(amount, d))


def cool_dark(rgb, k=0.28):
    h, l, s = colorsys.rgb_to_hls(*[v / 255 for v in rgb])
    return shade(rgb, -k, _toward(h, 0.70, 0.06), 0.05)          # toward blue/purple


def warm_light(rgb, k=0.16):
    h, l, s = colorsys.rgb_to_hls(*[v / 255 for v in rgb])
    return shade(rgb, k, _toward(h, 0.14, 0.04), 0.0)             # toward yellow


def fit(img, size, alpha_cut=110):
    img = img.convert('RGBA')
    bb = img.getbbox()
    if bb:
        img = img.crop(bb)
    inner = size - 2                                              # keep 1px for the outline
    k = inner / max(img.size)
    w, h = max(1, round(img.width * k)), max(1, round(img.height * k))
    small = img.resize((w, h), Image.BOX if k < 1 else Image.NEAREST)
    a = small.getchannel('A').point(lambda v: 255 if v > alpha_cut else 0)
    out = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    rgb = small.convert('RGB')
    rgb.putalpha(a)
    out.alpha_composite(rgb, ((size - w) // 2, (size - h) // 2))
    return out


def quantize(img, colors=8, palette=None):
    a = img.getchannel('A')
    rgb = img.convert('RGB')
    if palette:
        pal = [_rgb(c) for c in palette]
        flat = sum(pal, ()) + pal[-1] * (256 - len(pal))
        pimg = Image.new('P', (1, 1))
        pimg.putpalette(flat)
        q = rgb.quantize(palette=pimg, dither=Image.Dither.NONE).convert('RGB')
    else:
        q = rgb.quantize(colors=colors, method=Image.MEDIANCUT, dither=Image.Dither.NONE).convert('RGB')
    q.putalpha(a)
    return q


def add_light(img):
    """Highlight on top/left inner edge, cool shadow on bottom/right inner edge."""
    px = img.load()
    w, h = img.size
    src = img.copy().load()
    for y in range(h):
        for x in range(w):
            if src[x, y][3] == 0:
                continue
            up = y == 0 or src[x, y - 1][3] == 0
            left = x == 0 or src[x - 1, y][3] == 0
            down = y == h - 1 or src[x, y + 1][3] == 0
            right = x == w - 1 or src[x + 1, y][3] == 0
            c = src[x, y][:3]
            if (up or left) and not (down or right):
                px[x, y] = warm_light(c) + (255,)
            elif (down or right) and not (up or left):
                px[x, y] = cool_dark(c, 0.18) + (255,)
    return img


def add_outline(img, mode='auto'):
    """1px outline around the opaque shape. 'auto' = darker, cooler shade of the touching pixel."""
    if mode in (None, 'none', False):
        return img
    px = img.load()
    w, h = img.size
    src = img.copy().load()
    fixed = _rgb(mode) if mode not in ('auto', 'black') else ((12, 10, 14) if mode == 'black' else None)
    for y in range(h):
        for x in range(w):
            if src[x, y][3]:
                continue
            nb = [src[x + dx, y + dy] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                  if 0 <= x + dx < w and 0 <= y + dy < h and src[x + dx, y + dy][3]]
            if not nb:
                continue
            if fixed:
                px[x, y] = fixed + (255,)
            else:
                darkest = min(nb, key=lambda c: sum(c[:3]))
                px[x, y] = cool_dark(darkest[:3], 0.30) + (255,)
    return img


def extrude(img, depth=2):
    """Pseudo-3D: a darker copy of the silhouette stacked down-right under the icon."""
    w, h = img.size
    out = Image.new('RGBA', (w + depth, h + depth), (0, 0, 0, 0))
    a = img.getchannel('A')
    src = img.load()
    side = Image.new('RGBA', img.size, (0, 0, 0, 0))
    sp = side.load()
    for y in range(h):
        for x in range(w):
            if src[x, y][3]:
                sp[x, y] = cool_dark(src[x, y][:3], 0.35) + (255,)
    for d in range(depth, 0, -1):
        out.paste(side, (d, d), a)
    out.alpha_composite(img, (0, 0))
    return out


SPARKLE = ["..#..", "..#..", "##.##", "..#..", "..#.."]
SPARKLE_SMALL = [".#.", "#.#", ".#."]


def add_sparkles(img, color=(255, 246, 196)):
    w, h = img.size
    big = Image.new('RGBA', (w + 4, h + 4), (0, 0, 0, 0))
    big.alpha_composite(img, (2, 2))
    px = big.load()
    for spr, (ox, oy) in ((SPARKLE, (w - 2, 0)), (SPARKLE_SMALL, (0, h - 2))):
        for j, row in enumerate(spr):
            for i, ch in enumerate(row):
                if ch == '#' and 0 <= ox + i < big.width and 0 <= oy + j < big.height and px[ox + i, oy + j][3] == 0:
                    px[ox + i, oy + j] = tuple(color) + (255,)
    return big


def silhouette(img, color='#E08A2E', inner=48):
    """Line-art version (outer contour + inner lines where colours change sharply) for locked buttons."""
    c = _rgb(color) + (255,)
    w, h = img.size
    src = img.load()
    lum = lambda p: 0.3 * p[0] + 0.59 * p[1] + 0.11 * p[2]
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    op = out.load()
    for y in range(h):
        for x in range(w):
            if not src[x, y][3]:
                continue
            line = False
            for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1)):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < w and 0 <= ny < h) or src[nx, ny][3] == 0:
                    line = True
                    break
                # inner line only on the darker side of a sharp edge, so lines stay 1px thick
                if dx + dy > 0 and lum(src[nx, ny]) - lum(src[x, y]) > inner:
                    line = True
                    break
            if line:
                op[x, y] = c
    return out


def stylize(img, size=24, colors=10, outline='auto', light=True, palette=None,
            extrude_depth=0, sparkle=False, silhouette_color=None):
    icon = fit(img, size)
    icon = quantize(icon, colors, palette)
    if light:
        icon = add_light(icon)
    icon = add_outline(icon, outline)
    if silhouette_color:
        icon = silhouette(icon, silhouette_color)
    if extrude_depth:
        icon = extrude(icon, extrude_depth)
    if sparkle:
        icon = add_sparkles(icon)
    return icon


def _scale2x(img):
    """EPX / Scale2x: doubles pixel art, rounding diagonal steps instead of making blocks."""
    w, h = img.size
    src = img.load()
    out = Image.new('RGBA', (w * 2, h * 2))
    o = out.load()
    for y in range(h):
        for x in range(w):
            p = src[x, y]
            a = src[x, y - 1] if y > 0 else p
            b = src[x + 1, y] if x < w - 1 else p
            c = src[x - 1, y] if x > 0 else p
            d = src[x, y + 1] if y < h - 1 else p
            o[2 * x, 2 * y] = a if (c == a and c != d and a != b) else p
            o[2 * x + 1, 2 * y] = b if (a == b and a != c and b != d) else p
            o[2 * x, 2 * y + 1] = c if (d == c and d != b and c != a) else p
            o[2 * x + 1, 2 * y + 1] = d if (b == d and b != a and d != c) else p
    return out


def rotsprite(img, degrees):
    """RotSprite: Scale2x three times (8x), rotate nearest-neighbour, scale back by taking the most common colour
    of each 8x8 block - rotated pixel art keeps clean 1px lines and its own colours (no blur, no new colours)."""
    from collections import Counter
    img = img.convert('RGBA')
    pad = Image.new('RGBA', (img.width + 4, img.height + 4), (0, 0, 0, 0))
    pad.alpha_composite(img, (2, 2))
    big = _scale2x(_scale2x(_scale2x(pad)))
    rot = big.rotate(-degrees, resample=Image.NEAREST, expand=True)
    w, h = rot.width // 8, rot.height // 8
    rp = rot.load()
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    op = out.load()
    for y in range(h):
        for x in range(w):
            block = [rp[x * 8 + i, y * 8 + j] for j in range(2, 6) for i in range(2, 6)]
            c, n = Counter(block).most_common(1)[0]
            op[x, y] = c if c[3] else (0, 0, 0, 0)
    return out.crop(out.getbbox()) if out.getbbox() else out
