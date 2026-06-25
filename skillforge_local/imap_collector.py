from __future__ import annotations

import imaplib
from collections.abc import Iterator, Sequence

from skillforge_local.email_parser import parse_email_bytes
from skillforge_local.imap_config import ImapConfig


def build_event_from_imap_message(
    raw: bytes,
    *,
    uid: str,
    actor: str,
    mailbox: str = "INBOX",
) -> dict:
    return parse_email_bytes(raw, actor=actor, object_ref=f"imap://{mailbox}/{uid}")


def fetch_unseen_once(
    config: ImapConfig,
    *,
    actor: str = "fde_engineer",
    limit: int | None = None,
    latest: bool = False,
) -> Iterator[dict]:
    with imaplib.IMAP4_SSL(config.host, config.port) as client:
        client.login(config.username, config.password)
        client.select(config.mailbox)
        status, data = client.uid("search", None, "UNSEEN")
        if status != "OK":
            raise RuntimeError("IMAP UNSEEN search failed")

        uids = data[0].split() if data and data[0] else []
        if latest:
            uids = list(reversed(uids))
        if limit is not None:
            uids = uids[: max(0, limit)]
        for uid_bytes in uids:
            uid = uid_bytes.decode("ascii")
            fetch_status, fetch_data = client.uid("fetch", uid, "(BODY.PEEK[])")
            if fetch_status != "OK":
                continue
            raw = _extract_rfc822(fetch_data)
            if raw:
                yield build_event_from_imap_message(
                    raw,
                    uid=uid,
                    actor=actor,
                    mailbox=config.mailbox,
                )


def _extract_rfc822(fetch_data: Sequence[object]) -> bytes | None:
    for item in fetch_data:
        if isinstance(item, tuple) and isinstance(item[1], bytes):
            return item[1]
    return None
