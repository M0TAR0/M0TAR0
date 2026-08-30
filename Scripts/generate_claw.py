#!/usr/bin/env python3
"""
generate_claw.py

Renders your GitHub contribution grid, then animates a robot claw that
swoops down, grabs your most-active days one at a time, carries them to a
bin, drops them in, and repeats -- forever, looping. Same underlying trick
as before: one self-contained animated SVG, no JavaScript, just SMIL
<animate>/<animateTransform> tags that GitHub's renderer plays automatically.

USAGE:
    python generate_claw.py --username YOURNAME --out claw.svg
    python generate_claw.py --mock --out claw.svg          # test without network
"""

import argparse
import requests
from datetime import datetime, timedelta

CELL = 11
GAP = 3
GREEN_SCALE = ["#161b22", "#3d3d3d", "#6e6e6e", "#a3a3a3", "#e6e6e6"]  # 0..4 activity levels, grayscale
CLAW_COLOR = "#9ca3af"  # grey claw

RAIL_Y = -30          # the claw's "resting height" above the grid
DROP_X_OFFSET = 40    # how far right of the grid the bin sits
PICKS = 6              # how many squares get grabbed per loop
PICK_DURATION = 3.2    # seconds per pick


# ---------------------------------------------------------------------------
# contribution data (same approach as the Life project)
# ---------------------------------------------------------------------------
CONTRIB_API = "https://github-contributions-api.jogruber.de/v4/{username}?y=last"


def fetch_contributions(username):
    resp = requests.get(CONTRIB_API.format(username=username), timeout=20)
    resp.raise_for_status()
    return resp.json()["contributions"]


def mock_contributions():
    import random
    random.seed(7)
    today = datetime.utcnow().date()
    out = []
    for i in range(365, -1, -1):
        d = today - timedelta(days=i)
        count = random.choice([0, 0, 0, 1, 2, 3, 5, 8])
        out.append({"date": d.strftime("%Y-%m-%d"), "count": count})
    return out


def contributions_to_grid(contributions):
    by_date = {c["date"]: c["count"] for c in contributions}
    dates = sorted(by_date.keys())
    start = datetime.strptime(dates[0], "%Y-%m-%d")
    start -= timedelta(days=(start.weekday() + 1) % 7)
    end = datetime.strptime(dates[-1], "%Y-%m-%d")

    weeks, week, cur = [], [], start
    while cur <= end:
        week.append(cur)
        if len(week) == 7:
            weeks.append(week)
            week = []
        cur += timedelta(days=1)
    if week:
        weeks.append(week + [None] * (7 - len(week)))

    grid = [[0] * len(weeks) for _ in range(7)]
    for col, wk in enumerate(weeks):
        for row, day in enumerate(wk):
            if day:
                grid[row][col] = by_date.get(day.strftime("%Y-%m-%d"), 0)
    return grid


def level_of(count):
    if count == 0:
        return 0
    if count <= 2:
        return 1
    if count <= 4:
        return 2
    if count <= 7:
        return 3
    return 4


