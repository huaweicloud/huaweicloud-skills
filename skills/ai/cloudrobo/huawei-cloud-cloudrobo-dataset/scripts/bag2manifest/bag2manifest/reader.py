"""bag 读取抽象层.

目标: 在 **不安装 ROS、不依赖 metadata.yaml** 的前提下读取 ROS2 bag,
并对上层暴露统一接口.

支持输入 (可直接来自 Web 的文件/目录选择, 或命令行路径):
    * ``bag_dir/``              目录 (自动找里面的 .db3 / .mcap; 无 metadata.yaml 也行)
    * ``xxx.db3``               直接读 sqlite3, **不需要 metadata.yaml**
    * ``bag_0.db3 bag_1.db3``   分片多文件 (自动按时间归并)
    * ``xxx.mcap``              单文件 (schema 内嵌, 自定义消息也能解)
    * ``xxx.zip``               任意一种的压缩包 (Web 上传目录常用)
    * ``xxx.bag``               ROS1 bag (顺带支持)

后端优先级:
    1. ``_SqliteSource``   —— .db3 直接用 sqlite3 读, 不碰 metadata.yaml
    2. ``_McapSource``     —— .mcap 用官方 mcap 库 (索引可 seek)
    3. ``_RosbagsSource``  —— 目录含 metadata.yaml / ROS1 bag 时的兜底

自定义消息:
    * mcap: schema 内嵌, 自动可解
    * db3 : 消息定义不存储在 bag 里, 需通过 ``msg_dirs`` 提供 .msg/.idl 目录;
            否则该话题仍会列出类型/频率, 但无法解析出字段 (会给出明确告警)
"""

from __future__ import annotations

import heapq
import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence


@dataclass
class TopicInfo:
    topic: str
    msgtype: str          # 规范化为 'sensor_msgs/msg/Image'
    count: int
    resolved: bool = True  # False = 自定义消息, 无消息定义无法解析


class BagError(RuntimeError):
    """带修复建议的 bag 读取错误."""

    def __init__(self, code: str, title: str, detail: str = "", fix: Sequence[str] = ()):
        self.code, self.title, self.detail, self.fix = code, title, detail, list(fix)
        super().__init__(f"[{code}] {title}\n{detail}")


def _norm_msgtype(t: str) -> str:
    """'sensor_msgs/Image' -> 'sensor_msgs/msg/Image'."""
    parts = t.split("/")
    if len(parts) == 2:
        return f"{parts[0]}/msg/{parts[1]}"
    return t


# --------------------------------------------------------------------------- #
# 输入归一化: str | Path | list | gradio 文件对象 | 目录 | zip
# --------------------------------------------------------------------------- #
def _as_path(x: Any) -> Path | None:
    if isinstance(x, Path):
        return x.expanduser()
    if isinstance(x, str):
        return Path(x).expanduser()
    name = getattr(x, "name", None)  # gradio 文件对象
    if name:
        return Path(str(name)).expanduser()
    return None


def _expand(src: Any, outs: list[Path], tmpdirs: list[Path]) -> None:
    if isinstance(src, (list, tuple, set)):
        for x in src:
            _expand(x, outs, tmpdirs)
        return
    p = _as_path(src)
    if p is None:
        return
    if not p.exists():
        raise BagError("E001", f"路径不存在: {p}")
    if p.is_dir():
        outs.append(p)
        return
    if p.suffix.lower() == ".zip":
        td = Path(tempfile.mkdtemp(prefix="b2m_zip_"))
        tmpdirs.append(td)
        with zipfile.ZipFile(p) as zf:
            zf.extractall(td)
        _expand(td, outs, tmpdirs)
        return
    outs.append(p)


def _find_files(paths: Iterable[Path], suffixes: tuple[str, ...]) -> list[Path]:
    """在一组路径里找指定后缀的文件; 目录最多向下搜索 3 层."""
    out: list[Path] = []
    seen: set[Path] = set()
    for p in paths:
        if p.is_file() and p.suffix.lower() in suffixes:
            cand = [p]
        elif p.is_dir():
            cand = []
            for depth_pat in ("*", "*/*", "*/*/*"):
                cand += [f for f in sorted(p.glob(depth_pat)) if f.is_file()
                         and f.suffix.lower() in suffixes]
        else:
            cand = []
        for f in cand:
            rp = f.resolve()
            if rp not in seen:
                seen.add(rp)
                out.append(f)
    return out


