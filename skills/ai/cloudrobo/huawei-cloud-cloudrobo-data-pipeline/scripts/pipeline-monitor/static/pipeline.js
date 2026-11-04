// Run list, progress, dependency graph, events and completion summary.
import {
  $,
  AGENT_PROGRESS_HINT,
  button,
  clock,
  date,
  duration,
  empty,
  esc,
  eventAppearance,
  eventDetailHTML,
  status,
  terminalRuns,
} from './common.js';
import { manualInfo, stepKindTag } from './manual.js';
import { ui } from './state.js';

function dagSubtitle(n, info) {
  if (n.external) {
    return '外部输入';
  }
  if (n.kind === 'manual') {
    return info.subtitle;
  }
  return n.operator || n.kind;
}
function dagTag(n, info) {
  if (n.stale) {
    return '? 可能过期';
  }
  return stepKindTag(n, info);
}
function progress(nodes, mini = false) {
  return `<div class="progress-bar" aria-label="步骤进度">${nodes.map((n) => progressSegment(n, mini)).join('')}</div>${mini ? '' : `<div class="progress-labels">${nodes.map((n) => `<span title="${esc(n.name)}">${esc(n.name)}</span>`).join('')}</div>`}`;
}
function renderRuns() {
  const previous = $('#runs-table .table-wrap');
  const scroll = [previous?.scrollLeft || 0, previous?.scrollTop || 0];
  $('#breadcrumb').textContent = '运行列表';
  document.title = '运行列表 · CloudRobo';
  if (!$('#runs-table')) {
    $('#workspace').innerHTML =
      `<section class="list-page"><div class="list-intro"><h1>管线运行</h1><p class="muted mt">查看本地管线进度、任务记录与管线产物。</p></div><div class="row between list-filters"><div class="row"><input id="run-search" type="search" placeholder="搜索运行名称或 run_id" aria-label="搜索运行"><select id="run-status" aria-label="筛选运行状态"><option value="">全部状态</option><option value="RUNNING">运行中</option><option value="AWAITING_DECISION">等待处理</option><option value="completed">已完成</option><option value="TERMINATED">已终止</option></select></div>${button('refresh', '↻ 刷新')}</div><div id="runs-table"></div><p class="section-caption mt">所有数据来自当前 runs-root。Web 负责观察和步骤内操作，后续步骤由终端 Agent 推进。</p></section>`;
  }
  $('#run-search').value = ui.listSearch;
  $('#run-status').value = ui.listStatus;
  const runs = ui.runs.filter((r) => {
    const s = r.state || {};
    return (
      (r.run_id + ' ' + (s.pipeline_name || ''))
        .toLowerCase()
        .includes(ui.listSearch.toLowerCase()) &&
      (!ui.listStatus ||
        (ui.listStatus === 'completed'
          ? ['SUCCEEDED', 'SUCCEEDED_WITH_WARNINGS', 'FAILED'].includes(s.status)
          : s.status === ui.listStatus))
    );
  });
  $('#runs-table').innerHTML = runs.length
    ? `<div class="table-wrap"><table class="run-table"><thead><tr><th>运行</th><th>状态</th><th>进度</th><th>当前步骤</th><th>开始时间 / 耗时</th><th></th></tr></thead><tbody>${runs.map((r) => runTableRow(r)).join('')}</tbody></table></div>`
    : empty(runListEmptyTitle(), '计划确认后，通过 pipeline_state.py init 创建本地运行。');
  $('#runs-table .table-wrap')?.scrollTo(scroll[0], scroll[1]);
}
function renderAgentHint(snapshot) {
  if (
    snapshot.readonly ||
    snapshot.state.pending_action ||
    terminalRuns.has(snapshot.state.status)
  ) {
    return '';
  }
  const ready = snapshot.nodes.filter((n) => n.kind !== 'manual' && n.display_status === 'READY');
  if (!ready.length) {
    return '';
  }
  const names = ready.map((n) => esc(n.name)).join('、');
  return `<div class="banner neutral" id="agent-progress-hint" role="note" aria-label="智能体进度提示"><strong>请到智能体确认进度</strong><p>待提交：${names}。${esc(AGENT_PROGRESS_HINT)}</p></div>`;
}
function renderRun() {
  const graph = $('.dag-scroll');
  const position = [graph?.scrollLeft || 0, graph?.scrollTop || 0, $('#timeline')?.scrollTop || 0,
    $('#summary')?.scrollTop || 0];
  const s = ui.snapshot;
  const state = s.state;
  const timelineClass = ui.eventsCollapsed ? 'collapsed' : '';
  const timelineHidden = ui.eventsCollapsed ? 'hidden' : '';
  const shellClass = ui.eventsCollapsed ? '' : 'timeline-open';
  const timelineToggle = button('event-toggle', ui.eventsCollapsed ? '展开' : '收起', 'text-button',
    `aria-expanded="${!ui.eventsCollapsed}" aria-controls="event-panel"`);
  $('#breadcrumb').textContent = state.pipeline_name || ui.run;
  $('#workspace').innerHTML =
    `<div class="run-shell ${shellClass}"><section class="run-header"><div class="run-header-top"><div><div class="run-title"><h1>${esc(state.pipeline_name || ui.run)}</h1>${status(state.status)}</div><div class="run-meta"><code>run ${esc(ui.run)}</code><span>工作空间 ${esc(state.workspace_id || '—')}</span><span>${esc(state.region || '区域未记录')}</span><span>已用时 ${duration(state.created_at, state.finished_at)}</span></div><div class="run-meta"><span><span class="agent-dot ${s.agent_offline ? 'offline' : ''}"></span>编排 Agent：${s.agent_offline ? '可能离线' : '活跃'}</span><span>心跳 ${clock(state.orchestrator?.heartbeat_at)}</span><span>快照 ${clock(s.server_time)}</span></div></div><div class="run-actions">${button('runs', '运行列表')}${button('refresh', '↻ 刷新')}${button('export', '导出摘要')}${button('terminate', '终止管线', 'danger', `${s.actions.terminate ? '' : 'disabled'} title="${s.actions.terminate ? '停止后续编排，现有云端任务仍继续运行' : '当前运行已结束、状态过期或正在处理操作'}"`)}${deleteRunButton(s)}</div></div></section>
    <div class="run-notices" tabindex="0" aria-label="运行提示">${s.demo ? '<div class="banner">本地演示 · 页面中的任务、日志与预览均为模拟数据，操作不会访问云端。</div>' : ''}
    ${s.warnings.map((w) => `<div class="banner ${esc(w.tone)}" role="status">${esc(w.text)}</div>`).join('')}
    ${renderAgentHint(s)}</div>
    <section class="progress-section">${progress(s.nodes)}<p class="progress-summary"><strong>${s.progress.done}/${s.progress.total} 完成</strong> · 当前：${esc(s.progress.current)}<span class="subtle"> · 每 3 秒刷新，任务状态约每 15 秒更新</span></p></section>
    ${runViewTabs(state)}
    ${
      ui.view === 'summary'
        ? '<div id="summary" tabindex="0" aria-label="完成摘要"></div>'
        : `<section class="flow-panel" aria-label="管线步骤图"><div class="section-head"><h2>执行流程</h2><span class="hint">点击步骤查看详情 · 建议性评测可独立处理</span></div><div class="dag-scroll" tabindex="0" aria-label="流程图浏览区域"><div id="dag" class="dag"></div></div></section><section class="timeline-section ${timelineClass}" aria-label="事件时间线"><div class="section-head"><div class="row"><h2>事件时间线</h2><span id="event-count" class="small muted"></span></div><div class="filters" aria-label="事件筛选">${[
            ['all', '全部'],
            ['actions', '仅操作'],
            ['failures', '仅失败'],
          ]
            .map(([k, v]) =>
              button(
                'event-filter',
                v,
                ui.eventFilter === k ? 'active' : '',
                `data-filter="${k}" aria-pressed="${ui.eventFilter === k}"`,
              ),
            )
            .join('')}</div>${timelineToggle}</div><div id="event-panel" class="event-panel" ${timelineHidden}><div id="timeline" class="timeline" role="list" tabindex="0" aria-label="事件记录"></div><div id="event-pager" class="event-pager"></div></div></section>`
    }</div>`;
  if (ui.view === 'summary') {
    renderSummary();
    $('#summary').scrollTop = position[3];
  } else {
    renderDAG();
    renderEvents();
    $('.dag-scroll').scrollTo(position[0], position[1]);
    $('#timeline').scrollTop = position[2];
  }
}
function renderDAG() {
  const nodes = ui.snapshot.nodes;
  const columns = new Map();
  for (const n of nodes) {
    if (!columns.has(n.layer)) {
      columns.set(n.layer, []);
    }
    columns.get(n.layer).push(n);
  }
  const maxRows = Math.max(1, ...[...columns.values()].map((v) => v.length));
  const columnCount = Math.max(...nodes.map((n) => n.layer)) + 1;
  const available = Math.max(0, $('#dag').parentElement.clientWidth - 48);
  const gap = 36;
  const nodeWidth = Math.max(
    184,
    Math.min(300, (available - (columnCount - 1) * gap) / columnCount),
  );
  const nodeHeight = 144;
  const rowStep = nodeHeight + 20;
  const columnStep = nodeWidth + gap;
  const height = Math.max(260, maxRows * rowStep + 16);
  const positions = new Map();
  for (const [layer, column] of columns) {
    column.forEach((n, i) =>
      positions.set(n.key, {
        x: layer * columnStep,
        y: (height - column.length * rowStep) / 2 + i * rowStep + 10,
      }),
    );
  }
  const width = columnCount * columnStep - gap;
  const paths = nodes
    .flatMap((n) =>
      n.dependency_keys.map((key) => {
        const a = positions.get(key);
        const b = positions.get(n.key);
        if (!a || !b) {
          return '';
        }
        const source = nodes.find((n) => n.key === key);
        const active =
          ['RUNNING', 'PENDING', 'PROCESSING'].includes(n.display_status) &&
          ['SUCCEEDED', 'SKIPPED'].includes(source.display_status);
        const done = ['SUCCEEDED', 'SKIPPED'].includes(n.display_status);
        const x = a.x + nodeWidth;
        const y = a.y + nodeHeight / 2;
        const bx = b.x;
        const by = b.y + nodeHeight / 2;
        const m = (x + bx) / 2;
        return `<path class="${dagPathClass(active, done)}" d="M${x},${y}H${m}V${by}H${bx - 4}"/><path class="${dagPathClass(active, done)}" d="M${bx - 7},${by - 3}L${bx - 3},${by}L${bx - 7},${by + 3}"/>`;
      }),
    )
    .join('');
  $('#dag').style.setProperty('--node-width', nodeWidth + 'px');
  $('#dag').style.width = width + 'px';
  $('#dag').style.height = height + 'px';
  $('#dag').innerHTML =
    `<svg class="dag-lines" width="${width}" height="${height}" aria-hidden="true">${paths}</svg>` +
    nodes
      .map((n) => {
        const p = positions.get(n.key);
        const manual = n.kind === 'manual';
        const info = manual ? manualInfo(n) : null;
        return `<button type="button" class="dag-node ${n.display_status} ${ui.selected === n.key ? 'selected' : ''}" data-action="stage" data-key="${esc(n.key)}" style="left:${p.x}px;top:${p.y}px" aria-pressed="${ui.selected === n.key}" title="${esc(n.name + '\n' + (manual ? info.description : '任务 ' + (n.task_id || '未提交') + '\n平台状态 ' + (n.raw_status || '—') + '\n更新 ' + date(n.checked_at)) + (n.stale ? '\n可能过期' : ''))}">${n.attempt_count > 1 ? `<span class="attempt-badge">#${n.attempt_count}</span>` : ''}<span class="node-name">${esc(n.name)}</span><span class="node-operator">${esc(dagSubtitle(n, info))}</span>${status(n.display_status, !manual && n.display_status === 'READY' ? '待提交' : n.label, n.not_applicable)}<span class="node-tag">${dagTag(n, info)}</span></button>`;
      })
      .join('');
}
function renderEvents() {
  if (!$('#timeline')) {
    return;
  }
  const scroll = $('#timeline').scrollTop;
  const actions = new Set([
    'retry',
    'skip',
    'request-skip',
    'cancel-skip',
    'bypass',
    'skip_cancelled',
    'terminate',
    'action_started',
    'action_failed',
    'task_submitted',
  ]);
  const events = ui.events
    .filter(
      (e) =>
        ui.eventFilter === 'all' ||
        (ui.eventFilter === 'actions' && actions.has(e.type)) ||
        (ui.eventFilter === 'failures' &&
          (e.type === 'action_failed' || ['FAILED', 'DELETED'].includes(e.detail))),
    )
    .slice()
    .reverse();
  const unseen = events.filter((e) => ui.eventCutoff !== null && e.seq > ui.eventCutoff).length;
  const history = events.filter((e) => ui.eventCutoff === null || e.seq <= ui.eventCutoff);
  const pages = Math.max(1, Math.ceil(history.length / 20));
  ui.eventPage = Math.min(ui.eventPage, pages - 1);
  const visible = history.slice(ui.eventPage * 20, (ui.eventPage + 1) * 20);
  $('#event-count').textContent = `共 ${events.length} 条`;
  $('#event-pager').innerHTML = `<span class="small muted" role="status">第 ${ui.eventPage + 1} / ${pages} 页 · 每页 20 条${unseen ? ` · 有 ${unseen} 条新事件` : ''}</span><div class="row">${button('event-page', '较新', '', `data-direction="-1" ${ui.eventPage ? '' : 'disabled'}`)}${button('event-page', '较早', '', `data-direction="1" ${ui.eventPage < pages - 1 ? '' : 'disabled'}`)}${button('event-page', '回到最新', '', `data-direction="latest" ${ui.eventPage || unseen ? '' : 'disabled'}`)}</div>`;
  const eventNames = {
    initialized: '执行计划已确认',
    task_status: '任务状态更新',
    retry: '重新提交（新建任务）',
    skip: '跳过建议性步骤',
    'request-skip': '申请保留原输入跳过',
    'cancel-skip': '取消跳过请求',
    bypass: '兼容性校验后跳过处理',
    skip_cancelled: '智能体保留处理步骤',
    terminate: '终止后续编排',
    action_started: '正在创建新任务',
    action_failed: '操作失败',
    task_submitted: '提交任务',
    set_result: '记录任务结果',
    await_decision: '等待用户处理',
    finished: '生成完成摘要',
    demo_loaded: '载入演示数据',
    inputs_recorded: '记录输入资产与版本',
    action_reconciled: '已核实任务创建结果',
    heartbeat: '编排心跳',
  };
  $('#timeline').innerHTML = visible.length
    ? visible
        .map((e) => {
          const n = ui.snapshot.nodes.find((n) => n.stage === e.stage && n.member === e.member);
          const failed = e.type === 'action_failed' || ['FAILED', 'DELETED'].includes(e.detail);
          const appearance = eventAppearance(e, failed);
          return `<div class="event" role="listitem" data-seq="${esc(e.seq)}"><time class="event-time" title="${date(e.ts)}">${clock(e.ts)}</time><span class="${appearance.state}"><span class="status-icon" aria-hidden="true">${appearance.icon}</span></span><div class="event-detail"><strong>${esc(n?.name || eventNames[e.type] || e.type)}</strong>${n ? ' · ' + esc(eventNames[e.type] || e.type) : ''}${e.task_id ? ` <code>${esc(e.task_id)}</code>` : ''}${e.detail ? eventDetailHTML(e, ui.eventExpanded.has(e.seq)) : ''}</div><span class="event-actor">${esc(e.actor)}</span></div>`;
        })
        .join('')
    : empty('暂无匹配事件', 'Agent 与网页上的操作会记录在这里。');
  $('#timeline').scrollTop = scroll;
}
function summaryWarning(n) {
  if (n.bypassed) {
    return '已跳过处理，沿用原输入；不生成新版本';
  }
  if (n.skipped) {
    return n.kind === 'eval' ? '已跳过，尚未评测' : '已跳过，未执行';
  }
  return n.label;
}
function renderSummary() {
  const s = ui.snapshot;
  const state = s.state;
  const out = state.output || {};
  const outputSource = out.from_stage || s.plan.output?.from_stage || '见已确认执行计划';
  const evals = s.nodes.filter((n) => n.kind === 'eval');
  const attempts = s.nodes.reduce((v, n) => v + n.attempt_count, 0);
  const failed = s.nodes.reduce(
    (v, n) =>
      v + (n.raw_status === 'FAILED') + n.attempts.filter((a) => a.status === 'FAILED').length,
    0,
  );
  $('#summary').innerHTML =
    `<section class="summary"><div class="artifact"><div class="row between"><h2>管线产物</h2>${button('copy-output', '复制路径', '', out.target_path ? '' : 'disabled')}</div><div class="artifact-path">${esc(out.target_path || '尚未由 Agent 核实并记录产物')}</div><p class="small muted">资产 <code>${esc(out.target_asset_id || '—')}</code> · 版本 <code>${esc(out.target_version_id || '—')}</code></p><p class="section-caption">来源步骤：${esc(outputSource)}。产物以 Agent 的 show-task / show-version 核实结果为准。</p><p class="section-caption mt">发布提醒：请在智能体最终摘要中核对各产物版本状态，并按需确认发布。保留 DRAFT 不影响管线完成。</p></div><div class="stats"><div class="stat"><p>总耗时</p><strong>${duration(state.created_at, state.finished_at)}</strong><small>计划确认至当前终态</small></div><div class="stat"><p>完成步骤</p><strong>${s.progress.done}<span class="muted small"> / ${s.progress.total}</span></strong><small>含正常跳过和已结束的建议性步骤</small></div><div class="stat"><p>任务尝试</p><strong>${attempts}<span class="muted small"> 次</span></strong><small>其中 ${failed} 次失败</small></div><div class="stat"><p>评测结果</p><strong>${evals.filter((n) => n.raw_status === 'SUCCEEDED').length}<span class="muted small"> / ${evals.length}</span></strong><small>成功评测成员</small></div></div><div><h2 class="mb">各步骤汇总</h2><div class="table-wrap"><table><thead><tr><th>步骤</th><th>状态</th><th>任务 ID</th><th>尝试</th><th></th></tr></thead><tbody>${s.nodes.map((n) => `<tr><td>${esc(n.name)}</td><td>${status(n.display_status, n.label, n.not_applicable)}</td><td><code>${esc(n.task_id || '—')}</code></td><td>${n.attempt_count || '—'}</td><td>${button('stage', '查看', '', `data-key="${esc(n.key)}"`)}</td></tr>`).join('')}</tbody></table></div></div><div class="artifact"><h2 class="mb">评测报告</h2>${evals.map((n) => `<div class="row between mb"><span>${esc(n.name)} · ${status(n.display_status, n.label, n.not_applicable)}</span>${reportAction(n)}</div>`).join('') || '<p class="muted small">此运行未配置评测。</p>'}</div><div class="artifact"><h2 class="mb">告警与建议</h2><ul class="warning-list">${
      s.nodes
        .filter(
          (n) =>
            !n.not_applicable &&
            (['FAILED', 'DELETED', 'SKIPPED'].includes(n.raw_status) || n.skipped),
        )
        .map(
          (n) =>
            `<li>${esc(n.name)}：${esc(summaryWarning(n))}${n.fail_fast ? '' : '（建议性，可在终端 Agent 协同下补跑）'}</li>`,
        )
        .join('') || '<li>当前记录无失败或跳过步骤。</li>'
    }</ul></div></section>`;
}
function dagPathClass(active, done) {
  if (active) {
    return 'active';
  }
  if (done) {
    return 'done';
  }
  return '';
}
function progressSegment(n, mini) {
  if (mini) {
    return `<span class="progress-seg ${n.display_status} ${n.not_applicable ? 'not-applicable' : ''}" title="${esc(n.name + ' · ' + n.label)}"></span>`;
  }
  return `<button type="button" class="progress-seg ${n.display_status} ${n.not_applicable ? 'not-applicable' : ''} ${n.display_status === 'RUNNING' ? 'running' : ''}" data-action="stage" data-key="${esc(n.key)}" title="${esc(n.name + ' · ' + n.label)}" aria-label="${esc(n.name + ' · ' + n.label)}"></button>`;
}
function deleteRunButton(run) {
  let reason = '仅删除本地记录，云端任务和资产不受影响';
  if (run.readonly) {
    reason = '旧版记录为只读模式';
  } else if (run.state.pending_action) {
    reason = '请先到智能体核实未完成的提交事务';
  } else if (!terminalRuns.has(run.state.status)) {
    reason = '请先终止后续编排，再删除本地记录';
  }
  const disabled = run.actions?.delete ? '' : 'disabled';
  return button(
    'delete-run',
    '删除本地记录',
    'danger',
    `data-run="${esc(run.run_id)}" ${disabled} title="${esc(reason)}"`,
  );
}
function runTableRow(r) {
  if (r.error) {
    return `<tr><td><code>${esc(r.run_id)}</code></td><td colspan="5" class="error-text">${esc(r.error)}</td></tr>`;
  }
  return `<tr><td>${button('open-run', esc(r.state.pipeline_name || r.run_id), 'text-button run-link', `data-run="${esc(r.run_id)}"`)}<div class="run-id mono">${esc(r.run_id)}</div></td><td>${status(r.state.status)}${r.readonly ? '<div class="tag">旧版只读</div>' : ''}</td><td>${progress(r.nodes, true)}<small>${r.progress.done}/${r.progress.total} 完成</small></td><td>${esc(r.progress.current)}</td><td><div>${date(r.state.created_at)}</div><small class="muted">${duration(r.state.created_at, r.state.finished_at)}</small></td><td><div class="row">${button('open-run', '打开', '', `data-run="${esc(r.run_id)}"`)}${deleteRunButton(r)}</div></td></tr>`;
}
function runListEmptyTitle() {
  if (ui.runs.length) {
    return '没有匹配的运行';
  }
  return '暂无管线运行';
}
function runViewTabs(state) {
  if (terminalRuns.has(state.status)) {
    return `<nav class="run-tabs" aria-label="运行视图">${button('view-pipeline', '执行过程', ui.view === 'pipeline' ? 'active' : '')}${button('view-summary', '完成摘要', ui.view === 'summary' ? 'active' : '')}</nav>`;
  }
  return '';
}
function reportAction(n) {
  if (n.raw_status === 'SUCCEEDED') {
    return button('open-report', '查看报告', '', `data-key="${esc(n.key)}"`);
  }
  return button(
    'stage',
    n.actions.retry ? '查看 / 补跑' : '查看详情',
    '',
    `data-key="${esc(n.key)}"`,
  );
}

export { renderDAG, renderEvents, renderRun, renderRuns };
