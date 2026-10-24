# Фоны меню ZenFishing

Та же схема, что у ZenQuests (`ZenQuests/gui-specs/README.md`), только синяя и рыбацкая:
- `art/wall_full.png` — стена из выцветших сине-зелёных досок, `art/parts/*.png` — балка, столб, сеть, буй, якорь,
  связка рыбы, ящик, спасательный круг, камыш, фонарь, верёвка, записка (всё — Figma AI, лист `art/parts_full.png`,
  вырезан по магентовому фону).
- `scene_compose.py OUT` → `OUT/pier_hd.png` (472x478) и плитки `OUT/scene/scene_{tl,tr,bl,br}.png` (236x240 / 236x238).
- Накладки: `python3 scripts/gui_builder.py gui-specs/main_hd.json OUT` и `rod_hd.json` (из папки скилла
  `minecraft-nexo-gui` с патчем ленты), затем `python3 inventory_frame.py OUT/texture/*.png` (синяя рама инвентаря).
- Пак: `assets/zenfishing/font/menu.json` (`menu_font.json`), `textures/gui/menu/{main,rod}.png`, `textures/gui/scene/*`.
  Слоты главного меню: 2 удочка, 4 профиль, 6 Рыбак+, 20 продать, 22 прокачка, 24 топ, 49 закрыть; прокачка —
  4 удочка, 20..24 ветки, 49 назад (`FishMenu`).
- Превью: `preview_main.png`, `preview_rod.png`.

## Текстуры рыбы
`fish-icons/*.png` (64x64, 44 видов; `fish_icons_cut.py` режет листы с fit 60 + quantize 48) — сгенерированы Figma AI тремя листами 4x4 (`fish-icons/_sheet*.png`, промпт — список
рыб по рядам на магентовом фоне), нарезаны по клеткам `fish_icons_cut.py` (мусор соседних клеток отфильтрован по связным
компонентам, затем `pixelstyle.fit(30)` + `quantize(20)`). Пак: `assets/zenfishing/textures/item/fish/<id>.png`,
`models/item/fish/<id>.json` (generated), `items/fish/<id>.json`; плагин ставит модель `zenfishing:fish/<id>`
(`catch.item-model` в config.yml) — отдельных yml предметов Nexo нет. Превью — `fish_icons_preview.png`.

## Тултип «море»
`tooltip/sea_background.png`, `tooltip/sea_frame.png` (160x160 = 4x при логических 40x40, nine_slice border 12; рама 4 px из балки, столба и бухт верёвки причала, фон — тёмная стена причала) → `assets/zenfishing/textures/gui/sprites/tooltip/`.
Ставится на удочку (`rod.tooltip-style`), пойманную рыбу (`catch.tooltip-style`) и меню (`menu.tooltip-style`) — `zenfishing:sea`. Превью — `tooltip/preview_sea_tooltip.png`.

## 3D-модели рыбы
`fish_models3d.py SPRITES OUT_MODELS OUT_TEXTURES [preview.png]` — параметрические объёмные модели (как в Blockbench): тело из
ступенчатых сегментов по профилю рыбы, раздвоенный хвост под углом, ступенчатый спинной, анальный и грудные плавники;
типы тела standard / long / eel / sword / round / mola / flat / kraken / dragon / fancy (словарь KIND). Текстура-атлас 64x64
на вид рисуется процедурно по палитре спрайта (спина/бок/брюхо/плавники, чешуя, узор из PATTERN, глаз и рот у морды)
→ `assets/zenfishing/textures/item/fish3d/<id>.png`, модели → `assets/zenfishing/models/item/fish/<id>.json`.
Спрайты 64x64 (`fish-icons/`) остаются источником палитры. Превью рендера — `fish_3d_preview.png`.
У рыбы-предмета нет веса, редкости и автора: имя = название цветом редкости, описание пустое (стакается).

## 3D-рыба на моделях FreshFood (актуально с 24.10)
`fish_models_ff.py freshfood OUT_MODELS OUT_TEXTURES [preview.png]` — берёт `freshfood/cod_3d.{json,png}` (все виды) и
`pufferfish_3d` (pufferfish, mola, moon_fish, kraken_calf) из внешнего пака FreshFood (`Nexo/pack/external_packs/FreshFood`) и
перекрашивает: тело → цвет «бок» вида, плавники/хвост/шипы → цвет «плавники» из `PAL` в `fish_models3d.py`; светлота пикселей
исходника сохраняется, поэтому рыба остаётся простой (8–10 цветов, крупные пиксели). `fish_models3d.py` — старый параметрический
генератор, теперь нужен только как источник палитр.
