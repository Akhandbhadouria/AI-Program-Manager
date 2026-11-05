"""
Module: src/data_loader.py
Description: Robust, read-only data loader for Bambinos.live reconciliation datasets.
Preserves original CSV files and enforces immutable access.
"""

import os
import logging
from dataclasses import dataclass
from typing import Dict, Optional
import pandas as pd

logger = logging.getLogger("reconciliation.data_loader")

# Canonical file names in the Bambinos.live repository
DEFAULT_FILE_MAP = {
    "invoices": "1_invoices.csv",
    "faculty_form": "2_faculty_form_unapproved.csv",
    "booking_requests": "3_booking_requests.csv",
    "class_schedule_bookings": "4_class_schedule_bookings.csv",
    "reference": "reference_active_batches_and_students.csv",
}


@dataclass(frozen=True)
class DatasetBundle:
    """Immutable container holding all 5 raw datasets."""
    invoices: pd.DataFrame
    faculty_form: pd.DataFrame
    booking_requests: pd.DataFrame
    class_schedule_bookings: pd.DataFrame
    reference: pd.DataFrame

    def summary(self) -> Dict[str, int]:
        return {
            "invoices": len(self.invoices),
            "faculty_form": len(self.faculty_form),
            "booking_requests": len(self.booking_requests),
            "class_schedule_bookings": len(self.class_schedule_bookings),
            "reference": len(self.reference),
        }


def load_csv_file(file_path: str) -> pd.DataFrame:
    """
    Safely reads a CSV file into a pandas DataFrame without mutating the source.
    Reads all columns initially as string to prevent loss of precision or misinterpretation.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Required dataset not found at path: {file_path}")

    # Read all columns as object/string first to avoid unexpected type conversions
    df = pd.read_csv(file_path, dtype=str, keep_default_na=False)
    logger.debug(f"Loaded {os.path.basename(file_path)}: {df.shape[0]} rows, {df.shape[1]} columns")
    return df.copy(deep=True)


def load_all_datasets(data_dir: str = ".") -> DatasetBundle:
    """
    Loads all five Bambinos.live operational datasets from the specified directory.
    
    Args:
        data_dir: Directory path containing the CSV files.
        
    Returns:
        DatasetBundle containing copies of the 5 DataFrames.
    """
    logger.info(f"Loading reconciliation datasets from directory: '{os.path.abspath(data_dir)}'")
    loaded_dfs = {}

    for key, filename in DEFAULT_FILE_MAP.items():
        file_path = os.path.join(data_dir, filename)
        df = load_csv_file(file_path)
        loaded_dfs[key] = df

    bundle = DatasetBundle(
        invoices=loaded_dfs["invoices"],
        faculty_form=loaded_dfs["faculty_form"],
        booking_requests=loaded_dfs["booking_requests"],
        class_schedule_bookings=loaded_dfs["class_schedule_bookings"],
        reference=loaded_dfs["reference"],
    )

    logger.info(f"Successfully loaded all datasets: {bundle.summary()}")
    return bundle

