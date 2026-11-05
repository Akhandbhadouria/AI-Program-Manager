"""
Unit tests for src/validation.py (BusinessValidator).
Verifies all atomic deterministic validation rules and reason codes from BUSINESS_RULES.md.
"""

import pytest
import pandas as pd
from src.validation import BusinessValidator, ValidationResult


class TestPaymentValidation:
    """Tests for BR-PAY-002 and BR-PAY-004."""

    def test_successful_full_payment(self):
        inv_row = pd.Series({
            "id": "84901",
            "payment_status": "Paid",
            "gateway_payment_id": "pay_P8x99****01",
            "paid_at_dt": pd.Timestamp("2026-11-01 10:15:22"),
            "net_amount": 12000.0,
        })
        res = BusinessValidator.validate_payment_status(inv_row)
        assert res.is_valid is True
        assert res.status == "PASS"
        assert res.reason_code == "SUCCESS_PAYMENT_CONFIRMED"

    def test_payment_failed(self):
        inv_row = pd.Series({
            "id": "84911",
            "payment_status": "Failed",
            "gateway_payment_id": None,
            "paid_at_dt": None,
            "net_amount": 12000.0,
        })
        res = BusinessValidator.validate_payment_status(inv_row)
        assert res.is_valid is False
        assert res.status == "FAIL"
        assert res.reason_code == "ERR_PAYMENT_STATUS_FAILED"

    def test_partial_payment(self):
        inv_row = pd.Series({
            "id": "84909",
            "payment_status": "Partially_Paid",
            "gateway_payment_id": "pay_P8x99****09",
            "paid_at_dt": pd.Timestamp("2026-11-03 10:00:00"),
            "net_amount": 5250.0,
        })
        res = BusinessValidator.validate_payment_status(inv_row)
        assert res.is_valid is False
        assert res.status == "WARN"
        assert res.reason_code == "WARN_PARTIAL_PAYMENT_PROVISIONAL"

    def test_missing_gateway_id(self):
        inv_row = pd.Series({
            "id": "84999",
            "payment_status": "Paid",
            "gateway_payment_id": None,
            "paid_at_dt": pd.Timestamp("2026-11-01 10:15:22"),
        })
        res = BusinessValidator.validate_payment_status(inv_row)
        assert res.is_valid is False
        assert res.status == "FAIL"
        assert res.reason_code == "ERR_PAYMENT_UNCONFIRMED_GATEWAY"

    def test_missing_invoice_row(self):
        res = BusinessValidator.validate_payment_status(None)
        assert res.is_valid is False
        assert res.status == "FAIL"
        assert res.reason_code == "ERR_INVOICE_NOT_FOUND"


class TestAmountValidation:
    """Tests for BR-PAY-003 and BR-PAY-005."""

    def test_amount_exact_match(self):
        inv_row = pd.Series({"net_amount": 10500.0, "amount": 10500.0, "discount_amount": 0.0, "payment_status": "Paid"})
        form_row = pd.Series({"amount_paid": 10500.0})
        ref_row = pd.Series({"standard_fee_24_sessions_inr": 10500.0})

        res = BusinessValidator.validate_amount_and_discount(inv_row, form_row, ref_row)
        assert res.is_valid is True
        assert res.status == "PASS"
        assert res.reason_code == "SUCCESS_AMOUNT_VERIFIED"

    def test_amount_mismatch(self):
        inv_row = pd.Series({"net_amount": 12000.0, "amount": 12000.0, "discount_amount": 0.0, "payment_status": "Paid"})
        form_row = pd.Series({"amount_paid": 10000.0})  # Under-reported by educator
        ref_row = pd.Series({"standard_fee_24_sessions_inr": 12000.0})

        res = BusinessValidator.validate_amount_and_discount(inv_row, form_row, ref_row)
        assert res.is_valid is False
        assert res.status == "FAIL"
        assert res.reason_code == "ERR_AMOUNT_FORM_INVOICE_MISMATCH"

    def test_promotional_discount_audit(self):
        inv_row = pd.Series({"net_amount": 7600.0, "amount": 9500.0, "discount_amount": 1900.0, "payment_status": "Paid"})
        form_row = pd.Series({"amount_paid": 7600.0})
        ref_row = pd.Series({"standard_fee_24_sessions_inr": 9500.0})

        res = BusinessValidator.validate_amount_and_discount(inv_row, form_row, ref_row)
        assert res.is_valid is True
        assert res.status == "WARN"
        assert res.reason_code == "INFO_DISCOUNT_AUDIT_REQUIRED"

    def test_missing_faculty_form(self):
        inv_row = pd.Series({"net_amount": 18000.0, "amount": 18000.0, "discount_amount": 0.0, "payment_status": "Paid"})
        res = BusinessValidator.validate_amount_and_discount(inv_row, None, None)
        assert res.is_valid is False
        assert res.status == "FAIL"
        assert res.reason_code == "ERR_MISSING_FACULTY_FORM"


