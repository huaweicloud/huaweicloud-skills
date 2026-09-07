# Huawei ELB Stack Example

这是一个最小可运行的华为云 Terraform 示例，用于创建：
- 一个 VPC
- 一个 Subnet
- 一个 ELB Load Balancer
- 一个 Listener
- 一个 Backend Pool
- 一个关联到 ELB 的 EIP

## 设计目标

- 自包含
- 便于评审
- 默认只覆盖入口层，不混入后端 ECS
- 适合作为公网入口模板基础

## 文件说明

- `versions.tf`: Terraform 和 provider 版本约束
- `provider.tf`: provider 配置
- `variables.tf`: 输入变量
- `main.tf`: 网络、ELB、Listener、Pool 和 EIP 资源定义
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
region_name       = "cn-north-4"
vpc_name          = "demo-elb-vpc"
vpc_cidr          = "192.168.0.0/16"
subnet_name       = "demo-elb-subnet"
subnet_cidr       = "192.168.1.0/24"
subnet_gateway_ip = "192.168.1.1"
loadbalancer_name = "demo-elb"
```

### 3. 执行

```bash
terraform init
terraform plan
terraform apply
```

## 注意事项

- 这个示例只覆盖负载均衡入口层，不创建后端 member
- 如果你已有公网 EIP，可把 `create_eip` 设为 `false` 并提供 `eip_address`
- 后续若要扩展到真实业务流量，再追加 `huaweicloud_lb_member` 和健康检查
