# Phase 间跳转/降级/跳过规则

## 1. 前置依赖矩阵

| Phase | 前置依赖 | 检测文件 | 不可跳过的原因 |
|-------|---------|---------|---------------|
| 0 | 无 | — | 起始阶段 |
| 1 | Phase 0 | `phase-0-summary.json` | 需要 skill 目录完整性信息 |
| 2 | Phase 1 | `phase-1-summary.json` | 需要 commands 列表 |
| 3 | Phase 1+2 | `phase-1-summary.json` + `phase-2-summary.json` | 需要功能清单+技术调研 |
| 4 | Phase 3 | `phase-3-summary.json` | 需要测试用例 |
| 5 | Phase 4 | `phase-4-summary.json` | 需要资源变更记录 |
| 6 | 所有 skill 的 Phase 5 | 每个 skill 的 `phase-5-summary.json` | 需要所有单技能完成 |
| 7 | Phase 6 | `phase-6-summary.json` | 需要编排冲突检测结果 |
| 8 | — | 不检查（独立阶段） | 合规检查不依赖执行结果 |
| 9 | Phase 0~8 | 全部检查 | 需要所有阶段的 JSON |

## 2. 跳过条件

| Phase | 跳过条件 | 记录方式 |
|-------|---------|---------|
| 0 | 永不跳过 | — |
| 1 | 永不跳过 | — |
| 2 | 永不跳过（CLI 不可用是可接受的结果，非跳过理由） | — |
| 3 | 永不跳过 | — |
| 4 | 永不跳过 | — |
| 5 | Phase 4 无资源变更 | `verdict: skipped`, `mode: "skipped_no_resources"` |
| 6 | 永不跳过（1 skill 降级，0 skill 报错） | `mode: "downgraded_self_check"` |
| 7 | 永不跳过（1 skill 降级，0 skill 报错） | `mode: "downgraded_single_skill_flow"` |
| 8 | 永不跳过 | — |
| 9 | 永不跳过 | — |

## 3. 降级规则

### 3.1 Phase 6 降级条件

```
条件: skills_count == 1
结果: 从"全量编排冲突扫描"降级为"自检模式"
触发: 无需用户确认，自动降级，在 phase-6-summary.json 中记录 mode
```

### 3.2 Phase 7 降级条件

```
条件: skills_count == 1
结果: 从"多skill全流程走通"降级为"单skill完整功能闭环"
触发: 读取该 skill 的所有 Phase 1 capabilities
     按 create→list→update→delete 排序串联为闭环
```

## 4. 异常处理

| 场景 | 处理 | 示例日志 |
|------|------|---------|
| phase-N-summary.json 不存在 | 打印缺失链，退出码 1 | `⛔ phase-2-summary.json 不存在, 从 Phase 2 重新执行` |
| 多个 phase 缺失 | 打印完整缺失链 | `⛔ 缺失 phase: [2, 3, 4]，从 Phase 2 开始` |
| skill 目录不存在 | 报错列出可用 skill | `❌ skill 'xxx' 不存在，可用: [a, b, c]` |
| 0 个 skill 被指定 | 报错退出 | `❌ 未指定任何 skill。使用 --skills 或 --all-installed` |
| 网络/API 超时 | 重试 3 次，失败则标记 fail | `⚠️ TC-F-01 超时，重试 1/3...` |
| 用户 Ctrl+C | 已输出 JSON 保留 | `🛑 中断于 Phase 4，下次 --resume 可恢复` |

## 5. resume 逻辑

```
--resume (默认模式):
  for p in 0..9:
    if phase-p-summary.json 不存在:
      从 p 开始执行
      break

--phase N:
  检查 phase-(N-1).json 存在
  if 存在: 从 N 开始
  if 不存在: 报错 "前置依赖缺失，请从 Phase N-1 开始"

--fresh:
  rm -f phase-*.json
  from Phase 0
```

## 6. 批量执行的特殊规则

```
Tier 1 遍历多个 skill:
  skill A 的 Phase 0 失败 → 标记 skill A 为 fail
  → 不影响 skill B 的执行
  → Phase 6/7/8/9 跳过已 fail 的 skill

例外：如果 --all-installed 且某个 skill 目录损坏，
     标记该 skill 为 fail 但继续处理其他 skill。
     最终报告中汇总所有 fail。
```
