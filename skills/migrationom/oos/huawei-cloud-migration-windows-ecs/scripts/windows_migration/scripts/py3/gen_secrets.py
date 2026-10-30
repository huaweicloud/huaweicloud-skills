#!/usr/bin/env python3
"""
生成 configure_sms_agent.exe / .au3 所需的 base64 密钥文件。

用法:
  # 命令行传参
  python3 gen_secrets.py --ak XXX --sk XXX --domain XXX --ep "Example_Project(示例项目)" -o /tmp/.secrets.dat

  # 从 migrate.yaml 读取
  python3 gen_secrets.py --config config/migrate.yaml -o /tmp/.secrets.dat

  # 输出到 stdout（不写文件）
  python3 gen_secrets.py --ak XXX --sk XXX --domain XXX --ep XXX

生成的文件是 base64 编码的 key=value 文本，configure_sms_agent 读取后自动删除。
"""
import argparse
import base64
import sys
from pathlib import Path


def build_secrets(ak: str, sk: str, domain: str, ep: str,
                  proxy_user: str = "", proxy_pass: str = "") -> bytes:
    """构建 key=value 明文并 base64 编码。"""
    lines = [f"AK={ak}", f"SK={sk}", f"Domain={domain}", f"EP={ep}"]
    if proxy_user or proxy_pass:
        lines.append(f"ProxyUser={proxy_user}")
        lines.append(f"ProxyPass={proxy_pass}")
    plain = "\r\n".join(lines)
    return base64.b64encode(plain.encode("utf-8"))


def load_from_config(config_path: str) -> dict:
    """从 migrate.yaml 读取 SMS-Agent 凭据。"""
    import yaml
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    sa = cfg.get("sms_agent", {})
    return {
        "ak": sa.get("ak", ""),
        "sk": sa.get("sk", ""),
        "domain": sa.get("domain_id", ""),
        "ep": sa.get("enterprise_project", "0"),
    }


def main():
    parser = argparse.ArgumentParser(description="生成 base64 密钥文件")
    parser.add_argument("--ak", help="Access Key")
    parser.add_argument("--sk", help="Secret Key")
    parser.add_argument("--domain", help="Domain ID")
    parser.add_argument("--ep", help="企业项目名称/ID")
    parser.add_argument("--proxy-user", default="", help="代理用户名（可选）")
    parser.add_argument("--proxy-pass", default="", help="代理密码（可选）")
    parser.add_argument("--config", help="从 migrate.yaml 读取凭据")
    parser.add_argument("-o", "--output", help="输出文件路径（默认 stdout）")
    args = parser.parse_args()

    # 从 config 或命令行获取凭据
    if args.config:
        creds = load_from_config(args.config)
        ak = args.ak or creds["ak"]
        sk = args.sk or creds["sk"]
        domain = args.domain or creds["domain"]
        ep = args.ep or creds["ep"]
    else:
        ak = args.ak or ""
        sk = args.sk or ""
        domain = args.domain or ""
        ep = args.ep or ""

    if not ak or not sk:
        print("错误: AK 和 SK 必填", file=sys.stderr)
        sys.exit(1)

    b64 = build_secrets(ak, sk, domain, ep, args.proxy_user, args.proxy_pass)

    if args.output:
        Path(args.output).write_bytes(b64)
        print(f"已生成: {args.output} ({len(b64)} bytes)")
    else:
        print(b64.decode("ascii"))


if __name__ == "__main__":
    main()
