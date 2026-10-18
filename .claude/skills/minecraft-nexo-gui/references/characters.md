# Characters: people, mobs and animals built from parts

`scripts/characters.py` draws 37 original blocky Minecraft-like characters at two densities: k=1 (vanilla GUI
density, a humanoid is a mini player about 16x32 + outline) and k=2 ("HD", about 32x64), drawn natively with
more detail, never upscaled. Every character is a list of parts (modes.Parts), so it can be composed, moved,
hidden and exported to PNG layers or a layered .aseprite. Use them in menus (NPC portraits, shop keepers,
quest givers, pet / mob shops), as glyphs, or as walking animated glyphs (4-frame walk sheets).
Everything is original art in a Minecraft-like style. It is not a copy of any Mojang texture or skin. The
player is not the default skin: hoodie, jeans and a different face.

```bash
python3 scripts/characters.py chart OUT.png [--hd]     # all 37 labelled (x4 / HD x3) + walk strips + exploded parts
python3 scripts/characters.py extras OUT.png [--hd]    # poses, facing, every held item, colour variants
python3 scripts/characters.py render knight OUT.png --hd --pose walk --frame 1 --facing left
python3 scripts/characters.py render player OUT.png --held pickaxe --held-mat diamond --skin brown --hair '#c0c0c0'
python3 scripts/characters.py render sheep OUT.png --opt colour=pink        # per-character switches: --opt k=v
python3 scripts/characters.py parts king OUT_DIR --hd  # NN_part.png + layers.json + _sheet.png + .aseprite
python3 scripts/characters.py walk zombie OUT.png      # 4 frames side by side on one shared box
python3 scripts/characters.py list                     # catalog, poses, items, palette, switches
```

