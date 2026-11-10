#!/usr/bin/env python3
"""Regenerate languages.svg from the languages used across a user's public repos.

Run by the "Update languages chart" GitHub Action (daily, on demand, and when
this file changes). Uses only the Python standard library.

Environment:
  GITHUB_TOKEN  token for the GitHub API (provided automatically by Actions)
  GH_USER       GitHub username to chart (default: aabel3)
  OUT_FILE      output path (default: languages.svg)
"""
import json
import math
import os
import sys
import urllib.request
from xml.sax.saxutils import escape

API = "https://api.github.com"
USER = os.environ.get("GH_USER", "aabel3")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT_FILE = os.environ.get("OUT_FILE", "languages.svg")

MAX_SHOWN = 6  # languages listed individually; anything beyond is grouped as "Other"
BAR_X, BAR_W = 25, 445

# Blue palette for the social-network theme; "Other" is a neutral gray.
COLORS = ["#3b5998", "#8b9dc3", "#2f4373", "#4267b2", "#b3bfd9", "#5b74a8"]
OTHER_COLOR = "#c4c9d4"


def get(url):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "languages-chart-updater",
        **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}),
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def collect_bytes(user):
    """Sum bytes per language over the user's own, non-fork public repos."""
    totals = {}
    page = 1
    while True:
        repos = get(f"{API}/users/{user}/repos?per_page=100&type=owner&page={page}")
        if not repos:
            break
        for repo in repos:
            if repo.get("fork"):
                continue
            for lang, size in get(repo["languages_url"]).items():
                totals[lang] = totals.get(lang, 0) + size
        page += 1
    return totals


def build_rows(totals):
    """Return [(label, percent, color)] sorted by size, with a grouped 'Other'."""
    grand = sum(totals.values())
    if grand == 0:
        return []
    ordered = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    shown, rest = ordered[:MAX_SHOWN], ordered[MAX_SHOWN:]
    rows = [(name, size / grand * 100, COLORS[i % len(COLORS)])
            for i, (name, size) in enumerate(shown)]
    if rest:
        rows.append(("Other", sum(s for _, s in rest) / grand * 100, OTHER_COLOR))
    return rows


def render(rows):
    font = "'Segoe UI', Ubuntu, Helvetica, Arial, sans-serif"
    legend_rows = max(1, math.ceil(len(rows) / 2))
    height = 107 + (legend_rows - 1) * 30 + 33
    desc = ", ".join(f"{n} {p:.2f}%" for n, p, _ in rows) or "No language data yet"

    bars, x = [], BAR_X
    for _, pct, color in rows:
        w = pct * BAR_W / 100
        bars.append(f'    <rect x="{x:.2f}" y="62" width="{w:.2f}" height="12" fill="{color}"/>')
        x += w

    legend = []
    for i, (name, pct, color) in enumerate(rows):
        cx = 31 if i % 2 == 0 else 256
        cy = 107 + (i // 2) * 30
        legend.append(f'    <circle cx="{cx}" cy="{cy}" r="5" fill="{color}"/>')
        legend.append(f'    <text x="{cx + 14}" y="{cy + 4}">{escape(name)} {pct:.2f}%</text>')

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="495" height="{height}" viewBox="0 0 495 {height}" role="img" aria-labelledby="title desc">
  <title id="title">Most Used Languages</title>
  <desc id="desc">{escape(desc)}</desc>
  <defs>
    <clipPath id="bar">
      <rect x="{BAR_X}" y="62" width="{BAR_W}" height="12" rx="6"/>
    </clipPath>
  </defs>

  <!-- Card -->
  <rect x="0.5" y="0.5" width="494" height="{height - 1}" rx="8" fill="#ffffff" stroke="#3b5998"/>
  <rect x="0.5" y="0.5" width="494" height="6" rx="3" fill="#3b5998"/>

  <!-- Title -->
  <text x="25" y="40" font-family="{font}" font-size="18" font-weight="600" fill="#3b5998">Most Used Languages</text>

  <!-- Stacked bar -->
  <g clip-path="url(#bar)">
    <rect x="{BAR_X}" y="62" width="{BAR_W}" height="12" fill="#e9ebee"/>
{chr(10).join(bars)}
  </g>

  <!-- Legend -->
  <g font-family="{font}" font-size="13" fill="#333333">
{chr(10).join(legend)}
  </g>
</svg>
"""


def main():
    totals = collect_bytes(USER)
    rows = build_rows(totals)
    if not rows:
        sys.exit("No language data found; leaving the existing chart unchanged.")
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(render(rows))
    print("Wrote", OUT_FILE, "|", ", ".join(f"{n} {p:.2f}%" for n, p, _ in rows))


if __name__ == "__main__":
    main()
