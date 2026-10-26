#!/usr/bin/env python3
# SecScan AI core module
"""
Advanced AI Engine for SecScan AI
Context-aware analysis with memory and pattern recognition
"""

import os
import json
import logging
import hashlib
import time
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import subprocess
import requests

# Multi-provider AI imports
try:
    from .model_registry import (
        ModelProvider, ModelInfo, MODEL_CATALOG,
        get_model_info, list_all_models, get_models_by_provider,
        get_available_providers
    )
    from .providers import ProviderFactory, BaseProvider
except ImportError as e:
    logging.warning(f"Multi-provider modules not available: {e}")

# CVE Intelligence and Attack Chaining imports
try:
    from .cve_intelligence import CVEIntelligenceEngine, CVEInfo
    from .attack_chainer import (
        AttackChainingEngine, AttackGraph, AttackNode, AttackEdge, AttackStage
    )
except ImportError as e:
    CVEIntelligenceEngine = None
    CVEInfo = None
    AttackChainingEngine = None
    AttackGraph = None
    AttackNode = None
    AttackEdge = None
    AttackStage = None
    logging.warning(f"CVE Intelligence or Attack Chaining modules not available: {e}")

# ML and AI imports
try:
    import openai
except ImportError as e:
    openai = None
    logging.warning(f"openai not available: {e}")

# Lazy-load transformers and torch on demand to eliminate heavy module startup latency
pipeline = None
AutoTokenizer = None
AutoModel = None
torch = None

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError as e:
    TfidfVectorizer = None
    KMeans = None
    cosine_similarity = None
    logging.warning(f"sklearn dependencies not available: {e}")

from database import get_db_manager, AIContext

@dataclass
class AnalysisResult:
    """Structured analysis result"""
    summary: str
    risk_assessment: Dict[str, Any]
    recommendations: List[str]
    next_actions: List[str]
    confidence_score: float
    patterns_detected: List[str]
    context_used: Dict[str, Any]

@dataclass 
class VulnerabilityPattern:
    """Vulnerability pattern for ML recognition"""
    pattern_id: str
    pattern_type: str
    indicators: List[str]
    severity_prediction: str
    confidence: float
    remediation_template: str

class PatternRecognizer:
    """Machine learning-based pattern recognition"""
    
    def __init__(self):
        self.patterns = self._load_vulnerability_patterns()
        self.vectorizer = TfidfVectorizer(max_features=5000, stop_words='english') if TfidfVectorizer else None
        self.kmeans = None
        self.pattern_vectors = None
        if self.vectorizer is not None:
            self._initialize_ml_models()
        
    def _load_vulnerability_patterns(self) -> List[VulnerabilityPattern]:
        """Load known vulnerability patterns"""
        patterns = [
            VulnerabilityPattern(
                pattern_id="sql_injection",
                pattern_type="web_vuln",
                indicators=["error", "mysql", "syntax", "sql", "database", "union", "select"],
                severity_prediction="high",
                confidence=0.9,
                remediation_template="Use parameterized queries and input validation"
            ),
            VulnerabilityPattern(
                pattern_id="xss",
                pattern_type="web_vuln", 
                indicators=["script", "alert", "document", "cookie", "javascript", "payload"],
                severity_prediction="medium",
                confidence=0.85,
                remediation_template="Implement proper output encoding and CSP"
            ),
            VulnerabilityPattern(
                pattern_id="directory_traversal",
                pattern_type="web_vuln",
                indicators=["../", "..\\", "path", "file", "directory", "traversal"],
                severity_prediction="high",
                confidence=0.8,
                remediation_template="Validate and sanitize file path inputs"
            ),
            VulnerabilityPattern(
                pattern_id="weak_authentication",
                pattern_type="auth_vuln",
                indicators=["password", "weak", "default", "admin", "login", "authentication"],
                severity_prediction="high",
                confidence=0.75,
                remediation_template="Implement strong password policies and MFA"
            ),
            VulnerabilityPattern(
                pattern_id="privilege_escalation",
                pattern_type="system_vuln",
                indicators=["root", "sudo", "privilege", "escalation", "setuid", "permissions"],
                severity_prediction="critical",
                confidence=0.9,
                remediation_template="Apply principle of least privilege and patch management"
            ),
        ]
        return patterns
    
    def _initialize_ml_models(self):
        """Initialize ML models for pattern recognition"""
        try:
            # Create pattern corpus for training
            pattern_texts = []
            for pattern in self.patterns:
                pattern_text = " ".join(pattern.indicators)
                pattern_texts.append(pattern_text)
            
            if pattern_texts:
                self.pattern_vectors = self.vectorizer.fit_transform(pattern_texts)
                
                # Train clustering model
                self.kmeans = KMeans(n_clusters=min(len(pattern_texts), 5), random_state=42)
                self.kmeans.fit(self.pattern_vectors)
                
            logging.info("ML models initialized successfully")
            
        except Exception as e:
            logging.error(f"Error initializing ML models: {e}")
    
    def detect_patterns(self, text: str) -> List[Tuple[VulnerabilityPattern, float]]:
        """Detect vulnerability patterns in text"""
        if self.vectorizer is None or self.pattern_vectors is None or getattr(self.pattern_vectors, 'shape', [0])[0] == 0:
            detected_patterns = []
            text_lower = text.lower()
            for pattern in self.patterns:
                matches = sum(1 for ind in pattern.indicators if ind.lower() in text_lower)
                if matches > 0:
                    similarity = matches / len(pattern.indicators)
                    confidence = similarity * pattern.confidence
                    if confidence >= 0.2:
                        detected_patterns.append((pattern, confidence))
            detected_patterns.sort(key=lambda x: x[1], reverse=True)
            return detected_patterns[:5]
            
        try:
            # Vectorize input text
            text_vector = self.vectorizer.transform([text.lower()])
            
            # Calculate similarity with known patterns
            similarities = cosine_similarity(text_vector, self.pattern_vectors)[0]
            
            detected_patterns = []
            for i, similarity in enumerate(similarities):
                if similarity > 0.3:  # Threshold for pattern detection
                    pattern = self.patterns[i]
                    confidence = similarity * pattern.confidence
                    detected_patterns.append((pattern, confidence))
            
            # Sort by confidence
            detected_patterns.sort(key=lambda x: x[1], reverse=True)
            return detected_patterns[:5]  # Return top 5 patterns
            
        except Exception as e:
            logging.error(f"Error in pattern detection: {e}")
            return []
    
    def predict_vulnerability_type(self, indicators: List[str]) -> Dict[str, float]:
        """Predict vulnerability type based on indicators"""
        indicator_text = " ".join(indicators).lower()
        patterns = self.detect_patterns(indicator_text)
        
        predictions = {}
        for pattern, confidence in patterns:
            predictions[pattern.pattern_type] = max(predictions.get(pattern.pattern_type, 0), confidence)
        
        return predictions

