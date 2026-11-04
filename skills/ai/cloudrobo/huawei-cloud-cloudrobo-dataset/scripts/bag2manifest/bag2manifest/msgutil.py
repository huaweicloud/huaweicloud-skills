"""消息解析工具: 类型分类 / 数值字段展平 / 图像解码.

设计要点:
  * 展平是 **通用兜底**: 任何自定义消息都能靠反射把数值叶子抽出来,
    因此 Web 端不需要为新消息类型写代码.
  * JointState 按 name 取值而非下标 —— ROS 不保证关节顺序稳定.
"""

from __future__ import annotations

import io
import math
import re
from contextlib import closing
from typing import Any

import numpy as np

MAX_ARRAY_EXPAND = 64      # 数组最多展开多少维, 防止 PointCloud2 之类炸掉
# layout 是 MultiArray 的元数据 (dims/data_offset), 不是传感器信号
_SKIP_FIELDS = {"header", "layout", "_type", "__msgtype__"}

IMAGE_TYPES = {"sensor_msgs/msg/Image"}
COMPRESSED_TYPES = {"sensor_msgs/msg/CompressedImage"}
PC2_TYPES = {"sensor_msgs/msg/PointCloud2"}
TF_TYPES = {"tf2_msgs/msg/TFMessage"}
TEXT_TYPES = {"std_msgs/msg/String"}
IGNORE_TOPICS = re.compile(
    r"^(/rosout|/parameter_events|/diagnostics.*|/clock|.*/camera_info|.*/theora|.*/compressedDepth)$"
)


# --------------------------------------------------------------------------- #
# 分类
# --------------------------------------------------------------------------- #
def classify(msgtype: str, topic: str = "") -> str:
    """-> 'image' | 'compressed_image' | 'pointcloud' | 'tf' | 'text' | 'numeric'"""
    if msgtype in IMAGE_TYPES:
        return "image"
    if msgtype in COMPRESSED_TYPES:
        return "compressed_image"
    if msgtype in PC2_TYPES:
        return "pointcloud"
    if msgtype in TF_TYPES:
        return "tf"
    if msgtype in TEXT_TYPES:
        return "text"
    return "numeric"


def is_ignorable(topic: str) -> bool:
    return bool(IGNORE_TOPICS.match(topic))


# --------------------------------------------------------------------------- #
# 时间戳
# --------------------------------------------------------------------------- #
def stamp_ns(msg: Any) -> int | None:
    """从 header.stamp 取时间, 取不到返回 None."""
    h = getattr(msg, "header", None)
    st = getattr(h, "stamp", None) if h is not None else getattr(msg, "stamp", None)
    if st is None:
        return None
    sec = getattr(st, "sec", None)
    nsec = getattr(st, "nanosec", getattr(st, "nsec", None))
    if sec is None or nsec is None:
        return None
    v = int(sec) * 1_000_000_000 + int(nsec)
    return v if v > 0 else None


# --------------------------------------------------------------------------- #
# 数值展平
# --------------------------------------------------------------------------- #
def _iter_fields(msg: Any):
    """产出 (name, value), 兼容 rosbags dataclass 与 mcap_ros2 动态对象."""
    slots = getattr(msg, "__slots__", None)
    if slots:
        for n in slots:
            if n in _SKIP_FIELDS or n.startswith("_"):
                continue
            yield n, getattr(msg, n, None)
        return
    fields = getattr(msg, "__dataclass_fields__", None)
    if fields:
        for n in fields:
            if n in _SKIP_FIELDS or n.startswith("_"):
                continue
            yield n, getattr(msg, n, None)
        return
    d = getattr(msg, "__dict__", None)
    if isinstance(d, dict):
        for n, v in d.items():
            if n in _SKIP_FIELDS or n.startswith("_"):
                continue
            yield n, v


def _seq(v: Any) -> list:
    """安全取序列: numpy 数组不能用 ``or []`` (真值判断会抛异常)."""
    if v is None:
        return []
    if isinstance(v, np.ndarray):
        return v.tolist()
    if isinstance(v, (list, tuple)):
        return list(v)
    return []


def _is_scalar_num(v: Any) -> bool:
    return isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, bool)


def flatten_numeric(msg: Any, msgtype: str = "", prefix: str = "", depth: int = 0) -> dict[str, float]:
    """把消息里所有数值叶子展平成 ``{路径: 值}``.

    路径示例::
        position[panda_joint1]      # JointState 按名字
        pose.position.x
        data[3]
        gripper.width
    """
    out: dict[str, float] = {}
    if msg is None or depth > 6:
        return out

    # --- JointState 特化: 按 name 索引 ---
    if msgtype == "sensor_msgs/msg/JointState" and depth == 0:
        names = [str(x) for x in _seq(getattr(msg, "name", None))]
        for arr_name in ("position", "velocity", "effort"):
            arr = np.asarray(_seq(getattr(msg, arr_name, None)), dtype=float).ravel()
            for i, val in enumerate(arr[:MAX_ARRAY_EXPAND]):
                key = names[i] if i < len(names) and names[i] else str(i)
                if math.isfinite(val):
                    out[f"{arr_name}[{key}]"] = float(val)
        return out

    for name, val in _iter_fields(msg):
        path = f"{prefix}{name}"
        if val is None:
            continue
        if isinstance(val, bool):
            out[path] = float(val)
        elif _is_scalar_num(val):
            if math.isfinite(float(val)):
                out[path] = float(val)
        elif isinstance(val, (str, bytes, bytearray, memoryview)):
            continue
        elif isinstance(val, np.ndarray):
            if val.dtype.kind in "fiub":
                flat = val.ravel()[:MAX_ARRAY_EXPAND].astype(float)
                for i, v in enumerate(flat):
                    if math.isfinite(v):
                        out[f"{path}[{i}]"] = float(v)
        elif isinstance(val, (list, tuple)):
            if not val:
                continue
            if all(_is_scalar_num(x) or isinstance(x, bool) for x in val[:8]):
                for i, v in enumerate(val[:MAX_ARRAY_EXPAND]):
                    fv = float(v)
                    if math.isfinite(fv):
                        out[f"{path}[{i}]"] = fv
            else:
                for i, sub in enumerate(val[:8]):
                    out.update(flatten_numeric(sub, "", f"{path}[{i}].", depth + 1))
        else:
            out.update(flatten_numeric(val, "", f"{path}.", depth + 1))
    return out


