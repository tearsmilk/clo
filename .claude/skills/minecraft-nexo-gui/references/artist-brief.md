# Briefing a pixel artist (pictures the code should not draw)

Characters, detailed scenes and emblems look best hand-drawn. The skill draws frames, layout, labels and
configs; the artist only draws the pictures. Give them an exact kit:

```bash
python3 scripts/artist_kit.py OUT 120 48 --name card --safe 24 37 73 11 --covered 0 0 --covered 119 0 \
    --frame pack/farmer.png 68 53 --palette pack/farmer.png 68 53 120 48 --palette pack/miner.png 68 53 120 48
```
-> `card_template.png` (1:1 canvas), `card_guide_x4.png` (covered zones in red, centre lines),
`card_mockup.png` (where it lands in the menu), `palette.png/.txt/.gpl` (the reference's colours; the .gpl
loads into Aseprite via Palette > Load, also GIMP/Krita).

Brief (write it in the user's language), always with:
- exact size, 1 px = 1 px, PNG, no anti-aliasing / blur / semi-transparent pixels, fully filled background
- what is covered (labels, frame corners) with coordinates - faces and key details stay out
- the palette file and 1-2 reference cards of the set for style
- file names = variant ids, so the spec picks them up (`"picture": "art/${id}.png"`)
- recommend Aseprite (or LibreSprite / Piskel) - real pixel editors with palettes and 1:1 export

When the files arrive: drop them in `art/`, add the variants, build. Art at the exact size is pasted 1:1
(no posterize/resize); anything else is fitted and posterized, which loses detail - ask for the right size.
