# RFS Stack Readiness Playbook

## 目标

为 RFS curated registry 覆盖提供 stack、template、execution plan 的只读检查边界。

## 当前状态

- 已 live-smoked：`ListPrivateHooks`、`ListPrivateModules`
- 当前 registry 覆盖只读 stack/module/hook discovery 和 target-scoped stack readback，不开放通用 mutation submit。

## Readiness 检查

```bash
python3 scripts/hcloud_resource_discovery.py --service RFS --operation ListPrivateHooks --region=<region> --limit=10 --pretty
python3 scripts/hcloud_resource_discovery.py --service RFS --operation ListPrivateModules --region=<region> --limit=10 --pretty
python3 scripts/hcloud_resource_discovery.py --service RFS --operation ListStacks --region=<region> --limit=10 --pretty
```

有 stack name 后：

```bash
python3 scripts/hcloud_resource_query.py --service RFS --operation GetStackMetadata --region=<region> --param stack_name=<stack-name> --pretty
python3 scripts/hcloud_resource_query.py --service RFS --operation GetStackTemplate --region=<region> --param stack_name=<stack-name> --pretty
python3 scripts/hcloud_resource_query.py --service RFS --operation ListStackResources --region=<region> --param stack_name=<stack-name> --pretty
```

## 风险边界

RFS apply、continue、rollback、create execution plan 和 stack set 变更不在当前 curated registry 的 change operations 中。后续如果要加入写类能力，必须先补 template diff、execution plan、回滚路径、漂移检测和显式确认门禁。
