#!/usr/bin/env python3.10
"""
Relationship analysis script for Bambinos.live datasets.
Investigates ALL possible matching key combinations — not just invoice_id.
"""
import pandas as pd
import numpy as np

# ── Load all tables ──────────────────────────────────────────────────────────
dfs = {
    "invoices": pd.read_csv("1_invoices.csv", dtype=str),
    "faculty_form": pd.read_csv("2_faculty_form_unapproved.csv", dtype=str),
    "booking_requests": pd.read_csv("3_booking_requests.csv", dtype=str),
    "class_schedule_bookings": pd.read_csv("4_class_schedule_bookings.csv", dtype=str),
    "reference": pd.read_csv("reference_active_batches_and_students.csv", dtype=str),
}

inv = dfs["invoices"]
ff  = dfs["faculty_form"]
br  = dfs["booking_requests"]
csb = dfs["class_schedule_bookings"]
ref = dfs["reference"]

SEP = "=" * 70

# ── 1. INVOICE ↔ FACULTY_FORM ─────────────────────────────────────────────
print(f"\n{SEP}")
print("SECTION 1: invoices ↔ faculty_form")
print(SEP)

# a. invoice_id only
inv_ids = set(inv["id"])
ff_inv_ids = set(ff["invoice_id"])
print(f"\n[1a] invoice_id match:")
print(f"  Invoices:                   {sorted(inv_ids)}")
print(f"  Faculty form invoice_ids:   {sorted(ff_inv_ids)}")
print(f"  Matched (in both):          {sorted(inv_ids & ff_inv_ids)}")
print(f"  Invoices with NO form:      {sorted(inv_ids - ff_inv_ids)}")
print(f"  Forms with NO invoice:      {sorted(ff_inv_ids - inv_ids)}")

# b. student_id consistency in matched rows
matched_inv = inv[inv["id"].isin(ff_inv_ids)][["id","student_id","class_id","educator_id","net_amount","payment_status"]].copy()
matched_ff  = ff[ff["invoice_id"].isin(inv_ids)][["invoice_id","student_id","class_id","educator_id","amount_paid","approval_status"]].copy()
merged_1 = matched_ff.merge(
    matched_inv.rename(columns={"id":"invoice_id","student_id":"inv_student","class_id":"inv_class","educator_id":"inv_educator","net_amount":"inv_net"}),
    on="invoice_id", how="left"
)
merged_1["student_match"]  = merged_1["student_id"]  == merged_1["inv_student"]
merged_1["class_match"]    = merged_1["class_id"]    == merged_1["inv_class"]
merged_1["educator_match"] = merged_1["educator_id"] == merged_1["inv_educator"]
merged_1["amount_paid"]    = pd.to_numeric(merged_1["amount_paid"], errors="coerce")
merged_1["inv_net"]        = pd.to_numeric(merged_1["inv_net"],     errors="coerce")
merged_1["amount_match"]   = merged_1["amount_paid"] == merged_1["inv_net"]

print(f"\n[1b] Multi-key consistency (invoice_id + student_id + class_id + educator_id + amount):")
print(merged_1[["invoice_id","student_match","class_match","educator_match","amount_match","payment_status","approval_status"]].to_string(index=False))

# c. How many forms per invoice?
form_counts = ff.groupby("invoice_id")["id"].count().reset_index()
form_counts.columns = ["invoice_id","form_count"]
print(f"\n[1c] Forms per invoice_id:")
print(form_counts[form_counts["form_count"] > 1].to_string(index=False))
print(f"  (all invoices with exactly 1 form are omitted above)")

# d. Relationship type
print(f"\n[1d] Relationship type: invoices → faculty_form")
print(f"  One invoice can have multiple forms (invoice 84908 has 2)")
print(f"  → One-to-Many (1:N) in theory, designed as 1:1")

# ── 2. FACULTY_FORM ↔ BOOKING_REQUESTS ───────────────────────────────────
print(f"\n{SEP}")
print("SECTION 2: faculty_form ↔ booking_requests")
print(SEP)

ff_ids = set(ff["id"])
br_ff_ids = set(br["faculty_form_id"])

print(f"\n[2a] faculty_form_id match:")
print(f"  Faculty form ids:                        {sorted(ff_ids)}")
print(f"  Booking req faculty_form_ids:            {sorted(br_ff_ids)}")
print(f"  Matched:                                 {sorted(ff_ids & br_ff_ids)}")
print(f"  Faculty forms with NO booking request:   {sorted(ff_ids - br_ff_ids)}")
print(f"  Booking reqs with invalid form ref:      {sorted(br_ff_ids - ff_ids)}")

