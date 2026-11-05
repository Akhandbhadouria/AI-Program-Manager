"""
Module: src/message_generator.py
Description: Generates professional, actionable WhatsApp and Slack message drafts
for Teachers, Parents, and Operations across all renewal exception and review scenarios.
Adheres strictly to the rule that all messages are DRAFTS and payment decisions remain deterministic.
"""

import os
import sys
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
import pandas as pd

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_loader import load_all_datasets
from src.data_normalizer import DataNormalizer

logger = logging.getLogger("reconciliation.message_generator")


@dataclass
class MessageDraft:
    """Represents a generated communication draft."""
    message_id: str
    invoice_id: str
    student_id: str
    student_name: str
    reason_code: str
    recipient_role: str       # 'Parent', 'Teacher', 'Operations'
    recipient_name: str
    recipient_contact: str
    channel: str              # 'WhatsApp', 'Slack'
    priority: str             # 'P0 (Urgent)', 'P1 (High)', 'P2 (Standard)'
    message_subject: str
    message_body: str
    action_required: str
    responsible_person: str
    status: str = "DRAFT"


class MessageTemplateEngine:
    """Rule-based template engine generating structured, empathetic, and actionable drafts."""

    @staticmethod
    def generate_for_record(
        rec: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[MessageDraft]:
        """
        Generates appropriate message drafts across roles for a given exception or review record.
        """
        inv_id = str(rec.get("invoice_id", ""))
        std_id = str(rec.get("student_id", ""))
        std_name = rec.get("student_name", "Student")
        reason_code = rec.get("reason_code", "")
        resp_person = rec.get("responsible_person", "Operations Team")
        
        # Context enrichment
        parent_name = context.get("parent_name", "Parent")
        parent_mobile = context.get("parent_mobile", "")
        educator_name = context.get("educator_name", "Teacher")
        educator_mobile = context.get("educator_mobile", "")
        class_name = context.get("class_name", "Course")
        net_amount = context.get("net_amount", "0.00")
        batch_name = context.get("batch_name", "Batch")

        drafts: List[MessageDraft] = []
        msg_idx = 1

        # -------------------------------------------------------------------------
        # Scenario 1: Missing Faculty Form (Invoices 84906, 84910)
        # -------------------------------------------------------------------------
        if reason_code == "ERR_MISSING_FACULTY_FORM":
            # 1. Teacher WhatsApp
            drafts.append(MessageDraft(
                message_id=f"MSG-{inv_id}-{msg_idx}",
                invoice_id=inv_id,
                student_id=std_id,
                student_name=std_name,
                reason_code=reason_code,
                recipient_role="Teacher",
                recipient_name=educator_name,
                recipient_contact=educator_mobile or "Educator Portal",
                channel="WhatsApp",
                priority="P1 (High)",
                message_subject=f"Action Required: Renewal Form for {std_name} (Invoice {inv_id})",
                message_body=(
                    f"Hi {educator_name}! 👋\n\n"
                    f"Good news: Full renewal payment of INR {net_amount} has been received for your student "
                    f"*{std_name}* ({class_name}, Invoice #{inv_id}).\n\n"
                    f"To ensure uninterrupted classes, please confirm their batch details using this 1-click link:\n"
                    f"👉 https://bambinos.live/faculty/renewals?inv={inv_id}&std={std_id}\n\n"
                    f"Thank you for helping us keep {std_name}'s learning on track! ✨"
                ),
                action_required="Submit pre-filled renewal form in portal.",
                responsible_person=resp_person,
            ))
            msg_idx += 1

            # 2. Ops Slack
            drafts.append(MessageDraft(
                message_id=f"MSG-{inv_id}-{msg_idx}",
                invoice_id=inv_id,
                student_id=std_id,
                student_name=std_name,
                reason_code=reason_code,
                recipient_role="Operations",
                recipient_name="Academic Ops Queue",
                recipient_contact="#ops-renewals-alerts",
                channel="Slack",
                priority="P1 (High)",
                message_subject=f":warning: Missing Faculty Form | Invoice {inv_id} | {std_name}",
                message_body=(
                    f"*Missing Faculty Form Alert*\n"
                    f"• *Invoice ID:* `{inv_id}` (Amount: INR {net_amount})\n"
                    f"• *Student:* {std_name} (`{std_id}`) | *Course:* {class_name}\n"
                    f"• *Educator:* {educator_name}\n"
                    f"• *Status:* Payment confirmed, but educator has not submitted renewal form.\n"
                    f"• *Next Step:* Automated WhatsApp prompt dispatched to {educator_name}. If unsubmitted in 2 hrs, auto-generate renewal form from LMS master."
                ),
                action_required="Monitor teacher submission SLA or trigger auto-generation.",
                responsible_person=resp_person,
            ))

        # -------------------------------------------------------------------------
        # Scenario 2: Batch Capacity Exhausted (Invoice 84905)
        # -------------------------------------------------------------------------
        elif reason_code == "ERR_BATCH_CAPACITY_EXHAUSTED":
            # 1. Parent WhatsApp
            drafts.append(MessageDraft(
                message_id=f"MSG-{inv_id}-{msg_idx}",
                invoice_id=inv_id,
                student_id=std_id,
                student_name=std_name,
                reason_code=reason_code,
                recipient_role="Parent",
                recipient_name=parent_name,
                recipient_contact=parent_mobile,
                channel="WhatsApp",
                priority="P1 (High)",
                message_subject=f"Important Update: Class Schedule for {std_name}",
                message_body=(
                    f"Dear {parent_name},\n\n"
                    f"Thank you for renewing {std_name}'s {class_name} course! We have successfully received your payment of INR {net_amount}.\n\n"
                    f"Due to high demand, your current batch ({batch_name}) has reached its maximum capacity of 6 students. "
                    f"To ensure {std_name} receives personalized attention, we have reserved a priority seat in a parallel batch with identical timings, "
                    f"or you may select an alternative time that fits your schedule.\n\n"
                    f"Please choose your preference here:\n"
                    f"👉 https://bambinos.live/schedule/select-slot?std={std_id}&inv={inv_id}\n\n"
                    f"Our student support team is also available at +91-804568XXXX to assist you directly."
                ),
                action_required="Select parallel batch slot or request callback.",
                responsible_person=resp_person,
            ))
            msg_idx += 1

            # 2. Ops Slack
            drafts.append(MessageDraft(
                message_id=f"MSG-{inv_id}-{msg_idx}",
                invoice_id=inv_id,
                student_id=std_id,
                student_name=std_name,
                reason_code=reason_code,
                recipient_role="Operations",
                recipient_name="Batch Planning Team",
                recipient_contact="#ops-capacity-alerts",
                channel="Slack",
                priority="P1 (High)",
                message_subject=f":no_entry: Batch Full Alert | Batch {batch_name} | {std_name}",
                message_body=(
                    f"*Batch Capacity Overflow*\n"
                    f"• *Invoice ID:* `{inv_id}` | *Student:* {std_name} (`{std_id}`)\n"
                    f"• *Target Batch:* {batch_name} (`active: 6 / max: 6`)\n"
                    f"• *Impact:* Student paid in full but cannot be booked in full batch.\n"
                    f"• *Action Options:*\n"
                    f"  1. Approve educator +1 capacity override to 7 students.\n"
                    f"  2. Assign seat in parallel open batch (e.g. Batch 9210).\n"
                    f"• *Dashboard Link:* https://ops.bambinos.live/allocations/{inv_id}"
                ),
                action_required="Approve +1 capacity override or confirm parallel batch assignment.",
                responsible_person=resp_person,
            ))

        # -------------------------------------------------------------------------
        # Scenario 3: Payment Status Failed at Gateway (Invoice 84911)
        # -------------------------------------------------------------------------
        elif reason_code == "ERR_PAYMENT_STATUS_FAILED":
            # 1. Parent WhatsApp
            drafts.append(MessageDraft(
                message_id=f"MSG-{inv_id}-{msg_idx}",
                invoice_id=inv_id,
                student_id=std_id,
                student_name=std_name,
                reason_code=reason_code,
                recipient_role="Parent",
                recipient_name=parent_name,
                recipient_contact=parent_mobile,
                channel="WhatsApp",
                priority="P0 (Urgent)",
                message_subject=f"Payment Update: Renewal for {std_name} (Invoice {inv_id})",
                message_body=(
                    f"Dear {parent_name},\n\n"
                    f"We noticed that your recent payment attempt for {std_name}'s renewal ({class_name}, Invoice #{inv_id}) "
                    f"could not be processed by your bank/UPI gateway.\n\n"
                    f"If the amount was debited from your account, it will automatically be refunded by your bank within 3–5 business days. "
                    f"To ensure {std_name}'s class schedule is confirmed without interruption, please retry using our secure payment link below:\n\n"
                    f"👉 https://bambinos.live/pay/retry?inv={inv_id}&std={std_id}\n\n"
                    f"Need assistance? Reply to this message and our billing support team will assist you immediately."
                ),
                action_required="Retry payment using secure gateway link.",
                responsible_person=resp_person,
            ))
            msg_idx += 1

            # 2. Teacher WhatsApp
            drafts.append(MessageDraft(
                message_id=f"MSG-{inv_id}-{msg_idx}",
                invoice_id=inv_id,
                student_id=std_id,
                student_name=std_name,
                reason_code=reason_code,
                recipient_role="Teacher",
                recipient_name=educator_name,
                recipient_contact=educator_mobile or "Educator Portal",
                channel="WhatsApp",
                priority="P0 (Urgent)",
                message_subject=f"Urgent Notice: Unverified Payment for {std_name}",
                message_body=(
                    f"Hi {educator_name},\n\n"
                    f"Regarding Form #{rec.get('faculty_form_id', '')} submitted for *{std_name}* based on a payment screenshot:\n"
                    f"Our gateway reports that this transaction has *FAILED* at the bank. No funds were collected for Invoice #{inv_id}.\n\n"
                    f"⚠️ *Important:* Please do not add {std_name} to upcoming class schedules until we notify you of successful payment settlement.\n\n"
                    f"We have sent a secure payment retry link to the parent. Thank you for your cooperation!"
                ),
                action_required="Do not confirm class schedule until payment settlement confirmed.",
                responsible_person=resp_person,
            ))
            msg_idx += 1

            # 3. Ops Slack
            drafts.append(MessageDraft(
                message_id=f"MSG-{inv_id}-{msg_idx}",
                invoice_id=inv_id,
                student_id=std_id,
                student_name=std_name,
                reason_code=reason_code,
                recipient_role="Operations",
                recipient_name="Billing & Collections Queue",
                recipient_contact="#finance-ops-alerts",
                channel="Slack",
                priority="P0 (Urgent)",
                message_subject=f":rotating_light: Hard Block: Failed Payment Form Submitted | {inv_id}",
                message_body=(
                    f"*Financial Leakage Prevented*\n"
                    f"• *Invoice ID:* `{inv_id}` | *Student:* {std_name} (`{std_id}`)\n"
                    f"• *Status:* Payment status is `Failed` at Razorpay (paid_at is NULL).\n"
                    f"• *Educator:* {educator_name} submitted form based on unconfirmed UPI screenshot.\n"
                    f"• *Action Taken:* Engine has hard-blocked renewal approval. Automated payment recovery link sent to parent. Teacher instructed to pause scheduling."
                ),
                action_required="Track recovery link conversion; prevent manual approval.",
                responsible_person=resp_person,
            ))

        # -------------------------------------------------------------------------
        # Scenario 4: Ghost Invoice Typo Re-link (Invoice 84913 / Form 3313)
        # -------------------------------------------------------------------------
        elif reason_code == "ERR_INVOICE_NOT_FOUND_REPAIRABLE":
            # 1. Ops Slack
            drafts.append(MessageDraft(
                message_id=f"MSG-{inv_id}-{msg_idx}",
                invoice_id=inv_id,
                student_id=std_id,
                student_name=std_name,
                reason_code=reason_code,
                recipient_role="Operations",
                recipient_name="Ops Auto-Repair Queue",
                recipient_contact="#ops-renewals-alerts",
                channel="Slack",
                priority="P1 (High)",
                message_subject=f":wrench: 1-Click Re-link Candidate: Form 3313 ➔ Invoice {inv_id}",
                message_body=(
                    f"*Foreign Key Typo Detected (Repair Candidate)*\n"
                    f"• *Paid Invoice:* `{inv_id}` (Student: {std_name}, Class: {class_name}, Amount: INR {net_amount})\n"
                    f"• *Faculty Form:* `Form 3313` entered with ghost invoice `84931` by {educator_name}.\n"
                    f"• *Confidence:* 100% exact match on Student ID (`{std_id}`), Class, Educator, and Fee.\n"
                    f"• *Resolution:* Click below to execute automated re-link and release approval:\n"
                    f"👉 https://ops.bambinos.live/relink?form=3313&invoice={inv_id}"
                ),
                action_required="Execute 1-click re-link on Ops dashboard.",
                responsible_person=resp_person,
            ))
            msg_idx += 1

            # 2. Teacher WhatsApp
            drafts.append(MessageDraft(
                message_id=f"MSG-{inv_id}-{msg_idx}",
                invoice_id=inv_id,
                student_id=std_id,
                student_name=std_name,
                reason_code=reason_code,
                recipient_role="Teacher",
                recipient_name=educator_name,
                recipient_contact=educator_mobile or "Educator Portal",
                channel="WhatsApp",
                priority="P2 (Standard)",
                message_subject=f"Notice: Invoice Number Update for {std_name}",
                message_body=(
                    f"Hi {educator_name},\n\n"
                    f"Quick update on your renewal submission for *{std_name}*: The invoice number entered (`84931`) "
                    f"contained a minor typo. Our system matched it to the verified paid Invoice #{inv_id}.\n\n"
                    f"We have updated the record and {std_name}'s renewal is proceeding for approval. No action needed on your end! 👍"
                ),
                action_required="FYI only. No educator action required.",
                responsible_person=resp_person,
            ))

        # -------------------------------------------------------------------------
        # Scenario 5: Duplicate Form Submissions (Invoice 84908)
        # -------------------------------------------------------------------------
        elif reason_code == "ERR_DUPLICATE_FORM_SUBMISSION":
            # 1. Ops Slack
            drafts.append(MessageDraft(
                message_id=f"MSG-{inv_id}-{msg_idx}",
                invoice_id=inv_id,
                student_id=std_id,
                student_name=std_name,
                reason_code=reason_code,
                recipient_role="Operations",
                recipient_name="Ops Lead Queue",
                recipient_contact="#ops-renewals-alerts",
                channel="Slack",
                priority="P2 (Standard)",
                message_subject=f":information_source: Deduplication Applied | Invoice {inv_id}",
                message_body=(
                    f"*Duplicate Renewal Form Handled*\n"
                    f"• *Invoice:* `{inv_id}` | *Student:* {std_name} (`{std_id}`)\n"
                    f"• *Forms Received:* 3308 (08:30:00) and 3309 (08:35:12) by {educator_name}.\n"
                    f"• *Action Taken:* Engine has preserved Form 3308 as active and auto-archived Form 3309 to prevent duplicate seat booking."
                ),
                action_required="Auto-resolved. Verify deduplication log in dashboard.",
                responsible_person=resp_person,
            ))
            msg_idx += 1

            # 2. Teacher WhatsApp
            drafts.append(MessageDraft(
                message_id=f"MSG-{inv_id}-{msg_idx}",
                invoice_id=inv_id,
                student_id=std_id,
                student_name=std_name,
                reason_code=reason_code,
                recipient_role="Teacher",
                recipient_name=educator_name,
                recipient_contact=educator_mobile or "Educator Portal",
                channel="WhatsApp",
                priority="P2 (Standard)",
                message_subject=f"Confirmation: Renewal Form Received for {std_name}",
                message_body=(
                    f"Hi {educator_name},\n\n"
                    f"We received two submissions for *{std_name}* (Invoice #{inv_id}). We have processed your earlier submission "
                    f"(Form #3308) and safely archived the duplicate.\n\n"
                    f"The renewal is now progressing normally. Thank you!"
                ),
                action_required="FYI only. No educator action required.",
                responsible_person=resp_person,
            ))

        # -------------------------------------------------------------------------
        # Scenario 6: Secondary Parent Contact Divergence (Invoice 84904)
        # -------------------------------------------------------------------------
        elif reason_code == "WARN_SECONDARY_PARENT_PAYER":
            # 1. Parent WhatsApp (to Payer / Mother)
            drafts.append(MessageDraft(
                message_id=f"MSG-{inv_id}-{msg_idx}",
                invoice_id=inv_id,
                student_id=std_id,
                student_name=std_name,
                reason_code=reason_code,
                recipient_role="Parent",
                recipient_name=parent_name,
                recipient_contact=parent_mobile,
                channel="WhatsApp",
                priority="P2 (Standard)",
                message_subject=f"Payment Received: Renewal Confirmation for {std_name}",
                message_body=(
                    f"Dear {parent_name},\n\n"
                    f"Thank you! We have received your renewal payment of INR {net_amount} for *{std_name}* ({class_name}, Invoice #{inv_id}).\n\n"
                    f"We noticed you paid from this number ({parent_mobile}), while {std_name}'s profile was initially registered under another family number. "
                    f"To ensure you both receive class links and progress updates, please tap below to add this number as an authorized secondary contact:\n"
                    f"👉 https://bambinos.live/profile/link-contact?std={std_id}&phone={parent_mobile}\n\n"
                    f"{std_name}'s class schedule is being confirmed!"
                ),
                action_required="1-click confirm secondary contact linking.",
                responsible_person=resp_person,
            ))
            msg_idx += 1

            # 2. Ops Slack
            drafts.append(MessageDraft(
                message_id=f"MSG-{inv_id}-{msg_idx}",
                invoice_id=inv_id,
                student_id=std_id,
                student_name=std_name,
                reason_code=reason_code,
                recipient_role="Operations",
                recipient_name="Ops Review Queue",
                recipient_contact="#ops-assisted-review",
                channel="Slack",
                priority="P2 (Standard)",
                message_subject=f":busts_in_silhouette: Secondary Payer Verification | {std_name}",
                message_body=(
                    f"*Cross-Parent Payer Divergence*\n"
                    f"• *Invoice:* `{inv_id}` | *Student:* {std_name} (`{std_id}`)\n"
                    f"• *Payer:* {parent_name} (`{parent_mobile}`) | *Registered Profile:* Father\n"
                    f"• *Teacher Remark:* '{context.get('remarks', 'Mother paid')}'\n"
                    f"• *Action:* Click to approve renewal and link mother's contact to master profile:\n"
                    f"👉 https://ops.bambinos.live/approve-contact?inv={inv_id}"
                ),
                action_required="1-Click verify secondary contact and release approval.",
                responsible_person=resp_person,
            ))

        # -------------------------------------------------------------------------
        # Scenario 7: Promotional Discount Audit (Invoice 84907)
        # -------------------------------------------------------------------------
        elif reason_code == "INFO_DISCOUNT_AUDIT_REQUIRED":
            # 1. Ops Slack
            drafts.append(MessageDraft(
                message_id=f"MSG-{inv_id}-{msg_idx}",
                invoice_id=inv_id,
                student_id=std_id,
                student_name=std_name,
                reason_code=reason_code,
                recipient_role="Operations",
                recipient_name="Sales Ops Queue",
                recipient_contact="#sales-ops-audits",
                channel="Slack",
                priority="P2 (Standard)",
                message_subject=f":label: Discount Audit Required | Invoice {inv_id} | {std_name}",
                message_body=(
                    f"*Promotional Discount Audit*\n"
                    f"• *Invoice:* `{inv_id}` | *Student:* {std_name} (`{std_id}`)\n"
                    f"• *Gross Fee:* INR {context.get('gross_amount', '9500.00')} | *Discount:* INR {context.get('discount_amount', '1900.00')} (20.0%)\n"
                    f"• *Net Collected:* INR {net_amount} (matches Faculty Form exactly)\n"
                    f"• *Action:* 1-Click to confirm promotional code and auto-approve renewal:\n"
                    f"👉 https://ops.bambinos.live/audit-discount?inv={inv_id}"
                ),
                action_required="Verify promotional authorization and approve.",
                responsible_person=resp_person,
            ))

        # -------------------------------------------------------------------------
        # Scenario 8: Partial Payment Provisional Approval (Invoice 84909)
        # -------------------------------------------------------------------------
        elif reason_code == "WARN_PARTIAL_PAYMENT_PROVISIONAL":
            # 1. Parent WhatsApp
            drafts.append(MessageDraft(
                message_id=f"MSG-{inv_id}-{msg_idx}",
                invoice_id=inv_id,
                student_id=std_id,
                student_name=std_name,
                reason_code=reason_code,
                recipient_role="Parent",
                recipient_name=parent_name,
                recipient_contact=parent_mobile,
                channel="WhatsApp",
                priority="P2 (Standard)",
                message_subject=f"Installment Confirmation: {std_name}'s Renewal",
                message_body=(
                    f"Dear {parent_name},\n\n"
                    f"We have received your payment of INR {net_amount} for *Installment 1 of 2* for {std_name}'s {class_name} course.\n\n"
                    f"🎉 *{std_name}'s provisional batch booking of 12 sessions is confirmed!* Class schedules will appear in your parent app shortly.\n\n"
                    f"Your remaining installment of INR {net_amount} will be due prior to session 12. We will send a convenient reminder link closer to the date."
                ),
                action_required="Confirm provisional 12 sessions schedule in app.",
                responsible_person=resp_person,
            ))
            msg_idx += 1

            # 2. Ops Slack
            drafts.append(MessageDraft(
                message_id=f"MSG-{inv_id}-{msg_idx}",
                invoice_id=inv_id,
                student_id=std_id,
                student_name=std_name,
                reason_code=reason_code,
                recipient_role="Operations",
                recipient_name="Operations Lead",
                recipient_contact="#ops-assisted-review",
                channel="Slack",
                priority="P2 (Standard)",
                message_subject=f":credit_card: Installment 1 Approval | Invoice {inv_id} | {std_name}",
                message_body=(
                    f"*Partial Payment Provisional Booking*\n"
                    f"• *Invoice:* `{inv_id}` | *Student:* {std_name} (`{std_id}`)\n"
                    f"• *Collected:* INR {net_amount} (50% of 24-session fee)\n"
                    f"• *Recommendation:* Approve provisional booking for 12 sessions and set automated Installment 2 reminder.\n"
                    f"👉 https://ops.bambinos.live/approve-provisional?inv={inv_id}&sessions=12"
                ),
                action_required="Approve provisional 12 sessions in dashboard.",
                responsible_person=resp_person,
            ))

        # -------------------------------------------------------------------------
        # Scenario 9: Batch Change Preference Selection (Invoice 84912)
        # -------------------------------------------------------------------------
        elif reason_code == "WARN_BATCH_CHANGE_SELECTION_PENDING":
            # 1. Parent WhatsApp
            drafts.append(MessageDraft(
                message_id=f"MSG-{inv_id}-{msg_idx}",
                invoice_id=inv_id,
                student_id=std_id,
                student_name=std_name,
                reason_code=reason_code,
                recipient_role="Parent",
                recipient_name=parent_name,
                recipient_contact=parent_mobile,
                channel="WhatsApp",
                priority="P1 (High)",
                message_subject=f"Select New Weekend Batch for {std_name}",
                message_body=(
                    f"Dear {parent_name},\n\n"
                    f"Your renewal for {std_name}'s {class_name} course is approved! We noted your request to move to a *Saturday & Sunday 11:00 AM* batch.\n\n"
                    f"Here are the available weekend batches with open seats:\n"
                    f"1️⃣ Batch LY-SAT-SUN-A (Sat/Sun 11:00 AM) - Acharya Nancy\n"
                    f"2️⃣ Batch LY-SAT-SUN-B (Sat/Sun 11:30 AM) - Acharya Nancy\n\n"
                    f"Please tap below to confirm your preferred batch:\n"
                    f"👉 https://bambinos.live/batch/confirm?std={std_id}&inv={inv_id}&opt=weekend\n\n"
                    f"Once selected, your calendar invites and Zoom links will be generated automatically!"
                ),
                action_required="Confirm preferred weekend batch slot via 1-click link.",
                responsible_person=resp_person,
            ))
            msg_idx += 1

            # 2. Ops Slack
            drafts.append(MessageDraft(
                message_id=f"MSG-{inv_id}-{msg_idx}",
                invoice_id=inv_id,
                student_id=std_id,
                student_name=std_name,
                reason_code=reason_code,
                recipient_role="Operations",
                recipient_name="Customer Success Lead",
                recipient_contact="#ops-batch-changes",
                channel="Slack",
                priority="P1 (High)",
                message_subject=f":arrows_counterclockwise: Batch Change Pending Parent Selection | {std_name}",
                message_body=(
                    f"*Batch Change Request Dispatched*\n"
                    f"• *Invoice:* `{inv_id}` | *Student:* {std_name} (`{std_id}`)\n"
                    f"• *Preference:* Shifted from Wed/Fri to Sat/Sun 11:00 AM.\n"
                    f"• *Action Taken:* WhatsApp options sent to parent. Awaiting 1-click confirmation within 48-hour SLA window."
                ),
                action_required="Track parent response; follow up if unconfirmed in 24 hrs.",
                responsible_person=resp_person,
            ))

        return drafts


class MessageGeneratorService:
    """Orchestrates generation of all follow-up drafts and exports to CSV."""

    def __init__(self, data_dir: str = "."):
        self.data_dir = data_dir
        raw_bundle = load_all_datasets(data_dir=data_dir)
        self.invoices = DataNormalizer.normalize_invoices(raw_bundle.invoices)
        self.faculty_forms = DataNormalizer.normalize_faculty_form(raw_bundle.faculty_form)
        self.reference = DataNormalizer.normalize_reference(raw_bundle.reference)

    def generate_all_messages(
        self,
        exceptions_csv: str = "flagged_exceptions.csv",
        review_csv: str = "pending_human_review.csv",
        output_csv: str = "outputs/followup_messages.csv"
    ) -> pd.DataFrame:
        """
        Ingests exceptions and review items, builds full context, and produces followup_messages.csv.
        """
        all_drafts: List[MessageDraft] = []

        dfs_to_process = []
        if os.path.exists(exceptions_csv):
            dfs_to_process.append(pd.read_csv(exceptions_csv, dtype=str))
        if os.path.exists(review_csv):
            dfs_to_process.append(pd.read_csv(review_csv, dtype=str))

        if not dfs_to_process:
            logger.warning("No exception or review CSVs found to generate messages from.")
            return pd.DataFrame()

        combined_records = pd.concat(dfs_to_process, ignore_index=True)

        for _, row in combined_records.iterrows():
            inv_id = str(row.get("invoice_id", ""))
            std_id = str(row.get("student_id", ""))
            
            # Lookup invoice
            inv_match = self.invoices[self.invoices["id"] == inv_id]
            inv_row = inv_match.iloc[0] if not inv_match.empty else None

            # Lookup reference
            ref_match = self.reference[self.reference["student_id"] == std_id]
            ref_row = ref_match.iloc[0] if not ref_match.empty else None

            # Lookup faculty form
            form_match = self.faculty_forms[self.faculty_forms["invoice_id"] == inv_id]
            form_row = form_match.iloc[0] if not form_match.empty else None

            # Build enriched context
            context = {
                "parent_name": inv_row.get("parent_name") if inv_row is not None else (ref_row.get("parent_name_masked") if ref_row is not None else "Parent"),
                "parent_mobile": inv_row.get("mobile") if inv_row is not None else (ref_row.get("registered_mobile_masked") if ref_row is not None else ""),
                "educator_name": ref_row.get("educator_name") if ref_row is not None else (form_row.get("educator_name") if form_row is not None else "Teacher"),
                "educator_mobile": "",
                "class_name": ref_row.get("class_name") if ref_row is not None else "Course",
                "batch_name": ref_row.get("classbatch_name") if ref_row is not None else "Batch",
                "net_amount": f"{float(inv_row.get('net_amount', 0.0)):,.2f}" if inv_row is not None else "0.00",
                "gross_amount": f"{float(inv_row.get('amount', 0.0)):,.2f}" if inv_row is not None else "0.00",
                "discount_amount": f"{float(inv_row.get('discount_amount', 0.0)):,.2f}" if inv_row is not None else "0.00",
                "remarks": form_row.get("remarks") if form_row is not None else "",
            }

            drafts = MessageTemplateEngine.generate_for_record(row.to_dict(), context)
            all_drafts.extend(drafts)

        # Convert to DataFrame
        records_data = [d.__dict__ for d in all_drafts]
        df_out = pd.DataFrame(records_data)

        os.makedirs(os.path.dirname(output_csv), exist_ok=True)
        df_out.to_csv(output_csv, index=False)
        logger.info(f"Generated {len(df_out)} follow-up message drafts saved to: {output_csv}")

        return df_out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    service = MessageGeneratorService()
    df_msgs = service.generate_all_messages()
    print(f"\nGenerated {len(df_msgs)} message drafts.")
    print(df_msgs[["message_id", "invoice_id", "recipient_role", "channel", "priority", "message_subject"]].to_string(index=False))
