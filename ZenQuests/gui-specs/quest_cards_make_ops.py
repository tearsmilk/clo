"""Карточки квестов v2 — 32x32 (HD-иконки): пергамент с рваным краем и печатью по состоянию + эмблемы
с объёмом (3-4 тона, блики, контур тёмным тоном рампы). Aseprite через aseprite_draw.py."""
import json, os, sys
sys.path.insert(0, os.path.expanduser('~/.claude/skills/minecraft-nexo-gui/scripts'))
import shading

OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
def ramp(c): return ['#%02x%02x%02x' % tuple(t[:3]) for t in shading.ramp5(c)]
PAPER, GOLD, GREEN, RED, STEEL, WOOD, BLUE, ORANGE, PURPLE, PINK, GREY, BONE, SKY = (ramp(c) for c in
    ('#ead4aa', '#f2c94c', '#5fb43a', '#e04848', '#9aa1a8', '#b07a42', '#4aa3e0', '#e07b24', '#a35bd1', '#f06a9a',
     '#8b8b8b', '#f1ead6', '#8fd3ff'))
WHITE = '#ffffff'; WAX = ramp('#b3303c')

class Ops:
    def __init__(self): self.ops = []
    def layer(self, n): self.ops.append({"op": "layer", "name": n})
    def rect(self, c, x0, y0, x1, y1, fill=True): self.ops.append({"op": "rect", "c": c, "box": [x0, y0, x1, y1], "fill": fill})
    def ell(self, c, x0, y0, x1, y1, fill=True): self.ops.append({"op": "ellipse", "c": c, "box": [x0, y0, x1, y1], "fill": fill})
    def line(self, c, a, b): self.ops.append({"op": "line", "c": c, "pts": [a, b]})
    def pen(self, c, *pts): self.ops.append({"op": "pencil", "c": c, "pts": list(pts)})
    def curve(self, c, a, b, cc, d): self.ops.append({"op": "curve", "c": c, "pts": [a, b, cc, d]})
    def shape(self, c, *pts): self.ops.append({"op": "shape", "c": c, "pts": list(pts)})
    def px(self, c, *pts): self.ops.append({"op": "px", "c": c, "pts": list(pts)})
    def fill(self, c, x, y): self.ops.append({"op": "fill", "c": c, "at": [x, y]})
    def outline(self, c): self.ops.append({"op": "outline", "c": c, "place": "outside"})
    def save(self, name): json.dump({"w": 32, "h": 32, "ops": self.ops}, open(f'{OUT}/{name}.json', 'w'))

