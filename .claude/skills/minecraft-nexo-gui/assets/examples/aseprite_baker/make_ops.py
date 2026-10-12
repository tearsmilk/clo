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
    for bx in (87, 97, 107):
        ell("#c78540", bx, sy - 5, bx + 9, sy - 1)                                  # loaf
        line("#a25b30", [bx + 1, sy - 1], [bx + 8, sy - 1])                          # baked bottom
        line("#e1ae4f", [bx + 2, sy - 5], [bx + 7, sy - 5])                          # lit crust
        for k in range(3):                                                         # scoring cuts
            px("#f8f088", [bx + 2 + k * 3, sy - 3], [bx + 3 + k * 3, sy - 4])
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
shape("#ebe5df", [51, 24], [69, 24], [73, 27], [74, 40], [46, 40], [47, 27])       # jacket
rect("#d7cfc6", 67, 27, 73, 39)
line("#d7cfc6", [60, 29], [60, 39])
shape("#e8421e", [56, 23], [65, 23], [61, 28], [60, 28])                            # neckerchief
for y in (29, 33):
    px("#4a5a82", [57, y], [64, y])
shape("#ebe5df", [47, 26], [44, 30], [41, 35], [45, 37], [48, 32])                 # sleeves (bent arms)
shape("#d7cfc6", [73, 26], [76, 29], [79, 31], [76, 34], [72, 31])
ell("#fad5c9", 38, 33, 43, 37)                                                      # hands on the bread
ell("#f6c4b4", 76, 27, 81, 31)
outline("#7e7973")
L("bread")
shape("#c78540", [40, 35], [77, 28], [80, 31], [43, 38])                            # baguette across
line("#e1ae4f", [44, 35], [76, 29])
line("#a25b30", [45, 37], [78, 31])
for x in (49, 57, 65, 72):
    pen("#f8f088", [x, 35 - (x - 44) // 5], [x + 3, 33 - (x - 44) // 5])
outline("#a25b30")
L("head")
rect("#fad5c9", 52, 12, 69, 22)
rect("#f6c4b4", 67, 13, 69, 22)
line("#fad5c9", [53, 23], [68, 23])
rect("#6b2f25", 52, 12, 69, 13)                                                     # fringe with tufts
for x in range(52, 70, 3):
    px("#6b2f25", [x, 14], [x + 1, 14], [x, 15])
rect("#6b2f25", 52, 12, 53, 20)
rect("#6b2f25", 68, 12, 69, 20)
px("#8c3f2b", [55, 12], [59, 12], [63, 12], [66, 12], [57, 13], [64, 13])
for ex in (56, 63):                                                                 # eyes 2x2 + highlight
    px("#333e5a", [ex, 17], [ex + 1, 17], [ex, 18], [ex + 1, 18])
    px("#ffffff", [ex, 17])
    px("#5e7ea4", [ex + 1, 18])
px("#f07179", [54, 20], [55, 20], [66, 20], [67, 20])                               # blush
px("#b57669", [60, 20], [61, 20])                                                   # mouth
outline("#b57669")
L("hat")
ell("#ffffff", 48, 1, 59, 10)
ell("#ffffff", 62, 1, 73, 10)
ell("#ffffff", 54, -1, 67, 9)
curve("#ebe5df", [50, 8], [52, 10], [56, 10], [58, 8])                              # lobe shadows
curve("#ebe5df", [63, 8], [66, 10], [70, 10], [72, 8])
pen("#d7cfc6", [58, 3], [57, 5], [57, 7])                                          # lobe folds
pen("#d7cfc6", [64, 3], [65, 5], [65, 7])
px("#ffffff", [52, 3], [53, 3], [59, 1], [60, 1])
rect("#ebe5df", 51, 8, 70, 12)                                                      # band
line("#ffffff", [51, 8], [70, 8])
line("#d7cfc6", [51, 12], [70, 12])
outline("#b5a99d")

json.dump({"w": 120, "h": 48, "ops": ops}, open(sys.argv[1], "w"), indent=0)
print(len(ops), "ops")
