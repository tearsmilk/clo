"""Steel safe kit: brushed-steel window theme, safe door, hinges, keypad, code display with lamps, handle wheel,
brass nameplates, keyhole, bolt receivers. Used by gui_builder.py: `theme: "steel"` (window + slot wells) and
`{"type": "safe", "part": ...}` layers. Example: assets/examples/safe/ (code lock + storage skin).

Rules carried over from the measured packs (references/shop-flow.md, references/replicate.md):
  * everything clickable sits on whole slots: keys are 16x16 in the slot's item area, lamps are centred in slots
    so a 'lit lamp' item covers its socket exactly
  * colour = meaning: steel digits, red clear, green OK
  * keys / buttons: dark outline, light top line, lighter sides, 2 px darker lip, drop shadow
  * parts that hold something are attached, never floating: hinge leaves are screwed to the door and the
    knuckle overlaps the leaf; the wheel has a hub plate and a shadow on the door
  * the client writes 'Inventory' in dark grey at (8, 18*rows + 20) - a dark theme needs a light band there
Coordinates passed to these functions are texture pixels unless a parameter says window / slot.
"""
import math
import random
from PIL import Image, ImageDraw

from shop import H, _px, _hline, _vline, _keep, _restore, letters, text_size, ICON_SHAPES
from pixfont import draw_text, text_width

STEEL = {k: H(v) for k, v in dict(
    out='#101219', d3='#191c24', d2='#232731', d1='#2e333f', base='#3b414f', m1='#4a5263', m2='#5c6578',
    l1='#76829a', l2='#9aa6bc', hi='#c9d2e0', spec='#eef2f8').items()}
BRASS = {k: H(v) for k, v in dict(
    out='#2e1c0c', d2='#5a3a14', d1='#8a5a1e', base='#b8842e', l1='#dcae4a', hi='#f6dc8a').items()}
LCD = {k: H(v) for k, v in dict(bg='#0b1410', line='#10201a', ring='#1d3a2a', glass='#143322',
                                glow='#2bd46a', glow_l='#7af0a0', glow_hi='#e0fff0', red='#e0343c').items()}
KEY = {
    'steel': {k: H(v) for k, v in dict(out='#101219', fill='#5c6578', light='#c9d2e0', side='#76829a',
                                       lip='#2e333f', text='#eef2f8', text_dk='#9aa6bc').items()},
    'red':   {k: H(v) for k, v in dict(out='#3a0c14', fill='#a8323c', light='#f08088', side='#c8505a',
                                       lip='#5e1820', text='#ffe0e0', text_dk='#f08088').items()},
    'green': {k: H(v) for k, v in dict(out='#10240e', fill='#3f8a3a', light='#a0e08a', side='#5fae52',
                                       lip='#20501e', text='#e8ffe0', text_dk='#a0e08a').items()},
}


# ------------------------------------------------------------------ window theme

def _brushed(img, x0, y0, x1, y1, seed=3, light=None, dark=None, density=0.08):
    """Horizontal brush streaks of the neighbouring steel tones."""
    rnd = random.Random(seed)
    light, dark = light or STEEL['m1'], dark or STEEL['d1']
    for y in range(y0, y1 + 1):
        x = x0
        while x <= x1:
            if rnd.random() < density:
                ln = rnd.randint(5, 26)
                c = light if rnd.random() < 0.55 else dark
                for xx in range(x, min(x1, x + ln) + 1):
                    _px(img, xx, y, c)
                x += ln + rnd.randint(4, 20)
            else:
                x += rnd.randint(3, 12)


def rivet(img, x, y):
    """3x3 dome rivet with a dark ring: lit top-left, dark bottom-right."""
    S = STEEL
    for dx, dy, c in ((0, -1, S['out']), (-1, 0, S['out']), (1, 0, S['out']), (0, 1, S['out']),
                      (-1, -1, S['d2']), (1, -1, S['d1']), (-1, 1, S['d1']), (1, 1, S['out'])):
        _px(img, x + dx, y + dy, c)
    _px(img, x, y, S['l2'])
    _px(img, x - 1, y - 1, S['hi'])
    _px(img, x + 1, y + 1, S['d2'])


def panel(img, box, rows=6, seed=3):
    """Brushed steel window body (frame_style 'steel'): chamfered outline, 2 px bevel, brush streaks, corner
    rivets, and a light band under the client's 'Inventory' label so the dark-grey text stays readable."""
    S = STEEL
    bx, by, W, Hh = box
    d = ImageDraw.Draw(img)
    d.rectangle((bx, by, bx + W - 1, by + Hh - 1), fill=S['out'])
    d.rectangle((bx + 1, by + 1, bx + W - 2, by + Hh - 2), fill=S['base'])
    _brushed(img, bx + 3, by + 3, bx + W - 4, by + Hh - 4, seed)
    _hline(img, bx + 1, bx + W - 2, by + 1, S['l2'])
    _hline(img, bx + 1, bx + W - 3, by + 2, S['l1'])
    _vline(img, bx + 1, by + 1, by + Hh - 2, S['l2'])
    _vline(img, bx + 2, by + 1, by + Hh - 3, S['l1'])
    _hline(img, bx + 2, bx + W - 2, by + Hh - 2, S['d3'])
    _hline(img, bx + 3, bx + W - 2, by + Hh - 3, S['d2'])
    _vline(img, bx + W - 2, by + 2, by + Hh - 2, S['d3'])
    _vline(img, bx + W - 3, by + 3, by + Hh - 2, S['d2'])
    for cx, cy in ((0, 0), (W - 1, 0), (0, Hh - 1), (W - 1, Hh - 1)):      # chamfered corners like vanilla
        for ddx in range(3):
            for ddy in range(3 - ddx):
                _px(img, bx + abs(cx - ddx), by + abs(cy - ddy), (0, 0, 0, 0))
        _px(img, bx + abs(cx - 1) if cx else bx + 1, by + abs(cy - 1) if cy else by + 1, S['out'])
    # light band behind the 'Inventory' label (y 18*rows + 19 .. +29)
    ly = by + 18 * rows + 18
    d.rectangle((bx + 5, ly, bx + W - 6, ly + 11), fill=S['l1'])
    _hline(img, bx + 5, bx + W - 6, ly, S['hi'])
    _hline(img, bx + 5, bx + W - 6, ly + 11, S['m1'])
    _brushed(img, bx + 6, ly + 2, bx + W - 7, ly + 9, seed + 1, light=S['l2'], dark=S['m2'], density=0.05)
    for rx, ry in ((bx + 5, by + 5), (bx + W - 6, by + 5), (bx + 5, by + Hh - 6), (bx + W - 6, by + Hh - 6)):
        rivet(img, rx, ry)


