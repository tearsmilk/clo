"""Иконки меню ZenQuests v3: все 15 нарисованы вручную в одной сетке 16x16 (объект ~14x14, 1 px поля),
5 тонов на материал (shading.ramp5 из скилла), контур — тёмный конец рампы, свет сверху-слева."""
import os, sys
sys.path.insert(0, os.path.expanduser('~/.claude/skills/minecraft-nexo-gui/scripts'))
import shading
from PIL import Image

OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
def ramp(c): return [t[:3] + (255,) for t in shading.ramp5(c)]   # 0 контур,1 тень,2 тёмный,3 база,4 светлый,5 блик
R = {k: ramp(v) for k, v in {
    'g': '#f2c94c', 'e': '#5fb43a', 'r': '#e04848', 'w': '#b07a42', 'o': '#e07b24', 'p': '#ead4aa',
    'u': '#a35bd1', 's': '#9aa1a8', 'b': '#4aa3e0', 'l': '#c9561a', 'k': '#6e4523'}.items()}
WHITE = (255, 255, 255, 255)

def grid(rows):
    im = Image.new('RGBA', (16, 16), (0, 0, 0, 0)); p = im.load()
    assert len(rows) == 16, len(rows)
    for y, row in enumerate(rows):
        assert len(row) == 32, (y, len(row), row)
        for x in range(16):
            t = row[2 * x:2 * x + 2]
            if t == '..': continue
            p[x, y] = WHITE if t == 'WW' else R[t[0]][int(t[1])]
    return im

I = {}
# ── солнце ──
I['daily'] = grid([
    "..............o4................",
    "....o4........o4..........o4....",
    "......o3......o3........o3......",
    "........o0o0o0o0o0o0o0o0........",
    "......o0g4g5g5g5g5g4g3o0........",
    "o4o3o0g4g5g5g5g5g5g4g3g2o0o3o4..",
    "....o0g4g5g5g5g5g4g4g3g2o0......",
    "o4o3o0g4g5g5g4g4g4g3g3g2o0o3o4..",
    "....o0g4g4g4g4g4g3g3g2g2o0......",
    "o4o3o0g3g4g4g3g3g3g2g2g1o0o3o4..",
    "......o0g3g3g3g2g2g2g1o0........",
    "........o0o0o0o0o0o0o0o0........",
    "......o3......o3........o3......",
    "....o4........o4..........o4....",
    "..............o4................",
    "................................"])
# ── календарь ──
I['weekly'] = grid([
    "................................",
    "....s0s0........s0s0............",
    "....s0s4s0......s0s4s0..........",
    "..p0p0s0s0p0p0p0s0s0p0p0p0p0p0..",
    "..p0r4r4r4r4r4r4r4r4r4r4r3r3p0..",
    "..p0r3r3r3r3r3r3r3r3r3r2r2r2p0..",
    "..p0p5p5p5p5p5p5p5p5p5p5p4p4p0..",
    "..p0p5p2p5p2p5p2p5p2p5p2p4p4p0..",
    "..p0p4p4p4p4p4p4p4p4p4p4p3p3p0..",
    "..p0p4p2p4p2p4r3r3p2p4p2p3p3p0..",
    "..p0p4p4p4p4p4r3r3p4p4p4p3p3p0..",
    "..p0p3p2p3p2p3p2p3p2p3p2p2p2p0..",
    "..p0p3p3p3p3p3p3p3p3p3p3p2p2p0..",
    "..p0p1p1p1p1p1p1p1p1p1p1p1p1p0..",
    "....p0p0p0p0p0p0p0p0p0p0p0p0....",
    "................................"])
# ── осенний лист ──
I['seasonal'] = grid([
    "......l0l0......................",
    "....l0o4o5l0..........l0l0......",
    "..l0o3o4o5o4l0......l0o4o5l0....",
    "..l0o3o4o4o4o4l0..l0o4o5o4l0....",
    "....l0o3o4o4o4o4l0o4o4o4o3l0....",
    "......l0o3o4o4o4o1o4o4o3o2l0....",
    "..l0l0l0o3o3o4o1o4o3o3o2l0......",
    "l0o4o5o4o3o3o3o1o3o3o2o2l0......",
    "l0o3o4o4o3o3o3o1o3o2o2l0........",
    "..l0o3o3o3o3o3o1o2o2o1o1l0......",
    "....l0o2o3o3o2o1o2o2o1o1o1l0....",
    "......l0o2o2o2o1o1o1o1o1o1l0....",
    "........l0l0o1o1k3l0l0l0l0......",
    "............l0l0k3k2l0..........",
    "..............l0k2k1l0..........",
    "................l0l0............"])
