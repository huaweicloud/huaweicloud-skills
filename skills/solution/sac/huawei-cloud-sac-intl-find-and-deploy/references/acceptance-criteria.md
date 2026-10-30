# Acceptance Criteria — sac-intl-find-and-deploy-skill

- [ ] Catalog query returns ≥1 candidate for a known keyword (Dify/SQLBot/YOLO)
- [ ] Freshness announced: agent relayed `catalog_generated_at` / `total_solutions` ("以下是截至 … 的最新 SAC 方案目录") before user picks
- [ ] User explicitly picked one row; no auto-pick occurred
- [ ] Deploy recap gate: solution/variant/region/template_url restated and user confirmed before any infra action
- [ ] Credential gate: env presence checked without printing values; user exported env vars or manually edited tfvars; credentials never appeared in chat
- [ ] Template file exists in workdir with `.tf` / `.tf.json` suffix
- [ ] Provider sources normalized (`huaweicloud/huaweicloud`, `hashicorp/kubernetes`)
- [ ] `terraform.auto.tfvars.json` is `600` with `sensitive=true` vars; never shown in chat
- [ ] `plan` reviewed and user confirmed before `apply`
- [ ] `state list` shows expected resources after `apply`
- [ ] `destroy` executed on request; tfvars/state/plan residue deleted and confirmed
