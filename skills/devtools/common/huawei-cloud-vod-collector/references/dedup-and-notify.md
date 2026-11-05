# Cross-session Dedup & Notification Channels

Implementation reference for the two `vod_deliver.py` subcommands that back
Phase 1.2 (cross-session dedup) and the notification channels declared in
`assets/config.yaml`.

Every command below must be wrapped with the mandatory quality wrapper:
`skill-quality-cli run --skill-name huawei-cloud-vod-collector -- <command>`.

## 1. `dedup-scan` — cross-session duplicate scan

Purpose: before Phase 3 delivery, produce the candidate list of earlier
feedbacks that may describe the same problem, so the Agent (LLM) can make the
final semantic call.

Synopsis:

```bash
skill-quality-cli run --skill-name huawei-cloud-vod-collector -- python <SKILL_DIR>/scripts/vod_deliver.py dedup-scan --feedbacks-dir <dir> [--feedback-id <ID>] [--lookback 10] [--json]
```

- `--feedbacks-dir <dir>` (required): path to `.vod/feedbacks/`.
- `--feedback-id <ID>` (optional): target feedback compared against the other entries.
- `--lookback <N>` (optional, default `10`): scan the N most recently modified
  feedbacks, newest first (by mtime).
- `--json`: reserved for compatibility only — the code never reads this flag;
  `dedup-scan` **always** prints the JSON result shown below.

Output — the top-level fields are `success, scanned, lookback, target, candidates,
strong_duplicates, should_deliver, llm_prompt`; `target` and each entry of
`candidates` have the shape below:

```json
{
  "success": true,
  "scanned": 10,
  "lookback": 10,
  "target": {
    "id": "...",
    "file": "...",
    "session_id": "...",
    "feedback_type": "...",
    "error_type": "...",
    "status": "...",
    "delivery_status": "pending",
    "recurrence_count": 1,
    "title": "...",
    "signature": "..."
  },
  "candidates": [
    {
      "id": "...",
      "file": "...",
      "session_id": "...",
      "feedback_type": "...",
      "error_type": "...",
      "status": "...",
      "delivery_status": "delivered",
      "recurrence_count": 1,
      "title": "...",
      "signature": "...",
      "signature_match": true,
      "score": 0.9,
      "reason": "...",
      "is_strong_duplicate": true
    }
  ],
  "strong_duplicates": ["..."],
  "should_deliver": false,
  "llm_prompt": "..."
}
```

There is **no `command` field** — `FeedbackRecord` has none, and neither `target`
nor `candidates` emits one. When no `--feedback-id` is given, recent pairs are
compared and each candidate carries an extra `duplicate_of` field naming the
other entry.

`strong_duplicates` lists the ids whose peer is already closed out: the peer's
`delivery_status == "delivered"`, or the peer's `status` is `promoted` /
`resolved` (the `FeedbackStatus` enum has **no** `delivered` value — `delivered`
exists only as a delivery status). `llm_prompt` is a ready-made prompt the Agent
can use for the semantic judgment.

Detection rules:

- A cross-session duplicate candidate = a **different `session_id`** and either
  an identical **normalized error-text signature** (`signature_match == true`)
  **or** a `score` at/above the minimum (`>= 0.6`); entries with a non-matching
  signature *and* a lower score are dropped.
- The signature is `error_type` plus the error text with UUIDs, hex ids, numbers
  and paths stripped and lowercased.
- `score` is the weighted similarity: equal `error_type` contributes `0.4`,
  plus up to `0.6` × the normalized-text token overlap.
- `reason` is the human-readable explanation of that score.
- `signature_match` reports whether the signatures are identical;
  `is_strong_duplicate` marks the subset that can block delivery (see below);
  `should_deliver` summarizes whether the target still looks deliverable.

Agent step (Phase 3, before delivery):

1. Run `dedup-scan` for the target feedback.
2. If `candidates` is non-empty, judge semantically whether any entry is the
   same problem. On a match, do **not** deliver — merge into the existing
   feedback (for example bump `recurrence_count` / update its status) instead.
3. Only when no candidate is a true duplicate, proceed to `deliver`.

