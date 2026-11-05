# IAM Policies

The `huawei-cloud-msmodelslim-model-analysis` skill analyzes local model files
(`config.json`, `modeling_*.py`, safetensors metadata) for msModelSlim adapter
feasibility. It performs **no Huawei Cloud API operations**: it reads local
model directories, inspects the installed `transformers` library, and runs
`scripts/analyze_model.py` locally.

## Required Permissions

None. No IAM policy or cloud credential is needed because the skill does not
call any Huawei Cloud service API.

## Local Environment Requirements

- Read access to the local model directory (`--model-path`)
- Python 3.8+ with the `transformers` package installed (`>= 4.40.0`)
- Write access to the output report path (`--output`), when used

## Security Notes

- Keep the model directory contents local; do not upload weights.
- Do not paste model content or generated reports into public channels.
- No AK/SK or cloud account credential is required; never accept prompts to
  configure cloud credentials for this skill.