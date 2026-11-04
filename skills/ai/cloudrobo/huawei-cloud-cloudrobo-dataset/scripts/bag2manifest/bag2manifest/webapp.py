"""Gradio 可视化配置器 —— 本地选一个样例 bag, 点几下, 导出 manifest.yaml.

定位: **带即时预览的配置验证台**, 不是"YAML 生成器".

自由度设计:
    * 状态 / 动作 / 其他特征 都由「字段池 + 有序向量表」构成:
        - 字段池列出 **所有话题的所有数值字段**, 可任意挑选加入
        - 向量表是唯一真相源, 支持 上移/下移/删除, 顺序即最终拼接顺序
    * 支持 **计算字段 (表达式)**: 输入字段在表达式里叫 f0, f1, ...,
        例如 ``abs(f0) + abs(f1)`` 表示左右夹爪指关节绝对值相加.
    * 除 observation.state / action 外, 可自由添加任意顶层特征
        (如 next.reward / next.done / observation.force / observation.velocity).
    * 推断规则全部来自 bag2manifest.infer, 本文件 **不含任何推断逻辑**.
"""

from __future__ import annotations

import inspect
import json
import os
import tempfile
import traceback
from pathlib import Path
from typing import Any

import gradio as gr
import numpy as np
import yaml as _yaml

from . import __version__, derive
from .manifest import build_manifest, default_choices, manifest_to_yaml, validate_manifest
from .profiler import ProfileOptions, b64_to_array, profile_bag

# Gradio 版本差异（按签名探测，而不是吞 TypeError 重试）：
#   * Gradio >=6：css / theme 属于 launch()，Blocks() 仅给出弃用警告
#   * Gradio <=5：css / theme 属于 Blocks()，launch() 不接受（5.49.1 会 TypeError）
#   * gr.Tab(render_children=...) 仅 Gradio >=5.x 后期版本支持（4.44 / 5.0 不存在）
_STYLE_IN_LAUNCH = "css" in inspect.signature(gr.Blocks.launch).parameters
_TAB_KW: dict[str, Any] = (
    {"render_children": True}
    if "render_children" in inspect.signature(gr.Tab.__init__).parameters else {})


def _style_kwargs() -> dict[str, Any]:
    return dict(css=STATE_UI_CSS, theme=gr.themes.Soft())


def _blocks_style() -> dict[str, Any]:
    return {} if _STYLE_IN_LAUNCH else _style_kwargs()


def _launch_style() -> dict[str, Any]:
    return _style_kwargs() if _STYLE_IN_LAUNCH else {}


CAM_HEADERS = ["启用", "相机名", "话题", "深度图", "原始尺寸", "缩放 HxW (留空=原始)"]
VEC_HEADERS = ["#", "字段 / 表达式", "标记", "min", "max", "单位猜测"]
VEC_TYPES = ["number", "str", "str", "number", "number", "str"]
LEVEL_ICON = {"error": "🔴", "warn": "🟡", "info": "🔵"}


# --------------------------------------------------------------------------- #
# 基础工具
# --------------------------------------------------------------------------- #
def field_index(profile: dict) -> dict[str, dict]:
    idx: dict[str, dict] = {}
    for t in profile.get("topics", []):
        st = t.get("series_t") or []
        for f in t.get("fields", []):
            key = f"{t['name']}.{f['path']}"
            idx[key] = {"topic": t["name"], "path": f["path"], "stat": f,
                        "series_t": st, "series": (t.get("series") or {}).get(f["path"], [])}
    return idx


def field_choices(profile: dict) -> list[tuple[str, str]]:
    out = []
    for key, info in field_index(profile).items():
        s = info["stat"]
        tag = " ·恒定" if s["constant"] else (" ·近似恒定" if s.get("near_constant") else "")
        unit = f" ·{s['unit']}" if s["unit"] else ""
        out.append((f"{key}   [{s['min']:g}, {s['max']:g}]{unit}{tag}", key))
    return out


def _rows(df: Any) -> list[list]:
    if df is None:
        return []
    if hasattr(df, "values"):
        return [list(r) for r in df.values.tolist()]
    if isinstance(df, dict) and "data" in df:
        return [list(r) for r in df["data"]]
    return [list(r) for r in df]


def _truthy(v: Any) -> bool:
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes", "是", "✓")
    return bool(v)


def _need_profile(profile):
    if not profile:
        raise gr.Error("请先在「① 载入」页分析 bag")


def _as_list(v: Any) -> list[str]:
    if isinstance(v, (list, tuple, set)):
        return [str(x) for x in v if x]
    return [str(v)] if v else []


def issues_md(issues: list[dict], title: str = "体检结果") -> str:
    if not issues:
        return f"### {title}\n\n✅ 未发现问题。"
    order = {"error": 0, "warn": 1, "info": 2}
    items = sorted(issues, key=lambda i: order.get(i["level"], 3))
    n_err = sum(1 for i in items if i["level"] == "error")
    parts = [f"### {title} — 🔴 {n_err} 个错误 / 🟡 {len(items) - n_err} 个提醒\n"]
    for i in items:
        parts.append(f"\n**{LEVEL_ICON.get(i['level'], '·')} `{i['code']}` {i['title']}**\n")
        if i.get("detail"):
            parts.append("```\n" + str(i["detail"]).strip() + "\n```\n")
        for fx in i.get("fix", []):
            parts.append(f"- {fx['how']}")
            if fx.get("snippet"):
                parts.append(f"\n  ```yaml\n  {fx['snippet']}\n  ```")
            parts.append("\n")
    return "".join(parts)


def attention_md(profile: dict) -> str:
    """Keep issues that need a decision visible in the guided view."""
    issues = profile.get("issues", [])
    important = [i for i in issues if i["level"] == "error"]
    if not important:
        return "✅ 分析完成。按顺序核对相机、状态和动作，然后生成配置。"
    lines = ["### 分析后需要处理"]
    lines += [f"- 🔴 {i['title']}" for i in important]
    if any(i["code"] == "E021" for i in important):
        lines.append("- 请到「④ 动作」确认动作来源；确认前不能导出配置。")
    return "\n".join(lines)


def camera_review(profile, df_cams) -> str:
    if not profile:
        return "分析后在这里核对相机。"
    rows = [r for r in _rows(df_cams) if _truthy(r[0])]
    names = "、".join(str(r[1]) for r in rows) or "无"
    return f"**已选 {len(rows)} 路相机：{names}。** 请直接核对或修改下方映射表，再查看画面预览。"


def state_review(profile, vec) -> str:
    if not profile:
        return "分析后在这里核对状态。"
    items = list(vec or [])
    suggested = (profile.get("suggested", {}).get("state") or {}).get("value", [])
    same = [x.get("locator") if isinstance(x, dict) else x for x in items] == suggested
    same = same and all(not isinstance(x, dict) or not any(k in x for k in ("expr", "interpolation", "default", "name")) for x in items)
    source = "自动推断结果" if same else "已修改自动推断结果"
    mark = "✅" if items else "🔴"
    return f"{mark} **状态向量：{len(items)} 维。** {source}，请核对下方字段及顺序。"


