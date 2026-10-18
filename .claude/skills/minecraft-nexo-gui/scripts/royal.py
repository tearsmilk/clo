"""Royal kit (dark slate + gold) built to measured geometry of a premium 6-row chest GUI.

Every simple part (panel edges, grooves, rimmed slots, corner brackets, title tab, divider, gem, hotbar frame,
rails, key ornaments) follows the measured stripe order and offsets; illustrations (banner emblem, crystal
clusters, streamers) are our own drawings in the same palette and footprint. Coordinates are window-relative
(window = the vanilla 176 x (114 + 18*rows) rectangle); `ox, oy` is the window origin inside the texture.

    panel(img, ox, oy, rows)                 slate panel incl. outline, gold line, grooves, bottom lip, etches
    rim_slot(img, x, y)                      one rimmed slot well (18x18 box at texture x, y)
    corner_brackets(img, ox, oy, rows)       4 gold L brackets on the window corners
    tab(img, ox, oy, x, w, top, h)           title tab with '[' ']' brackets and a 2px shadow
    divider(img, ox, oy, rows, gem)          gem bar + thin line + side brackets between container and inventory
    hotbar_frame(img, ox, oy, rows)          gold/red frame around the hotbar
    rail(img, x, y), meander(img, x, y, flip), banner(...), shard(...), crystal_cluster(...), streamer(...)
"""
import math
import random
from PIL import Image, ImageDraw

O = '#1c1b2b'
G_DK, G, G_LT, G_HI, WHITE = '#b55a41', '#d9893f', '#ebcc5b', '#faec82', '#fffef8'
RED, RED_DK, RED2, RED3, RED4, RED5, DARK = '#8a3337', '#5c2534', '#a83333', '#852433', '#662031', '#4f1e36', '#33182a'
BODY, S1, S2, S3, S4, S5, S6, SIL = '#2b3545', '#3a4959', '#859aa9', '#6c8294', '#506275', '#1f2432', '#242a39', '#b3c2ca'
GEM = ('#c5cf7c', '#90bf64', '#439950', '#39785a', '#305a5c', '#273745')


def C(h):
    h = h.lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)


def _put(px, img, x, y, c):
    if 0 <= x < img.width and 0 <= y < img.height:
        px[x, y] = C(c)


def _hline(px, img, x0, x1, y, c):
    for x in range(x0, x1 + 1):
        _put(px, img, x, y, c)


def _vline(px, img, x, y0, y1, c):
    for y in range(y0, y1 + 1):
        _put(px, img, x, y, c)


# ----------------------------------------------------------------------------- panel + slots

def gold_at(i, center, inner=15, outer=40):
    """Brushed gold along a frame line: brightest in the middle, gold, then dark gold towards the ends, with
    1px alternating transitions (no smooth gradient, no dithering noise)."""
    t = abs(i - center)
    if t < inner:
        return G_LT
    if t < inner + 5:
        return G if (t - inner) in (0, 2, 3) else G_LT
    if t < outer:
        return G
    if t < outer + 3:
        return G_DK if (t - outer) in (1,) else G
    return G_DK


def panel(img, ox, oy, rows, split=None):
    """Slate window. Upper section: outline outside the window, 1px gold line on the window edge, two light top
    rows, an engraved groove 3-4px in (light then dark), etched scratches. Lower section (from `split`, the player
    inventory): outline on the edge and the groove at 2-3px. Bottom: light, mid, dark rows and a 2px outline."""
    W, H = 176, 114 + rows * 18
    split = split if split is not None else rows * 18 + 22
    px = img.load()
    d = ImageDraw.Draw(img)
    d.rectangle((ox - 1, oy - 1, ox + W, oy + H - 1), fill=C(O))
    d.rectangle((ox + 1, oy + 1, ox + W - 2, oy + H - 3), fill=C(BODY))
    for x in range(W):                                                          # gold top line
        _put(px, img, ox + x, oy, gold_at(x, 88, 30, 58))
    mid = (split - 1) / 2                                                       # gold side lines (upper)
    for y in range(split):
        c = gold_at(y, mid, 15, 40)
        _put(px, img, ox, oy + y, c)
        _put(px, img, ox + W - 1, oy + y, c)
    _hline(px, img, ox + 1, ox + W - 2, oy + 1, S1)
    _hline(px, img, ox + 1, ox + W - 2, oy + 2, S1)
    _hline(px, img, ox + 3, ox + W - 4, oy + 3, S2)                             # groove: light then dark
    _hline(px, img, ox + 4, ox + W - 5, oy + 4, S5)
    _vline(px, img, ox + 3, oy + 3, oy + split - 1, S3)
    _vline(px, img, ox + 4, oy + 4, oy + split - 1, S5)
    _vline(px, img, ox + W - 4, oy + 3, oy + split - 1, S3)
    _vline(px, img, ox + W - 5, oy + 4, oy + split - 1, S5)
    for xx in (0, 1, W - 2, W - 1):                                            # lower section: 2px outline
        _vline(px, img, ox + xx, oy + split, oy + H - 3, O)
    _vline(px, img, ox + 3, oy + split, oy + H - 6, S3)
    _vline(px, img, ox + 4, oy + split, oy + H - 6, S5)
    _vline(px, img, ox + W - 4, oy + split, oy + H - 6, S3)
    _vline(px, img, ox + W - 5, oy + split, oy + H - 6, S5)
    _hline(px, img, ox + 1, ox + W - 2, oy + H - 5, S1)                          # bottom lip
    _hline(px, img, ox + 1, ox + W - 2, oy + H - 4, S4)
    _hline(px, img, ox + 1, ox + W - 2, oy + H - 3, S5)
    for x, y in ((ox - 1, oy - 1), (ox + W, oy - 1), (ox - 1, oy + H - 1), (ox + W, oy + H - 1)):
        px[x, y] = (0, 0, 0, 0)
    # etched scratches in the top strip (dotted light line, a dark one under a light one)
    for x0, ln, y in ((6, 13, 6), (20, 7, 10), (W - 20, 13, 6), (W - 28, 7, 10)):
        for x in range(x0, x0 + ln):
            if (x - x0) % 7 != 1:
                _put(px, img, ox + x, oy + y, S1)
        _put(px, img, ox + x0 - 2, oy + y, S1)


