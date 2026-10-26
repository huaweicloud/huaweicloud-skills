# 验收标准(acceptance-criteria)

本文件定义本 skill 一次部署交付的验收标准:服务成功部署、调用验证通过、产物齐备、资源可管理。执行完整流程后逐项核对,全部满足视为验收通过。

## 一、部署交付验收清单

| # | 验收项 | 判定标准 | 核对 |
|---|--------|---------|------|
| 1 | 模型确认 | 最终模型 ID 为用户确认的模型(模糊名场景已列全候选并经 AskUserQuestion 确认;实验性模型已完成二次确认并记录) | ☐ |
| 2 | 部署形式确认 | 部署形式(single/multinode/pd/pd_colocate)已与用户确认并记录为 `DEPLOY_FORM` + `NNODES` + `REPLICAS`;生成脚本为该形式专用版本,不含 `DEPLOY_FORM` 运行时分支 | ☐ |
| 3 | 镜像就绪 | `SWR_IMAGE_ADDRESS` 已记录并向用户复述确认;tag 来源可追溯到模型文档页面 | ☐ |
| 4 | 部署产物齐备 | `./<模型名>-<部署方式>/` 下含 `start_vllm.sh`、`health_check.sh`(多节点含 `get_master_ip.py`);`chmod +x`、LF 行尾;内容与模板/模型文档一致(确定性取值: 端口 8080、健康检查失败次数 300、启动延迟 600s 等) | ☐ |
| 5 | 产物已上传 | 部署产物已上传到 `CODE_OBS_PATH`(code 目录),路径已记录 | ☐ |
| 6 | 部署成功 | 服务状态 **`RUNNING`**(方式 A `show` / 方式 B 控制台),无反复重启 | ☐ |
| 7 | 调用验证通过 | OpenAI 兼容调用 `/v1/chat/completions` 返回正常文本(`choices[0].message.content` 非空) | ☐ |
| 8 | 调用端点记录 | 调用 URL(`http://{PUBLIC_IP}/v2/infer/{service_id}/v1/chat/completions` 或 `access_address`)已告知用户 | ☐ |
| 9 | 资源可管理 | 用户知晓扩缩容/删除/停止命令(方式 A: `create_infer_service.py scale/delete`;方式 B: 控制台) | ☐ |
| 10 | 凭据安全 | IAM token/OBS AK-SK 未明文落盘(经环境变量/token-file 600);已提醒用户 `docker logout` 清理 SWR 登录凭据(分支 B-2) | ☐ |

## 二、验收通过条件

- 清单 10 项全部核对为 ☐ 已勾选;
- 若部署失败(如 `FAILED`/反复重启),不视为通过——必须按 `references/troubleshooting.md` 定位根因修复后重新部署,直至验收项 6/7 满足;
- 实验性模型部署成功但存在社区已知限制(如性能/可靠性验证中),验收时如实向用户披露,不隐瞒。

## 三、交付物核对(文件完整性)

| 目录 | 文件 | 说明 |
|------|------|------|
| 根目录 | `SKILL.md` | 主文档(≤500 行,含 frontmatter: name/description(Triggers include:)/tags/version) |
| references/ | `deployment-form-decision.md` | 4 种部署形式决策矩阵 |
| references/ | `modelarts-console-guide.md` | 控制台/API 部署详解(9 步 + 请求体 + 场景映射 + 平台适配清单) |
| references/ | `vllm-ascend-model-doc-guide.md` | 模型文档查阅指南 |
| references/ | `ascend-hardware-matrix.md` | 芯片型号速查 |
| references/ | `iam-policies.md` | IAM 最小权限策略与 token 获取 |
| references/ | `verification-method.md` | 部署验证方法 |
| references/ | `acceptance-criteria.md` | 本文件(验收标准) |
| references/ | `artifact-check.md` | 部署产物自检清单(上传 OBS 前强制关卡) |
| references/ | `troubleshooting.md` | 常见问题排查全表 |
| scripts/ | `create_infer_service.py` 等 6 个 | 部署/上传/验证等辅助脚本 |
| templates/ | `start_vllm.single/multinode/pd/pd_colocate.sh`、`health_check.sh` | 启动与探针模板 |
