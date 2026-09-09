# API Specification — Gallery Platform

Base URL: `https://gallery.developer.huaweicloud.com`（HTTPS，需 TLS 证书校验，见 `scripts/api.mjs` 的 `HOST`/`PORT`）

All API paths are prefixed with `/open-api-public/v1/gallery/`（需 STS 凭证）或 `/open-api-guest/v1/gallery/`（无需凭证，见公告接口）。

## Authentication

**`/open-api-public` 前缀的接口要求调用方通过头域传递最小权限 STS 临时凭证（X-Tmp-Ak / X-Tmp-Sk / X-Security-Token）。**

- 调用方（技能）通过 hcloud 自委托 `SELF_VERIFY` 生成**最小权限临时凭证**（临时 AK/SK + SecurityToken），经请求头传递。
- 网关用该临时凭证调用 `STS.GetCallerIdentity` 解析账号（Domain）ID，校验通过后注入已验证的 `X-Domain-Id`/`X-Domain-Hash` 头域供服务端记录用户信息。
- **不要主动向用户索要永久 AK/SK**——仅使用 STS 临时凭证（默认 900s 有效期）。
- 详见 [SELF_VERIFY 自委托与发布流程](self-verify-publish.md)。

**`/open-api-guest` 前缀的接口无需任何凭证**（访客语义），当前仅公告查询接口使用。

---

## GET /open-api-guest/v1/gallery/announcements/current

Query the single announcement that should be displayed at the current time. Also used as the connectivity check before Step 1 (no credentials required; receiving any HTTP response means the platform is reachable).

### Headers

None（无需任何鉴权头域）。

### Success Response (200)

```json
{
  "success": true,
  "code": "GALLERY.SUCCESS",
  "message": "成功",
  "data": {
    "announcement": {
      "id": "ann-001",
      "content": "新活动上线！详见 [活动说明](https://example.com/a) 与 [报名入口](https://example.com/b)，**今晚 20:00** 截止。",
      "startsAt": "2026-09-04T18:00:00",
      "endsAt": "2026-09-04T20:00:00",
      "timezone": "GMT+8"
    }
  }
}
```

`data.announcement` 为 `null` 时表示当前没有生效中的公告（连通性同样正常）。

### Announcement Object Fields

| Field       | Type   | Description                                                                     |
| ----------- | ------ | ------------------------------------------------------------------------------- |
| `id`        | string | Announcement ID                                                                 |
| `content`   | string | Markdown 行内文本：支持 `[文字](url)` 链接（新窗口打开）、`**加粗**`、`*斜体*`    |
| `startsAt`  | string | 展示起始时间（`timezone` 时区的墙上时间，"YYYY-MM-DDTHH:mm:ss"）                 |
| `endsAt`    | string | 展示终止时间（`timezone` 时区的墙上时间，"YYYY-MM-DDTHH:mm:ss"）                 |
| `timezone`  | string | 起止时间所属时区（`UTC` / `GMT+8`）                                              |

> 展示判定：服务端按 `timezone` 将起止时间换算为 UTC 时刻后与当前时刻比较（`startsAt <= now <= endsAt` 且公告已启用）。启用中的公告展示时间窗互斥，最多返回一条（多条兜底取起始时刻最新）。

---

## GET /open-api-guest/v1/gallery/skills/version

Query the version of a published skill on the platform. Used together with the connectivity check to detect whether the local skill is outdated (a newer version exists server-side). No credentials required.

### Query Parameters

| Parameter | Type   | Required | Description                                                            |
| --------- | ------ | -------- | ---------------------------------------------------------------------- |
| `name`    | string | yes      | Skill name (letters/digits/underscores/hyphens only, 1-32 chars). When querying the publish skill, use `publish-work-to-gallery`. |

### Success Response (200)

```json
{
  "success": true,
  "code": "GALLERY.SUCCESS",
  "message": "成功",
  "data": { "version": "2026.09.09.001" }
}
```

- `data.version`：`YYYY.MM.DD[.NNN]`（`.NNN` 可省略）。技能未在平台登记时 `version` 为 `null`（此时不视为"有新版可升级"）。
- 校验失败：`400 GALLERY.PARAM.MISSING`（缺 `name`）/ `400 GALLERY.PARAM.INVALID`（`name` 含非法字符或超长）。

## GET /open-api-guest/v1/gallery/prompt

