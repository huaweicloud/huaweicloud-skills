# Huawei VPCEP Stack Example

这是一个最小可运行的华为云 Terraform 示例，用于创建：
- 一个 VPC
- 一个 Subnet
- 一个 Security Group
- 一台作为后端服务的 ECS
- 一个 VPCEP Service
- 一个 VPCEP Endpoint

## 设计目标

- 自包含
- 便于评审
- 尽量减少硬编码
- 默认使用 data source 发现 AZ、flavor、image
- 先提供单 VPC 的最小闭环，再按真实需求扩成更复杂的服务提供方/消费方场景

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
region_name           = "cn-north-4"
vpc_name              = "demo-vpcep-vpc"
vpc_cidr              = "192.168.0.0/16"
subnet_name           = "demo-vpcep-subnet"
subnet_cidr           = "192.168.1.0/24"
subnet_gateway_ip     = "192.168.1.1"
security_group_name   = "demo-vpcep-secgroup"
instance_name         = "demo-vpcep-ecs"
key_pair_name         = "your-keypair"
endpoint_service_name = "demo-endpoint-service"
endpoint_name         = "demo-endpoint"
```

### 3. 执行

```bash
terraform init
terraform plan
terraform apply
```

## 注意事项

- 这个示例先覆盖单 VPC 的最小 VPCEP 闭环，不直接展开跨账号或跨 VPC 的服务提供方场景
- `endpoint_service_port_mapping` 默认给出一组 `8080 -> 8080` 映射，可以按实际后端服务调整
- 安全组默认只允许来自当前 VPC CIDR 的服务流量，不默认开放公网入口
- flavor 和 image 的最终可用性仍然取决于 region 和 AZ
- 如果你已经有现网 VPC、subnet 或 ECS，更适合后续再做复用型 VPCEP 模板
