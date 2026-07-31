#!/usr/bin/env python3
"""Draw the section headings as SVG.

GitHub strips <style>, style="", class="", <font> and inline <svg> from README
markdown, so an image is the only way to put the site's own typeface on a
heading. The form is the site's: a lowercase mono label, an index number, and a
hairline rule running to the right edge.

The tradeoff, stated plainly: an image heading has no anchor link, so GitHub's
README outline stays empty. The alt text carries the word for screen readers.

    .venv/bin/python scripts/make_headings.py
"""
import pathlib

import svgkit as k

ROOT = pathlib.Path(__file__).resolve().parent.parent

W, H = 880, 34
LABEL_SIZE = 13
NUM_SIZE = 11
BASE = 22  # baseline

SECTIONS = [
    ("01", "about", "hd-about.svg"),
    ("02", "selected work", "hd-work.svg"),
    ("03", "stack", "hd-stack.svg"),
    ("04", "activity", "hd-activity.svg"),
    ("05", "elsewhere", "hd-elsewhere.svg"),
    ("06", "colophon", "hd-colophon.svg"),
]

STYLES = (
    k.face(600)
    + k.face(400)
    + f".n{{font-family:'Fira400',ui-monospace,monospace;font-size:{NUM_SIZE}px;"
    f"fill:{k.FAINT};letter-spacing:.08em}}"
    + f".l{{font-family:'Fira600',ui-monospace,monospace;font-size:{LABEL_SIZE}px;"
    f"fill:{k.INK};letter-spacing:.14em}}"
)

# Fira Code advances 1200/1950 upm; tracking is added per character.
ADV = 0.61538


def label_width(s: str, size: float, tracking_em: float) -> float:
    return len(s) * size * (ADV + tracking_em)


def main() -> None:
    for num, label, filename in SECTIONS:
        parts = k.open_svg(W, H, f"{label} section heading", STYLES)
        parts.append(k.text(0, BASE, num, "n"))
        x_label = label_width(num, NUM_SIZE, 0.08) + 14
        parts.append(k.text(x_label, BASE, label, "l"))
        # Rule starts after the label and runs to the right edge, on the
        # label's optical centre line.
        x_rule = x_label + label_width(label, LABEL_SIZE, 0.14) + 14
        parts.append(k.rule(x_rule, BASE - 4, W))
        k.write(ROOT / filename, parts)


if __name__ == "__main__":
    main()
