# DNS Zone and Record Readiness Playbook

## 目标

确认公网 Zone、RecordSet 和解析结果一致，避免误改生产域名或错误 TTL。

## 适用场景

- 查询公网 Zone 和记录集
- 创建、修改、删除 DNS 记录前的计划审查
- 排查域名解析不生效或解析到错误目标

## 标准检查

```bash
python3 scripts/hcloud_resource_discovery.py --service DNS --operation ListPublicZones --pretty
python3 scripts/hcloud_resource_discovery.py --service DNS --operation ListRecordSets --pretty
```

有明确 ID 时：

```bash
python3 scripts/hcloud_resource_query.py --service DNS --operation ShowPublicZone --param zone_id=<zone-id> --pretty
python3 scripts/hcloud_resource_query.py --service DNS --operation ShowRecordSet --param recordset_id=<recordset-id> --pretty
```

## 风险边界

- DNS 变更默认高风险，即使 operation 名不是 Delete。
- 创建或修改记录前必须确认 zone、record name、type、value、TTL 和是否已有同名记录。
- 删除记录前必须输出受影响域名和当前解析值。

## 验收

成功时输出 zone ID、recordset ID、记录类型、TTL、值和外部解析探测结果。失败时区分云侧记录不存在、TTL 未过期、递归解析缓存和权威 DNS 配置问题。
