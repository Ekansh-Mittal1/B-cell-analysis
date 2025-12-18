<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { currentView, analysisState, resultsState, processSequenceResults, processDlSequenceResults, addLog, setProgress } from './lib/stores/app';
  import Wizard from './routes/wizard/Wizard.svelte';
  import Results from './routes/results/Results.svelte';
  import ThresholdDialog from './lib/components/ThresholdDialog.svelte';
  
  // Event listener cleanup functions
  let cleanupFns: (() => void)[] = [];
  
  onMount(() => {
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
            // Capture and store the output directory
            if (data.data.output_dir) {
              console.log('[App] Storing output directory:', data.data.output_dir);
              resultsState.update(s => ({
                ...s,
                outputDir: data.data.output_dir
              }));
            }
          }
          if (data.artifact === 'dl_sequences' && data.data) {
            processDlSequenceResults(data.data);
          }
          if (data.artifact === 'tree_images' && data.data?.images) {
            resultsState.update(s => ({
              ...s,
              treeImages: data.data.images
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
          console.log('[App] Received complete event:', data);
          analysisState.update(s => ({
            ...s,
            isRunning: false,
            error: data.error || null
          }));
          
          if (data.success) {
            currentView.set('results');
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

<div class="app-container">
  <!-- Header with drag region for macOS -->
  <header class="app-header">
    <div class="header-content">
      <h1 class="app-title">B-Cell Repertoire Analysis</h1>
      
      {#if $currentView === 'results'}
        <button 
          class="btn btn-ghost btn-sm"
          on:click={() => currentView.set('wizard')}
        >
          ← New Analysis
        </button>
      {/if}
    </div>
  </header>
  
  <!-- Main content -->
  <main class="app-content">
    {#if $currentView === 'wizard'}
      <Wizard />
    {:else}
      <Results />
    {/if}
  </main>
  
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
  
  .app-title {
    font-size: var(--text-sm);
    font-weight: var(--font-semibold);
    color: var(--text-primary);
    margin: 0;
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

