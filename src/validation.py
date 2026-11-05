"""
Module: src/validation.py
Description: Pure deterministic validation rules implementing BUSINESS_RULES.md.
Never uses an LLM. Enforces strict zero-loss financial and operational invariants.
"""

import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import pandas as pd

logger = logging.getLogger("reconciliation.validation")


@dataclass
class ValidationResult:
    """Standardized result of an individual business validation check."""
    rule_id: str
    rule_name: str
    is_valid: bool
    status: str            # 'PASS', 'WARN', 'FAIL'
    reason_code: str
    reason_message: str
    recommended_action: str
    responsible_person: str


class BusinessValidator:
    """Encapsulates all atomic validation rules defined in BUSINESS_RULES.md."""

    @staticmethod
    def validate_payment_status(inv_row: Optional[pd.Series]) -> ValidationResult:
        """BR-PAY-002: Verify payment is captured and confirmed at payment gateway."""
        if inv_row is None:
            return ValidationResult(
                rule_id="BR-INV-001",
                rule_name="Invoice Existence",
                is_valid=False,
                status="FAIL",
                reason_code="ERR_INVOICE_NOT_FOUND",
                reason_message="No invoice record found corresponding to renewal request.",
                recommended_action="Quarantine form and request valid invoice link from submitting educator.",
                responsible_person="Operations Associate",
            )

        status = inv_row.get("payment_status")
        gateway_payment_id = inv_row.get("gateway_payment_id")
        paid_at = inv_row.get("paid_at_dt")

        if status == "Failed":
            return ValidationResult(
                rule_id="BR-PAY-002",
                rule_name="Payment Completion",
                is_valid=False,
                status="FAIL",
                reason_code="ERR_PAYMENT_STATUS_FAILED",
                reason_message="Invoice payment status is 'Failed' at payment gateway. Uncollected transaction.",
                recommended_action="Hard block approval. Send payment retry link via WhatsApp to parent; notify educator.",
                responsible_person="Billing & Collections Specialist",
            )

        if status == "Partially_Paid":
            return ValidationResult(
                rule_id="BR-PAY-004",
                rule_name="Partial Payment Governance",
                is_valid=False,
                status="WARN",
                reason_code="WARN_PARTIAL_PAYMENT_PROVISIONAL",
                reason_message=f"Invoice is Partially_Paid (Installment 1: INR {inv_row.get('net_amount', 0):,.2f}).",
                recommended_action="Route to Ops: Issue provisional approval for 12 sessions; schedule Installment 2 reminder.",
                responsible_person="Operations Lead",
            )

        if status != "Paid" or gateway_payment_id is None or paid_at is None:
            return ValidationResult(
                rule_id="BR-PAY-002",
                rule_name="Payment Completion",
                is_valid=False,
                status="FAIL",
                reason_code="ERR_PAYMENT_UNCONFIRMED_GATEWAY",
                reason_message="Payment has not been confirmed or lacks gateway settlement identifier.",
                recommended_action="Check gateway portal for manual settlement confirmation before proceeding.",
                responsible_person="Billing & Collections Specialist",
            )

        return ValidationResult(
            rule_id="BR-PAY-002",
            rule_name="Payment Completion",
            is_valid=True,
            status="PASS",
            reason_code="SUCCESS_PAYMENT_CONFIRMED",
            reason_message="Full payment verified as Paid with valid gateway transaction ID.",
            recommended_action="Proceed to amount and identity validation.",
            responsible_person="System Automation",
        )

    @staticmethod
    def validate_amount_and_discount(
        inv_row: pd.Series,
        form_row: Optional[pd.Series],
        ref_row: Optional[pd.Series],
    ) -> ValidationResult:
        """BR-PAY-003 & BR-PAY-005: Verify collected net amount against form and catalog fee."""
        if form_row is None:
            return ValidationResult(
                rule_id="BR-INV-001",
                rule_name="Faculty Form Existence",
                is_valid=False,
                status="FAIL",
                reason_code="ERR_MISSING_FACULTY_FORM",
                reason_message="Invoice was paid, but educator has not submitted a renewal faculty form.",
                recommended_action="Trigger automated WhatsApp reminder to educator with pre-filled renewal link.",
                responsible_person="Academic Operations Coordinator",
            )

        inv_net = float(inv_row.get("net_amount", 0.0) or 0.0)
        inv_gross = float(inv_row.get("amount", 0.0) or 0.0)
        inv_discount = float(inv_row.get("discount_amount", 0.0) or 0.0)
        form_amount = float(form_row.get("amount_paid", 0.0) or 0.0)

        # Check discount
        if inv_discount > 0:
            if inv_discount <= (0.20 * inv_gross + 0.01) and abs((inv_gross - inv_discount) - inv_net) < 0.01:
                # 20% standard promotional discount
                if abs(form_amount - inv_net) < 0.01:
                    return ValidationResult(
                        rule_id="BR-PAY-005",
                        rule_name="Promotional Discount Verification",
                        is_valid=True,
                        status="WARN",
                        reason_code="INFO_DISCOUNT_AUDIT_REQUIRED",
                        reason_message=f"20% discount applied (INR {inv_discount:,.2f}). Form matches Net INR {inv_net:,.2f}.",
                        recommended_action="Sales Ops 1-click audit to verify promotional coupon code and release approval.",
                        responsible_person="Sales Operations Team Lead",
                    )

        # Installment amount mismatch
        if inv_row.get("payment_status") == "Partially_Paid":
            return ValidationResult(
                rule_id="BR-PAY-004",
                rule_name="Partial Payment Amount",
                is_valid=False,
                status="WARN",
                reason_code="WARN_PARTIAL_PAYMENT_PROVISIONAL",
                reason_message=f"Installment 1 paid (Net: INR {inv_net:,.2f}); Form logged gross INR {form_amount:,.2f}.",
                recommended_action="Update form amount to INR 5,250.00 and provision 12 sessions.",
                responsible_person="Operations Lead",
            )

        # General mismatch check
        if abs(inv_net - form_amount) > 0.01:
            return ValidationResult(
                rule_id="BR-PAY-003",
                rule_name="Amount Verification",
                is_valid=False,
                status="FAIL",
                reason_code="ERR_AMOUNT_FORM_INVOICE_MISMATCH",
                reason_message=f"Invoice net amount (INR {inv_net:,.2f}) does not match form amount paid (INR {form_amount:,.2f}).",
                recommended_action="Investigate discrepancy between billing statement and teacher submission.",
                responsible_person="Finance Operations Specialist",
            )

        return ValidationResult(
            rule_id="BR-PAY-003",
            rule_name="Amount Verification",
            is_valid=True,
            status="PASS",
            reason_code="SUCCESS_AMOUNT_VERIFIED",
            reason_message="Invoice net amount matches educator form recorded amount exactly.",
            recommended_action="Proceed to student identity verification.",
            responsible_person="System Automation",
        )

    @staticmethod
    def validate_student_and_class(
        inv_row: pd.Series,
        form_row: Optional[pd.Series],
        ref_row: Optional[pd.Series],
    ) -> ValidationResult:
        """BR-STD-006: Verify student ID, class ID, and educator ID alignment."""
        if ref_row is None:
            return ValidationResult(
                rule_id="BR-STD-006",
                rule_name="Student Master Alignment",
                is_valid=False,
                status="FAIL",
                reason_code="ERR_STUDENT_NOT_IN_MASTER",
                reason_message=f"Student ID {inv_row.get('student_id')} not found in active students reference table.",
                recommended_action="Check if student is a new enrollment or previously deactivated.",
                responsible_person="Academic Operations Coordinator",
            )

        std_id_inv = str(inv_row.get("student_id"))
        std_id_ref = str(ref_row.get("student_id"))
        class_id_inv = str(inv_row.get("class_id"))
        class_id_ref = str(ref_row.get("class_id"))
        edu_id_inv = str(inv_row.get("educator_id"))
        edu_id_ref = str(ref_row.get("educator_id"))

        if form_row is not None:
            std_id_form = str(form_row.get("student_id"))
            class_id_form = str(form_row.get("class_id"))
            edu_id_form = str(form_row.get("educator_id"))

            if std_id_inv != std_id_form or std_id_inv != std_id_ref:
                return ValidationResult(
                    rule_id="BR-STD-006",
                    rule_name="Student Identity Alignment",
                    is_valid=False,
                    status="FAIL",
                    reason_code="ERR_STUDENT_ID_MISMATCH",
                    reason_message=f"Student ID mismatch across tables (Inv: {std_id_inv}, Form: {std_id_form}, Ref: {std_id_ref}).",
                    recommended_action="Verify student record and re-align foreign keys.",
                    responsible_person="Academic Operations Coordinator",
                )

            if class_id_inv != class_id_form or class_id_inv != class_id_ref:
                return ValidationResult(
                    rule_id="BR-STD-006",
                    rule_name="Course Alignment",
                    is_valid=False,
                    status="FAIL",
                    reason_code="ERR_CLASS_MISMATCH",
                    reason_message=f"Class ID mismatch (Inv: {class_id_inv}, Form: {class_id_form}, Ref: {class_id_ref}).",
                    recommended_action="Verify if student is upgrading curriculum level or changing subject track.",
                    responsible_person="Academic Operations Coordinator",
                )

            if edu_id_inv != edu_id_form or edu_id_inv != edu_id_ref:
                return ValidationResult(
                    rule_id="BR-STD-006",
                    rule_name="Educator Alignment",
                    is_valid=False,
                    status="FAIL",
                    reason_code="ERR_EDUCATOR_MISMATCH",
                    reason_message=f"Educator ID mismatch (Inv: {edu_id_inv}, Form: {edu_id_form}, Ref: {edu_id_ref}).",
                    recommended_action="Check if student was transferred to a different teacher.",
                    responsible_person="Academic Operations Coordinator",
                )

        return ValidationResult(
            rule_id="BR-STD-006",
            rule_name="Identity Alignment",
            is_valid=True,
            status="PASS",
            reason_code="SUCCESS_IDENTITY_ALIGNED",
            reason_message="Student ID, Class ID, and Educator ID match master profile perfectly.",
            recommended_action="Proceed to contact verification.",
            responsible_person="System Automation",
        )

    @staticmethod
    def validate_contact(
        inv_row: pd.Series,
        ref_row: Optional[pd.Series],
        form_row: Optional[pd.Series],
    ) -> ValidationResult:
        """BR-CNT-007: Verify payer contact or resolve cross-parent payments via teacher remarks."""
        if ref_row is None:
            return ValidationResult(
                rule_id="BR-CNT-007",
                rule_name="Payer Contact Check",
                is_valid=False,
                status="FAIL",
                reason_code="ERR_CONTACT_REF_MISSING",
                reason_message="Reference student record missing.",
                recommended_action="Verify student profile.",
                responsible_person="Operations Associate",
            )

        inv_mob = inv_row.get("mobile")
        ref_mob = ref_row.get("registered_mobile_masked")
        inv_email = inv_row.get("email")
        ref_email = ref_row.get("registered_email_masked")
        remarks = (form_row.get("remarks") or "") if form_row is not None else ""

        # Direct exact match
        if inv_mob == ref_mob and inv_email == ref_email:
            return ValidationResult(
                rule_id="BR-CNT-007",
                rule_name="Payer Contact Check",
                is_valid=True,
                status="PASS",
                reason_code="SUCCESS_CONTACT_VERIFIED",
                reason_message="Payer mobile and email match LMS registered profile.",
                recommended_action="Proceed to batch capacity validation.",
                responsible_person="System Automation",
            )

        # Contact divergence: check for secondary parent remarks
        secondary_payer_keywords = ["mother", "father", "parent", "number", "mom", "dad", "phone"]
        has_remark = any(kw in remarks.lower() for kw in secondary_payer_keywords)

        if has_remark:
            return ValidationResult(
                rule_id="BR-CNT-007",
                rule_name="Payer Contact Divergence",
                is_valid=False,
                status="WARN",
                reason_code="WARN_SECONDARY_PARENT_PAYER",
                reason_message=f"Payer contact ({inv_mob}) differs from LMS profile ({ref_mob}). Teacher noted: '{remarks}'.",
                recommended_action="Ops 1-click verify: Confirm secondary parent payment, link mobile to student profile, and approve.",
                responsible_person="Operations Associate",
            )

        return ValidationResult(
            rule_id="BR-CNT-007",
            rule_name="Payer Contact Divergence",
            is_valid=False,
            status="FAIL",
            reason_code="ERR_UNVERIFIED_THIRD_PARTY_PAYER",
            reason_message=f"Payer contact ({inv_mob}) differs from profile ({ref_mob}) with no explanatory remark.",
            recommended_action="Call registered parent to verify payment authorization before proceeding.",
            responsible_person="Operations Associate",
        )

    @staticmethod
    def validate_batch_and_scheduling(
        form_row: Optional[pd.Series],
        ref_row: Optional[pd.Series],
        ref_df: pd.DataFrame,
    ) -> ValidationResult:
        """BR-BAT-010 & BR-BAT-011: Check batch capacity and continuation preferences."""
        if form_row is None or ref_row is None:
            return ValidationResult(
                rule_id="BR-BAT-010",
                rule_name="Batch Capacity Check",
                is_valid=False,
                status="FAIL",
                reason_code="ERR_BATCH_DATA_MISSING",
                reason_message="Form or reference row missing for batch capacity evaluation.",
                recommended_action="Check batch reference data.",
                responsible_person="Batch Planning Lead",
            )

        continue_same = str(form_row.get("continue_same_batch", "")).strip().capitalize()
        batch_id = form_row.get("current_classbatch_id")

        if continue_same == "No":
            pref_days = form_row.get("preferred_days", "Not specified")
            pref_time = form_row.get("preferred_time_slot", "Not specified")
            return ValidationResult(
                rule_id="BR-BAT-011",
                rule_name="Batch Change Preference",
                is_valid=False,
                status="WARN",
                reason_code="WARN_BATCH_CHANGE_SELECTION_PENDING",
                reason_message=f"Student requested batch change (Preferred: {pref_days} at {pref_time}).",
                recommended_action="Query LMS for matching weekend/alternate slots; send options to parent via WhatsApp.",
                responsible_person="Customer Success Specialist",
            )

        # Lookup batch in reference table
        batch_records = ref_df[ref_df["current_classbatch_id"] == str(batch_id)]
        if batch_records.empty:
            return ValidationResult(
                rule_id="BR-BAT-010",
                rule_name="Batch Capacity Check",
                is_valid=False,
                status="FAIL",
                reason_code="ERR_BATCH_NOT_FOUND",
                reason_message=f"Batch ID {batch_id} not found in reference batch directory.",
                recommended_action="Verify batch ID configuration in LMS.",
                responsible_person="Batch Planning Lead",
            )

        b_row = batch_records.iloc[0]
        active_count = int(b_row.get("active_students_count", 0))
        max_size = int(b_row.get("max_batch_size", 6))

        if active_count >= max_size:
            return ValidationResult(
                rule_id="BR-BAT-010",
                rule_name="Batch Capacity Check",
                is_valid=False,
                status="FAIL",
                reason_code="ERR_BATCH_CAPACITY_EXHAUSTED",
                reason_message=f"Batch {batch_id} ({b_row.get('classbatch_name')}) is at full capacity ({active_count}/{max_size}).",
                recommended_action="Alert Ops: Offer parallel open batch or request educator +1 capacity override.",
                responsible_person="Batch Planning Lead",
            )

        return ValidationResult(
            rule_id="BR-BAT-010",
            rule_name="Batch Capacity Check",
            is_valid=True,
            status="PASS",
            reason_code="SUCCESS_SAME_BATCH_SEAT_AVAILABLE",
            reason_message=f"Batch {batch_id} has seat available ({active_count}/{max_size} students).",
            recommended_action="Auto-allocate batch and generate schedule class slots.",
            responsible_person="System Automation",
        )

    @staticmethod
    def validate_pre_existing_bookings(
        invoice_id: str,
        bookings_df: pd.DataFrame,
        schedules_df: pd.DataFrame,
    ) -> ValidationResult:
        """BR-BKG-009: Guard against double-booking already scheduled renewals."""
        existing_schedules = schedules_df[schedules_df["invoice_id"] == str(invoice_id)]
        if not existing_schedules.empty:
            return ValidationResult(
                rule_id="BR-BKG-009",
                rule_name="Double-Booking Prevention",
                is_valid=True,
                status="PASS",
                reason_code="INFO_ALREADY_SCHEDULED_ACTIVE",
                reason_message=f"Invoice {invoice_id} already has {len(existing_schedules)} active class slots booked.",
                recommended_action="Maintain active schedule; suppress duplicate slot creation.",
                responsible_person="System Automation",
            )

        return ValidationResult(
            rule_id="BR-BKG-009",
            rule_name="Double-Booking Prevention",
            is_valid=True,
            status="PASS",
            reason_code="SUCCESS_NEW_RENEWAL_ELIGIBLE",
            reason_message="No prior duplicate class bookings detected.",
            recommended_action="Eligible for new slot creation.",
            responsible_person="System Automation",
        )

