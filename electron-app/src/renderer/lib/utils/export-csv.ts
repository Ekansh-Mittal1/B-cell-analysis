/**
 * Export utilities for all views.
 * CSV for simple exports, XLSX (multi-sheet) for shared clones & clonal dynamics.
 */

import * as XLSX from 'xlsx';
import type { GroupTimepointMetrics, LongitudinalGroupData } from './repertoire-metrics';
import { computeDiversity, computeVGeneFrequencies, computeIsotypeFrequencies } from './repertoire-metrics';
import type { ClonalDynamicsEntry, ClonalDynamicsData, IsotypeTileEntry } from './public-clones';
import { computePublicClonesPerTimepoint, computePublicClones, getTimepointLabels } from './public-clones';
import type { TreeMetadata, PublicClonesData, CohortResults, FileGroup, TimepointMapping, CovidMatchData } from '../stores/app';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function esc(value: any): string {
  if (value === null || value === undefined) return '';
  const str = String(value);
  if (str.includes(',') || str.includes('"') || str.includes('\n')) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

function row(values: any[]): string {
  return values.map(esc).join(',');
}

/**
 * Trigger a CSV download in the browser or via Electron save dialog.
 */
export async function downloadCsv(csvContent: string, defaultFilename: string): Promise<void> {
  if (window.electronAPI) {
    const filePath = await window.electronAPI.saveFile({
      defaultPath: defaultFilename,
      filters: [
        { name: 'CSV Files', extensions: ['csv'] },
        { name: 'All Files', extensions: ['*'] }
      ]
    });
    if (!filePath) return;
    const result = await window.electronAPI.writeFile(filePath, csvContent);
    if (!result.success) {
      alert(`Failed to export: ${result.error || 'Unknown error'}`);
    }
  } else {
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = defaultFilename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }
}

/**
 * Trigger an XLSX workbook download in the browser or via Electron save dialog.
 */
export async function downloadXlsx(workbook: XLSX.WorkBook, defaultFilename: string): Promise<void> {
  const xlsxData = XLSX.write(workbook, { bookType: 'xlsx', type: 'array' }) as ArrayBuffer;
  const bytes = new Uint8Array(xlsxData);

  if (window.electronAPI) {
    const filePath = await window.electronAPI.saveFile({
      defaultPath: defaultFilename,
      filters: [
        { name: 'Excel Files', extensions: ['xlsx'] },
        { name: 'All Files', extensions: ['*'] }
      ]
    });
    if (!filePath) return;
    // Convert to base64 for IPC transfer (chunked to avoid call-stack limits)
    let base64 = '';
    const chunkSize = 0x8000;
    for (let i = 0; i < bytes.length; i += chunkSize) {
      base64 += String.fromCharCode.apply(null, Array.from(bytes.subarray(i, i + chunkSize)));
    }
    base64 = btoa(base64);
    const result = await window.electronAPI.writeBinaryFile(filePath, base64);
    if (!result.success) {
      alert(`Failed to export: ${result.error || 'Unknown error'}`);
    }
  } else {
    const blob = new Blob([bytes], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = defaultFilename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }
}

/** Truncate an Excel sheet name to 31 chars (Excel limit) and ensure uniqueness. */
function safeSheetName(name: string, existing: string[]): string {
  let safe = name.replace(/[\\\/\?\*\[\]:]/g, '-').slice(0, 31);
  let suffix = 2;
  const base = safe;
  while (existing.includes(safe)) {
    const tag = ` (${suffix++})`;
    safe = base.slice(0, 31 - tag.length) + tag;
  }
  return safe;
}

// ---------------------------------------------------------------------------
// 1. Dashboard Export
// ---------------------------------------------------------------------------

/**
 * Export repertoire dashboard metrics.
 * One row per cohort × group × timepoint with all diversity metrics,
 * V-gene frequencies, and isotype frequencies.
 *
 * Structure:
 *   Cohort | Group | Timepoint | Total Sequences | Unique Clones | Shannon Entropy |
 *   Simpson Index | Chao1 | Gini Index | Mean SHM | Median SHM | D50 |
 *   Productive % | Mean Clone Size |
 *   V-Gene frequencies (IGHV1..IGHV7) | Isotype frequencies (IgM, IgD, IgG, IgA, IgE)
 */
export function dashboardMetricsToCsv(
  diseaseMetrics: GroupTimepointMetrics[],
  controlMetrics: GroupTimepointMetrics[],
  diseaseCohortName: string,
  controlCohortName: string,
  diseaseLongitudinal: LongitudinalGroupData[],
  controlLongitudinal: LongitudinalGroupData[]
): string {
  const lines: string[] = [];

  // --- Sheet 1: Per-Timepoint Metrics ---
  lines.push('# Per-Timepoint Repertoire Metrics');
  const vGeneFamilies = collectVGeneFamilies([...diseaseMetrics, ...controlMetrics]);
  const isoTypes = ['IgM', 'IgD', 'IgG', 'IgA', 'IgE'];

  const headers = [
    'Cohort', 'Group', 'Timepoint',
    'Total Sequences', 'Unique Clones', 'Mean Clone Size',
    'Shannon Entropy', 'Simpson Index', 'Chao1', 'Gini Index',
    'Mean SHM', 'Median SHM', 'D50', 'Productive %',
    ...vGeneFamilies.map(f => `V-Gene ${f} (freq)`),
    ...isoTypes.map(i => `${i} (freq)`)
  ];
  lines.push(row(headers));

  function pushMetricRows(metrics: GroupTimepointMetrics[], cohortName: string) {
    for (const m of metrics) {
      const vFreqMap = new Map(m.vGeneFreqs.map(v => [v.family, v.frequency]));
      const iFreqMap = new Map(m.isotypeFreqs.map(i => [i.isotype, i.frequency]));
      lines.push(row([
        cohortName, m.groupName, m.timepointLabel,
        m.diversity.totalSequences, m.diversity.uniqueClones,
        m.diversity.meanCloneSize.toFixed(2),
        m.diversity.shannonEntropy.toFixed(4),
        m.diversity.simpsonIndex.toFixed(4),
        m.diversity.chao1.toFixed(1),
        m.diversity.giniIndex.toFixed(4),
        m.diversity.meanSHM.toFixed(2),
        m.diversity.medianSHM.toFixed(2),
        m.diversity.d50,
        m.diversity.productivePercent.toFixed(1),
        ...vGeneFamilies.map(f => (vFreqMap.get(f) ?? 0).toFixed(4)),
        ...isoTypes.map(i => (iFreqMap.get(i) ?? 0).toFixed(4))
      ]));
    }
  }

  pushMetricRows(diseaseMetrics, diseaseCohortName);
  if (controlMetrics.length > 0) {
    pushMetricRows(controlMetrics, controlCohortName);
  }

  // --- Sheet 2: Longitudinal Diversity Trajectory ---
  if (diseaseLongitudinal.length > 0 || controlLongitudinal.length > 0) {
    lines.push('');
    lines.push('# Longitudinal Diversity Trajectory');
    lines.push(row([
      'Cohort', 'Group', 'Timepoint',
      'Total Sequences', 'Unique Clones',
      'Shannon Entropy', 'Simpson Index', 'Chao1', 'Gini Index',
      'Mean SHM', 'D50', 'Productive %',
      ...isoTypes.map(i => `${i} (freq)`)
    ]));

    function pushLongitudinal(data: LongitudinalGroupData[], cohortName: string) {
      for (const group of data) {
        for (let i = 0; i < group.timepointLabels.length; i++) {
          const d = group.diversityTrajectory[i];
          const iso = group.isotypeTrajectory[i] ?? [];
          const iMap = new Map(iso.map(x => [x.isotype, x.frequency]));
          lines.push(row([
            cohortName, group.groupName, group.timepointLabels[i],
            d.totalSequences, d.uniqueClones,
            d.shannonEntropy.toFixed(4), d.simpsonIndex.toFixed(4),
            d.chao1.toFixed(1), d.giniIndex.toFixed(4),
            d.meanSHM.toFixed(2), d.d50, d.productivePercent.toFixed(1),
            ...isoTypes.map(x => (iMap.get(x) ?? 0).toFixed(4))
          ]));
        }
      }
    }

    pushLongitudinal(diseaseLongitudinal, diseaseCohortName);
    pushLongitudinal(controlLongitudinal, controlCohortName);
  }

  return lines.join('\n');
}

function collectVGeneFamilies(metrics: GroupTimepointMetrics[]): string[] {
  const families = new Set<string>();
  for (const m of metrics) {
    for (const v of m.vGeneFreqs) families.add(v.family);
  }
  return [...families].sort();
}

// ---------------------------------------------------------------------------
// 1b. Dashboard Per-Patient Export
// ---------------------------------------------------------------------------

export interface PerPatientExportParams {
  diseaseFileGroups: FileGroup[];
  diseaseTimepointMapping: TimepointMapping;
  diseaseCohortName: string;
  controlFileGroups?: FileGroup[];
  controlTimepointMapping?: TimepointMapping;
  controlCohortName?: string;
}

/**
 * Export per-patient (per-file) repertoire metrics.
 * One row per patient × timepoint with full diversity metrics + isotype frequencies.
 * Patient ID is derived from the original filename (timepoint prefix stripped).
 */
export function dashboardPerPatientCsv(params: PerPatientExportParams): string {
  const lines: string[] = [];
  const isoTypes = ['IgM', 'IgD', 'IgG', 'IgA', 'IgE'];

  // Collect all V-gene families across all files for consistent columns
  const allVFamilies = new Set<string>();

  interface PatientRow {
    cohort: string;
    patientId: string;
    timepoint: string;
    fileGroup: FileGroup;
  }

  const allRows: PatientRow[] = [];

  function collectRows(fileGroups: FileGroup[], tpMapping: TimepointMapping, cohortName: string) {
    for (const fg of fileGroups) {
      const entry = tpMapping[fg.filename];
      const timepoint = entry?.timepoint ?? '';
      // Patient ID = original filename without extension
      let patientId = entry?.originalFile ?? fg.filename;
      // Strip file extension
      patientId = patientId.replace(/\.(fasta|fa|fastq|fq|csv|tsv)$/i, '');
      allRows.push({ cohort: cohortName, patientId, timepoint, fileGroup: fg });

      // Pre-collect V-gene families
      for (const v of computeVGeneFrequencies(fg.sequences)) {
        allVFamilies.add(v.family);
      }
    }
  }

  collectRows(params.diseaseFileGroups, params.diseaseTimepointMapping, params.diseaseCohortName);
  if (params.controlFileGroups && params.controlTimepointMapping && params.controlCohortName) {
    collectRows(params.controlFileGroups, params.controlTimepointMapping, params.controlCohortName);
  }

  const vGeneFamilies = [...allVFamilies].sort();

  const headers = [
    'Cohort', 'Patient_ID', 'Timepoint',
    'Total Sequences', 'Unique Clones', 'Mean Clone Size',
    'Shannon Entropy', 'Simpson Index', 'Chao1', 'Gini Index',
    'Mean SHM', 'Median SHM', 'D50', 'Productive %',
    ...vGeneFamilies.map(f => `V-Gene ${f} (freq)`),
    ...isoTypes.map(i => `${i} (freq)`)
  ];
  lines.push(row(headers));

  for (const pr of allRows) {
    const seqs = pr.fileGroup.sequences;
    const div = computeDiversity(seqs);
    const vFreqs = computeVGeneFrequencies(seqs);
    const iFreqs = computeIsotypeFrequencies(seqs);
    const vFreqMap = new Map(vFreqs.map(v => [v.family, v.frequency]));
    const iFreqMap = new Map(iFreqs.map(i => [i.isotype, i.frequency]));

    lines.push(row([
      pr.cohort, pr.patientId, pr.timepoint,
      div.totalSequences, div.uniqueClones,
      div.meanCloneSize.toFixed(2),
      div.shannonEntropy.toFixed(4),
      div.simpsonIndex.toFixed(4),
      div.chao1.toFixed(1),
      div.giniIndex.toFixed(4),
      div.meanSHM.toFixed(2),
      div.medianSHM.toFixed(2),
      div.d50,
      div.productivePercent.toFixed(1),
      ...vGeneFamilies.map(f => (vFreqMap.get(f) ?? 0).toFixed(4)),
      ...isoTypes.map(i => (iFreqMap.get(i) ?? 0).toFixed(4))
    ]));
  }

  return lines.join('\n');
}

// ---------------------------------------------------------------------------
// 2. Phylogenetic Trees Export
// ---------------------------------------------------------------------------

/**
 * Export tree metadata as a flat CSV.
 * One row per tree with cohort, timepoint, clone info.
 */
export function treeMetadataToCsv(
  treeMetadata: TreeMetadata[],
  treeImages: string[],
  cohortResults: CohortResults[]
): string {
  const lines: string[] = [];
  const headers = ['Cohort', 'Timepoint', 'Clone ID', 'Clone Size', 'Tree File'];
  lines.push(row(headers));

  if (cohortResults.length > 0) {
    for (const cohort of cohortResults) {
      for (let i = 0; i < cohort.treeMetadata.length; i++) {
        const m = cohort.treeMetadata[i];
        const imgPath = cohort.treeImages[i] ?? '';
        const filename = imgPath.split('/').pop() ?? '';
        lines.push(row([
          cohort.cohortName,
          m.timepoint ?? '',
          m.clone_id ?? '',
          m.clone_size ?? '',
          filename
        ]));
      }
    }
  } else {
    for (let i = 0; i < treeMetadata.length; i++) {
      const m = treeMetadata[i];
      const imgPath = treeImages[i] ?? m.path ?? '';
      const filename = imgPath.split('/').pop() ?? '';
      lines.push(row([
        '',
        m.timepoint ?? '',
        m.clone_id ?? '',
        m.clone_size ?? '',
        filename
      ]));
    }
  }

  return lines.join('\n');
}

// ---------------------------------------------------------------------------
// 3. Clones - Shared Clones Full Export (XLSX, one sheet per cohort×timepoint)
// ---------------------------------------------------------------------------

export interface SharedClonesExportParams {
  fileGroups: FileGroup[];
  timepointMapping: TimepointMapping;
  cohortResults: CohortResults[];
}

/**
 * Build an XLSX workbook with one sheet per cohort × timepoint.
 * Sheet names: "Disease T1", "Disease T2", "Control T1", etc.
 */
export function sharedClonesWorkbook(params: SharedClonesExportParams): XLSX.WorkBook {
  const { fileGroups, timepointMapping, cohortResults } = params;
  const wb = XLSX.utils.book_new();
  const hasCohorts = cohortResults.length > 0;

  interface CohortSource {
    cohortName: string;
    fileGroups: FileGroup[];
    timepointMapping: TimepointMapping;
  }

  const sources: CohortSource[] = hasCohorts
    ? cohortResults.map(c => ({
        cohortName: c.cohortName,
        fileGroups: c.fileGroups,
        timepointMapping: c.timepointMapping
      }))
    : [{ cohortName: 'All Samples', fileGroups, timepointMapping }];

  const usedNames: string[] = [];

  for (const src of sources) {
    const tpLabels = getTimepointLabels(src.timepointMapping);
    const hasTimepoints = tpLabels.length > 0;
    const timepointsToExport = hasTimepoints ? tpLabels : [null];

    for (const tp of timepointsToExport) {
      const data = tp
        ? computePublicClonesPerTimepoint(src.fileGroups, src.timepointMapping, tp, { topN: 99999 })
        : computePublicClones(src.fileGroups, src.timepointMapping, { topN: 99999 });

      const clones = data.public_clones;
      if (clones.length === 0) continue;

      // Collect patients
      const allPatients = new Set<string>();
      for (const c of clones) {
        for (const p of c.patients) allPatients.add(p);
      }
      const sortedPatients = [...allPatients].sort();

      const headers = [
        'Clone ID', 'CDR3 Amino Acid', 'CDR3 DNA', 'V Gene', 'J Gene',
        'Patient Count', 'Total Sequence Count', 'Unique CDR3 Variants',
        ...sortedPatients.map(p => `${p} (count)`)
      ];

      const rows: any[][] = [headers];
      for (const c of clones) {
        rows.push([
          c.id.replace('clone_', ''),
          c.cdr3_aa,
          c.cdr3_dna,
          c.v_gene,
          c.j_gene,
          c.patient_count,
          c.sequence_count,
          c.unique_cdr3_variants,
          ...sortedPatients.map(p => c.sequences_by_patient?.[p]?.length ?? 0)
        ]);
      }

      const rawName = tp
        ? (hasCohorts ? `${src.cohortName} ${tp}` : tp)
        : src.cohortName;
      const sheetName = safeSheetName(rawName, usedNames);
      usedNames.push(sheetName);

      const ws = XLSX.utils.aoa_to_sheet(rows);
      XLSX.utils.book_append_sheet(wb, ws, sheetName);
    }
  }

  return wb;
}

// ---------------------------------------------------------------------------
// 4. Clones - Full Clonal Dynamics Export (XLSX, 3 sheets)
// ---------------------------------------------------------------------------

export interface ClonalDynamicsExportParams {
  dynamicsData: ClonalDynamicsData | null;
  cohortName?: string;
  controlDynamicsData?: ClonalDynamicsData | null;
  controlCohortName?: string;
  isotypeTiles: IsotypeTileEntry[];
  isotypeTimepointLabels: string[];
  controlIsotypeTiles?: IsotypeTileEntry[];
  controlIsotypeTimepointLabels?: string[];
}

/**
 * Build an XLSX workbook with three sheets:
 *   1. Frequency (Heatmap)   – per-clone frequency + raw count at each timepoint
 *   2. Clone Sizes (Bubbles) – per-clone raw counts + timepoint totals
 *   3. Isotype               – per-clone × per-timepoint isotype breakdown
 */
export function clonalDynamicsWorkbook(params: ClonalDynamicsExportParams): XLSX.WorkBook | null {
  const {
    dynamicsData, cohortName,
    controlDynamicsData, controlCohortName,
    isotypeTiles, isotypeTimepointLabels,
    controlIsotypeTiles, controlIsotypeTimepointLabels
  } = params;

  if (!dynamicsData) return null;
  const wb = XLSX.utils.book_new();
  const hasCohort = !!cohortName;
  const tpLabels = dynamicsData.timepointLabels;
  const isoTypes = ['IgM', 'IgD', 'IgG', 'IgA', 'IgE'];

  // ─── Sheet 1: Heatmap / Frequency ──────────────────────────────────
  {
    const headers = [
      ...(hasCohort ? ['Cohort'] : []),
      'Clone Rank', 'Clone ID', 'Lineage ID', 'CDR3 Amino Acid', 'V Gene', 'J Gene',
      'Status', 'Total Raw Count',
      ...tpLabels.flatMap(tp => [`${tp} Frequency`, `${tp} Raw Count`])
    ];
    const rows: any[][] = [headers];

    function pushEntries(entries: ClonalDynamicsEntry[], cName: string, labels: string[]) {
      for (const e of entries) {
        const tpMap = new Map(e.timepointSizes.map(t => [t.label, t]));
        rows.push([
          ...(hasCohort ? [cName] : []),
          e.cloneLabel, e.cloneId, e.lineageId ?? '',
          e.cdr3Aa, e.vGene, e.jGene, e.status, e.totalRawCount,
          ...labels.flatMap(tp => {
            const t = tpMap.get(tp);
            return [t ? Number(t.frequency.toFixed(6)) : 0, t ? t.rawCount : 0];
          })
        ]);
      }
    }

    pushEntries(dynamicsData.allEntries, cohortName ?? '', tpLabels);
    if (controlDynamicsData && controlCohortName) {
      pushEntries(controlDynamicsData.allEntries, controlCohortName, controlDynamicsData.timepointLabels);
    }

    XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(rows), 'Frequency (Heatmap)');
  }

  // ─── Sheet 2: Clone Sizes (Bubbles) ───────────────────────────────
  {
    const headers = [
      ...(hasCohort ? ['Cohort'] : []),
      'Clone Rank', 'Clone ID', 'Status',
      ...tpLabels.map(tp => `${tp} Size`)
    ];
    const rows: any[][] = [headers];

    function pushBubbles(data: ClonalDynamicsData, cName: string) {
      // Summary row: timepoint totals
      rows.push([
        ...(hasCohort ? [cName] : []),
        '(Timepoint Total)', '', '',
        ...data.timepointTotals.map(t => t.total)
      ]);
      for (const e of data.allEntries) {
        const tpMap = new Map(e.timepointSizes.map(t => [t.label, t]));
        rows.push([
          ...(hasCohort ? [cName] : []),
          e.cloneLabel, e.cloneId, e.status,
          ...data.timepointLabels.map(tp => tpMap.get(tp)?.rawCount ?? 0)
        ]);
      }
    }

    pushBubbles(dynamicsData, cohortName ?? '');
    if (controlDynamicsData && controlCohortName) {
      pushBubbles(controlDynamicsData, controlCohortName);
    }

    XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(rows), 'Clone Sizes (Bubbles)');
  }

  // ─── Sheet 3: Isotype ─────────────────────────────────────────────
  if (isotypeTiles.length > 0 || (controlIsotypeTiles && controlIsotypeTiles.length > 0)) {
    const headers = [
      ...(hasCohort ? ['Cohort'] : []),
      'Clone Rank', 'Clone ID', 'Lineage ID', 'CDR3 Amino Acid', 'V Gene', 'J Gene',
      'Status', 'Total Raw Count', 'Overall Mean SHM', 'Patient Count',
      ...isotypeTimepointLabels.flatMap(tp => [
        `${tp} Dominant Isotype`, `${tp} Seq Count`, `${tp} Mean SHM`,
        ...isoTypes.map(i => `${tp} ${i} Count`)
      ])
    ];
    const rows: any[][] = [headers];

    function pushTiles(entries: IsotypeTileEntry[], cName: string, labels: string[]) {
      for (const e of entries) {
        const tileMap = new Map(e.tiles.map(t => [t.timepointLabel, t]));
        rows.push([
          ...(hasCohort ? [cName] : []),
          e.cloneLabel, e.cloneId, e.lineageId ?? '',
          e.cdr3Aa, e.vGene, e.jGene, e.status, e.totalRawCount,
          Number(e.meanSHM.toFixed(2)), e.patientCount,
          ...labels.flatMap(tp => {
            const t = tileMap.get(tp);
            if (!t) return ['', 0, '', ...isoTypes.map(() => 0)];
            return [
              t.dominantIsotype ?? '', t.seqCount, Number(t.meanSHM.toFixed(2)),
              ...isoTypes.map(i => t.isotypeBreakdown[i] ?? 0)
            ];
          })
        ]);
      }
    }

    pushTiles(isotypeTiles, cohortName ?? '', isotypeTimepointLabels);
    if (controlIsotypeTiles && controlCohortName && controlIsotypeTimepointLabels) {
      pushTiles(controlIsotypeTiles, controlCohortName, controlIsotypeTimepointLabels);
    }

    XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(rows), 'Isotype');
  }

  return wb;
}