Query a prompt template from server `PROMPTS` config by `type|target`. Used to fetch the outdated-skill upgrade hint.

### Query Parameters

| Parameter | Type   | Required | Description     |
| --------- | ------ | -------- | --------------- |
| `type`    | string | yes      | Prompt type     |
| `target`  | string | yes      | Prompt target   |
| `params`  | string | no       | JSON object to inject `\${key}` placeholders (default `{}`) |

### Success Response (200)

```json
{
  "success": true,
  "code": "GALLERY.SUCCESS",
  "message": "成功",
  "data": { "prompt": "您使用的 publish-work-to-gallery 技能已过时，请更新技能后重试：npx skills add ..." }
}
```

升级提示用法：`type=skills&target=outdated`，`data.prompt` 即展示给用户的原样文案（含升级指令，勿自行拼写版本号/命令）。

---

## GET /open-api-public/v1/gallery/camps

Query the list of publicly visible activities (训练营/培训活动).

### Headers

| Header             | Type   | Required | Description                                                                    |
| ------------------ | ------ | -------- | ------------------------------------------------------------------------------ |
| `X-Tmp-Ak`         | string | yes      | 最小权限 STS 临时凭证的 Access Key ID（经头域传递，服务端解析调用方身份）       |
| `X-Tmp-Sk`         | string | yes      | 最小权限 STS 临时凭证的 Secret Access Key                                       |
| `X-Security-Token` | string | yes      | 最小权限 STS 临时凭证的 Security Token（STS_TOKEN）                             |

### Query Parameters

| Parameter    | Type    | Required | Default | Description                                     |
| ------------ | ------- | -------- | ------- | ----------------------------------------------- |
| `pageNo`     | integer | no       | 1       | Page number, starting from 1                    |
| `pageSize`   | integer | no       | 20      | Items per page, max 100                         |
| `name`       | string  | no       | —       | Fuzzy search by activity name                   |
| `school`     | string  | no       | —       | Fuzzy search by school name                     |
| `periodYear` | integer | no       | —       | Filter by period year (exact match, e.g., 2026) |

> Results are sorted by `createdAt` descending.

### Success Response (200)

```json
{
  "success": true,
  "code": "GALLERY.SUCCESS",
  "message": "成功",
  "data": {
    "pageNo": 1,
    "pageSize": 20,
    "total": 15,
    "items": [
      {
        "id": "camp-001",
        "name": "华为云AI训练营",
        "theme": "人工智能",
        "school": "清华大学",
        "activityCategoryId": "category-training",
        "activityCategoryName": "训练营",
        "isSchoolLinked": true,
        "periodYear": 2026,
        "periodNumber": 1,
        "description": "...",
        "startsAt": "2026-03-01",
        "endsAt": "2026-06-30",
        "status": "published"
      }
    ]
  }
}
```

### TrainingCamp Object Fields

| Field                  | Type    | Description                                              |
| ---------------------- | ------- | -------------------------------------------------------- |
| `id`                   | string  | Activity ID (used in publish API)                        |
| `name`                 | string  | Activity name                                            |
| `theme`                | string  | Theme/topic of the activity                              |
| `school`               | string  | Host school name                                         |
| `activityCategoryId`   | string  | Associated activity category ID                          |
| `activityCategoryName` | string  | Associated activity category name (redundant for display) |
| `isSchoolLinked`       | boolean | Whether the camp is linked to a school                  |
| `periodYear`           | integer | Year of the activity period                              |
| `periodNumber`         | integer | Sequential period number within the year                 |
| `description`          | string  | Camp description (nullable)                              |
| `startsAt`             | string  | Start date (YYYY-MM-DD)                                  |
| `endsAt`               | string  | End date (YYYY-MM-DD)                                    |
| `status`               | string  | Camp status: draft, published, hidden, archived, ended   |

### Submission Status Determination

Each camp's submission status is derived from `startsAt`, `endsAt`, `status`, and the current date (today):

| Condition                                                     | Status Label | Submittable | Description                                               |
| ------------------------------------------------------------- | ------------ | ----------- | --------------------------------------------------------- |
| today < `startsAt`                                            | 未开始       | No          | Camp has not started yet                                  |
| `startsAt` <= today <= `endsAt` AND `status` == `"published"` | 可投稿       | Yes         | Camp is active and accepting submissions                  |
| `startsAt` <= today <= `endsAt` AND `status` != `"published"` | 进行中       | No          | Camp is ongoing but not open for submission (e.g., draft) |
| today > `endsAt`                                              | 已结束       | No          | Camp has ended                                            |

