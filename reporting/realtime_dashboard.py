#!/usr/bin/env python3
# SecScan AI core module
"""
Real-time Analytics Dashboard for SecScan AI
WebSocket-based real-time monitoring and metrics
"""

import os
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import threading
import time
from concurrent.futures import ThreadPoolExecutor

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    import aiohttp
    from aiohttp import web, WSMsgType
except ImportError as e:
    logging.warning(f"WebSocket dependencies not available: {e}")

from database import get_db_manager


@dataclass
class RealTimeMetric:
    metric_name: str
    value: Any
    timestamp: datetime
    session_id: str
    metric_type: str  # counter, gauge, histogram
    tags: Dict[str, str]


@dataclass
class AlertRule:
    rule_id: str
    metric_name: str
    condition: str  # >, <, ==, !=
    threshold: float
    severity: str
    message: str
    enabled: bool


class MetricsCollector:
    """Collects and processes real-time metrics"""

    def __init__(self):
        self.metrics_buffer = []
        self.active_sessions = {}
        self.alert_rules = []
        self.logger = logging.getLogger(__name__)
        self.db = get_db_manager()

        # Initialize default alert rules
        self._initialize_alert_rules()

    def _initialize_alert_rules(self):
        """Initialize default alert rules"""
        self.alert_rules = [
            AlertRule(
                rule_id="high_vulnerability_count",
                metric_name="vulnerabilities_found",
                condition=">",
                threshold=50.0,
                severity="warning",
                message="High number of vulnerabilities detected in session",
                enabled=True,
            ),
            AlertRule(
                rule_id="critical_vulnerability_detected",
                metric_name="critical_vulnerabilities",
                condition=">",
                threshold=0.0,
                severity="critical",
                message="Critical vulnerability detected",
                enabled=True,
            ),
            AlertRule(
                rule_id="exploitation_success",
                metric_name="successful_exploits",
                condition=">",
                threshold=0.0,
                severity="high",
                message="Successful exploitation detected",
                enabled=True,
            ),
            AlertRule(
                rule_id="long_running_session",
                metric_name="session_duration",
                condition=">",
                threshold=14400.0,  # 4 hours in seconds
                severity="info",
                message="Long-running session detected",
                enabled=True,
            ),
        ]

    def collect_session_metrics(self, session_id: str) -> Dict[str, Any]:
        """Collect metrics for a specific session"""
        try:
            # Get session data from database
            session = self.db.get_pentest_session(session_id)
            if not session:
                return {}

            # Get vulnerabilities
            vulnerabilities = self.db.get_vulnerabilities_by_session(session_id)

            # Get phase results
            phase_results = self.db.get_phase_results(session_id)

            # Calculate metrics
            current_time = datetime.utcnow()
            session_duration = (current_time - session.created_at).total_seconds()

            # Count vulnerabilities by severity
            severity_counts = {}
            for vuln in vulnerabilities:
                severity = vuln.severity.lower()
                severity_counts[severity] = severity_counts.get(severity, 0) + 1

            # Calculate completion percentage
            total_phases = 6  # Standard pentesting phases
            completed_phases = len(
                [p for p in phase_results if p.status == "completed"]
            )
            completion_percentage = (completed_phases / total_phases) * 100

            # Calculate risk score
            severity_weights = {
                "critical": 10,
                "high": 7,
                "medium": 4,
                "low": 2,
                "info": 1,
            }
            risk_score = sum(
                severity_weights.get(sev, 1) * count
                for sev, count in severity_counts.items()
            )

            metrics = {
                "session_id": session_id,
                "target": session.target,
                "status": session.status,
                "session_duration": session_duration,
                "completion_percentage": completion_percentage,
                "total_vulnerabilities": len(vulnerabilities),
                "severity_breakdown": severity_counts,
                "risk_score": risk_score,
                "phases_completed": completed_phases,
                "total_phases": total_phases,
                "current_phase": self._get_current_phase(phase_results),
                "last_updated": current_time.isoformat(),
            }

            # Store metrics for alerting
            self._process_metrics_for_alerts(session_id, metrics)

            return metrics

        except Exception as e:
            self.logger.error(f"Error collecting metrics for session {session_id}: {e}")
            return {}

    def _get_current_phase(self, phase_results: List) -> str:
        """Determine current phase from results"""
        if not phase_results:
            return "Not Started"

        # Find the last running or most recent phase
        running_phases = [p for p in phase_results if p.status == "running"]
        if running_phases:
            return running_phases[-1].phase_name

        completed_phases = [p for p in phase_results if p.status == "completed"]
        if completed_phases:
            # Return next phase after the last completed one
            phase_order = [
                "reconnaissance",
                "scanning_enumeration",
                "exploitation",
                "post_exploitation",
                "reporting",
                "retesting",
            ]

            last_completed = completed_phases[-1].phase_name.lower()
            try:
                current_index = phase_order.index(last_completed)
                if current_index + 1 < len(phase_order):
                    return phase_order[current_index + 1].replace("_", " ").title()
                else:
                    return "Completed"
            except ValueError:
                return "Unknown"

        return "Starting"

    def _process_metrics_for_alerts(self, session_id: str, metrics: Dict[str, Any]):
        """Process metrics against alert rules"""
        for rule in self.alert_rules:
            if not rule.enabled:
                continue

            metric_value = metrics.get(rule.metric_name)
            if metric_value is None:
                continue

            # Check condition
            triggered = False
            if rule.condition == ">" and float(metric_value) > rule.threshold:
                triggered = True
            elif rule.condition == "<" and float(metric_value) < rule.threshold:
                triggered = True
            elif rule.condition == "==" and float(metric_value) == rule.threshold:
                triggered = True
            elif rule.condition == "!=" and float(metric_value) != rule.threshold:
                triggered = True

            if triggered:
                self._trigger_alert(session_id, rule, metric_value)

    def _trigger_alert(self, session_id: str, rule: AlertRule, value: Any):
        """Trigger an alert"""
        alert = {
            "alert_id": f"{rule.rule_id}_{session_id}_{int(time.time())}",
            "rule_id": rule.rule_id,
            "session_id": session_id,
            "severity": rule.severity,
            "message": rule.message,
            "metric_name": rule.metric_name,
            "metric_value": value,
            "threshold": rule.threshold,
            "timestamp": datetime.utcnow().isoformat(),
        }

        self.logger.warning(f"Alert triggered: {alert}")

        # Store alert (in a real implementation, you might use a queue or database)
        if not hasattr(self, "active_alerts"):
            self.active_alerts = []
        self.active_alerts.append(alert)

    def get_global_metrics(self) -> Dict[str, Any]:
        """Get global system metrics"""
        try:
            # Get recent sessions (last 24 hours)
            cutoff_time = datetime.utcnow() - timedelta(hours=24)

            # This would need to be implemented in the database manager
            # For now, return mock global metrics
            global_metrics = {
                "active_sessions": len(self.active_sessions),
                "total_sessions_24h": 5,  # Mock data
                "total_vulnerabilities_24h": 23,  # Mock data
                "critical_vulnerabilities_24h": 2,  # Mock data
                "average_session_duration": 7200,  # 2 hours
                "system_status": "healthy",
                "last_updated": datetime.utcnow().isoformat(),
            }

            return global_metrics

        except Exception as e:
            self.logger.error(f"Error collecting global metrics: {e}")
            return {}


