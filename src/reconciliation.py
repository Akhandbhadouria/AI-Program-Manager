"""
Module: src/reconciliation.py
Description: Multi-table entity reconciliation and linkage across the 5 datasets.
Correlates invoices, educator forms, student reference master, booking requests, and class slots.
Detects duplicates, orphan forms, missing forms, and candidate repairs.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import pandas as pd

from src.data_loader import DatasetBundle
from src.data_normalizer import DataNormalizer

logger = logging.getLogger("reconciliation.engine")


@dataclass
class ReconciledRecord:
    """Unified container representing a single student renewal lifecycle record."""
    invoice_id: str
    student_id: str
    class_id: str
    educator_id: str
    
    # Linked source rows
    invoice_row: Optional[pd.Series] = None
    faculty_form_row: Optional[pd.Series] = None
    reference_row: Optional[pd.Series] = None
    booking_request_row: Optional[pd.Series] = None
    class_slots: List[pd.Series] = field(default_factory=list)
    
    # Structural linkage flags
    has_form: bool = True
    has_invoice: bool = True
    is_duplicate_form: bool = False
    all_form_ids: List[str] = field(default_factory=list)
    orphan_form_invoice_ref: Optional[str] = None
    candidate_repair_invoice: Optional[str] = None
    already_scheduled_count: int = 0


class DataReconciler:
    """Performs multi-key cross-table correlation across all five normalized datasets."""

    def __init__(self, bundle: DatasetBundle):
        self.raw_bundle = bundle
        # Create normalized copies
        self.invoices = DataNormalizer.normalize_invoices(bundle.invoices)
        self.faculty_forms = DataNormalizer.normalize_faculty_form(bundle.faculty_form)
        self.booking_requests = DataNormalizer.normalize_booking_requests(bundle.booking_requests)
        self.class_schedules = DataNormalizer.normalize_class_schedule_bookings(bundle.class_schedule_bookings)
        self.reference = DataNormalizer.normalize_reference(bundle.reference)

    def reconcile_all(self) -> List[ReconciledRecord]:
        """
        Executes end-to-end reconciliation across all records.
        Returns a list of ReconciledRecord objects capturing the state of each renewal.
        """
        reconciled_records: List[ReconciledRecord] = []
        processed_invoices = set()
        processed_forms = set()

        # Step 1: Check for duplicate forms submitted for the same invoice_id
        forms_by_invoice: Dict[str, List[pd.Series]] = {}
        for _, form in self.faculty_forms.iterrows():
            inv_ref = form.get("invoice_id")
            if inv_ref:
                forms_by_invoice.setdefault(inv_ref, []).append(form)

        # Step 2: Iterate through all invoices (Primary ledger of payments)
        for _, inv_row in self.invoices.iterrows():
            inv_id = str(inv_row["id"])
            std_id = str(inv_row["student_id"])
            class_id = str(inv_row["class_id"])
            edu_id = str(inv_row["educator_id"])
            processed_invoices.add(inv_id)

            # Match reference row on student_id
            ref_match = self.reference[self.reference["student_id"] == std_id]
            ref_row = ref_match.iloc[0] if not ref_match.empty else None

            # Match booking request on invoice_id
            br_match = self.booking_requests[self.booking_requests["invoice_id"] == inv_id]
            br_row = br_match.iloc[0] if not br_match.empty else None

            # Match scheduled slots on invoice_id
            cs_match = self.class_schedules[self.class_schedules["invoice_id"] == inv_id]
            slots = [row for _, row in cs_match.iterrows()]

            # Match faculty forms
            matching_forms = forms_by_invoice.get(inv_id, [])
            
            if len(matching_forms) == 0:
                # Check if there is an orphan form that matches this student_id and class_id
                orphan_candidates = self.faculty_forms[
                    (self.faculty_forms["student_id"] == std_id) &
                    (self.faculty_forms["class_id"] == class_id) &
                    (~self.faculty_forms["invoice_id"].isin(self.invoices["id"]))
                ]
                if not orphan_candidates.empty:
                    # Found orphan candidate with typo in invoice_id (e.g., Form 3313 with 84931 for Invoice 84913)
                    candidate_form = orphan_candidates.iloc[0]
                    form_id = str(candidate_form["id"])
                    processed_forms.add(form_id)
                    rec = ReconciledRecord(
                        invoice_id=inv_id,
                        student_id=std_id,
                        class_id=class_id,
                        educator_id=edu_id,
                        invoice_row=inv_row,
                        faculty_form_row=candidate_form,
                        reference_row=ref_row,
                        booking_request_row=br_row,
                        class_slots=slots,
                        has_form=True,
                        has_invoice=True,
                        orphan_form_invoice_ref=str(candidate_form["invoice_id"]),
                        candidate_repair_invoice=inv_id,
                        all_form_ids=[form_id],
                        already_scheduled_count=len(slots),
                    )
                else:
                    # Invoice exists, but teacher never submitted a faculty form
                    rec = ReconciledRecord(
                        invoice_id=inv_id,
                        student_id=std_id,
                        class_id=class_id,
                        educator_id=edu_id,
                        invoice_row=inv_row,
                        faculty_form_row=None,
                        reference_row=ref_row,
                        booking_request_row=br_row,
                        class_slots=slots,
                        has_form=False,
                        has_invoice=True,
                        all_form_ids=[],
                        already_scheduled_count=len(slots),
                    )
            elif len(matching_forms) == 1:
                # Exactly 1 form matches
                form_row = matching_forms[0]
                form_id = str(form_row["id"])
                processed_forms.add(form_id)
                rec = ReconciledRecord(
                    invoice_id=inv_id,
                    student_id=std_id,
                    class_id=class_id,
                    educator_id=edu_id,
                    invoice_row=inv_row,
                    faculty_form_row=form_row,
                    reference_row=ref_row,
                    booking_request_row=br_row,
                    class_slots=slots,
                    has_form=True,
                    has_invoice=True,
                    is_duplicate_form=False,
                    all_form_ids=[form_id],
                    already_scheduled_count=len(slots),
                )
            else:
                # Multiple forms submitted for the same invoice (e.g. 3308 and 3309 for 84908)
                # Sort by created_at_dt to find primary (earliest) and duplicate
                sorted_forms = sorted(
                    matching_forms,
                    key=lambda f: f["created_at_dt"] if pd.notna(f["created_at_dt"]) else pd.Timestamp.max
                )
                primary_form = sorted_forms[0]
                all_ids = [str(f["id"]) for f in sorted_forms]
                for f in sorted_forms:
                    processed_forms.add(str(f["id"]))

                rec = ReconciledRecord(
                    invoice_id=inv_id,
                    student_id=std_id,
                    class_id=class_id,
                    educator_id=edu_id,
                    invoice_row=inv_row,
                    faculty_form_row=primary_form,
                    reference_row=ref_row,
                    booking_request_row=br_row,
                    class_slots=slots,
                    has_form=True,
                    has_invoice=True,
                    is_duplicate_form=True,
                    all_form_ids=all_ids,
                    already_scheduled_count=len(slots),
                )

            reconciled_records.append(rec)

        # Step 3: Check for any orphan faculty forms that were NOT matched to an invoice
        for _, form_row in self.faculty_forms.iterrows():
            f_id = str(form_row["id"])
            if f_id not in processed_forms:
                inv_ref = str(form_row.get("invoice_id"))
                std_id = str(form_row.get("student_id"))
                ref_match = self.reference[self.reference["student_id"] == std_id]
                ref_row = ref_match.iloc[0] if not ref_match.empty else None

                rec = ReconciledRecord(
                    invoice_id=inv_ref,
                    student_id=std_id,
                    class_id=str(form_row.get("class_id")),
                    educator_id=str(form_row.get("educator_id")),
                    invoice_row=None,
                    faculty_form_row=form_row,
                    reference_row=ref_row,
                    booking_request_row=None,
                    class_slots=[],
                    has_form=True,
                    has_invoice=False,
                    orphan_form_invoice_ref=inv_ref,
                    all_form_ids=[f_id],
                )
                reconciled_records.append(rec)
                processed_forms.add(f_id)

        logger.info(f"Reconciliation correlated {len(reconciled_records)} operational renewal items.")
        return reconciled_records

