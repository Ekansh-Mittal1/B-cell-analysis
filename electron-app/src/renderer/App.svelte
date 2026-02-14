<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { currentView, analysisState, resultsState, wizardState, processSequenceResults, processDlSequenceResults, addLog, setProgress, saveSession, getSessions } from './lib/stores/app';
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
      analysisState.update(s => ({ ...s, isRunning: true, isSessionLoad: true }));
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
              fileIdMapping: {}
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
          console.log('[App] Received result event:', data);
          if (data.artifact === 'sequences' && data.data) {
            processSequenceResults(data.data);
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
        })
      );
      
      console.log('[App] About to register threshold request listener...');
      const thresholdCleanup = window.electronAPI.onThresholdRequest((data) => {
        console.log('[App] ========================================');
        console.log('[App] THRESHOLD REQUEST CALLBACK FIRED!');
        console.log('[App] Threshold request received in callback:', data);
        console.log('[App] Current thresholdRequest state before update:', $analysisState.thresholdRequest);
        console.log('[App] Calculated value:', data.calculated);
        console.log('[App] ========================================');
        
        analysisState.update(s => {
          console.log('[App] Inside update function, old thresholdRequest:', s.thresholdRequest);
          const newState = {
            ...s,
            thresholdRequest: data.calculated
          };
          console.log('[App] New state:', newState);
          return newState;
        });
        
        // Force a check after update
        setTimeout(() => {
          console.log('[App] After state update, thresholdRequest is now:', $analysisState.thresholdRequest);
        }, 100);
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
            error: data.error || null
          }));
          
          if (data.success && !wasSessionLoad) {
            currentView.set('results');
            // Save session for history / restore after sleep
            const outputDir = $resultsState.outputDir;
            if (outputDir) {
              const dirName = outputDir.split('/').pop() || 'Untitled';
              saveSession({
                name: dirName,
                outputDir,
                date: new Date().toISOString(),
                fileCount: lastFileCount || Object.keys($resultsState.fileIdMapping).length,
                fastaDir: lastFastaDir || $wizardState.fastaDir || ''
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
      
      // Attempt restore if we have persisted output dir (e.g. after sleep/minimize reload)
      tryRestoreFromStorage();
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
  
  function handleThresholdConfirm(value: number) {
    console.log('[App] handleThresholdConfirm called with value:', value);
    if (window.electronAPI) {
      console.log('[App] Sending threshold response via electronAPI');
      window.electronAPI.sendThresholdResponse(value);
    } else {
      console.error('[App] electronAPI not available!');
    }
    analysisState.update(s => ({
      ...s,
      thresholdRequest: null
    }));
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
    // Use the calculated value
    const calculated = $analysisState.thresholdRequest;
    console.log('[App] handleThresholdCancel called, using calculated:', calculated);
    if (calculated !== null && window.electronAPI) {
      console.log('[App] Sending threshold response (cancel) via electronAPI');
      window.electronAPI.sendThresholdResponse(calculated);
    } else {
      console.error('[App] electronAPI not available or calculated is null!');
    }
    analysisState.update(s => ({
      ...s,
      thresholdRequest: null
    }));
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
            on:click={() => currentView.set('wizard')}
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
      calculatedValue={$analysisState.thresholdRequest}
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

