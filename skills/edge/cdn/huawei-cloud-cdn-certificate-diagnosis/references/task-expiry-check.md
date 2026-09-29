# Step 4: Compute Days Remaining

Call `python scripts/cert_expiry_check.py --expiration_time <ms-timestamp>` to compute the days remaining until certificate expiration.

## Prerequisites

- Step 2 returned `https_status=3` (HTTPS certificate configured)
- Step 3 (certificate probe) has completed (whether successful or partially successful)

## Handling Empty expiration_time

**Key Rule**: If `ShowCertificatesHttpsInfo/v2` did not return a valid `expiration_time` (empty or missing):

1. **Do not calculate**; do not call the Python script (or pass an empty value via `--expiration_time`)
2. Directly report "Certificate expiration time unknown; API did not return a valid expiration time"
3. **Expose the raw API response to the user** for manual judgment
4. The certificate expiration date probed by `cert_probe.py` in Step 3 (the `data.tls.not_after` JSON field, ISO 8601 UTC) can be referenced as supplementary information

## Command

When `expiration_time` is valid (ms timestamp):

```bash
python scripts/cert_expiry_check.py --expiration_time <ms-timestamp>
```

When `expiration_time` is empty (verify the script's handling of empty values):

```bash
python scripts/cert_expiry_check.py --expiration_time ""
```

Expected output (empty value):
```json
{"result": "success", "data": {"days_remaining": null, "status": "unknown"}, "error_msg": ""}
```

## Decision Logic

The Python script outputs a status based on days remaining:

| days_remaining | status | Meaning |
|----------------|--------|---------|
| > 30 | normal | Certificate has sufficient remaining validity (✅) |
| 0 < ≤ 30 | warning | Certificate is about to expire; recommend updating in advance (⚠️) |
| ≤ 0 | expired | Certificate has expired; update immediately (❌) |
| null | unknown | expiration_time is empty or missing; no calculation performed |

## Output Format

The script outputs JSON wrapped in the platform standard envelope `{result, data, error_msg}`; business fields are inside `data`:

```json
{"result": "success", "data": {"days_remaining": <int|null>, "status": "normal|warning|expired|unknown"}, "error_msg": ""}
```

## Example

```bash
# expiration_time valid (far-future expiration)
python scripts/cert_expiry_check.py --expiration_time 1789824000000
# Output: {"result": "success", "data": {"days_remaining": 31, "status": "normal"}, "error_msg": ""}

# expiration_time valid (about to expire)
python scripts/cert_expiry_check.py --expiration_time 1723852800000
# Output: {"result": "success", "data": {"days_remaining": 15, "status": "warning"}, "error_msg": ""}

# expiration_time valid (already expired)
python scripts/cert_expiry_check.py --expiration_time 1722816000000
# Output: {"result": "success", "data": {"days_remaining": -5, "status": "expired"}, "error_msg": ""}

# expiration_time empty
python scripts/cert_expiry_check.py --expiration_time ""
# Output: {"result": "success", "data": {"days_remaining": null, "status": "unknown"}, "error_msg": ""}
```

## Exception Handling

| Exception Scenario | Handling |
|---------------------|----------|
| Python not installed or version < 3.8 | Prompt to install Python >= 3.8; see cli-installation-guide.md; alternatively calculate manually: days remaining ≈ (expiration_time - current ms timestamp) / 86400000 |
| `python` points to Python 2 | Use `python3 scripts/cert_expiry_check.py` instead |
| expiration_time is non-numeric | Script outputs `{"result": "success", "data": {"days_remaining": null, "status": "unknown"}, "error_msg": ""}`; report "Expiration time format invalid" |
| expiration_time is empty | Do not calculate; report "Certificate expiration time unknown; API did not return a valid expiration time"; expose the raw API response to the user |
| Script execution error | Check the script path and Python environment; manual calculation can be used as a fallback |

## Fallback (when Python is unavailable)

If the Python environment is temporarily unavailable, you can calculate manually:

```bash
# Linux/macOS: get current ms timestamp
NOW_MS=$(( $(date +%s) * 1000 ))

# Compute days remaining (replace 1789824000000 with the actual expiration_time)
echo $(( (1789824000000 - NOW_MS) / 86400000 ))
```

## Report Content

Record the following information in the diagnosis report:
- Diagnosis item name: Days Remaining Calculation
- Status: ✅ Pass (normal) / ⚠️ Warning (warning) / ❌ Fail (expired) / ⚠️ Warning (unknown)
- Detail: `data.days_remaining`, `data.status`
- If expiration_time is empty, attach the raw API response
- When Step 3's `cert_probe.py` returned `data.tls.not_after`, include that value as supplementary context (the value is in ISO 8601 UTC, e.g., `2026-09-12T00:00:00Z`)
