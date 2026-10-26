#!/usr/bin/env python3
# SecScan AI core module
"""
Kubernetes Management for SecScan AI
Handles Kubernetes deployment, scaling, and orchestration
"""

import os
import json
import logging
import yaml
import time
import tempfile
import subprocess
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
import threading
from concurrent.futures import ThreadPoolExecutor

try:
    from kubernetes import client, config, watch
    from kubernetes.client.rest import ApiException

    KUBERNETES_AVAILABLE = True
except ImportError:
    KUBERNETES_AVAILABLE = False
    logging.warning(
        "Kubernetes client not available. Install with: pip install kubernetes"
    )


@dataclass
class KubernetesResource:
    api_version: str
    kind: str
    metadata: Dict[str, Any]
    spec: Dict[str, Any]
    status: Optional[Dict[str, Any]] = None


@dataclass
class DeploymentConfig:
    name: str
    image: str
    replicas: int
    ports: List[Dict[str, Any]]
    env_vars: Dict[str, str]
    resources: Dict[str, Any]
    labels: Dict[str, str]
    namespace: str = "default"


@dataclass
class ServiceConfig:
    name: str
    selector: Dict[str, str]
    ports: List[Dict[str, Any]]
    service_type: str = "ClusterIP"
    namespace: str = "default"


