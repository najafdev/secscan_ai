#!/usr/bin/env python3
# SecScan AI core module
"""
Enterprise API Security Scanner & OpenAPI / Swagger Auditor for SecScan AI.
Evaluates REST and microservice APIs against the OWASP API Security Top 10 (2023-2026),
detecting BOLA, Broken Auth, Mass Assignment, BFLA, SSRF, and Security Misconfigurations.
"""

from __future__ import annotations

import re
import json
import logging
from enum import Enum
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field, asdict

import yaml

logger = logging.getLogger(__name__)


class OWASPAPICategory(str, Enum):
    """OWASP API Security Top 10 categories."""
    API1_BOLA = "API1: Broken Object Level Authorization"
    API2_BROKEN_AUTHENTICATION = "API2: Broken Authentication"
    API3_BOPLA = "API3: Broken Object Property Level Authorization"
    API4_UNRESTRICTED_RESOURCES = "API4: Unrestricted Resource Consumption"
    API5_BFLA = "API5: Broken Function Level Authorization"
    API6_SENSITIVE_FLOWS = "API6: Unrestricted Access to Sensitive Business Flows"
    API7_SSRF = "API7: Server-Side Request Forgery"
    API8_MISCONFIGURATION = "API8: Security Misconfiguration"
    API9_IMPROPER_INVENTORY = "API9: Improper Inventory Management"
    API10_UNSAFE_CONSUMPTION = "API10: Unsafe Consumption of APIs"


@dataclass
class APIFinding:
    """An individual security finding detected during API inspection."""
    finding_id: str
    title: str
    category: OWASPAPICategory
    severity: str  # "critical", "high", "medium", "low"
    endpoint: str
    http_method: str
    description: str
    evidence: str
    cvss_score: float
    remediation: str

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res["category"] = self.category.value
        return res


@dataclass
class APISecurityReport:
    """Aggregated assessment report for an API surface or OpenAPI spec."""
    api_title: str
    api_version: str
    endpoints_scanned: int
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    security_score: float  # 0.0 to 100.0 (100 = flawless)
    risk_rating: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    findings: List[APIFinding]
    category_summary: Dict[str, int]
    hardening_recommendations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "api_title": self.api_title,
            "api_version": self.api_version,
            "endpoints_scanned": self.endpoints_scanned,
            "total_findings": self.total_findings,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "security_score": self.security_score,
            "risk_rating": self.risk_rating,
            "category_summary": self.category_summary,
            "findings": [f.to_dict() for f in self.findings],
            "hardening_recommendations": self.hardening_recommendations,
        }


