#!/bin/bash
set -euo pipefail

# ============================================================
# SessionStart Hook — Local Voice AI Agent
# Purpose: Install deps + inject SPOT.md as mandatory context
# ============================================================

# --- Install dependencies ---
if [ "${CLAUDE_CODE_REMOTE:-}" = "true" ]; then
  if command -v uv &> /dev/null; then
    uv sync 2>&1 || true
  else
    pip install -e . 2>&1 || true
  fi
fi

# --- Inject SPOT.md as session context ---
SPOT_FILE="${CLAUDE_PROJECT_DIR:-$(pwd)}/SPOT.md"

if [ -f "$SPOT_FILE" ]; then
  echo "================================================================"
  echo "  SPOT.md — Single Point of Truth (MANDATORY CONTEXT)"
  echo "================================================================"
  echo ""
  cat "$SPOT_FILE"
  echo ""
  echo "================================================================"
  echo "  SESSION START DIRECTIVES"
  echo "================================================================"
  echo ""
  echo "You MUST follow these rules for this session:"
  echo ""
  echo "1. ALIGNMENT: All work must align with SPOT.md requirements."
  echo "   Parse the requirement statuses above before starting any work."
  echo ""
  echo "2. TDD: Write tests FIRST, then implement to make them pass."
  echo ""
  echo "3. QA GATEWAY: Before every commit, run 'pytest tests/ -v'."
  echo "   All tests must pass. Self-correct failures — no skipping."
  echo ""
  echo "4. SPOT UPDATE: After every commit, update SPOT.md:"
  echo "   - Set requirement status to DONE/IN-PROGRESS as appropriate"
  echo "   - Add a row to the Revision Log with date, commit hash, changes"
  echo ""
  echo "5. NO DRIFT: Do not omit, skip, or deviate from these directives."
  echo "================================================================"
else
  echo "WARNING: SPOT.md not found at $SPOT_FILE"
  echo "The Single Point of Truth document is missing."
  echo "Create SPOT.md before proceeding with any implementation work."
fi
