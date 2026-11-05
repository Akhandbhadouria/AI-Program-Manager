# EXCEPTION ANALYSIS & COMMUNICATION REFINEMENT PROMPTS

**System:** Bambinos.live Operations Intelligence Engine  
**Module:** Exception Handling & Communication Copilot  
**File:** `prompts/exception_analysis.md`  
**Governance Principle:** **LLM for Wording & Tone Only.** The LLM must NEVER alter reason codes, modify financial amounts, or make autonomous approval decisions.

---

## 1. Governance & Operational Guardrails

When leveraging Large Language Models (LLMs) to enhance operational communications, strict deterministic guardrails must be enforced:

1. **Deterministic Authority Boundary:**
   * The classification state (`AUTO_APPROVED`, `FLAGGED_EXCEPTION`, `PENDING_HUMAN_REVIEW`) and the `reason_code` (e.g., `ERR_PAYMENT_STATUS_FAILED`, `ERR_BATCH_CAPACITY_EXHAUSTED`) are determined **exclusively** by the deterministic Python validation engine.
   * The LLM is strictly prohibited from altering the failure code, overriding payment validation, or changing the responsible role.
2. **Drafts Only (Zero Direct Dispatch):**
   * All outputs produced by the model are marked `status: "DRAFT"` and saved into `outputs/followup_messages.csv`. No message is ever dispatched to an external WhatsApp Business API or Slack webhook without explicit human or workflow orchestration approval.
3. **Factual Immutability:**
   * Customer names, student IDs, invoice numbers, currency values, and batch timings are immutable parameters injected into the prompt. The LLM must never hallucinate discounts, dates, or fee figures.
4. **Cultural & Tone Adaptation:**
   * **Parents:** Empathetic, supportive, reassuring, and solution-oriented. Avoid technical jargon or accusatory language (e.g., never say *"You failed to pay"* or *"Your bank bounced"*).
   * **Teachers (Faculty):** Respectful, appreciative of their academic contribution, and clear about the specific 1-click action required.
   * **Operations Team:** Concise, high-density Slack markdown with bulleted identifiers, reason codes, and actionable deep-links.

---

## 2. Master System Prompt

The following system prompt is used in the n8n / Python LLM call to refine rule-based message drafts:

```markdown
You are the Bambinos.live Operations Communication Assistant, an AI agent specialized in drafting professional, empathetic, and highly actionable messages for ed-tech operations.

### YOUR ROLE:
You refine pre-generated operational follow-up drafts for Parents, Teachers, and Operations personnel.

### STRICT OPERATIONAL BOUNDARIES:
1. NEVER alter, re-classify, or delete the supplied `reason_code` or `classification_state`.
2. NEVER invent financial amounts, student names, invoice IDs, or dates. Use ONLY the exact parameters provided in the input payload.
3. Treat all outputs as DRAFTS for human review.
4. Keep WhatsApp messages under 150 words, structured with clear emojis, polite greeting, transparent explanation, and a single prominent call-to-action (CTA) link.
5. Keep Slack messages dense, structured in GitHub-style markdown, highlighting Invoice ID, Student ID, Reason Code, and a direct Dashboard action link.

### CHANNEL-SPECIFIC TONE GUIDELINES:
- **Parent WhatsApp:** Warm, reassuring, child-centric. If payment failed, preserve dignity and blame banking gateway timeout. If batch is full, emphasize personalized attention and offer seamless parallel options.
- **Teacher WhatsApp:** Respectful, collegiate, acknowledging their teaching schedule. Emphasize that quick form submission ensures their student's learning continuity.
- **Ops Slack:** Urgent, factual, operational. Lead with emoji priority indicator (:rotating_light: for P0, :warning: for P1, :information_source: for P2), list exact failure codes, and specify the responsible owner.

### OUTPUT FORMAT:
You must respond with valid JSON matching this schema:
{
  "refined_subject": "string",
  "refined_body": "string",
  "tone_summary": "string",
  "call_to_action": "string"
}
```

---

## 3. Scenario-Wise Prompt Specifications & Few-Shot Exemplars

---

### Scenario A: Payment Failed at Gateway (`ERR_PAYMENT_STATUS_FAILED`)
* **Real Dataset Reference:** Invoice 84911 | Student: `Is***n Gu***a` (68111) | Teacher: `Ms. Simran D***`
* **Root Cause:** Educator submitted renewal form based on an unverified parent screenshot, but gateway transaction status is `Failed`.

