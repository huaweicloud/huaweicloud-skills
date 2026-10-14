#!/usr/bin/env python3
"""generate_cover.py — 可复用的作品封面生成器

功能：读取应用截图，合成 PPT 风格的 1280×720 封面 PNG。
      内置多种色调方案与布局模板，支持自定义标题和副标题。
      使用 Playwright 渲染 HTML → PNG，自动处理 CJK 字体。

用法:
  python generate_cover.py --screenshot <path> --title <name> --out <path> \
      [--tagline <text>] [--description <text>] [--scheme <name>] [--layout <name>]

选项:
  --screenshot <path>   应用截图 PNG 路径（必填）
  --title <text>        作品名称（必填）
  --out <path>          输出封面 PNG 路径（必填）
  --tagline <text>      副标题（可选）
  --description <text>  主体介绍文字（1~3 句，可选）
  --scheme <name>       色调：auto(默认,按页面主色/标题哈希) / purple / blue / green / dark / warm / black-gold / vibrant-orange / warm-yellow / aurora / cyan-ink / rose-gold / mono
  --layout <name>       布局：auto(默认) / classic / split / hero / showcase / polaroid / blur / topbar / spotlight / cinema / blueprint / diorama / glass / collage-h / collage-v / collage-grid
  -h, --help            显示本帮助

退出码: 0=成功; 1=运行时错误; 2=参数错误
"""

import argparse
import base64
import sys
import zlib
from io import BytesIO
from pathlib import Path
from html import escape

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

SCHEMES = {
    "purple": {
        "bg": "linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%)",
        "glow": "rgba(99,102,241,0.15)",
        "titleShadow": "rgba(99,102,241,0.6)",
        "badgeBg": "rgba(99,102,241,0.3)",
        "badgeBorder": "rgba(99,102,241,0.5)",
        "badgeColor": "#a5b4fc",
        "gridColor": "rgba(99,102,241,0.08)",
        "frameShadow": "rgba(99,102,241,0.2)",
    },
    "blue": {
        "bg": "linear-gradient(135deg, #0c1929 0%, #1a3a5c 50%, #0f2444 100%)",
        "glow": "rgba(59,130,246,0.15)",
        "titleShadow": "rgba(59,130,246,0.6)",
        "badgeBg": "rgba(59,130,246,0.3)",
        "badgeBorder": "rgba(59,130,246,0.5)",
        "badgeColor": "#93c5fd",
        "gridColor": "rgba(59,130,246,0.08)",
        "frameShadow": "rgba(59,130,246,0.2)",
    },
    "green": {
        "bg": "linear-gradient(135deg, #0a1f0c 0%, #1a3a2e 50%, #0f2818 100%)",
        "glow": "rgba(34,197,94,0.15)",
        "titleShadow": "rgba(34,197,94,0.6)",
        "badgeBg": "rgba(34,197,94,0.3)",
        "badgeBorder": "rgba(34,197,94,0.5)",
        "badgeColor": "#86efac",
        "gridColor": "rgba(34,197,94,0.08)",
        "frameShadow": "rgba(34,197,94,0.2)",
    },
    "dark": {
        "bg": "linear-gradient(135deg, #0b1026 0%, #131c3b 50%, #0d1429 100%)",
        "glow": "rgba(120,150,220,0.16)",
        "titleShadow": "rgba(120,150,220,0.45)",
        "badgeBg": "rgba(120,150,220,0.18)",
        "badgeBorder": "rgba(120,150,220,0.35)",
        "badgeColor": "#b8c7ea",
        "gridColor": "rgba(120,150,220,0.08)",
        "frameShadow": "rgba(120,150,220,0.15)",
    },
    "warm": {
        "bg": "linear-gradient(135deg, #1a0f0c 0%, #3a2018 50%, #2a1810 100%)",
        "glow": "rgba(251,146,60,0.15)",
        "titleShadow": "rgba(251,146,60,0.6)",
        "badgeBg": "rgba(251,146,60,0.3)",
        "badgeBorder": "rgba(251,146,60,0.5)",
        "badgeColor": "#fdba74",
        "gridColor": "rgba(251,146,60,0.08)",
        "frameShadow": "rgba(251,146,60,0.2)",
    },
    "black-gold": {
        "bg": "linear-gradient(135deg, #050505 0%, #1c1a14 50%, #2a2416 100%)",
        "glow": "rgba(212,175,55,0.16)",
        "titleShadow": "rgba(212,175,55,0.6)",
        "badgeBg": "rgba(212,175,55,0.3)",
        "badgeBorder": "rgba(212,175,55,0.5)",
        "badgeColor": "#f0cf6d",
        "gridColor": "rgba(212,175,55,0.09)",
        "frameShadow": "rgba(212,175,55,0.22)",
    },
    "vibrant-orange": {
        "bg": "linear-gradient(135deg, #1a0a02 0%, #7a3410 50%, #b45309 100%)",
        "glow": "rgba(249,115,22,0.18)",
        "titleShadow": "rgba(249,115,22,0.6)",
        "badgeBg": "rgba(249,115,22,0.3)",
        "badgeBorder": "rgba(249,115,22,0.5)",
        "badgeColor": "#fdba74",
        "gridColor": "rgba(249,115,22,0.09)",
        "frameShadow": "rgba(249,115,22,0.22)",
    },
    "warm-yellow": {
        "bg": "linear-gradient(135deg, #1a1202 0%, #573e0a 50%, #7c5d10 100%)",
        "glow": "rgba(245,158,11,0.18)",
        "titleShadow": "rgba(245,158,11,0.6)",
        "badgeBg": "rgba(245,158,11,0.3)",
        "badgeBorder": "rgba(245,158,11,0.5)",
        "badgeColor": "#fcd34d",
        "gridColor": "rgba(245,158,11,0.09)",
        "frameShadow": "rgba(245,158,11,0.22)",
    },
    "aurora": {
        "bg": "linear-gradient(135deg, #04122e 0%, #124a6b 40%, #2a3a8c 70%, #7a2a6a 100%)",
        "glow": "rgba(56,189,248,0.22)",
        "titleShadow": "rgba(103,232,249,0.65)",
        "badgeBg": "rgba(56,189,248,0.28)",
        "badgeBorder": "rgba(103,232,249,0.55)",
        "badgeColor": "#a5f3fc",
        "gridColor": "rgba(103,232,249,0.10)",
        "frameShadow": "rgba(103,232,249,0.25)",
    },
    "cyan-ink": {
        "bg": "linear-gradient(150deg, #0b1a20 0%, #14323b 55%, #1e4b57 100%)",
        "glow": "rgba(94,234,212,0.16)",
        "titleShadow": "rgba(94,234,212,0.55)",
        "badgeBg": "rgba(94,234,212,0.22)",
        "badgeBorder": "rgba(94,234,212,0.45)",
        "badgeColor": "#99f6e4",
        "gridColor": "rgba(94,234,212,0.08)",
        "frameShadow": "rgba(94,234,212,0.18)",
    },
    "rose-gold": {
        "bg": "linear-gradient(135deg, #1a0a10 0%, #3d1726 45%, #6b2437 80%, #8f3d52 100%)",
        "glow": "rgba(251,113,133,0.20)",
        "titleShadow": "rgba(253,164,175,0.65)",
        "badgeBg": "rgba(251,113,133,0.28)",
        "badgeBorder": "rgba(253,164,175,0.5)",
        "badgeColor": "#fecdd3",
        "gridColor": "rgba(253,164,175,0.10)",
        "frameShadow": "rgba(253,164,175,0.25)",
    },
    "mono": {
        "bg": "linear-gradient(135deg, #0a0a0a 0%, #1f1f1f 50%, #333333 100%)",
        "glow": "rgba(255,255,255,0.10)",
        "titleShadow": "rgba(255,255,255,0.5)",
        "badgeBg": "rgba(255,255,255,0.16)",
        "badgeBorder": "rgba(255,255,255,0.35)",
        "badgeColor": "#e5e5e5",
        "gridColor": "rgba(255,255,255,0.07)",
        "frameShadow": "rgba(0,0,0,0.45)",
    },
}

LAYOUTS = ["auto", "classic", "split", "hero", "showcase", "polaroid", "blur", "topbar",
           "spotlight", "cinema", "blueprint", "diorama", "glass",
           "collage-h", "collage-v", "collage-grid"]
_AUTO_OPTIONS = ["classic", "split", "hero", "showcase", "polaroid", "blur", "topbar",
                 "spotlight", "cinema", "blueprint", "diorama", "glass"]
MULTI_SHOT_OPTIONS = ["collage-h", "collage-v", "collage-grid"]
SCHEME_CHOICES = ["auto"] + list(SCHEMES.keys())

