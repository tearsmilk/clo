"""Market-stall shop kit - geometry measured from a 5-screen shop GUI pack (main, sell, buy stacks, confirm,
item list), all parts drawn here. Used by gui_builder.py through `{"type": "shop", "part": ...}` layers.

Measured layout (6-row chest, texture 256x256, window at (40, 35), canvas 40/40/35/0):
  * striped awning in perspective: top edge y -15 (x 2..173), sloped part to y 5 (x -10..186), valance
    y 6..14 with one rounded scallop per stripe, 7 stripes (28 px each at the valance)
  * green sign 70x11 on the awning (x 53..122, y -23..-13) in a gold frame, flowering vines on both sides
  * corner supports left/right (x -29..-1 / 176..205): rafter from under the awning, 45 deg brace and corner
    post into the wall - drawn before the awning; a hanging vertical sign on the left rafter
    (board x -19..-6, y 42..105), vines hanging from the right one
  * plank wall x 7..168 from y 15: planks are 18 px wide and their seams sit on the slot grid (x = 7 + 18c), so
    every column of slots is one plank; plank ends staggered at y 119..125 (optional full-width sill)
  * everything clickable is whole slots: shop windows / shelves 3x4 slots, item grid 7x4 wells, buy row 7 wells
    in a green frame, -/+ groups of 3 wells in red / green frames, buttons 2-3 slots wide x 1 row
  * buttons: 1 px dark outline, light top line, lighter sides, 2 px darker lip, outline, 2 px drop shadow;
    two-tone bold letters (light, last row darker)
Coordinates passed to these functions are texture pixels; gui_builder converts window/slot coordinates.
"""
import math
import random
from PIL import Image, ImageDraw

from pixfont import _slab_mask, draw_text, text_width, LINE_H


def H(c):
    if isinstance(c, tuple):
        return c if len(c) == 4 else tuple(c) + (255,)
    c = c.lstrip('#')
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), 255)


WOOD = {k: H(v) for k, v in dict(
    out='#361b13', edge='#461f18', d1='#4d221b', d2='#573129', d3='#5e3428', well='#603928', grain='#693e2c',
    base='#7a4a30', frame='#825035', m1='#855436', m2='#8a5838', m3='#9a6442', seam='#ab724f', side='#ba815d',
    top='#db9d76', shadow='#391e17').items()}
STRIPE = {
    'red':   {k: H(v) for k, v in dict(out='#a44147', bot='#751e1e', dark='#b84950', base='#c9555a',
                                       light='#da6660', hi='#ff7770', rim='#d95959', deep='#8c383d').items()},
    'white': {k: H(v) for k, v in dict(out='#8c7e81', bot='#5b444a', dark='#b8a5aa', base='#c9b9bd',
                                       light='#dacdcf', hi='#f5f1f1', rim='#cdbac0', deep='#7e6b71').items()},
}
GREEN_SIGN = {k: H(v) for k, v in dict(body='#458966', dark='#2b6046', light='#5ea37c', frame='#c9ba82',
                                       frame_hi='#fceac5', frame_dk='#69542c', out='#45311d').items()}
VINE = [H(c) for c in ('#283b1f', '#38522b', '#4e7023', '#799237', '#b2bf4a')]
FLOWER = [H(c) for c in ('#753d5c', '#ab5986', '#d77bba', '#eba0df')]
SLATE = {k: H(v) for k, v in dict(body='#3c484f', light='#5b6a73', edge='#698185', text='#fceac5',
                                  text_dk='#c1995a', out='#16252d').items()}
GLASS = [H(c) for c in ('#4d638d', '#53678d', '#5b709a', '#6379a7', '#86ade2', '#9fc3e5', '#add3e8')]
PAPER = {k: H(v) for k, v in dict(body='#e0bb92', light='#efd3ad', dark='#bf9577', out='#8a5838',
                                  text='#9e6464', text_dk='#7a4646').items()}
BUTTON = {
    'red':   {k: H(v) for k, v in dict(out='#491524', fill='#a03c41', light='#e26f75', side='#c0575c',
                                       lip='#64242d', text='#ff9a9e', text_dk='#e26f75').items()},
    'green': {k: H(v) for k, v in dict(out='#2c3813', fill='#5f9a3c', light='#a5d47a', side='#7fb556',
                                       lip='#3f6b28', text='#e4ffc8', text_dk='#a5d47a').items()},
    'wood':  {k: H(v) for k, v in dict(out='#361b13', fill='#8a5838', light='#db9d76', side='#ab724f',
                                       lip='#5e3428', text='#fceac5', text_dk='#c1995a').items()},
    'gold':  {k: H(v) for k, v in dict(out='#45311d', fill='#c99a3c', light='#fceac5', side='#e0bb62',
                                       lip='#8a6a2a', text='#fffaf0', text_dk='#f1e1af').items()},
}


