"""Пак для Quastres из blocks.yml:
  assets/minecraft/blockstates/campfire.json, soul_campfire.json — на каждое состояние потушенного костра своя модель
      (незанятые потушенные состояния и все горящие остаются ванильными);
  assets/quastres/models/block/<id>.json — плита 16x7x16 (высота костра 7/16) с текстурами top/side/bottom из blocks.yml;
  Quastres.yml — предметы Nexo (PAPER с моделью quastres:block/<id>) для plugins/Nexo/items/.
Запуск: python3 make_pack.py ../src/main/resources/blocks.yml OUT_DIR"""
import sys, os, json, yaml

BLOCKS, OUT = sys.argv[1], sys.argv[2]
cfg = yaml.safe_load(open(BLOCKS, encoding='utf-8'))['slabs']
ROT = {'south': 0, 'west': 90, 'north': 180, 'east': 270}   # как у ванильного костра, модель не поворачиваем — y не задаём

def put(path, data, raw=False):
    p = os.path.join(OUT, path); os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        if raw: f.write(data)
        else: json.dump(data, f, ensure_ascii=False, indent=1)

states = {'campfire': {}, 'soul_campfire': {}}
items = {}
for sid, s in cfg.items():
    if 'model' in s:   # готовая модель (например ванильный потушенный костёр) — без генерации плиты
        base = s.get('base', 'campfire'); facing = s.get('facing', 'north'); signal = str(bool(s.get('signal', False))).lower()
        key = f"facing={facing},lit=false,signal_fire={signal}"
        assert key not in states[base], f'{sid}: состояние {base} {key} уже занято'
        v = {"model": s['model']}
        if s.get('y'): v['y'] = s['y']
        states[base][key] = v
        items[sid] = {"itemname": s['name'], "material": "PAPER", "lore": ["<gray>Полублок Quastres. Ставится ПКМ."], "Pack": {"model": s['model']}}
        continue
    t = s['textures']
    model = {"parent": "minecraft:block/block", "textures": {"particle": t['side'], "top": t['top'], "side": t['side'], "bottom": t['bottom']},
             "elements": [{"from": [0, 0, 0], "to": [16, 7, 16], "faces": {
                 "down": {"uv": [0, 0, 16, 16], "texture": "#bottom", "cullface": "down"},
                 "up": {"uv": [0, 0, 16, 16], "texture": "#top"},
                 "north": {"uv": [0, 9, 16, 16], "texture": "#side", "cullface": "north"},
                 "south": {"uv": [0, 9, 16, 16], "texture": "#side", "cullface": "south"},
                 "west": {"uv": [0, 9, 16, 16], "texture": "#side", "cullface": "west"},
                 "east": {"uv": [0, 9, 16, 16], "texture": "#side", "cullface": "east"}}}]}
    put(f'assets/quastres/models/block/{sid}.json', model)
    base = s.get('base', 'campfire'); facing = s.get('facing', 'north'); signal = str(bool(s.get('signal', False))).lower()
    key = f"facing={facing},lit=false,signal_fire={signal}"
    assert key not in states[base], f'{sid}: состояние {base} {key} уже занято'
    states[base][key] = {"model": f"quastres:block/{sid}"}
    items[sid] = {"itemname": s['name'], "material": "PAPER", "lore": ["<gray>Полублок Quastres. Ставится ПКМ."],
                  "Pack": {"model": f"quastres:block/{sid}"}}

for base, used in states.items():
    variants = {}
    for facing, rot in ROT.items():
        for signal in ('false', 'true'):
            key = f"facing={facing},lit=false,signal_fire={signal}"
            if key in used: variants[key] = used[key]
            else:
                v = {"model": f"minecraft:block/{base}_off"}
                if rot: v["y"] = rot
                variants[key] = v
        v = {"model": f"minecraft:block/{base}"}
        if rot: v["y"] = rot
        variants[f"facing={facing},lit=true"] = v
    put(f'assets/minecraft/blockstates/{base}.json', {"variants": variants})

header = ("# Предметы полублоков Quastres (генерируется pack/make_pack.py из blocks.yml плагина — править там).\n"
          "# Модель — та же, что у поставленного блока; сам блок ставит плагин Quastres (ПКМ), Nexo тут только предмет.\n")
put('Quastres.yml', header + yaml.safe_dump(items, allow_unicode=True, sort_keys=False, default_flow_style=False), raw=True)
print('pack ok:', len(cfg), 'slabs')