# Check multi-key: faculty_form_id + invoice_id + student_id
merged_2 = br.merge(
    ff[["id","invoice_id","student_id","class_id","educator_id","approval_status"]].rename(
        columns={"id":"faculty_form_id","invoice_id":"ff_invoice","student_id":"ff_student","class_id":"ff_class","educator_id":"ff_educator"}),
    on="faculty_form_id", how="left"
)
merged_2["invoice_match"]  = merged_2["invoice_id"]  == merged_2["ff_invoice"]
merged_2["student_match"]  = merged_2["student_id"]  == merged_2["ff_student"]
merged_2["class_match"]    = merged_2["class_id"]    == merged_2["ff_class"]
merged_2["educator_match"] = merged_2["educator_id"] == merged_2["ff_educator"]

print(f"\n[2b] Multi-key consistency (booking_req → faculty_form):")
print(merged_2[["id","faculty_form_id","invoice_match","student_match","class_match","educator_match","approval_status","request_status"]].to_string(index=False))

print(f"\n[2c] Relationship type: faculty_form → booking_requests")
print(f"  One form has at most 1 booking request in this dataset")
print(f"  → One-to-One (1:1) in practice, though 1:N is possible in design")

# ── 3. BOOKING_REQUESTS ↔ CLASS_SCHEDULE_BOOKINGS ────────────────────────
print(f"\n{SEP}")
print("SECTION 3: booking_requests ↔ class_schedule_bookings")
print(SEP)

br_ids  = set(br["id"])
csb_br_ids = set(csb["bookingrequest_id"])

print(f"\n[3a] bookingrequest_id match:")
print(f"  Booking req ids:                     {sorted(br_ids)}")
print(f"  Class booking bookingrequest_ids:    {sorted(csb_br_ids)}")
print(f"  Matched:                             {sorted(br_ids & csb_br_ids)}")
print(f"  Booking reqs with NO class slots:    {sorted(br_ids - csb_br_ids)}")
print(f"  Class slots with invalid req ref:    {sorted(csb_br_ids - br_ids)}")

# Check cardinality
slot_counts = csb.groupby("bookingrequest_id")["id"].count().reset_index()
slot_counts.columns = ["bookingrequest_id","slot_count"]
print(f"\n[3b] Class slots per booking request:")
print(slot_counts.to_string(index=False))
print(f"  → One-to-Many (1:N): 1 booking request → multiple class slots")

# Multi-key check
merged_3 = csb.merge(
    br[["id","invoice_id","student_id","class_id","educator_id","classbatch_id"]].rename(
        columns={"id":"bookingrequest_id","invoice_id":"br_invoice","student_id":"br_student","class_id":"br_class","educator_id":"br_educator","classbatch_id":"br_batch"}),
    on="bookingrequest_id", how="left"
)
merged_3["invoice_match"]  = merged_3["invoice_id"]  == merged_3["br_invoice"]
merged_3["student_match"]  = merged_3["student_id"]  == merged_3["br_student"]
merged_3["class_match"]    = merged_3["class_id"]    == merged_3["br_class"]
merged_3["educator_match"] = merged_3["educator_id"] == merged_3["br_educator"]
merged_3["batch_match"]    = merged_3["classbatch_id"] == merged_3["br_batch"]
print(f"\n[3c] Multi-key consistency (class_schedule → booking_request):")
print(merged_3[["id","bookingrequest_id","invoice_match","student_match","class_match","educator_match","batch_match"]].to_string(index=False))

# ── 4. REFERENCE → ALL TABLES ─────────────────────────────────────────────
print(f"\n{SEP}")
print("SECTION 4: reference ↔ all tables")
print(SEP)

ref_students = set(ref["student_id"])
for name, df in dfs.items():
    if name == "reference":
        continue
    if "student_id" in df.columns:
        tbl_students = set(df["student_id"])
        matched = ref_students & tbl_students
        unmatched = tbl_students - ref_students
        print(f"\n[4] reference ↔ {name} (via student_id):")
        print(f"  Reference students: {sorted(ref_students)}")
        print(f"  {name} students:    {sorted(tbl_students)}")
        print(f"  Matched:            {sorted(matched)}")
        print(f"  NOT in reference:   {sorted(unmatched)}")

