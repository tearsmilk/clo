# Заметки для Claude по проекту

## ZenQuests → сервер (Pterodactyl, panel.hoka.ink, сервер dafb2994-850a-408e-b4fe-e13e2bf96cbd)
- Рестарт сервера: команда в консоль **`tfrestart`** (`POST /api/client/servers/<id>/command`, `{"command":"tfrestart"}`).
  Рестартить ВСЕГДА после ЛЮБОЙ заливки на сервер (jar, конфиги, Nexo), даже мелкой, не спрашивая — так хочет владелец.
  Кнопки питания панели (`/power`) отвечают 500 — не использовать.
- Если владелец сказал «сначала покажи» — показать результат и ОСТАНОВИТЬСЯ. На сервер заливать только после его
  явного «заливай»; на репо это не распространяется. `/reload` (bukkit:reload) на сервере не работает
  (Leaf 1.21.11: lifecycle-хендлеры плагинов блокируют перезагрузку) — не пробовать.
- Jar: `./gradlew build` в `ZenQuests/` → `plugins/ZenQuests-<версия>.jar`, старый удалить. Загрузка — `files/write`
  (прямой upload на node.hoka.ink недоступен). После записи сверять содержимое с локальным файлом.
- Конфиги: `plugins/ZenQuests/config.yml`, `quests.yml`; `/квесты reload` после правок (jar — только рестарт).
  **quests.yml на сервере — мастер-копия** (владелец правит его сам, 18.10 заменил на свой набор из 24 ежедневных): перед любой правкой
  скачать с сервера, НЕ перезаписывать локальной версией из репо. Деплой jar — ТОЛЬКО после успешной сверки (cmp), старый jar
  удалять только после неё; при 502 панели повторять запись.
- Nexo: всё для квестов — только в `plugins/Nexo/pack/assets/zenquests/` (фоны меню, тултип, иконки, шрифты).
  Исключения: глифы — `plugins/Nexo/glyphs/zenquests.yml` (обязательно `font: minecraft:default`, иначе глиф уходит в шрифт nexo:default и голый символ из плейсхолдера не рисуется; поле `char` не задавать: Nexo назначает сам при reload
  и пишет в файл; свой PUA-символ клиент показывает как «тофу»). После заливки — `nexo reload all` в консоль.
- Таб/роли — TakuCore (`plugins/TakuCore/roles.yml`, общий для сети — не править без спроса).
- Фоны меню рисуются скиллом `minecraft-nexo-gui` из спеков `ZenQuests/gui-specs/` (см. README там); скилл лежит в ветке
  `claude/discord-minecraft-banner-k8ln0l` (`.claude/skills/minecraft-nexo-gui`) — забрать через `git archive` в `~/.claude/skills/`.
- Иконки меню — Aseprite (`ZenQuests/gui-specs/README.md`); бинарь собирается в контейнере заново: `build_aseprite.sh`.

## ZenFishing (рыбалка) — тот же сервер
- Jar: `./gradlew build` в `ZenFishing/` → `plugins/ZenFishing-<версия>.jar`, старый удалить; деплой и рестарт как у ZenQuests.
- Конфиги: `plugins/ZenFishing/config.yml`, `fish.yml`; `/рыбалка reload`. Продажа — Vault (экономика монет TakuFarmers).
- Своей подписки нет: бонусы рыбалки даёт Ферма+ из ZenQuests (право `zenquests.premium` / `QuestsAPI.isPremium`). Квесты на рыбу —
  типы `CATCH_FISH` (цель id рыбы), `CATCH_RARITY`, `CATCH_NIGHT`, `CATCH_BIG` (≥ `catch.big-kg`). Ночью (13000–23000) клёв и удача выше
  (`catch.night`). Тултип `zenfishing:sea` на удочке, рыбе и меню. Текстуры рыбы 64x64, модели объёмные (`gui-specs/fish_models3d.py`).
  Рыба-предмет без веса/редкости/автора (просто название), стакается; `CATCH_BIG` больше не засчитывается. rurukaFish удалён (jar), папка оставлена.

## ZenGroups (группы/права) — тот же сервер
- Jar: `./gradlew build` в `ZenGroups/` → `plugins/ZenGroups-<версия>.jar`; деплой и рестарт как у ZenQuests.
- Группы: player (по умолчанию), vip, vipplus, media, moder, admin; префиксы — глифы `{glyph:badge_*}` (badges.yml + `glyphs/zengroups.yml`,
  текстуры `assets/zengroups/textures/font/`, исходники `ZenGroups/nexo/`). Плагин сам резолвит `{glyph:}` через Nexo.
- Конфиги: `plugins/ZenGroups/config.yml` (плагин: таб/чат/над ником вкл-выкл), `groups.yml` (группы, вес, префиксы/суффиксы),
  `permissions.yml` (права групп, `-право`, `*`); `/group reload`. Команды: `/group add|set|take|info|list`, право `zengroups.admin` (op).
- Регистрируется в Vault как провайдер прав и чата; PAPI `%zengroups_*%`. Таб/ник/чат рисует TakuCore: в его `roles.yml`
  (с разрешения владельца, бэкап `roles.yml.bak-zengroups`) в prefix/suffix каждой роли подставлены `%zengroups_<tab|name|chat>_prefix/suffix%`;
  в ZenGroups `tab/nametag/chat.enabled: false`. На других серверах сети без ZenGroups эти плейсхолдеры покажутся текстом.

## BetterHud — плашки ежедневных квестов
- ZenQuests отдаёт `%zenquests_hud_<n>_active|name|desc|progress|amount|cat%` (n 1..4, закреплённые ПКМ в меню и не выполненные;
  сюжетный — отдельный верхний слот `%zenquests_hud_story_*%`, всегда текущий шаг, ПКМ скрывает; автозакреп ежедневных выключен; боссбар выключен). В BetterHud: `huds/quests.yml`,
  блок `quests:` в конце `layouts/default-layout.yml`, иконка `assets/icons/quest.png` + запись в `texts/default_font.yml`, `quests` в
  `default-hud` config.yml. Исходники — `ZenQuests/betterhud/`. Бэкап старого layout — `plugins/BetterHud/default-layout.yml.bak-quests`
  (не класть .bak в `layouts/` — BetterHud ругается). BetterHud собирает свой пак в `Nexo/pack/external_packs/modernhud`.
