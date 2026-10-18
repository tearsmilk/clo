# Materials library: ramps, seamless tiles, fill()

`scripts/materials.py` gives every block material a five-tone ramp and a seamless tile at two densities,
and paints any pixel mask with it. Use it for anything built from Minecraft materials: GUI frames and
plates, props, houses and buildings in scenes, item and block icons, button faces. 207 materials;
`python3 scripts/materials.py list` prints them, `chart OUT.png [--hd]` shows them.

## What is in it
| family | materials |
|--------|-----------|
| woods (43) | planks, log (bark side), log top (end grain) and stripped log of oak, spruce, birch, jungle, acacia, dark oak, mangrove, cherry, crimson / warped (stems), bamboo (planks, block, block top) |
| stones (40) | stone, cobblestone, mossy cobblestone, stone bricks (mossy, cracked, chiseled), granite, diorite, andesite (+ polished), smooth stone, deepslate (cobbled, polished, bricks, tiles), tuff, calcite, blackstone (+ polished), sandstone, red sandstone, cut sandstone, bricks, mud bricks, prismarine, end stone (+ bricks), purpur, quartz (block, bricks, pillar), obsidian, netherrack, nether bricks (+ red), basalt |
| soils (18) | dirt, coarse / rooted dirt, grass top, grass side, podzol, mycelium, sand, red sand, gravel, clay, mud, snow, ice, packed ice, soul sand, farmland, dirt path |
| metals (10) | iron, gold, copper, exposed / weathered / oxidized copper, netherite, raw iron / gold / copper blocks |
| gem blocks (6) | diamond, emerald, amethyst, lapis, redstone, coal |
| ores (8) | coal, iron, gold, copper, diamond, emerald, lapis, redstone - in stone, or `base='deepslate'` |
| fabrics (20) | wool in the 16 dye colours, leather, velvet, canvas, carpet (patterned rug) |
| others (24) | glass, tinted glass, water, lava, slime, honey, hay bale, bookshelf, terracotta, parchment, bone block, cracked ice, moss block, glowstone, leaves with holes (oak, birch, spruce, cherry, jungle, acacia, dark oak, mangrove, azalea, flowering azalea) |
| building (6) | wood shingles, clay roof tiles, slate roof, thatch, iron bars, ladder |
| dyed (32) | concrete and terracotta in the 16 dye colours |

## Densities
- `k=1` = vanilla density: a block face is 16x16. `k=2` = HD: the same block at 32x32 (2 texture px per
  GUI px, like `modes_hd.py`).
- HD is drawn natively, never scaled: 2 px joints with the shadowed row first, a second lit row on boards,
  wavy grain with knots and nail holes, rivets on metal, nuggets of 2-3 lumps in ores, cut rhombi for
  emeralds, pointed leaves with a midrib, fish-scale roof tiles, curls with a highlight in wool, title
  labels on books. One pixel size per set (`references/pixel-art-craft.md`): do not mix k=1 and k=2 tiles in
  one picture.

## Ramps
- One `shading.ramp5` ramp per material (`[outline, shadow, dark mid, base, light mid, highlight]`, RGBA),
  `ramp(name)` returns the main one, `ramps(name)` all of them, `RAMPS[key]` by key; every ramp is also a
  module global `R_<KEY>`, so `python3 scripts/shading.py check X.png --kit materials` counts each as one
  material.
- Matte materials are soft (`soft` 0.6-1: wood, stone, soil, fabric), metals and gems keep the contrasty
  ramp (`soft` 0-0.35: "metal = hard transitions"). Dark hues (blue, purple, red wool) get a lower `soft`
  so their values still spread. Lava's ramp turns hue to red in the darks and to yellow in the lights.
- A second ramp only where a second material really is there: moss on stone, ore in stone, patina on
  copper, bark round a log top, birch marks, nether glow veins, books on a shelf, pyrite in lapis.

## How each kind is drawn (what makes it read)
Everything is lit from the top-left inside the tile: a raised thing has a lit top-left rim, a dark
bottom-right rim and casts a one-step shadow down-right (`lump`); a recess has a shadowed top-left wall, a
dark floor and a lit far wall (`pit`). Texture is clusters (2-6 px streaks, chips, lumps), orphans are
cleaned, 1 px lines are kept pixel-perfect across the wrap. The tile's average stays flat (no light
gradient across a repeating tile); every coordinate wraps, so the tile is seamless.
- **Planks**: four boards, a lit top row and a dark seam per board, grain streaks along the board (dark,
  some light), one staggered end joint per board (dark gap, lit end grain after it). HD: a second lit row,
  a rounded dark lower edge, wavy long grain, a knot with grain bending round it, nail holes. Bamboo is the
  same turned 90 degrees (transpose keeps the top-left light).
