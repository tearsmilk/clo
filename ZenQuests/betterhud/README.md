# Плашки ежедневных квестов в BetterHud

Плагин отдаёт через PlaceholderAPI `%zenquests_hud_<n>_active|name|progress|amount|percent|left%` (n = 1..4 — невыполненные
ежедневные по порядку) и `%zenquests_hud_count%`. На сервере (plugins/BetterHud):
- `huds/quests.yml` — новый HUD (копировать);
- `layouts/quests-layout.append.yml` — дописать в конец `layouts/default-layout.yml`;
- `texts/default_font.append.yml` — дописать в `texts/default_font.yml` → `default_font.images`;
- `assets/icons/quest.png` — иконка (16x16, из иконки «Ежедневные» меню квестов);
- в `config.yml` BetterHud добавить `quests` в `default-hud`; затем `/betterhud reload` (или рестарт).
Плашки: align right, x -8, y 30/45/60/75 — под плашкой времени года (y 11). Превью — `preview_hud.png`.
