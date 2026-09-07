# ECS Guide

ECS 是当前最完整的上云入口。目标不是只创建一台云服务器，而是把规格、镜像、网络、安全组、登录凭证、job 终态、主机登录和应用验收串成闭环。

## hcloud-first 路径

1. 运行 `scripts/hcloud_context_inspect.py --pretty` 确认 profile、region 和 project。
2. 读取 `references/playbooks/ecs-create-readiness.md`、`ecs-ssh-access-readiness.md`、`ims-image-discovery.md`、`kps-keypair-discovery.md`。
3. 用 `hcloud_resource_discovery.py --service ECS --operation ListFlavors`、IMS/KPS/VPC discovery 补齐规格、镜像、密钥、VPC 和子网。
4. 创建前用 `hcloud_ecs_create_plan.py` 校验 `cli-jsonInput`、登录凭证、安全组和 dry-run/submit 命令。
5. 提交后先用 `hcloud_ecs_wait_job.py` 确认 job 终态，再用 `hcloud_ecs_verify_active.py` 确认实例 `ACTIVE`。
6. 如果任务包含部署或运维，继续做 SSH、cloud-init、端口和应用协议验收。

## SDK 补充

- 可用 SDK 补充：`ECS:ListFlavors`、`ECS:ShowServer`、`IMS:ListImages`。
- 用途：补充 request model、参数类型、path/query 参数和 region 线索。
- 不用途：不要用 SDK runner 创建、删除、启停或扩缩容 ECS。

## 不要做

- 不要把 job 成功说成 ECS 可用。
- 不要在没有可用 key/password/cloud-init/COC 通道时承诺机内操作可执行。
- 不要自动开放 SSH 或常见 Web 端口到 `0.0.0.0/0`。
- 不要根据顶层 catalog 猜内联 EIP、NIC、磁盘或批量删除 body；复杂结构先用 `request_contract` 和有限深度 SDK schema 补证。
- 删除 ECS 后要分别回读 EIP 和数据盘处置结果；`delete_publicip`、`delete_volume` 或请求成功不等于所有依赖已经释放。
