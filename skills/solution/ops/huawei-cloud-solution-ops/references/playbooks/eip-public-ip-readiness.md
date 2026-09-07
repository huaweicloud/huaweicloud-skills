# EIP Public IP Readiness Playbook

## 目标

确认弹性公网 IP 的状态、带宽和绑定关系，避免只看到创建或绑定命令返回成功就宣布公网入口可用。

## 适用场景

- 查询空闲 EIP
- 创建 EIP
- 将 EIP 绑定到 ECS、ELB 或其他 port
- 解绑、更新带宽或删除 EIP

## 标准检查

1. 查询当前上下文：

```bash
python3 scripts/hcloud_context_inspect.py --pretty
```

2. 生成 EIP 只读发现命令：

```bash
python3 scripts/hcloud_resource_discovery.py \
  --service EIP \
  --operation ListPublicips \
  --region=<region> \
  --project-id=<project-id> \
  --limit=20 \
  --pretty
```

创建 EIP 前额外执行 `EIP ShowPublicIpType`（或当前 catalog 中的等价只读 operation），以目标 region
的真实返回选择公网 IP 类型。不要把其他 region 的 `5_bgp`、`5_sbgp` 等值直接复制到当前请求。

3. 对 EIP 变更生成守护式 flow：

```bash
python3 scripts/hcloud_eip_change_flow.py \
  --operation UpdatePublicip \
  --publicip-id=<publicip-id> \
  --arg=--publicip_id=<publicip-id> \
  --region=<region> \
  --project-id=<project-id> \
  --pretty
```

默认只输出计划和 `ShowPublicip` 验证计划；真实提交必须先执行 dry-run，再由用户确认具体 EIP、计费/网络影响和回滚方式。

4. 对创建或绑定后的 JSON 结果做资源验收：

```bash
python3 scripts/hcloud_resource_verify.py \
  --service EIP \
  --json-file=<safe-exec-result.json> \
  --target-id=<publicip-id> \
  --expect-status BIND_ACTIVE \
  --expect-bound-to=<target-port-or-instance-id> \
  --require-match \
  --pretty
```

## 验收字段

- EIP ID
- 公网 IP 地址
- `status`
- `bandwidth` / 带宽大小
- `port_id`、`instance_id` 或等价绑定字段
- 计费模式和创建时间（如返回中存在）

## 失败分类

- `DOWN` 或 `UNBOUND`：还没有完成绑定，继续查目标 port/ECS/ELB。
- 绑定 ID 不一致：停止后续协议探测，先修正绑定对象。
- 查询为空：确认 region、project、权限和是否使用了正确的 EIP ID。
- 创建请求提示 EIP type/iptype 无效：回到目标 region 的公网 IP 类型查询和 request schema；不要只替换成另一个猜测值。
- 创建、绑定、解绑或删除发生 timeout/transport 中断：读取 `execution_semantics`；若为 `outcome_unknown`，先用 List/Show 回查绑定和资源状态，再决定是否重试。

## 最终输出

成功时给出 EIP ID、公网地址、状态、绑定目标和验证命令。失败时给出当前查询事实和下一步排查路径。
