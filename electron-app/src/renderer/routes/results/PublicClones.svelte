<script lang="ts">
  import { onMount } from 'svelte';
  import { resultsState, publicClonesActions } from '../../lib/stores/app';
  import HeatmapViz from '../../lib/components/visualizations/HeatmapViz.svelte';

  // Settings
  let selectedMode: 'exact' | 'lenient' | 'custom' = 'lenient';
  let customThreshold = 0.85;
  let customMismatches = 2;
  let topN = 10;
  let customTopN = 10;
  
  // UI State
  let selectedCloneId: string | null = null;
  let activeVizTab: 'details' | 'heatmap' = 'details';
  let isAnalyzing = false;

  $: hasResults = $resultsState.publicClonesData !== null;
  $: selectedClone = hasResults && selectedCloneId
    ? $resultsState.publicClonesData!.public_clones.find(c => c.id === selectedCloneId) || null
    : null;

  async function runAnalysis() {
    if (!window.electronAPI) {
      alert('Electron API not available.');
      return;
    }

    // Get output directory from app paths
    let outputDir = $resultsState.outputDir;
    
    // If not set, try to get from paths
    if (!outputDir) {
      try {
        const paths = await window.electronAPI.getPaths();
        outputDir = paths.userData + '/outs';
      } catch (error) {
        console.error('Failed to get paths:', error);
        alert('Analysis not ready. Please run main analysis first.');
        return;
      }
    }

    isAnalyzing = true;
    publicClonesActions.startAnalysis();

    const config = {
      output_dir: outputDir,
      mode: selectedMode,
      similarity_threshold: customThreshold,
      max_mismatches: customMismatches,
      top_n: topN === -1 ? customTopN : topN
    };

    try {
      await window.electronAPI.runPublicCloneAnalysis(config);
    } catch (error: any) {
      console.error('Public clone analysis error:', error);
      alert(`Analysis failed: ${error.message || 'Unknown error'}`);
      isAnalyzing = false;
      publicClonesActions.updateResults({
        public_clones: [],
        top_x: [],
        stats: {
          total_public_clones: 0,
          total_sequences_in_public_clones: 0,
          max_patient_sharing: 0,
          total_patients: 0,
          clustering_mode: selectedMode,
          similarity_threshold: customThreshold,
          top_n_displayed: 0
        },
        method: '',
        visualizations: {
          heatmap: { clones: [], patients: [], matrix: [], frequencies: [] },
          chord: { nodes: [], links: [] },
          upset: { sets: {}, intersections: [] },
          network: { nodes: [], edges: [] }
        }
      });
    }
  }

  function selectClone(cloneId: string) {
    selectedCloneId = cloneId;
  }

  function selectCloneByIndex(index: number) {
    if ($resultsState.publicClonesData && index < $resultsState.publicClonesData.public_clones.length) {
      selectedCloneId = $resultsState.publicClonesData.public_clones[index].id;
      activeVizTab = 'details';
    }
  }

  function getPatientColor(index: number): string {
    const colors = [
      '#4CAF50', '#2196F3', '#FF9800', '#E91E63', '#9C27B0',
      '#00BCD4', '#CDDC39', '#FF5722', '#795548', '#607D8B'
    ];
    return colors[index % colors.length];
  }

  // Listen for results
  onMount(() => {
    if (!window.electronAPI) return;

    const cleanup = window.electronAPI.onPublicCloneResult((data: any) => {
      console.log('Received public clone result:', data);
      if (data.data) {
        publicClonesActions.updateResults(data.data);
        isAnalyzing = false;
      }
    });

    const cleanupComplete = window.electronAPI.onPublicCloneComplete((data: any) => {
      console.log('Public clone analysis complete:', data);
      isAnalyzing = false;
    });

    const cleanupError = window.electronAPI.onPublicCloneError((error: any) => {
      console.error('Public clone analysis error:', error);
      alert(`Analysis failed: ${error}`);
      isAnalyzing = false;
    });

    return () => {
      cleanup();
      cleanupComplete();
      cleanupError();
    };
  });
</script>

