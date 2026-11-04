#!/usr/bin/env python3
"""生成一个"像真的"的合成 ROS2 mcap bag, 用于在没有真实数据时自测.

刻意包含了几个现实里常见的坑, 用来验证推断与告警是否生效:
  * 自定义消息 (my_robot_msgs/*)      -> 验证 schema 内嵌解码
  * 2 个候选动作话题                  -> 验证 E021 歧义告警
  * 一个恒定不变的状态通道            -> 验证 W106
  * 一个 header.stamp 全为 0 的话题   -> 验证 W041
  * /rosout /camera/camera_info 噪声  -> 验证自动忽略
  * 动作 = 状态向前平移               -> 叠加曲线上 action 应领先 state

用法:
    python tools/make_synth_bag.py -o /tmp/synth_demo.mcap --seconds 12
"""

from __future__ import annotations

import argparse
import io
import math
from pathlib import Path

import numpy as np

SEP = "\n" + "=" * 80 + "\n"

_TIME = "int32 sec\nuint32 nanosec\n"
_HEADER = "builtin_interfaces/Time stamp\nstring frame_id\n"


def _def(message_def: str, deps: dict[str, str]) -> str:
    out = message_def
    for name, body in deps.items():
        out += SEP + f"MSG: {name}\n" + body
    return out


_HDR_DEPS = {"std_msgs/Header": _HEADER, "builtin_interfaces/Time": _TIME}

DEFS: dict[str, str] = {
    "sensor_msgs/msg/Image": _def(
        "std_msgs/Header header\nuint32 height\nuint32 width\nstring encoding\n"
        "uint8 is_bigendian\nuint32 step\nuint8[] data\n", _HDR_DEPS),
    "sensor_msgs/msg/CompressedImage": _def(
        "std_msgs/Header header\nstring format\nuint8[] data\n", _HDR_DEPS),
    "sensor_msgs/msg/JointState": _def(
        "std_msgs/Header header\nstring[] name\nfloat64[] position\n"
        "float64[] velocity\nfloat64[] effort\n", _HDR_DEPS),
    "std_msgs/msg/Float64MultiArray": _def(
        "std_msgs/MultiArrayLayout layout\nfloat64[] data\n",
        {"std_msgs/MultiArrayLayout": "std_msgs/MultiArrayDimension[] dim\nuint32 data_offset\n",
         "std_msgs/MultiArrayDimension": "string label\nuint32 size\nuint32 stride\n"}),
    "std_msgs/msg/String": "string data\n",
    "rcl_interfaces/msg/Log": _def(
        "std_msgs/Header stamp_header\nuint8 level\nstring name\nstring msg\n", _HDR_DEPS),
    "sensor_msgs/msg/CameraInfo": _def(
        "std_msgs/Header header\nuint32 height\nuint32 width\nfloat64[] d\n", _HDR_DEPS),
    "tf2_msgs/msg/TFMessage": _def(
        "geometry_msgs/TransformStamped[] transforms\n",
        {"geometry_msgs/TransformStamped":
            "std_msgs/Header header\nstring child_frame_id\ngeometry_msgs/Transform transform\n",
         "geometry_msgs/Transform":
            "geometry_msgs/Vector3 translation\ngeometry_msgs/Quaternion rotation\n",
         "geometry_msgs/Vector3": "float64 x\nfloat64 y\nfloat64 z\n",
         "geometry_msgs/Quaternion": "float64 x\nfloat64 y\nfloat64 z\nfloat64 w\n",
         "std_msgs/Header": _HEADER, "builtin_interfaces/Time": _TIME}),
    # ---- 自定义消息: 现实里最常见的通用性挑战 ----
    "my_robot_msgs/msg/GripperState": _def(
        "std_msgs/Header header\nfloat64 width\nfloat64 force\nbool grasped\n", _HDR_DEPS),
    "my_robot_msgs/msg/GripperCommand":
        "float64 width\nfloat64 max_effort\n",
}

JOINTS = [f"panda_joint{i}" for i in range(1, 8)]


def _stamp(t: float) -> dict:
    return {"sec": int(t), "nanosec": int((t - int(t)) * 1e9)}


def _hdr(t: float, frame: str = "base") -> dict:
    return {"stamp": _stamp(t), "frame_id": frame}