# ── пергамент: рваный контур, складка-уголок, пятна, тёмный низ; печать в правом нижнем углу ──
def card(state):
    P = GREY if state == 'locked' else PAPER
    o = Ops(); o.layer('paper')
    o.shape(P[3], [2, 3], [5, 1], [12, 2], [20, 1], [24, 3], [29, 2], [30, 8], [29, 15], [30, 22], [29, 29], [23, 30],
            [16, 29], [9, 30], [3, 29], [1, 24], [2, 17], [1, 10])
    o.shape(P[4], [3, 4], [12, 3], [23, 3], [27, 5], [27, 10], [20, 11], [10, 12], [4, 11])          # свет сверху
    o.rect(P[5], 4, 4, 14, 5)
    o.shape(P[2], [3, 24], [28, 24], [28, 28], [23, 29], [9, 29], [3, 28])                              # тень снизу
    o.px(P[2], [6, 15], [7, 15], [6, 16], [24, 19], [25, 19], [25, 20], [12, 26], [13, 26])              # пятна
    o.shape(P[2], [23, 2], [30, 2], [30, 9])                                                            # загнутый уголок
    o.shape(P[1], [25, 3], [29, 3], [29, 7]); o.px(P[0], [30, 9], [29, 9])
    for y in (16, 19, 22): o.line(P[2], [5, y], [9, y])                                                 # строчки слева под эмблемой
    o.outline(P[0])
    if state == 'ready':
        o.layer('frame'); o.shape(GOLD[3], [0, 0], [31, 0], [31, 31], [0, 31]); o.shape(GOLD[3], [1, 1], [30, 1], [30, 30], [1, 30])
        o.fill('#00000000', 15, 15)
        o.ops = o.ops[:-3] + [{"op": "rect", "c": GOLD[3], "box": [0, 0, 31, 31], "fill": False},
                              {"op": "rect", "c": GOLD[2], "box": [1, 1, 30, 30], "fill": False}]
        o.line(GOLD[5], [1, 0], [10, 0]); o.line(GOLD[5], [0, 1], [0, 10]); o.line(GOLD[1], [21, 31], [30, 31]); o.line(GOLD[1], [31, 21], [31, 30])
        for x, y in ((0, 0), (31, 0), (0, 31), (31, 31)): o.px(GOLD[4], [x, y])
        o.layer('seal'); o.ell(GOLD[3], 20, 20, 31, 31); o.ell(GOLD[4], 21, 21, 27, 27); o.ell(GOLD[2], 22, 22, 29, 29, fill=False)
        o.rect(WAX[3], 25, 22, 26, 26); o.px(WAX[3], [25, 28], [26, 28]); o.px(WAX[5], [25, 22]); o.outline(GOLD[0])     # «!»
    elif state == 'claimed':
        o.layer('seal'); o.ell(GREEN[3], 20, 20, 31, 31); o.ell(GREEN[4], 21, 21, 27, 27); o.ell(GREEN[2], 22, 22, 29, 29, fill=False)
        o.pen(WHITE, [22, 26], [25, 29], [29, 23]); o.pen(WHITE, [22, 25], [25, 28], [29, 22]); o.outline(GREEN[0])
    elif state == 'active':
        o.layer('seal'); o.ell(WAX[3], 22, 22, 30, 30); o.ell(WAX[4], 23, 23, 27, 27); o.px(WAX[5], [24, 24]); o.ell(WAX[2], 24, 24, 28, 28, fill=False)
        o.outline(WAX[0])                                                                                  # сургуч без знака
    else:
        o.layer('seal'); o.rect(STEEL[3], 21, 24, 30, 31); o.rect(STEEL[4], 22, 25, 25, 27); o.ell(STEEL[3], 23, 19, 28, 26, fill=False)
        o.ell(STEEL[4], 23, 19, 27, 25, fill=False); o.rect(STEEL[0], 25, 27, 26, 29); o.outline(STEEL[0])
    o.save(f'card_{state}')
for s in ('active', 'ready', 'claimed', 'locked'): card(s)

# ── эмблемы: объект ~20x20 в области 4..23 (справа-снизу место под печать) ──
def E(name, draw):
    o = Ops(); o.layer('e'); draw(o); o.save(f'emblem_{name}')

def handle(o, a, b, R=WOOD, w=3):
    o.layer('handle')
    (x0, y0), (x1, y1) = a, b
    o.shape(R[3], [x0, y0], [x0 + w, y0], [x1 + w, y1], [x1, y1])
    o.line(R[4], [x0 + 1, y0], [x1 + 1, y1]); o.line(R[1], [x0 + w, y0], [x1 + w, y1]); o.outline(R[0])

def pickaxe(o):
    handle(o, (3, 24), (16, 9))
    o.layer('head')
    o.shape(STEEL[3], [4, 7], [7, 4], [12, 2], [18, 2], [23, 4], [26, 7], [24, 8], [19, 6], [14, 6], [9, 7], [6, 9])   # серп-кирка
    o.shape(STEEL[4], [6, 6], [9, 4], [14, 3], [19, 3], [22, 4], [20, 5], [14, 5], [9, 5]); o.px(STEEL[5], [10, 4], [11, 4], [12, 3], [13, 3])
    o.line(STEEL[1], [7, 9], [12, 7]); o.line(STEEL[1], [17, 7], [23, 8]); o.px(STEEL[2], [4, 8], [25, 8])
    o.rect(STEEL[2], 13, 6, 16, 9); o.px(STEEL[1], [16, 9], [15, 9])
    o.outline(STEEL[0])
