"""
HackBot Professional PDF Report Generator
============================================
Generates polished penetration testing reports with:
  • Cover page with assessment metadata
  • Table of contents
  • Executive summary with key metrics
  • Risk matrix chart (severity × likelihood)
  • Severity distribution pie/bar charts
  • Detailed findings with evidence and recommendations
  • Compliance mapping summary (if available)
  • Tool execution log
  • Professional footer with page numbers

Dependencies: reportlab, matplotlib, Pillow
"""

from __future__ import annotations

import io
import time
from typing import Any, Dict, List, Optional

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        Image,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

from hackbot.config import REPORTS_DIR


# ── Colour Palette ───────────────────────────────────────────────────────────

if HAS_REPORTLAB:
    _DARK_BG = colors.HexColor("#0d1117")
    _SURFACE = colors.HexColor("#161b22")
    _BORDER = colors.HexColor("#30363d")
    _TEXT = colors.HexColor("#c9d1d9")
    _TEXT_DIM = colors.HexColor("#8b949e")
    _ACCENT = colors.HexColor("#58a6ff")
    _GREEN = colors.HexColor("#3fb950")
    _WHITE = colors.white
    _BLACK = colors.black

    SEVERITY_COLORS = {
        "Critical": colors.HexColor("#f85149"),
        "High": colors.HexColor("#f0883e"),
        "Medium": colors.HexColor("#d29922"),
        "Low": colors.HexColor("#58a6ff"),
        "Info": colors.HexColor("#8b949e"),
    }
else:
    _DARK_BG = _SURFACE = _BORDER = _TEXT = _TEXT_DIM = _ACCENT = _GREEN = _WHITE = _BLACK = None
    SEVERITY_COLORS = {}

SEVERITY_COLORS_MPL = {
    "Critical": "#f85149",
    "High": "#f0883e",
    "Medium": "#d29922",
    "Low": "#58a6ff",
    "Info": "#8b949e",
}

SEVERITY_ORDER = ["Critical", "High", "Medium", "Low", "Info"]

# Likelihood levels for risk matrix
LIKELIHOOD_LEVELS = ["Very Low", "Low", "Medium", "High", "Very High"]

# Risk matrix: severity (rows) × likelihood (cols) → risk score colour
_RISK_MATRIX = {
    ("Critical", "Very High"): "Critical",
    ("Critical", "High"): "Critical",
    ("Critical", "Medium"): "Critical",
    ("Critical", "Low"): "High",
    ("Critical", "Very Low"): "High",
    ("High", "Very High"): "Critical",
    ("High", "High"): "High",
    ("High", "Medium"): "High",
    ("High", "Low"): "Medium",
    ("High", "Very Low"): "Medium",
    ("Medium", "Very High"): "High",
    ("Medium", "High"): "High",
    ("Medium", "Medium"): "Medium",
    ("Medium", "Low"): "Medium",
    ("Medium", "Very Low"): "Low",
    ("Low", "Very High"): "Medium",
    ("Low", "High"): "Medium",
    ("Low", "Medium"): "Low",
    ("Low", "Low"): "Low",
    ("Low", "Very Low"): "Info",
    ("Info", "Very High"): "Low",
    ("Info", "High"): "Low",
    ("Info", "Medium"): "Info",
    ("Info", "Low"): "Info",
    ("Info", "Very Low"): "Info",
}


# ── Chart Generators ─────────────────────────────────────────────────────────

