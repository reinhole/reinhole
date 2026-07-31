#!/usr/bin/env python3
"""Draw the hero: ASCII portrait, wordmark, and the four proof points.

One image rather than three stacked blocks. Previously the portrait was its own
471px band with a 152px wordmark under it -- 623px of scroll before the page
stated a single fact. Side by side the same content costs ~330px and reads as a
composition instead of a pile.

The site's identity is screen-dominating typography on pitch black, which
markdown cannot do: GitHub sets README text in its own sans and strips every
attempt to change it. So the wordmark has to be an image.

    .venv/bin/python scripts/make_hero.py
"""
import pathlib

import make_portrait as p
import svgkit as k

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "hero.svg"

NAME = "OLE REINHOLD"
SUB = "DATA · MARKETS · MACHINES"
KICKER = ["UNIVERSITY OF STUTTGART", "B.SC. ARTIFICIAL INTELLIGENCE AND DATA SCIENCE"]
PROOF = [
    "LLM-gated trading",
    "Full-stack university platform",
    "Registered SEO tools business",
    "Grant-funded ornithopter",
]

W = 880
PORTRAIT_COLS = 58
PORTRAIT_FS = 8.75      # -> ~5.2px per column, at the legibility floor
COL_X = 356             # where the text column starts
NAME_SIZE = 52

STYLES = (
    k.face(600)
    + k.face(400)
    + f".px{{font-family:'Fira400',ui-monospace,monospace;font-size:{PORTRAIT_FS}px;"
    f"letter-spacing:{p.TRACKING * PORTRAIT_FS:.3f}px;fill:{k.INK};white-space:pre}}"
    + f".n{{font-family:'Fira600',ui-monospace,monospace;font-size:{NAME_SIZE}px;"
    f"fill:{k.INK};letter-spacing:.02em}}"
    + f".s{{font-family:'Fira600',ui-monospace,monospace;font-size:12.5px;"
    f"fill:{k.INK};letter-spacing:.22em}}"
    + f".c{{font-family:'Fira400',ui-monospace,monospace;font-size:10px;"
    f"fill:{k.FAINT};letter-spacing:.12em}}"
    + f".p{{font-family:'Fira400',ui-monospace,monospace;font-size:11.5px;fill:{k.DIM}}}"
    + f".a{{font-family:'Fira400',ui-monospace,monospace;font-size:11.5px;fill:{k.INK}}}"
)


def main() -> None:
    rows = p.to_rows(PORTRAIT_COLS)
    frag, pw, ph = p.typing_fragment(rows, ox=0, oy=14, font_size=PORTRAIT_FS, ink=k.INK)

    h = max(ph + 28, 322)
    parts = k.open_svg(W, h, f"{NAME} — {SUB}. {'; '.join(PROOF)}", STYLES)
    parts += frag

    # A single vertical hairline separates portrait from type, the way the
    # site's menu overlay divides its columns.
    x_rule = COL_X - 30
    parts.append(
        f'<line x1="{x_rule}" y1="14" x2="{x_rule}" y2="{h - 14:g}" '
        f'stroke="{k.RULE}" stroke-width="1"/>'
    )

    parts.append(k.text(COL_X, 74, NAME, "n"))
    parts.append(k.rule(COL_X, 96, W))
    parts.append(k.text(COL_X + 2, 122, SUB, "s"))
    for i, line in enumerate(KICKER):
        parts.append(k.text(COL_X + 2, 148 + i * 16, line, "c"))
    parts.append(k.rule(COL_X, 196, W))
    for i, line in enumerate(PROOF):
        y = 220 + i * 22
        parts.append(k.text(COL_X + 2, y, "→", "a"))
        parts.append(k.text(COL_X + 22, y, line, "p"))

    k.write(OUT, parts)
    print(f"  portrait {PORTRAIT_COLS}x{len(rows)} at {pw:.0f}x{ph:.0f}px")


if __name__ == "__main__":
    main()
