# IAM Policies — huawei-cloud-cloudrobo-train-metrics

## Summary

**This skill requires no Huawei Cloud IAM permissions.** It does not call any
Huawei Cloud API and needs no AK/SK.

Everything the skill does runs locally in the user's training environment:

| Operation | Where it runs | Cloud permission |
|---|---|---|
| Check / install the `ocms` package (`python3 -m pip ...`) | local Python environment | none |
| Copy `scripts/ocms_recorder.py` into the training project | local filesystem | none |
| Edit the training script to call `OcmsRecorder.log()` | local filesystem | none |
| Write `metrics.json` + chart CSVs during training | local directory (`$METRICS` or `<output_dir>/ocms_metrics`) | none |
| Verify the integration (`python3 scripts/verify_ocms.py`) | local Python environment | none |

## Notes

- **ocms download**: the official `ocms` wheel is downloaded through a
  time-limited signed URL published in the Octopus course README. The
  signature in the URL grants access to that single object, so no IAM
  policy or OBS credential is needed.
- **Metric upload**: on the Octopus platform, the platform sets the `METRICS`
  environment variable and collects the files in that directory itself. The
  skill only writes local files and never uploads anything.
- **Training jobs**: submitting the training job itself (for example a
  CloudRobo/ModelArts training task) is out of scope for this skill. The
  permissions for that are listed in the IAM policies of the skill that
  submits the job, such as `huawei-cloud-cloudrobo-train`.

## Least privilege

No IAM policy, system role, or AK/SK needs to be created or granted for this
skill. Do not grant extra permissions for it.
