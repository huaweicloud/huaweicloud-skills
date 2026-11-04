// Step drawer, task overview and structured configuration rendering.
import {
  $,
  AGENT_PROGRESS_HINT,
  api,
  button,
  date,
  duration,
  empty,
  esc,
  json,
  labels,
  parseArray,
  status,
} from './common.js';
import { loadLogs } from './logs.js';
import { manualContext, manualInfo, renderManualStep, stepKindTag } from './manual.js';
import { renderDAG } from './pipeline.js';
import { loadPreview } from './preview.js';
import { node, taskAPI, ui } from './state.js';

function drawerFooter(manual, historical) {
  if (manual) {
    return '由终端 Agent 完成本步骤并登记结果。';
  }
  if (historical) {
    return '历史尝试 · 仅供查看';
  }
  return 'Web 操作后，请回到智能体确认进度并继续编排。';
}
function attemptSelector(manual, attempts) {
  if (manual) {
    return '<span class="muted">本步骤不创建云端任务</span>';
  }
  if (!attempts.length) {
    return '<span class="muted">此步骤尚无任务记录</span>';
  }
  const options = attempts
    .map(
      (attempt, index) =>
        `<option value="${esc(attempt.task_id)}" ${attempt.task_id === ui.attempt ? 'selected' : ''}>#${index + 1} ${esc(attempt.task_id)} · ${esc(attempt.status || 'UNKNOWN')}</option>`,
    )
    .reverse()
    .join('');
  return `<label for="attempt-select">尝试</label><select id="attempt-select">${options}</select><span>共 ${attempts.length} 次</span>`;
}
function taskStateClass(raw, failed) {
  if (failed) {
    return 'failure';
  }
  return raw === 'RUNNING' ? 'running' : '';
}
function taskStatusText(n, raw, failed, error) {
  if (n.skip_requested) {
    return '已申请保留原输入跳过。请到智能体校验下游兼容性；校验通过前后续步骤仍被阻断。';
  }
  if (n.bypassed) {
    return '已校验后跳过，沿用原输入，不产生新数据版本。' + esc(n.skip_reason || '');
  }
  if (failed) {
    return esc(error || '平台未返回错误详情，请检查作业和系统日志。');
  }
  if (raw === 'RUNNING') {
    return '任务正在运行，可查看作业和系统日志。';
  }
  if (n.display_status === 'READY') {
    return '当前任务尚未提交。' + AGENT_PROGRESS_HINT;
  }
  return '当前步骤以终端编排和平台核实结果为准。';
}
async function openStage(key, tab = 'overview') {
  const n = ui.snapshot?.nodes.find((n) => n.key === key);
  if (!n) {
    return;
  }
  ui.selected = key;
  ui.attempt = n.task_id;
  ui.tab = tab;
  document.body.classList.add('has-drawer');
  $('#drawer').hidden = false;
  if ($('#dag')) {
    renderDAG();
  }
  await renderDrawer();
  $('#drawer-close')?.focus();
}
function closeDrawer() {
  const key = ui.selected;
  ui.drawerEpoch++;
  ui.selected = null;
  $('#drawer').hidden = true;
  document.body.classList.remove('has-drawer');
  if ($('#dag')) {
    renderDAG();
    [...document.querySelectorAll('.dag-node')].find((n) => n.dataset.key === key)?.focus();
  }
}
function resetDrawerContext(context) {
  ui.drawerContext = context;
  ui.drawerPanels.clear();
  ui.activePanel = null;
  ui.detail = null;
  ui.systemLog = false;
  ui.logContent = '';
  ui.logFiles = [];
  ui.logFile = 0;
  ui.logFull = false;
  ui.errorIndex = 0;
  ui.logSearch = '';
  ui.logErrors = false;
  ui.previewTree = null;
  ui.logPolling = false;
}
function selectPanel() {
  const previous = ui.activePanel;
  if (previous) {
    previous.scroll = previous.element.scrollTop;
  }
  let panel = ui.drawerPanels.get(ui.tab);
  if (!panel) {
    const element = document.createElement('div');
    element.id = 'drawer-body';
    element.className = 'drawer-body';
    element.setAttribute('role', 'tabpanel');
    element.innerHTML = empty('正在读取详情…');
    panel = { element, ready: false, scroll: 0 };
    ui.drawerPanels.set(ui.tab, panel);
  }
  if (previous !== panel) {
    ui.logPolling = false;
  }
  $('#drawer-body').replaceWith(panel.element);
  panel.element.setAttribute('aria-labelledby', 'tab-' + ui.tab);
  panel.element.scrollTop = panel.scroll;
  ui.activePanel = panel;
  for (const tab of document.querySelectorAll('.drawer-tabs [role=tab]')) {
    const selected = tab.dataset.tab === ui.tab;
    tab.setAttribute('aria-selected', selected);
    tab.tabIndex = selected ? 0 : -1;
  }
  return panel;
}
async function renderDrawer(quiet = false, force = false) {
  const n = node();
  if (!n) {
    return;
  }
  const epoch = ++ui.drawerEpoch;
  const manual = n.kind === 'manual';
  const info = manual ? manualInfo(n) : null;
  const history = n.attempts || [];
  const attempts = taskAttempts(n, manual, history);
  const historical = Boolean(ui.attempt && ui.attempt !== n.task_id);
  const tabs = [
    ['overview', '概览'],
    ['config', manual ? info.config : '任务配置'],
    ['logs', '日志'],
    ['preview', n.kind === 'eval' ? '评测报告' : '输出预览'],
  ];
  const context = JSON.stringify([ui.run, ui.selected, ui.attempt, n.display_status, n.task_id,
    manual ? manualContext(n) : null]);
  if (force || ui.drawerContext !== context) {
    resetDrawerContext(context);
  }
  if (!ui.activePanel || !$('#drawer-body')) {
    $('#drawer').innerHTML =
      `<header class="drawer-header"><div class="row between"><h2>${esc(n.name)} <span class="tag">${stepKindTag(n, info)}</span></h2>${button('drawer-close', '×', 'icon-button', 'id="drawer-close" aria-label="关闭步骤详情"')}</div><div class="attempt-row">${attemptSelector(manual, attempts)}</div></header><div class="drawer-tabs" role="tablist" aria-label="步骤详情页签">${tabs.map(([id, name]) => button('tab', name, '', `data-tab="${id}" id="tab-${id}" role="tab" aria-selected="${ui.tab === id}" aria-controls="drawer-body" tabindex="${ui.tab === id ? 0 : -1}"`)).join('')}</div><div class="drawer-body" id="drawer-body" role="tabpanel" aria-labelledby="tab-${ui.tab}">${empty('正在读取详情…')}</div><footer class="drawer-footer">${drawerFooter(manual, historical)}</footer>`;
  }
  const panel = selectPanel();
  if (panel.ready && !quiet) {
    return;
  }
  if (manual) {
    renderManualStep();
    panel.ready = true;
    return;
  }
  try {
    const detail = ui.attempt
      ? await drawerDetail(quiet, force)
      : {
          record: {
            task_config: null,
          },
          live: n.live || {},
          kind: n.kind,
          historical: false,
        };
    if (epoch !== ui.drawerEpoch) {
      return;
    }
    ui.detail = detail;
    if (ui.tab === 'overview') {
      renderOverview();
    } else if (ui.tab === 'config') {
      renderConfig();
    } else if (!ui.attempt) {
      $('#drawer-body').innerHTML = empty('任务尚未提交', '任务提交后可查看此页签。');
    } else if (ui.tab === 'logs') {
      await loadLogs();
    } else if (ui.tab === 'preview') {
      await loadPreview();
    }
    if (epoch === ui.drawerEpoch) {
      panel.ready = true;
    }
  } catch (error) {
    if (epoch === ui.drawerEpoch) {
      $('#drawer-body').innerHTML =
        `<div class="banner critical">${esc(error.message)}</div>${button('detail-refresh', '重新读取')}`;
    }
  }
}
async function drawerDetail(quiet, force) {
  if (ui.detail && !quiet && !force) {
    return ui.detail;
  }
  return api(taskAPI(force ? '?refresh=1' : ''));
}
function skipButton(action, label, reason, enabled = true) {
  const attrs = `${enabled ? '' : 'disabled'} title="${esc(reason)}" aria-describedby="skip-hint"`;
  return `<span class="action-with-hint" title="${esc(reason)}" ${enabled ? '' : 'tabindex="0" aria-describedby="skip-hint"'}>${button(action, label, '', attrs)}</span><span id="skip-hint" class="small muted">${esc(reason)}</span>`;
}
function skipControl(n) {
  if (n.actions['cancel-skip']) {
    return skipButton('cancel-skip', '取消跳过请求', '取消申请，保留原处理步骤，由智能体继续编排。');
  }
  if (n.actions.skip) {
    return skipButton('skip', '跳过', '确认后跳过此建议性评测，保留数据产物；完成摘要将提示未评测，之后可补跑。');
  }
  if (n.kind !== 'proc' || n.task_id || n.skipped) {
    return '';
  }
  const allowed = n.actions['request-skip'];
  const reason = allowed
    ? '保留原输入，待智能体核实下游兼容性后生效'
    : n.skip_disabled_reason || '当前步骤不可申请跳过，请到智能体核实状态。';
  return skipButton('request-skip', '跳过', reason, allowed);
}
function actionButtons(n, historical = false) {
  if (historical) {
    return '<p class="small muted">历史尝试只供查看，请切换到当前尝试后操作。</p>';
  }
  return (
    button(
      'retry',
      '重新提交…',
      'primary',
      `${n.actions.retry ? '' : 'disabled'} title="${esc(n.actions.retry ? '重新查询算子并新建任务' : n.action_reason)}"`,
    ) +
    skipControl(n) +
    (ui.snapshot.actions.terminate
      ? button('terminate', '终止管线', 'danger', 'title="停止后续编排，现有云端任务仍继续运行"')
      : '')
  );
}
function overviewInput(config) {
  if (config.dataset_configs) {
    return json(parseArray(config.dataset_configs));
  }
  if (config.dataset_path) {
    return json({
      dataset_id: config.dataset_id,
      dataset_name: config.dataset_name,
      dataset_path: config.dataset_path,
    });
  }
  return '提交前由智能体按数据来源核实资产、版本和路径。';
}
function renderOverview() {
  const n = node();
  const detail = ui.detail;
  const live = detail.live || {};
  const config = detail.record?.task_config || {};
  const historical = detail.historical;
  const raw = live.status || n.raw_status;
  const failed = ['FAILED', 'DELETED'].includes(raw);
  const error = live.error_message || live.error || live.message || live.reason;
  const rows = [
    ['算子', config.algo_name || n.operator || '—'],
    ['算子 ID', config.algo_id || '—'],
    ['镜像', config.image || '—'],
    ['任务名', detail.record?.task_name || n.task_name || '—'],
    ['任务 ID', ui.attempt || '尚未提交'],
    ...(!historical
      ? [
          [
            '计划数据来源（按顺序）',
            n.input_from?.map((ref, index) => `${index + 1}. ${ref}`).join('\n') || '见已确认计划',
          ],
          ['等待依赖', n.depends_on?.join('、') || '无'],
        ]
      : []),
    ['输入', overviewInput(config)],
    ['输出', live.target_path || n.target_path || config.output_name || '尚未生成'],
    [
      '资源',
      config.worker_spec
        ? `${config.resource_pool_type || 'PUBLIC_POOL'} · ${config.worker_spec.cpu}c${config.worker_spec.memory}g × ${config.worker_num || 1}`
        : '—',
    ],
    ['平台状态', raw || '—'],
    ['开始 / 结束', date(live.start_at || n.started_at) + ' / ' + date(live.finish_at)],
    ...(n.kind === 'eval'
      ? [
          [
            '配置挂载 inputs',
            (Array.isArray(parseArray(config.inputs)) ? parseArray(config.inputs) : [])
              .map((mount) => `${mount.name} → ${mount.url_path || '—'}`)
              .join('\n') || '未挂载（使用算子内置/默认配置）',
          ],
        ]
      : []),
  ];
  const command = ui.attempt
    ? `cloudrobo dataset ${n.kind} show-task --task-id '${ui.attempt}'`
    : '';
  $('#drawer-body').innerHTML =
    `<div class="detail-card ${taskStateClass(raw, failed)}"><div class="row between"><h3>${status(historical ? raw : n.display_status, historical ? labels[raw] : n.label)}</h3><small class="muted">${duration(live.start_at || n.started_at, live.finish_at)}</small></div><p>${taskStatusText(n, raw, failed, error)}</p>${failed ? '<p class="muted mt">退出码 137 / Killed 可能与内存有关；请结合系统日志及 CloudRobo Console 中的资源详情确认原因。</p>' : ''}<div class="row">${ui.attempt ? button('tab', '查看日志', '', 'data-tab="logs"') : ''}${actionButtons(n, historical)}</div></div>${detail.error ? `<p class="error-text mt">${esc(detail.error)}</p>` : ''}<dl class="detail-list">${rows.map(([k, v]) => `<dt>${esc(k)}</dt><dd><pre>${esc(v)}</pre>${['任务 ID', '镜像', '输出'].includes(k) ? button('copy', '复制', 'copy', `data-copy="${esc(v)}"`) : ''}</dd>`).join('')}</dl>${n.kind === 'proc' ? '<p class="small muted mt">详细资源使用情况请复制任务 ID，前往 CloudRobo Console 查询。</p>' : ''}${command ? `<h3 class="mb">等效查询命令</h3><pre class="code">${esc(command)}</pre><div class="row mt">${button('copy', '复制命令', '', `data-copy="${esc(command)}"`)}${button('detail-refresh', '↻ 查询最新状态')}</div>` : ''}${n.kind === 'manual' ? '<p class="small muted mt">计划、上传注册和产物核对由 Agent 在终端确认并记录。</p>' : ''}`;
}
function differences(current, previous) {
  if (!previous) {
    return '';
  }
  const keys = new Set([...Object.keys(current || {}), ...Object.keys(previous || {})]);
  const changes = [...keys].filter((k) => json(current?.[k]) !== json(previous?.[k]));
  return changes.length
    ? `<div class="diff"><strong>与上次配置的差异</strong>${changes.map((k) => `<p class="mt"><b>${esc(k)}</b><code>− ${esc(typeof previous[k] === 'string' ? previous[k] : (json(previous[k]) ?? '未设置'))}</code><code>+ ${esc(typeof current[k] === 'string' ? current[k] : (json(current[k]) ?? '未设置'))}</code></p>`).join('')}</div>`
    : '<p class="small muted mb">与上次尝试的配置相同。</p>';
}
function configTables(config) {
  const arrays = ['dataset_configs', 'envs', 'inputs'];
  return (
    `<div class="table-wrap"><table class="config-table"><tbody>${Object.entries(config)
      .filter(([k]) => !arrays.includes(k))
      .map(
        ([k, v]) =>
          `<tr><th>${esc(k)}</th><td><pre>${esc(typeof v === 'object' ? json(v) : v)}</pre></td></tr>`,
      )
      .join('')}</tbody></table></div>` +
    arrays
      .filter((k) => config[k])
      .map((k) => {
        const array = parseArray(config[k]);
        if (!Array.isArray(array)) {
          return `<pre class="code">${esc(config[k])}</pre>`;
        }
        const keys = [...new Set(array.flatMap((v) => Object.keys(v)))];
        return `<section class="json-array"><h3>${k}</h3><div class="table-wrap"><table class="config-table"><thead><tr>${keys.map((k) => `<th>${esc(k)}</th>`).join('')}</tr></thead><tbody>${array.map((v) => `<tr>${keys.map((k) => `<td>${esc(typeof v[k] === 'object' ? json(v[k]) : v[k])}</td>`).join('')}</tr>`).join('')}</tbody></table></div></section>`;
      })
      .join('')
  );
}
function renderConfig() {
  const config = ui.detail.record?.task_config;
  if (!config) {
    $('#drawer-body').innerHTML = empty(
      '没有提交配置',
      node().kind === 'manual'
        ? '本步骤的输入和产物见概览。'
        : '原始 tasks/<task_id>.json 不存在，请到终端核对。',
    );
    return;
  }
  $('#drawer-body').innerHTML =
    `<div class="tab-tools">${button('copy-config', '复制 JSON')}${button('copy-cli', '复制提交命令')}<label class="row"><input type="checkbox" id="raw-config">原始 JSON</label></div><p class="small muted mb">敏感字段已打码。复制后的配置如含掩码，需在终端补全后使用。</p>${differences(config, ui.detail.previous_config)}<div id="config-tables">${configTables(config)}</div><pre id="config-raw" class="code" hidden>${esc(json(config))}</pre>`;
}
function taskAttempts(n, manual, history) {
  if (manual) {
    return [];
  }
  return [
    ...history,
    ...(n.task_id
      ? [
          {
            task_id: n.task_id,
            status: n.raw_status,
          },
        ]
      : []),
  ];
}

export { closeDrawer, differences, openStage, renderDrawer };
