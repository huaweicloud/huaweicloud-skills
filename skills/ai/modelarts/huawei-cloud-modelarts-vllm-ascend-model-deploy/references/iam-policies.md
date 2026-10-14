# IAM 最小权限策略与 Token 获取

本文件支撑 SKILL.md 步骤 4.3(方式 A API 自动部署)的 IAM 权限与 token 获取。原则:**最小权限**(least privilege)——只授部署流程实际用到的权限,不授超出范围的宽泛权限。

## 一、部署流程涉及的云服务与最小权限

| 云服务 | 操作 | 所需 IAM Action(最小权限) | 对应 SKILL.md 步骤 |
|--------|------|---------------------------|---------------------|
| IAM | 获取 token(用户名/密码登录) | 无需额外权限(登录即鉴权) | 4.3 token 获取 |
| IAM | 校验 token 可见项目 | 无需额外权限(`GET /v3/auth/projects`) | 4.3 可选校验 |
| ModelArts | 查工作空间 | `modelarts:workspace:list`(或 `modelarts:*:list`) | 4.3 步骤 0 |
| ModelArts | 查资源池 | `modelarts:pool:list` | 4.3 步骤 0 |
| ModelArts | 创建在线服务(CreateInferService) | `modelarts:service:create` | 4.3 |
| ModelArts | 查询服务列表/详情 | `modelarts:service:get` | 4.4 |
| ModelArts | 删除/停止/扩缩容服务 | `modelarts:service:delete`、`modelarts:service:update` | 4.6 / 失败清理 |
| SWR | 拉取/推送镜像 | `swr:repo:list`、`swr:repo:create`、`swr:image:push`、`swr:image:pull` | 步骤 2 |
| OBS | 上传部署产物到 code 目录 | `obs:object:PutObject`、`obs:bucket:ListBucket`(针对目标桶) | 3.4 |
| OBS | 读取权重(服务挂载读取,平台委托) | 委托 `agency` 方式(`group_configs[].secret_type: "agency"`),由 ModelArts 委托代读,用户无需另配 OBS 权限 | 4.3 secret_type |

> **说明**: 具体 Action 名称以华为云 IAM 策略 Action 列表为准(控制台"新建自定义策略"中按服务筛选)。若用户账号是**主账号**或已有"ModelArts FullAccess + OBS Buckets Viewer + SWR FullAccess"类预置策略,可跳过精细授权;子用户(推荐)则按上表最小授权。

## 二、自定义策略 JSON 示例(ModelArts 推理部署最小集)

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "modelarts:service:create",
        "modelarts:service:get",
        "modelarts:service:list",
        "modelarts:service:delete",
        "modelarts:service:update",
        "modelarts:pool:list",
        "modelarts:workspace:list"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "swr:repo:list",
        "swr:image:pull"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "obs:object:PutObject",
        "obs:bucket:ListBucket"
      ],
      "Resource": [
        "obs:::bucket:你的桶名",
        "obs:::object:你的桶名/*"
      ]
    }
  ]
}
```

> **注意**: OBS 桶名需替换为实际桶;若用户只想上传到特定前缀(如 `code/`),可将 object Resource 进一步收窄为 `obs:::object:你的桶名/code/*`。SWR 若只需拉取已有镜像,仅 `swr:image:pull` 即可;需代下载上传(分支 B-2)才需 push/create。

## 三、IAM Token 获取(用户名/密码方式,project scope)

> **强制要求**: token 必须用 **project scope**(与资源池同区域)获取;**禁止 domain scope**(会报 `400 ModelArts.6400 ... getProject() is null`)。**敏感凭据不落盘**: 密码建议经环境变量/交互式输入提供,不写进 shell 历史。

**IAM JSON 请求体**(用户名/密码 + project scope):

```json
{
  "auth": {
    "identity": {
      "methods": ["password"],
      "password": {
        "user": {
          "name": "<IAM 用户名(IAM 子用户)>",
          "password": "<登录密码>",
          "domain": {"name": "<账号名(主账号)>"}
        }
      }
    },
    "scope": {"project": {"name": "<region, 与资源池同区域>"}}
  }
}
```

**调用与提取**(URL `https://iam.<region>.myhuaweicloud.com/v3/auth/tokens` 在白名单内可访问;**必须用 Python requests 调用,禁止 curl `-d` 字符串拼接 JSON body**——Windows bash 下 `'"$VAR"'` 引号拼接致密码传递错误,凭据正确也返回 401):

```python
import requests, urllib3
urllib3.disable_warnings()

url = 'https://iam.<region>.myhuaweicloud.com/v3/auth/tokens'
payload = {
    'auth': {
        'identity': {
            'methods': ['password'],
            'password': {
                'user': {
                    'name': '<IAM 用户名(IAM 子用户)>',
                    'password': '<登录密码>',
                    'domain': {'name': '<账号名(主账号)>'}
                }
            }
        },
        'scope': {'project': {'name': '<region, 与资源池同区域>'}}
    }
}
resp = requests.post(url, json=payload, verify=False, timeout=30)
# 凭据正确返回 201;响应头 X-Subject-Token 即 token
token = resp.headers.get('X-Subject-Token', '')
print('STATUS:', resp.status_code, 'TOKEN_LEN:', len(token))
```

**提取 token(必须用 Python 正则完整提取,禁 shell 管道 `grep|sed|tr`,长 token 会丢字符)**:

```python
import re
content = open("headers.txt", encoding="utf-8").read()
token = re.search(r"(?i)^X-Subject-Token:\s*(\S+)", content, re.M).group(1)
print(token)  # 供 IAM_TOKEN 环境变量使用
```

**校验 token 可见项目(可选)**: `GET https://iam.<region>.myhuaweicloud.com/v3/auth/projects`(带 `X-Auth-Token: <token>`),确认 `project_id` 归属与 region 匹配。

> **字段对应关系(必须先与用户确认)**: 用 AskUserQuestion 收集 IAM 凭据时,**索要顺序固定为「账号名(domain.name)→ IAM 用户名(user.name)→ 密码(password)」**——账号名(主账号)放第一位、用户名(IAM 子用户)次之、密码最后。用户常按"账号名(domain)/ 用户名 / 密码"给出三行——**账号名是主账号(`domain.name`)、用户名是 IAM 子用户(`user.name`)、密码是登录密码**。收集后按"账号名(domain.name)、IAM 用户名(user.name)、密码(password)"顺序复述字段对应关系再取 token。顺序错配会 401(`The username or password is wrong`,连续错有账号锁定风险)。
