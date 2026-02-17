<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { get } from 'svelte/store';
  import { currentView, analysisState, resultsState, wizardState, studyDesign, processSequenceResults, processDlSequenceResults, addLog, setProgress, saveSession, getSessions, resetWizard, saveStudyDesignImmediate } from './lib/stores/app';
  import Wizard from './routes/wizard/Wizard.svelte';
  import Results from './routes/results/Results.svelte';
  import ThresholdDialog from './lib/components/ThresholdDialog.svelte';
  import SessionSidebar from './lib/components/SessionSidebar.svelte';
  
  let sessionSidebar: SessionSidebar;
  
  // Track fasta_dir from latest result so we can save it to session history
  let lastFastaDir = '';
  let lastFileCount = 0;
  
  
  // Event listener cleanup functions
  let cleanupFns: (() => void)[] = [];
  
  /** Migrate old single-key persistence into the new sessions array (one-time) */
  function migrateOldPersistence() {
    const OLD_KEY = 'bcr_last_output_dir';
    const oldDir = localStorage.getItem(OLD_KEY);
    if (!oldDir) return;
    // Only migrate if there isn't already a session for this dir
    const existing = getSessions();
    if (existing.some(s => s.outputDir === oldDir)) {
      localStorage.removeItem(OLD_KEY);
      return;
    }
    const dirName = oldDir.split('/').pop() || 'Untitled';
    saveSession({
      name: dirName,
      outputDir: oldDir,
      date: new Date().toISOString(),
      fileCount: 0,   // unknown from old key
      fastaDir: ''
    });
    localStorage.removeItem(OLD_KEY);
    console.log('[App] Migrated old persistence key to session:', dirName);
  }
  
  async function tryRestoreFromStorage() {
    try {
      const sessions = getSessions();
      if (sessions.length === 0 || !window.electronAPI) return;
      
      // Try the most recent session
      const latest = sessions[0];
      const markerPath = latest.outputDir + '/combined.fasta';
      const exists = await window.electronAPI.fileExists(markerPath);
      if (!exists) {
        console.log('[App] Most recent session output missing, skipping auto-restore');
        return;
      }
      
      console.log('[App] Restoring results from', latest.outputDir);
      if (sessionSidebar) sessionSidebar.collapse();
      analysisState.update(s => ({
        ...s,
        isRunning: true,
        isSessionLoad: true,
        pendingLoadOutputDir: latest.outputDir
      }));
      currentView.set('results');
      
      await window.electronAPI.loadResults(latest.outputDir);
      analysisState.update(s => ({ ...s, isRunning: false }));
    } catch (e) {
      console.warn('[App] Restore failed:', e);
      analysisState.update(s => ({ ...s, isRunning: false }));
    }
  }
  
  onMount(() => {
    // Migrate old single-key persistence to session array (one-time)
    migrateOldPersistence();
    
    // Debug: Check if electronAPI is available
    console.log('[App] App mounted, checking electronAPI...');
    console.log('[App] window.electronAPI:', window.electronAPI);
    console.log('[App] typeof window.electronAPI:', typeof window.electronAPI);
    
    // Set up pipeline event listeners
    if (window.electronAPI) {
      console.log('[App] Setting up event listeners...');
      console.log('[App] onThresholdRequest available:', typeof window.electronAPI.onThresholdRequest);
      
      cleanupFns.push(
        window.electronAPI.onPipelineProgress((data) => {
          console.log('[App] Received progress event:', data);
          setProgress(data);
          
          // Clear old tree data and file mapping when a new analysis starts
          if (data.stage === 'fasta' || data.stage === 'setup') {
            console.log('[App] New analysis starting - clearing old tree data');
            resultsState.update(s => ({
              ...s,
              treeImages: [],
              treeMetadata: [],
              fileIdMapping: {},
              timepointMapping: {}
            }));
            if (sessionSidebar) sessionSidebar.clearActive();
          }
        })
      );
      
      cleanupFns.push(
        window.electronAPI.onPipelineLog((data) => {
          console.log('[App] Received log event:', data);
          addLog(data.level as any, data.message);
        })
      );
      
      cleanupFns.push(
        window.electronAPI.onPipelineResult((data) => {
          console.log('[App] Received result event:', data.artifact, data.data ? '(has data)' : '(no data)');
          if (data.artifact === 'sequences' && data.data) {
            // During session load: only accept results for the session we're loading
            const pending = $analysisState.pendingLoadOutputDir;
            if (pending) {
              const received = (data.data.output_dir || '').replace(/\/$/, '');
              const expected = pending.replace(/\/$/, '');
              if (received && expected && received !== expected) {
                console.log('[App] Ignoring stale sequences result for', received, '- expected', expected);
                return;
              }
            }
            try {
              processSequenceResults(data.data);
              console.log('[App] processSequenceResults OK, sequences:', data.data.sequences?.length, 'file_groups:', Object.keys(data.data.file_groups || {}).length);
            } catch (e) {
              console.error('[App] processSequenceResults failed:', e);
            }
            // Capture output directory
            if (data.data.output_dir) {
              console.log('[App] Storing output directory:', data.data.output_dir);
              resultsState.update(s => ({
                ...s,
                outputDir: data.data.output_dir
              }));
            }
            // Track fasta_dir and file count for session history
            if (data.data.fasta_dir) {
              lastFastaDir = data.data.fasta_dir;
            }
            if (data.data.file_groups) {
              lastFileCount = Object.keys(data.data.file_groups).length;
            }
          }
          if (data.artifact === 'dl_sequences' && data.data) {
            processDlSequenceResults(data.data);
          }
          if (data.artifact === 'tree_images' && data.data?.images) {
            resultsState.update(s => ({
              ...s,
              treeImages: data.data.images,
              treeMetadata: data.data.tree_metadata || []
            }));
          }
          if (data.artifact === 'covid_matches' && data.data) {
            console.log('[App] Received COVID matching results:', data.data);
            resultsState.update(s => ({
              ...s,
              covidMatchData: data.data,
              isAnalyzingCovidMatching: false
            }));
          }
          if (data.artifact === 'timepoint_mapping' && data.data) {
            console.log('[App] Received timepoint_mapping artifact with', Object.keys(data.data).length, 'entries');
            console.log('[App] Sample entries:', Object.entries(data.data).slice(0, 3));
            resultsState.update(s => ({
              ...s,
              timepointMapping: data.data
            }));
            console.log('[App] timepointMapping stored in resultsState');
          }
          if (data.artifact === 'study_design' && data.data) {
            const design = data.data;
            if (design && (design.groups?.length > 0 || (design.unassigned && design.unassigned.length >= 0))) {
              studyDesign.set({
                groups: design.groups || [],
                unassigned: design.unassigned || []
              });
            }
          }
        })
      );
      
      console.log('[App] About to register threshold request listener...');
      const thresholdCleanup = window.electronAPI.onThresholdRequest((data) => {
        console.log('[App] THRESHOLD REQUEST received:', data);
        
        // Support both formats:
        //   Old: { calculated: number }
        //   New: { timepoint_thresholds: [{label, calculated}, ...] }
        analysisState.update(s => {
          let thresholdValue: number | { label: string; calculated: number }[];
          if (data.timepoint_thresholds && Array.isArray(data.timepoint_thresholds)) {
            thresholdValue = data.timepoint_thresholds;
            console.log('[App] Multi-timepoint thresholds:', thresholdValue);
          } else {
            thresholdValue = data.calculated;
            console.log('[App] Single threshold:', thresholdValue);
          }
          return { ...s, thresholdRequest: thresholdValue };
        });
      });
      console.log('[App] Threshold request listener registered successfully');
      console.log('[App] Cleanup function type:', typeof thresholdCleanup);
      cleanupFns.push(thresholdCleanup);
      
      cleanupFns.push(
        window.electronAPI.onPipelineComplete((data) => {
          const wasSessionLoad = $analysisState.isSessionLoad;
          console.log('[App] Received complete event:', data, 'isSessionLoad:', wasSessionLoad);
          analysisState.update(s => ({
            ...s,
            isRunning: false,
            isSessionLoad: false,
            pendingLoadOutputDir: null,
            error: data.error || null
          }));
          
          if (data.success && !wasSessionLoad) {
            currentView.set('results');
            
            // Populate StudyDesign from wizard timepoints (single group = the study)
            // Use setTimeout to ensure timepoint_mapping artifact has been processed
            setTimeout(() => {
              const wizard = get(wizardState);
              const results = get(resultsState);
              
              if (wizard.timepoints.length > 0) {
                const timepointMapping = results.timepointMapping || {};
                const tpLabels = wizard.timepoints.map(tp => tp.label);
                
                console.log('[App] Populating study design with', tpLabels.length, 'timepoints');
                console.log('[App] timepointMapping has', Object.keys(timepointMapping).length, 'entries');
                
                // Build a single group (the study) with timepoints
                const group = {
                  id: Math.random().toString(36).slice(2, 8),
                  name: wizard.studyName || 'Study',
                  color: '#4F46E5',
                  timepoints: tpLabels.map((label, idx) => {
                    const filesForTp = Object.entries(timepointMapping)
                      .filter(([, entry]) => entry.timepoint === label)
                      .map(([stagedFile]) => stagedFile);
                    console.log('[App] Timepoint', label, 'has', filesForTp.length, 'files');
                    return { id: Math.random().toString(36).slice(2, 8), label, order: idx, files: filesForTp };
                  })
                };
                
                const newDesign = {
                  groups: [group],
                  unassigned: [] as string[]
                };
                console.log('[App] Setting study design:', newDesign);
                studyDesign.set(newDesign);
                saveStudyDesignImmediate(newDesign);
              }
            }, 100);
            
            // Save session for history / restore after sleep
            const outputDir = $resultsState.outputDir;
            if (outputDir) {
              const dirName = outputDir.split('/').pop() || 'Untitled';
              const design = $studyDesign;
              saveSession({
                name: dirName,
                outputDir,
                date: new Date().toISOString(),
                fileCount: lastFileCount || Object.keys($resultsState.fileIdMapping).length,
                fastaDir: lastFastaDir || '',
                studyName: $wizardState.studyName || '',
                ...(design?.groups?.length ? { studyDesign: design } : {})
              });
              // Refresh sidebar and highlight the new session
              if (sessionSidebar) {
                sessionSidebar.refresh();
              }
            }
          }
        })
      );
      
      cleanupFns.push(
        window.electronAPI.onPipelineError((data) => {
          console.log('[App] Received error event:', data);
          analysisState.update(s => ({
            ...s,
            isRunning: false,
            error: data.message
          }));
        })
      );
      
      console.log('[App] All event listeners set up successfully');
      console.log('[App] Total cleanup functions:', cleanupFns.length);
      
      // Disabled: auto-restore was racing with manual session selection and could load wrong session.
      // User can select a session from history sidebar instead.
      // tryRestoreFromStorage();
    } else {
      console.error('[App] electronAPI not available in onMount!');
    }
  });
  
  onDestroy(() => {
    cleanupFns.forEach(fn => fn());
  });
  
  // Reactive statement to track threshold request changes
  $: {
    console.log('[App] Reactive statement: thresholdRequest =', $analysisState.thresholdRequest);
    if ($analysisState.thresholdRequest !== null) {
      console.log('[App] ✓ thresholdRequest is NOT null, dialog should show!', $analysisState.thresholdRequest);
    } else {
      console.log('[App] ✗ thresholdRequest is null, dialog will not show');
    }
  }
  
  function handleThresholdConfirm(value: number | Record<string, number>) {
    console.log('[App] handleThresholdConfirm called with value:', value);
    if (window.electronAPI) {
      if (typeof value === 'object' && value !== null) {
        // Multi-timepoint: send {thresholds: {T1: 0.12, T2: 0.15, ...}}
        window.electronAPI.sendThresholdResponse(value);
      } else {
        // Single value (legacy)
        window.electronAPI.sendThresholdResponse(value);
      }
    }
    analysisState.update(s => ({ ...s, thresholdRequest: null }));
  }
  
  let showFileIdTooltip = false;
  
  $: if ($currentView === 'wizard') {
    showFileIdTooltip = false;
  }
  
  function toggleFileIdTooltip() {
    showFileIdTooltip = !showFileIdTooltip;
  }
  
  let infoButtonWrapper: HTMLDivElement;
  
  function handleClickOutside(event: MouseEvent) {
    const target = event.target as Node;
    if (showFileIdTooltip && infoButtonWrapper && !infoButtonWrapper.contains(target)) {
      showFileIdTooltip = false;
    }
  }
  
  function handleThresholdCancel() {
    const req = $analysisState.thresholdRequest;
    if (req !== null && window.electronAPI) {
      if (Array.isArray(req)) {
        // Multi-timepoint: send calculated values
        const thresholds: Record<string, number> = {};
        for (const tp of req) {
          thresholds[tp.label] = tp.calculated;
        }
        window.electronAPI.sendThresholdResponse(thresholds);
      } else {
        window.electronAPI.sendThresholdResponse(req);
      }
    }
    analysisState.update(s => ({ ...s, thresholdRequest: null }));
  }
