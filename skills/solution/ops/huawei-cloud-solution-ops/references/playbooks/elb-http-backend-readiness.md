# ELB HTTP Backend Readiness Playbook

## 目标

让公网或私网 ELB 的 HTTP 后端真正进入 `ONLINE`，并用入口地址完成协议验收。

## 适用场景

- 创建 ELB、listener、pool、member、health monitor
- 后端是 ECS 上的 HTTP 服务
- `operating_status` 为 `OFFLINE`、`NO_MONITOR`、`CONNECT_FAILED` 或公网访问超时

## 创建顺序

1. 确认 VPC、子网和后端 ECS 的内网地址。
2. 先让后端 ECS 服务可用，推荐使用 `ecs-user-data-service-readiness.md`。
3. 安全组至少允许：
   - 外部到 ELB listener 端口
   - ELB 到后端 ECS 的服务端口
4. 创建 ELB、listener、pool、member、health monitor。
5. 轮询 member 到 `ONLINE`。
6. 用 ELB 入口地址做 HTTP 探测。

## 拓扑预检

ELB HTTP 后端是否能 `ONLINE`，首先取决于 ELB 与后端 ECS 是否处在同一套可达网络里。创建 listener、pool、member 前先做一次拓扑矩阵：

- 记录每台后端 ECS 的 `server_id`、内网 IP、网卡 `port_id`、network/subnet ID、VPC ID 和安全组。
- 选一个 canonical VPC/subnet：优先使用用户明确指定的 VPC；其次使用已有目标 ELB 的 VPC；再其次使用主要后端或第一台后端 ECS 所在 VPC。
- 公网 ELB 的 VPC/subnet 必须与后端 member 类型匹配；普通 instance member 优先要求后端 ECS 在同一 VPC，member `subnet_id` 使用该 ECS 网卡所属 subnet。
- 若后端 ECS 分属不同 VPC，不要直接硬加 member，也不要把 VPC peering 当成 ELB member 的默认修复。VPC peering 用于 VPC 间主机互通，不等价于让普通 ELB instance member 自动健康；只有用户明确要求跨 VPC 后端，且 `ip_target_enable`、pool/member 参数、路由和安全组都明确支持时，才走跨 VPC IP member。
- 如果跨 VPC 后端不可用，而任务目标是新建、演示、测试、无状态服务或可替换部署资源，应把不兼容的后端 ECS 重装/重建到 canonical VPC/subnet，并预埋 SSH key/cloud-init 和 `<backend-port>` 健康服务；然后再创建或修复 ELB。判断可替换性应基于用户意图、资源是否承载状态数据、是否有保留系统盘要求、以及是否已有业务依赖证据，而不是基于固定资源名模式。
- 如果后端是明确要保留状态的既有生产 ECS，不要擅自删除或重建；输出当前 VPC/subnet 差异、无法 `ONLINE` 的原因，以及需要用户允许的最小拓扑调整。

## HTTP/Web 入口来源限制

不要把“HTTP 可访问”自动实现为安全组 `0.0.0.0/0`。对以下入方向端口，必须使用受限来源 CIDR：

- `80`、`443`
- 常见应用端口 `3000`、`5000`、`8000`、`8080`

推荐来源包括用户明确提供的客户端 CIDR、办公网/VPN CIDR、CDN/WAF/ELB 来源范围、同 VPC 私网 CIDR 或后端健康检查来源。若用户没有提供来源范围，应先确认，不要提交全网开放规则。

## CONNECT_FAILED 排查

遇到后端 `CONNECT_FAILED`，按顺序检查：

1. member address 是否是后端 ECS 的正确私网 IP。
2. member subnet 是否使用后端 ECS 网卡所属 subnet/neutron subnet。
3. 后端安全组是否允许来自 ELB/同 VPC 的目标端口。
4. 后端 ECS 上是否真的有进程监听端口，例如 Nginx 监听 80。
5. health monitor 的 protocol、port、path 是否与后端服务一致。