class KubernetesManager:
    """Manages Kubernetes resources for SecScan AI microservices"""

    def __init__(self, kubeconfig_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.api_client = None
        self.v1 = None
        self.apps_v1 = None
        self.networking_v1 = None
        self.namespace = "secscan_ai"

        if KUBERNETES_AVAILABLE:
            try:
                # Load Kubernetes configuration
                if kubeconfig_path:
                    config.load_kube_config(config_file=kubeconfig_path)
                else:
                    try:
                        # Try in-cluster config first
                        config.load_incluster_config()
                    except config.ConfigException:
                        # Fall back to kubeconfig
                        config.load_kube_config()

                # Initialize API clients
                self.api_client = client.ApiClient()
                self.v1 = client.CoreV1Api()
                self.apps_v1 = client.AppsV1Api()
                self.networking_v1 = client.NetworkingV1Api()

                self.logger.info("Kubernetes client initialized successfully")

            except Exception as e:
                self.logger.error(f"Failed to initialize Kubernetes client: {e}")
        else:
            self.logger.warning("Kubernetes client not available")

    def is_kubernetes_available(self) -> bool:
        """Check if Kubernetes is available and accessible"""
        if not KUBERNETES_AVAILABLE or not self.v1:
            return False

        try:
            # Try to list namespaces as a connectivity test
            self.v1.list_namespace(limit=1)
            return True
        except Exception:
            return False

    def create_namespace(self, namespace: str) -> bool:
        """Create a Kubernetes namespace"""
        if not self.is_kubernetes_available():
            return False

        try:
            # Check if namespace already exists
            try:
                self.v1.read_namespace(namespace)
                self.logger.info(f"Namespace {namespace} already exists")
                return True
            except ApiException as e:
                if e.status != 404:
                    raise

            # Create namespace
            ns_body = client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace))

            self.v1.create_namespace(ns_body)
            self.logger.info(f"Created namespace: {namespace}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create namespace {namespace}: {e}")
            return False

    def create_deployment(self, config: DeploymentConfig) -> bool:
        """Create a Kubernetes deployment"""
        if not self.is_kubernetes_available():
            return False

        try:
            # Ensure namespace exists
            self.create_namespace(config.namespace)

            # Create container spec
            container = client.V1Container(
                name=config.name,
                image=config.image,
                ports=[
                    client.V1ContainerPort(container_port=port["port"])
                    for port in config.ports
                ],
                env=[
                    client.V1EnvVar(name=k, value=v) for k, v in config.env_vars.items()
                ],
                resources=client.V1ResourceRequirements(
                    requests=config.resources.get("requests", {}),
                    limits=config.resources.get("limits", {}),
                ),
            )

            # Create pod template spec
            template = client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels=config.labels),
                spec=client.V1PodSpec(containers=[container]),
            )

            # Create deployment spec
            deployment_spec = client.V1DeploymentSpec(
                replicas=config.replicas,
                selector=client.V1LabelSelector(match_labels=config.labels),
                template=template,
            )

            # Create deployment
            deployment = client.V1Deployment(
                api_version="apps/v1",
                kind="Deployment",
                metadata=client.V1ObjectMeta(
                    name=config.name, namespace=config.namespace, labels=config.labels
                ),
                spec=deployment_spec,
            )

            # Apply deployment
            try:
                self.apps_v1.create_namespaced_deployment(
                    namespace=config.namespace, body=deployment
                )
                self.logger.info(f"Created deployment: {config.name}")
            except ApiException as e:
                if e.status == 409:  # Already exists
                    self.apps_v1.patch_namespaced_deployment(
                        name=config.name, namespace=config.namespace, body=deployment
                    )
                    self.logger.info(f"Updated deployment: {config.name}")
                else:
                    raise

            return True

        except Exception as e:
            self.logger.error(f"Failed to create deployment {config.name}: {e}")
            return False

    def create_service(self, config: ServiceConfig) -> bool:
        """Create a Kubernetes service"""
        if not self.is_kubernetes_available():
            return False

        try:
            # Ensure namespace exists
            self.create_namespace(config.namespace)

            # Create service ports
            service_ports = []
            for port_config in config.ports:
                service_ports.append(
                    client.V1ServicePort(
                        name=port_config.get("name", f"port-{port_config['port']}"),
                        port=port_config["port"],
                        target_port=port_config.get("target_port", port_config["port"]),
                        protocol=port_config.get("protocol", "TCP"),
                    )
                )

            # Create service spec
            service_spec = client.V1ServiceSpec(
                selector=config.selector, ports=service_ports, type=config.service_type
            )

            # Create service
            service = client.V1Service(
                api_version="v1",
                kind="Service",
                metadata=client.V1ObjectMeta(
                    name=config.name, namespace=config.namespace
                ),
                spec=service_spec,
            )

            # Apply service
            try:
                self.v1.create_namespaced_service(
                    namespace=config.namespace, body=service
                )
                self.logger.info(f"Created service: {config.name}")
            except ApiException as e:
                if e.status == 409:  # Already exists
                    self.v1.patch_namespaced_service(
                        name=config.name, namespace=config.namespace, body=service
                    )
                    self.logger.info(f"Updated service: {config.name}")
                else:
                    raise

            return True

        except Exception as e:
            self.logger.error(f"Failed to create service {config.name}: {e}")
            return False

    def create_configmap(
        self, name: str, data: Dict[str, str], namespace: str = None
    ) -> bool:
        """Create a Kubernetes ConfigMap"""
        if not self.is_kubernetes_available():
            return False

        if namespace is None:
            namespace = self.namespace

        try:
            # Ensure namespace exists
            self.create_namespace(namespace)

            # Create ConfigMap
            configmap = client.V1ConfigMap(
                api_version="v1",
                kind="ConfigMap",
                metadata=client.V1ObjectMeta(name=name, namespace=namespace),
                data=data,
            )

            # Apply ConfigMap
            try:
                self.v1.create_namespaced_config_map(
                    namespace=namespace, body=configmap
                )
                self.logger.info(f"Created ConfigMap: {name}")
            except ApiException as e:
                if e.status == 409:  # Already exists
                    self.v1.patch_namespaced_config_map(
                        name=name, namespace=namespace, body=configmap
                    )
                    self.logger.info(f"Updated ConfigMap: {name}")
                else:
                    raise

            return True

        except Exception as e:
            self.logger.error(f"Failed to create ConfigMap {name}: {e}")
            return False

    def create_secret(
        self,
        name: str,
        data: Dict[str, str],
        secret_type: str = "Opaque",
        namespace: str = None,
    ) -> bool:
        """Create a Kubernetes Secret"""
        if not self.is_kubernetes_available():
            return False

        if namespace is None:
            namespace = self.namespace

        try:
            # Ensure namespace exists
            self.create_namespace(namespace)

            # Encode data (Kubernetes expects base64-encoded strings)
            import base64

            encoded_data = {
                k: base64.b64encode(v.encode()).decode() for k, v in data.items()
            }

            # Create Secret
            secret = client.V1Secret(
                api_version="v1",
                kind="Secret",
                metadata=client.V1ObjectMeta(name=name, namespace=namespace),
                type=secret_type,
                data=encoded_data,
            )

            # Apply Secret
            try:
                self.v1.create_namespaced_secret(namespace=namespace, body=secret)
                self.logger.info(f"Created Secret: {name}")
            except ApiException as e:
                if e.status == 409:  # Already exists
                    self.v1.patch_namespaced_secret(
                        name=name, namespace=namespace, body=secret
                    )
                    self.logger.info(f"Updated Secret: {name}")
                else:
                    raise

            return True

        except Exception as e:
            self.logger.error(f"Failed to create Secret {name}: {e}")
            return False

    def create_ingress(
        self,
        name: str,
        rules: List[Dict[str, Any]],
        tls: Optional[List[Dict[str, Any]]] = None,
        namespace: str = None,
    ) -> bool:
        """Create a Kubernetes Ingress"""
        if not self.is_kubernetes_available():
            return False

        if namespace is None:
            namespace = self.namespace

        try:
            # Ensure namespace exists
            self.create_namespace(namespace)

            # Create ingress rules
            ingress_rules = []
            for rule_config in rules:
                paths = []
                for path_config in rule_config.get("paths", []):
                    path = client.V1HTTPIngressPath(
                        path=path_config["path"],
                        path_type=path_config.get("path_type", "Prefix"),
                        backend=client.V1IngressBackend(
                            service=client.V1IngressServiceBackend(
                                name=path_config["service_name"],
                                port=client.V1ServiceBackendPort(
                                    number=path_config["service_port"]
                                ),
                            )
                        ),
                    )
                    paths.append(path)

                ingress_rule = client.V1IngressRule(
                    host=rule_config.get("host"),
                    http=client.V1HTTPIngressRuleValue(paths=paths),
                )
                ingress_rules.append(ingress_rule)

            # Create ingress spec
            ingress_spec = client.V1IngressSpec(rules=ingress_rules)

            # Add TLS if specified
            if tls:
                tls_configs = []
                for tls_config in tls:
                    tls_spec = client.V1IngressTLS(
                        hosts=tls_config.get("hosts", []),
                        secret_name=tls_config.get("secret_name"),
                    )
                    tls_configs.append(tls_spec)
                ingress_spec.tls = tls_configs

            # Create ingress
            ingress = client.V1Ingress(
                api_version="networking.k8s.io/v1",
                kind="Ingress",
                metadata=client.V1ObjectMeta(name=name, namespace=namespace),
                spec=ingress_spec,
            )

            # Apply ingress
            try:
                self.networking_v1.create_namespaced_ingress(
                    namespace=namespace, body=ingress
                )
                self.logger.info(f"Created Ingress: {name}")
            except ApiException as e:
                if e.status == 409:  # Already exists
                    self.networking_v1.patch_namespaced_ingress(
                        name=name, namespace=namespace, body=ingress
                    )
                    self.logger.info(f"Updated Ingress: {name}")
                else:
                    raise

            return True

        except Exception as e:
            self.logger.error(f"Failed to create Ingress {name}: {e}")
            return False

    def scale_deployment(
        self, deployment_name: str, replicas: int, namespace: str = None
    ) -> bool:
        """Scale a deployment to the specified number of replicas"""
        if not self.is_kubernetes_available():
            return False

        if namespace is None:
            namespace = self.namespace

        try:
            # Get current deployment
            deployment = self.apps_v1.read_namespaced_deployment(
                name=deployment_name, namespace=namespace
            )

            # Update replicas
            deployment.spec.replicas = replicas

            # Patch deployment
            self.apps_v1.patch_namespaced_deployment(
                name=deployment_name, namespace=namespace, body=deployment
            )

            self.logger.info(
                f"Scaled deployment {deployment_name} to {replicas} replicas"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to scale deployment {deployment_name}: {e}")
            return False

    def get_deployment_status(
        self, deployment_name: str, namespace: str = None
    ) -> Dict[str, Any]:
        """Get the status of a deployment"""
        if not self.is_kubernetes_available():
            return {"status": "unavailable"}

        if namespace is None:
            namespace = self.namespace

        try:
            deployment = self.apps_v1.read_namespaced_deployment(
                name=deployment_name, namespace=namespace
            )

            status = {
                "name": deployment.metadata.name,
                "namespace": deployment.metadata.namespace,
                "replicas": deployment.spec.replicas,
                "ready_replicas": deployment.status.ready_replicas or 0,
                "available_replicas": deployment.status.available_replicas or 0,
                "updated_replicas": deployment.status.updated_replicas or 0,
                "conditions": [],
            }

            # Add conditions
            if deployment.status.conditions:
                for condition in deployment.status.conditions:
                    status["conditions"].append(
                        {
                            "type": condition.type,
                            "status": condition.status,
                            "reason": condition.reason,
                            "message": condition.message,
                            "last_update_time": (
                                condition.last_update_time.isoformat()
                                if condition.last_update_time
                                else None
                            ),
                        }
                    )

            return status

        except ApiException as e:
            if e.status == 404:
                return {"status": "not_found"}
            else:
                return {"status": "error", "error": str(e)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_pod_logs(
        self,
        pod_name: str,
        container: str = None,
        namespace: str = None,
        tail_lines: int = 100,
    ) -> str:
        """Get logs from a pod"""
        if not self.is_kubernetes_available():
            return ""

        if namespace is None:
            namespace = self.namespace

        try:
            logs = self.v1.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                container=container,
                tail_lines=tail_lines,
                timestamps=True,
            )
            return logs

        except Exception as e:
            self.logger.error(f"Failed to get logs for pod {pod_name}: {e}")
            return ""

    def get_pods_by_label(
        self, label_selector: str, namespace: str = None
    ) -> List[Dict[str, Any]]:
        """Get pods matching a label selector"""
        if not self.is_kubernetes_available():
            return []

        if namespace is None:
            namespace = self.namespace

        try:
            pod_list = self.v1.list_namespaced_pod(
                namespace=namespace, label_selector=label_selector
            )

            pods = []
            for pod in pod_list.items:
                pod_info = {
                    "name": pod.metadata.name,
                    "namespace": pod.metadata.namespace,
                    "phase": pod.status.phase,
                    "node_name": pod.spec.node_name,
                    "pod_ip": pod.status.pod_ip,
                    "start_time": (
                        pod.status.start_time.isoformat()
                        if pod.status.start_time
                        else None
                    ),
                    "containers": [],
                }

                # Add container info
                if pod.status.container_statuses:
                    for container_status in pod.status.container_statuses:
                        container_info = {
                            "name": container_status.name,
                            "ready": container_status.ready,
                            "restart_count": container_status.restart_count,
                            "image": container_status.image,
                        }
                        pod_info["containers"].append(container_info)

                pods.append(pod_info)

            return pods

        except Exception as e:
            self.logger.error(f"Failed to get pods with label {label_selector}: {e}")
            return []

    def delete_deployment(self, deployment_name: str, namespace: str = None) -> bool:
        """Delete a deployment"""
        if not self.is_kubernetes_available():
            return False

        if namespace is None:
            namespace = self.namespace

        try:
            self.apps_v1.delete_namespaced_deployment(
                name=deployment_name, namespace=namespace
            )
            self.logger.info(f"Deleted deployment: {deployment_name}")
            return True

        except ApiException as e:
            if e.status == 404:
                return True  # Already deleted
            else:
                self.logger.error(f"Failed to delete deployment {deployment_name}: {e}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to delete deployment {deployment_name}: {e}")
            return False

    def delete_service(self, service_name: str, namespace: str = None) -> bool:
        """Delete a service"""
        if not self.is_kubernetes_available():
            return False

        if namespace is None:
            namespace = self.namespace

        try:
            self.v1.delete_namespaced_service(name=service_name, namespace=namespace)
            self.logger.info(f"Deleted service: {service_name}")
            return True

        except ApiException as e:
            if e.status == 404:
                return True  # Already deleted
            else:
                self.logger.error(f"Failed to delete service {service_name}: {e}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to delete service {service_name}: {e}")
            return False

    def apply_yaml(self, yaml_content: str, namespace: str = None) -> bool:
        """Apply Kubernetes resources from YAML content"""
        if not self.is_kubernetes_available():
            return False

        try:
            # Parse YAML documents
            documents = list(yaml.safe_load_all(yaml_content))

            for doc in documents:
                if not doc:
                    continue

                # Set namespace if specified
                if namespace and doc.get("metadata"):
                    doc["metadata"]["namespace"] = namespace

                # Apply the resource using kubectl (simpler than handling all resource types)
                self._apply_resource_with_kubectl(doc, namespace)

            return True

        except Exception as e:
            self.logger.error(f"Failed to apply YAML: {e}")
            return False

    def _apply_resource_with_kubectl(
        self, resource: Dict[str, Any], namespace: str = None
    ):
        """Apply a resource using kubectl command"""
        try:
            # Write resource to temporary file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False
            ) as f:
                yaml.dump(resource, f)
                yaml_file = f.name

            # Build kubectl command
            cmd = ["kubectl", "apply", "-f", yaml_file]
            if namespace:
                cmd.extend(["-n", namespace])

            # Execute kubectl
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            self.logger.debug(f"Applied resource: {result.stdout}")

            # Clean up temporary file
            os.unlink(yaml_file)

        except subprocess.CalledProcessError as e:
            self.logger.error(f"kubectl apply failed: {e.stderr}")
            raise
        except Exception as e:
            self.logger.error(f"Error applying resource with kubectl: {e}")
            raise

    def generate_secscan_ai_manifests(self) -> Dict[str, str]:
        """Generate Kubernetes manifests for SecScan AI microservices"""

        manifests = {}

        # Namespace
        manifests["namespace.yaml"] = """
apiVersion: v1
kind: Namespace
metadata:
  name: secscan_ai
  labels:
    name: secscan_ai
"""

        # API Service
        manifests["api-deployment.yaml"] = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: secscan_ai-api
  namespace: secscan_ai
  labels:
    app: secscan_ai-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: secscan_ai-api
  template:
    metadata:
      labels:
        app: secscan_ai-api
    spec:
      containers:
      - name: api
        image: secscan_ai/api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: secscan_ai-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: secscan_ai-secrets
              key: redis-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: secscan_ai-api
  namespace: secscan_ai
