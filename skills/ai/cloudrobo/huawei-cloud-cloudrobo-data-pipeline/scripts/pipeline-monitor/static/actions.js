// Explicit confirmation and submission for retry, skip and termination.
import { $, api, button, empty, enc, esc, json, parseArray, toast } from './common.js';
import { differences, renderDrawer } from './details.js';
import { navigate, refresh } from './navigation.js';
import { renderRun } from './pipeline.js';
import { node, runAPI, ui } from './state.js';

function actionPresentation(type) {
  const actions = {
    retry: {
      title: '重新提交（新建任务）',
      submit: '确认提交',
      success: '已创建新任务。后续步骤请回到终端回复“继续”。',
    },
    skip: {
      title: '跳过建议性步骤',
      submit: '确认跳过',
      success: '已跳过建议性步骤。请回到终端继续编排。',
    },
    'request-skip': {
      title: '保留原输入跳过处理步骤',
      submit: '申请跳过',
      success: '已登记请求。请到智能体核实原输入及下游兼容性，校验通过后生效。',
    },
    'cancel-skip': {
      title: '取消跳过请求',
      submit: '确认取消请求',
      success: '已取消跳过请求，保留原处理步骤。',
    },
    terminate: {
      title: '终止管线',
      submit: '确认终止',
      success: '已终止后续编排。现有云端任务仍继续运行。',
    },
  };
  return actions[type] || actions.terminate;
}
function resourcePoolFields(config) {
  return `<label>资源池<select id="retry-pool" aria-describedby="retry-pool-help"><option value="PUBLIC_POOL" ${config.resource_pool_type === 'PUBLIC_POOL' ? 'selected' : ''}>公共池</option><option value="DEDICATED_POOL" ${config.resource_pool_type === 'DEDICATED_POOL' ? 'selected' : ''}>专属池</option></select><small id="retry-pool-help" class="muted"></small></label><label hidden>专属池资源 ID<input id="retry-resource" value="${esc(config.resource_id || '')}" disabled></label><label hidden>专属池名称<input id="retry-pool-name" value="${esc(config.dedicated_pool_name || '')}" disabled></label>`;
}
function updateRetryPool() {
  const pool = $('#retry-pool');
  if (!pool) {
    return;
  }
  const dedicated = pool.value === 'DEDICATED_POOL';
  for (const selector of ['#retry-resource', '#retry-pool-name']) {
    const input = $(selector);
    input.closest('label').hidden = !dedicated;
    input.disabled = !dedicated;
    input.required = dedicated;
  }
  $('#retry-pool-help').textContent = dedicated
    ? '请填写同一个专属池的真实资源 ID 和名称，可在 CloudRobo Console 查询。'
    : '使用公共池，无需填写专属池信息。';
}
async function showAction(type) {
  const n = node();
  if (type !== 'terminate' && (!n || ui.attempt !== n.task_id)) {
    return;
  }
  ui.modal = {
    type,
    stage: n?.stage,
    member: n?.member,
    task: type === 'terminate' ? null : n?.task_id,
    version: ui.snapshot.state_version,
  };
  const dialog = $('#action-dialog');
  dialog.innerHTML = `<header class="dialog-header"><h2 id="dialog-title">${actionPresentation(type).title}</h2>${button('dialog-close', '×', 'icon-button', 'aria-label="关闭对话框"')}</header><div id="dialog-body" class="dialog-body">${empty(type === 'retry' ? '正在重新查询算子与上游版本…' : '正在读取操作…')}</div><footer class="dialog-footer">${button('dialog-close', '取消')}${button('action-submit', actionPresentation(type).submit, type === 'terminate' ? 'danger fill' : 'primary', 'id="action-submit" disabled')}</footer>`;
  dialog.showModal();
  if (type === 'retry') {
    try {
      const draft = await api(
        runAPI(
          '/actions/retry/draft?stage=' +
            enc(n.stage) +
            (n.member ? '&member=' + enc(n.member) : ''),
        ),
      );
      if (!dialog.open || ui.modal?.type !== 'retry') {
        return;
      }
      ui.modal.draft = draft;
      const c = draft.config;
      const outputField =
        draft.kind === 'proc'
          ? `<label>输出名<input id="retry-output" required minlength="2" maxlength="64" value="${esc(c.output_name)}"><small class="muted">默认使用管线名-步骤短名-秒级时间戳，可修改；完整名称不超过 64 字符。</small></label>`
          : `<p class="wide">评测输入数据集（只读）：${esc(c.dataset_name)} · <code>${esc(c.dataset_path)}</code></p>`;
      const headFields =
        draft.kind === 'proc'
          ? `<label>Head 规格<textarea id="retry-head">${esc(json(c.head_spec || {}))}</textarea></label><label>Worker 数量<input type="number" min="1" step="1" id="retry-count" value="${esc(c.worker_num || 1)}"></label>`
          : '';

      $('#dialog-body').innerHTML =
        `<div class="banner">将创建新任务，保留全部历史尝试。算子信息来自本次查询；后续步骤仍由终端 Agent 推进。</div><div class="locked-fields"><p><b>算子（只读）</b> ${esc(c.algo_name)} · <code>${esc(c.algo_id)}</code></p><p>镜像 <code>${esc(c.image)}</code></p><p>入口 <code>${esc(c.algo_entrance)}</code></p></div><div class="form-grid"><label class="wide">任务名<input id="retry-name" required minlength="3" maxlength="64" value="${esc(draft.name)}"></label>${outputField}${resourcePoolFields(c)}<label>Worker 规格<textarea id="retry-worker">${esc(json(c.worker_spec))}</textarea></label>${headFields}<label class="wide">已声明环境变量（只修改 value）<textarea id="retry-envs">${esc(json(parseArray(c.envs)))}</textarea></label><label class="wide">输入挂载（只修改 url_path）<textarea id="retry-inputs">${esc(json(parseArray(c.inputs)))}</textarea></label></div>${differences(c, draft.previous_config)}<label class="confirmation"><input type="checkbox" id="action-confirm">我已核对以上配置，确认在云端创建新任务。</label><p id="action-error" class="error-text mt" role="alert"></p>`;
      updateRetryPool();
    } catch (error) {
      $('#dialog-body').innerHTML =
        `<div class="banner critical"><strong>无法生成待确认配置，已阻止提交</strong><p class="mt">${esc(error.message)}</p></div><p class="small muted">请回到终端检查算子、原始提交配置与上游数据版本。</p>`;
    }
  } else if (type === 'request-skip') {
    $('#dialog-body').innerHTML =
      `<p>申请跳过 <strong>${esc(n.name)}</strong>，原输入为 <code>${esc(n.bypass.input_from.join('、'))}</code>。</p><p class="mt">受影响的直接下游：${esc(n.bypass.consumers.join('、') || '最终产物核对')}。</p><div class="banner warning mt">转换/清洗不会执行，也不产生新版本。智能体须核实原输入资产、版本、路径，以及所有下游算子的实际格式要求；未确认兼容前保持阻断。多输入合并步骤不能原样跳过。</div><label class="confirmation"><input type="checkbox" id="action-confirm">申请沿用原输入，校验后跳过。</label><p id="action-error" class="error-text mt" role="alert"></p>`;
  } else if (type === 'cancel-skip') {
    $('#dialog-body').innerHTML =
      `<p>取消 <strong>${esc(n.name)}</strong> 的跳过请求，继续保留该处理步骤。</p><label class="confirmation"><input type="checkbox" id="action-confirm">确认取消请求。</label><p id="action-error" class="error-text mt" role="alert"></p>`;
  } else if (type === 'skip') {
    $('#dialog-body').innerHTML =
      `<p>跳过 <strong>${esc(n.name)}</strong> 后保留已有数据产物，完成摘要将标记未评测告警。后续步骤由 Agent 推进，完成后仍可补跑该评测。</p><label class="confirmation"><input type="checkbox" id="action-confirm">确认跳过此建议性步骤。</label><p id="action-error" class="error-text mt" role="alert"></p>`;
  } else {
    const running = ui.snapshot.nodes.filter(
      (n) =>
        n.task_id && n.raw_status && !['SUCCEEDED', 'FAILED', 'DELETED'].includes(n.raw_status),
    );
    $('#dialog-body').innerHTML =
      `<div class="banner warning">终止管线会停止提交后续步骤。已经运行的云端任务仍会继续运行，需要在终端单独处理。</div>${running.length ? `<h3 class="mb">仍在运行的云端任务</h3><ul>${running.map((n) => `<li>${esc(n.name)} · <code>${esc(n.task_id)}</code></li>`).join('')}</ul>` : '<p>当前没有记录中的运行中任务。</p>'}<label class="stack gap-sm mt">请输入 run_id 最后四位 <strong>${esc(ui.run.slice(-4))}</strong><input id="terminate-code" autocomplete="off" maxlength="4" aria-label="run_id 最后四位"></label><p id="action-error" class="error-text mt" role="alert"></p>`;
  }
}
async function submitAction() {
  const modal = ui.modal;
  if (!modal || ui.busy) {
    return;
  }
  if (modal.type === 'delete') {
    await submitDeleteRun();
    return;
  }
  const body = {
    type: modal.type,
    stage: modal.type === 'terminate' ? null : modal.stage,
    member: modal.type === 'terminate' ? null : modal.member,
    expected_task_id: modal.task,
    expected_version: modal.version,
    confirmed: true,
  };
  if (modal.type === 'terminate') {
    body.confirmation = $('#terminate-code').value;
  }
  if (modal.type === 'retry') {
    if (![...$('#action-dialog').querySelectorAll('input')].every((e) => e.reportValidity())) {
      return;
    }
    try {
      body.draft_id = modal.draft.draft_id;
      body.overrides = {
        name: $('#retry-name').value,
        resource_pool_type: $('#retry-pool').value,
        worker_spec: JSON.parse($('#retry-worker').value),
        envs: JSON.stringify(JSON.parse($('#retry-envs').value)),
        inputs: JSON.stringify(JSON.parse($('#retry-inputs').value)),
      };
      if (body.overrides.resource_pool_type === 'DEDICATED_POOL') {
        body.overrides.resource_id = $('#retry-resource').value.trim();
        body.overrides.dedicated_pool_name = $('#retry-pool-name').value.trim();
      }
      if (modal.draft.kind === 'proc') {
        body.overrides.output_name = $('#retry-output').value;
        body.overrides.head_spec = JSON.parse($('#retry-head').value);
        body.overrides.worker_num = Number($('#retry-count').value);
      }
    } catch (error) {
      showActionError('JSON 格式有误：' + error.message);
      return;
    }
  }
  ui.busy = true;
  $('#action-submit').disabled = true;
  $('#action-submit').textContent = '正在处理…';
  try {
    const result = await api(runAPI('/actions'), body);
    $('#action-dialog').close();
    ui.snapshot = result;
    ui.modal = null;
    renderRun();
    if (ui.selected) {
      const n = node();
      ui.attempt = n.task_id;
      await renderDrawer();
    }
    toast(actionPresentation(modal.type).success);
    await refresh(true);
  } catch (error) {
    if (error.status === 409) {
      $('#action-dialog').close();
      toast('该步骤已被其他操作处理，页面已刷新。');
      await refresh(true);
    } else {
      showActionError(error.message);
      await refresh(true);
      if (ui.modal) {
        ui.modal.version = ui.snapshot?.state_version;
      }
    }
  } finally {
    ui.busy = false;
    if ($('#action-submit')) {
      $('#action-submit').textContent = actionPresentation(modal.type).submit;
      updateConfirmation();
    }
  }
}
function showActionError(message) {
  const error = $('#action-error');
  if (error) {
    error.textContent = message;
    error.scrollIntoView({
      block: 'nearest',
    });
  }
}
function updateConfirmation() {
  const submit = $('#action-submit');
  if (!submit) {
    return;
  }
  if (ui.modal?.type === 'delete') {
    submit.disabled = ui.busy || !ui.modal.version || !$('#action-confirm')?.checked;
    return;
  }
  submit.disabled =
    ui.busy ||
    Boolean(ui.snapshot?.state.pending_action) ||
    (ui.modal?.type === 'terminate'
      ? $('#terminate-code')?.value !== ui.run.slice(-4)
      : !$('#action-confirm')?.checked);
}

