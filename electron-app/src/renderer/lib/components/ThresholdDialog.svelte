<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  
  /** Single-value mode (legacy/single-cohort) */
  export let calculatedValue: number = 0;
  
  /** Multi-timepoint mode: array of {label, calculated} */
  export let timepointThresholds: { label: string; calculated: number }[] = [];
  
  const dispatch = createEventDispatcher<{
    confirm: number | Record<string, number>;
    cancel: void;
  }>();
  
  // Determine mode
  $: isMulti = timepointThresholds.length > 0 && timepointThresholds[0]?.label !== '_global';
  
  // Single-value state
  let singleInput = calculatedValue.toFixed(4);
  
  // Multi-value state: one input per timepoint
  let tpInputs: Record<string, string> = {};
  $: {
    if (isMulti && Object.keys(tpInputs).length === 0) {
      for (const tp of timepointThresholds) {
        tpInputs[tp.label] = tp.calculated.toFixed(4);
      }
      tpInputs = { ...tpInputs };
    }
  }
  
  let applyToAll = false;
  let applyAllValue = '';
  let error = '';
  
  function handleSubmit() {
    error = '';
    
    if (isMulti) {
      const thresholds: Record<string, number> = {};
      
      if (applyToAll) {
        const parsed = parseFloat(applyAllValue);
        if (isNaN(parsed) || parsed < 0 || parsed > 1) {
          error = 'Please enter a valid number between 0 and 1';
          return;
        }
        for (const tp of timepointThresholds) {
          thresholds[tp.label] = parsed;
        }
      } else {
        for (const tp of timepointThresholds) {
          const parsed = parseFloat(tpInputs[tp.label] || '');
          if (isNaN(parsed) || parsed < 0 || parsed > 1) {
            error = `Invalid value for ${tp.label}: must be between 0 and 1`;
            return;
          }
          thresholds[tp.label] = parsed;
        }
      }
      
      dispatch('confirm', thresholds);
    } else {
      const parsed = parseFloat(singleInput);
      if (isNaN(parsed) || parsed < 0 || parsed > 1) {
        error = 'Please enter a valid number between 0 and 1';
        return;
      }
      dispatch('confirm', parsed);
    }
  }
  
  function handleUseCalculated() {
    if (isMulti) {
      const thresholds: Record<string, number> = {};
      for (const tp of timepointThresholds) {
        thresholds[tp.label] = tp.calculated;
      }
      dispatch('confirm', thresholds);
    } else {
      dispatch('confirm', calculatedValue);
    }
  }
  
  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') handleSubmit();
    else if (e.key === 'Escape') handleUseCalculated();
  }
</script>

