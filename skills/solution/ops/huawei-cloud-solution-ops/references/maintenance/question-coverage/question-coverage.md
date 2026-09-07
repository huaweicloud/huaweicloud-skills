# 问题覆盖率最小回归样例

这个目录只提供 `check_question_coverage.py` 无参数运行所需的独立回归样例，覆盖只读、更新和删除风险分类，以及 registry 命中检查。

它不是完整用户问题语料，也不能代表所有服务的覆盖率。维护者需要审计完整数据集时，应显式传入：

```bash
python3 scripts/check_question_coverage.py \
  --questions-dir <generated-questions-root> \
  --xlsx-path <validation.xlsx> \
  --pretty
```

默认自检不得搜索 `huawei-cloud-solution-ops` 外部目录。