def state_item_selector(vec, sel, profile=None):
    """Make the state list itself the row selector for edit actions."""
    items = list(vec or [])
    stats = {int(row[0]) - 1: row for row in render_vec(profile, items)} if profile else {}
    choices = []
    for i, item in enumerate(items):
        row = stats.get(i)
        suffix = ""
        if row:
            span = (f"[{row[3]:g}, {row[4]:g}]" if row[3] is not None and row[4] is not None
                    else "范围未知")
            suffix = f"  ·  {span}"
            if row[5]:
                suffix += f" {row[5]}"
            if row[2]:
                suffix += f"  ·  {row[2]}"
        choices.append((f"{i + 1}. {derive.item_id(item)}{suffix}", i))
    selected = sel if isinstance(sel, int) and 0 <= sel < len(items) else None
    return gr.update(choices=choices, value=selected)


def state_target_selector(vec, sel):
    items = list(vec or [])
    choices = [(f"{i + 1}. {derive.item_id(item)}", i)
               for i, item in enumerate(items)]
    selected = sel if isinstance(sel, int) and 0 <= sel < len(items) else None
    return gr.update(choices=choices, value=selected)


def state_target_select(profile, vec, selected):
    sel = int(selected) if selected is not None else -1
    return sel, gr.update(value=sel if sel >= 0 else None), *state_selected_editor(profile, vec, sel)


def state_topic_choices(profile):
    if not profile:
        return []
    return [(f"{t['name']} · {len(t.get('fields', []))} 个数值字段", t["name"])
            for t in profile.get("topics", [])]


def state_field_choices(profile, topic):
    if not profile or not topic:
        return []
    t = next((item for item in profile.get("topics", []) if item["name"] == topic), None)
    if not t:
        return []
    out = []
    for f in t.get("fields", []):
        label = f"{f['path']}   [{f['min']:g}, {f['max']:g}]"
        if f.get("unit"):
            label += f" {f['unit']}"
        if f.get("constant"):
            label += " ·恒定"
        elif f.get("near_constant"):
            label += " ·近似恒定"
        out.append((label, f"{topic}.{f['path']}"))
    return out


def state_topic_update(profile, topic):
    choices = state_field_choices(profile, topic)
    hint = (f"该话题有 **{len(choices)}** 个可选数值字段。" if choices else
            "该话题没有可加入状态的数值字段；图像等话题可在相机页配置。")
    return gr.update(choices=choices, value=[]), hint


def inspect_state(profile, vec):
    if not profile:
        return [], None
    return render_vec(profile, vec), do_plot_state(profile, vec, False)


def state_selected_editor(profile, vec, sel):
    items = list(vec or [])
    if not isinstance(sel, int) or not 0 <= sel < len(items):
        return ("请先在上方选中一维。", gr.update(choices=field_choices(profile) if profile else [], value=None),
                gr.update(value=[]), "", gr.update(value=""), gr.update(value=True))
    item = items[sel]
    row = render_vec(profile, [item])[0]
    span = (f"[{row[3]:g}, {row[4]:g}]" if row[3] is not None and row[4] is not None
            else "未知")
    summary = f"**正在编辑第 {sel + 1} 维：** `{derive.item_id(item)}` · 范围 {span}"
    if row[2]:
        summary += f" · {row[2]}"
    if derive.is_expr(item):
        return (summary, gr.update(choices=field_choices(profile), value=None),
                gr.update(value=item.get("inputs", [])), item.get("expr", ""),
                gr.update(value=item.get("name") or ""),
                gr.update(value=bool(item.get("normalize", False))))
    return (summary, gr.update(choices=field_choices(profile), value=item), gr.update(value=[item]), "f0",
            gr.update(value=""), gr.update(value=True))


def state_select(profile, vec, selected):
    sel = int(selected) if selected is not None else -1
    return (sel, *state_selected_editor(profile, vec, sel))


def action_review(profile, state_vec, action_vec, strategy) -> str:
    if not profile:
        return "分析后在这里确认动作来源。"
    sug = (profile.get("suggested", {}).get("action") or {})
    descriptions = {
        "stored": f"使用已配置的 {len(action_vec or [])} 个动作维度",
        "next_state": "使用下一帧状态作为动作",
    }
    lines = [f"**当前动作来源：{descriptions.get(strategy, strategy)}。**"]
    if strategy == "stored":
        candidates = sug.get("candidates") or []
        if len(candidates) > 1:
            lines.append("🔴 检测到多个候选指令话题，请核对下方映射；请在下方统一编辑器中修改，最后勾选确认。候选："
                         + "、".join(f"`{c}`" for c in candidates))
        elif not action_vec:
            lines.append("🔴 尚未选择动作字段；请展开「编辑动作字段与曲线」添加。")
        elif len(state_vec or []) != len(action_vec or []):
            lines.append("🟡 动作与状态维度不同，请确认符合机器人控制方式。")
    elif strategy == "next_state":
        lines.append("🟡 未使用独立指令话题。请确认这符合数据采集方式。")
    return "\n\n".join(lines)


def action_view_controls(profile, strategy):
    ambiguous = bool(profile and any(i["code"] == "E021"
                                     for i in profile.get("issues", [])))
    return (gr.update(visible=strategy == "stored"),
            gr.update(visible=strategy == "stored" and ambiguous, value=False))


def _inputs(*cands):
    out: list[str] = []
    for c in cands:
        if c is None or c == "":
            continue
        if isinstance(c, (list, tuple, set)):
            out += _inputs(*c)
            continue
        p = c if isinstance(c, str) else getattr(c, "name", None)
        if p:
            out.append(str(p))
    return out


def _is_huggingface_space() -> bool:
    """Whether this process is running inside a Hugging Face Space."""
    return bool(os.getenv("SPACE_ID"))


# --------------------------------------------------------------------------- #
# 有序向量 (状态 / 动作 / 其他特征 共用)
# --------------------------------------------------------------------------- #
def aug_index(profile: dict, *vecs) -> dict[str, dict]:
    """在字段索引上追加计算字段, 供绘图/统计使用."""
    idx = field_index(profile)
    series = {k: v["series"] for k, v in idx.items()}
    zero = {"min": 0.0, "max": 0.0, "mean": 0.0, "std": 0.0,
            "constant": True, "near_constant": True, "unit": "", "n": 0}
    for vec in vecs:
        for it in (vec or []):
            if isinstance(it, dict) and it.get("strategy") == "next_state":
                source_vec = vecs[0] if len(vecs) > 1 else []
                index = it.get("state_index", -1)
                if isinstance(index, int) and 0 <= index < len(source_vec):
                    base = idx.get(derive.item_id(source_vec[index]))
                    if base:
                        values = base.get("series", [])
                        idx[derive.item_id(it)] = {**base, "series": values[1:] + values[-1:]}
                continue
            if not derive.is_expr(it):
                continue
            key = derive.item_id(it)
            if key in idx:
                continue
            try:
                arr = derive.eval_array(it["expr"], it["inputs"], series)
                t = idx.get(it["inputs"][0], {}).get("series_t") or []
                idx[key] = {"topic": "ƒ", "path": key,
                            "stat": {**derive.stats_of(arr), "unit": "", "n": int(arr.size)},
                            "series_t": t, "series": derive.to_series(arr)}
            except derive.ExprError as e:
                idx[key] = {"topic": "ƒ", "path": key, "error": str(e),
                            "stat": dict(zero), "series_t": [], "series": []}
    return idx


