#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存助手：管理 .stats/algorithm_id.csv 与 .stats/task_id.csv 的读写，
封装 agent 在跑 hcloud 命令前需要的「aid / tid / last_update_time」自动获取。

设计原则：**纯本地工具，不调 hcloud 子进程**；不依赖任何 IAM 权限。
- aid / tid 通过 put-algorithm / put-task 写入（CreateAlgorithm / CreateEvolveTask 之后）
- last_update_time 由 agent 在 shell 里自己 hcloud ShowAlgorithm 拿到，再 put-lut 写入

支持两种调用方式：

1) 命令行调用（agent 在 shell 里捕获 stdout）：
   AID=$(python scripts/cache.py ensure-algorithm --name "p1test")
   TID=$(python scripts/cache.py ensure-task --aid "$AID")

   写入：
   python scripts/cache.py put-algorithm --name p1test --aid <aid>
   python scripts/cache.py put-task --aid <aid> --tid <tid> [--name <name>]

   last_update_time 流程（agent 在 shell 里完成）：
   LUT=$(hcloud OptVerse ShowAlgorithm --algorithm_id=$AID \
     --cli-region=$REGION --cli-output=json \
     --cli-query="payload.item.content_update_at")
   python scripts/cache.py put-lut --aid "$AID" --lut "$LUT"

   之后直接：
   LUT=$(python scripts/cache.py get-lut --aid "$AID")

   推导 `--iteration`（commit_id 形如 `sample_<n>_<fp>`，`<n>` 即 iteration）：
   ITER=$(python scripts/cache.py get-iteration --commit-id "$COMMIT")

2) Python 模块调用：
   from scripts.cache import (
       ensure_algorithm, ensure_task, get_lut,
       put_algorithm, put_task, put_lut,
       get_iteration,
   )

缓存位置：
- 默认 <cwd>/.stats/
- 环境变量 OPTV_CACHE_DIR 可覆盖

CSV 格式：
- algorithm_id.csv：algorithm_name, algorithm_id, content_update_at
- task_id.csv：algorithm_id, evolve_task_id, task_name, create_time

错误处理：
- 缓存未命中：抛 RuntimeError（CLI 模式下 exit code=1 + stderr 报错信息）；
  agent 应按错误消息提示用户先 CreateAlgorithm / CreateEvolveTask / ShowAlgorithm。

设计注意：
- 整个模块是**纯本地文件操作**（Python 标准库 `csv` + `pathlib`），**不发起任何网络请求、不调 hcloud 子进程**。
- `for row in rows:` 等循环是**遍历内存中已读入的 rows**，遍历过程中不会触发任何 IO 副作用。
- 不依赖任何第三方包（仅 `argparse` / `csv` / `os` / `pathlib` / `sys`），纯 Python 3.8+ 标准库。
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path
from typing import Optional


STATS_DIR = Path(os.environ.get("OPTV_CACHE_DIR") or Path.cwd() / ".stats")
ALGO_CSV = STATS_DIR / "algorithm_id.csv"
TASK_CSV = STATS_DIR / "task_id.csv"

ALGO_HEADER = ["algorithm_name", "algorithm_id", "content_update_at"]
TASK_HEADER = ["algorithm_id", "evolve_task_id", "task_name", "create_time"]


def _ensure_stats_dir() -> None:
    STATS_DIR.mkdir(parents=True, exist_ok=True)


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    _ensure_stats_dir()
    header = ALGO_HEADER if path.name == ALGO_CSV.name else TASK_HEADER
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in header})


# ==================== Public API ====================

def ensure_algorithm(name: str) -> str:
    """按 name 查 aid；命中返回，未命中抛 RuntimeError 提示先建项目。"""
    rows = _read_csv(ALGO_CSV)
    for row in rows:
        if row.get("algorithm_name") == name:
            return row["algorithm_id"]
    raise RuntimeError(
        f"缓存未命中 algorithm_name={name!r}；"
        f"请先 CreateAlgorithm 并 put-algorithm 入缓存。"
    )


def put_algorithm(name: str, aid: str, lut: Optional[int] = None) -> None:
    """写入算法项目到缓存（CreateAlgorithm 之后调用）。LUT 可选，单独写可用 put-lut。"""
    rows = _read_csv(ALGO_CSV)
    rows = [r for r in rows if r.get("algorithm_name") != name]
    rows.append({"algorithm_name": name, "algorithm_id": aid, "content_update_at": str(lut or "")})
    _write_csv(ALGO_CSV, rows)


def ensure_task(aid: str, name: Optional[str] = None) -> str:
    """按 aid 查 tid（不传 name 则返回该 aid 下最近一个 task）。"""
    rows = _read_csv(TASK_CSV)
    matched = [r for r in rows if r.get("algorithm_id") == aid]
    if name:
        matched = [r for r in matched if r.get("task_name") == name]
    if not matched:
        raise RuntimeError(
            f"缓存未命中 algorithm_id={aid!r}"
            + (f" task_name={name!r}" if name else "")
            + "；请先 CreateEvolveTask 并 put-task 入缓存。"
        )
    return matched[-1]["evolve_task_id"]