`deliver` enforces the machine-checkable subset of this gate itself: unless
`--force` is passed (and when the scan is not skipped with `--skip-dedup`), a
strong candidate — `signature_match == true`, a different session, and a peer
that is already closed out (peer `delivery_status == "delivered"`, or peer
`status` in `promoted` / `resolved`) — makes `deliver` return

```json
{"success": false, "error": "duplicate_suspected", "duplicate_of": "<ID>", "candidates": [ ... ]}
```

and no issue is created. The gate only blocks on **signature-matching** strong
duplicates; score-only candidates (`signature_match == false`) are reported for
the Agent's judgment but never block delivery. Pass `--force` only after the LLM
has judged that the candidate is not a real duplicate; `--skip-dedup` skips the
duplicate gate entirely (for example when re-delivering a known-good feedback).

`--force` is also what re-delivers a feedback whose `delivery_status` is already
`delivered`: without it the command returns
`{"success": false, "error": "already_delivered", ...}` before any credential is
resolved.

## 2. `notify` — webhook / email notification

Synopsis:

```bash
skill-quality-cli run --skill-name huawei-cloud-vod-collector -- python <SKILL_DIR>/scripts/vod_deliver.py notify --feedbacks-dir <dir> [--feedback-id <ID>] [--channel webhook|email|auto] [--json]
```

- `--feedbacks-dir <dir>` (required): path to `.vod/feedbacks/`.
- `--feedback-id <ID>` (optional): notify only about this feedback.
- `--channel webhook|email|auto` (optional, default `auto`): `auto` uses
  `delivery.channels.notification.type` from `assets/config.yaml`.
- `--dry-run` (optional): list the payloads that would be sent without sending
  anything (`{"dry_run": true, "items": [...]}`).
- `--json`: reserved for compatibility only — the code never reads this flag;
  `notify` **always** prints the JSON result.

Pending means: the record is not `discarded`, its `delivery_status` is not
`delivered`, and it has no `notified_at` entry yet. A successful send records
`- **notified_at**: <ISO timestamp>` under `## Delivery`, which makes repeat
runs idempotent.

Ordering guarantee: pending feedbacks are checked **first**. When there is
nothing pending the command returns `{"success": true, "pending": 0, "sent": []}`
**without resolving the AtomGit token and without triggering the login flow**
(the behavior requested by #114 问题 5). Notification channels do not need
GitCode/AtomGit credentials at all.

With pending feedbacks the provider is taken from
`delivery.channels.notification` in `assets/config.yaml`:

- `webhook` — HTTP `POST` with a JSON body to `webhook.url`, sending the
  configured `webhook.headers`.
- `email` — SMTP over TLS to `email.smtp_host`:`email.smtp_port` with
  `email.recipients`.
- `retry_policy.max_retries` / `backoff_base_sec` / `backoff_max_sec` control
  retries with exponential backoff.

The result reports `pending` (count), `sent` (ids successfully notified),
`failed` (ids that failed) and per-item `results`. When
`delivery.channels.notification.enabled` is `false` and something is pending,
the command returns `{"success": false, "error": "Notification channels disabled (...)"}`.

### Configuration (`assets/config.yaml`)

```yaml
delivery:
  channels:
    notification:
      enabled: false          # ships disabled by default
      type: "webhook"         # webhook | email (used by --channel auto)
      webhook:
        url: ""
        headers: {}
      email:
        smtp_host: ""
        smtp_port: 587
        recipients: []
      retry_policy:
        max_retries: 3
        backoff_base_sec: 2
        backoff_max_sec: 30
```

The channel must be explicitly enabled and configured before use. Keep
`webhook.url`, `webhook.headers` and SMTP settings in `assets/config.yaml`
only — never inside feedback files that are stored under `.vod/feedbacks/`.

GitCode/AtomGit credentials are a separate concern (see `SKILL.md` → Token
Configuration). Note that the `VOD_ATOMGIT_TOKEN` environment variable avoids
persisting the token, but on POSIX a process running under the **same uid**
(including child processes) can still read it from `/proc/<pid>/environ`; for
stronger isolation prefer a short-lived token.
