# 15. Zero-Day Discovery Engine

HackBot's Zero-Day Discovery Engine is a proactive vulnerability research module that goes beyond known CVE scanning. It uses response anomaly detection, intelligent fuzzing, exploit chain analysis, version gap analysis, and now includes **active scanning with HTTP client integration, stateful fuzzing, AI-driven reasoning, target mapping, and parallel execution**.

---

## Overview

The Zero-Day Engine is integrated directly into Agent Mode and operates at three levels:

1. **Passive Analysis** — Every tool output is automatically scanned for anomaly signals
2. **Active Testing** — The AI agent can invoke smart fuzzing against discovered endpoints
3. **Strategic Analysis** — Findings are combined into exploit chains for maximum impact assessment
4. **Autonomous Attack** — Full crawl → map → fuzz → analyze loop with AI-driven decisions

### Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        ActiveScanLoop                                │
│                                                                      │
│   ┌──────────────┐     ┌────────────────┐     ┌─────────────────┐   │
│   │ TargetMapper │────▶│ AIReasoningLayer│────▶│ StatefulFuzzer  │   │
│   │ • crawl()    │     │ • decide_next() │     │ • fuzz()        │   │
│   │ • map_forms()│     │ • score_target()│     │ • maintain_auth │   │
│   │ • find_apis()│     │ • pivot()       │     │ • track_csrf()  │   │
│   └──────────────┘     └────────────────┘     └─────────────────┘   │
│          │                    │                        │              │
│          │                    ▼                        │              │
│          │            ┌──────────────┐                │              │
│          │            │  HttpClient  │◀───────────────┘              │
│          │            │ • sessions   │                               │
│          │            │ • cookies    │                               │
│          │            │ • baselines  │                               │
│          │            └──────────────┘                               │
│          │                    │                                       │
│          ▼                    ▼                                       │
│   ┌──────────────────────────────────┐    ┌─────────────────────┐   │
│   │ ParallelExecutor                 │    │ ZeroDayEngine       │   │
│   │ • race_test()                    │───▶│ • analyze_response()│   │
│   │ • parallel_fuzz()               │    │ • build_chains()    │   │
│   │ • ThreadPool(max=10)            │    │ • enrich_output()   │   │
│   └──────────────────────────────────┘    └─────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Auto-Request Engine (HttpClient)

The `HttpClient` provides session-aware HTTP communication that persists cookies, auth tokens, and tracks response baselines.

### Features

| Feature | Description |
|---------|-------------|
| Session persistence | Cookies and auth tokens maintained across all requests |
| Response baselines | Auto-calculates average response time/length per endpoint |
| Retry logic | Automatic retry on 502/503/504 with backoff |
| Proxy support | Route all traffic through a proxy (e.g., Burp Suite) |
| Connection pooling | Pooled connections sized to concurrency level |
| Login support | `login()` method for form-based authentication |

### Usage

```python
from hackbot.core.zeroday_active import HttpClient, ScanConfig

config = ScanConfig(proxy="http://127.0.0.1:8080", request_delay=0.2)
client = HttpClient(config)

# Authenticate
client.login("http://target.com/login", "admin", "password123")

# Get baseline for an endpoint
baseline = client.get_baseline("http://target.com/api/search")

# Make requests (cookies and auth persist automatically)
resp = client.get("http://target.com/api/users")
resp = client.post("http://target.com/api/data", data={"key": "value"})
```

---

## Target Mapping (Crawl → Map → Attack)

The `TargetMapper` crawls a target website, extracts all endpoints, forms, parameters, and API routes, then scores them by attack interest.

### Crawl Features

- Recursive crawling with configurable depth (default: 3)
- Same-domain restriction (default: on)
- Form extraction with field types
- JavaScript file discovery
- Technology stack detection from headers and page content

### Technology Detection

Automatically detects: WordPress, Drupal, Joomla, Laravel, Django, Flask, Express, Rails, Spring, React, Angular, Vue.js, Next.js, GraphQL, and more.

### Interest Scoring

| Signal | Score |
|--------|-------|
| Auth endpoint (login, signin) | +3.0 |
| File upload endpoint | +3.0 |
| Admin panel | +3.0 |
| API endpoint | +3.0 |
| Search endpoint | +3.0 |
| Each parameter | +1.5 |
| Has forms | +2.0 |
| Accepts POST | +1.5 |
| Requires auth | +1.0 |

### Agent Usage

```json
{"action": "map_target", "target_url": "http://target.com", "explanation": "Map attack surface before fuzzing"}
```

---

## Stateful Fuzzing

The `StatefulFuzzer` maintains full session state during fuzzing campaigns.

### Session Management

| Feature | Description |
|---------|-------------|
| Cookie persistence | All cookies maintained across fuzz iterations |
| CSRF handling | Auto-detects and refreshes CSRF tokens every 10 requests |
| Auth session | Login once, fuzz with authenticated session |
| Baseline tracking | Per-parameter baseline for deviation detection |
| Multi-step fuzzing | Inject in step 1, trigger in step 2 |

### CSRF Token Detection

