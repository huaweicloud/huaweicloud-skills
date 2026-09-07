# VPC Resource Discovery Playbook

## 目标

在 ECS 创建和网络排障前，先确认 VPC、子网和安全组的 discovery 路径。

## 与 `vpc-network-readiness.md` 的区别

- `vpc-network-readiness.md`
  - 讲“网络前置检查需要回答哪些问题”
- 本文件
  - 讲“如何发现 VPC 侧资源、如何在当前环境下处理 discovery 受限的问题”

## 当前环境约束

当前机器已经验证到：

- `VPC` 服务存在于服务目录
- 当前机器没有 `VPC` 的本地 template cache
- service help fallback 也会因为 `APIE_ERROR` 卡住

## 标准步骤

### 1. 先看上下文

```bash
python3 scripts/hcloud_context_inspect.py --pretty
```

### 2. 看本地是否已缓存 VPC

```bash
python3 scripts/hcloud_meta_lookup.py --service=VPC --allow-help-fallback --pretty
```

### 3. 明确最少资源清单

至少要知道：

- VPC
- 子网
- 安全组

如果用户还要公网访问，还需要明确：

- 是否需要 EIP
- 谁负责绑定

## 当前建议

在当前环境里，VPC 相关任务优先交付：

- 发现策略
- 依赖清单
- 创建前检查项

而不是假装已经拿到了可靠的 operation 级参数细节。
