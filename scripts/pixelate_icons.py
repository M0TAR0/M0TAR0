#!/usr/bin/env python3
"""Turns the downloaded skill icons into pixel art (assets/skills/<name>-<theme>.svg, in place).

Run fetch_skill_icons.py first, then this. Needs rsvg-convert and Pillow.
"""
import io
import subprocess
from PIL import Image

NAMES = ["python", "java", "c", "cpp", "html", "arduino", "github", "linux", "fedora"]
GRID = 24      # art pixels per side
SCALE = 3      # screen px per art pixel
COLORS = 10    # palette size per icon


def pixelate(path):
    png = subprocess.run(["rsvg-convert", "-w", "384", "-h", "384", path], capture_output=True, check=True).stdout
    img = Image.open(io.BytesIO(png)).convert("RGBA")
    small = img.resize((GRID, GRID), Image.BOX)
    alpha = small.getchannel("A").point(lambda a: 255 if a >= 128 else 0)
    # flatten onto the tile's own corner colour so transparent edges don't bleed into the palette
    rgb = Image.new("RGB", small.size, small.getpixel((GRID // 2, 1))[:3])
    rgb.paste(small.convert("RGB"), mask=small.getchannel("A"))
    q = rgb.quantize(COLORS, method=Image.MEDIANCUT, dither=Image.NONE).convert("RGB")
    rects = []
    for y in range(GRID):
        x = 0
        while x < GRID:
            if alpha.getpixel((x, y)) == 0:
                x += 1
                continue
            c = q.getpixel((x, y))
            x2 = x
            while x2 + 1 < GRID and alpha.getpixel((x2 + 1, y)) and q.getpixel((x2 + 1, y)) == c:
                x2 += 1
            rects.append(f'<rect x="{x}" y="{y}" width="{x2 - x + 1}" height="1" fill="#{c[0]:02x}{c[1]:02x}{c[2]:02x}"/>')
            x = x2 + 1
    size = GRID * SCALE
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {GRID} {GRID}" width="{size}" height="{size}" '
            f'shape-rendering="crispEdges">' + "".join(rects) + "</svg>")


for n in NAMES:
    for t in ("dark", "light"):
        p = f"assets/skills/{n}-{t}.svg"
        svg = pixelate(p)
        open(p, "w").write(svg)
        print(p)
