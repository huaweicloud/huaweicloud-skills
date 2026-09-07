# EIP Acceptance Closure Example

这个例子展示如何在不执行真实云操作的情况下，把“给 ECS 绑定或验证 EIP 公网入口”拆成可评审、可采证、可判定的闭环。

## 1. 生成 lifecycle plan

```bash
python3 scripts/hcloud_closure_plan.py \
  --tier lifecycle \
  --service EIP \
  --param publicip_id=<eip-id> \
  --param target_resource_id=<ecs-or-port-id> \
  --param probe_url=https://example.com/health \
  --region=<region> \
  --project-id=<project-id> \
  --pretty > eip-lifecycle-plan.json
```

重点看输出里的 `post_change_verification.acceptance_evidence_plan`。它会列出三个核心证据：

- `publicip_readback`：EIP 状态、地址、带宽、计费和绑定目标。
- `binding_target_readback`：确认 EIP 绑定到预期 ECS 网卡、ELB、NAT 或其他目标。
- `public_protocol_probe`：从公网入口做协议探测，例如 HTTP 健康检查。

## 2. 生成非执行 probe plan

```bash
python3 scripts/hcloud_acceptance_closure.py plan \
  --plan-file=eip-lifecycle-plan.json \
  --pretty
```

这个命令只输出探测模板，不会访问公网、不会调用 hcloud，也不会提交变更。模板用于提醒 Agent 或人工下一步应该采集什么证据。

## 3. 整理本地 evidence status

采集证据后，把结果整理成最小 JSON：

```json
{
  "evidence": {
    "publicip_readback": {
      "status": "passed",
      "summary": "ShowPublicip shows the EIP is bound to the expected target."
    },
    "binding_target_readback": {
      "status": "passed",
      "summary": "The target ECS port matches the requested workload."
    },
    "public_protocol_probe": {
      "status": "warning",
      "summary": "The public HTTP probe reached the host but returned 503."
    }
  }
}
```

状态只使用四类：

- `passed`：证据满足预期。
- `warning`：证据存在，但不应宣称完全可用。
- `missing`：证据未采集或缺输入。
- `blocked`：证据显示硬阻塞或失败。

## 4. 判定验收结果

```bash
python3 scripts/hcloud_acceptance_closure.py evaluate \
  --plan-file=eip-lifecycle-plan.json \
  --evidence-file=eip-evidence-status.json \
  --pretty
```

如果任一核心证据是 `warning`、`missing` 或 `blocked`，最终结果不会是 `passed`。例如上面的 HTTP 503 会让整体状态变成 `warning`，说明 EIP 绑定证据存在，但业务入口还不能宣称完成。

## 边界

- 这个流程不执行真实 submit。
- probe plan 不等于已经采集证据。
- `ShowPublicip` 成功不等于应用可访问。
- 真实绑定、解绑、释放仍应使用 EIP guarded flow，并在用户明确确认后执行。
