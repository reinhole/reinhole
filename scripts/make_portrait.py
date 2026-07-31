#!/usr/bin/env python3
"""The ASCII portrait: character grid, and the self-typing SVG fragment.

This is a module, not a standalone graphic. The portrait is composed into
`hero.svg` beside the wordmark rather than stacked above it -- as its own
full-width block it cost 471px of scroll before the page said anything.

The source of truth is the same file the website prints in its hero,
`portfolio-site/assets/portrait_ascii.txt`, so the two cannot drift into
showing different portraits. Run `make_hero.py` to regenerate.

Why the grid is resampled rather than copied
--------------------------------------------
The site's grid is 250 columns. It can afford that because it sets the portrait
in `cqw` units against a full-viewport hero. In the hero composition the
portrait is ~300px wide, where 250 columns land near 1px per character and
collapse into grey noise. Legibility needs roughly 5px per character.

So the characters are read back as ink densities, resampled as an image, and
re-mapped onto the site's own six-level ramp. The artwork survives; only the
resolution changes.
"""
import pathlib

import cv2
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE_ASCII = (
    ROOT.parent / "Personal_Website" / "portfolio-site" / "assets" / "portrait_ascii.txt"
)

# The site's ramp, blank -> solid. Kept exactly: it is part of the artwork.
RAMP = " ·-+#@"
# Approximate ink coverage per glyph, used to read the source back as an image.
INK = {" ": 0.0, "·": 0.10, "-": 0.20, "+": 0.34, "#": 0.70, "@": 0.92}

# Crop the source grid to head-and-shoulders. Below this the photo is flat torso
# that resamples to an even field of '·' -- 30% more height carrying no subject.
CROP_ROWS = 152

# Fira Code advances 1200/1950 upm = 0.61538 em, NOT the 0.600 that JetBrains
# Mono uses. The site tracks it -0.02em at line-height 1.
ADVANCE = 0.61538
TRACKING = -0.02
CELL = ADVANCE + TRACKING  # 0.59538 em per column, 1 em per row

STAGGER = 0.075  # seconds between row starts, top to bottom
CPS = 190.0      # characters per second -- a constant *speed*, not a constant
                 # duration, so every row types at the same rate
MIN_DUR = 0.12   # floor, so a two-character row still reads as a keystroke


def load_density() -> np.ndarray:
    if not SITE_ASCII.exists():
        raise SystemExit(f"missing {SITE_ASCII}")
    rows = SITE_ASCII.read_text().rstrip("\n").split("\n")
    width = max(len(r) for r in rows)
    grid = np.array(
        [[INK.get(c, 0.0) for c in r.ljust(width)] for r in rows], dtype=np.float32
    )
    # Trim the blank margin the site file carries around the subject.
    nz = np.argwhere(grid > 0)
    (r0, c0), (r1, c1) = nz.min(0), nz.max(0)
    return grid[r0 : r1 + 1, c0 : c1 + 1]


def to_rows(cols: int) -> list[str]:
    d = load_density()[:CROP_ROWS]
    h, w = d.shape
    # Source and output share a cell aspect, so the resample is proportional.
    small = cv2.resize(d, (cols, round(h * cols / w)), interpolation=cv2.INTER_AREA)
    idx = np.clip(
        (small / max(INK.values()) * (len(RAMP) - 1)).round().astype(int),
        0,
        len(RAMP) - 1,
    )
    return ["".join(RAMP[i] for i in row) for row in idx]


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def typing_fragment(
    rows: list[str], ox: float, oy: float, font_size: float, ink: str
) -> tuple[list[str], float, float]:
    """SVG for the portrait typing itself. Returns (parts, width, height)."""
    cw = font_size * CELL
    ch = font_size
    parts: list[str] = []

    for i, row in enumerate(rows):
        # Type only the row's own content span. Animating the full width sends
        # the cursor marching through the blank margin long after the last
        # character landed, so cursors detach and read as drifting specks.
        stripped = row.rstrip()
        if not stripped:
            continue
        c0 = len(row) - len(row.lstrip())
        c1 = len(stripped)
        span = (c1 - c0) * cw
        x0 = ox + c0 * cw
        top = oy + i * ch
        start = i * STAGGER
        dur = max(MIN_DUR, (c1 - c0) / CPS)
        begin = f"{start:.3f}s"

        # A clip rect widening from zero, with a block riding the wipe edge as
        # a cursor. fill="freeze" so the portrait types once and stops.
        parts.append(
            f'<clipPath id="w{i}"><rect x="{x0:.2f}" y="{top:.2f}" '
            f'height="{ch:.2f}" width="0">'
            f'<animate attributeName="width" values="0;{span:.2f}" '
            f'begin="{begin}" dur="{dur:.3f}s" fill="freeze"/></rect></clipPath>'
        )
        parts.append(
            f'<text class="px" x="{ox:.2f}" y="{top + ch * 0.78:.2f}" '
            f'clip-path="url(#w{i})">{esc(row)}</text>'
        )
        parts.append(
            f'<rect fill="{ink}" y="{top + ch * 0.15:.2f}" width="{cw:.2f}" '
            f'height="{ch * 0.7:.2f}" x="{x0:.2f}" opacity="0">'
            f'<animate attributeName="x" values="{x0:.2f};{x0 + span:.2f}" '
            f'begin="{begin}" dur="{dur:.3f}s" fill="freeze"/>'
            f'<set attributeName="opacity" to="1" begin="{begin}"/>'
            f'<set attributeName="opacity" to="0" begin="{start + dur:.3f}s"/>'
            "</rect>"
        )

    return parts, len(rows[0]) * cw, len(rows) * ch


if __name__ == "__main__":
    r = to_rows(58)
    print(f"{len(r[0])} cols x {len(r)} rows")
    print("\n".join(r))
