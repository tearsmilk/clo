# Drawing styles: restyle any sprite, demo objects in every style

`scripts/drawing_styles.py` does two things:
1. **A style engine**: `stylize(img, style)` turns ANY finished RGBA sprite from any kit (an item icon, a
   kitchen board, a whole `modes_hd` scene) into one of 18 drawing styles - from our delicate house style to
   PICO-8, Game Boy, an engraved ink drawing or neon at night.
2. **Six demo objects** drawn natively in the house style at two densities (k=1: a block is 16x16; k=2 "HD":
   32x32 density, drawn again with more detail, never upscaled), built from parts, used to show and test the
   styles: `sphere`, `stone_cube`, `sword`, `potion`, `house`, `tree`.

Charts: `python3 scripts/drawing_styles.py chart OUT.png [--hd]` (rows = objects, columns = styles, x4 / HD x3
on slot grey), `outlines OUT.png [--hd]` (the 8 outline modes), `styles IN.png OUT.png [--kit MODULE]` (one
sprite of yours in every style).

## Which style when
| style | what it is | use it for |
|-------|-----------|-----------|
| `house_soft` | our 5-tone delicate style (close mid tones, metals keep contrast), selective outline | everything in this skill; art that sits next to the other kits |
| `soft_noline` | the same tones, no outline - value and colour carry the form | tiles, terrain, big background areas, things behind glass |
| `vanilla` | Minecraft-like: firmer ramps (soft 0.35), a bit more saturation, the material's dark tone as outline everywhere | resource-pack items and blocks that sit next to vanilla ones |
| `high_contrast` | standard ramps stretched: deep shadows and outline, white glints, saturation x1.22 | tiny icons, focal items, rare drops - anything that must pop |
| `pastel` | lifted, desaturated colours, lavender-leaning shadows, a soft coloured outline (not near-black), 4 tones | cosy / cute servers, seasonal events |
| `cel` | one lit + one shadow tone per material + outline | mascots, characters, comic banners |
| `flat` | one tone per material + outline; 1 px dark features (cracks, grooves, seams) stay as lines | UI glyphs, map markers, status icons, logos |
| `sticker` | 3 tones + a double outline (dark + light outer ring) | titles and badges over the world, buttons on busy art |
| `lineart_ink` | 2 colours, ink on paper: outline, lines where light materials meet, hatching for shade | quest books, maps, lore pages, "sketch" previews |
| `silhouette` | one flat colour (+ a lighter ground shadow) | locked / undiscovered items, "?" slots |
| `sepia_old_map` | sepia ramps + faded rust / olive / teal washes, brown ink; greys become sepia | treasure maps, lore, the navigator menu (`references/mode-select.md`) |
| `neon_night` | night-dark bodies, glowing neon rim (pale on the lit side), a dark neon halo, glints kept | night events, cyber / tech servers, glowing rares |
| `pico8` | PICO-8 16 colours, 4 tones | retro mini-games, arcade lobbies |
| `sweetie16` | Sweetie 16 (GrafxKid), 4 tones | a friendly retro look with a modern palette |
| `endesga32` | Endesga 32, 5 tones | a whole new pack that needs a coherent rich palette |
| `nes_like` | 3 colours per material from the NES palette, black outline | 8-bit throwback events |
| `gameboy` | 4 greens (BGB palette) for everything, darkest green outline | nostalgia events, monochrome "handheld" screens |
| `gameboy_dither` | Game Boy + ordered (Bayer) dithering where a tone falls between two greens | the retro look where a checker texture is wanted on purpose |
One style per set (like one pixel size per set): mixing `vanilla` icons with `neon_night` ones in one menu
reads as two games. Value first still applies - check a restyled sheet with `shading.py gray`.

## How the engine works (what makes a restyle read)
1. **Materials.** Colours are grouped into materials. With declared ramps (`ramps='modes_hd'`, a kit module
   name, or `[(name, ramp)]` - 6-colour `shading.ramp5` ramps: outline + 5 tones) a colour IS that material at
   that tone - exact. Otherwise colours are grouped by hue + adjacency (union-find over touching colours of
   compatible hue; greys with greys) and get a tone index by value inside the group: the darkest colour is a
   line (index 0) when it is much darker than the rest and a minority; the count-weighted median is the base
   (3); darker ones become 1-2, lighter ones 4-5 (fractional when there are many). Value order inside a
   material never inverts. Ground shadows (`no_outline=('SHADOW',)`) are never outlined and keep their value.
2. **Base tone** = tone 3 unless the material's INNER pixels barely use it (edge pixels carry the outline
   tones and would fool it): a ground shadow's base is its core.
