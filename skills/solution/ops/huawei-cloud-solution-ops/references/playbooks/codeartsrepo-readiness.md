# CodeArtsRepo Readiness Candidate Playbook

## 目标

为 CodeArtsRepo 从 metadata-backed 晋级 curated 前建立仓库、分支、成员和合并请求的只读检查边界。

## 当前状态

- 已 live-smoked：`ListCurrentUserRepositories`
- 晋级前还需要至少 1 条额外 read-only `command_shape_ok` evidence。

## 候选检查

```bash
python3 scripts/hcloud_resource_discovery.py --service CodeArtsRepo --operation ListCurrentUserRepositories --region=<region> --limit=20 --pretty
python3 scripts/hcloud_resource_discovery.py --service CodeArtsRepo --operation ListGroups --region=<region> --limit=20 --pretty
```

有 repository ID 后：

```bash
python3 scripts/hcloud_resource_query.py --service CodeArtsRepo --operation ListBranches --region=<region> --param repository_id=<repository-id> --pretty
```

## 风险边界

成员、分支保护、deploy key、webhook、文件提交和合并请求操作默认 planner-only。晋级前不允许 submit；晋级后也必须明确项目、仓库、分支和权限影响。
