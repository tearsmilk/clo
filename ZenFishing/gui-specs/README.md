# Фоны меню ZenFishing

Та же схема, что у ZenQuests (`ZenQuests/gui-specs/README.md`), только синяя и рыбацкая:
- `art/wall_full.png` — стена из выцветших сине-зелёных досок, `art/parts/*.png` — балка, столб, сеть, буй, якорь,
  связка рыбы, ящик, спасательный круг, камыш, фонарь, верёвка, записка (всё — Figma AI, лист `art/parts_full.png`,
  вырезан по магентовому фону).
- `scene_compose.py OUT` → `OUT/pier_hd.png` (472x478) и плитки `OUT/scene/scene_{tl,tr,bl,br}.png` (236x240 / 236x238).
- Накладки: `python3 scripts/gui_builder.py gui-specs/main_hd.json OUT` и `collection_hd.json` (из папки скилла
  `minecraft-nexo-gui` с патчем ленты), затем `python3 inventory_frame.py OUT/texture/*.png` (синяя рама инвентаря).
- Пак: `assets/zenfishing/font/menu.json` (`menu_font.json`), `textures/gui/menu/{main,collection}.png`, `textures/gui/scene/*`.
  Слоты главного меню: 2 удочка, 4 профиль, 6 Рыбак+, 20 продать, 22 коллекция, 24 топ, 49 закрыть; коллекция —
  10..43 без крайних колонок, 48/49/50 навигация (`FishMenu`).
- Превью: `preview_main.png`, `preview_collection.png`.