- **Bark**: vertical furrows wander down with diagonal steps only; the ridge left of a furrow turns away
  (dark), the ridge right of it faces the light (lit); plate cracks across the ridges; jungle gets moss,
  cherry light lenticels, birch is white with dark tapered dashes and knot eyes, nether stems carry glowing
  veins. Log tops: rounded-square rings (1 px dark lines, light / base bands), dark pith, a check crack (HD),
  a bark border.
- **Stone**: mottled dents (shadowed top-left rim) and raised patches (dark pixel cast down-right), chips,
  hairline cracks at HD. Granite / diorite / andesite / tuff / calcite / blackstone add mineral grains (bumps
  or pits) of their own tones; deepslate has wavy cleavage lines with a lit row under each; sandstone is
  wavy strata (lit top row, dark bottom row per band); end stone is pocked with pits; netherrack and raw ore
  blocks are knobbly lumps; obsidian, amethyst, prismarine (two ramps), coal block and glowstone are
  Voronoi facets, each split into a lit and a turned-away face, with glints.
- **Cobble / gravel**: Voronoi stones with dark joints (k=1: flat faces with a lit rim, joint corners
  darkest; HD: rounded by the light, 2 px joints with an outline core, chips, a glint); some stones from a
  second ramp. Moss grows in the joints first, clumps with a lit top rim, hangs in strands (HD), shadows
  the stone under it.
- **Bricks / tiles / panels** (block faces): each face lit on its top row and left column, dark on the
  bottom row and right column, its joint on the right and bottom only (one joint between neighbours);
  clay bricks vary per brick, light mortar; cracks are dark lines with a lit lip; polished stone is the
  stone's grain inside a bevel ring with polish streaks; chiseled has a carved ring and a boss.
- **Soils**: small tone changes, low contrast: dirt clods and lit pebbles with a shadow pixel, grass tufts
  (lit blades, dark blades, shadowed roots), the grass side's fringe ends in a dark pixel and shadows the
  dirt, needles on podzol, spores on mycelium, sand grains in 2 px pairs, wet streaks on mud, blue-shadowed
  drifts and a few sparkles on snow, diagonal streaks and bubbles in ice, frozen grain lines in packed ice,
  furrows on farmland.
- **Metal**: a block-face panel with a lit top / left bevel, plates split by seams, short brushed streaks,
  a ragged diagonal sheen band (light mid, highlight core at HD), rivets (highlight top-left, shadow
  bottom-right). Patina grows from seams and joints outward and keeps the metal's tone index, so plates
  still read: exposed (a few spots in the seams), weathered (about half), oxidized (all patina, matte,
  drips).
- **Gem blocks**: diamond = 2x2 brilliant cuts (lit top / left facets, dark right / bottom, a table with a
  glint), emerald = octagonal step cuts in a running bond, lapis = framed panel with veins and pyrite
  nuggets, redstone = framed panel of glowing studs.
- **Ores**: the host stone (stone or deepslate) with clusters of the mineral as raised lumps (HD: 2-3
  nuggets per cluster), set in with a selective rim in the stone's darks (dark mid top / left, shadow
  bottom / right); emeralds are cut rhombi, redstone is bright grains, copper shows a patina speck.
- **Fabrics**: wool = overlapping curls on a jittered grid (lit upper-left arc, dark lower-right arc,
  highlight at HD); leather = a broken crease network (dark line, lit lip) with worn patches; velvet =
  ragged diagonal sheen bands with short highlight runs and nap dashes; canvas = a coarse weave (4x4 cell at
  k=1, alternating H / V pills at HD) with slub threads; carpet = gold lattice (lit upper line, shadow under)
  with navy medallions.
- **Glass**: a frame (highlight top / left, dark bottom / right), the middle left transparent - no
  semi-transparent pixels - diagonal highlight streaks; tinted glass fills the pane with opaque smoky
  clouds. **Water**: horizontally stretched swells, highlight on crests, shadow in troughs (`frame=` moves
  them). **Lava**: molten channels orange -> yellow -> pale, dark crust plates with lit rims. **Slime /
  honey**: a glossy shell round a denser inner cube, a glint. **Leaves**: two passes of leaves (deeper,
  darker first), each lit on its top-left half, each shadowing the leaves under it, gaps filled to ~75-80 %,
  the rest transparent holes; spruce = narrow needle tufts, cherry / azalea add five-petal flowers.
- **Roofs**: rows overlap downward - each row starts in the shadow of the one above, shingle faces lit
  left / dark right, lower edge dark; HD clay and slate get round fish-scale bottoms (k=1 is too small for
  a curve: staggered tiles). Thatch strands hang 1-2 px over the next row. Iron bars and the ladder are
  open (transparent) tiles.

