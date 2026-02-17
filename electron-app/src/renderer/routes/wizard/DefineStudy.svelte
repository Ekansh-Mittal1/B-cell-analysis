<script lang="ts">
  import { wizardState, canProceedStep1, type WizardTimepoint } from '../../lib/stores/app';

  let isLoading = false;

  function genId(): string {
    return Math.random().toString(36).slice(2, 8);
  }

  async function handleSelectFolder() {
    if (!window.electronAPI) return;
    isLoading = true;
    try {
      const result = await window.electronAPI.selectDirectory();
      if (!result) return;

      if (result.detectedTimepoints && result.detectedTimepoints.length > 0) {
        // Subdirectories detected as timepoints
        const timepoints: WizardTimepoint[] = result.detectedTimepoints.map(tp => ({
          id: genId(),
          label: tp.label,
          fastaDir: tp.dir,
          fastaFiles: tp.files.map(f => tp.dir + '/' + f)
        }));

        // Auto-fill study name from parent folder name if empty
        const folderName = result.path.split('/').pop() || '';
        wizardState.update(s => ({
          ...s,
          studyName: s.studyName || folderName,
          timepoints
        }));
      } else if (result.files.length > 0) {
        // Flat folder — treat as a single timepoint
        const folderName = result.path.split('/').pop() || '';
        const tp: WizardTimepoint = {
          id: genId(),
          label: 'Baseline',
          fastaDir: result.path,
          fastaFiles: result.files.map(f => result.path + '/' + f)
        };
        wizardState.update(s => ({
          ...s,
          studyName: s.studyName || folderName,
          timepoints: [tp]
        }));
      }
    } catch (error) {
      console.error('Error selecting directory:', error);
    } finally {
      isLoading = false;
    }
  }

  async function handleAddTimepointFolder(tpIndex: number) {
    if (!window.electronAPI) return;
    isLoading = true;
    try {
      const result = await window.electronAPI.selectDirectory();
      if (!result) return;

      const allFiles = result.files.length > 0
        ? result.files.map(f => result.path + '/' + f)
        : [];

      // If it's a folder with timepoint subfolders, flatten them
      if (result.detectedTimepoints && result.detectedTimepoints.length > 0) {
        const flatFiles = result.detectedTimepoints.flatMap(tp =>
          tp.files.map(f => tp.dir + '/' + f)
        );
        wizardState.update(s => {
          const tps = [...s.timepoints];
          tps[tpIndex] = {
            ...tps[tpIndex],
            fastaDir: result.path,
            fastaFiles: flatFiles
          };
          return { ...s, timepoints: tps };
        });
      } else {
        wizardState.update(s => {
          const tps = [...s.timepoints];
          tps[tpIndex] = {
            ...tps[tpIndex],
            fastaDir: result.path,
            fastaFiles: allFiles
          };
          return { ...s, timepoints: tps };
        });
      }
    } catch (error) {
      console.error('Error selecting timepoint directory:', error);
    } finally {
      isLoading = false;
    }
  }

  function addEmptyTimepoint() {
    wizardState.update(s => ({
      ...s,
      timepoints: [
        ...s.timepoints,
        { id: genId(), label: `T${s.timepoints.length + 1}`, fastaDir: null, fastaFiles: [] }
      ]
    }));
  }

  function removeTimepoint(index: number) {
    wizardState.update(s => ({
      ...s,
      timepoints: s.timepoints.filter((_, i) => i !== index)
    }));
  }

  function updateTimepointLabel(index: number, label: string) {
    wizardState.update(s => {
      const tps = [...s.timepoints];
      tps[index] = { ...tps[index], label };
      return { ...s, timepoints: tps };
    });
  }

  function handleStudyNameChange(e: Event) {
    const val = (e.target as HTMLInputElement).value;
    wizardState.update(s => ({ ...s, studyName: val }));
  }

  function handleCleanFastaChange(e: Event) {
    const target = e.target as HTMLInputElement;
    wizardState.update(s => ({ ...s, cleanFasta: target.checked }));
  }

  function handleNext() {
    wizardState.update(s => ({ ...s, step: 2 as 1 | 2 | 3 }));
  }

  function totalFileCount(tps: WizardTimepoint[]): number {
    return tps.reduce((sum, tp) => sum + tp.fastaFiles.length, 0);
  }
</script>

