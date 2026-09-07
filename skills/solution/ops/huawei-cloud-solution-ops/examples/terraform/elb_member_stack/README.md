# Huawei ELB Member Stack Example

这是一个最小可运行的华为云 Terraform 示例，用于创建：
- 一个 VPC
- 一个 Subnet
- 一个 ELB Load Balancer
- 一个 Listener
- 一个 Backend Pool
- 一台后端 ECS
- 一个 Backend Member
- 一个 Health Monitor
- 一个关联到 ELB 的 EIP

## 设计目标

- 自包含
- 便于评审
- 覆盖完整入口链：负载均衡 + 后端成员 + 健康检查
- 适合作为简单 Web 入口模板

## 文件说明

- `versions.tf`: Terraform 和 provider 版本约束
- `provider.tf`: provider 配置
- `variables.tf`: 输入变量
- `main.tf`: 网络、ELB、EIP、ECS、Member 和 Monitor 资源定义
- `outputs.tf`: 输出结果

## 推荐使用方式

### 1. 配置环境变量

先通过宿主凭据注入或受控本地配置，向 Terraform 进程提供同一套 `HW_ACCESS_KEY` 和 `HW_SECRET_KEY`。不要将真实密钥写入命令文本、说明文档、tfvars、shell 历史或日志。以下示例只设置非敏感的区域参数：

```bash
export HW_REGION_NAME="cn-north-4"
```

### 2. 准备变量文件

复制 `terraform.tfvars.example` 为 `terraform.tfvars`，再按实际环境填写：

```hcl
region_name                 = "cn-north-4"
vpc_name                    = "demo-elb-vpc"
vpc_cidr                    = "192.168.0.0/16"
subnet_name                 = "demo-elb-subnet"
subnet_cidr                 = "192.168.1.0/24"
subnet_gateway_ip           = "192.168.1.1"
loadbalancer_name           = "demo-elb"
instance_name               = "demo-backend-ecs"
security_group_ingress_cidr = "10.0.0.0/8"
```

在执行 plan 前，通过 `TF_VAR_admin_password` 环境变量或受控秘密注入机制提供必填密码；不要把密码写入 `terraform.tfvars`。

### 3. 执行

```bash
terraform init
terraform plan
terraform apply
```

## 注意事项

- `security_group_ingress_cidr` 必须显式填写，示例不默认开放到全网
- 这个示例默认健康检查使用 HTTP `/`
- 如果你已有公网 EIP，可把 `create_eip` 设为 `false` 并提供 `eip_address`
