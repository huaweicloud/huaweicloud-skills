#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OpenAI 兼容 API 调用验证脚本。

用途:
  - ModelArts 在线服务部署完成后,通过 OpenAI 兼容 API 验证推理服务可用性。
  - 调用 /v1/chat/completions 端点,打印返回内容;失败时打印错误信息与状态码。

用法:
    python test_inference.py --url https://<endpoint>/v1/chat/completions \
        --token <token> --model <MODEL_NAME> --prompt "你好,请介绍一下你自己"

    # 可选参数
    --max-tokens 256       # 最大生成 token 数(默认 256)
    --temperature 0.7     # 采样温度(默认 0.7)

依赖: pip install requests
"""

import argparse
import sys


def parse_args():
    parser = argparse.ArgumentParser(description="OpenAI 兼容 API 调用验证")
    parser.add_argument("--url", required=True,
                        help="ModelArts 在线服务调用地址,如 https://<endpoint>/v1/chat/completions")
    parser.add_argument("--token", default="", help="推理请求认证 token(ModelArts 在线服务需配置)")
    parser.add_argument("--model", required=True, help="模型名(与启动脚本 --served-model-name 一致)")
    parser.add_argument("--prompt", default="你好,请介绍一下你自己", help="测试 prompt")
    parser.add_argument("--max-tokens", type=int, default=256, help="最大生成 token 数")
    parser.add_argument("--temperature", type=float, default=0.7, help="采样温度")
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        import requests
    except ImportError:
        sys.exit("[错误] 缺少 requests,执行: pip install requests")

    headers = {"Content-Type": "application/json"}
    if args.token:
        headers["Authorization"] = f"Bearer {args.token}"
    payload = {
        "model": args.model,
        "messages": [{"role": "user", "content": args.prompt}],
        "max_tokens": args.max_tokens,
        "temperature": args.temperature,
    }
    print(f"[请求] POST {args.url}")
    print(f"  model={args.model}, prompt={args.prompt!r}")
    try:
        resp = requests.post(args.url, json=payload, headers=headers, timeout=120)
    except requests.exceptions.RequestException as e:
        sys.exit(f"[错误] 请求失败: {e}")

    print(f"[响应] HTTP {resp.status_code}")
    if resp.status_code != 200:
        sys.exit(f"[错误] HTTP {resp.status_code}: {resp.text}")

    data = resp.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    print("[OK] 推理结果:")
    print(content)


if __name__ == "__main__":
    main()
