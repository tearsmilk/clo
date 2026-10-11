# Decorative lettering: a beautiful letter in five steps

From a pixel-art lettering tutorial the user showed (blackletter "B" by @ribbitknight - the art is a
reference, the method is reused). `scripts/lettering.py` does it with the pixfont capitals:
`python3 scripts/lettering.py chart OUT.png Б` draws the five steps + a finished word; in a spec a layer
`{"type": "lettering", "style": "tutorial", "text": ..., "x": 88, "y": -20}` (x = centre, y = top). Use
lettering for headers, the server name, big titles on banners - not for small labels.

## Volumetric letters - the default for titles (`lettering.volume`)
The user asked for VOLUMETRIC letters and called the first try (tutorial steps on the slab font: nib cuts,
checker band, cracks everywhere) "not beautiful" - it read as noise. What makes them beautiful:
- **Clean, chunky shapes**: slab capitals grown 1 px all round, air between letters = scale + 2 px,
  staircase notches of diagonals filled, convex corners rounded by 1 px, counters NEVER filled (Ю, О, Б keep
  their holes - grow and smooth only outside them). No nib cuts on block letters.
- **Real thickness**: the letter pushed `depth` px down-right (light top-left); every side pixel is shaded by
  which way that side faces - right faces dark mid, bottom faces shadow, the back edge darkest. The facing is
  taken from a smoothed 5x5 edge direction, so a staircase diagonal (Х, К, Я) gets one tone, not stripes.
  The extrusion shows inside counters too.
- **Front face**: two flat bands (light top ~40 %, base below) - no checker, no gradient noise; a 1 px bevel by
  the smoothed edge direction: up-left edges highlight, down-right edges dark mid, edges along the light stay
  plain; a short glint on the upper left of a few stems.
- **One outline** round letter + extrusion in the darkest tone.
- **Accent only if asked**: `accent='sparkle'` (two or three tiny stars) for festive titles, the tutorial's
  cracks / drips only for a horror theme.
- Any ramp: `ramp5('#e0a234')` gold, `#3fa868` emerald, `#c8384a` crimson, the tutorial purple; keep the
  standard (contrasty) ramp for titles, not the soft one.
`python3 scripts/lettering.py volume OUT.png ХОКАРИЯ '#e0a234' 3`; in a spec
`{"type": "lettering", "text": "МЕНЮ", "x": 88, "y": -22, "scale": 3, "color": "#e0a234", "accent": "sparkle"}`.
Scale 3 reads best for 4-8 letters on a 176 px window; scale 4 for a short logo word.

## The tutorial: five steps (gothic / horror look, `lettering.render`)
1. **Shape.** A letter with character: thick vertical stems, thinner horizontals (broad-pen contrast),
   corners of stroke ends cut at 45 deg on the top-left and bottom-right (the pen nib), small counters
   (keep >= 2 px). The shape carries most of the beauty - a plain block letter stays plain whatever the
   shading. `lettering.shape(..., weight=1)` thickens the stems from scale 4 up (at scale 3 the diagonals of
   М / Ж / Ю would vanish between heavy stems).
2. **Outline.** 1 px ring in the LIGHTEST tone round the letter and round every counter. On a dark
   background the letter glows instead of sinking into it (on a light background use the darkest tone).
3. **Gradient.** Vertical: light band at the top, base in the middle, dark mid at the bottom. Between two
   bands 2 rows of checker (the two tones alternating). This is the one place where a checker is wanted: as
   narrow transition rows in lettering, never as an all-over blend (texture-shading rules still hold).
4. **Inner + outer shadow.** Inner: the shadow tone just inside the outline on the top / left - the fill
   sits below a raised rim lit from the top-left. Outer: the letter with its outline repeated 2-3 px
   down-right in the shadow tone, BEHIND it - the letter gets thickness and stands off the background. (The
   tutorial drops the shadow down-left; in this skill the light is always top-left, so it goes down-right.)