# 公共特效 CSS（注入到所有布局 </style> 前）：标题描边+分层投影 + 光泽斜扫高光。
# 纯静态实现（无动画），保证 verify-glyphs 像素判定稳定；shine 覆盖在标题文字之上
# 用半透明白斜带，中心墨密度影响微弱，已在布局矩阵回归中验证不误判。
COMMON_FX_CSS = """
  /* ===== 公共特效：标题描边 + 分层投影 ===== */
  .title {
    -webkit-text-stroke: 1px rgba(255,255,255,0.16);
    paint-order: stroke fill;
  }
  .title::after {
    content: none; /* 预留 */
  }
  /* ===== 公共特效：光泽斜扫高光（静态） ===== */
  .hb-shine {
    position: absolute; top: 0; left: -30%; width: 30%; height: 100%;
    background: linear-gradient(105deg, transparent 0%, rgba(255,255,255,0.16) 45%, rgba(255,255,255,0.30) 50%, rgba(255,255,255,0.16) 55%, transparent 100%);
    transform: skewX(-12deg);
    pointer-events: none;
    z-index: 10;
  }
  body { overflow: hidden; }
</style>"""


def inject_common_fx(html):
    """在 </style> 前注入公共特效 CSS，并对 body 追加光泽层。"""
    if "</style>" not in html:
        return html
    html = html.replace("</style>", COMMON_FX_CSS, 1)
    # 光泽层：追加在 body 起始处，绝对定位不干扰布局
    html = html.replace("<body>", '<body><div class="hb-shine"></div>', 1)
    return html


def _pick_layout(layout_arg, title):
    if layout_arg != "auto":
        return layout_arg
    return _AUTO_OPTIONS[zlib.crc32(title.encode("utf-8")) % len(_AUTO_OPTIONS)]


def _hex_to_hue(hex_color):
    """'#rrggbb' → 色相角（0~360）；灰阶（r==g==b）返回 None。"""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return None
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    if r == g == b:
        return None
    mx, mn = max(r, g, b), min(r, g, b)
    if mx == r:
        hue = 60 * ((g - b) / (mx - mn) % 6)
    elif mx == g:
        hue = 60 * ((b - r) / (mx - mn) + 2)
    else:
        hue = 60 * ((r - g) / (mx - mn) + 4)
    return hue % 360


def _hue_dist(a, b):
    d = abs(a - b)
    return d if d <= 180 else 360 - d


def _extract_dominant_hue(png_path):
    """从截图提取主导色相（0~360）。
    只统计高饱和/非纯黑白的像素（页面白底/黑底不算主色）；无明显主色返回 None。"""
    try:
        from PIL import Image
    except Exception:
        return None
    try:
        img = Image.open(png_path).convert("RGB")
        img.thumbnail((80, 80))  # 足够小，速度快
        pixels = list(img.getdata())
    except Exception:
        return None
    bucket_cnt = [0] * 12
    bucket_sum = [0.0] * 12
    colored = 0
    for r, g, b in pixels:
        mx, mn = max(r, g, b), min(r, g, b)
        if mx == mn:
            continue  # 灰度 → 无主色
        sat = 0 if mx == 0 else (mx - mn) / mx
        val = mx / 255.0
        if sat < 0.30 or val < 0.15 or val > 0.95:
            continue  # 灰白/近黑背景不参与
        hue = _hex_to_hue("#%02x%02x%02x" % (r, g, b))
        if hue is None:
            continue
        idx = int(hue // 30) % 12
        bucket_cnt[idx] += 1
        bucket_sum[idx] += hue
        colored += 1
    if colored < len(pixels) * 0.02:
        return None  # 彩色像素占比过低 → 无主导色
    best = max(range(12), key=lambda i: bucket_cnt[i])
    return bucket_sum[best] / bucket_cnt[best]


def _pick_scheme(scheme_arg, title, screenshot_path=None):
    """--scheme auto 时优先按截图主导色就近匹配预置主题；
    无截图主色（灰/白页面或 PIL 缺失）→ 回退标题哈希，避免所有封面清一色同一色调。"""
    if scheme_arg != "auto":
        return scheme_arg
    if screenshot_path and Path(screenshot_path).exists():
        hue = _extract_dominant_hue(str(screenshot_path))
        if hue is not None:
            best_name, best_d = None, 361.0
            for name, meta in SCHEMES.items():
                base_h = _hex_to_hue(meta["badgeColor"])
                if base_h is None:
                    continue
                d = _hue_dist(hue, base_h)
                if d < best_d:
                    best_d, best_name = d, name
            if best_name:
                return best_name
    return list(SCHEMES.keys())[zlib.crc32(title.encode("utf-8")) % len(SCHEMES)]


def build_classic(s, title_html, tagline_html, desc_html, screenshot_b64, tags_html=''):
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: 1280px; height: 720px;
    background: {s['bg']};
    font-family: 'Noto Sans CJK SC', 'Microsoft YaHei', sans-serif;
    overflow: hidden;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    position: relative; padding: 30px 0;
  }}
  body::before {{
    content: ''; position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background-image:
      linear-gradient({s['gridColor']} 1px, transparent 1px),
      linear-gradient(90deg, {s['gridColor']} 1px, transparent 1px);
    background-size: 40px 40px; pointer-events: none;
  }}
  body::after {{
    content: ''; position: absolute; top: 50%; left: 50%;
    transform: translate(-50%, -50%); width: 600px; height: 600px;
    background: radial-gradient(circle, {s['glow']} 0%, transparent 70%);
    pointer-events: none;
  }}
  .title-area {{ text-align: center; margin-bottom: 22px; z-index: 2; }}
  .title {{
    font-size: 52px; font-weight: 800; color: #fff;
    text-shadow: 0 0 20px {s['titleShadow']}, 0 0 40px {s['titleShadow']};
    letter-spacing: 2px;
  }}
  .tagline {{
    font-size: 18px; color: rgba(255,255,255,0.62);
    margin-top: 8px; letter-spacing: 1px;
  }}
  .desc {{
    font-size: 17px; color: rgba(255,255,255,0.78);
    margin-top: 16px; letter-spacing: 0.5px; line-height: 1.7;
    max-width: 920px; margin-left: auto; margin-right: auto;
  }}
  .screenshot-frame {{
    z-index: 2; border-radius: 12px; overflow: hidden;
    box-shadow: 0 20px 60px rgba(0,0,0,0.5), 0 0 30px {s['frameShadow']};
    border: 1px solid rgba(255,255,255,0.1);
  }}
  .screenshot-frame img {{
    display: block; width: 860px; height: auto; object-fit: contain;
  }}
  .badge {{
    position: absolute; top: 26px; right: 36px;
    background: {s['badgeBg']}; border: 1px solid {s['badgeBorder']};
    color: {s['badgeColor']}; padding: 6px 16px; border-radius: 20px;
    font-size: 14px; z-index: 3; backdrop-filter: blur(10px);
  }}

  .tags {{
    display: inline-flex; flex-wrap: wrap; gap: 10px; margin-top: 16px;
  }}
  .tag {{
    background: {s['badgeBg']}; border: 1px solid {s['badgeBorder']};
    color: {s['badgeColor']}; padding: 4px 14px; border-radius: 20px;
    font-size: 13px; font-weight: 600; letter-spacing: 0.5px;
    backdrop-filter: blur(6px);
  }}
</style>
</head>
<body>
  <div class="badge">Huawei Cloud Gallery</div>
  <div class="title-area">
    <div class="title">{title_html}</div>
    {tagline_html}
    {tags_html}
    {desc_html}
  </div>
  <div class="screenshot-frame">
    <img src="data:image/png;base64,{screenshot_b64}" alt="Screenshot">
  </div>
