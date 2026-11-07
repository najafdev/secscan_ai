"""
HackBot Report Generator
=========================
Generates comprehensive security assessment reports in HTML, Markdown, JSON, SARIF, and CSV formats.
"""

from __future__ import annotations

import csv
import json
import re
import time
from typing import Any, Dict, List, Optional

from jinja2 import Template

from hackbot import __version__
from hackbot.config import REPORTS_DIR


# ── HTML Report Template ─────────────────────────────────────────────────────

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>HackBot Security Report — {{ target }}</title>
<style>
  :root {
    --bg: #0d1117; --surface: #161b22; --border: #30363d;
    --text: #c9d1d9; --text-dim: #8b949e; --accent: #58a6ff;
    --critical: #f85149; --high: #f0883e; --medium: #d29922;
    --low: #58a6ff; --info: #8b949e; --success: #3fb950;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
         background: var(--bg); color: var(--text); line-height: 1.6; padding: 2rem; }
  .container { max-width: 1100px; margin: 0 auto; }
  h1 { color: var(--success); font-size: 2rem; margin-bottom: 0.5rem; }
  h2 { color: var(--accent); border-bottom: 1px solid var(--border); padding-bottom: 0.5rem;
       margin: 2rem 0 1rem; }
  h3 { color: var(--text); margin: 1.5rem 0 0.5rem; }
  .header { background: var(--surface); border: 1px solid var(--border); border-radius: 6px;
            padding: 2rem; margin-bottom: 2rem; }
  .meta { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 1rem; margin-top: 1rem; }
  .meta-item { background: var(--bg); padding: 1rem; border-radius: 4px; }
  .meta-label { font-size: 0.85rem; color: var(--text-dim); text-transform: uppercase;
                letter-spacing: 0.05em; }
  .meta-value { font-size: 1.1rem; font-weight: 600; margin-top: 0.25rem; }
  .severity-badge { display: inline-block; padding: 0.2rem 0.6rem; border-radius: 3px;
                    font-weight: 600; font-size: 0.85rem; }
  .severity-Critical { background: var(--critical); color: white; }
  .severity-High { background: var(--high); color: white; }
  .severity-Medium { background: var(--medium); color: white; }
  .severity-Low { background: var(--low); color: white; }
  .severity-Info { background: var(--info); color: white; }
  .stats { display: flex; gap: 1rem; flex-wrap: wrap; margin: 1rem 0; }
  .stat { background: var(--surface); border: 1px solid var(--border); border-radius: 4px;
          padding: 1rem 1.5rem; text-align: center; min-width: 100px; }
  .stat-num { font-size: 2rem; font-weight: 700; }
  .stat-label { font-size: 0.85rem; color: var(--text-dim); }
  .finding { background: var(--surface); border: 1px solid var(--border); border-radius: 6px;
             padding: 1.5rem; margin-bottom: 1rem; }
  .finding-header { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.75rem; }
  .finding-title { font-weight: 600; font-size: 1.1rem; }
  pre { background: var(--bg); border: 1px solid var(--border); border-radius: 4px;
        padding: 1rem; overflow-x: auto; font-size: 0.9rem; margin: 0.5rem 0; }
  code { font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; }
  .recommendation { background: rgba(56, 139, 253, 0.1); border-left: 3px solid var(--accent);
                    padding: 0.75rem 1rem; margin: 0.5rem 0; border-radius: 0 4px 4px 0; }
  .tool-history { margin: 1rem 0; }
  .tool-entry { background: var(--surface); border: 1px solid var(--border); border-radius: 4px;
                padding: 1rem; margin-bottom: 0.5rem; }
  .tool-cmd { font-family: monospace; color: var(--success); }
  .tool-status { font-weight: 600; }
  .success { color: var(--success); }
  .failed { color: var(--critical); }
  footer { margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--border);
           color: var(--text-dim); font-size: 0.85rem; text-align: center; }
