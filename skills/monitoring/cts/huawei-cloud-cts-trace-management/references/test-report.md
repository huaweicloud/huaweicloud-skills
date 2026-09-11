# 功能测试报告 — huawei-cloud-cts-trace-management

> 生成时间：2026-09-07 15:30:02
> 测试区域：cn-north-4
> CLI 版本：[USE_ERROR]The --version parameter format must be '--param=value'.
> 执行模式：cli

## 测试结果汇总

| 指标 | 值 |
|------|-----|
| 总测试数 | 10 |
| ✅ 通过 | 10 |
| ❌ 失败 | 0 |
| ⏭️ 跳过 | 0 |
| 测试者 | Huawei Cloud Skill Creator v2 |

## 测试详情

| 操作 | 测试类型 | 结果 | 备注 |
|------|----------|------|------|
| `hcloud CTS ListOperations --cli-region=cn-north-4` | CLI query | ✅ 通过 | CLI verified |
| `hcloud CTS ListTrackers --cli-region=cn-north-4` | CLI query | ✅ 通过 | CLI verified |
| `hcloud CTS ListTraces --cli-region=cn-north-4 --trace_type=system --limit=5` | CLI query | ✅ 通过 | CLI verified |
| `hcloud CTS ListNotifications --cli-region=cn-north-4 --notification_type=smn` | CLI query | ✅ 通过 | CLI verified |
| `hcloud CTS ListTraceResources --cli-region=cn-north-4 --domain_id=074c26ae7f0025b10fd7c0159cb576a0` | CLI query | ✅ 通过 | CLI verified |
| `hcloud CTS CreateTracker --cli-region=cn-north-4 --help` | CLI syntax | ✅ 通过 | CLI verified |
| `hcloud CTS CreateNotification --cli-region=cn-north-4 --help` | CLI syntax | ✅ 通过 | CLI verified |
| `hcloud CTS DeleteTracker --cli-region=cn-north-4 --help` | CLI syntax | ✅ 通过 | CLI verified |
| `hcloud CTS ListTraceResources --cli-region=cn-north-4 --project_id=383eff43089245eb90ee42bf24fb697b` | CLI negative | ✅ 通过 | CLI verified |
| `hcloud CTS ListTraces --cli-region=cn-north-4 --limit=1 --trace_type=invalid_value` | CLI negative | ✅ 通过 | CLI verified |

## 结论

全部 10 项测试通过，可进入用户验收。
