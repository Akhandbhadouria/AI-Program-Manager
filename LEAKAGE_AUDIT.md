# OPERATIONAL LEAKAGE AUDIT & ROOT CAUSE ANALYSIS (DELIVERABLE A)

**Company:** Bambinos.live  
**Role:** AI Program Manager (Operations) Take-Home Assignment  
**Audit Scope:** 5 Production Datasets (`invoices`, `faculty_form_unapproved`, `booking_requests`, `class_schedule_bookings`, `reference_active_batches_and_students`)  
**Audit Date:** 2026-11-05  
**Data Integrity Rule:** Purely deterministic analysis based strictly on raw data; zero fabricated SLA metrics or assumptions.

---

## 1. Executive Summary & Funnel Leakage

An exhaustive audit of the 5 operational datasets reveals **catastrophic operational leakage** in the student renewal lifecycle. While the sales and payment capture funnel functions well (11 out of 13 renewal payments successfully collected, 1 partial installment collected), **only 1 student out of 13 (7.69% of all renewals, 9.09% of paid renewals) has been successfully scheduled into class sessions.**

The remaining **90.91% of paid renewals are stranded** at various stages across educator submission omissions, manual operational review backlogs, batch capacity limits, contact mismatches, and data integrity errors.

### The Renewal Pipeline Leakage Funnel

```
[Stage 1: Invoices Generated]                13 Invoices (100%)
      │
      ├─► Payment Succeeded:                 11 Invoices (84.6%)
      ├─► Partially Paid (Installment 1):     1 Invoice  (7.7%)   ──► Stranded (Invoice 84909)
      └─► Payment Failed (Uncollected):       1 Invoice  (7.7%)   ──► False Renewal Form (Invoice 84911)
      │
[Stage 2: Educator Form Submission]         11 Invoices Paid
      │
      ├─► Teacher Form Submitted:             8 Invoices (72.7%)
      ├─► Teacher Form Has Wrong Key:         1 Invoice  (9.1%)   ──► Disconnected (Form 3313 ➔ Ghost 84931)
      ├─► Duplicate Form Submitted:           1 Invoice  (9.1%)   ──► Duplicate Confusion (Forms 3308 & 3309)
      └─► Teacher NEVER Submitted:            2 Invoices (18.2%)  ──► Complete Black Hole (Invoices 84906, 84910)
      │
[Stage 3: Ops Review & Approval]             10 Submitted Forms
      │
      ├─► Approved by Ops:                    4 Forms (40.0%)
      └─► Stuck in "Pending" Queue:           6 Forms (60.0%)     ──► 4+ Days Aging / Unreviewed
      │
[Stage 4: Batch Allocation Request]          4 Approved Forms
      │
      ├─► Batch Allocated:                    1 Request  (25.0%)
      ├─► Stalled in Allocation Queue:        1 Request  (25.0%)  ──► Seat open in 9202, Ops idle (Req 5502)
      ├─► Blocked: Batch Full:                1 Request  (25.0%)  ──► 6/6 Capacity Exhausted (Req 5505)
      └─► Blocked: Batch Change Requested:    1 Request  (25.0%)  ──► No Weekend Batch Mapped (Req 5512)
      │
[Stage 5: Class Slots Scheduled]             1 Completed Request
      │
      └─► End-to-End Success:                 1 Student Scheduled (Student 68101, Invoice 84901)
```

---

## 2. Quantitative Operational Metrics

The table below provides exact, measured operational metrics based on timestamps present in the datasets. Following the strict development guidelines, **metrics where timestamps are unavailable or records remain uncompleted are explicitly designated as uncalculated/censored**, avoiding fabricated performance figures.

