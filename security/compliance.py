#!/usr/bin/env python3
# SecScan AI core module
"""
Compliance Framework for SecScan AI
Maps findings to various compliance frameworks and generates reports
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

class ComplianceFramework(Enum):
    OWASP = "OWASP"
    NIST = "NIST"
    ISO27001 = "ISO27001"
    SOC2 = "SOC2"
    PCI_DSS = "PCI_DSS"
    HIPAA = "HIPAA"

@dataclass
class ComplianceMapping:
    framework_id: str
    control_id: str
    control_name: str
    description: str
    requirements: List[str]
    severity: str

@dataclass
class ComplianceGap:
    control_id: str
    control_name: str
    gap_description: str
    risk_level: str
    recommendations: List[str]

class ComplianceFrameworkMapper:
    """Maps security findings to compliance frameworks"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.framework_mappings = self._initialize_framework_mappings()
    
    def _initialize_framework_mappings(self) -> Dict[str, Dict[str, ComplianceMapping]]:
        """Initialize compliance framework mappings"""
        mappings = {}
        
        # OWASP Top 10 mappings
        mappings[ComplianceFramework.OWASP.value] = {
            'sql_injection': ComplianceMapping(
                'OWASP', 'A03:2021',
                'Injection',
                'Application is vulnerable to injection attacks',
                [
                    'Use parameterized queries',
                    'Validate all input',
                    'Use stored procedures',
                    'Implement input sanitization'
                ],
                'high'
            ),
            'xss': ComplianceMapping(
                'OWASP', 'A03:2021',
                'Injection',
                'Application vulnerable to Cross-Site Scripting',
                [
                    'Implement output encoding',
                    'Use Content Security Policy',
                    'Validate input data',
                    'Use secure frameworks'
                ],
                'medium'
            ),
            'broken_authentication': ComplianceMapping(
                'OWASP', 'A07:2021',
                'Identification and Authentication Failures',
                'Authentication mechanisms are compromised',
                [
                    'Implement multi-factor authentication',
                    'Use strong password policies',
                    'Secure session management',
                    'Account lockout mechanisms'
                ],
                'high'
            ),
            'sensitive_data_exposure': ComplianceMapping(
                'OWASP', 'A02:2021',
                'Cryptographic Failures',
                'Sensitive data is not properly protected',
                [
                    'Encrypt sensitive data at rest',
                    'Encrypt data in transit',
                    'Use strong encryption algorithms',
                    'Proper key management'
                ],
                'high'
            ),
            'security_misconfiguration': ComplianceMapping(
                'OWASP', 'A05:2021',
                'Security Misconfiguration',
                'Application components are insecurely configured',
                [
                    'Remove default accounts',
                    'Disable unnecessary services',
                    'Apply security patches',
                    'Use security headers'
                ],
                'medium'
            ),
            'ssrf': ComplianceMapping(
                'OWASP', 'A10:2021',
                'Server-Side Request Forgery',
                'Application fetches external resources without validating user-supplied URI input',
                [
                    'Sanitize and validate URL inputs',
                    'Restrict egress access from app servers',
                    'Use allow-lists for external domains',
                    'Disable HTTP redirects'
                ],
                'high'
            ),
            'logging_failures': ComplianceMapping(
                'OWASP', 'A09:2021',
                'Security Logging and Monitoring Failures',
                'Insufficient logging, auditing, and threat detection',
                [
                    'Enable centralized SIEM forwarding',
                    'Log authentication events and failures',
                    'Implement real-time alert correlation',
                    'Ensure tamper-proof storage of audit logs'
                ],
                'medium'
            ),
            'software_integrity_failures': ComplianceMapping(
                'OWASP', 'A08:2021',
                'Software and Data Integrity Failures',
                'Using dependencies from untrusted sources or without integrity checks',
                [
                    'Use signed artifact repositories',
                    'Verify package hashes and checksums',
                    'Scan third-party software for backdoors',
                    'Implement secure CI/CD build environments'
                ],
                'critical'
            ),
            # OWASP API Security Top 10 mappings
            'bola': ComplianceMapping(
                'OWASP_API', 'API1:2023',
                'Broken Object Level Authorization',
                'API endpoints do not validate user access permissions for target resource IDs',
                [
                    'Implement authorization checks for every object reference',
                    'Use random, unguessable UUIDs for resource keys',
                    'Avoid relying on client-supplied user parameters'
                ],
                'high'
            ),
            # OWASP LLM Applications Top 10 mappings (2025/2026)
            'prompt_injection': ComplianceMapping(
                'OWASP_LLM', 'LLM01',
                'Prompt Injection',
                'Manipulating an LLM via crafted prompt input causing unauthorized behaviors',
                [
                    'Separate user input from system instructions',
                    'Implement input filtering and sanitization',
                    'Use adversarial prompt detection models',
                    'Establish strict sandbox boundaries'
                ],
                'high'
            ),
            'insecure_output_handling': ComplianceMapping(
                'OWASP_LLM', 'LLM02',
                'Insecure Output Handling',
                'Insufficient validation of LLM outputs before displaying or executing them',
                [
                    'Sanitize LLM outputs before parsing as HTML or executing code',
                    'Use output filters to block sensitive disclosures',
                    'Implement client-side encoding'
                ],
                'high'
            ),
            'excessive_agency': ComplianceMapping(
                'OWASP_LLM', 'LLM08',
                'Excessive Agency',
                'LLM agent granted excessive permissions or capabilities without safety guardrails',
                [
                    'Restrict tool/plugin access using least-privilege principles',
                    'Enforce human-in-the-loop approvals for critical actions',
                    'Enforce API rate limits and strict schemas'
                ],
                'high'
            )
        }
        
        # NIST Cybersecurity Framework mappings
        mappings[ComplianceFramework.NIST.value] = {
            'access_control': ComplianceMapping(
                'NIST', 'PR.AC',
                'Access Control',
                'Identity and access management controls',
                [
                    'Implement least privilege principle',
                    'Use multi-factor authentication',
                    'Regular access reviews',
                    'Privileged account management'
                ],
                'high'
            ),
            'data_security': ComplianceMapping(
                'NIST', 'PR.DS',
                'Data Security',
                'Information and records data protection',
                [
                    'Data classification',
                    'Data encryption',
                    'Data loss prevention',
                    'Secure data disposal'
                ],
                'high'
            ),
            'detection_processes': ComplianceMapping(
                'NIST', 'DE.DP',
                'Detection Processes',
                'Detection processes and procedures maintained',
                [
                    'Continuous monitoring',
                    'Anomaly detection',
                    'Log analysis',
                    'Threat intelligence'
                ],
                'medium'
            ),
            'response_planning': ComplianceMapping(
                'NIST', 'RS.RP',
                'Response Planning',
                'Response processes and procedures executed',
                [
                    'Incident response plan',
                    'Response team training',
                    'Communication procedures',
                    'Recovery procedures'
                ],
                'medium'
            )
        }
        
        # ISO 27001 mappings
        mappings[ComplianceFramework.ISO27001.value] = {
            'information_security_policy': ComplianceMapping(
                'ISO27001', 'A.5.1.1',
                'Information Security Policy',
                'Information security policy must be established',
                [
                    'Document security policy',
                    'Management approval',
                    'Regular policy review',
                    'Employee communication'
                ],
                'high'
            ),
            'access_control_policy': ComplianceMapping(
                'ISO27001', 'A.9.1.1',
                'Access Control Policy',
                'Access control policy must be established',
                [
                    'Define access control policy',
                    'User access provisioning',
                    'Access rights review',
                    'User access termination'
                ],
                'high'
            ),
            'cryptography': ComplianceMapping(
                'ISO27001', 'A.10.1.1',
                'Cryptographic Controls',
                'Policy on the use of cryptographic controls',
                [
                    'Cryptographic policy',
                    'Key management',
                    'Strong encryption algorithms',
                    'Digital signatures'
                ],
                'high'
            )
        }
        
        # SOC 2 mappings
        mappings[ComplianceFramework.SOC2.value] = {
            'security_principle': ComplianceMapping(
                'SOC2', 'CC6.1',
                'Security - Logical and Physical Access',
                'Logical and physical access controls',
                [
                    'Access control procedures',
                    'Multi-factor authentication',
                    'Privileged user access',
                    'Physical access controls'
                ],
                'high'
            ),
            'availability_principle': ComplianceMapping(
                'SOC2', 'A1.1',
                'Availability',
                'System availability and performance',
                [
                    'Capacity monitoring',
                    'System performance',
                    'Backup and recovery',
                    'Incident response'
                ],
                'medium'
            )
        }
        
        return mappings
    
    def map_vulnerability_to_frameworks(self, vulnerability: Dict[str, Any], 
                                      frameworks: List[str] = None) -> Dict[str, List[ComplianceMapping]]:
        """Map a vulnerability to compliance frameworks"""
        if frameworks is None:
            frameworks = [f.value for f in ComplianceFramework]
        
        mappings = {}
        vuln_type = vulnerability.get('type', '').lower()
        vuln_category = vulnerability.get('category', '').lower()
        
        for framework in frameworks:
            if framework not in self.framework_mappings:
                continue
                
            framework_controls = []
            
            # Check for direct mappings
            for control_key, mapping in self.framework_mappings[framework].items():
                if (control_key in vuln_type or 
                    control_key in vuln_category or
                    any(keyword in vuln_type for keyword in control_key.split('_'))):
                    framework_controls.append(mapping)
            
            if framework_controls:
                mappings[framework] = framework_controls
        
        return mappings
    
    def generate_compliance_report(self, findings: List[Dict[str, Any]], 
                                 framework: str = 'OWASP') -> Dict[str, Any]:
        """Generate compliance report for specific framework"""
        if framework not in self.framework_mappings:
            raise ValueError(f"Framework {framework} not supported")
        
        # Map all findings to framework controls
        mapped_findings = {}
        unmapped_findings = []
        
        for finding in findings:
            framework_mappings = self.map_vulnerability_to_frameworks(finding, [framework])
            
            if framework in framework_mappings:
                for mapping in framework_mappings[framework]:
                    if mapping.control_id not in mapped_findings:
                        mapped_findings[mapping.control_id] = {
                            'control': mapping,
                            'findings': []
                        }
                    mapped_findings[mapping.control_id]['findings'].append(finding)
            else:
                unmapped_findings.append(finding)
        
        # Calculate compliance score
        total_controls = len(self.framework_mappings[framework])
        addressed_controls = len(mapped_findings)
        compliance_score = max(0, (total_controls - addressed_controls) / total_controls * 100)
        
        # Identify gaps
        gaps = self._identify_gaps(mapped_findings, framework)
        
        # Generate recommendations
        recommendations = self._get_framework_recommendations(mapped_findings, framework)
        
        report = {
            'framework': framework,
            'generated_at': datetime.utcnow().isoformat(),
            'compliance_score': compliance_score,
            'total_findings': len(findings),
            'mapped_findings': len(findings) - len(unmapped_findings),
            'unmapped_findings': len(unmapped_findings),
            'control_coverage': {
                'total_controls': total_controls,
                'addressed_controls': addressed_controls,
                'coverage_percentage': (addressed_controls / total_controls) * 100
            },
            'findings_by_control': mapped_findings,
            'gaps': gaps,
            'recommendations': recommendations,
            'unmapped_findings': unmapped_findings
        }
        
        return report
    
    def _identify_gaps(self, mapped_findings: Dict[str, Any], framework: str) -> List[ComplianceGap]:
        """Identify compliance gaps"""
        gaps = []
        all_controls = self.framework_mappings[framework]
        
        for control_id, control_mapping in all_controls.items():
            if control_id not in mapped_findings:
                # This control is not addressed by any findings
                gaps.append(ComplianceGap(
                    control_id=control_mapping.control_id,
                    control_name=control_mapping.control_name,
                    gap_description=f"No evidence of {control_mapping.control_name} implementation",
                    risk_level=control_mapping.severity,
                    recommendations=control_mapping.requirements
                ))
            else:
                # Check if control is adequately addressed
                findings_count = len(mapped_findings[control_id]['findings'])
                critical_findings = [
                    f for f in mapped_findings[control_id]['findings'] 
                    if f.get('severity', '').lower() in ['critical', 'high']
                ]
                
                if critical_findings:
                    gaps.append(ComplianceGap(
                        control_id=control_mapping.control_id,
                        control_name=control_mapping.control_name,
                        gap_description=f"Critical vulnerabilities found related to {control_mapping.control_name}",
                        risk_level='high',
                        recommendations=[
                            f"Address {len(critical_findings)} critical findings",
                            *control_mapping.requirements
                        ]
                    ))
        
        return gaps
    
    def _get_framework_recommendations(self, mapped_findings: Dict[str, Any], 
                                     framework: str) -> List[str]:
        """Get framework-specific recommendations"""
        recommendations = []
        
        # Priority recommendations based on severity
        high_severity_controls = []
        for control_id, data in mapped_findings.items():
            critical_findings = [
                f for f in data['findings']
                if f.get('severity', '').lower() in ['critical', 'high']
            ]
            if critical_findings:
                high_severity_controls.append((control_id, len(critical_findings)))
        
        if high_severity_controls:
            # Sort by number of critical findings
            high_severity_controls.sort(key=lambda x: x[1], reverse=True)
            top_control = high_severity_controls[0][0]
            
            control_mapping = None
            for mapping in self.framework_mappings[framework].values():
                if mapping.control_id == top_control:
                    control_mapping = mapping
                    break
            
            if control_mapping:
                recommendations.append(
                    f"PRIORITY: Address {control_mapping.control_name} - "
                    f"{high_severity_controls[0][1]} critical findings"
                )
                recommendations.extend(control_mapping.requirements[:2])  # Top 2 requirements
        
        # General framework recommendations
        framework_specific_recommendations = {
            'OWASP': [
                "Implement secure coding practices",
                "Regular security testing and code reviews",
                "Use OWASP security tools and guidelines"
            ],
            'NIST': [
                "Establish continuous monitoring program",
                "Implement risk management framework",
                "Regular security assessments and audits"
            ],
            'ISO27001': [
                "Establish information security management system",
                "Regular management reviews",
                "Employee security awareness training"
            ],
            'SOC2': [
                "Document security procedures and policies",
                "Regular third-party security assessments",
                "Implement continuous monitoring controls"
            ]
        }
        
        if framework in framework_specific_recommendations:
            recommendations.extend(framework_specific_recommendations[framework])
        
        return recommendations
    
    def export_compliance_report(self, report: Dict[str, Any], format: str = 'json') -> str:
        """Export compliance report in specified format"""
        if format.lower() == 'json':
            return json.dumps(report, indent=2, default=str)
        
        elif format.lower() == 'markdown':
            return self._format_markdown_report(report)
        
        elif format.lower() == 'html':
            return self._format_html_report(report)
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _format_markdown_report(self, report: Dict[str, Any]) -> str:
        """Format compliance report as Markdown"""
        markdown = f"""# {report['framework']} Compliance Report

Generated: {report['generated_at']}

## Executive Summary
- **Compliance Score**: {report['compliance_score']:.1f}%
- **Total Findings**: {report['total_findings']}
- **Control Coverage**: {report['control_coverage']['coverage_percentage']:.1f}%

## Findings by Control
"""
        
        for control_id, data in report['findings_by_control'].items():
            control = data['control']
            findings = data['findings']
            
            markdown += f"""
### {control.control_name} ({control.control_id})
**Severity**: {control.severity.upper()}
**Findings**: {len(findings)}

**Requirements**:
"""
            for req in control.requirements:
                markdown += f"- {req}\n"
            
            if findings:
                markdown += "\n**Related Findings**:\n"
                for finding in findings[:3]:  # Show top 3 findings
                    markdown += f"- {finding.get('title', 'Unknown')}: {finding.get('severity', 'Unknown')}\n"
        
        # Add gaps section
        if report['gaps']:
            markdown += "\n## Compliance Gaps\n"
            for gap in report['gaps']:
                markdown += f"""
### {gap.control_name}
**Risk Level**: {gap.risk_level.upper()}
**Gap**: {gap.gap_description}

**Recommendations**:
"""
                for rec in gap.recommendations[:3]:
                    markdown += f"- {rec}\n"
        
        return markdown
    
    def _format_html_report(self, report: Dict[str, Any]) -> str:
        """Format compliance report as HTML"""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{report['framework']} Compliance Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ background: #f4f4f4; padding: 20px; border-radius: 5px; }}
        .metric {{ display: inline-block; margin: 10px; padding: 15px; background: #e8f4f8; border-radius: 5px; }}
        .control {{ margin: 20px 0; padding: 15px; border-left: 4px solid #007cba; }}
        .gap {{ margin: 20px 0; padding: 15px; border-left: 4px solid #d9534f; }}
        .severity-high {{ color: #d9534f; }}
        .severity-medium {{ color: #f0ad4e; }}
        .severity-low {{ color: #5cb85c; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{report['framework']} Compliance Report</h1>
        <p>Generated: {report['generated_at']}</p>
    </div>
    
    <div class="metrics">
        <div class="metric">
            <h3>Compliance Score</h3>
            <p>{report['compliance_score']:.1f}%</p>
        </div>
        <div class="metric">
            <h3>Total Findings</h3>
            <p>{report['total_findings']}</p>
        </div>
        <div class="metric">
            <h3>Control Coverage</h3>
            <p>{report['control_coverage']['coverage_percentage']:.1f}%</p>
        </div>
    </div>
    
    <h2>Findings by Control</h2>
"""
        
        for control_id, data in report['findings_by_control'].items():
            control = data['control']
            findings = data['findings']
            
            html += f"""
    <div class="control">
        <h3>{control.control_name} ({control.control_id})</h3>
        <p><strong>Severity:</strong> <span class="severity-{control.severity}">{control.severity.upper()}</span></p>
        <p><strong>Findings:</strong> {len(findings)}</p>
        <p><strong>Description:</strong> {control.description}</p>
    </div>
"""
        
        html += """
</body>
</html>"""
        
        return html
