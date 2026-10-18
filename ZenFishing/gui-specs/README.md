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
