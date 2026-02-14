/**
 * Application State Stores
 * 
 * Svelte stores for managing application state
 */

import { writable, derived, type Writable, type Readable } from 'svelte/store';

// ============================================
// Types
// ============================================

export type AppView = 'wizard' | 'results';
export type WizardStep = 1 | 2 | 3;

export interface WizardState {
  step: WizardStep;
  fastaDir: string | null;
  fastaFiles: string[];
  fastaCount: number;
  cleanFasta: boolean;
  databaseType: 'IMGT' | 'Custom';
  customDatabaseV: string | null;
  customDatabaseD: string | null;
  customDatabaseJ: string | null;
  cloneMode: 'allele' | 'gene';  // V/J gene matching: allele (strict) or gene (permissive)
  linkageMethod: 'single' | 'average' | 'complete';  // Clustering linkage method
  runCovidMatching: boolean;  // Enable COVID database matching
  covAbdabPath: string | null;  // Path to CoV-AbDab CSV file
}

export interface AnalysisProgress {
  stage: string;
  percent: number;
  message: string;
}

export interface LogEntry {
  level: 'info' | 'warn' | 'error' | 'debug';
  message: string;
  timestamp: Date;
}

export interface SequenceData {
  id: string;
  name: string;
  file?: string;
  v_gene: string | null;
  d_gene: string | null;
  j_gene: string | null;
  v_locus: string | null;
  d_locus: string | null;
  j_locus: string | null;
  cdr3_dna: string | null;
  cdr3_peptide: string | null;
  somatic_mutations: number | null;
  isotype: string | null;
  clone_id?: number;
  clone_count?: number;
  productive?: boolean;
  dna_sequence?: string | null;  // Full DNA sequence for debugging
  aa_sequence?: string | null;   // Translated AA sequence (V-J region) for debugging
}

export interface FileGroup {
  filename: string;
  sequences: SequenceData[];
  cloneGroups: CloneGroup[];
  expanded: boolean;
}

export interface PublicCloneResult {
  id: string;
  cdr3_aa: string;
  cdr3_dna: string;
  v_gene: string;
  j_gene: string;
  sequence_count: number;
  patient_count: number;
  patients: string[];
  sequences: string[];
  /** Patient filename -> list of sequence IDs (for per-patient counts) */
  sequences_by_patient?: Record<string, string[]>;
  unique_cdr3_variants: number;
  avg_intra_cluster_similarity: number;
}

export interface VisualizationData {
  heatmap: {
    clones: string[];
    patients: string[];
    matrix: number[][];
    frequencies: number[][];
  };
  chord: {
    nodes: string[];
    links: Array<{source: string; target: string; value: number}>;
  };
  upset: {
    sets: Record<string, number>;
    intersections: Array<{sets: string[]; size: number}>;
  };
  network: {
    nodes: Array<{id: string; type: 'clone' | 'patient'; label: string}>;
    edges: Array<{source: string; target: string; count: number}>;
  };
}

export interface CovidMatchAlignment {
  query_aligned: string;
  reference_aligned: string;
  match_string: string;
  identity: number;
  matches: number;
  length: number;
}

export interface CovidMatchResult {
  antibody_name: string;
  identity: number;
  alignment: CovidMatchAlignment;
  db_info: {
    binds_to: string;
    neutralizes: string;
    v_gene: string;
    j_gene: string;
    origin: string;
    ab_or_nb: string;
  };
}

export interface CovidCloneData {
  clone_id: number;
  size: number;
  cdr3_aa: string;  // IMGT CDR3 format (trimmed)
  cdr3_aa_raw: string;  // Original AIRR Junction format
  vh_aa: string;  // Translated from DNA
  v_gene: string;
  j_gene: string;
  files: string[];
  vh_matches: CovidMatchResult[];
  cdr3_matches: CovidMatchResult[];
  has_high_vh_match: boolean;
  has_high_cdr3_match: boolean;
}

export interface CovidMatchData {
  top_clones: CovidCloneData[];
  stats: {
    total_clones_analyzed: number;
    clones_with_vh_matches: number;
    clones_with_cdr3_matches: number;
    clones_with_high_matches: number;
    database_size: number;
  };
}

export interface PublicClonesData {
  public_clones: PublicCloneResult[];
  top_x: PublicCloneResult[];
  stats: {
    total_public_clones: number;
    total_sequences_in_public_clones: number;
    max_patient_sharing: number;
    total_patients: number;
    clustering_mode: string;
    similarity_threshold: number;
    top_n_displayed: number;
  };
  method: string;
  visualizations: VisualizationData;
}

export interface TreeMetadata {
  path: string;
  clone_id: number | null;
  clone_size: number;
}