def render_vec(profile: dict, vec: list) -> list[list]:
    idx = aug_index(profile, vec)
    rows = []
    for i, it in enumerate(vec or []):
        if isinstance(it, dict) and it.get("strategy") == "next_state":
            rows.append([i + 1, derive.item_id(it), f"下一帧 state[{it.get('state_index')}]", None, None, "gripper" if it.get("role") else ""])
        elif derive.is_expr(it):
            key = derive.item_id(it)
            info = idx.get(key, {})
            st = info.get("stat") or {}
            mark = "ƒ 计算字段"
            if info.get("error"):
                mark += f"  ⚠️ {info['error']}"
            rows.append([i + 1, f"{key}  ←  {it.get('expr','')}", mark,
                         st.get("min"), st.get("max"), ""])
        else:
            info = idx.get(it.get("locator", "") if isinstance(it, dict) else str(it))
            if not info:
                rows.append([i + 1, derive.item_id(it), "⚠️ 样例中不存在", None, None, ""])
                continue
            s = info["stat"]
            dead = ("⚠️ 恒定" if s["constant"]
                    else ("⚠️ 近似恒定" if s.get("near_constant") else ""))
            rows.append([i + 1, derive.item_id(it), dead, s["min"], s["max"], s["unit"]])
    return rows


def _new_expr_item(picked, expr, name, normalize) -> dict:
    ins = _as_list(picked)
    if not ins:
        raise gr.Error("请先在字段池选择该计算字段的输入字段（表达式里叫 f0, f1, …）")
    expr = (expr or "").strip()
    try:
        need = derive.required_vars(expr)
    except derive.ExprError as e:
        raise gr.Error(str(e)) from e
    if need > len(ins):
        raise gr.Error(f"表达式用到 f{need - 1}，但只选了 {len(ins)} 个输入字段: "
                       + ", ".join(f"f{i}={p}" for i, p in enumerate(ins)))
    return {"expr": expr, "inputs": ins,
            "name": (str(name).strip() if name else "") or None,
            "normalize": bool(normalize)}


def expr_hint(picked) -> str:
    ins = _as_list(picked)
    if not ins:
        return "_先在上方选择参与计算的输入字段，再写公式。_"
    lines = [f"- `f{i}` = `{p}`" for i, p in enumerate(ins)]
    return "**表达式的变量映射**（可用 `abs/min/max/sqrt/exp/log/clip/where`）：\n" + "\n".join(lines)


def state_expr_hint(picked) -> str:
    ins = _as_list(picked)
    if not ins:
        return "_先选择参与计算的输入字段。_"
    return "\n".join(f"- `f{i}` = `{p}`" for i, p in enumerate(ins))


def on_select(evt: gr.SelectData):
    try:
        return int(evt.index[0])
    except Exception:  # noqa: BLE001
        return -1


# --------------------------------------------------------------------------- #
# 步骤 1: 分析
# --------------------------------------------------------------------------- #
def do_analyze(file_obj, dir_obj, path_text, msg_dir_text, quick_seconds):
    path_text = (path_text or "").strip()
    if _is_huggingface_space() and path_text:
        raise gr.Error("Hugging Face Space 不支持读取服务器本地路径；请上传 bag 文件或 zip 包")
    paths = _inputs(file_obj, dir_obj, path_text)
    if not paths:
        raise gr.Error("请上传 bag 文件、选择一个 bag 目录, 或填写本地路径")
    src: Any = paths[0] if len(paths) == 1 else paths
    msg_dirs = [x.strip() for x in (msg_dir_text or "").replace(";", ",").split(",")
                if x.strip()]

    try:
        profile = profile_bag(
            src,
            ProfileOptions(max_seconds=float(quick_seconds or 0), msg_dirs=msg_dirs))
    except Exception as e:  # noqa: BLE001
        fix = getattr(e, "fix", [])
        msg = f"{e}"
        if fix:
            msg += "\n\n建议:\n" + "\n".join(f"  - {f}" for f in fix)
        traceback.print_exc()
        raise gr.Error(msg[:900]) from e

    ch = default_choices(profile)
    sug = profile["suggested"]
    s = profile["source"]
    summary = (f"### 已分析：{s['name']}\n\n"
               f"时长 **{s['duration_s']:.1f} 秒** · 发现 **{s['topic_count']} 个话题**。"
               + (" ⚠️ 只分析了前一段。" if s["partial"] else ""))
    analysis_detail = (
        f"分析后端 `{s['backend']}` · 扫描耗时 {s['profiled_in_s']}s\n\n"
        f"自动忽略：`{'`, `'.join(s['ignored_topics']) or '无'}`\n\n"
        f"推断 fps：**{sug['fps']['value']}**（{sug['fps']['rule']}: {sug['fps']['why']}）\n\n"
        f"推断状态：**{len(sug['state']['value'])}** 维（{sug['state']['rule']}）\n\n"
        f"推断动作：**{sug['action'].get('strategy')}**（{sug['action']['rule']}: "
        f"{sug['action']['why']}）")
    topic_rows = [[
        t["name"], t["type"].replace("/msg/", "/"), t["kind"], t["count"], t["hz"],
        (f"{t['image']['width']}x{t['image']['height']} {t['image']['encoding']}"
         if t.get("image") else f"{len(t.get('fields', []))} 字段"),
    ] for t in profile["topics"]]

    cam_rows = cam_rows_from_choices(ch)
    fchoices = field_choices(profile)
    task_samples = (sug.get("task") or {}).get("samples") or []
    state_vec = list(ch["state"])
    action_vec = list(ch["action"])
    afig, anote = do_plot_action(profile, state_vec, action_vec,
                                 ch["action_strategy"], True)

    return (
        profile, summary, topic_rows, issues_md(profile["issues"]),
        gr.update(value=cam_rows), _gallery(profile, cam_rows),
        state_vec, action_vec,
        state_item_selector(state_vec, 0 if state_vec else -1, profile),
        gr.update(value=render_vec(profile, action_vec),
                  visible=ch["action_strategy"] == "stored"),
        gr.update(choices=fchoices, value=[]), gr.update(choices=fchoices, value=[]),
        gr.update(value=ch["action_strategy"]), gr.update(value=ch["fps"]),
        gr.update(value=ch["robot_type"]),
        gr.update(value=Path(str(src)).stem.replace(" ", "_")),
        gr.update(value=(task_samples[0] if task_samples else "")),
        0 if state_vec else -1, -1,
        {}, [], _feat_rows({}), render_vec(profile, []),
        do_plot_state(profile, state_vec, False), -1, "",
        gr.update(selected=1), afig, anote,
        attention_md(profile), camera_review(profile, cam_rows),
        state_review(profile, state_vec),
        action_review(profile, state_vec, action_vec, ch["action_strategy"]),
        gr.update(value=False, visible=ch["action_strategy"] == "stored" and
                  any(i["code"] == "E021" for i in profile["issues"])),
        gr.update(value=ch["task_topic"]),
        analysis_detail,
        render_vec(profile, state_vec),
        gr.update(choices=state_topic_choices(profile),
                  value=field_index(profile).get(state_vec[0], {}).get("topic")
                  if state_vec else None),
        *state_topic_update(profile,
                            field_index(profile).get(state_vec[0], {}).get("topic")
                            if state_vec else None),
        state_selected_editor(profile, state_vec, 0 if state_vec else -1)[0],
        gr.update(choices=fchoices,
                  value=state_vec[0] if state_vec and not derive.is_expr(state_vec[0]) else None),
        state_target_selector(state_vec, 0 if state_vec else -1),
        state_target_selector(state_vec, 0 if state_vec else -1),
    )


