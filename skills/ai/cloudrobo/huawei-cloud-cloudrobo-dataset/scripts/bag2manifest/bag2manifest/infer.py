"""映射推断规则 —— **唯一真相源**.

重要约定:
    Web 前端 **不得**重写这里的任何规则.
    它们只消费 ``profile["suggested"]``, 并展示 ``rule`` 字段作为依据.
    否则两套实现必然漂移, 预览与实跑不一致, 用户会彻底失去信任.

每条建议都带:
    value      推断结果
    rule       命中的规则 ID
    why        人话解释
    candidates 备选 (给 UI 做下拉)
"""

from __future__ import annotations

import re
from typing import Any

FPS_LADDER = [5, 10, 15, 20, 25, 30, 50, 60]

_CAM_NOISE = {
    "image_raw", "image", "imageraw", "compressed", "raw", "color", "rgb",
    "image_rect", "image_rect_raw", "image_color", "rect", "depth_registered",
    "sensor", "camera_node", "out", "data",
}
_ACTION_HINT = re.compile(r"(command|cmd|target|setpoint|goal|teleop|action|desired|ref|joint_plan)", re.I)
_STATE_HINT = re.compile(r"(state|status|feedback|joint|pose|odom|measured|current)", re.I)
_GRIPPER_HINT = re.compile(r"(gripper|finger|hand|jaw|claw|suction|width|inner_joint|outer_joint|knuckle)", re.I)
_TASK_HINT = re.compile(r"(task|instruction|language|prompt|description|goal_text)", re.I)


def _sug(value: Any, rule: str, why: str, **extra) -> dict:
    d = {"value": value, "rule": rule, "why": why}
    d.update(extra)
    return d


def _issue(code: str, level: str, title: str, detail: str = "", fix: list | None = None) -> dict:
    return {"code": code, "level": level, "title": title, "detail": detail, "fix": fix or []}


# --------------------------------------------------------------------------- #
def camera_name_from_topic(topic: str, taken: set[str]) -> str:
    """/wrist_cam/image_raw/compressed -> 'wrist';  /camera/color/image_raw -> 'camera'."""
    toks = [t for t in topic.strip("/").split("/") if t]
    keep = [t for t in toks if t.lower() not in _CAM_NOISE]
    base = keep[0] if keep else (toks[0] if toks else "cam")
    base = re.sub(r"_?(cam|camera)$", "", base, flags=re.I) or base
    base = re.sub(r"[^0-9a-zA-Z_]+", "_", base).strip("_").lower() or "cam"
    if base in taken and len(keep) > 1:
        base = f"{base}_{re.sub(r'[^0-9a-zA-Z]+', '', keep[1]).lower()}"
    name, i = base, 2
    while name in taken:
        name, i = f"{base}{i}", i + 1
    return name


def snap_fps(hz: float) -> int:
    """把源频率转成输出 fps.

    原则: 不高于源频率 (避免上采样/重复帧). 若源频率离档位足够近(≤0.5Hz)则取档位,
    否则向下取整 —— 例如 9.0Hz 应得到 9 而不是硬压到 5.
    """
    if hz <= 0:
        return 30
    nearest = min(FPS_LADDER, key=lambda f: abs(f - hz))
    if abs(nearest - hz) <= 0.5:
        return nearest
    return max(1, int(hz + 1e-6))


def _by_name(profile: dict) -> dict[str, dict]:
    return {t["name"]: t for t in profile["topics"]}


def _numeric_fields(t: dict) -> list[dict]:
    return [f for f in t.get("fields", []) if not f.get("constant")]


_IDX_RE = re.compile(r"^(.*)\[([^\]]+)\]$")


def vector_fields(t: dict) -> list[dict]:
    """取出话题里的"主向量字段组".

    为什么需要: ``Float64MultiArray.data[0..6]`` 是一个 7 维物理量,
    即使某一维在样例 bag 里恒为 0 也 **不能丢** —— 丢了会导致不同批次维度不一致,
    也会混入 ``layout.data_offset`` 这类元数据字段.

    策略: 把形如 ``prefix[i]`` 的字段按 prefix 分组, 取最大的一组并 **完整保留**;
          没有数组组时退化为"所有非恒定标量字段".
    """
    fields = t.get("fields", [])
    groups: dict[str, list[dict]] = {}
    for f in fields:
        m = _IDX_RE.match(f["path"])
        if m:
            groups.setdefault(m.group(1), []).append(f)
    if groups:
        def score(kv):
            key, items = kv
            varying = sum(0 if i["constant"] else 1 for i in items)
            # position 组优先于 velocity/effort 组
            pri = 0 if key.split(".")[-1] in ("position", "data", "positions") else 1
            return (-len(items), pri, -varying)

        key, items = sorted(groups.items(), key=score)[0]
        if len(items) >= 2 and any(not i["constant"] for i in items):
            def order(f):
                m = _IDX_RE.match(f["path"])
                sub = m.group(2) if m else ""
                return (0, int(sub)) if sub.isdigit() else (1, sub)

            return sorted(items, key=order)
    return _numeric_fields(t)


