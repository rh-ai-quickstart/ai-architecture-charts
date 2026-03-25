# ChromaDB Helm Chart

This Helm chart deploys ChromaDB, an open-source AI-native vector database for storing and querying embeddings used in RAG pipelines and semantic search applications.

## Overview

The chromadb chart creates:
- ChromaDB deployment as a StatefulSet for data persistence
- Service for HTTP API access
- Secret management for connection details and optional authentication
- Persistent storage for vector data

## Prerequisites

- OpenShift cluster or Kubernetes 1.19+
- Helm 3.x
- Persistent storage (PVC support)

## Installation

### Basic Installation

```bash
helm install chromadb ./helm
```

### Installation with Custom Storage

```bash
helm install chromadb ./helm \
  --set volumeClaimTemplates[0].spec.resources.requests.storage=20Gi
```

### Installation with Authentication

```bash
helm install chromadb ./helm \
  --set auth.enabled=true \
  --set auth.token=your_secret_token_here
```

### Installation with Custom Namespace

```bash
helm install chromadb ./helm \
  --namespace vector-db \
  --create-namespace
```

## Configuration

### Key Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of replicas | `1` |
| `image.repository` | ChromaDB image repository | `docker.io/chromadb/chroma` |
| `image.tag` | ChromaDB image tag | `latest` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `service.type` | Service type | `ClusterIP` |
| `service.port` | ChromaDB HTTP port | `8000` |
| `secret.host` | Service hostname | `chromadb` |
| `secret.port` | Service port | `"8000"` |
| `auth.enabled` | Enable token authentication | `false` |
| `auth.token` | Authentication token | `""` |

### Storage Configuration

```yaml
volumeClaimTemplates:
  - metadata:
      name: chroma-data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 5Gi

volumeMounts:
  - mountPath: /chroma/chroma
    name: chroma-data
```

### Authentication Configuration

```yaml
auth:
  enabled: true
  provider: "chromadb.auth.token.TokenAuthServerProvider"
  credentialsProvider: "chromadb.auth.token.TokenConfigServerProvider"
  token: "your_secret_token_here"
```

### Complete Example values.yaml

```yaml
replicaCount: 1

image:
  repository: docker.io/chromadb/chroma
  pullPolicy: IfNotPresent
  tag: "latest"

nameOverride: "chromadb"
fullnameOverride: "chromadb"

service:
  type: ClusterIP
  port: 8000

resources:
  requests:
    memory: "256Mi"
    cpu: "100m"
  limits:
    memory: "512Mi"
    cpu: "500m"

volumeClaimTemplates:
  - metadata:
      name: chroma-data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 10Gi

volumeMounts:
  - mountPath: /chroma/chroma
    name: chroma-data

secret:
  create: true
  host: chromadb
  port: "8000"

auth:
  enabled: false

nodeSelector:
  kubernetes.io/os: linux
```

## Usage

### Connecting from Within the Cluster

ChromaDB exposes a REST API on port 8000. Other services can connect using the service name:

```python
import chromadb

client = chromadb.HttpClient(host="chromadb", port=8000)
heartbeat = client.heartbeat()
print(f"ChromaDB is alive: {heartbeat}")
```

### Port Forwarding for External Access

```bash
oc port-forward svc/chromadb 8000:8000

# Test with curl
curl http://localhost:8000/api/v1/heartbeat
```

### Working with Collections

```python
import chromadb

client = chromadb.HttpClient(host="chromadb", port=8000)

collection = client.get_or_create_collection(name="documents")

collection.add(
    documents=["AI enables machines to simulate intelligence"],
    metadatas=[{"source": "intro"}],
    ids=["doc1"]
)

results = collection.query(
    query_texts=["What is artificial intelligence?"],
    n_results=5
)
```

## Monitoring and Troubleshooting

### Checking Service Health

```bash
# Check pod status
oc get pods -l app.kubernetes.io/name=chromadb

# Check StatefulSet
oc get statefulset chromadb

# Check service
oc get svc chromadb

# Test heartbeat
oc exec -it chromadb-0 -- curl -s http://localhost:8000/api/v1/heartbeat
```

### Viewing Logs

```bash
oc logs chromadb-0 -f

oc describe statefulset chromadb

oc get pvc -l app.kubernetes.io/name=chromadb
```

### Common Issues

1. **Pod Won't Start**:
   - Check PVC binding status
   - Verify storage class availability
   - Check resource limits

2. **Connection Refused**:
   - Verify service configuration
   - Check pod readiness
   - Test network connectivity

3. **Authentication Errors**:
   - Verify `auth.enabled` matches client configuration
   - Check token value in secret
   - Ensure client sends correct Authorization header

## Uninstalling

```bash
helm uninstall chromadb

# Remove persistent data (WARNING: This deletes all data)
oc delete pvc -l app.kubernetes.io/name=chromadb
```

## Integration with AI Components

This chart integrates with:

- **RAG Services**: Vector storage for document embeddings and semantic search
- **Ingestion Pipelines**: Embedding storage during document processing
- **Agent Services**: Knowledge retrieval for AI agents

### Example Integration Configuration

```yaml
env:
  - name: CHROMA_HOST
    valueFrom:
      secretKeyRef:
        name: chromadb
        key: host
  - name: CHROMA_PORT
    valueFrom:
      secretKeyRef:
        name: chromadb
        key: port
```
