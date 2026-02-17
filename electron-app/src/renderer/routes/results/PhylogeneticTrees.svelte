<script lang="ts">
  import { onMount } from 'svelte';
  import { resultsState } from '../../lib/stores/app';
  import type { TreeMetadata } from '../../lib/stores/app';
  import InteractiveTree from './InteractiveTree.svelte';
  
  let selectedTreeIndex = 0;
  let isLoading = false;
  
  interface TimepointTreeGroup {
    label: string;
    trees: { index: number; metadata: TreeMetadata; path: string }[];
  }
  
  // Group trees by timepoint
  $: hasTimepoints = $resultsState.treeMetadata.some(m => m.timepoint);
  
  $: timepointGroups = buildTimepointGroups($resultsState.treeMetadata, $resultsState.treeImages);
  
  let tpExpanded: Record<string, boolean> = {};
  
  function buildTimepointGroups(metadata: TreeMetadata[], images: string[]): TimepointTreeGroup[] {
    if (!metadata.length || !metadata.some(m => m.timepoint)) return [];
    
    const groups: Record<string, TimepointTreeGroup> = {};
    for (let i = 0; i < metadata.length; i++) {
      const m = metadata[i];
      const tp = m.timepoint || 'Other';
      if (!groups[tp]) {
        groups[tp] = { label: tp, trees: [] };
        if (!(tp in tpExpanded)) {
          tpExpanded[tp] = true; // Default expanded
        }
      }
      groups[tp].trees.push({ index: i, metadata: m, path: images[i] || m.path });
    }
    
    // Sort groups by label (T1, T2, T3...)
    return Object.values(groups).sort((a, b) => a.label.localeCompare(b.label, undefined, { numeric: true }));
  }
  
  function toggleTpGroup(label: string) {
    tpExpanded[label] = !tpExpanded[label];
    tpExpanded = { ...tpExpanded };
  }
  
  onMount(async () => {
    console.log('[PhylogeneticTrees] Mounted with', $resultsState.treeImages.length, 'trees');
  });
  
  function getNewickPath(pngPath: string): string {
    let newickPath = pngPath.replace('.png', '.newick');
    return newickPath;
  }
  
  function getTreeName(path: string, index: number): string {
    const metadata = $resultsState.treeMetadata?.[index];
    
    if (metadata && metadata.clone_id !== null) {
      const cloneId = metadata.clone_id;
      const cloneSize = metadata.clone_size;
      if (cloneSize > 0) {
        return `Clone ${cloneId} (${cloneSize} seqs)`;
      }
      return `Clone ${cloneId}`;
    }
    
    const filename = path.split('/').pop() || '';
    const match = filename.match(/tree_(\d+)/);
    if (match) return `Clone ${match[1]}`;
    return filename.replace('.png', '').replace(/_/g, ' ');
  }
  
</script>