def block(o):
    o.shape(GREEN[3], [4, 10], [14, 5], [24, 10], [14, 15]); o.shape(GREEN[4], [8, 10], [14, 7], [20, 10], [14, 13]); o.px(GREEN[5], [12, 9], [13, 8])
    o.shape(WOOD[3], [4, 10], [14, 15], [14, 25], [4, 20]); o.shape(WOOD[2], [14, 15], [24, 10], [24, 20], [14, 25])
    o.line(WOOD[1], [6, 14], [12, 17]); o.line(WOOD[1], [6, 18], [12, 21]); o.line(WOOD[0], [16, 18], [22, 15]); o.line(WOOD[0], [16, 22], [22, 19])
    o.outline(WOOD[0])
def sword(o):
    o.shape(STEEL[3], [19, 2], [24, 2], [24, 7], [11, 20], [6, 15]); o.line(STEEL[5], [22, 3], [8, 17]); o.line(STEEL[4], [23, 4], [9, 18])
    o.line(STEEL[1], [24, 6], [11, 19]); o.outline(STEEL[0])
    o.layer('guard'); o.shape(GOLD[3], [4, 13], [8, 13], [14, 19], [14, 23], [10, 23], [4, 17]); o.px(GOLD[5], [6, 14], [7, 14]); o.outline(GOLD[0])
    o.layer('grip'); o.shape(WOOD[3], [2, 23], [7, 18], [10, 21], [5, 26]); o.line(WOOD[4], [3, 22], [7, 19]); o.ell(GOLD[3], 1, 24, 5, 28); o.px(GOLD[5], [2, 25])
    o.outline(WOOD[0])
def fish(o):
    o.ell(BLUE[3], 4, 9, 22, 21); o.shape(BLUE[3], [20, 15], [27, 8], [27, 22]); o.ell(BLUE[4], 6, 10, 16, 15); o.px(BLUE[5], [8, 11], [9, 11])
    o.ell(BLUE[2], 7, 16, 20, 20); o.curve(BLUE[1], [8, 20], [12, 22], [17, 22], [21, 19])
    o.shape(BLUE[4], [11, 9], [15, 5], [18, 9]); o.ell(WHITE, 8, 12, 11, 15); o.px(BLUE[0], [10, 13], [10, 14], [9, 14])
    o.px(BLUE[5], [9, 13]); o.line(BLUE[1], [19, 12], [19, 18]); o.outline(BLUE[0])
def craft(o):
    o.rect(WOOD[3], 3, 4, 24, 25); o.rect(WOOD[4], 4, 5, 23, 8); o.rect(WOOD[2], 4, 22, 23, 24)
    for v in (10, 17): o.line(WOOD[1], [v, 5], [v, 24]); o.line(WOOD[1], [4, v], [23, v])
    o.rect(WOOD[0], 10, 5, 10, 24); o.rect(WOOD[0], 4, 10, 23, 10); o.px(WOOD[5], [5, 5], [6, 5], [12, 5], [13, 5], [19, 5], [20, 5])
    o.outline(WOOD[0])
def furnace(o):
    o.rect(STEEL[2], 3, 3, 24, 25); o.rect(STEEL[3], 4, 4, 23, 11); o.rect(STEEL[4], 5, 5, 22, 6); o.rect(STEEL[1], 6, 14, 21, 23)
    o.shape(ORANGE[3], [7, 23], [20, 23], [19, 17], [16, 19], [14, 14], [11, 18], [8, 17]); o.shape(GOLD[4], [10, 23], [17, 23], [16, 20], [13, 17], [11, 20])
    o.px(GOLD[5], [13, 21], [14, 22]); o.line(STEEL[1], [4, 12], [23, 12]); o.outline(STEEL[0])
def apple(o):
    o.ell(RED[3], 4, 8, 24, 26); o.ell(RED[3], 3, 9, 15, 25); o.ell(RED[4], 6, 10, 15, 18); o.ell(RED[5], 8, 11, 11, 13)
    o.ell(RED[2], 9, 18, 24, 25); o.px(RED[1], [20, 24], [21, 23]); o.shape(RED[2], [12, 8], [14, 6], [16, 8])
    o.shape(WOOD[3], [14, 8], [15, 3], [17, 3], [16, 8]); o.shape(GREEN[3], [16, 7], [20, 3], [24, 5], [20, 8]); o.px(GREEN[5], [19, 5])
    o.outline(RED[0])