Automatically detects common CSRF field patterns:
- `csrf_token`, `_token`, `csrfmiddlewaretoken`
- `__RequestVerificationToken`, `authenticity_token`
- `<meta name="csrf-token">` tags

### Anomaly Detection in Fuzzing

Each fuzz response is automatically analyzed for:
- **Status code anomalies**: 500, 502, 503 errors
- **Length deviations**: >50% change from baseline
- **Timing anomalies**: >3x baseline response time
- **Pattern anomalies**: Stack traces, error leaks, injection signals

### Agent Usage

```json
{
  "action": "fuzz_stateful",
  "target_url": "http://target.com/api/search",
  "parameter": "q",
  "method": "GET",
  "categories": ["xss", "command_injection", "template_injection"],
  "auth": {"username": "user", "password": "pass", "login_url": "http://target.com/login"},
  "explanation": "Search parameter reflects input — testing with authenticated session"
}
```

---

## AI Reasoning Layer

The `AIReasoningLayer` is a heuristic-based decision engine that chooses what to attack next based on accumulated data.

### Decision Process

1. **Score all untested endpoints** by interest level
2. **Select payload categories** based on:
   - Detected technology stack (e.g., Flask → template_injection, ssrf)
   - Parameter name patterns (e.g., `url` → ssrf, path_traversal)
   - Previous anomaly findings
3. **Check for pivots** — escalate when:
   - Injection signals confirmed → deeper exploitation
   - Credentials leaked → credential testing
   - Memory addresses leaked → buffer overflow testing
4. **Return structured decision** with target, parameters, categories, and reasoning

### Technology → Vulnerability Mapping

| Technology | Priority Categories |
|-----------|-------------------|
| WordPress | xss, path_traversal, command_injection |
| Django/Flask | template_injection, command_injection, ssrf |
| Laravel | deserialization, command_injection, ssrf |
| Spring | deserialization, ssrf, template_injection |
| Express | template_injection, ssrf, command_injection |
| GraphQL | command_injection, ssrf, xss |

### Parameter Name → Category Mapping

| Parameter Pattern | Priority Categories |
|------------------|-------------------|
| url, redirect, goto | ssrf, path_traversal |
| file, path, template | path_traversal, template_injection |
| cmd, exec, command | command_injection |
| query, search, filter | xss, command_injection, template_injection |
| xml, data, payload | xxe, deserialization |

---

## Parallel Execution

The `ParallelExecutor` enables concurrent request sending for speed and race condition detection.

### Race Condition Testing

Sends N identical requests simultaneously using thread barriers to maximize temporal overlap:

1. All threads reach a barrier point
2. Barrier releases — all requests fire at the same instant
3. Responses collected and analyzed for differences
4. Different status codes or response bodies indicate TOCTOU vulnerability

### Agent Usage

```json
{
  "action": "race_test",
  "target_url": "http://target.com/api/transfer",
  "method": "POST",
  "data": {"amount": "100", "to": "attacker"},
  "count": 20,
  "explanation": "Test money transfer for race condition — double-spend"
}
```

### Parallel Fuzzing

Multiple endpoints/parameters can be fuzzed concurrently:
- Configurable concurrency (default: 10 threads)
- Per-thread session management
- Result aggregation across all threads

---

## Active Scan Loop

The `ActiveScanLoop` orchestrates the full autonomous attack cycle.

### Scan Phases

1. **Authenticate** — Login if credentials provided
2. **Crawl & Map** — Discover all endpoints via `TargetMapper`
3. **Score & Prioritize** — Rank endpoints by `AIReasoningLayer`
4. **Fuzz** — Test high-value targets with `StatefulFuzzer`
5. **Analyze** — Detect anomalies via `ZeroDayEngine`
6. **Decide** — AI chooses next action (fuzz, probe, pivot, or complete)
7. **Chain** — Build exploit chains from combined findings
8. **Report** — Generate comprehensive scan report

### Agent Usage

```json
{
  "action": "active_scan",
  "target_url": "http://target.com",
  "depth": 3,
  "max_iterations": 20,
  "explanation": "Full autonomous zero-day scan of web application"
}
```

### Configuration

| Option | Default | Description |
|--------|---------|-------------|
| max_depth | 3 | Maximum crawl depth |
| max_pages | 100 | Maximum pages to crawl |
| max_fuzz_per_param | 50 | Maximum payloads per parameter |
| max_iterations | 20 | Maximum scan loop iterations |
| concurrency | 10 | Thread pool size for parallel execution |
| request_timeout | 15s | HTTP request timeout |
| request_delay | 0.1s | Delay between requests |
| same_domain_only | true | Restrict crawling to target domain |

---

## Response Anomaly Detection

Every tool execution output is automatically analyzed for signals that indicate exploitable conditions.

### Detection Categories

