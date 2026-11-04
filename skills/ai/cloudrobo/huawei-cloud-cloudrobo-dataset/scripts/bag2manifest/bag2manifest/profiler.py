"""扫描 bag -> BagProfile (profile.json).

profile.json 是算子与 Web 之间的 **唯一数据契约**:
拿到它之后 Web 全程不再需要访问 bag 文件.

因此这里必须一次性采足:
  * 所有话题的类型/频率/条数/时间戳有效率
  * 所有 **数值叶子字段** 的统计量 + 降采样曲线 (不做筛选, 避免用户想选的字段没采到)
  * 所有图像话题的若干张缩略图
  * 文本话题的样本 (任务描述来源)
"""

from __future__ import annotations

import base64
import io
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import numpy as np

from . import PROFILE_SCHEMA_VERSION
from . import msgutil as mu
from .reader import BagSource, TopicInfo, open_any

SERIES_POINTS = 400        # 每个字段曲线降采样点数
IMAGE_SAMPLES = 6          # 每个相机取几张缩略图
THUMB_SIDE = 220


@dataclass
class ProfileOptions:
    series_points: int = SERIES_POINTS
    image_samples: int = IMAGE_SAMPLES
    thumb_side: int = THUMB_SIDE
    max_seconds: float = 0.0        # >0 时只分析前 N 秒 (快速模式)
    include_ignorable: bool = False  # 是否保留 /rosout 之类
    msg_dirs: list = field(default_factory=list)  # 自定义消息定义目录 (db3 需要)


ProgressFn = Callable[[float, str], None]


def _noop(_p: float, _m: str) -> None:
    pass


def _png_b64(arr: np.ndarray) -> str:
    from PIL import Image as PILImage

    buf = io.BytesIO()
    PILImage.fromarray(arr).save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def b64_to_array(s: str) -> np.ndarray:
    from PIL import Image as PILImage

    return np.asarray(PILImage.open(io.BytesIO(base64.b64decode(s))).convert("RGB"))


# --------------------------------------------------------------------------- #
def profile_bag(path, opts: ProfileOptions | None = None,
                progress: ProgressFn = _noop) -> dict:
    """扫描 bag, 返回 profile dict (JSON 可序列化).

    ``path`` 可以是路径字符串 / Path / 路径列表 (Web 目录选择) / gradio 文件对象.
    """
    opts = opts or ProfileOptions()
    t0 = time.time()
    progress(0.02, "打开 bag")

    src, display = open_any(path, opts.msg_dirs)
    try:
        return _profile_impl(src, display, opts, progress, t0)
    finally:
        src.close()
        for td in (src.tmpdirs or []):
            shutil.rmtree(td, ignore_errors=True)


