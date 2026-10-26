#!/usr/bin/env python3
# SecScan AI core module
"""
Enterprise Cloud Security Posture Management (CSPM) & Kubernetes Security Posture (KSPM) Engine.
Audits multi-cloud infrastructure (AWS, Azure, GCP, and Kubernetes) and Infrastructure-as-Code (Terraform / K8s YAML)
against CIS Benchmarks (CIS AWS Foundations, CIS Kubernetes Benchmark), NIST SP 800-53,
and MITRE ATT&CK Cloud Matrix. Detects cloud storage leaks, IAM overprivilege, exposed management ports,
unencrypted resources, pod privilege escalation, and generates automated remediation patches.
"""

from __future__ import annotations

import re
import json
import logging
from enum import Enum
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field, asdict

import yaml

logger = logging.getLogger(__name__)


class CloudProvider(str, Enum):
    """Supported cloud and container platforms."""
    AWS = "AWS"
    AZURE = "Azure"
    GCP = "GCP"
    KUBERNETES = "Kubernetes"
    MULTI_CLOUD = "Multi-Cloud"


class CSPMSeverity(str, Enum):
    """Standardized finding severity ratings."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class CSPMResourceCategory(str, Enum):
    """Categorization of cloud and container resources."""
    STORAGE = "Storage & Object Stores"
    IAM = "Identity & Access Management"
    NETWORK = "Networking & Security Groups"
    COMPUTE = "Compute & Virtual Machines"
    KUBERNETES_PSS = "Kubernetes Pod Security Standards"
    KUBERNETES_RBAC = "Kubernetes RBAC & Authorization"
    LOGGING_MONITORING = "Audit Logging & Threat Detection"
    DATA_PROTECTION = "Encryption & Key Management"


@dataclass
class CSPMFinding:
    """An individual cloud misconfiguration or compliance finding."""
    finding_id: str
    title: str
    provider: CloudProvider
    category: CSPMResourceCategory
    service: str  # e.g., "S3", "IAM", "SecurityGroups", "PodSecurity", "KeyVault"
    severity: CSPMSeverity
    resource_id: str
    resource_type: str  # e.g., "aws_s3_bucket", "Deployment", "azurerm_key_vault"
    cis_benchmark: str  # e.g., "CIS AWS 2.1.5", "CIS K8s 5.2.2"
    mitre_attack_id: str  # e.g., "T1530: Data from Cloud Storage Object"
    mitre_tactic: str  # e.g., "Exfiltration", "Privilege Escalation", "Initial Access"
    description: str
    evidence: str
    cvss_score: float
    remediation_cli: str
    remediation_terraform: str

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res["provider"] = self.provider.value
        res["category"] = self.category.value
        res["severity"] = self.severity.value
        return res


@dataclass
class CSPMReport:
    """Aggregated assessment report for cloud & Kubernetes security posture."""
    environment_name: str
    timestamp: str
    total_resources_scanned: int
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    info_count: int
    compliance_score: float  # 0.0 to 100.0%
    cis_pass_rate: float     # 0.0 to 100.0%
    findings: List[CSPMFinding]
    provider_breakdown: Dict[str, int]
    category_breakdown: Dict[str, int]
    mitre_tactics_breakdown: Dict[str, int]
    hardening_roadmap: List[str]

    @property
    def provider_summary(self) -> Dict[str, int]:
        return self.provider_breakdown

    @property
    def category_summary(self) -> Dict[str, int]:
        return self.category_breakdown

    def to_dict(self) -> Dict[str, Any]:
        return {
            "environment_name": self.environment_name,
            "timestamp": self.timestamp,
            "total_resources_scanned": self.total_resources_scanned,
            "total_findings": self.total_findings,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "info_count": self.info_count,
            "compliance_score": round(self.compliance_score, 1),
            "cis_pass_rate": round(self.cis_pass_rate, 1),
            "findings": [f.to_dict() for f in self.findings],
            "provider_breakdown": self.provider_breakdown,
            "category_breakdown": self.category_breakdown,
            "mitre_tactics_breakdown": self.mitre_tactics_breakdown,
            "hardening_roadmap": self.hardening_roadmap,
        }

    def export_remediation_script(self, script_format: str = "bash") -> str:
        """Generate ready-to-execute remediation script or Terraform patch."""
        if script_format.lower() == "terraform":
            blocks = ["# SecScan AI Enterprise CSPM - Automated Terraform HCL Remediation Patch\n"]
            for f in self.findings:
                if f.remediation_terraform:
                    blocks.append(f"# Remediation for {f.finding_id}: {f.title} ({f.resource_id})")
                    blocks.append(f.remediation_terraform)
                    blocks.append("")
            return "\n".join(blocks)

        # Default bash
        lines = [
            "#!/bin/bash",
            "# SecScan AI Enterprise CSPM - Automated Cloud Remediation Script",
            f"# Environment: {self.environment_name}",
            f"# Total Critical/High Issues: {self.critical_count + self.high_count}",
            "set -euo pipefail",
            "",
            "echo '>>> Applying SecScan AI Cloud Posture Remediations...'",
            "",
        ]
        for f in self.findings:
            if f.remediation_cli:
                lines.append(f"# [{f.severity.value.upper()}] {f.finding_id}: {f.title}")
                lines.append(f"# Target: {f.resource_id}")
                lines.append(f.remediation_cli)
                lines.append("")
        lines.append("echo '>>> Cloud remediation commands completed successfully.'")
        return "\n".join(lines)


class CSPMScanner:
    """
    Enterprise Cloud Security Posture Management & Kubernetes Auditor.
    Inspects cloud architectures, IaC definitions (Terraform / K8s manifests),
    and runtime cloud configurations for security misconfigurations.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    # =========================================================================
    # Kubernetes Manifest Auditing (Pod Security Standards & RBAC)
    # =========================================================================

    def scan_kubernetes_manifest(self, content_or_dict: Union[str, Dict[str, Any], List[Dict[str, Any]]], filename: str = "k8s-manifest.yaml") -> List[CSPMFinding]:
        """Scan Kubernetes manifests for Pod Security Standards (PSS), RBAC, and network risks."""
        documents: List[Dict[str, Any]] = []
        if isinstance(content_or_dict, str):
            try:
                for doc in yaml.safe_load_all(content_or_dict):
                    if isinstance(doc, dict):
                        documents.append(doc)
            except Exception as e:
                self.logger.warning(f"Failed to parse Kubernetes YAML: {e}")
                return []
        elif isinstance(content_or_dict, list):
            documents = [d for d in content_or_dict if isinstance(d, dict)]
        elif isinstance(content_or_dict, dict):
            documents = [content_or_dict]

        findings: List[CSPMFinding] = []
        for doc in documents:
            kind = doc.get("kind", "")
            metadata = doc.get("metadata", {})
            res_name = metadata.get("name", "unnamed-resource")
            namespace = metadata.get("namespace", "default")
            full_res_id = f"{kind.lower()}/{namespace}/{res_name}"

            # Workloads with Pod templates
            pod_spec = None
            if kind == "Pod":
                pod_spec = doc.get("spec", {})
            elif kind in ("Deployment", "DaemonSet", "StatefulSet", "Job"):
                pod_spec = doc.get("spec", {}).get("template", {}).get("spec", {})
            elif kind == "CronJob":
                pod_spec = doc.get("spec", {}).get("jobTemplate", {}).get("spec", {}).get("template", {}).get("spec", {})

            if pod_spec:
                findings.extend(self._audit_pod_spec(pod_spec, full_res_id, kind))

            # RBAC checks
            if kind in ("ClusterRoleBinding", "RoleBinding"):
                findings.extend(self._audit_rbac_binding(doc, full_res_id))

            # Service checks
            if kind == "Service":
                findings.extend(self._audit_service(doc, full_res_id))

        return findings

    def _audit_pod_spec(self, pod_spec: Dict[str, Any], res_id: str, kind: str) -> List[CSPMFinding]:
        findings: List[CSPMFinding] = []
        containers = pod_spec.get("containers", []) + pod_spec.get("initContainers", [])
        pod_sec_ctx = pod_spec.get("securityContext", {})

        # PSS 1: Host Network or Host PID
        if pod_spec.get("hostNetwork") is True:
            findings.append(CSPMFinding(
                finding_id="CSPM-K8S-PSS-001",
                title="Pod Configured with hostNetwork Access",
                provider=CloudProvider.KUBERNETES,
                category=CSPMResourceCategory.KUBERNETES_PSS,
                service="PodSecurity",
                severity=CSPMSeverity.HIGH,
                resource_id=res_id,
                resource_type=kind,
                cis_benchmark="CIS Kubernetes 5.2.4",
                mitre_attack_id="T1611: Escape to Host",
                mitre_tactic="Privilege Escalation",
                description="The pod shares the host network namespace, allowing it to sniff host traffic, bypass network policies, and access localhost daemons.",
                evidence=f"{res_id}: hostNetwork: true",
                cvss_score=7.8,
                remediation_cli=f"kubectl patch {res_id} --type=merge -p '{{\"spec\":{{\"hostNetwork\":false}}}}'",
                remediation_terraform="""spec {
  host_network = false
}""",
            ))

        if pod_spec.get("hostPID") is True:
            findings.append(CSPMFinding(
                finding_id="CSPM-K8S-PSS-002",
                title="Pod Configured with hostPID Access",
                provider=CloudProvider.KUBERNETES,
                category=CSPMResourceCategory.KUBERNETES_PSS,
                service="PodSecurity",
                severity=CSPMSeverity.HIGH,
                resource_id=res_id,
                resource_type=kind,
                cis_benchmark="CIS Kubernetes 5.2.3",
                mitre_attack_id="T1611: Escape to Host",
                mitre_tactic="Privilege Escalation",
                description="The pod shares the host process namespace, permitting containerized processes to view and inspect all host processes and send signals.",
                evidence=f"{res_id}: hostPID: true",
                cvss_score=8.1,
                remediation_cli=f"kubectl patch {res_id} --type=merge -p '{{\"spec\":{{\"hostPID\":false}}}}'",
                remediation_terraform="""spec {
  host_pid = false
}""",
            ))

        # PSS 2: Sensitive hostPath Volumes
        for vol in pod_spec.get("volumes", []):
            host_path = vol.get("hostPath", {}).get("path", "")
            sensitive_paths = ["/", "/var/run/docker.sock", "/run/containerd/containerd.sock", "/etc", "/root", "/var/log"]
            if any(host_path == sp or host_path.startswith(sp + "/") for sp in sensitive_paths):
                findings.append(CSPMFinding(
                    finding_id="CSPM-K8S-PSS-003",
                    title="Sensitive Host Path Volume Mounted into Pod",
                    provider=CloudProvider.KUBERNETES,
                    category=CSPMResourceCategory.KUBERNETES_PSS,
                    service="PodSecurity",
                    severity=CSPMSeverity.CRITICAL,
                    resource_id=f"{res_id}/volume/{vol.get('name')}",
                    resource_type=kind,
                    cis_benchmark="CIS Kubernetes 5.2.7",
                    mitre_attack_id="T1611: Escape to Host",
                    mitre_tactic="Privilege Escalation",
                    description=f"Volume '{vol.get('name')}' mounts sensitive host path '{host_path}', which enables trivial container breakout to the host node.",
                    evidence=f"hostPath.path: {host_path}",
                    cvss_score=9.6,
                    remediation_cli=f"# Remove hostPath volume '{vol.get('name')}' from {res_id} manifest",
                    remediation_terraform="# Replace hostPath with persistentVolumeClaim or emptyDir",
                ))

        # Container-level checks
        for c in containers:
            c_name = c.get("name", "container")
            sec_ctx = c.get("securityContext", {})

            # Privileged mode
            if sec_ctx.get("privileged") is True:
                findings.append(CSPMFinding(
                    finding_id="CSPM-K8S-PSS-004",
                    title=f"Container '{c_name}' Running in Privileged Mode",
                    provider=CloudProvider.KUBERNETES,
                    category=CSPMResourceCategory.KUBERNETES_PSS,
                    service="PodSecurity",
                    severity=CSPMSeverity.CRITICAL,
                    resource_id=f"{res_id}/container/{c_name}",
                    resource_type=kind,
                    cis_benchmark="CIS Kubernetes 5.2.1",
                    mitre_attack_id="T1611: Escape to Host",
                    mitre_tactic="Privilege Escalation",
                    description=f"Container '{c_name}' has securityContext.privileged=true, granting kernel root capabilities and access to all host devices.",
                    evidence=f"{c_name}: securityContext.privileged: true",
                    cvss_score=9.8,
                    remediation_cli=f"# In manifest for {res_id}, set securityContext.privileged: false for container {c_name}",
                    remediation_terraform="""security_context {
  privileged = false
  allow_privilege_escalation = false
}""",
                ))

            # Run as Root
            run_as_non_root = sec_ctx.get("runAsNonRoot", pod_sec_ctx.get("runAsNonRoot"))
            run_as_user = sec_ctx.get("runAsUser", pod_sec_ctx.get("runAsUser"))
            if run_as_non_root is not True or run_as_user == 0:
                findings.append(CSPMFinding(
                    finding_id="CSPM-K8S-PSS-005",
                    title=f"Container '{c_name}' Allowed to Run as Root User",
                    provider=CloudProvider.KUBERNETES,
                    category=CSPMResourceCategory.KUBERNETES_PSS,
                    service="PodSecurity",
                    severity=CSPMSeverity.MEDIUM,
                    resource_id=f"{res_id}/container/{c_name}",
                    resource_type=kind,
                    cis_benchmark="CIS Kubernetes 5.2.6",
                    mitre_attack_id="T1068: Exploitation for Privilege Escalation",
                    mitre_tactic="Privilege Escalation",
                    description=f"Container '{c_name}' does not enforce runAsNonRoot=true and may execute processes as UID 0 (root).",
                    evidence=f"runAsNonRoot: {run_as_non_root}, runAsUser: {run_as_user}",
                    cvss_score=6.3,
                    remediation_cli=f"# Set securityContext.runAsNonRoot: true and runAsUser: 10001 for container {c_name}",
                    remediation_terraform="""security_context {
  run_as_non_root = true
  run_as_user     = 10001
}""",
                ))

            # Read-only Root Filesystem
            if sec_ctx.get("readOnlyRootFilesystem") is not True:
                findings.append(CSPMFinding(
                    finding_id="CSPM-K8S-PSS-006",
                    title=f"Container '{c_name}' Root Filesystem is Writable",
                    provider=CloudProvider.KUBERNETES,
                    category=CSPMResourceCategory.KUBERNETES_PSS,
                    service="PodSecurity",
                    severity=CSPMSeverity.LOW,
                    resource_id=f"{res_id}/container/{c_name}",
                    resource_type=kind,
                    cis_benchmark="CIS Kubernetes 5.2.12",
                    mitre_attack_id="T1562.001: Disable or Modify Tools",
                    mitre_tactic="Defense Evasion",
                    description=f"Container '{c_name}' allows writing to root filesystem, permitting adversaries to drop persistence binaries or malware.",
                    evidence=f"readOnlyRootFilesystem: {sec_ctx.get('readOnlyRootFilesystem')}",
                    cvss_score=4.2,
                    remediation_cli=f"# Set securityContext.readOnlyRootFilesystem: true for container {c_name}",
                    remediation_terraform="""security_context {
  read_only_root_filesystem = true
}""",
                ))

            # Plaintext Environment Secret Injection
            for env_var in c.get("env", []):
                var_name = env_var.get("name", "").upper()
                var_val = env_var.get("value")
                if var_val and any(k in var_name for k in ("PASSWORD", "SECRET", "TOKEN", "API_KEY", "PRIVATE_KEY")):
                    findings.append(CSPMFinding(
                        finding_id="CSPM-K8S-SEC-001",
                        title=f"Hardcoded Secret in Environment Variable '{var_name}'",
                        provider=CloudProvider.KUBERNETES,
                        category=CSPMResourceCategory.DATA_PROTECTION,
                        service="SecretsManagement",
                        severity=CSPMSeverity.HIGH,
                        resource_id=f"{res_id}/container/{c_name}/env/{var_name}",
                        resource_type=kind,
                        cis_benchmark="CIS Kubernetes 5.4.1",
                        mitre_attack_id="T1552.001: Credentials in Files or Env",
                        mitre_tactic="Credential Access",
                        description=f"Container '{c_name}' defines secret in plaintext env var '{var_name}' instead of referencing a Kubernetes Secret.",
                        evidence=f"env: {var_name}=***",
                        cvss_score=7.9,
                        remediation_cli=f"# Migrate env var {var_name} to secretKeyRef in {res_id}",
                        remediation_terraform=f"""env {{
  name = "{var_name}"
  value_from {{
    secret_key_ref {{
      name = "app-secrets"
      key  = "{var_name.lower()}"
    }}
  }}
}}""",
                    ))

        return findings

    def _audit_rbac_binding(self, doc: Dict[str, Any], res_id: str) -> List[CSPMFinding]:
        findings: List[CSPMFinding] = []
        role_ref = doc.get("roleRef", {}).get("name", "")
        subjects = doc.get("subjects", [])

        is_admin_role = role_ref in ("cluster-admin", "admin")
        for subj in subjects:
            subj_name = subj.get("name", "")
            subj_kind = subj.get("kind", "")
            if is_admin_role and (subj_name in ("system:anonymous", "system:unauthenticated") or subj_name == "default"):
                findings.append(CSPMFinding(
                    finding_id="CSPM-K8S-RBAC-001",
                    title=f"Excessive Cluster Admin Privileges Bound to '{subj_name}'",
                    provider=CloudProvider.KUBERNETES,
                    category=CSPMResourceCategory.KUBERNETES_RBAC,
                    service="RBAC",
                    severity=CSPMSeverity.CRITICAL,
                    resource_id=res_id,
                    resource_type=doc.get("kind", "RoleBinding"),
                    cis_benchmark="CIS Kubernetes 5.1.1",
                    mitre_attack_id="T1078.004: Cloud Accounts",
                    mitre_tactic="Privilege Escalation",
                    description=f"{res_id} binds administrative role '{role_ref}' to '{subj_kind}:{subj_name}', allowing unauthorized cluster takeover.",
                    evidence=f"roleRef: {role_ref}, subject: {subj_name}",
                    cvss_score=9.9,
                    remediation_cli=f"kubectl delete {res_id}",
                    remediation_terraform="# Remove or restrict ClusterRoleBinding to dedicated service account",
                ))

        return findings

    def _audit_service(self, doc: Dict[str, Any], res_id: str) -> List[CSPMFinding]:
        findings: List[CSPMFinding] = []
        spec = doc.get("spec", {})
        svc_type = spec.get("type", "ClusterIP")
        if svc_type == "NodePort":
            findings.append(CSPMFinding(
                finding_id="CSPM-K8S-NET-001",
                title=f"Kubernetes Service '{res_id}' Configured as NodePort",
                provider=CloudProvider.KUBERNETES,
                category=CSPMResourceCategory.NETWORK,
                service="Service",
                severity=CSPMSeverity.MEDIUM,
                resource_id=res_id,
                resource_type="Service",
                cis_benchmark="CIS Kubernetes 5.7.1",
                mitre_attack_id="T1190: Exploit Public-Facing Application",
                mitre_tactic="Initial Access",
                description=f"Service '{res_id}' exposes node ports directly across all worker nodes, potentially bypassing perimeter ingress controls.",
                evidence=f"spec.type: {svc_type}",
                cvss_score=5.5,
                remediation_cli=f"kubectl patch service {res_id} -p '{{\"spec\":{{\"type\":\"ClusterIP\"}}}}'",
                remediation_terraform="""spec {
  type = "ClusterIP"
}""",
            ))
        return findings

    # =========================================================================
    # Terraform / IaC Static Auditing
    # =========================================================================

    def scan_terraform(self, content_str: str, filename: str = "main.tf") -> List[CSPMFinding]:
        """Statically inspect Terraform HCL definitions for AWS, Azure, GCP, and K8s misconfigurations."""
        findings: List[CSPMFinding] = []

        # AWS S3: Missing Block Public Access or Public ACL
        if "aws_s3_bucket" in content_str:
            # Check for acl = "public-read"
            if re.search(r'resource\s+"aws_s3_bucket"\s+"([^"]+)"', content_str):
                for match in re.finditer(r'resource\s+"aws_s3_bucket"\s+"([^"]+)"\s*{(.*?)(?=\nresource|\Z)', content_str, re.DOTALL):
                    bucket_alias = match.group(1)
                    block = match.group(2)
                    res_id = f"aws_s3_bucket.{bucket_alias}"

                    if re.search(r'acl\s*=\s*"(public-read|public-read-write)"', block):
                        findings.append(CSPMFinding(
                            finding_id="CSPM-AWS-S3-001",
                            title=f"S3 Bucket '{bucket_alias}' Has Public Read/Write ACL",
                            provider=CloudProvider.AWS,
                            category=CSPMResourceCategory.STORAGE,
                            service="S3",
                            severity=CSPMSeverity.CRITICAL,
                            resource_id=res_id,
                            resource_type="aws_s3_bucket",
                            cis_benchmark="CIS AWS 2.1.5",
                            mitre_attack_id="T1530: Data from Cloud Storage Object",
                            mitre_tactic="Exfiltration",
                            description=f"Bucket '{bucket_alias}' is declared with a public ACL, allowing unauthenticated Internet users to access data.",
                            evidence=f"acl = \"{re.search(r'acl\s*=\s*\"([^\"]+)\"', block).group(1)}\"",
                            cvss_score=9.4,
                            remediation_cli=f"aws s3api put-bucket-acl --bucket {bucket_alias} --acl private",
                            remediation_terraform=f"""resource "aws_s3_bucket_public_access_block" "{bucket_alias}_block" {{
  bucket                  = aws_s3_bucket.{bucket_alias}.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}}""",
                        ))

                    # Check for server-side encryption
                    if "server_side_encryption_configuration" not in block and "aws_s3_bucket_server_side_encryption_configuration" not in content_str:
                        findings.append(CSPMFinding(
                            finding_id="CSPM-AWS-S3-002",
                            title=f"S3 Bucket '{bucket_alias}' Missing Server-Side Encryption",
                            provider=CloudProvider.AWS,
                            category=CSPMResourceCategory.DATA_PROTECTION,
                            service="S3",
                            severity=CSPMSeverity.HIGH,
                            resource_id=res_id,
                            resource_type="aws_s3_bucket",
                            cis_benchmark="CIS AWS 2.1.1",
                            mitre_attack_id="T1565.001: Stored Data Manipulation",
                            mitre_tactic="Impact",
                            description=f"Bucket '{bucket_alias}' does not declare default server-side encryption with KMS or AES256.",
                            evidence="server_side_encryption_configuration not declared",
                            cvss_score=7.1,
                            remediation_cli=f"aws s3api put-bucket-encryption --bucket {bucket_alias} --server-side-encryption-configuration '{{\"Rules\": [{{\"ApplyServerSideEncryptionByDefault\": {{\"SSEAlgorithm\": \"AES256\"}}}}]}}'",
                            remediation_terraform=f"""resource "aws_s3_bucket_server_side_encryption_configuration" "{bucket_alias}_enc" {{
  bucket = aws_s3_bucket.{bucket_alias}.id
  rule {{
    apply_server_side_encryption_by_default {{
      sse_algorithm = "AES256"
    }}
  }}
}}""",
                        ))

        # AWS Security Groups: Unrestricted Ingress (0.0.0.0/0 on sensitive ports)
        if "aws_security_group" in content_str:
            for match in re.finditer(r'resource\s+"aws_security_group"\s+"([^"]+)"\s*{(.*?)(?=\nresource|\Z)', content_str, re.DOTALL):
                sg_name = match.group(1)
                sg_block = match.group(2)
                res_id = f"aws_security_group.{sg_name}"

                # Check for 0.0.0.0/0 ingress
                if "0.0.0.0/0" in sg_block and "ingress" in sg_block:
                    port_matches = re.findall(r'(?:from_port|to_port)\s*=\s*(\d+)', sg_block)
                    ports = [int(p) for p in port_matches]
                    dangerous_ports = {
                        22: ("SSH Management Port Exposed to Internet", CSPMSeverity.CRITICAL, 9.1),
                        3389: ("RDP Remote Desktop Exposed to Internet", CSPMSeverity.CRITICAL, 9.1),
                        3306: ("MySQL Database Exposed to Internet", CSPMSeverity.HIGH, 8.4),
                        5432: ("PostgreSQL Database Exposed to Internet", CSPMSeverity.HIGH, 8.4),
                        27017: ("MongoDB Database Exposed to Internet", CSPMSeverity.HIGH, 8.4),
                    }
                    for port, (title, sev, cvss) in dangerous_ports.items():
                        if port in ports or (any(p <= port for p in ports) and any(p >= port for p in ports)):
                            findings.append(CSPMFinding(
                                finding_id=f"CSPM-AWS-SG-{port}",
                                title=f"Security Group '{sg_name}': {title}",
                                provider=CloudProvider.AWS,
                                category=CSPMResourceCategory.NETWORK,
                                service="SecurityGroups",
                                severity=sev,
                                resource_id=res_id,
                                resource_type="aws_security_group",
                                cis_benchmark="CIS AWS 5.2",
                                mitre_attack_id="T1190: Exploit Public-Facing Application",
                                mitre_tactic="Initial Access",
                                description=f"Security group '{sg_name}' allows inbound traffic from 0.0.0.0/0 (anywhere) to port {port}.",
                                evidence=f"cidr_blocks = [\"0.0.0.0/0\"] on port {port}",
                                cvss_score=cvss,
                                remediation_cli=f"# Restrict security group '{sg_name}' ingress on port {port} to authorized corporate CIDRs",
                                remediation_terraform=f"""ingress {{
  from_port   = {port}
  to_port     = {port}
  protocol    = "tcp"
  cidr_blocks = ["10.0.0.0/8"] # Restrict to internal VPC CIDR
}}""",
                            ))

        # AWS IAM: Wildcard Permissions
        if "aws_iam_policy" in content_str or "aws_iam_role_policy" in content_str:
            for match in re.finditer(r'resource\s+"aws_iam_(?:role_)?policy"\s+"([^"]+)"\s*{(.*?)(?=\n\s*resource|\Z)', content_str, re.DOTALL):
                pol_name = match.group(1)
                pol_block = match.group(2)
                has_wildcard_action = bool(re.search(r'["\']?action["\']?\s*[:=]\s*["\']?\*["\']?', pol_block, re.IGNORECASE))
                has_wildcard_resource = bool(re.search(r'["\']?resource["\']?\s*[:=]\s*["\']?\*["\']?', pol_block, re.IGNORECASE))
                if has_wildcard_action and (has_wildcard_resource or '"*"' in pol_block):
                    findings.append(CSPMFinding(
                        finding_id="CSPM-AWS-IAM-001",
                        title=f"IAM Policy '{pol_name}' Grants Full Administrator Privileges ('*:*')",
                        provider=CloudProvider.AWS,
                        category=CSPMResourceCategory.IAM,
                        service="IAM",
                        severity=CSPMSeverity.CRITICAL,
                        resource_id=f"aws_iam_policy.{pol_name}",
                        resource_type="aws_iam_policy",
                        cis_benchmark="CIS AWS 1.16",
                        mitre_attack_id="T1078.004: Cloud Accounts",
                        mitre_tactic="Privilege Escalation",
                        description=f"IAM policy '{pol_name}' contains unrestricted wildcard Action '*' on Resource '*', violating the principle of least privilege.",
                        evidence="Action = \"*\" and Resource = \"*\"",
                        cvss_score=9.5,
                        remediation_cli=f"# Detach and scope down IAM policy '{pol_name}' to specific AWS API actions",
                        remediation_terraform="""statement {
  actions   = ["s3:GetObject", "s3:PutObject"] # Least privilege actions
  resources = ["arn:aws:s3:::specific-bucket/*"]
}""",
                    ))

        # Azure Storage Account: HTTP traffic allowed
        if "azurerm_storage_account" in content_str:
            for match in re.finditer(r'resource\s+"azurerm_storage_account"\s+"([^"]+)"\s*{(.*?)(?=\nresource|\Z)', content_str, re.DOTALL):
                sa_name = match.group(1)
                sa_block = match.group(2)
                if 'enable_https_traffic_only = false' in sa_block:
                    findings.append(CSPMFinding(
                        finding_id="CSPM-AZ-STORAGE-001",
                        title=f"Azure Storage Account '{sa_name}' Allows Insecure HTTP Traffic",
                        provider=CloudProvider.AZURE,
                        category=CSPMResourceCategory.DATA_PROTECTION,
                        service="StorageAccount",
                        severity=CSPMSeverity.HIGH,
                        resource_id=f"azurerm_storage_account.{sa_name}",
                        resource_type="azurerm_storage_account",
                        cis_benchmark="CIS Azure 3.1",
                        mitre_attack_id="T1040: Network Sniffing",
                        mitre_tactic="Credential Access",
                        description=f"Storage account '{sa_name}' allows plain unencrypted HTTP connections, exposing blob tokens and data in transit.",
                        evidence="enable_https_traffic_only = false",
                        cvss_score=7.5,
                        remediation_cli=f"az storage account update --name {sa_name} --https-only true",
                        remediation_terraform="""enable_https_traffic_only = true""",
                    ))

        # GCP Storage Bucket: allUsers exposure
        if "google_storage_bucket" in content_str or "google_storage_bucket_iam_binding" in content_str:
            if "allUsers" in content_str or "allAuthenticatedUsers" in content_str:
                findings.append(CSPMFinding(
                    finding_id="CSPM-GCP-GCS-001",
                    title="Google Cloud Storage Bucket Publicly Accessible to allUsers",
                    provider=CloudProvider.GCP,
                    category=CSPMResourceCategory.STORAGE,
                    service="CloudStorage",
                    severity=CSPMSeverity.CRITICAL,
                    resource_id="google_storage_bucket_iam_binding",
                    resource_type="google_storage_bucket_iam_binding",
                    cis_benchmark="CIS GCP 5.1",
                    mitre_attack_id="T1530: Data from Cloud Storage Object",
                    mitre_tactic="Exfiltration",
                    description="Google Cloud Storage IAM binding grants 'allUsers' or 'allAuthenticatedUsers' access, making bucket contents publicly downloadable.",
                    evidence="members = [\"allUsers\"]",
                    cvss_score=9.4,
                    remediation_cli="gsutil iam ch -d allUsers:objectViewer gs://BUCKET_NAME",
                    remediation_terraform="""members = [
  "group:internal-engineers@example.com"
]""",
                ))

        return findings

    # =========================================================================
    # Cloud Configuration Dumps & Generic Auditing
    # =========================================================================

    def scan_cloud_config(self, config_data: Dict[str, Any], provider: CloudProvider = CloudProvider.MULTI_CLOUD) -> List[CSPMFinding]:
        """Audit structured cloud audit dumps (e.g. AWS SecurityHub, Azure Advisor, GCP Security Command Center)."""
        findings: List[CSPMFinding] = []

        # AWS S3 buckets in config
        for b in config_data.get("s3_buckets", []):
            b_name = b.get("name", "unknown-bucket")
            if b.get("public_access", False) or b.get("block_public_access", True) is False:
                findings.append(CSPMFinding(
                    finding_id="CSPM-AWS-S3-001",
                    title=f"S3 Bucket '{b_name}' Public Access Enabled",
                    provider=CloudProvider.AWS,
                    category=CSPMResourceCategory.STORAGE,
                    service="S3",
                    severity=CSPMSeverity.CRITICAL,
                    resource_id=f"arn:aws:s3:::{b_name}",
                    resource_type="s3_bucket",
                    cis_benchmark="CIS AWS 2.1.5",
                    mitre_attack_id="T1530: Data from Cloud Storage Object",
                    mitre_tactic="Exfiltration",
                    description=f"S3 bucket '{b_name}' has public access allowed or Block Public Access settings disabled.",
                    evidence=f"public_access: {b.get('public_access')}, block_public_acls: {b.get('block_public_acls')}",
                    cvss_score=9.4,
                    remediation_cli=f"aws s3api put-public-access-block --bucket {b_name} --public-access-block-configuration 'BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true'",
                    remediation_terraform=f"""resource "aws_s3_bucket_public_access_block" "block" {{
  bucket                  = "{b_name}"
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}}""",
                ))
            if not b.get("encrypted", True):
                findings.append(CSPMFinding(
                    finding_id="CSPM-AWS-S3-002",
                    title=f"S3 Bucket '{b_name}' Missing Default Encryption",
                    provider=CloudProvider.AWS,
                    category=CSPMResourceCategory.DATA_PROTECTION,
                    service="S3",
                    severity=CSPMSeverity.HIGH,
                    resource_id=f"arn:aws:s3:::{b_name}",
                    resource_type="s3_bucket",
                    cis_benchmark="CIS AWS 2.1.1",
                    mitre_attack_id="T1565.001: Stored Data Manipulation",
                    mitre_tactic="Impact",
                    description=f"Bucket '{b_name}' does not enforce server-side encryption.",
                    evidence="encrypted: false",
                    cvss_score=7.1,
                    remediation_cli=f"aws s3api put-bucket-encryption --bucket {b_name} --server-side-encryption-configuration '{{\"Rules\": [{{\"ApplyServerSideEncryptionByDefault\": {{\"SSEAlgorithm\": \"AES256\"}}}}]}}'",
                    remediation_terraform="""# Enable default KMS encryption""",
                ))

        # AWS Security Groups
        for sg in config_data.get("security_groups", []):
            sg_id = sg.get("id", "sg-unknown")
            for rule in sg.get("inbound_rules", []):
                cidr = rule.get("cidr", "")
                from_p = rule.get("from_port", 0)
                to_p = rule.get("to_port", 0)
                if cidr == "0.0.0.0/0":
                    if from_p <= 22 <= to_p:
                        findings.append(CSPMFinding(
                            finding_id="CSPM-AWS-SG-022",
                            title=f"Security Group '{sg_id}' Exposes SSH (Port 22) to Internet",
                            provider=CloudProvider.AWS,
                            category=CSPMResourceCategory.NETWORK,
                            service="SecurityGroups",
                            severity=CSPMSeverity.CRITICAL,
                            resource_id=sg_id,
                            resource_type="security_group",
                            cis_benchmark="CIS AWS 5.2",
                            mitre_attack_id="T1190: Exploit Public-Facing Application",
                            mitre_tactic="Initial Access",
                            description=f"Security group '{sg_id}' allows unrestricted inbound SSH (port 22) from 0.0.0.0/0.",
                            evidence="inbound 0.0.0.0/0:22",
                            cvss_score=9.1,
                            remediation_cli=f"aws ec2 revoke-security-group-ingress --group-id {sg_id} --protocol tcp --port 22 --cidr 0.0.0.0/0",
                            remediation_terraform="# Restrict ingress to corporate bastion IP",
                        ))
                    if from_p <= 3389 <= to_p:
                        findings.append(CSPMFinding(
                            finding_id="CSPM-AWS-SG-3389",
                            title=f"Security Group '{sg_id}' Exposes RDP (Port 3389) to Internet",
                            provider=CloudProvider.AWS,
                            category=CSPMResourceCategory.NETWORK,
                            service="SecurityGroups",
                            severity=CSPMSeverity.CRITICAL,
                            resource_id=sg_id,
                            resource_type="security_group",
                            cis_benchmark="CIS AWS 5.3",
                            mitre_attack_id="T1190: Exploit Public-Facing Application",
                            mitre_tactic="Initial Access",
                            description=f"Security group '{sg_id}' allows unrestricted inbound RDP (port 3389) from 0.0.0.0/0.",
                            evidence="inbound 0.0.0.0/0:3389",
                            cvss_score=9.1,
                            remediation_cli=f"aws ec2 revoke-security-group-ingress --group-id {sg_id} --protocol tcp --port 3389 --cidr 0.0.0.0/0",
                            remediation_terraform="# Restrict ingress to corporate VPN IP",
                        ))

        # Azure Key Vault
        for kv in config_data.get("azure_key_vaults", []):
            kv_name = kv.get("name", "kv-unknown")
            if not kv.get("purge_protection_enabled", True):
                findings.append(CSPMFinding(
                    finding_id="CSPM-AZ-KV-001",
                    title=f"Azure Key Vault '{kv_name}' Missing Purge Protection",
                    provider=CloudProvider.AZURE,
                    category=CSPMResourceCategory.DATA_PROTECTION,
                    service="KeyVault",
                    severity=CSPMSeverity.MEDIUM,
                    resource_id=f"/subscriptions/.../vaults/{kv_name}",
                    resource_type="azurerm_key_vault",
                    cis_benchmark="CIS Azure 8.5",
                    mitre_attack_id="T1485: Data Destruction",
                    mitre_tactic="Impact",
                    description=f"Key Vault '{kv_name}' has purge protection disabled, making certificates and cryptographic keys permanently deleteable upon compromise.",
                    evidence="purge_protection_enabled: false",
                    cvss_score=6.2,
                    remediation_cli=f"az keyvault update --name {kv_name} --enable-purge-protection true",
                    remediation_terraform="""purge_protection_enabled = true""",
                ))

        # CloudTrail
        if "cloudtrail" in config_data:
            ct = config_data["cloudtrail"]
            if not ct.get("is_multi_region_trail", True) or not ct.get("logging", True):
                findings.append(CSPMFinding(
                    finding_id="CSPM-AWS-TRAIL-001",
                    title="AWS CloudTrail is Not Enabled Across All Regions",
                    provider=CloudProvider.AWS,
                    category=CSPMResourceCategory.LOGGING_MONITORING,
                    service="CloudTrail",
                    severity=CSPMSeverity.HIGH,
                    resource_id="arn:aws:cloudtrail:global",
                    resource_type="aws_cloudtrail",
                    cis_benchmark="CIS AWS 3.1",
                    mitre_attack_id="T1562.008: Disable Cloud Logs",
                    mitre_tactic="Defense Evasion",
                    description="CloudTrail is not capturing API activity across all AWS regions, creating blind spots for adversary activity in unmonitored regions.",
                    evidence=f"is_multi_region_trail: {ct.get('is_multi_region_trail')}",
                    cvss_score=7.8,
                    remediation_cli="aws cloudtrail update-trail --name main-trail --is-multi-region-trail",
                    remediation_terraform="""is_multi_region_trail = true""",
                ))

        return findings

    # =========================================================================
    # High-Level Aggregation & Reporting
    # =========================================================================

    def compile_report(self, findings: List[CSPMFinding], environment_name: str = "Enterprise Multi-Cloud Infrastructure", total_scanned: int = 42) -> CSPMReport:
        """Compile findings into an actionable executive & technical CSPM report."""
        import datetime
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        crit = sum(1 for f in findings if f.severity == CSPMSeverity.CRITICAL)
        high = sum(1 for f in findings if f.severity == CSPMSeverity.HIGH)
        med = sum(1 for f in findings if f.severity == CSPMSeverity.MEDIUM)
        low = sum(1 for f in findings if f.severity == CSPMSeverity.LOW)
        info = sum(1 for f in findings if f.severity == CSPMSeverity.INFO)

        # Provider breakdown
        p_counts: Dict[str, int] = {}
        for f in findings:
            p_counts[f.provider.value] = p_counts.get(f.provider.value, 0) + 1

        # Category breakdown
        cat_counts: Dict[str, int] = {}
        for f in findings:
            cat_counts[f.category.value] = cat_counts.get(f.category.value, 0) + 1

        # MITRE tactics breakdown
        mitre_counts: Dict[str, int] = {}
        for f in findings:
            mitre_counts[f.mitre_tactic] = mitre_counts.get(f.mitre_tactic, 0) + 1

        # Weighted compliance score: starts at 100, penalized by severity
        penalty = (crit * 15.0) + (high * 8.0) + (med * 4.0) + (low * 1.5)
        compliance_score = max(0.0, min(100.0, 100.0 - penalty))

        # CIS pass rate approximation based on scanned resources vs failed checks
        total_checks = max(total_scanned * 3, len(findings) + 10)
        cis_pass_rate = max(0.0, min(100.0, ((total_checks - len(findings)) / total_checks) * 100.0))

        # Dynamic Hardening Roadmap
        roadmap: List[str] = []
        if crit > 0:
            roadmap.append(f"P0 IMMEDIATE: Remediate {crit} CRITICAL finding(s) (public storage buckets, open SSH/RDP, privileged containers)")
        if high > 0:
            roadmap.append(f"P1 PRIORITY: Remediate {high} HIGH finding(s) (unencrypted storage, plaintext K8s env secrets, multi-region logging)")
        if med > 0:
            roadmap.append(f"P2 STRENGTHEN: Address {med} MEDIUM finding(s) (NodePort exposures, purge protections, root container enforcement)")
        roadmap.append("P3 CONTINUOUS: Enforce automated IaC gate in CI/CD pipeline preventing non-compliant Terraform and K8s manifests from merging")

        return CSPMReport(
            environment_name=environment_name,
            timestamp=now_str,
            total_resources_scanned=total_scanned,
            total_findings=len(findings),
            critical_count=crit,
            high_count=high,
            medium_count=med,
            low_count=low,
            info_count=info,
            compliance_score=compliance_score,
            cis_pass_rate=cis_pass_rate,
            findings=findings,
            provider_breakdown=p_counts,
            category_breakdown=cat_counts,
            mitre_tactics_breakdown=mitre_counts,
            hardening_roadmap=roadmap,
        )

    # =========================================================================
    # Mock Benchmark Mode (Comprehensive Multi-Cloud Estate Assessment)
    # =========================================================================

    def scan_mock(self) -> CSPMReport:
        """Execute a comprehensive benchmark scan against a simulated enterprise multi-cloud environment."""
        # Simulated sample Terraform
        sample_tf = """
resource "aws_s3_bucket" "prod_customer_exports" {
  bucket = "corp-customer-exports-2026"
  acl    = "public-read"
}

resource "aws_security_group" "prod_dmz_sg" {
  name = "prod-dmz-web-sg"
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_iam_policy" "admin_delegated_policy" {
  name   = "cloud-ops-full-access"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action   = "*"
      Effect   = "Allow"
      Resource = "*"
    }]
  })
}

resource "azurerm_storage_account" "legacy_diagnostics" {
  name                     = "diagstorage2026"
  enable_https_traffic_only = false
}

resource "google_storage_bucket_iam_binding" "public_landing" {
  bucket  = "gcp-analytics-landing"
  role    = "roles/storage.objectViewer"
  members = ["allUsers"]
}
"""
        # Simulated Kubernetes Manifest
        sample_k8s = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-processing-service
  namespace: prod-banking
