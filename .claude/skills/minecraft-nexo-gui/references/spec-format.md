# gui_builder.py spec format

All coordinates of buttons/panels are in **slots**: `x` 0-8 (column), `y` 0..rows-1 (row), `w`/`h` in slots.
Paths are relative to the spec file.

## Top level

| key | default | meaning |
|-----|---------|---------|
| `id` | required | glyph id, file names, DeluxeMenus menu name |
| `namespace` | `gui` | pack namespace -> `assets/<ns>/textures/gui/<id>.png` |
| `rows` | 6 | 1-6 chest rows |
| `theme` | `oak` | `vanilla` (exact Minecraft), `oak`, `spruce`, `birch`, `stone`, `cobble`, `nether`, `dark`, `meadow` - textured frame band + calm body; or a dict |
| `palette` | `endesga32` | shading model: `endesga32` (palette ramps + hue-shifted shading for custom colours), `endesga32-strict` (snap every colour), `none` |
| `theme_overrides` | {} | override single theme colours: `fill` (list), `seam`, `hi`, `hi2`, `sh`, `sh2`, `slot_dk`, `slot_lt`, `slot_in`, `text`, `recess` |
| `header` | none | title plaque, see below. Without it `title` is drawn as plain text at (8,5) |
| `title` | none | plain title text (when no header) |
| `title_text` | none | live text printed after the glyph in the real title (placeholders allowed) |
| `label_case` | `keep` | `upper` turns every label to capitals (Quick-menu look) |
| `panels` | [] | recessed areas under buttons: `{x,y,w,h, color, pad}` - put one under a group of tiles to get dark separator lines |
| `draw_free_slots` | true | draw normal slots where no button is |
| `slots_visible` | [] | slot indexes to draw as normal slots even if covered/hidden - for real items (player head, armour) |
| `draw_player_inventory` | true | draw the 4 player rows + "Инвентарь" label |
| `inventory_label` | `Инвентарь` | text above the player inventory (`""` to hide) |
| `open_commands` | [id] | DeluxeMenus open commands |
| `extra_items` | [] | raw DeluxeMenus items, e.g. `{"id":"head","material":"head-%player_name%","slot":10}` |
| `ascent_nudge` / `shift_nudge` | 0 | 1px corrections after testing in game |
| `icon_style` | none | stylize every icon: `{"extrude": 1, "sparkle": false, "colors": 10, "outline": "auto", "light": true, "palette": ["#hex", ...]}` (see pixelstyle.py) |
| `decor` | [] | pixel decorations in px coords on top of everything (y may be negative = above the window): `{"type": "sparkle"\|"sparkle_small"\|"star"\|"cloud"\|"moon"\|"leaf", "x": 20, "y": -14, "color": "#hex"}` |
| `preview_tooltip` | none | button id to show hovered with its tooltip in preview.png |
| `preview_background` | none | image behind the preview (blurred, dimmed) |

### header
`{"text": "Меню", "size": 1|2, "style": "plaque"|"tab"|"text", "color": "#4A4A4A", "text_color": "#F0F0F0", "rivets": true, "case": "keep"}`
- `size: 2` = double-size letters on a tab that sticks out ~10px above the window (texture gets taller, ascent rises accordingly - handled automatically).
- `plaque` (size 1) = small plate inside the 17px top strip with rivets left/right.
- `style: block` + `depth: 3` (+ `side_color`) extrudes the letters into a 3D slab like Redstone-Labs logos.
- `style: block` = chunky "Minecraft logo" letters (light top, darker bottom third, outline, crack pixels) above
  the window. `size` 3 (default) or 4; size 2 merges letters - avoid. Colours: `top_color`, `bottom_color`, `outline_color`.

## Buttons

