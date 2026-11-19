# Custom Operator Reference 算子参考手册

Index of the custom-operator reference. This file used to hold ~970 lines; it is now split
by topic. **Open only the part you need.**

## Contents 目录

| Part | File | What it covers |
|---|---|---|
| Operator config catalog | [operator-config-catalog.md](operator-config-catalog.md) | `operator_config.yaml` fields, `ext_metadata` constraints, validation rules |
| Deploy mode comparison | [deploy-mode-comparison.md](deploy-mode-comparison.md) | 把代码打进镜像 vs 代码放 OBS、运行时挂载, image slimming, build network |
| Interaction guidelines | [interaction-guidelines.md](interaction-guidelines.md) | Dialogue control layer: when to ask, how to confirm high-risk operations |
| Verification report | [verification-report.md](verification-report.md) | 《验证报告.md》 template |

## Reading order

- Writing `operator_config.yaml` → [operator-config-catalog.md](operator-config-catalog.md)
- Choosing a deploy mode → [deploy-mode-comparison.md](deploy-mode-comparison.md)
- Unsure whether to ask the customer → [interaction-guidelines.md](interaction-guidelines.md)
- Finishing a run → [verification-report.md](verification-report.md)
