#!/usr/bin/env python3
"""Aseprite (https://github.com/aseprite/aseprite) in batch mode, for the artist workflow and pixel-art chores.

Aseprite is a human pixel editor; here it is used headless (`aseprite -b`, Lua scripts) to:
    template   make a layered .aseprite file for the artist: palette loaded, an `art` layer to paint on, the
               covered zones (real pack pixels or red marks) on a locked layer above, centre guides hidden
    export     export the `art` layer of the artist's .aseprite file to PNG (what the builder pastes 1:1)
    sheet      export all frames as a horizontal sprite sheet + JSON (animated glyphs / item frames)
    palette    convert any PNG to a palette (.gpl / .aseprite palette) without dithering - AI pictures,
               photos or our drafts into the pack's colours
    rotate     rotate pixel art cleanly with RotSprite (angled icons) - no blur, no lost pixels

    python3 aseprite_tools.py template OUT.aseprite W H [--palette pal.gpl] [--cover cover.png] [--name art]
    python3 aseprite_tools.py export IN.aseprite OUT.png [--layer art]
    python3 aseprite_tools.py sheet IN.aseprite OUT.png
    python3 aseprite_tools.py palette IN.png PAL.gpl OUT.png
    python3 aseprite_tools.py rotate IN.png DEGREES OUT.png

The binary is found via $ASEPRITE or `aseprite` on PATH. Aseprite's EULA allows compiling it for your own
use but not redistributing it: build it locally with scripts/build_aseprite.sh, never ship the binary.
"""
import os
import shutil
import subprocess
import sys
import tempfile

LUA_TEMPLATE = r'''
local W, H = tonumber(app.params.w), tonumber(app.params.h)
local spr = Sprite(W, H, ColorMode.RGB)
if app.params.palette ~= nil and app.params.palette ~= "" then
  spr:loadPalette(app.params.palette)
end
local art = spr.layers[1]
art.name = app.params.name
-- covered zones (plate / frame pixels from the real menu, or red marks) on a locked layer above the art
if app.params.cover ~= nil and app.params.cover ~= "" then
  local img = Image{ fromFile = app.params.cover }
  local cov = spr:newLayer()
  cov.name = "covered - do not paint"
  spr:newCel(cov, 1, img, Point(0, 0))
  cov.isEditable = false
end
-- centre guides, hidden
local g = spr:newLayer()
g.name = "guides"
local gi = Image(W, H, ColorMode.RGB)
local c = app.pixelColor.rgba(60, 120, 220, 160)
for y = 0, H - 1 do gi:drawPixel(W // 2, y, c) end
for x = 0, W - 1 do gi:drawPixel(x, H // 2, c) end
spr:newCel(g, 1, gi, Point(0, 0))
g.isVisible = false
g.isEditable = false
spr:saveAs(app.params.out)
'''

LUA_EXPORT_LAYER = r'''
local spr = app.open(app.params.inp)
for _, l in ipairs(spr.layers) do l.isVisible = (l.name == app.params.layer) end
spr:flatten()
spr:saveCopyAs(app.params.out)
'''

LUA_ROTATE = r'''
local spr = app.open(app.params.inp)
app.command.CanvasSize{ ui=false, left=spr.width//2, right=spr.width//2, top=spr.height//2, bottom=spr.height//2 }
app.command.SelectAll()
app.command.Rotate{ ui=false, target="mask", angle=tonumber(app.params.angle) }
app.command.AutocropSprite()
spr:saveCopyAs(app.params.out)
'''


def binary():
    exe = os.environ.get('ASEPRITE') or shutil.which('aseprite')
    if not exe or not os.path.exists(exe):
        sys.exit('aseprite not found: build it with scripts/build_aseprite.sh and set ASEPRITE=/path/to/aseprite')
    return exe


def run_lua(code, **params):
    with tempfile.NamedTemporaryFile('w', suffix='.lua', delete=False) as f:
        f.write(code)
        path = f.name
    args = [binary(), '-b']
    for k, v in params.items():
        args += ['--script-param', f'{k}={v}']
    args += ['--script', path]
    r = subprocess.run(args, capture_output=True, text=True)
    os.unlink(path)
    if r.returncode != 0 or 'error' in (r.stderr or '').lower():
        sys.exit(f'aseprite failed: {r.stdout}\n{r.stderr}')
    return r


def main(a):
    if not a:
        sys.exit(__doc__)
    cmd = a[0]
    opt = {a[i][2:]: a[i + 1] for i in range(1, len(a) - 1) if a[i].startswith('--')}
    pos = [x for i, x in enumerate(a[1:], 1) if not x.startswith('--') and not a[i - 1].startswith('--')]
    if cmd == 'template':
        out, w, h = pos[0], pos[1], pos[2]
        run_lua(LUA_TEMPLATE, out=os.path.abspath(out), w=w, h=h, palette=os.path.abspath(opt['palette'])
                if 'palette' in opt else '', cover=os.path.abspath(opt['cover']) if 'cover' in opt else '',
                name=opt.get('name', 'art'))
    elif cmd == 'export':
        run_lua(LUA_EXPORT_LAYER, inp=os.path.abspath(pos[0]), out=os.path.abspath(pos[1]),
                layer=opt.get('layer', 'art'))
    elif cmd == 'sheet':
        out = pos[1]
        subprocess.run([binary(), '-b', pos[0], '--sheet', out, '--sheet-type', 'horizontal',
                        '--data', os.path.splitext(out)[0] + '.json', '--format', 'json-array'], check=True)
    elif cmd == 'palette':
        subprocess.run([binary(), '-b', pos[0], '--palette', pos[1], '--color-mode', 'indexed',
                        '--dithering-algorithm', 'none', '--save-as', pos[2]], check=True)
    elif cmd == 'rotate':
        run_lua(LUA_ROTATE, inp=os.path.abspath(pos[0]), angle=pos[1], out=os.path.abspath(pos[2]))
    else:
        sys.exit(__doc__)
    print('ok')


if __name__ == '__main__':
    main(sys.argv[1:])
