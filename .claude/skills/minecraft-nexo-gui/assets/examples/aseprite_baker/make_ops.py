"""Drawing of a 'Пекарь' (baker) job card, 120x48, as Aseprite tool operations (run aseprite_draw.py on the
JSON this writes). Style follows the bought Jobs pack: chibi character waist-up in the centre, coloured outlines
per part (no black), 2-3 tone shading, a warm scene behind; the bottom centre (x 24..96, y 37..47) is hidden by
the menu's nameplate, so nothing important goes there."""
import json, sys

ops = []
def L(name): ops.append({"op": "layer", "name": name})
def rect(c, x0, y0, x1, y1, fill=True): ops.append({"op": "rect", "c": c, "box": [x0, y0, x1, y1], "fill": fill})
def ell(c, x0, y0, x1, y1, fill=True): ops.append({"op": "ellipse", "c": c, "box": [x0, y0, x1, y1], "fill": fill})
def line(c, a, b): ops.append({"op": "line", "c": c, "pts": [a, b]})
def pen(c, *pts): ops.append({"op": "pencil", "c": c, "pts": list(pts)})
def curve(c, a, b, cc, d): ops.append({"op": "curve", "c": c, "pts": [a, b, cc, d]})
def shape(c, *pts): ops.append({"op": "shape", "c": c, "pts": list(pts)})
def px(c, *pts): ops.append({"op": "px", "c": c, "pts": list(pts)})
def outline(c): ops.append({"op": "outline", "c": c, "place": "outside"})

# ---- background: brick wall
rect("#c78540", 0, 0, 119, 47)
for y in range(0, 40, 5):
    line("#a25b30", [0, y + 4], [119, y + 4])
    line("#e1ae4f", [0, y], [119, y])
    off = 0 if (y // 5) % 2 == 0 else 6
    for x in range(off, 120, 12):
        line("#a25b30", [x, y], [x, y + 3])
rect("#a25b30", 0, 0, 119, 1)
# oven (left): stone body, arched mouth, fire
L("oven")
rect("#7e7973", 2, 12, 31, 40)
ell("#7e7973", 2, 4, 31, 22)
ell("#bebcb7", 4, 6, 29, 20, fill=False)
rect("#371621", 8, 22, 25, 38)
ell("#371621", 8, 15, 25, 30)
ell("#e8421e", 10, 26, 23, 38)
ell("#f9b833", 12, 29, 21, 38)
ell("#fbe255", 14, 32, 19, 38)
pen("#fbe255", [16, 27], [15, 24])
rect("#555555", 2, 37, 31, 40)
line("#bebcb7", [3, 13], [3, 36])
outline("#555555")
# shelves with bread (right)
L("shelves")
for sy in (16, 30):
    rect("#6b2f25", 86, sy, 118, sy + 2)
    line("#c58b55", [86, sy], [118, sy])
    for bx in (88, 98, 108):
        ell("#c78540", bx, sy - 6, bx + 8, sy - 1)
        line("#e1ae4f", [bx + 2, sy - 5], [bx + 6, sy - 5])
        px("#a25b30", [bx + 3, sy - 3], [bx + 5, sy - 3])
outline("#683429")
# counter
L("counter")
rect("#8c3f2b", 0, 38, 119, 47)
line("#c58b55", [0, 38], [119, 38])
line("#6b2f25", [0, 39], [119, 39])
for x in range(10, 120, 22):
    line("#6b2f25", [x, 40], [x, 47])

# ---- baker, centred on x = 60, waist-up
L("body")
shape("#ebe5df", [50, 24], [70, 24], [74, 28], [75, 40], [45, 40], [46, 28])       # jacket
line("#d7cfc6", [69, 26], [72, 39])
rect("#d7cfc6", 66, 27, 72, 39)
shape("#e8421e", [56, 23], [65, 23], [61, 28], [60, 28])                            # neckerchief
for y in (29, 33):
    px("#4a5a82", [57, y], [64, y])
rect("#ebe5df", 42, 27, 47, 36)                                                     # sleeves
rect("#d7cfc6", 74, 27, 78, 36)
ell("#fad5c9", 42, 33, 48, 38)                                                      # hands
ell("#f6c4b4", 73, 31, 79, 36)
outline("#7e7973")
L("bread")
shape("#c78540", [41, 34], [77, 26], [80, 29], [44, 37])                            # baguette across
line("#e1ae4f", [45, 34], [77, 27])
for x in (50, 58, 66, 73):
    pen("#f8f088", [x, 33 - (x - 44) // 4], [x + 2, 31 - (x - 44) // 4])
outline("#a25b30")
L("head")
rect("#fad5c9", 52, 12, 69, 22)
rect("#f6c4b4", 67, 13, 69, 22)
line("#fad5c9", [53, 23], [68, 23])
rect("#6b2f25", 52, 12, 69, 14)                                                     # fringe
rect("#6b2f25", 52, 12, 53, 19)
rect("#6b2f25", 68, 12, 69, 19)
px("#8c3f2b", [55, 12], [59, 12], [63, 12], [66, 13])
px("#6b2f25", [56, 15], [61, 15], [65, 15])
for ex in (56, 63):                                                                 # eyes 2x2 + highlight
    px("#333e5a", [ex, 17], [ex + 1, 17], [ex, 18], [ex + 1, 18])
    px("#ffffff", [ex, 17])
    px("#5e7ea4", [ex + 1, 18])
px("#f07179", [54, 20], [55, 20], [66, 20], [67, 20])                               # blush
px("#b57669", [60, 20], [61, 20])                                                   # mouth
outline("#b57669")
L("hat")
ell("#ffffff", 49, 0, 60, 9)
ell("#ffffff", 55, -1, 66, 8)
ell("#ffffff", 61, 0, 72, 9)
rect("#ebe5df", 51, 7, 70, 12)
line("#d7cfc6", [51, 11], [70, 11])
px("#d7cfc6", [57, 3], [63, 2], [67, 5], [53, 5])
outline("#b5a99d")

json.dump({"w": 120, "h": 48, "ops": ops}, open(sys.argv[1], "w"), indent=0)
print(len(ops), "ops")