5. **Accent + texture.** One saturated accent colour in two tones, used sparingly: cracks that start at an
   edge with a splatter cluster and run into the stroke (light accent with a dark lower lip), drips falling
   from bottom edges over the outline and the shadow, light 2 px speckles in the top band. The accent sets
   the mood (blood for horror, gold for royal, cyan for magic, green for poison).

## Palette
Five tones of ONE hue + one accent - nothing else. Measured from the reference: darkest #241245, shadow
#4a337b, dark mid #734ca2, base #8c6db0, light (outline) #b6a8c8, accent #dc3783 (+ a dark accent #7d1745 for
the lips of cracks and drip tips). `lettering.render(text, ramp=..., accent=...)` takes any ramp5 list and
any two accent tones.

## Why it works
- Three readable layers: light outline (silhouette), gradient body (volume), dark extrusion (depth).
- The gradient runs top -> bottom like the light; the inner shadow and the extrusion agree with it.
- The accent is rare: a few small clusters on edges, never a second fill colour.

## Real fonts as pixel fonts (`scripts/font_pixel.py`)
When the user brings a TTF / OTF (e.g. a blackletter): `python3 scripts/font_pixel.py FONT.otf OUT --cap 16`.
- Rasterised by AREA COVERAGE at an exact cap height (rendered 8x, each pixel on at >= 45 % cover), baseline on
  the grid, lone pixels removed, pinholes filled - not the blurry or uneven freetype output.
- Cap 14-16 keeps a blackletter's spurs and flares; at cap 10 they turn to mush - use the slab pixfont there.
- **Cyrillic the font does not have is drawn from its own Latin parts**, so weight, flares and spurs match:
  lookalikes (А В Е К Н О Р С Т У Х, З from 3), mirrors (И from N, Я from R, Э from C + bar), marks (Ё, Й);
  recipes: Г = F without its middle arm, П = H without crossbar + top bar, Д = П on a base with feet, Л = П
  with the left leg bent out, Ь = B without its upper bowl, Б = Ь + top bar, Ъ = arm + Ь, Ы = Ь + I,
  Ж = mirrored K arms + stem + K arms, Ш = U + one more stem, Щ / Ц = Ш / U + tail, Ч = U with the left stem
  cut at the middle + bar, Ф = P bowls on both sides of its stem, Ю = I + bar + O, and М = two stems of H
  with a V (the blackletter M is an uncial "m" that Russian readers take for "т"). Lowercase Cyrillic = the
  same capitals drawn at x-height (small caps), Latin lookalikes (а е о р с у х) stay real lowercase.
  Always look at the preview: a recipe can misfire on an unusual font - fix that letter by hand.
- **Fixed cells** (the usual Minecraft font textures): `--cells 16,32` picks the biggest cap height whose
  glyphs, marks (Ё, Й) and descenders (Д, Ц, Щ, у) fit a 16x16 / 32x32 cell (cap 11 / 24 for a blackletter),
  writes `pack/assets/<ns>/font/<name>_<cell>.json` (height = cell, 1:1; lower it for a finer HD font) and a
  gridded preview. Area coverage beat FreeType's hinted 1-bit renderer (`--method mono`) even at 16: mono
  came out thin and uneven. From cap 18 up the edges are smoothed (1 px notches filled, 1 px bumps cut).
- The user judged a cap-10 test "worse" - below cap 11 a blackletter loses its shape; say so instead of
  shipping it.
- Output: glyph PNGs, `font.json`, `sheet.png`, `preview.png` and a Minecraft bitmap provider
  (`pack/assets/<ns>/font/<name>.json` + texture) - in titles / lore `<font:hokaria:title>Текст</font>`.
- Volumetric titles in that font: `lettering.volume(text, ramp, font=OUT_DIR)` (no growing / rounding: the
  font keeps its own shape).
- **Licences**: read the font's README. "Personal use only" fonts cannot go on a server with a shop or
  donations without the commercial licence. Never commit a third-party font or its converted glyphs into
  the skill or the repo - they go only into the user's own pack.
