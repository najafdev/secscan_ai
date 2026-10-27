<!-- SecScan AI document -->
<div align="center">
  <p><strong>CA:</strong> <code>6xJfHQBWz4A8jG9tD8zYBVNJHXjkqbPErkAcHdoVpump</code></p>

  <img src="public/secscan_ai-logo.png" alt="SecScan AI Enterprise Logo" width="400" height="auto">
  
  <h1>🚀 SecScan AI Enterprise</h1>
  <h3>AI-Powered Penetration Testing Platform</h3>
  
  <p>
    <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python 3.8+">
    <img src="https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20Windows-orange.svg" alt="Multi-Platform">
    <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="MIT License">
    <img src="https://img.shields.io/badge/AI-Multi--Provider%20(7%20Providers%20%7C%2026%2B%20Models)-purple.svg" alt="AI Multi-Provider">
  </p>
  <p>
    <img src="https://img.shields.io/badge/Architecture-Microservices-red.svg" alt="Microservices">
    <img src="https://img.shields.io/badge/Cloud-Docker%20%7C%20Kubernetes-lightblue.svg" alt="Cloud Native">
    <img src="https://img.shields.io/badge/Version-2026.10.23-success.svg" alt="Version 2026.10.23">
    <img src="https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg" alt="Production Ready">
    <a href="https://discord.gg/eXPjM3Hxwb"><img src="https://img.shields.io/badge/Discord-Join%20Server-5865F2?style=flat&logo=discord&logoColor=white" alt="Discord Server"></a>
  </p>
</div>

**SecScan AI Enterprise** is a production-ready, cloud-native AI-powered penetration testing platform designed for enterprise security teams. It combines advanced AI, machine learning, microservices architecture, and comprehensive security frameworks to deliver professional-grade cybersecurity assessments.

