#!/usr/bin/env python3
"""Downloads Skill Icons (full colour) into assets/skills so <picture> can swap dark/light versions.

Writes assets/skills/<name>-dark.svg and <name>-light.svg
"""
import re
import urllib.request

ICONS = ["python", "java", "c", "cpp", "html", "arduino", "github", "linux"]

# Skill Icons has no Fedora tile, so build one from the Simple Icons logo in the same style
FEDORA_URL = "https://cdn.jsdelivr.net/npm/simple-icons@latest/icons/fedora.svg"
FEDORA_TILE = {"dark": ("#242938", "#51a2da"), "light": ("#f4f2ed", "#3c6eb4")}


for name in ICONS:
    for theme in ("dark", "light"):
        url = f"https://skillicons.dev/icons?i={name}&theme={theme}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        svg = urllib.request.urlopen(req, timeout=30).read().decode()
        open(f"assets/skills/{name}-{theme}.svg", "w").write(svg)
        print(name, theme, len(svg))

req = urllib.request.Request(FEDORA_URL, headers={"User-Agent": "Mozilla/5.0"})
path = re.search(r' d="([^"]+)"', urllib.request.urlopen(req, timeout=30).read().decode()).group(1)
for theme, (tile, fg) in FEDORA_TILE.items():
    open(f"assets/skills/fedora-{theme}.svg", "w").write(
        '<svg width="48" height="48" viewBox="0 0 256 256" fill="none" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="256" height="256" rx="60" fill="{tile}"/>'
        f'<path transform="translate(49 49) scale(6.6)" fill="{fg}" d="{path}"/></svg>')
    print("fedora", theme)