<div class="public-clones-container">
  {#if !hasResults}
    <!-- Settings Panel -->
    <div class="settings-panel">
      <h2>Public Clone Analysis Settings</h2>
      <p class="description">
        Identify antibody clones that are shared across multiple patients/samples based on CDR3 sequence similarity.
      </p>
      
      {#if $resultsState.sequences.length === 0}
        <div class="info-banner">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <circle cx="8" cy="8" r="7" stroke="currentColor" stroke-width="1.5"/>
            <path d="M8 11V8M8 5h.01" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
          <span>Please run the main analysis first to enable public clone identification.</span>
        </div>
      {/if}

      <div class="settings-section">
        <h3>Clustering Mode</h3>
        <div class="radio-group">
          <label>
            <input type="radio" name="clustering-mode" bind:group={selectedMode} value="exact" />
            <div class="label-content">
              <span>Exact Match</span>
              <small>100% CDR3 AA identity</small>
            </div>
          </label>
          <label>
            <input type="radio" name="clustering-mode" bind:group={selectedMode} value="lenient" />
            <div class="label-content">
              <span>Lenient (Recommended)</span>
              <small>≤2 AA mismatches or ≥85% similarity (AIRR standard)</small>
            </div>
          </label>
          <label>
            <input type="radio" name="clustering-mode" bind:group={selectedMode} value="custom" />
            <div class="label-content">
              <span>Custom</span>
              <small>User-defined threshold</small>
            </div>
          </label>
        </div>

        {#if selectedMode === 'custom'}
          <div class="custom-inputs">
            <label>
              <span>Similarity Threshold:</span>
              <input type="range" bind:value={customThreshold} min="0.7" max="1.0" step="0.05" />
              <span class="value">{(customThreshold * 100).toFixed(0)}%</span>
            </label>
            <label>
              <span>Max AA Mismatches:</span>
              <input type="number" bind:value={customMismatches} min="0" max="5" />
            </label>
          </div>
        {/if}
      </div>

      <div class="settings-section">
        <h3>Display Settings</h3>
        <div class="form-group">
          <label>
            <span>Show Top:</span>
            <select bind:value={topN}>
              <option value={10}>10 clones</option>
              <option value={20}>20 clones</option>
              <option value={50}>50 clones</option>
              <option value={-1}>Custom</option>
            </select>
          </label>
          
          {#if topN === -1}
            <label>
              <span>Custom Number:</span>
              <input type="number" bind:value={customTopN} min="1" max="200" />
            </label>
          {/if}
        </div>
      </div>

      <button 
        class="btn btn-primary btn-large" 
        on:click={runAnalysis} 
        disabled={isAnalyzing || $resultsState.sequences.length === 0}
      >
        {#if isAnalyzing}
          <div class="spinner"></div>
          Analyzing...
        {:else if $resultsState.sequences.length === 0}
          Run Main Analysis First
        {:else}
          Analyze Public Clones
        {/if}
      </button>
    </div>
  {:else}
    <!-- Results Layout -->
    <div class="results-layout">
      <!-- Statistics Dashboard -->
      <div class="stats-dashboard">
        <div class="stat-card">
          <div class="stat-value">{$resultsState.publicClonesData?.stats.total_public_clones ?? 0}</div>
          <div class="stat-label">Public Clones</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{$resultsState.publicClonesData?.stats.total_patients ?? 0}</div>
          <div class="stat-label">Total Patients</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{$resultsState.publicClonesData?.stats.max_patient_sharing ?? 0}</div>
          <div class="stat-label">Max Sharing</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{$resultsState.publicClonesData?.stats.total_sequences_in_public_clones ?? 0}</div>
          <div class="stat-label">Total Sequences</div>
        </div>
      </div>

      <div class="results-content">
        <!-- Left Panel: Top X List -->
        <div class="clones-list">
          <div class="list-header">
            <h3>Top {$resultsState.publicClonesData?.stats.top_n_displayed ?? 0} Public Clones</h3>
            <button class="btn btn-secondary btn-sm" on:click={() => publicClonesActions.clearResults()}>
              Re-analyze
            </button>
          </div>

          <div class="clone-cards">
            {#each ($resultsState.publicClonesData?.top_x ?? []) as clone, index}
              <button
                class="clone-card"
                class:selected={selectedCloneId === clone.id}
                on:click={() => selectClone(clone.id)}
              >
                <div class="clone-rank">#{index + 1}</div>
                <div class="clone-info">
                  <div class="clone-header">
                    <code class="cdr3-sequence">{clone.cdr3_aa}</code>
                  </div>
                  <div class="clone-genes">
                    <span class="gene-badge v-gene">{clone.v_gene}</span>
                    <span class="gene-badge j-gene">{clone.j_gene}</span>
                  </div>
                  <div class="clone-metrics">
                    <span class="metric">
                      <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                        <circle cx="7" cy="5" r="2" stroke="currentColor" stroke-width="1.5"/>
                        <path d="M7 10c-3 0-5-1.5-5-3h10c0 1.5-2 3-5 3z" fill="currentColor"/>
                      </svg>
                      {clone.patient_count} patients
                    </span>
                    <span class="metric">
                      <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                        <rect x="2" y="2" width="10" height="10" rx="1" stroke="currentColor" stroke-width="1.5"/>
                      </svg>
                      {clone.sequence_count} sequences
                    </span>
                  </div>
                </div>
              </button>
            {/each}
          </div>
        </div>

        <!-- Right Panel: Details/Visualizations -->
        <div class="details-panel">
          <div class="detail-tabs">
            <button
              class="tab"
              class:active={activeVizTab === 'details'}
              on:click={() => activeVizTab = 'details'}
            >
              Clone Details
            </button>
            <button
              class="tab"
              class:active={activeVizTab === 'heatmap'}
              on:click={() => activeVizTab = 'heatmap'}
            >
              Heatmap
            </button>
          </div>

          <div class="detail-content" class:heatmap-active={activeVizTab === 'heatmap'}>
            {#if activeVizTab === 'details'}
              {#if selectedClone}
                <div class="clone-detail">
                  <h2>{selectedClone.cdr3_aa}</h2>

                  <div class="detail-card">
                    <h3>CDR3 Region</h3>
                    <div class="detail-row">
                      <span class="detail-label">Amino Acid:</span>
                      <code>{selectedClone.cdr3_aa}</code>
                    </div>
                    <div class="detail-row">
                      <span class="detail-label">DNA:</span>
                      <code class="dna">{selectedClone.cdr3_dna}</code>
                    </div>
                    <div class="detail-row">
                      <span class="detail-label">Length:</span>
                      <span>{selectedClone.cdr3_aa.length} aa</span>
                    </div>
                  </div>

                  <div class="detail-card">
                    <h3>Gene Usage</h3>
                    <div class="detail-row">
                      <span class="detail-label">V Gene:</span>
                      <span>{selectedClone.v_gene}</span>
                    </div>
                    <div class="detail-row">
                      <span class="detail-label">J Gene:</span>
                      <span>{selectedClone.j_gene}</span>
                    </div>
                  </div>

                  <div class="detail-card">
                    <h3>Patient Distribution</h3>
                    <div class="patient-list">
                      {#each selectedClone.patients as patient, index}
                        <div class="patient-item" style="border-left: 4px solid {getPatientColor(index)}">
                          <div class="patient-name">{patient}</div>
                          <div class="patient-count">
                            {selectedClone.sequences.filter(s => s.includes(patient)).length} sequences
                          </div>
                        </div>
                      {/each}
                    </div>
                  </div>
                </div>
              {:else}
                <div class="empty-selection">
                  <p>Select a clone to view details</p>
                </div>
              {/if}
            {:else if activeVizTab === 'heatmap' && $resultsState.publicClonesData}
              <div class="heatmap-wrapper">
                <HeatmapViz
                  data={$resultsState.publicClonesData.visualizations.heatmap}
                  onCloneClick={selectCloneByIndex}
                />
              </div>
            {/if}
          </div>
        </div>
      </div>
    </div>
  {/if}

  {#if isAnalyzing}
    <div class="loading-overlay">
      <div class="loading-content">
        <div class="spinner-large"></div>
        <p>Analyzing public clones...</p>
      </div>
    </div>
  {/if}
</div>

<style>
  .public-clones-container {
    height: 100%;
    background: var(--gray-50);
    overflow: hidden;
    position: relative;
    display: flex;
    flex-direction: column;
  }

  /* Settings Panel */
  .settings-panel {
    max-width: 800px;
    margin: 0 auto;
    padding: var(--space-8);
  }

  .settings-panel h2 {
    font-size: var(--text-2xl);
    font-weight: var(--font-bold);
    color: var(--text-primary);
    margin-bottom: var(--space-2);
  }

  .description {
    color: var(--text-secondary);
    margin-bottom: var(--space-6);
  }

  .info-banner {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-3) var(--space-4);
    background: #FFF3CD;
    border: 1px solid #FFC107;
    border-radius: var(--border-radius-md);
    color: #856404;
    margin-bottom: var(--space-4);
  }

  .info-banner svg {
    flex-shrink: 0;
  }

  .settings-section {
    background: var(--surface-raised);
    padding: var(--space-4);
    border-radius: var(--border-radius-md);
    margin-bottom: var(--space-4);
  }

  .settings-section h3 {
    font-size: var(--text-base);
    font-weight: var(--font-semibold);
    margin-bottom: var(--space-3);
  }

  .radio-group {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .radio-group label {
    display: flex;
    align-items: flex-start;
    gap: var(--space-2);
    cursor: pointer;
    padding: var(--space-3);
    border-radius: var(--border-radius-sm);
    transition: background var(--transition-fast);
  }

  .radio-group label:hover {
    background: var(--gray-50);
  }

  .radio-group label input[type="radio"] {
    margin-top: 2px;
    cursor: pointer;
  }

  .label-content {
    flex: 1;
  }

  .label-content span {
    display: block;
    font-weight: var(--font-medium);
    margin-bottom: 2px;
  }

  .label-content small {
    display: block;
    color: var(--text-tertiary);
    font-size: var(--text-xs);
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .form-group label {
    display: flex;
    align-items: center;
    gap: var(--space-2);
  }

  .form-group label span {
    min-width: 100px;
  }

  .form-group select,
  .form-group input[type="number"] {
    flex: 1;
    padding: var(--space-2);
    border: 1px solid var(--border-light);
    border-radius: var(--border-radius-sm);
    font-size: var(--text-sm);
  }

  .custom-inputs {
    margin-top: var(--space-3);
    padding: var(--space-3);
    background: var(--gray-50);
    border-radius: var(--border-radius-sm);
  }

  .custom-inputs label {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    margin-bottom: var(--space-2);
  }

  .custom-inputs label span:first-child {
    min-width: 150px;
  }

  .custom-inputs input[type="range"] {
    flex: 1;
  }

  .custom-inputs input[type="number"] {
    padding: var(--space-2);
    border: 1px solid var(--border-light);
    border-radius: var(--border-radius-sm);
    font-size: var(--text-sm);
    width: 100px;
  }

  .custom-inputs .value {
    min-width: 50px;
    text-align: right;
    font-weight: var(--font-semibold);
  }

  .btn-large {
    width: 100%;
    padding: var(--space-4);
    font-size: var(--text-base);
    margin-top: var(--space-6);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-2);
  }

  .btn-large:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .btn-large .spinner {
    display: inline-block;
  }

  /* Stats Dashboard */
  .stats-dashboard {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: var(--space-4);
    padding: var(--space-4);
  }

  .stat-card {
    background: var(--surface-raised);
    padding: var(--space-4);
    border-radius: var(--border-radius-lg);
    text-align: center;
  }

  .stat-value {
    font-size: var(--text-3xl);
    font-weight: var(--font-bold);
    color: var(--color-primary);
  }

  .stat-label {
    font-size: var(--text-sm);
    color: var(--text-secondary);
    margin-top: var(--space-2);
  }

  /* Results Layout */
  .results-layout {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }

  .results-content {
    flex: 1;
    display: flex;
    gap: var(--space-4);
    padding: var(--space-4);
    min-height: 0;
  }

  /* Clones List */
  .clones-list {
    width: 400px;
    background: var(--surface-raised);
    border-radius: var(--border-radius-md);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .list-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--space-4);
    border-bottom: 1px solid var(--border-light);
  }

  .list-header h3 {
    font-size: var(--text-base);
    font-weight: var(--font-semibold);
    margin: 0;
  }

  .clone-cards {
    flex: 1;
    overflow-y: auto;
    padding: var(--space-2);
  }

  .clone-card {
    display: flex;
    gap: var(--space-3);
    padding: var(--space-3);
    background: var(--surface-raised);
    border: 2px solid var(--border-light);
    border-radius: var(--border-radius-md);
    cursor: pointer;
    transition: all var(--transition-fast);
    width: 100%;
    text-align: left;
    margin-bottom: var(--space-2);
  }

  .clone-card:hover {
    border-color: var(--color-primary-light);
    transform: translateY(-1px);
    box-shadow: var(--shadow-sm);
  }

  .clone-card.selected {
    border-color: var(--color-primary);
    background: var(--color-primary-light);
  }

  .clone-rank {
    font-size: var(--text-xl);
    font-weight: var(--font-bold);
    color: var(--color-primary);
    min-width: 35px;
  }

  .clone-info {
    flex: 1;
    min-width: 0;
  }

  .cdr3-sequence {
    background: var(--gray-100);
    padding: 2px 6px;
    border-radius: var(--border-radius-sm);
    font-family: 'Courier New', monospace;
    font-size: var(--text-xs);
    word-break: break-all;
  }

  .clone-genes {
    display: flex;
    gap: var(--space-2);
    margin-top: var(--space-2);
  }

  .gene-badge {
    padding: 2px 6px;
    border-radius: var(--border-radius-sm);
    font-size: 10px;
    font-weight: var(--font-medium);
  }

  .v-gene {
    background: #E3F2FD;
    color: #1976D2;
  }

  .j-gene {
    background: #F3E5F5;
    color: #7B1FA2;
  }

  .clone-metrics {
    display: flex;
    gap: var(--space-3);
    margin-top: var(--space-2);
    font-size: var(--text-xs);
    color: var(--text-secondary);
  }

  .metric {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  /* Details Panel */
  .details-panel {
    flex: 1;
    background: var(--surface-raised);
    border-radius: var(--border-radius-md);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .detail-tabs {
    display: flex;
    border-bottom: 1px solid var(--border-light);
  }

  .tab {
    padding: var(--space-3) var(--space-4);
    background: none;
    border: none;
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    color: var(--text-secondary);
    cursor: pointer;
    border-bottom: 2px solid transparent;
    transition: all var(--transition-fast);
  }

  .tab:hover {
    color: var(--text-primary);
  }

  .tab.active {
    color: var(--color-primary);
    border-bottom-color: var(--color-primary);
  }

  .detail-content {
    flex: 1;
    overflow: auto;
    min-height: 0;
    padding: var(--space-4);
  }
  
  .detail-content.heatmap-active {
    padding: 0;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }
  
  .heatmap-wrapper {
    flex: 1;
    min-height: 0;
    width: 100%;
    display: flex;
    flex-direction: column;
  }

  .clone-detail h2 {
    font-size: var(--text-xl);
    font-weight: var(--font-bold);
    margin-bottom: var(--space-4);
    word-break: break-all;
  }

  .detail-card {
    background: var(--gray-50);
    padding: var(--space-4);
    border-radius: var(--border-radius-md);
    margin-bottom: var(--space-4);
  }

  .detail-card h3 {
    font-size: var(--text-sm);
    font-weight: var(--font-semibold);
    margin-bottom: var(--space-3);
    color: var(--text-secondary);
  }

  .detail-row {
    display: flex;
    gap: var(--space-3);
    margin-bottom: var(--space-2);
  }

  .detail-label {
    min-width: 100px;
    color: var(--text-secondary);
    font-size: var(--text-sm);
  }

  .detail-row code {
    background: white;
    padding: 2px 6px;
    border-radius: var(--border-radius-sm);
    font-size: var(--text-sm);
  }

  .detail-row code.dna {
    word-break: break-all;
    font-size: var(--text-xs);
  }

  .patient-list {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .patient-item {
    padding: var(--space-3);
    background: white;
    border-radius: var(--border-radius-sm);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .patient-name {
    font-weight: var(--font-medium);
  }

  .patient-count {
    color: var(--text-secondary);
    font-size: var(--text-sm);
  }

  .empty-selection {
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-tertiary);
  }

  /* Loading Overlay */
  .loading-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.7);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }

  .loading-content {
    text-align: center;
    color: white;
  }

  .spinner, .spinner-large {
    width: 24px;
    height: 24px;
    border: 3px solid rgba(255, 255, 255, 0.3);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 0 auto;
  }

  .spinner-large {
    width: 48px;
    height: 48px;
    border-width: 4px;
    margin-bottom: var(--space-4);
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }
</style>