## Catalog
| group | names | view | k=1 size (with outline, shadow) |
|-------|-------|------|------------|
| player | `player` | front | 19x35 |
| villagers | `villager_farmer` (straw hat, apron with wheat), `_librarian` (browline glasses, cap), `_blacksmith` (goggles, riveted leather apron), `_butcher` (headband, stained apron), `_cleric` (gold band, amethyst pendant), `_fisherman` (sou'wester, rope belt), `_cartographer` (monocle, feathered cap), `_merchant` (hood with gold trim, emerald) | front | 19x35-41 |
| roles | `knight` (great helm, plume, plate, tabard, shield, sword), `guard` (kettle hat, chainmail, spear), `wizard` (pointed hat, long beard, starry robe, staff), `miner` (hard hat with lamp, overalls, pickaxe), `witch`, `pirate` (tricorn, eyepatch, ginger beard, striped shirt, coat), `king` (crown, ermine, cape, scepter), `princess` (tiara, long hair, gown), `ninja` (mask, headband tails, katana on the back), `archer` (hood, quiver, bow) | front | 19-28 x 35-45 |
| humanoid mobs | `zombie` (arms reaching, torn clothes), `skeleton` (ribcage, bow), `ender_walker` (tall shadow, glowing eyes, particles) | front | 15-19 x 35-49 |
| mobs | `creeper_plant` (leafy explosive plant monster with a glowing seed core), `spider` (8 legs, 8 eyes), `slime` (gel cube with a core) | front | 16-40 wide |
| animals | `cow`, `pig`, `sheep`, `chicken`, `horse`, `cat`, `wolf` (dog with a collar), `fox`, `bee`, `fish`, `axolotl`, `parrot` (on a perch) | side | 15-36 wide |
HD sizes are about twice these (player 37x69, horse 71x70).

## Options
| option | values |
|--------|--------|
| `pose` | `idle`, `wave` (the free hand), `hold` (forearm forward, item in hand), `walk` + `frame` 0-3, `cross` (villagers' default), `reach` (zombie's default). Animals and mobs: `idle`, `walk` |
| `facing` | humanoids `front` / `left` / `right`: the face turns (features shift 1 skin px, a strip of the head's side shows) and the item goes to that hand. Animals `right` (default) / `left` |
| `held` | `sword pickaxe axe hoe rod book torch bow staff spear scepter potion map hammer cleaver bag` or `None`; each look has a default (villagers only hold theirs when not crossing their arms) |
| `held_mat` | `iron gold diamond wood stone` for blades and tool heads |
| colours | `skin= hair= top= bottom= shoes= eye=`: a `PALETTE` name (`tan`, `dark`, `blonde`, `ginger`, `teal`, `navy`, `cloth_black`, `iris_blue` ...) or `'#hex'` (built with `shading.ramp5`) |
| switches | knight `shield=False plume=False`, king `cape=False`, wolf `collar=False`, parrot `perch=False`, `colour=` for sheep, horse, cat, axolotl, slime; `shadow=False` for all |

Python: `render(name, k, **opts)` -> tight RGBA; `parts(name, k, **opts)` -> `[{name, sprite, x, y}]` in the
figure's box (`modes.compose`, `modes.override`, `layers.save_parts`, `layers.write_aseprite`);
`walk_frames(name, k)` / `walk_sheet(name, k)`; `exploded(name, k)` (the exploded-parts diagram).

## How it is built
- **Pixels are (ramp, tone).** Each part is a `Layer` holding pixel -> (6-colour ramp from `shading.ramp5`, tone
  0 outline .. 5 highlight). Painters write tones, never raw colours, so a colour variant is a ramp swap and the
  outline can take the tone of whatever material it wraps.
- **Part order** (humanoids): shadow, back (cape, hair, quiver, katana), legs, feet, torso, robe, belt, chest
  (apron, tabard, coat), arms, crossed arms, collar, item, hands, shield, head, face, beard, hair, hat, acc
  (glasses, eyepatch, pendant), fx (sparks, particles). The item is drawn before the hand, so the fist wraps
  the handle. Animals: shadow, tail, far legs, body, spots, belly, near legs, neck, mane, head, snout, ears,
  face, horns, gills, collar, wing, perch, feet, fx.
- **Outline last.** The ring round the union of all parts gets tone 0 of the material it touches, tone 1 on
  the lit top / left side (selective outline). L-corner doubles in it are removed (pixel-perfect). Each
  outline pixel goes to the topmost part it wraps, so `layers.compose(parts) == render()` exactly.
  Parts that sit in front of the body (held items, shields, crossed arms, animal heads) also get their own ring,
  built from their own pixels, so a grey sword separates from a grey breastplate. Strings, whiskers, spider legs
  at k=1, sparks and the ground shadow are `free` pixels: never outlined.
- Hiding a part with `modes.override` also drops its outline. To remove an accessory cleanly, use its switch
  or `held=None`, which renders the figure again with a closed outline.

## What makes them read (the rules the painters follow)
- **Proportions in skin units** (x k): head 8x8, torso 8x12, arms 4x12 (`slim` 3, `skinny` 2), legs 4x12;
  villager head 8x10, legs 10; `tall` limbs 2x26. Minecraft-like boxes. Volume comes from tones, not perspective.
- **One light, top-left, on boxes.** A flat face is one base tone. The screen-left column is lit, the right
  column darker. Shoulder tops catch the light. The arm's contact shadow sits on the torso's left column, the
  head's shadow round the neck, the shirt's hem shadow across the top of the legs. Inner leg columns meet in
  shadow. Turned-away faces (the right arm's outer side) go a step darker at k=2.
- **Faces.** k=1: eye = white + iris (2x1), brows 2 px, mouth 2 px; nothing else fits. k=2: a dark lid line over
  a 3x2 eye (white outside, 2x2 iris, a white glint on its top-left), the nose as a lit tip with shadow under
  and right of it, 2 px blush, mouth corners. The fringe casts a one-step shadow on the forehead.
  Hat brims cast theirs too, but never over the brows.
- **Villagers.** Tall bald head with a lit crown highlight, a unibrow, deep-set eyes. The nose is a box
  sticking out: lit left column, base, dark right column and underside, nostrils, and its cast shadow on the
  right cheek. The robe flares one step at the bottom with vertical folds (dark mid + a light-mid lip on the
  lit side). The crossed arms are their own outlined block with a lit top face, hands tucked in the middle and
  a cast shadow on the robe under them.
- **Metal is contrasty, cloth is soft.** Plate: a highlight streak inside the lit column, a lit-left / dark-right
  ridge, lames as gap lines with a lit lip under each, pauldrons wider than the arm with a dark row under them.
  Cloth: soft ramps, folds as a dark-mid streak with a light-mid lip, cuffs and hems a step darker.
- **Patterns are deliberate textures built from runs, not dots:** shirt stripes, chainmail (ring tops in 2 px
  runs, a dark gap row), wool (round puffs lit top-left with dark crescents bottom-right), tabby stripes,
  wood grain on shafts. No checker dithering.
- **Items** point up and away from the body; the light stays top-left whichever way they point. Per diagonal
  column: lit edge, core, lower bevel (HD sword: a fuller groove down the middle). Gold guards and pommels,
  wrapped grips, a reel on the rod, a hanging line (free pixels) and a red-white bobber. Upright items (torch,
  staff, spear, scepter, cleaver, potion) are held by their base so they show above the fist.
- **Animals (side view).** Drawn facing right in local coordinates; `facing='left'` mirrors the geometry only,
  and every box is shaded in screen space, so the light never flips. Far legs are one tone darker, behind the
  body. The head has its own outline. The eye glint sits on the screen top-left. Patches (cow spots, socks,
  bellies) are re-shaded by their own mask: lit top edge, dark bottom edge. HD adds split hooves, muscle arcs,
  fur streaks, inner ears, whiskers, teats, mud.
- **No transparency tricks.** The slime's translucency is a lighter outer gel with a darker core inside. The
  ender eyes glow with opaque bright tones. The bee's wings are opaque pale tones with veins.
- **Saturation on the focal parts:** faces, gems, items and emblems carry the strongest colour and contrast;
  robes and fur stay soft.

## Walk cycles (animated glyphs)
Frames 0-3 = contact, pass, contact, pass. Humanoids: on pass frames the body bobs up 1 skin px, one foot
lifts 2, and the arms swing (back arm 1 shorter, forward arm 1 longer). Villagers keep their arms crossed.
Zombies keep reaching. Quadrupeds: legs sheared ±2 px at the foot in diagonal pairs (near-front with
far-back), the passing pair lifted 1. Chickens bob their heads, bees flap, fish swish their tails, slimes squash
and stretch, spiders lift alternate legs. `walk_frames` puts all four frames on one shared box, so they line
up as glyph frames.

## Quality gate
`python3 scripts/shading.py check OUT.png --kit characters` (the kit's module-level ramps count as materials).
State of the catalog, 74 renders: 54 clean. The rest are deliberate, and they are listed here so nobody
"fixes" them:
- **jaggies** at design corners: hat-crown insets, crown points, ear and comb tips, the fist where a handle
  comes out, pauldron edges, the stinger and antenna. The jaggy measure assumes smooth curves.
- **"top edges darker"** on the witch and the pirate: black hats are a darker material than the shoes and the
  grey ground shadow. The fish's back is darker on purpose (countershading), and so are the axolotl's gills
  on its left side. Per part, the shading is lit top-left.
- **8 % single pixels** on the tiny k=1 chicken and fox: eyes, nose, comb and ear tips are 1 px details.
Doubles in outlines are removed automatically. There are no semi-transparent pixels, no checker dithering, and
the value spread is >= 82 everywhere.

## Adding a character
- **Humanoid:** write a look function returning a dict:
  `dict(kind='player'|'slim'|'villager'|'skinny'|'tall', skin=, hair=, eye=, top=, bottom=, shoes=, held=,
  pose=, paint=[painter])`. The painter calls the shared painters in order: `p_shadow`, legs (`p_legs`,
  `p_boots`, `p_plate_legs`, `p_villager_legs`), torso (`p_torso_shirt`, `p_robe`, `p_dress`, `chainmail`,
  `p_plate_torso`), extras (`apron`, `tabard`, `coat`, `belt`, `overalls`, `cape_back`), arms (`p_arms`,
  `p_cross_arms`, `p_plate_arms`, `bell_cuffs`), `p_hands`, head and face (`p_head` + `p_face_player`, or
  `p_villager_head` + `p_villager_face`), `p_hair` / `p_beard`, then a hat (`brim_hat`, `pointy_hat`,
  `kettle_helm`, `great_helm`, `hood`, `tricorn`, `crown`, `hard_hat`, `souwester`, `skullcap`) and accessories.
  Register it in `LOOKS`.
- **New painter:** read boxes from `h.b` (`head`, `torso`, `arm_l/r`, `hand_l/r`, `leg_l/r`, `foot_l/r`), write
  `(ramp, tone)` into a named layer `h.L('hat')`, and branch on `h.k` for the HD detail. Never scale.
  Respect `h.fs` (face shift) and `h.body.arm_mode` (`down`, `hold`, `up`, `cross`, `reach`).
- **Animal / mob:** `a = A(k, W, H, facing, pose, frame, shadow)`. Draw facing right in local coordinates with
  `a.box`, `a.leg`, `a.eye`, `a.fur`, `a.shade_pts`. Name layers from `ORDER_A`, return `a.finish()`, register it
  in `ANIMALS` (side view) or `MOBS` (front view).
- **Colours:** declare new ramps at module level with `_r5('#hex', soft=...)`, so `--kit characters` and the
  `drawing_styles` engine see them. Soft 0.6-0.8 for skin and cloth, 0 for metal, about 0.2 for gems and glows.
- Then run `chart` at both densities, look at it closely, and run `shading.py check --kit characters` on the renders.
