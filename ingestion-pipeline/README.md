# Ingestion Pipeline Helm Chart

This Helm chart deploys a comprehensive RAG (Retrieval-Augmented Generation) data ingestion pipeline that processes documents from various sources and stores vector embeddings for semantic search.

## Overview

The ingestion-pipeline chart creates:
- Document ingestion service with REST API
- Multiple pipeline jobs for batch processing from different sources
- RBAC configuration for Kubernetes access
- Integration with MinIO, GitHub, and URL sources
- Support for multiple embedding models
- Concurrent processing of multiple data sources

### Multi-Pipeline Architecture

This chart supports multiple concurrent pipelines, allowing you to:
- **Process different data sources simultaneously** (S3, GitHub, URLs)
- **Use different embedding models** for different content types
- **Enable/disable pipelines independently** for flexible deployment
- **Scale processing** by running multiple pipelines in parallel
- **Organize data** into separate vector stores by source

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
  --set pipelines.default-s3-pipeline.enabled=true \
  --set pipelines.default-s3-pipeline.S3.bucket_name=your-bucket \
  --set pipelines.default-s3-pipeline.embedding_model=all-MiniLM-L6-v2
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
| `image.repository` | Container image repository | `quay.io/ecosystem-appeng/ingestion-pipeline` |
| `image.pullPolicy` | Image pull policy | `Always` |
| `service.port` | Service port | `80` |
| `service.targetPort` | Container target port | `8000` |
| `pipelines.<name>.enabled` | Enable specific pipeline | `true` |
| `pipelines.<name>.source` | Data source type (S3, GITHUB, URL) | `S3` |
| `pipelines.<name>.embedding_model` | Embedding model to use | `all-MiniLM-L6-v2` |
| `pipelines.<name>.name` | Pipeline name | `demo-rag-vector-db` |
| `pipelines.<name>.version` | Pipeline version | `1.0` |
| `pipelines.<name>.vector_store_name` | Vector store name | `demo-rag-vector-db-v1-0-s3` |

### Data Source Configuration

#### S3/MinIO Source
```yaml
pipelines:
  my-s3-pipeline:
    enabled: true
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
pipelines:
  my-github-pipeline:
    enabled: true
    source: GITHUB
    GITHUB:
      url: https://github.com/your-org/docs-repo.git
      path: docs
      token: your_github_token
      branch: main
```

#### URL Source
```yaml
pipelines:
  my-url-pipeline:
    enabled: true
    source: URL
    URL:
      urls:
        - "https://arxiv.org/pdf/2408.09869"
        - "https://example.com/document.pdf"
```

#### Multiple Pipelines Example
```yaml
pipelines:
  # S3-based pipeline
  production-s3:
    enabled: true
    source: S3
    embedding_model: "all-MiniLM-L6-v2"
    name: "prod-s3-vector-db"
    version: "1.0"
    vector_store_name: "prod-s3-v1-0"
    S3:
      access_key_id: minio_rag_user
      secret_access_key: minio_rag_password
      bucket_name: production-docs
      endpoint_url: http://minio:9000
      region: us-east-1

  # GitHub documentation pipeline
  docs-github:
    enabled: true
    source: GITHUB
    embedding_model: "all-MiniLM-L6-v2"
    name: "docs-vector-db"
    version: "1.0"
    vector_store_name: "docs-github-v1-0"
    GITHUB:
      url: https://github.com/company/documentation.git
      path: docs
      token: github_token_here
      branch: main

  # Research papers pipeline
  research-urls:
    enabled: false  # Disabled by default
    source: URL
    embedding_model: "all-MiniLM-L6-v2"
    name: "research-vector-db"
    version: "1.0"
    vector_store_name: "research-url-v1-0"
    URL:
      urls:
        - "https://arxiv.org/pdf/2408.09869"
        - "https://arxiv.org/pdf/2310.06825"
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

pipelines:
  # Production S3 pipeline
  production-s3:
    enabled: true
    source: S3
    embedding_model: "sentence-transformers/all-MiniLM-L6-v2"
    name: "production-rag-db"
    version: "2.0"
    vector_store_name: "production-rag-db-v2-0-s3"
    S3:
      access_key_id: production_user
      secret_access_key: secure_password
      bucket_name: production-documents
      endpoint_url: https://s3.amazonaws.com
      region: us-west-2

  # Documentation from GitHub
  docs-pipeline:
    enabled: true
    source: GITHUB
    embedding_model: "all-MiniLM-L6-v2"
    name: "docs-vector-db"
    version: "1.0"
    vector_store_name: "docs-github-v1-0"
    GITHUB:
      url: https://github.com/company/documentation.git
      path: docs
      token: github_token_here
      branch: main

resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "1Gi"
    cpu: "500m"

authUser: "pipeline-user"
```

## Best Practices

### 1. Naming Convention
Use descriptive pipeline keys that indicate source and purpose:
```yaml
pipelines:
  s3-product-docs:     # Clear: S3 source, product docs
  github-api-docs:     # Clear: GitHub source, API docs
  url-research-papers: # Clear: URL source, research papers
```

### 2. Version Management
Use semantic versioning for knowledge bases:
```yaml
version: "1.0"      # Initial version
version: "1.1"      # Minor update
version: "2.0"      # Major change
```

### 3. Environment Separation
Use pipeline enable/disable for environment-specific deployments:
```yaml
pipelines:
  dev-pipeline:
    enabled: true   # Always enabled
  prod-pipeline:
    enabled: false  # Override in production: --set pipelines.prod-pipeline.enabled=true
```

### 4. Resource Optimization
Choose embedding models based on use case:
- `all-MiniLM-L6-v2`: Fast, good for development/general use
- `sentence-transformers/all-mpnet-base-v2`: Higher quality, better for production

## Migration from Single Pipeline

If you were using the old single pipeline configuration, migrate to the new structure:

### Before (Old Structure - No Longer Supported)
```yaml
defaultPipeline:
  enabled: true
  source: S3
  # ... rest of config
```

### After (New Multi-Pipeline Structure)
```yaml
pipelines:
  my-pipeline:  # You can name it anything descriptive
    enabled: true
    source: S3
    # ... rest of config (same structure)
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

The pipeline jobs run automatically when enabled and start ingesting data from the configured sources after the service is deployed:

```bash
# Check all pipeline jobs status
oc get jobs -l app.kubernetes.io/name=ingestion-pipeline

# View specific pipeline job logs
oc logs -l job-name=add-default-s3-pipeline-pipeline -f
oc logs -l job-name=add-github-docs-pipeline-pipeline -f
oc logs -l job-name=add-url-content-pipeline-pipeline -f

# Monitor pipeline progress
oc describe job add-default-s3-pipeline-pipeline
oc describe job add-github-docs-pipeline-pipeline
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
oc logs -l job-name=add-default-s3-pipeline-pipeline -f
oc logs -l job-name=add-github-docs-pipeline-pipeline -f

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
oc describe job add-default-s3-pipeline-pipeline
oc describe job add-github-docs-pipeline-pipeline
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
