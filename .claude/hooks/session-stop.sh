#!/bin/bash
set -euo pipefail

# ============================================================
# Stop Hook — Local Voice AI Agent
# Purpose: Enforce SPOT update + QA checklist before session ends
# ============================================================

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
SPOT_FILE="$PROJECT_DIR/SPOT.md"

echo "================================================================"
echo "  SESSION END — MANDATORY CHECKLIST"
echo "================================================================"
echo ""

# --- Check 1: Are there uncommitted changes? ---
if cd "$PROJECT_DIR" && git diff --quiet && git diff --cached --quiet; then
  echo "[OK] No uncommitted changes."
else
  echo "[ACTION REQUIRED] You have uncommitted changes."
  echo "  Review, test, and commit before ending this session."
  echo ""
fi

# --- Check 2: Did tests pass? ---
if [ -d "$PROJECT_DIR/tests" ]; then
  echo "[REMINDER] Run 'pytest tests/ -v' and confirm all tests pass."
else
  echo "[INFO] No tests/ directory found yet."
fi
echo ""

# --- Check 3: Was SPOT.md updated? ---
if [ -f "$SPOT_FILE" ]; then
  LAST_COMMIT_MSG=$(cd "$PROJECT_DIR" && git log -1 --pretty=%s 2>/dev/null || echo "")
  SPOT_CHANGED=$(cd "$PROJECT_DIR" && git diff --name-only HEAD~1 HEAD 2>/dev/null | grep -c "SPOT.md" || echo "0")

  if [ "$SPOT_CHANGED" = "0" ]; then
    echo "[ACTION REQUIRED] SPOT.md was NOT updated in the last commit."
    echo "  You must update:"
    echo "  - Requirement statuses (TODO -> IN-PROGRESS -> DONE)"
    echo "  - Revision Log with date, commit hash, and summary of changes"
    echo ""
  else
    echo "[OK] SPOT.md was updated in the last commit."
  fi
else
  echo "[WARNING] SPOT.md not found."
fi

echo ""
echo "Do NOT end this session until all items above are resolved."
echo "================================================================"
