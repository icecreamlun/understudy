from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, repr=False)
class ImapConfig:
    host: str
    port: int
    username: str
    password: str
    mailbox: str = "INBOX"

    def __repr__(self) -> str:
        return (
            "ImapConfig("
            f"host={self.host!r}, "
            f"port={self.port!r}, "
            f"username={self.username!r}, "
            "password=<redacted>, "
            f"mailbox={self.mailbox!r})"
        )


def load_imap_config() -> ImapConfig:
    required = [
        "SKILLFORGE_IMAP_HOST",
        "SKILLFORGE_IMAP_USERNAME",
        "SKILLFORGE_IMAP_PASSWORD",
    ]
    missing = [key for key in required if not os.environ.get(key)]
    if missing:
        raise RuntimeError(f"Missing IMAP environment variables: {', '.join(missing)}")

    port_raw = os.environ.get("SKILLFORGE_IMAP_PORT", "993")
    try:
        port = int(port_raw)
    except ValueError as exc:
        raise RuntimeError("SKILLFORGE_IMAP_PORT must be an integer") from exc

    return ImapConfig(
        host=os.environ["SKILLFORGE_IMAP_HOST"],
        port=port,
        username=os.environ["SKILLFORGE_IMAP_USERNAME"],
        password=os.environ["SKILLFORGE_IMAP_PASSWORD"],
        mailbox=os.environ.get("SKILLFORGE_IMAP_MAILBOX", "INBOX"),
    )