def rim_slot(img, x0, y0):
    """18x18 slot: light line above, mid left rim, light top/right rim, dark bottom rim, inner shadow top/left,
    lit inner bottom/right, dark gap row below (measured)."""
    px = img.load()
    for y in range(y0, y0 + 18):
        for x in range(x0, x0 + 18):
            _put(px, img, x, y, BODY)
    _put(px, img, x0, y0, S4)
    _put(px, img, x0 + 17, y0, S4)
    _hline(px, img, x0 + 1, x0 + 16, y0, S1)
    _hline(px, img, x0, x0 + 17, y0 + 17, S5)
    _put(px, img, x0, y0 + 17, S1)
    _put(px, img, x0 + 17, y0 + 17, S1)
    _vline(px, img, x0 + 1, y0 + 1, y0 + 16, S3)
    _hline(px, img, x0 + 2, x0 + 16, y0 + 1, S2)
    _vline(px, img, x0 + 16, y0 + 1, y0 + 16, S2)
    _hline(px, img, x0 + 2, x0 + 15, y0 + 16, S4)
    _hline(px, img, x0 + 2, x0 + 15, y0 + 2, S5)
    _vline(px, img, x0 + 2, y0 + 2, y0 + 15, S5)
    _hline(px, img, x0 + 3, x0 + 15, y0 + 15, S1)
    _vline(px, img, x0 + 15, y0 + 3, y0 + 15, S1)


# ----------------------------------------------------------------------------- brackets

def bracket_img(hw=16, vh=17, t=6):
    """Top-left gold L bracket (horizontal leg hw, vertical leg vh, thickness t incl. outlines), mitered ends.
    Horizontal leg rows: outline, gold, gold, light, red, outline. Vertical leg cols: outline, dark gold x2,
    light (palest near the corner), red, outline. The light stripes meet on the corner diagonal; each mitered
    end runs light gold -> dark red -> outline, and the light row turns pale gold over its last 4px."""
    im = Image.new('RGBA', (hw, vh), (0, 0, 0, 0))
    px = im.load()
    hrow = [O, G, G, G_HI, RED, O]
    vcol = [O, G_DK, G_DK, G_HI, RED, O]
    for y in range(vh):
        for x in range(hw):
            in_h = y < t and x <= (hw - 1 if y == 0 else hw - y)
            in_v = x < t and y <= (vh - 1 if x == 0 else vh - x)
            if not (in_h or in_v):
                continue
            if in_h and in_v:
                c = vcol[x] if x < y else (hrow[y] if x > y else (G_HI if 0 < x < t - 2 else (O if x in (0, t - 1) else RED)))
            elif in_h:
                end = hw - y
                c = hrow[y]
                if 0 < y < t - 1:
                    if x == end:
                        c = O
                    elif x == end - 1:
                        c = RED_DK
                    elif y < 3 and x == end - 2:
                        c = G_LT
                    elif y == 3 and x >= end - 5:
                        c = G_LT
            else:
                end = vh - x
                c = vcol[x]
                if x == 3 and y >= 8:
                    c = G_LT
                if 0 < x < t - 1:
                    if y == end:
                        c = O
                    elif y == end - 1:
                        c = RED_DK
                    elif y == end - 2 and x < 4:
                        c = G_LT
            px[x, y] = C(c)
    return im


