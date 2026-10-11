# Rebuilding a reference GUI "1 in 1"

When the user shows a finished GUI and says "повтори 1 в 1" / "make it exactly like this", do not eyeball it.
Measure the reference, rebuild every simple part to the measured geometry, draw the illustrations yourself in
the same footprint and palette, then score the result against the reference and iterate.

The user's references are usually third-party packs: copy geometry, proportions, stripe orders and palette
(that is style), never paste their pixels or trace their illustrations (emblems, characters, crystals). Say so in
one line when you deliver.

## 1. Measure (scripts/ref_tools.py)

```bash
python3 scripts/ref_tools.py palette REF.png                 # exact colours by frequency - reuse them verbatim
python3 scripts/ref_tools.py charmap REF.png 0 0 64 120      # one letter per pixel + legend
python3 scripts/ref_tools.py boxes REF.png 40 17 176 222     # parts outside the window, window-relative boxes
```

- **Find the window first.** Look for the 18px slot pattern in a charmap: the first container slot box's
  top-left is (window_x + 7, window_y + 17). Everything else is measured relative to the window, which is what
  the spec's `canvas`, `box` and layer coordinates use. A 256-wide texture with the window at x=40 means
  `canvas.left = 40`.
- **Read stripe orders**, not just colours: e.g. a bracket leg = outline, gold, gold, light, red, outline; a slot =
  light line above, mid left rim, light top/right rim, dark bottom rim, inner shadow, lit inner edge, dark gap.
- **Note where colours vary along a line** (brushed gold: dark at the ends, bright in the middle with 1px
  alternating transitions) and how ends are cut (mitered: each row 1px shorter, ending light -> dark red ->
  outline).
- **Check the reference against vanilla geometry.** Container rows at 17 + 18r, player inventory at 18*rows + 30,
  hotbar at 18*rows + 88. References are sometimes off by a pixel (the royal chest draws the player inventory 1px
  low) - keep the vanilla positions, otherwise items sit off-centre in game, and tell the user.

## 2. Rebuild

- Simple geometric parts (frames, grooves, slots, brackets, tabs, dividers, gems, rails, key ornaments) are
  reproduced exactly from the measurements - put them in a kit module like `scripts/royal.py` with one function
  per part, coordinates window-relative, so other menus reuse them.
- Illustrations get their own design with the same size, position, palette and visual weight (a crowned lion
  head instead of their lion, own crystal shapes, own ribbon).
- Wire the kit into the builder (`theme`, header style, spec keys) so the next menu in that style is a spec, not
  code.

## 3. Score and iterate

```bash
python3 scripts/ref_tools.py compare REF.png out/texture/ID.png cmp.png     # % equal pixels + red diff map
```

Score per region (window, divider, tab, ornaments) - a single number hides where the mismatch is. Then print
side-by-side charmaps of a mismatching region (ref row above ours) and fix the cause: an offset, a missing
stripe, a wrong miter, a 1px different length. Typical targets: frame/slots/tab/ornament geometry 96-100%, own
illustrations 55-65% (different art in the same place), whole texture ~89%.

## Royal kit (measured from a premium 6-row chest)

`theme: "royal"` + `corner_brackets`, `section_divider`, `hotbar_frame`, `header.style: "bracket_tab"`,
`royal_ornaments` reproduce it; see `assets/examples/royal_chest/spec.json` (texture 256 x 239, window at 40,17).
Measured facts: outline 1px outside the window on top/left/right, 2px inside at the bottom; 1px brushed gold line
on the window edge in the upper section, a 2px outline in the inventory section; grooves at 3/4px; top band of
two light rows; bottom lip light/mid/dark + 2px outline; tab 96 x 20 at y -10 with a 2px shadow; corner brackets
16x17 (top, 2px outside) and 16x16 (bottom, flush); divider zone y 125..137 with a 7-row gold bar (x 45..130)
and a 12x13 emerald; hotbar frame 1px around the hotbar, gold top/bottom, red sides.