class TestIdentityAndCourseValidation:
    """Tests for BR-STD-006."""

    def test_exact_alignment(self):
        inv_row = pd.Series({"student_id": "68101", "class_id": "104", "educator_id": "1102"})
        form_row = pd.Series({"student_id": "68101", "class_id": "104", "educator_id": "1102"})
        ref_row = pd.Series({"student_id": "68101", "class_id": "104", "educator_id": "1102"})

        res = BusinessValidator.validate_student_and_class(inv_row, form_row, ref_row)
        assert res.is_valid is True
        assert res.status == "PASS"
        assert res.reason_code == "SUCCESS_IDENTITY_ALIGNED"

    def test_student_id_mismatch(self):
        inv_row = pd.Series({"student_id": "68101", "class_id": "104", "educator_id": "1102"})
        form_row = pd.Series({"student_id": "68199", "class_id": "104", "educator_id": "1102"})  # Mismatch
        ref_row = pd.Series({"student_id": "68101", "class_id": "104", "educator_id": "1102"})

        res = BusinessValidator.validate_student_and_class(inv_row, form_row, ref_row)
        assert res.is_valid is False
        assert res.status == "FAIL"
        assert res.reason_code == "ERR_STUDENT_ID_MISMATCH"

    def test_class_id_mismatch(self):
        inv_row = pd.Series({"student_id": "68101", "class_id": "104", "educator_id": "1102"})
        form_row = pd.Series({"student_id": "68101", "class_id": "999", "educator_id": "1102"})  # Mismatch
        ref_row = pd.Series({"student_id": "68101", "class_id": "104", "educator_id": "1102"})

        res = BusinessValidator.validate_student_and_class(inv_row, form_row, ref_row)
        assert res.is_valid is False
        assert res.status == "FAIL"
        assert res.reason_code == "ERR_CLASS_MISMATCH"

    def test_educator_id_mismatch(self):
        inv_row = pd.Series({"student_id": "68101", "class_id": "104", "educator_id": "1102"})
        form_row = pd.Series({"student_id": "68101", "class_id": "104", "educator_id": "8888"})  # Mismatch
        ref_row = pd.Series({"student_id": "68101", "class_id": "104", "educator_id": "1102"})

        res = BusinessValidator.validate_student_and_class(inv_row, form_row, ref_row)
        assert res.is_valid is False
        assert res.status == "FAIL"
        assert res.reason_code == "ERR_EDUCATOR_MISMATCH"

    def test_student_not_in_master(self):
        inv_row = pd.Series({"student_id": "99999", "class_id": "104", "educator_id": "1102"})
        res = BusinessValidator.validate_student_and_class(inv_row, None, None)
        assert res.is_valid is False
        assert res.status == "FAIL"
        assert res.reason_code == "ERR_STUDENT_NOT_IN_MASTER"