def _flip(im, corner):
    if corner in ('tr', 'br'):
        im = im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    if corner in ('bl', 'br'):
        im = im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return im


def corner_brackets(img, ox, oy, rows):
    """Top corners: 16x17 brackets sticking 2px out of the window; bottom corners: 16x16, flush with it."""
    W, H = 176, 114 + rows * 18
    top, bot = bracket_img(16, 17), bracket_img(16, 16)
    img.alpha_composite(top, (ox - 2, oy - 2))
    img.alpha_composite(_flip(top, 'tr'), (ox + W + 2 - 16, oy - 2))
    img.alpha_composite(_flip(bot, 'bl'), (ox, oy + H - 16))
    img.alpha_composite(_flip(bot, 'br'), (ox + W - 16, oy + H - 16))


# ----------------------------------------------------------------------------- title tab

def tab_bracket_img(w=16, h=24, t=6):
    """'[' bracket for title tabs: mitered top leg (rows outline, gold, gold, light, red, outline), vertical leg
    (cols outline, dark gold x2, light, red, outline), mitered bottom leg (rows dark gold, light, red, red,
    outline) - the bottom leg grows longer downward."""
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    px = im.load()
    hrow = [O, G, G, G_HI, RED, O]
    vcol = [O, G_DK, G_DK, G_HI, RED, O]
    brow = [G_DK, G_LT, RED, RED, O]                 # bottom leg rows h-5 .. h-1
    for y in range(h):
        for x in range(w):
            c = None
            if y < t and x <= w - 1 - y:                                     # top leg
                c = hrow[y] if x > y else (vcol[x] if x < y else (G_HI if 0 < x < t - 2 else hrow[y]))
                if x == w - 1 - y and 0 < y < t - 1:
                    c = O
                elif x == w - 2 - y and 0 < y < t - 2:
                    c = G_LT if y < 2 else RED_DK
            elif y >= h - 5 and x <= w - 6 + (y - (h - 5)) + (1 if y == h - 1 else 0):   # bottom leg
                r = y - (h - 5)
                c = brow[r] if x >= t - 1 else vcol[x]
                if x < t - 1 and r >= 2:
                    c = (vcol[x] if x < t - 1 - r + 1 else RED) if r < 4 else O
                end = w - 6 + r + (1 if y == h - 1 else 0)
                if x == end and r < 4:
                    c = O
                elif x == end - 1 and r < 4:
                    c = G if r < 2 else G_LT
            elif x < t:                                                      # vertical leg
                c = vcol[x]
                if x == 3:
                    c = G_HI if y < 13 else G_LT
            if c:
                px[x, y] = C(c)
    return im


def tab(img, ox, oy, x, w, top=-10, h=20):
    """Dark tab across the window top: outline, 2 light rows, groove, body with etched lines, light/mid/dark lip,
    outline, then a 2px dark shadow; '[' and ']' gold brackets (with their own shadow) on its ends."""
    px = img.load()
    X0, Y0 = ox + x, oy + top
    d = ImageDraw.Draw(img)
    d.rectangle((X0, Y0 + h, X0 + w - 1, Y0 + h + 1), fill=C(S6))              # shadow
    d.rectangle((X0, Y0, X0 + w - 1, Y0 + h - 1), fill=C(O))
    d.rectangle((X0 + 1, Y0 + 1, X0 + w - 2, Y0 + h - 2), fill=C(BODY))
    _hline(px, img, X0 + 1, X0 + w - 2, Y0 + 1, S1)
    _hline(px, img, X0 + 1, X0 + w - 2, Y0 + 2, S1)
    _hline(px, img, X0 + 1, X0 + w - 2, Y0 + 3, S2)
    _hline(px, img, X0 + 1, X0 + w - 2, Y0 + 4, S5)
    for side in (0, 1):                                                         # etched lines at both ends
        def P(xx, yy, c):
            _put(px, img, X0 + xx if side == 0 else X0 + w - 1 - xx, Y0 + yy, c)
        for xx in [2] + list(range(4, 17)):
            P(xx, 6, S1)
        for xx in list(range(1, 12)) + [13]:
            P(xx, 8, S5)
        P(2, 10, S1)
        P(4, 10, S5)
        for xx in range(6, 20):
            P(xx, 10, S1)
        for xx in list(range(1, 7)) + [8]:
            P(xx, 12, S5)
        for yy in (9, 11):
            P(4, yy, S5)
    _hline(px, img, X0 + 1, X0 + w - 2, Y0 + h - 5, S1)
    _hline(px, img, X0 + 1, X0 + w - 2, Y0 + h - 4, S4)
    _hline(px, img, X0 + 1, X0 + w - 2, Y0 + h - 3, S5)
    _hline(px, img, X0 + 1, X0 + w - 2, Y0 + h - 2, S5)
    br = tab_bracket_img(16, h + 4)
    for side in (0, 1):
        im = br if side == 0 else br.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        bx = X0 - 5 if side == 0 else X0 + w + 5 - 16
        d.rectangle((bx, Y0 + h + 2, bx + 15, Y0 + h + 3), fill=C(S6))           # bracket shadow
        img.alpha_composite(im, (bx, Y0 - 2))


