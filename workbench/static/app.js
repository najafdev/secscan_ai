'use strict';
const $ = (id) => document.getElementById(id);
let token = sessionStorage.getItem('secscan_ai-token') || '';
let selectedRun = null;
let selectionEpoch = 0;
let comparisonEpoch = 0;
let polling = null;
let running = false;
let starting = false;
let testingModel = false;
let modelCheckEpoch = 0;
let discoveryEpoch = 0;
let historyRuns = [];
let stopRequestedRun = null;
const stopPendingMessage = 'Stop requested; waiting for terminal confirmation.';
const fragment = new URLSearchParams(location.hash.slice(1));
if (fragment.has('token')) {
  token = fragment.get('token');
  sessionStorage.setItem('secscan_ai-token', token);
  history.replaceState(null, '', location.pathname);
}
function notice(text, error = false) {
  $('notice').textContent = text;
  $('notice').className = text ? (error ? 'notice error' : 'notice') : '';
}
function stopPending(id = selectedRun) { return !!id && stopRequestedRun === id; }
function announcePendingStop() {
  if (stopPending() && running && $('notice').textContent !== stopPendingMessage) notice(stopPendingMessage);
}
async function api(path, body, raw = false) {
  const response = await fetch(path, {method: body === undefined ? 'GET' : 'POST', headers: {'Authorization': 'Bearer ' + token, ...(body === undefined ? {} : {'Content-Type': 'application/json'})}, ...(body === undefined ? {} : {body: JSON.stringify(body)})});
  if (!response.ok) {
    const error = await response.json().catch(() => ({error: 'Local service unavailable'}));
    throw new Error((error.error || 'Request failed') + (error.next_step ? ' ' + error.next_step : ''));
  }
  return raw ? response : response.json();
}
function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = String(text);
  if (className) node.className = className;
  return node;
}
function human(text) { return String(text || '').replaceAll('_', ' '); }
function comparisonCount(result, key) {
  const value = result && result.counts && result.counts[key];
  return Number.isInteger(value) && value >= 0 ? value : 0;
}
function comparisonFlag(value) {
  if (value === true) return 'same';
  if (value === false) return 'changed';
  return 'not recorded';
}
function adapterLabel(adapter) {
  if (!adapter || typeof adapter !== 'object' || typeof adapter.id !== 'string' || typeof adapter.version !== 'string') return null;
  return adapter.id + '@' + adapter.version;
}
function coverageText(coverage) {
  if (!coverage || typeof coverage !== 'object') return 'unknown';
  const parts = [human(coverage.status || 'unknown')];
  const expectedAdapter = adapterLabel(coverage.expected_adapter);
  if (expectedAdapter) parts.push('expected adapter ' + expectedAdapter);
  if (Array.isArray(coverage.observed_adapters)) {
    const observed = coverage.observed_adapters.map(adapterLabel).filter(Boolean);
    if (observed.length) parts.push('observed adapter ' + observed.join(', '));
  }
  if (typeof coverage.expected_method === 'string' && coverage.expected_method) parts.push('expected method ' + coverage.expected_method);
  if (Array.isArray(coverage.observed_methods) && coverage.observed_methods.length) parts.push('observed method ' + coverage.observed_methods.join(', '));
  if (typeof coverage.reason === 'string' && coverage.reason) parts.push(coverage.reason);
  return parts.join(' · ');
}
function comparisonText(result) {
  if (!result || result.schema !== 'secscan_ai.retest-diff/v1') throw new Error('Unsupported comparison response.');
  const scope = result.scope_comparison && typeof result.scope_comparison === 'object' ? result.scope_comparison : {};
  const lines = [
    result.comparable_scope ? 'Comparable scope: yes' : 'Comparable scope: no',
    'Scope: target ' + comparisonFlag(scope.same_target) + ' · environment ' + comparisonFlag(scope.same_environment) + ' · mode ' + comparisonFlag(scope.same_mode) + ' · engine ' + comparisonFlag(scope.same_engine_version),
    'Finding states: Still present ' + comparisonCount(result, 'still_present') + ' · New ' + comparisonCount(result, 'new') + ' · Not reproduced ' + comparisonCount(result, 'not_reproduced') + ' · Not retested ' + comparisonCount(result, 'not_retested'),
  ];
  const items = Array.isArray(result.items) ? result.items : [];
  if (items.length) {
    lines.push('', 'Finding review:');
    items.forEach((item, index) => {
      const label = item && (item.title || item.rule) ? (item.title || item.rule) : 'Untitled finding';
      lines.push((index + 1) + '. ' + human(item && item.state).toUpperCase() + ' — ' + label);
      if (item && typeof item.reason === 'string' && item.reason) lines.push('   ' + item.reason);
      const coverage = item && item.recheck && item.recheck.coverage;
      if (coverage) lines.push('   Coverage: ' + coverageText(coverage));
    });
  } else {
    lines.push('', 'No finding changes were recorded by this comparison.');
  }
  lines.push('', 'Reviewer boundary: not reproduced is not fixed; not retested means comparable successful coverage was not established.');
  return lines.join('\n');
}
function comparisonAnnouncement(result) {
  return 'Comparison ready. ' + comparisonCount(result, 'still_present') + ' still present, ' + comparisonCount(result, 'new') + ' new, ' + comparisonCount(result, 'not_reproduced') + ' not reproduced, ' + comparisonCount(result, 'not_retested') + ' not retested.';
}
function syncForm() {
  const lab = $('target-type').value === 'lab';
  $('target').disabled = lab;
  $('target').required = !lab;
  $('target-help').textContent = lab ? 'A disposable local fixture with a real HTTP proof. No external target is contacted.' : 'One HEAD request to this exact public URL. Ports 80/443 only. No redirects, private IPs or response bodies.';
  const verify = document.querySelector('input[name="mode"]:checked').value === 'verify';
  $('approval-row').hidden = !verify;
  $('approve').required = verify;
  $('model').disabled = !$('use-ai').checked;
  $('model').required = $('use-ai').checked;
  $('check-model').disabled = !$('use-ai').checked || running;
  $('test-model').disabled = !$('use-ai').checked || running;
  $('allow-cloud').disabled = !$('use-ai').checked || running;
  revokeCloud();
}
async function unlock() {
  try {
    const health = await api('/api/health');
    $('unlock').hidden = true;
    $('connection').textContent = 'Local session connected';
    $('connection').className = 'status connected';
    $('controls').disabled = false;
    $('refresh').disabled = false;
    syncForm();
    await loadHistory();
    notice('');
    if (health.active_run) await selectRun(health.active_run);
  } catch (error) {
    $('unlock').hidden = false;
    $('controls').disabled = true;
    $('refresh').disabled = true;
    $('connection').textContent = 'Session locked';
    $('connection').className = 'status';
    if (token) notice(error.message, true);
  }
}
$('unlock-form').addEventListener('submit', async (event) => {
  event.preventDefault(); token = $('token').value.trim(); $('token').value = '';
  sessionStorage.setItem('secscan_ai-token', token); await unlock();
});
$('target-type').addEventListener('change', syncForm);
$('use-ai').addEventListener('change', syncForm);
document.querySelectorAll('input[name="mode"]').forEach((node) => node.addEventListener('change', syncForm));
function cloudChoice() { return $('use-ai').checked && $('allow-cloud').checked; }
function policyBody() { return cloudChoice() ? {allow_cloud: true} : {}; }
function revokeCloud() {
  $('allow-cloud').checked = false;
  invalidateModel();
}
function invalidateModel() {
  modelCheckEpoch += 1;
  $('model-state').textContent = $('use-ai').checked ? 'Model not checked for this configuration.' : 'AI disabled. Native checks remain deterministic; no alternate provider is used.';
  $('model-details').hidden = true;
}
function needsTools() {
  return $('target-type').value === 'lab' && document.querySelector('input[name="mode"]:checked').value === 'verify';
}
async function checkModel() {
  const epoch = ++modelCheckEpoch;
  const model = $('model').value.trim();
  const requireTools = needsTools();
  if (!model) throw new Error('Detect and select an installed Ollama model first.');
  $('check-model').disabled = true;
  $('model-state').textContent = 'Checking installed model metadata. No inference is being run.';
  try {
    const result = await api('/api/models/check', {model, require_tools: requireTools, ...policyBody()});
    if (epoch !== modelCheckEpoch) return;
    $('model-state').textContent = result.tool_calling ? 'Metadata checked: analysis + tool calling.' : 'Metadata checked: analysis only. Tool-directed verification is unavailable.';
    $('model-details').textContent = result.model + ' · ' + result.parameter_size + ' · ' + result.quantization + ' · ' + human(result.execution_location || 'unknown') + '\n' + result.note;
    $('model-details').hidden = false;
  } catch (error) {
    if (epoch === modelCheckEpoch) $('model-state').textContent = error.message;
    throw error;
  } finally { $('check-model').disabled = !$('use-ai').checked || running; }
}
async function testModel() {
  if (running || starting || testingModel || !$('use-ai').checked) return;
  const model = $('model').value.trim();
  if (!model) throw new Error('Select an Ollama model first.');
  const epoch = ++modelCheckEpoch;
  testingModel = true;
  $('test-model').disabled = true;
  $('start').disabled = true;
  $('model-state').textContent = 'Testing fixed synthetic prompts. No assessment data is sent; model usage applies.';
  try {
    const result = await api('/api/models/self-test', {model, require_tools: needsTools(), ...policyBody()});
    if (epoch !== modelCheckEpoch) return;
    $('model-state').textContent = 'Synthetic response compatible. This is not a security finding or a quality benchmark.';
    $('model-details').textContent = result.model + '\n' + result.note;
    $('model-details').hidden = false;
  } catch (error) {
    if (epoch === modelCheckEpoch) $('model-state').textContent = error.message;
    throw error;
  } finally {
    testingModel = false;
    $('test-model').disabled = running || !$('use-ai').checked;
    $('start').disabled = running || starting;
  }
}
$('test-model').addEventListener('click', () => testModel().catch((error) => notice(error.message, true)));
$('model').addEventListener('input', revokeCloud);
$('target').addEventListener('input', revokeCloud);
$('authorization').addEventListener('input', revokeCloud);
$('authorized').addEventListener('change', revokeCloud);
$('approve').addEventListener('change', revokeCloud);
$('allow-cloud').addEventListener('change', invalidateModel);
$('check-model').addEventListener('click', () => checkModel().catch((error) => notice(error.message, true)));
$('detect').addEventListener('click', async () => {
  $('detect').disabled = true;
  invalidateModel();
  const epoch = ++discoveryEpoch;
  const choice = cloudChoice();
  try {
    const result = cloudChoice() ? await api('/api/models/discover', {allow_cloud: true}) : await api('/api/models');
    if (epoch !== discoveryEpoch || choice !== cloudChoice()) return;
    $('model-list').replaceChildren();
    result.models.forEach((name) => { const option = element('option'); option.value = name; $('model-list').append(option); });
    $('model-help').textContent = result.note;
    $('model-state').textContent = human(result.state) + (result.blocked_models ? ' · ' + result.blocked_models + ' remote model(s) filtered.' : '');
  } catch (error) { notice(error.message, true); }
  finally { $('detect').disabled = running; }
});
$('scan-form').addEventListener('submit', async (event) => {
  event.preventDefault(); if (running || starting || testingModel) return;
  starting = true;
  const body = {target: $('target-type').value === 'lab' ? 'lab' : $('target').value.trim(), mode: document.querySelector('input[name="mode"]:checked').value, authorized: $('authorized').checked, authorization: $('authorization').value.trim(), approve_verification: $('approve').checked, use_ai: $('use-ai').checked, model: $('model').value.trim(), allow_cloud: cloudChoice()};
  const revision = modelCheckEpoch;
  $('start').disabled = true;
  try {
    if (body.use_ai) await api('/api/models/check', {model: body.model, require_tools: body.target === 'lab' && body.mode === 'verify', ...(body.allow_cloud ? {allow_cloud: true} : {})});
    if (revision !== modelCheckEpoch) throw new Error('Configuration or processing approval changed during preflight. Review it and start again.');
    const result = await api('/api/runs', body);
    revokeCloud();
    notice('Run started with the approved configuration. Only recorded evidence determines verification.');
    await selectRun(result.id);
  } catch (error) { notice(error.message, true); }
  finally { starting = false; $('start').disabled = running; }
});
async function selectRun(id) {
  if (polling) clearTimeout(polling);
  selectedRun = id;
  selectionEpoch += 1;
  comparisonEpoch += 1;
  ['export-json', 'export-md', 'export-bundle', 'compare'].forEach((name) => { $(name).disabled = true; });
  $('compare-run').disabled = true;
  $('cancel').disabled = true;
  $('run-status').textContent = 'Loading selected report...';
  $('verdict').textContent = 'Waiting for the selected evidence';
  $('findings').replaceChildren();
  $('coverage-content').textContent = 'Loading selected coverage...';
  $('compare-content').textContent = 'Select a finalized earlier run after viewing the current report.';
  await poll(id);
}
async function poll(id) {
  const epoch = selectionEpoch;
  try {
    const report = await api('/api/runs/' + id);
    if (id !== selectedRun || epoch !== selectionEpoch) return;
    render(report);
    if (report.status === 'running') polling = setTimeout(() => poll(id), 900);
    else await loadHistory();
  } catch (error) {
    if (id !== selectedRun || epoch !== selectionEpoch) return;
    running = true; $('start').disabled = true; $('cancel').disabled = stopPending(id); $('refresh').disabled = false;
    const stopState = stopPending(id) ? ' Stop was requested; terminal state is unconfirmed.' : ' Use Refresh to check status before assuming the run has stopped.';
    notice(error.message + ' Outcome unconfirmed.' + stopState, true);
  }
}
function updateRetestOptions() {
  const select = $('compare-run');
  const oldValue = select.value;
  select.replaceChildren();
  const first = element('option', 'Select earlier run'); first.value = ''; select.append(first);
  historyRuns.filter((run) => run.id !== selectedRun).forEach((run) => {
    const option = element('option', new Date(run.started_at).toLocaleString() + ' · ' + run.target + ' · ' + human(run.verdict));
    option.value = run.id; select.append(option);
  });
  if (historyRuns.some((run) => run.id === oldValue && run.id !== selectedRun)) select.value = oldValue;
  else select.value = '';
  select.disabled = running || !selectedRun || select.children.length <= 1;
  $('compare').disabled = select.disabled || !select.value;
}
function render(report) {
  const wasStopPending = stopPending(report.id);
  running = report.status === 'running';
  if (wasStopPending && !running) stopRequestedRun = null;
  $('start').disabled = running; $('cancel').disabled = !running || stopPending(report.id);
  $('refresh').disabled = running;
  $('detect').disabled = running;
  $('check-model').disabled = running || !$('use-ai').checked;
  $('test-model').disabled = running || !$('use-ai').checked;
  $('allow-cloud').disabled = running || !$('use-ai').checked;
  document.querySelectorAll('.history-item').forEach((node) => { node.disabled = running; });
  const exportable = !running && !!report.integrity;
  $('export-json').disabled = !exportable; $('export-md').disabled = !exportable; $('export-bundle').disabled = !exportable;
  $('count-findings').textContent = report.findings.length;
  $('count-verified').textContent = report.findings.filter((f) => f.verification === 'verified_in_lab').length;
  $('count-checks').textContent = report.checks.filter((c) => c.status === 'completed').length;
  $('run-status').textContent = human(report.status).toUpperCase() + ' / ' + report.target;
  $('verdict').textContent = human(report.verdict);
  $('timeline').replaceChildren();
  report.events.forEach((event) => {
    const row = element('div', undefined, 'event');
    const time = new Date(event.at).toLocaleTimeString([], {hour: '2-digit', minute: '2-digit', second: '2-digit'});
    row.append(element('time', time), element('span', event.message)); $('timeline').append(row);
  });
  $('timeline').scrollTop = $('timeline').scrollHeight;
  $('findings').replaceChildren();
  if (!report.findings.length) $('findings').append(element('p', 'No findings recorded in the executed checks. Review coverage before drawing conclusions.', 'muted'));
  report.findings.forEach((finding) => {
    const details = element('details', undefined, 'finding');
    const summary = element('summary');
    summary.append(element('span', finding.severity.toUpperCase(), 'severity ' + finding.severity), element('strong', finding.title));
    details.append(summary, element('div', human(finding.verification), 'verification'), element('p', finding.remediation));
    details.append(element('pre', JSON.stringify(finding.evidence, null, 2)), element('p', 'Evidence SHA-256: ' + finding.evidence_sha256, 'hash'));
    $('findings').append(details);
  });
  $('coverage-content').textContent = JSON.stringify({checks: report.checks, limitations: report.limitations}, null, 2);
  $('ai-content').textContent = JSON.stringify(report.ai, null, 2);
  $('integrity').textContent = report.integrity ? 'Finalized report SHA-256 (unsigned): ' + report.integrity.report_sha256 : 'Report in progress. Integrity digest will be calculated at completion.';
  updateRetestOptions();
  if (wasStopPending && !running) notice('Stop request resolved. Terminal state: ' + human(report.status).toUpperCase() + '.');
  else announcePendingStop();
  if (report.persistence_error) notice(report.persistence_error, true);
}
async function loadHistory() {
  const result = await api('/api/runs');
  historyRuns = result.runs;
  $('history-list').replaceChildren();
  if (!result.runs.length) {
    updateRetestOptions();
    return $('history-list').append(element('p', 'No saved assessments yet. Completed, partial and failed runs will appear here.', 'muted'));
  }
  result.runs.forEach((run) => {
    const button = element('button', undefined, 'history-item'); button.type = 'button';
    button.append(element('strong', run.target), element('span', human(run.verdict)), element('time', new Date(run.started_at).toLocaleString()));
    button.disabled = running;
    button.addEventListener('click', () => selectRun(run.id)); $('history-list').append(button);
  });
  updateRetestOptions();
}
$('compare-run').addEventListener('change', () => { comparisonEpoch += 1; $('compare').disabled = running || !selectedRun || !$('compare-run').value; });
$('compare').addEventListener('click', async () => {
  const previous = $('compare-run').value;
  if (!previous || !selectedRun || previous === selectedRun || running) return;
  const current = selectedRun;
  const epoch = ++comparisonEpoch;
  const selection = selectionEpoch;
  const stillCurrent = () => current === selectedRun && epoch === comparisonEpoch && selection === selectionEpoch && previous === $('compare-run').value;
  $('compare').disabled = true;
  $('compare-content').textContent = 'Comparing finalized evidence and comparable coverage…';
  try {
    const result = await api('/api/runs/' + previous + '/compare/' + current);
    if (!stillCurrent()) return;
    $('compare-content').textContent = comparisonText(result);
    notice(comparisonAnnouncement(result));
  } catch (error) {
    if (!stillCurrent()) return;
    $('compare-content').textContent = 'Comparison unavailable.';
    notice(error.message, true);
  } finally {
    if (stillCurrent()) $('compare').disabled = running || !$('compare-run').value;
  }
});
$('refresh').addEventListener('click', () => (running && selectedRun ? selectRun(selectedRun) : loadHistory()).catch((error) => notice(error.message, true)));
$('cancel').addEventListener('click', async () => {
  const id = selectedRun, epoch = selectionEpoch;
  if (!id || !running || $('cancel').disabled || stopPending(id)) return;
  stopRequestedRun = id;
  $('cancel').disabled = true;
  notice('Requesting stop; waiting for service acknowledgement.');
  try {
    await api('/api/runs/' + id + '/cancel', {});
    if (id !== selectedRun || epoch !== selectionEpoch || !running || !stopPending(id)) return;
    announcePendingStop();
  } catch (error) {
    if (stopRequestedRun === id) stopRequestedRun = null;
    if (id !== selectedRun || epoch !== selectionEpoch || !running) return;
    $('cancel').disabled = false;
    notice(error.message + ' Stop is not confirmed.', true);
  }
});
async function download(extension) {
  const runId = selectedRun;
  if (!runId || running) return;
  try {
    const response = await api('/api/runs/' + runId + '/export.' + extension, undefined, true);
    const url = URL.createObjectURL(await response.blob()); const link = document.createElement('a');
    link.href = url; link.download = 'secscan_ai-' + runId + '.' + extension; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (error) { notice(error.message, true); }
}
$('export-json').addEventListener('click', () => download('json'));
$('export-md').addEventListener('click', () => download('md'));
$('export-bundle').addEventListener('click', () => download('bundle.zip'));
// This event only selects an existing local report; it grants no execution authority.
if (document.addEventListener) document.addEventListener('secscan_ai:review-report', async (event) => {
  const id = event.detail && event.detail.id;
  if (typeof id !== 'string' || !/^[a-f0-9]{32}$/.test(id)) return;
  if (running || starting || testingModel) {
    notice('Finish or stop the active operation before switching to the linked report.', true);
    return;
  }
  await selectRun(id);
  if (selectedRun === id && $('verdict').focus) $('verdict').focus();
});
if (token) unlock();
