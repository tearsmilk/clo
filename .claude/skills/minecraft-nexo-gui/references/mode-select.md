# Mode select ("Навигатор"): a star chart with illustrated mode cards, built from parts

`scripts/modes.py` draws a mode / server choice the way this user asked for it: "make the mode choice, come
up with an interesting concept that carries the meaning". The first version had small pictures in thick
frames on the slate counter, and the user said "looks not great, you can do better". Example:
`assets/examples/mode_select/modes.json`.

## The user's grid (6-row chest, from their layout screenshot)
| part | slots | grid |
|------|-------|------|
| Blessed (shown as skulls in the layout) | 9-12, 18-21, 27-30, 36-39 | c0-3 r1-4 |
| Farm (shown as redstone) | 14-17, 23-26, 32-35, 41-44 | c5-8 r1-4 |
| gap column | 13, 22, 31, 40 | c4 r1-4: the compass rose |
| row 0 | 0-8 | the title plaque (НАВИГАТОР) |
| row 5 | 48-50 | "Скоро..." (the old menu's clock button; the layout left row 5 empty, drop it if not wanted) |
- The layout screenshot uses placeholder items (skulls, redstone) to mark areas. They are not pictures to draw.
- The tooltips (name, lore, colour) come from the user's current menu and go into DeluxeMenus unchanged.

## What made the second version better (keep doing it)
1. **The menu's name is the setting.** "Навигатор" became a navigator's star chart:
   - navy paper with faint dashed latitude / longitude lines;
   - constellations;
   - a gold double border with ticks;
   - a gold compass rose in the gap column, with arrowheads toward both cards and a dashed meridian.

   The background is muted (low contrast), so the cards carry the colour and contrast.
2. **The picture fills the card.**
   - The card's frame is only 3 px (dark inner line + trim fillet). Thick slab frames ate half of each
     window.
   - The name goes on a ribbon across the bottom edge, tails folded behind, sitting half on the frame, so
     it takes no picture room.
3. **Three depths in every scene**:
   - far: small, muted, hazy;
   - middle: the main object;
   - near: big, saturated, overlapping.

   For example, Farm has a far forest and barn, then the stall and quest board, then big wheat stalks in
   front.
4. **Perspective instead of stripes.** The field's furrows radiate from a vanishing point on the horizon, and
   the far rows melt into one hazy tone. The path narrows toward the stall. Horizontal stripes read as a
   flag, not a field.
5. **Every noun of the tooltip is an object:**

   | from the tooltip | object |
   |------------------|--------|
   | oneblock | one floating grass block, with dirt and roots hanging under it |
   | pvp | a sword stuck in it |
   | рыбалка | a rod on the block with a line into the void and a bobber |
   | квантовые технологии | a glowing cube on two orbits with electrons (an atom) |
   | blessed | a holy beam with god rays, a gilded frame with gem bosses |
   | danger | a wither-skull keystone with violet eyes |
   | ресурсы | the wheat field |
   | задания | a quest board with notes and a floating "!" |
   | уровень | XP orbs rising |
   | лавка | a market stall with goods and a coin sign, a path leading to it |
   | the farm | barn, silo, an oak frame with leaves on the corners, a wheat-sheaf keystone |
6. **Mode colours from the tooltips**: a crimson ribbon for Blessed (&c), a green one for Farm (&a), gold
   arcade letters on both.
7. **"Скоро..." is uncharted territory:** a dark plaque with a dashed border, a dim clock and dim letters. It
   is calm because there is nothing to click into yet.
8. **Details that read at 1:1 (each fixed after looking at a zoom):**
   - Keep a small object off the scene edge. The atom was clipped by the frame and read as a fish.
   - A 1 px rod disappears: make it 2 px at the grip.
   - Small ribbon tails behind the title read as red blocks, so they were dropped.
   - The ribbon must not hide the near-depth details. It was moved down onto the frame edge.

## Version 3: HD, a scroll that breaks the frame, a new title (current example)
The user asked for "32x32, detailed and beautiful", "do something with the tile behind - it may go beyond the
frame" and "the title is not pretty, change its style". All three became one spec, `"hd": 2` (see
`references/gui-geometry.md`, "HD menus"):
- **HD scenes** (`modes_hd.py`, 124x120 each, drawn natively):
  - Blessed:
    - a 56 px grass block: grass fringe with drips, dirt pebbles, stones, blades and flowers on the top;
    - a lit spot where the beam lands, dirt stalactites and roots underneath;
    - a chest on the top;
    - a sword with a fuller, curved guard, gem and wrapped grip;
    - a rod with a reel, the line sagging to a bobber;
    - a cube with panel lines on three orbits with electrons;
    - three far islands, one with a tree; god rays and motes in the beam.
  - Farm:
    - the square sun, flat clouds, hazy mountains, a tree line;
    - a gambrel-roof barn with shingles, a hay loft and X doors; a ribbed silo; a fence;
    - furrows in perspective;
    - a stony path to a stall with apples, carrots and bread in crates, a coin sign and a lantern; a barrel;
    - a quest board with notes and a "!";
    - pumpkins, two chickens, XP orbs;
    - big wheat stalks with grains, awns and leaves.
- **The tile behind goes beyond the frame:** the star chart is a scroll unrolled between two wooden rods with
  gold caps. The rods stick out 16 GUI px past the window on both sides. The paper has a slowly wandering
  deckle edge past the window (no random 1 px nubs, the jaggy check flags those) and curls into each rod.
  Engraved ship and sea-serpent doodles sit in the bottom corners.
