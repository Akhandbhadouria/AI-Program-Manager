#!/usr/bin/env python3.10
import pandas as pd
import numpy as np

files = {
    "invoices":               "1_invoices.csv",
    "faculty_form":           "2_faculty_form_unapproved.csv",
    "booking_requests":       "3_booking_requests.csv",
    "class_schedule_bookings":"4_class_schedule_bookings.csv",
    "reference":              "reference_active_batches_and_students.csv",
}

dfs = {}
for name, path in files.items():
    dfs[name] = pd.read_csv(path, dtype=str)

# ── 1. Shape + column info ───────────────────────────────────────────────────
for name, df in dfs.items():
    print(f"\n{'='*70}")
    print(f"TABLE: {name}  |  {df.shape[0]} rows x {df.shape[1]} cols")
    print(f"  {'COL':<40} {'NULL_TEXT':>10} {'NA':>5} {'UNIQUE':>7}  SAMPLES")
    for col in df.columns:
        n_null_text = (df[col] == 'NULL').sum()
        n_na        = df[col].isna().sum()
        n_unique    = df[col].nunique(dropna=False)
        samples     = df[col][~df[col].isin(['NULL'])].dropna().head(2).tolist()
        print(f"  {col:<40} {n_null_text:>10} {n_na:>5} {n_unique:>7}  {samples}")

# ── 2. Duplicates ────────────────────────────────────────────────────────────
print("\n\n=== DUPLICATES ===")
for name, df in dfs.items():
    dups = df.duplicated().sum()
    print(f"  {name}: {dups} exact duplicate rows")

# ── 3. Payment-status value counts ──────────────────────────────────────────
print("\n\n=== INVOICE: payment_status counts ===")
print(dfs["invoices"]["payment_status"].value_counts().to_string())

print("\n=== INVOICE: is_renewal counts ===")
print(dfs["invoices"]["is_renewal"].value_counts().to_string())

print("\n=== INVOICE: payment_type counts ===")
print(dfs["invoices"]["payment_type"].value_counts().to_string())

print("\n=== INVOICE: payment_gateway counts ===")
print(dfs["invoices"]["payment_gateway"].value_counts().to_string())

print("\n=== INVOICE: currency counts ===")
print(dfs["invoices"]["currency"].value_counts().to_string())

# ── 4. Faculty form approval_status ─────────────────────────────────────────
print("\n\n=== FACULTY FORM: approval_status counts ===")
print(dfs["faculty_form"]["approval_status"].value_counts().to_string())

print("\n=== FACULTY FORM: continue_same_batch counts ===")
print(dfs["faculty_form"]["continue_same_batch"].value_counts().to_string())

# ── 5. Booking request statuses ─────────────────────────────────────────────
print("\n\n=== BOOKING REQUESTS: request_status counts ===")
print(dfs["booking_requests"]["request_status"].value_counts().to_string())

print("\n=== BOOKING REQUESTS: batch_allocated counts ===")
print(dfs["booking_requests"]["batch_allocated"].value_counts().to_string())

# ── 6. Cross-table join coverage ─────────────────────────────────────────────
print("\n\n=== JOIN COVERAGE ===")
inv_ids  = set(dfs["invoices"]["id"])
ff_inv   = set(dfs["faculty_form"]["invoice_id"])
br_inv   = set(dfs["booking_requests"]["invoice_id"])
csb_inv  = set(dfs["class_schedule_bookings"]["invoice_id"])
ref_std  = set(dfs["reference"]["student_id"])
inv_std  = set(dfs["invoices"]["student_id"])

print(f"  Invoice IDs in invoices:                   {sorted(inv_ids)}")
print(f"  Invoice IDs in faculty_form:               {sorted(ff_inv)}")
print(f"  Invoice IDs in booking_requests:           {sorted(br_inv)}")
print(f"  Invoice IDs in class_schedule_bookings:    {sorted(csb_inv)}")
print(f"\n  Faculty form invoice_ids NOT in invoices:  {sorted(ff_inv - inv_ids)}")
print(f"  Booking req invoice_ids NOT in invoices:   {sorted(br_inv - inv_ids)}")
print(f"  Invoices with NO faculty form:             {sorted(inv_ids - ff_inv)}")
print(f"  Invoices with NO booking request:          {sorted(inv_ids - br_inv)}")
print(f"  Faculty forms with NO booking request:     {sorted(set(dfs['faculty_form']['id']) - set(dfs['booking_requests']['faculty_form_id']))}")

print(f"\n  Student IDs in reference:                  {sorted(ref_std)}")
print(f"  Student IDs in invoices:                   {sorted(inv_std)}")
print(f"  Invoice students NOT in reference:         {sorted(inv_std - ref_std)}")
print(f"  Reference students NOT in invoices:        {sorted(ref_std - inv_std)}")

# ── 7. Amount/fee mismatches ──────────────────────────────────────────────────
print("\n\n=== AMOUNT MISMATCHES (invoice net_amount vs faculty form amount_paid) ===")
inv = dfs["invoices"][["id","net_amount","payment_status"]].copy()
inv.columns = ["invoice_id","inv_net","inv_status"]
ff  = dfs["faculty_form"][["invoice_id","amount_paid","approval_status"]].copy()
merged = ff.merge(inv, on="invoice_id", how="left")
merged["inv_net"]     = pd.to_numeric(merged["inv_net"],    errors="coerce")
merged["amount_paid"] = pd.to_numeric(merged["amount_paid"],errors="coerce")
merged["mismatch"]    = merged["inv_net"] != merged["amount_paid"]
print(merged[["invoice_id","inv_net","amount_paid","mismatch","inv_status","approval_status"]].to_string(index=False))

