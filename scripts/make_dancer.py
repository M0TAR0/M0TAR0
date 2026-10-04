#!/usr/bin/env python3
"""Generates dancer.svg: a pixel-art anime dancer close-up with SMIL animation.

Usage: python3 scripts/make_dancer.py [out.svg] [--pose N]   (--pose renders a static frame)
"""
import math
import sys

S = 8                 # screen px per art pixel
W, H = 96, 54         # art grid
BAR = 5               # letterbox rows (top and bottom)
BEAT = 0.5            # seconds per beat (120 bpm)
CYCLE = BEAT * 4

OUT = "#150a2a"
SKIN, SKIN_D = "#f9d0b0", "#e8a985"
HAIR, HAIR_D, HAIR_L = "#2b2150", "#1a1236", "#5446b0"
TEAL, TEAL_D, TEAL_L = "#35d8c9", "#1b8f9a", "#b9fff4"
JACKET, JACKET_D, JACKET_L = "#e0304a", "#a5203a", "#ff6d82"
GREEN, GREEN_D, GREEN_L = "#22b866", "#14804a", "#7cf0ac"
WHITE = "#f6f2ff"
BLUSH = "#ff8fa3"


# ---------- pixel helpers ----------
def rect(P, x0, y0, x1, y1, c):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            P[(x, y)] = c


def disc(P, cx, cy, rx, ry, c, shape=None):
    for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
        for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
            dx, dy = (x - cx) / rx, (y - cy) / ry
            if dx * dx + dy * dy <= 1 and (shape is None or shape(x, y)):
                P[(x, y)] = c


def line(P, x0, y0, x1, y1, r, c):
    n = int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 1
    for i in range(n + 1):
        t = i / n
        disc(P, x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, r, r, c)


def stroke(src, dst, color, diag=False):
    """Paint `color` on every cell next to `src` that isn't in `src`."""
    nb = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    if diag:
        nb += [(1, 1), (-1, 1), (1, -1), (-1, -1)]
    for (x, y) in list(src):
        for dx, dy in nb:
            n = (x + dx, y + dy)
            if n not in src:
                dst[n] = color


def stamp(P, x0, y0, rows, pal, flip=False):
    for j, row in enumerate(rows):
        if flip:
            row = row[::-1]
        for i, ch in enumerate(row):
            if ch in pal:
                P[(x0 + i, y0 + j)] = pal[ch]


def mirror(P):
    return {(W - 1 - x, y): c for (x, y), c in P.items()}


def to_rects(P, dx=0, dy=0):
    out = []
    rows = {}
    for (x, y), c in P.items():
        rows.setdefault((y, c), []).append(x)
    for (y, c), xs in sorted(rows.items()):
        xs.sort()
        start = prev = xs[0]
        for x in xs[1:] + [None]:
            if x is not None and x == prev + 1:
                prev = x
                continue
            out.append(f'<rect x="{(start + dx) * S}" y="{(y + dy) * S}" '
                       f'width="{(prev - start + 1) * S}" height="{S}" fill="{c}"/>')
            if x is not None:
                start = prev = x
    return "\n".join(out)


def anim_discrete(attr, values, dur, kind="animateTransform", ttype="translate"):
    n = len(values)
    kt = ";".join(f"{i / n:.4f}" for i in range(n))
    vs = ";".join(values)
    if kind == "animateTransform":
        return (f'<animateTransform attributeName="transform" type="{ttype}" dur="{dur}s" '
                f'repeatCount="indefinite" calcMode="discrete" keyTimes="{kt}" values="{vs}"/>')
    return (f'<animate attributeName="{attr}" dur="{dur}s" repeatCount="indefinite" '
            f'calcMode="discrete" keyTimes="{kt}" values="{vs}"/>')


