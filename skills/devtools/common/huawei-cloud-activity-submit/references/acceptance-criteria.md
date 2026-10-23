# 验收标准

## 功能验收

- [ ] `node submit.mjs --help` 正确显示帮助信息
- [ ] `--milestone beginner` dry-run 输出正确的请求体（含 `activity_code`、`milestone`、`work_link`）
- [ ] `--milestone intermediate` dry-run 输出正确的请求体（含 `api_link`）和请求头（含 `X-HW-PROJECT-ID`、`X-HW-REGION`）
- [ ] `--milestone sandbox` / `--milestone ecs` 别名正确归一化
- [ ] 沙箱域名格式校验：非 `devbridge-s2.hwtunnel.com` 域名被拒绝
- [ ] ECS 地址校验：缺少 `index.html` 时自动补全
- [ ] `--summary` 超过 500 字时报错
- [ ] 缺少 AK/SK 时报错并提示环境变量
- [ ] `--gallery-published` 正确记录状态
- [ ] 缺少 `--project-id` 或 `--region`（两步均需）时报错

## 安全验收

- [ ] 凭证来源仅限命令行参数和环境变量，不读取文件系统凭据文件
- [ ] AK/SK 不出现在代码中、不写入仓库
- [ ] `--dry-run` 不发送真实请求

## 文档验收

- [ ] SKILL.md 包含 Overview、Prerequisites、Reference Documents 章节
- [ ] references/ 目录包含 iam-policies.md、verification-method.md、acceptance-criteria.md
- [ ] 凭证优先级文档与代码实现一致（命令行参数 > 环境变量）
