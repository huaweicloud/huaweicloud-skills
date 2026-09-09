#!/usr/bin/env python3
# verify-glyphs.py <image> —— 像素级字形终检（fail-stop，最终防线）
#
# 背景:
#   测宽法对 CJK 不可靠（CJK 真实字形与 tofu 的 advance width 都是 1em），
#   截图后须以「像素墨水对比」为主判据：目标区域（应渲染真实 CJK 的文本行）
#   的墨水量应显著多于 DejaVu(tofu，缺 CJK) 对照行。差异小 ≈ 疑似只渲染了豆腐块。
#
# 用法:
#   python3 verify-glyphs.py <image>                          # 自动定位（封面/图表通用）
#   python3 verify-glyphs.py <image> --y-target 125 --y-control 5   # 显式坐标（对照行须指向真实空白区）
#   python3 verify-glyphs.py <image> --probe                   # 探测模式：遍历 y 打印各行墨量比值
#   python3 verify-glyphs.py <image> --quiet                   # 静默模式：仅输出通过/失败一行
#   python3 verify-glyphs.py --help                            # 查看完整用法
#
# 说明:
#   generate_cover.py / generate_diagram.py 生成图片时会嵌入 tEXt 元数据
#   `gal-text-bbox=x0,y0,x1,y1`（文字区域 bbox）。本脚本优先读取该元数据，
#   直接在文字区域采样目标行、并在 bbox 外自动找空白对照行，无需猜默认坐标，
#   避免“默认采样位置落在非文字区 → ratio=0”的误判。
#   旧图/无元数据图仍走内置自动定位：(自动)按墨带定位、probe 扫描兜底。
#
#   若未显式提供 --y-target/--y-control，本脚本会自动在图中定位「文字行墨迹带」，
#   取墨量最高的两条带分别作为目标行与对照行。脚本自动适配明暗背景（`build_ink_mask`：
#   亮底图数暗像素、暗底图数亮像素），白色/浅色底图表也可自动校验；仅同一图明暗混排或
#   自动定位失败时，会扫描全图找「墨量最小的 height 行窗口」作为空白对照，再输出 probe
#   扫描结果并推荐坐标——顶部固定取 y=5 仅当该处确为空白（无页眉/标题）时才可靠。
#
# exit 0 = 通过；exit 1 = 疑似未渲染真实字形（fail-closed，禁止继续合成/发布）。
#         --probe 模式 exit 0（仅输出信息，不判定）。

import argparse
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

try:
    import numpy as np
    from PIL import Image
except ImportError:
    np = None  # --help 不需要 numpy，main_cli 中实际使用时再检查


QUIET = False

def qprint(*args, **kwargs):
    """静默模式下不输出的诊断打印（最终结果行始终用 print）。"""
    if not QUIET:
        print(*args, **kwargs)


def build_ink_mask(arr):
    """构造墨迹判定掩码，自动适配明暗背景及彩色背景。

    通过采样图像边缘像素估计背景色，再计算每个像素与背景色的 L1 色彩距离。
    与背景色差异显著的像素即为"墨迹"（文字/图形），无论文字比背景更亮还是更暗。
    这解决了原实现在深色背景+深色文字场景下的误报问题
    （如紫色封面背景上的深色标题文字，原逻辑按 mean<128 走 arr>200 分支，
    但文字像素也未超过 200 → 全图零墨迹 → ratio=0 误判为豆腐块）。
    """
    h, w = arr.shape[:2]
    # 采样四边各 5 行/列像素，取中位数估计背景色（robust to 边缘文字/装饰）
    border = np.concatenate([
        arr[0:min(5, h), :, :].reshape(-1, 3),
        arr[max(0, h - 5):, :, :].reshape(-1, 3),
        arr[:, 0:min(5, w), :].reshape(-1, 3),
        arr[:, max(0, w - 5):, :].reshape(-1, 3),
    ])
    bg_color = np.median(border, axis=0).astype(np.float64)

    # L1 色彩距离：|r-br| + |g-bg| + |b-bb|
    dist = np.abs(arr.astype(np.float64) - bg_color).sum(axis=2)

    # 动态阈值：距离分布的 85 百分位 × 0.35，下限 30
    # 纯背景无文字时大部分像素距离≈0，阈值下限 30 不会误判；
    # 有文字时文字像素距离显著高于背景像素，能正确分离。
    threshold = max(30.0, float(np.percentile(dist, 85)) * 0.35)
    return dist > threshold