# Reference: validate class_id and educator_id consistency
print(f"\n[4b] Cross-validate invoice class_id + educator_id against reference:")
inv_ref = inv[["id","student_id","class_id","educator_id","net_amount"]].merge(
    ref[["student_id","class_id","educator_id","standard_fee_24_sessions_inr","current_classbatch_id"]].rename(
        columns={"class_id":"ref_class","educator_id":"ref_educator","standard_fee_24_sessions_inr":"ref_fee","current_classbatch_id":"ref_batch"}),
    on="student_id", how="left"
)
inv_ref["class_match"]    = inv_ref["class_id"]    == inv_ref["ref_class"]
inv_ref["educator_match"] = inv_ref["educator_id"] == inv_ref["ref_educator"]
inv_ref["net_amount"]     = pd.to_numeric(inv_ref["net_amount"],   errors="coerce")
inv_ref["ref_fee"]        = pd.to_numeric(inv_ref["ref_fee"],       errors="coerce")
inv_ref["inv_amount"]     = pd.to_numeric(inv[["id","amount"]].rename(columns={"id":"id"}).set_index("id").reindex(inv_ref["id"].values)["amount"].values, errors="coerce")
inv_ref["fee_vs_gross"]   = inv_ref["inv_amount"]  == inv_ref["ref_fee"]  # gross vs standard
print(inv_ref[["id","student_id","class_match","educator_match","fee_vs_gross","ref_batch"]].to_string(index=False))

# Reference: batch capacity
print(f"\n[4c] Batch capacity from reference:")
ref_batches = ref.drop_duplicates("current_classbatch_id")[["current_classbatch_id","classbatch_name","active_students_count","max_batch_size"]].copy()
ref_batches["active_students_count"] = pd.to_numeric(ref_batches["active_students_count"])
ref_batches["max_batch_size"]        = pd.to_numeric(ref_batches["max_batch_size"])
ref_batches["slots_available"]       = ref_batches["max_batch_size"] - ref_batches["active_students_count"]
ref_batches["is_full"]               = ref_batches["slots_available"] == 0
print(ref_batches[["current_classbatch_id","classbatch_name","active_students_count","max_batch_size","slots_available","is_full"]].to_string(index=False))

# ── 5. MATCHING KEY RELIABILITY ───────────────────────────────────────────
print(f"\n{SEP}")
print("SECTION 5: Matching key reliability analysis")
print(SEP)

# Invoice → Faculty Form key combinations
print("\n[5a] Key combinations: invoice → faculty_form")
test_keys = [
    ("invoice_id only",                    ["invoice_id"]),
    ("invoice_id + student_id",            ["invoice_id","student_id"]),
    ("invoice_id + student_id + class_id", ["invoice_id","student_id","class_id"]),
    ("invoice_id + student_id + educator_id", ["invoice_id","student_id","educator_id"]),
]
inv_keys = inv.rename(columns={"id":"invoice_id"})
for label, keys in test_keys:
    shared_cols_inv = [k for k in keys if k in inv_keys.columns]
    shared_cols_ff  = [k for k in keys if k in ff.columns]
    if len(shared_cols_inv) != len(keys) or len(shared_cols_ff) != len(keys):
        print(f"  {label}: SKIPPED (column missing)")
        continue
    merged = ff[shared_cols_ff + ["id"]].merge(inv_keys[shared_cols_inv + ["invoice_number"]], on=keys, how="outer", indicator=True)
    matched = (merged["_merge"] == "both").sum()
    left_only = (merged["_merge"] == "left_only").sum()
    right_only = (merged["_merge"] == "right_only").sum()
    print(f"  {label}:")
    print(f"    Matched={matched}, Unmatched_form={left_only}, Unmatched_invoice={right_only}")

# booking_request → faculty_form
print("\n[5b] Key combinations: booking_request → faculty_form")
test_keys_b = [
    ("faculty_form_id only", ["faculty_form_id"]),
    ("faculty_form_id + invoice_id", ["faculty_form_id","invoice_id"]),
    ("faculty_form_id + student_id", ["faculty_form_id","student_id"]),
]
ff_renamed = ff.rename(columns={"id":"faculty_form_id"})
for label, keys in test_keys_b:
    shared_br = [k for k in keys if k in br.columns]
    shared_ff = [k for k in keys if k in ff_renamed.columns]
    if len(shared_br) != len(keys) or len(shared_ff) != len(keys):
        print(f"  {label}: SKIPPED")
        continue
    merged = br[shared_br + ["id"]].merge(ff_renamed[shared_ff + ["invoice_id" if "invoice_id" not in keys else "approval_status"]], on=keys, how="outer", indicator=True)
    matched = (merged["_merge"] == "both").sum()
    left_only = (merged["_merge"] == "left_only").sum()
    right_only = (merged["_merge"] == "right_only").sum()
    print(f"  {label}: Matched={matched}, Unmatched_br={left_only}, Unmatched_ff={right_only}")

