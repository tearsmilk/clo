# Kitchen workstations: cutting board (input grid, tools, result)

A workstation GUI (cutting board, stove, workbench...) has three zones: an input grid the player fills, a
few tool slots, and a result area, plus a "go" button. The art comes from `scripts/kitchen.py`; the example is
`assets/examples/cutting_board/board.json`.

## Layout of the cutting board (user's request)
"5x5 for the food, next to it after one empty slot 3x2 for tools, below that after one empty slot the cut
results". A chest is 9 wide: 5 + 1 + 3 = 9 exactly. The board is 5 rows tall, so "below" cannot mean below the
board (5 + 1 + 1 = 7 rows, a chest has at most 6): the result goes below the tools, with one empty row between.
That fills a **5-row chest (45 slots)** exactly:

| zone | slots | grid |
|------|-------|------|
| board (food) | 0-4, 9-13, 18-22, 27-31, 36-40 | c0-4 r0-4 |
| tools (knife...) | 6, 7, 8, 15, 16, 17 | c6-8 r0-1 |
| result (cut food, on a plate) | 33, 34, 35, 42, 43, 44 | c6-8 r3-4 |
| empty gaps | 5, 14, 23 (column 5 up top), 24, 25, 26 (row 2 on the right) | |
| arrow = "cut" button | 32, 41 | c5, between board and plate |

If the user's numbers do not fit 9 x 6, find the reading that does and say which one you took.

## Look (what makes it read as a kitchen)
- One material per zone and strong value contrast: light beech board, dark walnut case lined with green felt,
  a white plate with a blue band, all on a cool grey stone counter. Stone is cool, woods are warm.
- Slots are drawn like vanilla slots in the material's own tones (shadowed top/left wall, lit bottom/right
  wall): shallow cells cut into the board, felt compartments in the case (with a soft self-cast shadow under
  the far wall). The result is a PLATE, not a compartment tray (user: "it should be like a plate"): a wide
  white brim with a rolled lit edge and a blue band, a sunken well (shadowed far wall, lit near wall) whose
  flat floor holds all 6 slots - no grid on a plate, the whole well is the slot area - glossy streaks on the
  brim and the floor. A plate cannot be round here (an ellipse round 3x2 slots is 76 px wide), so it is a
  rounded platter with a big corner radius.
- Every object is seen from the front-above like the shop buttons: lit far edge and left side, base top
  face, a darker front face (thickness), 1 px outline in the material's darkest tone, and a HARD projected
  shadow on the counter, offset down-right, one tone.
- Volume = thickness, not size (user: "make the board volumetric"): the board is 6 px thick - its front face
  is banded like a rounded edge (base under the lit nose, dark mid, shadow at the counter) with long-grain
  streaks, the top has a 2 px lit bevel band and a highlight along the lit corner, the shadow is offset 3 px.
- A box reads deep when you see INTO it (user: "make the tool place volumetric"): each compartment shows the
  inner face of its far wall as a 3 px strip at the top (dark mid, shadow where it meets the floor), the felt
  gets a contact shadow under that wall and along the left wall, the partitions show their top edges (lit
  nose on the far wall, darker on the side turned away), the walls are thick (5 px front face with grain,
  2 px lit bevel on the rim), and metal fittings sit ON the volume - brass caps folding over the front
  corners, a hasp folding from the rim down the front with its own contact shadow. The strip covers the top
  rows of the slot's item area; items are drawn over it.
- Props stay small next to the slots (user: "the knife is too big"): the knife's blade is about one slot
  long (20 px), 5 px tall - decoration must not compete with the zones.
- Parts that stick out of the window add volume: the board's handle with a hanging hole (left), the chef's
  knife lying on the counter with its handle over the edge (right), the plank sign above the window.
- The counter's front edge sits where the client would write "Inventory" (y 110 for 5 rows), so the label is
  hidden (`hide_inventory_label`), and the vanilla player inventory stays below (`container_panel: false`,
  `draw_player_inventory: false`, `preview_vanilla_under: true`).