def row_has_ink(mask, x0, x1):
    return mask[:, x0:x1].any(axis=1)


def find_bands(mask, x0, x1, pad=12, min_h=8, max_density=0.6):
    """逐行统计墨迹，合并为连续带；返回 [(y_top, y_bot, ink_amt, density)]。

    高密度带（实心彩色填充背景，density >= max_density）降权到末尾。
    """
    h = mask.shape[0]
    w = max(1, x1 - x0)
    marked = row_has_ink(mask, x0, x1).astype(int)
    bands, i = [], 0
    while i < h:
        if marked[i] == 0:
            i += 1
            continue
        j = i
        while j < h:
            if marked[j] == 1:
                j += 1
            else:
                k = j
                while k < h and marked[k] == 0:
                    k += 1
                if k - j > pad:
                    break
                j = k
        ink_amt = int(mask[i:j, x0:x1].sum())
        if j - i >= min_h:
            density = ink_amt / max(1, (j - i) * w)
            bands.append((i, j, ink_amt, density))
        i = j + 1
    bands.sort(key=lambda b: (b[3] >= max_density, -b[2]))
    return bands


def ink(mask, y0, y1, x0, x1):
    """窗口内「墨像素总数」（非行数）。

    原实现 `any(axis=1).sum()` 按行判定：x 范围内只要有 1 个像素超阈值即整行算墨，
    截图中大量鲜艳像素会把阈值抬高，纯背景区每行混入个别离群像素 → 空白行也被判墨
    → 目标/对照行墨量恒等 → ratio=0 误报（实测 dark 截图 showcase 布局 58/60 vs 60）。
    改用像素计数：个别离群像素只贡献 1~2 像素，空白区与文字行墨量差异仍巨大。
    """
    return int(mask[y0:y1, x0:x1].sum())


def long_run_detect(mask, y0, y1, x0, x1, min_long=8):
    """墨段法豆腐块检测（适配小字号，弥补 hollow_ratio 的字号盲区）。

    豆腐块（空心方框）的左右边框在行向投影上是多段「长度≈字符高的长墨段」，
    且**等距重复**（每字符两段）；真实 CJK 字符笔画零散，横向几乎无长墨段。
    实测（单字符高窗口）各字号可分性：

      | 字号 | tofu 长墨段 | normal 长墨段 |
      |------|------------|--------------|
      | 64px | 15         | 4            |
      | 40px | 23         | 5            |
      | 28px | 30         | 5            |
      | 20px | 37         | 4            |
      | 14px | 46         | 1            |

    注：窗口须为**单个文字行高**（约 1~1.2×字号）。若传入整个 bbox（含多行/底部
    装饰线），横向长条会干扰。故先按行墨量找「墨最密的连续带」近似单行，再做墨段。

    返回 True=豆腐块；False/None=无。
    """
    hgt = y1 - y0
    if hgt < 10 or (x1 - x0) < 10:
        return None
    # 去掉全空白行，取文字实际行高（替代外部传的单行窗高，兼容大字/小字）
    row_ink = mask[y0:y1, x0:x1].sum(axis=1)
    active_rows = np.where(row_ink > 0)[0]
    if len(active_rows) == 0:
        return None
    lo, hi = int(active_rows[0]), int(active_rows[-1]) + 1
    use_h = hi - lo
    if use_h < 8:
        return None
    band_h = min(use_h, 70)  # 单行文字带高（≤70px 防多行粘连）
    threshold = int(band_h * 0.6)
    # 列向投影（该带内任一行的墨 → 该列算墨）
    col_ink = mask[y0 + lo:y0 + hi, x0:x1].any(axis=0).astype(int)
    long_count = 0
    i = 0
    n = len(col_ink)
    while i < n:
        if col_ink[i] == 1:
            j = i
            while j < n and col_ink[j] == 1:
                j += 1
            if (j - i) >= threshold:
                long_count += 1
            i = j
        else:
            i += 1
    if long_count >= min_long:
        return True
    return False