</body>
</html>"""


def build_split(s, title_html, tagline_html, desc_html, screenshot_b64, tags_html=''):
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: 1280px; height: 720px;
    background: {s['bg']};
    font-family: 'Noto Sans CJK SC', 'Microsoft YaHei', sans-serif;
    overflow: hidden; position: relative;
    display: flex; flex-direction: row;
  }}
  body::before {{
    content: ''; position: absolute; inset: 0;
    background-image: radial-gradient(circle, {s['gridColor']} 1.5px, transparent 1.5px);
    background-size: 30px 30px; pointer-events: none;
  }}
  body::after {{
    content: ''; position: absolute; top: 50%; right: 25%;
    transform: translate(0, -50%); width: 520px; height: 520px;
    background: radial-gradient(circle, {s['glow']} 0%, transparent 70%);
    pointer-events: none;
  }}
  .accent {{
    width: 6px; height: 100%; background: {s['badgeColor']};
    box-shadow: 0 0 20px {s['titleShadow']}; z-index: 3; flex-shrink: 0;
  }}
  .left {{
    width: 640px; padding: 48px 44px; display: flex; flex-direction: column;
    justify-content: center; z-index: 2; position: relative;
    background: linear-gradient(135deg, rgba(0,0,0,0.55), rgba(0,0,0,0.35));
  }}
  .badge {{
    align-self: flex-start; background: {s['badgeBg']}; border: 1px solid {s['badgeBorder']};
    color: {s['badgeColor']}; padding: 6px 16px; border-radius: 20px;
    font-size: 13px; margin-bottom: 28px; backdrop-filter: blur(10px);
  }}
  .title {{
    font-size: 48px; font-weight: 800; color: #fff; line-height: 1.2;
    text-shadow: 0 0 20px {s['titleShadow']}, 0 0 40px {s['titleShadow']};
    letter-spacing: 2px;
  }}
  .tagline {{
    font-size: 18px; color: rgba(255,255,255,0.62);
    margin-top: 10px; letter-spacing: 1px;
  }}
  .desc {{
    font-size: 16px; color: rgba(255,255,255,0.78);
    margin-top: 18px; letter-spacing: 0.5px; line-height: 1.75;
    border-left: 3px solid {s['badgeColor']}; padding-left: 14px;
  }}
  .right {{
    flex: 1; display: flex; align-items: center; justify-content: center; z-index: 2;
    min-width: 0; overflow: hidden;
  }}
  .screenshot-frame {{
    border-radius: 12px; overflow: hidden;
    box-shadow: 0 20px 60px rgba(0,0,0,0.5), 0 0 30px {s['frameShadow']};
    border: 1px solid rgba(255,255,255,0.1);
    max-width: 100%;
  }}
  .screenshot-frame img {{ display: block; width: 100%; height: auto; max-height: 540px; max-width: 100%; object-fit: contain; }}

  .tags {{
    display: inline-flex; flex-wrap: wrap; gap: 10px; margin-top: 16px;
  }}
  .tag {{
    background: {s['badgeBg']}; border: 1px solid {s['badgeBorder']};
    color: {s['badgeColor']}; padding: 4px 14px; border-radius: 20px;
    font-size: 13px; font-weight: 600; letter-spacing: 0.5px;
    backdrop-filter: blur(6px);
  }}
</style>
</head>
<body>
  <div class="accent"></div>
  <div class="left">
    <div class="badge">Huawei Cloud Gallery</div>
    <div class="title">{title_html}</div>
    {tagline_html}
    {tags_html}
    {desc_html}
  </div>
  <div class="right">
    <div class="screenshot-frame">
      <img src="data:image/png;base64,{screenshot_b64}" alt="Screenshot">
    </div>
  </div>
</body>
</html>"""


def build_hero(s, title_html, tagline_html, desc_html, screenshot_b64, tags_html=''):
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: 1280px; height: 720px;
    background: {s['bg']};
    font-family: 'Noto Sans CJK SC', 'Microsoft YaHei', sans-serif;
    overflow: hidden; position: relative;
  }}
  .bg {{
    position: absolute; inset: 0;
    background-image: url(data:image/png;base64,{screenshot_b64});
    background-size: cover; background-position: center top;
  }}
  .scrim {{
    position: absolute; inset: 0;
    background: linear-gradient(to top, rgba(0,0,0,0.6) 0%, rgba(0,0,0,0.2) 35%, rgba(0,0,0,0.03) 100%);
  }}
  .scrim::after {{
    content: ''; position: absolute; inset: 0;
    background: linear-gradient(to right, rgba(0,0,0,0.25) 0%, transparent 55%);
  }}
  .badge {{
    position: absolute; top: 30px; right: 40px;
    background: {s['badgeBg']}; border: 1px solid {s['badgeBorder']};
    color: {s['badgeColor']}; padding: 6px 16px; border-radius: 20px;
    font-size: 13px; z-index: 3; backdrop-filter: blur(10px);
  }}
  .content {{
    position: absolute; left: 60px; bottom: 60px; right: 60px; z-index: 3;
    padding: 22px 28px;
    background: linear-gradient(to right, rgba(0,0,0,0.45) 0%, rgba(0,0,0,0.2) 55%, transparent 100%);
    border-left: 4px solid {s['badgeColor']};
    border-radius: 0 10px 10px 0;
  }}
  .accent-line {{
    width: 80px; height: 4px; background: {s['badgeColor']};
    box-shadow: 0 0 15px {s['titleShadow']}; margin-bottom: 20px; border-radius: 2px;
  }}
  .title {{
    font-size: 56px; font-weight: 800; color: #fff; line-height: 1.15;
    text-shadow: 0 2px 20px rgba(0,0,0,0.8), 0 0 40px {s['titleShadow']};
    letter-spacing: 2px;
  }}
  .tagline {{
    font-size: 19px; color: rgba(255,255,255,0.78);
    margin-top: 14px; letter-spacing: 1px;
    text-shadow: 0 1px 8px rgba(0,0,0,0.6);
  }}
  .desc {{
    font-size: 17px; color: rgba(255,255,255,0.88);
    margin-top: 12px; letter-spacing: 0.5px; line-height: 1.7;
    max-width: 840px; text-shadow: 0 1px 8px rgba(0,0,0,0.7);
  }}

  .tags {{
    display: inline-flex; flex-wrap: wrap; gap: 10px; margin-top: 16px;
  }}
  .tag {{
    background: {s['badgeBg']}; border: 1px solid {s['badgeBorder']};
    color: {s['badgeColor']}; padding: 4px 14px; border-radius: 20px;
    font-size: 13px; font-weight: 600; letter-spacing: 0.5px;
    backdrop-filter: blur(6px);
  }}
</style>
</head>
<body>
  <div class="bg"></div>
  <div class="scrim"></div>
  <div class="badge">Huawei Cloud Gallery</div>
  <div class="content">
    <div class="accent-line"></div>
    <div class="title">{title_html}</div>
    {tagline_html}
    {tags_html}
    {desc_html}
  </div>
</body>
</html>"""


def build_showcase(s, title_html, tagline_html, desc_html, screenshot_b64, tags_html=''):
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: 1280px; height: 720px;
    background: {s['bg']};
    font-family: 'Noto Sans CJK SC', 'Microsoft YaHei', sans-serif;
    overflow: hidden; position: relative;
    display: flex; flex-direction: column;
  }}
  body::before {{
    content: ''; position: absolute; inset: 0;
    background-image: repeating-linear-gradient(45deg, {s['gridColor']} 0, {s['gridColor']} 1px, transparent 1px, transparent 26px);
    pointer-events: none;
  }}
  body::after {{
    content: ''; position: absolute; top: 50%; left: 30%;
    transform: translate(-50%, -50%); width: 500px; height: 500px;
    background: radial-gradient(circle, {s['glow']} 0%, transparent 70%);
    pointer-events: none;
  }}
  .top-line {{
    width: 100%; height: 4px; background: {s['badgeColor']};
    box-shadow: 0 0 15px {s['titleShadow']}; z-index: 3; flex-shrink: 0;
  }}
  .main {{
    flex: 1; display: flex; flex-direction: row; position: relative; z-index: 2;
  }}
  .left {{
    width: 704px; display: flex; align-items: center; justify-content: center; padding: 26px;
  }}
  .screenshot-frame {{
    width: 100%; height: 100%;
    display: flex; align-items: center; justify-content: center;
    border-radius: 12px; overflow: hidden;
    box-shadow: 0 20px 60px rgba(0,0,0,0.5), 0 0 30px {s['frameShadow']};
    border: 1px solid {s['badgeBorder']};
    background: {s['bg']};
  }}
  .screenshot-frame img {{ display: block; width: 100%; height: 100%; object-fit: contain; }}
  .right {{
    flex: 1; display: flex; flex-direction: column; justify-content: center; padding: 34px 48px 34px 28px;
  }}
  .badge {{
    align-self: flex-start; background: {s['badgeBg']}; border: 1px solid {s['badgeBorder']};
    color: {s['badgeColor']}; padding: 6px 16px; border-radius: 20px;
    font-size: 13px; margin-bottom: 18px; backdrop-filter: blur(10px);
  }}
  .title {{
    font-size: 48px; font-weight: 800; color: #fff; line-height: 1.15;
    text-shadow: 0 0 20px {s['titleShadow']}, 0 0 40px {s['titleShadow']};
    letter-spacing: 2px;
    margin-bottom: 18px;
  }}
  .tagline {{
    font-size: 18px; color: rgba(255,255,255,0.62);
    letter-spacing: 1px;
  }}
  .desc {{
    font-size: 16px; color: rgba(255,255,255,0.8);
    margin-top: 18px; letter-spacing: 0.5px; line-height: 1.8;
    border-left: 3px solid {s['badgeColor']}; padding-left: 14px;
    max-width: 470px;
  }}

  .tags {{
    display: inline-flex; flex-wrap: wrap; gap: 10px; margin-top: 16px;
  }}
  .tag {{
    background: {s['badgeBg']}; border: 1px solid {s['badgeBorder']};
    color: {s['badgeColor']}; padding: 4px 14px; border-radius: 20px;
    font-size: 13px; font-weight: 600; letter-spacing: 0.5px;
    backdrop-filter: blur(6px);
  }}
</style>
</head>
<body>
  <div class="top-line"></div>
  <div class="main">
    <div class="left">
      <div class="screenshot-frame">
        <img src="data:image/png;base64,{screenshot_b64}" alt="Screenshot">
      </div>
    </div>
    <div class="right">
      <div class="badge">Huawei Cloud Gallery</div>
      <div class="title">{title_html}</div>
      {tagline_html}
    {tags_html}
      {desc_html}
    </div>
  </div>
</body>
</html>"""


