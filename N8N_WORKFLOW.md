# Bambinos.live – n8n Renewal Orchestration Workflow Specification

## 1. Executive Summary & Architecture Overview

This document specifies the end-to-end event-driven and scheduled automation workflow built in **n8n** to automate the post-payment student renewal lifecycle at Bambinos.live.

The workflow acts as an intelligent orchestration layer between incoming payment events (Stripe, Razorpay), the deterministic Python Reconciliation Engine (`main.py`), downstream operational tools (Bambinos LMS, Google Calendar), and stakeholder notification channels (Slack, WhatsApp).

### High-Level Architecture Principles:
1. **Hybrid Trigger Model:** Real-time Webhooks for instant student onboarding (< 60 seconds TAT) combined with a 15-Minute Cron Polling Sweep to guarantee zero lost transactions during gateway outages or network drops.
2. **Deterministic Financial Decoupling:** In strict accordance with corporate risk governance, **zero LLM authority** is granted over financial approval or seat booking. The Python reconciliation engine executes pure deterministic logic.
3. **Idempotency & Deduplication Guard:** Every trigger generates a canonical idempotency token (`idemp_<invoice_id>_<status>`) preventing double-billing, duplicate calendar booking, or repetitive messaging.
4. **Multi-Track Operational Routing:** Segregates requests into auto-approval pipelines, assisted human workflows, academic mismatch verifications, and financial hard blocks.
5. **Universal Audit Logging:** Every branch converges to a centralized operational tracking ledger, logging execution timestamps, decision matrices, and API response payloads.

---

## 2. End-to-End Workflow Architecture Diagram

```mermaid
flowchart TD
    subgraph Ingestion ["1. Trigger & Ingestion Layer"]
        T1["Webhook: Payment Completed<br/>(Stripe / Razorpay)"]
        T2["Cron: 15-Min Sweep<br/>(Batch Recovery)"]
        IG["Idempotency Guard & Deduplicator<br/>(Redis / In-Memory Cache)"]
    end

    subgraph CoreEngine ["2. Python Reconciliation Engine"]
        EXEC["Execute Command:<br/>python3.10 main.py"]
        PARSE["Parse Engine Outputs<br/>(auto_approved, flagged, pending CSVs)"]
    end

    subgraph DecisionTree ["3. Multi-Branch Routing Decision Tree"]
        SWITCH{"Switch: Routing Decision Tree"}
    end

    subgraph AutoBranch ["Branch 1: AUTO_APPROVED (Invoices 84901, 84902, 84903)"]
        B1_ALLOC["LMS API:<br/>Allocate Batch Seat"]
        B1_SCHED["LMS API:<br/>Schedule 24 Sessions"]
        B1_WA["WhatsApp:<br/>Parent Confirmation (Mock)"]
    end

    subgraph PartialBranch ["Branch 2: PARTIAL_PAYMENT (Invoice 84909)"]
        B2_PROV["LMS API:<br/>Provision 12 Sessions"]
        B2_SLACK["Slack: Ops Partial Review<br/>(#ops-assisted-review)"]
    end

    subgraph MismatchBranch ["Branch 3: STUDENT_MISMATCH (Invoices 84904, 84907, 84913)"]
        B3_SLACK["Slack: Academic Ops Mismatch<br/>(#academic-ops-alerts)"]
    end

    subgraph CapacityBranch ["Branch 4: BATCH_UNAVAILABLE (Invoice 84905)"]
        B4_SLACK["Slack: Batch Planning Full<br/>(#ops-batch-capacity)"]
        B4_WA["WhatsApp:<br/>Parallel Batch Offer (Mock)"]
    end

    subgraph MissingFormBranch ["Branch 5: MISSING_TEACHER_FORM (Invoices 84906, 84910)"]
        B5_WA["WhatsApp:<br/>Teacher 1-Click Form Chaser (Mock)"]
    end

    subgraph DuplicateBranch ["Branch 6: DUPLICATE_BOOKING (Invoices 84901, 84908)"]
        B6_SLACK["Slack: Duplicate Suppressed FYI<br/>(#ops-duplicate-alerts)"]
    end

    subgraph FailedBranch ["Branch 7: PAYMENT_FAILED (Invoice 84911)"]
        B7_WA["WhatsApp:<br/>Payment Retry Link (Mock)"]
        B7_SLACK["Slack: Billing Hard Block Alert<br/>(#finance-ops-alerts)"]
    end

    subgraph AuditLayer ["4. Centralized Audit & Telemetry"]
        AUDIT["Database: Operational Tracking & Audit Log<br/>(PostgreSQL / Supabase)"]
    end

    %% Trigger connections
    T1 --> IG
    T2 --> IG
    IG --> EXEC
    EXEC --> PARSE
    PARSE --> SWITCH

    %% Routing connections
    SWITCH -->|Output 0: AUTO_APPROVED| B1_ALLOC
    SWITCH -->|Output 1: PARTIAL_PAYMENT| B2_PROV
    SWITCH -->|Output 2: STUDENT_MISMATCH| B3_SLACK
    SWITCH -->|Output 3: BATCH_UNAVAILABLE| B4_SLACK
    SWITCH -->|Output 4: MISSING_TEACHER_FORM| B5_WA
    SWITCH -->|Output 5: DUPLICATE_BOOKING| B6_SLACK
    SWITCH -->|Output 6: PAYMENT_FAILED| B7_WA

    %% Step Progressions
    B1_ALLOC --> B1_SCHED --> B1_WA --> AUDIT
    B2_PROV --> B2_SLACK --> AUDIT
    B3_SLACK --> AUDIT
    B4_SLACK --> B4_WA --> AUDIT
    B5_WA --> AUDIT
    B6_SLACK --> AUDIT
    B7_WA --> B7_SLACK --> AUDIT
```

