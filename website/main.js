/**
 * SecScan AI — Web Platform Interactive Controller
 * Version: v2026.10.23
 * Core: Vanilla JS, Zero External Runtime Dependencies, Ultra-Smooth Interactivity
 */

document.addEventListener('DOMContentLoaded', () => {
  initClipboard();
  initMobileMenu();
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
            // Fallback for non-https/local dev contexts
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

          // UI feedback on button
          const originalHTML = btn.innerHTML;
          btn.classList.add('copied');
          btn.innerHTML = `
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            <span class="copy-label">Copied!</span>
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
      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="${isError ? '#ef4444' : '#10b981'}" stroke-width="2">
        ${isError 
          ? '<circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line>' 
          : '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline>'
        }
      </svg>
      <span>${message}</span>
    `;

    toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.transition = 'all 0.3s ease';
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      setTimeout(() => toast.remove(), 300);
    }, 2500);
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
}

/* ==========================================================================
   3. DEVELOPER CODE TABS
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
   4. INTERACTIVE THREAT PLAYGROUND / SIMULATOR
   ========================================================================== */
function initSimulator() {
  const simButtons = document.querySelectorAll('.sim-btn');
  const runBtn = document.getElementById('runSimulationBtn');
  const progressBar = document.getElementById('simProgressBar');
  const progressText = document.getElementById('simProgressText');

  const targetTag = document.getElementById('simTargetTag');
  const scoreNum = document.getElementById('simScore');
  const critVal = document.getElementById('simCrit');
  const highVal = document.getElementById('simHigh');
  const passVal = document.getElementById('simPass');
  const findingsList = document.getElementById('simFindingsList');
  const remedFileLabel = document.getElementById('remedFileLabel');
  const remedCodeContent = document.getElementById('remedCodeContent');

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
      code: `# Autonomous Remediation generated by SecScan AI
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
      code: `# Terraform Autonomous Fix synthesized by SecScan AI
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
      high: 1,
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
      fileName: 'api_gateway_policy.py',
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
      code: `# API Gateway Defense Layer synthesized by SecScan AI
from fastapi import Request, HTTPException, Depends
from security.auth import verify_bearer_jwt

async def validate_object_ownership(request: Request, user = Depends(verify_bearer_jwt)):
    account_id = request.path_params.get("account_id")
    if not user.has_explicit_access(account_id):
        # Prevent BOLA / IDOR traversal
        raise HTTPException(status_code=403, detail="Access to resource forbidden")
    return True`
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

    // Render findings
    if (findingsList) {
      findingsList.innerHTML = data.findings.map(f => `
        <div class="finding-item ${f.sev}">
          <div class="finding-header">
            <span class="vuln-pill ${f.sev === 'crit' ? 'red' : 'amber'}">${f.sev === 'crit' ? 'CRITICAL' : 'HIGH'}</span>
            <span class="vuln-code">${f.code}</span>
          </div>
          <div class="finding-name">${f.title}</div>
          <div class="finding-mitre">MITRE D3FEND: <code>${f.mitre}</code></div>
        </div>
      `).join('');
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
      if (progressText) progressText.textContent = 'Executing multi-layer autonomous security scan...';

      const interval = setInterval(() => {
        progress += 20;
        if (progressBar) progressBar.style.width = `${progress}%`;

        if (progress === 40 && progressText) {
          progressText.textContent = 'Fuzzing authorization bounds & cloud policies...';
        } else if (progress === 80 && progressText) {
          progressText.textContent = 'Synthesizing MITRE D3FEND patches via OrcaRouter...';
        } else if (progress >= 100) {
          clearInterval(interval);
          if (progressText) progressText.textContent = 'Scan completed. All 1-click remedies generated.';
          runBtn.disabled = false;
          updatePresetView(activePreset);
        }
      }, 150);
    });
  }
}

/* ==========================================================================
   5. MOUSE SPOTLIGHT EFFECT ON BENTO CARDS
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
      card.style.background = `radial-gradient(400px circle at ${x}px ${y}px, rgba(0, 240, 255, 0.08), rgba(13, 19, 31, 0.72) 70%)`;
    });

    card.addEventListener('mouseleave', () => {
      card.style.background = '';
    });
  });
}

/* ==========================================================================
   6. CONSOLE SIMULATION TYPEWRITER
   ========================================================================== */
function initConsoleTypewriter() {
  const typewriter = document.querySelector('.term-typewriter');
  if (!typewriter) return;

  const commands = [
    'secscan_ai posture-audit --target cloud://production --remediate auto',
    'secscan_ai llm-redteam --model enterprise-rag --owasp-top10',
    'secscan_ai api-scan --spec openapi.json --fuzz-bola'
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
      delay = 2500; // Pause at end of command
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