def _display_name(paths: Sequence[Path]) -> str:
    files = [p for p in paths if p.is_file()]
    if len(files) == 1:
        return files[0].name
    if len(paths) == 1 and paths[0].is_dir():
        return paths[0].name + "/"
    if files:
        return f"{files[0].parent.name}/ ({len(files)} 文件)"
    return str(paths[0]) if paths else "bag"


# --------------------------------------------------------------------------- #
# 消息类型解析 (自定义消息需要外部 .msg/.idl)
# --------------------------------------------------------------------------- #
_DISTROS = (
    "ROS2_LYRICAL", "ROS2_KILTED", "ROS2_JAZZY", "ROS2_IRON",
    "ROS2_HUMBLE", "ROS2_GALACTIC", "ROS2_FOXY",
)


def _msg_name_from_file(f: Path) -> str | None:
    """``.../my_pkg/msg/Type.msg`` -> ``my_pkg/msg/Type``."""
    if f.parent.name in ("msg", "srv") and f.parent.parent.name:
        return f"{f.parent.parent.name}/{f.parent.name}/{f.stem}"
    return None


def build_typestore(needed: set[str], msg_dirs: Sequence[str | Path] = ()):
    """为 db3 选择合适的 typestore, 并注册 msg_dirs 里的自定义消息.

    Returns:
        (typestore, unresolved: set[str])
    """
    from rosbags.typesys import Stores, get_types_from_idl, get_types_from_msg, get_typestore

    custom: dict[str, Any] = {}
    for d in msg_dirs:
        dp = Path(d).expanduser()
        if not dp.exists():
            continue
        for f in list(dp.rglob("*.msg")):
            name = _msg_name_from_file(f)
            if not name:
                continue
            try:
                custom.update(get_types_from_msg(f.read_text(encoding="utf-8"), name))
            except Exception:  # noqa: BLE001 - 单个坏定义不阻断其他
                pass
        for f in list(dp.rglob("*.idl")):
            name = _msg_name_from_file(f)
            if not name:
                continue
            try:
                custom.update(get_types_from_idl(f.read_text(encoding="utf-8"), name))
            except Exception:  # noqa: BLE001
                pass

    best: tuple[Any, set[str]] | None = None
    for distro in _DISTROS:
        try:
            st = get_typestore(getattr(Stores, distro))
        except Exception:  # noqa: BLE001
            continue
        if custom:
            try:
                st.register(custom)
            except Exception:  # noqa: BLE001
                pass
        unresolved = {t for t in needed if t not in st.types}
        if not unresolved:
            return st, set()
        if best is None or len(unresolved) < len(best[1]):
            best = (st, unresolved)
    if best is None:
        raise BagError("E006", "无法初始化消息类型库", "rosbags.typesys 不可用")
    return best


# --------------------------------------------------------------------------- #
# 统一 Source
# --------------------------------------------------------------------------- #
class _StrideCounter:
    """逐话题的 1/N 采样计数器."""

    def __init__(self, stride: int | dict[str, int]):
        self._map = stride if isinstance(stride, dict) else None
        self._default = 1 if isinstance(stride, dict) else max(1, int(stride))
        self._n: dict[str, int] = {}

    def hit(self, topic: str) -> bool:
        step = self._default if self._map is None else max(1, int(self._map.get(topic, 1)))
        i = self._n.get(topic, 0)
        self._n[topic] = i + 1
        return (i % step) == 0


