# Configure Pipeline Helm Chart

This Helm chart deploys a Data Science Pipelines Application (DSPA) along with an optional Jupyter notebook environment for RAG (Retrieval-Augmented Generation) configuration.

## Overview

The configure-pipeline chart creates:
- A DataSciencePipelinesApplication (DSPA) for running data science workflows
- Object storage (optional MinIO deployment or external S3-compatible storage)
- Optional Jupyter notebook deployment for pipeline configuration
- Persistent volume claims for data storage
- Secrets for storage credentials and pipeline configuration
- ConfigMaps for pipeline and RAG configuration

## Prerequisites

- OpenShift cluster with OpenDataHub or RHOAI installed
- Helm 3.x
- Access to required container registries
- Object storage (MinIO can be deployed as a dependency, or use external S3-compatible storage)

## Installation

### Basic Installation

```bash
helm install configure-pipeline ./helm
```

### Installation with Notebook

```bash
helm install configure-pipeline ./helm \
  --set notebook.create=true \
  --set notebook.repo="https://github.com/your-org/your-rag-repo.git"
```

### Installation with External Storage (without deploying MinIO)

```bash
helm install configure-pipeline ./helm \
  --set pipelineStorage.deployMinio=false \
  --set pipelineStorage.externalStorage.host="s3.amazonaws.com" \
  --set pipelineStorage.externalStorage.bucket="my-bucket" \
  --set pipelineStorage.externalStorage.s3CredentialsSecret.secretName="aws-credentials"
```

### Installation with Custom Namespace

```bash
helm install configure-pipeline ./helm \
  --namespace rag-pipeline \
  --create-namespace
```

## Configuration

### Key Configuration Options

#### Notebook Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `notebook.create` | Create notebook deployment | `true` |
| `notebook.image` | Notebook container image | `image-registry.openshift-image-registry.svc:5000/redhat-ods-applications/s2i-generic-data-science-notebook:2024.2` |
| `notebook.repo` | Git repository for notebook code | `https://github.com/rh-ai-quickstart/RAG.git` |
| `notebook.pvcName` | PVC name for notebook storage | `pipeline-vol` |
| `notebook.embedding_model` | Embedding model to use | `all-MiniLM-L6-v2` |
| `notebook.name` | RAG vector database name | `rag-vector-db` |
| `notebook.version` | Version identifier | `1.0` |
| `notebook.minio.region` | MinIO region for notebook | `us-east-1` |
| `notebook.minio.bucket_name` | MinIO bucket name for notebook | `llama` |

#### MinIO Subchart Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `minio.secret.user` | MinIO username | `minio_rag_user` |
| `minio.secret.password` | MinIO password | `minio_rag_password` |
| `minio.secret.host` | MinIO service host | `minio` |
| `minio.secret.port` | MinIO service port | `9000` |

#### Pipeline Storage Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `pipelineStorage.deployMinio` | Deploy MinIO as a dependency | `true` |
| `pipelineStorage.externalStorage.host` | External storage host | `minio` |
| `pipelineStorage.externalStorage.port` | External storage port | `9000` |
| `pipelineStorage.externalStorage.bucket` | Storage bucket for pipelines | `mlpipeline` |
| `pipelineStorage.externalStorage.scheme` | Connection scheme (http/https) | `http` |
| `pipelineStorage.externalStorage.s3CredentialsSecret.secretName` | Secret name for S3 credentials | `minio` |
| `pipelineStorage.externalStorage.s3CredentialsSecret.accessKey` | Access key field in secret | `user` |
| `pipelineStorage.externalStorage.s3CredentialsSecret.secretKey` | Secret key field in secret | `password` |

### Example values.yaml

#### Example 1: Deploy with MinIO (default)

```yaml
# MinIO credentials (used by minio chart and notebook)
minio:
  secret:
    user: custom_user
    password: custom_password
    host: minio
    port: "9000"

notebook:
  create: true
  image: "quay.io/your-org/custom-notebook:latest"
  repo: "https://github.com/your-org/custom-rag-repo.git"
  pvcName: "custom-pipeline-vol"
  embedding_model: sentence-transformers/all-MiniLM-L6-v2
  name: custom-rag-db
  version: 2.0
  minio:
    region: us-west-2
    bucket_name: custom-bucket

# Pipeline storage - deploy minio
pipelineStorage:
  deployMinio: true
  externalStorage:
    host: "minio"
    port: "9000"
    bucket: "mlpipeline"
    scheme: "http"
    s3CredentialsSecret:
      secretName: "minio"
      accessKey: "user"
      secretKey: "password"
```

#### Example 2: Use External S3-Compatible Storage

```yaml
notebook:
  create: false  # Disable notebook if not needed

# Pipeline storage - use external storage
pipelineStorage:
  deployMinio: false  # Don't deploy minio
  externalStorage:
    host: "s3.us-west-2.amazonaws.com"
    port: "443"
    bucket: "my-pipeline-bucket"
    scheme: "https"
    s3CredentialsSecret:
      secretName: "aws-s3-credentials"
      accessKey: "AWS_ACCESS_KEY_ID"
      secretKey: "AWS_SECRET_ACCESS_KEY"
```

## Usage

After installation, the chart will create:

