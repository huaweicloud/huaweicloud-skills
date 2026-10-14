#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""使用 OBS Python SDK 将部署产物上传到 OBS code 目录。

本地产物目录以 <模型名>-<部署方式> 命名,整体递归上传。
OBS 目标: --code-obs-path 直接指定,或 --model-obs-path 推导同级 code 目录。
凭据: 环境变量 OBS_AK/OBS_SK/OBS_ENDPOINT 或 --ak/--sk/--endpoint。
"""

import argparse
import os
import sys


def parse_obs_path(obs_path):
    """解析 obs://<bucket>/<key> 为 (bucket, key)。"""
    if not obs_path.startswith("obs://"):
        sys.exit(f"[错误] 非法 OBS 路径: {obs_path}(应以 obs:// 开头)")
    rest = obs_path[len("obs://"):]
    bucket, _, key = rest.partition("/")
    key = key.strip("/")
    if not bucket:
        sys.exit(f"[错误] 非法 OBS 路径: {obs_path}(缺少桶名)")
    return bucket, key


def derive_code_obs_path(model_obs_path):
    """根据模型目录推导同级 code 目录。

    模型目录 obs://<bucket>/<prefix>/model/<模型名>
        -> code 目录 obs://<bucket>/<prefix>/code
    若路径不含 model 段,则在模型目录的父级下创建 code。
    """
    bucket, key = parse_obs_path(model_obs_path)
    segments = [s for s in key.split("/") if s]
    if "model" in segments:
        prefix = segments[:segments.index("model")]
    else:
        prefix = segments[:-1] if len(segments) > 1 else []
    code_key = "/".join(prefix + ["code"])
    return f"obs://{bucket}/{code_key}"


def has_files(code_dir):
    for _root, _dirs, files in os.walk(code_dir):
        if files:
            return True
    return False


def resolve_credentials(args):
    ak = args.ak or os.environ.get("OBS_AK", "")
    sk = args.sk or os.environ.get("OBS_SK", "")
    endpoint = args.endpoint or os.environ.get("OBS_ENDPOINT", "")
    missing = [name for name, value in
               [("OBS_AK", ak), ("OBS_SK", sk), ("OBS_ENDPOINT", endpoint)]
               if not value]
    if missing:
        sys.exit(f"[错误] 缺少 OBS 凭据: {', '.join(missing)}(通过环境变量或 --ak/--sk/--endpoint 提供)")
    return ak, sk, endpoint


def upload_dir(obs_client, bucket, prefix, code_dir):
    """递归上传 code_dir 下的部署产物文件,返回已上传对象键列表。

    跳过隐藏目录/文件(以 . 开头,如 .cac/、.env、.gitignore)与
    __pycache__ 等缓存目录,避免把本地配置/缓存误传上 OBS。
    """
    uploaded = []
    for root, dirs, files in os.walk(code_dir):
        # 原地过滤: 跳过隐藏目录与 __pycache__(os.walk 会按过滤后的 dirs 递归)
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
        for name in sorted(files):
            if name.startswith(".") or name.endswith(".pyc"):
                continue
            local_path = os.path.join(root, name)
            rel = os.path.relpath(local_path, code_dir)
            object_key = f"{prefix}/{rel}" if prefix else rel
            print(f"[上传] {local_path} -> obs://{bucket}/{object_key}")
            resp = obs_client.putFile(bucket, object_key, local_path)
            if resp.status >= 300:
                print(f"[失败] obs://{bucket}/{object_key}: HTTP {resp.status} "
                      f"{resp.errorCode} {resp.errorMessage}", file=sys.stderr)
                sys.exit(1)
            uploaded.append(object_key)
    return uploaded


def main():
    parser = argparse.ArgumentParser(
        description="使用 OBS SDK 上传部署产物(code 目录)到 OBS")
    parser.add_argument("--code-dir", required=True,
                        help="本地产物目录(当前目录下,建议命名为 <模型名>-<部署方式>,如 Qwen3-8B-pd)")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--code-obs-path",
                        help="用户提供的 OBS code 目录,如 obs://bucket/prefix/code")
    target.add_argument("--model-obs-path",
                        help="模型目录 OBS 路径,由其推导同级 code 目录")
    parser.add_argument("--ak", help="OBS Access Key(缺省读环境变量 OBS_AK)")
    parser.add_argument("--sk", help="OBS Secret Key(缺省读环境变量 OBS_SK)")
    parser.add_argument("--endpoint",
                        help="OBS Endpoint,如 https://obs.cn-north-4.myhuaweicloud.com(缺省读环境变量 OBS_ENDPOINT)")
    args = parser.parse_args()

    code_dir = os.path.abspath(args.code_dir)
    if not os.path.isdir(code_dir):
        sys.exit(f"[错误] 本地 code 目录不存在: {code_dir}")
    if not has_files(code_dir):
        sys.exit(f"[错误] 本地 code 目录下没有任何文件: {code_dir}")

    if args.code_obs_path:
        code_obs_path = args.code_obs_path
    else:
        code_obs_path = derive_code_obs_path(args.model_obs_path)
        print(f"[推导] 由模型目录 {args.model_obs_path} 推导同级 code 目录: {code_obs_path}")

    bucket, prefix = parse_obs_path(code_obs_path)
    if not prefix:
        sys.exit(f"[错误] 目标 code 目录缺少对象前缀: {code_obs_path}")

    try:
        from obs import ObsClient
    except ImportError:
        sys.exit("[错误] 缺少 OBS SDK,执行: pip install esdk-obs-python")

    ak, sk, endpoint = resolve_credentials(args)
    obs_client = ObsClient(access_key_id=ak, secret_access_key=sk, server=endpoint)
    try:
        print(f"[上传] 目录 {code_dir} -> {code_obs_path}")
        uploaded = upload_dir(obs_client, bucket, prefix, code_dir)
    finally:
        obs_client.close()

    print("")
    print("================================================================")
    print("部署产物上传完成!")
    print(f"  code 目录(OBS): {code_obs_path}")
    print("  已上传文件:")
    for key in uploaded:
        print(f"    - obs://{bucket}/{key}")
    print("================================================================")
    print("请将该 code 目录记录为 CODE_OBS_PATH,后续部署新版在线服务时:")
    print("  文件存储挂载: 存储地址 =", code_obs_path, "-> 挂载路径 = /home/ma-user/code/")
    print("  启动命令 = bash /home/ma-user/code/start_vllm.sh")
    print("  探针命令 = bash /home/ma-user/code/health_check.sh startup|liveness|readiness")
    print("  角色识别等脚本也在该目录下,引用同目录文件时用")
    print('  $(dirname "$0") 相对定位,禁止硬编码 /code/ 等绝对路径。')


if __name__ == "__main__":
    main()
