"""
HackBot Planning Mode
=====================
Creates structured penetration testing plans, attack strategies, and
security assessment methodologies.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from hackbot.config import HackBotConfig, REPORTS_DIR
from hackbot.core.engine import AIEngine, create_conversation


# ── Plan Templates ───────────────────────────────────────────────────────────

PLAN_TEMPLATES = {
    "web_pentest": {
        "name": "Web Application Penetration Test",
        "phases": [
            "Reconnaissance & OSINT",
            "Technology Fingerprinting",
            "Content Discovery",
            "Authentication Testing",
            "Authorization Testing",
            "Input Validation Testing",
            "Session Management Testing",
            "API Security Testing",
            "Business Logic Testing",
            "Client-Side Testing",
            "Reporting & Remediation",
        ],
    },
    "network_pentest": {
        "name": "Network Penetration Test",
        "phases": [
            "Network Discovery & Mapping",
            "Port Scanning & Service Enumeration",
            "Vulnerability Scanning",
            "Service-Specific Testing",
            "Password Attacks",
            "Privilege Escalation",
            "Lateral Movement",
            "Data Exfiltration Testing",
            "Persistence Testing",
            "Reporting & Remediation",
        ],
    },
    "api_pentest": {
        "name": "API Security Assessment",
        "phases": [
            "API Discovery & Documentation Review",
            "Authentication & Authorization Testing",
            "Input Validation & Injection",
            "Rate Limiting & Abuse Testing",
            "Data Exposure Testing",
            "Business Logic Testing",
            "Error Handling & Information Disclosure",
            "Reporting & Remediation",
        ],
    },
    "cloud_audit": {
        "name": "Cloud Security Audit",
        "phases": [
            "IAM Configuration Review",
            "Network & Firewall Configuration",
            "Storage & Data Protection",
            "Compute Security",
            "Logging & Monitoring",
            "Compliance Checks",
            "Secret Management",
            "Container Security",
            "Reporting & Remediation",
        ],
    },
    "ad_pentest": {
        "name": "Active Directory Penetration Test",
        "phases": [
            "Domain Reconnaissance",
            "User & Group Enumeration",
            "Trust Relationship Mapping",
            "Kerberos Attacks",
            "LDAP Exploitation",
            "Privilege Escalation",
            "Lateral Movement",
            "Domain Dominance",
            "Persistence",
            "Reporting & Remediation",
        ],
    },
    "mobile_pentest": {
        "name": "Mobile Application Penetration Test",
        "phases": [
            "Static Analysis",
            "Dynamic Analysis",
            "Network Communication",
            "Data Storage",
            "Authentication & Session",
            "Cryptographic Analysis",
            "Platform-Specific Testing",
            "Reporting & Remediation",
        ],
    },
    "red_team": {
        "name": "Red Team Engagement",
        "phases": [
            "OSINT & Target Profiling",
            "Initial Access Planning",
            "Phishing & Social Engineering",
            "Perimeter Breach",
            "Internal Reconnaissance",
            "Privilege Escalation",
            "Lateral Movement",
            "Objective Achievement",
            "Exfiltration Simulation",
            "Cleanup & Reporting",
        ],
    },
    "bug_bounty": {
        "name": "Bug Bounty Methodology",
        "phases": [
            "Scope Analysis & Asset Discovery",
            "Subdomain Enumeration",
            "Content & Technology Discovery",
            "Vulnerability Hunting (OWASP Top 10)",
            "Business Logic Testing",
            "Chaining & Impact Assessment",
            "Report Writing & Submission",
        ],
    },
}


class PlanMode:
    """Creates structured cybersecurity assessment plans."""

    def __init__(self, engine: AIEngine, config: HackBotConfig):
        self.engine = engine
        self.config = config
        self.conversation = create_conversation("plan", language=config.ui.language)
        self.current_plan: Optional[Dict[str, Any]] = None

    def create_plan(
        self,
        target: str,
        plan_type: str = "web_pentest",
        scope: str = "",
        constraints: str = "",
        on_token: Optional[Callable[[str], None]] = None,
    ) -> str:
        """
        Generate a comprehensive penetration testing plan.

        Args:
            target: Target system/application
            plan_type: Type of assessment (see PLAN_TEMPLATES)
            scope: Scope definition
            constraints: Any constraints or limitations
        """
        template = PLAN_TEMPLATES.get(plan_type, PLAN_TEMPLATES["web_pentest"])

        prompt = f"""Create a detailed penetration testing plan:

**Assessment Type:** {template['name']}
**Target:** {target}
**Scope:** {scope or 'Full assessment as authorized by the client'}
**Constraints:** {constraints or 'Standard engagement rules'}

