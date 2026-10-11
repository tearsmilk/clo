# Designing menus that look like the good server menus

What the polished menus (BuiltByBit packs, Pinterest "Minecraft GUI menu" boards, big networks) have in common:

1. **Big painted buttons, not item grids.** A button covers several slots (3x2 is the classic "quick menu" tile,
   2x2 / 1x1 for secondary actions, a full-width 9x1 bar for navigation). Each tile = coloured background +
   one strong icon + a short UPPERCASE label. The real items in those slots are invisible.
2. **One colour per destination.** Distinct saturated hues (green farm, blue fishing, orange hunting, purple
   travel, red home, gold shop...). Same lightness range so nothing screams. Sunburst rays or a vertical
   gradient give depth cheaply and survive the slot hover highlight.
3. **Framed like vanilla.** Keep the 176px window, a 1px black chamfered outline and a 2px bevel (light top-left,
   dark bottom-right). Themed materials (oak, spruce, stone, nether...) instead of grey. Leave the player
   inventory rows looking like normal slots - players need to read their inventory.
4. **Pixel honesty.** Everything at 1 texture px = 1 GUI px: hard edges, no anti-aliasing, no TTF text, no
   blurry upscales. Icons ~16-24px; a 3x2 tile has a 52x34 inner area. Labels use the 5x7 pixel font with a
   1px drop shadow, max ~8 letters on a 3-wide tile, ~5 on a 2-wide tile. Shorten words rather than squeeze letters.
5. **Header strip.** The top 16px (above the first slot row) holds the menu name in pixel font; optionally a
   small decoration (wheat, gems) on the right.
6. **Hierarchy.** Main actions top/centre and largest; utilities (close, back, settings) as 1x1 buttons in the
   bottom row corners. Keep a consistent "close" (red, bottom-centre or bottom-right) across all menus.
7. **Tooltips carry the details.** The texture shows only the label; `display_name` + `lore` explain what the
   button does, cost, requirements, and end with a call to action ("» Нажми, чтобы перейти").

## Icons

Best quality path: generate each icon separately with an image model (prompt template in
`scripts/icon_tools.py`, "single Minecraft-style pixel art game UI icon of ..., isolated on a plain flat
background"), cut the background (rembg), then let the builder downscale with a hard alpha edge.
Generate on a background that contrasts with the subject (white for dark objects, dark navy for
cream/parchment/white objects) and use `--fill-holes` when a light interior got removed.

Do **not** use an image model to draw the whole menu as the final texture: models do not keep the 18px slot
grid, so buttons would not line up with clickable slots. Whole-menu generations are fine as mood boards.

When no image model is available: draw simple 16x16 icons as character grids (see the sprite approach in
pixfont.py) or ask the user for PNGs / an existing texture pack.

## Colour sets that work

| theme | frame | tile colours |
|-------|-------|--------------|
| farm / village | oak | #5DAA3A #3E86C8 #D9822B #E0AE22 #8B5CC8 #D2483C #D24C8C #B8763A #33A89C |
| winter | birch / stone | #6FB7E8 #A8D8F0 #4A78C2 #E8F4FF #C24A4A |
| dark fantasy | nether / dark | #8A2BE2 #C0392B #E67E22 #27AE60 #2C3E50 |
| shop / economy | spruce | #E0AE22 #2ECC71 #3498DB #E74C3C |
