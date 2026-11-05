/**
 * AgentDroid — Professional System Runtime & Interactive Explorer
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Mobile Drawer Navigation
  const menuBtn = document.getElementById('mobileMenuBtn');
  const closeBtn = document.getElementById('mobileDrawerClose');
  const mobileDrawer = document.getElementById('mobileDrawer');
  const drawerLinks = document.querySelectorAll('.mobile-drawer-link');

  function closeMobileDrawer() {
    if (!mobileDrawer) return;
    mobileDrawer.classList.remove('active');
    if (menuBtn) menuBtn.setAttribute('aria-expanded', 'false');
    document.body.style.overflow = '';
  }

  function openMobileDrawer() {
    if (!mobileDrawer) return;
    mobileDrawer.classList.add('active');
    if (menuBtn) menuBtn.setAttribute('aria-expanded', 'true');
    document.body.style.overflow = 'hidden';
  }

  if (menuBtn && mobileDrawer) {
    menuBtn.addEventListener('click', () => {
      const isOpen = mobileDrawer.classList.contains('active');
      if (isOpen) {
        closeMobileDrawer();
      } else {
        openMobileDrawer();
      }
    });

    if (closeBtn) {
      closeBtn.addEventListener('click', closeMobileDrawer);
    }

    drawerLinks.forEach(link => {
      link.addEventListener('click', closeMobileDrawer);
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && mobileDrawer.classList.contains('active')) {
        closeMobileDrawer();
      }
    });
  }

  // 2. Interactive Fleet Inspector Data & Controller
  const agentDatabase = {
    master: {
      name: 'Master Agent',
      category: 'core',
      role: 'DAG Task Decomposition & Dynamic Dependency Resolver',
      model: 'GPT-4o / Claude 3.5 Sonnet',
      permissions: 'System Orchestration, IPC Binder',
      latency: '< 45ms (Resolution)',
      code: `class MasterAgent @Inject constructor(
    private val dagScheduler: DAGScheduler,
    private val memoryManager: AgentMemoryManager
) : BaseAgent() {
    suspend fun planGoal(goalPrompt: String): TaskGraph {
        val decomposedNodes = llmProvider.decomposeIntoDAG(goalPrompt)
        return dagScheduler.buildTopologicalExecutionTree(decomposedNodes)
    }
}`
    },
    phone: {
      name: 'Phone Control Agent',
      category: 'automation',
      role: 'Native Android Accessibility UI Automation & Node Dispatcher',
      model: 'Local Ollama Llama 3 / Gemini Flash',
      permissions: 'android.permission.BIND_ACCESSIBILITY_SERVICE',
      latency: '~120ms (Gesture Dispatch)',
      code: `class PhoneControlAgent @Inject constructor(
    private val accessibilityService: AgentDroidAccessibilityService,
    private val stateVerifier: StateVerifier
) : BaseAgent() {
    suspend fun executeTap(nodeTarget: AccessibilityNodeInfo): Boolean {
        requireHumanApprovalIfHighRisk(nodeTarget)
        return accessibilityService.dispatchGestureClick(nodeTarget.boundsInScreen)
    }
}`
    },
    research: {
      name: 'Research Agent',
      category: 'intelligence',
      role: 'Real-Time Web Intelligence Extraction & Semantic Parsing',
      model: 'Perplexity Sonar / Llama 3 70B',
      permissions: 'android.permission.INTERNET',
      latency: '~650ms (Streamed)',
      code: `class ResearchAgent @Inject constructor(
    private val webEngine: HeadlessWebEngine,
    private val memory: WorkingMemory
) : BaseAgent() {
    suspend fun conductQuery(topic: String): SynthesizedReport {
        val rawCrawl = webEngine.fetchVerifiedSources(topic)
        return llmProvider.extractKeyClaimsAndEvidence(rawCrawl)
    }
}`
    },
    content: {
      name: 'Content Creation Agent',
      category: 'intelligence',
      role: 'Cross-Modal Document Drafting, Copywriting & Media Structuring',
      model: 'Claude 3.5 Sonnet / GPT-4o',
      permissions: 'Internal Shared Memory',
      latency: '~480ms (Streamed)',
      code: `class ContentCreationAgent @Inject constructor(
    private val contextBus: SharedTaskContext
) : BaseAgent() {
    suspend fun draftBrief(context: TaskContext): GeneratedDocument {
        val upstreamFindings = contextBus.getCompletedPayload("ResearchAgent")
        return llmProvider.generateFormattedMarkdown(upstreamFindings)
    }
}`
    },
    social: {
      name: 'Social Media Agent',
      category: 'automation',
      role: 'Multi-Platform Engagement Monitoring & Scheduled Dispatching',
      model: 'Groq Llama 3.1 70B / Mistral',
      permissions: 'Social App Intent Broadcasts',
      latency: '~180ms',
      code: `class SocialMediaAgent @Inject constructor(
    private val intentDispatcher: ActionDispatcher
) : BaseAgent() {
    suspend fun preparePost(platform: Platform, payload: PostPayload) {
        val intent = buildPlatformIntent(platform, payload)
        intentDispatcher.dispatchNativeIntent(intent)
    }
}`
    },
    productivity: {
      name: 'Productivity Agent',
      category: 'automation',
      role: 'Android Calendar, Reminder, Alarm & Content Provider Manager',
      model: 'Local Ollama Phi-3 Mini',
      permissions: 'READ_CALENDAR, WRITE_CALENDAR, SET_ALARM',
      latency: '< 60ms',
      code: `class ProductivityAgent @Inject constructor(
    private val calendarResolver: CalendarContentResolver
) : BaseAgent() {
    suspend fun detectConflicts(requestedTime: Instant): List<CalendarEvent> {
        return calendarResolver.queryOverlappingEvents(requestedTime)
    }
}`
    },
    communication: {
      name: 'Communication Agent',
      category: 'automation',
      role: 'Telephony Intent Triggering & Structured Message Drafting',
      model: 'Local Ollama Mistral 7B',
      permissions: 'SEND_SMS, READ_CONTACTS',
      latency: '< 80ms',
      code: `class CommunicationAgent @Inject constructor(
    private val telephonyManager: TelephonyIntentManager
) : BaseAgent() {
    suspend fun queueDraft(recipient: Contact, message: String) {
        verifySafetyPolicy(recipient)
        telephonyManager.createDraftIntent(recipient, message)
    }
}`
    },
    file: {
      name: 'File Management Agent',
      category: 'automation',
      role: 'Scoped Storage Organization, SQLite Archiving & Encryption',
      model: 'Local Ollama Embedded',
      permissions: 'Scoped Storage (MANAGE_MEDIA)',
      latency: '< 30ms (Local I/O)',
      code: `class FileManagementAgent @Inject constructor(
    private val database: AgentDroidDatabase
) : BaseAgent() {
    suspend fun archiveTaskArtifacts(taskId: String, data: ByteArray) {
        database.artifactDao().insertEncryptedBlob(taskId, data)
    }
}`
    },
    browser: {
      name: 'Browser Agent',
      category: 'intelligence',
      role: 'Automated Web Navigation, DOM Hierarchy Traversal & Forms',
      model: 'Gemini 1.5 Pro',
      permissions: 'Custom Tabs, android.permission.INTERNET',
      latency: '~320ms',
      code: `class BrowserAgent @Inject constructor(
    private val chromeCustomTabs: ChromeCustomTabsController
) : BaseAgent() {
    suspend fun navigateAndExtract(url: String): ParsedDOMSnapshot {
        return chromeCustomTabs.executeSession(url)
    }
}`
    },
    security: {
      name: 'Security & Policy Agent',
      category: 'security',
      role: 'Zero-Trust Gatekeeper, Prompt Injection Interceptor & Killswitch',
      model: 'Local FastBERT + Deterministic Rules',
      permissions: 'Hardware Keystore AES-256 GCM',
      latency: '< 15ms (Deterministic)',
      code: `class SecurityPolicyAgent @Inject constructor(
    private val killswitch: EmergencyKillswitch,
    private val keystore: SecurePreferencesManager
) : BaseAgent() {
    fun evaluateActionRisk(action: AgentAction): RiskVerdict {
        if (killswitch.isEngaged()) throw KillswitchActiveException()
        return if (action.isDestructive) RiskVerdict.REQUIRE_BIOMETRIC else RiskVerdict.ALLOW
    }
}`
    }
  };

  const agentItems = document.querySelectorAll('.fleet-agent-item');
  const filterTabs = document.querySelectorAll('.fleet-filter-tab');
  const panelTitle = document.getElementById('panelTitle');
  const panelDesc = document.getElementById('panelDesc');
  const specRole = document.getElementById('specRole');
  const specModel = document.getElementById('specModel');
  const specPerm = document.getElementById('specPerm');
  const panelCode = document.getElementById('panelCode');

  function updateFleetPanel(agentId) {
    const data = agentDatabase[agentId];
    if (!data) return;

    if (panelTitle) panelTitle.textContent = data.name;
    if (panelDesc) panelDesc.textContent = data.role;
    if (specRole) specRole.textContent = data.latency;
    if (specModel) specModel.textContent = data.model;
    if (specPerm) specPerm.textContent = data.permissions;
    if (panelCode) panelCode.textContent = data.code;

    agentItems.forEach(item => {
      item.classList.toggle('active', item.getAttribute('data-agent') === agentId);
    });
  }

  agentItems.forEach(item => {
    item.addEventListener('click', () => {
      const agentId = item.getAttribute('data-agent');
      updateFleetPanel(agentId);
    });
  });

  filterTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      filterTabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');

      const filter = tab.getAttribute('data-filter');
      agentItems.forEach(item => {
        const agentId = item.getAttribute('data-agent');
        const data = agentDatabase[agentId];
        if (filter === 'all' || (data && data.category === filter)) {
          item.style.display = 'flex';
        } else {
          item.style.display = 'none';
        }
      });
    });
  });

  // 3. Interactive DAG Simulation Engine
  const startSimBtn = document.getElementById('startSimBtn');
  const resetSimBtn = document.getElementById('resetSimBtn');
  const simConsole = document.getElementById('simConsole');
  const scenarioSelect = document.getElementById('scenarioSelect');
  const simNodes = document.querySelectorAll('.dag-step-node');

  const simScenarios = {
    social: [
      { step: 0, badge: 'PLANNING', title: 'Intent Decomposition', agent: 'MasterAgent', log: '[DAGScheduler] Parsed goal: "Analyze market trends and draft update". Building DAG.' },
      { step: 1, badge: 'RETRIEVAL', title: 'Web Analysis', agent: 'ResearchAgent', log: '[ResearchAgent] Executing web intelligence crawl. Ingested 5 data sources.' },
      { step: 2, badge: 'SYNTHESIS', title: 'Document Drafting', agent: 'ContentAgent', log: '[ContentAgent] Synthesizing brief via Ollama Llama 3 GGUF (8-bit quantization).' },
      { step: 3, badge: 'GOVERNANCE', title: 'Zero-Trust Gate', agent: 'SecurityAgent', log: '[SecurityAgent] Verifying prompt safety and verifying Keystore integrity.' },
      { step: 4, badge: 'AUTOMATION', title: 'Intent Execution', agent: 'PhoneControlAgent', log: '[PhoneControlAgent] Accessibility action verified. Target state achieved.' }
    ],
    productivity: [
      { step: 0, badge: 'PLANNING', title: 'Goal Parsing', agent: 'MasterAgent', log: '[DAGScheduler] Parsed goal: "Resolve calendar overlap and notify team".' },
      { step: 1, badge: 'RETRIEVAL', title: 'Provider Query', agent: 'ProductivityAgent', log: '[ProductivityAgent] Read Calendar ContentProvider. Found 1 conflict.' },
      { step: 2, badge: 'SYNTHESIS', title: 'Message Prep', agent: 'ContentAgent', log: '[ContentAgent] Drafted concise rescheduling note in volatile memory.' },
      { step: 3, badge: 'GOVERNANCE', title: 'Permission Check', agent: 'SecurityAgent', log: '[SecurityAgent] Keystore signature check passed. Dispatch allowed.' },
      { step: 4, badge: 'AUTOMATION', title: 'Intent Broadcast', agent: 'CommunicationAgent', log: '[CommunicationAgent] Telephony intent emitted via native Android OS.' }
    ]
  };

  let simInterval = null;

  function appendSimLog(text, colorClass = '') {
    if (!simConsole) return;
    const line = document.createElement('div');
    if (colorClass) line.className = colorClass;
    line.textContent = `[${new Date().toISOString().substring(11, 19)}] ${text}`;
    simConsole.appendChild(line);
    simConsole.scrollTop = simConsole.scrollHeight;
  }

  function resetSim() {
    if (simInterval) clearInterval(simInterval);
    simNodes.forEach(node => {
      node.classList.remove('active', 'done');
      const badge = node.querySelector('.step-badge');
      if (badge) badge.textContent = 'READY';
    });
    if (simConsole) {
      simConsole.innerHTML = '<div style="color: var(--text-tertiary);">Simulation runtime idle. Choose workflow and click "Execute DAG".</div>';
    }
  }

  if (resetSimBtn) {
    resetSimBtn.addEventListener('click', resetSim);
  }

  if (startSimBtn) {
    startSimBtn.addEventListener('click', () => {
      resetSim();
      const scenarioKey = scenarioSelect ? scenarioSelect.value : 'social';
      const steps = simScenarios[scenarioKey] || simScenarios.social;

      appendSimLog(`Initializing Directed Acyclic Graph: [${scenarioKey.toUpperCase()}]`, 'log-cyan');

      let currentStepIdx = 0;

      function runNextStep() {
        if (currentStepIdx >= steps.length) {
          appendSimLog('DAG completed successfully. 0 fake mocks. Output synced to Room SQLite.', 'log-green');
          return;
        }

        const stepData = steps[currentStepIdx];
        const node = simNodes[stepData.step];

        if (node) {
          node.classList.add('active');
          const badge = node.querySelector('.step-badge');
          if (badge) badge.textContent = 'RUNNING...';
        }

        appendSimLog(stepData.log, 'log-purple');

        setTimeout(() => {
          if (node) {
            node.classList.remove('active');
            node.classList.add('done');
            const badge = node.querySelector('.step-badge');
            if (badge) badge.textContent = 'RESOLVED ✓';
          }
          currentStepIdx++;
          runNextStep();
        }, 850);
      }

      runNextStep();
    });
  }

  // 4. Accordion Component
  const accordionItems = document.querySelectorAll('.accordion-item');
  accordionItems.forEach(item => {
    const btn = item.querySelector('.accordion-btn');
    if (btn) {
      btn.addEventListener('click', () => {
        const isOpen = item.classList.contains('open');
        accordionItems.forEach(i => i.classList.remove('open'));
        if (!isOpen) item.classList.add('open');
      });
    }
  });

  // 5. Copy Text Utility
  window.copyText = function(text, btnElement) {
    navigator.clipboard.writeText(text).then(() => {
      const origText = btnElement.innerText;
      btnElement.innerText = 'Copied';
      btnElement.style.borderColor = 'var(--color-success)';
      setTimeout(() => {
        btnElement.innerText = origText;
        btnElement.style.borderColor = '';
      }, 2000);
    }).catch(err => {
      console.error('Copy failed', err);
    });
  };
});