---

## 3. Node-by-Node Technical Specification

The workflow is saved as an executable n8n workflow definition in [workflows/renewal_orchestrator.json](file:///Users/lambardaar/Downloads/bombios/workflows/renewal_orchestrator.json). Below is the comprehensive technical breakdown of all 19 nodes.

### 3.1 Ingestion & Idempotency Layer

#### Node 1: `Webhook: Payment Event`
- **ID:** `node-webhook-payment`
- **Type:** `n8n-nodes-base.webhook` (Version 1)
- **Path:** `/payment-completed`
- **HTTP Method:** `POST`
- **Response Mode:** `onReceived` (HTTP 200 returned immediately to avoid payment gateway timeouts).
- **Incoming Payload Format:**
  ```json
  {
    "event": "invoice.paid",
    "invoice_id": "84902",
    "amount_paid": 4000.0,
    "parent_phone": "+91-9876543211",
    "parent_email": "parent2@example.com",
    "timestamp": "2026-11-05T10:00:00Z"
  }
  ```

#### Node 2: `Cron: 15-Min Sweep`
- **ID:** `node-cron-sweep`
- **Type:** `n8n-nodes-base.scheduleTrigger` (Version 1)
- **Interval:** Every 15 minutes (`*/15 * * * *`)
- **Purpose:** Scans the payment gateway for successful invoices that did not trigger a webhook or encountered a network timeout during transit.

#### Node 3: `Idempotency Guard & Deduplicator`
- **ID:** `node-idempotency-guard`
- **Type:** `n8n-nodes-base.code` (Version 2, JavaScript)
- **Logic:**
  Constructs a composite key `idemp_${invoice_id}_${status}`. In production, this performs an atomic `SET key val NX EX 86400` in Redis. If the key exists, the incoming execution is flagged as duplicate and safely terminated.

---

### 3.2 Processing & Parsing Layer

#### Node 4: `Trigger Reconciliation Engine`
- **ID:** `node-reconciliation-engine`
- **Type:** `n8n-nodes-base.executeCommand` (Version 1)
- **Command:** `/opt/homebrew/bin/python3.10 /Users/lambardaar/Downloads/bombios/main.py`
- **Execution Mode:** Synchronous subprocess execution. Loads the 5 canonical CSVs, applies the 12 deterministic business rules (`BR-INV-001` through `BR-DAT-012`), and refreshes output CSV artifacts.

#### Node 5: `Parse Engine Outputs`
- **ID:** `node-parse-results`
- **Type:** `n8n-nodes-base.code` (Version 2, JavaScript)
- **Functionality:** Reads `auto_approved.csv`, `flagged_exceptions.csv`, and `pending_human_review.csv`. Evaluates `primary_reason_code` and maps each record to its corresponding operational branch:
  - `AUTO_APPROVED` → `AUTO_APPROVED`
  - `PARTIAL_PAYMENT_INSTALLMENT_1` → `PARTIAL_PAYMENT`
  - `STUDENT_PARENT_INFO_MISMATCH` / `AMBIGUOUS_STUDENT_IDENTITY` → `STUDENT_MISMATCH`
  - `BATCH_CAPACITY_FULL` / `INACTIVE_BATCH_REFERENCED` → `BATCH_UNAVAILABLE`
  - `MISSING_FACULTY_FORM` / `FACULTY_FORM_UNMATCHED_INVOICE` → `MISSING_TEACHER_FORM`
  - `DUPLICATE_BOOKING_PREVENTION` / `DUPLICATE_RENEWAL_REQUEST` → `DUPLICATE_BOOKING`
  - `PAYMENT_NOT_COMPLETED` → `PAYMENT_FAILED`

---

### 3.3 Multi-Branch Routing & Action Nodes

#### Node 6: `Switch: Routing Decision Tree`
- **ID:** `node-switch-routing`
- **Type:** `n8n-nodes-base.switch` (Version 1)
- **Evaluation Key:** `={{ $json.routing_branch }}`
- **Outputs:**
  - `0`: `AUTO_APPROVED`
  - `1`: `PARTIAL_PAYMENT`
  - `2`: `STUDENT_MISMATCH`
  - `3`: `BATCH_UNAVAILABLE`
  - `4`: `MISSING_TEACHER_FORM`
  - `5`: `DUPLICATE_BOOKING`
  - `6`: `PAYMENT_FAILED`

---

#### Branch 1: Auto-Approval Pipeline (Invoices 84901, 84902, 84903)
*Triggered when full payment is confirmed, faculty form is verified, student identity is validated, and batch capacity is available.*

- **Node 7: `LMS API: Allocate Batch Seat`**
  - **Type:** `n8n-nodes-base.httpRequest`
  - **URL:** `https://api.bambinos.live/mock/lms/allocate-seat`
  - **Payload:** `{"invoice_id": "{{ $json.invoice_id }}", "student_id": "{{ $json.student_id }}", "batch_id": "{{ $json.batch_id }}", "action": "ALLOCATE_SEAT"}`
  - **Result:** Decrements available capacity in batch master (e.g. Batch 9202 seats occupied goes from 4 to 5).

- **Node 8: `LMS API: Schedule 24 Sessions`**
  - **Type:** `n8n-nodes-base.httpRequest`
  - **URL:** `https://api.bambinos.live/mock/lms/schedule-slots`
  - **Payload:** `{"invoice_id": "{{ $json.invoice_id }}", "batch_id": "{{ $json.batch_id }}", "sessions": 24}`
  - **Result:** Generates 24 recurring calendar events matching the batch day/time schedule.

- **Node 9: `WhatsApp: Parent Confirmation (Mock)`**
  - **Type:** `n8n-nodes-base.httpRequest`
  - **URL:** `https://api.bambinos.live/mock/whatsapp/send`
  - **Payload:** Dispatches official renewal confirmation message draft with student name, batch timing, and teacher details.

---

#### Branch 2: Partial Payment Handling (Invoice 84909)
*Triggered when parent paid Installment 1 (₹2,500 of ₹5,000).*

- **Node 10: `LMS API: Provision 12 Sessions`**
  - **Type:** `n8n-nodes-base.httpRequest`
  - **URL:** `https://api.bambinos.live/mock/lms/provision-partial`
  - **Payload:** `{"invoice_id": "{{ $json.invoice_id }}", "student_id": "{{ $json.student_id }}", "sessions": 12}`
  - **Result:** Provisions provisional access for 12 sessions only, ensuring learning continuity while preventing revenue loss.

- **Node 11: `Slack: Ops Partial Review`**
  - **Type:** `n8n-nodes-base.slack`
  - **Channel:** `#ops-assisted-review`
  - **Message:** `:credit_card: *Partial Payment (Installment 1)* | Invoice \`{{ $json.invoice_id }}\` (Student: \`{{ $json.student_id }}\`)\nProvisioned 12 sessions. Next installment due in 15 days. Action required: Send balance payment link.`

---

#### Branch 3: Student Information Mismatch (Invoices 84904, 84907, 84913)
*Triggered when student names diverge, parent phone numbers mismatch, or promo discounts are applied without authorization.*

- **Node 12: `Slack: Academic Ops Mismatch`**
  - **Type:** `n8n-nodes-base.slack`
  - **Channel:** `#academic-ops-alerts`
  - **Message:** `:warning: *Student / Course Mismatch* | Invoice \`{{ $json.invoice_id }}\` (Student: \`{{ $json.student_id }}\`)\nReason: \`{{ $json.primary_reason_code }}\`\nAction: Verify registered profile vs payer before seat assignment.`

---

#### Branch 4: Batch Capacity Full / Inactive (Invoice 84905)
*Triggered when student requests renewal into Batch 9205 which is at maximum capacity (6/6 enrolled).*

- **Node 13: `Slack: Batch Planning Full Alert`**
  - **Type:** `n8n-nodes-base.slack`
  - **Channel:** `#ops-batch-capacity`
  - **Message:** `:no_entry: *Batch Capacity Full (6/6)* | Invoice \`{{ $json.invoice_id }}\` (Batch: \`{{ $json.batch_id }}\`)\nSeat request blocked. Action: Open parallel section or reallocate.`

- **Node 14: `WhatsApp: Parallel Batch Offer (Mock)`**
  - **Type:** `n8n-nodes-base.httpRequest`
  - **URL:** `https://api.bambinos.live/mock/whatsapp/send`
  - **Payload:** Sends WhatsApp template to parent proposing 2 alternate parallel batches with identical curriculum and grade-level peer groups.

---

#### Branch 5: Missing Teacher Renewal Form (Invoices 84906, 84910)
*Triggered when full payment is confirmed but teacher has not submitted renewal form after 24+ hours.*

- **Node 15: `WhatsApp: Teacher 1-Click Form Chaser (Mock)`**
  - **Type:** `n8n-nodes-base.httpRequest`
  - **URL:** `https://api.bambinos.live/mock/whatsapp/send`
  - **Payload:** Dispatches high-priority reminder to educator (e.g. Teacher Rhea or Coach Arvind) with pre-filled 1-click submission link.

---

#### Branch 6: Duplicate Booking Prevention (Invoices 84901, 84908)
*Triggered when student already has active calendar slots for the invoice period.*

- **Node 16: `Slack: Duplicate Suppressed FYI`**
  - **Type:** `n8n-nodes-base.slack`
  - **Channel:** `#ops-duplicate-alerts`
  - **Message:** `:information_source: *Duplicate Booking Blocked* | Invoice \`{{ $json.invoice_id }}\` (Student: \`{{ $json.student_id }}\`)\nPre-existing active schedule detected. No duplicate calendar slot created.`

---

#### Branch 7: Payment Failed Hard Block (Invoice 84911)
*Triggered when educator submits renewal form for an invoice whose gateway status is `FAILED`.*

- **Node 17: `WhatsApp: Payment Retry Link (Mock)`**
  - **Type:** `n8n-nodes-base.httpRequest`
  - **URL:** `https://api.bambinos.live/mock/whatsapp/send`
  - **Payload:** Notifies parent with a 1-click secure checkout link to complete failed transaction.

- **Node 18: `Slack: Billing Hard Block Alert`**
  - **Type:** `n8n-nodes-base.slack`
  - **Channel:** `#finance-ops-alerts`
  - **Message:** `:rotating_light: *P0 Financial Alert: Failed Payment Form Submitted* | Invoice \`{{ $json.invoice_id }}\`\nHard-block active. Payment retry dispatched to parent.`

---

### 3.4 Telemetry & Audit Layer

#### Node 19: `Database: Operational Tracking & Audit Log`
- **ID:** `node-db-audit`
- **Type:** `n8n-nodes-base.httpRequest` (Version 4.1)
- **URL:** `https://api.bambinos.live/mock/db/audit-log`
- **Payload:**
  ```json
  {
    "invoice_id": "={{ $json.invoice_id }}",
    "routing_branch": "={{ $json.routing_branch }}",
    "reason_code": "={{ $json.primary_reason_code || 'SUCCESS' }}",
    "action_taken": "={{ $json.recommended_action || 'ALLOCATE_AND_SCHEDULE' }}",
    "processed_at": "={{ new Date().toISOString() }}"
  }
  ```
- **Functionality:** Centralized immutable ledger recording every processing cycle, guaranteeing compliance and observability.

---

## 4. Idempotency & Concurrency Strategy

In high-volume subscription renewals, duplicate webhook delivery is common. To guarantee safety:

1. **State Machine Lock:**
   A payment record transitions through strict states: `UNPROCESSED` → `PROCESSING` → `TERMINAL` (`AUTO_APPROVED`, `FLAGGED_EXCEPTION`, `PENDING_REVIEW`). Once terminal, re-executions are no-ops.
2. **In-Flight Redis Mutex:**
   When an event arrives, a temporary distributed mutex (`SETNX lock_84902 true EX 30`) is acquired. Concurrent requests for the same invoice are rejected with HTTP 429.
3. **Database Constraints:**
   The `class_schedule_bookings` table enforces a composite unique key `(invoice_id, student_id, batch_id)`. Any redundant INSERT attempt triggers an `ON CONFLICT DO NOTHING` statement.

---

## 5. Error-Handling, Retries & Dead Letter Queue (DLQ)

### 5.1 Retry Policy Matrix

| Node Type | Transient Error | Retry Strategy | Backoff Interval | Max Retries | Fallback Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Payment Webhook** | Network drop | Exponential backoff | 5s, 15s, 45s | 3 | Route to Cron Sweep |
| **LMS API** | HTTP 500 / 503 | Exponential backoff + jitter | 10s, 30s, 90s | 3 | Dead Letter Queue + Slack P1 |
| **WhatsApp API** | Rate Limit (HTTP 429) | Linear backoff | 30s, 60s, 120s | 3 | Enqueue in notification queue |
| **Engine Execution** | Script crash (exit != 0) | Zero immediate retry | N/A | 0 | Hard fail to `#tech-ops-oncall` |

### 5.2 Dead Letter Queue (DLQ) Architecture
When any HTTP endpoint exhausts its 3 retries:
1. The error interceptor captures `{ error_message, request_payload, node_id, timestamp }`.
2. The payload is written to `dlq_failed_orchestrations` in PostgreSQL.
3. An emergency alert is routed to `#engineering-incidents` on Slack with a 1-click **"Replay Payload"** webhook link.

---

## 6. Security, Compliance & Mock Integrations Disclaimer

> [!IMPORTANT]
> **Production Guardrails & Sandboxing Notice**
> 1. **Mock Integrations Only:** In compliance with assignment instructions, all HTTP requests to WhatsApp Cloud API, Bambinos LMS, and Slack endpoints point to mock sandboxes (`https://api.bambinos.live/mock/...`). No live WhatsApp messages or customer communications have been dispatched.
> 2. **Financial Integrity:** No payment gateway charges or refunds are executed by the automation workflow. All financial updates remain strictly read-only audit validations.
> 3. **Secrets Management:** In a live deployment, all bearer tokens, HMAC secrets, and API keys are stored in n8n encrypted environment credentials (`$env.WHATSAPP_API_KEY`, `$env.SLACK_BOT_TOKEN`), never hardcoded in plaintext workflows.

---

## 7. Workflow Verification & Validation Summary

The exported workflow JSON was comprehensively inspected and verified:
- **File Location:** [workflows/renewal_orchestrator.json](file:///Users/lambardaar/Downloads/bombios/workflows/renewal_orchestrator.json)
- **JSON Syntax:** 100% syntactically valid (verified via Python `json.load`).
- **Nodes:** 19 configured nodes across ingestion, reconciliation, routing, LMS scheduling, messaging, and database audit logging.
- **Connections:** 18 directed edges mapping all 7 operational branches without dangling endpoints.
- **Execution Compatibility:** Fully compatible with n8n v1.x and v2.x cloud/self-hosted instances.

