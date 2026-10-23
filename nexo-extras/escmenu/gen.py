"""Esc-меню и настройки в стиле меню квестов: кнопки — балка амбара, фон — стена амбара (те же части,
что в сцене ZenQuests). HD: 2 px текстуры на 1 px интерфейса (nine_slice width/height — логический размер)."""
import sys, os, json
from PIL import Image, ImageDraw, ImageEnhance, ImageChops
SP = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, f'{SP}/../mcfont'); import mcfont
RAW = f'{SP}/../nexogui/parts'
OUT = sys.argv[1]; G = 2
W_ = f'{OUT}/pack/assets/minecraft/textures/gui'; sp = f'{W_}/sprites/widget'
os.makedirs(sp, exist_ok=True)

def mcmeta(path, w, h, b, bv=None):
    border = b if bv is None else {"left": b, "top": bv, "right": b, "bottom": bv}
    json.dump({"gui": {"scaling": {"type": "nine_slice", "width": w, "height": h, "border": border}}}, open(path + '.mcmeta', 'w'))
def hard(im, t=110):
    r, g, b, a = im.split(); im.putalpha(a.point(lambda v: 255 if v > t else 0)); return im
def quant(im, n=48):
    a = im.split()[3]; q = im.convert('RGB').quantize(colors=n, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert('RGBA'); q.putalpha(a); return q

beam = Image.open(f'{RAW}/raw/beam.png').convert('RGBA')
FB = Image.open(f'{SP}/figma/btn_cut.png').convert('RGBA'); FBH = Image.open(f'{SP}/figma/btn_hl_cut.png').convert('RGBA')
wall = Image.open(f'{RAW}/wall_full.png').convert('RGB')

def button(w, h, light=1.0, warm=0, rim=None, dim=False, src=None):
    """Балка, сжатая до кнопки; по контуру — тёмная обводка; rim — светлый кант (наведение)."""
    im = hard((src if src is not None else FB).resize((w, h), Image.LANCZOS))
    if dim:
        im = ImageEnhance.Color(im).enhance(0.25); im = ImageEnhance.Brightness(im).enhance(0.75)
    elif light != 1.0:
        im = ImageEnhance.Brightness(im).enhance(light)
    if warm:
        a = im.split()[3]; t = Image.new('RGBA', im.size, (255, 200, 110, 255)); im = Image.blend(im, t, warm); im.putalpha(a)
    a = im.split()[3]
    # тёмная обводка 1 GUI px снаружи альфы
    from PIL import ImageFilter
    grow = a.filter(ImageFilter.MaxFilter(2 * G + 1))
    outl = Image.new('RGBA', im.size, (46, 26, 18, 255)); outl.putalpha(ImageChops.subtract(grow, a))
    im.alpha_composite(outl)
    if rim:   # кант внутри: кольцо между альфой и её эрозией
        er = a.filter(ImageFilter.MinFilter(2 * G + 1))
        ring = Image.new('RGBA', im.size, rim + (255,)); ring.putalpha(ImageChops.subtract(a, er)); im.alpha_composite(ring)
    return quant(im)

BW, BH = 200 * G, 20 * G
button(BW, BH).save(f'{sp}/button.png')
button(BW, BH, src=FBH).save(f'{sp}/button_highlighted.png')
button(BW, BH, dim=True).save(f'{sp}/button_disabled.png')
for n in ('button', 'button_highlighted', 'button_disabled'): mcmeta(f'{sp}/{n}.png', 200, 20, 20, 4)

# фон: стена амбара (четверть, сведена к бесшовному тайлу 64x64), затемнена
def wall_tile(k, alpha, size=128, seed_box=(0, 0, 512, 512)):
    t = wall.crop(seed_box).resize((size, size), Image.LANCZOS).convert('RGBA')
    # сшивка краёв: сдвиг на полтайла и мягкая маска крестом посередине
    sh = ImageChops.offset(t, size // 2, size // 2)
    m = Image.new('L', (size, size), 0); mp = m.load(); c = size // 2; fw = 14
    for y in range(size):
        for x in range(size):
            dx, dy = abs(x - c), abs(y - c)
            mp[x, y] = int(255 * max(0.0, 1 - min(dx, dy) / fw))
    t = Image.composite(sh, t, m)
    t = ImageEnhance.Brightness(t).enhance(k); t.putalpha(alpha); return quant(t, 40)
wall_tile(0.5, 232).save(f'{W_}/inworld_menu_background.png')
wall_tile(0.3, 240, seed_box=(512, 512, 1024, 1024)).save(f'{W_}/inworld_menu_list_background.png')
wall_tile(0.62, 255).save(f'{W_}/menu_background.png')
wall_tile(0.36, 255, seed_box=(512, 512, 1024, 1024)).save(f'{W_}/menu_list_background.png')
sepim = hard(beam.crop((20, 0, 465, 121)).resize((64, 4), Image.LANCZOS)); sepim.putalpha(255)
for n in ('inworld_header_separator', 'inworld_footer_separator', 'header_separator', 'footer_separator'): quant(sepim).save(f'{W_}/{n}.png')

# слайдер: дорожка — тёмное углубление в стене, ручка — торец балки
def track(k):
    t = wall.crop((0, 0, 1024, 205)).resize((BW, BH), Image.LANCZOS).convert('RGBA')
    t = ImageEnhance.Brightness(t).enhance(k); d = ImageDraw.Draw(t)
    d.rectangle((0, 0, BW - 1, BH - 1), outline=(46, 26, 18, 255), width=G)
    d.rectangle((G, G, BW - 1 - G, 2 * G - 1), fill=(30, 16, 10, 255)); d.rectangle((G, G, 2 * G - 1, BH - 1 - G), fill=(30, 16, 10, 255))
    for cx, cy in ((0, 0), (BW - 1, 0), (0, BH - 1), (BW - 1, BH - 1)):
        d.rectangle((cx - G + 1 if cx else 0, cy - G + 1 if cy else 0, cx if cx else G - 1, cy if cy else G - 1), fill=(0, 0, 0, 0))
    return quant(t)
track(0.5).save(f'{sp}/slider.png'); track(0.62).save(f'{sp}/slider_highlighted.png')
def handle(rim=None):
    src = FBH if rim else FB; k = src.height * 0.55
    im = hard(src.crop((0, 0, int(k), src.height)).resize((8 * G, BH), Image.LANCZOS))
    return quant(im)
def _finish(im, rim):
    from PIL import ImageFilter
    a = im.split()[3]; grow = a.filter(ImageFilter.MaxFilter(2 * G + 1))
    outl = Image.new('RGBA', im.size, (46, 26, 18, 255)); outl.putalpha(ImageChops.subtract(grow, a)); im.alpha_composite(outl)
    if rim:
        er = a.filter(ImageFilter.MinFilter(2 * G + 1)); ring = Image.new('RGBA', im.size, rim + (255,)); ring.putalpha(ImageChops.subtract(a, er)); im.alpha_composite(ring)
    return quant(im)
handle().save(f'{sp}/slider_handle.png'); handle((240, 196, 96)).save(f'{sp}/slider_handle_highlighted.png')
for n in ('slider', 'slider_highlighted'): mcmeta(f'{sp}/{n}.png', 200, 20, 4)
for n in ('slider_handle', 'slider_handle_highlighted'): mcmeta(f'{sp}/{n}.png', 8, 20, 3)

# ── превью (GUI scale 2, окно 427x240 GUI px), подписи шрифтом Minecraft по-русски ──
S = 2; PW, PH = 427 * S, 240 * S
def nine(img, lw, lh, b, lw0, lh0, bv=None):
    bv = b if bv is None else bv
    """Девятислайс как в игре: img логически lw0 x lh0, рисуем lw x lh (в GUI px), углы b."""
    sx = img.width / lw0; out = Image.new('RGBA', (lw * S, lh * S))
    def part(x0, y0, x1, y1, dx, dy, dw, dh):
        out.alpha_composite(img.crop((int(x0 * sx), int(y0 * sx), int(x1 * sx), int(y1 * sx))).resize((dw * S, dh * S), Image.NEAREST), (dx * S, dy * S))
    cw, ch = lw - 2 * b, lh - 2 * bv
    part(0, 0, b, bv, 0, 0, b, bv); part(lw0 - b, 0, lw0, bv, lw - b, 0, b, bv); part(0, lh0 - bv, b, lh0, 0, lh - bv, b, bv); part(lw0 - b, lh0 - bv, lw0, lh0, lw - b, lh - bv, b, bv)
    part(b, 0, b + cw, bv, b, 0, cw, bv); part(b, lh0 - bv, b + cw, lh0, b, lh - bv, cw, bv)
    part(0, bv, b, bv + ch, 0, bv, b, ch); part(lw0 - b, bv, lw0, bv + ch, lw - b, bv, b, ch); part(b, bv, b + cw, bv + ch, b, bv, cw, ch)
    return out
def label(pv, lx, ly, lw, text, color='#ffffff'):
    tw = mcfont.width(text, S); inner = (lw - 4) * S
    t = Image.new('RGBA', (tw + S, 10 * S)); mcfont.draw(t, 0, 0, text, color, scale=S)
    if tw > inner: t = t.crop((0, 0, inner, t.height)); tw = inner
    pv.alpha_composite(t, ((lx + lw // 2) * S - tw // 2, (ly + 6) * S))
def btn(pv, kind, lx, ly, lw, text, color='#ffffff'):
    pv.alpha_composite(nine(Image.open(f'{sp}/{kind}.png'), lw, 20, 20, 200, 20, 4), (lx * S, ly * S)); label(pv, lx, ly, lw, text, color)
def slider(pv, lx, ly, lw, text, frac, hl=False):
    pv.alpha_composite(nine(Image.open(f'{sp}/slider.png'), lw, 20, 4, 200, 20), (lx * S, ly * S))
    hx = lx + int((lw - 8) * frac); pv.alpha_composite(nine(Image.open(f'{sp}/slider_handle{"_highlighted" if hl else ""}.png'), 8, 20, 3, 8, 20), (hx * S, ly * S))
    label(pv, lx, ly, lw, text, '#ffffa0' if hl else '#ffffff')

pv = Image.new('RGBA', (PW, PH)); px = pv.load()
for y in range(PH):
    k = y / PH; c = (int(85 * (1 - k) + 35 * k), int(150 * (1 - k) + 70 * k), int(70 * (1 - k) + 30 * k), 255)
    for x in range(PW): px[x, y] = c
pv.alpha_composite(Image.new('RGBA', (PW, PH), (16, 16, 16, 200)))
mcfont.draw(pv, PW // 2 - mcfont.width('Меню игры', S) // 2, 40 * S, 'Меню игры', scale=S)
cx = 427 // 2 - 102; y0 = 240 // 4 + 8
btn(pv, 'button', cx, y0, 204, 'Вернуться в игру')
btn(pv, 'button', cx, y0 + 24, 98, 'Достижения'); btn(pv, 'button_highlighted', cx + 106, y0 + 24, 98, 'Статистика', '#ffffa0')
btn(pv, 'button_disabled', cx, y0 + 48, 98, 'Оставить отзыв', '#a0a0a0'); btn(pv, 'button', cx + 106, y0 + 48, 98, 'Сообщить об ошибке')
btn(pv, 'button', cx, y0 + 72, 98, 'Настройки...'); btn(pv, 'button', cx + 106, y0 + 72, 98, 'Открыть для сети')
btn(pv, 'button', cx, y0 + 96, 204, 'Выйти в главное меню')
pv.save(f'{OUT}/preview_pause.png')

op = Image.new('RGBA', (PW, PH))
def tilebg(name, y0, y1):
    t = Image.open(f'{W_}/{name}.png').resize((32 * S, 32 * S), Image.NEAREST)
    for y in range(y0 * S, y1 * S, 32 * S):
        for x in range(0, PW, 32 * S): op.alpha_composite(t.crop((0, 0, 32 * S, min(32 * S, y1 * S - y))), (x, y))
tilebg('inworld_menu_background', 0, 240); tilebg('inworld_menu_list_background', 33, 240 - 33)
hs = Image.open(f'{W_}/inworld_header_separator.png').resize((32 * S, 2 * S), Image.NEAREST)
for x in range(0, PW, 32 * S): op.alpha_composite(hs, (x, 33 * S)); op.alpha_composite(hs, (x, (240 - 33) * S))
pv = op
mcfont.draw(pv, PW // 2 - mcfont.width('Настройки', S) // 2, 15 * S, 'Настройки', scale=S)
slider(pv, cx, 50, 98, 'Поле зрения: 90', 0.5); btn(pv, 'button_highlighted', cx + 106, 50, 98, 'Уведомления Realms', '#ffffa0')
btn(pv, 'button', cx, 74, 98, 'Настройка скина...'); btn(pv, 'button', cx + 106, 74, 98, 'Музыка и звуки...')
btn(pv, 'button', cx, 98, 98, 'Настройки графики...'); slider(pv, cx + 106, 98, 98, 'Сложность: Обычная', 0.66, hl=True)
btn(pv, 'button', cx, 240 - 27, 204, 'Готово')
pv.save(f'{OUT}/preview_options.png'); print('ok')
