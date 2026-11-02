"""Erzeugt den animierten Terminal-Kopf des Profil-READMEs (hell und dunkel).

Jede Zeile wird per Clip-Rechteck zeichenweise aufgedeckt (CSS steps()),
am Ende blinkt ein Cursor. Bei prefers-reduced-motion steht alles sofort da.
Aufruf: python scripts/terminal_header.py  -> assets/header-dark.svg, assets/header-light.svg
"""
from pathlib import Path
from xml.sax.saxutils import escape

LINES = [
    ("~ $", "whoami"),
    (None, "murat · sap developer by day, app & ai tinkerer by night"),
    ("~ $", "ls ~/coming-soon"),
    (None, "akari/  salihiit/  jgl-diff/"),
]
THEMES = {
    "dark": {"bg": "#0d1117", "rule": "#30363d", "fg": "#e6edf3", "dim": "#9198a1", "acc": "#3fb950"},
    "light": {"bg": "#f6f8fa", "rule": "#d1d9e0", "fg": "#1f2328", "dim": "#59636e", "acc": "#1a7f37"},
}
W, PAD, TOP, STEP, SIZE = 840, 28, 42, 32, 15
CHAR = SIZE * 0.62  # Monospace-Breite mit Reserve fuer Ersatzschriften
FONT = "ui-monospace, 'JetBrains Mono', SFMono-Regular, Menlo, Consolas, monospace"
PER_CHAR, PAUSE = 0.045, 0.45


def build(t):
    h = TOP + STEP * len(LINES) + 34
    css, clips, texts = [], [], []
    start = 0.3
    for i, (prompt, text) in enumerate(LINES):
        full = (prompt + " " if prompt else "") + text
        n = len(full)
        dur = n * PER_CHAR
        y = TOP + i * STEP
        clips.append(f'<clipPath id="c{i}"><rect class="r{i}" x="{PAD}" y="{y - SIZE}" width="{n * CHAR + 4:.0f}" height="{SIZE + 8}"/></clipPath>')
        css.append(f".r{i}{{animation:tip {dur:.2f}s steps({n},end) {start:.2f}s both}}")
        body = (f'<tspan fill="{t["acc"]}">{escape(prompt)}</tspan> <tspan fill="{t["fg"]}">{escape(text)}</tspan>'
                if prompt else f'<tspan fill="{t["dim"]}">{escape(text)}</tspan>')
        texts.append(f'<text x="{PAD}" y="{y}" clip-path="url(#c{i})" xml:space="preserve">{body}</text>')
        start += dur + PAUSE
    y = TOP + len(LINES) * STEP
    css.append(f".last{{animation:show 0s {start:.2f}s both}}.cur{{animation:blink 1s steps(1) {start:.2f}s infinite}}")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img" aria-label="murat: sap developer by day, app and ai tinkerer by night">
<style>
text{{font-family:{FONT};font-size:{SIZE}px}}
.r0,.r1,.r2,.r3{{transform-box:fill-box;transform-origin:left center}}
@keyframes tip{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}
@keyframes show{{from{{opacity:0}}to{{opacity:1}}}}
@keyframes blink{{50%{{opacity:0}}}}
{''.join(css)}
@media (prefers-reduced-motion:reduce){{.r0,.r1,.r2,.r3,.last,.cur{{animation:none}}}}
</style>
<defs>{''.join(clips)}</defs>
<rect x="0.5" y="0.5" width="{W - 1}" height="{h - 1}" rx="6" fill="{t['bg']}" stroke="{t['rule']}"/>
{chr(10).join(texts)}
<g class="last"><text x="{PAD}" y="{y}" fill="{t['acc']}">~ $</text><rect class="cur" x="{PAD + 4 * CHAR:.0f}" y="{y - SIZE + 2}" width="9" height="{SIZE + 2}" fill="{t['acc']}"/></g>
</svg>
"""


if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "assets"
    out.mkdir(exist_ok=True)
    for name, t in THEMES.items():
        (out / f"header-{name}.svg").write_text(build(t), encoding="utf-8", newline="\n")
        print(out / f"header-{name}.svg")
