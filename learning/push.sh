#!/usr/bin/env bash
# Commit, tag and push the learning track. Run on your Mac:  make learn-push
# Each nightly session appends a line "session-NN|Session NN: <title>" to learning/.pending
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
PENDING=learning/.pending
if [ -s "$PENDING" ]; then
  tags=$(cut -d'|' -f1 "$PENDING")
  titles=$(cut -d'|' -f2 "$PENDING")
  first_title=$(echo "$titles" | head -1)
  git add learning docker-compose.healthcare.yml Makefile .gitignore
  if [ "$(echo "$tags" | wc -l)" -gt 1 ]; then
    git commit -m "Learning: $(echo "$tags" | tr '\n' ' ')" -m "$titles"
  else
    git commit -m "$first_title"
  fi
  paste -d'|' <(echo "$tags") <(echo "$titles") | while IFS='|' read -r t m; do
    git tag -a "$t" -m "$m" 2>/dev/null || echo "tag $t already exists, skipped"
  done
  rm -f "$PENDING"
else
  echo "No new sessions pending; pushing anything already committed."
fi
git push origin HEAD --follow-tags
