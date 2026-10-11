# Shop GUI set: screens, layout and logic

Measured on a 5-screen market-stall shop pack (main, item list, sell, buy stacks, confirm + 16px back/next
plaques, a warning icon, mouse hints). Our kit `scripts/shop.py` draws the same structure with its own art;
`assets/examples/shop_market/` has all five specs (farm shop, Russian labels).

## Screens a shop needs
| screen | what it shows | clickable slots (6-row chest) |
|--------|---------------|-------------------------------|
| main | stall with a shop window left, a cabinet of categories in the middle, a window right | 3 blocks of 3x4 slots: c0-2 / c3-5 / c6-8, rows 1-4 |
| item list | 7x4 grid of products, home plaque on top, back / next items | wells c1-7 r1-4, home c4 r0, prev c1 r0, next c7 r0 |
| sell | 7x4 grid of wells for the player's goods | wells c1-7 r1-4 |
| buy stacks | banner, 7 wells in a green frame (1..7 stacks), red cancel | wells c1-7 r2, cancel c3-5 r4 |
| confirm | banner, min -10 -1 / item / +1 +10 max, NO / YES, a counter plate | red group c0-2 r2, item c4 r2, green group c6-8 r2, NO c2-3 r4, YES c5-6 r4, counter c4 r5 |

Every clickable thing covers whole slots; nothing important sits between slots.

## Measured geometry (texture 256x256, window at (40, 35) in the pack; we use top 34 so 222 px fit)
- art outside the window: x -29..205, y -30..106 -> spec `canvas: {"left": 40, "right": 40, "top": 34}`
- awning: roof y -15..5 (x 2..173 at the top, -10..186 at the bottom), valance y 6..14, 7 stripes of 28 px with one
  rounded scallop each, light line on the valance top, dark outline under the scallops
- sign 70x11 at x 53..122, y -23..-13 (green, gold frame); vine mounds left and right of it on the awning
- eave brackets x -29..-1 and 176..205 under the awning corners; the left one carries a 14 px wide vertical
  sign on ropes (x -19..-6, y 42..105, 7 letters)
- wall x 3..172 (the vanilla panel border stays visible), planks 18 px wide with seams at x = 7 + 18c - one
  plank per slot column, so the grid and the wall agree
- planks end at staggered heights y 119..125; the client writes "Inventory" at y 128 - keep it clear
- the vanilla player inventory is part of the texture (grey panel, slots) - our builder draws it with
  `theme: "vanilla"`

## Visual rules worth reusing in any themed menu
- One shared "building" (stall, wall, awning, signs) on every screen; only the middle changes. Players
  recognise the set and the screens feel like rooms of one place.
- Colour = meaning: red for cancel / minus / no, green for buy / plus / yes, wood for navigation; the
  screen's question goes on a parchment banner above the controls.
- Buttons: 1 px dark outline, 1 px light top line, lighter sides, 2 px darker lip at the bottom, then a 2 px
  drop shadow on the wall; letters two-tone (light, last row darker), bold 2 px stems.
- Wells: light top/side rim, 2 px inner shadow at the top, dark interior, a mid line at the bottom.
- Decoration lives outside the clickable area: vines, signs and brackets stick out of the window, the middle
  stays calm so items read.
- Glass: blue base, a darker left/top edge, two light diagonal streaks; shelves are 3 px boards with a shadow.
- Navigation plaques (back / next / home) are 16x16 item textures, not baked into the background, so they can
  disappear on the first / last page (`view_requirement`).

## Build
```bash
for s in main items sell stacks confirm; do
  python3 scripts/gui_builder.py assets/examples/shop_market/$s.json out/shop_$s
done
```
Change texts in the specs (`sign`, `hanging`, `poster`, banner and button `text`), products in `extra_items`
(`preview` = icon used in the preview; real menus use `material` - vanilla or `nexo-<id>`).
Product icons: `scripts/item_icons.py` (`item:jar:honey` ...), see `references/item-icons.md`.

## DeluxeMenus logic
**Amount counter (confirm screen)** - DeluxeMenus meta data (1.13.4+; check `/dm` version), PlaceholderAPI
with the Math expansion (`/papi ecloud download Math`) and Vault for money:
```yaml
# on the product in the item list: start at 1 and open the confirm menu
left_click_commands: ['[meta] set amount INTEGER 1', '[openguimenu] hokaria_shop_confirm']
# +10 button (invisible item over the painted plus); the requirement keeps the amount <= 64
left_click_commands: ['[meta] add amount INTEGER 10', '[refresh]']
left_click_requirement:
  requirements:
    range: {type: '<=', input: '%deluxemenus_meta_amount_INTEGER_1%', output: 54}
# the outer buttons jump to the limits: '[meta] set amount INTEGER 1' / '[meta] set amount INTEGER 64'
# the product in the middle and the counter plate show the live amount
dynamic_amount: '%deluxemenus_meta_amount_INTEGER_1%'
# YES: check and take the money, give the goods
left_click_requirement:
  requirements:
    money: {type: has money, amount: '%math_0_{deluxemenus_meta_amount_INTEGER_1}*5%'}
  deny_commands: ['[message] &cНе хватает монет']
left_click_commands:
  - '[takemoney] %math_0_{deluxemenus_meta_amount_INTEGER_1}*5%'
  - '[console] give %player_name% bread %deluxemenus_meta_amount_INTEGER_1%'
```
The counter plate trick: an invisible item (`item_model: nexo:empty`) with `dynamic_amount` sits on the plate -
the client draws its stack count, so the number on the plate is live (1..99).
Test the meta and Math syntax on the user's server versions once; both plugins have changed syntax before.

**Sell screen** - a DeluxeMenus menu cannot take items from the player. Either
1. use a shop plugin with a sell GUI (ShopGUIPlus `/sell gui`, EconomyShopGUI `/sellgui`, ...) and set its
   inventory title to the glyph string from our DeluxeMenus file (`<shift:-48><glyph:hokaria_shop_sell>`), or
2. keep DeluxeMenus and make each well a "sell all of X" button (`[player] sell <item>` from an economy plugin,
   or a console command of your sell plugin).

**Pages** - one menu per page (`hokaria_shop_items`, `..._2`), back / next items open the neighbours; hide
"next" on the last page with a `view_requirement` or simply leave it out of that page's spec.

## Before handing over
- Preview each screen: banner text fits, buttons read, nothing covers the "Inventory" label line (y 128).
- Every painted control has an invisible button or an item on exactly its slots (`preview_grid.png`).
- Red/green/wood meaning is consistent across the screens.
- Third-party packs are references: measure them, draw your own (`references/replicate.md`).
