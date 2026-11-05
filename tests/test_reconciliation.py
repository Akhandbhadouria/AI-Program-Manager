"""
Unit tests for src/reconciliation.py and src/data_normalizer.py.
Verifies multi-table linkage, deduplication, orphan detection, and normalization under edge cases.
"""

import pytest
import pandas as pd
import numpy as np

from src.data_loader import DatasetBundle
from src.data_normalizer import (
    clean_str, clean_id, clean_float, clean_int, clean_phone, clean_email,
    DataNormalizer
)
from src.reconciliation import DataReconciler, ReconciledRecord


class TestDataNormalizer:
    """Verifies that data normalization safely handles dirty, malformed, or missing inputs."""

    def test_clean_str(self):
        assert clean_str("  Hello  ") == "Hello"
        assert clean_str("NULL") is None
        assert clean_str("null") is None
        assert clean_str("NaN") is None
        assert clean_str("") is None
        assert clean_str(None) is None
        assert clean_str(np.nan) is None

    def test_clean_id(self):
        assert clean_id("84901") == "84901"
        assert clean_id("84901.0") == "84901"
        assert clean_id("  68101  ") == "68101"
        assert clean_id("NULL") is None
        assert clean_id("") is None

    def test_clean_float(self):
        assert clean_float("12,000.50") == 12000.50
        assert clean_float("  9500  ") == 9500.0
        assert clean_float("NULL", default=0.0) == 0.0
        assert clean_float("invalid", default=0.0) == 0.0
        assert clean_float(None, default=0.0) == 0.0

    def test_clean_int(self):
        assert clean_int("24") == 24
        assert clean_int("24.0") == 24
        assert clean_int("NULL", default=6) == 6
        assert clean_int(None, default=6) == 6

    def test_clean_phone(self):
        assert clean_phone(" +91-9811XXXX01 ") == "+91-9811XXXX01"
        assert clean_phone("+91 - 9811XXXX01") == "+91-9811XXXX01"
        assert clean_phone("NULL") is None

    def test_clean_email(self):
        assert clean_email("  TEST@EXAMPLE.COM  ") == "test@example.com"
        assert clean_email("NULL") is None


class TestReconciliationLogic:
    """Verifies multi-table cross-referencing and entity resolution."""

    @pytest.fixture
    def mock_bundle(self):
        invoices = pd.DataFrame([
            {"id": "84901", "student_id": "68101", "class_id": "104", "educator_id": "1102", "net_amount": "12000.00", "payment_status": "Paid"},
            {"id": "84906", "student_id": "68106", "class_id": "108", "educator_id": "1102", "net_amount": "18000.00", "payment_status": "Paid"},
            {"id": "84908", "student_id": "68108", "class_id": "302", "educator_id": "1115", "net_amount": "22000.00", "payment_status": "Paid"},
            {"id": "84913", "student_id": "68113", "class_id": "501", "educator_id": "1130", "net_amount": "11500.00", "payment_status": "Paid"},
        ])
        faculty_form = pd.DataFrame([
            {"id": "3301", "invoice_id": "84901", "student_id": "68101", "class_id": "104", "educator_id": "1102", "amount_paid": "12000.00", "created_at": "2026-11-01 10:45:00"},
            {"id": "3308", "invoice_id": "84908", "student_id": "68108", "class_id": "302", "educator_id": "1115", "amount_paid": "22000.00", "created_at": "2026-11-03 08:30:00"},
            {"id": "3309", "invoice_id": "84908", "student_id": "68108", "class_id": "302", "educator_id": "1115", "amount_paid": "22000.00", "created_at": "2026-11-03 08:35:12"},
            {"id": "3313", "invoice_id": "84931", "student_id": "68113", "class_id": "501", "educator_id": "1130", "amount_paid": "11500.00", "created_at": "2026-11-03 17:10:00"},
        ])
        booking_requests = pd.DataFrame([
            {"id": "5501", "invoice_id": "84901", "faculty_form_id": "3301", "student_id": "68101", "request_status": "Completed"}
        ])
        class_schedules = pd.DataFrame([
            {"id": "990101", "invoice_id": "84901", "bookingrequest_id": "5501", "class_date": "2026-11-03"}
        ])
        reference = pd.DataFrame([
            {"student_id": "68101", "class_id": "104", "educator_id": "1102", "current_classbatch_id": "9201", "active_students_count": 4, "max_batch_size": 6},
            {"student_id": "68106", "class_id": "108", "educator_id": "1102", "current_classbatch_id": "9206", "active_students_count": 5, "max_batch_size": 6},
            {"student_id": "68108", "class_id": "302", "educator_id": "1115", "current_classbatch_id": "9208", "active_students_count": 5, "max_batch_size": 6},
            {"student_id": "68113", "class_id": "501", "educator_id": "1130", "current_classbatch_id": "9213", "active_students_count": 4, "max_batch_size": 6},
        ])

        return DatasetBundle(
            invoices=invoices,
            faculty_form=faculty_form,
            booking_requests=booking_requests,
            class_schedule_bookings=class_schedules,
            reference=reference,
        )

    def test_clean_linking(self, mock_bundle):
        reconciler = DataReconciler(mock_bundle)
        records = reconciler.reconcile_all()
        rec_84901 = next(r for r in records if r.invoice_id == "84901")

        assert rec_84901.has_form is True
        assert rec_84901.has_invoice is True
        assert rec_84901.is_duplicate_form is False
        assert rec_84901.already_scheduled_count == 1
        assert str(rec_84901.faculty_form_row["id"]) == "3301"

    def test_missing_faculty_form_detected(self, mock_bundle):
        reconciler = DataReconciler(mock_bundle)
        records = reconciler.reconcile_all()
        rec_84906 = next(r for r in records if r.invoice_id == "84906")

        assert rec_84906.has_invoice is True
        assert rec_84906.has_form is False
        assert rec_84906.faculty_form_row is None

    def test_duplicate_faculty_forms_detected(self, mock_bundle):
        reconciler = DataReconciler(mock_bundle)
        records = reconciler.reconcile_all()
        rec_84908 = next(r for r in records if r.invoice_id == "84908")

        assert rec_84908.is_duplicate_form is True
        assert rec_84908.all_form_ids == ["3308", "3309"]
        # Primary should be the earlier submission (3308)
        assert str(rec_84908.faculty_form_row["id"]) == "3308"

    def test_orphan_form_typo_repair_detected(self, mock_bundle):
        reconciler = DataReconciler(mock_bundle)
        records = reconciler.reconcile_all()
        rec_84913 = next(r for r in records if r.invoice_id == "84913")

        assert rec_84913.orphan_form_invoice_ref == "84931"
        assert rec_84913.candidate_repair_invoice == "84913"
        assert str(rec_84913.faculty_form_row["id"]) == "3313"

    def test_malformed_csv_missing_columns(self):
        """Engine should not crash when columns are missing or empty."""
        empty_df = pd.DataFrame()
        norm_inv = DataNormalizer.normalize_invoices(pd.DataFrame([{"id": "999"}]))
        assert "net_amount" in norm_inv.columns
        assert norm_inv.iloc[0]["net_amount"] == 0.0

