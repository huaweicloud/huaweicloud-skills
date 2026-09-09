#!/usr/bin/env python3
"""screenshot_guard.py — 截图前字形自检 + 兜底注入（核心防线，跨平台）

行为:
  - goto 用 domcontentloaded + 30s；等 fonts.ready 带 3s 竞速（防离线 @import 挂死）
  - 截图源 charset 门禁（fail-closed：非 UTF-8 即报错）
  - 字形自检（document.fonts.check/load）
  - emoji 像素级 tofu 检测（含 arm64 canvasTextBroken 回退）
  - 缺失字体族用 @font-face { src: local(兜底) } 原地重映射
  - 通过后写 screenshot-gate-ok 标记
  - 最后截图到 --out

用法:
  python screenshot_guard.py <appUrl> [选项]

选项:
  --required-file <f>   extract-fonts 输出（每行一个字体族）
  --required "A,B"      直接逗号分隔字体族列表
  --fallback "A=B,C=D"  缺失族→兜底族映射
  --out <png>           截图输出路径
  --quiet               静默模式
  -h, --help            显示本帮助

退出码: 0=成功; 1=字形/emoji 硬失败; 2=参数错误
"""

import argparse
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

SANS_FALLBACK = "Noto Sans CJK SC"
GENERIC = ["sans-serif", "serif", "monospace", "ui-monospace",
           "system-ui", "-apple-system", "BlinkMacSystemFont", "inherit"]

DEFAULT_REQUIRED = ["Outfit", "Inter", "Microsoft YaHei UI", "Microsoft YaHei",
                    "SFMono-Regular", "Cascadia Mono", "Roboto Mono", "Consolas"]
DEFAULT_FALLBACK = {
    "Inter": SANS_FALLBACK, "Outfit": SANS_FALLBACK,
    "Microsoft YaHei UI": SANS_FALLBACK, "Microsoft YaHei": SANS_FALLBACK,
    "SFMono-Regular": "DejaVu Sans Mono", "Cascadia Mono": "DejaVu Sans Mono",
    "Roboto Mono": "DejaVu Sans Mono", "Consolas": "DejaVu Sans Mono",
}

SAMPLES_CJK = "中文示例「汉字测试」（括号）㎡"
SAMPLES_LATIN = "The quick fox 0123"


