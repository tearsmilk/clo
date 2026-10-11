# Texture shading - requirements for every texture

Hand-painted texture shading in Minecraft pixel-art style. This is about how the pixels of a texture are
coloured (light, shadow, volume) - not about render shaders. It applies to everything this skill draws: GUI
backgrounds, frames, buttons, props, scenes, item icons, crop/block textures.
Check every result with `python3 scripts/shading.py check OUT.png` (add `--tile` for seamless tiles).

## 1. Main principle
Never fill a surface with one flat colour. Every material gets a planned set of light, base and dark tones
that builds volume, depth and a readable form.

## 2. Light and shadow
- One light direction for the whole texture (this skill: from the top-left).
- Light pixels on top and protruding parts of a surface.
- Darken the lower parts, recesses, cracks, joints and the places where parts touch.
- Transitions are soft in meaning but stepped in pixels (bands of one tone, no blur).
- Use contact shadows and ambient occlusion (darker where two parts meet, inside corners, under a ledge) to
  show depth.
- No random highlights or shadows that contradict the light direction.

## Light anatomy (what every shaded form has)
From the user's shading references (sphere anatomy, a 5-stage material chart, a hue-shifting/band sheet):
| part | what it is | tone |
|------|-----------|------|
| main light | one direction for the whole texture (top-left here) | - |
| highlight | the specular spot where the light reflects | Highlight, small |
| reflection | a second small bright spot / window streaks on glossy things | Highlight / Light Mid |
| light side | faces turned to the light | Light Mid |
| base | the material in plain light | Base, the widest band |
| terminator | where light turns into shadow - the narrow, darkest, most saturated band | Shadow |
| volume (form) shadow | the side turned away | Dark Mid |
| bounce light | light reflected from the ground lifts the bottom of the shadow | Dark Mid -> Base |
| rim light | a thin light edge on the shadow side | Light Mid, 1 px |
| projected shadow | the object's shadow on the ground/wall: HARD edge, one dark tone | darker than the surface |
| self-cast shadow | a part shading another part of the same object: SOFT edge (one extra step) | Dark Mid / Shadow |
| ambient occlusion | darker where things touch or in tight corners | one step down |

- **Hue shifting**: do not only change brightness - move darker tones toward cool / darker hues on the colour
  wheel and lighter tones toward warm / lighter hues (`ramp5` does it).
- **Band compression**: keep the steps between tones from reading as rings - narrow highlight, terminator and
  rim bands, wide base and light bands; band widths vary along the form.
- **Faces**: avoid gradients where possible - a flat face is mostly ONE solid tone; volume comes from the
  differing tones of neighbouring faces, lit edges, reflections and AO, not from a gradient across the face.
- **Material progression** (`python3 scripts/shading.py demo chart.png` draws it): 1 flat -> 2 form shadow
  (light / base / shadow faces) -> 3 highlight + terminator + lit edges -> 4 reflections (diagonal streaks on
  glass and metal) + bounce light -> 5 rim light + projected shadow + AO. Gold/steel spheres, a glass pane, a
  steel cube and a chrome cylinder go through all five; finished textures are stage 5.
- `shading.sphere5(nx, ny, stage)` and `shading.cylinder5(side, stage, chrome)` return the tone index for
  any ball, dome, rivet, knob, pipe, handle spoke or hinge knuckle.

## 3. Colour palette - five tones per main colour
| tone | use |
|------|-----|
| Highlight | the brightest pixels: edges facing the light, glints |
| Light Midtone | lit faces |
| Base Color | the material itself |
| Dark Midtone | faces turned away, the lower half |
| Shadow | recesses, contact shadows, cracks |
An outline / gap colour (near-black of the same hue) may come on top for structure. Do not only change
brightness: shift hue and saturation a little (shadows cooler or toward the material's dark hue, highlights
warmer or desaturated) - `shading.ramp5('#hex')` builds such a ramp. A measured reference palette (a pack being
replicated 1:1) wins over this rule; anything new follows it.

## 4. Pixel art
- Every pixel is a hard square: no blur, no smoothing, no anti-aliasing, no semi-transparent pixels.
- Meaningful clusters (2-6 px streaks, chips, grain lines) instead of single-pixel noise.
- No photographic gradients and no all-over dithering: gradients are bands of the five tones; a checker
  pattern only as a deliberate texture (e.g. coarse cloth), never as a blend between two tones.
- Stepped transitions typical of good pixel art.
- Readable at the original size and when enlarged.

## 5. Material-specific shading
| material | how |
|----------|-----|
| stone | cool shadows, irregular chips, dark cracks |
| wood | shading along the grain, darker gaps between boards |
| metal | contrasting highlights and hard light/shadow transitions; chrome = glint, light, DARK reflection band, base, bounce light |
| grass | variations of greens, local shadows and light spots |
| leather, cloth | wider colour groups, folds, contact shadows |
| sand, earth | small tone variations without strong contrast |

## 6. Minecraft compatibility
- Keep the original resolution, UV layout and element positions unless the task is to change them.
- Seamless textures: colours, details and shading must match on opposite edges (`shading.py check --tile`).
- A repeating tile must not carry a directional light gradient across it (it shows as stripes when tiled):
  light the details inside the tile, keep the tile's average flat.
- Do not change the silhouette, geometry or structure without a reason.

## 7. Quality criteria
Volume that is clear but controlled; an obvious light direction; readable details and materials; a consistent
palette; crisp pixels without blur; a natural spread of lights, midtones and shadows.

## How this skill implements it
- `scripts/shading.py ramp5 '#5a6578'` prints Highlight / Light Mid / Base / Dark Mid / Shadow (+ outline) with
  hue and saturation shifts; `ramp5()` in Python returns them.
- `scripts/safe.py` metal: 5 tones + outline, `tone(t)` quantises to bands (no dithering), plates have a
  stepped vertical gradient, a diagonal sheen band, brushed streak clusters and darker edges (AO); chrome
  uses `chrome()` bands; contact shadows under raised parts.
- `scripts/item_icons.py`: ramps per material, outline from the dark end, stroke clusters instead of noise.
- `scripts/art.py` / `props.py`: structured textures (planks, bricks, cobble) instead of noise.
- `shading.py check OUT.png --kit kitchen` (or `safe`): every colour that comes from a ramp the kit declares
  counts as that material; only colours outside all ramps are grouped by hue - use it for scenes with several
  materials of similar hue (light wood, walnut, brass), where plain hue groups would add them up.
- `shading.py check` reports: colours per hue group (> 6 tones per group = too many), single-pixel noise,
  checker dithering, semi-transparent pixels, light direction (are top-left-facing edges lighter?), and with
  `--tile` the edge mismatch. Fix everything it flags before handing over.
