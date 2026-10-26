import { spawn } from 'node:child_process';
import { mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import net from 'node:net';

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, '..', '..');
const python = process.env.PYTHON || 'python';
const chrome = process.env.CHROME_BIN || 'google-chrome';
const workRoot = await mkdtemp(join(tmpdir(), 'secscan_ai-browser-e2e-'));
const dataDir = join(workRoot, 'data');
const profileDir = join(workRoot, 'chrome');
const children = [];

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function freePort() {
  return await new Promise((resolvePort, reject) => {
    const server = net.createServer();
    server.on('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const address = server.address();
      const port = address && typeof address === 'object' ? address.port : null;
      server.close((error) => error ? reject(error) : resolvePort(port));
    });
  });
}

async function waitFor(check, label, timeoutMs = 15000, intervalMs = 80) {
  const end = Date.now() + timeoutMs;
  let lastError;
  while (Date.now() < end) {
    try {
      const value = await check();
      if (value) return value;
    } catch (error) {
      lastError = error;
    }
    await new Promise((resolveWait) => setTimeout(resolveWait, intervalMs));
  }
  throw new Error(`Timed out waiting for ${label}${lastError ? `: ${lastError.message}` : ''}`);
}

function terminate(child) {
  if (!child || child.exitCode !== null || child.killed) return;
  try { child.kill('SIGTERM'); } catch {}
}