# ---------------------------------------------------------------------------
# pick the juiciest targets: highest-activity days, spread across the grid
# ---------------------------------------------------------------------------
def choose_targets(grid, k):
    cells = []
    for r, row in enumerate(grid):
        for c, count in enumerate(row):
            cells.append((count, r, c))
    cells.sort(reverse=True)  # highest counts first
    top = cells[: k * 3]  # widen the pool a bit
    # spread them out left-to-right instead of clumping
    top.sort(key=lambda x: x[2])
    step = max(1, len(top) // k)
    chosen = top[::step][:k]
    chosen.sort(key=lambda x: x[2])
    return chosen  # list of (count, row, col)


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------
def render(grid, targets, out_path):
    rows = len(grid)
    cols = len(grid[0])
    grid_w = cols * (CELL + GAP) + GAP
    grid_h = rows * (CELL + GAP) + GAP

    bin_x = grid_w + DROP_X_OFFSET
    bin_y = grid_h / 2

    total_dur = PICKS * PICK_DURATION
    n = len(targets)

    def cell_xy(row, col):
        x = GAP + col * (CELL + GAP) + CELL / 2
        y = GAP + row * (CELL + GAP) + CELL / 2
        return x, y

    # ---- build the claw's global path across all picks ----
    claw_times, claw_pts = [], []
    pincer_times, pincer_vals = [], []
    square_anims = []  # (row, col, times, dxdy_list, opacity_list)

    prev_x, prev_y = cell_xy(*[t[1:] for t in targets][0]) if targets else (0, 0)
    prev_x, prev_y = bin_x, bin_y  # start parked at the bin

    for i, (count, row, col) in enumerate(targets):
        base = i / n
        tx, ty = cell_xy(row, col)
        seg = 1 / n

        def gt(frac):  # local fraction -> global time
            return base + frac * seg

        # claw waypoints for this pick
        wp = [
            (gt(0.00), prev_x, prev_y),          # start where it left off
            (gt(0.18), tx, RAIL_Y),               # travel above target
            (gt(0.32), tx, ty),                   # descend onto target
            (gt(0.42), tx, ty),                   # pause (about to grab)
            (gt(0.50), tx, RAIL_Y),               # lift back up (grabbed)
            (gt(0.68), bin_x, RAIL_Y),            # travel to bin
            (gt(0.80), bin_x, bin_y),             # descend into bin
            (gt(0.88), bin_x, bin_y),             # release
            (gt(1.00), bin_x, bin_y),             # settle, ready for next pick
        ]
        for t, x, y in wp:
            claw_times.append(round(t, 5))
            claw_pts.append(f"{x:.1f},{y:.1f}")

        # pincers: open .. closed (grab) .. open (release) .. closed(idle)
        pw = [
            (gt(0.00), 18),
            (gt(0.30), 18),
            (gt(0.42), 2),     # closed = grabbed
            (gt(0.78), 2),
            (gt(0.88), 18),    # open = release
            (gt(1.00), 18),
        ]
        for t, a in pw:
            pincer_times.append(round(t, 5))
            pincer_vals.append(str(a))

        # the grabbed square: rides along with the claw from grab to release,
        # then fades out (removed) for the rest of the loop
        dx_start = tx - tx  # 0
        sw = [
            (gt(0.00), 0, 0, 1),
            (gt(0.42), 0, 0, 1),                        # still sitting in grid
            (gt(0.50), 0, RAIL_Y - ty, 1),               # lifted with claw
            (gt(0.68), bin_x - tx, RAIL_Y - ty, 1),      # carried to bin
            (gt(0.80), bin_x - tx, bin_y - ty, 1),       # lowered into bin
            (gt(0.88), bin_x - tx, bin_y - ty, 0),       # released -> faded out
            (1.0, bin_x - tx, bin_y - ty, 0),
        ]
        square_anims.append((row, col, sw))

        prev_x, prev_y = bin_x, bin_y

    # close the loop: last point must also exist at t=1 exactly once
    if claw_times[-1] < 1.0:
        claw_times.append(1.0)
        claw_pts.append(claw_pts[-1])
    if pincer_times[-1] < 1.0:
        pincer_times.append(1.0)
        pincer_vals.append(pincer_vals[-1])

    # ---- assemble SVG ----
    W = bin_x + 40
    H = max(grid_h, RAIL_Y * -1 + 40) + 20
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-10} {RAIL_Y - 40} {W} {H}" '
        f'width="{int(W)}" height="{int(H)}">',
        f'<rect x="{-10}" y="{RAIL_Y - 40}" width="{W}" height="{H}" fill="#0d1117"/>',
    ]

    # grid squares
    square_lookup = {(r, c): anim for (r, c, anim) in square_anims}
    for r in range(rows):
        for c in range(cols):
            x, y = cell_xy(r, c)
            color = GREEN_SCALE[level_of(grid[r][c])]
            gx, gy = x - CELL / 2, y - CELL / 2
            if (r, c) in square_lookup:
                sw = square_lookup[(r, c)]
                times = ";".join(str(t) for t, *_ in sw)
                dxs = ";".join(f"{dx:.1f}" for _, dx, dy, op in sw)
                dys = ";".join(f"{dy:.1f}" for _, dx, dy, op in sw)
                ops = ";".join(str(op) for *_, op in sw)
                pair_values = ";".join(f"{a},{b}" for a, b in zip(dxs.split(";"), dys.split(";")))
                parts.append(
                    f'<g>'
                    f'<animateTransform attributeName="transform" type="translate" '
                    f'values="{pair_values}" '
                    f'keyTimes="{times}" dur="{total_dur}s" repeatCount="indefinite" calcMode="linear"/>'
                    f'<rect x="{gx:.1f}" y="{gy:.1f}" width="{CELL}" height="{CELL}" rx="2" fill="{color}">'
                    f'<animate attributeName="opacity" values="{ops}" keyTimes="{times}" '
                    f'dur="{total_dur}s" repeatCount="indefinite" calcMode="linear"/>'
                    f'</rect></g>'
                )
            else:
                parts.append(f'<rect x="{gx:.1f}" y="{gy:.1f}" width="{CELL}" height="{CELL}" rx="2" fill="{color}"/>')

    # bin graphic
    parts.append(
        f'<g stroke="#7d8590" stroke-width="2" fill="none">'
        f'<path d="M {bin_x-14} {bin_y} L {bin_x-11} {bin_y+16} L {bin_x+11} {bin_y+16} L {bin_x+14} {bin_y} Z"/>'
        f'<line x1="{bin_x-16}" y1="{bin_y-3}" x2="{bin_x+16}" y2="{bin_y-3}"/>'
        f'</g>'
    )

    # claw group: rail line (decorative) + moving assembly
    claw_values = " ".join(claw_pts)
    claw_keytimes = ";".join(str(t) for t in claw_times)
    pincer_values = ";".join(pincer_vals)
    pincer_keytimes = ";".join(str(t) for t in pincer_times)

    parts.append(f'<line x1="0" y1="{RAIL_Y-10}" x2="{grid_w}" y2="{RAIL_Y-10}" stroke="#30363d" stroke-width="2" stroke-dasharray="4 3"/>')

    pincer_values_neg = ";".join(str(-int(v)) for v in pincer_vals)

    parts.append(
        f'<g id="claw">'
        f'<animateTransform attributeName="transform" type="translate" '
        f'values="{claw_values}" keyTimes="{claw_keytimes}" dur="{total_dur}s" '
        f'calcMode="linear" repeatCount="indefinite"/>'
        f'<line x1="0" y1="{RAIL_Y-10}" x2="0" y2="0" stroke="#7d8590" stroke-width="2"/>'
        f'<g id="pincer-left">'
        f'<animateTransform attributeName="transform" type="rotate" '
        f'values="{pincer_values_neg}" keyTimes="{pincer_keytimes}" '
        f'dur="{total_dur}s" calcMode="linear" repeatCount="indefinite"/>'
        f'<path d="M 0 0 L -10 14 L -4 14 Z" fill="#c9ccd1"/>'
        f'</g>'
        f'<g id="pincer-right">'
        f'<animateTransform attributeName="transform" type="rotate" '
        f'values="{pincer_values}" keyTimes="{pincer_keytimes}" '
        f'dur="{total_dur}s" calcMode="linear" repeatCount="indefinite"/>'
        f'<path d="M 0 0 L 10 14 L 4 14 Z" fill="#c9ccd1"/>'
        f'</g>'
        f'<circle cx="0" cy="0" r="3" fill="#c9ccd1"/>'
        f'</g>'
    )

    parts.append("</svg>")
    with open(out_path, "w") as f:
        f.write("\n".join(parts))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--username", default=None)
    ap.add_argument("--out", default="claw.svg")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--picks", type=int, default=PICKS)
    args = ap.parse_args()

    contributions = mock_contributions() if args.mock else fetch_contributions(args.username)
    grid = contributions_to_grid(contributions)
    targets = choose_targets(grid, args.picks)
    render(grid, targets, args.out)
    print(f"Wrote {args.out} -- {len(targets)} squares will be grabbed per loop")


if __name__ == "__main__":
    main()
