// A classic script can explain file: opening before loading HTTP-only modules.
(() => {
  function appendText(parent, tag, text) {
    const element = document.createElement(tag);
    element.textContent = text;
    parent.append(element);
  }

  function showStartupHelp(status, message) {
    document.querySelector('#connection').textContent = status;
    const panel = document.createElement('section');
    panel.className = 'startup-help';
    panel.setAttribute('role', 'alert');
    appendText(panel, 'h1', status);
    appendText(panel, 'p', message);
    appendText(panel, 'p', '在 skill 根目录运行以下命令，可打开本地演示：');
    appendText(panel, 'pre', 'python3 scripts/pipeline-monitor/server.py --demo --open');
    appendText(panel, 'p', '查看已有运行时，将 --demo 替换为 --run <run_id>。');
    appendText(panel, 'p', '请访问服务启动时打印的完整 http://127.0.0.1 地址。');
    document.querySelector('#workspace').replaceChildren(panel);
  }

  if (location.protocol === 'file:') {
    showStartupHelp(
      '请先启动本地监控服务',
      '当前打开的是本地 HTML 文件。运行记录需要通过本地监控服务读取。',
    );
    return;
  }

  import('./app.js').catch(() => {
    showStartupHelp(
      '页面脚本加载失败',
      '请确认本地监控服务仍在运行，并重新打开服务地址；如果问题持续，请检查 skill 文件是否完整。',
    );
  });
})();
