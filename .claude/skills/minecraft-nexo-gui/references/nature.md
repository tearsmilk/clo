# Nature kit: trees, plants, crops, rocks, props, biome strips

`scripts/nature.py` draws original blocky-but-organic nature art for GUI scenes, mode cards and shop
pictures: 76 drawables plus `scatter()`, which composes a whole ground strip for a biome. Everything comes at
two densities and is built from parts. `python3 scripts/nature.py chart OUT.png [--hd]` shows it all.

## What is in it
| group | names |
|-------|-------|
| trees (`season`, `size`) | oak, birch, spruce, jungle, acacia, dark_oak, cherry, palm, dead_tree, swamp_oak, giant_red_mushroom, giant_brown_mushroom |
| plants, flowers | bush, berry_bush, rose_bush, tall_grass, fern, dead_bush, poppy, dandelion, cornflower, blue_orchid, tulip_red / _orange / _white / _pink, allium, lily_of_the_valley, sunflower, red_mushroom, brown_mushroom |
| crops | wheat, carrots, potatoes, beetroots (`age` 0..3), pumpkin (`carved=True`), melon |
| desert, water | cactus (`arms`, `flower`), sugar_cane, bamboo, vines, lily_pad, pond, kelp, coral |
| rocks, wood | rock, mossy_boulder, coal / iron / copper / gold / redstone / lapis / emerald / diamond _rock, log, stump (`kind` = oak / birch / spruce / dark_oak) |
| fire, light | campfire, soul_campfire, torch, soul_torch, lantern, soul_lantern, hanging_lantern (`frame=N` wavers the flames) |
| signs, fences | sign, hanging_sign, fence (`sections`), fence_gate (`open=True`) - `wood` = oak / spruce / birch / dark_oak |
| props | hay_bale, barrel, crate, chest, beehive (with bees) |
| terrain | lava_pool, snow_drift, ice_spikes |
| biome strips | `scatter(width, height, biome, seed, k)`: forest, plains, desert, snowy, swamp, cherry_grove |

Seasons (`season='spring' | 'summer' | 'autumn' | 'winter'`): spring = fresh light leaves + white blossoms
(cherry: petals drift and lie on the ground), summer = full green + apples on the oak, autumn = orange / red /
yellow puffs + falling leaves, winter = dull leaves under snow caps, snowy ground, a frozen pond. Spruce keeps
its needles; props get snow on top.

## Scale, view, densities
- Frontal view like `buildings.py`: things straight on, ground and block tops seen slightly from above. A
  block-sized prop (crate, hay bale, chest, melon) is 16 px wide at k=1, a flower about 14 px tall, a tree
  2-3 blocks tall (oak 46 px), so props, flowers and trees mix in one scene.
- k=1 = vanilla GUI density, k=2 = HD (32x32 density). HD is drawn natively by the same code with its own
  detail choices (`S.kv(a, b)`): leaf marks of 4-8 px instead of 2-3, bark ridges, kernels, nails, veins,
  petal shading, 2x2 vine leaves - never an upscale.
- Every drawable stands on its base line `gy` (scene coordinates). `ground=True` (default) adds a small
  island under it (grass / dry grass / podzol / sand / snow / stone / gravel / swamp / seabed, chosen by the
  item); `ground=False` gives the bare sprite.

## How things are drawn (the rules that make them read)
- **Ramps**: one five-tone ramp per material, declared at module level (`shading.py check --kit nature`
  counts each as one material). Matte things `soft` 0.5-1 (leaves, bark, soil, snow); metal and gems
  contrasty (`soft=0`); fire, lava, glow and embers are hand-set (`_ramp_hex`) so their lights stay
  saturated yellow instead of turning pale. Emissive colours never darken in a shadow.
- **Light** from the top-left everywhere; selective outlines in the material's own dark tones (`outline`:
  shadow tone on the lit top / left, outline tone on the shadow side), no outline where a thing touches the
  ground; the bottom row resting on the ground gets one step darker (contact AO, done by `build`).
