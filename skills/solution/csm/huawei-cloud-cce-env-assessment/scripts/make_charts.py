#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate the radar chart and staircase chart (pure SVG) from artifacts/cloud-native-summary.xlsx.

Design notes:
- Output is SVG (XML text); Chinese text is rendered through SVG <text>, with fonts handled by the browser/viewer (no TTF file required)
- No longer depends on matplotlib, avoiding Python 3.6 + legacy numpy/matplotlib compatibility issues
- Still produces data/score_meta.json for consumption by make_report_html.py
- Also writes placeholder legacy paths radar.png/stair.png (make_report_html.py already handles SVG)
"""
import os, json, math, openpyxl, html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XLSX  = os.path.join(ROOT, "artifacts", "cloud-native-summary.xlsx")
RADAR = os.path.join(ROOT, "artifacts", "radar.svg")
STAIR = os.path.join(ROOT, "artifacts", "stair.svg")
META  = os.path.join(ROOT, "data", "score_meta.json")

# === Read Excel ===
wb = openpyxl.load_workbook(XLSX, data_only=True)
ws = wb.active
DIMS = ["服务化", "安全", "自动化", "弹性", "可观测性", "韧性"]
DIM_ALIAS = {"安全性": "安全"}
acc = {d: [0.0, 0.0] for d in DIMS}
total_score = 0.0
total_full  = 0.0
verdict_count = {"完全满足":0,"基本满足":0,"部分满足":0,"未满足":0,"不适用":0,"未评估":0}

for r in ws.iter_rows(min_row=2, values_only=True):
    if not r or r[0] is None: continue
    dim_raw = (r[1] or "").replace("\n", " ").replace("、", " ").strip()
    verdict = r[7]
    score = r[8] or 0
    full  = r[9] or 0
    verdict_count[verdict] = verdict_count.get(verdict, 0) + 1
    if verdict == "不适用":
        continue
    total_score += score
    total_full  += full
    parts = [DIM_ALIAS.get(p, p) for p in dim_raw.split() if p]
    for p in parts:
        if p in acc:
            acc[p][0] += score
            acc[p][1] += full

print("dim breakdown:")
dim_scores = []
for d in DIMS:
    s, fl = acc[d]
    score5 = (s / fl) * 5 if fl else 0
    dim_scores.append(score5)
    print(f"  {d}: {s}/{fl} = {round(score5, 2)}")
overall = (total_score / total_full) * 5 if total_full else 0
print(f"OVERALL: {total_score}/{total_full} = {round(overall, 2)} (5-scale)")
print("verdict counts:", verdict_count)

# === SVG Utilities ===
SVG_FONT = '-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei","Noto Sans CJK SC","WenQuanYi Micro Hei",sans-serif'

def esc(s): return html.escape(str(s))

def svg_open(width, height, title=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="100%" preserveAspectRatio="xMidYMid meet" font-family=\'{SVG_FONT}\'>\n'
        f'  <title>{esc(title)}</title>\n'
        f'  <rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"/>\n'
    )

def svg_close(): return "</svg>\n"


# === Radar Chart (SVG) ===
def render_radar(dims, values, overall_score, out_path):
    W, H = 560, 560
    cx, cy = W/2, H/2 + 12
    R = 200
    N = len(dims)
    max_val = 5
    rings = 5  # 1..5 concentric circles

    out = [svg_open(W, H, f"Cloud-native Maturity Radar (Overall {round(overall_score,2)}/5)")]
    # Title
    out.append(f'  <text x="{W/2}" y="32" text-anchor="middle" font-size="18" font-weight="700" fill="#1F4E78">'
               f'Cloud-native Maturity Radar (Score {round(overall_score,2)}/5)</text>\n')

    # Concentric polygons (background scale)
    for ring in range(1, rings+1):
        r = R * ring / rings
        pts = []
        for i in range(N):
            a = -math.pi/2 + i * 2*math.pi/N
            pts.append(f"{cx + r*math.cos(a):.1f},{cy + r*math.sin(a):.1f}")
        out.append(f'  <polygon points="{" ".join(pts)}" fill="none" stroke="#dfe3e8" stroke-width="1"/>\n')

    # Axis lines (from center to vertices)
    axis_pts = []
    for i in range(N):
        a = -math.pi/2 + i * 2*math.pi/N
        x = cx + R*math.cos(a)
        y = cy + R*math.sin(a)
        axis_pts.append((a, x, y))
        out.append(f'  <line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="#c8ced6" stroke-width="1"/>\n')

    # Scale numbers (1~5 along the rightmost axis)
    for ring in range(1, rings+1):
        r = R * ring / rings
        out.append(f'  <text x="{cx + r + 4}" y="{cy + 4}" font-size="10" fill="#888">{ring}</text>\n')

    # Data polygon
    data_pts = []
    for i, v in enumerate(values):
        a = -math.pi/2 + i * 2*math.pi/N
        r = R * (v / max_val)
        data_pts.append((cx + r*math.cos(a), cy + r*math.sin(a)))
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in data_pts)
    out.append(f'  <polygon points="{poly}" fill="#2E86AB" fill-opacity="0.28" stroke="#2E86AB" stroke-width="2"/>\n')
    # Data points
    for (x, y) in data_pts:
        out.append(f'  <circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#2E86AB"/>\n')

    # Dimension labels + values
    for i, (dim, val) in enumerate(zip(dims, values)):
        a = -math.pi/2 + i * 2*math.pi/N
        lx = cx + (R + 28) * math.cos(a)
        ly = cy + (R + 28) * math.sin(a)
        # Adjust text anchor based on quadrant
        cos_a = math.cos(a)
        if cos_a > 0.3:   anchor = "start"
        elif cos_a < -0.3: anchor = "end"
        else:             anchor = "middle"
        out.append(f'  <text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" '
                   f'dominant-baseline="middle" font-size="14" font-weight="600" fill="#333">{esc(dim)}</text>\n')
        # Value (right below dimension name)
        out.append(f'  <text x="{lx:.1f}" y="{ly + 16:.1f}" text-anchor="{anchor}" '
                   f'font-size="12" font-weight="700" fill="#A23B72">{round(val,2)}</text>\n')

    out.append(svg_close())
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("".join(out))

render_radar(DIMS, dim_scores, overall, RADAR)
print(f"radar saved: {RADAR}")


# === Stair Chart (SVG) ===
def render_stair(overall_score, out_path):
    W, H = 880, 440
    PAD_L, PAD_R, PAD_T, PAD_B = 60, 40, 60, 80
    inner_w = W - PAD_L - PAD_R
    inner_h = H - PAD_T - PAD_B

    stages = [
        ("传统化",    "≤1", 1),
        ("基础云化",  "1~2", 2),
        ("服务化",    "2~3", 3),
        ("自动化",    "3~4", 4),
        ("智能化",    ">4",  5),
    ]
    n = len(stages)
    bar_gap = 4
    bar_w = (inner_w - bar_gap * (n - 1)) / n

    # Current stage
    if overall_score <= 1:   cur = 0
    elif overall_score <= 2: cur = 1
    elif overall_score <= 3: cur = 2
    elif overall_score <= 4: cur = 3
    else:                    cur = 4

    out = [svg_open(W, H, f"Cloud-native Maturity Stair Chart")]
    out.append(f'  <text x="{W/2}" y="32" text-anchor="middle" font-size="18" font-weight="700" fill="#1F4E78">'
               f'Cloud-native Maturity Stair Chart</text>\n')

    # Y axis
    out.append(f'  <line x1="{PAD_L}" y1="{PAD_T}" x2="{PAD_L}" y2="{PAD_T+inner_h}" stroke="#888" stroke-width="1"/>\n')
    # Y axis ticks (0..5)
    for v in range(0, 6):
        y = PAD_T + inner_h * (1 - v/5)
        out.append(f'  <line x1="{PAD_L-4}" y1="{y:.1f}" x2="{PAD_L}" y2="{y:.1f}" stroke="#888"/>\n')
        out.append(f'  <text x="{PAD_L-8}" y="{y+4:.1f}" text-anchor="end" font-size="11" fill="#555">{v}</text>\n')
    # Y axis title
    out.append(f'  <text x="{PAD_L-44}" y="{PAD_T+inner_h/2:.1f}" text-anchor="middle" font-size="12" fill="#444" '
               f'transform="rotate(-90, {PAD_L-44}, {PAD_T+inner_h/2:.1f})">Maturity Score (5-point scale)</text>\n')

    # Stair bars
    for i, (name, rng, h) in enumerate(stages):
        x = PAD_L + i * (bar_w + bar_gap)
        bar_h = inner_h * (h / 5)
        y = PAD_T + inner_h - bar_h
        is_cur = (i == cur)
        fill = "#F18F01" if is_cur else "#cccccc"
        stroke = "#A23B72" if is_cur else "#888"
        sw = 2 if is_cur else 1
        out.append(f'  <rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" '
                   f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" rx="2"/>\n')
        # Stage name + range (above bar top)
        weight = "700" if is_cur else "400"
        color  = "#1F4E78" if is_cur else "#333"
        out.append(f'  <text x="{x + bar_w/2:.1f}" y="{y - 8:.1f}" text-anchor="middle" font-size="13" '
                   f'font-weight="{weight}" fill="{color}">{esc(name)}</text>\n')
        out.append(f'  <text x="{x + bar_w/2:.1f}" y="{y - 24:.1f}" text-anchor="middle" font-size="11" fill="#888">'
                   f'({esc(rng)})</text>\n')
        # Stage number (below bar bottom)
        out.append(f'  <text x="{x + bar_w/2:.1f}" y="{PAD_T + inner_h + 24:.1f}" text-anchor="middle" font-size="13" fill="#555">'
                   f'L{i+1}</text>\n')

    # Current score horizontal line
    score_y = PAD_T + inner_h * (1 - overall_score/5)
    out.append(f'  <line x1="{PAD_L}" y1="{score_y:.1f}" x2="{PAD_L+inner_w}" y2="{score_y:.1f}" '
               f'stroke="#A23B72" stroke-width="2" stroke-dasharray="6,4"/>\n')
    out.append(f'  <text x="{PAD_L+inner_w-6:.1f}" y="{score_y-6:.1f}" text-anchor="end" '
               f'font-size="14" font-weight="700" fill="#A23B72">Current {round(overall_score,2)} pts</text>\n')

    out.append(svg_close())
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("".join(out))

render_stair(overall, STAIR)
print(f"stair saved: {STAIR}")

# === Output score_meta.json (for make_report_html.py consumption) ===
stage_names = ["传统化", "基础云化", "服务化", "自动化", "智能化"]
if overall <= 1:   cur = 0
elif overall <= 2: cur = 1
elif overall <= 3: cur = 2
elif overall <= 4: cur = 3
else:              cur = 4

with open(META, "w", encoding="utf-8") as f:
    json.dump({
        "overall": round(overall, 2),
        "total_score": int(total_score),
        "total_full": int(total_full),
        "dim_scores": {d: round(v, 2) for d, v in zip(DIMS, dim_scores)},
        "verdict_count": verdict_count,
        "stage": stage_names[cur],
    }, f, ensure_ascii=False, indent=2)
print(f"meta saved: {META}")
