#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate dark-themed GitHub stats card + contribution calendar SVGs from live data.
Run by .github/workflows/update-stats.yml on a schedule. No external deps."""
import os, re, json, html, urllib.request

USER = os.environ.get("GH_USER", "BISWAJIT822")
TOKEN = os.environ.get("GH_TOKEN", "")

API_HEADERS = {"User-Agent": "readme-stats-bot", "Accept": "application/vnd.github+json"}
if TOKEN:
    API_HEADERS["Authorization"] = "Bearer " + TOKEN
WEB_HEADERS = {"User-Agent": "Mozilla/5.0"}

def get_json(url):
    req = urllib.request.Request(url, headers=API_HEADERS)
    return json.load(urllib.request.urlopen(req, timeout=30))

def get_text(url, headers):
    req = urllib.request.Request(url, headers=headers)
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")

# ---------------- fetch data ----------------
user = get_json(f"https://api.github.com/users/{USER}")
public_repos = user.get("public_repos", 0)
created = (user.get("created_at") or "2021-01-01")[:7]  # YYYY-MM

MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
since = f"{MONTHS[int(created[5:7])-1]} {created[:4]}"

# languages
totals = {}
page = 1
while True:
    repos = get_json(f"https://api.github.com/users/{USER}/repos?per_page=100&page={page}&type=owner")
    if not repos:
        break
    for rp in repos:
        if rp.get("fork"):
            continue
        try:
            langs = get_json(rp["languages_url"])
        except Exception:
            langs = {}
        for k, v in langs.items():
            totals[k] = totals.get(k, 0) + v
    if len(repos) < 100:
        break
    page += 1
lang_sum = sum(totals.values()) or 1
top_langs = sorted(totals.items(), key=lambda x: -x[1])[:5]

# contributions calendar
chtml = get_text(f"https://github.com/users/{USER}/contributions", WEB_HEADERS)
m = re.search(r'([\d,]+)\s+cont(?:ribution)?', chtml)
total_contrib = int(m.group(1).replace(",", "")) if m else 0
cells = re.findall(r'<td[^>]*id="contribution-day-component-(\d+)-(\d+)"[^>]*data-level="(\d+)"', chtml)
date_map = {}
for mm in re.finditer(r'data-date="([^"]+)"[^>]*id="contribution-day-component-(\d+)-(\d+)"', chtml):
    date_map[(int(mm.group(3)), int(mm.group(2)))] = mm.group(1)  # (col,row)->date
grid, maxcol = {}, 0
seq = []  # (date, level) ordered
for a, b, lvl in cells:
    row, col, lvl = int(a), int(b), int(lvl)
    grid[(col, row)] = lvl
    maxcol = max(maxcol, col)
for (col, row), d in date_map.items():
    if (col, row) in grid:
        seq.append((d, grid[(col, row)]))
seq.sort()
# streaks (active day = level > 0)
longest = cur = run = 0
for _, lvl in seq:
    if lvl > 0:
        run += 1; longest = max(longest, run)
    else:
        run = 0
# current streak = trailing active run
for _, lvl in reversed(seq):
    if lvl > 0:
        cur += 1
    else:
        break

# ---------------- language colors ----------------
LC = {
    "Python": "#3572A5", "JavaScript": "#f1e05a", "TypeScript": "#3178c6",
    "HTML": "#e34c26", "CSS": "#a371f7", "Java": "#e07a2c", "C": "#8a9199",
    "C++": "#f34b7d", "Kotlin": "#A97BFF", "PHP": "#4F5D95", "Shell": "#89e051",
    "PowerShell": "#4ea1d3", "Dart": "#00B4AB", "Go": "#00ADD8", "Ruby": "#cc3e44",
    "Jupyter Notebook": "#DA5B0B", "Vue": "#41b883", "Swift": "#F05138",
    "Rust": "#dea584", "Go Template": "#00ADD8", "Batchfile": "#C1F12E",
}

# ================= build stats card SVG =================
def stats_svg():
    W, H = 720, 346
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
         f'font-family="\'Segoe UI\',\'Helvetica Neue\',Arial,sans-serif">']
    def panel(x, y, w, h):
        s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="13" fill="#0f1621" stroke="#1e2735"/>')
    def text(x, y, t, sz, fill, w="400", anc="start"):
        s.append(f'<text x="{x}" y="{y}" font-size="{sz}" font-weight="{w}" fill="{fill}" text-anchor="{anc}">{html.escape(str(t))}</text>')
    PAD, GAP = 16, 14
    inner = W - PAD*2
    top_y, top_h = 14, 96
    pw = (inner - GAP*2) / 3
    x1 = PAD; x2 = x1+pw+GAP; x3 = x2+pw+GAP
    # panel 1 repos
    panel(x1, top_y, pw, top_h); cx1 = x1+pw/2
    s.append(f'<g transform="translate({x1+20},{top_y+22})" fill="none" stroke="#58a6ff" stroke-width="1.8">'
             f'<rect x="0" y="0" width="16" height="19" rx="2.5"/><path d="M0 14 H16" stroke-opacity="0.5"/><path d="M4 4 H12"/></g>')
    text(x1+46, top_y+22, "Total", 11.5, "#7d8894"); text(x1+46, top_y+37, "Repositories", 11.5, "#7d8894")
    text(cx1, top_y+78, public_repos, 34, "#58a6ff", "800", "middle")
    # panel 2 contributions
    panel(x2, top_y, pw, top_h); cx2 = x2+pw/2
    s.append(f'<g transform="translate({x2+20},{top_y+20})" fill="#3fb950">'
             f'<path d="M11 0 L13.4 8.2 L21.5 8.2 L15 13.2 L17.3 21 L11 16.2 L4.7 21 L7 13.2 L0.5 8.2 L8.6 8.2 Z"/></g>')
    text(x2+48, top_y+22, "Total", 11.5, "#7d8894"); text(x2+48, top_y+37, "Contributions", 11.5, "#7d8894")
    text(cx2, top_y+78, total_contrib, 34, "#3fb950", "800", "middle")
    # panel 3 graph
    panel(x3, top_y, pw, top_h)
    text(x3+18, top_y+24, "Contributions", 11.5, "#7d8894")
    pat = ["00112233","01223321","12332100","23321012","11223301"]
    greens = {"0":"#161b22","1":"#0e4429","2":"#26a641","3":"#39d353"}
    gx, gy, sz, gp = x3+18, top_y+36, 8.5, 4
    for r, row in enumerate(pat):
        for c, ch in enumerate(row):
            s.append(f'<rect x="{gx+c*(sz+gp):.1f}" y="{gy+r*(sz+gp):.1f}" width="{sz}" height="{sz}" rx="2" fill="{greens[ch]}"/>')
    # bottom
    bot_y = top_y+top_h+GAP; bot_h = H-bot_y-PAD
    lw = 428; rx_ = PAD+lw+GAP; rw = W-PAD-rx_
    panel(PAD, bot_y, lw, bot_h)
    text(PAD+22, bot_y+30, "Most Used Languages", 15, "#e6edf3", "700")
    row_y = bot_y+58; row_gap = (bot_h-58-12)/max(1,len(top_langs))
    bar_x = PAD+118; bar_w = 232
    for name, val in top_langs:
        pct = 100*val/lang_sum
        col = LC.get(name, "#8b949e")
        text(PAD+22, row_y+4, name, 12.5, "#c9d1d9", "500")
        s.append(f'<rect x="{bar_x}" y="{row_y-6}" width="{bar_w}" height="9" rx="4.5" fill="#21262d"/>')
        s.append(f'<rect x="{bar_x}" y="{row_y-6}" width="{max(5, bar_w*pct/100):.1f}" height="9" rx="4.5" fill="{col}"/>')
        text(bar_x+bar_w+34, row_y+4, f"{pct:.1f}%", 12, "#8b949e", "400", "end")
        row_y += row_gap
    panel(rx_, bot_y, rw, bot_h); rcx = rx_+rw/2
    s.append(f'<g transform="translate({rx_+20},{bot_y+16})">'
             f'<path d="M8 0 C10 4 13 5 13 9.5 C13 13 10.8 15 8 15 C5.2 15 3 13 3 9.7 C3 7.5 4.2 6.2 5.2 7.2 C5 4.5 6 2.2 8 0 Z" fill="#ff8c42"/></g>')
    text(rx_+42, bot_y+30, "GitHub Streak", 15, "#e6edf3", "700")
    text(rcx, bot_y+64, "Keep Going!", 13, "#8b949e", "400", "middle")
    text(rcx, bot_y+120, longest, 52, "#ff8c42", "800", "middle")
    text(rcx, bot_y+146, "Longest Streak (days)", 12, "#c9d1d9", "600", "middle")
    text(rcx, bot_y+172, f"Current: {cur}  ·  Since {since}", 11, "#7d8894", "400", "middle")
    s.append('</svg>')
    return "\n".join(s)

# ================= build contribution calendar SVG =================
def contrib_svg():
    CELL, GAP = 11, 3
    STEP = CELL+GAP
    LEFT, TOP, PADX, PADB = 30, 22, 16, 30
    ncols = maxcol+1
    Wc = LEFT+ncols*STEP+8
    W = PADX*2+Wc
    Hh = TOP+7*STEP+PADB+8
    COL = ["#161b22","#0e4429","#006d32","#26a641","#39d353"]
    TXT = "#8b949e"
    gx0 = PADX+LEFT; gy0 = TOP+6
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{Hh}" viewBox="0 0 {W} {Hh}" font-family="\'Segoe UI\',Arial,sans-serif">']
    s.append(f'<rect x="1" y="1" width="{W-2}" height="{Hh-2}" rx="14" fill="#0d1117" stroke="#20293a"/>')
    prev_m = None
    for col in range(ncols):
        d = None
        for row in range(7):
            if (col, row) in date_map: d = date_map[(col, row)]; break
        if not d: continue
        mth = int(d.split('-')[1])
        if mth != prev_m:
            s.append(f'<text x="{gx0+col*STEP}" y="{TOP-6}" font-size="11" fill="{TXT}">{MONTHS[mth-1]}</text>')
            prev_m = mth
    for row, lab in [(1,"Mon"),(3,"Wed"),(5,"Fri")]:
        s.append(f'<text x="{PADX}" y="{gy0+row*STEP+CELL-1}" font-size="10" fill="{TXT}">{lab}</text>')
    for col in range(ncols):
        for row in range(7):
            if (col, row) not in grid: continue
            s.append(f'<rect x="{gx0+col*STEP}" y="{gy0+row*STEP}" width="{CELL}" height="{CELL}" rx="2.5" fill="{COL[grid[(col,row)]]}"/>')
    ly = Hh-16; lx = W-PADX-(5*(CELL+3)+80)
    s.append(f'<text x="{PADX}" y="{ly}" font-size="10.5" fill="{TXT}">Contribution Graph</text>')
    s.append(f'<text x="{lx}" y="{ly}" font-size="10.5" fill="{TXT}">Less</text>')
    for i in range(5):
        s.append(f'<rect x="{lx+30+i*(CELL+3)}" y="{ly-9}" width="{CELL}" height="{CELL}" rx="2.5" fill="{COL[i]}"/>')
    s.append(f'<text x="{lx+30+5*(CELL+3)+4}" y="{ly}" font-size="10.5" fill="{TXT}">More</text>')
    s.append('</svg>')
    return "\n".join(s)

os.makedirs("assets", exist_ok=True)
open("assets/github-stats.svg", "w", encoding="utf-8").write(stats_svg())
open("assets/contributions.svg", "w", encoding="utf-8").write(contrib_svg())
print(f"Done. repos={public_repos} contrib={total_contrib} longest={longest} current={cur} langs={[l[0] for l in top_langs]}")