async function showDeleteRun(run) {
  const dialog = $('#action-dialog');
  ui.modal = { type: 'delete', run, version: null };
  dialog.innerHTML = `<header class="dialog-header"><h2 id="dialog-title">删除本地运行记录</h2>${button('dialog-close', '×', 'icon-button', 'aria-label="关闭对话框"')}</header><div id="dialog-body" class="dialog-body">${empty('正在核对运行状态…')}</div><footer class="dialog-footer">${button('dialog-close', '取消')}${button('action-submit', '确认删除本地记录', 'danger fill', 'id="action-submit" disabled')}</footer>`;
  dialog.showModal();
  try {
    const snapshot = await api('/api/runs/' + enc(run));
    if (!dialog.open || ui.modal?.run !== run) {
      return;
    }
    if (!snapshot.actions.delete) {
      throw Error('当前记录不可删除：请先终止后续编排，并核实所有未完成的提交事务。旧版记录只读。');
    }
    ui.modal.version = snapshot.state_version;
    $('#dialog-body').innerHTML =
      `<p>运行：<strong>${esc(snapshot.state.pipeline_name || run)}</strong></p><p class="mono mt">${esc(run)}</p><div class="banner warning mt">将永久删除这次运行的本地计划、状态、任务配置、历史事件和已下载日志，删除后无法从本地恢复。</div><p class="mt">不会停止或删除云端任务，也不会删除 OBS 数据、资产或版本。已停止管线中的云端任务可能仍在运行。</p><label class="confirmation"><input type="checkbox" id="action-confirm">确认仅删除这条本地运行记录。</label><p id="action-error" class="error-text mt" role="alert"></p>`;
  } catch (error) {
    if (dialog.open && ui.modal?.run === run) {
      $('#dialog-body').innerHTML =
        `<div class="banner critical" role="alert">${esc(error.message)}</div>`;
    }
  }
}
async function submitDeleteRun() {
  const modal = ui.modal;
  if (!modal.version || !$('#action-confirm')?.checked) {
    return;
  }
  ui.busy = true;
  $('#action-submit').disabled = true;
  $('#action-submit').textContent = '正在删除本地记录…';
  try {
    const result = await api('/api/runs/' + enc(modal.run) + '/delete', {
      confirmed: true,
      expected_version: modal.version,
    });
    $('#action-dialog').close();
    ui.modal = null;
    ui.runs = ui.runs.filter((entry) => entry.run_id !== modal.run);
    await navigate();
    toast(result.warning || '本地运行记录已删除，云端任务和资产不受影响。');
  } catch (error) {
    if (error.status === 404) {
      $('#action-dialog').close();
      ui.modal = null;
      await navigate();
      toast('该本地记录已不存在，已刷新运行列表。');
    } else {
      showActionError(error.message);
      if (error.status === 409) {
        modal.version = null;
        $('#action-confirm').checked = false;
        showActionError(error.message + '，请关闭窗口并刷新后重新确认。');
      }
    }
  } finally {
    ui.busy = false;
    $('#action-submit').textContent = '确认删除本地记录';
    updateConfirmation();
  }
}

export { showAction, showDeleteRun, submitAction, updateConfirmation, updateRetryPool };