let workbench;
let browser;
let socket;
try {
  const appPort = await freePort();
  const debugPort = await freePort();
  let stdout = '';
  let stderr = '';
  workbench = spawn(python, ['-u', '-m', 'workbench', '--port', String(appPort), '--data-dir', dataDir], {
    cwd: repoRoot,
    stdio: ['ignore', 'pipe', 'pipe'],
    env: {...process.env, PYTHONUNBUFFERED: '1'},
  });
  children.push(workbench);
  workbench.stdout.setEncoding('utf8');
  workbench.stderr.setEncoding('utf8');
  workbench.stdout.on('data', (chunk) => { stdout += chunk; });
  workbench.stderr.on('data', (chunk) => { stderr += chunk; });

  const launchUrl = await waitFor(() => {
    const match = stdout.match(/Open locally:\s+(http:\/\/127\.0\.0\.1:\d+\/#token=[^\s]+)/);
    if (match) return match[1];
    if (workbench.exitCode !== null) throw new Error(`workbench exited ${workbench.exitCode}: ${stderr}`);
    return null;
  }, 'private workbench launch URL');
  const launchToken = new URL(launchUrl).hash.slice('#token='.length);
  assert(launchToken.length >= 20, 'launch token was not parsed');

  const chromeArgs = [
    '--headless=new',
    '--no-sandbox',
    '--disable-gpu',
    '--disable-dev-shm-usage',
    '--disable-background-networking',
    '--disable-component-update',
    '--disable-default-apps',
    '--disable-sync',
    '--metrics-recording-only',
    '--no-first-run',
    '--safebrowsing-disable-auto-update',
    `--user-data-dir=${profileDir}`,
    `--remote-debugging-port=${debugPort}`,
    'about:blank',
  ];
  browser = spawn(chrome, chromeArgs, {stdio: ['ignore', 'pipe', 'pipe']});
  children.push(browser);
  let chromeError = '';
  browser.stderr.setEncoding('utf8');
  browser.stderr.on('data', (chunk) => { chromeError += chunk; });

  const version = await waitFor(async () => {
    if (browser.exitCode !== null) throw new Error(`chrome exited ${browser.exitCode}: ${chromeError}`);
    const response = await fetch(`http://127.0.0.1:${debugPort}/json/version`).catch(() => null);
    if (!response?.ok) return null;
    return response.json();
  }, 'Chrome DevTools endpoint', 30000, 100);
  assert(version.webSocketDebuggerUrl, 'Chrome DevTools websocket URL missing');

  socket = new WebSocket(version.webSocketDebuggerUrl);
  await new Promise((resolveOpen, reject) => {
    const timer = setTimeout(() => reject(new Error('DevTools websocket open timed out')), 5000);
    socket.addEventListener('open', () => { clearTimeout(timer); resolveOpen(); }, {once: true});
    socket.addEventListener('error', () => { clearTimeout(timer); reject(new Error('DevTools websocket failed')); }, {once: true});
  });

  let nextId = 0;
  const pending = new Map();
  const runtimeExceptions = [];
  socket.addEventListener('message', (event) => {
    const message = JSON.parse(String(event.data));
    if (message.id && pending.has(message.id)) {
      const {resolve: resolveCall, reject: rejectCall} = pending.get(message.id);
      pending.delete(message.id);
      if (message.error) rejectCall(new Error(`${message.error.message || 'CDP error'} (${message.error.code || 'unknown'})`));
      else resolveCall(message.result || {});
      return;
    }
    if (message.method === 'Runtime.exceptionThrown') runtimeExceptions.push(message.params?.exceptionDetails || {});
  });

  function cdp(method, params = {}, sessionId) {
    const id = ++nextId;
    return new Promise((resolveCall, rejectCall) => {
      pending.set(id, {resolve: resolveCall, reject: rejectCall});
      socket.send(JSON.stringify({id, method, params, ...(sessionId ? {sessionId} : {})}));
      setTimeout(() => {
        if (!pending.has(id)) return;
        pending.delete(id);
        rejectCall(new Error(`CDP command timed out: ${method}`));
      }, 7000);
    });
  }

  const {targetId} = await cdp('Target.createTarget', {url: 'about:blank'});
  const {sessionId} = await cdp('Target.attachToTarget', {targetId, flatten: true});
  await cdp('Page.enable', {}, sessionId);
  await cdp('Runtime.enable', {}, sessionId);
  await cdp('Accessibility.enable', {}, sessionId);

  async function evaluate(expression) {
    const result = await cdp('Runtime.evaluate', {expression, returnByValue: true, awaitPromise: true}, sessionId);
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.text || 'Runtime evaluation failed');
    return result.result?.value;
  }

  await cdp('Page.navigate', {url: launchUrl}, sessionId);
  await waitFor(async () => (await evaluate("document.readyState === 'complete' && document.getElementById('connection')?.textContent === 'Local session connected'")) === true, 'authenticated UI unlock');
  assert(await evaluate('location.hash === ""'), 'launch token fragment was not removed from the address bar');
  assert(await evaluate(`!document.body.innerText.includes(${JSON.stringify(launchToken)})`), 'launch token appeared in rendered page text');
  assert(await evaluate("document.getElementById('controls').disabled === false"), 'assessment controls stayed disabled after unlock');

  const viewportWidths = [1440, 768, 390];
  for (const width of viewportWidths) {
    await cdp('Emulation.setDeviceMetricsOverride', {width, height: 900, deviceScaleFactor: 1, mobile: width < 600}, sessionId);
    await new Promise((resolveWait) => setTimeout(resolveWait, 100));
    const layout = await evaluate('({innerWidth: window.innerWidth, scrollWidth: document.documentElement.scrollWidth})');
    assert(layout.scrollWidth <= layout.innerWidth + 1, `horizontal overflow at ${width}px: ${layout.scrollWidth} > ${layout.innerWidth}`);
  }
  await cdp('Emulation.setDeviceMetricsOverride', {width: 1280, height: 900, deviceScaleFactor: 1, mobile: false}, sessionId);

  const axTree = await cdp('Accessibility.getFullAXTree', {}, sessionId);
  const interactiveRoles = new Set(['button', 'checkbox', 'combobox', 'link', 'radio', 'textbox']);
  const unnamed = (axTree.nodes || []).filter((node) => {
    if (node.ignored || !interactiveRoles.has(node.role?.value)) return false;
    const focusable = (node.properties || []).some((property) => property.name === 'focusable' && property.value?.value === true);
    return focusable && !(node.name?.value || '').trim();
  });
  assert(unnamed.length === 0, `focusable accessible controls without names: ${unnamed.length}`);

  await evaluate("document.querySelector('.brand').focus()");
  const visited = new Set();
  for (let index = 0; index < 90; index += 1) {
    await cdp('Input.dispatchKeyEvent', {type: 'keyDown', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9, nativeVirtualKeyCode: 9}, sessionId);
    await cdp('Input.dispatchKeyEvent', {type: 'keyUp', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9, nativeVirtualKeyCode: 9}, sessionId);
    const focus = await evaluate("document.activeElement?.id || (document.activeElement?.classList?.contains('nav-link') ? 'nav-link' : document.activeElement?.tagName?.toLowerCase())");
    if (focus) visited.add(focus);
  }
  const keyboardTargets = ['target-type', 'authorization', 'authorized', 'start', 'refresh', 'adapter-kind', 'adapter-plan'];
  for (const required of keyboardTargets) {
    assert(visited.has(required), `keyboard tab order did not reach #${required}`);
  }

  await evaluate(`(() => {
    const mode = document.querySelector('input[name="mode"][value="verify"]');
    mode.checked = true;
    mode.dispatchEvent(new Event('change', {bubbles: true}));
    document.getElementById('authorization').value = 'Browser E2E owned synthetic fixture';
    document.getElementById('authorized').checked = true;
    document.getElementById('approve').checked = true;
    document.getElementById('scan-form').requestSubmit();
    return true;
  })()`);

  await waitFor(async () => (await evaluate("document.getElementById('integrity').textContent.startsWith('Finalized report SHA-256')")) === true, 'finalized synthetic assessment', 20000, 120);
  assert(Number(await evaluate("document.getElementById('count-verified').textContent")) >= 1, 'owned synthetic verification did not render a verified lab finding');
  assert((await evaluate("document.getElementById('verdict').textContent")).includes('verified in synthetic lab only'), 'UI did not preserve synthetic-only verdict wording');
  assert(await evaluate("document.getElementById('history-list').textContent.includes('lab')"), 'finalized run did not appear in browser history UI');
  assert(await evaluate("document.getElementById('history-list').textContent.includes('Status COMPLETED')"), 'run history did not expose terminal execution state separately from verdict');
  assert(await evaluate("document.getElementById('history-list').textContent.includes('Mode verify')"), 'run history did not expose recorded assessment mode');
  assert(await evaluate("document.getElementById('run-status').textContent.includes('durable final report')"), 'selected finalized run did not expose durable persistence state');
  assert(await evaluate("globalThis.reviewerDurabilityState({status:'completed', durability:{status:'not_durable'}}) === 'memory_only'"), 'memory-only durability did not fail closed in reviewer classification');
  assert(await evaluate("globalThis.reviewerRunHistoryText({status:'interrupted', verdict:'inconclusive', mode:'verify'}).includes('Status INTERRUPTED')"), 'interrupted history state was not reviewable');
  // Exercise the existing approved metadata adapter -> report path on an owned directory.
  const projectDir = join(workRoot, 'owned-project');
  await mkdir(projectDir);
  await writeFile(join(projectDir, 'README.md'), 'Owned browser integration fixture. No secrets.\n');
  await evaluate(`(() => {
    document.getElementById('adapter-kind').value = 'project';
    document.getElementById('adapter-kind').dispatchEvent(new Event('change', {bubbles:true}));
    document.getElementById('adapter-asset').value = 'browser-owned-project';
    document.getElementById('adapter-target').value = ${JSON.stringify(projectDir)};
    document.getElementById('adapter-plan').click();
    return true;
  })()`);
  await waitFor(() => evaluate("!document.getElementById('adapter-approve').disabled"), 'adapter authority preview');
  assert(await evaluate("document.getElementById('adapter-execute').disabled"), 'planning alone enabled execution');
  assert(await evaluate("document.getElementById('adapter-target').disabled"), 'planned scope was editable');
  await evaluate("document.getElementById('adapter-approve').click()");
  await waitFor(() => evaluate("!document.getElementById('adapter-execute').disabled"), 'exact plan approval');
  await evaluate("document.getElementById('adapter-execute').click()");
  await waitFor(() => evaluate("!document.getElementById('adapter-report').disabled"), 'owned adapter receipt');
  assert(await evaluate("document.getElementById('adapter-preview').textContent.includes('Lifecycle state: COMPLETED')"), 'adapter did not render completed lifecycle state');
  assert(await evaluate("document.getElementById('adapter-preview').textContent.includes('Durable receipt: present')"), 'adapter did not render durable receipt boundary');
  await evaluate("document.getElementById('adapter-report').click()");
  await waitFor(() => evaluate("!document.getElementById('adapter-open-report').disabled"), 'linked candidate report');
  await evaluate("document.getElementById('adapter-open-report').click()");
  await waitFor(() => evaluate("document.getElementById('run-status').textContent.includes('project://') && !document.getElementById('export-json').disabled"), 'linked report review');
  await waitFor(() => evaluate("document.activeElement.id === 'verdict'"), 'linked report conclusion focus');
  assert(await evaluate("Number(document.getElementById('count-verified').textContent) === 0"), 'adapter observations were promoted to verified');
  assert(await evaluate("!document.getElementById('use-ai').checked"), 'report review enabled AI');
  assert(await evaluate(`!document.body.innerText.includes(${JSON.stringify(launchToken)})`), 'token leaked during adapter review');
  assert(runtimeExceptions.length === 0, `browser runtime exceptions observed: ${runtimeExceptions.length}`);

  const summary = {
    schema: 'secscan_ai.browser-e2e/v1',
    browser: version.Browser || 'unknown',
    protocol: version['Protocol-Version'] || 'unknown',
    loopback_server: true,
    token_fragment_removed: true,
    viewport_widths: viewportWidths,
    keyboard_reached: keyboardTargets,
    unnamed_focusable_controls: 0,
    history_lifecycle_visible: true,
    durable_review_visible: true,
    memory_only_classification_tested: true,
    approved_project_adapter_completed: true,
    linked_report_reviewed: true,
    linked_report_focus_verified: true,
    synthetic_assessment_completed: true,
    verified_lab_finding_rendered: true,
    runtime_exceptions: 0,
    external_target_contacted: false,
    live_model_used: false,
  };
  console.log(JSON.stringify(summary, null, 2));
} finally {
  if (socket && socket.readyState === WebSocket.OPEN) socket.close();
  terminate(browser);
  terminate(workbench);
  await new Promise((resolveWait) => setTimeout(resolveWait, 250));
  for (const child of children) terminate(child);
  await rm(workRoot, {recursive: true, force: true});
}