| Metric | Measured Value | Sample Size / Basis | Definition / Calculation Method | Status & Remarks |
|---|---|---|---|---|
| **Orphaned Invoice Rate (Strict Join)** | **27.27%** | 3 / 11 Paid Invoices | `Paid Invoices with NO matching faculty_form on invoice_id` / `Total Paid Invoices` | Invoices 84906, 84910 have no form. Invoice 84913 has form with typo (`84931`). |
| **Orphaned Invoice Rate (Relinked)** | **18.18%** | 2 / 11 Paid Invoices | `Paid Invoices with NO faculty form anywhere` / `Total Paid Invoices` | Invoices 84906 & 84910 have zero teacher submissions. |
| **Unscheduled Booking Rate (Request Level)** | **75.00%** | 3 / 4 Booking Requests | `Requests with batch_allocated == 'No' or class_slots == 0` / `Total Booking Requests` | Requests 5502, 5505, and 5512 have zero class schedule slots created. |
| **Unscheduled Renewal Rate (Invoice Level)** | **90.91%** | 10 / 11 Paid Invoices | `Paid Invoices with 0 class schedule bookings` / `Total Paid Invoices` | Only 1 of 11 paying students has been scheduled. |
| **Duplicate Request Rate** | **8.33%** | 1 / 12 Faculty Forms (9.09% of invoices with forms) | `Duplicate Form Submissions for Same Invoice` / `Total Faculty Forms` | Educator submitted Forms 3308 and 3309 for Invoice 84908 within 5 min 12 sec. |
| **Data Mismatch Rate (Payer Contact)** | **7.69%** | 1 / 13 Invoices | `Invoices where contact details differ from Student Master Profile` / `Total Invoices` | Invoice 84904: Mother paid (`+91-9844XXXX77`), registered profile is Father (`+91-9844XXXX04`). |
| **Data Mismatch Rate (Overall)** | **30.77%** | 4 / 13 Invoices | `Invoices affected by contact, amount, foreign-key, or status mismatch` | Invoices 84904 (contact), 84909 (amount), 84911 (failed payment), 84913 (foreign key). |
| **Teacher Submission Delay (Mean)** | **29.25 minutes** | n = 10 matched paid forms | `ff.created_at - inv.paid_at` for clean paid pairs | Fast educator response (~0.49 hours). Min: 14.8 min, Max: 49.8 min, Median: 27.07 min. |
| **Teacher Submission Delay (Unsubmitted)** | *Cannot be calculated* | n = 2 paid invoices (84906, 84910) | Form was never submitted as of data cutoff | Delay is currently infinite / uncalculated; educator never notified. |
| **Approval Turnaround Time (Mean)** | **95.00 minutes** | n = 4 approved forms | `ff.approved_at - ff.created_at` for Approved records | Average of 1.58 hours. Min: 45.0 min (3301), Max: 150.0 min (3305), Median: 92.5 min. |
| **Approval Turnaround Time (Pending Queue)** | *Cannot be calculated* | n = 8 pending forms | Form remains pending; `approved_at` is NULL | Censored metric. Current aging is between **48 hours and 72+ hours** without decision. |
| **Booking Allocation Turnaround Time** | **30.00 minutes** | n = 1 allocated request | `br.allocated_at - br.created_at` for Request 5501 | Only 1 request was ever allocated. Other 3 requests have `allocated_at = NULL`. |
| **Payment-to-Schedule Turnaround Time** | **104.72 minutes** (~1.75 hrs) | n = 1 completed renewal | `csb.created_at - inv.paid_at` for Invoice 84901 | **Only 1 student ever completed this journey.** For 10 paid students, metric is uncalculated / halted. |

---

## 3. Comprehensive Failure Modes & Leakage Audit Matrix

The audit identified **10 primary operational failure modes** across the five tables. Each failure mode is cataloged below with exact data evidence, business impact, root cause, and recommended resolution:

### Failure 1: Teacher Non-Submission / Black Hole Invoices
* **Failure Code:** `ORPHAN_INVOICE_MISSING_FORM`
* **Affected Table:** `1_invoices.csv` (Invoices 84906, 84910)
* **Number of Affected Records:** 2 records (18.18% of paid renewals; Net Revenue: INR 29,000)
* **Root Cause:** Complete process disconnection between payment capture and teacher notification. When parents pay via Razorpay/Stripe, no automated webhook notifies the assigned educator (Ms. Rhea B*** for 84906; Coach Arvind K*** for 84910). The educator is unaware of the renewal payment, so no faculty form is submitted.
* **Business Impact:** High-value customers (including international Stripe customer paying INR 18,000) experience zero fulfillment. Ops has zero visibility because unapproved forms drive the Ops queue. High risk of parent churn, dispute, and brand degradation.
* **Resolution Type:** **Automated**
* **Recommended Resolution:**
  1. Trigger automated n8n webhook on `invoices.payment_status == 'Paid'` to send an instant WhatsApp/Slack prompt to the educator with a pre-filled renewal link.
  2. Implement an auto-generation fallback: if teacher does not submit within 2 hours, auto-generate a provisional faculty form based on `reference_active_batches_and_students.csv`.

