# Browser qualification observations — 2026-10-05

The parent used the in-app browser against a loopback-only Frappe server serving the candidate worktree and disposable `release-gaps.localhost`. The test user was a synthetic Project Manager with Accounts User, one assigned Project and a user-default Company. The selected scope filter was disabled to exercise native Project permissions. Credentials and screenshots remain in the private release bench; no customer credentials or records were used.

## Actual observations and corrections

- Login and the permitted BOQ Header/Item routes worked. The allowed Project's records appeared in the list; a forbidden BOQ Item opened a native **Not permitted** response rather than its fields.
- A native BOQ Item Save was initially obstructed by the custom theme controls. The controls were appended beside Frappe's full-width header container; their position covered the Save button. They now share the inner header flex row, and the row/actions wrap. The Save button's center resolves to Save at widths 960, 1280 and 1440 pixels. Temporary viewport overrides were reset.
- The user saved quantity 10, factor 0.5 and contract rate 100. Reloaded native fields show factor 0.50 and line total **500**, with a native activity entry for the pricing change. The same fixture shows estimated cost 100 and estimated price 120. This is a synthetic INR Company, not Egyptian invoice-tax certification.
- Entering factor zero, leaving the field, and pressing Save returned native HTTP 417 with visible **Factor must be finite and greater than zero.** The item remained unsaved; factor 0.5 was restored and saved. The earlier automation attempt saved too quickly after field entry; the final probe uses native typing, field blur, Save and the subsequent response.
- Trial Balance requested 2026-01-01 through 2026-10-05 initially selected a configured future fiscal year (2050), causing the vendor to change the requested dates. The API now resolves a fiscal year with the requested date and Company, keeps historical year bounds, preserves explicit complete periods, and raises when the required year is missing. After server restart, the requested 2026 report returned HTTP 200 without the future-year warning.
- Arabic and English modes rendered the table and zero-total row. This fixture had no qualifying ledger rows; it does not establish translation/financial correctness on populated Arabic reports. Report/company authorization was subsequently strengthened using native Report and Company checks. Final code `4f110b0` passed 25 Stage-7 regressions, including native accounting-user Company allow/deny and disabled Report refusal. A final rebuilt-runtime browser smoke rendered Trial Balance for the selected/default Company with the requested 2026 dates and returned HTTP 200.
- The viewer no longer invents a hard-coded customer Company. It uses the user's default or requests selection. Stale error responses are ignored, and error text is rendered as text rather than HTML.

## Limits and retained evidence

This is selected browser workflow evidence, not a complete customer-role/company matrix, Arabic/English printing qualification, mobile-device qualification, v15 compatibility test or whole-app acceptance. The standalone loopback server has no Socket.IO service; its polling failures mean realtime behavior is unqualified. No print/PDF readiness is inferred from these screenshots.

Private evidence directory:
`/home/mohamed/frappe-bench/release-tests/customer-release-gap-fixes/private/end-to-end-20261005/`

Screenshots: `browser-saved-pricing.png`, `browser-zero-factor.png`, `browser-report-period.png`, `browser-report-final.png`. The saved-pricing screenshot shows the priced status and entered fields; line total 500 was verified in native field state and reload, not within that screenshot's crop. Server logs: the isolated bench's `logs/browser-server-20261005*.log`. Screenshots and fixture files remain outside Git. The native cleanup disabled the synthetic user, cleared API credentials and restored the original private site configuration. Owned browser tabs and the loopback server were closed; the GitHub Actions tab was retained only for pending authorized CI work.
