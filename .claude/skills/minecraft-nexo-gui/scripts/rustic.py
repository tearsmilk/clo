"""Rustic kit (wooden board frame + old parchment + plank sign) after a popular "Jobs" GUI pack, measured and
redrawn: chipped wooden frame with a black outline and board joints, parchment with a light rim, wavy torn edges
and corner nails, a plank title sign crowned with a gold crown, coins, red pennants and crossed arrows, a red
bookmark tab with an icon, a picture card with a green ribbon nameplate, and recessed maroon slot wells.

All functions draw into a texture at texture coordinates (callers add the window offset).
"""
import math
import random
from PIL import Image, ImageDraw

import icons16
from pixfont import draw_text, text_width, draw_material_text, material_text_size


def C(h, a=255):
    h = h.lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


BLACK = '#000000'
W0, W1, W2, W3, W3B, W4, W5, W6, W7, W8 = ('#2c1424', '#371621', '#4d1b22', '#6b2f25', '#683429', '#8c3f2b',
                                          '#a95e3b', '#ac6e48', '#c58b55', '#dcb06b')
P_LT, P, P_SH, P_SH2 = '#ffe6cc', '#f8cfad', '#e4aa8a', '#c58b55'
NAIL_L, NAIL_M, NAIL_D = '#a8b5b2', '#78abc4', '#4c7b79'
R_EDGE, R_BODY, R_LIGHT, R_DARK, R_GOLD, R_DEEP = '#e8efed', '#e8421e', '#fff2ab', '#cb1a13', '#f9b833', '#a90b2c'
G_OUT, G_RIM, G_RIM2, G_DK, G_BODY, G_TEXT = '#683429', '#c58b55', '#ac6e48', '#32904e', '#42ad48', '#e0f1f6'
GOLD = ('#a8621a', '#eca323', '#f0d366', '#fbe255', '#fffef0')
STEEL = ('#555555', '#7e7973', '#bebcb7', '#d9d7d2')
SIGN_MAT = ('#371621', '#c58b55', '#f8cfad', '#ffe6cc', '#fffaf0')     # cream letters, dark wood outline


