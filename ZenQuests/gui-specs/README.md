# Фоны меню ZenQuests — спеки для скилла minecraft-nexo-gui

Картинки меню рисует `scripts/gui_builder.py` из скилла `minecraft-nexo-gui` (лежит в `.claude/skills/` в ветке
`claude/discord-minecraft-banner-k8ln0l` репозитория, либо `~/.claude/skills/minecraft-nexo-gui`):

```bash
python3 scripts/gui_builder.py gui-specs/main.json OUT_main     # главное меню
python3 scripts/gui_builder.py gui-specs/pages.json OUT_pages   # daily / weekly / seasonal / story / chain (variants)
```

Выход `texture/*.png` (236x239: окно 176x222 + поля 30/30 слева-справа и 17 сверху) кладётся в
`plugins/Nexo/pack/assets/zenquests/textures/gui/menu/<name>.png`; шрифт `assets/zenquests/font/menu.json`:
`ascent: 30`, `height: 239`, сдвиги ` = -38` (к левому краю поля) и ` = -191` (обратно к началу названия).
Плагин сам подставляет эти символы в название окна (`QuestMenu.menuTitle`), глифы Nexo для этого не нужны.
Раскладка слотов фиксирована в `QuestMenu`: главное — 4 (профиль), 19/21/23/25 (категории), 48 (Ферма+), 50 (закрыть);
страницы — 4 (шапка), 10..43 без крайних колонок (28 квестов), 48/49/50 (навигация).

Заголовки — лента (`header.style: ribbon`) с жирным шрифтом `font: "bold"` и вышивкой `embroidered: "#f2c94c"` (цвет нити) (капители из `shop.letters`, как на
кухонной вывеске). Этой опции в скилле из ветки нет — она добавлена патчем `gui_builder_ribbon_bold.patch`
(`patch -p0 scripts/gui_builder.py < gui_builder_ribbon_bold.patch` внутри папки скилла).

Иконки кнопок меню (`assets/zenquests/textures/item/icon/*.png`, 15 штук) рисуются инструментами Aseprite
через скилл: `python3 icons_make_ops.py OPS/` пишет операции (эллипсы, контуры, Outline; 5-тоновые рампы
`shading.ramp5`), затем на каждую `python3 scripts/aseprite_draw.py OPS/<name>.json OUT/<name>.png`.
Aseprite собирается `bash scripts/build_aseprite.sh DIR` (нужны `apt-get update` и libxcursor/libxi/libxrandr/
libgl1-mesa/libfontconfig dev-пакеты; ~10 мин), бинарь не коммитить (EULA). `icons_preview.png` — как выглядят.

Карточки квестов (`menu.quest-cards`, текстуры 32x32 — клиент ужимает в слот): `quest_cards_make_ops.py OPS/` рисует 4 пергамента по состоянию
(`card_active|ready|claimed|locked`) и 19 эмблем по типу задания; модели `models/item/quest/<state>_<emblem>.json`
(generated, layer0 карточка + layer1 эмблема) и определения `items/quest_<state>_<emblem>.json` генерируются на
каждую пару. Плагин подставляет модель по состоянию квеста и его objective.type (`QuestMenu.emblem`).
