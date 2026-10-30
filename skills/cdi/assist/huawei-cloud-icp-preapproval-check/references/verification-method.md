# Verification Method

## Step-by-step Verification

| Step | Verification Criteria |
|---|---|
| Input Validation | Company name, business scope, and province are all present and non-empty; OCR output validated by user |
| Script Execution | `check_preapproval.py` exits with code 0; standard output is complete and non-truncated |
| Rule Loading | `--validate-only` passes without error; JSON schema version = 2 |
| Keyword Matching | Matched terms are highlighted with inline code markers; deduplication is stable |
| Template Resolution | Province-specific templates matched first; fallback chain: specific → generic → "not provided" |
| Output Format | Six-column table with headers; disclaimer present; no rewrite or omission |

## Tool Verification

| Tool | Verification Command | Expected Result |
|---|---|---|
| Python 3.8+ | `python --version` | Version >= 3.8 |
| `check_preapproval.py` | `python scripts/check_preapproval.py --validate-only` | Exit code 0, all rules validated |
| `ocr_license.py` | `python scripts/ocr_license.py --image <test-image> --pretty` | Valid JSON with required fields; or graceful error if OCR unavailable |
| OCR dependency | `python -c "import rapidocr_onnxruntime"` | No error |

## Pass/Fail Criteria

| Criterion | Pass | Fail |
|---|---|---|
| `--validate-only` passes | 0 errors | Any validation error |
| All references exist | JSON and markdown present | Missing files |
| Output format | Six-column table + disclaimer | Any column missing or format deviation |
| No network required | Runs offline | Any HTTP request attempted |
| No credential required | Runs without env vars | Fails without API key |
