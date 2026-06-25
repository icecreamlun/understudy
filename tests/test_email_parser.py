import os
from pathlib import Path


def test_load_imap_config_from_env(monkeypatch):
    from skillforge_local.imap_config import load_imap_config

    monkeypatch.setenv("SKILLFORGE_IMAP_HOST", "imap.example.com")
    monkeypatch.setenv("SKILLFORGE_IMAP_PORT", "993")
    monkeypatch.setenv("SKILLFORGE_IMAP_USERNAME", "fde@example.com")
    monkeypatch.setenv("SKILLFORGE_IMAP_PASSWORD", "secret")
    monkeypatch.setenv("SKILLFORGE_IMAP_MAILBOX", "INBOX")

    config = load_imap_config()

    assert config.host == "imap.example.com"
    assert config.port == 993
    assert config.username == "fde@example.com"
    assert config.mailbox == "INBOX"
    assert "secret" not in repr(config)


def test_load_imap_config_requires_password(monkeypatch):
    from skillforge_local.imap_config import load_imap_config

    for key in list(os.environ):
        if key.startswith("SKILLFORGE_IMAP_"):
            monkeypatch.delenv(key, raising=False)

    try:
        load_imap_config()
    except RuntimeError as exc:
        assert "SKILLFORGE_IMAP_PASSWORD" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError")


def test_parse_email_bytes_to_activity_event():
    from skillforge_local.email_parser import parse_email_bytes

    raw = Path("tests/fixtures/acme_request.eml").read_bytes()

    event = parse_email_bytes(raw, actor="fde_engineer", object_ref="imap://INBOX/1")

    assert event["type"] == "email_received"
    assert event["source"] == "email"
    assert event["payload"]["message_id"] == "msg_acme_001@example.com"
    assert event["payload"]["from"] == "maya@acme.example"
    assert event["payload"]["subject"] == "API onboarding request for Acme"
    assert "credentials" in event["payload"]["content_summary"]


def test_build_event_from_imap_message():
    from skillforge_local.imap_collector import build_event_from_imap_message

    raw = Path("tests/fixtures/acme_request.eml").read_bytes()

    event = build_event_from_imap_message(raw, uid="42", actor="fde_engineer")

    assert event["object_ref"] == "imap://INBOX/42"
    assert event["type"] == "email_received"
    assert event["payload"]["message_id"] == "msg_acme_001@example.com"
