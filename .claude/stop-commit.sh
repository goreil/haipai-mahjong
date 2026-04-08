#!/bin/bash
# Stop hook: commit and push all changed tracked files when Claude finishes
set -e

cd /opt/haipai

# Check for any staged or unstaged changes to tracked files
if git diff --quiet HEAD 2>/dev/null && git diff --cached --quiet 2>/dev/null; then
  # Check for new untracked files in the repo (not .claude/, not data files)
  NEW=$(git ls-files --others --exclude-standard -- '*.py' '*.js' '*.css' '*.html' '*.md' '*.yml' '*.yaml' '*.json' '*.sh' 2>/dev/null | head -1)
  if [ -z "$NEW" ]; then
    exit 0
  fi
fi

# Stage all changes to known file types
git add -u
git ls-files --others --exclude-standard -- '*.py' '*.js' '*.css' '*.html' '*.md' '*.yml' '*.yaml' '*.sh' | xargs -r git add

# Don't commit if nothing staged
if git diff --cached --quiet 2>/dev/null; then
  exit 0
fi

# Build commit message from changed files
FILES=$(git diff --cached --name-only | head -10)
COUNT=$(git diff --cached --name-only | wc -l)
SUMMARY=$(echo "$FILES" | head -3 | tr '\n' ', ' | sed 's/,$//')
if [ "$COUNT" -gt 3 ]; then
  SUMMARY="$SUMMARY (+$((COUNT - 3)) more)"
fi

git commit -m "Auto: update $SUMMARY

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>" --no-verify 2>/dev/null || exit 0

git push origin main 2>/dev/null || true