def build_polaroid(s, title_html, tagline_html, desc_html, screenshot_b64, tags_html=''):
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: 1280px; height: 720px;
    background: {s['bg']};
    font-family: 'Noto Sans CJK SC', 'Microsoft YaHei', sans-serif;
    overflow: hidden; position: relative;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
  }}
  body::before {{
    content: ''; position: absolute; inset: 0;
    background-image:
      linear-gradient({s['gridColor']} 1px, transparent 1px),
      linear-gradient(90deg, {s['gridColor']} 1px, transparent 1px);
    background-size: 40px 40px; pointer-events: none;
  }}
  body::after {{
    content: ''; position: absolute; top: 42%; left: 50%;
    transform: translate(-50%, -50%); width: 640px; height: 640px;
    background: radial-gradient(circle, {s['glow']} 0%, transparent 70%);
    pointer-events: none;
  }}
  .text-block {{
    text-align: center; z-index: 2; padding: 0 40px; margin-bottom: 26px;
  }}
  .title {{
    font-size: 46px; font-weight: 800; color: #fff;
    text-shadow: 0 0 20px {s['titleShadow']}, 0 0 40px {s['titleShadow']};
    letter-spacing: 2px;
  }}
  .tagline {{
    font-size: 18px; color: rgba(255,255,255,0.62);
    margin-top: 10px; letter-spacing: 1px;
  }}
  .desc {{
    font-size: 16px; color: rgba(255,255,255,0.8);
    margin-top: 14px; line-height: 1.7; max-width: 860px;
    margin-left: auto; margin-right: auto;
  }}
  .polaroid {{
    z-index: 2; background: #fff; padding: 16px 16px 40px;
    border-radius: 6px; box-shadow: 0 24px 60px rgba(0,0,0,0.55), 0 0 30px {s['frameShadow']};
    transform: rotate(-2deg);
  }}
  .polaroid img {{
    display: block; width: 660px; height: 372px; object-fit: cover; border-radius: 2px;
  }}
  .polaroid-cap {{
    display: flex; align-items: center; gap: 10px; margin-top: 14px; padding: 0 8px;
  }}
  .polaroid-cap .bar {{
    flex: 1; height: 14px; background: {s['badgeColor']}; border-radius: 4px; opacity: 0.7;
  }}
  .polaroid-cap .note {{
    font-size: 15px; color: #333; font-family: 'Segoe Script', 'Comic Sans MS', cursive; font-weight: 600;
  }}
  .badge {{
    position: absolute; top: 26px; right: 36px;
    background: {s['badgeBg']}; border: 1px solid {s['badgeBorder']};
    color: {s['badgeColor']}; padding: 6px 16px; border-radius: 20px;
    font-size: 14px; z-index: 3; backdrop-filter: blur(10px);
  }}

  .tags {{
    display: inline-flex; flex-wrap: wrap; gap: 10px; margin-top: 16px;
  }}
  .tag {{
    background: {s['badgeBg']}; border: 1px solid {s['badgeBorder']};
    color: {s['badgeColor']}; padding: 4px 14px; border-radius: 20px;
    font-size: 13px; font-weight: 600; letter-spacing: 0.5px;
    backdrop-filter: blur(6px);
  }}
</style>
</head>
<body>
  <div class="badge">Huawei Cloud Gallery</div>
  <div class="text-block">
    <div class="title">{title_html}</div>
    {tagline_html}
    {tags_html}
    {desc_html}
  </div>
  <div class="polaroid">
    <img src="data:image/png;base64,{screenshot_b64}" alt="Screenshot">
    <div class="polaroid-cap">
      <span class="note">{escape('作品一角')}</span>
      <span class="bar"></span>
    </div>
  </div>
</body>
</html>"""


def build_blur(s, title_html, tagline_html, desc_html, screenshot_b64, tags_html=''):
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: 1280px; height: 720px;
    background: {s['bg']};
    font-family: 'Noto Sans CJK SC', 'Microsoft YaHei', sans-serif;
    overflow: hidden; position: relative;
  }}
  .bg-blur {{
    position: absolute; inset: 0;
    background-image: url(data:image/png;base64,{screenshot_b64});
    background-size: cover; background-position: center;
    filter: blur(16px) saturate(1.3) brightness(0.55);
    transform: scale(1.15);
  }}
  .scrim {{
    position: absolute; inset: 0;
    background: linear-gradient(to right, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0.05) 55%);
  }}
  .badge {{
    position: absolute; top: 30px; right: 40px;
    background: {s['badgeBg']}; border: 1px solid {s['badgeBorder']};
    color: {s['badgeColor']}; padding: 6px 16px; border-radius: 20px;
    font-size: 13px; z-index: 3; backdrop-filter: blur(10px);
  }}
  .content {{
    position: absolute; left: 70px; top: 50%; transform: translateY(-50%);
    width: 480px; z-index: 3;
  }}
  .accent-line {{
    width: 80px; height: 4px; background: {s['badgeColor']};
    box-shadow: 0 0 15px {s['titleShadow']}; margin-bottom: 20px; border-radius: 2px;
  }}
  .title {{
    font-size: 54px; font-weight: 800; color: #fff; line-height: 1.15;
    text-shadow: 0 2px 20px rgba(0,0,0,0.8), 0 0 40px {s['titleShadow']};
    letter-spacing: 2px;
  }}
  .tagline {{
    font-size: 19px; color: rgba(255,255,255,0.78);
    margin-top: 14px; letter-spacing: 1px;
    text-shadow: 0 1px 8px rgba(0,0,0,0.6);
  }}
  .desc {{
    font-size: 17px; color: rgba(255,255,255,0.9);
    margin-top: 14px; letter-spacing: 0.5px; line-height: 1.7;
    max-width: 440px; text-shadow: 0 1px 8px rgba(0,0,0,0.7);
  }}
  .shot-frame {{
    position: absolute; right: 90px; top: 50%; transform: translateY(-50%);
    width: 560px; z-index: 3;
    border-radius: 14px; overflow: hidden;
    box-shadow: 0 24px 70px rgba(0,0,0,0.65), 0 0 40px {s['frameShadow']};
    border: 1px solid rgba(255,255,255,0.18);
  }}
  .shot-frame img {{ display: block; width: 560px; height: 420px; object-fit: cover; }}

  .tags {{
    display: inline-flex; flex-wrap: wrap; gap: 10px; margin-top: 16px;
  }}
  .tag {{
    background: {s['badgeBg']}; border: 1px solid {s['badgeBorder']};
    color: {s['badgeColor']}; padding: 4px 14px; border-radius: 20px;
    font-size: 13px; font-weight: 600; letter-spacing: 0.5px;
    backdrop-filter: blur(6px);
  }}
</style>
</head>
<body>
  <div class="bg-blur"></div>
  <div class="scrim"></div>
  <div class="badge">Huawei Cloud Gallery</div>
  <div class="content">
    <div class="accent-line"></div>
    <div class="title">{title_html}</div>
    {tagline_html}
    {tags_html}
    {desc_html}
  </div>
  <div class="shot-frame">
    <img src="data:image/png;base64,{screenshot_b64}" alt="Screenshot">
  </div>
</body>
</html>"""


