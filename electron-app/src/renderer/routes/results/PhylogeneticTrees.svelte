<script lang="ts">
  import { onMount } from 'svelte';
  import { resultsState } from '../../lib/stores/app';
  
  let selectedTreeIndex = 0;
  let treeImageData: string[] = [];
  let isLoading = true;
  let isExporting = false;
  
  onMount(async () => {
    if (window.electronAPI && $resultsState.treeImages.length > 0) {
      // Load all tree images
      const images = await Promise.all(
        $resultsState.treeImages.map(async (path) => {
          const result = await window.electronAPI.readImageBase64(path);
          return result.success ? result.data! : '';
        })
      );
      treeImageData = images;
    }
    isLoading = false;
  });
  
  function getTreeName(path: string): string {
    const filename = path.split('/').pop() || '';
    return filename.replace('.png', '').replace(/_/g, ' ');
  }
  
  async function exportTreeImage() {
    if (!window.electronAPI) {
      alert('Electron API not available');
      return;
    }
    
    if (selectedTreeIndex < 0 || selectedTreeIndex >= $resultsState.treeImages.length) {
      alert('No tree selected');
      return;
    }
    
    const sourcePath = $resultsState.treeImages[selectedTreeIndex];
    const treeName = getTreeName(sourcePath);
    
    isExporting = true;
    
    try {
      // Open save dialog
      const destPath = await window.electronAPI.saveFile({
        defaultPath: `${treeName}.png`,
        filters: [
          { name: 'PNG Images', extensions: ['png'] },
          { name: 'All Files', extensions: ['*'] }
        ]
      });
      
      if (!destPath) {
        // User cancelled
        isExporting = false;
        return;
      }
      
      // Copy the image file to the selected location
      const result = await window.electronAPI.copyFile(sourcePath, destPath);
      
      if (result.success) {
        alert(`Tree image exported successfully to ${destPath}`);
      } else {
        alert(`Failed to export tree image: ${result.error || 'Unknown error'}`);
      }
    } catch (error: any) {
      console.error('Export error:', error);
      alert(`Export failed: ${error.message || 'Unknown error'}`);
    } finally {
      isExporting = false;
    }
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
          {#each $resultsState.treeImages as treePath, index}
            <button 
              class="tree-item"
              class:selected={selectedTreeIndex === index}
              on:click={() => selectedTreeIndex = index}
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M8 2v4M8 6H4v4M8 6h4v4M4 10v4M12 10v4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
              </svg>
              <span class="tree-name">{getTreeName(treePath)}</span>
            </button>
          {/each}
        </div>
      </aside>
      
      <!-- Tree viewer -->
      <main class="tree-viewer">
        {#if isLoading}
          <div class="loading-state">
            <div class="spinner"></div>
            <span>Loading tree images...</span>
          </div>
        {:else if treeImageData[selectedTreeIndex]}
          <div class="tree-image-container">
            <div class="tree-header">
              <div class="tree-header-main">
                <h2 class="tree-title">{getTreeName($resultsState.treeImages[selectedTreeIndex])}</h2>
                <div class="tree-info-note">
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                    <circle cx="8" cy="8" r="7" stroke="currentColor" stroke-width="1.5"/>
                    <path d="M8 6v4M8 4v0" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                  </svg>
                  <span>Trees show unique sequences only. Sequence counts are displayed on tip labels (e.g., "×5" indicates 5 identical sequences).</span>
                </div>
              </div>
              <div class="tree-actions">
                <button 
                  class="btn btn-secondary btn-sm"
                  on:click={exportTreeImage}
                  disabled={isExporting || isLoading}
                  title="Export tree image to PNG file"
                >
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                    <path d="M7 1v8M4 6l3 3 3-3M2 11h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                  {isExporting ? 'Exporting...' : 'Export'}
                </button>
              </div>
            </div>
            <div class="tree-image-wrapper">
              <img 
                src={treeImageData[selectedTreeIndex]}
                alt="Phylogenetic tree"
                class="tree-image"
              />
            </div>
          </div>
        {:else}
          <div class="error-state">
            <p>Failed to load tree image</p>
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
</style>