def _rgb_frame(t: float, h: int, w: int, hue_shift: float = 0.0) -> np.ndarray:
    """背景渐变 + 一个来回移动的方块, 保证不同时刻缩略图肉眼可辨."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    img = np.zeros((h, w, 3), np.uint8)
    img[:, :, 0] = (xx / w * 120 + 40).astype(np.uint8)
    img[:, :, 1] = (yy / h * 120 + 30).astype(np.uint8)
    img[:, :, 2] = int(60 + 60 * math.sin(t * 0.7 + hue_shift))
    cx = int((0.5 + 0.4 * math.sin(t * 0.9 + hue_shift)) * w)
    cy = int((0.5 + 0.3 * math.cos(t * 0.6 + hue_shift)) * h)
    r = max(6, h // 10)
    y0, y1 = max(0, cy - r), min(h, cy + r)
    x0, x1 = max(0, cx - r), min(w, cx + r)
    img[y0:y1, x0:x1] = (250, 40, 40)
    return img


def _jpeg(arr: np.ndarray) -> bytes:
    from PIL import Image as PILImage

    buf = io.BytesIO()
    PILImage.fromarray(arr).save(buf, format="JPEG", quality=80)
    return buf.getvalue()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default="/tmp/synth_demo.mcap")
    ap.add_argument("--seconds", type=float, default=12.0)
    ap.add_argument("--height", type=int, default=180)
    ap.add_argument("--width", type=int, default=240)
    a = ap.parse_args()

    from mcap_ros2.writer import Writer as Ros2Writer

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    T0 = 1_700_000_000.0

    with out.open("wb") as fp:
        w = Ros2Writer(fp)
        sch = {name: w.register_msgdef(name, text) for name, text in DEFS.items()}

        def emit(topic: str, typ: str, msg: dict, t: float) -> None:
            ns = int(t * 1e9)
            w.write_message(topic, sch[typ], msg, log_time=ns, publish_time=ns)

        n_img = int(a.seconds * 30)
        for i in range(n_img):
            t = T0 + i / 30.0
            rel = i / 30.0
            rgb = _rgb_frame(rel, a.height, a.width)
            emit("/camera/color/image_raw", "sensor_msgs/msg/Image", {
                "header": _hdr(t, "camera_color"), "height": a.height, "width": a.width,
                "encoding": "rgb8", "is_bigendian": 0, "step": a.width * 3,
                "data": rgb.tobytes()}, t)
            emit("/wrist_cam/image_raw/compressed", "sensor_msgs/msg/CompressedImage", {
                "header": _hdr(t, "wrist"), "format": "jpeg",
                "data": _jpeg(_rgb_frame(rel, a.height, a.width, hue_shift=2.0))}, t)
            emit("/camera/camera_info", "sensor_msgs/msg/CameraInfo", {
                "header": _hdr(t), "height": a.height, "width": a.width, "d": [0.0] * 5}, t)
            emit("/tf", "tf2_msgs/msg/TFMessage", {"transforms": [{
                "header": _hdr(t, "panda_link0"), "child_frame_id": "panda_hand",
                "transform": {
                    "translation": {"x": 0.4 + 0.1 * math.sin(rel), "y": 0.05 * math.cos(rel),
                                    "z": 0.3 + 0.05 * math.sin(rel * 2)},
                    "rotation": {"x": 0.0, "y": 1.0, "z": 0.0, "w": 0.0}}}]}, t)

        # --- 状态 100Hz; joint7 故意恒定 -> 触发 W106 ---
        n_js = int(a.seconds * 100)
        for i in range(n_js):
            t = T0 + i / 100.0
            rel = i / 100.0
            pos = [0.6 * math.sin(rel * 0.8 + k * 0.5) for k in range(6)] + [0.0]
            vel = [0.48 * math.cos(rel * 0.8 + k * 0.5) for k in range(6)] + [0.0]
            emit("/joint_states", "sensor_msgs/msg/JointState", {
                "header": _hdr(t), "name": JOINTS, "position": pos,
                "velocity": vel, "effort": [0.0] * 7}, t)

        # --- 夹爪状态 (自定义消息) 50Hz, 物理量 0~0.08m -> 触发自动归一化建议 ---
        n_g = int(a.seconds * 50)
        for i in range(n_g):
            t = T0 + i / 50.0
            rel = i / 50.0
            width = 0.04 + 0.04 * math.sin(rel * 0.4)
            emit("/my_robot/gripper_state", "my_robot_msgs/msg/GripperState", {
                "header": _hdr(t), "width": width, "force": 3.0,
                "grasped": bool(width < 0.02)}, t)

        # --- 动作候选 1: 关节指令 = 状态向前 0.1s (曲线上应领先) ---
        n_a = int(a.seconds * 50)
        for i in range(n_a):
            t = T0 + i / 50.0
            rel = i / 50.0 + 0.1
            cmd = [0.6 * math.sin(rel * 0.8 + k * 0.5) for k in range(6)] + [0.0]
            emit("/arm_controller/commands", "std_msgs/msg/Float64MultiArray", {
                "layout": {"dim": [], "data_offset": 0}, "data": cmd}, t)
            emit("/gripper_controller/command", "my_robot_msgs/msg/GripperCommand", {
                "width": 0.04 + 0.04 * math.sin((rel + 0.1) * 0.4), "max_effort": 20.0}, t)

        # --- 动作候选 2: 末端速度指令 -> 制造 E021 歧义 ---
        for i in range(int(a.seconds * 20)):
            t = T0 + i / 20.0
            rel = i / 20.0
            emit("/servo_node/delta_twist_cmd", "std_msgs/msg/Float64MultiArray", {
                "layout": {"dim": [], "data_offset": 0},
                "data": [0.01 * math.sin(rel), 0.0, 0.01 * math.cos(rel), 0.0, 0.0, 0.0]}, t)

        # --- header.stamp 全 0 的话题 -> 触发 W041 ---
        for i in range(int(a.seconds * 10)):
            t = T0 + i / 10.0
            emit("/legacy_sensor/status", "sensor_msgs/msg/JointState", {
                "header": {"stamp": {"sec": 0, "nanosec": 0}, "frame_id": ""},
                "name": ["temp"], "position": [30.0 + math.sin(i / 10.0)],
                "velocity": [], "effort": []}, t)

        # --- 任务描述 + 噪声话题 ---
        for i in range(int(a.seconds)):
            t = T0 + i
            emit("/task_description", "std_msgs/msg/String",
                 {"data": "pick up the red cube and place it in the box"}, t)
            emit("/rosout", "rcl_interfaces/msg/Log", {
                "stamp_header": _hdr(t), "level": 20, "name": "driver", "msg": "ok"}, t)

        w.finish()

    size_mb = out.stat().st_size / 1e6
    print(f"✅ 生成 {out}  ({size_mb:.1f} MB, {a.seconds}s)")
    print("   下一步: python scripts/bag2manifest/start_web.py   然后在页面里填这个路径")


if __name__ == "__main__":
    main()
