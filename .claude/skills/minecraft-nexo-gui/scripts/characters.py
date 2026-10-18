#!/usr/bin/env python3
"""Characters kit: original blocky Minecraft-like people, mobs and animals, BUILT FROM PARTS, at two densities.

k=1 is vanilla GUI density (a humanoid is about 16x32 px plus its outline, like a mini player); k=2 is "HD"
(about 32x64) and is drawn natively with more detail - eyelids and glints, nostrils, fabric folds, cuffs,
belt buckles, laces, toe caps, chainmail rings, fur and fleece clusters, split hooves - never upscaled.
references/characters.md says how each thing is drawn and how to add one.

Humanoids (front view): player, villager_farmer, villager_librarian, villager_blacksmith, villager_butcher,
villager_cleric, villager_fisherman, villager_cartographer, villager_merchant, knight, guard, wizard, miner,
witch, pirate, king, princess, ninja, archer; humanoid mobs: zombie, skeleton, ender_walker.
Mobs (front view): creeper_plant, spider, slime. Animals (side view): cow, pig, sheep, chicken, horse, cat,
wolf, fox, bee, fish, axolotl, parrot.

Every pixel is drawn as (material ramp, tone) on the layer of its part (Layer). The outline is made last from
the union of all parts - tone 0 of the material it wraps, the softer tone 1 on the lit top / left side (the
selective outline of references/pixel-art-craft.md) - cleaned of L-corner doubles, and every outline pixel is
given to the part it wraps, so the parts rebuild the picture exactly. Held items, shields, crossed arms and
animal heads also get their own outline, so they separate from the body behind them. Light from the top-left
everywhere (a left-facing animal is mirrored in geometry only; its shading is computed in screen space).
Shading follows references/texture-shading.md: five-tone ramps from shading.ramp5 (soft for skin and cloth,
contrasty for metal and gems), contact and cast shadows, clusters, no gradients, no dithering, no
semi-transparent pixels. Deterministic (seeded random only).

API: CATALOG {name: builder(k, **opts) -> modes.Parts}; render(name, k=1, **opts) -> tight RGBA;
parts(name, k=1, **opts) -> [part dicts: name, sprite, x, y] (modes.compose / modes.override /
layers.save_parts / layers.write_aseprite); walk_frames / walk_sheet (4 frames on one shared box);
chart / extras / exploded (sheets); PALETTE (colour variants), ITEMS (held items), SWITCHES (per-character).

Options: pose = idle | wave | hold | walk (frame 0-3 = contact, pass, contact, pass) | cross (villagers'
default) | reach (zombie's default); facing = front | left | right (humanoids turn the head and hold the item
on that side; animals are drawn in side view facing right or left); held = sword | pickaxe | axe | hoe | rod |
book | torch | bow | staff | spear | scepter | potion | map | hammer | cleaver | bag | None; held_mat = iron |
gold | diamond | wood | stone; colour variants skin= hair= top= bottom= shoes= eye= (a PALETTE name or
'#hex'); shadow=False drops the ground shadow; per-character switches (SWITCHES): knight shield= plume=,
king cape=, wolf collar=, parrot perch=, colour= for sheep / horse / cat / axolotl / slime.

    python3 characters.py chart OUT.png [--hd]       every character labelled (x4, HD x3) + walk-cycle strips +
                                                     one character's parts exploded
    python3 characters.py extras OUT.png [--hd]      poses and facing, every held item, colour variants,
                                                     animals facing left
    python3 characters.py render NAME OUT.png [--hd] [--pose P] [--frame N] [--facing F] [--held ITEM]
                       [--held-mat M] [--skin S] [--hair S] [--top S] [--bottom S] [--shoes S] [--eye S]
                       [--opt key=value ...] [--no-shadow]
    python3 characters.py parts NAME OUT_DIR [--hd] [...]   PNG per part + layers.json + _sheet.png + .aseprite
    python3 characters.py walk NAME OUT.png [--hd] [...]    4-frame walk sheet (frames side by side, one size)
    python3 characters.py list                       catalog, poses, held items, palette, switches
"""
import os
import random
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kitchen import _r5, N4                    # noqa: E402
from hub import GOLD, CREAM                     # noqa: E402
from modes import Parts, compose, override      # noqa: E402,F401 (override re-exported for parts)
import layers                                   # noqa: E402

# ------------------------------------------------------------------ ramps (outline, shadow, dark, base, light, hi)
# skin and cloth are matte (soft), hair a little firmer, metal and gems keep the standard contrast
SKIN_LIGHT = _r5('#f2cca8', soft=0.75)
SKIN_FAIR = _r5('#e8b48a', soft=0.75)
SKIN_TAN = _r5('#c98c5e', soft=0.75)
SKIN_BROWN = _r5('#9a6440', soft=0.7)
SKIN_DARK = _r5('#6c4430', soft=0.6)
BLUSH = _r5('#e0857a', soft=0.6)
ZOMBIE = _r5('#6f9e58', soft=0.7)
BONE = _r5('#dcd6c2', soft=0.7)
ENDER = _r5('#2e2638', soft=0.5)
ENDER_EYE = _r5('#d27cf0', soft=0.2)

HAIR_BROWN = _r5('#70452a', soft=0.5)
HAIR_DARK = _r5('#3e302c', soft=0.4)
HAIR_BLACK = _r5('#2e2c38', soft=0.3)
HAIR_BLONDE = _r5('#e0b850', soft=0.5)
HAIR_GINGER = _r5('#c65e2c', soft=0.5)
HAIR_WHITE = _r5('#e2e0d8', soft=0.6)
HAIR_GREY = _r5('#a09c98', soft=0.6)

EYE_W = _r5('#e9ecee', soft=1)
IRIS_BLUE = _r5('#3f72cf', soft=0.3)
IRIS_GREEN = _r5('#3f9a4c', soft=0.3)
IRIS_BROWN = _r5('#6e4224', soft=0.3)

RED = _r5('#c8443a', soft=0.7)
CRIMSON = _r5('#a02c3c', soft=0.7)
ORANGE = _r5('#d8782e', soft=0.7)
YELLOW = _r5('#e6b638', soft=0.6)
GREEN = _r5('#4f8f3c', soft=0.7)
FOREST = _r5('#3a6a40', soft=0.7)
TEAL = _r5('#2f7486', soft=0.7)
BLUE = _r5('#3f66b0', soft=0.7)
NAVY = _r5('#2e3c6a', soft=0.7)
PURPLE = _r5('#7a4aa6', soft=0.7)
PLUM = _r5('#4e3460', soft=0.6)
PINK = _r5('#e08aaa', soft=0.7)
BROWN = _r5('#8a5c36', soft=0.75)
ROBE = _r5('#7c5638', soft=0.8)            # the villagers' brown robe
OLIVE = _r5('#7a7a3c', soft=0.75)
DENIM = _r5('#3e4e78', soft=0.7)
GREYC = _r5('#6c6e78', soft=0.75)          # grey cloth
BLACKC = _r5('#3a3844', soft=0.5)          # black cloth (ninja): keeps a little range
WHITEC = _r5('#e6e2d6', soft=0.8)
LEATHER = _r5('#8c5a34', soft=0.7)
DLEATHER = _r5('#5a3a28', soft=0.6)        # boots, belts
FUR = _r5('#ecebe6', soft=1)               # ermine trim
STRAW = _r5('#e2c062', soft=0.7)
WOOD = _r5('#a06e3c', soft=0.8)            # handles, bows, staffs
DWOOD = _r5('#6a4628', soft=0.8)
PAPER = _r5('#e8dab6', soft=1)
BOOKC = _r5('#a03a32', soft=0.7)           # book cover

IRON = _r5('#a9b2bf')                      # metal: standard (hard) contrast
STEEL = _r5('#8a94a4')
CHAIN = _r5('#7e8692')
DIAMOND = _r5('#4fd2d6', soft=0.2)
STONE = _r5('#8c8e94', soft=0.6)
EMERALD = _r5('#3ccf6c', soft=0.2)
RUBY = _r5('#d0304a', soft=0.2)
SAPPHIRE = _r5('#3a6ae0', soft=0.2)
AMETHYST = _r5('#a65ae0', soft=0.2)
FIRE = _r5('#f2a02c', soft=0.2)
LAMP = _r5('#f6e27a', soft=0.2)
SPARK = _r5('#f0d27a', soft=0.3)
POTION_P = _r5('#b03ca0', soft=0.4)
GLASS = _r5('#a8d0e6', soft=0.5)
SHADOW = _r5('#7c808c', soft=1)            # ground shadow: core [1], penumbra [2] - never outlined

# mobs and animals
LEAF = _r5('#5a9e3e', soft=0.6)            # creeper_plant leaves
MOSSY = _r5('#3e7434', soft=0.6)
BLOOM = _r5('#e0588a', soft=0.4)
SPIDER = _r5('#4a3e44', soft=0.5)
SPIDER_EYE = _r5('#e83a3a', soft=0.2)
SLIME = _r5('#7fd65c', soft=0.4)
SLIME_IN = _r5('#4f9e3a', soft=0.5)
COW = _r5('#5e3e2c', soft=0.7)
COW_W = _r5('#e8e4da', soft=0.8)
HORN = _r5('#d8ceb0', soft=0.8)
PIG = _r5('#eba2a0', soft=0.7)
WOOL = _r5('#ecebe2', soft=0.8)
SHEEP_FACE = _r5('#d6c0a0', soft=0.8)
FEATHER = _r5('#f0eee6', soft=0.9)
COMB = _r5('#d83a32', soft=0.4)
BEAK = _r5('#eab03a', soft=0.5)
HORSE = _r5('#9c6a3e', soft=0.7)
MANE = _r5('#4a3428', soft=0.5)
HOOF = _r5('#4a4040', soft=0.6)
CAT = _r5('#e09a48', soft=0.7)
WOLF = _r5('#c6c4c0', soft=0.8)
COLLAR = _r5('#c83a3a', soft=0.5)
FOX = _r5('#e2782c', soft=0.6)
FOX_W = _r5('#f2ece0', soft=0.9)
BEE = _r5('#f0c234', soft=0.5)
BEE_B = _r5('#3a2e2a', soft=0.4)
WING = _r5('#d6eaf4', soft=0.6)
FISH = _r5('#c8a06a', soft=0.6)
FISH_B = _r5('#8a9a6a', soft=0.6)
AXO = _r5('#f2a2c2', soft=0.6)
AXO_G = _r5('#d8506e', soft=0.5)
PARROT_R = _r5('#d63a32', soft=0.5)
PARROT_B = _r5('#3a6ad6', soft=0.5)
PARROT_Y = _r5('#ecc23a', soft=0.5)
NOSE_P = _r5('#e07a86', soft=0.6)          # pink noses, pig snout inside
PIG_HOOF = _r5('#a8605e', soft=0.6)
MUD = _r5('#8a5a3a', soft=0.6)
ZOMBIE_HAIR = _r5('#3a4a30', soft=0.4)
LENS = _r5('#3a5a5a', soft=0.2)            # goggles

LIGHT = (-0.55, -0.62, 0.56)

# colour variants: names usable in skin= hair= top= bottom= shoes= eye= accent=
PALETTE = {
    'light': SKIN_LIGHT, 'fair': SKIN_FAIR, 'tan': SKIN_TAN, 'brown': SKIN_BROWN, 'dark': SKIN_DARK,
    'zombie': ZOMBIE,
    'hair_brown': HAIR_BROWN, 'hair_dark': HAIR_DARK, 'black': HAIR_BLACK, 'blonde': HAIR_BLONDE,
    'ginger': HAIR_GINGER, 'white': HAIR_WHITE, 'grey': HAIR_GREY,
    'red': RED, 'crimson': CRIMSON, 'orange': ORANGE, 'yellow': YELLOW, 'green': GREEN, 'forest': FOREST,
    'teal': TEAL, 'blue': BLUE, 'navy': NAVY, 'purple': PURPLE, 'plum': PLUM, 'pink': PINK, 'cloth_brown': BROWN,
    'robe': ROBE, 'olive': OLIVE, 'denim': DENIM, 'cloth_grey': GREYC, 'cloth_black': BLACKC,
    'cloth_white': WHITEC, 'leather': LEATHER, 'dark_leather': DLEATHER,
    'iris_blue': IRIS_BLUE, 'iris_green': IRIS_GREEN, 'iris_brown': IRIS_BROWN,
    'iron': IRON, 'gold': GOLD, 'diamond': DIAMOND, 'emerald': EMERALD, 'ruby': RUBY,
}


def ramp_of(v, soft=0.7):
    """A PALETTE name, a '#hex' (built with shading.ramp5) or a ready 6-colour ramp."""
    if v is None or isinstance(v, list):
        return v
    if isinstance(v, str) and v.startswith('#'):
        return _r5(v, soft=soft)
    if v in PALETTE:
        return PALETTE[v]
    if 'hair_' + v in PALETTE:
        return PALETTE['hair_' + v]
    raise KeyError(f'unknown colour {v!r}: use a PALETTE name or #hex')


# ------------------------------------------------------------------ layers: pixels as (ramp, tone)
class Layer:
    """One part of a figure: pixel -> (ramp, tone). `free` pixels (strings, sparks, particles, ground shadow)
    are left out of the outline. own=True: the part gets its own outline ring too (held items, crossed
    arms), so it separates from the body behind it."""

    def __init__(self, name, line=True, own=False):
        self.name, self.line, self.own = name, line, own
        self.px, self.free = {}, set()

    def put(self, x, y, r, t, free=False):
        p = (int(x), int(y))
        self.px[p] = (r, max(0, min(5, int(t))))
        if free:
            self.free.add(p)
        else:
            self.free.discard(p)

    def rect(self, x0, y0, x1, y1, r, t, free=False):
        for y in range(int(y0), int(y1) + 1):
            for x in range(int(x0), int(x1) + 1):
                self.put(x, y, r, t, free)

    def pts(self, pts, r, t, free=False):
        for p in pts:
            self.put(p[0], p[1], r, t, free)

    def tone(self, x, y):
        v = self.px.get((int(x), int(y)))
        return v[1] if v else None

    def ramp(self, x, y):
        v = self.px.get((int(x), int(y)))
        return v[0] if v else None

    def shift(self, x, y, d, lo=1, hi=5):
        p = (int(x), int(y))
        if p in self.px:
            r, t = self.px[p]
            self.px[p] = (r, max(lo, min(hi, t + d)))

    def drop(self, pts):
        for p in pts:
            self.px.pop(p, None)
            self.free.discard(p)

    def mask(self):
        return set(self.px)


class Fig:
    """A figure under construction: named layers in a fixed bottom -> top order (`order`; unknown names go on
    top in creation order). finish() adds the outline and returns modes.Parts."""

    def __init__(self, k, W, H, order=()):
        self.k, self.W, self.H = k, W, H
        self.rank = {n: i for i, n in enumerate(order)}
        self.layers = {}
        self.ring_px = {}                                  # outline pixels this figure added: pixel -> layer

    def __call__(self, name, line=True, own=False):
        if name not in self.layers:
            self.layers[name] = Layer(name, line, own)
            if name not in self.rank:
                self.rank[name] = 1000 + len(self.layers)
        L = self.layers[name]
        L.own = L.own or own
        return L

    def ordered(self):
        return sorted(self.layers.values(), key=lambda L: self.rank[L.name])

    def owner(self):
        """pixel -> (layer, ramp, tone) of the topmost part there."""
        own = {}
        for L in self.ordered():
            for p, v in L.px.items():
                own[p] = (L, v[0], v[1])
        return own

    def _ring(self, solid, ownmap, into=None):
        """Selective outline round `solid`: ring pixels on the lit top / left take tone 1 of the ramp they wrap,
        the others tone 0; each goes to the topmost part among its 4 neighbours (or to `into`)."""
        rank = self.rank
        ring = {(x + dx, y + dy) for (x, y) in solid for dx, dy in N4} - set(solid)
        for q in sorted(ring):
            cur = ownmap.get(q)
            if cur and q in cur[0].free and cur[0].name != 'shadow':
                continue                                   # a string or a spark stays as it is
            if into is None and cur and cur[0].name != 'shadow':
                continue
            nb = [ownmap[(q[0] + dx, q[1] + dy)] for dx, dy in N4 if (q[0] + dx, q[1] + dy) in solid]
            if not nb:
                continue
            L, r, _ = max(nb, key=lambda v: rank[v[0].name])
            below = (q[0], q[1] + 1) in solid or (q[0] + 1, q[1]) in solid
            above = (q[0], q[1] - 1) in solid or (q[0] - 1, q[1]) in solid
            t = 1 if below and not above else 0
            (into or L).put(q[0], q[1], r, t)
            self.ring_px[q] = into or L

    def composite(self):
        im = Image.new('RGBA', (self.W, self.H), (0, 0, 0, 0))
        px = im.load()
        for L in self.ordered():
            for (x, y), (r, t) in L.px.items():
                if 0 <= x < self.W and 0 <= y < self.H:
                    px[x, y] = r[t]
        return im

    def _clean_doubles(self, passes=3):
        """Pixel-perfect outline (references/pixel-art-craft.md): an outline pixel that makes an L-corner with
        two neighbours of its colour is dropped from its part, so diagonal runs stay 1 px thin; whatever lies
        under it (a lower part or nothing) shows instead."""
        from shading import _is_double
        for _ in range(passes):
            im = self.composite()
            px = im.load()
            n = 0
            for q in sorted(self.ring_px):
                L = self.ring_px[q]
                x, y = q
                if q not in L.px or not (0 <= x < self.W and 0 <= y < self.H):
                    continue
                if _is_double(px, self.W, self.H, x, y):
                    L.drop([q])
                    del self.ring_px[q]
                    n += 1
                    under = [M for M in self.ordered() if q in M.px]
                    px[x, y] = under[-1].px[q][0][under[-1].px[q][1]] if under else (0, 0, 0, 0)
            if not n:
                break

    def finish(self, outline=True):
        if outline:
            own = self.owner()
            solid = {p for p, (L, r, t) in own.items() if L.line and p not in L.free}
            masks = {L.name: {p for p in L.px if p not in L.free} for L in self.ordered() if L.own}
            self._ring(solid, own)
            for L in self.ordered():                       # parts that keep their own outline
                if L.own and L.px:
                    m = masks[L.name]                      # its own pixels, before the figure's ring
                    lm = {p: (L, *L.px[p]) for p in m}
                    full = self.owner()
                    ring = {(x + dx, y + dy) for (x, y) in m for dx, dy in N4} - m
                    for q in sorted(ring):
                        cur = full.get(q)
                        if cur and self.rank[cur[0].name] > self.rank[L.name]:
                            continue                       # a part above covers it anyway
                        if cur and cur[0] is L and q not in self.ring_px:
                            continue
                        nb = [lm[(q[0] + dx, q[1] + dy)] for dx, dy in N4 if (q[0] + dx, q[1] + dy) in m]
                        if not nb:
                            continue
                        r = nb[0][1]
                        below = (q[0], q[1] + 1) in m or (q[0] + 1, q[1]) in m
                        above = (q[0], q[1] - 1) in m or (q[0] - 1, q[1]) in m
                        L.put(q[0], q[1], r, 1 if below and not above else 0)
                        self.ring_px[q] = L
            self._clean_doubles()
        Pt = Parts(self.W, self.H)
        for L in self.ordered():
            if not L.px:
                continue

            def draw(im, L=L):
                px = im.load()
                for (x, y), (r, t) in L.px.items():
                    if 0 <= x < im.width and 0 <= y < im.height:
                        px[x, y] = r[t]
            Pt.add(L.name, draw)
        return Pt


# ------------------------------------------------------------------ small geometry helpers
def ell(cx, cy, rx, ry=None):
    """Pixels whose centres lie in the ellipse."""
    ry = ry or rx
    return {(x, y) for y in range(int(cy - ry - 1), int(cy + ry + 2)) for x in range(int(cx - rx - 1), int(cx + rx + 2))
            if ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= 1}


def ground_shadow(fig, cx, gy, rx, ry=None):
    """Projected shadow on the ground under the feet: hard core SHADOW[1], a penumbra one step lighter as a
    crescent on the far (right) side. Never outlined."""
    k = fig.k
    ry = ry or 1.2 * k + 0.3
    L = fig('shadow', line=False)
    core = ell(cx + 0.5 * k, gy, rx, ry)
    pen = ell(cx + 1.5 * k, gy, rx + 0.5 * k, ry) - core
    for p in pen:
        if p[0] > cx:
            L.put(*p, SHADOW, 2, free=True)
    for p in core:
        L.put(*p, SHADOW, 1, free=True)


def box(L, b, r, base=3, left=4, right=2, top=None, bottom=None):
    """A cuboid's front face: one base tone, a lit left column, a darker right column, optional top / bottom
    rows (a flat face stays mostly one tone - volume comes from the edges and neighbours)."""
    x0, y0, x1, y1 = b
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            t = base
            if x == x1 and right is not None:
                t = right
            if x == x0 and left is not None:
                t = left
            if y == y0 and top is not None:
                t = top
            if y == y1 and bottom is not None:
                t = bottom
            L.put(x, y, r, t)


def line(x0, y0, x1, y1):
    n = max(abs(x1 - x0), abs(y1 - y0))
    return [(round(x0 + (x1 - x0) * i / max(1, n)), round(y0 + (y1 - y0) * i / max(1, n))) for i in range(n + 1)]


# ------------------------------------------------------------------ humanoid body geometry
KINDS = {                       # in skin units (x k): head w, h; torso w, h; arm w, h; leg w, h; leg gap; arm gap
    'player':   dict(head=(8, 8), torso=(8, 12), arm=(4, 12), leg=(4, 12), lgap=0, agap=0),
    'slim':     dict(head=(8, 8), torso=(8, 12), arm=(3, 12), leg=(4, 12), lgap=0, agap=0),
    'villager': dict(head=(8, 10), torso=(8, 12), arm=(4, 12), leg=(4, 10), lgap=0, agap=0),
    'skinny':   dict(head=(8, 8), torso=(8, 12), arm=(2, 12), leg=(2, 12), lgap=2, agap=0),
    'tall':     dict(head=(8, 8), torso=(8, 12), arm=(2, 26), leg=(2, 26), lgap=2, agap=0),
}
POSES = ('idle', 'wave', 'hold', 'walk', 'cross', 'reach')
ORDER = ('shadow', 'back', 'cape', 'leg_l', 'leg_r', 'foot_l', 'foot_r', 'torso', 'robe', 'belt', 'chest',
         'arm_l', 'arm_r', 'arms', 'collar', 'shield_back', 'item', 'hand_l', 'hand_r', 'shield', 'head', 'face', 'beard',
         'hair', 'hat', 'acc', 'fx')


