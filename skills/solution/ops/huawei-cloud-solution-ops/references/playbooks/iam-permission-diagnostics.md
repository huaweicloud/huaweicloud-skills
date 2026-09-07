# IAM Permission Diagnostics

## 目标

当 hcloud 查询或变更返回 403、AccessDenied、not authorized、permission denied 等错误时，先把错误归类并给出缺失 action / scope / region / project 的下一步，而不是反复换命令重试。

## 适用场景

- 用户遇到 `403`、`AccessDenied`、`Forbidden`、`Unauthorized`。
- safe_exec 输出 `error_details.category=permission`。
- 任务涉及 COC agency、BSS billing、CES metrics、OBS config、CCE kubeconfig、EIP/VPC/RDS 等权限边界。
- 用户不知道该给 IAM 用户加什么权限。

## 标准流程

1. 先确认当前上下文：

```bash
python3 scripts/hcloud_context_inspect.py --pretty
```

2. 真实 hcloud 调用统一通过 safe_exec，以便分类错误并生成 permission hint：

```bash
python3 scripts/hcloud_safe_exec.py \
  --service <SERVICE> \
  --operation <Operation> \
  --arg=--cli-region=<region> \
  --arg=--project_id=<project_id> \
  --expect-json
```

3. 如果输出中有 `permission_hint`，优先给用户展示：
   - service
   - operation
   - required_actions
   - scope
   - 是否可能被 SCP、企业项目、agency、region/project 限制影响

4. 如果没有 permission hint，查 `references/iam-actions-catalog.json` 的同服务近似 action，或提示需要从服务文档/控制台权限模板补证据。

## 常见分类

| 错误表现 | 常见原因 | 下一步 |
| --- | --- | --- |
| `AccessDenied` / `Forbidden` | IAM policy 缺 action | 输出 required actions，要求用户在控制台授权后重试。 |
| BSS 查询失败 | 账单权限独立、账号角色不足 | 进入 `billing-cost-governance.md`，确认账单 scope 和隐私边界。 |
| COC 失败 | 缺 ServiceAgencyForCOC 或 COC service policy | 进入 `coc-readiness.md`，不要直接 fallback 到不受控 SSH。 |
| OBS 403 | obsutil AK/SK 与 hcloud profile 不同、bucket policy 或对象匿名读不足 | 进入 `obs-boundary.md` 或 `obs-static-website-hosting.md`。 |
| CCE kubeconfig/节点操作失败 | CCE action、集群权限或 kubeconfig 权限不足 | 进入 CCE readiness；危险操作仍需二次确认。 |
| 查询为空但无错误 | region/project 错或无资源 | 不当成权限问题，先查上下文和 scope。 |

## 输出给用户时

不要说“权限不够”就结束。至少输出：

- 当前操作想访问哪个 service/operation。
- 失败属于认证、权限、region/project、参数还是资源不存在。
- 需要检查的 IAM action 或权限模板。
- 用户应在控制台/组织/SCP/企业项目中确认的 scope。
- 授权后建议重跑的只读命令。

## 不要做的事

- 不要让用户把 AK/SK 贴进对话。
- 不要为了绕过权限切换到更高风险的工具或账号。
- 不要在权限不明时继续执行写操作。
- 不要把 `not_found`、region 错误或 project 错误误报成权限问题。