def put_task(aid: str, tid: str, name: Optional[str] = None) -> None:
    """写入演化任务到缓存（CreateEvolveTask 之后调用）。"""
    rows = _read_csv(TASK_CSV)
    rows.append({
        "algorithm_id": aid,
        "evolve_task_id": tid,
        "task_name": name or "",
        "create_time": "",
    })
    _write_csv(TASK_CSV, rows)


def get_lut(aid: str) -> int:
    """读缓存里的 last_update_time；未写入时抛 RuntimeError。

    取 LUT 由 agent 在 shell 里手工完成：
        LUT=$(hcloud OptVerse ShowAlgorithm --algorithm_id=$AID \\
            --cli-region=$REGION --cli-output=json \\
            --cli-query="payload.item.content_update_at")
        python scripts/cache.py put-lut --aid "$AID" --lut "$LUT"
    然后下次 get_lut 直接拿到缓存值。
    """
    rows = _read_csv(ALGO_CSV)
    for row in rows:
        if row.get("algorithm_id") == aid:
            cached = row.get("content_update_at", "")
            if not cached:
                raise RuntimeError(
                    f"缓存中 algorithm_id={aid!r} 的 content_update_at 为空；"
                    f"请先在 shell 里跑 hcloud OptVerse ShowAlgorithm 取 LUT，"
                    f"再调 put-lut 写入。"
                )
            return int(cached)
    raise RuntimeError(
        f"缓存未命中 algorithm_id={aid!r}；请先 put-algorithm。"
    )


def put_lut(aid: str, lut: int) -> None:
    """写入 last_update_time（agent 自己 hcloud 取到 LUT 后调用）。"""
    rows = _read_csv(ALGO_CSV)
    found = False
    for row in rows:
        if row.get("algorithm_id") == aid:
            row["content_update_at"] = str(lut)
            found = True
            break
    if not found:
        raise RuntimeError(f"缓存未命中 algorithm_id={aid!r}")
    _write_csv(ALGO_CSV, rows)


def get_iteration(commit_id: str) -> int:
    """从 commit_id 形如 `sample_<n>_<fp>` 推导 `<n>`（即 `ShowTaskResultCommit --iteration` 必填值）。

    抛 RuntimeError：commit_id 格式不匹配时，让 agent 知道需要手动传。
    """
    parts = commit_id.split("_", 2)
    if len(parts) < 3 or parts[0] != "sample":
        raise RuntimeError(
            f"无法从 commit_id={commit_id!r} 推导 iteration；"
            f"期望格式 sample_<n>_<fp>，请手动传 --iteration=<n>。"
        )
    try:
        return int(parts[1])
    except ValueError:
        raise RuntimeError(
            f"commit_id={commit_id!r} 中 <n>={parts[1]!r} 不是数字；"
            f"请手动传 --iteration=<n>。"
        )


# ==================== CLI ====================

def main() -> int:
    parser = argparse.ArgumentParser(description="OptVerse skill 缓存助手")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ea = sub.add_parser("ensure-algorithm", help="按 name 查 aid（未命中报错）")
    p_ea.add_argument("--name", required=True)

    p_pa = sub.add_parser("put-algorithm", help="写入算法项目到缓存")
    p_pa.add_argument("--name", required=True)
    p_pa.add_argument("--aid", required=True)

    p_et = sub.add_parser("ensure-task", help="按 aid 查最新 tid（可选 --name 精确匹配）")
    p_et.add_argument("--aid", required=True)
    p_et.add_argument("--name", default=None)

    p_pt = sub.add_parser("put-task", help="写入演化任务到缓存")
    p_pt.add_argument("--aid", required=True)
    p_pt.add_argument("--tid", required=True)
    p_pt.add_argument("--name", default=None)

    p_gl = sub.add_parser("get-lut", help="读缓存里的 last_update_time（需先 put-lut）")
    p_gl.add_argument("--aid", required=True)

    p_pl = sub.add_parser("put-lut", help="写入 last_update_time")
    p_pl.add_argument("--aid", required=True)
    p_pl.add_argument("--lut", required=True, type=int)

    p_gi = sub.add_parser("get-iteration", help="从 commit_id (sample_<n>_<fp>) 推导 iteration <n>")
    p_gi.add_argument("--commit-id", required=True)

    args = parser.parse_args()

    try:
        if args.cmd == "ensure-algorithm":
            print(ensure_algorithm(args.name))
        elif args.cmd == "put-algorithm":
            put_algorithm(args.name, args.aid)
            print(f"✓ cached algorithm_name={args.name} -> algorithm_id={args.aid} (file: {ALGO_CSV})")
        elif args.cmd == "ensure-task":
            print(ensure_task(args.aid, args.name))
        elif args.cmd == "put-task":
            put_task(args.aid, args.tid, args.name)
            print(f"✓ cached evolve_task_id={args.tid} under algorithm_id={args.aid} (file: {TASK_CSV})")
        elif args.cmd == "get-lut":
            print(get_lut(args.aid))
        elif args.cmd == "put-lut":
            put_lut(args.aid, args.lut)
            print(f"✓ cached content_update_at={args.lut} for algorithm_id={args.aid}")
        elif args.cmd == "get-iteration":
            print(get_iteration(args.commit_id))
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