</style>
</head>
<body>
<div class="container">

<div class="header">
  <h1>⚡ HackBot Security Report</h1>
  <div class="meta">
    <div class="meta-item">
      <div class="meta-label">Target</div>
      <div class="meta-value">{{ target }}</div>
    </div>
    <div class="meta-item">
      <div class="meta-label">Date</div>
      <div class="meta-value">{{ date }}</div>
    </div>
    <div class="meta-item">
      <div class="meta-label">Scope</div>
      <div class="meta-value">{{ scope or 'Full Assessment' }}</div>
    </div>
    <div class="meta-item">
      <div class="meta-label">Duration</div>
      <div class="meta-value">{{ duration }}</div>
    </div>
  </div>
</div>

<h2>1. Executive Summary</h2>
<div class="stats">
  {% for sev, count in severity_counts.items() %}
  <div class="stat">
    <div class="stat-num severity-{{ sev }}" style="color: inherit;">{{ count }}</div>
    <div class="stat-label">{{ sev }}</div>
  </div>
  {% endfor %}
  <div class="stat">
    <div class="stat-num">{{ total_findings }}</div>
    <div class="stat-label">Total</div>
  </div>
</div>

{% if summary %}
<p>{{ summary }}</p>
{% endif %}

{% if posture %}
<div style="background: var(--surface); border: 1px solid var(--border); border-radius: 6px; padding: 1.25rem; margin: 1.5rem 0; display: flex; align-items: center; justify-content: space-around; flex-wrap: wrap; gap: 1rem;">
  <div style="text-align: center;">
    <div style="font-size: 0.8rem; color: var(--text-dim); text-transform: uppercase;">Security Posture Score</div>
    <div style="font-size: 2.2rem; font-weight: 800; color: {% if posture.score >= 80 %}var(--success){% elif posture.score >= 60 %}var(--medium){% else %}var(--critical){% endif %};">{{ posture.score }} / 100</div>
    <div style="font-weight: 600;">Grade: {{ posture.grade }}</div>
  </div>
  <div style="text-align: center;">
    <div style="font-size: 0.8rem; color: var(--text-dim); text-transform: uppercase;">Overall Risk Level</div>
    <div style="font-size: 1.6rem; font-weight: 700; margin-top: 0.25rem;">{{ posture.risk_level }}</div>
    <div style="font-size: 0.8rem; color: var(--text-dim);">Risk Index: {{ posture.risk_index }} / 10.0</div>
  </div>
  <div style="text-align: center;">
    <div style="font-size: 0.8rem; color: var(--text-dim); text-transform: uppercase;">Remediation Effort</div>
    <div style="font-size: 1.6rem; font-weight: 700; margin-top: 0.25rem;">~{{ posture.remediation_hours }} hrs</div>
    <div style="font-size: 0.8rem; color: var(--text-dim);">Estimated engineering time</div>
  </div>
</div>
{% endif %}

<h2>2. Risk Assessment Charts</h2>
{% if severity_counts %}
<table style="width: 100%; border-collapse: collapse; margin: 1rem 0;">
  <thead>
    <tr style="background: var(--accent); color: white;">
      <th style="padding: 0.5rem 1rem; text-align: left;">Severity</th>
      <th style="padding: 0.5rem 1rem; text-align: center;">Count</th>
      <th style="padding: 0.5rem 1rem; text-align: center;">Percentage</th>
    </tr>
  </thead>
  <tbody>
    {% for sev, count in severity_counts.items() %}
    <tr style="background: var(--surface); border-bottom: 1px solid var(--border);">
      <td style="padding: 0.5rem 1rem; font-weight: 600;">
        <span class="severity-badge severity-{{ sev }}">{{ sev }}</span>
      </td>
      <td style="padding: 0.5rem 1rem; text-align: center;">{{ count }}</td>
      <td style="padding: 0.5rem 1rem; text-align: center;">{{ (count / total_findings * 100) | round(0) | int if total_findings else 0 }}%</td>
    </tr>
    {% endfor %}
    <tr style="background: var(--bg); border-top: 2px solid var(--border); font-weight: 700;">
      <td style="padding: 0.5rem 1rem;">Total</td>
      <td style="padding: 0.5rem 1rem; text-align: center;">{{ total_findings }}</td>
      <td style="padding: 0.5rem 1rem; text-align: center;">100%</td>
    </tr>
  </tbody>
