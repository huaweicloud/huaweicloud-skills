# Huawei RDS Stack Example

这是一个最小可运行的华为云 Terraform 示例，用于创建：
- 一个 VPC
- 一个 Subnet
- 一个 Security Group
- 一个 PostgreSQL RDS 实例

## 设计目标

- 自包含
- 便于评审
- 默认走单机 PostgreSQL 场景
- 先把网络依赖一并建好，减少现网依赖

## 文件说明

- `versions.tf`: Terraform 和 provider 版本约束
- `provider.tf`: provider 配置
- `variables.tf`: 输入变量
- `main.tf`: 网络和 RDS 资源定义
- `outputs.tf`: 输出结果

## 推荐使用方式

### 1. 配置环境变量

先通过宿主凭据注入或受控本地配置，向 Terraform 进程提供同一套 `HW_ACCESS_KEY` 和 `HW_SECRET_KEY`。不要将真实密钥写入命令文本、说明文档、tfvars、shell 历史或日志。以下示例只设置非敏感的区域参数：

```bash
export HW_REGION_NAME="cn-north-4"
```

如果你当前环境里只有项目已有变量，也可以先映射：

```bash
export HW_ACCESS_KEY="$HUAWEI_ACCESS_KEY"
export HW_SECRET_KEY="$HUAWEI_SECRET_KEY"
export HW_REGION_NAME="$HUAWEI_REGION"
```

### 2. 准备变量文件

复制 `terraform.tfvars.example` 为 `terraform.tfvars`，再按实际环境填写：

```hcl
region_name         = "cn-north-4"
vpc_name            = "demo-rds-vpc"
vpc_cidr            = "192.168.0.0/16"
subnet_name         = "demo-rds-subnet"
subnet_cidr         = "192.168.1.0/24"
subnet_gateway_ip   = "192.168.1.1"
security_group_name = "demo-rds-secgroup"
rds_name            = "demordsinstance"
availability_zone   = "cn-north-4a"
rds_flavor_vcpus    = 2
rds_flavor_memory   = 4
```

在执行 plan 前，通过 `TF_VAR_rds_password` 环境变量或受控秘密注入机制提供必填密码；不要把密码写入 `terraform.tfvars`。

### 3. 执行

```bash
terraform init
terraform plan
terraform apply
```

## 注意事项

- 这是单机 PostgreSQL 示例，不是主备高可用示例
- `rds_name` 需要满足华为云命名约束
- `rds_password` 应使用安全来源，不要把真实密码提交到版本库
- 默认会按 `db_version`、`rds_instance_mode`、`rds_flavor_group_type`、`rds_flavor_vcpus`、`rds_flavor_memory` 和 `availability_zone` 自动发现 flavor
- 如果你已经确认了 flavor，也可以显式设置 `rds_flavor`
- `availability_zone` 和 volume 类型仍需要和目标 region 的实际可用性匹配