class Body:
    """Boxes (x0, y0, x1, y1 inclusive) of a blocky humanoid in front view for a pose / walk frame.
    side = which arm holds the item ('l' = screen left); facing shifts the face features (fs)."""

    def __init__(self, k, kind='player', pose='idle', frame=0, facing='front', cx=None, top=None, side='r',
                 held=False, reach=False, cross=False):
        s = KINDS[kind]
        self.k, self.kind, self.pose, self.frame, self.facing, self.side = k, kind, pose, frame, facing, side
        hw, hh = s['head']
        tw, th = s['torso']
        aw, ah = s['arm']
        lw, lh = s['leg']
        lg = s['lgap']
        cx = cx if cx is not None else 28 * k
        top = top if top is not None else 18 * k
        walk = pose == 'walk'
        bob = k if walk and frame in (1, 3) else 0
        self.ground = top + (hh + th + lh) * k              # first row under the feet
        self.cx = cx
        b = {}
        hy = top - bob
        b['head'] = (cx - hw * k // 2, hy, cx + hw * k // 2 - 1, hy + hh * k - 1)
        ty = b['head'][3] + 1
        b['torso'] = (cx - tw * k // 2, ty, cx + tw * k // 2 - 1, ty + th * k - 1)
        hip = b['torso'][3] + 1
        lift = {'l': 0, 'r': 0}
        if walk and frame == 1:
            lift['l'] = 2 * k
        if walk and frame == 3:
            lift['r'] = 2 * k
        gx = lg * k // 2
        b['leg_l'] = (cx - gx - lw * k, hip, cx - gx - 1, self.ground - 1 - lift['l'])
        b['leg_r'] = (cx + gx, hip, cx + gx + lw * k - 1, self.ground - 1 - lift['r'])
        fh = 2 * k if kind != 'tall' else 2 * k
        for sd in 'lr':
            x0, y0, x1, y1 = b['leg_' + sd]
            b['foot_' + sd] = (x0, y1 - fh + 1, x1, y1)
        tx0, _, tx1, _ = b['torso']
        ag = s['agap'] * k
        b['arm_l'] = [tx0 - ag - aw * k, ty, tx0 - ag - 1, ty + ah * k - 1]
        b['arm_r'] = [tx1 + 1 + ag, ty, tx1 + ag + aw * k, ty + ah * k - 1]
        self.arm_mode = {'l': 'down', 'r': 'down'}
        hold = held and pose in ('idle', 'hold', 'walk', 'wave')
        if walk:
            sw = {1: ('l', 'r'), 3: ('r', 'l')}.get(frame)
            if sw and not reach and not cross:
                b['arm_' + sw[0]][3] -= k                   # back swing: the hand hides a little
                b['arm_' + sw[1]][3] += k                   # forward swing: the hand comes lower
        if pose == 'wave':
            w = ('l' if side == 'r' else 'r') if hold else side   # the free hand waves
            a = b['arm_' + w]
            dx = -k if w == 'l' else k
            a[0] += dx
            a[2] += dx
            a[3] = ty + 3 * k
            a[1] = a[3] - ah * k + 1
            self.arm_mode[w] = 'up'
        if hold:
            a = b['arm_' + side]
            if not walk:
                a[3] -= 2 * k                               # forearm forward: the arm looks shorter
            self.arm_mode[side] = 'hold'
        if pose == 'reach' or (walk and reach):             # zombie: both arms toward the viewer
            for sd in 'lr':
                a = b['arm_' + sd]
                a[3] = ty + 8 * k - 1
                self.arm_mode[sd] = 'reach'
        if pose == 'cross' or cross:
            self.arm_mode = {'l': 'cross', 'r': 'cross'}
        for sd in 'lr':
            b['arm_' + sd] = tuple(b['arm_' + sd])
            x0, y0, x1, y1 = b['arm_' + sd]
            hn = (3 if aw >= 3 else 2) * k
            if self.arm_mode[sd] == 'up':
                b['hand_' + sd] = (x0, y0, x1, y0 + hn - 1)
            elif self.arm_mode[sd] == 'reach':
                b['hand_' + sd] = (x0, y1 - 4 * k + 1, x1, y1)
            else:
                b['hand_' + sd] = (x0, y1 - hn + 1, x1, y1)
        self.b = b
        self.fs = {'front': 0, 'left': -k, 'right': k}[facing]

    def __getitem__(self, n):
        return self.b[n]


# ------------------------------------------------------------------ the humanoid builder
class H:
    """Context handed to every painter: k, fig, body boxes (b), look (materials + styles), options."""

    def __init__(self, k, look, pose, frame, facing, held, held_mat, shadow, opts):
        self.k, self.look, self.opts = k, look, opts
        self.pose, self.frame, self.facing, self.held, self.held_mat = pose, frame, facing, held, held_mat
        kind = look.get('kind', 'player')
        self.side = 'l' if facing == 'left' else 'r'
        if opts.get('hand') in ('l', 'r', 'left', 'right'):
            self.side = opts['hand'][0]
        self.fig = Fig(k, 64 * k, 80 * k, ORDER)
        self.body = Body(k, kind, pose, frame, facing, side=self.side, held=bool(held),
                         reach=look.get('pose') == 'reach', cross=look.get('walk_cross', False))
        self.b = self.body.b
        self.fs = self.body.fs
        self.rnd = random.Random(look.get('seed', 7) * 31 + k)
        self.shadow = shadow

    def m(self, slot):
        return self.look[slot]

    def L(self, name, **kw):
        return self.fig(name, **kw)


def p_shadow(h):
    if not h.shadow:
        return
    k = h.k
    x0 = min(h.b['leg_l'][0], h.b['arm_l'][0])
    x1 = max(h.b['leg_r'][2], h.b['arm_r'][2])
    w = h.look.get('shadow_w', 0)
    ground_shadow(h.fig, (x0 + x1 + 1) / 2, h.body.ground + 0.5 * k, (x1 - x0 + 1) / 2 + w * k, 1.2 * k + 0.3)


# ---- heads and faces
def p_head(h):
    """The skin cube: base tone, lit left column, darker right column and chin row; a turned head shows a
    strip of its side (lit when it turns right, in shade when it turns left)."""
    k = h.k
    S = h.m('skin')
    L = h.L('head')
    x0, y0, x1, y1 = h.b['head']
    box(L, (x0, y0, x1, y1), S, left=4, right=2, bottom=2)
    if k == 2:
        for y in range(y0 + 2, y1):
            L.put(x1 - 1, y, S, 2 if y > y0 + 9 else 3)
        L.rect(x0 + 2, y1 - 1, x1 - 2, y1 - 1, S, 2)
    if h.facing == 'right':
        L.rect(x0, y0, x0 + k - 1, y1, S, 4)
        L.rect(x0 + k, y0, x0 + k, y1, S, 2)
    elif h.facing == 'left':
        L.rect(x1 - k + 1, y0, x1, y1, S, 2)
        L.rect(x1 - k, y0, x1 - k, y1, S, 1)


def eye(L, x, y, k, iris, side, white=True, look=0):
    """One eye at (x, y) = top-left. k=1: white + iris (2x1). k=2: a lid line over a 3x2 eye - white on the
    outer side, a 2x2 iris with its glint at the top-left (one light for the whole picture)."""
    if k == 1:
        if side == 'l':
            if white:
                L.put(x, y, EYE_W, 3)
            L.put(x + 1, y, iris, 2)
        else:
            L.put(x, y, iris, 2)
            if white:
                L.put(x + 1, y, EYE_W, 3)
        return
    ox = x if side == 'l' else x + 1
    ix = x + 1 if side == 'l' else x
    ix += look
    for j in (0, 1):
        if white:
            L.put(ox if side == 'l' else x + 2, y + 1 + j, EYE_W, 3)
    L.put(ix, y + 1, EYE_W, 5)
    L.put(ix + 1, y + 1, iris, 2)
    L.put(ix, y + 2, iris, 3)
    L.put(ix + 1, y + 2, iris, 1)


def p_face_player(h, brows=True, blush='hd', mouth='smile'):
    k = h.k
    S = h.m('skin')
    hair = h.m('hair')
    iris = h.m('eye')
    L = h.L('face')
    x0, y0, x1, y1 = h.b['head']
    f = h.fs
    if k == 1:
        ey = y0 + 4
        eye(L, x0 + 1 + f, ey, 1, iris, 'l')
        eye(L, x0 + 5 + f, ey, 1, iris, 'r')
        if brows:
            for x in (x0 + 1 + f, x0 + 2 + f, x0 + 5 + f, x0 + 6 + f):
                L.put(x, ey - 1, hair, 2)
        if mouth:
            L.put(x0 + 3 + f, y0 + 6, S, 1)
            L.put(x0 + 4 + f, y0 + 6, S, 1)
        if blush and blush != 'hd':
            L.put(x0 + 1 + f, y0 + 5, BLUSH, 3)
            L.put(x0 + 6 + f, y0 + 5, BLUSH, 2)
        return
    ey = y0 + 7
    if brows:
        L.rect(x0 + 3 + f, ey - 1, x0 + 5 + f, ey - 1, hair, 1)
        L.put(x0 + 2 + f, ey, hair, 2)
        L.rect(x0 + 10 + f, ey - 1, x0 + 12 + f, ey - 1, hair, 1)
        L.put(x0 + 13 + f, ey, hair, 2)
    for x in range(x0 + 3 + f, x0 + 6 + f):                 # upper lid: the eye's dark top line
        L.put(x, ey + 1, S, 0)
    for x in range(x0 + 10 + f, x0 + 13 + f):
        L.put(x, ey + 1, S, 0)
    eye(L, x0 + 3 + f, ey + 1, 2, iris, 'l')
    eye(L, x0 + 10 + f, ey + 1, 2, iris, 'r')
    L.put(x0 + 7 + f, ey + 3, S, 4)                        # nose: lit bridge and tip, shadow under / right
    L.put(x0 + 8 + f, ey + 4, S, 2)
    L.put(x0 + 7 + f, ey + 5, S, 2)
    L.put(x0 + 8 + f, ey + 5, S, 2)
    if blush:
        L.rect(x0 + 2 + f, ey + 5, x0 + 3 + f, ey + 5, BLUSH, 3)
        L.rect(x0 + 12 + f, ey + 5, x0 + 13 + f, ey + 5, BLUSH, 2)
    my = ey + 6
    if mouth == 'smile':
        L.rect(x0 + 7 + f, my, x0 + 8 + f, my, S, 1)
        L.put(x0 + 6 + f, my, S, 2)
        L.put(x0 + 9 + f, my, S, 2)
        L.put(x0 + 5 + f, my - 1, S, 2)
        L.put(x0 + 10 + f, my - 1, S, 2)
    elif mouth == 'flat':
        L.rect(x0 + 6 + f, my, x0 + 9 + f, my, S, 1)
    elif mouth == 'open':
        L.rect(x0 + 6 + f, my, x0 + 9 + f, my + 1, S, 0)
        L.rect(x0 + 7 + f, my + 1, x0 + 8 + f, my + 1, BLUSH, 2)


# ---- hair
def p_hair(h, style=None):
    """Hair on the head cube: a lit crown (a sheen streak on the top-left), a fringe with an uneven lower edge
    (strand clusters), sideburns; the fringe casts a soft shadow on the forehead (one step down)."""
    style = style or h.look.get('hair_style', 'short')
    if style in (None, 'bald'):
        return
    k = h.k
    R = h.m('hair')
    S = h.m('skin')
    L = h.L('hair')
    F = h.L('face')
    x0, y0, x1, y1 = h.b['head']
    w = x1 - x0 + 1
    f = h.fs
    if k == 1:
        fr = {'short': [3, 3, 3, 3, 2, 2, 3, 3], 'swept': [3, 3, 3, 3, 3, 2, 2, 3],
              'long': [8, 3, 3, 2, 2, 3, 3, 8], 'bob': [6, 3, 2, 2, 2, 2, 3, 6],
              'spiky': [3, 2, 3, 2, 3, 2, 3, 3], 'bun': [3, 2, 2, 2, 2, 2, 2, 3],
              'cap': [2] * 8, 'beardless_old': [3, 1, 1, 1, 1, 1, 1, 3]}.get(style, [3] * 8)
    else:
        fr = {'short': [7, 6, 6, 5, 5, 5, 6, 5, 4, 4, 4, 5, 5, 6, 6, 7],
              'swept': [7, 6, 6, 6, 6, 6, 5, 5, 5, 4, 4, 4, 4, 5, 6, 7],
              'long': [16, 16, 6, 5, 5, 4, 4, 5, 4, 4, 5, 5, 6, 6, 16, 16],
              'bob': [12, 12, 6, 5, 5, 4, 4, 4, 4, 4, 4, 5, 5, 6, 12, 12],
              'spiky': [7, 5, 6, 4, 5, 6, 4, 5, 6, 4, 5, 6, 4, 6, 6, 7],
              'bun': [6, 5, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 5, 6],
              'cap': [4] * 16, 'beardless_old': [7, 6, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 6, 7]}.get(style, [6] * 16)
    if f:
        fr = (fr[1:] + fr[-1:]) if f < 0 else (fr[:1] + fr[:-1])
        if k == 2:
            fr = (fr[1:] + fr[-1:]) if f < 0 else (fr[:1] + fr[:-1])
    for i in range(w):
        x = x0 + i
        n = min(fr[i], y1 - y0 + 1)
        for j in range(n):
            y = y0 + j
            t = 3
            if j == 0:
                t = 4
            if i == w - 1 or (k == 2 and i == w - 2 and j > 1):
                t = 2
            if i == 0:
                t = 4 if j < n - 1 else 3
            if j == n - 1 and n < 6 * k:
                t = 2 if i > w // 2 else 3                  # strand tips turn into the shadow
            L.put(x, y, R, t)
        if n < y1 - y0 + 1 and 0 < i < w - 1 and k == 2:
            F.put(x, y0 + n, S, 2)                          # the fringe's soft shadow on the forehead
    # sheen: a short arc of light on the top-left of the crown
    if k == 1:
        L.put(x0 + 1, y0, R, 5)
        L.put(x0 + 2, y0, R, 5)
        L.put(x0 + 3, y0 + 1, R, 4)
    else:
        for (x, y) in ((2, 1), (3, 1), (4, 1), (5, 1), (6, 2), (7, 2), (3, 2), (4, 2)):
            L.put(x0 + x, y0 + y, R, 5 if y == 1 else 4)
        for (x, y) in ((9, 3), (10, 3), (11, 4), (12, 4), (6, 4), (7, 4)):   # strand clusters
            if fr[x] > y + 1:
                L.put(x0 + x, y0 + y, R, 2)
    if style == 'bun':
        bx = (x0 + x1) // 2
        top = y0 - 3 * k
        for (x, y) in ell(bx + 0.5, top + 1.5 * k, 2.2 * k, 1.6 * k):
            L.put(x, y, R, 4 if x < bx and y < top + k else 3 if x < bx + k else 2)
    if style == 'spiky':
        for i in range(0, w, 2 * k):
            for j in range(k):
                for q in range(k):
                    L.put(x0 + i + q, y0 - 1 - j, R, 4 if i < w // 2 else 3)


# ---- torso, arms, legs
def fold(L, x, y, r, k, n=3, d=1, lit=True):
    """A cloth fold at k=2: a dark-mid streak running down-left / down-right with a light-mid lip above it."""
    for i in range(n):
        L.put(x + i * d, y + i, r, 2)
        if lit:
            L.put(x + i * d, y + i - 1, r, 4)


def p_torso_shirt(h, R=None, style='tee', folds=True):
    """A shirt / hoodie front: base cloth, the arm's contact shadow on the left column, the head's cast
    shadow round the neck, a darker hem; k=2 adds folds at the waist and a seam."""
    k = h.k
    R = R or h.m('top')
    L = h.L('torso')
    x0, y0, x1, y1 = h.b['torso']
    box(L, (x0, y0, x1, y1), R, left=2, right=2, bottom=2)
    cx = (x0 + x1 + 1) // 2
    if k == 1:
        L.rect(cx - 2, y0, cx + 1, y0, R, 1)               # under the chin
        L.put(cx - 3, y0, R, 2)
        L.put(cx + 2, y0, R, 2)
    else:
        L.rect(cx - 5, y0, cx + 4, y0, R, 2)
        L.rect(cx - 3, y0, cx + 2, y0 + 1, R, 1)
        L.rect(x0 + 1, y0 + 1, x0 + 1, y1 - 1, R, 4)       # lit chest plane beside the arm's shadow
        if folds:
            for i in range(3):                               # creases from the armpits
                L.put(x0 + 2 + i, y0 + 8 + i, R, 2)
                L.put(x0 + 2 + i, y0 + 7 + i, R, 4)
                L.put(x1 - 2 - i, y0 + 8 + i, R, 2)
        L.rect(x0, y1 - 1, x1, y1 - 1, R, 2)
    if style == 'hoodie':
        CR = CREAM
        if k == 1:
            L.put(cx - 2, y0 + 1, CR, 3)
            L.put(cx - 2, y0 + 2, CR, 2)
            L.put(cx + 1, y0 + 1, CR, 3)
            L.put(cx + 1, y0 + 2, CR, 2)
            L.rect(x0 + 1, y0 + 7, x1 - 1, y0 + 7, R, 2)     # kangaroo pocket
            L.put(x0 + 1, y0 + 8, R, 2)
            L.put(x1 - 1, y0 + 8, R, 2)
            L.rect(x0, y1, x1, y1, R, 1)
        else:
            for x in (cx - 3, cx + 2):                       # drawstrings with metal tips
                L.rect(x, y0 + 2, x, y0 + 6, CR, 3 if x < cx else 2)
                L.put(x, y0 + 7, IRON, 4 if x < cx else 3)
                L.put(x, y0 + 8, IRON, 2)
            L.rect(x0 + 3, y0 + 2, x0 + 3, y0 + 2, R, 1)
            L.rect(x1 - 3, y0 + 2, x1 - 3, y0 + 2, R, 1)
            py = y0 + 14                                     # kangaroo pocket: slanted openings, top seam
            L.rect(x0 + 4, py, x1 - 4, py, R, 2)
            L.rect(x0 + 4, py + 1, x1 - 4, py + 1, R, 4)
            for j in range(5):
                L.put(x0 + 3 - (j > 2), py + j, R, 1 if j else 2)
                L.put(x1 - 3 + (j > 2), py + j, R, 1 if j else 2)
            for x in range(x0, x1 + 1):                      # ribbed hem
                L.put(x, y1 - 1, R, 2 if x % 2 else 3)
                L.put(x, y1, R, 1 if x % 2 else 2)


def p_hood(h, R=None):
    """The hood bunched round the neck (hoodie): a lit roll on the left, the lining in shadow."""
    k = h.k
    R = R or h.m('top')
    L = h.L('torso')
    x0, y0, x1, y1 = h.b['torso']
    cx = (x0 + x1 + 1) // 2
    if k == 1:
        L.put(x0 + 1, y0, R, 4)
        L.put(x1 - 1, y0, R, 3)
        return
    for x in range(x0 + 1, x1):
        if x < cx - 5 or x > cx + 4:
            L.put(x, y0, R, 4 if x < cx else 3)
            L.put(x, y0 + 1, R, 3 if x < cx else 2)
    L.rect(x0 + 2, y0 + 2, x0 + 3, y0 + 2, R, 2)
    L.rect(x1 - 3, y0 + 2, x1 - 2, y0 + 2, R, 1)


def p_arms(h, R=None, sleeve='long', cuff=True, folds=True):
    """Arms: sleeve cloth, skin below short sleeves. The screen-left arm is lit on its outer side, the right
    arm darker on its outer side; the shoulder tops catch the light; a raised arm shows its sleeve below the
    hand. k=2: an elbow crease (a dark-mid fold with a light lip on the lit arm) and a two-row cuff."""
    k = h.k
    R = R or h.m('top')
    S = h.m('skin')
    for sd in 'lr':
        mode = h.body.arm_mode[sd]
        if mode == 'cross':
            continue
        L = h.L('arm_' + sd)
        x0, y0, x1, y1 = h.b['arm_' + sd]
        hx0, hy0, hx1, hy1 = h.b['hand_' + sd]
        if mode == 'reach':
            p_arm_reach(h, sd, R, sleeve)
            continue
        lt, rt = (4, 3) if sd == 'l' else (3, 2)
        if k == 2 and sd == 'r':
            rt = 1
        short = 4 * k if sleeve == 'short' else 99
        for y in range(y0, y1 + 1):
            if hy0 <= y <= hy1:
                continue
            for x in range(x0, x1 + 1):
                if mode == 'up':
                    rr = S if y < y1 - short + 1 else R
                else:
                    rr = S if y > y0 + short - 1 else R
                t = lt if x == x0 else rt if x == x1 else 3
                if y == y0 and mode != 'up':
                    t = 4 if sd == 'l' else 3                # the shoulder top catches the light
                L.put(x, y, rr, t)
        if k == 2 and mode != 'up' and sleeve != 'short' and folds:
            fy = y0 + 11
            if sd == 'l':
                for i, x in enumerate(range(x0 + 2, x0 + 5)):
                    L.put(x, fy + i // 2, R, 2)
                    L.put(x, fy - 1 + i // 2, R, 4)
            else:
                for i, x in enumerate(range(x1 - 2, x1 - 5, -1)):
                    L.put(x, fy + i // 2, R, 2)
        if cuff and sleeve == 'long':
            cy = hy0 - 1 if mode != 'up' else hy1 + 1
            for x in range(x0, x1 + 1):
                L.put(x, cy, R, 2 if x != x0 else 3)
                if k == 2:
                    L.put(x, cy - (1 if mode != 'up' else -1), R, 4 if x == x0 and sd == 'l' else 3)


def p_arm_reach(h, sd, R, sleeve):
    """An arm pointing at the viewer (zombie): the sleeve's lit top face runs down from the shoulder, the
    fist's front face at its end."""
    k = h.k
    S = h.m('skin')
    L = h.L('arm_' + sd)
    x0, y0, x1, y1 = h.b['arm_' + sd]
    hx0, hy0, hx1, hy1 = h.b['hand_' + sd]
    for y in range(y0, hy0):
        for x in range(x0, x1 + 1):
            t = 4 if y < y0 + k else 3
            if x == x1:
                t = 2 if sd == 'r' else 3
            if x == x0 and sd == 'l':
                t = 4
            L.put(x, y, R, t)
        if sleeve == 'torn' and (y - y0) % (2 * k) == 0:
            L.put(x0 + (y // k) % (x1 - x0 + 1), y, S, 3)


def p_hands(h):
    """Hands: a skin block with a lit knuckle row (k=2: finger notches, the thumb on the inner side);
    a raised hand shows its palm with fingers."""
    k = h.k
    S = h.m('skin')
    for sd in 'lr':
        mode = h.body.arm_mode[sd]
        if mode == 'cross':
            continue
        L = h.L('hand_' + sd)
        x0, y0, x1, y1 = h.b['hand_' + sd]
        R = h.look.get('glove') or S
        if mode == 'reach':
            box(L, (x0, y0, x1, y1), R, left=3 if sd == 'l' else 3, right=2, top=4, bottom=2)
            if k == 2:
                for x in range(x0 + 1, x1, 2):
                    L.put(x, y0 + 3, R, 2)
                L.rect(x0 + 1, y0 + 1, x1 - 1, y0 + 1, R, 4)
            else:
                L.put(x0 + 1, y0 + 2, R, 2)
            continue
        lt, rt = (4, 3) if sd == 'l' else (3, 2)
        box(L, (x0, y0, x1, y1), R, left=lt, right=rt, bottom=2)
        if mode == 'up':
            if k == 1:
                L.put(x0 + 1, y0, R, 4)
                L.put(x1 - 1, y0, R, 4)
                L.put(x0 + (x1 - x0) // 2, y0, R, 4)
                for x in range(x0, x1 + 1):
                    L.put(x, y1, R, 2)
            else:
                for x in range(x0, x1 + 1):                  # fingers: lit tips, dark gaps
                    for y in range(y0, y0 + 3):
                        gap = (x - x0) % 2 == 1
                        if gap and y < y0 + 2:
                            L.drop([(x, y)])
                        else:
                            L.put(x, y, R, 4 if y == y0 else 3)
                L.rect(x0 + 1, y0 + 3, x1 - 1, y0 + 4, R, 4)   # palm
                L.put(x1, y0 + 3, R, 2)
            continue
        if k == 2:
            th = x1 if sd == 'l' else x0                     # the thumb faces the body
            L.put(th, y0 + 1, R, 2)
            L.put(th, y0 + 2, R, 2)
            for x in range(x0 + 1, x1, 2):
                L.put(x, y1, R, 1)
            L.rect(x0, y0, x1, y0, R, 4 if sd == 'l' else 3)
        if mode == 'hold' and k == 2:
            L.rect(x0 + 1, y0 + 2, x1 - 1, y0 + 2, R, 2)      # the fist round the handle


def p_legs(h, R=None, style='pants'):
    """Trousers: the lit leg keeps a light outer column, the inner columns meet in shadow, the shirt casts a
    band of shadow under its hem; k=2: a knee highlight with a crease under it, a rolled hem over the shoe
    (jeans: plus a dark outer seam)."""
    k = h.k
    R = R or h.m('bottom')
    for sd in 'lr':
        L = h.L('leg_' + sd)
        x0, y0, x1, y1 = h.b['leg_' + sd]
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if sd == 'l':
                    t = 4 if x == x0 else 2 if x == x1 else 3
                else:
                    t = 2 if x == x1 or (k == 2 and x == x0) else 3
                if y < y0 + k:
                    t = min(t, 2)                           # under the shirt's hem
                L.put(x, y, R, t)
        if k == 2:
            ky = y0 + 10
            kx = x0 + 2
            L.rect(kx, ky, kx + 2, ky, R, 4)                 # knee: lit top, crease below
            L.rect(kx + 1, ky + 2, kx + 3, ky + 2, R, 2)
            if style == 'jeans':
                sx = x0 + 1 if sd == 'l' else x1 - 1
                L.rect(sx, y0 + 3, sx, y1 - 6, R, 2)         # outer seam
                L.rect(x0, y1 - 5, x1, y1 - 5, R, 4)         # rolled hem over the shoe
                L.rect(x0, y1 - 4, x1, y1 - 4, R, 2)


def p_feet(h, R=None, style='shoe'):
    """Shoes: lit toe cap, base upper, a dark sole row; k=2 adds laces, a welt, a heel shadow."""
    k = h.k
    R = R or h.m('shoes')
    for sd in 'lr':
        L = h.L('foot_' + sd)
        x0, y0, x1, y1 = h.b['foot_' + sd]
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                t = 3
                if y == y0:
                    t = 4
                if x == x1:
                    t = 2
                if y == y1:
                    t = 1
                L.put(x, y, R, t)
        if k == 2:
            if style == 'sneaker':
                L.rect(x0 + 1, y0, x1 - 1, y0, R, 5)
                L.put(x0 + 3, y0 + 1, R, 2)
                L.put(x0 + 5, y0 + 1, R, 2)
                L.rect(x0, y1, x1, y1, GREYC, 2)
                L.rect(x0, y1 - 1, x1, y1 - 1, R, 2)
            elif style == 'boot':
                L.rect(x0, y0, x1, y0, R, 4)
                L.put(x0 + 1, y0 + 1, R, 4)
                L.rect(x0, y1, x1, y1, R, 0)


# ------------------------------------------------------------------ held items
ITEMS = ('sword', 'pickaxe', 'axe', 'hoe', 'rod', 'book', 'torch', 'bow', 'staff', 'spear', 'scepter',
         'potion', 'map', 'hammer', 'cleaver', 'bag')
ITEM_MAT = {'iron': IRON, 'gold': GOLD, 'diamond': DIAMOND, 'wood': WOOD, 'stone': STONE}


def _stick(L, gx, gy, n, d, r, k, w=None, t_lit=4, t_mid=3, t_dark=2):
    """A diagonal handle from the grip (gx, gy) n px long toward d = +1 (up-right) / -1 (up-left): the pixel
    above each step is the lit edge; at k=2 a third row below is the shadow edge."""
    pts = []
    for i in range(n):
        x, y = gx + i * d, gy - i
        L.put(x, y, r, t_mid)
        pts.append((x, y))
        if k == 2:
            L.put(x, y - 1, r, t_lit)
    return pts


def draw_item(h, item, sd=None):
    """The held item in hand `sd`, drawn as its own part ('item') with its own outline. Diagonal tools
    point up and away from the body; the light stays top-left whichever way they point."""
    if not item:
        return
    k = h.k
    sd = sd or h.side
    L = h.L('item', own=True)
    hx0, hy0, hx1, hy1 = h.b['hand_' + sd]
    d = 1 if sd == 'r' else -1
    gx = (hx0 + hx1 + (1 if sd == 'r' else 0)) // 2
    gy = (hy0 + hy1) // 2 + (0 if k == 1 else 1)
    M = ITEM_MAT.get(h.held_mat or '', None)
    if item == 'sword':
        M = M or IRON
        _stick(L, gx - d * k, gy + k, 2 * k + 1, d, DLEATHER, k)       # grip through the fist
        L.put(gx - 2 * d * k, gy + 2 * k, GOLD, 3)                     # pommel
        if k == 2:
            L.put(gx - 2 * d * k - d, gy + 2 * k + 1, GOLD, 2)
            L.put(gx - 2 * d * k, gy + 2 * k + 1, GOLD, 2)
            L.put(gx - 2 * d * k - d, gy + 2 * k, GOLD, 4)
        cxg, cyg = gx + d * (k + 1), gy - k - 1                         # guard: across the blade
        for j in range(-k - 1, k + 2):                                 # perpendicular to the blade
            L.put(cxg + j, cyg + j * d, GOLD, 4 if j * d < 0 else 3)
        n = 6 if k == 1 else 13
        bx, by = cxg + d, cyg - 1
        for i in range(n):
            x, y = bx + i * d, by - i
            if k == 1:
                L.put(x, y, M, 3)
                L.put(x, y - 1, M, 5 if i < n - 1 else 4)
            else:                                      # per column: lit edge, core, lower bevel; a fuller
                fuller = 1 < i < n - 4                 # groove runs down the middle of the blade
                L.put(x, y - 1, M, 5)
                L.put(x, y, M, 2 if fuller else 3)
                L.put(x, y + 1, M, 3 if fuller else 2)
        tx, ty = bx + n * d, by - n
        L.put(tx, ty, M, 4)
        if k == 2:
            L.put(tx - d, ty, M, 4)
    elif item in ('pickaxe', 'axe', 'hoe', 'hammer'):
        M = M or IRON
        n = 7 if k == 1 else 14
        pts = _stick(L, gx - d * k, gy + 2 * k, n + 2 * k, d, WOOD, k)
        tx, ty = pts[-1]
        if item == 'pickaxe':
            if k == 1:
                for (x, y) in [(tx - 2, ty - 1), (tx - 1, ty - 2), (tx, ty - 2), (tx + 1, ty - 2), (tx + 2, ty - 1),
                               (tx - 3, ty), (tx + 3, ty)]:
                    L.put(x, y, M, 4 if y <= ty - 2 or x < tx else 3)
                L.put(tx, ty - 1, M, 2)
            else:
                arc = []
                for a in range(-7, 8):
                    yy = ty - 4 + int(round(a * a / 14.0))
                    arc.append((tx + a, yy))
                for (x, y) in arc:
                    L.put(x, y, M, 3)
                    L.put(x, y - 1, M, 5 if x < tx else 4)
                    L.put(x, y + 1, M, 2)
                for (x, y) in arc[:2] + arc[-2:]:
                    L.put(x, y + 2, M, 2)
                L.rect(tx - 1, ty - 4, tx + 1, ty - 1, DWOOD, 3)
                L.put(tx - 1, ty - 4, M, 4)
        elif item == 'axe':
            if k == 1:
                for (x, y, t) in ((0, -2, 4), (1, -2, 4), (1, -1, 3), (2, -1, 3), (1, 0, 2), (2, 0, 2), (2, -3, 4),
                                  (0, -1, 3)):
                    L.put(tx + x * d, ty + y, M, t)
            else:
                for j in range(-5, 3):
                    w = 5 - abs(j + 1) // 2
                    for i in range(1, w + 1):
                        L.put(tx + i * d, ty + j, M, 4 if j < -3 else 3 if i < w else 2)
                    L.put(tx + (w + 1) * d, ty + j, M, 5 if j < 0 else 4)
        elif item == 'hoe':
            if k == 1:
                for (x, y, t) in ((-1, -1, 4), (0, -1, 4), (1, -1, 3), (2, -1, 3), (2, 0, 2)):
                    L.put(tx + x * d, ty + y, M, t)
            else:
                for i in range(-2, 6):
                    L.put(tx + i * d, ty - 2, M, 5 if i < 2 else 4)
                    L.put(tx + i * d, ty - 1, M, 3)
                for j in range(0, 3):
                    L.put(tx + 5 * d, ty + j, M, 2)
                    L.put(tx + 4 * d, ty + j, M, 3)
        elif item == 'hammer':
            if k == 1:
                L.rect(tx - 1, ty - 2, tx + 1, ty - 1, M, 3)
                L.put(tx - 1, ty - 2, M, 4)
                L.put(tx + 1, ty - 1, M, 2)
            else:
                L.rect(tx - 3, ty - 5, tx + 3, ty - 1, M, 3)
                L.rect(tx - 3, ty - 5, tx + 3, ty - 5, M, 5)
                L.rect(tx - 3, ty - 4, tx - 3, ty - 1, M, 4)
                L.rect(tx + 3, ty - 4, tx + 3, ty - 1, M, 2)
                L.rect(tx - 2, ty - 1, tx + 3, ty - 1, M, 2)
    elif item == 'cleaver':                              # upright: a short handle, a wide blade outside it
        M = M or STEEL
        top = hy0 - 2 * k
        for y in range(top, gy + 2 * k):
            L.put(gx, y, DWOOD, 4 if k == 1 else 3)
            if k == 2:
                L.put(gx + 1, y, DWOOD, 2)
        bw, bh = (3, 5) if k == 1 else (7, 10)
        bx0 = gx if d > 0 else gx - bw + 1 + (k - 1)
        by0 = top - bh
        for y in range(by0, top + 1):
            for x in range(bx0, bx0 + bw + (k - 1)):
                t = 3
                if y == by0:
                    t = 4                                   # the spine on top
                if x == bx0:
                    t = 4 if y > by0 else 4
                if x == bx0 + bw + (k - 1) - 1:
                    t = 2
                if y == top:
                    t = 2
                L.put(x, y, M, t)
        edge = bx0 + bw + (k - 1) - 1 if d > 0 else bx0
        for y in range(by0 + 1, top):
            L.put(edge, y, M, 5 if d < 0 else 4)            # the sharpened edge catches the light
        L.put(bx0 + (bw + k - 1) // 2, by0 + k, M, 1)       # the hanging hole
    elif item == 'rod':
        n = 9 if k == 1 else 18
        pts = _stick(L, gx - d * k, gy + 2 * k, n, d, WOOD, k, t_mid=3)
        tx, ty = pts[-1]
        if k == 2:
            L.put(gx + d, gy - 1, DWOOD, 2)                  # reel
            L.put(gx + 2 * d, gy - 1, IRON, 4)
            L.put(gx + 2 * d, gy, IRON, 2)
        ln = 9 * k
        for j in range(1, ln):
            L.put(tx + d, ty + j, CREAM, 4 if j % 2 else 3, free=True)
        by = ty + ln
        L.put(tx + d, by, RED, 3)
        L.put(tx + d, by + k, CREAM, 4)
        if k == 2:
            L.put(tx + d + 1, by, RED, 2)
            L.put(tx + d + 1, by + 2, CREAM, 3)
            L.put(tx + d, by + 1, RED, 2)
            L.put(tx + d + 1, by + 1, RED, 1)
    elif item == 'book':
        cr = BOOKC
        bw, bh = (5, 6) if k == 1 else (10, 12)
        x0 = gx - bw // 2
        y0 = gy - bh // 2 - k
        for y in range(y0, y0 + bh):
            for x in range(x0, x0 + bw):
                t = 3
                if x == x0:
                    t = 4
                if y == y0:
                    t = 4
                if y == y0 + bh - 1:
                    t = 2
                L.put(x, y, cr, t)
        for y in range(y0 + 1, y0 + bh):                    # page edges on the right
            L.put(x0 + bw, y, PAPER, 3 if y % 2 else 2)
        if k == 2:
            L.rect(x0 + 1, y0 + 1, x0 + 1, y0 + bh - 2, cr, 2)   # spine crease
            L.rect(x0 + 4, y0 + 3, x0 + 7, y0 + 3, GOLD, 4)      # gold title bands
            L.rect(x0 + 4, y0 + 8, x0 + 7, y0 + 8, GOLD, 3)
            L.rect(x0 + 5, y0 + 5, x0 + 6, y0 + 6, GOLD, 3)
            L.put(x0 + 5, y0 + 5, GOLD, 5)
        else:
            L.put(x0 + 2, y0 + 2, GOLD, 4)
            L.put(x0 + 3, y0 + 2, GOLD, 3)
    elif item == 'torch':
        n = 6 if k == 1 else 12
        for j in range(n):
            y = gy + 2 * k - j
            L.put(gx, y, WOOD, 4 if k == 1 else 4)
            if k == 2:
                L.put(gx + 1, y, WOOD, 2)
        top = gy + 2 * k - n
        if k == 1:
            L.put(gx, top, GOLD, 2)
            L.put(gx, top - 1, FIRE, 4)
            L.put(gx, top - 2, LAMP, 4)
            L.put(gx - 1, top - 1, FIRE, 3)
            L.put(gx + 1, top - 1, FIRE, 2)
            L.put(gx, top - 3, FIRE, 3)
        else:
            L.rect(gx - 1, top, gx + 2, top + 1, DWOOD, 2)
            L.rect(gx - 1, top, gx + 2, top, DWOOD, 3)
            for (x, y, t, r) in ((0, -1, 4, FIRE), (1, -1, 3, FIRE), (-1, -1, 3, FIRE), (2, -1, 2, FIRE),
                                 (0, -2, 5, LAMP), (1, -2, 4, LAMP), (-1, -2, 3, FIRE), (2, -2, 3, FIRE),
                                 (0, -3, 4, LAMP), (1, -3, 4, FIRE), (-1, -3, 3, FIRE), (0, -4, 4, FIRE),
                                 (1, -4, 3, FIRE), (0, -5, 3, FIRE), (1, -6, 2, FIRE)):
                L.put(gx + x, top + y, r, t)
    elif item == 'bow':
        hgt = 7 if k == 1 else 15
        bulge = 2 * k
        pts = []
        for j in range(-hgt, hgt + 1):
            u = j / hgt
            off = round(bulge * (1 - u * u))
            pts.append((gx + d * off - d * bulge + d * k, gy + j))
        for (x, y) in pts:
            L.put(x, y, WOOD, 3 if y < gy else 2)
            if k == 2:
                L.put(x + d, y, WOOD, 2 if d > 0 else 4)
                L.put(x - d, y, WOOD, 4 if d > 0 else 2)
        sx = pts[0][0]
        for j in range(-hgt + 1, hgt):
            if (sx, gy + j) not in L.px:
                L.put(sx, gy + j, CREAM, 4, free=True)
        for (x, y) in (pts[0], pts[-1]):
            L.put(x, y, DWOOD, 3)
        if k == 2:
            L.rect(pts[hgt][0] - 1, gy - 2, pts[hgt][0] + 1, gy + 2, DLEATHER, 3)
    elif item in ('staff', 'spear', 'scepter'):
        top = gy - (20 * k if item != 'scepter' else 8 * k)
        bot = gy + (8 * k if item != 'scepter' else 2 * k)
        r = WOOD if item != 'scepter' else GOLD
        for y in range(top, bot):
            if k == 1:
                L.put(gx, y, r, 4 if y < top + 3 and item != 'scepter' else 3)
            else:
                L.put(gx, y, r, 4)
                L.put(gx + 1, y, r, 2)
                if item == 'staff' and y % 6 == 0:
                    L.put(gx, y, r, 3)
        if item == 'staff':
            G = h.look.get('gem') or AMETHYST
            cy = top - 2 * k
            if k == 1:
                L.put(gx - 1, top, r, 3)
                L.put(gx + 1, top, r, 2)
                L.rect(gx - 1, cy - 1, gx + 1, cy + 1, G, 3)
                L.put(gx - 1, cy - 1, G, 5)
                L.put(gx + 1, cy + 1, G, 2)
            else:
                for (x, y) in ((-2, 0), (-2, -1), (3, 0), (3, -1), (-1, 1), (2, 1)):
                    L.put(gx + x, top + y, r, 3 if x < 0 else 2)
                for (x, y) in ell(gx + 1, cy - 1, 3.2, 3.2):
                    nx, ny = (x + 0.5 - gx - 1) / 3.2, (y + 0.5 - cy + 1) / 3.2
                    lam = -0.6 * nx - 0.7 * ny
                    L.put(x, y, G, 5 if lam > 0.7 else 4 if lam > 0.25 else 3 if lam > -0.3 else 2)
                L.put(gx, cy - 2, CREAM, 5)
            fx_spark(h, gx + 4 * k, cy - 3 * k)
        elif item == 'spear':
            M = M or IRON
            if k == 1:
                L.put(gx, top - 1, M, 4)
                L.put(gx, top - 2, M, 5)
                L.put(gx - 1, top, M, 4)
                L.put(gx + 1, top, M, 2)
                L.put(gx, top - 3, M, 4)
            else:
                for j in range(8):
                    w = min(j, 7 - j, 2) if j > 0 else 0
                    for i in range(-w, w + 2):
                        L.put(gx + i, top - 1 - j, M, 5 if i <= 0 and j > 2 else 4 if i <= 0 else 2)
                L.rect(gx - 1, top, gx + 2, top + 1, GOLD, 3)
                L.rect(gx - 1, top, gx + 2, top, GOLD, 4)
        else:
            G = RUBY
            if k == 1:
                L.put(gx, top - 1, G, 4)
                L.put(gx - 1, top, GOLD, 4)
                L.put(gx + 1, top, GOLD, 2)
            else:
                L.rect(gx - 2, top, gx + 3, top + 1, GOLD, 3)
                L.rect(gx - 2, top, gx + 3, top, GOLD, 5)
                L.rect(gx - 1, top - 3, gx + 2, top - 1, G, 3)
                L.put(gx - 1, top - 3, G, 5)
                L.put(gx, top - 3, G, 4)
                L.rect(gx + 2, top - 2, gx + 2, top - 1, G, 2)
                L.rect(gx, top - 5, gx + 1, top - 4, GOLD, 4)
    elif item == 'potion':
        G = h.look.get('potion') or POTION_P
        if k == 1:                                         # held by its base: the flask shows above the fist
            x0, y0 = gx - 1, hy0 - 4
            L.put(x0 + 1, y0, CREAM, 2)
            L.put(x0 + 1, y0 + 1, GLASS, 4)
            L.rect(x0, y0 + 2, x0 + 2, y0 + 4, G, 3)
            L.put(x0, y0 + 2, GLASS, 5)
            L.put(x0 + 2, y0 + 4, G, 2)
        else:
            x0, y0 = gx - 3, hy0 - 9
            L.rect(x0 + 2, y0, x0 + 4, y0 + 1, DWOOD, 3)
            L.put(x0 + 2, y0, DWOOD, 4)
            L.rect(x0 + 2, y0 + 2, x0 + 4, y0 + 3, GLASS, 3)
            L.put(x0 + 2, y0 + 2, GLASS, 5)
            for (x, y) in ell(x0 + 3.5, y0 + 7.5, 3.6, 3.4):
                nx, ny = (x + 0.5 - x0 - 3.5) / 3.6, (y + 0.5 - y0 - 7.5) / 3.4
                lam = -0.6 * nx - 0.7 * ny
                if y <= y0 + 5:
                    L.put(x, y, GLASS, 4 if lam > 0.2 else 3)
                else:
                    L.put(x, y, G, 4 if lam > 0.5 else 3 if lam > -0.2 else 2)
            L.put(x0 + 1, y0 + 6, CREAM, 5)
            L.put(x0 + 4, y0 + 8, G, 5)
    elif item == 'map':
        if k == 1:
            x0, y0 = gx - 2, gy - 3
            L.rect(x0, y0, x0 + 4, y0 + 4, PAPER, 3)
            L.rect(x0, y0, x0 + 4, y0, PAPER, 4)
            L.put(x0 + 1, y0 + 2, RED, 3)
            L.put(x0 + 2, y0 + 2, RED, 3)
            L.put(x0 + 3, y0 + 3, BLUE, 3)
            L.rect(x0 + 4, y0 + 1, x0 + 4, y0 + 4, PAPER, 2)
        else:
            x0, y0 = gx - 5, gy - 7
            L.rect(x0, y0, x0 + 10, y0 + 9, PAPER, 3)
            L.rect(x0, y0, x0 + 10, y0, PAPER, 5)
            L.rect(x0 + 10, y0 + 1, x0 + 10, y0 + 9, PAPER, 2)
            L.rect(x0, y0 + 9, x0 + 10, y0 + 9, PAPER, 2)
            for (x, y) in ((2, 3), (3, 3), (4, 4), (5, 4), (6, 5)):
                L.put(x0 + x, y0 + y, RED, 3)
            L.rect(x0 + 6, y0 + 2, x0 + 8, y0 + 3, GREEN, 3)
            L.rect(x0 + 2, y0 + 6, x0 + 4, y0 + 7, BLUE, 3)
            L.put(x0 + 7, y0 + 6, RED, 2)
            L.put(x0 + 8, y0 + 7, RED, 2)
            L.put(x0 + 7, y0 + 7, RED, 4)
            L.put(x0 + 8, y0 + 6, RED, 4)
    elif item == 'bag':
        G = h.look.get('bag') or LEATHER                   # a coin pouch hanging from the fist
        if k == 1:
            x0, y0 = gx - 2, hy1
            L.rect(x0, y0, x0 + 3, y0 + 3, G, 3)
            L.rect(x0, y0, x0 + 3, y0, G, 4)
            L.rect(x0 + 3, y0 + 1, x0 + 3, y0 + 3, G, 2)
            L.put(x0 + 1, y0 + 2, GOLD, 4)
            L.put(x0 + 2, y0 + 2, GOLD, 3)
        else:
            x0, y0 = gx - 4, hy1 - 2
            for (x, y) in ell(x0 + 4, y0 + 6, 4.6, 4.2):
                nx, ny = (x + 0.5 - x0 - 4) / 4.6, (y + 0.5 - y0 - 6) / 4.2
                lam = -0.6 * nx - 0.7 * ny
                L.put(x, y, G, 4 if lam > 0.45 else 3 if lam > -0.25 else 2)
            L.rect(x0 + 2, y0 + 1, x0 + 6, y0 + 2, G, 2)
            L.rect(x0 + 1, y0 + 2, x0 + 7, y0 + 2, GOLD, 3)
            L.put(x0 + 4, y0 + 6, GOLD, 5)
            L.put(x0 + 5, y0 + 6, GOLD, 3)
            L.put(x0 + 4, y0 + 7, GOLD, 3)


def fx_spark(h, x, y, r=None):
    """A small four-armed sparkle (glint) - free pixels, no outline."""
    k = h.k
    r = r or SPARK
    L = h.L('fx', line=False)
    L.put(x, y, r, 5, free=True)
    if k == 2:
        for dx, dy in N4:
            L.put(x + dx, y + dy, r, 3, free=True)


# ------------------------------------------------------------------ villagers
def p_villager_head(h, bald=True):
    """The villager's tall head: a lit bald crown (k=2: a highlight patch on the top-left), lit left column,
    darker right column and chin."""
    k = h.k
    S = h.m('skin')
    L = h.L('head')
    x0, y0, x1, y1 = h.b['head']
    box(L, (x0, y0, x1, y1), S, left=4, right=2, top=4 if bald else None, bottom=2)
    if k == 2:
        L.rect(x1 - 1, y0 + 2, x1 - 1, y1 - 1, S, 3)
        L.rect(x0 + 1, y1 - 1, x1 - 1, y1 - 1, S, 2)
        if bald:
            L.rect(x0 + 2, y0 + 1, x0 + 5, y0 + 1, S, 5)
            L.rect(x0 + 1, y0 + 2, x0 + 3, y0 + 2, S, 5)
            L.rect(x0 + 1, y0 + 1, x0 + 1, y0 + 1, S, 4)
    if h.facing == 'right':
        L.rect(x0, y0 + k, x0 + k - 1, y1, S, 4)
    elif h.facing == 'left':
        L.rect(x1 - k + 1, y0 + k, x1, y1, S, 2)


def p_villager_face(h, brow=True, eyes=True, mouth=True, wrinkles=True):
    """Unibrow, deep-set eyes, the big nose: a box sticking out of the face - lit left side, base front,
    shadow side and underside, nostrils, and its cast shadow on the cheek to the right."""
    k = h.k
    S = h.m('skin')
    B = h.m('hair')
    iris = h.m('eye')
    L = h.L('face')
    x0, y0, x1, y1 = h.b['head']
    f = h.fs
    cx = (x0 + x1 + 1) // 2 + f
    if k == 1:
        ey = y0 + 4
        if brow:
            L.rect(cx - 3, ey - 1, cx + 2, ey - 1, B, 1)
            L.put(cx - 1, ey - 1, B, 2)
            L.put(cx, ey - 1, B, 2)
        if eyes:
            eye(L, cx - 3, ey, 1, iris, 'l')
            eye(L, cx + 1, ey, 1, iris, 'r')
        for y in range(ey, ey + 4):                         # the nose: 2 wide, 4 long
            L.put(cx - 1, y, S, 4 if y < ey + 3 else 2)
            L.put(cx, y, S, 3 if y < ey + 3 else 1)
        L.put(cx + 1, ey + 1, S, 2)                         # its shadow on the right cheek
        L.put(cx + 1, ey + 2, S, 2)
        if mouth:
            L.put(cx - 2, ey + 4, S, 2)
            L.put(cx + 1, ey + 4, S, 2)
        return
    ey = y0 + 8
    if brow:
        for x in range(cx - 7, cx + 7):
            t = 1 if x not in (cx - 1, cx) else 2
            L.put(x, ey - 2, B, t)
            if cx - 6 <= x <= cx + 5 and x not in (cx - 1, cx):
                L.put(x, ey - 1, B, 2 if x < cx else 1)
        L.rect(cx - 6, ey - 3, cx - 3, ey - 3, B, 2)          # bushy top on the lit side
        L.rect(cx + 2, ey - 3, cx + 4, ey - 3, B, 1)
    if eyes:
        for x in range(cx - 6, cx - 2):                     # sockets: shadow under the brow
            L.put(x, ey, S, 2)
        for x in range(cx + 2, cx + 6):
            L.put(x, ey, S, 2)
        eye(L, cx - 6, ey, 2, iris, 'l')
        eye(L, cx + 3, ey, 2, iris, 'r')
        if wrinkles:
            L.put(cx - 7, ey + 2, S, 2)
            L.put(cx + 6, ey + 2, S, 2)
            L.rect(cx - 5, ey + 3, cx - 4, ey + 3, S, 2)      # bags under the eyes
            L.rect(cx + 3, ey + 3, cx + 4, ey + 3, S, 2)
    ny0, ny1 = ey - 1, ey + 8                               # nose 4 wide, 10 long
    for y in range(ny0, ny1 + 1):
        for i, x in enumerate(range(cx - 2, cx + 2)):
            t = (4, 3, 3, 2)[i]
            if y >= ny1 - 1:
                t = (2, 2, 1, 1)[i] if y == ny1 else (3, 3, 2, 2)[i]
            L.put(x, y, S, t)
    L.put(cx - 2, ny0 + 3, S, 5)                            # glint on the bridge
    L.put(cx - 2, ny0 + 4, S, 5)
    L.put(cx - 1, ny1 - 2, S, 4)                            # lit tip
    L.put(cx - 2, ny1, S, 0)                                # nostrils
    L.put(cx + 1, ny1, S, 0)
    for y in range(ny0 + 2, ny1 + 1):                       # cast shadow on the right cheek
        L.put(cx + 2, y, S, 2)
    L.put(cx + 3, ny1, S, 2)
    if mouth:
        L.rect(cx - 2, ny1 + 2, cx + 1, ny1 + 2, S, 1)
        L.put(cx - 3, ny1 + 1, S, 2)
        L.put(cx + 2, ny1 + 1, S, 2)
    if wrinkles:
        L.put(cx - 4, ny1 - 1, S, 2)                        # lines from the nose to the mouth
        L.put(cx - 4, ny1, S, 2)
        L.put(cx + 3, ny1 - 1, S, 2)


def p_robe(h, R=None, flare=True, folds=True, collar=True, hem=None):
    """The villager robe: torso and a skirt down to the ankles, flaring one step at the bottom; vertical
    folds (dark-mid lines with a light-mid lip on their lit side), the head's shadow round the neck, the
    crossed arms' cast shadow under them, a darker hem; feet show under it."""
    k = h.k
    R = R or h.m('top')
    L = h.L('torso')
    x0, y0, x1, y1 = h.b['torso']
    g = h.body.ground
    bot = g - 3 * k
    fy = y1 + 1 + 4 * k                                     # where the skirt flares
    pts = {}
    for y in range(y0, bot):
        e = k if flare and y >= fy else 0
        for x in range(x0 - e, x1 + e + 1):
            t = 3
            if x == x0 - e:
                t = 4
            if x == x1 + e:
                t = 2
            if k == 2 and x == x1 + e - 1:
                t = 2
            pts[(x, y)] = t
    for (x, y), t in pts.items():
        L.put(x, y, R, t)
    cx = (x0 + x1 + 1) // 2
    L.rect(cx - 2 * k, y0, cx + 2 * k - 1, y0 + k - 1, R, 1)   # under the chin
    if k == 2:
        L.rect(cx - 5, y0, cx + 4, y0, R, 2)
    if flare:
        L.rect(x0 - k, fy, x0 - 1, fy, R, 4)                # the step of the flare catches light
        L.rect(x1 + 1, fy, x1 + k, fy, R, 2)
    if folds:
        for fx_ in ((x0 + 2 * k, x1 - 2 * k + 1) if k == 1 else (x0 + 3, x0 + 8, x1 - 3)):
            top = y1 + 1 if k == 1 else y1 - 2
            for y in range(top, bot - k):
                L.put(fx_, y, R, 2)
                if k == 2 and fx_ < cx:
                    L.put(fx_ - 1, y, R, 4)
            L.put(fx_, bot - k, R, 2)
    for x in range(x0 - (k if flare else 0), x1 + (k if flare else 0) + 1):    # hem
        L.put(x, bot - 1, R, 2 if x > x0 else 3)
        if k == 2:
            L.put(x, bot - 2, R, 3 if x < cx else 2)
    if hem:
        for x in range(x0 - (k if flare else 0), x1 + (k if flare else 0) + 1):
            for j in range(k):
                L.put(x, bot - 1 - j, hem, 3 if x < cx else 2)
    if collar and k == 2:
        L.rect(cx - 3, y0 + 1, cx + 2, y0 + 1, R, 1)
        L.put(cx - 4, y0 + 1, R, 2)
        L.put(cx + 3, y0 + 1, R, 2)
        L.rect(cx - 1, y0 + 2, cx, y0 + 3, R, 2)
    if h.body.arm_mode['l'] == 'cross':
        ay = y0 + 9 * k                                     # shadow under the crossed arms
        L.rect(x0, ay, x1, ay + k - 1, R, 2)


def p_villager_legs(h, R=None, S=None):
    """What shows under the robe: dark trousers and shoes."""
    k = h.k
    R = R or DLEATHER
    S = S or h.m('shoes')
    g = h.body.ground
    for sd in 'lr':
        L = h.L('leg_' + sd)
        x0, y0, x1, y1 = h.b['leg_' + sd]
        for y in range(g - 6 * k, y1 + 1):
            for x in range(x0, x1 + 1):
                L.put(x, y, R, 2 if x == x1 or (sd == 'r' and x == x0) else 3)
        F = h.L('foot_' + sd)
        fx0, fy0, fx1, fy1 = h.b['foot_' + sd]
        for y in range(fy0, fy1 + 1):
            for x in range(fx0, fx1 + 1):
                F.put(x, y, S, 1 if y == fy1 else 4 if y == fy0 and x < fx1 else 2 if x == fx1 else 3)
        if k == 2:
            F.put(fx0 + 1, fy0, S, 5)


def p_cross_arms(h, R=None, S=None, cuff=None):
    """Crossed arms (villager idle): upper arms hang beside the robe, the folded forearms make a block in
    front of the chest with the hands tucked in the middle; the block's top face is lit, its underside dark,
    and it gets its own outline so it separates from the robe."""
    k = h.k
    R = R or h.m('top')
    S = S or h.m('skin')
    cuff = cuff or R
    L = h.L('arms', own=True)
    x0, y0, x1, y1 = h.b['torso']
    aw = 4 * k
    for sd in 'lr':
        ax0 = x0 - aw if sd == 'l' else x1 + 1
        for y in range(y0, y0 + 7 * k):
            for x in range(ax0, ax0 + aw):
                t = 3
                if x == ax0:
                    t = 4 if sd == 'l' else 3
                if x == ax0 + aw - 1:
                    t = 3 if sd == 'l' else 2
                if y < y0 + k:
                    t = 4 if sd == 'l' else 3
                L.put(x, y, R, t)
    by0, by1 = y0 + 5 * k, y0 + 9 * k - 1                   # the folded forearms
    bx0, bx1 = x0 - aw, x1 + aw
    for y in range(by0, by1 + 1):
        for x in range(bx0, bx1 + 1):
            t = 3
            if y == by0:
                t = 4
            if y == by1:
                t = 2
            if x == bx0:
                t = 4
            if x == bx1:
                t = 2
            L.put(x, y, R, t)
    cx = (x0 + x1 + 1) // 2
    hx0, hx1 = cx - 2 * k, cx + 2 * k - 1                   # hands in the middle
    for y in range(by0 + k, by1 + 1):
        for x in range(hx0, hx1 + 1):
            t = 3 if y < by1 else 2
            if x == hx0:
                t = 4 if y < by1 else 3
            L.put(x, y, S, t)
    L.put(hx0 - 1, by0 + k, cuff, 2)
    L.put(hx1 + 1, by0 + k, cuff, 2)
    for y in range(by0, by1 + 1):                           # cuffs
        L.put(hx0 - 1, y, cuff, 2 if y > by0 else 3)
        L.put(hx1 + 1, y, cuff, 2 if y > by0 else 3)
    if k == 2:
        L.put(cx, by0 + 3, S, 2)                            # the two fists meet
        L.put(cx - 1, by0 + 3, S, 2)
        L.put(cx, by0 + 4, S, 2)
        L.put(hx0 + 1, by0 + 2, S, 4)
        for x in (hx0 - 2, hx1 + 2):
            for y in range(by0 + 1, by1):
                L.put(x, y, cuff, 4 if x < cx else 3)
        for i in range(3):                                  # one crease per sleeve, running to the hands
            L.put(bx0 + 3 + i, by0 + 1 + i, R, 2)
            L.put(bx0 + 4 + i, by0 + 1 + i, R, 4) if i < 2 else None
            L.put(bx1 - 3 - i, by0 + 1 + i, R, 2)


def brim_hat(h, R, brim=2, crown_h=3, brim_y=1, crown_in=0, band=None, weave=False, droop=0, slope=False):
    """A hat with a brim: the crown on the head top (lit left, darker right, band at its foot), the brim
    across the head (lit top, dark underside, ends drooping `droop` px) and its cast shadow on the face.
    Units are k (skin px)."""
    k = h.k
    S = h.m('skin')
    L = h.L('hat')
    x0, y0, x1, y1 = h.b['head']
    by = y0 + brim_y * k                                    # brim row(s)
    cx0, cx1 = x0 + crown_in * k, x1 - crown_in * k
    ct = by - crown_h * k
    for y in range(ct, by):
        for x in range(cx0, cx1 + 1):
            t = 3
            if x == cx0:
                t = 4
            if x >= cx1 - (k - 1):
                t = 2
            if y == ct:
                t = 4 if x < cx1 - k else 3
            if weave and k == 2 and (x + (y // 2) * 2) % 4 == 0 and cx0 < x < cx1 - 1 and y > ct:
                t = 2
            elif weave and k == 1 and (x + y) % 3 == 0 and cx0 < x < cx1 and y > ct:
                t = 2
            L.put(x, y, R, t)
    if band:
        for x in range(cx0, cx1 + 1):
            for j in range(k):
                L.put(x, by - 1 - j, band, 4 if x == cx0 else 2 if x == cx1 else 3)
    bx0, bx1 = x0 - brim * k, x1 + brim * k
    for x in range(bx0, bx1 + 1):
        dd = 0
        if droop and (x < x0 or x > x1):
            dd = droop * k if (x < x0 - (brim - 1) * k or x > x1 + (brim - 1) * k) else 0
        for j in range(k):
            y = by + j + dd
            t = 4 if j == 0 else 2
            if k == 1:
                t = 4 if x < (x0 + x1) // 2 + 2 else 3
            if weave and k == 2 and j == 0 and x % 3 == 0:
                t = 3
            L.put(x, y, R, t)
        if k == 2 or True:
            L.put(x, by + k + dd, R, 1 if k == 1 and False else (2 if k == 1 else 1))
    face = h.fig.layers.get('face')
    for x in range(x0, x1 + 1):                             # the brim's shadow on the forehead
        if k == 2 and not (face and (x, by + k + 1) in face.px):
            L.put(x, by + k + 1, S, 2)


def apron(h, R, top=4, straps=True, pocket=True, stains=None, rivets=False, wheat=False, bib=True):
    """An apron over the robe: a bib on the chest (straps to the shoulders), a skirt panel down to just
    above the hem; lit left edge, dark right edge, a pocket with a shadowed opening; stains are 2-3 px
    clusters; rivets lit top-left."""
    k = h.k
    L = h.L('chest')
    x0, y0, x1, y1 = h.b['torso']
    bot = h.body.ground - 4 * k
    ax0, ax1 = x0 + k, x1 - k
    yt = y0 + top * k
    for y in range(yt if bib else y1 + 1 - 2 * k, bot + 1):
        for x in range(ax0, ax1 + 1):
            t = 3
            if x == ax0:
                t = 4
            if x == ax1:
                t = 2
            if y == bot:
                t = 2
            L.put(x, y, R, t)
    if straps and bib:
        for y in range(y0, yt):
            L.put(ax0, y, R, 4)
            L.put(ax1, y, R, 2)
            if k == 2:
                L.put(ax0 + 1, y, R, 3)
                L.put(ax1 - 1, y, R, 2)
    if k == 2:
        L.rect(ax0, y1 - 1, ax1, y1 - 1, R, 2)               # waist tie
        L.rect(ax0 + 1, y1, ax1 - 1, y1, R, 4)
    if pocket:
        py = y1 + 3 * k
        px0, px1 = ax0 + k, ax1 - k
        L.rect(px0, py, px1, py, R, 1 if k == 1 else 1)
        if k == 2:
            L.rect(px0, py + 1, px1, py + 1, R, 2)
            for y in range(py, py + 6):
                L.put(px0, y, R, 4)
                L.put(px1, y, R, 2)
            L.rect(px0, py + 6, px1, py + 6, R, 2)
            L.rect(px0 + 2, py - 1, px1 - 2, py - 1, R, 4)
    if rivets:
        for (x, y) in ((ax0, yt), (ax1, yt), (ax0, y1 + k), (ax1, y1 + k)):
            L.put(x, y, IRON, 4 if x == ax0 else 3)
    if stains:
        rnd = random.Random(5 + k)
        for (dx, dy, n) in ((2, 6, 3), (5, 13, 2), (3, 17, 2), (6, 9, 2)):
            x, y = ax0 + dx * k // (2 if k == 1 else 1), yt + dy * k // 2
            if k == 1:
                x, y = ax0 + (dx % 5), yt + dy // 2
            pts = [(x, y), (x + 1, y), (x, y + 1)][:n]
            for q in pts:
                if q in L.px:
                    L.put(*q, stains, 3 if q == pts[0] else 2)
            rnd.random()
    if wheat and k == 2:
        wx = ax0 + 3
        wy = y1 + 3 * k
        for j in range(1, 7):
            L.put(wx + (j > 4), wy - j, STRAW, 3 if j < 5 else 4)
        for (x, y) in ((wx, wy - 8), (wx + 1, wy - 9), (wx + 1, wy - 7), (wx + 2, wy - 8)):
            L.put(x, y, STRAW, 4 if x == wx else 3)
        L.put(wx - 1, wy - 7, STRAW, 5)


def goggles(h, strap=DLEATHER, rim=IRON, lens=None):
    """Work goggles pushed up on the forehead: a leather strap round the head, two lenses with iron rims and
    a glint at the top-left."""
    k = h.k
    lens = lens or LENS
    L = h.L('hat')
    x0, y0, x1, y1 = h.b['head']
    sy = y0 + 2 * k
    for x in range(x0, x1 + 1):
        for j in range(k):
            L.put(x, sy + j, strap, 3 if j == 0 else 2)
    cx = (x0 + x1 + 1) // 2
    for c in (cx - 2 * k - (1 if k == 1 else 1), cx + (1 if k == 1 else 1)):
        if k == 1:
            L.rect(c - 1 + 1, sy - 1, c + 1, sy, rim, 3)
            L.put(c + (0 if c < cx else 1), sy, lens, 3)
            L.put(c, sy - 1, rim, 4)
        else:
            for (x, y) in ell(c + 1.5, sy + 0.5, 2.7, 2.4):
                L.put(x, y, rim, 4 if x < c + 1 and y < sy else 3 if x < c + 3 else 2)
            for (x, y) in ell(c + 1.5, sy + 0.5, 1.6, 1.4):
                L.put(x, y, lens, 3 if x > c + 1 or y > sy else 4)
            L.put(c + 1, sy, CREAM, 5)


def headband(h, R, knot=True):
    k = h.k
    L = h.L('hat')
    x0, y0, x1, y1 = h.b['head']
    y = y0 + 2 * k
    for x in range(x0, x1 + 1):
        for j in range(k):
            L.put(x, y + j, R, (4 if x < (x0 + x1) // 2 else 3) if j == 0 else 2)
    if knot:
        kx = x1 + 1
        L.put(kx, y, R, 3)
        L.put(kx, y + k, R, 2)
        L.put(kx + 1, y + k + (1 if k == 2 else 0), R, 2)
        if k == 2:
            L.put(kx, y + 1, R, 2)
            L.put(kx + 1, y + 2, R, 2)
            L.put(kx + 1, y + 4, R, 1)
            L.put(kx + 2, y + 5, R, 1)


def skullcap(h, R, rim=None, button=None, rows=3):
    k = h.k
    L = h.L('hat')
    x0, y0, x1, y1 = h.b['head']
    for y in range(y0 - k, y0 + rows * k - k):
        for x in range(x0 + (k if y < y0 else 0), x1 + 1 - (k if y < y0 else 0)):
            t = 4 if y < y0 and x < x1 - 2 * k else 3
            if x == x1 or (y < y0 and x == x1 - k):
                t = 2
            if x == x0 and y >= y0:
                t = 4
            L.put(x, y, R, t)
    if rim:
        y = y0 + rows * k - k
        for x in range(x0, x1 + 1):
            for j in range(k):
                L.put(x, y + j, rim, (4 if x < x1 - k else 3) if j == 0 else 2)
    if button:
        cx = (x0 + x1 + 1) // 2
        L.put(cx - 1, y0 - k - 1, button, 4)
        if k == 2:
            L.put(cx, y0 - k - 1, button, 3)
            L.put(cx - 1, y0 - k - 2, button, 5)
            L.put(cx, y0 - k - 2, button, 3)


def glasses(h, R=GOLD, villager=True):
    """Round reading glasses: a rim round each eye, a bridge over the nose, lenses as a light glass tone with
    a glint."""
    k = h.k
    L = h.L('acc')
    x0, y0, x1, y1 = h.b['head']
    cx = (x0 + x1 + 1) // 2 + h.fs
    if k == 1:                                              # browline frames: the rim replaces the brow
        ey = y0 + 4
        for x in (cx - 3, cx - 2, cx + 1, cx + 2):
            L.put(x, ey - 1, R, 4 if x < cx else 3)
        L.put(cx - 4, ey, R, 3)
        L.put(cx + 3, ey, R, 2)
        return
    ey = y0 + 8
    for ox in (cx - 7, cx + 2):
        ring = {(x, y) for x in range(ox, ox + 6) for y in range(ey - 1, ey + 4)}
        inner = {(x, y) for x in range(ox + 1, ox + 5) for y in range(ey, ey + 3)}
        for (x, y) in ring - inner:
            if (x in (ox, ox + 5)) and (y in (ey - 1, ey + 3)):
                continue
            L.put(x, y, R, 4 if (y == ey - 1 or x == ox) else 2)
    L.rect(cx - 1, ey, cx, ey, R, 3)
    L.put(cx - 7 + 1, ey, GLASS, 5)
    L.put(cx + 3, ey, GLASS, 5)


def monocle(h, R=GOLD):
    k = h.k
    L = h.L('acc')
    x0, y0, x1, y1 = h.b['head']
    cx = (x0 + x1 + 1) // 2 + h.fs
    if k == 1:
        ey = y0 + 4
        L.put(cx + 3, ey, R, 2)
        L.put(cx + 1, ey - 1, R, 4)
        L.put(cx + 2, ey - 1, R, 3)
        L.put(cx + 3, ey + 1, R, 2)
        L.put(cx + 3, ey + 2, R, 2)
        return
    ey = y0 + 8
    ox = cx + 2
    for (x, y) in ell(ox + 2.5, ey + 1.5, 3.4, 3.0) - ell(ox + 2.5, ey + 1.5, 2.2, 1.9):
        L.put(x, y, R, 4 if x < ox + 2 and y < ey + 1 else 3 if y < ey + 2 else 2)
    L.put(ox + 2, ey, GLASS, 5)
    for j in range(1, 9):                                   # the chain down to the collar
        L.put(ox + 5 + (j > 4), ey + 3 + j, R, 3 if j % 2 else 2)


def souwester(h, R=None):
    """A fisherman's rain hat: a rounded crown as wide as the head, a band at its foot, a brim that turns
    down at the sides, its dark underside, stitches round the crown (k=2)."""
    R = R or YELLOW
    k = h.k
    L = h.L('hat')
    x0, y0, x1, y1 = h.b['head']
    ct = y0 - 3 * k
    for y in range(ct, y0 + k):
        inset = k if y < ct + k else 0
        for x in range(x0 + inset, x1 + 1 - inset):
            t = 3
            if x == x0 + inset:
                t = 4
            if x >= x1 - inset - (k - 1):
                t = 2
            if y == ct:
                t = 4 if x < x1 - 2 * k else 3
            L.put(x, y, R, t)
    for x in range(x0, x1 + 1):                             # band
        L.put(x, y0, R, 2 if x > x0 else 3)
    by = y0 + k
    for x in range(x0 - 2 * k, x1 + 2 * k + 1):           # brim, turned down at the sides
        out = x < x0 - k or x > x1 + k
        y = by + (k if out else 0)
        for j in range(k):
            L.put(x, y + j, R, (4 if x < (x0 + x1) // 2 else 3) if j == 0 else 2)
        L.put(x, y + k, R, 1)
        if out:
            for j in range(k):
                L.put(x, by + j, R, 4 if x < x0 else 3)
    if k == 2:
        for x in range(x0 + 1, x1, 2):
            L.put(x, ct + 4, R, 2)                          # stitches round the crown
        L.rect(x0 + 2, ct + 1, x0 + 4, ct + 1, R, 5)


def hood(h, R, trim=None, up=True):
    """A hood up round the face (and a short cape on the shoulders): cloth round the head, the face opening
    in shadow at its top, a trim along the edge."""
    k = h.k
    L = h.L('hat')
    x0, y0, x1, y1 = h.b['head']
    hy0 = y0 - k
    pts = {}
    for y in range(hy0, y1 + 1):
        for x in range(x0 - k, x1 + k + 1):
            if y == hy0 and (x < x0 or x > x1):
                continue
            opening = x0 + k <= x <= x1 - k and y >= y0 + 2 * k
            if opening:
                continue
            t = 3
            if x <= x0 - k + (k - 1):
                t = 4
            if x >= x1 + k - (k - 1):
                t = 2
            if y == hy0:
                t = 4 if x < x1 - k else 3
            pts[(x, y)] = t
    for p, t in pts.items():
        L.put(*p, R, t)
    for x in range(x0 + k, x1 - k + 1):                     # the opening's top edge in shadow
        L.put(x, y0 + 2 * k, h.m('skin'), 1)
        if k == 2:
            L.put(x, y0 + 5, h.m('skin'), 2)
    if trim:
        for y in range(y0 + 2 * k, y1 + 1):
            for j in range(k):
                L.put(x0 + j, y, trim, 4 if j == 0 else 3)
                L.put(x1 - j, y, trim, 2 if j == 0 else 3)
        for x in range(x0 + k, x1 - k + 1):
            for j in range(k):
                L.put(x, y0 + k + j, trim, 4 if j == 0 and x < (x0 + x1) // 2 else 3)
    cy = y1 + 1                                              # the short cape on the shoulders
    C = h.L('cape')
    tx0, ty0, tx1, ty1 = h.b['torso']
    for y in range(cy, cy + 3 * k):
        w = 4 * k - (y - cy) // 2
        for x in range(tx0 - w, tx1 + w + 1):
            C.put(x, y, R, 4 if x < tx0 - w + k else 2 if x > tx1 + w - k else 3)


def center_band(h, R, w=2, start=0):
    """A trim running down the front of the robe (cleric, merchant): lit left half, darker right half."""
    k = h.k
    L = h.L('chest')
    x0, y0, x1, y1 = h.b['torso']
    cx = (x0 + x1 + 1) // 2
    bot = h.body.ground - 3 * k
    for y in range(y0 + start * k, bot):
        for x in range(cx - w * k // 2, cx + w * k // 2):
            L.put(x, y, R, 4 if x < cx else 3)
        if k == 2 and (y - y0) % 6 == 3:
            L.put(cx - 1, y, R, 5)


def rope_belt(h, R=STRAW, y=None):
    k = h.k
    L = h.L('belt')
    x0, y0, x1, y1 = h.b['torso']
    y = y if y is not None else y1 - k + 1
    for x in range(x0, x1 + 1):
        for j in range(k):
            L.put(x, y + j, R, (4 if (x + j) % 2 == 0 else 3) if k == 2 else 3)
    L.put(x0 + 2 * k, y + k, R, 3)
    L.put(x0 + 2 * k, y + 2 * k, R, 2)
    if k == 2:
        L.put(x0 + 4, y + 2, R, 3)
        L.put(x0 + 4, y + 5, R, 2)
        L.put(x0 + 5, y + 6, R, 2)


def pendant(h, G, chain=GOLD):
    k = h.k
    L = h.L('acc')
    x0, y0, x1, y1 = h.b['torso']
    cx = (x0 + x1 + 1) // 2
    if k == 1:
        L.put(cx - 1, y0 + 1, chain, 3)
        L.put(cx, y0 + 1, chain, 2)
        L.put(cx - 1, y0 + 2, G, 4)
        L.put(cx, y0 + 2, G, 2)
        return
    for i in range(4):
        L.put(cx - 4 + i, y0 + 1 + i, chain, 4 if i % 2 == 0 else 3)
        L.put(cx + 3 - i, y0 + 1 + i, chain, 3 if i % 2 == 0 else 2)
    L.rect(cx - 1, y0 + 5, cx, y0 + 8, G, 3)
    L.put(cx - 2, y0 + 6, G, 3)
    L.put(cx + 1, y0 + 6, G, 2)
    L.put(cx - 1, y0 + 5, G, 5)
    L.put(cx - 2, y0 + 7, G, 2)
    L.put(cx + 1, y0 + 7, G, 1)
    L.put(cx, y0 + 8, G, 1)


def buttons(h, R=GOLD, n=3, x=None):
    k = h.k
    L = h.L('chest')
    x0, y0, x1, y1 = h.b['torso']
    cx = x if x is not None else (x0 + x1 + 1) // 2
    for i in range(n):
        y = y0 + (3 + 3 * i) * k
        L.put(cx - 1 if k == 2 else cx, y, R, 4)
        if k == 2:
            L.put(cx, y, R, 3)
            L.put(cx, y + 1, R, 2)
            L.put(cx - 1, y + 1, R, 3)


def feather_cap(h, R=BROWN, F=RED):
    k = h.k
    skullcap(h, R, rim=None, rows=2)
    L = h.L('hat')
    x0, y0, x1, y1 = h.b['head']
    for y in range(y0 + k, y0 + 2 * k):                       # tilted brim on the right
        for x in range(x0, x1 + 2 * k):
            L.put(x, y, R, 2 if x > x1 else 3)
    feather(h, x0 + 2 * k, y0 - k, F)


def feather(h, x, y, F, L=None):
    """A feather stuck in a hat band, leaning right: a vane lit on its left, a light quill down its middle."""
    k = h.k
    L = L or h.L('hat')
    if k == 1:
        for (dx, dy, t) in ((0, 0, 3), (0, -1, 4), (1, -1, 3), (0, -2, 4), (1, -2, 2), (1, -3, 3), (1, -4, 4),
                            (2, -5, 3)):
            L.put(x + dx, y + dy, F, t)
        return
    for j in range(12):
        c = x + j // 4
        w = 0 if j < 2 or j > 10 else 1
        for i in range(-w, w + 2):
            t = 4 if i < 0 else 3 if i == 0 else 2
            L.put(c + i, y - j, F, t)
        L.put(c, y - j, F, 5 if 2 < j < 10 else 3)
    L.put(x + 2, y - 12, F, 3)


def villager_paint(robe_extras=(), hat=None, acc=(), legs=True, flare=True, folds=True):
    def paint(h):
        p_shadow(h)
        if legs:
            p_villager_legs(h)
        p_robe(h, flare=flare, folds=folds)
        for f in robe_extras:
            f(h)
        if h.body.arm_mode['l'] == 'cross':
            p_cross_arms(h)
        p_arms(h, sleeve='long', folds=False)
        p_hands(h)
        p_villager_head(h)
        p_villager_face(h)
        if hat:
            hat(h)
        for f in acc:
            f(h)
    return paint


def V(**kw):
    out = dict(kind='villager', pose='cross', skin=SKIN_TAN, hair=HAIR_DARK, eye=IRIS_GREEN, top=ROBE,
               shoes=DLEATHER, seed=11)
    out.update(kw)
    return out


def villager_farmer():
    return V(top=ROBE, held='hoe', paint=[villager_paint(
        robe_extras=[lambda h: apron(h, OLIVE, top=5, wheat=True)],
        hat=lambda h: brim_hat(h, STRAW, brim=2, crown_h=3, brim_y=1, crown_in=1, band=RED, weave=True))])


def villager_librarian():
    return V(top=CRIMSON, held='book', eye=IRIS_BROWN, paint=[villager_paint(
        robe_extras=[lambda h: buttons(h, GOLD, 3)],
        hat=lambda h: skullcap(h, PLUM, rim=GOLD, button=GOLD, rows=2),
        acc=[lambda h: glasses(h, GOLD)])])


def villager_blacksmith():
    return V(top=GREYC, held='hammer', hair=HAIR_BLACK, skin=SKIN_BROWN, paint=[villager_paint(
        robe_extras=[lambda h: apron(h, LEATHER, top=3, rivets=True)],
        hat=lambda h: goggles(h))])


def villager_butcher():
    return V(top=ROBE, held='cleaver', paint=[villager_paint(
        robe_extras=[lambda h: apron(h, WHITEC, top=3, stains=CRIMSON, pocket=False)],
        hat=lambda h: headband(h, RED))])


def villager_cleric():
    return V(top=PURPLE, held='potion', eye=IRIS_BLUE, paint=[villager_paint(
        robe_extras=[lambda h: center_band(h, GOLD, 2, start=2), lambda h: pendant(h, AMETHYST)],
        hat=lambda h: skullcap(h, PURPLE, rim=GOLD, rows=2))])


def villager_fisherman():
    return V(top=BLUE, held='rod', paint=[villager_paint(
        robe_extras=[lambda h: rope_belt(h, STRAW)],
        hat=lambda h: souwester(h, YELLOW))])


def villager_cartographer():
    return V(top=FOREST, held='map', eye=IRIS_BLUE, hair=HAIR_GREY, paint=[villager_paint(
        robe_extras=[lambda h: buttons(h, GOLD, 4)],
        hat=lambda h: feather_cap(h, CRIMSON, WHITEC),
        acc=[lambda h: monocle(h, GOLD)])])


def villager_merchant():
    return V(top=NAVY, held='bag', eye=IRIS_BROWN, paint=[villager_paint(
        robe_extras=[lambda h: center_band(h, GOLD, 2, start=3)],
        hat=lambda h: hood(h, BLUE, trim=GOLD),
        acc=[lambda h: pendant(h, EMERALD)])])


# ------------------------------------------------------------------ armour, beards, hats, dresses (roles)
def plate(L, b, M, k, lames=0, hi=True, side='l', bottom=True):
    """A metal plate (contrasty ramp): base front, lit left column, a highlight streak a little inside it,
    dark right edge (two columns at k=2), lames = a gap line every `lames` skin px with a lit lip under it."""
    x0, y0, x1, y1 = b
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            t = 3
            if x == x0:
                t = 4
            if x == x1 or (k == 2 and x == x1 - 1):
                t = 2 if x == x1 - 1 or k == 1 else 1
            L.put(x, y, M, t)
    if hi:
        hx = x0 + (1 if k == 1 else 2)
        if hx < x1 - 1:
            for y in range(y0 + k, y0 + max(k + 1, (y1 - y0) * 3 // 5)):
                L.put(hx, y, M, 5)
    if lames:
        y = y0 + lames * k
        while y < y1 - k:
            for x in range(x0, x1 + 1):
                L.put(x, y, M, 1)
                if k == 2:
                    L.put(x, y + 1, M, 4 if x < x1 - 1 else 3)
            y += lames * k
    if bottom:
        for x in range(x0, x1 + 1):
            L.put(x, y1, M, 1 if x > x0 else 2)


def p_plate_legs(h, M=IRON):
    k = h.k
    for sd in 'lr':
        L = h.L('leg_' + sd)
        x0, y0, x1, y1 = h.b['leg_' + sd]
        plate(L, (x0, y0, x1, y1), M, k, lames=0, bottom=False)
        ky = y0 + 5 * k                                     # knee cop: a lit rim, its shadow below
        for x in range(x0, x1 + 1):
            L.put(x, ky, M, 5 if x < x1 - k else 3)
            L.put(x, ky + k, M, 1)
            if k == 2:
                L.put(x, ky + 1, M, 4 if x < x1 - 1 else 2)
        if k == 2:
            L.put(x0 + 3, ky + 1, M, 5)
        for x in range(x0, x1 + 1):
            L.put(x, y0, M, 2)                              # under the faulds


def p_plate_feet(h, M=STEEL):
    k = h.k
    for sd in 'lr':
        L = h.L('foot_' + sd)
        x0, y0, x1, y1 = h.b['foot_' + sd]
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                L.put(x, y, M, 1 if y == y1 else 4 if y == y0 and x < x1 else 2 if x == x1 else 3)
        if k == 2:
            L.put(x0 + 1, y0, M, 5)


def p_plate_torso(h, M=IRON):
    k = h.k
    L = h.L('torso')
    x0, y0, x1, y1 = h.b['torso']
    plate(L, (x0, y0, x1, y1), M, k, hi=False, bottom=False)
    cx = (x0 + x1 + 1) // 2
    for y in range(y0 + k, y1 - 3 * k):                     # the breastplate's ridge: lit left, dark right
        L.put(cx - 1, y, M, 5 if k == 2 else 4)
        L.put(cx, y, M, 2)
        if k == 2:
            L.put(cx - 2, y, M, 4)
    for x in range(x0, x1 + 1):                             # gorget under the chin
        L.put(x, y0, M, 1 if x0 + k < x < x1 - k else 2)
    y = y1 - 3 * k + 1                                      # faulds: overlapping lames at the waist
    while y <= y1:
        for x in range(x0, x1 + 1):
            L.put(x, y, M, 1)
            if y + 1 <= y1:
                L.put(x, y + 1, M, 4 if x < x1 - k else 3)
        y += 2 * k if k == 2 else 2


def p_plate_arms(h, M=IRON):
    """Plate arms: rerebrace and vambrace as lit plates with lames, and a pauldron over the shoulder - wider
    than the arm on the outer side, lit on top, casting a dark row on the arm under it."""
    k = h.k
    for sd in 'lr':
        mode = h.body.arm_mode[sd]
        if mode == 'cross':
            continue
        L = h.L('arm_' + sd)
        x0, y0, x1, y1 = h.b['arm_' + sd]
        hx0, hy0, hx1, hy1 = h.b['hand_' + sd]
        a0, a1 = (y0, hy0 - 1) if mode != 'up' else (hy1 + 1, y1)
        plate(L, (x0, a0, x1, a1), M, k, lames=4, hi=True, bottom=False)
        if mode == 'reach':
            continue
        py0, py1 = (y0 - k, y0 + 3 * k) if mode != 'up' else (y1 - 3 * k, y1 + k)
        px0, px1 = (x0 - k, x1) if sd == 'l' else (x0, x1 + k)
        for y in range(py0, py1 + 1):
            for x in range(px0, px1 + 1):
                t = 3
                if y == py0:
                    t = 5 if x < px1 - k else 4
                elif x == px0:
                    t = 4
                elif x >= px1 - (k - 1):
                    t = 2
                if y == py1:
                    t = 1 if x > px0 else 2
                L.put(x, y, M, t)
        if k == 2:
            for x in range(px0 + 1, px1):
                L.put(x, py0 + 3, M, 1 if x > px0 + 1 else 2)
                L.put(x, py0 + 4, M, 4 if x < px1 - 1 else 3)
            L.put(px0 + 2, py0 + 1, M, 5)


def great_helm(h, M=IRON, plume=RED):
    """A great helm over the whole head: lit left, the ridge down the middle, a visor slit with a lit lower
    lip, breathing holes on the shadow side, a darker rim at the neck; a feather plume on top."""
    k = h.k
    L = h.L('hat')
    x0, y0, x1, y1 = h.b['head']
    cx = (x0 + x1 + 1) // 2
    plate(L, (x0, y0, x1, y1), M, k, hi=False, bottom=True)
    for x in range(x0, x1 + 1):
        L.put(x, y0, M, 4 if x < x1 - k else 3)
    for y in range(y0 + k, y1):
        L.put(cx - 1, y, M, 5 if k == 2 else 4)
        L.put(cx, y, M, 2)
    sy = y0 + 3 * k                                         # visor slit
    for x in range(x0 + k, x1 - k + 1):
        if x in (cx - 1, cx) and k == 1:
            continue
        for j in range(k):
            L.put(x, sy + j, M, 0)
        L.put(x, sy + k, M, 4 if x < cx else 3)
    if k == 2:
        L.rect(cx - 1, sy, cx, sy + 1, M, 3)
        for (x, y) in ((cx + 2, y0 + 10), (cx + 4, y0 + 10), (cx + 3, y0 + 12), (cx + 5, y0 + 12)):
            L.put(x, y, M, 0)
        for x in (x0 + 2, x1 - 2):
            L.put(x, y0 + 2, M, 4)                          # rivets on the brow band
            L.put(x, y0 + 3, M, 1)
        for x in range(x0, x1 + 1):
            L.put(x, y0 + 4, M, 1 if x > x0 else 2)
            L.put(x, y0 + 5, M, 4 if x < cx else 3)
    if plume:
        P_ = h.L('hat')
        pts = ([(0, -1, 4), (-1, -1, 3), (0, -2, 4), (1, -2, 3), (1, -3, 4), (2, -3, 3), (2, -4, 3), (3, -4, 2)]
               if k == 1 else
               [(i, j, 0) for j in range(-1, -9, -1) for i in range(-2 + (-j) // 2, 2 + (-j) // 2 + (1 if -j < 6 else 0))])
        for (dx, dy, t) in pts:
            if k == 2:
                rel = dx - (-dy) // 2
                t = 4 if rel < 0 else 3 if rel < 2 else 2
                if dy == -8 or (dy == -7 and rel > 1):
                    continue
            P_.put(cx + dx, y0 + dy, plume, t)
        if k == 2:
            for j in range(1, 7):
                P_.put(cx - 1 + j // 2, y0 - j, plume, 5 if j < 6 else 4)


def shield(h, sd='l', field=BLUE, rim=GOLD, emblem=CREAM):
    """A heater shield strapped to the arm: a gold rim lit on the top-left, the field, a chevron, a boss;
    its own outline separates it from the body."""
    k = h.k
    if h.body.arm_mode[sd] in ('up', 'cross'):
        return
    L = h.L('shield', own=True)
    x0, y0, x1, y1 = h.b['arm_' + sd]
    w, hh = 7 * k, 9 * k
    sx0 = x0 - 2 * k if sd == 'l' else x1 - 5 * k + 1 + k
    sy0 = y0 + 3 * k
    pts = set()
    for j in range(hh):
        cut = 0
        if j >= hh - 4 * k:
            cut = (j - (hh - 4 * k)) * (w // 2) // (4 * k) + 1
        for i in range(cut, w - cut):
            pts.add((sx0 + i, sy0 + j))
    cxs = sx0 + w // 2
    edge_px = {p for p in pts if any((p[0] + dx, p[1] + dy) not in pts for dx, dy in N4)}
    for (x, y) in pts:
        edge = any((x + dx, y + dy) not in pts for dx, dy in N4)
        edge2 = k == 2 and any((x + dx, y + dy) not in pts for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)))
        if edge:
            lit = (x - 1, y) not in pts or (x, y - 1) not in pts
            L.put(x, y, rim, 4 if lit and x < cxs else 3 if lit else 2)
        elif edge2:
            L.put(x, y, rim, 2)
        else:
            L.put(x, y, field, 4 if x < cxs - k and y < sy0 + 3 * k else 3 if x < cxs else 2)
    for i in range(-(w // 2) + k, w // 2 - k + 1):         # chevron: a clean 1:1 V
        y = sy0 + (4 if k == 1 else 9) - abs(i if k == 1 else (i + (1 if i < 0 else 0)))
        x = cxs + i
        for j in range(k):
            if (x, y + j) in pts and (x, y + j) not in edge_px:
                L.put(x, y + j, emblem, 4 if i < 0 else 3)
    if k == 2:
        L.rect(cxs - 1, sy0 + 2, cxs, sy0 + 3, GOLD, 4)
        L.put(cxs, sy0 + 3, GOLD, 2)


def tabard(h, R, top=2, below=4, trim=None, emblem=None, w=None):
    """A cloth tabard over the armour: a front panel from the chest to over the thighs, lit left edge, a
    fold, a gold trim and an emblem (a lit diamond) at k=2."""
    k = h.k
    L = h.L('chest')
    x0, y0, x1, y1 = h.b['torso']
    w = w if w is not None else 1
    ax0, ax1 = x0 + w * k, x1 - w * k
    yt, yb = y0 + top * k, y1 + below * k
    cx = (x0 + x1 + 1) // 2
    for y in range(yt, yb + 1):
        for x in range(ax0, ax1 + 1):
            t = 3
            if x == ax0:
                t = 4
            if x == ax1:
                t = 2
            if y == yb:
                t = 2
            if y > y1 - k and y <= y1:
                t = min(t, 2) if x > ax0 else 3              # belted waist
            L.put(x, y, R, t)
    if k == 2:
        for y in range(y1 + 2, yb):
            L.put(cx + 2, y, R, 2)
            L.put(cx + 1, y, R, 4)
        for i in range(ax0, ax1 + 1, 2):                    # cut hem
            L.put(i, yb, R, 1)
    if trim and k == 2:
        for y in range(yt, yb + 1):
            L.put(ax0, y, trim, 4)
            L.put(ax1, y, trim, 2)
        for x in range(ax0, ax1 + 1):
            L.put(x, yt, trim, 4 if x < cx else 3)
    if emblem:
        ey = yt + (2 * k if k == 1 else 4)
        if k == 1:
            L.put(cx - 1, ey, emblem, 4)
            L.put(cx, ey, emblem, 3)
            L.put(cx - 1, ey + 1, emblem, 3)
            L.put(cx, ey + 1, emblem, 2)
        else:
            for (x, y) in {(cx - 1 + i, ey + j) for j in range(-3, 4) for i in range(-3, 4)
                           if abs(i + 0.5) + abs(j) <= 3.5}:
                rel = (x - cx + 0.5) + (y - ey)
                L.put(x, y, emblem, 5 if rel < -2 else 4 if rel < 0 else 3 if rel < 2 else 2)


def belt(h, R=DLEATHER, buckle=GOLD, y=None, h_=1):
    k = h.k
    L = h.L('belt')
    x0, y0, x1, y1 = h.b['torso']
    y = y if y is not None else y1 - h_ * k + 1
    cx = (x0 + x1 + 1) // 2
    for x in range(x0, x1 + 1):
        for j in range(h_ * k):
            L.put(x, y + j, R, 3 if j == 0 and x < x1 else 2)
    if buckle:
        if k == 1:
            L.put(cx - 1, y, buckle, 4)
            L.put(cx, y, buckle, 3)
        else:
            bw = 3 if h_ == 1 else 4
            for j in range(-1, h_ * k + 1):
                for i in range(-bw // 2 - 1, bw // 2 + 1):
                    x = cx + i
                    rim = j in (-1, h_ * k) or i in (-bw // 2 - 1, bw // 2)
                    if rim:
                        L.put(x, y + j, buckle, 4 if (j == -1 or i == -bw // 2 - 1) else 2)
            L.put(cx - 1, y + (h_ * k) // 2, buckle, 3)


def chainmail(L, b, M, k, lit_l=True):
    """Mail: rows of small rings - a lit ring top in every other pixel, a dark gap row between - a pattern on
    purpose (a texture, not dithering), lit left column, darker right."""
    x0, y0, x1, y1 = b
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if k == 1:                                       # 2 px ring tops, offset every other row
                t = (4 if ((x + (y // 2) * 2) // 2) % 2 == 0 else 3) if y % 2 == 0 else 2
            else:
                r = y % 3                                    # ring tops lit, a dark row of gaps
                t = 4 if r == 0 and (x + (y // 3)) % 3 != 2 else 2 if r == 2 else 3
            if k == 1:                                       # edges as solid columns: runs, not dots
                if x == x0:
                    t = 4 if lit_l else 3
                if x == x1:
                    t = 2
            else:
                if x == x0 and lit_l:
                    t = min(5, t + 1)
                if x == x1:
                    t = max(1, t - 1)
            L.put(x, y, M, t)


def kettle_helm(h, M=IRON):
    """A kettle hat: a dome over the top of the head (lit top-left, highlight streak) and a wide brim with a
    dark underside; a leather chin strap."""
    k = h.k
    L = h.L('hat')
    x0, y0, x1, y1 = h.b['head']
    cx = (x0 + x1 + 1) // 2
    top = y0 - 2 * k
    by = y0 + 2 * k
    for y in range(top, by):
        inset = k if y < top + k else 0
        for x in range(x0 + inset, x1 + 1 - inset):
            t = 3
            if x == x0 + inset:
                t = 4
            if x >= x1 - inset - (k - 1):
                t = 2
            if y == top:
                t = 4
            L.put(x, y, M, t)
    for y in range(top + k, by - k):
        L.put(x0 + 2 * k, y, M, 5)
    for x in range(x0 - 2 * k, x1 + 2 * k + 1):
        for j in range(k):
            L.put(x, by + j, M, (5 if x < cx - 2 * k else 4 if x < cx else 3) if j == 0 else 2)
        L.put(x, by + k, M, 1)
    for y in range(by + k + 1, y1 + 1):
        L.put(x0, y, DLEATHER, 3)
        L.put(x1, y, DLEATHER, 2)


def p_beard(h, R=None, length=2, style='full', mustache=True):
    """Facial hair on its own part: a mustache over the mouth, a beard round the jaw (k=2: strands as lit /
    dark streaks), long beards hang over the chest and taper to a point; lit left, dark right."""
    k = h.k
    R = R or h.m('hair')
    L = h.L('beard')
    x0, y0, x1, y1 = h.b['head']
    f = h.fs
    cx = (x0 + x1 + 1) // 2 + f
    w = x1 - x0 + 1
    hh = y1 - y0 + 1
    if style != 'none':
        jaw = y0 + hh - (3 * k if k == 1 else 6)
        bot = y1 + length * k
        for y in range(jaw, bot + 1):
            if y <= y1:
                if y < jaw + k:
                    rng = [x for x in range(x0, x1 + 1) if x < x0 + k or x > x1 - k]
                else:
                    rng = [x for x in range(x0, x1 + 1)]
            else:
                d = y - y1
                taper = (d * (w // 2 - 1)) // max(1, length * k) if style == 'long' else d // 2
                rng = [x for x in range(x0 + taper, x1 - taper + 1)]
            for x in rng:
                if y <= y1 and y >= jaw + k and x0 + 2 * k <= x <= x1 - 2 * k and y < y1 - k + 1 and k == 1:
                    continue                                # the mouth area stays open at k=1
                if y <= y1 and k == 2 and x0 + 4 <= x <= x1 - 4 and y < jaw + 4:
                    continue
                t = 3
                rel = x - x0
                if rel < w // 3:
                    t = 4
                elif rel > 2 * w // 3:
                    t = 2
                if k == 2 and (x * 3 + y) % 7 == 0:
                    t = max(1, t - 1)
                L.put(x, y, R, t)
    if mustache:
        my = y0 + (6 if k == 1 else 12)
        if style == 'none':
            my = y0 + (5 if k == 1 else 12)
        if k == 1:
            for x in (cx - 2, cx - 1, cx, cx + 1):
                L.put(x, y0 + 5, R, 4 if x < cx - 1 else 3 if x < cx + 1 else 2)
        else:
            for i, x in enumerate(range(cx - 5, cx + 5)):
                yy = my - 1 + (1 if i in (0, 9) else 0)
                L.put(x, yy, R, 4 if x < cx - 1 else 3 if x < cx + 1 else 2)
                if 1 <= i <= 8:
                    L.put(x, yy - 1, R, 3 if x < cx else 2)
            L.put(cx - 1, my - 2, R, 1)


def pointy_hat(h, R, band=None, tip=1, brim=2, height=10, emblem=None, buckle=None):
    """A wizard / witch hat: a wide brim (lit top, dark underside, its shadow on the forehead), a cone that
    narrows step by step and bends over at the tip (tip = +1 right / -1 left), a band at its foot."""
    k = h.k
    L = h.L('hat')
    x0, y0, x1, y1 = h.b['head']
    cx = (x0 + x1 + 1) // 2
    by = y0 + k
    w0 = (x1 - x0 + 1) // 2 + k
    H_ = height * k
    for j in range(H_):
        y = by - 1 - j
        half = max(k, w0 - (j * w0) // H_)
        bend = 0
        if j > H_ * 0.62:
            bend = tip * (j - int(H_ * 0.62)) * 2 // 3
        for x in range(cx - half + bend, cx + half + bend):
            rel = (x - (cx + bend - half)) / max(1, 2 * half)
            t = 4 if rel < 0.3 else 3 if rel < 0.72 else 2
            L.put(x, y, R, t)
    if band:
        for j in range(2 * k if k == 2 else 1):
            y = by - 1 - j
            half = w0
            for x in range(cx - half, cx + half):
                rel = (x - (cx - half)) / (2 * half)
                L.put(x, y, band, 4 if rel < 0.3 else 3 if rel < 0.72 else 2)
        if buckle:
            if k == 1:
                L.put(cx - 1, by - 1, buckle, 4)
            else:
                L.rect(cx - 2, by - 4, cx + 1, by - 4, buckle, 4)
                L.rect(cx - 2, by - 1, cx + 1, by - 1, buckle, 3)
                L.rect(cx - 2, by - 4, cx - 2, by - 1, buckle, 4)
                L.rect(cx + 1, by - 4, cx + 1, by - 1, buckle, 2)
    for x in range(x0 - brim * k, x1 + brim * k + 1):
        for j in range(k):
            L.put(x, by + j, R, (4 if x < cx else 3) if j == 0 else 2)
        L.put(x, by + k, R, 1)
    if emblem and k == 2:
        ex, ey = cx - 1, by - 9
        for (dx, dy, t) in ((0, 0, 5), (1, 0, 4), (0, -1, 4), (0, 1, 4), (-1, 0, 4), (1, 1, 3), (-1, -1, 4),
                            (2, 0, 3), (0, 2, 3), (-2, 0, 4), (0, -2, 4)):
            L.put(ex + dx, ey + dy, emblem, t)
    elif emblem:
        L.put(cx - 1, by - 3, emblem, 4)
    face = h.fig.layers.get('face')
    S = h.m('skin')
    for x in range(x0, x1 + 1):
        if k == 2 and not (face and (x, by + k + 1) in face.px):
            L.put(x, by + k + 1, S, 2)


def p_dress(h, R, waist=None, steps=3, step_h=4, hem=None, folds=True, bottom=1):
    """A long skirt from the waist to the ground, flaring one step every `step_h` px (a bell), vertical folds
    with a lit lip, a darker hem band (or a lace trim), the waist shadow at the top."""
    k = h.k
    L = h.L('robe')
    x0, y0, x1, y1 = h.b['torso']
    g = h.body.ground
    wy = waist if waist is not None else y1 - 2 * k + 1
    bot = g - bottom * k - 1
    cx = (x0 + x1 + 1) // 2
    rows = list(range(wy, bot + 1))
    for y in rows:
        e = min(steps, (y - wy) // (step_h * k)) * k
        for x in range(x0 - e, x1 + e + 1):
            t = 3
            if x <= x0 - e + (k - 1):
                t = 4
            if x >= x1 + e - (k - 1):
                t = 2
            if y < wy + k:
                t = 2 if x > x0 else 3
            L.put(x, y, R, t)
        if folds:
            for fx_ in ((cx - 2 * k - e // 2, cx + 2 * k + e // 2 - 1) if k == 1 else
                        (cx - 5 - e // 2, cx - 1, cx + 4 + e // 2)):
                if y > wy + 2 * k:
                    L.put(fx_, y, R, 2)
                    if k == 2 and fx_ < cx + 2:
                        L.put(fx_ - 1, y, R, 4)
        if y > wy and (y - wy) % (step_h * k) == 0 and (y - wy) // (step_h * k) <= steps:
            L.put(x0 - e, y, R, 4)
    last = min(steps, (bot - wy) // (step_h * k)) * k
    for x in range(x0 - last, x1 + last + 1):
        for j in range(k):
            L.put(x, bot - j, hem or R, (2 if x > cx else 3) if hem is None else (4 if x < cx else 3) if j else 2)
        if hem and k == 2 and x % 3 == 0:
            L.put(x, bot + 1, hem, 3)


def p_boots(h, R=DLEATHER, height=4, cuff=True):
    """Tall boots over the trouser legs: a turned-down cuff (lit), the shaft, a lit toe, a dark sole."""
    k = h.k
    for sd in 'lr':
        L = h.L('foot_' + sd)
        x0, y0, x1, y1 = h.b['leg_' + sd]
        top = y1 - height * k + 1
        for y in range(top, y1 + 1):
            for x in range(x0, x1 + 1):
                t = 3
                if x == x0 and sd == 'l':
                    t = 4
                if x == x1:
                    t = 2
                if y == y1:
                    t = 1
                if y == y1 - k and x < x1:
                    t = 4 if k == 1 else t
                L.put(x, y, R, t)
        if cuff:
            for x in range(x0, x1 + 1):
                for j in range(k):
                    L.put(x, top + j, R, 4 if x < x1 else 3)
                L.put(x, top + k, R, 2)
        if k == 2:
            L.rect(x0 + 1, y1 - 3, x1 - 1, y1 - 3, R, 4)      # toe cap
            L.rect(x0, y1 - 1, x1, y1 - 1, R, 2)
            L.put(x0 + 1, y1 - 3, R, 5)


def cape_back(h, R, lining=None, to=1, spread=2):
    """A cape hanging behind the body: shows round the arms and legs, wider at the bottom, lit on the left,
    deep folds as dark-mid stripes."""
    k = h.k
    L = h.L('back')
    x0, y0, x1, y1 = h.b['torso']
    ax0 = h.b['arm_l'][0]
    ax1 = h.b['arm_r'][2]
    g = h.body.ground
    bot = g - to * k
    for y in range(y0, bot):
        u = (y - y0) / max(1, bot - y0)
        e = int(round(spread * k * u))
        for x in range(ax0 - e, ax1 + e + 1):
            rel = (x - (ax0 - e)) / max(1, ax1 - ax0 + 2 * e)
            t = 4 if rel < 0.12 else 3 if rel < 0.8 else 2
            if (x - ax0) % (3 * k) == 0 and y > y0 + 6 * k:
                t = 2
            L.put(x, y, R, t)
    for x in range(ax0 - spread * k, ax1 + spread * k + 1):
        if (x, bot - 1) in L.px:
            L.put(x, bot - 1, R, 1)


def ermine(h, rows=2):
    """An ermine collar over the shoulders: white fur with black tail tips, lit top."""
    k = h.k
    L = h.L('collar')
    x0, y0, x1, y1 = h.b['torso']
    ax0 = h.b['arm_l'][0]
    ax1 = h.b['arm_r'][2]
    for y in range(y0 - k, y0 + rows * k):
        for x in range(ax0, ax1 + 1):
            if y < y0 and (x < x0 - k or x > x1 + k):
                continue
            t = 4 if y < y0 else 3
            if x == ax1 or (y == y0 + rows * k - 1):
                t = 2
            L.put(x, y, FUR, t)
    for x in range(ax0 + k, ax1, 3 * k):
        L.put(x, y0 + (rows - 1) * k - (1 if k == 2 else 0), BLACKC, 1)
        if k == 2:
            L.put(x, y0 + rows * k - 2, BLACKC, 1)


def crown(h, M=GOLD, gems=(RUBY, SAPPHIRE), velvet=CRIMSON):
    """A gold crown: a band round the head with lit top edge, three points, gems with a glint, red velvet
    inside between the points."""
    k = h.k
    L = h.L('hat')
    x0, y0, x1, y1 = h.b['head']
    cx = (x0 + x1 + 1) // 2
    by = y0 - k
    for y in range(by, by + 2 * k):
        for x in range(x0, x1 + 1):
            t = 3
            if x == x0:
                t = 4
            if x >= x1 - (k - 1):
                t = 2
            if y == by:
                t = 5 if x < cx else 4
            if y == by + 2 * k - 1:
                t = 2
            L.put(x, y, M, t)
    for y in range(by - 2 * k, by):                         # velvet cap
        for x in range(x0 + k, x1 - k + 1):
            L.put(x, y, velvet, 3 if x < cx else 2)
    for pxc in (x0, cx - k, x1 - k + 1):                    # points
        ph = 3 * k if pxc == cx - k else 2 * k
        for j in range(ph):
            for i in range(k if pxc != cx - k else 2 * k):
                L.put(pxc + i, by - 1 - j, M, 4 if i == 0 else 3)
        L.put(pxc, by - ph, M, 5)
    g0, g1 = gems
    if k == 1:
        L.put(cx - 1, by, g0, 4)
        L.put(cx, by, g0, 3)
    else:
        L.rect(cx - 2, by + 1, cx + 1, by + 2, g0, 3)
        L.put(cx - 2, by + 1, g0, 5)
        L.put(cx + 1, by + 2, g0, 2)
        for gx in (x0 + 2, x1 - 3):
            L.rect(gx, by + 1, gx + 1, by + 2, g1, 3)
            L.put(gx, by + 1, g1, 5)
        L.put(cx - 1, by - 7, RUBY, 4)


def tiara(h, M=GOLD, gem=None):
    k = h.k
    gem = gem or PINK
    L = h.L('hat')
    x0, y0, x1, y1 = h.b['head']
    cx = (x0 + x1 + 1) // 2
    if k == 1:
        L.put(cx - 2, y0, M, 4)
        L.put(cx + 1, y0, M, 3)
        L.put(cx - 1, y0 - 1, gem, 4)
        L.put(cx, y0 - 1, M, 4)
        L.put(cx - 1, y0, M, 4)
        L.put(cx, y0, M, 3)
        return
    for x in range(cx - 6, cx + 6):
        L.put(x, y0 + 1, M, 4 if x < cx else 3)
    for (dx, dy) in ((-4, 0), (3, 0), (-2, -1), (1, -1), (-1, -2), (0, -2), (-1, -3), (0, -3)):
        L.put(cx + dx, y0 + 1 + dy, M, 4 if dx < 0 else 3)
    L.rect(cx - 1, y0 - 1, cx, y0, gem, 3)
    L.put(cx - 1, y0 - 1, gem, 5)
    L.put(cx, y0, gem, 2)


def hair_front_locks(h, R, length=6):
    """Long hair falling in front of the shoulders: two locks over the chest, strands lit on the left."""
    k = h.k
    L = h.L('hair')
    x0, y0, x1, y1 = h.b['head']
    tx0, ty0, tx1, ty1 = h.b['torso']
    for sd in 'lr':
        lx0 = x0 - k if sd == 'l' else x1 - 2 * k + 1
        lx1 = lx0 + 3 * k - 1 - (k if sd == 'r' else 0)
        if sd == 'r':
            lx0, lx1 = x1 - 2 * k + 1, x1 + k
        for y in range(y1 - 4 * k, ty0 + length * k):
            tip = y > ty0 + length * k - 2 * k
            for x in range(lx0 + (k if tip and sd == 'l' else 0), lx1 + 1 - (k if tip and sd == 'r' else 0)):
                t = 4 if x == lx0 else 2 if x == lx1 else 3
                if k == 2 and (x - lx0) == 3 and y % 4 != 0:
                    t = 2
                L.put(x, y, R, t)


def hair_back(h, R, length=8):
    """Long hair behind the head and shoulders (shows beside the head and the neck)."""
    k = h.k
    L = h.L('back')
    x0, y0, x1, y1 = h.b['head']
    for y in range(y0 + k, y1 + length * k):
        for x in range(x0 - k, x1 + k + 1):
            L.put(x, y, R, 2 if x > (x0 + x1) // 2 else 3)


def eyepatch(h, R=BLACKC):
    k = h.k
    L = h.L('acc')
    x0, y0, x1, y1 = h.b['head']
    cx = (x0 + x1 + 1) // 2 + h.fs
    if k == 1:
        ey = y0 + 4
        L.put(cx + 1, ey, R, 2)
        L.put(cx + 2, ey, R, 1)
        L.put(cx + 1, ey + 1, R, 1)
        L.put(cx + 2, ey + 1, R, 1)
        L.put(cx + 3, ey - 1, R, 1)
        L.put(cx - 2, ey - 2, R, 2)
        for x in range(cx - 1, cx + 3):
            L.put(x, ey - 2 + (1 if x > cx + 1 else 0), R, 2)
        return
    ey = y0 + 8
    for (x, y) in ell(cx + 4.5, ey + 1.5, 2.8, 2.4):
        L.put(x, y, R, 2 if x > cx + 4 or y > ey + 1 else 3)
    L.put(cx + 3, ey, R, 4)
    for i in range(11):                                     # the strap across the forehead
        L.put(cx + 6 - i, ey - 2 - (i // 3), R, 2)
        L.put(cx + 7, ey + i // 4, R, 1) if i < 3 else None


def tricorn(h, R=BLACKC, trim=GOLD, emblem=BONE):
    """A tricorn: a crown on the head, the brim turned up into a point at the front - low in the middle,
    rising to horns at the sides - gold trim on the edge, a little skull on the front."""
    k = h.k
    L = h.L('hat')
    x0, y0, x1, y1 = h.b['head']
    cx = (x0 + x1 + 1) // 2
    for y in range(y0 - 3 * k, y0 + k):                     # crown
        inset = k if y < y0 - 2 * k else 0
        for x in range(x0 + inset, x1 + 1 - inset):
            L.put(x, y, R, 4 if x < cx - k and y < y0 - k else 3 if x < x1 - k else 2)
    for x in range(x0 - 3 * k, x1 + 3 * k + 1):             # brim: V-shaped front edge
        d = abs(x + 0.5 - cx)
        yb = y0 + 2 * k - int(d * 2 // (3 if k == 1 else 3))
        yt = yb - 2 * k
        for y in range(yt, yb + 1):
            t = 3 if y < yb else 2
            if y == yt:
                t = 4 if x < cx else 3
            L.put(x, y, R, t)
        L.put(x, yb, trim, 4 if x < cx else 2)
        if k == 2:
            L.put(x, yb - 1, trim, 3 if x < cx else 2)
    if k == 1:
        L.put(cx - 1, y0 - 1, emblem, 4)
        L.put(cx, y0 - 1, emblem, 3)
    else:
        ex, ey = cx - 2, y0 - 3
        for (dx, dy) in ((0, 0), (1, 0), (2, 0), (3, 0), (0, 1), (1, 1), (2, 1), (3, 1), (1, 2), (2, 2)):
            L.put(ex + dx, ey + dy, emblem, 4 if dx < 2 else 3)
        L.put(ex + 1, ey + 1, emblem, 0)
        L.put(ex + 3, ey + 1, emblem, 0)
        L.put(ex - 1, ey + 3, emblem, 3)
        L.put(ex + 4, ey + 3, emblem, 2)
        L.put(ex + 4, ey - 1, emblem, 3)
        L.put(ex - 1, ey - 1, emblem, 4)


def coat(h, R, trim=GOLD, tails=6, open_w=2):
    """An open long coat: two front panels down past the hips, lit lapel edge on the left panel, dark
    inner edge on the right one, gold buttons; the shirt shows between them."""
    k = h.k
    L = h.L('chest')
    x0, y0, x1, y1 = h.b['torso']
    cx = (x0 + x1 + 1) // 2
    bot = y1 + tails * k
    for y in range(y0, bot + 1):
        for x in range(x0, x1 + 1):
            if cx - open_w * k <= x < cx + open_w * k:
                continue
            left = x < cx
            t = 3
            if x == x0:
                t = 2
            if left and x == cx - open_w * k - 1:
                t = 4                                       # lapel edge catches the light
            if not left and x == cx + open_w * k:
                t = 2
            if x == x1:
                t = 2
            if y == bot:
                t = 2
            L.put(x, y, R, t)
    if trim:
        for i in range(3):
            y = y0 + (4 + 3 * i) * k
            L.put(cx - open_w * k - 2 * k, y, trim, 4)
            if k == 2:
                L.put(cx - open_w * k - 3, y, trim, 3)
                L.put(cx - open_w * k - 4, y + 1, trim, 2)
                L.put(cx - open_w * k - 3, y + 1, trim, 2)


def stripes(h, A, B, every=2):
    k = h.k
    L = h.L('torso')
    x0, y0, x1, y1 = h.b['torso']
    for y in range(y0 + k, y1 + 1):
        r = A if ((y - y0) // (every * k)) % 2 == 0 else B
        for x in range(x0, x1 + 1):
            t = 3 if x0 < x < x1 else (4 if x == x0 else 2)
            if x == x0:
                t = 2
            L.put(x, y, r, t)


def hard_hat(h, M=YELLOW, lamp=True):
    """A miner's hard hat: a dome with a centre ridge, a short brim with a dark underside, and a head lamp -
    an iron ring round a glowing lens with a white core."""
    k = h.k
    L = h.L('hat')
    x0, y0, x1, y1 = h.b['head']
    cx = (x0 + x1 + 1) // 2
    top = y0 - 2 * k
    by = y0 + 2 * k
    for y in range(top, by):
        inset = k if y < top + k else 0
        for x in range(x0 + inset, x1 + 1 - inset):
            t = 3
            if x == x0 + inset:
                t = 4
            if x >= x1 - inset - (k - 1):
                t = 2
            if y == top:
                t = 4 if x < cx else 3
            L.put(x, y, M, t)
    if k == 2:
        for y in range(top, by):
            L.put(cx - 1, y, M, 4)
            L.put(cx, y, M, 2)
        L.rect(x0 + 2, top + 1, x0 + 3, top + 2, M, 5)
    for x in range(x0 - k, x1 + k + 1):
        for j in range(k):
            L.put(x, by + j, M, (4 if x < cx else 3) if j == 0 else 2)
        L.put(x, by + k, M, 1)
    if lamp:
        ly = y0 - (0 if k == 1 else 1)
        if k == 1:
            L.put(cx - 1, ly, LAMP, 5)
            L.put(cx, ly, LAMP, 4)
            L.put(cx - 1, ly + 1, IRON, 3)
            L.put(cx, ly + 1, IRON, 2)
            fx_spark(h, cx - 1, ly - 2, LAMP)
        else:
            for (x, y) in ell(cx, ly + 1, 3.0, 2.8):
                L.put(x, y, IRON, 4 if x < cx - 1 and y < ly + 1 else 3 if x < cx + 1 else 2)
            for (x, y) in ell(cx, ly + 1, 2.0, 1.8):
                L.put(x, y, LAMP, 4)
            L.put(cx - 1, ly, LAMP, 5)
            L.put(cx - 2, ly + 1, CREAM, 5)
            L.put(cx, ly + 2, LAMP, 3)
            fx_spark(h, cx - 6, ly - 4, LAMP)


def overalls(h, R=DENIM, button=GOLD):
    """Overalls: a bib on the chest with straps to the shoulders and two buttons, a pocket on the bib."""
    k = h.k
    L = h.L('chest')
    x0, y0, x1, y1 = h.b['torso']
    bx0, bx1 = x0 + k, x1 - k
    by = y0 + 4 * k
    for y in range(by, y1 + 1):
        for x in range(bx0, bx1 + 1):
            t = 4 if x == bx0 else 2 if x == bx1 else 3
            L.put(x, y, R, t)
    for y in range(y0, by):
        for j in range(k):
            L.put(bx0 + j, y, R, 4 if j == 0 else 3)
            L.put(bx1 - j, y, R, 2 if j == 0 else 3)
    L.put(bx0 + (k - 1), by, button, 4)
    L.put(bx1 - (k - 1), by, button, 3)
    if k == 2:
        L.rect(bx0 + 3, by + 3, bx1 - 3, by + 3, R, 2)      # pocket
        L.rect(bx0 + 3, by + 4, bx1 - 3, by + 4, R, 4)
        for y in range(by + 3, by + 9):
            L.put(bx0 + 3, y, R, 2)
            L.put(bx1 - 3, y, R, 2)
        L.rect(bx0 + 3, by + 9, bx1 - 3, by + 9, R, 2)
        L.rect(x0, y1 - 1, x1, y1, R, 3)
        L.rect(x0, y1 - 1, x1, y1 - 1, R, 2)


def ninja_mask(h, R=BLACKC, band=RED):
    """The ninja hood: everything black but an eye slit; a red headband whose tails fly out to the right."""
    k = h.k
    L = h.L('hat')
    x0, y0, x1, y1 = h.b['head']
    sy0, sy1 = y0 + 3 * k, y0 + 5 * k - 1                   # eye slit rows (k=2: 6..9)
    if k == 2:
        sy0, sy1 = y0 + 6, y0 + 10
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if sy0 <= y <= sy1 and x0 + k <= x <= x1 - k:
                continue
            t = 3
            if x == x0:
                t = 4
            if x >= x1 - (k - 1):
                t = 2
            if y == y0:
                t = 4
            if y == sy1 + 1 and x0 < x < x1:
                t = 4                                       # the mask's lit upper edge under the eyes
            L.put(x, y, R, t)
    if k == 2:
        for (x, y) in ((x0 + 5, y0 + 13), (x0 + 6, y0 + 14), (x0 + 10, y0 + 13), (x0 + 9, y0 + 14)):
            L.put(x, y, R, 2)                               # cloth folds over the nose
    by = y0 + 2 * k
    for x in range(x0, x1 + 1):
        for j in range(k):
            L.put(x, by + j, band, (4 if x < (x0 + x1) // 2 else 3) if j == 0 else 2)
    tx = x1 + 1
    for i in range(6 * k):                                  # two tails, waving
        y = by + (i // (2 * k)) + (1 if (i // k) % 3 == 1 else 0)
        L.put(tx + i, y, band, 3 if i % 2 else 2)
        if i < 5 * k:
            L.put(tx + i, y + k + (i // (3 * k)), band, 2)
    for (x, y) in ((tx, by - 1), (tx + 1, by - 1)) if k == 2 else ((tx, by - 1),):
        L.put(x, y, band, 4)


def katana_back(h):
    """A katana carried on the back: the wrapped grip and the gold guard stick out over the left shoulder,
    the scabbard's tip shows past the right hip (the rest is hidden by the body)."""
    k = h.k
    L = h.L('back')
    x0, y0, x1, y1 = h.b['torso']
    ax0 = h.b['arm_l'][0]
    ax1 = h.b['arm_r'][2]
    sx, sy = ax0 - k, y0 - 5 * k                             # pommel
    n = 4 * k
    for i in range(n):                                       # grip: wrap in a diamond pattern
        x, y = sx + i, sy + i
        L.put(x, y, BLACKC, 3)
        L.put(x, y - 1, BLACKC, 4 if k == 2 else 3)
        if k == 2 and i % 3 == 1:
            L.put(x, y, RED, 3)
    gx, gy = sx + n, sy + n                                  # tsuba
    for j in range(-k, k + 1):
        L.put(gx - j, gy + j, GOLD, 4 if j < 0 else 3)
    L.put(gx, gy + 1, DWOOD, 3)
    tx, ty = ax1 + 1, y1 - k                                 # scabbard tip past the right hip
    for i in range(3 * k):
        L.put(tx + i, ty + i, DWOOD, 3)
        L.put(tx + i, ty + i - 1, DWOOD, 4)
    L.put(tx + 3 * k, ty + 3 * k, GOLD, 3)
    L.put(tx + 3 * k, ty + 3 * k - 1, GOLD, 4)


def quiver_back(h, R=LEATHER):
    """A quiver on the back: leather tube over the left shoulder, arrow shafts and fletchings above it."""
    k = h.k
    L = h.L('back')
    x0, y0, x1, y1 = h.b['torso']
    qx, qy = x0 - 2 * k, y0 - 3 * k
    for i in range(10 * k):
        x, y = qx + i // 2, qy + i
        for j in range(3 * k):
            L.put(x + j, y, R, 4 if j == 0 else 2 if j == 3 * k - 1 else 3)
    for a in range(3):
        ax = qx + a * k + (k - 1)
        top = qy - (3 + a % 2) * k
        for y in range(top, qy):
            L.put(ax, y, WOOD, 3)
        L.put(ax, top - 1, WHITEC if a != 1 else RED, 4)
        L.put(ax, top, WHITEC if a != 1 else RED, 3)
        if k == 2:
            L.put(ax - 1, top, WHITEC if a != 1 else RED, 4)
            L.put(ax - 1, top + 1, WHITEC if a != 1 else RED, 3)
            L.put(ax + 1, top + 1, WHITEC if a != 1 else RED, 2)


def bracer(h, sd, R=DLEATHER):
    k = h.k
    if h.body.arm_mode[sd] in ('cross', 'reach'):
        return
    L = h.L('arm_' + sd)
    x0, y0, x1, y1 = h.b['arm_' + sd]
    hx0, hy0, hx1, hy1 = h.b['hand_' + sd]
    if h.body.arm_mode[sd] == 'up':
        b0, b1 = hy1 + 1, hy1 + 3 * k
    else:
        b0, b1 = hy0 - 3 * k, hy0 - 1
    for y in range(b0, b1 + 1):
        for x in range(x0, x1 + 1):
            L.put(x, y, R, 4 if x == x0 and sd == 'l' else 2 if x == x1 else 3)
    if k == 2:
        L.rect(x0, b0 + 2, x1, b0 + 2, R, 2)
        L.put(x0 + 1, b0 + 1, GOLD, 4)


def bandages(h, R=GREYC, legs=True, arms=True):
    """Cloth wraps (ninja): bands across the forearms and shins - a lit row and a dark row."""
    k = h.k
    if arms:
        for sd in 'lr':
            if h.body.arm_mode[sd] in ('cross', 'reach', 'up'):
                continue
            L = h.L('arm_' + sd)
            x0, y0, x1, y1 = h.b['arm_' + sd]
            hy0 = h.b['hand_' + sd][1]
            for y in range(hy0 - 4 * k, hy0):
                for x in range(x0, x1 + 1):
                    L.put(x, y, R, 4 if (y - hy0) % (2 * k) == 0 else 3 if x < x1 else 2)
    if legs:
        for sd in 'lr':
            L = h.L('leg_' + sd)
            x0, y0, x1, y1 = h.b['leg_' + sd]
            for y in range(y1 - 6 * k, y1 - 2 * k + 1):
                for x in range(x0, x1 + 1):
                    L.put(x, y, R, 4 if (y - y1) % (2 * k) == 0 else 3 if x < x1 else 2)


def bell_cuffs(h, R):
    """Wide sleeves that flare at the wrist: the cuff is a step wider on both sides, its underside dark."""
    k = h.k
    for sd in 'lr':
        if h.body.arm_mode[sd] in ('cross', 'reach', 'up'):
            continue
        L = h.L('arm_' + sd)
        x0, y0, x1, y1 = h.b['arm_' + sd]
        hy0 = h.b['hand_' + sd][1]
        for y in range(hy0 - 3 * k, hy0 + k):
            for x in range(x0 - k, x1 + k + 1):
                t = 3
                if x == x0 - k:
                    t = 4
                if x >= x1 + k - (k - 1):
                    t = 2
                if y >= hy0:
                    t = 1 if x > x0 - k else 2
                L.put(x, y, R, t)


def robe_stars(h, M=GOLD, seed=3):
    """Stars and a crescent moon scattered on a robe (k=1: single gold glints; k=2: little 5 px stars)."""
    k = h.k
    L = h.L('chest')
    x0, y0, x1, y1 = h.b['torso']
    spots = [(1, 7), (6, 3), (2, 15), (6, 18), (4, 11)]
    for (sx, sy) in spots:
        x, y = x0 + sx * k, y0 + sy * k
        if k == 1:
            L.put(x, y, M, 4)
        else:
            for (dx, dy, t) in ((0, 0, 5), (-1, 0, 4), (1, 0, 3), (0, -1, 4), (0, 1, 3)):
                L.put(x + dx, y + dy, M, t)
    if k == 2:
        mx, my = x0 + 10, y0 + 28
        for (dx, dy) in ((0, 0), (1, -1), (2, -1), (0, 1), (0, 2), (1, 3), (2, 3), (-1, 1), (-1, 2)):
            L.put(mx + dx, my + dy, M, 4 if dx <= 0 else 3)


def zombie_face(h):
    """Sunken dark eye sockets with a dull glint, a gaping mouth with a tooth, rot patches as clusters."""
    k = h.k
    S = h.m('skin')
    L = h.L('face')
    x0, y0, x1, y1 = h.b['head']
    f = h.fs
    if k == 1:
        ey = y0 + 3
        for x in (x0 + 1 + f, x0 + 2 + f, x0 + 5 + f, x0 + 6 + f):
            L.put(x, ey + 1, S, 0)
            L.put(x, ey, S, 2)
        L.put(x0 + 2 + f, ey + 1, YELLOW, 1)
        L.put(x0 + 5 + f, ey + 1, YELLOW, 1)
        L.rect(x0 + 2 + f, y0 + 6, x0 + 5 + f, y0 + 6, S, 0)
        L.put(x0 + 3 + f, y0 + 6, BONE, 3)
        L.put(x0 + 6, y0 + 1, S, 2)
        L.put(x0 + 6, y0 + 2, S, 2)
        return
    ey = y0 + 6
    for ox in (x0 + 2 + f, x0 + 10 + f):
        L.rect(ox, ey, ox + 3, ey, S, 2)
        L.rect(ox, ey + 1, ox + 3, ey + 3, S, 0)
        L.put(ox + (2 if ox < x0 + 8 else 1), ey + 2, YELLOW, 2)
        L.rect(ox, ey + 4, ox + 3, ey + 4, S, 2)
    L.put(x0 + 7 + f, ey + 5, S, 1)
    L.put(x0 + 8 + f, ey + 5, S, 1)
    my = y0 + 12
    L.rect(x0 + 4 + f, my, x0 + 11 + f, my + 2, S, 0)
    L.rect(x0 + 5 + f, my + 2, x0 + 10 + f, my + 2, CRIMSON, 1)
    L.put(x0 + 5 + f, my, BONE, 4)
    L.put(x0 + 9 + f, my, BONE, 3)
    L.put(x0 + 9 + f, my + 1, BONE, 2)
    for (x, y) in ((12, 1), (13, 1), (13, 2), (2, 13), (2, 14), (3, 14), (14, 12), (14, 13)):
        L.put(x0 + x, y0 + y, S, 2)
    for (x, y) in ((11, 2), (12, 3)):
        L.put(x0 + x, y0 + y, S, 4)


def torn(h, layer, box, S, n=3, seed=1):
    """Holes in cloth showing the skin under it (2x2 clusters with a dark top-left rim)."""
    k = h.k
    L = h.L(layer)
    x0, y0, x1, y1 = box
    rnd = random.Random(seed * 7 + k)
    for _ in range(n):
        x = rnd.randint(x0 + k, max(x0 + k, x1 - 2 * k))
        y = rnd.randint(y0 + 2 * k, max(y0 + 2 * k, y1 - 2 * k))
        for dx in range(k + 1):
            for dy in range(k + 1):
                L.put(x + dx, y + dy, S, 3 if dx or dy else 2)
        L.put(x - 1, y, L.ramp(x - 1, y) or S, 1)


def ragged_hem(h, layer, box, R, below=1):
    """A torn hem: every few pixels a tongue of cloth hangs one or two px lower."""
    k = h.k
    L = h.L(layer)
    x0, y0, x1, y1 = box
    for x in range(x0, x1 + 1):
        d = (x * 5) % 7
        n = (below * k if d < 3 else 0) + (k if d == 0 else 0)
        for j in range(1, n + 1):
            L.put(x, y1 + j, R, 2 if j == n else 3)


def skull_face(h):
    """A skull: dark eye sockets with a faint glint, the nose hole, a row of teeth."""
    k = h.k
    B = h.m('skin')
    L = h.L('face')
    x0, y0, x1, y1 = h.b['head']
    f = h.fs
    if k == 1:
        for ox in (x0 + 1 + f, x0 + 5 + f):
            L.rect(ox, y0 + 3, ox + 1, y0 + 4, B, 0)
        L.put(x0 + 2 + f, y0 + 3, B, 1)
        L.put(x0 + 6 + f, y0 + 3, B, 1)
        L.put(x0 + 3 + f, y0 + 5, B, 0)
        L.put(x0 + 4 + f, y0 + 5, B, 1)
        for x in range(x0 + 1 + f, x0 + 7 + f):
            L.put(x, y0 + 6, B, 4 if x % 2 == 0 else 1)
        L.rect(x0 + 1, y0 + 7, x0 + 6, y0 + 7, B, 2)
        return
    for ox in (x0 + 2 + f, x0 + 10 + f):
        L.rect(ox, y0 + 6, ox + 3, y0 + 9, B, 0)
        L.rect(ox, y0 + 5, ox + 3, y0 + 5, B, 2)
        L.put(ox + 1, y0 + 7, B, 2)
    L.rect(x0 + 7 + f, y0 + 10, x0 + 8 + f, y0 + 11, B, 0)
    L.put(x0 + 7 + f, y0 + 10, B, 1)
    L.rect(x0 + 2, y0 + 12, x0 + 13, y0 + 12, B, 1)
    for x in range(x0 + 3 + f, x0 + 13 + f):
        L.put(x, y0 + 13, B, 4 if (x - x0) % 2 else 1)
        L.put(x, y0 + 14, B, 3 if (x - x0) % 2 else 1)
    L.rect(x0 + 2, y0 + 15, x0 + 13, y0 + 15, B, 2)
    L.rect(x0 + 1, y0 + 2, x0 + 4, y0 + 2, B, 5)


def p_ribcage(h):
    """A skeleton's torso: collarbones, a spine down the middle, ribs with dark gaps (the outline fills the
    gaps with the bone's darkest tone, which reads as the hollow), a pelvis."""
    k = h.k
    B = h.m('skin')
    L = h.L('torso')
    x0, y0, x1, y1 = h.b['torso']
    cx = (x0 + x1 + 1) // 2
    for x in range(x0, x1 + 1):
        for j in range(k):
            L.put(x, y0 + j, B, 4 if j == 0 and x < x1 else 2)
    for y in range(y0, y1 + 1):
        for x in range(cx - k, cx + k):
            L.put(x, y, B, 4 if x == cx - k else 2 if x == cx + k - 1 else 3)
    for r in range(3):
        ry = y0 + (2 + 2 * r) * k
        for x in range(x0 + (k if r == 2 else 0), x1 + 1 - (k if r == 2 else 0)):
            for j in range(k):
                L.put(x, ry + j, B, (4 if x < cx else 3) if j == 0 else 2)
        if k == 2:
            L.put(x0 + (2 if r == 2 else 0), ry + 1, B, 1)
    py = y1 - 2 * k + 1
    for x in range(x0, x1 + 1):
        for j in range(2 * k):
            if j == 2 * k - 1 and cx - k <= x < cx + k:
                continue
            L.put(x, py + j, B, 4 if j == 0 and x < x1 else 2 if x > cx + k else 3)


def p_bones(h):
    """Thin bone limbs: lit left column, dark right, joints as a lit knob with a dark line under it."""
    k = h.k
    B = h.m('skin')
    for sd in 'lr':
        for part in ('arm_', 'leg_'):
            mode = h.body.arm_mode[sd] if part == 'arm_' else 'down'
            L = h.L(part + sd)
            x0, y0, x1, y1 = h.b[part + sd]
            for y in range(y0, y1 + 1):
                for x in range(x0, x1 + 1):
                    L.put(x, y, B, 4 if x == x0 else 2 if x == x1 else 3)
            jy = (y0 + y1) // 2
            for x in range(x0, x1 + 1):
                L.put(x, jy, B, 5 if x == x0 else 4)
                L.put(x, jy + 1, B, 1 if x > x0 else 2)
            if k == 2:
                L.put(x0 - 1, jy, B, 4)
                L.put(x1 + 1, jy, B, 2)
            if part == 'arm_' and mode != 'up':
                for x in range(x0, x1 + 1):
                    L.put(x, y0, B, 4 if x == x0 else 3)
        F = h.L('foot_' + sd)
        x0, y0, x1, y1 = h.b['foot_' + sd]
        for x in range(x0 - (k if sd == 'l' else 0), x1 + 1 + (k if sd == 'r' else 0)):
            for y in range(y1 - k + 1, y1 + 1):
                F.put(x, y, B, 4 if y == y1 - k + 1 and x < x1 else 2)


def ender_eyes(h):
    """Glowing eye slits: a bright core, lighter ends, a dim glow line under them (all opaque)."""
    k = h.k
    G = ENDER_EYE
    L = h.L('face')
    x0, y0, x1, y1 = h.b['head']
    ey = y0 + 4 * k
    f = h.fs
    for (a, b_) in ((x0 + f, x0 + 3 * k - 1 + f), (x1 - 3 * k + 1 + f, x1 + f)):
        for x in range(max(x0, a), min(x1, b_) + 1):
            for j in range(k):
                core = (x - a) in range(k // 2 + (1 if k == 1 else 0), 2 * k + (0 if k == 1 else 0))
                L.put(x, ey + j, G, 5 if core else 4)
            if k == 2:
                L.put(x, ey - 1, G, 2)
                L.put(x, ey + 2, G, 1)


def particles(h, R=ENDER_EYE, n=6, spread=(10, 30), seed=3):
    """A few floating particles round a figure: 1 px (k=2: 2x2 with a lit corner) free pixels, no outline."""
    k = h.k
    L = h.L('fx', line=False)
    rnd = random.Random(seed)
    cx = h.body.cx
    gy = h.body.ground
    for i in range(n):
        x = cx + rnd.choice((-1, 1)) * rnd.randint(spread[0] // 2, spread[0]) * k // 1
        y = gy - rnd.randint(4, spread[1]) * k
        if k == 1:
            L.put(x, y, R, 4 if i % 2 else 3, free=True)
        else:
            L.put(x, y, R, 5, free=True)
            L.put(x + 1, y, R, 3, free=True)
            L.put(x, y + 1, R, 3, free=True)
            L.put(x + 1, y + 1, R, 2, free=True)


# ------------------------------------------------------------------ looks
def look_defaults(look):
    out = dict(kind='player', skin=SKIN_FAIR, hair=HAIR_BROWN, eye=IRIS_BROWN, top=RED, bottom=DENIM,
               shoes=WHITEC, hair_style='short', seed=7)
    out.update(look)
    return out


def build_humanoid(look, k=1, pose=None, frame=0, facing='front', held='default', held_mat=None, shadow=True,
                   **opts):
    look = look_defaults(look)
    for slot in ('skin', 'hair', 'top', 'bottom', 'shoes', 'eye', 'accent'):
        if opts.get(slot) is not None:
            look[slot] = ramp_of(opts.pop(slot))
    pose = pose or look.get('pose', 'idle')
    crossed = look.get('pose') == 'cross' and pose in ('cross', 'walk') and held in ('default', None)
    if held == 'default':                                   # the look's own item; crossed arms hold nothing
        held = look.get('held') if pose != 'cross' and not crossed else None
    look = dict(look, walk_cross=crossed and pose == 'walk')
    if pose == 'cross' and held:
        pose = 'hold'
    h = H(k, look, pose, frame, facing, held, held_mat or look.get('held_mat'), shadow, opts)
    for painter in look['paint']:
        painter(h)
    if held:
        draw_item(h, held)
    return h.fig.finish()


def player_look():
    def paint(h):
        p_shadow(h)
        p_legs(h, style='jeans')
        p_feet(h, style='sneaker')
        p_torso_shirt(h, style='hoodie')
        p_hood(h)
        p_arms(h)
        p_hands(h)
        p_head(h)
        p_face_player(h)
        p_hair(h)
    return dict(kind='player', skin=SKIN_FAIR, hair=HAIR_BROWN, eye=IRIS_GREEN, top=RED, bottom=DENIM, shoes=WHITEC,
                hair_style='swept', paint=[paint])


def knight():
    def paint(h):
        p_shadow(h)
        p_plate_legs(h, IRON)
        p_plate_feet(h, STEEL)
        p_plate_torso(h, IRON)
        tabard(h, RED, top=2, below=4, trim=GOLD, emblem=GOLD)
        belt(h, DLEATHER, GOLD)
        p_plate_arms(h, IRON)
        p_hands(h)
        if h.opts.get('shield', True):
            shield(h, 'l' if h.side == 'r' else 'r', BLUE, GOLD, CREAM)
        p_head(h)
        great_helm(h, IRON, RED if h.opts.get('plume', True) else None)
    return dict(kind='player', skin=SKIN_FAIR, top=RED, glove=STEEL, held='sword', paint=[paint], shadow_w=1)


def guard():
    def paint(h):
        p_shadow(h)
        p_legs(h, GREYC)
        p_boots(h, DLEATHER, height=4)
        chainmail(h.L('torso'), h.b['torso'], CHAIN, h.k)
        tabard(h, BLUE, top=2, below=3, trim=None, emblem=YELLOW, w=2)
        belt(h, DLEATHER, IRON)
        for sd in 'lr':
            if h.body.arm_mode[sd] in ('down', 'hold'):
                x0, y0, x1, y1 = h.b['arm_' + sd]
                hy0 = h.b['hand_' + sd][1]
                chainmail(h.L('arm_' + sd), (x0, y0, x1, hy0 - 1), CHAIN, h.k, lit_l=sd == 'l')
            elif h.body.arm_mode[sd] == 'up':
                x0, y0, x1, y1 = h.b['arm_' + sd]
                hy1 = h.b['hand_' + sd][3]
                chainmail(h.L('arm_' + sd), (x0, hy1 + 1, x1, y1), CHAIN, h.k, lit_l=sd == 'l')
        p_hands(h)
        p_head(h)
        p_face_player(h, mouth='flat')
        p_hair(h, 'short')
        p_beard(h, style='none', mustache=True)
        kettle_helm(h, IRON)
    return dict(kind='player', skin=SKIN_TAN, hair=HAIR_DARK, eye=IRIS_BROWN, glove=DLEATHER, held='spear',
                paint=[paint])


def wizard():
    def paint(h):
        p_shadow(h)
        p_villager_legs(h, R=NAVY, S=DLEATHER)
        p_robe(h, NAVY, flare=True, folds=True, collar=False)
        robe_stars(h, GOLD)
        p_arms(h, NAVY, sleeve='long', folds=False)
        bell_cuffs(h, NAVY)
        p_hands(h)
        p_head(h)
        p_face_player(h, blush=False, mouth=None)
        p_hair(h, 'beardless_old')
        p_beard(h, HAIR_WHITE, length=9, style='long')
        pointy_hat(h, BLUE, band=GOLD, tip=1, brim=2, height=11, emblem=YELLOW)
    return dict(kind='player', skin=SKIN_FAIR, hair=HAIR_WHITE, eye=IRIS_BLUE, held='staff', gem=SAPPHIRE,
                paint=[paint], shadow_w=1)


def miner():
    def paint(h):
        p_shadow(h)
        p_legs(h, DENIM, style='jeans')
        p_boots(h, DLEATHER, height=3)
        p_torso_shirt(h, GREYC, folds=False)
        overalls(h, DENIM, GOLD)
        p_arms(h, GREYC, sleeve='long')
        p_hands(h)
        p_head(h)
        p_face_player(h, mouth='flat', blush=False)
        p_hair(h, 'short')
        p_beard(h, style='none', mustache=True)
        if h.k == 2:
            F = h.L('face')
            x0, y0 = h.b['head'][:2]
            for (x, y) in ((2, 12), (3, 12), (3, 13)):
                F.put(x0 + x, y0 + y, h.m('skin'), 2)         # a smudge of dust
        hard_hat(h, YELLOW, lamp=True)
    return dict(kind='player', skin=SKIN_FAIR, hair=HAIR_BROWN, eye=IRIS_BLUE, held='pickaxe', paint=[paint])


def witch():
    def paint(h):
        p_shadow(h)
        hair_back(h, h.m('hair'), length=6)
        p_villager_legs(h, R=PLUM, S=BLACKC)
        p_robe(h, PLUM, flare=True, folds=True, collar=False)
        k = h.k
        L = h.L('chest')
        x0, y0, x1, y1 = h.b['torso']
        cx = (x0 + x1 + 1) // 2
        for y in range(y0 + 3 * k, y1 + 1):                 # laced bodice
            for x in range(x0 + k, x1 - k + 1):
                L.put(x, y, PURPLE, 4 if x == x0 + k else 2 if x == x1 - k else 3)
            if (y - y0) % (2 * k) == 0:
                L.put(cx - 1, y, CREAM, 4)
                L.put(cx, y, CREAM, 3)
                if k == 2:
                    L.put(cx - 2, y + 1, CREAM, 3)
                    L.put(cx + 1, y + 1, CREAM, 2)
        belt(h, BLACKC, GOLD)
        ragged_hem(h, 'torso', (x0 - k, y0, x1 + k, h.body.ground - 3 * k - 1), PLUM, below=1)
        p_arms(h, PLUM, sleeve='long', folds=False)
        bell_cuffs(h, PLUM)
        p_hands(h)
        p_head(h)
        p_face_player(h, mouth='smile', blush=False)
        F = h.L('face')
        x0h, y0h, x1h, y1h = h.b['head']
        if k == 2:
            F.put(x0h + 7 + h.fs, y0h + 12, h.m('skin'), 3)    # a longer nose and a wart
            F.put(x0h + 8 + h.fs, y0h + 12, h.m('skin'), 2)
            F.put(x0h + 9 + h.fs, y0h + 11, GREEN, 3)
        p_hair(h, 'long')
        pointy_hat(h, BLACKC, band=PURPLE, tip=-1, brim=3, height=11, buckle=GOLD)
    return dict(kind='slim', skin=SKIN_LIGHT, hair=HAIR_GINGER, eye=IRIS_GREEN, held='potion', paint=[paint],
                shadow_w=1)


def pirate():
    def paint(h):
        p_shadow(h)
        p_legs(h, BROWN)
        p_boots(h, DLEATHER, height=5)
        p_torso_shirt(h, WHITEC, folds=False)
        stripes(h, WHITEC, NAVY, every=2)
        coat(h, CRIMSON, GOLD, tails=6, open_w=2)
        belt(h, BLACKC, GOLD, h_=1)
        p_arms(h, CRIMSON, sleeve='long')
        for sd in 'lr':
            if h.body.arm_mode[sd] in ('down', 'hold', 'up'):
                x0, y0, x1, y1 = h.b['arm_' + sd]
                hx0, hy0, hx1, hy1 = h.b['hand_' + sd]
                cy = hy0 - 2 * h.k if h.body.arm_mode[sd] != 'up' else hy1 + 1
                h.L('arm_' + sd).rect(x0, cy, x1, cy + 2 * h.k - 1, GOLD, 3)
                h.L('arm_' + sd).rect(x0, cy, x1, cy, GOLD, 4)
        p_hands(h)
        p_head(h)
        p_face_player(h, mouth='flat', blush=False)
        p_hair(h, 'short')
        p_beard(h, length=1, style='full')
        eyepatch(h)
        tricorn(h, BLACKC, GOLD, BONE)
    return dict(kind='player', skin=SKIN_TAN, hair=HAIR_GINGER, eye=IRIS_BROWN, held='sword', paint=[paint])


def king():
    def paint(h):
        p_shadow(h)
        if h.opts.get('cape', True):
            cape_back(h, CRIMSON, spread=2)
        p_legs(h, NAVY)
        p_boots(h, DLEATHER, height=3)
        p_torso_shirt(h, BLUE, folds=True)
        L = h.L('chest')
        x0, y0, x1, y1 = h.b['torso']
        k = h.k
        for x in range(x0, x1 + 1):                         # tunic skirt over the thighs with a gold hem
            for y in range(y1 + 1, y1 + 3 * k + 1):
                L.put(x, y, BLUE, 4 if x == x0 else 2 if x == x1 else 3)
            for j in range(k):
                L.put(x, y1 + 3 * k - j, GOLD, 3 if j else 2)
        buttons(h, GOLD, 2)
        belt(h, GOLD, RUBY)
        p_arms(h, BLUE, sleeve='long')
        p_hands(h)
        if h.opts.get('cape', True):
            ermine(h)
        p_head(h)
        p_face_player(h, mouth=None, blush=False)
        p_hair(h, 'short')
        p_beard(h, length=3, style='full')
        crown(h)
    return dict(kind='player', skin=SKIN_FAIR, hair=HAIR_GREY, eye=IRIS_BLUE, held='scepter', paint=[paint],
                shadow_w=2)


def princess():
    def paint(h):
        p_shadow(h)
        hair_back(h, h.m('hair'), length=8)
        p_villager_legs(h, R=PINK, S=PINK)
        k = h.k
        p_torso_shirt(h, PINK, folds=False)
        L = h.L('torso')
        x0, y0, x1, y1 = h.b['torso']
        cx = (x0 + x1 + 1) // 2
        for y in range(y0 + 2 * k, y1 + 1):                 # bodice panel
            for x in range(cx - 2 * k, cx + 2 * k):
                L.put(x, y, PINK, 4 if x < cx else 3)
        for x in range(x0 + k, x1 - k + 1):
            L.put(x, y0 + k, WHITEC, 4 if x < cx else 3)    # lace neckline
        p_dress(h, PINK, steps=3, step_h=3, hem=WHITEC, folds=True)
        p_arms(h, PINK, sleeve='short', folds=False)
        for sd in 'lr':                                     # puffed sleeves
            if h.body.arm_mode[sd] in ('down', 'hold'):
                A = h.L('arm_' + sd)
                ax0, ay0, ax1, ay1 = h.b['arm_' + sd]
                for y in range(ay0, ay0 + 4 * k):
                    for x in range(ax0 - (k if sd == 'l' else 0), ax1 + 1 + (k if sd == 'r' else 0)):
                        t = 4 if y < ay0 + k or (sd == 'l' and x == ax0 - k) else 3
                        if y == ay0 + 4 * k - 1:
                            t = 2
                        if sd == 'r' and x == ax1 + k:
                            t = 2
                        A.put(x, y, PINK, t)
        p_hands(h)
        p_head(h)
        p_face_player(h, blush=True, mouth='smile')
        p_hair(h, 'long')
        hair_front_locks(h, h.m('hair'), length=5)
        tiara(h)
    return dict(kind='slim', skin=SKIN_LIGHT, hair=HAIR_BLONDE, eye=IRIS_BLUE, held=None, paint=[paint],
                shadow_w=2)


def ninja():
    def paint(h):
        p_shadow(h)
        katana_back(h)
        p_legs(h, BLACKC)
        p_feet(h, BLACKC)
        p_torso_shirt(h, BLACKC, folds=False)
        L = h.L('torso')
        x0, y0, x1, y1 = h.b['torso']
        k = h.k
        cx = (x0 + x1 + 1) // 2
        for i in range(4 * k):                              # the crossed collar
            L.put(x0 + k + i, y0 + i, BLACKC, 4)
            if x1 - k - i > cx:
                L.put(x1 - k - i, y0 + i, BLACKC, 2)
        belt(h, RED, None, h_=2 if k == 1 else 1)
        p_arms(h, BLACKC, sleeve='long')
        bandages(h, GREYC)
        p_hands(h)
        p_head(h)
        p_face_player(h, brows=False, mouth=None, blush=False)
        ninja_mask(h)
    return dict(kind='player', skin=SKIN_TAN, hair=HAIR_BLACK, eye=IRIS_BROWN, held=None, paint=[paint])


def archer():
    def paint(h):
        p_shadow(h)
        quiver_back(h)
        p_legs(h, BROWN)
        p_boots(h, DLEATHER, height=5)
        p_torso_shirt(h, GREEN, folds=True)
        L = h.L('chest')
        x0, y0, x1, y1 = h.b['torso']
        k = h.k
        for x in range(x0, x1 + 1):                         # tunic skirt
            for y in range(y1 + 1, y1 + 3 * k + 1):
                if y == y1 + 3 * k and (x - x0) % (2 * k) >= k:
                    continue
                L.put(x, y, GREEN, 4 if x == x0 else 2 if x == x1 else 2 if y == y1 + 3 * k else 3)
        for i in range(8 * k):                              # the quiver strap across the chest
            L.put(x0 + i, y0 + 1 + i * 10 // 8 // 1 if k == 1 else y0 + 1 + (i * 5) // 4, DLEATHER, 3)
        belt(h, DLEATHER, GOLD)
        p_arms(h, GREEN, sleeve='long')
        bracer(h, h.side)
        p_hands(h)
        p_head(h)
        p_face_player(h, mouth='flat')
        p_hair(h, 'short')
        hood(h, FOREST, trim=None)
    return dict(kind='player', skin=SKIN_FAIR, hair=HAIR_GINGER, eye=IRIS_GREEN, held='bow', paint=[paint])


def zombie():
    def paint(h):
        p_shadow(h)
        p_legs(h, GREYC)
        p_feet(h, h.m('skin'))
        for sd in 'lr':
            torn(h, 'leg_' + sd, h.b['leg_' + sd], h.m('skin'), n=1, seed=3 if sd == 'l' else 8)
            ragged_hem(h, 'leg_' + sd, h.b['leg_' + sd][:3] + (h.b['foot_' + sd][1] - 1,), GREYC, below=0)
        p_torso_shirt(h, BROWN, folds=False)
        torn(h, 'torso', h.b['torso'], h.m('skin'), n=2, seed=4)
        ragged_hem(h, 'torso', h.b['torso'], BROWN, below=1)
        p_arms(h, BROWN, sleeve='torn')
        p_hands(h)
        p_head(h)
        zombie_face(h)
        p_hair(h, 'short')
    return dict(kind='player', pose='reach', skin=ZOMBIE, hair=ZOMBIE_HAIR, held=None, paint=[paint])


def skeleton():
    def paint(h):
        p_shadow(h)
        p_bones(h)
        p_ribcage(h)
        p_hands(h)
        p_head(h)
        skull_face(h)
    return dict(kind='skinny', skin=BONE, held='bow', paint=[paint])


def ender_walker():
    def paint(h):
        p_shadow(h)
        k = h.k
        E = h.m('skin')
        for sd in 'lr':
            for part in ('arm_', 'leg_'):
                L = h.L(part + sd)
                x0, y0, x1, y1 = h.b[part + sd]
                for y in range(y0, y1 + 1):
                    for x in range(x0, x1 + 1):
                        L.put(x, y, E, 4 if x == x0 and sd == 'l' else 2 if x == x1 else 3)
        box(h.L('torso'), h.b['torso'], E, left=2, right=2, bottom=2)
        x0, y0, x1, y1 = h.b['torso']
        if k == 2:
            h.L('torso').rect(x0 + 1, y0 + 1, x0 + 1, y1 - 2, E, 4)
        p_hands(h)
        box(h.L('head'), h.b['head'], E, left=4, right=2, bottom=2, top=4)
        ender_eyes(h)
        particles(h, ENDER_EYE, n=7, spread=(10, 40), seed=5)
    return dict(kind='tall', skin=ENDER, held=None, paint=[paint])


LOOKS = {
    'player': player_look,
    'villager_farmer': villager_farmer,
    'villager_librarian': villager_librarian,
    'villager_blacksmith': villager_blacksmith,
    'villager_butcher': villager_butcher,
    'villager_cleric': villager_cleric,
    'villager_fisherman': villager_fisherman,
    'villager_cartographer': villager_cartographer,
    'villager_merchant': villager_merchant,
    'knight': knight,
    'guard': guard,
    'wizard': wizard,
    'miner': miner,
    'witch': witch,
    'pirate': pirate,
    'king': king,
    'princess': princess,
    'ninja': ninja,
    'archer': archer,
    'zombie': zombie,
    'skeleton': skeleton,
    'ender_walker': ender_walker,
}


# ------------------------------------------------------------------ animals and mobs (side view / front view)
ORDER_A = ('shadow', 'perch_back', 'tail', 'wing_far', 'leg_fb', 'leg_ff', 'body', 'spots', 'belly', 'leg_nb',
           'leg_nf', 'neck', 'mane', 'head', 'snout', 'ears', 'face', 'horns', 'gills', 'collar', 'acc', 'wing',
           'perch', 'feet', 'fx')


class A:
    """Context for a side-view animal drawn facing right in local coordinates: facing='left' mirrors the
    geometry (sx), but every shading rule works in screen space, so the light stays top-left either way."""

    def __init__(self, k, W, H, facing='right', pose='idle', frame=0, shadow=True, order=ORDER_A, **opts):
        self.k, self.W, self.H = k, W * k, H * k
        self.flip = facing == 'left'
        self.pose, self.frame, self.shadow, self.opts = pose, frame % 4, shadow, opts
        self.fig = Fig(k, self.W, self.H, order)
        self.walk = pose == 'walk'

    def sx(self, x):
        return self.W - 1 - x if self.flip else x

    def L(self, name, **kw):
        return self.fig(name, **kw)

    def put(self, L, x, y, r, t, free=False):
        L.put(self.sx(x), y, r, t, free)

    def rect(self, L, x0, y0, x1, y1, r, t, free=False):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.put(L, x, y, r, t, free)

    def box(self, L, x0, y0, x1, y1, r, top=4, bottom=2, left=4, right=2, base=3):
        """Local box, shaded in screen space: top row lit, bottom row dark, screen-left column lit."""
        a, b = sorted((self.sx(x0), self.sx(x1)))
        for y in range(y0, y1 + 1):
            for x in range(a, b + 1):
                t = base
                if x == b and right is not None:
                    t = right
                if x == a and left is not None:
                    t = left
                if y == y0 and top is not None:
                    t = top
                if y == y1 and bottom is not None:
                    t = bottom
                L.put(x, y, r, t)

    def shade_pts(self, L, pts, r, top=4, bottom=2, left=4, right=2, base=3):
        """Shade any local set of pixels like a box: edges facing up / screen-left lit, down / right dark."""
        sp = {(self.sx(x), y) for (x, y) in pts}
        for (x, y) in sp:
            t = base
            if (x + 1, y) not in sp and right is not None:
                t = right
            if (x - 1, y) not in sp and left is not None:
                t = left
            if (x, y - 1) not in sp and top is not None:
                t = top
            if (x, y + 1) not in sp and bottom is not None:
                t = bottom
            L.put(x, y, r, t)

    def shade_layer(self, L, r, top=4, bottom=2, left=None, right=None):
        """Re-shade the pixels of ramp r on layer L by their own mask (screen space): patches get a lit top
        edge and a dark lower edge (spots, socks, saddles)."""
        m = {p for p, v in L.px.items() if v[0] is r}
        for (x, y) in m:
            t = L.px[(x, y)][1]
            if (x, y + 1) not in m and bottom is not None:
                t = bottom
            if (x, y - 1) not in m and top is not None:
                t = top
            if left is not None and (x - 1, y) not in m:
                t = left
            if right is not None and (x + 1, y) not in m:
                t = right
            L.put(x, y, r, t)

    def tone(self, L, x, y, t, r=None):
        p = (self.sx(x), y)
        if p in L.px:
            L.put(p[0], p[1], r or L.px[p][0], t)

    def leg_motion(self, which):
        """(swing, lift) for leg `which` in nf / nb / ff / fb (near / far, front / back) at this walk frame.
        Pairs move together: near-front with far-back, near-back with far-front."""
        if not self.walk:
            return 0, 0
        a = which in ('nf', 'fb')
        f = self.frame
        if f == 0:
            return (2 if a else -2), 0
        if f == 2:
            return (-2 if a else 2), 0
        if f == 1:
            return 0, (1 if a else 0)
        return 0, (0 if a else 1)

    def leg(self, which, x, y, w, h, r, hoof=None, hoof_h=1, sock=None, sock_h=0):
        """A leg from the hip (x, y) w x h (skin px): sheared by the walk swing, shortened by a lift, a hoof /
        sock at the bottom; far legs are one step darker and drawn behind the body."""
        k = self.k
        L = self.L('leg_' + which)
        sw, lift = self.leg_motion(which)
        far = which[0] == 'f'
        H_ = (h - lift) * k
        for j in range(H_):
            off = int(round(sw * k * j / max(1, H_ - 1))) if sw else 0
            yy = y + j
            for i in range(w * k):
                xx = x + i + off
                ramp = r
                bottom = j >= H_ - hoof_h * k
                if hoof and bottom:
                    ramp = hoof
                elif sock and j >= H_ - (sock_h + hoof_h) * k:
                    ramp = sock
                t = 3
                if i == 0:
                    t = 4
                if i == w * k - 1:
                    t = 2
                if far:
                    t = max(1, t - 1)
                if bottom and j == H_ - 1:
                    t = max(1, t - 1)
                self.put(L, xx, yy, ramp, t)
        return L

    def eye(self, L, x, y, iris=None, white=False, big=False):
        """An eye at local (x, y): dark pupil; k=2 adds a glint on its screen top-left (2x2 eye)."""
        k = self.k
        iris = iris or BLACKC
        if k == 1:
            self.put(L, x, y, iris, 0 if iris is BLACKC else 2)
            if white:
                self.put(L, x - 1, y, EYE_W, 3)
            return
        for (dx, dy) in ((0, 0), (1, 0), (0, 1), (1, 1)):
            self.put(L, x + dx, y + dy, iris, 0 if iris is BLACKC else 2)
        if big:
            self.put(L, x - 1, y, iris, 0 if iris is BLACKC else 2)
            self.put(L, x - 1, y + 1, iris, 0 if iris is BLACKC else 2)
        gx = min(self.sx(x), self.sx(x + 1))             # the glint: screen top-left of the eye
        L.put(gx, y, EYE_W, 5)
        if white:
            self.put(L, x - 1, y, EYE_W, 3)
            self.put(L, x - 1, y + 1, EYE_W, 3)

    def fur(self, L, pts, r, n, seed=1, length=(2, 3), up=4, down=2):
        """Fur / feather texture: n short horizontal streaks (2-3 px), lit ones on the upper half, dark ones
        lower - clusters, never single pixels, kept off the edges."""
        rnd = random.Random(seed * 13 + self.k)
        pts = set(pts)
        ys = [y for _, y in pts]
        if not ys:
            return
        mid = (min(ys) + max(ys)) / 2
        cand = sorted(p for p in pts if all((p[0] + dx, p[1] + dy) in pts for dx, dy in N4))
        used = set()
        tries = 0
        while n > 0 and cand and tries < 300:
            tries += 1
            x, y = cand[rnd.randrange(len(cand))]
            ln = rnd.randint(*length)
            run = [(x + i, y) for i in range(ln)]
            if not all(q in pts and all((q[0] + dx, q[1] + dy) in pts for dx, dy in N4) for q in run):
                continue
            if any((q[0] + dx, q[1] + dy) in used for q in run for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                continue
            t = up if y < mid else down
            for q in run:
                self.put(L, q[0], q[1], r, t)
            used.update(run)
            n -= 1

    def ground(self, cx, gy, rx, ry=None):
        if self.shadow:
            ground_shadow(self.fig, self.sx(cx) + (0 if not self.flip else 1), gy, rx, ry)

    def finish(self):
        return self.fig.finish()


def _walk_bob(a):
    return -a.k if a.walk and a.frame in (1, 3) else 0


def cow(k=1, facing='right', pose='idle', frame=0, shadow=True, **o):
    """Cow: a long brown body with white patches, a head with a pale muzzle, horns, a pink udder, a tail with
    a tuft, hooves."""
    a = A(k, 34, 30, facing, pose, frame, shadow, **o)
    ox, oy = 4 * k, 4 * k
    B, W_ = COW, COW_W
    gy = oy + 24 * k
    a.ground(ox + 13 * k, gy, 13 * k, 1.3 * k + 0.3)
    for which, lx in (('fb', 4), ('ff', 16), ('nb', 2), ('nf', 14)):
        a.leg(which, ox + lx * k, oy + 15 * k, 3, 9, B, hoof=HOOF, hoof_h=2 if k == 2 else 1)
    L = a.L('body')
    a.box(L, ox, oy + 5 * k, ox + 18 * k - 1, oy + 15 * k - 1, B)
    if k == 2:
        a.rect(L, ox + 2, oy + 11, ox + 33, oy + 11, B, 4)       # the back's lit ridge
        a.rect(L, ox + 1, oy + 27, ox + 34, oy + 28, B, 2)
    S = a.L('spots')
    for (x0, y0, w, h) in ((3, 7, 5, 4), (5, 6, 2, 1), (10, 10, 4, 4), (11, 9, 2, 1), (14, 6, 3, 2)):
        for y in range(y0, y0 + h):
            for x in range(x0, x0 + w):
                if (x == x0 or x == x0 + w - 1) and (y == y0 + h - 1) and w > 2:
                    continue
                for i in range(k):
                    for j in range(k):
                        a.put(S, ox + x * k + i, oy + y * k + j, W_, 3)
    a.shade_layer(S, W_, top=4, bottom=2)
    U = a.L('belly')
    a.rect(U, ox + 9 * k, oy + 15 * k, ox + 11 * k - 1 + k, oy + 16 * k + (k - 1), NOSE_P, 3)
    a.put(U, ox + 9 * k, oy + 15 * k, NOSE_P, 4)
    if k == 2:
        for x in (ox + 18, ox + 21, ox + 24):
            a.put(U, x, oy + 33, NOSE_P, 2)                  # teats
        for which in ('nb', 'nf', 'fb', 'ff'):               # split hooves
            Lg = a.L('leg_' + which)
            xs = sorted({x for (x, y) in Lg.px if y == max(yy for _, yy in Lg.px)})
            if xs:
                Lg.put(xs[len(xs) // 2], max(yy for _, yy in Lg.px), HOOF, 0)
                Lg.put(xs[len(xs) // 2], max(yy for _, yy in Lg.px) - 1, HOOF, 1)
    T = a.L('tail')
    for j in range(8 * k):
        a.put(T, ox - k + (0 if j < 5 * k else 0), oy + 6 * k + j, B, 3 if j % 3 else 2)
    a.rect(T, ox - 2 * k, oy + 13 * k, ox - 1, oy + 15 * k, BLACKC, 3)
    a.put(T, ox - 2 * k, oy + 13 * k, BLACKC, 4)
    if k == 2:
        a.put(T, ox - 3, oy + 27, BLACKC, 4)
        a.put(T, ox - 1, oy + 31, BLACKC, 2)
    H_ = a.L('head', own=True)
    hx, hy = ox + 17 * k, oy + 2 * k + _walk_bob(a)
    a.box(H_, hx, hy, hx + 7 * k - 1, hy + 8 * k - 1, B)
    for y in range(hy, hy + 5 * k):                          # white blaze down the face
        for x in range(hx + 4 * k, hx + 5 * k):
            a.put(H_, x, y, W_, 4 if y == hy else 3)
    M = a.L('snout')
    a.box(M, hx + 4 * k, hy + 5 * k, hx + 7 * k + (k - 1), hy + 8 * k - 1, HORN, top=4, bottom=2)
    a.put(M, hx + 7 * k + (k - 1), hy + 6 * k, BLACKC, 1)
    if k == 2:
        a.put(M, hx + 14, hy + 13, BLACKC, 1)
        a.rect(M, hx + 8, hy + 15, hx + 13, hy + 15, HORN, 1)
    F = a.L('face')
    a.eye(F, hx + 3 * k, hy + 3 * k)
    E = a.L('ears')
    a.box(E, hx - 2 * k, hy + 2 * k, hx - 1, hy + 3 * k - 1, B, top=3, bottom=2)
    if k == 2:
        a.put(E, hx - 3, hy + 5, NOSE_P, 3)
        a.put(E, hx - 2, hy + 5, NOSE_P, 2)
    Hn = a.L('horns')
    for (x, y) in ((0, -1), (1, -1), (1, -2)):
        for i in range(k):
            for j in range(k):
                a.put(Hn, hx + x * k + i, hy + y * k + j, HORN, 4 if y == -2 else 3)
    for (x, y) in ((4, -1), (5, -1), (5, -2)):
        for i in range(k):
            for j in range(k):
                a.put(Hn, hx + x * k + i, hy + y * k + j, HORN, 2 if y == -1 else 3)
    if k == 2:
        a.fur(L, {(x, y) for x in range(ox + 2, ox + 34) for y in range(oy + 12, oy + 28)}, B, 6, seed=2)
    return a.finish()


def pig(k=1, facing='right', pose='idle', frame=0, shadow=True, **o):
    """Pig: a round pink body, a box snout with nostrils, floppy ears, a curly tail, darker trotters."""
    a = A(k, 30, 24, facing, pose, frame, shadow, **o)
    ox, oy = 4 * k, 4 * k
    R = PIG
    gy = oy + 18 * k
    a.ground(ox + 10 * k, gy, 11 * k, 1.2 * k + 0.3)
    for which, lx in (('fb', 3), ('ff', 13), ('nb', 1), ('nf', 11)):
        a.leg(which, ox + lx * k, oy + 13 * k, 3, 5, R, hoof=PIG_HOOF, hoof_h=1)
    L = a.L('body')
    body = {(x, y) for x in range(ox, ox + 15 * k) for y in range(oy + 5 * k, oy + 13 * k)}
    body -= {(ox, oy + 5 * k), (ox + 15 * k - 1, oy + 5 * k), (ox, oy + 13 * k - 1)}
    if k == 2:
        body -= {(ox + 1, oy + 10), (ox, oy + 11), (ox, oy + 25), (ox + 1, oy + 25), (ox + 29, oy + 10)}
    a.shade_pts(L, body, R)
    if k == 2:
        a.rect(L, ox + 3, oy + 11, ox + 26, oy + 11, R, 4)
        a.fur(L, body, R, 4, seed=3, up=4, down=2)
        for (x, y) in ((6, 21), (7, 21), (7, 22)):           # a little mud
            a.put(L, ox + x, oy + y, MUD, 3)
    T = a.L('tail')
    for (x, y, t) in ((-1, 6, 3), (-2, 6, 4), (-2, 5, 3), (-1, 4, 3), (-2, 4, 2)):
        for i in range(k):
            for j in range(k):
                a.put(T, ox + x * k + i, oy + y * k + j, R, t)
    H_ = a.L('head', own=True)
    hx, hy = ox + 14 * k, oy + 3 * k + _walk_bob(a)
    a.box(H_, hx, hy, hx + 7 * k - 1, hy + 7 * k - 1, R)
    M = a.L('snout')
    a.box(M, hx + 7 * k, hy + 3 * k, hx + 9 * k - 1, hy + 6 * k - 1, NOSE_P, top=4, bottom=2)
    a.put(M, hx + 8 * k + (k - 1), hy + 4 * k, NOSE_P, 0)
    if k == 2:
        a.put(M, hx + 17, hy + 9, NOSE_P, 0)
        a.put(M, hx + 17, hy + 10, NOSE_P, 1)
    F = a.L('face')
    a.eye(F, hx + 4 * k, hy + 2 * k)
    if k == 2:
        a.rect(F, hx + 9, hy + 13, hx + 12, hy + 13, R, 1)     # smile
    E = a.L('ears')
    a.box(E, hx + k, hy - k, hx + 3 * k - 1, hy + k - 1, R, top=4, bottom=2)
    a.box(E, hx + 3 * k, hy, hx + 4 * k - 1, hy + 2 * k - 1, R, top=3, bottom=1)
    return a.finish()


def _wool(a, L, pts, R, seed=1):
    """Wool: the fleece is a cluster of round puffs - each lit on its top-left, a dark crescent at its
    bottom-right - so the texture reads curly, not noisy."""
    k = a.k
    rnd = random.Random(seed)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    step = 3 * k
    centres = []
    for cy in range(min(ys), max(ys) + 1, step):
        for cx in range(min(xs) - (cy // step % 2) * step // 2, max(xs) + 1, step):
            centres.append((cx + rnd.randint(0, k), cy + rnd.randint(0, k)))
    for (x, y) in pts:
        c = min(centres, key=lambda c: (x - c[0]) ** 2 + (y - c[1]) ** 2)
        dx, dy = x - c[0], y - c[1]
        t = 3
        if dx + dy < -k:
            t = 4
        elif dx + dy > k + (1 if k == 2 else 0):
            t = 2
        a.put(L, x, y, R, t)


def sheep(k=1, facing='right', pose='idle', frame=0, shadow=True, colour=None, **o):
    """Sheep: a puffy fleece (round puffs, lit top-left, dark crescents), a tan face with a wool cap, thin
    legs with dark hooves. colour= dyes the wool (a PALETTE name or #hex)."""
    a = A(k, 32, 26, facing, pose, frame, shadow, **o)
    ox, oy = 4 * k, 4 * k
    R = ramp_of(colour, soft=0.8) if colour else WOOL
    Fc = SHEEP_FACE
    gy = oy + 21 * k
    a.ground(ox + 11 * k, gy, 12 * k, 1.2 * k + 0.3)
    for which, lx in (('fb', 5), ('ff', 13), ('nb', 3), ('nf', 11)):
        a.leg(which, ox + lx * k, oy + 15 * k, 2, 6, Fc, hoof=HOOF)
    L = a.L('body')
    pts = set()
    for (cx, cy, rx, ry) in ((9, 10, 9, 5.5), (4, 8, 4, 3.5), (12, 7, 5, 3.5), (16, 10, 3.5, 4), (8, 13, 7, 3)):
        pts |= ell(ox + cx * k, oy + cy * k, rx * k, ry * k)
    _wool(a, L, pts, R, seed=4 + k)
    for (x, y) in pts:                                      # the underside of the fleece in shadow
        if (x, y + 1) not in pts:
            a.put(L, x, y, R, 2)
    H_ = a.L('head', own=True)
    hx, hy = ox + 16 * k, oy + 5 * k + _walk_bob(a)
    a.box(H_, hx, hy, hx + 6 * k - 1, hy + 7 * k - 1, Fc)
    if k == 2:
        a.rect(H_, hx + 9, hy + 11, hx + 11, hy + 11, Fc, 2)
    cap = ell(hx + 2.5 * k, hy, 3.4 * k, 2 * k)
    W2 = a.L('ears')
    for p in cap:
        if p[1] <= hy + k:
            a.put(W2, p[0], p[1], R, 4 if p[0] < hx + 2 * k else 3)
    a.box(W2, hx - k, hy + 2 * k, hx, hy + 3 * k - 1, Fc, top=3, bottom=2)
    F = a.L('face')
    a.eye(F, hx + 3 * k, hy + 2 * k)
    a.put(F, hx + 6 * k - 1, hy + 5 * k, Fc, 1)
    return a.finish()


def chicken(k=1, facing='right', pose='idle', frame=0, shadow=True, **o):
    """Chicken: a white feathered body with a folded wing, an upright head, red comb and wattle, a yellow beak,
    thin yellow legs with toes; tail feathers up at the back."""
    a = A(k, 20, 22, facing, pose, frame, shadow, **o)
    ox, oy = 3 * k, 3 * k
    R = FEATHER
    gy = oy + 17 * k
    a.ground(ox + 6 * k, gy, 6 * k, 1.1 * k + 0.2)
    bob = _walk_bob(a)
    G = a.L('feet')
    for i, lx in enumerate((5, 8)):
        sw, lift = a.leg_motion('nf' if i else 'nb')
        lh = 3 - lift
        for j in range(lh * k):
            a.put(G, ox + lx * k + (sw // 2 if j > k else 0), oy + 14 * k + j, BEAK, 3 if j % 2 == 0 else 2)
        a.rect(G, ox + lx * k + sw // 2, oy + (14 + lh) * k - 1, ox + lx * k + sw // 2 + 2 * k - 1,
               oy + (14 + lh) * k - 1, BEAK, 2)
    L = a.L('body')
    body = {(x, y) for x in range(ox + 2 * k, ox + 10 * k) for y in range(oy + 7 * k + bob, oy + 14 * k + bob)}
    body -= {(ox + 2 * k + i, oy + 13 * k + bob + j) for i in range(k) for j in range(k)}
    a.shade_pts(L, body, R)
    T = a.L('tail')
    for (x, y, w, h) in ((0, 4, 2, 4), (1, 3, 2, 2), (2, 6, 2, 3)):
        a.box(T, ox + x * k, oy + y * k + bob, ox + (x + w) * k - 1, oy + (y + h) * k - 1 + bob, R, top=4, bottom=2)
    Wg = a.L('wing')
    wpts = {(x, y) for x in range(ox + 3 * k, ox + 8 * k) for y in range(oy + 9 * k + bob, oy + 12 * k + bob)}
    a.shade_pts(Wg, wpts, R, top=4, bottom=1, left=3, right=2, base=3)
    if k == 2:
        for x in range(ox + 7, ox + 15, 2):
            a.put(Wg, x, oy + 22 + bob, R, 2)
            a.put(Wg, x, oy + 21 + bob, R, 2)
    H_ = a.L('head', own=True)
    hx, hy = ox + 7 * k, oy + 1 * k + bob + (k if a.walk and a.frame in (0, 2) else 0)
    a.box(H_, hx, hy, hx + 4 * k - 1, hy + 7 * k - 1, R)
    C_ = a.L('acc')
    a.rect(C_, hx + k, hy - k, hx + 3 * k - 1, hy - 1, COMB, 3)
    a.put(C_, hx + k, hy - k, COMB, 4)
    if k == 2:
        a.put(C_, hx + 4, hy - 3, COMB, 4)
        a.put(C_, hx + 2, hy - 3, COMB, 3)
    a.rect(C_, hx + 4 * k, hy + 4 * k, hx + 5 * k - 1, hy + 6 * k - 1, COMB, 3)
    M = a.L('snout')
    a.box(M, hx + 4 * k, hy + 2 * k, hx + 6 * k - 1, hy + 4 * k - 1, BEAK, top=4, bottom=2)
    F = a.L('face')
    a.eye(F, hx + 2 * k, hy + 2 * k)
    return a.finish()


def horse(k=1, facing='right', pose='idle', frame=0, shadow=True, colour=None, **o):
    """Horse: a long body on long legs with dark split hooves and white socks, a neck leaning forward with a
    dark mane, a long face sloping down to a darker muzzle, ears, a forelock, a flowing tail; k=2 adds the
    lit muscle arcs of the shoulder and hip, mane and tail strands. colour= recolours the coat."""
    a = A(k, 40, 38, facing, pose, frame, shadow, **o)
    ox, oy = 6 * k, 4 * k
    R = ramp_of(colour, soft=0.7) if colour else HORSE
    gy = oy + 31 * k
    bob = _walk_bob(a)
    a.ground(ox + 11 * k, gy, 13 * k, 1.3 * k + 0.3)
    for which, lx in (('fb', 3), ('ff', 15), ('nb', 1), ('nf', 13)):
        Lg = a.leg(which, ox + lx * k, oy + 19 * k, 3, 12, R, hoof=HOOF, hoof_h=1,
                   sock=WHITEC if which in ('nb', 'nf') else None, sock_h=2)
        if k == 2:
            yb = max(y for _, y in Lg.px)
            xs = sorted(x for (x, y) in Lg.px if y == yb)
            Lg.put(xs[len(xs) // 2], yb, HOOF, 0)
    L = a.L('body')
    a.box(L, ox, oy + 11 * k + bob, ox + 18 * k - 1, oy + 19 * k - 1, R)
    if k == 2:
        for (cx_, cy_) in ((ox + 31, oy + 26), (ox + 6, oy + 25)):       # shoulder and hip muscles
            for i in range(6):
                a.put(L, cx_ - i, cy_ + (i * i) // 8, R, 4)
            for i in range(4):
                a.put(L, cx_ + 1 - i, cy_ + 6 + i // 2, R, 2)
        a.rect(L, ox + 4, oy + 36, ox + 32, oy + 36, R, 2)
        a.fur(L, {(x, y) for x in range(ox + 8, ox + 28) for y in range(oy + 25, oy + 35)}, R, 3, seed=6)
    T = a.L('tail')
    for j in range(14 * k):
        x = ox - k - (j * j) // (40 * k) - (k if j > 3 * k else 0)
        for i in range(2 * k + (k if 3 * k < j < 11 * k else 0)):
            t = 4 if i == 0 else 3
            if k == 2 and i == 2 and j % 4 < 2:
                t = 2
            a.put(T, x + i, oy + 11 * k + j + bob, MANE, t)
    N = a.L('neck')
    neck = set()
    for y in range(oy + 3 * k + bob, oy + 14 * k + bob):
        sh = (oy + 14 * k + bob - y) // 2
        for x in range(ox + 14 * k + sh, ox + 19 * k + sh):
            neck.add((x, y))
    a.shade_pts(N, neck, R)
    Mn = a.L('mane')
    for (x, y) in sorted(neck):
        if (x - 1, y) not in neck:
            for i in range(-k, k):
                t = 4 if i < 0 else 3
                if k == 2 and (y // 2) % 3 == 0 and i == 0:
                    t = 2
                a.put(Mn, x + i, y, MANE, t)
    H_ = a.L('head', own=True)
    hx, hy = ox + 19 * k, oy + bob
    head = set()
    for i in range(10 * k):
        top = hy + i // 3
        for y in range(top, top + 5 * k):
            head.add((hx + i, y))
    head |= {(hx + i, hy + 5 * k + j) for i in range(4 * k) for j in range(k)}          # the cheek
    a.shade_pts(H_, head, R)
    for (x, y) in head:
        if x >= hx + 7 * k:
            a.put(H_, x, y, R, 2 if (x, y + 1) in head else 1)                       # the muzzle
    a.put(H_, hx + 10 * k - 1, hy + 3 * k + 1, MANE, 0)
    if k == 2:
        a.rect(H_, hx + 2, hy + 1, hx + 12, hy + 1, R, 4)
        a.rect(H_, hx + 15, hy + 13, hx + 19, hy + 13, R, 0)
        a.put(H_, hx + 1, hy + 10, R, 2)
        a.put(H_, hx + 2, hy + 11, R, 2)
    F = a.L('face')
    a.eye(F, hx + 3 * k, hy + 2 * k)
    E = a.L('ears')
    for ex in (hx, hx + 2 * k):
        a.box(E, ex, hy - 2 * k, ex + k - 1, hy - 1, R, top=4, bottom=3, left=4, right=2)
        if k == 2:
            a.put(E, ex + 1, hy - 4, R, 3)
            a.put(E, ex + 1, hy - 3, R, 3)
    for i in range(3 * k):                                    # forelock
        a.put(Mn, hx + k + i // 2, hy + i // 2, MANE, 3 if i % 2 else 4)
    return a.finish()


def cat(k=1, facing='right', pose='idle', frame=0, shadow=True, colour=None, **o):
    """Cat: a small body with tabby stripes, a big head with pointed ears (pink inside at k=2), green eyes, a
    pink nose, whiskers, a tail curling up."""
    a = A(k, 26, 20, facing, pose, frame, shadow, **o)
    ox, oy = 4 * k, 3 * k
    R = ramp_of(colour, soft=0.7) if colour else CAT
    gy = oy + 14 * k
    a.ground(ox + 8 * k, gy, 9 * k, 1.1 * k + 0.2)
    for which, lx in (('fb', 3), ('ff', 11), ('nb', 1), ('nf', 9)):
        a.leg(which, ox + lx * k, oy + 10 * k, 2, 4, R, sock=WHITEC if which[0] == 'n' and k == 2 else None,
              sock_h=1)
    L = a.L('body')
    a.box(L, ox, oy + 6 * k, ox + 12 * k - 1, oy + 10 * k - 1, R)
    for x in range(ox + 2 * k, ox + 11 * k, 3 * k):           # tabby stripes over the back
        for j in range(2 * k + (k - 1)):
            a.put(L, x, oy + 6 * k + j, R, 1 if j == 0 and k == 2 else 2)
            if k == 2:
                a.put(L, x + 1, oy + 6 * k + j, R, 2)
    T = a.L('tail')
    path = [(-1, 7), (-1, 6), (-2, 5), (-2, 4), (-2, 3), (-2, 2), (-1, 1), (0, 1)]   # a J rising from the rump
    for n, (x, y) in enumerate(path):
        for i in range(k):
            for j in range(k):
                t = 4 if i == 0 and n < 6 else 3
                if n in (2, 5) and k == 2:
                    t = 2                                   # rings
                a.put(T, ox + x * k + i, oy + y * k + j, R, t)
    H_ = a.L('head', own=True)
    hx, hy = ox + 11 * k, oy + 2 * k + _walk_bob(a)
    a.box(H_, hx, hy, hx + 7 * k - 1, hy + 6 * k - 1, R)
    for x in (hx + k, hx + 3 * k):                            # forehead stripes
        a.put(H_, x, hy + k, R, 2)
    E = a.L('ears')
    for ex in (hx, hx + 4 * k):
        a.rect(E, ex, hy - k, ex + 2 * k - 1, hy - 1, R, 3)
        a.rect(E, ex, hy - 2 * k, ex + k - 1, hy - k - 1, R, 4)
        if k == 2:
            a.put(E, ex + 2, hy - 1, NOSE_P, 3)
    F = a.L('face')
    a.eye(F, hx + 4 * k, hy + 2 * k, iris=IRIS_GREEN)
    a.put(F, hx + 7 * k - 1, hy + 3 * k + (k - 1), NOSE_P, 3)
    if k == 2:
        for i in range(3):
            a.put(F, hx + 15 + i, hy + 9 + (i // 2), WHITEC, 4, free=True)
            a.put(F, hx + 15 + i, hy + 11, WHITEC, 3, free=True)
        a.rect(H_, hx + 1, hy + 10, hx + 5, hy + 10, R, 2)
    return a.finish()


def wolf(k=1, facing='right', pose='idle', frame=0, shadow=True, collar=True, **o):
    """Wolf / dog: grey fur with a lighter belly, a head with a snout and black nose, pointed ears, a bushy tail
    held up, a red collar with a gold tag (collar=False for a wild wolf)."""
    a = A(k, 28, 22, facing, pose, frame, shadow, **o)
    ox, oy = 5 * k, 3 * k
    R = WOLF
    gy = oy + 17 * k
    a.ground(ox + 8 * k, gy, 10 * k, 1.1 * k + 0.2)
    for which, lx in (('fb', 3), ('ff', 11), ('nb', 1), ('nf', 9)):
        a.leg(which, ox + lx * k, oy + 11 * k, 2, 6, R)
    L = a.L('body')
    a.box(L, ox, oy + 5 * k, ox + 12 * k - 1, oy + 11 * k - 1, R)
    a.rect(L, ox + k, oy + 10 * k, ox + 11 * k - 1, oy + 11 * k - 1, R, 4)
    a.rect(L, ox + k, oy + 11 * k - 1, ox + 11 * k - 1, oy + 11 * k - 1, R, 2)
    a.fur(L, {(x, y) for x in range(ox + k, ox + 12 * k) for y in range(oy + 5 * k, oy + 10 * k)}, R,
          3 if k == 1 else 6, seed=9, up=4, down=2)
    if k == 1:
        a.rect(L, ox + 2, oy + 6, ox + 8, oy + 6, R, 2)       # the darker saddle under the lit back
    else:
        a.rect(L, ox + 3, oy + 11, ox + 17, oy + 12, R, 2)
        a.rect(L, ox + 3, oy + 10, ox + 17, oy + 10, R, 1)
    T = a.L('tail')
    tail = set()
    for (x, y) in ((-0.5, 6.5), (-1.5, 5.5), (-2.5, 4.5), (-3, 3.5), (-3.2, 2.5)):
        tail |= ell(ox + x * k, oy + y * k, 1.5 * k, 1.5 * k)
    a.shade_pts(T, tail, R)
    if k == 2:
        a.fur(T, tail, R, 2, seed=4)
    H_ = a.L('head', own=True)
    hx, hy = ox + 11 * k, oy + 1 * k + _walk_bob(a)
    a.box(H_, hx, hy + k, hx + 6 * k - 1, hy + 7 * k - 1, R)
    M = a.L('snout')
    a.box(M, hx + 6 * k, hy + 4 * k, hx + 9 * k - 1, hy + 7 * k - 1, R, top=4, bottom=2)
    a.rect(M, hx + 9 * k - k, hy + 4 * k, hx + 9 * k - 1, hy + 5 * k - 1, BLACKC, 2)
    if k == 2:
        a.rect(M, hx + 13, hy + 13, hx + 16, hy + 13, R, 1)
    E = a.L('ears')
    for ex in (hx, hx + 3 * k):
        a.rect(E, ex, hy - k, ex + 2 * k - 1, hy + k - 1, R, 3)
        a.rect(E, ex, hy - k, ex + k - 1, hy - 1, R, 4)
    F = a.L('face')
    a.eye(F, hx + 3 * k, hy + 3 * k, iris=IRIS_BROWN)
    if k == 2:
        for ex in (hx + 1, hx + 7):
            a.put(E, ex, hy - 1, NOSE_P, 2)                 # inside of the ears
        for (x, y) in ((1, 9), (2, 10), (1, 11), (3, 11), (2, 12)):
            a.put(H_, hx + x, hy + y, R, 4)                 # cheek ruff
        a.rect(L, ox + 20, oy + 15, ox + 22, oy + 19, R, 4)   # chest ruff
        a.put(L, ox + 21, oy + 20, R, 4)
    if collar:
        C_ = a.L('collar')
        a.rect(C_, hx, hy + 6 * k, hx + 2 * k - 1, hy + 7 * k - 1, COLLAR, 3)
        a.put(C_, hx, hy + 6 * k, COLLAR, 4)
        a.put(C_, hx + k, hy + 7 * k, GOLD, 4)
        if k == 2:
            a.put(C_, hx + 2, hy + 15, GOLD, 3)
    return a.finish()


def fox(k=1, facing='right', pose='idle', frame=0, shadow=True, **o):
    """Fox: orange body with a white belly and chest, dark socks, a pointed snout with a white cheek and black
    nose, big ears with dark tips, a huge bushy tail with a white tip."""
    a = A(k, 32, 20, facing, pose, frame, shadow, **o)
    ox, oy = 8 * k, 3 * k
    R, W_ = FOX, FOX_W
    gy = oy + 14 * k
    a.ground(ox + 6 * k, gy, 11 * k, 1.1 * k + 0.2)
    for which, lx in (('fb', 3), ('ff', 10), ('nb', 1), ('nf', 8)):
        a.leg(which, ox + lx * k, oy + 10 * k, 2, 4, R, sock=BEE_B, sock_h=2)
    T = a.L('tail')
    tail = ell(ox - 3 * k, oy + 9 * k, 5 * k, 2.6 * k)
    a.shade_pts(T, tail, R)
    for (x, y) in tail:
        if x < ox - 6 * k:
            a.put(T, x, y, W_, 4 if y < oy + 9 * k else 3)
    L = a.L('body')
    a.box(L, ox, oy + 6 * k, ox + 11 * k - 1, oy + 10 * k - 1, R)
    a.rect(L, ox + k, oy + 10 * k - k, ox + 10 * k - 1, oy + 10 * k - 1, W_, 3)
    a.fur(L, {(x, y) for x in range(ox, ox + 11 * k) for y in range(oy + 6 * k, oy + 9 * k)}, R,
          2 if k == 1 else 5, seed=5)
    H_ = a.L('head', own=True)
    hx, hy = ox + 10 * k, oy + 3 * k + _walk_bob(a)
    a.box(H_, hx, hy, hx + 6 * k - 1, hy + 5 * k - 1, R)
    a.rect(H_, hx + 3 * k, hy + 3 * k, hx + 6 * k - 1, hy + 5 * k - 1, W_, 3)
    M = a.L('snout')
    a.box(M, hx + 6 * k, hy + 3 * k, hx + 8 * k - 1, hy + 5 * k - 1, R, top=4, bottom=2)
    a.rect(M, hx + 6 * k, hy + 4 * k, hx + 8 * k - 1, hy + 5 * k - 1, W_, 3)
    a.rect(M, hx + 8 * k, hy + 3 * k, hx + 9 * k - 1, hy + 4 * k - 1, BLACKC, 2)
    E = a.L('ears')
    for ex in (hx, hx + 3 * k):
        a.rect(E, ex, hy - 2 * k, ex + 2 * k - 1, hy - 1, R, 3)
        a.rect(E, ex, hy - 3 * k, ex + 2 * k - 1, hy - 2 * k - 1, BEE_B, 3)
        if k == 2:
            a.put(E, ex + 1, hy - 2, W_, 3)
    F = a.L('face')
    a.eye(F, hx + 3 * k, hy + k)
    return a.finish()


def bee(k=1, facing='right', pose='idle', frame=0, shadow=True, **o):
    """Bee: a striped yellow body, a dark face with a big eye, antennae, a stinger, two light wings on top
    (veins at k=2; they flap in the walk frames), tiny legs; the shadow lies on the ground under it."""
    a = A(k, 20, 22, facing, pose, frame, shadow, **o)
    ox, oy = 3 * k, 4 * k
    bob = -k if a.walk and a.frame in (1, 2) else 0
    a.ground(ox + 7 * k, oy + 17 * k, 4 * k, 0.9 * k + 0.2)
    L = a.L('body')
    y0 = oy + 5 * k + bob
    a.box(L, ox + k, y0, ox + 11 * k - 1, y0 + 7 * k - 1, BEE)
    for sx_ in (4, 7):
        for j in range(7 * k):
            for i in range(2 * k):
                t = 3 if 0 < j < 7 * k - 1 else (4 if j == 0 else 2)
                a.put(L, ox + sx_ * k + i, y0 + j, BEE_B, t)
    a.rect(L, ox + 9 * k, y0, ox + 11 * k - 1, y0 + 7 * k - 1, BEE_B, 3)
    a.rect(L, ox + 9 * k, y0, ox + 11 * k - 1, y0, BEE_B, 4)
    a.rect(L, ox, y0 + 3 * k, ox + k - 1, y0 + 4 * k - 1, BEE_B, 2)          # stinger
    F = a.L('face')
    a.eye(F, ox + 9 * k, y0 + 2 * k, big=k == 2)
    A_ = a.L('acc')
    for (x, y) in ((11, -1), (12, -2)):
        for i in range(k):
            a.put(A_, ox + x * k + i, y0 + y * k, BEE_B, 3)
    up = a.walk and a.frame in (0, 2)
    Wg = a.L('wing')
    wy = y0 - (4 if up else 3) * k
    a.box(Wg, ox + 3 * k, wy, ox + 6 * k - 1, y0 - 1 + (0 if up else 0), WING, top=4, bottom=3, left=4, right=3)
    if k == 2:
        a.rect(Wg, ox + 7, wy + 2, ox + 7, y0 - 2, WING, 2)
    Wf = a.L('wing_far')
    a.box(Wf, ox + 6 * k, wy + k, ox + 8 * k - 1, y0 - 1, WING, top=3, bottom=2, left=3, right=2)
    G = a.L('feet')
    for x in (4, 6, 8):
        a.rect(G, ox + x * k, y0 + 7 * k, ox + x * k + k - 1, y0 + 8 * k - 1, BEE_B, 2)
    return a.finish()


def fish(k=1, facing='right', pose='idle', frame=0, shadow=False, **o):
    """Fish (cod-like): an olive back, a tan side, a cream belly, a forked tail, a dorsal fin, a pectoral fin, an
    eye with a white ring and a gill line; the tail swings in the walk (swim) frames."""
    a = A(k, 22, 14, facing, pose, frame, shadow, **o)
    ox, oy = 2 * k, 2 * k
    R, Bk = FISH, FISH_B
    sw = {0: 0, 1: -k, 2: 0, 3: k}[a.frame] if a.walk else 0
    T = a.L('tail')
    for j in range(-4 * k, 4 * k + 1):
        w = abs(j) // 2 + k
        for i in range(w):
            if abs(j) < k and i > 0:
                continue
            a.put(T, ox + 3 * k - i - 1, oy + 5 * k + j + (sw if abs(j) > k else 0), Bk if j < 0 else R,
                  4 if j < -2 * k else 3 if j < 2 * k else 2)
    L = a.L('body')
    body = ell(ox + 9.5 * k, oy + 5.5 * k, 7 * k, 3.5 * k)
    for (x, y) in body:
        rel = (y - (oy + 2 * k)) / (7 * k)
        r = Bk if rel < 0.32 else R if rel < 0.78 else WHITEC
        t = 3
        if (x, y - 1) not in body:
            t = 4
        if (x, y + 1) not in body:
            t = 2
        a.put(L, x, y, r, t)
    if k == 2:
        for x in range(ox + 6, ox + 30, 4):                  # lateral line and scales
            a.put(L, x, oy + 11, R, 4)
            a.put(L, x + 1, oy + 11, R, 4)
            a.put(L, x + 2, oy + 8, Bk, 2)
            a.put(L, x + 3, oy + 9, Bk, 2)
    Fn = a.L('acc')
    for i in range(4 * k):
        a.put(Fn, ox + 7 * k + i, oy + 2 * k - 1 - (1 if k < i < 3 * k else 0), Bk, 3)
    a.rect(Fn, ox + 12 * k, oy + 7 * k, ox + 13 * k + (k - 1), oy + 8 * k - 1, R, 2)
    F = a.L('face')
    a.eye(F, ox + 14 * k, oy + 4 * k, white=True)
    for j in range(2 * k):
        a.put(F, ox + 12 * k, oy + 4 * k + j, R, 2)
    a.put(F, ox + 16 * k + (k - 1), oy + 6 * k, Bk, 1)
    return a.finish()


def axolotl(k=1, facing='right', pose='idle', frame=0, shadow=True, colour=None, **o):
    """Axolotl: a soft pink body with a lighter belly, a wide head with a smile and dot eyes, three frilly gills
    on each side (darker tips), little legs, a long tail with a fin. colour= recolours it."""
    a = A(k, 28, 16, facing, pose, frame, shadow, **o)
    ox, oy = 8 * k, 3 * k
    R = ramp_of(colour, soft=0.6) if colour else AXO
    G = AXO_G
    gy = oy + 10 * k
    a.ground(ox + 6 * k, gy, 9 * k, 1.0 * k + 0.2)
    for which, lx in (('fb', 2), ('ff', 9), ('nb', 1), ('nf', 8)):
        a.leg(which, ox + lx * k, oy + 7 * k, 1, 3, R)
    T = a.L('tail')
    sw = {1: -k, 3: k}.get(a.frame, 0) if a.walk else 0
    for i in range(8 * k):
        x = ox - 1 - i
        hh = max(k, 3 * k - (i * 2 * k) // (8 * k))
        yc = oy + 5 * k + (sw * i) // (8 * k)
        for j in range(-hh // 2 - (k if i < 6 * k else 0), hh // 2 + (k if i < 5 * k else 0) + 1):
            fin = abs(j) > hh // 2
            a.put(T, x, yc + j, R, 4 if fin and j < 0 else 2 if fin else 3)
    L = a.L('body')
    a.box(L, ox, oy + 4 * k, ox + 10 * k - 1, oy + 7 * k - 1, R)
    a.rect(L, ox + k, oy + 7 * k - k, ox + 10 * k - 1, oy + 7 * k - 1, R, 4)
    a.rect(L, ox + k, oy + 7 * k - 1, ox + 10 * k - 1, oy + 7 * k - 1, R, 2)
    if k == 2:
        for x in range(ox + 4, ox + 18, 5):
            a.put(L, x, oy + 9, R, 2)
            a.put(L, x + 1, oy + 9, R, 2)
    H_ = a.L('head', own=True)
    hx, hy = ox + 9 * k, oy + 2 * k
    a.box(H_, hx, hy, hx + 6 * k - 1, hy + 5 * k - 1, R)
    F = a.L('face')
    a.eye(F, hx + 4 * k, hy + 2 * k)
    a.rect(F, hx + 3 * k, hy + 4 * k, hx + 6 * k - 1, hy + 4 * k, R, 1)
    Gl = a.L('gills')
    for (x, y, t) in ((0, -1, 3), (-1, -2, 4), (-1, 0, 3), (-2, -1, 2), (0, 3, 3), (-1, 4, 2), (-1, 2, 3),
                      (-2, 2, 2)):
        for i in range(k):
            for j in range(k):
                a.put(Gl, hx + x * k + i, hy + y * k + j, G, t)
    return a.finish()


def parrot(k=1, facing='right', pose='idle', frame=0, shadow=True, perch=True, **o):
    """Parrot on a perch: an upright red body, a blue wing with a yellow shoulder and layered feather tips, a
    long tail, a white face patch round the eye, a hooked beak (light upper, dark lower), dark toes gripping a
    wooden perch."""
    a = A(k, 18, 24, facing, pose, frame, shadow and not perch, **o)
    ox, oy = 3 * k, 2 * k
    R, Bl, Y = PARROT_R, PARROT_B, PARROT_Y
    bob = -k if a.walk and a.frame in (1, 3) else 0
    if perch:
        Pp = a.L('perch')
        a.box(Pp, ox - 2 * k, oy + 14 * k, ox + 11 * k - 1, oy + 15 * k + (k - 1), WOOD, top=4, bottom=2)
    T = a.L('tail')
    for j in range(7 * k):
        x = ox + 2 * k - j // 3
        for i in range(2 * k):
            r = R if i >= k else Bl
            a.put(T, x + i, oy + 12 * k + j + bob, r, 3 if i else 4)
    L = a.L('body')
    body = {(x, y) for x in range(ox + 3 * k, ox + 8 * k) for y in range(oy + 5 * k + bob, oy + 13 * k + bob)}
    body -= {(ox + 3 * k + i, oy + 13 * k - 1 + bob) for i in range(k)}
    a.shade_pts(L, body, R)
    Wg = a.L('wing')
    wing = {(x, y) for x in range(ox + 2 * k, ox + 6 * k) for y in range(oy + 6 * k + bob, oy + 13 * k + bob)}
    a.shade_pts(Wg, wing, Bl, top=3, bottom=1)
    for x in range(ox + 2 * k, ox + 6 * k):
        for j in range(k):
            a.put(Wg, x, oy + 6 * k + bob + j, Y, 4 if j == 0 else 3)
    for y in range(oy + 9 * k + bob, oy + 13 * k + bob, 2 * k):
        for x in range(ox + 2 * k, ox + 6 * k):
            a.put(Wg, x, y, Bl, 2)
    H_ = a.L('head', own=True)
    hx, hy = ox + 4 * k, oy + bob
    a.box(H_, hx, hy + k, hx + 5 * k - 1, hy + 6 * k - 1, R)
    a.rect(H_, hx + 2 * k, hy + 2 * k, hx + 4 * k - 1, hy + 4 * k - 1, WHITEC, 4)
    F = a.L('face')
    a.eye(F, hx + 3 * k, hy + 2 * k)
    M = a.L('snout')
    a.rect(M, hx + 5 * k, hy + 2 * k, hx + 6 * k + (k - 1), hy + 3 * k - 1, HORN, 4)
    a.rect(M, hx + 6 * k, hy + 3 * k, hx + 7 * k - 1, hy + 4 * k + (k - 1), HORN, 3)
    a.rect(M, hx + 5 * k, hy + 3 * k, hx + 6 * k - 1, hy + 4 * k + (k - 1), BLACKC, 3)
    G = a.L('feet')
    for x in (ox + 4 * k, ox + 6 * k):
        a.rect(G, x, oy + 13 * k + bob, x + k - 1, oy + 14 * k - 1, CHAIN, 2)
        a.rect(G, x - k, oy + 14 * k, x + k - 1, oy + 14 * k + (k - 1), CHAIN, 3)
    return a.finish()


def slime(k=1, facing='front', pose='idle', frame=0, shadow=True, colour=None, **o):
    """Slime (front view): a gel cube - lit top face, a light outer layer with a big glint, a darker inner core
    seen through it carrying the face; squash / stretch in the walk (hop) frames. colour= recolours it."""
    a = A(k, 22, 22, 'right', pose, frame, shadow, **o)
    R = ramp_of(colour, soft=0.4) if colour else SLIME
    Ri = SLIME_IN if not colour else ramp_of(colour, soft=0.6)
    sq = {0: (0, 0), 1: (k, -k), 2: (0, 0), 3: (-k, k)}[a.frame] if a.walk else (0, 0)
    w = 14 * k + 2 * sq[0]
    hh = 12 * k + sq[1]
    ox = 4 * k - sq[0]
    gy = 18 * k
    oy = gy - hh
    if a.walk and a.frame == 3:
        oy -= 2 * k
    a.ground(ox + w // 2, gy + 0.5 * k, w / 2 + k, 1.2 * k + 0.3)
    L = a.L('body')
    top = 3 * k
    for y in range(oy, oy + hh):
        for x in range(ox, ox + w):
            t = 3
            if y < oy + top:
                t = 4
                if y == oy:
                    t = 5 if x < ox + w // 2 else 4
            if x == ox:
                t = 4
            if x == ox + w - 1:
                t = 2
            if y == oy + hh - 1:
                t = 2
            L.put(x, y, R, t)
    for x in range(ox, ox + w):
        L.put(x, oy + top, R, 2 if x > ox else 3)              # the edge between top and front
    ix0, ix1 = ox + 3 * k, ox + w - 3 * k - 1
    iy0, iy1 = oy + top + 2 * k, oy + hh - 2 * k - 1
    C_ = a.L('belly')
    for y in range(iy0, iy1 + 1):
        for x in range(ix0, ix1 + 1):
            t = 3
            if y == iy0 or x == ix0:
                t = 4
            if x == ix1 or y == iy1:
                t = 2
            C_.put(x, y, Ri, t)
    F = a.L('face')
    cx = (ix0 + ix1 + 1) // 2
    ey = iy0 + 2 * k
    for ex in (cx - 3 * k, cx + k):
        for i in range(2 * k):
            for j in range(2 * k if k == 2 else 2):
                F.put(ex + i, ey + j, Ri, 0)
        if k == 2:
            F.put(ex, ey, EYE_W, 4)
    F.put(cx - k, ey + 3 * k + (k - 1), Ri, 0)
    if k == 2:
        F.put(cx - 1, ey + 7, Ri, 0)
        F.put(cx, ey + 7, Ri, 0)
    G = a.L('fx', line=False)
    gx, gy2 = ox + 2 * k, oy + top + 2 * k
    for (dx, dy) in ((0, 0), (1, 0), (0, 1)) if k == 1 else ((0, 0), (1, 0), (2, 0), (0, 1), (0, 2), (1, 1)):
        G.put(gx + dx, gy2 + dy, R, 5)
    return a.finish()


def spider(k=1, facing='front', pose='idle', frame=0, shadow=True, **o):
    """Spider (front view): a round abdomen behind, the head in front with eight red eyes (two big ones with
    glints), fangs, and eight legs spread out - each an upper segment rising to a lit knee and a lower one
    down to the ground; the legs step in the walk frames."""
    a = A(k, 40, 20, 'right', pose, frame, shadow, **o)
    R = SPIDER
    cx = 20 * k
    gy = 16 * k
    a.ground(cx, gy + 0.5 * k, 16 * k, 1.3 * k + 0.3)
    Ab = a.L('body')
    abd = ell(cx, 6 * k, 7 * k, 4.2 * k)
    for (x, y) in abd:
        nx, ny = (x + 0.5 - cx) / (7 * k), (y + 0.5 - 6 * k) / (4.2 * k)
        lam = -0.6 * nx - 0.7 * ny
        Ab.put(x, y, R, 4 if lam > 0.45 else 3 if lam > -0.2 else 2)
    if k == 2:
        for (x, y) in ((cx - 4, 5), (cx - 3, 5), (cx + 2, 4), (cx + 3, 4), (cx - 1, 3), (cx, 3)):
            Ab.put(x, y, R, 1)
    for side in (-1, 1):
        for i in range(4):
            lift = 0
            if a.walk:
                ph = (i + (0 if side < 0 else 1)) % 2
                lift = k if (a.frame in (1, 3) and ph == (a.frame // 2)) else 0
            Lg = a.L('leg_f%s%d' % ('l' if side < 0 else 'r', i))
            hipx = cx + side * (3 * k + i * k)
            hipy = 8 * k + i * k // 2
            kneex = cx + side * (8 * k + i * 3 * k)
            kneey = (2 + i) * k - lift
            footx = cx + side * (11 * k + i * 3 * k + (i == 3) * k)
            footy = gy - 1 - lift
            for (p, q, up) in (((hipx, hipy), (kneex, kneey), True), ((kneex, kneey), (footx, footy), False)):
                pts = line(p[0], p[1], q[0], q[1])
                for (x, y) in pts:
                    if k == 1:                              # 1 px legs, no outline: they stay thin
                        Lg.put(x, y, R, 2 if up else 1, free=True)
                        continue
                    for j in range(k):
                        Lg.put(x, y + j, R, (4 if up else 3) if j == 0 else 2)
            if k == 2:
                Lg.put(kneex, kneey, R, 5)                  # the knee catches the light
    Hd = a.L('head', own=True)
    hx0, hy0 = cx - 4 * k, 7 * k
    for y in range(hy0, hy0 + 7 * k):
        for x in range(hx0, hx0 + 8 * k):
            t = 3
            if x == hx0:
                t = 4
            if x == hx0 + 8 * k - 1:
                t = 2
            if y == hy0:
                t = 4
            if y == hy0 + 7 * k - 1:
                t = 2
            Hd.put(x, y, R, t)
    F = a.L('face')
    E = SPIDER_EYE
    ey = hy0 + 3 * k
    for ex in (cx - 3 * k, cx + k):
        for i in range(2 * k):
            for j in range(k):
                F.put(ex + i, ey + j, E, 3 if j == 0 else 2)
        F.put(ex, ey, E, 5)
    for ex in (cx - 2 * k, cx + k):
        F.put(ex, ey - 2 * k + (k - 1), E, 3)
        if k == 2:
            F.put(ex + 1, ey - 3, E, 3)
    for ex in (cx - 4 * k + k, cx + 2 * k):
        F.put(ex, ey - k, E, 2)
    for fx_ in (cx - 2 * k, cx + k):
        for j in range(k + (k - 1)):
            F.put(fx_, hy0 + 7 * k + j - (k - 1), BONE, 4 if j == 0 else 3)
    return a.finish()


def creeper_plant(k=1, facing='front', pose='idle', frame=0, shadow=True, **o):
    """A blocky explosive plant monster (front view): a leafy head with a pink bud on top, slanted angry eyes
    and a jagged mouth, a stalk-like body with leaf clusters and a glowing seed core in the chest (the
    explosive), four stubby root feet (the front two step in the walk frames)."""
    a = A(k, 24, 38, 'right', pose, frame, shadow, **o)
    R, Dk = LEAF, MOSSY
    cx = 12 * k
    gy = 34 * k
    a.ground(cx, gy + 0.5 * k, 7 * k, 1.2 * k + 0.3)
    bob = -k if a.walk and a.frame in (1, 3) else 0
    for i, sd in enumerate('lr'):
        lift = k if a.walk and ((a.frame == 1 and sd == 'l') or (a.frame == 3 and sd == 'r')) else 0
        Lf = a.L('leg_n' + ('b' if sd == 'l' else 'f'))
        fx0 = cx - 4 * k if sd == 'l' else cx
        for y in range(gy - 5 * k, gy - lift):
            for x in range(fx0, fx0 + 4 * k):
                t = 3
                if x == fx0:
                    t = 4
                if x == fx0 + 4 * k - 1:
                    t = 2
                if y == gy - lift - 1:
                    t = 1
                Lf.put(x, y, Dk, t)
        if k == 2:
            for x in range(fx0, fx0 + 4 * k, 2 * k):          # root toes
                Lf.put(x, gy - lift - 1, DWOOD, 3)
                Lf.put(x + 1, gy - lift - 1, DWOOD, 2)
    B = a.L('body')
    by0, by1 = 14 * k + bob, gy - 5 * k - 1
    bx0, bx1 = cx - 3 * k, cx + 3 * k - 1
    for y in range(by0, by1 + 1):
        for x in range(bx0, bx1 + 1):
            t = 3
            if x == bx0:
                t = 4
            if x == bx1:
                t = 2
            B.put(x, y, R, t)
    for (dx, dy) in ((-2, 3), (1, 9), (-3, 12), (1, 1)):          # leaf clusters on the stalk
        x, y = cx + dx * k, by0 + dy * k
        for (i, j, t) in (((0, 0, 4), (1, 0, 4), (0, 1, 2), (1, 1, 3), (2, 1, 2)) if k == 2 else
                          ((0, 0, 4), (1, 0, 4), (1, 1, 2), (2, 1, 2))):
            if bx0 < x + i * k < bx1:
                for q in range(k):
                    B.put(x + i * k + q, y + j * k, R, t)
    core = a.L('belly')
    ccy = by0 + 5 * k
    for y in range(ccy, ccy + 3 * k):
        for x in range(cx - k, cx + k):
            core.put(x, y, FIRE, 4 if (x < cx and y < ccy + k) else 3)
    core.put(cx - k, ccy, LAMP, 5)
    if k == 2:
        for (x, y) in ((cx - 3, ccy - 1), (cx + 2, ccy + 6), (cx - 3, ccy + 6), (cx + 2, ccy - 1)):
            core.put(x, y, Dk, 1)
    H_ = a.L('head', own=True)
    hx0, hy0 = cx - 4 * k, 6 * k + bob
    head = {(x, y) for x in range(hx0, hx0 + 8 * k) for y in range(hy0, hy0 + 8 * k)}
    a.shade_pts(H_, head, R)
    for (dx, dy) in ((1, 1), (5, 0), (2, 5), (6, 4), (0, 3)):
        x, y = hx0 + dx * k, hy0 + dy * k
        for (i, j, t) in (((0, 0, 4), (1, 0, 3), (0, 1, 2)) if k == 2 else ((0, 0, 4), (1, 0, 4))):
            p = (x + i * k, y + j * k)
            if p in head and p[0] < hx0 + 8 * k - 1:
                for q in range(k):
                    for r_ in range(k):
                        if (p[0] + q, p[1] + r_) in head:
                            H_.put(p[0] + q, p[1] + r_, R if t != 2 else Dk, t if t != 2 else 3)
    F = a.L('face')
    ey = hy0 + 3 * k
    for sd in (-1, 1):                                        # slanted angry eyes
        x0_ = cx - 3 * k if sd < 0 else cx + k
        for i in range(2 * k):
            slope = (i if sd < 0 else 2 * k - 1 - i) // k
            for j in range(k):
                F.put(x0_ + i, ey + slope + j, Dk, 0)
        if k == 2:
            F.put(x0_ + (1 if sd < 0 else 2), ey + 2, LAMP, 4)
    my = hy0 + 6 * k
    for i in range(-2 * k, 2 * k):
        F.put(cx + i, my + (1 if (i // k) % 2 else 0) * (1 if k == 1 else 1), Dk, 0)
        if k == 2:
            F.put(cx + i, my + 1 + ((i // 2) % 2), Dk, 0)
    Bd = a.L('acc')
    bx, byy = cx, hy0 - k
    bud = (((0, 0, LEAF, 3), (-1, 0, LEAF, 4), (-2, -1, LEAF, 4), (1, -1, LEAF, 2),
            (0, -1, BLOOM, 3), (-1, -1, BLOOM, 4), (0, -2, BLOOM, 4), (-1, -2, BLOOM, 5),
            (1, -2, BLOOM, 2), (0, -3, BLOOM, 3)) if k == 2 else
           ((0, 0, LEAF, 4), (-1, 0, LEAF, 4), (1, 0, LEAF, 2), (0, -1, BLOOM, 4), (-1, -1, BLOOM, 4),
            (0, -2, BLOOM, 3), (-1, -2, BLOOM, 3)))
    for (dx, dy, r, t) in bud:
        for i in range(k):
            for j in range(k):
                Bd.put(bx + dx * k + i, byy + dy * k + j, r, t)
    return a.finish()


SWITCHES = {'knight': 'shield=False plume=False', 'king': 'cape=False', 'wolf': 'collar=False',
            'parrot': 'perch=False', 'sheep': 'colour=NAME|#hex', 'horse': 'colour=NAME|#hex',
            'cat': 'colour=NAME|#hex', 'axolotl': 'colour=NAME|#hex', 'slime': 'colour=NAME|#hex',
            'fish': 'shadow=True'}
ANIMALS = {'cow': cow, 'pig': pig, 'sheep': sheep, 'chicken': chicken, 'horse': horse, 'cat': cat, 'wolf': wolf,
           'fox': fox, 'bee': bee, 'fish': fish, 'axolotl': axolotl, 'parrot': parrot}
MOBS = {'creeper_plant': creeper_plant, 'spider': spider, 'slime': slime}


def _humanoid(name):
    def f(k=1, **opts):
        return build_humanoid(LOOKS[name](), k=k, **opts)
    f.__name__ = name
    return f


CATALOG = {n: _humanoid(n) for n in LOOKS}


def _beast(fn, side_view):
    def f(k=1, pose='idle', frame=0, facing=None, shadow=True, **opts):
        for key in ('held', 'held_mat', 'skin', 'hair', 'top', 'bottom', 'shoes', 'eye', 'accent', 'hand'):
            opts.pop(key, None)
        if pose not in ('idle', 'walk'):
            pose = 'idle'
        fc = facing if facing in ('left', 'right') else 'right'
        return fn(k=k, facing=fc if side_view else 'front', pose=pose, frame=frame, shadow=shadow, **opts)
    f.__name__ = fn.__name__
    f.__doc__ = fn.__doc__
    return f


CATALOG.update({n: _beast(fn, False) for n, fn in MOBS.items()})
CATALOG.update({n: _beast(fn, True) for n, fn in ANIMALS.items()})


# ------------------------------------------------------------------ API
def _build(name, k=1, **opts):
    return CATALOG[name](k=k, **opts)


def parts(name, k=1, **opts):
    """Parts bottom -> top (dicts: name, sprite, x, y) in the figure's tight box."""
    items = _build(name, k, **opts).items
    x0 = min(it['x'] for it in items)
    y0 = min(it['y'] for it in items)
    return [dict(it, x=it['x'] - x0, y=it['y'] - y0) for it in items]


def _canvas_size(items):
    return (max(it['x'] + it['sprite'].width for it in items), max(it['y'] + it['sprite'].height for it in items))


def render(name, k=1, **opts):
    """The character as one tight RGBA image (composed from its parts)."""
    items = parts(name, k, **opts)
    canvas = Image.new('RGBA', _canvas_size(items), (0, 0, 0, 0))
    compose(items, canvas)
    return canvas


def walk_frames(name, k=1, **opts):
    """The 4 walk frames on one shared box (so they line up as an animated glyph / sprite sheet)."""
    raw = [_build(name, k, pose='walk', frame=i, **opts).items for i in range(4)]
    x0 = min(it['x'] for its in raw for it in its)
    y0 = min(it['y'] for its in raw for it in its)
    x1 = max(it['x'] + it['sprite'].width for its in raw for it in its)
    y1 = max(it['y'] + it['sprite'].height for its in raw for it in its)
    out = []
    for its in raw:
        im = Image.new('RGBA', (x1 - x0, y1 - y0), (0, 0, 0, 0))
        compose([dict(it, x=it['x'] - x0, y=it['y'] - y0) for it in its], im)
        out.append(im)
    return out


def walk_sheet(name, k=1, **opts):
    fr = walk_frames(name, k, **opts)
    w, hh = fr[0].size
    sheet = Image.new('RGBA', (w * 4, hh), (0, 0, 0, 0))
    for i, im in enumerate(fr):
        sheet.alpha_composite(im, (i * w, 0))
    return sheet


def export_parts(name, out_dir, k=1, **opts):
    """PNG per part + layers.json + _sheet.png, the composite, a x4 zoom and a layered .aseprite; checks that
    the parts rebuild the picture."""
    items = parts(name, k, **opts)
    size = _canvas_size(items)
    meta = layers.save_parts(items, out_dir, size)
    canvas = Image.new('RGBA', size, (0, 0, 0, 0))
    compose(items, canvas)
    rebuilt = layers.compose(meta, out_dir)
    assert rebuilt.tobytes() == canvas.tobytes(), 'parts do not rebuild the picture'
    tag = f'{name}{"_hd" if k == 2 else ""}'
    canvas.save(os.path.join(out_dir, f'{tag}.png'))
    canvas.resize((size[0] * 4, size[1] * 4), Image.NEAREST).save(os.path.join(out_dir, f'{tag}_x4.png'))
    layers.write_aseprite(os.path.join(out_dir, f'{tag}.aseprite'), items, size)
    return meta


# ------------------------------------------------------------------ charts
BG = (52, 54, 64, 255)
CELL = (138, 138, 142, 255)                 # neutral mid grey (the slot grey family)
INK = (226, 222, 210, 255)


def _label(img, x, y, text, colour=INK):
    from pixfont import draw_text
    draw_text(img, x, y, text.replace('_', ' '), colour)


def _text_w(text):
    from pixfont import text_width
    return text_width(text.replace('_', ' '))


def _grid(cells, cols, title=None):
    """cells = [(label, image)]: each image on a grey cell with its label under it; rows of `cols`."""
    boxes = []
    for lab, im in cells:
        w = max(im.width, _text_w(lab)) + 12
        hh = im.height + 26
        c = Image.new('RGBA', (w, hh), BG)
        c.paste(Image.new('RGBA', (w, im.height + 10), CELL), (0, 0))
        c.alpha_composite(im, ((w - im.width) // 2, 5))
        _label(c, (w - _text_w(lab)) // 2, im.height + 14, lab)
        boxes.append(c)
    rows = [boxes[i:i + cols] for i in range(0, len(boxes), cols)]
    top = 22 if title else 4
    W = max(sum(c.width + 4 for c in r) for r in rows) + 4
    Hh = top + sum(max(c.height for c in r) + 4 for r in rows)
    out = Image.new('RGBA', (W, Hh), BG)
    if title:
        _label(out, 6, 7, title)
    y = top
    for r in rows:
        x = 4
        rh = max(c.height for c in r)
        for c in r:
            out.paste(c, (x, y + rh - c.height))
            x += c.width + 4
        y += rh + 4
    return out


def _big(im, s):
    return im.resize((im.width * s, im.height * s), Image.NEAREST)


WALK_DEMO = ('player', 'villager_farmer', 'knight', 'zombie', 'skeleton', 'princess', 'cow', 'horse', 'chicken',
             'fox', 'slime', 'spider', 'bee', 'fish')


def _stack(sheets, gap=6):
    W = max(s_.width for s_ in sheets)
    out = Image.new('RGBA', (W, sum(s_.height for s_ in sheets) + gap * (len(sheets) - 1)), BG)
    y = 0
    for s_ in sheets:
        out.paste(s_, (0, y))
        y += s_.height + gap
    return out


def walk_section(k=1, names=WALK_DEMO, scale=None, cols=None):
    """The 4-frame walk cycle of several characters, frames side by side on one shared box each."""
    scale = scale or (4 if k == 1 else 3)
    cells = []
    for n in names:
        fr = walk_frames(n, k)
        w, hh = fr[0].size
        strip = Image.new('RGBA', (w * 4 + 6, hh), (0, 0, 0, 0))
        for i, im in enumerate(fr):
            strip.alpha_composite(im, (i * (w + 2), 0))
        cells.append((n + ' walk 0-3', _big(strip, scale)))
    return _grid(cells, cols or (4 if k == 1 else 3), f'walk cycles - frames 0 1 2 3 (contact, pass, contact, pass) x{scale}')


EXPLODE_GROUPS = {'head': 'top', 'face': 'top', 'hair': 'top', 'hat': 'top', 'beard': 'top', 'acc': 'top',
                  'torso': 'body', 'robe': 'body', 'chest': 'body', 'belt': 'body', 'collar': 'body',
                  'arms': 'body', 'cape': 'body', 'back': 'back',
                  'arm_l': 'left', 'hand_l': 'left', 'shield': 'left', 'shield_back': 'left',
                  'arm_r': 'right', 'hand_r': 'right', 'item': 'right',
                  'leg_l': 'legs', 'leg_r': 'legs', 'foot_l': 'legs', 'foot_r': 'legs', 'shadow': 'ground',
                  'fx': 'ground'}


EXPLODE_SLOTS = {'back': (0, 0), 'top': (1, 0), 'left': (0, 1), 'body': (1, 1), 'right': (2, 1), 'legs': (1, 2),
                 'ground': (1, 3)}


def exploded(name='knight', k=2, scale=None, gap=None):
    """One character's parts as an exploded diagram: parts grouped by body region and laid out in slots (head
    group on top, the arms either side of the body, legs and the ground shadow below); inside a group the
    layers are fanned out side by side in draw order, each labelled under it. Next to it the composed figure."""
    scale = scale or (4 if k == 1 else 3)
    gap = gap if gap is not None else 3 * k
    items = parts(name, k)
    groups = {}
    for it in items:
        groups.setdefault(EXPLODE_GROUPS.get(it['name'], it['name']), []).append(it)
    lab_h = -(-14 // scale)                                     # label height in sprite px
    strips = {}
    for g, its in groups.items():
        gy0 = min(it['y'] for it in its)
        x, row = 0, []
        for it in its:
            w = max(it['sprite'].width, -(-(_text_w(it['name']) + 4) // scale))
            row.append((it, x + (w - it['sprite'].width) // 2, it['y'] - gy0))
            x += w + gap
        hgt = max(dy + it['sprite'].height for it, _, dy in row) + lab_h
        strips[g] = (row, x - gap, hgt)
    extra = [g for g in strips if g not in EXPLODE_SLOTS]
    slots = dict(EXPLODE_SLOTS)
    for i, g in enumerate(extra):
        slots[g] = (i % 3, 4 + i // 3)
    cols_w, rows_h = {}, {}
    for g, (row, w, hgt) in strips.items():
        c, r = slots[g]
        cols_w[c] = max(cols_w.get(c, 0), w)
        rows_h[r] = max(rows_h.get(r, 0), hgt)
    pad = 4 * k
    cx_ = {c: pad + sum(cols_w.get(i, 0) + pad for i in range(c)) for c in range(3)}
    ry_ = {}
    y = pad
    for r in sorted(rows_h):
        ry_[r] = y
        y += rows_h[r] + pad
    Wd = pad + sum(cols_w.get(i, 0) + pad for i in range(3))
    view = Image.new('RGBA', (Wd * scale, y * scale), CELL)
    labels = []
    for g, (row, w, hgt) in strips.items():
        c, r = slots[g]
        ox = cx_[c] + (cols_w[c] - w) // 2
        oy = ry_[r] + (rows_h[r] - hgt) // 2
        for it, dx, dy in row:
            X, Y = (ox + dx) * scale, (oy + dy) * scale
            view.alpha_composite(_big(it['sprite'], scale), (X, Y))
            labels.append((it['name'], X + it['sprite'].width * scale // 2, Y + it['sprite'].height * scale + 3))
    for lab, mx, ly in labels:
        lx = max(1, min(view.width - _text_w(lab) - 1, mx - _text_w(lab) // 2))
        view.alpha_composite(Image.new('RGBA', (_text_w(lab) + 4, 10), (36, 38, 48, 255)), (lx - 2, ly - 2))
        _label(view, lx, ly, lab)
    whole = _big(render(name, k), scale)
    return _grid([(f'{name} (composed)', whole), (f'{name}: {len(items)} parts, exploded', view)], 2,
                 f'parts of one character - {"HD" if k == 2 else "k=1"}')


def chart(out, k=1, names=None, scale=None, cols=None):
    """Every character enlarged (x4, HD x3) on a neutral grey cell, labelled; then walk-cycle strips and one
    character's parts exploded."""
    names = names or list(CATALOG)
    scale = scale or (4 if k == 1 else 3)
    cells = [(n, _big(render(n, k), scale)) for n in names]
    sheet = _grid(cells, cols or 10, f'characters - {"HD k=2" if k == 2 else "k=1"} x{scale}')
    sheet = _stack([sheet, walk_section(k, scale=scale), exploded('knight', k, scale=scale)])
    sheet.save(out)
    return out


def extras(out, k=1, scale=None):
    """Options at a glance: poses and facings, every held item, colour variants (skin / hair / clothes, wool,
    coats), animals facing left."""
    scale = scale or (4 if k == 1 else 3)
    poses = [('idle', {}), ('wave', dict(pose='wave')), ('hold sword', dict(held='sword')),
             ('walk 1', dict(pose='walk', frame=1)), ('facing left', dict(facing='left', held='sword')),
             ('facing right', dict(facing='right', held='torch')), ('villager cross', {}),
             ('villager hold', dict(pose='hold')), ('villager wave', dict(pose='wave')),
             ('zombie walk 0', dict(pose='walk', frame=0))]
    cells = []
    for lab, kw in poses:
        n = 'villager_librarian' if lab.startswith('villager') else 'zombie' if lab.startswith('zombie') else 'player'
        cells.append((lab, _big(render(n, k, **kw), scale)))
    s1 = _grid(cells, 10, 'poses and facing')
    s2 = _grid([(it + (' gold' if it == 'pickaxe' else ''), _big(render('player', k, held=it,
                held_mat='gold' if it == 'pickaxe' else None, shadow=False), scale)) for it in ITEMS], 8,
               'held items (player, pose hold)')
    pal = [('default', {}), ('tan / black / blue', dict(skin='tan', hair='black', top='blue')),
           ('brown / blonde / green', dict(skin='brown', hair='blonde', top='green', bottom='cloth_brown')),
           ('dark / white / purple', dict(skin='dark', hair='white', top='purple', bottom='cloth_black')),
           ('light / ginger / #2f9a8a', dict(skin='light', hair='ginger', top='#2f9a8a', eye='iris_blue'))]
    cells = [(lab, _big(render('player', k, **kw), scale)) for lab, kw in pal]
    cells += [('sheep ' + c, _big(render('sheep', k, colour=c), scale)) for c in ('pink', 'cloth_black', 'yellow')]
    cells += [('horse #e8e0d0', _big(render('horse', k, colour='#e8e0d0'), scale)),
              ('slime #e0603a', _big(render('slime', k, colour='#e0603a'), scale)),
              ('axolotl #f2d050', _big(render('axolotl', k, colour='#f2d050'), scale)),
              ('wolf wild', _big(render('wolf', k, collar=False), scale))]
    s3 = _grid(cells, 6, 'colour variants (PALETTE names or #hex)')
    cells = [(n + ' left', _big(render(n, k, facing='left'), scale)) for n in ('cow', 'pig', 'fox', 'cat', 'parrot',
                                                                             'bee')]
    s4 = _grid(cells, 6, 'animals facing left (the light stays top-left)')
    _stack([s1, s2, s3, s4]).save(out)
    return out


def _flag(a, name, default=None):
    if name in a:
        i = a.index(name)
        v = a[i + 1] if i + 1 < len(a) else default
        del a[i:i + 2]
        return v
    return default


def main(argv):
    a = list(argv)
    hd = '--hd' in a
    if hd:
        a.remove('--hd')
    k = 2 if hd else 1
    opts = {}
    for key in ('pose', 'facing', 'held', 'held_mat', 'skin', 'hair', 'top', 'bottom', 'shoes', 'eye', 'accent'):
        v = _flag(a, '--' + key.replace('_', '-'))
        if v is not None:
            opts[key] = None if v in ('none', 'None') else v
    fr = _flag(a, '--frame')
    if fr is not None:
        opts['frame'] = int(fr)
    while '--opt' in a:                                     # --opt shield=False, --opt colour=pink
        kv = _flag(a, '--opt')
        key, _, v = kv.partition('=')
        opts[key] = {'True': True, 'False': False, 'None': None}.get(v, int(v) if v.lstrip('-').isdigit() else v)
    if '--no-shadow' in a:
        a.remove('--no-shadow')
        opts['shadow'] = False
    if not a or a[0] in ('-h', '--help'):
        print(__doc__)
        return 0
    cmd = a[0]
    if cmd == 'list':
        print('characters:', ', '.join(CATALOG))
        print('poses:', ', '.join(POSES))
        print('held items:', ', '.join(ITEMS), '| materials:', ', '.join(ITEM_MAT))
        print('palette:', ', '.join(PALETTE))
        print('switches (--opt key=value):', '; '.join(f'{n}: {v}' for n, v in SWITCHES.items()))
    elif cmd == 'chart' and len(a) == 2:
        chart(a[1], k)
        print('chart ->', a[1])
    elif cmd == 'render' and len(a) == 3:
        render(a[1], k, **opts).save(a[2])
        print(a[1], '->', a[2])
    elif cmd == 'parts' and len(a) == 3:
        meta = export_parts(a[1], a[2], k, **opts)
        print(f'{a[1]}: {len(meta["layers"])} parts -> {a[2]}/')
    elif cmd == 'extras' and len(a) == 2:
        extras(a[1], k)
        print('extras ->', a[1])
    elif cmd == 'walk' and len(a) == 3:
        walk_sheet(a[1], k, **opts).save(a[2])
        print(a[1], 'walk ->', a[2])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