- Delicate shading (user: "beautiful, very delicate shading"): wood, stone, felt and ceramic use
  `ramp5(..., soft=1)` (kitchen.SOFT), objects get a selective outline and a soft contact shadow, the board a
  sheen band along the grain, the slot cells gentle walls, the plate a concave well - see "Delicate shading"
  in `references/texture-shading.md`. The knife's steel keeps the contrasty metal ramp.
- Grain and granite are sparse clusters; flat faces stay mostly one tone (`references/texture-shading.md`).
  Check: `python3 scripts/shading.py check out/texture/<id>.png --kit kitchen` (every colour must come from a
  kit ramp, 0 outside).

## Kit parts (`{"type": "kitchen", "part": ...}`)
| part | keys (defaults) | draws |
|------|-----------------|-------|
| `counter` | `y0` (-1), `front_y` (116), `front` (3), `x0`/`x1` (-1/176), `seed` | stone worktop over the container part, lit front edge, front face |
| `board` | `slots` [c, r, w, h] ([0,0,5,5]), `rim` [l, r, t, b] (5,3,5,2), `thick` (6), `handle` (22), `handle_h` (14), `seed` | cutting board with a cell per slot, knife marks, handle with a hole out of the window (canvas `left` >= handle + 2) |
| `tool_case` | `slots` ([6,0,3,2]), `rim` (4), `thick` (5), `wall` (3) | deep walnut tool box: far-wall strip in each compartment, felt with contact shadows, partition tops, brass hasp and corner caps |
| `plate` | `slots` ([6,3,3,2]), `brim` (5), `thick` (3) | white plate: brim with blue band, sunken well = slot area |
| `arrow` | `x`, `y` (window px, top-left of the 6x5 shape) | cream arrow with outline and shadow |
| `knife` | `x` (tip), `y` (spine), `blade` (20), `handle` (14), `bh` (5) | small chef's knife lying on the counter |
| `sign` | `x` (centre, 88), `y`, `text` | light plank sign with burnt-in letters |

Item icons: `kitchen:cutting_board32` - the 32x32 item with volume (the board at 45 deg, 4 px thick sides,
juice groove, hanging hole: 45 deg lines stay clean, a 2:1 iso view breaks into dots at this size; 32x32 item
textures work with `Pack.texture` like 16x16 ones), `kitchen:cutting_board` (16x16 flat), `kitchen:knife`;
sliced food from `item_icons.py`: `item:rounds:carrot`, `item:rounds:tomato:cheese` (seeds from a 2nd ramp).
`preview_items: [{"slot": 10, "icon": "item:tomato", "amount": 3}, ...]` in the spec draws a second preview,
`preview_items.png`, with the menu in use - items never go into the menu config.

## The logic is a plugin, not DeluxeMenus
DeluxeMenus menus cannot take items from the player, so a board the player fills needs a plugin (own Java
plugin, Skript, or a crafting-station plugin whose GUI title can be set). The builder's DeluxeMenus file only
lets you look at the art in game. What the plugin does:
1. Open a 45-slot chest titled with the glyph from the generated DeluxeMenus file
   (`<white><shift:-32><glyph:hokaria_cutting_board>`, or `%nexo_shift_-32%%nexo_hokaria_cutting_board%`).
   Open it from a Nexo furniture interaction (right-click on the placed board) or a command.
2. Allow placing / taking in the board and tool slots; the result slots are take-only; cancel clicks on the
   gaps and on the arrow (shift-click from the player inventory must land on the board, not in the gaps).
3. The arrow (32 / 41): for each board stack with a recipe whose tool is in the tool slots, move the result
   into the result slots (stack, stop when full), maybe damage the tool, play a sound.
4. On close, give back everything left in the board, tool and result slots (or drop it).
Ask the user for the recipes (what turns into what, which tool) before writing that plugin.
