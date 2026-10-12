# Заметки для Claude по проекту

## ZenQuests → сервер (Pterodactyl, panel.hoka.ink, сервер dafb2994-850a-408e-b4fe-e13e2bf96cbd)
- Рестарт сервера: команда в консоль **`tfrestart`** (`POST /api/client/servers/<id>/command`, `{"command":"tfrestart"}`).
  Кнопки питания панели (`/power`) отвечают 500 — не использовать.
- Jar: `./gradlew build` в `ZenQuests/` → `plugins/ZenQuests-<версия>.jar`, старый удалить. Загрузка — `files/write`
  (прямой upload на node.hoka.ink недоступен). После записи сверять содержимое с локальным файлом.
- Конфиги: `plugins/ZenQuests/config.yml`, `quests.yml`; `/квесты reload` после правок (jar — только рестарт).
- Nexo: всё для квестов — только в `plugins/Nexo/pack/assets/zenquests/` (фоны меню, тултип, иконки, шрифты).
  Исключения: глифы — `plugins/Nexo/glyphs/zenquests.yml`. После заливки — `nexo reload all` в консоль.
- Таб/роли — TakuCore (`plugins/TakuCore/roles.yml`, общий для сети — не править без спроса).
