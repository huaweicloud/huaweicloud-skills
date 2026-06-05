#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INDEX_FILE="$SCRIPT_DIR/../references/index.json"
CN_EN_FILE="$SCRIPT_DIR/../references/cn-en-map.json"

KEYWORD="${1:-}"
CATEGORY="${2:-}"

if [ ! -f "$INDEX_FILE" ]; then
    echo "Error: index.json not found at $INDEX_FILE" >&2; exit 1
fi

if [ -z "$KEYWORD" ] && [ -z "$CATEGORY" ]; then
    echo "Usage: $0 <keyword> [category]"
    echo "Categories: $(jq -r '.categories | join(", ")' "$INDEX_FILE")"
    exit 1
fi

KEYWORDS=()
if [ -n "$KEYWORD" ] && [ -f "$CN_EN_FILE" ]; then
    IFS=' ,' read -ra PARTS <<< "$KEYWORD"
    for p in "${PARTS[@]}"; do
        KEYWORDS+=("$p")
        while IFS=: read -r cn en; do
            cn=$(echo "$cn" | tr -d '"'); en=$(echo "$en" | tr -d '" ,')
            if [ "$cn" = "$p" ]; then KEYWORDS+=("$en"); fi
            if [ "$en" = "$(echo "$p" | tr '[:upper:]' '[:lower:]')" ]; then KEYWORDS+=("$cn"); fi
        done < <(jq -r 'to_entries[] | "\(.key):\(.value)"' "$CN_EN_FILE")
    done
elif [ -n "$KEYWORD" ]; then
    IFS=' ,' read -ra PARTS <<< "$KEYWORD"
    KEYWORDS=("${PARTS[@]}")
fi

KW_JSON=$(printf '%s\n' "${KEYWORDS[@]}" | jq -R . | jq -s .)

QUERY=$(jq -r --argjson kws "$KW_JSON" --arg cat "$CATEGORY" '
.skills | map(
  select(.category == $cat or $cat == "") |
  . as $s |
  ($kws | map(
    . as $kw | $s |
    (if .name | test($kw; "i") then 10 else 0 end) +
    (if .triggers | any(test($kw; "i")) then 8 else 0 end) +
    (if .description | test($kw; "i") then 5 else 0 end) +
    (if .service | test($kw; "i") then 3 else 0 end)
  ) | add // 0) as $score |
  select($score > 0 or ($kws | length) == 0) |
  {
    name, category, service,
    description: (if (.description | length) > 150 then .description[:150] + "..." else .description end),
    triggers: (.triggers[:5]),
    score: (if ($kws | length) == 0 then 1 else $score end)
  }
) | sort_by(-.score)
' "$INDEX_FILE")

TOTAL=$(echo "$QUERY" | jq 'length')

if [ "$TOTAL" -eq 0 ]; then
    echo "No results for keyword='$KEYWORD' category='$CATEGORY'"
    echo ""
    echo "Fallback suggestions:"
    echo "  1. Try broader or alternative keywords"
    echo "  2. Remove category filter"
    echo "  3. Switch CN<->EN (e.g., 'obs' <-> 'object storage')"
    echo "  4. List all: $0 '' 'computing'"
    exit 0
fi

echo "Found $TOTAL skill(s) for keyword='$KEYWORD' category='$CATEGORY':"
echo ""
echo "$QUERY" | jq -r '.[] | "  [\(.score)pts] \(.name) (\(.category)/\(.service))\n    \(.description)\n    triggers: \(.triggers | join(", "))\n"'