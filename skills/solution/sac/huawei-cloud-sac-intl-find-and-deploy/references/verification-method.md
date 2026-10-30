# Verification Method — sac-intl-find-and-deploy-skill

## 1. Catalog search (two stages)

```bash
# Stage A: concept search
python3 scripts/query_catalog.py --keyword "模型网关" --group --out /tmp/sac_verify_stagea.json
# Pass: rows include New API AND LiteLLM; stderr shows "catalog data as of: <generated_at>"
# and the output JSON carries catalog_generated_at + total_solutions;
# describe-aware: --keyword "微服务" hits Nacos, --keyword "语音转写" hits VibeVoice;
# no-match keyword prints full catalog with no_match=true

# Stage B: all regions for picked solution+variant
python3 scripts/query_catalog.py --solution "LiteLLM 统一的AI网关" --variant "单机版部署" --out /tmp/sac_verify_stageb.json
# Pass: ALL regions listed and count matches stage A region_count; candidates[] have template_url/deploy_link

# Freshness: stderr shows "catalog fetched fresh ..."; on network failure script exits 1 after 3 retries (no stale fallback)
python3 scripts/query_catalog.py --keyword "不存在的词" --group   # exercises retry/error path only when network is down
```

## 2. Template download

```bash
python3 scripts/download_tf_template_file.py --url "<template_url>" --out-dir /tmp/sac-verify-workdir
ls /tmp/sac-verify-workdir/*.tf*
```

Pass: `.tf/.tf.json` present.

## 3. Normalize (dry check)

```bash
python3 scripts/normalize_tf_providers.py /tmp/sac-verify-workdir --region "<console_region>"
```

Pass: scans files; missing token aborts with exit 3 (expected without creds).

## 4. Variables

```bash
python3 scripts/list_tf_variables.py /tmp/sac-verify-workdir
```

Pass: list prints; sensitive values masked `********`.

## 5. Terraform (needs creds + confirmation)

```bash
terraform -chdir=/tmp/sac-verify-workdir init
terraform -chdir=/tmp/sac-verify-workdir plan
```

Pass: `plan` clean; `apply` only after explicit user confirmation.
