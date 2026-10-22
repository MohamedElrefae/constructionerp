# Consultant Handoff to General Manager — Construction ERP First Client Release

**Date:** 2026-08-21
**From:** Software Consultant (Independent Release Review)
**To:** General Manager — for issue to client for UAT / first productive use
**Reviewed commit:** `88493fc` (`release: sign off construction ERP deployment`)
**Branch:** `develop` = `origin/develop` (hashes match exactly: `88493fcdc5e24c3495c98a6751f2aacd0288339a`, working tree clean)
**Authoritative sign-off:** [DEPLOYMENT_SIGN_OFF_2026-08-20.md](DEPLOYMENT_SIGN_OFF_2026-08-20.md)
**User guide under review:** [USER_GUIDE.md](USER_GUIDE.md) v1.3 (2026-08-20)

---

## 1. Consultant Verdict

**APPROVED FOR CLIENT HANDOVER.** I independently re-verified the 2026-08-20 sign-off rather than accepting it on trust: every remediation finding (F1–F7) was re-checked line-by-line in code, all nine claimed test suites were re-executed live on this bench, and `migrate` + asset build were re-run. **No release blocker remains.**

---

## 2. Independent Verification Performed (2026-08-21)

### 2.1 Git & release state
| Check | Result |
|---|---|
| Local HEAD = remote HEAD | ✔ `88493fc` both sides |
| Working tree | ✔ clean |
| `bench --site localhost migrate` | ✔ passed |
| `bench build --app construction` | ✔ passed |

### 2.2 Line-by-line code ⇄ user-guide sync audit
| Guide claim | Code evidence verified | Result |
|---|---|---|
| §2.1/§1.3 BOQ Header scope enforcement is feature-gated, admin-safe, preserves explicit project | `boq_header.py:21-49` — Administrator bypass (:22), gated on `enable_scope_context` (:26-32), explicit project preserved (:35-36) | ✔ F1 fixed |
| §3.2 leaf-only rejection message | Exact string at `boq_item.py:59`: "BOQ Item can only be linked to leaf nodes (is_group=0)." | ✔ F3 fixed |
| §12.2 cache-bust table (5 files) | All 5 match `hooks.py` exactly: `modern_theme.css?v=2.5.7`, `ct_link_control.js?v=16`, `boq_filters.js?v=8`, `filter_fix.js?v=11`, `scope_context_form_defaults.js?v=3` | ✔ F4 fixed |
| §8.4 omitted item hidden from dropdowns | `boq_filters.js:380` and `variation_order.js:71,83` pass `exclude_zero_revised=true`; server honors it (`boq_link_queries.py:201,266`) | ✔ F5 fixed |
| §11.1 "Form Config" grid-icon button | `vite_layout_controls.js` injects exactly that control | ✔ F6 fixed |
| §1.4 scope drift alert wording | Exact message at `boq_filters.js:523`; Error Log writer confirmed | ✔ |
| §2.3 Lock flow Draft→Pricing→Frozen→Locked, locked_by/locked_date | `VALID_TRANSITIONS` + `on_update` baseline revisions, `boq_header.py:9-13,67-76` | ✔ |
| §8 VO gates: Locked-only header, PDF-only client doc, lines frozen after Engineer Approval | `variation_order.py:67`, `:103-104`, `:121-151` | ✔ |
| §9.3 math `amount = qty × rate × (1 + wastage%)`, supersede/restore, est-cost refresh | `boq_cost_analysis.py:64`, supersede `:98`, restore-on-cancel `:137`, `est_unit_cost` write `:104` | ✔ |
| §10 Cost DB endpoints (template download / import / reprice) | 3 whitelisted functions in `cost_database_api.py` match guide URLs | ✔ |
| §2.2 WBS tree inline rollups; §4.3 Quick Create Leaf Structure; §5.1 onboarding banner key; §12.1 settings fields | `boq_structure_tree.js`; `boq_item.js:132,229`; `ct_boq_stage_onboarding_dismissed` at `boq_item_stage.js:87`; all four Construction Settings fields present in JSON | ✔ |