# ---------- background ----------
def background():
    P = {}
    bands = ["#12082e", "#1a0b3d", "#240f4d", "#31145c", "#43196b", "#5a1f78", "#74267f", "#8f2e84"]
    for y in range(H):
        P_row = bands[min(len(bands) - 1, y * len(bands) // H)]
        for x in range(W):
            P[(x, y)] = P_row
    # subtle diagonal grid-ish dither
    for y in range(0, H, 2):
        for x in range((y // 2) % 2, W, 2):
            if y > 30:
                P[(x, y)] = "#99358a"
    return P


def sun():
    P = {}
    cx, cy, r = 48, 27, 31
    top, bot = (0xff, 0xd1, 0x66), (0xef, 0x47, 0x6f)
    for y in range(cy - r, cy + r + 1):
        t = (y - (cy - r)) / (2 * r)
        col = "#%02x%02x%02x" % tuple(int(a + (b - a) * t) for a, b in zip(top, bot))
        for x in range(cx - r, cx + r + 1):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                P[(x, y)] = col
    # retro cut stripes in the lower half
    gaps = [(36, 36), (40, 41), (44, 46), (49, 52)]
    for a, b in gaps:
        for y in range(a, b + 1):
            for x in range(cx - r, cx + r + 1):
                P.pop((x, y), None)
    return P


def eq_bars(x0, n):
    """Returns svg for n equalizer bars starting at column x0."""
    pal = ["#35d8c9", "#4fe0b4", "#7cf0ac", "#ffd166", "#ff8fa3", "#ef476f"]
    svg = []
    base = 47
    for i in range(n):
        x = x0 + i * 3
        hs = [3 + ((i * 7 + k * 5) % 9) for k in range(8)]
        ys = ";".join(str((base - h) * S) for h in hs)
        hh = ";".join(str(h * S) for h in hs)
        kt = ";".join(f"{k / 8:.4f}" for k in range(8))
        col = pal[i % len(pal)]
        svg.append(
            f'<rect x="{x * S}" y="{(base - hs[0]) * S}" width="{2 * S}" height="{hs[0] * S}" fill="{col}">'
            f'<animate attributeName="y" dur="{CYCLE}s" repeatCount="indefinite" calcMode="discrete" keyTimes="{kt}" values="{ys}"/>'
            f'<animate attributeName="height" dur="{CYCLE}s" repeatCount="indefinite" calcMode="discrete" keyTimes="{kt}" values="{hh}"/>'
            f'</rect>')
    return "\n".join(svg)


NOTE = ["..###",
        "..#..",
        "..#..",
        "..#..",
        "###..",
        "###.."]


def notes():
    svg = []
    spots = [(14, "#7cf0ac", 0.0), (82, "#ffd166", 1.1), (22, "#ff8fa3", 2.1), (72, "#35d8c9", 3.0)]
    for x, col, delay in spots:
        P = {}
        stamp(P, 0, 0, NOTE, {"#": col})
        svg.append(
            f'<g opacity="0"><g transform="translate({x * S},{40 * S})">'
            f'{to_rects(P)}'
            f'<animateTransform attributeName="transform" type="translate" additive="sum" dur="4s" begin="{delay}s" '
            f'repeatCount="indefinite" values="0,0;{3 * S},{-14 * S};{-2 * S},{-28 * S};{2 * S},{-36 * S}" keyTimes="0;0.35;0.7;1" calcMode="discrete"/>'
            f'</g>'
            f'<animate attributeName="opacity" dur="4s" begin="{delay}s" repeatCount="indefinite" '
            f'values="0;1;1;0" keyTimes="0;0.1;0.8;1"/></g>')
    return "\n".join(svg)


def sparkles():
    svg = []
    pts = [(10, 12, 0.0), (86, 10, 0.4), (24, 26, 0.9), (73, 24, 1.3), (6, 36, 1.7), (90, 34, 0.2), (30, 9, 1.1), (66, 8, 1.6)]
    for i, (x, y, d) in enumerate(pts):
        P = {}
        for dx, dy in [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)]:
            P[(x + dx, y + dy)] = "#ffffff"
        P[(x + 2, y)] = P[(x - 2, y)] = P[(x, y + 2)] = P[(x, y - 2)] = "#b9fff4"
        svg.append(f'<g opacity="0">{to_rects(P)}'
                   f'<animate attributeName="opacity" dur="{CYCLE}s" begin="{d}s" repeatCount="indefinite" '
                   f'calcMode="discrete" keyTimes="0;0.25;0.5;0.75" values="0;1;0.4;1"/></g>')
    return "\n".join(svg)


# ---------- character ----------
SHOULDER = (63, 46)
ARM_POSES = {
    "up":   ((76, 38), (78, 19)),
    "mid":  ((77, 45), (75, 31)),
    "down": ((76, 51), (81, 58)),
}


def arm(pose, side):
    (ex, ey), (hx, hy) = ARM_POSES[pose]
    sx, sy = SHOULDER
    P, fill = {}, {}
    line(fill, sx, sy, ex, ey, 3.2, JACKET)
    line(fill, ex, ey, hx, hy, 2.6, SKIN)
    # sleeve cuff in green
    cx, cy = ex + (hx - ex) * 0.25, ey + (hy - ey) * 0.25
    line(fill, ex, ey, cx, cy, 2.9, GREEN)
    disc(fill, hx, hy, 3.4, 3.4, SKIN)         # hand
    for k in [(-1, -1), (0, -1), (1, -1)]:       # fingers hint
        fill[(int(hx) + k[0] * 2, int(hy) - 3)] = SKIN
    P.update(fill)
    # sleeve shade
    for (x, y), c in list(fill.items()):
        if c == JACKET and (x + y) % 5 == 0:
            P[(x, y)] = JACKET_D
    stroke(fill, P, OUT)
    return P if side == "R" else mirror(P)


def torso():
    P = {}
    for y in range(40, H):
        hw = 14 + (y - 40) * 1.1
        for x in range(int(48 - hw), int(48 + hw) + 1):
            P[(x, y)] = JACKET
    body = dict(P)
    # shading on right flank + highlights on left shoulder
    for (x, y) in body:
        if x > 48 + 8 + (y - 40) * 0.4:
            P[(x, y)] = JACKET_D
        if y in (41, 42) and 36 < x < 42:
            P[(x, y)] = JACKET_L
    shirt = {}
    for y in range(40, H):
        hw = 7 - (y - 40) * 0.45
        if hw < 1.5:
            hw = 1.5
        for x in range(int(48 - hw), int(48 + hw) + 1):
            shirt[(x, y)] = WHITE
    for k, c in shirt.items():
        if k in P:
            P[k] = c
    # green lapels around the shirt
    lap = {}
    stroke(shirt, lap, GREEN)
    for k, c in lap.items():
        if k in body:
            P[k] = c
    # shirt shadow near neck
    for x in range(44, 53):
        P[(x, 40)] = SKIN_D
    # a white stripe on the jacket (Mexican flag nod: green / white / red)
    for y in range(48, H):
        for x in range(int(48 - (14 + (y - 40) * 1.1)) + 4, int(48 - (14 + (y - 40) * 1.1)) + 7):
            P[(x, y)] = WHITE if x % 3 else GREEN
    stroke(body, P, OUT)
    return P


def neck():
    P = {}
    rect(P, 44, 33, 51, 41, SKIN_D)
    rect(P, 44, 33, 49, 40, SKIN)
    stroke(P, P, OUT)
    return P


def tail(side):
    P = {}
    pts = [(35, 17, 3.2), (31, 24, 3.6), (30, 32, 3.4), (32, 39, 3.0), (35, 45, 2.0)]
    for a, b in zip(pts, pts[1:]):
        n = 12
        for i in range(n + 1):
            t = i / n
            r = a[2] + (b[2] - a[2]) * t
            disc(P, a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, r, r, HAIR)
    fill = dict(P)
    for (x, y) in fill:
        if x <= 30 + (y > 36) and (x + y) % 3 == 0:
            P[(x, y)] = HAIR_L
        if x >= 33:
            P[(x, y)] = HAIR_D if (x + y) % 2 == 0 else HAIR
    # scrunchie
    rect(P, 32, 20, 36, 22, GREEN)
    P[(32, 20)] = GREEN_L
    stroke(fill, P, OUT)
    return P if side == "L" else mirror(P)


# bang bottoms for x = 36..60
BANGS = [27, 25, 23, 21, 18, 20, 19, 17, 19, 20, 17, 15, 14, 15, 17, 20, 19, 17, 18, 20, 21, 23, 25, 27, 28]

EYE = ["DDDDDD",
       "DHBBBD",
       "DHPPBD",
       "DTPPTD",
       "DTTLTD",
       ".DDDD."]
EYE_PAL = {"D": OUT, "H": WHITE, "B": TEAL_D, "P": OUT, "T": TEAL, "L": TEAL_L}


def head(eyes_open=True):
    P = {}
    # hair back
    disc(P, 48, 21, 15.5, 15, HAIR)
    back = dict(P)
    # face
    face = {}
    for y in range(12, 37):
        t = (y - 24) / 12.5
        if abs(t) > 1:
            continue
        hw = 10.7 * math.sqrt(max(0, 1 - t * t))
        if t > 0:
            hw *= (1 - 0.28 * t)
        for x in range(int(48 - hw + 0.5), int(48 + hw + 0.5) + 1):
            face[(x, y)] = SKIN
    P.update(face)
    # soft shade on the right cheek / jaw
    for (x, y), c in face.items():
        if x >= 55 and y > 27:
            P[(x, y)] = SKIN_D
        if y >= 34 and x > 46:
            P[(x, y)] = SKIN_D
    # eyes
    for x0 in (39, 52):
        if eyes_open:
            stamp(P, x0, 22, EYE, EYE_PAL, flip=(x0 == 52))
        else:
            for x in range(x0, x0 + 6):
                P[(x, 25)] = OUT
            P[(x0, 26)] = P[(x0 + 5, 26)] = OUT
    # brows
    for x in range(39, 45):
        P[(x, 20 - (1 if x > 41 else 0))] = HAIR_D
    for x in range(52, 58):
        P[(x, 20 - (1 if x < 55 else 0))] = HAIR_D
    # blush + nose + mouth
    for x in (39, 40, 41, 55, 56, 57):
        P[(x, 29)] = BLUSH
    P[(48, 28)] = SKIN_D
    for x in range(45, 52):
        P[(x, 31)] = OUT
    P[(44, 30)] = P[(52, 30)] = OUT
    for x in range(46, 51):
        P[(x, 32)] = "#ff5d78"
    P[(47, 33)] = P[(48, 33)] = P[(49, 33)] = OUT
    # hair front (bangs + side locks)
    front = {}
    for i, bot in enumerate(BANGS):
        x = 36 + i
        top = 21 - 12 * math.sqrt(max(0, 1 - ((x - 48) / 13.7) ** 2))
        for y in range(int(math.ceil(top)), bot + 1):
            front[(x, y)] = HAIR
    for y in range(20, 30):
        front[(36, y)] = front[(37, y)] = HAIR
        front[(59, y)] = front[(60, y)] = HAIR
    for (x, y) in list(front):
        if y == 11 + (x % 4 == 0) and 40 <= x <= 56:
            front[(x, y)] = HAIR_L
        if (x - y) % 7 == 0 and y < 17:
            front[(x, y)] = HAIR_L
    P.update(front)
    stroke(set(front), P, HAIR_D)
    # headphone band + cups
    band = {}
    for ang in range(180, 361, 2):
        a = math.radians(ang)
        for r in (14.2, 15.2):
            band[(int(round(48 + r * math.cos(a))), int(round(19 + 13.5 * math.sin(a))))] = GREEN
    P.update(band)
    stroke(set(band), P, OUT)
    for x0 in (32, 60):
        cup = {}
        rect(cup, x0, 20, x0 + 4, 30, GREEN)
        rect(cup, x0 + 3 if x0 == 32 else x0, 21, x0 + 4 if x0 == 32 else x0 + 1, 29, GREEN_D)
        rect(cup, x0 + (1 if x0 == 32 else 3), 22, x0 + (1 if x0 == 32 else 3), 24, GREEN_L)
        P.update(cup)
        stroke(set(cup), P, OUT)
    sil = {}
    stroke(set(P), sil, OUT)
    for k, c in sil.items():
        P.setdefault(k, c)
    return P


# ---------- assembly ----------
def build(animate=True, pose=0):
    bg = background()
    sunP = sun()
    torsoP, neckP = torso(), neck()
    tails = [tail("L"), tail("R")]
    headO, headC = head(True), head(False)
    # which arms in which beat: (left-screen arm, right-screen arm)
    poses = [("down", "up"), ("mid", "mid"), ("up", "down"), ("up", "up")]
    # visible (open) eye cells differ from closed: only draw closed eyes as an overlay of the diff
    closed_diff = {k: v for k, v in headC.items() if headO.get(k) != v}
    open_diff = {k: v for k, v in headO.items() if headC.get(k) != v}

    o = []
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W * S} {H * S}" width="{W * S}" height="{H * S}" '
             f'shape-rendering="crispEdges">')
    o.append('<title>Pixel-art anime dancer</title>')
    o.append('<defs>'
             '<radialGradient id="vig" cx="50%" cy="50%" r="75%"><stop offset="55%" stop-color="#000" stop-opacity="0"/>'
             '<stop offset="100%" stop-color="#000" stop-opacity="0.65"/></radialGradient>'
             f'<pattern id="scan" width="{S}" height="{S}" patternUnits="userSpaceOnUse"><rect width="{S}" height="2" fill="#000" opacity="0.1"/></pattern>'
             '</defs>')
    o.append(to_rects(bg))
    o.append('<g>' + to_rects(sunP))
    if animate:
        o.append(f'<animate attributeName="opacity" dur="{BEAT}s" repeatCount="indefinite" calcMode="discrete" '
                 f'keyTimes="0;0.5" values="1;0.88"/>')
    o.append('</g>')
    o.append(sparkles() if animate else "")
    o.append(eq_bars(3, 6))
    o.append(eq_bars(75, 6))
    if animate:
        o.append(notes())

    # ----- dancer: sway group -----
    o.append('<g>')
    if animate:
        # 8 half-beat steps: x leans per beat, small bounce on every off-beat
        xs = [-1, -1, 0, 0, 1, 1, 0, 0]
        ys = [0, 1, 0, 1, 0, 1, 0, 1]
        vals = [f"{x * S},{y * S}" for x, y in zip(xs, ys)]
        o.append(anim_discrete("transform", vals, CYCLE))

    # arms
    for i, (l, r) in enumerate(poses):
        vis = "visible" if (not animate and i == pose) or (animate and i == 0) else "hidden"
        o.append(f'<g visibility="{vis}">')
        o.append(to_rects(arm(l, "L")))
        o.append(to_rects(arm(r, "R")))
        if animate:
            vals = ["visible" if k == i else "hidden" for k in range(4)]
            o.append(anim_discrete("visibility", vals, CYCLE, kind="animate"))
        o.append('</g>')

    o.append(to_rects(torsoP))
    o.append(to_rects(neckP))

    # tails (swing opposite to the lean)
    o.append('<g>')
    o.append(to_rects(tails[0]) + to_rects(tails[1]))
    if animate:
        tv = [f"{x * S},{y * S}" for x, y in [(0, 0), (1, 0), (0, 1), (-1, 0), (0, 0), (1, 0), (0, 1), (-1, 0)]]
        o.append(anim_discrete("transform", tv, CYCLE))
    o.append('</g>')

    # head (extra sway + bob)
    o.append('<g>')
    o.append(to_rects(headO))
    # blink overlay
    o.append('<g visibility="hidden">' + to_rects({k: v for k, v in headC.items() if k in closed_diff}) )
    if animate:
        o.append('<animate attributeName="visibility" dur="3.5s" repeatCount="indefinite" calcMode="discrete" '
                 'keyTimes="0;0.9;0.95" values="hidden;visible;hidden"/>')
    o.append('</g>')
    if animate:
        hx = [-1, 0, 0, -1, 1, 0, 0, 1]
        hy = [0, 0, -1, 0, 0, 0, -1, 0]
        hv = [f"{x * S},{y * S}" for x, y in zip(hx, hy)]
        o.append(anim_discrete("transform", hv, CYCLE))
    o.append('</g>')
    o.append('</g>')

    # ----- cinematic finish -----
    o.append(f'<rect width="{W * S}" height="{H * S}" fill="url(#scan)"/>')
    o.append(f'<rect width="{W * S}" height="{H * S}" fill="url(#vig)"/>')
    o.append(f'<rect width="{W * S}" height="{BAR * S}" fill="#000"/>')
    o.append(f'<rect y="{(H - BAR) * S}" width="{W * S}" height="{BAR * S}" fill="#000"/>')
    rec = f'<rect x="{3 * S}" y="{2 * S - 4}" width="{S}" height="{S}" fill="#ff2d4a">'
    if animate:
        rec += '<animate attributeName="opacity" dur="1s" repeatCount="indefinite" calcMode="discrete" keyTimes="0;0.5" values="1;0"/>'
    rec += '</rect>'
    o.append(rec)
    o.append(f'<text x="{5 * S}" y="{3 * S - 2}" font-family="monospace" font-size="14" fill="#d9d4ee">REC</text>')
    o.append('</svg>')
    return "\n".join(s for s in o if s)


if __name__ == "__main__":
    args = sys.argv[1:]
    pose = None
    if "--pose" in args:
        i = args.index("--pose")
        pose = int(args[i + 1])
        del args[i:i + 2]
    out = args[0] if args else "dancer.svg"
    svg = build(animate=pose is None, pose=pose or 0)
    with open(out, "w") as f:
        f.write(svg)
    print(out, len(svg) // 1024, "KB")