def hollow_ratio(mask, y0, y1, x0, x1):
    """检测豆腐块（空心方框）的空心度判据：文字实际占据区中心 1/3×1/3 墨密度 / 整窗口墨密度。

    真实 CJK 字符笔画贯穿，文字中心区墨密度 ≈ 整体（比值 ≥1）；
    豆腐块（缺字字形）是空心矩形边框，中心区墨量远低于边框（比值 <1）。
    已验证：真实封面（44 张）+ collage 布局全部 ≥0.8，豆腐块合成图 0.688。

    横向排布（collage 头部/topbar）的 bbox 很宽，直接取 bbox 中心会落到标题右侧
    的空白/tagline 区 → 误报。故先按列墨量定位「文字实际占据的 x 区间」，再在该
    区间内取中心 1/3——豆腐块在此中心仍是空心，真实文字笔画贯穿。

    返回 None 表示窗口墨过稀无法判定（走空白判定保底）。
    """
    hgt = y1 - y0
    if hgt < 12 or (x1 - x0) < 12:
        return None
    full = mask[y0:y1, x0:x1]
    fd = float(full.mean())
    if fd < 0.01:
        return None
    # 定位文字实际 x 区间：列墨量 > 0 的连续范围（忽略零墨列）
    col = full.sum(axis=0)
    active = col > 0
    if not active.any():
        return None
    xs = np.where(active)[0]
    ax0, ax1 = int(xs.min()) + x0, int(xs.max()) + x0 + 1
    aw = ax1 - ax0
    if aw < 12:
        return None
    cy0, cy1 = y0 + hgt // 3, y0 + 2 * hgt // 3
    cx0, cx1 = ax0 + aw // 3, ax0 + 2 * aw // 3
    if cx1 <= cx0 or cy1 <= cy0:
        return None
    cd = float(mask[cy0:cy1, cx0:cx1].mean())
    return cd / fd


def find_blank_control(mask, x0, x1, height, step=5):
    """自动找一条「纯空白窗口」作为对照：窗口 [y, y+height) 的墨量最小。

    顶部固定取 y=5 作对照在「满幅底色 + 顶部有标题/页眉」的图表上不可靠
    （y=5 可能落在标题文字上 → 目标行与对照行墨量接近 → ratio 恒 < 2 误判 tofu）。
    注意要用与 ink() 相同的窗口口径（height 行），仅找「单行最小」仍可能让窗口
    边缘滑入相邻文本（如 y=0 行空白但窗口 0..height 覆盖顶部标题）。
    """
    h = mask.shape[0]
    best_y, best_ink = 0, None
    for y in range(0, max(1, h - height), step):
        win_ink = ink(mask, y, y + height, x0, x1)
        if best_ink is None or win_ink < best_ink:
            best_ink, best_y = win_ink, y
    qprint(f"（自动定位对照行）y={best_y} 墨量={best_ink}")
    return best_y


def find_blank_control_outside(mask, x0, x1, height, avoid_lo, avoid_hi, step=5):
    """全图范围内、与 [avoid_lo, avoid_hi) 不重叠的最小墨量窗口。

    用于 bbox 采样：目标窗口取自 bbox 内最大墨带，对照窗口必须与目标窗口
    无重叠（窗口 [y, y+height) 与避让区间 [lo, hi) 不相交），避免对照行切入
    文字区导致目标与对照墨量接近 → ratio < 阈值误判。
    """
    h = mask.shape[0]
    best_y, best_ink = None, None
    for y in range(0, max(1, h - height), step):
        win_lo, win_hi = y, y + height
        if win_hi > avoid_lo and win_lo < avoid_hi:
            continue
        win_ink = ink(mask, y, y + height, x0, x1)
        if best_ink is None or win_ink < best_ink:
            best_ink, best_y = win_ink, y
    if best_y is not None:
        qprint(f"（bbox 对照行）y={best_y} 墨量={best_ink}（避让目标 {avoid_lo}..{avoid_hi}）")
    return best_y