def build_topbar(s, title_html, tagline_html, desc_html, screenshot_b64, tags_html=''):
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: 1280px; height: 720px;
    background: {s['bg']};
    font-family: 'Noto Sans CJK SC', 'Microsoft YaHei', sans-serif;
    overflow: hidden; position: relative;
    display: flex; flex-direction: column;
  }}
  .bar {{
    height: 118px; position: relative; z-index: 2;
    display: flex; align-items: center;
    padding: 0 56px; gap: 28px;
    background: {s['badgeBg']};
    border-bottom: 2px solid {s['badgeBorder']};
    backdrop-filter: blur(10px);
  }}
  .bar .badge {{
    background: {s['badgeBg']}; border: 1px solid {s['badgeBorder']};
    color: {s['badgeColor']}; padding: 6px 16px; border-radius: 20px;
    font-size: 13px; flex-shrink: 0;
  }}
  .bar .title {{
    font-size: 40px; font-weight: 800; color: #fff;
    text-shadow: 0 0 20px {s['titleShadow']}; letter-spacing: 2px;
    white-space: nowrap;
  }}
  .bar .tagline {{
    font-size: 17px; color: rgba(255,255,255,0.66); letter-spacing: 1px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }}
  .shot-area {{
    flex: 1; position: relative; padding: 24px 56px 34px;
    display: flex; flex-direction: column; z-index: 2; min-height: 0;
  }}
  .shot-frame {{
    flex: 1; position: relative; min-height: 0;
    border-radius: 12px; overflow: hidden;
    box-shadow: 0 20px 60px rgba(0,0,0,0.5), 0 0 30px {s['frameShadow']};
    border: 2px solid {s['badgeBorder']};
    background: {s['bg']}; padding: 8px;
  }}
  .shot-frame img {{ display: block; width: 100%; height: 100%; object-fit: contain; border-radius: 6px; }}
  .desc {{
    margin-top: 16px; font-size: 15px; color: rgba(255,255,255,0.82);
    letter-spacing: 0.5px; line-height: 1.6; max-width: 960px;
  }}

  .tags {{
    display: inline-flex; flex-wrap: wrap; gap: 10px; margin-top: 16px;
  }}
  .tag {{
    background: {s['badgeBg']}; border: 1px solid {s['badgeBorder']};
    color: {s['badgeColor']}; padding: 4px 14px; border-radius: 20px;
    font-size: 13px; font-weight: 600; letter-spacing: 0.5px;
    backdrop-filter: blur(6px);
  }}
</style>
</head>
<body>
  <div class="bar">
    <span class="badge">Huawei Cloud Gallery</span>
    <span class="title">{title_html}</span>
    {tagline_html}
    {tags_html}
  </div>
  <div class="shot-area">
    <div class="shot-frame">
      <img src="data:image/png;base64,{screenshot_b64}" alt="Screenshot">
    </div>
    {desc_html}
  </div>
</body>
</html>"""


def build_spotlight(s, title_html, tagline_html, desc_html, screenshot_b64, tags_html=''):
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: 1280px; height: 720px;
    background: {s['bg']};
    font-family: 'Noto Sans CJK SC', 'Microsoft YaHei', sans-serif;
    overflow: hidden; position: relative;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
  }}
  body::before {{
    content: ''; position: absolute; inset: 0;
    background-image: radial-gradient(circle at 20% 12%, {s['glow']} 0, transparent 45%),
      radial-gradient(circle at 80% 90%, {s['glow']} 0, transparent 40%);
    pointer-events: none;
  }}
  .spot {{
    position: absolute; top: 8%; left: 50%; transform: translateX(-50%);
    width: 720px; height: 460px;
    background: radial-gradient(ellipse at center, {s['glow']} 0%, transparent 68%);
    filter: blur(2px); pointer-events: none; z-index: 1;
  }}
  .head {{
    position: relative; z-index: 2; text-align: center; padding: 0 90px;
  }}
  .badge {{
    display: inline-block; background: {s['badgeBg']}; border: 1px solid {s['badgeBorder']};
    color: {s['badgeColor']}; padding: 6px 18px; border-radius: 20px;
    font-size: 13px; margin-bottom: 22px; backdrop-filter: blur(8px); letter-spacing: 1px;
  }}
  .title {{
    font-size: 54px; font-weight: 800; color: #fff; line-height: 1.18; letter-spacing: 2px;
    text-shadow: 0 0 18px {s['titleShadow']}, 0 0 46px {s['titleShadow']};
  }}
  .tagline {{ font-size: 19px; color: rgba(255,255,255,0.72); margin-top: 14px; letter-spacing: 1px; }}
  .shot {{
    position: relative; z-index: 2; margin-top: 26px;
    border-radius: 16px; overflow: hidden;
    box-shadow: 0 24px 70px rgba(0,0,0,0.55), 0 0 40px {s['frameShadow']};
    border: 1px solid {s['badgeBorder']};
    width: 900px; height: 300px;
  }}
  .shot img {{ display: block; width: 100%; height: 100%; object-fit: contain; }}
  .desc {{ position: relative; z-index: 2; margin-top: 22px; font-size: 16px; color: rgba(255,255,255,0.85); letter-spacing: 0.5px; line-height: 1.7; max-width: 1000px; text-align: center; }}
  .tags {{ display: inline-flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; position: relative; z-index: 2; justify-content: center; }}
  .tag {{ background: {s['badgeBg']}; border: 1px solid {s['badgeBorder']}; color: {s['badgeColor']}; padding: 4px 14px; border-radius: 20px; font-size: 13px; font-weight: 600; backdrop-filter: blur(6px); }}
</style>
</head>
<body>
  <div class="spot"></div>
  <div class="head">
    <div class="badge">Huawei Cloud Gallery</div>
    <div class="title">{title_html}</div>
    {tagline_html}
  </div>
  <div class="shot">
    <img src="data:image/png;base64,{screenshot_b64}" alt="Screenshot">
  </div>
  {tags_html}
  {desc_html}
</body>
</html>"""


def build_cinema(s, title_html, tagline_html, desc_html, screenshot_b64, tags_html=''):
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: 1280px; height: 720px;
    background: {s['bg']};
    font-family: 'Noto Sans CJK SC', 'Microsoft YaHei', sans-serif;
    overflow: hidden; position: relative;
    display: flex; flex-direction: column; justify-content: center;
  }}
  .letterbox {{
    position: absolute; left: 0; right: 0; height: 70px; background: {s['bg']}; z-index: 3;
    opacity: 0.96;
  }}
  .letterbox.top {{ top: 0; border-bottom: 1px solid {s['badgeBorder']}; }}
  .letterbox.bottom {{ bottom: 0; border-top: 1px solid {s['badgeBorder']}; }}
  .scan {{
    position: absolute; top: -20%; left: 0; right: 0; height: 40px; z-index: 4; pointer-events: none;
    background: linear-gradient(to bottom, transparent, {s['glow']}, transparent);
    filter: blur(1px);
  }}
  .reel {{
    position: absolute; top: 14px; left: 26px; z-index: 4; font-size: 13px; color: rgba(255,255,255,0.5); letter-spacing: 3px;
  }}
  .reel.r {{ right: 26px; left: auto; }}
  .screen {{
    position: relative; z-index: 2; margin: 26px 110px 0; height: 380px;
    border-radius: 8px; overflow: hidden;
    box-shadow: 0 0 60px {s['frameShadow']}, 0 30px 80px rgba(0,0,0,0.8);
    border: 1px solid {s['badgeBorder']};
    background: {s['bg']};
  }}
  .screen img {{ display: block; width: 100%; height: 100%; object-fit: contain; }}
  .screen::after {{
    content: ''; position: absolute; inset: 0;
    background: linear-gradient(to bottom, rgba(0,0,0,0.28) 0%, transparent 22%, transparent 78%, rgba(0,0,0,0.30) 100%);
  }}
  .caption {{
    position: relative; z-index: 2; text-align: center; margin-top: 30px;
  }}
.title {{ font-size: 44px; font-weight: 900; color: {s['badgeColor']}; letter-spacing: 6px; text-shadow: 0 0 22px {s['titleShadow']}, 0 4px 24px rgba(0,0,0,0.9); }}
  .tagline {{ font-size: 17px; color: rgba(255,255,255,0.72); margin-top: 12px; letter-spacing: 3px; }}
  .tags {{ display: inline-flex; gap: 10px; margin-top: 18px; }}
  .tag {{ background: {s['badgeBg']}; border: 1px solid {s['badgeBorder']}; color: {s['badgeColor']}; padding: 4px 14px; border-radius: 20px; font-size: 13px; backdrop-filter: blur(6px); }}
  .desc {{ position: relative; z-index: 2; width: 100%; text-align: center; margin-top: 16px; font-size: 15px; color: rgba(255,255,255,0.78); letter-spacing: 0.5px; }}
  .crawl {{ position: absolute; left: 0; right: 0; bottom: 74px; height: 2px; z-index: 2;
    background: linear-gradient(90deg, transparent, {s['badgeColor']}, transparent); opacity: 0.75; }}
</style>
</head>
<body>
  <div class="letterbox top"></div>
  <div class="letterbox bottom"></div>
  <div class="reel">HUAWEI · ICT</div>
  <div class="reel r">REEL 01</div>
  <div class="scan"></div>
  <div class="screen">
    <img src="data:image/png;base64,{screenshot_b64}" alt="Screenshot">
  </div>
  <div class="crawl"></div>
  <div class="caption">
    <div class="title">{title_html}</div>
    {tagline_html}
    {tags_html}
  </div>
  {desc_html}
