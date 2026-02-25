<script lang="ts">
  import { wizardState, canProceedStep1, type WizardTimepoint, type WizardCohort } from '../../lib/stores/app';

  let isLoading = false;

  function genId(): string {
    return Math.random().toString(36).slice(2, 8);
  }

  // ── Control cohort management ──

  function initCohorts() {
    wizardState.update(s => {
      if (s.cohorts.length >= 2) return s;
      const disease: WizardCohort = {
        id: genId(), name: 'Disease', type: 'disease',
        timepoints: s.timepoints.length > 0 ? [...s.timepoints] : []
      };
      const control: WizardCohort = {
        id: genId(), name: 'Control', type: 'control', timepoints: []
      };
      return { ...s, hasControlCohort: true, cohorts: [disease, control] };
    });
  }

  function removeControlCohort() {
    wizardState.update(s => {
      const diseaseTps = s.cohorts.find(c => c.type === 'disease')?.timepoints ?? s.timepoints;
      return { ...s, hasControlCohort: false, cohorts: [], timepoints: diseaseTps };
    });
  }

  function toggleControlCohort() {
    if ($wizardState.hasControlCohort) removeControlCohort();
    else initCohorts();
  }

  $: if ($wizardState.hasControlCohort && $wizardState.cohorts.length >= 1) {
    const diseaseTps = $wizardState.cohorts.find(c => c.type === 'disease')?.timepoints ?? [];
    if (diseaseTps !== $wizardState.timepoints) {
      wizardState.update(s => ({ ...s, timepoints: diseaseTps }));
    }
  }

  // ── Folder selection (per timepoint) ──

  async function handleSelectTimepointFolder(tpIndex: number) {
    if (!window.electronAPI) return;
    isLoading = true;
    try {
      const result = await window.electronAPI.selectDirectory();
      if (!result) return;

      const files = result.files.length > 0
        ? result.files.map((f: string) => result.path + '/' + f)
        : (result.detectedTimepoints || []).flatMap((tp: any) => tp.files.map((f: string) => tp.dir + '/' + f));

      wizardState.update(s => {
        const tps = [...s.timepoints];
        tps[tpIndex] = { ...tps[tpIndex], fastaDir: result.path, fastaFiles: files };
        return { ...s, timepoints: tps };
      });
    } catch (error) {
      console.error('Error selecting directory:', error);
    } finally {
      isLoading = false;
    }
  }

  async function handleSelectTimepointFolderForCohort(cohortType: 'disease' | 'control', tpIndex: number) {
    if (!window.electronAPI) return;
    isLoading = true;
    try {
      const result = await window.electronAPI.selectDirectory();
      if (!result) return;

      const files = result.files.length > 0
        ? result.files.map((f: string) => result.path + '/' + f)
        : (result.detectedTimepoints || []).flatMap((tp: any) => tp.files.map((f: string) => tp.dir + '/' + f));

      wizardState.update(s => {
        const cohorts = s.cohorts.map(c => {
          if (c.type !== cohortType) return c;
          const tps = [...c.timepoints];
          tps[tpIndex] = { ...tps[tpIndex], fastaDir: result.path, fastaFiles: files };
          return { ...c, timepoints: tps };
        });
        return { ...s, cohorts };
      });
    } catch (error) {
      console.error('Error selecting directory:', error);
    } finally {
      isLoading = false;
    }
  }

  // ── Timepoint CRUD (single cohort) ──

  function addEmptyTimepoint() {
    wizardState.update(s => ({
      ...s,
      timepoints: [...s.timepoints, { id: genId(), label: `T${s.timepoints.length + 1}`, fastaDir: null, fastaFiles: [] }]
    }));
  }

  function removeTimepoint(index: number) {
    wizardState.update(s => ({ ...s, timepoints: s.timepoints.filter((_, i) => i !== index) }));
  }

  function updateTimepointLabel(index: number, label: string) {
    wizardState.update(s => {
      const tps = [...s.timepoints];
      tps[index] = { ...tps[index], label };
      return { ...s, timepoints: tps };
    });
  }

  // ── Timepoint CRUD (cohort-aware) ──

  function addEmptyTimepointForCohort(cohortType: 'disease' | 'control') {
    wizardState.update(s => {
      const cohorts = s.cohorts.map(c => {
        if (c.type !== cohortType) return c;
        return { ...c, timepoints: [...c.timepoints, { id: genId(), label: `T${c.timepoints.length + 1}`, fastaDir: null, fastaFiles: [] }] };
      });
      return { ...s, cohorts };
    });
  }

  function removeTimepointForCohort(cohortType: 'disease' | 'control', index: number) {
    wizardState.update(s => {
      const cohorts = s.cohorts.map(c => {
        if (c.type !== cohortType) return c;
        return { ...c, timepoints: c.timepoints.filter((_, i) => i !== index) };
      });
      return { ...s, cohorts };
    });
  }

  function updateTimepointLabelForCohort(cohortType: 'disease' | 'control', index: number, label: string) {
    wizardState.update(s => {
      const cohorts = s.cohorts.map(c => {
        if (c.type !== cohortType) return c;
        const tps = [...c.timepoints];
        tps[index] = { ...tps[index], label };
        return { ...c, timepoints: tps };
      });
      return { ...s, cohorts };
    });
  }

  function updateCohortName(cohortType: 'disease' | 'control', name: string) {
    wizardState.update(s => ({
      ...s,
      cohorts: s.cohorts.map(c => c.type === cohortType ? { ...c, name } : c)
    }));
  }

  // ── Other ──

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

  $: diseaseCohort = $wizardState.cohorts.find(c => c.type === 'disease');
  $: controlCohort = $wizardState.cohorts.find(c => c.type === 'control');