def _px(img, x, y, c):
    if 0 <= x < img.width and 0 <= y < img.height and c is not None:
        img.putpixel((x, y), c)


def _hline(img, x0, x1, y, c):
    for x in range(x0, x1 + 1):
        _px(img, x, y, c)


def _vline(img, x, y0, y1, c):
    for y in range(y0, y1 + 1):
        _px(img, x, y, c)


# ------------------------------------------------------------------ lettering

def text_size(text):
    m = _slab_mask(text, 1, 1, 'bold')
    return m.width, m.height


def letters(img, x, y, text, top, bottom, shadow=None, vertical=False):
    """Bold 7-row capitals (Latin + Cyrillic), two-tone like the pack: light rows, last row darker.
    vertical=True stacks the letters (hanging signs), x is then the centre."""
    if vertical:
        for i, ch in enumerate(text):
            w, _ = text_size(ch)
            letters(img, x - w // 2, y + i * 9, ch, top, bottom, shadow)
        return
    m = _slab_mask(text, 1, 1, 'bold')
    mp = m.load()
    for yy in range(m.height):
        for xx in range(m.width):
            if mp[xx, yy]:
                if shadow:
                    _px(img, x + xx, y + yy + 1, shadow) if not (yy + 1 < m.height and mp[xx, yy + 1]) else None
    for yy in range(m.height):
        for xx in range(m.width):
            if mp[xx, yy]:
                last = yy + 1 >= m.height or not mp[xx, yy + 1]
                _px(img, x + xx, y + yy, bottom if (last and yy >= 4) else top)


def letters_centered(img, cx, y, text, top, bottom, shadow=None):
    w, _ = text_size(text)
    letters(img, cx - w // 2, y, text, top, bottom, shadow)


# ------------------------------------------------------------------ awning

def awning(img, ox, oy, colors=('red', 'white'), stripes=7, seed=1):
    """Perspective striped awning over the window at (ox, oy): sloped roof y oy-15..oy+5, valance to oy+14."""
    rnd = random.Random(seed)
    yt, yb = oy - 15, oy + 5
    xl_t, xr_t, xl_b, xr_b = ox + 2, ox + 173, ox - 10, ox + 186
    phase = [rnd.uniform(0, 6) for _ in range(stripes)]
    for y in range(yt, yb + 1):
        t = (y - yt) / (yb - yt)
        xl = round(xl_t + (xl_b - xl_t) * t)
        xr = round(xr_t + (xr_b - xr_t) * t)
        for x in range(xl, xr + 1):
            u = (x - xl) / max(1, xr - xl + 1)
            k = min(stripes - 1, int(u * stripes))
            P = STRIPE[colors[k % 2]]
            if y == yt or x in (xl, xr):
                c = P['out']
            else:
                w = math.sin(y * 0.85 + 2.6 * math.sin(x * 0.07 + phase[k]) + phase[k])
                c = P['light'] if w > 0.62 else P['dark'] if w < -0.55 else P['base']
                if y <= yt + 2:                               # shade under the sign / roof ridge
                    c = P['dark'] if y == yt + 2 else P['deep']
            _px(img, x, y, c)
    # valance: highlight line, flat band, one scallop per stripe with a lighter rim and dark outline
    seg = (xr_b - xl_b + 1) / stripes
    for k in range(stripes):
        P = STRIPE[colors[k % 2]]
        sx0 = round(xl_b + k * seg)
        sx1 = round(xl_b + (k + 1) * seg) - 1
        for y in range(yb + 1, yb + 10):
            r = y - yb                                       # 1..9
            inset = max(0, r - 5)                           # rows 6..9 round the bottom corners
            x0, x1 = sx0 + inset, sx1 - inset
            for x in range(x0, x1 + 1):
                edge_x = x in (x0, x1)
                if r == 1:
                    c = P['hi']
                elif r == 9:
                    c = P['bot']
                elif edge_x and (k == 0 and x == x0 or k == stripes - 1 and x == x1 or inset):
                    c = P['bot']
                elif inset and x in (x0 + 1, x1 - 1) or r == 8:
                    c = P['rim']
                else:
                    c = P['dark'] if r > 2 else P['base']
                _px(img, x, y, c)
    # shadow on the wall right under the valance (only where there is wall, never in the air)
    for x in range(ox + 7, ox + 169):
        _px(img, x, yb + 10, WOOD['out'])
        _px(img, x, yb + 11, WOOD['d1'])


# ------------------------------------------------------------------ sign, vines, eaves, hanging sign

def sign(img, cx, y, text, w=70, h=11):
    """Green sign board with a gold frame (pack: 70x11 at x 53..122, y -23..-13)."""
    G = GREEN_SIGN
    x0 = cx - w // 2
    x1 = x0 + w - 1
    d = ImageDraw.Draw(img)
    d.rectangle((x0 - 2, y - 2, x1 + 2, y + h + 1), fill=G['out'])
    d.rectangle((x0 - 1, y - 1, x1 + 1, y + h), fill=G['frame'])
    _hline(img, x0 - 1, x1 + 1, y - 1, G['frame_hi'])
    _hline(img, x0 - 1, x1 + 1, y + h, G['frame_dk'])
    d.rectangle((x0, y, x1, y + h - 1), fill=G['body'])
    _hline(img, x0, x1, y + h - 1, G['dark'])
    _hline(img, x0, x1, y, G['light'])
    for xx in (x0 - 2, x1 + 2):
        for yy in (y - 2, y + h + 1):
            _px(img, xx, yy, (0, 0, 0, 0))
    tw, th = text_size(text)
    letters(img, cx - tw // 2, y + (h - th) // 2 + 1, text, G['frame_hi'], G['frame'], shadow=G['dark'])


def vines(img, x0, y0, x1, y1, seed=1, flowers=3, hang=0):
    """Bushy mound of leaves sitting on its bottom edge (pack: beside the sign on the awning), pink flowers;
    hang > 0 adds two leafy strands hanging that many px below the box (eave vines)."""
    rnd = random.Random(seed)
    cl = Image.new('RGBA', img.size, (0, 0, 0, 0))
    cx, rx, ry = (x0 + x1) / 2, (x1 - x0) / 2, (y1 - y0)
    pts = []
    for _ in range(int(rx * ry * 0.9)):
        x = rnd.uniform(x0, x1)
        y = rnd.uniform(y0, y1)
        if ((x - cx) / rx) ** 2 + ((y1 - y) / ry) ** 2 <= 1.0:      # half-ellipse standing on y1
            pts.append((int(x), int(y)))
    for s_ in range(2 if hang else 0):
        sx = int(cx + rnd.uniform(-rx * 0.5, rx * 0.5))
        for yy in range(y1 - 2, y1 + hang, 2):
            pts.append((sx + rnd.choice((-1, 0, 0, 1)), yy))
    pts.sort(key=lambda p: (p[1], p[0]))
    for (x, y) in pts:                                     # rounded 3x3 leaves, lit from the top-left
        tone = rnd.choice((2, 3, 3, 4, 4))
        for dx, dy in ((1, 0), (0, 1), (1, 1), (2, 1), (1, 2), (0, 0), (2, 0), (0, 2), (2, 2)):
            if (dx, dy) in ((0, 0), (2, 0), (0, 2), (2, 2)) and rnd.random() < 0.7:
                continue
            c = VINE[tone] if dy == 0 or (dx, dy) == (0, 1) else VINE[max(2, tone - 1)] if dy == 1 else VINE[1]
            _px(cl, x + dx, y + dy, c)
    # outline the cluster with the darkest green
    src = cl.copy()
    sp = src.load()
    for y in range(max(0, y0 - 2), min(img.height, y1 + hang + 3)):
        for x in range(max(0, x0 - 2), min(img.width, x1 + 3)):
            if sp[x, y][3]:
                continue
            if any(0 <= x + dx < img.width and 0 <= y + dy < img.height and sp[x + dx, y + dy][3]
                   for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                cl.putpixel((x, y), VINE[0])
    for _ in range(flowers):                                # 4x4 flowers (pack size): rounded, lit top-left
        x = int(cx + rnd.uniform(-rx * 0.6, rx * 0.6)) - 1
        y = rnd.randint(int(y1 - ry * 0.7), y1 - 3)
        for dx, dy, c in ((1, 0, FLOWER[2]), (2, 0, FLOWER[1]), (0, 1, FLOWER[2]), (1, 1, FLOWER[3]),
                          (2, 1, FLOWER[2]), (3, 1, FLOWER[1]), (0, 2, FLOWER[1]), (1, 2, FLOWER[2]),
                          (2, 2, FLOWER[1]), (3, 2, FLOWER[0]), (1, 3, FLOWER[0]), (2, 3, FLOWER[0])):
            _px(cl, x + dx, y + dy, c)
    img.alpha_composite(cl)


def eave(img, ox, oy, side='left'):
    """Corner support of the stall, measured from the pack (window coords, left side; the right one is mirrored):
      * rafter: comes out from under the awning (inner end x -6..1 at y 16, ends at the window edge x -1 lower
        down), arches down and out to a blunt tip at x -29, y 26..34; ~9 px thick: outline, 4 rows of light wood,
        a light streak, dark underside, dark outline
      * brace: 8 px wide, from the rafter's underside (x -6, y 23) down at 45 deg into the wall corner (x 6, y 35)
      * corner post: from under the awning (x 3..10, y 16) slanting into the wall top corner (x 8..13, y 27) with
        a dark notch where it meets the wall
    Draw it before the awning so the valance hides the upper ends. Returns the rafter's bottom y per x (window
    coords) so ropes / vines can hang from it."""
    def P(x, y, c):
        _px(img, ox + (x if side == 'left' else 175 - x), oy + y, c)

    W = WOOD
    bottom = {}
    for x in range(-29, 2):                               # rafter
        top = 16 if x >= -6 else 16 + round(10 * math.sqrt((-6 - x) / 23))
        if x >= -1:
            bot = 18                                      # under the valance it only reaches the post
        else:
            bot = round(35 - (x + 27) * 8 / 20) if x < -7 else 27 + (x + 7)
        bot = max(bot, top + 3)
        bottom[x] = bot
        for y in range(top, bot + 1):
            k = y - top
            if x == -29 or y == top:
                c = W['m2'] if (y == top and x != -29) else W['out']
                c = W['out'] if x == -29 else H('#603620')
            elif y == bot:
                c = H('#3d1816')
            elif y == bot - 1:
                c = H('#522821')
            elif k <= 4:
                c = W['m2'] if x < -10 else W['base']
            elif k == 5:
                c = W['side']
            else:
                c = H('#5e3028')
            P(x, y, c)
    for y in range(23, 36):                               # brace into the wall corner
        xl = -6 + (y - 23)
        for i, c in enumerate((H('#603620'), H('#603620'), W['m2'], W['side'], H('#5e3028'), H('#5e3028'),
                               H('#5e3028'), H('#3d1816'))):
            x = xl + i
            if x <= 6:
                P(x, y, c)
    for y in range(16, 28):                               # corner post into the wall top
        xl = 3 + round((y - 16) * 0.45)
        for i, c in enumerate((W['edge'], W['base'], W['base'], W['side'], H('#5e3028'), H('#5e3028'),
                               H('#5e3028'), W['edge'])):
            P(xl + i, y, c)
    for y in (28, 29):
        for x in range(8, 14):
            P(x, y, H('#522821'))
    return bottom


def hanging_sign(img, cx, y_beam, y0, text, h=None):
    """Vertical board hanging on a twisted rope from the eave rafter (pack: 14 x 64 board at x -19..-6, y 42..105,
    rope 4 px wide), letters stacked top to bottom."""
    S = SLATE
    n = len(text)
    h = h or n * 9 + 7
    w = 14
    x0, x1 = cx - w // 2, cx - w // 2 + w - 1
    rope = (H('#5f4b21'), H('#897339'), H('#b99f5e'), H('#3c2517'))
    for yy in range(y_beam, y0):
        for i in range(4):
            c = rope[(i + yy) % 3] if i < 3 else rope[3]
            _px(img, cx - 2 + i, yy, c)
    d = ImageDraw.Draw(img)
    d.rectangle((x0, y0, x1, y0 + h - 1), fill=S['out'])
    d.rectangle((x0 + 1, y0 + 1, x1 - 1, y0 + h - 2), fill=S['text'])
    d.rectangle((x0 + 2, y0 + 2, x1 - 2, y0 + h - 3), fill=S['body'])
    _vline(img, x0 + 2, y0 + 2, y0 + h - 3, S['light'])
    _hline(img, x0 + 2, x1 - 2, y0 + 2, S['edge'])
    _hline(img, x0 + 1, x1 - 1, y0 + h - 2, S['text_dk'])
    letters(img, cx, y0 + 4, text, S['text'], S['text_dk'], vertical=True)
    _hline(img, x0 + 1, x1 + 1, y0 + h, H('#00000060'))


# ------------------------------------------------------------------ wall, sill, plank ends

def wall(img, ox, oy, y_top, y_bottom, x0=7, x1=168, seed=1):
    """Vertical plank wall x 7..168 (the vanilla window border stays visible beside it), seams on the slot grid
    (x = 7 + 18c): exactly one 18 px plank per slot column."""
    rnd = random.Random(seed)
    for y in range(oy + y_top, oy + y_bottom + 1):
        for x in range(ox + x0, ox + x1 + 1):
            _px(img, x, y, WOOD['base'])
    for c in range(1, 9):
        sx = ox + 7 + 18 * c
        _vline(img, sx, oy + y_top, oy + y_bottom, WOOD['d3'])
        _vline(img, sx - 1, oy + y_top, oy + y_bottom, WOOD['seam'])
        _vline(img, sx + 1, oy + y_top, oy + y_bottom, WOOD['seam'])
    for c in range(9):                                      # grain strokes and knots inside each plank
        px0 = ox + 7 + 18 * c + 2
        for _ in range(3):
            gx = px0 + rnd.randint(1, 12)
            gy = oy + y_top + rnd.randint(0, max(1, y_bottom - y_top - 10))
            gl = rnd.randint(6, 22)
            for yy in range(gy, min(gy + gl, oy + y_bottom)):
                _px(img, gx, yy, WOOD['grain'])
                if rnd.random() < 0.5:
                    _px(img, gx + 1, yy, WOOD['grain'])
        if rnd.random() < 0.6:
            kx = px0 + rnd.randint(3, 10)
            ky = oy + y_top + rnd.randint(4, max(5, y_bottom - y_top - 6))
            for dx, dy, cc in ((0, 0, WOOD['d3']), (1, 0, WOOD['grain']), (0, 1, WOOD['grain']),
                               (1, 1, WOOD['d2']), (0, -1, WOOD['seam'])):
                _px(img, kx + dx, ky + dy, cc)
    _vline(img, ox + x0, oy + y_top, oy + y_bottom, H('#603620'))
    _vline(img, ox + x0 + 1, oy + y_top, oy + y_bottom, WOOD['seam'])
    _vline(img, ox + x1, oy + y_top, oy + y_bottom, H('#603620'))
    _vline(img, ox + x1 - 1, oy + y_top, oy + y_bottom, WOOD['grain'])


def sill(img, ox, oy, y, x0=7, x1=168):
    """Horizontal board across the wall (counter / window sill) with a shadow under it."""
    _hline(img, ox + x0, ox + x1, oy + y, WOOD['out'])
    _hline(img, ox + x0, ox + x1, oy + y + 1, WOOD['top'])
    for k in range(2, 5):
        _hline(img, ox + x0, ox + x1, oy + y + k, WOOD['side'] if k == 2 else WOOD['m3'])
    _hline(img, ox + x0, ox + x1, oy + y + 5, WOOD['d3'])
    _hline(img, ox + x0, ox + x1, oy + y + 6, WOOD['out'])
    _hline(img, ox + x0 + 1, ox + x1 - 1, oy + y + 7, WOOD['shadow'])
    _hline(img, ox + x0 + 1, ox + x1 - 1, oy + y + 8, WOOD['d1'])


def plank_ends(img, ox, oy, y_from, y_end=125, x0=7, x1=168, seed=1):
    """Planks continue under the sill and end at staggered heights, each end with a lit face and a shadow."""
    rnd = random.Random(seed)
    offs = [0, -4, -1, -6, 0, -5, -2, -6, -1, -3]          # stays above the client's inventory label (y 128)
    rnd.shuffle(offs)
    edges = [ox + x0] + [ox + 7 + 18 * c for c in range(1, 10) if ox + 7 + 18 * c < ox + x1] + [ox + x1 + 1]
    for i in range(len(edges) - 1):
        a, b = edges[i], edges[i + 1] - 1
        end = oy + y_end + offs[i % len(offs)]
        for y in range(oy + y_from, end + 1):
            for x in range(a, b + 1):
                c = WOOD['base']
                if x in (a, b):
                    c = WOOD['edge']
                elif x in (a + 1, b - 1):
                    c = WOOD['seam'] if x == a + 1 else WOOD['grain']
                elif (x - a) % 6 == 3 and (y + i) % 9 < 6:
                    c = WOOD['grain']
                if y >= end - 3:                              # end face
                    c = WOOD['out'] if y == end or x in (a, b) else WOOD['d2'] if y > end - 3 else WOOD['seam']
                _px(img, x, y, c)
        for x in range(a + 1, b + 2):                          # shadow on the panel behind
            _px(img, x, end + 1, H('#00000055'))


# ------------------------------------------------------------------ windows, wells, cabinet

def well(img, x, y, interior=None):
    """16x16 recessed item well at the slot's item area (x, y)."""
    W_ = WOOD
    _hline(img, x, x + 15, y - 1, W_['top'])
    _vline(img, x - 1, y - 1, y + 15, W_['side'])
    _vline(img, x + 16, y - 1, y + 15, W_['side'])
    for yy in range(y, y + 16):
        for xx in range(x, x + 16):
            _px(img, xx, yy, interior or W_['well'])
    _hline(img, x, x + 15, y, W_['edge'])
    _hline(img, x, x + 15, y + 1, W_['edge'])
    _vline(img, x, y, y + 13, W_['edge'])
    _vline(img, x + 15, y, y + 13, W_['edge'])
    _hline(img, x, x + 15, y + 14, W_['m3'])


def frame(img, x0, y0, x1, y1, fill=None, out=None, light=None, dark=None):
    d = ImageDraw.Draw(img)
    d.rectangle((x0, y0, x1, y1), fill=out or WOOD['edge'])
    d.rectangle((x0 + 1, y0 + 1, x1 - 1, y1 - 1), fill=fill or WOOD['frame'])
    _hline(img, x0 + 1, x1 - 1, y0 + 1, light or WOOD['m3'])
    _hline(img, x0 + 1, x1 - 1, y1 - 1, dark or WOOD['d3'])
    for xx, yy in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        _px(img, xx, yy, (0, 0, 0, 0))


def wells(img, ox, oy, c0, r0, cw, ch, framed=True):
    """Grid of item wells on whole slots (item list, sell grid, cabinet) inside a wooden frame."""
    if framed:
        x0, y0 = ox + 7 + 18 * c0 - 3, oy + 17 + 18 * r0 - 3
        frame(img, x0, y0, x0 + 18 * cw + 5, y0 + 18 * ch + 5)
        _hline(img, x0 + 1, x0 + 18 * cw + 5, y0 + 18 * ch + 6, WOOD['shadow'])
        _hline(img, x0 + 1, x0 + 18 * cw + 5, y0 + 18 * ch + 7, WOOD['d1'])
    for r in range(ch):
        for c in range(cw):
            well(img, ox + 8 + 18 * (c0 + c), oy + 18 + 18 * (r0 + r))


def shop_window(img, ox, oy, c0, r0, cw=3, ch=4, shelves=2, seed=1, poster=None, items=()):
    """Glass shop window over a block of slots (pack: frame 44x71 over 3x4 slots): wooden frame, blue glass with
    two light diagonal streaks, wooden shelves; optional parchment poster and 16x16 items on the shelves."""
    fx0, fy0 = ox + 7 + 18 * c0 + 5, oy + 17 + 18 * r0 + 3
    fx1, fy1 = ox + 7 + 18 * (c0 + cw) - 6, oy + 17 + 18 * (r0 + ch) + 1
    frame(img, fx0, fy0, fx1, fy1, fill=WOOD['m1'], light=WOOD['seam'], dark=WOOD['d2'])
    gx0, gy0, gx1, gy1 = fx0 + 3, fy0 + 3, fx1 - 3, fy1 - 3
    gw = gx1 - gx0 + 1
    for y in range(gy0, gy1 + 1):
        for x in range(gx0, gx1 + 1):
            band = (x - gx0 + (gy1 - y)) % (gw + 24)
            c = GLASS[2] if y < gy0 + 2 else GLASS[1] if (x + y) % 11 else GLASS[0]
            if 6 <= band <= 9 or 15 <= band <= 16:
                c = GLASS[5] if band != 16 else GLASS[4]
            if x == gx0 or y == gy0:
                c = GLASS[0]
            _px(img, x, y, c)
    shelf_ys = [round(gy0 + (gy1 - gy0) * (i + 1) / (shelves + 1)) for i in range(shelves)]
    for sy in shelf_ys:
        _hline(img, gx0, gx1, sy - 1, WOOD['out'])
        _hline(img, gx0, gx1, sy, WOOD['top'])
        _hline(img, gx0, gx1, sy + 1, WOOD['m3'])
        _hline(img, gx0, gx1, sy + 2, WOOD['d3'])
        _hline(img, gx0, gx1, sy + 3, GLASS[0])
    levels = [sy - 1 for sy in shelf_ys] + [gy1 + 1]      # the y each row of items stands on
    if poster:                                            # small parchment in the top section, thin letters
        sp = 1 if text_width(poster, spacing=1) <= gw - 8 else 0
        tw = text_width(poster, spacing=sp)
        nl = poster.count('\n') + 1
        ph = nl * LINE_H + 3
        pcx = (gx0 + gx1) // 2
        top = gy0 + max(1, (levels[0] - gy0 - ph) // 2)
        _paper(img, pcx - tw // 2 - 3, top, pcx - tw // 2 + tw + 2, top + ph, seed)
        draw_text(img, pcx - tw // 2 + 1, top + 3, poster, PAPER['text'], spacing=sp, align='center')
        levels = levels[1:]
    for i, it in enumerate(items):
        if it is None or i // 2 >= len(levels):
            continue
        base = levels[i // 2]
        x = gx0 + 2 if i % 2 == 0 else gx1 - 1 - it.width
        img.alpha_composite(it, (x, base - it.height))


def _paper(img, x0, y0, x1, y1, seed=1):
    """Parchment with torn edges (posters, banners)."""
    rnd = random.Random(seed)
    for y in range(y0, y1 + 1):
        cut_l = rnd.choice((0, 0, 0, 1)) if y not in (y0, y1) else 1
        cut_r = rnd.choice((0, 0, 0, 1)) if y not in (y0, y1) else 1
        for x in range(x0 + cut_l, x1 - cut_r + 1):
            c = PAPER['body']
            if y == y0 or x == x0 + cut_l:
                c = PAPER['light']
            if y == y1 or x == x1 - cut_r:
                c = PAPER['dark']
            if (y == y1 or y == y0) and rnd.random() < 0.18:
                continue
            _px(img, x, y, c)


def banner(img, cx, y, text, w=None, seed=2):
    """Parchment banner with torn edges and muted brown letters (pack: 'BUY STACKS!', 'ARE YOU SURE ?')."""
    tw, th = text_size(text)
    w = w or tw + 16
    x0 = cx - w // 2
    _paper(img, x0, y, x0 + w - 1, y + 16, seed)
    _hline(img, x0 + 2, x0 + w - 2, y + 17, H('#00000050'))
    letters_centered(img, cx, y + 5, text, PAPER['text'], PAPER['text_dk'])


# ------------------------------------------------------------------ buttons, groups, badge

def button(img, x0, y0, x1, y1, color='green', text=''):
    """Bevelled button as measured: outline, light top line, lighter sides, 2 px lip, 2 px drop shadow."""
    B = BUTTON[color]
    d = ImageDraw.Draw(img)
    d.rectangle((x0 + 1, y1 + 1, x1 + 1, y1 + 2), fill=H('#42251a'))         # drop shadow on the wall
    d.rectangle((x0, y0, x1, y1), fill=B['out'])
    d.rectangle((x0 + 1, y0 + 1, x1 - 1, y1 - 1), fill=B['fill'])
    _hline(img, x0 + 1, x1 - 1, y0 + 1, B['light'])
    _vline(img, x0 + 1, y0 + 2, y1 - 4, B['side'])
    _vline(img, x1 - 1, y0 + 2, y1 - 4, B['side'])
    _hline(img, x0 + 2, x1 - 2, y1 - 4, B['side'])
    _hline(img, x0 + 1, x1 - 1, y1 - 3, B['lip'])
    _hline(img, x0 + 1, x1 - 1, y1 - 2, B['lip'])
    _hline(img, x0 + 1, x1 - 1, y1 - 1, B['fill'])
    if text:
        tw, th = text_size(text)
        letters(img, (x0 + x1 + 1) // 2 - tw // 2, y0 + 3, text, B['text'], B['text_dk'])


def glyph(img, x, y, kind, color):
    """Minus / plus sign centred in a 16x16 well at (x, y): outline, light top, fill, dark bottom."""
    B = BUTTON[color]
    if kind == 'minus':
        cells = {(xx, yy) for xx in range(4, 12) for yy in range(7, 10)}
    else:
        cells = {(xx, yy) for xx in range(4, 12) for yy in range(7, 10)} | \
                {(xx, yy) for xx in range(6, 10) for yy in range(4, 13)}
    for (cx, cy) in cells:
        up = (cx, cy - 1) not in cells
        down = (cx, cy + 1) not in cells
        _px(img, x + cx, y + cy, B['light'] if up else B['lip'] if down else B['fill'])
    for (cx, cy) in cells:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (cx + dx, cy + dy) not in cells:
                _px(img, x + cx + dx, y + cy + dy, B['out'])


def slot_group(img, ox, oy, c0, r, n, color='green', kind=None):
    """Coloured frame around n wells in a row (buy row, -/+ amount groups), optional -/+ in every well."""
    B = BUTTON[color]
    x0, y0 = ox + 7 + 18 * c0 - 4, oy + 17 + 18 * r - 4
    x1, y1 = ox + 7 + 18 * (c0 + n) + 3, oy + 17 + 18 * (r + 1) + 5
    d = ImageDraw.Draw(img)
    d.rectangle((x0 + 1, y1 + 1, x1 + 1, y1 + 2), fill=H('#42251a'))
    d.rectangle((x0, y0, x1, y1), fill=B['out'])
    d.rectangle((x0 + 1, y0 + 1, x1 - 1, y1 - 1), fill=B['fill'])
    _hline(img, x0 + 1, x1 - 1, y0 + 1, B['light'])
    _hline(img, x0 + 1, x1 - 1, y1 - 2, B['lip'])
    _hline(img, x0 + 1, x1 - 1, y1 - 1, B['lip'])
    for xx, yy in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        _px(img, xx, yy, (0, 0, 0, 0))
    for i in range(n):
        wx, wy = ox + 8 + 18 * (c0 + i), oy + 18 + 18 * r
        well(img, wx, wy)
        if kind:
            glyph(img, wx, wy, kind, color)


def badge(img, x, y, text, color='green'):
    """Small counter plate (amount '64') under a slot."""
    B = BUTTON[color]
    tw, th = text_size(text)
    w = max(16, tw + 6)
    button(img, x + 8 - w // 2, y, x + 8 - w // 2 + w - 1, y + 13, color, '')
    letters(img, x + 8 - tw // 2, y + 2, text, B['text'], B['text_dk'])


# ------------------------------------------------------------------ whole stall

def stall(img, ox, oy, sign_text='МАГАЗИН', hanging='ОТКРЫТО', sill_y=None, seed=3, awning_colors=('red', 'white')):
    """Everything every screen of the set shares: wall, plank ends, awning, sign, vines, eaves, hanging sign
    (+ a full-width sill board at sill_y if given). Draw it first, then windows / wells / buttons on top.
    The planks run down to staggered ends at y 119..125, above the client's 'Inventory' label (y 128)."""
    wall(img, ox, oy, 15, 112, seed=seed)
    plank_ends(img, ox, oy, 112, seed=seed)
    if sill_y:
        sill(img, ox, oy, sill_y)
    bl = eave(img, ox, oy, 'left')                        # before the awning: it comes out from under the valance
    br = eave(img, ox, oy, 'right')
    awning(img, ox, oy, awning_colors, seed=seed)
    vines(img, ox + 25, oy - 31, ox + 53, oy - 9, seed=seed, flowers=2)
    vines(img, ox + 122, oy - 31, ox + 150, oy - 9, seed=seed + 1, flowers=2)
    vines(img, ox + 183, oy + 11, ox + 199, oy + 21, seed=seed + 2, flowers=2)            # sitting on the right rafter
    vines(img, ox + 189, oy + 27, ox + 195, oy + 31, seed=seed + 5, flowers=1, hang=12)   # strand hanging under it
    sign(img, ox + 88, oy - 23, sign_text)
    if hanging:
        hanging_sign(img, ox - 12, oy + bl[-12] + 1, oy + 42, hanging)


# ------------------------------------------------------------------ 16x16 item icons of the set

ICON_SHAPES = {        # 12x8 glyph masks ('#' fill), drawn light with a dark underside on the plaque
    'back':  ['    #       ', '   ##       ', '  ##########', ' ###########', '  ##########', '   ##       ',
              '    #       '],
    'next':  ['       #    ', '       ##   ', '########### ', '############', '########### ', '       ##   ',
              '       #    '],
    'home':  ['     ##     ', '    ####    ', '   ######   ', '  ########  ', '   ######   ', '   ##  ##   ',
              '   ##  ##   '],
    'close': ['  ##    ##  ', '   ##  ##   ', '    ####    ', '     ##     ', '    ####    ', '   ##  ##   ',
              '  ##    ##  '],
    'ok':    ['         ## ', '        ##  ', '       ##   ', '  ##  ##    ', '   ####     ', '    ##      ',
              '            '],
}


def nav_icon(kind='next', color='wood'):
    """16x16 square plaque with a glyph (pack: wooden back / next buttons used as item textures in slots)."""
    B = BUTTON[color]
    im = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 15, 15), fill=B['out'])
    d.rectangle((1, 1, 14, 12), fill=B['side'])
    d.rectangle((2, 2, 13, 11), fill=B['fill'])
    _hline(im, 1, 14, 1, B['light'])
    _hline(im, 1, 14, 13, B['lip'])
    _hline(im, 1, 14, 14, B['lip'])
    for xx, yy in ((0, 0), (15, 0), (0, 15), (15, 15)):
        im.putpixel((xx, yy), (0, 0, 0, 0))
    rows = ICON_SHAPES[kind]
    for j, row in enumerate(rows):
        for i, c in enumerate(row):
            if c == '#':
                below = j + 1 >= len(rows) or rows[j + 1][i] != '#'
                if color == 'wood':                     # embossed like the pack: light glyph, darker underside
                    _px(im, 2 + i, 3 + j, B['side'] if below else B['light'])
                else:
                    _px(im, 2 + i, 3 + j, B['text_dk'] if below else B['text'])
    return im


def alert_icon():
    """16x16 squat red warning triangle with a white '!' (not enough money, inventory full)."""
    out, fill, light, dark = H('#4a0d16'), H('#c8202e'), H('#ff6464'), H('#8e1420')
    im = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    for y in range(4, 15):
        half = 1 + (y - 4) * 6 // 10
        for x in range(8 - half, 8 + half):
            edge = x in (8 - half, 8 + half - 1) or y in (4, 14)
            _px(im, x, y, out if edge else light if y < 7 else dark if y > 12 else fill)
    for y in range(6, 11):
        for x in (7, 8):
            _px(im, x, y, H('#ffffff') if y < 10 else H('#f2d0d0'))
    for x in (7, 8):
        _px(im, x, 12, H('#ffffff'))
    return im


def render_icon(name):
    """'back' / 'next' / 'home' / 'close' / 'ok' [':color'] or 'alert' -> 16x16 RGBA."""
    if name == 'alert':
        return alert_icon()
    kind, _, color = name.partition(':')
    return nav_icon(kind, color or 'wood')
