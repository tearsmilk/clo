# Фоны меню ZenQuests — спеки для скилла minecraft-nexo-gui

Сцена собирается из частей (`scene_compose.py`, запускать из папки с `raw/` и `wall_full.png` — в репозитории это
`art/parts/` и `art/wall_full.png`): тайл дощатой стены с виньеткой и тёплым светом фонарей, балка, столбы во всю
высоту, гирлянды, записки, верёвка и серп, кусты (задний план), бочка и мешок, сено, тыквы (передний план); у каждой
части мягкая тень на стене и контактная тень снизу. Части и стена сгенерированы Figma AI (`art/parts_full.png`,
`art/wall_full.png`) и вырезаны по цвету фона. Плашки под «Инвентарь» больше нет. Инвентарь игрока: сцена амбара продолжается вниз на всё окно (472x478, плитки 236x240 / 236x238, height 120/119,
ascent 30 / -90), а рама и колодцы инвентаря и хотбара дорисовываются на накладку `inventory_frame.py` в том же
стиле, что доска квестов (`draw_player_inventory: false` в спеках). Всё непрозрачно — у игроков с любым своим
ресурспаком меню выглядит одинаково.

Текущая схема — HD: сцена `art/barn_hd.png` (472x270 = 2 px текстуры на 1 px интерфейса) режется на 4 плитки
`textures/gui/scene/scene_{tl,tr,bl,br}.png` (236x136 / 236x134), в `menu_font.json` они — bitmap с `height` 68/67 и
`ascent` 30 / -38; поверх идёт накладка меню 1x (`textures/gui/menu/<name>.png`, окно прозрачное, в (235,238) пиксель
с alpha=1 — якорь ширины глифа). Порядок символов задаёт `menu.textures.sequence` в config.yml плагина.
Сцена амбара (`art/barn_full.png`, 1536x864) сгенерирована Figma AI (gpt-image) по промпту «16-bit pixel art barn wall,
lanterns, wheat garland, hay and pumpkins in the corners, calm empty centre»; `art/barn.png` — она же, обрезана до 236x135
(box [-30,0,236,135] в спеке) и квантована до 48 цветов. Поверх неё билдер кладёт ленту-заголовок, рамки слотов и
панель инвентаря — так арт от модели, а геометрия слотов точная.

Картинки меню рисует `scripts/gui_builder.py` из скилла `minecraft-nexo-gui` (лежит в `.claude/skills/` в ветке
`claude/discord-minecraft-banner-k8ln0l` репозитория, либо `~/.claude/skills/minecraft-nexo-gui`):

```bash
python3 scripts/gui_builder.py gui-specs/main_hd.json OUT_main     # накладки 1x (рамки, лента, инвентарь; окно прозрачное)
python3 scripts/gui_builder.py gui-specs/pages_hd.json OUT_pages   # daily / weekly / seasonal / story / chain (variants)
# main_art/pages_art — та же сцена, но 1x внутри одной картинки; main/pages — сцена целиком от билдера
# main.json / pages.json — старая версия, где сцена целиком рисовалась билдером
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

Иконки квестов (`menu.quest-cards`, 32x32): сгенерированы картиночной моделью (Figma AI, gpt-image) одним листом
в стиле 16-bit RPG-паков — `quest-icons/generated_sheet.png`; дальше лист режется по сетке, фон (#3d3d3c) убирается
по цветовому расстоянию, каждый предмет ужимается `pixelstyle.fit(30)` + `quantize(20)` в 32x32 (`quest-icons/*.png`).
Состояние — бейдж 1:1 в правом нижнем углу (`badge_ready` искра, `badge_claimed` галочка, `badge_locked` замок,
`badge_active` пустой; рисуются `quest_items16.py`). Модели `models/item/quest/<state>_<emblem>.json` = generated,
layer0 предмет + layer1 бейдж; плагин выбирает модель по состоянию и objective.type (`QuestMenu.emblem`).
Промпт для догенерации — в истории сессии; новые предметы добавлять тем же способом, чтобы стиль совпадал.