</script>

<svelte:window on:click={handleClickOutside} />
<div class="app-container">
  <!-- Header with drag region for macOS -->
  <header class="app-header">
    <div class="header-content">
      <h1 class="app-title">B-Cell Repertoire Analysis</h1>
      
      <div class="header-actions">
        {#if $currentView === 'results' && Object.keys($resultsState.fileIdMapping).length > 0}
          <div class="info-button-wrapper" role="group" bind:this={infoButtonWrapper}>
            <button 
              class="btn btn-ghost btn-sm" 
              on:click={toggleFileIdTooltip}
              aria-label="File ID mapping"
              aria-expanded={showFileIdTooltip}
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                <circle cx="8" cy="8" r="6"/>
                <path d="M8 7v4M8 5v0" stroke-linecap="round"/>
              </svg>
              <span class="info-button-label">File ID mapping</span>
            </button>
            {#if showFileIdTooltip}
              <div class="info-tooltip" role="tooltip">
                <div class="info-tooltip-title">File ID → Filename</div>
                {#each Object.entries($resultsState.fileIdMapping).sort((a, b) => a[0].localeCompare(b[0])) as [id, filename]}
                  <div class="info-tooltip-row"><span class="info-tooltip-id">{id}</span> → {filename}</div>
                {/each}
              </div>
            {/if}
          </div>
        {/if}
        {#if $currentView === 'results'}
          <button 
            class="btn btn-ghost btn-sm"
            on:click={() => { resetWizard(); currentView.set('wizard'); }}
          >
            ← New Analysis
          </button>
        {/if}
      </div>
    </div>
  </header>
  
  <!-- Main content area with session sidebar -->
  <div class="app-body">
    <SessionSidebar bind:this={sessionSidebar} />
    <main class="app-content">
      {#if $currentView === 'wizard'}
        <Wizard />
      {:else}
        <Results />
      {/if}
    </main>
  </div>
  
  <!-- Threshold dialog -->
  {#if $analysisState.thresholdRequest !== null}
    <ThresholdDialog
      calculatedValue={typeof $analysisState.thresholdRequest === 'number' ? $analysisState.thresholdRequest : 0}
      timepointThresholds={Array.isArray($analysisState.thresholdRequest) ? $analysisState.thresholdRequest : []}
      on:confirm={(e) => handleThresholdConfirm(e.detail)}
      on:cancel={handleThresholdCancel}
    />
  {/if}
</div>

<style>
  :global(html, body) {
    height: 100%;
    overflow: hidden;
    margin: 0;
    padding: 0;
  }
  
  :global(#app) {
    height: 100%;
    overflow: hidden;
  }
  
  .app-container {
    height: 100vh;
    display: flex;
    flex-direction: column;
    background: var(--gray-50);
    overflow: hidden;
  }
  
  .app-header {
    height: 52px;
    background: var(--surface-raised);
    border-bottom: 1px solid var(--border-light);
    display: flex;
    align-items: center;
    padding: 0 var(--space-6);
    padding-left: 80px; /* Space for macOS traffic lights */
    -webkit-app-region: drag;
    flex-shrink: 0;
  }
  
  .app-header > * {
    -webkit-app-region: no-drag;
  }
  
  .header-content {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
  }
  
  .header-actions {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    -webkit-app-region: no-drag;
  }
  
  .info-button-wrapper {
    position: relative;
    display: inline-flex;
  }
  
  .info-button-wrapper .btn {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-3);
    border-radius: var(--radius-md);
    color: var(--gray-600);
  }
  
  .info-button-wrapper .btn:hover {
    color: var(--gray-800);
    background: var(--gray-100);
  }
  
  .info-button-label {
    font-size: var(--text-sm);
    white-space: nowrap;
  }
  
  .info-tooltip {
    position: absolute;
    top: 100%;
    right: 0;
    margin-top: var(--space-2);
    padding: var(--space-3);
    background: var(--surface-raised);
    border: 1px solid var(--gray-200);
    border-radius: var(--radius-md);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    font-size: var(--text-xs);
    min-width: 180px;
    max-width: 280px;
    z-index: 1000;
  }
  
  .info-tooltip-title {
    font-weight: var(--font-semibold);
    color: var(--gray-700);
    margin-bottom: var(--space-2);
    padding-bottom: var(--space-2);
    border-bottom: 1px solid var(--gray-200);
  }
  
  .info-tooltip-row {
    padding: var(--space-1) 0;
    color: var(--gray-600);
    word-break: break-all;
  }
  
  .info-tooltip-id {
    font-family: var(--font-mono);
    font-size: 0.9em;
    color: var(--gray-800);
    font-weight: var(--font-medium);
  }
  
  .app-title {
    font-size: var(--text-sm);
    font-weight: var(--font-semibold);
    color: var(--text-primary);
    margin: 0;
  }
  
  .app-body {
    flex: 1;
    display: flex;
    overflow: hidden;
  }

  .app-content {
    flex: 1;
    overflow: hidden;
    display: flex;
    width: 100%;
    margin: 0;
    padding: 0;
  }
</style>

