"""Карточки квестов ZenQuests: 4 фона-пергамента по состоянию (active/ready/claimed/locked) + эмблемы по типу
задания (layer1 поверх карточки в модели minecraft:item/generated). Рисуется Aseprite через aseprite_draw.py.
    python3 make_ops.py OPS_DIR  -> OPS_DIR/card_<state>.json, OPS_DIR/emblem_<name>.json"""
import json, os, sys
sys.path.insert(0, os.path.expanduser('~/.claude/skills/minecraft-nexo-gui/scripts'))
import shading

OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
def ramp(c): return ['#%02x%02x%02x' % tuple(t[:3]) for t in shading.ramp5(c)]
PAPER, GOLD, GREEN, RED, STEEL, WOOD, BLUE, ORANGE, PURPLE, PINK, GREY = (ramp(c) for c in
    ('#ead4aa', '#f2c94c', '#5fb43a', '#e04848', '#9aa1a8', '#b07a42', '#4aa3e0', '#e07b24', '#a35bd1', '#f06a9a', '#8b8b8b'))
WHITE = '#ffffff'

class Ops:
    def __init__(self): self.ops = []
    def layer(self, n): self.ops.append({"op": "layer", "name": n})
    def rect(self, c, x0, y0, x1, y1, fill=True): self.ops.append({"op": "rect", "c": c, "box": [x0, y0, x1, y1], "fill": fill})
    def ell(self, c, x0, y0, x1, y1, fill=True): self.ops.append({"op": "ellipse", "c": c, "box": [x0, y0, x1, y1], "fill": fill})
    def line(self, c, a, b): self.ops.append({"op": "line", "c": c, "pts": [a, b]})
    def pen(self, c, *pts): self.ops.append({"op": "pencil", "c": c, "pts": list(pts)})
    def shape(self, c, *pts): self.ops.append({"op": "shape", "c": c, "pts": list(pts)})
    def px(self, c, *pts): self.ops.append({"op": "px", "c": c, "pts": list(pts)})
    def outline(self, c): self.ops.append({"op": "outline", "c": c, "place": "outside"})
    def save(self, name): json.dump({"w": 16, "h": 16, "ops": self.ops}, open(f'{OUT}/{name}.json', 'w'))

# ── карточки: пергамент 1..14 с загнутым уголком, состояние — рамка и бейдж в правом нижнем углу ──
def card(state):
    P = GREY if state == 'locked' else PAPER
    o = Ops(); o.layer('paper')
    o.shape(P[4], [1, 1], [11, 1], [14, 4], [14, 14], [1, 14])
    o.rect(P[5], 2, 2, 9, 3); o.rect(P[3], 2, 12, 13, 14); o.rect(P[3], 13, 5, 13, 14)
    o.shape(P[2], [11, 1], [11, 4], [14, 4])                      # загнутый уголок
    o.px(P[1], [12, 3], [13, 4])
    for y in (5, 8): o.line(P[3], [3, y], [5, y])                 # намёк на строчки слева (под эмблемой не видно)
    if state == 'active':
        o.outline(P[0])
    elif state == 'ready':
        o.outline(GOLD[2]); o.layer('frame'); o.rect(GOLD[3], 0, 0, 15, 15, fill=False); o.px(GOLD[5], [0, 0], [1, 0], [0, 1])
        o.px(GOLD[1], [15, 15], [14, 15], [15, 14]); o.layer('badge'); o.ell(GOLD[3], 10, 10, 15, 15); o.px(GOLD[5], [11, 11])
        o.px(WHITE, [12, 11], [12, 12], [12, 13]); o.px(GOLD[1], [12, 14]); o.outline(GOLD[0])     # «!»
    elif state == 'claimed':
        o.outline(P[0]); o.layer('badge'); o.ell(GREEN[3], 9, 9, 15, 15); o.px(GREEN[5], [10, 10])
        o.pen(WHITE, [10, 12], [12, 14], [14, 10]); o.outline(GREEN[0])
    elif state == 'locked':
        o.outline(P[0]); o.layer('badge'); o.rect(STEEL[3], 10, 11, 15, 15); o.ell(STEEL[3], 11, 8, 14, 12, fill=False)
        o.px(STEEL[5], [11, 12]); o.px(STEEL[0], [12, 13], [13, 13]); o.outline(STEEL[0])
    o.save(f'card_{state}')