</body>
</html>"""


def build_blueprint(s, title_html, tagline_html, desc_html, screenshot_b64, tags_html=''):
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: 1280px; height: 720px;
    background: #0a1f3c;
    font-family: 'Consolas', 'Courier New', monospace;
    overflow: hidden; position: relative;
    display: flex; flex-direction: column;
  }}
  body::before {{
    content: ''; position: absolute; inset: 0;
    background-image:
      linear-gradient(rgba(96,165,250,0.14) 1px, transparent 1px),
      linear-gradient(90deg, rgba(96,165,250,0.14) 1px, transparent 1px);
    background-size: 28px 28px; pointer-events: none;
  }}
  .corner {{ position: absolute; width: 30px; height: 30px; border: 3px solid {s['badgeColor']}; z-index: 4; opacity: 0.85; }}
  .corner.tl {{ top: 22px; left: 22px; border-right: 0; border-bottom: 0; }}
  .corner.tr {{ top: 22px; right: 22px; border-left: 0; border-bottom: 0; }}
  .corner.bl {{ bottom: 22px; left: 22px; border-right: 0; border-top: 0; }}
  .corner.br {{ bottom: 22px; right: 22px; border-left: 0; border-top: 0; }}
  .label {{
    position: absolute; top: 34px; right: 64px; font-size: 12px; color: {s['badgeColor']};
    letter-spacing: 2px; z-index: 4; opacity: 0.8;
  }}
  .head {{ position: relative; z-index: 2; padding: 78px 70px 8px; }}
  .kicker {{ font-size: 13px; color: {s['badgeColor']}; letter-spacing: 6px; margin-bottom: 16px; opacity: 0.9; }}
  .title {{ font-size: 50px; font-weight: 700; color: #e2e8f0; line-height: 1.16; letter-spacing: 2px; text-shadow: 0 0 16px {s['titleShadow']}; }}
  .tagline {{ font-size: 17px; color: rgba(148,197,255,0.8); margin-top: 12px; letter-spacing: 1px; }}
  .main {{ position: relative; z-index: 2; flex: 1; display: flex; align-items: center; justify-content: center; padding: 18px 70px 40px; min-height: 0; }}
  .shot {{ border-radius: 10px; overflow: hidden; border: 2px solid {s['badgeBorder']}; box-shadow: 0 0 0 1px rgba(96,165,250,0.25), 0 20px 50px rgba(0,0,0,0.5); position: relative; height: 330px; }}
  .shot img {{ display: block; height: 100%; width: auto; max-width: 100%; object-fit: contain; }}
  .coord-ver {{ position: absolute; top: 40%; right: 40px; font-size: 12px; color: {s['badgeColor']}; letter-spacing: 2px; opacity: 0.75; transform: rotate(90deg); z-index: 4; }}
  .desc {{ position: relative; z-index: 2; padding: 0 70px 26px; font-size: 14px; color: rgba(148,197,255,0.9); letter-spacing: 0.5px; line-height: 1.7; max-width: 900px; }}
  .tags {{ display: inline-flex; gap: 8px; }}
  .tag {{ border: 1px solid {s['badgeBorder']}; color: {s['badgeColor']}; padding: 3px 12px; border-radius: 3px; font-size: 12px; letter-spacing: 1px; }}
</style>
</head>
<body>
  <span class="corner tl"></span><span class="corner tr"></span>
  <span class="corner bl"></span><span class="corner br"></span>
  <div class="label">BLUEPRINT · 01</div>
  <div class="coord-ver">A-01</div>
  <div class="head">
    <div class="kicker">PROJECT</div>
    <div class="title">{title_html}</div>
    {tagline_html}
  </div>
  <div class="main">
    <div class="shot">
      <img src="data:image/png;base64,{screenshot_b64}" alt="Screenshot">
    </div>
  </div>
  {tags_html}
  {desc_html}
</body>
</html>"""


