# COC Readiness And Remote Execution Boundary

## 目标

当任务需要进入 ECS 内执行命令、安装软件、排障服务或采集机内证据时，先判断是否有可用的远程执行通道。COC/远程命令可以优先尝试，但它不是默认可用能力；没有 COC 时必须按 SSH、cloud-init、重装/重建等受控 fallback 收敛。

## 适用场景

- ECS 已经创建，但需要机内执行命令。
- ELB member 不健康，需要检查后端服务、端口、进程或日志。
- EVS 已挂载到云侧，但还需要在系统内分区、格式化、挂载或写入测试。
- Docker、Nginx、WordPress、应用服务启动后需要协议验收。
- 用户说“帮我进机器看看”“服务器打不开”“网站打不开”“服务起不来”。

## 先判定任务类型

1. 新建、演示、测试、可替换资源：
   - 可以优先用 cloud-init/user_data、保存的 keypair、一次性密码或重装/重建注入执行通道。
   - 如果 COC 不可用，不要停在“无法远程命令”；继续走 SSH 或 cloud-init fallback。
2. 已有生产资源、保留系统盘、有状态服务：
   - 不要擅自重装、换 OS、重置密码或开放 SSH。
   - 只输出缺少的最小执行通道和需要用户授权的动作。
3. 只读排障：
   - 优先收集云侧证据：ECS 状态、安全组、EIP、ELB member、CES 指标、LTS 日志。
   - 只有云侧证据不能解释问题时，再进入机内执行。

## COC 可用性检查

当前 skill 没有把 COC 做成独立执行面。需要使用 COC 时，按 hcloud-first 方式发现能力：

```bash
python3 scripts/hcloud_meta_lookup.py --service=COC --pretty
python3 scripts/hcloud_resource_discovery.py \
  --service COC \
  --operation <discovered-readonly-operation> \
  --region=<region> \
  --project-id=<project-id> \
  --pretty
```

如果本地 metadata 或 live help 没有 COC service/operation，不要猜 operation 名称。把 COC 标记为 `unavailable_or_unknown`，继续走 SSH 或 cloud-init fallback。

如果 COC 调用返回权限错误：

- 通过 `hcloud_safe_exec.py` 查看 `error_details.category` 和 `permission_hint`。
- 不要连续重试同一个 COC 调用超过一次。
- 记录 region、project、ECS ID、错误码、缺失权限提示和是否存在 agency/SCP/custom deny 可能。

## COC 双 region 上下文

COC 排障必须分开两个 region：

- `coc_service_region`：调用 COC API、查询脚本和管理任务的控制面 endpoint 区域。
- `target_instance_region`：目标 HCSS/ECS 实例真实所在区域。

当出现脚本存在但目标查不到、agent offline、跨区 target not found，或同一实例在某个 COC endpoint 不可见时，按以下顺序取证：

1. 记录 COC endpoint 和 `coc_service_region`。
2. 记录目标的 `provider`、`type`、`resource_id`、`region_id`。
3. 确认目标已被该 COC 控制面纳管，且 agent 在线。
4. 确认 project/agency 权限。
5. 最后再检查 script ID 和 execute 参数。

两个 region 中任一个未知时，不要只切换 `--region` 连续重试；明确报告缺少哪个上下文。目标 region 正确但 COC endpoint 错误时，应定位为控制面上下文问题；agent status 为空时，不能把任务失败直接归因到脚本。

## COC 委托与临时凭证模式

如果要把 COC 用作已有 ECS 的机内执行通道，先把授权链和临时凭证设计清楚，不要直接把“能创建脚本”当成“可以安全登录机器”。

已知高价值事实：

- COC 跨服务委托常见名称是 `ServiceAgencyForCOC`，信任主体是 `op_svc_coc`。
- 典型授权链需要同时核对 IAM 只读、RMS 只读、DCS 用户访问和 COC 服务委托策略；具体角色以当前账号/IAM 返回为准，不在本 skill 中硬编码执行。
- 创建委托或绑定角色时，HTTP `409` 通常表示“已存在/已绑定”的幂等信号；不要把它直接当失败，也不要重复创建。
- 如果通过 COC 临时注入 SSH 公钥，推荐模式是：生成短期 key pair -> COC 脚本写入 `authorized_keys` -> 先建立 SSH ControlMaster 持久连接 -> 定时清理远端 key、本地私钥和 COC 临时脚本。
- 清理公钥只阻止新的 SSH 认证，已建立的 ControlMaster 会话仍可继续用于当前排障窗口；这能同时降低密钥落地时间和保持任务连续性。

本项目当前只吸收该安全模式和验收标准，不默认自动创建委托、绑定角色或注入密钥。任何委托、角色绑定、脚本执行、临时 SSH 规则都必须走显式确认和后置清理验证。

## Fallback 顺序

1. 复用已验证 SSH key。
   - 私钥必须存在，权限建议为 `0600`。
   - 安全组只允许受限来源 CIDR，不允许全网 SSH。
2. 使用创建时保存的密码 artifact。
   - 不在最终回复里明文打印密码。
   - 登录成功后尽快切换到 key 或临时受控通道。
3. 判断是否可以 reset password。
   - 先查 `ShowResetPasswordFlag` 或等价能力。
   - 需要用户确认重置和重启影响。
4. 对可替换资源使用 cloud-init、重装或重建注入 key 和幂等脚本。
   - 不用于未经确认的生产资源。
5. 如果以上都不可用，停止机内执行，输出缺失证据和可选授权项。

## 安全组和公网边界

- 临时 SSH 入站规则必须限制到用户确认的管理员 IP、办公网、VPN、跳板机或堡垒机来源。
- 不生成 `0.0.0.0/0` 到 TCP 22 的兜底规则。
- 复用已有安全组前，必须读回 `ListSecurityGroupRules` 或 `ShowSecurityGroup` 证据。
- 临时规则需要有清理计划，不能把“排障临时开口”变成长期暴露面。

## 执行后验收

远程执行完成后，不只看命令退出码。至少保留以下证据：

- 登录或远程命令通道：用户、主机名、目标 ECS ID、时间。
- 目标服务：`systemctl status`、进程、监听端口或应用健康检查摘要。
- 网络：本机 `ss -lntp` 和外部协议探测，例如 HTTP 状态码、TLS 证书、ELB member health。
- 日志：只截取有限窗口和关键错误，不回显密钥、token、密码、完整业务数据。
- 清理：临时 SSH 安全组规则、一次性密码、临时脚本和调试文件处理结果。
- 如使用 COC 临时 key：记录委托已存在/已创建、409 幂等处理、脚本提交终态、SSH ControlMaster 建立结果、远端 key 删除、本地私钥删除和临时脚本删除结果。

## 不能宣称完成的情况

- COC 返回 accepted/job_id，但没有终态和命令输出。
- ECS 是 `ACTIVE`，但没有 SSH、COC 或应用协议验收。
- ELB member 仍然 `OFFLINE` 或 `CONNECT_FAILED`。
- Web 只在机器内 curl 成功，公网 DNS/CDN/ELB 路径未验证。
- 只创建了云资源，没有完成机内服务启动或健康检查。
