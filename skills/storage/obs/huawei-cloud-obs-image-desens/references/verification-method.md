# Verification Method

Follow these steps to confirm the skill behaves correctly in a real OBS environment.

## 0. Prerequisites

- `hcloud obs ls -limit=1` succeeds (obsutil credentials configured)
- `python3 -c "import PIL"` succeeds (Pillow installed)
- A source bucket with at least one known image (e.g. `input/photo.png`), and write
  permission to a target bucket/prefix

## 1. Verify `list`

```bash
python3 scripts/obs_image_desens.py list --bucket <bucket> --prefix input
```

**Expected**: JSON output `{"images": [...]}` where all listed objects are image files
(`.jpg/.jpeg/.png/.bmp/.webp/.gif/.tif/.tiff`) under the requested prefix.

## 2. Verify `process` (all rules)

Run once per rule, each to a distinct target prefix:

```bash
python3 scripts/obs_image_desens.py process \
  --source-bucket <bucket> --source-prefix input \
  --target-prefix out/whole --rule whole --block-size 16 --yes

python3 scripts/obs_image_desens.py process \
  --source-bucket <bucket> --source-prefix input \
  --target-prefix out/blur --rule blur --radius 10 --yes

python3 scripts/obs_image_desens.py process \
  --source-bucket <bucket> --source-prefix input \
  --target-prefix out/region --rule region --regions 40,20,180,90 --yes
```

**Expected**: `"status": "done"`, `"failed": 0`, target objects listed under the target prefix.

### Prove the image changed

```bash
hcloud obs cp obs://<bucket>/input/photo.png  /tmp/src.png
hcloud obs cp obs://<bucket>/out/whole/photo.png /tmp/dst.png
md5sum /tmp/src.png /tmp/dst.png
```

**Expected**: hashes differ; `dst.png` is visibly pixelated/blurred when opened.

## 3. Verify input safety

Run `process` with a prefix that has no images:

```bash
python3 scripts/obs_image_desens.py list --bucket <bucket> --prefix no-such-prefix
```

**Expected**: `"images": []`, no crash.

## 4. Verify error handling

- `--rule edges` → argparse rejects with an invalid-choice error (only the 5 supported rules).
- `--rule region --regions 0,0,9999,9999` on a small image → per-file `"status": "failed"`
  with `out of image bounds`, run marked `partial`.

## 5. Verify `setup-trigger` (optional, needs FunctionGraph permission)

```bash
python3 scripts/obs_image_desens.py setup-trigger \
  --function-name obs-desens-test --trigger-bucket <bucket> \
  --event-type ObjectCreated --rule whole --block-size 16 \
  --region cn-north-4 --project-id <project_id>
```

**Expected**: returns function URN and trigger id; the function appears in the FunctionGraph
console. Without `functiongraph:function:create` permission it fails with an explicit FSS.0403
message (this is expected in an IAM user without that permission).

> Mutating steps (uploads, function/trigger creation) must be confirmed by the user first.
