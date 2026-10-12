# Main menu in the house style (hub kit)

`scripts/hub.py` draws a main menu (bento layout of destinations) the way this user's menus look: every
destination is a raised SLAB of its own material lying on a slate counter, with a volumetric picture and a
label plaque. Example: `assets/examples/main_menu/menu.json` (rebuilt from the user's reference menu).

## Layout of the reference (measured, 6-row chest)
| tile | slots | material / picture |
|------|-------|--------------------|
| Боевой пропуск | c0-2 r0-3 | olive leather with stitching, gold medallion with a sword, coins |
| Профиль | c3-5 r0-4 | maple planks, picture frame on a nail round slot 22 - the player's OWN head item shows in it |
| Выбор сервера | c6-8 r0-3 | purple deepslate, obsidian nether portal with a swirled surface, sparks |
| Магазин | c0-2 r4-5 | green velvet, market chest with a striped lid, sparkles |
| Вики | c6-8 r4 | blue book cloth, open book + label |
| Настройки | c3-5 r5 | brushed steel, label |
| Discord / YouTube / TikTok | slots 51 / 52 / 53 | raised keys in the brand colour with a white logo |
Header: walnut plank with gold "МЕНЮ" (material lettering) sticking out above the window.

To measure a reference: sample the colour in the middle of each slot (window found from its dark border,
scale = border width / 176) - neighbouring slots of one tile share the colour, so the tile boxes fall out.

## House style for menus (what makes it "ours")
- Slabs, not flat tiles: each tile is a slab 1 px inside its slots (2 px gaps between tiles), 3 px front
  face, selective outline, soft contact shadow on the counter, 2 px lit bevel on the far / left edge.
- One material per destination, shaded with the soft ramps (delicate shading); metal parts (gold, steel)
  keep contrasty ramps. Material textures are sparse clusters: leather pebbles + stitches, plank seams +
  grain + varnish sheen, stone chips + cracks with a lit lip, velvet sheen, cloth threads, brushed steel.
- Pictures are objects with volume lying ON the slab and casting shadows onto it: a medallion (torus-lit
  ring, sunken enamel centre with the ring's shadow and a reflection, embossed sword), coins (face + edge),
  a portrait hanging from a nail by a cord, a portal frame with its surface sunk inside, a chest, a book.
- Labels: tall tiles get a dark plaque (raised, brass nails) at the bottom; one-row tiles get light raised
  letters right on the slab (dark letters cut into blue or steel do not read at 1:1). A plaque keeps >= 3 px
  of slab round it; when the text does not fit, it switches to the narrow face (`pixfont` `narrow=True`:
  4 px letters, "Настройки" = 45 px instead of 53).
- The counter's front edge covers the client's "Inventory" line (y 128 for 6 rows): `hide_inventory_label`.

## Player head in the profile
DeluxeMenus shows the viewer's head with `material: head-%player_name%`. The profile button covers its whole
tile, the head is an extra item in slot 22 with `priority: 0`, the button gets `dm: {"priority": 1}` - the
lower number wins the shared slot, so the head shows and both open the profile. `preview: "hub:head"` draws a
generic head in preview.png only.

## Kit parts (`{"type": "hub", "part": ...}`)
| part | keys | draws |
|------|------|-------|
| `backdrop` | `front_y` (127), `front` (3), `seed` | slate counter over the container part |
| `sign` | `x` (88), `y`, `text` | walnut header plank with gold letters (canvas `top` >= -y) |
| `tile` | `slots` [c, r, w, h], `material` (leather, planks, stone, velvet, cloth, steel), `label` (`\n`), `art` (medallion, portrait, portal, chest, book), `narrow`, `head_slot`, `seed` | slab + picture + plaque / letters |
| `key` | `slot`, `brand` (discord, youtube, tiktok) | 1x1 social key |
Check: `python3 scripts/shading.py check out/texture/<id>.png --kit hub` - only the three logo colours
(white, TikTok cyan / pink) are outside the kit ramps.