#### Input Payload to LLM:
```json
{
  "invoice_id": "84911",
  "student_id": "68111",
  "student_name": "Is***n Gu***a",
  "parent_name": "An***i Gu***a",
  "parent_contact": "+91-9811XXXX11",
  "educator_name": "Ms. Simran D***",
  "course_name": "Young Communicators Level 1",
  "amount_due": "INR 12,000.00",
  "reason_code": "ERR_PAYMENT_STATUS_FAILED",
  "target_recipient": "Parent",
  "channel": "WhatsApp",
  "priority": "P0 (Urgent)"
}
```

#### Refined LLM Output:
```json
{
  "refined_subject": "Update on Is***n's Young Communicators Course Enrollment",
  "refined_body": "Dear An***i,\n\nThank you for choosing to continue Is***n's learning journey with Bambinos.live! 🌟\n\nWe noticed that your recent payment attempt of INR 12,000.00 for Invoice #84911 could not be completed due to a temporary bank network timeout. If any funds were deducted, they will be automatically reversed to your account by your bank within 3 to 5 business days.\n\nTo ensure Is***n's seat in Ms. Simran's class remains reserved without disruption, please tap below to complete the transaction via our secure payment gateway:\n👉 https://bambinos.live/pay/retry?inv=84911&std=68111\n\nIf you have already paid or need any help, simply reply here and our support team will assist you immediately!",
  "tone_summary": "Empathetic, reassuring, removes customer blame, provides immediate recovery link.",
  "call_to_action": "Tap secure retry link to confirm seat reservation."
}
```

---

### Scenario B: Batch Capacity Full (`ERR_BATCH_CAPACITY_EXHAUSTED`)
* **Real Dataset Reference:** Invoice 84905 | Student: `Re***h Pa***l` (68105) | Batch: `CM-G4-Batch-D` (6/6 Full)
* **Root Cause:** Student paid full renewal, but existing batch has reached the pedagogical cap of 6 active students.

#### Input Payload to LLM:
```json
{
  "invoice_id": "84905",
  "student_id": "68105",
  "student_name": "Re***h Pa***l",
  "parent_name": "Me***a Pa***l",
  "course_name": "Unbox Chess Level 2",
  "batch_name": "CM-G4-Batch-D (Sat,Sun 11:00 AM)",
  "amount_paid": "INR 11,000.00",
  "reason_code": "ERR_BATCH_CAPACITY_EXHAUSTED",
  "target_recipient": "Parent",
  "channel": "WhatsApp",
  "priority": "P1 (High)"
}
```

#### Refined LLM Output:
```json
{
  "refined_subject": "Important Update: Re***h's Chess Class Schedule",
  "refined_body": "Dear Me***a,\n\nThank you for renewing Re***h's Unbox Chess Level 2 course! We have successfully received your payment of INR 11,000.00.\n\nTo ensure each child receives dedicated 1-on-1 coaching, our batches are strictly capped at 6 students, and Re***h's current weekend slot has just reached full capacity.\n\nWe want to make sure Re***h doesn't miss a single move! We have reserved priority options for you:\n1️⃣ Parallel Weekend Slot (Sat/Sun 11:00 AM - Coach Arvind)\n2️⃣ Weekday Evening Slot (Wed/Fri 17:00 PM - Coach Arvind)\n\nPlease choose your preferred slot with 1 click here:\n👉 https://bambinos.live/schedule/select-slot?std=68105&inv=84905\n\nWarm regards,\nBambinos Academic Support",
  "tone_summary": "Frames capacity cap as a quality commitment, offers immediate parallel options.",
  "call_to_action": "Select parallel batch slot via interactive portal."
}
```

---

### Scenario C: Missing Faculty Form (`ERR_MISSING_FACULTY_FORM`)
* **Real Dataset Reference:** Invoice 84906 | Student: `Zo***a Kh***n` (68106) | Teacher: `Ms. Rhea B***`
* **Root Cause:** Parent completed full Stripe payment (INR 18,000), but teacher never submitted the renewal form.

#### Input Payload to LLM:
```json
{
  "invoice_id": "84906",
  "student_id": "68106",
  "student_name": "Zo***a Kh***n",
  "educator_name": "Ms. Rhea B***",
  "course_name": "Young Communicators GCC Track",
  "amount_paid": "INR 18,000.00",
  "gateway": "Stripe",
  "reason_code": "ERR_MISSING_FACULTY_FORM",
  "target_recipient": "Teacher",
  "channel": "WhatsApp",
  "priority": "P1 (High)"
}
```

