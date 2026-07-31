#!/usr/bin/env python3
"""Shared SVG primitives for the profile graphics.

Every graphic on this page is drawn here and committed to this repo. Nothing is
fetched from a third-party card service at render time, so nothing on the page
can 503, rate-limit, or quietly restyle itself.

Design tokens are lifted from the portfolio site's `assets/css/main.css` so the
two surfaces stay one design:

    --bg-primary     #0a0a0a
    --text-primary   #f0f0f0
    --text-secondary rgba(255,255,255,.6)
    --border-color   rgba(255,255,255,.15)

The panels paint their own background rather than adapting to the viewer's
theme. Inside an SVG loaded through <img>, `prefers-color-scheme` resolves
against the OS, not GitHub's in-app theme toggle -- so an adaptive panel shows
white ink on a white page for anyone running OS-dark with GitHub-light. A panel
that paints #0a0a0a is deterministic everywhere, and pitch black *is* the
site's design language rather than an approximation of it.
"""
import base64
import pathlib

FONTS = pathlib.Path(__file__).resolve().parent / "fonts"

BG = "#0a0a0a"
INK = "#f0f0f0"
DIM = "rgba(255,255,255,.6)"
FAINT = "rgba(255,255,255,.32)"
RULE = "rgba(255,255,255,.15)"

_CACHE: dict[str, str] = {}


def face(weight: int = 400) -> str:
    """Return an @font-face rule with the subset inlined as base64.

    Each SVG has to carry its own copy: an <img>-loaded SVG cannot fetch a
    subresource, so an external font URL silently falls back to the system
    monospace. Subsetting keeps the cost at ~4.6 KB per file instead of ~400 KB.
    """
    key = f"w{weight}"
    if key not in _CACHE:
        path = FONTS / f"firacode-{weight}.woff2"
        if not path.exists():
            raise SystemExit(f"missing {path} -- run scripts/subset_fonts.py first")
        b64 = base64.b64encode(path.read_bytes()).decode()
        _CACHE[key] = (
            f"@font-face{{font-family:'Fira{weight}';font-style:normal;"
            f"font-weight:{weight};"
            f"src:url(data:font/woff2;base64,{b64}) format('woff2');}}"
        )
    return _CACHE[key]


def esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def open_svg(w: float, h: float, label: str, styles: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:g}" height="{h:g}" '
        f'viewBox="0 0 {w:g} {h:g}" role="img" aria-label="{esc(label)}">',
        f"<style>{styles}</style>",
        f'<rect width="{w:g}" height="{h:g}" fill="{BG}"/>',
    ]


def text(
    x: float, y: float, s: str, cls: str = "b", anchor: str = "start", extra: str = ""
) -> str:
    a = f' text-anchor="{anchor}"' if anchor != "start" else ""
    return f'<text class="{cls}" x="{x:g}" y="{y:g}"{a}{extra}>{esc(s)}</text>'


def rule(x1: float, y: float, x2: float, opacity: float = 1.0) -> str:
    """A hairline. The site's menu grid is built from exactly these."""
    op = f' opacity="{opacity:g}"' if opacity != 1.0 else ""
    return (
        f'<line x1="{x1:g}" y1="{y:g}" x2="{x2:g}" y2="{y:g}" '
        f'stroke="{RULE}" stroke-width="1"{op}/>'
    )


def write(path: pathlib.Path, parts: list[str]) -> None:
    parts.append("</svg>")
    path.write_text("".join(parts))
    print(f"{path.name:22} {path.stat().st_size / 1024:5.1f} KB")