spec:
  selector:
    app: secscan_ai-api
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
"""

        # Worker Service
        manifests["worker-deployment.yaml"] = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: secscan_ai-worker
  namespace: secscan_ai
  labels:
    app: secscan_ai-worker
spec:
  replicas: 2
  selector:
    matchLabels:
      app: secscan_ai-worker
  template:
    metadata:
      labels:
        app: secscan_ai-worker
    spec:
      containers:
      - name: worker
        image: secscan_ai/worker:latest
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: secscan_ai-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: secscan_ai-secrets
              key: redis-url
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        securityContext:
          privileged: true  # Required for some security tools
"""

        # Database Service
        manifests["database-deployment.yaml"] = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: secscan_ai-database
  namespace: secscan_ai
  labels:
    app: secscan_ai-database
spec:
  replicas: 1
  selector:
    matchLabels:
      app: secscan_ai-database
  template:
    metadata:
      labels:
        app: secscan_ai-database
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        env:
        - name: POSTGRES_DB
          value: secscan_ai
        - name: POSTGRES_USER
          value: secscan_ai
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: secscan_ai-secrets
              key: database-password
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
      volumes:
      - name: postgres-storage
        persistentVolumeClaim:
          claimName: secscan_ai-database-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: secscan_ai-database
  namespace: secscan_ai
