from __future__ import annotations

from email import policy
from email.message import EmailMessage, Message
from email.parser import BytesParser
from email.utils import getaddresses, parsedate_to_datetime
from hashlib import sha256


def parse_email_bytes(raw: bytes, *, actor: str, object_ref: str) -> dict:
    message = BytesParser(policy=policy.default).parsebytes(raw)
    message_id = _clean_message_id(str(message.get("Message-ID", "")))
    subject = str(message.get("Subject", "")).strip()
    sender = _first_address(str(message.get("From", "")))
    recipients = [addr for _, addr in getaddresses(message.get_all("To", []))]
    received_at = parsedate_to_datetime(str(message.get("Date"))).isoformat()
    body_text = _extract_text(message)
    digest = sha256(raw).hexdigest()

    return {
        "contract_version": "activity_event.v1",
        "event_id": f"evt_email_{digest[:12]}",
        "ts": received_at,
        "actor": actor,
        "source": "email",
        "type": "email_received",
        "object_ref": object_ref,
        "payload": {
            "message_id": message_id,
            "thread_id": message_id,
            "received_at": received_at,
            "from": sender,
            "to": recipients,
            "subject": subject,
            "content_summary": _summarize(body_text),
            "body_text": body_text,
            "body_text_ref": object_ref,
        },
    }


def _clean_message_id(value: str) -> str:
    return value.strip().strip("<>").strip()


def _first_address(value: str) -> str:
    addresses = getaddresses([value])
    return addresses[0][1] if addresses else ""


def _extract_text(message: EmailMessage | Message) -> str:
    if message.is_multipart():
        parts: list[str] = []
        for part in message.walk():
            if part.get_content_type() == "text/plain":
                parts.append(str(part.get_content()))
        return "\n".join(parts).strip()
    return str(message.get_content()).strip()


def _summarize(text: str, limit: int = 240) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3].rstrip() + "..."
