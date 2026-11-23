# Verification Method

## Specification Compliance Verification

```bash
bash scripts/validate-skill.sh -s {skill-path}
```

This script checks the skill against the Huawei Cloud Skill Specification:
- SKILL.md existence and frontmatter validity
- Required sections (Overview, Prerequisites, Workflow, Core Commands, Parameter Confirmation, Reference Documents)
- File count and size limits
- Credential hardcoding detection
- Quality-CLI integration
- File extension allowlist

## Functional Testing

```bash
bash scripts/test-cli-commands.sh -s {skill-path} -e sdk
```

This script executes test cases defined in `templates/test-vars.json`:
- SDK import verification
- Script syntax check
- Signed URL generation (requires valid AK/SK)
- Image processing URL generation

## Manual Verification

### 1. Verify OBS SDK Installation

```bash
python3 -c "from obs import ObsClient; print('OBS SDK available')"
```

### 2. Verify Credential Environment Variables

```bash
# Check that credentials are set (values masked)
env | grep -iE 'ACCESS_KEY|SECRET_KEY' | sed 's/=.*/=***/'
```

### 3. Verify Signed URL Generation

```bash
python3 scripts/generate_signed_url.py \
  --bucket-name "test-bucket" \
  --object-key "test.txt" \
  --method GET \
  --expires 3600 \
  --server "obs.cn-north-4.myhuaweicloud.com"
```

### 4. Verify Image Processing URL

```bash
python3 scripts/generate_signed_url.py \
  --bucket-name "test-bucket" \
  --object-key "photo.jpg" \
  --method GET \
  --expires 3600 \
  --server "obs.cn-north-4.myhuaweicloud.com" \
  --image-process "image/resize,w_100,h_200"
```

## Test Result Interpretation

| Result | Meaning |
|--------|---------|
| PASS | Test case executed successfully |
| FAIL | Test case failed — check error message |
| SKIP | Test case was skipped (e.g., missing credentials) |
