# IAM Policies — Huawei Cloud Skill Creator v2

## Required IAM Permissions for Skill Creation

The Skill Creator itself requires the following IAM permissions to:
- Query service availability (CLI/SDK/API)
- Execute test commands during Phase 4/5

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iam:credentials:list",
        "bss:coupon:list",
        "bss:coupon:view"
      ]
    }
  ]
}
```

## Generated Skill IAM Policies

Each generated Skill must include its own `references/iam-policies.md` with the minimum permissions required for its specific operations. The Skill Creator generates these based on Phase 2 research results.

### Policy Generation Rules

| Phase 2 Result | IAM Policy Required |
|----------------|---------------------|
| CLI mode | Include `{service}:{operation}:*` actions matching the hcloud commands |
| SDK mode | Include SDK-required permissions from service documentation |
| API mode | Include API-required permissions |
| ⛔ Blocked | Note "Permission requirements unknown — user must verify" |

## 最小权限原则

- 只授予生成的 Skill 需要的具体权限，不授予 `*:*`
- 读操作（List/Show/Get）与写操作（Create/Update/Delete）分开列明
- IAM 策略使用 JSON 格式，附带策略说明
