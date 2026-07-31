#!/usr/bin/env python3
"""Subset Fira Code into the smallest woff2 files each SVG role needs.

Every SVG has to carry its own copy of the font -- an <img>-loaded SVG cannot
fetch a subresource, so a base64 @font-face is the only option. Inlining the
full 400 KB TTF into each file would cost megabytes; subsetting keeps the whole
page in the tens of KB.

Fira Code is SIL OFL 1.1, so it may ship inside a public repo. OFL.txt sits
next to the woff2 files, which is what the licence requires.

    ../.venv/bin/python scripts/subset_fonts.py
"""
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
TTF = HERE / "fonts" / "fira_extract" / "ttf"
OUT = HERE / "fonts"

RAMP = " ·-+#@"  # the portfolio site's own six-level ramp
# Lowercase labels, digits, and the punctuation the data graphics actually set.
LATIN = (
    " abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789.,:;'/()[]%+-−·→_@#&?!"
)

JOBS = [
    ("FiraCode-Regular.ttf", RAMP, "firacode-ramp.woff2"),
    ("FiraCode-SemiBold.ttf", LATIN, "firacode-head.woff2"),
    ("FiraCode-Regular.ttf", LATIN, "firacode-400.woff2"),
    ("FiraCode-SemiBold.ttf", LATIN, "firacode-600.woff2"),
]


def main() -> None:
    if not TTF.exists():
        raise SystemExit(f"missing {TTF} -- see scripts/fonts/README.md")
    for src, text, dest in JOBS:
        subprocess.run(
            [
                sys.executable, "-m", "fontTools.subset", str(TTF / src),
                f"--text={text}",
                "--flavor=woff2",
                # Drop ligatures: Fira Code's programming ligatures would fuse
                # ramp pairs like '=+' into a single glyph and shear the grid.
                "--layout-features=",
                "--no-hinting",
                "--desubroutinize",
                f"--output-file={OUT / dest}",
            ],
            check=True,
        )
        print(f"{dest:24} {(OUT / dest).stat().st_size / 1024:5.1f} KB  ({len(set(text))} chars)")


if __name__ == "__main__":
    main()