class WebSocketManager:
    """Manages WebSocket connections for real-time updates"""

    def __init__(self, metrics_collector: MetricsCollector):
        self.connections: Set[WebSocketServerProtocol] = set()
        self.session_subscriptions: Dict[str, Set[WebSocketServerProtocol]] = {}
        self.metrics_collector = metrics_collector
        self.logger = logging.getLogger(__name__)
        self.running = False

    async def register_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Register a new WebSocket connection"""
        self.connections.add(websocket)
        self.logger.info(
            f"New WebSocket connection registered: {websocket.remote_address}"
        )

        try:
            await self.handle_client_messages(websocket)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister_connection(websocket)

    async def unregister_connection(self, websocket: WebSocketServerProtocol):
        """Unregister a WebSocket connection"""
        self.connections.discard(websocket)

        # Remove from session subscriptions
        for session_id, subscribers in self.session_subscriptions.items():
            subscribers.discard(websocket)

        self.logger.info(f"WebSocket connection unregistered")

    async def handle_client_messages(self, websocket: WebSocketServerProtocol):
        """Handle messages from WebSocket clients"""
        async for message in websocket:
            try:
                data = json.loads(message)
                await self.process_client_message(websocket, data)
            except json.JSONDecodeError:
                await websocket.send(json.dumps({"error": "Invalid JSON message"}))
            except Exception as e:
                self.logger.error(f"Error processing client message: {e}")
                await websocket.send(json.dumps({"error": str(e)}))

    async def process_client_message(
        self, websocket: WebSocketServerProtocol, data: Dict[str, Any]
    ):
        """Process a message from a WebSocket client"""
        message_type = data.get("type")

        if message_type == "subscribe_session":
            session_id = data.get("session_id")
            if session_id:
                await self.subscribe_to_session(websocket, session_id)

        elif message_type == "unsubscribe_session":
            session_id = data.get("session_id")
            if session_id:
                await self.unsubscribe_from_session(websocket, session_id)

        elif message_type == "get_metrics":
            session_id = data.get("session_id")
            if session_id:
                metrics = self.metrics_collector.collect_session_metrics(session_id)
                await websocket.send(
                    json.dumps(
                        {
                            "type": "session_metrics",
                            "session_id": session_id,
                            "data": metrics,
                        }
                    )
                )
            else:
                # Send global metrics
                metrics = self.metrics_collector.get_global_metrics()
                await websocket.send(
                    json.dumps({"type": "global_metrics", "data": metrics})
                )

    async def subscribe_to_session(
        self, websocket: WebSocketServerProtocol, session_id: str
    ):
        """Subscribe a WebSocket to session updates"""
        if session_id not in self.session_subscriptions:
            self.session_subscriptions[session_id] = set()

        self.session_subscriptions[session_id].add(websocket)

        await websocket.send(
            json.dumps({"type": "subscription_confirmed", "session_id": session_id})
        )

    async def unsubscribe_from_session(
        self, websocket: WebSocketServerProtocol, session_id: str
    ):
        """Unsubscribe a WebSocket from session updates"""
        if session_id in self.session_subscriptions:
            self.session_subscriptions[session_id].discard(websocket)

    async def broadcast_to_session_subscribers(
        self, session_id: str, message: Dict[str, Any]
    ):
        """Broadcast a message to all subscribers of a session"""
        if session_id not in self.session_subscriptions:
            return

        subscribers = self.session_subscriptions[session_id].copy()
        if not subscribers:
            return

        message_json = json.dumps(message)

        # Send to all subscribers
        disconnected = set()
        for websocket in subscribers:
            try:
                await websocket.send(message_json)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(websocket)
            except Exception as e:
                self.logger.error(f"Error sending message to WebSocket: {e}")
                disconnected.add(websocket)

        # Clean up disconnected clients
        for websocket in disconnected:
            self.session_subscriptions[session_id].discard(websocket)

    async def broadcast_global(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients"""
        if not self.connections:
            return

        message_json = json.dumps(message)
        disconnected = set()

        for websocket in self.connections.copy():
            try:
                await websocket.send(message_json)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(websocket)
            except Exception as e:
                self.logger.error(f"Error broadcasting to WebSocket: {e}")
                disconnected.add(websocket)

        # Clean up disconnected clients
        for websocket in disconnected:
            await self.unregister_connection(websocket)


