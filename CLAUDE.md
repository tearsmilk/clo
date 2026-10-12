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
- Подписка Рыбак+: право `zenfishing.premium` или `/рыбалка premium give <ник> [срок]`; PAPI `%zenfishing_premium_badge%`.
- На сервере есть старый rurukaFish 0.2.0 — тоже подменяет улов; одновременно с ZenFishing не держать.

## ZenGroups (группы/права) — тот же сервер
- Jar: `./gradlew build` в `ZenGroups/` → `plugins/ZenGroups-<версия>.jar`; деплой и рестарт как у ZenQuests.
- Конфиги: `plugins/ZenGroups/config.yml` (плагин: таб/чат/над ником вкл-выкл), `groups.yml` (группы, вес, префиксы/суффиксы),
  `permissions.yml` (права групп, `-право`, `*`); `/group reload`. Команды: `/group add|set|take|info|list`, право `zengroups.admin` (op).
- Регистрируется в Vault как провайдер прав и чата; PAPI `%zengroups_*%`. Таб/чат могут пересекаться с TakuCore — выключать в config.yml.
