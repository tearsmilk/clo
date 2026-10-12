"""Hand-made pixel sprites and procedural props for GUI scenes (no image model needed).

    render(name, **opts) -> RGBA Image at 1:1

Grid sprites use one letter per pixel with a palette; '.' is transparent. Procedural props take a size and
colour so they fit any slot layout: crate(w, h), arrow(w, h, color), awning(w, h, colors, stripe), post(w, h).
All follow the pixel-art rules in references/design-guide.md (dark coloured outline, top-left light).
"""
from PIL import Image, ImageDraw
import colorsys


def _rgb(c):
    c = c.lstrip('#')
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), 255)


def _shade(c, dl):
    r, g, b = [v / 255 for v in c[:3]]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    l = min(1, max(0, l + dl))
    return tuple(int(v * 255) for v in colorsys.hls_to_rgb(h, l, s)) + (255,)


GRIDS = {
    'hourglass': ([
        "KKKKKKKKKKKK",
        "KwwwwwwwwwwK",
        "KKKKKKKKKKKK",
        ".KGGGGGGGgK.",
        ".KGSSSSSSgK.",
        "..KGSSSSgK..",
        "...KGSSgK...",
        "....KSsK....",
        "...KGgSgK...",
        "..KGGSSGgK..",
        ".KGSSSSSSgK.",
        "KKKKKKKKKKKK",
        "KwwwwwwwwwwK",
        "KKKKKKKKKKKK",
    ], {'K': '#3A1E0C', 'w': '#C07A3A', 'G': '#E4F2F8', 'g': '#9CC4D8', 'S': '#F2C94C', 's': '#C9962A'}),
    'ledger': ([
        ".KKKKKKKKKKK.",
        "KdrrrrrrrrrrK",
        "KdRRRRRRRRRRK",
        "KdRYYYYYYRRRK",
        "KdRYRRRRYRRRK",
        "KdRYYYYYYRRRK",
        "KdRRRRRRRRYYK",
        "KdRRRRRRRRYyK",
        "KdRRRRRRRRYYK",
        "KdRRRRRRRRRRK",
        "KdRRRRRRRRRRK",
        "KdPPPPPPPPPPK",
        "KdppppppppppK",
        ".KKKKKKKKKKK.",
    ], {'K': '#2A0E0A', 'R': '#B83A2E', 'r': '#D85A46', 'd': '#7E2218', 'P': '#F2E6C8', 'p': '#CDBB94',
        'Y': '#F2C94C', 'y': '#B88A1E'}),
    'sack': ([
        "...Y.Y.Y....",
        "..YyYyYyY...",
        "...KTTTK....",
        "..KbTTTbK...",
        ".KBBBBBBBK..",
        "KBlBBBBBBbK.",
        "KBlBBBBBBBbK",
        "KBBBBBBBBBbK",
        "KBBBBBBBBbbK",
        ".KbBBBBBbbK.",
        "..KKKKKKKK..",
    ], {'K': '#4A2E14', 'B': '#C89A5A', 'b': '#9A6E38', 'l': '#E2BC7E', 'Y': '#F2C94C', 'y': '#C9962A', 'T': '#6E4A22'}),
    'wheat': ([
        "....Y...",
        "...YyY..",
        "..YyY.Y.",
        "...YyYy.",
        "..YyYy..",
        "...YyY..",
        "....g...",
        "...g....",
        "...g....",
        "..g.....",
    ], {'Y': '#F2C94C', 'y': '#C9962A', 'g': '#7FA13A'}),
    'coin': ([
        "..KKKK..",
        ".KYYYyK.",
        "KYYlYYyK",
        "KYlYYYyK",
        "KYYYYYyK",
        "KYYYYyyK",
        ".KyyyyK.",
        "..KKKK..",
    ], {'K': '#6A4210', 'Y': '#F2C94C', 'y': '#C9962A', 'l': '#FFF3B0'}),
    'check': ([
        "........KK",
        ".......KGK",
        "KK....KGK.",
        "KGK..KGK..",
        ".KGKKGK...",
        "..KGGK....",
        "...KK.....",
    ], {'K': '#14330C', 'G': '#7ED957'}),
    'carrot': ([
        "........gg.g",
        ".......gGgG.",
        "......KOKg..",
        ".....KOoOK..",
        "....KOOoK...",
        "...KOOoK....",
        "..KOOoK.....",
        ".KOoOK......",
        "KOOK........",
        "KK..........",
    ], {'K': '#7A2E08', 'O': '#F08A24', 'o': '#C25E10', 'g': '#3E7A22', 'G': '#7ED957'}),
    'pumpkin': ([
        "......gg......",
        "....KKgKKK....",
        "..KKOOoOOoKK..",
        ".KOlOOoOOoOOK.",
        "KOlOOoOOoOOooK",
        "KOOOOoOOoOOooK",
        "KOOOOoOOoOOooK",
        ".KOOOoOOoOooK.",
        "..KKOoOOoOKK..",
        "....KKKKKK....",
    ], {'K': '#6A2A06', 'O': '#E8862A', 'o': '#B85E14', 'l': '#FFC266', 'g': '#4E8A2A'}),
    'emerald': ([
        "...KKKK...",
        "..KlGGgK..",
        ".KlGGGGgK.",
        "KlGGGGGGgK",
        "KGGGGGGggK",
        ".KGGGGggK.",
        "..KGGggK..",
        "...KKKK...",
    ], {'K': '#0E4A22', 'G': '#2FC36A', 'g': '#17853F', 'l': '#BFFFD6'}),
    'fish': ([
        "....KKKKK.....K",
        "..KKBBBBBKK..KK",
        ".KBBbBBBBBBKKBK",
        "KBWBBBBBBBBBBBK",
        "KBBBBBBBBBbbKBK",
        ".KbbbbbbbbbK.KK",
        "..KKKKKKKKK...K",
    ], {'K': '#1E3A52', 'B': '#7AA6C8', 'b': '#4E7A9E', 'W': '#FFFFFF'}),
    # quest cards (real Nexo items in quest slots): new / done / locked
    'quest_new': ([
        ".KKKKKKKKKK.",
        "KPPPPPPPPPPK",
        "KPRRRRRRRRpK",
        "KPRRRYYRRRpK",
        "KPRRRYYRRRpK",
        "KPRRRYYRRRpK",
        "KPRRRYyRRRpK",
        "KPRRRRRRRRpK",
        "KPRRRYYRRRpK",
        "KPRRRyyRRRpK",
        "KPrrrrrrrrpK",
        "KppppppppppK",
        ".KKKKKKKKKK.",
    ], {'K': '#3e2731', 'P': '#ead4aa', 'p': '#c28569', 'R': '#a22633', 'r': '#73203a', 'Y': '#fee761',
        'y': '#feae34'}),
    'quest_done': ([
        ".KKKKKKKKKK.",
        "KPPPPPPPPPPK",
        "KPGGGGGGGGpK",
        "KPGGGGGGWGpK",
        "KPGGGGGWWGpK",
        "KPGWGGWWGGpK",
        "KPGWWWWGGGpK",
        "KPGGWWGGGGpK",
        "KPGGGGGGGGpK",
        "KPGGGGGGGGpK",
        "KPggggggggpK",
        "KppppppppppK",
        ".KKKKKKKKKK.",
    ], {'K': '#193c3e', 'P': '#ead4aa', 'p': '#c28569', 'G': '#3e8948', 'g': '#265c42', 'W': '#ffffff'}),
    'quest_locked': ([
        ".KKKKKKKKKK.",
        "KPPPPPPPPPPK",
        "KPSSSSSSSSpK",
        "KPSSSkkSSSpK",
        "KPSSkSSkSSpK",
        "KPSSkSSkSSpK",
        "KPSYYYYYYSpK",
        "KPSYYkYYySpK",
        "KPSYYkYYySpK",
        "KPSyyyyyySpK",
        "KPsssssssspK",
        "KppppppppppK",
        ".KKKKKKKKKK.",
    ], {'K': '#262b44', 'P': '#c0cbdc', 'p': '#8b9bb4', 'S': '#5a6988', 's': '#3a4466', 'k': '#262b44',
        'Y': '#feae34', 'y': '#f77622'}),
    'arrow_gold': ([
        ".....KK....",
        ".....KlK...",
        "KKKKKKllK..",
        "KllllllYYK.",
        "KYYYYYYYYyK",
        "KyyyyyyYyK.",
        "KKKKKKyyK..",
        ".....KyK...",
        ".....KK....",
    ], {'K': '#3e2731', 'l': '#fee761', 'Y': '#feae34', 'y': '#f77622'}),
    'barrier': ([
        "...KKKKK...",
        ".KKRRRRRKK.",
        ".KRRKKKRRK.",
        "KRRKK..KRRK",
        "KRK.KK..KRK",
        "KRK..KK.KRK",
        "KRK...KKKRK",
        "KRRK...KRRK",
        ".KRRKKKRRK.",
        ".KKRRRRRKK.",
        "...KKKKK...",
    ], {'K': '#5c0a0a', 'R': '#e43b44'}),
    'crest': ([
        "..Y..Y..Y..",
        "..YY.Y.YY..",
        "..YYYYYYY..",
        "..yyyyyyy..",
        ".KKKKKKKKK.",
        ".KYYYYYYYK.",
        ".KYyYYYyYK.",
        ".KYYyYyYYK.",
        ".KYYYyYYYK.",
        ".KYYyYyYYK.",
        "..KYYYYYK..",
        "...KYYYK...",
        "....KyK....",
        ".....K.....",
    ], {'Y': '#ebcc5b', 'y': '#b55a41', 'K': '#33182a'}),
    'page': ([
        "KKKKKKK..",
        "KWWWWWKK.",
        "KWddWWKwK",
        "KWWWWWKKK",
        "KWdddWWWK",
        "KWWWWWWWK",
        "KWddddWWK",
        "KWWWWWWWK",
        "KWdddWWwK",
        "KwwwwwwwK",
        "KKKKKKKKK",
    ], {'K': '#262b44', 'W': '#ffffff', 'w': '#c0cbdc', 'd': '#5a6988'}),
}


