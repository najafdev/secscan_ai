#!/usr/bin/env python3
# SecScan AI core module
"""
Docker Container Management for SecScan AI
Handles containerization, image building, and container orchestration
"""

import os
import json
import logging
import subprocess
import time
import tempfile
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import yaml
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import docker
    from docker.errors import DockerException, APIError, BuildError

    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    logging.warning("Docker SDK not available. Install with: pip install docker")


@dataclass
class ContainerConfig:
    name: str
    image: str
    ports: Dict[str, int]
    volumes: Dict[str, str]
    environment: Dict[str, str]
    command: Optional[str] = None
    working_dir: Optional[str] = None
    network: Optional[str] = None
    restart_policy: str = "unless-stopped"
    memory_limit: Optional[str] = None
    cpu_limit: Optional[float] = None


@dataclass
class ServiceDefinition:
    service_name: str
    container_config: ContainerConfig
    dependencies: List[str]
    health_check: Dict[str, Any]
    scaling: Dict[str, Any]


class DockerManager:
    """Manages Docker containers and images for SecScan AI services"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.client = None
        self.containers = {}
        self.images_built = set()

        if DOCKER_AVAILABLE:
            try:
                self.client = docker.from_env()
                # Test connection
                self.client.ping()
                self.logger.info("Docker client initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize Docker client: {e}")
                self.client = None
        else:
            self.logger.warning("Docker SDK not available")

    def is_docker_available(self) -> bool:
        """Check if Docker is available and running"""
        if not DOCKER_AVAILABLE or not self.client:
            return False

        try:
            self.client.ping()
            return True
        except Exception:
            return False

    def build_image(
        self,
        dockerfile_path: str,
        image_name: str,
        build_args: Optional[Dict[str, str]] = None,
        context_path: Optional[str] = None,
    ) -> bool:
        """Build a Docker image from Dockerfile"""
        if not self.is_docker_available():
            self.logger.error("Docker not available")
            return False

        try:
            if context_path is None:
                context_path = os.path.dirname(dockerfile_path)

            self.logger.info(f"Building Docker image: {image_name}")

            # Build the image
            image, build_logs = self.client.images.build(
                path=context_path,
                dockerfile=os.path.basename(dockerfile_path),
                tag=image_name,
                buildargs=build_args or {},
                rm=True,
                pull=True,
            )

            # Log build output
            for log in build_logs:
                if "stream" in log:
                    self.logger.debug(f"Build: {log['stream'].strip()}")

            self.images_built.add(image_name)
            self.logger.info(f"Successfully built image: {image_name}")
            return True

        except BuildError as e:
            self.logger.error(f"Failed to build image {image_name}: {e}")
            for log in e.build_log:
                if "stream" in log:
                    self.logger.error(f"Build error: {log['stream'].strip()}")
            return False
        except Exception as e:
            self.logger.error(f"Error building image {image_name}: {e}")
            return False

    def create_container(self, config: ContainerConfig) -> bool:
        """Create a container from configuration"""
        if not self.is_docker_available():
            self.logger.error("Docker not available")
            return False

        try:
            # Stop and remove existing container if it exists
            self.stop_container(config.name)
            self.remove_container(config.name)

            # Prepare container arguments
            container_args = {
                "image": config.image,
                "name": config.name,
                "detach": True,
                "restart_policy": {"Name": config.restart_policy},
            }

            # Add ports
            if config.ports:
                container_args["ports"] = config.ports

            # Add volumes
            if config.volumes:
                container_args["volumes"] = config.volumes

            # Add environment variables
            if config.environment:
                container_args["environment"] = config.environment

            # Add command
            if config.command:
                container_args["command"] = config.command

            # Add working directory
            if config.working_dir:
                container_args["working_dir"] = config.working_dir

            # Add network
            if config.network:
                container_args["network"] = config.network

            # Add resource limits
            if config.memory_limit or config.cpu_limit:
                container_args["mem_limit"] = config.memory_limit
                if config.cpu_limit:
                    container_args["cpu_period"] = 100000
                    container_args["cpu_quota"] = int(config.cpu_limit * 100000)

            # Create the container
            container = self.client.containers.create(**container_args)

            self.containers[config.name] = container
            self.logger.info(f"Created container: {config.name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create container {config.name}: {e}")
            return False

    def start_container(self, container_name: str) -> bool:
        """Start a container"""
        if not self.is_docker_available():
            return False

        try:
            if container_name in self.containers:
                container = self.containers[container_name]
            else:
                container = self.client.containers.get(container_name)
                self.containers[container_name] = container

            container.start()
            self.logger.info(f"Started container: {container_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to start container {container_name}: {e}")
            return False

    def stop_container(self, container_name: str) -> bool:
        """Stop a container"""
        if not self.is_docker_available():
            return False

        try:
            if container_name in self.containers:
                container = self.containers[container_name]
            else:
                try:
                    container = self.client.containers.get(container_name)
                except docker.errors.NotFound:
                    return True  # Container doesn't exist, consider it stopped

            if container.status == "running":
                container.stop(timeout=10)
                self.logger.info(f"Stopped container: {container_name}")

            return True

        except Exception as e:
            self.logger.error(f"Failed to stop container {container_name}: {e}")
            return False

    def remove_container(self, container_name: str) -> bool:
        """Remove a container"""
        if not self.is_docker_available():
            return False

        try:
            if container_name in self.containers:
                container = self.containers[container_name]
                del self.containers[container_name]
            else:
                try:
                    container = self.client.containers.get(container_name)
                except docker.errors.NotFound:
                    return True  # Container doesn't exist

            container.remove(force=True)
            self.logger.info(f"Removed container: {container_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to remove container {container_name}: {e}")
            return False

    def get_container_logs(self, container_name: str, tail: int = 100) -> str:
        """Get container logs"""
        if not self.is_docker_available():
            return ""

        try:
            if container_name in self.containers:
                container = self.containers[container_name]
            else:
                container = self.client.containers.get(container_name)

            logs = container.logs(tail=tail, timestamps=True).decode("utf-8")
            return logs

        except Exception as e:
            self.logger.error(f"Failed to get logs for container {container_name}: {e}")
            return ""

    def get_container_status(self, container_name: str) -> Dict[str, Any]:
        """Get container status and statistics"""
        if not self.is_docker_available():
            return {"status": "unavailable"}

        try:
            if container_name in self.containers:
                container = self.containers[container_name]
            else:
                container = self.client.containers.get(container_name)

            # Reload container to get current status
            container.reload()

            # Get basic info
            status_info = {
                "name": container.name,
                "status": container.status,
                "image": container.image.tags[0] if container.image.tags else "unknown",
                "created": container.attrs["Created"],
                "started": container.attrs["State"].get("StartedAt"),
                "ports": container.attrs["NetworkSettings"]["Ports"],
            }

            # Get resource usage if container is running
            if container.status == "running":
                try:
                    stats = container.stats(stream=False)
                    status_info.update(
                        {
                            "cpu_usage": self._calculate_cpu_percent(stats),
                            "memory_usage": self._calculate_memory_usage(stats),
                            "network_io": self._calculate_network_io(stats),
                        }
                    )
                except Exception:
                    pass  # Stats might not be available

            return status_info

        except docker.errors.NotFound:
            return {"status": "not_found"}
        except Exception as e:
            self.logger.error(
                f"Failed to get status for container {container_name}: {e}"
            )
            return {"status": "error", "error": str(e)}

    def _calculate_cpu_percent(self, stats: Dict) -> float:
        """Calculate CPU usage percentage from stats"""
        try:
            cpu_stats = stats["cpu_stats"]
            precpu_stats = stats["precpu_stats"]

            cpu_delta = (
                cpu_stats["cpu_usage"]["total_usage"]
                - precpu_stats["cpu_usage"]["total_usage"]
            )
            system_delta = (
                cpu_stats["system_cpu_usage"] - precpu_stats["system_cpu_usage"]
            )

            if system_delta > 0 and cpu_delta > 0:
                cpu_percent = (
                    (cpu_delta / system_delta)
                    * len(cpu_stats["cpu_usage"].get("percpu_usage", [1]))
                    * 100
                )
                return round(cpu_percent, 2)
        except (KeyError, ZeroDivisionError):
            pass
        return 0.0

    def _calculate_memory_usage(self, stats: Dict) -> Dict[str, Any]:
        """Calculate memory usage from stats"""
        try:
            memory_stats = stats["memory_stats"]
            usage = memory_stats.get("usage", 0)
            limit = memory_stats.get("limit", 0)

            return {
                "usage_bytes": usage,
                "limit_bytes": limit,
                "usage_percent": round((usage / limit) * 100, 2) if limit > 0 else 0,
            }
        except KeyError:
            return {"usage_bytes": 0, "limit_bytes": 0, "usage_percent": 0}

    def _calculate_network_io(self, stats: Dict) -> Dict[str, int]:
        """Calculate network I/O from stats"""
        try:
            networks = stats.get("networks", {})
            total_rx = sum(net.get("rx_bytes", 0) for net in networks.values())
            total_tx = sum(net.get("tx_bytes", 0) for net in networks.values())

            return {"rx_bytes": total_rx, "tx_bytes": total_tx}
        except (KeyError, AttributeError):
            return {"rx_bytes": 0, "tx_bytes": 0}

    def create_network(self, network_name: str, driver: str = "bridge") -> bool:
        """Create a Docker network"""
        if not self.is_docker_available():
            return False

        try:
            # Check if network already exists
            try:
                self.client.networks.get(network_name)
                self.logger.info(f"Network {network_name} already exists")
                return True
            except docker.errors.NotFound:
                pass

            # Create the network
            network = self.client.networks.create(
                network_name, driver=driver, check_duplicate=True
            )

            self.logger.info(f"Created network: {network_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create network {network_name}: {e}")
            return False

    def remove_network(self, network_name: str) -> bool:
        """Remove a Docker network"""
        if not self.is_docker_available():
            return False

        try:
            network = self.client.networks.get(network_name)
            network.remove()
            self.logger.info(f"Removed network: {network_name}")
            return True

        except docker.errors.NotFound:
            return True  # Network doesn't exist
        except Exception as e:
            self.logger.error(f"Failed to remove network {network_name}: {e}")
            return False

    def create_volume(self, volume_name: str, driver: str = "local") -> bool:
        """Create a Docker volume"""
        if not self.is_docker_available():
            return False

        try:
            # Check if volume already exists
            try:
                self.client.volumes.get(volume_name)
                self.logger.info(f"Volume {volume_name} already exists")
                return True
            except docker.errors.NotFound:
                pass

            # Create the volume
            volume = self.client.volumes.create(name=volume_name, driver=driver)

            self.logger.info(f"Created volume: {volume_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create volume {volume_name}: {e}")
            return False

    def remove_volume(self, volume_name: str, force: bool = False) -> bool:
        """Remove a Docker volume"""
        if not self.is_docker_available():
            return False

        try:
            volume = self.client.volumes.get(volume_name)
            volume.remove(force=force)
            self.logger.info(f"Removed volume: {volume_name}")
            return True

        except docker.errors.NotFound:
            return True  # Volume doesn't exist
        except Exception as e:
            self.logger.error(f"Failed to remove volume {volume_name}: {e}")
            return False

    def generate_dockerfile(self, service_type: str, config: Dict[str, Any]) -> str:
        """Generate Dockerfile for a service"""

        if service_type == "api":
            return self._generate_api_dockerfile(config)
        elif service_type == "worker":
            return self._generate_worker_dockerfile(config)
        elif service_type == "database":
            return self._generate_database_dockerfile(config)
        elif service_type == "web":
            return self._generate_web_dockerfile(config)
        else:
            return self._generate_base_dockerfile(config)

    def _generate_api_dockerfile(self, config: Dict[str, Any]) -> str:
        """Generate Dockerfile for API service"""
        return f"""FROM python:3.11-slim

