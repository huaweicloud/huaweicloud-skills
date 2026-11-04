#!/usr/bin/env python3
"""端到端冒烟测试 (无需 pytest):  python tests/smoke_test.py

用合成 bag 验证"该报的告警都报出来了" —— 推断规则的回归测试.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bag2manifest.manifest import build_manifest, default_choices, manifest_to_yaml, validate_manifest, expand_locator, _field_stats  # noqa: E402
from bag2manifest.profiler import ProfileOptions, profile_bag  # noqa: E402

FAILED: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(("  ✅ " if cond else "  ❌ ") + msg)
    if not cond:
        FAILED.append(msg)


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="b2m_smoke_"))
    bag = tmp / "synth.mcap"
    print(f"[1/5] 生成合成 bag -> {bag}")
    subprocess.run([sys.executable, str(ROOT / "tools/make_synth_bag.py"),
                    "-o", str(bag), "--seconds", "10"], check=True,
                   stdout=subprocess.DEVNULL)

    print("[2/5] 扫描")
    p = profile_bag(bag, ProfileOptions())
    names = {t["name"] for t in p["topics"]}
    codes = {i["code"] for i in p["issues"]}

    check(p["source"]["backend"] == "mcap", "mcap 后端被选中")
    check("/rosout" not in names and "/camera/camera_info" not in names, "噪声话题被自动忽略")
    check("/my_robot/gripper_state" in names, "自定义消息可解码 (schema 内嵌)")

    print("[3/5] 校验推断")
    sug = p["suggested"]
    cams = sug["cameras"]
    check(set(cams) == {"camera", "wrist"}, f"相机命名自动派生: {list(cams)}")
    check(all(len(t.get("thumbnails", [])) >= 3
              for t in p["topics"] if t.get("image")), "两路相机都解出缩略图")
    check(sug["fps"]["value"] == 30, f"fps 推断为 30 (实际 {sug['fps']['value']})")
    check(len(sug["state"]["value"]) == 8, f"状态 8 维 (实际 {len(sug['state']['value'])})")
    check(len(sug["action"]["value"]) == 7, f"仅自动选择手臂动作 7 维 (实际 {len(sug['action']['value'])})")
    check("E021" in codes, "多候选动作话题 -> E021")
    check("W105" in codes, "恒定关节 -> W105 (且未被静默丢弃)")
    check("W041" in codes, "stamp 全 0 -> W041")
    check("I042" in codes, "无 header 的消息类型 -> I042")
    check(sug["task"]["mode"] == "topic", "任务描述话题被识别")

    print("[4/5] 生成并校验 manifest.yaml")
    plan = build_manifest(p, default_choices(p))
    text = manifest_to_yaml(plan)
    v = validate_manifest(plan, p)
    grip = [x for x in plan["state"] if isinstance(x, dict) and x.get("role") == "gripper"]
    check(bool(grip) and "normalize" not in grip[0],
          "夹爪状态标 role 且保持原始尺度")
    check(plan["schema_version"] == "2.0" and plan["source_type"] == "ros2", "导出 ROS Manifest 2.0")
    check(sum(len(expand_locator(x, _field_stats(p))) for x in plan["state"]) == 8, "合并后的状态字段仍保留 8 维")
    check(plan["state"][0]["names_from"] == "embedded", "JointState 按名称反查且保留有序 names")
    check("W110" in codes and "W109" in {x["code"] for x in v}, "提示显式配置夹爪动作及维度差异")
    check(not any(i["level"] == "error" for i in v),
          f"默认配置无 error 级问题 (实际 {[i['code'] for i in v if i['level'] == 'error']})")

    print("[5/6] db3 无 metadata.yaml + 自定义消息")
    _test_db3_no_metadata(tmp)

    print("[6/6] 计算字段 (表达式) 与其他特征")
    _test_expr_and_extra(p)

    print(f"\n{'❌ 失败 ' + str(len(FAILED)) if FAILED else '✅ 全部通过'}")
    for f in FAILED:
        print("   -", f)
    return 1 if FAILED else 0


def _test_expr_and_extra(profile: dict) -> None:
    """计算字段表达式 + 其他特征."""
    ch = default_choices(profile)
    base = [x for x in ch["state"] if "gripper" not in x]
    ch["state"] = base + [{
        "expr": "abs(f0) + abs(f1)",
        "inputs": ["/joint_states.position[panda_joint1]",
                   "/joint_states.position[panda_joint2]"],
        "name": "j12_sum", "normalize": True,
    }]
    ch["extra_features"] = {
        "observation.joint_sq": [{
            "expr": "f0*f0", "inputs": ["/joint_states.position[panda_joint1]"],
            "name": "j1_sq"}],
    }
    plan = build_manifest(profile, ch)
    text = manifest_to_yaml(plan)
    v = validate_manifest(plan, profile)
    expr_items = [x for x in plan["state"] if isinstance(x, dict) and "expr" in x]
    check(bool(expr_items) and len(expr_items[0].get("normalize", [])) == 2,
          "计算字段写入 manifest 并自动算出归一化区间")
    check("extra_features" in plan and "observation.joint_sq" in plan["extra_features"],
          "其他特征写入 manifest")
    check("expr:" in text and "extra_features:" in text, "manifest.yaml 含 expr 与 extra_features")
    check(not any(i["level"] == "error" for i in v),
          f"含计算字段时无 error (实际 {[i['code'] for i in v if i['level'] == 'error']})")

    bad = dict(ch)
    bad["state"] = base + [{"expr": "f0 +", "inputs": ["/joint_states.position[panda_joint1]"]}]
    codes = {i["code"] for i in validate_manifest(build_manifest(profile, bad), profile)}
    check("E112" in codes, "非法表达式 -> E112")


def _test_db3_no_metadata(tmp: Path) -> None:
    """构造一个没有 metadata.yaml 的 db3 (含自定义消息), 验证两条路径."""
    import numpy as np
    from rosbags.rosbag2 import Writer
    from rosbags.typesys import Stores, get_typestore, get_types_from_msg

    msgroot = tmp / "ws/src/my_robot_msgs/msg"
    msgroot.mkdir(parents=True, exist_ok=True)
    (msgroot / "GripperState.msg").write_text(
        "std_msgs/Header header\nfloat64 width\nfloat64 force\nbool grasped\n")
    ts = get_typestore(Stores.ROS2_HUMBLE)
    ts.register(get_types_from_msg((msgroot / "GripperState.msg").read_text(),
                                   "my_robot_msgs/msg/GripperState"))

    out = tmp / "db3bag"
    Grip = ts.types["my_robot_msgs/msg/GripperState"]
    Hdr = ts.types["std_msgs/msg/Header"]
    Time = ts.types["builtin_interfaces/msg/Time"]
    with Writer(out, version=9) as w:
        c = w.add_connection("/gripper/state", "my_robot_msgs/msg/GripperState", typestore=ts)
        for i in range(200):
            t = 1_700_000_000_000_000_000 + int(i * 2e7)
            hdr = Hdr(stamp=Time(sec=t // 10**9, nanosec=t % 10**9), frame_id="b")
            w.write(c, t, ts.serialize_cdr(
                Grip(header=hdr, width=0.02 + 0.02 * abs(np.sin(i / 20)),
                     force=3.0, grasped=bool(i % 2)),
                "my_robot_msgs/msg/GripperState"))
    # 故意删掉 metadata.yaml
    (out / "metadata.yaml").unlink(missing_ok=True)

    db3_file = next(out.glob("*.db3"))
    p_file = profile_bag(db3_file, ProfileOptions(image_samples=1))
    check(p_file["source"]["backend"] == "sqlite3", "直接选 .db3 文件可读 (无 metadata.yaml)")
    p_dir = profile_bag(out, ProfileOptions(image_samples=1))
    check(p_dir["source"]["backend"] == "sqlite3", "选整个目录可读 (无 metadata.yaml)")
    check("E015" in {i["code"] for i in p_dir["issues"]}, "自定义消息缺定义 -> E015")

    p_ok = profile_bag(out, ProfileOptions(image_samples=1, msg_dirs=[str(tmp / "ws/src")]))
    fields = [f["path"] for t in p_ok["topics"] for f in t.get("fields", [])]
    check({"width", "force", "grasped"} <= set(fields),
          f"提供 msg_dir 后可解析自定义字段: {fields}")


if __name__ == "__main__":
    raise SystemExit(main())
