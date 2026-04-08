#!/bin/bash
# Auto-commit hook: stages changed file, commits, and pushes after Edit/Write
set -e

cd /opt/haipai

# Extract file path from stdin JSON
FILE=$(jq -r '.tool_input.file_path // .tool_response.filePath // empty')
if [ -z "$FILE" ]; then
  exit 0
fi

# Skip non-repo files (memory, settings, etc.)
case "$FILE" in
  /root/*|/tmp/*) exit 0 ;;
esac

# Only commit if the file is actually changed in git
if git diff --quiet -- "$FILE" 2>/dev/null && git diff --cached --quiet -- "$FILE" 2>/dev/null; then
  # Check if it's a new untracked file
  if ! git ls-files --others --exclude-standard | grep -qF "$(basename "$FILE")"; then
    exit 0
  fi
fi

# Stage and commit
BASENAME=$(basename "$FILE")
git add "$FILE"
git commit -m "Auto: update $BASENAME

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>" --no-verify 2>/dev/null || exit 0

# Push in background so it doesn't slow things down
git push origin main 2>/dev/null &