def ench(o):
    o.rect(PURPLE[3], 5, 3, 23, 25); o.rect(PURPLE[4], 6, 4, 22, 7); o.rect(PURPLE[2], 5, 22, 23, 25); o.rect(PURPLE[1], 5, 3, 7, 25)
    o.rect(PAPER[4], 8, 25, 23, 26); o.rect(GOLD[3], 9, 9, 19, 19, fill=False); o.rect(GOLD[2], 10, 10, 18, 18, fill=False)
    for y in (12, 14, 16): o.line(PINK[4], [11, y], [17, y]); o.px(PINK[5], [12, 12], [14, 14], [16, 16])
    o.px(SKY[4], [21, 10], [24, 14], [20, 20]); o.outline(PURPLE[0])
def heart(o):
    o.ell(PINK[3], 3, 5, 15, 17); o.ell(PINK[3], 13, 5, 25, 17); o.shape(PINK[3], [4, 13], [24, 13], [14, 25])
    o.ell(PINK[4], 5, 7, 12, 13); o.ell(PINK[5], 6, 8, 9, 10); o.shape(PINK[2], [8, 17], [21, 15], [14, 24]); o.outline(PINK[0])
def bone(o):
    o.shape(BONE[3], [8, 20], [20, 8], [24, 12], [12, 24]); o.ell(BONE[3], 4, 18, 11, 25); o.ell(BONE[3], 7, 21, 14, 28); o.ell(BONE[3], 17, 5, 24, 12); o.ell(BONE[3], 20, 8, 27, 15)
    o.line(BONE[5], [9, 19], [20, 8]); o.px(BONE[5], [6, 20], [19, 7]); o.line(BONE[1], [12, 23], [23, 12]); o.outline(BONE[0])
def boots(o):
    o.rect(WOOD[3], 5, 3, 13, 15); o.shape(WOOD[3], [5, 15], [13, 15], [24, 19], [24, 25], [5, 25]); o.rect(WOOD[4], 6, 4, 12, 7); o.rect(WOOD[2], 5, 22, 24, 25)
    o.rect(WOOD[1], 5, 25, 24, 26); o.rect(STEEL[3], 15, 19, 21, 20); o.px(STEEL[5], [16, 19]); o.px(GOLD[3], [8, 10], [8, 13]); o.outline(WOOD[0])
def clock(o):
    o.ell(GOLD[3], 3, 3, 25, 25); o.ell(GOLD[5], 5, 5, 11, 9); o.ell(GOLD[1], 10, 17, 25, 25); o.ell(PAPER[5], 6, 6, 22, 22); o.ell(PAPER[3], 12, 12, 22, 22)
    o.ell(PAPER[5], 7, 7, 21, 21)
    for a, b in (([14, 7], [14, 9]), ([14, 19], [14, 21]), ([7, 14], [9, 14]), ([19, 14], [21, 14])): o.line(PAPER[0], a, b)
    o.line(RED[3], [14, 14], [14, 9]); o.line(PAPER[0], [14, 14], [19, 14]); o.px(GOLD[2], [14, 14]); o.outline(GOLD[0])
def wheat(o):
    o.line(GREEN[2], [14, 27], [14, 12]); o.line(GREEN[2], [7, 27], [9, 16]); o.line(GREEN[2], [21, 27], [19, 16])
    o.curve(GREEN[3], [14, 20], [10, 18], [8, 15], [7, 13]); o.curve(GREEN[3], [14, 22], [18, 20], [20, 17], [21, 15])
    for cx, cy in ((14, 3), (9, 8), (19, 8)):
        for k in range(4):
            y = cy + k * 2; o.ell(GOLD[3], cx - 2, y, cx + 2, y + 3); o.px(GOLD[5], [cx - 1, y + 1]); o.px(GOLD[1], [cx + 1, y + 2])
        o.px(GOLD[4], [cx, cy - 2], [cx, cy - 1])
    o.outline(GOLD[0])
