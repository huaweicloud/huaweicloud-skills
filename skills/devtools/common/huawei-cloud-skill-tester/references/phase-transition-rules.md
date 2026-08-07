# Phase 间跳转/降级/跳过规则

> 与 `scripts/` 实际脚本对齐（**三轨八节** = Phase 0~7，共 8 个 phase）。
> 旧版"Phase 0~9" 描述中提到的 Phase 7/8/9（清理 / 合规 / 终报告）脚本未实现，按"不补缺失模块"原则删除；
> 旧表述"Phase 0~6 共 7 个 phase，Phase 7 是报告聚合"已统一为"三轨八节"。

## 1. 前置依赖矩阵

| Phase | 前置依赖 | 检测文件 | 不可跳过的原因 |
|-------|---------|---------|---------------|
| 0 | 无 | — | 起始阶段 |
| 1 | Phase 0 | `phase-0-summary.json` | 需要 skill 目录完整性信息 |
| 2 | Phase 1 | `phase-1-summary.json` | 需要 commands 列表 |
| 3 | Phase 1+2 | `phase-1-summary.json` + `phase-2-summary.json` | 需要功能清单+技术调研 |
| 4 | Phase 3 | `phase-3-summary.json` | 需要测试用例 |
| 5 | Phase 4 | `phase-4-summary.json`（所有被测 skill） | 需要 commands + capabilities 元数据 |
| 6 | Phase 5 | `phase-5-summary.json`（在第一个 skill 目录下） | 需要冲突扫描结果 |
| 7 | Phase 0~6 | 全部 `phase-N-summary.json`（N=0..6，在第一个 skill 目录下） | 需要所有执行 phase 的 JSON 才能合并报告 |

## 2. 跳过条件

| Phase | 跳过条件 | 记录方式 |
|-------|---------|---------|
| 0 | 永不跳过 | — |
| 1 | 永不跳过 | — |
| 2 | 永不跳过（CLI 不可用是可接受的结果，非跳过理由） | — |
| 3 | 永不跳过 | — |
| 4 | 永不跳过 | — |
| 5 | 永不跳过（1 skill 降级为 self_check，不跳过整个 phase） | `mode: "downgraded_self_check"` |
| 6 | 永不跳过（1 skill 降级为 single_skill_flow） | `mode: "downgraded_single_skill_flow"` |
| 7 | 永不跳过 | — |

## 3. 降级规则

### 3.1 Phase 5 降级条件

```
条件: skills_count == 1
结果: 从"全量触发词冲突扫描"降级为"单 skill 自检"
触发: 无需用户确认，自动降级
字段: phase-5-summary.json.result.mode = "downgraded_self_check"
自检内容:
  - 内部 trigger 子串歧义 (internal_ambiguities)
  - 内部写操作命令两两排序提示 (cycle_warnings)
  - data_flow_tests / parallel_load_test 标记 skipped
```

### 3.2 Phase 6 降级条件

```
条件: skills_count == 1
结果: 从"多 skill 场景链（派生计划）"降级为"单 skill 完整功能闭环（真跑）"
触发: 读取该 skill 的所有 Phase 1 capabilities
     按 list → create → update → delete 排序串联为闭环
字段: phase-6-summary.json.result.mode = "downgraded_single_skill_flow"
写操作门控: ALLOW_WRITES=0 时所有写步骤 status=skip
```

## 4. 异常处理

| 场景 | 处理 | 示例日志 |
|------|------|----------|
| phase-N-summary.json 不存在 | 打印缺失链，退出码 1 | `⛔ phase-2-summary.json 不存在, 从 Phase 2 重新执行` |
| 多个 phase 缺失 | 打印完整缺失链 | `⛔ 缺失 phase: [2, 3, 4]，从 Phase 2 开始` |
| skill 目录不存在 | 报错列出可用 skill | `❌ skill 'xxx' 不存在，可用: [a, b, c]` |
| 0 个 skill 被指定 | 报错退出 | `❌ 未指定任何 skill。使用 --skills 或 --all-installed` |
| 网络/API 超时 | 重试 3 次，失败则标记 fail | `⚠️ TC-F-01 超时，重试 1/3...` |
| 用户 Ctrl+C | 已输出 JSON 保留 | `🛑 中断于 Phase 4，下次 --resume 可恢复` |
| AK/SK 凭证缺失 | Phase 4 / Phase 6 启动时输出 env-var 设置模板到 stderr 并 exit 77（任何模式均不再 prompt） | `⛔ AK/SK 凭证缺失，请在 shell profile / PowerShell $PROFILE 中设置 HUAWEI_ACCESS_KEY / HUAWEI_SECRET_KEY 后重跑 --phase 4 / 6` |
| Phase 0 目录不完整（缺 iam-policies.md） | 整体 verdict=fail | `❌ directory_integrity pass=false` |

## 5. resume 逻辑

```
--resume (默认模式):
  for p in 0..6:
    if phase-p-summary.json 不存在:
      从 p 开始执行
      break

--phase N:
  检查 phase-(N-1).json 存在
  if 存在: 从 N 开始
  if 不存在: 报错 "前置依赖缺失，请从 Phase N-1 开始"

--fresh:
  archive_phase_files  # 移动 phases/phase-*.json 到 phases/archive/<ts>/
  from Phase 0
```

> `--fresh` **不删除任何文件**。`archive_phase_files()` (在 `lib/chain-verify.sh`)
> 把 `phases/phase-*.json` 移到 `phases/archive/<timestamp>/`，保留全部历史。
> 报告 `reports/` 始终保留。`SKILL_INSTALL_DIR` 里的 skill 安装副本在
> pipeline 结束时会被 uninstall（这样下次 run 看到干净安装状态）。

## 6. 批量执行的特殊规则

```
Tier 1 遍历多个 skill:
  skill A 的 Phase 0 失败 → 标记 skill A 为 fail
  → 不影响 skill B 的执行
  → Phase 5/6/7 跳过已 fail 的 skill

例外：如果 --all-installed 且某个 skill 目录损坏，
     标记该 skill 为 fail 但继续处理其他 skill。
     最终报告中汇总所有 fail。
```

## 7. 与旧版"三轨九阶"的差异（历史说明）

旧文档 `architecture.md` 描述过 Phase 0~9：
- 旧 P5 = 清理
- 旧 P6 = 编排冲突扫描
- 旧 P7 = 单 skill 闭环 / 全流程
- 旧 P8 = 合规检查
- 旧 P9 = 最终报告

当前实现合并并重新编号为 Phase 0~6（合并入 Tier 3 的 P7 = 终报告）：
- 清理职责内嵌于 Phase 4 的 `execution_results[i].resource_changes`，残留命令走
  `phase-6-summary.json.result.cleanup.manual_required[]`
- 冲突扫描 = 当前 Phase 5
- 单 skill 闭环 / 多 skill 场景链 = 当前 Phase 6
- 合规检查未实现，已删除
- 终报告 = 当前 Phase 7
