# Huawei ECS Stack Example

这是一个最小可运行的华为云 Terraform 示例，用于创建：
- 一个 VPC
- 一个 Subnet
- 一个 Security Group
- 一台 ECS

## 设计目标

- 自包含
- 便于评审
- 尽量减少硬编码
- 默认使用 data source 发现 AZ、flavor、image

## 文件说明

- `versions.tf`: Terraform 和 provider 版本约束
- `provider.tf`: provider 配置
- `variables.tf`: 输入变量
- `main.tf`: 主资源定义
- `outputs.tf`: 输出结果

## 推荐使用方式

### 1. 配置环境变量

Terraform 官方推荐环境变量：

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
vpc_name            = "demo-vpc"
vpc_cidr            = "192.168.0.0/16"
subnet_name         = "demo-subnet"
subnet_cidr         = "192.168.1.0/24"
subnet_gateway_ip   = "192.168.1.1"
security_group_name = "demo-secgroup"
instance_name       = "demo-ecs"
image_name          = "Ubuntu 20.04 server 64bit"
key_pair_name       = "your-keypair"
ssh_allowed_cidr    = "203.0.113.10/32"
```

### 3. 执行

```bash
terraform init
terraform plan
terraform apply
```

## 注意事项

- `bucket`、`RDS` 等其他资源不在这个示例里
- 默认通过 `key_pair_name` 登录 ECS
- 如果你想改为密码登录，可以把 `main.tf` 里的 `key_pair` 改成 `admin_pass`
- flavor 和 image 的最终可用性仍然取决于 region 和 AZ
- `ssh_allowed_cidr` 必须显式填写，示例不再默认对全网开放 SSH
- `system_disk_type` 和 `system_disk_size` 已显式写出，若当前 region/AZ 不支持请按实际可用值调整
