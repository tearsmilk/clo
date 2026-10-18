"""Объёмные модели рыбы из спрайтов 64x64: силуэт режется на вертикальные ломтики (колонки), каждый — параллелепипед
высотой по силуэту и толщиной по профилю рыбы (толще в середине, тоньше к хвосту). Боковые грани берут UV из спрайта,
верх/низ/торцы — узкие полоски спрайта. Результат — воксельная 3D-рыба в руке и на земле; в GUI повёрнута на 3/4."""
import sys, os, json
from PIL import Image
SRC, OUT = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
SLICES = 12
for f in sorted(os.listdir(SRC)):
    if not f.endswith('.png'): continue
    fid = f[:-4]; im = Image.open(f'{SRC}/{f}').convert('RGBA'); W, H = im.size; a = im.split()[3].load()
    cols = [[y for y in range(H) if a[x, y] > 0] for x in range(W)]
    xs = [x for x in range(W) if cols[x]]
    if not xs: continue
    x0, x1 = xs[0], xs[-1] + 1; span = x1 - x0
    # центр масс по вертикали для профиля толщины
    elements = []
    for i in range(SLICES):
        sx0 = x0 + span * i // SLICES; sx1 = x0 + span * (i + 1) // SLICES
        ys = [y for x in range(sx0, sx1) for y in cols[x]]
        if not ys: continue
        y0, y1 = min(ys), max(ys) + 1
        t = (i + 0.5) / SLICES
        depth = 1.0 + 3.2 * (1 - abs(2 * t - 1)) ** 0.8 * (min(1.0, (y1 - y0) / (H * 0.35)))   # толщина в 1/16 блока
        u = 16.0 / W
        fx0, fx1, fy0, fy1 = sx0 * u, sx1 * u, 16 - y1 * u, 16 - y0 * u   # координаты модели (y снизу вверх)
        z0, z1 = round(8 - depth / 2, 3), round(8 + depth / 2, 3)
        side = [round(sx0 * u, 3), round(y0 * u, 3), round(sx1 * u, 3), round(y1 * u, 3)]
        strip_top = [side[0], side[1], side[2], round(side[1] + 0.5, 3)]
        strip_bot = [side[0], round(side[3] - 0.5, 3), side[2], side[3]]
        el = {"from": [round(fx0, 3), round(fy0, 3), z0], "to": [round(fx1, 3), round(fy1, 3), z1],
              "faces": {"north": {"uv": [side[2], side[1], side[0], side[3]], "texture": "#0"},
                        "south": {"uv": side, "texture": "#0"},
                        "up": {"uv": strip_top, "texture": "#0"}, "down": {"uv": strip_bot, "texture": "#0"},
                        "west": {"uv": [side[0], side[1], round(side[0] + 0.5, 3), side[3]], "texture": "#0"},
                        "east": {"uv": [round(side[2] - 0.5, 3), side[1], side[2], side[3]], "texture": "#0"}}}
        elements.append(el)
    model = {"credit": "ZenFishing fish_models3d.py", "texture_size": [W, H] if W != 16 else None,
             "textures": {"0": f"zenfishing:item/fish/{fid}", "particle": f"zenfishing:item/fish/{fid}"},
             "elements": elements,
             "display": {
                 "gui": {"rotation": [20, -35, 0], "translation": [0, 0, 0], "scale": [0.85, 0.85, 0.85]},
                 "ground": {"rotation": [0, 0, 0], "translation": [0, 2, 0], "scale": [0.5, 0.5, 0.5]},
                 "fixed": {"rotation": [0, 180, 0], "scale": [1, 1, 1]},
                 "thirdperson_righthand": {"rotation": [0, 90, -20], "translation": [0, 2, 1], "scale": [0.55, 0.55, 0.55]},
                 "thirdperson_lefthand": {"rotation": [0, -90, 20], "translation": [0, 2, 1], "scale": [0.55, 0.55, 0.55]},
                 "firstperson_righthand": {"rotation": [0, -60, 15], "translation": [1, 2, 0], "scale": [0.6, 0.6, 0.6]},
                 "firstperson_lefthand": {"rotation": [0, 60, -15], "translation": [1, 2, 0], "scale": [0.6, 0.6, 0.6]}}}
    if model["texture_size"] is None: del model["texture_size"]
    json.dump(model, open(f'{OUT}/{fid}.json', 'w'), separators=(',', ':'))
print('models:', len([f for f in os.listdir(OUT) if f.endswith('.json')]))