| key | default | meaning |
|-----|---------|---------|
| `id` | required | DeluxeMenus item id |
| `x,y,w,h` | w=h=1 | slot rect |
| `style` | `sunburst` | `sunburst`, `gradient` (banded), `flat`, `button` (two-tone body), `pattern`, `image` |
| `color` | `#5DAA3A` | base colour (also tints frame, plaque) |
| `pattern` | `noise` | for `style: pattern`: `planks`/`planks_h`, `planks_v`, `bricks`, `cobble`/`stone`, `grass`, `meadow` (grass + flowers), `cloth`, `dirt`/`noise`, `sky`, `checker`, `stripes`, `dots` |
| `image` | - | for `style: image`: illustration that covers the tile (centre-cropped, posterized to `colors`, default 48) |
| `icon` | - | transparent PNG, auto-fitted with a hard alpha edge |
| `icon_size` | auto | max icon side in px |
| `icon_frame` | false | draw a bevelled box behind the icon (`icon_frame_color`) |
| `label` | - | text; `\n` for two lines (e.g. `"Боевой\nПропуск"`) |
| `label_style` | `outline` | `outline` (white + coloured outline, 2px spacing when it fits), `shadow` (Minecraft text shadow), `plaque` (dark rounded plate), `bar` (full-width band), `wood` (plank plate with nails), `stone` (stone plate) |
| `label_pos` | `bottom` | `bottom` or `top` |
| `label_color` / `plaque_color` | white / derived | |
| `frame` | - | colour of a 1px inner frame instead of the bevel (card look) |
| `outline` | derived | outer 1px outline (default: dark, cooler shade of `color`) |
| `inset` | 1 | px kept free on each side; 0 makes tiles touch |
| `disabled` | false | greyscale background + the icon redrawn as orange line-art (locked / coming soon) |
| `icon_style` | - | per-button override of the top-level `icon_style` |
| `sparkle` | false | add sparkles to this icon (rare / special) |
| `name`, `lore` | label / - | DeluxeMenus display name & lore (legacy `&` codes) |
| `commands` | - | DeluxeMenus `left_click_commands` |
| `material` | invisible | set e.g. `nexo-farm_icon` to show a real item instead of `PAPER` + `item_model: nexo:empty` |
| `hide_tooltip` | false | no tooltip (pure decoration) |

Label fit (pixel font, 1px spacing): a 3-wide button holds ~8 capitals / ~9 lowercase letters on one line,
a 2-wide ~5, a 1-wide none - use two lines or a tooltip. The builder stops with an error instead of
squeezing letters.

## Scene layers (free-form art, like a market stall or a workshop)

`layers` is a list drawn after the panel and before buttons (`"above": true` draws after buttons). Boxes are
`"slots": [col,row,w,h]` (+ `pad`) or `"box": [x,y,w,h]` in window pixels.

| type | keys | use |
|------|------|-----|
| `rect` | `color`, `pattern`, `outline`, `bevel` | grass ground, wooden walls, cloth, counters |
| `awning` | `colors` (stripe colours), `stripe` px, `scallop` px | striped market awning with rail and wavy edge |
| `post` | `color` | wooden posts/pillars |
| `image` | `path`, `colors` | an illustration covering the box |
| `sprite` | `name`, `x`,`y` or `slot`, `opts` | props: `crate` (w,h,color), `arrow` (w,h,color), `sack`, `wheat`, `coin`, `hourglass`, `ledger`, `carrot`, `pumpkin`, `emerald`, `fish`, `check` |
| `slot_frame` | `slot` or `slot_list`, `color`, `inner`, `outline` | framed highlighted slots for quest steps, rewards, inputs (real items go there) |

Button icons can be sprites: `"icon": "sprite:hourglass"`.
`extra_items[].preview: "sprite:carrot"` (or a PNG) draws a stand-in item with its amount in preview.png only, so
the user sees how slots with real items will look; it is not written to the DeluxeMenus file.
See `assets/examples/market_menu/spec.json` (market stall with 4 order steps, arrows, reward slot, hand-in button).
