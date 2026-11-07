"""
HackBot Zero-Day Active Attack Engine
=======================================
Active scanning, stateful fuzzing, target mapping, AI reasoning,
and parallel execution for autonomous vulnerability discovery.

Subsystems:
  - HttpClient          — Session-aware HTTP with baselines
  - TargetMapper        — Crawl → map endpoints → build attack surface
  - StatefulFuzzer      — Auth-aware fuzzing with CSRF / cookie persistence
  - AIReasoningLayer    — Heuristic scoring to decide next attack action
  - ParallelExecutor    — Concurrent requests for speed + race conditions
  - ActiveScanLoop      — Orchestrates the full attack cycle

Developed by Yashab Alam
"""

from __future__ import annotations

import hashlib
import html.parser
import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse, parse_qs, urlencode

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from hackbot.core.zeroday import (
    AnomalySignal,
    ExploitChain,
    FuzzResult,
    ZeroDayEngine,
    FUZZ_PAYLOADS,
)

logger = logging.getLogger(__name__)


# ── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class EndpointInfo:
    """Discovered endpoint with attack-relevant metadata."""
    url: str
    methods: List[str] = field(default_factory=lambda: ["GET"])
    params: List[str] = field(default_factory=list)
    content_type: str = ""
    has_form: bool = False
    form_fields: List[Dict[str, str]] = field(default_factory=list)
    requires_auth: bool = False
    technology: str = ""
    interest_score: float = 0.0
    tested: bool = False
    findings: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "methods": self.methods,
            "params": self.params,
            "content_type": self.content_type,
            "has_form": self.has_form,
            "form_fields": self.form_fields,
            "requires_auth": self.requires_auth,
            "technology": self.technology,
            "interest_score": self.interest_score,
            "tested": self.tested,
        }


@dataclass
class FuzzSession:
    """Tracks a complete stateful fuzzing campaign."""
    target_url: str
    parameter: str
    session_cookies: Dict[str, str] = field(default_factory=dict)
    csrf_token: str = ""
    csrf_field: str = ""
    auth_token: str = ""
    baseline_code: int = 200
    baseline_length: int = 0
    baseline_time: float = 0.0
    results: List[FuzzResult] = field(default_factory=list)
    interesting_count: int = 0
    total_sent: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_url": self.target_url,
            "parameter": self.parameter,
            "total_sent": self.total_sent,
            "interesting_count": self.interesting_count,
            "has_auth": bool(self.auth_token or self.session_cookies),
            "has_csrf": bool(self.csrf_token),
        }


@dataclass
class AttackState:
    """Global state for AI reasoning across the scan."""
    target_base: str = ""
    endpoints: Dict[str, EndpointInfo] = field(default_factory=dict)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    anomalies: List[AnomalySignal] = field(default_factory=list)
    tech_stack: Set[str] = field(default_factory=set)
    tested_params: Set[str] = field(default_factory=set)
    response_history: List[Dict[str, Any]] = field(default_factory=list)
    iteration: int = 0


@dataclass
class ScanConfig:
    """Configuration for an active scan."""
    max_depth: int = 3
    max_pages: int = 100
    max_fuzz_per_param: int = 50
    max_iterations: int = 20
    concurrency: int = 10
    request_timeout: int = 15
    request_delay: float = 0.1
    same_domain_only: bool = True
    follow_redirects: bool = True
    user_agent: str = "HackBot/2.0 ZeroDay-Scanner"
    auth_username: str = ""
    auth_password: str = ""
    auth_url: str = ""
    custom_headers: Dict[str, str] = field(default_factory=dict)
    proxy: str = ""
    scope_patterns: List[str] = field(default_factory=list)


# ── Link / Form Extractor ────────────────────────────────────────────────────

class _LinkFormParser(html.parser.HTMLParser):
    """HTML parser that extracts links, forms, and form fields."""

    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url
        self.links: Set[str] = set()
        self.forms: List[Dict[str, Any]] = []
        self._current_form: Optional[Dict[str, Any]] = None

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        attr = dict(attrs)
        if tag == "a" and attr.get("href"):
            url = urljoin(self.base_url, attr["href"])
            self.links.add(url.split("#")[0].split("?")[0])
        elif tag == "form":
            self._current_form = {
                "action": urljoin(self.base_url, attr.get("action", "")),
                "method": (attr.get("method") or "GET").upper(),
                "fields": [],
            }
        elif tag in ("input", "textarea", "select") and self._current_form is not None:
            field_info = {
                "name": attr.get("name", ""),
                "type": attr.get("type", "text"),
                "value": attr.get("value", ""),
            }
            if field_info["name"]:
                self._current_form["fields"].append(field_info)
        elif tag == "script" and attr.get("src"):
            self.links.add(urljoin(self.base_url, attr["src"]))

    def handle_endtag(self, tag: str) -> None:
        if tag == "form" and self._current_form is not None:
            self.forms.append(self._current_form)
            self._current_form = None