def _severity_bar_chart(severity_counts: Dict[str, int]) -> Optional[bytes]:
    """Create a severity distribution bar chart, returned as PNG bytes."""
    if not HAS_MATPLOTLIB:
        return None

    labels = [s for s in SEVERITY_ORDER if severity_counts.get(s, 0) > 0]
    values = [severity_counts.get(s, 0) for s in labels]
    bar_colors = [SEVERITY_COLORS_MPL.get(s, "#8b949e") for s in labels]

    if not labels:
        return None

    fig, ax = plt.subplots(figsize=(5.5, 2.8))
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#161b22")

    bars = ax.barh(labels[::-1], values[::-1], color=bar_colors[::-1],
                   edgecolor="#30363d", linewidth=0.5, height=0.6)

    for bar, val in zip(bars, values[::-1]):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                str(val), va="center", ha="left", color="#c9d1d9",
                fontsize=10, fontweight="bold")

    ax.set_xlabel("Count", color="#8b949e", fontsize=9)
    ax.set_title("Findings by Severity", color="#c9d1d9", fontsize=12,
                 fontweight="bold", pad=10)
    ax.tick_params(colors="#c9d1d9", labelsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color("#30363d")
    ax.spines["left"].set_color("#30363d")
    ax.set_xlim(0, max(values) * 1.35 if values else 1)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def _severity_pie_chart(severity_counts: Dict[str, int]) -> Optional[bytes]:
    """Create a severity distribution pie/donut chart."""
    if not HAS_MATPLOTLIB:
        return None

    labels = [s for s in SEVERITY_ORDER if severity_counts.get(s, 0) > 0]
    values = [severity_counts.get(s, 0) for s in labels]
    pie_colors = [SEVERITY_COLORS_MPL.get(s, "#8b949e") for s in labels]

    if not labels:
        return None

    fig, ax = plt.subplots(figsize=(3.5, 3.5))
    fig.patch.set_facecolor("#0d1117")

    wedges, texts, autotexts = ax.pie(
        values, labels=labels, colors=pie_colors, autopct="%1.0f%%",
        startangle=90, pctdistance=0.75, textprops={"color": "#c9d1d9", "fontsize": 9},
        wedgeprops={"edgecolor": "#0d1117", "linewidth": 2},
    )
    for t in autotexts:
        t.set_fontsize(8)
        t.set_fontweight("bold")

    # Donut hole
    centre_circle = plt.Circle((0, 0), 0.50, fc="#0d1117")
    ax.add_artist(centre_circle)
    ax.text(0, 0, str(sum(values)), ha="center", va="center",
            fontsize=18, fontweight="bold", color="#3fb950")

    ax.set_title("Severity Distribution", color="#c9d1d9", fontsize=11,
                 fontweight="bold", pad=10)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def _risk_matrix_chart(severity_counts: Dict[str, int]) -> Optional[bytes]:
    """Create a 5×5 risk matrix heat-map with finding counts overlaid."""
    if not HAS_MATPLOTLIB:
        return None

    risk_colors_mpl = {
        "Critical": "#f85149",
        "High": "#f0883e",
        "Medium": "#d29922",
        "Low": "#58a6ff",
        "Info": "#3d444d",
    }

    fig, ax = plt.subplots(figsize=(5.0, 4.0))
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#0d1117")

    sev_rows = SEVERITY_ORDER[::-1]  # Info at bottom, Critical at top
    lik_cols = LIKELIHOOD_LEVELS

    for i, sev in enumerate(sev_rows):
        for j, lik in enumerate(lik_cols):
            risk = _RISK_MATRIX.get((sev, lik), "Info")
            c = risk_colors_mpl.get(risk, "#3d444d")
            rect = plt.Rectangle((j, i), 1, 1, facecolor=c, edgecolor="#0d1117",
                                 linewidth=2, alpha=0.7)
            ax.add_patch(rect)
            ax.text(j + 0.5, i + 0.5, risk[0],
                    ha="center", va="center", fontsize=9,
                    color="white", fontweight="bold")

    # Overlay finding counts on the severity axis (rightmost "High" likelihood column)
    for i, sev in enumerate(sev_rows):
        count = severity_counts.get(sev, 0)
        if count > 0:
            ax.text(5.3, i + 0.5, f"×{count}", ha="left", va="center",
                    color=risk_colors_mpl.get(sev, "#8b949e"), fontsize=10,
                    fontweight="bold")

    ax.set_xlim(0, 5)
    ax.set_ylim(0, 5)
    ax.set_xticks([x + 0.5 for x in range(5)])
    ax.set_xticklabels(lik_cols, fontsize=8, color="#c9d1d9")
    ax.set_yticks([y + 0.5 for y in range(5)])
    ax.set_yticklabels(sev_rows, fontsize=8, color="#c9d1d9")

    ax.set_xlabel("Likelihood", color="#8b949e", fontsize=9, labelpad=8)
    ax.set_ylabel("Impact / Severity", color="#8b949e", fontsize=9, labelpad=8)
    ax.set_title("Risk Matrix", color="#c9d1d9", fontsize=12,
                 fontweight="bold", pad=12)

    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


# ── Styles ───────────────────────────────────────────────────────────────────

def _build_styles() -> Dict[str, ParagraphStyle]:
    """Build paragraph styles for the PDF."""
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "CoverTitle", parent=base["Title"],
            fontSize=28, leading=34, textColor=_GREEN,
            alignment=TA_CENTER, spaceAfter=6,
        ),
        "cover_subtitle": ParagraphStyle(
            "CoverSubtitle", parent=base["Normal"],
            fontSize=14, leading=18, textColor=_ACCENT,
            alignment=TA_CENTER, spaceAfter=20,
        ),
        "cover_meta": ParagraphStyle(
            "CoverMeta", parent=base["Normal"],
            fontSize=11, leading=16, textColor=_TEXT,
            alignment=TA_CENTER, spaceAfter=4,
        ),
        "h1": ParagraphStyle(
            "H1", parent=base["Heading1"],
            fontSize=18, leading=24, textColor=_GREEN,
            spaceBefore=20, spaceAfter=10,
            borderWidth=1, borderColor=_BORDER, borderPadding=4,
        ),
        "h2": ParagraphStyle(
            "H2", parent=base["Heading2"],
            fontSize=14, leading=18, textColor=_ACCENT,
            spaceBefore=14, spaceAfter=6,
        ),
        "h3": ParagraphStyle(
            "H3", parent=base["Heading3"],
            fontSize=12, leading=16, textColor=_TEXT,
            spaceBefore=10, spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "Body", parent=base["Normal"],
            fontSize=10, leading=14, textColor=_TEXT,
            alignment=TA_JUSTIFY, spaceAfter=6,
        ),
        "body_dim": ParagraphStyle(
            "BodyDim", parent=base["Normal"],
            fontSize=9, leading=13, textColor=_TEXT_DIM,
            spaceAfter=4,
        ),
        "finding_title": ParagraphStyle(
            "FindingTitle", parent=base["Heading3"],
            fontSize=12, leading=16, textColor=_WHITE,
            spaceBefore=6, spaceAfter=2,
        ),
        "evidence": ParagraphStyle(
            "Evidence", parent=base["Code"],
            fontSize=8, leading=11, textColor=colors.HexColor("#e6edf3"),
            backColor=colors.HexColor("#161b22"),
            borderWidth=1, borderColor=_BORDER, borderPadding=6,
            spaceAfter=6, spaceBefore=4,
        ),
        "recommendation": ParagraphStyle(
            "Recommendation", parent=base["Normal"],
            fontSize=9.5, leading=14, textColor=_ACCENT,
            leftIndent=12, borderWidth=0, spaceAfter=6,
            borderPadding=4,
        ),
        "toc": ParagraphStyle(
            "TOC", parent=base["Normal"],
            fontSize=11, leading=18, textColor=_ACCENT,
            spaceAfter=4, leftIndent=10,
        ),
        "footer": ParagraphStyle(
            "Footer", parent=base["Normal"],
            fontSize=8, leading=10, textColor=_TEXT_DIM,
            alignment=TA_CENTER,
        ),
    }


