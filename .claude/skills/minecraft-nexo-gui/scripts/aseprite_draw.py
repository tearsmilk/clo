#!/usr/bin/env python3
"""Draw pixel art with Aseprite's own tools (headless), from a list of drawing operations.

Why: Aseprite's pencil has a pixel-perfect mode (no doubled corner pixels on curves), a real curve tool, filled
contours, a paint bucket and an Outline command - line art comes out cleaner than hand-rolled raster code.
Coordinates are pixels on the canvas; colours are '#rrggbb' (or '#rrggbbaa').

    python3 aseprite_draw.py ops.json OUT.png [--aseprite OUT.aseprite] [--scale 4 --preview prev.png]

ops.json = {"w": 120, "h": 48, "palette": "kit/palette.gpl" (optional), "ops": [...]} with ops:
    {"op": "layer", "name": "bg"}                       new layer (drawing goes to the newest layer)
    {"op": "rect", "c": "#..", "box": [x0, y0, x1, y1], "fill": true}
    {"op": "ellipse", "c": "#..", "box": [x0, y0, x1, y1], "fill": true}
    {"op": "line", "c": "#..", "pts": [[x, y], [x, y]]}
    {"op": "pencil", "c": "#..", "pts": [[x, y], ...]}  pixel-perfect freehand through the points
    {"op": "curve", "c": "#..", "pts": [[x0,y0],[cx0,cy0],[cx1,cy1],[x1,y1]]}   cubic curve tool
    {"op": "shape", "c": "#..", "pts": [[x, y], ...]}   filled polygon (contour tool)
    {"op": "fill", "c": "#..", "at": [x, y]}            paint bucket, contiguous, on the current layer
    {"op": "px", "c": "#..", "pts": [[x, y], ...]}      single pixels
    {"op": "outline", "c": "#..", "place": "outside"}   Aseprite Outline command on the current layer
    {"op": "merge"}                                     flatten all layers into one
Run `python3 aseprite_tools.py` for the other batch helpers (template, export, palette, rotate, sheet).
"""
import json
import os
import subprocess
import sys
import tempfile

LUA_HEAD = r'''
local spr = Sprite(%d, %d, ColorMode.RGB)
%s
local function C(h)
  local r = tonumber(h:sub(2,3),16); local g = tonumber(h:sub(4,5),16); local b = tonumber(h:sub(6,7),16)
  local a = 255
  if #h >= 9 then a = tonumber(h:sub(8,9),16) end
  return Color{ r=r, g=g, b=b, a=a }
end
local function P(t) local out = {} for i, p in ipairs(t) do out[i] = Point(p[1], p[2]) end return out end
local layer = spr.layers[1]
layer.name = "base"
local function use(tool, color, pts, extra)
  local args = { tool=tool, color=C(color), points=P(pts), layer=layer, frame=spr.frames[1] }
  if extra then for k, v in pairs(extra) do args[k] = v end end
  app.useTool(args)
end
'''

LUA_TAIL = r'''
spr:saveCopyAs("%s")
%s
'''


def lua_op(o):
    op, c = o['op'], o.get('c', '#000000')
    if op == 'layer':
        return f'layer = spr:newLayer(); layer.name = "{o.get("name", "layer")}"'
    if op == 'rect':
        x0, y0, x1, y1 = o['box']
        tool = 'filled_rectangle' if o.get('fill', True) else 'rectangle'
        return f'use("{tool}", "{c}", {{{{{x0},{y0}}},{{{x1},{y1}}}}})'
    if op == 'ellipse':
        x0, y0, x1, y1 = o['box']
        tool = 'filled_ellipse' if o.get('fill', True) else 'ellipse'
        return f'use("{tool}", "{c}", {{{{{x0},{y0}}},{{{x1},{y1}}}}})'
    if op in ('line', 'curve', 'pencil', 'shape'):
        pts = '{' + ','.join(f'{{{x},{y}}}' for x, y in o['pts']) + '}'
        tool = {'line': 'line', 'curve': 'curve', 'pencil': 'pencil', 'shape': 'contour'}[op]
        extra = ', {freehandAlgorithm=1}' if op == 'pencil' else ''
        return f'use("{tool}", "{c}", {pts}{extra})'
    if op == 'fill':
        x, y = o['at']
        return f'use("paint_bucket", "{c}", {{{{{x},{y}}}}}, {{contiguous=true}})'
    if op == 'px':
        return '\n'.join(f'use("pencil", "{c}", {{{{{x},{y}}}}})' for x, y in o['pts'])
    if op == 'outline':
        return (f'app.activeLayer = layer\napp.command.Outline{{ ui=false, color=C("{c}"), '
                f'place="{o.get("place", "outside")}", matrix="circle", bgColor=Color{{a=0}} }}')
    if op == 'merge':
        return 'spr:flatten(); layer = spr.layers[1]'
    raise ValueError(f'unknown op {op}')


def run(spec, out_png, out_ase=None):
    exe = os.environ.get('ASEPRITE')
    if not exe or not os.path.exists(exe):
        sys.exit('set ASEPRITE=/path/to/aseprite (build it with scripts/build_aseprite.sh)')
    pal = f'spr:loadPalette("{os.path.abspath(spec["palette"])}")' if spec.get('palette') else ''
    body = '\n'.join(lua_op(o) for o in spec['ops'])
    save_ase = f'spr:saveAs("{os.path.abspath(out_ase)}")' if out_ase else ''
    code = (LUA_HEAD % (spec['w'], spec['h'], pal)) + body + (LUA_TAIL % (os.path.abspath(out_png), save_ase))
    with tempfile.NamedTemporaryFile('w', suffix='.lua', delete=False) as f:
        f.write(code)
        path = f.name
    r = subprocess.run([exe, '-b', '--script', path], capture_output=True, text=True)
    if r.returncode != 0 or r.stderr.strip():
        print(code[:4000], file=sys.stderr)
        sys.exit(f'aseprite failed:\n{r.stdout}\n{r.stderr}')
    os.unlink(path)


if __name__ == '__main__':
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)
    spec = json.load(open(a[0], encoding='utf-8'))
    ase = a[a.index('--aseprite') + 1] if '--aseprite' in a else None
    run(spec, a[1], ase)
    if '--preview' in a:
        from PIL import Image
        k = int(a[a.index('--scale') + 1]) if '--scale' in a else 4
        im = Image.open(a[1]).convert('RGBA')
        im.resize((im.width * k, im.height * k), Image.NEAREST).save(a[a.index('--preview') + 1])
    print('ok')
