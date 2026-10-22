# Week 4: Pilot & Hardening Plan
## Searchable Dropdown Enhancement

**Status:** Week 4 — Pilot Deployment  
**Timeline:** Days 22–28  
**Goal:** Deploy to 5 pilot users, monitor, fix issues, make Go/No-Go decision  

---

## 1. Pilot Overview

### 1.1 Objectives

1. **Validate functionality** in real-world usage
2. **Measure performance** on production-like data
3. **Gather user feedback** on UX improvements
4. **Identify edge cases** and bugs
5. **Make Go/No-Go decision** for broader rollout

### 1.2 Success Criteria (Go/No-Go)

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| Functional tests pass | 100% | Automated + Manual checklist |
| Search latency | < 500ms* | Browser dev tools timing |
| Zero permission/security issues | 0 | Security audit + logs review |
| User satisfaction | ≥ 80% | Post-pilot survey |
| Rollback requests | 0 | Support tickets |

*Target adjusted for ERPNext Cloud network latency. Real-world may vary.

---

## 2. Pilot User Selection

### 2.1 Selection Criteria

Select **5 users** representing:

| Role | Count | Why |
|------|-------|-----|
| Senior Accountant | 1 | Heavy Journal Entry usage, can validate account search |
| AR/AP Clerk | 1 | Daily invoice processing, tests Item/Customer search |
| Procurement Officer | 1 | Purchase orders, tests Supplier search |
| Finance Manager | 1 | Review/approval workflow, management perspective |
| System Admin/Super User | 1 | Technical feedback, can troubleshoot |

### 2.2 User Requirements

- Uses ERPNext daily (≥5 transactions/day)
- Comfortable with technology
- Willing to provide feedback
- Has access to test/staging environment
- Available for 30-min kickoff meeting

### 2.3 Exclusion Criteria

- New hires (<1 month experience)
- Users with accessibility needs (Phase 2)
- Users on mobile-only (Phase 2)

---

## 3. Week 4 Schedule

### Day 22: Monday — Preparation

| Time | Task | Owner |
|------|------|-------|
| 09:00 | Select 5 pilot users | Project Lead |
| 10:00 | Send invitation emails | Project Lead |
| 11:00 | Deploy to staging environment | DevOps |
| 14:00 | Verify deployment (run smoke tests) | QA |
| 16:00 | Prepare user guide (1-pager) | UX |
| 17:00 | Schedule kickoff meeting | PM |

**Deliverable:** Staging environment ready, users confirmed

### Day 23: Tuesday — Kickoff

| Time | Task | Owner |
|------|------|-------|
| 10:00 | Kickoff meeting (30 min) | All |
| 10:30 | Demo: How to use enhanced dropdown | Dev |
| 10:45 | Distribute user guide | PM |
| 11:00 | Grant staging access to users | DevOps |
| 14:00 | Monitor initial usage (watch logs) | Dev |

**Kickoff Agenda:**
1. What changed (2 min)
2. Demo of new dropdown (5 min)
3. What to test (Journal Entry, Sales Invoice, etc.) (5 min)
4. How to report issues (3 min)
5. Feedback survey preview (2 min)
6. Q&A (10 min)

**Deliverable:** Users briefed, ready to test

### Day 24: Wednesday — Day 1 Monitoring

| Time | Task | Owner |
|------|------|-------|
| 09:00 | Check error logs from overnight | Dev |
| 10:00 | Send "How's it going?" message to users | PM |
| 12:00 | Review morning usage patterns | Dev |
| 15:00 | Check for critical issues | Dev |
| 17:00 | Daily status report | PM |

**Watch for:**
- JavaScript errors in browser console
- API errors in server logs
- Slow search responses (>1s)
- Users unable to complete transactions

**Deliverable:** Zero critical errors confirmed

### Day 25: Thursday — Feedback Collection

| Time | Task | Owner |
|------|------|-------|
| 09:00 | Send feedback survey to users | PM |
| 11:00 | 1:1 interviews with 2 users (15 min each) | UX |
| 14:00 | 1:1 interviews with 2 more users | UX |
| 16:00 | Compile feedback summary | UX |

