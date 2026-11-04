// Plan checks, asset registration and output verification without cloud tasks.
import { $, date, detailFields, empty, esc, json, status } from './common.js';
import { node, ui } from './state.js';

function uploadDescription(n, local, obs) {
  if (n.skipped) {
    return n.skip_reason || '本次无需上传注册，按已确认的输入交接记录继续。';
  }
  if (local) {
    return '由终端 Agent 使用资产中心导入数据、注册资产与版本，并核实下游使用的确切版本。本步骤不创建处理或评测任务。';
  }
  if (obs) {
    return '输入数据已在 OBS，无需再次上传；由终端 Agent 注册数据资产与版本，并核实下游使用的确切版本。本步骤不创建处理或评测任务。';
  }
  return '由终端 Agent 完成所需的数据上传、资产注册与版本核实，并登记交接信息。本步骤不创建处理或评测任务。';
}
function manualInfo(n) {
  if (n.stage === 'plan') {
    return {
      tag: '检查项',
      config: '检查项',
      subtitle: '输入 · 步骤 · 算子 · 资源检查',
      description:
        '核对输入数据、步骤依赖、算子参数、资源与输出，并确认执行范围。本步骤只记录执行前检查，不创建云端任务。',
      logs: ['计划确认不产生日志', '这是执行前检查项；确认记录见概览、检查项和事件时间线。'],
      preview: [
        '计划确认不产生数据输出',
        '本步骤的结果是已确认的执行计划，可在“检查项”中查看；数据产物由后续处理步骤生成。',
      ],
    };
  }
  if (n.stage === 'upload') {
    const inputs = ui.snapshot.state.inputs || [];
    const local = inputs.some((i) => i.source_type === 'local');
    const obs = inputs.some((i) => i.source_type === 'obs');
    const description = uploadDescription(n, local, obs);
    return {
      tag: '数据准备',
      config: '注册信息',
      subtitle: n.skipped ? '无需上传注册' : '数据资产与版本登记',
      description,
      logs: [
        n.skipped ? '本次已跳过上传注册' : '上传注册没有作业日志',
        n.skipped ? description : '上传与注册由终端 Agent 执行，操作进度和结果见终端及事件时间线。',
      ],
      preview: [
        n.skipped ? '复用已有数据资产' : '查看资产登记结果',
        '此处展示输入路径、资产与版本；文件内容预览请进入后续处理步骤。',
      ],
    };
  }
  if (n.stage === 'output') {
    return {
      tag: '产物核对',
      config: '产物信息',
      subtitle: '最终数据产物核实',
      description:
        '由终端 Agent 核实最终数据路径、资产和版本，汇总处理与评测结果。本步骤不创建云端任务。',
      logs: [
        '产物核对不产生作业日志',
        '运行日志保存在对应处理或评测步骤；核对结果见概览和完成摘要。',
      ],
      preview: [
        '最终产物信息',
        '这里展示已核实的数据路径、资产和版本；文件内容预览请进入对应处理步骤。',
      ],
    };
  }
  return {
    tag: '确认项',
    config: '确认信息',
    subtitle: '由 Agent 确认并记录',
    description: '由终端 Agent 完成检查并登记结果，本步骤不创建云端任务。',
    logs: ['本步骤不产生作业日志', '操作记录见终端及事件时间线。'],
    preview: ['本步骤的登记结果', '输入与产物信息由终端 Agent 核实后记录。'],
  };
}
function inputDescription() {
  return (ui.snapshot.state.inputs || []).map(describeInput).join('\n') || '以已确认执行计划为准';
}
function describeInput(input) {
  if (input.source_type === 'asset') {
    return `已有资产 ${input.asset_id || '待核实'} / 版本 ${input.version_id || '待核实'}`;
  }
  if (input.source_type === 'obs') {
    return `OBS 目录 ${input.obs_path || '待核实'}`;
  }
  if (input.source_type === 'local') {
    return `本地目录 ${input.local_path || '待核实'}`;
  }
  return '以已确认执行计划为准';
}
function stepKindTag(n, info) {
  if (n.kind === 'manual') {
    return info.tag;
  }
  return n.fail_fast ? '阻断步骤' : '建议性';
}
function manualContext(n) {
  return json([n, ui.snapshot?.state.inputs, ui.snapshot?.state.output]);
}
function registrationRows(n) {
  const sources = n.registrations || [];
  const missing = n.raw_status === 'SUCCEEDED' ? '未记录，请到智能体补齐登记信息' : '待登记';
  if (!sources.length) {
    return [['输入来源', inputDescription()], ['资产 ID', missing], ['版本 ID', missing]];
  }
  return [
    ['输入来源', inputDescription()],
    ...sources.flatMap((source) => {
      const prefix = sources.length > 1 ? `输入 ${source.id} · ` : '';
      return [
        [prefix + '资产名称', source.asset_name || '待核实'],
        [prefix + '数据路径', source.obs_path || source.local_path || '待核实'],
        [prefix + '资产 ID', source.asset_id || missing],
        [prefix + '版本 ID', source.version_id || missing],
      ];
    }),
  ];
}
function manualRows(n) {
  const state = ui.snapshot.state;
  if (n.stage === 'plan') {
    return [
      ['管线', state.pipeline_name || ui.run],
      ['工作空间 / 区域', `${state.workspace_id || '—'} / ${state.region || '—'}`],
      ['确认时间', date(state.created_at)],
      ['输入数据', inputDescription()],
      [
        '处理与评测步骤',
        ui.snapshot.nodes
          .filter((v) => v.kind !== 'manual')
          .map((v) => `${v.name}（等待：${v.depends_on.join('、') || '输入准备'}）`)
          .join('\n') || '以已确认执行计划为准',
      ],
    ];
  }
  if (n.stage === 'upload') {
    return registrationRows(n);
  }
  const input = state.inputs?.[0] || {};
  const out = n.stage === 'output' ? state.output || {} : {};
  return [
    ...(n.stage === 'upload' ? [['输入来源', inputDescription()]] : []),
    ...(n.stage === 'output' ? [['产物来源步骤', out.from_stage || ui.snapshot.plan.output?.from_stage || '见已确认执行计划；仅评测时保留输入数据集']] : []),
    [
      '数据路径',
      n.target_path ||
        out.target_path ||
        (n.stage === 'upload' ? input.obs_path || input.local_path : '') ||
        '待 Agent 核实并记录',
    ],
    [
      '资产 ID',
      n.target_asset_id ||
        out.target_asset_id ||
        (n.stage === 'upload' ? input.asset_id : '') ||
        '待登记',
    ],
    [
      '版本 ID',
      n.target_version_id ||
        out.target_version_id ||
        (n.stage === 'upload' ? input.version_id : '') ||
        '待登记',
    ],
  ];
}
function renderManualStep() {
  const n = node();
  const info = manualInfo(n);
  if (ui.tab === 'overview') {
    $('#drawer-body').innerHTML =
      `<div class="detail-card"><h3>${status(n.display_status, n.label, n.not_applicable)}</h3><p class="mt">${esc(info.description)}</p></div>${detailFields(manualRows(n))}`;
  } else if (ui.tab === 'config' && n.stage === 'plan') {
    const checks = [
      ['输入数据', '数据来源、格式、资产版本及所处处理阶段'],
      ['步骤与依赖', '用户选择的算子顺序、输入输出兼容性及评测范围'],
      ['算子与参数', '算子来源、当次查询结果、环境变量与输入挂载'],
      ['资源与输出', '资源池、规格、任务命名、最终产物来源步骤及数据集名称'],
      ['执行确认', '工作空间、区域和本次允许执行的操作范围'],
    ];
    $('#drawer-body').innerHTML =
      `<h3 class="mb">执行前检查项</h3><p class="small muted mb">以下内容由终端 Agent 核对后随执行计划登记。此处不配置或提交云端任务。</p><div class="table-wrap"><table><thead><tr><th>检查项</th><th>核对内容</th></tr></thead><tbody>${checks.map(([k, v]) => `<tr><td>${k}</td><td>${v}</td></tr>`).join('')}</tbody></table></div><details class="mt"><summary>查看已确认执行计划</summary><pre class="code mt">${esc(json(ui.snapshot.plan))}</pre></details>`;
  } else if (ui.tab === 'config') {
    $('#drawer-body').innerHTML =
      `<h3 class="mb">${info.config}</h3><p class="small muted mb">${esc(info.description)}</p>${detailFields(manualRows(n))}`;
  } else if (ui.tab === 'logs') {
    $('#drawer-body').innerHTML = empty(...info.logs);
  } else {
    $('#drawer-body').innerHTML =
      empty(...info.preview) + (n.stage === 'plan' ? '' : detailFields(manualRows(n)));
  }
}

export { manualContext, manualInfo, renderManualStep, stepKindTag };