def case(img, ox, oy, rows=6, seed=3, h=None):
    """The safe as a steel box over the container part of the window only (x 0..175, y 0..17 + 18*rows); the
    player inventory below stays vanilla (the client always draws it - it cannot be removed, only left out of
    our texture). Chamfered outline, 2 px bevel, brush streaks, corner rivets."""
    S = STEEL
    W, Hh = 176, h or 18 + 18 * rows
    bx, by = ox, oy
    d = ImageDraw.Draw(img)
    d.rectangle((bx, by, bx + W - 1, by + Hh - 1), fill=S['out'])
    d.rectangle((bx + 1, by + 1, bx + W - 2, by + Hh - 2), fill=S['base'])
    _brushed(img, bx + 3, by + 3, bx + W - 4, by + Hh - 4, seed)
    _hline(img, bx + 1, bx + W - 2, by + 1, S['l2'])
    _hline(img, bx + 1, bx + W - 3, by + 2, S['l1'])
    _vline(img, bx + 1, by + 1, by + Hh - 2, S['l2'])
    _vline(img, bx + 2, by + 1, by + Hh - 3, S['l1'])
    _hline(img, bx + 2, bx + W - 2, by + Hh - 2, S['d3'])
    _vline(img, bx + W - 2, by + 2, by + Hh - 2, S['d3'])
    _vline(img, bx + W - 3, by + 3, by + Hh - 3, S['d2'])
    for cx in (0, W - 1):                                   # only the top corners are window corners (vanilla
        for ddx in range(2):                                # cuts them too); the bottom joins the vanilla panel
            for ddy in range(2 - ddx):
                _px(img, bx + abs(cx - ddx), by + ddy, (0, 0, 0, 0))
    for rx, ry in ((bx + 4, by + 4), (bx + W - 5, by + 4)):
        rivet(img, rx, ry)


def body(img, ox, oy, W=176, Hh=222, depth=4, feet=True, bottom_depth=None):
    """Volume: the safe as a box - a dark side face right of the window and a bottom face under it (oblique, light
    from the top-left), plus two feet under the bottom face. Parts that stick out of the frame add depth; they all
    start at the body so nothing floats. Needs canvas right >= depth and bottom >= depth + 3."""
    S = STEEL
    for k in range(depth):                                  # right face: columns W+k, shifted down by k+1
        x = ox + W + k
        for y in range(oy + k + 2, oy + Hh + k):
            c = S['out'] if k == depth - 1 or y == oy + k + 2 else (S['d1'] if k == 0 else S['d2'])
            if k < depth - 1 and (y - oy) % 37 == 18:
                c = S['m1']                                  # seam highlights on the side
            _px(img, x, y, c)
    bd = depth if bottom_depth is None else bottom_depth
    for k in range(bd):                                     # bottom face: rows Hh+k, shifted right by k+1
        y = oy + Hh + k
        for x in range(ox + k + 2, ox + W + k + 1):
            c = S['out'] if k == bd - 1 or x == ox + k + 2 else (S['d2'] if k == 0 else S['d3'])
            _px(img, x, y, c)
    if feet:
        for fx in (ox + 10, ox + W - 26):                   # feet under the bottom face
            for y in range(oy + Hh + bd, oy + Hh + bd + 3):
                for x in range(fx, fx + 16):
                    c = S['out'] if x in (fx, fx + 15) or y == oy + Hh + bd + 2 else S['m1'] if y == oy + Hh + bd else S['d1']
                    _px(img, x, y, c)


def slot(img, x0, y0):
    """18x18 steel slot well (slot_style 'steel'): dark recess, lit bottom/right lip, a faint inner rim."""
    S = STEEL
    d = ImageDraw.Draw(img)
    d.rectangle((x0, y0, x0 + 17, y0 + 17), fill=H('#262a34'))
    _hline(img, x0, x0 + 16, y0, S['out'])
    _vline(img, x0, y0, y0 + 16, S['out'])
    _hline(img, x0 + 1, x0 + 16, y0 + 1, S['d3'])
    _vline(img, x0 + 1, y0 + 1, y0 + 16, S['d3'])
    _hline(img, x0 + 1, x0 + 17, y0 + 17, S['l1'])
    _vline(img, x0 + 17, y0 + 1, y0 + 17, S['l1'])
    _px(img, x0 + 16, y0 + 16, H('#30353f'))


# ------------------------------------------------------------------ door and hardware

def door(img, x0, y0, x1, y1, seed=5):
    """Raised door plate: heavy bevel, brushed face, engraved groove 6 px in, rivets on the groove corners."""
    S = STEEL
    d = ImageDraw.Draw(img)
    d.rectangle((x0 + 2, y1 + 1, x1 + 2, y1 + 2), fill=S['d3'])             # shadow on the frame
    _vline(img, x1 + 1, y0 + 2, y1 + 2, S['d3'])
    d.rectangle((x0, y0, x1, y1), fill=S['out'])
    d.rectangle((x0 + 1, y0 + 1, x1 - 1, y1 - 1), fill=S['m1'])
    _brushed(img, x0 + 3, y0 + 3, x1 - 3, y1 - 3, seed, light=S['m2'], dark=S['base'])
    for i, c in enumerate((S['hi'], S['l2'], S['l1'])):
        _hline(img, x0 + 1 + i, x1 - 1 - i, y0 + 1 + i, c)
        _vline(img, x0 + 1 + i, y0 + 1 + i, y1 - 1 - i, c)
    for i, c in enumerate((S['d3'], S['d2'], S['d1'])):
        _hline(img, x0 + 1 + i, x1 - 1 - i, y1 - 1 - i, c)
        _vline(img, x1 - 1 - i, y0 + 1 + i, y1 - 1 - i, c)
    g = 6                                                                   # engraved groove
    _hline(img, x0 + g, x1 - g, y0 + g, S['d2'])
    _vline(img, x0 + g, y0 + g, y1 - g, S['d2'])
    _hline(img, x0 + g + 1, x1 - g + 1, y1 - g + 1, S['l1'])
    _vline(img, x1 - g + 1, y0 + g + 1, y1 - g + 1, S['l1'])
    _hline(img, x0 + g, x1 - g, y1 - g, S['d2'])
    _vline(img, x1 - g, y0 + g, y1 - g, S['d2'])
    _hline(img, x0 + g + 1, x1 - g - 1, y0 + g + 1, S['l1'])
    _vline(img, x0 + g + 1, y0 + g + 1, y1 - g - 1, S['l1'])
    for rx in (x0 + 3, x1 - 3):
        for ry in (y0 + 3, y1 - 3):
            rivet(img, rx, ry)


