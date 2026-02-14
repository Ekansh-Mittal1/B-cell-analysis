<script lang="ts">
  import { onMount } from 'svelte';
  import { currentView, analysisState, resultsState, getSessions, deleteSession, renameSession } from '../stores/app';
  import type { SessionEntry } from '../stores/app';

  let expanded = false;
  let sessions: SessionEntry[] = [];
  let renamingId: string | null = null;
  let renameValue = '';
  let confirmDeleteId: string | null = null;
  let isLoadingSession = false;
  let activeSessionId: string | null = null;

  // Keep activeSessionId in sync: only when viewing results and outputDir matches a session
  $: if ($currentView === 'results' && $resultsState.outputDir && sessions.length > 0) {
    const match = sessions.find(s => s.outputDir === $resultsState.outputDir);
    if (match && !activeSessionId) {
      activeSessionId = match.id;
    }
  } else if ($currentView === 'wizard') {
    activeSessionId = null;
  }

  onMount(() => {
    sessions = getSessions();
  });

  export function refresh() {
    sessions = getSessions();
    // After refresh, try to match active session to current outputDir
    if ($resultsState.outputDir) {
      const match = sessions.find(s => s.outputDir === $resultsState.outputDir);
      if (match) activeSessionId = match.id;
    }
  }

  export function collapse() {
    expanded = false;
  }

  export function clearActive() {
    activeSessionId = null;
  }

  function toggle() {
    expanded = !expanded;
    if (expanded) {
      sessions = getSessions();
    }
  }

  async function loadSession(session: SessionEntry) {
    if (!window.electronAPI?.loadResults) return;

    const exists = await window.electronAPI.fileExists(session.outputDir + '/combined.fasta');
    if (!exists) {
      if (confirm(`The output directory for "${session.name}" no longer exists.\nRemove this session from history?`)) {
        deleteSession(session.id);
        sessions = getSessions();
      }
      return;
    }

    isLoadingSession = true;
    activeSessionId = session.id;
    expanded = false; // Auto-collapse when loading a session
    analysisState.update(s => ({ ...s, isRunning: true, isSessionLoad: true }));
    currentView.set('results');

    try {
      await window.electronAPI.loadResults(session.outputDir);
      analysisState.update(s => ({ ...s, isRunning: false }));
    } catch (e) {
      console.warn('[SessionSidebar] Failed to load session:', e);
      analysisState.update(s => ({ ...s, isRunning: false, isSessionLoad: false }));
      activeSessionId = null;
      currentView.set('wizard');
    } finally {
      isLoadingSession = false;
    }
  }

  function startRename(session: SessionEntry, event: MouseEvent) {
    event.stopPropagation();
    renamingId = session.id;
    renameValue = session.name;
  }

  function confirmRename() {
    if (renamingId && renameValue.trim()) {
      renameSession(renamingId, renameValue.trim());
      sessions = getSessions();
    }
    renamingId = null;
    renameValue = '';
  }

  function cancelRename() {
    renamingId = null;
    renameValue = '';
  }

  function handleRenameKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') confirmRename();
    if (e.key === 'Escape') cancelRename();
  }

  function handleDelete(session: SessionEntry, event: MouseEvent) {
    event.stopPropagation();
    confirmDeleteId = session.id;
  }

  function confirmDelete() {
    if (confirmDeleteId) {
      deleteSession(confirmDeleteId);
      sessions = getSessions();
    }
    confirmDeleteId = null;
  }

  function cancelDelete() {
    confirmDeleteId = null;
  }

  function formatDate(iso: string): string {
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
  }

  function formatTime(iso: string): string {
    const d = new Date(iso);
    return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
  }
</script>

