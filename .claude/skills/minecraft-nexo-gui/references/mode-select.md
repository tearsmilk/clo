# Mode select ("Навигатор"): every mode is a window into its world

`scripts/modes.py` draws a mode / server choice the way this user asked for it ("make the mode choice, come up
with an interesting concept that carries the meaning"). Example: `assets/examples/mode_select/modes.json`.

## The user's grid (6-row chest, from their layout screenshot)
| part | slots | grid |
|------|-------|------|
| Blessed (shown as skulls in the layout) | 9-12, 18-21, 27-30, 36-39 | c0-3 r1-4 |
| Farm (shown as redstone) | 14-17, 23-26, 32-35, 41-44 | c5-8 r1-4 |
| gap column | 13, 22, 31, 40 | c4 r1-4: the signpost |
| row 0 | 0-8 | the header plank (НАВИГАТОР) |
| row 5 | 48-50 | "Скоро..." (the old menu's clock button; the layout left row 5 empty, drop it if not wanted) |
The layout screenshot uses placeholder items (skulls, redstone) to mark areas; they are not pictures to draw.
The tooltips (name, lore, colour) come from the user's current menu and go into DeluxeMenus unchanged.

## How the concept was found (repeat it for any new mode)
1. **Read the tooltip as a list of nouns.**
   - Blessed: "Oneblock, pvp, рыбалка, квантовые технологии", plus the name (blessed) and the red name colour.
   - Farm: "добывай ресурсы, выполняй задания, прокачивай уровень, открывай свою лавку", plus the green
     colour.
2. **Turn each noun into an object** that fits in one small scene:

   | from the tooltip | object in the picture |
   |------------------|-----------------------|
   | oneblock | ONE grass block floating in the void |
   | pvp | a sword stuck in that block |
   | рыбалка | a fishing line hanging from the block into the void, with a bobber |
   | квантовые технологии | a cyan orb on an orbit |
   | blessed | a holy beam of light falling onto the block, a gilded frame |
   | danger | a skull keystone |
   | ресурсы | the wheat field |
   | уровень | XP orbs rising from the field |
   | лавка | a market stall, with a dirt path leading to it |
   | the farm | a red barn gable on the frame |
3. **Show the WORLD, not an icon.** The tile is a window you look through. The window's frame is the mode's
   material: blackstone with gold trim for Blessed, oak planks for Farm. One glance tells the mood: the dark
   void at night vs. a sunny day.
4. **Name in the mode's own colour**, the colour of its tooltip name: arcade letters, `ruby` for &c and `mint`
   for &a, on a dark plate under the window.
5. **Tie the menu's own name to an object:** "Навигатор" becomes a signpost in the gap column. It has a
   lantern on top and two arrow boards pointing to the two worlds, with a red mark on the left board and a
   green mark on the right.
6. **What is not playable yet is calm:** "Скоро..." is a low-contrast stone plank with a small clock. It is
   not a third window (`references/pixel-art-craft.md`: contrast and saturation go to what the player can
   use).

## Drawing rules that made it read at 1:1
- **The Minecraft grass block is in 2:1 isometric:**
  - the top diamond has rows 2, 6, ... 22 px wide in 2 px steps;
  - each side column starts right under the diamond;
  - the lit left face and darker right face meet at a front edge (lit pixel + shadow pixel);
  - the grass fringe is uneven, 2-4 px deep;
  - the dirt has pebble clusters.
- **Minecraft cues** say "this is Minecraft" without text: the square sun, flat blocky clouds, stepped hills,
  far-off 2x2 oneblocks of other players.
- **One light (top-left) everywhere:**
  - the sun sits top-left in the farm window;
  - the beam falls on the block's top face;
  - the frame shades the top rows and left column of each picture (`_shade_in`).
- **Each scene keeps one focal object** (the block, the stall) with props around it, all small. The
  windows leave 19 px of slab under them for the name plate.
- **Clean lines:** `pixel_perfect` runs over each gate and the signpost, and the hub header's letter outlines
  are cleaned too.

## Kit parts (`{"type": "modes", "part": ...}`)
| part | keys | draws |
|------|------|-------|
| `gate` | `slots` [c, r, w, h], `kind` blessed / farm, `name`, `seed` | slab + sunk scene window + keystone + name plate |
| `signpost` | `col` (4), `rows` [1, 4] | walnut post, two arrow boards, lantern, shadows on the counter |
| `soon` | `slots` [c, r, w], `text` ("Скоро...") | calm blackstone plank with a gold clock |
Use the hub `backdrop` and the hub `sign` (header) with them. Check the result with
`python3 scripts/shading.py check out/texture/<id>.png --kit modes`.

## Adding a mode
Write a `scene_<name>(img, box, seed)` in `modes.py`, built from the tooltip nouns as above. Add an entry to
`GATES`: (slab ramp, frame trim ramp, arcade palette), plus a keystone if the mode has an emblem. For three
modes in 9 columns use 3x4 gates (c0-2, c3-5, c6-8, no gap column): the scenes get 44 px wide, so keep one
object per scene. Move the signpost to the header or drop it.

## Config notes
- Buttons are invisible items over each 4x4 window. In the game, hovering shows the user's own tooltips.
- `[connect] blessed` / `[connect] farm` need BungeeCord / Velocity server names, so replace them with the
  real ones, or with `[player] server blessed` if a plugin handles it.
- The old navigator opened from the lobby compass: point the compass at the new menu's `open_command`, or
  rename the menu to the old one.
