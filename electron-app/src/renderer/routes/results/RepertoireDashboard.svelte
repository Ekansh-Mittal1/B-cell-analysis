<script lang="ts">
  import { resultsState, studyDesign, type StudyDesign, type TimepointMapping, type FileGroup, GROUP_COLORS } from '../../lib/stores/app';
  import {
    computeAllMetrics,
    computePerFileMetrics,
    computePerSampleMetrics,
    computeLongitudinalAnalysis,
    type GroupTimepointMetrics,
    type LongitudinalGroupData
  } from '../../lib/utils/repertoire-metrics';
  import DiversityChart from '../../lib/components/visualizations/DiversityChart.svelte';
  import VGeneChart from '../../lib/components/visualizations/VGeneChart.svelte';
  import ExpansionChart from '../../lib/components/visualizations/ExpansionChart.svelte';
  import IsotypeChart from '../../lib/components/visualizations/IsotypeChart.svelte';
  import DiversityTrajectoryChart from '../../lib/components/visualizations/DiversityTrajectoryChart.svelte';
  import ClonalTrackingChart from '../../lib/components/visualizations/ClonalTrackingChart.svelte';
  import ExpansionDynamicsChart from '../../lib/components/visualizations/ExpansionDynamicsChart.svelte';
  import ShmAccumulationChart from '../../lib/components/visualizations/ShmAccumulationChart.svelte';

  function buildDesignFromTimepointMapping(tpMapping: TimepointMapping, fileGroups: FileGroup[]): StudyDesign {
    const fileGroupNames = new Set(fileGroups.map(fg => fg.filename));
    const tpMap = new Map<string, string[]>();
    const tpOrder: string[] = [];
    for (const [stagedFile, entry] of Object.entries(tpMapping)) {
      if (!fileGroupNames.has(stagedFile)) continue;
      if (!tpMap.has(entry.timepoint)) {
        tpMap.set(entry.timepoint, []);
        tpOrder.push(entry.timepoint);
      }
      tpMap.get(entry.timepoint)!.push(stagedFile);
    }
    if (tpMap.size === 0) return { groups: [], unassigned: [] };
    return {
      groups: [{
        id: 'cohort-auto',
        name: 'All Samples',
        color: GROUP_COLORS[0],
        timepoints: tpOrder.map((label, i) => ({
          id: `tp-${i}`,
          label,
          order: i,
          files: tpMap.get(label) || []
        }))
      }],
      unassigned: []
    };
  }

  // ── Cohort awareness ─────────────────────────────────────
  $: hasCohorts = $resultsState.cohortResults.length > 0;
  $: diseaseCohort = $resultsState.cohortResults.find(c => c.cohortType === 'disease') || null;
  $: controlCohort = $resultsState.cohortResults.find(c => c.cohortType === 'control') || null;
  let selectedCohortType: 'disease' | 'control' = 'disease';

  $: activeCohort = hasCohorts
    ? (selectedCohortType === 'control' ? controlCohort : diseaseCohort)
    : null;

  $: activeSequences = activeCohort ? activeCohort.sequences : $resultsState.sequences;
  $: activeFileGroups = activeCohort ? activeCohort.fileGroups : $resultsState.fileGroups;
  $: activeDesign = activeCohort
    ? buildDesignFromTimepointMapping(activeCohort.timepointMapping, activeCohort.fileGroups)
    : $studyDesign;

  // ── Filter state ─────────────────────────────────────────
  let enabledGroups = new Set<string>();
  let enabledTimepoints = new Set<string>();
  let enabledSamples = new Set<string>();
  let initialized = false;
  let lastCohortKey = '';

  // ── Section collapse state ───────────────────────────────
  let perTimepointOpen = true;
  let perSampleComparisonOpen = true;
  let longitudinalOpen = true;

  // ── Derived data ─────────────────────────────────────────
  let allMetrics: GroupTimepointMetrics[] = [];
  let filteredMetrics: GroupTimepointMetrics[] = [];
  let longitudinalData: LongitudinalGroupData[] = [];
  let hasDesign = false;
  let hasLongitudinal = false;

  $: {
    const design = activeDesign;
    hasDesign = design.groups.length > 0;

    const cohortKey = hasCohorts ? selectedCohortType : 'none';
    if (cohortKey !== lastCohortKey) {
      initialized = false;
      lastCohortKey = cohortKey;
    }

    if (hasDesign) {
      allMetrics = computeAllMetrics(design, activeSequences, activeFileGroups);
      longitudinalData = computeLongitudinalAnalysis(design, activeSequences, activeFileGroups);
    } else {
      allMetrics = computePerFileMetrics(activeFileGroups);
      longitudinalData = [];
    }

    hasLongitudinal = longitudinalData.length > 0;

    if (!initialized && allMetrics.length > 0) {
      enabledGroups = new Set(allMetrics.map(m => m.groupId));
      enabledTimepoints = new Set(allMetrics.map(m => m.timepointLabel));
      initialized = true;
    }

    filteredMetrics = allMetrics.filter(m =>
      enabledGroups.has(m.groupId) && enabledTimepoints.has(m.timepointLabel)
    );
  }

  $: filteredTimepointCount = new Set(filteredMetrics.map(m => m.timepointLabel)).size;

  // Per-sample metrics (one per file within selected timepoints)
  $: perSampleMetrics = computePerSampleMetrics(
    hasDesign ? activeDesign : null,
    activeFileGroups,
    enabledGroups,
    enabledTimepoints
  );

  // Sync enabledSamples: remove stale, add newly appeared samples, fallback to all if empty
  let prevValidSampleNames = new Set<string>();
  $: if (perSampleMetrics.length > 0) {
    const valid = new Set(perSampleMetrics.map(m => m.groupName));
    const next = new Set(enabledSamples);
    for (const s of [...next]) { if (!valid.has(s)) next.delete(s); }
    for (const s of valid) { if (!prevValidSampleNames.has(s)) next.add(s); } // new samples default on
    prevValidSampleNames = valid;
    enabledSamples = next.size > 0 ? next : new Set(valid);
  } else {
    prevValidSampleNames = new Set();
    enabledSamples = new Set();
  }

  $: filteredPerSampleMetrics = perSampleMetrics.filter(m => enabledSamples.has(m.groupName));

  function toggleSample(sampleName: string) {
    if (enabledSamples.has(sampleName)) enabledSamples.delete(sampleName);
    else enabledSamples.add(sampleName);
    enabledSamples = new Set(enabledSamples);
  }

  // ── Unique groups and timepoint labels ───────────────────
  $: uniqueGroups = (() => {
    const seen = new Map<string, { id: string; name: string; color: string }>();
    for (const m of allMetrics) {
      if (!seen.has(m.groupId)) {
        seen.set(m.groupId, { id: m.groupId, name: m.groupName, color: m.groupColor });
      }
    }
    return Array.from(seen.values());
  })();

  $: uniqueTimepoints = [...new Set(allMetrics.map(m => m.timepointLabel))];

  function toggleGroup(id: string) {
    if (enabledGroups.has(id)) enabledGroups.delete(id);
    else enabledGroups.add(id);
    enabledGroups = new Set(enabledGroups);
  }

  function toggleTimepoint(label: string) {
    if (enabledTimepoints.has(label)) enabledTimepoints.delete(label);
    else enabledTimepoints.add(label);
    enabledTimepoints = new Set(enabledTimepoints);
  }

  // Summary stats
  $: totalSeqs = filteredMetrics.reduce((a, m) => a + m.diversity.totalSequences, 0);
  $: totalClones = filteredMetrics.reduce((a, m) => a + m.diversity.uniqueClones, 0);
  $: totalFiles = filteredMetrics.reduce((a, m) => {
    if (hasDesign) {
      const d = activeDesign;
      const g = d.groups.find(g => g.id === m.groupId);
      const tp = g?.timepoints.find(t => t.id === m.timepointId);
      return a + (tp?.files.length || 0);
    }
    return a + 1;
  }, 0);
  $: persistentTotal = longitudinalData.reduce((a, g) => a + g.persistentCloneCount, 0);

  import { createEventDispatcher } from 'svelte';
  const dispatch = createEventDispatcher();
  function goToOrganizer() {
    dispatch('switch-tab', 'organizer');
  }

  // Metric tooltips for hover
  const METRIC_TOOLTIPS: Record<string, string> = {
    Sequences: 'Total number of sequences in the sample.',
    Clones: 'Number of unique clonotypes (clusters of related sequences).',
    Shannon: 'Shannon entropy: diversity measure. Higher = more diverse repertoire.',
    Chao1: 'Chao1 richness estimator: predicts total clone diversity from singletons/doubletons.',
    Gini: 'Gini index: clonal inequality. 0 = even distribution, 1 = one clone dominates.',
    Simpson: 'Simpson diversity index: probability two random sequences are from different clones.',
    'Mean SHM': 'Mean somatic hypermutation count per sequence (affinity maturation level).',
    D50: 'Number of largest clones needed to cover 50% of sequences. Lower = more focused response.',
    Productive: 'Percentage of productive (in-frame) sequences.'
  };
