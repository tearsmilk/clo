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

## What the reference menus do (studied examples)

Five popular styles, all built on the same grid trick:

| example | frame | buttons | labels | extras |
|---------|-------|---------|--------|--------|
| "Quick Menu" | vanilla grey | 3x? tiles with sunburst backgrounds, big icon | white caps with dark outline, 2 lines ("MAIN\nWORLD") | group separator line between two tile blocks; bottom toolbar of 1x1 icon buttons |
| steampunk "МЕНЮ/НАБОРЫ" | ornate copper frame wider than the window, gears, header tab above | cards of different widths with an illustration (a little scene) | full-width dark **bar** under each card | back-arrow bar at the bottom; player inventory hidden under art |
| bento "МЕНЮ" | vanilla grey + dark plaque header with rivets | different sizes (3x4, 3x5, 3x1, 1x1); each tile has its own **material texture** (grass with coins, wooden boards, stone) | mixed-case text on a dark **plaque**, 2 lines | inner framed picture; social 1x1 icons; player inventory kept |
| "Select Language" | vanilla grey | two big framed paintings (Kremlin, Statue of Liberty) | text + small flag under the picture | lots of breathing room - few, large choices |
| profile strip | vanilla grey | big player face, rank badges (coloured plates), equipment slots | short caps badges | **real items** (armour, head) live in normal slots next to the art |

| castle "Квесты" board | no window frame: the whole upper part is a scene (stone wall wider than the window, pillars with braziers, red banners, rubble with plants) | a gold-framed row of 5 dark slot wells holding real quest-card items (! new, check done, empty), a gold divider, a gold-framed 3-slot page navigation | red cloth ribbon with V-cut tails across the top, white outlined text | gold winged ornament under the title, pinned parchment notes, vanilla player inventory below |

| royal slate chest (6 rows) | dark slate body, thin gold line, gold L brackets on every corner, a dark title tab with brackets | all 54 slots as rimmed wells (light rim, recessed dark well) | none - pure storage skin | red crest banners on rods with ball ends, thin gold rails with gems, golden crystal fans + red streamers at the gem divider, key ornaments by the tab, hotbar framed in red/gold |
| slab title font | - | - | 2px-stroke letters, light upper block over a mid lower block, sheen lines, dark base, near-black outline, cut corners; steel/gold/wood variants and an outline-less engraved variant | - |

Takeaways baked into the builder:
- vary tile sizes: one hero tile (3x4 / 3x5), mid tiles (3x3, 3x2), strips (3x1) for secondary actions, 1x1 icons for socials/close
- give tiles material (`style: pattern`) or a scene (`style: image`) - flat colour only for small utility buttons
- labels on plaques/bars read better over busy art than bare text
- a dark recessed `panel` under all tiles produces the thin separator lines seen in every example
- the header deserves size: `header.size: 2` puts a double-size title on a tab above the window
- keep slots that hold real items (`slots_visible`) drawn as slots so players see where items go
- **scene menus**: the art can be a place, not a window - `container_panel: false` + `canvas` margins + scene
  layers (wall/planks, pillars/posts, braziers/lanterns, banners, rubble/hedge/hay, notes) and functional parts as
  framed `slot_bar`s with real items inside. Quests, rewards and page lists change at runtime, so their items are
  real Nexo items (`nexo_items`), not paint; only the static frame is painted
- build a scene back to front: wall -> pillars -> fire -> banners -> ornaments/notes -> frames -> back piles
  (side mounds behind the banner tips) -> inventory panel -> **foreground piles** (`above`) over the panel's top
  corners and beside it, so stones/hay/bushes come forward and the window looks embedded in the place
- **age and wear** make it look hand-made and lived-in: parchment is yellowed with a darker rim, stains, faded ink
  and nibbled, slightly torn edges; banners have soft sagging folds, a dirtier lower part, gaps in the trim and one
  or two small tears. "Slightly" is the point - a few pixels, never holes that break the silhouette
- the middle of the scene stays calm (wall down to the panel) - clutter goes to the sides
- **royal kit**: one accent metal (gold) used only for lines, brackets and ornaments, one accent colour (red cloth)
  and one gem colour (green); everything else dark slate. Ornaments live outside the window and at the seams
  (corners, title tab, divider) - never over slots
- **titles in material letters** (steel on slate, gold on red, wood on a farm sign) read as part of the art;
  flat pixel text is for labels and tooltips

## Polish checklist (what separates "drawn" from "generated")

The builder applies these automatically through `scripts/art.py`; keep them when you hand-draw or extend it.

