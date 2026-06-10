# VO Quantity Revision — Manual UI Test Plan

> **Who:** End user / QA tester  
> **Where:** Frappe Desk in a browser  
> **What:** Verify Variation Orders with quantity revision end-to-end  
> **Estimated time:** 30 minutes

---

## Prerequisites

- [ ] Logged in as **Administrator** or **Project Manager**
- [ ] A **Project** exists in your ERPNext site
- [ ] Feature flag `enable_variation_orders` is **ON**  
      → Go to *Construction Settings* → check **Enable Variation Orders**

---

## Part 1: Create & Lock a BOQ

### Step 1 — Create BOQ Header
1. Go to **BOQ Header → New**
2. Fill in:
   - **Title:** `QA Test BOQ`
   - **Project:** select any project
   - **BOQ Type:** `Tender`
3. **Save**

### Step 2 — Add BOQ Structure (WBS group)
1. Go to **BOQ Structure → New**
2. Fill in:
   - **BOQ Header:** select your QA Test BOQ
   - **Title:** `Site Works`
   - **Is Group:** ✅ checked
3. **Save**

### Step 3 — Add BOQ Items
1. From the **Site Works** structure form, click **View BOQ Item**
2. Set:
   - **Quantity:** `100`
   - **Unit:** `Nos`
   - **Contract Unit Price:** `50`
3. **Save**
4. Go back to BOQ Structure, create another leaf:
   - **Title:** `Item 2`
   - **Quantity:** `50`
   - **Unit:** `Nos`
   - **Contract Unit Price:** `80`
   - **Save**

### Step 4 — Lock the BOQ
1. Go to **BOQ Header** → open your QA Test BOQ
2. Change status step by step:
   - [ ] **Draft → Pricing** → Save
   - [ ] **Pricing → Frozen** → Save  
   - [ ] **Frozen → Locked** → Save
3. ✅ **Verify:** Status shows **Locked**, `Locked By` and `Locked Date` are populated

### Step 5 — Verify Baseline (optional check)
1. Go to **BOQ Quantity Revision** list
2. ✅ **Verify:** Two rows exist (one per item), each with `Revision Type = Original Lock` and `Status = Approved`

---

## Part 2: Quantity Increase VO

### Step 6 — Create VO
1. On the **Locked BOQ Header** form, click **Actions → Variation Orders** (or go to Variation Order → New)
2. Create a new VO:
   - **BOQ Header:** select your locked BOQ
   - **Reason:** `Quantity increase for Item 1`
3. **Save**

### Step 7 — Add VO Line
1. In the **Lines** child table, add a row:
   - **Line Type:** `Quantity Change`
   - **BOQ Item:** select **Item 1** (the one with qty=100)
   - **Revised Qty:** `126`
   - **Revised Unit Price:** `60`
   - **Rate Change Justification:** `Quantity exceeds 25% of contract — rate renegotiated`
2. **Save**

### Step 8 — Submit to Engineer
1. Change **Status** to `Submitted`
2. **Save**

### Step 9 — Approve by Engineer
1. Change **Status** to `Approved by Engineer`
2. **Save**
3. ✅ **Verify:** `Engineer Approval Date` is populated

### Step 10 — Verify Line Locked (P0-1)
1. Try to edit **Revised Qty** on the VO line
2. ✅ **Verify:** Save fails — the line is read-only after Engineer Approval

### Step 11 — Approve by Client
1. Change **Status** to `Approved by Client`
2. Set **Client Approval Document** to any PDF file (upload one)
3. **Save**
4. ✅ **Verify:** Status = `Approved by Client`, `Client Approval Date` populated

### Step 12 — Verify Revision
1. Go to **BOQ Quantity Revision** list
2. ✅ **Verify:** A new revision exists with:
   - `Revision Type = Increase Above 25%`
   - `Revised Qty = 126`
   - `Delta Qty = 26`
   - `Rate Change Triggered = ✅`

### Step 13 — Verify Item Updated
1. Go to **BOQ Item** → open **Item 1**
2. ✅ **Verify:**
   - `Original Qty = 100` (unchanged from contract)
   - `Current Revised Qty = 126`
   - `Current Revised Unit Price = 60`

---

## Part 3: Quantity Decrease VO

### Step 14 — Create Decrease VO
1. Create a new **Variation Order** (same BOQ Header)
   - **Reason:** `Quantity decrease for Item 1`
