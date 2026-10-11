#!/usr/bin/env python3
"""Make button icons for glyph GUIs: generate with an AI model, cut the background, pixelize.

Subcommands
    gen  OUT.png "prompt" [--model M] [--size 512]     generate one icon (Pollinations, key from $POLLI_KEY)
    cut  IN.png OUT.png [--fill-holes]                 remove background with rembg, crop to content
    pixel IN.png OUT.png --size 24 [--colors 24]       downscale to a pixel icon (hard alpha, limited palette)
    sheet OUT.png IN1.png IN2.png ...                  contact sheet on a mid-blue backdrop to eyeball cut quality

Typical flow per icon:  gen -> cut -> (look at the sheet) -> gui_builder.py fits it into the button.
Generate on a flat background that contrasts with the object (white for dark objects, dark navy for
light/cream objects like parchment) - rembg removes interior regions that match the backdrop colour,
and --fill-holes repaints fully enclosed transparent areas when that happens anyway.
"""
import argparse, os, sys, urllib.parse, urllib.request, random
from collections import deque
from PIL import Image

ICON_PROMPT = ("single Minecraft-style pixel art game UI icon of {subject}, centered, filling most of the frame, "
               "bold dark outline, chunky clearly visible square pixels, slight 3/4 view, vibrant saturated colors, "
               "soft shading, isolated on a plain flat solid {bg} background, no shadow on background, no text, no border")


def gen(out, subject, model, size, bg):
    key = os.environ.get('POLLI_KEY')
    if not key:
        sys.exit('POLLI_KEY is not set - ask the user for a Pollinations key, or use another image tool '
                 '(Figma generate_image, a provided PNG) and continue with `cut`.')
    prompt = ICON_PROMPT.format(subject=subject, bg=bg)
    url = (f"https://gen.pollinations.ai/image/{urllib.parse.quote(prompt)}"
           f"?model={model}&width={size}&height={size}&seed={random.randint(1, 10**9)}")
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {key}', 'User-Agent': 'minecraft-nexo-gui/1.0'})
    try:
        data = urllib.request.urlopen(req, timeout=240).read()
    except urllib.error.HTTPError as e:
        body = e.read()[:300].decode('utf-8', 'replace')
        if e.code == 402:
            sys.exit(f'Pollinations: out of credits ({body}). Tell the user; credits refill daily.')
        sys.exit(f'Pollinations HTTP {e.code}: {body}')
    open(out, 'wb').write(data)
    print(out)


def fill_holes(im, orig):
    """Make transparent pixels that are not connected to the border opaque (rembg ate the inside)."""
    w, h = im.size
    p = im.load()
    seen = bytearray(w * h)
    q = deque([(x, y) for x in range(w) for y in (0, h - 1)] + [(x, y) for y in range(h) for x in (0, w - 1)])
    while q:
        x, y = q.popleft()
        if x < 0 or y < 0 or x >= w or y >= h or seen[y * w + x] or p[x, y][3] > 0:
            continue
        seen[y * w + x] = 1
        q.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    src = orig.convert('RGB').load()  # rembg zeroes RGB under removed pixels, so read the source
    filled = 0
    for y in range(h):
        for x in range(w):
            if p[x, y][3] == 0 and not seen[y * w + x]:
                r, g, b = src[x, y]
                p[x, y] = (r, g, b, 255)
                filled += 1
    return filled


def cut(inp, out, holes):
    from rembg import remove, new_session  # pip install "rembg[cpu]"
    orig = Image.open(inp).convert('RGB')
    im = remove(orig, session=new_session('isnet-general-use'))
    im.putalpha(im.getchannel('A').point(lambda v: 0 if v < 60 else 255))
    if holes:
        print('filled', fill_holes(im, orig), 'enclosed px', file=sys.stderr)
    bb = im.getbbox()
    im = im.crop(bb) if bb else im
    im.save(out)
    print(out, im.size)


def pixel(inp, out, size, colors):
    im = Image.open(inp).convert('RGBA')
    bb = im.getbbox()
    im = im.crop(bb) if bb else im
    k = size / max(im.size)
    im = im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)
    a = im.getchannel('A').point(lambda v: 255 if v > 110 else 0)
    rgb = im.convert('RGB').quantize(colors=colors, method=Image.MEDIANCUT).convert('RGB')
    rgb.putalpha(a)
    rgb.save(out)
    print(out, rgb.size)


def sheet(out, files):
    ims = [Image.open(f).convert('RGBA') for f in files]
    cell = 200
    s = Image.new('RGBA', (cell * len(ims), cell), (60, 90, 160, 255))
    for i, im in enumerate(ims):
        im.thumbnail((cell - 10, cell - 10))
        s.alpha_composite(im, (i * cell + (cell - im.width) // 2, (cell - im.height) // 2))
    s.save(out)
    print(out)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    g = sp.add_parser('gen'); g.add_argument('out'); g.add_argument('subject')
    g.add_argument('--model', default='black-forest-labs/flux.2-klein-4b'); g.add_argument('--size', type=int, default=512)
    g.add_argument('--bg', default='pure white')
    c = sp.add_parser('cut'); c.add_argument('inp'); c.add_argument('out'); c.add_argument('--fill-holes', action='store_true')
    p = sp.add_parser('pixel'); p.add_argument('inp'); p.add_argument('out'); p.add_argument('--size', type=int, default=24)
    p.add_argument('--colors', type=int, default=24)
    sh = sp.add_parser('sheet'); sh.add_argument('out'); sh.add_argument('files', nargs='+')
    a = ap.parse_args()
    if a.cmd == 'gen':
        gen(a.out, a.subject, a.model, a.size, a.bg)
    elif a.cmd == 'cut':
        cut(a.inp, a.out, a.fill_holes)
    elif a.cmd == 'pixel':
        pixel(a.inp, a.out, a.size, a.colors)
    else:
        sheet(a.out, a.files)