def hinge(img, x, y, h=26, leaf=12):
    """Hinge on the door's left edge: a leaf plate screwed to the door (x+3..x+3+leaf), then the knuckle
    (x..x+6) drawn over the leaf's edge - attached, not floating. leaf=3 keeps it on the window frame (storage
    screens, where slots start at x 7). (x, y) = knuckle top-left."""
    S = STEEL
    d = ImageDraw.Draw(img)
    lx1 = x + 3 + leaf
    d.rectangle((x + 4, y + 3, lx1 + 1, y + h - 2), fill=S['d3'])           # leaf shadow
    d.rectangle((x + 3, y + 2, lx1, y + h - 3), fill=S['out'])
    d.rectangle((x + 4, y + 3, lx1 - 1, y + h - 4), fill=S['m2'])
    _hline(img, x + 4, lx1 - 1, y + 3, S['l2'])
    _hline(img, x + 4, lx1 - 1, y + h - 4, S['d1'])
    _vline(img, lx1 - 1, y + 4, y + h - 4, S['d1'])
    if leaf >= 8:
        for sy in (y + 7, y + h - 8):
            rivet(img, lx1 - 4, sy)
    cols = (S['out'], S['l1'], S['hi'], S['l2'], S['m1'], S['d1'], S['out'])  # round knuckle, lit left
    for i, c in enumerate(cols):
        _vline(img, x + i, y + 1, y + h - 2, c)
    for i in range(1, 6):
        _px(img, x + i, y, S['out'])
        _px(img, x + i, y + h - 1, S['out'])
    for sy in range(y + 6, y + h - 3, 7):                                   # knuckle joints
        _hline(img, x + 1, x + 5, sy, S['d2'])
        _hline(img, x + 1, x + 5, sy + 1, S['l1'])


def bolts(img, x, ys, length=10):
    """Locking bolts sticking out of the safe's right side: a dark slot in the frame where each bolt exits
    (x .. x+2), then a round steel bar out to x+length with a lit top, a dark underside, a rounded end and a
    shadow under it - they come out of the body, they are not stuck on."""
    S = STEEL
    rows = (S['out'], S['hi'], S['l2'], S['l1'], S['m1'], S['d2'], S['out'])
    for y in ys:
        d = ImageDraw.Draw(img)
        d.rectangle((x - 1, y - 1, x + 2, y + 7), fill=S['out'])              # slot in the frame
        d.rectangle((x, y, x + 2, y + 6), fill=S['d3'])
        for i in range(length + 1):
            xx = x + i
            end = i >= length - 1
            for k, c in enumerate(rows):
                if end and k in (0, 6):
                    continue                                                 # rounded end
                _px(img, xx, y + k, S['out'] if (i == length and 0 < k < 6) else c)
            if i >= 2:
                _px(img, xx + 1, y + 7, S['d3'])                             # shadow under the bar
        _vline(img, x + 3, y + 1, y + 5, S['m2'])                            # bar meets the slot


def bolt_receivers(img, x, ys):
    """Rectangular bolt slots cut into the frame (bolts retracted)."""
    S = STEEL
    for y in ys:                                          # 5x9 slots cut into the frame (x .. x+4)
        d = ImageDraw.Draw(img)
        d.rectangle((x, y, x + 4, y + 8), fill=S['out'])
        d.rectangle((x + 1, y + 1, x + 3, y + 7), fill=S['d3'])
        _hline(img, x + 1, x + 4, y + 8, S['l1'])
        _vline(img, x + 4, y + 1, y + 8, S['l1'])


def nameplate(img, cx, y, text, w=None):
    """Brass plate with engraved letters (dark cut, light lower-right edge) and a screw on each end."""
    B = BRASS
    tw, th = text_size(text)
    w = w or tw + 18
    x0, x1 = cx - w // 2, cx - w // 2 + w - 1
    d = ImageDraw.Draw(img)
    d.rectangle((x0 + 1, y + 12, x1 + 1, y + 12), fill=STEEL['d3'])
    d.rectangle((x0, y, x1, y + 11), fill=B['out'])
    d.rectangle((x0 + 1, y + 1, x1 - 1, y + 10), fill=B['base'])
    _hline(img, x0 + 1, x1 - 1, y + 1, B['hi'])
    _hline(img, x0 + 1, x1 - 1, y + 2, B['l1'])
    _hline(img, x0 + 1, x1 - 1, y + 10, B['d1'])
    _vline(img, x1 - 1, y + 2, y + 10, B['d1'])
    for sx in (x0 + 3, x1 - 3):
        _px(img, sx, y + 5, B['d2'])
        _px(img, sx, y + 6, B['hi'])
    tx = cx - tw // 2
    letters(img, tx + 1, y + 3, text, B['hi'], B['hi'])      # light edge of the engraving
    letters(img, tx, y + 2, text, B['d2'], B['d2'])
    return x0, x1


def small_plate(img, cx, y, text):
    """Brass label plate with thin letters, 1-2 lines (instructions)."""
    B = BRASS
    tw = text_width(text, spacing=1)
    nl = text.count('\n') + 1
    w, h = tw + 8, nl * 9 + 4
    if w > 50:                                  # a 3-slot side zone is 54 px: keep 2 px air to the neighbours
        print(f'warning: plate "{text}" is {w} px wide - more than a 3-slot zone takes; use shorter lines',
              file=__import__('sys').stderr)
    x0 = cx - w // 2
    d = ImageDraw.Draw(img)
    d.rectangle((x0 + 1, y + 1, x0 + w, y + h), fill=STEEL['d3'])
    d.rectangle((x0, y, x0 + w - 1, y + h - 1), fill=B['out'])
    d.rectangle((x0 + 1, y + 1, x0 + w - 2, y + h - 2), fill=B['base'])
    _hline(img, x0 + 1, x0 + w - 2, y + 1, B['hi'])
    _hline(img, x0 + 1, x0 + w - 2, y + h - 2, B['d1'])
    draw_text(img, x0 + 4, y + 3, text, B['d2'], spacing=1, align='center')


def recess(img, x0, y0, x1, y1, fill=None):
    """Sunken panel: dark top/left, light bottom/right (inverse bevel)."""
    S = STEEL
    d = ImageDraw.Draw(img)
    d.rectangle((x0, y0, x1, y1), fill=fill or S['d1'])
    _hline(img, x0, x1, y0, S['out'])
    _vline(img, x0, y0, y1, S['out'])
    _hline(img, x0 + 1, x1, y0 + 1, S['d3'])
    _vline(img, x0 + 1, y0 + 1, y1, S['d3'])
    _hline(img, x0, x1, y1, S['l2'])
    _vline(img, x1, y0, y1, S['l2'])


def socket(img, cx, cy, r=5):
    """Unlit lamp socket (the 'lit' state is an item - lamp_icon - placed in the same slot)."""
    for y in range(cy - r - 1, cy + r + 2):
        for x in range(cx - r - 1, cx + r + 2):
            dd = math.hypot(x - cx, y - cy)
            if dd <= r - 1.5:
                c = LCD['glass'] if (x - cx) + (y - cy) > -3 else LCD['ring']
            elif dd <= r:
                c = STEEL['l1'] if (x - cx) + (y - cy) > 0 else STEEL['out']
            elif dd <= r + 0.9:
                c = STEEL['d3']
            else:
                continue
            _px(img, x, y, c)