# --------------------------------------------------------------------------- #
# 相机
# --------------------------------------------------------------------------- #
def _gallery(profile: dict, cam_rows: list[list]) -> list:
    if not profile:
        return []
    by_topic = {t["name"]: t for t in profile["topics"]}
    items = []
    for r in cam_rows:
        enabled, name, topic = _truthy(r[0]), str(r[1]), str(r[2])
        t = by_topic.get(topic)
        if not t:
            continue
        mark = "" if enabled else "（未启用）"
        for th in (t.get("thumbnails") or []):
            items.append((b64_to_array(th["png_b64"]), f"{name}{mark}  t={th['t']}s"))
        if not t.get("thumbnails"):
            items.append((np.zeros((80, 160, 3), np.uint8),
                          f"{name} 无法解码: {t.get('decode_error') or '未取到帧'}"))
    return items


def do_refresh_gallery(profile, df_cams):
    _need_profile(profile)
    return _gallery(profile, _rows(df_cams))


def cam_rows_from_choices(ch: dict) -> list[list]:
    rows = []
    for c in ch.get("cameras", []):
        rows.append([
            bool(c.get("enabled")), c["name"], c["topic"], bool(c.get("depth")),
            f"{c['width']}x{c['height']}" if c.get("width") else "?",
            c.get("resize", ""),
        ])
    return rows


def do_reset_cameras(profile):
    _need_profile(profile)
    rows = cam_rows_from_choices(default_choices(profile))
    return gr.update(value=rows), _gallery(profile, rows)


# --------------------------------------------------------------------------- #
# 曲线
# --------------------------------------------------------------------------- #
def _series_fig(idx, ids, normalize, title, dash_ids=()):
    import plotly.graph_objects as go

    fig = go.Figure()
    palette = ["#2E86DE", "#EE5A24", "#009432", "#8854d0", "#e58e26",
               "#0abde3", "#c44569", "#1B1464"]
    for i, k in enumerate(ids or []):
        info = idx.get(k)
        if not info or not info.get("series"):
            continue
        x = info["series_t"]
        arr = np.asarray([np.nan if v is None else v for v in info["series"]], dtype=float)
        if normalize:
            lo, hi = np.nanmin(arr), np.nanmax(arr)
            arr = (arr - lo) / (hi - lo) if hi > lo else arr * 0
        fig.add_trace(go.Scatter(
            x=x, y=arr, mode="lines", name=k[:36],
            line=dict(width=1.8, color=palette[i % len(palette)],
                      dash="dot" if k in dash_ids else "solid"),
            hovertemplate=f"{k}<br>t=%{{x:.2f}}s<br>v=%{{y:.4f}}<extra></extra>"))
    fig.update_layout(
        title=title, height=360, margin=dict(l=40, r=20, t=48, b=36),
        xaxis_title="时间 (s)", yaxis_title="归一化值" if normalize else "值",
        legend=dict(orientation="h", y=-0.22, font=dict(size=10)),
        template="plotly_white")
    return fig


def do_plot_state(profile, vec, normalize):
    if not profile:
        raise gr.Error("请先在「① 载入」页分析 bag")
    ids = [derive.item_id(x) for x in (vec or [])]
    return _series_fig(aug_index(profile, vec), ids, normalize,
                       f"observation.state — {len(ids)} 维")


def do_plot_action(profile, state_vec, action_vec, strategy, normalize):
    if not profile:
        raise gr.Error("请先在「① 载入」页分析 bag")
    idx = aug_index(profile, state_vec, action_vec)
    sids = [derive.item_id(x) for x in (state_vec or [])]
    aids = [derive.item_id(x) for x in (action_vec or [])]
    if strategy != "stored":
        note = ("当前策略 **%s**：动作由状态推导，不需要选择字段。\n\n"
                "- `next_state`  action[t] = state[t+1]（末帧复制）\n"
                "ROS Manifest 2.0 只支持 stored / next_state。" % strategy)
        return _series_fig(idx, sids, normalize, "仅显示状态（动作由状态推导）"), note
    n = min(len(sids), len(aids))
    keys = []
    for i in range(min(n, 4)):
        keys += [sids[i], aids[i]]
    if n == 0:
        keys = aids[:8]
    fig = _series_fig(idx, keys, normalize, "状态(虚线) vs 动作(实线) — 前 4 维配对",
                      dash_ids=set(sids))
    note = (
        "**怎么判断动作选对了**\n\n"
        "- ✅ 动作曲线形状与状态相似、且**略微领先**（位置控制）\n"
        "- ✅ 动作是状态的导数形态（速度控制）\n"
        "- ❌ 两条线完全重合 → 你八成选到了状态的回读话题\n"
        "- ❌ 两条线毫无关系 → 选错话题，或该话题不是本次遥操作的指令源\n\n"
        f"当前：状态 {len(sids)} 维 / 动作 {len(aids)} 维"
        + ("（维度不一致，若为关节位控请检查）" if len(sids) != len(aids) else "")
    )
    return fig, note


# --------------------------------------------------------------------------- #
# 三种向量操作: state / action / extra
# --------------------------------------------------------------------------- #
def do_vec_add(profile, vec, picked):
    _need_profile(profile)
    new = list(vec or [])
    for k in _as_list(picked):
        if k not in new:
            new.append(k)
    return new


def do_state_add(profile, vec, sel, picked):
    if not _as_list(picked):
        raise gr.Error("请先选择要添加的数值字段")
    new = do_vec_add(profile, vec, picked)
    if len(new) == len(vec or []):
        raise gr.Error("所选字段已在状态列表中。如需用它们计算新结果，请展开「方式二」填写公式。")
    return new, state_item_selector(new, len(new) - 1, profile), do_plot_state(profile, new, False), len(new) - 1


def do_state_replace_field(profile, vec, sel, picked):
    _need_profile(profile)
    cur = list(vec or [])
    if not isinstance(sel, int) or not 0 <= sel < len(cur):
        raise gr.Error("请先在状态列表中选中要替换的一维")
    if not picked or picked not in field_index(profile):
        raise gr.Error("请先选择一个数值字段")
    if picked != cur[sel] and picked in cur:
        raise gr.Error("这个字段已在状态列表中，请选择其他字段")
    cur[sel] = picked
    return cur, state_item_selector(cur, sel, profile), do_plot_state(profile, cur, False), sel


def do_state_replace_from_bag(profile, vec, sel, picked):
    fields = _as_list(picked)
    if len(fields) != 1:
        raise gr.Error("原位替换只能选 1 个数值字段；若要加入多个字段，请使用追加")
    return do_state_replace_field(profile, vec, sel, fields[0])


