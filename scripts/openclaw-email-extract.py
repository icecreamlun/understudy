#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path


def ensure_local_openclaw_config(root: Path) -> Path:
    source = root / "config" / "openclaw.json"
    target = root / ".runtime" / "openclaw.local.json"
    config = json.loads(source.read_text(encoding="utf-8"))
    defaults = config.setdefault("agents", {}).setdefault("defaults", {})
    defaults["workspace"] = str(root / "workspace")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return target


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    prompt = sys.stdin.read()
    session_key = os.environ.get("SKILLFORGE_OPENCLAW_SESSION_KEY")
    if not session_key:
        session_key = f"agent:main:skillforge-email-extract-{uuid.uuid4().hex}"
    command = [
        os.environ.get("OPENCLAW_BIN", "openclaw"),
        "agent",
        "--local",
        "--json",
        "--session-key",
        session_key,
        "--timeout",
        os.environ.get("SKILLFORGE_OPENCLAW_AGENT_TIMEOUT", "180"),
        "--message",
        prompt,
    ]
    env = os.environ.copy()
    env.setdefault("OPENCLAW_CONFIG_PATH", str(ensure_local_openclaw_config(root)))
    env.setdefault("OPENCLAW_HOME", str(root / ".runtime" / "openclaw-home"))
    env.setdefault("OPENCLAW_STATE_DIR", str(root / ".runtime" / "openclaw-state"))

    completed = subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
        timeout=int(os.environ.get("SKILLFORGE_OPENCLAW_WRAPPER_TIMEOUT", "240")),
        env=env,
    )
    if completed.returncode != 0:
        sys.stderr.write(completed.stderr)
        return completed.returncode

    text = completed.stdout.strip()
    start = text.find("{")
    if start < 0:
        sys.stderr.write("OpenClaw output did not contain JSON\n")
        return 2
    payload = json.loads(text[start:])
    response_text = ""
    payloads = payload.get("payloads")
    if isinstance(payloads, list) and payloads:
        response_text = str(payloads[0].get("text") or "")
    response_text = response_text or str(payload.get("meta", {}).get("finalAssistantVisibleText") or "")
    if not response_text:
        sys.stderr.write("OpenClaw JSON did not include assistant text\n")
        return 2
    print(response_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
