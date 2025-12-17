<script lang="ts">
  import { resultsState, selectedSequence } from '../../lib/stores/app';
  import SequenceBrowser from './SequenceBrowser.svelte';
  import SequenceDetails from './SequenceDetails.svelte';
  import PhylogeneticTrees from './PhylogeneticTrees.svelte';
  
  type Tab = 'browser' | 'trees';
  let activeTab: Tab = 'browser';
</script>

<div class="results-container">
  <!-- Header with tabs -->
  <div class="results-header">
    <div class="header-info">
      <h1 class="results-title">Analysis Results</h1>
      <span class="sequence-count">
        {$resultsState.sequences.length} sequences analyzed
      </span>
    </div>
    
    <div class="tabs">
      <button 
        class="tab" 
        class:active={activeTab === 'browser'}
        on:click={() => activeTab = 'browser'}
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <rect x="2" y="2" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.5"/>
          <rect x="9" y="2" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.5"/>
          <rect x="2" y="9" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.5"/>
          <rect x="9" y="9" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.5"/>
        </svg>
        Sequence Browser
      </button>
      <button 
        class="tab" 
        class:active={activeTab === 'trees'}
        on:click={() => activeTab = 'trees'}
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M8 2v4M8 6H4v4M8 6h4v4M4 10v4M12 10v4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
        Phylogenetic Trees
        {#if $resultsState.treeImages.length > 0}
          <span class="tab-badge">{$resultsState.treeImages.length}</span>
        {/if}
      </button>
    </div>
  </div>
  
  <!-- Main content -->
  <div class="results-content">
    {#if activeTab === 'browser'}
      <div class="browser-layout">
        <aside class="browser-sidebar">
          <SequenceBrowser />
        </aside>
        <main class="details-panel">
          {#if $selectedSequence}
            <SequenceDetails sequence={$selectedSequence} />
          {:else}
            <div class="empty-state">
              <div class="empty-icon">
                <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                  <path d="M24 4l20 11.5v17L24 44 4 32.5v-17L24 4z" stroke="currentColor" stroke-width="2"/>
                  <path d="M24 22v12M24 18h.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
              </div>
              <h3 class="empty-title">No Sequence Selected</h3>
              <p class="empty-description">
                Select a sequence from the browser to view detailed information
              </p>
            </div>
          {/if}
        </main>
      </div>
    {:else}
      <PhylogeneticTrees />
    {/if}
  </div>
</div>

<style>
  .results-container {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
    width: 100%;
    margin: 0;
    padding: 0;
  }
  
  .results-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--space-4) var(--space-6);
    background: var(--surface-raised);
    border-bottom: 1px solid var(--border-light);
    flex-shrink: 0;
  }
  
  .header-info {
    display: flex;
    align-items: baseline;
    gap: var(--space-3);
  }
  
  .results-title {
    font-size: var(--text-lg);
    font-weight: var(--font-semibold);
    color: var(--text-primary);
    margin: 0;
  }
  
  .sequence-count {
    font-size: var(--text-sm);
    color: var(--text-tertiary);
  }
  
  .tabs {
    display: flex;
    gap: var(--space-1);
    background: var(--gray-100);
    padding: var(--space-1);
    border-radius: var(--border-radius-md);
  }
  
  .tab {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-4);
    background: transparent;
    border: none;
    border-radius: var(--border-radius-sm);
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    color: var(--text-secondary);
    cursor: pointer;
    transition: all var(--transition-fast);
  }
  
  .tab:hover {
    color: var(--text-primary);
  }
  
  .tab.active {
    background: var(--surface-raised);
    color: var(--text-primary);
    box-shadow: var(--shadow-sm);
  }
  
  .tab svg {
    opacity: 0.7;
  }
  
  .tab.active svg {
    opacity: 1;
  }
  
  .tab-badge {
    padding: 2px 6px;
    background: var(--color-primary);
    color: white;
    border-radius: var(--border-radius-full);
    font-size: 10px;
    font-weight: var(--font-semibold);
  }
  
  .results-content {
    flex: 1;
    overflow: hidden;
    min-height: 0;
    margin: 0;
    padding: 0;
    width: 100%;
  }
  
  .browser-layout {
    display: flex;
    height: 100%;
    min-height: 0;
    width: 100%;
    margin: 0;
    padding: 0;
  }
  
  .browser-sidebar {
    width: 340px;
    background: var(--surface-raised);
    border-right: 1px solid var(--border-light);
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
    overflow: hidden;
    min-height: 0;
  }
  
  .details-panel {
    flex: 1 !important;
    overflow-y: auto;
    background: var(--gray-50);
    width: 100% !important;
    min-width: 0;
    max-width: none !important;
    box-sizing: border-box;
  }
  
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    padding: var(--space-8);
    text-align: center;
  }
  
  .empty-icon {
    color: var(--gray-300);
    margin-bottom: var(--space-4);
  }
  
  .empty-title {
    font-size: var(--text-lg);
    font-weight: var(--font-semibold);
    color: var(--text-primary);
    margin: 0 0 var(--space-2) 0;
  }
  
  .empty-description {
    font-size: var(--text-sm);
    color: var(--text-tertiary);
    margin: 0;
  }
</style>