1. **DataSciencePipelinesApplication (DSPA)**: A complete data science pipeline environment for running workflows
2. **Object Storage**: Either a deployed MinIO instance or configured external S3-compatible storage
3. **Jupyter Notebook** (optional): Access your notebook environment for pipeline configuration
4. **Storage**: Persistent volumes for data persistence
5. **Secrets**: Storage credentials and pipeline configuration secrets
6. **ConfigMaps**: Pipeline and RAG configuration

### Storage Options

The chart supports two storage modes:

#### 1. Deployed MinIO (default)

When `pipelineStorage.deployMinio: true`, the chart deploys MinIO as a subchart dependency. This is suitable for:
- Development and testing environments
- Single-cluster deployments
- When you don't have existing S3-compatible storage

The deployed MinIO instance:
- Runs in the same namespace as the pipeline
- Creates a secret with credentials configured in `minio.secret`
- Automatically configures the DSPA to use it (with namespace-qualified hostname)

#### 2. External Storage

When `pipelineStorage.deployMinio: false`, the chart uses external S3-compatible storage. This is suitable for:
- Production environments
- AWS S3, Google Cloud Storage, Azure Blob Storage (with S3 compatibility)
- External/shared MinIO instances
- Multi-cluster deployments

For external storage:
- Set the host to the external endpoint (e.g., `s3.amazonaws.com`)
- Configure credentials via an existing secret
- The chart will NOT append the namespace to the hostname

### Accessing the Data Science Pipeline

Check the DSPA status:

```bash
oc get datasciencepipelinesapplication dspa
```

Access the pipeline UI through the OpenDataHub/RHOAI dashboard, or get the route:

```bash
oc get route -l app=dspa
```

### Accessing the Notebook

If `notebook.create: true`, the notebook will be available through the Kubernetes service. Port-forward to access:

```bash
oc port-forward svc/configure-pipeline-notebook 8888:8888
```

Then access at `http://localhost:8888`

### OpenShift Route (if available)

On OpenShift, you can create a route for external access to the notebook:

```bash
oc expose service configure-pipeline-notebook
```

### Storage Configuration

#### When using deployed MinIO

The chart automatically:
- Deploys MinIO via the subchart dependency
- Creates a secret with credentials from `minio.secret`
- Configures DSPA to use the deployed MinIO with namespace-qualified hostname (`minio.<namespace>`)
- Configures notebook secret with MinIO access details

#### When using external storage

Ensure you:
- Create a secret with your S3 credentials before installing the chart
- Configure `pipelineStorage.externalStorage` to point to your external storage endpoint
- Set `pipelineStorage.deployMinio: false`
- The secret should contain the keys specified in `s3CredentialsSecret.accessKey` and `s3CredentialsSecret.secretKey`

### Pipeline Configuration

The notebook environment includes:
- Pre-configured MinIO access
- RAG pipeline templates
- Embedding model configuration
- Vector database setup scripts

## Monitoring and Troubleshooting

### Checking Pod Status

```bash
oc get pods -l app.kubernetes.io/name=configure-pipeline
```

### Viewing Logs

```bash
oc logs -l app.kubernetes.io/name=configure-pipeline -f
```

### Common Issues

1. **Notebook won't start**: 
   - Check if the specified Git repository is accessible
   - Verify image registry permissions
   - Check resource limits

2. **Storage connection issues**:
   - If using deployed MinIO: Verify MinIO pod is running (`oc get pods -l app=minio`)
   - If using external storage: Check credentials secret exists and contains correct keys
   - Verify DSPA can reach the storage endpoint (check DSPA pod logs)
   - Validate bucket exists and credentials have appropriate permissions
   - For deployed MinIO, ensure the namespace is correctly appended to the hostname

3. **Storage issues**: 
   - Ensure sufficient storage is available for PVCs
   - Check storage class availability
   - Verify PVC binding

4. **Git repository access**:
   - Ensure repository URL is correct and accessible
   - For private repos, configure authentication
   - Check network policies

### Checking Configuration

```bash
# Check secrets
oc get secrets -l app.kubernetes.io/name=configure-pipeline

# Check configmaps
oc get configmaps -l app.kubernetes.io/name=configure-pipeline

# Check PVCs
oc get pvc -l app.kubernetes.io/name=configure-pipeline
```

## Upgrading

To upgrade the chart:

```bash
helm upgrade configure-pipeline ./helm
```

## Uninstalling

```bash
helm uninstall configure-pipeline
```

**Note**: This will not delete PVCs by default. To also remove persistent data:

```bash
oc delete pvc -l app.kubernetes.io/name=configure-pipeline
```

## Dependencies

- **OpenDataHub or RHOAI**: Required for DataSciencePipelinesApplication CRD
- **Object storage**: Either deploy MinIO (default) or provide external S3-compatible storage
- **Git repository access**: For notebook code and templates (if notebook.create is enabled)
- **Sufficient cluster resources**: CPU, memory, and storage
- **Container registry access**: For pulling notebook and MinIO images
- **Network connectivity**: Between components and external services

### Chart Dependencies

This chart has the following subchart dependency:

- **minio** (version 0.5.0): Conditionally deployed when `pipelineStorage.deployMinio: true`

## Integration

This chart works well with other components in the AI architecture:

- **ingestion-pipeline**: For data processing workflows
- **llama-stack** / **ogx-ai**: For LLM inference and orchestration capabilities
- **pgvector**: For vector storage
- **minio**: For object storage

Deploy these components in the same namespace for optimal integration.