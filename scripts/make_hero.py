#!/usr/bin/env python3
"""Draw the hero wordmark.

The site's identity is screen-dominating typography on pitch black. Markdown
cannot do that -- GitHub sets README text in its own sans and strips any
attempt to change it -- so the wordmark has to be an image.

    .venv/bin/python scripts/make_hero.py
"""
import pathlib

import svgkit as k

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "hero.svg"

NAME = "OLE REINHOLD"
SUB = "DATA · MARKETS · MACHINES"
KICKER = "UNIVERSITY OF STUTTGART · B.SC. ARTIFICIAL INTELLIGENCE AND DATA SCIENCE"

W, H = 880, 152
NAME_SIZE = 72
NAME_TRACK = 0.02
SUB_SIZE = 14
KICKER_SIZE = 10.5

STYLES = (
    k.face(600)
    + k.face(400)
    + f".n{{font-family:'Fira600',ui-monospace,monospace;font-size:{NAME_SIZE}px;"
    f"fill:{k.INK};letter-spacing:{NAME_TRACK}em}}"
    + f".s{{font-family:'Fira600',ui-monospace,monospace;font-size:{SUB_SIZE}px;"
    f"fill:{k.INK};letter-spacing:.24em}}"
    + f".c{{font-family:'Fira400',ui-monospace,monospace;font-size:{KICKER_SIZE}px;"
    f"fill:{k.FAINT};letter-spacing:.12em}}"
)


def main() -> None:
    p = k.open_svg(W, H, f"{NAME} — {SUB}", STYLES)
    p.append(k.text(0, 74, NAME, "n"))
    p.append(k.rule(0, 92, W))
    p.append(k.text(2, 116, SUB, "s"))
    p.append(k.text(2, 140, KICKER, "c"))
    k.write(OUT, p)


if __name__ == "__main__":
    main()
