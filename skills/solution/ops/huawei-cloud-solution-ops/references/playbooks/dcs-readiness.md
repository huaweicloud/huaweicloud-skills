# DCS Readiness Playbook

## 目标

为 DCS curated registry 覆盖提供只读 readiness、实例配置检查和风险边界。

## 当前状态

- 已 live-smoked：`ListAvailableZones`、`ListMaintenanceWindows`
- 当前 registry 覆盖只读 discovery 和 target-scoped instance readback，不开放通用 mutation submit。

## Readiness 检查

```bash
python3 scripts/hcloud_resource_discovery.py --service DCS --operation ListAvailableZones --region=<region> --pretty
python3 scripts/hcloud_resource_discovery.py --service DCS --operation ListInstances --region=<region> --limit=20 --pretty
python3 scripts/hcloud_resource_discovery.py --service DCS --operation ListMaintenanceWindows --region=<region> --pretty
```

有实例 ID 后：

```bash
python3 scripts/hcloud_resource_query.py --service DCS --operation ListConfigurations --region=<region> --param instance_id=<instance-id> --pretty
python3 scripts/hcloud_resource_query.py --service DCS --operation ListBackupRecords --region=<region> --param instance_id=<instance-id> --pretty
python3 scripts/hcloud_resource_query.py --service DCS --operation ListDiagnosisTasks --region=<region> --param instance_id=<instance-id> --pretty
```

## 风险边界

DCS 创建、删除、主备切换、参数修改和账号修改不在当前 curated registry 的 change operations 中。后续如果要加入写类能力，必须先补专用 guarded flow、备份/维护窗口检查、实例状态回读和显式确认门禁。