spec:
  selector:
    app: secscan_ai-database
  ports:
  - port: 5432
    targetPort: 5432
  type: ClusterIP
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: secscan_ai-database-pvc
  namespace: secscan_ai
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
"""

        # Redis Service
        manifests["redis-deployment.yaml"] = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: secscan_ai-redis
  namespace: secscan_ai
  labels:
    app: secscan_ai-redis
spec:
  replicas: 1
  selector:
    matchLabels:
      app: secscan_ai-redis
  template:
    metadata:
      labels:
        app: secscan_ai-redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "250m"
---
apiVersion: v1
kind: Service
metadata:
  name: secscan_ai-redis
  namespace: secscan_ai
spec:
  selector:
    app: secscan_ai-redis
  ports:
  - port: 6379
    targetPort: 6379
  type: ClusterIP
"""

        # Web Frontend
        manifests["web-deployment.yaml"] = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: secscan_ai-web
  namespace: secscan_ai
  labels:
    app: secscan_ai-web
spec:
  replicas: 2
  selector:
    matchLabels:
      app: secscan_ai-web
  template:
    metadata:
      labels:
        app: secscan_ai-web
    spec:
      containers:
      - name: web
        image: secscan_ai/web:latest
        ports:
        - containerPort: 80
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "250m"
---
apiVersion: v1
kind: Service
metadata:
  name: secscan_ai-web
  namespace: secscan_ai
spec:
  selector:
    app: secscan_ai-web
  ports:
  - port: 80
    targetPort: 80
  type: ClusterIP
"""

        # Ingress
        manifests["ingress.yaml"] = """
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: secscan_ai-ingress
  namespace: secscan_ai
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - secscan_ai.example.com
    secretName: secscan_ai-tls
  rules:
  - host: secscan_ai.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: secscan_ai-web
            port:
              number: 80
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: secscan_ai-api
            port:
              number: 80
"""

        return manifests

    def cleanup(self, namespace: str = None):
        """Clean up Kubernetes resources"""
        if namespace is None:
            namespace = self.namespace

        try:
            # Delete namespace (this will delete all resources in it)
            self.v1.delete_namespace(name=namespace)
            self.logger.info(f"Deleted namespace: {namespace}")

        except ApiException as e:
            if e.status != 404:
                self.logger.error(f"Failed to delete namespace {namespace}: {e}")
        except Exception as e:
            self.logger.error(f"Error during Kubernetes cleanup: {e}")