Only camps with status label "可投稿" are selectable for work submission. If a user attempts to submit to a camp that is "未开始", "进行中", or "已结束", the request is rejected with `GALLERY.CAMP.UNAVAILABLE`.

### Error Response (400)

```json
{
  "success": false,
  "code": "GALLERY.PARAM.PAGINATION_INVALID",
  "message": "分页参数不合法",
  "httpStatus": 400
}
```

---

## POST /open-api-public/v1/gallery/works

Publish a work to the platform. The work is submitted for review and will appear in the gallery after approval.

> **调用方身份识别（SELF_VERIFY 最小权限 STS）**：调用方通过 `hcloud` 自委托（SELF_VERIFY）生成**最小权限临时凭证**（临时 AK/SK + SecurityToken），经请求头 `X-Tmp-Ak`/`X-Tmp-Sk`/`X-Security-Token` 传递（与 `/camps` 查询接口一致，不放入 multipart 表单）；网关用该临时凭证调用 `STS.GetCallerIdentity` 解析账号（Domain）ID，校验通过后注入已验证的 `X-Domain-Id`/`X-Domain-Hash` 头域供服务端记录用户信息。详见 [SELF_VERIFY 自委托与发布流程](self-verify-publish.md)。

### Headers

| Header              | Type   | Required | Description                                                                                                                                                     |
| ------------------- | ------ | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Idempotency-Key`   | string | no       | Idempotency key (8–128 chars). Retrying with the same key and same body returns the original result. Retrying with the same key but different body returns 409. |
| `X-Tmp-Ak`          | string | yes      | 最小权限 STS 临时凭证的 Access Key ID（调用方通过 hcloud `STS.AssumeAgency` 自委托生成，非永久 AK）。经头域传递，网关读取并解析，不接收 multipart 表单字段。                 |
| `X-Tmp-Sk`          | string | yes      | 最小权限 STS 临时凭证的 Secret Access Key。同上，经头域传递。                                                                                                    |
| `X-Security-Token`  | string | yes      | 最小权限 STS 临时凭证的 Security Token（STS_TOKEN）。同上，经头域传递。                                                                                          |

> ⚠️ STS 凭证三件套必须通过请求头 `X-Tmp-Ak`/`X-Tmp-Sk`/`X-Security-Token` 传递，**不可作为 multipart 表单字段**——由网关只读并校验。这与 `/camps` 查询接口的凭证传递方式一致。

### Request Body (multipart/form-data)

| Field            | Type   | Required | Description                                                                                                                                                                        |
| ---------------- | ------ | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `trainingCampId` | string | yes      | ID of the activity to associate the work with                                                                                                                                      |
| `workName`       | string | yes      | Display name of the work (min 1 char)                                                                                                                                              |
| `introduction`   | string | yes      | One-sentence work introduction (15–50 chars)                                                                                                                                       |
| `image`          | file   | yes      | Binary stream of the cover image (png/jpeg/webp/gif)                                                                                                                               |
| `detail`         | file   | yes      | Detail zip (max 20 MiB). Must contain `README.md` at root and optional `resources/` directory with images. README image references must use `resources/<filename>` relative paths. |
| `gitUrl`         | string | yes      | Git 仓库 clone URL（`https://` 开头、`.git` 结尾）。技能仅做前置宽松校验（https:// + .git），域名白名单由服务端校验并返回错误码。                                                   |
| `gitBranch`      | string | yes      | Git 分支名，常规分支字符（字母/数字/`_`/`-`/`.`/`/`），长度 1–250，由服务端校验。                                                                                                  |
| `envUrl`         | string | yes      | Work access URL. Field required; the API accepts an **empty string `""`** as placeholder when no tunnel was opened in Step 2.                                                      |

> 响应中的 `domainID`（/ `PublishedAgentWork.domainID`）为服务端通过临时凭证解析出的账号（Domain）ID，不再由调用方指定。

### Success Response (201)