export interface ResultsState {
  sequences: SequenceData[];
  fileGroups: FileGroup[];
  dlSequences: SequenceData[];
  dlFileGroups: FileGroup[];
  selectedSequenceId: string | null;
  selectedDlSequenceId: string | null;
  treeImages: string[];
  treeMetadata: TreeMetadata[];
  outputDir: string | null;
  /** Mapping of numeric file ID (e.g. "1001") to original filename */
  fileIdMapping: Record<string, string>;
  publicClonesData: PublicClonesData | null;
  isAnalyzingPublicClones: boolean;
  covidMatchData: CovidMatchData | null;
  isAnalyzingCovidMatching: boolean;
}

export interface AnalysisState {
  isRunning: boolean;
  isSessionLoad: boolean;  // True when loading a previous session (not a real pipeline run)
  progress: AnalysisProgress | null;
  logs: LogEntry[];
  error: string | null;
  thresholdRequest: number | null;
}

// ============================================
// Session History
// ============================================

export interface SessionEntry {
  id: string;
  name: string;
  outputDir: string;
  date: string;        // ISO 8601 timestamp
  fileCount: number;
  fastaDir: string;
}

const SESSIONS_KEY = 'bcr_sessions';

function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
}

export function getSessions(): SessionEntry[] {
  try {
    const raw = localStorage.getItem(SESSIONS_KEY);
    if (!raw) return [];
    const sessions: SessionEntry[] = JSON.parse(raw);
    // Sort by date descending (most recent first)
    return sessions.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
  } catch {
    return [];
  }
}

export function saveSession(entry: Omit<SessionEntry, 'id'>): SessionEntry {
  const sessions = getSessions();
  const newEntry: SessionEntry = {
    id: generateId(),
    ...entry
  };
  sessions.unshift(newEntry);
  localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions));
  return newEntry;
}

export function deleteSession(id: string): void {
  const sessions = getSessions().filter(s => s.id !== id);
  localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions));
}

export function renameSession(id: string, newName: string): void {
  const sessions = getSessions();
  const session = sessions.find(s => s.id === id);
  if (session) {
    session.name = newName;
    localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions));
  }
}


// ============================================
// Stores
// ============================================

// Current view
export const currentView: Writable<AppView> = writable('wizard');

// Wizard state
export const wizardState: Writable<WizardState> = writable({
  step: 1,
  fastaDir: null,
  fastaFiles: [],
  fastaCount: 0,
  cleanFasta: false,
  databaseType: 'IMGT',
  customDatabaseV: null,
  customDatabaseD: null,
  customDatabaseJ: null,
  cloneMode: 'allele',  // Default: strict allele matching
  linkageMethod: 'average',  // Default: average linkage
  runCovidMatching: false,
  covAbdabPath: null
});

// Analysis state
export const analysisState: Writable<AnalysisState> = writable({
  isRunning: false,
  isSessionLoad: false,
  progress: null,
  logs: [],
  error: null,
  thresholdRequest: null
});

// Results state
export const resultsState: Writable<ResultsState> = writable({
  sequences: [],
  fileGroups: [],
  dlSequences: [],
  dlFileGroups: [],
  selectedSequenceId: null,
  selectedDlSequenceId: null,
  treeImages: [],
  treeMetadata: [],
  outputDir: null,
  fileIdMapping: {},
  publicClonesData: null,
  isAnalyzingPublicClones: false,
  covidMatchData: null,
  isAnalyzingCovidMatching: false
});


// ============================================
// Derived Stores
// ============================================

// Can proceed to next wizard step
export const canProceedStep1: Readable<boolean> = derived(
  wizardState,
  ($state) => $state.fastaDir !== null && $state.fastaCount > 0
);

export const canProceedStep2: Readable<boolean> = derived(
  wizardState,
  ($state) => {
    if ($state.databaseType === 'IMGT') return true;
    return (
      $state.customDatabaseV !== null &&
      $state.customDatabaseD !== null &&
      $state.customDatabaseJ !== null
    );
  }
);

// Selected sequence
export const selectedSequence: Readable<SequenceData | null> = derived(
  resultsState,
  ($state) => {
    if (!$state.selectedSequenceId) return null;
    return $state.sequences.find(s => s.id === $state.selectedSequenceId) || null;
  }
);

// Selected DL sequence
export const selectedDlSequence: Readable<SequenceData | null> = derived(
  resultsState,
  ($state) => {
    if (!$state.selectedDlSequenceId) return null;
    return $state.dlSequences.find(s => s.id === $state.selectedDlSequenceId) || null;
  }
);

// Search filter for sequences
export const sequenceSearchQuery: Writable<string> = writable('');

