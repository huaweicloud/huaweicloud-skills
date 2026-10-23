# 验证方法

## 端到端验证步骤

### 1. 环境准备

- 确认 Node.js ≥ 18：`node --version`
- 确认 AK/SK 已通过环境变量设置：`echo $HW_ACCESS_KEY`（非空）

### 2. dry-run 验证（不真正提交）

```bash
# 沙箱部署步骤（两步均需 --project-id / --region）
HW_ACCESS_KEY=test_ak HW_SECRET_KEY=test_sk node submit.mjs \
  --milestone beginner \
  --work-link https://abcd1234-3000.devbridge-s2.hwtunnel.com \
  --project-id abc123 --region cn-north-4 \
  --summary "test" \
  --dry-run

# ECS 持久化部署步骤
HW_ACCESS_KEY=test_ak HW_SECRET_KEY=test_sk node submit.mjs \
  --milestone intermediate \
  --api-link http://1.2.3.4/hc-activity/index.html \
  --project-id abc123 --region cn-north-4 \
  --dry-run
```

验证输出中 `body.activity_code` 为 `open-capability-2026-1024`，`body.milestone` 正确。

### 3. 真实提交验证

使用有效 AK/SK 和真实沙箱域名/ECS 地址进行提交，确认返回 `code: "success"`。

### 4. gallery-published 状态验证

```bash
node submit.mjs --gallery-published
```

确认输出"已记录：作品展览馆已发布"。

### 5. 帮助信息验证

```bash
node submit.mjs --help
```

确认帮助信息正确显示所有参数说明。
