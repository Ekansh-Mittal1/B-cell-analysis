<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  
  export let calculatedValue: number;
  
  const dispatch = createEventDispatcher<{
    confirm: number;
    cancel: void;
  }>();
  
  let inputValue = calculatedValue.toFixed(4);
  let error = '';
  
  function handleSubmit() {
    const parsed = parseFloat(inputValue);
    if (isNaN(parsed) || parsed < 0 || parsed > 1) {
      error = 'Please enter a valid number between 0 and 1 (inclusive)';
      return;
    }
    dispatch('confirm', parsed);
  }
  
  function handleUseCalculated() {
    dispatch('confirm', calculatedValue);
  }
  
  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') {
      handleSubmit();
    } else if (e.key === 'Escape') {
      handleUseCalculated();
    }
  }
</script>

<div class="modal-overlay" on:keydown={handleKeydown}>
  <div class="modal" role="dialog" aria-modal="true">
    <div class="modal-header">
      <h2 class="modal-title">Distance Threshold</h2>
    </div>
    
    <div class="modal-body">
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
          bind:value={inputValue}
          placeholder="0.0 to 1.0"
          autofocus
        />
        {#if error}
          <p class="error-text">{error}</p>
        {/if}
      </div>
    </div>
    
    <div class="modal-actions">
      <button class="btn btn-secondary" on:click={handleUseCalculated}>
        Use Calculated
      </button>
      <button class="btn btn-primary" on:click={handleSubmit}>
        Apply Custom Value
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
    z-index: 1000; /* Higher than progress overlay */
    animation: fadeIn var(--transition-fast) ease-out;
  }
  
  .modal {
    background: var(--surface-raised);
    border-radius: var(--border-radius-xl);
    padding: var(--space-6);
    max-width: 440px;
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
    margin: 0;
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
    from {
      opacity: 0;
      transform: translateY(10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
</style>