- **Leaf crowns** (`crown`): a dark back mass (the shaded inside of the crown, no highlight) under front
  puffs, each puff its own part, drawn top -> bottom so a lower puff sits in front of the one above: its
  lit top rim against the dark underside behind is the scalloped layering that reads as foliage. Every puff
  is lit as a ball AND by its place in the whole crown (`_lam`: mostly side light, so a puff's middle is
  base, its top-left light, its bottom-right dark). The silhouette is a ring of leaf bumps (`lumpy`); leaf
  marks (`leaf_marks`, a lit leaf over its own shadow) give texture as clusters; see-through holes are cut
  in the back mass between puffs so the limbs show, their upper edge in shadow; one pixel-perfect outline
  round the whole crown, split between the puffs (`perfect_ring`). Front puffs cast a 1-2 px shadow on what
  is behind.
- **Trunks and limbs**: a cylinder per row (`cyl_tone`), bark by `style` - furrow (dashed furrows two
  steps darker, a lit ridge at HD), birch (black dashes), smooth (lenticels), rings (palm), plates (acacia,
  dead wood); roots are short curved limbs gripping the ground with dark crevices. Limbs share one mask and
  are shaded together (`shade_wood`) so joins have no seams.
- **Spruce**: stacked drooping tiers, each a skirt lit on its left with a fringe of needle tips that casts on
  the tier below; needle strokes slant down and outward; snow settles under each overhang. **Palm**: arching
  fronds (lit midrib, leaflets hanging from both sides, far fronds darker), a ringed curved trunk.
- **Flowers**: a stem (1 px k=1, 2 px lit / dark HD), stroke leaves with one shadow pixel, a head from
  `bloom` (petals on a tilted ring, far ones drawn first; at k=1 the head is one lit ball, the petals only
  in the outline). Tulips are a three-petal cup (lit / base / shaded petal), allium a floret ball.
- **Blocks** (`box_faces` + `box_shade`): oblique front + top + right side; the top lit, the front base,
  the side dark, a highlight on the front-top edge; textures go on each face (hay strands, crate frame and
  brace, chest lid seam and latch, hive boards and honey, melon stripes).
- **Rocks** (`boulder`): a jittered polygon cut into flat facets fanned from a peak plus a front face; one
  tone per facet by the way it faces, a lit ridge on the lighter side of each edge, cracks, chips. Ores are
  lit nuggets in a dark socket; moss is a cushion thick on the crown, thin on slopes, with drips.
- **Water** (`water_patch`): far edge lit (sky reflection), base, darker near edge, broken ripple arcs,
  glints on the left, a bank with its shadow on the water. **Lava**: saturated bright cores, crust plates
  with glowing edges, a warm-lit stone rim. **Light pools** (`S.glow`): the ground round a fire / torch /
  lantern / lava turns one ramp step lighter - a hard band, no blur.
- **Snow** (`snow_cap`): settles on every upward surface of the visible masks (puffs, limbs, caps, block
  tops): a highlight row, base, a blue shaded lower row, a lip on flat runs, a pale outline above.
- **Shadows**: `ground_shadow` = the flat lens a standing thing throws to the right on the ground (two steps
  darker) + a contact line under its base; `cast=(dx, dy, steps)` on a part = its hard shadow on what is
  under it, kept as part `<name>_shadow`.
- **Cleanup** (`Scene.finish`): each part pixel-perfect (outline and shadow-tone lines, dark strokes), then
  once more on the whole composite with each fix written into the topmost part owning that pixel - so
  L-corners that two parts make together disappear too.