def pot(o):
    o.rect(STEEL[2], 5, 9, 23, 25); o.rect(STEEL[3], 6, 10, 22, 14); o.rect(STEEL[4], 7, 11, 12, 12); o.rect(STEEL[1], 5, 22, 23, 25)
    o.rect(STEEL[3], 3, 7, 25, 9); o.rect(STEEL[5], 4, 7, 10, 7); o.rect(STEEL[3], 2, 13, 5, 15); o.rect(STEEL[3], 23, 13, 26, 15)
    o.curve(WHITE, [10, 5], [11, 1], [8, 2], [9, -1]); o.curve(WHITE, [16, 5], [17, 1], [14, 2], [15, -1]); o.px(ORANGE[4], [12, 6], [14, 6], [16, 6])
    o.outline(STEEL[0])
def mill(o):
    o.ell(STEEL[3], 3, 3, 25, 25); o.ell(STEEL[4], 5, 5, 13, 11); o.ell(STEEL[1], 9, 15, 25, 25); o.ell(STEEL[2], 11, 11, 17, 17); o.px(STEEL[0], [14, 14])
    for a, b in (([5, 14], [23, 14]), ([14, 5], [14, 23]), ([8, 8], [20, 20]), ([20, 8], [8, 20])): o.line(STEEL[1], a, b)
    o.ell(STEEL[2], 3, 3, 25, 25, fill=False); o.outline(STEEL[0])
def sack(o):
    o.shape(WOOD[4], [8, 10], [20, 10], [25, 26], [3, 26]); o.shape(WOOD[3], [14, 10], [20, 10], [25, 26], [14, 26]); o.rect(WOOD[3], 10, 4, 18, 10)
    o.rect(WOOD[2], 10, 8, 18, 10); o.line(GOLD[3], [9, 9], [19, 9]); o.px(GOLD[5], [10, 9], [11, 9]); o.rect(WOOD[2], 4, 23, 24, 26)
    o.px(WOOD[5], [9, 13], [10, 13], [9, 14]); o.shape(PAPER[5], [11, 3], [13, 1], [16, 3], [14, 5]); o.outline(WOOD[0])
def coin(o):
    o.ell(GOLD[3], 3, 3, 25, 25); o.ell(GOLD[4], 5, 5, 15, 13); o.ell(GOLD[5], 6, 6, 10, 9); o.ell(GOLD[1], 9, 17, 25, 25)
    o.ell(GOLD[2], 7, 7, 21, 21, fill=False); o.rect(GOLD[2], 12, 10, 16, 18); o.rect(GOLD[4], 12, 10, 13, 17); o.px(GOLD[1], [16, 18], [15, 18])
    o.outline(GOLD[0])
def house(o):
    o.shape(RED[3], [2, 14], [14, 3], [26, 14]); o.shape(RED[4], [5, 13], [14, 5], [13, 13]); o.px(RED[5], [11, 7], [12, 6])
    o.rect(WOOD[4], 5, 14, 23, 26); o.rect(WOOD[3], 14, 14, 23, 26); o.rect(WOOD[1], 12, 19, 16, 26); o.rect(WOOD[2], 13, 20, 15, 26); o.px(GOLD[3], [15, 23])
    o.rect(SKY[3], 7, 17, 10, 20); o.px(SKY[5], [7, 17]); o.rect(SKY[3], 18, 17, 21, 20); o.px(SKY[5], [18, 17])
    o.rect(RED[2], 2, 13, 26, 14); o.rect(STEEL[3], 19, 5, 21, 9); o.outline(WOOD[0])
def bubble(o):
    o.ell(WHITE, 3, 3, 25, 19); o.shape(WHITE, [7, 16], [13, 18], [5, 24]); o.ell(BONE[4], 5, 12, 24, 19)
    o.ell(STEEL[2], 8, 9, 11, 12); o.ell(STEEL[2], 13, 9, 16, 12); o.ell(STEEL[2], 18, 9, 21, 12); o.px(WHITE, [8, 9], [13, 9], [18, 9])
    o.outline(STEEL[1])

for n, f in (('pickaxe', pickaxe), ('block', block), ('sword', sword), ('fish', fish), ('craft', craft), ('furnace', furnace),
             ('apple', apple), ('ench', ench), ('heart', heart), ('bone', bone), ('boots', boots), ('clock', clock),
             ('wheat', wheat), ('pot', pot), ('mill', mill), ('sack', sack), ('coin', coin), ('house', house), ('bubble', bubble)):
    E(n, f)
print('ops:', len(os.listdir(OUT)))