3. **Targets.** `palette='own'` styles rebuild each material with `shading.ramp5` around its base colour
   (style saturation, softness, `_pastel` / `_contrast` post-steps; metals keep soft 0). Limited palettes pick
   the hand-made ramp (`PALETTES`: dark -> light lists, like pixel artists use them) whose colours are nearest
   in Lab, then the anchor colour: value first (within 35 luminance of the base), then hue. A tone maps to
   `anchor + (index offset + value offset) / 2`: the index keeps faces apart (a cube's right face stays darker),
   the measured value difference stops a soft material from jumping across a coarse palette's big steps.
   Tone tables (`TONE_OFFSETS`): 5 tones -2..+2; 4 merge shadow + dark mid; 3 also merge light + highlight;
   cel 2 = lit / shadow; flat 1. Only the base's neighbours get room (the anchor shifts at most to fit -1 / +1);
   extremes collapse into the ramp ends.
4. **Outline.** The silhouette edge = pixels next to the exterior (flood fill from the border; holes like an
   empty glass are not exterior; a full-bleed scene or tile gets no frame). If the source already has an
   outline (declared ramps: edge tones 0-1; else edge darker than inside) it is recoloured in place, so the
   silhouette never changes; otherwise a new ring is added outside (`stylize` only - never inside a parts
   picture). Modes (`OUTLINES`): `none` (inner colour), `black` (style ink), `dark` (darkest tone of the area
   it wraps), `selective` (shadow tone on the lit top / left, dark elsewhere), `double` (+ a light outer
   ring), `lit` (light tone on the lit side), `glow` (bright rim, pale on the lit side, + a darker halo),
   `broken` (gap where the light hits). Recoloured outlines and coarse-palette inner lines get
   `shading.pixel_perfect` restricted to those pixels.
5. **Expansion.** A material with < 3 tones (a flat input) in a style with >= 3 tones gets shading
   synthesised: lit top / left edges, a shaded bottom / right edge, a highlight just inside the top-left.
6. **Special modes.** `ink`: engraving value = tone + how dark the material is (a cream wall stays paper,
   dark timber is hatched even where lit); k=1 hatches only the shadow side with horizontal lines (calm at
   16 px), k=2 uses diagonal hatching and cross-hatching; 1 px dark features stay as ink lines. `neon`: hue
   snapped to 8 neon hues, bodies at value 0.1-0.35, glints kept, rim + halo. `silhouette`: one colour.
   Dithering: `BAYER4` ordered dithering only where a tone falls between two style tones (`DITHER_OFFSETS`).
7. Alpha < 128 -> transparent, >= 128 -> opaque: no semi-transparent pixel ever comes out.

## Demo objects (house style, light from the top-left)
| object | k=1 | k=2 adds | parts |
|--------|-----|----------|-------|
| `sphere` | 11 px glossy ball: highlight, lit cap, base, dark mid, a narrow terminator (pixel-perfect), bounce light | reflection dot, rim light, rounder 22 px disc | shadow, ball |
| `stone_cube` | 2:1 iso block (4kk+2 diamond rows), top light mid with a highlight on the near-left edge, base left face, dark-mid right face, AO bottom rows, 2-3 px chips along each face, dark diagonal cracks, moss over the far corner | more chips, a crack with a lit lip, moss highlights | shadow, block |
| `sword` | diagonal blade addressed as s = x + y (across) / t = x - y (along): every s-line is a clean 45-degree line; lit bevel, base ridge, dark bevel; gold guard, banded grip, 2x2 pommel | 5-line blade with a lit edge and a rim light, fuller, reflection streaks across the blade, curved guard with a gem, round pommel | grip, blade, guard, pommel |
| `potion` | item-icon rules: glass light left / dark right and bottom, empty part transparent, liquid lit top-left with a light surface line, a bubble, a cork | meniscus, caustic, ring bubbles, a reflection streak and a window glint, twine, two sparkles | liquid, glass, cork (+ twine, sparkles) |
| `house` | 2:1 iso cottage: plaster lit left / shaded right, timber posts and sill, stone footing, door + window, gable with tie beam and vent, tiled roof (rows along the eave, lit ridge cap, barge boards in shade), stone chimney with a contact shadow on the tiles, soft eave shadow, cast shadow | footing courses, framed windows with mullions, a flower box, door with planks / battens / handle and a step, tile gaps, brick courses, smoke, grass | shadow, walls, door, (step), roof, chimney_shadow, chimney, (flowers, grass, smoke) |
| `tree` | clumped canopy, each clump lit as a ball, front clumps shading the ones behind, leaf clusters (never single pixels), bark streaks, canopy shadow on the trunk, roots, ground shadow | more clumps, apples, grass tufts | shadow, trunk, leaves (+ apples, grass) |
Every part is drawn on its own transparent canvas (`modes.Parts`) with its own selective per-area outline
(`Sheet.outline`: the outline pixel takes the dark tone of the material it wraps, the shadow tone on the lit
side). Ramps are module constants (`ORB`, `STONE`, `MOSS`, `STEEL`, `GRIP`, `GEM`, `PLASTER`, `ROOF`, `DOOR`,
`GLASS`, `LEAVES`, `BARK`, `APPLE`, `GRASS`, `FLOWER`, `POTION`, `CORK`, `SMOKE`, `SHADOW`, + `WALNUT` / `GOLD`
/ `CREAM` from kitchen / hub), so `shading.py check --kit drawing_styles` knows every material.
Iso slopes are chosen so every edge is a clean pixel line: walls, eave and ridge 2:1, the front gable edge a
regular 2-1 staircase, the back gable edge 1:2. Ground shadows: hard core + a one-step-lighter penumbra
crescent at the far end.

## API and CLI
```python
import drawing_styles as ds
ds.render('house', k=2, style='sepia_old_map')            # tight RGBA; object opts: shadow, smoke, moss, ...
ds.parts('tree', k=1, style='sticker')                     # [{'name','sprite','x','y'}], + 'outline_outer'
ds.stylize(img, 'pico8', ramps='modes_hd', outline='selective', dither=True)   # any sprite
ds.stylize_parts(items, 'neon_night', ramps=..., no_outline=('SHADOW',))      # a whole parts list
ds.check('house', k=2, style='vanilla')                    # shading.check with the style's material ramps
```
```bash
python3 scripts/drawing_styles.py chart OUT.png [--hd]
python3 scripts/drawing_styles.py render NAME OUT.png [--hd] [--style S] [--no-shadow] [--outline M] [--dither]
python3 scripts/drawing_styles.py parts NAME OUT_DIR [--hd] [--style S]     # PNG per part, layers.json, .aseprite
python3 scripts/drawing_styles.py stylize IN.png OUT.png STYLE [--kit MODULE] [--outline M] [--dither]
python3 scripts/drawing_styles.py styles IN.png OUT.png [--kit MODULE]
python3 scripts/drawing_styles.py outlines OUT.png [--hd]
python3 scripts/drawing_styles.py check NAME [OUT.png] [--hd] [--style S]
python3 scripts/drawing_styles.py list
```
Restyling parts: one analysis over all parts (consistent materials), each part restyled on its own canvas
(its own outline kept where it had one), the second ring of `double` / `glow` added once round the whole
picture as the part `outline_outer` - hide or re-run it after moving parts with `modes.override`.
Deterministic: seeded random, ties broken by order (same output for any `PYTHONHASHSEED`).

## Adding things
- **A new object**: a builder `def thing(k=1, shadow=True, **_)` returning `modes.Parts(W, H)`; draw each
  part with a `Sheet` (`put(x, y, RAMP, tone)`, `_chips` for clusters, `_crack`, `outline(1, 0)`), declare
  new ramps as module constants with `_r5('#hex', soft=...)` (soft 1 for matte, 0 for metal / gems), draw k=2
  natively (more tones, clusters, small features), add it to `CATALOG`, then `chart`, zoom, `check`.
- **A new style**: `_add_style(Style('name', 'doc', palette=..., tones=..., outline=..., soft=..., sat=...,
  adjust=fn, use='...'))` and add it to `CHART_STYLES`. A new limited palette: `PALETTES['x'] = {'ink': hex,
  'ramps': [[dark .. light], ...]}` (+ `'neutral': i` to send greys to ramp i); write ramps by hue family the
  way artists use the palette - the engine never invents colours outside it.

## Known check results (deliberate)
`shading.py check` / `drawing_styles.py check`: native objects pass except - jaggies at designed corners
(sword guard ends and pommel, potion cork and lip, house roof corner / chimney / step, the tree's lumpy
canopy); the k=1 potion's "top darker than bottom" comes from the transparent empty glass (filled, it reads
top 111 > bottom 106). Styles: `silhouette` (one colour: no value spread, no light direction), `flat` / `cel` /
`lineart_ink` light-direction notes (no or 2 tones), `gameboy_dither` checker windows, `lineart_ink`
cross-hatching L-corners, and a few (4-6) L-corners where two outlines of one coarse-palette colour meet on
the HD house.