class BagSource:
    """统一读取接口. 用 ``open_any()`` 构造."""

    backend: str = "?"
    start_ns: int = 0
    end_ns: int = 0
    tmpdirs: list[Path] | None = None   # zip 解压临时目录, 由 open_any 填充

    def topics(self) -> list[TopicInfo]:  # pragma: no cover - 抽象
        raise NotImplementedError

    def iter_messages(
        self,
        topics: Sequence[str] | None = None,
        start_ns: int | None = None,
        stop_ns: int | None = None,
        deserialize: bool = True,
        stride: int | dict[str, int] = 1,
    ) -> Iterator[tuple[str, int, Any]]:
        """按时间顺序产出 ``(topic, t_ns, msg | None)``.

        Args:
            stride: 每 N 条只反序列化一条 (未命中时 msg 为 None), 用于低成本采样.
                    可以是 int (全局) 或 ``{topic: n}`` (逐话题).
        """
        raise NotImplementedError  # pragma: no cover

    def close(self) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class _RosbagsSource(BagSource):
    """metadata.yaml 目录 / ROS1 bag 的兜底后端."""

    backend = "rosbags"

    def __init__(self, path: Path):
        from rosbags.highlevel import AnyReader

        self._reader = AnyReader([path])
        self._reader.open()
        self.start_ns = int(self._reader.start_time)
        self.end_ns = int(self._reader.end_time)
        self._conns = list(self._reader.connections)

    def topics(self) -> list[TopicInfo]:
        agg: dict[str, TopicInfo] = {}
        for c in self._conns:
            ti = agg.get(c.topic)
            if ti is None:
                agg[c.topic] = TopicInfo(c.topic, _norm_msgtype(c.msgtype), int(c.msgcount))
            else:
                ti.count += int(c.msgcount)
        return sorted(agg.values(), key=lambda t: t.topic)

    def iter_messages(self, topics=None, start_ns=None, stop_ns=None, deserialize=True, stride=1):
        conns = self._conns if topics is None else [c for c in self._conns if c.topic in set(topics)]
        if not conns:
            return
        counter = _StrideCounter(stride)
        for conn, ts, raw in self._reader.messages(connections=conns, start=start_ns, stop=stop_ns):
            hit = counter.hit(conn.topic)
            msg = None
            if deserialize and hit:
                try:
                    msg = self._reader.deserialize(raw, conn.msgtype)
                except Exception:  # noqa: BLE001 - 单条坏消息不应中断整个扫描
                    msg = None
            yield conn.topic, int(ts), msg

    def close(self):
        try:
            self._reader.close()
        except Exception:  # noqa: BLE001
            pass


class _McapSource(BagSource):
    """单个 .mcap 文件, 使用官方 mcap + mcap_ros2 (schema 内嵌, 索引可 seek)."""

    backend = "mcap"

    def __init__(self, path: Path):
        from mcap.reader import make_reader
        from mcap_ros2.decoder import DecoderFactory

        self._path = path
        self._fp = path.open("rb")
        self._reader = make_reader(self._fp, decoder_factories=[DecoderFactory()])
        summary = self._reader.get_summary()
        if summary is None or summary.statistics is None:
            raise BagError(
                "E004", "mcap 缺少 summary/statistics 段",
                f"文件可能未正常关闭 (录制中断): {path}",
                ["用 `mcap recover in.mcap -o out.mcap` 修复后重试"],
            )
        stats = summary.statistics
        self.start_ns = int(stats.message_start_time)
        self.end_ns = int(stats.message_end_time)
        self._topics: list[TopicInfo] = []
        for cid, ch in summary.channels.items():
            schema = summary.schemas.get(ch.schema_id)
            self._topics.append(
                TopicInfo(
                    ch.topic,
                    _norm_msgtype(schema.name if schema else "unknown"),
                    int(stats.channel_message_counts.get(cid, 0)),
                )
            )
        self._topics.sort(key=lambda t: t.topic)

    def topics(self) -> list[TopicInfo]:
        return list(self._topics)

    def iter_messages(self, topics=None, start_ns=None, stop_ns=None, deserialize=True, stride=1):
        counter = _StrideCounter(stride)
        it = self._reader.iter_decoded_messages(
            topics=list(topics) if topics else None,
            start_time=start_ns,
            end_time=stop_ns,
            log_time_order=True,
        )
        for _schema, channel, message, ros_msg in it:
            hit = counter.hit(channel.topic)
            yield channel.topic, int(message.log_time), (ros_msg if (deserialize and hit) else None)

    def close(self):
        try:
            self._fp.close()
        except Exception:  # noqa: BLE001
            pass


