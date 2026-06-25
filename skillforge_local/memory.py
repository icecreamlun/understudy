"""Skill-feedback memory layer.

Captures thumbs up/down + free-text feedback on generated skills and recalls it
the next time a skill is generated, so the planner learns this reviewer's
preferences across sessions.

Primary store is **HydraDB** (the context layer): durable, semantic, and shared
across sessions/skills via a per-reviewer ``sub_tenant_id``. We also keep a local
JSONL mirror so (a) just-submitted feedback is applied immediately even while
HydraDB finishes its async ingestion, and (b) the loop still works with no
``HYDRA_DB_API_KEY`` set. Recall merges both and de-dupes.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .llm import load_local_env


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _feedback_log(root: Path) -> Path:
    return root / "workspace" / "feedback" / "skill_feedback.jsonl"


def _trace_log(root: Path) -> Path:
    return root / "workspace" / "feedback" / "memory_trace.jsonl"


class SkillMemory:
    """Read/write skill feedback to HydraDB (+ a local mirror)."""

    def __init__(self, root: Path | str = ".") -> None:
        self.root = Path(root)
        load_local_env(self.root)
        self.tenant = os.environ.get("HYDRA_TENANT_ID", "default-tenant")
        # Per-reviewer namespace: preferences carry across every skill this person
        # reviews, not just the one they gave feedback on.
        self.default_user = os.environ.get("HYDRA_SUB_TENANT", "controller")
        self._client: Any = None
        self._client_error: str | None = None

    # -- backend wiring --------------------------------------------------

    @property
    def hydra_configured(self) -> bool:
        return bool(os.environ.get("HYDRA_DB_API_KEY"))

    def _client_or_none(self) -> Any:
        if not self.hydra_configured or self._client_error is not None:
            return None
        if self._client is None:
            try:
                from hydra_db import HydraDB

                self._client = HydraDB(token=os.environ["HYDRA_DB_API_KEY"])
            except Exception as exc:  # noqa: BLE001 - degrade to local mirror
                self._client_error = str(exc)
                return None
        return self._client

    # -- trace (proof that the agent read/wrote HydraDB) ----------------

    def _trace(self, op: str, **fields: Any) -> None:
        record = {"ts": _utc_now(), "op": op, "tenant_id": self.tenant, "backend": self.status()["backend"], **fields}
        try:
            log = _trace_log(self.root)
            log.parent.mkdir(parents=True, exist_ok=True)
            with log.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record) + "\n")
        except Exception:  # noqa: BLE001 - tracing must never break the flow
            pass

    def recent_trace(self, limit: int = 30) -> list[dict[str, Any]]:
        log = _trace_log(self.root)
        if not log.exists():
            return []
        rows = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]
        return list(reversed(rows))[:limit]

    def status(self) -> dict[str, Any]:
        backend = "hydradb" if self._client_or_none() is not None else "local"
        return {
            "backend": backend,
            "tenant_id": self.tenant,
            "sub_tenant_id": self.default_user,
            "hydra_configured": self.hydra_configured,
            "error": self._client_error,
        }

    # -- write -----------------------------------------------------------

    def _feedback_text(self, skill_name: str, rating: str, note: str) -> str:
        verb = {"up": "liked (thumbs up)", "down": "disliked (thumbs down)"}.get(rating, rating)
        text = f"Reviewer {verb} the generated '{skill_name}' skill."
        if note.strip():
            text += f" Their feedback: {note.strip()}"
        text += " Apply this preference when generating or refining skills for this reviewer."
        return text

    def add_feedback(
        self,
        *,
        skill_id: str,
        skill_name: str,
        rating: str,
        note: str = "",
        user: str | None = None,
    ) -> dict[str, Any]:
        user = user or self.default_user
        record = {
            "ts": _utc_now(),
            "skill_id": skill_id,
            "skill_name": skill_name,
            "rating": rating,
            "note": note,
            "user": user,
        }

        # Local mirror first — guarantees immediacy + offline fallback.
        log = _feedback_log(self.root)
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")

        # HydraDB (durable, semantic, cross-session). Best-effort.
        hydra_status = "disabled"
        client = self._client_or_none()
        if client is not None:
            try:
                resp = client.upload.add_memory(
                    tenant_id=self.tenant,
                    sub_tenant_id=user,
                    upsert=True,
                    memories=[
                        {
                            "text": self._feedback_text(skill_name, rating, note),
                            "infer": True,
                            "user_name": user,
                        }
                    ],
                )
                hydra_status = "queued" if getattr(resp, "success", False) else "error"
            except Exception as exc:  # noqa: BLE001
                hydra_status = f"error: {exc}"

        record["hydra_status"] = hydra_status
        record["backend"] = self.status()["backend"]
        self._trace(
            "write",
            sub_tenant_id=user,
            rating=rating,
            stored=self._feedback_text(skill_name, rating, note)[:220],
            hydra_status=hydra_status,
        )
        return record

    # -- read ------------------------------------------------------------

    def recall_preferences(self, *, query: str, user: str | None = None, limit: int = 8) -> list[dict[str, Any]]:
        user = user or self.default_user
        items: list[dict[str, Any]] = []

        # HydraDB semantic recall (cross-session, the part that "remembers").
        client = self._client_or_none()
        if client is not None:
            try:
                rr = client.recall.recall_preferences(
                    tenant_id=self.tenant,
                    sub_tenant_id=user,
                    query=query,
                    max_results=limit,
                )
                for chunk in (getattr(rr, "chunks", None) or []):
                    text = (getattr(chunk, "chunk_content", None) or "").strip()
                    if text:
                        items.append(
                            {
                                "text": text,
                                "score": getattr(chunk, "relevancy_score", None),
                                "source": "hydradb",
                            }
                        )
            except Exception:  # noqa: BLE001 - fall back to local mirror
                pass

        # Local recent feedback — covers HydraDB's async ingestion lag and offline.
        items.extend(self._local_recent(user, limit))
        results = self._dedupe(items, limit)
        self._trace(
            "recall",
            sub_tenant_id=user,
            query=query[:160],
            hits=len(results),
            from_hydra=sum(1 for it in results if it.get("source") == "hydradb"),
            top=[
                {"text": r["text"][:140], "score": r.get("score"), "source": r.get("source")}
                for r in results[:3]
            ],
        )
        return results

    def _local_recent(self, user: str, limit: int) -> list[dict[str, Any]]:
        log = _feedback_log(self.root)
        out: list[dict[str, Any]] = []
        if not log.exists():
            return out
        rows = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]
        for row in reversed(rows):
            if row.get("user") and row["user"] != user:
                continue
            out.append(
                {
                    "text": self._feedback_text(row.get("skill_name", ""), row.get("rating", ""), row.get("note", "")),
                    "score": None,
                    "source": "local",
                    "rating": row.get("rating"),
                    "note": row.get("note"),
                }
            )
            if len(out) >= limit:
                break
        return out

    @staticmethod
    def _dedupe(items: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        for item in items:
            key = (item.get("note") or item.get("text") or "")[:80].lower()
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(item)
            if len(out) >= limit:
                break
        return out
