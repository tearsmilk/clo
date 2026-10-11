# Safe: turn-the-handle lock + storage (steel kit)

Example: `assets/examples/safe/` - `lock.json` (classic safe front, `/safe`), `storage.json` (the safe open,
54 slots, skin for a vault plugin). Alternative: `code_lock.json` + `pin.json` (keypad with a 4-digit code).
Kit: `scripts/safe.py`, `theme: "steel"`, layers `{"type": "safe", ...}` (keys in `references/spec-format.md`).

## Look (from the user's photo of a real safe)
- Only the safe is drawn: a steel box over the container part of the window (`case`), the vanilla player
  inventory stays below (it cannot be removed - the client always draws it; we only leave it out of the
  texture: `container_panel: false`, `draw_player_inventory: false`, `preview_vanilla_under: true`).
- Volume: top face and left face (`box3d`), heavy hinges whose pins stick out past the right side
  (`hinge_blocks`), the nameplate on the top edge. Volume = depth, not size. No feet: they land on the vanilla
  inventory panel under the safe and look stuck on (user feedback).
- Door set into the front with a dark seam (`door_inset`), a combination dial on top (`dial`), a big 3-spoke
  chrome handle with ball ends below (`handle`). Keep the handle's reach clear of the dial at every angle.

## Turning the handle (no code)
A texture cannot rotate inside a menu, so every handle angle is its own menu: `lock.json` has `variants`
0 / 40 / 80 deg -> menus `hokaria_safe_lock_0/_1/_2`. The handle is one invisible button over its slots
(c2-c6, r1-r5); a click plays a sound and opens the next angle, the last click plays the door sound, closes
and opens the vault (`[player] pv 1` for PlayerVaults - replace with your plugin's command).
Turning menus reopen instantly; there is no progress indicator on purpose (the user wanted just the handle).

## The open safe (storage)
`open_door` with `side: "right"` (hinges on the right like the photo): the door swung out in perspective -
same height as the closed door, thick edge with the bolts coming out of it, raised plug, mechanism and rods;
the hinges are the SAME as on the closed screen (leaf on the frame x 170..175, knuckle x 176..183) and the
open door hangs right off the knuckle (`x: -8` -> hinge edge at x 183) - if the hinge or the distance changes
between the two screens, players see the door jump. A hinge also needs its door leaf, or door and hinge read
as two separate things: closed - `door_strap: 20` runs from the knuckle across the seam onto the door with two
screws; open - `hinge_ys` draws the same straps on the open door's face at the hinge edge. Bolts only on the door - not also on the body.
`box3d` draws a 2 px dark base strip under the safe that separates it from the vanilla inventory.
Canvas `{"left": 8, "right": 66, "top": 8, "bottom": 0}` -> texture 250x230.
DeluxeMenus cannot hold items: use the `menu_title` from `DeluxeMenus/gui_menus/hokaria_safe.yml` as the
inventory title of the vault plugin (PlayerVaults, AxVaults...); PlaceholderAPI form in the file's comment.

## Code lock (alternative)
Keypad on the door, LCD with lamp sockets; DeluxeMenus meta + regex requirements:
- on open `[meta] set code STRING -`; digit `[meta] set code STRING %deluxemenus_meta_code_STRING_-%7` with
  requirement `regex matches` `^-[0-9]{0,3}$`; lamp n is an item with `view_requirement` regex `^-[0-9]{n,}$`;
- OK compares with `%deluxemenus_meta_safe_pin_STRING_-0000%`; `/safe_pin` (open_requirement `has meta
  safe_unlocked`) saves a new code. The same pattern makes any numeric input.
