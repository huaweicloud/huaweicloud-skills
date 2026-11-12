# Workflow

1. **Clarify the intent** — read (inventory, detail, nodes, channels, members,
   quotas, status, operation records, alerts, metrics) or write (certificates,
   channels, peers/orgs, instance lifecycle, invitations).
2. **Inspect first when unsure** — use `list`, `detail`, `channels` or `members`
   to confirm ids and current state before a write.
3. **Choose the region** — default `cn-north-4`; confirm when the tenant's
   instances live elsewhere.
4. **Run the matching subcommand.**
5. **For writes, review the impact preview** and get explicit approval before
   adding `--confirm`; irreversible actions require a user instruction naming
   the exact target.
6. **Report the result** — the script polls ListOpRecord (default 60 s) and
   prints the final status. Do not report success before it is `finished`.
7. **Never retry an irreversible delete automatically**; ask the user instead.