# Week 4 Pilot Checklist
## Daily Task Tracker

---

## Pre-Pilot (Day 22)

### Deployment
- [ ] Code merged to `main` branch
- [ ] `git pull` latest
- [ ] `bench build` executed (SCSS compiled)
- [ ] `bench migrate` completed
- [ ] `bench restart` successful
- [ ] Smoke tests passed (see below)
- [ ] 5 pilot users identified and invited
- [ ] Kickoff meeting scheduled

### Documentation
- [ ] User guide written (1-pager)
- [ ] Feedback survey created
- [ ] Interview script prepared
- [ ] Rollback procedure documented

---

## Day 23 — Kickoff

### Morning
- [ ] Kickoff meeting completed
- [ ] User guide distributed
- [ ] Staging access granted to all 5 users
- [ ] Users confirmed they can log in

### Verification
- [ ] Journal Entry form loads without errors
- [ ] Account dropdown opens
- [ ] Search returns results
- [ ] Hover effect visible (blue border)
- [ ] Selection shows checkmark

### End of Day
- [ ] No critical errors in logs
- [ ] Daily status email sent to stakeholders

---

## Day 24 — Monitoring

### Morning Check (9 AM)
- [ ] Review overnight error logs
- [ ] Check server performance metrics
- [ ] Send "How's it going?" message to users

### Midday Check (12 PM)
- [ ] Review morning usage logs
- [ ] Count transactions completed
- [ ] Check for any stuck/broken sessions

### Evening Check (5 PM)
- [ ] Verify no critical bugs reported
- [ ] Document any issues in tracker
- [ ] Send daily status update

### Key Metrics to Track
- [ ] Number of searches performed
- [ ] Average search response time
- [ ] Number of JavaScript errors
- [ ] Number of API errors
- [ ] User complaints/feedback received

---

## Day 25 — Feedback Collection

### Morning
- [ ] Feedback survey sent to all 5 users
- [ ] Reminder: Survey closes tomorrow

### Interviews
- [ ] Interview User 1 completed (15 min)
- [ ] Interview User 2 completed (15 min)
- [ ] Interview User 3 completed (15 min)
- [ ] Interview User 4 completed (15 min)
- [ ] Interview User 5 completed (15 min)

### Compilation
- [ ] Survey responses collected
- [ ] Interview notes compiled
- [ ] Feedback summary document created
- [ ] Issues prioritized (P0/P1/P2)

---

## Day 26 — Bug Fixes

### Morning
- [ ] Issues triaged and assigned
- [ ] P0 bugs fixed first
- [ ] P1 bugs fixed if time permits

### Deployment
- [ ] Fixes merged to `main`
- [ ] `bench build` executed
- [ ] Patches deployed to staging
- [ ] Fixes verified by QA

### Communication
- [ ] Users notified of fixes
- [ ] Any workarounds documented

---

## Day 27 — Performance Benchmarking

### Tests to Run

#### Test 1: Basic Search Performance
- [ ] Open Journal Entry
- [ ] Type "cash" in Account field
- [ ] Measure time to show results
- [ ] Target: < 500ms
- [ ] Record actual: _____ ms

#### Test 2: Large Dataset Performance
- [ ] Open Journal Entry
- [ ] Type "1" (matches many accounts)
- [ ] Measure time to show results
- [ ] Target: < 1000ms
- [ ] Record actual: _____ ms

#### Test 3: Memory Leak Test
- [ ] Open Journal Entry
- [ ] Open/close Account dropdown 50 times
- [ ] Check browser memory usage
- [ ] Target: No significant increase
- [ ] Record: _____ MB

#### Test 4: Concurrent Users
- [ ] Have 2-3 users search simultaneously
- [ ] Measure response times
- [ ] Target: No degradation
- [ ] Record: _____ ms average

### Results Documentation
- [ ] All tests completed
- [ ] Results documented in performance report
- [ ] Comparison against targets made

---

## Day 28 — Go/No-Go Decision

### Data Compilation (Morning)
- [ ] Test results compiled
- [ ] User feedback summarized
- [ ] Performance report finalized
- [ ] Issue tracker reviewed

### Decision Meeting (11 AM)
Attendees: Project Lead, Engineering Lead, Product Owner

Agenda:
- [ ] Review success criteria (15 min)
- [ ] Review test results (10 min)
- [ ] Review user feedback (10 min)
- [ ] Review performance data (10 min)
- [ ] Open discussion (15 min)
- [ ] Decision recorded (5 min)

### Decision Record
- [ ] Decision made: **GO** / **NO-GO** / **CONDITIONAL GO**
- [ ] Rationale documented
- [ ] Next steps defined
- [ ] All stakeholders notified

### Post-Decision Actions

**If GO:**
- [ ] Phase 2 kickoff scheduled
- [ ] Rollout timeline created
- [ ] Communication plan drafted

**If NO-GO:**
- [ ] Lessons learned documented
- [ ] Fix/re-pilot or abandon decision made
- [ ] Team debrief scheduled

---

## Success Criteria Verification

| Criterion | Target | Actual | Met? |
|-----------|--------|--------|------|
| Automated tests | 100% | _____ | ☐ |
| Manual tests | 100% | _____ | ☐ |
| Critical bugs | 0 | _____ | ☐ |
| Security issues | 0 | _____ | ☐ |
| Search latency | < 500ms | _____ | ☐ |
| User satisfaction | ≥ 80% | _____ | ☐ |
| Task completion | 100% | _____ | ☐ |

**Overall: GO / NO-GO** (circle one)

---

## Smoke Test Script

Run these tests immediately after deployment:

### Test 1: API
```bash
curl -X POST https://[site]/api/method/construction.searchable_dropdown.api.search.searchable_link_search \
  -H "Authorization: token [api_key]:[api_secret]" \
  -d '{"doctype":"Account","txt":"cash","search_fields":["account_name"]}'
```
Expected: JSON array with results

### Test 2: JavaScript (Browser Console)
```javascript
console.log(construction.searchable_dropdown.utils);
console.log(SearchableDropdownEnhancer);
```
Expected: Both return functions/objects, not undefined

### Test 3: UI
1. Open Journal Entry
2. Add row
3. Click Account field
4. Type "100"
5. Expected: Dropdown opens with results
6. Hover over first result
7. Expected: Blue border appears on left
8. Click first result
9. Expected: Selection made, checkmark visible

### Test 4: RTL
1. Add `?lang=ar` to URL
2. Open Journal Entry
3. Click Account field
4. Expected: Blue border appears on RIGHT (not left)

All tests must pass before declaring Day 22 complete.

---

**End of Checklist**
