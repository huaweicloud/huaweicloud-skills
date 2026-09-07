# ECS SSH Access Readiness Playbook

## 目标

创建 ECS 时同时完成 SSH 登录能力闭环，避免资源已经 `ACTIVE` 但 agent 没有可用凭证进入机器。

## 适用场景

- 创建 Linux ECS 后需要 SSH 登录。
- 创建 ECS 后还要在机器内安装或排障 Web、Docker、WordPress、数据库等服务。
- 用户要求“能登录服务器”“能远程排查”“外网可访问并能修服务”。

## 创建前硬门槛

创建 Linux ECS 前必须明确一种登录方式，并确保凭证在本地可用：

1. 密钥对方式，推荐默认使用。
   - `body.server.key_name` 指向目标 region 内存在的 keypair。
   - agent 必须确认本地有对应私钥文件，并且权限限制为 `0600`。
   - 如果 keypair 是刚创建的，必须在创建返回时立刻保存 private key；之后通常不能再次读取完整私钥。
   - 如果目标 ECS 后续需要安装软件、挂载磁盘、启动服务或排障，优先创建任务专用 keypair 并保存私钥，不要引用没有本地私钥、也无法导出的旧 keypair。
2. 密码方式。
   - `body.server.adminPass` 由 agent 在创建前生成。
   - agent 必须先把密码保存到受限权限的本地 artifact。需要交给 SSH 客户端时，
     使用只含密码的单行文件，例如 `credentials/ecs-password.txt`，权限必须为
     `0600`。
   - 日志和最终回复不要明文打印密码，只说明保存位置和使用方式。

`body.server.key_name` 和 `body.server.adminPass` 不要同时设置。二者同时存在时，应停止并让用户选择登录方式。

如果两种凭证都不可用，不要提交 ECS 创建请求。`ACTIVE` 只代表云资源状态，不代表可以 SSH。

## SSH 安全组来源限制

SSH 连通性不能通过全网开放来兜底。创建或复用安全组前必须确认：

- 入方向 TCP `22` 的来源 CIDR 不能是 `0.0.0.0/0`。
- 推荐来源是固定管理员 IP `/32`、办公网 CIDR、VPN CIDR、跳板机/堡垒机安全组或私网管理网段。
- 如果 ECS 创建 JSON 只引用已有安全组 ID，提交前先查询 `ListSecurityGroupRules` 或 `ShowSecurityGroup`，确认没有 `22` + `0.0.0.0/0`。
- 如果用户要求“临时开放 SSH”，仍要让用户给出具体来源 IP/CIDR；不要生成全网 SSH 规则。

## 密码不可事后查询

Linux ECS 的 root 初始密码不是创建后再从云侧查询的可靠信息。`ShowServerPassword` 属于敏感读操作，且主要用于 Windows 初始密码场景；不要把它当作 Linux root 密码恢复路径。

如果创建时没有保存 `adminPass`，也没有可用私钥，标准恢复方式是让用户确认后执行 `ResetServerPassword`，再按需重启并重新验证 SSH。

## 没有 COC 时的纳管阶梯

当任务需要进入 ECS 内执行命令，而当前 region、账号或环境没有可用远程命令/COC 时，不要直接把 COC 缺失当作硬阻塞。按以下顺序收敛：

1. 使用本地已保存的 private key，并确认文件权限为 `0600`。
2. 如果 ECS 有 keypair name，尝试 `KPS ExportPrivateKey`；只有拿到私钥并完成 `ssh -i` 验证，才把该路径视为可用。
3. key 不可用时，使用 `ShowResetPasswordFlag` 判断是否支持在线重置密码。
4. 生成一次性强密码并调用 `ResetServerPassword`；密码只保存在受限临时 artifact，不进入命令参数、环境变量、日志或最终回复。
5. 只为受限来源 CIDR 临时开放 TCP 22，例如用户给定管理员 IP、当前执行环境 `/32`、VPN/办公网或跳板机来源；不要创建全网 SSH 规则。
6. 优先使用当前 runtime 实际提供的受控 SSH 工具。若只能使用 OpenSSH，密码内容
   仍不得进入命令参数或环境变量；可以使用受限密码文件和支持文件输入的认证辅助
   工具。若连续 `Permission denied`，且 sshd/user_data 显示禁用密码登录，不要
   重复重置密码。
7. 登录成功后立即执行目标幂等脚本和验收命令，并在完成后删除临时 SSH 入站规则。

对本轮新建、演示、测试、部署类或可替换资源，如果 key/password 都不可用且 COC 不可用，可以改用 `ReinstallServerWithCloudInit`、`ChangeServerOsWithCloudInit` 或同名重建来注入可用 key、SSH 配置和目标初始化脚本。对明确已有且需保留数据或系统盘状态的生产资源，不要擅自重装；输出缺少的最小执行通道并等待授权。

## 推荐 API / CLI 序列

### 1. 发现和确认登录方式

密钥对路线：

```bash
python3 scripts/hcloud_resource_discovery.py \
  --service KPS \
  --operation ListKeypairs \
  --region=<region> \
  --project-id=<project-id> \
  --pretty
```