for s in ('active', 'ready', 'claimed', 'locked'): card(s)

# ── эмблемы: объект ~10x10 в области 2..11, свет сверху-слева, контур тёмным тоном ──
def E(name, draw):
    o = Ops(); o.layer('e'); draw(o); o.save(f'emblem_{name}')

def pickaxe(o):
    o.shape(STEEL[3], [3, 2], [9, 2], [11, 4], [11, 6], [9, 5], [6, 5], [4, 8], [3, 7], [5, 4], [3, 4])
    o.line(STEEL[5], [4, 2], [8, 2]); o.px(STEEL[1], [10, 6], [9, 5])
    o.outline(STEEL[0]); o.layer('h'); o.line(WOOD[3], [8, 5], [4, 11]); o.line(WOOD[4], [8, 4], [4, 10]); o.outline(WOOD[0])
def block(o):
    o.shape(GREEN[3], [3, 4], [8, 2], [12, 4], [7, 6]); o.shape(WOOD[3], [3, 4], [7, 6], [7, 12], [3, 10]); o.shape(WOOD[2], [7, 6], [12, 4], [12, 10], [7, 12])
    o.px(GREEN[5], [6, 3], [7, 3]); o.line(WOOD[1], [8, 8], [11, 7]); o.outline(WOOD[0])
def sword(o):
    o.shape(STEEL[3], [10, 2], [12, 2], [12, 4], [6, 10], [4, 8]); o.line(STEEL[5], [11, 2], [5, 8]); o.line(STEEL[1], [12, 4], [7, 9])
    o.outline(STEEL[0]); o.layer('g'); o.line(GOLD[3], [3, 7], [7, 11]); o.line(WOOD[3], [4, 10], [2, 12]); o.px(WOOD[4], [3, 11]); o.outline(WOOD[0])
def fish(o):
    o.ell(BLUE[3], 3, 4, 11, 10); o.ell(BLUE[4], 4, 5, 8, 7); o.shape(BLUE[3], [10, 7], [13, 4], [13, 10]); o.px(BLUE[0], [5, 6])
    o.px(WHITE, [5, 6]); o.px(BLUE[0], [6, 6]); o.line(BLUE[2], [6, 9], [9, 9]); o.outline(BLUE[0])
def craft(o):
    o.rect(WOOD[3], 2, 3, 12, 12); o.rect(WOOD[4], 3, 4, 11, 5); o.rect(WOOD[2], 3, 11, 11, 12)
    for v in (6, 9): o.line(WOOD[1], [v, 4], [v, 11]); o.line(WOOD[1], [3, v], [11, v])
    o.outline(WOOD[0])
def furnace(o):
    o.rect(STEEL[2], 2, 2, 12, 12); o.rect(STEEL[3], 3, 3, 11, 6); o.rect(STEEL[1], 4, 8, 10, 11); o.rect(ORANGE[3], 5, 9, 9, 11)
    o.px(GOLD[5], [6, 9], [7, 10]); o.px(ORANGE[1], [9, 11]); o.outline(STEEL[0])
def apple(o):
    o.ell(RED[3], 3, 4, 12, 12); o.ell(RED[4], 4, 5, 8, 8); o.px(RED[5], [5, 6]); o.pen(WOOD[2], [8, 4], [8, 2]); o.px(GREEN[3], [9, 3], [10, 3])
    o.outline(RED[0])
def ench(o):
    o.rect(PURPLE[3], 3, 2, 11, 12); o.rect(PURPLE[4], 4, 3, 10, 4); o.rect(PURPLE[2], 3, 11, 11, 12); o.line(PINK[4], [5, 6], [9, 6])
    o.line(PINK[4], [5, 8], [9, 8]); o.px(PINK[5], [6, 6], [8, 8]); o.outline(PURPLE[0])
def heart(o):
    o.ell(PINK[3], 2, 3, 8, 9); o.ell(PINK[3], 7, 3, 13, 9); o.shape(PINK[3], [3, 7], [12, 7], [8, 12]); o.px(PINK[5], [4, 4], [5, 4])
    o.px(PINK[1], [8, 11]); o.outline(PINK[0])
