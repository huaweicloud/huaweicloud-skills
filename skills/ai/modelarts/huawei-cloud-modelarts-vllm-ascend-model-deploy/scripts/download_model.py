#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 HuggingFace 或 ModelScope 下载大语言模型权重到本地目录。

用法:
    # HuggingFace
    python download_model.py --source huggingface --model Qwen/Qwen2.5-7B-Instruct --dest ./models/Qwen2.5-7B-Instruct

    # ModelScope(国内推荐,访问更快)
    python download_model.py --source modelscope --model Qwen/Qwen2.5-7B-Instruct --dest ./models/Qwen2.5-7B-Instruct

    # 可选参数
    --revision 分支/tag(默认 main)
    --hf-mirror 使用 hf-mirror.com 加速(默认自动: 当 HF 直连超时时提示使用)
"""

import argparse
import os
import sys


def parse_args():
    parser = argparse.ArgumentParser(description="下载开源大模型权重")
    parser.add_argument("--source", required=True, choices=["huggingface", "modelscope"],
                        help="权重来源: huggingface 或 modelscope")
    parser.add_argument("--model", required=True, help="模型 ID,如 Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--dest", required=True, help="本地保存目录")
    parser.add_argument("--revision", default="main", help="分支或 tag,默认 main")
    parser.add_argument("--hf-mirror", action="store_true",
                        help="使用 HF_ENDPOINT=https://hf-mirror.com 镜像下载")
    return parser.parse_args()


def download_from_huggingface(model_id, dest, revision, use_mirror):
    if use_mirror:
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("缺少 huggingface_hub,执行: pip install huggingface_hub", file=sys.stderr)
        sys.exit(1)
    print(f"[HF] 下载 {model_id} (revision={revision}) -> {dest}")
    snapshot_download(
        repo_id=model_id,
        revision=revision,
        local_dir=dest,
        local_dir_use_symlinks=False,
    )
    print("[HF] 下载完成")


def download_from_modelscope(model_id, dest, revision):
    try:
        from modelscope import snapshot_download
    except ImportError:
        sys.exit(1)
    print(f"[MS] 下载 {model_id} (revision={revision}) -> {dest}")
    snapshot_download(model_id=model_id, revision=revision, local_dir=dest)
    print("[MS] 下载完成")


def main():
    args = parse_args()
    os.makedirs(args.dest, exist_ok=True)
    if args.source == "huggingface":
        download_from_huggingface(args.model, args.dest, args.revision, args.hf_mirror)
    else:
        download_from_modelscope(args.model, args.dest, args.revision)
    # 列出关键文件,便于确认完整性
    for name in ["config.json", "tokenizer.json", "model.safetensors.index.json"]:
        p = os.path.join(args.dest, name)
        if os.path.exists(p):
            print(f"  [OK] {name}")
    print("提示: 确认目录完整后,下一步用 obs_upload.sh 上传到 OBS 桶。")


if __name__ == "__main__":
    main()