---

### Failure 2: Foreign Key Transposition / Disconnected Records
* **Failure Code:** `FOREIGN_KEY_TYPO_DISCONNECTED`
* **Affected Table:** `2_faculty_form_unapproved.csv` (Form 3313 referencing ghost Invoice 84931) ↔ `1_invoices.csv` (Invoice 84913)
* **Number of Affected Records:** 1 record (Student 68113, Net Revenue: INR 11,500)
* **Root Cause:** Manual, unvalidated text entry in teacher form interface. Teacher Mary M*** entered invoice number `84931` instead of `84913` (transposition typo). The form does not validate the entered invoice ID against the invoice database before submission.
* **Business Impact:** Invoice 84913 appears orphaned (paid but no form); Form 3313 appears orphaned (form submitted with non-existent invoice). Neither gets approved, stalling the renewal indefinitely.
* **Resolution Type:** **Automated**
* **Recommended Resolution:**
  1. **Immediate Engine Fix:** Deterministically re-link records when `student_id`, `class_id`, `educator_id`, and `net_amount` match exactly between an orphan invoice and orphan form.
  2. **Preventative Fix:** Replace free-text invoice input in teacher portal with a dropdown populated only with unfulfilled, paid invoices for that teacher's students.

---

### Failure 3: Financial Leakage Risk / Form Submitted on Failed Payment
* **Failure Code:** `PAYMENT_FAILED_UNCOLLECTED`
* **Affected Table:** `1_invoices.csv` (Invoice 84911) ↔ `2_faculty_form_unapproved.csv` (Form 3311)
* **Number of Affected Records:** 1 record (Student 68111, Listed Amount: INR 12,000)
* **Root Cause:** Process loophole. Educator Simran D*** submitted Form 3311 noting: *"Parent shared UPI processing screenshot"*. However, Razorpay gateway rejected the transaction (`payment_status = Failed`, `gateway_payment_id = NULL`, `paid_at = NULL`). The educator accepted an unconfirmed screenshot without waiting for LMS billing sync.
* **Business Impact:** **Direct financial leakage.** If Ops approves this form based on teacher submission, Bambinos provides 24 free classes (worth INR 12,000) for uncollected revenue.
* **Resolution Type:** **Automated**
* **Recommended Resolution:**
  1. Hard validation rule in Auto-Approval Engine: **Strictly reject / block any form where `invoices.payment_status != 'Paid'`**. LLMs must never override this.
  2. Auto-dispatch an SMS/WhatsApp payment retry link to parent (+91-9811XXXX11) with Razorpay order details.
  3. Send an automated notification to Educator 1125: *"Payment for student 68111 failed at gateway. Please do not confirm class schedule until payment receipt is generated."*

---

### Failure 4: Installment Amount Mismatch & Partial Payment Ambiguity
* **Failure Code:** `PARTIAL_PAYMENT_AMOUNT_MISMATCH`
* **Affected Table:** `2_faculty_form_unapproved.csv` (Form 3310) ↔ `1_invoices.csv` (Invoice 84909)
* **Number of Affected Records:** 1 record (Student 68109, Net Collected: INR 5,250 of INR 10,500)
* **Root Cause:** 
  1. Data entry discrepancy: Educator recorded full standard course fee (`amount_paid = 10,500`), while invoice collected was only `Installment_1_of_2` (`net_amount = 5,250`).
  2. Business policy gap: Ops has no documented standard operating procedure (SOP) on whether partial payment entitles a student to provisional batch booking (e.g., 12 sessions) or requires 100% full collection before booking.
* **Business Impact:** Form sits in "Pending" limbo for days while Ops executives hesitate. Student's classes are stalled despite paying half the tuition on time.
* **Resolution Type:** **Human Review** (Policy Decision) + **Automated Execution**
* **Recommended Resolution:**
  1. Formalize SOP: Authorize provisional booking of **12 sessions** for Installment 1 payments.
  2. Engine reconciles `amount_paid` against `net_amount`, updates booking request to 12 sessions, and schedules an automated payment reminder 7 days before Session 12 for Installment 2.

