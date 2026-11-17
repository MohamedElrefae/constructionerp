"""Deterministic local MCP/T3 protocol simulator (test-only, loopback only).

Implements the JSON-RPC surface `HttpT3Client` speaks: initialize,
tools/list, tools/call for t3_thread_launch / t3_thread_read /
t3_thread_interrupt / t3_project_list / t3_thread_list, with bearer auth,
session header, pagination and configurable failures.
"""

import json
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class SimState:
    def __init__(self, token="sim-token-0123456789abcdef", fail=None, delay=0.0,
                 legacy_marker_mode=False):
        self.token = token
        self.fail = fail
        self.delay = float(delay or 0.0)
        # Explicit legacy protocol-fixture mode: low-level transport tests
        # send arbitrary briefs and need only a marker. Engine integration
        # prompts carry a prepared envelope and always exercise the full wire.
        self.legacy_marker_mode = bool(legacy_marker_mode)
        # fail: None | "http500" | "malformed" | "lost_reply" | "no_marker"
        self.lock = threading.Lock()
        self.calls = []             # [(method, name_or_none)]
        self.sessions_seen = []     # Mcp-Session-Id header per tools/call
        self.threads = {}           # threadId -> record
        self.projects = [{"projectId": "proj-a"}, {"projectId": "proj-b"}, {"projectId": "proj-c"}]
        self._next = 0
        self.session = "sess-sim-1"
        self.event_file = None      # optional JSONL launch log for tests


