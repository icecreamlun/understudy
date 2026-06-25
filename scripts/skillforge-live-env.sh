#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

export PATH="$HOME/.local/bin:$PATH"
export OPENCLAW_CONFIG_PATH="${OPENCLAW_CONFIG_PATH:-$ROOT/config/openclaw.json}"
export OPENCLAW_HOME="${OPENCLAW_HOME:-$ROOT/.runtime/openclaw-home}"
export OPENCLAW_STATE_DIR="${OPENCLAW_STATE_DIR:-$ROOT/.runtime/openclaw-state}"
export SKILLFORGE_OPENCLAW_COMMAND="${SKILLFORGE_OPENCLAW_COMMAND:-$ROOT/scripts/openclaw-email-extract.py}"
export SKILLFORGE_OPENCLAW_AGENT_TIMEOUT="${SKILLFORGE_OPENCLAW_AGENT_TIMEOUT:-180}"
export SKILLFORGE_OPENCLAW_WRAPPER_TIMEOUT="${SKILLFORGE_OPENCLAW_WRAPPER_TIMEOUT:-240}"

export SKILLFORGE_IMAP_HOST="${SKILLFORGE_IMAP_HOST:-imap.gmail.com}"
export SKILLFORGE_IMAP_PORT="${SKILLFORGE_IMAP_PORT:-993}"
export SKILLFORGE_IMAP_MAILBOX="${SKILLFORGE_IMAP_MAILBOX:-INBOX}"

if [[ -z "${SKILLFORGE_IMAP_USERNAME:-}" ]]; then
  echo "Set SKILLFORGE_IMAP_USERNAME before sourcing this file." >&2
fi

if [[ -z "${SKILLFORGE_IMAP_PASSWORD:-}" ]]; then
  echo "Set SKILLFORGE_IMAP_PASSWORD before sourcing this file." >&2
fi
