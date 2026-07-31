#!/usr/bin/env python3
"""Draw the stack panel.

This deliberately replaces the usual top-languages chart. That chart has to be
computed over *public* repos only -- the workflow's token cannot see private
ones, and mixing the two makes the output depend on who ran the script. On this
account the public set is two repositories, so a bytes-per-language chart would
render as "JavaScript, mostly", which is a worse description than no chart.

Every entry below is taken from the `tech:` front matter of a project on
olereinhold.com, so the panel describes work that exists rather than badges
collected. Nothing here is a logo fetched from a third-party service.

    .venv/bin/python scripts/make_stack.py
"""
import pathlib

import svgkit as k

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "stack.svg"

# label, items, and the project each row is drawn from (kept as a comment so
# the provenance survives edits)
ROWS = [
    ("languages", "Python · Java · TypeScript · GDScript"),
    ("ai & data", "Claude API · Google Gemini · pandas · NumPy · OpenCV · MediaPipe"),
    ("services", "Spring Boot · FastAPI · PostgreSQL · SQLite · Docker"),
    ("interfaces", "React · Hugo · Godot · Tkinter"),
    ("testing", "Playwright · Vitest"),
    ("hardware", "Fusion 360 · Raspberry Pi · 3D printing"),
]

FOOT = "every entry ships in a project listed above"

W = 880
PAD_X = 0
LABEL_X = 2
ITEM_X = 150
ROW_H = 31
TOP = 8
LABEL_SIZE = 11.5
ITEM_SIZE = 12.5
FOOT_SIZE = 10.5

STYLES = (
    k.face(400)
    + k.face(600)
    + f".k{{font-family:'Fira400',ui-monospace,monospace;font-size:{LABEL_SIZE}px;"
    f"fill:{k.FAINT};letter-spacing:.1em}}"
    + f".v{{font-family:'Fira600',ui-monospace,monospace;font-size:{ITEM_SIZE}px;"
    f"fill:{k.INK};letter-spacing:.02em}}"
    + f".f{{font-family:'Fira400',ui-monospace,monospace;font-size:{FOOT_SIZE}px;"
    f"fill:{k.FAINT};letter-spacing:.06em}}"
)


def main() -> None:
    h = TOP + len(ROWS) * ROW_H + 30
    parts = k.open_svg(W, h, "Stack: " + "; ".join(f"{a}: {b}" for a, b in ROWS), STYLES)

    for i, (label, items) in enumerate(ROWS):
        y = TOP + i * ROW_H
        # A hairline above every row but the first: the site's menu grid is
        # built from exactly these, not from boxes.
        if i:
            parts.append(k.rule(PAD_X, y, W))
        base = y + ROW_H * 0.68
        parts.append(k.text(LABEL_X, base, label, "k"))
        parts.append(k.text(ITEM_X, base, items, "v"))

    y_foot = TOP + len(ROWS) * ROW_H
    parts.append(k.rule(PAD_X, y_foot, W))
    parts.append(k.text(LABEL_X, y_foot + 19, FOOT, "f"))
    k.write(OUT, parts)


if __name__ == "__main__":
    main()