```json
{
  "success": true,
  "code": "GALLERY.SUCCESS",
  "message": "成功",
  "data": {
    "work": {
      "id": "work-001",
      "domainID": "domain-xxx",
      "trainingCampId": "camp-001",
      "name": "智能问答系统",
      "introduction": "基于大语言模型的智能问答与知识检索系统",
      "status": "pending_review",
      "authorDisplayName": "张三",
      "image": {},
      "createdAt": "2026-07-28T12:00:00Z",
      "publishedAt": "2026-07-28T12:00:00Z"
    },
    "workUrl": "https://gallery.example.com/works/work-001",
    "reward": {
      "is_success": true,
      "value": 200,
      "error_code": "GALLERY.SUCCESS",
      "error_msg": "成功"
    }
  }
}
```

> **`data.reward` — 即时领取成长积分的结果：** 服务端在作品发布成功后立即代为领取发布作品成长任务积分，领取结果随发布响应一并返回。奖励领取失败不影响发布结果（仍返回 201），仅 `reward.is_success=false`。

### PublishedAgentWork Object Fields

| Field            | Type   | Description                                                             |
| ---------------- | ------ | ----------------------------------------------------------------------- |
| `id`             | string | Work ID                                                                 |
| `domainID`       | string | Domain ID of the publishing user                                        |
| `trainingCampId` | string | Associated activity ID                                                  |
| `name`           | string | Work display name                                                       |
| `introduction`   | string | Work introduction                                                       |
| `status`         | string | Work status: pending_review, published, hidden, archived, review_failed |
| `authorDisplayName` | string | Author display name                                                         |
| `image`          | object | Cover image info (structure TBD)                                        |
| `createdAt`      | string | Creation timestamp (ISO 8601)                                           |
| `publishedAt`    | string | Publication timestamp (ISO 8601)                                        |

### Error Responses

错误响应统一结构：`success:false`、`code`（`GALLERY.<category>.<code>`）、`message`、`httpStatus`。**全部错误码、触发原因与处理方法（单一事实源）见 [error-codes.md](error-codes.md)。** 按 HTTP 状态分组：

| 状态 | 码 |
| --- | --- |
| 400 | `GALLERY.PARAM.*`、`GALLERY.CAMP.INACCESSIBLE/UNAVAILABLE`、`GALLERY.WORK.INACCESSIBLE`、`GALLERY.WORK.CONTENT_POLICY_VIOLATION` |
| 401 | `GALLERY.AUTH.UNAUTHORIZED` |
| 404 | `GALLERY.CAMP.INACCESSIBLE`、`GALLERY.WORK.INACCESSIBLE` |
| 409 | `GALLERY.WORK.DUPLICATE`、`GALLERY.IDEMPOTENCY.CONFLICT` |
| 429 | `GALLERY.RATE_LIMIT.PUBLISH/GENERAL` |
| 500 | `GALLERY.SYSTEM.INTERNAL`、`GALLERY.PUBLISH.IMAGE_PROCESS_FAILED` |

### Reward Object Fields（`data.reward`）

| Field | Type | Description |
| ---- | ---- | ---- |
| `is_success` | boolean | 奖励领取请求是否成功。**注意：当日重复领取也返回 `true`，但不实际发放积分** |
| `value` | number | 领取积分值（取自配置 `WORK_PUBLISH_GROWTH_SCORE`，默认 200；当日已领时仍返回该值但不保证到账） |
| `error_code` | string | 领取异常错误码（如 `GALLERY.REWARD.CREDENTIALS_MISSING`、`GALLERY.REWARD.DEVELOPER_ID_FAILED`、`GALLERY.REWARD.RECEIVE_FAILED`），成功时为 `GALLERY.SUCCESS` |
| `error_msg` | string | 领取异常描述，成功时为「成功」 |

> **⚠️⚠️ 关键陷阱 — 当日重复领取同样返回 `is_success: true`：** 发布作品成长任务**每日仅限领取一次积分**。若今日已领取过（例如之前发布过作品），**接口仍返回 `is_success: true`，但实际不会发放积分**。即：**无法通过响应判断积分是否真正到账**。因此调用方必须始终向用户输出"每日限一次"提示，不能因为 `is_success: true` 就断定积分已发放。详见 SKILL.md Step 8。

> **领取失败不影响发布结果：** 若 `reward.is_success=false`（网络异常、服务端错误、凭证缺失等），作品已发布成功，仅积分领取未成功。告知用户：发布作品任务每日仅限领取一次积分，前往 https://developer.huaweicloud.com/grow 查看积分余额。
