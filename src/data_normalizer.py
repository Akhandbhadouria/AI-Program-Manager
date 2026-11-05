"""
Module: src/data_normalizer.py
Description: Normalizes raw string data into strongly typed, sanitized formats
for deterministic validation and comparison across tables.
Handles missing columns gracefully without throwing KeyError.
"""

import logging
import re
from typing import Optional, Any
import numpy as np
import pandas as pd

logger = logging.getLogger("reconciliation.data_normalizer")


def clean_str(val: Any) -> Optional[str]:
    """Cleans string values, converting 'NULL', 'nan', empty strings to None."""
    if val is None or pd.isna(val):
        return None
    s = str(val).strip()
    if s.upper() in ("NULL", "NAN", "NONE", ""):
        return None
    return s


def clean_id(val: Any) -> Optional[str]:
    """Cleans numeric/alphanumeric IDs to standard string representation without decimals."""
    if val is None or pd.isna(val):
        return None
    s = str(val).strip()
    if s.upper() in ("NULL", "NAN", "NONE", ""):
        return None
    if re.match(r"^\d+\.0+$", s):
        s = s.split(".")[0]
    return s


def clean_float(val: Any, default: Optional[float] = None) -> Optional[float]:
    """Parses numeric amount fields safely to float."""
    if val is None or pd.isna(val):
        return default
    s = str(val).strip().replace(",", "")
    if s.upper() in ("NULL", "NAN", "NONE", ""):
        return default
    try:
        return float(s)
    except (ValueError, TypeError):
        return default


def clean_int(val: Any, default: Optional[int] = None) -> Optional[int]:
    """Parses integer counts safely."""
    f = clean_float(val)
    if f is None:
        return default
    return int(round(f))


def clean_phone(val: Any) -> Optional[str]:
    """
    Normalizes phone numbers by stripping whitespace.
    Preserves mask characters ('X') and country codes for exact string matching.
    """
    s = clean_str(val)
    if s is None:
        return None
    s = re.sub(r"\s*-\s*", "-", s)
    return s.strip()


def clean_email(val: Any) -> Optional[str]:
    """Normalizes email addresses to lowercase stripped string."""
    s = clean_str(val)
    if s is None:
        return None
    return s.lower()


def clean_datetime(val: Any) -> Optional[pd.Timestamp]:
    """Parses timestamp strings into pd.Timestamp."""
    s = clean_str(val)
    if s is None:
        return None
    try:
        return pd.to_datetime(s)
    except Exception:
        return None