<div class="step-container">
  <header class="step-header">
    <span class="step-number">Step 1</span>
    <h1 class="step-title">Define Study</h1>
    <p class="step-description">
      Name your study and define timepoints. Select a folder with subfolders (auto-detected as timepoints)
      or add timepoints manually.
    </p>
  </header>

  <div class="step-content">
    <!-- Study name -->
    <div class="field-group">
      <label class="field-label" for="study-name">Study Name</label>
      <input
        id="study-name"
        type="text"
        class="text-input"
        placeholder="e.g. Memory Loss, COVID Recovery..."
        value={$wizardState.studyName}
        on:input={handleStudyNameChange}
      />
    </div>

    <!-- Auto-detect from folder -->
    <div class="picker-card">
      <div class="picker-icon">
        <svg width="40" height="40" viewBox="0 0 48 48" fill="none">
          <rect x="4" y="10" width="40" height="32" rx="3" stroke="currentColor" stroke-width="2"/>
          <path d="M4 18h40" stroke="currentColor" stroke-width="2"/>
          <path d="M4 13a3 3 0 0 1 3-3h12l3 4h22a3 3 0 0 1 3 3" stroke="currentColor" stroke-width="2"/>
        </svg>
      </div>

      {#if $wizardState.timepoints.length > 0}
        <div class="selected-info">
          <div class="file-count-badge">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M11.5 4L5.5 10L2.5 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            {$wizardState.timepoints.length} timepoint{$wizardState.timepoints.length !== 1 ? 's' : ''} &middot; {totalFileCount($wizardState.timepoints)} files
          </div>
        </div>
        <button class="btn btn-secondary" on:click={handleSelectFolder} disabled={isLoading}>
          Re-detect from Folder
        </button>
      {:else}
        <button class="btn btn-primary btn-lg" on:click={handleSelectFolder} disabled={isLoading}>
          {#if isLoading}
            Scanning...
          {:else}
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <rect x="2" y="5" width="16" height="12" rx="2" stroke="currentColor" stroke-width="1.5"/>
              <path d="M2 8h16" stroke="currentColor" stroke-width="1.5"/>
              <path d="M2 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2" stroke="currentColor" stroke-width="1.5"/>
            </svg>
            Select Study Folder
          {/if}
        </button>
        <p class="picker-hint">Subfolders will be auto-detected as timepoints</p>
      {/if}
    </div>

    <!-- Timepoint list -->
    {#if $wizardState.timepoints.length > 0}
      <div class="timepoints-section">
        <div class="section-header">
          <h3 class="section-title">Timepoints</h3>
          <button class="btn btn-secondary btn-sm" on:click={addEmptyTimepoint}>
            + Add Timepoint
          </button>
        </div>

        <div class="timepoints-list">
          {#each $wizardState.timepoints as tp, i (tp.id)}
            <div class="tp-card">
              <div class="tp-header">
                <input
                  type="text"
                  class="tp-label-input"
                  value={tp.label}
                  on:input={(e) => updateTimepointLabel(i, e.currentTarget.value)}
                  placeholder="Timepoint name"
                />
                <div class="tp-actions">
                  {#if tp.fastaFiles.length > 0}
                    <span class="tp-badge">{tp.fastaFiles.length} file{tp.fastaFiles.length !== 1 ? 's' : ''}</span>
                  {/if}
                  <button class="btn btn-ghost btn-sm" on:click={() => handleAddTimepointFolder(i)} disabled={isLoading}>
                    {tp.fastaDir ? 'Change' : 'Select'} Folder
                  </button>
                  {#if $wizardState.timepoints.length > 1}
                    <button class="btn btn-ghost btn-sm btn-danger" on:click={() => removeTimepoint(i)} title="Remove timepoint">
                      <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                        <path d="M3 3l8 8M11 3l-8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                      </svg>
                    </button>
                  {/if}
                </div>
              </div>
              {#if tp.fastaDir}
                <div class="tp-dir">{tp.fastaDir.split('/').pop()}</div>
              {/if}
              {#if tp.fastaFiles.length > 0}
                <div class="tp-files">
                  {#each tp.fastaFiles.slice(0, 3) as file}
                    <span class="tp-file">{file.split('/').pop()}</span>
                  {/each}
                  {#if tp.fastaFiles.length > 3}
                    <span class="tp-file more">+{tp.fastaFiles.length - 3} more</span>
                  {/if}
                </div>
              {:else}
                <div class="tp-empty">No files selected — click "Select Folder" above</div>
              {/if}
            </div>
          {/each}
        </div>
      </div>
    {:else}
      <div class="empty-hint">
        <p>Or add timepoints manually:</p>
        <button class="btn btn-secondary" on:click={addEmptyTimepoint}>
          + Add Timepoint
        </button>
      </div>
    {/if}

    <!-- Options -->
    <div class="options-section">
      <h3 class="options-title">Processing Options</h3>
      <label class="checkbox-option">
        <input
          type="checkbox"
          checked={$wizardState.cleanFasta}
          on:change={handleCleanFastaChange}
        />
        <div class="checkbox-content">
          <span class="checkbox-label">Clean FASTA files</span>
          <span class="checkbox-description">
            Remove IMGT formatting and standardize sequence headers.
            Recommended for IMGT-formatted files.
          </span>
        </div>
      </label>
    </div>
  </div>

  <footer class="step-footer">
    <div class="footer-spacer"></div>
    <button
      class="btn btn-primary btn-lg"
      disabled={!$canProceedStep1}
      on:click={handleNext}
    >
      Continue
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <path d="M6 4l4 4-4 4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
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

  /* Study name field */
  .field-group {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .field-label {
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    color: var(--text-primary);
  }

  .text-input {
    padding: var(--space-3) var(--space-4);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
    font-size: var(--text-base);
    color: var(--text-primary);
    background: var(--surface-raised);
    transition: border-color var(--transition-fast);
  }

  .text-input:focus {
    outline: none;
    border-color: var(--color-primary);
    box-shadow: 0 0 0 3px var(--color-primary-muted);
  }

  .text-input::placeholder {
    color: var(--text-tertiary);
  }

  /* Folder picker card */
  .picker-card {
    background: var(--surface-raised);
    border: 2px dashed var(--border-default);
    border-radius: var(--border-radius-lg);
    padding: var(--space-6);
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    transition: border-color var(--transition-fast);
  }

  .picker-card:hover {
    border-color: var(--color-primary-muted);
  }

  .picker-icon {
    color: var(--gray-400);
    margin-bottom: var(--space-3);
  }

  .selected-info {
    margin-bottom: var(--space-3);
  }

  .file-count-badge {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-3);
    background: var(--color-success-light);
    color: var(--color-success);
    border-radius: var(--border-radius-full);
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
  }

  .picker-hint {
    font-size: var(--text-sm);
    color: var(--text-tertiary);
    margin: var(--space-3) 0 0 0;
  }

  /* Timepoints section */
  .timepoints-section {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .section-title {
    font-size: var(--text-sm);
    font-weight: var(--font-semibold);
    color: var(--text-primary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin: 0;
  }

  .timepoints-list {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .tp-card {
    background: var(--surface-raised);
    border: 1px solid var(--border-light);
    border-radius: var(--radius-md);
    padding: var(--space-4);
  }

  .tp-header {
    display: flex;
    align-items: center;
    gap: var(--space-3);
  }

  .tp-label-input {
    flex: 1;
    padding: var(--space-2) var(--space-3);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-sm);
    font-size: var(--text-sm);
    font-weight: var(--font-semibold);
    color: var(--text-primary);
    background: transparent;
    min-width: 0;
  }

  .tp-label-input:focus {
    outline: none;
    border-color: var(--color-primary);
  }

  .tp-actions {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    flex-shrink: 0;
  }

  .tp-badge {
    font-size: var(--text-xs);
    color: var(--color-success);
    font-weight: var(--font-medium);
    white-space: nowrap;
  }

  .btn-danger {
    color: var(--color-error) !important;
  }

  .btn-danger:hover {
    background: rgba(239, 68, 68, 0.08) !important;
  }

  .tp-dir {
    font-size: var(--text-xs);
    color: var(--text-tertiary);
    margin-top: var(--space-2);
    padding-left: var(--space-3);
  }

  .tp-files {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-1);
    margin-top: var(--space-2);
    padding-left: var(--space-3);
  }

  .tp-file {
    font-size: var(--text-xs);
    color: var(--text-secondary);
    background: var(--gray-100);
    padding: 2px var(--space-2);
    border-radius: var(--radius-sm);
  }

  .tp-file.more {
    color: var(--text-tertiary);
    font-style: italic;
    background: none;
  }

  .tp-empty {
    font-size: var(--text-xs);
    color: var(--text-tertiary);
    margin-top: var(--space-2);
    padding-left: var(--space-3);
    font-style: italic;
  }

  .empty-hint {
    text-align: center;
    color: var(--text-tertiary);
    font-size: var(--text-sm);
    padding: var(--space-4) 0;
  }

  .empty-hint p {
    margin: 0 0 var(--space-3) 0;
  }

  /* Options */
  .options-section {
    background: var(--surface-raised);
    border: 1px solid var(--border-light);
    border-radius: var(--border-radius-lg);
    padding: var(--space-5);
  }

  .options-title {
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    color: var(--text-primary);
    margin: 0 0 var(--space-4) 0;
  }

  .checkbox-option {
    display: flex;
    gap: var(--space-3);
    cursor: pointer;
  }

  .checkbox-option input[type="checkbox"] {
    appearance: none;
    width: 20px;
    height: 20px;
    border: 2px solid var(--border-default);
    border-radius: var(--border-radius-sm);
    cursor: pointer;
    transition: all var(--transition-fast);
    position: relative;
    flex-shrink: 0;
    margin-top: 2px;
  }

  .checkbox-option input[type="checkbox"]:checked {
    background: var(--color-primary);
    border-color: var(--color-primary);
  }

  .checkbox-option input[type="checkbox"]:checked::after {
    content: '';
    position: absolute;
    left: 6px;
    top: 2px;
    width: 4px;
    height: 9px;
    border: solid white;
    border-width: 0 2px 2px 0;
    transform: rotate(45deg);
  }

  .checkbox-content {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
  }

  .checkbox-label {
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    color: var(--text-primary);
  }

  .checkbox-description {
    font-size: var(--text-xs);
    color: var(--text-tertiary);
    line-height: var(--leading-relaxed);
  }

  /* Footer */
  .step-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: var(--space-8);
    padding-top: var(--space-6);
    border-top: 1px solid var(--border-light);
  }

  .footer-spacer {
    flex: 1;
  }

  .btn svg {
    margin-left: var(--space-2);
  }
</style>
