#!/usr/bin/env python3
"""
Organize all_contig.fasta files from Long COVID study by symptom and timepoint.

For EVERY symptom in the Excel file, creates 3 folders (T1/T2/T3).
Also produces a summary Excel showing patient counts per symptom/timepoint.
"""

import os
import re
import shutil
import pandas as pd
from pathlib import Path
from collections import defaultdict

# ──────────────────────── Configuration ────────────────────────
FASTA_ROOT = Path("/Users/teichmann/Desktop/all fastas long covid study")
SYMPTOM_EXCEL = Path("/Users/teichmann/Downloads/FullsymptomWithControl-082722 (1).xlsx")
OUTPUT_DIR = Path("/Users/teichmann/Desktop/LongCovid_Symptom_FASTA")

TIMEPOINT_MAP = {
    "BL": "T1",
    "AC": "T2",
    "CV": "T3",
}

# Columns to skip (metadata, non-symptom, empty category headers, lab markers)
SKIP_COLUMNS = {
    "SampleID", "LongCovid", "long COVID", "Gender1", "Gender", "DOB", "age",
    "No. Of Symptoms", "No. of Pre-Infections", "No. of Antibodies", ">1 Antibody",
    # Category headers with 0 patients (section dividers)
    "Respiratory", "Neurological", "Gastrointesti0l", "Ear_nose_taste", "Musculoskeletal",
    # Lab/viremia/antibody markers — not symptoms
    "R0emia_T1", "CMV_viremia_T1_T2", "EBV_viremia_T1_T2",
    "IFN_a2_IgG_T3", "RibosomalPhosphoprotein_P1_IgG_T3",
    "Ro_SS_A_IgG_T3", "La_SS_B_IgG_T3", "Jo_1_IgG_T3", "U1_snRNP_IgG_T3",
}

# Clean display names for folder creation (fix encoding artifacts)
DISPLAY_NAMES = {
    "anxiety": "Anxiety",
    "depression": "Depression",
    "difficulty_sleeping": "DifficultySleeping",
    "Generalized_symptoms": "GeneralizedSymptoms",
    "fatigue": "Fatigue",
    "fever_or_chills": "FeverOrChills",
    "cough": "Cough",
    "shortness_of_breath": "ShortnessOfBreath",
    "sputum": "Sputum",
    "Cardiovascular": "Cardiovascular",
    "heart_palpitations": "HeartPalpitations",
    "headache": "Headache",
    "neuro": "Neuro",
    "memory_problems": "MemoryProblems",
    "difficulty_concentrating": "DifficultyConcentrating",
    "dizziness": "Dizziness",
    "blurry_vision": "BlurryVision",
    "abdomi0l_pain": "AbdominalPain",
    "0usea": "Nausea",
    "diarrhea": "Diarrhea",
    "loss_of_smell": "LossOfSmell",
    "loss_of_taste": "LossOfTaste",
    "loss_of_sense": "LossOfSense",
    "hair_loss": "HairLoss",
    "i0bility_to_exercise": "InabilityToExercise",
    "joint_pain": "JointPain",
    "muscle_body_aches": "MuscleBodyAches",
    "pain_feet_hands": "PainFeetHands",
    "persistent_chest_pain": "PersistentChestPain",
    "respiratory_viral": "RespiratoryViral",
    "gastrointesti0l": "Gastrointestinal",
}

# ──────────────────────── Step 1: Load symptom data ────────────────────────
print("Loading symptom data...")
symptom_df = pd.read_excel(SYMPTOM_EXCEL)

# Identify all binary symptom columns with at least 1 positive patient
symptom_columns = []
for col in symptom_df.columns:
    if col in SKIP_COLUMNS:
        continue
    vals = symptom_df[col].dropna().unique()
    is_binary = set(vals).issubset({0, 1, 0.0, 1.0})
    count_pos = (symptom_df[col] == 1).sum()
    if is_binary and count_pos > 0:
        symptom_columns.append(col)

print(f"Found {len(symptom_columns)} symptom columns with positive patients:")
symptom_patients = {}
for col in symptom_columns:
    patients = sorted(symptom_df[symptom_df[col] == 1]["SampleID"].tolist())
    display = DISPLAY_NAMES.get(col, col)
    symptom_patients[col] = {"patients": set(patients), "display": display}
    print(f"  {display:35s} ({col:35s}): {len(patients)} patients")

# ──────────────────────── Step 2: Index all FASTA files ────────────────────────
print(f"\nIndexing all_contig.fasta files from {FASTA_ROOT}...")

patient_timepoint_files = defaultdict(lambda: defaultdict(list))

for fasta_path in FASTA_ROOT.rglob("all_contig.fasta"):
    path_str = str(fasta_path)
    match = re.search(r"/(INCOV\d+)-(BL|AC|CV)/", path_str)
    if match:
        patient_id = match.group(1)
        timepoint_code = match.group(2)
        patient_timepoint_files[patient_id][timepoint_code].append(fasta_path)

print(f"  Found FASTA files for {len(patient_timepoint_files)} patients")

