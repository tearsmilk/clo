"""Текстуры полублоков Carpentry из ванильных (client.jar 1.21.11): дёрн (трава тонирована цветом равнин #91BD59),
песок, дубовая и берёзовая кора (oak_wood / birch_wood). Боковая текстура плиты — верхняя половина блока, продублированная в обе половины
(block/slab берёт uv 8..16, block/slab_top — 0..8), так у плиты виден верх блока, а низ срезан.
Запуск: python3 make_slab_textures.py <папка с grass_block_side.png, grass_block_side_overlay.png, grass_block_top.png, dirt.png, sand.png, oak_log.png, birch_log.png> OUT_DIR"""
import sys, os
from PIL import Image
V, OUT = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
def load(n): return Image.open(os.path.join(V, n + '.png')).convert('RGBA')
def tint(img, rgb):
    out = img.copy(); px = img.load(); po = out.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = px[x, y]; po[x, y] = (r * rgb[0] // 255, g * rgb[1] // 255, b * rgb[2] // 255, a)
    return out
def halfside(img):
    h = img.crop((0, 0, 16, 8)); out = Image.new('RGBA', (16, 16)); out.paste(h, (0, 0)); out.paste(h, (0, 8)); return out
GREEN = (0x7F, 0xD6, 0x45)   # ярче равнин: у плит нет биомной окраски, берём сочный зелёный
side = load('grass_block_side'); side.alpha_composite(tint(load('grass_block_side_overlay'), GREEN))
tint(load('grass_block_top'), GREEN).save(f'{OUT}/slab_grass_top.png'); halfside(side).save(f'{OUT}/slab_grass_side.png'); load('dirt').save(f'{OUT}/slab_grass_bottom.png')
sand = load('sand'); sand.save(f'{OUT}/slab_sand.png'); halfside(sand).save(f'{OUT}/slab_sand_side.png')
for w in ('oak', 'birch'):   # «дерево» = блок *_wood: кора со всех сторон
    bark = load(w + '_log'); bark.save(f'{OUT}/slab_{w}_wood.png'); halfside(bark).save(f'{OUT}/slab_{w}_wood_side.png')
print('ok')
