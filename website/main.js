/**
 * HACKNOVA — Premium Web Platform Interactive Controller
 * Version: v2026.10.23
 * Core: Vanilla JS, Zero External Runtime Dependencies, 60fps Native Interactivity
 */

document.addEventListener('DOMContentLoaded', () => {
  initClipboard();
  initMobileMenu();
  initHeroInstallerTabs();
  initHeroConsoleTabs();
  initBentoProviderSwitcher();
  initRadarTooltips();
  initCodeTabs();
  initSimulator();
  initSpotlightEffect();
  initConsoleTypewriter();
});

/* ==========================================================================
   1. CLIPBOARD COPY UTILITY & TOAST NOTIFICATIONS
   ========================================================================== */
function initClipboard() {
  const copyButtons = document.querySelectorAll('.copy-btn');
  const toastContainer = document.getElementById('toastContainer');

  copyButtons.forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      const targetId = btn.getAttribute('data-target');
      let textToCopy = '';

      if (targetId) {
        const targetEl = document.getElementById(targetId);
        if (targetEl) {
          textToCopy = targetEl.value !== undefined ? targetEl.value : targetEl.innerText;
        }
      }

      if (!textToCopy) {
        textToCopy = btn.getAttribute('data-copy-text') || '';
      }

      if (textToCopy) {
        try {
          if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(textToCopy);
          } else {
            const textArea = document.createElement('textarea');
            textArea.value = textToCopy;
            textArea.style.position = 'fixed';
            textArea.style.left = '-999999px';
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
          }

          // Visual tactile feedback on button
          const originalHTML = btn.innerHTML;
          btn.classList.add('copied');
          btn.innerHTML = `
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            <span class="copy-label">Copied</span>
          `;

          showToast('Copied to clipboard');

          setTimeout(() => {
            btn.classList.remove('copied');
            btn.innerHTML = originalHTML;
          }, 2000);
        } catch (err) {
          console.error('Failed to copy to clipboard', err);
          showToast('Failed to copy text', true);
        }
      }
    });
  });

  function showToast(message, isError = false) {
    if (!toastContainer) return;
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `
      <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="${isError ? '#ef4444' : '#10b981'}" stroke-width="2.5">
        ${isError 
          ? '<circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line>' 
          : '<polyline points="20 6 9 17 4 12"></polyline>'
        }
      </svg>
      <span>${message}</span>
    `;

    toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.transition = 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)';
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      setTimeout(() => toast.remove(), 300);
    }, 2400);
  }
}

/* ==========================================================================
   2. MOBILE NAVIGATION MENU
   ========================================================================== */
function initMobileMenu() {
  const menuBtn = document.getElementById('mobileMenuBtn');
  const drawer = document.getElementById('mobileDrawer');
  const links = document.querySelectorAll('.mobile-nav-link');

  if (!menuBtn || !drawer) return;

  menuBtn.addEventListener('click', () => {
    const isOpen = drawer.classList.toggle('open');
    menuBtn.setAttribute('aria-expanded', isOpen);
  });

  links.forEach(link => {
    link.addEventListener('click', () => {
      drawer.classList.remove('open');
      menuBtn.setAttribute('aria-expanded', 'false');
    });
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && drawer.classList.contains('open')) {
      drawer.classList.remove('open');
      menuBtn.setAttribute('aria-expanded', 'false');
    }
  });
}

/* ==========================================================================
   3. HERO QUICK-INSTALL TABS (bash / docker / pip)
   ========================================================================== */
function initHeroInstallerTabs() {
  const tabs = document.querySelectorAll('.term-tab');
  const codeEl = document.getElementById('heroInstallCmd');
  if (!tabs.length || !codeEl) return;

  const commands = {
    bash: 'git clone https://github.com/najafdev/hacknova.git && bash install.sh',
    docker: 'docker run -d -p 8080:8080 najafdev/hacknova:latest',
    pip: 'pip install hacknova && hacknova --init'
  };

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const cmdKey = tab.getAttribute('data-tab-cmd');
      if (commands[cmdKey]) {
        codeEl.textContent = commands[cmdKey];
      }
    });
  });
}

/* ==========================================================================
   4. HERO INTERACTIVE CONSOLE TABS (Stream / Diff / MITRE)
   ========================================================================== */
function initHeroConsoleTabs() {
  const tabs = document.querySelectorAll('.c-tab');
  const panels = {
    stream: document.getElementById('cViewStream'),
    diff: document.getElementById('cViewDiff'),
    mitre: document.getElementById('cViewMitre')
  };

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      Object.values(panels).forEach(p => p && p.classList.remove('active'));

      tab.classList.add('active');
      const viewKey = tab.getAttribute('data-console-view');
      if (panels[viewKey]) {
        panels[viewKey].classList.add('active');
      }
    });
  });
}