class _SqliteSource(BagSource):
    """直接读 ROS2 ``.db3`` (sqlite3), **不依赖 metadata.yaml**.

    这是本工具读取 db3 的主路径:
        * topics / messages 两张表就足以拿到 话题名/类型/频率/时间戳
        * 消息定义不在 db3 里 —— 标准类型用 rosbags 内置库,
          自定义类型通过 ``msg_dirs`` 注册; 否则该话题标记为 unresolved.
    """

    backend = "sqlite3"

    def __init__(self, paths: Sequence[Path], msg_dirs: Sequence[str | Path] = ()):
        self._conns: list[sqlite3.Connection] = []
        for p in paths:
            self._conns.append(self._connect(p))
        if not self._conns:
            raise BagError("E007", "没有可读的 .db3 文件")

        # 1) 读 topics 表
        raw: dict[tuple[str, str], int] = {}
        for con in self._conns:
            for name, typ, tid in con.execute("SELECT name, type, id FROM topics"):
                raw[(name, _norm_msgtype(str(typ)))] = raw.get((name, _norm_msgtype(str(typ))), 0)
                cnt = con.execute("SELECT COUNT(*) FROM messages WHERE topic_id=?", (tid,)).fetchone()[0]
                raw[(name, _norm_msgtype(str(typ)))] += int(cnt)

        # 2) 时间范围
        starts, ends = [], []
        for con in self._conns:
            r = con.execute("SELECT MIN(timestamp), MAX(timestamp) FROM messages").fetchone()
            if r and r[0] is not None:
                starts.append(int(r[0]))
                ends.append(int(r[1]))
        if not starts:
            raise BagError("E008", "db3 里没有任何消息", f"{[p.name for p in paths]}")
        self.start_ns = min(starts)
        self.end_ns = max(ends)

        # 3) 类型解析
        needed = {t for _n, t in raw}
        self._typestore, unresolved = build_typestore(needed, msg_dirs)
        self._topics = [
            TopicInfo(name, typ, cnt, resolved=(typ in self._typestore.types))
            for (name, typ), cnt in raw.items()
        ]
        self._topics.sort(key=lambda t: t.topic)
        self.unresolved_types = sorted(unresolved)

    @staticmethod
    def _connect(p: Path) -> sqlite3.Connection:
        for uri in (f"file:{p}?mode=ro&immutable=1", f"file:{p}?mode=ro"):
            try:
                con = sqlite3.connect(uri, uri=True)
                con.execute("PRAGMA query_only=1")
                con.execute("SELECT COUNT(*) FROM messages").fetchone()
                return con
            except sqlite3.Error:
                continue
        raise BagError("E009", f"无法打开 db3: {p}",
                       "文件损坏或不是 ROS2 sqlite3 bag",
                       ["确认文件是 ROS2 录制的 .db3", "或改用 .mcap"])

    def topics(self) -> list[TopicInfo]:
        return list(self._topics)

    def iter_messages(self, topics=None, start_ns=None, stop_ns=None, deserialize=True, stride=1):
        want = set(topics) if topics else None
        counter = _StrideCounter(stride)
        gens = [self._iter_one(con, want, start_ns, stop_ns, deserialize, counter)
                for con in self._conns]
        if len(gens) == 1:
            yield from gens[0]
        else:
            yield from heapq.merge(*gens, key=lambda r: r[1])

    def _iter_one(self, con, want, start_ns, stop_ns, deserialize, counter):
        sql = "SELECT topic_id, timestamp, data FROM messages"
        cond, params = [], []
        if want:
            ids = [tid for tid, in con.execute("SELECT DISTINCT topic_id FROM messages")
                   if self._topic_by_id(con, tid)[0] in want]
            if not ids:
                return
            cond.append("topic_id IN (%s)" % ",".join("?" * len(ids)))
            params += ids
        if start_ns is not None:
            cond.append("timestamp >= ?")
            params.append(int(start_ns))
        if stop_ns is not None:
            cond.append("timestamp <= ?")
            params.append(int(stop_ns))
        if cond:
            sql += " WHERE " + " AND ".join(cond)
        sql += " ORDER BY timestamp, id"

        cur = con.execute(sql, params)
        while True:
            rows = cur.fetchmany(2048)
            if not rows:
                break
            for tid, ts, data in rows:
                name, typ = self._topic_by_id(con, tid)
                hit = counter.hit(name)
                msg = None
                if deserialize and hit and typ in self._typestore.types:
                    try:
                        msg = self._typestore.deserialize_cdr(bytes(data), typ)
                    except Exception:  # noqa: BLE001
                        msg = None
                yield name, int(ts), msg

    def _topic_by_id(self, con, tid: int) -> tuple[str, str]:
        cache = getattr(self, "_tid_cache", None)
        if cache is None:
            cache = self._tid_cache = {}
        key = (id(con), int(tid))
        if key not in cache:
            r = con.execute("SELECT name, type FROM topics WHERE id=?", (tid,)).fetchone()
            cache[key] = (str(r[0]), _norm_msgtype(str(r[1]))) if r else ("?", "unknown")
        return cache[key]

    def close(self):
        for con in self._conns:
            try:
                con.close()
            except Exception:  # noqa: BLE001
                pass


