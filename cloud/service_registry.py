#!/usr/bin/env python3
# SecScan AI core module
"""
Service Registry for SecScan AI Microservices
Handles service discovery, registration, and health checking
"""

import os
import json
import time
import threading
import logging
import hashlib
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor

try:
    import consul

    CONSUL_AVAILABLE = True
except ImportError:
    CONSUL_AVAILABLE = False
    logging.warning(
        "Consul client not available. Install with: pip install python-consul"
    )

try:
    import etcd3

    ETCD_AVAILABLE = True
except ImportError:
    ETCD_AVAILABLE = False
    logging.warning("etcd3 client not available. Install with: pip install etcd3")


@dataclass
class ServiceInstance:
    service_name: str
    instance_id: str
    host: str
    port: int
    health_endpoint: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    ttl: int = 30
    last_heartbeat: Optional[datetime] = None
    status: str = "unknown"  # healthy, unhealthy, unknown


@dataclass
class ServiceHealth:
    instance_id: str
    status: str
    last_check: datetime
    response_time: float
    error_message: Optional[str] = None


class ServiceRegistry:
    """Service registry for microservices discovery and health management"""

    def __init__(self, backend: str = "memory", **kwargs):
        self.backend = backend
        self.logger = logging.getLogger(__name__)
        self.services = {}  # In-memory storage
        self.health_checks = {}
        self.health_check_interval = 10  # seconds
        self.service_ttl = 30  # seconds
        self.running = False
        self.health_thread = None
        self.cleanup_thread = None

        # Initialize backend
        if backend == "consul" and CONSUL_AVAILABLE:
            self.consul_client = consul.Consul(
                host=kwargs.get("host", "localhost"), port=kwargs.get("port", 8500)
            )
        elif backend == "etcd" and ETCD_AVAILABLE:
            self.etcd_client = etcd3.client(
                host=kwargs.get("host", "localhost"), port=kwargs.get("port", 2379)
            )
        else:
            self.backend = "memory"

        self.logger.info(f"Service registry initialized with {self.backend} backend")

    def start(self):
        """Start the service registry"""
        self.running = True

        # Start health checking thread
        self.health_thread = threading.Thread(
            target=self._health_check_loop, daemon=True
        )
        self.health_thread.start()

        # Start cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()

        self.logger.info("Service registry started")

    def stop(self):
        """Stop the service registry"""
        self.running = False

        if self.health_thread:
            self.health_thread.join(timeout=5)

        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=5)

        self.logger.info("Service registry stopped")

    def register_service(self, service: ServiceInstance) -> bool:
        """Register a service instance"""
        try:
            service.last_heartbeat = datetime.utcnow()
            service.instance_id = service.instance_id or self._generate_instance_id(
                service
            )

            if self.backend == "consul":
                return self._register_consul(service)
            elif self.backend == "etcd":
                return self._register_etcd(service)
            else:
                return self._register_memory(service)

        except Exception as e:
            self.logger.error(f"Failed to register service {service.service_name}: {e}")
            return False

    def deregister_service(self, service_name: str, instance_id: str) -> bool:
        """Deregister a service instance"""
        try:
            if self.backend == "consul":
                return self._deregister_consul(service_name, instance_id)
            elif self.backend == "etcd":
                return self._deregister_etcd(service_name, instance_id)
            else:
                return self._deregister_memory(service_name, instance_id)

        except Exception as e:
            self.logger.error(
                f"Failed to deregister service {service_name}:{instance_id}: {e}"
            )
            return False

    def discover_services(
        self, service_name: str, healthy_only: bool = True
    ) -> List[ServiceInstance]:
        """Discover instances of a service"""
        try:
            if self.backend == "consul":
                return self._discover_consul(service_name, healthy_only)
            elif self.backend == "etcd":
                return self._discover_etcd(service_name, healthy_only)
            else:
                return self._discover_memory(service_name, healthy_only)

        except Exception as e:
            self.logger.error(f"Failed to discover services for {service_name}: {e}")
            return []

    def get_service_instance(
        self, service_name: str, instance_id: str
    ) -> Optional[ServiceInstance]:
        """Get a specific service instance"""
        try:
            instances = self.discover_services(service_name, healthy_only=False)
            for instance in instances:
                if instance.instance_id == instance_id:
                    return instance
            return None

        except Exception as e:
            self.logger.error(
                f"Failed to get service instance {service_name}:{instance_id}: {e}"
            )
            return None

    def list_services(self) -> Dict[str, List[ServiceInstance]]:
        """List all registered services"""
        try:
            if self.backend == "consul":
                return self._list_consul()
            elif self.backend == "etcd":
                return self._list_etcd()
            else:
                return self._list_memory()

        except Exception as e:
            self.logger.error(f"Failed to list services: {e}")
            return {}

    def heartbeat(self, service_name: str, instance_id: str) -> bool:
        """Send heartbeat for a service instance"""
        try:
            if self.backend == "memory":
                if service_name in self.services:
                    for instance in self.services[service_name]:
                        if instance.instance_id == instance_id:
                            instance.last_heartbeat = datetime.utcnow()
                            return True
            # For consul and etcd, heartbeat is handled differently
            return True

        except Exception as e:
            self.logger.error(
                f"Failed to send heartbeat for {service_name}:{instance_id}: {e}"
            )
            return False

    def _generate_instance_id(self, service: ServiceInstance) -> str:
        """Generate a unique instance ID"""
        unique_string = (
            f"{service.service_name}-{service.host}-{service.port}-{int(time.time())}"
        )
        return hashlib.md5(unique_string.encode()).hexdigest()[:16]

    # Memory backend implementations
    def _register_memory(self, service: ServiceInstance) -> bool:
        """Register service in memory"""
        if service.service_name not in self.services:
            self.services[service.service_name] = []

        # Remove existing instance with same ID
        self.services[service.service_name] = [
            s
            for s in self.services[service.service_name]
            if s.instance_id != service.instance_id
        ]

        # Add new instance
        self.services[service.service_name].append(service)

        self.logger.info(
            f"Registered service {service.service_name}:{service.instance_id}"
        )
        return True

    def _deregister_memory(self, service_name: str, instance_id: str) -> bool:
        """Deregister service from memory"""
        if service_name in self.services:
            original_count = len(self.services[service_name])
            self.services[service_name] = [
                s for s in self.services[service_name] if s.instance_id != instance_id
            ]

            if len(self.services[service_name]) < original_count:
                self.logger.info(f"Deregistered service {service_name}:{instance_id}")
                return True

        return False

    def _discover_memory(
        self, service_name: str, healthy_only: bool
    ) -> List[ServiceInstance]:
        """Discover services from memory"""
        instances = self.services.get(service_name, [])

        if healthy_only:
            instances = [s for s in instances if s.status == "healthy"]

        return instances

    def _list_memory(self) -> Dict[str, List[ServiceInstance]]:
        """List all services from memory"""
        return self.services.copy()

    # Consul backend implementations
    def _register_consul(self, service: ServiceInstance) -> bool:
        """Register service with Consul"""
        if not CONSUL_AVAILABLE:
            return False

        try:
            check = None
            if service.health_endpoint:
                check = consul.Check.http(
                    f"http://{service.host}:{service.port}{service.health_endpoint}",
                    interval=f"{self.health_check_interval}s",
                    timeout="10s",
                )

            self.consul_client.agent.service.register(
                name=service.service_name,
                service_id=service.instance_id,
                address=service.host,
                port=service.port,
                tags=service.tags or [],
                check=check,
                meta=service.metadata or {},
            )

            self.logger.info(
                f"Registered service {service.service_name}:{service.instance_id} with Consul"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to register with Consul: {e}")
            return False

    def _deregister_consul(self, service_name: str, instance_id: str) -> bool:
        """Deregister service from Consul"""
        if not CONSUL_AVAILABLE:
            return False

        try:
            self.consul_client.agent.service.deregister(instance_id)
            self.logger.info(
                f"Deregistered service {service_name}:{instance_id} from Consul"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to deregister from Consul: {e}")
            return False

    def _discover_consul(
        self, service_name: str, healthy_only: bool
    ) -> List[ServiceInstance]:
        """Discover services from Consul"""
        if not CONSUL_AVAILABLE:
            return []

        try:
            _, services = self.consul_client.health.service(
                service_name, passing=healthy_only
            )

            instances = []
            for service_data in services:
                service_info = service_data["Service"]
                health_info = service_data.get("Checks", [])

                status = "healthy"
                if health_info:
                    # Check if all health checks are passing
                    if not all(check["Status"] == "passing" for check in health_info):
                        status = "unhealthy"

                instance = ServiceInstance(
                    service_name=service_info["Service"],
                    instance_id=service_info["ID"],
                    host=service_info["Address"],
                    port=service_info["Port"],
                    metadata=service_info.get("Meta", {}),
                    tags=service_info.get("Tags", []),
                    status=status,
                )
                instances.append(instance)

            return instances

        except Exception as e:
            self.logger.error(f"Failed to discover from Consul: {e}")
            return []

    def _list_consul(self) -> Dict[str, List[ServiceInstance]]:
        """List all services from Consul"""
        if not CONSUL_AVAILABLE:
            return {}

        try:
            _, services = self.consul_client.agent.services()

            service_map = {}
            for service_id, service_info in services.items():
                service_name = service_info["Service"]

                if service_name not in service_map:
                    service_map[service_name] = []

                instance = ServiceInstance(
                    service_name=service_name,
                    instance_id=service_id,
                    host=service_info["Address"],
                    port=service_info["Port"],
                    metadata=service_info.get("Meta", {}),
                    tags=service_info.get("Tags", []),
                )
                service_map[service_name].append(instance)

            return service_map

        except Exception as e:
            self.logger.error(f"Failed to list from Consul: {e}")
            return {}

    # etcd backend implementations (basic implementation)
    def _register_etcd(self, service: ServiceInstance) -> bool:
        """Register service with etcd"""
        if not ETCD_AVAILABLE:
            return False

        try:
            key = f"/services/{service.service_name}/{service.instance_id}"
            value = json.dumps(asdict(service), default=str)

            self.etcd_client.put(key, value, lease=self.etcd_client.lease(service.ttl))

            self.logger.info(
                f"Registered service {service.service_name}:{service.instance_id} with etcd"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to register with etcd: {e}")
            return False

    def _deregister_etcd(self, service_name: str, instance_id: str) -> bool:
        """Deregister service from etcd"""
        if not ETCD_AVAILABLE:
            return False

        try:
            key = f"/services/{service_name}/{instance_id}"
            self.etcd_client.delete(key)

            self.logger.info(
                f"Deregistered service {service_name}:{instance_id} from etcd"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to deregister from etcd: {e}")
            return False

    def _discover_etcd(
        self, service_name: str, healthy_only: bool
    ) -> List[ServiceInstance]:
        """Discover services from etcd"""
        if not ETCD_AVAILABLE:
            return []

        try:
            key_prefix = f"/services/{service_name}/"
            values = self.etcd_client.get_prefix(key_prefix)

            instances = []
            for value, _ in values:
                if value:
                    try:
                        service_data = json.loads(value.decode("utf-8"))
                        instance = ServiceInstance(**service_data)

                        if not healthy_only or instance.status == "healthy":
                            instances.append(instance)

                    except Exception as e:
                        self.logger.warning(f"Failed to parse service data: {e}")
                        continue

            return instances

        except Exception as e:
            self.logger.error(f"Failed to discover from etcd: {e}")
            return []

    def _list_etcd(self) -> Dict[str, List[ServiceInstance]]:
        """List all services from etcd"""
        if not ETCD_AVAILABLE:
            return {}

        try:
            values = self.etcd_client.get_prefix("/services/")

            service_map = {}
            for value, metadata in values:
                if value:
                    try:
                        service_data = json.loads(value.decode("utf-8"))
                        instance = ServiceInstance(**service_data)

                        if instance.service_name not in service_map:
                            service_map[instance.service_name] = []

                        service_map[instance.service_name].append(instance)

                    except Exception as e:
                        self.logger.warning(f"Failed to parse service data: {e}")
                        continue

            return service_map

        except Exception as e:
            self.logger.error(f"Failed to list from etcd: {e}")
            return {}

    def _health_check_loop(self):
        """Background thread for health checking"""
        while self.running:
            try:
                self._perform_health_checks()
                time.sleep(self.health_check_interval)
            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")
                time.sleep(self.health_check_interval)

    def _perform_health_checks(self):
        """Perform health checks on registered services"""
        if self.backend != "memory":
            return  # Health checks handled by backend for consul/etcd

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []

            for service_name, instances in self.services.items():
                for instance in instances:
                    if instance.health_endpoint:
                        future = executor.submit(self._check_instance_health, instance)
                        futures.append((future, instance))

            # Collect results
            for future, instance in futures:
                try:
                    health = future.result(timeout=10)
                    instance.status = health.status
                    self.health_checks[instance.instance_id] = health
                except Exception as e:
                    instance.status = "unhealthy"
                    self.health_checks[instance.instance_id] = ServiceHealth(
                        instance_id=instance.instance_id,
                        status="unhealthy",
                        last_check=datetime.utcnow(),
                        response_time=0,
                        error_message=str(e),
                    )

    def _check_instance_health(self, instance: ServiceInstance) -> ServiceHealth:
        """Check health of a single instance"""
        start_time = time.time()

        try:
            url = f"http://{instance.host}:{instance.port}{instance.health_endpoint}"

            # Use requests for synchronous health checks
            import requests

            response = requests.get(url, timeout=5)
            response_time = time.time() - start_time

            status = "healthy" if response.status_code == 200 else "unhealthy"

            return ServiceHealth(
                instance_id=instance.instance_id,
                status=status,
                last_check=datetime.utcnow(),
                response_time=response_time,
            )

        except Exception as e:
            response_time = time.time() - start_time

            return ServiceHealth(
                instance_id=instance.instance_id,
                status="unhealthy",
                last_check=datetime.utcnow(),
                response_time=response_time,
                error_message=str(e),
            )

    def _cleanup_loop(self):
        """Background thread for cleaning up expired services"""
        while self.running:
            try:
                self._cleanup_expired_services()
                time.sleep(30)  # Cleanup every 30 seconds
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
                time.sleep(30)

    def _cleanup_expired_services(self):
        """Remove expired services (memory backend only)"""
        if self.backend != "memory":
            return

        current_time = datetime.utcnow()
        expired_threshold = timedelta(seconds=self.service_ttl * 2)

        for service_name in list(self.services.keys()):
            instances = self.services[service_name]
            active_instances = []

            for instance in instances:
                if instance.last_heartbeat:
                    time_since_heartbeat = current_time - instance.last_heartbeat
                    if time_since_heartbeat < expired_threshold:
                        active_instances.append(instance)
                    else:
                        self.logger.info(
                            f"Removing expired service {service_name}:{instance.instance_id}"
                        )
                else:
                    # No heartbeat recorded, consider expired
                    self.logger.info(
                        f"Removing service with no heartbeat {service_name}:{instance.instance_id}"
                    )

            if active_instances:
                self.services[service_name] = active_instances
            else:
                del self.services[service_name]

    def get_load_balancer_target(
        self, service_name: str, algorithm: str = "round_robin"
    ) -> Optional[ServiceInstance]:
        """Get a service instance for load balancing"""
        instances = self.discover_services(service_name, healthy_only=True)
        if not instances:
            return None

        if algorithm == "round_robin":
            # Simple round-robin (stateless, use hash of service name)
            index = hash(service_name + str(int(time.time() / 10))) % len(instances)
            return instances[index]
        elif algorithm == "random":
            import random

            return random.choice(instances)
        elif algorithm == "least_connections":
            # For now, just return the first one
            # In a real implementation, you'd track connection counts
            return instances[0]
        else:
            return instances[0]

    def get_health_status(self, service_name: str = None) -> Dict[str, Any]:
        """Get health status of services"""
        if service_name:
            instances = self.discover_services(service_name, healthy_only=False)
            return {
                "service_name": service_name,
                "total_instances": len(instances),
                "healthy_instances": len(
                    [i for i in instances if i.status == "healthy"]
                ),
                "instances": [asdict(i) for i in instances],
            }
        else:
            all_services = self.list_services()
            summary = {}

            for svc_name, instances in all_services.items():
                summary[svc_name] = {
                    "total_instances": len(instances),
                    "healthy_instances": len(
                        [i for i in instances if i.status == "healthy"]
                    ),
                    "unhealthy_instances": len(
                        [i for i in instances if i.status == "unhealthy"]
                    ),
                }

            return summary