# ──────────────────────── Step 3: Create output folders and copy files ────────────────────────
print(f"\nCreating output in: {OUTPUT_DIR}")

if OUTPUT_DIR.exists():
    shutil.rmtree(OUTPUT_DIR)

# Tracking for summary
summary_rows = []

for col in symptom_columns:
    info = symptom_patients[col]
    display = info["display"]
    patients = info["patients"]

    for tp_code, tp_label in TIMEPOINT_MAP.items():
        folder_name = f"{display}_{tp_label}"
        folder_path = OUTPUT_DIR / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)

        copied_patients = []
        for patient_id in sorted(patients):
            if patient_id not in patient_timepoint_files:
                continue
            if tp_code not in patient_timepoint_files[patient_id]:
                continue

            fasta_files = sorted(patient_timepoint_files[patient_id][tp_code])
            output_file = folder_path / f"{patient_id}.fasta"
            multi_run = len(fasta_files) > 1

            with open(output_file, "w") as out_f:
                for run_idx, fasta_src in enumerate(fasta_files, start=1):
                    run_prefix = f"run{run_idx}_" if multi_run else ""
                    with open(fasta_src, "r") as in_f:
                        for line in in_f:
                            if line.startswith(">") and run_prefix:
                                # Prefix the sequence header to avoid barcode collisions
                                # e.g. >ACGT-1_contig_1 -> >run1_ACGT-1_contig_1
                                out_f.write(f">{run_prefix}{line[1:]}")
                            else:
                                out_f.write(line)
                        if not line.endswith("\n"):
                            out_f.write("\n")

            copied_patients.append(patient_id)

        n = len(copied_patients)
        status = f"{n} patients" if n > 0 else "EMPTY (no data)"
        print(f"  {folder_name:45s} -> {status}")

        summary_rows.append({
            "Symptom": display,
            "Symptom_Column": col,
            "Timepoint": tp_label,
            "Timepoint_Code": tp_code,
            "Folder_Name": folder_name,
            "Total_Patients_With_Symptom": len(patients),
            "Patients_With_FASTA": n,
            "Patient_IDs": ", ".join(copied_patients) if copied_patients else "",
        })

# ──────────────────────── Step 3b: GI extended cohort (gastrointesti0l OR nausea OR diarrhea) ────────────────────────
print("\nCreating GI extended cohort (gastrointesti0l OR nausea OR diarrhea)...")

gi_extended = (
    (symptom_df["gastrointesti0l"] == 1) |
    (symptom_df["0usea"] == 1) |
    (symptom_df["diarrhea"] == 1)
)
gi_extended_patients = set(symptom_df[gi_extended]["SampleID"].tolist())
print(f"  Found {len(gi_extended_patients)} patients: {sorted(gi_extended_patients)}")

symptom_patients["_GI_Extended"] = {"patients": gi_extended_patients, "display": "GI_NauseaOrDiarrhea"}

for tp_code, tp_label in TIMEPOINT_MAP.items():
    folder_name = f"GI_NauseaOrDiarrhea_{tp_label}"
    folder_path = OUTPUT_DIR / folder_name
    folder_path.mkdir(parents=True, exist_ok=True)

    copied_patients = []
    for patient_id in sorted(gi_extended_patients):
        if patient_id not in patient_timepoint_files:
            continue
        if tp_code not in patient_timepoint_files[patient_id]:
            continue

        fasta_files = sorted(patient_timepoint_files[patient_id][tp_code])
        output_file = folder_path / f"{patient_id}.fasta"
        multi_run = len(fasta_files) > 1

        with open(output_file, "w") as out_f:
            for run_idx, fasta_src in enumerate(fasta_files, start=1):
                run_prefix = f"run{run_idx}_" if multi_run else ""
                with open(fasta_src, "r") as in_f:
                    for line in in_f:
                        if line.startswith(">") and run_prefix:
                            out_f.write(f">{run_prefix}{line[1:]}")
                        else:
                            out_f.write(line)
                    if not line.endswith("\n"):
                        out_f.write("\n")

        copied_patients.append(patient_id)

    n = len(copied_patients)
    status = f"{n} patients" if n > 0 else "EMPTY (no data)"
    print(f"  {folder_name:45s} -> {status}")

    summary_rows.append({
        "Symptom": "GI_NauseaOrDiarrhea",
        "Symptom_Column": "gastrointesti0l | 0usea | diarrhea",
        "Timepoint": tp_label,
        "Timepoint_Code": tp_code,
        "Folder_Name": folder_name,
        "Total_Patients_With_Symptom": len(gi_extended_patients),
        "Patients_With_FASTA": n,
        "Patient_IDs": ", ".join(copied_patients) if copied_patients else "",
    })

# ──────────────────────── Step 3c: Non-Long COVID control folders ────────────────────────
print("\nCreating Non-Long COVID control folders...")

non_lc_mask = (
    (symptom_df["LongCovid"] == 0) |
    (symptom_df["long COVID"].astype(str).str.lower().str.contains("delete", na=False)) |
    (symptom_df["long COVID"].astype(str).str.lower().str.contains("non-long", na=False))
)
non_lc_patients = set(symptom_df[non_lc_mask]["SampleID"].tolist())
print(f"  Found {len(non_lc_patients)} non-Long COVID patients: {sorted(non_lc_patients)}")

