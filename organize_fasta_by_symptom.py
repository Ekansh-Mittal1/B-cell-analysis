#!/usr/bin/env python3
"""
Organize FASTA and annotation files from Long COVID study by symptom and timepoint.

For each symptom group, creates 3 folders (T1/T2/T3) containing:
  - <PatientID>.fasta              (all_contig.fasta, run-prefixed if multi-run)
  - <PatientID>_filtered.fasta     (filtered_contig.fasta, prefixed with PatientID_Timepoint_)
  - <PatientID>_filtered_annotations.csv  (filtered_contig_annotations.csv, prefixed)

Prefixing scheme for filtered files:
  - FASTA headers:  >INCOV002_BL_BARCODE-1_contig_1
  - CSV columns barcode, contig_id, raw_clonotype_id, raw_consensus_id: all prefixed with INCOV002_BL_
  - For multi-run patients, run index is added: INCOV002_BL_run1_BARCODE-1_contig_1
"""

import os
import re
import csv
import shutil
import pandas as pd
from pathlib import Path
from collections import defaultdict

# ──────────────────────── Configuration ────────────────────────
FASTA_ROOT = Path("/Users/teichmann/Library/CloudStorage/GoogleDrive-jo.f.teichmann@gmail.com"
                   "/Shared drives/Long_COVID_(PASC)/2_Raw_Data/10x_Genomics")
SYMPTOM_EXCEL = Path("/Users/teichmann/Downloads/FullsymptomWithControl-082722 (1).xlsx")
OUTPUT_DIR = Path("/Users/teichmann/Desktop/LongCovid_Symptom_FASTA_neu")

TIMEPOINT_MAP = {"BL": "T1", "AC": "T2", "CV": "T3"}

SKIP_COLUMNS = {
    "SampleID", "LongCovid", "long COVID", "Gender1", "Gender", "DOB", "age",
    "No. Of Symptoms", "No. of Pre-Infections", "No. of Antibodies", ">1 Antibody",
    "Respiratory", "Neurological", "Gastrointesti0l", "Ear_nose_taste", "Musculoskeletal",
    "R0emia_T1", "CMV_viremia_T1_T2", "EBV_viremia_T1_T2",
    "IFN_a2_IgG_T3", "RibosomalPhosphoprotein_P1_IgG_T3",
    "Ro_SS_A_IgG_T3", "La_SS_B_IgG_T3", "Jo_1_IgG_T3", "U1_snRNP_IgG_T3",
}

DISPLAY_NAMES = {
    "anxiety": "Anxiety", "depression": "Depression",
    "difficulty_sleeping": "DifficultySleeping", "Generalized_symptoms": "GeneralizedSymptoms",
    "fatigue": "Fatigue", "fever_or_chills": "FeverOrChills", "cough": "Cough",
    "shortness_of_breath": "ShortnessOfBreath", "sputum": "Sputum",
    "Cardiovascular": "Cardiovascular", "heart_palpitations": "HeartPalpitations",
    "headache": "Headache", "neuro": "Neuro", "memory_problems": "MemoryProblems",
    "difficulty_concentrating": "DifficultyConcentrating", "dizziness": "Dizziness",
    "blurry_vision": "BlurryVision", "abdomi0l_pain": "AbdominalPain",
    "0usea": "Nausea", "diarrhea": "Diarrhea",
    "loss_of_smell": "LossOfSmell", "loss_of_taste": "LossOfTaste",
    "loss_of_sense": "LossOfSense", "hair_loss": "HairLoss",
    "i0bility_to_exercise": "InabilityToExercise", "joint_pain": "JointPain",
    "muscle_body_aches": "MuscleBodyAches", "pain_feet_hands": "PainFeetHands",
    "persistent_chest_pain": "PersistentChestPain", "respiratory_viral": "RespiratoryViral",
    "gastrointesti0l": "Gastrointestinal",
}

