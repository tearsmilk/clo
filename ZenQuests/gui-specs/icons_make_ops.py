"""Иконки меню ZenQuests, нарисованные инструментами Aseprite (aseprite_draw.py из скилла minecraft-nexo-gui):
16x16, объект ~14x14, свет сверху-слева, 5-тоновые рампы (shading.ramp5), контур — Outline тёмным тоном рампы.
    python3 make_ops.py OUT_DIR   -> OUT_DIR/<name>.json (операции) — дальше aseprite_draw.py на каждый."""
import json, os, sys
sys.path.insert(0, os.path.expanduser('~/.claude/skills/minecraft-nexo-gui/scripts'))
import shading

OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
def ramp(c): return ['#%02x%02x%02x' % tuple(t[:3]) for t in shading.ramp5(c)]   # [0 контур, 1 тень, 2 тёмный, 3 база, 4 светлый, 5 блик]
GOLD, GREEN, RED, WOOD, ORANGE, PAPER, PURPLE, STEEL, BLUE, LEAF = (ramp(c) for c in
    ('#f2c94c', '#5fb43a', '#e04848', '#b07a42', '#e07b24', '#ead4aa', '#a35bd1', '#9aa1a8', '#4aa3e0', '#c9561a'))
WHITE = '#ffffff'

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
    def outline(self, c): self.ops.append({"op": "outline", "c": c, "place": "outside"})
    def merge(self): self.ops.append({"op": "merge"})
    def save(self, name):
        json.dump({"w": 16, "h": 16, "ops": self.ops}, open(f'{OUT}/{name}.json', 'w'))

def sun():
    o = Ops(); o.layer('rays')
    for a, b in (([7, 0], [7, 2]), ([7, 13], [7, 15]), ([0, 7], [2, 7]), ([13, 7], [15, 7]),
                 ([2, 2], [3, 3]), ([12, 2], [11, 3]), ([2, 12], [3, 11]), ([12, 12], [11, 11])):
        o.line(GOLD[4], a, b)
    o.outline(ORANGE[2])
    o.layer('disc'); o.ell(GOLD[3], 3, 3, 11, 11); o.ell(GOLD[4], 3, 3, 9, 9); o.ell(GOLD[5], 4, 4, 6, 6)
    o.curve(GOLD[2], [5, 11], [8, 12], [11, 10], [11, 7]); o.outline(ORANGE[1]); o.save('daily')

def calendar():
    o = Ops(); o.layer('body'); o.rect(PAPER[4], 1, 3, 14, 13); o.rect(PAPER[5], 2, 6, 7, 9)
    o.rect(PAPER[2], 13, 4, 13, 12); o.rect(PAPER[2], 2, 13, 13, 13)
    o.rect(RED[3], 1, 3, 14, 5); o.line(RED[4], [2, 3], [13, 3]); o.line(RED[2], [2, 5], [13, 5])
    for y in (8, 11):
        for x in (3, 6, 9, 12): o.px(PAPER[2], [x, y])
    o.rect(RED[3], 8, 10, 9, 11); o.px(RED[4], [8, 10])
    o.outline(PAPER[0])
    o.layer('rings')
    for x in (4, 10): o.rect(STEEL[3], x, 1, x + 1, 4); o.px(STEEL[5], [x, 1]); o.px(STEEL[1], [x + 1, 4])
    o.outline(STEEL[0]); o.save('weekly')

def leaf():
    o = Ops(); o.layer('leaf')
    o.shape(ORANGE[3], [8, 1], [12, 4], [14, 8], [12, 12], [8, 14], [4, 12], [2, 8], [4, 4])
    o.shape(ORANGE[4], [8, 2], [8, 13], [4, 11], [3, 8], [5, 4])            # левая, освещённая половина
    o.shape(ORANGE[2], [9, 6], [13, 8], [11, 12], [9, 13])                  # правая, в тени
    o.px(ORANGE[5], [6, 4], [5, 5], [6, 5])
    o.line(ORANGE[1], [8, 2], [8, 13])                                       # центральная жилка
    o.pen(ORANGE[1], [8, 5], [5, 7]); o.pen(ORANGE[1], [8, 8], [5, 10]); o.pen(ORANGE[1], [8, 6], [11, 8]); o.pen(ORANGE[1], [8, 9], [11, 11])
    o.outline(LEAF[0])
    o.layer('stem'); o.pen(WOOD[2], [8, 13], [8, 14], [9, 15]); o.px(WOOD[4], [8, 14]); o.outline(WOOD[0]); o.save('seasonal')

def book():
    o = Ops(); o.layer('pages'); o.rect(PAPER[4], 3, 3, 14, 13); o.rect(PAPER[2], 3, 12, 14, 13)
    for y in (4, 6, 8, 10): o.line(PAPER[3], [13, y], [14, y])
    o.outline(PAPER[0])
    o.layer('cover'); o.rect(PURPLE[3], 1, 1, 12, 13); o.rect(PURPLE[4], 2, 2, 11, 3); o.rect(PURPLE[2], 1, 11, 12, 13)
    o.rect(PURPLE[1], 1, 1, 2, 13); o.rect(GOLD[3], 5, 5, 8, 8); o.px(GOLD[5], [5, 5], [6, 5]); o.px(GOLD[2], [8, 8], [7, 8])
    o.line(GOLD[2], [3, 1], [3, 13]); o.outline(PURPLE[0]); o.save('story')

