# Task

> 默认优先只使用这个轻量入口。Agent 可按任务复杂度删除、合并或增加字段。

- task_id:
- task_id_source: runtime | agent-generated
- summary:
- goal:
- important_constraints:
- authorization_boundary:
- expected_outcome:
- completion_conditions: # optional; only conditions that matter to the current goal
- status:
- current_approach:
- recent_progress:
- important_changes_or_failures:
- evidence_and_artifacts: # optionally note status/source/time/scope when they affect the conclusion
- unknown_or_remaining:
- open_questions:
- next_step:
- last_updated:

## 资源生命周期摘要（按需）

> 仅在付费或有副作用资源的创建/删除/替换/绑定、异步恢复或结果未知时保留；继续操作前以实时回读更新，不要写入凭据或完整 API 输出。

| logical_role | expected_count | canonical_resource | state | pending_operation | last_verified_at |
| --- | ---: | --- | --- | --- | --- |
|  |  |  |  |  |  |