def main():
    ap = argparse.ArgumentParser(
        prog="screenshot_guard.py",
        description="截图前字形自检 + 兜底注入（核心防线）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("appUrl", nargs="?", help="HTTP(S) URL（如 http://127.0.0.1:8099/index.html）")
    ap.add_argument("--required-file", default="", help="extract-fonts 输出（每行一个字体族）")
    ap.add_argument("--required", default="", help='直接逗号分隔字体族列表（如 "Inter,Outfit"）')
    ap.add_argument("--fallback", default="", help="缺失族→兜底族映射（如 A=B,C=D）")
    ap.add_argument("--out", default=str(Path(tempfile.gettempdir()) / "work-screenshot.png"), help="截图输出路径")
    ap.add_argument("--quiet", action="store_true", help="静默模式")
    args = ap.parse_args()

    if not args.appUrl:
        sys.exit("❌ 用法: python screenshot_guard.py <appUrl> [--required-file <fonts.txt>] [--required ...] [--out <png>]\n  运行 python screenshot_guard.py --help 查看完整用法。")
    if not re.match(r"^https?://", args.appUrl, re.I):
        sys.exit(f"❌ 首个参数必须是 HTTP(S) URL，不能是文件系统路径。\n  收到: {args.appUrl}\n  若你要截图本地文件，请先启动 HTTP 服务再传入其 URL。")

    # 解析字体需求
    required = None
    if args.required_file:
        required = [l.strip() for l in Path(args.required_file).read_text(encoding="utf-8").splitlines() if l.strip()]
    elif args.required:
        required = [s.strip() for s in args.required.split(",") if s.strip()]

    fallback = dict(DEFAULT_FALLBACK)
    if args.fallback:
        for kv in args.fallback.split(","):
            parts = kv.split("=", 1)
            if len(parts) == 2 and parts[0].strip() and parts[1].strip():
                fallback[parts[0].strip()] = parts[1].strip()

    quiet = args.quiet

    try:
        from playwright.sync_api import sync_playwright
        from browser_launch import launch_browser
    except ImportError as e:
        sys.exit(
            "❌ 缺少 Python 依赖 playwright（截图必需）。请先运行渲染前 preflight 自动补齐：\n"
            "   bash <skill>/scripts/preflight.sh   （或 Windows: powershell preflight.ps1）\n"
            "   或手动安装：python -m pip install playwright && python -m playwright install chromium\n"
            f"   原始错误: {e}"
        )

    with sync_playwright() as pw:
        browser = launch_browser(pw)
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.goto(args.appUrl, wait_until="domcontentloaded", timeout=30000)

        # 等 fonts.ready，带 3s 竞速
        try:
            page.evaluate("() => Promise.race([document.fonts.ready, new Promise(r => setTimeout(r, 3000))])")
        except Exception:
            pass

        # 页面字体自动探测
        page_families = page.evaluate("""(generic) => {
            const seen = new Set();
            for (const el of document.querySelectorAll('*')) {
                const fam = getComputedStyle(el).fontFamily || "";
                for (const token of fam.split(',')) {
                    const f = token.trim().replace(/^['"]|['"]$/g, "");
                    if (f && !generic.includes(f)) seen.add(f);
                }
            }
            return [...seen];
        }""", GENERIC)

        if required is None:
            required = page_families if page_families else list(DEFAULT_REQUIRED)
        targets = [f for f in required if f not in GENERIC]

        # charset 门禁
        page_charset = page.evaluate("() => document.characterSet || ''")
        if not re.search(r"utf-8", page_charset, re.I):
            browser.close()
            sys.exit(f'❌ 截图源页面字符集为 "{page_charset}"（非 UTF-8）——页面缺 <meta charset> 或被按 Latin-1 判读，截图必 mojibake。先跑 ensure-utf8 归一，或给页面加 <meta charset="UTF-8"> 后重试。')

        # 字形自检函数
        def probe(fam, text):
            return page.evaluate("""async ([fam, text]) => {
                const fontStr = `16px "${fam}", sans-serif`;
                try { await document.fonts.load(fontStr, text); } catch {}
                return document.fonts.check(fontStr, text);
            }""", [fam, text])

        # emoji 像素级检测
        emoji_result = page.evaluate(r"""async () => {
            const size = 32;
            const renderPixels = (ch) => {
                const c = document.createElement("canvas");
                c.width = c.height = size;
                const ctx = c.getContext("2d");
                ctx.font = "16px sans-serif";
                ctx.textBaseline = "top";
                ctx.fillText(ch, 4, 4);
                return ctx.getImageData(0, 0, size, size).data;
            };
            const notdefPixels = renderPixels("\uFFFF");
            const isTofu = (ch) => {
                const pixels = renderPixels(ch);
                let diff = 0;
                for (let i = 0; i < pixels.length; i += 4) {
                    diff += Math.abs(pixels[i]     - notdefPixels[i])
                          + Math.abs(pixels[i + 1] - notdefPixels[i + 1])
                          + Math.abs(pixels[i + 2] - notdefPixels[i + 2]);
                }
                return diff < 50;
            };
            const core = ["😀", "🚀", "🎮", "🛒", "🧩"];
            const extended = ["🫡", "🧑\u200D💻"];
            const pageEmoji = new Set();
            for (const el of document.querySelectorAll('*')) {
                const text = (el.textContent || "") + (el.value || "");
                for (const ch of text) {
                    const cp = ch.codePointAt(0);
                    if (cp >= 0x1F000 && cp <= 0x1FAFF || (cp >= 0x2600 && cp <= 0x27BF)) {
                        pageEmoji.add(ch);
                    }
                }
            }
            const asciiTofu = isTofu("A");
            const canvasTextBroken = asciiTofu;
            const coreFail = canvasTextBroken ? [] : core.filter(ch => isTofu(ch));
            const extFail = canvasTextBroken ? [] : extended.filter(ch => isTofu(ch));
            const pageFail = canvasTextBroken ? [] : [...pageEmoji].filter(ch => isTofu(ch)).slice(0, 5);
            let fontsCheckFallback = null;
            if (canvasTextBroken) {
                const emojiFontFamilies = ["Noto Color Emoji", "NotoEmoji", "Apple Color Emoji", "Segoe UI Emoji"];
                fontsCheckFallback = [];
                for (const fam of emojiFontFamilies) {
                    const fontStr = `16px "${fam}"`;
                    try { await document.fonts.load(fontStr, "😀"); fontsCheckFallback.push({ family: fam, available: document.fonts.check(fontStr, "😀") }); }
                    catch { fontsCheckFallback.push({ family: fam, available: false }); }
                }
            }
            return { coreFail, extFail, pageFail, pageEmojiCount: pageEmoji.size, canvasTextBroken, fontsCheckFallback };
        }""")

        if not quiet:
            print(f"emoji 校验: 核心={'OK' if len(emoji_result['coreFail']) == 0 else 'FAIL(' + ''.join(emoji_result['coreFail']) + ')'}"
                  f" | 扩展={'OK' if len(emoji_result['extFail']) == 0 else 'WARN(' + ''.join(emoji_result['extFail']) + ')'}"
                  + (f" | 页面emoji={emoji_result['pageEmojiCount']}" if emoji_result['pageEmojiCount'] > 0 else "")
                  + (" | canvasTextBroken=true" if emoji_result['canvasTextBroken'] else ""))

        if emoji_result['canvasTextBroken']:
            fc = emoji_result.get('fontsCheckFallback')
            if not quiet:
                if fc and any(f['available'] for f in fc):
                    found = ", ".join(f['family'] for f in fc if f['available'])
                    print(f"⚠️ canvas 文字渲染整体不可用（arm64 headless Chromium 已知限制）。document.fonts.check 回退检测: 检出 emoji 字体族 [{found}]。截图应正常（Playwright 走浏览器渲染管线，非 canvas），emoji 校验已跳过。")
                else:
                    tried = " ".join(f"{f['family']}:❌" for f in fc) if fc else "(未检测)"
                    print(f"⚠️ canvas 文字渲染不可用且 document.fonts.check 未检出任何 emoji 字体族（{tried}）。建议安装 Noto Color Emoji: bash <skill>/scripts/download-noto-color-emoji.sh 后重启浏览器。Playwright 截图仍会尝试渲染，但 emoji 可能显示为方块。")
        elif len(emoji_result['coreFail']) > 0:
            browser.close()
            sys.exit(f"❌ 系统缺核心 emoji 字形（{''.join(emoji_result['coreFail'])}）——先装 Noto Color Emoji: bash <skill>/scripts/download-noto-color-emoji.sh 后重启浏览器")

        if len(emoji_result['extFail']) > 0 and not quiet:
            print(f"⚠️ 扩展 emoji 测宽失败（{''.join(emoji_result['extFail'])}）——Chromium HarfBuzz 对 CBDT 彩色 emoji (Emoji 13.0+) 的 canvas measureText 不稳定，字体 cmap 实际有该码点。不影响截图渲染，仅作警告。")
        if len(emoji_result['pageFail']) > 0 and not quiet:
            print(f"⚠️ 页面使用的部分 emoji 测宽异常（{''.join(emoji_result['pageFail'])}）——可能渲染为方块，建议检查截图效果。")

        # CJK 字形自检
        missing = []
        for fam in targets:
            if not (probe(fam, SAMPLES_CJK) or probe(fam, SAMPLES_LATIN)):
                missing.append(fam)
        if not quiet:
            print("缺失字体族:", ", ".join(missing) if missing else "无")

        # 注入 @font-face 重映射
        if missing:
            css_parts = []
            for f in missing:
                fb = fallback.get(f, SANS_FALLBACK)
                css_parts.append(f'@font-face {{ font-family: "{f}"; src: local("{fb}"); font-display: swap; }}')
            css = "\n".join(css_parts)
            page.add_style_tag(content=css)
            still_missing = []
            for fam in missing:
                if not (probe(fam, SAMPLES_CJK) or probe(fam, SAMPLES_LATIN)):
                    still_missing.append(fam)
            if still_missing:
                browser.close()
                sys.exit(f"❌ 兜底注入后仍缺字形: {', '.join(still_missing)}——请先完成兜底字体套件安装并重启浏览器")
            if not quiet:
                print("✅ 兜底注入完成，字形自检通过")

        # 写 screenshot-gate-ok 标记
        marker_path = Path(tempfile.gettempdir()) / "screenshot-gate-ok"
        emoji_status = "ok"
        if emoji_result['canvasTextBroken']:
            fc = emoji_result.get('fontsCheckFallback')
            if fc and any(f['available'] for f in fc):
                emoji_status = "skip(canvas-broken,fonts-ok)"
            else:
                emoji_status = "skip(canvas-broken,fonts-missing)"
        elif len(emoji_result['coreFail']) > 0 or len(emoji_result['extFail']) > 0:
            emoji_status = "missing"

        marker_content = (
            f"ok=true\n"
            f"gate=screenshot-guard\n"
            f"charset={page_charset}\n"
            f"glyphs=ok\n"
            f"emoji={emoji_status}\n"
            f"missing_fonts={','.join(missing) if missing else 'none'}\n"
            f"ts={time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())}\n"
        )
        try:
            marker_path.write_text(marker_content, encoding="utf-8")
        except Exception as e:
            print(f"❌ 无法写 screenshot-gate-ok 标记: {e}", file=sys.stderr)

        # 图标/Web 字体加载失败检测
        failed_fonts = page.evaluate("""() =>
            performance.getEntriesByType("resource")
                .filter(e => /\\.(woff2?|ttf|otf|eot)$/i.test(e.name) && (e.responseStatus >= 400 || e.responseStatus === 0))
                .map((e) => e.name.split("/").pop())
        """)
        if failed_fonts and not quiet:
            print(f"⚠️ 检测到图标/Web 字体加载失败: {', '.join(failed_fonts)}\n   可能显示为方块。请确认本地静态资源可访问。")

        page.screenshot(path=args.out, full_page=False)
        browser.close()
        print(f"✅ 截图完成: {args.out}")


if __name__ == "__main__":
    main()
