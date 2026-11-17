"""Do not treat an incomplete T3 message projection as a complete result."""

import pytest

from t3_transport import HttpT3Client, TransportRefusal, TransportUncertain


def client_for(pages):
    client = object.__new__(HttpT3Client)
    calls = []

    def tool(name, arguments):
        assert name == "t3_thread_read"
        calls.append(arguments)
        return pages[len(calls) - 1]

    client._tool = tool
    return client, calls


def page(text, **extra):
    return {
        "thread": {"status": "completed", "model": "model-a"},
        "recentRuns": [{"status": "completed", "executedModel": "model-a"}],
        "items": [{"type": "assistant_message", "text": text}],
        **extra,
    }


def test_status_reads_all_message_pages():
    client, calls = client_for([
        page("first", hasMore=True, nextPosition=5),
        page("second", hasMore=False),
    ])
    assert client.status("thread-a")["summary"] == "first\nsecond"
    assert calls[1]["afterPosition"] == 5


def test_status_uses_current_run_and_ignores_truncated_user_prompt():
    response = page("unused")
    response["recentRuns"][0]["runId"] = "run-new"
    response["items"] = [
        {"type": "user_message", "text": "long prompt", "textTruncated": True},
        {"type": "assistant_message", "runId": "run-old", "text": "old"},
        {"type": "assistant_message", "runId": "run-new", "text": "new"},
    ]
    client, _ = client_for([response])
    assert client.status("thread-a")["summary"] == "new"


def test_status_refuses_repeated_pagination_cursor():
    client, calls = client_for([
        page("first", hasMore=True, nextPosition=5),
        page("second", hasMore=True, nextPosition=5),
    ])
    with pytest.raises(TransportUncertain):
        client.status("thread-a")
    assert len(calls) == 2


def test_configured_model_is_not_reported_as_execution_evidence():
    response = page("result")
    response["recentRuns"][0]["executedModel"] = None
    response["recentRuns"][0]["model"] = "opencode-go/deepseek-v4.1-flash"
    client, _ = client_for([response])
    status = client.status("thread-a")
    assert status["model"] == "opencode-go/deepseek-v4.1-flash"
    assert status["executedModel"] is None
    assert status["modelEvidence"] == "configured_only"


@pytest.mark.parametrize("is_tool_error", [False, True])
def test_tool_error_does_not_expose_mcp_credential(is_tool_error):
    token = "sensitive-token-0123456789"
    client = HttpT3Client("http://127.0.0.1:12345", token)
    payload = {"isError": True, "content": [{"type": "text", "text": token}]}
    client._post = lambda _: {"result": payload} if is_tool_error else {"error": {"message": token}}
    with pytest.raises(TransportRefusal) as exc:
        client._tool("test", {})
    assert token not in str(exc.value)


@pytest.mark.parametrize("response", [
    page("partial", hasMore=True, nextPosition=None),
    {**page("partial"), "items": [{"type": "assistant_message", "text": "partial", "textTruncated": True}]},
    page("x" * 50_001),
])
def test_status_refuses_incomplete_or_overlong_messages(response):
    client, _ = client_for([response])
    with pytest.raises(TransportUncertain):
        client.status("thread-a")


def test_status_requests_practical_item_limit_and_accepts_response_under_bound():
    client, calls = client_for([page("x" * 9_000)])
    assert len(client.status("thread-a")["summary"]) == 9_000
    assert calls[0]["maxCharsPerItem"] == 50_000


def test_status_fails_closed_when_assistant_item_reports_truncation():
    response = page("complete-looking marker")
    response["items"][0]["textTruncated"] = True
    client, _ = client_for([response])
    with pytest.raises(TransportUncertain, match="truncated"):
        client.status("thread-a")