PREFIX_COLS = {"barcode", "contig_id", "raw_clonotype_id", "raw_consensus_id"}


# ──────────────────────── Helper: write files for one patient ────────────────────────
def write_patient_files(patient_id, tp_code, folder_path,
                        all_contig_sources, filtered_contig_sources, filtered_csv_sources):
    """Write all_contig.fasta, filtered_contig.fasta, and filtered_annotations.csv for one patient."""
    id_tp_prefix = f"{patient_id}_{tp_code}_"
    multi_run = len(all_contig_sources) > 1

    # ── all_contig.fasta (run-prefixed only) ──
    out_all = folder_path / f"{patient_id}.fasta"
    with open(out_all, "w") as out_f:
        for run_idx, fasta_src in enumerate(all_contig_sources, start=1):
            run_prefix = f"run{run_idx}_" if multi_run else ""
            with open(fasta_src, "r") as in_f:
                for line in in_f:
                    if line.startswith(">") and run_prefix:
                        out_f.write(f">{run_prefix}{line[1:]}")
                    else:
                        out_f.write(line)
                if not line.endswith("\n"):
                    out_f.write("\n")

    # ── filtered_contig.fasta (patient_timepoint + run prefix) ──
    out_filtered = folder_path / f"{patient_id}_filtered.fasta"
    with open(out_filtered, "w") as out_f:
        for run_idx, fasta_src in enumerate(filtered_contig_sources, start=1):
            run_part = f"run{run_idx}_" if multi_run else ""
            prefix = f"{id_tp_prefix}{run_part}"
            with open(fasta_src, "r") as in_f:
                for line in in_f:
                    if line.startswith(">"):
                        out_f.write(f">{prefix}{line[1:]}")
                    else:
                        out_f.write(line)
                if not line.endswith("\n"):
                    out_f.write("\n")

    # ── filtered_contig_annotations.csv (prefix barcode/contig_id/clonotype/consensus columns) ──
    out_csv = folder_path / f"{patient_id}_filtered_annotations.csv"
    with open(out_csv, "w", newline="") as out_f:
        writer = None
        for run_idx, csv_src in enumerate(filtered_csv_sources, start=1):
            run_part = f"run{run_idx}_" if multi_run else ""
            prefix = f"{id_tp_prefix}{run_part}"
            with open(csv_src, "r", newline="") as in_f:
                reader = csv.DictReader(in_f)
                if writer is None:
                    writer = csv.DictWriter(out_f, fieldnames=reader.fieldnames)
                    writer.writeheader()
                for row in reader:
                    for col in PREFIX_COLS:
                        if col in row and row[col] and row[col] != "None":
                            row[col] = f"{prefix}{row[col]}"
                    writer.writerow(row)


# ──────────────────────── Step 1: Load symptom data ────────────────────────
print("Loading symptom data...")
symptom_df = pd.read_excel(SYMPTOM_EXCEL)

symptom_columns = []
for col in symptom_df.columns:
    if col in SKIP_COLUMNS:
        continue
    vals = symptom_df[col].dropna().unique()
    if set(vals).issubset({0, 1, 0.0, 1.0}) and (symptom_df[col] == 1).sum() > 0:
        symptom_columns.append(col)

print(f"Found {len(symptom_columns)} symptom columns with positive patients:")
symptom_patients = {}
for col in symptom_columns:
    patients = sorted(symptom_df[symptom_df[col] == 1]["SampleID"].tolist())
    display = DISPLAY_NAMES.get(col, col)
    symptom_patients[col] = {"patients": set(patients), "display": display}
    print(f"  {display:35s} ({col:35s}): {len(patients)} patients")

# ──────────────────────── Step 2: Index all source files ────────────────────────
print(f"\nIndexing source files from {FASTA_ROOT}...")

# Index by run subfolder so all file types for the same run stay together:
#   run_idx[patient][timepoint][run_subfolder][file_type] = path
# Path structure: .../<10x_Genomics_N>/<INCOV-TP>/<run_subfolder>/outs/<file>
run_idx = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))