## scatter()
`layout()` plans the strip in GUI units (so k=1 and HD show the same scene): a ground strip (top face +
soil face), then per biome three rows - tall things at the back, mid-size in the middle, small ones in front
- walked left to right with each thing's measured width (`extent`) plus the row gap (negative = overlap, a
dense forest), a weighted seeded choice and a skip chance; extras per biome (swamp pools with lily pads, a
desert oasis with palms, petal or leaf litter). Things are drawn back -> front, each prefixed `name_i/`, their
ground shadows falling on what is behind them. The biome table `BIOMES` is plain data: add rows or
candidates there.

## API / CLI
```python
from nature import render, parts, scatter, layout, CATALOG, BIOMES, SEASONS
img = render('oak', k=2, season='autumn', size='l', seed=3)     # tight RGBA
items = parts('cherry', k=1, ground=False)                       # modes.Parts items, bottom -> top
items = scatter(160, 80, 'forest', seed=3, k=2)                   # canvas (160*k) x (80*k)
from modes import override, compose
items = override(items, {'falling_leaves': None, 'leaves_8': None})
```
```bash
python3 scripts/nature.py chart OUT.png [--hd]                   # everything, oak seasons, a scatter per biome
python3 scripts/nature.py render NAME OUT.png [--hd] [--season S] [--size s|m|l] [--seed N] [--no-ground]
                                    [--wood W] [--kind K] [--age N] [--frame N]
python3 scripts/nature.py parts NAME OUT_DIR [--hd] [...]        # PNG per part + layers.json + _sheet.png + .aseprite
python3 scripts/nature.py parts forest OUT_DIR                   # a biome strip as parts
python3 scripts/nature.py scatter BIOME OUT.png [--hd] [--width W --height H --seed N --season S]
python3 scripts/nature.py list
```

## Adding a new item
1. Declare its ramps at module level with `_ramp('name', '#hex', soft)` (matte soft >= 0.5, metal 0) or
   `_ramp_hex` for an emissive thing; add new emissive ramps to `EMISSIVE`.
2. Write `def thing(S, cx, gy, size='m', **_)` drawing into named layers: `lay = S.lay('body', z, cast=...)`,
   pixels `lay[(x, y)] = R[tone]`, geometry in GUI units through `S.u(n)`, detail per density through
   `S.kv(k1, hd)`, randomness only from `S.rnd(...)`. Reuse the helpers: `crown`, `trunk`, `limb` /
   `shade_wood`, `bloom` / `stem` / `leaf`, `box_faces` / `box_shade`, `boulder`, `water_patch`, `flame`,
   `snow_cap`, `outline`, `sphere_tone` / `cyl_tone`. Finish with `ground_shadow(...)` (and `S.glow` for a
   light) and handle `S.season == 'winter'` with `snow_cap`.
3. Return `{'ground': 'grass'}` (or another `GROUND` kind, `None` for no island; `ground_opts` to size it).
4. Register it in `_register()` and, if it belongs in a group or biome, in `GROUPS` / `BIOMES`.
5. Check: `python3 scripts/nature.py render thing /tmp/t.png [--hd]`, then
   `python3 scripts/shading.py check /tmp/t.png --kit nature`, and look at it at 1:1 and zoomed.

## Check results (and what is deliberate)
All 76 drawables at both densities: no semi-transparent pixels, no checker dithering, no ring / pillow
shading, no doubles in dark lines, the tone count per material within its ramp. What `shading.py check`
still reports and why it stays:
- jaggies on organic silhouettes (leaf bumps on crowns, fronds, flames, smoke, leaflets, facet corners of
  boulders) - the scalloped edge is the design; regular shapes (crates, barrels, signs, fences) have none;
- 8-13 % single pixels on 16 px drawables (a flower eye, cactus spines, engraved sign letters, a bee, the
  white potato flower) - single-pixel details, the HD versions are clustered;
- "top darker than bottom" where two materials meet (dark tube-coral mouths over pale sand, deepslate
  diamond rock on gravel, twigs on sand, blue flames on sand) and on some `ground=False` sprites, whose
  bottom row is a cut at the ground line rather than a lit edge.
