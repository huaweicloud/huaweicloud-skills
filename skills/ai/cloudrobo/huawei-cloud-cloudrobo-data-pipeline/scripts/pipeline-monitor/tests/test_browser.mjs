#!/usr/bin/env node
// Optional, offline browser smoke test. Node 22+ and installed Chrome/Chromium.
// Starts its own isolated demo server; never touches a real run or calls cloud APIs.
import { spawn, spawnSync } from 'node:child_process';
import { existsSync, mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import assert from 'node:assert/strict';

const here = dirname(fileURLToPath(import.meta.url));
const chrome =
  process.env.CHROME_PATH ||
  [
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/usr/bin/google-chrome',
    '/usr/bin/google-chrome-stable',
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
    ...['PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA']
      .filter((name) => process.env[name])
      .map((name) => join(process.env[name], 'Google/Chrome/Application/chrome.exe')),
  ].find(existsSync);
if (!chrome || typeof WebSocket === 'undefined') {
  console.error('需要 Node 22+ 和 Chrome/Chromium；可用 CHROME_PATH 指定浏览器。');
  process.exit(2);
}
const temporary = mkdtempSync(join(tmpdir(), 'pipeline-browser-'));
const outIndex = process.argv.indexOf('--out');
const output = outIndex >= 0 ? resolve(process.argv[outIndex + 1]) : join(temporary, 'screenshots');
mkdirSync(output, { recursive: true });
let service;
let demoURL;
let browser;
let socket;
const pending = new Map();
let sequence = 0;
let session;
let previewRequests = 0;
let failNextPreview = false;
let taskRequests = 0;
let resourceRequests = 0;
let apiRequests = 0;
const errors = [];
const moduleResponses = new Map();
const browserMessages = [];
const passed = [];
const actionRequests = [];
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
function lineFrom(process, stream, pattern) {
  return new Promise((resolve, reject) => {
    let buffer = '';
    const timer = setTimeout(
      () => reject(Error(stream + ' 进程启动超时\n' + buffer.slice(-800))),
      60000,
    );
    process[stream].on('data', (chunk) => {
      buffer += chunk;
      const match = buffer.match(pattern);
      if (match) {
        clearTimeout(timer);
        resolve(match[1]);
      }
    });
    process.on('exit', (code) => {
      clearTimeout(timer);
      reject(Error('进程提前退出 ' + code + '\n' + buffer.slice(-800)));
    });
  });
}
function send(method, params = {}, target = session) {
  return new Promise((resolve, reject) => {
    const id = ++sequence;
    const timer = setTimeout(() => {
      pending.delete(id);
      reject(Error('CDP 超时 ' + method));
    }, 20000);
    pending.set(id, { resolve, reject, timer });
    socket.send(
      JSON.stringify({
        id,
        method,
        params,
        ...(target ? { sessionId: target } : {}),
      }),
    );
  });
}
async function evaluate(expression) {
  const result = await send('Runtime.evaluate', {
    expression,
    awaitPromise: true,
    returnByValue: true,
  });
  if (result.exceptionDetails) {
    throw Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
  }
  return result.result.value;
}
async function until(expression, label) {
  for (let i = 0; i < 100; i++) {
    if (await evaluate(expression)) {
      return;
    }
    await sleep(100);
  }
  throw Error('等待失败: ' + label);
}
async function click(selector) {
  await evaluate(`document.querySelector(${JSON.stringify(selector)})?.click()`);
}
async function verifySkipHint(action, label, text) {
  const selector = `[data-action="${action}"]`;
  const point = await evaluate(`(()=>{const button=document.querySelector(${JSON.stringify(selector)});const wrapper=button.closest('.action-with-hint');wrapper.scrollIntoView({block:'center'});const rect=wrapper.getBoundingClientRect();return {x:rect.x+rect.width/2,y:rect.y+rect.height/2};})()`);
  await send('Input.dispatchMouseEvent', { type: 'mouseMoved', ...point });
  assert(await evaluate(`(()=>{const button=document.querySelector(${JSON.stringify(selector)});const wrapper=button.closest('.action-with-hint');const hint=document.getElementById(button.getAttribute('aria-describedby'));return wrapper.matches(':hover')&&hint.checkVisibility();})()`));
  assert.equal(await evaluate(`document.querySelector(${JSON.stringify(selector)}).textContent`), label);
  assert((await evaluate(`document.querySelector(${JSON.stringify(selector)}).title`)).includes(text));
}
async function screenshot(name) {
  await sleep(300);
  const result = await send('Page.captureScreenshot', {
    format: 'png',
    captureBeyondViewport: false,
  });
  writeFileSync(join(output, name + '.png'), Buffer.from(result.data, 'base64'));
}
function pass(name) {
  passed.push(name);
  console.log('PASS ' + name);
}
function seedMultiInputRun() {
  const source = `import json, sys
from pathlib import Path
sys.path[:0] = [sys.argv[1], str(Path(sys.argv[1]).parent)]
from pipeline_state import Store, atomic_json, read_json_object
store = Store(sys.argv[2])
record_path = store.directory('demo-completed-1003') / 'tasks' / 'demo-diversity.json'
record = read_json_object(record_path)
record['task_config'].update(resource_pool_type='DEDICATED_POOL', resource_id='existing-demo-id', dedicated_pool_name='existing-demo-pool')
atomic_json(record_path, record)
inputs = [{'dataset_type': 'BUILD_IN_ASSET', 'asset_id': key, 'version_id': 'v1',
           'asset_name': 'data-' + key, 'obs_path': 'obs://example/' + key + '/'} for key in ('B', 'A')]
plan = {'name': 'multi-input-monitor', 'inputs': [{'source_type': 'asset', 'asset_id': 'source', 'version_id': 'v1'}],
        'stages': [{'id': key, 'external': True, 'artifacts': {'target_asset_id': key,
                    'target_version_id': 'v1', 'target_path': 'obs://example/' + key + '/', 'output_name': 'data-' + key},
                    'input_from': ['input:default']} for key in ('A', 'B')]
                  + [{'id': 'C', 'name': '双输入合并', 'depends_on': ['A', 'B'], 'input_from': ['B', 'A']}]}
store.init('demo-multi-1004', plan)
store.set_task('demo-multi-1004', 'C', None, None, 'demo-clean-2',
               {'dataset_configs': json.dumps(inputs)}, 'merge-two-datasets')
for required in (False, True):
    source = {'source_type': 'asset', 'asset_id': 'original-data', 'version_id': 'v3', 'asset_name': 'original-data',
              'obs_path': 'obs://example/original/', 'data_source_type': 'h5' if required else 'lerobotv3'}
    stages = [{'id': 'convert', 'operator': '数据转换--H5转LeRobotV3'}, {'id': 'clean', 'operator': '数据清洗'}] if required else [
               {'id': 'clean', 'operator': '数据清洗'}, {'id': 'eval', 'kind': 'eval', 'operator': '数据集质量评测-LeRobot'}]
    store.init('demo-required-1006' if required else 'demo-bypass-1005', {'name': 'required-conversion' if required else 'skip-processing',
               'inputs': [source], 'output': {'from_stage': 'clean'}, 'stages': stages})
`;
  const result = spawnSync(
    process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3'),
    ['-c', source, join(here, '..'), join(temporary, 'runs')],
    { encoding: 'utf-8', env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' } },
  );
  assert.equal(result.status, 0, result.stderr);
}
function timelineFixture(mode) {
  const source = `import sys
from pipeline_state import Store
store = Store(sys.argv[1])
count = 240 if sys.argv[2] == 'seed' else 3
for index in range(count):
    failure = index % 4 == 0
    detail = 'timeline-' + sys.argv[2] + '-' + str(index)
    if index == count - 1:
        detail += ' 完整事件详情' * 180
    store.mutate('demo-registration-1008', lambda state: None, actor='agent' if failure else 'monitor', event_type='action_failed' if failure else 'task_status', detail=detail)
`;
  const result = spawnSync(
    process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3'),
    ['-c', source, join(temporary, 'runs'), mode],
    { encoding: 'utf-8', cwd: join(here, '../..'), env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' } },
  );
  assert.equal(result.status, 0, result.stderr);
}
function registrationFixture(mode) {
  const source = `import sys
from pipeline_state import Store
store = Store(sys.argv[1])
if sys.argv[2] == 'seed':
    store.init('demo-registration-1007', {'name': 'registration-update', 'inputs': [{'source_type': 'obs', 'obs_path': 'obs://example/raw/'}], 'stages': [{'id': 'A'}]})
    store.mutate('demo-registration-1007', lambda state: state['stages']['upload'].update(status='SUCCEEDED'))
    store.init('demo-registration-1008', {'name': 'multi-registration', 'inputs': [{'id': key, 'source_type': 'obs', 'obs_path': 'obs://example/' + key + '/'} for key in ('left', 'right')], 'stages': [{'id': key, 'input_from': ['input:' + source]} for key, source in [('A', 'left'), ('B', 'right')]]})
    store.record_inputs('demo-registration-1008', {key: {'asset_id': 'asset-' + key, 'version_id': 'version-' + key, 'asset_name': 'data-' + key, 'obs_path': 'obs://example/' + key + '/'} for key in ('left', 'right')}, 1)
else:
    run = 'demo-registration-1007'
    store.record_inputs(run, {'default': {'asset_id': 'registered-browser-asset', 'version_id': 'registered-browser-version', 'asset_name': 'registered-browser-data', 'obs_path': 'obs://example/registered/'}}, store.read(run)['version'])
`;
  const result = spawnSync(
    process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3'),
    ['-c', source, join(temporary, 'runs'), mode],
    { encoding: 'utf-8', cwd: join(here, '../..'), env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' } },
  );
  assert.equal(result.status, 0, result.stderr);
}
try {
  console.log('Starting isolated demo service…');
  service = spawn(
    process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3'),
    [
      join(here, '../server.py'),
      '--demo',
      '--runs-root',
      join(temporary, 'runs'),
      '--port',
      '0',
      '--run',
      'demo-running-1001',
      '--idle-exit',
      '0',
    ],
    {
      stdio: ['ignore', 'pipe', 'pipe'],
      env: { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' },
    },
  );
  const url = await lineFrom(service, 'stdout', /(http:\/\/127\.0\.0\.1:[^\s]+)/);
  demoURL = new URL(url);
  seedMultiInputRun();
  console.log('Starting headless Chrome…');
  browser = spawn(
    chrome,
    [
      '--headless=new',
      '--remote-debugging-port=0',
      '--user-data-dir=' + join(temporary, 'chrome'),
      '--no-first-run',
      '--no-default-browser-check',
      '--disable-background-networking',
      '--disable-features=Translate,MediaRouter',
      '--disable-extensions',
      '--window-size=1512,920',
      'about:blank',
    ],
    { stdio: ['ignore', 'ignore', 'pipe'] },
  );
  const ws = await lineFrom(browser, 'stderr', /DevTools listening on (ws:\/\/[^\s]+)/);
  socket = new WebSocket(ws);
  await new Promise((resolve, reject) => {
    socket.onopen = resolve;
    socket.onerror = reject;
  });
  socket.onmessage = (event) => {
    const message = JSON.parse(event.data);
    if (message.id) {
      const task = pending.get(message.id);
      if (task) {
        clearTimeout(task.timer);
        pending.delete(message.id);
        message.error ? task.reject(Error(message.error.message)) : task.resolve(message.result);
      }
    } else if (message.method === 'Runtime.exceptionThrown') {
      errors.push(
        message.params.exceptionDetails.exception?.description ||
          message.params.exceptionDetails.text,
      );
    } else if (message.method === 'Log.entryAdded') {
      browserMessages.push(message.params.entry.text);
    } else if (message.method === 'Fetch.requestPaused') {
      const requestId = message.params.requestId;
      const task = failNextPreview
        ? send('Fetch.fulfillRequest', {
            requestId,
            responseCode: 502,
            responseHeaders: [{ name: 'Content-Type', value: 'application/json' }],
            body: Buffer.from(
              JSON.stringify({ error: 'Server error 500: Internal error' }),
            ).toString('base64'),
          })
        : send('Fetch.continueRequest', { requestId });
      failNextPreview = false;
      task.catch((error) => errors.push(error.message));
    } else if (message.method === 'Network.responseReceived') {
      const response = message.params.response;
      if (new URL(response.url).pathname.endsWith('.js')) {
        moduleResponses.set(response.url, response.status);
      }
    } else if (message.method === 'Network.requestWillBeSent') {
      const request = message.params.request;
      if (request.url.endsWith('/actions') && request.postData) {
        actionRequests.push(JSON.parse(request.postData));
      }
      if (message.params.request.url.includes('/api/')) {
        apiRequests++;
      }
      if (message.params.request.url.includes('/preview?')) {
        previewRequests++;
      }
      if (message.params.request.url.includes('/tasks/')) {
        taskRequests++;
      }
      if (message.params.request.url.includes('/resource-usage')) {
        resourceRequests++;
      }
    }
  };
  const { targetId } = await send('Target.createTarget', { url: 'about:blank' }, null);
  ({ sessionId: session } = await send('Target.attachToTarget', { targetId, flatten: true }, null));
  await send('Page.enable');
  await send('Runtime.enable');
  await send('Network.enable');
  await send('Log.enable');
  const downloads = join(output, 'downloads');
  mkdirSync(downloads, { recursive: true });
  await send('Browser.setDownloadBehavior', { behavior: 'allow', downloadPath: downloads }, null);
  await send('Emulation.setDeviceMetricsOverride', {
    width: 1512,
    height: 920,
    deviceScaleFactor: 1,
    mobile: false,
  });
  await send('Page.navigate', {
    url: pathToFileURL(join(here, '../static/index.html')).href,
  });
  await until(`!!document.querySelector('.startup-help')`, '直接打开 HTML 的启动提示');
  assert(await evaluate(`getComputedStyle(document.body).backgroundColor==='rgb(245, 245, 242)'`));
  assert(await evaluate(`document.querySelector('.brand svg').getBoundingClientRect().width<=24`));
  assert(await evaluate(`getComputedStyle(document.querySelector('.brand svg')).fill==='none'`));
  assert(await evaluate(`!document.body.innerText.includes('正在连接')`));
  assert(
    await evaluate(
      `document.querySelector('.startup-help').innerText.includes('server.py --demo --open')`,
    ),
  );
  assert.equal(apiRequests, 0);
  assert.equal(moduleResponses.size, 1);
  assert.deepEqual(browserMessages, []);
  await screenshot('desktop-file-startup');
  await send('Emulation.setDeviceMetricsOverride', {
    width: 390,
    height: 844,
    deviceScaleFactor: 1,
    mobile: false,
  });
  assert(await evaluate(`document.documentElement.scrollWidth<=window.innerWidth`));
  await screenshot('mobile-file-startup');
  await send('Emulation.setDeviceMetricsOverride', {
    width: 1512,
    height: 920,
    deviceScaleFactor: 1,
    mobile: false,
  });
  moduleResponses.clear();
  pass('直接打开 HTML 时样式和图标正常，提示启动服务，无模块或 API 请求');
  await send('Page.navigate', { url });
  await until(`document.querySelectorAll('.dag-node').length===7`, '运行图');
  assert(moduleResponses.size > 1);
  assert([...moduleResponses.values()].every((status) => status === 200));
  assert.equal(await evaluate(`location.search.includes('token=')`), false);
  pass('cookie 鉴权、令牌 URL 清理与原生模块加载');
  const requestsBeforeChecks = taskRequests;
  await click('.dag-node[data-key="plan"]');
  await until(`!!document.querySelector('.detail-list')`, '计划检查概览');
  assert(
    await evaluate(
      `[...document.querySelectorAll('#drawer dt')].every(e=>!['镜像','任务 ID','算子 ID','资源','平台状态'].includes(e.textContent))`,
    ),
  );
  assert(
    await evaluate(
      `!document.querySelector('#attempt-select')&&!document.querySelector('#drawer [data-action="retry"]')`,
    ),
  );
  await click('[data-tab="config"]');
  await until(`document.querySelectorAll('#drawer-body tbody tr').length===5`, '执行前检查清单');
  await screenshot('desktop-plan-checks');
  await click('[data-tab="logs"]');
  await until(
    `document.querySelector('#drawer-body').textContent.includes('计划确认不产生日志')`,
    '检查项日志说明',
  );
  await click('[data-tab="preview"]');
  await until(
    `document.querySelector('#drawer-body').textContent.includes('计划确认不产生数据输出')`,
    '检查项输出说明',
  );
  assert(
    !(await evaluate(`document.querySelector('#drawer').textContent.includes('任务尚未提交')`)),
  );
  assert.equal(taskRequests, requestsBeforeChecks);
  pass('计划确认展示检查清单，无任务字段或任务接口请求');
  await click('[data-action="drawer-close"]');
  await click('.dag-node[data-key="upload"]');
  await until(`!!document.querySelector('.detail-list')`, '上传注册说明');
  assert(
    await evaluate(
      `document.querySelector('#drawer-body').textContent.includes('输入数据已在 OBS，无需再次上传')`,
    ),
  );
  assert(!(await evaluate(`document.querySelector('#drawer [data-action="retry"]')`)));
  await click('[data-tab="config"]');
  await until(
    `document.querySelector('#drawer-body').textContent.includes('demo-raw')`,
    '注册资产与版本',
  );
  await click('[data-tab="logs"]');
  await until(
    `document.querySelector('#drawer-body').textContent.includes('上传注册没有作业日志')`,
    '注册日志说明',
  );
  await click('[data-tab="preview"]');
  await until(
    `document.querySelector('#drawer-body').textContent.includes('obs://demo-bucket/raw/')`,
    '资产登记结果',
  );
  assert.equal(taskRequests, requestsBeforeChecks);
  pass('OBS 输入说明仅注册，登记信息与非任务页签正确');
  await click('[data-action="drawer-close"]');
  await click('.dag-node[data-key="cleaning"]');
  await until(`!!document.querySelector('.detail-list')`, '步骤抽屉');
  await screenshot('desktop-overview');
  await click('[data-tab="config"]');
  await until(`!!document.querySelector('#config-tables')`, '任务配置');
  assert(
    await evaluate(
      `document.querySelector('#config-tables').textContent.includes('dataset_configs')`,
    ),
  );
  pass('DAG、历史尝试与结构化配置');
  await click('#raw-config');
  assert.equal(await evaluate(`document.querySelector('#config-raw').hidden`), false);
  assert(
    await evaluate(
      `JSON.parse(document.querySelector('#config-raw').textContent).algo_id==='demo-algo-old'`,
    ),
  );
  await click('#raw-config');
  pass('配置原始 JSON 与表格切换');
  await click('[data-tab="logs"]');
  await until(`document.querySelectorAll('.log-line').length>5`, '日志');
  assert.equal(await evaluate(`document.querySelector('#log-auto').checked`), false);
  assert(
    await evaluate(`document.querySelector('#log-auto').parentElement.textContent.includes('60s')`),
  );
  const logsBeforeManualRefresh = await evaluate(
    `performance.getEntriesByType('resource').filter(e=>e.name.includes('/logs/content?')).length`,
  );
  await click('[data-action="log-refresh"]');
  await until(
    `performance.getEntriesByType('resource').filter(e=>e.name.includes('/logs/content?')).length>${logsBeforeManualRefresh}`,
    '手动获取最新日志',
  );
  await evaluate(
    `{const e=document.querySelector('#log-search');e.value='WARN';e.dispatchEvent(new Event('input',{bubbles:true}));}`,
  );
  assert.equal(await evaluate(`document.querySelectorAll('.log-line').length`), 1);
  pass('日志默认手动刷新、可选 60s 自动刷新与搜索');
  const cachedLogRequests = taskRequests;
  await click('[data-tab="preview"]');
  await until(
    `document.querySelector('#drawer-body').textContent.includes('任务成功后可预览')`,
    '运行中输出说明',
  );
  await click('[data-tab="logs"]');
  await until(`!!document.querySelector('#log-search')`, '恢复已加载日志');
  assert.equal(await evaluate(`document.querySelector('#log-search').value`), 'WARN');
  assert.equal(await evaluate(`document.querySelectorAll('.log-line').length`), 1);
  assert.equal(taskRequests, cachedLogRequests);
  pass('运行中页签复用任务详情与日志，保留搜索且不重复请求');
  await click('[data-tab="overview"]');
  await until(`!!document.querySelector('.detail-list')`, '任务概览');
  assert(await evaluate(`document.querySelector('[data-tab="resources"]')===null`));
  assert(
    await evaluate(
      `document.querySelector('#drawer-body').textContent.includes('CloudRobo Console')`,
    ),
  );
  assert.equal(resourceRequests, 0);
  const windowsCommand = await evaluate(`(async()=>{
    const original = navigator.platform;
    Object.defineProperty(navigator, 'platform', {value:'Win32', configurable:true});
    try {
      return (await import('/common.js')).cliCommand(['cloudrobo','--task-config',JSON.stringify({name:"中文 O'Reilly",inputs:'[{"name":"数据"}]'})]);
    } finally {
      Object.defineProperty(navigator, 'platform', {value:original, configurable:true});
    }
  })()`);
  const payload = JSON.parse(windowsCommand.split('\n')[3]);
  assert.equal(JSON.parse(payload[2]).name, "中文 O'Reilly");
  assert(windowsCommand.includes('json.load(sys.stdin)'));
  assert(windowsCommand.includes("$env:PYTHONIOENCODING = 'utf-8'"));
  pass('Windows 复制 CLI 使用 PowerShell 与 JSON argv，保留嵌套引号和中文');
  pass('无资源监控页签，资源详情引导至 CloudRobo Console');
  await evaluate(
    `{const e=document.querySelector('#attempt-select');e.value='demo-clean-1';e.dispatchEvent(new Event('change',{bubbles:true}));}`,
  );
  await click('[data-tab="overview"]');
  await until(`!!document.querySelector('.detail-list')`, '历史概览');
  assert(
    await evaluate(`document.querySelector('#drawer').textContent.includes('历史尝试只供查看')`),
  );
  assert(
    !(await evaluate(
      `document.querySelector('#drawer-body').textContent.includes('计划数据来源')`,
    )),
  );
  pass('历史尝试不可修改');
  await click('[data-tab="logs"]');
  await until(`!!document.querySelector('#log-search')`, '历史日志');
  await evaluate(
    `{const e=document.querySelector('#log-search');e.value='';e.dispatchEvent(new Event('input',{bubbles:true}));}`,
  );
  await until(`document.querySelectorAll('.log-line.error').length===1`, '失败日志错误行');
  await click('#log-errors');
  assert.equal(await evaluate(`document.querySelectorAll('.log-line').length`), 1);
  await click('[data-action="error-next"]');
  assert(await evaluate(`document.querySelector('#toast').textContent.includes('1 / 1')`));
  pass('历史失败日志错误过滤与定位');
  await evaluate(
    `{const e=document.querySelector('#log-kind');e.value='system';e.dispatchEvent(new Event('change',{bubbles:true}));}`,
  );
  await until(
    `document.querySelector('#log-file')?.textContent.includes('system.log')`,
    '系统日志切换',
  );
  await click('[data-action="log-full"]');
  await until(
    `document.querySelector('.log-caption')?.textContent.startsWith('完整日志')`,
    '完整日志',
  );
  await click('[data-action="log-download"]');
  for (let i = 0; i < 100 && !existsSync(join(downloads, 'task.log')); i++) {
    await sleep(100);
  }
  assert(existsSync(join(downloads, 'task.log')));
  assert(readFileSync(join(downloads, 'task.log'), 'utf8').includes('Killed'));
  pass('系统日志、完整日志与文件下载');
  await click('[data-action="drawer-close"]');
  await click('.dag-node[data-key="convert-lerobotv3"]');
  await until(`!!document.querySelector('.detail-list')`, '转换详情');
  await click('[data-tab="preview"]');
  await until(`document.querySelectorAll('.file-row').length===5`, '第一层目录和文件');
  assert.deepEqual(
    await evaluate(`[...document.querySelectorAll('#output-tree code')].map(e=>e.textContent)`),
    ['data/', 'meta/', 'robot/', 'videos/', 'manifest.yaml'],
  );
  assert.equal(await evaluate(`document.querySelectorAll('[data-action="frame-dir"]').length`), 0);
  assert.equal(await evaluate(`document.querySelectorAll('.tree-children').length`), 0);
  assert.equal(
    await evaluate(`document.querySelectorAll('[data-action="frame-preview"]').length`),
    1,
  );
  const firstLevelRequests = taskRequests;
  await sleep(1000);
  assert.equal(taskRequests, firstLevelRequests);
  assert.equal(
    await evaluate(
      `performance.getEntriesByType('resource').filter(e=>e.name.includes('/frames?prefix=')).length`,
    ),
    0,
  );
  pass('输出只列第一层文件夹和文件，保留独立目录列表，不展开或查询子目录');
  await click('[data-action="frame-preview"][data-file$="/manifest.yaml"]');
  await until(
    `document.querySelector('#preview-result')?.textContent.includes('manifest.yaml')`,
    '输出内容预览',
  );
  await until(`document.querySelector('#toast').hidden`, '临时提示消失');
  await screenshot('desktop-preview');
  pass('proc 第一层文件可预览，文件夹没有预览或展开操作');
  await click('[data-tab="logs"]');
  await until(`document.querySelectorAll('.log-line').length>5`, '转换日志');
  await evaluate(`document.querySelector('.log-box').scrollTop=120`);
  const retainedScroll = await evaluate(`document.querySelector('.log-box').scrollTop`);
  const retainedTaskRequests = taskRequests;
  await click('[data-tab="preview"]');
  await until(`!!document.querySelector('#output-tree')`, '恢复输出目录');
  assert.deepEqual(
    await evaluate(`[...document.querySelectorAll('#output-tree code')].map(e=>e.textContent)`),
    ['data/', 'meta/', 'robot/', 'videos/', 'manifest.yaml'],
  );
  assert(
    await evaluate(
      `document.querySelector('#preview-result').textContent.includes('manifest.yaml')`,
    ),
  );
  await click('[data-tab="logs"]');
  assert.equal(await evaluate(`document.querySelector('.log-box').scrollTop`), retainedScroll);
  assert.equal(taskRequests, retainedTaskRequests);
  pass('日志与输出切换无重复接口请求，保留第一层列表、预览和日志滚动位置');
  await click('[data-tab="preview"]');
  const framesBeforeRefresh = await evaluate(
    `performance.getEntriesByType('resource').filter(e=>e.name.endsWith('/frames')).length`,
  );
  await click('[data-action="frames-refresh"]');
  await until(
    `performance.getEntriesByType('resource').filter(e=>e.name.endsWith('/frames')).length>${framesBeforeRefresh}`,
    '刷新输出目录',
  );
  await until(`document.querySelectorAll('.file-row').length===5`, '重建第一层目录');
  assert.equal(await evaluate(`document.querySelector('#preview-result').textContent`), '');
  pass('手动刷新只重查根目录并替换第一层列表和预览结果');
  await click('[data-tab="config"]');
  await until(`!!document.querySelector('#raw-config')`, '键盘导航配置');
  await evaluate(
    `document.querySelector('[data-tab="config"]').dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}))`,
  );
  await until(`!!document.querySelector('#log-kind')`, '键盘切换页签');
  await evaluate(
    `document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))`,
  );
  assert.equal(await evaluate(`document.querySelector('#drawer').hidden`), true);
  pass('页签键盘导航与 Escape 关闭');
  await click('[data-action="runs"]');
  await until(`document.querySelectorAll('.run-table tbody tr').length===6`, '运行列表');
  await screenshot('desktop-runs');
  assert(
    await evaluate(
      `document.querySelector('[data-action="delete-run"][data-run="demo-running-1001"]').disabled`,
    ),
  );
  assert(
    await evaluate(
      `document.querySelector('[data-action="delete-run"][data-run="demo-awaiting-1002"]').disabled`,
    ),
  );
  await click('[data-action="delete-run"][data-run="demo-completed-1003"]');
  await until(`!!document.querySelector('#action-confirm')`, '删除本地记录确认');
  assert(await evaluate(`document.querySelector('#action-submit').disabled`));
  assert(
    await evaluate(`document.querySelector('#dialog-body').textContent.includes('无法从本地恢复')`),
  );
  assert(
    await evaluate(
      `document.querySelector('#dialog-body').textContent.includes('不会停止或删除云端任务')`,
    ),
  );
  await screenshot('desktop-delete-confirm');
  await click('#action-dialog .dialog-footer [data-action="dialog-close"]');
  assert(existsSync(join(temporary, 'runs/demo-completed-1003/state.json')));
  assert.equal(await evaluate(`document.querySelectorAll('.run-table tbody tr').length`), 6);
  pass('本地删除有明确确认和取消，运行中/等待处理记录禁用，取消保留全部记录');

  await click('[data-action="open-run"][data-run="demo-awaiting-1002"]');
  await until(`!!document.querySelector('.dag-node.AWAITING_DECISION')`, '待处理运行');
  await click('.dag-node[data-key="cleaning"]');
  await until(`!!document.querySelector('[data-action="retry"]:not(:disabled)')`, '可重试任务');
  assert.equal(
    await evaluate(`document.querySelector('#drawer [data-action="skip"]')===null`),
    true,
  );
  await click('[data-action="retry"]');
  await until(`!!document.querySelector('#action-confirm')`, '最新算子配置');
  const generatedOutputName = await evaluate(`document.querySelector('#retry-output').value`);
  assert(generatedOutputName.length <= 64);
  assert(generatedOutputName.startsWith('sim-teleop-cleaning-cleaning-'));
  assert.match(generatedOutputName, /^.+-\d{10}(?:-\d+)?$/);
  assert.notEqual(generatedOutputName, 'sim-teleop-cleaned');
  assert((await evaluate(`document.querySelector('#retry-name').value`)).length <= 64);
  pass('重试输出名保留管线和步骤前缀，秒级时间戳与重名序号计入完整 64 字符限制');

  assert.equal(await evaluate(`document.querySelector('#retry-pool').value`), 'PUBLIC_POOL');
  assert(await evaluate(`['#retry-resource','#retry-pool-name'].every(s=>{const e=document.querySelector(s);return !e.checkVisibility()&&e.disabled&&!e.required;})`));
  await evaluate(`{const e=document.querySelector('#retry-pool');e.value='DEDICATED_POOL';e.dispatchEvent(new Event('change',{bubbles:true}));}`);
  assert(await evaluate(`['#retry-resource','#retry-pool-name'].every(s=>{const e=document.querySelector(s);return e.checkVisibility()&&!e.disabled&&e.required;})`));
  assert(await evaluate(`document.querySelector('#retry-pool-help').textContent.includes('同一个专属池')`));
  await screenshot('desktop-retry-dedicated-pool');
  await click('#action-confirm');
  const submissionsBeforePoolValidation = actionRequests.length;
  await click('#action-submit');
  await sleep(100);
  assert.equal(actionRequests.length, submissionsBeforePoolValidation);
  assert(await evaluate(`document.querySelector('#retry-resource').validity.valueMissing`));
  await evaluate(`{document.querySelector('#retry-resource').value='unused-demo-pool';document.querySelector('#retry-pool-name').value='unused-demo-name';const e=document.querySelector('#retry-pool');e.value='PUBLIC_POOL';e.dispatchEvent(new Event('change',{bubbles:true}));}`);
  assert(await evaluate(`document.querySelector('#retry-resource').disabled&&!document.querySelector('#retry-resource').checkVisibility()`));
  await click('#action-confirm');
  pass('公共池隐藏且禁用专属池字段；专属池按需必填，缺失时不发出创建请求');

  assert(await evaluate(`document.querySelector('#action-submit').disabled`));
  await screenshot('desktop-retry');
  await evaluate(
    `{document.querySelector('#retry-worker').value='{"cpu":-1,"memory":16,"gpu":0,"npu":0}';document.querySelector('#action-confirm').click();}`,
  );
  await click('#action-submit');
  await until(
    `document.querySelector('#action-error')?.textContent.includes('worker_spec')`,
    '规格校验错误',
  );
  assert(await evaluate(`document.querySelector('#action-dialog').open`));
  assert(
    await evaluate(
      `(()=>{const error=document.querySelector('#action-error').getBoundingClientRect();const body=document.querySelector('#dialog-body').getBoundingClientRect();return error.top>=body.top&&error.bottom<=body.bottom;})()`,
    ),
  );
  assert(
    await evaluate(
      `document.querySelector('#attempt-select').textContent.includes('demo-clean-1')`,
    ),
  );
  await screenshot('desktop-retry-error');
  pass('非法规格被拒绝、保留对话框并支持修正');
  await evaluate(
    `document.querySelector('#retry-worker').value='{"cpu":4,"memory":16,"gpu":0,"npu":0}'`,
  );
  await click('#action-submit');
  await until(`!document.querySelector('#action-dialog').open`, '重试提交');
  assert(
    await evaluate(
      `document.querySelector('#attempt-select').textContent.includes('demo-retry-1')`,
    ),
  );
  pass('重新查询算子、显式确认、新建任务与历史保留');
  const publicRetry = actionRequests.filter((body) => body.type === 'retry').at(-1);
  assert.equal(publicRetry.overrides.resource_pool_type, 'PUBLIC_POOL');
  assert.equal(Object.hasOwn(publicRetry.overrides, 'resource_id'), false);
  assert.equal(Object.hasOwn(publicRetry.overrides, 'dedicated_pool_name'), false);
  const publicTask = JSON.parse(readFileSync(join(temporary, 'runs/demo-awaiting-1002/tasks/demo-retry-1.json'), 'utf-8'));
  assert.equal(Object.hasOwn(publicTask.task_config, 'resource_id'), false);
  assert.equal(Object.hasOwn(publicTask.task_config, 'dedicated_pool_name'), false);
  pass('专属池切回公共池后，请求和最终任务配置都不携带专属池字段');
  await click('[data-action="drawer-close"]');
  await click('[data-filter="actions"]');
  await until(`document.querySelectorAll('.event').length>0`, '操作时间线');
  assert(
    await evaluate(
      `[...document.querySelectorAll('.event-actor')].every(e=>e.textContent!=='monitor')`,
    ),
  );
  await click('[data-filter="failures"]');
  await until(`document.querySelector('#timeline').textContent.includes('FAILED')`, '失败时间线');
  await click('[data-filter="all"]');
  pass('操作和失败事件筛选');
  await click('.dag-node[data-key="evaluation/quality-eval"]');
  await until(`!!document.querySelector('[data-action="skip"]')`, '建议性操作');
  await verifySkipHint('skip', '跳过', '建议性评测');
  assert(await evaluate(`document.querySelector('#skip-hint').textContent.includes('之后可补跑')`));
  await screenshot('desktop-eval-skip-hint');
  await click('[data-action="skip"]');
  await click('#action-confirm');
  await click('#action-submit');
  await until(`!document.querySelector('#action-dialog').open`, '跳过提交');
  pass('建议性步骤直接跳过，已提交的阻断任务不可跳过');
  await click('[data-action="drawer-close"]');
  await click('.run-actions [data-action="terminate"]');
  await until(`!!document.querySelector('#terminate-code')`, '终止确认');
  assert(await evaluate(`document.querySelector('#action-submit').disabled`));
  await evaluate(
    `{const e=document.querySelector('#terminate-code');e.value='0000';e.dispatchEvent(new Event('input',{bubbles:true}));}`,
  );
  assert(await evaluate(`document.querySelector('#action-submit').disabled`));
  await evaluate(
    `{const e=document.querySelector('#terminate-code');e.value='1002';e.dispatchEvent(new Event('input',{bubbles:true}));}`,
  );
  await click('#action-submit');
  await until(`document.querySelector('.run-title').textContent.includes('已终止')`, '终止状态');
  pass('终止确认与后续编排停止');
  await click('[data-action="runs"]');
  await until(`!!document.querySelector('.run-table')`, '返回列表');
  await click('[data-run="demo-completed-1003"]');
  await until(`!!document.querySelector('[data-action="view-summary"]')`, '完成视图');
  await click('[data-action="view-summary"]');
  await until(`!!document.querySelector('.artifact-path')`, '摘要');
  assert(
    await evaluate(
      `document.querySelector('.artifact-path').textContent.includes('training-ready')`,
    ),
  );
  await screenshot('desktop-summary');
  const requestsBeforeArtifacts = taskRequests;
  assert(
    !(await evaluate(`document.querySelector('.warning-list').textContent.includes('上传注册')`)),
  );
  await click('.summary [data-action="stage"][data-key="upload"]');
  await until(`!!document.querySelector('#drawer .status.SKIPPED')`, '已有资产跳过上传注册');
  assert(
    await evaluate(`document.querySelector('#drawer-body').textContent.includes('无需上传或注册')`),
  );
  await screenshot('desktop-upload-skipped');
  await click('[data-tab="config"]');
  await until(
    `document.querySelector('#drawer-body').textContent.includes('demo-raw')`,
    '复用资产信息',
  );
  await click('[data-tab="logs"]');
  await until(
    `document.querySelector('#drawer-body').textContent.includes('本次已跳过上传注册')`,
    '跳过注册日志说明',
  );
  await click('[data-tab="preview"]');
  await until(
    `document.querySelector('#drawer-body').textContent.includes('复用已有数据资产')`,
    '已有数据说明',
  );
  assert(
    !(await evaluate(`document.querySelector('#drawer').textContent.includes('任务尚未提交')`)),
  );
  await click('[data-action="drawer-close"]');
  await click('.summary [data-action="stage"][data-key="output"]');
  await until(`!!document.querySelector('.detail-list')`, '最终产物核对');
  await click('[data-tab="config"]');
  await until(
    `document.querySelector('#drawer-body').textContent.includes('training-ready')`,
    '产物信息',
  );
  await click('[data-tab="logs"]');
  await until(
    `document.querySelector('#drawer-body').textContent.includes('产物核对不产生作业日志')`,
    '产物日志说明',
  );
  await click('[data-tab="preview"]');
  await until(
    `document.querySelector('#drawer-body').textContent.includes('obs://demo-bucket/training-ready/')`,
    '最终产物路径',
  );
  assert.equal(taskRequests, requestsBeforeArtifacts);
  await click('[data-action="drawer-close"]');
  pass('已有资产自动跳过注册且无误报告警，产物核对无任务请求');
  assert.equal(await evaluate(`document.querySelector('#summary h2').textContent`), '管线产物');
  await click('[data-action="open-report"]');
  await until(`!!document.querySelector('[data-action="report-preview"]')`, '评测报告');
  await send('Fetch.enable', { patterns: [{ urlPattern: '*/api/runs/*/tasks/*/preview?*' }] });
  failNextPreview = true;
  const beforeFailure = previewRequests;
  await click('[data-action="report-preview"]');
  await until(
    `document.querySelector('#preview-result [role="alert"]')?.textContent.includes('Server error 500')`,
    '报告读取失败提示',
  );
  await sleep(1500);
  assert.equal(previewRequests, beforeFailure + 1);
  assert(
    await evaluate(
      `document.querySelector('#preview-result').textContent.includes('手动重试一次')`,
    ),
  );
  assert.equal(await evaluate(`document.querySelector('#attempt-select').value`), 'demo-quality');
  assert(await evaluate(`!!document.querySelector('.run-title .SUCCEEDED_WITH_WARNINGS')`));
  await screenshot('desktop-preview-read-failure');
  await send('Fetch.disable');
  const requestsBefore = previewRequests;
  await click('[data-action="report-preview"]');
  await until(
    `document.querySelector('#preview-result').textContent.includes('本地演示预览')`,
    '报告内容',
  );
  assert.equal(await evaluate(`document.querySelector('[data-tab="resources"]')===null`), true);
  pass('报告读取5xx保留任务状态且不自动重试，手动重新获取成功');
  pass('完成摘要、报告获取与 eval 页签限制');
  await click('[data-action="report-download"]');
  for (let i = 0; i < 50 && previewRequests < requestsBefore + 2; i++) {
    await sleep(100);
  }
  assert(previewRequests >= requestsBefore + 2);
  pass('报告预览和下载均发起新的平台请求');
  await click('[data-action="drawer-close"]');
  await click('.summary [data-action="stage"][data-key="evaluation/diversity-eval"]');
  await until(`!!document.querySelector('[data-action="retry"]:not(:disabled)')`, '评测重试入口');
  await click('[data-action="retry"]');
  await until(`!!document.querySelector('#retry-name')`, '评测重试配置');
  assert.equal(await evaluate(`document.querySelector('#retry-output')===null`), true);
  assert.equal(await evaluate(`document.querySelector('#retry-head')===null`), true);
  assert.equal(await evaluate(`document.querySelector('#retry-pool').value`), 'DEDICATED_POOL');
  assert.equal(await evaluate(`document.querySelector('#retry-resource').value`), 'existing-demo-id');
  assert.equal(await evaluate(`document.querySelector('#retry-pool-name').value`), 'existing-demo-pool');
  assert(await evaluate(`document.querySelector('#retry-resource').checkVisibility()&&document.querySelector('#retry-resource').required`));
  await evaluate(`{const e=document.querySelector('#retry-pool');e.value='PUBLIC_POOL';e.dispatchEvent(new Event('change',{bubbles:true}));}`);
  assert(await evaluate(`document.querySelector('#retry-resource').disabled&&!document.querySelector('#retry-resource').checkVisibility()`));
  await evaluate(`{const e=document.querySelector('#retry-pool');e.value='DEDICATED_POOL';e.dispatchEvent(new Event('change',{bubbles:true}));}`);
  assert.equal(await evaluate(`document.querySelector('#retry-resource').value`), 'existing-demo-id');
  assert.equal(await evaluate(`document.querySelector('#retry-pool-name').value`), 'existing-demo-pool');
  pass('原专属池配置正确回填，切换公共池再切回仍保留原值');
  await evaluate(`{const e=document.querySelector('#retry-pool');e.value='DEDICATED_POOL';e.dispatchEvent(new Event('change',{bubbles:true}));document.querySelector('#retry-resource').value='demo-eval-pool-id';document.querySelector('#retry-pool-name').value='demo-eval-pool';}`);
  assert(
    await evaluate(
      `document.querySelector('#dialog-body').textContent.includes('评测输入数据集（只读）')`,
    ),
  );
  await click('#action-confirm');
  await click('#action-submit');
  await until(`!document.querySelector('#action-dialog').open`, '评测新任务提交');
  const dedicatedRetry = actionRequests.filter((body) => body.type === 'retry').at(-1);
  assert.equal(dedicatedRetry.overrides.resource_pool_type, 'DEDICATED_POOL');
  assert.equal(dedicatedRetry.overrides.resource_id, 'demo-eval-pool-id');
  assert.equal(dedicatedRetry.overrides.dedicated_pool_name, 'demo-eval-pool');
  assert(
    await evaluate(
      `document.querySelector('#attempt-select').textContent.includes('demo-diversity')`,
    ),
  );
  await screenshot('desktop-eval-retry');
  pass('评测重试保留原数据集，不显示或提交处理输出名及 Head 配置');

  await click('[data-action="drawer-close"]');
  await click('[data-action="runs"]');
  await until(`!!document.querySelector('[data-run="demo-multi-1004"]')`, '多输入运行');
  await click('[data-run="demo-multi-1004"]');
  await until(`document.querySelectorAll('.dag-node').length===6`, '分支汇合图');
  await click('.dag-node[data-key="C"]');
  await until(`!!document.querySelector('.detail-list')`, '多输入概览');
  assert(
    await evaluate(`document.querySelector('#drawer-body').textContent.includes('1. B\\n2. A')`),
  );
  assert(await evaluate(`document.querySelector('#drawer-body').textContent.includes('A、B')`));
  await click('[data-tab="config"]');
  await until(
    `document.querySelectorAll('.json-array tbody tr').length===2`,
    '两项 dataset_configs',
  );
  assert(
    await evaluate(
      `document.querySelector('.json-array tbody tr:first-child').textContent.includes('data-B')`,
    ),
  );
  assert(
    await evaluate(
      `document.querySelector('.json-array tbody tr:last-child').textContent.includes('data-A')`,
    ),
  );
  await screenshot('desktop-multi-input');
  pass('多输入分支汇合、等待与数据来源分别展示，实际配置保持输入顺序');
  await click('[data-action="drawer-close"]');
  await click('[data-action="runs"]');
  await until(`!!document.querySelector('[data-run="demo-bypass-1005"]')`, '可申请跳过运行');
  await click('[data-run="demo-bypass-1005"]');
  await until(`document.querySelectorAll('.dag-node').length===5`, '未提交处理步骤');
  await click('.dag-node[data-key="clean"]');
  await until(
    `!!document.querySelector('[data-action="request-skip"]:not(:disabled)')`,
    '处理步骤跳过入口',
  );
  await verifySkipHint('request-skip', '跳过', '兼容性');
  await click('[data-action="request-skip"]');
  await until(`!!document.querySelector('#action-confirm')`, '原输入和兼容性说明');
  assert(
    await evaluate(
      `document.querySelector('#dialog-body').textContent.includes('未确认兼容前保持阻断')`,
    ),
  );
  await evaluate(`document.querySelector('#action-confirm').click()`);
  await click('#action-submit');
  await until(`!!document.querySelector('[data-action="cancel-skip"]')`, '跳过请求待核实');
  await verifySkipHint('cancel-skip', '取消跳过请求', '保留原处理步骤');
  assert(await evaluate(`!!document.querySelector('.dag-node[data-key="eval"].IDLE')`));
  await screenshot('desktop-processing-skip-request');
  await click('[data-action="cancel-skip"]');
  await until(`!!document.querySelector('#action-confirm')`, '取消请求');
  await evaluate(`document.querySelector('#action-confirm').click()`);
  await click('#action-submit');
  await until(
    `!!document.querySelector('[data-action="request-skip"]:not(:disabled)')`,
    '保留原步骤',
  );
  await click('[data-action="request-skip"]');
  await until(`!!document.querySelector('#action-confirm')`, '重新申请');
  await evaluate(`document.querySelector('#action-confirm').click()`);
  await click('#action-submit');
  await until(`!!document.querySelector('[data-action="cancel-skip"]')`, '申请已登记');
  const skipState = JSON.parse(
    readFileSync(join(temporary, 'runs/demo-bypass-1005/state.json'), 'utf-8'),
  );
  const resolvedSkip = spawnSync(
    process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3'),
    [
      join(here, '../../pipeline_state.py'),
      '--runs-root',
      join(temporary, 'runs'),
      '--run',
      'demo-bypass-1005',
      'resolve-skip',
      '--stage',
      'clean',
      '--expect-version',
      String(skipState.version),
      '--decision',
      'skip',
      '--compatibility-note',
      'Offline fixture: original LeRobot dataset accepted by downstream evaluation',
    ],
    { encoding: 'utf-8', env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' } },
  );
  assert.equal(resolvedSkip.status, 0, resolvedSkip.stderr);
  await click('[data-action="refresh"]');
  await until(
    `!!document.querySelector('.dag-node[data-key="clean"].SKIPPED')`,
    '校验后沿用原输入',
  );
  await until(
    `document.querySelector('#drawer-body').textContent.includes('不产生新数据版本')`,
    '跳过实际语义',
  );
  assert(await evaluate(`!!document.querySelector('.dag-node[data-key="eval"].READY')`));
  await screenshot('desktop-processing-bypassed');
  const finishFixture = `import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from pipeline_state import Store
store = Store(sys.argv[2])
def complete(state):
    state['stages']['eval']['status'] = 'SUCCEEDED'
    state['stages']['output']['status'] = 'SUCCEEDED'
    state['output'].update({key: state['stages']['clean'][key] for key in ('target_path', 'target_asset_id', 'target_version_id')})
store.mutate('demo-bypass-1005', complete)
`;
  const complete = spawnSync(
    process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3'),
    ['-c', finishFixture, join(here, '../..'), join(temporary, 'runs')],
    { encoding: 'utf-8', env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' } },
  );
  assert.equal(complete.status, 0, complete.stderr);
  const finish = spawnSync(
    process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3'),
    [
      join(here, '../../pipeline_state.py'),
      '--runs-root',
      join(temporary, 'runs'),
      '--run',
      'demo-bypass-1005',
      'finish',
    ],
    { encoding: 'utf-8', env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' } },
  );
  assert.equal(finish.status, 0, finish.stderr);
  await click('[data-action="drawer-close"]');
  await click('[data-action="refresh"]');
  await until(`!!document.querySelector('[data-action="view-summary"]')`, '跳过处理完成摘要');
  await click('[data-action="view-summary"]');
  await until(
    `document.querySelector('.warning-list')?.textContent.includes('沿用原输入')`,
    '摘要准确区分处理跳过',
  );
  assert(
    !(await evaluate(`document.querySelector('.warning-list').textContent.includes('尚未评测')`)),
  );
  await screenshot('desktop-processing-bypass-summary');
  pass('未提交处理步骤可申请/取消跳过，校验前不放行，校验后沿用原版本并正确汇总');
  await click('[data-action="drawer-close"]');
  await click('[data-action="runs"]');
  await until(`!!document.querySelector('[data-run="demo-required-1006"]')`, '必要转换运行');
  await click('[data-run="demo-required-1006"]');
  await until(`!!document.querySelector('.dag-node[data-key="convert"]')`, '必要转换节点');
  await click('.dag-node[data-key="convert"]');
  await until(
    `!!document.querySelector('[data-action="request-skip"]:disabled')`,
    '禁止不兼容的跳过',
  );
  await verifySkipHint('request-skip', '跳过', '不能跳过必要转换');
  assert(await evaluate(`(()=>{const e=document.querySelector('[data-action="request-skip"]');const wrapper=e.closest('.action-with-hint');wrapper.focus();return wrapper.title.length>0&&document.activeElement===wrapper&&getComputedStyle(e).pointerEvents==='none';})()`));
  assert(
    await evaluate(
      `document.querySelector('#drawer-body').textContent.includes('不能跳过必要转换')`,
    ),
  );
  await screenshot('desktop-required-conversion');
  pass('原始 H5 到 LeRobot 清洗的必要转换显示禁用跳过和具体不兼容原因');
  await click('[data-action="drawer-close"]');
  await click('[data-action="runs"]');
  await until(`!!document.querySelector('#run-search')`, '搜索');
  await evaluate(
    `{const e=document.querySelector('#run-search');e.value='completed';e.dispatchEvent(new Event('input',{bubbles:true}));}`,
  );
  assert.equal(await evaluate(`document.querySelectorAll('.run-table tbody tr').length`), 1);
  pass('运行列表筛选');
  await evaluate(
    `{const e=document.querySelector('#run-search');e.value='';e.dispatchEvent(new Event('input',{bubbles:true}));const s=document.querySelector('#run-status');s.value='completed';s.dispatchEvent(new Event('change',{bubbles:true}));}`,
  );
  assert.equal(await evaluate(`document.querySelectorAll('.run-table tbody tr').length`), 2);
  pass('运行列表状态筛选');
  await click('[data-run="demo-completed-1003"]');
  await until(`document.querySelectorAll('.dag-node').length===7`, '移动视图');
  for (const width of [2560, 1920, 1280, 768, 390]) {
    await send('Emulation.setDeviceMetricsOverride', {
      width,
      height: 844,
      deviceScaleFactor: 1,
      mobile: false,
    });
    await until(
      `Math.abs(document.querySelector('#dag').parentElement.getBoundingClientRect().width-document.documentElement.clientWidth)<2`,
      '流程图容器适应视口',
    );
    if (width >= 1920) {
      await until(
        `document.querySelector('#dag').getBoundingClientRect().width>window.innerWidth*0.75`,
        '大屏流程图利用率',
      );
      assert(
        await evaluate(
          `parseFloat(getComputedStyle(document.querySelector('.node-name')).fontSize)>=16`,
        ),
      );
      assert(await evaluate(`parseFloat(getComputedStyle(document.body).fontSize)>=16`));
      await screenshot('wide-flow-' + width);
    }
    await click('.dag-node[data-key="cleaning"]');
    await until(`!!document.querySelector('.detail-list')`, '响应式抽屉');
    await screenshot('viewport-' + width);
    assert(await evaluate(`document.documentElement.scrollWidth<=window.innerWidth`));
    assert(await evaluate(`document.scrollingElement.scrollHeight<=window.innerHeight+1`));
    await click('[data-action="drawer-close"]');
    assert(await evaluate(`document.documentElement.scrollWidth<=window.innerWidth`));
  }
  pass('2560 / 1920 / 1512 / 1280 / 768 / 390 布局、大屏流程图宽度与字号检查');
  await send('Emulation.setDeviceMetricsOverride', {
    width: 1512,
    height: 920,
    deviceScaleFactor: 1,
    mobile: false,
  });
  await click('[data-action="runs"]');
  await until(`!!document.querySelector('#run-status')`, '删除前运行列表');
  await evaluate(
    `{const s=document.querySelector('#run-status');s.value='';s.dispatchEvent(new Event('change',{bubbles:true}));}`,
  );
  await click('[data-action="delete-run"][data-run="demo-awaiting-1002"]');
  await until(`!!document.querySelector('#action-confirm')`, '删除已终止记录');
  await evaluate(`document.querySelector('#action-confirm').click()`);
  await click('#action-submit');
  await until(
    `!!document.querySelector('#run-search') && !document.querySelector('[data-run="demo-awaiting-1002"]')`,
    '终止记录已从列表删除',
  );
  assert(!existsSync(join(temporary, 'runs/demo-awaiting-1002')));
  assert(existsSync(join(temporary, 'runs/demo-running-1001/state.json')));
  pass('已终止运行可删除，物理目录和历史随记录移除，其他运行保留');

  await click('[data-action="open-run"][data-run="demo-completed-1003"]');
  await until(
    `!!document.querySelector('.run-actions [data-action="delete-run"]:not(:disabled)')`,
    '详情删除入口',
  );
  await click('.run-actions [data-action="delete-run"]');
  await until(`!!document.querySelector('#action-confirm')`, '完成记录删除确认');
  const changedBeforeDelete = spawnSync(
    process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3'),
    [
      join(here, '../../pipeline_state.py'),
      '--runs-root',
      join(temporary, 'runs'),
      '--run',
      'demo-completed-1003',
      'heartbeat',
    ],
    { encoding: 'utf-8', env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' } },
  );
  assert.equal(changedBeforeDelete.status, 0, changedBeforeDelete.stderr);
  await evaluate(`document.querySelector('#action-confirm').click()`);
  await click('#action-submit');
  await until(
    `document.querySelector('#action-error')?.textContent.includes('状态已变化')`,
    '删除版本冲突',
  );
  assert(existsSync(join(temporary, 'runs/demo-completed-1003/state.json')));
  assert(await evaluate(`document.querySelector('#action-submit').disabled`));
  pass('删除期间状态变化会拒绝操作，保留记录并要求刷新重新确认');

  await click('#action-dialog .dialog-footer [data-action="dialog-close"]');
  await click('[data-action="refresh"]');
  await click('.run-actions [data-action="delete-run"]');
  await until(`!!document.querySelector('#action-confirm')`, '重新确认删除完成记录');
  await evaluate(`document.querySelector('#action-confirm').click()`);
  await click('#action-submit');
  await until(
    `!!document.querySelector('#run-search') && !document.querySelector('[data-run="demo-completed-1003"]')`,
    '完成记录已删除',
  );
  assert(!existsSync(join(temporary, 'runs/demo-completed-1003')));
  assert(await evaluate(`!new URL(location.href).searchParams.has('run')`));
  await screenshot('desktop-runs-after-delete');
  await send('Page.navigate', { url: demoURL.origin + '/?run=demo-completed-1003' });
  await until(
    `!!document.querySelector('#run-search') && !new URL(location.href).searchParams.has('run')`,
    '旧链接返回运行列表',
  );
  assert.equal(await evaluate(`document.querySelectorAll('.run-table tbody tr').length`), 4);
  pass('完成记录可从详情删除并返回列表，刷新及旧链接不会恢复已删除记录');
  registrationFixture('seed');
  await evaluate(`import('/navigation.js').then(m=>m.navigate('demo-registration-1007'))`);
  await click('.dag-node[data-key="upload"]');
  await until(`document.querySelector('#drawer-body').textContent.includes('登记信息待补全')`, '旧记录登记缺项提示');
  await click('[data-tab="config"]');
  await until(`document.querySelector('#drawer-body').textContent.includes('未记录，请到智能体补齐登记信息')`, '注册信息缺项');
  await click('[data-tab="preview"]');
  await until(`document.querySelector('#drawer-body').textContent.includes('未记录，请到智能体补齐登记信息')`, '预览缓存缺项');
  pass('上传旧记录缺资产时明确提示补齐登记信息，不伪称已登记');
  await click('[data-tab="config"]');
  registrationFixture('record');
  await until(`document.querySelector('#drawer-body').textContent.includes('registered-browser-asset')`, '相同成功状态下自动刷新注册页签');
  assert(await evaluate(`document.querySelector('#drawer-body').textContent.includes('registered-browser-version')`));
  await click('[data-tab="preview"]');
  await until(`document.querySelector('#drawer-body').textContent.includes('registered-browser-asset')`, '失效的预览缓存更新');
  assert(!(await evaluate(`document.querySelector('#drawer-body').textContent.includes('未记录，请到智能体')`)));
  await screenshot('desktop-registration-updated');
  pass('登记信息后补无需关闭抽屉，自动更新当前页签并使其他页签旧缓存失效');
  await evaluate(`import('/navigation.js').then(m=>m.navigate('demo-registration-1008'))`);
  await click('.dag-node[data-key="upload"]');
  await click('[data-tab="config"]');
  await until(`document.querySelector('#drawer-body').textContent.includes('asset-left')`, '多输入注册信息');
  assert(await evaluate(`['asset-left','asset-right','version-left','version-right','输入 left','输入 right'].every(v=>document.querySelector('#drawer-body').textContent.includes(v))`));
  assert(await evaluate(`['A','B'].every(key=>document.querySelector('.dag-node[data-key="'+key+'"]').classList.contains('READY'))`));
  await screenshot('desktop-multi-registration');
  pass('上传注册按输入 ID 分别展示两个数据源的资产、版本和路径');
  await click('[data-action="drawer-close"]');
  timelineFixture('seed');
  await evaluate(`import('/navigation.js').then(m=>m.refresh(true))`);
  await click('[data-filter="all"]');
  await until(`Number(document.querySelector('#event-count').textContent.replace(/[^0-9]/g,''))>240`, '大量历史事件');
  assert(await evaluate(`document.querySelector('.timeline-section').classList.contains('collapsed')`));
  assert.equal(await evaluate(`document.querySelectorAll('#timeline .event').length`), 20);
  assert(await evaluate(`document.scrollingElement.scrollHeight<=window.innerHeight+1`));
  await screenshot('desktop-timeline-collapsed');
  pass('大量事件默认收起且最多渲染20条，整页高度固定');
  await click('[data-action="event-toggle"]');
  await until(`!document.querySelector('#event-panel').hidden`, '展开事件面板');
  assert(await evaluate(`document.querySelector('#timeline').scrollHeight>document.querySelector('#timeline').clientHeight&&document.querySelector('#timeline').clientHeight>40`));
  assert(await evaluate(`document.scrollingElement.scrollHeight<=window.innerHeight+1`));
  const longEventSeq = await evaluate(`document.querySelector('.event-full').dataset.seq`);
  assert(!(await evaluate(`document.querySelector('.event-full').open`)));
  await click('.event-full summary');
  await until(`import('/state.js').then(m=>m.ui.eventExpanded.has(Number(${JSON.stringify(longEventSeq)})))`, '展开完整事件');
  await evaluate(`import('/navigation.js').then(m=>m.refresh(true))`);
  assert(await evaluate(`document.querySelector('.event-full[data-seq="${longEventSeq}"]').open`));
  await click('.event-full summary');
  await screenshot('desktop-timeline-expanded');
  await click('[data-action="event-page"][data-direction="1"]');
  const historicalSequences = await evaluate(`[...document.querySelectorAll('#timeline .event')].map(e=>e.dataset.seq)`);
  await evaluate(`document.querySelector('#timeline').scrollTop=80`);
  timelineFixture('append');
  await evaluate(`import('/navigation.js').then(m=>m.refresh(true))`);
  assert.deepEqual(await evaluate(`[...document.querySelectorAll('#timeline .event')].map(e=>e.dataset.seq)`), historicalSequences);
  assert(await evaluate(`document.querySelector('#event-pager').textContent.includes('有 3 条新事件')`));
  assert(await evaluate(`document.querySelector('#timeline').scrollTop>=79`));
  await screenshot('desktop-timeline-history');
  await click('[data-action="event-page"][data-direction="latest"]');
  assert(!(await evaluate(`document.querySelector('#event-pager').textContent.includes('条新事件')`)));
  await click('[data-filter="failures"]');
  assert(await evaluate(`[...document.querySelectorAll('#timeline .event-detail strong')].every(e=>e.textContent==='操作失败')`));
  assert.equal(await evaluate(`document.querySelectorAll('#timeline .event').length`), 20);
  await click('[data-filter="all"]');
  pass('时间线独立滚动与分页，浏览旧页时新事件不挤动内容，可返回最新并保留筛选');
  for (const [width, height] of [[2560, 1080], [1512, 920], [1280, 600], [768, 844], [390, 844]]) {
    await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: false });
    await evaluate(`import('/pipeline.js').then(m=>m.renderRun())`);
    assert(await evaluate(`document.scrollingElement.scrollHeight<=window.innerHeight+1&&document.scrollingElement.scrollWidth<=window.innerWidth`));
    assert(await evaluate(`document.querySelector('#event-pager').getBoundingClientRect().bottom<=window.innerHeight+1`));
    assert(await evaluate(`document.querySelector('#timeline').clientHeight>0`));
    assert(await evaluate(`document.querySelector('.event-preview').getBoundingClientRect().height<=44`));
    if (width <= 700 || height <= 700) {
      assert(await evaluate(`getComputedStyle(document.querySelector('.flow-panel')).display==='none'`));
      await click('[data-action="event-toggle"]');
      assert(await evaluate(`getComputedStyle(document.querySelector('.flow-panel')).display!=='none'&&document.querySelector('.dag-scroll').clientHeight>0`));
      await click('[data-action="event-toggle"]');
    }
    await screenshot('timeline-viewport-' + width);
  }
  pass('大屏、短屏、平板和手机无整页滚动条，小屏事件聚焦与流程恢复可用');
  await send('Emulation.setDeviceMetricsOverride', { width: 1512, height: 920, deviceScaleFactor: 1, mobile: false });
  await evaluate(`import('/navigation.js').then(m=>m.navigate('demo-bypass-1005'))`);
  await click('[data-action="view-summary"]');
  assert(await evaluate(`document.scrollingElement.scrollHeight<=window.innerHeight+1`));
  assert(await evaluate(`document.querySelector('#summary').scrollHeight>document.querySelector('#summary').clientHeight`));
  await evaluate(`document.querySelector('#summary').scrollTop=140`);
  await evaluate(`import('/navigation.js').then(m=>m.refresh(true))`);
  assert(await evaluate(`document.querySelector('#summary').scrollTop>=139`));
  await screenshot('desktop-summary-contained');
  await click('[data-action="runs"]');
  assert(await evaluate(`document.scrollingElement.scrollHeight<=window.innerHeight+1`));
  pass('摘要和运行列表在固定工作台内浏览，刷新保留摘要滚动位置');
  assert.equal(resourceRequests, 0);
  assert.deepEqual(errors, []);
  pass('无浏览器脚本异常或资源监控请求');
  writeFileSync(
    join(output, 'report.json'),
    JSON.stringify({ passed, errors, screenshots: output }, null, 2),
  );
  console.log(`${passed.length} browser checks passed. Screenshots: ${output}`);
} catch (error) {
  if (socket && session) {
    try {
      await screenshot('failure');
      console.error(
        await evaluate("document.querySelector('#drawer')?.innerText||document.body.innerText"),
      );
      console.error(JSON.stringify(errors));
      console.error(
        JSON.stringify({
          modules: [...moduleResponses],
          messages: browserMessages,
        }),
      );
    } catch {}
  }
  throw error;
} finally {
  if (socket) {
    try {
      await send('Browser.close', {}, null);
    } catch {}
    socket.close();
  }
  browser?.kill();
  if (service && demoURL) {
    try {
      await fetch(demoURL.origin + '/api/shutdown', {
        method: 'POST',
        headers: {
          Authorization: 'Bearer ' + demoURL.searchParams.get('token'),
          'X-Pipeline-Monitor': '1',
          'Content-Type': 'application/json',
        },
        body: '{}',
        signal: AbortSignal.timeout(3000),
      });
    } catch {}
  }
  await sleep(500);
  service?.kill();
  rmSync(temporary, {
    recursive: true,
    force: true,
    maxRetries: 20,
    retryDelay: 100,
  });
}
