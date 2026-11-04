// Log retrieval, filtering and optional 60-second refresh eligibility.
import { $, api, button, empty, enc, esc, json } from './common.js';
import { LOG_REFRESH_INTERVAL_MS, node, taskAPI, ui } from './state.js';

async function loadLogs() {
  const epoch = ui.drawerEpoch;
  const task = ui.attempt;
  const request = ++ui.logListRequest;
  ui.logRequest++;
  ui.logPolling = false;
  const result = await api(taskAPI('/logs?system=' + ui.systemLog));
  if (epoch !== ui.drawerEpoch || task !== ui.attempt || request !== ui.logListRequest) {
    return;
  }
  const selected = ui.logFiles[ui.logFile];
  const selectedIndex = result.files.findIndex((file) => file.file_path === selected?.file_path);
  ui.logFiles = result.files;
  if (selectedIndex >= 0) {
    ui.logFile = selectedIndex;
  }
  ui.logFile = Math.min(ui.logFile, Math.max(0, result.files.length - 1));
  $('#drawer-body').innerHTML =
    `<div class="tab-tools"><label for="log-kind">日志类型</label><select id="log-kind"><option value="job" ${!ui.systemLog ? 'selected' : ''}>作业日志</option><option value="system" ${ui.systemLog ? 'selected' : ''}>系统日志</option></select></div>${logFilesPanel(result)}`;
  if (result.files.length) {
    await readLog();
  }
}
async function readLog() {
  const file = ui.logFiles[ui.logFile];
  if (!file) {
    return;
  }
  const epoch = ui.drawerEpoch;
  const request = ++ui.logRequest;
  ui.logPolling = true;
  try {
    const result = await api(
      taskAPI(
        '/logs/content?file=' +
          enc(file.file_name) +
          '&path=' +
          enc(file.file_path) +
          '&all=' +
          (ui.logFull ? '1' : '0'),
      ),
    );
    if (epoch !== ui.drawerEpoch || request !== ui.logRequest) {
      return;
    }
    if (result.too_large) {
      $('#log-content').innerHTML = empty(result.message);
      return;
    }
    ui.logContent = result.content;
    renderLogContent();
  } finally {
    if (request === ui.logRequest) {
      ui.logPolling = false;
    }
  }
}
function renderLogContent() {
  if (!$('#log-content')) {
    return;
  }
  const search = ui.logSearch.toLowerCase();
  const lines = ui.logContent.split('\n').map((text, i) => ({
    text,
    i,
    error: /error|exception|traceback|killed|fatal|oom|failed/i.test(text),
  }));
  const visible = lines.filter(
    (l) => (!ui.logErrors || l.error) && (!search || l.text.toLowerCase().includes(search)),
  );
  const errors = visible.filter((l) => l.error).length;
  $('#log-content').innerHTML =
    `<div class="log-box" tabindex="0" aria-label="日志内容">${visible.map((l) => `<div class="log-line ${l.error ? 'error' : ''}"><span class="line-number">${l.i + 1}</span><span>${esc(l.text) || ' '}</span></div>`).join('') || '<p class="empty">没有匹配的日志行</p>'}</div><p class="log-caption">${ui.logFull ? '完整日志' : '最新 64 KB；行号为当前片段内的相对行号'} · ${visible.length} 行 · ${errors} 个错误行</p>`;
}
function shouldAutoRefreshLogs() {
  if (document.hidden || !ui.logAuto || ui.logFull) {
    return false;
  }
  if (ui.logPolling || !ui.selected || ui.tab !== 'logs') {
    return false;
  }
  const current = node();
  if (!['RUNNING', 'PENDING', 'PROCESSING'].includes(current?.display_status)) {
    return false;
  }
  return ui.attempt === current?.task_id;
}
function logFilesPanel(result) {
  if (result.files.length) {
    return `<div class="tab-tools"><label for="log-file">文件</label><select id="log-file">${result.files.map((f, i) => `<option value="${i}" ${i === ui.logFile ? 'selected' : ''}>${esc(f.file_name)}</option>`).join('')}</select></div><div class="tab-tools"><label class="row"><input type="checkbox" id="log-auto" ${ui.logAuto ? 'checked' : ''}>自动刷新 ${LOG_REFRESH_INTERVAL_MS / 1000}s</label><input type="search" id="log-search" placeholder="搜索日志" aria-label="搜索日志" value="${esc(ui.logSearch)}"><label class="row"><input id="log-errors" type="checkbox" ${ui.logErrors ? 'checked' : ''}>仅错误行</label></div><div class="tab-tools">${button('log-full', '完整日志')}${button('log-download', '下载')}${button('log-refresh', '↻ 手动刷新')}${button('error-prev', '↑ 上一个错误')}${button('error-next', '↓ 下一个错误')}</div><div id="log-content"></div>`;
  }
  return (
    empty('尚未产生日志文件', '任务排队或接口尚未上线时可能没有日志。') +
    (result.raw ? `<pre class="code">${esc(json(result.raw))}</pre>` : '')
  );
}

export { loadLogs, readLog, renderLogContent, shouldAutoRefreshLogs };
