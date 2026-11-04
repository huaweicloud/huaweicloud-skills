// Browser entry point: event bindings, timers and initial refresh.
import { showAction, showDeleteRun, submitAction, updateConfirmation, updateRetryPool } from './actions.js';
import { $, api, cliCommand, copy, enc, json, toast } from './common.js';
import { closeDrawer, openStage, renderDrawer } from './details.js';
import { loadLogs, readLog, renderLogContent, shouldAutoRefreshLogs } from './logs.js';
import { navigate, refresh } from './navigation.js';
import { renderDAG, renderEvents, renderRun, renderRuns } from './pipeline.js';
import { loadPreview, requestPreview } from './preview.js';
import { LOG_REFRESH_INTERVAL_MS, node, runAPI, taskAPI, ui } from './state.js';

function nextTabIndex(key, index, length) {
  if (key === 'Home') {
    return 0;
  }
  if (key === 'End') {
    return length - 1;
  }
  const direction = key === 'ArrowRight' ? 1 : -1;
  return (index + direction + length) % length;
}
document.addEventListener('click', async (event) => {
  const target = event.target.closest('[data-action]');
  if (!target || target.disabled) {
    return;
  }
  event.preventDefault();
  const action = target.dataset.action;
  try {
    if (action === 'runs') {
      await navigate();
    } else if (action === 'open-run') {
      await navigate(target.dataset.run);
    } else if (action === 'delete-run') {
      await showDeleteRun(target.dataset.run);
    } else if (action === 'refresh') {
      await refresh(true);
    } else if (action === 'stage') {
      await openStage(target.dataset.key);
    } else if (action === 'drawer-close') {
      closeDrawer();
    } else if (action === 'tab') {
      ui.tab = target.dataset.tab;
      await renderDrawer();
    } else if (action === 'detail-refresh') {
      await refresh(true);
      await renderDrawer(false, true);
    } else if (action === 'event-filter') {
      ui.eventFilter = target.dataset.filter;
      ui.eventPage = 0;
      ui.eventCutoff = null;
      renderRun();
    } else if (action === 'event-toggle') {
      ui.eventsCollapsed = !ui.eventsCollapsed;
      renderRun();
      $('[data-action="event-toggle"]').focus({ preventScroll: true });
    } else if (action === 'event-page') {
      if (target.dataset.direction === 'latest') {
        ui.eventPage = 0;
      } else {
        ui.eventCutoff ??= ui.eventSeq;
        ui.eventPage = Math.max(0, ui.eventPage + Number(target.dataset.direction));
      }
      if (!ui.eventPage) {
        ui.eventCutoff = null;
      }
      renderEvents();
      $('#timeline').scrollTop = 0;
      $(`[data-action="event-page"][data-direction="${target.dataset.direction}"]`).focus({ preventScroll: true });
    } else if (action === 'view-pipeline' || action === 'view-summary') {
      ui.view = action === 'view-summary' ? 'summary' : 'pipeline';
      renderRun();
    } else if (action === 'copy') {
      await copy(target.dataset.copy);
    } else if (action === 'copy-output') {
      await copy(ui.snapshot.state.output.target_path);
    } else if (action === 'copy-config') {
      await copy(json(ui.detail.record.task_config));
    } else if (action === 'copy-cli') {
      const c = ui.detail.record.task_config;
      const args = [
        'cloudrobo',
        'dataset',
        node().kind,
        'create-task',
        '--name',
        ui.detail.record.task_name || node().task_name || 'new-task-name',
      ];
      if (node().kind === 'proc') {
        args.push('--algo-type', c.algo_type || 'PRESET_ASSETS');
      }
      args.push('--task-config', JSON.stringify(c));
      await copy(cliCommand(args));
    } else if (action === 'export') {
      location.href = runAPI('/summary');
    } else if (['retry', 'skip', 'terminate', 'request-skip', 'cancel-skip'].includes(action)) {
      await showAction(action);
    } else if (action === 'dialog-close') {
      if (ui.busy) {
        toast('操作正在执行，请等待结果。');
      } else {
        $('#action-dialog').close();
      }
    } else if (action === 'action-submit') {
      await submitAction();
    } else if (action === 'log-full') {
      ui.logFull = true;
      await readLog();
    } else if (action === 'log-refresh') {
      await loadLogs();
    } else if (action === 'log-download') {
      const f = ui.logFiles[ui.logFile];
      const result = await api(taskAPI('/logs/download'), {
        file: f.file_name,
        path: f.file_path,
      });
      location.href = result.url;
      toast('日志已保存到运行目录的 logs/，正在下载。');
    } else if (action === 'error-next' || action === 'error-prev') {
      const errors = [...document.querySelectorAll('.log-line.error')];
      if (!errors.length) {
        return;
      }
      ui.errorIndex =
        (ui.errorIndex + (action === 'error-next' ? 1 : -1) + errors.length) % errors.length;
      errors[ui.errorIndex].scrollIntoView({
        block: 'nearest',
      });
      toast(`第 ${ui.errorIndex + 1} / ${errors.length} 个错误行`);
    } else if (action === 'frames-refresh') {
      await loadPreview();
    } else if (action === 'frame-preview') {
      await requestPreview('/preview?file=' + enc(target.dataset.file));
    } else if (action === 'report-preview' || action === 'report-download') {
      await requestPreview('/preview?download=' + (action === 'report-download' ? '1' : '0'));
    } else if (action === 'open-report') {
      await openStage(target.dataset.key, 'preview');
    }
  } catch (error) {
    toast(error.message);
  }
});
document.addEventListener('toggle', (event) => {
  if (!event.target.matches?.('.event-full')) {
    return;
  }
  const seq = Number(event.target.dataset.seq);
  if (event.target.open) {
    ui.eventExpanded.add(seq);
  } else {
    ui.eventExpanded.delete(seq);
  }
}, true);
document.addEventListener('input', (event) => {
  const el = event.target;
  if (el.id === 'run-search') {
    ui.listSearch = el.value;
    renderRuns();
  } else if (el.id === 'log-search') {
    ui.logSearch = el.value;
    renderLogContent();
  } else if (el.id === 'terminate-code') {
    updateConfirmation();
  }
});
document.addEventListener('change', async (event) => {
  const el = event.target;
  try {
    if (el.id === 'run-status') {
      ui.listStatus = el.value;
      renderRuns();
    } else if (el.id === 'attempt-select') {
      ui.attempt = el.value;
      await renderDrawer();
    } else if (el.id === 'raw-config') {
      $('#config-raw').hidden = !el.checked;
      $('#config-tables').hidden = el.checked;
    } else if (el.id === 'log-kind') {
      ui.systemLog = el.value === 'system';
      ui.logFile = 0;
      await loadLogs();
    } else if (el.id === 'log-file') {
      ui.logFile = Number(el.value);
      ui.logFull = false;
      await readLog();
    } else if (el.id === 'log-auto') {
      ui.logAuto = el.checked;
    } else if (el.id === 'log-errors') {
      ui.logErrors = el.checked;
      renderLogContent();
    } else if (el.id === 'action-confirm') {
      updateConfirmation();
    } else if (el.id === 'retry-pool') {
      updateRetryPool();
    }
  } catch (error) {
    toast(error.message);
  }
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && !$('#action-dialog').open && ui.selected) {
    event.preventDefault();
    closeDrawer();
  }
  const tab = event.target?.closest?.('[role=tab]');
  if (tab && ['ArrowRight', 'ArrowLeft', 'Home', 'End'].includes(event.key)) {
    event.preventDefault();
    const tabs = [...document.querySelectorAll('[role=tab]')];
    let index = tabs.indexOf(tab);
    index = nextTabIndex(event.key, index, tabs.length);
    tabs[index].click();
    setTimeout(() => document.querySelectorAll('[role=tab]')[index]?.focus(), 0);
  }
});
$('#action-dialog').addEventListener('cancel', (event) => {
  if (ui.busy) {
    event.preventDefault();
  }
});
document.addEventListener('visibilitychange', () => {
  if (!document.hidden) {
    refresh(true);
  }
});
setInterval(() => {
  if (!document.hidden && !$('#action-dialog').open) {
    refresh();
  }
}, 3000);
setInterval(() => {
  if (shouldAutoRefreshLogs()) {
    readLog().catch((e) => toast(e.message));
  }
}, LOG_REFRESH_INTERVAL_MS);
refresh(true);

let resizeTimer;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    if ($('#dag')) {
      renderDAG();
    }
  }, 100);
});
