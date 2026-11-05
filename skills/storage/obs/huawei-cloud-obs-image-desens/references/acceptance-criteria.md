# Acceptance Criteria

These criteria define when the skill is considered working and complete.

## Functional Criteria

| # | Criterion | Verification |
| --- | ----------- | -------------- |
| AC-1 | `list` returns image objects under a bucket/prefix | Run `list` on a bucket with known image keys |
| AC-2 | `process` downloads, desensitizes and uploads every matched image | All rules return `"status": "done"`, `failed: 0` |
| AC-3 | `whole` pixels block the full image | Download result and diff hash / open image |
| AC-4 | `blur` applies Gaussian blur to the full image | Result visually blurred |
| AC-5 | `region` mosaics only the given rectangle(s) | Coordinates match a visible mosaic box |
| AC-6 | `region-blur` blurs only the given rectangle(s) | Coordinates match a visible blurred box |
| AC-7 | `region-block` occludes the given rectangle(s) with a solid color | Solid fill within coordinates |
| AC-8 | Results are written to the configured target bucket/prefix | Objects listed under `desensitized/` or chosen prefix |
| AC-9 | Originals are never modified | Source keys unchanged on every rule |
| AC-10 | Non-image files under the prefix are skipped | `list`/`process` ignore `.txt` etc. (unless `--show-all`) |

## Automation Criteria (optional path)

| # | Criterion | Verification |
|---|-----------|--------------|
| AC-11 | `setup-trigger` creates a FunctionGraph function | Function URN returned; visible in console |
| AC-12 | The OBS trigger is created on the chosen bucket/event | Trigger id returned when permission allows |

## Failure handling criteria

| # | Criterion | Verification |
| --- | ----------- | -------------- |
| AC-13 | Unknown rule is rejected with a clear message | `--rule edges` → invalid-choice error |
| AC-14 | Out-of-bounds regions produce `failed` per file, not a crash | `--regions 0,0,9999,9999` handles gracefully |
| AC-15 | Missing obsutil credentials produce a clear hint, not a stack trace | Run without config |

## Compliance

- No AK/SK hardcoding anywhere in the repo; credentials only via env/`hcloud` config.
- No delete operations performed by the skill.
- Write operations require explicit confirmation (or explicit `--yes`).
