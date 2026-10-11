#!/usr/bin/env python3
"""Hand-off kit for a pixel artist who draws the pictures of a menu (job cards, shop banners, quest scenes).

    python3 artist_kit.py OUT W H [--safe X Y W H]... [--covered X Y]... [--frame BG.png X Y]
                          [--palette IMG X Y W H]... [--name card]

Writes into OUT:
    <name>_template.png       W x H, transparent with the covered pixels marked (paint on a copy of it)
    <name>_guide_x4.png       4x enlarged guide: safe zones in red, centre lines, size label
    <name>_mockup.png         (with --frame) the guide placed into the real menu art at X,Y, 3x
    palette.png / .txt / .gpl (with --palette) the colours used in those areas of the reference art, by frequency;
                              palette.gpl loads straight into Aseprite (Palette > Load), GIMP and Krita
The text brief goes next to it (see references/artist-brief.md for the template).
"""
import argparse
import os
from collections import Counter
from PIL import Image, ImageDraw

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pixfont import draw_text  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('w', type=int)
    ap.add_argument('h', type=int)
    ap.add_argument('--safe', type=int, nargs=4, action='append', default=[], metavar=('X', 'Y', 'W', 'H'),
                    help='area covered by a label/plate - keep important things out')
    ap.add_argument('--covered', type=int, nargs=2, action='append', default=[], metavar=('X', 'Y'),
                    help='single pixel hidden by the frame (rounded corners)')
    ap.add_argument('--frame', nargs=3, metavar=('BG', 'X', 'Y'))
    ap.add_argument('--palette', nargs=5, action='append', default=[], metavar=('IMG', 'X', 'Y', 'W', 'H'))
    ap.add_argument('--name', default='card')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    W, H = a.w, a.h

    tpl = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for (x, y) in a.covered:
        tpl.putpixel((x, y), (255, 0, 255, 255))
    tpl.save(os.path.join(a.out, f'{a.name}_template.png'))

    k = 4
    g = Image.new('RGBA', (W * k, H * k), (0, 0, 0, 0))
    gp = g.load()
    for y in range(H * k):
        for x in range(W * k):
            gp[x, y] = (205, 205, 205, 255) if ((x // (k * 4)) + (y // (k * 4))) % 2 else (235, 235, 235, 255)
    d = ImageDraw.Draw(g, 'RGBA')
    for (x, y, w, h) in a.safe:
        d.rectangle((x * k, y * k, (x + w) * k - 1, (y + h) * k - 1), fill=(230, 40, 40, 110), outline=(200, 0, 0, 255))
        draw_text(g, x * k + 4, y * k + 4, f'закрыто {w}x{h}', (120, 0, 0, 255), scale=2)
    for (x, y) in a.covered:
        d.rectangle((x * k, y * k, x * k + k - 1, y * k + k - 1), fill=(255, 0, 255, 255))
    d.line((W * k // 2, 0, W * k // 2, H * k), fill=(60, 120, 220, 160))
    d.line((0, H * k // 2, W * k, H * k // 2), fill=(60, 120, 220, 160))
    d.rectangle((0, 0, W * k - 1, H * k - 1), outline=(40, 40, 40, 255))
    draw_text(g, 6, 6, f'{W} x {H} px', (40, 40, 40, 255), scale=2)
    g.save(os.path.join(a.out, f'{a.name}_guide_x4.png'))

    if a.frame:
        bg = Image.open(a.frame[0]).convert('RGBA')
        fx, fy = int(a.frame[1]), int(a.frame[2])
        small = g.resize((W, H), Image.NEAREST)
        m = bg.copy()
        m.alpha_composite(small, (fx, fy))
        canvas = Image.new('RGBA', m.size, (32, 26, 38, 255))
        canvas.alpha_composite(m)
        canvas.resize((m.width * 3, m.height * 3), Image.NEAREST).save(os.path.join(a.out, f'{a.name}_mockup.png'))

    if a.palette:
        cnt = Counter()
        for (path, x, y, w, h) in a.palette:
            im = Image.open(path).convert('RGBA').crop((int(x), int(y), int(x) + int(w), int(y) + int(h)))
            cnt.update(p[:3] for p in (im.getpixel((x_, y_)) for y_ in range(im.height) for x_ in range(im.width)) if p[3] == 255)
        cols = [c for c, _ in cnt.most_common(48)]
        sw = 24
        pal = Image.new('RGBA', (8 * sw, ((len(cols) + 7) // 8) * sw), (0, 0, 0, 0))
        dd = ImageDraw.Draw(pal)
        for i, c in enumerate(cols):
            dd.rectangle(((i % 8) * sw, (i // 8) * sw, (i % 8) * sw + sw - 1, (i // 8) * sw + sw - 1), fill=c + (255,))
        pal.save(os.path.join(a.out, 'palette.png'))
        open(os.path.join(a.out, 'palette.txt'), 'w').write('\n'.join('#%02x%02x%02x' % c for c in cols) + '\n')
        gpl = ['GIMP Palette', f'Name: {a.name} palette', 'Columns: 8', '#']      # loads in Aseprite / GIMP / Krita
        gpl += ['%3d %3d %3d\t#%02x%02x%02x' % (c + c) for c in cols]
        open(os.path.join(a.out, 'palette.gpl'), 'w').write('\n'.join(gpl) + '\n')
    print('kit written to', a.out)


if __name__ == '__main__':
    main()
