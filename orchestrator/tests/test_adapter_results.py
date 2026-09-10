import json

import pytest
from adapters import classify_failure, parse_output
from core import WorkflowError


def native_trace(body):
    wire = json.dumps({"result_json": json.dumps(body), "explanation": "evidence", "plan_text": ""})
    return "\n".join(
        [
            json.dumps({"type": "thread.started", "thread_id": "native-session"}),
            json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": wire}}),
        ]
    )


def test_native_identity_is_taken_from_transport_not_body():
    session, body, _wire, _events = parse_output(native_trace({"session_id": "claimed"}), "codex")
    assert session == "native-session" and body["session_id"] == "claimed"


@pytest.mark.parametrize("value", [None, [], 1, "invalid"])
def test_non_object_result_is_malformed(value):
    with pytest.raises(WorkflowError):
        parse_output(native_trace(value), "codex")


@pytest.mark.parametrize(
    "text,timeout,expected",
    [
        ("401 unauthorized", False, "AUTH_FAILURE"),
        ("permission denied", False, "DENIED_ACTION"),
        ("", True, "TIMEOUT"),
        ("invalid output", False, "MALFORMED_RESULT"),
    ],
)
def test_adapter_failure_classes(text, timeout, expected):
    assert classify_failure(text, timeout) == expected
