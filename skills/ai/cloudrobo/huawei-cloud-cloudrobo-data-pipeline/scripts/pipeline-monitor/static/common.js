// Shared DOM, formatting, request and notification helpers.

const $ = (selector, root = document) => root.querySelector(selector);
const esc = (value) =>
  String(value ?? '').replace(
    /[&<>"']/g,
    (c) =>
      ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
      })[c],
  );
const enc = encodeURIComponent;
const AGENT_PROGRESS_HINT =
  '若进度停留在“待提交”，请前往智能体查看进度，确认是否有产物版本或参数等事项待处理。完成确认后，由智能体继续提交后续任务。';
const labels = {
  IDLE: '未开始',
  READY: '待提交（等待编排）',
  PENDING: '排队中',
  RUNNING: '运行中',
  SUCCEEDED: '成功',
  FAILED: '失败',
  DELETED: '已删除',
  SKIPPED: '已跳过',
  PROCESSING: '处理中',
  AWAITING_DECISION: '等待处理',
  TERMINATED: '已终止',
  SUCCEEDED_WITH_WARNINGS: '成功（有告警）',
  UNKNOWN: '未知状态',
};
const glyphs = {
  SUCCEEDED: '✓',
  FAILED: '×',
  DELETED: '−',
  SKIPPED: '»',
  AWAITING_DECISION: 'Ⅱ',
  TERMINATED: '■',
  PENDING: '◷',
  READY: '·',
  UNKNOWN: '?',
  SUCCEEDED_WITH_WARNINGS: '!',
};
const terminalRuns = new Set(['SUCCEEDED', 'SUCCEEDED_WITH_WARNINGS', 'FAILED', 'TERMINATED']);
function timeValue(value) {
  if (!value) {
    return NaN;
  }
  if (typeof value === 'number') {
    return value < 1e11 ? value * 1000 : value;
  }
  return new Date(value).getTime();
}
function clock(value) {
  const t = timeValue(value);
  return Number.isFinite(t)
    ? new Date(t).toLocaleTimeString('zh-CN', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      })
    : '—';
}
function date(value) {
  const t = timeValue(value);
  return Number.isFinite(t)
    ? new Date(t).toLocaleString('zh-CN', {
        hour12: false,
      })
    : '—';
}
function duration(start, end) {
  const t = timeValue(start);
  const seconds = Math.max(0, Math.floor(((timeValue(end) || Date.now()) - t) / 1000));
  if (!Number.isFinite(seconds)) {
    return '—';
  }
  if (seconds < 60) {
    return `${seconds}s`;
  }
  if (seconds < 3600) {
    return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  }
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
}
function status(value, text, notApplicable = false) {
  const known = labels[value] ? value : 'UNKNOWN';
  const spinning = ['RUNNING', 'PROCESSING'].includes(known);
  let iconClass = '';
  if (spinning) {
    iconClass = 'running';
  } else if (['IDLE', 'READY'].includes(known)) {
    iconClass = 'idle';
  }
  return `<span class="status ${known}${notApplicable ? ' not-applicable' : ''}"><span aria-hidden="true" class="status-icon ${iconClass}">${spinning ? '' : glyphs[known] || ''}</span>${esc(text || labels[value] || value || '未开始')}</span>`;
}
function button(action, text, cls = '', attrs = '') {
  return `<button type="button" class="${cls}" data-action="${action}" ${attrs}>${text}</button>`;
}
function empty(title, text = '') {
  return `<div class="empty">${esc(title)}${text ? `<p>${esc(text)}</p>` : ''}</div>`;
}
function json(value) {
  return JSON.stringify(value, null, 2);
}
function parseArray(value) {
  try {
    return typeof value === 'string' ? JSON.parse(value) : value || [];
  } catch {
    return value;
  }
}
function detailFields(rows, copyKeys = []) {
  return `<dl class="detail-list">${rows.map(([k, v]) => `<dt>${esc(k)}</dt><dd><pre>${esc(v)}</pre>${copyKeys.includes(k) ? button('copy', '复制', 'copy', `data-copy="${esc(v)}"`) : ''}</dd>`).join('')}</dl>`;
}
async function api(path, body) {
  const response = await fetch(path, {
    method: body === undefined ? 'GET' : 'POST',
    credentials: 'same-origin',
    cache: 'no-store',
    headers:
      body === undefined
        ? {}
        : {
            'Content-Type': 'application/json',
            'X-Pipeline-Monitor': '1',
          },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (response.status === 204) {
    return null;
  }
  const data = await response.json();
  if (!response.ok) {
    const error = new Error(data.error || `请求失败（${response.status}）`);
    error.status = response.status;
    throw error;
  }
  return data;
}
let toastTimer;
function toast(message) {
  $('#toast').textContent = message;
  $('#toast').hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => ($('#toast').hidden = true), 6000);
}
function showError(message) {
  $('#global-error').textContent = message;
  $('#global-error').hidden = false;
  $('#connection').textContent = '连接异常';
}
function connected(demo) {
  $('#global-error').hidden = true;
  $('#mode').hidden = !demo;
  $('#connection').textContent = '已连接 · ' + clock(Date.now());
}
async function copy(value) {
  try {
    await navigator.clipboard.writeText(String(value));
    toast('已复制');
  } catch {
    toast('浏览器未开放剪贴板，请选择文本后复制。');
  }
}
function cliCommand(args) {
  if (/Win/i.test(navigator.platform || '')) {
    // Feed JSON argv to Python to preserve nested quotes on PowerShell 5.1 too.
    return [
      "$env:PYTHONIOENCODING = 'utf-8'",
      '$OutputEncoding = New-Object System.Text.UTF8Encoding',
      "@'",
      JSON.stringify(args),
      '\'@ | python -c "import json, subprocess, sys; subprocess.run(json.load(sys.stdin), check=True)"',
    ].join('\n');
  }
  const quote = (value) => "'" + String(value).replace(/'/g, "'\"'\"'") + "'";
  return args.map(quote).join(' ');
}
function eventAppearance(event, failed) {
  if (failed) {
    return { state: 'FAILED', icon: '×' };
  }
  if (event.type === 'retry') {
    return { state: 'RUNNING', icon: '↻' };
  }
  return { state: 'SUCCEEDED', icon: '·' };
}
function eventDetailText(event) {
  if (typeof event.detail === 'string') {
    return event.detail;
  }
  return json(event.detail);
}
function eventDetailHTML(event, expanded) {
  const text = eventDetailText(event);
  if (text.length <= 180) {
    return `<div class="muted">${esc(text)}</div>`;
  }
  return `<div class="muted event-preview">${esc(text.slice(0, 180))}…</div><details class="event-full" data-seq="${esc(event.seq)}" ${expanded ? 'open' : ''}><summary>查看完整内容</summary><pre>${esc(text)}</pre></details>`;
}
function hideToast() {
  clearTimeout(toastTimer);
  $('#toast').hidden = true;
}

export {
  $,
  AGENT_PROGRESS_HINT,
  api,
  button,
  clock,
  cliCommand,
  connected,
  copy,
  date,
  detailFields,
  duration,
  empty,
  enc,
  esc,
  eventAppearance,
  eventDetailHTML,
  hideToast,
  json,
  labels,
  parseArray,
  showError,
  status,
  terminalRuns,
  toast,
};