---

### Failure 5: Duplicate Renewal Submissions (Race Condition)
* **Failure Code:** `DUPLICATE_RENEWAL_REQUEST`
* **Affected Table:** `2_faculty_form_unapproved.csv` (Forms 3308 and 3309)
* **Number of Affected Records:** 2 form records representing 1 invoice (Invoice 84908, Student 68108)
* **Root Cause:** Frontend lacks submission idempotency or submit button debouncing. Educator Acharya Nancy S*** submitted Form 3308 at 08:30:00, then re-submitted identical Form 3309 at 08:35:12 (5 minutes 12 seconds later), likely due to a lack of immediate visual confirmation on the portal.
* **Business Impact:** Ops executive confusion over which record to approve; risk of duplicate booking requests, double seat reservations in LMS, or accidental double cancellation.
* **Resolution Type:** **Automated**
* **Recommended Resolution:**
  1. Automated deduplication rule: When multiple pending forms share the same `(invoice_id, student_id)`, preserve the earliest timestamp (`id: 3308`) and automatically archive subsequent duplicates (`id: 3309`) with status `Archived_Duplicate`.
  2. Add database constraint: `UNIQUE (invoice_id)` on `faculty_form` table.

---

### Failure 6: Operational Approval Paralysis / Queue Backlog
* **Failure Code:** `UNPROCESSED_APPROVAL_QUEUE`
* **Affected Table:** `2_faculty_form_unapproved.csv` (Forms 3303, 3307)
* **Number of Affected Records:** 2 records (Clean renewals: Students 68103, 68107; Net Revenue: INR 16,600)
* **Root Cause:** Over-reliance on manual human review. Even when an invoice is 100% paid, student ID matches, class ID matches, fee matches, and batch has open capacity (e.g., Student 68103 in batch 9203 with 3 open seats), the record sits in `Pending` awaiting an Ops executive's manual click.
* **Business Impact:** Pure artificial latency. Student 68103 has been waiting over 72 hours post-payment for approval. Slow fulfillment directly damages customer satisfaction (NPS).
* **Resolution Type:** **Automated**
* **Recommended Resolution:**
  1. Deploy deterministic Auto-Approval Engine: If `payment_status == 'Paid'`, `amount_paid == net_amount`, `student_id == ref.student_id`, and `active_students_count < max_batch_size`, auto-approve instantly (`approved_by = 'auto_engine'`).

---

### Failure 7: Batch Capacity Exhaustion / Seat Deficit
* **Failure Code:** `BATCH_CAPACITY_EXCEEDED`
* **Affected Table:** `3_booking_requests.csv` (Request 5505) ↔ `reference` (Batch 9205)
* **Number of Affected Records:** 1 record (Student 68105, Batch 9205)
* **Root Cause:** Lack of pre-payment seat reservation and real-time inventory locking. Student paid INR 11,000 to renew in existing batch 9205 (`CM-G4-Batch-D`). Ops approved the form, but booking request failed with `Failed_Batch_Full` because active students count reached 6/6 (`max_batch_size = 6`).
* **Business Impact:** Parent paid for renewal but student cannot take classes. Friction occurs when Ops contacts parent after payment to say their batch is full. High refund and chargeback risk.
* **Resolution Type:** **Human Review** (Batch Rescheduling / Educator Approval)
* **Recommended Resolution:**
  1. Trigger immediate exception workflow to Ops lead.
  2. Provide Ops with two instant resolution options:
     - **Option A:** Approve educator override to expand batch capacity from 6 to 7 (if pedagogy allows).
     - **Option B:** Automated WhatsApp template sent to parent showing open parallel Chess batches (e.g., Batch 9210 which has 1 seat open).

---

