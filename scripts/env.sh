#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -z "${QWEN_MODEL_PATH:-}" ]]; then
  if [[ -f "/mnt/d/models/qwen3-30b/Qwen3-30B-A3B-Q4_K_M.gguf" ]]; then
    export QWEN_MODEL_PATH="/mnt/d/models/qwen3-30b/Qwen3-30B-A3B-Q4_K_M.gguf"
  elif [[ -f "/models/qwen3-30b/Qwen3-30B-A3B-Q4_K_M.gguf" ]]; then
    export QWEN_MODEL_PATH="/models/qwen3-30b/Qwen3-30B-A3B-Q4_K_M.gguf"
  else
    export QWEN_MODEL_PATH="D:/models/qwen3-30b/Qwen3-30B-A3B-Q4_K_M.gguf"
  fi
fi

export HACKATHON_ROOT="$ROOT"
export QWEN_MODEL_TAG="${QWEN_MODEL_TAG:-qwen3-30b-a3b-local}"

if [[ -z "${MODEL_ROOT:-}" ]]; then
  if [[ -d "/mnt/d/models" ]]; then
    export MODEL_ROOT="/mnt/d/models"
  else
    export MODEL_ROOT="D:/models"
  fi
fi

export OPENCLAW_SOURCE_DIR="${OPENCLAW_SOURCE_DIR:-$MODEL_ROOT/openclaw}"
export NEMOCLAW_SOURCE_DIR="${NEMOCLAW_SOURCE_DIR:-$MODEL_ROOT/NemoClaw}"
export OPENSHELL_SOURCE_DIR="${OPENSHELL_SOURCE_DIR:-$MODEL_ROOT/OpenShell}"
export OPENCLAW_HOME="${OPENCLAW_HOME:-$ROOT/.runtime/openclaw-home}"
export OPENCLAW_STATE_DIR="${OPENCLAW_STATE_DIR:-$ROOT/.runtime/openclaw-state}"
export OPENCLAW_CONFIG_PATH="${OPENCLAW_CONFIG_PATH:-$ROOT/config/openclaw.json}"
export OLLAMA_API_KEY="${OLLAMA_API_KEY:-ollama-local}"

export NEMOCLAW_ACCEPT_THIRD_PARTY_SOFTWARE=1
export NEMOCLAW_NON_INTERACTIVE=1
export NEMOCLAW_YES=1
export NEMOCLAW_PROVIDER="${NEMOCLAW_PROVIDER:-ollama}"
export NEMOCLAW_MODEL="${NEMOCLAW_MODEL:-$QWEN_MODEL_TAG}"
export NEMOCLAW_CONTEXT_WINDOW="${NEMOCLAW_CONTEXT_WINDOW:-32768}"
export NEMOCLAW_SANDBOX_NAME="${NEMOCLAW_SANDBOX_NAME:-vendor-risk-agent}"
export NEMOCLAW_POLICY_MODE="${NEMOCLAW_POLICY_MODE:-suggested}"
export NEMOCLAW_POLICY_TIER="${NEMOCLAW_POLICY_TIER:-balanced}"