# Keep the old flat indices for backward-compat with summary code
all_contig_idx = defaultdict(lambda: defaultdict(list))

for file_path in FASTA_ROOT.rglob("*"):
    if not file_path.is_file():
        continue
    fname = file_path.name
    if fname not in ("all_contig.fasta", "filtered_contig.fasta", "filtered_contig_annotations.csv"):
        continue
    m = re.search(r"/(INCOV\d+)-(BL|AC|CV)/", str(file_path))
    if not m:
        continue
    pid, tp = m.group(1), m.group(2)

    # Extract run subfolder: the directory between <INCOV-TP>/ and /outs/
    parts = file_path.parts
    try:
        tp_dir_idx = next(i for i, p in enumerate(parts) if re.match(rf"{re.escape(pid)}-{tp}$", p))
        run_subfolder = parts[tp_dir_idx + 1]  # e.g. "F1_donor1", "F2_donor4"
    except (StopIteration, IndexError):
        run_subfolder = "default"

    if fname == "all_contig.fasta":
        run_idx[pid][tp][run_subfolder]["all_contig"] = file_path
        all_contig_idx[pid][tp].append(file_path)
    elif fname == "filtered_contig.fasta":
        run_idx[pid][tp][run_subfolder]["filtered_contig"] = file_path
    elif fname == "filtered_contig_annotations.csv":
        run_idx[pid][tp][run_subfolder]["filtered_csv"] = file_path

n_pt = sum(len(tps) for tps in all_contig_idx.values())
n_runs = sum(len(runs) for pt in run_idx.values() for runs in pt.values())
print(f"  Patient-timepoints: {n_pt}, total runs: {n_runs}")

# ──────────────────────── Step 3: Build all groups to process ────────────────────────

# Add GI extended cohort (nausea or diarrhea)
gi_extended = (
    (symptom_df["gastrointesti0l"] == 1) |
    (symptom_df["0usea"] == 1) |
    (symptom_df["diarrhea"] == 1)
)
gi_extended_patients = set(symptom_df[gi_extended]["SampleID"].tolist())
symptom_patients["_GI_Extended"] = {"patients": gi_extended_patients, "display": "GI_NauseaOrDiarrhea"}

# Add GI any-symptom cohort (nausea or diarrhea or abdominal pain)
gi_any = (
    (symptom_df["0usea"] == 1) |
    (symptom_df["diarrhea"] == 1) |
    (symptom_df["abdomi0l_pain"] == 1)
)
gi_any_patients = set(symptom_df[gi_any]["SampleID"].tolist())
symptom_patients["_GI_Any"] = {"patients": gi_any_patients, "display": "GI_Any"}

# Add Non-Long COVID controls
non_lc_mask = (
    (symptom_df["LongCovid"] == 0) |
    (symptom_df["long COVID"].astype(str).str.lower().str.contains("delete", na=False)) |
    (symptom_df["long COVID"].astype(str).str.lower().str.contains("non-long", na=False))
)
non_lc_patients = set(symptom_df[non_lc_mask]["SampleID"].tolist())
symptom_patients["_NonLongCovid"] = {"patients": non_lc_patients, "display": "NonLongCovid"}

# Collect all groups: (display_name, symptom_column_label, patient_set)
all_groups = []
for col in symptom_columns:
    info = symptom_patients[col]
    all_groups.append((info["display"], col, info["patients"]))
all_groups.append(("GI_NauseaOrDiarrhea", "gastrointesti0l | 0usea | diarrhea", gi_extended_patients))
all_groups.append(("GI_Any", "0usea | diarrhea | abdomi0l_pain", gi_any_patients))
all_groups.append(("NonLongCovid", "LongCovid==0 / delete", non_lc_patients))

