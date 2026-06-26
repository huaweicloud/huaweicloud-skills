from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


_VOD_SUBDIRS = ["feedbacks"]
_CONFIG_TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "config.yaml.template"


def create_vod_directory(base_dir: Path) -> Path:
    vod_dir = base_dir / ".vod"
    for sub in _VOD_SUBDIRS:
        (vod_dir / sub).mkdir(parents=True, exist_ok=True)
    config_target = vod_dir / "config.yaml"
    if not config_target.exists() and _CONFIG_TEMPLATE.exists():
        shutil.copy2(_CONFIG_TEMPLATE, config_target)
    return vod_dir


def verify_vod_structure(vod_dir: Path) -> bool:
    if not vod_dir.exists():
        return False
    for sub in _VOD_SUBDIRS:
        if not (vod_dir / sub).is_dir():
            return False
    if not (vod_dir / "config.yaml").exists():
        return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="初始化VoD收集Skill的.vod/目录结构")
    parser.add_argument("--base-dir", type=Path, default=Path("."), help="项目根目录（默认当前目录）")
    args = parser.parse_args()

    base_dir = args.base_dir.resolve()

    vod_dir = create_vod_directory(base_dir)
    print(f"已创建.vod/目录: {vod_dir}")

    if verify_vod_structure(vod_dir):
        print("校验通过: .vod/目录结构完整")
    else:
        print("校验失败: .vod/目录结构不完整", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()