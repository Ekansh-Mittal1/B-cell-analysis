<script lang="ts">
  import { wizardState, analysisState, resetAnalysis } from '../../lib/stores/app';
  
  function handleBack() {
    wizardState.update(s => ({
      ...s,
      step: 2
    }));
  }
  
  async function handleStartAnalysis() {
    if (!window.electronAPI) return;
    
    resetAnalysis();
    analysisState.update(s => ({
      ...s,
      isRunning: true
    }));
    
    try {
      await window.electronAPI.startPipeline({
        fasta_dir: $wizardState.fastaDir!,
        clean_fasta: $wizardState.cleanFasta,
        database_type: $wizardState.databaseType,
        database_v: $wizardState.customDatabaseV || undefined,
        database_d: $wizardState.customDatabaseD || undefined,
        database_j: $wizardState.customDatabaseJ || undefined
      });
    } catch (error: any) {
      analysisState.update(s => ({
        ...s,
        isRunning: false,
        error: error.message || 'An unexpected error occurred'
      }));
    }
  }
  
  function getDirectoryName(path: string): string {
    return path.split('/').pop() || path;
  }
  
  function getFileName(path: string): string {
    return path.split('/').pop() || path;
  }
</script>

<div class="step-container">
  <header class="step-header">
    <span class="step-number">Step 3</span>
    <h1 class="step-title">Review & Start</h1>
    <p class="step-description">
      Review your analysis settings before starting. The analysis may take several minutes 
      depending on the number of sequences.
    </p>
  </header>
  
  <div class="step-content">
    <!-- Summary card -->
    <div class="summary-card">
      <div class="summary-header">
        <h2 class="summary-title">Analysis Configuration</h2>
        <span class="ready-badge">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M11.5 4L5.5 10L2.5 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          Ready to Start
        </span>
      </div>
      
      <div class="summary-sections">
        <!-- Input Files Section -->
        <div class="summary-section">
          <div class="section-icon">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <rect x="2" y="5" width="16" height="12" rx="2" stroke="currentColor" stroke-width="1.5"/>
              <path d="M2 8h16" stroke="currentColor" stroke-width="1.5"/>
            </svg>
          </div>
          <div class="section-content">
            <h3 class="section-title">Input Files</h3>
            <div class="section-details">
              <div class="detail-row">
                <span class="detail-label">Directory</span>
                <span class="detail-value">{getDirectoryName($wizardState.fastaDir || '')}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">Files</span>
                <span class="detail-value">{$wizardState.fastaCount} FASTA file{$wizardState.fastaCount !== 1 ? 's' : ''}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">Clean Files</span>
                <span class="detail-value">{$wizardState.cleanFasta ? 'Yes' : 'No'}</span>
              </div>
            </div>
          </div>
          <button class="edit-btn" on:click={() => wizardState.update(s => ({...s, step: 1}))}>
            Edit
          </button>
        </div>
        
        <!-- Database Section -->
        <div class="summary-section">
          <div class="section-icon">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <ellipse cx="10" cy="5" rx="7" ry="3" stroke="currentColor" stroke-width="1.5"/>
              <path d="M3 5v10c0 1.66 3.13 3 7 3s7-1.34 7-3V5" stroke="currentColor" stroke-width="1.5"/>
              <path d="M3 10c0 1.66 3.13 3 7 3s7-1.34 7-3" stroke="currentColor" stroke-width="1.5"/>
            </svg>
          </div>
          <div class="section-content">
            <h3 class="section-title">Reference Database</h3>
            <div class="section-details">
              <div class="detail-row">
                <span class="detail-label">Type</span>
                <span class="detail-value">
                  {$wizardState.databaseType === 'IMGT' ? 'IMGT Human Database' : 'Custom Database'}
                </span>
              </div>
              {#if $wizardState.databaseType === 'Custom'}
                <div class="detail-row">
                  <span class="detail-label">V Gene</span>
                  <span class="detail-value file">{getFileName($wizardState.customDatabaseV || '')}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">D Gene</span>
                  <span class="detail-value file">{getFileName($wizardState.customDatabaseD || '')}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">J Gene</span>
                  <span class="detail-value file">{getFileName($wizardState.customDatabaseJ || '')}</span>
                </div>
              {/if}
            </div>
          </div>
          <button class="edit-btn" on:click={() => wizardState.update(s => ({...s, step: 2}))}>
            Edit
          </button>
        </div>
      </div>
    </div>
    
    <!-- Analysis steps info -->
    <div class="analysis-info">
      <h3 class="info-title">Analysis Pipeline</h3>
      <p class="info-description">
        The following steps will be performed:
      </p>
      <div class="pipeline-steps">
        <div class="pipeline-step">
          <span class="step-marker">1</span>
          <div class="step-info">
            <span class="step-name">IgBLAST Alignment</span>
            <span class="step-desc">Align sequences against germline database</span>
          </div>
        </div>
        <div class="pipeline-step">
          <span class="step-marker">2</span>
          <div class="step-info">
            <span class="step-name">Distance Calculation</span>
            <span class="step-desc">Calculate pairwise sequence distances</span>
          </div>
        </div>
        <div class="pipeline-step">
          <span class="step-marker">3</span>
          <div class="step-info">
            <span class="step-name">Clone Definition</span>
            <span class="step-desc">Identify clonal families using threshold</span>
          </div>
        </div>
        <div class="pipeline-step">
          <span class="step-marker">4</span>
          <div class="step-info">
            <span class="step-name">Germline Reconstruction</span>
            <span class="step-desc">Generate inferred germline sequences</span>
          </div>
        </div>
        <div class="pipeline-step">
          <span class="step-marker">5</span>
          <div class="step-info">
            <span class="step-name">Phylogenetic Trees</span>
            <span class="step-desc">Build lineage trees for top clones</span>
          </div>
        </div>
      </div>
    </div>
  </div>
  
  <footer class="step-footer">
    <button class="btn btn-ghost" on:click={handleBack}>
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <path d="M10 4l-4 4 4 4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      Back
    </button>
    <button 
      class="btn btn-primary btn-lg start-btn"
      on:click={handleStartAnalysis}
    >
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
        <path d="M4 3l11 6-11 6V3z" fill="currentColor"/>
      </svg>
      Start Analysis
    </button>
  </footer>
</div>

<style>
  .step-container {
    display: flex;
    flex-direction: column;
    min-height: 100%;
  }
  
  .step-header {
    margin-bottom: var(--space-8);
  }
  
  .step-number {
    display: inline-block;
    font-size: var(--text-xs);
    font-weight: var(--font-semibold);
    color: var(--color-primary);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: var(--space-2);
  }
  
  .step-title {
    font-size: var(--text-2xl);
    font-weight: var(--font-bold);
    color: var(--text-primary);
    margin: 0 0 var(--space-2) 0;
  }
  
  .step-description {
    font-size: var(--text-base);
    color: var(--text-secondary);
    line-height: var(--leading-relaxed);
    margin: 0;
  }
  
  .step-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: var(--space-6);
  }
  
  .summary-card {
    background: var(--surface-raised);
    border: 1px solid var(--border-light);
    border-radius: var(--border-radius-lg);
    overflow: hidden;
  }
  
  .summary-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--space-4) var(--space-5);
    background: var(--gray-50);
    border-bottom: 1px solid var(--border-light);
  }
  
  .summary-title {
    font-size: var(--text-sm);
    font-weight: var(--font-semibold);
    color: var(--text-primary);
    margin: 0;
  }
  
  .ready-badge {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-1) var(--space-3);
    background: var(--color-success-light);
    color: var(--color-success);
    border-radius: var(--border-radius-full);
    font-size: var(--text-xs);
    font-weight: var(--font-medium);
  }
  
  .summary-sections {
    padding: var(--space-2);
  }
  
  .summary-section {
    display: flex;
    gap: var(--space-4);
    padding: var(--space-4);
    border-radius: var(--border-radius-md);
    transition: background var(--transition-fast);
  }
  
  .summary-section:hover {
    background: var(--gray-50);
  }
  
  .section-icon {
    width: 40px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--color-primary-light);
    color: var(--color-primary);
    border-radius: var(--border-radius-md);
    flex-shrink: 0;
  }
  
  .section-content {
    flex: 1;
    min-width: 0;
  }
  
  .section-title {
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    color: var(--text-primary);
    margin: 0 0 var(--space-2) 0;
  }
  
  .section-details {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
  }
  
  .detail-row {
    display: flex;
    gap: var(--space-3);
    font-size: var(--text-xs);
  }
  
  .detail-label {
    color: var(--text-tertiary);
    min-width: 80px;
  }
  
  .detail-value {
    color: var(--text-secondary);
    font-weight: var(--font-medium);
  }
  
  .detail-value.file {
    font-family: var(--font-mono);
    font-size: 11px;
  }
  
  .edit-btn {
    padding: var(--space-2) var(--space-3);
    background: transparent;
    border: 1px solid var(--border-default);
    border-radius: var(--border-radius-md);
    font-size: var(--text-xs);
    font-weight: var(--font-medium);
    color: var(--text-secondary);
    cursor: pointer;
    opacity: 0;
    transition: all var(--transition-fast);
    align-self: flex-start;
  }
  
  .summary-section:hover .edit-btn {
    opacity: 1;
  }
  
  .edit-btn:hover {
    background: var(--gray-100);
    color: var(--text-primary);
  }
  
  .analysis-info {
    background: var(--surface-raised);
    border: 1px solid var(--border-light);
    border-radius: var(--border-radius-lg);
    padding: var(--space-5);
  }
  
  .info-title {
    font-size: var(--text-sm);
    font-weight: var(--font-semibold);
    color: var(--text-primary);
    margin: 0 0 var(--space-1) 0;
  }
  
  .info-description {
    font-size: var(--text-xs);
    color: var(--text-tertiary);
    margin: 0 0 var(--space-4) 0;
  }
  
  .pipeline-steps {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }
  
  .pipeline-step {
    display: flex;
    align-items: flex-start;
    gap: var(--space-3);
  }
  
  .step-marker {
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--gray-100);
    color: var(--text-tertiary);
    border-radius: var(--border-radius-full);
    font-size: var(--text-xs);
    font-weight: var(--font-semibold);
    flex-shrink: 0;
  }
  
  .step-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  
  .step-name {
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    color: var(--text-primary);
  }
  
  .step-desc {
    font-size: var(--text-xs);
    color: var(--text-tertiary);
  }
  
  .step-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: var(--space-8);
    padding-top: var(--space-6);
    border-top: 1px solid var(--border-light);
  }
  
  .btn svg {
    margin-right: var(--space-2);
  }
  
  .start-btn {
    padding-left: var(--space-6);
    padding-right: var(--space-6);
  }
  
  .start-btn svg {
    margin-right: var(--space-3);
  }
</style>

