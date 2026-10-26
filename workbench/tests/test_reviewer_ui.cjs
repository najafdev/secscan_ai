'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {join} = require('node:path');
const vm = require('node:vm');
const root = join(__dirname, '..', 'static');
const html = readFileSync(join(root, 'index.html'), 'utf8');
const script = readFileSync(join(root, 'app.js'), 'utf8');
const reviewerScript = readFileSync(join(root, 'reviewer.js'), 'utf8');

function node() {
  return {value: '', checked: false, disabled: false, hidden: true, textContent: '', className: '', children: [], listeners: {},
    addEventListener(name, callback) { this.listeners[name] = callback; },
    append(...items) { this.children.push(...items); }, replaceChildren(...items) { this.children = [...items]; }};
}
function harness(responder = async () => ({})) {
  const nodes = Object.fromEntries([...html.matchAll(/\bid="([^"]+)"/g)].map((match) => [match[1], node()]));
  const mode = {value: 'analyst'};
  nodes['target-type'].value = 'lab'; nodes.authorization.value = 'Reviewer UI fixture'; nodes.authorized.checked = true;
  const requests = [];
  const document = {getElementById(id) { assert.ok(nodes[id], `HTML must define #${id}`); return nodes[id]; },
    querySelector() { return mode; }, querySelectorAll() { return []; }, createElement() { return node(); }};
  const context = vm.createContext({document, location: {hash: '', pathname: '/'}, history: {replaceState() {}},
    sessionStorage: {getItem() { return ''; }, setItem() {}}, URLSearchParams, console, setTimeout, clearTimeout,
    fetch: async (path, options) => { const body = options.body ? JSON.parse(options.body) : undefined; requests.push({path, body}); const value = await responder(path, body); return {ok: !value.__error, json: async () => value.__error || value}; }});
  vm.runInContext(script, context);
  return {nodes, requests, run: (code) => vm.runInContext(code, context),
    trigger: (id, event = 'click') => nodes[id].listeners[event]({preventDefault() {}})};
}
function report(id) {
  return {id, status: 'completed', target: 'lab://fixture', environment: 'synthetic_lab', verdict: 'observations_need_context', findings: [], checks: [], events: [], limitations: [], ai: {}, integrity: {report_sha256: 'fixture'}};
}
function comparison(overrides = {}) {
  return {
    schema: 'secscan_ai.retest-diff/v1',
    comparable_scope: true,
    scope_comparison: {same_target: true, same_environment: true, same_mode: true, same_engine_version: true},
    counts: {still_present: 1, new: 1, not_reproduced: 1, not_retested: 1},
    items: [],
    note: 'comparison only',
    ...overrides,
  };
}

function reviewerNode(tagName = 'div') {
  return {
    tagName: tagName.toUpperCase(),
    className: '',
    textContent: '',
    children: [],
    append(...items) { this.children.push(...items); },
    insertBefore(item, before) {
      const index = before ? this.children.indexOf(before) : -1;
      if (index < 0) this.children.push(item);
      else this.children.splice(index, 0, item);
    },
    querySelector(selector) {
      if (selector === 'pre') return this.children.find((child) => child.tagName === 'PRE') || null;
      if (selector.startsWith('.')) {
        const className = selector.slice(1);
        return this.children.find((child) => String(child.className).split(/\s+/).includes(className)) || null;
      }
      return null;
    },
  };
}

function reviewerHarness() {
  let cards = [];
  const document = {
    createElement(tag) { return reviewerNode(tag); },
    querySelectorAll(selector) { return selector === '#findings .finding' ? cards : []; },
  };
  const context = vm.createContext({document, console});
  context.render = (value) => {
    cards = value.findings.map((finding) => {
      const card = reviewerNode('details');
      card.className = 'finding';
      const raw = reviewerNode('pre');
      raw.textContent = JSON.stringify(finding.evidence, null, 2);
      card.append(raw);
      return card;
    });
  };
  vm.runInContext(reviewerScript, context);
  return {context, cards: () => cards};
}

function coverageHarness() {
  const coverage = reviewerNode('pre');
  let cards = [];
  const document = {
    createElement(tag) { return reviewerNode(tag); },
    getElementById(id) { return id === 'coverage-content' ? coverage : null; },
    querySelectorAll(selector) { return selector === '#findings .finding' ? cards : []; },
  };
  const context = vm.createContext({document, console});
  context.render = (value) => {
    cards = (value.findings || []).map((finding) => {
      const card = reviewerNode('details');
      card.className = 'finding';
      const raw = reviewerNode('pre');
      raw.textContent = JSON.stringify(finding.evidence, null, 2);
      card.append(raw);
      return card;
    });
    coverage.textContent = JSON.stringify({checks: value.checks || [], limitations: value.limitations || []}, null, 2);
  };
  vm.runInContext(reviewerScript, context);
  return {context, coverage};
}

function aiHarness() {
  const ai = reviewerNode('pre');
  const coverage = reviewerNode('pre');
  let cards = [];
  const document = {
    createElement(tag) { return reviewerNode(tag); },
    getElementById(id) {
      if (id === 'ai-content') return ai;
      if (id === 'coverage-content') return coverage;
      return null;
    },
    querySelectorAll(selector) { return selector === '#findings .finding' ? cards : []; },
  };
  const context = vm.createContext({document, console});
  context.render = (value) => {
    cards = (value.findings || []).map((finding) => {
      const card = reviewerNode('details');
      card.className = 'finding';
      const raw = reviewerNode('pre');
      raw.textContent = JSON.stringify(finding.evidence, null, 2);
      card.append(raw);
      return card;
    });
    coverage.textContent = JSON.stringify({checks: value.checks || [], limitations: value.limitations || []}, null, 2);
    ai.textContent = JSON.stringify(value.ai || {}, null, 2);
  };
  vm.runInContext(reviewerScript, context);
  return {context, ai};
}

function coverageReport() {
  return {
    findings: [],
    checks: [
      {tool: 'http_baseline', status: 'completed', result: 'observed_only'},
      {tool: 'native-web-headers', status: 'inconclusive', reason: 'Synthetic response was not comparable', coverage: {objects_tested: 2, objects_total: 3, notes: ['one route excluded']}},
      {tool: 'controlled_verification', status: 'skipped', reason: 'No approved external verification adapter'},
      {tool: 'scanner-x', status: 'error', reason: 'Synthetic parser failure'},
    ],
    limitations: ['Authentication coverage was not executed.', 'No findings is not a security guarantee.'],
  };
}

function factMap(context, finding) {
  return Object.fromEntries(JSON.parse(JSON.stringify(context.reviewerEvidenceFacts(finding))));
}

test('finalized report enables evidence bundle export control', () => {
  const h = harness(); h.run(`selectedRun = '${'b'.repeat(32)}'; render(${JSON.stringify(report('b'.repeat(32)))})`);
  assert.equal(h.nodes['export-bundle'].disabled, false);
  assert.match(html, /Evidence bundle/);
});

test('running report keeps evidence bundle disabled', () => {
  const h = harness(); const running = {...report('b'.repeat(32)), status: 'running', integrity: null};
  h.run(`selectedRun = '${'b'.repeat(32)}'; render(${JSON.stringify(running)})`);
  assert.equal(h.nodes['export-bundle'].disabled, true);
});

test('retest selector renders reviewer summary instead of raw JSON', async () => {
  const oldId = 'a'.repeat(32), currentId = 'b'.repeat(32);
  const result = comparison({items: [{
    state: 'not_retested', title: 'CSP missing', reason: 'Mapped adapter identity changed.',
    recheck: {coverage: {
      status: 'version_changed',
      expected_adapter: {id: 'native-web-headers', version: '1'},
      observed_adapters: [{id: 'native-web-headers', version: '2'}],
      expected_method: 'HEAD', observed_methods: ['HEAD'],
    }},
  }]});
  const h = harness(async (path) => path.includes('/compare/') ? result : {});
  h.run(`historyRuns = [{id:'${oldId}', started_at:'2026-09-20T00:00:00Z', target:'lab://fixture', verdict:'observations_need_context'}]; selectedRun='${currentId}'; render(${JSON.stringify(report(currentId))})`);
  h.nodes['compare-run'].value = oldId; await h.trigger('compare-run', 'change'); await h.trigger('compare');
  assert.equal(h.requests[0].path, `/api/runs/${oldId}/compare/${currentId}`);
  assert.match(h.nodes['compare-content'].textContent, /Comparable scope: yes/);
  assert.match(h.nodes['compare-content'].textContent, /Still present 1 · New 1 · Not reproduced 1 · Not retested 1/);
  assert.match(h.nodes['compare-content'].textContent, /CSP missing/);
  assert.match(h.nodes['compare-content'].textContent, /version changed/);
  assert.match(h.nodes['compare-content'].textContent, /native-web-headers@1/);
  assert.match(h.nodes['compare-content'].textContent, /native-web-headers@2/);
  assert.match(h.nodes['compare-content'].textContent, /not reproduced is not fixed/);
  assert.doesNotMatch(h.nodes['compare-content'].textContent, /"counts"/);
  assert.match(h.nodes.notice.textContent, /Comparison ready\. 1 still present, 1 new, 1 not reproduced, 1 not retested\./);
});

test('scope drift is visible in reviewer summary', () => {
  const h = harness();
  const text = h.run(`comparisonText(${JSON.stringify(comparison({
    comparable_scope: false,
    scope_comparison: {same_target: false, same_environment: true, same_mode: null, same_engine_version: false},
    counts: {still_present: 0, new: 0, not_reproduced: 0, not_retested: 2},
  }))})`);
  assert.match(text, /Comparable scope: no/);
  assert.match(text, /target changed/);
  assert.match(text, /environment same/);
  assert.match(text, /mode not recorded/);
  assert.match(text, /engine changed/);
  assert.match(text, /Not retested 2/);
});

test('unsupported comparison schema fails closed', () => {
  const h = harness();
  assert.throws(() => h.run(`comparisonText({schema:'unknown'})`), /Unsupported comparison response/);
});

test('finding evidence drill-down exposes only recorded reviewer facts', () => {
  const h = reviewerHarness();
  const facts = factMap(h.context, {
    source: 'adapter/native-web-headers/1',
    rule: 'header/content-security-policy',
    verification: 'candidate',
    confidence: 0.875,
    external_id: 'finding-7',
    observed_at: '2026-09-24T07:30:00+00:00',
    evidence_sha256: 'a'.repeat(64),
    evidence: {method: 'HEAD', http_status: 200, scope: 'this response only', absent_header: 'content-security-policy'},
  });
  assert.equal(facts.Source, 'adapter/native-web-headers/1');
  assert.equal(facts.Rule, 'header/content-security-policy');
  assert.equal(facts.Verification, 'candidate');
  assert.equal(facts.Confidence, '87.5%');
  assert.equal(facts['External ID'], 'finding-7');
  assert.equal(facts.Method, 'HEAD');
  assert.equal(facts['HTTP status'], '200');
  assert.equal(facts['Scope note'], 'this response only');
  assert.equal(facts['Absent header'], 'content-security-policy');
  assert.equal(facts['Evidence SHA-256'], 'a'.repeat(64));
});

test('finding evidence drill-down keeps raw synthetic proof unchanged', () => {
  const h = reviewerHarness();
  const evidence = {
    environment: 'ephemeral synthetic loopback lab',
    demonstrated_impact: 'unauthenticated read of designated synthetic records',
    control_status: 401,
    record_status: 200,
    credentials_sent: false,
    customer_data_sampled: false,
  };
  const finding = {
    source: 'native/0.1.0',
    rule: 'lab/missing-authorization',
    verification: 'verified_in_lab',
    evidence,
    evidence_sha256: 'c'.repeat(64),
  };
  h.context.render({findings: [finding]});
  const card = h.cards()[0];
  const panel = card.querySelector('.reviewer-evidence');
  const raw = card.querySelector('pre');
  assert.ok(panel, 'structured reviewer panel missing');
  assert.ok(card.children.indexOf(panel) < card.children.indexOf(raw), 'structured review should precede raw JSON');
  assert.equal(raw.textContent, JSON.stringify(evidence, null, 2));
  const text = JSON.stringify(panel);
  assert.match(text, /ephemeral synthetic loopback lab/);
  assert.match(text, /Credentials sent/);
  assert.match(text, /Customer data sampled/);
});

test('finding evidence drill-down treats recorded values as text', () => {
  const h = reviewerHarness();
  const malicious = '<img src=x onerror=alert(1)>';
  h.context.render({findings: [{source: malicious, rule: 'safe/rule', verification: 'candidate', evidence: {}, evidence_sha256: 'd'.repeat(64)}]});
  const panel = h.cards()[0].querySelector('.reviewer-evidence');
  assert.match(JSON.stringify(panel), /<img src=x onerror=alert\(1\)>/);
  assert.doesNotMatch(reviewerScript, /\.innerHTML\s*=/);
});

test('coverage review keeps every non-success state visible', () => {
  const h = coverageHarness();
  h.context.render(coverageReport());
  const text = h.coverage.textContent;
  assert.match(text, /4 checks · 1 completed · 1 inconclusive · 1 skipped · 1 error · 0 unknown/);
  assert.match(text, /http_baseline — COMPLETED · result observed only/);
  assert.match(text, /native-web-headers — INCONCLUSIVE/);
  assert.match(text, /coverage 2\/3/);
  assert.match(text, /notes one route excluded/);
  assert.match(text, /controlled_verification — SKIPPED/);
  assert.match(text, /scanner-x — ERROR/);
  assert.match(text, /completed means the check executed; it does not mean the target is safe/);
});

test('coverage review fails closed for missing or unknown status', () => {
  const h = coverageHarness();
  const text = h.context.reviewerCoverageText({checks: [{tool: 'alpha'}, {tool: 'beta', status: 'mystery'}], limitations: []});
  assert.match(text, /2 checks · 0 completed · 0 inconclusive · 0 skipped · 0 error · 2 unknown/);
  assert.match(text, /alpha — UNKNOWN/);
  assert.match(text, /beta — UNKNOWN/);
  assert.doesNotMatch(text, /alpha — COMPLETED/);
});

test('coverage review preserves the raw coverage record verbatim at the end', () => {
  const h = coverageHarness();
  const value = coverageReport();
  const expected = JSON.stringify({checks: value.checks, limitations: value.limitations}, null, 2);
  const text = h.context.reviewerCoverageText(value);
  assert.ok(text.endsWith(expected));
  assert.match(text, /Recorded limitations:/);
  assert.match(text, /Authentication coverage was not executed\./);
});

test('coverage review renders recorded strings as text and never uses innerHTML', () => {
  const h = coverageHarness();
  const malicious = '<img src=x onerror=alert(1)>';
  h.context.render({findings: [], checks: [{tool: malicious, status: 'skipped', reason: malicious}], limitations: [malicious]});
  assert.match(h.coverage.textContent, /<img src=x onerror=alert\(1\)>/);
  assert.doesNotMatch(reviewerScript, /\.innerHTML\s*=/);
});

test('AI review keeps not-requested state explicit with no fallback implication', () => {
  const h = aiHarness();
  const text = h.context.reviewerAiText({ai: {
    status: 'not_requested', provider: null, model: null,
    processing_policy: 'local_only', cloud_processing_approved: false,
  }});
  assert.match(text, /Status: NOT REQUESTED/);
  assert.match(text, /Provider: not used/);
  assert.match(text, /Model: not used/);
  assert.match(text, /Inference: not requested/);
  assert.match(text, /no alternate provider is substituted/);
});

test('AI review separates cloud approval from reported execution location and usage', () => {
  const h = aiHarness();
  const value = {
    status: 'completed', provider: 'ollama', model: 'fixture-model',
    processing_policy: 'cloud_allowed', cloud_processing_approved: true,
    data_disclosure: 'Minimized recorded fields only.',
    usage: {
      provider: 'ollama', model: 'fixture-model', processing_policy: 'cloud_allowed',
      execution_location: 'local_reported', cloud_processing_approved: true,
      inference_attempts: 2, responses_received: 1,
      prompt_tokens_reported: null, output_tokens_reported: 19, billing_cost: null,
    },
  };
  const text = h.context.reviewerAiText({ai: value});
  assert.match(text, /Processing policy: cloud allowed/);
  assert.match(text, /Cloud processing approved: yes/);
  assert.match(text, /Reported execution location: local reported/);
  assert.match(text, /Inference attempts: 2/);
  assert.match(text, /Responses received: 1/);
  assert.match(text, /Prompt tokens reported: not reported/);
  assert.match(text, /Output tokens reported: 19/);
  assert.match(text, /approval does not prove where inference actually ran/);
  assert.match(text, /Billing cost: not estimated by the workbench/);
});

test('AI review fails closed for unknown status, policy, location and invalid counters', () => {
  const h = aiHarness();
  const text = h.context.reviewerAiText({ai: {
    status: 'success-ish', processing_policy: 'mystery',
    usage: {execution_location: 'somewhere', inference_attempts: -1, responses_received: 1.5},
  }});
  assert.match(text, /Status: UNKNOWN/);
  assert.match(text, /Processing policy: unknown/);
  assert.match(text, /Reported execution location: unknown/);
  assert.match(text, /Inference attempts: not reported/);
  assert.match(text, /Responses received: not reported/);
});

test('AI review preserves raw record and renders recorded strings as text', () => {
  const h = aiHarness();
  const malicious = '<img src=x onerror=alert(1)>';
  const value = {status: 'unavailable', provider: malicious, error_type: malicious};
  h.context.render({findings: [], checks: [], limitations: [], ai: value});
  assert.match(h.ai.textContent, /<img src=x onerror=alert\(1\)>/);
  assert.ok(h.ai.textContent.endsWith(JSON.stringify(value, null, 2)));
  assert.doesNotMatch(reviewerScript, /\.innerHTML\s*=/);
});
