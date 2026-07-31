#!/usr/bin/env python3
"""Draw the activity graphics from the GitHub GraphQL API.

Runs in CI on a schedule and commits the result. Standard library only --
urllib for the API, nothing to break in a workflow six months from now.

Two determinism traps, both of which produce a nightly stream of meaningless
commits if you miss them:

1. The window is pinned to whole UTC days. Left alone, contributionsCollection
   measures "the past year" from the moment of the request, so two runs minutes
   apart bucket days into different weeks and shift the sparkline by a fraction
   of a pixel -- enough to look changed every night.
2. Numbers are rounded and formatted before they reach the SVG, so a value that
   is visually identical is also byte-identical.

The workflow commits only when a file actually changed, so a quiet day is a
no-op rather than an empty commit.

    GITHUB_TOKEN=... GH_LOGIN=reinhole python3 scripts/generate_stats.py
"""
import datetime as dt
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import svgkit as k  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
API = "https://api.github.com/graphql"

W = 880
RAMP = " ·-+#@"  # the portrait's ramp, reused for the year grid

QUERY = """
query($login:String!, $from:DateTime!, $to:DateTime!) {
  user(login:$login) {
    contributionsCollection(from:$from, to:$to) {
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount weekday } }
      }
    }
  }
}
"""


# --- data -------------------------------------------------------------------
def window() -> tuple[str, str, dt.date]:
    """Whole UTC days: today-364 00:00:00Z .. today 23:59:59Z."""
    today = dt.datetime.now(dt.timezone.utc).date()
    start = today - dt.timedelta(days=364)
    return (
        f"{start.isoformat()}T00:00:00Z",
        f"{today.isoformat()}T23:59:59Z",
        today,
    )