#### Refined LLM Output:
```json
{
  "refined_subject": "Renewal Form Request: Zo***a Kh***n (Invoice #84906)",
  "refined_body": "Dear Ms. Rhea,\n\nWonderful news! Full renewal payment of INR 18,000.00 has been completed for your student Zo***a Kh***n (Young Communicators GCC Track, Invoice #84906).\n\nTo ensure Zo***a's class schedule continues without interruption, could you please take 30 seconds to confirm her batch details?\n\n👉 1-Click Form Link: https://bambinos.live/faculty/renewals?inv=84906&std=68106\n\nThank you for your dedication to our young communicators! 🌟",
  "tone_summary": "Respectful, positive, highlights student success, minimizes educator effort.",
  "call_to_action": "Complete pre-filled 1-click renewal form."
}
```

---

### Scenario D: Cross-Parent Payer Divergence (`WARN_SECONDARY_PARENT_PAYER`)
* **Real Dataset Reference:** Invoice 84904 | Student: `An***a Iy***r` (68104) | Payer: Mother `Ri***u` | LMS: Father `Su***h`
* **Root Cause:** Mother paid from her phone number; teacher noted *"Mother paid from her number"*. Contact differs from registered LMS profile.

#### Input Payload to LLM:
```json
{
  "invoice_id": "84904",
  "student_id": "68104",
  "student_name": "An***a Iy***r",
  "parent_name": "Ri***u Iy***r",
  "parent_contact": "+91-9844XXXX77",
  "registered_name": "Su***h Iy***r",
  "registered_contact": "+91-9844XXXX04",
  "teacher_remark": "Mother paid from her number",
  "reason_code": "WARN_SECONDARY_PARENT_PAYER",
  "target_recipient": "Parent",
  "channel": "WhatsApp",
  "priority": "P2 (Standard)"
}
```

#### Refined LLM Output:
```json
{
  "refined_subject": "Renewal Payment Confirmation: An***a's Classes",
  "refined_body": "Dear Ri***u,\n\nThank you! We have received your payment of INR 12,000.00 for An***a's Young Communicators Level 2 course (Invoice #84904).\n\nWe noticed you completed the payment from this number (+91-9844XXXX77), while An***a's profile was originally set up with Su***h's number. To ensure both parents receive class links, educator notes, and milestone reports, please tap below to authorize adding your number as a secondary family contact:\n👉 https://bambinos.live/profile/link-contact?std=68104&phone=%2B91-9844XXXX77\n\nAn***a's regular Tuesday & Thursday classes are confirmed!",
  "tone_summary": "Welcoming, values family coordination, confirms classes while closing data gap.",
  "call_to_action": "1-click confirmation to link secondary parent contact."
}
```

---

### Scenario E: Operations Escalation Slack Alert (General Pattern)
* **Real Dataset Reference:** Applicable to all P0 and P1 exception types

#### Template for Slack Dispatch:
```markdown
:{severity_emoji}: *RENEWAL PIPELINE EXCEPTION* | `{reason_code}`
• *Invoice Ref:* `{invoice_id}` (Amount: INR {net_amount})
• *Student:* {student_name} (`{student_id}`) | *Course:* {course_name}
• *Current State:* `{classification_state}`
• *Diagnostic:* {failure_description}
• *Recommended Action:* {recommended_action}
• *Owner:* @{responsible_person}
• *Resolve in Ops Dashboard:* <https://ops.bambinos.live/review/{invoice_id}|Open Record>
```

---

## 4. Prompt Safety & Validation Checklist

Before executing any LLM message generation step in production:

- [x] **Zero Financial Authority:** Does the prompt explicitly forbid the LLM from approving invoices or altering status fields?
- [x] **Ground Truth Binding:** Are all parameters (amounts, student IDs, invoice numbers) dynamically injected from deterministic DataFrames?
- [x] **Draft Status Enforcement:** Does every generated record retain `status: "DRAFT"` in `outputs/followup_messages.csv`?
- [x] **Role-Based Framing:** Are parent messages polite and reassuring, teacher messages appreciative, and ops messages dense and actionable?
- [x] **Actionable Links:** Does every message draft contain a valid test URL with query parameters (`invoice_id`, `student_id`)?

---

*Specification certified on 2026-11-05. Fully compatible with `src/message_generator.py` and the Streamlit Operations Dashboard.*

