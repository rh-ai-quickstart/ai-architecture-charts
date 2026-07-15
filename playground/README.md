# Playground Helm Chart

A Helm chart for integrating hub-deployed resources with the RHOAI Gen AI Studio Playground UI. It registers MCP servers and external model endpoints with the Playground, and optionally configures dashboard feature flags via `OdhDashboardConfig`.

## Overview

This chart does **not** deploy any workloads. Instead, it creates ConfigMaps and Secrets that register existing resources with the Gen AI Studio Playground:

- **MCP Server Registration**: Creates a ConfigMap (`gen-ai-aa-mcp-servers`) in `redhat-ods-applications` that tells the Playground about available MCP servers
- **External Model Endpoints**: Creates a ConfigMap (`gen-ai-aa-custom-model-endpoints`) and Secrets that pre-register external OpenAI-compatible models (Gemini, OpenAI, Anthropic, etc.)
- **Vector Store Registration**: Creates a ConfigMap (`gen-ai-aa-vector-stores`) in the project namespace that registers external vector stores for RAG in the Playground Knowledge tab
- **Dashboard Configuration**: Optionally creates an `OdhDashboardConfig` CR to enable Gen AI Studio features



## Prerequisites

- OpenShift cluster with RHOAI 3.4+ installed
- Gen AI Studio Playground enabled (`genAiStudio: true` in dashboard config)
- For external models: `aiAssetCustomEndpoints: true` and `externalProviders: true` in `OdhDashboardConfig`
- For vector stores: `externalVectorStores: true` in `OdhDashboardConfig`
- For prompt management (MLflow): `promptManagement: true` in `OdhDashboardConfig` and `mlflowoperator: Managed` in `DataScienceCluster`
- For external models: outbound network access to the provider API



## Installation



### As a dependency in a parent chart

Add to your `Chart.yaml`:

```yaml
dependencies:
  - name: playground
    version: 0.0.1
    repository: https://rh-ai-quickstart.github.io/ai-architecture-charts
    condition: playground.enabled
```

Then configure in your `values.yaml`:

```yaml
playground:
  enabled: true
  dashboardConfig:
    enabled: true
  genAiStudio: true
  aiAssetCustomEndpoints: true
  externalProviders: true
  mcpServers:
    servers:
      - name: My-MCP-Server
        url: "http://my-mcp-server.{{ .Release.Namespace }}.svc:8000/mcp/"
        description: My MCP server description
  customEndpoints:
    enabled: true
    endpoints:
      - modelId: <model-id>
        displayName: <display-name>
        url: <provider-openai-compatible-url>
        apiKey: ""
```

Provide API keys by creating Secrets before installing. Each endpoint references a Secret by name (`endpoint-api-key-N`):

```bash
oc create secret generic endpoint-api-key-1 --from-literal=api_key=<your-api-key-1> -n <namespace>
oc create secret generic endpoint-api-key-2 --from-literal=api_key=<your-api-key-2> -n <namespace>
```

Then install:

```bash
helm upgrade --install <release-name> ./helm
```

> **Note:** Do not pass API keys via `--set` on array elements (e.g. `--set playground.customEndpoints.endpoints[0].apiKey=...`) as this will wipe other fields in the array. Always pre-create the Secrets or use a values override file.

Alternatively, use a local values override file (not committed to git):

```bash
helm upgrade --install <release-name> ./helm -f secrets-values.yaml
```

Where `secrets-values.yaml` contains the full endpoints array with API keys:

```yaml
playground:
  customEndpoints:
    endpoints:
      - modelId: <model-id>
        displayName: <display-name>
        url: <provider-openai-compatible-url>
        apiKey: "<your-api-key>"
```



### Standalone installation

```bash
helm install playground ./helm \
  --set dashboardConfig.enabled=true \
  --set playground.genAiStudio=true \
  --set playground.aiAssetCustomEndpoints=true \
  --set playground.externalProviders=true
```



## Configuration



### Dashboard Feature Flags


| Parameter                           | Description                                                 | Default |
| ----------------------------------- | ----------------------------------------------------------- | ------- |
| `dashboardConfig.enabled`           | Create the OdhDashboardConfig CR (requires RHOAI operator)  | `false` |
| `playground.genAiStudio`            | Enable Gen AI Studio in the dashboard                       | `false` |
| `playground.aiAssetCustomEndpoints` | Enable custom endpoint creation                             | `false` |
| `playground.externalProviders`      | Allow third-party provider endpoints (OpenAI, Gemini, etc.) | `false` |
| `playground.externalVectorStores`   | Enable external vector store connections                    | `false` |
| `playground.mcpCatalog`             | Enable MCP catalog in the dashboard                         | `false` |
| `playground.mlflow`                 | Enable MLflow integration                                   | `false` |
| `playground.modelAsService`         | Enable Models-as-a-Service                                  | `false` |