def fetch() -> dict:
    token = os.environ.get("GITHUB_TOKEN")
    login = os.environ.get("GH_LOGIN")
    if not token or not login:
        raise SystemExit("set GITHUB_TOKEN and GH_LOGIN")
    frm, to, _ = window()
    body = json.dumps(
        {"query": QUERY, "variables": {"login": login, "from": frm, "to": to}}
    ).encode()
    req = urllib.request.Request(
        API,
        data=body,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": f"{login}-profile-stats",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if "errors" in payload:
        raise SystemExit(f"GraphQL: {payload['errors']}")
    return payload["data"]["user"]["contributionsCollection"]


def days(cc: dict) -> list[tuple[dt.date, int]]:
    out = []
    for week in cc["contributionCalendar"]["weeks"]:
        for d in week["contributionDays"]:
            out.append((dt.date.fromisoformat(d["date"]), d["contributionCount"]))
    return sorted(out)


def streaks(series: list[tuple[dt.date, int]]) -> tuple[tuple, tuple]:
    """Return (current, longest) as (length, start, end)."""
    best = (0, None, None)
    run, run_start = 0, None
    for day, count in series:
        if count > 0:
            run += 1
            run_start = run_start or day
            if run > best[0]:
                best = (run, run_start, day)
        else:
            run, run_start = 0, None

    # Current streak: walk back from the end. A zero *today* does not break it
    # -- the day is not over yet in every timezone.
    cur, end, start = 0, None, None
    for day, count in reversed(series):
        if count == 0:
            if end is None and day == series[-1][0]:
                continue  # today, still open
            break
        cur += 1
        end = end or day
        start = day
    return (cur, start, end), best


def fmt(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def fmt_date(d: dt.date | None) -> str:
    return d.strftime("%d %b %Y").lower() if d else "—"


# --- graphics ---------------------------------------------------------------
def panel_stats(cc: dict, series: list[tuple[dt.date, int]], out: pathlib.Path) -> None:
    total = cc["contributionCalendar"]["totalContributions"]
    private = cc["restrictedContributionsCount"]
    busiest = max(series, key=lambda x: x[1])
    active = sum(1 for _, c in series if c > 0)

    h = 200
    styles = (
        k.face(400)
        + k.face(600)
        + f".big{{font-family:'Fira600',ui-monospace,monospace;font-size:62px;"
        f"fill:{k.INK};letter-spacing:-.02em}}"
        + f".k{{font-family:'Fira400',ui-monospace,monospace;font-size:10.5px;"
        f"fill:{k.FAINT};letter-spacing:.12em}}"
        + f".v{{font-family:'Fira600',ui-monospace,monospace;font-size:15px;fill:{k.INK}}}"
        + f".bar{{fill:{k.INK}}}"
    )
    p = k.open_svg(W, h, f"{total} contributions in the last 365 days", styles)

    p.append(k.text(2, 64, fmt(total), "big"))
    p.append(k.text(4, 86, "CONTRIBUTIONS · LAST 365 DAYS", "k"))

    col = 470
    for i, (key, val) in enumerate(
        [
            ("ACTIVE DAYS", f"{active} / {len(series)}"),
            ("BUSIEST DAY", f"{busiest[1]} · {fmt_date(busiest[0])}"),
            ("IN PRIVATE REPOS", f"{fmt(private)}"),
        ]
    ):
        y = 24 + i * 30
        p.append(k.text(col, y, key, "k"))
        p.append(k.text(col + 200, y, val, "v"))

    # Weekly columns, not a line. Daily contributions are sparse and discrete;
    # a line through 0,0,11,0 claims values that never existed. A zero week is
    # empty space.
    weeks: list[int] = []
    for i in range(0, len(series), 7):
        weeks.append(sum(c for _, c in series[i : i + 7]))
    base_y, bar_h = 182, 56
    peak = max(weeks) or 1
    gap = 2.0
    bw = (W - gap * (len(weeks) - 1)) / len(weeks)
    p.append(k.rule(0, 108, W))
    p.append(k.text(2, 126, f"PER WEEK · PEAK {peak}", "k"))
    p.append(k.rule(0, base_y + 1, W))
    for i, v in enumerate(weeks):
        bh = max(1.0, round(v / peak * bar_h, 1))
        x = round(i * (bw + gap), 2)
        op = 0.28 + 0.72 * (v / peak)
        p.append(
            f'<rect class="bar" x="{x:g}" y="{base_y - bh:g}" '
            f'width="{bw:.2f}" height="{bh:g}" opacity="{op:.2f}"/>'
        )
    k.write(out, p)


def panel_streak(series: list[tuple[dt.date, int]], out: pathlib.Path) -> None:
    (cur, cur_s, cur_e), (best, best_s, best_e) = streaks(series)
    h = 118
    styles = (
        k.face(400)
        + k.face(600)
        + f".n{{font-family:'Fira600',ui-monospace,monospace;font-size:40px;fill:{k.INK}}}"
        + f".k{{font-family:'Fira400',ui-monospace,monospace;font-size:10.5px;"
        f"fill:{k.FAINT};letter-spacing:.12em}}"
        + f".d{{font-family:'Fira400',ui-monospace,monospace;font-size:11.5px;fill:{k.DIM}}}"
    )
    p = k.open_svg(W, h, f"Current streak {cur} days, longest {best} days", styles)

    half = W / 2
    # A single vertical hairline splits the panel into two bordered columns,
    # the way the site's menu overlay divides ACTIONS / WORDS / ABOUT.
    p.append(
        f'<line x1="{half:g}" y1="8" x2="{half:g}" y2="{h - 8:g}" '
        f'stroke="{k.RULE}" stroke-width="1"/>'
    )
    for i, (key, n, s, e) in enumerate(
        [("CURRENT STREAK", cur, cur_s, cur_e), ("LONGEST STREAK", best, best_s, best_e)]
    ):
        x = 2 + i * (half + 26)
        p.append(k.text(x, 30, key, "k"))
        p.append(k.text(x, 76, f"{n}", "n"))
        unit_x = x + len(str(n)) * 40 * 0.61538 + 10
        p.append(k.text(unit_x, 76, "days" if n != 1 else "day", "d"))
        p.append(k.text(x, 100, f"{fmt_date(s)} → {fmt_date(e)}" if n else "—", "d"))
    k.write(out, p)


def panel_year(series: list[tuple[dt.date, int]], out: pathlib.Path) -> None:
    """One character per day, on the portrait's own ramp."""
    peak = max(c for _, c in series) or 1
    active = sorted(c for _, c in series if c > 0)

    # Quantiles of the *active* days, not a linear share of the peak. One
    # 90-contribution day makes a linear scale put almost every other day in
    # the lowest bucket, and the grid comes out looking empty. Quantiles keep
    # the five levels populated, which is what GitHub's own calendar does.
    def cut(q: float) -> int:
        return active[min(len(active) - 1, int(q * len(active)))] if active else 1

    edges = [cut(q) for q in (0.2, 0.4, 0.6, 0.8)]

    # Index 0 stays reserved for a zero day, so an empty day is genuinely
    # empty rather than a faint mark.
    def glyph(c: int) -> str:
        if c == 0:
            return RAMP[0]
        level = 1 + sum(1 for e in edges if c > e)
        return RAMP[min(level, len(RAMP) - 1)]

    weeks: list[list[str]] = []
    col: list[str] = []
    # GitHub weeks start Sunday; pad the first column so weekdays line up.
    pad = (series[0][0].weekday() + 1) % 7
    col = [" "] * pad
    for day, count in series:
        col.append(glyph(count))
        if len(col) == 7:
            weeks.append(col)
            col = []
    if col:
        weeks.append(col + [" "] * (7 - len(col)))

    # Square-ish cells spanning the panel. The glyph advance is smaller than a
    # cell, so the difference is added as letter-spacing rather than stretched
    # with textLength -- stretching scales the gaps unevenly at the row ends.
    cw = W / len(weeks)
    fs = 20.0
    tracking = cw - fs * 0.61538
    ch = 17.0
    top = 30
    h = top + 7 * ch + 34
    styles = (
        k.face(400)
        + k.face(600)
        + f".g{{font-family:'Fira400',ui-monospace,monospace;font-size:{fs}px;"
        f"letter-spacing:{tracking:.3f}px;fill:{k.INK};white-space:pre}}"
        + f".k{{font-family:'Fira400',ui-monospace,monospace;font-size:10.5px;"
        f"fill:{k.FAINT};letter-spacing:.12em}}"
    )
    total = sum(c for _, c in series)
    p = k.open_svg(W, h, f"Contribution year: {total} contributions, one character per day", styles)
    p.append(k.text(2, 16, "THE YEAR, ONE CHARACTER PER DAY", "k"))

    for row in range(7):
        y = top + row * ch + fs * 0.8
        # One <text> per row with a fixed advance, so the grid cannot drift.
        line = "".join(w[row] if row < len(w) else " " for w in weeks)
        p.append(f'<text class="g" x="0" y="{y:.1f}">{k.esc(line)}</text>')

    y_leg = top + 7 * ch + 20
    p.append(k.rule(0, y_leg - 14, W))
    legend = "  ".join(RAMP[1:])
    p.append(
        k.text(2, y_leg, f"QUIET  {legend}  BUSY · PEAK {peak} IN ONE DAY", "k")
    )
    k.write(out, p)


def main() -> None:
    cc = fetch()
    series = days(cc)
    if len(series) < 300:
        raise SystemExit(f"only {len(series)} days returned -- refusing to draw")
    panel_stats(cc, series, ROOT / "stats.svg")
    panel_streak(series, ROOT / "streak.svg")
    panel_year(series, ROOT / "year.svg")
    total = cc["contributionCalendar"]["totalContributions"]
    print(f"{total} contributions over {len(series)} days "
          f"({cc['restrictedContributionsCount']} in private repos)")


if __name__ == "__main__":
    main()