def do_state_derive(profile, vec, sel, picked, expr, name, norm):
    _need_profile(profile)
    new = list(vec or []) + [_new_expr_item(picked, expr, name, norm)]
    return new, state_item_selector(new, len(new) - 1, profile), do_plot_state(profile, new, False), len(new) - 1, ""


def do_state_replace_expr(profile, vec, sel, picked, expr, name, norm):
    _need_profile(profile)
    cur = list(vec or [])
    if not isinstance(sel, int) or not 0 <= sel < len(cur):
        raise gr.Error("请先在状态列表中选中要替换的一维")
    cur[sel] = _new_expr_item(picked, expr, name, norm)
    return cur, state_item_selector(cur, sel, profile), do_plot_state(profile, cur, False), sel


def do_state_move(profile, vec, sel, delta):
    _need_profile(profile)
    cur = list(vec or [])
    if not 0 <= sel < len(cur):
        raise gr.Error("请先选择要移动的状态字段")
    j = sel + delta
    if 0 <= j < len(cur):
        cur[sel], cur[j] = cur[j], cur[sel]
        sel = j
    return cur, state_item_selector(cur, sel, profile), do_plot_state(profile, cur, False), sel


def do_state_del(profile, vec, sel):
    _need_profile(profile)
    cur = list(vec or [])
    if not 0 <= sel < len(cur):
        raise gr.Error("请先选择要删除的状态字段")
    cur.pop(sel)
    sel = min(sel, len(cur) - 1)
    return cur, state_item_selector(cur, sel, profile), do_plot_state(profile, cur, False), sel


def do_state_reset(profile):
    _need_profile(profile)
    vec = list(default_choices(profile)["state"])
    return vec, state_item_selector(vec, len(vec) - 1, profile), do_plot_state(profile, vec, False), len(vec) - 1


def _aout(profile, state_v, vec, strategy, sel):
    fig, note = do_plot_action(profile, state_v, vec, strategy, True)
    return vec, render_vec(profile, vec), fig, note, sel


def do_action_add(profile, state_v, vec, sel, strategy, picked):
    new = do_vec_add(profile, vec, picked)
    return _aout(profile, state_v, new, strategy, len(new) - 1)


def do_action_derive(profile, state_v, vec, sel, strategy, picked, expr, name, norm):
    _need_profile(profile)
    new = list(vec or []) + [_new_expr_item(picked, expr, name, norm)]
    v, rows, fig, note, s = _aout(profile, state_v, new, strategy, len(new) - 1)
    return v, rows, fig, note, s, ""


def do_action_move(profile, state_v, vec, sel, delta, strategy):
    _need_profile(profile)
    cur = list(vec or [])
    if 0 <= sel < len(cur):
        j = sel + delta
        if 0 <= j < len(cur):
            cur[sel], cur[j] = cur[j], cur[sel]
            sel = j
    return _aout(profile, state_v, cur, strategy, sel)


def do_action_del(profile, state_v, vec, sel, strategy):
    _need_profile(profile)
    cur = list(vec or [])
    if 0 <= sel < len(cur):
        cur.pop(sel)
        sel = min(sel, len(cur) - 1)
    return _aout(profile, state_v, cur, strategy, sel)


def do_action_next_state(profile, state_v, vec, strategy, index, name, gripper):
    _need_profile(profile)
    if index is None or not 0 <= int(index) < len(state_v or []):
        raise gr.Error("请选择有效的状态维度")
    if strategy != "stored":
        raise gr.Error("混合动作字段需要选择 stored 动作来源")
    item = {"strategy": "next_state", "state_index": int(index),
            "name": (name or "").strip() or f"state_{int(index)}_action"}
    if gripper:
        item["role"] = "gripper"
    current = list(vec or []) + [item]
    return _aout(profile, state_v, current, strategy, len(current) - 1)


def do_action_reset(profile, state_v, strategy):
    _need_profile(profile)
    vec = list(default_choices(profile)["action"])
    return _aout(profile, state_v, vec, strategy, len(vec) - 1)


def do_redraw_action(profile, state_v, action_v, strategy):
    return do_plot_action(profile, state_v, action_v, strategy, True)


# ---- 其他特征 ----
def _feat_rows(d: dict) -> list[list]:
    rows = []
    for name, vec in (d or {}).items():
        summary = ", ".join(derive.item_id(x) for x in vec[:3]) + (" …" if len(vec) > 3 else "")
        rows.append([name, len(vec), summary])
    return rows


def do_feat_add_real(profile, extra_vec, picked):
    new = do_vec_add(profile, extra_vec, picked)
    return new, render_vec(profile, new), do_plot_state(profile, new, True), len(new) - 1


def do_feat_derive(profile, extra_vec, picked, expr, name, norm):
    _need_profile(profile)
    new = list(extra_vec or []) + [_new_expr_item(picked, expr, name, norm)]
    return new, render_vec(profile, new), do_plot_state(profile, new, True), len(new) - 1, ""


def do_feat_move(profile, extra_vec, sel, delta):
    cur = list(extra_vec or [])
    if 0 <= sel < len(cur):
        j = sel + delta
        if 0 <= j < len(cur):
            cur[sel], cur[j] = cur[j], cur[sel]
            sel = j
    return cur, render_vec(profile, cur), do_plot_state(profile, cur, True), sel


def do_feat_del(profile, extra_vec, sel):
    cur = list(extra_vec or [])
    if 0 <= sel < len(cur):
        cur.pop(sel)
        sel = min(sel, len(cur) - 1)
    return cur, render_vec(profile, cur), do_plot_state(profile, cur, True), sel


def do_feat_save(profile, features, name, vec):
    _need_profile(profile)
    nm = (str(name) if name else "").strip()
    if not nm:
        raise gr.Error("请填写特征名，例如 observation.force / next.reward")
    if not vec:
        raise gr.Error("该特征还没有任何字段")
    d = dict(features or {})
    d[nm] = list(vec)
    return d, _feat_rows(d), nm


def do_feat_delete(profile, features, featsel):
    d = dict(features or {})
    keys = list(d)
    if 0 <= featsel < len(keys):
        d.pop(keys[featsel], None)
    return d, _feat_rows(d), "", [], render_vec(profile, []), \
        do_plot_state(profile, [], True), -1


def do_feat_load(profile, features, evt: gr.SelectData):
    keys = list(features or {})
    row = evt.index[0] if evt and evt.index else -1
    if not (0 <= row < len(keys)):
        return "", [], render_vec(profile, []), do_plot_state(profile, [], True), -1
    name = keys[row]
    vec = list(features[name])
    return name, vec, render_vec(profile, vec), do_plot_state(profile, vec, True), len(vec) - 1


def do_feat_new(profile):
    return "", [], render_vec(profile, []), do_plot_state(profile, [], True), -1


