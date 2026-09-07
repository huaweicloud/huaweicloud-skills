# DLI Readiness Candidate Playbook

## 目标

为 DLI 从 metadata-backed 晋级 curated 前建立权限、catalog、database、queue 和 SQL 检查边界。

## 当前状态

- 已 live-smoked：`ListAuthInfo`
- 晋级前还需要至少 1 条额外 read-only `command_shape_ok` evidence。

## 候选检查

```bash
python3 scripts/hcloud_resource_discovery.py --service DLI --operation ListAuthInfo --region=<region> --pretty
python3 scripts/hcloud_resource_discovery.py --service DLI --operation ListCatalogs --region=<region> --limit=20 --pretty
python3 scripts/hcloud_resource_discovery.py --service DLI --operation ListDatabases --region=<region> --limit=20 --pretty
```

SQL 只做语法检查时：

```bash
python3 scripts/hcloud_resource_query.py --service DLI --operation CheckSql --region=<region> --param sql='SELECT 1' --pretty
```

## 风险边界

DLI 作业运行、队列关联、资源池、权限、模板和 tag 批量操作默认 planner-only。晋级前不允许 submit；晋级后也要区分只读检查、SQL 语法检查和真实作业执行。
