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
    return f"{start.isoformat()}T00:00:00Z", f"{today.isoformat()}T23:59:59Z", today


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


def levels(series: list[tuple[dt.date, int]]) -> tuple[list[int], int]:
    """Quantile edges over the *active* days, and the peak.

    Not a linear share of the peak: one 90-contribution day would push almost
    every other day into the lowest bucket and the year would look empty.
    Quantiles keep all five levels populated, which is what GitHub's own
    calendar does.
    """
    active = sorted(c for _, c in series if c > 0)
    if not active:
        return [1, 2, 3, 4], 1
    edges = [active[min(len(active) - 1, int(q * len(active)))] for q in (0.2, 0.4, 0.6, 0.8)]
    return edges, active[-1]


def fmt(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def fmt_date(d: dt.date | None) -> str:
    return d.strftime("%d %b %Y").lower() if d else "—"


# --- graphics ---------------------------------------------------------------
def panel_stats(cc: dict, series: list[tuple[dt.date, int]], out: pathlib.Path) -> None:
    """Headline number, the four facts worth knowing, and a weekly column chart.

    Streaks live here rather than in their own panel: as a separate image they
    cost 118px of scroll to carry two integers.
    """
    total = cc["contributionCalendar"]["totalContributions"]
    private = cc["restrictedContributionsCount"]
    busiest = max(series, key=lambda x: x[1])
    active = sum(1 for _, c in series if c > 0)
    (cur, _, _), (best, _, _) = streaks(series)

    h = 210
    styles = (
        k.face(400)
        + k.face(600)
        + f".big{{font-family:'Fira600',ui-monospace,monospace;font-size:62px;"
        f"fill:{k.INK};letter-spacing:-.02em}}"
        + f".k{{font-family:'Fira400',ui-monospace,monospace;font-size:10.5px;"
        f"fill:{k.FAINT};letter-spacing:.12em}}"
        + f".v{{font-family:'Fira600',ui-monospace,monospace;font-size:14px;fill:{k.INK}}}"
    )
    p = k.open_svg(W, h, f"{total} contributions in the last 365 days", styles)

    p.append(k.text(2, 64, fmt(total), "big"))
    p.append(k.text(4, 86, "CONTRIBUTIONS · LAST 365 DAYS", "k"))

    col = 452
    facts = [
        ("ACTIVE DAYS", f"{active} / {len(series)}"),
        ("CURRENT STREAK", f"{cur} days" if cur != 1 else "1 day"),
        ("LONGEST STREAK", f"{best} days"),
        ("BUSIEST DAY", f"{busiest[1]} · {fmt_date(busiest[0])}"),
    ]
    for i, (key, val) in enumerate(facts):
        y = 26 + i * 22
        p.append(k.text(col, y, key, "k"))
        p.append(k.text(col + 190, y, val, "v"))

    # Weekly columns, not a line. Daily contributions are sparse and discrete;
    # a line through 0,0,11,0 claims values that never existed. A zero week is
    # empty space.
    weeks = [sum(c for _, c in series[i : i + 7]) for i in range(0, len(series), 7)]
    base_y, bar_h = 192, 54
    peak = max(weeks) or 1
    gap = 2.0
    bw = (W - gap * (len(weeks) - 1)) / len(weeks)
    p.append(k.rule(0, 122, W))
    p.append(k.text(2, 140, f"PER WEEK · BUSIEST WEEK {peak}", "k"))
    p.append(k.rule(0, base_y + 1, W))
    for i, v in enumerate(weeks):
        bh = max(1.0, round(v / peak * bar_h, 1))
        p.append(
            f'<rect fill="{k.INK}" x="{round(i * (bw + gap), 2):g}" '
            f'y="{base_y - bh:g}" width="{bw:.2f}" height="{bh:g}" '
            f'opacity="{0.28 + 0.72 * (v / peak):.2f}"/>'
        )
    k.write(out, p)


def panel_year(series: list[tuple[dt.date, int]], out: pathlib.Path) -> None:
    """The year as a grid of filled squares, one per day.

    This started as one *character* per day on the portrait's ramp. That reads
    as texture at the portrait's ~5px cell, but a full-width year grid needs a
    ~17px cell, and at that size '#' and '@' stop being density and become
    glyphs -- the panel looked like stray ASCII rather than data. Squares carry
    the same five quantile levels with none of the noise, and stay inside the
    design language: hard edges, no radius, one hue, opacity doing the work.
    """
    edges, peak = levels(series)

    def level(c: int) -> int:
        return 0 if c == 0 else 1 + sum(1 for e in edges if c > e)

    # GitHub weeks start Sunday; pad the first column so weekdays line up.
    weeks: list[list[tuple[dt.date, int] | None]] = []
    col: list[tuple[dt.date, int] | None] = [None] * ((series[0][0].weekday() + 1) % 7)
    for day, count in series:
        col.append((day, count))
        if len(col) == 7:
            weeks.append(col)
            col = []
    if col:
        weeks.append(col + [None] * (7 - len(col)))

    pitch = W / len(weeks)
    gap = 3.0
    cell = pitch - gap
    top = 36
    h = top + 7 * pitch + 40
    # Level 0 is a faint plate rather than nothing, so the grid reads as a
    # calendar with quiet days instead of holes with marks floating in them.
    fills = [0.07, 0.26, 0.44, 0.62, 0.81, 1.0]

    styles = (
        k.face(400)
        + f".k{{font-family:'Fira400',ui-monospace,monospace;font-size:10.5px;"
        f"fill:{k.FAINT};letter-spacing:.12em}}"
    )
    total = sum(c for _, c in series)
    p = k.open_svg(W, h, f"Contribution calendar: {total} contributions over the last year", styles)

    seen: set[str] = set()
    for wi, week in enumerate(weeks):
        x = wi * pitch
        for di, slot in enumerate(week):
            if slot is None:
                continue
            day, count = slot
            y = top + di * pitch
            p.append(
                f'<rect x="{x:.2f}" y="{y:.2f}" width="{cell:.2f}" '
                f'height="{cell:.2f}" fill="{k.INK}" '
                f'opacity="{fills[level(count)]:.2f}"/>'
            )
        # Month label above the week that starts a new month.
        first = next((s for s in week if s), None)
        if first:
            tag = first[0].strftime("%b").upper()
            if first[0].day <= 7 and tag not in seen:
                seen.add(tag)
                p.append(k.text(x, 22, tag, "k"))

    y_leg = top + 7 * pitch + 26
    p.append(k.rule(0, y_leg - 20, W))
    p.append(k.text(2, y_leg, "QUIET", "k"))
    lx = 52
    for i, op in enumerate(fills):
        p.append(
            f'<rect x="{lx + i * 15:.1f}" y="{y_leg - 9:.1f}" width="11" '
            f'height="11" fill="{k.INK}" opacity="{op:.2f}"/>'
        )
    p.append(k.text(lx + len(fills) * 15 + 6, y_leg, "BUSY", "k"))
    p.append(k.text(W, y_leg, f"PEAK {peak} IN ONE DAY", "k", anchor="end"))
    k.write(out, p)


def main() -> None:
    cc = fetch()
    series = days(cc)
    if len(series) < 300:
        raise SystemExit(f"only {len(series)} days returned -- refusing to draw")
    panel_stats(cc, series, ROOT / "stats.svg")
    panel_year(series, ROOT / "year.svg")
    total = cc["contributionCalendar"]["totalContributions"]
    print(
        f"{total} contributions over {len(series)} days "
        f"({cc['restrictedContributionsCount']} in private repos)"
    )


if __name__ == "__main__":
    main()