# ── HttpClient ───────────────────────────────────────────────────────────────

class HttpClient:
    """
    Session-aware HTTP client with automatic cookie/auth persistence
    and response baseline tracking.
    """

    def __init__(self, config: Optional[ScanConfig] = None):
        self.config = config or ScanConfig()
        self.session = requests.Session()
        self._setup_session()
        self._baselines: Dict[str, Dict[str, float]] = {}
        self._response_history: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def _setup_session(self) -> None:
        retry = Retry(total=2, backoff_factor=0.3, status_forcelist=[502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry, pool_maxsize=self.config.concurrency + 5)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update({
            "User-Agent": self.config.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/json,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        if self.config.custom_headers:
            self.session.headers.update(self.config.custom_headers)
        if self.config.proxy:
            self.session.proxies = {"http": self.config.proxy, "https": self.config.proxy}
        self.session.verify = False  # Pentest context: accept self-signed certs

    def request(
        self,
        method: str,
        url: str,
        data: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        allow_redirects: Optional[bool] = None,
    ) -> Optional[requests.Response]:
        """Make an HTTP request with timing and history tracking."""
        if allow_redirects is None:
            allow_redirects = self.config.follow_redirects

        if self.config.request_delay > 0:
            time.sleep(self.config.request_delay)

        start = time.time()
        try:
            resp = self.session.request(
                method=method.upper(),
                url=url,
                data=data,
                json=json_data,
                headers=headers,
                timeout=self.config.request_timeout,
                allow_redirects=allow_redirects,
            )
            elapsed = time.time() - start

            record = {
                "url": url,
                "method": method.upper(),
                "status": resp.status_code,
                "length": len(resp.content),
                "time": round(elapsed, 4),
                "headers": dict(resp.headers),
                "timestamp": time.time(),
            }
            with self._lock:
                self._response_history.append(record)
                if len(self._response_history) > 500:
                    self._response_history = self._response_history[-300:]

            return resp
        except requests.RequestException as e:
            logger.debug(f"Request failed: {method} {url} — {e}")
            return None

    def get(self, url: str, **kwargs: Any) -> Optional[requests.Response]:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> Optional[requests.Response]:
        return self.request("POST", url, **kwargs)

    def get_baseline(self, url: str) -> Dict[str, float]:
        """Get or establish a response baseline for a URL."""
        if url in self._baselines:
            return self._baselines[url]

        times, lengths = [], []
        for _ in range(3):
            resp = self.get(url)
            if resp is not None:
                times.append(resp.elapsed.total_seconds())
                lengths.append(len(resp.content))

        if times:
            baseline = {
                "avg_time": sum(times) / len(times),
                "avg_length": sum(lengths) / len(lengths),
                "min_time": min(times),
                "max_time": max(times),
            }
        else:
            baseline = {"avg_time": 0, "avg_length": 0, "min_time": 0, "max_time": 0}

        self._baselines[url] = baseline
        return baseline

    def login(self, login_url: str, username: str, password: str,
              username_field: str = "username", password_field: str = "password") -> bool:
        """Authenticate and persist the session."""
        resp = self.post(login_url, data={username_field: username, password_field: password})
        if resp is not None and resp.status_code in (200, 301, 302, 303):
            logger.info(f"Login successful at {login_url}")
            return True
        logger.warning(f"Login failed at {login_url}")
        return False

    @property
    def cookies(self) -> Dict[str, str]:
        return {str(k): str(v) for k, v in self.session.cookies.get_dict().items() if v is not None}

    @property
    def history(self) -> List[Dict[str, Any]]:
        return list(self._response_history)


# ── TargetMapper ─────────────────────────────────────────────────────────────

class TargetMapper:
    """Crawl a target, extract endpoints, build an attack surface map."""

    HIGH_VALUE_PATTERNS = [
        (r"(?:login|signin|auth|sso)", "auth_endpoint"),
        (r"(?:upload|file|attach|import)", "file_upload"),
        (r"(?:admin|dashboard|manage|panel)", "admin_panel"),
        (r"(?:api|graphql|rest|v[0-9]+)", "api_endpoint"),
        (r"(?:search|query|find|lookup)", "search_endpoint"),
        (r"(?:user|profile|account|setting)", "user_endpoint"),
        (r"(?:webhook|callback|notify|hook)", "webhook_endpoint"),
        (r"(?:redirect|return|next|goto|url=)", "redirect_param"),
        (r"(?:download|export|report|generate)", "data_export"),
        (r"(?:comment|feedback|contact|message)", "user_input"),
    ]

    TECH_HEADERS = {
        "X-Powered-By": "server_tech",
        "Server": "server_tech",
        "X-AspNet-Version": "aspnet",
        "X-Generator": "generator",
        "X-Drupal-Cache": "drupal",
    }

    def __init__(self, client: HttpClient, config: Optional[ScanConfig] = None):
        self.client = client
        self.config = config or ScanConfig()
        self.endpoints: Dict[str, EndpointInfo] = {}
        self.tech_stack: Set[str] = set()
        self._visited: Set[str] = set()
        self._domain: str = ""

    def crawl(self, start_url: str) -> Dict[str, EndpointInfo]:
        """Crawl from start_url and build endpoint map."""
        parsed = urlparse(start_url)
        self._domain = parsed.netloc
        self._crawl_recursive(start_url, depth=0)
        self._score_endpoints()
        logger.info(f"Mapped {len(self.endpoints)} endpoints on {self._domain}")
        return self.endpoints

    def _crawl_recursive(self, url: str, depth: int) -> None:
        if depth > self.config.max_depth:
            return
        if len(self._visited) >= self.config.max_pages:
            return

        normalized = url.split("?")[0].split("#")[0]
        if normalized in self._visited:
            return
        self._visited.add(normalized)

        resp = self.client.get(url)
        if resp is None:
            return

        self._detect_tech(resp)
        content_type = resp.headers.get("Content-Type", "")

        ep = self.endpoints.get(normalized, EndpointInfo(url=normalized))
        ep.content_type = content_type

        # Extract query params from original URL
        parsed = urlparse(url)
        if parsed.query:
            for param in parse_qs(parsed.query).keys():
                if param not in ep.params:
                    ep.params.append(param)

        if "text/html" in content_type:
            try:
                parser = _LinkFormParser(url)
                parser.feed(resp.text)
            except Exception:
                parser = _LinkFormParser(url)
                parser.links = set()
                parser.forms = []

            # Process forms
            for form in parser.forms:
                ep.has_form = True
                ep.form_fields = form.get("fields", [])
                form_url = form.get("action", normalized)
                form_norm = form_url.split("?")[0].split("#")[0]
                form_ep = self.endpoints.get(form_norm, EndpointInfo(url=form_norm))
                form_ep.methods = list(set(form_ep.methods + [form.get("method", "POST")]))
                form_ep.has_form = True
                form_ep.form_fields = form.get("fields", [])
                for f in form.get("fields", []):
                    if f["name"] and f["name"] not in form_ep.params:
                        form_ep.params.append(f["name"])
                self.endpoints[form_norm] = form_ep

            # Follow links
            for link in parser.links:
                link_parsed = urlparse(link)
                if self.config.same_domain_only and link_parsed.netloc != self._domain:
                    continue
                if link_parsed.scheme not in ("http", "https", ""):
                    continue
                self._crawl_recursive(link, depth + 1)

        self.endpoints[normalized] = ep

    def _detect_tech(self, resp: requests.Response) -> None:
        for header, label in self.TECH_HEADERS.items():
            val = resp.headers.get(header, "")
            if val:
                self.tech_stack.add(f"{label}:{val}")
        body_lower = resp.text[:5000].lower() if resp.text else ""
        tech_sigs = [
            ("wp-content", "WordPress"), ("drupal", "Drupal"), ("joomla", "Joomla"),
            ("laravel", "Laravel"), ("django", "Django"), ("flask", "Flask"),
            ("express", "Express"), ("rails", "Rails"), ("spring", "Spring"),
            ("react", "React"), ("angular", "Angular"), ("vue", "Vue.js"),
            ("next.js", "Next.js"), ("nuxt", "Nuxt"), ("graphql", "GraphQL"),
        ]
        for sig, name in tech_sigs:
            if sig in body_lower:
                self.tech_stack.add(name)

    def _score_endpoints(self) -> None:
        for ep in self.endpoints.values():
            score = 0.0
            url_lower = ep.url.lower()
            for pattern, label in self.HIGH_VALUE_PATTERNS:
                if re.search(pattern, url_lower):
                    score += 3.0
            score += len(ep.params) * 1.5
            if ep.has_form:
                score += 2.0
            if "POST" in ep.methods:
                score += 1.5
            if ep.requires_auth:
                score += 1.0
            ep.interest_score = round(score, 1)

    def get_prioritized(self) -> List[EndpointInfo]:
        return sorted(self.endpoints.values(), key=lambda e: e.interest_score, reverse=True)


# ── StatefulFuzzer ───────────────────────────────────────────────────────────

class StatefulFuzzer:
    """Session-aware fuzzer that maintains auth, cookies, and CSRF tokens."""

    CSRF_PATTERNS = [
        re.compile(r'name=["\']?(csrf[_-]?token|_token|csrfmiddlewaretoken|__RequestVerificationToken|authenticity_token)["\']?\s+value=["\']?([^"\'>\s]+)', re.I),
        re.compile(r'<meta\s+name=["\']?csrf-token["\']?\s+content=["\']?([^"\'>\s]+)', re.I),
    ]

    def __init__(self, client: HttpClient, engine: ZeroDayEngine, config: Optional[ScanConfig] = None):
        self.client = client
        self.engine = engine
        self.config = config or ScanConfig()
        self.sessions: Dict[str, FuzzSession] = {}

    def _extract_csrf(self, resp: requests.Response) -> Tuple[str, str]:
        for pat in self.CSRF_PATTERNS:
            m = pat.search(resp.text)
            if m:
                groups = m.groups()
                if len(groups) == 2:
                    return groups[0], groups[1]
                elif len(groups) == 1:
                    return "csrf_token", groups[0]
        return "", ""

    def _refresh_csrf(self, session: FuzzSession) -> None:
        resp = self.client.get(session.target_url)
        if resp is not None:
            csrf_field, csrf_token = self._extract_csrf(resp)
            if csrf_token:
                session.csrf_field = csrf_field
                session.csrf_token = csrf_token

    def _establish_baseline(self, session: FuzzSession) -> None:
        baseline = self.client.get_baseline(session.target_url)
        session.baseline_time = baseline["avg_time"]
        resp = self.client.get(session.target_url)
        if resp is not None:
            session.baseline_code = resp.status_code
            session.baseline_length = len(resp.content)

    def fuzz_parameter(
        self,
        url: str,
        parameter: str,
        categories: Optional[List[str]] = None,
        method: str = "GET",
        extra_data: Optional[Dict[str, str]] = None,
        max_payloads: int = 0,
    ) -> FuzzSession:
        """Fuzz a single parameter with stateful session management."""
        session_key = f"{url}:{parameter}"
        session = FuzzSession(target_url=url, parameter=parameter)
        session.session_cookies = self.client.cookies
        self.sessions[session_key] = session

        self._establish_baseline(session)

        # Get CSRF if needed
        resp = self.client.get(url)
        if resp is not None:
            csrf_field, csrf_token = self._extract_csrf(resp)
            if csrf_token:
                session.csrf_field = csrf_field
                session.csrf_token = csrf_token

        # Get payloads
        if not categories:
            categories = list(FUZZ_PAYLOADS.keys())
        payloads: List[Tuple[str, str]] = []
        for cat in categories:
            for p in FUZZ_PAYLOADS.get(cat, []):
                payloads.append((cat, p))

        limit = max_payloads if max_payloads > 0 else self.config.max_fuzz_per_param
        payloads = payloads[:limit]

        for cat, payload in payloads:
            result = self._send_fuzz(session, method, payload, cat, extra_data)
            session.results.append(result)
            session.total_sent += 1
            if result.interesting:
                session.interesting_count += 1

            # Refresh CSRF every 10 requests
            if session.csrf_token and session.total_sent % 10 == 0:
                self._refresh_csrf(session)

        return session

    def _send_fuzz(
        self,
        session: FuzzSession,
        method: str,
        payload: str,
        category: str,
        extra_data: Optional[Dict[str, str]] = None,
    ) -> FuzzResult:
        data = dict(extra_data or {})
        data[session.parameter] = payload
        if session.csrf_field and session.csrf_token:
            data[session.csrf_field] = session.csrf_token

        start = time.time()
        if method.upper() == "GET":
            query = urlencode(data)
            target = f"{session.target_url}?{query}" if "?" not in session.target_url else f"{session.target_url}&{query}"
            resp = self.client.get(target)
        else:
            resp = self.client.post(session.target_url, data=data)
        elapsed = time.time() - start

        result = FuzzResult(payload=payload, category=category)
        if resp is None:
            result.notes = "No response (connection error/timeout)"
            result.interesting = True
            return result

        result.response_code = resp.status_code
        result.response_time = round(elapsed, 4)
        result.response_length = len(resp.content)

        # Analyze for anomalies
        anomalies = self.engine.analyze_response(
            response_body=resp.text,
            response_headers=str(resp.headers),
            response_code=resp.status_code,
            response_time=elapsed,
            baseline_time=session.baseline_time,
        )
        result.anomalies = anomalies

        # Determine if interesting
        if anomalies:
            result.interesting = True
            result.notes = f"{len(anomalies)} anomalies detected"
        elif resp.status_code >= 500:
            result.interesting = True
            result.notes = f"Server error {resp.status_code}"
        elif abs(result.response_length - session.baseline_length) > session.baseline_length * 0.5:
            result.interesting = True
            result.notes = f"Length deviation: {result.response_length} vs baseline {session.baseline_length}"
        elif session.baseline_time > 0 and elapsed > session.baseline_time * 3:
            result.interesting = True
            result.notes = f"Time anomaly: {elapsed:.2f}s vs baseline {session.baseline_time:.2f}s"

        return result


# ── AIReasoningLayer ─────────────────────────────────────────────────────────

class AIReasoningLayer:
    """Heuristic-based decision engine for choosing next attack actions."""

    TECH_VULN_MAP = {
        "WordPress": ["xss", "path_traversal", "command_injection"],
        "Drupal": ["xss", "deserialization", "command_injection"],
        "Django": ["template_injection", "command_injection", "ssrf"],
        "Flask": ["template_injection", "ssrf", "command_injection"],
        "Laravel": ["deserialization", "command_injection", "ssrf"],
        "Spring": ["deserialization", "ssrf", "template_injection"],
        "Express": ["template_injection", "ssrf", "command_injection"],
        "Rails": ["deserialization", "command_injection", "ssrf"],
        "GraphQL": ["command_injection", "ssrf", "xss"],
    }

    PARAM_CATEGORY_MAP = {
        r"(?:url|link|redirect|goto|return|next|ref|src)": ["ssrf", "path_traversal"],
        r"(?:file|path|doc|page|dir|template|include)": ["path_traversal", "template_injection"],
        r"(?:cmd|exec|command|run|shell|ping)": ["command_injection"],
        r"(?:query|search|q|keyword|term|filter|sort|order)": ["xss", "command_injection", "template_injection"],
        r"(?:id|uid|user_id|item|num|count|qty|price|amount)": ["integer_overflow", "command_injection"],
        r"(?:name|title|desc|comment|body|text|content|message)": ["xss", "template_injection"],
        r"(?:xml|data|payload|body)": ["xxe", "deserialization"],
        r"(?:token|session|cookie|jwt|auth)": ["header_injection", "deserialization"],
    }

    def __init__(self, state: AttackState):
        self.state = state

    def decide_next_action(self) -> Dict[str, Any]:
        """Decide the next best action based on current attack state."""
        untested = [
            ep for ep in self.state.endpoints.values()
            if not ep.tested and ep.interest_score > 0
        ]
        if not untested:
            return {"action": "complete", "reason": "All endpoints tested"}

        untested.sort(key=lambda e: e.interest_score, reverse=True)
        target = untested[0]

        categories = self._select_categories(target)
        method = "POST" if "POST" in target.methods else "GET"
        params_to_test = [p for p in target.params if f"{target.url}:{p}" not in self.state.tested_params]

        if not params_to_test and target.has_form:
            params_to_test = [f["name"] for f in target.form_fields if f.get("name")]

        if not params_to_test:
            params_to_test = target.params[:3] if target.params else []

        pivot = self._check_pivot()

        return {
            "action": "fuzz" if params_to_test else "probe",
            "target": target.to_dict(),
            "parameters": params_to_test[:5],
            "categories": categories,
            "method": method,
            "reason": self._explain_decision(target, categories),
            "pivot": pivot,
            "priority": target.interest_score,
        }

    def _select_categories(self, ep: EndpointInfo) -> List[str]:
        cats: List[str] = []
        for tech in self.state.tech_stack:
            for known_tech, tech_cats in self.TECH_VULN_MAP.items():
                if known_tech.lower() in tech.lower():
                    cats.extend(tech_cats)

        for param in ep.params:
            for pattern, param_cats in self.PARAM_CATEGORY_MAP.items():
                if re.search(pattern, param, re.I):
                    cats.extend(param_cats)

        if not cats:
            cats = ["xss", "command_injection", "template_injection", "path_traversal"]

        seen: Set[str] = set()
        unique: List[str] = []
        for c in cats:
            if c not in seen:
                seen.add(c)
                unique.append(c)
        return unique[:6]

    def _check_pivot(self) -> Optional[Dict[str, Any]]:
        for anomaly in self.state.anomalies:
            if anomaly.category == "injection_signal":
                return {"type": "escalate", "reason": f"Confirmed injection: {anomaly.indicator}", "target_categories": ["command_injection", "deserialization"]}
            if anomaly.category == "auth_leak":
                return {"type": "credential_test", "reason": f"Credentials found: {anomaly.indicator}"}
            if anomaly.category == "memory_address":
                return {"type": "buffer_test", "reason": "Memory leak detected — try buffer overflow", "target_categories": ["buffer_overflow"]}
        return None

    def _explain_decision(self, ep: EndpointInfo, cats: List[str]) -> str:
        reasons = []
        if ep.has_form:
            reasons.append("has input forms")
        if ep.params:
            reasons.append(f"{len(ep.params)} parameters")
        if "POST" in ep.methods:
            reasons.append("accepts POST")
        url_lower = ep.url.lower()
        for pattern, label in TargetMapper.HIGH_VALUE_PATTERNS:
            if re.search(pattern, url_lower):
                reasons.append(f"matches {label}")
                break
        base = f"Score {ep.interest_score}"
        if reasons:
            base += f" — {', '.join(reasons)}"
        base += f" → testing [{', '.join(cats[:3])}]"
        return base

    def update_with_results(self, fuzz_session: FuzzSession) -> None:
        for result in fuzz_session.results:
            if result.interesting:
                self.state.findings.append(result.to_dict())
            self.state.anomalies.extend(result.anomalies)
        key = f"{fuzz_session.target_url}:{fuzz_session.parameter}"
        self.state.tested_params.add(key)


# ── ParallelExecutor ─────────────────────────────────────────────────────────

class ParallelExecutor:
    """Concurrent request engine for speed and race condition testing."""

    def __init__(self, client: HttpClient, config: Optional[ScanConfig] = None):
        self.client = client
        self.config = config or ScanConfig()

    def race_test(
        self,
        url: str,
        method: str = "POST",
        data: Optional[Dict[str, str]] = None,
        count: int = 20,
    ) -> Dict[str, Any]:
        """Send N identical concurrent requests to test for race conditions (TOCTOU)."""
        results: List[Dict[str, Any]] = []
        barrier = threading.Barrier(min(count, self.config.concurrency))

        def _fire(idx: int) -> Dict[str, Any]:
            try:
                barrier.wait(timeout=5)
            except threading.BrokenBarrierError:
                pass
            start = time.time()
            if method.upper() == "GET":
                resp = self.client.get(url)
            else:
                resp = self.client.post(url, data=data)
            elapsed = time.time() - start
            if resp is not None:
                return {
                    "index": idx, "status": resp.status_code,
                    "length": len(resp.content), "time": round(elapsed, 4),
                    "body_hash": hashlib.md5(resp.content).hexdigest(),
                }
            return {"index": idx, "status": 0, "length": 0, "time": round(elapsed, 4), "body_hash": "error"}

        with ThreadPoolExecutor(max_workers=self.config.concurrency) as pool:
            futures = {pool.submit(_fire, i): i for i in range(count)}
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    results.append({"index": futures[future], "error": str(e)})

        results.sort(key=lambda r: r.get("index", 0))

        # Analyze for race condition signals
        statuses = [r.get("status", 0) for r in results]
        hashes = [r.get("body_hash", "") for r in results if r.get("body_hash")]
        unique_statuses = set(statuses)
        unique_hashes = set(hashes)

        race_detected = len(unique_statuses) > 1 or len(unique_hashes) > 1

        return {
            "url": url,
            "total_requests": count,
            "results": results,
            "race_detected": race_detected,
            "unique_statuses": list(unique_statuses),
            "unique_response_hashes": len(unique_hashes),
            "analysis": (
                f"RACE CONDITION LIKELY — {len(unique_statuses)} different status codes, "
                f"{len(unique_hashes)} unique response bodies"
                if race_detected else
                "No race condition signals — all responses identical"
            ),
        }

    def parallel_fuzz(
        self,
        fuzzer: 'StatefulFuzzer',
        targets: List[Dict[str, Any]],
    ) -> List[FuzzSession]:
        """Fuzz multiple endpoints/parameters concurrently."""
        sessions: List[FuzzSession] = []

        def _fuzz_target(target: Dict[str, Any]) -> FuzzSession:
            return fuzzer.fuzz_parameter(
                url=target["url"],
                parameter=target["parameter"],
                categories=target.get("categories"),
                method=target.get("method", "GET"),
                extra_data=target.get("extra_data"),
            )

        with ThreadPoolExecutor(max_workers=min(len(targets), self.config.concurrency)) as pool:
            futures = {pool.submit(_fuzz_target, t): t for t in targets}
            for future in as_completed(futures):
                try:
                    sessions.append(future.result())
                except Exception as e:
                    logger.warning(f"Parallel fuzz error: {e}")

        return sessions


# ── ActiveScanLoop ───────────────────────────────────────────────────────────

class ActiveScanLoop:
    """
    Orchestrates the full active attack cycle:
    Crawl → Map → Score → Fuzz → Analyze → Reason → Repeat
    """

    def __init__(self, config: Optional[ScanConfig] = None,
                 on_finding: Optional[Callable[[Dict[str, Any]], None]] = None,
                 on_status: Optional[Callable[[str], None]] = None):
        self.config = config or ScanConfig()
        self.client = HttpClient(self.config)
        self.engine = ZeroDayEngine()
        self.mapper = TargetMapper(self.client, self.config)
        self.fuzzer = StatefulFuzzer(self.client, self.engine, self.config)
        self.executor = ParallelExecutor(self.client, self.config)
        self.state = AttackState()
        self.reasoning = AIReasoningLayer(self.state)
        self.on_finding = on_finding
        self.on_status = on_status
        self._stop_event = threading.Event()

    def _emit_status(self, msg: str) -> None:
        logger.info(msg)
        if self.on_status:
            self.on_status(msg)

    def _emit_finding(self, finding: Dict[str, Any]) -> None:
        self.state.findings.append(finding)
        if self.on_finding:
            self.on_finding(finding)

    def stop(self) -> None:
        self._stop_event.set()

    def run(self, target_url: str) -> Dict[str, Any]:
        """Execute the full active scan loop against a target."""
        self._stop_event.clear()
        self.state.target_base = target_url
        self._emit_status(f"🎯 Starting active scan: {target_url}")

        # Phase 1: Authenticate if needed
        if self.config.auth_url and self.config.auth_username:
            self._emit_status("🔐 Authenticating...")
            self.client.login(
                self.config.auth_url,
                self.config.auth_username,
                self.config.auth_password,
            )

        # Phase 2: Crawl & Map
        self._emit_status("🕷️ Crawling target...")
        endpoints = self.mapper.crawl(target_url)
        self.state.endpoints = endpoints
        self.state.tech_stack = self.mapper.tech_stack
        self._emit_status(f"📍 Mapped {len(endpoints)} endpoints, tech: {', '.join(self.state.tech_stack) or 'unknown'}")

        # Phase 3: Active scan loop
        for iteration in range(self.config.max_iterations):
            if self._stop_event.is_set():
                self._emit_status("⛔ Scan stopped by user")
                break

            self.state.iteration = iteration + 1
            decision = self.reasoning.decide_next_action()

            if decision["action"] == "complete":
                self._emit_status(f"✅ Scan complete: {decision['reason']}")
                break

            self._emit_status(
                f"🔄 Iteration {iteration + 1}/{self.config.max_iterations} — "
                f"{decision['reason']}"
            )

            target_info = decision.get("target", {})
            params = decision.get("parameters", [])
            categories = decision.get("categories", [])
            method = decision.get("method", "GET")

            if decision["action"] == "fuzz" and params:
                for param in params:
                    if self._stop_event.is_set():
                        break
                    self._emit_status(f"  💉 Fuzzing {target_info.get('url', '?')} → {param}")
                    fuzz_session = self.fuzzer.fuzz_parameter(
                        url=target_info["url"],
                        parameter=param,
                        categories=categories,
                        method=method,
                    )
                    self.reasoning.update_with_results(fuzz_session)

                    if fuzz_session.interesting_count > 0:
                        self._emit_finding({
                            "title": f"Fuzzing anomalies on {param}",
                            "url": target_info["url"],
                            "parameter": param,
                            "interesting_count": fuzz_session.interesting_count,
                            "total_sent": fuzz_session.total_sent,
                            "details": [r.to_dict() for r in fuzz_session.results if r.interesting],
                        })
            else:
                # Probe: just fetch and analyze
                resp = self.client.get(target_info.get("url", target_url))
                if resp is not None:
                    anomalies = self.engine.analyze_response(
                        resp.text, str(resp.headers), resp.status_code,
                    )
                    self.state.anomalies.extend(anomalies)

            # Mark endpoint tested
            ep_url = target_info.get("url", "")
            if ep_url in self.state.endpoints:
                self.state.endpoints[ep_url].tested = True

            # Handle pivots
            pivot = decision.get("pivot")
            if pivot and pivot.get("type") == "escalate":
                self._emit_status(f"  🔀 Pivot: {pivot['reason']}")

        # Phase 4: Build exploit chains
        self._emit_status("⛓️ Analyzing exploit chains...")
        chains = self.engine.build_exploit_chains(self.state.findings)

        # Build final report
        report = {
            "target": target_url,
            "endpoints_mapped": len(self.state.endpoints),
            "endpoints_tested": sum(1 for e in self.state.endpoints.values() if e.tested),
            "tech_stack": list(self.state.tech_stack),
            "total_findings": len(self.state.findings),
            "total_anomalies": len(self.state.anomalies),
            "exploit_chains": len(chains),
            "iterations": self.state.iteration,
            "findings": self.state.findings,
            "chains": [c.to_dict() for c in chains],
            "endpoint_map": {k: v.to_dict() for k, v in self.state.endpoints.items()},
        }
        self._emit_status(
            f"🏁 Active scan complete — {report['total_findings']} findings, "
            f"{report['exploit_chains']} exploit chains"
        )
        return report

    def format_report(self, report: Dict[str, Any]) -> str:
        """Format the active scan report as markdown."""
        lines = [
            "# 🔬 Zero-Day Active Scan Report\n",
            f"**Target:** {report['target']}",
            f"**Endpoints Mapped:** {report['endpoints_mapped']}",
            f"**Endpoints Tested:** {report['endpoints_tested']}",
            f"**Technology Stack:** {', '.join(report.get('tech_stack', [])) or 'Unknown'}",
            f"**Total Findings:** {report['total_findings']}",
            f"**Exploit Chains:** {report['exploit_chains']}",
            f"**Iterations:** {report['iterations']}\n",
        ]

        if report.get("findings"):
            lines.append("## 💥 Findings\n")
            for i, f in enumerate(report["findings"][:20], 1):
                lines.append(f"### {i}. {f.get('title', 'Finding')}")
                lines.append(f"- **URL:** {f.get('url', 'N/A')}")
                lines.append(f"- **Parameter:** {f.get('parameter', 'N/A')}")
                lines.append(f"- **Interesting Responses:** {f.get('interesting_count', 0)}/{f.get('total_sent', 0)}")
                details = f.get("details", [])
                for d in details[:3]:
                    lines.append(f"  - `{d.get('payload', '?')[:60]}` → {d.get('notes', '')}")
                lines.append("")

        if report.get("chains"):
            chain_objects = []
            for c in report["chains"]:
                chain_objects.append(ExploitChain(**c))
            lines.append(self.engine.format_chains_report(chain_objects))

        return "\n".join(lines)
