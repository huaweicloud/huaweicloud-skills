# 场景契约

`scenario-contracts.json` 为当前重点场景提供机器可读的任务边界。它不替代 `scenario-router.json`：前者说明任务所需输入、验收证据、交付结构和风险边界，后者负责把自然语言目标路由到本地 playbook 与 planner。

每个契约必须包含：

- `required_inputs`：开始规划前必须确认或明确标为缺失的输入。
- `optional_inputs`：可缩小范围或提升验收质量的输入。
- `evidence_requirements`：不得跳过的事实或验收证据。
- `output_sections`：面向用户输出的固定结构。
- `risk_boundaries`：必须停止自动推进并取得确认的边界。

`hcloud_scenario_router.py` 对命中且有契约的场景返回 `scenario_contract`。契约只用于规划和交付质量控制，不执行 hcloud、SDK、Terraform 或任何资源变更。

维护时，契约 ID 必须等于 `scenario-router.json` 中的本地场景 ID；新增契约前先确认对应的 playbook、planner 和测试都存在。
