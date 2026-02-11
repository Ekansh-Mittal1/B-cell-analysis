<script lang="ts">
  import { resultsState } from '../../lib/stores/app';

  let selectedCloneId: number | null = null;

  $: covidData = $resultsState.covidMatchData;
  $: selectedClone = covidData?.top_clones.find(c => c.clone_id === selectedCloneId);
  
  // Auto-select first clone if none selected
  $: if (covidData && !selectedCloneId && covidData.top_clones.length > 0) {
    selectedCloneId = covidData.top_clones[0].clone_id;
  }

  function selectClone(cloneId: number) {
    selectedCloneId = cloneId;
  }

  function formatFileList(files: string[]): string {
    if (files.length <= 3) {
      return files.join(', ');
    }
    return `${files.slice(0, 3).join(', ')} (+${files.length - 3} more)`;
  }
</script>

<div class="covid-matching-container">
  {#if !covidData}
    <div class="empty-state">
      <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor">
        <path d="M3 3v18M21 3v18M9 6l6 3-6 3 6 3-6 3" stroke-width="2"/>
      </svg>
      <h3>No COVID Database Matching Data</h3>
      <p>Enable COVID database matching in the wizard to see results here.</p>
    </div>
  {:else}
    <!-- Stats Dashboard -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-value">{covidData.stats.total_clones_analyzed}</div>
        <div class="stat-label">Clones Analyzed</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{covidData.stats.clones_with_high_matches}</div>
        <div class="stat-label">High Matches (≥90%)</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{covidData.stats.clones_with_vh_matches}</div>
        <div class="stat-label">VH Matches Found</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{covidData.stats.database_size.toLocaleString()}</div>
        <div class="stat-label">CoV-AbDab Antibodies</div>
      </div>
    </div>

    <!-- Two-column layout -->
    <div class="results-content">
      <!-- Left: Clone List -->
      <div class="clones-list">
        <div class="list-header">
          <h3>Top 20 Clones</h3>
          <span class="list-count">{covidData.top_clones.length} clones</span>
        </div>
        <div class="list-content">
          {#each covidData.top_clones as clone}
            <button
              class="clone-card"
              class:active={selectedCloneId === clone.clone_id}
              on:click={() => selectClone(clone.clone_id)}
            >
              <div class="clone-header">
                <span class="clone-id">Clone {clone.clone_id}</span>
                <span class="clone-size">{clone.size} seqs</span>
              </div>
              <div class="clone-cdr3">
                <span class="cdr3-label">CDR3:</span>
                <code class="cdr3-seq">{clone.cdr3_aa_raw}</code>
              </div>
              <div class="clone-indicators">
                {#if clone.has_high_vh_match}
                  <span class="indicator match">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                      <path d="M20 6L9 17l-5-5"/>
                    </svg>
                    VH: {clone.vh_matches[0]?.identity.toFixed(1)}%
                  </span>
                {:else if clone.vh_matches.length > 0}
                  <span class="indicator low-match">VH: {clone.vh_matches[0]?.identity.toFixed(1)}%</span>
                {:else}
                  <span class="indicator no-match">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M18 6L6 18M6 6l12 12"/>
                    </svg>
                    VH: No match
                  </span>
                {/if}
                
                {#if clone.has_high_cdr3_match}
                  <span class="indicator match">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                      <path d="M20 6L9 17l-5-5"/>
                    </svg>
                    CDR3: {clone.cdr3_matches[0]?.identity.toFixed(1)}%
                  </span>
                {:else if clone.cdr3_matches.length > 0}
                  <span class="indicator low-match">CDR3: {clone.cdr3_matches[0]?.identity.toFixed(1)}%</span>
                {:else}
                  <span class="indicator no-match">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M18 6L6 18M6 6l12 12"/>
                    </svg>
                    CDR3: No match
                  </span>
                {/if}
              </div>
            </button>
          {/each}
        </div>
      </div>

      <!-- Right: Details Panel -->
      <div class="details-panel">
        {#if selectedClone}
          <!-- Clone Summary -->
          <div class="clone-summary">
            <h3>Clone {selectedClone.clone_id} Summary</h3>
            <div class="summary-grid">
              <div class="summary-item">
                <span class="label">Junction (AIRR):</span>
                <code class="value">{selectedClone.cdr3_aa_raw}</code>
              </div>
              <div class="summary-item">
                <span class="label">CDR3 (IMGT):</span>
                <code class="value">{selectedClone.cdr3_aa}</code>
              </div>
              <div class="summary-item">
                <span class="label">Size:</span>
                <span class="value">{selectedClone.size} sequences</span>
              </div>
              <div class="summary-item">
                <span class="label">V Gene:</span>
                <span class="value">{selectedClone.v_gene}</span>
              </div>
              <div class="summary-item">
                <span class="label">J Gene:</span>
                <span class="value">{selectedClone.j_gene}</span>
              </div>
              <div class="summary-item full-width">
                <span class="label">Files:</span>
                <span class="value">{formatFileList(selectedClone.files)}</span>
              </div>
            </div>
          </div>

          <!-- VH Matches -->
          <div class="matches-section">
            <h3>
              VH Sequence Matches 
              <span class="match-count">({selectedClone.vh_matches.length} found)</span>
            </h3>
            {#if selectedClone.vh_matches.length > 0}
              <div class="matches-list">
                {#each selectedClone.vh_matches as match, idx}
                  <div class="match-card" class:high-match={match.identity >= 90}>
                    <div class="match-header">
                      <div class="match-title">
                        <span class="match-rank">#{idx + 1}</span>
                        <span class="antibody-name">{match.antibody_name}</span>
                        <span class="ab-type">{match.db_info.ab_or_nb}</span>
                      </div>
                      <span class="identity" class:high={match.identity >= 90}>
                        {match.identity.toFixed(2)}%
                      </span>
                    </div>
                    
                    <div class="alignment-viz">
                      <div class="alignment-header">
                        <span>Query:</span>
                        <span class="alignment-stats">
                          {match.alignment.matches}/{match.alignment.length} matches
                        </span>
                      </div>
                      <div class="alignment-rows">
                        <code class="alignment-row query">{match.alignment.query_aligned}</code>
                        <code class="alignment-row match">{match.alignment.match_string}</code>
                        <code class="alignment-row reference">{match.alignment.reference_aligned}</code>
                      </div>
                      <div class="alignment-footer">
                        <span>Reference: {match.antibody_name}</span>
                      </div>
                    </div>

                    <div class="db-info">
                      {#if match.db_info.binds_to}
                        <div class="info-row">
                          <span class="info-label">Binds to:</span>
                          <span class="info-value">{match.db_info.binds_to}</span>
                        </div>
                      {/if}
                      {#if match.db_info.neutralizes}
                        <div class="info-row">
                          <span class="info-label">Neutralizes:</span>
                          <span class="info-value neutralizes">{match.db_info.neutralizes}</span>
                        </div>
                      {/if}
                      {#if match.db_info.v_gene || match.db_info.j_gene}
                        <div class="info-row">
                          <span class="info-label">Genes:</span>
                          <span class="info-value">{match.db_info.v_gene} / {match.db_info.j_gene}</span>
                        </div>
                      {/if}
                      {#if match.db_info.origin}
                        <div class="info-row">
                          <span class="info-label">Origin:</span>
                          <span class="info-value">{match.db_info.origin}</span>
                        </div>
                      {/if}
                    </div>
                  </div>
                {/each}
              </div>
            {:else}
              <div class="no-matches">
                <p>No VH sequences of matching length found in database.</p>
                <p class="hint">CoV-AbDab only compares sequences of identical length.</p>
              </div>
            {/if}
          </div>

          <!-- CDR3 Matches -->
          <div class="matches-section">
            <h3>
              CDR3 Sequence Matches 
              <span class="match-count">({selectedClone.cdr3_matches.length} found)</span>
            </h3>
            {#if selectedClone.cdr3_matches.length > 0}
              <div class="matches-list">
                {#each selectedClone.cdr3_matches as match, idx}
                  <div class="match-card" class:high-match={match.identity >= 90}>
                    <div class="match-header">
                      <div class="match-title">
                        <span class="match-rank">#{idx + 1}</span>
                        <span class="antibody-name">{match.antibody_name}</span>
                        <span class="ab-type">{match.db_info.ab_or_nb}</span>
                      </div>
                      <span class="identity" class:high={match.identity >= 90}>
                        {match.identity.toFixed(2)}%
                      </span>
                    </div>
                    
                    <div class="alignment-viz">
                      <div class="alignment-header">
                        <span>Query (IMGT CDR3):</span>
                        <span class="alignment-stats">
                          {match.alignment.matches}/{match.alignment.length} matches
                        </span>
                      </div>
                      <div class="alignment-rows">
                        <code class="alignment-row query">{match.alignment.query_aligned}</code>
                        <code class="alignment-row match">{match.alignment.match_string}</code>
                        <code class="alignment-row reference">{match.alignment.reference_aligned}</code>
                      </div>
                      <div class="alignment-footer">
                        <span>Reference: {match.antibody_name}</span>
                      </div>
                    </div>

                    <div class="db-info">
                      {#if match.db_info.binds_to}
                        <div class="info-row">
                          <span class="info-label">Binds to:</span>
                          <span class="info-value">{match.db_info.binds_to}</span>
                        </div>
                      {/if}
                      {#if match.db_info.neutralizes}
                        <div class="info-row">
                          <span class="info-label">Neutralizes:</span>
                          <span class="info-value neutralizes">{match.db_info.neutralizes}</span>
                        </div>
                      {/if}
                      {#if match.db_info.v_gene || match.db_info.j_gene}
                        <div class="info-row">
                          <span class="info-label">Genes:</span>
                          <span class="info-value">{match.db_info.v_gene} / {match.db_info.j_gene}</span>
                        </div>
                      {/if}
                      {#if match.db_info.origin}
                        <div class="info-row">
                          <span class="info-label">Origin:</span>
                          <span class="info-value">{match.db_info.origin}</span>
                        </div>
                      {/if}
                    </div>
                  </div>
                {/each}
              </div>
            {:else}
              <div class="no-matches">
                <p>No CDR3 sequences of matching length found in database.</p>
                <p class="hint">CoV-AbDab only compares sequences of identical length.</p>
              </div>
            {/if}
          </div>
        {:else}
          <div class="empty-selection">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
            </svg>
            <h3>Select a Clone</h3>
            <p>Click on a clone from the list to view COVID antibody matches</p>
          </div>
        {/if}
      </div>
    </div>
  {/if}
</div>

<style>
  .covid-matching-container {
    height: 100%;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    background: var(--background-primary);
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: var(--text-muted);
    gap: var(--space-3);
    padding: var(--space-8);
    text-align: center;
  }

  .empty-state svg {
    opacity: 0.3;
  }

  .empty-state h3 {
    margin: 0;
    color: var(--text-primary);
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: var(--space-4);
    padding: var(--space-4);
  }

  .stat-card {
    background: var(--surface-raised);
    padding: var(--space-4);
    border-radius: var(--border-radius-md);
    text-align: center;
    box-shadow: var(--shadow-sm);
  }

  .stat-value {
    font-size: 2rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: var(--space-2);
  }

  .stat-label {
    font-size: 0.875rem;
    color: var(--text-muted);
  }

  .results-content {
    flex: 1;
    display: flex;
    gap: var(--space-4);
    padding: 0 var(--space-4) var(--space-4);
    min-height: 0;
  }

  .clones-list {
    width: 400px;
    background: var(--surface-raised);
    border-radius: var(--border-radius-md);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    box-shadow: var(--shadow-sm);
  }

  .list-header {
    padding: var(--space-4);
    border-bottom: 1px solid var(--border-default);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .list-header h3 {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
  }

  .list-count {
    font-size: 0.875rem;
    color: var(--text-muted);
  }

  .list-content {
    flex: 1;
    overflow-y: auto;
  }

  .clone-card {
    width: 100%;
    padding: var(--space-3);
    border: none;
    border-bottom: 1px solid var(--border-subtle);
    background: transparent;
    cursor: pointer;
    transition: background 0.2s, border-left 0.2s;
    text-align: left;
    font-family: inherit;
    border-left: 3px solid transparent;
  }

  .clone-card:hover {
    background: var(--surface-hover);
  }

  .clone-card.active {
    background: var(--surface-selected);
    border-left-color: var(--accent-primary);
  }

  .clone-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--space-2);
  }

  .clone-id {
    font-weight: 600;
    color: var(--text-primary);
  }

  .clone-size {
    font-size: 0.875rem;
    color: var(--text-muted);
  }

  .clone-cdr3 {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    margin-bottom: var(--space-2);
    font-size: 0.875rem;
  }

  .cdr3-label {
    color: var(--text-muted);
  }

  .cdr3-seq {
    font-family: 'SF Mono', Monaco, monospace;
    font-size: 0.8rem;
    color: var(--text-primary);
    background: var(--surface-base);
    padding: 2px 6px;
    border-radius: var(--border-radius-sm);
  }

  .clone-indicators {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
  }

  .indicator {
    display: flex;
    align-items: center;
    gap: var(--space-1);
    font-size: 0.875rem;
  }

  .indicator.match {
    color: var(--success-text);
    font-weight: 500;
  }

  .indicator.low-match {
    color: var(--text-muted);
  }

  .indicator.no-match {
    color: var(--text-muted);
    opacity: 0.6;
  }

  .indicator svg {
    flex-shrink: 0;
  }

  .details-panel {
    flex: 1;
    background: var(--surface-raised);
    border-radius: var(--border-radius-md);
    overflow-y: auto;
    padding: var(--space-4);
    box-shadow: var(--shadow-sm);
  }

  .empty-selection {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: var(--text-muted);
    gap: var(--space-3);
  }

  .empty-selection svg {
    opacity: 0.3;
  }

  .empty-selection h3 {
    margin: 0;
    color: var(--text-primary);
  }

  .clone-summary {
    background: var(--surface-base);
    padding: var(--space-4);
    border-radius: var(--border-radius-md);
    margin-bottom: var(--space-4);
    border: 1px solid var(--border-default);
  }

  .clone-summary h3 {
    margin: 0 0 var(--space-3) 0;
    font-size: 1.125rem;
  }

  .summary-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: var(--space-3);
  }

  .summary-item {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
  }

  .summary-item.full-width {
    grid-column: 1 / -1;
  }

  .summary-item .label {
    font-size: 0.875rem;
    color: var(--text-muted);
    font-weight: 500;
  }

  .summary-item .value {
    color: var(--text-primary);
  }

  .summary-item code.value {
    font-family: 'SF Mono', Monaco, monospace;
    font-size: 0.9rem;
    background: var(--surface-raised);
    padding: var(--space-2);
    border-radius: var(--border-radius-sm);
    display: block;
  }

  .matches-section {
    margin-bottom: var(--space-6);
  }

  .matches-section h3 {
    margin: 0 0 var(--space-3) 0;
    font-size: 1.125rem;
    display: flex;
    align-items: center;
    gap: var(--space-2);
  }

  .match-count {
    font-size: 0.875rem;
    font-weight: 400;
    color: var(--text-muted);
  }

  .matches-list {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .match-card {
    background: var(--surface-base);
    border: 1px solid var(--border-default);
    border-radius: var(--border-radius-md);
    padding: var(--space-4);
    transition: border-color 0.2s, box-shadow 0.2s;
  }

  .match-card:hover {
    border-color: var(--border-hover);
    box-shadow: var(--shadow-md);
  }

  .match-card.high-match {
    border-color: var(--success-border);
    background: var(--success-bg);
  }

  .match-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--space-3);
  }

  .match-title {
    display: flex;
    align-items: center;
    gap: var(--space-2);
  }

  .match-rank {
    font-size: 0.875rem;
    color: var(--text-muted);
    font-weight: 600;
    min-width: 2rem;
  }

  .antibody-name {
    font-weight: 600;
    font-size: 1rem;
    color: var(--text-primary);
  }

  .ab-type {
    font-size: 0.875rem;
    color: var(--text-muted);
    background: var(--surface-raised);
    padding: 2px 8px;
    border-radius: var(--border-radius-sm);
  }

  .identity {
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--text-primary);
  }

  .identity.high {
    color: var(--success-text);
  }

  .alignment-viz {
    background: var(--surface-raised);
    border: 1px solid var(--border-subtle);
    border-radius: var(--border-radius-sm);
    padding: var(--space-3);
    margin-bottom: var(--space-3);
  }

  .alignment-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--space-2);
    font-size: 0.875rem;
    color: var(--text-muted);
  }

  .alignment-stats {
    font-weight: 500;
  }

  .alignment-rows {
    display: flex;
    flex-direction: column;
    gap: 2px;
    overflow-x: auto;
  }

  .alignment-row {
    font-family: 'SF Mono', Monaco, 'Courier New', monospace;
    font-size: 12px;
    line-height: 1.4;
    white-space: pre;
    display: block;
    padding: var(--space-1) 0;
  }

  .alignment-row.query {
    color: var(--accent-primary);
  }

  .alignment-row.match {
    color: var(--text-muted);
    opacity: 0.7;
  }

  .alignment-row.reference {
    color: var(--text-secondary);
  }

  .alignment-footer {
    margin-top: var(--space-2);
    font-size: 0.875rem;
    color: var(--text-muted);
  }

  .db-info {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .info-row {
    display: flex;
    gap: var(--space-2);
    font-size: 0.875rem;
  }

  .info-label {
    font-weight: 600;
    color: var(--text-muted);
    min-width: 100px;
  }

  .info-value {
    color: var(--text-primary);
    flex: 1;
  }

  .info-value.neutralizes {
    color: var(--success-text);
    font-weight: 500;
  }

  .no-matches {
    background: var(--surface-base);
    border: 1px dashed var(--border-default);
    border-radius: var(--border-radius-md);
    padding: var(--space-6);
    text-align: center;
    color: var(--text-muted);
  }

  .no-matches p {
    margin: var(--space-2) 0;
  }

  .no-matches .hint {
    font-size: 0.875rem;
    font-style: italic;
  }

  /* Scrollbar styling */
  .list-content::-webkit-scrollbar,
  .details-panel::-webkit-scrollbar,
  .alignment-rows::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }

  .list-content::-webkit-scrollbar-track,
  .details-panel::-webkit-scrollbar-track,
  .alignment-rows::-webkit-scrollbar-track {
    background: var(--surface-base);
  }

  .list-content::-webkit-scrollbar-thumb,
  .details-panel::-webkit-scrollbar-thumb,
  .alignment-rows::-webkit-scrollbar-thumb {
    background: var(--border-default);
    border-radius: 4px;
  }

  .list-content::-webkit-scrollbar-thumb:hover,
  .details-panel::-webkit-scrollbar-thumb:hover,
  .alignment-rows::-webkit-scrollbar-thumb:hover {
    background: var(--border-hover);
  }
</style>