Use the following phase structure:
{chr(10).join(f'{i+1}. {phase}' for i, phase in enumerate(template['phases']))}

For each phase, provide:
1. **Objective** — What we're trying to achieve
2. **Tools** — Specific tools and commands to use
3. **Techniques** — Methodologies and approaches
4. **Expected Output** — What we should document
5. **Time Estimate** — Approximate time needed
6. **Risk Level** — How likely to trigger alerts/issues

Also include:
- Prerequisites and setup requirements
- Rules of engagement
- Communication plan
- Deliverables and report structure
- Emergency contacts and rollback procedures

Make the plan specific and actionable with real commands and tool configurations."""

        self.conversation.add("user", prompt)

        response = self.engine.chat(
            self.conversation,
            stream=bool(on_token),
            on_token=on_token,
        )
        self.conversation.add("assistant", response)

        self.current_plan = {
            "type": plan_type,
            "target": target,
            "scope": scope,
            "content": response,
            "timestamp": time.time(),
        }

        return response

    def refine_plan(
        self,
        feedback: str,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Refine the current plan based on feedback."""
        self.conversation.add("user", f"Refine the plan based on this feedback:\n\n{feedback}")

        response = self.engine.chat(
            self.conversation,
            stream=bool(on_token),
            on_token=on_token,
        )
        self.conversation.add("assistant", response)

        if self.current_plan:
            self.current_plan["content"] = response
            self.current_plan["refined"] = True

        return response

    def generate_checklist(
        self,
        plan_type: str = "web_pentest",
        on_token: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Generate a testing checklist for a given assessment type."""
        template = PLAN_TEMPLATES.get(plan_type, PLAN_TEMPLATES["web_pentest"])

        prompt = f"""Generate a comprehensive security testing checklist for: {template['name']}

Format as a markdown checklist with:
- [ ] items grouped by phase
- Priority tags [P1/P2/P3]
- Specific tools for each check
- OWASP/CWE references where applicable

Phases: {', '.join(template['phases'])}"""

        self.conversation.add("user", prompt)
        response = self.engine.chat(
            self.conversation,
            stream=bool(on_token),
            on_token=on_token,
        )
        self.conversation.add("assistant", response)
        return response

    def generate_commands(
        self,
        target: str,
        tools: List[str],
        on_token: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Generate ready-to-use commands for specific tools against a target."""
        prompt = f"""Generate ready-to-use commands for testing target: {target}

Tools to use: {', '.join(tools)}

For each tool provide:
1. Basic scan command
2. Aggressive/thorough scan command
3. Stealthy scan command (if applicable)
4. Output file specification
5. Brief explanation of what each flag does

Format as copy-paste ready commands with explanations."""

        self.conversation.add("user", prompt)
        response = self.engine.chat(
            self.conversation,
            stream=bool(on_token),
            on_token=on_token,
        )
        self.conversation.add("assistant", response)
        return response

    def analyze_scope(
        self,
        scope_text: str,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Analyze a scope document and identify testing boundaries."""
        prompt = f"""Analyze this scope/rules of engagement and identify:

1. **In-Scope Assets** — What can be tested
2. **Out-of-Scope** — What must NOT be tested
3. **Testing Windows** — When testing is allowed
4. **Restrictions** — Any technique limitations
5. **Risks** — Potential issues to watch for
6. **Recommendations** — Suggested approach given the constraints

Scope Document:
{scope_text}"""

        self.conversation.add("user", prompt)
        response = self.engine.chat(
            self.conversation,
            stream=bool(on_token),
            on_token=on_token,
        )
        self.conversation.add("assistant", response)
        return response

    def ask(
        self,
        question: str,
        stream: bool = True,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Ask a planning-related question."""
        self.conversation.add("user", question)
        response = self.engine.chat(
            self.conversation,
            stream=stream and bool(on_token),
            on_token=on_token,
        )
        self.conversation.add("assistant", response)
        return response

    def save_plan(self, name: str = "") -> Path:
        """Save the current plan to disk."""
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        fname = name or f"plan_{ts}"
        path = REPORTS_DIR / f"{fname}.md"

        content = self.current_plan.get("content", "") if self.current_plan else ""
        if not content:
            # Export full conversation
            content = "\n\n---\n\n".join(
                f"**{m.role.upper()}:**\n\n{m.content}"
                for m in self.conversation.messages
                if m.role != "system"
            )

        with open(path, "w") as f:
            f.write(content)

        return path

    def reset(self) -> None:
        """Reset planning session."""
        self.conversation = create_conversation("plan", language=self.config.ui.language)
        self.current_plan = None

    @staticmethod
    def list_templates() -> Dict[str, str]:
        """List available plan templates."""
        return {k: str(v["name"]) for k, v in PLAN_TEMPLATES.items()}