</script>

<div class="dashboard">
  <!-- Header -->
  <div class="dash-header">
    <h2 class="dash-title">Repertoire Dashboard</h2>
  </div>

  {#if allMetrics.length === 0}
    <div class="empty-state">
      <p>No data available yet. Run an analysis first.</p>
    </div>
  {:else}
    <!-- Cohort selector (when cohorts exist) -->
    {#if hasCohorts}
      <div class="cohort-selector">
        <span class="cohort-selector-label">Cohort:</span>
        {#if diseaseCohort}
          <button
            class="cohort-toggle"
            class:active={selectedCohortType === 'disease'}
            class:cohort-disease={true}
            on:click={() => selectedCohortType = 'disease'}
          >
            {diseaseCohort.cohortName}
          </button>
        {/if}
        {#if controlCohort}
          <button
            class="cohort-toggle"
            class:active={selectedCohortType === 'control'}
            class:cohort-control={true}
            on:click={() => selectedCohortType = 'control'}
          >
            {controlCohort.cohortName}
          </button>
        {/if}
      </div>
    {/if}

    <!-- Filter bar -->
    <div class="filter-bar">
      {#if !hasCohorts}
        <div class="filter-section">
          <span class="filter-label">Groups:</span>
          {#each uniqueGroups as group (group.id)}
            <button
              class="filter-pill"
              class:active={enabledGroups.has(group.id)}
              on:click={() => toggleGroup(group.id)}
            >
              <span class="pill-dot" style="background: {group.color}"></span>
              {group.name}
            </button>
          {/each}
        </div>
      {/if}
      {#if hasDesign && uniqueTimepoints.length > 1}
        <div class="filter-section">
          <span class="filter-label">Timepoints:</span>
          {#each uniqueTimepoints as tp (tp)}
            <button
              class="filter-pill"
              class:active={enabledTimepoints.has(tp)}
              on:click={() => toggleTimepoint(tp)}
            >
              {tp}
            </button>
          {/each}
        </div>
      {/if}
      {#if !hasDesign && !hasCohorts}
        <button class="organize-link" on:click={goToOrganizer}>
          Organize files into groups for richer comparisons &amp; longitudinal analysis
        </button>
      {/if}
    </div>

    <!-- Summary cards -->
    <div class="summary-row">
      <div class="summary-card">
        <span class="sum-value">{totalSeqs.toLocaleString()}</span>
        <span class="sum-label">Total Sequences</span>
      </div>
      <div class="summary-card">
        <span class="sum-value">{totalClones.toLocaleString()}</span>
        <span class="sum-label">Unique Clones</span>
      </div>
      <div class="summary-card">
        <span class="sum-value">{totalFiles}</span>
        <span class="sum-label">Files</span>
      </div>
      <div class="summary-card">
        <span class="sum-value">{filteredMetrics.length}</span>
        <span class="sum-label">Group &times; Timepoints</span>
      </div>
      {#if hasLongitudinal}
        <div class="summary-card accent">
          <span class="sum-value">{persistentTotal}</span>
          <span class="sum-label">Persistent Clones</span>
        </div>
      {/if}
    </div>

    <!-- ════════════════════════════════════════════════════════
         SECTION 1: Per-Timepoint Metrics
         ════════════════════════════════════════════════════════ -->
    <section class="collapsible-section">
      <button class="section-header" on:click={() => perTimepointOpen = !perTimepointOpen}>
        <span class="section-chevron" class:open={perTimepointOpen}>
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M4 2l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </span>
        <h3 class="section-title">Per-Timepoint Metrics</h3>
        <span class="section-badge">{filteredTimepointCount} timepoint{filteredTimepointCount !== 1 ? 's' : ''}</span>
      </button>

      {#if perTimepointOpen}
        <div class="section-body">
          {#if filteredMetrics.length > 0}
            <!-- Metric cards per timepoint -->
            <div class="metric-cards-scroll">
              {#each filteredMetrics as m}
                <div class="metric-card">
                  <div class="mc-header">
                    <span class="mc-dot" style="background: {m.groupColor}"></span>
                    <span class="mc-label">{m.groupName}{hasDesign ? ` / ${m.timepointLabel}` : ''}</span>
                  </div>
                  <div class="mc-grid">
                    <div class="mc-item" title={METRIC_TOOLTIPS['Sequences']}>
                      <span class="mc-val">{m.diversity.totalSequences}</span>
                      <span class="mc-key">Sequences</span>
                    </div>
                    <div class="mc-item" title={METRIC_TOOLTIPS['Clones']}>
                      <span class="mc-val">{m.diversity.uniqueClones}</span>
                      <span class="mc-key">Clones</span>
                    </div>
                    <div class="mc-item" title={METRIC_TOOLTIPS['Shannon']}>
                      <span class="mc-val">{m.diversity.shannonEntropy.toFixed(2)}</span>
                      <span class="mc-key">Shannon</span>
                    </div>
                    <div class="mc-item" title={METRIC_TOOLTIPS['Chao1']}>
                      <span class="mc-val">{m.diversity.chao1.toFixed(0)}</span>
                      <span class="mc-key">Chao1</span>
                    </div>
                    <div class="mc-item" title={METRIC_TOOLTIPS['Gini']}>
                      <span class="mc-val">{m.diversity.giniIndex.toFixed(3)}</span>
                      <span class="mc-key">Gini</span>
                    </div>
                    <div class="mc-item" title={METRIC_TOOLTIPS['Simpson']}>
                      <span class="mc-val">{m.diversity.simpsonIndex.toFixed(3)}</span>
                      <span class="mc-key">Simpson</span>
                    </div>
                    <div class="mc-item" title={METRIC_TOOLTIPS['Mean SHM']}>
                      <span class="mc-val">{m.diversity.meanSHM.toFixed(1)}</span>
                      <span class="mc-key">Mean SHM</span>
                    </div>
                    <div class="mc-item" title={METRIC_TOOLTIPS['D50']}>
                      <span class="mc-val">{m.diversity.d50}</span>
                      <span class="mc-key">D50</span>
                    </div>
                    <div class="mc-item" title={METRIC_TOOLTIPS['Productive']}>
                      <span class="mc-val">{m.diversity.productivePercent.toFixed(0)}%</span>
                      <span class="mc-key">Productive</span>
                    </div>
                  </div>
                </div>
              {/each}
            </div>

            <!-- Charts -->
            <div class="charts-grid">
              <section class="chart-panel">
                <h3 class="chart-heading">Clonal Diversity &amp; SHM</h3>
                <DiversityChart data={filteredMetrics} />
              </section>
              <section class="chart-panel">
                <h3 class="chart-heading">V-Gene Family Usage</h3>
                <VGeneChart data={filteredMetrics} />
              </section>
              <section class="chart-panel">
                <h3 class="chart-heading">Isotype Distribution</h3>
                <IsotypeChart data={filteredMetrics} />
              </section>
            </div>
            <section class="chart-panel full-width">
              <h3 class="chart-heading">Clonal Expansion (Rank-Abundance)</h3>
              <ExpansionChart data={filteredMetrics} />
            </section>
          {:else}
            <div class="empty-state">
              <p>No data matches the current filters.</p>
            </div>
          {/if}
        </div>
      {/if}
    </section>

    <!-- ════════════════════════════════════════════════════════
         SECTION 2: Per-Sample Comparison
         ════════════════════════════════════════════════════════ -->
    <section class="collapsible-section">
      <button class="section-header" on:click={() => perSampleComparisonOpen = !perSampleComparisonOpen}>
        <span class="section-chevron" class:open={perSampleComparisonOpen}>
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M4 2l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </span>
        <h3 class="section-title">Per-Sample Comparison</h3>
        <span class="section-badge">
          {filteredPerSampleMetrics.length}{perSampleMetrics.length !== filteredPerSampleMetrics.length ? ` of ${perSampleMetrics.length}` : ''} sample{filteredPerSampleMetrics.length !== 1 ? 's' : ''}
        </span>
      </button>

      {#if perSampleComparisonOpen}
        <div class="section-body">
          <p class="section-desc">
            Side-by-side comparison of all metrics for each sample (file) within the selected timepoints above.
          </p>
          {#if perSampleMetrics.length > 0}
            <!-- Sample selector pills -->
            <div class="sample-filter-bar">
              <span class="filter-label">Samples:</span>
              {#each perSampleMetrics as m}
                <button
                  class="filter-pill filter-pill-sm"
                  class:active={enabledSamples.has(m.groupName)}
                  on:click={() => toggleSample(m.groupName)}
                  title={m.groupName}
                >
                  <span class="pill-dot" style="background: {m.groupColor}"></span>
                  <span class="pill-name">{m.groupName}{hasDesign ? ` (${m.timepointLabel})` : ''}</span>
                </button>
              {/each}
            </div>

            <!-- Metric cards per sample -->
            {#if filteredPerSampleMetrics.length > 0}
            <div class="metric-cards-scroll">
              {#each filteredPerSampleMetrics as m}
                <div class="metric-card">
                  <div class="mc-header">
                    <span class="mc-dot" style="background: {m.groupColor}"></span>
                    <span class="mc-label">{m.groupName}{hasDesign ? ` (${m.timepointLabel})` : ''}</span>
                  </div>
                  <div class="mc-grid">
                    <div class="mc-item" title={METRIC_TOOLTIPS['Sequences']}>
                      <span class="mc-val">{m.diversity.totalSequences}</span>
                      <span class="mc-key">Sequences</span>
                    </div>
                    <div class="mc-item" title={METRIC_TOOLTIPS['Clones']}>
                      <span class="mc-val">{m.diversity.uniqueClones}</span>
                      <span class="mc-key">Clones</span>
                    </div>
                    <div class="mc-item" title={METRIC_TOOLTIPS['Shannon']}>
                      <span class="mc-val">{m.diversity.shannonEntropy.toFixed(2)}</span>
                      <span class="mc-key">Shannon</span>
                    </div>
                    <div class="mc-item" title={METRIC_TOOLTIPS['Chao1']}>
                      <span class="mc-val">{m.diversity.chao1.toFixed(0)}</span>
                      <span class="mc-key">Chao1</span>
                    </div>
                    <div class="mc-item" title={METRIC_TOOLTIPS['Gini']}>
                      <span class="mc-val">{m.diversity.giniIndex.toFixed(3)}</span>
                      <span class="mc-key">Gini</span>
                    </div>
                    <div class="mc-item" title={METRIC_TOOLTIPS['Simpson']}>
                      <span class="mc-val">{m.diversity.simpsonIndex.toFixed(3)}</span>
                      <span class="mc-key">Simpson</span>
                    </div>
                    <div class="mc-item" title={METRIC_TOOLTIPS['Mean SHM']}>
                      <span class="mc-val">{m.diversity.meanSHM.toFixed(1)}</span>
                      <span class="mc-key">Mean SHM</span>
                    </div>
                    <div class="mc-item" title={METRIC_TOOLTIPS['D50']}>
                      <span class="mc-val">{m.diversity.d50}</span>
                      <span class="mc-key">D50</span>
                    </div>
                    <div class="mc-item" title={METRIC_TOOLTIPS['Productive']}>
                      <span class="mc-val">{m.diversity.productivePercent.toFixed(0)}%</span>
                      <span class="mc-key">Productive</span>
                    </div>
                  </div>
                </div>
              {/each}
            </div>

            <!-- Same charts as per-timepoint, but with per-sample data -->
            <div class="charts-grid">
              <section class="chart-panel">
                <h3 class="chart-heading">Clonal Diversity &amp; SHM (per sample)</h3>
                <DiversityChart data={filteredPerSampleMetrics} />
              </section>
              <section class="chart-panel">
                <h3 class="chart-heading">V-Gene Family Usage (per sample)</h3>
                <VGeneChart data={filteredPerSampleMetrics} />
              </section>
              <section class="chart-panel">
                <h3 class="chart-heading">Isotype Distribution (per sample)</h3>
                <IsotypeChart data={filteredPerSampleMetrics} />
              </section>
            </div>
            <section class="chart-panel full-width">
              <h3 class="chart-heading">Clonal Expansion / Rank-Abundance (per sample)</h3>
              <ExpansionChart data={filteredPerSampleMetrics} />
            </section>
            {:else}
              <div class="empty-state">
                <p>Select at least one sample above to view metrics and charts.</p>
              </div>
            {/if}
          {:else}
            <div class="empty-state">
              <p>No samples match the current timepoint and group filters.</p>
            </div>
          {/if}
        </div>
      {/if}
    </section>

    <!-- ════════════════════════════════════════════════════════
         SECTION 3: Longitudinal Analysis
         ════════════════════════════════════════════════════════ -->
    <section class="collapsible-section">
      <button class="section-header" on:click={() => longitudinalOpen = !longitudinalOpen}>
        <span class="section-chevron" class:open={longitudinalOpen}>
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M4 2l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </span>
        <h3 class="section-title">Longitudinal Analysis</h3>
        {#if hasLongitudinal}
          <span class="section-badge">{longitudinalData.length} group{longitudinalData.length !== 1 ? 's' : ''}</span>
        {:else}
          <span class="section-badge muted">requires &ge;2 timepoints</span>
        {/if}
      </button>

      {#if longitudinalOpen}
        <div class="section-body">
          {#if hasLongitudinal}
            <!-- Diversity trajectory -->
            <section class="chart-panel full-width">
              <h3 class="chart-heading">Diversity &amp; SHM Trajectory</h3>
              <p class="chart-desc">How repertoire diversity and mutation load change over time per group.</p>
              <DiversityTrajectoryChart data={longitudinalData} />
            </section>

            <!-- Clonal tracking -->
            <section class="chart-panel full-width">
              <h3 class="chart-heading">Clonal Tracking</h3>
              <p class="chart-desc">Top clones tracked across timepoints. Solid lines = persistent clones (present at all timepoints). Dashed = transient.</p>
              <ClonalTrackingChart data={longitudinalData} />
            </section>

            <!-- Expansion dynamics -->
            <section class="chart-panel full-width">
              <h3 class="chart-heading">Expansion Dynamics</h3>
              <p class="chart-desc">Which clones expand, contract, persist, or appear transiently across timepoints.</p>
              <ExpansionDynamicsChart data={longitudinalData} />
            </section>

            <!-- SHM accumulation -->
            <section class="chart-panel full-width">
              <h3 class="chart-heading">SHM Accumulation</h3>
              <p class="chart-desc">Do persistent clones accumulate somatic hypermutations over time? Lines show mean SHM per clone across timepoints.</p>
              <ShmAccumulationChart data={longitudinalData} />
            </section>
          {:else}
            <div class="empty-state longitudinal-prompt">
              <div class="prompt-icon">
                <svg width="36" height="36" viewBox="0 0 36 36" fill="none">
                  <path d="M6 26L14 18L20 24L30 10" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
                  <circle cx="14" cy="18" r="2.5" fill="currentColor"/>
                  <circle cx="20" cy="24" r="2.5" fill="currentColor"/>
                  <circle cx="30" cy="10" r="2.5" fill="currentColor"/>
                </svg>
              </div>
              <p class="prompt-title">Longitudinal analysis requires groups with multiple timepoints</p>
              <p class="prompt-desc">
                Use the <button class="inline-link" on:click={goToOrganizer}>Organize tab</button> to assign files to groups and define timepoints within each group. Once a group has at least two timepoints, clonal tracking, expansion dynamics, SHM accumulation, and diversity trajectory will appear here.
              </p>
            </div>
          {/if}
        </div>
      {/if}
    </section>
  {/if}
</div>

<style>
  .dashboard {
    padding: var(--space-6);
    overflow-y: auto;
    height: 100%;
  }

  .dash-header {
    margin-bottom: var(--space-4);
  }
  .dash-title {
    margin: 0;
    font-size: var(--text-xl);
    font-weight: var(--font-semibold);
    color: var(--text-primary);
  }

  /* ── Cohort selector ─────────── */
  .cohort-selector {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    margin-bottom: var(--space-3);
  }
  .cohort-selector-label {
    font-size: var(--text-xs);
    font-weight: var(--font-semibold);
    text-transform: uppercase;
    letter-spacing: var(--tracking-wide);
    color: var(--text-tertiary);
  }
  .cohort-toggle {
    padding: 5px 16px;
    border: 2px solid var(--border-light);
    border-radius: var(--border-radius-full);
    background: var(--surface-raised);
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    color: var(--text-secondary);
    cursor: pointer;
    transition: all var(--transition-fast);
  }
  .cohort-toggle.active.cohort-disease {
    border-color: #1565C0;
    background: #E3F2FD;
    color: #1565C0;
    font-weight: var(--font-semibold);
  }
  .cohort-toggle.active.cohort-control {
    border-color: #616161;
    background: #F5F5F5;
    color: #424242;
    font-weight: var(--font-semibold);
  }
  .cohort-toggle:hover:not(.active) {
    border-color: var(--gray-300);
    background: var(--gray-50);
  }

  /* ── Filter bar ──────────────── */
  .filter-bar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--space-4);
    margin-bottom: var(--space-5);
    padding: var(--space-3) var(--space-4);
    background: var(--gray-50);
    border-radius: var(--border-radius-md);
    border: 1px solid var(--border-light);
  }
  .filter-section {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    flex-wrap: wrap;
  }
  .filter-label {
    font-size: var(--text-xs);
    font-weight: var(--font-semibold);
    text-transform: uppercase;
    letter-spacing: var(--tracking-wide);
    color: var(--text-tertiary);
    margin-right: var(--space-1);
  }
  .filter-pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 4px 12px;
    border: 1px solid var(--border-light);
    border-radius: var(--border-radius-full);
    background: var(--surface-raised);
    font-size: var(--text-xs);
    font-weight: var(--font-medium);
    color: var(--text-secondary);
    cursor: pointer;
    transition: all var(--transition-fast);
  }
  .filter-pill.active {
    border-color: var(--color-primary-muted);
    background: var(--color-primary-light);
    color: var(--color-primary);
  }
  .pill-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }
  .organize-link {
    background: none;
    border: none;
    color: var(--text-link);
    font-size: var(--text-xs);
    cursor: pointer;
    text-decoration: underline;
    padding: 0;
  }
  .organize-link:hover { opacity: 0.8; }

  /* ── Per-sample filter bar (within section) ────── */
  .sample-filter-bar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--space-2);
    margin-bottom: var(--space-4);
    padding: var(--space-2) 0;
  }
  .sample-filter-bar .filter-label {
    margin-right: 0;
  }
  .filter-pill-sm {
    padding: 3px 10px;
    font-size: 11px;
  }
  .filter-pill-sm .pill-name {
    max-width: 140px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* ── Summary ─────────────────── */
  .summary-row {
    display: flex;
    gap: var(--space-3);
    margin-bottom: var(--space-5);
    flex-wrap: wrap;
  }
  .summary-card {
    flex: 1;
    min-width: 100px;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: var(--space-3) var(--space-4);
    background: var(--surface-raised);
    border: 1px solid var(--border-light);
    border-radius: var(--border-radius-md);
  }
  .summary-card.accent {
    border-color: var(--color-primary-muted);
    background: var(--color-primary-light);
  }
  .sum-value {
    font-size: var(--text-xl);
    font-weight: var(--font-bold);
    color: var(--text-primary);
  }
  .sum-label {
    font-size: var(--text-xs);
    color: var(--text-tertiary);
    margin-top: var(--space-1);
  }

  /* ── Collapsible sections ────── */
  .collapsible-section {
    margin-bottom: var(--space-4);
    border: 1px solid var(--border-light);
    border-radius: var(--border-radius-md);
    background: var(--surface-raised);
    overflow: hidden;
  }
  .section-header {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    width: 100%;
    padding: var(--space-3) var(--space-4);
    background: var(--gray-50);
    border: none;
    border-bottom: 1px solid var(--border-light);
    cursor: pointer;
    text-align: left;
    transition: background var(--transition-fast);
  }
  .section-header:hover {
    background: var(--gray-100);
  }
  .section-chevron {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 20px;
    height: 20px;
    color: var(--text-tertiary);
    transition: transform 0.2s ease;
    transform: rotate(0deg);
  }
  .section-chevron.open {
    transform: rotate(90deg);
  }
  .section-title {
    margin: 0;
    font-size: var(--text-sm);
    font-weight: var(--font-semibold);
    color: var(--text-primary);
    flex: 1;
  }
  .section-badge {
    font-size: var(--text-xs);
    color: var(--color-primary);
    background: var(--color-primary-light);
    padding: 2px 8px;
    border-radius: var(--border-radius-full);
    font-weight: var(--font-medium);
  }
  .section-badge.muted {
    color: var(--text-tertiary);
    background: var(--gray-100);
  }
  .section-body {
    padding: var(--space-4);
  }
  .section-desc {
    font-size: var(--text-sm);
    color: var(--text-tertiary);
    margin: 0 0 var(--space-4) 0;
    line-height: var(--leading-relaxed);
  }

  /* ── Per-timepoint metric cards ─── */
  .metric-cards-scroll {
    display: flex;
    gap: var(--space-3);
    overflow-x: auto;
    padding-bottom: var(--space-3);
    margin-bottom: var(--space-4);
  }
  .metric-card {
    flex: 0 0 auto;
    min-width: 220px;
    max-width: 280px;
    border: 1px solid var(--border-light);
    border-radius: var(--border-radius-md);
    padding: var(--space-3);
    background: var(--surface-raised);
  }
  .mc-header {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    margin-bottom: var(--space-2);
  }
  .mc-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .mc-label {
    font-size: var(--text-xs);
    font-weight: var(--font-semibold);
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .mc-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 6px 10px;
  }
  .mc-item {
    display: flex;
    flex-direction: column;
    cursor: help;
  }
  .mc-val {
    font-size: var(--text-sm);
    font-weight: var(--font-bold);
    color: var(--text-primary);
    font-feature-settings: 'tnum' 1;
  }
  .mc-key {
    font-size: 10px;
    color: var(--text-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  /* ── Charts ──────────────────── */
  .charts-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--space-4);
    margin-bottom: var(--space-4);
  }
  .chart-panel {
    background: var(--surface-raised);
    border: 1px solid var(--border-light);
    border-radius: var(--border-radius-md);
    padding: var(--space-4);
    overflow: hidden;
  }
  .chart-panel.full-width {
    margin-bottom: var(--space-4);
  }
  .chart-heading {
    margin: 0 0 var(--space-1) 0;
    font-size: var(--text-sm);
    font-weight: var(--font-semibold);
    color: var(--text-primary);
  }
  .chart-desc {
    margin: 0 0 var(--space-3) 0;
    font-size: var(--text-xs);
    color: var(--text-tertiary);
    line-height: var(--leading-relaxed);
  }

  /* ── Empty state / prompt ────── */
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 120px;
    color: var(--text-tertiary);
    font-size: var(--text-sm);
  }
  .longitudinal-prompt {
    padding: var(--space-6) var(--space-4);
    text-align: center;
  }
  .prompt-icon {
    color: var(--gray-300);
    margin-bottom: var(--space-3);
  }
  .prompt-title {
    font-size: var(--text-sm);
    font-weight: var(--font-semibold);
    color: var(--text-secondary);
    margin: 0 0 var(--space-2) 0;
  }
  .prompt-desc {
    font-size: var(--text-xs);
    color: var(--text-tertiary);
    max-width: 400px;
    margin: 0 auto;
    line-height: var(--leading-relaxed);
  }
  .inline-link {
    background: none;
    border: none;
    color: var(--text-link);
    font-size: inherit;
    cursor: pointer;
    text-decoration: underline;
    padding: 0;
  }
  .inline-link:hover { opacity: 0.8; }
</style>
