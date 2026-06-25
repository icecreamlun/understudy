"""Codex-CLI-backed LLM helper — Understudy's engine.

Every AI call in Understudy routes through this module, and every call runs through
the **OpenAI Codex CLI** (`codex exec`) in API-key mode. There is no Anthropic/OpenAI
SDK call here: Codex is the engine, so the whole product is powered by Codex.

`codex exec` runs non-interactively, read-only (no file writes, no network), in an
ephemeral session, and writes its final message to a file we capture. Credentials come
from `OPENAI_API_KEY` (loaded from a git-ignored `.env.local` at the project root).
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

# Empty default = let the Codex CLI choose its model. Override with CODEX_MODEL.
DEFAULT_MODEL = ""


def default_model() -> str:
    return os.environ.get("CODEX_MODEL") or os.environ.get("SKILLGEN_MODEL") or DEFAULT_MODEL


def load_local_env(root: Path | str = ".") -> None:
    """Populate os.environ from a git-ignored .env.local / .env file if present.

    Existing environment variables are never overwritten.
    """
    for name in (".env.local", ".env"):
        path = Path(root) / name
        if not path.exists():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _is_openai_model(model: str | None) -> bool:
    """Only forward real OpenAI model ids to the CLI (e.g. gpt-5.5).

    Legacy Claude ids and our internal "codex-default" placeholder are ignored, so
    the Codex CLI just uses its own default model in those cases.
    """
    if not model:
        return False
    m = str(model).lower()
    if "claude" in m or "opus" in m or "sonnet" in m or "haiku" in m or m == "codex-default":
        return False
    return any(tag in m for tag in ("gpt-", "o1", "o3", "o4"))


def _messages_to_prompt(messages: list[dict[str, str]]) -> str:
    """Flatten OpenAI-style messages into one prompt for `codex exec`."""
    system_parts: list[str] = []
    convo: list[str] = []
    for message in messages:
        role = message.get("role")
        content = message.get("content", "") or ""
        if role == "system":
            if content:
                system_parts.append(content)
        elif role == "assistant":
            convo.append(f"[assistant]\n{content}")
        else:
            convo.append(content)
    prompt = ""
    if system_parts:
        prompt += "\n\n".join(system_parts) + "\n\n"
    prompt += "\n\n".join(convo)
    return prompt.strip()


def complete_text(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    max_tokens: int = 16000,
    timeout_seconds: int = 180,
    api_key: str | None = None,
    base_url: str | None = None,
    thinking: bool = True,
) -> str:
    """Run a single completion through the Codex CLI and return its final message.

    Accepts OpenAI-style messages. ``max_tokens`` / ``thinking`` / ``base_url`` are kept
    for signature compatibility with existing callers but are not used — Codex manages
    its own reasoning. Raises on failure so callers can fall back deterministically.
    """
    load_local_env()
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to .env.local at the project root "
            "or export it in your shell. (Understudy runs on the Codex CLI.)"
        )

    prompt = _messages_to_prompt(messages)
    chosen_model = (model if _is_openai_model(model) else None) or (os.environ.get("CODEX_MODEL") or None)

    with tempfile.TemporaryDirectory(prefix="understudy-codex-") as workdir:
        out_path = Path(workdir) / "last_message.txt"
        cmd = [
            "codex", "exec",
            "--skip-git-repo-check",
            "--ephemeral",
            "-s", "read-only",
            "-c", "preferred_auth_method=apikey",
            "--color", "never",
            "-C", workdir,
            "-o", str(out_path),
        ]
        if chosen_model:
            cmd += ["-m", chosen_model]

        env = {**os.environ, "OPENAI_API_KEY": key}
        try:
            proc = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                env=env,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                "The Codex CLI ('codex') was not found. Install it and run `codex` once, "
                "or `npm i -g @openai/codex`."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"Codex CLI timed out after {timeout_seconds}s") from exc

        if out_path.exists():
            text = out_path.read_text(encoding="utf-8").strip()
            if text:
                return text

        if proc.returncode != 0:
            raise RuntimeError(f"Codex CLI failed (exit {proc.returncode}): {(proc.stderr or '')[-600:]}")
        out = (proc.stdout or "").strip()
        if not out:
            raise RuntimeError("Codex CLI returned no output.")
        return out
