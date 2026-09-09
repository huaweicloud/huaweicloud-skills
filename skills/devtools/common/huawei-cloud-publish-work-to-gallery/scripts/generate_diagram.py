#!/usr/bin/env python3
"""generate_diagram.py — 可复用的架构图/图表生成器

功能：接受 HTML 文件，用 Playwright 渲染并截图为 PNG。
      支持 fullPage 截图（高度自适应）和固定视口截图。

用法:
  python generate_diagram.py --html <file> --out <path> [--width 1280] [--height 800] [--fullpage]

选项:
  --html <file>       HTML 文件路径（必填）
  --out <path>        输出 PNG 路径（必填）
  --width <number>    视口宽度（默认 1280）
  --height <number>   视口高度（默认 800，--fullpage 时忽略）
  --fullpage          截取完整页面高度（默认开启）
  --no-fullpage       仅截取视口范围
  -h, --help          显示帮助

退出码: 0=成功; 1=运行时错误; 2=参数错误
"""

import argparse
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser(
        prog="generate_diagram.py",
        description="可复用的架构图/图表生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--html", required=True, help="HTML 文件路径")
    ap.add_argument("--out", required=True, help="输出 PNG 路径")
    ap.add_argument("--width", type=int, default=1280, help="视口宽度（默认 1280）")
    ap.add_argument("--height", type=int, default=800, help="视口高度（默认 800，--fullpage 时忽略）")
    fullpage_group = ap.add_mutually_exclusive_group()
    fullpage_group.add_argument("--fullpage", action="store_true", default=True, help="截取完整页面高度（默认开启）")
    fullpage_group.add_argument("--no-fullpage", action="store_false", dest="fullpage", help="仅截取视口范围")
    args = ap.parse_args()

    html_path = Path(args.html)
    if not html_path.exists():
        sys.exit(f"❌ HTML 文件不存在: {html_path}")

    html_content = html_path.read_text(encoding="utf-8")

    try:
        from playwright.sync_api import sync_playwright
        from browser_launch import launch_browser
    except ImportError as e:
        sys.exit(
            "❌ 缺少 Python 依赖 playwright（图表生成必需）。请先运行渲染前 preflight 自动补齐：\n"
            "   bash <skill>/scripts/preflight.sh   （或 Windows: powershell preflight.ps1）\n"
            "   或手动安装：python -m pip install playwright && python -m playwright install chromium\n"
            f"   原始错误: {e}"
        )

    text_bbox = None
    with sync_playwright() as pw:
        browser = launch_browser(pw)
        page = browser.new_page(viewport={"width": args.width, "height": args.height})
        page.set_content(html_content, wait_until="networkidle")

        view_h = args.height
        if args.fullpage:
            view_h = page.evaluate("""() => {
                const body = document.body;
                let maxBottom = 0;
                for (const el of body.querySelectorAll('*')) {
                    const r = el.getBoundingClientRect();
                    if (r.bottom > maxBottom) maxBottom = r.bottom;
                }
                let lastMargin = 0;
                const kids = body.children;
                if (kids.length) {
                    const last = kids[kids.length - 1];
                    const cs = getComputedStyle(last);
                    const r = last.getBoundingClientRect();
                    lastMargin = parseFloat(cs.marginBottom) || 0;
                    if (r.bottom + lastMargin > maxBottom) maxBottom = r.bottom + lastMargin;
                }
                return Math.min(Math.ceil(Math.max(body.scrollHeight, maxBottom)), 20000);
            }""")
            page.set_viewport_size({"width": args.width, "height": view_h})

        # 计算所有可见文字元素的联合 bbox（供 verify-glyphs.py 精确采样，避免自动定位猜坐标）
        # fullpage 场景坐标按绝对位置（rect.top + scrollY）换算到截图坐标系
        text_bbox = page.evaluate(r"""() => {
            const all = document.querySelectorAll('body *');
            const sx = window.scrollX, sy = window.scrollY;
            let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
            for (const el of all) {
                const cs = getComputedStyle(el);
                if (cs.display === 'none' || cs.visibility === 'hidden') continue;
                const txt = (el.textContent || '').trim();
                if (!txt) continue;
                const r = el.getBoundingClientRect();
                if (r.width < 4 || r.height < 4) continue;
                const ax0 = r.left + sx, ay0 = r.top + sy, ax1 = r.right + sx, ay1 = r.bottom + sy;
                // 只统计“叶子文字块”（无文本子元素），避免父子重复计入
                const hasTextKid = Array.from(el.children).some(k => (k.textContent || '').trim());
                if (!hasTextKid) {
                    x0 = Math.min(x0, ax0); y0 = Math.min(y0, ay0);
                    x1 = Math.max(x1, ax1); y1 = Math.max(y1, ay1);
                }
            }
            if (!isFinite(x0)) return null;
            return { x0: Math.max(0, Math.floor(x0) - 6), y0: Math.max(0, Math.floor(y0) - 6),
                     x1: Math.ceil(x1) + 6, y1: Math.ceil(y1) + 6 };
        }""")

        page.screenshot(path=args.out, full_page=False)
        browser.close()

    # 嵌入 tEXt 元数据 gal-text-bbox=x0,y0,x1,y1
    try:
        if text_bbox:
            from io import BytesIO
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
        print(f"⚠️ 无法写入文字区域元数据（不影响图表生成）: {e}", file=sys.stderr)

    size = Path(args.out).stat().st_size
    h_desc = f"auto(内容高度{view_h})" if args.fullpage else args.height
    print(f"✅ 图表已生成: {args.out} ({size} bytes, {args.width}×{h_desc})")


if __name__ == "__main__":
    main()