# ── книга (сюжет) ──
I['story'] = grid([
    "................................",
    "..u0u0u0u0u0u0u0u0u0u0u0u0......",
    "..u0u4u4u4u4u4u4u4u4u4u3u0p0....",
    "..u0u4u3u3u3u3u3u3u3u3u2u0p4p0..",
    "..u0u4u3g4g5g4u3u3u3u3u2u0p4p0..",
    "..u0u4u3g4g3g3u3u3u3u3u2u0p4p0..",
    "..u0u4u3u3u3u3u3u3u3u3u2u0p4p0..",
    "..u0u4u3u3u3u3u3u3u3u3u2u0p4p0..",
    "..u0u4u3u3u3u3u3u3u3u3u2u0p4p0..",
    "..u0u4u3u3u3u3u3u3u3u3u2u0p4p0..",
    "..u0u4u3u3u3u3u3u3u3u3u2u0p4p0..",
    "..u0u4u2u2u2u2u2u2u2u2u2u0p3p0..",
    "..u0u4u4u4u4u4u4u4u4u4u3u0p3p0..",
    "..u0u1u1u1u1u1u1u1u1u1u1u0p0....",
    "..u0u0u0u0u0u0u0u0u0u0u0u0......",
    "................................"])
# ── мотыга по диагонали (ручка слева-снизу) ──
def hoe(m):
    rows = [
        "................................",
        "..........M0M0M0M0M0M0M0........",
        "........M0M4M5M5M4M4M3M2M0......",
        "......M0M4M5M4M3M3M2M2M1M0......",
        "......M0M3M3M0M0M0M0M0M0M0......",
        "......M0M3M2M0..................",
        "........M0M2M0w0w0..............",
        "........M0M0w0w4w3w0............",
        "..........w0w4w3w2w0............",
        "........w0w4w3w2w0..............",
        "......w0w4w3w2w0................",
        "....w0w4w3w2w0..................",
        "..w0w4w3w2w0....................",
        "..w0w3w2w0......................",
        "..w0w0w0........................",
        "................................"]
    return grid([r.replace('M', m) for r in rows])
I['premium_off'] = hoe('s')
I['premium_on'] = hoe('g'); p = I['premium_on'].load()
for (x, y) in ((13, 1), (3, 10)):
    for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
        if 0 <= x + dx < 16 and 0 <= y + dy < 16 and p[x + dx, y + dy][3] == 0: p[x + dx, y + dy] = R['g'][5 if (dx, dy) == (0, 0) else 4]
# ── замок ──
def lock(m):
    rows = [
        "................................",
        "......s0s0s0s0s0s0..............",
        "....s0s4s4s3s3s3s2s0............",
        "....s0s4s0s0s0s0s2s0............",
        "....s0s3s0......s0s2s0..........",
        "....s0s3s0......s0s2s0..........",
        "..M0M0M0M0M0M0M0M0M0M0M0M0......",
        "..M0M5M4M4M4M4M4M4M4M3M3M0......",
        "..M0M4M4M4M4M0M0M4M3M3M2M0......",
        "..M0M4M4M4M0M1M1M0M3M3M2M0......",
        "..M0M4M3M3M3M0M0M3M3M2M2M0......",
        "..M0M3M3M3M3M0M0M3M2M2M2M0......",
        "..M0M3M3M3M3M3M3M2M2M2M1M0......",
        "..M0M2M2M2M2M2M2M2M1M1M1M0......",
        "..M0M0M0M0M0M0M0M0M0M0M0M0......",
        "................................"]
    return grid([r.replace('M', m) for r in rows])
I['locked'] = lock('g'); I['step_locked'] = lock('s')
# ── зелёный круг с галочкой (получено) ──
I['claimed'] = grid([
    "................................",
    "........e0e0e0e0e0e0............",
    "....e0e0e4e4e4e4e3e3e0e0........",
    "..e0e4e4e4e4e4e4e3e3e3e2e0......",
    "..e0e4e4e4e4e4e4e3e3WWe2e0......",
    "e0e4e4e4e4e4e4e3e3WWWWe2e2e0....",
    "e0e4e4e4e4e4e4e3WWWWe2e2e2e0....",
    "e0e4e4WWe4e3e3WWWWe2e2e2e1e0....",
    "e0e4e3WWWWe3WWWWe2e2e2e2e1e0....",
    "e0e3e3e3WWWWWWe2e2e2e2e1e1e0....",
    "e0e3e3e3e3WWWWe2e2e2e1e1e1e0....",
    "..e0e3e3e3e3WWe2e2e2e1e1e0......",
    "..e0e2e3e3e2e2e2e2e1e1e1e0......",
    "....e0e0e2e2e2e1e1e1e0e0........",
    "........e0e0e0e0e0e0............",
    "................................"])
