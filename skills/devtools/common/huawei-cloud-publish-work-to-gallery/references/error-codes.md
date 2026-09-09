# Error Codes — Gallery Platform API

平台业务错误码遵循 `GALLERY.<category>.<specific>` 模式，每条响应含 `success: false`、`code`、`message`、`httpStatus`。

> **何时读本文件**：发布/查询 API 返回非 2xx 时，按错误码查表定位修复。

## Parameter Errors (400)

| Code | Message | Cause | Resolution |
| --- | --- | --- | --- |
| `GALLERY.PARAM.MISSING` | 参数缺失 | A required field was omitted | Check all required fields: trainingCampId, workName, image, detail, introduction, gitUrl, gitBranch |
| `GALLERY.PARAM.INVALID` | 参数错误 | A field value is malformed | Validate field formats — ensure strings non-empty, files valid binary |
| `GALLERY.PARAM.GIT_URL_INVALID` | gitUrl 必须以 https:// 开头、.git 结尾 | gitUrl not start with https:// or not end with .git | 引导用户修正 gitUrl 为 https:// 开头、.git 结尾的克隆地址 |
| `GALLERY.PARAM.GIT_URL_DOMAIN_FORBIDDEN` | gitUrl 域名不在允许范围内 | hostname not in server allowlist | 引导用户托管到 gitcode/gitee/github 等支持平台 |
| `GALLERY.PARAM.GIT_BRANCH_INVALID` | gitBranch 不支持字符或长度不合法 | violates conventional branch rules | 用常规分支名（字母数字 `_ - . /`，长度 1–250） |
| `GALLERY.PARAM.IMAGE_INVALID` | 图片参数不合法 | cover image invalid or unsupported format | Regenerate as valid PNG/JPG, < 10MB |
| `GALLERY.PARAM.INTRODUCTION_LENGTH_INVALID` | 作品介绍长度必须为 15-50 个字符 | < 15 or > 50 chars | Re-generate, condensing or expanding to 15–50 |
| `GALLERY.PARAM.DETAIL_ZIP_INVALID` | 详情压缩包不合法 | missing README.md at root, or structure invalid | Rebuild: `README.md` at root + `resources/` only images |
| `GALLERY.PARAM.DETAIL_RESOURCE_UNSUPPORTED` | 详情资源仅允许图片 | `resources/` contains non-image files | Remove non-image files, rebuild and retry |
| `GALLERY.PARAM.PAGINATION_INVALID` | 分页参数不合法 | pageNo/pageSize invalid | pageNo >= 1, 1 <= pageSize <= 100 |

## Authentication Errors (401)

| Code | Message | Cause | Resolution |
| --- | --- | --- | --- |
| `GALLERY.AUTH.UNAUTHORIZED` | 未认证或鉴权失败 | STS 凭证无效或已过期 | 重新执行 Step 1 生成新 STS 凭证（900s 有效期），确保 `X-Tmp-Ak`/`X-Tmp-Sk`/`X-Security-Token` 头域正确传递 |

> **⚠️ STS token 截断（401 常见原因，凭证实际有效）**：`security_token` 是超长 base64 串。若内联成 `--header "X-Security-Token: ${securityToken}"` 命令行参数，Windows 会按 8191 字符上限截断 → 网关验签失败返回 401，但 `GetCallerIdentity` 单独验证凭证又有效。**统一解法：凭证落盘再用文件/环境变量传递——`api.mjs --creds-file /tmp/sts-creds.json` 或 `source /tmp/sts-creds.sh` 后经 `STS_AK/STS_SK/STS_TOKEN` 环境变量。**

## Activity Errors (400/404)

| Code | Message | Cause | Resolution |
| --- | --- | --- | --- |
| `GALLERY.CAMP.INACCESSIBLE` | 活动不存在或不可访问 | activity ID invalid or removed | Re-query the activity list and select a valid activity |
| `GALLERY.CAMP.UNAVAILABLE` | 活动不可投稿 | not accepting submissions (draft/ended) | Inform user, ask to select a different activity |

## Work Errors (400/404/409)

| Code | Message | Cause | Resolution |
| --- | --- | --- | --- |
| `GALLERY.WORK.INACCESSIBLE` | 作品不存在或不可访问 | Work ID not found (GET) | N/A for publish — read error |
| `GALLERY.WORK.DUPLICATE` | 作品已存在 | same name already exists in activity | **⚠️ Stop immediately. Never auto-rename and re-submit.** Report to user, present options: (A) abandon, (B) user provides new name to re-publish, (C) overwrite if supported. User must explicitly choose. |
| `GALLERY.WORK.CONTENT_POLICY_VIOLATION` | 作品内容未通过规则校验 | content failed automated review | Inform user of policy violation, ask to review and modify |

## Publish Errors (500)

| Code | Message | Cause | Resolution |
| --- | --- | --- | --- |
| `GALLERY.PUBLISH.IMAGE_PROCESS_FAILED` | 图片处理失败 | server-side image processing failed | Regenerate cover as valid PNG (1280×720 recommended). Retry |

## Idempotency Errors (409)

| Code | Message | Cause | Resolution |
| --- | --- | --- | --- |
| `GALLERY.IDEMPOTENCY.CONFLICT` | 同一幂等键对应不同请求体 | Idempotency-Key reused with different body | Generate new Idempotency-Key and retry, or omit header |

## Rate Limit Errors (429)

| Code | Message | Cause | Resolution |
| --- | --- | --- | --- |
| `GALLERY.RATE_LIMIT.PUBLISH` | 发布请求过于频繁 | Too many publish requests | Wait 60 seconds and retry |
| `GALLERY.RATE_LIMIT.GENERAL` | 请求过于频繁 | General rate limit exceeded | Wait and retry |

## System Errors (500)

| Code | Message | Cause | Resolution |
| --- | --- | --- | --- |
| `GALLERY.SYSTEM.INTERNAL` | 服务内部异常 | Unhandled server-side error | Retry after 30 seconds. If persists after 3 retries, contact administrator with `requestId` |

## General Error Handling Strategy

```
1. Parse JSON body → extract code, message, httpStatus.
2. Look up error code in tables above.
3. Recoverable (param fix, retry, wait) → take prescribed action.
4. Not recoverable (content policy, duplicate) → inform user, ask how to proceed.
5. Unrecognized code → inform user of raw error, contact administrator.
```