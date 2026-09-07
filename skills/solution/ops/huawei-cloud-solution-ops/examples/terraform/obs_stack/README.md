# Huawei OBS Stack Example

这是一个最小可运行的华为云 Terraform 示例，用于创建一个 OBS Bucket，并启用一组常见的基础能力：
- 私有访问控制
- 版本控制
- 默认服务端加密
- 基础标签

## 设计目标

- 自包含
- 便于评审
- 默认采用安全取向的最小配置
- 避免使用公共读写这类高风险默认值

## 文件说明

- `versions.tf`: Terraform 和 provider 版本约束
- `provider.tf`: provider 配置
- `variables.tf`: 输入变量
- `main.tf`: OBS Bucket 资源定义
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
region_name = "cn-north-4"
bucket_name = "your-unique-obs-bucket-name"
environment = "dev"
```

### 3. 执行

```bash
terraform init
terraform plan
terraform apply
```

## 注意事项

- Bucket 名称必须全局唯一
- 默认启用版本控制和加密
- 如需使用 `kms` 加密，必须同时填写 `kms_key_id`
- 如果你需要网站托管、日志或生命周期规则，可以在这个示例基础上继续扩展
