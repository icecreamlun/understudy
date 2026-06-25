import json


def test_openclaw_extractor_uses_runner_json_output():
    from skillforge_local.openclaw_email import extract_email_activity_with_openclaw

    calls = []

    def fake_runner(prompt: str) -> str:
        calls.append(prompt)
        return json.dumps(
            {
                "is_match": True,
                "intent": "customer_implementation_request",
                "extracted": {
                    "customer": "Acme",
                    "contact": "maya@acme.example",
                    "request_type": "API onboarding",
                    "due_date": "",
                    "blockers": ["Credentials missing"],
                    "next_step": "Ask customer for credentials",
                },
            }
        )

    event = {
        "payload": {
            "from": "maya@acme.example",
            "subject": "API onboarding request for Acme",
            "content_summary": "Acme needs credentials.",
        }
    }

    result = extract_email_activity_with_openclaw(event, runner=fake_runner)

    assert calls
    assert "API onboarding request for Acme" in calls[0]
    assert result["is_match"] is True
    assert result["intent"] == "customer_implementation_request"
    assert result["extracted"]["customer"] == "Acme"


def test_mock_openclaw_extractor_is_deterministic_for_demo():
    from skillforge_local.openclaw_email import mock_openclaw_extract

    event = {
        "payload": {
            "from": "maya@acme.example",
            "subject": "API onboarding request for Acme",
            "content_summary": "We need credentials and field mapping.",
        }
    }

    result = mock_openclaw_extract(event)

    assert result["is_match"] is True
    assert result["intent"] == "customer_implementation_request"
    assert result["extracted"]["customer"] == "Acme"
    assert "Credentials missing" in result["extracted"]["blockers"]


def test_enrich_email_event_with_openclaw_fields():
    from skillforge_local.openclaw_email import enrich_email_event

    event = {
        "payload": {
            "from": "maya@acme.example",
            "subject": "API onboarding request for Acme",
            "content_summary": "Acme needs credentials.",
        }
    }
    extraction = {
        "is_match": True,
        "intent": "customer_implementation_request",
        "extracted": {
            "customer": "Acme",
            "contact": "maya@acme.example",
            "request_type": "API onboarding",
            "due_date": "",
            "blockers": ["Credentials missing"],
            "next_step": "Ask customer for credentials",
        },
    }

    enriched = enrich_email_event(event, extraction)

    assert enriched["payload"]["intent"] == "customer_implementation_request"
    assert enriched["payload"]["customer"] == "Acme"
    assert enriched["payload"]["extracted"]["request_type"] == "API onboarding"
    assert enriched["payload"]["openclaw"]["is_match"] is True