/* ==========================================================================
   5. BENTO PROVIDER SWITCHER (OrcaRouter Upstream Hub)
   ========================================================================== */
function initBentoProviderSwitcher() {
  const chips = document.querySelectorAll('#providerSwitcher .provider-chip');
  if (!chips.length) return;

  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      chips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
    });
  });
}

/* ==========================================================================
   6. RADAR TOOLTIPS
   ========================================================================== */
function initRadarTooltips() {
  const pings = document.querySelectorAll('.radar-ping');
  const toastContainer = document.getElementById('toastContainer');

  pings.forEach(ping => {
    ping.addEventListener('click', () => {
      const info = ping.getAttribute('data-tooltip') || 'Target vulnerability anomaly';
      if (!toastContainer) return;

      const toast = document.createElement('div');
      toast.className = 'toast';
      toast.innerHTML = `
        <span class="badge-dot red"></span>
        <span>${info}</span>
      `;
      toastContainer.appendChild(toast);

      setTimeout(() => {
        toast.style.transition = 'all 0.3s ease';
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        setTimeout(() => toast.remove(), 300);
      }, 2500);
    });
  });
}

/* ==========================================================================
   7. DEVELOPER CODE TABS
   ========================================================================== */
function initCodeTabs() {
  const tabs = document.querySelectorAll('.code-tab');
  const panels = document.querySelectorAll('.code-panel');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const targetId = `tab-${tab.getAttribute('data-tab')}`;

      tabs.forEach(t => t.classList.remove('active'));
      panels.forEach(p => p.classList.remove('active'));

      tab.classList.add('active');
      const targetPanel = document.getElementById(targetId);
      if (targetPanel) {
        targetPanel.classList.add('active');
      }
    });
  });
}

/* ==========================================================================
   8. INTERACTIVE THREAT PLAYGROUND / SIMULATOR
   ========================================================================== */