spec:
  replicas: 3
  template:
    spec:
      hostNetwork: true
      hostPID: true
      volumes:
      - name: docker-socket
        hostPath:
          path: /var/run/docker.sock
      containers:
      - name: payment-worker
        image: payment-worker:v2.4
        securityContext:
          privileged: true
          runAsNonRoot: false
          readOnlyRootFilesystem: false
        env:
        - name: DATABASE_PASSWORD
          value: "SuperSecretPassw0rd!2026"
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: anonymous-admin-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
- kind: User
  name: system:anonymous
"""
        tf_findings = self.scan_terraform(sample_tf)
        k8s_findings = self.scan_kubernetes_manifest(sample_k8s)

        cloud_config_findings = self.scan_cloud_config({
            "cloudtrail": {
                "logging": True,
                "is_multi_region_trail": False,
            },
            "azure_key_vaults": [
                {
                    "name": "kv-enterprise-core-prod",
                    "purge_protection_enabled": False,
                }
            ]
        })

        all_findings = tf_findings + k8s_findings + cloud_config_findings
        return self.compile_report(
            all_findings,
            environment_name="Enterprise Multi-Cloud AWS/Azure/GCP & Kubernetes Estate",
            total_scanned=58
        )

    def scan_path(self, target_path: str) -> CSPMReport:
        """Scan a file or directory for Terraform and Kubernetes manifests."""
        p = Path(target_path)
        if not p.exists():
            raise FileNotFoundError(f"Target path does not exist: {target_path}")

        files_to_scan: List[Path] = []
        if p.is_file():
            files_to_scan = [p]
        elif p.is_dir():
            files_to_scan = [
                f for f in p.rglob("*")
                if f.is_file() and f.suffix in (".tf", ".yaml", ".yml", ".json")
            ]

        all_findings: List[CSPMFinding] = []
        for file in files_to_scan:
            try:
                content = file.read_text(encoding="utf-8")
                if file.suffix == ".tf":
                    all_findings.extend(self.scan_terraform(content, filename=file.name))
                elif file.suffix in (".yaml", ".yml"):
                    all_findings.extend(self.scan_kubernetes_manifest(content, filename=file.name))
                elif file.suffix == ".json":
                    try:
                        data = json.loads(content)
                        if isinstance(data, dict):
                            if "kind" in data:
                                all_findings.extend(self.scan_kubernetes_manifest(data, filename=file.name))
                            else:
                                all_findings.extend(self.scan_cloud_config(data))
                    except json.JSONDecodeError:
                        pass
            except Exception as e:
                self.logger.warning(f"Error scanning file {file}: {e}")

        return self.compile_report(
            all_findings,
            environment_name=f"Filesystem Audit: {p.name}",
            total_scanned=max(len(files_to_scan), len(all_findings))
        )
