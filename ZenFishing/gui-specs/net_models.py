"""Модели рыболовной сети для пака Nexo (assets/zenfishing):
  fishing_net       — предмет в руке: свёрнутая сеть на палке с пробковыми поплавками
  fishing_net_tile  — плитка 1x1 на воде: сетка с поплавками по углам (ставится ItemDisplay, FIXED, повёрнута на 90° по X)
Текстуры рисуются процедурно. Запуск: python3 net_models.py OUT_DIR  (создаёт items/, models/item/, textures/item/)"""
import sys, os, json
from PIL import Image, ImageDraw
OUT = sys.argv[1]
for d in ('items', 'models/item', 'textures/item'): os.makedirs(os.path.join(OUT, d), exist_ok=True)

ROPE, ROPE_D, CORK, CORK_D, WOOD, WOOD_D = (222, 206, 160), (170, 150, 105), (214, 142, 72), (160, 98, 44), (150, 108, 62), (104, 72, 40)

# ── текстура плитки 32x32: сетка (прозрачные ячейки), поплавки на углах ──
t = Image.new('RGBA', (32, 32), (0, 0, 0, 0)); p = t.load()
for i in range(0, 32, 4):
    for j in range(32):
        p[i, j] = (ROPE if (i + j) % 3 else ROPE_D) + (255,)
        p[j, i] = (ROPE if (i + j) % 3 else ROPE_D) + (255,)
for j in range(32): p[31, j] = ROPE_D + (255,); p[j, 31] = ROPE_D + (255,)
d = ImageDraw.Draw(t)
for (cx, cy) in ((2, 2), (29, 2), (2, 29), (29, 29)):
    d.rectangle((cx - 2, cy - 2, cx + 2, cy + 2), fill=CORK + (255,), outline=CORK_D + (255,))
t.save(os.path.join(OUT, 'textures/item/fishing_net_tile.png'))

# ── текстура предмета 32x32: кусок сети, пробка, дерево ──
h = Image.new('RGBA', (32, 32), (0, 0, 0, 0)); q = h.load()
for y in range(16):                      # 0..15 — сеть намотанная (плотная)
    for x in range(32): q[x, y] = ((ROPE if (x + y) % 2 else ROPE_D) if (x % 3 and y % 3) else ROPE_D) + (255,)
for y in range(16, 24):                  # 16..23 — пробка
    for x in range(32): q[x, y] = (CORK if (x * 5 + y) % 7 else CORK_D) + (255,)
for y in range(24, 32):                  # 24..31 — дерево
    for x in range(32): q[x, y] = (WOOD if (x + y * 2) % 5 else WOOD_D) + (255,)
h.save(os.path.join(OUT, 'textures/item/fishing_net.png'))

def face(x0, y0, x1, y1): return {'uv': [x0 / 2, y0 / 2, x1 / 2, y1 / 2], 'texture': '#0'}   # 32px → 16 юнитов
def box(fr, to, tex, rot=None):
    e = {'from': fr, 'to': to, 'faces': {f: face(*tex) for f in ('north', 'south', 'east', 'west', 'up', 'down')}}
    if rot: e['rotation'] = rot
    return e

# предмет: палка по диагонали, на ней рулон сети, два поплавка
item = {"credit": "ZenFishing net_models.py", "texture_size": [32, 32],
        "textures": {"0": "zenfishing:item/fishing_net", "particle": "zenfishing:item/fishing_net"},
        "elements": [
            box([7.0, 0.0, 7.0], [9.0, 16.0, 9.0], (0, 24, 32, 32)),                       # палка
            box([4.5, 5.0, 4.5], [11.5, 13.0, 11.5], (0, 0, 32, 16), {'origin': [8, 9, 8], 'axis': 'y', 'angle': 22.5}),  # рулон
            box([3.0, 11.0, 6.5], [6.0, 14.0, 9.5], (0, 16, 32, 24)),                     # поплавок
            box([10.0, 3.5, 6.5], [13.0, 6.5, 9.5], (0, 16, 32, 24)),                     # поплавок
        ],
        "display": {"gui": {"rotation": [30, 45, 0], "translation": [0, 0, 0], "scale": [0.8, 0.8, 0.8]},
                    "ground": {"scale": [0.5, 0.5, 0.5], "translation": [0, 2, 0]},
                    "fixed": {"rotation": [0, 180, 0], "scale": [0.9, 0.9, 0.9]},
                    "thirdperson_righthand": {"rotation": [0, 0, -35], "translation": [0, 3, 1], "scale": [0.75, 0.75, 0.75]},
                    "thirdperson_lefthand": {"rotation": [0, 0, 35], "translation": [0, 3, 1], "scale": [0.75, 0.75, 0.75]},
                    "firstperson_righthand": {"rotation": [0, -45, 25], "translation": [1, 1, 0], "scale": [0.6, 0.6, 0.6]},
                    "firstperson_lefthand": {"rotation": [0, 45, -25], "translation": [-1, 1, 0], "scale": [0.6, 0.6, 0.6]}}}
json.dump(item, open(os.path.join(OUT, 'models/item/fishing_net.json'), 'w'), separators=(',', ':'))

# плитка: тонкая пластина 16x0.4x16 с сеткой (прозрачность) — после поворота на 90° по X ItemDisplay'ем лежит в XZ.
# Модель рисуем в плоскости XY (north/south — лицо), чтобы FIXED + поворот дал горизонтальную плитку.
tile = {"credit": "ZenFishing net_models.py", "texture_size": [32, 32],
        "textures": {"0": "zenfishing:item/fishing_net_tile", "particle": "zenfishing:item/fishing_net_tile"},
        "elements": [{"from": [0, 0, 7.8], "to": [16, 16, 8.2], "faces": {
            "north": {"uv": [0, 0, 16, 16], "texture": "#0"}, "south": {"uv": [16, 0, 0, 16], "texture": "#0"},
            "up": {"uv": [0, 0, 16, 0.2], "texture": "#0"}, "down": {"uv": [0, 0, 16, 0.2], "texture": "#0"},
            "east": {"uv": [0, 0, 0.2, 16], "texture": "#0"}, "west": {"uv": [0, 0, 0.2, 16], "texture": "#0"}}},
            # поплавки чуть выше плоскости по углам
            *[box([x, y, 6.6], [x + 2.4, y + 2.4, 9.4], (0, 16, 32, 24)) for (x, y) in ((0.2, 0.2), (13.4, 0.2), (0.2, 13.4), (13.4, 13.4))]],
        "display": {"fixed": {"rotation": [0, 0, 0], "scale": [1, 1, 1]}, "gui": {"rotation": [30, 45, 0], "scale": [0.8, 0.8, 0.8]}}}
# поплавки у плитки — пробковая часть текстуры предмета; она в другом файле, поэтому вторая текстура
tile["textures"]["1"] = "zenfishing:item/fishing_net"
for e in tile["elements"][1:]:
    for f in e["faces"].values(): f["texture"] = "#1"
json.dump(tile, open(os.path.join(OUT, 'models/item/fishing_net_tile.json'), 'w'), separators=(',', ':'))

for n in ('fishing_net', 'fishing_net_tile'):
    json.dump({"model": {"type": "minecraft:model", "model": f"zenfishing:item/{n}"}}, open(os.path.join(OUT, f'items/{n}.json'), 'w'))
print('net models ok')
