#!/usr/bin/env python3
# SecScan AI core module
"""
Enterprise Reporting System for SecScan AI
Dynamic report generation with analytics and trend analysis
"""

import os
import json
import logging
import base64
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import matplotlib

matplotlib.use("Agg")  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import pandas as pd
from jinja2 import Environment, FileSystemLoader, Template

from database import get_db_manager


@dataclass
class ReportTemplate:
    name: str
    template_type: str
    description: str
    template_content: str
    required_data: List[str]


class ChartGenerator:
    """Generates charts and visualizations for reports"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Set up matplotlib style
        plt.style.use("seaborn-v0_8")
        sns.set_palette("husl")

    def create_vulnerability_severity_chart(
        self, vulnerabilities: List[Dict[str, Any]]
    ) -> str:
        """Create vulnerability severity distribution chart"""
        try:
            # Count vulnerabilities by severity
            severity_counts = {}
            for vuln in vulnerabilities:
                severity = vuln.get("severity", "unknown").lower()
                severity_counts[severity] = severity_counts.get(severity, 0) + 1

            if not severity_counts:
                return ""

            # Create pie chart
            fig, ax = plt.subplots(figsize=(10, 8))

            colors = {
                "critical": "#ff0000",
                "high": "#ff6600",
                "medium": "#ffcc00",
                "low": "#00cc00",
                "info": "#0066cc",
                "unknown": "#999999",
            }

            severities = list(severity_counts.keys())
            counts = list(severity_counts.values())
            chart_colors = [colors.get(sev, "#999999") for sev in severities]

            wedges, texts, autotexts = ax.pie(
                counts,
                labels=severities,
                autopct="%1.1f%%",
                colors=chart_colors,
                startangle=90,
            )

            ax.set_title(
                "Vulnerability Distribution by Severity", fontsize=16, fontweight="bold"
            )

            # Save to base64 string
            buffer = BytesIO()
            plt.savefig(buffer, format="png", dpi=300, bbox_inches="tight")
            buffer.seek(0)

            chart_base64 = base64.b64encode(buffer.read()).decode()
            buffer.close()
            plt.close()

            return f"data:image/png;base64,{chart_base64}"

        except Exception as e:
            self.logger.error(f"Error creating vulnerability severity chart: {e}")
            return ""

    def create_timeline_chart(self, sessions: List[Dict[str, Any]]) -> str:
        """Create timeline chart of pentest sessions"""
        try:
            if not sessions:
                return ""

            # Prepare data
            dates = []
            session_names = []

            for session in sessions[-20:]:  # Last 20 sessions
                created_at = session.get("created_at", datetime.utcnow().isoformat())
                if isinstance(created_at, str):
                    date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                else:
                    date = created_at

                dates.append(date)
                session_names.append(
                    f"{session.get('target', 'Unknown')} ({date.strftime('%m/%d')})"
                )

            # Create timeline plot
            fig, ax = plt.subplots(figsize=(14, 8))

            # Plot timeline
            ax.scatter(dates, range(len(dates)), alpha=0.7, s=100)

            # Add labels
            for i, (date, name) in enumerate(zip(dates, session_names)):
                ax.annotate(
                    name,
                    (date, i),
                    xytext=(10, 0),
                    textcoords="offset points",
                    va="center",
                    fontsize=9,
                )

            ax.set_xlabel("Date", fontsize=12)
            ax.set_ylabel("Sessions", fontsize=12)
            ax.set_title("Penetration Test Timeline", fontsize=16, fontweight="bold")

            # Format x-axis
            plt.xticks(rotation=45)
            ax.grid(True, alpha=0.3)

            # Save to base64 string
            buffer = BytesIO()
            plt.savefig(buffer, format="png", dpi=300, bbox_inches="tight")
            buffer.seek(0)

            chart_base64 = base64.b64encode(buffer.read()).decode()
            buffer.close()
            plt.close()

            return f"data:image/png;base64,{chart_base64}"

        except Exception as e:
            self.logger.error(f"Error creating timeline chart: {e}")
            return ""

    def create_risk_heatmap(self, vulnerabilities: List[Dict[str, Any]]) -> str:
        """Create risk assessment heatmap"""
        try:
            if not vulnerabilities:
                return ""

            # Prepare data for heatmap
            categories = {}
            for vuln in vulnerabilities:
                category = vuln.get("category", "Other")
                severity = vuln.get("severity", "unknown").lower()

                if category not in categories:
                    categories[category] = {
                        "critical": 0,
                        "high": 0,
                        "medium": 0,
                        "low": 0,
                    }

                if severity in categories[category]:
                    categories[category][severity] += 1

            # Create DataFrame for heatmap
            df_data = []
            for category, severities in categories.items():
                df_data.append(
                    [
                        severities["critical"],
                        severities["high"],
                        severities["medium"],
                        severities["low"],
                    ]
                )

            df = pd.DataFrame(
                df_data,
                columns=["Critical", "High", "Medium", "Low"],
                index=list(categories.keys()),
            )

            # Create heatmap
            fig, ax = plt.subplots(figsize=(10, 8))

            sns.heatmap(df, annot=True, cmap="Reds", ax=ax, fmt="d")
            ax.set_title("Vulnerability Risk Heatmap", fontsize=16, fontweight="bold")
            ax.set_xlabel("Severity Level", fontsize=12)
            ax.set_ylabel("Vulnerability Category", fontsize=12)

            # Save to base64 string
            buffer = BytesIO()
            plt.savefig(buffer, format="png", dpi=300, bbox_inches="tight")
            buffer.seek(0)

            chart_base64 = base64.b64encode(buffer.read()).decode()
            buffer.close()
            plt.close()

            return f"data:image/png;base64,{chart_base64}"

        except Exception as e:
            self.logger.error(f"Error creating risk heatmap: {e}")
            return ""


class TrendAnalyzer:
    """Analyzes trends across multiple pentest sessions"""

    def __init__(self):
        self.db = get_db_manager()
        self.logger = logging.getLogger(__name__)

    def analyze_trends(
        self, sessions: List[Dict[str, Any]], timeframe: str = "monthly"
    ) -> Dict[str, Any]:
        """Analyze trends across sessions"""
        trends = {
            "vulnerability_trends": self._analyze_vulnerability_trends(
                sessions, timeframe
            ),
            "target_trends": self._analyze_target_trends(sessions, timeframe),
            "severity_trends": self._analyze_severity_trends(sessions, timeframe),
            "tool_effectiveness": self._analyze_tool_effectiveness(sessions),
            "risk_evolution": self._analyze_risk_evolution(sessions, timeframe),
        }

        return trends

    def _analyze_vulnerability_trends(
        self, sessions: List[Dict[str, Any]], timeframe: str
    ) -> Dict[str, Any]:
        """Analyze vulnerability trends over time"""
        trends = {}

        # Group sessions by time period
        time_groups = self._group_sessions_by_time(sessions, timeframe)

        for period, period_sessions in time_groups.items():
            period_stats = {
                "total_vulnerabilities": 0,
                "avg_vulnerabilities_per_session": 0,
                "vulnerability_types": {},
                "session_count": len(period_sessions),
            }

            total_vulns = 0
            for session in period_sessions:
                session_vulns = session.get("vulnerabilities", [])
                total_vulns += len(session_vulns)

                # Count by type
                for vuln in session_vulns:
                    vuln_type = vuln.get("type", "unknown")
                    period_stats["vulnerability_types"][vuln_type] = (
                        period_stats["vulnerability_types"].get(vuln_type, 0) + 1
                    )

            period_stats["total_vulnerabilities"] = total_vulns
            period_stats["avg_vulnerabilities_per_session"] = (
                total_vulns / len(period_sessions) if period_sessions else 0
            )

            trends[period] = period_stats

        return trends

    def _analyze_severity_trends(
        self, sessions: List[Dict[str, Any]], timeframe: str
    ) -> Dict[str, Any]:
        """Analyze severity trends over time"""
        trends = {}

        time_groups = self._group_sessions_by_time(sessions, timeframe)

        for period, period_sessions in time_groups.items():
            severity_counts = {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "info": 0,
            }

            for session in period_sessions:
                session_vulns = session.get("vulnerabilities", [])
                for vuln in session_vulns:
                    severity = vuln.get("severity", "unknown").lower()
                    if severity in severity_counts:
                        severity_counts[severity] += 1

            trends[period] = severity_counts

        return trends

    def _analyze_target_trends(
        self, sessions: List[Dict[str, Any]], timeframe: str
    ) -> Dict[str, Any]:
        """Analyze target trends"""
        trends = {}

        time_groups = self._group_sessions_by_time(sessions, timeframe)

        for period, period_sessions in time_groups.items():
            target_stats = {
                "unique_targets": set(),
                "target_types": {},
                "repeat_targets": [],
            }

            for session in period_sessions:
                target = session.get("target", "unknown")
                target_stats["unique_targets"].add(target)

                # Categorize target type (basic heuristic)
                if any(tld in target for tld in [".com", ".org", ".net"]):
                    target_type = "external"
                elif target.startswith("192.168.") or target.startswith("10."):
                    target_type = "internal"
                else:
                    target_type = "unknown"

                target_stats["target_types"][target_type] = (
                    target_stats["target_types"].get(target_type, 0) + 1
                )

            # Convert set to count
            target_stats["unique_targets"] = len(target_stats["unique_targets"])
            trends[period] = target_stats

        return trends

    def _analyze_tool_effectiveness(
        self, sessions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze tool effectiveness across sessions"""
        tool_stats = {}

        for session in sessions:
            phase_results = session.get("phase_results", [])

            for phase in phase_results:
                tools_used = phase.get("tools_used", [])
                vulnerabilities_found = len(
                    phase.get("results", {}).get("vulnerabilities", [])
                )

                for tool in tools_used:
                    if tool not in tool_stats:
                        tool_stats[tool] = {
                            "usage_count": 0,
                            "total_vulnerabilities": 0,
                            "avg_vulnerabilities": 0,
                        }

                    tool_stats[tool]["usage_count"] += 1
                    tool_stats[tool]["total_vulnerabilities"] += vulnerabilities_found

        # Calculate averages
        for tool, stats in tool_stats.items():
            if stats["usage_count"] > 0:
                stats["avg_vulnerabilities"] = (
                    stats["total_vulnerabilities"] / stats["usage_count"]
                )

        return tool_stats

    def _analyze_risk_evolution(
        self, sessions: List[Dict[str, Any]], timeframe: str
    ) -> Dict[str, Any]:
        """Analyze risk evolution over time"""
        risk_trends = {}

        time_groups = self._group_sessions_by_time(sessions, timeframe)

        for period, period_sessions in time_groups.items():
            risk_scores = []

            for session in period_sessions:
                # Calculate risk score for session
                session_vulns = session.get("vulnerabilities", [])
                session_risk = 0

                severity_weights = {
                    "critical": 10,
                    "high": 7,
                    "medium": 4,
                    "low": 2,
                    "info": 1,
                }

                for vuln in session_vulns:
                    severity = vuln.get("severity", "low").lower()
                    session_risk += severity_weights.get(severity, 1)

                risk_scores.append(session_risk)

            period_risk = {
                "avg_risk_score": (
                    sum(risk_scores) / len(risk_scores) if risk_scores else 0
                ),
                "max_risk_score": max(risk_scores) if risk_scores else 0,
                "min_risk_score": min(risk_scores) if risk_scores else 0,
                "session_count": len(period_sessions),
            }

            risk_trends[period] = period_risk

        return risk_trends

    def _group_sessions_by_time(
        self, sessions: List[Dict[str, Any]], timeframe: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group sessions by time period"""
        groups = {}

        for session in sessions:
            created_at = session.get("created_at", datetime.utcnow().isoformat())
            if isinstance(created_at, str):
                date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            else:
                date = created_at

            if timeframe == "weekly":
                # Week starting Monday
                week_start = date - timedelta(days=date.weekday())
                key = week_start.strftime("%Y-W%U")
            elif timeframe == "monthly":
                key = date.strftime("%Y-%m")
            elif timeframe == "quarterly":
                quarter = (date.month - 1) // 3 + 1
                key = f"{date.year}-Q{quarter}"
            else:  # daily
                key = date.strftime("%Y-%m-%d")

            if key not in groups:
                groups[key] = []
            groups[key].append(session)

        return groups


class DynamicReportGenerator:
    """Dynamic report generator with multiple formats"""

    def __init__(self):
        self.db = get_db_manager()
        self.chart_generator = ChartGenerator()
        self.trend_analyzer = TrendAnalyzer()
        self.logger = logging.getLogger(__name__)

        # Initialize Jinja2 environment
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        os.makedirs(template_dir, exist_ok=True)
        self.jinja_env = Environment(loader=FileSystemLoader(template_dir))

        # Create default templates
        self._create_default_templates()

    def _create_default_templates(self):
        """Create default report templates"""
        templates_dir = os.path.join(os.path.dirname(__file__), "templates")

        # Executive Summary Template
        executive_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Executive Summary - {{ report_data.title }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f8f9fa; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                 color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; }
        .summary-box { background: white; padding: 25px; border-radius: 8px; 
                      box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin: 20px 0; }
        .metric { display: inline-block; margin: 15px 20px 15px 0; text-align: center; 
                 background: #f1f3f4; padding: 20px; border-radius: 8px; min-width: 120px; }
        .metric h3 { margin: 0; color: #1a73e8; font-size: 2em; }
        .metric p { margin: 5px 0 0 0; color: #5f6368; font-weight: 500; }
        .risk-critical { color: #d93025; font-weight: bold; }
        .risk-high { color: #f9ab00; font-weight: bold; }
        .risk-medium { color: #ff6d00; font-weight: bold; }
        .risk-low { color: #137333; font-weight: bold; }
        .chart-container { text-align: center; margin: 30px 0; }
        .chart-container img { max-width: 100%; height: auto; border-radius: 8px; }
        .recommendation { background: #e8f5e8; border-left: 4px solid #137333; 
                         padding: 15px; margin: 10px 0; border-radius: 0 8px 8px 0; }
        .finding { background: #fff3cd; border-left: 4px solid #f9ab00; 
                  padding: 15px; margin: 10px 0; border-radius: 0 8px 8px 0; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ report_data.title }}</h1>
        <p>Generated: {{ report_data.generated_at }}</p>
        <p>Target: {{ report_data.target }}</p>
    </div>
    
    <div class="summary-box">
        <h2>Executive Summary</h2>
        <div class="metrics">
            <div class="metric">
                <h3>{{ metrics.total_vulnerabilities }}</h3>
                <p>Total Vulnerabilities</p>
            </div>
            <div class="metric">
                <h3 class="risk-critical">{{ metrics.critical_count }}</h3>
                <p>Critical Risk</p>
            </div>
            <div class="metric">
                <h3 class="risk-high">{{ metrics.high_count }}</h3>
                <p>High Risk</p>
            </div>
            <div class="metric">
                <h3>{{ metrics.overall_risk_score }}/10</h3>
                <p>Risk Score</p>
            </div>
        </div>
        
        {% if severity_chart %}
        <div class="chart-container">
            <h3>Vulnerability Distribution</h3>
            <img src="{{ severity_chart }}" alt="Vulnerability Severity Chart">
        </div>
        {% endif %}
        
        <h3>Key Findings</h3>
        {% for finding in key_findings %}
        <div class="finding">
            <strong>{{ finding.title }}</strong><br>
            {{ finding.description }}
        </div>
        {% endfor %}
        
        <h3>Priority Recommendations</h3>
        {% for recommendation in recommendations %}
        <div class="recommendation">
            {{ recommendation }}
        </div>
        {% endfor %}
    </div>
</body>
</html>
        """

        with open(os.path.join(templates_dir, "executive_summary.html"), "w") as f:
            f.write(executive_template)

    def generate_executive_report(
        self, sessions: List[Dict[str, Any]], timeframe: str = "monthly"
    ) -> Dict[str, Any]:
        """Generate executive-level report"""
        # Analyze trends across sessions
        trends = self.trend_analyzer.analyze_trends(sessions, timeframe)

        # Calculate executive metrics
        total_vulnerabilities = sum(len(s.get("vulnerabilities", [])) for s in sessions)

        all_vulnerabilities = []
        for session in sessions:
            all_vulnerabilities.extend(session.get("vulnerabilities", []))

        severity_counts = {}
        for vuln in all_vulnerabilities:
            severity = vuln.get("severity", "unknown").lower()
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        # Calculate overall risk score
        severity_weights = {"critical": 10, "high": 7, "medium": 4, "low": 2, "info": 1}
        total_risk = sum(
            severity_weights.get(sev, 1) * count
            for sev, count in severity_counts.items()
        )
        max_possible_risk = total_vulnerabilities * 10
        overall_risk_score = (
            min((total_risk / max_possible_risk * 10), 10)
            if max_possible_risk > 0
            else 0
        )

        # Generate insights
        insights = self._generate_executive_insights(trends, sessions)

        # Create visualizations
        charts = {}
        if all_vulnerabilities:
            charts["severity_distribution"] = (
                self.chart_generator.create_vulnerability_severity_chart(
                    all_vulnerabilities
                )
            )
            charts["risk_heatmap"] = self.chart_generator.create_risk_heatmap(
                all_vulnerabilities
            )

        if sessions:
            charts["timeline"] = self.chart_generator.create_timeline_chart(sessions)

        executive_report = {
            "title": "Executive Security Assessment Report",
            "generated_at": datetime.utcnow().strftime("%B %d, %Y"),
            "timeframe": timeframe,
            "session_count": len(sessions),
            "metrics": {
                "total_vulnerabilities": total_vulnerabilities,
                "critical_count": severity_counts.get("critical", 0),
                "high_count": severity_counts.get("high", 0),
                "medium_count": severity_counts.get("medium", 0),
                "low_count": severity_counts.get("low", 0),
                "overall_risk_score": round(overall_risk_score, 1),
                "unique_targets": len(
                    set(s.get("target", "unknown") for s in sessions)
                ),
            },
            "trends": trends,
            "insights": insights,
            "charts": charts,
            "key_findings": self._extract_key_findings(all_vulnerabilities),
            "recommendations": self._generate_strategic_recommendations(
                insights, trends
            ),
        }

        return executive_report

    def _generate_executive_insights(
        self, trends: Dict[str, Any], sessions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate executive-level insights"""
        insights = []

        # Vulnerability trend insight
        vuln_trends = trends.get("vulnerability_trends", {})
        if len(vuln_trends) >= 2:
            periods = sorted(vuln_trends.keys())
            latest = vuln_trends[periods[-1]]
            previous = vuln_trends[periods[-2]] if len(periods) > 1 else {}

            latest_avg = latest.get("avg_vulnerabilities_per_session", 0)
            previous_avg = previous.get("avg_vulnerabilities_per_session", 0)

            if previous_avg > 0:
                change_percent = ((latest_avg - previous_avg) / previous_avg) * 100
                trend_direction = (
                    "increased"
                    if change_percent > 5
                    else "decreased" if change_percent < -5 else "remained stable"
                )

                insights.append(
                    {
                        "type": "vulnerability_trend",
                        "title": "Vulnerability Trend Analysis",
                        "description": f"Average vulnerabilities per assessment {trend_direction} by {abs(change_percent):.1f}% compared to previous period.",
                        "impact": (
                            "high"
                            if abs(change_percent) > 20
                            else "medium" if abs(change_percent) > 5 else "low"
                        ),
                    }
                )

        # Risk evolution insight
        risk_trends = trends.get("risk_evolution", {})
        if len(risk_trends) >= 2:
            periods = sorted(risk_trends.keys())
            latest_risk = risk_trends[periods[-1]].get("avg_risk_score", 0)
            previous_risk = (
                risk_trends[periods[-2]].get("avg_risk_score", 0)
                if len(periods) > 1
                else 0
            )

            if previous_risk > 0:
                risk_change = ((latest_risk - previous_risk) / previous_risk) * 100

                insights.append(
                    {
                        "type": "risk_evolution",
                        "title": "Risk Evolution",
                        "description": f'Overall risk score has {"increased" if risk_change > 0 else "decreased"} by {abs(risk_change):.1f}%.',
                        "impact": "high" if abs(risk_change) > 25 else "medium",
                    }
                )

        # Tool effectiveness insight
        tool_effectiveness = trends.get("tool_effectiveness", {})
        if tool_effectiveness:
            most_effective = max(
                tool_effectiveness.items(),
                key=lambda x: x[1].get("avg_vulnerabilities", 0),
            )

            insights.append(
                {
                    "type": "tool_effectiveness",
                    "title": "Tool Performance",
                    "description": f'{most_effective[0]} is the most effective tool, finding an average of {most_effective[1]["avg_vulnerabilities"]:.1f} vulnerabilities per use.',
                    "impact": "medium",
                }
            )

        return insights

    def _extract_key_findings(
        self, vulnerabilities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract key findings from vulnerabilities"""
        key_findings = []

        # Critical vulnerabilities
        critical_vulns = [
            v for v in vulnerabilities if v.get("severity", "").lower() == "critical"
        ]
        if critical_vulns:
            key_findings.append(
                {
                    "title": f"{len(critical_vulns)} Critical Vulnerabilities Identified",
                    "description": "Immediate action required to address critical security vulnerabilities that pose significant risk to the organization.",
                    "severity": "critical",
                }
            )

        # Common vulnerability types
        vuln_types = {}
        for vuln in vulnerabilities:
            vuln_type = vuln.get("type", "unknown")
            vuln_types[vuln_type] = vuln_types.get(vuln_type, 0) + 1

        if vuln_types:
            most_common = max(vuln_types.items(), key=lambda x: x[1])
            key_findings.append(
                {
                    "title": f"{most_common[0]} Vulnerabilities Most Common",
                    "description": f"{most_common[1]} instances of {most_common[0]} vulnerabilities found across assessments.",
                    "severity": "high",
                }
            )

        return key_findings

    def _generate_strategic_recommendations(
        self, insights: List[Dict[str, Any]], trends: Dict[str, Any]
    ) -> List[str]:
        """Generate strategic recommendations for executives"""
        recommendations = []

        # Based on insights
        for insight in insights:
            if insight["type"] == "vulnerability_trend" and insight["impact"] == "high":
                if "increased" in insight["description"]:
                    recommendations.append(
                        "Increase security assessment frequency and implement more proactive security controls"
                    )
                else:
                    recommendations.append(
                        "Continue current security practices while monitoring for emerging threats"
                    )

            elif insight["type"] == "risk_evolution" and insight["impact"] == "high":
                recommendations.append(
                    "Implement immediate risk mitigation strategies and increase security budget allocation"
                )

        # General strategic recommendations
        recommendations.extend(
            [
                "Establish regular executive security briefings to maintain visibility into security posture",
                "Consider implementing automated continuous security monitoring",
                "Invest in security awareness training for all employees",
                "Evaluate cyber insurance coverage based on current risk profile",
            ]
        )

        return recommendations[:6]  # Limit to top 6 recommendations

    def generate_technical_report(self, session_data: Dict[str, Any]) -> str:
        """Generate detailed technical report"""
        template = (
            self.jinja_env.get_template("technical_report.html")
            if self.jinja_env.get_template
            else None
        )

        if not template:
            # Return basic text report if template not available
            return self._generate_text_technical_report(session_data)

        return template.render(session_data=session_data)

    def _generate_text_technical_report(self, session_data: Dict[str, Any]) -> str:
        """Generate basic text technical report"""
        report_lines = [
            f"TECHNICAL PENETRATION TEST REPORT",
            f"=" * 50,
            f"Target: {session_data.get('target', 'Unknown')}",
            f"Date: {session_data.get('created_at', 'Unknown')}",
            f"Scope: {session_data.get('scope', 'Unknown')}",
            "",
            "EXECUTIVE SUMMARY",
            "-" * 20,
        ]

        vulnerabilities = session_data.get("vulnerabilities", [])
        if vulnerabilities:
            severity_counts = {}
            for vuln in vulnerabilities:
                severity = vuln.get("severity", "unknown")
                severity_counts[severity] = severity_counts.get(severity, 0) + 1

            report_lines.append(f"Total Vulnerabilities Found: {len(vulnerabilities)}")
            for severity, count in severity_counts.items():
                report_lines.append(f"  - {severity.title()}: {count}")

        report_lines.extend(
            [
                "",
                "DETAILED FINDINGS",
                "-" * 20,
            ]
        )

        for i, vuln in enumerate(vulnerabilities[:10], 1):  # Top 10 vulnerabilities
            report_lines.extend(
                [
                    f"{i}. {vuln.get('title', 'Unknown Vulnerability')}",
                    f"   Severity: {vuln.get('severity', 'Unknown')}",
                    f"   Description: {vuln.get('description', 'No description available')[:200]}",
                    f"   Recommendation: {vuln.get('remediation', 'No recommendation available')[:200]}",
                    "",
                ]
            )

        return "\n".join(report_lines)

    def export_report(
        self, report_data: Dict[str, Any], format_type: str = "html"
    ) -> str:
        """Export report in specified format"""
        if format_type.lower() == "html":
            return self._export_html_report(report_data)
        elif format_type.lower() == "pdf":
            return self._export_pdf_report(report_data)
        elif format_type.lower() == "json":
            return json.dumps(report_data, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported format: {format_type}")

    def _export_html_report(self, report_data: Dict[str, Any]) -> str:
        """Export report as HTML"""
        try:
            template = self.jinja_env.get_template("executive_summary.html")
            return template.render(
                report_data=report_data,
                metrics=report_data.get("metrics", {}),
                severity_chart=report_data.get("charts", {}).get(
                    "severity_distribution", ""
                ),
                key_findings=report_data.get("key_findings", []),
                recommendations=report_data.get("recommendations", []),
            )
        except Exception as e:
            self.logger.error(f"Error exporting HTML report: {e}")
            return (
                f"<html><body><h1>Error generating report: {str(e)}</h1></body></html>"
            )

    def _export_pdf_report(self, report_data: Dict[str, Any]) -> str:
        """Export report as PDF (returns file path)"""
        try:
            # This would use a library like WeasyPrint or ReportLab to generate PDF
            # For now, return a placeholder
            html_content = self._export_html_report(report_data)

            # In a real implementation, you would convert HTML to PDF here
            pdf_path = f"/tmp/report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"

            # Placeholder: save HTML instead of PDF for now
            with open(pdf_path.replace(".pdf", ".html"), "w") as f:
                f.write(html_content)

            return pdf_path.replace(".pdf", ".html")

        except Exception as e:
            self.logger.error(f"Error exporting PDF report: {e}")
            raise