function initSimulator() {
  const simButtons = document.querySelectorAll('.sim-btn');
  const runBtn = document.getElementById('runSimulationBtn');
  const progressBar = document.getElementById('simProgressBar');
  const progressText = document.getElementById('simProgressText');

  const targetTag = document.getElementById('simTargetTag');
  const scoreNum = document.getElementById('simScore');
  const scoreCircle = document.getElementById('simScoreCircle');
  const critVal = document.getElementById('simCrit');
  const highVal = document.getElementById('simHigh');
  const passVal = document.getElementById('simPass');
  const findingsList = document.getElementById('simFindingsList');
  const remedFileLabel = document.getElementById('remedFileLabel');
  const remedCodeContent = document.getElementById('remedCodeContent');
  const applyBtn = document.getElementById('applyRemedyBtn');

  let activePreset = 'k8s';

  const presets = {
    k8s: {
      target: 'k8s://production-cluster-01',
      score: 92,
      crit: 1,
      high: 2,
      pass: 48,
      fileName: 'security_patch_k8s.yaml',
      findings: [
        {
          sev: 'crit',
          code: 'K8S-CIS-5.2.2',
          title: 'Privileged Container Mode Enabled in Deployment',
          mitre: 'D3-PSA (Process Segment Authorization)'
        },
        {
          sev: 'high',
          code: 'K8S-RBAC-04',
          title: 'Wildcard (*) Permissions on ClusterRole default-sa',
          mitre: 'D3-LPA (Least Privilege Access)'
        }
      ],
      code: `# Autonomous Remediation generated by HACKNOVA via OrcaRouter
apiVersion: apps/v1
kind: Deployment
metadata:
  name: auth-service
spec:
  template:
    spec:
      securityContext:
        runAsNonRoot: true
        allowPrivilegeEscalation: false
        capabilities:
          drop: ["ALL"]
        readOnlyRootFilesystem: true`
    },
    aws: {
      target: 'cloud://aws-us-east-1:financial-vpc',
      score: 87,
      crit: 2,
      high: 3,
      pass: 114,
      fileName: 'remediate_aws_vpc.tf',
      findings: [
        {
          sev: 'crit',
          code: 'CIS-AWS-2.1.5',
          title: 'Public Read/Write ACL on S3 Bucket prod-customer-vault',
          mitre: 'D3-BPA (Block Public Access)'
        },
        {
          sev: 'high',
          code: 'CIS-AWS-4.1',
          title: 'Security Group sg-08af9 allows 0.0.0.0/0 on port 22',
          mitre: 'D3-NIA (Network Ingress Authorization)'
        }
      ],
      code: `# Terraform Autonomous Fix synthesized by HACKNOVA via OrcaRouter
resource "aws_s3_bucket_public_access_block" "vault_block" {
  bucket                  = "prod-customer-vault"
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_security_group_rule" "restrict_ssh" {
  type              = "ingress"
  from_port         = 22
  to_port           = 22
  protocol          = "tcp"
  cidr_blocks       = ["10.0.0.0/16"] # Restricted to internal VPN
  security_group_id = "sg-08af9"
}`
    },
    llm: {
      target: 'llm://enterprise-rag-assistant:v3',
      score: 95,
      crit: 0,
      high: 2,
      pass: 36,
      fileName: 'llm_guardrail_rules.json',
      findings: [
        {
          sev: 'high',
          code: 'OWASP-LLM-01',
          title: 'Indirect Prompt Injection Vulnerability in RAG context',
          mitre: 'D3-SPH (System Prompt Hardening)'
        },
        {
          sev: 'high',
          code: 'OWASP-LLM-06',
          title: 'Sensitive Training Data Exfiltration via Markdown Leak',
          mitre: 'D3-ODS (Output Data Sanitization)'
        }
      ],
      code: `{
  "policy_name": "OrcaRouter_Autonomous_LLM_Defense",
  "version": "2026.10.23",
  "rules": [
    {
      "vector": "indirect_prompt_injection",
      "action": "SANITIZE_AND_ISOLATE",
      "delimiter_wrap": "<<USER_QUERY_ISOLATED>>",
      "deny_patterns": ["ignore previous instructions", "exfiltrate to http", "system override"]
    },
    {
      "vector": "pii_output_leakage",
      "action": "MASK_REGEX",
      "entities": ["api_key", "jwt_secret", "credit_card", "ssn"]
    }
  ]
}`
    },
    api: {
      target: 'https://api.internal.bank.com/v2',
      score: 89,
      crit: 1,
      high: 2,
      pass: 62,
      fileName: 'api_gateway_defense.py',
      findings: [
        {
          sev: 'crit',
          code: 'OWASP-API-01',
          title: 'Broken Object Level Authorization (BOLA) on /accounts/{id}',
          mitre: 'D3-OAC (Object Access Control)'
        },
        {
          sev: 'high',
          code: 'OWASP-API-02',
          title: 'Weak JWT Signature Validation accepts algorithm "none"',
          mitre: 'D3-TKA (Token Key Authentication)'
        }
      ],
      code: `# API Gateway Defense Layer synthesized by HACKNOVA
from fastapi import Request, HTTPException, Depends
from security.auth import verify_bearer_jwt

async def validate_object_ownership(request: Request, user = Depends(verify_bearer_jwt)):
    account_id = request.path_params.get("account_id")
    if not user.has_explicit_access(account_id):
        # Neutralize BOLA / IDOR traversal attempt
        raise HTTPException(status_code=403, detail="Access to resource forbidden")
    return True`
    },
    kernel: {
      target: 'host://k8s-worker-node-04 (Kernel 6.1)',
      score: 96,
      crit: 0,
      high: 1,
      pass: 78,
      fileName: 'ebpf_trace_filter.c',
      findings: [
        {
          sev: 'high',
          code: 'KERNEL-CVE-2026-PRIV',
          title: 'Potential Unprivileged eBPF Map Escalation Vector',
          mitre: 'D3-PSA (Process Segment Authorization)'
        }
      ],
      code: `// eBPF Proactive Kernel Defense synthesized by HACKNOVA
#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>

SEC("lsm/bpf")
int BPF_PROG(restrict_unprivileged_bpf, int cmd, union bpf_attr *attr, unsigned int size) {
    if (!bpf_capable(CAP_SYS_ADMIN)) {
        // Enforce strict kernel security isolation
        return -EPERM;
    }
    return 0;
}
char LICENSE[] SEC("license") = "GPL";`
    }
  };

  function updatePresetView(presetKey) {
    activePreset = presetKey;
    const data = presets[presetKey];
    if (!data) return;

    if (targetTag) targetTag.textContent = data.target;
    if (scoreNum) scoreNum.textContent = data.score;
    if (critVal) critVal.textContent = data.crit;
    if (highVal) highVal.textContent = data.high;
    if (passVal) passVal.textContent = data.pass;
    if (remedFileLabel) remedFileLabel.textContent = data.fileName;
    if (remedCodeContent) remedCodeContent.textContent = data.code;

    // Update circular score gauge
    if (scoreCircle) {
      const circumference = 264;
      const offset = circumference * (1 - data.score / 100);
      scoreCircle.style.strokeDashoffset = offset;
      if (data.score >= 90) {
        scoreCircle.style.stroke = 'var(--accent-emerald)';
      } else if (data.score >= 75) {
        scoreCircle.style.stroke = 'var(--accent-amber)';
      } else {
        scoreCircle.style.stroke = 'var(--accent-red)';
      }
    }

    // Render findings
    if (findingsList) {
      findingsList.innerHTML = data.findings.map((f, idx) => `
        <div class="finding-item ${f.sev} ${idx === 0 ? 'active' : ''}" data-finding-id="${idx}">
          <div class="finding-header">
            <span class="vuln-pill ${f.sev === 'crit' ? 'red' : 'amber'}">${f.sev === 'crit' ? 'CRITICAL' : 'HIGH'}</span>
            <span class="vuln-code">${f.code}</span>
          </div>
          <div class="finding-name">${f.title}</div>
          <div class="finding-mitre">MITRE D3FEND: <code>${f.mitre}</code></div>
        </div>
      `).join('');

      // Add click listeners to findings
      const items = findingsList.querySelectorAll('.finding-item');
      items.forEach(item => {
        item.addEventListener('click', () => {
          items.forEach(it => it.classList.remove('active'));
          item.classList.add('active');
        });
      });
    }
  }

  simButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      simButtons.forEach(b => {
        b.classList.remove('active');
        b.setAttribute('aria-selected', 'false');
      });
      btn.classList.add('active');
      btn.setAttribute('aria-selected', 'true');
      const preset = btn.getAttribute('data-preset');
      updatePresetView(preset);
    });
  });

  if (runBtn) {
    runBtn.addEventListener('click', () => {
      runBtn.disabled = true;
      let progress = 0;
      if (progressText) progressText.textContent = 'Initiating autonomous reconnaissance & surface mapping...';

      const interval = setInterval(() => {
        progress += 25;
        if (progressBar) progressBar.style.width = `${progress}%`;

        if (progress === 25 && progressText) {
          progressText.textContent = 'Auditing CIS benchmarks & cloud IAM policies...';
        } else if (progress === 50 && progressText) {
          progressText.textContent = 'Engaging OrcaRouter Cyber Inference & D3FEND mapping...';
        } else if (progress === 75 && progressText) {
          progressText.textContent = 'Synthesizing zero-downtime remediation script...';
        } else if (progress >= 100) {
          clearInterval(interval);
          if (progressText) progressText.textContent = 'Audit complete. Zero-downtime remediation verified.';
          runBtn.disabled = false;
          updatePresetView(activePreset);
        }
      }, 180);
    });
  }

  if (applyBtn) {
    applyBtn.addEventListener('click', () => {
      const originalText = applyBtn.innerHTML;
      applyBtn.innerHTML = '<span>Verifying...</span>';
      applyBtn.disabled = true;

      setTimeout(() => {
        applyBtn.innerHTML = '<span>Applied ✓</span>';
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.innerHTML = `
          <span class="badge-dot emerald"></span>
          <span>Remediation patch verified &amp; staged successfully.</span>
        `;
        const tc = document.getElementById('toastContainer');
        if (tc) tc.appendChild(toast);

        setTimeout(() => {
          toast.remove();
          applyBtn.innerHTML = originalText;
          applyBtn.disabled = false;
        }, 2200);
      }, 700);
    });
  }

  // Initialize first preset
  updatePresetView('k8s');
}

