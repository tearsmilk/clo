# GUI geometry for title-glyph menus

All numbers are GUI pixels (what Minecraft calls "scaled" pixels; at GUI scale 3 one GUI pixel is 3x3 screen pixels).
A glyph texture drawn with `height` equal to its pixel height is exactly 1 texture pixel = 1 GUI pixel, which is
why menu textures are authored 1:1 and kept under Nexo's 256x256 glyph limit.

## Chest-type containers (9 columns, 1-6 rows) - the usual menu

| rows | DeluxeMenus `size` | window (w x h) | container slot boxes y | player inv boxes y | hotbar boxes y | "Inventory" label y |
|------|-----|-----------|----------------------|------|------|------|
| 1 | 9  | 176 x 132 | 17 | 48 | 106 | 38 |
| 2 | 18  | 176 x 150 | 17, 35 | 66 | 124 | 56 |
| 3 | 27  | 176 x 168 | 17, 35, 53 | 84 | 142 | 74 |
| 4 | 36  | 176 x 186 | 17 ... 71 | 102 | 160 | 92 |
| 5 | 45  | 176 x 204 | 17 ... 89 | 120 | 178 | 110 |
| 6 | 54  | 176 x 222 | 17 ... 107 | 138 | 196 | 128 |

Formulas (rows = r):
- window height `114 + 18r`
- container slot `(col,row)` outer 18x18 box at `x = 7 + 18*col`, `y = 17 + 18*row`; the item itself is the 16x16 inside it at +1,+1
- slot index = `row*9 + col` (0 top-left, the order DeluxeMenus `slot`/`slots` use)
- player inventory slot boxes at `y = 18r + 30 + 18*i`, hotbar boxes at `18r + 88` (vanilla ChestMenu places the
  items at `103 + (r-4)*18` and `161 + (r-4)*18`, i.e. one pixel inside those boxes)
- vanilla draws the title at `(8, 6)` and the "Inventory" label at `(8, 18r + 20)`

## Placing the glyph

Minecraft draws the title as a text line whose first character starts at x=8, y=6 inside the window.
A bitmap glyph's top edge lands `ascent` pixels above the baseline, and the baseline is 7px below the line top, so

```
glyph top  = 6 + 7 - ascent = 13 - ascent      (relative to the window top)
glyph left = 8 + sum of preceding <shift:N>
```

So a texture whose (0,0) should coincide with the window's (0,0) uses **`ascent: 13` and `<shift:-8>`**.
If the texture has `p` transparent rows above the window art, use `ascent: 13 + p`. `ascent` must be <= `height`.
Treat 13/-8 as the computed starting point and confirm in-game: the Nexo GUI Visualizer
(https://nexomc.com/tools/gui-visualizer) or the Glypher client mod show the exact fit; nudge by 1px if needed.

Rows 1-3 use the small chest screen and rows 4-6 the large one, but both keep the same top-left origin, so the
same ascent/shift works for every row count as long as the texture is authored for that row count's height.

After the glyph the text cursor has advanced `width + 1` pixels. To print readable title text on top of the art,
shift back: `<shift:-8><glyph:menu><shift:-177>Title` for a 176px-wide glyph (the builder does this when the spec
has `title_text`). Usually it is nicer to bake the title into the texture with the pixel font.

## Layering - what draws over what

1. vanilla container background (the generic chest texture)
2. the title glyph (your art) - it covers the vanilla background entirely if it is opaque
3. item icons (an `item_model: nexo:empty` item draws nothing, so your painted button stays visible)
4. slot hover highlight: a white 16x16 overlay on the hovered slot. It still appears over painted buttons, so
   design buttons that look fine with one 16x16 cell lightened (sunburst / gradient tiles do; tiny text does not)
5. tooltip of the hovered item (the button's `display_name`/`lore`)

Because the glyph is part of the title, anything that recolours titles (legacy `&7` before the glyph) tints it -
start the title with `<white>`, or rely on Nexo forcing glyphs to white unless `:colorable` is used.

## Other screens

Title glyphs work on any container with a title. Widths are 176 unless noted.

| screen | size | notes |
|--------|------|-------|
| hopper (5 slots) | 176 x 133 | slots at x = 44 + 18*i, y = 20 |
| dispenser/dropper (3x3) | 176 x 166 | slots at x = 62 + 18*c, y = 17 + 18*r |
| furnace / smoker / blast | 176 x 166 | fixed vanilla widgets (fuel, arrow) still render |
| shulker box | 176 x 166 | same grid as a 3-row chest |
| anvil | 176 x 166 | has a text field - good for search/rename inputs |

For anything bigger than 256px or wider than the window (full-screen menus), split the texture into a
Multi-Bitmap Glyph (see nexo-reference.md) or several glyphs joined with `<shift>`.