def _profile_impl(src: BagSource, display: str, opts: ProfileOptions,
                  progress: ProgressFn, t0: float) -> dict:
    start_ns, end_ns = src.start_ns, src.end_ns
    if opts.max_seconds > 0:
        end_ns = min(end_ns, start_ns + int(opts.max_seconds * 1e9))
    dur = max((end_ns - start_ns) / 1e9, 1e-6)

    all_topics = src.topics()
    topics: list[TopicInfo] = [
        t for t in all_topics if opts.include_ignorable or not mu.is_ignorable(t.topic)
    ]
    ignored = [t.topic for t in all_topics if t not in topics]
    progress(0.06, f"发现 {len(all_topics)} 个话题")

    kinds = {t.topic: mu.classify(t.msgtype, t.topic) for t in topics}
    scalar_topics = [t for t in topics if kinds[t.topic] in ("numeric", "text", "tf")]
    image_topics = [t for t in topics if kinds[t.topic] in ("image", "compressed_image")]

    # ---------------- 低维话题: 一次合并扫描, 逐话题 stride 采样 -------------- #
    stride_map = {
        t.topic: max(1, int(t.count // max(opts.series_points, 1)))
        for t in scalar_topics
    }
    acc: dict[str, dict] = {
        t.topic: {"t": [], "vals": {}, "texts": [], "stamp_ok": 0, "stamp_n": 0,
                  "hdr": 0, "clock_delta": []}
        for t in scalar_topics
    }
    if scalar_topics:
        progress(0.10, f"采样 {len(scalar_topics)} 个低维话题")
        names = [t.topic for t in scalar_topics]
        typemap = {t.topic: t.msgtype for t in scalar_topics}
        seen = 0
        total_hint = max(sum(t.count for t in scalar_topics), 1)
        for topic, ts, msg in src.iter_messages(names, start_ns, end_ns, stride=stride_map):
            seen += 1
            if seen % 5000 == 0:
                progress(0.10 + 0.45 * min(seen / total_hint, 1.0), f"低维采样 {seen}")
            if msg is None:
                continue
            a = acc[topic]
            hs = mu.stamp_ns(msg)
            a["stamp_n"] += 1
            if getattr(msg, "header", None) is not None or getattr(msg, "stamp", None) is not None:
                a["hdr"] += 1
            if hs:
                a["stamp_ok"] += 1
                # 记录 header 时钟与 bag 记录时钟的差, 用于识别"相对时间戳"的驱动
                a["clock_delta"].append((ts - hs) / 1e9)
            # 时间轴统一用 bag 记录时间: header 有可能来自另一时钟域 (如 sim_time / 节点启动计时)
            a["t"].append(ts - start_ns)
            mt = typemap[topic]
            if kinds[topic] == "tf":
                flat = _flatten_tf(msg)
            else:
                flat = mu.flatten_numeric(msg, mt)
            for k, v in flat.items():
                a["vals"].setdefault(k, []).append((len(a["t"]) - 1, v))
            if kinds[topic] == "text":
                for tv in mu.flatten_text(msg).values():
                    if tv not in a["texts"]:
                        a["texts"].append(tv)

    # ---------------- 图像话题: 分窗 seek, 只取少量帧 ------------------------ #
    img_acc: dict[str, dict] = {}
    for i, t in enumerate(image_topics):
        progress(0.55 + 0.35 * (i / max(len(image_topics), 1)), f"解码相机 {t.topic}")
        img_acc[t.topic] = _sample_images(src, t, start_ns, end_ns, opts)

    # ---------------- 组装 -------------------------------------------------- #
    out_topics: list[dict] = []
    for t in topics:
        kind = kinds[t.topic]
        hz = t.count / dur if dur > 0 else 0.0
        entry: dict[str, Any] = {
            "name": t.topic,
            "type": t.msgtype,
            "kind": kind,
            "count": t.count,
            "hz": round(hz, 2),
        }
        if kind in ("image", "compressed_image"):
            entry.update(img_acc.get(t.topic, {}))
        else:
            a = acc.get(t.topic, {})
            n_t = len(a.get("t", []))
            entry["stamp_valid_ratio"] = round(
                (a.get("stamp_ok", 0) / a["stamp_n"]) if a.get("stamp_n") else 0.0, 3
            )
            # 区分"有 header 但 stamp 没填" 与 "消息类型本来就没有 header"
            entry["has_header"] = bool(a.get("hdr", 0))
            entry["sampled"] = n_t
            cd = a.get("clock_delta") or []
            if cd:
                entry["clock_delta_s"] = round(float(np.median(cd)), 3)
                entry["clock_mismatch"] = bool(abs(float(np.median(cd))) > 1.0)
            else:
                entry["clock_delta_s"] = None
                entry["clock_mismatch"] = False
            ts_rel = np.asarray(a.get("t", []), dtype=float) / 1e9
            entry["series_t"] = [round(float(x), 4) for x in ts_rel]
            fields, series = [], {}
            for pathk, pairs in sorted(a.get("vals", {}).items()):
                idx = np.asarray([p[0] for p in pairs], dtype=int)
                val = np.asarray([p[1] for p in pairs], dtype=float)
                if val.size == 0:
                    continue
                full = np.full(n_t, np.nan)
                full[idx] = val
                lo, hi = float(np.nanmin(val)), float(np.nanmax(val))
                exact = (hi - lo) < 1e-9
                # 真实传感器有噪声, 严格相等几乎不会出现; 用绝对容差识别"近似恒定"通道
                near = (not exact) and (hi - lo) < 1e-3
                fields.append({
                    "path": pathk,
                    "min": round(lo, 6),
                    "max": round(hi, 6),
                    "mean": round(float(np.nanmean(val)), 6),
                    "std": round(float(np.nanstd(val)), 6),
                    "constant": exact,
                    "near_constant": near,
                    "unit": mu.unit_guess(pathk, lo, hi),
                    "n": int(val.size),
                })
                series[pathk] = [None if np.isnan(x) else round(float(x), 6) for x in full]
            entry["fields"] = fields
            entry["series"] = series
            if a.get("texts"):
                entry["text_samples"] = a["texts"][:10]
        out_topics.append(entry)

    profile = {
        "schema_version": PROFILE_SCHEMA_VERSION,
        "source": {
            "path": display,
            "name": display,
            "backend": src.backend,
            "start_ns": start_ns,
            "end_ns": end_ns,
            "duration_s": round(dur, 3),
            "topic_count": len(all_topics),
            "ignored_topics": ignored,
            "profiled_in_s": round(time.time() - t0, 2),
            "partial": opts.max_seconds > 0,
        },
        "topics": out_topics,
    }

    from .infer import infer_plan  # 延迟导入避免循环
    profile["suggested"], profile["issues"] = infer_plan(profile)

    # 空话题 (如 n=0 的 action feedback) 不需要消息定义, 不报警
    unresolved = [t for t in topics if not t.resolved and t.count > 0]
    if unresolved:
        types = sorted({t.msgtype for t in unresolved})
        profile["issues"].insert(0, {
            "code": "E015", "level": "error",
            "title": f"{len(unresolved)} 个自定义消息话题无法解析",
            "detail": ("db3 不存储消息定义, 标准类型可自动识别, 以下自定义类型需要 .msg/.idl 定义:\n"
                       + "\n".join(types)
                       + "\n\n受影响话题:\n" + "\n".join(t.topic for t in unresolved[:12])),
            "fix": [
                {"how": "在「载入」页填写「消息定义目录」(包含 pkg/msg/*.msg 的工作空间 src 目录)"},
                {"how": "或改用 .mcap 格式录制: schema 内嵌在文件里, 无需额外定义"},
            ],
        })
    progress(1.0, "完成")
    return profile


def _record_clock(out: dict, ts: int, msg: Any) -> None:
    """记录图像话题的 header 时钟与 log_time 的差."""
    hs = mu.stamp_ns(msg)
    if not hs:
        return
    d = (ts - hs) / 1e9
    out.setdefault("_clock_deltas", []).append(d)
    deltas = out["_clock_deltas"]
    med = float(np.median(deltas))
    out["clock_delta_s"] = round(med, 3)
    out["clock_mismatch"] = bool(abs(med) > 1.0)


def _flatten_tf(msg: Any) -> dict[str, float]:
    """TFMessage -> {parent>child.x: v}, 便于按 frame 对选择."""
    out: dict[str, float] = {}
    for tr in mu._seq(getattr(msg, "transforms", None))[:32]:
        parent = str(getattr(getattr(tr, "header", None), "frame_id", "?"))
        child = str(getattr(tr, "child_frame_id", "?"))
        t = getattr(getattr(tr, "transform", None), "translation", None)
        r = getattr(getattr(tr, "transform", None), "rotation", None)
        base = f"{parent}>{child}"
        for ax in ("x", "y", "z"):
            v = getattr(t, ax, None)
            if v is not None:
                out[f"{base}.t{ax}"] = float(v)
        for ax in ("x", "y", "z", "w"):
            v = getattr(r, ax, None)
            if v is not None:
                out[f"{base}.q{ax}"] = float(v)
    return out


def _sample_images(src: BagSource, t: TopicInfo, start_ns: int, end_ns: int,
                   opts: ProfileOptions) -> dict:
    """在时间轴上均匀取 N 帧, 用分窗 seek 避免整包扫描."""
    n = max(1, opts.image_samples)
    span = max(end_ns - start_ns, 1)
    hz = max(t.count / (span / 1e9), 1e-3)
    win = int(max(3.0 / hz, 0.25) * 1e9)
    out: dict[str, Any] = {"thumbnails": [], "image": None, "decode_error": None}
    metas: list[dict] = []

    for i in range(n):
        anchor = start_ns + int(span * (i + 0.5) / n)
        lo = max(start_ns, anchor - win // 2)
        hi = min(end_ns, lo + win)
        got = False
        try:
            for _topic, ts, msg in src.iter_messages([t.topic], lo, hi):
                if msg is None:
                    continue
                rgb, meta = mu.decode_image(msg, t.msgtype)
                _record_clock(out, ts, msg)
                metas.append(meta)
                if rgb is not None:
                    out["thumbnails"].append({
                        "t": round((ts - start_ns) / 1e9, 3),
                        "png_b64": _png_b64(mu.thumbnail(rgb, opts.thumb_side)),
                    })
                got = True
                break
        except Exception as e:  # noqa: BLE001
            out["decode_error"] = str(e)
            break
        if not got and i == 0:
            # 分窗没抓到 (稀疏话题) -> 退化为顺序读前几帧
            try:
                cnt = 0
                for _topic, ts, msg in src.iter_messages([t.topic], start_ns, end_ns):
                    if msg is None:
                        continue
                    rgb, meta = mu.decode_image(msg, t.msgtype)
                    _record_clock(out, ts, msg)
                    metas.append(meta)
                    if rgb is not None:
                        out["thumbnails"].append({
                            "t": round((ts - start_ns) / 1e9, 3),
                            "png_b64": _png_b64(mu.thumbnail(rgb, opts.thumb_side)),
                        })
                    cnt += 1
                    if cnt >= n:
                        break
            except Exception as e:  # noqa: BLE001
                out["decode_error"] = str(e)
            break

    if metas:
        m = metas[0]
        out["image"] = {
            "width": m.get("width"), "height": m.get("height"),
            "encoding": m.get("encoding"), "is_depth": bool(m.get("is_depth")),
        }
        errs = [m2["error"] for m2 in metas if m2.get("error")]
        if errs:
            out["decode_error"] = errs[0]
        sizes = {(m2.get("width"), m2.get("height")) for m2 in metas if m2.get("width")}
        out["size_stable"] = len(sizes) <= 1
    out.pop("_clock_deltas", None)
    return out
