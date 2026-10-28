# Передача контекста: плагины фермы (Noratrum, Quastres и пак Nexo)

Состояние на 28.10.2026. Репо `github.com/tearsmilk/clo`, ветка `claude/nice-bell-zigxag` (всё закоммичено и запушено).
Полные правила работы — в `CLAUDE.md` в корне репо; здесь краткая карта.

## Сервер
- Pterodactyl `panel.hoka.ink`, сервер `dafb2994-850a-408e-b4fe-e13e2bf96cbd`, ядро Leaf 1.21.11 (форк Paper), доступ через прокси по `/api/client/`.
- Файлы: `GET /files/contents?file=…`, `POST /files/write?file=…` (сырое тело), `POST /files/delete`, `GET /files/list?directory=…`.
  Панель часто отвечает 502 — повторять с паузой. После записи ВСЕГДА скачивать обратно и сверять `cmp`.
- Рестарт: команда в консоль `POST /command {"command":"tfrestart"}`. Рестартить после ЛЮБОЙ заливки, не спрашивая. `/power` отдаёт 500,
  вебсокет к ноде отсюда не доступен. Если панель показывает `offline` при живом сервере — команды не доходят, рестарт делает владелец.
- Nexo: после правок пака — `nexo reload all` в консоль, затем рестарт. `/reload` сервера не работает.
- Jar НИКОГДА не перезаписывать поверх работающего с тем же именем (ленивая загрузка классов → флуд NoClassDefFoundError до рестарта):
  заливать под новым именем, удалять старый, рестарт.
- Владелец: если сказал «сначала покажи» — показать результат и остановиться, заливать только после явного «заливай».

## Noratrum (paper-plugin, `Noratrum/`), версия `o012mk23f87`, authors `fame/ktnqqq`, без description/website
Объединяет три бывших плагина как модули (`ink.hoka.noratrum.Module` реализует `Plugin`, делегирует в хост; имя модуля даёт прежний
неймспейс ключей PDC `zenquests:`, `zenfishing:`; команды старого образца через `LegacyCommands` → Brigadier; права в `Noratrum.registerPermissions`).
- Сборка: `cd Noratrum && ./gradlew build` → `build/libs/Noratrum-o012mk23f87.jar`. Исходники модулей: `ZenQuests/src`, `ZenFishing/src`,
  `ZenGroups/src` (подключены в сборку Noratrum; своих gradle у них больше нет). На сервере: `plugins/Noratrum-o012mk23f87.jar`.
- Папки: `plugins/Noratrum/config.yml` (modules.*, plugins-command), `plugins/Noratrum/quests/`, `fishing/`, `groups/` (конфиги и данные игроков).
  **`quests/quests.yml` — мастер-копия владельца: перед правкой скачать с сервера, не перезаписывать из репо** (в репо лежит зеркало `ZenQuests/src/main/resources/quests.yml`).
- `/plugins` и `/pl` перехвачены (`PluginsCommand`): секция «Leaf Plugins» (config `plugins-command.leaf-plugins: [Noratrum, Quastres]`),
  далее Paper/Bukkit по meta плагина автоматически; подсказка как у Paper (Version/Description/Website/Authors, значения &a). Право `noratrum.plugins` (default true).
- Зависимости (optional): Vault, PlaceholderAPI, Nexo, TakuFarmers (BEFORE), TakuCore (AFTER — Noratrum грузится раньше него).

### Модуль ZenQuests (квесты) — `/квесты`, `/ffly`
- Категории: daily/weekly/seasons/story; сюжет — цепочки: «Хроники Тихой долины» (11 глав), «Первая грядка» (2), «Тихая гавань» (8, рыбацкая), «Фермерская жизнь» (Ферма+).
- Типы заданий: ванильные (BREAK, PLACE, KILL, FISH, CRAFT…), TakuFarmers (CROP_HIT/HARVEST/BREAK, COOK, COOK_ITEM, MILL, FLOUR_SACK, EARN, SPEND,
  FARM_VISIT, NPC_TALK, DIALOG), грядки API 1.1 (WEED, WATER, WELL, FERTILIZE, BED_PLACE, BED_PLANT, BED_HARVEST), SEEDS (стол семян), OBTAIN (прирост
  предмета в инвентаре, напр. flour, summer_salad), рыбалка (CATCH_FISH, CATCH_NIGHT, FISH_EARN — деньги с продажи рыбы; CATCH_RARITY/CATCH_BIG устарели).
- TakuFarmers (`hook/TakuFarmersHook`, рефлексия по именам классов): столы (скалка/жёрнов/кухня) шлют CookCompleteEvent на каждый клик по слоту выхода —
  считаем реально забранные предметы (сравнение слота 15 на следующем тике); `seed_table` → SEEDS, `millstone` → MILL.
- Ферма+ (подписка): право `zenquests.premium` или `/квесты premium give`; значок `%zenquests_premium_badge%` стоит в суффиксе ролей TakuCore
  (`plugins/TakuCore/roles.yml`, общий для сети, бэкап `.bak-zengroups`); бонусы рыбалки и `/ffly` (полёт на своей ферме) завязаны на неё.
- HUD (BetterHud): `%zenquests_hud_<1..4>_*%` закреплённые ПКМ в меню квесты, `%zenquests_hud_story_*%` текущая сюжетная глава (на плашке только название);
  строка задания обрезается до `hud.desc-max` (30). Layout: `plugins/BetterHud/layouts/default-layout.yml` блок `quests:`; исходники `ZenQuests/betterhud/`.