// ---------------------------------------------------------------------------
// 5. COVID Database Matching Export (XLSX, 2 sheets)
// ---------------------------------------------------------------------------

export interface CovidMatchExportParams {
  covidData: CovidMatchData;
  cohortName?: string;
  controlCovidData?: CovidMatchData | null;
  controlCohortName?: string;
}

/**
 * Build an XLSX workbook with two sheets:
 *   1. Clone Summary  – one row per analyzed clone with match counts & top match
 *   2. All Matches    – one row per VH/CDR3 match with full antibody details
 */
export function covidMatchWorkbook(params: CovidMatchExportParams): XLSX.WorkBook {
  const { covidData, cohortName, controlCovidData, controlCohortName } = params;
  const wb = XLSX.utils.book_new();
  const hasCohort = !!cohortName && !!controlCovidData;

  // ─── Sheet 1: Clone Summary ────────────────────────────────────────
  {
    const headers = [
      ...(hasCohort ? ['Cohort'] : []),
      'Clone ID', 'Clone Size', 'CDR3 AA (IMGT)', 'CDR3 AA (AIRR)', 'VH AA',
      'V Gene', 'J Gene', 'Files',
      'VH Matches', 'CDR3 Matches', 'Has High VH Match', 'Has High CDR3 Match',
      'Best VH Match Antibody', 'Best VH Match Identity %',
      'Best CDR3 Match Antibody', 'Best CDR3 Match Identity %'
    ];
    const rows: any[][] = [headers];

    function pushClones(data: CovidMatchData, cName: string) {
      for (const c of data.top_clones) {
        const bestVH = c.vh_matches.length > 0
          ? c.vh_matches.reduce((a, b) => a.identity > b.identity ? a : b)
          : null;
        const bestCDR3 = c.cdr3_matches.length > 0
          ? c.cdr3_matches.reduce((a, b) => a.identity > b.identity ? a : b)
          : null;
        rows.push([
          ...(hasCohort ? [cName] : []),
          c.clone_id, c.size, c.cdr3_aa, c.cdr3_aa_raw, c.vh_aa,
          c.v_gene, c.j_gene, c.files.join('; '),
          c.vh_matches.length, c.cdr3_matches.length,
          c.has_high_vh_match ? 'Yes' : 'No',
          c.has_high_cdr3_match ? 'Yes' : 'No',
          bestVH?.antibody_name ?? '', bestVH ? Number((bestVH.identity * 100).toFixed(1)) : '',
          bestCDR3?.antibody_name ?? '', bestCDR3 ? Number((bestCDR3.identity * 100).toFixed(1)) : ''
        ]);
      }
    }

    pushClones(covidData, cohortName ?? '');
    if (controlCovidData && controlCohortName) {
      pushClones(controlCovidData, controlCohortName);
    }

    XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(rows), 'Clone Summary');
  }

  // ─── Sheet 2: All Matches (detailed) ──────────────────────────────
  {
    const headers = [
      ...(hasCohort ? ['Cohort'] : []),
      'Clone ID', 'Clone Size', 'Match Type',
      'Antibody Name', 'Identity %',
      'Binds To', 'Neutralizes', 'Origin', 'Antibody Type',
      'DB V Gene', 'DB J Gene',
      'Query CDR3 AA', 'Clone V Gene', 'Clone J Gene'
    ];
    const rows: any[][] = [headers];

    function pushMatches(data: CovidMatchData, cName: string) {
      for (const c of data.top_clones) {
        for (const m of c.vh_matches) {
          rows.push([
            ...(hasCohort ? [cName] : []),
            c.clone_id, c.size, 'VH',
            m.antibody_name, Number((m.identity * 100).toFixed(1)),
            m.db_info.binds_to, m.db_info.neutralizes, m.db_info.origin, m.db_info.ab_or_nb,
            m.db_info.v_gene, m.db_info.j_gene,
            c.cdr3_aa, c.v_gene, c.j_gene
          ]);
        }
        for (const m of c.cdr3_matches) {
          rows.push([
            ...(hasCohort ? [cName] : []),
            c.clone_id, c.size, 'CDR3',
            m.antibody_name, Number((m.identity * 100).toFixed(1)),
            m.db_info.binds_to, m.db_info.neutralizes, m.db_info.origin, m.db_info.ab_or_nb,
            m.db_info.v_gene, m.db_info.j_gene,
            c.cdr3_aa, c.v_gene, c.j_gene
          ]);
        }
      }
    }

    pushMatches(covidData, cohortName ?? '');
    if (controlCovidData && controlCohortName) {
      pushMatches(controlCovidData, controlCohortName);
    }

    XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(rows), 'All Matches');
  }

  return wb;
}
