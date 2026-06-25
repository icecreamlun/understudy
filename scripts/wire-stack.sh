#!/usr/bin/env bash
set -euo pipefail

START_MODEL=0
RUN_NEMOCLAW=0

for arg in "$@"; do
  case "$arg" in
    --start-model) START_MODEL=1 ;;
    --run-nemoclaw-onboard) RUN_NEMOCLAW=1 ;;
    *) echo "unknown argument: $arg" >&2; exit 2 ;;
  esac
done

# shellcheck source=./env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/env.sh"

mkdir -p \
  "$HACKATHON_ROOT/.runtime/logs" \
  "$OPENCLAW_HOME" \
  "$OPENCLAW_STATE_DIR/agents/main/agent" \
  "$HACKATHON_ROOT/workspace"

if [[ ! -f "$QWEN_MODEL_PATH" ]]; then
  echo "Qwen GGUF not found: $QWEN_MODEL_PATH" >&2
  exit 1
fi

for stack_path in "$OPENCLAW_SOURCE_DIR" "$NEMOCLAW_SOURCE_DIR" "$OPENSHELL_SOURCE_DIR"; do
  if [[ ! -d "$stack_path" ]]; then
    echo "Stack source not found: $stack_path" >&2
    exit 1
  fi
done

echo "Hackathon root: $HACKATHON_ROOT"
echo "Qwen model:     $QWEN_MODEL_PATH"
echo "Model tag:      $QWEN_MODEL_TAG"
echo "OpenClaw src:   $OPENCLAW_SOURCE_DIR"
echo "NemoClaw src:   $NEMOCLAW_SOURCE_DIR"
echo "OpenShell src:  $OPENSHELL_SOURCE_DIR"
echo "OpenClaw cfg:   $OPENCLAW_CONFIG_PATH"
echo "OpenClaw home:  $OPENCLAW_HOME"
echo "OpenClaw state: $OPENCLAW_STATE_DIR"
echo

for cmd in openclaw ollama nemoclaw openshell docker; do
  if command -v "$cmd" >/dev/null 2>&1; then
    printf "%-10s found\n" "$cmd"
  else
    printf "%-10s missing\n" "$cmd"
  fi
done

if [[ "$START_MODEL" == "1" ]]; then
  command -v ollama >/dev/null 2>&1 || {
    echo "ollama is not on PATH. Install/start Ollama first." >&2
    exit 1
  }

  if ! curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    nohup ollama serve >"$HACKATHON_ROOT/.runtime/logs/ollama.log" 2>&1 &
    for _ in $(seq 1 20); do
      curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1 && break
      sleep 1
    done
  fi

  cat >"$HACKATHON_ROOT/.runtime/Modelfile.qwen3-30b-a3b" <<EOF_MODELFILE
FROM $QWEN_MODEL_PATH

PARAMETER num_ctx 32768
PARAMETER temperature 0.2
PARAMETER top_p 0.95

SYSTEM """
You are a local offline business AI agent running on the Dell/NVIDIA hackathon stack.
Use only local context, local tools, and documents provided in the workspace.
When evidence is missing, say what is missing. Prefer concise, cited risk analysis.
"""
EOF_MODELFILE

  if ! ollama list | awk '{print $1}' | grep -qx "$QWEN_MODEL_TAG"; then
    ollama create "$QWEN_MODEL_TAG" -f "$HACKATHON_ROOT/.runtime/Modelfile.qwen3-30b-a3b"
  fi

  curl -fsS http://127.0.0.1:11434/api/chat \
    -H 'content-type: application/json' \
    -d "{\"model\":\"$QWEN_MODEL_TAG\",\"stream\":false,\"messages\":[{\"role\":\"user\",\"content\":\"Reply with READY only.\"}]}" \
    >/dev/null

  echo "Ollama model ready: $QWEN_MODEL_TAG"
fi

if [[ "$RUN_NEMOCLAW" == "1" ]]; then
  command -v nemoclaw >/dev/null 2>&1 || {
    echo "nemoclaw is not on PATH. Install NemoClaw first." >&2
    exit 1
  }
  command -v openshell >/dev/null 2>&1 || {
    echo "openshell is not on PATH. NemoClaw needs OpenShell available or installable during onboarding." >&2
    exit 1
  }
  nemoclaw onboard --non-interactive --yes
fi
