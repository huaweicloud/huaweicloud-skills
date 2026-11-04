// First-level output listing; signed preview/report links are fetched per click.
import { $, api, button, empty, esc, json } from './common.js';
import { node, taskAPI, ui } from './state.js';

function findURLs(value) {
  const result = [];
  function visit(v) {
    if (typeof v === 'string' && /^https?:\/\/[^\s<>]+$/.test(v)) {
      result.push(v);
    } else if (Array.isArray(v)) {
      v.forEach(visit);
    } else if (v && typeof v === 'object') {
      Object.values(v).forEach(visit);
    }
  }
  visit(value);
  return [...new Set(result)];
}
function previewResult(data) {
  const urls = findURLs(data);
  return `${urls.map((url, i) => `<p class="mb"><a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${urls.length === 1 ? '打开平台预览 / 报告' : '打开链接 ' + (i + 1)} ↗</a></p>`).join('')}<pre class="code">${esc(json(data))}</pre>`;
}
async function requestPreview(suffix) {
  const epoch = ui.drawerEpoch;
  const request = ++ui.previewRequest;
  try {
    const result = await api(taskAPI(suffix));
    if (epoch === ui.drawerEpoch && request === ui.previewRequest) {
      $('#preview-result').innerHTML = previewResult(result);
    }
  } catch (error) {
    if (epoch === ui.drawerEpoch && request === ui.previewRequest) {
      $('#preview-result').innerHTML =
        `<div class="banner critical" role="alert"><strong>预览读取失败</strong><p>${esc(error.message)}</p></div><p class="small muted mt">平台返回 500/502/503/504 时，可短暂等待后再次点击原预览或报告按钮，手动重试一次。读取错误不改变任务状态；连续失败请保留任务 ID、报告或文件路径及错误信息，交给智能体排查。</p>`;
    }
  }
}
async function loadPreview() {
  const n = node();
  const epoch = ui.drawerEpoch;
  if (n.kind === 'eval') {
    $('#drawer-body').innerHTML =
      `<h3 class="mb">${esc(n.name)}报告</h3><p class="small muted mb">每次点击时重新获取临时链接，避免报告地址过期。</p><div class="row">${button('report-preview', '获取报告链接', 'primary')}${button('report-download', '获取下载链接')}</div><div id="preview-result" class="mt"></div>`;
    return;
  }
  if (n.kind !== 'proc') {
    $('#drawer-body').innerHTML = empty(
      '本步骤没有可浏览的任务输出',
      '管线产物路径与资产信息见概览或完成摘要。',
    );
    return;
  }
  if (!(ui.detail.live?.target_path || n.target_path)) {
    $('#drawer-body').innerHTML = empty('任务成功后可预览输出数据', '当前尚未返回 target_path。');
    return;
  }
  const result = await api(taskAPI('/frames'));
  if (epoch !== ui.drawerEpoch) {
    return;
  }
  ui.previewTree = result;
  $('#drawer-body').innerHTML =
    `<div class="row between mb"><h3>输出目录</h3>${button('frames-refresh', '↻ 刷新目录')}</div><p class="mono muted output-root">${esc(result.base)}</p><p class="small muted mt">仅显示第一层文件夹和文件，不展开子目录。切换页签保留列表；文件预览链接按点击重新获取。</p><div id="output-tree" class="file-list" aria-label="输出根目录第一层"></div><div id="preview-result" class="mt"></div>`;
  renderFiles();
}
function renderFiles() {
  const listing = ui.previewTree;
  const rows = listing.files
    .map((entry) => {
      const label = esc(entry.name) + (entry.directory ? '/' : '');
      const icon = entry.directory ? '▱' : '▤';
      const action = entry.directory
        ? '<span class="small muted">文件夹</span>'
        : button('frame-preview', '预览', '', `data-file="${esc(entry.key)}"`);
      return `<li class="file-entry ${entry.directory ? 'tree-directory' : ''}"><div class="file-row"><span class="tree-file"><span aria-hidden="true">${icon}</span><code title="${esc(entry.key)}">${label}</code></span>${action}</div></li>`;
    })
    .join('');
  let content = empty('此目录没有文件或文件夹');
  if (rows) {
    content = `<ul class="tree-root">${rows}</ul>`;
  } else if (listing.raw) {
    content += `<details class="mt"><summary>查看接口原始返回</summary><pre class="code mt">${esc(json(listing.raw))}</pre></details>`;
  }
  $('#output-tree').innerHTML = content;
}

export { loadPreview, requestPreview };