class RealTimeDashboard:
    """Real-time analytics dashboard"""

    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.metrics_collector = MetricsCollector()
        self.websocket_manager = WebSocketManager(self.metrics_collector)
        self.logger = logging.getLogger(__name__)
        self.running = False
        self.update_task = None

    async def start_server(self):
        """Start the WebSocket server"""
        self.running = True

        # Start WebSocket server
        server = await websockets.serve(
            self.websocket_manager.register_connection, self.host, self.port
        )

        self.logger.info(
            f"Real-time dashboard server started on {self.host}:{self.port}"
        )

        # Start metrics update task
        self.update_task = asyncio.create_task(self.periodic_updates())

        try:
            await server.wait_closed()
        except KeyboardInterrupt:
            self.logger.info("Dashboard server stopped by user")
        finally:
            if self.update_task:
                self.update_task.cancel()
            self.running = False

    async def periodic_updates(self):
        """Send periodic updates to connected clients"""
        while self.running:
            try:
                # Send global metrics update
                global_metrics = self.metrics_collector.get_global_metrics()
                await self.websocket_manager.broadcast_global(
                    {"type": "global_metrics_update", "data": global_metrics}
                )

                # Send session-specific updates
                for session_id in self.websocket_manager.session_subscriptions.keys():
                    session_metrics = self.metrics_collector.collect_session_metrics(
                        session_id
                    )
                    if session_metrics:
                        await self.websocket_manager.broadcast_to_session_subscribers(
                            session_id,
                            {
                                "type": "session_metrics_update",
                                "session_id": session_id,
                                "data": session_metrics,
                            },
                        )

                # Wait before next update
                await asyncio.sleep(5)  # Update every 5 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in periodic updates: {e}")
                await asyncio.sleep(5)

    def start_background_server(self):
        """Start the server in a background thread"""

        def run_server():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.start_server())
            except Exception as e:
                self.logger.error(f"Error running dashboard server: {e}")
            finally:
                loop.close()

        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        return thread

    def stream_session_metrics(self, session_id: str):
        """Stream metrics for a specific session (synchronous version)"""
        while True:
            try:
                metrics = self.metrics_collector.collect_session_metrics(session_id)
                self.logger.info(f"Session {session_id} metrics: {metrics}")

                # In a real implementation, this would be handled by the WebSocket system
                time.sleep(5)  # Update every 5 seconds

            except KeyboardInterrupt:
                break
            except Exception as e:
                self.logger.error(f"Error streaming metrics: {e}")
                time.sleep(5)

    def get_dashboard_html(self) -> str:
        """Get the HTML for the dashboard interface"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SecScan AI Real-Time Dashboard</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background: #0d1117;
            color: #c9d1d9;
        }
        .header {
            background: linear-gradient(135deg, #1f6feb 0%, #388bfd 100%);
            padding: 20px;
            text-align: center;
        }
        .dashboard {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            padding: 20px;
        }
        .metric-card {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }
        .metric-title {
            font-size: 14px;
            font-weight: 600;
            color: #7c3aed;
            margin-bottom: 8px;
        }
        .metric-value {
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 4px;
        }
        .metric-change {
            font-size: 12px;
            color: #56d364;
        }
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .status-running { background: #f85149; }
        .status-completed { background: #56d364; }
        .status-paused { background: #e3b341; }
        .progress-bar {
            width: 100%;
            height: 8px;
            background: #21262d;
            border-radius: 4px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #1f6feb, #388bfd);
            transition: width 0.3s ease;
        }
        #connection-status {
            position: fixed;
            top: 10px;
            right: 10px;
            padding: 8px 16px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
        }
        .connected { background: #238636; }
        .disconnected { background: #da3633; }
    </style>
</head>
<body>
    <div id="connection-status" class="disconnected">Disconnected</div>
    
    <div class="header">
        <h1>SecScan AI Real-Time Dashboard</h1>
        <p>Live monitoring of penetration testing activities</p>
    </div>
    
    <div class="dashboard">
        <div class="metric-card">
            <div class="metric-title">Active Sessions</div>
            <div class="metric-value" id="active-sessions">-</div>
            <div class="metric-change" id="sessions-change">-</div>
        </div>
        
        <div class="metric-card">
            <div class="metric-title">Vulnerabilities Found (24h)</div>
            <div class="metric-value" id="vulnerabilities-24h">-</div>
            <div class="metric-change" id="vulns-change">-</div>
        </div>
        
        <div class="metric-card">
            <div class="metric-title">Critical Vulnerabilities</div>
            <div class="metric-value" id="critical-vulns">-</div>
            <div class="metric-change" id="critical-change">-</div>
        </div>
        
        <div class="metric-card">
            <div class="metric-title">Average Session Duration</div>
            <div class="metric-value" id="avg-duration">-</div>
            <div class="metric-change">hours</div>
        </div>
        
        <div class="metric-card">
            <div class="metric-title">System Status</div>
            <div class="metric-value" id="system-status">
                <span class="status-indicator status-running"></span>
                <span id="status-text">Loading...</span>
            </div>
        </div>
        
        <div class="metric-card">
            <div class="metric-title">Current Session Progress</div>
            <div id="session-info">
                <div>Target: <span id="current-target">-</span></div>
                <div>Phase: <span id="current-phase">-</span></div>
                <div class="progress-bar">
                    <div class="progress-fill" id="progress-fill" style="width: 0%"></div>
                </div>
                <div><span id="progress-text">0%</span> Complete</div>
            </div>
        </div>
    </div>
    
    <script>
        class DashboardClient {
            constructor() {
                this.ws = null;
                this.reconnectInterval = 5000;
                this.connect();
            }
            
            connect() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.hostname}:8765`;
                
                this.ws = new WebSocket(wsUrl);
                
                this.ws.onopen = () => {
                    console.log('Connected to dashboard server');
                    this.updateConnectionStatus(true);
                    this.requestMetrics();
                };
                
                this.ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                };
                
                this.ws.onclose = () => {
                    console.log('Disconnected from dashboard server');
                    this.updateConnectionStatus(false);
                    setTimeout(() => this.connect(), this.reconnectInterval);
                };
                
                this.ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                };
            }
            
            updateConnectionStatus(connected) {
                const status = document.getElementById('connection-status');
                status.textContent = connected ? 'Connected' : 'Disconnected';
                status.className = connected ? 'connected' : 'disconnected';
            }
            
            requestMetrics() {
                if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                    this.ws.send(JSON.stringify({
                        type: 'get_metrics'
                    }));
                }
            }
            
            handleMessage(data) {
                if (data.type === 'global_metrics' || data.type === 'global_metrics_update') {
                    this.updateGlobalMetrics(data.data);
                } else if (data.type === 'session_metrics' || data.type === 'session_metrics_update') {
                    this.updateSessionMetrics(data.data);
                }
            }
            
            updateGlobalMetrics(metrics) {
                document.getElementById('active-sessions').textContent = metrics.active_sessions || 0;
                document.getElementById('vulnerabilities-24h').textContent = metrics.total_vulnerabilities_24h || 0;
                document.getElementById('critical-vulns').textContent = metrics.critical_vulnerabilities_24h || 0;
                
                const avgDuration = metrics.average_session_duration || 0;
                document.getElementById('avg-duration').textContent = (avgDuration / 3600).toFixed(1);
                
                const statusText = document.getElementById('status-text');
                statusText.textContent = (metrics.system_status || 'Unknown').charAt(0).toUpperCase() + 
                                       (metrics.system_status || 'Unknown').slice(1);
            }
            
            updateSessionMetrics(metrics) {
                if (metrics.target) {
                    document.getElementById('current-target').textContent = metrics.target;
                }
                if (metrics.current_phase) {
                    document.getElementById('current-phase').textContent = metrics.current_phase;
                }
                if (metrics.completion_percentage !== undefined) {
                    const percentage = Math.round(metrics.completion_percentage);
                    document.getElementById('progress-fill').style.width = `${percentage}%`;
                    document.getElementById('progress-text').textContent = `${percentage}%`;
                }
            }
        }
        
        // Initialize dashboard client
        const dashboard = new DashboardClient();
        
        // Request metrics every 30 seconds
        setInterval(() => {
            dashboard.requestMetrics();
        }, 30000);
    </script>
</body>
</html>
        """
