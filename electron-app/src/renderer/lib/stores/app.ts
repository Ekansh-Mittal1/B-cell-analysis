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
}

export interface FileGroup {
  filename: string;
  sequences: SequenceData[];
  expanded: boolean;
}

export interface ResultsState {
  sequences: SequenceData[];
  fileGroups: FileGroup[];
  selectedSequenceId: string | null;
  treeImages: string[];
  outputDir: string | null;
}

export interface AnalysisState {
  isRunning: boolean;
  progress: AnalysisProgress | null;
  logs: LogEntry[];
  error: string | null;
  thresholdRequest: number | null;
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
  customDatabaseJ: null
});

// Analysis state
export const analysisState: Writable<AnalysisState> = writable({
  isRunning: false,
  progress: null,
  logs: [],
  error: null,
  thresholdRequest: null
});

// Results state
export const resultsState: Writable<ResultsState> = writable({
  sequences: [],
  fileGroups: [],
  selectedSequenceId: null,
  treeImages: [],
  outputDir: null
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

// Search filter for sequences
export const sequenceSearchQuery: Writable<string> = writable('');

export const filteredFileGroups: Readable<FileGroup[]> = derived(
  [resultsState, sequenceSearchQuery],
  ([$results, $query]) => {
    const lowerQuery = $query.trim().toLowerCase();
    
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
    customDatabaseJ: null
  });
}

export function resetAnalysis(): void {
  analysisState.set({
    isRunning: false,
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

export function processSequenceResults(data: { sequences: SequenceData[]; file_groups: Record<string, SequenceData[]> }): void {
  const fileGroups: FileGroup[] = Object.entries(data.file_groups).map(([filename, sequences]) => ({
    filename,
    sequences,
    expanded: true
  }));
  
  resultsState.update(state => ({
    ...state,
    sequences: data.sequences,
    fileGroups
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

