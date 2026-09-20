# Stage 3 — live HTTP dispatch claim WITHDRAWN (builder decision, round 5)

The prior live-socket HTTP artifact claimed that the overridden vendor
endpoint was exercised through the real HTTP layer. Reproducibility could
not be established in this environment: `bench serve` (development WSGI
server) intermittently refuses the very same whitelisted request it served
seconds earlier with an identical payload, flipping between HTTP 417
(governed refusal — reached the function) and HTTP 403 (framework
whitelist membership miss) for identical requests to the same endpoint.

Preserved artifacts in this directory document the intermittency rather
than a stable dispatch claim:

- `transcript.raw` — full request/response JSON (headers, bodies, statuses)
  from a failing run (403s) on the dev server.
- `transcript-417.raw` — full request/response JSON from a passing run
  (417 ValidationError from the governed function through the vendor path).
- `serve.log` — the dev-server access log of the same session showing
  identical requests producing both 417 and 403.
- `http_dispatch.py`, `setup.session`, `cleanup.session` — the exact
  fixture/runner/cleanup scripts.

The HTTP-dispatch closure for Stage 3 therefore rests on the permanent
handler-level test
(`test_http_dispatch_through_overridden_endpoint` in
`construction/tests/test_bilingual_account_pilot.py`), which drives
`frappe.handler.execute_cmd` — the exact dispatch function the HTTP
`/api/method` layer runs — with POST-shaped `form_dict` string coercion
(including the `from_descendant: "1"` string form field), override
resolution, reason enforcement at the vendor path. Its coverage is:
reason-free rejection, reasoned success, and handler-level string coercion
of `from_descendant`. The independent Round-4 AI-R review already accepted
this as closing the code-path point ("The hermetic dispatcher test closes
the code-path point").

Fixture lifecycle proof: `setup.out` and `cleanup.out` are the CAPTURED
outputs of the governed setup/cleanup console sessions — the setup creates
`CT-HTTP-1 - CT HTTP Probe - E` and the final recorded cleanup removes it
with `"leftover": []` (no residue).

No live-socket dispatch claim is made by the builder for this round.
