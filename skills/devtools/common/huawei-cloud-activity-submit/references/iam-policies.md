# IAM 权限说明

本 skill 使用 **AK/SK 请求头鉴权**，不依赖 IAM 策略或 hcloud CLI。

## 鉴权方式

通过 HTTP 请求头传递凭证：

- `X-HW-AK`（必填）：华为云 Access Key
- `X-HW-SK`（必填）：华为云 Secret Key
- `X-HW-Security-Token`（可选）：STS 临时凭证时必填

## 附加请求头（两步均需）

`beginner`（沙箱部署）与 `intermediate`（ECS 持久化部署）提交时均携带：

- `X-HW-PROJECT-ID`：Project ID
- `X-HW-REGION`：region（如 `cn-north-4`）

## 凭证来源

优先级：命令行参数 > 环境变量

1. **命令行参数**：`--ak <AK>` / `--sk <SK>` / `--security-token <token>`
2. **环境变量**：`HW_ACCESS_KEY` / `HW_SECRET_KEY` / `HW_SECURITY_TOKEN`（兼容 `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK` / `HUAWEICLOUD_SDK_SECURITY_TOKEN`、`HW_AK` / `HW_SK`）

## 所需权限

AK/SK 对应的 IAM 用户需具备活动接口的调用权限。本 skill 不调用华为云 OpenAPI（ECS/VPC 等），仅调用活动提交接口。