# All NLC patients: everyone with FASTA data who is NOT explicitly LC in the symptom Excel
lc_patients_in_excel = set(symptom_df[symptom_df["LongCovid"] == 1]["SampleID"].tolist())
all_fasta_patients = set(all_contig_idx.keys())
all_nlc_patients = all_fasta_patients - lc_patients_in_excel
symptom_patients["_AllNLC"] = {"patients": all_nlc_patients, "display": "AllNLC"}
all_groups.append(("AllNLC", "Not explicitly LC (all remaining)", all_nlc_patients))
print(f"\n  AllNLC (not explicitly LC): {len(all_nlc_patients)} patients")

# LC GI-negative: LC patients who do NOT have any GI symptoms
lc_gi_negative_patients = lc_patients_in_excel - gi_extended_patients
symptom_patients["_LC_GI_Negative"] = {"patients": lc_gi_negative_patients, "display": "LC_GI_Negative"}
all_groups.append(("LC_GI_Negative", "LC without gastrointesti0l/nausea/diarrhea", lc_gi_negative_patients))
print(f"  LC_GI_Negative: {len(lc_gi_negative_patients)} patients")

# ──────────────────────── Step 4: Create output folders and write all files ────────────────────────
print(f"\nCreating output in: {OUTPUT_DIR}")

if OUTPUT_DIR.exists():
    print(f"  WARNING: {OUTPUT_DIR} already exists. Aborting to avoid overwriting.")
    print(f"  Rename or delete the existing folder first.")
    raise SystemExit(1)

summary_rows = []

for display, col_label, patients in all_groups:
    for tp_code, tp_label in TIMEPOINT_MAP.items():
        folder_name = f"{display}_{tp_label}"
        folder_path = OUTPUT_DIR / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)

        copied_patients = []
        for patient_id in sorted(patients):
            runs = run_idx.get(patient_id, {}).get(tp_code, {})
            if not runs:
                continue

            # Sort by run subfolder name so all file types get consistent ordering
            sorted_runs = sorted(runs.keys())
            ac_files = [runs[r]["all_contig"] for r in sorted_runs if "all_contig" in runs[r]]
            fc_files = [runs[r]["filtered_contig"] for r in sorted_runs if "filtered_contig" in runs[r]]
            csv_files = [runs[r]["filtered_csv"] for r in sorted_runs if "filtered_csv" in runs[r]]

            if not ac_files:
                continue

            write_patient_files(
                patient_id, tp_code, folder_path,
                all_contig_sources=ac_files,
                filtered_contig_sources=fc_files,
                filtered_csv_sources=csv_files,
            )
            copied_patients.append(patient_id)

        n = len(copied_patients)
        status = f"{n} patients" if n > 0 else "EMPTY (no data)"
        print(f"  {folder_name:45s} -> {status}")

        summary_rows.append({
            "Symptom": display,
            "Symptom_Column": col_label,
            "Timepoint": tp_label,
            "Timepoint_Code": tp_code,
            "Folder_Name": folder_name,
            "Total_Patients_With_Symptom": len(patients),
            "Patients_With_FASTA": n,
            "Patient_IDs": ", ".join(copied_patients) if copied_patients else "",
        })

# ──────────────────────── Step 5: Write summary Excel ────────────────────────
summary_df = pd.DataFrame(summary_rows)

pivot_df = summary_df.pivot_table(
    index="Symptom", columns="Timepoint", values="Patients_With_FASTA", aggfunc="first",
).reset_index()
pivot_df.columns.name = None
pivot_df = pivot_df[["Symptom", "T1", "T2", "T3"]]
symptom_totals = summary_df.groupby("Symptom")["Total_Patients_With_Symptom"].first()
pivot_df["Total_Patients_With_Symptom"] = pivot_df["Symptom"].map(symptom_totals)
pivot_df = pivot_df.sort_values("Total_Patients_With_Symptom", ascending=False)

# Patient × Symptom matrix
patient_symptom_rows = []
all_patients_in_output = set()
for key, info in symptom_patients.items():
    for pid in info["patients"]:
        if pid in all_contig_idx:
            all_patients_in_output.add(pid)

