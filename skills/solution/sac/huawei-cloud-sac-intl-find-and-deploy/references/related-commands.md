# Related Commands — sac-intl-find-and-deploy-skill

```bash
# Stage A: concept search (solution + variant + region count)
python3 scripts/query_catalog.py --keyword "<business term>" --group --out /tmp/sac_solutions.json

# Stage B: ALL regions for the picked solution+variant
python3 scripts/query_catalog.py --solution "<solution_name>" --variant "<variant>" --out /tmp/sac_candidates.json

python3 scripts/download_tf_template_file.py --url "<template_url>" --out-dir <workdir>
python3 scripts/normalize_tf_providers.py <workdir> --region "<console_region>"
python3 scripts/list_tf_variables.py <workdir>
terraform -chdir=<workdir> init
terraform -chdir=<workdir> plan
terraform -chdir=<workdir> apply
terraform -chdir=<workdir> state list
terraform -chdir=<workdir> output -json
terraform -chdir=<workdir> destroy
bash scripts/ensure_cli.sh
```
