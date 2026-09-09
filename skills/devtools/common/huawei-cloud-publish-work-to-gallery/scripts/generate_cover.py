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
  --scheme <name>       色调：auto(默认,按标题哈希选色) / purple / blue / green / dark / warm / black-gold / vibrant-orange / warm-yellow
  --layout <name>       布局：auto(默认,按标题哈希) / classic / split / hero / showcase
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
}

LAYOUTS = ["auto", "classic", "split", "hero", "showcase", "polaroid", "blur", "topbar",
           "collage-h", "collage-v", "collage-grid"]
_AUTO_OPTIONS = ["classic", "split", "hero", "showcase", "polaroid", "blur", "topbar"]
MULTI_SHOT_OPTIONS = ["collage-h", "collage-v", "collage-grid"]
SCHEME_CHOICES = ["auto"] + list(SCHEMES.keys())


def _pick_layout(layout_arg, title):
    if layout_arg != "auto":
        return layout_arg
    return _AUTO_OPTIONS[zlib.crc32(title.encode("utf-8")) % len(_AUTO_OPTIONS)]


def _pick_scheme(scheme_arg, title):
    """--scheme auto 时按标题哈希选色，避免所有封面清一色同一色调。"""
    if scheme_arg != "auto":
        return scheme_arg
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
    ap.add_argument("--scheme", default="auto", choices=SCHEME_CHOICES, help="色调：auto(默认,按标题哈希选色) / purple / blue / green / dark / warm / black-gold / vibrant-orange / warm-yellow")
    ap.add_argument("--layout", default="auto", choices=LAYOUTS, help="布局模板（默认 auto，按标题哈希选择）")
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
            "   bash <skill>/scripts/preflight.sh   （或 Windows: powershell preflight.ps1）\n"
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

    # 计算文字区域 bbox（供 verify-glyphs.py 精确采样，避免自动定位猜坐标）
    # 覆盖全部布局：classic/split/hero/showcase 的文字元素统一用 .title/.tagline/.desc
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

    size = Path(args.out).stat().st_size
    print(f"✅ 封面已生成: {args.out} ({size} bytes, scheme={scheme}, layout={layout})")


if __name__ == "__main__":
    main()