### Failure 8: Stalled Batch Allocation Despite Available Seat
* **Failure Code:** `STALLED_BATCH_ALLOCATION`
* **Affected Table:** `3_booking_requests.csv` (Request 5502) ↔ `reference` (Batch 9202)
* **Number of Affected Records:** 1 record (Student 68102, Invoice 84902)
* **Root Cause:** Disconnected process handoff between Ops approval and batch booking. Ops approved Form 3302 on 2026-11-01 at 17:00:00, creating Booking Request 5502. The student requested to continue in same batch 9202 (`BM-G5-Batch-C`). Batch 9202 currently has 5 active students out of 6 max capacity (**1 seat is completely open!**). Yet, the request has sat unallocated in `Pending_Batch_Allocation` for **over 4 days** because no automated rule booked the open seat.
* **Business Impact:** Severe service delivery breakdown. Parent's card was charged INR 10,500 on Nov 1st; as of Nov 5th, no class schedule exists.
* **Resolution Type:** **Automated**
* **Recommended Resolution:**
  1. Implement automated allocation rule: If `continue_same_batch == 'Yes'` and `batch.active_students_count < batch.max_batch_size`, auto-allocate batch immediately upon form approval and generate class schedule bookings without waiting for manual human ops.

---

### Failure 9: Batch Change Preference Without Target Slot
* **Failure Code:** `UNALLOCATED_BATCH_CHANGE`
* **Affected Table:** `3_booking_requests.csv` (Request 5512) ↔ `2_faculty_form` (Form 3312)
* **Number of Affected Records:** 1 record (Student 68112, Invoice 84912)
* **Root Cause:** Parent requested a batch change (`continue_same_batch = 'No'`, preferred days: `Sat,Sun`, preferred time: `11:00:00`). Ops approved the form, but Booking Request 5512 was created with `classbatch_id = NULL` and set to `Awaiting_Parent_Batch_Selection`. The system lacks automated matching to find batches corresponding to the parent's preferred time.
* **Business Impact:** Stalled transition. Renewal is approved in principle, but student is effectively unscheduled and cannot resume classes.
* **Resolution Type:** **Human Review** (Assisted Match) + **Automated Messaging**
* **Recommended Resolution:**
  1. Automated lookup: Search LMS batch table for Class 301 (`Little Yogi Gita Level 1`) batches running on Sat/Sun at 11:00 AM with capacity < 6.
  2. Dispatch WhatsApp message to parent with the specific matching batch options and 1-click confirmation buttons.

---

### Failure 10: Payer Contact Profile Divergence (Cross-Parent Payment)
* **Failure Code:** `PAYER_CONTACT_MISMATCH`
* **Affected Table:** `1_invoices.csv` (Invoice 84904) ↔ `reference` (Student 68104)
* **Number of Affected Records:** 1 record (Student 68104, Student Name: `An***a Iy***r`)
* **Root Cause:** Cross-parent payment. Invoice contains mother's details (`parent_name = Ri***u Iy***r`, `mobile = +91-9844XXXX77`, `email = ri***u.iy***@gmail.com`), whereas student registration profile contains father's details (`parent_name = Su***h Iy***r`, `mobile = +91-9844XXXX04`, `email = su***h.iy***@outlook.com`). The educator explicitly noted in Form 3304 remarks: *"Mother paid from her number"*.
* **Business Impact:** If an automated reconciliation system uses a naive phone-number join, this record fails completely, resulting in false rejection or manual escalation.
* **Resolution Type:** **Human Review** (One-time audit) + **Master Data Update**
* **Recommended Resolution:**
  1. Check educator remarks field for secondary payer confirmation.
  2. Add mother's phone and email as `secondary_contact` on Student 68104's master profile in reference table.
  3. Approve Form 3304 and proceed with renewal.

---

## 4. End-to-End Audit of All 13 Renewal Invoices

The table below traces the exact journey of every invoice present in the dataset, documenting its current terminal state and operational diagnosis:

