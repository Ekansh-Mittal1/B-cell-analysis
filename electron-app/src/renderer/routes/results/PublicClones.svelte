<script lang="ts">
  import { onMount } from 'svelte';
  import { resultsState, publicClonesActions } from '../../lib/stores/app';
  import {
    computePublicClonesPerTimepoint,
    computePublicClones,
    computeClonalDynamicsHeatmap,
    getTimepointLabels
  } from '../../lib/utils/public-clones';
  import type { ClonalDynamicsData, ClonalDynamicsEntry, ClonalStatus } from '../../lib/utils/public-clones';
  import type { TreeMetadata } from '../../lib/stores/app';
  import HeatmapViz from '../../lib/components/visualizations/HeatmapViz.svelte';
  import ClonalDynamicsHeatmap from '../../lib/components/visualizations/ClonalDynamicsHeatmap.svelte';
  import InteractiveTree from './InteractiveTree.svelte';

  const DYNAMICS_STATUSES: { value: ClonalStatus; label: string }[] = [
    { value: 'persistent', label: 'Persistent' },
    { value: 'expanding', label: 'Expanding' },
    { value: 'contracting', label: 'Contracting' },
    { value: 'disappeared', label: 'Disappeared' },
    { value: 'late_emerging', label: 'Late emerging' },
    { value: 'transient', label: 'Transient' }
  ];

  // ── Section collapse state ──
  let sharedOpen = true;
  let dynamicsOpen = true;

  // ── Shared Clones state ──
  let topN = 20;
  let selectedCloneId: string | null = null;
  let activeVizTab: 'details' | 'heatmap' = 'heatmap';
  let timepointLabels: string[] = [];
  let selectedTimepoint: string = '';

  // ── Clonal Dynamics state ──
  let dynamicsData: ClonalDynamicsData | null = null;
  let dynamicsTopN = 30;
  let selectedDynamicsEntry: ClonalDynamicsEntry | null = null;
  let activeStatuses: Record<ClonalStatus, boolean> = {
    persistent: true, expanding: true, contracting: true, disappeared: true, late_emerging: true, transient: true
  };

  function toggleStatusFilter(status: ClonalStatus) {
    activeStatuses = { ...activeStatuses, [status]: !activeStatuses[status] };
  }

  $: filteredDynamicsEntries = dynamicsData
    ? dynamicsData.entries.filter(e => activeStatuses[e.status])
    : [];
  $: if (selectedDynamicsEntry && !activeStatuses[selectedDynamicsEntry.status]) {
    selectedDynamicsEntry = null;
  }

  $: hasResults = $resultsState.publicClonesData !== null;
  $: selectedClone = hasResults && selectedCloneId
    ? $resultsState.publicClonesData!.public_clones.find(c => c.id === selectedCloneId) || null
    : null;
  $: hasTimepoints = timepointLabels.length > 0;

  // Detect available timepoints
  onMount(() => {
    timepointLabels = getTimepointLabels($resultsState.timepointMapping);
    if (timepointLabels.length > 0 && !selectedTimepoint) {
      selectedTimepoint = timepointLabels[0];
    }
    recomputeShared();
    recomputeDynamics();
  });

  // When timepoint changes, recompute shared clones
  $: if (selectedTimepoint && $resultsState.fileGroups.length > 0) {
    recomputeShared();
  }

  function recomputeShared() {
    if ($resultsState.fileGroups.length === 0) return;
    const data = hasTimepoints && selectedTimepoint
      ? computePublicClonesPerTimepoint(
          $resultsState.fileGroups,
          $resultsState.timepointMapping,
          selectedTimepoint,
          { topN }
        )
      : computePublicClones(
          $resultsState.fileGroups,
          $resultsState.timepointMapping,
          { topN }
        );
    publicClonesActions.updateResults(data);
    if (data.top_x.length > 0) {
      selectedCloneId = data.top_x[0].id;
    } else {
      selectedCloneId = null;
    }
  }

  function recomputeDynamics() {
    if ($resultsState.fileGroups.length === 0) return;
    dynamicsData = computeClonalDynamicsHeatmap(
      $resultsState.fileGroups,
      $resultsState.timepointMapping,
      dynamicsTopN
    );
  }

  function selectClone(cloneId: string) {
    selectedCloneId = cloneId;
  }

  function selectCloneByIndex(index: number) {
    if ($resultsState.publicClonesData && index < $resultsState.publicClonesData.public_clones.length) {
      selectedCloneId = $resultsState.publicClonesData.public_clones[index].id;
      activeVizTab = 'details';
    }
  }

  function handleTopNChange() {
    publicClonesActions.clearResults();
    recomputeShared();
  }

  function handleDynamicsTopNChange() {
    recomputeDynamics();
  }

  let selectedDynamicsTimepoint: string | null = null;

  function handleDynamicsCloneClick(entry: ClonalDynamicsEntry, timepoint?: string) {
    selectedDynamicsEntry = entry;
    selectedDynamicsTimepoint = timepoint ?? null;
  }

  // Find matching tree for the selected dynamics entry + timepoint
  function findDynamicsTree(
    entry: ClonalDynamicsEntry | null,
    tp: string | null,
    treeMeta: TreeMetadata[]
  ): { index: number; meta: TreeMetadata } | null {
    if (!entry || !treeMeta?.length) return null;

    const cloneIds = new Set<number>();

    if (tp && entry.cloneIdsByTimepoint?.[tp]) {
      for (const cid of entry.cloneIdsByTimepoint[tp]) cloneIds.add(cid);
    } else {
      if (entry.cloneIdsByTimepoint) {
        for (const cids of Object.values(entry.cloneIdsByTimepoint)) {
          for (const cid of cids) cloneIds.add(cid);
        }
      }
      if (cloneIds.size === 0) cloneIds.add(entry.cloneId);
    }

    let best: { index: number; meta: TreeMetadata } | null = null;
    treeMeta.forEach((m, i) => {
      if (m.clone_id == null || !cloneIds.has(m.clone_id)) return;
      if (tp && m.timepoint && m.timepoint !== tp) return;
      if (!best || (m.clone_size ?? 0) > (best.meta.clone_size ?? 0)) {
        best = { index: i, meta: m };
      }
    });

    if (!best && tp) {
      treeMeta.forEach((m, i) => {
        if (m.clone_id == null || !cloneIds.has(m.clone_id)) return;
        if (!best || (m.clone_size ?? 0) > (best.meta.clone_size ?? 0)) {
          best = { index: i, meta: m };
        }
      });
    }

    return best;
  }

  $: selectedDynamicsTree = findDynamicsTree(
    selectedDynamicsEntry,
    selectedDynamicsTimepoint,
    $resultsState.treeMetadata
  );

  function getTreeNewickPath(pngPath: string): string {
    return pngPath.replace('.png', '.newick');
  }

  function getTreeLabel(meta: TreeMetadata): string {
    const cid = meta.clone_id;
    const size = meta.clone_size;
    const tp = meta.timepoint;
    let label = cid != null ? `Clone ${cid}` : 'Tree';
    if (size > 0) label += ` (${size} seqs)`;
    if (tp) label += ` — ${tp}`;
    return label;
  }

  function getPatientColor(index: number): string {
    const colors = [
      '#4CAF50', '#2196F3', '#FF9800', '#E91E63', '#9B27B0',
      '#00BCD4', '#CDDC39', '#FF5722', '#795548', '#607D8B'
    ];
    return colors[index % colors.length];
  }

  function cloneDisplayId(id: string): string {
    return id.replace('clone_', 'Clone ');
  }