// Helper function to sort sequences by clone size (largest first)
const sortSequencesByClone = (sequences: SequenceData[]): SequenceData[] => {
  return [...sequences].sort((a, b) => {
    // Sequences with clones come first
    const aHasClone = a.clone_id !== undefined && a.clone_id !== null && (a.clone_count ?? 0) > 0;
    const bHasClone = b.clone_id !== undefined && b.clone_id !== null && (b.clone_count ?? 0) > 0;
    
    // If one has a clone and the other doesn't, clone comes first
    if (aHasClone && !bHasClone) return -1;
    if (!aHasClone && bHasClone) return 1;
    
    // If both have clones, sort by clone_count (descending)
    if (aHasClone && bHasClone) {
      const aCount = a.clone_count ?? 0;
      const bCount = b.clone_count ?? 0;
      if (bCount !== aCount) {
        return bCount - aCount; // Descending order
      }
      // If same clone count, sort by clone_id for consistency
      return (a.clone_id ?? 0) - (b.clone_id ?? 0);
    }
    
    // If neither has a clone, maintain original order
    return 0;
  });
};

export const filteredFileGroups: Readable<FileGroup[]> = derived(
  [resultsState, sequenceSearchQuery],
  ([$results, $query]) => {
    const lowerQuery = $query.trim().toLowerCase();
    
    let groups = $results.fileGroups;
    
    // Apply search filter if query exists
    if (lowerQuery) {
      groups = groups
        .map(group => ({
          ...group,
          sequences: group.sequences.filter(seq =>
            seq.name.toLowerCase().includes(lowerQuery) ||
            seq.v_gene?.toLowerCase().includes(lowerQuery) ||
            seq.d_gene?.toLowerCase().includes(lowerQuery) ||
            seq.j_gene?.toLowerCase().includes(lowerQuery) ||
            seq.cdr3_peptide?.toLowerCase().includes(lowerQuery)
          )
        }))
        .filter(group => group.sequences.length > 0);
    }
    
    // Sort sequences within each group by clone size
    return groups.map(group => ({
      ...group,
      sequences: sortSequencesByClone(group.sequences)
    }));
  }
);

// Filtered DL file groups (same logic as traditional clustering)
export const filteredDlFileGroups: Readable<FileGroup[]> = derived(
  [resultsState, sequenceSearchQuery],
  ([$results, $query]) => {
    const lowerQuery = $query.trim().toLowerCase();
    
    let groups = $results.dlFileGroups;
    
    // Apply search filter if query exists
    if (lowerQuery) {
      groups = groups
        .map(group => ({
          ...group,
          sequences: group.sequences.filter(seq =>
            seq.name.toLowerCase().includes(lowerQuery) ||
            seq.v_gene?.toLowerCase().includes(lowerQuery) ||
            seq.d_gene?.toLowerCase().includes(lowerQuery) ||
            seq.j_gene?.toLowerCase().includes(lowerQuery) ||
            seq.cdr3_peptide?.toLowerCase().includes(lowerQuery)
          )
        }))
        .filter(group => group.sequences.length > 0);
    }
    
    // Sort sequences within each group by clone size
    return groups.map(group => ({
      ...group,
      sequences: sortSequencesByClone(group.sequences)
    }));
  }
);


// ============================================
// Actions
// ============================================

export function resetWizard(): void {
  wizardState.set({
    step: 1,
    fastaDir: null,
    fastaFiles: [],
    fastaCount: 0,
    cleanFasta: false,
    databaseType: 'IMGT',
    customDatabaseV: null,
    customDatabaseD: null,
    customDatabaseJ: null,
    cloneMode: 'allele',
    linkageMethod: 'average',
    runCovidMatching: false,
    covAbdabPath: null
  });
}

export function resetAnalysis(): void {
  analysisState.set({
    isRunning: false,
    isSessionLoad: false,
    progress: null,
    logs: [],
    error: null,
    thresholdRequest: null
  });
}

export function addLog(level: LogEntry['level'], message: string): void {
  analysisState.update(state => ({
    ...state,
    logs: [...state.logs, { level, message, timestamp: new Date() }]
  }));
}

export function setProgress(progress: AnalysisProgress): void {
  analysisState.update(state => ({
    ...state,
    progress
  }));
}