# --------------------------------------------------------------------------- #
# 生成 / 校验
# --------------------------------------------------------------------------- #
def collect_choices(profile, df_cams, state_keys, strategy, action_keys, extra_features,
                    auto_norm, repo_id, robot_type, fps, task_mode, task_text,
                    task_topic, segment_mode, min_frames, on_stale, tol_ms,
                    codec, bag_glob, stamp_source, chunk_size, data_size, video_size,
                    curation_text) -> dict:
    ch = default_choices(profile)
    ch.update({
        "repo_id": (repo_id or "").strip(),
        "robot_type": (robot_type or "unknown").strip(),
        "fps": int(fps or 30),
        "cameras": [{
            "enabled": _truthy(r[0]), "name": str(r[1]).strip(), "topic": str(r[2]).strip(),
            "depth": _truthy(r[3]), "resize": str(r[5] or "").strip(),
        } for r in _rows(df_cams) if str(r[2] or "").strip()],
        "state": list(state_keys or []),
        "action": list(action_keys or []),
        "extra_features": dict(extra_features or {}),
        "action_strategy": strategy,
        "auto_normalize": bool(auto_norm),
        "task_mode": task_mode,
        "task_text": task_text,
        "task_topic": task_topic,
        "segment_mode": segment_mode,
        "min_frames": int(min_frames or 30),
        "on_stale": on_stale,
        "tolerance_ms": int(tol_ms or 0),
        "bag_glob": bag_glob,
        "stamp_source": stamp_source,
        "chunk_size": int(chunk_size),
        "data_file_size_mb": int(data_size),
        "video_file_size_mb": int(video_size),
        "video_codec": codec,
    })
    if (curation_text or "").strip():
        try:
            ch["curation"] = _yaml.safe_load(curation_text)
        except Exception as exc:
            raise gr.Error(f"清洗配置 YAML 无法解析: {exc}") from exc
    return ch


def do_generate(profile, *args):
    if not profile:
        raise gr.Error("请先在「① 载入」页分析 bag")
    ch = collect_choices(profile, *args)
    plan = build_manifest(profile, ch)
    issues = validate_manifest(plan, profile)
    text = manifest_to_yaml(plan)
    tmp = Path(tempfile.mkdtemp(prefix="b2m_manifest_"))
    (tmp / "manifest.yaml").write_text(text, encoding="utf-8")
    (tmp / "profile.json").write_text(json.dumps(profile, ensure_ascii=False), encoding="utf-8")
    has_err = any(i["level"] == "error" for i in issues)
    banner = ("### 🔴 存在错误，请先修正\n" if has_err else
              "### ✅ 校验通过，可作为转换输入\n")
    next_step = (
        "\n---\n**下一步**\n\n"
        "1. 上面就是这份样例数据生成的全部配置，可直接编辑\n"
        "2. 改完点 **✅ 校验编辑后的 YAML** 复检\n"
        "3. 下载 `manifest.yaml` 交给后续转换流程；正式转换前建议先用少量 episode 试跑\n"
    )
    files = None if has_err else [str(tmp / "manifest.yaml"), str(tmp / "profile.json")]
    return text, banner + issues_md(issues, "配置校验") + next_step, files


def do_generate_guided(profile, action_confirm, *args):
    _need_profile(profile)
    strategy = args[2]
    if strategy == "stored" and not action_confirm and any(
            i["code"] == "E021" for i in profile.get("issues", [])):
        raise gr.Error("检测到多个候选动作话题。请到「④ 动作」核对字段映射，并勾选确认。")
    return do_generate(profile, *args)


def do_revalidate(profile, text):
    _need_profile(profile)
    try:
        data = _yaml.safe_load(text or "")
    except Exception as e:  # noqa: BLE001
        return f"### 🔴 YAML 解析失败\n```\n{e}\n```", None
    if not isinstance(data, dict):
        return "### 🔴 YAML 顶层必须是键值对", None
    issues = validate_manifest(data, profile)
    tmp = Path(tempfile.mkdtemp(prefix="b2m_edit_"))
    f = tmp / "manifest.yaml"
    f.write_text(text or "", encoding="utf-8")
    file = None if any(i["level"] == "error" for i in issues) else str(f)
    return issues_md(issues, "编辑后的 manifest.yaml 校验"), file


# --------------------------------------------------------------------------- #
# UI
# --------------------------------------------------------------------------- #
INTRO = f"""
# ROS Bag → LeRobot Manifest 2.0 配置工作台 <sub>v{__version__}</sub>

上传一条有代表性的 bag，依次核对**相机 → 状态 → 动作 → 输出**，再下载 `manifest.yaml`。
每一步都提供需要的编辑入口；不常用的选项可在该页按需展开。

> 仅上传用于分析的样例数据。Space 不会修改原始 bag；请勿上传包含敏感数据的文件。
"""

STATE_UI_CSS = """
.vector-workspace { align-items: flex-start; }
.vector-list { max-height: 360px; overflow-y: auto; }
.vector-toolbar { position: sticky; top: 0; z-index: 2; background: var(--background-fill-primary); }
"""