class TestContactValidation:
    """Tests for BR-CNT-007."""

    def test_contact_exact_match(self):
        inv_row = pd.Series({"mobile": "+91-9811XXXX01", "email": "pr***a.sh***@gmail.com"})
        ref_row = pd.Series({"registered_mobile_masked": "+91-9811XXXX01", "registered_email_masked": "pr***a.sh***@gmail.com"})
        form_row = pd.Series({"remarks": ""})

        res = BusinessValidator.validate_contact(inv_row, ref_row, form_row)
        assert res.is_valid is True
        assert res.status == "PASS"
        assert res.reason_code == "SUCCESS_CONTACT_VERIFIED"

    def test_contact_divergence_with_secondary_remark(self):
        inv_row = pd.Series({"mobile": "+91-9844XXXX77", "email": "ri***u.iy***@gmail.com"})
        ref_row = pd.Series({"registered_mobile_masked": "+91-9844XXXX04", "registered_email_masked": "su***h.iy***@outlook.com"})
        form_row = pd.Series({"remarks": "Mother paid from her number"})

        res = BusinessValidator.validate_contact(inv_row, ref_row, form_row)
        assert res.is_valid is False
        assert res.status == "WARN"
        assert res.reason_code == "WARN_SECONDARY_PARENT_PAYER"

    def test_contact_divergence_without_remark(self):
        inv_row = pd.Series({"mobile": "+91-9899XXXX99", "email": "unknown@example.com"})
        ref_row = pd.Series({"registered_mobile_masked": "+91-9811XXXX01", "registered_email_masked": "known@example.com"})
        form_row = pd.Series({"remarks": "Clean renewal"})

        res = BusinessValidator.validate_contact(inv_row, ref_row, form_row)
        assert res.is_valid is False
        assert res.status == "FAIL"
        assert res.reason_code == "ERR_UNVERIFIED_THIRD_PARTY_PAYER"


class TestBatchAndSchedulingValidation:
    """Tests for BR-BAT-010, BR-BAT-011, and BR-BKG-009."""

    @pytest.fixture
    def mock_ref_df(self):
        return pd.DataFrame([
            {"current_classbatch_id": "9201", "classbatch_name": "Batch-A", "active_students_count": 4, "max_batch_size": 6},
            {"current_classbatch_id": "9205", "classbatch_name": "Batch-D", "active_students_count": 6, "max_batch_size": 6},
        ])

    def test_same_batch_available(self, mock_ref_df):
        form_row = pd.Series({"continue_same_batch": "Yes", "current_classbatch_id": "9201"})
        ref_row = pd.Series({"current_classbatch_id": "9201"})

        res = BusinessValidator.validate_batch_and_scheduling(form_row, ref_row, mock_ref_df)
        assert res.is_valid is True
        assert res.status == "PASS"
        assert res.reason_code == "SUCCESS_SAME_BATCH_SEAT_AVAILABLE"

    def test_batch_capacity_full(self, mock_ref_df):
        form_row = pd.Series({"continue_same_batch": "Yes", "current_classbatch_id": "9205"})
        ref_row = pd.Series({"current_classbatch_id": "9205"})

        res = BusinessValidator.validate_batch_and_scheduling(form_row, ref_row, mock_ref_df)
        assert res.is_valid is False
        assert res.status == "FAIL"
        assert res.reason_code == "ERR_BATCH_CAPACITY_EXHAUSTED"

    def test_batch_change_requested(self, mock_ref_df):
        form_row = pd.Series({"continue_same_batch": "No", "preferred_days": "Sat,Sun", "preferred_time_slot": "11:00:00"})
        ref_row = pd.Series({"current_classbatch_id": "9201"})

        res = BusinessValidator.validate_batch_and_scheduling(form_row, ref_row, mock_ref_df)
        assert res.is_valid is False
        assert res.status == "WARN"
        assert res.reason_code == "WARN_BATCH_CHANGE_SELECTION_PENDING"

    def test_existing_schedule_detected(self):
        schedules_df = pd.DataFrame([{"invoice_id": "84901", "classschedule_id": "2126100101"}])
        bookings_df = pd.DataFrame([{"invoice_id": "84901", "request_status": "Completed"}])

        res = BusinessValidator.validate_pre_existing_bookings("84901", bookings_df, schedules_df)
        assert res.is_valid is True
        assert res.reason_code == "INFO_ALREADY_SCHEDULED_ACTIVE"

    def test_no_prior_schedule(self):
        schedules_df = pd.DataFrame(columns=["invoice_id", "classschedule_id"])
        bookings_df = pd.DataFrame(columns=["invoice_id", "request_status"])

        res = BusinessValidator.validate_pre_existing_bookings("84902", bookings_df, schedules_df)
        assert res.is_valid is True
        assert res.reason_code == "SUCCESS_NEW_RENEWAL_ELIGIBLE"