# ── 8. Mobile mismatches ─────────────────────────────────────────────────────
print("\n\n=== MOBILE MISMATCHES (invoice mobile vs reference registered_mobile) ===")
inv_mob = dfs["invoices"][["id","student_id","mobile"]].copy()
inv_mob.columns = ["invoice_id","student_id","inv_mobile"]
ref_mob = dfs["reference"][["student_id","registered_mobile_masked"]].copy()
mob_merged = inv_mob.merge(ref_mob, on="student_id", how="left")
mob_merged["mobile_match"] = mob_merged["inv_mobile"] == mob_merged["registered_mobile_masked"]
print(mob_merged[["invoice_id","student_id","inv_mobile","registered_mobile_masked","mobile_match"]].to_string(index=False))

# ── 9. Standard fee vs charged amount ────────────────────────────────────────
print("\n\n=== FEE MISMATCHES (invoice net_amount vs reference standard_fee) ===")
inv_fee = dfs["invoices"][["id","student_id","net_amount","discount_amount","amount"]].copy()
inv_fee.columns = ["invoice_id","student_id","net_amount","discount_amount","gross_amount"]
ref_fee = dfs["reference"][["student_id","standard_fee_24_sessions_inr"]].copy()
fee_merged = inv_fee.merge(ref_fee, on="student_id", how="left")
for col in ["net_amount","discount_amount","gross_amount","standard_fee_24_sessions_inr"]:
    fee_merged[col] = pd.to_numeric(fee_merged[col], errors="coerce")
fee_merged["fee_match"] = fee_merged["gross_amount"] == fee_merged["standard_fee_24_sessions_inr"]
fee_merged["discount_applied"] = fee_merged["discount_amount"] > 0
print(fee_merged[["invoice_id","student_id","gross_amount","standard_fee_24_sessions_inr","net_amount","discount_amount","fee_match","discount_applied"]].to_string(index=False))

# ── 10. Batch capacity ────────────────────────────────────────────────────────
print("\n\n=== BATCH CAPACITY ===")
ref = dfs["reference"].copy()
ref["active_students_count"] = pd.to_numeric(ref["active_students_count"], errors="coerce")
ref["max_batch_size"]         = pd.to_numeric(ref["max_batch_size"],         errors="coerce")
ref["is_full"] = ref["active_students_count"] >= ref["max_batch_size"]
print(ref[["current_classbatch_id","classbatch_name","class_id","active_students_count","max_batch_size","is_full"]].to_string(index=False))

# ── 11. Failed / Null gateway_payment_id ─────────────────────────────────────
print("\n\n=== INVOICES: gateway_payment_id = NULL ===")
mask = (dfs["invoices"]["gateway_payment_id"] == "NULL") | dfs["invoices"]["gateway_payment_id"].isna()
print(dfs["invoices"][mask][["id","invoice_number","payment_status","paid_at","gateway_payment_id"]].to_string(index=False))

# ── 12. deleted_at across tables ─────────────────────────────────────────────
print("\n\n=== SOFT-DELETED RECORDS (deleted_at != NULL) ===")
for name, df in dfs.items():
    if "deleted_at" in df.columns:
        soft = df[df["deleted_at"] != "NULL"]["deleted_at"].count() if "deleted_at" in df.columns else 0
        # Also count actual nulls vs NULL strings
        not_null = df["deleted_at"][~df["deleted_at"].isin(["NULL"]) & df["deleted_at"].notna()]
        print(f"  {name}: {len(not_null)} soft-deleted rows")

# ── 13. Educator/class consistency across tables ──────────────────────────────
print("\n\n=== EDUCATOR + CLASS CONSISTENCY (invoice vs faculty_form) ===")
inv_ec = dfs["invoices"][["id","class_id","educator_id"]].copy()
inv_ec.columns = ["invoice_id","inv_class","inv_educator"]
ff_ec  = dfs["faculty_form"][["invoice_id","class_id","educator_id"]].copy()
ff_ec.columns  = ["invoice_id","ff_class","ff_educator"]
ec_merged = ff_ec.merge(inv_ec, on="invoice_id", how="left")
ec_merged["class_match"]    = ec_merged["ff_class"]    == ec_merged["inv_class"]
ec_merged["educator_match"] = ec_merged["ff_educator"] == ec_merged["inv_educator"]
print(ec_merged[["invoice_id","ff_class","inv_class","class_match","ff_educator","inv_educator","educator_match"]].to_string(index=False))

# ── 14. Date format consistency ───────────────────────────────────────────────
print("\n\n=== DATE COLUMNS SAMPLE ===")
date_cols = {
    "invoices": ["paid_at","created_at","updated_at"],
    "faculty_form": ["approved_at","created_at"],
    "booking_requests": ["allocated_at","created_at"],
    "class_schedule_bookings": ["class_date","created_at"],
}
for tbl, cols in date_cols.items():
    df = dfs[tbl]
    for col in cols:
        if col in df.columns:
            vals = df[col][~df[col].isin(["NULL"]) & df[col].notna()].head(3).tolist()
            print(f"  {tbl}.{col}: {vals}")

print("\n\nDONE")

