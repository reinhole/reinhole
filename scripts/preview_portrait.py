#!/usr/bin/env python3
"""Rasterise the resampled portrait at its true README size, for tuning.

Reading the grid in a terminal is misleading: the terminal's cell aspect and
font are not the ones the SVG ships. This draws the same characters with the
same Fira Code face at the same advance and the same 460px display width, so
what you see here is what a visitor sees.

    .venv/bin/python scripts/preview_portrait.py [out.png]
"""
import pathlib
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import make_portrait as mp  # noqa: E402

TTF = (
    pathlib.Path(__file__).resolve().parent
    / "fonts" / "fira_extract" / "ttf" / "FiraCode-Regular.ttf"
)
DISPLAY_W = 460  # the width the README sets on ascii.svg
SUPERSAMPLE = 4  # so the glyph shapes stay judgeable on screen


def main() -> None:
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "portrait-preview.png")
    rows = mp.to_rows(mp.load_density())

    fs = DISPLAY_W / mp.COLS / (mp.ADVANCE + mp.TRACKING) * SUPERSAMPLE
    cw = fs * (mp.ADVANCE + mp.TRACKING)
    ch = fs
    pad = 14 * SUPERSAMPLE

    img = Image.new(
        "RGB",
        (int(mp.COLS * cw + pad * 2), int(len(rows) * ch + pad * 2)),
        "#0a0a0a",
    )
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(str(TTF), int(fs))
    for i, row in enumerate(rows):
        # Drawn per character: PIL would apply its own spacing to a whole
        # string, and the point of this preview is to honour the fixed advance.
        for j, ch_ in enumerate(row):
            if ch_ != " ":
                draw.text((pad + j * cw, pad + i * ch), ch_, font=font, fill="#f0f0f0")
    img.save(out)
    print(f"{out}: {mp.COLS}x{len(rows)} chars, displays at {DISPLAY_W}px wide")


if __name__ == "__main__":
    main()