class DataNormalizer:
    """Orchestrates normalization across all 5 datasets, resilient to missing columns."""

    @staticmethod
    def _apply_or_default(df: pd.DataFrame, col: str, func, default=None) -> pd.Series:
        if col in df.columns:
            return df[col].apply(func)
        return pd.Series([default] * len(df), index=df.index)

    @classmethod
    def normalize_invoices(cls, df: pd.DataFrame) -> pd.DataFrame:
        norm = df.copy()
        norm["id"] = cls._apply_or_default(norm, "id", clean_id)
        norm["invoice_number"] = cls._apply_or_default(norm, "invoice_number", clean_str)
        norm["user_id"] = cls._apply_or_default(norm, "user_id", clean_id)
        norm["student_id"] = cls._apply_or_default(norm, "student_id", clean_id)
        norm["class_id"] = cls._apply_or_default(norm, "class_id", clean_id)
        norm["educator_id"] = cls._apply_or_default(norm, "educator_id", clean_id)
        norm["parent_name"] = cls._apply_or_default(norm, "parent_name", clean_str)
        norm["mobile"] = cls._apply_or_default(norm, "mobile", clean_phone)
        norm["email"] = cls._apply_or_default(norm, "email", clean_email)
        norm["currency"] = cls._apply_or_default(norm, "currency", clean_str)
        norm["amount"] = cls._apply_or_default(norm, "amount", lambda v: clean_float(v, 0.0), 0.0)
        norm["discount_amount"] = cls._apply_or_default(norm, "discount_amount", lambda v: clean_float(v, 0.0), 0.0)
        norm["net_amount"] = cls._apply_or_default(norm, "net_amount", lambda v: clean_float(v, 0.0), 0.0)
        norm["payment_type"] = cls._apply_or_default(norm, "payment_type", clean_str)
        norm["payment_mode"] = cls._apply_or_default(norm, "payment_mode", clean_str)
        norm["payment_gateway"] = cls._apply_or_default(norm, "payment_gateway", clean_str)
        norm["gateway_order_id"] = cls._apply_or_default(norm, "gateway_order_id", clean_str)
        norm["gateway_payment_id"] = cls._apply_or_default(norm, "gateway_payment_id", clean_str)
        norm["payment_status"] = cls._apply_or_default(norm, "payment_status", clean_str)
        norm["is_renewal"] = cls._apply_or_default(norm, "is_renewal", clean_str)
        norm["paid_at_dt"] = cls._apply_or_default(norm, "paid_at", clean_datetime)
        norm["created_at_dt"] = cls._apply_or_default(norm, "created_at", clean_datetime)
        return norm

    @classmethod
    def normalize_faculty_form(cls, df: pd.DataFrame) -> pd.DataFrame:
        norm = df.copy()
        norm["id"] = cls._apply_or_default(norm, "id", clean_id)
        norm["educator_id"] = cls._apply_or_default(norm, "educator_id", clean_id)
        norm["educator_name"] = cls._apply_or_default(norm, "educator_name", clean_str)
        norm["user_id"] = cls._apply_or_default(norm, "user_id", clean_id)
        norm["student_id"] = cls._apply_or_default(norm, "student_id", clean_id)
        norm["student_name"] = cls._apply_or_default(norm, "student_name", clean_str)
        norm["parent_mobile"] = cls._apply_or_default(norm, "parent_mobile", clean_phone)
        norm["class_id"] = cls._apply_or_default(norm, "class_id", clean_id)
        norm["current_classbatch_id"] = cls._apply_or_default(norm, "current_classbatch_id", clean_id)
        norm["invoice_id"] = cls._apply_or_default(norm, "invoice_id", clean_id)
        norm["amount_paid"] = cls._apply_or_default(norm, "amount_paid", lambda v: clean_float(v, 0.0), 0.0)
        norm["sessions_purchased"] = cls._apply_or_default(norm, "sessions_purchased", lambda v: clean_int(v, 24), 24)
        norm["continue_same_batch"] = cls._apply_or_default(norm, "continue_same_batch", clean_str)
        norm["preferred_days"] = cls._apply_or_default(norm, "preferred_days", clean_str)
        norm["preferred_time_slot"] = cls._apply_or_default(norm, "preferred_time_slot", clean_str)
        norm["remarks"] = cls._apply_or_default(norm, "remarks", clean_str)
        norm["approval_status"] = cls._apply_or_default(norm, "approval_status", clean_str)
        norm["approved_by"] = cls._apply_or_default(norm, "approved_by", clean_str)
        norm["approved_at_dt"] = cls._apply_or_default(norm, "approved_at", clean_datetime)
        norm["created_at_dt"] = cls._apply_or_default(norm, "created_at", clean_datetime)
        return norm

    @classmethod
    def normalize_booking_requests(cls, df: pd.DataFrame) -> pd.DataFrame:
        norm = df.copy()
        norm["id"] = cls._apply_or_default(norm, "id", clean_id)
        norm["faculty_form_id"] = cls._apply_or_default(norm, "faculty_form_id", clean_id)
        norm["invoice_id"] = cls._apply_or_default(norm, "invoice_id", clean_id)
        norm["user_id"] = cls._apply_or_default(norm, "user_id", clean_id)
        norm["student_id"] = cls._apply_or_default(norm, "student_id", clean_id)
        norm["class_id"] = cls._apply_or_default(norm, "class_id", clean_id)
        norm["educator_id"] = cls._apply_or_default(norm, "educator_id", clean_id)
        norm["classbatch_id"] = cls._apply_or_default(norm, "classbatch_id", clean_id)
        norm["sessions_count"] = cls._apply_or_default(norm, "sessions_count", lambda v: clean_int(v, 24), 24)
        norm["continue_same_batch"] = cls._apply_or_default(norm, "continue_same_batch", clean_str)
        norm["request_status"] = cls._apply_or_default(norm, "request_status", clean_str)
        norm["batch_allocated"] = cls._apply_or_default(norm, "batch_allocated", clean_str)
        norm["allocated_by"] = cls._apply_or_default(norm, "allocated_by", clean_str)
        norm["allocated_at_dt"] = cls._apply_or_default(norm, "allocated_at", clean_datetime)
        norm["created_at_dt"] = cls._apply_or_default(norm, "created_at", clean_datetime)
        return norm

    @classmethod
    def normalize_class_schedule_bookings(cls, df: pd.DataFrame) -> pd.DataFrame:
        norm = df.copy()
        norm["id"] = cls._apply_or_default(norm, "id", clean_id)
        norm["bookingrequest_id"] = cls._apply_or_default(norm, "bookingrequest_id", clean_id)
        norm["invoice_id"] = cls._apply_or_default(norm, "invoice_id", clean_id)
        norm["classschedule_id"] = cls._apply_or_default(norm, "classschedule_id", clean_id)
        norm["classbatch_id"] = cls._apply_or_default(norm, "classbatch_id", clean_id)
        norm["class_id"] = cls._apply_or_default(norm, "class_id", clean_id)
        norm["student_id"] = cls._apply_or_default(norm, "student_id", clean_id)
        norm["educator_id"] = cls._apply_or_default(norm, "educator_id", clean_id)
        norm["class_date"] = cls._apply_or_default(norm, "class_date", clean_str)
        norm["start_time"] = cls._apply_or_default(norm, "start_time", clean_str)
        norm["end_time"] = cls._apply_or_default(norm, "end_time", clean_str)
        norm["booking_type"] = cls._apply_or_default(norm, "booking_type", clean_str)
        norm["is_cancelled"] = cls._apply_or_default(norm, "is_cancelled", clean_str)
        norm["attended_class"] = cls._apply_or_default(norm, "attended_class", clean_str)
        norm["created_at_dt"] = cls._apply_or_default(norm, "created_at", clean_datetime)
        return norm

    @classmethod
    def normalize_reference(cls, df: pd.DataFrame) -> pd.DataFrame:
        norm = df.copy()
        norm["student_id"] = cls._apply_or_default(norm, "student_id", clean_id)
        norm["user_id"] = cls._apply_or_default(norm, "user_id", clean_id)
        norm["student_name_masked"] = cls._apply_or_default(norm, "student_name_masked", clean_str)
        norm["parent_name_masked"] = cls._apply_or_default(norm, "parent_name_masked", clean_str)
        norm["registered_mobile_masked"] = cls._apply_or_default(norm, "registered_mobile_masked", clean_phone)
        norm["registered_email_masked"] = cls._apply_or_default(norm, "registered_email_masked", clean_email)
        norm["current_classbatch_id"] = cls._apply_or_default(norm, "current_classbatch_id", clean_id)
        norm["classbatch_name"] = cls._apply_or_default(norm, "classbatch_name", clean_str)
        norm["class_id"] = cls._apply_or_default(norm, "class_id", clean_id)
        norm["class_name"] = cls._apply_or_default(norm, "class_name", clean_str)
        norm["category_id"] = cls._apply_or_default(norm, "category_id", clean_id)
        norm["category_name"] = cls._apply_or_default(norm, "category_name", clean_str)
        norm["educator_id"] = cls._apply_or_default(norm, "educator_id", clean_id)
        norm["educator_name"] = cls._apply_or_default(norm, "educator_name", clean_str)
        norm["standard_fee_24_sessions_inr"] = cls._apply_or_default(norm, "standard_fee_24_sessions_inr", lambda v: clean_float(v, 0.0), 0.0)
        norm["batch_days"] = cls._apply_or_default(norm, "batch_days", clean_str)
        norm["batch_start_time"] = cls._apply_or_default(norm, "batch_start_time", clean_str)
        norm["active_students_count"] = cls._apply_or_default(norm, "active_students_count", lambda v: clean_int(v, 0), 0)
        norm["max_batch_size"] = cls._apply_or_default(norm, "max_batch_size", lambda v: clean_int(v, 6), 6)
        return norm
