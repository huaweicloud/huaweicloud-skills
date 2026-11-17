# Verification Method

How to verify the vod-collector skill end-to-end after any change.
All script invocations below use the mandatory quality wrapper
(`skill-quality-cli run --skill-name huawei-cloud-vod-collector -- `).

## 1. Capture chain (Phase 1)

```bash
skill-quality-cli run --skill-name huawei-cloud-vod-collector -- \
  python <SKILL_DIR>/scripts/md_io.py write-feedback --output .vod/feedbacks/
skill-quality-cli run --skill-name huawei-cloud-vod-collector -- \
  python <SKILL_DIR>/scripts/vod_sanitize.py file --path <file>
```

Expected:
- `VOD-YYYYMMDD-NNNN.md` is created under `.vod/feedbacks/`.
- Identical `session_id + command + error_type` within the dedup window
  increments `recurrence_count` instead of writing a new file.
- Secrets are redacted by `write-feedback`.

## 2. Token safety (auth.toml)

- `_read_atomgit_token` must tighten the token file to mode `0600` **before**
  reading it, and must return `None` (refuse to read) when the file mode cannot
  be tightened.
- A missing/expired token must result in `"need_login": true` from `deliver`,
  not a crash.

## 3. Product-name extraction

Given a feedback whose `error_message` contains a date (`2024-12-31`), a UUID,
a version-like token (`v1-2-3`) or a numeric request id (`req-123456`),
`_infer_product_name` must NOT return those as the product name — it returns a
plausible alpha-led product token or `""`.

## 4. Delivery chain (Phase 3)

```bash
skill-quality-cli run --skill-name huawei-cloud-vod-collector -- \
  python <SKILL_DIR>/scripts/vod_deliver.py deliver \
  --feedback-id <id> --feedbacks-dir .vod/feedbacks
skill-quality-cli run --skill-name huawei-cloud-vod-collector -- \
  python <SKILL_DIR>/scripts/vod_deliver.py update-status \
  --feedback-id <id> --status delivered --feedbacks-dir .vod/feedbacks
```

Expected:
- Issue is created at `delivery.channels.gitcode.repo_url` (read only from
  `assets/config.yaml`, never from `git remote`).
- Updates are in-place; IDs are immutable; status machine
  `open → delivered → promoted → resolved` or `open → delivered → discarded`
  (the `delivered` state is written by `update-status --status delivered`,
  so it appears before any promotion/discard transition).

## 5. Cross-session dedup and notifications

```bash
skill-quality-cli run --skill-name huawei-cloud-vod-collector -- \
  python <SKILL_DIR>/scripts/vod_deliver.py dedup-scan \
  --feedbacks-dir .vod/feedbacks --feedback-id <id> --lookback 10 --json
skill-quality-cli run --skill-name huawei-cloud-vod-collector -- \
  python <SKILL_DIR>/scripts/vod_deliver.py notify \
  --feedbacks-dir .vod/feedbacks --feedback-id <id> --channel auto --json
```

Expected:
- `dedup-scan` reports `{"success": true, "scanned": N, "target": {...},
  "candidates": [...], "should_deliver": ...}`; candidates come from a different
  `session_id` with a matching command / error_type / normalized signature.
- `deliver` without `--force` returns
  `{"success": false, "error": "duplicate_suspected", "duplicate_of": "<ID>"}`
  when a strong candidate exists; `--force` / `--skip-dedup` bypass the gate.
- `notify` on a directory with no pending feedback returns
  `{"success": true, "pending": 0, "sent": []}` and does **not** resolve the
  AtomGit token or trigger login.
- `notify` with pending feedback sends via `delivery.channels.notification`
  (webhook HTTP POST JSON / email SMTP with TLS) and honors `retry_policy`.

## 6. Installer

- `ensure_cli.sh`: run twice — the second run must exit without re-downloading
  (idempotent: it short-circuits as soon as an executable `skill-quality-cli`
  exists in `$SKILL_QUALITY_CLI_DIR`, default `${HOME}/.local/bin`).
- `tests/test_ensure_cli.py` drives the real, unmodified script offline (stubbed
  manifest endpoint) and covers: idempotent short-circuit, missing sha256,
  sha256 mismatch, non-OBS `bootstrap_url`, and "second run does not download".
- If installation fails (network / manifest / checksum), `ensure_cli.sh` prints a
  warning and exits 0, so the skill keeps running in degraded mode.
- UTF-8: `scripts/hcloud-run.sh` exports `PYTHONUTF8=1` and
  `PYTHONIOENCODING=utf-8` before invoking `skill-quality-cli` / `hcloud`, so
  `hcloud` calls routed through it do not raise `UnicodeDecodeError` for Chinese
  output on a Chinese Windows host. `ensure_cli.sh` does **not** set these
  variables, and direct `skill-quality-cli run -- ...` invocations (as listed in
  `SKILL.md` Core Commands) do not inherit them — on a Chinese Windows host,
  export both variables in the calling shell before using direct `run` calls.

## 7. Syntax gates

```bash
bash -n <SKILL_DIR>/scripts/*.sh
python3 -m py_compile <SKILL_DIR>/scripts/*.py
```