### 2.3 Live test execution (re-run by consultant, not taken from reports)
| Suite | Sign-off claim | Consultant re-run |
|---|---|---|
| Variation Orders | 23/23 | **23/23 OK** |
| Quantity Revisions | 30/30 | **30/30 OK** |
| Transaction Validation | 13/13 | **13/13 OK** |
| BOQ Link Queries | 9/9 | **9/9 OK** |
| BOQ Properties | 17/17 | **17/17 OK** |
| Scope Context integration runner | 17/17 | **17 passed, 0 failed** |
| Cost Analysis Engine | 17/17 | **17/17 OK** |
| Cost Database API | 10/10 | **10/10 OK** |
| VFC Backend | 39/39 | **39/39 OK** |
| **Total** | **175** | **175/175 PASS** |

> Environment note: bench Redis instances (ports 13000/11000) were down when review started; tests initially failed to run until they were restarted. This was an environment issue, not an app defect — see Risk R1.

---

## 3. Comments & Enhancements (non-blocking)

| # | Severity | Observation | Recommendation |
|---|---|---|---|
| E1 | Medium | Cache-bust table (guide §12.2) hardcodes 5 version numbers; it went stale once already (F4) and covers only 5 of ~20+ versioned assets in `hooks.py`. It will rot again on the next deploy. | Replace the table with one line: "compare loaded asset URLs against `construction/hooks.py` (source of truth)". Do this before the *second* client deployment. |
| E2 | Medium | Scope Context runner (`test_scope_context.py`, T-001…T-017) is a manual runner — invisible to `bench run-tests`, so future regressions there won't fail CI. | Wrap T-001…T-017 in a `unittest.TestCase` so it joins standard runs. |
| E3 | Low | First-run dead-end risk: a non-admin who skips guide §1 (enable Scope Context + pick project) hits a throw only *on save* of a new BOQ Header, with no visible path forward on the form itself. | Add a pre-save form-level banner/hint on BOQ Header when scope project is missing ("Set Project in top bar first"). |
| E4 | Low | Known gaps disclosed in Appendix B (cost templates applied manually; estimation reports service-layer only) are honest but must be communicated as roadmap items, or the client will file them as defects. | Include Appendix B items verbatim in the client UAT pack as "planned, not defects". |
| E5 | Low | `AGENTS.md` header still says latest commit `698ea94` / 191 commits — stale vs actual `88493fc`. Cosmetic but confuses future agent sessions. | Update AGENTS.md identity block at next commit. |
| E6 | Low | Guide §12.2 verification assumes users know DevTools; acceptable for pilot, heavy for business users. | Move cache-check instructions into the admin runbook instead of the end-user guide. |

## 4. Risks to Manage at Deployment

| # | Risk | Mitigation |
|---|---|---|
| R1 | Bench services (Redis cache/queue) were down in this environment; any test/smoke run silently fails without them. | Before production deploy: verify `redis_cache` (13000) and `redis_queue` (11000) respond to PING; add this to the runbook pre-flight. |
| R2 | Production migrate mutates schema. | Take `bench --site <site> backup --with-files` immediately before `migrate`. |
| R3 | Single-user smoke test won't exercise the permission matrix. | UAT with three role logins minimum: Construction Owner, Project Manager, Site Engineer (validates guide §9.2 read-only/no-access rules). |

## 5. Deployment Sequence (for GM's operations team)

```bash
# Pre-flight
redis-cli -p 13000 ping && redis-cli -p 11000 ping   # both must PONG
bench --site <production-site> backup --with-files

# Deploy
bench --site <production-site> migrate
bench build --app construction
bench restart
```

Then execute the acceptance smoke test from the sign-off with a real non-administrator user:
select Scope Context → create + lock BOQ Header → create omission VO → confirm omitted item cannot be selected in a new transaction or VO line.

## 6. Handoff Statement

The application at commit `88493fc`, together with User Guide v1.3, is internally consistent and independently revalidated: **175/175 automated checks pass**, all prior audit findings are verifiably remediated in code, and migration/build gates pass. I recommend the General Manager issue this release to the client for supervised UAT under risks R1–R3 above. Enhancement items E1–E6 are scheduled follow-ups and do not gate this release.

**Consultant:** Approved — handoff issued 2026-08-21.