class _Handler(BaseHTTPRequestHandler):
    state: SimState = None

    def log_message(self, *args):  # silence
        pass

    def _send(self, code, payload, headers=None):
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        state = self.state
        if self.path != "/mcp":
            return self._send(404, {"error": "not found"})
        auth = self.headers.get("Authorization", "")
        if auth != f"Bearer {state.token}":
            return self._send(401, {"error": "unauthorized"})
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length)
        try:
            body = json.loads(raw.decode())
        except ValueError:
            return self._send(400, {"error": "bad json"})
        method = body.get("method")
        with state.lock:
            state.calls.append((method, (body.get("params") or {}).get("name")))
            if method == "tools/call":
                state.sessions_seen.append(self.headers.get("Mcp-Session-Id"))
            fail = state.fail
        if fail == "http500":
            return self._send(500, {"error": "simulated failure"})
        if fail == "echo_token":
            return self._send(500, {"error": f"upstream said Bearer {state.token} is invalid"})
        if fail == "malformed":
            return self._send(200, b"this is not json")
        if method == "initialize":
            return self._send(200, {"jsonrpc": "2.0", "id": body.get("id"),
                                    "result": {"protocolVersion": "2025-03-26",
                                               "capabilities": {},
                                               "serverInfo": {"name": "mcp-sim", "version": "1"}}},
                              headers={"Mcp-Session-Id": state.session})
        if method == "notifications/initialized":
            return self._send(202, {})
        if method == "tools/list":
            return self._send(200, {"jsonrpc": "2.0", "id": body.get("id"),
                                    "result": {"tools": [{"name": n} for n in (
                                        "t3_thread_launch", "t3_thread_read",
                                        "t3_thread_interrupt", "t3_project_list",
                                        "t3_thread_list")]}})
        if method != "tools/call":
            return self._send(200, {"jsonrpc": "2.0", "id": body.get("id"),
                                    "error": {"code": -32601, "message": "unknown method"}})
        params = body.get("params") or {}
        name = params.get("name")
        args = params.get("arguments") or {}
        result = self._tool(state, name, args)
        if result is None:
            return self._send(500, {"error": "simulated lost reply"})
        return self._send(200, {"jsonrpc": "2.0", "id": body.get("id"), "result": result})

    @staticmethod
    def _tool(state, name, args):
        def text(payload):
            return {"content": [{"type": "text", "text": json.dumps(payload)}]}

        if name == "t3_thread_launch":
            if state.delay:
                time.sleep(state.delay)
            with state.lock:
                state._next += 1
                tid = f"thr-{state._next:04d}"
                model = (args.get("modelSelection") or {}).get("model")
                state.threads[tid] = {
                    "threadId": tid,
                    "title": args.get("title"),
                    "message": args.get("message"),
                    "model": model,
                    "provider": (args.get("modelSelection") or {}).get("instanceId"),
                    "createdAt": datetime.now(timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%S.000Z"),
                }
                if state.event_file:
                    with open(state.event_file, "a") as fh:
                        fh.write(json.dumps({"event": "launch", "threadId": tid,
                                             "title": args.get("title")}) + "\n")
                if state.fail == "lost_reply":
                    return None  # caller turns this into a 500
            return text({"threadId": tid, "projectId": "proj-a", "title": args.get("title")})
        if name == "t3_thread_read":
            tid = args.get("threadId")
            rec = state.threads.get(tid)
            if rec is None:
                raise KeyError(tid)
            import re as _re
            marker = _re.search(r"ENGINE-T3-RESULT job-[0-9a-f]+", rec["message"] or "")
            nonce = _re.search(r"Per-attempt token: ([0-9a-f]+)", rec["message"] or "")
            if state.fail == "no_marker" or marker is None:
                answer = "SYNTHETIC-OK (no marker)"
            else:
                # Emit a real result-wire-shaped assistant response from the
                # prepared envelope embedded in the Engine prompt. This keeps
                # the simulator synthetic while exercising production decoding
                # and binding checks instead of relying on a fabricated PASS.
                import json as _json
                prompt = rec.get("message") or ""
                prefix = "result_json must encode this envelope, changing verdict/findings as warranted: "
                at = prompt.find(prefix)
                if at < 0:
                    if not state.legacy_marker_mode:
                        raise ValueError("simulator prompt lacks prepared result envelope")
                    answer = f"SYNTHETIC-LEGACY-MARKER\n{marker.group(0)}"
                else:
                    start = at + len(prefix)
                    prepared, _end = _json.JSONDecoder().raw_decode(prompt, start)
                    prepared = dict(prepared)
                    prepared.update(status="COMPLETE", failure_class=None, findings=[])
                    prepared["verdict"] = "PROPOSED" if prepared.get("role") in ("architect", "proposer") else "PASS"
                    wire = {"result_json": _json.dumps(prepared),
                            "explanation": "Synthetic simulator result wire.",
                            "plan_text": "Synthetic simulator plan." if prepared.get("role") in ("architect", "proposer") else ""}
                    answer = _json.dumps(wire) + "\n" + marker.group(0)
                if nonce:
                    answer += f"\nPer-attempt token: {nonce.group(1)}"
            return text({
                "thread": {"threadId": tid, "status": "completed",
                           "model": rec["model"], "pendingRequestCount": 0},
                "recentRuns": [{"status": "completed", "executedModel": rec["model"]}],
                "items": [{"type": "assistant_message", "text": answer}],
            })
        if name == "t3_thread_interrupt":
            if state.event_file:
                with open(state.event_file, "a") as fh:
                    fh.write(json.dumps({"event": "interrupt",
                                         "threadId": args.get("threadId")}) + "\n")
            return text({"threadId": args.get("threadId"), "status": "cancelled"})
        if name == "t3_project_list":
            limit = int(args.get("limit") or 100)
            cursor = int(args.get("cursor") or 0)
            page = state.projects[cursor:cursor + limit]
            nxt = cursor + limit if cursor + limit < len(state.projects) else None
            return text({"projects": page, "nextCursor": nxt})
        if name == "t3_thread_list":
            title = args.get("titleContains") or ""
            matches = [{"threadId": t, "title": r["title"], "createdAt": r["createdAt"]}
                       for t, r in state.threads.items() if title in (r["title"] or "")]
            limit = int(args.get("limit") or 100)
            cursor = int(args.get("cursor") or 0)
            page = matches[cursor:cursor + limit]
            nxt = cursor + limit if cursor + limit < len(matches) else None
            return text({"threads": page, "nextCursor": nxt})
        return {"isError": True, "content": [{"type": "text", "text": f"unknown tool {name}"}]}


class SimServer:
    def __init__(self, state: SimState):
        self.state = state
        handler = type("_H", (_Handler,), {"state": state})
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        host, port = self.httpd.server_address[:2]
        return f"http://{host}:{port}"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()
