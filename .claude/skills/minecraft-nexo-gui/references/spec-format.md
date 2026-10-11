# gui_builder.py spec format

All coordinates of buttons/panels are in **slots**: `x` 0-8 (column), `y` 0..rows-1 (row), `w`/`h` in slots.
Paths are relative to the spec file.

## Top level

| key | default | meaning |
|-----|---------|---------|
| `id` | required | glyph id, file names, DeluxeMenus menu name |
| `namespace` | `gui` | pack namespace -> `assets/<ns>/textures/gui/<id>.png` |
| `rows` | 6 | 1-6 chest rows |
| `theme` | `oak` | `vanilla` (exact Minecraft), `oak`, `spruce`, `birch`, `stone`, `cobble`, `nether`, `dark`, `meadow` - textured frame band + calm body; `rustic` - wooden board frame around the window + parchment + maroon wells (pair with `header.style: "sign"`); `royal` - dark slate body, thin gold line, rimmed slot wells (pair with `bracket_tab`, `section_divider`, `hotbar_frame`, `brackets`); or a dict |
| `section_divider` | none | gold bar with a gem between the container rows and the player inventory (covers the client's "Инвентарь" label - use with `hide_inventory_label`). Royal theme: `true` / `{"gem": false}` = the measured kit divider; other themes: `{"gem": "#439950", "color": "#d9893f", "overhang": 4, "brackets": true}` |
| `hotbar_frame` | none | royal theme: `true` = measured gold/red frame; other themes `{"color": "#a83333", "corner": "#d9893f"}` |
| `corner_brackets` | false | gold L brackets on the window corners (royal kit; top ones stick 2px out - needs `canvas` margins >= 2) |
| `royal_ornaments` | none | `true` or `{"banners", "emblem", "rails", "crystals", "meanders": bool}` - the royal kit's outside decoration at measured positions; needs `canvas` `{"left": 40, "right": 40, "top": 17}` |
| `palette` | `endesga32` | shading model: `endesga32` (palette ramps + hue-shifted shading for custom colours), `endesga32-strict` (snap every colour), `none` |
| `theme_overrides` | {} | override single theme colours: `fill` (list), `seam`, `hi`, `hi2`, `sh`, `sh2`, `slot_dk`, `slot_lt`, `slot_in`, `text`, `recess` |
| `header` | none | title plaque, see below. Without it `title` is drawn as plain text at (8,5) |
| `title` | none | plain title text (when no header) |
| `title_text` | none | live text printed after the glyph in the real title (placeholders allowed) |
| `label_case` | `keep` | `upper` turns every label to capitals (Quick-menu look) |
| `panels` | [] | recessed areas under buttons: `{x,y,w,h, color, pad}` - put one under a group of tiles to get dark separator lines |
| `draw_free_slots` | true (false in scenes) | draw normal slots where no button is |
| `slots_visible` | [] | slot indexes to draw as normal slots even if covered/hidden - for real items (player head, armour) |
| `draw_player_inventory` | true | draw the 4 player rows |
| `inventory_label` | `Инвентарь` | preview only: the client itself prints this label at (8, 18r+20) over the art, so it is never baked into the texture |
| `hide_inventory_label` | false | ship `assets/minecraft/lang/{ru_ru,en_us,uk_ua}.json` with `container.inventory: ""` (hides the label in **every** chest menu of the server) - for scenes whose art sits where the label would be |
| `canvas` | {} | `{"left": 30, "right": 30, "top": 17, "bottom": 0}` px of art outside the 176px window (banners, pillars, torches). Texture must stay <= 256x256; the title shift becomes `-8 - left` automatically |
| `container_panel` | true | false = no window panel above the player inventory: the `layers` paint the whole upper part (scene menus). The builder warns and writes `preview_holes.png` if any window pixel stays transparent (vanilla grey would show there) |
| `inventory_panel` | theme | theme name for a separate player-inventory panel (`"vanilla"` keeps it looking like Minecraft under a painted scene) |
| `background` / `window_at` | none | use a ready-made PNG (bought pack) as the texture; `window_at: [x, y]` = vanilla window origin inside it. Turns off panel/slot/inventory drawing and turns on `preview_vanilla_under`. Layers and buttons still apply (relabel with `patch`/`text`/`nameplate`) |
| `preview_vanilla_under` | false | preview draws the vanilla chest under the texture (what shows through in game) |
| `variants` | none | list of dicts with `id`: one menu per entry, `${key}` placeholders anywhere in the spec (+ `${index}`, `${prev_id}`, `${next_id}`, `${prev_label}`, `${next_label}`); output `OUT/<id>/` + merged `OUT/_all/` |
| `variant_defaults` | {} | values shared by all variants (overridden per variant); a default may use other keys, e.g. `"icon_png": "pack/icons/${tex}.png"` with one variant setting its own `icon_png` |
| `hint_glyphs` | false | `true` = our mouse icons, or `{"lmb": "x.png", "rmb": "y.png"}`; Nexo glyphs `<ns>_lmb`/`<ns>_rmb` for lore (`%nexo_<ns>_lmb%` with PlaceholderAPI); the preview tooltip renders them |
| `nexo_items` | [] | real icon items for slots: `{"id": "hokaria_quest_new", "icon": "sprite:quest_new" or "icons/x.png", "name": "<gold>Новый квест"}` -> 16x16 texture + `Nexo/items/<id>_items.yml`; use them with `material: nexo-<id>` in `extra_items` |
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
- `style: bracket_tab` = royal tab across the top edge (96 x 20 at y -10 by default) with '[' ']' gold brackets
  and a shadow; `text` may be "" (blank tab like the reference); text in material lettering (`material`
  steel/gold/..., `size` 1 or 2 - size 2 makes the tab 26 high) or `font: "pixel"`; `width`, `height`, `top`.
- `style: lettering` = only material letters over the window top (`material`, `size`, `y`).
- `style: sign` = rustic plank sign with crown, coins, pennants and crossed arrows (`width`, `height`, `y`, `dx`).
- `font: "material"` + `material` also works for `ribbon` headers (gold letters on a red ribbon).
- `style: ribbon` = cloth ribbon with folded, V-cut tails across the top edge (quest boards, castle scenes):
  `color`, `width` (px, default text + 76), `y` (px from the window top, default `9 - band height`), `size` 1|2,
  `spacing`, `case: "keep"` for mixed case. White text with a dark outline in the ribbon's hue.
- `style: block` = chunky "Minecraft logo" letters (light top, darker bottom third, outline, crack pixels) above
  the window. `size` 3 (default) or 4; size 2 merges letters - avoid. Colours: `top_color`, `bottom_color`, `outline_color`.

## Buttons

| key | default | meaning |
|-----|---------|---------|
| `id` | required | DeluxeMenus item id |
| `x,y,w,h` | w=h=1 | slot rect |
| `style` | `sunburst` | `sunburst`, `gradient` (banded), `flat`, `button` (two-tone body), `pattern`, `image`, `none` (no tile: an invisible clickable area over scene art; only `icon` is drawn, `icon_flip` mirrors it) |
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
| `right_commands` | - | DeluxeMenus `right_click_commands` |
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
| `sprite` | `name`, `x`,`y` or `slot`, `opts`, `flip` | props: `crate` (w,h,color), `arrow` (w,h,color), `sack`, `wheat`, `coin`, `hourglass`, `ledger`, `carrot`, `pumpkin`, `emerald`, `fish`, `check`, `quest_new`, `quest_done`, `quest_locked`, `arrow_gold`, `page`, `crest` |
| `slot_frame` | `slot` or `slot_list`, `color`, `inner`, `outline` | framed highlighted slots for quest steps, rewards, inputs (real items go there) |
| `slot_bar` | `slots: [col,row,w,h]`, `kind` gold/wood/stone/iron, `rim`, `inner`, `well`, `pad` (4) | one metal/wood frame around a group of slots, each slot a dark recessed well - quest rows, reward rows, page navigation |
| `wall` | `color`, `coping`, `seed` | castle wall of staggered stone blocks with per-block tones, chips and a lit cap ledge |
| `planks` | `color`, `seed` | barn wall: vertical boards with a top beam |
| `pillar` | `color` | stone column with capital and base |
| `brazier` | `kind` bowl/torch/lantern, `color` | fire bowl, torch or lantern (put it on a pillar/post top) |
| `banner` | `color`, `trim`, `rod`, `rod_ball` left/right (rod runs on 8px to a gold ball), `tail` point/swallow, `emblem` (sprite name, e.g. `crest`, `wheat`), `folds` swag/vertical, `age` 0..1 (0.5), `torn` 0..3 (1), `seed` | hanging cloth banner on a rod: sagging drape folds, worn lower part, gaps in the gold trim, small tears in the edges and a ragged tip |
| `ribbon` | `color` | a ribbon anywhere (the header style uses the same drawing) |
| `rubble` | `color`, `leaves`, `flowers`, `seed`, `density`, `shape` band/left/right/mound/valley, `round_bottom`, `size` [min,max] radius | pile of outlined boulders with plants on the surface; green `color` = bushes/hedge. Side mounds: `left`/`right`; foreground piles: `round_bottom: true` + `"above": true` |
| `hay` | `color`, `seed` | hay bales with twine - farm scenes |
| `flourish` | `color`, `gem` | symmetric gold ornament with feathered wings, under a title |
| `note` | `color`, `seal` (null = none), `age` 0..1 (0.7), `torn` 0..2 (1), `pin`, `shadow`, `seed` | old parchment: yellowed rim, stains, faded ink, nibbled edges, a torn-off corner, ragged bottom, 1px shadow on the wall |
| `divider` | `color`, `gem` | ornamental line with arrow tips, beads and a centre gem |
| `frame` | `kind`, `inner`, `rim` | empty framed panel (like slot_bar without wells) |
| `card` | `picture` (PNG at box-6 size = 1:1, or `scene:<name>`, `hero` icon), `label` | rustic picture card with a ribbon nameplate |
| `grid_frame` | `slots: [c,r,w,h]` | rustic frame around a block of well slots (show them with `slots_visible`) |
| `bookmark` | `x`, `y` (window px), `icon` (icons16 name), `w`, `h` | red ribbon tab sticking out of the window side, tucked under the parchment |
| `patch` | `box`, `from_x` | wipe text in a background: each row filled with the colour at column `from_x` |
| `text` | `x` (centre), `y`, `text`, `material` (name or 5 colours), `scale`, `condensed` (`"bold"` small) | material lettering anywhere |
| `shop` | `part` + part keys (below) | market-stall shop kit (`scripts/shop.py`, `references/shop-flow.md`) |

Shop kit parts (`{"type": "shop", "part": ...}`; spec `canvas` 40/40/34/0, `theme: "vanilla"`, `draw_free_slots: false`):

| part | keys | draws |
|------|------|-------|
| `stall` | `sign`, `hanging` (vertical sign text or null), `seed`, `colors` (awning stripes, default red/white), `sill_y` | wall of 18px planks on the slot columns, staggered plank ends, perspective awning with scallops, green sign, vines, eave brackets, hanging sign |
| `window` | `slots`, `poster` (thin text, `\n` for 2 lines), `items` (16px icon sources, 2 per shelf), `shelves`, `seed` | glass shop window with streaks and shelves over a block of slots |
| `wells` | `slots`, `frame` (true), `icons` (baked into the wells row by row) | framed grid of recessed item wells |
| `group` | `slots: [c, r, n]`, `color` red/green/wood/gold, `glyph` minus/plus | coloured frame around n wells in a row (-/+ amount, buy row) |
| `button` | `slots`, `color`, `text` | bevelled button (outline, light top, 2px lip, drop shadow, two-tone letters) |
| `banner` | `x` (centre), `y`, `text`, `w` | parchment banner with torn edges (screen title) |
| `badge` | `slot`, `text`, `color` | small counter plate; put an invisible item with `dynamic_amount` on it to show a live number |
| `icon` | `slot` / `slot_list`, `icon` | any 16px icon painted into the texture (e.g. `shop:home`) |
| `well` | `slot` / `slot_list` | single wells |

Safe kit parts (`{"type": "safe", "part": ...}`; pair with `theme: "steel"` - brushed steel window, steel
slot wells, a light band under the client's "Inventory" label; window px `x`/`y`/`box`, slots `[col, row, ...]`):

| part | keys | draws |
|------|------|-------|
| `door` | `box` [x0,y0,x1,y1] (4,4,171,121) | raised steel door with heavy bevel, engraved groove, rivets |
| `hinges` | `x` (-2), `ys`, `h` (26), `leaf` (12; 3 = frame only, for storage screens) | knuckle + leaf screwed to the door |
| `bolts` | `x` (171), `ys`, `length` (10) | locking bolts sticking out of the right side (needs canvas `right` >= length - 3) |
| `bolt_slots` | `x`, `ys` | retracted bolt slots in the frame |
| `open_door` | `x` (-3, hinge edge), `y0`/`y1` (the closed door's top/bottom), `width` (44), `grow` (7), `thick` (9), `top_thick` (3), `side` left/right | the door swung open, in perspective, with volume: thick lit edge with the bolts coming out of it, a top face, a raised plug panel with shadow, brass mechanism, rods following the perspective; `side: "right"` mirrors it for hinges on the right; put it before the hinges |
| `case` | `rows` | steel box over the container part only (x 0..175, y 0..17+18*rows) - the vanilla player inventory stays below; spec `container_panel: false`, `draw_player_inventory: false`, `preview_vanilla_under: true` |
| `box3d` | `h` (126), `side` (5), `top` (5) | volume: top face (lit) and left face (shadow) receding up-left - the box seen from the front-left |
| `door_inset` | `box` | plain door set into the front with a dark seam all round |
| `dial` | `x`, `y`, `r` | combination dial: chrome ring, black scale with ticks, knob, index mark |
| `handle` | `x`, `y`, `length`, `angle`, `spokes` (3) | classic 3-spoke chrome handle with ball ends and a big hub; one menu per `angle` fakes turning |
| `hinge_blocks` | `x` (176 = right edge), `ys`, `h`, `side`, `leaf` (false when the door is open) | heavy hinges: leaf on the door edge, knuckle and pin past the body side |
| `feet` | `pts` [[x, y]...], `w`, `h` | small dark feet |
| `wheel` (+`angle`), `turn_arrows`, `lamps` | see safe.py | spoked wheel handle, curved clockwise arrows, painted progress lamps |
| `nameplate` | `x` (centre), `y`, `text`, `w` | brass plate with engraved letters |
| `plate` | `x` (centre), `y`, `text` (thin, `\n`) | small brass instruction plate (warns if wider than 50 px) |
| `display` | `slots: [c, r, n]`, `lamps` (columns), `lock` (column) | sunken LCD with lamp sockets centred in slots; lit lamps are items (`safe:lamp`) |
| `keypad` | `slots: [c, r]`, `labels` (3 per row), `colors` {index: red/green}, `glyphs` {index: close/ok} | 16x16 keys in the slots' item areas on a sunken plate |
| `wheel` | `x`, `y` (centre), `r`, `spokes` | spoked handle wheel with brass hub and knobs, shadow on the door |
| `keyhole` | `x`, `y` | brass escutcheon with keyhole |
| `recess` | `box` | sunken area (e.g. the inside of an open safe around the slot grid) |

16px icon sources accepted wherever an icon or `preview` is read: PNG path, `sprite:<name>`, `item:<recipe>:<ramp>`
(`scripts/item_icons.py`), `shop:back|next|home|close|ok[:color]`, `shop:alert`, `safe:lamp[:red|amber]`.
Buttons take `dm: {...}` for raw DeluxeMenus keys (requirements, `dynamic_amount`, `priority`); the spec takes
`on_open: [...]` (DeluxeMenus `open_commands`, actions when the menu opens) and `dm_menu: {...}` (raw menu-level
keys such as `open_requirement`).
| `nameplate` | `x` (centre), `y`, `text`, `min_w` | green ribbon label (rustic) |

Any layer takes `"if": "${var}"` - skipped when the value is empty (variants).
| `brackets` | `size` (16), `t` (5) | gold L brackets on the 4 corners of the box - put the box 2px outside the window or a section |
| `bracket` | `corner` tl/tr/bl/br, `t` | one bracket |
| `meander` | `color` | gold key strip (squares, dots, bars) - beside a title tab |
| `rail` | `color`, `gem_color` | thin vertical gold rail with hooked ends and a gem - beside a window side |
| `crystals` | `color`, `side` left/right, `seed` | fan of golden crystal shards pointing away from the window, at the divider level |
| `streamer` | `color`, `side` | red ribbon tail with a V cut running out under the crystals |
| `gem` | `color` | faceted rhombus gem |

Box layers take `"flip": true` to mirror them. `"above": true` paints a layer after the player-inventory panel and
the buttons, so props come to the foreground (stones over the panel's corners). The builder warns if such a layer
touches the player's slots (keep it on the panel border: y < 18*rows + 30, x < 7 or x > 168). Boxes may have negative x/y or reach past 176 - that is the
`canvas` margin. Order matters: layers are painted in list order (wall first, props, then piles in front).

Button icons can be sprites: `"icon": "sprite:hourglass"`.
`extra_items[].preview: "sprite:carrot"` (or a PNG) draws a stand-in item with its amount in preview.png only, so
the user sees how slots with real items will look; it is not written to the DeluxeMenus file.
See `assets/examples/market_menu/spec.json` (market stall with 4 order steps, arrows, reward slot, hand-in button),
`assets/examples/quest_menu/spec.json` (castle quest board: wall wider than the window, pillars with fire, banners,
ribbon title, gold slot bars with real quest-card items, rubble with plants, vanilla player inventory) and
`assets/examples/quest_menu_farm/spec.json` (the same board as a barn: planks, lanterns, wheat banners, hedge, hay),
`assets/examples/royal_chest/spec.json` (6-row royal chest: slate + gold, bracket title tab with steel letters,
crest banners, rails, crystals and streamers at the gem divider, framed hotbar).

## Material lettering (pixfont.draw_material_text)

Big titles in a material instead of flat pixel text: `draw_material_text(img, x, y, "Сундук", "gold", scale=2)`.
Each letter is a light upper block over a mid-tone lower block, sheen lines, a dark 2px base and a 1px near-black
outline with dark counters; corners are cut. Materials: `steel`, `gold`, `wood`, `emerald`, `crimson`, `stone`,
`snow` or a tuple (outline, dark, mid, light, sheen). `outline=False` = soft engraved text, `condensed=True` =
narrower letters when space is tight. Scale 2 = 10x14 capitals (Latin + Cyrillic); keep `gap` >= 2.
