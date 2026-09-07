# Provider & Auth

本文件定义华为云 Terraform provider 的推荐写法，以及与 `huawei-cloud-solution-ops` / `hcloud` 主链路的环境变量协同规则。

## 推荐 `required_providers`

```hcl
terraform {
  required_providers {
    huaweicloud = {
      source  = "huaweicloud/huaweicloud"
      version = ">= 1.36.0, < 2.0.0"
    }
  }
}
```

说明：
- provider 源应使用 `huaweicloud/huaweicloud`
- 版本约束应明确写出，不要省略
- 版本策略建议使用明确的最小版本和主版本上界，不要完全放开

## 参考快照

当前维护快照来自上游 `huaweicloud/terraform-provider-huaweicloud`；刷新时通过 `--provider-root <provider-source-root>` 显式传入本地 checkout：

- 本地 provider changelog 顶部版本：`1.93.0`
- 本地 changelog 日期：`June 12, 2026`
- 本地 provider docs inventory：1689 个 resource，2251 个 data source

注意：这表示本仓库当前吸收的 reference snapshot，不等同于用户机器或 Terraform Registry 一定已经可用的最新版本。真实执行前仍应以 `terraform init` 下载到的 provider 版本、`.terraform.lock.hcl` 和 Terraform Registry 为准。

## 推荐 provider 配置

### 1. 环境变量驱动，优先推荐

```hcl
provider "huaweicloud" {}
```

推荐配套环境变量：

先通过宿主凭据注入或受控本地配置，向 Terraform 进程提供同一套 `HW_ACCESS_KEY` 和 `HW_SECRET_KEY`。不要将真实密钥写入命令文本、说明文档、tfvars、shell 历史或日志。以下示例只设置非敏感的区域参数：

```bash
export HW_REGION_NAME="cn-north-4"
```

Provider 也兼容部分 OpenStack 风格 `OS_*` 别名，例如 `OS_ACCESS_KEY`、`OS_SECRET_KEY`、`OS_REGION_NAME`、`OS_PROJECT_ID`、`OS_DOMAIN_ID`、`OS_AUTH_URL`。为了减少混淆，`huawei-cloud-solution-ops` 生成的新示例仍优先使用 `HW_*`。

### 2. 显式 provider 参数

```hcl
provider "huaweicloud" {
  region     = var.region_name
  access_key = var.access_key
  secret_key = var.secret_key
}
```

适用场景：
- 示例代码
- 多 provider alias
- 需要明确展示认证来源

### 3. 临时凭证

```hcl
provider "huaweicloud" {
  region         = var.region_name
  access_key     = var.access_key
  secret_key     = var.secret_key
  security_token = var.security_token
}
```

## 与项目现有 `HUAWEI_*` 变量的兼容规则

项目中既有 `hcloud` 主链路可能常用：
- `HUAWEI_ACCESS_KEY`
- `HUAWEI_SECRET_KEY`
- `HUAWEI_REGION`
- `HUAWEI_PROJECT_ID`

Terraform provider 官方常用：
- `HW_ACCESS_KEY`
- `HW_SECRET_KEY`
- `HW_REGION_NAME`
- `HW_PROJECT_NAME`

### 兼容建议
- 文档和 Terraform 最佳实践优先写 `HW_*`
- 如果任务上下文只提供了 `HUAWEI_*`，应提醒用户 Terraform 官方默认读取的是 `HW_*`
- 在联动模式下，可以提示做以下映射：

```bash
export HW_ACCESS_KEY="$HUAWEI_ACCESS_KEY"
export HW_SECRET_KEY="$HUAWEI_SECRET_KEY"
export HW_REGION_NAME="$HUAWEI_REGION"
```

注意：
- `HUAWEI_PROJECT_ID` 不是 provider 官方默认环境变量
- 如果任务需要 project 级别约束，应优先通过显式变量或现网发现确认

## 其他认证方式

根据 provider 文档，华为云 provider 还支持：
- `shared_config_file`
- ECS Instance Metadata Service
- `assume_role`
- `assume_role_with_oidc`

### Shared hcloud config

Provider 能读取 hcloud CLI 配置文件，但有一个重要限制：Terraform 不能直接使用加密后的 hcloud 认证信息。如果要走 shared config，provider 文档要求先关闭 hcloud CLI 认证信息加密：

```bash
hcloud configure set --cli-auth-encrypt=false
```

这会提升 Terraform 兼容性，但也会让本机 hcloud 配置中的认证信息更容易被读取。只有在用户理解凭证暴露风险、机器环境可信、并且不把配置文件提交到仓库时才建议使用。默认路线仍是环境变量、ECS metadata 或更短期的临时凭证。

### ECS metadata

如果 Terraform 运行在已绑定 Agency 的 ECS 上，provider 可以通过 ECS metadata 获取临时凭证。这个方式比在 `.tf` 或 `tfvars` 中保存 AK/SK 更适合长期运行环境。

### Assume role / OIDC

Provider 支持 IAM agency assume role，也支持 OIDC token。相关环境变量包括：

| 变量 | 用途 |
| --- | --- |
| `HW_ASSUME_ROLE_AGENCY_NAME` | Agency 名称 |
| `HW_ASSUME_ROLE_DOMAIN_NAME` | Agency 所在账号名 |
| `HW_ASSUME_ROLE_DOMAIN_ID` | Agency 所在账号 ID |
| `HW_ASSUME_ROLE_DURATION` | 临时凭证有效期 |
| `HW_ASSUME_ROLE_IDP_ID` | OIDC 身份提供商 ID |
| `HW_ASSUME_ROLE_ID_TOKEN` | OIDC token |
| `HW_ASSUME_ROLE_ID_TOKEN_FILE` | OIDC token 文件路径 |

OIDC token 和临时凭证都按敏感信息处理，不能写入示例、日志、plan 摘要或提交到仓库。

## Provider 高级上下文

Provider schema 还支持这些上下文配置：

| 配置/变量 | 用途 |
| --- | --- |
| `cloud` / `HW_CLOUD` | 指定云域，例如公有云或兼容 HCSO 的云域 |
| `auth_url` / `HW_AUTH_URL` / `OS_AUTH_URL` | 指定 IAM endpoint |
| `endpoints` | 按服务覆盖 endpoint |
| `regional` | 控制 endpoint 选择策略 |
| `enterprise_project_id` / `HW_ENTERPRISE_PROJECT_ID` | 企业项目隔离 |
| `max_retries` / `HW_MAX_RETRIES` | provider 重试次数 |
| `signing_algorithm` / `HW_SIGNING_ALGORITHM` | 签名算法选择 |
| `default_tags` | 给支持的资源统一加默认标签 |
| `ignore_tags` | 忽略外部系统写入的标签差异 |

这些配置适合进入企业级模块或复杂环境，不应默认塞进入门示例。agent 需要先确认用户的账号治理、企业项目、endpoint 和标签策略，再生成对应 provider 块。

第一轮 skill 中应当：
- 知道这些方式存在
- 能在用户提及时引用
- 但默认示例仍以 AK/SK 或环境变量方式为主

## 实践规则
- 不要在示例代码里硬编码真实凭证
- 不要把凭证直接写入 `terraform.tfvars` 并提交版本库
- 如果用户已经在 ECS 上运行 Terraform，优先考虑元数据方式而不是明文 AK/SK
- 看到 `hcloud_shared_config_encrypted` 警告时，不要直接建议 Terraform 使用 shared config；先解释 `--cli-auth-encrypt=false` 的风险和替代方案
- `default_tags` / `ignore_tags` 会影响 drift review，生成模块前需要明确用户的标签治理策略