def grid(name):
    rows, pal = GRIDS[name]
    w = max(len(r) for r in rows)
    im = Image.new('RGBA', (w, len(rows)), (0, 0, 0, 0))
    px = im.load()
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch in pal:
                px[x, y] = _rgb(pal[ch])
    return im


def crate(w=12, h=10, color='#B07A42'):
    base = _rgb(color)
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    k = _shade(base, -0.42)
    d.rectangle((0, 0, w - 1, h - 1), fill=k)
    d.rectangle((1, 1, w - 2, h - 2), fill=base)
    d.line((1, 1, w - 2, 1), fill=_shade(base, 0.15))
    d.line((1, h // 2, w - 2, h // 2), fill=_shade(base, -0.2))      # plank seam
    d.line((2, h - 2, w - 2, h - 2), fill=_shade(base, -0.15))
    for x in (1, w - 2):                                              # corner posts
        d.line((x, 1, x, h - 2), fill=_shade(base, -0.28))
    return im


def arrow(w=12, h=9, color='#5DAA3A'):
    base = _rgb(color)
    k = _shade(base, -0.45)
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    mid = h // 2
    head = (h + 1) // 2
    pts = [(0, mid - 2), (w - head - 1, mid - 2), (w - head - 1, 0), (w - 1, mid), (w - head - 1, h - 1),
           (w - head - 1, mid + 2), (0, mid + 2)]
    d.polygon(pts, fill=base, outline=k)
    d.line((1, mid - 1, w - head - 2, mid - 1), fill=_shade(base, 0.18))
    return im


def awning(w, h, colors=('#C2453A', '#F2E4C8'), stripe=9, scallop=4):
    """Striped market awning with a top rail and a scalloped lower edge (bottom `scallop` px are the wave)."""
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    px = im.load()
    cols = [_rgb(c) for c in colors]
    body = h - scallop
    for y in range(h):
        for x in range(w):
            i = (x // stripe) % len(cols)
            c = cols[i]
            if y < 3:                                                  # wooden rail
                c = _rgb('#6E4A22') if y != 1 else _rgb('#9A6A34')
            elif y >= body:                                            # scallops: half-discs per stripe
                cx = (x // stripe) * stripe + stripe / 2
                r = stripe / 2
                dy = y - body
                if (x - cx + 0.5) ** 2 + (dy + 0.5) ** 2 * 2.2 > r * r:
                    continue
            else:
                if (x % stripe) == 0:
                    c = _shade(c, -0.12)
                if y == 3:
                    c = _shade(c, 0.12)
                if y >= body - 2:
                    c = _shade(c, -0.1)
            px[x, y] = c
    # dark outline around the shape
    src = im.copy().load()
    for y in range(h):
        for x in range(w):
            if src[x, y][3] and any(not (0 <= x + dx < w and 0 <= y + dy < h) or src[x + dx, y + dy][3] == 0
                                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                px[x, y] = _rgb('#2E1608')
    return im


def post(w, h, color='#8A5A2E'):
    base = _rgb(color)
    im = Image.new('RGBA', (w, h), _shade(base, -0.45))
    d = ImageDraw.Draw(im)
    d.rectangle((1, 0, w - 2, h - 1), fill=base)
    d.line((1, 0, 1, h - 1), fill=_shade(base, 0.15))
    d.line((w - 2, 0, w - 2, h - 1), fill=_shade(base, -0.2))
    for y in range(3, h, 9):
        d.point((w // 2, y), fill=_shade(base, -0.25))
    return im


def render(name, **kw):
    if name in GRIDS:
        return grid(name)
    return {'crate': crate, 'arrow': arrow, 'awning': awning, 'post': post}[name](**kw)