def probe_scan(mask, x0, x1, height, y_control, step=10):
    """遍历 y 坐标打印各行墨量比值，辅助定位纯背景上的中文文本行。"""
    h = mask.shape[0]
    b_ctrl = ink(mask, y_control, y_control + height, x0, x1)
    qprint(f"（探测模式）对照行 y={y_control} 墨量={b_ctrl} | 步长={step}")
    qprint(f"{'y':>6}  {'墨量':>6}  {'ratio':>8}")
    best_y, best_ratio = y_control, 0.0
    for y in range(0, max(1, h - height), step):
        a = ink(mask, y, y + height, x0, x1)
        # 方向性比值：目标行（真实 CJK 文本）墨量必须显著多于对照行（空白背景）。
        # 若 a <= b_ctrl（目标行为空/与背景无差），比值记 0，避免空行被当作"目标"假通过。
        r = (a / max(b_ctrl, 1)) if a > b_ctrl else 0.0
        if r > best_ratio:
            best_y, best_ratio = y, r
        flag = " ★" if r >= 2.0 else ""
        qprint(f"{y:>6}  {a:>6}  {r:>8.2f}{flag}")
    qprint(f"\n推荐: --y-target {best_y} --y-control {y_control}（ratio={best_ratio:.2f}）")
    return best_y, best_ratio