2. Add a line:
   - **Line Type:** `Quantity Change`
   - **BOQ Item:** Item 1
   - **Revised Qty:** `90`
3. **Save**

### Step 15 — Approve
- [ ] Status → `Submitted`
- [ ] Status → `Approved by Engineer`
- [ ] Set **Client Approval Document** → PDF
- [ ] Status → `Approved by Client`

### Step 16 — Verify
1. Open **Item 1** again
2. ✅ **Verify:** `Current Revised Qty = 90`
3. Go to **BOQ Quantity Revision** → filter by Item 1
4. ✅ **Verify:** Three revisions exist (Original Lock + Increase + Decrease)

---

## Part 4: Omission VO

### Step 17 — Create Omission VO
1. Create a new **Variation Order**
   - **Reason:** `Omit Item 2`
2. Add a line:
   - **Line Type:** `Omission`
   - **BOQ Item:** Item 2
   - **Revised Qty:** auto-set to `0`
3. **Save**

### Step 18 — Approve
- [ ] Status → `Submitted`
- [ ] Status → `Approved by Engineer`
- [ ] Set **Client Approval Document** → PDF
- [ ] Status → `Approved by Client`

### Step 19 — Verify
1. Open **Item 2**
2. ✅ **Verify:** `Current Revised Qty = 0`
3. ✅ **Verify:** `Original Qty` still shows original contract quantity (not zeroed)

### Step 20 — Verify Selector Gate
1. Go to **BOQ Item** list for this BOQ Header
2. ✅ **Verify:** Item 2 is hidden from dropdowns when `exclude_zero_revised` is active
3. (Behind the scenes: transaction forms should not show omitted items)

---

## Part 5: New Variation Item VO

### Step 21 — Create New Item VO
1. Create a new **Variation Order**
   - **Reason:** `Add new scope item`
2. Add a line:
   - **Line Type:** `New Item`
   - **BOQ Structure:** select the **Site Works** group
   - **Title:** `Additional Painting Works`
   - **Unit:** `Sqm`
   - **Revised Qty:** `15`
   - **Revised Unit Price:** `120`
   - **Rate Change Justification:** `New scope item`
3. **Save**

### Step 22 — Approve
- [ ] Status → `Submitted`
- [ ] Status → `Approved by Engineer`
- [ ] Set **Client Approval Document** → PDF
- [ ] Status → `Approved by Client`

### Step 23 — Verify Variation Item
1. Go to the VO Line — ✅ **Verify:** `Created BOQ Item` and `Created BOQ Structure` are populated
2. Open the **BOQ Item** from `Created BOQ Item`
3. ✅ **Verify:**
   - `Is Variation Item = ✅`
   - `Original Qty = 0`
   - `Current Revised Qty = 15`
   - `Current Revised Unit Price = 120`

### Step 24 — Verify No item_code Required
1. Look at the VO Line form
2. ✅ **Verify:** There is NO `Item Code` field — it was removed from the schema

---

## Part 6: Verify Totals & Idempotency

### Step 25 — Verify BOQ Header Totals
1. Open your **BOQ Header**
2. ✅ **Verify:**
   - `Total Contract Value` = original contract sum (unchanged)
   - `Total Revised Value` > `Total Contract Value` (includes variation items)

### Step 26 — Verify Idempotency (P0-4)
1. Open the Client-Approved **Quantity Increase VO**
2. Click **Save** again (without any changes)
3. ✅ **Verify:** No duplicate revisions created
4. Check **BOQ Quantity Revision** list — counts should be unchanged

### Step 27 — Final UI Check
1. Go to **BOQ Header** form
2. ✅ **Verify:** **Actions → Variation Orders** button is visible
3. Click it → ✅ **Verify:** All 4 VOs appear in the list

---

## Summary

| Part | Steps | Status |
|------|-------|--------|
| Part 1: Create & Lock BOQ | 1–5 | ☐ |
| Part 2: Quantity Increase VO | 6–13 | ☐ |
| Part 3: Quantity Decrease VO | 14–16 | ☐ |
| Part 4: Omission VO | 17–20 | ☐ |
| Part 5: New Variation Item VO | 21–24 | ☐ |
| Part 6: Totals & Idempotency | 25–27 | ☐ |
| **Total** | **27 steps** | **☐ /27** |

**Pass mark:** All 27 steps pass  
**Tested by:** _________________  
**Date:** _________________