**Feedback Survey Questions:**
1. How easy was it to find accounts/items using the new dropdown? (1-5)
2. Did the hover highlighting help you identify selections? (Yes/No)
3. Was the "— بلا —" clear option useful? (Yes/No/Don't use)
4. Did you experience any slowness? (Yes/No — describe)
5. Any other feedback or issues?

**Deliverable:** Feedback compiled, issues identified

### Day 26: Friday — Bug Fixes

| Time | Task | Owner |
|------|------|-------|
| 09:00 | Prioritize issues from feedback | Dev |
| 10:00 | Fix critical bugs (if any) | Dev |
| 14:00 | Deploy patches to staging | DevOps |
| 16:00 | Verify fixes | QA |
| 17:00 | Update pilot users on fixes | PM |

**Deliverable:** Issues resolved (or documented for Phase 2)

### Day 27: Saturday — Performance Benchmarking

| Time | Task | Owner |
|------|------|-------|
| 10:00 | Run performance test suite | QA |
| 12:00 | Document benchmark results | Dev |
| 14:00 | Compare against targets | PM |
| 16:00 | Performance report | Dev |

**Performance Tests:**
1. Search 10 accounts: measure time
2. Search 100 accounts: measure time
3. Open/close dropdown 50x: check for memory leaks
4. Test with 1000+ Chart of Accounts: measure initial load

**Deliverable:** Performance report with measurements

### Day 28: Sunday — Go/No-Go Decision

| Time | Task | Owner |
|------|------|-------|
| 10:00 | Compile all data (tests, feedback, performance) | PM |
| 11:00 | Stakeholder review meeting | All |
| 12:00 | Make Go/No-Go decision | Decision Maker |
| 14:00 | Document decision and rationale | PM |
| 15:00 | Communicate decision to team | PM |
| 16:00 | If GO: Plan Phase 2 rollout | PM |
| 16:00 | If NO-GO: Document lessons learned | PM |

**Decision Meeting Agenda:**
1. Review success criteria (15 min)
2. Present test results (10 min)
3. Present user feedback (10 min)
4. Present performance data (10 min)
5. Open discussion (15 min)
6. Decision (5 min)

**Deliverable:** Go/No-Go decision documented

---

## 4. Deployment Checklist

### 4.1 Pre-Deployment

- [ ] All Week 1-3 code merged to `main` branch
- [ ] All automated tests passing
- [ ] Manual test checklist completed
- [ ] Security review passed (no permission leaks)
- [ ] Performance benchmarks acceptable
- [ ] User guide written (1-pager)
- [ ] Rollback plan documented
- [ ] Staging environment ready

### 4.2 Deployment to Staging

- [ ] `git pull` latest code
- [ ] `bench build` to compile SCSS → CSS
- [ ] `bench migrate` to update database (if needed)
- [ ] `bench restart` to restart services
- [ ] Verify assets loading (check browser network tab)
- [ ] Run smoke tests (see below)
- [ ] Verify no console errors

### 4.3 Smoke Tests (Post-Deployment)

```bash
# 1. API test
curl -X POST https://staging-site/api/method/construction.searchable_dropdown.api.search.searchable_link_search \
  -H "Authorization: token api_key:api_secret" \
  -d '{"doctype":"Account","txt":"cash","search_fields":["account_name"]}'

# Expected: JSON array with results
```

```javascript
// 2. JS test (browser console)
console.log('Utils:', typeof construction.searchable_dropdown.utils);
console.log('Enhancer:', typeof SearchableDropdownEnhancer);

// Expected: "function" for both
```

```javascript
// 3. UI test
// Open Journal Entry → Add row → Click Account field
// Expected: Dropdown opens, hover shows blue border
```

### 4.4 Monitoring Setup

- [ ] Error logging enabled (`frappe.log_error`)
- [ ] Performance tracking enabled
- [ ] User activity monitoring (Google Analytics or internal)
- [ ] Daily log review scheduled

---

## 5. Feedback Collection

### 5.1 User Guide (1-Pager)

```
┌─────────────────────────────────────────────────────────────────┐
│         NEW: Enhanced Dropdown Search                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  What's New:                                                     │
│  • Search by code OR name (Arabic/English)                      │
│  • Hover to see selection highlighted in blue                 │
│  • Selected items show ✓ checkmark                            │
│  • Clear selection with "— بلا —"                             │
│                                                                  │
│  How to Use:                                                     │
│  1. Click in Account/Item field                                 │
│  2. Start typing (code or name)                                 │
│  3. Hover over results to see preview                           │
│  4. Click to select                                             │
│  5. Use keyboard arrows + Enter if preferred                    │
│                                                                  │
│  Questions? Contact: [support email]                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Feedback Survey Template

Create Google Form / Typeform with:

**Section 1: Usability (5 questions)**
- Rating 1-5: Overall ease of use
- Rating 1-5: Search speed
- Yes/No: Hover highlighting helpful
- Yes/No: Clear option useful
- Text: What worked well?

**Section 2: Issues (3 questions)**
- Yes/No: Encountered any errors?
- Text: Describe any issues
- Text: What could be improved?

**Section 3: General (2 questions)**
- Rating 1-5: Would you recommend this to others?
- Text: Additional comments

### 5.3 Interview Script (15 min)

1. **Show me** how you create a Journal Entry (observe)
2. **Tell me** about your experience finding accounts
3. **Did** the blue hover effect help you?
4. **Was** the "— بلا —" option useful?
5. **What** would you change or add?
6. **Any** bugs or issues to report?

---

## 6. Go/No-Go Decision Framework

### 6.1 GO Criteria (All must be met)

| # | Criterion | Threshold | Evidence |
|---|-----------|-----------|----------|
| 1 | Automated tests pass | 100% | Test output |
| 2 | Manual tests pass | 100% | Checklist signed |
| 3 | No critical bugs | 0 open P0 bugs | Issue tracker |
| 4 | No security issues | 0 | Security audit |
| 5 | Search latency | < 500ms median | Performance report |
| 6 | User satisfaction | ≥ 80% positive | Survey results |
| 7 | Users can complete tasks | 100% | Observation |

### 6.2 NO-GO Triggers (Any one triggers NO-GO)

- [ ] Critical bug preventing transaction completion
- [ ] Permission leak (users see unauthorized data)
- [ ] Search consistently > 2 seconds
- [ ] < 50% user satisfaction
- [ ] Multiple rollback requests (>2 users)
- [ ] Data corruption or loss

### 6.3 Decision Matrix

| Tests | Performance | Feedback | Decision |
|-------|-------------|----------|----------|
| Pass | Good | Positive | **GO** → Broad rollout |
| Pass | Acceptable | Mixed | **GO** → Rollout with monitoring |
| Pass | Poor | Positive | **CONDITIONAL GO** → Optimize first |
| Fail | Any | Any | **NO-GO** → Fix and re-pilot |
| Pass | Any | Negative | **NO-GO** → Reassess approach |

### 6.4 Post-Decision Actions

**If GO:**
1. Schedule Phase 2 kickoff
2. Expand to all users
3. Add more doctypes (Purchase Order, etc.)
4. Monitor for 2 weeks
5. Plan Phase 3 enhancements (tree view, etc.)

**If NO-GO:**
1. Document lessons learned
2. Decide: Fix and re-pilot OR abandon
3. If abandon: Remove form scripts, revert to native
4. Communicate decision to stakeholders
5. Sunk cost is minimal (4 weeks, no schema changes)

---

## 7. Risk Mitigation (Week 4)

| Risk | Mitigation |
|------|------------|
| Users don't test | Daily check-ins, make it easy to report issues |
| Critical bug found | Fix immediately, deploy patch same day |
| Performance poor | Measure early (Day 24), optimize or scope down |
| User resistance | Emphasize "easy to rollback," gather specific feedback |
| Scope creep | Strictly no new features during pilot |

---

## 8. Communication Plan

| Day | Communication | Audience |
|-----|---------------|----------|
| 22 | Invitation email | 5 pilot users |
| 23 | Kickoff meeting | Pilot users + team |
| 24 | "How's it going?" | Pilot users |
| 25 | Feedback survey | Pilot users |
| 26 | Daily status | Internal team |
| 27 | Performance report | Stakeholders |
| 28 | Go/No-Go decision | All stakeholders |

---

## 9. Templates & Tools

### 9.1 Daily Status Update Template

```
Subject: Searchable Dropdown Pilot - Day X Update

Status: [Green / Yellow / Red]

Testing:
- Active users: X/5
- Transactions completed: X
- Issues reported: X (link to tracker)

Performance:
- Median search time: X ms
- 95th percentile: X ms
- Errors in logs: X

Blockers: [None / List]

Next: [What's happening tomorrow]
```

### 9.2 Issue Tracker Template

| ID | User | Description | Severity | Status | Assigned |
|----|------|-------------|----------|--------|----------|
| 1 | User A | Search slow on mobile | P2 | Open | Dev |
| 2 | User B | Can't find account "XYZ" | P1 | Fixed | Dev |

---

## 10. Appendices

### A. Quick Commands

```bash
# Check logs
bench --site [site] log

# Restart
cd ~/frappe-bench && bench restart

# Build assets
bench build

# Run tests
bench --site [site] run-tests --module construction.searchable_dropdown.tests.test_search_api
```

### B. Rollback Procedure

If needed, disable by:

1. Comment out form scripts in `hooks.py`:
```python
# "journal_entry.js",
# "sales_invoice.js",
```

2. Restart bench:
```bash
bench restart
```

3. Clear browser cache for users

---

**End of Week 4 Pilot Plan**
