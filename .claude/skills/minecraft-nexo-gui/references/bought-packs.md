# Menus on top of a ready-made (bought) GUI pack

When the user owns a GUI pack (textures with frames, pictures, labels already drawn), use its PNGs as they are
and let the builder do the rest: glyph YAML with the right ascent/shift, invisible buttons, real items,
DeluxeMenus files, variants, tooltip hints, previews. Ask once whether the pack is theirs (bought); third-party
art the user only "likes" is reference material - rebuild it instead (references/replicate.md). Never commit or
redistribute pack files: keep them out of the skill and the repo, ship them only inside the user's own output.

## 1. Find the window inside the texture
```bash
python3 scripts/ref_tools.py window pack/farmer.png      # slot grid -> candidate window x; centred is usual
python3 scripts/ref_tools.py charmap pack/farmer.png 60 30 200 60
```
- Packs often paint only some slots (e.g. a centred 5x2 grid) -> window x from the centred candidate.
- Window y: pick the row so the art's frame top sits on the window top, and check that the art's bottom ends
  where the player inventory starts (18*rows + 30) - that confirms rows (Jobs pack: window (40, 33), 5 rows).
- Below the art the vanilla chest (player inventory) shows - that is the pack's design. The preview draws the
  vanilla window under the texture (`preview_vanilla_under`, on by default for `background`).

## 2. Spec
```json
{"id": "hokaria_jobs", "rows": 5, "background": "pack/${tex}.png", "window_at": [40, 33],
 "hint_glyphs": {"lmb": "pack/left_click.png", "rmb": "pack/right_click.png"},
 "layers": [
   {"type": "patch", "box": [74, -1, 30, 8], "from_x": 60, "above": true},
   {"type": "text", "x": 88, "y": -2, "text": "Работы", "material": ["#371621", "#c58b55", "#f8cfad", "#ffe6cc", "#fffaf0"], "above": true},
   {"type": "nameplate", "x": 88, "y": 57, "text": "${label}", "min_w": 73, "above": true}],
 "nexo_items": [{"id": "hokaria_job_${id}", "icon": "pack/icons/${tex}.png", "name": "<yellow>${label}"}],
 "buttons": [{"id": "join", "x": 2, "y": 0, "w": 5, "h": 3, "style": "none", "commands": ["[player] jobs join ${job}"],
              "right_commands": ["[player] jobs info ${job}"]}],
 "variants": [{"id": "farmer", "tex": "farmer", "label": "Фермер", "job": "Farmer"}]}
```
- **Relabel** English text: `patch` wipes the old letters (each row filled with the colour at column `from_x`,
  so plank lines survive), `text` writes material letters (`condensed: "bold"` = small 2px-stem font that
  matches 7-8 px tall pack lettering), `nameplate` re-draws a ribbon label of the same size over the old one.
  Measure the boxes with charmap; window coordinates.
- **Variants**: one spec, one menu per entry; `${key}` anywhere, plus `${prev_id}`, `${next_id}`,
  `${prev_label}`, `${next_label}` for paging, `variant_defaults` for shared values, `{"if": "${picture}"}`
  to skip a layer when a variant has no value.
- **New entries the pack does not have** (e.g. a "Пекарь" job): use one texture as the base and paste the
  artist's picture into the card with an `image` layer of the exact size (pasted 1:1), then the nameplate.
- **Hints**: `%nexo_<ns>_lmb%` / `%nexo_<ns>_rmb%` in lore (PlaceholderAPI + Nexo expansion); the preview
  tooltip draws the icons.

## 3. Hand-off
Write an install note in the user's language: copy `_all/Nexo` and `_all/DeluxeMenus`, the `gui_menus:` block
for config.yml, reload commands, which plugin commands the buttons call (Jobs Reborn names differ:
Weaponsmith, Brewer), and the optional lang override for the "Inventory" label.