### MCP Server Registration


| Parameter                          | Description                           | Default                   |
| ---------------------------------- | ------------------------------------- | ------------------------- |
| `mcpServers.enabled`               | Create the MCP servers ConfigMap      | `true`                    |
| `mcpServers.namespace`             | Namespace for the ConfigMap           | `redhat-ods-applications` |
| `mcpServers.servers`               | List of MCP server entries            | `[]`                      |
| `mcpServers.servers[].name`        | Display name (ConfigMap key)          |                           |
| `mcpServers.servers[].url`         | Server URL (supports `tpl` expansion) |                           |
| `mcpServers.servers[].description` | Optional description                  |                           |




### Custom External Model Endpoints


| Parameter                                        | Description                                             | Default          |
| ------------------------------------------------ | ------------------------------------------------------- | ---------------- |
| `customEndpoints.enabled`                        | Create the external endpoints ConfigMap and Secrets     | `false`          |
| `customEndpoints.namespace`                      | Namespace for resources (defaults to release namespace) | `""`             |
| `customEndpoints.endpoints`                      | List of external model endpoints                        | `[]`             |
| `customEndpoints.endpoints[].modelId`            | Model ID as recognized by the provider                  |                  |
| `customEndpoints.endpoints[].displayName`        | Friendly name shown in the Playground UI                |                  |
| `customEndpoints.endpoints[].url`                | Provider API base URL                                   |                  |
| `customEndpoints.endpoints[].apiKey`             | API key (pre-create Secret or use `-f` override)        | `""`             |
| `customEndpoints.endpoints[].providerType`       | Provider type identifier                                | `remote::openai` |
| `customEndpoints.endpoints[].modelType`          | Model type (`llm` or `embedding`)                       | `llm`            |
| `customEndpoints.endpoints[].embeddingDimension` | Embedding dimension (required for embedding models)     |                  |




### Vector Store Registration


