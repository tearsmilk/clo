# jobs_pack - menus on top of a bought "Jobs" GUI pack

The pack's PNGs are NOT included (they belong to the pack author / the buyer). Put them here:

    pack/<job>.png          10 GUI textures, 256x256, window at (40, 33), 5-row chest
    pack/icons/<job>.png    16x16 job icons
    pack/left_click.png     16x16 mouse icons (tooltip hints)
    pack/right_click.png

then `python3 scripts/gui_builder.py assets/examples/jobs_pack/spec.json out/` builds 10 menus (one per
variant) with Russian labels patched over the English ones, icon items, hint glyphs and DeluxeMenus files;
everything merged in `out/_all/`. See references/bought-packs.md.
