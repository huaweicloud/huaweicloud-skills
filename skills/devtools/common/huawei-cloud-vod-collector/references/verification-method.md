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

## 6. Installers

- `ensure_cli.sh`: run twice — the second run must exit without re-downloading
  (idempotent even when `${HOME}/.local/bin` is not in `PATH`).
- `ensure_cli.sh --help` / `install_cli.sh --help` print usage and exit 0.
- `install_cli.sh` fails closed when the manifest lacks `sha256` or the checksum
  does not match (no silent bypass).
- `ensure_cli.ps1` (Windows) / `install_cli.py` (#929): `install_cli.py --dry-run`
  prints the install plan without writing; on a platform without a native package it
  installs the `python-fallback` launchers and `skill-quality-cli version` succeeds;
  a manifest without `sha256` or a mismatching checksum refuses to install.
  Exit-code contract: `ensure_cli.sh` / `ensure_cli.ps1` degrade to a warning + exit 0
  when installation is impossible (the skill keeps running); `install_cli.py` is the
  low-level installer and always exits non-zero on failure, leaving no partial artifacts.
- The UTF-8 requirement holds: after `ensure_cli.sh` / `ensure_cli.ps1` /
  `hcloud-run.sh` set `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8`, wrapped commands
  that print Chinese do not raise `UnicodeDecodeError` on a Chinese Windows host.
- `vod_install.sh --repo-dir <unsafe-value>` rejects the argument; unsupported
  OS/arch is detected before any clone happens.

## 7. Syntax gates

```bash
bash -n <SKILL_DIR>/scripts/*.sh
python3 -m py_compile <SKILL_DIR>/scripts/*.py
```