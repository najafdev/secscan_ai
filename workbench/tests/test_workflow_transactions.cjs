'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {join} = require('node:path');
const vm = require('node:vm');
const root = join(__dirname, '..', 'static');
const html = readFileSync(join(root, 'index.html'), 'utf8');

{
const script = readFileSync(join(root, 'adapter.js'), 'utf8');
function node() {
  return {value: '', checked: false, disabled: false, hidden: false, textContent: '', className: '', listeners: {},
    addEventListener(name, callback) { this.listeners[name] = callback; }};
}

function harness(responder) {
  const nodes = Object.fromEntries([...html.matchAll(/\bid="([^"]+)"/g)].map((m) => [m[1], node()]));
  nodes['adapter-kind'].value = 'project';
  nodes['adapter-asset'].value = 'asset-1';
  nodes['adapter-target'].value = '/tmp/project';
  const requests = [];
  const events = [];
  const document = {getElementById(id) { assert.ok(nodes[id], `missing #${id}`); return nodes[id]; },
    dispatchEvent(event) { events.push(event); }};
  const context = vm.createContext({
    document,
    CustomEvent: class { constructor(type, options) { this.type = type; this.detail = options.detail; } },
    sessionStorage: {getItem() { return 'session-token'; }},
    fetch: async (path, options) => {
      const body = options.body ? JSON.parse(options.body) : undefined;
      requests.push({path, body, options});
      const value = await responder(path, body);
      return {ok: !value.__error, json: async () => value.__error || value};
    },
    console,
  });
  vm.runInContext(script, context);
  return {nodes, requests, events, trigger: async (id, event='click') => nodes[id].listeners[event]({preventDefault() {}})};
}

const id = 'a'.repeat(32);
const sha = 'b'.repeat(64);
const declaration = {adapter: {id: 'native-project-metadata', version: '1'}, limits: {max_objects: 1000, max_requests: 0, timeout_seconds: 30}};

function planned(status='planned') {
  return {id, status, adapter_id: 'native-project-metadata', plan_sha256: sha, declaration,
    request_summary: {adapter_id: 'native-project-metadata', asset_key: 'asset-1', project_label: 'project', full_path_included: false}, outcome: null};
}

function deferred() {
  let resolve;
  const promise = new Promise((done) => { resolve = done; });
  return {promise, resolve};
}
function completed(resultStatus = 'completed') {
  return {...planned('completed'), receipt: {
    usage: {objects_tested: 2, network_requests: 0, elapsed_ms: 3},
    result: {status: resultStatus, findings: [], coverage: {objects_tested: 2}},
  }};
}
async function approve(h) { await h.trigger('adapter-plan'); await h.trigger('adapter-approve'); }

test('inputs freeze before slow planning returns, so displayed scope cannot drift', async () => {
  const gate = deferred(); const h = harness(async () => gate.promise);
  const pending = h.trigger('adapter-plan');
  assert.equal(h.nodes['adapter-target'].disabled, true);
  assert.equal(h.nodes['adapter-kind'].disabled, true);
  await h.trigger('adapter-plan');
  assert.equal(h.requests.length, 1);
  gate.resolve(planned()); await pending;
});

test('planning failure unfreezes inputs and never permits approval', async () => {
  const h = harness(async () => ({__error: {error: 'Invalid typed scope'}}));
  await h.trigger('adapter-plan');
  assert.equal(h.nodes['adapter-target'].disabled, false);
  assert.equal(h.nodes['adapter-approve'].disabled, true);
  assert.equal(h.nodes['adapter-execute'].disabled, true);
});

test('reset cannot race a pending approval or discard its exact plan', async () => {
  const gate = deferred(); const h = harness(async (path) => path.endsWith('/approve') ? gate.promise : planned());
  await h.trigger('adapter-plan'); const pending = h.trigger('adapter-approve');
  assert.equal(h.nodes['adapter-reset'].disabled, true);
  await h.trigger('adapter-reset');
  assert.equal(h.nodes['adapter-target'].disabled, true);
  gate.resolve(planned('approved')); await pending;
  assert.equal(h.nodes['adapter-execute'].disabled, false);
});

for (const state of ['failed', 'cancelled', 'interrupted', 'executing']) {
  test('HTTP success with lifecycle ' + state + ' cannot claim completed receipt', async () => {
    const h = harness(async (path) => path.endsWith('/approve') ? planned('approved') : path.endsWith('/execute') ? planned(state) : planned());
    await approve(h); await h.trigger('adapter-execute');
    assert.doesNotMatch(h.nodes['adapter-status'].textContent, /Execution completed with a durable receipt/);
    assert.equal(h.nodes['adapter-report'].disabled, true);
    assert.match(h.nodes['adapter-status'].textContent.toLowerCase(), new RegExp(state));
  });
}

test('partial adapter result keeps incomplete coverage visible before report creation', async () => {
  const h = harness(async (path) => path.endsWith('/approve') ? planned('approved') : path.endsWith('/execute') ? completed('partial') : planned());
  await approve(h); await h.trigger('adapter-execute');
  assert.match(h.nodes['adapter-status'].textContent, /partial|incomplete/i);
  assert.equal(h.nodes['adapter-report'].disabled, false);
});

test('late cancellation response cannot overwrite a completed outcome', async () => {
  const run = deferred(), stop = deferred();
  const h = harness(async (path) => {
    if (path.endsWith('/execute')) return run.promise;
    if (path.endsWith('/cancel')) return stop.promise;
    return path.endsWith('/approve') ? planned('approved') : planned();
  });
  await approve(h); const pending = h.trigger('adapter-execute'); const stopping = h.trigger('adapter-cancel');
  run.resolve(completed()); await pending;
  const finalStatus = h.nodes['adapter-status'].textContent;
  stop.resolve({note: 'Cancellation requested'}); await stopping;
  assert.equal(h.nodes['adapter-status'].textContent, finalStatus);
});

test('transport loss permits status recovery, never automatic re-execution', async () => {
  let rechecks = 0;
  const h = harness(async (path) => {
    if (path.endsWith('/approve')) return planned('approved');
    if (path.endsWith('/execute')) throw new Error('Connection interrupted');
    if (path === '/api/adapter-runs/' + id) {
      if (++rechecks === 1) throw new Error('Status unavailable');
      return completed();
    }
    return planned();
  });
  await approve(h); await h.trigger('adapter-execute');
  assert.match(h.nodes['adapter-status'].textContent, /unknown|unconfirmed/i);
  assert.equal(h.nodes['adapter-reset'].disabled, true);
  assert.equal(h.nodes['adapter-recheck'].disabled, false);
  await h.trigger('adapter-recheck');
  assert.equal(h.requests.filter((r) => r.path.endsWith('/execute')).length, 1);
  assert.equal(h.nodes['adapter-report'].disabled, false);
});

test('mismatched returned plan identity fails closed before execution', async () => {
  const h = harness(async (path) => path.endsWith('/approve') ? {...planned('approved'), id: 'd'.repeat(32)} : planned());
  await approve(h);
  assert.equal(h.nodes['adapter-execute'].disabled, true);
});


test('linked report navigation is explicit, local and does not rerun the adapter', async () => {
  const reportId = 'e'.repeat(32);
  const h = harness(async (path) => {
    if (path.endsWith('/report')) return {id: reportId, created: true};
    if (path.endsWith('/execute')) return completed();
    return path.endsWith('/approve') ? planned('approved') : planned();
  });
  await approve(h); await h.trigger('adapter-execute'); await h.trigger('adapter-report');
  assert.equal(h.events.length, 0);
  assert.equal(h.nodes['adapter-open-report'].disabled, false);
  await h.trigger('adapter-open-report');
  assert.equal(h.events[0].type, 'secscan_ai:review-report');
  assert.equal(h.events[0].detail.id, reportId);
  assert.equal(h.requests.filter((r) => r.path.endsWith('/execute')).length, 1);
});


test('malformed planning response never creates an approvable record', async () => {
  const h = harness(async () => ({id: '../untrusted', status: 'planned', plan_sha256: 'bad'}));
  await h.trigger('adapter-plan');
  assert.equal(h.nodes['adapter-approve'].disabled, true);
  assert.equal(h.nodes['adapter-target'].disabled, false);
  assert.match(h.nodes['adapter-status'].textContent, /No valid reviewed/);
});

}

{
const script = readFileSync(join(root, 'app.js'), 'utf8');
function node() {
  return {value: '', checked: false, disabled: false, hidden: true, textContent: '', className: '', children: [], listeners: {},
    addEventListener(name, callback) { this.listeners[name] = callback; },
    focus() { this.focused = true; },
    append(...items) { this.children.push(...items); }, replaceChildren(...items) { this.children = [...items]; }};
}
function harness(responder = async () => ({})) {
  const nodes = Object.fromEntries([...html.matchAll(/\bid="([^"]+)"/g)].map((match) => [match[1], node()]));
  const mode = {value: 'analyst'};
  nodes['target-type'].value = 'lab'; nodes.authorization.value = 'Reviewer UI fixture'; nodes.authorized.checked = true;
  const requests = [];
  const events = {}; const downloads = [];
  const document = {getElementById(id) { assert.ok(nodes[id], `HTML must define #${id}`); return nodes[id]; },
    querySelector() { return mode; }, querySelectorAll() { return []; },
    addEventListener(type, listener) { events[type] = listener; },
    createElement() { const item = node(); item.click = () => downloads.push(item); return item; }};
  const context = vm.createContext({document, location: {hash: '', pathname: '/'}, history: {replaceState() {}},
    URL: {createObjectURL() { return 'blob:owned-fixture'; }, revokeObjectURL() {}},
    sessionStorage: {getItem() { return ''; }, setItem() {}}, URLSearchParams, console, setTimeout, clearTimeout,
    fetch: async (path, options) => { const body = options.body ? JSON.parse(options.body) : undefined; requests.push({path, body}); const value = await responder(path, body); return {ok: !value.__error, blob: async () => value, json: async () => value.__error || value}; }});
  vm.runInContext(script, context);
  return {nodes, requests, downloads, dispatch: (type, detail) => events[type]({detail}), run: (code) => vm.runInContext(code, context),
    trigger: (id, event = 'click') => nodes[id].listeners[event]({preventDefault() {}})};
}
function report(id) {
  return {id, status: 'completed', target: 'lab://fixture', environment: 'synthetic_lab', verdict: 'observations_need_context', findings: [], checks: [], events: [], limitations: [], ai: {}, integrity: {report_sha256: 'fixture'}};
}

function deferred() {
  let resolve, reject;
  const promise = new Promise((ok, fail) => { resolve = ok; reject = fail; });
  return {promise, resolve, reject};
}

test('selecting another report immediately disables exports of previous evidence', async () => {
  const gate = deferred(); const oldId = 'a'.repeat(32), nextId = 'b'.repeat(32);
  const h = harness(async (path) => path === '/api/runs' ? {runs: []} : gate.promise);
  h.run(`selectedRun='${oldId}'; render(${JSON.stringify(report(oldId))})`);
  const selecting = h.run(`selectRun('${nextId}')`);
  assert.equal(h.nodes['export-json'].disabled, true);
  assert.equal(h.nodes['export-bundle'].disabled, true);
  gate.resolve(report(nextId)); await selecting;
  assert.equal(h.nodes['export-json'].disabled, false);
});

test('late failed poll of old report cannot unlock an active selected run', async () => {
  const gate = deferred(); const oldId = 'a'.repeat(32), currentId = 'b'.repeat(32);
  const h = harness(async () => gate.promise);
  h.run(`selectedRun='${oldId}'`); const pollingOld = h.run(`poll('${oldId}')`);
  h.run(`selectedRun='${currentId}'; render(${JSON.stringify({...report(currentId), status: 'running', integrity: null})})`);
  gate.reject(new Error('Old request failed')); await pollingOld;
  assert.equal(h.nodes['start'].disabled, true);
  assert.equal(h.nodes['cancel'].disabled, false);
});

test('late comparison cannot replace the selected report comparison panel', async () => {
  const gate = deferred(); const oldId = 'a'.repeat(32), currentId = 'b'.repeat(32);
  const h = harness(async () => gate.promise);
  h.run(`selectedRun='${currentId}'; running=false`); h.nodes['compare-run'].value = oldId;
  const comparing = h.trigger('compare');
  h.run(`selectedRun='${'c'.repeat(32)}'`);
  h.nodes['compare-content'].textContent = 'New report pending review';
  gate.resolve({items: [{state: 'not_reproduced'}]}); await comparing;
  assert.equal(h.nodes['compare-content'].textContent, 'New report pending review');
});


test('linked report opens through authenticated existing review endpoint only', async () => {
  const id = 'e'.repeat(32);
  const h = harness(async (path) => path === '/api/runs' ? {runs: []} : report(id));
  await h.dispatch('secscan_ai:review-report', {id});
  assert.deepEqual(h.requests.map((r) => r.path), ['/api/runs/' + id, '/api/runs']);
  assert.equal(h.nodes['export-json'].disabled, false);
  assert.equal(h.nodes.verdict.focused, true);
});

test('report bridge denies invalid IDs and switching during an active assessment', async () => {
  const h = harness();
  await h.dispatch('secscan_ai:review-report', {id: '../secrets'});
  h.run('running=true'); await h.dispatch('secscan_ai:review-report', {id: 'a'.repeat(32)});
  assert.equal(h.requests.length, 0);
  assert.match(h.nodes.notice.textContent, /active operation/);
});

test('download keeps requested report identity even if selection changes while waiting', async () => {
  const gate = deferred(); const oldId = 'a'.repeat(32), newId = 'b'.repeat(32);
  const h = harness(async () => gate.promise);
  h.run(`selectedRun='${oldId}'; running=false`);
  const pending = h.run("download('json')");
  h.run(`selectedRun='${newId}'`); gate.resolve({owned: true}); await pending;
  assert.equal(h.requests[0].path, '/api/runs/' + oldId + '/export.json');
  assert.equal(h.downloads[0].download, 'secscan_ai-' + oldId + '.json');
});

test('unconfirmed active run stays locked until explicit status refresh succeeds', async () => {
  const id = 'a'.repeat(32); let calls = 0;
  const h = harness(async (path) => {
    if (path === '/api/runs') return {runs: []};
    if (++calls === 1) throw new Error('Connection lost');
    return report(id);
  });
  h.run(`selectedRun='${id}'; render(${JSON.stringify({...report(id), status:'running', integrity:null})})`);
  await h.run(`poll('${id}')`);
  assert.equal(h.nodes.start.disabled, true);
  assert.equal(h.nodes.refresh.disabled, false);
  await h.trigger('refresh');
  assert.equal(h.nodes.start.disabled, false);
  assert.equal(h.requests.filter((r) => r.body !== undefined).length, 0);
});

test('accepted stop request stays pending across running renders and suppresses duplicates', async () => {
  const id = 'a'.repeat(32); let stops = 0;
  const h = harness(async (path) => {
    if (path.endsWith('/cancel')) { stops += 1; return {note: 'Cancellation requested'}; }
    return {runs: []};
  });
  const active = {...report(id), status: 'running', integrity: null};
  h.run(`selectedRun='${id}'; render(${JSON.stringify(active)})`);
  await h.trigger('cancel');
  assert.equal(stops, 1);
  assert.equal(h.nodes.cancel.disabled, true);
  assert.match(h.nodes.notice.textContent, /Stop requested; waiting for terminal confirmation/);
  await h.trigger('cancel');
  assert.equal(stops, 1);
  h.run(`render(${JSON.stringify(active)})`);
  assert.equal(h.nodes.cancel.disabled, true);
  assert.match(h.nodes.notice.textContent, /Stop requested; waiting for terminal confirmation/);
});

test('terminal report resolves a pending stop without inventing a cancelled outcome', async () => {
  const id = 'a'.repeat(32);
  const h = harness(async () => ({note: 'Cancellation requested'}));
  h.run(`selectedRun='${id}'; render(${JSON.stringify({...report(id), status: 'running', integrity: null})})`);
  await h.trigger('cancel');
  h.run(`render(${JSON.stringify(report(id))})`);
  assert.equal(h.nodes.cancel.disabled, true);
  assert.match(h.nodes.notice.textContent, /Stop request resolved/);
  assert.match(h.nodes.notice.textContent, /completed/i);
  assert.doesNotMatch(h.nodes.notice.textContent, /cancelled/i);
});

test('failed stop request clears pending state and restores Stop for the same running run', async () => {
  const id = 'a'.repeat(32);
  const h = harness(async () => ({__error: {error: 'Cancellation service unavailable'}}));
  h.run(`selectedRun='${id}'; render(${JSON.stringify({...report(id), status: 'running', integrity: null})})`);
  await h.trigger('cancel');
  assert.equal(h.nodes.cancel.disabled, false);
  assert.match(h.nodes.notice.textContent, /Stop is not confirmed/);
  assert.equal(h.run('stopRequestedRun'), null);
});

test('accepted stop remains non-repeatable when a status poll becomes unconfirmed', async () => {
  const id = 'a'.repeat(32); let stops = 0;
  const h = harness(async (path) => {
    if (path.endsWith('/cancel')) { stops += 1; return {note: 'Cancellation requested'}; }
    throw new Error('Status unavailable');
  });
  h.run(`selectedRun='${id}'; render(${JSON.stringify({...report(id), status: 'running', integrity: null})})`);
  await h.trigger('cancel');
  await h.run(`poll('${id}')`);
  assert.equal(h.nodes.cancel.disabled, true);
  assert.match(h.nodes.notice.textContent, /Stop was requested; terminal state is unconfirmed/);
  await h.trigger('cancel');
  assert.equal(stops, 1);
});


test('late stop response cannot overwrite the next selected report', async () => {
  const gate = deferred(); const id = 'a'.repeat(32); const nextId = 'b'.repeat(32); const h = harness(async () => gate.promise);
  h.run(`selectedRun='${id}'; render(${JSON.stringify({...report(id), status: 'running', integrity: null})})`);
  const pending = h.trigger('cancel');
  h.run(`selectionEpoch += 1; selectedRun='${nextId}'; render(${JSON.stringify({...report(nextId), status: 'running', integrity: null})})`);
  h.nodes.notice.textContent = 'Selected next report';
  gate.resolve({note: 'Cancellation requested'}); await pending;
  assert.equal(h.nodes.notice.textContent, 'Selected next report');
  assert.equal(h.nodes.cancel.disabled, false);
});

}
