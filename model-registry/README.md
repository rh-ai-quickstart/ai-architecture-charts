# Model Registry Helm Chart

A Helm chart for deploying OpenDataHub Model Registry on OpenShift clusters.

## Overview

This chart deploys a Model Registry instance with PostgreSQL backend, providing a centralized repository for managing ML models. It integrates with OpenShift AI and supports Istio service mesh for advanced routing and security.

## Prerequisites

- Kubernetes 1.19+ or OpenShift 4.x
- Helm 3.x
- Model Registry Operator installed (for `createService: true`)
- PV provisioner support (for PostgreSQL persistence)

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
  --set postgres.password=secure_password \
  --set postgres.database=my_registry
```

### OpenShift AI Installation

```bash
helm install model-registry ./model-registry/helm \
  --set namespace=rhoai-model-registries
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

### PostgreSQL Subchart Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `postgres.enabled` | Enable PostgreSQL subchart | `true` |
| `postgres.name` | PostgreSQL resource name | `pgvector-model-registry` |
| `postgres.user` | PostgreSQL user | `postgres` |
| `postgres.password` | PostgreSQL password | `model_registry_password` |
| `postgres.database` | Database name | `model_registry` |
| `postgres.port` | PostgreSQL port | `5432` |
| `postgres.skipDBCreation` | Skip database creation | `false` |

### Using External PostgreSQL

```yaml
postgres:
  enabled: false
  name: external-postgres
  namespace: databases
  user: registry_user
  password: external_password
  database: model_registry
  port: 5432
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
│           │   PostgreSQL    │                   │
│           │   Backend DB    │                   │
│           │     :5432       │                   │
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
kubectl delete pvc pg-data-pgvector-model-registry-0
```

## Troubleshooting

### Model Registry Operator Not Found

If you see errors about the ModelRegistry CRD not found:
1. Install the Model Registry Operator from OperatorHub
2. Or set `createService: false` to skip creating the CR

### PostgreSQL Connection Issues

Check PostgreSQL pod status:
```bash
kubectl get pods -l app.kubernetes.io/name=pgvector
kubectl logs -l app.kubernetes.io/name=pgvector
```

Verify PostgreSQL is ready:
```bash
kubectl exec -it sts/pgvector-model-registry -- psql -U postgres -c '\l'
```