# Add as a special "symptom" group
symptom_patients["_NonLongCovid"] = {"patients": non_lc_patients, "display": "NonLongCovid"}

for tp_code, tp_label in TIMEPOINT_MAP.items():
    folder_name = f"NonLongCovid_{tp_label}"
    folder_path = OUTPUT_DIR / folder_name
    folder_path.mkdir(parents=True, exist_ok=True)

    copied_patients = []
    for patient_id in sorted(non_lc_patients):
        if patient_id not in patient_timepoint_files:
            continue
        if tp_code not in patient_timepoint_files[patient_id]:
            continue

        fasta_files = sorted(patient_timepoint_files[patient_id][tp_code])
        output_file = folder_path / f"{patient_id}.fasta"
        multi_run = len(fasta_files) > 1

        with open(output_file, "w") as out_f:
            for run_idx, fasta_src in enumerate(fasta_files, start=1):
                run_prefix = f"run{run_idx}_" if multi_run else ""
                with open(fasta_src, "r") as in_f:
                    for line in in_f:
                        if line.startswith(">") and run_prefix:
                            out_f.write(f">{run_prefix}{line[1:]}")
                        else:
                            out_f.write(line)
                    if not line.endswith("\n"):
                        out_f.write("\n")

        copied_patients.append(patient_id)

    n = len(copied_patients)
    status = f"{n} patients" if n > 0 else "EMPTY (no data)"
    print(f"  {folder_name:45s} -> {status}")

    summary_rows.append({
        "Symptom": "NonLongCovid",
        "Symptom_Column": "LongCovid==0 / delete",
        "Timepoint": tp_label,
        "Timepoint_Code": tp_code,
        "Folder_Name": folder_name,
        "Total_Patients_With_Symptom": len(non_lc_patients),
        "Patients_With_FASTA": n,
        "Patient_IDs": ", ".join(copied_patients) if copied_patients else "",
    })

# ──────────────────────── Step 4: Write summary Excel ────────────────────────
summary_df = pd.DataFrame(summary_rows)

# Sheet 1: Detailed per-folder breakdown
# Sheet 2: Pivot table (symptoms × timepoints)
pivot_df = summary_df.pivot_table(
    index="Symptom",
    columns="Timepoint",
    values="Patients_With_FASTA",
    aggfunc="first",
).reset_index()
pivot_df.columns.name = None
pivot_df = pivot_df[["Symptom", "T1", "T2", "T3"]]

# Add total patients with symptom
symptom_totals = summary_df.groupby("Symptom")["Total_Patients_With_Symptom"].first()
pivot_df["Total_Patients_With_Symptom"] = pivot_df["Symptom"].map(symptom_totals)
pivot_df = pivot_df.sort_values("Total_Patients_With_Symptom", ascending=False)

# Sheet 3: Patient × Symptom matrix (with run counts per timepoint)
patient_symptom_rows = []
all_patients_in_output = set()
for key, info in symptom_patients.items():
    for pid in info["patients"]:
        if pid in patient_timepoint_files:
            all_patients_in_output.add(pid)

for pid in sorted(all_patients_in_output):
    row = {"Patient_ID": pid}
    row["Group"] = "NonLongCovid" if pid in non_lc_patients else "LongCovid"
    tp_data = patient_timepoint_files.get(pid, {})
    tps_available = sorted(tp_data.keys())
    row["Available_Timepoints"] = ", ".join(tps_available)
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

# Sheet 4: Dedicated run-count table (Patient × Timepoint → number of runs)
run_count_rows = []
for pid in sorted(all_patients_in_output):
    tp_data = patient_timepoint_files.get(pid, {})
    row = {"Patient_ID": pid}
    for tp_code, tp_label in TIMEPOINT_MAP.items():
        n_runs = len(tp_data.get(tp_code, []))
        row[f"{tp_label} ({tp_code}) Runs"] = n_runs if n_runs > 0 else ""
        # Also list the source folders for traceability
        if n_runs > 0:
            sources = []
            for p in sorted(tp_data[tp_code]):
                # Extract the 10x_Genomics folder and subfolder
                parts = str(p).split("/")
                genomics_idx = next(
                    (i for i, x in enumerate(parts) if x.startswith("10x_Genomics")),
                    None,
                )
                if genomics_idx is not None and genomics_idx + 2 < len(parts):
                    sources.append(f"{parts[genomics_idx]}/{parts[genomics_idx+2]}")
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
print(f"  Symptoms:           {len(symptom_columns)} + NonLongCovid control")
print(f"  Total folders:      {total_folders} ({len(symptom_columns)} symptoms × 3 timepoints)")
print(f"  Non-empty folders:  {nonempty_folders}")
print(f"  Total FASTA files:  {total_files}")
print(f"  Output directory:   {OUTPUT_DIR}")
print(f"  Summary Excel:      {summary_path}")
print()

print("Overview (patients with FASTA per timepoint):")
print(pivot_df.to_string(index=False))
