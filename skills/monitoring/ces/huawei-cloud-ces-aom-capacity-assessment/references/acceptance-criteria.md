# Acceptance Criteria

Checklist for skill delivery acceptance; the skill is usable only when all items pass.

## Structure

- [ ] Directories: `SKILL.md` + `references/` + `scripts/` + `templates/`
- [ ] All files in `references/` use kebab-case naming and include:
      `cli-installation-guide.md`, `iam-policies.md`, `verification-method.md`, `acceptance-criteria.md`
- [ ] `SKILL.md` frontmatter has `name` and `description`, consistent with the directory; referenced file paths actually exist

## Runtime usability

- [ ] `pip install -r scripts/requirements.txt` succeeds
- [ ] `python3 scripts/capacity_cli.py info` outputs: template instructions + instance-type abbreviations + metric list
- [ ] `smoke --region <available region>` returns `{"ok": true}` (fix the DNS environment per troubleshooting-dns.md first)

## Expand (auto-fill metrics)

- [ ] `expand <xlsx>` reads rows with only region/实例类型/实例ID/入口实例ID, expands each into one row per supported metric
- [ ] Original row gets 关键指标/云服务维度/云服务维度资源ID filled (first metric); additional rows inserted for remaining metrics
- [ ] Inserted rows copy base info (region/实例类型/实例ID/入口实例ID/活动增长倍数) from the original row
- [ ] For DMS instances, the tool auto-detects subtype (kafka/rabbitmq/rocketmq) and filters metrics accordingly
- [ ] Rows that already have 关键指标 filled are skipped (idempotent)
- [ ] For metrics requiring 云服务维度资源ID, every discovered value gets its own row (e.g. both DCS cluster nodes); instance ID is used only when discovery finds nothing
- [ ] When the instance-filtered dimension query finds nothing, the namespace-wide fallback recovers this instance's sub-resource IDs, and such recoveries / empty discoveries appear in `warnings`
- [ ] A multi-dimension metric collects even though CES returns the response dimensions in a different order than requested

## Collection correctness

- [ ] `collect` returns real peak/valley data
- [ ] The returned `unit` is CES's real unit (not forced from the registry); `unknown` in data-less windows is filtered out
- [ ] No crash when there is no data / the instance is stopped; returns a clear error message
- [ ] CCE metrics (backend=aom) are collected via `hcloud AOM ListSample`, with output structure identical to CES (peak/valley/unit/dates)
- [ ] All 8 CCE AOM metric_names verified collectible on an account with a real CCE cluster (pre-rename names cpuUsage/memUsedRate/diskUsedRate/memUsage)
- [ ] 云服务维度资源ID rule holds: CCE cluster-dimension metrics (CPU/memory/disk) collect without a resource ID; node/master/POD dimensions without a resource ID report "该指标需要云服务维度资源ID"

## Computation and write-back

- [ ] 峰谷值倍数/压力系数/预计节日上限/扩容建议 consistent with SKILL.md formulas (verify with `calculate` unit tests)
- [ ] 资源上限 is **optional**: user-filled value takes precedence; empty falls back to registry default; both absent outputs "现有数据不支持给出建议"
- [ ] Unit conversion: CES raw unit → registry display unit (including bit/s ↔ Byte/s /8, *8)
- [ ] Excel write-back uses temp file + atomic replace, **no `.bak-*` backups generated**
- [ ] Historical-mode daily peak/valley columns inserted after 【入口实例ID】 in time order

## Error handling

- [ ] Missing required fields (region/实例类型/实例ID/入口实例ID for expand; +关键指标 for assess) → row skipped/errored with details
- [ ] Metric not in registry → `skipped(metric_mismatch/unsupported_service)`, returns the service's supported-metric list
- [ ] Valley = 0 → historical "无法计算", T-24 "无法预测"; no ceiling → "现有数据不支持给出建议"
- [ ] Incompatible multi-entry units → 压力系数 outputs "多入口实例，但单位不兼容"
- [ ] Region no permission / collection failure → goes into `collection_failures` details, reported truthfully by the model