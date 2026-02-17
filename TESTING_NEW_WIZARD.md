# Testing the New Wizard Flow

## What Changed

The wizard now requires you to **define your study upfront** before analysis runs:

1. **Step 1: Define Study** - Name your study and assign files to timepoints
2. **Step 2: Choose Database** - Select IMGT or custom database
3. **Step 3: Review & Start** - Confirm and start analysis

## Expected Behavior

### When You Run a Fresh Analysis

1. **In the Wizard:**
   - Enter a study name (e.g., "Memory Loss")
   - Click "Select Study Folder" and choose a folder with subfolders
   - Subfolders should auto-populate as timepoints (e.g., `MemoryProblems_T1/` → "T1")
   - Verify each timepoint shows the correct file count

2. **During Analysis:**
   - Files are staged with timepoint prefixes to avoid collisions
   - A `timepoint_mapping.json` is created mapping staged filenames to their timepoints

3. **In the Results View:**
   - **Sequence Browser** should show a 4-level hierarchy:
     ```
     📍 T1 (600 sequences)
       > INCOV002.fasta (45)
       > INCOV007.fasta (82)
       ...
     📍 T2 (589 sequences)
       > T2_INCOV030.fasta (120)  ← Note: prefixed if collision with T1
       ...
     📍 T3 (773 sequences)
       ...
     ```
   - **Dashboard** should show longitudinal analysis automatically (since study design is auto-populated)
   - **NO "Organize" tab** (it's been removed)

## Debugging

Open the browser console (View > Developer > Developer Tools) and look for:

```
[App] Received timepoint_mapping artifact with X entries
[SequenceBrowser] timepointMapping keys: X
[SequenceBrowser] hasTimepointMapping: true
[SequenceBrowser] Built X timepoint groups
```

If you see:
- `timepointMapping keys: 0` → The mapping wasn't loaded
- `hasTimepointMapping: false` → UI falls back to flat file list
- `Built 0 timepoint groups` → Mapping exists but files don't match

## Known Issues

### Loading Old Sessions

If you load a session from before this code was implemented:
- ❌ No `timepoint_mapping.json` exists in that session's output directory
- ❌ UI will show the flat file list (fallback behavior)
- ✅ This is expected - old sessions can't be retroactively timepoint-aware

**Solution:** Run a new analysis with the new wizard.

### File Prefixes Look Weird

You might see files like:
- `INCOV022.fasta` (no prefix)
- `T2_INCOV030.fasta` (prefixed)
- `T3_INCOV030.fasta` (prefixed)

This is **correct** when:
- INCOV022 only exists at T1 (no collision, no prefix)
- INCOV030 exists at T1, T2, and T3 (collision, so T2 and T3 get prefixes)

The first occurrence doesn't get a prefix, subsequent collisions do. This is by design to keep filenames clean when possible.

## What to Test

1. **Fresh Analysis:**
   - Select the `memory/` folder with 3 timepoint subfolders
   - Verify the wizard detects 3 timepoints
   - Run the analysis
   - Check if the Sequence Browser shows the timepoint hierarchy

2. **Check Console Logs:**
   - Look for `[App] Received timepoint_mapping artifact`
   - Verify the mapping has entries
   - Check if SequenceBrowser logs indicate the mapping is being used

3. **Verify Files:**
   - In the latest `outs/run_XXXX/` directory, verify:
     - `timepoint_mapping.json` exists
     - `study_name.txt` exists

If the timepoint hierarchy doesn't show up, the console logs should reveal why.