# ── 6. DUPLICATE ANALYSIS ─────────────────────────────────────────────────
print(f"\n{SEP}")
print("SECTION 6: Duplicate record analysis")
print(SEP)

# Faculty form duplicates by student_id
print("\n[6a] Faculty forms with same student_id (potential duplicate submissions):")
dup_students = ff.groupby("student_id").filter(lambda x: len(x) > 1)
if len(dup_students):
    print(dup_students[["id","invoice_id","student_id","class_id","approval_status","created_at"]].to_string(index=False))
else:
    print("  None found.")

# Faculty form duplicates by invoice_id
print("\n[6b] Faculty forms with same invoice_id (definite duplicate submissions):")
dup_invoices = ff.groupby("invoice_id").filter(lambda x: len(x) > 1)
if len(dup_invoices):
    print(dup_invoices[["id","invoice_id","student_id","educator_id","approval_status","created_at"]].to_string(index=False))
else:
    print("  None found.")

# Class schedule bookings with same (student_id, class_date, start_time)
print("\n[6c] Class schedule bookings with same (student_id, class_date, start_time):")
dup_slots = csb.groupby(["student_id","class_date","start_time"]).filter(lambda x: len(x) > 1)
if len(dup_slots):
    print(dup_slots.to_string(index=False))
else:
    print("  None found.")

# ── 7. UNMATCHED RECORDS SUMMARY ─────────────────────────────────────────
print(f"\n{SEP}")
print("SECTION 7: Complete unmatched record summary")
print(SEP)

print("\n[7a] Invoices with no faculty form:")
no_form = inv[~inv["id"].isin(ff["invoice_id"])]
print(no_form[["id","student_id","class_id","payment_status"]].to_string(index=False))

print("\n[7b] Faculty forms with no matching invoice:")
no_inv = ff[~ff["invoice_id"].isin(inv["id"])]
print(no_inv[["id","invoice_id","student_id","approval_status"]].to_string(index=False))

print("\n[7c] Faculty forms (approved or pending) with no booking request:")
no_br = ff[~ff["id"].isin(br["faculty_form_id"])]
print(no_br[["id","invoice_id","student_id","approval_status","created_at"]].to_string(index=False))

print("\n[7d] Booking requests with no class schedule bookings:")
no_csb = br[~br["id"].isin(csb["bookingrequest_id"])]
print(no_csb[["id","faculty_form_id","invoice_id","student_id","request_status"]].to_string(index=False))

print("\n[7e] Reference students NOT in any operational table (invoices):")
ref_not_in_inv = ref[~ref["student_id"].isin(inv["student_id"])]
if len(ref_not_in_inv):
    print(ref_not_in_inv[["student_id","classbatch_name"]].to_string(index=False))
else:
    print("  All reference students have an invoice record.")

# ── 8. RELATIONSHIP SUMMARY ───────────────────────────────────────────────
print(f"\n{SEP}")
print("SECTION 8: Relationship type summary")
print(SEP)

rels = [
    ("invoices (id)", "faculty_form (invoice_id)", "1:N (designed 1:1; 84908 has 2 forms)", "invoice_id + student_id + class_id + educator_id"),
    ("faculty_form (id)", "booking_requests (faculty_form_id)", "1:1 in practice (only 1 req per form)", "faculty_form_id + invoice_id + student_id"),
    ("booking_requests (id)", "class_schedule_bookings (bookingrequest_id)", "1:N (1 req → many class dates)", "bookingrequest_id + invoice_id + student_id"),
    ("reference (student_id)", "invoices (student_id)", "1:1 (each student has 1 invoice in this batch)", "student_id"),
    ("reference (student_id)", "faculty_form (student_id)", "1:1 mostly (84908 is 2:1)", "student_id"),
    ("reference (current_classbatch_id)", "booking_requests (classbatch_id)", "1:N (batch → multiple students)", "classbatch_id"),
    ("reference (student_id)", "booking_requests (student_id)", "1:1 in this dataset", "student_id + invoice_id"),
]
print(f"{'LEFT':<40} {'RIGHT':<45} {'CARDINALITY':<40} {'COMPOSITE KEY'}")
print("-" * 170)
for r in rels:
    print(f"  {r[0]:<40} {r[1]:<45} {r[2]:<40} {r[3]}")

print("\n\nDONE")

