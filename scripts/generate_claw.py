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
GREEN_SCALE = ["#2b2b2b", "#555555", "#7d7d7d", "#a6a6a6", "#d4d4d4"]  # 0..4 activity levels, neutral grayscale
CLAW_COLOR = "#9a9a9a"
RAIL_COLOR = "#6a6a6a"


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
# Pixel-art claw: every shape is made of U x U blocks. Pincer cells are (col, row) offsets
# from the tip, in blocks. Open and closed poses have the same number of cells so each block
# can animate between them with the shared keyTimes.
U = 4
LEFT_OPEN = [(-1, -1), (-2, 0), (-3, 0), (-4, 1), (-5, 2), (-5, 3), (-5, 4), (-4, 4)]
LEFT_CLOSED = [(-1, -1), (-2, 0), (-2, 1), (-2, 2), (-2, 3), (-2, 4), (-1, 4), (-3, 4)]
RIGHT_OPEN = [(-x, y) for x, y in LEFT_OPEN]
RIGHT_CLOSED = [(-x, y) for x, y in LEFT_CLOSED]
HOUSING = [(-2, -3), (-1, -3), (0, -3), (1, -3), (-1, -2), (0, -2)]   # box above the pincers


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
        f'width="{int(W)}" height="{int(H)}" shape-rendering="crispEdges">',
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
                    f'<rect x="{gx:.1f}" y="{gy:.1f}" width="{CELL}" height="{CELL}" fill="{color}">'
                    f'<animate attributeName="x" values="{xs}" keyTimes="{times}" '
                    f'dur="{total_dur}s" repeatCount="indefinite" calcMode="linear"/>'
                    f'<animate attributeName="y" values="{ys}" keyTimes="{times}" '
                    f'dur="{total_dur}s" repeatCount="indefinite" calcMode="linear"/>'
                    f'<animate attributeName="opacity" values="{ops}" keyTimes="{times}" '
                    f'dur="{total_dur}s" repeatCount="indefinite" calcMode="linear"/>'
                    f'</rect>'
                )
            else:
                parts.append(f'<rect x="{gx:.1f}" y="{gy:.1f}" width="{CELL}" height="{CELL}" fill="{color}"/>')

    def block(x, y, extra=""):
        return f'<rect x="{x:.1f}" y="{y:.1f}" width="{U}" height="{U}" fill="{CLAW_COLOR}"{extra}/>'

    # bin (static): wide rim, two walls and a base, built from blocks
    bx, by = round(bin_x / U) * U, round(bin_y / U) * U
    for i in range(-5, 6):
        parts.append(block(bx + i * U, by - U))                    # rim
    for j in range(0, 4):
        parts.append(block(bx - 4 * U, by + j * U))                # walls
        parts.append(block(bx + 4 * U, by + j * U))
    for i in range(-4, 5):
        parts.append(block(bx + i * U, by + 4 * U))                # base

    # rail: dashed pixel line
    ry = RAIL_Y - 10
    for x in range(0, int(grid_w), 4 * U):
        parts.append(f'<rect x="{x}" y="{ry}" width="{2 * U}" height="{U}" fill="{RAIL_COLOR}"/>')

    # ---- claw: cable, housing and two pincers, every block animated with the shared keyTimes ----
    times = ";".join(str(t) for t, *_ in all_waypoints)
    dur = f'dur="{total_dur}s" repeatCount="indefinite" calcMode="linear"'
    start_x, start_y = all_waypoints[0][1], all_waypoints[0][2]

    def anim(attr, values):
        return f'<animate attributeName="{attr}" values="{";".join(values)}" keyTimes="{times}" {dur}/>'

    def moving_block(cells_for, ox, oy):
        """One animated block. cells_for(closed) -> (col, row) offset for this block in that pose."""
        xs = [f"{x + cells_for(c)[0] * U + ox:.1f}" for _, x, y, c in all_waypoints]
        ys = [f"{y + cells_for(c)[1] * U + oy:.1f}" for _, x, y, c in all_waypoints]
        return (f'<rect x="{xs[0]}" y="{ys[0]}" width="{U}" height="{U}" fill="{CLAW_COLOR}">'
                f'{anim("x", xs)}{anim("y", ys)}</rect>')

    # cable: a thin pixel column from the rail down to the housing
    cx = [f"{x - U / 2:.1f}" for _, x, y, c in all_waypoints]
    cy = [f"{y - 3 * U:.1f}" for _, x, y, c in all_waypoints]
    ch = [f"{max(y - 3 * U - ry, 0):.1f}" for _, x, y, c in all_waypoints]
    parts.append(
        f'<rect x="{cx[0]}" y="{ry}" width="{U}" height="{ch[0]}" fill="{CLAW_COLOR}">'
        f'{anim("x", cx)}{anim("height", ch)}</rect>'
    )
    for dx, dy in HOUSING:
        parts.append(moving_block(lambda c, dx=dx, dy=dy: (dx, dy), -U / 2, 0))
    for op, cl in zip(LEFT_OPEN + RIGHT_OPEN, LEFT_CLOSED + RIGHT_CLOSED):
        parts.append(moving_block(lambda c, op=op, cl=cl: cl if c else op, -U / 2, 0))

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