| Invoice ID | Student ID | Student Name | Payment Status | Net Paid (INR) | Faculty Form ID | Form Status | Booking Req ID | Request Status | Classes Booked | Journey Outcome & Diagnosis |
|---|---|---|---|---|---|---|---|---|---|---|
| **84901** | 68101 | Aa***v Sh***a | Paid | 12,000.00 | 3301 | Approved | 5501 | Completed | 2 slots | **✅ Complete Success:** Only end-to-end completed renewal in entire dataset. |
| **84902** | 68102 | Di***a Na***r | Paid | 10,500.00 | 3302 | Approved | 5502 | Pending_Batch_Allocation | 0 slots | **❌ Stalled in Ops Allocation:** Form approved Nov 1st; seat open in batch 9202 (5/6); left unallocated for 4 days. |
| **84903** | 68103 | Ka***r Ve***a | Paid | 9,000.00 | 3303 | Pending | None | Not_Created | 0 slots | **❌ Stranded in Ops Approval:** 100% clean record; batch 9203 has 3 open seats; awaiting manual approval since Nov 2nd. |
| **84904** | 68104 | An***a Iy***r | Paid | 12,000.00 | 3304 | Pending | None | Not_Created | 0 slots | **⚠️ Contact Mismatch Queue:** Mother paid; phone/email differs from father's master profile; awaiting manual review. |
| **84905** | 68105 | Re***h Pa***l | Paid | 11,000.00 | 3305 | Approved | 5505 | Failed_Batch_Full | 0 slots | **❌ Blocked by Capacity:** Form approved; batch 9205 is full (6/6); renewal halted without alternative batch offer. |
| **84906** | 68106 | Zo***a Kh***n | Paid | 18,000.00 | None | Not_Submitted | None | Not_Created | 0 slots | **❌ Black Hole (No Form):** Full payment via Stripe Nov 2nd; teacher Rhea B*** never submitted form; unfulfilled for 3 days. |
| **84907** | 68107 | Vi***n Jo***i | Paid | 7,600.00 | 3307 | Pending | None | Not_Created | 0 slots | **⚠️ Discount Audit Pending:** 20% discount (INR 1,900); amount matches invoice; pending manual ops approval since Nov 2nd. |
| **84908** | 68108 | Si***a Ma***a | Paid | 22,000.00 | 3308, 3309 | Pending (Dup) | None | Not_Created | 0 slots | **⚠️ Duplicate Submission:** Teacher Nancy S*** submitted two identical forms within 5 minutes; neither processed. |
| **84909** | 68109 | Ad***t Ku***i | Partially_Paid | 5,250.00 | 3310 | Pending | None | Not_Created | 0 slots | **⚠️ Partial Payment Mismatch:** Installment 1 paid (INR 5,250); teacher logged INR 10,500; blocked by policy ambiguity. |
| **84910** | 68110 | My***a Re***y | Paid | 11,000.00 | None | Not_Submitted | None | Not_Created | 0 slots | **❌ Black Hole (No Form):** Full payment Nov 3rd; Coach Arvind never submitted form; zero ops visibility. |
| **84911** | 68111 | Is***n Gu***a | Failed | 12,000.00 | 3311 | Pending | None | Not_Created | 0 slots | **🚨 Financial Leakage Trap:** Payment failed at gateway; teacher submitted form on unconfirmed screenshot; must reject. |
| **84912** | 68112 | Ta***a Me***n | Paid | 9,000.00 | 3312 | Approved | 5512 | Awaiting_Parent_Batch_Selection | 0 slots | **⚠️ Stalled on Batch Change:** Approved Nov 3rd; parent wants Sat/Sun 11 AM; request sitting with NULL batch_id. |
| **84913** | 68113 | De***a Me***a | Paid | 11,500.00 | 3313 (Ghost) | Pending | None | Not_Created | 0 slots | **❌ Disconnected Foreign Key:** Teacher entered invoice 84931 instead of 84913; invoice and form stranded as separate orphans. |

---

## 5. Root Cause Analysis: The 4 Dimensions

To engineer permanent operational fixes, failures are categorized across the four operational dimensions:

```
                  ┌──────────────────────────────────────────────┐
                  │          ROOT CAUSE CLASSIFICATION           │
                  └──────────────────────────────────────────────┘
                                  │
         ┌────────────────┬───────┴────────┬────────────────┐
         ▼                ▼                ▼                ▼
     [ PEOPLE ]      [ PROCESS ]      [ SYSTEMS ]       [ DATA ]
   - Teacher form   - No partial-    - No payment-    - Payer contact
     omission         payment SOP      teacher hook     mismatch
   - Manual data    - No capacity    - No idempotency - Foreign key
     entry typos      reservation      lock on forms    typos
   - Screenshot     - Manual gate    - Unautomated    - Form amount
     acceptance       bottleneck       batch booking    discrepancy
```

### 1. People (Faculty & Operations Personnel)
* **Educator Reliance on Informal Proof:** Educators accepting WhatsApp payment screenshots from parents (Invoice 84911) without checking billing portal status.
* **Manual Data Entry Errors:** Educators typing numeric invoice numbers by hand rather than selecting from authenticated student rosters (Form 3313 typo: 84931).
* **Operational Inertia:** Operations team taking 4+ days to allocate open seats that are already available in reference batches (Booking Request 5502 in Batch 9202).

