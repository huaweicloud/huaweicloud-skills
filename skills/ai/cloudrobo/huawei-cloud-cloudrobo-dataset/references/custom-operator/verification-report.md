> Part of the custom-operator guide. Index: [custom-operator-reference.md](custom-operator-reference.md)

## 算子验证报告 Verification Report

> 本报告由 cloudrobo-dataset skill 的 Custom Operator Onboarding 流程在验证结束后生成，仅包含本次验证的有用信息。

### 1. 验证概要 Summary

| 项目 Item | 内容 Value |
|-----------|-----------|
| 算子名称 Operator | `{{ operator_name }}` |
| 部署方式 Deploy mode | 把代码打进镜像 镜像内置（image-inbuilt, custom） / 代码放 OBS、运行时挂载 OBS挂载（OBS-mounted, preset） |
| 代码放 OBS、运行时挂载 任务创建方式 Task-creation way | 空间资产-算法 引用已创建算法（`WORKSPACE_ASSETS`+`algo_id`） / OBS算法 直接挂载 OBS 代码（`OBS_ASSETS` 无 `algo_id`） |
| 验证结果 Result | ✅ 通过（SUCCEEDED） / ❌ 不通过 |
| 验证时间 Time | {{ timestamp }} |
| 工作空间 Workspace | {{ workspace_id }}（{{ workspace_name }}） |

### 2. 算子与资产信息 Operator & Assets

| 资产 Asset | 名称 Name | ID | 详情 Detail |
|------------|-----------|-----|-------------|
| 镜像资产 Image asset | `{{ image_asset_name }}` | `{{ image_asset_id }}` | SWR: `{{ image_url }}`（版本 `{{ image_version }}`） |
| 算法资产 Algorithm asset | `{{ algorithm_asset_name }}` | `{{ algorithm_asset_id }}` | `image_source={{ image_source }}` |
| 算法代码位置 Code dir | — | — | `{{ code_dir_or_image_path }}` |

### 3. 数据集 Datasets

| 数据集 Dataset | 名称 Name | ID | 路径 Path |
|----------------|----------|-----|-----------|
| 输入数据集 Input | `{{ input_dataset_name }}` | `{{ input_dataset_id }}` | `{{ input_dataset_obs_path }}` |
| 输出数据集 Output | `{{ output_dataset_name }}` | `{{ output_dataset_id }}` | `{{ output_dataset_obs_path }}` |

### 4. 验证任务 Task

| 项目 Item | 内容 Value |
|-----------|-----------|
| 任务名称 Task name | `{{ task_name }}` |
| 任务 ID Task id | `{{ task_id }}` |
| 任务状态 Status | ✅ SUCCEEDED |
| 运行耗时 Duration | {{ duration_minutes }} 分钟 |
| 输出摘要 Output summary | {{ output_summary }}（示例：152 帧 / 1 个 episode / 视频+parquet 齐全） |

### 5. 结论 Conclusion

本次验证 **通过**。算子 `{{ operator_name }}` 已成功完成数据处理任务，输出数据集
`{{ output_dataset_name }}` 可作为后续训练等流程的输入使用。

---