</script>

<div class="public-clones-container">
  {#if $resultsState.sequences.length === 0}
    <div class="empty-state">
      <div class="empty-icon">
        <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
          <circle cx="20" cy="28" r="8" stroke="currentColor" stroke-width="2"/>
          <circle cx="44" cy="28" r="8" stroke="currentColor" stroke-width="2"/>
          <path d="M28 28h8M32 16v4M32 44v4M20 42c4 4 20 4 24 0" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
      </div>
      <h3 class="empty-title">No Analysis Data</h3>
      <p class="empty-description">
        Run the main analysis first to identify public clones shared across patients.
      </p>
    </div>
  {:else}
    <div class="sections-scroll">

      <!-- ═══════════════════════════════════════════════════════════════════
           SECTION 1: Shared Clones (per timepoint)
           ═══════════════════════════════════════════════════════════════════ -->
      <section class="collapsible-section">
        <button class="section-header" on:click={() => sharedOpen = !sharedOpen}>
          <span class="section-chevron" class:open={sharedOpen}>
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M4 2l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </span>
          <h2 class="section-title">Shared Clones</h2>
          <span class="section-subtitle">per timepoint</span>
          {#if $resultsState.publicClonesData}
            <span class="section-badge">{$resultsState.publicClonesData.stats.total_public_clones} found</span>
          {/if}
        </button>

        {#if sharedOpen}
          <div class="section-body">
            <!-- Info banner -->
            <div class="info-banner">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" class="info-icon">
                <circle cx="8" cy="8" r="7" stroke="currentColor" stroke-width="1.5"/>
                <path d="M8 7v4M8 5.5v0" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
              </svg>
              <span>
                Shared clones are identified <strong>within each timepoint independently</strong>.
                Clonality is defined per-timepoint by DefineClones &mdash; clones from different
                timepoints have distinct ID spaces.
                {#if hasTimepoints}Select a timepoint to view clones shared across patients.{/if}
              </span>
            </div>

            <!-- Timepoint selector -->
            {#if hasTimepoints}
              <div class="tp-selector">
                {#each timepointLabels as tp}
                  <button
                    class="tp-pill"
                    class:active={selectedTimepoint === tp}
                    on:click={() => { selectedTimepoint = tp; }}
                  >
                    {tp}
                  </button>
                {/each}
              </div>
            {/if}

            {#if !hasResults}
              <div class="loading-state">
                <div class="spinner"></div>
                <span>Computing shared clones...</span>
              </div>
            {:else if $resultsState.publicClonesData && $resultsState.publicClonesData.public_clones.length === 0}
              <div class="empty-inline">
                No clones are shared across multiple patients in {selectedTimepoint || 'this dataset'}.
              </div>
            {:else}
              <!-- Stats row -->
              <div class="stats-dashboard">
                <div class="stat-card">
                  <div class="stat-value">{$resultsState.publicClonesData?.stats.total_public_clones ?? 0}</div>
                  <div class="stat-label">Shared Clones</div>
                </div>
                <div class="stat-card">
                  <div class="stat-value">{$resultsState.publicClonesData?.stats.total_patients ?? 0}</div>
                  <div class="stat-label">Patients</div>
                </div>
                <div class="stat-card">
                  <div class="stat-value">{$resultsState.publicClonesData?.stats.max_patient_sharing ?? 0}</div>
                  <div class="stat-label">Max Sharing</div>
                </div>
                <div class="stat-card">
                  <div class="stat-value">{$resultsState.publicClonesData?.stats.total_sequences_in_public_clones ?? 0}</div>
                  <div class="stat-label">Total Sequences</div>
                </div>
              </div>

              <!-- Split view -->
              <div class="shared-content">
                <!-- Left: Clone list -->
                <div class="clones-list">
                  <div class="list-header">
                    <h3>Shared Clones</h3>
                    <label class="topn-label">
                      Top
                      <select bind:value={topN} on:change={handleTopNChange}>
                        <option value={10}>10</option>
                        <option value={20}>20</option>
                        <option value={50}>50</option>
                        <option value={100}>100</option>
                      </select>
                    </label>
                  </div>
                  <div class="clone-cards">
                    {#each ($resultsState.publicClonesData?.top_x ?? []) as clone, index}
                      <button
                        class="clone-card"
                        class:selected={selectedCloneId === clone.id}
                        on:click={() => selectClone(clone.id)}
                      >
                        <div class="clone-rank">#{index + 1}</div>
                        <div class="clone-info">
                          <div class="clone-id-label">{cloneDisplayId(clone.id)}</div>
                          <code class="cdr3-subtitle">{clone.cdr3_aa || '(no CDR3)'}</code>
                          <div class="clone-genes">
                            {#if clone.v_gene}<span class="gene-badge v-gene">{clone.v_gene}</span>{/if}
                            {#if clone.j_gene}<span class="gene-badge j-gene">{clone.j_gene}</span>{/if}
                          </div>
                          <div class="clone-metrics">
                            <span class="metric">{clone.patient_count} patients</span>
                            <span class="metric">{clone.sequence_count} seqs</span>
                          </div>
                        </div>
                      </button>
                    {/each}
                  </div>
                </div>

                <!-- Right: Detail/Heatmap -->
                <div class="details-panel">
                  <div class="detail-tabs">
                    <button class="tab" class:active={activeVizTab === 'heatmap'} on:click={() => activeVizTab = 'heatmap'}>
                      Patient &times; Clone Heatmap
                    </button>
                    <button class="tab" class:active={activeVizTab === 'details'} on:click={() => activeVizTab = 'details'}>
                      Clone Details
                    </button>
                  </div>

                  <div class="detail-content" class:heatmap-active={activeVizTab === 'heatmap'}>
                    {#if activeVizTab === 'heatmap' && $resultsState.publicClonesData}
                      <div class="heatmap-wrapper">
                        <HeatmapViz
                          data={$resultsState.publicClonesData.visualizations.heatmap}
                          onCloneClick={selectCloneByIndex}
                        />
                      </div>
                    {:else if activeVizTab === 'details'}
                      {#if selectedClone}
                        <div class="clone-detail">
                          <h2 class="detail-title">{cloneDisplayId(selectedClone.id)}</h2>
                          <div class="detail-card">
                            <h3>CDR3 Region</h3>
                            <div class="detail-row">
                              <span class="detail-label">Amino Acid:</span>
                              <code>{selectedClone.cdr3_aa}</code>
                            </div>
                            {#if selectedClone.cdr3_dna}
                              <div class="detail-row">
                                <span class="detail-label">DNA:</span>
                                <code class="dna">{selectedClone.cdr3_dna}</code>
                              </div>
                            {/if}
                            <div class="detail-row">
                              <span class="detail-label">Length:</span>
                              <span>{selectedClone.cdr3_aa.length} aa</span>
                            </div>
                          </div>
                          <div class="detail-card">
                            <h3>Gene Usage</h3>
                            <div class="detail-row">
                              <span class="detail-label">V Gene:</span>
                              <span>{selectedClone.v_gene}</span>
                            </div>
                            <div class="detail-row">
                              <span class="detail-label">J Gene:</span>
                              <span>{selectedClone.j_gene}</span>
                            </div>
                          </div>
                          <div class="detail-card">
                            <h3>Patient Distribution ({selectedClone.patient_count} patients, {selectedClone.sequence_count} sequences)</h3>
                            <div class="patient-list">
                              {#each selectedClone.patients as patient, pidx}
                                <div class="patient-item" style="border-left: 4px solid {getPatientColor(pidx)}">
                                  <div class="patient-name">{patient}</div>
                                  <div class="patient-count">
                                    {(selectedClone.sequences_by_patient?.[patient]?.length ?? 0)} sequences
                                  </div>
                                </div>
                              {/each}
                            </div>
                          </div>
                        </div>
                      {:else}
                        <div class="empty-selection">
                          <p>Select a clone from the list to view details</p>
                        </div>
                      {/if}
                    {/if}
                  </div>
                </div>
              </div>
            {/if}
          </div>
        {/if}
      </section>

      <!-- ═══════════════════════════════════════════════════════════════════
           SECTION 2: Clonal Dynamics (across timepoints)
           ═══════════════════════════════════════════════════════════════════ -->
      {#if hasTimepoints}
        <section class="collapsible-section">
          <button class="section-header" on:click={() => dynamicsOpen = !dynamicsOpen}>
            <span class="section-chevron" class:open={dynamicsOpen}>
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path d="M4 2l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </span>
            <h2 class="section-title">Clonal Dynamics</h2>
            <span class="section-subtitle">across timepoints</span>
            {#if dynamicsData}
              <span class="section-badge">{dynamicsData.stats.total} tracked</span>
            {/if}
          </button>

          {#if dynamicsOpen}
            <div class="section-body">
              <!-- Info banner -->
              <div class="info-banner">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" class="info-icon">
                  <circle cx="8" cy="8" r="7" stroke="currentColor" stroke-width="1.5"/>
                  <path d="M8 7v4M8 5.5v0" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                </svg>
                <span>
                  Tracks clones/lineages across timepoints using
                  {#if dynamicsData?.entries.some(e => e.lineageId != null)}
                    <strong>lineage IDs</strong> (cross-timepoint lineage grouping).
                  {:else}
                    <strong>clone IDs</strong> (per-timepoint clonality).
                  {/if}
                  Clones are classified by their expansion dynamics over time.
                </span>
              </div>

              {#if dynamicsData && dynamicsData.entries.length > 0}
                <!-- Status filter pills -->
                <div class="status-filter-row">
                  <span class="status-filter-label">Show:</span>
                  <div class="status-pills">
                    {#each DYNAMICS_STATUSES as { value, label }}
                      <button
                        type="button"
                        class="status-pill-filter"
                        class:active={activeStatuses[value]}
                        class:inactive={!activeStatuses[value]}
                        class:persistent={value === 'persistent'}
                        class:expanding={value === 'expanding'}
                        class:contracting={value === 'contracting'}
                        class:disappeared={value === 'disappeared'}
                        class:late_emerging={value === 'late_emerging'}
                        class:transient={value === 'transient'}
                        on:click={() => toggleStatusFilter(value)}
                      >
                        {label}
                      </button>
                    {/each}
                  </div>
                </div>

                <!-- Stats -->
                <div class="dynamics-stats">
                  <div class="dstat persistent">
                    <span class="dstat-val">{dynamicsData.stats.persistent}</span>
                    <span class="dstat-label">Persistent</span>
                  </div>
                  <div class="dstat expanding">
                    <span class="dstat-val">{dynamicsData.stats.expanding}</span>
                    <span class="dstat-label">Expanding</span>
                  </div>
                  <div class="dstat contracting">
                    <span class="dstat-val">{dynamicsData.stats.contracting}</span>
                    <span class="dstat-label">Contracting</span>
                  </div>
                  <div class="dstat disappeared">
                    <span class="dstat-val">{dynamicsData.stats.disappeared}</span>
                    <span class="dstat-label">Disappeared</span>
                  </div>
                  <div class="dstat late-emerging">
                    <span class="dstat-val">{dynamicsData.stats.lateEmerging}</span>
                    <span class="dstat-label">Late Emerging</span>
                  </div>
                </div>

                <!-- Top-N control -->
                <div class="dynamics-controls">
                  <label class="topn-label">
                    Show top
                    <select bind:value={dynamicsTopN} on:change={handleDynamicsTopNChange}>
                      <option value={10}>10</option>
                      <option value={20}>20</option>
                      <option value={30}>30</option>
                      <option value={50}>50</option>
                      <option value={100}>100</option>
                      <option value={250}>250</option>
                    </select>
                    clones
                  </label>
                </div>

                <!-- 3-column layout: Heatmap | Tree | Detail -->
                <div class="dynamics-split">
                  <!-- Left: Heatmap matrix -->
                  <div class="dynamics-heatmap-section">
                    <ClonalDynamicsHeatmap
                      entries={filteredDynamicsEntries}
                      timepointLabels={dynamicsData.timepointLabels}
                      timepointTotals={dynamicsData.timepointTotals}
                      onCloneClick={handleDynamicsCloneClick}
                    />
                  </div>

                  <!-- Middle: Phylogenetic tree -->
                  <div class="dynamics-tree-panel">
                    {#if selectedDynamicsEntry}
                      {#if selectedDynamicsTree}
                        <div class="dynamics-tree-section">
                          <div class="dynamics-tree-header">
                            <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                              <path d="M8 2v4M8 6H4v4M8 6h4v4M4 10v4M12 10v4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                            </svg>
                            <span class="dynamics-tree-title">Phylogenetic Tree</span>
                            <span class="dynamics-tree-label">{getTreeLabel(selectedDynamicsTree.meta)}</span>
                          </div>
                          <div class="dynamics-tree-container">
                            <InteractiveTree
                              newickPath={getTreeNewickPath(selectedDynamicsTree.meta.path)}
                              treeName={getTreeLabel(selectedDynamicsTree.meta)}
                              cloneSize={selectedDynamicsTree.meta.clone_size || 0}
                            />
                          </div>
                        </div>
                      {:else}
                        <div class="dynamics-tree-empty-full">
                          <svg width="32" height="32" viewBox="0 0 16 16" fill="none">
                            <path d="M8 2v4M8 6H4v4M8 6h4v4M4 10v4M12 10v4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                          </svg>
                          <span>No phylogenetic tree available{selectedDynamicsTimepoint ? ` for ${selectedDynamicsTimepoint}` : ''}</span>
                          <span class="dynamics-tree-hint">Trees are built for the top 20 clones per timepoint. Click a timepoint cell to look up trees.</span>
                        </div>
                      {/if}
                    {:else}
                      <div class="dynamics-tree-empty-full">
                        <svg width="32" height="32" viewBox="0 0 16 16" fill="none">
                          <path d="M8 2v4M8 6H4v4M8 6h4v4M4 10v4M12 10v4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                        </svg>
                        <span>Select a clone to view its phylogenetic tree</span>
                      </div>
                    {/if}
                  </div>

                  <!-- Right: Lineage detail -->
                  <div class="dynamics-detail-panel">
                    {#if selectedDynamicsEntry}
                      <div class="dynamics-detail-card">
                        <div class="dynamics-detail-header">
                          <h3>{selectedDynamicsEntry.cloneLabel}</h3>
                          <span class="status-pill {selectedDynamicsEntry.status}">
                            {selectedDynamicsEntry.status.replace('_', ' ')}
                          </span>
                        </div>
                        <div class="dynamics-detail-body">
                          <div class="detail-row">
                            <span class="detail-label">CDR3 AA:</span>
                            <code>{selectedDynamicsEntry.cdr3Aa || '(none)'}</code>
                          </div>
                          <div class="detail-row">
                            <span class="detail-label">V Gene:</span>
                            <span>{selectedDynamicsEntry.vGene}</span>
                          </div>
                          <div class="detail-row">
                            <span class="detail-label">J Gene:</span>
                            <span>{selectedDynamicsEntry.jGene}</span>
                          </div>
                          <div class="detail-row">
                            <span class="detail-label">Total seqs:</span>
                            <span>{selectedDynamicsEntry.totalRawCount} sequences</span>
                          </div>
                          <h4 class="tp-sizes-heading">Timepoint Frequencies</h4>
                          <div class="tp-sizes">
                            {#each selectedDynamicsEntry.timepointSizes as tpSize}
                              <div class="tp-size-item">
                                <span class="tp-size-label">{tpSize.label}</span>
                                <div class="tp-size-bar-bg">
                                  <div
                                    class="tp-size-bar"
                                    style="width: {Math.max(2, tpSize.frequency / Math.max(0.001, ...selectedDynamicsEntry.timepointSizes.map(t => t.frequency)) * 100)}%"
                                  ></div>
                                </div>
                                <span class="tp-size-val">{(tpSize.frequency * 100).toFixed(2)}%</span>
                                <span class="tp-size-raw">({tpSize.rawCount})</span>
                              </div>
                            {/each}
                          </div>
                          {#if selectedDynamicsEntry.cloneIdsByTimepoint}
                            <h4 class="tp-sizes-heading">Clone IDs by Timepoint</h4>
                            <div class="clone-ids-by-tp">
                              {#each Object.entries(selectedDynamicsEntry.cloneIdsByTimepoint) as [tp, cids]}
                                <div class="clone-tp-row">
                                  <span class="clone-tp-label">{tp}:</span>
                                  <span class="clone-tp-ids">{cids.join(', ')}</span>
                                </div>
                              {/each}
                            </div>
                          {/if}
                        </div>
                      </div>
                    {:else}
                      <div class="dynamics-empty-detail">
                        <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
                          <rect x="4" y="8" width="32" height="24" rx="3" stroke="currentColor" stroke-width="1.5"/>
                          <path d="M4 14h32M14 14v18" stroke="currentColor" stroke-width="1.5"/>
                        </svg>
                        <p>Select a lineage from the heatmap to view details</p>
                      </div>
                    {/if}
                  </div>
                </div>
              {:else}
                <div class="empty-inline">
                  Clonal dynamics require at least 2 timepoints with clonal data.
                </div>
              {/if}
            </div>
          {/if}
        </section>
      {/if}
    </div>
  {/if}
</div>

<style>
  .public-clones-container {
    height: 100%;
    background: var(--gray-50);
    overflow: hidden;
    position: relative;
    display: flex;
    flex-direction: column;
  }

  .sections-scroll {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: var(--space-4);
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
  }

  /* ── Empty / Loading states ── */
  .empty-state, .loading-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    padding: var(--space-8);
    text-align: center;
    gap: var(--space-4);
    color: var(--text-tertiary);
  }

  .empty-icon { color: var(--gray-300); margin-bottom: var(--space-2); }
  .empty-title { font-size: var(--text-xl); font-weight: var(--font-semibold); color: var(--text-primary); margin: 0; }
  .empty-description { font-size: var(--text-sm); color: var(--text-tertiary); max-width: 400px; margin: 0; }

  .spinner {
    width: 24px; height: 24px;
    border: 3px solid var(--gray-200);
    border-top-color: var(--color-primary);
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  .empty-inline {
    text-align: center;
    padding: var(--space-8);
    color: var(--text-tertiary);
    font-size: var(--text-sm);
  }

  /* ── Collapsible sections ── */
  .collapsible-section {
    border: 1px solid var(--border-light);
    border-radius: var(--border-radius-lg);
    background: var(--surface-raised);
    overflow: hidden;
  }

  .section-header {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-4) var(--space-5);
    width: 100%;
    background: none;
    border: none;
    cursor: pointer;
    font-family: var(--font-sans);
    transition: background var(--transition-fast);
  }
  .section-header:hover { background: var(--gray-50); }

  .section-chevron {
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-tertiary);
    transition: transform var(--transition-fast);
    transform: rotate(0deg);
  }
  .section-chevron.open { transform: rotate(90deg); }

  .section-title {
    font-size: var(--text-lg);
    font-weight: var(--font-semibold);
    margin: 0;
    color: var(--text-primary);
  }

  .section-subtitle {
    font-size: var(--text-sm);
    color: var(--text-tertiary);
  }

  .section-badge {
    margin-left: auto;
    font-size: var(--text-xs);
    font-weight: var(--font-medium);
    padding: var(--space-1) var(--space-2);
    border-radius: var(--border-radius-full);
    background: var(--color-primary-light);
    color: var(--color-primary);
  }

  .section-body {
    padding: 0 var(--space-5) var(--space-5);
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
  }

  /* ── Info banner ── */
  .info-banner {
    display: flex;
    align-items: flex-start;
    gap: var(--space-3);
    padding: var(--space-3) var(--space-4);
    background: var(--color-info-light);
    border-radius: var(--border-radius-md);
    font-size: var(--text-sm);
    color: var(--text-secondary);
    line-height: var(--leading-relaxed);
  }
  .info-icon {
    flex-shrink: 0;
    margin-top: 2px;
    color: var(--color-info);
  }

  /* ── Timepoint pill selector ── */
  .tp-selector {
    display: flex;
    gap: var(--space-2);
    flex-wrap: wrap;
  }

  .tp-pill {
    padding: var(--space-2) var(--space-4);
    border: 1px solid var(--border-light);
    border-radius: var(--border-radius-full);
    background: var(--surface-raised);
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    color: var(--text-secondary);
    cursor: pointer;
    transition: all var(--transition-fast);
    font-family: var(--font-sans);
  }
  .tp-pill:hover { border-color: var(--color-primary-muted); color: var(--color-primary); }
  .tp-pill.active {
    background: var(--color-primary);
    color: white;
    border-color: var(--color-primary);
  }

  /* ── Stats Dashboard ── */
  .stats-dashboard {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: var(--space-3);
  }
  .stat-card {
    background: var(--gray-50);
    padding: var(--space-3);
    border-radius: var(--border-radius-md);
    text-align: center;
  }
  .stat-value {
    font-size: var(--text-2xl);
    font-weight: var(--font-bold);
    color: var(--color-primary);
  }
  .stat-label {
    font-size: var(--text-xs);
    color: var(--text-secondary);
    margin-top: var(--space-1);
  }

  /* ── Shared Content Split View ── */
  .shared-content {
    display: flex;
    gap: var(--space-4);
    min-height: 350px;
    max-height: 500px;
  }

  .clones-list {
    width: 340px;
    background: var(--surface-raised);
    border: 1px solid var(--border-light);
    border-radius: var(--border-radius-md);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    flex-shrink: 0;
  }
  .list-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--space-3) var(--space-4);
    border-bottom: 1px solid var(--border-light);
  }
  .list-header h3 { font-size: var(--text-sm); font-weight: var(--font-semibold); margin: 0; }

  .topn-label {
    display: flex;
    align-items: center;
    gap: var(--space-1);
    font-size: var(--text-xs);
    color: var(--text-secondary);
  }
  .topn-label select {
    padding: 2px 4px;
    font-size: var(--text-xs);
    border: 1px solid var(--border-light);
    border-radius: var(--border-radius-sm);
  }

  .clone-cards { flex: 1; overflow-y: auto; padding: var(--space-2); }

  .clone-card {
    display: flex;
    gap: var(--space-3);
    padding: var(--space-3);
    background: var(--surface-raised);
    border: 2px solid var(--border-light);
    border-radius: var(--border-radius-md);
    cursor: pointer;
    transition: all var(--transition-fast);
    width: 100%;
    text-align: left;
    margin-bottom: var(--space-2);
    font-family: var(--font-sans);
  }
  .clone-card:hover { border-color: var(--color-primary-light); transform: translateY(-1px); box-shadow: var(--shadow-sm); }
  .clone-card.selected { border-color: var(--color-primary); background: var(--color-primary-light); }

  .clone-rank { font-size: var(--text-lg); font-weight: var(--font-bold); color: var(--color-primary); min-width: 30px; }
  .clone-info { flex: 1; min-width: 0; }

  .clone-id-label {
    font-size: var(--text-sm);
    font-weight: var(--font-semibold);
    color: var(--text-primary);
    margin-bottom: 2px;
  }

  .cdr3-subtitle {
    display: block;
    background: var(--gray-100);
    padding: 2px 6px;
    border-radius: var(--border-radius-sm);
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--text-secondary);
    word-break: break-all;
    margin-bottom: var(--space-1);
  }

  .clone-genes { display: flex; gap: var(--space-2); margin-bottom: var(--space-1); }
  .gene-badge { padding: 2px 6px; border-radius: var(--border-radius-sm); font-size: 10px; font-weight: var(--font-medium); }
  .v-gene { background: #E3F2FD; color: #1976D2; }
  .j-gene { background: #F3E5F5; color: #7B1FA2; }

  .clone-metrics { display: flex; gap: var(--space-3); font-size: var(--text-xs); color: var(--text-secondary); }
  .metric { display: flex; align-items: center; gap: 4px; }

  /* ── Details panel ── */
  .details-panel {
    flex: 1;
    background: var(--surface-raised);
    border: 1px solid var(--border-light);
    border-radius: var(--border-radius-md);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .detail-tabs { display: flex; border-bottom: 1px solid var(--border-light); flex-shrink: 0; }
  .tab {
    padding: var(--space-3) var(--space-4);
    background: none; border: none;
    font-size: var(--text-sm); font-weight: var(--font-medium);
    color: var(--text-secondary); cursor: pointer;
    border-bottom: 2px solid transparent;
    transition: all var(--transition-fast);
    font-family: var(--font-sans);
  }
  .tab:hover { color: var(--text-primary); }
  .tab.active { color: var(--color-primary); border-bottom-color: var(--color-primary); }

  .detail-content { flex: 1; overflow: auto; min-height: 0; padding: var(--space-4); }
  .detail-content.heatmap-active { padding: 0; overflow: hidden; display: flex; flex-direction: column; }
  .heatmap-wrapper { flex: 1; min-height: 0; width: 100%; display: flex; flex-direction: column; }

  .detail-title {
    font-size: var(--text-lg); font-weight: var(--font-bold);
    margin-bottom: var(--space-4);
    color: var(--text-primary);
  }
  .detail-card {
    background: var(--gray-50);
    padding: var(--space-4);
    border-radius: var(--border-radius-md);
    margin-bottom: var(--space-4);
  }
  .detail-card h3 { font-size: var(--text-sm); font-weight: var(--font-semibold); margin-bottom: var(--space-3); color: var(--text-secondary); }
  .detail-row { display: flex; gap: var(--space-3); margin-bottom: var(--space-2); align-items: baseline; }
  .detail-label { min-width: 100px; color: var(--text-secondary); font-size: var(--text-sm); flex-shrink: 0; }
  .detail-row code { background: white; padding: 2px 6px; border-radius: var(--border-radius-sm); font-size: var(--text-sm); }
  .detail-row code.dna { word-break: break-all; font-size: var(--text-xs); }

  .patient-list { display: flex; flex-direction: column; gap: var(--space-2); }
  .patient-item {
    padding: var(--space-3);
    background: white;
    border-radius: var(--border-radius-sm);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .patient-name { font-weight: var(--font-medium); font-size: var(--text-sm); }
  .patient-count { color: var(--text-secondary); font-size: var(--text-sm); }

  .empty-selection { height: 100%; display: flex; align-items: center; justify-content: center; color: var(--text-tertiary); font-size: var(--text-sm); }

  /* ═══════════════════════════════════════
     Section 2: Clonal Dynamics styles
     ═══════════════════════════════════════ */

  /* ── Status filter pills (like timepoint selector) ── */
  .status-filter-row {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    margin-bottom: var(--space-4);
  }
  .status-filter-label {
    font-size: var(--text-sm);
    color: var(--text-secondary);
    flex-shrink: 0;
  }
  .status-pills {
    display: flex;
    gap: var(--space-2);
    flex-wrap: wrap;
  }
  .status-pill-filter {
    padding: var(--space-1) var(--space-3);
    border: 1px solid transparent;
    border-radius: var(--border-radius-full);
    font-size: var(--text-xs);
    font-weight: var(--font-medium);
    cursor: pointer;
    transition: all var(--transition-fast);
    font-family: var(--font-sans);
  }
  .status-pill-filter.inactive {
    opacity: 0.45;
    background: var(--gray-100);
    color: var(--text-tertiary);
    border-color: var(--border-light);
  }
  .status-pill-filter.inactive:hover {
    opacity: 0.7;
  }
  .status-pill-filter.active.persistent { background: #E3F2FD; color: #1565C0; border-color: #1565C0; }
  .status-pill-filter.active.expanding { background: #E8F5E9; color: #2E7D32; border-color: #2E7D32; }
  .status-pill-filter.active.contracting { background: #FFEBEE; color: #C62828; border-color: #C62828; }
  .status-pill-filter.active.disappeared { background: #F5F5F5; color: #616161; border-color: #616161; }
  .status-pill-filter.active.late_emerging { background: #FFF3E0; color: #E65100; border-color: #E65100; }
  .status-pill-filter.active.transient { background: #F3E5F5; color: #7B1FA2; border-color: #7B1FA2; }

  .dynamics-stats {
    display: flex;
    gap: var(--space-3);
    flex-wrap: wrap;
  }

  .dstat {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: var(--space-3) var(--space-5);
    border-radius: var(--border-radius-md);
    min-width: 100px;
  }
  .dstat-val { font-size: var(--text-2xl); font-weight: var(--font-bold); }
  .dstat-label { font-size: var(--text-xs); font-weight: var(--font-medium); margin-top: 2px; }

  .dstat.persistent { background: #E3F2FD; }
  .dstat.persistent .dstat-val { color: #1565C0; }
  .dstat.persistent .dstat-label { color: #1565C0; }

  .dstat.expanding { background: #E8F5E9; }
  .dstat.expanding .dstat-val { color: #2E7D32; }
  .dstat.expanding .dstat-label { color: #2E7D32; }

  .dstat.contracting { background: #FFEBEE; }
  .dstat.contracting .dstat-val { color: #C62828; }
  .dstat.contracting .dstat-label { color: #C62828; }

  .dstat.disappeared { background: #F5F5F5; }
  .dstat.disappeared .dstat-val { color: #616161; }
  .dstat.disappeared .dstat-label { color: #616161; }

  .dstat.late-emerging { background: #FFF3E0; }
  .dstat.late-emerging .dstat-val { color: #E65100; }
  .dstat.late-emerging .dstat-label { color: #E65100; }

  .dynamics-controls {
    display: flex;
    justify-content: flex-end;
  }

  /* ── Dynamics 3-column layout (heatmap | tree | detail) ── */
  .dynamics-split {
    display: flex;
    gap: var(--space-4);
    height: 500px;
    overflow: hidden;
  }

  .dynamics-heatmap-section {
    flex: 0 0 auto;
    min-width: 0;
    height: 100%;
    overflow: auto;
    border: 1px solid var(--border-light);
    border-radius: var(--border-radius-md);
  }

  .dynamics-tree-panel {
    flex: 1;
    min-width: 0;
    height: 100%;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .dynamics-detail-panel {
    width: 300px;
    flex-shrink: 0;
    height: 100%;
    display: flex;
    flex-direction: column;
    overflow-y: auto;
  }

  .dynamics-empty-detail {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: var(--space-3);
    color: var(--text-muted);
    font-size: var(--text-sm);
    text-align: center;
    border: 1px dashed var(--border-light);
    border-radius: var(--border-radius-md);
    padding: var(--space-6);
  }

  .dynamics-empty-detail p { margin: 0; }

  /* ── Dynamics detail card ── */
  .dynamics-detail-card {
    border: 1px solid var(--border-light);
    border-radius: var(--border-radius-md);
    overflow: hidden;
    flex: 1;
    display: flex;
    flex-direction: column;
  }

  .dynamics-detail-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--space-3) var(--space-4);
    background: var(--gray-50);
    border-bottom: 1px solid var(--border-light);
  }
  .dynamics-detail-header h3 {
    font-size: var(--text-base);
    font-weight: var(--font-semibold);
    margin: 0;
  }

  .status-pill {
    font-size: var(--text-xs);
    font-weight: var(--font-semibold);
    padding: var(--space-1) var(--space-3);
    border-radius: var(--border-radius-full);
    text-transform: capitalize;
  }
  .status-pill.persistent { background: #E3F2FD; color: #1565C0; }
  .status-pill.expanding { background: #E8F5E9; color: #2E7D32; }
  .status-pill.contracting { background: #FFEBEE; color: #C62828; }
  .status-pill.disappeared { background: #F5F5F5; color: #616161; }
  .status-pill.late_emerging { background: #FFF3E0; color: #E65100; }
  .status-pill.transient { background: #F3E5F5; color: #7B1FA2; }

  .dynamics-detail-body {
    padding: var(--space-4);
    flex: 1;
    overflow-y: auto;
  }

  .tp-sizes {
    margin-top: var(--space-3);
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }
  .tp-size-item {
    display: flex;
    align-items: center;
    gap: var(--space-3);
  }
  .tp-size-label {
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    min-width: 40px;
    color: var(--text-secondary);
  }
  .tp-size-bar-bg {
    flex: 1;
    height: 14px;
    background: var(--gray-100);
    border-radius: var(--border-radius-full);
    overflow: hidden;
  }
  .tp-size-bar {
    height: 100%;
    background: var(--color-primary);
    border-radius: var(--border-radius-full);
    transition: width var(--transition-normal);
  }
  .tp-size-val {
    font-size: var(--text-sm);
    font-weight: var(--font-semibold);
    min-width: 48px;
    text-align: right;
    color: var(--text-primary);
  }
  .tp-size-raw {
    font-size: var(--text-xs);
    color: var(--text-tertiary);
    min-width: 40px;
  }

  /* ── Dynamics tree section ── */
  .dynamics-tree-section {
    border: 1px solid var(--border-light);
    border-radius: var(--border-radius-md);
    overflow: hidden;
    display: flex;
    flex-direction: column;
    flex: 1;
  }

  .dynamics-tree-header {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-3);
    background: var(--gray-50);
    border-bottom: 1px solid var(--border-light);
    color: var(--text-secondary);
    flex-shrink: 0;
  }

  .dynamics-tree-title {
    font-size: var(--text-xs);
    font-weight: var(--font-semibold);
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  .dynamics-tree-label {
    font-size: var(--text-xs);
    color: var(--text-tertiary);
    margin-left: auto;
  }

  .dynamics-tree-container {
    flex: 1;
    min-height: 0;
    overflow: hidden;
    background: white;
  }

  .dynamics-tree-empty-full {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: var(--space-3);
    color: var(--text-muted);
    font-size: var(--text-sm);
    text-align: center;
    border: 1px dashed var(--border-light);
    border-radius: var(--border-radius-md);
    padding: var(--space-6);
  }

  .dynamics-tree-hint {
    font-size: var(--text-xs);
    color: var(--text-tertiary);
    max-width: 240px;
  }

  .tp-sizes-heading {
    font-size: var(--text-xs);
    font-weight: var(--font-semibold);
    color: var(--text-secondary);
    margin: var(--space-3) 0 var(--space-2) 0;
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  .clone-ids-by-tp {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .clone-tp-row {
    display: flex;
    gap: var(--space-2);
    font-size: var(--text-xs);
  }
  .clone-tp-label {
    color: var(--text-secondary);
    font-weight: var(--font-medium);
    min-width: 28px;
  }
  .clone-tp-ids {
    color: var(--text-tertiary);
    font-family: var(--font-mono, monospace);
  }
</style>
