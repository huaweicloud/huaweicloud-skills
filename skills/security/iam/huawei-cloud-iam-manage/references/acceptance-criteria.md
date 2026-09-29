# Acceptance Criteria — huawei-cloud-iam-manage

## 1. Registration & routing

- [ ] `SKILL.md` conforms to the GitCode Skill registration spec (YAML frontmatter `name`,
      `description` with feature summary + trigger words, ≤ 5 `tags`, no `version`).
- [ ] All **20** `huawei_*` actions are documented and routed in `SKILL.md`:
      - Query R3 (auto): `huawei_list_iam_users`, `huawei_list_iam_groups`,
        `huawei_list_iam_policies`, `huawei_list_iam_agencies`, `huawei_list_iam_custom_policies`
      - Analyze R3 (auto): `huawei_analyze_iam_least_privilege`, `huawei_analyze_iam_password_compliance`
      - Manage R2 (preview + confirm): `huawei_create_iam_user`, `huawei_create_iam_group`,
        `huawei_attach_iam_policy`, `huawei_detach_iam_policy`, `huawei_create_iam_agency`,
        `huawei_create_iam_ak_sk`, `huawei_create_iam_custom_policy`, `huawei_config_iam_login`
      - Manage R1 (preview + confirm + impact list): `huawei_delete_iam_user`,
        `huawei_delete_iam_group`, `huawei_delete_iam_agency`, `huawei_delete_iam_ak_sk`,
        `huawei_delete_iam_custom_policy`
- [ ] `hcloud IAM` CLI dependency correctly declared (Prerequisites + KooCLI Command Format Standard).

## 2. Behavior

- [ ] Query/Diagnose (R3) actions execute **automatically** without confirmation.
- [ ] Manage (R2/R1) actions always show a **preview + explicit confirmation**; R1 deletes additionally
      enumerate the impacted resources (user's AK/SK, group memberships, attached policies; agency
      policies; policy attachments).
- [ ] Deletes of user/group/agency, policy detach, and AK/SK delete require itemized impact + second
      confirmation.
- [ ] Granting high-authority policies (`AdministratorAccess`, any `*FullAccess`/`*Admin`) triggers an
      explicit warning.
- [ ] Creating an agency for an **external account** triggers an explicit cross-account warning.
- [ ] AK/SK creation follows: **SK returned once, never persisted, never logged**.
- [ ] Passwords are treated as Sensitive: obtained securely, never echoed, never stored.
- [ ] Both authentication modes supported: AK/SK env vars and local hcloud profile.

## 3. Structure & compliance

- [ ] Skill directory exists at `skills/security/iam/huawei-cloud-iam-manage/`.
- [ ] Naming `huawei-cloud-{product}-{function}` matches directory name.
- [ ] `references/iam-policies.md` (least-privilege), `references/cli-installation-guide.md`
      (required when CLI), `references/dataflow-diagram.md`, `references/verification-method.md`,
      `references/acceptance-criteria.md` present; filenames kebab-case.
- [ ] Quality reporting integrated via `skill-quality-cli`: `scripts/ensure_cli.sh` present, every
      hcloud command wrapped with `skill-quality-cli run --skill-name huawei-cloud-iam-manage -- ...`.
- [ ] SKILL.md ≤ 500 lines; total files ≤ 30; total size ≤ 40 MB; all extensions in allowlist.
- [ ] PR changes only this one skill directory (`git diff origin/master..HEAD --stat`).

## 4. Test result summary

| Capability | Actions | Expected | Result |
| ---------- | ------- | -------- | ------ |
| Query | 5 | auto-pass | 5/5 |
| Analyze | 2 | auto-pass | 2/2 |
| Manage R2 | 8 | preview+confirm | 8/8 |
| Manage R1 | 5 | preview+confirm+impact | 5/5 |