<aside class="session-sidebar" class:expanded>
  <!-- Collapsed: slim vertical strip with icon -->
  {#if !expanded}
    <button class="collapse-strip" on:click={toggle} title="Session History">
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="9" cy="9" r="7"/>
        <path d="M9 5v4l2.5 1.5"/>
      </svg>
      <span class="strip-label">History</span>
      <svg class="strip-chevron" width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M4.5 3l3 3-3 3"/>
      </svg>
    </button>
  {:else}
    <!-- Expanded: full session panel -->
    <div class="panel">
      <div class="panel-header">
        <h3 class="panel-title">Session History</h3>
        <button class="collapse-btn" on:click={toggle} title="Collapse">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 3.5L5 7l4 3.5"/>
          </svg>
        </button>
      </div>

      {#if sessions.length === 0}
        <div class="empty-state">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" opacity="0.4">
            <circle cx="14" cy="14" r="11"/>
            <path d="M14 8v6l3.5 2"/>
          </svg>
          <p class="empty-text">No sessions yet</p>
          <p class="empty-sub">Completed analyses will appear here</p>
        </div>
      {:else}
        <div class="session-list">
          {#each sessions as session (session.id)}
            <div
              class="session-card"
              class:loading={isLoadingSession}
              class:active={activeSessionId === session.id}
              on:click={() => loadSession(session)}
              on:keydown={(e) => e.key === 'Enter' && loadSession(session)}
              role="button"
              tabindex="0"
            >
              <div class="session-card-body">
                {#if renamingId === session.id}
                  <!-- svelte-ignore a11y-autofocus -->
                  <input
                    class="rename-input"
                    type="text"
                    bind:value={renameValue}
                    on:keydown={handleRenameKeydown}
                    on:blur={confirmRename}
                    on:click|stopPropagation
                    autofocus
                  />
                {:else}
                  <span class="session-name">{session.name}</span>
                {/if}
                <div class="session-meta">
                  <span>{formatDate(session.date)}</span>
                  <span>{formatTime(session.date)}</span>
                </div>
                {#if session.fileCount > 0}
                  <div class="session-files">
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.2">
                      <path d="M3 1.5h3.5l3 3v6a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1v-8a1 1 0 0 1 1-1z"/>
                      <path d="M6.5 1.5v3h3"/>
                    </svg>
                    {session.fileCount} file{session.fileCount !== 1 ? 's' : ''}
                  </div>
                {/if}
              </div>
              <div class="session-card-actions">
                <button
                  class="icon-btn"
                  on:click={(e) => startRename(session, e)}
                  title="Rename"
                  disabled={isLoadingSession}
                >
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M8.5 1.5l2 2-6 6H2.5v-2l6-6z"/>
                  </svg>
                </button>
                {#if confirmDeleteId === session.id}
                  <div class="confirm-row" on:click|stopPropagation>
                    <button class="confirm-yes" on:click={confirmDelete}>Del</button>
                    <button class="confirm-no" on:click={cancelDelete}>No</button>
                  </div>
                {:else}
                  <button
                    class="icon-btn icon-btn-danger"
                    on:click={(e) => handleDelete(session, e)}
                    title="Delete"
                    disabled={isLoadingSession}
                  >
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M1.5 3.5h9M4 3.5V2.5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v1M9.5 3.5v6a1 1 0 0 1-1 1h-5a1 1 0 0 1-1-1v-6"/>
                    </svg>
                  </button>
                {/if}
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/if}
</aside>

<style>
  .session-sidebar {
    display: flex;
    flex-shrink: 0;
    background: var(--gray-50);
    border-right: 1px solid var(--border-light);
    transition: width 0.2s ease;
    width: 42px;
    overflow: hidden;
  }

  .session-sidebar.expanded {
    width: 260px;
  }

  /* --- Collapsed strip --- */
  .collapse-strip {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    width: 42px;
    padding: 16px 0;
    background: none;
    border: none;
    cursor: pointer;
    color: var(--gray-400);
    transition: color 0.15s, background 0.15s;
  }

  .collapse-strip:hover {
    color: var(--color-primary);
    background: var(--gray-100);
  }

  .strip-label {
    writing-mode: vertical-rl;
    text-orientation: mixed;
    font-size: var(--text-xs);
    font-weight: var(--font-medium);
    letter-spacing: 0.05em;
    white-space: nowrap;
  }

  .strip-chevron {
    margin-top: auto;
  }

  /* --- Expanded panel --- */
  .panel {
    display: flex;
    flex-direction: column;
    width: 260px;
    height: 100%;
    overflow: hidden;
  }

  .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 14px 10px 16px;
    border-bottom: 1px solid var(--border-light);
    flex-shrink: 0;
  }

  .panel-title {
    font-size: var(--text-sm);
    font-weight: var(--font-semibold);
    color: var(--text-primary);
    margin: 0;
  }

  .collapse-btn {
    width: 26px;
    height: 26px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: none;
    border: 1px solid var(--border-light);
    border-radius: var(--border-radius-sm);
    cursor: pointer;
    color: var(--gray-500);
    transition: all 0.15s;
  }

  .collapse-btn:hover {
    background: var(--gray-100);
    color: var(--gray-700);
  }

  /* --- Empty state --- */
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 32px 16px;
    text-align: center;
    gap: 6px;
    flex: 1;
  }

  .empty-text {
    font-size: var(--text-sm);
    color: var(--text-tertiary);
    margin: 6px 0 0;
    font-weight: var(--font-medium);
  }

  .empty-sub {
    font-size: var(--text-xs);
    color: var(--gray-400);
    margin: 0;
  }

  /* --- Session list --- */
  .session-list {
    flex: 1;
    overflow-y: auto;
    padding: 8px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .session-card {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    padding: 10px 10px 8px;
    border-radius: var(--border-radius-md);
    cursor: pointer;
    transition: background 0.12s;
    border: 1px solid transparent;
  }

  .session-card:hover {
    background: var(--surface-raised);
    border-color: var(--border-light);
  }

  .session-card.active {
    background: var(--color-primary-light);
    border-color: var(--color-primary-muted);
  }

  .session-card.active .session-name {
    color: var(--color-primary);
  }

  .session-card.loading {
    opacity: 0.5;
    pointer-events: none;
  }

  .session-card-body {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
    flex: 1;
  }

  .session-name {
    font-size: var(--text-sm);
    font-weight: var(--font-semibold);
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.3;
  }

  .session-meta {
    display: flex;
    gap: 6px;
    font-size: 10px;
    color: var(--gray-400);
  }

  .session-files {
    display: flex;
    align-items: center;
    gap: 3px;
    font-size: 10px;
    color: var(--gray-400);
    margin-top: 1px;
  }

  .session-card-actions {
    display: flex;
    flex-direction: column;
    gap: 2px;
    flex-shrink: 0;
    margin-left: 6px;
    opacity: 0;
    transition: opacity 0.12s;
  }

  .session-card:hover .session-card-actions {
    opacity: 1;
  }

  /* --- Icon buttons --- */
  .icon-btn {
    width: 22px;
    height: 22px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: none;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    color: var(--gray-400);
    transition: all 0.12s;
    padding: 0;
  }

  .icon-btn:hover {
    background: var(--gray-100);
    color: var(--gray-600);
  }

  .icon-btn-danger:hover {
    background: var(--color-error-light);
    color: var(--color-error);
  }

  .icon-btn:disabled {
    opacity: 0.4;
    pointer-events: none;
  }

  /* --- Delete confirmation --- */
  .confirm-row {
    display: flex;
    gap: 2px;
  }

  .confirm-yes, .confirm-no {
    font-size: 9px;
    padding: 2px 5px;
    border: none;
    border-radius: 3px;
    cursor: pointer;
    font-weight: var(--font-medium);
  }

  .confirm-yes {
    background: var(--color-error);
    color: white;
  }

  .confirm-yes:hover {
    opacity: 0.9;
  }

  .confirm-no {
    background: var(--gray-100);
    color: var(--gray-600);
  }

  .confirm-no:hover {
    background: var(--gray-200);
  }

  /* --- Rename input --- */
  .rename-input {
    font-size: var(--text-sm);
    font-weight: var(--font-semibold);
    color: var(--text-primary);
    background: var(--surface-raised);
    border: 1px solid var(--color-primary);
    border-radius: 4px;
    padding: 1px 5px;
    outline: none;
    width: 100%;
    box-sizing: border-box;
  }
</style>