</table>
{% else %}
<p style="color: var(--text-dim);">No findings recorded.</p>
{% endif %}

<h2>3. Detailed Findings</h2>
{% for finding in findings %}
<div class="finding">
  <div class="finding-header">
    <span class="severity-badge severity-{{ finding.severity }}">{{ finding.severity }}</span>
    <span class="finding-title">{{ finding.title }}</span>
  </div>
  <p>{{ finding.description }}</p>
  {% if finding.evidence %}
  <h4>Evidence</h4>
  <pre><code>{{ finding.evidence }}</code></pre>
  {% endif %}
  {% if finding.recommendation %}
  <div class="recommendation">
    <strong>Recommendation:</strong> {{ finding.recommendation }}
  </div>
  {% endif %}
</div>
{% endfor %}

{% if tool_history %}
<h2>4. List of Commands Executed</h2>
{% for entry in tool_history %}
<div class="tool-entry">
  <div><strong>#{{ loop.index }} Tool:</strong> <span class="tool-cmd">{{ entry.tool }}</span></div>
  <div><strong>Sudo:</strong> {{ 'Yes' if entry.sudo_used else 'No' }}</div>
  <span class="tool-cmd">$ {{ entry.command }}</span>
  <span class="tool-status {{ 'success' if entry.success else 'failed' }}">
    {{ '✓' if entry.success else '✗' }}
  </span>
  <span style="color: var(--text-dim);">({{ entry.duration }}s, exit={{ entry.return_code }})</span>
</div>
{% endfor %}

<h2>5. Technical Annex (Agent Output)</h2>
{% if include_raw %}
{% for entry in tool_history %}
<div class="tool-entry">
  <div><strong>#{{ loop.index }} {{ entry.tool }}</strong></div>
  <div class="tool-cmd">$ {{ entry.command }}</div>
  <pre><code>{{ entry.annex_output[:8000] }}</code></pre>
</div>
{% endfor %}
{% else %}
<p>Raw output export is disabled by configuration (`include_raw_output: false`).</p>
{% endif %}
{% endif %}

{% if scripts %}
<h2>Generated Scripts</h2>
{% for script in scripts %}
<div class="tool-entry">
  <div><strong>Name:</strong> <span class="tool-cmd">{{ script.name }}</span></div>
  <div><strong>Language:</strong> <span class="tool-cmd">{{ script.language }}</span></div>
  {% if script.path %}<div><strong>Saved To:</strong> {{ script.path }}</div>{% endif %}
  {% if script.description %}<p>{{ script.description }}</p>{% endif %}
  <pre><code>{{ script.content[:4000] }}</code></pre>
</div>
{% endfor %}
{% endif %}

<footer>
  Generated by HackBot AI Cybersecurity Assistant • {{ date }}
</footer>

