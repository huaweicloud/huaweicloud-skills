# Custom Operator Workflow 算子执行工作流

Index of the custom-operator onboarding guide. This file used to hold all ~2750 lines;
it is now split by topic so each part can be read on its own. **Open only the part the
current step needs** — do not read the whole guide.

## Contents 目录

| Part | File | What it covers | Read it when |
|---|---|---|---|
| Prerequisites + Phase 0/1 | [onboarding-phase-0-1.md](onboarding-phase-0-1.md) | Prerequisite checks, deploy-mode question, asset detection, code adaptation | Starting an onboarding; adapting the operator code |
| Phase 2/3 | [onboarding-phase-2-3.md](onboarding-phase-2-3.md) | Image build & push, asset registration (image + algorithm) | 把代码打进镜像; registering assets |
| Phase 4 | [onboarding-phase-4.md](onboarding-phase-4.md) | Dataset source, task config assembly, create-task, verification, common issues | Submitting and verifying a runtime task |
| Post-onboarding | [onboarding-post.md](onboarding-post.md) | Resume & recovery, interaction rules, full example, post-onboarding, cleanup | A phase failed, or the onboarding finished |
| Phase boundaries | [phase-boundaries.md](phase-boundaries.md) | Boundary matrix, global ask-user checklist, missing-info table, mutation confirmation table | Deciding whether to ask the customer |
| Cleanup & report | [garbage-cleanup-report.md](garbage-cleanup-report.md) | Server-side junk cleanup, platform cleanup (ask-first), verification report | After a run, housekeeping |
| Progress feedback | [progress-feedback.md](progress-feedback.md) | Long-wait checklist, create-then-poll, docker push progress | A step will take many minutes |
| Failure analysis | [failure-analysis-guide.md](failure-analysis-guide.md) | Error pattern matrix (P0-P3), analysis algorithm, common failures | A task FAILED |
| OBS upload | [obs-upload-guide.md](obs-upload-guide.md) | Concurrent sharded upload, verification, boundary cases | Uploading a large dataset to OBS |

## Reading order for a first-time onboarding

1. [onboarding-phase-0-1.md](onboarding-phase-0-1.md) — prerequisites, then the deploy-mode question
2. Phase 2/3 **or** skip Phase 2 (代码放 OBS) — see the branch table in
   [onboarding-phase-2-3.md](onboarding-phase-2-3.md)
3. [onboarding-phase-4.md](onboarding-phase-4.md) — submit and verify
4. [onboarding-post.md](onboarding-post.md) — cleanup and report

Read [phase-boundaries.md](phase-boundaries.md) only when a decision point is unclear, and
[failure-analysis-guide.md](failure-analysis-guide.md) only after a task actually fails.

## Scope reminder

An explicit single-point request ("register this script as an operator") needs no discovery:
go straight to the deploy-mode question in
[onboarding-phase-0-1.md](onboarding-phase-0-1.md). Do not survey same-name operators,
reusable images, or what preset operators cover.
