# ICP备案知识问答 · 验证方法

## 验证环境准备

### 1. 检查知识库文件存在

```bash
# 确认 index.json 存在
ls -la C:/Users/x50060590/.cac/skills/huawei-icp-filing-scout/index.json

# 确认知识库目录可访问
ls -la D:/WikiFix/wiki/
```

### 2. 检查 index.json 格式

```bash
# 验证 JSON 格式有效
cat C:/Users/x50060590/.cac/skills/huawei-icp-filing-scout/index.json | python -m json.tool > /dev/null && echo "JSON格式正确"
```

### 3. 验证知识库文档

```bash
# 统计知识库文档数量
cat index.json | python -c "import json,sys; d=json.load(sys.stdin); print(f'共 {d[\"total_docs\"]} 篇文档')"

# 列出所有文档路径
cat index.json | python -c "import json,sys; d=json.load(sys.stdin); [print(doc['path']) for doc in d['docs']]"
```

## 功能验证

### 触发条件验证

**验证场景**：以下问题应该激活此 Skill

| 测试问题 | 预期行为 |
|---|---|
| "华为云ICP备案需要准备什么材料？" | 触发，成功返回备案材料信息 |
| "备案被驳回了怎么处理？" | 触发，成功返回驳回处理指引 |
| "授权码怎么生成？" | 触发，成功返回授权码相关内容 |
| "分公司能在母公司账号下备案吗？" | 触发，成功返回备案限制说明 |
| "阿里云备案怎么弄？" | 触发，但应礼貌拒绝（非华为云） |
| "ECS价格是多少？" | 不触发，说明超出范围 |

### 边界场景验证

| 测试场景 | 预期行为 |
|---|---|
| 知识库有的问题 | 返回准确答案，标明来源 |
| 知识库没有的问题 | 老实说明"暂无收录"，不臆造 |
| 问题表述模糊 | 尽量理解意图，必要时反问确认 |

## 性能验证

### 响应时间

- 单次问答响应时间应 < 3秒（不含用户思考时间）
- 知识库文档数量不影响首次响应速度（lazy load）

### 稳定性

- 连续10次问答无崩溃
- index.json损坏时给出友好错误提示

## 回归验证

每次更新知识库后，执行以下回归测试：

```bash
# 1. 验证 index.json 更新
python -c "import json; json.load(open('index.json'))" && echo "index.json有效"

# 2. 抽样检查文档可读性
python -c "
import json
with open('index.json') as f:
    data = json.load(f)
for doc in data['docs'][:3]:
    import os
    doc_path = os.path.join('D:/WikiFix/wiki', doc['path'])
    assert os.path.exists(doc_path), f'文档缺失: {doc_path}'
print('抽样文档检查通过')
"
```