def build_diorama(s, title_html, tagline_html, desc_html, screenshot_b64, tags_html=''):
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: 1280px; height: 720px;
    background: {s['bg']};
    font-family: 'Noto Sans CJK SC', 'Microsoft YaHei', sans-serif;
    overflow: hidden; position: relative;
    display: flex; flex-direction: column; justify-content: center;
  }}
  body::before {{
    content: ''; position: absolute; inset: 0;
    background: radial-gradient(circle at 50% 30%, {s['glow']} 0%, transparent 60%);
    pointer-events: none;
  }}
  .stack {{ position: relative; z-index: 1; margin: 0 auto; width: 860px; height: 400px; }}
  .card {{
    position: absolute; border-radius: 16px; overflow: hidden;
    border: 1px solid {s['badgeBorder']};
    box-shadow: 0 24px 60px rgba(0,0,0,0.5);
    background: {s['bg']};
  }}
  .card img {{ display: block; width: 100%; height: 100%; object-fit: contain; }}
  .card.back {{ width: 780px; height: 340px; top: 40px; left: 40px; transform: rotate(-3deg); opacity: 0.6; }}
  .card.mid {{ width: 820px; height: 370px; top: 22px; left: 24px; transform: rotate(2deg); opacity: 0.82; }}
  .card.front {{ width: 860px; height: 400px; top: 0; left: 0; z-index: 3; transform: rotate(-0.5deg); }}
  .head {{
    position: relative; z-index: 4; margin-top: 18px; text-align: center; padding: 0 80px;
  }}
  .title {{ font-size: 46px; font-weight: 800; color: #fff; line-height: 1.18; letter-spacing: 2px; text-shadow: 0 2px 4px rgba(0,0,0,0.6), 0 0 26px {s['titleShadow']}; }}
  .tagline {{ font-size: 18px; color: rgba(255,255,255,0.7); margin-top: 10px; letter-spacing: 1px; }}
  .badge {{ display: inline-block; background: {s['badgeBg']}; border: 1px solid {s['badgeBorder']}; color: {s['badgeColor']}; padding: 5px 16px; border-radius: 20px; font-size: 12px; margin-bottom: 16px; }}
  .tags {{ display: inline-flex; gap: 10px; margin-top: 14px; justify-content: center; }}
  .tag {{ background: {s['badgeBg']}; border: 1px solid {s['badgeBorder']}; color: {s['badgeColor']}; padding: 4px 14px; border-radius: 20px; font-size: 13px; backdrop-filter: blur(6px); }}
  .desc {{ position: relative; z-index: 4; margin-top: 20px; text-align: center; font-size: 16px; color: rgba(255,255,255,0.85); letter-spacing: 0.5px; padding: 0 140px; line-height: 1.7; }}
</style>
</head>
<body>
  <div class="stack">
    <div class="card back"><img src="data:image/png;base64,{screenshot_b64}" alt="b"></div>
    <div class="card mid"><img src="data:image/png;base64,{screenshot_b64}" alt="m"></div>
    <div class="card front"><img src="data:image/png;base64,{screenshot_b64}" alt="f"></div>
  </div>
  <div class="head">
    <div class="badge">Huawei Cloud Gallery</div>
    <div class="title">{title_html}</div>
    {tagline_html}
    {tags_html}
  </div>
  {desc_html}
</body>
</html>"""


def build_glass(s, title_html, tagline_html, desc_html, screenshot_b64, tags_html=''):
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: 1280px; height: 720px;
    background: {s['bg']};
    font-family: 'Noto Sans CJK SC', 'Microsoft YaHei', sans-serif;
    overflow: hidden; position: relative;
    display: flex; flex-direction: column; justify-content: center;
  }}
  body::before {{
    content: ''; position: absolute; inset: 0;
    background-image: radial-gradient(circle at 12% 20%, {s['glow']} 0, transparent 42%),
      radial-gradient(circle at 88% 78%, {s['glow']} 0, transparent 46%);
    pointer-events: none;
  }}
  .glow-orb {{
    position: absolute; width: 340px; height: 340px; border-radius: 50%;
    filter: blur(60px); background: {s['glow']}; z-index: 1;
  }}
  .glow-orb.a {{ top: -60px; left: -60px; }}
  .glow-orb.b {{ bottom: -80px; right: -60px; }}
  .panel {{
    position: relative; z-index: 2; margin: 0 auto;
    display: flex; flex-direction: row; gap: 30px; align-items: center;
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.18);
    border-radius: 22px; padding: 34px 40px; width: 1000px;
    backdrop-filter: blur(18px) saturate(1.4);
    -webkit-backdrop-filter: blur(18px) saturate(1.4);
    box-shadow: 0 30px 70px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.25);
  }}
  .shot {{ border-radius: 14px; overflow: hidden; flex-shrink: 0; flex-basis: 480px; min-width: 0; height: 372px; border: 1px solid rgba(255,255,255,0.2); box-shadow: 0 18px 40px rgba(0,0,0,0.4); background: {s['bg']}; }}
  .shot img {{ display: block; width: 100%; height: 100%; object-fit: contain; }}
  .text {{ flex: 1; min-width: 0; }}
  .badge {{ display: inline-block; background: {s['badgeBg']}; border: 1px solid {s['badgeBorder']}; color: {s['badgeColor']}; padding: 5px 16px; border-radius: 20px; font-size: 12px; margin-bottom: 16px; letter-spacing: 1px; }}
  .title {{ font-size: 42px; font-weight: 800; color: #fff; line-height: 1.2; letter-spacing: 1.5px; text-shadow: 0 2px 8px rgba(0,0,0,0.35), 0 0 24px {s['titleShadow']}; }}
  .tagline {{ font-size: 17px; color: rgba(255,255,255,0.72); margin-top: 12px; letter-spacing: 1px; }}
  .tags {{ display: inline-flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }}
  .tag {{ background: {s['badgeBg']}; border: 1px solid {s['badgeBorder']}; color: {s['badgeColor']}; padding: 4px 14px; border-radius: 20px; font-size: 13px; backdrop-filter: blur(6px); }}
  .desc {{ position: relative; z-index: 2; margin-top: 26px; text-align: center; font-size: 15px; color: rgba(255,255,255,0.8); letter-spacing: 0.5px; padding: 0 140px; line-height: 1.7; }}
</style>
</head>
<body>
  <div class="glow-orb a"></div>
  <div class="glow-orb b"></div>
  <div class="panel">
    <div class="shot">
      <img src="data:image/png;base64,{screenshot_b64}" alt="Screenshot">
    </div>
    <div class="text">
      <div class="badge">Huawei Cloud Gallery</div>
      <div class="title">{title_html}</div>
      {tagline_html}
      {tags_html}
    </div>
  </div>
  {desc_html}
</body>
</html>"""


def build_collage(s, title_html, tagline_html, desc_html, screenshot_b64, small_shots_b64, tags_html='', variant='h'):
    # variant: "h" 大图在上小图在下 | "v" 大图在左小图在右 | "grid" 1大+3小网格
    if variant == "v":
        # 左大右小竖排
        main_area = """<div class="main-v">
      <div class="big"><img src="data:image/png;base64,BIG0" alt="main"></div>
      <div class="col">
        SMALLS
      </div>
    </div>"""
        css_extra = """
  .main-v { flex: 1; display: flex; gap: 22px; padding: 34px 44px 40px; position: relative; z-index: 2; min-height: 0; }
  .big { flex-basis: 72%; border-radius: 12px; overflow: hidden; box-shadow: 0 20px 60px rgba(0,0,0,0.5); border: 1px solid rgba(255,255,255,0.12); background: {s['bg']}; position: relative; padding: 10px; }
  .big img { width: 100%; height: 100%; object-fit: contain; display: block; border-radius: 6px; }
  .col { flex: 1; display: flex; flex-direction: column; gap: 18px; min-height: 0; }
  .col .sm { flex: 1; border-radius: 10px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.12); background: {s['bg']}; position: relative; padding: 6px; min-height: 0; }
  .col .sm img { width: 100%; height: 100%; object-fit: contain; display: block; border-radius: 5px; }
"""
    elif variant == "grid":
        # 宫格：左大图 + 右侧两行小图（1 大 + 3 小，2×2 感）
        main_area = """<div class="main-g">
      <div class="g-big"><img src="data:image/png;base64,BIG0" alt="main"></div>
      <div class="g-col">
        SMALLS
      </div>
    </div>"""
        css_extra = """
  .main-g { flex: 1; display: flex; gap: 22px; padding: 26px 44px 40px; position: relative; z-index: 2; min-height: 0; }
  .g-big { flex: 1.15; border-radius: 12px; overflow: hidden; box-shadow: 0 20px 60px rgba(0,0,0,0.5); border: 1px solid rgba(255,255,255,0.12); background: {s['bg']}; position: relative; padding: 10px; min-width: 0; }
  .g-big img { width: 100%; height: 100%; object-fit: contain; display: block; border-radius: 6px; }
  .g-col { flex: 1; display: flex; flex-direction: column; gap: 18px; min-height: 0; min-width: 0; }
  .g-col .sm { flex: 1; border-radius: 10px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.12); background: {s['bg']}; position: relative; padding: 6px; min-height: 0; min-width: 0; }
  .g-col .sm img { width: 100%; height: 100%; object-fit: contain; display: block; border-radius: 5px; }
"""
    else:
        # 默认 variant in ("h",): 大图在上，小图横幅
        main_area = """<div class="main-h">
      <div class="big"><img src="data:image/png;base64,BIG0" alt="main"></div>
      <div class="row">
        SMALLS
      </div>
    </div>"""
        css_extra = """
  .main-h { flex: 1; display: flex; flex-direction: column; gap: 18px; padding: 26px 44px 40px; position: relative; z-index: 2; min-height: 0; }
  .main-h .big { flex: 3; border-radius: 12px; overflow: hidden; box-shadow: 0 20px 60px rgba(0,0,0,0.5); border: 1px solid rgba(255,255,255,0.12); background: {s['bg']}; position: relative; padding: 10px; min-height: 0; }
  .main-h .big img { width: 100%; height: 100%; object-fit: contain; display: block; border-radius: 6px; }
  .row { flex: 2; display: flex; gap: 16px; min-height: 0; }
  .row .sm { flex: 1; border-radius: 10px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.12); background: {s['bg']}; position: relative; padding: 6px; min-height: 0; min-width: 0; }
  .row .sm img { width: 100%; height: 100%; object-fit: contain; display: block; border-radius: 5px; }
"""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: 1280px; height: 720px;
    background: {s['bg']};
    font-family: 'Noto Sans CJK SC', 'Microsoft YaHei', sans-serif;
    overflow: hidden; position: relative;
    display: flex; flex-direction: column;
  }}
  body::before {{
    content: ''; position: absolute; inset: 0;
    background-image:
      linear-gradient({s['gridColor']} 1px, transparent 1px),
      linear-gradient(90deg, {s['gridColor']} 1px, transparent 1px);
    background-size: 40px 40px; pointer-events: none;
  }}
  .head {{
    padding: 18px 32px 10px; display: flex; align-items: baseline; gap: 16px;
    position: relative; z-index: 3;
  }}
  .head .badge {{
    background: {s['badgeBg']}; border: 1px solid {s['badgeBorder']};
    color: {s['badgeColor']}; padding: 5px 14px; border-radius: 20px;
    font-size: 13px;
  }}
  .head .title {{
    font-size: 38px; font-weight: 800; color: #fff;
    text-shadow: 0 0 20px {s['titleShadow']}; letter-spacing: 2px;
  }}
  .head .tagline {{
    font-size: 16px; color: rgba(255,255,255,0.66); letter-spacing: 1px;
  }}
  .desc {{
    padding: 0 32px 12px; font-size: 15px; color: rgba(255,255,255,0.82);
    line-height: 1.6; max-width: 1160px; position: relative; z-index: 3;
  }}
  {css_extra}

  .tags {{
    display: inline-flex; flex-wrap: wrap; gap: 10px; margin-top: 16px;
  }}
  .tag {{
    background: {s['badgeBg']}; border: 1px solid {s['badgeBorder']};
    color: {s['badgeColor']}; padding: 4px 14px; border-radius: 20px;
    font-size: 13px; font-weight: 600; letter-spacing: 0.5px;
    backdrop-filter: blur(6px);
  }}
</style>
</head>
<body>
  <div class="head">
    <span class="badge">Huawei Cloud Gallery</span>
    <span class="title">{title_html}</span>
    {tagline_html}
    {tags_html}
  </div>
  {desc_html}
  {main_area.replace('BIG0', screenshot_b64).replace('SMALLS', small_shots_b64)}
