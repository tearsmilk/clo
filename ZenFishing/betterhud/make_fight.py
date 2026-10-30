"""Полоса вываживания для BetterHud: все слои — картинки шириной с полосу (148 px), ставятся с x: 0 поверх друг друга,
поэтому зона/маркер/точки не могут разъехаться с полосой. Генерирует assets/fight/full/*.png, images/fishfight.yml и
layouts/fishfight-layout.append.yml. Запуск: python3 make_fight.py (из ZenFishing/betterhud)."""
from PIL import Image
W, H, CELLS, CELL = 148, 16, 24, 6          # полоса 148×12 внутри холста 148×16 (маркер 16 px выступает сверху/снизу)
BAR_Y = 2
bar, zone, marker, hit, todo = (Image.open(f'assets/fight/{n}.png').convert('RGBA') for n in ('bar', 'zone', 'marker', 'hit', 'todo'))
def canvas(w=W, h=H): return Image.new('RGBA', (w, h), (0, 0, 0, 0))
c = canvas(); c.alpha_composite(bar, (0, BAR_Y)); c.save('assets/fight/full/bar.png')
for i in range(CELLS):
    z = canvas(); z.alpha_composite(zone, (2 + CELL * i, BAR_Y + (bar.height - zone.height) // 2)); z.save(f'assets/fight/full/zone_{i}.png')
    m = canvas(); m.alpha_composite(marker, (2 + CELL * i, 0)); m.save(f'assets/fight/full/marker_{i}.png')
DOT, GAP, MAXN = hit.width, 2, 5
for n in range(1, MAXN + 1):
    x0 = (W - (n * DOT + (n - 1) * GAP)) // 2
    for i in range(n):
        for name, img in (('hit', hit), ('todo', todo)):
            d = canvas(W, DOT); d.alpha_composite(img, (x0 + i * (DOT + GAP), 0)); d.save(f'assets/fight/full/{name}_{n}_{i}.png')
imgs = [('fight_bar', 'bar.png')] + [(f'fight_zone_{i}', f'zone_{i}.png') for i in range(CELLS)] + [(f'fight_marker_{i}', f'marker_{i}.png') for i in range(CELLS)] \
     + [(f'fight_{k}_{n}_{i}', f'{k}_{n}_{i}.png') for n in range(1, MAXN + 1) for i in range(n) for k in ('hit', 'todo')]
with open('images/fishfight.yml', 'w', encoding='utf-8') as f:
    f.write('# Полоса вываживания ZenFishing (plugins/BetterHud/assets/fight/full/*.png). Каждая картинка шириной с полосу (148 px),\n'
            '# элемент нарисован на своём месте — все слои ставятся с x: 0 и не разъезжаются. Генерируется make_fight.py.\n')
    for name, file in imgs: f.write(f'{name}: {{type: single, file: fight/full/{file}}}\n')
def ph(name): return name.replace('fight_', 'zenfishing_fight_', 1) if name != 'fight_bar' else 'zenfishing_fight_active'
with open('layouts/fishfight-layout.append.yml', 'w', encoding='utf-8') as f:
    f.write('\n# Вываживание ZenFishing: полоса, 24 клетки зоны, 24 позиции маркера, точки попаданий (hit/todo_<всего>_<i>, по центру).\n'
            '# Все картинки шириной с полосу и стоят с x: 0 — одно условие на картинку (%zenfishing_fight_*% = 1/0). Генерируется make_fight.py.\n'
            'fishfight:\n  images:\n')
    for k, (name, _) in enumerate(imgs, 1):
        y = DOT and (H + 1) if name.startswith(('fight_hit', 'fight_todo')) else 0
        f.write(f'    {k}:\n      name: {name}\n      align: center\n      layer: {0 if name == "fight_bar" else 1}\n      x: 0\n      y: {y}\n'
                f'      conditions:\n        1:\n          first: "(number)papi:{ph(name)}"\n          second: "\'(number)1\'"\n          operation: \'==\'\n')
print('images:', len(imgs))
