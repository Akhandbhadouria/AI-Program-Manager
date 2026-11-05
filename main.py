#!/usr/bin/env python3.10
"""
File: main.py
Description: Main orchestration entry point for the Bambinos.live Reconciliation Engine.
Executes deterministic validation, generates the three required classification CSVs,
and outputs execution metrics.
"""

import os
import sys
import logging
from typing import Tuple
import pandas as pd

from src.data_loader import load_all_datasets
from src.reconciliation import DataReconciler
from src.approval_engine import ApprovalEngine
from src.message_generator import MessageGeneratorService

# Set up clean, structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("reconciliation.main")


def run_pipeline(data_dir: str = ".", output_dir: str = ".") -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Orchestrates the complete deterministic renewal reconciliation workflow.
    
    Args:
        data_dir: Directory containing the 5 source CSV files.
        output_dir: Directory where the 3 output CSV files will be saved.
        
    Returns:
        Tuple of (df_auto_approved, df_flagged_exceptions, df_pending_human_review)
    """
    logger.info("=" * 70)
    logger.info("STARTING BAMBINOS.LIVE RECONCILIATION & AUTO-APPROVAL ENGINE")
    logger.info("=" * 70)

    # Step 1: Load Datasets
    try:
        raw_bundle = load_all_datasets(data_dir=data_dir)
    except Exception as e:
        logger.error(f"Failed to load input datasets: {e}")
        sys.exit(1)

    # Step 2: Reconcile Cross-Table Entities
    logger.info("Executing multi-table reconciliation and linkage...")
    reconciler = DataReconciler(raw_bundle)
    reconciled_records = reconciler.reconcile_all()

    # Step 3: Run Deterministic Approval Engine
    logger.info("Applying business validation rules & decision matrix...")
    engine = ApprovalEngine(reconciler.reference)
    df_approved, df_exceptions, df_review = engine.execute(reconciled_records)

    # Step 4: Write Output CSV Files (Ensuring Idempotent & Non-Mutating Execution)
    os.makedirs(output_dir, exist_ok=True)
    
    path_approved = os.path.join(output_dir, "auto_approved.csv")
    path_exceptions = os.path.join(output_dir, "flagged_exceptions.csv")
    path_review = os.path.join(output_dir, "pending_human_review.csv")

    df_approved.to_csv(path_approved, index=False)
    df_exceptions.to_csv(path_exceptions, index=False)
    df_review.to_csv(path_review, index=False)

    logger.info(f"Generated output file: {path_approved} ({len(df_approved)} records)")
    logger.info(f"Generated output file: {path_exceptions} ({len(df_exceptions)} records)")
    logger.info(f"Generated output file: {path_review} ({len(df_review)} records)")

    # Step 5: Generate Actionable Communication Drafts for Exceptions & Reviews
    logger.info("Generating actionable follow-up message drafts (WhatsApp & Slack)...")
    msg_service = MessageGeneratorService(data_dir=data_dir)
    df_messages = msg_service.generate_all_messages(
        exceptions_csv=path_exceptions,
        review_csv=path_review,
        output_csv=os.path.join(output_dir, "outputs", "followup_messages.csv")
        if output_dir == "."
        else os.path.join(output_dir, "followup_messages.csv"),
    )

    # Step 6: Display Summary Dashboard
    total_processed = len(df_approved) + len(df_exceptions) + len(df_review)
    print("\n" + "=" * 75)
    print("                 RECONCILIATION ENGINE EXECUTION SUMMARY")
    print("=" * 75)
    print(f"Total Renewal Records Processed:     {total_processed}")
    print(f"  ├── AUTO_APPROVED:                 {len(df_approved):>2} records ({len(df_approved)/total_processed*100:>5.1f}%)")
    print(f"  ├── FLAGGED_EXCEPTION:             {len(df_exceptions):>2} records ({len(df_exceptions)/total_processed*100:>5.1f}%)")
    print(f"  └── PENDING_HUMAN_REVIEW:          {len(df_review):>2} records ({len(df_review)/total_processed*100:>5.1f}%)")
    print(f"Actionable Follow-up Message Drafts: {len(df_messages):>2} drafts generated (Saved: outputs/followup_messages.csv)")
    print("=" * 75)

    if not df_approved.empty:
        print("\n--- [1] AUTO_APPROVED RECORDS ---")
        cols_app = ["invoice_id", "student_id", "student_name", "classbatch_name", "net_amount_paid", "action_taken"]
        print(df_approved[cols_app].to_string(index=False))

    if not df_exceptions.empty:
        print("\n--- [2] FLAGGED_EXCEPTIONS ---")
        cols_exc = ["invoice_id", "student_id", "failure_category", "reason_code", "recommended_action"]
        print(df_exceptions[cols_exc].to_string(index=False))

    if not df_review.empty:
        print("\n--- [3] PENDING_HUMAN_REVIEW ---")
        cols_rev = ["invoice_id", "student_id", "review_category", "reason_code", "suggested_resolution_options"]
        print(df_review[cols_rev].to_string(index=False))

    print("\n" + "=" * 75)
    logger.info("PIPELINE COMPLETED SUCCESSFULLY WITH ZERO ERRORS.")
    return df_approved, df_exceptions, df_review


if __name__ == "__main__":
    run_pipeline()

