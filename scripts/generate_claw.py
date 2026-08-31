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
CLAW_COLOR = "#9ca3af"
RAIL_COLOR = "#30363d"

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
# pick targets
# ---------------------------------------------------------------------------
def choose_targets(grid, k):
    """Pick k targets, spread left-to-right (used only if --limit is passed)."""
    cells = []
    for r, row in enumerate(grid):
        for c, count in enumerate(row):
            cells.append((count, r, c))
    cells.sort(reverse=True)  # highest counts first
    top = cells[: k * 3]  # widen the pool a bit
    top.sort(key=lambda x: x[2])
    step = max(1, len(top) // k)
    chosen = top[::step][:k]
    chosen.sort(key=lambda x: x[2])
    return chosen


def choose_all_targets(grid):
    """Every day with at least 1 contribution, ordered from MOST to LEAST active.
    Ties keep their original left-to-right/top-to-bottom grid order."""
    cells = []
    for r, row in enumerate(grid):
        for c, count in enumerate(row):
            if count > 0:
                cells.append((count, r, c))
    cells.sort(key=lambda x: -x[0])  # stable sort: descending count, ties keep grid order
    return cells


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------
# Local pincer shapes (relative to the claw's tip point at 0,0), for open vs closed.
# Each is a small hook/clamp silhouette (4 points) rather than a thin triangle,
# so it reads as "gripping" the square rather than a stick figure standing on it.
LEFT_OPEN = [(-2, -2), (-15, 3), (-15, 13), (-7, 15)]
LEFT_CLOSED = [(-2, -2), (-7, 2), (-7, 11), (-3, 12)]
RIGHT_OPEN = [(2, -2), (15, 3), (15, 13), (7, 15)]
RIGHT_CLOSED = [(2, -2), (7, 2), (7, 11), (3, 12)]


def render(grid, targets, out_path):
    rows = len(grid)
    cols = len(grid[0])
    grid_w = cols * (CELL + GAP) + GAP
    grid_h = rows * (CELL + GAP) + GAP

    bin_x = grid_w + DROP_X_OFFSET
    bin_y = grid_h / 2

    total_dur = max(len(targets), 1) * PICK_DURATION
    n = len(targets)

    def cell_xy(row, col):
        x = GAP + col * (CELL + GAP) + CELL / 2
        y = GAP + row * (CELL + GAP) + CELL / 2
        return x, y

    # ---- build ONE unified waypoint list per pick: (time, x, y, is_closed) ----
    # Using the same waypoints for claw position AND pincer state means every
    # animated attribute (cable, tip, pincers, carried square) shares identical
    # keyTimes -- simpler, and avoids any mismatched-length animation values.
    all_waypoints = []  # list of (time, x, y, is_closed)
    square_anims = []   # (row, col, list of (time, x, y, opacity))

    prev_x, prev_y = bin_x, bin_y  # start parked at the bin

    for i, (count, row, col) in enumerate(targets):
        base = i / n
        seg = 1 / n
        tx, ty = cell_xy(row, col)

        def gt(frac):
            return round(base + frac * seg, 5)

        wp = [
            (gt(0.00), prev_x, prev_y, False),   # continue from wherever it was
            (gt(0.18), tx, RAIL_Y, False),         # travel above target, open
            (gt(0.32), tx, ty, False),             # descend onto target, open
            (gt(0.42), tx, ty, True),              # CLOSE -- grab it
            (gt(0.50), tx, RAIL_Y, True),          # lift back up, still closed
            (gt(0.68), bin_x, RAIL_Y, True),       # travel to bin, still closed
            (gt(0.80), bin_x, bin_y, True),        # descend into bin, still closed
            (gt(0.88), bin_x, bin_y, False),       # OPEN -- release
            (gt(1.00), bin_x, bin_y, False),       # settle, ready for next pick
        ]
        all_waypoints.extend(wp)

        # the grabbed square: sits still until grabbed (idx 0-2), then exactly
        # tracks the claw's x/y while closed (idx 3-6), then disappears (idx 7+).
        # IMPORTANT: this list must start at global time 0.0 exactly (not wp[0][0],
        # which is i/6 for pick i) -- SVG requires every animation's keyTimes to
        # start at 0, otherwise the whole animation is silently invalid and ignored.
        sq = [
            (0.0, tx, ty, 1),
            (wp[2][0], tx, ty, 1),                  # still resting, right up to grab
            (wp[3][0], wp[3][1], wp[3][2], 1),      # jumps to claw position -- grabbed
            (wp[4][0], wp[4][1], wp[4][2], 1),
            (wp[5][0], wp[5][1], wp[5][2], 1),
            (wp[6][0], wp[6][1], wp[6][2], 1),
            (wp[7][0], wp[7][1], wp[7][2], 0),      # released -> faded out
            (1.0, wp[7][1], wp[7][2], 0),
        ]
        square_anims.append((row, col, sq))
        prev_x, prev_y = bin_x, bin_y

    if all_waypoints[-1][0] < 1.0:
        t, x, y, closed = all_waypoints[-1]
        all_waypoints.append((1.0, x, y, closed))

    # ---- assemble SVG ----
    W = bin_x + 40
    content_bottom = max(grid_h, bin_y + 16) + 15   # tallest thing: grid rows or the bin
    content_top = RAIL_Y - 40                          # rail + claw dock, above the grid
    H = content_bottom - content_top

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-10 {content_top} {W} {H}" '
        f'width="{int(W)}" height="{int(H)}">',
    ]

    # grid squares (targets get their own animated x/y/opacity, no transform needed)
    square_lookup = {(r, c): anim for (r, c, anim) in square_anims}
    for r in range(rows):
        for c in range(cols):
            x, y = cell_xy(r, c)
            color = GREEN_SCALE[level_of(grid[r][c])]
            gx, gy = x - CELL / 2, y - CELL / 2
            if (r, c) in square_lookup:
                sq = square_lookup[(r, c)]
                times = ";".join(str(t) for t, *_ in sq)
                xs = ";".join(f"{(px - CELL/2):.1f}" for _, px, py, op in sq)
                ys = ";".join(f"{(py - CELL/2):.1f}" for _, px, py, op in sq)
                ops = ";".join(str(op) for *_, op in sq)
                parts.append(
                    f'<rect x="{gx:.1f}" y="{gy:.1f}" width="{CELL}" height="{CELL}" rx="2" fill="{color}">'
                    f'<animate attributeName="x" values="{xs}" keyTimes="{times}" '
                    f'dur="{total_dur}s" repeatCount="indefinite" calcMode="linear"/>'
                    f'<animate attributeName="y" values="{ys}" keyTimes="{times}" '
                    f'dur="{total_dur}s" repeatCount="indefinite" calcMode="linear"/>'
                    f'<animate attributeName="opacity" values="{ops}" keyTimes="{times}" '
                    f'dur="{total_dur}s" repeatCount="indefinite" calcMode="linear"/>'
                    f'</rect>'
                )
            else:
                parts.append(f'<rect x="{gx:.1f}" y="{gy:.1f}" width="{CELL}" height="{CELL}" rx="2" fill="{color}"/>')

    # bin graphic (static)
    parts.append(
        f'<g stroke="{CLAW_COLOR}" stroke-width="2" fill="none">'
        f'<path d="M {bin_x-14} {bin_y} L {bin_x-11} {bin_y+16} L {bin_x+11} {bin_y+16} L {bin_x+14} {bin_y} Z"/>'
        f'<line x1="{bin_x-16}" y1="{bin_y-3}" x2="{bin_x+16}" y2="{bin_y-3}"/>'
        f'</g>'
    )

    parts.append(f'<line x1="0" y1="{RAIL_Y-10}" x2="{grid_w}" y2="{RAIL_Y-10}" '
                 f'stroke="{RAIL_COLOR}" stroke-width="2" stroke-dasharray="4 3"/>')

    # ---- claw: cable, tip circle, two pincer polygons -- all direct-attribute animated ----
    times = ";".join(str(t) for t, *_ in all_waypoints)
    xs = ";".join(f"{x:.1f}" for _, x, y, c in all_waypoints)
    ys = ";".join(f"{y:.1f}" for _, x, y, c in all_waypoints)

    def poly_values(local_open, local_closed):
        frames = []
        for t, x, y, closed in all_waypoints:
            pts = local_closed if closed else local_open
            frames.append(" ".join(f"{x+lx:.1f},{y+ly:.1f}" for lx, ly in pts))
        return ";".join(frames)

    left_points = poly_values(LEFT_OPEN, LEFT_CLOSED)
    right_points = poly_values(RIGHT_OPEN, RIGHT_CLOSED)
    start_x, start_y = all_waypoints[0][1], all_waypoints[0][2]
    start_left = " ".join(f"{start_x+lx:.1f},{start_y+ly:.1f}" for lx, ly in LEFT_OPEN)
    start_right = " ".join(f"{start_x+lx:.1f},{start_y+ly:.1f}" for lx, ly in RIGHT_OPEN)

    # cable: vertical line from the fixed rail down to the claw's current position
    parts.append(
        f'<line x1="{start_x:.1f}" x2="{start_x:.1f}" y1="{RAIL_Y-10}" y2="{start_y:.1f}" '
        f'stroke="{CLAW_COLOR}" stroke-width="2">'
        f'<animate attributeName="x1" values="{xs}" keyTimes="{times}" dur="{total_dur}s" '
        f'repeatCount="indefinite" calcMode="linear"/>'
        f'<animate attributeName="x2" values="{xs}" keyTimes="{times}" dur="{total_dur}s" '
        f'repeatCount="indefinite" calcMode="linear"/>'
        f'<animate attributeName="y2" values="{ys}" keyTimes="{times}" dur="{total_dur}s" '
        f'repeatCount="indefinite" calcMode="linear"/>'
        f'</line>'
    )
    # pincers
    parts.append(
        f'<polygon points="{start_left}" fill="{CLAW_COLOR}">'
        f'<animate attributeName="points" values="{left_points}" keyTimes="{times}" '
        f'dur="{total_dur}s" repeatCount="indefinite" calcMode="linear"/>'
        f'</polygon>'
        f'<polygon points="{start_right}" fill="{CLAW_COLOR}">'
        f'<animate attributeName="points" values="{right_points}" keyTimes="{times}" '
        f'dur="{total_dur}s" repeatCount="indefinite" calcMode="linear"/>'
        f'</polygon>'
    )
    # tip
    parts.append(
        f'<circle cx="{start_x:.1f}" cy="{start_y:.1f}" r="3" fill="{CLAW_COLOR}">'
        f'<animate attributeName="cx" values="{xs}" keyTimes="{times}" dur="{total_dur}s" '
        f'repeatCount="indefinite" calcMode="linear"/>'
        f'<animate attributeName="cy" values="{ys}" keyTimes="{times}" dur="{total_dur}s" '
        f'repeatCount="indefinite" calcMode="linear"/>'
        f'</circle>'
    )
    # small housing bracket above the pincers, for a more "mechanical claw" read
    parts.append(
        f'<rect x="{start_x-6:.1f}" y="{start_y-6:.1f}" width="12" height="5" rx="1.5" fill="{CLAW_COLOR}">'
        f'<animate attributeName="x" values="{";".join(f"{x-6:.1f}" for x in [float(v) for v in xs.split(";")])}" '
        f'keyTimes="{times}" dur="{total_dur}s" repeatCount="indefinite" calcMode="linear"/>'
        f'<animate attributeName="y" values="{";".join(f"{y-6:.1f}" for y in [float(v) for v in ys.split(";")])}" '
        f'keyTimes="{times}" dur="{total_dur}s" repeatCount="indefinite" calcMode="linear"/>'
        f'</rect>'
    )

    parts.append("</svg>")
    with open(out_path, "w") as f:
        f.write("\n".join(parts))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--username", default=None)
    ap.add_argument("--out", default="claw.svg")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--limit", type=int, default=0,
                     help="grab only this many top days (spread out) instead of ALL contributions")
    ap.add_argument("--pick-duration", type=float, default=1.1,
                     help="seconds per pick -- lower this if you have a lot of contributions")
    args = ap.parse_args()

    global PICK_DURATION
    PICK_DURATION = args.pick_duration

    contributions = mock_contributions() if args.mock else fetch_contributions(args.username)
    grid = contributions_to_grid(contributions)

    if args.limit:
        targets = choose_targets(grid, args.limit)
    else:
        targets = choose_all_targets(grid)  # ALL contributions, most to least

    if not targets:
        print("No contributions found -- nothing to animate.")
        targets = []

    render(grid, targets, args.out)
    total_seconds = len(targets) * PICK_DURATION
    print(f"Wrote {args.out} -- grabbing {len(targets)} days, "
          f"most to least active ({total_seconds:.0f}s per full loop)")


if __name__ == "__main__":
    main()
