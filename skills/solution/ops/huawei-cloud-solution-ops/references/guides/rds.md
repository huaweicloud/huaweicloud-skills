# RDS Guide

RDS 任务优先收集实例、配置、备份、连接和网络证据。数据库变更会影响可用性和数据安全，默认只做 planner 和只读证据。

## hcloud-first 路径

1. 读取 `references/playbooks/rds-instance-readiness.md`、`cbr-backup-posture.md` 和 `vpc-network-readiness.md`。
2. 用 `hcloud_resource_discovery.py --service RDS` 查询实例列表和基础状态。
3. 已知实例 ID 后，用 `hcloud_resource_query.py` 查询实例详情、配置、备份或参数相关只读信息。
4. 变更类请求先走 `hcloud_service_change_plan.py`，输出风险、dry-run 支持性、回滚和后置验证。
5. 完成后结合 VPC/安全组、连接串、端口、备份和监控证据判断 readiness。

## SDK 补充

- 可用 SDK 补充：`RDS:ShowInstanceConfiguration`。
- 用途：补充实例配置查询的 request model 和参数类型。
- 不用途：不要用 SDK runner 改参数组、重启、扩容、删除或改备份策略。

## 不要做

- 不要读取或输出数据库密码。
- 不要在未确认备份、维护窗口和回滚方式前提交数据库变更。
- 不要把云侧实例 `ACTIVE` 等同于业务连接成功。