SHARD_SMALL = [".....aa", "....aca", "...acca", "..accda", ".accbda", "accbbda", "aaabbea", "..abdea", "..addea",
               "..addea", "..adda.", "..ada..", "..aa..."]


def small_shard(flip=False):
    pal = {'a': O, 'b': G, 'c': G_LT, 'd': G_DK, 'e': RED}
    im = Image.new('RGBA', (7, 13), (0, 0, 0, 0))
    for j, r in enumerate(SHARD_SMALL):
        for i, ch in enumerate(r):
            if ch in pal:
                im.putpixel((i, j), C(pal[ch]))
    return im.transpose(Image.Transpose.FLIP_LEFT_RIGHT) if flip else im


# ----------------------------------------------------------------------------- divider, gem, hotbar

def gem_img(w=12, h=13):
    """Rhombus emerald in a gold setting: light gold upper-left edge, gold upper-right, dark lower edges, four
    green facets (light upper-left -> dark lower-right), facet lines."""
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    px = im.load()
    cx, cy = (w - 1) / 2, (h - 1) / 2
    for y in range(h):
        for x in range(w):
            u, v = abs(x - cx) / (w / 2), abs(y - cy) / (h / 2)
            s = u + v
            if s > 1.0:
                continue
            if s > 0.86:
                c = O
            elif s > 0.70:
                c = (G_LT if x <= cx else G) if y <= cy else (G_DK if x >= cx else GEM[5])
            elif s > 0.58:
                c = GEM[4] if y <= cy else GEM[5]
            else:
                c = (GEM[1] if x < cx else GEM[2]) if y < cy else (GEM[2] if x < cx else GEM[3])
            px[x, y] = C(c)
    return im


def divider(img, ox, oy, rows, gem=True):
    """Between the container rows and the player inventory (window y 125..137): a thin engraved line with a gold
    stripe across the window, a heavy gold bar (gold, gold, light, red, red) over the middle, a gem in the
    centre and gold side brackets."""
    px = img.load()
    y = oy + rows * 18 + 17 + 3          # 3px below the last container row
    X0, X1 = ox + 13, ox + 162
    _hline(px, img, X0, X1, y, S1)
    _hline(px, img, X0, X1, y + 1, S4)
    _hline(px, img, X0, X1, y + 2, S5)
    for x in range(X0, X1 + 1):                    # brushed gold per segment: dark at the ends, light inside
        seg_c = 28.5 if (x - ox) < 88 else 147.5
        _put(px, img, x, y + 3, gold_at(x - ox, seg_c, 6, 11))
    _hline(px, img, X0, X1, y + 4, O)
    _hline(px, img, X0, X1, y + 5, S2)
    _hline(px, img, X0, X1, y + 6, S5)
    b0, b1 = ox + 45, ox + 130                                                  # central bar
    for i, c in enumerate((O, G, G, G_HI, RED, RED, O)):
        _hline(px, img, b0 + (1 if i in (0, 6) else 0), b1 - (1 if i in (0, 6) else 0), y + i, c)
    _vline(px, img, b0 - 1, y + 1, y + 5, O)
    _vline(px, img, b1 + 1, y + 1, y + 5, O)
    if gem:
        g = gem_img(12, 13)
        img.alpha_composite(g, (ox + 88 - 6, y - 3))
    # side brackets: two L brackets per side - the upper one (flipped) closes on the line from above with its
    # arm, the lower one (1px further in) from below; their arms meet on the shared outline row
    ub = bracket_img(16, 16).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    lb = bracket_img(15, 20)
    img.alpha_composite(ub, (ox - 2, y - 13))
    img.alpha_composite(lb, (ox, y + 2))
    img.alpha_composite(ub.transpose(Image.Transpose.FLIP_LEFT_RIGHT), (ox + 176 + 2 - 16, y - 13))
    img.alpha_composite(lb.transpose(Image.Transpose.FLIP_LEFT_RIGHT), (ox + 176 - 15, y + 2))


