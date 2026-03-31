<script lang="ts">
  import { resultsState, studyDesign, type StudyDesign, type TimepointMapping, type FileGroup, type CohortResults, GROUP_COLORS } from '../../lib/stores/app';
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

  // ── Designs per cohort ──────────────────────────────────
  $: diseaseDesign = diseaseCohort
    ? buildDesignFromTimepointMapping(diseaseCohort.timepointMapping, diseaseCohort.fileGroups)
    : { groups: [], unassigned: [] } as StudyDesign;
  $: controlDesign = controlCohort
    ? buildDesignFromTimepointMapping(controlCohort.timepointMapping, controlCohort.fileGroups)
    : { groups: [], unassigned: [] } as StudyDesign;

  // Single-cohort mode (no control)
  $: singleDesign = hasCohorts ? diseaseDesign : $studyDesign;
  $: singleFileGroups = hasCohorts ? (diseaseCohort?.fileGroups ?? []) : $resultsState.fileGroups;
  $: singleSequences = hasCohorts ? (diseaseCohort?.sequences ?? []) : $resultsState.sequences;

  // ── Section collapse state ───────────────────────────────
  let perTimepointOpen = true;
  let perSampleComparisonOpen = true;
  let longitudinalOpen = true;

  // ── Disease metrics ──────────────────────────────────────
  let diseaseMetrics: GroupTimepointMetrics[] = [];
  let diseaseLongitudinal: LongitudinalGroupData[] = [];
  let diseaseHasDesign = false;

  $: {
    if (hasCohorts && diseaseCohort) {
      diseaseHasDesign = diseaseDesign.groups.length > 0;
      diseaseMetrics = diseaseHasDesign
        ? computeAllMetrics(diseaseDesign, diseaseCohort.sequences, diseaseCohort.fileGroups)
        : computePerFileMetrics(diseaseCohort.fileGroups);
      diseaseLongitudinal = diseaseHasDesign
        ? computeLongitudinalAnalysis(diseaseDesign, diseaseCohort.sequences, diseaseCohort.fileGroups)
        : [];
    } else if (!hasCohorts) {
      diseaseHasDesign = singleDesign.groups.length > 0;
      diseaseMetrics = diseaseHasDesign
        ? computeAllMetrics(singleDesign, singleSequences, singleFileGroups)
        : computePerFileMetrics(singleFileGroups);
      diseaseLongitudinal = diseaseHasDesign
        ? computeLongitudinalAnalysis(singleDesign, singleSequences, singleFileGroups)
        : [];
    }
  }

  // ── Control metrics (only when cohorts exist) ────────────
  let controlMetrics: GroupTimepointMetrics[] = [];
  let controlLongitudinal: LongitudinalGroupData[] = [];
  let controlHasDesign = false;

  $: {
    if (hasCohorts && controlCohort) {
      controlHasDesign = controlDesign.groups.length > 0;
      controlMetrics = controlHasDesign
        ? computeAllMetrics(controlDesign, controlCohort.sequences, controlCohort.fileGroups)
        : computePerFileMetrics(controlCohort.fileGroups);
      controlLongitudinal = controlHasDesign
        ? computeLongitudinalAnalysis(controlDesign, controlCohort.sequences, controlCohort.fileGroups)
        : [];
    } else {
      controlMetrics = [];
      controlLongitudinal = [];
    }
  }

  // ── Timepoint filters (independent per cohort) ───────────
  let diseaseEnabledTimepoints = new Set<string>();
  let controlEnabledTimepoints = new Set<string>();
  let diseaseTimepointsInit = false;
  let controlTimepointsInit = false;

  $: diseaseUniqueTimepoints = [...new Set(diseaseMetrics.map(m => m.timepointLabel))];
  $: controlUniqueTimepoints = [...new Set(controlMetrics.map(m => m.timepointLabel))];

  $: {
    if (!diseaseTimepointsInit && diseaseMetrics.length > 0) {
      diseaseEnabledTimepoints = new Set(diseaseMetrics.map(m => m.timepointLabel));
      diseaseTimepointsInit = true;
    }
  }
  $: {
    if (!controlTimepointsInit && controlMetrics.length > 0) {
      controlEnabledTimepoints = new Set(controlMetrics.map(m => m.timepointLabel));
      controlTimepointsInit = true;
    }
  }

  function toggleDiseaseTimepoint(label: string) {
    if (diseaseEnabledTimepoints.has(label)) diseaseEnabledTimepoints.delete(label);
    else diseaseEnabledTimepoints.add(label);
    diseaseEnabledTimepoints = new Set(diseaseEnabledTimepoints);
  }
  function toggleControlTimepoint(label: string) {
    if (controlEnabledTimepoints.has(label)) controlEnabledTimepoints.delete(label);
    else controlEnabledTimepoints.add(label);
    controlEnabledTimepoints = new Set(controlEnabledTimepoints);
  }

  $: filteredDiseaseMetrics = diseaseMetrics.filter(m => diseaseEnabledTimepoints.has(m.timepointLabel));
  $: filteredControlMetrics = controlMetrics.filter(m => controlEnabledTimepoints.has(m.timepointLabel));

  // ── Summary stats ────────────────────────────────────────
  function sumStat(metrics: GroupTimepointMetrics[], key: 'totalSequences' | 'uniqueClones') {
    return metrics.reduce((a, m) => a + m.diversity[key], 0);
  }
  function avgStat(metrics: GroupTimepointMetrics[], key: 'shannonEntropy' | 'meanSHM') {
    if (metrics.length === 0) return 0;
    return metrics.reduce((a, m) => a + m.diversity[key], 0) / metrics.length;
  }

  // ── Per-sample metrics ───────────────────────────────────
  $: diseasePerSampleMetrics = computePerSampleMetrics(
    diseaseHasDesign ? (hasCohorts ? diseaseDesign : singleDesign) : null,
    hasCohorts ? (diseaseCohort?.fileGroups ?? []) : singleFileGroups,
    new Set(diseaseMetrics.map(m => m.groupId)),
    diseaseEnabledTimepoints
  );
  $: controlPerSampleMetrics = hasCohorts ? computePerSampleMetrics(
    controlHasDesign ? controlDesign : null,
    controlCohort?.fileGroups ?? [],
    new Set(controlMetrics.map(m => m.groupId)),
    controlEnabledTimepoints
  ) : [];

  // Per-sample enabled state
  let diseaseEnabledSamples = new Set<string>();
  let controlEnabledSamples = new Set<string>();
  let prevDiseaseSampleNames = new Set<string>();
  let prevControlSampleNames = new Set<string>();

  $: if (diseasePerSampleMetrics.length > 0) {
    const valid = new Set(diseasePerSampleMetrics.map(m => m.groupName));
    const next = new Set(diseaseEnabledSamples);
    for (const s of [...next]) { if (!valid.has(s)) next.delete(s); }
    for (const s of valid) { if (!prevDiseaseSampleNames.has(s)) next.add(s); }
    prevDiseaseSampleNames = valid;
    diseaseEnabledSamples = next.size > 0 ? next : new Set(valid);
  } else { prevDiseaseSampleNames = new Set(); diseaseEnabledSamples = new Set(); }

  $: if (controlPerSampleMetrics.length > 0) {
    const valid = new Set(controlPerSampleMetrics.map(m => m.groupName));
    const next = new Set(controlEnabledSamples);
    for (const s of [...next]) { if (!valid.has(s)) next.delete(s); }
    for (const s of valid) { if (!prevControlSampleNames.has(s)) next.add(s); }
    prevControlSampleNames = valid;
    controlEnabledSamples = next.size > 0 ? next : new Set(valid);
  } else { prevControlSampleNames = new Set(); controlEnabledSamples = new Set(); }

  $: filteredDiseasePerSample = diseasePerSampleMetrics.filter(m => diseaseEnabledSamples.has(m.groupName));
  $: filteredControlPerSample = controlPerSampleMetrics.filter(m => controlEnabledSamples.has(m.groupName));

  function toggleDiseaseSample(name: string) {
    if (diseaseEnabledSamples.has(name)) diseaseEnabledSamples.delete(name);
    else diseaseEnabledSamples.add(name);
    diseaseEnabledSamples = new Set(diseaseEnabledSamples);
  }
  function toggleControlSample(name: string) {
    if (controlEnabledSamples.has(name)) controlEnabledSamples.delete(name);
    else controlEnabledSamples.add(name);
    controlEnabledSamples = new Set(controlEnabledSamples);
  }

  // Group samples by timepoint for hierarchical selector
  interface TimepointGroup { label: string; samples: GroupTimepointMetrics[]; }
  function groupByTimepoint(metrics: GroupTimepointMetrics[]): TimepointGroup[] {
    const map = new Map<string, GroupTimepointMetrics[]>();
    const order: string[] = [];
    for (const m of metrics) {
      if (!map.has(m.timepointLabel)) { map.set(m.timepointLabel, []); order.push(m.timepointLabel); }
      map.get(m.timepointLabel)!.push(m);
    }
    return order.map(label => ({ label, samples: map.get(label)! }));
  }
  $: diseaseSampleGroups = groupByTimepoint(diseasePerSampleMetrics);
  $: controlSampleGroups = groupByTimepoint(controlPerSampleMetrics);

  function toggleAllSamplesInTp(tpGroup: TimepointGroup, enabledSet: Set<string>, setter: (s: Set<string>) => void) {
    const names = tpGroup.samples.map(m => m.groupName);
    const allOn = names.every(n => enabledSet.has(n));
    const next = new Set(enabledSet);
    if (allOn) { for (const n of names) next.delete(n); }
    else { for (const n of names) next.add(n); }
    setter(next);
  }

  // ── Longitudinal: combined for overlay ───────────────────
  $: combinedLongitudinal = (() => {
    const result: LongitudinalGroupData[] = [];
    if (diseaseLongitudinal.length > 0) {
      result.push(...diseaseLongitudinal.map(g => ({
        ...g,
        groupName: hasCohorts ? `${diseaseCohort?.cohortName ?? 'Disease'} – ${g.groupName}` : g.groupName,
        groupColor: '#1565C0'
      })));
    }
    if (controlLongitudinal.length > 0) {
      result.push(...controlLongitudinal.map(g => ({
        ...g,
        groupName: `${controlCohort?.cohortName ?? 'Control'} – ${g.groupName}`,
        groupColor: '#757575'
      })));
    }
    return result;
  })();

  $: hasLongitudinal = combinedLongitudinal.length > 0;

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

  const COHORT_COLOR_DISEASE = '#1565C0';
  const COHORT_COLOR_CONTROL = '#757575';

  // ── Export ─────────────────────────────────────────────
  import { dashboardMetricsToCsv, dashboardPerPatientCsv, downloadCsv } from '../../lib/utils/export-csv';

  let isExportingDashboard = false;
  let isExportingPerPatient = false;

  async function exportDashboard() {
    isExportingDashboard = true;
    try {
      const csv = dashboardMetricsToCsv(
        diseaseMetrics,
        controlMetrics,
        hasCohorts ? (diseaseCohort?.cohortName ?? 'Disease') : 'All Samples',
        controlCohort?.cohortName ?? 'Control',
        diseaseLongitudinal,
        controlLongitudinal
      );
      await downloadCsv(csv, 'repertoire_dashboard_metrics.csv');
    } catch (err: any) {
      alert(`Export failed: ${err.message || 'Unknown error'}`);
    } finally {
      isExportingDashboard = false;
    }
  }

  async function exportPerPatient() {
    isExportingPerPatient = true;
    try {
      const csv = dashboardPerPatientCsv({
        diseaseFileGroups: hasCohorts ? (diseaseCohort?.fileGroups ?? []) : singleFileGroups,
        diseaseTimepointMapping: hasCohorts
          ? (diseaseCohort?.timepointMapping ?? {})
          : ($resultsState.timepointMapping ?? {}),
        diseaseCohortName: hasCohorts ? (diseaseCohort?.cohortName ?? 'Disease') : 'All Samples',
        controlFileGroups: hasCohorts ? (controlCohort?.fileGroups ?? undefined) : undefined,
        controlTimepointMapping: hasCohorts ? (controlCohort?.timepointMapping ?? undefined) : undefined,
        controlCohortName: hasCohorts ? (controlCohort?.cohortName ?? 'Control') : undefined
      });
      await downloadCsv(csv, 'repertoire_per_patient_metrics.csv');
    } catch (err: any) {
      alert(`Export failed: ${err.message || 'Unknown error'}`);
    } finally {
      isExportingPerPatient = false;
    }
  }
