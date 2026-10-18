# Menu plugins: wiring buttons to a glyph background

## DeluxeMenus (most common; what gui_builder.py emits)

Docs: https://wiki.helpch.at/helpchat-plugins/deluxemenus

```yaml
menu_title: '<white><shift:-8><glyph:hokaria_main>'
open_command: [menu, hokaria]
size: 54                       # 9 x rows
update_interval: 1             # only if lore uses live placeholders
items:
  'farm':
    material: PAPER
    item_model: nexo:empty     # invisible; 1.21.2+ clients. Older: material nexo-<invisible_item_id>
    slots: [0, 1, 2, 9, 10, 11]  # every slot under the painted button; ranges like '0-2' also work
    display_name: '&e&lФерма'
    lore: ['&7Сажай и собирай урожай', '', '&a» Нажми, чтобы перейти']
    left_click_commands: ['[close]', '[player] warp farm']
    right_click_commands: ['[message] &7Подсказка...']
    click_requirement:          # optional gating
      requirements:
        perm: {type: has permission, permission: hokaria.farm}
      deny_commands: ['[message] &cНет доступа']
```

Useful keys: `material: nexo-<id>` (a real Nexo item as a visible icon), `item_model`, `model_data_component`
(1.21.4+ replacement for `model_data`), `hide_tooltip: true` (no tooltip at all - good for pure decoration),
`tooltip_style` (1.21.2+), `item_flags`, `priority` + `view_requirement` (state-dependent buttons, e.g. a
locked/unlocked variant in the same slots), `update: true` (refresh name/lore).
Actions: `[player]`, `[console]`, `[commandevent]`, `[message]`, `[openguimenu] other_menu`, `[close]`,
`[refresh]`, `[sound] UI_BUTTON_CLICK`, `[takemoney]`/`[givemoney]` (Vault).

Registering: `plugins/DeluxeMenus/config.yml` -> `gui_menus: { hokaria_main: { file: hokaria_main.yml } }`, files live in
`gui_menus/`. Reload with `/dm reload`.

If `<glyph:...>` shows as literal text in the title (older Nexo/Adventure combos), switch the title to PAPI:
`menu_title: '%nexo_shift_-8%%nexo_hokaria_main%'` (needs PlaceholderAPI).

### State changes without new menus
Paint each state into a separate glyph (e.g. `shop_page1`, `shop_page2`) and switch with
`[openguimenu] shop_page2`, or put both buttons in the same slots and select with `view_requirement` + `priority`.
Dynamic numbers (balance, level) are best left as live text: shift back after the glyph and print
`%vault_eco_balance%` in the title, or show it in a tooltip.

## zMenu

Supports Java + Bedrock, has Nexo item support. Title is `name:`; buttons are `items:` with `slot`/`slots`,
`item: {material: PAPER, model-id/item-model}`. Same glyph title and invisible-item idea applies.

## Nexo's own inventory.yml
Only for the `/nexo inventory` item browser (`menu_title: <shift:-37><glyph:menu_items_search>`). Not for server menus.

## Writing a plugin yourself
`Bukkit.createInventory(holder, 54, MiniMessage.miniMessage().deserialize("<shift:-8><glyph:hokaria_main>"))`
on Paper with Nexo installed; Nexo resolves the tags. Fill slots with an ItemStack whose
`setItemModel(NamespacedKey.fromString("nexo:empty"))` and cancel `InventoryClickEvent` for that holder.
