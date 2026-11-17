#!/usr/bin/env bash
# Fails (exit 1) if anything that must never be published is found.
# Run before every commit:  bash scripts/scrub_check.sh
cd "$(dirname "$0")/.." || exit 2
fail=0
SELF="scripts/scrub_check.sh"
hit() { echo "SCRUB HIT [$1]: $2"; fail=1; }

# 1. forbidden files
while IFS= read -r f; do hit "forbidden file" "$f"; done < <(find . -path ./.git -prune -o -type f \( -name '.env' -o -name '.env.*' -o -name '*.pem' -o -name '*.key' -o -name '*keys*' -o -name 'id_rsa*' -o -name '*.p12' -o -name 'credentials*' -o -name '*.pkl' \) -print)

# 2. content patterns (extended regex, case-insensitive). Skips .git and this script.
scan() { # label regex
  out=$(grep -rInEi --exclude-dir=.git --exclude="$(basename "$SELF")" --exclude=.gitignore -e "$2" . 2>/dev/null)
  [ -n "$out" ] && { echo "$out" | while IFS= read -r l; do hit "$1" "$l"; done; fail=1; }
}
scan "private key"      '-----BEGIN [A-Z ]*PRIVATE KEY'
scan "key/token assignment" '(api[_-]?key|api[_-]?secret|secret[_-]?key|access[_-]?token|auth[_-]?token|bearer|passwd|password|private[_-]?key)["'"'"' ]*[:=]["'"'"' ]*[A-Za-z0-9/+_.=-]{12,}'
scan "known token shapes" '(sk-[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|xox[abprs]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{30,})'
scan "email address"    '[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}'
scan "uuid / account or order id" '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
scan "long hex (hash/key)"  '\b[0-9a-f]{32,}\b'
scan "account/order id field" '(account[_ -]?id|member[_ -]?id|user[_ -]?id|client[_ -]?order[_ -]?id|order[_ -]?id|wallet[_ -]?address|funder)["'"'"' ]*[:=]'
scan "live order settings" '(live[_-]?mode|LIVE_TRADING|ENABLE_LIVE|executor[_-]?config|max[_-]?order[_-]?size)["'"'"' ]*[:=]'
# Private banned names (people, emails, hosts) live in an untracked local file,
# one regex per line, so the list itself is never published. See .gitignore.
LOCAL_TERMS="scripts/.scrub_local_terms"
if [ -f "$LOCAL_TERMS" ]; then
  while IFS= read -r term; do [ -n "$term" ] && scan "forbidden name" "$term"; done < "$LOCAL_TERMS"
fi
scan ".env reference"   '(^|[^A-Za-z])\.env([^A-Za-z]|$)'

if [ "$fail" -ne 0 ]; then echo "scrub_check: FAILED. Fix the hits above before committing."; exit 1; fi
echo "scrub_check: clean."
