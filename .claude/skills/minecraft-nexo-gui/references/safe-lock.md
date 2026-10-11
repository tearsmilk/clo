# Safe: code lock + storage (steel kit)

Example: `assets/examples/safe/` - `lock.json` (door with keypad, `/safe`), `pin.json` (same door, sets a new
code, `/safe_pin`), `storage.json` (54-slot steel skin for a vault plugin). Kit: `scripts/safe.py`,
`theme: "steel"`, layers `{"type": "safe", ...}` (keys in `references/spec-format.md`).

## Layout (6 rows)
| zone | slots | what |
|------|-------|------|
| title band y 0..16 | - | brass nameplate (СЕЙФ / НОВЫЙ КОД) |
| row 0 | c2-c6 | LCD: lamp sockets c2, c3, c5, c6, padlock c4 - a lit-lamp item appears per typed digit |
| rows 1-4 | c3-c5 | keypad 1-9, red clear, 0, green OK - each key on its own slot |
| rows 1-4 | c0-c2 | instruction plate + keyhole (decor) |
| rows 1-4 | c6-c8 | handle wheel (decor) |
| row 5 | - | bottom of the door, keeps the keys off the door edge |
Volume: the safe is a box - `body` adds a dark side face (right) and bottom face with feet, the nameplate sits
on the top edge, hinges stick out on the left, bolts out of the right side of the storage screen (spec
`canvas: {"left": 6, "right": 9, "top": 6, "bottom": 7}`). The client's "Inventory" label line
(y 18*rows + 20) gets a light band because dark-grey text vanishes on dark steel.

## Code entry with DeluxeMenus meta (no extra plugin)
- On open: `[meta] set code STRING -` (the leading `-` keeps the string non-empty).
- Digit key: `[meta] set code STRING %deluxemenus_meta_code_STRING_-%7`, `[refresh]`; requirement
  `regex matches` input `%deluxemenus_meta_code_STRING_-%` regex `^-[0-9]{0,3}$` (max 4 digits).
- Lamp n (item over the socket): `view_requirement` regex `^-[0-9]{n,}$`.
- Clear: `[meta] set code STRING -`.
- OK: `string equals` input the code, output `%deluxemenus_meta_safe_pin_STRING_-0000%` (default code 0000);
  success opens the storage (`[player] pv 1` for PlayerVaults - replace with your vault plugin) and sets
  `safe_unlocked BOOLEAN true`; deny resets the code with a message and a sound.
- Change code: `/safe_pin` has `open_requirement` `has meta safe_unlocked BOOLEAN true` (only right after a
  correct code); OK requires `^-[0-9]{4}$` and saves `[meta] set safe_pin STRING <code>`.
The same pattern makes any numeric input: amounts, page numbers, a lottery number.
Meta data is stored per player (persistent). Test regex / meta syntax once on the server's DeluxeMenus version.

## Storage
The storage screen shows the safe OPEN: `open_door` draws the door swung out on the left hinges in perspective
(far edge taller - closer to the viewer), then the `hinges` sit on the joint. It keeps the closed door's size
and gets its weight from depth: a 9 px thick edge with the bolts coming out of it, a top face, a raised plug
panel that casts a shadow, shadows under the rods and the mechanism. (User feedback: "small door" meant flat,
not short - a door as tall as the whole window looked huge.) Canvas `{"left": 64, "right": 9, "top": 8,
"bottom": 7}` -> texture 249x237.

DeluxeMenus cannot hold items. The storage screen is a skin: use the `menu_title` string from
`DeluxeMenus/gui_menus/hokaria_safe.yml` as the inventory title of the vault plugin (PlayerVaults, AxVaults,
...). If the plugin does not parse `<glyph:...>` tags, use the PlaceholderAPI form from the file's comment.