# --------------------------------------------------------------------------- #
def infer_plan(profile: dict) -> tuple[dict, list[dict]]:
    """从 profile 推断映射建议. 返回 ``(suggested, issues)``."""
    topics = profile["topics"]
    issues: list[dict] = []
    sug: dict[str, Any] = {}

    # ---------------- 相机 ---------------------------------------------------
    cams = [t for t in topics if t["kind"] in ("image", "compressed_image")]
    cam_map: dict[str, dict] = {}
    taken: set[str] = set()
    for t in sorted(cams, key=lambda x: x["name"]):
        if t["hz"] < 1.0:
            issues.append(_issue(
                "W011", "warn", f"相机 {t['name']} 频率过低 ({t['hz']}Hz)",
                "低于 1Hz 的图像流通常不是主相机, 已默认不启用",
                [{"how": "如确实需要, 在「相机」页手动勾选启用"}]))
            continue
        info = t.get("image") or {}
        is_depth = bool(info.get("is_depth"))
        name = camera_name_from_topic(t["name"], taken)
        taken.add(name)
        cam_map[name] = {
            "topic": t["name"],
            "enabled": not is_depth,          # 深度默认不开, 需用户显式确认
            "is_depth": is_depth,
            "width": info.get("width"),
            "height": info.get("height"),
            "encoding": info.get("encoding"),
            "hz": t["hz"],
            "rule": "R-CAM-02(depth)" if is_depth else "R-CAM-01",
        }
        if t.get("decode_error"):
            issues.append(_issue(
                "E013", "error", f"相机 {t['name']} 解码异常", str(t["decode_error"]),
                [{"how": "确认 encoding 在支持列表内 (rgb8/bgr8/mono8/16UC1/32FC1/jpeg/png)"}]))
        if t.get("size_stable") is False:
            issues.append(_issue(
                "E014", "error", f"相机 {t['name']} 分辨率不稳定",
                "同一话题内图像尺寸发生变化, LeRobot 要求固定 shape",
                [{"how": "在「相机」页设置统一的 resize 目标尺寸",
                  "snippet": "resize: [480, 640]"}]))
    sug["cameras"] = cam_map

    # ---------------- fps ----------------------------------------------------
    active_hz = [c["hz"] for c in cam_map.values() if c["enabled"]]
    if active_hz:
        fps = snap_fps(min(active_hz))
        sug["fps"] = _sug(fps, "R-FPS-01", f"取最低启用相机频率 {min(active_hz)}Hz, 向下取档")
    else:
        num_hz = [t["hz"] for t in topics if t["kind"] == "numeric" and t["hz"] > 1]
        fps = snap_fps(min(num_hz)) if num_hz else 30
        sug["fps"] = _sug(fps, "R-FPS-02", "无相机, 取最低数值话题频率")
        issues.append(_issue(
            "W021", "warn", "没有启用任何相机",
            "生成的数据集将只有低维信号, 多数 VLA 策略无法训练",
            [{"how": "在「相机」页启用至少一个图像话题"}]))

    # ---------------- 状态 ---------------------------------------------------
    state_parts: list[str] = []
    state_rule = None
    js = [t for t in topics if t["type"] == "sensor_msgs/msg/JointState"
          and not _ACTION_HINT.search(t["name"])
          and any(f["path"].startswith("position[") for f in t.get("fields", []))]
    if js:
        t = max(js, key=lambda x: x["hz"])
        # 注意: 这里 **保留恒定关节**. 样例 bag 里没动 ≠ 全量数据里不动,
        # 静默丢一维会导致 state 维度与其他批次不一致. 改为在校验阶段 W106 提醒.
        pos = [f["path"] for f in t.get("fields", []) if f["path"].startswith("position[")]
        state_parts += [f"{t['name']}.{p}" for p in pos]
        state_rule = "R-ST-01"
        const_pos = [p for p in pos
                     if next(f for f in t["fields"] if f["path"] == p).get("constant")
                     or next(f for f in t["fields"] if f["path"] == p).get("near_constant")]
        if const_pos:
            issues.append(_issue(
                "W105", "warn", f"{len(const_pos)} 个关节在样例 bag 中基本不动",
                "已保留在状态向量里(避免不同批次维度不一致), 但请确认传感器正常:\n"
                + "\n".join(const_pos),
                [{"how": "若确实是冗余通道, 在「状态」页取消勾选"}]))
    if not state_parts:
        cands = [t for t in topics
                 if t["kind"] == "numeric" and _STATE_HINT.search(t["name"])
                 and not _ACTION_HINT.search(t["name"]) and _numeric_fields(t)]
        if cands:
            t = max(cands, key=lambda x: (len(vector_fields(x)), x["hz"]))
            state_parts = [f"{t['name']}.{f['path']}" for f in vector_fields(t)]
            state_rule = "R-ST-03"

    # 夹爪追加. 要求有像样的频率: 极稀疏(如几帧的指令回读)通常是命令而非状态流
    grip = [t for t in topics
            if t["kind"] == "numeric" and _GRIPPER_HINT.search(t["name"])
            and not _ACTION_HINT.search(t["name"]) and _numeric_fields(t)
            and t["hz"] >= 0.5]
    for t in grip:
        best = _pick_gripper_field(t)
        if best:
            key = f"{t['name']}.{best}"
            if key not in state_parts:
                state_parts.append(key)
                state_rule = (state_rule or "R-ST-02") + "+R-ST-02"

    if state_parts:
        sug["state"] = _sug(state_parts, state_rule or "R-ST-01",
                            f"共 {len(state_parts)} 维")
    else:
        sug["state"] = _sug([], "R-ST-00", "未找到状态源")
        issues.append(_issue(
            "E022", "error", "找不到状态 (observation.state) 来源",
            "没有 JointState, 也没有名字含 state/status/feedback 的数值话题",
            [{"how": "在「状态」页手动勾选字段拼成状态向量"}]))

    # ---------------- 动作 ---------------------------------------------------
    # 夹爪指令不参与主候选，也不自动追加；由用户显式配置 expr/next_state。
    act_cands = [t for t in topics
                 if t["kind"] == "numeric" and _ACTION_HINT.search(t["name"])
                 and not _GRIPPER_HINT.search(t["name"]) and _numeric_fields(t)]
    state_dim = len(state_parts)
    arm_dim = sum(not _GRIPPER_HINT.search(x) for x in state_parts)
    if len(act_cands) == 1:
        t = act_cands[0]
        parts = [f"{t['name']}.{f['path']}" for f in vector_fields(t)]
        sug["action"] = _sug(parts, "R-ACT-01", f"话题名含动作关键词: {t['name']}",
                             strategy="stored", candidates=[t["name"]])
    elif len(act_cands) > 1:
        scored = sorted(
            act_cands,
            key=lambda x: (abs(len(vector_fields(x)) - arm_dim), -x["hz"]))
        best = scored[0]
        parts = [f"{best['name']}.{f['path']}" for f in vector_fields(best)]
        sug["action"] = _sug(parts, "R-ACT-02",
                             f"{len(act_cands)} 个候选, 按与手臂状态维度({arm_dim})的接近度选中 {best['name']}",
                             strategy="stored",
                             candidates=[t["name"] for t in act_cands])
        issues.append(_issue(
            "E021", "error", f"检测到 {len(act_cands)} 个候选动作话题, 无法自动确定",
            "\n".join(f"{t['name']}  ({len(vector_fields(t))} 维, {t['hz']}Hz)" for t in act_cands),
            [{"how": "在「动作」页选定一个话题, 并用叠加曲线图确认与状态的关系"},
             {"how": "或直接编辑 manifest.yaml 的 action 段", "snippet": "action:\n  strategy: stored\n  fields:\n    - locator: " + parts[0]},
             {"how": "或改用 next_state 策略 (动作 = 下一帧状态)", "snippet": "action:\n  strategy: next_state"}]))
    else:
        sug["action"] = _sug([], "R-ACT-03", "未找到动作话题, 回退为 action = 下一帧状态",
                             strategy="next_state", candidates=[])
        issues.append(_issue(
            "D101", "warn", "未找到动作话题, 已回退 next_state",
            "action[t] 将取 observation.state[t+1], 末帧复制. 这对遥操作数据通常可用, "
            "但如果你的机器人有独立的指令话题, 请手动指定.",
            [{"how": "在「动作」页改选具体话题"}]))

    if sug["action"].get("strategy") == "stored" and any(_GRIPPER_HINT.search(p) for p in state_parts):
        issues.append(_issue(
            "W110", "warn", "夹爪动作需要显式配置",
            "夹爪话题不进入主动作候选。请选择计算字段或 per-field next_state，标记 role: gripper；不要假定状态与命令同尺度。",
            [{"how": "在动作页添加下一帧状态维度，或手动添加夹爪表达式"}]))

    # ---------------- 任务描述 -----------------------------------------------
    task_topics = [t for t in topics if t["kind"] == "text" and _TASK_HINT.search(t["name"])]
    if task_topics and task_topics[0].get("text_samples"):
        sug["task"] = _sug(task_topics[0]["name"], "R-TASK-01",
                           f"话题样本: {task_topics[0]['text_samples'][0][:60]}",
                           mode="topic", samples=task_topics[0]["text_samples"])
    else:
        sug["task"] = _sug("", "R-TASK-02", "未找到任务描述来源, 需填写常量任务文本或提供 task.txt/prompt.json",
                           mode="const", samples=[])
        issues.append(_issue(
            "W031", "warn", "没有任务描述来源",
            "LeRobot 需要每条 episode 绑定一段自然语言任务描述",
            [{"how": "在「输出」页直接填写任务文本"},
             {"how": "或在数据集目录放 task.txt 或 prompt.json", "snippet": 'pick the red cube'}]))

    # ---------------- 时间戳质量 ---------------------------------------------
    scalar = [t for t in topics
              if t["kind"] not in ("image", "compressed_image") and t.get("sampled", 0) > 0]
    bad_stamp = [t["name"] for t in scalar
                 if t.get("has_header") and t.get("stamp_valid_ratio", 1.0) < 0.5]
    no_header = [t["name"] for t in scalar if not t.get("has_header")]
    if bad_stamp:
        issues.append(_issue(
            "W041", "warn", f"{len(bad_stamp)} 个话题有 header 但 stamp 未填写",
            "驱动没填时间戳, 将回退 bag 记录时间(log_time), 跨机采集时可能引入对齐误差:\n"
            + "\n".join(bad_stamp[:8]),
            [{"how": "如果确认时钟同步良好可忽略"},
             {"how": "或全局强制使用 log_time", "snippet": "source:\n  time:\n    stamp_source: log_time"}]))
    if no_header:
        issues.append(_issue(
            "I042", "info", f"{len(no_header)} 个话题的消息类型不含 header",
            "这些话题只能用 bag 记录时间(log_time)对齐, 会引入约一个传输延迟的偏差 "
            "(通常 1~5ms, 一般可接受):\n" + "\n".join(no_header[:8]),
            [{"how": "请确认采集端同一时钟域，必要时统一使用 source.time.stamp_source: log_time"}]))

    # header 时钟与 bag 记录时钟不一致 (相对时间戳驱动) —— 必须强制 log_time, 否则跨话题错位
    mismatched = [(t["name"], t.get("clock_delta_s")) for t in topics
                  if t.get("clock_mismatch")]
    sug["time"] = _sug("auto", "R-TIME-01", "header 与 log_time 一致, 自动即可")
    if mismatched:
        worst = max(mismatched, key=lambda x: abs(x[1] or 0))
        sug["time"] = _sug(
            "log_time", "R-TIME-02",
            "header.stamp 与 bag 记录时间不在同一时钟域, 必须统一用 log_time 对齐")
        issues.append(_issue(
            "W043", "warn", f"{len(mismatched)} 个话题的 header.stamp 与 bag 记录时间相差过大",
            "这些话题的 header 用的是相对时间(如驱动/仿真计时), 与 bag 的 log_time 不是同一时钟。\n"
            "若按 header 对齐, 会与其他无 header 的指令话题错位数十万秒。\n"
            f"最大差值示例: {worst[0]} = {worst[1]:.1f}s\n受影响话题:\n"
            + "\n".join(f"  {n}  (+{d:.1f}s)" for n, d in mismatched[:10]),
            [{"how": "转换时统一使用 bag 记录时间 (已默认勾选, 无需手动改)",
              "snippet": "source:\n  time:\n    stamp_source: log_time"},
             {"how": "如果采集端能提供与系统时钟同步的 header.stamp, 重新采集可避免此问题"}]))

    sug["segment"] = _sug("per_bag", "R-SEG-01", "默认一个 bag 一条 episode")
    sug["robot_type"] = _sug("unknown", "R-ROB-01", "无法自动识别, 建议手工填写")
    return sug, issues


def _pick_gripper_field(t: dict) -> str | None:
    fields = _numeric_fields(t)
    if not fields:
        return None
    named = [f for f in fields if _GRIPPER_HINT.search(f["path"])]
    pool = named or fields
    pool = sorted(pool, key=lambda f: (0 if "position" in f["path"] or "width" in f["path"] else 1,
                                       len(f["path"])))
    return pool[0]["path"]
