#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""调用 ModelArts 新版推理 API 部署/管理在线服务。

核心接口 CreateInferService: POST /v2/{project_id}/services,请求体为顶层平铺结构。
配套: ListServices/ShowService/DeleteService/UpdateInferDeploymentScale。

请求体关键字段:
  - secret_type: "agency"(OBS 委托认证); weight: 100(必填)
  - health: failure_threshold=300/initial_delay=300/period=60
  - request_timeout: 300(平台默认 30s 会掐断慢速推理)
  - workspace_id: dev 环境需 X-Workspace-Id 头

token: IAM_TOKEN 环境变量(推荐) > --token-file(权限 600) > 交互式输入
"""

import argparse
import json
import os
import stat
import sys

try:
    import getpass
except ImportError:  # 非标准库,理论上始终存在;防御性兜底
    getpass = None

API_PREFIX = "/v2/{project_id}/services"


def parse_role(spec):
    """解析 'name=role-1,replicas=1' 形式的角色参数为 dict。"""
    role = {}
    for kv in spec.split(","):
        if "=" not in kv:
            sys.exit(f"[错误] 非法角色参数: {spec}(应为 name=xxx,replicas=N)")
        key, _, value = kv.partition("=")
        key = key.strip()
        value = value.strip()
        if key == "replicas":
            try:
                role[key] = int(value)
            except ValueError:
                sys.exit(f"[错误] 角色 replicas 必须是整数: {value}")
        else:
            role[key] = value
    return role


def build_request_body(args):
    """构建 CreateInferService 请求体(顶层平铺结构)。

