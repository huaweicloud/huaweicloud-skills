# Related Commands

Commands not already covered in SKILL.md's 核心命令 table.

## OpenClaw Sandbox Restart (Apply Template Changes)

`stop + start` recreates the bwrap process, re-running `start.sh` with template changes:

```bash
BASE=http://127.0.0.1:8090/api/v1
curl -s -X POST $BASE/envs/openclaw/stop
# Wait for stopped, then:
curl -s -X POST $BASE/envs/openclaw/start
# Poll until running:
for i in $(seq 1 60); do
  st=$(curl -s $BASE/envs/openclaw | jq -r .state)
  [ "$st" = "running" ] && break; [ "$st" = "error" ] && break
  sleep 2
done
```

Full rebuild fallback (if `stop + start` fails):

```bash
curl -s -X POST $BASE/envs/openclaw/stop
curl -s -X DELETE $BASE/envs/openclaw
curl -s -X POST $BASE/envs -H 'Content-Type: application/json' -d '{"template":"openclaw"}'
curl -s -X POST $BASE/envs/openclaw/deploy
# Poll until running (same loop as above)
```

## OpenClaw Live Config Verification (from outside bwrap)

```bash
gw_pid=$(pgrep -f "openclaw-gateway" | head -1)
tr '\0' '\n' < /proc/$gw_pid/environ | grep OPENVIKING
# Expected: OPENVIKING_BASE_URL=http://127.0.0.1:1933
```

Or use: `scripts/integrate.sh --agent openclaw --dry-run`

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OV_ENDPOINT` | `http://127.0.0.1:1933` | OpenViking server endpoint |
| `OV_LANG` | (unset → `zh`) | Override i18n language (`zh`/`en`) |
