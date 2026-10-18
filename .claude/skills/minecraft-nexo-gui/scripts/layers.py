#!/usr/bin/env python3
"""Split a drawing into parts: every part a layer you can export, move and build the picture from again.

A recorder watches the canvas while kits draw: `mark(name)` after each part stores the pixels that part
changed (its own pixels plus the shadow it cast) as a tight sprite with its offset. Nothing happens when no
recorder is active, so kits can call mark() freely.

    rec = layers.start(img)          # gui_builder --layers does this
    ... draw ... layers.mark('blessed/sword') ...
    layers.stop()
    layers.save_parts(rec.items, 'out/layers')            # NN_name.png + layers.json (x, y, order)
    layers.write_aseprite('out/menu.aseprite', rec.items, img.size)   # one layer per part, no Aseprite needed
    layers.compose(json.load(open('out/layers/layers.json')), 'out/layers')   # the picture again from parts

The .aseprite writer follows the published file format (header, one frame, a layer chunk + a zlib cel
chunk per layer, RGBA); `read_aseprite()` reads such files back for checks.
"""
import json
import os
import struct
import zlib

from PIL import Image, ImageChops

_REC = None


class Recorder:
    def __init__(self, img):
        self.img = img
        self.prev = img.copy()
        self.items = []                                  # dicts: name, sprite, x, y

    def mark(self, name):
        diff = ImageChops.difference(self.img, self.prev).getbbox(alpha_only=False)   # colour changes count too
        if diff:
            x0, y0, x1, y1 = diff
            cur = self.img.crop(diff)
            old = self.prev.crop(diff)
            sprite = Image.new('RGBA', cur.size, (0, 0, 0, 0))
            cp, op, sp = cur.load(), old.load(), sprite.load()
            for y in range(cur.height):
                for x in range(cur.width):
                    if cp[x, y] != op[x, y]:
                        sp[x, y] = cp[x, y]
            bb = sprite.getbbox()
            if bb:
                self.items.append({'name': name, 'sprite': sprite.crop(bb), 'x': x0 + bb[0], 'y': y0 + bb[1]})
        self.prev = self.img.copy()


def start(img):
    global _REC
    _REC = Recorder(img)
    return _REC


def stop():
    global _REC
    rec, _REC = _REC, None
    return rec


def active():
    return _REC is not None


def mark(name):
    if _REC is not None:
        _REC.mark(name)


def _safe(name):
    return ''.join(ch if ch.isalnum() or ch in '-_' else '_' for ch in name)


def save_parts(items, out_dir, size=None):
    """Each part as NN_name.png (tight crop) + layers.json with its position and order; and a contact sheet
    (parts at x4 with their names) as _sheet.png."""
    os.makedirs(out_dir, exist_ok=True)
    meta = {'size': list(size) if size else None, 'layers': []}
    for i, it in enumerate(items):
        fn = f'{i:02d}_{_safe(it["name"])}.png'
        it['sprite'].save(os.path.join(out_dir, fn))
        meta['layers'].append({'name': it['name'], 'file': fn, 'x': it['x'], 'y': it['y']})
    with open(os.path.join(out_dir, 'layers.json'), 'w') as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    sheet(items).save(os.path.join(out_dir, '_sheet.png'))
    return meta


def compose(meta, parts_dir, size=None):
    """Build the picture from parts: layers.json order, positions, the PNGs next to it."""
    W, H = size or meta['size']
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for L in meta['layers']:
        if L.get('hidden'):
            continue
        sp = Image.open(os.path.join(parts_dir, L['file'])).convert('RGBA')
        img.alpha_composite(sp, (L['x'], L['y']))
    return img