class APISecurityScanner:
    """
    Automated API Security Scanner for OpenAPI (Swagger) v2/v3/v3.1 definitions
    and live microservice endpoints.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def parse_spec(self, spec_data: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Parse raw JSON or YAML OpenAPI specification string into Python dictionary.
        """
        if isinstance(spec_data, dict):
            return spec_data

        content = spec_data.strip()
        if content.startswith("{") or content.startswith("["):
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed parsing JSON spec: {e}")

        # Fallback to YAML
        try:
            parsed = yaml.safe_load(content)
            if isinstance(parsed, dict):
                return parsed
        except Exception as e:
            self.logger.warning(f"Failed parsing YAML spec: {e}")

        return {}

    def scan_spec(self, spec_data: Union[str, Dict[str, Any]]) -> APISecurityReport:
        """
        Scan an OpenAPI / Swagger definition and return a comprehensive APISecurityReport.
        """
        spec = self.parse_spec(spec_data)
        if not spec:
            return self._build_empty_report("Unknown API", "0.0.0")

        info = spec.get("info", {})
        api_title = info.get("title", "SecScan AI Target API")
        api_version = str(info.get("version", "1.0.0"))

        global_security = spec.get("security", [])
        paths = spec.get("paths", {})
        findings: List[APIFinding] = []
        endpoint_count = 0

        # Patterns indicative of sensitive mass-assignment target properties
        mass_assignment_keywords = {
            "role", "roles", "is_admin", "admin", "permissions", "privileges",
            "balance", "credit", "is_verified", "account_type", "status", "tenant_id"
        }

        # Sensitive business flow routes requiring rate limiting / CAPTCHA
        sensitive_flow_keywords = {
            "login", "signin", "auth", "register", "signup", "checkout",
            "transfer", "withdraw", "payment", "reset-password", "forgot-password", "otp"
        }

        # Administrative function keywords
        admin_keywords = {"admin", "system", "manage", "tenant", "internal", "config", "debug", "actuator"}

        for path_str, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            for method_str, op in path_item.items():
                method = method_str.upper()
                if method not in ("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"):
                    continue

                endpoint_count += 1
                op_id = op.get("operationId", f"{method}_{path_str}")
                op_security = op.get("security", global_security)
                tags = op.get("tags", [])
                deprecated = op.get("deprecated", False)

                # -------------------------------------------------------------
                # 1. API1: Broken Object Level Authorization (BOLA / IDOR)
                # -------------------------------------------------------------
                # Check for direct object reference identifier in path
                id_params = re.findall(r"\{([a-zA-Z0-9_-]*(?:id|key|uuid|account|user|tenant)[a-zA-Z0-9_-]*)\}", path_str, re.IGNORECASE)
                if id_params:
                    # If endpoint operates on an entity ID, check if it specifies auth scopes or policies
                    if not op_security:
                        findings.append(APIFinding(
                            finding_id=f"BOLA_{method}_{path_str}",
                            title=f"Unauthenticated BOLA / IDOR Risk on Object Route",
                            category=OWASPAPICategory.API1_BOLA,
                            severity="critical",
                            endpoint=path_str,
                            http_method=method,
                            description=f"Path parameter {id_params} references specific entity directly without declared authentication or authorization constraints.",
                            evidence=f"Parameters: {id_params}; Security: None declared.",
                            cvss_score=9.1,
                            remediation="Require authentication and enforce strict tenancy/ownership checks verifying requester owns the requested object ID."
                        ))
                    elif method in ("PUT", "DELETE", "PATCH"):
                        # State modification with object ID requires granular ownership validation
                        findings.append(APIFinding(
                            finding_id=f"BOLA_MUT_{method}_{path_str}",
                            title=f"Object State Modification Without Granular Scope",
                            category=OWASPAPICategory.API1_BOLA,
                            severity="high",
                            endpoint=path_str,
                            http_method=method,
                            description=f"State-altering method {method} on {path_str} allows modifying entity {id_params}. Ensure policy engine checks subject ownership before applying mutation.",
                            evidence=f"Method {method} with object reference {id_params}.",
                            cvss_score=8.5,
                            remediation="Enforce object-level access control middleware verifying the authenticated user's tenant ID matches the entity's owner ID."
                        ))

                # -------------------------------------------------------------
                # 2. API2: Broken Authentication
                # -------------------------------------------------------------
                if not op_security and not any(kw in path_str.lower() for kw in ("health", "ping", "docs", "swagger", "openapi")):
                    findings.append(APIFinding(
                        finding_id=f"AUTH_{method}_{path_str}",
                        title="Endpoint Missing Authentication Enforcement",
                        category=OWASPAPICategory.API2_BROKEN_AUTHENTICATION,
                        severity="high",
                        endpoint=path_str,
                        http_method=method,
                        description=f"The endpoint {method} {path_str} does not declare any security schemes or bearer token requirements.",
                        evidence="Empty security array for endpoint and global specification.",
                        cvss_score=8.2,
                        remediation="Add security scheme (e.g. bearerAuth / OAuth2) to the endpoint definition and require valid JWT verification."
                    ))

                # -------------------------------------------------------------
                # 3. API3: BOPLA (Mass Assignment & Excessive Data Exposure)
                # -------------------------------------------------------------
                if method in ("POST", "PUT", "PATCH"):
                    request_body = op.get("requestBody", {})
                    content_schema = (
                        request_body.get("content", {})
                        .get("application/json", {})
                        .get("schema", {})
                    )
                    props = content_schema.get("properties", {})
                    matched_sensitive = [p for p in props.keys() if p.lower() in mass_assignment_keywords]
                    if matched_sensitive:
                        findings.append(APIFinding(
                            finding_id=f"MASS_ASSIGN_{method}_{path_str}",
                            title="Potential Mass Assignment Vulnerability (BOPLA)",
                            category=OWASPAPICategory.API3_BOPLA,
                            severity="high",
                            endpoint=path_str,
                            http_method=method,
                            description=f"Client input schema directly binds sensitive administrative attributes: {matched_sensitive}.",
                            evidence=f"Sensitive properties allowed in request body: {matched_sensitive}",
                            cvss_score=7.8,
                            remediation="Implement dedicated Data Transfer Objects (DTOs) with strict property whitelisting to disallow client modification of role or privilege fields."
                        ))

                # -------------------------------------------------------------
                # 4. API4: Unrestricted Resource Consumption (Rate Limiting)
                # -------------------------------------------------------------
                if method == "GET":
                    params = op.get("parameters", [])
                    has_pagination = any(
                        p.get("name", "").lower() in ("limit", "page", "size", "offset", "count", "per_page")
                        for p in params if isinstance(p, dict)
                    )
                    # List endpoints returning collections without pagination
                    if not has_pagination and not id_params:
                        findings.append(APIFinding(
                            finding_id=f"RES_CONSUME_{method}_{path_str}",
                            title="Missing Pagination on Collection Endpoint",
                            category=OWASPAPICategory.API4_UNRESTRICTED_RESOURCES,
                            severity="medium",
                            endpoint=path_str,
                            http_method=method,
                            description=f"Collection endpoint {path_str} lacks declared pagination parameters, exposing backend to denial of service via memory exhaustion.",
                            evidence="No limit/page/offset query parameters specified.",
                            cvss_score=6.5,
                            remediation="Enforce mandatory pagination with strict default (e.g. limit=20) and maximum ceiling (e.g. max=100)."
                        ))

                # -------------------------------------------------------------
                # 5. API5: Broken Function Level Authorization (BFLA)
                # -------------------------------------------------------------
                is_admin_route = any(kw in path_str.lower() for kw in admin_keywords)
                if is_admin_route:
                    # Check if endpoint requires dedicated admin role / scope
                    sec_scopes = []
                    for s in op_security:
                        for s_name, s_scopes in s.items():
                            sec_scopes.extend(s_scopes)

                    has_admin_scope = any("admin" in s.lower() or "system" in s.lower() for s in sec_scopes)
                    if not has_admin_scope:
                        findings.append(APIFinding(
                            finding_id=f"BFLA_{method}_{path_str}",
                            title="Administrative Function Without Dedicated Role Scope (BFLA)",
                            category=OWASPAPICategory.API5_BFLA,
                            severity="high",
                            endpoint=path_str,
                            http_method=method,
                            description=f"Administrative endpoint {path_str} does not mandate specific administrative role scopes, risking horizontal or vertical privilege escalation.",
                            evidence=f"Security scopes present: {sec_scopes}; Missing dedicated admin scope.",
                            cvss_score=8.5,
                            remediation="Enforce explicit Role-Based Access Control (RBAC) middleware verifying caller possesses the 'admin' permission."
                        ))

                # -------------------------------------------------------------
                # 6. API6: Sensitive Business Flow Abuse
                # -------------------------------------------------------------
                if any(flow in path_str.lower() for flow in sensitive_flow_keywords):
                    # Check if rate limiting or captcha header is noted
                    responses = op.get("responses", {})
                    has_rate_limit_resp = "429" in responses or 429 in responses
                    if not has_rate_limit_resp:
                        findings.append(APIFinding(
                            finding_id=f"SENS_FLOW_{method}_{path_str}",
                            title="Sensitive Business Flow Missing Rate Limiting Specification",
                            category=OWASPAPICategory.API6_SENSITIVE_FLOWS,
                            severity="medium",
                            endpoint=path_str,
                            http_method=method,
                            description=f"Critical business flow {path_str} does not declare HTTP 429 Too Many Requests response handling or throttling controls.",
                            evidence="HTTP 429 rate limit response missing from endpoint contract.",
                            cvss_score=5.8,
                            remediation="Apply IP and account-based rate limiting (e.g. 5 attempts per minute) and return HTTP 429 upon threshold breach."
                        ))

                # -------------------------------------------------------------
                # 7. API7: Server-Side Request Forgery (SSRF)
                # -------------------------------------------------------------
                params = op.get("parameters", [])
                url_params = [
                    p.get("name") for p in params
                    if isinstance(p, dict) and any(u in p.get("name", "").lower() for u in ("url", "uri", "webhook", "callback", "redirect", "dest", "target"))
                ]
                if url_params:
                    findings.append(APIFinding(
                        finding_id=f"SSRF_{method}_{path_str}",
                        title="Potential SSRF Parameter Detected",
                        category=OWASPAPICategory.API7_SSRF,
                        severity="high",
                        endpoint=path_str,
                        http_method=method,
                        description=f"Endpoint accepts remote resource address via parameter(s): {url_params}. Potential for internal cloud metadata or intranet scraping.",
                        evidence=f"Parameters: {url_params}",
                        cvss_score=8.0,
                        remediation="Validate destination URLs against an explicit allowlist and disallow resolution to RFC 1918 private IP ranges or 169.254.169.254."
                    ))

                # -------------------------------------------------------------
                # 8. API8: Security Misconfiguration (Debug & Profiler Routes)
                # -------------------------------------------------------------
                if any(kw in path_str.lower() for kw in ("actuator", "_profiler", "env", "phpinfo", "debug")):
                    findings.append(APIFinding(
                        finding_id=f"MISCONFIG_{method}_{path_str}",
                        title="Exposed Framework Debug / Diagnostic Endpoint",
                        category=OWASPAPICategory.API8_MISCONFIGURATION,
                        severity="high",
                        endpoint=path_str,
                        http_method=method,
                        description=f"Internal diagnostic endpoint {path_str} is documented in public API specification, exposing system state and metrics.",
                        evidence=f"Diagnostic path exposed: {path_str}",
                        cvss_score=7.5,
                        remediation="Disable or restrict debug and telemetry routes to loopback interfaces with mutual TLS."
                    ))

                # -------------------------------------------------------------
                # 9. API9: Improper Inventory Management (Deprecated / Shadow APIs)
                # -------------------------------------------------------------
                if deprecated:
                    findings.append(APIFinding(
                        finding_id=f"DEPRECATED_{method}_{path_str}",
                        title="Deprecated Endpoint Retained in Inventory",
                        category=OWASPAPICategory.API9_IMPROPER_INVENTORY,
                        severity="low",
                        endpoint=path_str,
                        http_method=method,
                        description=f"Endpoint {method} {path_str} is marked as deprecated but still active. Legacy endpoints often harbor unpatched flaws.",
                        evidence="deprecated: true in endpoint schema.",
                        cvss_score=4.0,
                        remediation="Establish a formal sunset schedule and retire deprecated endpoints with HTTP 410 Gone responses."
                    ))

        return self._compile_report(api_title, api_version, endpoint_count, findings)

    def scan_mock(self) -> APISecurityReport:
        """
        Execute deterministic evaluation using a built-in benchmark API spec for CI/offline use.
        """
        mock_spec = {
            "openapi": "3.0.0",
            "info": {"title": "SecScan AI Enterprise Sample Microservice", "version": "2.4.0"},
            "security": [],
            "paths": {
                "/api/v1/users/{userId}": {
                    "get": {
                        "summary": "Retrieve user profile by ID",
                        "security": [],
                        "parameters": [{"name": "userId", "in": "path", "required": True, "schema": {"type": "integer"}}]
                    },
                    "delete": {
                        "summary": "Delete user profile by ID",
                        "security": [{"bearerAuth": []}],
                        "parameters": [{"name": "userId", "in": "path", "required": True, "schema": {"type": "integer"}}]
                    }
                },
                "/api/v1/users": {
                    "get": {
                        "summary": "List all users without pagination",
                        "security": [{"bearerAuth": []}]
                    },
                    "post": {
                        "summary": "Create user with mass assignment risk",
                        "security": [{"bearerAuth": []}],
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "username": {"type": "string"},
                                            "email": {"type": "string"},
                                            "is_admin": {"type": "boolean"},
                                            "role": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "/api/v1/admin/tenants": {
                    "get": {
                        "summary": "Administrative tenant overview without admin scope",
                        "security": [{"bearerAuth": ["read:profile"]}]
                    }
                },
                "/api/v1/webhooks/trigger": {
                    "post": {
                        "summary": "Webhook trigger accepting arbitrary destination",
                        "security": [{"bearerAuth": []}],
                        "parameters": [{"name": "callback_url", "in": "query", "schema": {"type": "string"}}]
                    }
                },
                "/actuator/env": {
                    "get": {
                        "summary": "Exposed Spring Boot Actuator environment diagnostic",
                        "security": []
                    }
                }
            }
        }
        return self.scan_spec(mock_spec)

    def _compile_report(
        self,
        api_title: str,
        api_version: str,
        endpoint_count: int,
        findings: List[APIFinding]
    ) -> APISecurityReport:
        """Compile raw findings into metrics, scores, and categorized summaries."""
        crit = sum(1 for f in findings if f.severity == "critical")
        high = sum(1 for f in findings if f.severity == "high")
        med = sum(1 for f in findings if f.severity == "medium")
        low = sum(1 for f in findings if f.severity == "low")
        total = len(findings)

        # Calculate security score (100 base, with penalty deductions)
        penalty = (crit * 25.0) + (high * 15.0) + (med * 8.0) + (low * 3.0)
        score = max(0.0, 100.0 - penalty)

        if score >= 85.0:
            rating = "LOW"
        elif score >= 65.0:
            rating = "MEDIUM"
        elif score >= 40.0:
            rating = "HIGH"
        else:
            rating = "CRITICAL"

        # Category summary
        cat_summary: Dict[str, int] = {}
        for cat in OWASPAPICategory:
            cat_summary[cat.value] = sum(1 for f in findings if f.category == cat)

        # Strategic recommendations
        recs = []
        if crit > 0:
            recs.append("CRITICAL: Eliminate unauthenticated BOLA routes immediately by adding authentication and tenancy validation.")
        if any(f.category == OWASPAPICategory.API3_BOPLA for f in findings):
            recs.append("Adopt strict DTO whitelisting for all POST/PUT/PATCH schemas to prevent Mass Assignment.")
        if any(f.category == OWASPAPICategory.API5_BFLA for f in findings):
            recs.append("Implement role-based authorization gates on all administrative routes.")
        if any(f.category == OWASPAPICategory.API7_SSRF for f in findings):
            recs.append("Deploy strict URL allowlisting and RFC 1918 egress filtering on webhook handlers.")
        if not recs:
            recs.append("API demonstrates strong compliance with OWASP API Security guidelines.")

        return APISecurityReport(
            api_title=api_title,
            api_version=api_version,
            endpoints_scanned=endpoint_count,
            total_findings=total,
            critical_count=crit,
            high_count=high,
            medium_count=med,
            low_count=low,
            security_score=round(score, 1),
            risk_rating=rating,
            findings=findings,
            category_summary=cat_summary,
            hardening_recommendations=recs
        )

    def _build_empty_report(self, title: str, version: str) -> APISecurityReport:
        """Fallback empty report when parsing fails or input is null."""
        return APISecurityReport(
            api_title=title,
            api_version=version,
            endpoints_scanned=0,
            total_findings=0,
            critical_count=0,
            high_count=0,
            medium_count=0,
            low_count=0,
            security_score=100.0,
            risk_rating="LOW",
            findings=[],
            category_summary={cat.value: 0 for cat in OWASPAPICategory},
            hardening_recommendations=["Provide a valid OpenAPI or Swagger definition to execute assessment."]
        )