LABEL maintainer="SecScan AI Team"
LABEL service_type="api"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    g++ \\
    libffi-dev \\
    libssl-dev \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash secscan_ai && \\
    chown -R secscan_ai:secscan_ai /app
USER secscan_ai

# Expose port
EXPOSE {config.get('port', 8000)}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \\
    CMD curl -f http://localhost:{config.get('port', 8000)}/health || exit 1

# Start command
CMD ["python", "api_server.py"]
"""

    def _generate_worker_dockerfile(self, config: Dict[str, Any]) -> str:
        """Generate Dockerfile for worker service"""
        return f"""FROM python:3.11-slim

LABEL maintainer="SecScan AI Team"
LABEL service_type="worker"

# Set working directory
WORKDIR /app

# Install system dependencies including security tools
RUN apt-get update && apt-get install -y \\
    gcc \\
    g++ \\
    libffi-dev \\
    libssl-dev \\
    nmap \\
    masscan \\
    nikto \\
    dirb \\
    gobuster \\
    sqlmap \\
    john \\
    hashcat \\
    hydra \\
    metasploit-framework \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user (but allow sudo for tools)
RUN useradd --create-home --shell /bin/bash --groups sudo secscan_ai && \\
    echo "secscan_ai ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers && \\
    chown -R secscan_ai:secscan_ai /app