def hoe(name, M, sparkle=False):
    o = Ops(); o.layer('handle')
    o.shape(WOOD[3], [1, 13], [2, 12], [10, 4], [11, 5], [3, 13], [2, 14])     # черенок 2 px по диагонали
    o.line(WOOD[4], [1, 12], [10, 3]); o.line(WOOD[1], [3, 14], [11, 6]); o.outline(WOOD[0])
    o.layer('head')
    o.shape(M[3], [6, 1], [14, 1], [14, 4], [12, 4], [14, 9], [11, 10], [9, 4], [6, 4])   # перекладина + лезвие вниз
    o.line(M[4], [7, 1], [13, 1]); o.line(M[5], [8, 1], [11, 1]); o.px(M[5], [7, 2])
    o.line(M[2], [7, 4], [9, 4]); o.pen(M[2], [12, 5], [13, 8]); o.pen(M[1], [11, 9], [13, 9])
    o.outline(M[0])
    if sparkle:
        o.layer('sparkle')
        for cx, cy in ((3, 4), (14, 12)):
            o.px(GOLD[5], [cx, cy]); o.px(GOLD[4], [cx - 1, cy], [cx + 1, cy], [cx, cy - 1], [cx, cy + 1])
    o.save(name)

def lock(name, M):
    o = Ops(); o.layer('shackle'); o.ell(STEEL[3], 4, 1, 11, 10, fill=False); o.ell(STEEL[4], 4, 1, 10, 9, fill=False)
    o.outline(STEEL[0])
    o.layer('body'); o.rect(M[3], 2, 6, 13, 14); o.rect(M[4], 3, 7, 7, 9); o.px(M[5], [3, 7]); o.rect(M[2], 2, 12, 13, 14)
    o.rect(M[2], 12, 7, 13, 14); o.rect(M[0], 7, 9, 8, 11); o.px(M[0], [7, 12])
    o.outline(M[0]); o.save(name)

def check_circle():
    o = Ops(); o.layer('disc'); o.ell(GREEN[3], 1, 1, 14, 14); o.ell(GREEN[4], 2, 2, 10, 10); o.ell(GREEN[5], 3, 3, 5, 5)
    o.curve(GREEN[2], [3, 12], [7, 15], [13, 12], [14, 7]); o.outline(GREEN[0])
    o.layer('check'); o.pen(WHITE, [4, 8], [6, 10], [11, 5]); o.pen(WHITE, [4, 7], [6, 9], [11, 4]); o.outline(GREEN[1]); o.save('claimed')

def page_check():
    o = Ops(); o.layer('page'); o.rect(PAPER[4], 2, 1, 11, 14); o.shape(PAPER[2], [9, 1], [12, 4], [9, 4])
    o.rect(PAPER[5], 3, 2, 8, 4); o.rect(PAPER[3], 3, 13, 11, 14)
    for y in (6, 8, 10): o.line(PAPER[2], [4, y], [9, y])
    o.outline(PAPER[0])
    o.layer('check'); o.ell(GREEN[3], 7, 8, 14, 15); o.pen(WHITE, [9, 12], [10, 13], [13, 10]); o.outline(GREEN[0]); o.save('step_done')

def barrier():
    o = Ops(); o.layer('disc'); o.ell(RED[3], 1, 1, 14, 14); o.ell(RED[4], 2, 2, 9, 9); o.px(RED[5], [3, 3], [4, 3])
    o.curve(RED[2], [3, 12], [7, 15], [13, 12], [14, 7]); o.outline(RED[0])
    o.layer('bar'); o.shape(WHITE, [3, 5], [5, 3], [12, 10], [10, 12]); o.line(PAPER[3], [4, 6], [10, 12]); o.outline(RED[1]); o.save('close')

def arrow(name, M, flip=False):
    o = Ops(); o.layer('arrow')
    pts = [[1, 6], [8, 6], [8, 2], [14, 8], [8, 14], [8, 10], [1, 10]]
    if flip: pts = [[15 - x, y] for x, y in pts]
    o.shape(M[3], *pts)
    hi = [[2, 6], [8, 6], [8, 3], [12, 7]] if not flip else [[13, 6], [7, 6], [7, 3], [3, 7]]
    o.pen(M[4], *hi)
    lo = [[2, 10], [8, 10], [8, 13], [12, 9]] if not flip else [[13, 10], [7, 10], [7, 13], [3, 9]]
    o.pen(M[2], *lo); o.px(M[5], hi[0], hi[1]); o.px(M[1], lo[2])
    o.outline(M[0]); o.save(name)

def basket():
    o = Ops(); o.layer('handle'); o.ell(WOOD[3], 4, 1, 11, 8, fill=False); o.px(WOOD[4], [5, 2], [6, 1], [7, 1]); o.outline(WOOD[0])
    o.layer('body'); o.shape(WOOD[3], [1, 6], [14, 6], [12, 14], [3, 14]); o.line(WOOD[4], [2, 6], [13, 6])
    for y in (8, 10, 12): o.line(WOOD[2], [3, y], [12, y])
    for x in (5, 8, 11): o.line(WOOD[2], [x, 7], [x, 13])
    o.px(WOOD[4], [4, 7], [7, 7], [10, 7], [4, 9], [7, 9], [10, 9]); o.rect(WOOD[1], 4, 13, 11, 13)
    o.outline(WOOD[0]); o.save('empty')

sun(); calendar(); leaf(); book(); hoe('premium_on', GOLD, True); hoe('premium_off', STEEL)
lock('locked', GOLD); lock('step_locked', STEEL); check_circle(); page_check(); barrier()
arrow('next', GOLD); arrow('prev', GOLD, True); arrow('back', WOOD, True); basket()
print('ops written:', sorted(os.listdir(OUT)))
