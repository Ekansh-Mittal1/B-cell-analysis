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
FASTA_ROOT = Path("/Users/teichmann/Desktop/all fastas long covid study")
SYMPTOM_EXCEL = Path("/Users/teichmann/Downloads/FullsymptomWithControl-082722 (1).xlsx")
OUTPUT_DIR = Path("/Users/teichmann/Desktop/LongCovid_Symptom_FASTA")

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

# Index by file type: patient -> timepoint -> [paths]
all_contig_idx = defaultdict(lambda: defaultdict(list))
filtered_contig_idx = defaultdict(lambda: defaultdict(list))
filtered_csv_idx = defaultdict(lambda: defaultdict(list))

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
    if fname == "all_contig.fasta":
        all_contig_idx[pid][tp].append(file_path)
    elif fname == "filtered_contig.fasta":
        filtered_contig_idx[pid][tp].append(file_path)
    elif fname == "filtered_contig_annotations.csv":
        filtered_csv_idx[pid][tp].append(file_path)

print(f"  all_contig.fasta:                {sum(len(tps) for tps in all_contig_idx.values())} patient-timepoints")
print(f"  filtered_contig.fasta:           {sum(len(tps) for tps in filtered_contig_idx.values())} patient-timepoints")
print(f"  filtered_contig_annotations.csv: {sum(len(tps) for tps in filtered_csv_idx.values())} patient-timepoints")

# ──────────────────────── Step 3: Build all groups to process ────────────────────────

# Add GI extended cohort
gi_extended = (
    (symptom_df["gastrointesti0l"] == 1) |
    (symptom_df["0usea"] == 1) |
    (symptom_df["diarrhea"] == 1)
)
gi_extended_patients = set(symptom_df[gi_extended]["SampleID"].tolist())
symptom_patients["_GI_Extended"] = {"patients": gi_extended_patients, "display": "GI_NauseaOrDiarrhea"}

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
all_groups.append(("NonLongCovid", "LongCovid==0 / delete", non_lc_patients))

# ──────────────────────── Step 4: Create output folders and write all files ────────────────────────
print(f"\nCreating output in: {OUTPUT_DIR}")

if OUTPUT_DIR.exists():
    shutil.rmtree(OUTPUT_DIR)

summary_rows = []

for display, col_label, patients in all_groups:
    for tp_code, tp_label in TIMEPOINT_MAP.items():
        folder_name = f"{display}_{tp_label}"
        folder_path = OUTPUT_DIR / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)

        copied_patients = []
        for patient_id in sorted(patients):
            ac_files = sorted(all_contig_idx.get(patient_id, {}).get(tp_code, []))
            fc_files = sorted(filtered_contig_idx.get(patient_id, {}).get(tp_code, []))
            csv_files = sorted(filtered_csv_idx.get(patient_id, {}).get(tp_code, []))

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
print(f"  Groups:             {len(all_groups)} (31 symptoms + GI_extended + NonLongCovid)")
print(f"  Total folders:      {total_folders}")
print(f"  Non-empty folders:  {nonempty_folders}")
print(f"  Total patient-files:{total_files} (×3 files each: .fasta, _filtered.fasta, _filtered_annotations.csv)")
print(f"  Output directory:   {OUTPUT_DIR}")
print(f"  Summary Excel:      {summary_path}")
print()
print("Overview (patients with FASTA per timepoint):")
print(pivot_df.to_string(index=False))
