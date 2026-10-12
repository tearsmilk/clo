"""Рендер текста настоящим шрифтом Minecraft (bitmap-провайдеры default.json из клиента)."""
import json, os
from PIL import Image
A = os.path.dirname(os.path.abspath(__file__))
_G = {}
def _load():
    if _G: return
    d = json.load(open(f'{A}/assets/minecraft/font/include/default.json'))
    for p in d['providers']:
        if p['type'] != 'bitmap': continue
        im = Image.open(f"{A}/assets/minecraft/textures/{p['file'].split(':')[1]}").convert('RGBA')
        rows = p['chars']; cols = len(rows[0]); gw = im.width // cols; gh = im.height // len(rows)
        h = p.get('height', 8); asc = p['ascent']; sc = h / gh
        for r, row in enumerate(rows):
            for c, ch in enumerate(row):
                if ch == '\x00' or ch in _G: continue
                g = im.crop((c * gw, r * gh, (c + 1) * gw, (r + 1) * gh))
                a = g.split()[3].getbbox()
                if a is None: _G[ch] = (None, 0, asc, sc); continue
                _G[ch] = (g.crop((0, 0, a[2], gh)), a[2], asc, sc)
    _G[' '] = (None, 4, 7, 1)
def width(text, scale=1):
    _load(); return sum(int((_G.get(ch, _G['?'])[1] * _G.get(ch, _G['?'])[3]) + 1) * scale for ch in text) - scale
def draw(img, x, y, text, color='#ffffff', scale=1, shadow=True):
    """y — верх строки (как в игре, базовая линия ascent=7)."""
    _load()
    rgb = tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))
    def tint(g, col):
        m = g.split()[3]; t = Image.new('RGBA', g.size, col + (0,)); t.putalpha(m); return t
    for ch in text:
        g, w, asc, sc = _G.get(ch, _G['?'])
        if g is not None:
            gi = g.resize((int(g.width * sc * scale), int(g.height * sc * scale)), Image.NEAREST)
            gy = y + (7 - asc) * scale
            if shadow: img.alpha_composite(tint(gi, tuple(c // 4 for c in rgb)), (x + scale, gy + scale))
            img.alpha_composite(tint(gi, rgb), (x, gy))
        x += int(w * sc + 1) * scale
    return x