def lamp_icon(color='green'):
    """16x16 lit lamp for a slot over a socket: glowing glass in a steel ring, white glint top-left."""
    glow = {'green': ('#1f9e4c', '#2bd46a', '#7af0a0', '#e0fff0'),
            'red':   ('#9e1f28', '#e0343c', '#f58088', '#fff0f0'),
            'amber': ('#a8661a', '#f0a030', '#f8d070', '#fff8e0')}[color]
    g = [H(c) for c in glow]
    im = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    cx, cy, r = 7.5, 7.5, 5
    for y in range(16):
        for x in range(16):
            dd = math.hypot(x - cx, y - cy)
            if dd <= r - 1.2:
                t = (x - cx) + (y - cy)
                c = g[2] if t < -2 else g[1] if t < 3 else g[0]
            elif dd <= r + 0.4:
                c = STEEL['l1'] if (x - cx) + (y - cy) > 0 else STEEL['out']
            else:
                continue
            im.putpixel((x, y), c)
    im.putpixel((6, 5), g[3])
    im.putpixel((5, 6), g[3])
    return im


def display(img, ox, oy, c0, r, n, lamps=(), lock_slot=None):
    """Code display over a row of n slots: sunken LCD glass with scan lines, a socket centred in every slot of
    `lamps` (slot columns), a small padlock in `lock_slot`."""
    x0, y0 = ox + 7 + 18 * c0 - 2, oy + 17 + 18 * r - 1
    x1, y1 = ox + 7 + 18 * (c0 + n) + 1, oy + 17 + 18 * (r + 1)
    recess(img, x0, y0, x1, y1, LCD['bg'])
    for y in range(y0 + 3, y1 - 1, 2):
        _hline(img, x0 + 2, x1 - 2, y, LCD['line'])
    for c in lamps:
        socket(img, ox + 8 + 18 * c + 7, oy + 18 + 18 * r + 7)
    if lock_slot is not None:
        padlock(img, ox + 8 + 18 * lock_slot, oy + 18 + 18 * r, LCD['glow'])


def padlock(img, x, y, color):
    """12x12 padlock glyph in a 16x16 cell (LCD green)."""
    c = color
    dk = LCD['ring']
    for yy in range(3, 8):
        _px(img, x + 5, y + yy, c)
        _px(img, x + 10, y + yy, c)
    _hline(img, x + 6, x + 9, y + 2, c)
    for yy in range(7, 13):
        _hline(img, x + 4, x + 11, y + yy, c)
    _px(img, x + 7, y + 9, dk)
    _px(img, x + 8, y + 9, dk)
    _px(img, x + 7, y + 10, dk)
    _px(img, x + 8, y + 10, dk)