USER secscan_ai

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \\
    CMD python -c "import sys; sys.exit(0)"

# Start command
CMD ["python", "worker.py"]
"""

    def _generate_database_dockerfile(self, config: Dict[str, Any]) -> str:
        """Generate Dockerfile for database service"""
        db_type = config.get("db_type", "postgresql")

        if db_type == "postgresql":
            return f"""FROM postgres:15-alpine

LABEL maintainer="SecScan AI Team"
LABEL service_type="database"

# Set environment variables
ENV POSTGRES_DB={config.get('db_name', 'secscan_ai')}
ENV POSTGRES_USER={config.get('db_user', 'secscan_ai')}
ENV POSTGRES_PASSWORD={config.get('db_password', 'secscan_ai123')}

# Copy initialization scripts
COPY init.sql /docker-entrypoint-initdb.d/

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \\
    CMD pg_isready -U $POSTGRES_USER -d $POSTGRES_DB || exit 1

# Expose port
EXPOSE 5432
"""
        else:
            return self._generate_base_dockerfile(config)

    def _generate_web_dockerfile(self, config: Dict[str, Any]) -> str:
        """Generate Dockerfile for web frontend service"""
        return f"""FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci --only=production

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Production stage
FROM nginx:alpine

LABEL maintainer="SecScan AI Team"
LABEL service_type="web"