</script>

<div class="dashboard">
  <div class="dash-header">
    <h2 class="dash-title">Repertoire Dashboard</h2>
    {#if diseaseMetrics.length > 0 || controlMetrics.length > 0}
      <div class="dash-export-group">
        <button
          class="export-view-btn"
          on:click={exportDashboard}
          disabled={isExportingDashboard}
          title="Export aggregated metrics (one row per timepoint)"
        >
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
            <path d="M8 2v8M5 7l3 3 3-3M2 12h12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          {isExportingDashboard ? '...' : 'Export Aggregated'}
        </button>
        <button
          class="export-view-btn"
          on:click={exportPerPatient}
          disabled={isExportingPerPatient}
          title="Export per-patient metrics (one row per patient × timepoint)"
        >
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
            <path d="M8 2v8M5 7l3 3 3-3M2 12h12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          {isExportingPerPatient ? '...' : 'Export Per-Patient'}
        </button>
      </div>
    {/if}
  </div>

  {#if diseaseMetrics.length === 0 && controlMetrics.length === 0}
    <div class="empty-state">
      <p>No data available yet. Run an analysis first.</p>
    </div>
  {:else}

    <!-- ════════════════════════════════════════════════════════
         SUMMARY CARDS
         ════════════════════════════════════════════════════════ -->
    {#if hasCohorts}
      <div class="comparison-summary">
        <div class="comp-card">
          <span class="comp-metric-label">Total Sequences</span>
          <div class="comp-values">
            <span class="comp-val disease">{sumStat(diseaseMetrics, 'totalSequences').toLocaleString()}</span>
            <span class="comp-sep">vs</span>
            <span class="comp-val control">{sumStat(controlMetrics, 'totalSequences').toLocaleString()}</span>
          </div>
          <div class="comp-cohort-labels">
            <span class="comp-cohort-name disease">{diseaseCohort?.cohortName ?? 'Disease'}</span>
            <span class="comp-cohort-name control">{controlCohort?.cohortName ?? 'Control'}</span>
          </div>
        </div>
        <div class="comp-card">
          <span class="comp-metric-label">Unique Clones</span>
          <div class="comp-values">
            <span class="comp-val disease">{sumStat(diseaseMetrics, 'uniqueClones').toLocaleString()}</span>
            <span class="comp-sep">vs</span>
            <span class="comp-val control">{sumStat(controlMetrics, 'uniqueClones').toLocaleString()}</span>
          </div>
          <div class="comp-cohort-labels">
            <span class="comp-cohort-name disease">{diseaseCohort?.cohortName ?? 'Disease'}</span>
            <span class="comp-cohort-name control">{controlCohort?.cohortName ?? 'Control'}</span>
          </div>
        </div>
        <div class="comp-card">
          <span class="comp-metric-label">Shannon Diversity</span>
          <div class="comp-values">
            <span class="comp-val disease">{avgStat(diseaseMetrics, 'shannonEntropy').toFixed(2)}</span>
            <span class="comp-sep">vs</span>
            <span class="comp-val control">{avgStat(controlMetrics, 'shannonEntropy').toFixed(2)}</span>
          </div>
          <div class="comp-cohort-labels">
            <span class="comp-cohort-name disease">{diseaseCohort?.cohortName ?? 'Disease'}</span>
            <span class="comp-cohort-name control">{controlCohort?.cohortName ?? 'Control'}</span>
          </div>
        </div>
        <div class="comp-card">
          <span class="comp-metric-label">Mean SHM</span>
          <div class="comp-values">
            <span class="comp-val disease">{avgStat(diseaseMetrics, 'meanSHM').toFixed(1)}</span>
            <span class="comp-sep">vs</span>
            <span class="comp-val control">{avgStat(controlMetrics, 'meanSHM').toFixed(1)}</span>
          </div>
          <div class="comp-cohort-labels">
            <span class="comp-cohort-name disease">{diseaseCohort?.cohortName ?? 'Disease'}</span>
            <span class="comp-cohort-name control">{controlCohort?.cohortName ?? 'Control'}</span>
          </div>
        </div>
      </div>
    {:else}
      <div class="summary-row">
        <div class="summary-card">
          <span class="sum-value">{sumStat(diseaseMetrics, 'totalSequences').toLocaleString()}</span>
          <span class="sum-label">Total Sequences</span>
        </div>
        <div class="summary-card">
          <span class="sum-value">{sumStat(diseaseMetrics, 'uniqueClones').toLocaleString()}</span>
          <span class="sum-label">Unique Clones</span>
        </div>
        <div class="summary-card">
          <span class="sum-value">{diseaseMetrics.length}</span>
          <span class="sum-label">Timepoints</span>
        </div>
        {#if diseaseLongitudinal.length > 0}
          <div class="summary-card accent">
            <span class="sum-value">{diseaseLongitudinal.reduce((a, g) => a + g.persistentCloneCount, 0)}</span>
            <span class="sum-label">Persistent Clones</span>
          </div>
        {/if}
      </div>
    {/if}

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
      </button>

      {#if perTimepointOpen}
        <div class="section-body">
          {#if hasCohorts}
            <!-- COMPARISON: side-by-side disease | control -->
            <div class="cohort-comparison-row">
              <!-- Disease column -->
              <div class="cohort-col">
                <div class="cohort-col-header disease">
                  <span class="cohort-col-dot" style="background: {COHORT_COLOR_DISEASE}"></span>
                  {diseaseCohort?.cohortName ?? 'Disease'}
                </div>
                {#if diseaseUniqueTimepoints.length > 1}
                  <div class="tp-filter-row">
                    {#each diseaseUniqueTimepoints as tp}
                      <button
                        class="filter-pill filter-pill-sm"
                        class:active={diseaseEnabledTimepoints.has(tp)}
                        on:click={() => toggleDiseaseTimepoint(tp)}
                      >{tp}</button>
                    {/each}
                  </div>
                {/if}
                {#if filteredDiseaseMetrics.length > 0}
                  <div class="metric-cards-scroll">
                    {#each filteredDiseaseMetrics as m}
                      <div class="metric-card">
                        <div class="mc-header">
                          <span class="mc-dot" style="background: {m.groupColor}"></span>
                          <span class="mc-label">{m.timepointLabel}</span>
                        </div>
                        <div class="mc-grid">
                          <div class="mc-item" title={METRIC_TOOLTIPS['Sequences']}><span class="mc-val">{m.diversity.totalSequences}</span><span class="mc-key">Sequences</span></div>
                          <div class="mc-item" title={METRIC_TOOLTIPS['Clones']}><span class="mc-val">{m.diversity.uniqueClones}</span><span class="mc-key">Clones</span></div>
                          <div class="mc-item" title={METRIC_TOOLTIPS['Shannon']}><span class="mc-val">{m.diversity.shannonEntropy.toFixed(2)}</span><span class="mc-key">Shannon</span></div>
                          <div class="mc-item" title={METRIC_TOOLTIPS['Mean SHM']}><span class="mc-val">{m.diversity.meanSHM.toFixed(1)}</span><span class="mc-key">Mean SHM</span></div>
                          <div class="mc-item" title={METRIC_TOOLTIPS['Gini']}><span class="mc-val">{m.diversity.giniIndex.toFixed(3)}</span><span class="mc-key">Gini</span></div>
                          <div class="mc-item" title={METRIC_TOOLTIPS['D50']}><span class="mc-val">{m.diversity.d50}</span><span class="mc-key">D50</span></div>
                        </div>
                      </div>
                    {/each}
                  </div>
                  <div class="charts-grid">
                    <section class="chart-panel"><h3 class="chart-heading">Diversity &amp; SHM</h3><DiversityChart data={filteredDiseaseMetrics} /></section>
                    <section class="chart-panel chart-panel-scroll"><h3 class="chart-heading">V-Gene Usage</h3><VGeneChart data={filteredDiseaseMetrics} /></section>
                  </div>
                  <section class="chart-panel full-width"><h3 class="chart-heading">Isotype Distribution</h3><IsotypeChart data={filteredDiseaseMetrics} /></section>
                  <section class="chart-panel full-width"><h3 class="chart-heading">Rank-Abundance</h3><ExpansionChart data={filteredDiseaseMetrics} /></section>
                {:else}
                  <div class="empty-state-sm"><p>No data for selected timepoints.</p></div>
                {/if}
              </div>

              <!-- Control column -->
              <div class="cohort-col">
                <div class="cohort-col-header control">
                  <span class="cohort-col-dot" style="background: {COHORT_COLOR_CONTROL}"></span>
                  {controlCohort?.cohortName ?? 'Control'}
                </div>
                {#if controlUniqueTimepoints.length > 1}
                  <div class="tp-filter-row">
                    {#each controlUniqueTimepoints as tp}
                      <button
                        class="filter-pill filter-pill-sm"
                        class:active={controlEnabledTimepoints.has(tp)}
                        on:click={() => toggleControlTimepoint(tp)}
                      >{tp}</button>
                    {/each}
                  </div>
                {/if}
                {#if filteredControlMetrics.length > 0}
                  <div class="metric-cards-scroll">
                    {#each filteredControlMetrics as m}
                      <div class="metric-card">
                        <div class="mc-header">
                          <span class="mc-dot" style="background: {m.groupColor}"></span>
                          <span class="mc-label">{m.timepointLabel}</span>
                        </div>
                        <div class="mc-grid">
                          <div class="mc-item" title={METRIC_TOOLTIPS['Sequences']}><span class="mc-val">{m.diversity.totalSequences}</span><span class="mc-key">Sequences</span></div>
                          <div class="mc-item" title={METRIC_TOOLTIPS['Clones']}><span class="mc-val">{m.diversity.uniqueClones}</span><span class="mc-key">Clones</span></div>
                          <div class="mc-item" title={METRIC_TOOLTIPS['Shannon']}><span class="mc-val">{m.diversity.shannonEntropy.toFixed(2)}</span><span class="mc-key">Shannon</span></div>
                          <div class="mc-item" title={METRIC_TOOLTIPS['Mean SHM']}><span class="mc-val">{m.diversity.meanSHM.toFixed(1)}</span><span class="mc-key">Mean SHM</span></div>
                          <div class="mc-item" title={METRIC_TOOLTIPS['Gini']}><span class="mc-val">{m.diversity.giniIndex.toFixed(3)}</span><span class="mc-key">Gini</span></div>
                          <div class="mc-item" title={METRIC_TOOLTIPS['D50']}><span class="mc-val">{m.diversity.d50}</span><span class="mc-key">D50</span></div>
                        </div>
                      </div>
                    {/each}
                  </div>
                  <div class="charts-grid">
                    <section class="chart-panel"><h3 class="chart-heading">Diversity &amp; SHM</h3><DiversityChart data={filteredControlMetrics} /></section>
                    <section class="chart-panel chart-panel-scroll"><h3 class="chart-heading">V-Gene Usage</h3><VGeneChart data={filteredControlMetrics} /></section>
                  </div>
                  <section class="chart-panel full-width"><h3 class="chart-heading">Isotype Distribution</h3><IsotypeChart data={filteredControlMetrics} /></section>
                  <section class="chart-panel full-width"><h3 class="chart-heading">Rank-Abundance</h3><ExpansionChart data={filteredControlMetrics} /></section>
                {:else}
                  <div class="empty-state-sm"><p>No data for selected timepoints.</p></div>
                {/if}
              </div>
            </div>
          {:else}
            <!-- SINGLE COHORT: original layout -->
            {#if diseaseUniqueTimepoints.length > 1}
              <div class="tp-filter-row" style="margin-bottom: var(--space-3);">
                <span class="filter-label">Timepoints:</span>
                {#each diseaseUniqueTimepoints as tp}
                  <button
                    class="filter-pill filter-pill-sm"
                    class:active={diseaseEnabledTimepoints.has(tp)}
                    on:click={() => toggleDiseaseTimepoint(tp)}
                  >{tp}</button>
                {/each}
              </div>
            {/if}
            {#if filteredDiseaseMetrics.length > 0}
              <div class="metric-cards-scroll">
                {#each filteredDiseaseMetrics as m}
                  <div class="metric-card">
                    <div class="mc-header">
                      <span class="mc-dot" style="background: {m.groupColor}"></span>
                      <span class="mc-label">{m.groupName}{diseaseHasDesign ? ` / ${m.timepointLabel}` : ''}</span>
                    </div>
                    <div class="mc-grid">
                      <div class="mc-item" title={METRIC_TOOLTIPS['Sequences']}><span class="mc-val">{m.diversity.totalSequences}</span><span class="mc-key">Sequences</span></div>
                      <div class="mc-item" title={METRIC_TOOLTIPS['Clones']}><span class="mc-val">{m.diversity.uniqueClones}</span><span class="mc-key">Clones</span></div>
                      <div class="mc-item" title={METRIC_TOOLTIPS['Shannon']}><span class="mc-val">{m.diversity.shannonEntropy.toFixed(2)}</span><span class="mc-key">Shannon</span></div>
                      <div class="mc-item" title={METRIC_TOOLTIPS['Chao1']}><span class="mc-val">{m.diversity.chao1.toFixed(0)}</span><span class="mc-key">Chao1</span></div>
                      <div class="mc-item" title={METRIC_TOOLTIPS['Gini']}><span class="mc-val">{m.diversity.giniIndex.toFixed(3)}</span><span class="mc-key">Gini</span></div>
                      <div class="mc-item" title={METRIC_TOOLTIPS['Simpson']}><span class="mc-val">{m.diversity.simpsonIndex.toFixed(3)}</span><span class="mc-key">Simpson</span></div>
                      <div class="mc-item" title={METRIC_TOOLTIPS['Mean SHM']}><span class="mc-val">{m.diversity.meanSHM.toFixed(1)}</span><span class="mc-key">Mean SHM</span></div>
                      <div class="mc-item" title={METRIC_TOOLTIPS['D50']}><span class="mc-val">{m.diversity.d50}</span><span class="mc-key">D50</span></div>
                      <div class="mc-item" title={METRIC_TOOLTIPS['Productive']}><span class="mc-val">{m.diversity.productivePercent.toFixed(0)}%</span><span class="mc-key">Productive</span></div>
                    </div>
                  </div>
                {/each}
              </div>
              <div class="charts-grid">
                <section class="chart-panel"><h3 class="chart-heading">Clonal Diversity &amp; SHM</h3><DiversityChart data={filteredDiseaseMetrics} /></section>
                <section class="chart-panel chart-panel-scroll"><h3 class="chart-heading">V-Gene Family Usage</h3><VGeneChart data={filteredDiseaseMetrics} /></section>
              </div>
              <section class="chart-panel full-width"><h3 class="chart-heading">Isotype Distribution</h3><IsotypeChart data={filteredDiseaseMetrics} /></section>
              <section class="chart-panel full-width"><h3 class="chart-heading">Clonal Expansion (Rank-Abundance)</h3><ExpansionChart data={filteredDiseaseMetrics} /></section>
            {:else}
              <div class="empty-state"><p>No data matches the current filters.</p></div>
            {/if}
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
          {filteredDiseasePerSample.length + filteredControlPerSample.length} sample{(filteredDiseasePerSample.length + filteredControlPerSample.length) !== 1 ? 's' : ''}
        </span>
      </button>

      {#if perSampleComparisonOpen}
        <div class="section-body">
          <p class="section-desc">
            Side-by-side comparison of metrics for individual samples, organized by cohort and timepoint.
          </p>

          {#if hasCohorts}
            <div class="cohort-comparison-row">
              <!-- Disease samples -->
              <div class="cohort-col">
                <div class="cohort-col-header disease">
                  <span class="cohort-col-dot" style="background: {COHORT_COLOR_DISEASE}"></span>
                  {diseaseCohort?.cohortName ?? 'Disease'}
                </div>
                {#if diseaseSampleGroups.length > 0}
                  <div class="hierarchical-selector">
                    {#each diseaseSampleGroups as tpGroup}
                      <div class="tp-sample-group">
                        <div class="tp-sample-header">
                          <span class="tp-sample-label">{tpGroup.label}</span>
                          <button
                            class="tp-all-btn"
                            on:click={() => toggleAllSamplesInTp(tpGroup, diseaseEnabledSamples, s => { diseaseEnabledSamples = s; })}
                          >All</button>
                        </div>
                        <div class="tp-sample-pills">
                          {#each tpGroup.samples as m}
                            <button
                              class="filter-pill filter-pill-sm"
                              class:active={diseaseEnabledSamples.has(m.groupName)}
                              on:click={() => toggleDiseaseSample(m.groupName)}
                              title={m.groupName}
                            >
                              <span class="pill-dot" style="background: {m.groupColor}"></span>
                              <span class="pill-name">{m.groupName}</span>
                            </button>
                          {/each}
                        </div>
                      </div>
                    {/each}
                  </div>
                  {#if filteredDiseasePerSample.length > 0}
                    <div class="metric-cards-scroll">
                      {#each filteredDiseasePerSample as m}
                        <div class="metric-card">
                          <div class="mc-header">
                            <span class="mc-dot" style="background: {m.groupColor}"></span>
                            <span class="mc-label">{m.groupName} ({m.timepointLabel})</span>
                          </div>
                          <div class="mc-grid">
                            <div class="mc-item"><span class="mc-val">{m.diversity.totalSequences}</span><span class="mc-key">Sequences</span></div>
                            <div class="mc-item"><span class="mc-val">{m.diversity.uniqueClones}</span><span class="mc-key">Clones</span></div>
                            <div class="mc-item"><span class="mc-val">{m.diversity.shannonEntropy.toFixed(2)}</span><span class="mc-key">Shannon</span></div>
                            <div class="mc-item"><span class="mc-val">{m.diversity.meanSHM.toFixed(1)}</span><span class="mc-key">Mean SHM</span></div>
                            <div class="mc-item"><span class="mc-val">{m.diversity.giniIndex.toFixed(3)}</span><span class="mc-key">Gini</span></div>
                            <div class="mc-item"><span class="mc-val">{m.diversity.d50}</span><span class="mc-key">D50</span></div>
                          </div>
                        </div>
                      {/each}
                    </div>
                    <div class="charts-grid">
                      <section class="chart-panel"><h3 class="chart-heading">Diversity &amp; SHM</h3><DiversityChart data={filteredDiseasePerSample} /></section>
                      <section class="chart-panel chart-panel-scroll"><h3 class="chart-heading">V-Gene Usage</h3><VGeneChart data={filteredDiseasePerSample} /></section>
                    </div>
                    <section class="chart-panel full-width"><h3 class="chart-heading">Isotype Distribution</h3><IsotypeChart data={filteredDiseasePerSample} /></section>
                    <section class="chart-panel full-width"><h3 class="chart-heading">Rank-Abundance</h3><ExpansionChart data={filteredDiseasePerSample} /></section>
                  {:else}
                    <div class="empty-state-sm"><p>Select at least one sample.</p></div>
                  {/if}
                {:else}
                  <div class="empty-state-sm"><p>No samples available.</p></div>
                {/if}
              </div>

              <!-- Control samples -->
              <div class="cohort-col">
                <div class="cohort-col-header control">
                  <span class="cohort-col-dot" style="background: {COHORT_COLOR_CONTROL}"></span>
                  {controlCohort?.cohortName ?? 'Control'}
                </div>
                {#if controlSampleGroups.length > 0}
                  <div class="hierarchical-selector">
                    {#each controlSampleGroups as tpGroup}
                      <div class="tp-sample-group">
                        <div class="tp-sample-header">
                          <span class="tp-sample-label">{tpGroup.label}</span>
                          <button
                            class="tp-all-btn"
                            on:click={() => toggleAllSamplesInTp(tpGroup, controlEnabledSamples, s => { controlEnabledSamples = s; })}
                          >All</button>
                        </div>
                        <div class="tp-sample-pills">
                          {#each tpGroup.samples as m}
                            <button
                              class="filter-pill filter-pill-sm"
                              class:active={controlEnabledSamples.has(m.groupName)}
                              on:click={() => toggleControlSample(m.groupName)}
                              title={m.groupName}
                            >
                              <span class="pill-dot" style="background: {m.groupColor}"></span>
                              <span class="pill-name">{m.groupName}</span>
                            </button>
                          {/each}
                        </div>
                      </div>
                    {/each}
                  </div>
                  {#if filteredControlPerSample.length > 0}
                    <div class="metric-cards-scroll">
                      {#each filteredControlPerSample as m}
                        <div class="metric-card">
                          <div class="mc-header">
                            <span class="mc-dot" style="background: {m.groupColor}"></span>
                            <span class="mc-label">{m.groupName} ({m.timepointLabel})</span>
                          </div>
                          <div class="mc-grid">
                            <div class="mc-item"><span class="mc-val">{m.diversity.totalSequences}</span><span class="mc-key">Sequences</span></div>
                            <div class="mc-item"><span class="mc-val">{m.diversity.uniqueClones}</span><span class="mc-key">Clones</span></div>
                            <div class="mc-item"><span class="mc-val">{m.diversity.shannonEntropy.toFixed(2)}</span><span class="mc-key">Shannon</span></div>
                            <div class="mc-item"><span class="mc-val">{m.diversity.meanSHM.toFixed(1)}</span><span class="mc-key">Mean SHM</span></div>
                            <div class="mc-item"><span class="mc-val">{m.diversity.giniIndex.toFixed(3)}</span><span class="mc-key">Gini</span></div>
                            <div class="mc-item"><span class="mc-val">{m.diversity.d50}</span><span class="mc-key">D50</span></div>
                          </div>
                        </div>
                      {/each}
                    </div>
                    <div class="charts-grid">
                      <section class="chart-panel"><h3 class="chart-heading">Diversity &amp; SHM</h3><DiversityChart data={filteredControlPerSample} /></section>
                      <section class="chart-panel chart-panel-scroll"><h3 class="chart-heading">V-Gene Usage</h3><VGeneChart data={filteredControlPerSample} /></section>
                    </div>
                    <section class="chart-panel full-width"><h3 class="chart-heading">Isotype Distribution</h3><IsotypeChart data={filteredControlPerSample} /></section>
                    <section class="chart-panel full-width"><h3 class="chart-heading">Rank-Abundance</h3><ExpansionChart data={filteredControlPerSample} /></section>
                  {:else}
                    <div class="empty-state-sm"><p>Select at least one sample.</p></div>
                  {/if}
                {:else}
                  <div class="empty-state-sm"><p>No samples available.</p></div>
                {/if}
              </div>
            </div>
          {:else}
            <!-- SINGLE: grouped by timepoint -->
            {#if diseaseSampleGroups.length > 0}
              <div class="hierarchical-selector">
                {#each diseaseSampleGroups as tpGroup}
                  <div class="tp-sample-group">
                    <div class="tp-sample-header">
                      <span class="tp-sample-label">{tpGroup.label}</span>
                      <button
                        class="tp-all-btn"
                        on:click={() => toggleAllSamplesInTp(tpGroup, diseaseEnabledSamples, s => { diseaseEnabledSamples = s; })}
                      >All</button>
                    </div>
                    <div class="tp-sample-pills">
                      {#each tpGroup.samples as m}
                        <button
                          class="filter-pill filter-pill-sm"
                          class:active={diseaseEnabledSamples.has(m.groupName)}
                          on:click={() => toggleDiseaseSample(m.groupName)}
                          title={m.groupName}
                        >
                          <span class="pill-dot" style="background: {m.groupColor}"></span>
                          <span class="pill-name">{m.groupName}{diseaseHasDesign ? ` (${m.timepointLabel})` : ''}</span>
                        </button>
                      {/each}
                    </div>
                  </div>
                {/each}
              </div>
              {#if filteredDiseasePerSample.length > 0}
                <div class="metric-cards-scroll">
                  {#each filteredDiseasePerSample as m}
                    <div class="metric-card">
                      <div class="mc-header">
                        <span class="mc-dot" style="background: {m.groupColor}"></span>
                        <span class="mc-label">{m.groupName}{diseaseHasDesign ? ` (${m.timepointLabel})` : ''}</span>
                      </div>
                      <div class="mc-grid">
                        <div class="mc-item" title={METRIC_TOOLTIPS['Sequences']}><span class="mc-val">{m.diversity.totalSequences}</span><span class="mc-key">Sequences</span></div>
                        <div class="mc-item" title={METRIC_TOOLTIPS['Clones']}><span class="mc-val">{m.diversity.uniqueClones}</span><span class="mc-key">Clones</span></div>
                        <div class="mc-item" title={METRIC_TOOLTIPS['Shannon']}><span class="mc-val">{m.diversity.shannonEntropy.toFixed(2)}</span><span class="mc-key">Shannon</span></div>
                        <div class="mc-item" title={METRIC_TOOLTIPS['Chao1']}><span class="mc-val">{m.diversity.chao1.toFixed(0)}</span><span class="mc-key">Chao1</span></div>
                        <div class="mc-item" title={METRIC_TOOLTIPS['Gini']}><span class="mc-val">{m.diversity.giniIndex.toFixed(3)}</span><span class="mc-key">Gini</span></div>
                        <div class="mc-item" title={METRIC_TOOLTIPS['Simpson']}><span class="mc-val">{m.diversity.simpsonIndex.toFixed(3)}</span><span class="mc-key">Simpson</span></div>
                        <div class="mc-item" title={METRIC_TOOLTIPS['Mean SHM']}><span class="mc-val">{m.diversity.meanSHM.toFixed(1)}</span><span class="mc-key">Mean SHM</span></div>
                        <div class="mc-item" title={METRIC_TOOLTIPS['D50']}><span class="mc-val">{m.diversity.d50}</span><span class="mc-key">D50</span></div>
                        <div class="mc-item" title={METRIC_TOOLTIPS['Productive']}><span class="mc-val">{m.diversity.productivePercent.toFixed(0)}%</span><span class="mc-key">Productive</span></div>
                      </div>
                    </div>
                  {/each}
                </div>
                <div class="charts-grid">
                  <section class="chart-panel"><h3 class="chart-heading">Diversity &amp; SHM (per sample)</h3><DiversityChart data={filteredDiseasePerSample} /></section>
                  <section class="chart-panel chart-panel-scroll"><h3 class="chart-heading">V-Gene Usage (per sample)</h3><VGeneChart data={filteredDiseasePerSample} /></section>
                </div>
                <section class="chart-panel full-width"><h3 class="chart-heading">Isotype Distribution (per sample)</h3><IsotypeChart data={filteredDiseasePerSample} /></section>
                <section class="chart-panel full-width"><h3 class="chart-heading">Rank-Abundance (per sample)</h3><ExpansionChart data={filteredDiseasePerSample} /></section>
              {:else}
                <div class="empty-state"><p>Select at least one sample above to view metrics and charts.</p></div>
              {/if}
            {:else}
              <div class="empty-state"><p>No samples available.</p></div>
            {/if}
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
          <span class="section-badge">{combinedLongitudinal.length} group{combinedLongitudinal.length !== 1 ? 's' : ''}</span>
        {:else}
          <span class="section-badge muted">requires &ge;2 timepoints</span>
        {/if}
      </button>

      {#if longitudinalOpen}
        <div class="section-body">
          {#if hasLongitudinal}
            <section class="chart-panel full-width">
              <h3 class="chart-heading">Diversity &amp; SHM Trajectory</h3>
              <p class="chart-desc">How repertoire diversity and mutation load change over time.{hasCohorts ? ' Both cohorts are overlaid for comparison.' : ''}</p>
              <DiversityTrajectoryChart data={combinedLongitudinal} />
            </section>

            <section class="chart-panel full-width">
              <h3 class="chart-heading">SHM Accumulation</h3>
              <p class="chart-desc">Do persistent clones accumulate somatic hypermutations over time?{hasCohorts ? ' Both cohorts overlaid.' : ''}</p>
              <ShmAccumulationChart data={combinedLongitudinal} />
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
              <p class="prompt-title">Longitudinal analysis requires at least 2 timepoints</p>
              <p class="prompt-desc">
                Assign files to multiple timepoints during the wizard setup. Once a cohort has at least two timepoints, diversity trajectory and SHM accumulation will appear here.
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
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .dash-title {
    margin: 0;
    font-size: var(--text-xl);
    font-weight: var(--font-semibold);
    color: var(--text-primary);
  }
  .dash-export-group {
    display: flex;
    gap: var(--space-2);
  }
  .export-view-btn {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-3);
    font-size: var(--text-xs);
    font-weight: var(--font-medium);
    color: var(--text-secondary);
    background: var(--surface-raised);
    border: 1px solid var(--border-light);
    border-radius: var(--border-radius-md);
    cursor: pointer;
    transition: all var(--transition-fast);
    white-space: nowrap;
  }
  .export-view-btn:hover { background: var(--gray-100); color: var(--text-primary); }
  .export-view-btn:disabled { opacity: 0.5; cursor: not-allowed; }
  .export-view-btn svg { flex-shrink: 0; }

  /* ── Comparison summary cards ─── */
  .comparison-summary {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: var(--space-3);
    margin-bottom: var(--space-5);
  }
  .comp-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: var(--space-3) var(--space-4);
    background: var(--surface-raised);
    border: 1px solid var(--border-light);
    border-radius: var(--border-radius-md);
    text-align: center;
  }
  .comp-metric-label {
    font-size: var(--text-xs);
    color: var(--text-tertiary);
    text-transform: uppercase;
    letter-spacing: var(--tracking-wide);
    margin-bottom: var(--space-2);
  }
  .comp-values {
    display: flex;
    align-items: baseline;
    gap: var(--space-2);
  }
  .comp-val {
    font-size: var(--text-lg);
    font-weight: var(--font-bold);
    font-feature-settings: 'tnum' 1;
  }
  .comp-val.disease { color: #1565C0; }
  .comp-val.control { color: #616161; }
  .comp-sep {
    font-size: var(--text-xs);
    color: var(--text-tertiary);
    font-weight: var(--font-medium);
  }
  .comp-cohort-labels {
    display: flex;
    justify-content: space-between;
    width: 100%;
    margin-top: var(--space-1);
  }
  .comp-cohort-name {
    font-size: 10px;
    font-weight: var(--font-medium);
  }
  .comp-cohort-name.disease { color: #1565C0; }
  .comp-cohort-name.control { color: #757575; }

  /* ── Single-cohort summary ────── */
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

  /* ── Cohort comparison columns ── */
  .cohort-comparison-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--space-4);
  }
  .cohort-col {
    min-width: 0;
  }
  .cohort-col-header {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    font-size: var(--text-sm);
    font-weight: var(--font-semibold);
    padding: var(--space-2) var(--space-3);
    border-radius: var(--border-radius-sm);
    margin-bottom: var(--space-3);
  }
  .cohort-col-header.disease {
    color: #1565C0;
    background: #E3F2FD;
  }
  .cohort-col-header.control {
    color: #424242;
    background: #F5F5F5;
  }
  .cohort-col-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  /* ── Timepoint filter row ─────── */
  .tp-filter-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--space-1);
    margin-bottom: var(--space-3);
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
  .filter-pill-sm {
    padding: 3px 10px;
    font-size: 11px;
  }
  .pill-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }
  .pill-name {
    max-width: 140px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* ── Hierarchical sample selector ── */
  .hierarchical-selector {
    margin-bottom: var(--space-4);
  }
  .tp-sample-group {
    margin-bottom: var(--space-2);
  }
  .tp-sample-header {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    margin-bottom: var(--space-1);
  }
  .tp-sample-label {
    font-size: 11px;
    font-weight: var(--font-semibold);
    color: var(--text-secondary);
    min-width: 32px;
  }
  .tp-all-btn {
    font-size: 10px;
    padding: 1px 8px;
    border: 1px solid var(--border-light);
    border-radius: var(--border-radius-full);
    background: var(--gray-50);
    color: var(--text-tertiary);
    cursor: pointer;
    transition: all var(--transition-fast);
  }
  .tp-all-btn:hover {
    background: var(--color-primary-light);
    color: var(--color-primary);
  }
  .tp-sample-pills {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-1);
    padding-left: var(--space-3);
  }

  /* ── Collapsible sections ──────── */
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
  .section-header:hover { background: var(--gray-100); }
  .section-chevron {
    display: flex; align-items: center; justify-content: center;
    width: 20px; height: 20px;
    color: var(--text-tertiary);
    transition: transform 0.2s ease;
    transform: rotate(0deg);
  }
  .section-chevron.open { transform: rotate(90deg); }
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
  .section-body { padding: var(--space-4); }
  .section-desc {
    font-size: var(--text-sm);
    color: var(--text-tertiary);
    margin: 0 0 var(--space-4) 0;
    line-height: var(--leading-relaxed);
  }

  /* ── Per-timepoint metric cards ── */
  .metric-cards-scroll {
    display: flex;
    gap: var(--space-3);
    overflow-x: auto;
    padding-bottom: var(--space-3);
    margin-bottom: var(--space-4);
  }
  .metric-card {
    flex: 0 0 auto;
    min-width: 200px;
    max-width: 260px;
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
  .mc-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
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
  .mc-item { display: flex; flex-direction: column; cursor: help; }
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
    grid-template-rows: 560px;
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
  .chart-panel.full-width { margin-bottom: var(--space-4); }
  .chart-panel.chart-panel-scroll {
    overflow-y: auto;
    overflow-x: hidden;
    min-height: 0;
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

  /* ── Empty states ─────────────── */
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 120px;
    color: var(--text-tertiary);
    font-size: var(--text-sm);
  }
  .empty-state-sm {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 60px;
    color: var(--text-tertiary);
    font-size: var(--text-xs);
  }
  .longitudinal-prompt {
    padding: var(--space-6) var(--space-4);
    text-align: center;
  }
  .prompt-icon { color: var(--gray-300); margin-bottom: var(--space-3); }
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
</style>