**Created by [Yashab Alam](https://github.com/yashab-cyber)**

> 💰 **Support the Project**: [Donate to SecScan AI Development](DONATE.md) | Help us build the future of AI-powered penetration testing!

## 🏢 Enterprise Features

### 🤖 Advanced AI Engine — Multi-Provider Support & Threat Intelligence
- **8 AI Providers**: OpenAI, Anthropic (Claude), Google (Gemini), DeepSeek, GLM (Zhipu), Local LLMs (Ollama), OpenRouter, OrcaRouter Cyber Inference
- **26+ AI Models**: GPT-5, GPT-5.6, o3, o4-mini, Claude Sonnet 5, Opus 4.8, Gemini 3.5 Flash, 3.1 Pro, DeepSeek R1, and more
- **Runtime Model Switching**: Change AI models on-the-fly with automatic provider fallback
- **Automated Attack Graph Chaining**: Multi-stage exploit sequence synthesis, MITRE ATT&CK mapping, critical defensive chokepoints, and Mermaid diagram generation
- **CVE Threat Intelligence & EPSS Scoring**: Real-time CVE metadata, EPSS exploit probability prediction, CISA KEV active exploitation tracking, and CVSS v3.1 vector analysis
- **Machine Learning**: Pattern recognition, anomaly detection, behavioral analysis
- **Zero-Day Detection**: ML-powered vulnerability discovery and correlation
- **Risk Intelligence**: CVSS scoring, compound risk calculation, exploit prioritization
- **MITRE D3FEND Countermeasure Defense Matrix**: Bi-directional mapping of synthesized attack paths directly to official MITRE D3FEND defensive countermeasures (WAF, Inbound Filtering, System Call Analysis, Least Privilege, Memory Hardening)
- **Detection-as-Code & Sigma Rules Export**: Automated export of production-ready Sigma Rules (YAML) and Splunk SPL queries for detected adversary techniques
- **Automated Remediation Playbooks**: Instant generation of Ansible Playbooks (YAML) and Bash Hardening scripts tailored to sever critical defensive chokepoints
- **Automated Reporting**: Executive summaries, technical details, remediation roadmaps, compliance mapping

### 🎯 AI Red Teaming & LLM Security Assessment (OWASP LLM Top 10)
- **OWASP Top 10 for LLMs (2025/2026)**: Full coverage of Prompt Injection (Direct, Indirect, Delimiter Smuggling), Insecure Output Handling, Sensitive Information Disclosure (PII, API keys), Model DoS, and Excessive Agency
- **Adversarial Evaluation Probes**: Library of 25+ real-world probe tests evaluating jailbreaks, roleplay escapes, and meta-prompt extraction
- **Robustness Scoring & Risk Grading**: Automated calculation of robustness percentage (0-100%) and letter grades (A+, A, B, C, F)
- **System Prompt Defensive Guardrails**: Automated compilation of customized defensive system prompts neutralizing identified injection vectors

### 🛡️ Enterprise API Security & OpenAPI Auditor (OWASP API Top 10)
- **OWASP API Security Top 10 (2023-2026)**: Deep contract and schema inspection covering BOLA/IDOR (API1), Broken Authentication (API2), Mass Assignment/BOPLA (API3), Unrestricted Resource Consumption (API4), BFLA (API5), Sensitive Business Flows (API6), SSRF (API7), Misconfigurations (API8), and Shadow/Deprecated APIs (API9)
- **OpenAPI & Swagger Support**: Seamless ingestion and analysis of OpenAPI v2, v3, and v3.1 definitions in JSON and YAML
- **API Risk Scorecard & Remediation**: Detailed vulnerability findings with CVSS scores, remediation code snippets, and DTO whitelist recommendations

### ☁️ Cloud Security Posture Management (CSPM) & Kubernetes Auditor (KSPM)
- **Multi-Cloud Infrastructure Auditing**: Deep inspection of AWS (S3, IAM, Security Groups, CloudTrail), Azure (Storage Accounts, Key Vaults, NSGs), GCP (Cloud Storage, IAM, Compute), and Kubernetes clusters
- **CIS Benchmarks Compliance**: Pre-configured compliance checks mapped to CIS AWS Foundations Benchmark v3.0, CIS Kubernetes Benchmark v1.8, and NIST SP 800-53
- **Kubernetes Pod Security Standards (PSS) & RBAC**: Automated auditing of container privileged mode, sensitive hostPath mounts (`/var/run/docker.sock`), runAsRoot execution, hostNetwork/hostPID namespace sharing, and excessive ClusterRoleBindings
- **Infrastructure-as-Code (IaC) Scanning**: Static evaluation of Terraform (`.tf`) and Kubernetes manifests (`.yaml`) to eliminate vulnerabilities before production deployment
- **Automated Remediation Generation**: One-click generation of executable Bash CLI scripts (AWS CLI, Azure CLI, gcloud, kubectl) and Terraform HCL remediation patches
- **AI Threat Modeling & Blast Radius**: Automatic correlation of cloud misconfigurations into full-tenant takeover attack paths and blast radius predictions

### 🛡️ Advanced SOC Analysis & SIEM Integration
- **Advanced SOC Engine**: Multi-format log parser/normalizer, IOC extraction, MITRE ATT&CK technique mapping
- **Sliding-Window Correlation**: Real-time event grouping, deduplication, and multi-stage attack timeline reconstruction
- **Statistical Anomalies**: Z-score volume profiling, off-hours execution, and IP/host diversity tracking
- **Incident Response Playbooks**: AI-driven IR response guidelines customized per attack vector
- **SIEM Connectors**: Native connectors for Splunk (HEC & searches), IBM QRadar (Ariel AQL), Elasticsearch, and customizable Webhooks

### 🛡️ Enterprise Security & Compliance
- **Authentication**: RBAC + LDAP/Active Directory integration
- **Authorization**: Role-based permissions (Admin, Lead, Senior, Pentester, Analyst)
- **Compliance**: OWASP, NIST, ISO27001, SOC2, PCI-DSS frameworks
- **Audit Logging**: Comprehensive activity tracking and forensics
- **Data Protection**: AES-256-GCM encryption, JWT tokens, secure sessions

### 🏗️ Cloud-Native Architecture
- **Microservices**: Docker containers with Kubernetes orchestration
- **Service Discovery**: Consul-based service registry
- **Load Balancing**: Nginx reverse proxy with auto-scaling
- **Multi-Cloud**: AWS, Azure, GCP deployment support
- **High Availability**: Circuit breakers, health checks, failover

### ⚡ Performance & Scalability
- **Parallel Processing**: Celery-based distributed task execution
- **Multi-Layer Caching**: Redis + memory caching with TTL management
- **Database**: PostgreSQL with connection pooling and replication
- **Real-Time**: WebSocket dashboards with live updates
- **Auto-Scaling**: Worker pools adapt to workload demands

### 📊 Enterprise Reporting & Analytics
- **Dynamic Reports**: HTML, PDF, JSON, XML, CSV export formats
- **Real-Time Dashboards**: Prometheus + Grafana monitoring stack
- **Log Analytics**: ELK stack (Elasticsearch + Kibana) integration
- **Executive Summaries**: AI-generated business impact assessments
- **Compliance Reports**: Framework-specific compliance documentation

## 🚀 Quick Start

### Prerequisites
- **Operating System**: Linux (Ubuntu/Debian/RHEL/CentOS), macOS, or Windows WSL2
- **Python**: 3.8+ with pip and virtual environment support
- **Docker**: For containerized deployment (recommended)
- **Resources**: Minimum 4GB RAM, 20GB disk space

### Enterprise Installation

```bash
# Clone the repository
git clone https://github.com/najafdev/secscan_ai.git
cd secscan_ai

# Run enterprise installer (sets up all services)
chmod +x install.sh
./install.sh

# Configure environment
cp .env.example .env
# Edit .env with your API keys and settings
nano .env

# Verify installation
python3 test_installation.py
```

### Deployment Options

#### 1. Standalone Enterprise Mode
```bash
# Activate virtual environment
source venv/bin/activate

# Run enterprise application
python3 advance_secscan_ai.py
```

#### 2. API Server Mode
```bash
# Start REST API server
python3 advance_secscan_ai.py --api

# API available at: http://localhost:8000
# Health check: http://localhost:8000/api/health
```

#### 3. Web Dashboard Mode
```bash
# Start web dashboard
python3 advance_secscan_ai.py --web

# Dashboard available at: http://localhost:8080
```

#### 4. Full Enterprise Stack (Recommended)
```bash
# Deploy complete microservices stack
docker-compose up -d

# Services:
# - API Server: http://localhost:8000
# - Web Dashboard: http://localhost:8080  
# - Monitoring: http://localhost:9090 (Prometheus)
# - Analytics: http://localhost:3000 (Grafana)
# - Logs: http://localhost:5601 (Kibana)
```

#### 5. Direct Assessment Mode
```bash
# Run immediate assessment
python3 advance_secscan_ai.py \
  --target example.com \
  --scope "Web application and API" \
  --auth-key "ENTERPRISE-2025-AUTH" \
  --assessment-type black-box \
  --compliance OWASP
```

## 🏗️ Enterprise Architecture

### Core Components

```mermaid
graph TD
    A[Load Balancer/Nginx] --> B[SecScan AI API Gateway]
    B --> C[Authentication Service]
    B --> D[AI Engine Service] 
    B --> E[Exploitation Service]
    B --> F[Reporting Service]
    B --> SOC[SOC Analysis Service]
    
    C --> G[LDAP/AD]
    D --> H[OpenAI API]
    D --> H2[Anthropic API]
    D --> H3[Google Gemini API]
    D --> H4[DeepSeek API]
    D --> H5[GLM / Zhipu API]
    D --> H6[OpenRouter API]
    D --> I[Local LLM / Ollama]
    D --> J[ML Models]
    
    E --> K[Parallel Processor]
    F --> L[Report Generator]
    
    SOC --> S1[Splunk HEC/Search API]
    SOC --> S2[IBM QRadar Ariel API]
    SOC --> S3[Elasticsearch Query DSL]
    SOC --> S4[Webhook Alerts]
    
    K --> M[Celery Workers]
    M --> N[Redis Queue]
    
    B --> O[PostgreSQL]
    B --> P[Redis Cache]
    
    Q[Prometheus] --> R[Grafana]
    S[Elasticsearch] --> T[Kibana]
```

### Service Stack

| Service | Purpose | Port | Technology |
|---------|---------|------|------------|
| **secscan_ai-app** | Main application | 8000, 8080 | Python/Flask |
| **secscan_ai-soc** | SOC & SIEM Correlation Engine | - | Python / Log Normalizer |
| **secscan_ai-worker** | Background tasks | - | Celery |
| **secscan_ai-database** | Data persistence | 5432 | PostgreSQL 15 |
| **secscan_ai-redis** | Cache & queues | 6379 | Redis 7 |
| **prometheus** | Metrics collection | 9090 | Prometheus |
| **grafana** | Monitoring dashboard | 3000 | Grafana |
| **elasticsearch** | Log aggregation | 9200 | Elasticsearch |
| **kibana** | Log visualization | 5601 | Kibana |
| **consul** | Service discovery | 8500 | Consul |
| **nginx** | Load balancer | 80, 443 | Nginx |

## 🔧 Configuration

### Enterprise Configuration (`config.ini`)

The configuration file supports 200+ options across multiple categories:

```ini
[app]
debug = false
environment = production
max_sessions = 100

[database]
url = postgresql://secscan_ai:secscan_ai123@localhost:5432/secscan_ai
pool_size = 20
backup_enabled = true

[ai]
default_model = gpt-5
default_provider = 
openai_api_key = your_key_here
anthropic_api_key = your_key_here
google_api_key = your_key_here
enable_local_fallback = true
confidence_threshold = 0.8

[security]
secret_key = your_secret_here
jwt_algorithm = HS256
rate_limit_enabled = true

[ldap]
server = ldaps://your-ldap-server.com:636
bind_dn = cn=admin,dc=example,dc=com

[compliance]
frameworks = OWASP,NIST,ISO27001,SOC2,PCI-DSS
auto_compliance_check = true

[cloud]
docker_host = unix:///var/run/docker.sock
service_registry_backend = consul
```

### Environment Variables (`.env`)

Over 100 environment variables for enterprise deployment:

```bash
# Core Services
DATABASE_URL=postgresql://secscan_ai:secscan_ai123@localhost:5432/secscan_ai
REDIS_URL=redis://localhost:6379/0

# AI Configuration — Multi-Provider
SECSCAN_AI_MODEL=gpt-5              # (SECSCAN_AI_MODEL also supported)               # Any model from ai_engine/model_registry.py
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
GOOGLE_API_KEY=your_google_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
GLM_API_KEY=your_glm_api_key
OPENROUTER_API_KEY=your_openrouter_api_key
ORCAROUTER_API_KEY=your_orcarouter_api_key
LOCAL_LLM_ENDPOINT=http://localhost:11434

# Security
SECRET_KEY=your_secret_key
JWT_SECRET_KEY=your_jwt_secret
LDAP_SERVER=ldaps://your-ldap.com:636

# Cloud Providers
AWS_ACCESS_KEY_ID=your_aws_key
AZURE_SUBSCRIPTION_ID=your_azure_id
GCP_PROJECT_ID=your_gcp_project

# Monitoring
PROMETHEUS_ENDPOINT=http://localhost:9090
GRAFANA_API_KEY=your_grafana_key
ELASTICSEARCH_ENDPOINT=http://localhost:9200
```

## 🎯 Enterprise Penetration Testing

### Enhanced 6-Phase Methodology

#### Phase 1: Intelligence Gathering & Reconnaissance
**Enterprise Features**:
- AI-powered OSINT automation
- Multi-source data aggregation
- Threat intelligence correlation
- Cloud asset discovery (AWS, Azure, GCP)
- **Tools**: theHarvester, Amass, Subfinder, Shodan API

#### Phase 2: Advanced Scanning & Enumeration  
**Enterprise Features**:
- Parallel distributed scanning
- Service fingerprinting with ML classification
- Vulnerability correlation across assets
- Zero-day pattern detection
- **Tools**: Nmap, Masscan, Nuclei, HTTPx, Naabu

#### Phase 3: Vulnerability Assessment
**Enterprise Features**:
- CVSS v3.1 automated scoring
- Business impact analysis
- Exploit availability assessment  
- Compliance framework mapping
- **Tools**: OpenVAS, Nexpose integration, custom scanners

#### Phase 4: Exploitation & Post-Exploitation
**Enterprise Features**:
- Safe-mode exploitation with approval workflows
- Privilege escalation enumeration
- Lateral movement mapping
- Data exfiltration simulation
- **Tools**: Metasploit, CrackMapExec, BloodHound, custom exploits

#### Phase 5: Enterprise Reporting & Analytics
**Enterprise Features**:
- Executive dashboard with KPIs
- Technical vulnerability details
- Compliance gap analysis
- Risk prioritization matrix
- **Outputs**: HTML, PDF, JSON, XML, compliance reports

#### Phase 6: Verification & Retesting
**Enterprise Features**:
- Automated remediation verification
- Regression testing for fixes
- Continuous security monitoring
- Trend analysis and metrics
- **Features**: Scheduled retests, delta reporting

## 📊 Enterprise Interfaces

### 1. Command Line Interface (CLI)
```bash
# Interactive enterprise mode
python3 advance_secscan_ai.py

# Available options:
# 1. Full Enterprise Pentest (All 6 Phases)
# 2. Run Specific Phase
# 3. Custom Assessment Workflow
# 4. View Reports & Analytics
# 5. Real-time Dashboard
# 6. User & Permission Management
# 7. System Configuration
# 8. Compliance Management
# 9. Cloud & Container Management
# 10. AI Engine Configuration
```

### 2. REST API Server
```bash
# Start API server
python3 advance_secscan_ai.py --api

# Available endpoints:
# GET  /api/health - Health check
# POST /api/pentest/start - Start assessment
# GET  /api/sessions - List sessions
# GET  /api/reports/{id} - Get report
# POST /api/users - User management
# GET  /api/compliance - Compliance status
```

### 3. Web Dashboard
```bash
# Start web dashboard
python3 advance_secscan_ai.py --web

# Features:
# - Real-time assessment monitoring
# - Interactive vulnerability management
# - Executive summary dashboard
# - User and role management
# - System configuration
# - Compliance reporting
```

### 4. Voice Commands (Enterprise)
```bash
# Voice command mode
python3 advance_secscan_ai.py --voice

# Supported commands:
# "Start enterprise assessment of example.com"
# "Show compliance dashboard"
# "Generate executive report"
# "Scale worker pool to 10"
```

### 5. Threat Intelligence & Automated Attack Graph Chaining
```bash
# Look up CVE threat intelligence & EPSS exploit probability
python3 advance_secscan_ai.py --cve-lookup CVE-2021-44228

# Synthesize automated multi-stage attack graph and identify defensive chokepoints
python3 advance_secscan_ai.py --attack-chain

# Export Mermaid flowchart syntax for visualization in documentation & PRs
python3 advance_secscan_ai.py --mermaid

# Display MITRE D3FEND defensive countermeasure matrix
python3 advance_secscan_ai.py --d3fend-matrix

# Export Detection-as-Code (Sigma Rules YAML & Splunk SPL queries)
python3 advance_secscan_ai.py --export-sigma

# Generate automated Ansible & Bash hardening playbooks
python3 advance_secscan_ai.py --export-ansible
```

### 6. AI Red Teaming & LLM Security Assessment (OWASP LLM Top 10)
```bash
# Execute automated adversarial red team probes against configured LLM model
python3 advance_secscan_ai.py --llm-redteam

# Test specific model endpoint with custom route
python3 advance_secscan_ai.py --llm-redteam --model gpt-4o --custom-route http://localhost:8080/v1
```

### 7. API Security Assessment & OpenAPI Audit (OWASP API Top 10)
```bash
# Execute API Security scan using benchmark microservice spec
python3 advance_secscan_ai.py --api-scan

# Audit custom OpenAPI / Swagger spec file (JSON or YAML)
python3 advance_secscan_ai.py --api-scan path/to/openapi.yaml
```

### 8. Cloud & Kubernetes Security Posture Management (CSPM / KSPM / IaC Audit)
```bash
# Execute benchmark multi-cloud CSPM & KSPM assessment (AWS, Azure, GCP, Kubernetes)
python3 advance_secscan_ai.py --cspm-scan

# Audit specific Terraform IaC directory or Kubernetes manifest path
python3 advance_secscan_ai.py --cspm-scan path/to/terraform/

# Execute dedicated Kubernetes Security Posture Management (KSPM) audit
python3 advance_secscan_ai.py --k8s-audit

# Export automated CLI and IaC hardening remediation script
python3 advance_secscan_ai.py --cspm-scan --export-cloud-fix cloud_hardening.sh
```

## 🔐 Enterprise Security

### Authentication & Authorization
- **Multi-Factor Authentication**: LDAP/AD + JWT tokens
- **Role-Based Access Control**: Granular permissions matrix
- **Session Management**: Secure session handling with timeout
- **API Security**: Rate limiting, CORS, input validation

### Data Protection
- **Encryption**: AES-256-GCM for data at rest
- **Transport Security**: TLS 1.3 for data in transit  
- **Key Management**: Automated key rotation
- **Audit Logging**: Comprehensive activity tracking

### Compliance Frameworks
| Framework | Coverage | Reports | Automation |
|-----------|----------|---------|------------|
| **OWASP Top 10** | ✅ Full | ✅ Yes | ✅ Automated |
| **NIST Cybersecurity Framework** | ✅ Full | ✅ Yes | ✅ Automated |
| **ISO 27001** | ✅ Partial | ✅ Yes | ✅ Semi-automated |
| **SOC 2** | ✅ Partial | ✅ Yes | ✅ Semi-automated |
| **PCI DSS** | ✅ Partial | ✅ Yes | ✅ Manual |

## 📈 Monitoring & Analytics

### Real-Time Monitoring
- **System Metrics**: CPU, memory, disk, network utilization
- **Application Metrics**: Request rates, response times, error rates
- **Security Metrics**: Vulnerability counts, risk scores, remediation rates
- **Business Metrics**: Assessment coverage, compliance scores

### Alerting
- **Email Alerts**: Critical vulnerabilities, system issues
- **Slack Integration**: Real-time notifications to security teams
- **Webhook Support**: Custom integrations with SIEM systems
- **Dashboard Alerts**: Visual indicators and notifications

### Analytics Dashboard
```bash
# Access Grafana dashboard
http://localhost:3000
# Login: admin / secscan_ai123

# Pre-configured dashboards:
# - SecScan AI System Overview
# - Assessment Performance Metrics  
# - Vulnerability Trend Analysis
# - User Activity Dashboard
# - Compliance Status Overview
```

## 🛠️ Advanced Usage

### Multi-Provider AI Models
```python
from ai_engine import get_advanced_ai_engine, list_all_models, get_available_providers
# Initialize with a specific model
engine = get_advanced_ai_engine(model_id='claude-sonnet-5')

# Switch models at runtime
engine.set_model('gemini-3.5-flash')

# List all 26+ available models
for model in engine.list_available_models():
    status = "✅" if model['available'] else "❌"
    print(f"{status} {model['display_name']} ({model['provider']})")

# Check available providers
for provider in get_available_providers():
    print(f"{provider['name']}: {provider['model_count']} models")
```

### OrcaRouter Cyber Inference
[OrcaRouter](https://www.orcarouter.ai) is an OpenAI-compatible gateway for authorized
security teams. It routes scoped security reasoning to the OrcaCyber models and carries
the gateway's blue-team controls on the same endpoint. Select the `orcarouter` provider
(base URL `https://api.orcarouter.ai/v1`) and set `ORCAROUTER_API_KEY`, or
`[ai] orcarouter_api_key` in `config.ini`.

- Recommended default: `orca/orcacyber-ultra-1.0` (OrcaCyber Ultra); `orca/orcacyber-zero-1.5`
  is the harness-driven alternative. Both require the cyber tier to be unlocked for
  your workspace during business verification.
- When the cyber tier is not unlocked, use `orcarouter/fusion`.
- Provider page: https://www.orcarouter.ai/cyber
- Cyber model catalog: https://www.orcarouter.ai/models?tier=cyber

The dashboard's **AI Providers** view accepts the key and loads models from the live
`GET https://api.orcarouter.ai/v1/models?capability=chat` catalog.

### Custom Compliance Frameworks
```python
# Add custom compliance framework
from security.compliance import ComplianceFrameworkMapper

mapper = ComplianceFrameworkMapper()
mapper.add_framework('CUSTOM', {
    'sql_injection': 'SEC-01',
    'xss': 'SEC-02',
    # ... custom mappings
})
```

### Kubernetes Deployment
```yaml
# Deploy to Kubernetes cluster
kubectl apply -f k8s/
```

### Multi-Cloud Deployment
```bash
# Deploy to AWS
python3 advance_secscan_ai.py --deploy aws

# Deploy to Azure  
python3 advance_secscan_ai.py --deploy azure

# Deploy to GCP
python3 advance_secscan_ai.py --deploy gcp
```

## 🧪 Testing & Development

### Running Tests
```bash
# Unit tests
pytest tests/unit/

# Integration tests  
pytest tests/integration/

# End-to-end tests
pytest tests/e2e/

# Security tests
bandit -r .
safety check
```

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Pre-commit hooks
pre-commit install

# Code formatting
black .
flake8 .
mypy .
```

## 📦 Enterprise Deployment

### Docker Swarm
```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml secscan_ai
```

### Kubernetes
```bash
# Create namespace
kubectl create namespace secscan_ai

# Deploy applications
kubectl apply -f k8s/

# Scale workers
kubectl scale deployment secscan_ai-worker --replicas=10
```

### Cloud Platforms

#### AWS Deployment
```bash
# ECS deployment
aws ecs create-cluster --cluster-name secscan_ai
aws ecs create-service --service-name secscan_ai-api
```

#### Azure Deployment  
```bash
# ACI deployment
az container create --resource-group secscan_ai --name secscan_ai-api
```

#### GCP Deployment
```bash
# GKE deployment
gcloud container clusters create secscan_ai-cluster
kubectl apply -f k8s/
```

## 🔧 Troubleshooting

### Common Enterprise Issues

#### Database Connection Issues
```bash
# Check PostgreSQL status
systemctl status postgresql
docker logs secscan_ai-database

# Test connection
python3 -c "from database import get_db_manager; print(get_db_manager().test_connection())"
```

#### Redis Cache Issues
```bash
# Check Redis status
redis-cli ping
docker logs secscan_ai-redis

# Clear cache
redis-cli FLUSHALL
```

#### AI Engine Issues
```bash
# List available AI models and providers
python3 -c "from ai_engine import list_all_models; [print(m.display_name, m.provider.value) for m in list_all_models()]"

# Test provider connectivity
python3 -c "from ai_engine.providers import ProviderFactory; print(ProviderFactory.get_available_providers())"

# Check local LLM (Ollama)
ollama list
ollama run llama3.3:70b
```

#### Worker Pool Issues
```bash
# Check Celery workers
celery -A performance.parallel_processor inspect active

# Restart workers
docker-compose restart secscan_ai-worker
```

### Performance Optimization
```bash
# Database optimization
python3 -c "from database import optimize_database; optimize_database()"

# Cache warming
python3 -c "from performance.cache_manager import warm_cache; warm_cache()"

# Worker scaling
docker-compose up --scale secscan_ai-worker=10
```

## 📄 Enterprise License

This project is licensed under the MIT License with additional enterprise terms:

- **Commercial Use**: Permitted with attribution
- **Enterprise Support**: Available through support channels
- **Compliance**: Tool usage must comply with applicable laws
- **Liability**: Limited liability for enterprise deployments

## 🆘 Enterprise Support

### Support Channels
- **Enterprise Support**: yashabalam707@gmail.com
- **Technical Issues**: https://github.com/najafdev/secscan_ai/issues
- **Feature Requests**: https://github.com/najafdev/secscan_ai/discussions
- **Security Issues**: yashabalam707@gmail.com
- **WhatsApp Business**: [Join Channel](https://whatsapp.com/channel/0029Vaoa1GfKLaHlL0Kc8k1q)

### Professional Services
- **Implementation**: Custom deployment and configuration
- **Training**: Security team training and certification  
- **Custom Development**: Feature development and integration
- **24/7 Support**: Enterprise support packages available

### Connect with the Team
- **Yashab Alam**: [GitHub](https://github.com/yashab-cyber) | [Instagram](https://www.instagram.com/yashab.alam) | [LinkedIn](https://www.linkedin.com/in/yashab-alam)

## 📊 Project Statistics

| Metric | Value |
|--------|-------|
| **Total Lines of Code** | 15,000+ |
| **Enterprise Dependencies** | 90+ |
| **Configuration Options** | 200+ |
| **Environment Variables** | 100+ |
| **Docker Services** | 12 |
| **Supported Compliance Frameworks** | 5 |
| **Penetration Testing Tools** | 50+ |
| **API Endpoints** | 25+ |
| **Deployment Platforms** | 6+ |

## 🗺️ Roadmap

### Version 2.1 (Q3 2025)
- [x] Multi-provider AI support (OpenAI, Anthropic, Google, DeepSeek, GLM, Local, OpenRouter)
- [x] 26+ model catalog with runtime switching
- [x] Provider fallback chain and automatic detection
- [ ] ML-based false positive reduction
- [ ] Integration with popular SIEM systems

### Version 2.2 (Q4 2025)
- [ ] Streaming responses from all providers
- [ ] Automated penetration testing workflows
- [ ] Advanced cloud security assessments
- [ ] Integration with CI/CD pipelines

### Version 3.0 (Q1 2026)
- [ ] Fully autonomous security assessments
- [ ] Advanced AI attack simulation
- [ ] Quantum-safe cryptography
- [ ] Next-generation threat detection

## 🙏 Contributors

### Core Development Team
- **Lead Developer & Founder**: [Yashab Alam](https://github.com/yashab-cyber) - [@yashab.alam](https://www.instagram.com/yashab.alam) | [LinkedIn](https://www.linkedin.com/in/yashab-alam)
- **AI/ML Engineer**: Enterprise AI Team
- **Security Engineer**: Enterprise Security Team
- **DevOps Engineer**: Enterprise Infrastructure Team


- 💬 **WhatsApp**: [Business Channel](https://whatsapp.com/channel/0029Vaoa1GfKLaHlL0Kc8k1q)

### Acknowledgments
- OpenAI for GPT-5 and o-series API access
- Anthropic for the Claude model family
- Google DeepMind for Gemini models
- DeepSeek, Zhipu AI (GLM), and OpenRouter
- Ollama team for local LLM support
- Docker & Kubernetes communities
- Security research community
- Open source tool developers

### 💰 Support SecScan AI Development
Your support accelerates development, research infrastructure, and frontier AI model integrations:

- **🪙 Official Solana Contract Address (CA)**: `6xJfHQBWz4A8jG9tD8zYBVNJHXjkqbPErkAcHdoVpump`
- **🪙 Cryptocurrency Donations**: For transfers (**Solana, Bitcoin, Ethereum, USDT, etc.**), please email **[sai466769@gmail.com](mailto:sai466769@gmail.com)**
- **📄 Full Sponsorship & Donation Guide**: See [DONATE.md](DONATE.md) for tier perks, transparency reports, and roadmap goals

## ⚖️ Legal & Compliance

**⚠️ IMPORTANT LEGAL NOTICE**

SecScan AI Enterprise is designed for authorized security testing only:

- ✅ **Authorized Use**: Only use against systems you own or have explicit written permission
- ✅ **Compliance**: Follow all applicable laws, regulations, and industry standards
- ✅ **Responsible Disclosure**: Report vulnerabilities through proper channels
- ✅ **Documentation**: Maintain audit trails and documentation
- ❌ **Unauthorized Use**: Never use against systems without permission
- ❌ **Malicious Activity**: Not for criminal or malicious purposes

**The developers and contributors are not liable for misuse of this platform.**

---

---

<div align="center">
  <img src="public/secscan_ai-logo.png" alt="SecScan AI Enterprise" width="150" height="auto">
  
  <h3>🚀 SecScan AI Enterprise - Transforming Cybersecurity Through AI 🚀</h3>
  <p><em>Made with ❤️ by Yashab Alam for enterprise security teams worldwide</em></p>
  
  <p>
    <a href="https://github.com/najafdev/secscan_ai">⭐ Star us on GitHub</a> |
    <a href="DONATE.md">💰 Support Development</a> |
    <a href="#-enterprise-support">📞 Get Support</a> |
    <a href="#-contributors">🤝 Contribute</a> |
    <a href="LICENSE">📄 License</a>
  </p>
</div>

### 🔗 Connect with Yashab Alam

<div align="center">
  <p>
    <a href="https://whatsapp.com/channel/0029Vaoa1GfKLaHlL0Kc8k1q">💬 WhatsApp Business</a> |
    <a href="https://discord.gg/eXPjM3Hxwb">👾 Discord Channel</a>
  </p>
  
  <p>
    <strong>Founder & Lead Developer:</strong> Yashab Alam<br>
    <a href="https://github.com/yashab-cyber">🔧 GitHub</a> |
    <a href="https://www.instagram.com/yashabcyber">📸 Instagram</a> |
    <a href="https://x.com/_gh0st0fs0l">🐦 X (Twitter)</a> |
    <a href="https://www.linkedin.com/in/yashab-alam">💼 LinkedIn</a> |
    <a href="https://www.threads.com/@yashabcyber">🧵 Threads</a>
  </p>
  
  <p>
    <strong>Email Contacts:</strong><br>
    📧 <a href="mailto:yashabalam9@gmail.com">yashabalam9@gmail.com</a> | 📧 <a href="mailto:yashabalam707@gmail.com">yashabalam707@gmail.com</a>
  </p>
</div>