</div>
</body>
</html>"""


def calculate_security_posture(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate an executive security posture score and risk metrics from findings.

    Returns:
        dict containing:
            - score: int (0 to 100, where 100 is perfectly secure, 0 is heavily compromised)
            - grade: str ("A+", "A", "B", "C", "D", "F")
            - risk_level: str ("Low", "Medium", "High", "Critical")
            - risk_index: float (aggregate weighted risk index from 0.0 to 10.0)
            - remediation_hours: int (estimated effort in engineering hours)
            - counts: Dict[str, int] (breakdown of findings by severity)
    """
    counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Info": 0}
    for f in findings:
        sev = str(f.get("severity", "Info")).strip().capitalize()
        if sev not in counts:
            sev = "Info"
        counts[sev] += 1

    total_deduction = (
        counts["Critical"] * 25
        + counts["High"] * 12
        + counts["Medium"] * 5
        + counts["Low"] * 1
    )
    score = max(0, 100 - total_deduction)

    if score >= 97:
        grade = "A+"
    elif score >= 90:
        grade = "A"
    elif score >= 80:
        grade = "B"
    elif score >= 70:
        grade = "C"
    elif score >= 60:
        grade = "D"
    else:
        grade = "F"

    if counts["Critical"] > 0 or score < 50:
        risk_level = "Critical"
    elif counts["High"] > 0 or score < 70:
        risk_level = "High"
    elif counts["Medium"] > 0 or score < 85:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    weighted_sum = (
        counts["Critical"] * 10.0
        + counts["High"] * 7.5
        + counts["Medium"] * 4.0
        + counts["Low"] * 1.5
    )
    risk_index = round(min(10.0, weighted_sum / max(1, len(findings))), 1) if findings else 0.0

    remediation_hours = (
        counts["Critical"] * 16
        + counts["High"] * 8
        + counts["Medium"] * 4
        + counts["Low"] * 1
    )

    return {
        "score": score,
        "grade": grade,
        "risk_level": risk_level,
        "risk_index": risk_index,
        "remediation_hours": remediation_hours,
        "counts": counts,
    }


