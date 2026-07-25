#!/usr/bin/env python3
"""Builds top-languages.svg straight from the GitHub REST API.

Exists because github-readme-stats' hosted top-langs card depends on a
third-party Vercel deployment that goes down independently of GitHub, and
the lowlighter/metrics languages plugin returns an empty panel for this
account with no error to act on. Computing straight from
`GET /repos/{owner}/{repo}/languages` removes both failure points.
"""
import json
import os
import sys
import urllib.request

USERNAME = os.environ["GH_USERNAME"]
TOKEN = os.environ["GITHUB_TOKEN"]
API = "https://api.github.com"
LIMIT = 8

LANGUAGE_COLORS = {
    "PHP": "#4F5D95",
    "Blade": "#f7523f",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "Python": "#3572A5",
    "Vue": "#41b883",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "Shell": "#89e051",
    "Dockerfile": "#384d54",
    "Go": "#00ADD8",
    "Java": "#b07219",
    "Ruby": "#701516",
    "C#": "#178600",
    "C++": "#f34b7d",
    "Vue.js": "#41b883",
}
DEFAULT_COLOR = "#8b949e"


def gh_get(path, params=None):
    url = f"{API}{path}"
    if params:
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{query}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "User-Agent": USERNAME,
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def fetch_repos():
    repos, page = [], 1
    while True:
        batch = gh_get(
            f"/users/{USERNAME}/repos",
            {"type": "owner", "per_page": 100, "page": page},
        )
        if not batch:
            break
        repos.extend(r for r in batch if not r["fork"])
        page += 1
    return repos


def aggregate_languages(repos):
    totals = {}
    for repo in repos:
        try:
            langs = gh_get(f"/repos/{repo['full_name']}/languages")
        except Exception as exc:  # noqa: BLE001
            print(f"skip {repo['full_name']}: {exc}", file=sys.stderr)
            continue
        for lang, bytes_count in langs.items():
            totals[lang] = totals.get(lang, 0) + bytes_count
    return totals


def render_svg(totals):
    total_bytes = sum(totals.values()) or 1
    top = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:LIMIT]

    width, row_h, pad_top, pad_x = 340, 28, 55, 25
    height = pad_top + row_h * len(top) + 20
    bar_w = width - pad_x * 2

    rows = []
    y = pad_top
    for lang, bytes_count in top:
        pct = bytes_count / total_bytes * 100
        color = LANGUAGE_COLORS.get(lang, DEFAULT_COLOR)
        filled = bar_w * pct / 100
        rows.append(f"""
    <g transform="translate(0, {y})">
      <text x="{pad_x}" y="0" class="lang-name" fill="#c9d1d9">{lang}</text>
      <text x="{width - pad_x}" y="0" text-anchor="end" class="lang-pct" fill="#8b949e">{pct:.1f}%</text>
      <rect x="{pad_x}" y="8" width="{bar_w}" height="6" rx="3" fill="#30363d"/>
      <rect x="{pad_x}" y="8" width="{filled:.1f}" height="6" rx="3" fill="{color}"/>
    </g>""")
        y += row_h

    svg = f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" font-family="'Segoe UI', Ubuntu, sans-serif">
  <style>
    .title {{ font-size: 16px; font-weight: 600; fill: #c9d1d9; }}
    .lang-name {{ font-size: 13px; }}
    .lang-pct {{ font-size: 12px; }}
  </style>
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="4.5" fill="#0d1117" stroke="#30363d"/>
  <text x="{pad_x}" y="30" class="title">Most Used Languages</text>
  {''.join(rows)}
</svg>"""
    return svg


def main():
    repos = fetch_repos()
    totals = aggregate_languages(repos)
    if not totals:
        print("no language data found", file=sys.stderr)
        sys.exit(1)
    svg = render_svg(totals)
    with open("top-languages.svg", "w", encoding="utf-8") as fh:
        fh.write(svg)
    print(f"wrote top-languages.svg from {len(repos)} repos, {len(totals)} languages")


if __name__ == "__main__":
    main()
