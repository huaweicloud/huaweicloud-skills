// Shared monitor state and API paths; modules mutate fields on ui.
import { enc } from './common.js';

const LOG_REFRESH_INTERVAL_MS = 60000;
const ui = {
  run: new URL(location.href).searchParams.get('run'),
  snapshot: null,
  runs: [],
  events: [],
  eventSeq: 0,
  eventFilter: 'all',
  eventPage: 0,
  eventCutoff: null,
  eventExpanded: new Set(),
  eventsCollapsed: true,
  selected: null,
  attempt: null,
  tab: 'overview',
  detail: null,
  drawerContext: '',
  drawerPanels: new Map(),
  activePanel: null,
  previewTree: null,
  view: 'pipeline',
  drawerEpoch: 0,
  runEpoch: 0,
  listSearch: '',
  listStatus: '',
  systemLog: false,
  logFiles: [],
  logFile: 0,
  logContent: '',
  logFull: false,
  logAuto: false,
  logErrors: false,
  logSearch: '',
  errorIndex: 0,
  modal: null,
  busy: false,
  polling: false,
  logPolling: false,
  logRequest: 0,
  logListRequest: 0,
  previewRequest: 0,
};
function node() {
  return ui.snapshot?.nodes.find((n) => n.key === ui.selected);
}
function runAPI(suffix = '') {
  return '/api/runs/' + enc(ui.run) + suffix;
}
function taskAPI(suffix = '') {
  return runAPI('/tasks/' + enc(ui.attempt) + suffix);
}

export { LOG_REFRESH_INTERVAL_MS, node, runAPI, taskAPI, ui };
