#!/usr/bin/env python3
# SecScan AI core module
"""
Microservice Base Class for SecScan AI
Provides common functionality for all microservices
"""

import os
import sys
import json
import time
import signal
import logging
import threading
import traceback
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor
from abc import ABC, abstractmethod

try:
    from flask import Flask, request, jsonify
    from flask_cors import CORS

    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    logging.warning("Flask not available. Install with: pip install flask flask-cors")

try:
    from fastapi import FastAPI, HTTPException, BackgroundTasks
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    logging.warning("FastAPI not available. Install with: pip install fastapi uvicorn")

from .service_registry import ServiceRegistry, ServiceInstance
from database import get_db_manager


@dataclass
class ServiceConfig:
    service_name: str
    service_type: str
    host: str = "0.0.0.0"
    port: int = 8000
    health_endpoint: str = "/health"
    metrics_endpoint: str = "/metrics"
    registry_backend: str = "memory"
    registry_host: str = "localhost"
    registry_port: int = 8500
    log_level: str = "INFO"
    debug: bool = False


class MicroserviceBase(ABC):
    """Base class for all SecScan AI microservices"""

    def __init__(self, config: ServiceConfig):
        self.config = config
        self.logger = self._setup_logging()
        self.registry = None
        self.app = None
        self.server_thread = None
        self.running = False
        self.start_time = datetime.utcnow()
        self.request_count = 0
        self.error_count = 0

        # Setup database connection
        self.db = get_db_manager()

        # Setup service registry
        self._setup_service_registry()

        # Setup web framework
        self._setup_web_framework()

        # Setup graceful shutdown
        self._setup_signal_handlers()

    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the microservice"""
        logger = logging.getLogger(self.config.service_name)
        logger.setLevel(getattr(logging, self.config.log_level.upper()))

        # Create console handler
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            f"%(asctime)s - {self.config.service_name} - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)

        if not logger.handlers:
            logger.addHandler(handler)

        return logger

    def _setup_service_registry(self):
        """Setup service registry connection"""
        try:
            self.registry = ServiceRegistry(
                backend=self.config.registry_backend,
                host=self.config.registry_host,
                port=self.config.registry_port,
            )
            self.registry.start()
            self.logger.info("Service registry initialized")
        except Exception as e:
            self.logger.error(f"Failed to setup service registry: {e}")

    def _setup_web_framework(self):
        """Setup web framework (Flask or FastAPI)"""
        if FASTAPI_AVAILABLE:
            self._setup_fastapi()
        elif FLASK_AVAILABLE:
            self._setup_flask()
        else:
            self.logger.error("No web framework available")
            raise RuntimeError("Neither Flask nor FastAPI is available")

    def _setup_fastapi(self):
        """Setup FastAPI application"""
        self.app = FastAPI(
            title=f"SecScan AI {self.config.service_name.title()} Service",
            description=f"SecScan AI {self.config.service_type} microservice",
            version="1.0.0",
        )

        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Add middleware
        @self.app.middleware("http")
        async def request_logging_middleware(request, call_next):
            start_time = time.time()
            self.request_count += 1

            try:
                response = await call_next(request)
                process_time = time.time() - start_time
                self.logger.info(
                    f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s"
                )
                return response
            except Exception as e:
                self.error_count += 1
                self.logger.error(f"Request error: {e}")
                raise

        # Add default endpoints
        @self.app.get("/health")
        async def health_check():
            return self._get_health_status()

        @self.app.get("/metrics")
        async def metrics():
            return self._get_metrics()

        @self.app.get("/info")
        async def service_info():
            return self._get_service_info()

        # Register custom routes
        self.register_routes()

    def _setup_flask(self):
        """Setup Flask application"""
        self.app = Flask(self.config.service_name)
        CORS(self.app)

        # Add request logging
        @self.app.before_request
        def before_request():
            request.start_time = time.time()
            self.request_count += 1

        @self.app.after_request
        def after_request(response):
            if hasattr(request, "start_time"):
                process_time = time.time() - request.start_time
                self.logger.info(
                    f"{request.method} {request.path} - {response.status_code} - {process_time:.3f}s"
                )
            return response

        # Add default endpoints
        @self.app.route("/health", methods=["GET"])
        def health_check():
            return jsonify(self._get_health_status())

        @self.app.route("/metrics", methods=["GET"])
        def metrics():
            return jsonify(self._get_metrics())

        @self.app.route("/info", methods=["GET"])
        def service_info():
            return jsonify(self._get_service_info())

        # Register custom routes
        self.register_routes()

    def _setup_signal_handlers(self):
        """Setup graceful shutdown signal handlers"""

        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, shutting down gracefully...")
            self.shutdown()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    @abstractmethod
    def register_routes(self):
        """Register service-specific routes"""
        pass

    @abstractmethod
    def initialize(self):
        """Initialize service-specific components"""
        pass

    @abstractmethod
    def cleanup(self):
        """Cleanup service-specific resources"""
        pass

    def start(self):
        """Start the microservice"""
        try:
            self.logger.info(f"Starting {self.config.service_name} service...")

            # Initialize service-specific components
            self.initialize()

            # Register with service registry
            if self.registry:
                service_instance = ServiceInstance(
                    service_name=self.config.service_name,
                    instance_id=f"{self.config.service_name}-{os.getpid()}",
                    host=self.config.host,
                    port=self.config.port,
                    health_endpoint=self.config.health_endpoint,
                    metadata={
                        "service_type": self.config.service_type,
                        "version": "1.0.0",
                        "start_time": self.start_time.isoformat(),
                    },
                    tags=[self.config.service_type, "secscan_ai"],
                )

                self.registry.register_service(service_instance)

                # Start heartbeat thread
                self.heartbeat_thread = threading.Thread(
                    target=self._heartbeat_loop, daemon=True
                )
                self.heartbeat_thread.start()

            self.running = True

            # Start web server
            if FASTAPI_AVAILABLE and isinstance(self.app, FastAPI):
                self._start_fastapi_server()
            elif FLASK_AVAILABLE:
                self._start_flask_server()

        except Exception as e:
            self.logger.error(f"Failed to start service: {e}")
            self.shutdown()
            raise

    def _start_fastapi_server(self):
        """Start FastAPI server"""
        try:
            uvicorn.run(
                self.app,
                host=self.config.host,
                port=self.config.port,
                log_level="info" if self.config.debug else "warning",
                access_log=False,
            )
        except Exception as e:
            self.logger.error(f"FastAPI server error: {e}")
            self.shutdown()

    def _start_flask_server(self):
        """Start Flask server"""
        try:
            self.app.run(
                host=self.config.host,
                port=self.config.port,
                debug=self.config.debug,
                use_reloader=False,
                threaded=True,
            )
        except Exception as e:
            self.logger.error(f"Flask server error: {e}")
            self.shutdown()

    def _heartbeat_loop(self):
        """Send periodic heartbeats to service registry"""
        while self.running:
            try:
                if self.registry:
                    self.registry.heartbeat(
                        self.config.service_name,
                        f"{self.config.service_name}-{os.getpid()}",
                    )
                time.sleep(10)  # Heartbeat every 10 seconds
            except Exception as e:
                self.logger.error(f"Heartbeat error: {e}")
                time.sleep(10)

    def shutdown(self):
        """Shutdown the microservice gracefully"""
        if not self.running:
            return

        self.logger.info("Shutting down service...")
        self.running = False

        try:
            # Deregister from service registry
            if self.registry:
                self.registry.deregister_service(
                    self.config.service_name,
                    f"{self.config.service_name}-{os.getpid()}",
                )
                self.registry.stop()

            # Cleanup service-specific resources
            self.cleanup()

            self.logger.info("Service shutdown complete")

        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")

    def _get_health_status(self) -> Dict[str, Any]:
        """Get service health status"""
        uptime = (datetime.utcnow() - self.start_time).total_seconds()

        # Check database connectivity
        db_healthy = True
        try:
            if self.db:
                # Simple database health check
                self.db.get_connection()
        except Exception:
            db_healthy = False

        status = {
            "status": "healthy" if db_healthy else "unhealthy",
            "service_name": self.config.service_name,
            "service_type": self.config.service_type,
            "uptime_seconds": uptime,
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "checks": {"database": "healthy" if db_healthy else "unhealthy"},
        }

        return status

    def _get_metrics(self) -> Dict[str, Any]:
        """Get service metrics"""
        uptime = (datetime.utcnow() - self.start_time).total_seconds()

        metrics = {
            "service_name": self.config.service_name,
            "uptime_seconds": uptime,
            "request_count": self.request_count,
            "error_count": self.error_count,
            "error_rate": (self.error_count / max(self.request_count, 1)) * 100,
            "timestamp": datetime.utcnow().isoformat(),
        }

        return metrics

    def _get_service_info(self) -> Dict[str, Any]:
        """Get service information"""
        return {
            "service_name": self.config.service_name,
            "service_type": self.config.service_type,
            "version": "1.0.0",
            "host": self.config.host,
            "port": self.config.port,
            "start_time": self.start_time.isoformat(),
            "endpoints": {
                "health": self.config.health_endpoint,
                "metrics": self.config.metrics_endpoint,
            },
        }

    def call_service(
        self,
        service_name: str,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict] = None,
        timeout: int = 30,
    ) -> Optional[Dict[str, Any]]:
        """Call another microservice"""
        try:
            # Discover service instance
            if not self.registry:
                self.logger.error("Service registry not available")
                return None

            instance = self.registry.get_load_balancer_target(service_name)
            if not instance:
                self.logger.error(
                    f"No healthy instances found for service: {service_name}"
                )
                return None

            # Make HTTP request
            import requests

            url = f"http://{instance.host}:{instance.port}{endpoint}"

            if method.upper() == "GET":
                response = requests.get(url, params=data, timeout=timeout)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, timeout=timeout)
            elif method.upper() == "PUT":
                response = requests.put(url, json=data, timeout=timeout)
            elif method.upper() == "DELETE":
                response = requests.delete(url, timeout=timeout)
            else:
                self.logger.error(f"Unsupported HTTP method: {method}")
                return None

            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(
                    f"Service call failed: {response.status_code} - {response.text}"
                )
                return None

        except Exception as e:
            self.logger.error(f"Error calling service {service_name}: {e}")
            return None

    def publish_event(self, event_type: str, event_data: Dict[str, Any]):
        """Publish an event (basic implementation)"""
        try:
            event = {
                "event_type": event_type,
                "source_service": self.config.service_name,
                "timestamp": datetime.utcnow().isoformat(),
                "data": event_data,
            }

            # In a real implementation, this would publish to a message queue
            self.logger.info(f"Event published: {event_type}")

        except Exception as e:
            self.logger.error(f"Error publishing event: {e}")

    def run(self):
        """Run the microservice (blocking)"""
        try:
            self.start()
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        except Exception as e:
            self.logger.error(f"Service error: {e}")
            traceback.print_exc()
        finally:
            self.shutdown()


class WorkerService(MicroserviceBase):
    """Base class for worker services"""

    def __init__(self, config: ServiceConfig):
        super().__init__(config)
        self.task_queue = []
        self.worker_pool = None
        self.max_workers = 5

    def initialize(self):
        """Initialize worker service"""
        self.worker_pool = ThreadPoolExecutor(max_workers=self.max_workers)
        self.logger.info(f"Worker service initialized with {self.max_workers} workers")

    def cleanup(self):
        """Cleanup worker service"""
        if self.worker_pool:
            self.worker_pool.shutdown(wait=True)
            self.logger.info("Worker pool shutdown complete")

    def submit_task(self, task_func: Callable, *args, **kwargs):
        """Submit a task to the worker pool"""
        if self.worker_pool:
            future = self.worker_pool.submit(task_func, *args, **kwargs)
            return future
        else:
            self.logger.error("Worker pool not initialized")
            return None

    @abstractmethod
    def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a task (to be implemented by subclasses)"""
        pass


class APIService(MicroserviceBase):
    """Base class for API services"""

    def __init__(self, config: ServiceConfig):
        super().__init__(config)
        self.rate_limits = {}
        self.api_keys = set()

    def initialize(self):
        """Initialize API service"""
        self.logger.info("API service initialized")

    def cleanup(self):
        """Cleanup API service"""
        self.logger.info("API service cleanup complete")

    def check_rate_limit(
        self, client_id: str, limit: int = 100, window: int = 3600
    ) -> bool:
        """Check if client is within rate limit"""
        current_time = time.time()
        window_start = current_time - window

        if client_id not in self.rate_limits:
            self.rate_limits[client_id] = []

        # Clean old requests
        self.rate_limits[client_id] = [
            req_time
            for req_time in self.rate_limits[client_id]
            if req_time > window_start
        ]

        # Check limit
        if len(self.rate_limits[client_id]) >= limit:
            return False

        # Add current request
        self.rate_limits[client_id].append(current_time)
        return True

    def validate_api_key(self, api_key: str) -> bool:
        """Validate API key"""
        return (
            api_key in self.api_keys or not self.api_keys
        )  # Allow all if no keys configured
