#!/usr/bin/env python3
"""Render the portfolio site's ASCII portrait as a self-typing SVG.

The source of truth is the same file the website prints in its hero,
`portfolio-site/assets/portrait_ascii.txt`, so the two pages cannot drift into
showing different portraits.

Run locally, once, and commit ascii.svg. This deliberately does NOT run in CI:
generating the same file in two places guarantees merge conflicts, and the
portrait has no reason to change nightly.

    .venv/bin/python scripts/make_portrait.py

Why the grid is resampled rather than copied
--------------------------------------------
The site's grid is 250 columns. It can afford that because it sets the portrait
in `cqw` units against a full-viewport hero. A README column is ~880px at its
widest and GitHub scales images down from there, so 250 columns lands near 2px
per character and the whole thing collapses into grey noise. Legibility needs
roughly 5px per character, which caps a 460px-wide block at ~90 columns.

So the characters are read back as ink densities, resampled as an image, and
re-mapped onto the site's own six-level ramp. The artwork survives; only the
resolution changes.
"""
import base64
import pathlib

import cv2
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE_ASCII = (
    ROOT.parent / "Personal_Website" / "portfolio-site" / "assets" / "portrait_ascii.txt"
)
OUT = ROOT / "ascii.svg"
RAMP_FONT = ROOT / "scripts" / "fonts" / "firacode-ramp.woff2"

# The site's ramp, blank -> solid. Kept exactly: it is part of the artwork.
RAMP = " ·-+#@"
# Approximate ink coverage per glyph, used to read the source back as an image.
INK = {" ": 0.0, "·": 0.10, "-": 0.20, "+": 0.34, "#": 0.70, "@": 0.92}

COLS = 90
# Crop the source grid to head-and-shoulders. Below this the photo is flat torso
# that resamples to an even field of '·' -- 30% more height carrying no subject.
CROP_ROWS = 152

# Cell geometry, matched to how the site sets the same text:
#   font-family Fira Code  -> advance 1200/1950 upm = 0.61538 em
#   letter-spacing -0.02em -> 0.59538 em effective
#   line-height 1.0        -> 1.0 em
# Fira Code is NOT 0.600 like JetBrains Mono; every constant derived from 0.600
# is wrong here. Measure the font, never inherit the number.
FONT_SIZE = 8.6
ADVANCE = 0.61538
TRACKING = -0.02
CHAR_W = FONT_SIZE * (ADVANCE + TRACKING)
CHAR_H = FONT_SIZE * 1.0

STAGGER = 0.09  # seconds between row starts, top to bottom
WIPE = 0.55     # seconds for one row to type


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


def to_rows(density: np.ndarray) -> list[str]:
    d = density[:CROP_ROWS]
    h, w = d.shape
    # Source and output share a cell aspect, so the resample is proportional.
    rows = round(h * COLS / w)
    small = cv2.resize(d, (COLS, rows), interpolation=cv2.INTER_AREA)
    idx = np.clip(
        (small / max(INK.values()) * (len(RAMP) - 1)).round().astype(int),
        0,
        len(RAMP) - 1,
    )
    return ["".join(RAMP[i] for i in row) for row in idx]


def font_face() -> str:
    if not RAMP_FONT.exists():
        raise SystemExit(f"missing {RAMP_FONT} -- run scripts/subset_fonts.py first")
    b64 = base64.b64encode(RAMP_FONT.read_bytes()).decode()
    # An external font URL cannot work: this SVG loads through an <img>, and
    # browsers refuse subresource fetches for image documents. Base64 does.
    return (
        "@font-face{font-family:'FiraRamp';font-style:normal;font-weight:400;"
        f"src:url(data:font/woff2;base64,{b64}) format('woff2');}}"
    )


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build(rows: list[str]) -> str:
    pad = 14.0
    row_w = COLS * CHAR_W
    w = row_w + pad * 2
    h = len(rows) * CHAR_H + pad * 2

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.1f}" height="{h:.1f}" '
        f'viewBox="0 0 {w:.1f} {h:.1f}" role="img" '
        f'aria-label="ASCII portrait of Ole Reinhold, typing itself line by line">',
        "<style>"
        + font_face()
        + ".r{font-family:'FiraRamp',ui-monospace,monospace;"
        f"font-size:{FONT_SIZE}px;letter-spacing:{TRACKING * FONT_SIZE:.3f}px;"
        "fill:#f0f0f0;white-space:pre}"
        "</style>",
        f'<rect width="{w:.1f}" height="{h:.1f}" fill="#0a0a0a"/>',
    ]

    for i, row in enumerate(rows):
        # Baseline sits near the bottom of the cell; 0.78em is the visual centre
        # for Fira Code at line-height 1.
        y = pad + i * CHAR_H + CHAR_H * 0.78
        begin = f"{i * STAGGER:.2f}s"
        clip_y = pad + i * CHAR_H
        # Each row is revealed by a clip rect widening from zero, with a block
        # riding the wipe edge as a cursor. fill="freeze" so the portrait types
        # once and stops -- no looping.
        out.append(
            f'<clipPath id="w{i}"><rect x="{pad:.1f}" y="{clip_y:.2f}" '
            f'height="{CHAR_H:.2f}" width="0">'
            f'<animate attributeName="width" values="0;{row_w:.1f}" '
            f'begin="{begin}" dur="{WIPE}s" fill="freeze"/></rect></clipPath>'
        )
        out.append(
            f'<text class="r" x="{pad:.1f}" y="{y:.2f}" clip-path="url(#w{i})">'
            f"{esc(row)}</text>"
        )
        out.append(
            f'<rect fill="#f0f0f0" y="{clip_y + CHAR_H * 0.15:.2f}" '
            f'width="{CHAR_W:.2f}" height="{CHAR_H * 0.7:.2f}" x="{pad:.1f}" opacity="0">'
            f'<animate attributeName="x" values="{pad:.1f};{pad + row_w:.1f}" '
            f'begin="{begin}" dur="{WIPE}s" fill="freeze"/>'
            f'<set attributeName="opacity" to="1" begin="{begin}"/>'
            f'<set attributeName="opacity" to="0" begin="{i * STAGGER + WIPE:.2f}s"/>'
            "</rect>"
        )

    out.append("</svg>")
    return "".join(out)


def main() -> None:
    rows = to_rows(load_density())
    OUT.write_text(build(rows))
    kb = OUT.stat().st_size / 1024
    print(
        f"{OUT.name}: {COLS}x{len(rows)} chars, {kb:.0f} KB, "
        f"types in {len(rows) * STAGGER + WIPE:.1f}s"
    )


if __name__ == "__main__":
    main()
