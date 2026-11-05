/**
 * AgentDroid Official Website Interactions
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Mobile Menu Toggle
  const mobileToggle = document.getElementById('mobileToggle');
  const navLinks = document.getElementById('navLinks');

  if (mobileToggle && navLinks) {
    mobileToggle.addEventListener('click', () => {
      navLinks.classList.toggle('mobile-open');
    });
  }

  // 2. Agent Fleet Filter
  const filterBtns = document.querySelectorAll('.filter-btn');
  const agentCards = document.querySelectorAll('.agent-card');

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const filter = btn.getAttribute('data-filter');

      agentCards.forEach(card => {
        if (filter === 'all' || card.getAttribute('data-category') === filter) {
          card.style.display = 'block';
        } else {
          card.style.display = 'none';
        }
      });
    });
  });

  // 3. FAQ Accordion
  const faqItems = document.querySelectorAll('.faq-item');

  faqItems.forEach(item => {
    const question = item.querySelector('.faq-question');
    question.addEventListener('click', () => {
      const isOpen = item.classList.contains('open');
      faqItems.forEach(i => i.classList.remove('open'));
      if (!isOpen) {
        item.classList.add('open');
      }
    });
  });

  // 4. Copy-to-Clipboard Utility
  window.copyText = function(text, btnElement) {
    navigator.clipboard.writeText(text).then(() => {
      const originalText = btnElement.innerText;
      btnElement.innerText = 'Copied!';
      btnElement.classList.add('btn-copied');
      setTimeout(() => {
        btnElement.innerText = originalText;
        btnElement.classList.remove('btn-copied');
      }, 2000);
    }).catch(err => {
      console.error('Failed to copy: ', err);
    });
  };

  // 5. Interactive DAG Simulator
  const runDagBtn = document.getElementById('runDagBtn');
  const resetDagBtn = document.getElementById('resetDagBtn');
  const simConsole = document.getElementById('simConsole');
  const scenarioSelect = document.getElementById('scenarioSelect');
  const dagNodes = document.querySelectorAll('.dag-node');

  const scenarios = {
    social: {
      steps: [
        { nodeIndex: 0, title: 'Plan & Decompose', agent: 'MasterAgent', log: '[MasterAgent] Decomposing natural language command into 4 parallel tasks...', duration: 800 },
        { nodeIndex: 1, title: 'Competitor Intelligence', agent: 'ResearchAgent', log: '[ResearchAgent] Scraping X/Threads engagement metrics. Synthesized 4 trends.', duration: 1100 },
        { nodeIndex: 2, title: 'Content Generation', agent: 'ContentAgent', log: '[ContentAgent] Drafted 3 carousel tweets & 1 markdown summary via Ollama Llama 3.', duration: 900 },
        { nodeIndex: 3, title: 'Human Approval', agent: 'SecurityEngine', log: '[SecurityEngine] Zero-trust checkpoint: Policy approved automatically.', duration: 700 },
        { nodeIndex: 4, title: 'Accessibility Post', agent: 'PhoneControlAgent', log: '[PhoneControlAgent] Dispatched Accessibility Node tap on Compose -> Posted.', duration: 1000 }
      ]
    },
    calendar: {
      steps: [
        { nodeIndex: 0, title: 'Intent Parsing', agent: 'MasterAgent', log: '[MasterAgent] Parsing calendar conflict resolution request...', duration: 700 },
        { nodeIndex: 1, title: 'Read Calendar DB', agent: 'ProductivityAgent', log: '[ProductivityAgent] Read native calendar content provider: Found conflict at 3:00 PM.', duration: 900 },
        { nodeIndex: 2, title: 'Draft Reschedule', agent: 'ContentAgent', log: '[ContentAgent] Formulated polite reschedule proposal email.', duration: 800 },
        { nodeIndex: 3, title: 'Permission Check', agent: 'SecurityEngine', log: '[SecurityEngine] Verified external SMS/Email dispatch signature with Keystore.', duration: 700 },
        { nodeIndex: 4, title: 'Dispatch Message', agent: 'CommunicationAgent', log: '[CommunicationAgent] Sent SMS notification via Android telephony intent.', duration: 950 }
      ]
    }
  };

  let isSimRunning = false;

  function appendLog(message, className = '') {
    if (!simConsole) return;
    const line = document.createElement('div');
    line.className = className;
    line.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
    simConsole.appendChild(line);
    simConsole.scrollTop = simConsole.scrollHeight;
  }

  function resetDag() {
    isSimRunning = false;
    dagNodes.forEach(node => {
      node.classList.remove('active-node', 'completed-node');
      const status = node.querySelector('.node-status');
      if (status) status.textContent = 'READY';
    });
    if (simConsole) {
      simConsole.innerHTML = '<div class="t-dim">DAG Engine idle. Select scenario and click "Run Simulation".</div>';
    }
  }

  if (resetDagBtn) {
    resetDagBtn.addEventListener('click', resetDag);
  }

  if (runDagBtn) {
    runDagBtn.addEventListener('click', async () => {
      if (isSimRunning) return;
      isSimRunning = true;
      resetDag();

      const selectedScenario = scenarioSelect ? scenarioSelect.value : 'social';
      const scenario = scenarios[selectedScenario] || scenarios.social;

      appendLog(`Starting DAG Topological Execution for [${selectedScenario.toUpperCase()}]`, 't-cyan');

      for (let i = 0; i < scenario.steps.length; i++) {
        if (!isSimRunning) break;
        const step = scenario.steps[i];
        const node = dagNodes[step.nodeIndex];

        if (node) {
          node.classList.add('active-node');
          const status = node.querySelector('.node-status');
          if (status) status.textContent = 'EXECUTING...';
        }

        appendLog(step.log, 't-prompt');

        await new Promise(r => setTimeout(r, step.duration));

        if (node) {
          node.classList.remove('active-node');
          node.classList.add('completed-node');
          const status = node.querySelector('.node-status');
          if (status) status.textContent = 'COMPLETED ✓';
        }
      }

      if (isSimRunning) {
        appendLog('DAG execution finished successfully. All tasks committed to SQLite.', 't-success');
        isSimRunning = false;
      }
    });
  }
});
