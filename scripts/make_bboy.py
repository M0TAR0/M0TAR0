#!/usr/bin/env python3
"""Generates bboy.svg: a black & white pixel-art b-boy breakdancing across a wide banner.

Usage: python3 scripts/make_bboy.py [out.svg] [--frame N]   (--frame renders one static frame)
"""
import math
import sys

S = 8                  # screen px per art pixel
W, H = 120, 34         # art grid  -> 960 x 272
GY = 30                # floor row
FPS = 8
FACE = 1               # dancer faces right

OUT = "#000000"
SHIRT, SHIRT_F = "#f4f4f4", "#b4b4b4"
SKIN, SKIN_F = "#c4c4c4", "#8a8a8a"
PANTS, PANTS_F = "#7a7a7a", "#4e4e4e"
SHOE, SHOE_F = "#ffffff", "#cfcfcf"
HAT, HAT_BAND = "#ececec", "#2a2a2a"


# ---------- pixel helpers ----------
def disc(P, cx, cy, r, c):
    for y in range(int(cy - r) - 1, int(cy + r) + 2):
        for x in range(int(cx - r) - 1, int(cx + r) + 2):
            if (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 <= r * r:
                P[(x, y)] = c


def line(P, a, b, r, c):
    n = int(max(abs(b[0] - a[0]), abs(b[1] - a[1])) * 2) + 1
    cells = {}
    for i in range(n + 1):
        t = i / n
        disc(cells, a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, r, c)
    return cells


def paint(P, cells, outline=True):
    if outline:
        for (x, y) in cells:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (x + dx, y + dy)
                if n not in cells:
                    P[n] = OUT
    P.update(cells)


def to_paths(P, k=S):
    by_color = {}
    for (x, y), c in P.items():
        by_color.setdefault(c, {}).setdefault(y, []).append(x)
    out = []
    for c, rows in sorted(by_color.items()):
        d = []
        for y, xs in sorted(rows.items()):
            xs.sort()
            start = prev = xs[0]
            for x in xs[1:] + [None]:
                if x is not None and x == prev + 1:
                    prev = x
                    continue
                d.append(f"M{start * k} {y * k}h{(prev - start + 1) * k}v{k}h-{(prev - start + 1) * k}z")
                if x is not None:
                    start = prev = x
        out.append(f'<path fill="{c}" d="{"".join(d)}"/>')
    return "".join(out)


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def ang(o, deg, l):
    r = math.radians(deg)
    return (o[0] + math.cos(r) * l, o[1] + math.sin(r) * l)


def limb(o, a1, l1, a2, l2):
    k = ang(o, a1, l1)
    return k, ang(k, a2, l2)


# ---------- skeleton ----------
KEYS = ["head", "neck", "hip", "shL", "shR", "elL", "elR", "haL", "haR", "hpL", "hpR", "knL", "knR", "ftL", "ftR"]


def skeleton(**j):
    return {k: j[k] for k in KEYS}


def blend(a, b, t):
    return {k: lerp(a[k], b[k], t) for k in KEYS}


def toprock(rx, ph, bob=True):
    a = 2 * math.pi * ph
    hip = (rx, GY - 11.4 + (0.9 * abs(math.sin(a)) if bob else 0))
    tilt = 7 * math.sin(a)
    neck = ang(hip, -90 + tilt, 8)
    head = ang(neck, -90 + tilt * 1.6 + 8, 4.6)
    legs = {}
    for s, off in (("L", math.pi), ("R", 0)):
        p = a + off
        th = 90 - 30 * math.sin(p)
        flex = 55 * max(0, math.sin(p))
        legs[s] = limb(hip, th, 5.6, th + flex, 5.6)
    arms = {}
    sh = (neck[0] + 0.3, neck[1] + 1)
    for s, off in (("L", 0), ("R", math.pi)):
        p = a + off
        up = 90 + 40 * math.sin(p)
        arms[s] = limb(sh, up, 4.3, up - 55, 4.0)
    return skeleton(head=head, neck=neck, hip=hip, shL=sh, shR=sh, elL=arms["L"][0], elR=arms["R"][0],
                    haL=arms["L"][1], haR=arms["R"][1], hpL=hip, hpR=hip,
                    knL=legs["L"][0], knR=legs["R"][0], ftL=legs["L"][1], ftR=legs["R"][1])


def moonwalk(rx, ph):
    """Moonwalk: feet glide backwards while he leans back and tips his cap."""
    a = 2 * math.pi * ph
    hip = (rx, GY - 10.6 + 0.35 * abs(math.sin(a)))
    neck = ang(hip, -97, 8)
    head = ang(neck, -92, 4.6)
    legs = {}
    for s, shift in (("L", 0.0), ("R", 0.5)):
        u = (ph + shift) % 1.0
        if u < 0.5:                                  # flat foot slides back under the body
            fx, lift = 3.4 - 6.8 * (u / 0.5), 0.0
        else:                                        # other foot resets on its toes
            v = (u - 0.5) / 0.5
            fx, lift = -3.4 + 6.8 * v, 2.2 * math.sin(math.pi * v)
        foot = (hip[0] + fx, GY - 0.4 - lift)
        mid = lerp(hip, foot, 0.5)
        d = math.hypot(foot[0] - hip[0], foot[1] - hip[1])
        bulge = math.sqrt(max(0.0, 5.6 ** 2 - (d / 2) ** 2))
        n = ((foot[1] - hip[1]) / d, -(foot[0] - hip[0]) / d)       # perpendicular, points forward
        if n[0] < 0:
            n = (-n[0], -n[1])
        legs[s] = ((mid[0] + n[0] * bulge, mid[1] + n[1] * bulge), foot)
    sh = (neck[0] + 0.3, neck[1] + 1.0)
    swing = 90 + 24 * math.sin(a)
    elL, haL = limb(sh, swing, 4.3, swing - 40, 4.0)
    haR = (head[0] + 3.4, head[1] + 0.6)                      # hand on the cap brim
    elR = (sh[0] + 3.2, sh[1] + 2.6)
    return skeleton(head=head, neck=neck, hip=hip, shL=sh, shR=sh, elL=elL, elR=elR, haL=haL, haR=haR,
                    hpL=hip, hpR=hip, knL=legs["L"][0], knR=legs["R"][0], ftL=legs["L"][1], ftR=legs["R"][1])


# local poses for the flip, relative to the hip (hb = hip height above the floor)
def _lp(hb, head, neck, sh, elL, elR, haL, haR, knL, knR, ftL, ftR):
    return dict(hb=hb, head=head, neck=neck, shL=sh, shR=sh, elL=elL, elR=elR, haL=haL, haR=haR,
                knL=knL, knR=knR, ftL=ftL, ftR=ftR)


F_STAND = _lp(11.4, (0.6, -12.6), (0.2, -8), (0.3, -7.2), (-1.2, -3.5), (1.2, -3.5), (-0.8, 0.5), (1.0, 0.5),
              (0.2, 5.5), (-0.2, 5.5), (0.4, 11.4), (-0.4, 11.4))
F_CROUCH = _lp(7.6, (3.6, -11.6), (2.4, -7.4), (2.5, -6.4), (4.2, -3.0), (4.8, -2.6), (6.0, -0.2), (6.4, 0.2),
               (3.6, 3.2), (3.2, 3.2), (0.6, 7.6), (0.2, 7.6))
F_LAUNCH = _lp(11.2, (0.8, -12.6), (0.3, -8), (0.4, -7.2), (1.2, -12.2), (2.0, -12.0), (1.4, -16.6), (2.4, -16.4),
               (0.0, 5.5), (-0.2, 5.5), (0.2, 11.2), (-0.2, 11.2))
F_TUCK = _lp(11.0, (4.8, -8.6), (2.8, -6.6), (2.8, -5.8), (3.4, -2.6), (2.6, -2.2), (4.0, 1.0), (3.6, 1.4),
             (4.6, -1.6), (4.4, -1.2), (1.0, 3.8), (0.6, 4.2))
F_OPEN = _lp(11.0, (0.8, -12.6), (0.3, -8), (0.4, -7.2), (3.2, -8.8), (-2.6, -8.6), (5.8, -10.0), (-5.0, -10.5),
             (0.4, 5.5), (-0.4, 5.5), (0.8, 11.2), (-0.8, 11.2))
F_KEYS = [(0.0, F_STAND), (0.12, F_CROUCH), (0.26, F_LAUNCH), (0.46, F_TUCK), (0.66, F_TUCK),
          (0.8, F_OPEN), (0.9, F_CROUCH), (1.0, F_STAND)]


def _flip_pose(ph):
    for (t0, p0), (t1, p1) in zip(F_KEYS, F_KEYS[1:]):
        if t0 <= ph <= t1:
            f = (ph - t0) / (t1 - t0)
            return {k: (p0[k] + (p1[k] - p0[k]) * f if k == "hb" else lerp(p0[k], p1[k], f)) for k in p0}
    return F_STAND


def flip(rx, ph):
    """Front flip: crouch, launch, tuck, spin once around the body's centre, open up and land."""
    ph = ph % 1.0
    lp = _flip_pose(ph)
    u = min(1.0, max(0.0, (ph - 0.2) / 0.45))
    theta = 2 * math.pi * (u * u * (3 - 2 * u))
    fu = min(1.0, max(0.0, (ph - 0.2) / 0.6))
    lift = 8.0 * math.sin(math.pi * fu)
    hip_w = (rx, GY - lp["hb"] - lift)
    c = (1.0, -3.0)
    cs, sn = math.cos(theta), math.sin(theta)

    def tf(j):
        dx, dy = j[0] - c[0], j[1] - c[1]
        return (hip_w[0] + c[0] + dx * cs - dy * sn, hip_w[1] + c[1] + dx * sn + dy * cs)

    out = {k: tf(lp[k]) for k in lp if k != "hb"}
    out["hip"] = tf((0.0, 0.0))
    out["hpL"] = out["hpR"] = out["hip"]
    return {k: out[k] for k in KEYS}


def headspin(rx, ph):
    a = 2 * math.pi * ph * 2
    head = (rx, GY - 3.0)
    neck = (rx, GY - 5.2)
    hip = (rx, GY - 13.2)
    legs = {}
    for s, off in (("L", 0.0), ("R", math.pi * 0.75)):
        p = a + off
        foot = (hip[0] + 5.2 * math.cos(p), hip[1] - 8.4 + 0.8 * math.sin(p))
        knee = (hip[0] + 3.4 * math.cos(p), hip[1] - 4.6)
        legs[s] = (knee, foot)
    return skeleton(head=head, neck=neck, hip=hip, shL=neck, shR=neck,
                    elL=(rx - 3.4, GY - 3.2), elR=(rx + 3.4, GY - 3.2), haL=(rx - 4.8, GY - 0.4), haR=(rx + 4.8, GY - 0.4),
                    hpL=hip, hpR=hip, knL=legs["L"][0], knR=legs["R"][0], ftL=legs["L"][1], ftR=legs["R"][1])


def freeze(rx, ph):
    a = 2 * math.pi * ph
    sway = 0.5 * math.sin(a)
    neck = (rx + sway * 0.4, GY - 9.0)
    hip = (rx + 0.6 + sway, GY - 17.0)
    head = (rx + 1.6, GY - 6.6)
    sp = 4.6 + 0.8 * math.sin(a)
    kL, fL = (hip[0] - 3.2 - 0.5 * math.sin(a), hip[1] - 4.0), (hip[0] - sp - 1.6, hip[1] - 9.0)
    kR, fR = (hip[0] + 3.4, hip[1] - 4.4), (hip[0] + 1.4, hip[1] - 9.4 + 0.6 * math.sin(a))   # bent leg, foot to knee
    return skeleton(head=head, neck=neck, hip=hip, shL=neck, shR=neck,
                    elL=(rx - 0.6, GY - 4.6), elR=(rx + 0.8, GY - 4.6), haL=(rx - 0.8, GY - 0.4), haR=(rx + 1.2, GY - 0.4),
                    hpL=hip, hpR=hip, knL=kL, knR=kR, ftL=fL, ftR=fR)


# ---------- timeline ----------
# (move, seconds, x_start, x_end, cycles)
TIMELINE = [
    (toprock, 3.0, -9, 50, 3.0),
    (moonwalk, 2.0, 50, 40, 2.0),
    (flip, 2.5, 40, 72, 2.0),
    (headspin, 1.25, 72, 78, 1.25),
    (freeze, 1.5, 78, 80, 1.0),
    (toprock, 1.5, 80, 130, 2.0),
]
BLEND = 2


def build_frames():
    frames, xs = [], []
    prev = None
    for move, secs, x0, x1, cyc in TIMELINE:
        n = int(round(secs * FPS))
        seq = []
        for i in range(n):
            t = i / n
            seq.append((move(x0 + (x1 - x0) * t, cyc * t), x0 + (x1 - x0) * t))
        if prev is not None:
            for k in range(1, BLEND + 1):
                f = k / (BLEND + 1)
                frames.append(blend(prev[0], seq[0][0], f))
                xs.append(prev[1] + (seq[0][1] - prev[1]) * f)
        for sk, x in seq:
            frames.append(sk)
            xs.append(x)
        prev = seq[-1]
    return frames, xs


# ---------- rendering ----------
def render_sk(sk):
    P = {}
    far, near = ("L", "R")
    cl = {"L": (SHIRT_F, SKIN_F, PANTS_F, SHOE_F), "R": (SHIRT, SKIN, PANTS, SHOE)}

    def leg(s):
        shirt, skin, pants, shoe = cl[s]
        hp, kn, ft = sk["hp" + s], sk["kn" + s], sk["ft" + s]
        paint(P, line({}, hp, kn, 1.6, pants))
        paint(P, line({}, kn, ft, 1.35, pants))
        d = (ft[0] - kn[0], ft[1] - kn[1])
        ln = math.hypot(*d) or 1
        if ft[1] > GY - 3 and abs(d[1]) > abs(d[0]) * 0.5 and sk["hip"][1] < GY - 8:
            toe = (ft[0] + FACE * 2.4, ft[1] + 0.3)     # standing feet point forward
        else:
            toe = (ft[0] + d[0] / ln * 2.2, ft[1] + d[1] / ln * 2.2)
        paint(P, line({}, ft, toe, 1.05, shoe))

    def arm(s):
        shirt, skin, pants, shoe = cl[s]
        sh, el, ha = sk["sh" + s], sk["el" + s], sk["ha" + s]
        paint(P, line({}, sh, el, 1.25, shirt))
        paint(P, line({}, el, ha, 1.05, skin))
        paint(P, line({}, ha, ha, 1.3, skin), outline=False)

    leg(far)
    arm(far)
    # torso (shirt) + pelvis (pants)
    paint(P, line({}, sk["hip"], sk["neck"], 2.4, SHIRT))
    pel = lerp(sk["hip"], sk["neck"], 0.3)
    paint(P, line({}, sk["hip"], pel, 2.45, PANTS), outline=False)
    leg(near)
    # head + cap
    h = {}
    hx, hy = sk["head"]
    disc(h, hx, hy, 2.9, SKIN)
    for (x, y) in list(h):
        if y + 0.5 < hy - 0.2:
            h[(x, y)] = HAT
        elif y + 0.5 < hy + 0.7 and x + 0.5 > hx - 2.6:
            h[(x, y)] = HAT_BAND
    for dx in (3, 4, 5):
        h[(int(hx + FACE * dx), int(hy - 0.4))] = HAT
    paint(P, h)
    arm(near)
    return P


def background():
    P = {}
    bricks_a, bricks_b = "#101010", "#151515"
    for y in range(GY + 1):
        for x in range(W):
            row = y // 3
            off = 4 if row % 2 else 0
            mortar = (y % 3 == 2) or ((x + off) % 8 == 7)
            P[(x, y)] = "#0b0b0b" if mortar else (bricks_b if (x + off) // 8 % 3 == row % 3 else bricks_a)
    for y in range(GY + 1, H):
        for x in range(W):
            P[(x, y)] = "#0a0a0a" if (x + y) % 4 else "#111111"
    for x in range(W):
        P[(x, GY + 1)] = "#3a3a3a"
    return P


def dust():
    out = []
    pts = [(14, 8, 0.0), (28, 18, 0.9), (44, 6, 1.7), (63, 14, 0.4), (80, 9, 1.3), (97, 20, 2.1), (108, 7, 0.7),
           (7, 22, 1.5), (52, 24, 2.6), (90, 26, 0.2)]
    for x, y, d in pts:
        out.append(f'<rect x="{x * S}" y="{y * S}" width="{S // 2}" height="{S // 2}" fill="#fff" opacity="0">'
                   f'<animate attributeName="opacity" dur="4s" begin="{d}s" repeatCount="indefinite" values="0;0.5;0" />'
                   f'<animate attributeName="y" dur="4s" begin="{d}s" repeatCount="indefinite" values="{y * S};{(y - 3) * S}" />'
                   f'</rect>')
    return "".join(out)


def vis_anim(i, n, dur):
    if i == 0:
        return (f'<animate attributeName="visibility" dur="{dur}s" repeatCount="indefinite" calcMode="discrete" '
                f'keyTimes="0;{1 / n:.5f}" values="visible;hidden"/>')
    end = (i + 1) / n
    kt = f"0;{i / n:.5f}" + (f";{end:.5f}" if i < n - 1 else "")
    vs = "hidden;visible" + (";hidden" if i < n - 1 else "")
    return (f'<animate attributeName="visibility" dur="{dur}s" repeatCount="indefinite" calcMode="discrete" '
            f'keyTimes="{kt}" values="{vs}"/>')


def build(only=None):
    frames, xs = build_frames()
    n = len(frames)
    dur = n / FPS
    animate = only is None
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W * S} {H * S}" width="{W * S}" height="{H * S}" '
         f'shape-rendering="crispEdges">',
         '<title>Pixel-art b-boy breakdancing</title>',
         '<defs>'
         '<linearGradient id="cone" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0.34"/>'
         '<stop offset="1" stop-color="#fff" stop-opacity="0.04"/></linearGradient>'
         '<radialGradient id="vig" cx="50%" cy="55%" r="80%"><stop offset="45%" stop-color="#000" stop-opacity="0"/>'
         '<stop offset="100%" stop-color="#000" stop-opacity="0.85"/></radialGradient>'
         f'<pattern id="scan" width="{S}" height="{S}" patternUnits="userSpaceOnUse"><rect width="{S}" height="2" fill="#000" opacity="0.18"/></pattern>'
         '</defs>']
    o.append(to_paths(background()))

    # spotlight following the dancer
    sx = [(x * S) for x in xs]
    cone = (f'<g transform="translate({sx[0] - 60 * S if only is None else xs[only] * S - 60 * S},0)">'
            f'<polygon points="{54 * S},0 {66 * S},0 {80 * S},{(GY + 1) * S} {40 * S},{(GY + 1) * S}" fill="url(#cone)"/>'
            f'<ellipse cx="{60 * S}" cy="{(GY + 1) * S + 3}" rx="{17 * S}" ry="{1.6 * S}" fill="#fff" opacity="0.16"/>')
    if animate:
        kt = ";".join(f"{i / n:.5f}" for i in range(n))
        vals = ";".join(f"{sx[i] - 60 * S:.1f},0" for i in range(n))
        cone += (f'<animateTransform attributeName="transform" type="translate" dur="{dur}s" repeatCount="indefinite" '
                 f'calcMode="discrete" keyTimes="{kt}" values="{vals}"/>')
    cone += '</g>'
    o.append(cone)

    def cast():
        g = []
        for i, sk in enumerate(frames):
            if only is not None and i != only:
                continue
            P = render_sk(sk)
            # shift joints are absolute already (x baked in); render at the frame's own x
            g.append(f'<g visibility="{"visible" if (not animate or i == 0) else "hidden"}">{to_paths(P, 1)}'
                     f'{vis_anim(i, n, dur) if animate else ""}</g>')
        return "".join(g)

    o.append(f'<g transform="scale({S})">{cast()}</g>')
    if animate:
        o.append(dust())
    o.append(f'<rect width="{W * S}" height="{H * S}" fill="url(#scan)"/>')
    o.append(f'<rect width="{W * S}" height="{H * S}" fill="url(#vig)"/>')
    rec = f'<rect x="{3 * S}" y="{2 * S}" width="{S}" height="{S}" fill="#fff">'
    if animate:
        rec += '<animate attributeName="opacity" dur="1s" repeatCount="indefinite" calcMode="discrete" keyTimes="0;0.5" values="1;0"/>'
    rec += '</rect>'
    o.append(rec)
    o.append(f'<text x="{5 * S}" y="{3 * S - 2}" font-family="monospace" font-size="14" fill="#bdbdbd">REC</text>')
    o.append('</svg>')
    return "\n".join(o), n


if __name__ == "__main__":
    args = sys.argv[1:]
    only = None
    if "--frame" in args:
        i = args.index("--frame")
        only = int(args[i + 1])
        del args[i:i + 2]
    out = args[0] if args else "bboy.svg"
    svg, n = build(only)
    with open(out, "w") as f:
        f.write(svg)
    print(out, len(svg) // 1024, "KB", n, "frames")