class ReportGenerator:
    """Generates security assessment reports."""

    calculate_security_posture = staticmethod(calculate_security_posture)

    def __init__(self, include_raw: bool = True, report_format: str = "html"):
        self.include_raw = include_raw
        self.report_format = report_format

    def generate(
        self,
        target: str,
        findings: List[Dict[str, Any]],
        tool_history: Optional[List[Dict[str, Any]]] = None,
        scripts: Optional[List[Dict[str, Any]]] = None,
        scope: str = "",
        summary: str = "",
        start_time: float = 0,
    ) -> str:
        """Generate a report and return the file path."""
        fmt = (self.report_format or "html").lower()
        if fmt == "html":
            return self._generate_html(target, findings, tool_history, scripts, scope, summary, start_time)
        elif fmt == "markdown":
            return self._generate_markdown(target, findings, tool_history, scripts, scope, summary, start_time)
        elif fmt == "json":
            return self._generate_json(target, findings, tool_history, scripts, scope, summary, start_time)
        elif fmt in ("sarif", "sarif.json"):
            return self._generate_sarif(target, findings, tool_history, scripts, scope, summary, start_time)
        elif fmt == "csv":
            return self._generate_csv(target, findings, tool_history, scripts, scope, summary, start_time)
        else:
            return self._generate_html(target, findings, tool_history, scripts, scope, summary, start_time)

    def _generate_html(
        self, target, findings, tool_history, scripts, scope, summary, start_time
    ) -> str:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = REPORTS_DIR / f"report_{target.replace('/', '_').replace(':', '_')}_{ts}.html"

        severity_counts: Dict[str, int] = {}
        for f in findings:
            sev = f.get("severity", "Info")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        duration = ""
        if start_time:
            mins = (time.time() - start_time) / 60
            duration = f"{mins:.0f} minutes"

        template = Template(HTML_TEMPLATE)
        normalized_tool_history = self._normalize_tool_history(tool_history)
        normalized_scripts = self._normalize_scripts(scripts)
        posture = calculate_security_posture(findings)
        html = template.render(
            target=target,
            date=time.strftime("%Y-%m-%d %H:%M:%S"),
            scope=scope,
            duration=duration,
            severity_counts=severity_counts,
            total_findings=len(findings),
            summary=summary,
            findings=findings,
            tool_history=normalized_tool_history,
            scripts=normalized_scripts,
            include_raw=self.include_raw,
            posture=posture,
        )

        with open(path, "w", encoding="utf-8") as f:
            f.write(html)

        return str(path)

    def _generate_markdown(
        self, target, findings, tool_history, scripts, scope, summary, start_time
    ) -> str:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = REPORTS_DIR / f"report_{target.replace('/', '_').replace(':', '_')}_{ts}.md"

        lines = [
            "# HackBot Security Report",
            "",
            f"**Target:** {target}",
            f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Scope:** {scope or 'Full Assessment'}",
            "",
        ]

        lines.append("## 1. Executive Summary")
        lines.append("")
        if summary:
            lines.extend([summary, ""])

        posture = calculate_security_posture(findings)
        lines.extend([
            f"**Security Posture Score:** {posture['score']} / 100 (Grade: {posture['grade']})  ",
            f"**Risk Level:** {posture['risk_level']} (Risk Index: {posture['risk_index']}/10.0)  ",
            f"**Remediation Effort Est.:** ~{posture['remediation_hours']} hours",
            "",
        ])

        # Risk Assessment Charts section
        severity_counts: Dict[str, int] = {}
        for finding in findings:
            sev = finding.get("severity", "Info")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        total = len(findings)

        lines.extend(["## 2. Risk Assessment Charts", ""])
        lines.append("| Severity | Count | Percentage |")
        lines.append("|----------|-------|------------|")
        for sev, count in severity_counts.items():
            pct = f"{count / total * 100:.0f}%" if total else "0%"
            lines.append(f"| {sev} | {count} | {pct} |")
        lines.append(f"| **Total** | **{total}** | **100%** |")
        lines.append("")

        lines.extend(["## 3. Detailed Findings", ""])

        for i, f in enumerate(findings, 1):
            sev = f.get("severity", "Info")
            lines.append(f"### {i}. [{sev}] {f.get('title', 'Untitled')}")
            lines.append("")
            lines.append(f"{f.get('description', '')}")
            if f.get("evidence"):
                lines.extend(["", "**Evidence:**", "```", f["evidence"], "```"])
            if f.get("recommendation"):
                lines.extend(["", f"**Recommendation:** {f['recommendation']}"])
            lines.append("")

        normalized_tool_history = self._normalize_tool_history(tool_history)

        if normalized_tool_history:
            lines.extend(["## 4. List of Commands Executed", ""])
            for entry in normalized_tool_history:
                status = "✓" if entry.get("success") else "✗"
                lines.append(
                    f"- {status} [{entry.get('tool', 'unknown')}] `{entry.get('command', '(no command)')}` "
                    f"(sudo={'yes' if entry.get('sudo_used') else 'no'}, "
                    f"exit={entry.get('return_code', '')}, {entry.get('duration', 0)}s)"
                )

            lines.extend(["", "## 5. Technical Annex (Agent Output)", ""])
            if self.include_raw:
                for i, entry in enumerate(normalized_tool_history, 1):
                    lines.extend([
                        f"### {i}. {entry.get('tool', 'unknown')}",
                        f"Command: `{entry.get('command', '(no command)')}`",
                        "```",
                        str(entry.get("annex_output", ""))[:8000],
                        "```",
                        "",
                    ])
            else:
                lines.append("Raw output export is disabled by configuration (`include_raw_output: false`).")

        normalized_scripts = self._normalize_scripts(scripts)
        if normalized_scripts:
            lines.extend(["", "## Generated Scripts", ""])
            for i, script in enumerate(normalized_scripts, 1):
                lines.append(
                    f"### {i}. {script.get('name', 'generated_script')} "
                    f"[{script.get('language', 'text')}]"
                )
                if script.get("description"):
                    lines.append(script.get("description", ""))
                if script.get("path"):
                    lines.append(f"Saved to: `{script.get('path')}`")
                lines.extend([
                    f"```{script.get('language', 'text')}",
                    script.get("content", ""),
                    "```",
                    "",
                ])

        lines.extend(["", "---", "*Generated by HackBot AI Cybersecurity Assistant*"])

        content = "\n".join(lines)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        return str(path)

    def _generate_json(
        self, target, findings, tool_history, scripts, scope, summary, start_time
    ) -> str:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = REPORTS_DIR / f"report_{target.replace('/', '_').replace(':', '_')}_{ts}.json"

        normalized_tool_history = self._normalize_tool_history(tool_history)

        severity_counts: Dict[str, int] = {}
        for f in findings:
            sev = f.get("severity", "Info")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        total = len(findings)

        risk_assessment = [
            {
                "severity": sev,
                "count": count,
                "percentage": f"{count / total * 100:.0f}%" if total else "0%",
            }
            for sev, count in severity_counts.items()
        ]

        data = {
            "target": target,
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "scope": scope,
            "summary": summary,
            "risk_assessment": risk_assessment,
            "security_posture": calculate_security_posture(findings),
            "findings": findings,
            "tool_history": normalized_tool_history,
            "commands_executed": [
                {
                    "index": i + 1,
                    "tool": e.get("tool", "unknown"),
                    "command": e.get("command", "(no command)"),
                    "sudo_used": bool(e.get("sudo_used", False)),
                    "success": bool(e.get("success", False)),
                    "return_code": e.get("return_code", ""),
                    "duration": e.get("duration", 0),
                }
                for i, e in enumerate(normalized_tool_history)
            ],
            "technical_annex": [
                {
                    "index": i + 1,
                    "tool": e.get("tool", "unknown"),
                    "command": e.get("command", "(no command)"),
                    "output": str(e.get("annex_output", "")) if self.include_raw else "",
                }
                for i, e in enumerate(normalized_tool_history)
            ],
            "scripts": self._normalize_scripts(scripts),
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return str(path)

    def _generate_sarif(
        self,
        target: str,
        findings: List[Dict[str, Any]],
        tool_history: Optional[List[Dict[str, Any]]] = None,
        scripts: Optional[List[Dict[str, Any]]] = None,
        scope: str = "",
        summary: str = "",
        start_time: float = 0,
    ) -> str:
        """Generate a SARIF 2.1.0 report for CI/CD and vulnerability tracking tools."""
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        clean_target = target.replace("/", "_").replace(":", "_") or "target"
        path = REPORTS_DIR / f"report_{clean_target}_{ts}.sarif"

        rules: List[Dict[str, Any]] = []
        results: List[Dict[str, Any]] = []
        rule_map: Dict[str, int] = {}

        severity_to_sarif_level = {
            "critical": "error",
            "high": "error",
            "medium": "warning",
            "low": "note",
            "info": "none",
        }
        severity_to_score = {
            "critical": "9.5",
            "high": "8.0",
            "medium": "5.5",
            "low": "2.5",
            "info": "0.0",
        }

        for idx, f in enumerate(findings):
            title = str(f.get("title", f"Finding {idx + 1}") or f"Finding {idx + 1}").strip()
            sev = str(f.get("severity", "Info")).strip().lower()
            cvss = f.get("cvss") or severity_to_score.get(sev, "0.0")
            desc = str(f.get("description", "") or title)
            recom = str(f.get("recommendation", "") or "")
            evidence = str(f.get("evidence", "") or "")
            rule_id = str(f.get("id") or f.get("cve") or f"HB-{idx + 1:04d}")

            if rule_id not in rule_map:
                rule_idx = len(rules)
                rule_map[rule_id] = rule_idx
                rule_name = re.sub(r"[^A-Za-z0-9_]", "", title) or f"FindingRule_{idx + 1}"
                rule_def: Dict[str, Any] = {
                    "id": rule_id,
                    "name": rule_name,
                    "shortDescription": {"text": title},
                    "fullDescription": {"text": desc},
                    "defaultConfiguration": {
                        "level": severity_to_sarif_level.get(sev, "warning"),
                    },
                    "properties": {
                        "security-severity": str(cvss),
                        "tags": ["security", sev],
                    },
                }
                if recom:
                    rule_def["help"] = {"text": f"Recommendation: {recom}"}
                rules.append(rule_def)
            else:
                rule_idx = rule_map[rule_id]

            message_text = f"{title}: {desc}"
            if evidence:
                message_text += f"\nEvidence: {evidence}"

            res: Dict[str, Any] = {
                "ruleId": rule_id,
                "ruleIndex": rule_idx,
                "level": severity_to_sarif_level.get(sev, "warning"),
                "message": {"text": message_text},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": target or "unknown-target",
                            },
                        }
                    }
                ],
            }
            results.append(res)

        sarif_data = {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "HackBot",
                            "version": __version__,
                            "informationUri": "https://github.com/yashab-cyber/hackbot",
                            "rules": rules,
                        }
                    },
                    "results": results,
                }
            ],
        }

        with open(path, "w", encoding="utf-8") as outfile:
            json.dump(sarif_data, outfile, indent=2, ensure_ascii=False)

        return str(path)

    def _generate_csv(
        self,
        target: str,
        findings: List[Dict[str, Any]],
        tool_history: Optional[List[Dict[str, Any]]] = None,
        scripts: Optional[List[Dict[str, Any]]] = None,
        scope: str = "",
        summary: str = "",
        start_time: float = 0,
    ) -> str:
        """Generate a structured CSV report for spreadsheet analysis."""
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        clean_target = target.replace("/", "_").replace(":", "_") or "target"
        path = REPORTS_DIR / f"report_{clean_target}_{ts}.csv"

        headers = ["Title", "Severity", "CVSS", "Tool", "Description", "Evidence", "Recommendation"]

        with open(path, "w", newline="", encoding="utf-8") as outfile:
            writer = csv.writer(outfile)
            writer.writerow(headers)
            for f_dict in findings:
                writer.writerow([
                    str(f_dict.get("title", "")),
                    str(f_dict.get("severity", "Info")),
                    str(f_dict.get("cvss", "")),
                    str(f_dict.get("tool", "")),
                    str(f_dict.get("description", "")),
                    str(f_dict.get("evidence", "")),
                    str(f_dict.get("recommendation", "")),
                ])

        return str(path)


    @staticmethod
    def _normalize_tool_history(tool_history: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Ensure each tool log entry has explicit tool and command values for reporting."""
        normalized: List[Dict[str, Any]] = []
        for entry in tool_history or []:
            cmd = str(entry.get("command", "") or "").strip()
            tool = str(entry.get("tool", "") or "").strip()
            if not tool and cmd:
                tool = cmd.split()[0]

            out = dict(entry)
            out["tool"] = tool or "unknown"
            out["command"] = cmd or "(no command)"
            out["sudo_used"] = out["command"].startswith("sudo ")

            stdout = str(out.get("stdout", "") or "")
            stderr = str(out.get("stderr", "") or "")
            if stdout and stderr:
                out["annex_output"] = f"{stdout}\n\n[STDERR]\n{stderr}"
            elif stdout:
                out["annex_output"] = stdout
            elif stderr:
                out["annex_output"] = f"[STDERR]\n{stderr}"
            else:
                out["annex_output"] = "(no output)"
            normalized.append(out)
        return normalized

    @staticmethod
    def _normalize_scripts(scripts: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Normalize generated script entries for report rendering."""
        normalized: List[Dict[str, Any]] = []
        for script in scripts or []:
            out = dict(script)
            out["name"] = str(out.get("name", "generated_script") or "generated_script").strip()
            out["language"] = str(out.get("language", "text") or "text").strip()
            out["content"] = str(out.get("content", "") or "")
            out["description"] = str(out.get("description") or out.get("purpose") or "")
            out["path"] = str(out.get("path", "") or "")
            normalized.append(out)
        return normalized