def sheet(items, k=4, cols=6):
    """Contact sheet: every part enlarged k times on a checker, with its name."""
    from pixfont import draw_text, text_width
    cells = []
    for it in items:
        sp = it['sprite']
        big = sp.resize((sp.width * k, sp.height * k), Image.NEAREST)
        label = it['name'].split('/')[-1][:18]
        w = max(big.width, text_width(label) + 2) + 8
        h = big.height + 16
        cell = Image.new('RGBA', (w, h), (36, 38, 48, 255))
        for y in range(0, big.height, 8):
            for x in range(0, big.width, 8):
                if (x // 8 + y // 8) % 2:
                    for yy in range(y, min(y + 8, big.height)):
                        for xx in range(x, min(x + 8, big.width)):
                            cell.putpixel((xx + 4, yy + 4), (46, 48, 60, 255))
        cell.alpha_composite(big, (4, 4))
        draw_text(cell, 4, big.height + 6, label, (226, 222, 210, 255))
        cells.append(cell)
    rows = [cells[i:i + cols] for i in range(0, len(cells), cols)]
    W = max(sum(c.width + 4 for c in r) for r in rows) + 4
    H = sum(max(c.height for c in r) + 4 for r in rows) + 4
    out = Image.new('RGBA', (W, H), (24, 26, 34, 255))
    y = 4
    for r in rows:
        x = 4
        for c in r:
            out.paste(c, (x, y))
            x += c.width + 4
        y += max(c.height for c in r) + 4
    return out


# ------------------------------------------------------------------ .aseprite (format: aseprite/docs/ase-file-specs.md)
def _string(s):
    b = s.encode('utf-8')
    return struct.pack('<H', len(b)) + b


def _chunk(ctype, data):
    return struct.pack('<IH', len(data) + 6, ctype) + data


def write_aseprite(path, items, size, background=None):
    """RGBA .aseprite with one layer per part (bottom -> top), each a compressed cel at the part's offset.
    background (an Image) becomes the first layer 'background' if given."""
    W, H = size
    layers = ([{'name': 'background', 'sprite': background, 'x': 0, 'y': 0}] if background else []) + list(items)
    chunks = []
    for L in layers:                                     # layer chunks first, in order
        data = struct.pack('<HHHHHHB3s', 3, 0, 0, 0, 0, 0, 255, b'\0\0\0') + _string(L['name'])
        chunks.append(_chunk(0x2004, data))
    for i, L in enumerate(layers):                       # one compressed cel per layer
        sp = L['sprite'].convert('RGBA')
        raw = zlib.compress(sp.tobytes())
        data = struct.pack('<HhhBHh5s', i, L['x'], L['y'], 255, 2, 0, b'\0' * 5) + struct.pack('<HH', *sp.size) + raw
        chunks.append(_chunk(0x2005, data))
    body = b''.join(chunks)
    frame = struct.pack('<IHHH2sI', 16 + len(body), 0xF1FA, min(len(chunks), 0xFFFF), 100, b'\0\0',
                        len(chunks)) + body
    header = struct.pack('<IHHHHHIHII', 128 + len(frame), 0xA5E0, 1, W, H, 32, 1, 100, 0, 0)
    header += struct.pack('<B3sHBBhhHH', 0, b'\0\0\0', 0, 1, 1, 0, 0, 16, 16)
    header += b'\0' * (128 - len(header))
    with open(path, 'wb') as f:
        f.write(header + frame)
    return path


def read_aseprite(path):
    """Read back what write_aseprite writes: (size, [(layer name, x, y, Image)])."""
    b = open(path, 'rb').read()
    fsize, magic, frames, W, H, depth = struct.unpack_from('<IHHHHH', b, 0)
    assert magic == 0xA5E0 and fsize == len(b) and depth == 32, 'not an RGBA .aseprite'
    pos = 128
    flen, fmagic, _, _, _, nchunks = struct.unpack_from('<IHHH2sI', b, pos)
    assert fmagic == 0xF1FA
    pos += 16
    names, cels = [], []
    for _ in range(nchunks):
        size, ctype = struct.unpack_from('<IH', b, pos)
        data = b[pos + 6:pos + size]
        if ctype == 0x2004:
            n = struct.unpack_from('<H', data, 16)[0]
            names.append(data[18:18 + n].decode('utf-8'))
        elif ctype == 0x2005:
            li, x, y, _, ctyp = struct.unpack_from('<HhhBH', data, 0)
            w, h = struct.unpack_from('<HH', data, 16)
            im = Image.frombytes('RGBA', (w, h), zlib.decompress(data[20:]))
            cels.append((li, x, y, im))
        pos += size
    return (W, H), [(names[li], x, y, im) for li, x, y, im in cels]