for pid in sorted(all_patients_in_output):
    row = {"Patient_ID": pid}
    row["Group"] = "NonLongCovid" if pid in non_lc_patients else "LongCovid"
    tp_data = all_contig_idx.get(pid, {})
    row["Available_Timepoints"] = ", ".join(sorted(tp_data.keys()))
    for tp_code, tp_label in TIMEPOINT_MAP.items():
        n_runs = len(tp_data.get(tp_code, []))
        row[f"Runs_{tp_label}_{tp_code}"] = n_runs if n_runs > 0 else ""
    for col in symptom_columns:
        display = symptom_patients[col]["display"]
        row[display] = 1 if pid in symptom_patients[col]["patients"] else 0
    row["NonLongCovid"] = 1 if pid in non_lc_patients else 0
    row["GI_NauseaOrDiarrhea"] = 1 if pid in gi_extended_patients else 0
    row["GI_Any"] = 1 if pid in gi_any_patients else 0
    row["AllNLC"] = 1 if pid in all_nlc_patients else 0
    row["LC_GI_Negative"] = 1 if pid in lc_gi_negative_patients else 0
    patient_symptom_rows.append(row)

patient_matrix_df = pd.DataFrame(patient_symptom_rows)

# Runs per patient
run_count_rows = []
for pid in sorted(all_patients_in_output):
    tp_data = all_contig_idx.get(pid, {})
    row = {"Patient_ID": pid}
    for tp_code, tp_label in TIMEPOINT_MAP.items():
        n_runs = len(tp_data.get(tp_code, []))
        row[f"{tp_label} ({tp_code}) Runs"] = n_runs if n_runs > 0 else ""
        if n_runs > 0:
            sources = []
            for p in sorted(tp_data[tp_code]):
                parts = str(p).split("/")
                gi = next((i for i, x in enumerate(parts) if x.startswith("10x_Genomics")), None)
                if gi is not None and gi + 2 < len(parts):
                    sources.append(f"{parts[gi]}/{parts[gi+2]}")
                else:
                    sources.append(str(p))
            row[f"{tp_label} ({tp_code}) Sources"] = "; ".join(sources)
        else:
            row[f"{tp_label} ({tp_code}) Sources"] = ""
    run_count_rows.append(row)

run_count_df = pd.DataFrame(run_count_rows)

summary_path = OUTPUT_DIR / "Summary_SymptomFolders.xlsx"
with pd.ExcelWriter(summary_path, engine="openpyxl") as writer:
    pivot_df.to_excel(writer, sheet_name="Overview", index=False)
    summary_df.to_excel(writer, sheet_name="Detailed_Per_Folder", index=False)
    patient_matrix_df.to_excel(writer, sheet_name="Patient_Symptom_Matrix", index=False)
    run_count_df.to_excel(writer, sheet_name="Runs_Per_Patient", index=False)

print(f"\nSummary Excel saved to: {summary_path}")

# ──────────────────────── Final Summary ────────────────────────
total_folders = len(summary_rows)
total_files = summary_df["Patients_With_FASTA"].sum()
nonempty_folders = (summary_df["Patients_With_FASTA"] > 0).sum()

print(f"\n{'=' * 60}")
print(f"FINAL SUMMARY")
print(f"{'=' * 60}")
print(f"  Groups:             {len(all_groups)} (31 symptoms + GI_extended + GI_Any + NonLongCovid)")
print(f"  Total folders:      {total_folders}")
print(f"  Non-empty folders:  {nonempty_folders}")
print(f"  Total patient-files:{total_files} (×3 files each: .fasta, _filtered.fasta, _filtered_annotations.csv)")
print(f"  Output directory:   {OUTPUT_DIR}")
print(f"  Summary Excel:      {summary_path}")
print()
print("Overview (patients with FASTA per timepoint):")
print(pivot_df.to_string(index=False))