### 2. Process & SOP Gaps
* **Missing Installment Fulfillment SOP:** Lack of defined policy regarding whether installment payers get partial class blocks (e.g. 12 classes) or must be held until final payment.
* **No Pre-Payment Seat Reservation:** Inability to reserve a seat in high-demand batches before payment collection, creating post-payment capacity collisions (Batch 9205).
* **Manual Approval Bottleneck:** Requiring human ops sign-off on 100% of renewal records, even when payments, fees, and student details are completely clean.

### 3. System & Technical Architecture Gaps
* **Lack of Event-Driven Webhooks:** No automated trigger firing between payment gateway success and LMS teacher notification, causing orphaned paid invoices.
* **Lack of UI Idempotency:** Missing submit-button debounce or unique constraint on `faculty_form.invoice_id`, allowing rapid duplicate submissions (Forms 3308/3309).
* **Unautomated Batch Allocation:** Absence of rule-based batch booking service that matches clean, approved requests to open batch inventory.

### 4. Data Quality & Schema Vulnerabilities
* **Rigid Single-Contact Profiles:** Student profiles only storing one primary parent contact, causing false flags when the other parent pays.
* **Decoupled Form Pricing:** Educator forms capturing manual free-text `amount_paid` rather than inheriting the verified `net_amount` directly from `invoices`.

---

## 6. High-Priority Remediation Roadmap

Based on the findings of this operational audit, the table below defines the immediate operational priorities for Deliverable B (Reconciliation & Auto-Approval Engine):

| Priority | Action Item | Target Failure Mode | Impacted Records | Target Resolution |
|---|---|---|---|---|
| **P0 (Immediate)** | **Block Approval on Failed Invoices** | Financial Leakage (Failure 3) | Invoice 84911 (Form 3311) | Engine hard-rejects approval; issues payment recovery link to parent. |
| **P0 (Immediate)** | **Deterministic Auto-Approval for Clean Records** | Operational Backlog (Failure 6) | Invoices 84903, 84907 | Instantly auto-approve clean forms; create booking requests immediately. |
| **P0 (Immediate)** | **Auto-Allocate Available Same-Batch Seats** | Stalled Allocation (Failure 8) | Invoice 84902 (Req 5502) | Auto-allocate open seat in Batch 9202 (5/6 < 6); generate class schedule slots. |
| **P1 (High)** | **Automated Foreign-Key Reconnection** | Orphan Disconnection (Failure 2) | Invoice 84913 (Form 3313) | Re-link ghost form 3313 to invoice 84913 via student ID + class ID match; approve. |
| **P1 (High)** | **Form Deduplication Engine** | Duplicate Submissions (Failure 5) | Invoice 84908 (Forms 3308/3309) | Preserve earliest submission (3308), auto-archive duplicate (3309). |
| **P1 (High)** | **Automated Teacher Chaser / Notification Webhook** | Orphan Invoices (Failure 1) | Invoices 84906, 84910 | Fire immediate WhatsApp/Slack alerts to educators with pre-filled renewal link. |
| **P2 (Medium)** | **Cross-Parent Contact Aliasing** | Contact Mismatch (Failure 10) | Invoice 84904 (Form 3304) | Verify educator remarks, alias mother's mobile to profile, approve renewal. |
| **P2 (Medium)** | **Batch Capacity Overflow Workflow** | Batch Full Failure (Failure 7) | Invoice 84905 (Req 5505) | Send WhatsApp alternative batch options or request educator capacity override to 7. |
| **P2 (Medium)** | **Interactive Batch Selection Service** | Unallocated Change (Failure 9) | Invoice 84912 (Req 5512) | Surface Sat/Sun 11 AM slots in Class 301 for parent 1-click confirmation. |
| **P2 (Medium)** | **Installment Provisional Booking SOP** | Partial Payment (Failure 4) | Invoice 84909 (Form 3310) | Provision 12 sessions; schedule reminder for Installment 2 collection. |

---

*Audit completed and certified on 2026-11-05. All findings correspond directly with the accompanying machine-readable `leakage_analysis.csv`.*