// Helper function to group sequences by clone within a file
function groupSequencesByClone(sequences: SequenceData[]): CloneGroup[] {
  const cloneMap = new Map<number | null, SequenceData[]>();
  
  for (const seq of sequences) {
    const cloneId = seq.clone_id !== undefined ? seq.clone_id : null;
    if (!cloneMap.has(cloneId)) {
      cloneMap.set(cloneId, []);
    }
    cloneMap.get(cloneId)!.push(seq);
  }
  
  // Separate into categories
  const multiSeqClones: CloneGroup[] = [];  // Clones with ≥2 sequences
  const singletonSeqs: SequenceData[] = [];  // Clones with 1 sequence
  const noCloneSeqs: SequenceData[] = [];    // Sequences without clone_id
  
  for (const [cloneId, seqs] of cloneMap.entries()) {
    if (cloneId === null) {
      // No clone ID assigned
      noCloneSeqs.push(...seqs);
    } else if (seqs.length === 1) {
      // Singleton clone
      singletonSeqs.push(...seqs);
    } else {
      // Multi-sequence clone
      multiSeqClones.push({
        cloneId,
        sequences: seqs,
        expanded: false,  // Collapsed by default
        size: seqs.length
      });
    }
  }
  
  // Sort multi-sequence clones by size (largest first)
  multiSeqClones.sort((a, b) => b.size - a.size);
  
  // Build final groups array
  const groups: CloneGroup[] = [...multiSeqClones];
  
  // Add "Singletons" folder if there are any
  if (singletonSeqs.length > 0) {
    groups.push({
      cloneId: -1,  // Special ID for Singletons folder
      sequences: singletonSeqs,
      expanded: false,  // Collapsed by default
      size: singletonSeqs.length
    });
  }
  
  // Add "No Clone" folder if there are any
  if (noCloneSeqs.length > 0) {
    groups.push({
      cloneId: null,
      sequences: noCloneSeqs,
      expanded: false,  // Collapsed by default
      size: noCloneSeqs.length
    });
  }
  
  return groups;
}

export function processSequenceResults(data: {
  sequences: SequenceData[];
  file_groups: Record<string, SequenceData[]>;
  output_dir?: string;
  file_id_mapping?: Record<string, string>;
}): void {
  const fileGroups: FileGroup[] = Object.entries(data.file_groups).map(([filename, sequences]) => ({
    filename,
    sequences,
    cloneGroups: groupSequencesByClone(sequences),
    expanded: true
  }));
  
  resultsState.update(state => ({
    ...state,
    sequences: data.sequences,
    fileGroups,
    ...(data.output_dir != null && { outputDir: data.output_dir }),
    ...(data.file_id_mapping != null && { fileIdMapping: data.file_id_mapping })
  }));
}

export function processDlSequenceResults(data: { sequences: SequenceData[]; file_groups: Record<string, SequenceData[]> }): void {
  const fileGroups: FileGroup[] = Object.entries(data.file_groups).map(([filename, sequences]) => ({
    filename,
    sequences,
    expanded: true
  }));
  
  resultsState.update(state => ({
    ...state,
    dlSequences: data.sequences,
    dlFileGroups: fileGroups
  }));
}

export function toggleFileGroup(filename: string): void {
  resultsState.update(state => ({
    ...state,
    fileGroups: state.fileGroups.map(group =>
      group.filename === filename
        ? { ...group, expanded: !group.expanded }
        : group
    )
  }));
}

export function selectSequence(id: string): void {
  resultsState.update(state => ({
    ...state,
    selectedSequenceId: id
  }));
}

export function selectDlSequence(id: string): void {
  resultsState.update(state => ({
    ...state,
    selectedDlSequenceId: id
  }));
}

export function toggleDlFileGroup(filename: string): void {
  resultsState.update(state => ({
    ...state,
    dlFileGroups: state.dlFileGroups.map(group =>
      group.filename === filename
        ? { ...group, expanded: !group.expanded }
        : group
    )
  }));
}

export function toggleCloneGroup(filename: string, cloneId: number | null): void {
  resultsState.update(state => ({
    ...state,
    fileGroups: state.fileGroups.map(fileGroup => {
      if (fileGroup.filename === filename) {
        return {
          ...fileGroup,
          cloneGroups: fileGroup.cloneGroups.map(cloneGroup => {
            if (cloneGroup.cloneId === cloneId) {
              return {
                ...cloneGroup,
                expanded: !cloneGroup.expanded
              };
            }
            return cloneGroup;
          })
        };
      }
      return fileGroup;
    })
  }));
}

// Public clone actions
export const publicClonesActions = {
  startAnalysis() {
    resultsState.update(s => ({ ...s, isAnalyzingPublicClones: true }));
  },
  
  updateResults(data: PublicClonesData) {
    resultsState.update(s => ({
      ...s,
      publicClonesData: data,
      isAnalyzingPublicClones: false
    }));
  },
  
  clearResults() {
    resultsState.update(s => ({ ...s, publicClonesData: null }));
  }
};