def main_cli():
    ap = argparse.ArgumentParser(
        prog="verify-glyphs.py",
        description="像素级字形终检: 比对目标 CJK 文本行与对照行的墨量，差异过小即疑似豆腐块（fail-stop）。",
        epilog=(
            "示例:\n"
            "  封面/图表（自动定位）: python3 verify-glyphs.py cover.png\n"
            "  显式坐标（对照行指向真实空白区）: python3 verify-glyphs.py arch.png --y-target 125 --y-control 5\n"
            "  探测合适 y 坐标:    python3 verify-glyphs.py arch.png --probe\n"
            "\n"
            "坐标选择: --y-target 指向纯暗背景上的中文文本行（避开彩色方框）；\n"
            "          --y-control 指向图片空白区（顶部有页眉/标题时不要用 y=5，让脚本自动定位或显式指定）。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("image", nargs="?", help="待校验图片路径（PNG/JPEG 等）")
    ap.add_argument("--y-target", type=int, default=None,
                    help="目标行（含中文文本）的顶部 y 坐标；省略则自动定位")
    ap.add_argument("--y-control", type=int, default=None,
                    help="对照行（无文本/空白）的顶部 y 坐标；省略则自动定位")
    ap.add_argument("--height", type=int, default=50, help="行高窗口（默认 50）")
    # 默认 x 范围全图宽，覆盖所有文字区域。
    ap.add_argument("--x0", type=int, default=0, help="x 起始（默认 0）")
    ap.add_argument("--x1", type=int, default=None, help="x 结束（默认全图宽）")
    ap.add_argument("--min-ratio", type=float, default=2.0,
                    help="目标与对照的最低墨量比值阈值（max/min < 此值即疑似 tofu，默认 2.0）")
    ap.add_argument("--max-density", type=float, default=0.6,
                    help="自动定位时剔除实心彩色填充带的密度阈值（默认 0.6；越高越宽松）")
    ap.add_argument("--probe", action="store_true",
                    help="探测模式: 遍历 y 坐标打印各行墨量比值，辅助定位（不判定通过/失败）")
    ap.add_argument("--quiet", action="store_true",
                    help="静默模式: 仅输出最终通过/失败一行，抑制诊断扫描表（用于自动化流程减少 token 消耗）")
    args = ap.parse_args()

    global QUIET
    QUIET = args.quiet

    if not args.image:
        ap.print_help()
        sys.exit(2)

    if np is None:
        print("❌ 缺 numpy/PIL——请运行: pip install numpy pillow", file=sys.stderr)
        sys.exit(1)

    try:
        arr = np.array(Image.open(args.image).convert("RGB"))
    except Exception as e:
        print(f"❌ 无法读取图片 {args.image}: {e}", file=sys.stderr)
        sys.exit(1)

    # 读取生成脚本嵌入的 tEXt 元数据 gal-text-bbox=x0,y0,x1,y1；
    # 命中则直接在文字区域采样（目标行=bbox 顶部，窗口高度=bbox 高），不再猜默认坐标。
    text_bbox = None
    try:
        from PIL import Image as _Img
        _bbox_str = _Img.open(args.image).info.get("gal-text-bbox", "")
        if _bbox_str and "," in _bbox_str:
            bx0, by0, bx1, by1 = (int(v) for v in _bbox_str.split(","))
            if 0 <= bx0 < bx1 and 0 <= by0 < by1 and by1 - by0 >= 10:
                text_bbox = (bx0, by0, bx1, by1)
                qprint(f"（元数据 bbox）文字区域 [{bx0},{by0}]-[{bx1},{by1}]")
    except Exception:
        pass

    mask = build_ink_mask(arr)
    h = mask.shape[0]
    x0 = max(0, min(args.x0, mask.shape[1]))
    x1 = mask.shape[1] if args.x1 is None else max(args.x0 + 1, min(args.x1, mask.shape[1]))

    # ---- 探测模式: 遍历 y 打印比值，不判定 ----
    if args.probe:
        y_ctrl = args.y_control if args.y_control is not None else find_blank_control(mask, x0, x1, args.height)
        probe_scan(mask, x0, x1, args.height, y_ctrl)
        sys.exit(0)

    # ---- 用生成脚本嵌入的 bbox 精确采样（优先级最高，解决“默认坐标猜不到文字区”导致 ratio=0）----
    bbox_resolved = False
    if text_bbox is not None and args.y_target is None and args.y_control is None:
        bx0, by0, bx1, by1 = text_bbox
        bx0 = max(bx0, x0); bx1 = min(bx1, x1)
        bb_h = min(max(10, by1 - by0), 60)  # 目标行窗口取 10~60px，避免整页文字带被当“一行”
        # 目标行：bbox 内墨量最大的窗口（滑动扫描）
        best_t, best_ink_t = None, 0
        for yy in range(by0, max(by0 + 1, by1 - bb_h + 1), 5):
            ink_t = ink(mask, yy, yy + bb_h, bx0, bx1)
            if ink_t > best_ink_t:
                best_ink_t, best_t = ink_t, yy
        # 对照行：bbox 列范围内（不含右侧截图区）、与【目标窗口自身】无重叠的最小墨窗口
        # （仅避让目标窗口而非整个 bbox：bbox 常覆盖整页文字带，全避让会无对照可找 → 回落自动定位触发重试）
        y_c = None
        if best_t is not None:
            y_c = find_blank_control_outside(mask, bx0, bx1, bb_h, best_t, best_t + bb_h)
        if best_t is not None and y_c is not None and best_ink_t >= 200:
            y_t, a, b = best_t, best_ink_t, ink(mask, y_c, y_c + bb_h, bx0, bx1)
            # 豆腐块检测：真实 CJK 笔画贯穿中心（比值≥0.8），豆腐块空心方框中心稀疏（<0.8）
            holl_ratio = hollow_ratio(mask, y_t, y_t + bb_h, bx0, bx1)
            if holl_ratio is not None and holl_ratio < 0.8:
                print(f"❌ 疑似豆腐块：文字区域呈空心矩形（中心墨密度/整体墨密度={holl_ratio:.2f}<0.8）。", file=sys.stderr)
                print("   请检查字体是否丢失/字形缺失——真实 CJK 笔画应贯穿字符中心。", file=sys.stderr)
                sys.exit(1)
            if holl_ratio is not None:
                qprint(f"（豆腐块检测）中心/整体墨密度比={holl_ratio:.2f}")
            # 墨段法小字豆腐块检测：对整个 bbox 文字带扫（涵盖 tagline/desc 等小字号），
            # 空心方框的左右边框形成长墨段（≥8 段），真实汉字笔画零散无长段
            ld = long_run_detect(mask, by0, by1, bx0, bx1)
            if ld:
                print("❌ 疑似豆腐块：文字区域存在多个长直框线（空心矩形边框特征，≥8 段）——多为小字号缺字字形。", file=sys.stderr)
                print("   请检查字体是否丢失/字形缺失，或调紧凑标题/正文的字体。", file=sys.stderr)
                sys.exit(1)
            bbox_resolved = True
            qprint(f"（bbox 采样）目标 y≈{y_t} 墨量={a} | 对照 y≈{y_c} 墨量={b} | 窗口高={bb_h}")
        else:
            text_bbox = None  # bbox 内无明显文字或找不到合理对照，回落自动定位

    if not bbox_resolved and args.y_target is not None and args.y_control is not None:
        y_t, y_c = args.y_target, args.y_control
        a = ink(mask, y_t, y_t + args.height, x0, x1)
        b = ink(mask, y_c, y_c + args.height, x0, x1)
        qprint(f"（显式坐标）目标 y≈{y_t} 墨量={a} | 对照 y≈{y_c} 墨量={b}")
    if not bbox_resolved and args.y_target is None and args.y_control is None:
        bands = find_bands(mask, x0, x1, max_density=args.max_density)
        bands = [b for b in bands if b[2] >= 10]
        if len(bands) >= 2:
            y_t = bands[0][0]; a = ink(mask, y_t, y_t + args.height, x0, x1)
            y_c = bands[1][0]; b = ink(mask, y_c, y_c + args.height, x0, x1)
            qprint(f"（自动定位）目标行 y≈{y_t} 墨量={a} | 对照行 y≈{y_c} 墨量={b}")
        else:
            # 墨迹带 < 2 条（如大块亮截图与文字同属一条带）→ 走 probe 自动定位
            qprint(f"（自动定位）仅找到 {len(bands)} 条墨迹带，改用 probe 扫描最佳坐标...")
            best_ctrl = find_blank_control(mask, x0, x1, args.height)
            best_y, best_ratio = probe_scan(mask, x0, x1, args.height, best_ctrl)
            if best_ratio >= args.min_ratio:
                a = ink(mask, best_y, best_y + args.height, x0, x1)
                b = ink(mask, best_ctrl, best_ctrl + args.height, x0, x1)
                y_t, y_c = best_y, best_ctrl
                qprint(f"（probe 定位）目标 y={best_y} 墨量={a} | 对照 y={best_ctrl} 墨量={b} ratio={best_ratio:.2f}")
            else:
                print(f"❌ 自动定位失败：墨迹带 < 2 且 probe 最佳 ratio={best_ratio:.2f}<{args.min_ratio}。", file=sys.stderr)
                print("   可显式指定: --y-target <行顶y> --y-control <行顶y> --height <行高>", file=sys.stderr)
                sys.exit(1)

    diff = a - b
    # 方向性比值：目标行（真实 CJK 文本行）墨量须显著多于对照行（空白/无文字背景）才可通过。
    # ⚠️ 不能用 hi/max(lo,1)（对称比值）——目标行为空（墨量 0）而对照行有墨时，
    #    对称比值相等反向计算仍会 >=min_ratio → 假通过（"空行 vs 有内容"ratio>=2 无意义）。
    #    真实中国字行墨量 >> 空白对照行，故 a/b 方向性比值能正确区分：只有 a > b 才算候选。
    if a > b:
        ratio = a / max(b, 1)
    else:
        ratio = 0.0
    qprint(f"目标={a} 对照={b} diff={diff} ratio={ratio:.2f}")
    if ratio < args.min_ratio:
        if args.y_target is None:
            # 自动定位失败: 找空白对照行 → 跑 probe 找最佳坐标，自动重试
            print(f"⚠️ 自动定位 ratio={ratio:.2f}<{args.min_ratio}，扫描最佳坐标重试...", file=sys.stderr)
            best_ctrl = find_blank_control(mask, x0, x1, args.height)
            best_y, best_ratio = probe_scan(mask, x0, x1, args.height, best_ctrl)
            if best_ratio >= args.min_ratio:
                a2 = ink(mask, best_y, best_y + args.height, x0, x1)
                b2 = ink(mask, best_ctrl, best_ctrl + args.height, x0, x1)
                qprint(f"（自动重试）目标 y={best_y} 墨量={a2} | 对照 y={best_ctrl} 墨量={b2} ratio={best_ratio:.2f}")
                print("✅ 像素级字形校验通过（自动重试）")
                sys.exit(0)
            else:
                print(f"❌ 自动重试仍未通过（最佳 ratio={best_ratio:.2f}<{args.min_ratio}）。", file=sys.stderr)
                print("   请检查字体是否丢失，或手动指定坐标:", file=sys.stderr)
                print(f"     python3 verify-glyphs.py {args.image} --probe", file=sys.stderr)
                print(f"     python3 verify-glyphs.py {args.image} --y-target <y> --y-control <y>", file=sys.stderr)
        else:
            print(f"❌ 疑似未渲染真实 CJK 字形（ratio={ratio:.2f}<{args.min_ratio}）。", file=sys.stderr)
            print("   请检查文字行是否排布/字体是否丢失，或调整 --y-target/--y-control 坐标。", file=sys.stderr)
        sys.exit(1)
    print("✅ 像素级字形校验通过")
    sys.exit(0)


if __name__ == "__main__":
    main_cli()