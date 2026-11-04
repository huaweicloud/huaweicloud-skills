// Run navigation, snapshot refresh and stale-response guards.
import { $, api, connected, empty, enc, hideToast, showError, toast } from './common.js';
import { closeDrawer, renderDrawer } from './details.js';
import { manualContext } from './manual.js';
import { renderEvents, renderRun, renderRuns } from './pipeline.js';
import { node, ui } from './state.js';

function runTitlePrefix(runStatus) {
  if (['FAILED', 'AWAITING_DECISION'].includes(runStatus)) {
    return '✗ ';
  }
  if (['SUCCEEDED', 'SUCCEEDED_WITH_WARNINGS'].includes(runStatus)) {
    return '✓ ';
  }
  return '';
}
async function navigate(run = null) {
  hideToast();
  closeDrawer();
  ui.drawerContext = '';
  ui.drawerPanels.clear();
  ui.activePanel = null;
  ui.detail = null;
  ui.previewTree = null;
  ui.logFiles = [];
  ui.logContent = '';
  ui.attempt = null;
  $('#drawer-body')?.replaceChildren();
  ui.run = run;
  ui.snapshot = null;
  ui.events = [];
  ui.eventSeq = 0;
  ui.eventPage = 0;
  ui.eventCutoff = null;
  ui.eventExpanded.clear();
  ui.eventsCollapsed = true;
  ui.view = 'pipeline';
  ui.runEpoch++;
  const url = new URL(location.href);
  run ? url.searchParams.set('run', run) : url.searchParams.delete('run');
  url.searchParams.delete('token');
  history.replaceState(null, '', url);
  $('#breadcrumb').textContent = '';
  $('#workspace').innerHTML = empty('正在读取运行…');
  await refresh(true);
}
async function refresh(force = false) {
  if (ui.polling && !force) {
    return;
  }
  const run = ui.run;
  const epoch = ui.runEpoch;
  ui.polling = true;
  try {
    if (!run) {
      const data = await api('/api/runs');
      if (epoch !== ui.runEpoch) {
        return;
      }
      ui.runs = data.runs;
      connected(data.demo);
      renderRuns();
      return;
    }
    const data = await api(
      '/api/runs/' + enc(run) + (force || !ui.snapshot ? '' : '?since=' + enc(ui.snapshot.version)),
    );
    if (epoch !== ui.runEpoch) {
      return;
    }
    if (data) {
      const previousNode = node();
      const previousManual = previousNode?.kind === 'manual' ? manualContext(previousNode) : '';
      const previousAttempt = ui.attempt;
      if (ui.selected && ui.attempt === previousNode?.task_id) {
        ui.attempt = data.nodes.find((n) => n.key === ui.selected)?.task_id;
      }
      ui.snapshot = data;
      connected(data.demo);
      renderRun();
      document.title =
        runTitlePrefix(data.state.status) + data.state.pipeline_name + ' · CloudRobo';
      const taskChanged = ui.attempt !== previousAttempt;
      const statusChanged = previousNode?.display_status !== node()?.display_status;
      const manualChanged = node()?.kind === 'manual' && previousManual !== manualContext(node());
      const needsDrawer = ui.tab === 'overview' || taskChanged || statusChanged || manualChanged;
      if (ui.selected && needsDrawer && !$('#action-dialog').open) {
        await renderDrawer(true);
      }
    } else {
      connected(ui.snapshot?.demo);
    }
    const events = await api('/api/runs/' + enc(run) + '/events?after=' + ui.eventSeq);
    if (epoch !== ui.runEpoch) {
      return;
    }
    if (events.events.length) {
      ui.events.push(...events.events);
      ui.eventSeq = Math.max(ui.eventSeq, ...events.events.map((e) => e.seq));
      renderEvents();
    }
  } catch (error) {
    if (epoch !== ui.runEpoch) {
      return;
    }
    if (error.status === 404 && run) {
      $('#action-dialog').close();
      ui.modal = null;
      await navigate();
      toast('运行记录已在本地删除，已返回运行列表。');
      return;
    }
    showError(error.message);
  } finally {
    ui.polling = false;
  }
}

export { navigate, refresh };