# ── PDF Report Builder ───────────────────────────────────────────────────────

class PDFReportGenerator:
    """
    Generates a professional penetration testing PDF report.

    Usage::

        gen = PDFReportGenerator()
        path = gen.generate(
            target="example.com",
            findings=[...],          # list of finding dicts
            tool_history=[...],      # list of tool execution dicts
            scope="Full external assessment",
            summary="Two critical findings...",
            start_time=time.time(),
            compliance_data=None,    # optional ComplianceReport.to_dict()
        )
    """

    def __init__(self, include_raw: bool = True):
        if not HAS_REPORTLAB:
            raise ImportError(
                "reportlab is required for PDF reports. "
                "Install it with: pip install 'hackbot[pdf]'"
            )
        self.include_raw = include_raw
        self.styles = _build_styles()
        self._page_width, self._page_height = A4

    # ── Public API ───────────────────────────────────────────────────────

    def generate(
        self,
        target: str,
        findings: List[Dict[str, Any]],
        tool_history: Optional[List[Dict[str, Any]]] = None,
        scripts: Optional[List[Dict[str, Any]]] = None,
        scope: str = "",
        summary: str = "",
        start_time: float = 0,
        compliance_data: Optional[Dict[str, Any]] = None,
        attack_data: Optional[Dict[str, Any]] = None,
        agent_steps: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Generate PDF report, return file path."""
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        safe_target = target.replace("/", "_").replace(":", "_").replace(" ", "_")
        path = REPORTS_DIR / f"report_{safe_target}_{ts}.pdf"

        severity_counts = self._count_severities(findings)
        duration = ""
        if start_time:
            mins = (time.time() - start_time) / 60
            duration = f"{mins:.0f} minutes"

        doc = SimpleDocTemplate(
            str(path),
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2.5 * cm,
            bottomMargin=2 * cm,
        )

        story: List[Any] = []

        # Cover page
        story.extend(self._cover_page(target, scope, duration, severity_counts, findings))

        # Table of contents
        story.append(PageBreak())
        story.extend(self._table_of_contents(findings, tool_history, scripts, compliance_data, attack_data, agent_steps))

        # Executive summary
        story.append(PageBreak())
        story.extend(self._executive_summary(
            target, findings, severity_counts, summary, scope, duration,
        ))

        # Charts
        story.extend(self._charts_section(severity_counts))

        # Detailed findings
        story.append(PageBreak())
        story.extend(self._findings_section(findings))

        # 4. Commands executed / 5. Technical annex
        if tool_history:
            story.append(PageBreak())
            story.extend(self._tool_log_section(tool_history))
            story.append(PageBreak())
            story.extend(self._technical_annex_section(tool_history))

        # Compliance mapping (optional)
        if compliance_data:
            story.append(PageBreak())
            story.extend(self._compliance_section(compliance_data))

        # ATT&CK mapping (optional)
        if attack_data:
            story.append(PageBreak())
            story.extend(self._attack_section(attack_data))

        # Generated scripts / exploits
        if scripts:
            story.append(PageBreak())
            story.extend(self._scripts_section(scripts))

        # Agent Execution Log
        if agent_steps:
            story.append(PageBreak())
            story.extend(self._agent_log_section(agent_steps))

        # Build PDF
        doc.build(story, onFirstPage=self._page_footer, onLaterPages=self._page_footer)

        return str(path)

    # ── Cover Page ───────────────────────────────────────────────────────

    def _cover_page(
        self, target, scope, duration, severity_counts, findings,
    ) -> list:
        s = self.styles
        elements = []

        elements.append(Spacer(1, 4 * cm))
        elements.append(Paragraph("⚡ HackBot", s["cover_title"]))
        elements.append(Paragraph("Penetration Testing Report", s["cover_subtitle"]))
        elements.append(Spacer(1, 1.5 * cm))

        meta_data = [
            ["Target", target],
            ["Date", time.strftime("%B %d, %Y")],
            ["Scope", scope or "Full Assessment"],
        ]
        if duration:
            meta_data.append(["Duration", duration])

        meta_table = Table(meta_data, colWidths=[4 * cm, 10 * cm])
        meta_table.setStyle(TableStyle([
            ("TEXTCOLOR", (0, 0), (0, -1), _TEXT_DIM),
            ("TEXTCOLOR", (1, 0), (1, -1), _TEXT),
            ("FONTSIZE", (0, 0), (-1, -1), 11),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("ALIGN", (0, 0), (0, -1), "RIGHT"),
            ("ALIGN", (1, 0), (1, -1), "LEFT"),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica"),
            ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ]))
        elements.append(meta_table)

        elements.append(Spacer(1, 2 * cm))

        # Quick severity summary cards
        card_data = [[""] + SEVERITY_ORDER + ["Total"]]
        card_values = [""] + [str(severity_counts.get(sev, 0)) for sev in SEVERITY_ORDER]
        card_values.append(str(len(findings)))
        card_data.append(card_values)

        card_table = Table(card_data, colWidths=[0.5 * cm] + [2.3 * cm] * 6)
        card_style = [
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TEXTCOLOR", (0, 0), (-1, 0), _TEXT_DIM),
            ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
            ("LINEBELOW", (1, 0), (-1, 0), 0.5, _BORDER),
            ("GRID", (1, 0), (-1, -1), 0.5, _BORDER),
            ("BACKGROUND", (1, 0), (-1, -1), _SURFACE),
        ]
        for i, sev in enumerate(SEVERITY_ORDER):
            col = i + 1
            card_style.append(("TEXTCOLOR", (col, 1), (col, 1), SEVERITY_COLORS.get(sev, _TEXT)))
        card_style.append(("TEXTCOLOR", (-1, 1), (-1, 1), _GREEN))

        card_table.setStyle(TableStyle(card_style))
        elements.append(card_table)

        elements.append(Spacer(1, 3 * cm))
        elements.append(Paragraph(
            f"<i>Generated by HackBot AI Cybersecurity Assistant — {time.strftime('%Y-%m-%d %H:%M:%S')}</i>",
            s["cover_meta"]
        ))

        return elements

    # ── Table of Contents ────────────────────────────────────────────────

    def _table_of_contents(self, findings, tool_history, scripts, compliance_data, attack_data=None, agent_steps=None) -> list:
        s = self.styles
        elements = [Paragraph("Table of Contents", s["h1"])]

        sections = [
            "1. Executive Summary",
            "2. Risk Assessment Charts",
            "3. Detailed Findings",
        ]
        if tool_history:
            sections.append("4. List of Commands Executed")
            sections.append("5. Technical Annex (Agent Output)")

        idx = 6
        if compliance_data:
            sections.append(f"{idx}. Compliance Mapping")
            idx += 1
        if attack_data:
            sections.append(f"{idx}. MITRE ATT&CK Mapping")
            idx += 1
        if scripts:
            sections.append(f"{idx}. Generated Scripts")
            idx += 1
        if agent_steps:
            sections.append(f"{idx}. Agent Execution Log")
            idx += 1

        for section in sections:
            elements.append(Paragraph(f"• {section}", s["toc"]))

        if findings:
            elements.append(Spacer(1, 0.5 * cm))
            elements.append(Paragraph("Findings Index", s["h2"]))
            for i, f in enumerate(findings, 1):
                sev = f.get("severity", "Info")
                color = SEVERITY_COLORS_MPL.get(sev, "#8b949e")
                elements.append(Paragraph(
                    f'<font color="{color}">▪ [{sev}]</font> {i}. {self._safe(f.get("title", "Untitled"))}',
                    s["body"],
                ))

        return elements

    def _scripts_section(self, scripts: List[Dict[str, Any]]) -> list:
        """Render generated scripts/exploits included in the assessment."""
        s = self.styles
        elements = [Paragraph("Generated Scripts", s["h1"])]

        if not scripts:
            elements.append(Paragraph("No scripts were generated.", s["body_dim"]))
            return elements

        for idx, script in enumerate(scripts[:50], 1):
            name = self._safe(str(script.get("name", f"script_{idx}")))
            language = self._safe(str(script.get("language", "text")))
            desc = self._safe(str(script.get("description") or script.get("purpose") or ""))
            path = self._safe(str(script.get("path", "")))
            content = str(script.get("content", "") or "")

            elements.append(Paragraph(f"{idx}. {name} [{language}]", s["finding_title"]))
            if desc:
                elements.append(Paragraph(desc, s["body"]))
            if path:
                elements.append(Paragraph(f"Saved to: {path}", s["body_dim"]))

            snippet = content[:3000]
            if len(content) > 3000:
                snippet += "\n... [truncated]"
            if snippet:
                elements.append(Paragraph(
                    self._safe(snippet).replace("\n", "<br/>"),
                    s["evidence"],
                ))

            elements.append(Spacer(1, 0.25 * cm))

        return elements

    # ── Executive Summary ────────────────────────────────────────────────

    def _executive_summary(
        self, target, findings, severity_counts, summary, scope, duration,
    ) -> list:
        s = self.styles
        elements = [Paragraph("1. Executive Summary", s["h1"])]

        if summary:
            elements.append(Paragraph(self._safe(summary), s["body"]))
            elements.append(Spacer(1, 0.3 * cm))

        # Overview paragraph
        total = len(findings)
        crit = severity_counts.get("Critical", 0)
        high = severity_counts.get("High", 0)

        risk_level = "Critical" if crit > 0 else "High" if high > 0 else "Medium" if severity_counts.get("Medium", 0) > 0 else "Low"
        risk_color = SEVERITY_COLORS_MPL.get(risk_level, "#8b949e")

        overview = (
            f'A security assessment of <b>{self._safe(target)}</b> identified '
            f'<b>{total}</b> findings. '
            f'The overall risk level is assessed as '
            f'<font color="{risk_color}"><b>{risk_level}</b></font>. '
        )
        if crit > 0 or high > 0:
            overview += (
                f'There are <font color="{SEVERITY_COLORS_MPL["Critical"]}"><b>{crit}</b> critical</font> '
                f'and <font color="{SEVERITY_COLORS_MPL["High"]}"><b>{high}</b> high</font> severity findings '
                f"requiring immediate attention."
            )
        elements.append(Paragraph(overview, s["body"]))
        elements.append(Spacer(1, 0.4 * cm))

        # Severity summary table
        elements.append(Paragraph("Findings Summary", s["h2"]))

        header = ["Severity", "Count", "Percentage", "Risk Level"]
        rows = [header]
        for sev in SEVERITY_ORDER:
            count = severity_counts.get(sev, 0)
            pct = f"{count / total * 100:.0f}%" if total else "0%"
            rows.append([sev, str(count), pct, self._risk_label(sev)])

        rows.append(["Total", str(total), "100%", ""])

        col_widths = [3.5 * cm, 2.5 * cm, 3 * cm, 5 * cm]
        table = Table(rows, colWidths=col_widths)

        table_style = [
            ("BACKGROUND", (0, 0), (-1, 0), _ACCENT),
            ("TEXTCOLOR", (0, 0), (-1, 0), _WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (1, 0), (2, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [_SURFACE, colors.HexColor("#1c2128")]),
            ("TEXTCOLOR", (0, 1), (-1, -1), _TEXT),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#1c2128")),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ]

        # Color-code severity names
        for i, sev in enumerate(SEVERITY_ORDER):
            table_style.append(
                ("TEXTCOLOR", (0, i + 1), (0, i + 1), SEVERITY_COLORS.get(sev, _TEXT))
            )

        table.setStyle(TableStyle(table_style))
        elements.append(table)

        return elements

    # ── Charts Section ───────────────────────────────────────────────────

    def _charts_section(self, severity_counts: Dict[str, int]) -> list:
        s = self.styles
        elements = []

        if not HAS_MATPLOTLIB:
            elements.append(Paragraph("2. Risk Assessment Charts", s["h1"]))
            elements.append(Paragraph(
                "<i>Charts unavailable — install matplotlib for visual charts.</i>",
                s["body_dim"],
            ))
            return elements

        elements.append(Paragraph("2. Risk Assessment Charts", s["h1"]))

        # Bar chart
        bar_png = _severity_bar_chart(severity_counts)
        if bar_png:
            elements.append(Paragraph("Severity Distribution", s["h2"]))
            elements.append(Image(io.BytesIO(bar_png), width=14 * cm, height=7.5 * cm))
            elements.append(Spacer(1, 0.3 * cm))

        # Pie chart + risk matrix side by side if both exist
        pie_png = _severity_pie_chart(severity_counts)
        risk_png = _risk_matrix_chart(severity_counts)

        if pie_png and risk_png:
            elements.append(Paragraph("Risk Assessment", s["h2"]))
            chart_table = Table(
                [[
                    Image(io.BytesIO(pie_png), width=7.5 * cm, height=7.5 * cm),
                    Image(io.BytesIO(risk_png), width=8.5 * cm, height=7 * cm),
                ]],
                colWidths=[8 * cm, 9 * cm],
            )
            chart_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]))
            elements.append(chart_table)
        else:
            if pie_png:
                elements.append(Paragraph("Severity Breakdown", s["h2"]))
                elements.append(Image(io.BytesIO(pie_png), width=9 * cm, height=9 * cm))
            if risk_png:
                elements.append(Paragraph("Risk Matrix", s["h2"]))
                elements.append(Image(io.BytesIO(risk_png), width=12 * cm, height=10 * cm))

        return elements

    # ── Detailed Findings ────────────────────────────────────────────────

    def _findings_section(self, findings: List[Dict[str, Any]]) -> list:
        s = self.styles
        elements = [Paragraph("3. Detailed Findings", s["h1"])]

        if not findings:
            elements.append(Paragraph("No findings recorded.", s["body_dim"]))
            return elements

        for i, f in enumerate(findings, 1):
            sev = f.get("severity", "Info")
            color = SEVERITY_COLORS_MPL.get(sev, "#8b949e")

            elements.append(Paragraph(
                f'<font color="{color}"><b>[{sev}]</b></font> '
                f'{i}. {self._safe(f.get("title", "Untitled"))}',
                s["finding_title"],
            ))

            # Meta row
            meta_parts = []
            if f.get("tool"):
                meta_parts.append(f"Tool: {f['tool']}")
            meta_parts.append(f"Severity: {sev}")
            elements.append(Paragraph(" | ".join(meta_parts), s["body_dim"]))

            # Description
            desc = f.get("description", "")
            if desc:
                elements.append(Paragraph(self._safe(desc), s["body"]))

            # Evidence
            evidence = f.get("evidence", "")
            if evidence and self.include_raw:
                elements.append(Paragraph("<b>Evidence:</b>", s["body"]))
                # Truncate very long evidence
                ev_text = evidence[:3000]
                if len(evidence) > 3000:
                    ev_text += "\n... [truncated]"
                elements.append(Paragraph(
                    self._safe(ev_text).replace("\n", "<br/>"),
                    s["evidence"],
                ))

            # Recommendation
            rec = f.get("recommendation", "")
            if rec:
                elements.append(Paragraph(
                    f'<b>Recommendation:</b> {self._safe(rec)}', s["recommendation"],
                ))

            elements.append(Spacer(1, 0.4 * cm))

            # Separator line between findings
            if i < len(findings):
                sep = Table([[""]], colWidths=[self._page_width - 4 * cm])
                sep.setStyle(TableStyle([
                    ("LINEBELOW", (0, 0), (-1, -1), 0.5, _BORDER),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]))
                elements.append(sep)

        return elements

    # ── Compliance Section ───────────────────────────────────────────────

    def _compliance_section(self, compliance_data: Dict[str, Any]) -> list:
        s = self.styles
        elements = [Paragraph("Compliance Mapping", s["h1"])]

        summary_data = compliance_data.get("summary", {})
        if not summary_data:
            elements.append(Paragraph("No compliance mappings available.", s["body_dim"]))
            return elements

        # Summary table
        header = ["Framework", "Fail", "Warn", "Pass", "Not Tested", "Total"]
        rows = [header]
        for fw, counts in summary_data.items():
            f_count = counts.get("fail", 0)
            w_count = counts.get("warn", 0)
            p_count = counts.get("pass", 0)
            n_count = counts.get("not_tested", 0)
            total = f_count + w_count + p_count + n_count
            rows.append([fw, str(f_count), str(w_count), str(p_count), str(n_count), str(total)])

        col_w = [5.5 * cm, 1.8 * cm, 1.8 * cm, 1.8 * cm, 2.4 * cm, 1.8 * cm]
        table = Table(rows, colWidths=col_w)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _ACCENT),
            ("TEXTCOLOR", (0, 0), (-1, 0), _WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_SURFACE, colors.HexColor("#1c2128")]),
            ("TEXTCOLOR", (0, 1), (-1, -1), _TEXT),
            ("TEXTCOLOR", (1, 1), (1, -1), SEVERITY_COLORS["Critical"]),
            ("TEXTCOLOR", (2, 1), (2, -1), SEVERITY_COLORS["Medium"]),
            ("TEXTCOLOR", (3, 1), (3, -1), _GREEN),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.5 * cm))

        # Per-framework detail
        mappings_data = compliance_data.get("mappings", {})
        for fw, mappings in mappings_data.items():
            elements.append(Paragraph(fw, s["h2"]))

            header2 = ["Status", "Control", "Title", "Finding"]
            rows2 = [header2]
            for m in mappings[:50]:  # limit per framework
                ctrl = m.get("control", {})
                status = m.get("status", "")
                icon = {"fail": "FAIL", "warn": "WARN", "pass": "PASS", "not_tested": "N/T"}.get(status, status)
                rows2.append([
                    icon,
                    ctrl.get("control_id", ""),
                    ctrl.get("title", ""),
                    m.get("finding_title", ""),
                ])

            col_w2 = [2 * cm, 2.5 * cm, 5.5 * cm, 5 * cm]
            t2 = Table(rows2, colWidths=col_w2)
            style2 = [
                ("BACKGROUND", (0, 0), (-1, 0), _ACCENT),
                ("TEXTCOLOR", (0, 0), (-1, 0), _WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_SURFACE, colors.HexColor("#1c2128")]),
                ("TEXTCOLOR", (0, 1), (-1, -1), _TEXT),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
            # Color status column
            for ri, row in enumerate(rows2[1:], 1):
                status_text = row[0]
                if status_text == "FAIL":
                    style2.append(("TEXTCOLOR", (0, ri), (0, ri), SEVERITY_COLORS["Critical"]))
                elif status_text == "WARN":
                    style2.append(("TEXTCOLOR", (0, ri), (0, ri), SEVERITY_COLORS["Medium"]))
                elif status_text == "PASS":
                    style2.append(("TEXTCOLOR", (0, ri), (0, ri), _GREEN))

            t2.setStyle(TableStyle(style2))
            elements.append(t2)
            elements.append(Spacer(1, 0.3 * cm))

        return elements

    # ── ATT&CK Section ───────────────────────────────────────────────────

    def _attack_section(self, attack_data: Dict[str, Any]) -> list:
        s = self.styles
        elements = [Paragraph("MITRE ATT&CK Mapping", s["h1"])]

        total_mappings = attack_data.get("total_mappings", 0)
        unique_techs = attack_data.get("unique_techniques", 0)
        tactics_covered = attack_data.get("tactics_covered", 0)
        total_tactics = attack_data.get("total_tactics", 14)

        if not total_mappings:
            elements.append(Paragraph("No ATT&CK technique mappings available.", s["body_dim"]))
            return elements

        # Summary
        elements.append(Paragraph(
            f"<b>{unique_techs}</b> unique techniques across <b>{tactics_covered}</b>/"
            f"<b>{total_tactics}</b> tactics ({total_mappings} total mappings)",
            s["body"],
        ))
        elements.append(Spacer(1, 0.3 * cm))

        # Summary table: technique count per tactic
        by_tactic = attack_data.get("by_tactic", {})
        header = ["Tactic", "Techniques", "High", "Medium", "Low"]
        rows = [header]
        for tactic_name, mappings in by_tactic.items():
            seen_ids = set()
            conf_counts = {"high": 0, "medium": 0, "low": 0}
            for m in mappings:
                tech_id = m.get("technique", {}).get("id", "")
                if tech_id not in seen_ids:
                    seen_ids.add(tech_id)
                    conf = m.get("confidence", "medium")
                    conf_counts[conf] = conf_counts.get(conf, 0) + 1
            rows.append([
                tactic_name,
                str(len(seen_ids)),
                str(conf_counts["high"]),
                str(conf_counts["medium"]),
                str(conf_counts["low"]),
            ])

        col_w = [5.5 * cm, 2.5 * cm, 2 * cm, 2 * cm, 2 * cm]
        table = Table(rows, colWidths=col_w)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _ACCENT),
            ("TEXTCOLOR", (0, 0), (-1, 0), _WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_SURFACE, colors.HexColor("#1c2128")]),
            ("TEXTCOLOR", (0, 1), (-1, -1), _TEXT),
            ("TEXTCOLOR", (2, 1), (2, -1), SEVERITY_COLORS["Critical"]),
            ("TEXTCOLOR", (3, 1), (3, -1), SEVERITY_COLORS["Medium"]),
            ("TEXTCOLOR", (4, 1), (4, -1), SEVERITY_COLORS["Low"]),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.5 * cm))

        # Per-tactic detail
        for tactic_name, mappings in by_tactic.items():
            elements.append(Paragraph(tactic_name, s["h2"]))

            header2 = ["Technique", "Name", "Confidence", "Source", "Source Detail"]
            rows2 = [header2]
            seen_ids = set()
            for m in mappings:
                tech = m.get("technique", {})
                tech_id = tech.get("id", "")
                if tech_id in seen_ids:
                    continue
                seen_ids.add(tech_id)
                conf = m.get("confidence", "medium").upper()
                source = m.get("source", "")
                source_name = m.get("source_name", "")
                rows2.append([tech_id, tech.get("name", ""), conf, source, source_name])

            col_w2 = [2 * cm, 4.5 * cm, 2.2 * cm, 2 * cm, 4.3 * cm]
            t2 = Table(rows2, colWidths=col_w2)
            style2 = [
                ("BACKGROUND", (0, 0), (-1, 0), _ACCENT),
                ("TEXTCOLOR", (0, 0), (-1, 0), _WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_SURFACE, colors.HexColor("#1c2128")]),
                ("TEXTCOLOR", (0, 1), (-1, -1), _TEXT),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
            # Color confidence column
            for ri, row in enumerate(rows2[1:], 1):
                conf_text = row[2]
                if conf_text == "HIGH":
                    style2.append(("TEXTCOLOR", (2, ri), (2, ri), SEVERITY_COLORS["Critical"]))
                elif conf_text == "MEDIUM":
                    style2.append(("TEXTCOLOR", (2, ri), (2, ri), SEVERITY_COLORS["Medium"]))
                elif conf_text == "LOW":
                    style2.append(("TEXTCOLOR", (2, ri), (2, ri), SEVERITY_COLORS["Low"]))

            t2.setStyle(TableStyle(style2))
            elements.append(t2)
            elements.append(Spacer(1, 0.3 * cm))

        return elements

    # ── Tool Log Section ─────────────────────────────────────────────────

    def _tool_log_section(self, tool_history: List[Dict[str, Any]]) -> list:
        s = self.styles
        elements = [Paragraph("4. List of Commands Executed", s["h1"])]

        normalized = self._normalize_tool_history(tool_history)

        header = ["#", "Tool", "Sudo", "Command", "Status", "Duration", "Exit"]
        rows = [header]
        for i, entry in enumerate(normalized[:100], 1):
            cmd = entry.get("command", "")
            if len(cmd) > 70:
                cmd = cmd[:67] + "..."
            tool = entry.get("tool", "unknown")
            if len(tool) > 20:
                tool = tool[:17] + "..."
            success = entry.get("success", False)
            status = "OK" if success else "FAIL"
            dur = f"{entry.get('duration', 0):.1f}s"
            sudo = "Yes" if entry.get("sudo_used", False) else "No"
            rows.append([str(i), tool, sudo, cmd, status, dur, str(entry.get("return_code", ""))])

        col_w = [0.8 * cm, 1.8 * cm, 1.4 * cm, 6.0 * cm, 1.5 * cm, 1.8 * cm, 1.4 * cm]
        table = Table(rows, colWidths=col_w)
        style = [
            ("BACKGROUND", (0, 0), (-1, 0), _ACCENT),
            ("TEXTCOLOR", (0, 0), (-1, 0), _WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("FONTNAME", (1, 1), (3, -1), "Courier"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_SURFACE, colors.HexColor("#1c2128")]),
            ("TEXTCOLOR", (0, 1), (-1, -1), _TEXT),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (2, 0), (2, -1), "CENTER"),
            ("ALIGN", (4, 0), (-1, -1), "CENTER"),
        ]
        # Color status column
        for ri, row in enumerate(rows[1:], 1):
            if row[4] == "FAIL":
                style.append(("TEXTCOLOR", (4, ri), (4, ri), SEVERITY_COLORS["Critical"]))
            else:
                style.append(("TEXTCOLOR", (4, ri), (4, ri), _GREEN))

        table.setStyle(TableStyle(style))
        elements.append(table)

        return elements

    def _technical_annex_section(self, tool_history: List[Dict[str, Any]]) -> list:
        """Render technical annex with agent/tool output for each command."""
        s = self.styles
        elements = [Paragraph("5. Technical Annex (Agent Output)", s["h1"])]

        normalized = self._normalize_tool_history(tool_history)
        if not normalized:
            elements.append(Paragraph("No tool output available.", s["body_dim"]))
            return elements

        if not self.include_raw:
            elements.append(Paragraph(
                "Raw output export is disabled by configuration (include_raw_output: false).",
                s["body_dim"],
            ))
            return elements

        for i, entry in enumerate(normalized[:100], 1):
            elements.append(Paragraph(f"{i}. {self._safe(entry.get('tool', 'unknown'))}", s["h3"]))
            elements.append(Paragraph(
                f"<b>Command:</b> {self._safe(entry.get('command', '(no command)'))}",
                s["body_dim"],
            ))
            annex = str(entry.get("annex_output", "(no output)"))
            if len(annex) > 6000:
                annex = annex[:6000] + "\n... [truncated]"
            elements.append(Paragraph(self._safe(annex).replace("\n", "<br/>"), s["evidence"]))
            elements.append(Spacer(1, 0.25 * cm))

        return elements

    @staticmethod
    def _normalize_tool_history(tool_history: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Ensure each tool execution row has explicit tool and command fields."""
        normalized: List[Dict[str, Any]] = []
        for entry in tool_history or []:
            cmd = str(entry.get("command", "") or "").strip()
            tool = str(entry.get("tool", "") or "").strip()
            if not tool and cmd:
                parts = cmd.split()
                if parts[0] == "sudo" and len(parts) > 1:
                    tool = parts[1]
                else:
                    tool = parts[0]

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

    def _agent_log_section(self, agent_steps: List[Dict[str, Any]]) -> list:
        """Render the detailed AI agent execution log, including thoughts and outputs."""
        s = self.styles
        elements = [Paragraph("Agent Execution Log", s["h1"])]

        if not agent_steps:
            elements.append(Paragraph("No agent execution steps recorded.", s["body_dim"]))
            return elements

        for i, step in enumerate(agent_steps, 1):
            action = step.get("action", "unknown")
            tool_res = step.get("tool_result")
            if tool_res:
                title = f"Step {step.get('step_num', i)}: Execute Tool -> {tool_res.get('tool', 'unknown')}"
                status = "SUCCESS" if tool_res.get("success") else "FAILED"
            else:
                title = f"Step {step.get('step_num', i)}: Action -> {action.upper()}"
                status = ""

            elements.append(Paragraph(self._safe(title), s["h2"]))
            
            if status:
                color = _GREEN if status == "SUCCESS" else SEVERITY_COLORS["Critical"]
                status_xml = f'<font color="{color}">[{status}]</font>'
                elements.append(Paragraph(f"<b>Status:</b> {status_xml}", s["body_dim"]))

            desc = step.get("description", "")
            if desc:
                elements.append(Paragraph(self._safe(desc), s["body"]))

            ai_analysis = step.get("ai_analysis", "")
            if ai_analysis:
                elements.append(Paragraph("<b>Agent Thought / Reasoning:</b>", s["body"]))
                elements.append(Paragraph(self._safe(ai_analysis).replace("\n", "<br/>"), s["evidence"]))

            if tool_res and self.include_raw:
                cmd = tool_res.get("command", "")
                if cmd:
                    elements.append(Paragraph(f"<b>Command:</b> {self._safe(cmd)}", s["body_dim"]))

                stdout = str(tool_res.get("stdout", "") or "")
                stderr = str(tool_res.get("stderr", "") or "")
                
                output = ""
                if stdout:
                    output += stdout
                if stderr:
                    output += f"\\n[STDERR]\\n{stderr}" if stdout else f"[STDERR]\\n{stderr}"

                if output:
                    if len(output) > 6000:
                        output = output[:6000] + "\\n... [truncated]"
                    elements.append(Paragraph(self._safe(output).replace("\\n", "<br/>").replace("\n", "<br/>"), s["evidence"]))

            elements.append(Spacer(1, 0.4 * cm))

        return elements

    # ── Page Footer ──────────────────────────────────────────────────────

    def _page_footer(self, canvas, doc):
        """Render footer with page number on every page."""
        canvas.saveState()
        w, h = self._page_width, self._page_height

        # Footer line
        canvas.setStrokeColor(_BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(2 * cm, 1.5 * cm, w - 2 * cm, 1.5 * cm)

        # Footer text
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(_TEXT_DIM)
        canvas.drawString(2 * cm, 1.1 * cm, "HackBot AI Cybersecurity Assistant — Confidential")
        canvas.drawRightString(w - 2 * cm, 1.1 * cm, f"Page {doc.page}")

        canvas.restoreState()

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _count_severities(findings: List[Dict[str, Any]]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for f in findings:
            sev = f.get("severity", "Info")
            counts[sev] = counts.get(sev, 0) + 1
        return counts

    @staticmethod
    def _safe(text: str) -> str:
        """Escape XML special characters for reportlab Paragraph."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    @staticmethod
    def _risk_label(severity: str) -> str:
        return {
            "Critical": "Immediate remediation required",
            "High": "Remediate within 30 days",
            "Medium": "Remediate within 90 days",
            "Low": "Remediate at next opportunity",
            "Info": "Informational / best practice",
        }.get(severity, "")
