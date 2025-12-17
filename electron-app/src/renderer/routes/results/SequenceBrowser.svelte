<script lang="ts">
  import { resultsState, filteredFileGroups, sequenceSearchQuery, toggleFileGroup, selectSequence } from '../../lib/stores/app';
  
  // Function to clean the sequence name for display (remove |||filename.fasta suffix)
  function cleanSequenceName(name: string): string {
    if (name.includes('|||')) {
      return name.split('|||')[0];
    }
    // Fallback for old format with _ delimiter
    if (name.includes('_') && (name.endsWith('.fasta') || name.endsWith('.fa'))) {
      const parts = name.split('_');
      // Remove the last part if it looks like a filename
      if (parts[parts.length - 1].includes('.fasta') || parts[parts.length - 1].includes('.fa')) {
        return parts.slice(0, -1).join('_');
      }
    }
    return name;
  }
</script>

<div class="sequence-browser">
  <!-- Search header -->
  <div class="search-header">
    <div class="search-input-wrapper">
      <svg class="search-icon" width="16" height="16" viewBox="0 0 16 16" fill="none">
        <circle cx="7" cy="7" r="5" stroke="currentColor" stroke-width="1.5"/>
        <path d="M11 11l3 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      </svg>
      <input
        type="text"
        class="search-input"
        placeholder="Search sequences..."
        bind:value={$sequenceSearchQuery}
      />
      {#if $sequenceSearchQuery}
        <button 
          class="clear-btn"
          on:click={() => $sequenceSearchQuery = ''}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M4 4l6 6M10 4l-6 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
        </button>
      {/if}
    </div>
  </div>
  
  <!-- File groups list -->
  <div class="groups-list">
    {#each $filteredFileGroups as group}
      <div class="file-group">
        <!-- Group header -->
        <button 
          class="group-header"
          on:click={() => toggleFileGroup(group.filename)}
        >
          <svg 
            class="expand-icon"
            class:expanded={group.expanded}
            width="14" 
            height="14" 
            viewBox="0 0 14 14" 
            fill="none"
          >
            <path d="M5 4l4 3-4 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <span class="group-name">{group.filename}</span>
          <span class="group-count">{group.sequences.length}</span>
        </button>
        
        <!-- Sequence list -->
        {#if group.expanded}
          <div class="sequence-list">
            {#each group.sequences as seq}
              <button 
                class="sequence-item"
                class:selected={$resultsState.selectedSequenceId === seq.id}
                on:click={() => selectSequence(seq.id)}
              >
                <div class="seq-main">
                  <span class="seq-name">{cleanSequenceName(seq.name)}</span>
                  {#if seq.clone_id}
                    <span class="clone-badge">Clone {seq.clone_id}</span>
                  {/if}
                </div>
              </button>
            {/each}
          </div>
        {/if}
      </div>
    {:else}
      <div class="empty-state">
        {#if $sequenceSearchQuery}
          <p>No sequences match your search</p>
        {:else}
          <p>No sequences available</p>
        {/if}
      </div>
    {/each}
  </div>
</div>

<style>
  .sequence-browser {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
    overflow: hidden;
  }
  
  .search-header {
    padding: var(--space-4);
    border-bottom: 1px solid var(--border-light);
    flex-shrink: 0;
  }
  
  .search-input-wrapper {
    position: relative;
    display: flex;
    align-items: center;
  }
  
  .search-icon {
    position: absolute;
    left: var(--space-3);
    color: var(--text-muted);
    pointer-events: none;
  }
  
  .search-input {
    width: 100%;
    padding: var(--space-2) var(--space-4);
    padding-left: calc(var(--space-3) + 16px + var(--space-2));
    padding-right: var(--space-8);
    font-size: var(--text-sm);
    border: 1px solid var(--border-default);
    border-radius: var(--border-radius-md);
    background: var(--surface-raised);
    color: var(--text-primary);
    transition: all var(--transition-fast);
  }
  
  .search-input:focus {
    outline: none;
    border-color: var(--border-focus);
    box-shadow: 0 0 0 3px var(--color-primary-light);
  }
  
  .search-input::placeholder {
    color: var(--text-muted);
  }
  
  .clear-btn {
    position: absolute;
    right: var(--space-2);
    padding: var(--space-1);
    background: none;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    border-radius: var(--border-radius-sm);
    transition: all var(--transition-fast);
  }
  
  .clear-btn:hover {
    background: var(--gray-100);
    color: var(--text-secondary);
  }
  
  .groups-list {
    flex: 1;
    overflow-y: auto;
    padding: var(--space-2);
  }
  
  .file-group {
    margin-bottom: var(--space-1);
  }
  
  .group-header {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    width: 100%;
    padding: var(--space-2) var(--space-3);
    background: var(--gray-50);
    border: none;
    border-radius: var(--border-radius-md);
    cursor: pointer;
    text-align: left;
    transition: background var(--transition-fast);
  }
  
  .group-header:hover {
    background: var(--gray-100);
  }
  
  .expand-icon {
    color: var(--text-tertiary);
    transition: transform var(--transition-fast);
    flex-shrink: 0;
  }
  
  .expand-icon.expanded {
    transform: rotate(90deg);
  }
  
  .group-name {
    flex: 1;
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    color: var(--text-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  
  .group-count {
    padding: 2px 8px;
    background: var(--gray-200);
    border-radius: var(--border-radius-full);
    font-size: 10px;
    font-weight: var(--font-semibold);
    color: var(--text-secondary);
  }
  
  .sequence-list {
    padding: var(--space-1) var(--space-2);
  }
  
  .sequence-item {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
    width: 100%;
    padding: var(--space-2) var(--space-3);
    background: transparent;
    border: none;
    border-radius: var(--border-radius-md);
    cursor: pointer;
    text-align: left;
    transition: all var(--transition-fast);
    box-sizing: border-box;
  }
  
  .sequence-item:hover {
    background: var(--gray-50);
  }
  
  .sequence-item.selected {
    background: var(--color-primary-light);
  }
  
  .seq-main {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-1);
    width: 100%;
  }
  
  .seq-name {
    font-size: var(--text-sm);
    color: var(--text-primary);
    font-weight: var(--font-medium);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    width: 100%;
    min-width: 0;
  }
  
  .sequence-item.selected .seq-name {
    color: var(--color-primary);
  }
  
  .clone-badge {
    padding: 2px 6px;
    background: var(--color-info-light);
    color: var(--color-info);
    border-radius: var(--border-radius-sm);
    font-size: 10px;
    font-weight: var(--font-semibold);
    flex-shrink: 0;
  }
  
  .empty-state {
    padding: var(--space-8);
    text-align: center;
  }
  
  .empty-state p {
    font-size: var(--text-sm);
    color: var(--text-tertiary);
    margin: 0;
  }
</style>