def hotbar_frame(img, ox, oy, rows):
    """1px frame around the hotbar: gold top/bottom lines (dark gold at the ends, brighter inward), red sides."""
    px = img.load()
    hy = oy + rows * 18 + 88
    x0, x1, y0, y1 = ox + 6, ox + 169, hy - 1, hy + 18
    for x in range(x0, x1 + 1):
        k = 1 - abs((x - ox) - 88) / 82
        c = G if k > 0.35 else G_DK
        _put(px, img, x, y0, c)
        _put(px, img, x, y1, c)
    _vline(px, img, x0, y0 + 1, y1 - 1, RED)
    _vline(px, img, x1, y0 + 1, y1 - 1, RED)
    for x, y in ((x0, y0 + 1), (x1, y0 + 1), (x0, y1 - 1), (x1, y1 - 1)):
        _put(px, img, x, y, RED_DK)


# ----------------------------------------------------------------------------- side ornaments

HOOK = ["aaaada", "addada", "adaada", "adddda", "aaaaaa"]


def rail(img, x, y, top_len=16, bottom_len=17):
    """Vertical gold rail beside a window side: a 3px line (outline, gold, outline) that brightens towards the
    middle, a square spiral hook, a gem, a mirrored hook, the line again. (x, y) = texture top-left of the
    7px wide column (the gem's left edge); the line runs at x+4..x+6."""
    px = img.load()
    lx = x + 4

    def line(y0, y1, bright_end):
        n = y1 - y0 + 1
        for k, yy in enumerate(range(y0, y1 + 1)):
            dist = (n - 1 - k) if bright_end == 'bottom' else k
            c = G_LT if dist < 3 else (G if dist < 10 else G_DK)
            _put(px, img, lx, yy, O)
            _put(px, img, lx + 1, yy, c)
            _put(px, img, lx + 2, yy, O)

    def hook(y0, flip):
        rows = HOOK[::-1] if flip else HOOK
        for j, r in enumerate(rows):
            for i, ch in enumerate(r):
                _put(px, img, x + 1 + i, y0 + j, O if ch == 'a' else G_LT)

    line(y, y + top_len - 1, 'bottom')
    hook(y + top_len, False)
    img.alpha_composite(small_gem(), (x, y + top_len + 6))
    hook(y + top_len + 17, True)
    line(y + top_len + 22, y + top_len + 22 + bottom_len - 1, 'top')


def small_gem():
    """7x10 green gem for rails (light facet top-left, dark bottom-right)."""
    rows = ["...a...", "..ava..", ".avuwa.", "avvuwwa", "auuuvva", "awwuxxa", "awwvxxa", ".awvxa.", "..ava..",
            "...a..."]
    pal = {'a': O, 'u': GEM[0], 'v': GEM[1], 'w': GEM[2], 'x': GEM[3]}
    im = Image.new('RGBA', (7, 10), (0, 0, 0, 0))
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch in pal:
                im.putpixel((i, j), C(pal[ch]))
    return im


MEANDER = [  # 30 x 7 greek key: hollow square, hook + bar ending in a spiral square, two small squares above
    "..............aaa.aaaa........",
    "aaaaaa.aaaaa..aca.acda..aaaaaa",
    "abbcca.addda..aaa.aaaa..abbbba",
    "abaaca.adada............abbaba",
    "acaada.adaaaaaaaaaaaaaaaaaaaba",
    "accdda.addddddccccbccbcbbbbbba",
    "aaaaaa.aaaaaaaaaaaaaaaaaaaaaaa",
]


def meander(img, x, y, flip=False):
    """Key ornament beside the title tab (x, y = texture top-left; 30 x 7 px)."""
    pal = {'a': O, 'b': G_LT, 'c': G, 'd': G_DK}
    im = Image.new('RGBA', (30, 7), (0, 0, 0, 0))
    for j, r in enumerate(MEANDER):
        for i, ch in enumerate(r):
            if ch in pal:
                im.putpixel((i, j), C(pal[ch]))
    if flip:
        im = im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    img.alpha_composite(im, (x, y))


# ----------------------------------------------------------------------------- illustrations (own drawings)

EMBLEM = [  # 17 x 30 heraldic emblem: crown, crowned rampant lion silhouette on a shield-like mane
    "......y.y.y......",
    ".....yYyYyYy.....",
    ".....yYYYYYy.....",
    ".....yHHHHHy.....",
    "......yyyyy......",
    "....yyYYYYYyy....",
    "...yYYyyYyyYYy...",
    "..yYYy.yYy.yYYy..",
    ".yYYy.yYYYy.yYYy.",
    ".yYy.yYYHYYy.yYy.",
    "yYYy.yYHHHYy.yYYy",
    "yYy..yYYHYYy..yYy",
    "yYYy.yyYYYyy.yYYy",
    ".yYYy.yYYYy.yYYy.",
    ".yYYYyyYyYyyYYYy.",
    "..yYYYYYyYYYYYy..",
    "..yyYYYyYyYYYyy..",
    ".yYYyyYYYYYyyYYy.",
    ".yYy.yYYHYYy.yYy.",
    "yYYy.yYYYYYy.yYYy",
    "yYy..yyYYYyy..yYy",
    ".yy...yYYYy...yy.",
    "......yYYYy......",
    ".....yYYyYYy.....",
    "....yYYy.yYYy....",
    "....yYy...yYy....",
    "...yYYy...yYYy...",
    "...yyy.....yyy...",
    ".................",
    ".................",
]


