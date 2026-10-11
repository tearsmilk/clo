# Nexo reference (GUI, glyphs, items, pack)

Source: https://docs.nexomc.com (append `.md` to any page URL for raw markdown; index at /llms.txt).
Re-check there when the user's Nexo version is newer than what is described here.

## Contents
- Glyphs: keys, tags, multi-bitmap, reference glyphs
- Custom GUIs: how Nexo fits in
- Items: invisible items, item models, icons
- Resource pack: folder layout, hosting, commands
- Versions and Bedrock

## Glyphs

Files: any `*.yml` in `plugins/Nexo/glyphs/`. The top-level key is the glyph id.

```yaml
my_menu:
  texture: hokaria:gui/my_menu   # assets/hokaria/textures/gui/my_menu.png  (namespace:path, no .png)
  ascent: 13                     # vertical offset, must be <= height
  height: 222                    # rendered height in GUI px; = texture height for 1:1
  #font: minecraft:default       # optional; default from settings.yml Glyphs.default_font
  #permission: nexo.glyph.my_menu  # optional, for chat use
  #placeholders: ["<3"]          # chat shorthands
  #is_emoji: true / tabcomplete: true
```

- Textures over **256x256** must be downscaled or made a Multi-Bitmap Glyph.
- Tags (MiniMessage, work in inventory titles, item names, lore, scoreboards, tab, chat):
  - `<glyph:id>`; `<glyph:id:colorable>` / `:c` to accept preceding colour (otherwise forced white)
  - `<glyph:id:shadow:#AARRGGBB>` / `:s:` shadow colour (1.21.4+); `<glyph:id:2>` / `<glyph:id:2..3>` multi-bitmap parts
  - `<shift:N>` move N px right (negative = left), e.g. `<shift:-8>`
- PlaceholderAPI fallback when a plugin does not parse the tags: `%nexo_<glyphid>%`, `%nexo_shift_-8%`.
  (For glyphs on a non-default font PAPI falls back to the tag.)

Multi-bitmap (big or sprite-sheet textures): add `rows:` and `columns:`; Nexo assigns one char per cell.
In lore (no newlines) print row ranges per line: `"<glyph:big:1..2>"`, `"<glyph:big:3..4>"`.

Reference glyph (one cell of a sheet as its own glyph):
```yaml
icons_sheet: {texture: gui/icons, rows: 2, columns: 5}
icon_star: {reference: icons_sheet, index: 3}
```

Animated glyphs exist too (configuration/glyphs/animated-glyphs) - useful for blinking "NEW" badges.

## Custom GUIs

Nexo renders only the **visual** part: a tall glyph in the inventory title. The inventory, items and clicks come
from a menu plugin (DeluxeMenus, zMenu, your own plugin) or Nexo's own `inventory.yml` for its item browser.
Nexo's own example:
```yaml
customshop:
  texture: required/ui/menu_items
  ascent: 37
  height: 256
# title: <shift:-37><glyph:customshop>  (values depend on how the art sits inside the texture)
```
Alignment helpers: https://nexomc.com/tools/gui-visualizer (drag art over the slot grid, it outputs height,
ascent and title shift), Glypher (Fabric client mod, live preview of title glyphs in vanilla GUIs).

## Items

- Invisible item (clickable buttons over painted art): `Components: { item_model: nexo:empty }` - built into Nexo.
  Any plugin that can set an item model can use `nexo:empty` directly (DeluxeMenus: `item_model: nexo:empty`).
- 1.21.4+: prefer **ItemModels** over CustomModelData (`settings.yml` `Pack.generation.prefer_item_models: true`,
  then `/nexo reset_custom_model_data`, `/nexo reload`). Item model default id is `nexo:<item_id>`.
- 2D icon item from a PNG (good for real item icons inside menus, e.g. 16x16 or 32x32):
```yaml
farm_icon:
  itemname: "<yellow>Ферма"
  material: PAPER
  excludeFromInventory: true     # hide from /nexo inventory, it is a GUI icon
  Pack:
    texture: hokaria:item/gui/farm_icon      # assets/hokaria/textures/item/gui/farm_icon.png
  #Components: {item_model: nexo:farm_icon}  # implicit default on 1.21.4+
```
- Old style CustomModelData: `Pack: { parent_model: item/generated, texture: ..., custom_model_data: 452 }`.
- Icons larger than 16x16 in slots on 1.21.6+: `Pack.oversized_in_gui: true` (or settings `Pack.generation.force_oversized_in_gui`).
- Different model in GUI vs hand: an ItemModel `select` on `display_context` with `when: gui`.
- Item config bits often used for icons: `itemname`, `lore`, `Components.tooltip_display` (1.21.5+, replaces ItemFlags), `template:` to share settings.

## Resource pack

```
plugins/Nexo/pack/
  assets/<namespace>/textures/gui/*.png      GUI backgrounds (glyph textures)
  assets/<namespace>/textures/item/...        item icons
  assets/<namespace>/models/..., items/...    models / item model definitions
  external_packs/                             drop whole .zip/folders here to merge them
```
- Config references drop the `textures/`, `models/` and `.png/.json` parts: `texture: ns:gui/my_menu`.
- Omitted namespace means `minecraft`.
- Hosting `Pack.server.type`: `POLYMATH` (Nexo's host), `SELFHOST` (port + public_address), `LOBFILE`, `S3`, `NONE`.
- Dispatch: `Pack.dispatch.send_pre_join`, `send_on_reload`, `mandatory`.
- Obfuscation `Pack.obfuscation.type: NONE|SIMPLE|FULL` (+ `cache: true`).
- Reload after changes: `/nexo reload all` (regenerates and resends the pack). Players must accept the pack.

## Versions & Bedrock

- Supported: 1.21.4, 1.21.5, 1.21.8, 1.21.10, 1.21.11, 26.1-26.3 (newest Nexo). 1.21.1-1.21.3 only up to Nexo 1.24.
  `item_model` needs 1.21.2+ clients (DeluxeMenus) and Nexo's ItemModel flow targets 1.21.4+.
- Bedrock (Geyser) via the Scaffolding addon: glyph GUI backgrounds are converted automatically (approximate
  alignment, fix in `plugins/Scaffolding/gui.yml` with `offset`, `size: "176px,222px"`, `shift`).
- Nexo also supports native Dialogs (`plugins/Nexo/dialogs/*.yml`, 1.21.6+) - a different kind of menu
  (buttons, text inputs, sliders) that needs no texture tricks; suggest it for forms/settings screens.
