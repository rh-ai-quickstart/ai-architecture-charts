# Ingestion Pipeline Helm Chart

This Helm chart deploys a comprehensive RAG (Retrieval-Augmented Generation) data ingestion pipeline that processes documents from various sources and stores vector embeddings for semantic search.

## Overview

The ingestion-pipeline chart creates:
- Document ingestion service with REST API
- Pipeline job for batch processing
- RBAC configuration for Kubernetes access
- Integration with MinIO, GitHub, and URL sources
- Support for multiple embedding models

## Prerequisites

- OpenShift cluster
- Helm 3.x
- Access to container registries
- External dependencies:
  - MinIO instance for S3 storage
  - Vector database (PGVector recommended)
  - LlamaStack for embeddings (optional)

## Installation

### Basic Installation

```bash
helm install ingestion-pipeline ./helm
```

### Custom Installation with Parameters

```bash
helm install ingestion-pipeline ./helm \
  --set defaultPipeline.enabled=true \
  --set defaultPipeline.source=S3 \
  --set defaultPipeline.S3.bucket_name=your-bucket \
  --set defaultPipeline.embedding_model=all-MiniLM-L6-v2
```

### Installation with Custom Namespace

```bash
helm install ingestion-pipeline ./helm \
  --namespace rag-ingestion \
  --create-namespace
```

## Configuration

### Key Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of service replicas | `1` |
| `image.repository` | Container image repository | `quay.io/rh-ai-quickstart/ingestion-pipeline` |
| `image.pullPolicy` | Image pull policy | `Always` |
| `service.port` | Service port | `80` |
| `service.targetPort` | Container target port | `8000` |
| `defaultPipeline.enabled` | Enable default pipeline job (runs automatically after deployment) | `true` |
| `defaultPipeline.source` | Data source type (S3, GITHUB, URL) | `S3` |
| `defaultPipeline.embedding_model` | Embedding model to use | `all-MiniLM-L6-v2` |
| `defaultPipeline.name` | Pipeline name | `demo-rag-vector-db` |
| `defaultPipeline.version` | Pipeline version | `1.0` |
| `defaultPipeline.vector_store_name` | Vector store name | `demo-rag-vector-db-v1-0-s3` |

### Data Source Configuration

#### S3/MinIO Source
```yaml
defaultPipeline:
  source: S3
  S3:
    access_key_id: minio_rag_user
    secret_access_key: minio_rag_password
    bucket_name: documents
    endpoint_url: http://minio:9000
    region: us-east-1
```

#### GitHub Source
```yaml
defaultPipeline:
  source: GITHUB
  GITHUB:
    url: https://github.com/your-org/docs-repo.git
    path: docs
    token: your_github_token
    branch: main
```

#### URL Source
```yaml
defaultPipeline:
  source: URL
  URL:
    urls:
      - "https://arxiv.org/pdf/2408.09869"
      - "https://example.com/document.pdf"
```

### Complete Example values.yaml

```yaml
replicaCount: 2

image:
  repository: quay.io/your-org/custom-ingestion-pipeline
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 8080
  targetPort: 8000

defaultPipeline:
  enabled: true
  source: S3
  embedding_model: "sentence-transformers/all-MiniLM-L6-v2"
  name: "production-rag-db"
  version: "2.0"
  vector_store_name: "production-rag-db-v2-0"
  
  S3:
    access_key_id: production_user
    secret_access_key: secure_password
    bucket_name: production-documents
    endpoint_url: https://s3.amazonaws.com
    region: us-west-2

resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "1Gi"
    cpu: "500m"

authUser: "pipeline-user"
```

## Usage

### REST API Service

The ingestion pipeline exposes a REST API for document processing:

```bash
# Get service endpoint
oc get svc ingestion-pipeline

# Port forward for local access
oc port-forward svc/ingestion-pipeline 8000:80

# Submit documents for ingestion
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "source": "S3",
    "bucket": "documents",
    "path": "folder/document.pdf"
  }'
```

