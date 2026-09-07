# 运行时依赖与准备

本文件定义 Agent 在不同宿主中准备华为云任务运行环境的统一方法。核心原则是**按任务选择依赖**，
不要为了一个查询同时要求安装 hcloud、全部 SDK、Terraform 和 obsutil。

## 职责边界

- Agent：根据任务和后端选择声明依赖，读取检查结果，决定修复、切换后端或报告缺口。
- Skill：说明需要什么、如何检查、常见安装命令和华为云特有配置，不假设安装权限。
- 宿主：提供进程、网络、凭据注入、依赖安装权限、可写目录、缓存和超时。网络能力由宿主提供，
  Skill 的 check-only doctor 不主动连接外部 endpoint。

缺少 hcloud 不表示 SDK 后端不可用；缺少 SDK package 也不表示已有 hcloud 路径不可用。Terraform 只在
IaC 意图成立时要求，OBS 工具只在 OBS object/bucket/静态网站任务中要求。

## 依赖类型

| need | 什么时候声明 | 检查重点 |
| --- | --- | --- |
| `hcloud` | 选择 KooCLI 作为后端 | CLI、profile、metadata；凭据单独由 `live` 表达 |
| `live` | 需要真实云 API 或 MaaS 之外的华为云认证 | 当前进程或宿主 action-scoped 凭据可见性 |
| `sdk` | 选择官方 Python SDK | 当前任务服务 package，不检查无关服务 |
| `terraform` | 用户明确要求 IaC/import/drift/长期纳管 | Terraform CLI、provider/cache、runtime artifact |
| `obs` | `hcloud obs` 或 standalone obsutil 任一即可 | OBS 命令工具与独立配置状态 |
| `obsutil` | 用户或流程明确要求 standalone obsutil | standalone binary 与配置 |
| `maas` | 调用 MaaS 模型、图片或视频 API | MaaS API Key 的当前进程可见性 |
| `network` | 需要访问华为云 endpoint 或公网探测 | doctor 返回 `unknown`，由宿主或显式预检验证 |
| `artifacts` | 结果可能较大或任务需要可恢复产物 | `--workdir` 是否存在、为目录且可写 |

Python 3.12+ 是 Skill Python 脚本的基础依赖，始终检查。

## 推荐检查命令

hcloud 真实查询：

```bash
python3 scripts/hcloud_environment_doctor.py \
  --need hcloud --need live --need network --need artifacts \
  --workdir <task-workdir> --pretty
```

SDK ECS 任务：

```bash
python3 scripts/hcloud_environment_doctor.py \
  --need sdk --sdk-service ECS --need live --need network \
  --pretty
```

跨服务 SDK 可重复 `--sdk-service`。只安装 `missing_services` 中的 package，不默认安装
`huaweicloudsdkall`。声明 `--need sdk` 但没有给出任何 `--sdk-service` 时，SDK 状态为 `unknown`，
doctor 不会用“扫描到任意一个 SDK package”冒充当前任务已经 ready。

Terraform 任务：

```bash
python3 scripts/hcloud_environment_doctor.py \
  --need terraform --need live --need network --need artifacts \
  --workdir <terraform-workdir> --pretty
```

OBS 任务使用 `--need obs`；只有明确需要 standalone obsutil 时才使用 `--need obsutil`。

## 结果解释

- 顶层 `success=true` 只表示 doctor 成功生成报告，不表示环境已准备好。
- `summary.ready=true` 表示所有本次声明为 required 的依赖状态都是 `ok`。
- `required_blockers` 是已确认缺失的必要依赖。
- `required_unready` 还包括 `unknown`；例如 check-only doctor 不探测网络，因此 `--need network`
  必须交给宿主 preflight 或一次明确的低风险连接检查收敛。
- 未声明的可选工具可以是 `skipped`，不会阻断当前任务。
- 传入任意 `--need` 时使用 `scan_scope=task_scoped`，不会运行无关工具的版本命令或全量 package
  扫描；完全不传 `--need` 时才使用兼容的 `full_overview` 总览。
- `recovery_plan` 只从上述检查结果投影可审查步骤，列出 `actions` 和精确 `commands`，但始终保持
  `execution_performed=false`。它不会接受凭据值、安装 package、修改 profile、下载 metadata 或探测宿主网络。
- hcloud 检查分别报告 binary、隐私声明、profile 认证、region 和 metadata cache。`--need hcloud`
  时缺少可调用上下文返回 warning/unready，而不是只因 binary 存在就声称真实调用已经就绪。

## 缺失依赖的兜底顺序

1. 优先使用宿主已经提供的二进制、package、provider cache 和凭据 broker。
2. 需要安装时只安装当前后端和服务的最小依赖，并向用户说明安装位置与影响。
3. 没有安装权限时，评估另一已就绪后端是否同样适合任务；切换后重新验证 operation、参数和结果。
4. 认证、权限、配额和业务参数错误通常不会通过换后端消失，应保留结构化证据并直接处理根因。
5. 依赖仍不满足时交付计划、已确认事实和明确缺口，不声称真实执行完成。

常见安装提示：

- hcloud：按华为云 KooCLI quickstart 安装；首次隐私确认、profile 和 metadata cache 需要在非交互任务前准备。
- SDK：使用 `python3 -m pip install huaweicloudsdk<service>` 的具体服务包，例如
  `huaweicloudsdkecs`；先核对 client/version/request model。
- Terraform：安装 CLI 后检查 provider mirror/cache；允许网络安装时再运行 `terraform init`，离线环境
  不要反复下载。
- OBS：优先复用可用的 `hcloud obs`；只有流程需要 standalone binary 时单独安装 obsutil，并确认其
  AK/SK/token/endpoint 配置不等同于普通 hcloud profile。

任何安装命令都是建议，不是授权。Skill 不自行提升权限、修改系统包源或绕过宿主限制。