<div class="modal-overlay" on:keydown={handleKeydown}>
  <div class="modal" role="dialog" aria-modal="true">
    <div class="modal-header">
      <h2 class="modal-title">Distance Threshold</h2>
    </div>
    
    <div class="modal-body">
      {#if isMulti}
        <p class="calculated-info">
          Calculated thresholds per timepoint for clone definition:
        </p>
        
        <div class="tp-table">
          <div class="tp-row tp-header-row">
            <span class="tp-cell tp-label-cell">Timepoint</span>
            <span class="tp-cell tp-calc-cell">Calculated</span>
            <span class="tp-cell tp-input-cell">Custom</span>
          </div>
          {#each timepointThresholds as tp (tp.label)}
            <div class="tp-row">
              <span class="tp-cell tp-label-cell tp-name">{tp.label}</span>
              <span class="tp-cell tp-calc-cell tp-value">{tp.calculated.toFixed(4)}</span>
              <span class="tp-cell tp-input-cell">
                <input
                  type="text"
                  class="tp-input"
                  bind:value={tpInputs[tp.label]}
                  placeholder={tp.calculated.toFixed(4)}
                  disabled={applyToAll}
                />
              </span>
            </div>
          {/each}
        </div>
        
        <label class="apply-all-label">
          <input type="checkbox" bind:checked={applyToAll} />
          Apply a single value to all timepoints:
          {#if applyToAll}
            <input
              type="text"
              class="apply-all-input"
              bind:value={applyAllValue}
              placeholder="0.0 to 1.0"
              autofocus
            />
          {/if}
        </label>
      {:else}
        <p class="calculated-info">
          The calculated optimal threshold for clone definition is:
        </p>
        <div class="calculated-value">
          {calculatedValue.toFixed(4)}
        </div>
        <div class="input-section">
          <label for="threshold-input" class="input-label">
            Enter a custom value (0 to 1) or use the calculated threshold:
          </label>
          <input
            id="threshold-input"
            type="text"
            class="input"
            bind:value={singleInput}
            placeholder="0.0 to 1.0"
            autofocus
          />
        </div>
      {/if}
      
      {#if error}
        <p class="error-text">{error}</p>
      {/if}
    </div>
    
    <div class="modal-actions">
      <button class="btn btn-secondary" on:click={handleUseCalculated}>
        Use Calculated
      </button>
      <button class="btn btn-primary" on:click={handleSubmit}>
        Apply
      </button>
    </div>
  </div>
</div>

<style>
  .modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    animation: fadeIn var(--transition-fast) ease-out;
  }
  
  .modal {
    background: var(--surface-raised);
    border-radius: var(--border-radius-xl);
    padding: var(--space-6);
    max-width: 540px;
    width: 90%;
    box-shadow: var(--shadow-xl);
    animation: slideUp var(--transition-normal) ease-out;
  }
  
  .modal-header {
    margin-bottom: var(--space-4);
  }
  
  .modal-title {
    font-size: var(--text-xl);
    font-weight: var(--font-semibold);
    color: var(--text-primary);
    margin: 0;
  }
  
  .modal-body {
    margin-bottom: var(--space-6);
  }
  
  .calculated-info {
    font-size: var(--text-sm);
    color: var(--text-secondary);
    margin: 0 0 var(--space-3) 0;
  }
  
  .calculated-value {
    font-family: var(--font-mono);
    font-size: var(--text-2xl);
    font-weight: var(--font-bold);
    color: var(--color-primary);
    background: var(--color-primary-light);
    padding: var(--space-3) var(--space-4);
    border-radius: var(--border-radius-md);
    text-align: center;
    margin-bottom: var(--space-5);
  }
  
  .input-section {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }
  
  .input-label {
    font-size: var(--text-sm);
    color: var(--text-secondary);
  }
  
  .error-text {
    font-size: var(--text-xs);
    color: var(--color-error);
    margin: var(--space-2) 0 0;
  }
  
  .tp-table {
    display: flex;
    flex-direction: column;
    gap: 1px;
    background: var(--gray-200);
    border-radius: var(--border-radius-md);
    overflow: hidden;
    margin-bottom: var(--space-4);
  }
  
  .tp-row {
    display: grid;
    grid-template-columns: 1fr 100px 120px;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-3);
    background: var(--surface-primary);
    align-items: center;
  }
  
  .tp-header-row {
    background: var(--gray-50);
    font-size: var(--text-xs);
    font-weight: var(--font-semibold);
    color: var(--text-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  
  .tp-name {
    font-weight: var(--font-medium);
    color: var(--text-primary);
  }
  
  .tp-value {
    font-family: var(--font-mono);
    font-size: var(--text-sm);
    color: var(--color-primary);
    font-weight: var(--font-semibold);
  }
  
  .tp-input {
    width: 100%;
    padding: var(--space-1) var(--space-2);
    border: 1px solid var(--gray-300);
    border-radius: var(--border-radius-sm);
    font-family: var(--font-mono);
    font-size: var(--text-sm);
    background: var(--surface-primary);
    color: var(--text-primary);
  }
  
  .tp-input:disabled {
    opacity: 0.4;
    background: var(--gray-100);
  }
  
  .apply-all-label {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    font-size: var(--text-sm);
    color: var(--text-secondary);
    cursor: pointer;
  }
  
  .apply-all-input {
    width: 80px;
    padding: var(--space-1) var(--space-2);
    border: 1px solid var(--gray-300);
    border-radius: var(--border-radius-sm);
    font-family: var(--font-mono);
    font-size: var(--text-sm);
  }
  
  .modal-actions {
    display: flex;
    gap: var(--space-3);
    justify-content: flex-end;
  }
  
  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }
  
  @keyframes slideUp {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }
</style>
