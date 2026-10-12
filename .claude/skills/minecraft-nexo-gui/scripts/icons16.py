"""16x16 job/tool icons in the classic Minecraft item style (diagonal tools, handle bottom-left, dark outline),
drawn procedurally so they stay consistent: hoe, pickaxe, axe, shovel, sword, hammer, fishing_rod, bow, potion,
book, plus 8x11 mouse hint icons (lmb / rmb) for tooltips.

    icon(name) -> 16x16 RGBA            mouse(side) -> 8x11 RGBA ('left' / 'right')
"""
from PIL import Image, ImageDraw

K = (44, 20, 36, 255)            # outline
H, HD = (172, 110, 72, 255), (107, 47, 37, 255)          # handle light / dark
S, SM, SD = (224, 241, 246, 255), (160, 168, 177, 255), (100, 104, 112, 255)   # steel
GL, GM, GD = (251, 226, 85, 255), (236, 163, 35, 255), (168, 98, 26, 255)      # gold


def _outline(im):
    w, h = im.size
    src = im.copy().load()
    px = im.load()
    for y in range(h):
        for x in range(w):
            if src[x, y][3] == 0 and any(0 <= x + dx < w and 0 <= y + dy < h and src[x + dx, y + dy][3]
                                         for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                px[x, y] = K
    return im


def _handle(d, x0, y0, x1, y1):
    """Diagonal 1px handle with a darker lower-right edge (drawn as two offset lines)."""
    d.line((x0, y0, x1, y1), fill=H)
    d.line((x0 + 1, y0, x1 + 1, y1), fill=HD)


def _steel(im, mask_pts, light_side='tl'):
    """Fill a polygon in steel: light upper-left, mid, dark lower-right by distance to the polygon centre."""
    m = Image.new('L', im.size, 0)
    ImageDraw.Draw(m).polygon(mask_pts, fill=255)
    px, mp = im.load(), m.load()
    xs = [p[0] for p in mask_pts]
    ys = [p[1] for p in mask_pts]
    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
    for y in range(im.height):
        for x in range(im.width):
            if mp[x, y]:
                t = (x - cx) + (y - cy)
                px[x, y] = S if t < -1 else (SM if t < 2 else SD)


def icon(name):
    im = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    px = im.load()
    if name == 'pickaxe':
        _handle(d, 2, 13, 10, 5)
        for (x, y) in ((4, 3), (5, 2), (6, 2), (7, 2), (8, 2), (9, 2), (10, 3), (11, 3), (12, 4), (12, 5), (13, 6),
                       (13, 7), (13, 8), (13, 9), (5, 3), (6, 3), (11, 4), (12, 6), (12, 7)):
            px[x, y] = S if x + y < 14 else (SM if x + y < 18 else SD)
        px[4, 4] = SM
        px[13, 10] = SD
    elif name == 'axe':
        _handle(d, 2, 13, 11, 4)
        _steel(im, [(8, 2), (11, 1), (14, 4), (13, 8), (11, 8), (9, 5)])
    elif name == 'hoe':
        _handle(d, 2, 13, 11, 4)
        for (x, y) in ((8, 2), (9, 2), (10, 2), (11, 2), (12, 3), (12, 4), (13, 4), (13, 5), (9, 3), (10, 3), (11, 3)):
            px[x, y] = S if y < 3 else (SM if y < 5 else SD)
    elif name == 'shovel':
        _handle(d, 2, 13, 8, 7)
        _steel(im, [(8, 6), (9, 3), (12, 1), (14, 3), (12, 6), (9, 8)])
    elif name == 'sword':
        d.line((4, 11, 13, 2), fill=S)
        d.line((5, 11, 13, 3), fill=SM)
        d.line((6, 11, 13, 4), fill=SD)
        for (x, y) in ((3, 9), (4, 10), (5, 11), (6, 12), (7, 13)):
            px[x, y] = GM
        px[2, 13], px[3, 12], px[1, 14] = HD, H, GL
    elif name == 'hammer':
        _handle(d, 2, 13, 9, 6)
        for y in range(16):                       # heavy head: a 3px bar across the handle end
            for x in range(16):
                u, v = (x - 11) - (y - 4), (x - 11) + (y - 4)
                if abs(u) <= 1 and abs(v) <= 4:
                    px[x, y] = S if v < -1 else (SM if v < 2 else SD)
    elif name == 'fishing_rod':
        d.line((1, 14, 12, 2), fill=H)
        d.line((2, 14, 12, 3), fill=HD)
        d.line((12, 2, 13, 2), fill=SM)
        d.line((13, 3, 13, 10), fill=(232, 239, 237, 255))
        px[13, 11], px[13, 12] = (232, 66, 30, 255), (240, 240, 240, 255)
        px[12, 11], px[14, 11] = (203, 26, 19, 255), (203, 26, 19, 255)
    elif name == 'bow':
        d.line((12, 2, 2, 12), fill=(232, 239, 237, 255))          # string
        for i in range(21):                                         # limb bulging to the top-left
            t = i / 20
            x = (1 - t) ** 2 * 13 + 2 * (1 - t) * t * 1 + t * t * 3
            y = (1 - t) ** 2 * 3 + 2 * (1 - t) * t * 1 + t * t * 13
            px[round(x), round(y)] = H if i % 4 else HD
        for (x, y) in ((13, 2), (12, 1), (2, 13), (3, 14)):
            px[x, y] = HD
        d.line((5, 10, 10, 5), fill=SM)                             # nocked arrow
        px[10, 4], px[11, 4], px[11, 5] = S, S, SD
        px[4, 11], px[4, 12], px[3, 11] = (232, 66, 30, 255), (203, 26, 19, 255), (232, 66, 30, 255)
    elif name == 'potion':
        d.rectangle((6, 1, 9, 2), fill=(140, 63, 43, 255))
        d.rectangle((6, 3, 9, 4), fill=(224, 241, 246, 255))
        d.ellipse((3, 4, 12, 14), fill=(224, 241, 246, 255))
        d.ellipse((4, 7, 11, 13), fill=(66, 173, 72, 255))
        d.line((4, 10, 11, 10), fill=(141, 227, 106, 255))
        px[5, 6], px[5, 7] = (255, 255, 255, 255), (255, 255, 255, 255)
        px[9, 12], px[10, 11] = (50, 144, 78, 255), (50, 144, 78, 255)
    elif name == 'book':
        d.rectangle((3, 2, 13, 14), fill=(104, 56, 108, 255))
        d.rectangle((4, 2, 13, 13), fill=(181, 80, 136, 255))
        d.line((3, 2, 3, 14), fill=(62, 39, 49, 255))
        d.rectangle((5, 14, 13, 14), fill=(234, 212, 170, 255))
        for (x, y) in ((8, 5), (7, 6), (9, 6), (8, 7), (8, 9), (7, 8), (9, 8)):
            px[x, y] = GL
        for (x, y) in ((12, 3), (12, 12), (5, 3)):
            px[x, y] = GM
    elif name == 'star':
        pts = [(8, 1), (10, 6), (15, 6), (11, 9), (13, 14), (8, 11), (3, 14), (5, 9), (1, 6), (6, 6)]
        d.polygon(pts, fill=GM)
        d.polygon([(8, 3), (9, 7), (12, 7), (9, 9), (8, 9), (6, 8), (6, 7), (8, 6)], fill=GL)
        px[7, 5] = (255, 255, 255, 255)
    else:
        raise KeyError(name)
    return _outline(im)


def mouse(side='left'):
    """8x11 mouse for tooltip hints: pale body, the pressed button tinted, wheel line, dark outline."""
    im = Image.new('RGBA', (8, 11), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    body, shade, press = (224, 241, 246, 255), (160, 175, 190, 255), (232, 66, 30, 255)
    d.rounded_rectangle((1, 1, 6, 9), radius=2, fill=body)
    d.line((1, 5, 6, 5), fill=shade)
    d.line((3, 1, 3, 4), fill=shade) if side == 'right' else d.line((4, 1, 4, 4), fill=shade)
    if side == 'left':
        d.rectangle((1, 2, 3, 4), fill=press)
        d.point((2, 1), fill=press)
    else:
        d.rectangle((4, 2, 6, 4), fill=press)
        d.point((5, 1), fill=press)
    d.line((2, 8, 5, 8), fill=shade)
    return _outline(im)


NAMES = ['hoe', 'pickaxe', 'axe', 'shovel', 'sword', 'hammer', 'fishing_rod', 'bow', 'potion', 'book', 'star']
