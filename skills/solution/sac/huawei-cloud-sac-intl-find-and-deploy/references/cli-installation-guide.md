# CLI Installation Guide — sac-intl-find-and-deploy-skill

No KooCLI required. Terraform-only skill.

## Python 3.8+

```bash
python3 --version  # >= 3.8
```

Scripts use stdlib only (`urllib`, `json`, `ssl`, `argparse`); no pip packages needed.

## Terraform 1.5+

```bash
terraform version  # >= 1.5
```

Install: https://developer.hashicorp.com/terraform/install

## skill-quality-cli (telemetry)

```bash
bash scripts/ensure_cli.sh  # idempotent, skips if present
bash scripts/install_cli.sh # manual install if ensure warns
skill-quality-cli upgrade   # manual upgrade only, no auto-upgrade
SKILL_QUALITY_REPORT=0      # disable telemetry report
```

## TLS edge cases

Self-signed cert / MITM proxy: pass `--insecure` or `--ca-bundle <pem>` to `query_catalog.py` / `download_tf_template_file.py`.
