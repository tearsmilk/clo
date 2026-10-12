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

Заголовки — лента (`header.style: ribbon`) с жирным шрифтом `font: "bold"` (капители из `shop.letters`, как на
кухонной вывеске). Этой опции в скилле из ветки нет — она добавлена патчем `gui_builder_ribbon_bold.patch`
(`patch -p0 scripts/gui_builder.py < gui_builder_ribbon_bold.patch` внутри папки скилла).