单部署单元: 所有 role 收集到 group_configs[0].unit_configs[]。
PD 分离: 2 个 unit(prefill/decode);其余形式: 1 个 unit。
--raw-json 优先级最高,直接放行平铺 JSON。
"""
    roles = []
    for spec in args.role:
        role = parse_role(spec)
        # 自动注入健康检查失败次数 60(规避 vLLM 首启误杀重启循环)
        probe = role.setdefault("probe", {})
        probe.setdefault("failure_threshold", 300)
        roles.append(role)

    body = {
        "name": args.service_name,
        "type": "REAL_TIME",
        "deploy_type": "MULTI",
        # 部署超时统一 300 分钟(多节点/大模型首启含模型加载 + CUDAGraph 编译,
        # 平台默认 20~60 分钟不足会触发部署超时失败 status=FAILED)
        "deploy_timeout_minutes": 300,
        "group_configs": [],
        "runtime_config": {
            "service_invoke": {"auth_type": "NONE", "port": 8080, "protocol": "HTTP"},
            # 请求超时统一 300s(平台默认 30s:PD 分离首请求需 prefill+decode 协作
            # 与模型加载/图编译,>30s 被平台掐断报 ModelArts.8909 request timeout)
            "service_limit": {
                "request_timeout": 300,
                "request_size_limit": 20,
                "rate_limit": {"num": 200, "unit": "SECONDS"},
            },
        },
    }

    # 角色附加字段(JSON 字符串,键为单元名或索引)
    extra = {}
    if args.role_extra_json:
        try:
            extra = json.loads(args.role_extra_json)
        except json.JSONDecodeError as e:
            sys.exit(f"[错误] --role-extra-json 不是合法 JSON: {e}")

    # 所有 role(推理单元)收集到单一 group_configs[0].unit_configs[]
    # (单部署单元;PD 分离 = 2 个单元 prefill/decode,其余形式 = 1 个单元)
    group_replicas = getattr(args, "group_replicas", 1)
    unit_configs = []
    for i, role in enumerate(roles):
        role_name = role.get("name", f"role-{i + 1}")
        replicas = role.get("replicas", 1)
        probe = role.pop("probe", {})
        failure_threshold = probe.get("failure_threshold", 300)
        probe_cmd = "bash /home/ma-user/code/health_check.sh {}"
        unit = {
            "name": role_name,
            "count": replicas,
            "role": "COMMON",
            "cmd": "bash /home/ma-user/code/start_vllm.sh",
            "image": {"source": "SWR", "swr_path": ""},
            "liveness_health": {
                "check_method": "EXEC",
                "cmd": probe_cmd.format("liveness"),
                "failure_threshold": failure_threshold,
                "initial_delay_seconds": 300,
                "period_seconds": 60,
                "protocol": "HTTP",
                "timeout_seconds": 60,
            },
            "readiness_health": {
                "check_method": "EXEC",
                "cmd": probe_cmd.format("readiness"),
                "failure_threshold": failure_threshold,
                "initial_delay_seconds": 300,
                "period_seconds": 60,
                "protocol": "HTTP",
                "timeout_seconds": 60,
            },
            "startup_health": {
                "check_method": "EXEC",
                "cmd": probe_cmd.format("startup"),
                "failure_threshold": failure_threshold,
                "initial_delay_seconds": 300,
                "period_seconds": 60,
                "protocol": "HTTP",
                "timeout_seconds": 60,
            },
            "recovery": "Instance",
        }
        # 应用 --role-extra-json 附加字段(键为单元名或索引)
        if role_name in extra:
            unit.update(extra[role_name])
        elif str(i) in extra:
            unit.update(extra[str(i)])
        unit_configs.append(unit)

    body["group_configs"].append({
        "name": "group-0",
        "weight": 100,
        "count": group_replicas,
        "secret_type": "agency",
        "schedule_strategy": "HIGH_AVAILABILITY",
        "unit_configs": unit_configs,
    })

    # 完整请求体覆盖(最高优先级,用户可从 API Explorer 直接粘贴)
    if args.raw_json:
        try:
            raw = json.loads(args.raw_json)
        except json.JSONDecodeError as e:
            sys.exit(f"[错误] --raw-json 不是合法 JSON: {e}")
        if "service" not in raw:
            # 新版 CreateInferService API 要求**顶层平铺结构**
            # (name/type/group_configs[]/runtime_config 直接放顶层,无 service 包裹)。
            # 平铺 JSON 直接放行,仅缺 name 时用骨架 name 填充默认,不报错退出。
            raw.setdefault("name", body["name"])
            return raw
        # 兼容旧版 service.deployment.roles[] 嵌套结构: 转为顶层平铺结构返回
        raw_service = raw["service"]
        raw_service.setdefault("name", body["name"])
        deployment = raw_service.get("deployment", {})
        legacy_roles = deployment.get("roles", [])
        raw_flat = {"name": raw_service["name"], "type": "REAL_TIME", "group_configs": [], "runtime_config": {}}
        for i, r in enumerate(legacy_roles):
            replicas = r.pop("replicas", 1)
            probe = r.pop("probe", {})
            unit = {
                "name": r.pop("name", f"role-{i + 1}"),
                "count": replicas,
                "role": "COMMON",
                "cmd": "bash /home/ma-user/code/start_vllm.sh",
            }
            for attr in ("image", "envs", "files", "liveness_health", "readiness_health", "startup_health", "recovery"):
                if attr in r:
                    unit[attr] = r.pop(attr)
            if not any(k in unit for k in ("liveness_health", "readiness_health", "startup_health")):
                ft = probe.get("failure_threshold", 300)
                unit["liveness_health"] = {"check_method": "EXEC", "cmd": "bash /home/ma-user/code/health_check.sh liveness", "failure_threshold": ft, "initial_delay_seconds": 300, "period_seconds": 60, "protocol": "HTTP", "timeout_seconds": 60}
                unit["readiness_health"] = {"check_method": "EXEC", "cmd": "bash /home/ma-user/code/health_check.sh readiness", "failure_threshold": ft, "initial_delay_seconds": 300, "period_seconds": 60, "protocol": "HTTP", "timeout_seconds": 60}
                unit["startup_health"] = {"check_method": "EXEC", "cmd": "bash /home/ma-user/code/health_check.sh startup", "failure_threshold": ft, "initial_delay_seconds": 300, "period_seconds": 60, "protocol": "HTTP", "timeout_seconds": 60}
            raw_flat["group_configs"].append({
                "name": f"group-{i}",
                "weight": 100,
                "count": 1,
                "secret_type": "agency",
                "schedule_strategy": "HIGH_AVAILABILITY",
                "unit_configs": [unit],
            })
        return raw_flat
    return body


def api_url(endpoint, project_id, suffix=""):
    return f"{endpoint}{API_PREFIX.format(project_id=project_id)}{suffix}"


def request_with_auth(method, url, token, body=None, workspace_id=None):
    try:
        import requests
    except ImportError:
        sys.exit("[错误] 缺少 requests,执行: pip install requests")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if workspace_id:
        # dev/新版环境需要 workspace 头(不带会 400 校验失败或查不到服务)
        headers["X-Workspace-Id"] = workspace_id
    print(f"[请求] {method} {url}")
    try:
        if method in ("POST", "PUT", "PATCH"):
            resp = requests.request(method, url, headers=headers, json=body, timeout=120)
        else:
            resp = requests.request(method, url, headers=headers, timeout=120)
    except requests.exceptions.RequestException as e:
        sys.exit(f"[错误] 请求失败: {e}")
    print(f"[响应] HTTP {resp.status_code}")
    if resp.status_code >= 300:
        sys.exit(f"[错误] HTTP {resp.status_code}: {resp.text}")
    if not resp.text:
        return None
    try:
        return resp.json()
    except ValueError:
        return resp.text


def load_token(args):
    """按安全优先级获取 IAM Token,禁止命令行明文传参。

    命令行参数会通过 ps /proc/<pid>/cmdline 与 Shell 历史暴露给同机
    其他用户或恶意进程,因此 IAM Token 只能通过以下途径提供:
      1. 环境变量 IAM_TOKEN(推荐,不进进程 argv)
      2. --token-file <文件>(文件仅含 token,须为仅本人可读权限,拒绝 0o644 等)
      3. 交互式输入(getpass,终端不回显,不可管道/脚本化)
    """
    token = os.environ.get("IAM_TOKEN", "").strip()
    if token:
        return token

    if args.token_file:
        path = args.token_file
        try:
            mode = stat.S_IMODE(os.stat(path).st_mode)
        except OSError as e:
            sys.exit(f"[错误] 无法读取 token 文件 {path}: {e}")
        # 组/其他用户可读(含 0o644/0o600 以外的宽松权限)即拒绝,提示收紧权限
        if mode & (stat.S_IRGRP | stat.S_IROTH):
            sys.exit(f"[错误] token 文件 {path} 权限过宽(0o{mode:o}),其他用户可读。"
                     f"请执行: chmod 600 {path}")
        try:
            with open(path, encoding="utf-8") as f:
                token = f.read().strip()
        except OSError as e:
            sys.exit(f"[错误] 无法读取 token 文件 {path}: {e}")
        if not token:
            sys.exit(f"[错误] token 文件 {path} 内容为空")
        return token

    if getpass is None:
        sys.exit("[错误] 未提供 token: 请设置环境变量 IAM_TOKEN 或 --token-file")
    try:
        token = getpass.getpass("IAM Token(输入不回显): ").strip()
    except (EOFError, KeyboardInterrupt):
        sys.exit("\n[错误] 未提供 token")
    if not token:
        sys.exit("[错误] 未提供 token: 请设置环境变量 IAM_TOKEN 或 --token-file")
    return token


def cmd_create(args):
    body = build_request_body(args)
    print("[构建] CreateInferService 请求体:")
    print(json.dumps(body, indent=2, ensure_ascii=False))
    data = request_with_auth("POST", api_url(args.endpoint, args.project_id), args.token, body,
                             workspace_id=args.workspace_id)
    if data is None:
        sys.exit("[错误] 创建服务失败: 无响应")
    print("")
    print("================================================================")
    print("创建服务请求已提交!")
    # 新版 API 平铺响应: id / name / status(旧版可能是 service_id)
    print(f"  service_id: {data.get('service_id') or data.get('id', '未知')}")
    print(f"  状态: {data.get('status', '未知')}")
    print("  下一步: 用 show 子命令查询部署状态与调用端点 URL")
    print("================================================================")


def cmd_list(args):
    url = api_url(args.endpoint, args.project_id)
    if args.workspace_id:
        url = f"{url}?workspace_id={args.workspace_id}"
    data = request_with_auth("GET", url, args.token, workspace_id=args.workspace_id)
    if data is None:
        sys.exit("[错误] 查询服务列表失败: 无响应")
    # GetServices 响应字段是 "data"(非 "services"),取错会误判无服务
    services = data.get("data", data.get("services", data if isinstance(data, list) else []))
    print("")
    print("================================================================")
    print("在线服务列表:")
    for s in services:
        print(f"  - {s.get('service_name') or s.get('name', '未知')}: "
              f"id={s.get('service_id', '未知')}, status={s.get('status', '未知')}")
    print("================================================================")


def cmd_show(args):
    url = api_url(args.endpoint, args.project_id, f"/{args.service_id}")
    data = request_with_auth("GET", url, args.token, workspace_id=args.workspace_id)
    if data is None:
        sys.exit("[错误] 查询服务详情失败: 无响应")
    print("")
    print("================================================================")
    print("服务详情:")
    for key in ("service_id", "status", "access_address", "internal_path",
                "service_name", "name", "deployment_id"):
        if key in data:
            print(f"  {key}: {data[key]}")
    if "access_address" in data:
        print(f"  调用端点(OpenAI 兼容): {data['access_address']}/v1/chat/completions")
    print("================================================================")


def cmd_delete(args):
    url = api_url(args.endpoint, args.project_id, f"/{args.service_id}")
    request_with_auth("DELETE", url, args.token, workspace_id=args.workspace_id)
    print("[OK] 删除服务请求已提交")


def cmd_scale(args):
    # 新版扩缩容接口: UpdateInferDeploymentScale(路径随版本,默认按
    # /deployments/{deployment_id}/scale;若 404 可用 --scale-url 覆盖)
    if args.scale_url:
        url = args.scale_url
    else:
        url = api_url(args.endpoint, args.project_id,
                      f"/{args.service_id}/deployments/{args.deployment_id}/scale")
    body = {"replicas": args.replicas}
    data = request_with_auth("POST", url, args.token, body, workspace_id=args.workspace_id)
    if data is None:
        sys.exit("[错误] 扩缩容失败: 无响应")
    print(f"[OK] 扩缩容请求已提交: replicas={args.replicas}")


def parse_args():
    parser = argparse.ArgumentParser(description="ModelArts 新版推理 API 在线服务部署与生命周期管理")
    sub = parser.add_subparsers(dest="command", required=True)

    # 公共参数
    for cmd in ("create", "list", "show", "delete", "scale"):
        p = sub.add_parser(cmd)
        p.add_argument("--endpoint", required=True,
                       help="ModelArts 服务端点,如 https://modelarts.cn-north-4.myhuaweicloud.com")
        p.add_argument("--project-id", required=True, help="华为云项目 ID(Project ID)")
        # 安全设计: 禁止命令行直接传 token(ps//proc/<pid>/cmdline/Shell 历史均会明文暴露)。
        # 优先用环境变量 IAM_TOKEN,或 --token-file(权限须 600),否则交互式输入(不回显)。
        p.add_argument("--token-file", default="",
                       help="IAM Token 文件路径(文件仅含 token,权限须 600;亦可用环境变量 IAM_TOKEN)")
        p.add_argument("--workspace-id", default="",
                       help="Workspace ID(可选,dev/新版环境需要 X-Workspace-Id 头,不带会校验失败)")

    # create 专属参数
    p = sub.choices["create"]
    p.add_argument("--service-name", required=True, help="服务名称,1-64 字符,同一地域唯一")
    p.add_argument("--replicas", type=int, default=1, help="(兼容保留)部署副本数,等价于 --group-replicas")
    p.add_argument("--group-replicas", type=int, default=None,
                   help="部署单元副本数(group_configs[].count): 默认 1(单副本多实例);"
                        "多副本单实例(可靠性)时 >1")
    p.add_argument("--role", action="append", default=[],
                   help="推理单元,可重复: name=role-1,replicas=1。**单部署单元结构**: "
                        "所有 --role 收集到同一 group_configs[0].unit_configs[]——单节点/多节点/"
                        "PD 共置传 1 个,PD 分离传 2 个(name=prefill,replicas=N name=decode,replicas=M);"
                        "unit_configs[].count(=replicas)为单元内实例数(跨节点数);"
                        "单元名仅允许小写字母/数字/连字符)")
    p.add_argument("--role-extra-json", default="",
                   help="按角色附加字段的 JSON(键为单元名,仅小写字母/数字/连字符),如 "
                        '{"prefill":{"image":"swr.xxx/vllm-ascend:v0.23.0","envs":{"VLLM_ROLE":"prefill","PORT":"8080"}},'
                        '"decode":{"image":"swr.xxx/vllm-ascend:v0.23.0","envs":{"VLLM_ROLE":"decode","PORT":"7101"}}}')
    p.add_argument("--raw-json", default="",
                   help="完整请求体 JSON(从 API Explorer 生成后粘贴,最高优先级,覆盖骨架)")

    # show/delete 专属参数
    p = sub.choices["show"]
    p.add_argument("--service-id", required=True, help="服务 ID")
    p = sub.choices["delete"]
    p.add_argument("--service-id", required=True, help="服务 ID")

    # scale 专属参数
    p = sub.choices["scale"]
    p.add_argument("--service-id", required=True, help="服务 ID")
    p.add_argument("--deployment-id", default="", help="部署 ID(新版 /deployments 路径)")
    p.add_argument("--replicas", type=int, required=True, help="调整后的副本数")
    p.add_argument("--scale-url", default="", help="扩缩容接口完整 URL(默认自动拼接,404 时用此覆盖)")

    return parser.parse_args()


def main():
    args = parse_args()
    # 安全获取 token(环境变量/--token-file/交互式),并挂到 args 供各子命令使用
    args.token = load_token(args)
    dispatch = {
        "create": cmd_create,
        "list": cmd_list,
        "show": cmd_show,
        "delete": cmd_delete,
        "scale": cmd_scale,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