- **Title: written on the chart, the way old maps name themselves** (`title` part, `title_inlay`):
  - Letters: bold capitals (`lettering.chunky`, scale 3) - a lighter top edge, the last row of every stroke
    darker (the cutting board sign's lettering the user pointed at).
  - The ink is the border's muted gold (GOLD 3 / 2 / 1) with a faint 1 px shadow, no bright highlight, no dark
    outline. The user: "make the text darker so it is part of the map" - bright gold read as a label stuck
    on top.
  - The chart's top double border runs through the title's middle and stops in gold diamonds either side,
    with the grid and stars cleared under the letters.
  - The user's verdicts on the way:
    - volumetric letters standing over the top rod: "why will it just hang there";
    - a wooden plank sign under the rod: "no wooden background, place it on the paper nicely";
    - bright gold letters on the paper: "darker, so it is part of the map".

    So the title belongs on the paper, not floating and not on a separate plate.
  - `{"part": "title", "style": "volume"}` still gives the floating gold letters, and `modes_hd.sign()` the
    plank, if another menu wants them.
- **Cards:** a 10 px frame (textured material band, 2 px trim fillet, dark line). Blessed has faceted gold
  bosses with ruby gems and a 21x20 wither skull with glowing sockets. Farm has leaf sprays on the corners
  and a fanned wheat sheaf.
- **The 4x4 card is cut into 4 glyph tiles** (404x472 -> 256 px tiles), joined in the title with measured
  shifts. All 39 parts export with `--layers`, and Aseprite flattens the `.aseprite` back to the exact
  texture.
- Name ribbons on the cards were removed at the user's request ("not needed": the picture and the tooltip
  name the mode). `gate` draws one only when a `name` is given (1x kit).

## Built from parts
Every scene is a list of parts, bottom to top. Each part is drawn on its own transparent canvas and kept as
a tight sprite with its offset.

| scene | parts |
|-------|-------|
| `blessed_parts()` (1x and HD) | void (nebula), stars, far_islands, god_rays, beam, quantum, island, sword, fishing |
| `farm_parts()` 1x | sky, sun, clouds, forest, barn, meadow, field, path, stall (casts a shadow on the field), quest_board, xp, wheat_front |
| `farm_parts()` HD | sky, sun, clouds, mountains, forest, barn, field, fence, path, quest_board, pumpkins, barrel, stall, chickens, xp, wheat_front |

- `compose(items, img, ox, oy, clip)` pastes the parts in order.
  - A part with `shadow` darkens what is under its lower rows in that surface's own ramp, so the shadow
    follows the part when it moves.
- A spec moves or hides parts per card: `"scene": {"stall": {"x": 30, "y": 8}, "xp": {"dx": -4}, "barn": null}`.
- `python3 scripts/modes.py parts OUT/` (1x) or `python3 scripts/modes_hd.py parts OUT/` (HD) exports, per
  scene:
  - every part as `NN_part.png` + `layers.json` (name, file, x, y) + `_sheet.png`;
  - `<scene>.png`, rebuilt FROM the exported PNGs (asserted equal to the drawn scene);
  - `<scene>.aseprite` with one layer per part (shadows baked into their part's layer).
- `gui_builder.py spec.json OUT/ --layers` splits the WHOLE menu the same way. Every spec layer, and every
  part a kit marks inside it (`layers.mark`), becomes a layer:
  - for this menu, 35 layers: chart, card, 9 + 12 scene parts, frame, corners, keystone, ribbon, compass,
    soon, title;
  - `OUT/layers/` + `OUT/<id>.aseprite`;
  - the builder warns if the parts do not rebuild the texture exactly.
- The `.aseprite` writer (`layers.write_aseprite`) needs no Aseprite. It was checked with a real headless
  Aseprite build: `aseprite -b file.aseprite --save-as flat.png` gives back the exact texture, and
  `--list-layers` shows every part by name.
- Use the parts:
  - give one part to an artist to repaint (same size and position, then drop it back into `OUT/layers/`
    and compose);
  - rearrange a scene without touching code;
  - reuse parts in other menus (the island, the stall, the compass).

## Kit parts (`{"type": "modes", "part": ...}`)
| part | keys | draws |
|------|------|-------|
| `chart` | `front_y` (127), `seed` | the star-chart backdrop with its lit front edge (covers "Inventory") |
| `gate` | `slots` [c, r, w, h], `kind` blessed / farm, `name`, `seed`, `scene` | card + scene from parts + frame + corners + keystone + ribbon |
| `compass` | `col` (4), `rows` [1, 4] | gold compass rose with a red north tip, meridian, arrowheads |
| `title` | `text`, `x` (88), `y` (-7) | gold-framed navy plaque with gold material letters |
| `soon` | `slots` [c, r, w], `text` | dark dashed plaque, dim clock, dim letters |
Check: `python3 scripts/shading.py check out/texture/<id>.png --kit modes`.

## Adding a mode
1. Write `<name>_parts(W, H, seed)` with `Parts.add(name, draw)`. Turn the tooltip nouns into objects and
   give the scene three depths.
2. Register it in `SCENES` and `CARDS`: slab ramp, trim ramp, ribbon ramp, letter palette. Add a keystone.
3. For three modes in 9 columns use 3x4 cards (c0-2, c3-5, c6-8). Move the compass into the title row.

## Config notes
- The buttons are invisible items over each 4x4 card. Hovering shows the user's own tooltips.
- `[connect] blessed` / `[connect] farm` need the real BungeeCord / Velocity server names. Use
  `[player] server blessed` instead if a plugin does the switching.
- The old navigator opened from the lobby compass. Point the compass at this menu's `open_command`, or rename
  the menu to the old one.
