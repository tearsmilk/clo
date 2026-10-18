# Buildings kit: little houses, towers, workshops, a village

`scripts/buildings.py` draws 27 original blocky buildings in a frontal view (the facade straight on, the roof
seen slightly from above, like the barn in `modes_hd.py`) at two densities, built from parts, with day /
night / snow variants and three sizes, plus `village()`, which composes several of them into one scene. Use
it for scene menus (warps, a village hub, quest boards), tile illustrations, lore pages, map markers.
`python3 scripts/buildings.py list` prints the catalog, `chart OUT.png [--hd]` shows all of them.

## What is in it
| group | buildings (catalog names) |
|-------|---------------------------|
| houses | `cottage` (oak + cobblestone, front gable, shutters, flower boxes), `stone_house` (two storeys, quoins, slate hip roof, two chimneys), `log_cabin` (stacked logs with round ends, side chimney, woodpile), `birch_house` (white birch posts, clay tiles, porch), `spruce_aframe` (roof to the ground, big gable window, balcony), `desert_house` (sandstone, parapet, vigas, curtain, cactus pot), `igloo`, `mushroom_house`, `treehouse` |
| towers | `tower` (round, battlements, pennant), `wizard_tower` (crooked hat with stars, arcane windows, orbs, crystals), `lighthouse` (bands, gallery, lantern room; beams at night), `guard_post` (wooden watchtower) |
| castle | `castle_gate` (two towers, curtain wall, lancet gateway, portcullis, banners, torches), `castle_keep` (turrets with cones, flag turret, steps) |
| village | `chapel` (rose window, belfry with bell, spire, cross), `tavern` (jettied timber frame, mug sign, barrels), `market_stall` (awning, crates of produce, coin sign, lamp post), `forge` (glowing furnace, anvil, quench barrel, tools), `well`, `barn` (gambrel roof, X doors, hay loft, silo, bales, vane at HD) |
| mills | `windmill` (tapered tower, X or + sails with canvas), `watermill` (timber upper floor, wheel in a stream that spills over the edge) |
| outdoors | `tent` (A-tent with a receding roof plane, campfire, log seat, bedroll), `mine_entrance` (hill with ore, timber frame, rails, minecart, pick sign), `portal_ruin` (obsidian with crying blocks, swirling portal, netherrack, ruins), `dock` (pier over water, rowboat, lamp, reeds) |

## Densities, sizes, options
- `k=1` = vanilla GUI density (a cottage is ~48 px wide with its island), `k=2` = HD (~94 px). HD is drawn
  natively from the same geometry with more detail: 2 px frames, grain streaks and nails on planks, lit top
  rows and chips on bricks, cracks and moss on ashlar, Z-braced shutters, rails and strap hinges on doors,
  2x2 flower heads, ridge tiles, weathervane, keystones. Never scale one density into the other, never mix
  them in one picture (`references/pixel-art-craft.md`).
- `size='s' | 'm' | 'l'`: fewer / more bays, storeys, height; window counts are fitted to the wall
  (`fits()`), so a variant never crams openings together. `seed=N` varies stones, flowers, smoke, tiles.
- `night=True`, `snow=True` (combinable), `ground=False` (no island: for your own scenes).

## The view and the forms
- **Facade**: flat, mostly ONE tone per material (texture only as clusters); volume comes from planes that
  differ: proud beams / sills / lintels / quoins (lit top row, dark bottom row, a cast shadow), recessed
  windows and doors (shadow row under the top bar), the roof's overhang shadow on the wall.
- **Roofs** (`gable_roof`, `hip_roof`, `roof_px`): a front gable is a thick inverted V - courses parallel to
  the slope, left slope lit, right slope a tone darker, a lit rim, cut eave ends, a barge board (`trim`).
  Steep slopes (A-frame, spire) are too narrow for courses across them: the courses run down the slope,
  edge-on (lit outer strip, course lines every 3/5 rows). `top_fn` gives other profiles (`gambrel_top` for
  the barn), `solid=True` a full triangle (spires, the well). An eave-front roof is a trapezoid (hip ends:
  lit left, dark right, hip lines at HD), fascia along the bottom, ridge tiles on top. Styles: `wood`
  (staggered shingles), `clay` (barrel tiles in columns, rounded bottoms), `slate`, `thatch`.
- **Round forms**: `dome_tone(nx, ny)` and `cyl_tone(nx)` give the tone of a ball / dome / cylinder lit from
  the top-left with compressed bands; towers add joints that crowd toward the sides (the cylinder turning
  away). `dome_mask()` and `steady()` keep curved silhouettes clean: per monotone stretch the stair runs
  are re-ordered so they change steadily (1-1-2-3-4, never 2-1-3).
- **Integer-clean diagonals**: windmill sails on 45 deg (`cross='x'`) or upright, wheel spokes on the axes
  and diagonals, gable slopes with integer steps (1:1, 2:1, 1:2, 1:3) - no jaggies by construction.

## Materials (all textures are world-aligned, clusters not noise)
| texture | how it reads |
|---------|-------------|
| `planks` | seams between boards, staggered butt joints, HD: lit top row per board, grain streaks 3-6 px, nails |
| `logs_h`, `log_v`, `log_end` | logs as cylinders (lit top / dark bottom; lit left / dark right), bark streaks, end grain with a ring |
| `stones` | jittered nearest-centre cells, 1 px joints, lit top-left rim, dark bottom-right, tone per stone |
| `bricks`, `ashlar` | running bond / cut blocks: mortar or dark joints, lit top-left, dark bottom-right, odd cracks and moss |
| `plaster`, `sandstone` | one flat tone with sparse 2-4 px stains / strata bands per block |
| `water`, `foliage` | ripple dashes 2-5 px; leaf blobs lit like balls with clumps and contact lines between blobs |
Ramps are module globals (`OAK`, `COBBLE`, `SLATE`, `GLOW`, ...; 76 of them). `GLOW`, `FIRE`, `PORTAL`,
`ARCANE` are emissive: they keep their colours at night.

