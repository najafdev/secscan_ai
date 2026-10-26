'use strict';
(() => {
  const byId = (id) => document.getElementById(id);
  const panel = byId('adapter-workspace');
  if (!panel) return;

  let plan = null;
  let executing = false;
  let pendingAction = false;
  let approved = false;
  let lastStatus = null;
  let linkedReport = null;

  async function request(path, body) {
    const token = sessionStorage.getItem('secscan_ai-token') || '';
    const response = await fetch(path, {
      method: body === undefined ? 'GET' : 'POST',
      headers: {
        Authorization: 'Bearer ' + token,
        ...(body === undefined ? {} : {'Content-Type': 'application/json'}),
      },
      ...(body === undefined ? {} : {body: JSON.stringify(body)}),
    });
    const payload = await response.json().catch(() => ({error: 'Local adapter service unavailable'}));
    if (!response.ok) throw new Error(payload.error || 'Adapter request failed');
    return payload;
  }

  function setStatus(text, error = false) {
    const node = byId('adapter-status');
    node.textContent = text;
    node.className = error ? 'help adapter-error' : 'help';
  }

  function kind() { return byId('adapter-kind').value; }
  function adapterId() {
    if (kind() === 'project') return 'native-project-metadata';
    if (kind() === 'semgrep') return 'semgrep-project-local';
    return 'native-web-headers';
  }

  function buildRequest() {
    const assetKey = byId('adapter-asset').value.trim();
    const target = byId('adapter-target').value.trim();
    if (!assetKey || !target) throw new Error('Provide an engagement asset key and exact target.');
    if (kind() === 'project') {
      return {root: target, asset_key: assetKey, max_files: 1000, max_depth: 12, timeout_seconds: 30};
    }
    if (kind() === 'semgrep') {
      return {root: target, asset_key: assetKey, max_files: 250, max_depth: 12, timeout_seconds: 90, max_target_bytes: 500000};
    }
    return {target, asset_key: assetKey, timeout_seconds: 15};
  }

  function freeze(value) {
    byId('adapter-kind').disabled = value;
    byId('adapter-asset').disabled = value;
    byId('adapter-target').disabled = value;
  }

  function resetPlan() {
    if (executing || pendingAction || lastStatus === 'executing' || lastStatus === 'unknown') return;
    plan = null;
    approved = false;
    lastStatus = null;
    linkedReport = null;
    byId('adapter-recheck').disabled = true;
    byId('adapter-open-report').disabled = true;
    freeze(false);
    byId('adapter-plan').disabled = false;
    byId('adapter-approve').disabled = true;
    byId('adapter-execute').disabled = true;
    byId('adapter-cancel').disabled = true;
    byId('adapter-report').disabled = true;
    byId('adapter-reset').disabled = true;
    byId('adapter-preview').textContent = 'No reviewed adapter plan yet.';
    setStatus('Plan first. Execution remains disabled until the exact minimized authority preview is approved.');
    syncTargetLabel();
  }

  function syncTargetLabel() {
    const selected = kind();
    const project = selected === 'project' || selected === 'semgrep';
    byId('adapter-target-label').textContent = project ? 'Project directory on this machine' : 'Exact authorized URL';
    byId('adapter-target').placeholder = project ? '/path/to/authorized/project' : 'https://authorized.example';
    if (selected === 'project') {
      byId('adapter-target-help').textContent = 'Metadata-only: filenames may be inspected within the displayed limits. File contents are not read and symlinks are not followed.';
    } else if (selected === 'semgrep') {
      byId('adapter-target-help').textContent = 'Pinned Semgrep CE: project content is mounted read-only into a network-disabled container using repository-authored local rules. The exact image must already be installed; execution never auto-pulls it.';
    } else {
      byId('adapter-target-help').textContent = 'Passive bounded web check: one HEAD request, no redirects and no response body.';
    }
  }

  function assertCurrent(record) {
    if (!record || !plan || record.id !== plan.id || record.plan_sha256 !== plan.planSha256) {
      throw new Error('Returned adapter record does not match the reviewed plan. No execution is enabled.');
    }
  }

  function reportable(record) {
    return record.status === 'completed' && record.receipt && record.receipt.result &&
      Array.isArray(record.receipt.result.findings) && record.receipt.result.coverage;
  }

  function lifecycleStatus(value) {
    return ['planned', 'approved', 'executing', 'completed', 'failed', 'cancelled', 'interrupted'].includes(value) ? value : 'unknown';
  }

  function recordedNumber(value) {
    return Number.isInteger(value) && value >= 0 ? String(value) : 'not reported';
  }

  function previewRecord(record) {
    return {
      id: record && record.id,
      status: record && record.status,
      declaration: record && record.declaration,
      request_summary: record && record.request_summary,
      plan_sha256: record && record.plan_sha256,
      outcome: record && record.outcome ? record.outcome : null,
      usage: record && record.receipt ? record.receipt.usage : null,
      candidate_findings: record && record.receipt && record.receipt.result && Array.isArray(record.receipt.result.findings) ? record.receipt.result.findings.length : null,
      coverage: record && record.receipt && record.receipt.result ? record.receipt.result.coverage : null,
    };
  }

  function adapterReviewText(record) {
    const status = lifecycleStatus(record && record.status);
    const declaration = record && record.declaration && typeof record.declaration === 'object' ? record.declaration : {};
    const declaredAdapter = declaration.adapter && typeof declaration.adapter === 'object' ? declaration.adapter : {};
    const limits = declaration.limits && typeof declaration.limits === 'object' ? declaration.limits : {};
    const receipt = record && record.receipt && typeof record.receipt === 'object' ? record.receipt : null;
    const result = receipt && receipt.result && typeof receipt.result === 'object' ? receipt.result : null;
    const usage = receipt && receipt.usage && typeof receipt.usage === 'object' ? receipt.usage : null;
    const outcomeCode = record && record.outcome && typeof record.outcome.code === 'string' && record.outcome.code.trim() ? record.outcome.code.trim() : 'not recorded';
    const adapter = typeof record?.adapter_id === 'string' && record.adapter_id.trim() ? record.adapter_id.trim() :
      (typeof declaredAdapter.id === 'string' && declaredAdapter.id.trim() ? declaredAdapter.id.trim() : 'not recorded');
    const planDigest = typeof record?.plan_sha256 === 'string' && /^[a-f0-9]{64}$/.test(record.plan_sha256) ? record.plan_sha256 : 'not recorded';
    const lines = [
      'Adapter lifecycle review',
      'Lifecycle state: ' + status.toUpperCase(),
      'Adapter: ' + adapter,
      'Plan digest: ' + planDigest,
      'Max objects: ' + recordedNumber(limits.max_objects),
      'Max requests: ' + recordedNumber(limits.max_requests),
      'Timeout seconds: ' + recordedNumber(limits.timeout_seconds),
      'Recorded outcome: ' + outcomeCode,
      'Authority boundary: only the exact reviewed plan digest can be approved; lifecycle state never expands adapter scope, effects, requests or time limits.',
    ];

    if (status === 'planned') {
      lines.push('Approval: not granted. Execution remains disabled until the exact plan digest is approved.');
    } else if (status === 'approved') {
      lines.push('Approval: exact plan digest approved. Execution has not yet been confirmed.');
    } else if (status === 'executing') {
      lines.push('Approval: exact plan digest approved. Execution is in progress; Stop is a cancellation request until a terminal state is confirmed.');
    } else if (status === 'completed') {
      lines.push(receipt ?
        'Durable receipt: present. Completion describes adapter execution only; returned findings remain candidate observations until separately verified.' :
        'Durable receipt: not recorded. Do not treat this completed state as reportable success; check run status.');
    } else if (status === 'cancelled') {
      lines.push('Terminal state: cancelled. No successful receipt or verification claim is inferred.');
    } else if (status === 'failed') {
      lines.push('Terminal state: failed. No successful receipt or verification claim is inferred.');
    } else if (status === 'interrupted') {
      lines.push('Terminal state: interrupted. Execution may have started, but durable completion is not claimed; do not automatically retry.');
    } else {
      lines.push('Lifecycle state: unknown. Fail closed: execution, cancellation and durable completion are not inferred from an unrecognized state.');
    }

    if (usage) {
      lines.push(
        'Objects tested: ' + recordedNumber(usage.objects_tested),
        'Network requests: ' + recordedNumber(usage.network_requests),
        'Elapsed milliseconds: ' + recordedNumber(usage.elapsed_ms)
      );
    }
    if (result) {
      const findingCount = Array.isArray(result.findings) ? result.findings.length : null;
      lines.push('Candidate findings recorded: ' + (findingCount === null ? 'not reported' : String(findingCount)));
      if (result.coverage && typeof result.coverage === 'object') {
        lines.push('Coverage record: present; review the recorded coverage and limitations before drawing conclusions.');
      }
    }

    lines.push('', 'Recorded lifecycle preview:', JSON.stringify(previewRecord(record), null, 2));
    return lines.join('\n');
  }

  function outcome(record) {
    assertCurrent(record);
    show(record);
    lastStatus = record.status;
    const available = reportable(record);
    byId('adapter-report').disabled = !available || !!linkedReport;
    byId('adapter-recheck').disabled = false;
    byId('adapter-reset').disabled = record.status === 'executing';
    byId('adapter-cancel').disabled = record.status !== 'executing';
    if (available) {
      const status = record.receipt.result.status;
      const detail = status === 'completed' ? 'Review actual coverage; no findings does not mean safe.' :
        'Adapter result: ' + (status || 'unknown') + '. Coverage may be incomplete; review limitations.';
      setStatus('Execution completed with a durable receipt. ' + detail + ' Add to report preserves candidate observations without rerunning tools or AI.');
    } else if (record.status === 'completed') {
      setStatus('Completed state has no usable receipt. Report linking is disabled; check run status.', true);
    } else {
      setStatus('Adapter state: ' + record.status + '. ' + (record.status === 'executing' ?
        'It has not stopped. Use Stop or Check run status.' : 'No successful receipt is claimed. Review the recorded outcome.'), record.status !== 'executing');
    }
  }

  function unknownOutcome() {
    lastStatus = 'unknown';
    byId('adapter-report').disabled = true;
    byId('adapter-reset').disabled = true;
    byId('adapter-recheck').disabled = false;
    byId('adapter-cancel').disabled = false;
    setStatus('Adapter outcome unknown. A lost connection does not prove execution stopped. Use Check run status; execution will not be retried automatically.', true);
  }

  function show(record) {
    byId('adapter-preview').textContent = adapterReviewText(record);
  }

  globalThis.adapterLifecycleReviewText = adapterReviewText;

  byId('adapter-kind').addEventListener('change', syncTargetLabel);
  byId('adapter-reset').addEventListener('click', resetPlan);

  byId('adapter-plan').addEventListener('click', async () => {
    if (plan || executing || pendingAction) return;
    try {
      const body = {adapter_id: adapterId(), request: buildRequest()};
      pendingAction = true;
      freeze(true);
      byId('adapter-plan').disabled = true;
      setStatus('Validating typed scope and operator authority. No adapter I/O is performed while planning.');
      const record = await request('/api/adapters/plan', body);
      if (!record || record.status !== 'planned' || !/^[a-f0-9]{32}$/.test(record.id) || !/^[a-f0-9]{64}$/.test(record.plan_sha256)) {
        throw new Error('No valid reviewed adapter plan was returned.');
      }
      plan = {id: record.id, planSha256: record.plan_sha256, adapterId: body.adapter_id, request: body.request};
      freeze(true);
      byId('adapter-approve').disabled = false;
      byId('adapter-reset').disabled = false;
      show(record);
      setStatus('Plan ready. Review the minimized declaration and limits before approving the exact plan digest.');
    } catch (error) {
      byId('adapter-plan').disabled = false;
      freeze(false);
      setStatus(error.message, true);
    } finally { pendingAction = false; }
  });

  byId('adapter-approve').addEventListener('click', async () => {
    if (!plan || executing || pendingAction || approved) return;
    pendingAction = true;
    byId('adapter-reset').disabled = true;
    try {
      byId('adapter-approve').disabled = true;
      const record = await request('/api/adapter-runs/' + plan.id + '/approve', {plan_sha256: plan.planSha256});
      assertCurrent(record);
      if (record.status !== 'approved') throw new Error('Exact plan approval is not confirmed.');
      approved = true;
      show(record);
      byId('adapter-execute').disabled = false;
      setStatus('Exact plan approved. Execution will revalidate the same request before any I/O.');
    } catch (error) {
      byId('adapter-approve').disabled = false;
      setStatus(error.message, true);
    } finally {
      pendingAction = false;
      byId('adapter-reset').disabled = false;
    }
  });

  byId('adapter-execute').addEventListener('click', async () => {
    if (!plan || executing || pendingAction || !approved) return;
    approved = false;
    executing = true;
    lastStatus = 'executing';
    byId('adapter-execute').disabled = true;
    byId('adapter-reset').disabled = true;
    byId('adapter-cancel').disabled = false;
    setStatus('Executing the approved bounded adapter. Findings remain candidate observations until separately verified.');
    try {
      const record = await request('/api/adapter-runs/' + plan.id + '/execute', {adapter_id: plan.adapterId, request: plan.request});
      outcome(record);
    } catch (error) {
      try {
        const record = await request('/api/adapter-runs/' + plan.id);
        outcome(record);
      } catch (_) { unknownOutcome(); }
    } finally {
      executing = false;
      byId('adapter-cancel').disabled = !['executing', 'unknown'].includes(lastStatus);
      byId('adapter-reset').disabled = ['executing', 'unknown'].includes(lastStatus);
    }
  });

  byId('adapter-report').addEventListener('click', async () => {
    if (!plan || executing || pendingAction || lastStatus !== 'completed' || linkedReport || byId('adapter-report').disabled) return;
    pendingAction = true;
    byId('adapter-reset').disabled = true;
    byId('adapter-recheck').disabled = true;
    byId('adapter-report').disabled = true;
    try {
      const result = await request('/api/adapter-runs/' + plan.id + '/report', {});
      if (!/^[a-f0-9]{32}$/.test(result.id)) throw new Error('Invalid linked report identity.');
      linkedReport = result.id;
      byId('adapter-open-report').disabled = false;
      setStatus((result.created ? 'Candidate observations added to report ' : 'Adapter receipt is already linked to report ') + result.id + '. Use Run history to review or export it.');
    } catch (error) {
      byId('adapter-report').disabled = false;
      setStatus(error.message, true);
    } finally {
      pendingAction = false;
      byId('adapter-reset').disabled = false;
      byId('adapter-recheck').disabled = false;
    }
  });

  byId('adapter-cancel').addEventListener('click', async () => {
    if (!plan || !['executing', 'unknown'].includes(lastStatus) || byId('adapter-cancel').disabled) return;
    const current = plan;
    byId('adapter-cancel').disabled = true;
    try {
      await request('/api/adapter-runs/' + plan.id + '/cancel', {});
      if (plan !== current || !['executing', 'unknown'].includes(lastStatus)) return;
      setStatus('Cancellation requested. The adapter stops at its next enforced cancellation boundary.');
    } catch (error) {
      if (plan !== current || !['executing', 'unknown'].includes(lastStatus)) return;
      byId('adapter-cancel').disabled = false;
      setStatus(error.message + ' Stop is not confirmed; check run status.', true);
    }
  });

  byId('adapter-refresh').addEventListener('click', async () => {
    if (pendingAction || executing) return;
    const current = plan;
    try {
      const info = await request('/api/adapters');
      if (pendingAction || executing || plan !== current) return;
      const ids = info.adapters.map((item) => item.adapter.id).join(', ');
      setStatus('Reviewed execution registry: ' + ids + '. Optional scanner images are never downloaded by assessment execution.');
    } catch (error) {
      setStatus(error.message, true);
    }
  });

  byId('adapter-recheck').addEventListener('click', async () => {
    if (!plan || executing || pendingAction) return;
    pendingAction = true;
    byId('adapter-recheck').disabled = true;
    byId('adapter-reset').disabled = true;
    try { outcome(await request('/api/adapter-runs/' + plan.id)); }
    catch (_) { unknownOutcome(); }
    finally { pendingAction = false; }
  });

  byId('adapter-open-report').addEventListener('click', () => {
    if (!linkedReport || executing || pendingAction) return;
    document.dispatchEvent(new CustomEvent('secscan_ai:review-report', {detail: {id: linkedReport}}));
  });

  resetPlan();
})();
