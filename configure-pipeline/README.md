# Configure Pipeline Helm Chart

This Helm chart deploys a Data Science Pipelines Application (DSPA) along with an optional Jupyter notebook environment for RAG (Retrieval-Augmented Generation) configuration.

## Overview

The configure-pipeline chart creates:
- A DataSciencePipelinesApplication (DSPA) for running data science workflows
- Bundled AWS-compatible storage by default, or external S3-compatible storage
- Optional Jupyter notebook deployment for pipeline configuration
- Persistent volume claims for data storage
- Secrets for storage credentials and pipeline configuration
- ConfigMaps for pipeline and RAG configuration

## Prerequisites

- OpenShift cluster with OpenDataHub or RHOAI installed
- Helm 3.x
- Access to required container registries
- S3-compatible object storage (the bundled service or an external endpoint)

## Installation

### Basic Installation (with bundled storage)

```bash
helm install configure-pipeline ./helm
```

### Installation with Notebook

```bash
helm install configure-pipeline ./helm \
  --set notebook.create=true \
  --set notebook.repo="https://github.com/your-org/your-rag-repo.git"
```

### Installation with External Storage

```bash
helm install configure-pipeline ./helm \
  --set pipelineStorage.deployAwsCompatibleStorage=false \
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
| `notebook.s3.region` | S3 region for notebook | `us-east-1` |
| `notebook.s3.bucket_name` | S3 bucket name for notebook | `llama` |
| `notebook.s3.accessKeyId` | External S3 access key for notebook data connection | `""` |
| `notebook.s3.secretAccessKey` | External S3 secret key for notebook data connection | `""` |


#### Pipeline Storage Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `pipelineStorage.deployAwsCompatibleStorage` | Deploy bundled AWS-compatible storage | `true` |
| `pipelineStorage.externalStorage.host` | External storage host | `minio` |
| `pipelineStorage.externalStorage.port` | External storage port | `9000` |
| `pipelineStorage.externalStorage.bucket` | Storage bucket for pipelines | `mlpipeline` |
| `pipelineStorage.externalStorage.scheme` | Connection scheme (http/https) | `http` |
| `pipelineStorage.externalStorage.s3CredentialsSecret.secretName` | Secret name for S3 credentials | `minio` |
| `pipelineStorage.externalStorage.s3CredentialsSecret.accessKey` | Access key field in secret | `user` |
| `pipelineStorage.externalStorage.s3CredentialsSecret.secretKey` | Secret key field in secret | `password` |

### Example values.yaml

#### Example 1: Deploy with bundled AWS-compatible storage (default)

Bundled AWS-compatible storage is enabled by default, so no `pipelineStorage` settings are needed. Customize the notebook settings as needed:

```yaml
notebook:
  create: true
  image: "quay.io/your-org/custom-notebook:latest"
  repo: "https://github.com/your-org/custom-rag-repo.git"
  pvcName: "custom-pipeline-vol"
  embedding_model: sentence-transformers/all-MiniLM-L6-v2
  name: custom-rag-db
  version: 2.0
  s3:
    region: us-west-2
    bucket_name: custom-bucket
```

#### Example 2: Use External S3-Compatible Storage

```yaml
notebook:
  create: false  # Disable notebook if not needed

# Pipeline storage - use external storage
pipelineStorage:
  deployAwsCompatibleStorage: false
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
2. **Object Storage**: Deployed AWS-compatible storage or configured external S3-compatible storage
3. **Jupyter Notebook** (optional): Access your notebook environment for pipeline configuration
4. **Storage**: Persistent volumes for data persistence
5. **Secrets**: Storage credentials and pipeline configuration secrets
6. **ConfigMaps**: Pipeline and RAG configuration

### Storage Options

The chart supports two storage modes.

#### 1. Bundled AWS-compatible storage

When `pipelineStorage.deployAwsCompatibleStorage: true`, the chart deploys the `aws-compatible-storage` dependency with the stable Service name `aws-compatible-storage` and credentials Secret `aws-compatible-storage-credentials`. The DSPA and notebook use its S3 endpoint on port `7480`.

#### 2. External Storage

Set `pipelineStorage.deployAwsCompatibleStorage: false` to use an external S3-compatible service. The existing `pipelineStorage.externalStorage` defaults are retained; override the endpoint and point `s3CredentialsSecret` to an existing Secret as needed. When the notebook is enabled, also set `notebook.s3.accessKeyId` and `notebook.s3.secretAccessKey` so the dashboard data connection Secret can be generated.

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

#### When using bundled AWS-compatible storage

The chart deploys the bundled AWS-compatible storage service and configures the DSPA and notebook to use its in-cluster S3 endpoint.

#### When using external storage

Ensure you:
- Create a secret with your S3 credentials before installing the chart
- Configure `pipelineStorage.externalStorage` to point to your external storage endpoint
- Set `pipelineStorage.deployAwsCompatibleStorage: false`
- The secret should contain the keys specified in `s3CredentialsSecret.accessKey` and `s3CredentialsSecret.secretKey`

### Pipeline Configuration

The notebook environment includes:
- Pre-configured S3 access
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
   - If using bundled storage: Verify the `aws-compatible-storage` pod is running
   - If using external storage: Check credentials secret exists and contains correct keys
   - Verify DSPA can reach the storage endpoint (check DSPA pod logs)
   - Validate bucket exists and credentials have appropriate permissions

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
- **Object storage**: Deploy bundled AWS-compatible storage (default) or provide external S3-compatible storage
- **Git repository access**: For notebook code and templates (if notebook.create is enabled)
- **Sufficient cluster resources**: CPU, memory, and storage
- **Container registry access**: For pulling notebook and storage images
- **Network connectivity**: Between components and external services

### Chart Dependencies

This chart has the following subchart dependency:

- **aws-compatible-storage** (version 0.1.0): Deployed by default when `pipelineStorage.deployAwsCompatibleStorage: true`

## Integration

This chart works well with other components in the AI architecture:

- **ingestion-pipeline**: For data processing workflows
- **llama-stack** / **ogx-ai**: For LLM inference and orchestration capabilities
- **pgvector**: For vector storage

Deploy these components in the same namespace for optimal integration.
