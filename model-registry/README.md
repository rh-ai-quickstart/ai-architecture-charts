# Model Registry Helm Chart

A Helm chart for deploying OpenDataHub Model Registry on OpenShift clusters.

## Overview

This chart deploys a Model Registry instance with MySQL backend, providing a centralized repository for managing ML models. It integrates with OpenShift AI and supports Istio service mesh for advanced routing and security.

## Prerequisites

- Kubernetes 1.19+ or OpenShift 4.x
- Helm 3.x
- Model Registry Operator installed (for `createService: true`)
- PV provisioner support (for MySQL persistence)

## Installation

### Basic Installation

```bash
# Update dependencies first
helm dependency update ./model-registry/helm

# Install the chart
helm install model-registry ./model-registry/helm
```

### With Custom Values

```bash
helm install model-registry ./model-registry/helm \
  --set name=my-model-registry \
  --set mysql.password=secure_password \
  --set mysql.database=my_registry
```

### OpenShift AI Installation

```bash
helm install model-registry ./model-registry/helm \
  --set namespace=rhoai-model-registries \
  --set mysql.openshift.enabled=true \
  --set mysql.openshift.imageStream.enabled=true
```

### With Istio Service Mesh

```bash
helm install model-registry ./model-registry/helm \
  --set istio.enabled=true \
  --set istio.gateway.domain=apps.my-cluster.example.com
```

## Configuration

### Model Registry Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `enabled` | Enable Model Registry deployment | `true` |
| `createService` | Create ModelRegistry CR (requires operator) | `true` |
| `name` | Model Registry name | `model-registry` |
| `namespace` | Namespace override | Release namespace |
| `grpcPort` | gRPC service port | `9090` |
| `restPort` | REST service port | `8080` |

### Istio Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `istio.enabled` | Enable Istio integration | `false` |
| `istio.audiences` | JWT audiences | `["https://kubernetes.default.svc"]` |
| `istio.authProvider` | Auth provider URL | `https://kubernetes.default.svc` |
| `istio.gateway.domain` | External domain | `""` |
| `istio.gateway.grpc.gatewayRoute` | gRPC gateway route | `enabled` |
| `istio.gateway.rest.gatewayRoute` | REST gateway route | `enabled` |

### MySQL Subchart Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `mysql.enabled` | Enable MySQL subchart | `true` |
| `mysql.name` | MySQL resource name | `mysql` |
| `mysql.user` | MySQL user | `mysql_user` |
| `mysql.password` | MySQL password | `mysql_password` |
| `mysql.rootPassword` | MySQL root password | `mysql_root_password` |
| `mysql.database` | Database name | `model_registry` |
| `mysql.port` | MySQL port | `3306` |
| `mysql.persistence.enabled` | Enable persistence | `true` |
| `mysql.persistence.size` | PVC size | `1Gi` |
| `mysql.openshift.enabled` | OpenShift features | `false` |

### Using External MySQL

```yaml
mysql:
  enabled: false
  name: external-mysql
  namespace: databases
  user: registry_user
  password: external_password
  database: model_registry
  port: 3306
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│              Model Registry                     │
│  ┌─────────────────┐  ┌─────────────────┐       │
│  │   REST API      │  │   gRPC API      │       │
│  │   :8080         │  │   :9090         │       │
│  └────────┬────────┘  └────────┬────────┘       │
│           │                    │                │
│           └────────┬───────────┘                │
│                    │                            │
│           ┌────────▼────────┐                   │
│           │     MySQL       │                   │
│           │   Backend DB    │                   │
│           │     :3306       │                   │
│           └─────────────────┘                   │
└─────────────────────────────────────────────────┘
```

## Accessing the Model Registry

### REST API

```bash
# Port forward for local access
kubectl port-forward svc/model-registry 8080:8080

# List registered models
curl http://localhost:8080/api/model_registry/v1alpha3/registered_models
```

### gRPC API

```bash
# Port forward for local access
kubectl port-forward svc/model-registry 9090:9090

# Use grpcurl or your preferred gRPC client
grpcurl -plaintext localhost:9090 list
```

### Python Client

```python
from model_registry import ModelRegistry

registry = ModelRegistry(
    server_address="model-registry:8080",
    author="user@example.com"
)

# Register a model
model = registry.register_model(
    name="my-model",
    uri="s3://bucket/model",
    version="1.0.0"
)
```

## Uninstallation

```bash
helm uninstall model-registry
```

Note: PVCs are not automatically deleted. Remove manually if needed:
```bash
kubectl delete pvc mysql
```

## Troubleshooting

### Model Registry Operator Not Found

If you see errors about the ModelRegistry CRD not found:
1. Install the Model Registry Operator from OperatorHub
2. Or set `createService: false` to skip creating the CR

### MySQL Connection Issues

Check MySQL pod status:
```bash
kubectl get pods -l app=mysql
kubectl logs -l app=mysql
```

Verify MySQL is ready:
```bash
kubectl exec -it deploy/mysql -- mysqladmin -u $MYSQL_USER -p ping
```

