"""Бейджи 9 px в стиле badge_admin/badge_player: иконка в квадрате + плашка с надписью 3x5, тень +1."""
from PIL import Image, ImageDraw
F = {  # 3x5 (M, N, W — шире)
 'A': ['.#.','#.#','###','#.#','#.#'], 'D': ['##.','#.#','#.#','#.#','##.'], 'M': ['#...#','##.##','#.#.#','#...#','#...#'],
 'I': ['###','.#.','.#.','.#.','###'], 'N': ['#..#','##.#','#.##','#..#','#..#'], 'P': ['##.','#.#','##.','#..','#..'],
 'L': ['#..','#..','#..','#..','###'], 'Y': ['#.#','#.#','.#.','.#.','.#.'], 'E': ['###','#..','##.','#..','###'],
 'R': ['##.','#.#','##.','#.#','#.#'], 'O': ['###','#.#','#.#','#.#','###'], 'V': ['#.#','#.#','#.#','#.#','.#.'],
 '+': ['...','.#.','###','.#.','...'], 'Ф': ['.###.','#.#.#','#.#.#','.###.','..#..'],
}
ICONS = {
 'shield': (['#####','#####','#####','.###.','..#..'], None),
 'play':   (['#....','###..','#####','###..','#....'], None),
 'star':   (['..#..','.###.','#####','.###.','#...#'], None),
 'star+':  (['..#..','.###.','#####','.###.','#.#.#'], None),
 'camera': (['.#.#.','#####','#.#.#','#####','.....'], None),
}
def badge(text, icon, pal, icon_cols, text_col=(255,255,255), icon_box=None):
    out, main, light, dark = pal
    tw = sum(len(F[c][0]) + 1 for c in text) - 1
    W = 10 + 3 + tw + 3; H = 9
    im = Image.new('RGBA', (W, H), (0,0,0,0)); px = im.load()
    for x in range(1, W-1): px[x,0] = out; px[x,8] = out
    for y in range(1, 8): px[0,y] = out; px[W-1,y] = out; px[9,y] = out
    for x in range(1, 9):
        px[x,1] = main
        for y in range(2, 8): px[x,y] = dark
    for x in range(10, W-1):
        px[x,1] = light
        for y in range(2, 7): px[x,y] = main
        px[x,7] = dark
    if icon_box is not None:  # готовая картинка 9x9 (левая часть исходного бейджа)
        im.paste(icon_box, (0,0))
    else:
        rows = ICONS[icon][0]
        for r, row in enumerate(rows):
            for c, ch in enumerate(row):
                if ch == '#': px[2+c, 2+r] = icon_cols[0] if (len(icon_cols)==1 or r < 3) else icon_cols[1]
    x = 13
    for ch in text:
        g = F[ch]
        for r, row in enumerate(g):
            for c, v in enumerate(row):
                if v == '#':
                    px[x+c+1, 2+r+1] = dark if px[x+c+1, 2+r+1] != text_col else text_col
        for r, row in enumerate(g):
            for c, v in enumerate(row):
                if v == '#': px[x+c, 2+r] = text_col
        x += len(g[0]) + 1
    return im
pal = {
 'moder':  ((14,24,62), (58,120,216), (99,158,242), (32,70,158)),
 'media':  ((44,14,62), (176,66,216), (210,110,242), (112,32,158)),
 'vip':    ((62,40,10), (230,170,40), (255,210,80), (160,110,20)),
 'vipplus':((62,30,10), (240,120,40), (255,170,80), (170,70,20)),
}
res = {}
res['badge_moder'] = badge('MODER', 'shield', pal['moder'], [(255,255,255),(150,200,255)])
res['badge_media'] = badge('MEDIA', 'play', pal['media'], [(255,255,255)])
res['badge_vip'] = badge('VIP', 'star', pal['vip'], [(255,246,160)])
res['badge_vipplus'] = badge('VIP+', 'star+', pal['vipplus'], [(255,246,160)])
# Ферма+ укороченный: иконка колоса из старого бейджа + плашка «Ф+» в его же цветах
old = Image.open('premium_badge.png').convert('RGBA')
res['premium_badge'] = badge('Ф+', None, ((42,23,11),(242,169,59),(255,216,74),(217,130,28)), None, text_col=(255,246,220), icon_box=old.crop((0,0,10,9)))
for n, im in res.items(): im.save(f'out_{n}.png')
# превью рядом со старыми
names = ['badge_admin','badge_moder','badge_media','badge_vipplus','badge_vip','badge_player','premium_badge_old','premium_badge']
ims = [Image.open('badge_admin.png'), res['badge_moder'], res['badge_media'], res['badge_vipplus'], res['badge_vip'], Image.open('badge_player.png'), old, res['premium_badge']]
S = 8; pv = Image.new('RGBA', (60*S, len(ims)*(9*S+24)+10), (40,44,60,255)); d = ImageDraw.Draw(pv); y = 6
for n, im in zip(names, ims):
    im = im.convert('RGBA'); pv.alpha_composite(im.resize((im.width*S, im.height*S), Image.NEAREST), (8, y)); d.text((8, y+9*S+3), n + f'  {im.width}x{im.height}', fill=(230,230,230,255)); y += 9*S+24
pv.save('preview_badges.png'); print({n: im.size for n, im in res.items()})