def _outline(im, color):
    w, h = im.size
    src = im.copy().load()
    px = im.load()
    for y in range(h):
        for x in range(w):
            if src[x, y][3] == 0 and any(0 <= x + dx < w and 0 <= y + dy < h and src[x + dx, y + dy][3]
                                         for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                px[x, y] = C(color)
    return im


# ----------------------------------------------------------------------------- frame + parchment

def frame(img, x0, y0, w, h, t=10, seed=4):
    """Wooden board frame (outer box x0,y0,w,h; band t px): black outline, light top edge, dark inner edge,
    boards joined every 12-18px with a dark seam and a 1px chip in the outer edge, a few grain streaks,
    a heavier bottom board and a grey ground shadow under it."""
    rnd = random.Random(seed)
    d = ImageDraw.Draw(img)
    px = img.load()
    x1, y1 = x0 + w - 1, y0 + h - 1
    d.rectangle((x0 + 1, y1 + 1, x1 - 1, y1 + 2), fill=C(STEEL[0]))           # ground shadow
    d.rectangle((x0, y0, x1, y1), fill=C(BLACK))
    d.rectangle((x0 + 1, y0 + 1, x1 - 1, y1 - 1), fill=C(W3))
    d.line((x0 + 1, y0 + 1, x1 - 1, y0 + 1), fill=C(W5))                      # lit top edge
    d.line((x0 + 1, y0 + 2, x1 - 1, y0 + 2), fill=C(W5))
    d.line((x0 + 1, y0 + 1, x0 + 1, y1 - 3), fill=C(W4))                      # lit left edge
    d.rectangle((x0 + 1, y1 - 3, x1 - 1, y1 - 1), fill=C(W2))                 # heavy bottom
    d.line((x0 + 1, y1 - 3, x1 - 1, y1 - 3), fill=C(W4))
    # inner edge (towards the parchment): dark line
    d.rectangle((x0 + t - 1, y0 + t - 1, x1 - t + 1, y1 - t + 1), outline=C(W1))
    # board joints on the sides and the top/bottom boards, each with a chipped outer edge
    for side in ('l', 'r'):
        y = y0 + t + rnd.randint(2, 8)
        while y < y1 - t - 4:
            xs = (x0 + 1, x0 + t - 2) if side == 'l' else (x1 - t + 2, x1 - 1)
            d.line((xs[0], y, xs[1], y), fill=C(W1))
            d.line((xs[0], y + 1, xs[1], y + 1), fill=C(W4))
            ex = x0 if side == 'l' else x1
            for yy in (y, y + 1):
                px[ex, yy] = (0, 0, 0, 0)
                px[ex + (1 if side == 'l' else -1), yy] = C(BLACK)
            y += rnd.randint(12, 18)
    for x in range(x0 + t + rnd.randint(4, 14), x1 - t - 4, 1):
        if rnd.random() < 0.035:                                                # top board joints
            d.line((x, y0 + 3, x, y0 + t - 2), fill=C(W1))
            d.line((x + 1, y0 + 3, x + 1, y0 + t - 2), fill=C(W4))
    for _ in range(max(6, (w + h) // 18)):                                       # grain streaks
        side = rnd.choice('tlrb')
        if side == 't':
            gx, gy, L = rnd.randint(x0 + 4, x1 - 12), rnd.randint(y0 + 4, y0 + t - 3), rnd.randint(4, 9)
            d.line((gx, gy, gx + L, gy), fill=C(W2))
        elif side == 'b':
            gx, gy, L = rnd.randint(x0 + 4, x1 - 12), rnd.randint(y1 - t + 2, y1 - 5), rnd.randint(4, 9)
            d.line((gx, gy, gx + L, gy), fill=C(W4))
        else:
            gx = rnd.randint(x0 + 3, x0 + t - 3) if side == 'l' else rnd.randint(x1 - t + 3, x1 - 3)
            gy, L = rnd.randint(y0 + t, y1 - t - 6), rnd.randint(3, 6)
            d.line((gx, gy, gx + 2, gy), fill=C(W4))
    for cx, cy in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):                    # cut corners
        px[cx, cy] = (0, 0, 0, 0)


def nail(img, x, y):
    """4x4 steel nail with a highlight and a soft shade under it."""
    rows = [".LM.", "LWMD", "MMDD", ".DD."]
    pal = {'L': NAIL_L, 'W': '#e0f1f6', 'M': NAIL_M, 'D': NAIL_D}
    px = img.load()
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch in pal:
                px[x + i, y + j] = C(pal[ch])
    px[x + 1, y + 4] = C(P_SH)
    px[x + 2, y + 4] = C(P_SH)


def parchment(img, x0, y0, w, h, seed=7, nails=True):
    """Old paper panel with wavy torn edges (1-2px), a light rim top/left, shade bottom/right and in the dents,
    a few soft creases, and nails in the corners."""
    rnd = random.Random(seed)
    px = img.load()
    x1, y1 = x0 + w - 1, y0 + h - 1

    def wob(i, k):
        return int(1 + math.sin(i / 7.0 + k) + 0.6 * math.sin(i / 3.1 + 2 * k) > 1.6)

    left = [x0 + wob(y, 1) for y in range(y0, y1 + 1)]
    right = [x1 - wob(y, 2) for y in range(y0, y1 + 1)]
    top = [y0 + wob(x, 3) for x in range(x0, x1 + 1)]
    bottom = [y1 - wob(x, 4) for x in range(x0, x1 + 1)]
    for y in range(y0, y1 + 1):
        for x in range(left[y - y0], right[y - y0] + 1):
            if top[x - x0] <= y <= bottom[x - x0]:
                c = P
                dl, dr = x - left[y - y0], right[y - y0] - x
                dt, db = y - top[x - x0], bottom[x - x0] - y
                if dt < 2 or dl < 2:
                    c = P_LT
                if db < 2 or dr < 1:
                    c = P_SH
                px[x, y] = C(c)
    d = ImageDraw.Draw(img)
    for _ in range(max(2, w * h // 2500)):                                     # creases
        cx, cy = rnd.randint(x0 + 6, x1 - 16), rnd.randint(y0 + 6, y1 - 8)
        L = rnd.randint(5, 12)
        d.line((cx, cy, cx + L, cy + rnd.choice((-1, 0, 1))), fill=C(P_SH))
        d.line((cx + 1, cy + 1, cx + L, cy + 1), fill=C(P_LT))
    for _ in range(max(2, (w + h) // 30)):                                      # torn bites
        side = rnd.randint(0, 3)
        if side == 0:
            bx, by = rnd.randint(x0 + 8, x1 - 8), top[0]
            for k in range(rnd.randint(2, 4)):
                px[bx + k, by] = C(P_SH)
        elif side == 1:
            bx, by = left[0], rnd.randint(y0 + 8, y1 - 8)
            px[bx, by] = C(P_SH)
            px[bx, by + 1] = C(P_SH)
    if nails:
        for nx, ny in ((x0 + 3, y0 + 3), (x1 - 6, y0 + 3), (x0 + 3, y1 - 7), (x1 - 6, y1 - 7)):
            nail(img, nx, ny)


# ----------------------------------------------------------------------------- sign + crest

def sign(img, cx, y0, w, h, text, scale=2, condensed=True):
    """Plank title sign: dark outline, two boards (lit top rows, grain, dark lower edges), a darker border,
    nails in the corners and cream letters with a dark wood outline."""
    x0 = cx - w // 2
    x1, y1 = x0 + w - 1, y0 + h - 1
    d = ImageDraw.Draw(img)
    d.rectangle((x0, y0, x1, y1), fill=C(W1))
    d.rectangle((x0 + 1, y0 + 1, x1 - 1, y1 - 1), fill=C(W3B))
    mid = y0 + h // 2
    for (ya, yb) in ((y0 + 2, mid - 1), (mid, y1 - 2)):
        d.rectangle((x0 + 2, ya, x1 - 2, yb), fill=C(W4))
        d.line((x0 + 2, ya, x1 - 2, ya), fill=C(W5))
        d.line((x0 + 2, yb, x1 - 2, yb), fill=C(W3))
    rnd = random.Random(w)
    for _ in range(w // 10):
        gx, gy = rnd.randint(x0 + 4, x1 - 10), rnd.randint(y0 + 3, y1 - 3)
        d.line((gx, gy, gx + rnd.randint(3, 7), gy), fill=C(W3))
    for nx, ny in ((x0 + 2, y0 + 2), (x1 - 3, y0 + 2), (x0 + 2, y1 - 3), (x1 - 3, y1 - 3)):
        d.rectangle((nx, ny, nx + 1, ny + 1), fill=C(STEEL[2]))
        d.point((nx, ny), fill=C(STEEL[3]))
    if text:
        tw, th = material_text_size(text, scale, condensed=condensed)
        draw_material_text(img, cx - tw // 2, y0 + (h - (7 * scale + 3)) // 2, text, SIGN_MAT, scale=scale,
                           condensed=condensed)


def coins(w, h, seed=3):
    """Mound of gold coins: overlapping 4x3 coins, light tops, dark rims, a few white glints."""
    rnd = random.Random(seed)
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for row in range(h // 2 + 1):
        y = h - 3 - row * 2
        span = int(w * (1 - row / (h / 2 + 1)) ** 0.7)
        for x in range((w - span) // 2, (w + span) // 2 - 2, 3):
            xx = x + rnd.randint(-1, 1)
            d.ellipse((xx, y, xx + 3, y + 2), fill=C(GOLD[1]))
            d.line((xx + 1, y, xx + 2, y), fill=C(GOLD[3]))
            d.point((xx + 3, y + 2), fill=C(GOLD[0]))
            if rnd.random() < 0.08:
                d.point((xx + 1, y), fill=C(GOLD[4]))
    return _outline(im, W1)


CROWN = [
    "....g.....g.....g....",
    "...gYg...gYg...gYg...",
    "...gYYg.gYYYg.gYYg...",
    "..gYYYYgYYRYYgYYYYg..",
    "..gYyYYYYRRRYYYYyYg..",
    "..gYYYYYYYBYYYYYYYg..",
    "..gyyyYYYBWBYYYyyyg..",
    "..gYYYyyyyByyyyYYYg..",
    "..gyBydyyyyyyyydyByg..",
    "..gggggggggggggggggg..",
]


def crown(scale=1):
    pal = {'g': '#5c2a10', 'Y': GOLD[2], 'y': GOLD[1], 'd': GOLD[0], 'R': R_BODY, 'B': '#3e7fd0', 'W': '#d9f4ff'}
    im = Image.new('RGBA', (len(CROWN[0]), len(CROWN)), (0, 0, 0, 0))
    for j, r in enumerate(CROWN):
        for i, ch in enumerate(r):
            if ch in pal:
                im.putpixel((i, j), C(pal[ch]))
    return im


def pennant(w=14, h=12, flip=False):
    """Red pennant on a short pole, waving to the outside, swallow-tail end."""
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.line((1, 0, 1, h - 1), fill=C(W4))
    pts = [(2, 1), (w - 1, 2), (w - 4, 5), (w - 1, 8), (2, 7)]
    d.polygon(pts, fill=C(R_BODY))
    d.line((2, 1, w - 2, 2), fill=C('#f6757a'))
    d.line((2, 6, w - 5, 6), fill=C(R_DARK))
    _outline(im, W1)
    return im.transpose(Image.Transpose.FLIP_LEFT_RIGHT) if flip else im


def arrow(w=16, h=16, flip=False):
    """Diagonal arrow pointing down-out (crossed behind the sign): red fletching top, wooden shaft, steel tip."""
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.line((w - 3, 2, 3, h - 3), fill=C(W5))
    d.line((w - 2, 2, 4, h - 3), fill=C(W3))
    d.polygon([(1, h - 1), (1, h - 5), (5, h - 1)], fill=C(STEEL[2]))
    d.point((2, h - 3), fill=C(STEEL[3]))
    for k in range(3):
        d.line((w - 5 + k, k, w - 1, 4 - k), fill=C(R_BODY if k < 2 else R_DARK))
        d.line((w - 6 + k, 1 + k, w - 3 + k, 4 + k), fill=C(R_BODY))
    _outline(im, W0)
    return im.transpose(Image.Transpose.FLIP_LEFT_RIGHT) if flip else im


def header(img, cx, y0, text, w=84, h=22):
    """The whole title group: arrows crossed behind the sign corners, the plank sign, coins along its top, the
    crown in the middle and pennants on both sides."""
    for flip, ax in ((False, cx - w // 2 - 10), (True, cx + w // 2 - 6)):
        img.alpha_composite(arrow(16, 16, flip=not flip), (ax, y0 + 4))
    sign(img, cx, y0 + 6, w, h, text)
    cn = coins(w - 8, 7)
    img.alpha_composite(cn, (cx - (w - 8) // 2, y0 + 1))
    for flip, px_ in ((False, cx - 34), (True, cx + 20)):
        img.alpha_composite(pennant(14, 12, flip=flip), (px_, y0 - 8))
    cr = crown()
    img.alpha_composite(cr, (cx - cr.width // 2, y0 - 7))


# ----------------------------------------------------------------------------- bookmark, card, nameplate

def bookmark(img, x, y, w=27, h=18, icon=None):
    """Red ribbon tab sticking out to the left of a window: near-white outline, red body, pale-yellow light
    stripe following the top and the V cut, darker lower band with a gold line, icon in the middle."""
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    px = im.load()
    notch = h // 2 - 1
    for yy in range(h):
        cut = notch - abs(yy - (h - 1) / 2) * notch / ((h - 1) / 2)
        for xx in range(int(round(cut)), w):
            c = R_BODY
            if yy >= h - 5:
                c = R_DARK
            if yy == h - 3:
                c = R_GOLD
            if xx >= w - 2:
                c = R_DEEP
            px[xx, yy] = C(c)
    src = im.copy().load()
    for yy in range(h):                                                        # light stripe inside the edge
        for xx in range(w - 2):
            if src[xx, yy][3] and (yy == 1 or (xx > 0 and not src[xx - 1, yy][3] and yy < h - 5)):
                if 0 < yy < h - 1:
                    px[xx + (1 if yy != 1 else 0), yy] = C(R_LIGHT)
    _outline_inside(im, R_EDGE)
    if icon:
        ic = icons16.icon(icon) if isinstance(icon, str) else icon
        im.alpha_composite(ic, ((w - 16) // 2 + 2, (h - 16) // 2))
    img.alpha_composite(im, (x, y))


def _outline_inside(im, color):
    w, h = im.size
    src = im.copy().load()
    px = im.load()
    for y in range(h):
        for x in range(w):
            if src[x, y][3] and any(not (0 <= x + dx < w and 0 <= y + dy < h) or not src[x + dx, y + dy][3]
                                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                if x < w - 1:
                    px[x, y] = C(color)


def nameplate(img, cx, y, text, min_w=60):
    """Green ribbon label with hexagonal arrow ends: brown outline, tan rim, dark-green rim, green body,
    pale text with a dark-green drop shadow (13 px tall)."""
    tw = text_width(text)
    w = max(min_w, tw + 28)
    h = 13
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    px = im.load()
    mid = (h - 1) / 2
    for yy in range(h):
        inset = int(abs(yy - mid))
        for xx in range(inset, w - inset):
            px[xx, yy] = C(G_BODY)
    layers = [(G_OUT, 0), (G_RIM, 1), (G_DK, 2)]
    src = im.copy().load()

    def depth(xx, yy):
        k = 0
        while k < 3:
            ok = all(0 <= xx + dx < w and 0 <= yy + dy < h and src[xx + dx, yy + dy][3]
                     for dx in range(-k - 1, k + 2) for dy in range(-k - 1, k + 2) if abs(dx) + abs(dy) == k + 1)
            if not ok:
                return k
            k += 1
        return k

    for yy in range(h):
        for xx in range(w):
            if src[xx, yy][3]:
                k = depth(xx, yy)
                if k == 0:
                    px[xx, yy] = C(G_OUT)
                elif k == 1:
                    px[xx, yy] = C(G_RIM if yy < mid else G_RIM2)
                elif k == 2:
                    px[xx, yy] = C(G_DK)
    draw_text(im, (w - tw) // 2, 3, text, C(G_TEXT), shadow=C(G_DK))
    img.alpha_composite(im, (cx - w // 2, y))
    return w


def card(img, x, y, w, h, picture, label=None):
    """Picture card: dark outline, brown frame with a tan inner line, the picture, and a nameplate overlapping
    the bottom edge."""
    corners = ((x, y), (x + w - 1, y), (x, y + h - 1), (x + w - 1, y + h - 1))
    under = {p: img.getpixel(p) for p in corners}           # cut corners show what was below (never a hole)
    d = ImageDraw.Draw(img)
    d.rectangle((x, y, x + w - 1, y + h - 1), fill=C(W1))
    d.rectangle((x + 1, y + 1, x + w - 2, y + h - 2), fill=C(W4))
    d.rectangle((x + 2, y + 2, x + w - 3, y + h - 3), fill=C(W7))
    pic = picture.resize((w - 6, h - 6), Image.NEAREST) if picture.size != (w - 6, h - 6) else picture
    img.alpha_composite(pic, (x + 3, y + 3))
    for p_, c_ in under.items():
        img.putpixel(p_, c_)
    if label:
        nameplate(img, x + w // 2, y + h - 10, label)


# ----------------------------------------------------------------------------- slots

def well_slot(img, x0, y0):
    """18x18 recessed maroon well: light wood line on top, 2 dark rows, dark sides, maroon 14x14 inside,
    wood row at the bottom, 1px wood columns at the box edges (2px between neighbours)."""
    d = ImageDraw.Draw(img)
    d.rectangle((x0, y0, x0 + 17, y0 + 17), fill=C(W4))
    d.line((x0, y0, x0 + 17, y0), fill=C(W5))
    d.rectangle((x0 + 1, y0 + 1, x0 + 16, y0 + 16), fill=C(W1))
    d.rectangle((x0 + 2, y0 + 3, x0 + 15, y0 + 16), fill=C(W2))
    d.line((x0, y0 + 17, x0 + 17, y0 + 17), fill=C(W3))


def grid_frame(img, x0, y0, cols, rows):
    """Frame around a block of well slots: dark, tan, dark lines (3px) with a light wood top."""
    d = ImageDraw.Draw(img)
    x1, y1 = x0 + cols * 18 - 1, y0 + rows * 18 - 1
    d.rectangle((x0 - 3, y0 - 3, x1 + 3, y1 + 3), fill=C(W1))
    d.rectangle((x0 - 2, y0 - 2, x1 + 2, y1 + 2), fill=C(W7))
    d.rectangle((x0 - 1, y0 - 1, x1 + 1, y1 + 1), fill=C(W1))
    d.line((x0 - 2, y0 - 2, x1 + 2, y0 - 2), fill=C(W8))
