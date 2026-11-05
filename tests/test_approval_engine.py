"""
End-to-end tests for the ApprovalEngine and main reconciliation pipeline.
Verifies operational edge cases, reason codes, safety guarantees (invalid records never approved),
and idempotency over repeated runs.
"""

import os
import pytest
import pandas as pd
from main import run_pipeline
from src.data_loader import load_all_datasets
from src.reconciliation import DataReconciler
from src.approval_engine import ApprovalEngine


@pytest.fixture(scope="module")
def pipeline_results():
    """Runs the pipeline once and caches results for inspection."""
    df_app, df_exc, df_rev = run_pipeline()
    return df_app, df_exc, df_rev


class TestApprovalEngineEndToEnd:
    """End-to-end tests executed on the real Bambinos.live datasets."""

    def test_overall_record_counts(self, pipeline_results):
        df_app, df_exc, df_rev = pipeline_results
        total = len(df_app) + len(df_exc) + len(df_rev)
        assert total == 13, f"Expected 13 records total, got {total}"
        assert len(df_app) == 3, f"Expected exactly 3 AUTO_APPROVED records, got {len(df_app)}"
        assert len(df_exc) == 6, f"Expected exactly 6 FLAGGED_EXCEPTION records, got {len(df_exc)}"
        assert len(df_rev) == 4, f"Expected exactly 4 PENDING_HUMAN_REVIEW records, got {len(df_rev)}"

    def test_auto_approved_membership(self, pipeline_results):
        df_app, _, _ = pipeline_results
        approved_ids = set(df_app["invoice_id"].astype(str))
        expected_approved = {"84901", "84902", "84903"}
        assert approved_ids == expected_approved, f"Unexpected approved IDs: {approved_ids}"

        # Verify scheduling information is present for all approved records
        required_cols = [
            "invoice_id", "student_id", "student_name", "class_id", "class_name",
            "classbatch_id", "classbatch_name", "educator_id", "educator_name",
            "sessions_count", "batch_days", "batch_start_time", "net_amount_paid", "action_taken"
        ]
        for col in required_cols:
            assert col in df_app.columns, f"Missing required scheduling column: {col}"
            assert df_app[col].notna().all(), f"Found NaN values in approved column: {col}"

    def test_never_auto_approve_failed_payment(self, pipeline_results):
        df_app, df_exc, _ = pipeline_results
        # Invoice 84911 is Failed payment
        assert "84911" not in df_app["invoice_id"].values
        row = df_exc[df_exc["invoice_id"] == "84911"].iloc[0]
        assert row["reason_code"] == "ERR_PAYMENT_STATUS_FAILED"
        assert row["failure_category"] == "Financial Leakage Risk"

    def test_never_auto_approve_partial_payment(self, pipeline_results):
        df_app, _, df_rev = pipeline_results
        # Invoice 84909 is Partially_Paid (Installment 1)
        assert "84909" not in df_app["invoice_id"].values
        row = df_rev[df_rev["invoice_id"] == "84909"].iloc[0]
        assert row["reason_code"] == "WARN_PARTIAL_PAYMENT_PROVISIONAL"

    def test_never_auto_approve_batch_full(self, pipeline_results):
        df_app, df_exc, _ = pipeline_results
        # Invoice 84905 is in batch 9205 which is 6/6
        assert "84905" not in df_app["invoice_id"].values
        row = df_exc[df_exc["invoice_id"] == "84905"].iloc[0]
        assert row["reason_code"] == "ERR_BATCH_CAPACITY_EXHAUSTED"

    def test_never_auto_approve_missing_form(self, pipeline_results):
        df_app, df_exc, _ = pipeline_results
        # Invoices 84906 and 84910 have no faculty forms
        assert "84906" not in df_app["invoice_id"].values
        assert "84910" not in df_app["invoice_id"].values
        for inv_id in ["84906", "84910"]:
            row = df_exc[df_exc["invoice_id"] == inv_id].iloc[0]
            assert row["reason_code"] == "ERR_MISSING_FACULTY_FORM"

    def test_never_auto_approve_duplicate_forms(self, pipeline_results):
        df_app, df_exc, _ = pipeline_results
        # Invoice 84908 has duplicate forms 3308 and 3309
        assert "84908" not in df_app["invoice_id"].values
        row = df_exc[df_exc["invoice_id"] == "84908"].iloc[0]
        assert row["reason_code"] == "ERR_DUPLICATE_FORM_SUBMISSION"

    def test_never_auto_approve_ghost_invoice_typo(self, pipeline_results):
        df_app, df_exc, _ = pipeline_results
        # Invoice 84913 has form with typo 84931
        assert "84913" not in df_app["invoice_id"].values
        row = df_exc[df_exc["invoice_id"] == "84913"].iloc[0]
        assert row["reason_code"] == "ERR_INVOICE_NOT_FOUND_REPAIRABLE"

    def test_secondary_parent_contact_review(self, pipeline_results):
        _, _, df_rev = pipeline_results
        # Invoice 84904 (Mother paid)
        row = df_rev[df_rev["invoice_id"] == "84904"].iloc[0]
        assert row["reason_code"] == "WARN_SECONDARY_PARENT_PAYER"
        assert row["review_category"] == "Payer Contact Divergence"

    def test_batch_change_preference_review(self, pipeline_results):
        _, _, df_rev = pipeline_results
        # Invoice 84912 requested weekend batch change
        row = df_rev[df_rev["invoice_id"] == "84912"].iloc[0]
        assert row["reason_code"] == "WARN_BATCH_CHANGE_SELECTION_PENDING"

    def test_discount_audit_review(self, pipeline_results):
        _, _, df_rev = pipeline_results
        # Invoice 84907 has 20% discount
        row = df_rev[df_rev["invoice_id"] == "84907"].iloc[0]
        assert row["reason_code"] == "INFO_DISCOUNT_AUDIT_REQUIRED"


class TestIdempotencyAndNoDuplicates:
    """Verifies that running the pipeline repeatedly is completely idempotent and safe."""

    def test_repeated_runs_produce_identical_results(self):
        """Pipeline must be strictly idempotent with zero state mutation."""
        run1_app, run1_exc, run1_rev = run_pipeline()
        run2_app, run2_exc, run2_rev = run_pipeline()

        pd.testing.assert_frame_equal(
            run1_app.drop(columns=["approval_timestamp"], errors="ignore"),
            run2_app.drop(columns=["approval_timestamp"], errors="ignore")
        )
        pd.testing.assert_frame_equal(run1_exc, run2_exc)
        pd.testing.assert_frame_equal(run1_rev, run2_rev)

    def test_no_duplicate_class_bookings(self, pipeline_results):
        """Verifies that already-scheduled renewals are marked without generating double bookings."""
        df_app, _, _ = pipeline_results
        # Invoice 84901 already has class schedule bookings
        row_84901 = df_app[df_app["invoice_id"] == "84901"].iloc[0]
        assert "Pre-existing scheduled slots active" in row_84901["action_taken"]
