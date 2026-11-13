#!/usr/bin/env python3
"""Regenerate contributions.svg from a public GitHub contribution calendar.

Usage:
    python make_contributions.py --user d1masg0d --out contributions.svg

No third-party packages are needed, so this runs unchanged in GitHub Actions.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
import urllib.request

CELL, GAP = 15.5, 4.5
STEP = CELL + GAP
X0, Y0 = 96, 164
W, H = 1200, 384

# Palette: #0D0D0D background, #252526 empty cells, cyan ramp for activity.
BG_TOP, BG_MID, BG_BOTTOM = "#0D0D0D", "#161616", "#0D0D0D"
RAMP = ["#252526", "#0A5454", "#04BFBF", "#04D9D9", "#05F2F2"]
INK, SUB, MUTED, DIM = "#F5F5F5", "#A3A3A3", "#737373", "#5A5A5A"

TD_RE = re.compile(r"<td\b[^>]*>", re.IGNORECASE)
TIP_RE = re.compile(r"<tool-tip\b([^>]*)>([^<]*)</tool-tip>", re.IGNORECASE)
ATTR_RE = r'\b{}\s*=\s*"([^"]*)"'
COUNT_RE = re.compile(r"^([\d,]+)\s+contribution")
ID_RE = re.compile(r"contribution-day-component-(\d+)-(\d+)")


def attr(text: str, name: str) -> str | None:
    match = re.search(ATTR_RE.format(name), text)
    return match.group(1) if match else None


def fetch(user: str) -> str:
    url = f"https://github.com/users/{user}/contributions"
    request = urllib.request.Request(url, headers={"User-Agent": "contribution-card/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", "replace")


def parse(html: str):
    """Return (date, row, column, level, count) tuples sorted by date."""
    tooltips = {}
    for attrs, text in TIP_RE.findall(html):
        target = attr(attrs, "for")
        if target:
            tooltips[target] = text.strip()

    days = []
    for tag in TD_RE.findall(html):
        date, element_id, level = attr(tag, "data-date"), attr(tag, "id"), attr(tag, "data-level")
        if not date or not element_id or level is None:
            continue
        position = ID_RE.search(element_id)
        if not position:
            continue
        count = 0
        match = COUNT_RE.match(tooltips.get(element_id, ""))
        if match:
            count = int(match.group(1).replace(",", ""))
        days.append(
            (dt.date.fromisoformat(date), int(position.group(1)), int(position.group(2)), int(level), count)
        )

    if not days:
        sys.exit("Could not read the contribution calendar; GitHub may have changed its markup.")

    days.sort(key=lambda day: day[0])
    return days


def stats(days):
    total = sum(count for *_, count in days)
    active = sum(1 for *_, count in days if count)
    longest = run = 0
    for *_, count in days:
        run = run + 1 if count else 0
        longest = max(longest, run)
    return total, active, longest


def year_label(days) -> str:
    years = {day.year for day, *_ in days}
    return str(years.pop()) if len(years) == 1 else "LAST 12 MONTHS"


def build(days, user: str) -> str:
    total, active, longest = stats(days)

    cells = []
    for day, row, column, level, count in days:
        x, y = X0 + column * STEP, Y0 + row * STEP
        label = f"{count} contribution" + ("" if count == 1 else "s") + f" on {day.strftime('%b %-d, %Y')}"
        cells.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{CELL}" height="{CELL}" rx="3" '
            f'fill="{RAMP[level]}"><title>{label}</title></rect>'
        )

    months, seen = [], set()
    for day, _, column, _, _ in days:
        if day.day == 1 and day.month not in seen:
            seen.add(day.month)
            months.append((column, day.strftime("%b")))
    month_text = "".join(
        f'<text class="month" x="{X0 + column * STEP:.1f}" y="{Y0 - 12}">{name}</text>'
        for column, name in months
    )
    week_text = "".join(
        f'<text class="week" x="{X0 - 14}" y="{Y0 + row * STEP + 11.5}" text-anchor="end">{name}</text>'
        for row, name in [(1, "Mon"), (3, "Wed"), (5, "Fri")]
    )

    legend_x = W - 196
    legend = "".join(
        f'<rect x="{legend_x + 40 + index * 16}" y="{H - 77}" width="11" height="11" rx="2.5" fill="{RAMP[index]}"/>'
        for index in range(5)
    )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="ct cd">
  <title id="ct">GitHub contribution activity for {user}</title>
  <desc id="cd">{total} contributions across {active} active days, longest streak {longest} days, shown as a terminal-style heatmap.</desc>
  <defs>
    <linearGradient id="panel" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{BG_TOP}"/><stop offset="0.65" stop-color="{BG_MID}"/><stop offset="1" stop-color="{BG_BOTTOM}"/>
    </linearGradient>
    <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#05F2F2"/><stop offset="1" stop-color="#04BFBF"/>
    </linearGradient>
    <radialGradient id="glow" cx="50%" cy="50%" r="50%">
      <stop offset="0" stop-color="#05F2F2" stop-opacity="0.10"/>
      <stop offset="1" stop-color="#05F2F2" stop-opacity="0"/>
    </radialGradient>
    <style>
      .mono {{ font-family: 'JetBrains Mono','Fira Code','SFMono-Regular',Consolas,monospace; }}
      .cmd {{ font-size: 15px; fill: {INK}; }}
      .range {{ font-size: 12px; fill: {DIM}; letter-spacing: 0.4px; }}
      .dollar {{ font-size: 15px; fill: #05F2F2; }}
      .total {{ font-size: 46px; font-weight: 700; fill: #05F2F2; letter-spacing: -1px; }}
      .total-label {{ font-size: 12px; letter-spacing: 1.6px; fill: {MUTED}; }}
      .month {{ font-size: 11px; fill: {MUTED}; }}
      .week {{ font-size: 10px; fill: {DIM}; }}
      .legend {{ font-size: 11px; fill: {MUTED}; }}
      .chrome {{ font-size: 12px; fill: {MUTED}; }}
      .chrome-dim {{ font-size: 11px; fill: {DIM}; }}
      .bar {{ font-size: 11px; fill: {SUB}; }}
      .bar-dim {{ font-size: 10px; letter-spacing: 1.3px; fill: {MUTED}; }}
      .chip {{ font-size: 11px; font-weight: 700; letter-spacing: 1.2px; fill: #0D0D0D; }}
    </style>
  </defs>

  <rect width="{W}" height="{H}" fill="url(#panel)"/>
  <ellipse cx="1000" cy="120" rx="340" ry="200" fill="url(#glow)"/>
  <rect x="0" y="0" width="{W}" height="2" fill="url(#accent)" opacity="0.7"/>

  <g class="mono">
    <circle cx="38" cy="27" r="5" fill="#05F2F2"/>
    <circle cx="56" cy="27" r="5" fill="#04BFBF"/>
    <circle cx="74" cy="27" r="5" fill="#252526"/>
    <text class="chrome" x="600" y="32" text-anchor="middle">{user}@eindhoven: ~/contributions</text>
    <text class="chrome-dim" x="1164" y="32" text-anchor="end">zsh · 120×38</text>
  </g>

  <line x1="0" y1="54" x2="{W}" y2="54" stroke="#252526"/>
  <line x1="0" y1="55" x2="{W}" y2="55" stroke="#05F2F2" stroke-opacity="0.07"/>

  <g class="mono">
    <text class="dollar" x="48" y="96">$</text>
    <text class="cmd" x="66" y="96">contributions --last 12m</text>
    <text class="range" x="48" y="124">{days[0][0].isoformat()} → {days[-1][0].isoformat()}</text>
    <text class="total" x="1152" y="108" text-anchor="end">{total}</text>
    <text class="total-label" x="1152" y="128" text-anchor="end">CONTRIBUTIONS</text>
  </g>

  <g class="mono">
    {month_text}
    {week_text}
    <g>{"".join(cells)}</g>
  </g>

  <g class="mono">
    <text class="legend" x="{legend_x}" y="{H - 66}">Less</text>
    {legend}
    <text class="legend" x="{legend_x + 40 + 5 * 16 + 6}" y="{H - 66}">More</text>
  </g>

  <rect x="0" y="{H - 48}" width="{W}" height="48" fill="#141414"/>
  <line x1="0" y1="{H - 48}" x2="{W}" y2="{H - 48}" stroke="#252526"/>
  <rect x="32" y="{H - 36}" width="72" height="24" rx="3" fill="#05F2F2"/>
  <text class="mono chip" x="68" y="{H - 20}" text-anchor="middle">STATS</text>
  <text class="mono bar" x="120" y="{H - 20}">~/contributions</text>
  <text class="mono bar" x="250" y="{H - 20}" fill="#04BFBF">main*</text>
  <text class="mono bar-dim" x="1168" y="{H - 20}" text-anchor="end">{year_label(days)} · {active} ACTIVE DAYS · LONGEST STREAK {longest}D</text>
</svg>
'''


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a GitHub contribution card as SVG.")
    parser.add_argument("--user", required=True, help="GitHub username")
    parser.add_argument("--out", default="contributions.svg", help="output SVG path")
    args = parser.parse_args()

    days = parse(fetch(args.user))
    with open(args.out, "w", encoding="utf-8") as handle:
        handle.write(build(days, args.user))
    print(f"Wrote {args.out} ({len(days)} days)")


if __name__ == "__main__":
    main()