每修复一项后再轮询健康状态，不要重复创建新的 ELB 或后端 ECS。

如果外部探测从 `timeout` 变成 `connection refused`，通常说明安全组/网络路径已放通，但后端端口没有进程监听。此时下一步是进入后端 ECS 启动应用或临时健康检查服务，而不是继续改 ELB。

## 后端服务启动边界

- 已有 ECS 上启动后端服务属于机内动作。必须通过已可用的 SSH、COC/远程命令或用户提供的部署通道执行。
- 没有 COC 时，先读取 `ecs-ssh-access-readiness.md`。对新建、演示、测试或可替换后端 ECS，必须通过保存私钥、cloud-init、重装或重建拿到机内执行能力；不要停留在“ELB 云侧已配好但 member OFFLINE”。
- 对创建、部署、配置、验收类任务，若 COC 不可用且后端 ECS 未运行服务，可以自动走受控纳管 fallback 完成后端服务启动：
  1. 优先使用本地已保存 private key；若 ECS 有 keypair name，尝试 `KPS ExportPrivateKey` 并用 `ssh -i` 实测。
  2. key 不可用时，用 `ShowResetPasswordFlag` 确认 ECS 支持在线重置密码。
  3. 生成一次性强密码，调用 `ResetServerPassword`，不要在最终输出中展示密码。
  4. 只为受限来源 CIDR 创建临时 TCP 22 入站规则，例如用户给定管理员 IP、当前执行环境 `/32`、VPN/办公网或跳板机来源。
  5. 用 `sshpass` 依次尝试 root 和镜像默认用户。若 user_data/sshd 显示 `PasswordAuthentication no` 或连续 `Permission denied`，不要重复重置密码。
  6. 登录成功后在每台后端 ECS 执行幂等服务脚本。
  7. 用实例 EIP 或内网探测确认 `<backend-port>` 返回 HTTP 200。
  8. 轮询 ELB member 到 `ONLINE`，并用 ELB 入口地址确认 HTTP 200。
  9. 删除临时 SSH 入站规则；若保留，最终输出规则 ID 和原因。
- 如果业务应用尚未提供，可以启动最小健康检查服务作为部署验收占位，例如 systemd + Python/BusyBox HTTP server，监听 `0.0.0.0:<backend-port>` 并返回 HTTP 200。命名应体现用途，例如 `ppx-health-<backend-port>.service`。
- 若 key 不可用、托管私钥不存在、密码登录被系统策略拒绝且 COC 不可用：
  - 对本轮新建、演示、测试或可替换部署资源，创建/导出任务专用 keypair 后，优先用 `ReinstallServerWithCloudInit` 注入 key 和 `<backend-port>` 健康服务，保留实例身份与 ELB/EIP 关系；需要换镜像时用 `ChangeServerOsWithCloudInit`；无法保留或原实例无意义时再同名重建并重新绑定到 ELB。
  - 对明确已有且需保留业务状态的 ECS，不能宣称 ELB 完成；输出云侧 ELB 配置事实和缺少的机内执行通道。

### 幂等健康服务脚本要点

- 创建固定目录，例如 `/opt/ppx-health-<backend-port>`。
- 写一个最小 HTTP 响应页面，包含主机名和时间，便于区分后端。
- 用 systemd 管理，`Restart=always`，服务监听 `0.0.0.0:<backend-port>`。
- 启动后本机执行 `curl -fsS http://127.0.0.1:<backend-port>/`；公网或 ELB 侧再做协议探测。

## 保守轮询

- 轮询间隔建议 10 到 20 秒。
- 连续 6 到 10 次仍无状态变化时，进入失败分类和输出证据。
- 若发现新的可修复差异，可以修复一次后重置轮询。
- 若没有新证据，不要无限等待到外部超时。

## 最终输出

成功时给出：

- ELB ID、IP、provisioning status
- listener/pool/health monitor ID
- member ID、address、operating status
- `curl` 或 `web_fetch` 的 HTTP 状态

失败时不要说高可用已完成；应输出当前资源事实和剩余阻塞。
