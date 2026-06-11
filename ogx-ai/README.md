# OGX Helm Chart

This Helm chart deploys **[OGX](https://github.com/ogx-ai/ogx)** (formerly Llama Stack): an OpenAI-compatible, agentic API server that supports multiple LLM providers, remote vLLM endpoints, VertexAI, embeddings, and MCP-style tool integration. See the [project announcement](https://ogx-ai.github.io/blog/from-ogx-ai-to-ogx).

> **Chart path:** In this repo the chart still lives under `ogx-ai/helm` for backwards compatibility; the Helm chart name is `ogx-ai`.

> **Service name:** Defaults use `fullnameOverride: ogx-ai`, so the Kubernetes `Service` is `ogx-ai`. Charts or jobs that still call `http://llamastack:8321` should either point at `ogx-ai` or set `fullnameOverride: llamastack` in `values.yaml` until those references are updated.
-
## Overview

The chart creates:
- OGX deployment with configurable models
- Service for API access
- ConfigMap for runtime configuration
- PVC for model storage and cache
- Secret management for external providers
- Support for VertexAI, local models, and MCP servers

## Prerequisites

### Standard Mode
- OpenShift cluster
- Helm 3.x
- Access to model repositories (HuggingFace, etc.)
- External dependencies:
  - PGVector database for vector storage
  - LLM Service deployment for model inference (if using local models)

### Operator Mode
All of the above, plus:
- **ogx-ai operator** installed in the cluster
- CRD `llamastackdistributions.llamastack.io` registered (API: `llamastack.io/v1alpha1`)

To install the ogx-ai operator:
```bash
# Verify CRD is registered
kubectl get crd llamastackdistributions.llamastack.io

# Verify operator is running
kubectl get deployment -n ogx-ai-operator-system

# Check operator version
kubectl get deployment -n ogx-ai-operator-system -o jsonpath='{.items[0].spec.template.spec.containers[0].image}'
```

**Note**: The ogx-ai operator is typically installed as part of OpenDataHub or via a standalone operator deployment. Consult your platform documentation for specific installation steps.

## Deployment Modes

This chart supports two deployment modes:

1. **Standard Helm Deployment** (default): Deploys traditional Kubernetes resources (Deployment, Service, ConfigMap, etc.)
2. **Operator-based Deployment**: Deploys a LlamaStackDistribution custom resource managed by the ogx-ai operator

### Choosing a Deployment Mode

Use standard Helm deployment when:
- You want direct control over Kubernetes resources
- You don't have the ogx-ai operator installed
- You're deploying in environments without CRD support

Use operator-based deployment when:
- You have the ogx-ai operator installed in your cluster
- You want operator-managed lifecycle and reconciliation
- You prefer declarative CRD-based configuration

## Installation

### Basic Installation (Standard Mode)

```bash
helm install ogx ./helm
```

### Installation with Operator Mode

**Prerequisites**: The ogx-ai operator must be installed in your cluster.

```bash
helm install ogx-ai ./helm \
  --set managedByOperator=true
```

This will create a LlamaStackDistribution custom resource instead of traditional Kubernetes resources. The operator will then create and manage the underlying Deployment, Service, and ConfigMap.

### Installation with VertexAI Support

**Important**: VertexAI requires a Google Cloud service account file. You must provide this file during installation:

```bash
helm install ogx-ai ./helm \
  --set vertexai.enabled=true \
  --set vertexai.projectId=your-gcp-project \
  --set vertexai.location=us-central1 \
  --set-file gcpServiceAccountFile=path/to/service-account.json
```

The service account file will be mounted at `/var/secrets/gcp-service-account.json` inside the container.

### Installation with Local Models

**Standard Mode:**
```bash
helm install ogx-ai ./helm \
  --set models.llama-3-2-3b-instruct.enabled=true \
  --set models.llama-guard-3-8b.enabled=true
```

**Operator Mode:**
```bash
helm install ogx-ai ./helm \
  --set managedByOperator=true \
  --set models.llama-3-2-3b-instruct.enabled=true \
  --set models.llama-guard-3-8b.enabled=true
```

**Note**: When enabling models without providing a `url`, LlamaStack assumes the models are served by the LLM Service in the same namespace. The chart automatically generates URLs pointing to `{model-name}-predictor.{namespace}.svc.cluster.local:8080/v1`.

## Configuration

### Key Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `managedByOperator` | Deploy using LlamaStackDistribution CRD via operator | `false` |
| `network.exposeRoute` | (Operator only) Create Ingress/Route for external access | `false` |
| `network.allowedFrom.namespaces` | (Operator only) List of namespaces allowed to access service | `[]` |
| `network.allowedFrom.labels` | (Operator only) List of namespace labels allowed to access service | `[]` |
| `workers` | (Operator only) Number of uvicorn worker processes | `unset` |
| `podDisruptionBudget` | (Operator only) PDB configuration | `{}` |
| `tlsConfig` | (Operator only) Custom CA bundle configuration | `{}` |
| `replicaCount` | Number of replicas | `1` |
| `rawDeploymentMode` | Use raw Deployment instead of other controllers (standard mode) | `true` |
| `image.repository` | Container image repository | `llamastack/distribution-starter` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `service.port` | Service port | `8321` |
| `progressDeadlineSeconds` | Deployment progress deadline (standard mode) | `3600` |
| `strategy.type` | Deployment strategy (standard mode) | `Recreate` |
| `vertexai.enabled` | Enable VertexAI provider | `false` |
| `vertexai.projectId` | Google Cloud project ID for VertexAI | `""` |
| `vertexai.location` | Google Cloud region/location for VertexAI | `""` |
| `gcpServiceAccount.name` | GCP service account secret name | `gcp-service-account` |
| `gcpServiceAccount.mountPath` | Path where GCP service account is mounted | `/var/secrets/gcp-service-account.json` |
| `gcpServiceAccountFile` | GCP service account file (use --set-file) | `""` |

### Model Configuration

The chart supports multiple models that can be enabled/disabled. Models can be served by:
1. **Local LLM Service** (same namespace) - no URL needed, automatically generated
2. **Remote vLLM endpoints** - provide explicit URL
3. **VertexAI** - Google Cloud hosted models

```yaml
models:
  # Local model (served by LLM Service in same namespace)
  llama-3-2-3b-instruct:
    id: meta-llama/Llama-3.2-3B-Instruct
    enabled: true
    # No URL needed - auto-generated as:
    # http://llama-3-2-3b-instruct-predictor.{namespace}.svc.cluster.local:8080/v1
  
  # Optional moderation model (OGX 1.x: use MODERATION_ENDPOINT, not registerShield)
  llama-guard-3-8b:
    id: meta-llama/Llama-Guard-3-8B
    enabled: true
    url: "http://remote-vllm-service:8000/v1"
  
  # Another local model
  llama-3-1-8b-instruct:
    id: meta-llama/Llama-3.1-8B-Instruct
    enabled: false
```

### Content moderation (OGX 1.x)

The **Safety** and **Shields** APIs were removed in OGX 1.x. Guardrails use an OpenAI-compatible **`/v1/moderations`** endpoint configured on the **responses** provider:

```yaml
providers:
  responses:
    - provider_id: builtin
      provider_type: inline::builtin
      config:
        moderation_endpoint: ${env.MODERATION_ENDPOINT:+}
```

Set `MODERATION_ENDPOINT` on the deployment (for example to a Llama Guard vLLM moderations URL). The chart default leaves moderation disabled when the variable is unset.

`registerShield` in `values.yaml` model entries is **ignored** by the chart (kept only for backward-compatible values files).

### VertexAI Configuration

For Google Cloud VertexAI integration, you **must** provide a service account file:

```yaml
vertexai:
  enabled: true
  projectId: your-gcp-project-id
  location: us-central1

gcpServiceAccount:
  name: gcp-service-account
  mountPath: /var/secrets/gcp-service-account.json
```

**Required**: Use `--set-file gcpServiceAccountFile=path/to/service-account.json` during installation to provide the GCP service account credentials. Without this file, VertexAI integration will not work.

### Environment Variables

```yaml
env:
  - name: OTEL_ENDPOINT
    value: http://otel-collector-collector.observability-hub.svc.cluster.local:4318/v1/traces
  - name: POSTGRES_USER
    valueFrom:
      secretKeyRef:
        key: user
        name: pgvector
  - name: POSTGRES_PASSWORD
    valueFrom:
      secretKeyRef:
        key: password
        name: pgvector
```

### Storage Configuration
<!-- TODO -->
```yaml
volumes:
  - configMap:
      defaultMode: 420
      name: run-config
    name: run-config-volume
  - name: dot-llama
    persistentVolumeClaim:
      claimName: ogx-ai-data
  - emptyDir: {}
    name: cache

volumeMounts:
  - mountPath: /app-config
    name: run-config-volume
  - mountPath: /.llama
    name: dot-llama
  - mountPath: /.cache
    name: cache
```

### Operator Mode Deployment

When `managedByOperator: true`, the chart creates:
1. A **ConfigMap** (`run-config`) containing the ogx-ai configuration (models, providers, etc.)
2. A **LlamaStackDistribution** custom resource that references this ConfigMap and defines the deployment characteristics
3. **Secrets** for environment variables and credentials
4. A **PersistentVolumeClaim** (`ogx-ai-data`) for model storage and cache

The ogx-ai operator then reconciles the LlamaStackDistribution CRD to create and manage:
- Deployment
- Service  
- NetworkPolicy (if network access controls are specified)
- Ingress/Route (if `network.exposeRoute` is true)
- HorizontalPodAutoscaler (if autoscaling is enabled)
- PodDisruptionBudget (if configured)

#### Operator Mode Benefits

- **Declarative Management**: Entire stack configuration in a single CRD
- **Automatic Reconciliation**: Operator ensures desired state is maintained
- **Simplified Operations**: Operator handles complex lifecycle operations
- **Consistent Configuration**: CRD schema validates configuration at admission time

#### Operator Mode Example

```yaml
managedByOperator: true

replicaCount: 1

# Operator-specific features
network:
  # Expose externally via Ingress/Route
  exposeRoute: true
  # Allow access from specific namespaces
  allowedFrom:
    namespaces:
      - data-science-project
      - ml-workloads
    labels:
      - team/authorized

# Configure uvicorn workers for better performance
workers: 4

# Pod disruption budget for high availability
podDisruptionBudget:
  minAvailable: 2

# Autoscaling configuration
autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

image:
  repository: llamastack/distribution-starter
  tag: "0.6.0"
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 8321

# Enable VertexAI
vertexai:
  enabled: true
  projectId: my-gcp-project
  location: us-central1

# Enable specific models
models:
  llama-3-2-3b-instruct:
    enabled: true
  llama-guard-3-8b:
    enabled: true
    registerShield: true

# Resource limits
resources:
  requests:
    memory: "4Gi"
    cpu: "4"  # Matches workers count
  limits:
    memory: "8Gi"
    cpu: "8"

# Agent provider configuration
providers:
  agents:
    - provider_id: meta-reference
      provider_type: inline::meta-reference
      config:
        persistence:
          agent_state:
            namespace: agents
            backend: kv_default
```

#### Minimal Operator Mode Example

```yaml
# Minimal configuration using operator mode
managedByOperator: true

models:
  llama-3-2-3b-instruct:
    enabled: true
```

The operator will use default settings and create all necessary resources.

#### Viewing the Created Resources

```bash
# Get the LlamaStackDistribution resource (shortname: llsd)
kubectl get llamastackdistribution
# or
kubectl get llsd

# View detailed status including phase, versions, and available replicas
kubectl get llsd ogx-ai -o wide

# Describe the resource to see conditions and events
kubectl describe llsd ogx-ai

# View the full CRD specification
kubectl get llsd ogx-ai -o yaml

# View the ConfigMap referenced by the CRD
kubectl get configmap run-config -o yaml

# Check the service URL
kubectl get llsd ogx-ai -o jsonpath='{.status.serviceURL}'

# Check the external route URL (if exposeRoute is true)
kubectl get llsd ogx-ai -o jsonpath='{.status.routeURL}'

# View provider health status
kubectl get llsd ogx-ai -o jsonpath='{.status.distributionConfig.providers}'
```

### Complete Example values.yaml (Standard Mode)

```yaml
replicaCount: 1
rawDeploymentMode: true

image:
  repository: ogx/distribution-starter
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 8321

# Enable VertexAI
vertexai:
  enabled: true
  projectId: my-gcp-project
  location: us-central1

# Enable specific models
models:
  llama-3-2-3b-instruct:
    enabled: true
  llama-guard-3-8b:
    enabled: true
    registerShield: true

# Resource limits
resources:
  requests:
    memory: "4Gi"
    cpu: "1000m"
  limits:
    memory: "8Gi"
    cpu: "2000m"

# Agent provider configuration
providers:
  responses:
    - provider_id: builtin
      provider_type: inline::builtin
      config:
        persistence_store:
          type: sqlite
          db_path: ${env.SQLITE_STORE_DIR:=~/.llama/distributions/starter}/agents_store.db
```

## Usage

### Accessing the API

The OGX API is available on port 8321:

```bash
# Port forward for local access
oc port-forward svc/ogx-ai 8321:8321

# Test the API
curl http://localhost:8321/models
```

### OpenShift Route

Create a route for external access:

```bash
oc expose service ogx-ai
oc get routes ogx-ai
```

### API Examples

#### List Available Models
```bash
curl -X GET http://localhost:8321/models
```

#### Generate Text Completion
```bash
curl -X POST http://localhost:8321/inference/completion \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "llama-3-2-3b-instruct",
    "content": {
      "type": "text",
      "text": "What is artificial intelligence?"
    }
  }'
```

#### Create Embeddings
```bash
curl -X POST http://localhost:8321/inference/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "llama-3-2-3b-instruct",
    "contents": ["Hello world", "How are you?"]
  }'
```

### Integration with Vector Database

OGX integrates with PGVector for storing embeddings:

```bash
# Check database connection
oc exec -it deployment/ogx-ai -- env | grep POSTGRES
```

## Monitoring and Troubleshooting

### Checking Service Health

**Standard Mode:**
```bash
# Check pod status
oc get pods -l app.kubernetes.io/name=ogx-ai

# Check deployment
oc get deployment ogx-ai

# Check service
oc get svc ogx-ai

# Test health endpoint
oc exec -it deployment/ogx -- curl localhost:8321/health
```

**Operator Mode:**
```bash
# Check LlamaStackDistribution resource and its phase
kubectl get llsd ogx-ai -o wide

# Check resource status, conditions, and events
kubectl describe llsd ogx-ai

# View detailed status information
kubectl get llsd ogx-ai -o jsonpath='{.status}' | jq

# Check pods created by the operator
kubectl get pods -l app.kubernetes.io/managed-by=ogx-ai-operator

# Check deployment created by operator
kubectl get deployment -l app.kubernetes.io/managed-by=ogx-ai-operator

# Check service created by operator
kubectl get svc -l app.kubernetes.io/managed-by=ogx-ai-operator

# Check operator logs for reconciliation errors
kubectl logs -n ogx-ai-operator-system -l app.kubernetes.io/name=ogx-ai-operator --tail=100 -f

# Check the ConfigMap referenced by the CRD
kubectl get configmap run-config

# Test health endpoint (once pods are running)
kubectl exec -it deployment/ogx-ai -- curl localhost:8321/v1/health

# Check network policies (if allowedFrom is configured)
kubectl get networkpolicy

# Check ingress/route (if exposeRoute is true)
kubectl get ingress
# or on OpenShift
oc get route
```

### Viewing Logs

```bash
# Service logs
oc logs -l app.kubernetes.io/name=ogx -f

# Previous container logs (if crashed)
oc logs -l app.kubernetes.io/name=ogx --previous

# Check specific container logs
oc logs deployment/ogx -c ogx -f
```

### Common Issues

1. **`ValueError: invalid literal for int() ... 'tcp://...'` on startup**:
   - Kubernetes injects `OGX_PORT=tcp://<cluster-ip>:8321` when a Service is named `ogx`, which conflicts with the OGX CLI expecting a numeric port.
   - This chart sets `enableServiceLinks: false` and an explicit `OGX_PORT` matching `service.port`. Upgrade the chart or set the same on older manifests.

2. **`ValueError: API 'safety' does not exist`** (or `agents`, `scoring`, etc.):
   - OGX 1.x removed several Llama Stack-era APIs. This chart targets OGX 1.x (`responses`, `inference`, `vector_io`, `files`, `tool_runtime`, `batches`).
   - Upgrade the chart and restart the deployment so `run-config` is regenerated.

3. **`ValueError: Provider inline::rag-runtime is not available for API tool_runtime`**:
   - The default image `ogxai/distribution-starter` does not include the RAG runtime provider.
   - Chart defaults now set `toolRuntime.ragRuntime.enabled: false` and `toolGroups.rag.enabled: false`.
   - Only enable those values if your OGX distribution includes `inline::rag-runtime`.

4. **`ValidationError: ReferenceBatchesImplConfig sqlstore Field required`**:
   - OGX 1.x batches provider config requires `sqlstore`, not the legacy `kvstore` block.
   - Upgrade the chart so `run-config` uses `sqlstore.table_name: batches` with `backend: sql_default`.

5. **Model Download Failures**:
   - Check internet connectivity
   - Verify HuggingFace access tokens
   - Ensure sufficient storage space
   - Check model permissions

2. **VertexAI Connection Issues**:
   - Verify GCP service account credentials
   - Check project ID and location settings
   - Validate API permissions
   - Ensure VertexAI APIs are enabled

3. **Memory/Storage Issues**:
   - Models require significant storage and memory
   - Check PVC size and availability
   - Monitor resource usage
   - Consider using smaller models for testing

4. **Database Connection Errors**:
   - Verify PGVector is running
   - Check database credentials in secrets
   - Validate network connectivity
   - Test database schema compatibility

5. **Model Endpoint Issues**:
   - Ensure LLM Service is deployed in same namespace (for local models)
   - Verify model predictor services are running
   - Check if model URLs are accessible
   - Validate model configuration in LLM Service

6. **Operator Mode Issues**:
   - Verify ogx-ai operator is installed: `kubectl get deployment -n ogx-ai-operator-system`
   - Check if CRD is registered: `kubectl get crd llamastackdistributions.llamastack.io`
   - Review operator logs for reconciliation errors: `kubectl logs -n ogx-ai-operator-system -l app.kubernetes.io/name=ogx-ai-operator`
   - Check LlamaStackDistribution status and phase: `kubectl get llsd -o wide`
   - View conditions for error details: `kubectl get llsd ogx-ai -o jsonpath='{.status.conditions}' | jq`
   - Ensure operator has proper RBAC permissions
   - Verify the ConfigMap exists: `kubectl get configmap run-config`
   - Check for admission webhook errors in events: `kubectl get events --sort-by='.lastTimestamp'`
   - Verify distribution image is accessible: `kubectl describe llsd ogx-ai | grep -A5 distribution`

### Resource Requirements

OGX is a lightweight orchestration layer and doesn't require GPU resources:

```yaml
# Typical OGX resource requirements
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "1000m"
```

**Note**: Model inference resources are managed by the LLM Service component, not OGX.

## Security and Authentication

### Custom Authentication

Configure custom authentication provider:

```yaml
auth:
  provider_config:
    type: "custom"
    endpoint: "https://auth.example.com/validate"
  access_policy:
    - permit:
        actions: [create]
        resource: session::*
      description: all users have create access to sessions
    - permit:
        actions: [read]
        resource: model::*
      description: all users have read access to models
```

### Service Account Security

The chart creates minimal RBAC permissions:
- ConfigMap read access
- Secret read access
- PVC read/write access

## Upgrading

### Upgrading in Standard Mode

```bash
# Upgrade with new image version
helm upgrade ogx ./helm \
  --set image.tag=v0.3.0

# Check rollout status
oc rollout status deployment/ogx
```

### Upgrading in Operator Mode

```bash
# Upgrade the Helm release (updates the CRD)
helm upgrade ogx-ai ./helm \
  --set managedByOperator=true \
  --set image.tag=v0.3.0

# Watch the operator reconcile the changes
kubectl get llamastackdistribution ogx-ai -w

# Check operator-created deployment status
oc rollout status deployment/ogx-ai
```

### Switching Between Modes

**Important**: Switching between standard and operator modes requires careful consideration:

**From Standard to Operator Mode:**
```bash
# 1. Ensure operator is installed
kubectl get crd llamastackdistributions.llama.meta.com

# 2. Backup current configuration
kubectl get deployment ogx-ai -o yaml > ogx-ai-backup.yaml

# 3. Upgrade to operator mode
helm upgrade ogx-ai ./helm \
  --set managedByOperator=true \
  --reuse-values

# Note: This will delete the existing Deployment/Service/ConfigMap
# and create a LlamaStackDistribution CRD. The operator will then
# recreate these resources. Expect brief downtime during transition.
```

**From Operator to Standard Mode:**
```bash
# 1. Backup the CRD
kubectl get llamastackdistribution ogx-ai -o yaml > ogx-ai-crd-backup.yaml

# 2. Upgrade to standard mode
helm upgrade ogx-ai ./helm \
  --set managedByOperator=false \
  --reuse-values

# Note: This will delete the LlamaStackDistribution CRD
# and create standard Kubernetes resources directly.
# Expect brief downtime during transition.
```

## Uninstalling

```bash
# Remove chart
helm uninstall ogx

# Remove persistent data
oc delete pvc ogx-ai-data

# Remove secrets (if needed)
oc delete secret gcp-service-account
```

## Integration with Other Components

This chart integrates with:

- **LLM Service**: Deploy and serve models locally in the same namespace. OGX automatically discovers and configures models deployed by the LLM Service chart
- **PGVector**: Vector database for embeddings and agent memory
- **MinIO**: Model and data storage
- **Ingestion Pipeline**: Document processing workflows
- **VertexAI**: Google Cloud AI services
- **MCP Servers**: External tool integration

### OGX + LLM Service Integration

OGX works seamlessly with the LLM Service chart to provide a complete model serving solution:

```bash
# 1. Deploy models using LLM Service
helm install llm-service ../llm-service/helm \
  --set models.llama-3-2-3b-instruct.enabled=true \
  --set models.llama-guard-3-8b.enabled=true

# 2. Deploy OGX and configure it to use the deployed models
helm install ogx ./helm \
  --set models.llama-3-2-3b-instruct.enabled=true \
  --set models.llama-guard-3-8b.enabled=true \
  --set models.llama-guard-3-8b.registerShield=true
```

**How it works**:
- LLM Service deploys models as InferenceServices with predictors
- OGX automatically generates URLs pointing to these predictors
- Model URLs follow the pattern: `{model-name}-predictor.{namespace}.svc.cluster.local:8080/v1`
- OGX provides unified API access and orchestration layer
- Safety shields and agent capabilities are handled by OGX
- Model inference is handled by LLM Service/vLLM

**Benefits of this approach**:
- **Separation of concerns**: LLM Service handles model deployment, OGX handles orchestration
- **Automatic discovery**: No manual URL configuration needed for local models
- **Unified API**: Single endpoint for multiple models and capabilities
- **Safety integration**: Automatic shield model integration
- **Agent capabilities**: Advanced AI agent features through OGX

### OGX + PGVector Integration

OGX can be deployed with the PGVector component from this repository to provide persistent vector storage for embeddings, agent memory, and RAG capabilities:

```bash
# 1. Deploy PGVector using the pgvector chart from this repo
helm install pgvector ../pgvector/helm \
  --set secret.dbname=ogx_vectors \
  --set extraDatabases[0].name=agent_memory \
  --set extraDatabases[0].vectordb=true

# 2. Deploy OGX configured to use the PGVector deployment
helm install ogx ./helm \
  --set models.llama-3-2-3b-instruct.enabled=true
  # PGVector connection is automatically configured via environment variables
```

**How it works**:
- The PGVector chart from this repo creates a PostgreSQL deployment with pgvector extension
- OGX automatically connects using the `pgvector` secret created by the PGVector chart
- Environment variables (`POSTGRES_USER`, `POSTGRES_PASSWORD`, etc.) are automatically configured
- OGX uses PGVector for vector storage, agent memory, and RAG operations

**What OGX stores in PGVector**:
- **Vector embeddings**: Document and text embeddings for RAG
- **Agent memory**: Persistent memory for AI agents across sessions
- **Knowledge base**: Long-term storage of facts and learned information
- **Session context**: Conversation history and multi-turn interactions

## Advanced Configuration

### MCP Servers Integration

```yaml
mcp-servers:
  weather-server:
    endpoint: "http://mcp-weather:8000/sse"
    capabilities: ["weather_lookup"]
```

### Custom Model Providers

```yaml
providers:
  inference:
    - provider_id: custom-vllm
      provider_type: remote::vllm
      config:
        url: "http://custom-vllm-service:8000/v1"
```

### Observability Integration

```yaml
env:
  - name: OTEL_ENDPOINT
    value: "http://jaeger-collector:14268/api/traces"
  - name: OTEL_SERVICE_NAME
    value: "ogx"
```