/* ==========================================================================
   9. MOUSE SPOTLIGHT EFFECT ON DATA-SPOTLIGHT CARDS
   ========================================================================== */
function initSpotlightEffect() {
  const cards = document.querySelectorAll('[data-spotlight]');

  cards.forEach(card => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      card.style.setProperty('--mouse-x', `${x}px`);
      card.style.setProperty('--mouse-y', `${y}px`);
    });
  });
}

/* ==========================================================================
   10. CONSOLE SIMULATION TYPEWRITER
   ========================================================================== */
function initConsoleTypewriter() {
  const typewriter = document.querySelector('.term-typewriter');
  if (!typewriter) return;

  const commands = [
    'hacknova posture-audit --target cloud://production --remediate auto',
    'hacknova llm-redteam --model enterprise-rag --owasp-top10',
    'hacknova api-scan --spec openapi.json --fuzz-bola',
    'hacknova mitre-d3fend --compile-rules sigma'
  ];

  let cmdIndex = 0;
  let charIndex = 0;
  let isDeleting = false;

  function type() {
    const currentCmd = commands[cmdIndex];
    if (isDeleting) {
      typewriter.textContent = currentCmd.substring(0, charIndex - 1);
      charIndex--;
    } else {
      typewriter.textContent = currentCmd.substring(0, charIndex + 1);
      charIndex++;
    }

    let delay = isDeleting ? 25 : 55;

    if (!isDeleting && charIndex === currentCmd.length) {
      delay = 2500;
      isDeleting = true;
    } else if (isDeleting && charIndex === 0) {
      isDeleting = false;
      cmdIndex = (cmdIndex + 1) % commands.length;
      delay = 400;
    }

    setTimeout(type, delay);
  }

  setTimeout(type, 1500);
}