def banner(img, x, y, w=25, h=58, emblem=True, mirror=False):
    """Hanging crest banner. (x, y) = texture top-left of the cloth column at the rod row. A silver rod (bright
    near the ball, darker outward) runs 8px past the cloth to a gold ball; the cloth hangs from a silver bar with
    clips, has a dark hem, a red field with gold trim stripes inset 2px (dark line + trim on the right), a shaded
    right half, a 12-row point tail and a gold emblem."""
    ext = 8
    im = Image.new('RGBA', (w + ext, h), (0, 0, 0, 0))
    px = im.load()
    d = ImageDraw.Draw(im)
    X = ext                                                     # cloth x0 inside im
    d.rectangle((ext - 2, 2, X + w - 1, 4), fill=C(O))         # rod
    for xx in range(ext - 1, X + w - 1):
        t = (xx - ext) / max(1, w)
        px[xx, 3] = C(SIL if t < 0.3 else (S2 if t < 0.75 else (S3 if xx < X + w - 2 else S4)))
    for j, r in enumerate([".aaa.", "abbba", "abddbba", "abddbca", "abbbcca", ".accca.", "..aaa.."]):
        for i, ch in enumerate(r):
            if ch != '.':
                xx = i - (1 if len(r) == 5 else 0) + (1 if len(r) == 5 else 0)
                px[i if len(r) == 7 else i + 1, j] = C({'a': O, 'b': G, 'c': G_DK, 'd': G_LT}[ch])
    top, tail = 5, 12
    mid = (w - 1) / 2

    def inside(xx, yy):
        if yy < top or yy >= h or xx < 0 or xx >= w:
            return False
        if yy >= h - tail:
            k = yy - (h - tail) + 1
            return k <= xx <= w - 1 - k
        return True

    for yy in range(top, h):
        for xx in range(w):
            if not inside(xx, yy):
                continue
            dl = min(xx - (yy - (h - tail) + 1 if yy >= h - tail else 0), 99)
            dr = min((w - 1 - (yy - (h - tail) + 1 if yy >= h - tail else 0)) - xx, 99)
            tail_part = yy >= h - tail
            c = RED2 if xx < w * 0.36 + 8 else RED3
            if dl == 0 or dr == 0 or yy == h - 1:
                c = O
            elif dl == 1:
                c = RED2
            elif dl == 2:
                c = RED3 if tail_part else (G if (yy // 4) % 2 else G_DK)
            elif dl == 3:
                c = (G if (yy // 4) % 2 else G_DK) if tail_part else RED3
            elif dr == 1:
                c = RED3
            elif dr == 2:
                c = DARK if tail_part else (G if (yy // 4) % 2 else G_DK)
            elif dr == 3:
                c = (G if (yy // 4) % 2 else G_DK) if tail_part else DARK
            px[X + xx, yy] = C(c)
    # silver bar with clips under the rod, dark hem
    for xx in range(w):
        px[X + xx, top] = C(O)
        px[X + xx, top + 1] = C(SIL if 4 < xx < w - 5 else S2)
        px[X + xx, top + 2] = C(DARK)
    for cx in (1, w - 5):
        for xx in range(cx, cx + 4):
            px[X + xx, top] = C(S2)
            px[X + xx, top - 1] = C(O)
    px[X, top + 1] = px[X + w - 1, top + 1] = C(O)
    px[X, top + 2] = px[X + w - 1, top + 2] = C(O)
    if emblem:
        em = lion_emblem(19, 34)
        im.alpha_composite(em, (X + (w - 19) // 2, top + 4))
    if mirror:
        im = im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        img.alpha_composite(im, (x, y))
    else:
        img.alpha_composite(im, (x - ext, y))


def shard_layer(size, base, tip, width):
    """One chunky crystal on its own layer: light upper face, gold middle band, dark lower face, red-brown
    root, a white glint along the light face, dark outline. base/tip in layer coordinates."""
    im = Image.new('RGBA', size, (0, 0, 0, 0))
    bx, by = base
    tx, ty = tip
    L = math.hypot(tx - bx, ty - by) or 1
    ux, uy = (tx - bx) / L, (ty - by) / L
    nx, ny = -uy, ux
    if ny > 0:                                     # make n point "up" on screen so the light face is on top
        nx, ny = -nx, -ny
    sh = (bx + ux * L * 0.32, by + uy * L * 0.32)
    up = (sh[0] + nx * width / 2, sh[1] + ny * width / 2)
    dn = (sh[0] - nx * width / 2, sh[1] - ny * width / 2)
    mu = (sh[0] + nx * width / 6, sh[1] + ny * width / 6)
    md = (sh[0] - nx * width / 6, sh[1] - ny * width / 6)
    d = ImageDraw.Draw(im)
    d.polygon([base, up, tip], fill=C(G_LT))
    d.polygon([base, mu, tip, md], fill=C(G))
    d.polygon([base, dn, tip], fill=C(G_DK))
    d.polygon([base, mu, md], fill=C(G))
    d.line([(bx, by), (bx + ux * 3, by + uy * 3)], fill=C(RED), width=2)
    g0 = (up[0] * 0.75 + tip[0] * 0.25, up[1] * 0.75 + tip[1] * 0.25)
    g1 = (up[0] * 0.35 + tip[0] * 0.65, up[1] * 0.35 + tip[1] * 0.65)
    d.line([g0, g1], fill=C(WHITE))
    d.line([(up[0] * 0.5 + bx * 0.5, up[1] * 0.5 + by * 0.5), up], fill=C(G_HI))
    src = im.copy().load()
    px = im.load()
    w, h = size
    for y in range(h):
        for x in range(w):
            if src[x, y][3] and any(not (0 <= x + dx < w and 0 <= y + dy < h) or not src[x + dx, y + dy][3]
                                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                px[x, y] = C(O)
    return im


def shard(w, h, angle, seed=1):
    """A crystal pointing at `angle` degrees (180 = left) filling a w x h box."""
    a = math.radians(angle)
    cx, cy = w / 2, h / 2
    L = max(w, h) * 0.95
    ux, uy = math.cos(a), -math.sin(a)
    base = (cx - ux * L / 2, cy - uy * L / 2)
    tip = (cx + ux * L / 2, cy + uy * L / 2)
    return shard_layer((w, h), base, tip, max(4, min(w, h) * 0.55))


# crystal cluster beside the divider and the single shards (window-relative base -> tip, width), left side
CRYSTALS = [((-8, 107), (-19, 96), 7),          # lone shard above the cluster
            ((1, 124), (-24, 110), 13),          # big shard up-left
            ((1, 133), (-24, 133), 11),          # shard to the left
            ((-1, 135), (-5, 149), 10)]          # short shard pointing down


def crystal_cluster(img, ox, oy, mirror=False):
    for (b, t, wd) in CRYSTALS:
        lay = shard_layer((64, 80), (b[0] + 40, b[1] - 80), (t[0] + 40, t[1] - 80), wd)
        if mirror:
            lay = lay.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            img.alpha_composite(lay, (ox + 176 - 64 + 40, oy + 80))
        else:
            img.alpha_composite(lay, (ox - 40, oy + 80))


def streamer(img, ox, oy, mirror=False):
    """Red ribbon from under the crystals down and out, folded once, ending in a V cut (window-relative
    footprint x -23..1, y 149..173 on the left side)."""
    im = Image.new('RGBA', (30, 28), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # coordinates relative to (ox - 25, oy + 148)
    body = [(27, 1), (23, 1), (2, 12), (7, 16), (5, 24), (19, 17), (27, 10)]
    d.polygon(body, fill=C(RED3))
    d.polygon([(23, 1), (2, 12), (7, 14), (25, 4)], fill=C(RED2))           # lit upper edge
    d.polygon([(7, 16), (5, 24), (19, 17), (16, 15)], fill=C(RED4))         # shadowed lower flap
    d.line([(9, 15), (24, 7)], fill=C(RED5))                                # fold line
    src = im.copy().load()
    px = im.load()
    for y in range(28):
        for x in range(30):
            if src[x, y][3] and any(not (0 <= x + dx < 30 and 0 <= y + dy < 28) or not src[x + dx, y + dy][3]
                                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                px[x, y] = C(O)
    if mirror:
        im = im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        img.alpha_composite(im, (ox + 176 + 25 - 30, oy + 148))
    else:
        img.alpha_composite(im, (ox - 25, oy + 148))


def lion_emblem(w=19, h=34):
    """Own heraldic emblem: a crown over a lion head in a radiating mane with a pointed beard, gold tones with
    dark separators (procedural, symmetric)."""
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    px = im.load()
    cx = (w - 1) / 2
    crown = ["....K...K...K....", "...KYK.KYK.KYK...", "...KYYKYYYKYYK...", "...KHYYYHYYYHK...",
             "...KGGGGGGGGGK...", "..KKKKKKKKKKKKK.."]
    pal = {'K': DARK, 'Y': G_LT, 'H': G_HI, 'G': G, 'D': G_DK}
    off = (w - 17) // 2
    for j, r in enumerate(crown):
        for i, ch in enumerate(r):
            if ch in pal:
                px[off + i, j] = C(pal[ch])
    my = 17.5
    for y in range(5, h):
        for x in range(w):
            dx, dy = x - cx, y - my
            th = math.atan2(dy, dx)
            rad = math.hypot(dx / (w / 2), dy / 11.5)
            edge = 1.0 + 0.10 * math.cos(12 * th)
            beard = y > my + 8 and abs(dx) <= (h - 1 - y) * 0.75
            if rad > edge and not beard:
                continue
            if y <= 5 and px[x, y][3]:
                continue
            sector = (th + math.pi) / (2 * math.pi) * 12
            f = sector - math.floor(sector)
            c = G_LT if int(sector) % 2 == 0 else G
            if f < 0.14:
                c = DARK
            if y > my + 5:
                c = G if c == G_LT else (G_DK if c == G else c)
            px[x, y] = C(c)
    # face
    for y in range(10, 25):
        for x in range(w):
            if ((x - cx) / 4.6) ** 2 + ((y - 16.5) / 6.4) ** 2 <= 1:
                px[x, y] = C(G_LT if y < 19 else G)
    fx = int(cx)
    for (x, y, c) in ((fx - 3, 13, G_DK), (fx - 2, 13, G_DK), (fx + 2, 13, G_DK), (fx + 3, 13, G_DK),
                      (fx - 2, 14, DARK), (fx + 2, 14, DARK), (fx, 15, G_DK), (fx, 16, G_DK), (fx - 1, 17, DARK),
                      (fx, 17, DARK), (fx + 1, 17, DARK), (fx - 2, 19, DARK), (fx - 1, 20, DARK), (fx, 20, DARK),
                      (fx + 1, 20, DARK), (fx + 2, 19, DARK), (fx, 12, G_HI), (fx - 1, 11, G_HI)):
        px[x, y] = C(c)
    # dark outline around the whole emblem
    src = im.copy().load()
    for y in range(h):
        for x in range(w):
            if src[x, y][3] and any(not (0 <= x + dx < w and 0 <= y + dy < h) or not src[x + dx, y + dy][3]
                                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                px[x, y] = C(DARK)
    return im


# ----------------------------------------------------------------------------- whole kit

def ornaments(img, ox, oy, rows, banners=True, emblem=True, rails=True, crystals=True, meanders=True):
    """Everything outside the window, placed like the measured reference (window-relative): key ornaments and
    small shards by the tab, big shards over the banner rods, crest banners, rails with gems (only when there is
    room between banner and crystals), crystal fans + streamers at the divider."""
    dy = rows * 18 + 20 - 128                  # crystals/streamers follow the divider (reference: 6 rows)
    for flip in (False, True):
        if meanders:
            meander(img, ox - 2 if not flip else ox + 176 + 2 - 30, oy - 10, flip)
            img.alpha_composite(small_shard(flip), (ox + 27 if not flip else ox + 142, oy - 17))
        if rails and rows * 18 + 20 >= 110:
            rail(img, ox - 9 if not flip else ox + 176 + 2, oy + 56)
        if crystals:
            streamer(img, ox, oy + dy, flip)
            crystal_cluster(img, ox, oy + dy, flip)
    if banners:
        for flip in (False, True):             # big shard lying over each banner's rod
            lay = shard_layer((26, 16), (22, 11), (1, 2), 9)
            if flip:
                img.alpha_composite(lay.transpose(Image.Transpose.FLIP_LEFT_RIGHT), (ox + 176 - 2, oy - 7))
            else:
                img.alpha_composite(lay, (ox - 24, oy - 7))
        banner(img, ox - 28, oy + 2, emblem=emblem)
        banner(img, ox + 176 + 3, oy + 2, emblem=emblem, mirror=True)


def chest(rows=6, title_tab=True, gem=True, decorate=True):
    """The complete royal chest texture (256 x (17 + 114 + 18*rows)), window origin (40, 17)."""
    ox, oy = 40, 17
    H = 114 + rows * 18
    img = Image.new('RGBA', (256, oy + H), (0, 0, 0, 0))
    panel(img, ox, oy, rows)
    if decorate:
        ornaments(img, ox, oy, rows)
    for r in range(rows):
        for c in range(9):
            rim_slot(img, ox + 7 + c * 18, oy + 17 + r * 18)
    for r in range(3):
        for c in range(9):
            rim_slot(img, ox + 7 + c * 18, oy + rows * 18 + 30 + r * 18)
    for c in range(9):
        rim_slot(img, ox + 7 + c * 18, oy + rows * 18 + 88)
    hotbar_frame(img, ox, oy, rows)
    divider(img, ox, oy, rows, gem)
    corner_brackets(img, ox, oy, rows)
    if title_tab:
        tab(img, ox, oy, 40, 96)
    return img


if __name__ == '__main__':
    import sys
    chest().save(sys.argv[1] if len(sys.argv) > 1 else 'royal_chest.png')