class _MultiSource(BagSource):
    """多个同类单文件后端按时间归并 (如分片的多段 mcap)."""

    backend = "multi"

    def __init__(self, sources: Sequence[BagSource]):
        self._sources = list(sources)
        self.start_ns = min(s.start_ns for s in self._sources)
        self.end_ns = max(s.end_ns for s in self._sources)
        self.backend = self._sources[0].backend + f"×{len(self._sources)}"

    def topics(self) -> list[TopicInfo]:
        agg: dict[str, TopicInfo] = {}
        for s in self._sources:
            for t in s.topics():
                cur = agg.get(t.topic)
                if cur is None:
                    agg[t.topic] = TopicInfo(t.topic, t.msgtype, t.count, t.resolved)
                else:
                    cur.count += t.count
        return sorted(agg.values(), key=lambda t: t.topic)

    def iter_messages(self, topics=None, start_ns=None, stop_ns=None, deserialize=True, stride=1):
        gens = [s.iter_messages(topics, start_ns, stop_ns, deserialize, stride)
                for s in self._sources]
        yield from heapq.merge(*gens, key=lambda r: r[1])

    def close(self):
        for s in self._sources:
            s.close()


# --------------------------------------------------------------------------- #
# 工厂
# --------------------------------------------------------------------------- #
def open_any(src: Any, msg_dirs: Sequence[str | Path] = ()) -> tuple[BagSource, str]:
    """打开任意输入, 返回 ``(source, 显示名)``.

    Args:
        src: 路径字符串 / Path / 路径列表 (支持 Web 目录选择) / gradio 文件对象
        msg_dirs: 自定义消息定义目录 (仅 db3 需要)
    """
    paths: list[Path] = []
    tmpdirs: list[Path] = []
    _expand(src, paths, tmpdirs)
    if not paths:
        raise BagError("E001", "没有有效的输入路径")

    name = _display_name(paths)
    errors: list[str] = []

    def _finish(source: BagSource) -> tuple[BagSource, str]:
        source.tmpdirs = tmpdirs
        return source, name

    # 1) db3 直接读, 不需要 metadata.yaml
    db3s = _find_files(paths, (".db3",))
    if db3s:
        try:
            return _finish(_SqliteSource(db3s, msg_dirs))
        except BagError:
            raise
        except Exception as e:  # noqa: BLE001
            errors.append(f"sqlite3 后端失败: {e}")

    # 2) mcap (单文件优先, 多文件归并)
    mcaps = _find_files(paths, (".mcap",))
    if mcaps:
        srcs: list[BagSource] = []
        for f in mcaps:
            try:
                srcs.append(_McapSource(f))
            except BagError as e:
                errors.append(f"{e.title}: {f.name}")
            except Exception as e:  # noqa: BLE001
                errors.append(f"mcap 后端失败 ({f.name}): {e}")
        if len(srcs) == 1:
            return _finish(srcs[0])
        if srcs:
            return _finish(_MultiSource(srcs))

    # 3) metadata.yaml 目录 / ROS1 bag 兜底
    for p in paths:
        target = p
        if p.is_dir() and not (p / "metadata.yaml").exists():
            metas = sorted(p.rglob("metadata.yaml"))
            if metas:
                target = metas[0].parent
        try:
            return _finish(_RosbagsSource(target))
        except Exception as e:  # noqa: BLE001
            errors.append(f"rosbags 后端失败 ({p}): {e}")
            break

    raise BagError(
        "E005", "无法读取该 bag",
        "\n".join(errors) or "输入里没有 .db3 / .mcap / metadata.yaml / .bag",
        [
            "选择 bag 目录 (里面应有 .db3 或 .mcap), 或直接选择 .db3 / .mcap 文件",
            "db3 里的自定义消息需要额外提供 .msg 定义目录 (界面上的「消息定义目录」)",
            "推荐使用 .mcap 格式录制: schema 内嵌, 无需 metadata.yaml 和消息包",
        ],
    )


def resolve_input(path: Any) -> tuple[Path, Path | None]:
    """兼容旧接口: 返回单个路径 (多输入时取第一个). 新代码请用 ``open_any``."""
    paths: list[Path] = []
    tmpdirs: list[Path] = []
    _expand(path, paths, tmpdirs)
    if not paths:
        raise BagError("E001", "没有有效的输入路径")
    return paths[0], (tmpdirs[0] if tmpdirs else None)


def open_bag(path: Any, msg_dirs: Sequence[str | Path] = ()) -> BagSource:
    """兼容旧接口."""
    return open_any(path, msg_dirs)[0]