- Книга квестов: 3D-модель `zenquests:quest_book` (`gui-specs/quest_book_model.py`, `.bbmodel` в `gui-specs/quest-book/`), выдаётся при входе, ПКМ → меню.
- Меню/карточки/тултипы: пак `Nexo/pack/assets/zenquests/`, спеки и генераторы в `ZenQuests/gui-specs/` (README там).

### Модуль ZenFishing (рыбалка) — `/рыбалка`
- 44 вида рыбы (`fishing/fish.yml`), редкости, биомы; рыба-предмет без веса/редкости/автора, стакается; продажа через Vault (`/рыбалка продать`, меню).
- Удочка: уровни/опыт/ветки (удача, клёв, двойной улов, продажа, опыт), не ломается; меню прокачки. Ночью (13000–23000) клёв и удача выше.
- Любой ванильный улов заменяется нашей рыбой. Рыбацкий журнал — предмет-книга (синяя 3D-модель `zenfishing:fish_journal`), ПКМ → меню; при ПКМ старый журнал без модели обновляется.
- Сети (`Nets.java`): `/рыбалка сеть` купить (500 монет), 4 ПКМ по блокам/воде = углы, сеть ложится на воду (ItemDisplay-плитки + Interaction),
  ловит сама раз в минуту, ПКМ — улов, Shift+ПКМ — снять; хранятся в `fishing/nets.yml`. Модели `zenfishing:fishing_net`, `fishing_net_tile`.
- **Модели рыбы (актуально):** перекрашенные `cod_3d` (все) и `pufferfish_3d` (pufferfish, mola, moon_fish, kraken_calf) из внешнего пака
  FreshFood (`Nexo/pack/external_packs/FreshFood`): `gui-specs/fish_models_ff.py`, палитры видов — `PAL` в `gui-specs/fish_models3d.py`,
  исходники FreshFood скопированы в `gui-specs/freshfood/`. Пак: `assets/zenfishing/models/item/fish/<id>.json`, `textures/item/fish3d/<id>.png`,
  `items/fish/<id>.json`; плагин ставит `item_model zenfishing:fish/<id>`. Владелец хочет простые «пиксельные» модели в стиле FreshFood, без детализации.
- Тултип `zenfishing:sea` (спрайты `textures/gui/sprites/tooltip/`), фоны меню `assets/zenfishing/textures/gui/`.

### Модуль ZenGroups (группы/права) — `/group add|set|take|info|list|reload`
- Группы player/vip/vipplus/media/moder/admin (`groups/groups.yml`, веса, префиксы-глифы `{glyph:badge_*}`), права `groups/permissions.yml`, пользователи `groups/users/`.
- Vault-провайдер прав и чата, PAPI `%zengroups_*%`; отрисовку таба/ника/чата делает TakuCore через плейсхолдеры в его roles.yml. Глифы: `Nexo/glyphs/zengroups.yml` (`font: minecraft:default`).

## Quastres (paper-plugin, `Quastres/`, v1.0.2) — полублоки сверх лимита Carpentry
- Полублок = потушенный костёр в одном состоянии (campfire|soul_campfire × facing × signal = 16 слотов), `plugins/Quastres/blocks.yml`.
  Заняты: campfire north — декоративный костёр без огня (ванильная модель `campfire_off`; обычные костры плагин поворачивает на север, так что
  потушенный ванильный костёр = этот блок), south пальма, west осина, east сосна; soul_campfire north берёза. 11 слотов свободно.
- Плагин ставит состояние по ПКМ, роняет Nexo-предмет, блокирует поджиг/готовку/физику; команды `/quastres give|list|reload` (`quastres.admin`).
- Пак: `pack/make_pack.py blocks.yml OUT` → `assets/minecraft/blockstates/{campfire,soul_campfire}.json`, `assets/quastres/models/block/*.json`,
  `Quastres.yml` (предметы Nexo → `plugins/Nexo/items/`). Текстуры коры `Nexo/pack/assets/orsess/textures/block/slab_*.png`. Высота блока 7/16.

## Nexo Carpentry (addon, `plugins/carpentry-1.6.1.jar`) — плиты
- Тип SLAB = 4 вощёные медные плиты, жёстко в jar. Заняты: 1 дёрн, 2 песок, 4 дуб-кора (`items/Полублоки.yml`), 3 ореховая владельца (`Дерево.yml`).
  Пример `ashen_oak_slab` закомментирован (бэкап `carpentry_blocks.yml.bak-slabs`). Биомной окраски у плит нет — трава затонирована ярким зелёным.
  Генератор текстур `nexo-blocks/slabs/make_slab_textures.py` (из ванильного client.jar), боковина = верхняя половина блока.

## Типичный деплой
1. Собрать jar / сгенерировать файлы пака.
2. Залить каждый файл через `files/write`, скачать обратно, `cmp`. Jar — под новым именем, старый удалить после сверки.
3. Если менялся пак — `nexo reload all`. Затем `tfrestart`. Проверить `logs/latest.log` (строки `[Noratrum]`, `[Quastres]`, ошибки).
4. Закоммитить в репо (копии пака: `ZenFishing/nexo/pack/`, `Quastres/pack/generated`, `nexo-blocks/`).

## Открытые хвосты / идеи
- Проверить в игре новую рыбу FreshFood-стиля (залита 24.10) и ориентацию плиток сети на воде.
- Берёза в Carpentry закомментирована (нет слота) — живёт в Quastres.
- Книга квестов: владелец может прислать свой `.bbmodel` — заменить `assets/zenquests/models/item/quest_book.json` + текстуру.
- Пароль БД TakuFarmers виден в его config.yml — не копировать и не светить.