| Parameter                                     | Description                                                            | Default            |
| --------------------------------------------- | ---------------------------------------------------------------------- | ------------------ |
| `vectorStores.enabled`                        | Create the vector stores ConfigMap                                     | `false`            |
| `vectorStores.namespace`                      | Namespace for the ConfigMap (defaults to release namespace)            | `""`               |
| `vectorStores.stores`                         | List of vector store entries                                           | `[]`               |
| `vectorStores.stores[].providerId`            | Unique provider identifier                                             | `provider-N`       |
| `vectorStores.stores[].providerType`          | Provider type (`remote::pgvector`, `remote::milvus`, `remote::qdrant`) | `remote::pgvector` |
| `vectorStores.stores[].host`                  | Database host (supports `tpl` expansion)                               |                    |
| `vectorStores.stores[].port`                  | Database port                                                          |                    |
| `vectorStores.stores[].db`                    | Database name                                                          |                    |
| `vectorStores.stores[].user`                  | Database user                                                          |                    |
| `vectorStores.stores[].uri`                   | Connection URI (for Milvus/Qdrant)                                     |                    |
| `vectorStores.stores[].distanceMetric`        | Distance metric (e.g. `COSINE`)                                        |                    |
| `vectorStores.stores[].credentialSecret.name` | Secret name for credentials                                            |                    |
| `vectorStores.stores[].credentialSecret.key`  | Key within the Secret                                                  |                    |
| `vectorStores.stores[].vectorStoreId`         | Unique vector store identifier                                         |                    |
| `vectorStores.stores[].displayName`           | Friendly name shown in the UI                                          |                    |
| `vectorStores.stores[].embeddingModel`        | Embedding model ID (must be registered in the Playground's LlamaStack) |                    |
| `vectorStores.stores[].embeddingDimension`    | Embedding vector dimension                                             | `768`              |
| `vectorStores.stores[].description`           | Optional description                                                   |                    |


**Important notes on vector stores:**

- The ConfigMap is created in the **project namespace** (not `redhat-ods-applications`)
- The `embeddingModel` must match a model registered in the Playground's LlamaStack



## Resources Created


| Template                          | Resource                                       | Namespace                 | Condition                                         |
| --------------------------------- | ---------------------------------------------- | ------------------------- | ------------------------------------------------- |
| `playground.yaml`                 | `OdhDashboardConfig`                           | `redhat-ods-applications` | `dashboardConfig.enabled`                         |
| `mcp-servers-configmap.yaml`      | ConfigMap `gen-ai-aa-mcp-servers`              | `redhat-ods-applications` | `mcpServers.enabled` and servers non-empty        |
| `custom-endpoints-configmap.yaml` | ConfigMap `gen-ai-aa-custom-model-endpoints`   | Release namespace         | `customEndpoints.enabled` and endpoints non-empty |
| `custom-endpoints-secrets.yaml`   | Secret `endpoint-api-key-N` (one per endpoint) | Release namespace         | `customEndpoints.enabled` and `apiKey` non-empty  |
| `vector-stores-configmap.yaml`    | ConfigMap `gen-ai-aa-vector-stores`            | Release namespace         | `vectorStores.enabled` and stores non-empty       |
| `post-install-job.yaml`           | Job (polls for LlamaStack, runs ingestion)     | Release namespace         | `postInstall.enabled` and command non-empty       |




## Examples



### Register MCP servers only (no external models)

```yaml
playground:
  enabled: true
  mcpServers:
    servers:
      - name: GitHub-MCP
        url: "https://api.githubcopilot.com/mcp/x/repos/readonly"
        description: GitHub repository access
```



### External model endpoint

```yaml
playground:
  enabled: true
  dashboardConfig:
    enabled: true
  genAiStudio: true
  aiAssetCustomEndpoints: true
  externalProviders: true
  customEndpoints:
    enabled: true
    endpoints:
      - modelId: <inference-model-id>
        displayName: <display-name>
        url: <provider-openai-compatible-url>
        apiKey: ""
      - modelId: <embedding-model-id>
        displayName: <display-name>
        url: <provider-openai-compatible-url>
        apiKey: ""
        modelType: embedding
        embeddingDimension: 768
      - modelId: <guardrail-model-id>
        displayName: <display-name>
        url: <provider-openai-compatible-url>
        apiKey: ""
```



### Vector store with pgvector

```yaml
playground:
  enabled: true
  externalVectorStores: true
  vectorStores:
    enabled: true
    stores:
      - providerId: pgvector-provider
        providerType: remote::pgvector
        host: "pgvector.{{ .Release.Namespace }}.svc.cluster.local"
        port: 5432
        db: rag_blueprint
        user: postgres
        distanceMetric: COSINE
        credentialSecret:
          name: pgvector
          key: password
        vectorStoreId: vs-my-store-001
        displayName: "My Vector Store (pgvector)"
        embeddingModel: <embedding-model-id>
        embeddingDimension: 768
        description: My knowledge base
```



### Post-Install Ingestion Job

The chart includes a generic Job template that can run a container after deploy. It uses an init container to poll for the Playground's LlamaStack (`lsd-genai-playground-service`) - the Job waits indefinitely until the user creates the Playground through the UI, then runs the ingestion.


| Parameter                               | Description                             | Default |
| --------------------------------------- | --------------------------------------- | ------- |
| `postInstall.enabled`                   | Create the ingestion Job                | `false` |
| `postInstall.image`                     | Container image to run                  | `""`    |
| `postInstall.waitForLlamaStack.enabled` | Poll for LlamaStack before running      | `false` |
| `postInstall.waitForLlamaStack.url`     | LlamaStack URL to poll                  | `""`    |
| `postInstall.command`                   | Command to run in the container         | `[]`    |
| `postInstall.env`                       | Environment variables for the container | `[]`    |
| `postInstall.backoffLimit`              | Number of retries                       | `2`     |


```yaml
playground:
  postInstall:
    enabled: true
    image: <ingestion-pipeline-image>
    waitForLlamaStack:
      enabled: true
      url: http://lsd-genai-playground-service:8321
    command:
      - sh
      - -c
      - |
        ingestion-pipeline &
        sleep 5
        until wget -qO- http://localhost:8000/health > /dev/null 2>&1; do sleep 2; done
        wget -qO- --post-data= http://localhost:8000/runbooks/sync
        wget -qO- --post-data= http://localhost:8000/runbooks/ingest
    env:
      - name: LLAMASTACK_HOST
        value: lsd-genai-playground-service
```



### MLflow Prompt Management

MLflow prompt save/load is managed at the platform level - no chart configuration needed. To enable:

1. Ensure `mlflowoperator: Managed` in the `DataScienceCluster` CR
2. Ensure `promptManagement: true` in the `OdhDashboardConfig`

These are cluster-scoped settings that must be configured by a cluster admin:

```bash
oc patch datasciencecluster default-dsc --type=merge \
  -p '{"spec":{"components":{"mlflowoperator":{"managementState":"Managed"}}}}'

oc patch OdhDashboardConfig odh-dashboard-config -n redhat-ods-applications --type=merge \
  -p '{"spec":{"dashboardConfig":{"promptManagement":true}}}'
```

Once enabled, users can save and load prompts in the Playground's Prompt tab. Saved prompts are stored via MLflow and visible on the Gen AI Studio > Prompts page.

## Security Notes

- API keys are stored in Kubernetes Secrets, never in ConfigMaps or source code
- The `apiKey` field in `values.yaml` should always be empty (`""`) -- pre-create Secrets before deploying
- Do not pass API keys via `--set` on array elements as Helm will wipe other fields
- Enabling `externalProviders` allows data (RAG context, MCP tool results, user input) to be sent outside the cluster



## Uninstall

```bash
helm uninstall playground
```