def key(img, x, y, label='', color='steel', glyph=None):
    """16x16 keypad key in a slot's item area (x, y): outline, light top line, lighter sides, 2 px lip, shadow,
    a two-tone digit or a 12x7 glyph (ICON_SHAPES: close / ok / back / next)."""
    K = KEY[color]
    saved = _keep(img, [(x, y), (x + 15, y), (x, y + 15), (x + 15, y + 15)])
    d = ImageDraw.Draw(img)
    d.rectangle((x + 1, y + 16, x + 16, y + 16), fill=STEEL['out'])
    _vline(img, x + 16, y + 1, y + 16, STEEL['out'])
    d.rectangle((x, y, x + 15, y + 15), fill=K['out'])
    d.rectangle((x + 1, y + 1, x + 14, y + 14), fill=K['fill'])
    _hline(img, x + 1, x + 14, y + 1, K['light'])
    _vline(img, x + 1, y + 2, y + 11, K['side'])
    _vline(img, x + 14, y + 2, y + 11, K['side'])
    _hline(img, x + 1, x + 14, y + 12, K['lip'])
    _hline(img, x + 1, x + 14, y + 13, K['lip'])
    _hline(img, x + 1, x + 14, y + 14, K['out'])
    _restore(img, saved)
    if glyph:
        rows = ICON_SHAPES[glyph]
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                if ch == '#':
                    below = j + 1 >= len(rows) or rows[j + 1][i] != '#'
                    _px(img, x + 2 + i, y + 3 + j, K['text_dk'] if below else K['text'])
    elif label:
        tw, th = text_size(label)
        letters(img, x + 8 - tw // 2, y + 3, label, K['text'], K['text_dk'])


def keypad(img, ox, oy, c0, r0, labels, colors=None, glyphs=None):
    """Keys on a block of slots, row by row; a sunken plate around them."""
    cols = 3
    rows = (len(labels) + cols - 1) // cols
    recess(img, ox + 7 + 18 * c0 - 3, oy + 17 + 18 * r0 - 3, ox + 7 + 18 * (c0 + cols) + 2,
           oy + 17 + 18 * (r0 + rows) + 2, STEEL['d2'])
    for i, lab in enumerate(labels):
        c, r = c0 + i % cols, r0 + i // cols
        key(img, ox + 8 + 18 * c, oy + 18 + 18 * r, lab, (colors or {}).get(i, 'steel'), (glyphs or {}).get(i))


def wheel(img, cx, cy, r=20, spokes=4, angle=0.0):
    """Spoked handle wheel on the door, any size: shadow on the door, rim lit top-left, spokes from a brass hub,
    brass knobs on the spoke ends. `angle` (degrees) turns it - one menu per angle fakes the turning
    (variants: 0, 30, 60). Rim, spokes, hub and knobs scale with r."""
    S, B = STEEL, BRASS
    rim_w = max(3.5, r * 0.13)
    spoke_w = 1 if r < 30 else 2
    hub_r = max(4.9, r * 0.2)
    knob_r = 1 if r < 30 else 3
    rim_in, rim_out = r - rim_w, r
    a0 = math.radians(45 + angle)
    pts = {}
    for y in range(cy - r - 3, cy + r + 4):
        for x in range(cx - r - 3, cx + r + 4):
            dd = math.hypot(x - cx, y - cy)
            if rim_in <= dd <= rim_out:
                pts[(x, y)] = 'rim'
    for k in range(spokes):
        a = a0 + k * 2 * math.pi / spokes
        for t10 in range(int(hub_r * 10) - 10, int((rim_in + 1) * 10)):
            t = t10 / 10
            for w in range(-spoke_w, spoke_w + 1):
                x = round(cx + math.cos(a) * t - math.sin(a) * w)
                y = round(cy + math.sin(a) * t + math.cos(a) * w)
                if (x, y) not in pts:
                    pts[(x, y)] = ('spoke', w)
    sh = 2 if r < 30 else 3
    for (x, y) in pts:                                       # shadow on the door first
        _px(img, x + sh, y + sh, S['d2'])
    for (x, y), kind in pts.items():
        lit = ((x - cx) + (y - cy)) / max(1, r)              # -1.4 top-left .. +1.4 bottom-right
        edge = any((x + dx, y + dy) not in pts for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        if edge:
            c = S['out']
        elif kind == 'rim':
            dd = math.hypot(x - cx, y - cy)
            band = (dd - rim_in) / max(0.1, rim_out - rim_in)   # inner .. outer: a rounded tube
            c = S['hi'] if lit < -0.8 and band < 0.6 else S['l2'] if lit < -0.1 else S['l1'] if lit < 0.6 else S['m1']
            if band > 0.75 and lit > -0.2:
                c = S['m2'] if lit < 0.6 else S['base']
        else:
            w = kind[1]
            c = S['l2'] if w < 0 else S['l1'] if w == 0 else S['m1']
            if lit > 0.5:
                c = S['m2'] if w <= 0 else S['base']
        _px(img, x, y, c)
    hr = hub_r
    for y in range(cy - int(hr) - 1, cy + int(hr) + 2):      # brass hub with a cap
        for x in range(cx - int(hr) - 1, cx + int(hr) + 2):
            dd = math.hypot(x - cx, y - cy)
            if dd <= hr:
                lit = (x - cx) + (y - cy)
                if dd > hr - 1:
                    c = B['out']
                elif dd > hr * 0.55:
                    c = B['hi'] if lit < -hr * 0.6 else B['l1'] if lit < 0 else B['base'] if lit < hr * 0.6 else B['d1']
                else:
                    c = B['l1'] if lit < -1 else B['base'] if lit < 2 else B['d1']
                _px(img, x, y, c)
    _px(img, cx, cy, B['d2'])
    _px(img, cx - 1, cy - 1, B['hi'])
    for k in range(spokes):                                  # knobs on the spoke ends, outside the rim
        a = a0 + k * 2 * math.pi / spokes
        kx, ky = cx + math.cos(a) * (r + knob_r), cy + math.sin(a) * (r + knob_r)
        for y in range(int(ky) - knob_r - 2, int(ky) + knob_r + 3):
            for x in range(int(kx) - knob_r - 2, int(kx) + knob_r + 3):
                dd = math.hypot(x - kx, y - ky)
                if dd <= knob_r + 1:
                    lit = (x - kx) + (y - ky)
                    c = B['out'] if dd > knob_r + 0.2 else B['hi'] if lit < -knob_r * 0.7 else B['l1'] if lit < 0.5 else B['base'] if lit < knob_r else B['d1']
                    _px(img, x, y, c)


def turn_arrows(img, cx, cy, r, color='brass'):
    """Two curved arrows round a wheel, both clockwise ('turn it'): top arc left -> right, bottom arc right ->
    left, 2 px brass strokes with arrowheads."""
    B = BRASS
    for a_from, a_to in ((-150, -35), (30, 145)):
        pts = []
        for k in range(0, 200):
            a = math.radians(a_from + (a_to - a_from) * k / 199)
            pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
        for (x, y) in pts:
            _px(img, round(x) + 1, round(y) + 1, STEEL['d2'])
        for (x, y) in pts:
            nx, ny = (x - cx) / r, (y - cy) / r
            _px(img, round(x), round(y), B['l1'])
            _px(img, round(x + nx), round(y + ny), B['d1'])
            _px(img, round(x - nx), round(y - ny), B['hi'])
        # arrowhead at the end, pointing along the tangent (clockwise)
        a = math.radians(a_to)
        tx, ty = -math.sin(a), math.cos(a)                    # clockwise tangent (y down)
        hx, hy = cx + math.cos(a) * r, cy + math.sin(a) * r
        nx, ny = math.cos(a), math.sin(a)
        for i in range(6):
            for j in range(-(5 - i), 6 - i):
                x = round(hx + tx * i + nx * j * 0.8)
                y = round(hy + ty * i + ny * j * 0.8)
                edge = i == 5 or abs(j) == 5 - i
                _px(img, x, y, B['out'] if edge else B['l1'] if j < 0 else B['base'])


def lamps(img, pts, lit=0, color='green'):
    """Progress lamps painted into the texture (each turn stage is its own glyph): sockets, the first `lit`
    of them glowing."""
    for i, (x, y) in enumerate(pts):
        if i < lit:
            img.alpha_composite(lamp_icon(color), (x - 8, y - 8))
        else:
            socket(img, x - 1, y - 1)


def keyhole(img, cx, cy):
    """Brass escutcheon with a keyhole."""
    B = BRASS
    for y in range(cy - 8, cy + 9):
        for x in range(cx - 6, cx + 7):
            dd = ((x - cx) / 6) ** 2 + ((y - cy) / 8.5) ** 2
            if dd <= 1:
                lit = (x - cx) + (y - cy)
                c = B['out'] if dd > 0.78 else B['hi'] if lit < -6 else B['l1'] if lit < 0 else B['base'] if lit < 6 else B['d1']
                _px(img, x, y, c)
    for y in range(cy - 4, cy - 1):
        for x in range(cx - 1, cx + 2):
            _px(img, x, y, STEEL['out'])
    for y in range(cy - 1, cy + 5):
        _px(img, cx, y, STEEL['out'])
    _px(img, cx - 1, cy + 4, STEEL['out'])
    _px(img, cx + 1, cy + 4, STEEL['out'])


def render_icon(name):
    """'lamp' / 'lamp:red' / 'lamp:amber' -> 16x16."""
    kind, _, color = name.partition(':')
    if kind == 'lamp':
        return lamp_icon(color or 'green')
    raise SystemExit(f'unknown safe icon {name}')


def open_door(img, ox, oy, x_hinge=-3, y0=4, y1=121, width=44, grow=7, thick=9, top_thick=3,
              bolt_v=(0.2, 0.5, 0.8), side='left', hinge_ys=(), hinge_h=24, grow_top=None, grow_bot=None):
    """The door swung open to the left of the window (storage screens), in perspective, with VOLUME rather
    than size: same height as the closed door, but a thick vault door.
      * inner face: quad from the hinge edge (x_hinge, y0..y1) to the free edge `width` px left, which is
        closer to the viewer so it is `grow` px taller at both ends
      * thickness: a `thick` px edge face along the free edge (lit, it faces the light) with the bolts coming
        out of its middle, and a `top_thick` px top face along the upper edge (lit from above)
      * a raised plug panel on the face (lit top / free side, dark bottom / hinge side, shadow under it),
        a brass mechanism with rods to the bolts that follow the perspective, rivets on the corners
    Draw it before the hinges so the knuckles sit on the joint.
    Needs canvas left >= width + thick + 8 - x_hinge and top >= grow + top_thick - y0 + 1."""
    if side == 'right':                                       # hinges on the right: draw the left door mirrored
        tmp = Image.new('RGBA', img.size, (0, 0, 0, 0))
        oxm = img.width - ox - 176                            # the window maps onto itself under the flip
        open_door(tmp, oxm, oy, x_hinge, y0, y1, width, grow, thick, top_thick, bolt_v, 'left', hinge_ys, hinge_h,
                  grow_top, grow_bot)
        img.alpha_composite(tmp.transpose(Image.Transpose.FLIP_LEFT_RIGHT))
        return
    S, B = STEEL, BRASS
    xh, xf = ox + x_hinge, ox + x_hinge - width
    yth, ybh = oy + y0, oy + y1
    # the free edge is closer to the viewer: taller. Seen from above (the box shows its top face) it grows
    # mostly downward - equal growth up and down makes the open door look shifted up
    gt = grow if grow_top is None else grow_top
    gb = grow if grow_bot is None else grow_bot
    ytf, ybf = oy + y0 - gt, oy + y1 + gb

    def top(u):
        return yth + (ytf - yth) * u

    def bot(u):
        return ybh + (ybf - ybh) * u

    def at(u, v):
        return xh + (xf - xh) * u, top(u) + (bot(u) - top(u)) * v

    rnd = random.Random(9)
    streak = [rnd.random() for _ in range(121)]              # brush streaks in door space (follow perspective)
    # top face (thickness seen from above), behind the face's top border
    for x in range(xf - thick + 1, xh + 1):
        u = min(1.0, (xh - x) / max(1, width))
        t = round(top(u)) if x >= xf else round(ytf + (xf - x) * 0.35)
        for k in range(1, top_thick + 1):
            c = S['out'] if k == top_thick else S['hi'] if k == 1 else S['l2']
            _px(img, x, t - k, c)
    # free-edge face (the door's thickness), lit: it faces the light
    for x in range(xf - thick, xf):
        k = xf - x                                           # 1..thick, away from the face
        t0 = round(ytf + k * 0.35)
        b0 = round(ybf - k * 0.25)
        for y in range(t0, b0 + 1):
            if k == thick or y in (t0, b0):
                c = S['out']
            elif k == 1:
                c = S['m2']                                  # the corner where edge meets face
            elif k == 2:
                c = S['hi']
            elif k >= thick - 2:
                c = S['l1']
            else:
                c = S['l2']
            if k not in (1, thick) and (y - t0) % 23 == 11:
                c = S['m2']                                  # edge seams
            _px(img, x, y, c)
    # inner face
    pl, pr, pt, pb = 0.14, 0.86, 0.08, 0.92                  # plug panel (u from hinge, v from top)
    for x in range(xf, xh + 1):
        u = (xh - x) / max(1, width)
        t, b = round(top(u)), round(bot(u))
        for y in range(t, b + 1):
            v = (y - t) / max(1, b - t)
            if x in (xf, xh) or y in (t, b):
                c = S['out']
            elif y == t + 1 or x == xf + 1:
                c = S['l2']
            elif y == b - 1 or x == xh - 1:
                c = S['d2']
            else:
                c = S['m1'] if u > 0.3 else S['base'] if u > 0.1 else S['d1']      # darker near the body
                ytp, ybp = top(u) + (bot(u) - top(u)) * pt, top(u) + (bot(u) - top(u)) * pb
                xl_p, xr_p = xh + (xf - xh) * pr, xh + (xf - xh) * pl
                if pl <= u <= pr and ytp <= y <= ybp:                              # raised plug
                    c = S['m2'] if u > 0.3 else S['m1']
                    si = round(v * 120)
                    if streak[si] < 0.1 and (round(u * 30) + si) % 7:
                        c = S['l1']
                    if y - ytp < 1 or x - xl_p < 1:
                        c = S['hi']                                                # lit top / free side
                    elif y - ytp < 2 or x - xl_p < 2:
                        c = S['l2']
                    elif ybp - y < 1 or xr_p - x < 1:
                        c = S['out']                                               # dark bottom / hinge side
                    elif ybp - y < 2 or xr_p - x < 2:
                        c = S['d1']
                elif pl <= u <= pr + 0.05 and ybp < y <= ybp + 2.5:
                    c = S['d1']                                                    # plug shadow below
                elif pr < u <= pr + 0.05 and ytp + 2 <= y <= ybp + 2.5:
                    c = S['d1']                                                    # plug shadow, hinge side
            _px(img, x, y, c)
    for hy in hinge_ys:                                       # hinge straps on the face at the hinge edge: the
        v0 = (hy + 4 - y0) / (y1 - y0)                        # same hinges as on the closed screen, seen from
        v1 = (hy + hinge_h - 5 - y0) / (y1 - y0)              # inside - they meet the knuckles on the joint
        for x in range(round(at(0.3, 0)[0]), xh + 1):
            u = (xh - x) / max(1, width)
            ya, yb = round(top(u) + (bot(u) - top(u)) * v0), round(top(u) + (bot(u) - top(u)) * v1)
            for y in range(ya, yb + 1):
                edge = y in (ya, yb) or x == round(at(0.3, 0)[0])
                c = S['out'] if edge else S['hi'] if y == ya + 1 else S['d1'] if y == yb - 1 else S['m2']
                _px(img, x, y, c)
            _px(img, x + 1, yb + 1, S['d2'])
        for uu in (0.08, 0.2):
            rx_, ry_ = at(uu, (v0 + v1) / 2)
            rivet(img, round(rx_), round(ry_))
    for uu, vv in ((0.06, 0.035), (0.94, 0.035), (0.06, 0.965), (0.94, 0.965)):   # rivets on the face corners
        rx_, ry_ = at(uu, vv)
        rivet(img, round(rx_), round(ry_))
    # rods from the mechanism to the bolts (horizontal in door space -> slanted on screen)
    gx, gy = at(0.45, 0.5)
    for v in bolt_v:
        for x in range(xf + 2, round(gx) + 1):
            u = (xh - x) / max(1, width)
            y = round(top(u) + (bot(u) - top(u)) * v)
            _px(img, x, y - 1, S['hi'])
            _px(img, x, y, S['l1'])
            _px(img, x, y + 1, S['out'])
            _px(img, x + 1, y + 2, S['d1'])                  # rod shadow on the plug
    vx = round(gx)                                           # vertical connecting rod
    for y in range(round(at(0.45, bolt_v[0])[1]), round(at(0.45, bolt_v[-1])[1]) + 1):
        _px(img, vx - 1, y, S['hi'])
        _px(img, vx, y, S['l1'])
        _px(img, vx + 1, y, S['out'])
        _px(img, vx + 2, y + 1, S['d1'])
    # brass mechanism cover with a rim, sunk disc and spindle, shadow on the plug
    rx, ry = 6.5, 8.0
    for y in range(round(gy - ry) - 1, round(gy + ry) + 3):
        for x in range(round(gx - rx) - 1, round(gx + rx) + 3):
            if ((x - 2 - gx) / rx) ** 2 + ((y - 2 - gy) / ry) ** 2 <= 1 and ((x - gx) / rx) ** 2 + ((y - gy) / ry) ** 2 > 1:
                _px(img, x, y, S['d1'])
    for y in range(round(gy - ry) - 1, round(gy + ry) + 2):
        for x in range(round(gx - rx) - 1, round(gx + rx) + 2):
            dd = ((x - gx) / rx) ** 2 + ((y - gy) / ry) ** 2
            if dd <= 1:
                lit = (x - gx) + (y - gy)
                if dd > 0.82:
                    c = B['out']
                elif dd > 0.5:
                    c = B['hi'] if lit < -3 else B['l1'] if lit < 3 else B['d1']
                else:
                    c = B['d1'] if lit < -2 else B['base'] if lit < 4 else B['l1']
                _px(img, x, y, c)
    for dx, dy in ((0, -5), (-4, 0), (4, 0), (0, 5)):
        _px(img, round(gx) + dx, round(gy) + dy, B['d2'])
    for dx, dy, c in ((0, 0, STEEL['l2']), (-1, 0, STEEL['out']), (1, 0, STEEL['out']), (0, -1, STEEL['out']),
                      (0, 1, STEEL['out'])):
        _px(img, round(gx) + dx, round(gy) + dy, c)
    # bolts out of the middle of the thick edge
    x0 = xf - thick
    rows = (S['out'], S['hi'], S['l2'], S['l1'], S['m1'], S['d2'], S['out'])
    for v in bolt_v:
        by = round(ytf + (ybf - ytf) * v) - 3
        for k in range(7):                                   # slot in the edge face
            _px(img, x0 + 1, by + k, S['out'] if k in (0, 6) else S['d3'])
            _px(img, x0 + 2, by + k, S['out'] if k in (0, 6) else S['d2'])
        for i in range(0, 8):
            xx = x0 - i
            for k, c in enumerate(rows):
                if i == 7 and k in (0, 6):
                    continue
                _px(img, xx, by + k, S['out'] if (i == 7 and 0 < k < 6) else c)


# ------------------------------------------------------------------ classic safe (front view, box seen from the left)

def box3d(img, ox, oy, W=176, Hh=126, side=5, top=5, base=2):
    """The safe body as a box seen from the front-left-above: a top face above the front (lit) and a left face
    (in shadow), both receding up-left. The front itself is `case`. Needs canvas left >= side, top >= top."""
    S = STEEL
    for k in range(1, top + 1):                               # top face: row oy-k, shifted left by k
        y = oy - k
        for x in range(ox - k, ox + W - k + 1):
            c = S['out'] if k == top or x == ox + W - k else S['hi'] if k == 1 else S['l2'] if k < top - 1 else S['l1']
            _px(img, x, y, c)
    for k in range(base):                                     # dark base strip under the front: separates the
        for x in range(ox - side, ox + W):                    # safe from the vanilla inventory below
            _px(img, x, oy + Hh + k, S['d2'] if k < base - 1 else S['out'])
    for k in range(1, side + 1):                              # left face: column ox-k, shifted up by k
        x = ox - k
        for y in range(oy - k, oy + Hh - k + 1):
            c = S['out'] if k == side or y == oy + Hh - k else S['d1'] if k == 1 else S['d2']
            if 1 < k < side and (y - oy) % 31 == 15:
                c = S['base']
            _px(img, x, y, c)


def door_inset(img, x0, y0, x1, y1, seed=5):
    """A plain door set into the front: dark seam all round, slightly raised face (bevel), brushed - no groove."""
    S = STEEL
    d = ImageDraw.Draw(img)
    d.rectangle((x0 - 2, y0 - 2, x1 + 2, y1 + 2), fill=S['d3'])           # the gap round the door
    _hline(img, x0 - 2, x1 + 2, y1 + 2, S['l1'])                             # lit lower lip of the frame
    _vline(img, x1 + 2, y0 - 2, y1 + 2, S['l1'])
    d.rectangle((x0, y0, x1, y1), fill=S['out'])
    d.rectangle((x0 + 1, y0 + 1, x1 - 1, y1 - 1), fill=S['m1'])
    _brushed(img, x0 + 3, y0 + 3, x1 - 3, y1 - 3, seed, light=S['m2'], dark=S['base'], density=0.06)
    for i, c in enumerate((S['hi'], S['l2'])):
        _hline(img, x0 + 1 + i, x1 - 1 - i, y0 + 1 + i, c)
        _vline(img, x0 + 1 + i, y0 + 1 + i, y1 - 1 - i, c)
    for i, c in enumerate((S['d3'], S['d1'])):
        _hline(img, x0 + 1 + i, x1 - 1 - i, y1 - 1 - i, c)
        _vline(img, x1 - 1 - i, y0 + 1 + i, y1 - 1 - i, c)


def dial(img, cx, cy, r=13):
    """Combination dial: chrome ring, a black scale with 20 ticks, black knob with a chrome cap, index mark."""
    S = STEEL
    for y in range(cy - r - 3, cy + r + 4):                   # shadow on the door
        for x in range(cx - r - 3, cx + r + 4):
            if math.hypot(x - cx - 2, y - cy - 2) <= r and math.hypot(x - cx, y - cy) > r:
                _px(img, x, y, S['d1'])
    for y in range(cy - r - 1, cy + r + 2):
        for x in range(cx - r - 1, cx + r + 2):
            dd = math.hypot(x - cx, y - cy)
            lit = (x - cx) + (y - cy)
            if dd > r + 0.4:
                continue
            if dd > r - 0.6:
                c = S['out']
            elif dd > r - 3:                                  # chrome ring
                c = S['spec'] if lit < -r * 0.9 else S['hi'] if lit < -2 else S['l2'] if lit < r * 0.6 else S['m2']
            elif dd > r - 6:                                  # black scale
                c = H('#15171c')
            elif dd > r - 7:
                c = S['out']
            else:                                             # knob
                c = H('#24272e') if lit > -3 else H('#3a3e48')
            _px(img, x, y, c)
    for k in range(20):                                       # ticks on the scale
        a = k * math.pi / 10
        ln = 2 if k % 5 == 0 else 1
        for t in range(ln):
            rr = r - 3.5 - t
            _px(img, round(cx + math.cos(a) * rr), round(cy + math.sin(a) * rr), S['l2'] if k % 5 else S['spec'])
    for y in range(cy - 3, cy + 4):                           # chrome cap
        for x in range(cx - 3, cx + 4):
            dd = math.hypot(x - cx, y - cy)
            if dd <= 3.2:
                lit = (x - cx) + (y - cy)
                _px(img, x, y, S['out'] if dd > 2.5 else S['spec'] if lit < -1 else S['l2'] if lit < 2 else S['m2'])
    for dy, w in ((r + 2, 2), (r + 3, 1)):                    # index mark above the dial
        for dx in range(-w + 1, w):
            _px(img, cx + dx, cy - dy, BRASS['l1'] if dy == r + 2 else BRASS['out'])


def handle3(img, cx, cy, length=30, angle=0.0, spokes=3):
    """Classic safe handle: 3 tapered chrome spokes with ball ends from a big chrome hub (a cylinder seen from
    the front: rings), drop shadow on the door. `angle` (degrees) turns it - one menu per angle fakes turning."""
    S = STEEL
    pts = {}
    a0 = math.radians(angle)                                  # angle 0: right, down-left, up-left (like a real safe)
    ball_r = 4.2 if length < 26 else 5.2
    for k in range(spokes):
        a = a0 + k * 2 * math.pi / spokes
        ca, sa = math.cos(a), math.sin(a)
        for t10 in range(0, length * 10):
            t = t10 / 10
            w = 3.2 - 1.2 * t / length                        # thick tapered spoke
            for w10 in range(int(-w * 10), int(w * 10) + 1, 3):
                ww = w10 / 10
                x, y = round(cx + ca * t - sa * ww), round(cy + sa * t + ca * ww)
                pts.setdefault((x, y), ('spoke', ww / w))
        bx, by = cx + ca * (length + 2), cy + sa * (length + 2)   # ball end
        for y in range(int(by) - 7, int(by) + 8):
            for x in range(int(bx) - 7, int(bx) + 8):
                if math.hypot(x - bx, y - by) <= ball_r:
                    pts[(x, y)] = ('ball', (bx, by))
    hub_r = 11 if length >= 26 else 9
    for y in range(cy - hub_r - 1, cy + hub_r + 2):
        for x in range(cx - hub_r - 1, cx + hub_r + 2):
            if math.hypot(x - cx, y - cy) <= hub_r:
                pts[(x, y)] = ('hub', None)
    for (x, y) in pts:                                        # shadow
        _px(img, x + 3, y + 3, S['d2'])
    for (x, y), (kind, info) in pts.items():
        edge = any((x + dx, y + dy) not in pts for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        if edge:
            c = S['out']
        elif kind == 'ball':
            bx, by = info
            lit = (x - bx) + (y - by)
            c = S['spec'] if lit < -4 else S['hi'] if lit < -1 else S['l2'] if lit < 3 else S['m2']
        elif kind == 'hub':
            dd = math.hypot(x - cx, y - cy)
            lit = (x - cx) + (y - cy)
            if dd > hub_r - 2.5:                              # outer ring
                c = S['spec'] if lit < -hub_r else S['hi'] if lit < 0 else S['l1'] if lit < hub_r * 0.8 else S['m1']
            elif dd > hub_r - 4:
                c = S['m1']                                   # groove
            else:                                             # cap
                c = S['spec'] if lit < -3 else S['hi'] if lit < 0 else S['l2'] if lit < 3 else S['l1']
        else:
            side = info                                       # -1 .. 1 across the spoke
            c = S['spec'] if side < -0.3 else S['hi'] if side < 0.2 else S['l1'] if side < 0.7 else S['m2']
        _px(img, x, y, c)


def hinge_block(img, x_edge, y, h=24, side='right', leaf=True, leaf_w=6, door_strap=0):
    """Heavy hinge of a classic safe: a leaf on the door edge, a knuckle with a pin sticking out past the body's
    side (x_edge = the body's outer edge), caps at both ends. side='right' for the photo look."""
    S = STEEL
    s = 1 if side == 'right' else -1
    leaf0, leaf1 = x_edge - s * leaf_w, x_edge - s * 1            # leaf on the frame (same open and closed)
    d = ImageDraw.Draw(img)
    lx0, lx1 = min(leaf0, leaf1), max(leaf0, leaf1)
    if not leaf:                                                  # open door: the leaf is on the door, only
        lx0 = lx1 = None                                          # the knuckles stay on the body edge
    if lx0 is None:
        pass
    else:
        d.rectangle((lx0 + 1, y + 1 + 2, lx1 + 1, y + h - 4 + 2), fill=S['d2'])   # leaf shadow
        d.rectangle((lx0, y + 2, lx1, y + h - 3), fill=S['out'])
        d.rectangle((lx0 + 1, y + 3, lx1 - 1, y + h - 4), fill=S['m2'])
        _hline(img, lx0 + 1, lx1 - 1, y + 3, S['hi'])
        _hline(img, lx0 + 1, lx1 - 1, y + h - 4, S['d1'])
        for ry in (y + 7, y + h - 8):
            rivet(img, (lx0 + lx1) // 2, ry)
    if door_strap:                                                # closed door: a strap from the knuckle across
        sx0, sx1 = (x_edge - door_strap, x_edge - 1) if side == 'right' else (x_edge, x_edge + door_strap - 1)
        d.rectangle((sx0 + 1, y + 5, sx1 + 1, y + h - 4), fill=S['d2'])          # the seam onto the door,
        d.rectangle((sx0, y + 4, sx1, y + h - 5), fill=S['out'])                 # screwed to the door - the
        d.rectangle((sx0 + 1, y + 5, sx1 - 1, y + h - 6), fill=S['m2'])          # door visibly hangs on it
        _hline(img, sx0 + 1, sx1 - 1, y + 5, S['hi'])
        _hline(img, sx0 + 1, sx1 - 1, y + h - 6, S['d1'])
        end = sx0 if side == 'right' else sx1                     # rounded free end
        for yy in (y + 4, y + h - 5):
            _px(img, end, yy, img.getpixel((end - s, yy)) if False else S['d2'])
        for k, sx in enumerate((sx0 + 3, sx0 + 8) if side == 'right' else (sx1 - 3, sx1 - 8)):
            rivet(img, sx, y + h // 2 - (2 if k else -2) - 1 + 1)
    kx0 = x_edge if side == 'right' else x_edge - 7               # knuckle: a vertical cylinder past the edge
    cols = (S['out'], S['hi'], S['spec'], S['l2'], S['l1'], S['m1'], S['d1'], S['out'])
    for i, c in enumerate(cols):
        _vline(img, kx0 + i, y + 1, y + h - 2, c)
    for i in range(1, 7):
        _px(img, kx0 + i, y, S['out'])
        _px(img, kx0 + i, y + h - 1, S['out'])
    for py in (y - 2, y - 1, y + h, y + h + 1):                    # pin ends
        for i in (3, 4):
            _px(img, kx0 + i, py, S['l2'] if i == 3 else S['m1'])
    _hline(img, kx0 + 1, kx0 + 6, y + h // 2, S['d2'])            # split between the two knuckle halves
    _hline(img, kx0 + 1, kx0 + 6, y + h // 2 + 1, S['l1'])


def feet(img, pts, w=12, h=3):
    """Small dark feet under the body."""
    S = STEEL
    for (x, y) in pts:
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                c = S['out'] if xx in (x, x + w - 1) or yy == y + h - 1 else H('#1c1e24') if yy > y else S['d1']
                _px(img, xx, yy, c)