def bone(o):
    o.line(PAPER[4], [4, 10], [10, 4]); o.line(PAPER[4], [5, 11], [11, 5]); o.ell(PAPER[4], 2, 8, 5, 11); o.ell(PAPER[4], 9, 2, 12, 5)
    o.px(PAPER[5], [3, 9], [10, 3]); o.outline(PAPER[0])
def boots(o):
    o.rect(WOOD[3], 3, 2, 7, 8); o.rect(WOOD[3], 3, 8, 11, 12); o.rect(WOOD[4], 4, 3, 6, 4); o.rect(WOOD[1], 3, 11, 11, 12)
    o.px(STEEL[4], [8, 9], [10, 9]); o.outline(WOOD[0])
def clock(o):
    o.ell(GOLD[3], 2, 2, 12, 12); o.ell(PAPER[5], 3, 3, 11, 11); o.px(PAPER[0], [7, 4], [7, 10], [4, 7], [10, 7])
    o.line(RED[3], [7, 7], [7, 5]); o.line(PAPER[0], [7, 7], [9, 7]); o.outline(GOLD[0])
def wheat(o):
    o.line(GREEN[2], [7, 12], [7, 6]); o.line(GREEN[2], [4, 12], [5, 8]); o.line(GREEN[2], [10, 12], [9, 8])
    for x, y in ((7, 2), (5, 5), (9, 5)):
        o.ell(GOLD[3], x - 1, y, x + 1, y + 3); o.px(GOLD[5], [x - 1, y + 1]); o.px(GOLD[1], [x + 1, y + 3])
    o.outline(GOLD[0])
def pot(o):
    o.rect(STEEL[2], 3, 5, 12, 12); o.rect(STEEL[3], 4, 6, 11, 7); o.rect(STEEL[1], 3, 11, 12, 12); o.rect(STEEL[3], 2, 4, 13, 5)
    o.px(ORANGE[4], [6, 2], [9, 3], [7, 1]); o.px(STEEL[4], [2, 7], [13, 7]); o.outline(STEEL[0])
def mill(o):
    o.ell(STEEL[3], 2, 2, 12, 12); o.ell(STEEL[2], 5, 5, 9, 9); o.px(STEEL[0], [7, 7]); o.line(STEEL[1], [3, 7], [11, 7]); o.line(STEEL[1], [7, 3], [7, 11])
    o.px(STEEL[5], [4, 4], [5, 3]); o.outline(STEEL[0])
def sack(o):
    o.shape(WOOD[4], [4, 5], [10, 5], [12, 12], [2, 12]); o.rect(WOOD[3], 5, 2, 9, 5); o.line(WOOD[1], [4, 5], [10, 5]); o.rect(WOOD[2], 3, 11, 11, 12)
    o.px(WOOD[5], [5, 7], [6, 7]); o.outline(WOOD[0])
def coin(o):
    o.ell(GOLD[3], 2, 2, 12, 12); o.ell(GOLD[2], 4, 4, 10, 10, fill=False); o.rect(GOLD[2], 6, 5, 8, 9); o.px(GOLD[5], [4, 3], [3, 4], [5, 3])
    o.px(GOLD[1], [11, 10], [10, 11]); o.outline(GOLD[0])
def house(o):
    o.shape(RED[3], [2, 7], [7, 2], [12, 7]); o.rect(WOOD[4], 3, 7, 11, 12); o.rect(WOOD[2], 6, 9, 8, 12); o.px(BLUE[4], [4, 8], [10, 8])
    o.px(RED[5], [6, 3], [5, 4]); o.outline(WOOD[0])
def bubble(o):
    o.ell(WHITE, 2, 2, 12, 9); o.shape(WHITE, [4, 8], [7, 8], [3, 12]); o.px(STEEL[2], [5, 5], [7, 5], [9, 5]); o.px(PAPER[3], [10, 8], [11, 7])
    o.outline(STEEL[1])

for n, f in (('pickaxe', pickaxe), ('block', block), ('sword', sword), ('fish', fish), ('craft', craft), ('furnace', furnace),
             ('apple', apple), ('ench', ench), ('heart', heart), ('bone', bone), ('boots', boots), ('clock', clock),
             ('wheat', wheat), ('pot', pot), ('mill', mill), ('sack', sack), ('coin', coin), ('house', house), ('bubble', bubble)):
    E(n, f)
print('ops:', len(os.listdir(OUT)))