def flatten_text(msg: Any) -> dict[str, str]:
    out: dict[str, str] = {}
    for name, val in _iter_fields(msg):
        if isinstance(val, str) and val:
            out[name] = val[:200]
    return out


def unit_guess(path: str, lo: float, hi: float) -> str:
    p = path.lower()
    if "quat" in p or re.search(r"orientation\.[wxyz]$", p):
        return "quat"
    if "position[" in p and abs(hi) <= 7 and abs(lo) <= 7:
        return "rad?"
    if "gripper" in p or "finger" in p or "width" in p:
        return "gripper?"
    if "velocity" in p or "twist" in p:
        return "vel"
    if "effort" in p or "torque" in p or "wrench" in p:
        return "torque"
    return ""


# --------------------------------------------------------------------------- #
# 图像解码
# --------------------------------------------------------------------------- #
def _as_uint8_buf(data: Any) -> np.ndarray:
    if isinstance(data, np.ndarray):
        return data.astype(np.uint8, copy=False).ravel()
    return np.frombuffer(bytes(data), dtype=np.uint8)


DEPTH_ENCODINGS = {"16UC1", "32FC1", "mono16", "16SC1"}


def decode_image(msg: Any, msgtype: str) -> tuple[np.ndarray | None, dict]:
    """解码成 HxWx3 uint8 (可视化用) + 元信息.

    Returns:
        (rgb_uint8 | None, meta)
        meta: {width, height, encoding, is_depth, channels, error}
    """
    meta: dict = {"error": None}
    try:
        if msgtype in COMPRESSED_TYPES:
            from PIL import Image as PILImage

            buf = _as_uint8_buf(getattr(msg, "data"))
            with io.BytesIO(buf.tobytes()) as stream:
                with closing(PILImage.open(stream)) as im:
                    with closing(im.convert("RGB")) as rgb:
                        arr = np.array(rgb)
            meta.update(
                width=arr.shape[1], height=arr.shape[0],
                encoding=str(getattr(msg, "format", "jpeg")), is_depth=False, channels=3,
            )
            return arr, meta

        h = int(getattr(msg, "height"))
        w = int(getattr(msg, "width"))
        enc = str(getattr(msg, "encoding", "")).strip()
        buf = _as_uint8_buf(getattr(msg, "data"))
        is_depth = enc in DEPTH_ENCODINGS
        meta.update(width=w, height=h, encoding=enc, is_depth=is_depth)

        if enc in ("rgb8", "bgr8", "8UC3"):
            arr = buf[: h * w * 3].reshape(h, w, 3)
            if enc == "bgr8":
                arr = arr[:, :, ::-1]
            meta["channels"] = 3
            return np.ascontiguousarray(arr), meta
        if enc in ("rgba8", "bgra8"):
            arr = buf[: h * w * 4].reshape(h, w, 4)[:, :, :3]
            if enc == "bgra8":
                arr = arr[:, :, ::-1]
            meta["channels"] = 3
            return np.ascontiguousarray(arr), meta
        if enc in ("mono8", "8UC1"):
            g = buf[: h * w].reshape(h, w)
            meta["channels"] = 1
            return np.repeat(g[:, :, None], 3, axis=2), meta
        if enc in ("mono16", "16UC1", "16SC1"):
            g16 = buf[: h * w * 2].view(np.uint16).reshape(h, w).astype(np.float32)
            meta["channels"] = 1
            return _depth_to_rgb(g16), meta
        if enc == "32FC1":
            g32 = buf[: h * w * 4].view(np.float32).reshape(h, w)
            meta["channels"] = 1
            return _depth_to_rgb(g32), meta
        if enc.startswith("bayer"):
            g = buf[: h * w].reshape(h, w)
            meta["channels"] = 1
            meta["error"] = f"bayer 编码 {enc} 仅做灰度近似显示"
            return np.repeat(g[:, :, None], 3, axis=2), meta

        meta["error"] = f"不支持的 encoding: {enc}"
        return None, meta
    except Exception as e:  # noqa: BLE001
        meta["error"] = f"解码失败: {e}"
        return None, meta


def _depth_to_rgb(d: np.ndarray) -> np.ndarray:
    """深度图归一化到灰度以便肉眼检查 (2%~98% 分位裁剪)."""
    v = d.astype(np.float32)
    finite = np.isfinite(v) & (v > 0)
    if not finite.any():
        return np.zeros((*d.shape, 3), np.uint8)
    lo, hi = np.percentile(v[finite], [2, 98])
    if hi <= lo:
        hi = lo + 1.0
    g = np.clip((v - lo) / (hi - lo), 0, 1)
    g[~finite] = 0
    g8 = (g * 255).astype(np.uint8)
    return np.repeat(g8[:, :, None], 3, axis=2)


def thumbnail(rgb: np.ndarray, max_side: int = 200) -> np.ndarray:
    from PIL import Image as PILImage

    im = PILImage.fromarray(rgb)
    im.thumbnail((max_side, max_side))
    return np.asarray(im)
