# Verification Method

Verify the skill works in the target environment in the following order. `<SKILL_DIR>` in the commands is the skill installation root.

## 0. Prerequisites

```bash
pip install -r <SKILL_DIR>/scripts/requirements.txt   # dependency: openpyxl
hcloud version                                        # hcloud (KooCLI) installed
```

## 1. Info output (offline)

```bash
python3 <SKILL_DIR>/scripts/capacity_cli.py info
```

Expected: three sections — template instructions (including the template file location), the supported instance-type abbreviation list,
and the metric list grouped by 云服务/云服务维度/关键指标 (238 total, including 8 CCE items).

## 2. Connectivity self-check

```bash
python3 <SKILL_DIR>/scripts/capacity_cli.py smoke --region cn-east-3
```

Expected: `{"ok": true, ...}` with `message` = `CES: ok; AOM: ok` (smoke probes both CES and AOM backends;
CCE metrics go through AOM; either backend failing is marked in the message). If false, follow `troubleshooting-dns.md`.

## 3. Single-metric collection

```bash
python3 <SKILL_DIR>/scripts/capacity_cli.py collect \
  --region cn-east-3 --instance-type ecs \
  --metric "ECS CPU使用率" --instance-id <real instance ID> --t24
```

Expected: `ok: true`, with `unit` being CES's real returned unit (e.g. `%`/`B/s`), and peak/valley being actual data.

## 4. Single-row end-to-end assessment

```bash
python3 <SKILL_DIR>/scripts/capacity_cli.py assess-row <capacity_assessment_template.xlsx> \
  --row 2 --mode t24
```

Expected: `ok: true`, `updates` contains 资源上限/单位/t-24峰值/t-24谷值 plus conclusion columns; `unit_converted: true`.

## 5. Full assessment (with write-back)

```bash
python3 <SKILL_DIR>/scripts/capacity_cli.py assess-all <capacity_assessment_template.xlsx> --mode t24
```

Expected: `done: true`, Excel written with result columns; no `.bak-*` backups generated; returns `skipped_rows` / `collection_failures` details.

## 6. Spot-check results

Open the template in Excel and check: 峰谷值倍数/压力系数/预计节日上限/扩容建议 columns have values or match the error wording;
T-24 manually-filled rows do not trigger collection (`assess-row` returns `manual_t24: true`).

## 6b. CCE metric collection (optional; requires the account to have CCE/host monitoring integrated with AOM)

```bash
python3 <SKILL_DIR>/scripts/capacity_cli.py collect \
  --region cn-north-4 --instance-type cce \
  --metric "CCE节点CPU利用率" --instance-id <cluster ID> \
  --dim-resource-id <node ID (hostID)> --t24
```

Expected: `ok: true` (backend=aom, via `hcloud AOM ListSample`), `unit` being AOM's real returned unit (e.g. `Percent`).
- Cluster-dimension metrics (e.g. "CCE CPU利用率") only need `--instance-id <cluster ID>`, no `--dim-resource-id`;
- Node/master/POD-dimension metrics must pass `--dim-resource-id` (= node ID/master node ID/POD name); without it the error is "该指标需要 --dim-resource-id".

## 7. (Optional) abnormal scenarios

- Stop the instance then collect → should return "该时间窗口内无监控数据", not crash;
- Manually fill `t-24峰值/谷值` then assess → no collection request is sent.