class ContextManager:
    """Manages AI context and memory"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.db = get_db_manager()
        self.context_cache = {}
        self.max_context_age = timedelta(hours=24)
        
    def get_session_context(self) -> Dict[str, Any]:
        """Get accumulated context for session"""
        # Check cache first
        cache_key = f"session_context_{self.session_id}"
        if cache_key in self.context_cache:
            return self.context_cache[cache_key]
        
        # Retrieve from database
        ai_contexts = self.db.get_ai_context(self.session_id)
        
        context = {
            'target_info': {},
            'discovered_services': [],
            'vulnerabilities': [],
            'attack_vectors': [],
            'patterns': [],
            'previous_phases': []
        }
        
        for ai_context in ai_contexts:
            context_data = ai_context.context_data
            context_type = ai_context.context_type
            
            if context_type == 'target':
                context['target_info'].update(context_data)
            elif context_type == 'vulnerability':
                context['vulnerabilities'].append(context_data)
            elif context_type == 'service':
                context['discovered_services'].extend(context_data.get('services', []))
            elif context_type == 'phase':
                context['previous_phases'].append(context_data)
        
        # Cache the result
        self.context_cache[cache_key] = context
        return context
    
    def update_context(self, context_type: str, data: Dict[str, Any], confidence: float = 1.0):
        """Update context with new information"""
        self.db.save_ai_context(self.session_id, context_type, data, confidence)
        
        # Invalidate cache
        cache_key = f"session_context_{self.session_id}"
        if cache_key in self.context_cache:
            del self.context_cache[cache_key]
    
    def get_relevant_context(self, query: str, context_type: str = None) -> Dict[str, Any]:
        """Get context relevant to a specific query"""
        all_context = self.get_session_context()
        
        if context_type:
            return all_context.get(context_type, {})
        
        # Use simple keyword matching for relevance
        relevant_context = {}
        query_words = set(query.lower().split())
        
        for key, value in all_context.items():
            if isinstance(value, (list, dict)):
                value_text = json.dumps(value).lower()
                if any(word in value_text for word in query_words):
                    relevant_context[key] = value
        
        return relevant_context

class VulnerabilityCorrelator:
    """Correlates vulnerabilities to identify attack chains with graph modeling and CVE enrichment"""
    
    def __init__(self):
        self.db = get_db_manager()
        self.cve_intel = CVEIntelligenceEngine() if CVEIntelligenceEngine else None
        self.attack_chainer = AttackChainingEngine() if AttackChainingEngine else None
        
    def correlate_findings(self, session_id: str, vulnerabilities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Correlate vulnerabilities to find attack chains, graph paths, and chokepoints"""
        # Enrich findings with CVE threat intelligence if available
        enriched_vulns = vulnerabilities
        cisa_kev_summary = {"total_kev_count": 0, "requires_immediate_action": False, "vulnerabilities": []}
        if self.cve_intel:
            enriched_vulns = self.cve_intel.enrich_findings(vulnerabilities)
            cisa_kev_summary = self.cve_intel.get_cisa_kev_summary(enriched_vulns)

        # Build directed attack graph with multi-stage attack chaining
        attack_graph_dict = {}
        critical_chokepoints = []
        remediation_roadmap = []
        mermaid_diagram = ""
        if self.attack_chainer:
            graph = self.attack_chainer.synthesize_attack_graph(enriched_vulns)
            attack_graph_dict = graph.to_dict()
            critical_chokepoints = graph.find_critical_chokepoints()
            remediation_roadmap = self.attack_chainer.generate_remediation_roadmap(graph)
            mermaid_diagram = graph.to_mermaid()

        # Build traditional attack chains for backward compatibility
        attack_chains = self._build_attack_chains(enriched_vulns)
        compound_risks = self._calculate_compound_risk(attack_chains)
        exploitation_priority = self._prioritize_exploits(attack_chains, compound_risks)
        
        # Save attack chains to database
        for i, chain in enumerate(attack_chains):
            try:
                self.db.create_attack_chain(
                    session_id=session_id,
                    vulnerability_id=chain.get('primary_vulnerability_id', ''),
                    chain_sequence=i,
                    exploit_path=chain['steps'],
                    risk_score=compound_risks.get(i, 0.0),
                    impact_description=chain.get('impact', '')
                )
            except Exception as e:
                logging.debug(f"Could not persist chain {i} to db: {e}")
        
        return {
            'attack_chains': attack_chains,
            'risk_assessment': compound_risks,
            'exploitation_priority': exploitation_priority,
            'attack_graph': attack_graph_dict,
            'critical_chokepoints': critical_chokepoints,
            'remediation_roadmap': remediation_roadmap,
            'mermaid_diagram': mermaid_diagram,
            'cisa_kev_summary': cisa_kev_summary,
            'enriched_vulnerabilities': enriched_vulns
        }
    
    def _build_attack_chains(self, vulnerabilities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build potential attack chains from vulnerabilities"""
        chains = []
        
        # Group vulnerabilities by type and system
        web_vulns = [v for v in vulnerabilities if v.get('category') == 'web']
        system_vulns = [v for v in vulnerabilities if v.get('category') == 'system']
        network_vulns = [v for v in vulnerabilities if v.get('category') == 'network']
        
        # Build web application attack chains
        if web_vulns:
            for vuln in web_vulns:
                if vuln.get('severity') in ['critical', 'high']:
                    chain = {
                        'name': f"Web Application Attack via {vuln['title']}",
                        'primary_vulnerability_id': vuln.get('id', ''),
                        'steps': [
                            {'step': 1, 'action': 'Exploit web vulnerability', 'vuln': vuln['title']},
                            {'step': 2, 'action': 'Gain initial access', 'method': 'web_shell'},
                            {'step': 3, 'action': 'Enumerate system', 'tools': ['linpeas', 'enum4linux']},
                        ],
                        'impact': 'Initial system access and potential lateral movement',
                        'likelihood': 0.8 if vuln.get('severity') == 'critical' else 0.6
                    }
                    
                    # Add privilege escalation if system vulns exist
                    if system_vulns:
                        chain['steps'].append({
                            'step': 4, 'action': 'Privilege escalation', 
                            'vulns': [v['title'] for v in system_vulns[:2]]
                        })
                        chain['impact'] += ', privilege escalation to root'
                        chain['likelihood'] *= 0.9
                    
                    chains.append(chain)
        
        # Build network attack chains
        if network_vulns:
            for vuln in network_vulns:
                if vuln.get('severity') in ['critical', 'high']:
                    chain = {
                        'name': f"Network Attack via {vuln['title']}",
                        'primary_vulnerability_id': vuln.get('id', ''),
                        'steps': [
                            {'step': 1, 'action': 'Network reconnaissance', 'vuln': vuln['title']},
                            {'step': 2, 'action': 'Service exploitation', 'method': 'direct_exploit'},
                            {'step': 3, 'action': 'Lateral movement', 'scope': 'network_segment'},
                        ],
                        'impact': 'Network compromise and lateral movement',
                        'likelihood': 0.7
                    }
                    chains.append(chain)
        
        return chains
    
    def _calculate_compound_risk(self, attack_chains: List[Dict[str, Any]]) -> Dict[int, float]:
        """Calculate compound risk scores for attack chains"""
        risks = {}
        
        for i, chain in enumerate(attack_chains):
            # Base risk from likelihood
            base_risk = chain.get('likelihood', 0.5)
            
            # Multiply by number of steps (more complex = higher risk if successful)
            complexity_multiplier = min(len(chain.get('steps', [])) * 0.2, 2.0)
            
            # Impact factor based on description
            impact_keywords = ['root', 'admin', 'critical', 'network', 'data']
            impact_score = sum(1 for keyword in impact_keywords 
                             if keyword in chain.get('impact', '').lower())
            impact_factor = min(1.0 + (impact_score * 0.3), 3.0)
            
            # Calculate final compound risk (0-10 scale)
            compound_risk = base_risk * complexity_multiplier * impact_factor * 3.33
            risks[i] = min(compound_risk, 10.0)
        
        return risks
    
    def _prioritize_exploits(self, attack_chains: List[Dict[str, Any]], 
                           compound_risks: Dict[int, float]) -> List[Dict[str, Any]]:
        """Prioritize exploits based on risk and feasibility"""
        prioritized = []
        
        for i, chain in enumerate(attack_chains):
            risk_score = compound_risks.get(i, 0.0)
            likelihood = chain.get('likelihood', 0.5)
            
            # Priority score combines risk and likelihood
            priority_score = (risk_score * 0.6) + (likelihood * 10 * 0.4)
            
            prioritized.append({
                'chain_index': i,
                'chain_name': chain['name'],
                'priority_score': priority_score,
                'risk_score': risk_score,
                'likelihood': likelihood,
                'recommendation': self._get_exploit_recommendation(chain, risk_score)
            })
        
        # Sort by priority score (highest first)
        prioritized.sort(key=lambda x: x['priority_score'], reverse=True)
        
        return prioritized
    
    def _get_exploit_recommendation(self, chain: Dict[str, Any], risk_score: float) -> str:
        """Get recommendation for exploit prioritization"""
        if risk_score >= 8.0:
            return "CRITICAL: Exploit immediately - high impact, high likelihood"
        elif risk_score >= 6.0:
            return "HIGH: Priority exploit - significant risk"
        elif risk_score >= 4.0:
            return "MEDIUM: Consider for exploitation after high priority items"
        else:
            return "LOW: Low priority - consider for comprehensive testing"

class AdvancedAIEngine:
    """Advanced AI Engine with context awareness and ML capabilities"""
    
    def __init__(
        self,
        session_id: str = None,
        model_id: str = None,
        provider: str = None,
        custom_route: str = None,
    ):
        self.session_id = session_id
        self.api_key = os.getenv('OPENAI_API_KEY')
        
        # Multi-provider model selection
        self.model_id = model_id or os.getenv('SECSCAN_AI_MODEL', os.getenv('OPENAI_MODEL', 'gpt-4o'))
        self.provider_name = provider or os.getenv('SECSCAN_AI_PROVIDER', None)
        self.custom_route = custom_route or os.getenv('SECSCAN_AI_CUSTOM_ROUTE') or os.getenv('CUSTOM_ROUTER_BASE_URL')
        self.active_provider = None
        self.active_model_info = None
        
        # Initialize components
        self.pattern_recognizer = PatternRecognizer()
        self.vulnerability_correlator = VulnerabilityCorrelator()
        self.cve_intelligence = CVEIntelligenceEngine() if CVEIntelligenceEngine else None
        self.attack_chainer = AttackChainingEngine() if AttackChainingEngine else None
        
        if session_id:
            self.context_manager = ContextManager(session_id)
        else:
            self.context_manager = None
        
        self.logger = logging.getLogger(__name__)
        
        # Initialize AI models
        self._setup_ai_models()
        
    def _setup_ai_models(self):
        """Setup AI models with multi-provider support"""
        try:
            # Try to resolve the selected model via the provider factory
            provider_instance, model_info = ProviderFactory.get_provider_for_model(
                self.model_id, custom_route=self.custom_route
            )
            if provider_instance.is_available():
                self.active_provider = provider_instance
                self.active_model_info = model_info
                self.local_mode = False
                self.logger.info(
                    f"Using {model_info.provider.value} provider with model '{model_info.display_name}'"
                )
                return
        except Exception as e:
            self.logger.warning(f"Could not initialize provider for model '{self.model_id}': {e}")
        
        # Fallback: try OpenAI API key directly
        if self.api_key:
            self.local_mode = False
            self.logger.info("Falling back to direct OpenAI API")
            return
        
        # Final fallback: local models
        self.local_mode = True
        self.local_analyzer = None
        self._local_analyzer_failed = False
        self.logger.info("Configured for local AI models fallback")
    
    def _setup_local_models(self):
        """Setup local AI models"""
        if getattr(self, "_local_analyzer_failed", False):
            return
        try:
            # Try to use a local model or Hugging Face transformers on demand
            global pipeline
            if pipeline is None:
                from transformers import pipeline
            self.local_analyzer = pipeline(
                "text-classification", 
                model="distilbert-base-uncased-finetuned-sst-2-english",
                device=-1  # Use CPU
            )
            self.logger.info("Local AI models setup complete")
        except Exception as e:
            self.logger.warning(f"Could not setup local AI models: {e}")
            self.local_analyzer = None
            self._local_analyzer_failed = True
    
    def analyze_with_context(self, data: str, phase: str, context_type: str = "general") -> AnalysisResult:
        """Perform context-aware analysis"""
        try:
            # Get relevant context
            relevant_context = {}
            if self.context_manager:
                relevant_context = self.context_manager.get_relevant_context(data, context_type)
            
            # Detect patterns
            detected_patterns = self.pattern_recognizer.detect_patterns(data)
            pattern_info = [f"{p[0].pattern_type}: {p[0].pattern_id} (confidence: {p[1]:.2f})" 
                          for p in detected_patterns]
            
            # Create enhanced prompt with context
            prompt = self._create_context_aware_prompt(data, phase, relevant_context, detected_patterns)
            
            # Get AI analysis
            if self.local_mode:
                analysis_text = self._analyze_local(prompt)
            else:
                analysis_text = self._analyze_openai(prompt)
            
            # Parse and structure the analysis
            structured_analysis = self._structure_analysis(analysis_text, detected_patterns)
            
            # Update context with new findings
            if self.context_manager:
                self.context_manager.update_context(
                    context_type, 
                    {
                        'phase': phase,
                        'findings': structured_analysis.summary,
                        'patterns': pattern_info,
                        'timestamp': datetime.utcnow().isoformat()
                    },
                    structured_analysis.confidence_score
                )
            
            return structured_analysis
            
        except Exception as e:
            self.logger.error(f"Error in context-aware analysis: {e}")
            # Return basic analysis as fallback
            return AnalysisResult(
                summary=f"Error in analysis: {str(e)}",
                risk_assessment={'error': True},
                recommendations=["Review analysis system"],
                next_actions=["Check logs for details"],
                confidence_score=0.1,
                patterns_detected=[],
                context_used={}
            )
    
    def _create_context_aware_prompt(self, data: str, phase: str, context: Dict[str, Any], 
                                   patterns: List[Tuple]) -> str:
        """Create context-aware prompt"""
        context_summary = ""
        if context:
            context_summary = f"\nPrevious Context:\n{json.dumps(context, indent=2, default=str)[:1000]}..."
        
        pattern_summary = ""
        if patterns:
            pattern_summary = f"\nDetected Patterns:\n"
            for pattern, confidence in patterns[:3]:
                pattern_summary += f"- {pattern.pattern_type}: {pattern.pattern_id} (confidence: {confidence:.2f})\n"
        
        prompt = f"""
You are SecScanAI, an expert penetration testing AI assistant with advanced pattern recognition.

Current Phase: {phase}
Data to Analyze: {data}

{context_summary}

{pattern_summary}

Please provide a comprehensive analysis including:
1. **Summary**: Key findings and their significance
2. **Risk Assessment**: Severity levels, CVSS estimates, business impact
3. **Pattern Analysis**: How detected patterns relate to known vulnerability types
4. **Context Integration**: How findings relate to previous phases and discoveries
5. **Recommendations**: Specific actions to take
6. **Next Actions**: Concrete steps for the next phase
7. **Confidence Score**: Your confidence in the analysis (0.0-1.0)

Format your response as clear, actionable insights for penetration testers.
"""
        return prompt
    
    def _analyze_openai(self, prompt: str) -> str:
        """Analyze using configured AI provider (multi-provider support)"""
        # Use multi-provider system if available
        if self.active_provider:
            try:
                messages = [{"role": "user", "content": prompt}]
                max_tokens = 2000
                if self.active_model_info:
                    max_tokens = min(2000, self.active_model_info.max_tokens)
                
                result = self.active_provider.chat_completion(
                    model_id=self.model_id,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=0.7
                )
                return result
            except Exception as e:
                self.logger.error(f"Provider '{self.active_provider.provider_name}' error: {e}")
                self.logger.info("Attempting fallback to direct OpenAI API...")
        
        # Fallback to direct OpenAI API call
        try:
            client = openai.OpenAI(api_key=self.api_key)
            model = os.getenv('OPENAI_MODEL', 'gpt-4o')
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            return f"AI Analysis Error: {str(e)}"
    
    def _analyze_local(self, prompt: str) -> str:
        """Analyze using local models"""
        try:
            if self.local_analyzer is None and not getattr(self, "_local_analyzer_failed", False):
                self._setup_local_models()
            if self.local_analyzer:
                # This is a simplified local analysis - in production you'd use a more sophisticated model
                sentiment = self.local_analyzer(prompt[:512])[0]
                
                return f"""
                Local AI Analysis:
                Based on pattern recognition and local processing:
                
                Summary: Detected technical content with {sentiment['label']} sentiment (confidence: {sentiment['score']:.2f})
                
                Risk Assessment: Requires manual review for accurate risk assessment
                
                Recommendations:
                - Review findings manually
                - Consider upgrading to cloud AI for better analysis
                - Use pattern matching results for initial assessment
                
                Note: This is a simplified local analysis. For production use, consider OpenAI API or specialized security AI models.
                """
            else:
                return "Local AI analysis not available. Please configure OpenAI API key or install required models."
                
        except Exception as e:
            return f"Local AI Error: {str(e)}"
    
    def _structure_analysis(self, analysis_text: str, patterns: List[Tuple]) -> AnalysisResult:
        """Structure the AI analysis into components"""
        # Simple parsing - in production, you might use more sophisticated NLP
        lines = analysis_text.split('\n')
        
        summary = ""
        risk_assessment = {}
        recommendations = []
        next_actions = []
        confidence_score = 0.7  # Default confidence
        
        current_section = ""
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Detect sections
            if "summary" in line.lower() and (":" in line or "#" in line):
                current_section = "summary"
                after_colon = line.split(":", 1)[1].strip() if ":" in line else ""
                if after_colon:
                    summary += after_colon + " "
                continue
            elif "risk" in line.lower() and (":" in line or "#" in line):
                current_section = "risk"
                continue  
            elif "recommendation" in line.lower() and (":" in line or "#" in line):
                current_section = "recommendations"
                continue
            elif "next" in line.lower() and "action" in line.lower() and (":" in line or "#" in line):
                current_section = "actions"
                continue
            elif "confidence" in line.lower() and (":" in line or "#" in line):
                current_section = "confidence"
                import re
                match = re.search(r'(\d+\.?\d*)', line)
                if match:
                    try:
                        raw_val = float(match.group(1))
                        if raw_val > 1.0:
                            confidence_score = min(raw_val / 100.0, 1.0)
                        else:
                            confidence_score = max(0.0, raw_val)
                    except ValueError:
                        pass
                continue
            
            # Parse content based on current section
            if current_section == "summary" and line:
                summary += line + " "
            elif current_section == "recommendations" and line.startswith(('-', '•', '*')):
                recommendations.append(line[1:].strip())
            elif current_section == "actions" and line.startswith(('-', '•', '*')):
                next_actions.append(line[1:].strip())
            elif current_section == "confidence":
                # Try to extract confidence score
                import re
                match = re.search(r'(\d+\.?\d*)', line)
                if match:
                    try:
                        raw_val = float(match.group(1))
                        if raw_val > 1.0:
                            confidence_score = min(raw_val / 100.0, 1.0)
                        else:
                            confidence_score = max(0.0, raw_val)
                    except ValueError:
                        pass
        
        # Extract risk assessment from patterns
        for pattern, pattern_confidence in patterns:
            risk_assessment[pattern.pattern_id] = {
                'severity': pattern.severity_prediction,
                'confidence': pattern_confidence,
                'type': pattern.pattern_type
            }
        
        return AnalysisResult(
            summary=summary.strip() or "Analysis completed",
            risk_assessment=risk_assessment,
            recommendations=recommendations or ["Continue with next phase"],
            next_actions=next_actions or ["Proceed to next testing phase"],
            confidence_score=confidence_score,
            patterns_detected=[f"{p[0].pattern_id}" for p in patterns],
            context_used=self.context_manager.get_session_context() if self.context_manager else {}
        )
    
    def correlate_vulnerabilities(self, session_id: str, vulnerabilities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Correlate vulnerabilities to identify attack chains"""
        return self.vulnerability_correlator.correlate_findings(session_id, vulnerabilities)
    
    def generate_custom_payloads(self, vulnerability_info: Dict[str, Any], target_info: Dict[str, Any]) -> List[str]:
        """Generate custom payloads for specific vulnerabilities"""
        payloads = []
        
        vuln_type = vulnerability_info.get('type', '').lower()
        
        if 'sql' in vuln_type:
            payloads.extend([
                "' OR '1'='1",
                "' UNION SELECT user(), database(), version() --",
                "'; DROP TABLE users; --"
            ])
        elif 'xss' in vuln_type:
            payloads.extend([
                "<script>alert('XSS')</script>",
                "<img src=x onerror=alert('XSS')>",
                "javascript:alert('XSS')"
            ])
        elif 'command' in vuln_type or 'injection' in vuln_type:
            payloads.extend([
                "; cat /etc/passwd",
                "| whoami",
                "&& id"
            ])
        
        return payloads
    
    def predict_next_steps(self, current_phase: str, findings: Dict[str, Any]) -> List[str]:
        """Predict optimal next steps based on current findings"""
        next_steps = []
        
        # Base next steps on current phase
        phase_transitions = {
            'reconnaissance': [
                'Perform detailed port scanning',
                'Enumerate discovered services',
                'Check for web applications'
            ],
            'scanning': [
                'Exploit high-severity vulnerabilities',
                'Test for authentication bypass',
                'Attempt privilege escalation'
            ],
            'exploitation': [
                'Establish persistence',
                'Enumerate local system',
                'Attempt lateral movement'
            ]
        }
        
        base_steps = phase_transitions.get(current_phase, ['Continue assessment'])
        next_steps.extend(base_steps)
        
        # Customize based on findings
        if findings.get('web_application'):
            next_steps.append('Perform comprehensive web application testing')
        
        if findings.get('high_severity_vulns', 0) > 0:
            next_steps.append('Prioritize exploitation of critical vulnerabilities')
        
        if findings.get('network_services'):
            next_steps.append('Test network service configurations')
        
        return next_steps

    def set_model(self, model_id: str) -> bool:
        """Switch to a different AI model at runtime"""
        try:
            provider_instance, model_info = ProviderFactory.get_provider_for_model(model_id)
            if provider_instance.is_available():
                self.model_id = model_id
                self.active_provider = provider_instance
                self.active_model_info = model_info
                self.local_mode = False
                self.logger.info(f"Switched to model '{model_info.display_name}' via {model_info.provider.value}")
                return True
            else:
                self.logger.warning(f"Provider for model '{model_id}' is not available")
                return False
        except Exception as e:
            self.logger.error(f"Error switching to model '{model_id}': {e}")
            return False
    
    def get_current_model(self) -> Dict[str, Any]:
        """Get information about the currently active model"""
        if self.active_model_info:
            return {
                'model_id': self.model_id,
                'display_name': self.active_model_info.display_name,
                'provider': self.active_model_info.provider.value,
                'max_tokens': self.active_model_info.max_tokens,
                'context_window': self.active_model_info.context_window,
                'supports_streaming': self.active_model_info.supports_streaming,
                'supports_tools': self.active_model_info.supports_tools,
                'custom_route': getattr(self, 'custom_route', None),
            }
        return {
            'model_id': self.model_id or os.getenv('OPENAI_MODEL', 'gpt-4o'),
            'display_name': 'Unknown',
            'provider': self.provider_name or ('openai' if getattr(self, 'api_key', None) else 'local'),
            'local_mode': getattr(self, 'local_mode', False),
            'custom_route': getattr(self, 'custom_route', None),
        }
    
    def list_available_models(self) -> List[Dict[str, Any]]:
        """List all available AI models across all providers"""
        try:
            models = list_all_models()
            available = []
            for model in models:
                try:
                    provider_instance = ProviderFactory.get_provider(model.provider)
                    is_available = provider_instance.is_available()
                except Exception:
                    is_available = False
                
                available.append({
                    'model_id': model.model_id,
                    'display_name': model.display_name,
                    'provider': model.provider.value,
                    'max_tokens': model.max_tokens,
                    'context_window': model.context_window,
                    'available': is_available,
                    'description': model.description,
                })
            return available
        except Exception as e:
            self.logger.error(f"Error listing models: {e}")
            return []

    # ==================== CVE Intelligence & Attack Chaining ====================

    def lookup_cve(self, cve_id: str) -> Optional[Any]:
        """Look up threat intelligence for a specific CVE ID."""
        if not self.cve_intelligence:
            return None
        return self.cve_intelligence.lookup_cve(cve_id)

    def extract_cves(self, text: str) -> List[str]:
        """Extract all CVE identifiers from arbitrary text or scan output."""
        if not self.cve_intelligence:
            import re
            return re.findall(r'\bCVE-\d{4}-\d{4,7}\b', text, re.IGNORECASE)
        return self.cve_intelligence.extract_cves(text)

    def enrich_with_cve_intelligence(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enrich vulnerability findings with CVE, CVSS, EPSS, and CISA KEV data."""
        if not self.cve_intelligence:
            return findings
        return self.cve_intelligence.enrich_findings(findings)

    def build_attack_graph(self, vulnerabilities: List[Dict[str, Any]], target_assets: Optional[List[Dict[str, Any]]] = None) -> Any:
        """Synthesize a directed multi-stage attack graph from vulnerabilities."""
        if not self.attack_chainer:
            return None
        # Enrich before chaining if CVE intelligence is available
        enriched = self.enrich_with_cve_intelligence(vulnerabilities)
        return self.attack_chainer.synthesize_attack_graph(enriched, target_assets)

    def generate_attack_mermaid(self, vulnerabilities: List[Dict[str, Any]]) -> str:
        """Generate a Mermaid flowchart visualizing the synthesized attack chains."""
        graph = self.build_attack_graph(vulnerabilities)
        if graph and hasattr(graph, 'to_mermaid'):
            return graph.to_mermaid()
        return "```mermaid\nflowchart TD\n    A[No attack paths synthesized]\n```"

    def get_defensive_chokepoints(self, vulnerabilities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Compute critical defensive chokepoints across all synthesized attack paths."""
        graph = self.build_attack_graph(vulnerabilities)
        if graph and hasattr(graph, 'find_critical_chokepoints'):
            return graph.find_critical_chokepoints()
        return []

    def get_cisa_kev_report(self, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a focused CISA KEV compliance and threat triage report."""
        if not self.cve_intelligence:
            return {"total_kev_count": 0, "requires_immediate_action": False, "vulnerabilities": []}
        enriched = self.enrich_with_cve_intelligence(findings)
        return self.cve_intelligence.get_cisa_kev_summary(enriched)

    def get_d3fend_countermeasures(self, vulnerabilities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Map synthesized attack paths to official MITRE D3FEND defensive countermeasures."""
        graph = self.build_attack_graph(vulnerabilities)
        if graph and hasattr(graph, 'to_d3fend_matrix'):
            return graph.to_d3fend_matrix()
        return []

    def export_sigma_rules(self, vulnerabilities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate Detection-as-Code Sigma Rules and Splunk SPL queries for detected attack paths."""
        graph = self.build_attack_graph(vulnerabilities)
        if graph and hasattr(graph, 'export_sigma_rules'):
            return graph.export_sigma_rules()
        return []

    def generate_remediation_playbooks(self, vulnerabilities: List[Dict[str, Any]]) -> Dict[str, str]:
        """Generate automated Ansible and Bash remediation playbooks for critical defensive chokepoints."""
        graph = self.build_attack_graph(vulnerabilities)
        if graph and hasattr(graph, 'generate_ansible_playbook') and hasattr(graph, 'generate_hardening_script'):
            return {
                "ansible": graph.generate_ansible_playbook(),
                "bash": graph.generate_hardening_script()
            }
        return {"ansible": "", "bash": ""}

    def analyze_cloud_posture(self, cspm_data: Any) -> Dict[str, Any]:
        """Synthesize AI threat model & blast radius analysis from Cloud Security Posture (CSPM) audit findings."""
        findings_list = []
        env_name = "Cloud Environment"
        compliance_score = 100.0

        if hasattr(cspm_data, "findings"):
            findings_list = [f.to_dict() if hasattr(f, "to_dict") else f for f in cspm_data.findings]
            env_name = getattr(cspm_data, "environment_name", env_name)
            compliance_score = getattr(cspm_data, "compliance_score", compliance_score)
        elif isinstance(cspm_data, dict):
            findings_list = cspm_data.get("findings", [])
            env_name = cspm_data.get("environment_name", env_name)
            compliance_score = cspm_data.get("compliance_score", compliance_score)
        elif isinstance(cspm_data, list):
            findings_list = [f.to_dict() if hasattr(f, "to_dict") else f for f in cspm_data]

        criticals = [f for f in findings_list if f.get("severity") in ("critical", "CRITICAL")]
        highs = [f for f in findings_list if f.get("severity") in ("high", "HIGH")]

        # Determine composite blast radius
        blast_radius = "LOW"
        if len(criticals) >= 2 or (len(criticals) >= 1 and len(highs) >= 2):
            blast_radius = "TENANT_TAKEOVER_RISK"
        elif len(criticals) >= 1 or len(highs) >= 2:
            blast_radius = "ACCOUNT_COMPROMISE_RISK"
        elif len(highs) >= 1:
            blast_radius = "CONTAINED_WORKLOAD_RISK"

        # Threat chaining narrative
        scenarios: List[str] = []
        if any("S3" in f.get("service", "") or "Storage" in f.get("category", "") for f in criticals):
            scenarios.append("Public Object Store Exfiltration: Direct unauthenticated data scraping without credentials.")
        if any("SecurityGroups" in f.get("service", "") or "022" in f.get("finding_id", "") for f in criticals):
            scenarios.append("Perimeter Breach via Exposed Management Port: SSH brute-forcing or credential stuffing to gain initial access.")
        if any("PSS" in f.get("finding_id", "") or "Privileged" in f.get("title", "") for f in criticals):
            scenarios.append("Kubernetes Host Node Compromise: Privileged container escape accessing host root filesystem and containerd socket.")
        if any("IAM" in f.get("service", "") or "RBAC" in f.get("service", "") for f in criticals + highs):
            scenarios.append("Lateral Privilege Escalation: Wildcard cloud policies or cluster-admin bindings enabling full control over cloud control plane.")

        if not scenarios:
            scenarios.append("Isolated misconfigurations with low lateral movement potential.")

        return {
            "environment_name": env_name,
            "compliance_score": compliance_score,
            "evaluated_findings_count": len(findings_list),
            "critical_risk_count": len(criticals),
            "high_risk_count": len(highs),
            "assessed_blast_radius": blast_radius,
            "synthesized_attack_scenarios": scenarios,
            "ai_hardening_priority": [
                "Sever exposed perimeter ingress ports (SSH/RDP/Databases) immediately.",
                "Enforce S3 Block Public Access and enable KMS key rotation.",
                "Apply Pod Security Standards (Restricted Profile) blocking privileged containers and hostPath mounts.",
                "Adopt Least Privilege IAM roles with ABAC/RBAC condition keys."
            ]
        }
