# Module Blueprints

本文件回答一个更偏实战的问题：当用户不是只要一段 `.tf`，而是想要“一个可维护的华为云 Terraform 项目”时，应该怎么组织。

## 推荐分层

推荐采用环境层与模块层分离的方式，资源内容使用华为云 provider：

```text
environments/
  dev/
    main.tf
    terraform.tfvars
    versions.tf
  prod/
    main.tf
    terraform.tfvars
    versions.tf

modules/
  networking/
    main.tf
    variables.tf
    outputs.tf
    versions.tf
  ecs_instance/
    main.tf
    variables.tf
    outputs.tf
    versions.tf
  obs_bucket/
    main.tf
    variables.tf
    outputs.tf
    versions.tf
  rds_instance/
    main.tf
    variables.tf
    outputs.tf
    versions.tf
```

## 推荐模块边界

### networking 模块
负责：
- `huaweicloud_vpc`
- `huaweicloud_vpc_subnet`
- `huaweicloud_networking_secgroup`
- 可选 `huaweicloud_networking_secgroup_rule`

输出：
- `vpc_id`
- `subnet_id`
- `security_group_id`

### ecs_instance 模块
负责：
- `huaweicloud_compute_instance`
- 可选 `huaweicloud_vpc_eip`
- 可选 `huaweicloud_compute_eip_associate`

输入：
- `subnet_id`
- `security_group_id`
- `instance_name`
- `image_name` 或 `image_id`
- `flavor_id` 或 flavor 选择条件

### obs_bucket 模块
负责：
- `huaweicloud_obs_bucket`

输入：
- `bucket_name`
- `acl`
- `versioning`
- `encryption`
- `kms_key_id`

### rds_instance 模块
负责：
- `huaweicloud_rds_instance`

输入：
- `vpc_id`
- `subnet_id`
- `security_group_id`
- `availability_zones`
- `db_password`
- `flavor`

## 推荐变量设计

### 优先暴露“业务稳定输入”
例如：
- `instance_name`
- `bucket_name`
- `db_engine`
- `environment`

### 不要过早暴露大量底层可选项
第一版模块优先暴露：
- 关键必填项
- 少量最常变的可选项

不要在第一版就把 provider 每个字段都抛给用户，否则模块会失去价值。

## 推荐输出设计

### networking
- `vpc_id`
- `subnet_id`
- `security_group_id`

### ecs_instance
- `instance_id`
- `private_ip`
- `eip_address`

### obs_bucket
- `bucket_id`
- `bucket_domain_name`

### rds_instance
- `instance_id`
- `private_ips`
- `port`

## 环境层推荐做法

环境层主要负责：
- provider
- 后端配置
- 不同环境的变量值
- 模块组合

模块层不要放 `terraform.tfvars`，`terraform.tfvars` 只放在环境层或组合层。

## 第一轮落地建议

如果用户要求“先做最小可运行版本”，推荐优先输出：
1. 一个 `modules/networking`
2. 一个 `modules/ecs_instance`
3. 一个 `environments/dev/main.tf`

这三部分已经足够跑出第一条主链路。