需要新建 keypair 时，优先用 `KPS CreateKeypair`，并立即把返回的 `private_key` 保存为受限权限文件：

```bash
mkdir -p credentials/keys/huawei/<region>
umask 077
# 将 CreateKeypair 返回的 private_key 写入下面路径；不要写入日志或最终回复。
chmod 600 credentials/keys/huawei/<region>/<keypair>.pem
```

确认 keypair 后，本地检查私钥：

```bash
test -f <private-key-file>
stat -f '%Lp %N' <private-key-file>
```

密码路线：

```bash
python3 - <<'PY'
import secrets
import string
from pathlib import Path

chars = string.ascii_letters + string.digits + '!@%-_=+[]:./?'
while True:
    generated_secret = 'Ec2@' + ''.join(secrets.choice(chars) for _ in range(18))
    if (
        any(c.islower() for c in generated_secret)
        and any(c.isupper() for c in generated_secret)
        and any(c.isdigit() for c in generated_secret)
        and any(c in '!@%-_=+[]:./?' for c in generated_secret)
        and 'root' not in generated_secret.lower()
    ):
        break

path = Path('credentials/ecs-password.txt')
path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
path.write_text(generated_secret, encoding='utf-8')
path.chmod(0o600)
print(path)
PY
```

把生成的密码填入 ECS 创建 JSON 的 `body.server.adminPass`，不要同时设置 `key_name`。

### 2. 创建前本地校验

```bash
python3 scripts/hcloud_ecs_create_plan.py \
  --json-input-file=<ecs-create-json> \
  --operation=CreateServers \
  --region=<region> \
  --pretty
```

通过条件：

- `success=true`
- `validation.errors=[]`
- `credential_mode` 为 `keypair` 或 `password`
- `next_steps` 明确包含对应 SSH 验证动作

### 3. dry-run 和提交

先执行 dry-run。只有 dry-run 通过且用户确认费用和公网暴露范围后，才执行 submit。

submit 返回 `job_id` 后：

```bash
python3 scripts/hcloud_ecs_wait_job.py \
  --job-id=<job-id> \
  --region=<region> \
  --project-id=<project-id> \
  --pretty
```

再确认 ECS `ACTIVE`：

```bash
python3 scripts/hcloud_ecs_verify_active.py \
  --server-id=<server-id> \
  --region=<region> \
  --project-id=<project-id> \
  --pretty
```

### 4. SSH 验收

优先使用当前 Agent/runtime 提供的受控 SSH 能力，并按其真实参数、审批和凭据接口
执行。不存在专用能力时，可以使用本地 OpenSSH；不要臆造某个平台的模块或 Tool
名称。凭据文件保持 `0600`，为本任务使用独立 `known_hosts`，并明确目标、端口、
登录用户和远端命令。

密钥对路线：

```bash
ssh \
  -p 22 \
  -i <private-key-file> \
  -o IdentitiesOnly=yes \
  -o StrictHostKeyChecking=accept-new \
  -o UserKnownHostsFile=credentials/known_hosts \
  root@<public-ip> \
  'echo SSH_OK && id && hostname'
```

密码路线：

```bash
sshpass -f credentials/ecs-password.txt \
  ssh \
  -p 22 \
  -o PreferredAuthentications=password \
  -o PubkeyAuthentication=no \
  -o StrictHostKeyChecking=accept-new \
  -o UserKnownHostsFile=credentials/known_hosts \
  root@<public-ip> \
  'echo SSH_OK && id && hostname'
```

`sshpass -f` 只把密码文件路径放入 argv，不把密码内容放入 argv/env。当前环境没有
`sshpass` 或等效安全输入方式时，不要退化为 `sshpass -p`、`SSHPASS` 环境变量或
在 shell 中展开密码；改用密钥、runtime 原生秘密输入或说明最小阻塞条件。

如果 runtime 提供受控网络出口或 action approval，必须使用该边界并忠实处理其
基础设施错误；不要通过换用裸 `ssh`、域名或另一个端口绕过。

验收成功条件：

- 出现 `SSH_OK`。
- `id` 显示当前用户为 `root` 或预期登录用户。
- 可以执行只读诊断命令，例如 `hostname`、`uptime`、`ss -lntp`。

## 失败分流

- 22 端口不通：优先检查安全组、EIP、路由、ACL、本机代理或 VPN。
- TCP 通但无 SSH banner：优先检查代理/TUN 路由、实例内 sshd 状态、22 端口是否被异常服务占用。
- 出现密码提示但认证失败：检查是否使用了创建前保存的 `adminPass`，或是否需要重置密码/重启后生效。
- 密钥认证失败：检查 keypair 名称是否匹配、私钥文件是否对应、文件权限是否为 `0600`。
- SSH 成功但 Web 不通：进入 `ecs-user-data-service-readiness.md` 或具体服务 playbook 做应用层诊断。

## 最终回复必须说明

- 登录方式：`keypair` 或 `password`。
- 凭证保存状态：私钥文件路径或密码 artifact 路径，不输出明文密码。
- SSH 验收结果：成功命令或失败阶段。
- 如果没有完成 SSH 验收，不能说“服务器可登录”或“应用已部署完成”。
