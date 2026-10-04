#!/usr/bin/env python3
"""Generates the black & white theme text images: section headings and the typing intro.

Each image comes in a -dark (light text) and a -light (dark text) variant, used through <picture>.
"""
import os

THEMES = {"dark": "#f2f2f2", "light": "#141414"}
FONT = "'Courier New', Courier, monospace"
os.makedirs("assets/headings", exist_ok=True)

HEADINGS = {
    "who": "I'M ROMEL:",
    "skills": "LANGUAGES & SKILLS",
    "certs": "CERTIFICATIONS",
    "contrib": "CONTRIBUTIONS",
    "contact": "CONTACT ME",
}

for key, text in HEADINGS.items():
    label = text.replace("&", "&amp;")
    n = len(text)
    cw, size = 20, 30
    w = n * cw + 20
    for theme, fg in THEMES.items():
        open(f"assets/headings/{key}-{theme}.svg", "w").write(
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} 52" width="{w}" height="52">'
            f'<title>{text.replace("&", "&amp;")}</title>'
            f'<text x="10" y="35" font-family="{FONT}" font-size="{size}" font-weight="bold" fill="{fg}" '
            f'textLength="{n * cw}" lengthAdjust="spacing">{label}</text></svg>')

# typing intro: types once, stays, cursor blinks 3 times then disappears
text = "Hey there, Welcome :)"
n, cw, W, H = len(text), 22, 560, 64
x0 = (W - n * cw) // 2
start, per = 0.6, 0.09
dur = n * per
end = start + dur
kt = ";".join(f"{i / (n + 1):.4f}" for i in range(n + 1))
widths = "0;" + ";".join(str(i * cw) for i in range(1, n + 1))
xs = f"{x0};" + ";".join(str(x0 + i * cw) for i in range(1, n + 1))
for theme, fg in THEMES.items():
    open(f"assets/typing-{theme}.svg", "w").write(f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<title>{text}</title>
<defs><clipPath id="c"><rect x="{x0}" y="0" width="0" height="{H}">
<animate attributeName="width" begin="{start}s" dur="{dur:.2f}s" fill="freeze" calcMode="discrete" keyTimes="{kt}" values="{widths}"/>
</rect></clipPath></defs>
<text x="{x0}" y="43" font-family="{FONT}" font-size="36" font-weight="bold" fill="{fg}" textLength="{n * cw}" lengthAdjust="spacing" clip-path="url(#c)">{text}</text>
<rect x="{x0}" y="10" width="3" height="40" fill="{fg}" opacity="0">
<set attributeName="opacity" to="1" begin="{start}s"/>
<animate attributeName="x" begin="{start}s" dur="{dur:.2f}s" fill="freeze" calcMode="discrete" keyTimes="{kt}" values="{xs}"/>
<animate attributeName="opacity" begin="{end:.2f}s" dur="0.8s" repeatCount="3" calcMode="discrete" keyTimes="0;0.5" values="1;0"/>
<set attributeName="opacity" to="0" begin="{end + 2.4:.2f}s"/>
</rect>
</svg>
''')
