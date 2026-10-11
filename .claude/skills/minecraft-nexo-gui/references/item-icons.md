# 16x16 item icons (food, drinks, crops, drops)

Measured on a 62-icon food set (bread, meat, fruit, drinks in glass, soups, sweets). Use these rules
whenever you draw item icons for Nexo items, shop slots or menu buttons; `scripts/item_icons.py` implements them.

## Numbers
| what | measured |
|------|----------|
| canvas | 16x16, every pixel alpha 255 (no soft edges) |
| margin | 1 px empty on most sides (11/62 exactly 1-1-1-1); flat food uses the full width (0 px left/right) |
| coverage | 47% of the canvas on average (bottles ~26-30%, pancakes/waffles ~65%) |
| colours | 6-24 per icon, 11.8 on average; one material = one ramp of 6-9 steps |
| outline | the darkest step of the material it wraps - darker than the inside on 56/62 icons, never pure black; only glass has a light outline |
| light | from the top-left (47/62 icons lighter on the top-left half) |
| tone bands | outline step ~0.05 of the ramp; first ring inside ~0.46 on the shadow side, ~0.58 on the lit side; deeper ~0.55-0.67 |
| texture | inside, 57-100% of neighbouring pixels differ in tone: short 2-3 px strokes of neighbouring steps, following the long axis (baguette, sausage) or the edge (round things) |
| highlight | the lightest step on only 2-5 pixels |

## Ramps
- Dark -> light, 6-9 steps. Value rises from ~0.45x the main tone to full, then the light end loses saturation
  (orange: s 87% -> 29% in the last two steps) instead of turning white.
- Hue shift: yellows darken toward orange-brown (butter 44 -> 25 deg; a dark yellow without the shift turns
  olive and looks rotten); fruit lights shift toward yellow (orange 6 -> 38 deg, banana 7 -> 62 deg).
  Browns (toast, chocolate) keep their hue and only change value.
- One ramp per material, shared across the set: every chocolate item uses the same chocolate ramp, every soup
  the same bowl ramp, every glass the same 5 blues. That is what makes a set look like a set.
- `item_icons.RAMPS` has measured ramps (bread, toast, butter, cheese, pancake, fries, chocolate, honey,
  tomato, leaf, orange, meat, meat_raw, sausage, glass, cork, wood) and generated ones in the same shape
  (apple, milk, pumpkin, carrot, berry, grape, wheat, egg, corn, jam, cream, cocoa, fish...).
  New material: `make_ramp('#hex')` with the main tone; check the darks are not olive or grey.

## Shapes and composition
- Long things on the diagonal bottom-left -> top-right (baguette, sausage, bacon, carrot, kebab).
- Round things fill ~12x12, a dip or a calyx/stem/leaf on top breaks the circle.
- Flat food (pancakes, waffles) uses the full 16 px width and shows layers: each layer = a dark line, a mid
  band, a light band; the top face is an ellipse with the highlight.
- Bowls: the soup surface is a wide ellipse above, the bowl front covers its lower half; garnish on top.
- Glass (bottles, jars, cups, mugs): light wall on the left, dark wall on the right and the bottom row,
  the empty part of the glass is transparent (the slot shows through), the liquid has its own ramp
  (lit left, dark right and bottom, light surface line, one white glint), cork/lid on top.
- Details are drawn, not shaded: scores on bread (dark cut + light lip), holes in cheese (dark top-left,
  light bottom-right), lattice on pie, grain on wheat ears, seeds on strawberries.

## Variants
- Palette swap of one shape: raw -> cooked, green/orange/white frog legs, flavours of a shake.
  `item_icons.swap(img, 'meat_raw', 'meat')`.
- Base + topping layer: pancake / pancake with honey / with chocolate; toast / honey toast.
- Keep one silhouette per family so players recognise "this is a drink" before reading the name.

## Using item_icons.py
```bash
python3 scripts/item_icons.py --list                                   # recipes and ramps
python3 scripts/item_icons.py out/icons jar:honey bottle:milk cup:juice_apple mug:cocoa:cream \
    bowl:soup_pumpkin fruit:apple tomato loaf:bread long:bread carrot stack:pancake:honey slice:cheese \
    drumstick:meat pie:bread:berry egg bundle:wheat --aseprite         # + layered .aseprite per icon
```
Recipes: `bottle`, `jar`, `cup`, `mug`, `bowl`, `fruit`, `tomato`, `loaf`, `long`, `carrot`, `stack`,
`slice`, `drumstick`, `pie`, `egg`, `bundle`, `rounds` (sliced food: three flat discs with a skin ring and a
light core - `rounds:carrot`, `rounds:tomato:cheese` adds seeds); arguments after the name are ramps
(`jar:jam`, `cup:berry`, `fruit:pumpkin`, `bowl:soup_beet`).
Cut food reads as cut when the inside shows: a cross-section (rings, core, seeds) on a flat face, a darker
skin ring round it - a plain round shape reads as a whole fruit or a bun.

In a spec, any 16px icon source can be a recipe: `"icon": "item:jar:honey"` in `nexo_items`, buttons with
`style: "none"` and `extra_items[].preview`.

New item that no recipe covers - compose it from masks and ramps:
```python
from item_icons import Icon, ellipse, poly, capsule, rect
ic = Icon()
ic.part('body', ellipse(2, 4, 13, 14), 'melon')                       # shaded + outlined with the ramp
ic.part('rind', {p for p in ellipse(2, 4, 13, 14) if p[1] >= 12}, 'leaf', outline=False, highlight=0)
ic.pixels('seeds', {(6, 8): (30, 20, 20), (9, 9): (30, 20, 20)})       # hand-placed details
ic.save('melon_slice.png', aseprite='melon_slice.aseprite')
```
`shade()` options: `base` (main tone 0..1), `contrast`, `rim`, `texture` (0 = smooth, 0.16 default,
0.3 grainy), `highlight` (pixels of the lightest step), `flat` (slices, plates), `light`, `outline`.

## Check before shipping
- Look at the icon at x1 on the slot grey (#8b8b8b) and on the dark tooltip background - it must read at x1.
- Outline darker than the inside, no black, no semi-transparent pixels, 1 px margin.
- Same family = same silhouette and the same ramps.
- Third-party icon packs are for measuring style only; draw your own items.