<div class="trees-container">
  {#if $resultsState.treeImages.length === 0}
    <div class="empty-state">
      <div class="empty-icon">
        <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
          <path d="M32 8v8M32 48v8M8 32h8M48 32h8M17 17l6 6M41 41l6 6M17 47l6-6M41 23l6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          <circle cx="32" cy="32" r="12" stroke="currentColor" stroke-width="2"/>
        </svg>
      </div>
      <h3 class="empty-title">No Phylogenetic Trees</h3>
      <p class="empty-description">
        Tree visualizations will appear here after a successful analysis with enough clonal diversity.
      </p>
    </div>
  {:else}
    <div class="trees-layout">
      <!-- Tree list sidebar -->
      <aside class="trees-sidebar">
        <div class="sidebar-header">
          <h3 class="sidebar-title">Generated Trees</h3>
          <span class="tree-count">{$resultsState.treeImages.length}</span>
        </div>
        <div class="tree-list">
          {#if hasTimepoints && timepointGroups.length > 0}
            {#each timepointGroups as group}
              <button class="tp-group-header" on:click={() => toggleTpGroup(group.label)}>
                <svg class="tp-chevron" class:expanded={tpExpanded[group.label] !== false} width="12" height="12" viewBox="0 0 12 12" fill="none">
                  <path d="M4 2l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                <span class="tp-group-label">{group.label}</span>
                <span class="tp-group-count">{group.trees.length}</span>
              </button>
              {#if tpExpanded[group.label] !== false}
                {#each group.trees as tree}
                  <button 
                    class="tree-item tree-item-nested"
                    class:selected={selectedTreeIndex === tree.index}
                    on:click={() => selectedTreeIndex = tree.index}
                  >
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                      <path d="M8 2v4M8 6H4v4M8 6h4v4M4 10v4M12 10v4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                    </svg>
                    <span class="tree-name">{getTreeName(tree.path, tree.index)}</span>
                  </button>
                {/each}
              {/if}
            {/each}
          {:else}
            {#each $resultsState.treeImages as treePath, index}
              <button 
                class="tree-item"
                class:selected={selectedTreeIndex === index}
                on:click={() => selectedTreeIndex = index}
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M8 2v4M8 6H4v4M8 6h4v4M4 10v4M12 10v4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                </svg>
                <span class="tree-name">{getTreeName(treePath, index)}</span>
              </button>
            {/each}
          {/if}
        </div>
      </aside>
      
      <!-- Tree viewer -->
      <main class="tree-viewer">
        {#if isLoading}
          <div class="loading-state">
            <div class="spinner"></div>
            <span>Loading tree images...</span>
          </div>
        {:else}
          <div class="tree-view-container">
            <div class="tree-header">
              <div class="tree-header-main">
                <h2 class="tree-title">{getTreeName($resultsState.treeImages[selectedTreeIndex], selectedTreeIndex)}</h2>
              </div>
            </div>
            
            <div class="tree-content">
              <!-- Interactive phylogenetic tree with export functionality -->
              <InteractiveTree 
                newickPath={getNewickPath($resultsState.treeImages[selectedTreeIndex])}
                treeName={getTreeName($resultsState.treeImages[selectedTreeIndex], selectedTreeIndex)}
                cloneSize={$resultsState.treeMetadata?.[selectedTreeIndex]?.clone_size || 0}
              />
            </div>
          </div>
        {/if}
      </main>
    </div>
  {/if}
</div>

<style>
  .trees-container {
    height: 100%;
    overflow: hidden;
  }
  
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    padding: var(--space-8);
    text-align: center;
    background: var(--gray-50);
  }
  
  .empty-icon {
    color: var(--gray-300);
    margin-bottom: var(--space-4);
  }
  
  .empty-title {
    font-size: var(--text-xl);
    font-weight: var(--font-semibold);
    color: var(--text-primary);
    margin: 0 0 var(--space-2) 0;
  }
  
  .empty-description {
    font-size: var(--text-sm);
    color: var(--text-tertiary);
    max-width: 400px;
    margin: 0;
  }
  
  .trees-layout {
    display: flex;
    height: 100%;
  }
  
  .trees-sidebar {
    width: 260px;
    background: var(--surface-raised);
    border-right: 1px solid var(--border-light);
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
  }
  
  .sidebar-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--space-4);
    border-bottom: 1px solid var(--border-light);
  }
  
  .sidebar-title {
    font-size: var(--text-sm);
    font-weight: var(--font-semibold);
    color: var(--text-primary);
    margin: 0;
  }
  
  .tree-count {
    padding: 2px 8px;
    background: var(--color-primary-light);
    color: var(--color-primary);
    border-radius: var(--border-radius-full);
    font-size: 11px;
    font-weight: var(--font-semibold);
  }
  
  .tree-list {
    flex: 1;
    overflow-y: auto;
    padding: var(--space-2);
  }
  
  .tree-item {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    width: 100%;
    padding: var(--space-2) var(--space-3);
    background: transparent;
    border: none;
    border-radius: var(--border-radius-md);
    font-size: var(--text-sm);
    color: var(--text-secondary);
    text-align: left;
    cursor: pointer;
    transition: all var(--transition-fast);
  }
  
  .tree-item:hover {
    background: var(--gray-50);
    color: var(--text-primary);
  }
  
  .tree-item.selected {
    background: var(--color-primary-light);
    color: var(--color-primary);
  }
  
  .tree-item svg {
    flex-shrink: 0;
    opacity: 0.6;
  }
  
  .tree-item.selected svg {
    opacity: 1;
  }
  
  .tree-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  
  .tree-viewer {
    flex: 1;
    background: var(--gray-50);
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }
  
  .loading-state,
  .error-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    gap: var(--space-4);
    color: var(--text-tertiary);
    font-size: var(--text-sm);
  }
  
  .spinner {
    width: 24px;
    height: 24px;
    border: 3px solid var(--gray-200);
    border-top-color: var(--color-primary);
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }
  
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
  
  .tree-image-container {
    display: flex;
    flex-direction: column;
    height: 100%;
  }
  
  .tree-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding: var(--space-4) var(--space-6);
    background: var(--surface-raised);
    border-bottom: 1px solid var(--border-light);
    flex-shrink: 0;
    gap: var(--space-4);
  }
  
  .tree-header-main {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }
  
  .tree-title {
    font-size: var(--text-base);
    font-weight: var(--font-semibold);
    color: var(--text-primary);
    margin: 0;
  }
  
  .viewer-note {
    display: flex;
    align-items: center;
    gap: var(--space-1);
    font-size: 11px;
    color: var(--gray-600);
    margin-top: var(--space-1);
  }
  
  .viewer-note svg {
    flex-shrink: 0;
  }
  
  .tree-info-note {
    display: flex;
    align-items: flex-start;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-3);
    background: var(--color-primary-light);
    border-radius: var(--border-radius-md);
    font-size: var(--text-xs);
    color: var(--color-primary);
    line-height: 1.4;
  }
  
  .tree-info-note svg {
    flex-shrink: 0;
    margin-top: 2px;
    opacity: 0.8;
  }
  
  .tree-info-note span {
    flex: 1;
  }
  
  .tree-actions {
    display: flex;
    gap: var(--space-2);
  }
  
  .tree-actions button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  
  .tree-image-wrapper {
    flex: 1;
    overflow: auto;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: var(--space-6);
  }
  
  .tree-image {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    border-radius: var(--border-radius-md);
    box-shadow: var(--shadow-md);
    background: white;
  }
  
  .tree-view-container {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  
  .tree-content {
    flex: 1;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }
  
  .tp-group-header {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    width: 100%;
    padding: var(--space-2) var(--space-3);
    background: var(--gray-50);
    border: none;
    border-radius: var(--border-radius-md);
    font-size: var(--text-sm);
    font-weight: var(--font-semibold);
    color: var(--text-primary);
    text-align: left;
    cursor: pointer;
    margin-bottom: 2px;
    transition: background var(--transition-fast);
  }
  
  .tp-group-header:hover {
    background: var(--gray-100);
  }
  
  .tp-chevron {
    flex-shrink: 0;
    transition: transform var(--transition-fast);
  }
  
  .tp-chevron.expanded {
    transform: rotate(90deg);
  }
  
  .tp-group-label {
    flex: 1;
  }
  
  .tp-group-count {
    padding: 1px 6px;
    background: var(--color-primary-light);
    color: var(--color-primary);
    border-radius: var(--border-radius-full);
    font-size: 10px;
    font-weight: var(--font-semibold);
  }
  
  .tree-item-nested {
    padding-left: var(--space-6);
  }
  
</style>