- **Ramps, not mixes.** Never lighten/darken by mixing with white/black (muddy greys). Shade with ramps:
  ENDESGA 32 ramps for palette colours (wood, stone, grass, sky...), and for any custom colour `art.hue_step`
  (darker = bluer/purpler + more saturated, lighter = yellower). `palette: "endesga32-strict"` snaps everything.
- **Structured textures, never noise.** Planks have boards with a lit top edge, dark seam, grain streaks,
  staggered joints and nails; bricks have mortar and lit/shaded edges; cobble has cells with joints; grass has
  tufts; cloth has folds and a hem. Random per-pixel noise reads as TV static.
- **Every interactive thing is a drawn button:** coloured dark outline with cut corners, lit top/left rim,
  2px darker bottom lip, darker right edge. Optional light inner frame (`frame: "#ffffff"`).
- **Labels:** white with a coloured dark outline and 2px letter spacing when it fits (1px otherwise); plates
  (`plaque`, `wood`, `stone`) for busy art. Outlined labels may overlap the bottom of the icon - icons get bigger.
- **Depth:** plates, rivets and headers cast a 1px shadow; recessed panels are carved (dark top/left, lit
  bottom/right); windows have a textured frame band around a calm, flat body so content stays readable.
- **Volume from parts that stick out.** Let hardware leave the window: hinges, locking bolts, signs and
  nameplates on the top edge, eave beams, hanging signs, feet, and a 3-4 px dark side + bottom face (the window
  as a box, light from the top-left). Users read it as depth - a flat rectangle looks like a sticker. Each part
  must be attached: it starts inside or behind the frame (a slot, a leaf plate, a post, a rafter under the
  awning), casts a shadow, and is drawn before whatever overlaps it. Floating or glued-on parts, or a straight
  gap where two timbers should meet, read as broken (`scripts/safe.py` body/hinge/bolts, `scripts/shop.py` eave).
- **Calm body, loud buttons.** Window body and slots low-contrast and light (parchment/vanilla grey); colour
  and texture go into the buttons and the scene.
- **Soft effects.** Sunburst rays and "gradients" are half a ramp step, banded - not a jump to a new hue.

## Pixel-art asset rules (from item/icon sheets, UI kits and Minecraft-style packs)

These are what `pixelstyle.stylize` and the builder apply; follow them for anything drawn by hand too.

1. **One grid per set.** Items 16x16 (big ones 32x32), menu icons 16-24px, all on whole pixels, no
   semi-transparent edge pixels. Tools/weapons lie diagonally, handle bottom-left (Minecraft convention).
2. **Few colours, shared palette.** 4-6 colours per object, a set drawn from one ~16-24 colour palette so
   everything matches. Pass `palette` to stylize a whole menu with one palette.
3. **Coloured outline.** 1px outline in a darker, slightly cooler shade of the colour it touches - not black.
   Black outlines are a valid style (UI kits, chunky Redstone-Labs icons) but pick one per set.
4. **Hue-shifted ramps.** Each colour has 3-4 steps: highlight (lighter + warmer), base, shadow (darker +
   cooler/purple), outline. Light comes from the top-left; the bottom/right edge gets the shadow.
5. **Silhouette first.** At 16px an item is recognised by its outline shape and 1-2 main colours. Simplify
   prompts ("a red gift box with a gold ribbon") rather than adding detail that turns to noise.
6. **States.** Rare/special = 4-point sparkles; locked/coming soon = single-colour line-art of the same icon
   (orange or grey) on a desaturated tile; pressed/selected = brighter rim.
7. **Pseudo-3D.** Extruding the sprite 1-3px down-right in a dark side colour gives the chunky "block" look of
   popular icon packs and logo lettering (`icon_style.extrude`, `header.depth`).
8. **UI pieces are kits.** Plates, signs and frames are built from the same recipe: black outline with cut
   corners, light top row, 2px darker bottom, nails/rivets at the ends, wood grain or stone chips inside
   (`label_style: wood|stone`, header plaques). Framed "paintings" with a wooden frame work well for big choices.
9. **Decor sparingly.** Clouds, moons, stars and sparkles around a header or on a sky-coloured tile add life;
   keep them away from labels and clickable centres.

Style references collected from the user (third-party art, use for style only, never copy into a pack):
pixel item/food/harvest sheets, Minecraft-style mob drops, bird and animal sprites, cloud/moon/sparkle sets,
wooden/stone UI plates, Redstone-Labs Social/PvP/Weather icon packs, House-Management GUI with framed pictures.

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