# ── лист бумаги с галочкой (шаг пройден) ──
I['step_done'] = grid([
    "................................",
    "....p0p0p0p0p0p0p0p0............",
    "....p0p5p5p5p5p5p4p0p0..........",
    "....p0p5p4p2p2p4p4p0p4p0........",
    "....p0p5p4p4p4p4p4p0p0p0p0......",
    "....p0p5p2p2p2p2p4p3p3p3p0......",
    "....p0p4p4p4p4p4p4p3p3p3p0......",
    "....p0p4p2p2p2p2p3p3p3p3p0......",
    "....p0p4p4p4p4p4p3p3p3p3p0......",
    "....p0p4p2p2p2p3p3e0e0p3p0......",
    "....p0p4p4p4p4p3e0e4e4e0e0......",
    "....p0p3e0e0p3p3e0e4e3e3e0......",
    "....p0p3p3e0e4e0e4e3e3e0........",
    "....p0p2p2p2e0e4e3e3e0p0........",
    "....p0p0p0p0p0e0e0e0p0..........",
    "................................"])
# ── запрет (закрыть) ──
I['close'] = grid([
    "................................",
    "........r0r0r0r0r0r0............",
    "....r0r0r4r4r4r4r3r3r0r0........",
    "..r0r4r4WWWWr4r4r3r3r3r2r0......",
    "..r0r4r4WWWWWWr4r3r3r3r2r0......",
    "r0r4r4r4r4WWWWWWr3r3r2r2r2r0....",
    "r0r4r4r4r4r4WWWWWWr2r2r2r2r0....",
    "r0r4r4r4r4r4r3WWWWWWr2r2r1r0....",
    "r0r4r3r3r3r3r3r3WWWWWWr2r1r0....",
    "r0r3r3r3r3r3r3r3r2WWWWWWr1r0....",
    "r0r3r3r3r3r3r2r2r2r2WWWWr1r0....",
    "..r0r3r3r3r2r2r2r2r2r1WWr0......",
    "..r0r2r3r3r2r2r2r2r1r1r1r0......",
    "....r0r0r2r2r2r1r1r1r0r0........",
    "........r0r0r0r0r0r0............",
    "................................"])
# ── стрелки ──
def arrow(m):
    rows = [
        "................................",
        "................................",
        "..................M0M0..........",
        "..................M0M5M0........",
        "..................M0M5M4M0......",
        "..M0M0M0M0M0M0M0M0M0M5M4M4M0....",
        "..M0M5M5M5M5M5M5M5M5M4M4M3M3M0..",
        "..M0M5M4M4M4M4M4M4M4M4M3M3M2M2M0",
        "..M0M4M3M3M3M3M3M3M3M3M2M2M2M1M0",
        "..M0M3M2M2M2M2M2M2M2M2M2M2M1M0..",
        "..M0M0M0M0M0M0M0M0M0M2M2M1M0....",
        "..................M0M2M1M0......",
        "..................M0M1M0........",
        "..................M0M0..........",
        "................................",
        "................................"]
    return grid([r.replace('M', m) for r in rows])
I['next'] = arrow('g'); I['prev'] = arrow('g').transpose(Image.FLIP_LEFT_RIGHT); I['back'] = arrow('w').transpose(Image.FLIP_LEFT_RIGHT)
# ── пустая корзина ──
I['empty'] = grid([
    "................................",
    "..........k0k0k0k0k0............",
    "......k0k0w4w3w3w4k0k0..........",
    "....k0w4k0k0k0k0k0k0w3k0........",
    "....k0w4k0..........k0w3k0......",
    "..k0k0k0k0k0k0k0k0k0k0k0k0k0k0..",
    "..k0w5w4w4w4w4w4w4w4w3w3w3w3k0..",
    "..k0w4w2w4w2w4w2w4w2w3w2w3w2k0..",
    "..k0w4w4w3w4w3w4w3w3w3w3w2w2k0..",
    "....k0w2w3w2w3w2w3w2w3w2w2w2k0..",
    "....k0w3w3w3w3w3w3w3w2w2w2w1k0..",
    "....k0w2w2w3w2w3w2w2w2w2w1w1k0..",
    "......k0w3w3w3w3w3w2w2w2w1k0....",
    "......k0w1w1w1w1w1w1w1w1w1k0....",
    "........k0k0k0k0k0k0k0k0k0......",
    "................................"])

order = ['daily', 'weekly', 'seasonal', 'story', 'premium_on', 'premium_off', 'locked', 'step_locked', 'claimed', 'step_done', 'close', 'back', 'prev', 'next', 'empty']
sheet = Image.new('RGBA', (len(order) * 72 + 8, 80), (139, 139, 139, 255))
for i, n in enumerate(order):
    im = I[n]; im.save(f'{OUT}/{n}.png')
    sheet.alpha_composite(im.resize((64, 64), Image.NEAREST), (8 + i * 72, 8))
sheet.save(f'{OUT}/../icons3_sheet.png'); print('ok', len(order))
