#!/bin/bash
#===============================================================================
# verify-skill-features.sh — Phase 0: Feature Verification
#
# Reads the target SKILL.md, extracts and lists all main features
# for user confirmation before proceeding with testing.
# Loops until user confirms features are correct.
#
# Usage: bash scripts/verify-skill-features.sh <skill-path>
#===============================================================================
set -euo pipefail

SKILL_PATH=""
SKILL_MD=""

usage() {
  echo "Usage: bash scripts/verify-skill-features.sh <skill-path>"
  echo "Reads SKILL.md and displays features for user confirmation."
  exit 1
}

[ $# -ge 1 ] || usage
SKILL_PATH="$1"
SKILL_MD="$SKILL_PATH/SKILL.md"

[ -f "$SKILL_MD" ] || { echo "[FAIL] SKILL.md not found at $SKILL_MD"; exit 1; }

#--- Extract frontmatter ---
extract_field() {
  local field="$1"
  sed -n "/^${field}:/{s/^${field}: *//;p;q}" "$SKILL_MD" 2>/dev/null || echo ""
}

#--- Extract description numbered points ---
extract_description_points() {
  sed -n '/^description:/,/^[a-zA-Z]/p' "$SKILL_MD" 2>/dev/null \
    | grep -oP '^\s*\d+\.\s*\K.*' | sed 's/^[[:space:]]*//' || true
}

#--- Extract triggers ---
extract_triggers() {
  local desc_block
  desc_block=$(sed -n '/^description:/,/^[^ ]/p' "$SKILL_MD" 2>/dev/null)
  echo "$desc_block" \
    | grep -oP '(Triggers include|触发包括|触发词):\s*\K.*' \
    | tr ',' '\n' | sed 's/^[[:space:]]*"//;s/"[[:space:]]*$//;s/^[[:space:]]*//;s/[[:space:]]*$//' \
    | grep -v '^$' || true
}

#--- Extract tags ---
extract_tags() {
  sed -n '/^tags:/{s/^tags: *\[//;s/\].*//;p;q}' "$SKILL_MD" 2>/dev/null \
    | tr ',' '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' || true
}

#--- Extract Core Commands ---
extract_core_commands() {
  local in_core=false
  while IFS= read -r line; do
    if echo "$line" | grep -qP '^##\s+(核心命令|Core Commands)'; then
      in_core=true; continue
    fi
    if $in_core && echo "$line" | grep -qP '^##\s+'; then
      break
    fi
    if $in_core && echo "$line" | grep -qP '^\|\s*`'; then
      local cmd=$(echo "$line" | grep -oP '`\K[^`]+' | head -1)
      local desc=$(echo "$line" | awk -F'|' '{print $3}' | xargs)
      local backend=$(echo "$line" | awk -F'|' '{print $4}' | xargs)
      if [ -n "$cmd" ]; then
        # Remove operation name for display (keep params)
        local op=$(echo "$cmd" | grep -oP '^[A-Za-z]+')
        local params=$(echo "$cmd" | grep -oP '\(.*\)' || echo "")
        echo "$op|$params|$backend|$desc"
      fi
    fi
  done < "$SKILL_MD"
}

#--- Extract workflow scenarios ---
extract_workflows() {
  local in_wf=false
  while IFS= read -r line; do
    if echo "$line" | grep -qP '^##\s+(工作流|Workflow|Scenario|场景)'; then
      in_wf=true; continue
    fi
    if $in_wf && echo "$line" | grep -qP '^##\s+'; then
      break
    fi
    if $in_wf && echo "$line" | grep -qP '^### '; then
      echo "$line" | sed 's/^### *//'
    fi
  done < "$SKILL_MD"
}

#--- Display feature summary ---
display_features() {
  local name desc_ver tags desc_points triggers commands workflows
  name=$(extract_field "name")
  desc_ver=$(extract_field "version")
  tags=$(extract_field "tags")

  echo ""
  echo "╔══════════════════════════════════════════════════════════════╗"
  echo "║              Skill Feature Verification                     ║"
  echo "╚══════════════════════════════════════════════════════════════╝"
  echo ""
  echo "  Skill:       $name"
  echo "  Version:     $desc_ver"
  echo "  Tags:        $tags"
  echo ""

  # Description points
  echo "  ┌─ Description ──────────────────────────────────────────────┐"
  local idx=0
  while IFS= read -r pt; do
    [ -z "$pt" ] && continue
    idx=$((idx + 1))
    printf "  │ %d. %s\n" "$idx" "$pt"
  done < <(extract_description_points)
  if [ "$idx" -eq 0 ]; then echo "  │ (none)"; fi
  echo "  └────────────────────────────────────────────────────────────┘"

  # Core Commands
  echo ""
  echo "  ┌─ Core Operations ──────────────────────────────────────────┐"
  local cmd_count=0
  while IFS='|' read -r op params backend desc; do
    [ -z "$op" ] && continue
    cmd_count=$((cmd_count + 1))
    printf "  │ %-2d %-25s %-10s %s\n" "$cmd_count" "${op}${params}" "[$backend]" "$desc"
  done < <(extract_core_commands)
  if [ "$cmd_count" -eq 0 ]; then echo "  │ (none — possibly non-CLI skill)"; fi
  echo "  └────────────────────────────────────────────────────────────┘"

  # Triggers
  echo ""
  echo "  ┌─ Triggers ─────────────────────────────────────────────────┐"
  local tg_count=0
  while IFS= read -r tg; do
    [ -z "$tg" ] && continue
    tg_count=$((tg_count + 1))
    printf "  │ %-2d %s\n" "$tg_count" "$tg"
  done < <(extract_triggers)
  if [ "$tg_count" -eq 0 ]; then echo "  │ (none declared)"; fi
  echo "  └────────────────────────────────────────────────────────────┘"

  # Workflow scenarios
  echo ""
  echo "  ┌─ Workflow Scenarios ───────────────────────────────────────┐"
  local wf_count=0
  while IFS= read -r wf; do
    [ -z "$wf" ] && continue
    wf_count=$((wf_count + 1))
    printf "  │ %-2d %s\n" "$wf_count" "$wf"
  done < <(extract_workflows)
  if [ "$wf_count" -eq 0 ]; then echo "  │ (none detected)"; fi
  echo "  └────────────────────────────────────────────────────────────┘"
  echo ""
}

#--- Main loop ---
while true; do
  display_features

  echo "  Does the above feature list look correct?"
  echo "  [y] Yes, proceed to testing"
  echo "  [n] No, re-read and show again"
  echo "  [q] Quit"
  echo ""
  echo "  Your choice (y/n/q): "
  if [ -t 0 ]; then
    read -r -p "  " choice
  else
    read -r choice
  fi

  case "$choice" in
    y|Y)
      echo ""
      # Export confirmed features to .skill-features.conf for downstream phases
      conf_file="$SKILL_PATH/.skill-features.conf"

      # Extract metadata at top level (not inside function)
      name=$(extract_field "name")
      desc_ver=$(extract_field "version")
      tags=$(extract_field "tags")

      # Collect description points
      desc_json=""
      first=true
      while IFS= read -r pt; do
        [ -z "$pt" ] && continue
        $first && desc_json="\"$pt\"" || desc_json="$desc_json, \"$pt\""
        first=false
      done < <(extract_description_points)
      [ -z "$desc_json" ] && desc_json="\"(none)\""

      # Collect core commands
      cmds_json=""
      first=true
      while IFS='|' read -r op params backend desc; do
        [ -z "$op" ] && continue
        entry="{\"op\":\"${op}\",\"params\":\"${params}\",\"backend\":\"${backend}\",\"desc\":\"${desc}\"}"
        $first && cmds_json="$entry" || cmds_json="$cmds_json, $entry"
        first=false
      done < <(extract_core_commands)
      [ -z "$cmds_json" ] && cmds_json="{\"op\":\"(none)\",\"params\":\"\",\"backend\":\"\",\"desc\":\"\"}"

      # Collect triggers
      triggers_json=""
      first=true
      while IFS= read -r tg; do
        [ -z "$tg" ] && continue
        $first && triggers_json="\"$tg\"" || triggers_json="$triggers_json, \"$tg\""
        first=false
      done < <(extract_triggers)
      [ -z "$triggers_json" ] && triggers_json="\"(none)\""

      # Collect workflows
      wf_json=""
      first=true
      while IFS= read -r wf; do
        [ -z "$wf" ] && continue
        $first && wf_json="\"$wf\"" || wf_json="$wf_json, \"$wf\""
        first=false
      done < <(extract_workflows)
      [ -z "$wf_json" ] && wf_json="\"(none)\""

      cat > "$conf_file" << EOF
{
  "skill": "$(echo "$name" | sed 's/"/\\"/g')",
  "version": "$(echo "$desc_ver" | sed 's/"/\\"/g')",
  "tags": "$(echo "$tags" | sed 's/"/\\"/g')",
  "description_points": [$desc_json],
  "core_commands": [$cmds_json],
  "triggers": [$triggers_json],
  "workflows": [$wf_json]
}
EOF

      echo "[PASS] Features verified by user — saved to $conf_file"
      exit 0
      ;;
    n|N)
      echo ""
      echo "[INFO] Re-reading skill features..."
      echo ""
      continue
      ;;
    q|Q)
      echo ""
      echo "[INFO] Verification aborted by user"
      exit 1
      ;;
    *)
      echo "  Invalid choice, please enter y, n, or q"
      ;;
  esac
done
