# Huawei CCE Stack Example

这是一个最小可运行的华为云 Terraform 示例，用于创建：
- 一个 VPC
- 一个带 DNS 配置的 Subnet
- 一个 EIP
- 一个标准 CCE Cluster

## 设计目标

- 自包含
- 便于评审
- 默认优先 discovery-first
- 先覆盖标准集群本体，节点池留到下一轮单独扩展

## 文件说明

- `versions.tf`: Terraform 和 provider 版本约束
- `provider.tf`: provider 配置
- `variables.tf`: 输入变量
- `main.tf`: 网络、EIP 和 CCE Cluster 资源定义
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
vpc_name          = "demo-cce-vpc"
vpc_cidr          = "192.168.0.0/16"
subnet_name       = "demo-cce-subnet"
subnet_cidr       = "192.168.1.0/24"
subnet_gateway_ip = "192.168.1.1"
cluster_name      = "demo-cce-cluster"
cluster_type      = "VirtualMachine"
```

### 3. 执行

```bash
terraform init
terraform plan
terraform apply
```

## 注意事项

- 子网必须配置 DNS，否则后续 CCE 节点安装会受影响
- 默认会通过 `huaweicloud_cce_flavor_specifications` 自动选择一个可售卖的集群 flavor
- 如果你已经确认了 flavor，也可以显式设置 `cluster_flavor_id`
- 这个示例只创建集群本体，不创建节点池
- 如果你不想新建 EIP，可以把 `create_eip` 设为 `false` 并显式提供 `eip_address`