# Copy built application
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \\
    CMD curl -f http://localhost/health || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
"""

    def _generate_base_dockerfile(self, config: Dict[str, Any]) -> str:
        """Generate base Dockerfile"""
        return f"""FROM python:3.11-slim

LABEL maintainer="SecScan AI Team"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    g++ \\
    libffi-dev \\
    libssl-dev \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash secscan_ai && \\
    chown -R secscan_ai:secscan_ai /app
USER secscan_ai

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \\
    CMD python -c "import sys; sys.exit(0)"

# Start command
CMD ["python", "main.py"]
"""

    def generate_docker_compose(self, services: List[ServiceDefinition]) -> str:
        """Generate docker-compose.yml for services"""

        compose_config = {
            "version": "3.8",
            "services": {},
            "networks": {"secscan_ai-network": {"driver": "bridge"}},
            "volumes": {},
        }

        # Generate services
        for service in services:
            config = service.container_config
            service_config = {
                "image": config.image,
                "container_name": config.name,
                "restart": config.restart_policy,
                "networks": ["secscan_ai-network"],
            }

            # Add ports
            if config.ports:
                service_config["ports"] = [
                    f"{host_port}:{container_port}"
                    for container_port, host_port in config.ports.items()
                ]

            # Add volumes
            if config.volumes:
                service_config["volumes"] = [
                    f"{host_path}:{container_path}"
                    for container_path, host_path in config.volumes.items()
                ]

                # Add named volumes to the volumes section
                for container_path, host_path in config.volumes.items():
                    if not host_path.startswith("/") and not host_path.startswith("."):
                        compose_config["volumes"][host_path] = None

            # Add environment variables
            if config.environment:
                service_config["environment"] = config.environment

            # Add command
            if config.command:
                service_config["command"] = config.command

            # Add working directory
            if config.working_dir:
                service_config["working_dir"] = config.working_dir

            # Add resource limits
            if config.memory_limit or config.cpu_limit:
                deploy_config = {}
                if config.memory_limit:
                    deploy_config["resources"] = {
                        "limits": {"memory": config.memory_limit}
                    }
                if config.cpu_limit:
                    if "resources" not in deploy_config:
                        deploy_config["resources"] = {"limits": {}}
                    deploy_config["resources"]["limits"]["cpus"] = str(config.cpu_limit)

                service_config["deploy"] = deploy_config

            # Add dependencies
            if service.dependencies:
                service_config["depends_on"] = service.dependencies

            # Add health check
            if service.health_check:
                service_config["healthcheck"] = service.health_check

            compose_config["services"][service.service_name] = service_config

        return yaml.dump(compose_config, default_flow_style=False, sort_keys=False)

    def deploy_stack(self, compose_file: str, stack_name: str = "secscan_ai") -> bool:
        """Deploy a Docker stack using docker-compose"""
        try:
            # Write compose file to temporary location
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yml", delete=False
            ) as f:
                f.write(compose_file)
                compose_path = f.name

            # Deploy using docker-compose
            cmd = ["docker-compose", "-f", compose_path, "-p", stack_name, "up", "-d"]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            self.logger.info(f"Successfully deployed stack: {stack_name}")
            self.logger.debug(f"Deploy output: {result.stdout}")

            # Clean up temporary file
            os.unlink(compose_path)
            return True

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to deploy stack {stack_name}: {e}")
            self.logger.error(f"Error output: {e.stderr}")
            return False
        except Exception as e:
            self.logger.error(f"Error deploying stack {stack_name}: {e}")
            return False

    def cleanup(self):
        """Clean up Docker resources"""
        try:
            # Stop all containers
            for container_name in list(self.containers.keys()):
                self.stop_container(container_name)
                self.remove_container(container_name)

            # Clean up unused resources
            if self.client:
                self.client.containers.prune()
                self.client.images.prune()
                self.client.networks.prune()
                self.client.volumes.prune()

            self.logger.info("Docker cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during Docker cleanup: {e}")