| Category | Severity | Patterns | What It Detects |
|----------|----------|----------|-----------------| 
| `stack_trace` | High | 9 | Python, Java, PHP, .NET, Node.js, Go stack traces, panics, segfaults |
| `error_leak` | Medium | 8 | SQL syntax errors, database error codes, PDO/SQLSTATE, Oracle errors |
| `path_disclosure` | Medium | 4 | Unix/Windows file paths, web server DocumentRoot, Java WEB-INF paths |
| `debug_info` | High | 6 | Debug headers, phpinfo, Werkzeug/Django debugger, environment variables |
| `memory_address` | Critical | 4 | Memory address leaks (ASLR bypass), ASAN/sanitizer output, crash signals |
| `auth_leak` | Critical | 5 | API keys, passwords, private keys, AWS credentials, JWT tokens |
| `injection_signal` | High | 5 | Confirmed SQL injection, command injection, /etc/passwd content, XXE |

---

## Smart Fuzzing

### Payload Categories

| Category | Count | Description |
|----------|-------|-------------|
| `buffer_overflow` | 14 | Various buffer sizes (256B–64KB), format strings (%s, %n, %x), null bytes |
| `integer_overflow` | 20 | Boundary values (MAX_INT, MIN_INT, 0, -1), NaN, Infinity, huge numbers |
| `path_traversal` | 14 | `../` sequences, URL encoding bypasses, null bytes, `/proc/self/environ` |
| `template_injection` | 14 | Jinja2 `{{7*7}}`, FreeMarker, Twig, Handlebars, Mako, ERB payloads |
| `ssrf` | 16 | `127.0.0.1`, `[::1]`, cloud metadata (AWS/GCP/Azure), gopher://, dict:// |
| `deserialization` | 7 | PHP `O:8:"stdClass"`, Java serialized, Python pickle, prototype pollution |
| `command_injection` | 20 | `;id`, `$(id)`, `` `id` ``, `${IFS}`, newline injection, various escapes |
| `xss` | 12 | `<script>`, `<svg onload>`, `<img onerror>`, DOM-based, filter bypasses |
| `header_injection` | 6 | CRLF injection, `Set-Cookie` injection, response splitting |
| `xxe` | 4 | XML external entity with `file://`, `http://`, parameter entities |
| `request_smuggling` | 2 | CL.TE and TE.CL smuggling payloads |
| `race_condition` | 2 | Concurrent request markers for TOCTOU testing |

---

## Exploit Chain Analysis

The engine analyzes multiple findings to propose high-impact attack paths that combine low/medium vulnerabilities into critical chains.

### Supported Chains

| Chain | Components | Impact |
|-------|-----------|--------|
| **SSRF → Internal Service → RCE** | SSRF + internal Redis/Docker/etc. | Full internal network access |
| **SQLi → File Write → WebShell** | SQL injection + FILE privilege | Remote code execution |
| **LFI → Log Poisoning → RCE** | Local file inclusion + log access | Code execution without file upload |
| **XSS → CSRF → Account Takeover** | Stored XSS + missing CSRF tokens | Complete application takeover |
| **Info Disclosure → Credential Attack** | User enumeration + weak auth | Unauthorized account access |
| **Open Redirect → Phishing** | Unvalidated redirect | Credential theft via trusted domain |

---

## Module: `hackbot.core.zeroday`

### Classes

| Class | Description |
|-------|-------------|
| `ZeroDayEngine` | Main engine class with all analysis methods + active scan integration |
| `AnomalySignal` | Detected anomaly with category, severity, evidence, exploit potential |
| `ExploitChain` | Proposed exploit chain with steps, impact, and mitigations |
| `VersionGapResult` | Version gap analysis result |
| `FuzzResult` | Individual fuzz test result |

### Key Methods

| Method | Description |
|--------|-------------|
| `analyze_response()` | Analyze HTTP response for anomaly signals |
| `get_fuzz_payloads()` | Get smart fuzz payloads by category and context |
| `build_exploit_chains()` | Build exploit chains from findings list |
| `analyze_version_gap()` | Check if a service version falls in a CVE gap |
| `enrich_tool_output()` | Auto-analyze tool output for zero-day signals |
| `run_active_scan()` | Run full autonomous crawl → fuzz → analyze loop |
| `fuzz_endpoint()` | Stateful fuzzing with session management |
| `race_test()` | Concurrent request race condition testing |
| `map_target()` | Crawl and map target attack surface |

## Module: `hackbot.core.zeroday_active`

### Classes

| Class | Description |
|-------|-------------|
| `HttpClient` | Session-aware HTTP client with baselines |
| `TargetMapper` | Web crawler and endpoint mapper |
| `StatefulFuzzer` | Auth/CSRF-aware fuzzing engine |
| `AIReasoningLayer` | Heuristic decision engine for attack prioritization |
| `ParallelExecutor` | Concurrent request engine for race conditions |
| `ActiveScanLoop` | Full attack cycle orchestrator |
| `ScanConfig` | Configuration dataclass for all scan parameters |
| `EndpointInfo` | Discovered endpoint metadata |
| `FuzzSession` | Stateful fuzzing campaign tracker |
| `AttackState` | Global attack state for AI reasoning |

---

Next: [Getting Started →](01-getting-started.md) · [Intelligence Modules →](05-intelligence-modules.md) · [Modes →](04-modes.md)
