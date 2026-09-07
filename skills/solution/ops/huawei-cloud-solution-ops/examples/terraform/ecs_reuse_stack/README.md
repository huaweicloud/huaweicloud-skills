# Huawei ECS Reuse Stack Example

这是一个“复用现网网络资源”的华为云 Terraform 示例，用于：
- 复用已有 Subnet
- 复用已有 Security Group
- 创建一台新的 ECS

适合这些场景：
- 你已经通过控制台或 `hcloud` 查到了现网资源 ID
- 你不想再新建 VPC / Subnet / Security Group
- 你想把现网依赖沉淀成 Terraform

## 设计目标

- 复用现网资源
- 仍然保持 Terraform 代码可审查
- 通过 data source 对输入 ID 做二次校验
- 默认使用 data source 发现 AZ、flavor、image

## 文件说明

- `versions.tf`: Terraform 和 provider 版本约束
- `provider.tf`: provider 配置
- `variables.tf`: 输入变量
- `main.tf`: 复用现网依赖并创建 ECS
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
region_name       = "cn-north-4"
subnet_id         = "your-existing-subnet-id"
security_group_id = "your-existing-secgroup-id"
instance_name     = "demo-ecs-reuse"
image_name        = "Ubuntu 20.04 server 64bit"
key_pair_name     = "your-keypair"
```

### 3. 执行

```bash
terraform init
terraform plan
terraform apply
```

## 联动建议

如果你手里还没有 `subnet_id` 和 `security_group_id`，建议先通过现网查询拿到这些值，再填入变量文件。

## 注意事项

- 这个示例不会创建 VPC、Subnet、Security Group
- 输入的 `subnet_id` 和 `security_group_id` 必须属于同一 region
- ECS 所选 flavor、image、AZ 最终仍然受当前 region 可用性约束
- `system_disk_type` 和 `system_disk_size` 已显式写出，若当前 region/AZ 不支持请按实际可用值调整