</body>
</html>"""


def _collage_smalls(small_shots_b64, count=None, variant="h"):
    """生成小图板块；按实际传入的小图张数显示（0~count 张自适应伸缩），不重复填充。

    此前用「不足则复制第一张补位」导致大图/某页在小图位重复出现，视觉上明显。
    改为：有几张显示几张，容器 flex 自动均分；无图则板块留空（flex:1 空位让其他区扩展）。
    """
    if count is None:
        count = 4
    max_count = min(count, len(small_shots_b64))
    return "".join(f'<div class="sm"><img src="data:image/png;base64,{b}" alt="s"></div>' if b else "" for b in small_shots_b64[:max_count])


def build_collage_h(s, title_html, tagline_html, desc_html, screenshot_b64, small_shots_b64, tags_html=''):
    return build_collage(s, title_html, tagline_html, desc_html, screenshot_b64, _collage_smalls(small_shots_b64, 4, "h"), tags_html, "h")


def build_collage_v(s, title_html, tagline_html, desc_html, screenshot_b64, small_shots_b64, tags_html=''):
    return build_collage(s, title_html, tagline_html, desc_html, screenshot_b64, _collage_smalls(small_shots_b64, 3, "v"), tags_html, "v")


def build_collage_grid(s, title_html, tagline_html, desc_html, screenshot_b64, small_shots_b64, tags_html=''):
    return build_collage(s, title_html, tagline_html, desc_html, screenshot_b64, _collage_smalls(small_shots_b64, 3, "grid"), tags_html, "grid")


BUILDERS = {
    "classic": build_classic,
    "split": build_split,
    "hero": build_hero,
    "showcase": build_showcase,
    "polaroid": build_polaroid,
    "blur": build_blur,
    "topbar": build_topbar,
    "spotlight": build_spotlight,
    "cinema": build_cinema,
    "blueprint": build_blueprint,
    "diorama": build_diorama,
    "glass": build_glass,
    "collage-h": build_collage_h,
    "collage-v": build_collage_v,
    "collage-grid": build_collage_grid,
}


def main():
    ap = argparse.ArgumentParser(
        prog="generate_cover.py",
        description="可复用的作品封面生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--screenshot", required=True, help="应用截图 PNG 路径")
    ap.add_argument("--title", required=True, help="作品名称")
    ap.add_argument("--out", required=True, help="输出封面 PNG 路径")
    ap.add_argument("--tagline", default="", help="副标题")
    ap.add_argument("--description", default="", help="主体介绍文字（1~3 句）")
    ap.add_argument("--scheme", default="auto", choices=SCHEME_CHOICES, help=f"色调：auto(默认,按标题哈希选色) / " + " / ".join(list(SCHEMES.keys())))
    ap.add_argument("--layout", default="auto", choices=LAYOUTS, help="布局模板（默认 auto，按标题哈希选择）：" + " / ".join(LAYOUTS))
    ap.add_argument("--screenshots", default="", help="多图布局的附加截图路径，逗号分隔（collage-* 用；其余布局忽略）")
    ap.add_argument("--keywords", default="", help="作品关键词标签，逗号分隔 3~5 个（如 'Web,游戏,前端'；可选，渲染为一排徽章）")
    args = ap.parse_args()

    screenshot_path = Path(args.screenshot)
    if not screenshot_path.exists():
        sys.exit(f"❌ 截图文件不存在: {screenshot_path}")

    try:
        from playwright.sync_api import sync_playwright
        from browser_launch import launch_browser
    except ImportError as e:
        sys.exit(
            "❌ 缺少 Python 依赖 playwright（封面生成必需）。请先运行渲染前 preflight 自动补齐：\n"
            "   bash $SKILL_DIR/scripts/preflight.sh   （或 Windows: powershell $SKILL_DIR/scripts/preflight.ps1）\n"
            "   或手动安装：python -m pip install playwright && python -m playwright install chromium\n"
            f"   原始错误: {e}"
        )

    screenshot_b64 = base64.b64encode(screenshot_path.read_bytes()).decode("ascii")

    title_html = escape(args.title)
    tagline_html = f'<div class="tagline">{escape(args.tagline)}</div>' if args.tagline else ""
    desc_html = f'<div class="desc">{escape(args.description)}</div>' if args.description else ""
    # 关键词徽章（可选）：传 --keywords 时须 3~5 个词（英文/中文皆可），渲染为一排 pill 标签
    tags_html = ""
    if args.keywords:
        kws = [k.strip() for k in args.keywords.split(",") if k.strip()]
        if len(kws) < 3 or len(kws) > 5:
            sys.exit(f"❌ --keywords 须 3~5 个词（逗号分隔），收到 {len(kws)} 个: {args.keywords}")
        tags_html = '<div class="tags">' + "".join(
            f'<span class="tag">{escape(k)}</span>' for k in kws
        ) + '</div>'
    layout = _pick_layout(args.layout, args.title)
    scheme = _pick_scheme(args.scheme, args.title)
    s = SCHEMES[scheme]
    # 多图布局：加载附加小图（collage-*）；单图布局忽略 --screenshots
    small_shots_b64 = []
    if layout in MULTI_SHOT_OPTIONS and args.screenshots:
        for p in args.screenshots.split(","):
            p = p.strip()
            if p and Path(p).exists():
                small_shots_b64.append(base64.b64encode(Path(p).read_bytes()).decode("ascii"))
    if layout in MULTI_SHOT_OPTIONS:
        if not small_shots_b64:
            # 无附加截图时用小图=大图（拼贴仍成立，只是同图重复，避免破版）
            small_shots_b64 = [screenshot_b64] * (3 if layout != "collage-h" else 4)
        html = BUILDERS[layout](s, title_html, tagline_html, desc_html, screenshot_b64, small_shots_b64, tags_html)
    else:
        html = BUILDERS[layout](s, title_html, tagline_html, desc_html, screenshot_b64, tags_html)

    # 公共特效注入（描边+投影+光泽，所有布局统一）
    html = inject_common_fx(html)

    # 计算文字区域 bbox（供 verify-glyphs.py 精确采样，避免自动定位猜坐标）
    # 覆盖全部布局（含 collage-* 多图布局）：文字元素统一用 .title/.tagline/.desc
    text_bbox = None
    with sync_playwright() as pw:
        browser = launch_browser(pw)
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.set_content(html, wait_until="networkidle")
        # 标题自适应：优先保持单行（nowrap + 微缩字号至 32px 下限）；
        # 32px 仍放不下则释放换行（white-space:normal），允许折行——比硬缩到 22px 更美观。
        # 短标题保持原字号单行；中等标题微缩；超长标题（≥12 字）自然折行不挤截图。
        page.evaluate(r"""() => {
            const titles = document.querySelectorAll('.title');
            for (const el of titles) {
                const parent = el.parentElement;
                const maxW = parent ? parent.clientWidth : window.innerWidth;
                let fs = parseFloat(getComputedStyle(el).fontSize) || 40;
                el.style.fontSize = fs + 'px';
                el.style.whiteSpace = 'nowrap';
                while (el.scrollWidth > maxW && fs > 32) {
                    fs -= 1;
                    el.style.fontSize = fs + 'px';
                }
                if (el.scrollWidth > maxW) {
                    // 32px 单行仍放不下 → 释放换行
                    el.style.whiteSpace = 'normal';
                    el.style.wordBreak = 'break-all';
                }
            }
        }""")
        text_bbox = page.evaluate(r"""() => {
            const els = document.querySelectorAll('.title, .tagline, .desc');
            let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
            for (const el of els) {
                const r = el.getBoundingClientRect();
                if (r.width === 0 && r.height === 0) continue;
                x0 = Math.min(x0, r.left);
                y0 = Math.min(y0, r.top);
                x1 = Math.max(x1, r.right);
                y1 = Math.max(y1, r.bottom);
            }
            if (!isFinite(x0)) return null;
            // 外扩 8px 防字形顶出边界
            return {
                x0: Math.max(0, Math.floor(x0) - 8),
                y0: Math.max(0, Math.floor(y0) - 8),
                x1: Math.min(1280, Math.ceil(x1) + 8),
                y1: Math.min(720, Math.ceil(y1) + 8),
            };
        }""")
        page.screenshot(path=args.out, type="png")
        browser.close()

    # 嵌入 tEXt 元数据 gal-text-bbox=x0,y0,x1,y1（PIL 重存，详见 verify-glyphs.py）
    try:
        if text_bbox:
            from PIL import Image
            from PIL.PngImagePlugin import PngInfo

            png = Image.open(args.out)
            info = PngInfo()
            info.add_text("gal-text-bbox",
                          f"{text_bbox['x0']},{text_bbox['y0']},{text_bbox['x1']},{text_bbox['y1']}")
            buf = BytesIO()
            png.save(buf, format="PNG", pnginfo=info, optimize=True)
            Path(args.out).write_bytes(buf.getvalue())
    except Exception as e:
        print(f"⚠️ 无法写入文字区域元数据（不影响封面生成）: {e}", file=sys.stderr)

    # 封面比例门禁（fail-closed）：画布必须 16:9（±0.02 容差）。
    # 输出恒为 PNG（page.screenshot type="png"），直接读 IHDR 宽高，零额外依赖。
    try:
        with open(args.out, "rb") as fh:
            head = fh.read(24)
        if head[:8] == b"\x89PNG\r\n\x1a\n":
            w, h = int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")
            if w > 0 and h > 0:
                ratio = w / h
                if abs(ratio - 16 / 9) > 0.02:
                    sys.exit(f"❌ 封面宽高比 {w}×{h}={ratio:.3f} 非 16:9（±0.02 容差）— 禁止发布。请检查 body/viewport 尺寸。")
    except Exception as e:
        sys.exit(f"❌ 无法校验封面尺寸 {args.out}: {e}")

    size = Path(args.out).stat().st_size
    print(f"✅ 封面已生成: {args.out} ({size} bytes, scheme={scheme}, layout={layout})")


if __name__ == "__main__":
    main()
