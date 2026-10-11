# Pixel-art craft: lines, outlines, value, focus

The drawing fundamentals behind every texture, icon and title this skill makes, learned from the MakeBead
lesson "how to make pixel art" (built on Saultoons' "Ultimate Pixel Art Tutorial"). Light, ramps, hue
shifting, materials, dithering and clusters are already in `references/texture-shading.md`. This file adds
the line work, the outline choice, the value test and where the eye goes.
`python3 scripts/shading.py craft chart.png` draws every bad / good pair below. `shading.py check` measures
the ones that can be measured.

## 1. Process
Silhouette -> line art -> flat colours -> shading -> cleanup. Code follows the same order: the mask (does it
read as a black shape at 1:1?), then the outline, then the ramp tones, then the details. Cleanup comes last:
`shading.pixel_perfect`, then `shading.py check`. Look at the result at 1:1 all the time, not only zoomed:
the player sees 1:1 (GUI scale makes it bigger, never sharper).
Other ways to start are fine (construction shapes, blobs then cleanup). One is not: drawing big and shrinking.

## 2. Size and scale
| canvas | in Minecraft |
|--------|--------------|
| 8x8 | font glyphs, tiny hint icons (mouse buttons, arrows) |
| 16x16 | item and block textures, slot icons - the standard |
| 32x32 | HD items (`kitchen:cutting_board32`), big pictures on tiles |
| 64x64 | portraits, artist pictures (`references/artist-brief.md`) |
| <= 256 | a whole GUI glyph |
- **One pixel size per set.** Do not mix "mixels": a 16px item next to a 32px item in one menu, or a picture
  scaled x2 next to 1 px details, reads as two resolutions. Scaled-up titles (pixfont x2, `lettering`
  scale 3) are allowed because the style adds 1 px detail on top of them (outline, bevel, glints), so the
  pixel grid stays 1 px.
- **Never auto-shrink.** A 16px version is redrawn or rebuilt at 16, not halved from 32. The user saw this
  happen: a font built at cap 10 looked worse ("чёт хуже стало"). `font_pixel.py` builds every size from the
  outlines, and icons are drawn per size.

## 3. Lines: doubles and jaggies
- **Doubles** (L-corners): a 1 px line moving diagonally must step corner to corner. A pixel that makes an L
  with its two neighbours makes the line look thick at that spot. A right angle that is meant to be a
  corner stays (both arms go on straight).
  ```
  double        clean
  ##.           #..
  .##           .#.
  ..#           ..#
  ```
  `shading.doubles(px, W, H)` finds them. `shading.pixel_perfect(img, only={colours}, box=...)` removes
  them (the corner pixel takes the colour outside the corner). It is the same rule as Aseprite's
  pixel-perfect pencil.
  - Outlines: an outline built from 4-neighbours (`kitchen.edge_ring`) is clean. A ring dilated with
    8-neighbours (bold sticker outlines) has doubles at every rounded corner, so run `pixel_perfect` on its
    colour. `lettering.arcade / bands / bubble`, `kitchen.arrow` and `hub.medallion` do this.
- **Jaggies**: on a curve the step lengths change steadily: 6-4-3-2-1-1 then 1-1-2-3-4-6, never 6-2-4-1.
  On a straight line they stay constant (2-2-2) or repeat regularly (2-1-2-1). No lone 1 px nub or notch on
  a straight edge. `shading.check` reports jaggies on the silhouettes of sprites >= 20 px. On 16 px icons
  a 1 px guard, layer edge or stem is design, so they are not counted there.

## 4. Eight outline styles - pick one per job
| style | use it for |
|-------|-----------|
| black 1 px | almost never. It flattens everything and looks like a sticker. Exception: the arcade title style uses near-black on purpose |
| double (dark + light outer ring) | titles and stickers over a busy or changing background: a title over the world above the window, bubble letters on a dark GUI |
| dark tone of the material | the default for objects and icons (`references/item-icons.md`: the ramp's dark end, never black) |
| per area | each part outlined in its own dark tone (fruit red, leaf green), so the parts separate |
| lit outline | light tone on the lit side. It glows (the tutorial lettering's light outline) |
| selective | shadow tone on the lit top / left, dark outline on the shadow side and below. The default for delicate shading |
| broken | gaps where the light hits a glossy round object (fruit, gems, glass) |
| none | seamless tiles, terrain, big background areas, where value and colour carry the form |

## 5. Value first
- Hue only works if the values work. `python3 scripts/shading.py gray IN.png OUT.png` puts the picture next to
  its greyscale.
  - In grey, check that buttons separate from the background, materials from each other and the item from
    its slot.
  - Two colours of the same value (red and green in the chart) merge into one grey. That is how a menu looks
    to a colour-blind player, and at a glance to everyone.
- Hues are not equally bright: yellow reads lightest, blue and purple darkest. A blue and a yellow ramp at
  the same "brightness" setting do not have the same values.
- `shading.check` prints the value spread (5th to 95th percentile of luminance) and warns below 40.

## 6. Where the eye goes: contrast and saturation
- The strongest value contrast and the most saturated colours go to what the player must look at: the
  buttons, the slot zones, the item. Background, frame and decoration get lower contrast and duller
  colours. In the kits, the slate counter and felt are muted, and the board, plate and medallion carry the
  contrast.
- Saturation is seasoning: one or two saturated accents per screen, not every tile at maximum. Same idea as
  "props stay small" (`references/kitchen.md`): decoration must not compete with the zones.
- Warm and cool are relative: a grey turns warm next to blue and cool next to orange. Judge a ramp against
  its neighbours, not alone.

## 7. Shading mistakes the check now catches
- **Pillow shading**: dark all round the edge, light in the middle, as if the light came from the viewer.
  The form goes flat and soft. Light comes from one side (top-left here), so every ring round the edge has
  a light part and a dark part.
- **Banding**: bands of equal width running parallel to the outline (or parallel steps lining up). They read
  as extra lines and lower the resolution. Vary the band widths along the form (wide in the deep shadow,
  tapering to the sides) and offset where the steps of neighbouring bands fall.
- `shading.check` measures the rings 1-3 px inside the silhouette of a sprite. When two or more rings are
  each mostly one colour (>= 75 %) and those colours differ, it warns "tones follow the outline in rings".

## 8. Anti-aliasing, orphans, dithering
- **Inner AA only**: an existing ramp tone in the step corners of a curve, between two colours INSIDE the
  sprite, 1-2 px per step, never along straight lines, never changing the silhouette. Do it by hand, where
  a curve looks jagged at 1:1.
- **Never outer AA in Minecraft.** Blend pixels toward the background on the silhouette assume one
  background. An item icon sits on slot grey, the white hover highlight and the dark tooltip. A GUI glyph
  sits over the dimmed world. A halo that is invisible on grey shows as a dirty ring on dark (chart:
  "внешн." vs "на тёмном"). Semi-transparent pixels are forbidden anyway.
- **Orphan pixels**: a lone pixel of a colour is noise. Allowed only as a glint, a sparkle or a tiny detail
  (an eye, a rivet). Texture is 2-4 px clusters along the grain (chart: "сироты" vs "кластеры";
  `check` warns above 8 % single pixels).
- **Dithering** only with a reason (coarse cloth, the 2 rows of a lettering gradient), as before.

## 9. Palettes
Limit the palette: a few ramps of five tones (the kit ramps) beat many loose colours. Even four greens
work if the values are right. Lospec palettes are a good start for a brand-new pack, but a pack being
continued keeps its own ramps.

## What `shading.py check` reports from this file
| line | meaning | warns when |
|------|---------|-----------|
| `doubles {'dark_lines': n, 'other': m}` | L-corners in 1 px lines. Dark lines are outlines, cracks and grooves; other is grain and gloss | dark-line doubles > max(3, opaque px / 2000) |
| `jaggies n` | irregular steps / nubs on sprite silhouettes >= 20 px | n > 2 |
| `rings [(ring, px, share)]` | share of the most common colour in rings 1-3 inside the silhouette | >= 2 rings over 75 % with different colours |
| `value spread n` | light / dark range | n < 40 |
Look at a flagged spot before you fix it: a deliberate feature (a hilt, a layer edge, a pixfont glyph's
designed corner) stays.