## Parts
Every building returns modes.Parts items bottom -> top (`ground`, `walls`, `foundation`, `gable`, `beams`,
`roof`, `windows`, `door`, `flowers`, `lanterns`, `chimney`, `smoke`, `sign`, ...). A feature draws into a
named part (`S.lay(name, z, cast=...)`), so all windows are one part. Generated parts:
- `<part>_shadow` - the hard cast shadow a part throws on what is behind it (swept along its offset, one ramp
  step darker, `darker()`), placed right under the part, so hiding the part can hide its shadow too;
- `snow` - caps on every top surface (tone runs as long as the slope step, so steep slopes stay clean),
  roof planes mostly covered with a wavy edge and a shadow line, sills, icicles from the lowest roof row;
- `light` - at night, the warm pools round lights (two hard bands: inner strong, outer half), kinds `lamp`,
  `fire`, `portal`, `arcane`.
Move / hide with `modes.override(items, {'smoke': None, 'sign': {'dx': 4}})`, compose with `modes.compose`,
export with `parts NAME OUT_DIR` (PNGs + `layers.json` + `_sheet.png` + `.aseprite` + the rebuilt PNG; the
parts rebuild the picture byte for byte).

## Night, snow
- Night is a colour map, not a filter: every ramp colour maps 1:1 to a moonlit one (`night_c`: darker,
  cooler, a little desaturated, value order kept), emissive colours stay, windows switch to lit glass with
  a bright core, open doorways get a dark warm interior with a lit floor. The night and lit versions of every
  ramp are declared as module globals, so `shading.py check X.png --kit buildings` counts them as ramps.
- Snow: grass, sand and stone grounds turn to snow; snowy roofs, sills, caps on chimneys, fences, lanterns.

## Village
`village(width=160, height=100, seed=0, k=1, night=False, snow=False, names=None)` (GUI px; the canvas is
width*k x height*k): sky (day bands + blocky clouds / night with stars and a cratered moon, raw colours),
hazy hills with a tree line, the field, a road with lamp posts, a back row of buildings from `VILLAGE_POOL`
with footpaths to the road and cast shadows on the grass, trees between them (spruce in snow), a front row of
small buildings (`well`, `market_stall`, `tent`) and fenced gardens with crops, near trees. Parts are
prefixed per object (`cottage0/roof`, `tree3/tree`, `lamp52/lamp_posts_lamps`), rows are z-ordered so nearer
objects cover farther ones; one `light` part for the whole scene.

## API / CLI
```python
from buildings import render, parts, village, CATALOG, Scene, build
img = render('tavern', k=2, night=True, size='l')        # tight RGBA image
items = parts('windmill', k=1, snow=True, seed=4)         # modes.Parts items
S = Scene(k=1, ground=False); build(S, 'cottage', cx=40, gy=60); items, size = S.finish()   # into your scene
```
```bash
python3 scripts/buildings.py chart OUT.png [--hd]         # all buildings day/night(/snow) + a village
python3 scripts/buildings.py render NAME OUT.png [--hd] [--night] [--snow] [--size s|m|l] [--seed N] [--no-ground]
python3 scripts/buildings.py parts NAME OUT_DIR [--hd] [...]   # NAME can be 'village'
python3 scripts/buildings.py village OUT.png [--hd] [--night] [--snow] [--width W --height H --seed N]
```

## Quality gate
`shading.py check --kit buildings` on all 27 x 2 densities x day / night / snow: no semi-transparent pixels,
no dithering, no tone-count warnings (every colour is a declared ramp), light from the top-left, value spread
fine, villages "ok". Every part is pixel-perfected (dark 1 px lines and outline tones), and `_clean_seams`
removes L-corners where lines of two parts meet. What stays, deliberately:
- jaggies on silhouettes = icicles, snow-cap ends, chimneys, lanterns, flags, wheel paddles, signs (features);
- single pixels 8-12 % on a few k=1 sprites (1 px panes, handles, flower heads, thin cast-shadow slivers,
  night pool band edges) - k=1 has no room for clusters there;
- tent at night is lit from the right (its campfire), so its left edge reads darker.

## Adding a building
1. Write `def name(S, cx, gy):` with a one-line docstring summary; `cx` = centre, `gy` = ground row (the
   building stands on `gy - 1`). Use `S.u(n)` for geometry, `S.kv(a, b)` for per-density details,
   `_sz(S, s, m, l)` for sizes, `S.rnd(...)` for anything random.
2. Build it from the helpers: `foundation`, a wall texture into `S.lay('walls', 0)` + `outline`, `gable_roof`
   or `hip_roof`, `window(...)` / `door(...)`, `lantern`, `chimney` (+ smoke), `hanging_sign`, `fence`,
   `barrel`, `crate`, `pot`, `awning`, `banner`; new materials get a ramp at the top (`_r5(hex, soft=...)`).
3. End with `ground(S, x0, x1, gy, foot=(left, right), paths=[(door x0, door x1)])`; register lights with
   `S.light(x, y, r, kind)` when `S.night`, ledges with `S.ledge`, roof planes with `S.field`.
4. Add it to `CATALOG`; run `render` at both densities with `--night` / `--snow` / `--size s|l`, look at it
   x4, run `shading.py check --kit buildings`, fix, repeat.