def build_ui() -> gr.Blocks:
    from .editor import build_editor, prepare, reconcile_refs, label
    with gr.Blocks(title='ROS Bag → Manifest 2.0', **_blocks_style()) as demo:
        profile=gr.State(None); state_vec=gr.State([]); previous_state=gr.State([])
        features=gr.State({}); feature_selection=gr.State(-1)
        gr.Markdown(INTRO)
        with gr.Tabs() as tabs:
            with gr.Tab('① 载入与体检',id=0,**_TAB_KW):
                fi=gr.File(label='上传样例 bag（MCAP / DB3 / BAG / ZIP）',file_count='multiple',type='filepath')
                with gr.Accordion('其他输入方式和分析选项',open=False):
                    dirs=gr.File(label='上传录制目录',file_count='directory',type='filepath')
                    path=gr.Textbox(label='服务器本地路径',visible=not _is_huggingface_space())
                    msgdir=gr.Textbox(label='自定义消息定义目录（多个用逗号分隔）')
                    quick=gr.Number(label='只分析前 N 秒（0=全部）',value=0,precision=0)
                analyze=gr.Button('开始分析',variant='primary')
                summary=gr.Markdown(); attention=gr.Markdown()
                with gr.Accordion('话题与体检详情',open=False):
                    topics=gr.Dataframe(headers=['话题','类型','分类','条数','Hz','内容'],interactive=False)
                    issues=gr.Markdown()
            with gr.Tab('② 相机',id=1,**_TAB_KW):
                cam_review=gr.Markdown()
                cams=gr.Dataframe(headers=CAM_HEADERS,datatype=['bool','str','str','bool','str','str'],interactive=True,wrap=True)
                gallery=gr.Gallery(label='按时间采样的相机预览',columns=6,height=250)
                reset_cam=gr.Button('恢复自动推断的相机')
                with gr.Row(): prev2=gr.Button('← 载入'); next2=gr.Button('状态 →',variant='primary')
            with gr.Tab('③ 状态',id=2,**_TAB_KW) as state_tab:
                state_review_md=gr.Markdown()
                state_editor=build_editor('state',profile,state_vec)
                with gr.Row(): prev3=gr.Button('← 相机'); next3=gr.Button('动作 →',variant='primary')
            with gr.Tab('④ 动作',id=3,**_TAB_KW) as action_tab:
                strategy=gr.Radio([('存储指令 stored','stored'),('整体使用下一帧状态','next_state')],value='next_state',label='动作来源')
                action_review_md=gr.Markdown()
                confirmation=gr.Checkbox(label='我已核对多个候选动作话题的映射',value=False,visible=False)
                with gr.Group() as action_group:
                    action_editor=build_editor('action',profile,state_vec,strategy)
                action_vec=action_editor['vec']
                next_note=gr.Markdown('整体 next_state：动作使用下一帧完整状态，末帧复制；不输出 fields。请确认符合训练目标。',visible=True)
                gr.Markdown('夹爪动作需要显式选择来源与尺度；不能仅凭曲线形状判断指令语义。')
                with gr.Row(): prev4=gr.Button('← 状态'); next4=gr.Button('其他特征 →',variant='primary')
            with gr.Tab('⑤ 其他特征',id=4,**_TAB_KW) as extra_tab:
                gr.Markdown('不需要额外特征可直接继续。编辑完成后点击“保存特征”；列表中的修改不会自动写入已保存特征。')
                with gr.Row():
                    feature_name=gr.Textbox(label='特征名',placeholder='observation.force / next.reward')
                    feature_save=gr.Button('保存特征',variant='primary')
                    feature_new=gr.Button('新建特征')
                    feature_delete=gr.Button('删除选中特征')
                feature_table=gr.Dataframe(headers=['特征名','维度','内容'],interactive=False)
                extra_editor=build_editor('extra',profile,state_vec)
                with gr.Row(): prev5=gr.Button('← 动作'); next5=gr.Button('输出 →',variant='primary')
            with gr.Tab('⑥ 输出与导出',id=5,**_TAB_KW) as output_tab:
                gr.Markdown('### 基本信息')
                with gr.Row():
                    repo=gr.Textbox(label='数据集 ID',placeholder='myorg/pick-place')
                    robot=gr.Textbox(label='robot_type',value='unknown')
                gr.Markdown('### 任务文本')
                task_mode=gr.Radio([('固定文本','const'),('从文本话题读取','topic')],value='const',label='先选择任务来源')
                task_text=gr.Textbox(label='固定任务文本',placeholder='pick up the red cube')
                task_topic=gr.Dropdown(label='文本话题',choices=[],value=None,visible=False)
                task_preview=gr.Markdown()
                gr.Markdown('固定任务文本的优先级：env task → task.txt → prompt.json → manifest文本 → lerobot_teleoperation。topic 模式是否也被外部文本覆盖，规范尚未明确。')
                gr.Markdown('### 采样与时间对齐')
                with gr.Row():
                    fps=gr.Number(label='输出 fps',value=30,precision=0)
                    stamp=gr.Radio(['auto','log_time','header_time','rosbag_time'],value='auto',label='消息时间戳来源')
                time_reason=gr.Markdown()
                gr.Markdown('时间戳来源决定每条消息使用什么时间，不是选择主相机。规范尚未定义输出主时间轴的生成方式与起止边界；此处不新增主话题配置。')
                with gr.Row():
                    tolerance_mode=gr.Radio([('自动：半帧时间','auto'),('手动指定','manual')],value='auto',label='对齐容差')
                    tolerance=gr.Number(label='手动容差 ms',value=50,precision=0,visible=False)
                tolerance_note=gr.Markdown('当前自动容差：**17ms**（30fps半帧）；省略此字段时规范默认50ms。')
                gr.Markdown('超时处理：**hold**（当前唯一支持）。字段的 nearest / linear / front 在状态、动作和其他特征编辑器中设置。容差与插值的具体判定、首帧回退行为需转换器定义。')
                gr.Markdown('### 正式输入与 episode')
                with gr.Row():
                    bag_glob=gr.Textbox(label='整批文件模式 source.bag_glob',value='*.db3')
                    minframes=gr.Number(label='最少帧数（不足则丢弃 episode）',value=30,precision=0)
                gr.Markdown('切分方式：**per_bag**（当前唯一支持）。同一录制的 DB3 分片应如何归组需与转换器确认；不要把样例文件类型直接当成正式批次类型。')
                with gr.Accordion('高级输出：分片、编码和清洗配置',open=False):
                    with gr.Row():
                        chunk=gr.Number(label='chunk_size',value=1000,precision=0)
                        data_size=gr.Number(label='data_file_size_mb',value=100,precision=0)
                        video_size=gr.Number(label='video_file_size_mb',value=200,precision=0)
                    codec=gr.Radio(['auto','libx264','libsvtav1'],value='auto',label='视频编码')
                    curation=gr.Code(label='curation 段内 YAML（原样传给下游，不在此处执行清洗）',language='yaml',lines=6)
                gr.Markdown('### 检查与导出')
                final_summary=gr.Markdown()
                with gr.Row(): prev6=gr.Button('← 其他特征'); generate=gr.Button('生成并校验 manifest.yaml',variant='primary')
                validation=gr.Markdown()
                with gr.Accordion('查看或编辑完整 YAML',open=False):
                    gr.Markdown('手动 YAML 不会反向更新表单。再次生成会按表单覆盖 YAML；手动修改应最后完成并重新校验。')
                    yaml_code=gr.Code(label='manifest.yaml',language='yaml',lines=24,interactive=True)
                    revalidate=gr.Button('校验编辑后的 YAML')
                downloads=gr.File(label='下载',file_count='multiple')
        def analyze_new(*args):
            old=do_analyze(*args); p=old[0]; ch=default_choices(p)
            st=prepare(ch['state']); act=prepare(ch['action'])
            texts=[(t['name'],t['name']) for t in p['topics'] if t['kind']=='text']
            return (p,old[1],old[2],old[3],old[28],cam_rows_from_choices(ch),old[5],st,act,
                    0 if st else -1,0 if act else -1,ch['action_strategy'],ch['fps'],ch['robot_type'],
                    'converted',ch['task_mode'],gr.update(value='',visible=ch['task_mode']=='const'),gr.update(choices=texts,value=ch['task_topic'] or None,visible=ch['task_mode']=='topic'),
                    ch['bag_glob'],ch['stamp_source'],{},[],[], -1,'',gr.update(selected=1),None,None,None,gr.update(visible=ch['action_strategy']=='stored'),gr.update(visible=ch['action_strategy']!='stored'))
        analyze.click(analyze_new,[fi,dirs,path,msgdir,quick],
                      [profile,summary,topics,issues,attention,cams,gallery,state_vec,action_vec,
                       state_editor['selected'],action_editor['selected'],strategy,fps,robot,repo,task_mode,task_text,task_topic,
                       bag_glob,stamp,features,extra_editor['vec'],feature_table,extra_editor['selected'],feature_name,tabs,
                       state_editor['undo'],action_editor['undo'],extra_editor['undo'],action_group,next_note])
        for section,editor in ((state_tab,state_editor),(action_tab,action_editor),(extra_tab,extra_editor)):
            section.select(editor['reload'],[profile,editor['vec'],editor['selected']],editor['editor_outputs'],queue=False)
        output_tab.select(lambda task,mode:(gr.update(visible=task=='const'),gr.update(visible=task=='topic'),gr.update(visible=mode=='manual')),
                          [task_mode,tolerance_mode],[task_text,task_topic,tolerance],queue=False)
        state_vec.change(lambda old,new,act:(reconcile_refs(old,new,act),new),
                         [previous_state,state_vec,action_vec],[action_vec,previous_state])
        for trigger in (state_vec,): trigger.change(state_review,[profile,state_vec],[state_review_md])
        for trigger in (state_vec,action_vec,strategy):
            trigger.change(action_review,[profile,state_vec,action_vec,strategy],[action_review_md])
        action_vec.change(lambda:False,None,[confirmation])
        def action_visibility(p,mode,confirmed=False):
            ambiguous=bool(p and any(i['code']=='E021' for i in p.get('issues',[])))
            return gr.update(visible=mode=='stored'),gr.update(visible=mode!='stored'),gr.update(visible=mode=='stored' and ambiguous,value=confirmed)
        strategy.change(action_visibility,[profile,strategy],[action_group,next_note,confirmation])
        action_tab.select(action_visibility,[profile,strategy,confirmation],[action_group,next_note,confirmation],queue=False)
        cams.change(do_refresh_gallery,[profile,cams],[gallery])
        cams.change(camera_review,[profile,cams],[cam_review])
        reset_cam.click(do_reset_cameras,[profile],[cams,gallery])
        task_mode.change(lambda mode:(gr.update(visible=mode=='const'),gr.update(visible=mode=='topic')),[task_mode],[task_text,task_topic])
        def preview_task(p,mode,topic,text):
            if mode=='const': return f'固定文本预览：{text or "未填写，将使用转换环境覆盖项或默认文本"}'
            samples=next((t.get('text_samples',[]) for t in (p or {}).get('topics',[]) if t['name']==topic),[])
            return '话题样本：\n\n'+'\n\n'.join(str(x) for x in samples[:3]) if samples else '请选择文本话题。'
        for trigger in (profile,task_mode,task_topic,task_text): trigger.change(preview_task,[profile,task_mode,task_topic,task_text],[task_preview])
        def clock_note(p,mode):
            suggestion=(p or {}).get('suggested',{}).get('time',{})
            return f'当前选择：**{mode}**。推断建议：**{suggestion.get("value","auto")}**。依据：{suggestion.get("why","先分析样例")}'
        for trigger in (profile,stamp): trigger.change(clock_note,[profile,stamp],[time_reason])
        tolerance_mode.change(lambda m:gr.update(visible=m=='manual'),[tolerance_mode],[tolerance])
        def tol_note(rate,mode,value):
            effective=max(1,round(500/max(float(rate or 30),1))) if mode=='auto' else value
            return f'将写入 tolerance_ms：**{effective} ms**。规范省略此字段时默认50ms；本页面自动模式按半帧计算。'
        for trigger in (profile,fps,tolerance_mode,tolerance): trigger.change(tol_note,[fps,tolerance_mode,tolerance],[tolerance_note])
        def summary_output(p,cam,st,act,mode,rate,task,topic,glob,clock,tolmode,tol,minimum):
            if not p: return '先载入样例，之后在这里检查最终配置。'
            count=sum(_truthy(r[0]) for r in _rows(cam))
            mixed=sum(isinstance(v,dict) and v.get('strategy')=='next_state' for v in act or [])
            effective=max(1,round(500/max(float(rate or 30),1))) if tolmode=='auto' else tol
            return (f'**{count} 路相机 · 状态 {len(st)} 维 · 动作 {len(st) if mode=="next_state" else len(act)} 维**\n\n'
                    f'动作：{mode}'+(f'，其中 {mixed} 维引用下一帧状态' if mode=='stored' else '')+
                    f'。任务：{task} {topic if task=="topic" else ""}。\n\n'
                    f'输出 {rate} fps · 时间源 {clock} · 容差 {effective}ms · 正式输入 `{glob}` · per_bag · 最少 {minimum} 帧。')
        summary_inputs=[profile,cams,state_vec,action_vec,strategy,fps,task_mode,task_topic,bag_glob,stamp,tolerance_mode,tolerance,minframes]
        for trigger in summary_inputs: trigger.change(summary_output,summary_inputs,[final_summary])
        def save_feature(p,d,nm,items): return do_feat_save(p,d,nm,items)
        feature_save.click(save_feature,[profile,features,feature_name,extra_editor['vec']],[features,feature_table,feature_name])
        def load_feature(d,evt:gr.SelectData):
            i=int(evt.index[0]); names=list(d); nm=names[i]
            return nm,prepare(d[nm]),0 if d[nm] else -1,i,None
        feature_table.select(load_feature,[features],[feature_name,extra_editor['vec'],extra_editor['selected'],feature_selection,extra_editor['undo']])
        feature_new.click(lambda:('',[],-1,-1,None),None,[feature_name,extra_editor['vec'],extra_editor['selected'],feature_selection,extra_editor['undo']])
        def remove_feature(d,i):
            d=dict(d); names=list(d)
            if 0<=i<len(names): d.pop(names[i])
            return d,_feat_rows(d),'',[],-1,-1,None
        feature_delete.click(remove_feature,[features,feature_selection],[features,feature_table,feature_name,extra_editor['vec'],extra_editor['selected'],feature_selection,extra_editor['undo']])
        for button,index in ((prev2,0),(next2,2),(prev3,1),(next3,3),(prev4,2),(next4,4),(prev5,3),(next5,5),(prev6,4)):
            button.click(lambda i=index:gr.update(selected=i),None,[tabs])
        # Saved extras are forwarded explicitly; unsaved feature drafts stay in the editor.
        def generate_with_extras(p,confirm,cam,st,act,mode,id_,robot_,rate,task,text,topic,minimum,tolmode,tol,codec_,glob,clock,chunk_,data_,video_,curation_,extras):
            if tolmode=='manual' and (tol is None or tol<=0): raise gr.Error('手动容差必须大于0')
            return do_generate_guided(p,confirm,cam,st,mode,act,extras,False,id_,robot_,rate,task,text,topic or '',
                'per_bag',minimum,'hold',0 if tolmode=='auto' else tol,codec_,glob,clock,chunk_,data_,video_,curation_)
        generate.click(generate_with_extras,[profile,confirmation,cams,state_vec,action_vec,strategy,repo,robot,fps,task_mode,task_text,task_topic,minframes,tolerance_mode,tolerance,codec,bag_glob,stamp,chunk,data_size,video_size,curation,features],[yaml_code,validation,downloads])
        revalidate.click(do_revalidate,[profile,yaml_code],[validation,downloads])
        # A previous download is invalid after a form edit or YAML edit.
        for trigger in (cams,state_vec,action_vec,strategy,repo,robot,fps,task_mode,task_text,task_topic,minframes,tolerance_mode,tolerance,codec,bag_glob,stamp,chunk,data_size,video_size,curation,features):
            trigger.change(lambda:('当前配置尚未校验或已修改，请重新生成并校验。',None),None,[validation,downloads])
        yaml_code.input(lambda:('YAML 已修改，请校验编辑后的 YAML。',None),None,[validation,downloads])
    return demo

def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="ROS2 → LeRobot v3 配置工作台")
    ap.add_argument("--host", default=os.getenv("GRADIO_SERVER_NAME", "0.0.0.0"))
    ap.add_argument("--port", type=int, default=int(os.getenv("PORT", "7860")))
    ap.add_argument("--share", action="store_true")
    a = ap.parse_args()
    demo = build_ui()
    demo.launch(server_name=a.host, server_port=a.port, share=a.share,
                **_launch_style())


if __name__ == "__main__":
    main()