</script>

<div class="step-container">
  <header class="step-header">
    <span class="step-number">Step 1</span>
    <h1 class="step-title">Define Study</h1>
    <p class="step-description">
      Name your study, add timepoints, and select FASTA files for each timepoint.
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

    <!-- Control cohort toggle (always visible, prominent) -->
    <div class="control-toggle-section">
      <label class="checkbox-option">
        <input type="checkbox" checked={$wizardState.hasControlCohort} on:change={toggleControlCohort} />
        <div class="checkbox-content">
          <span class="checkbox-label">Add Control Cohort</span>
          <span class="checkbox-description">
            Compare with a control group. Both groups are analyzed independently and compared side-by-side.
          </span>
        </div>
      </label>
    </div>

    {#if !$wizardState.hasControlCohort}
      <!-- ═══ SINGLE COHORT MODE ═══ -->
      <div class="timepoints-section">
        <div class="section-header">
          <h3 class="section-title">Timepoints</h3>
          <button class="btn btn-secondary btn-sm" on:click={addEmptyTimepoint}>+ Add Timepoint</button>
        </div>

        {#if $wizardState.timepoints.length > 0}
          <div class="timepoints-list">
            {#each $wizardState.timepoints as tp, i (tp.id)}
              <div class="tp-card">
                <div class="tp-header">
                  <input type="text" class="tp-label-input" value={tp.label}
                    on:input={(e) => updateTimepointLabel(i, e.currentTarget.value)} placeholder="Timepoint name" />
                  <div class="tp-actions">
                    {#if tp.fastaFiles.length > 0}
                      <span class="tp-badge">{tp.fastaFiles.length} file{tp.fastaFiles.length !== 1 ? 's' : ''}</span>
                    {/if}
                    <button class="btn btn-ghost btn-sm" on:click={() => handleSelectTimepointFolder(i)} disabled={isLoading}>
                      {tp.fastaDir ? 'Change' : 'Select'} Folder
                    </button>
                    <button class="btn btn-ghost btn-sm btn-danger" on:click={() => removeTimepoint(i)} title="Remove timepoint">
                      <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                        <path d="M3 3l8 8M11 3l-8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                      </svg>
                    </button>
                  </div>
                </div>
                {#if tp.fastaDir}<div class="tp-dir">{tp.fastaDir.split('/').pop()}</div>{/if}
                {#if tp.fastaFiles.length > 0}
                  <div class="tp-files">
                    {#each tp.fastaFiles.slice(0, 5) as file}
                      <span class="tp-file">{file.split('/').pop()}</span>
                    {/each}
                    {#if tp.fastaFiles.length > 5}
                      <span class="tp-file more">+{tp.fastaFiles.length - 5} more</span>
                    {/if}
                  </div>
                {:else}
                  <div class="tp-empty">No files selected — click "Select Folder"</div>
                {/if}
              </div>
            {/each}
          </div>
        {:else}
          <div class="empty-hint">
            <p>Add timepoints and select FASTA files for each one.</p>
            <button class="btn btn-primary" on:click={addEmptyTimepoint}>+ Add First Timepoint</button>
          </div>
        {/if}

        {#if $wizardState.timepoints.length > 0}
          <div class="timepoints-summary">
            {$wizardState.timepoints.length} timepoint{$wizardState.timepoints.length !== 1 ? 's' : ''} &middot; {totalFileCount($wizardState.timepoints)} files total
          </div>
        {/if}
      </div>

    {:else}
      <!-- ═══ TWO-COHORT MODE ═══ -->
      {#each ['disease', 'control'] as ctype (ctype)}
        {@const cohort = ctype === 'disease' ? diseaseCohort : controlCohort}
        {@const ct = ctype === 'disease' ? 'disease' : 'control'}
        {#if cohort}
          <div class="cohort-section cohort-{ctype}">
            <div class="cohort-header">
              <div class="cohort-indicator cohort-indicator-{ctype}"></div>
              <input type="text" class="cohort-name-input" value={cohort.name}
                on:input={(e) => updateCohortName(ct, e.currentTarget.value)}
                placeholder="{ctype === 'disease' ? 'Disease Group' : 'Control Group'}" />
              <span class="cohort-type-badge cohort-type-{ctype}">{ctype}</span>
            </div>

            <div class="timepoints-section">
              <div class="section-header">
                <h3 class="section-title">Timepoints</h3>
                <button class="btn btn-secondary btn-sm" on:click={() => addEmptyTimepointForCohort(ct)}>+ Add Timepoint</button>
              </div>

              {#if cohort.timepoints.length > 0}
                <div class="timepoints-list">
                  {#each cohort.timepoints as tp, i (tp.id)}
                    <div class="tp-card">
                      <div class="tp-header">
                        <input type="text" class="tp-label-input" value={tp.label}
                          on:input={(e) => updateTimepointLabelForCohort(ct, i, e.currentTarget.value)} placeholder="Timepoint name" />
                        <div class="tp-actions">
                          {#if tp.fastaFiles.length > 0}
                            <span class="tp-badge">{tp.fastaFiles.length} file{tp.fastaFiles.length !== 1 ? 's' : ''}</span>
                          {/if}
                          <button class="btn btn-ghost btn-sm" on:click={() => handleSelectTimepointFolderForCohort(ct, i)} disabled={isLoading}>
                            {tp.fastaDir ? 'Change' : 'Select'} Folder
                          </button>
                          <button class="btn btn-ghost btn-sm btn-danger" on:click={() => removeTimepointForCohort(ct, i)} title="Remove timepoint">
                            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                              <path d="M3 3l8 8M11 3l-8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                            </svg>
                          </button>
                        </div>
                      </div>
                      {#if tp.fastaDir}<div class="tp-dir">{tp.fastaDir.split('/').pop()}</div>{/if}
                      {#if tp.fastaFiles.length > 0}
                        <div class="tp-files">
                          {#each tp.fastaFiles.slice(0, 5) as file}
                            <span class="tp-file">{file.split('/').pop()}</span>
                          {/each}
                          {#if tp.fastaFiles.length > 5}
                            <span class="tp-file more">+{tp.fastaFiles.length - 5} more</span>
                          {/if}
                        </div>
                      {:else}
                        <div class="tp-empty">No files selected — click "Select Folder"</div>
                      {/if}
                    </div>
                  {/each}
                </div>
              {:else}
                <div class="empty-hint">
                  <button class="btn btn-secondary btn-sm" on:click={() => addEmptyTimepointForCohort(ct)}>+ Add First Timepoint</button>
                </div>
              {/if}

              {#if cohort.timepoints.length > 0}
                <div class="timepoints-summary">
                  {cohort.timepoints.length} timepoint{cohort.timepoints.length !== 1 ? 's' : ''} &middot; {totalFileCount(cohort.timepoints)} files
                </div>
              {/if}
            </div>
          </div>
        {/if}
      {/each}
    {/if}

    <!-- Options -->
    <div class="options-section">
      <h3 class="options-title">Processing Options</h3>
      <label class="checkbox-option">
        <input type="checkbox" checked={$wizardState.cleanFasta} on:change={handleCleanFastaChange} />
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
    <button class="btn btn-primary btn-lg" disabled={!$canProceedStep1} on:click={handleNext}>
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

  .step-header { margin-bottom: var(--space-8); }

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

  .field-group { display: flex; flex-direction: column; gap: var(--space-2); }

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
  .text-input:focus { outline: none; border-color: var(--color-primary); box-shadow: 0 0 0 3px var(--color-primary-muted); }
  .text-input::placeholder { color: var(--text-tertiary); }

  /* ── Timepoints ── */
  .timepoints-section { display: flex; flex-direction: column; gap: var(--space-3); }
  .section-header { display: flex; justify-content: space-between; align-items: center; }

  .section-title {
    font-size: var(--text-sm);
    font-weight: var(--font-semibold);
    color: var(--text-primary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin: 0;
  }

  .timepoints-list { display: flex; flex-direction: column; gap: var(--space-3); }

  .tp-card {
    background: var(--surface-raised);
    border: 1px solid var(--border-light);
    border-radius: var(--radius-md);
    padding: var(--space-4);
  }

  .tp-header { display: flex; align-items: center; gap: var(--space-3); }

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
  .tp-label-input:focus { outline: none; border-color: var(--color-primary); }

  .tp-actions { display: flex; align-items: center; gap: var(--space-2); flex-shrink: 0; }

  .tp-badge { font-size: var(--text-xs); color: var(--color-success); font-weight: var(--font-medium); white-space: nowrap; }
  .btn-danger { color: var(--color-error) !important; }
  .btn-danger:hover { background: rgba(239, 68, 68, 0.08) !important; }

  .tp-dir { font-size: var(--text-xs); color: var(--text-tertiary); margin-top: var(--space-2); padding-left: var(--space-3); }

  .tp-files { display: flex; flex-wrap: wrap; gap: var(--space-1); margin-top: var(--space-2); padding-left: var(--space-3); }

  .tp-file {
    font-size: var(--text-xs);
    color: var(--text-secondary);
    background: var(--gray-100);
    padding: 2px var(--space-2);
    border-radius: var(--radius-sm);
  }
  .tp-file.more { color: var(--text-tertiary); font-style: italic; background: none; }

  .tp-empty {
    font-size: var(--text-xs);
    color: var(--text-tertiary);
    margin-top: var(--space-2);
    padding-left: var(--space-3);
    font-style: italic;
  }

  .timepoints-summary {
    font-size: var(--text-xs);
    color: var(--text-tertiary);
    text-align: right;
    padding-top: var(--space-1);
  }

  .empty-hint { text-align: center; color: var(--text-tertiary); font-size: var(--text-sm); padding: var(--space-6) 0; }
  .empty-hint p { margin: 0 0 var(--space-3) 0; }

  /* ── Cohort sections ── */
  .cohort-section {
    border: 1px solid var(--border-light);
    border-radius: var(--border-radius-lg);
    padding: var(--space-5);
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
    background: var(--surface-raised);
  }
  .cohort-section.cohort-disease { border-left: 3px solid #0066CC; }
  .cohort-section.cohort-control { border-left: 3px solid #7F8C8D; }

  .cohort-header { display: flex; align-items: center; gap: var(--space-3); }

  .cohort-indicator { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
  .cohort-indicator-disease { background: #0066CC; }
  .cohort-indicator-control { background: #7F8C8D; }

  .cohort-name-input {
    flex: 1;
    padding: var(--space-2) var(--space-3);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-sm);
    font-size: var(--text-base);
    font-weight: var(--font-semibold);
    color: var(--text-primary);
    background: transparent;
    min-width: 0;
  }
  .cohort-name-input:focus { outline: none; border-color: var(--color-primary); }

  .cohort-type-badge {
    font-size: var(--text-xs);
    font-weight: var(--font-semibold);
    padding: var(--space-1) var(--space-2);
    border-radius: var(--border-radius-full);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    flex-shrink: 0;
  }
  .cohort-type-disease { background: #E3F2FD; color: #1565C0; }
  .cohort-type-control { background: #F5F5F5; color: #616161; }

  /* ── Control toggle ── */
  .control-toggle-section {
    background: var(--surface-raised);
    border: 1px solid var(--border-light);
    border-radius: var(--border-radius-lg);
    padding: var(--space-4) var(--space-5);
  }

  /* ── Options ── */
  .options-section {
    background: var(--surface-raised);
    border: 1px solid var(--border-light);
    border-radius: var(--border-radius-lg);
    padding: var(--space-5);
  }
  .options-title { font-size: var(--text-sm); font-weight: var(--font-medium); color: var(--text-primary); margin: 0 0 var(--space-4) 0; }

  .checkbox-option { display: flex; gap: var(--space-3); cursor: pointer; }
  .checkbox-option input[type="checkbox"] {
    appearance: none;
    width: 20px; height: 20px;
    border: 2px solid var(--border-default);
    border-radius: var(--border-radius-sm);
    cursor: pointer;
    transition: all var(--transition-fast);
    position: relative;
    flex-shrink: 0;
    margin-top: 2px;
  }
  .checkbox-option input[type="checkbox"]:checked { background: var(--color-primary); border-color: var(--color-primary); }
  .checkbox-option input[type="checkbox"]:checked::after {
    content: '';
    position: absolute;
    left: 6px; top: 2px;
    width: 4px; height: 9px;
    border: solid white;
    border-width: 0 2px 2px 0;
    transform: rotate(45deg);
  }
  .checkbox-content { display: flex; flex-direction: column; gap: var(--space-1); }
  .checkbox-label { font-size: var(--text-sm); font-weight: var(--font-medium); color: var(--text-primary); }
  .checkbox-description { font-size: var(--text-xs); color: var(--text-tertiary); line-height: var(--leading-relaxed); }

  /* Footer */
  .step-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: var(--space-8);
    padding-top: var(--space-6);
    border-top: 1px solid var(--border-light);
  }
  .footer-spacer { flex: 1; }
  .btn svg { margin-left: var(--space-2); }
</style>