### Pipeline Job Execution

The default pipeline job runs automatically when enabled and starts ingesting data from the configured source after the service is deployed:

```bash
# Check job status
oc get jobs -l app.kubernetes.io/name=ingestion-pipeline

# View job logs
oc logs -l job-name=default-pipeline-job -f

# Monitor pipeline progress
oc describe job default-pipeline-job
```

### Integration with OpenShift AI

1. **Access Workbench**: Navigate to OpenShift AI and open the workbench
2. **Pipeline Notebooks**: Use provided notebooks to trigger ingestion
3. **View Pipeline Runs**: Monitor progress in the Pipelines section
4. **Check Results**: Verify embeddings in your vector database

## Monitoring and Troubleshooting

### Checking Service Health

```bash
# Check pod status
oc get pods -l app.kubernetes.io/name=ingestion-pipeline

# Check service endpoints
oc get endpoints ingestion-pipeline

# Test service connectivity
oc exec -it deployment/ingestion-pipeline -- curl localhost:8000/health
```

### Viewing Logs

```bash
# Service logs
oc logs -l app.kubernetes.io/name=ingestion-pipeline -f

# Job logs
oc logs -l job-name=default-pipeline-job -f

# Previous container logs (if crashed)
oc logs -l app.kubernetes.io/name=ingestion-pipeline --previous
```

### Common Issues

1. **Pipeline Job Fails**:
   - Check data source connectivity (S3, GitHub, URLs)
   - Verify authentication credentials
   - Ensure embedding model is accessible
   - Check vector database connectivity

2. **Service Not Responding**:
   - Verify container image availability
   - Check resource limits and requests
   - Validate service configuration
   - Review network policies

3. **Authentication Errors**:
   - Verify S3/MinIO credentials
   - Check GitHub token permissions
   - Validate authUser configuration

4. **Vector Database Issues**:
   - Ensure vector database is running
   - Check connection parameters
   - Verify database schema compatibility

### Debugging Commands

```bash
# Check RBAC permissions
oc auth can-i create jobs --as=system:serviceaccount:default:ingestion-pipeline

# Inspect configuration
oc get configmaps -l app.kubernetes.io/name=ingestion-pipeline -o yaml

# Check secrets
oc get secrets -l app.kubernetes.io/name=ingestion-pipeline

# Describe resources
oc describe deployment ingestion-pipeline
oc describe job default-pipeline-job
```

## Security Considerations

### Service Account Configuration

The chart creates a dedicated service account with minimal required permissions:
- Job creation and management
- ConfigMap and Secret access
- Pod execution

### Network Security

- Service operates on internal cluster network by default
- Use NetworkPolicies to restrict traffic
- Enable TLS for external access

## Upgrading

```bash
# Upgrade with new values
helm upgrade ingestion-pipeline ./helm \
  --set image.tag=v0.3.0

# Check upgrade status
oc rollout status deployment/ingestion-pipeline
```

## Uninstalling

```bash
# Remove chart
helm uninstall ingestion-pipeline

# Clean up jobs (if needed)
oc delete jobs -l app.kubernetes.io/name=ingestion-pipeline

# Remove persistent data (if any)
oc delete pvc -l app.kubernetes.io/name=ingestion-pipeline
```

## Integration with Other Components

This chart integrates with:

- **MinIO**: Object storage for documents
- **PGVector**: Vector database for embeddings
- **LlamaStack**: LLM inference and embeddings
- **OpenShift AI**: Pipeline orchestration and notebooks

## API Reference

### Health Check
```
GET /health
Response: {"status": "ok"}
```

### Document Ingestion
```
POST /ingest
Content-Type: application/json
Body: {
  "source": "S3|GITHUB|URL",
  "config": { source-specific parameters }
}
```

### Pipeline Status
```
GET /status/{pipeline_id}
Response: {"status": "running|completed|failed", "progress": 75}
```
