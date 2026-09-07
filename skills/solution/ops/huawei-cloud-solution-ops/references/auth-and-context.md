# Huawei CLI Auth and Context

## 目标

在执行任何华为云 CLI 任务前，先确认：

- 当前使用哪个 profile
- 当前 region 是什么
- 当前 project 和 domain 是否已显式配置
- 当前是 online 还是 offline mode
- 当前任务是项目级服务还是全局服务

## 认证优先级

根据 KooCLI 常见问题文档，认证优先级大致如下：

1. 命令中直接传入的 AK/SK 或临时安全凭证
2. 显式指定的 profile 或默认 profile
3. `ecsAgency`

含义：

- 如果命令里显式传了 AK/SK，它会压过 profile。
- 如果 profile 已经可用，不要为了默认上下文再追问 AK/SK。
- 如果高优先级认证解析失败，KooCLI 不会自动回退到低优先级认证。

## 环境变量兼容与可见性

本 skill 把 AK/SK 作为同一命名家族解析，绝不从两个家族各取一半：

| 家族 | AK | SK |
| --- | --- | --- |
| Cloud SDK 简写 | `CLOUD_SDK_AK` | `CLOUD_SDK_SK` |
| Cloud SDK 长写 | `CLOUD_SDK_ACCESS_KEY` | `CLOUD_SDK_SECRET_KEY` |
| Terraform/KooCLI 常用 | `HW_ACCESS_KEY` | `HW_SECRET_KEY` |
| 华为云通用 ID 写法 | `HUAWEICLOUD_ACCESS_KEY_ID` | `HUAWEICLOUD_SECRET_ACCESS_KEY` |
| 华为云 SDK 写法 | `HUAWEICLOUD_SDK_AK` | `HUAWEICLOUD_SDK_SK` |
| 华为云通用写法 | `HUAWEICLOUD_ACCESS_KEY` | `HUAWEICLOUD_SECRET_KEY` |
| 简写兼容 | `HUAWEI_ACCESS_KEY` | `HUAWEI_SECRET_KEY` |
| OpenStack 兼容 | `OS_ACCESS_KEY` | `OS_SECRET_KEY` |

region 支持 `CLOUD_SDK_REGION`、`HW_REGION_NAME`、`HW_REGION`、`HUAWEICLOUD_REGION`、`HUAWEI_REGION`、`OS_REGION_NAME`；project/domain/security token 也支持对应的 `CLOUD_SDK_*`、`HUAWEICLOUD_SDK_*`、`HW_*`、`HUAWEICLOUD_*`、`HUAWEI_*`、`OS_*` 写法。MaaS API Key 支持 `MAAS_API_KEY` 和 `MODELARTS_MAAS_API_KEY`。

环境检查只能说明“当前进程是否看得到”。在使用凭据 broker 的运行时中，普通 Agent
进程看不到已保存凭据是正常的；凭据可能仅在受授权的执行子进程中注入。因此：

- 当前进程未发现凭据：配置状态是 `unknown`，不得告诉用户“未配置”。
- action 子进程发现凭据：只报告来源变量和 presence，禁止输出值。
- 输出中的 `***`、`****` 或更多连续星号：表示值存在但已被安全脱敏，不表示空值、无效值或未配置；不要因此要求用户重新输入密钥。

## 默认检查顺序

推荐顺序：

1. `python3 scripts/hcloud_context_inspect.py --pretty`
2. `hcloud configure show`
3. `hcloud configure list --cli-output=json`

需要切 profile 时，再显式使用 `--cli-profile=<name>`。

## 关于 region

大多数任务都需要 `cli-region`。

默认规则：

- 命令里显式指定的 `--cli-region` 优先
- 命令里没指定时，才使用当前 profile 中的 region

因此：

- 如果当前任务跨 region，不要偷用默认 region
- 如果用户没说 region，但当前 profile 已有明确 region，可先按默认值工作，再在回复里说明当前使用范围

## 关于 project_id 和 domain_id

### `project_id`

适用于项目级服务。

例如：

- ECS
- VPC
- IMS
- EVS

如果当前 profile 里没有 `projectId`：

- 先确认当前任务是否真的需要它
- 如果需要，运行：

```bash
python3 scripts/hcloud_project_resolve.py \
  --region=cn-north-4 \
  --pretty
```

解析顺序固定为：

1. 显式 `--project-id`
2. 支持的 project ID 环境变量
3. region 匹配的本地 hcloud profile 缓存
4. 通过 `hcloud_safe_exec.py` 调用 IAM `KeystoneListProjects`

`project_id` 不是密钥，可以原样返回。不要把“缺少 `huaweicloudsdkiam`”当作阻塞：主链路是 hcloud，不需要安装 IAM SDK，也不要自行实现 AK/SK 请求签名。

### `domain_id`

适用于全局服务或全局认证场景。

文档明确提到：

- AK/SK 模式访问全局服务时，可能需要 `cli-domain-id`

因此：

- 如果看到错误提示在追 `cli-domain-id`，不要继续盲试项目级参数

## Offline Mode

KooCLI 支持 online 和 offline mode。

### Offline mode 的优点

- 固定脚本更稳定
- 已下载的离线元数据不会频繁变化

### Offline mode 的风险

- 新服务或新 operation 可能不存在
- 老缓存可能不包含最新参数

### 实际策略

- 当前任务是固定脚本式自动化：offline mode 通常更稳
- 当前任务是临时探索新服务或新 operation：online mode 更灵活

## 当前上下文缺失时的处理原则

### 可以默认继续的场景

- 当前 profile 明确可用
- region 明确
- 当前任务只是查询类

### 不应该硬推进的场景

- profile 不明确
- region 缺失
- 任务是费用敏感或高风险变更
- project 或 domain 明显缺失，且目标服务确实依赖它

## 推荐做法

### 先给出当前上下文摘要

例如：

- 当前 profile：`default`
- 当前 region：`cn-north-4`
- 当前 project：未显式配置
- 当前 mode：`AKSK`

### 再说明本轮作用域

例如：

- 本轮先按 `default` profile 和 `cn-north-4` 执行查询

这会让后续变更更可审查。