## fill(): paint any mask
`fill(img, mask, name, k=1, bevel=True, outline=True, origin=None, **opts)` paints a set of (x, y) or an
image (alpha / value > 127) with the material: the tile (anchored at the mask's top-left or `origin`),
a lit band on the top / left (+1 tone; HD +2 then +1), a darker band on the bottom / right, and a selective
outline in the material's own darks (shadow tone on the lit side, outline tone elsewhere; glass and bars
use a light outline). It also: removes corner pixels that would make an L in the outline (clean rounded
corners), runs the pixel-perfect pass on the result, forces the lit / dark rim where a texel would invert
it, hides the glass frame so a filled shape is one pane. Transparent texels (leaves, glass) stay holes.
`fill_layers()` returns {texture, bevel, outline} dicts, `fill_parts()` the same as modes.Parts items.
Contact shadows belong to the caller (the chart draws a hard one-tone shadow down-right on its backdrop).

## API and CLI
```python
from materials import render, parts, fill, fill_parts, ramp, ramps, tile, circle, CATALOG, MATERIALS, is_face
img = render('oak_planks', k=2)              # 32x32 RGBA tile (tight=True crops a sprite out of it)
render('diamond_ore', base='deepslate')      # ores in deepslate
render('white_wool', color='#6a3cb0')        # any one-ramp material in another colour (custom_ramp)
render('water', frame=3)                     # water / lava frames (8 loop)
items = parts('mossy_cobblestone', k=2)      # layers as modes.Parts items: stones, joints, detail, moss
CATALOG['gold_block'](k=2)                   # = render('gold_block', 2)
fill(canvas, rrect(0, 0, 47, 23, 4), 'cobblestone', k=1)
fill(canvas, circle(20, 20, 11), 'gold_block', k=1)
```
```bash
python3 scripts/materials.py chart OUT.png [--hd]       # all tiles by family (x4 / HD x3) + a 1:1 repeat + fill() samples
python3 scripts/materials.py render NAME OUT.png [--hd] [--seed N] [--base deepslate] [--color '#hex'] [--frame N]
python3 scripts/materials.py parts NAME OUT_DIR [--hd]  # NN_layer.png + layers.json + _sheet.png + NAME.aseprite
python3 scripts/materials.py parts slab:NAME OUT_DIR    # fill() on a slab (or disc:NAME) as texture / bevel / outline
python3 scripts/materials.py list
```
Deterministic: seeds come from crc32 of the name, density and `seed`; the same call gives the same pixels.

## Checking
- Tiles: `python3 scripts/shading.py check TILE.png --tile --kit materials`. Fill samples (a slab of every
  material at both densities) pass `shading.py check` with no warnings: light from the top-left, no noise,
  no doubles, no jaggies.
- What `check --tile` still reports on tiles, and why it is not a defect:
  - "top-/left-facing edges darker" on opaque tiles: the check treats the tile border as a silhouette; a
    seamless tile has none. Light direction is checked on the fill samples instead.
  - "edges do not match" on seamless tiles: it compares the wrap pair with the mean HORIZONTAL neighbour
    difference, so anything with horizontal structure (planks, strata, rows) trips it; on a copy rolled by
    half it fires just as often. The tiles are drawn on a torus; measured over all 310 seamless tiles, the
    wrap pair is an outlier (z > 2.5 among the adjacent pairs) as often as a control pair in the middle of
    the tile (21 vs 20 of 620) - no seam.
  - Block faces (`is_face(name)`: bricks, panels, metal and gem blocks, glass, gel, log tops, polished stone,
    bookshelf, grass side, bars, ladder) carry their joint / frame at the tile edge on purpose - they tile
    as a grid of blocks, like the game's own. Check them without `--tile`.
  - Deliberate: concrete has a value spread under 40 (it is flat by nature); leaves report jaggies on the
    hole edges (organic outlines); single doubles at the tile edge (the check does not wrap).

## Adding a material
1. A ramp: `_ramp('basalt2', '#hex', soft=0.7)` next to its family (matte 0.6-1, metal / gem 0-0.35).
2. A generator `g_x(t, R, ...)` drawing on the Tile `t` (size `t.S` = 16k, density `t.k`, `t.rnd` seeded):
   start a named layer with `t.layer('name')` per part, draw with `t.put` (coordinates wrap), `t.shift(x, y,
   d)` to move a pixel along its own ramp, and the helpers `field` (seamless value noise, rank-normalised:
   thresholds are area fractions), `voronoi`, `spots`, `blob`, `lump`, `pit`, `streak`, `wander` (clean 1 px
   cracks), `bevel_cell`, `moss`, `verdigris`; finish with `clean(t, keep=glints)`. Draw k=2 natively (more
   detail, not bigger blobs). `tile()` runs the wrap-aware pixel-perfect pass after it.
3. Register it: `_mat('name', 'family', g_x, ['ramp_key', ...], **params)` (the first ramp is the main one;
   `fill_hide=('frame',)` hides layers in fill(), `edge=(lit, dark)` sets fill()'s outline tones); add the
   generator to `FACE_GENS` if the tile is a block face; if it takes a second ramp positionally, add it to the
   tuple in `tile()`.
4. `chart` both densities, look at the tile at x4 and at its 1:1 repeat, run the checks.
