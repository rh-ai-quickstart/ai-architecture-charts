# AI Architecture Charts

A comprehensive collection of Helm charts for deploying end-to-end AI/ML infrastructure on OpenShift, featuring LlamaStack orchestration, model serving, vector databases, and supporting services.

## Overview

This repository provides production-ready Helm charts for building AI applications with components that work seamlessly together. The architecture supports various AI use cases including RAG (Retrieval-Augmented Generation), conversational AI, document processing, and AI agent workflows.

## Architecture Components

### 🧠 Core AI Services

#### [LlamaStack](./llama-stack/README.md)
Comprehensive AI orchestration platform that provides a unified API for multiple model providers, safety shields, and AI agent capabilities. Supports local models (via LLM Service), remote vLLM endpoints, and VertexAI integration.

**Key Features:**
- Multi-provider model support (local, remote, VertexAI)
- Safety shields with Llama Guard and other safety models
- AI agent capabilities with persistent memory
- Automatic model discovery and URL generation

#### [LLM Service](./llm-service/README.md)
High-performance model serving infrastructure using vLLM runtime with OpenShift AI/KServe integration. Supports GPU and CPU deployment modes with any models compatible with vLLM.

**Key Features:**
- vLLM-based model serving with OpenAI-compatible API
- Support for any vLLM-compatible models and sizes
- GPU/CPU deployment flexibility
- Tool calling and function execution support

### 📊 Data & Storage Services

#### [PGVector](./pgvector/README.md)
PostgreSQL with pgvector extension providing high-performance vector database capabilities for storing and querying embeddings in AI/ML applications.

**Key Features:**
- Vector similarity search (cosine, L2, inner product)
- Multiple index types (IVFFlat, HNSW)
- Support for various embedding dimensions
- ACID compliance with PostgreSQL reliability

#### [MinIO](./minio/README.md)
S3-compatible object storage server for documents, models, and data in AI/ML pipelines. Provides scalable storage with web console management.

**Key Features:**
- S3-compatible API
- Web-based management console
- Bucket policies and lifecycle management
- Sample file upload functionality

#### [Oracle 23ai](./oracle23ai/README.md)
Oracle Database Free 23ai with AI Vector features, providing enterprise-grade database capabilities with built-in vector operations for AI applications.

**Key Features:**
- Native vector operations and similarity search
- JSON duality and graph analytics
- Enterprise database reliability
- AI-optimized storage and indexing

**TPC-DS Data Population Job:**
The Oracle 23ai chart includes an automated TPC-DS (Transaction Processing Performance Council Decision Support) data population job that creates comprehensive test datasets for AI/ML applications. This Kubernetes Job replaces manual database setup scripts with a cloud-native approach:

- **Purpose**: Automatically populates the Oracle database with standardized TPC-DS benchmark data (25 tables with synthetic retail/e-commerce data)
- **Scale Factor**: Configurable data volume (default generates ~1GB of test data)
- **Schema Management**: Creates both SYSTEM and Sales schemas with proper data distribution
- **Security**: Applies read-only restrictions to the Sales user for safe AI MCP server integration
- **Automation**: Eliminates manual database setup, ensuring consistent test data across deployments
- **Integration**: Provides realistic datasets for RAG applications, vector search testing, and AI agent development

The job runs automatically when `tpcds.enabled=true` and handles the complete lifecycle from database readiness verification to data loading and security configuration.

### 🔧 Pipeline & Processing Services

#### [Ingestion Pipeline](./ingestion-pipeline/README.md)
Comprehensive data ingestion pipeline that processes documents from various sources (S3, GitHub, URLs) and stores vector embeddings for semantic search and RAG applications.

**Key Features:**
- Multi-source data ingestion (S3/MinIO, GitHub, URLs)
- Document chunking and embedding generation
- REST API for pipeline management
- Integration with vector databases

#### [Configure Pipeline](./configure-pipeline/README.md)
Jupyter notebook environment for RAG configuration and pipeline setup. Provides interactive tools for configuring and testing AI pipelines.

**Key Features:**
- Pre-configured Jupyter environment
- RAG pipeline configuration tools
- MinIO integration for data access
- Template and configuration management

### 🔌 Integration & Tools

#### [MCP Servers](./mcp-servers/README.md)
Model Context Protocol servers that provide external tools and capabilities to AI models, enabling AI agents to interact with external systems and APIs.

**Key Features:**
- Weather information services
- Server-Sent Events (SSE) endpoints
- Custom tool development framework
- Integration with LlamaStack agents

#### [Oracle SQLcl MCP](./oracle-sqlcl/helm/README.md)
MCP server that exposes Oracle SQLcl capabilities to AI agents via Toolhive, enabling database tooling and interactions from LlamaStack and compatible clients.

**Key Features:**
- Execute SQL/PLSQL against Oracle databases via Model Context Protocol
- Integrates with Toolhive Operator v0.4.0 (with OpenShift-specific security context settings)
- Orale connection managed via Kubernetes secrets and configurable service

## Quick Start

### Prerequisites

- OpenShift cluster
- Helm 3.x
- Sufficient storage and compute resources
- Access to container registries

### Basic Deployment

Deploy a complete AI stack with vector storage and model serving:

```bash
# 1. Deploy vector database
helm install pgvector ./pgvector/helm

# 2. Deploy object storage
helm install minio ./minio/helm

# 3. Deploy model serving
helm install llm-service ./llm-service/helm \
  --set models.llama-3-2-3b-instruct.enabled=true

# 4. Deploy LlamaStack orchestration
helm install llama-stack ./llama-stack/helm \
  --set models.llama-3-2-3b-instruct.enabled=true

# 5. Deploy ingestion pipeline
helm install ingestion-pipeline ./ingestion-pipeline/helm
```

### RAG Application Setup

For document processing and retrieval-augmented generation:

```bash
# Deploy storage and database
helm install minio ./minio/helm \
  --set sampleFileUpload.enabled=true
helm install pgvector ./pgvector/helm

# Configure pipeline
helm install configure-pipeline ./configure-pipeline/helm

# Deploy processing pipeline
helm install ingestion-pipeline ./ingestion-pipeline/helm \
  --set defaultPipeline.enabled=true \
  --set defaultPipeline.source=S3

# Deploy model serving and orchestration
helm install llm-service ./llm-service/helm \
  --set models.llama-3-2-3b-instruct.enabled=true
helm install llama-stack ./llama-stack/helm \
  --set models.llama-3-2-3b-instruct.enabled=true
```

## Integration Patterns

### LlamaStack + LLM Service
LlamaStack provides orchestration while LLM Service handles model inference:
- LLM Service deploys models as InferenceServices
- LlamaStack automatically discovers and configures model endpoints
- Unified API access through LlamaStack

### Vector Storage Integration
Both PGVector and Oracle 23ai can serve as vector databases:
- PGVector: Open-source PostgreSQL with pgvector extension
- Oracle 23ai: Enterprise database with native AI vector features
- Choose based on performance, compliance, and feature requirements

### Multi-Source Data Ingestion
Ingestion Pipeline supports various data sources:
- **S3/MinIO**: Object storage for documents and files
- **GitHub**: Repository documentation and code
- **URLs**: Direct document links and web content

## Component Dependencies

```mermaid
graph TB
    LS[LlamaStack] --> LLM[LLM Service]
    LS --> PG[PGVector]
    LS --> MCP[MCP Servers]
    
    IP[Ingestion Pipeline] --> MINIO[MinIO]
    IP --> PG
    IP --> LS
    
    CP[Configure Pipeline] --> MINIO
    CP --> IP
    
    LLM --> GPU[GPU Nodes]
    PG --> STORAGE[Persistent Storage]
    MINIO --> STORAGE
```

## Security Considerations

- **Secrets Management**: All components use Kubernetes secrets for credentials
- **Network Policies**: Implement network policies to restrict inter-component communication
- **RBAC**: Configure role-based access control for service accounts
- **TLS**: Enable TLS for external access and sensitive communications
- **Safety Shields**: Use Llama Guard or other safety models for content moderation

## Monitoring and Observability

- **Prometheus Integration**: Many components support Prometheus metrics
- **OpenTelemetry**: LlamaStack supports distributed tracing
- **Logging**: All components provide structured logging
- **Health Checks**: Kubernetes-native health and readiness probes

## Development and Customization

Each component is designed to be:
- **Configurable**: Extensive values.yaml configuration options
- **Extensible**: Support for custom models, tools, and integrations
- **Scalable**: Horizontal and vertical scaling capabilities
- **Production-ready**: Comprehensive monitoring and operational features

### Container Image Building

The repository includes automated container image building through GitHub workflows:

- **Supported components**: Components with a `build.yaml` file automatically build container images
- **Automated publishing**: Images are built and pushed to Quay.io with chart versioning
- **Custom development**: Add new components or modify existing ones with automatic CI/CD
- **Workflow integration**: Components are automatically built when changes are detected

To add container builds to a component, create a `build.yaml` file in the component directory:

```yaml
# component/build.yaml
builds:
  - name: component-name
    containerfile: Containerfile
    context: src
```

The workflow automatically discovers and builds images for all components with `build.yaml` files.

### Helm Repository and Versioning

This project maintains a Helm repository at `https://rh-ai-quickstart.github.io/ai-architecture-charts` with full version history:

- **Version tracking**: All chart versions are preserved and available for download
- **Automated publishing**: GitHub workflow automatically packages and publishes charts to the repository
- **Backward compatibility**: Previous versions remain accessible for rollbacks and compatibility
- **Index management**: Helm repository index is automatically maintained with each release

## Support and Documentation

- **Component READMEs**: Detailed documentation for each Helm chart
- **Configuration Examples**: Real-world configuration patterns
- **Troubleshooting Guides**: Common issues and solutions
- **Integration Examples**: How components work together

## Using Charts as Dependencies

These charts can be used standalone or as dependencies in larger AI applications. Each chart is designed to work independently or as part of a composed solution.

### Standalone Deployment

Each chart can be deployed individually:

```bash
# Deploy individual components
helm install pgvector ./pgvector/helm
helm install minio ./minio/helm
helm install llm-service ./llm-service/helm
```

### Chart Dependencies

Reference these charts as dependencies in your own Chart.yaml without requiring a Helm repository:

```yaml
# Chart.yaml for your AI application
apiVersion: v2
name: my-ai-application
version: 1.0.0

dependencies:
  - name: pgvector
    version: "0.1.0"
    repository: "file://../ai-architecture-charts/pgvector/helm"
  
  - name: minio
    version: "0.1.0"
    repository: "file://../ai-architecture-charts/minio/helm"
  
  - name: llm-service
    version: "0.1.0"
    repository: "file://../ai-architecture-charts/llm-service/helm"
  
  - name: llama-stack
    version: "0.2.18"
    repository: "file://../ai-architecture-charts/llama-stack/helm"
  
  - name: ingestion-pipeline
    version: "0.2.18"
    repository: "file://../ai-architecture-charts/ingestion-pipeline/helm"
```

### Configuring Subcharts

Configure the dependent charts in your values.yaml:

```yaml
# values.yaml for your AI application
pgvector:
  secret:
    dbname: "my_ai_app_vectors"
  extraDatabases:
    - name: agent_memory
      vectordb: true

minio:
  secret:
    user: "ai_app_user"
    password: "secure_password"
  sampleFileUpload:
    enabled: true
    bucket: "ai-documents"

llm-service:
  models:
    llama-3-2-3b-instruct:
      enabled: true
    llama-guard-3-8b:
      enabled: true

llama-stack:
  models:
    llama-3-2-3b-instruct:
      enabled: true
    llama-guard-3-8b:
      enabled: true
      registerShield: true

ingestion-pipeline:
  defaultPipeline:
    enabled: true
    source: S3
    S3:
      bucket_name: ai-documents
      endpoint_url: http://minio:9000
```

### Shared Configuration with Global Values

Use global values to configure multiple charts simultaneously, reducing duplication:

```yaml
# values.yaml for your AI application
global:
  models:
    llama-3-2-3b-instruct:
      enabled: true
    llama-guard-3-8b:
      enabled: true
      registerShield: true
  
  mcp-servers:
    mcp-weather:
      deploy: true

# MCP Servers Configuration Example
# To enable and configure MCP servers, add the following to your values.yaml:
mcp-servers:
  toolhive:
    crds:
      enabled: false  # Set to false if CRDs already exist
    operator:
      enabled: false  # Set to false if operator already installed

  mcp-servers:
    mcp-weather:
      mcpserver:
        enabled: true
        env:
          TAVILY_API_KEY: ""  # Add your API key if needed
        permissionProfile:
          name: network
          type: builtin

    oracle-sqlcl:
      mcpserver:
        enabled: true
        env:
          ORACLE_USER: "sales"  # Sales schema user created by Oracle DB chart
          ORACLE_PASSWORD: null  # Sourced from secret
          ORACLE_CONNECTION_STRING: null  # Sourced from secret
          ORACLE_CONN_NAME: "oracle_connection"
        envSecrets:
          ORACLE_PASSWORD:
            name: oracle23ai
            key: password
          ORACLE_CONNECTION_STRING:
            name: oracle23ai
            key: jdbc-uri
        permissionProfile:
          name: network
          type: builtin

# Individual chart configurations
pgvector:
  secret:
    dbname: "my_ai_app_vectors"

minio:
  sampleFileUpload:
    enabled: true
    bucket: "ai-documents"

# Global models will be merged with local configurations
# Both llm-service and llama-stack will use the global.models settings
```

### Deployment Workflow

```bash
# 1. Update dependencies
helm dependency update

# 2. Deploy complete AI stack
helm install my-ai-app . \
  --namespace my-ai-app \
  --create-namespace

# 3. Verify deployment
helm list -n my-ai-app
```

This approach allows you to compose comprehensive AI applications by combining these foundational charts with your own application-specific components while minimizing configuration duplication.

## Testing MCP Servers

### Using MCP Inspector

The [MCP Inspector](https://github.com/modelcontextprotocol/inspector) is a debugging and testing tool for Model Context Protocol servers. Use it to test MCP servers deployed in OpenShift.

#### Prerequisites

Install MCP Inspector on your local machine:

```bash
npm install -g @modelcontextprotocol/inspector
```

#### Testing MCP Servers in OpenShift

1. **Get MCP Server Details**:
   ```bash
   # List MCP servers
   oc get mcpserver

   # Get server URL and transport type
   oc describe mcpserver <server-name>

   # Check route configuration
   oc get route <mcp-server-route>
   ```

2. **Start MCP Inspector**:
   ```bash
   # For SSE transport (most common)
   mcp-inspector --transport sse --server-url http://<mcp-server-route>/sse

   # For HTTP transport
   mcp-inspector --transport http --server-url http://<mcp-server-route>
   ```

3. **Test Connection**:
   - Open the provided URL in your browser (e.g., `http://localhost:6274/?MCP_PROXY_AUTH_TOKEN=...`)
   - Use the web interface to:
     - Connect to the MCP server
     - View available tools and resources
     - Execute tool calls with test parameters
     - Monitor MCP protocol messages

#### Example: Testing Weather MCP Server

```bash
# Connect to weather MCP server
mcp-inspector --transport sse --server-url http://mcp-mcp-weather-proxy-<namespace>.apps.<cluster-domain>/sse

# In the web interface:
# 1. Connect to the server
# 2. Find the weather tool (e.g., "get_weather")
# 3. Test with coordinates:
#    - New York: lat=40.7128, lon=-74.0060
#    - Los Angeles: lat=34.0522, lon=-118.2437
```

#### Troubleshooting MCP Connections

**Common Issues:**

1. **503 Service Unavailable**
   - Check if using HTTP vs HTTPS correctly
   - Verify route has proper TLS configuration: `oc get route <name> -o yaml`

2. **404 Not Found**
   - Ensure correct endpoint path (usually `/sse` for SSE transport)
   - Test endpoint manually: `curl http://<server-url>/sse -H "Accept: text/event-stream"`

3. **Connection Timeout**
   - Check if MCP server pods are running: `oc get pods -l app=<server-name>`
   - Review server logs: `oc logs <pod-name>`

4. **Transport Type Mismatch**
   - Match transport type with server configuration
   - SSE transport requires `/sse` endpoint
   - HTTP transport uses root path `/`

**Debugging Commands:**
```bash
# Check server status
oc get mcpserver <name> -o yaml

# View server logs
oc logs -l toolhive-name=<server-name>

# Test endpoint manually
curl -v http://<server-route>/sse -H "Accept: text/event-stream" --max-time 5
```

## Versioning and Releases

This repository uses automated per-component semantic versioning with git tagging. Every merge to `main` creates traceable releases with git tags and versioned container images.

### Version Format

Each component follows semantic versioning:
```
component-name-X.Y.Z
```

Where:
- `X` - Major version (breaking changes)
- `Y` - Minor version (new features)
- `Z` - Patch version (bug fixes)

Examples:
- `ingestion-pipeline-0.2.18`
- `llama-stack-0.3.0`
- `mcp-servers-0.1.0`

### Container Image Tags

Each build creates three image tags:
```bash
quay.io/rh-ai-quickstart/ingestion-pipeline:0.2.19   # Version (matches chart)
quay.io/rh-ai-quickstart/ingestion-pipeline:a1b2c3d  # Git SHA
quay.io/rh-ai-quickstart/ingestion-pipeline:latest   # Latest build
```

### For Contributors

When making changes to a component:

1. **(Optional) Bump the chart version** in `component/helm/Chart.yaml`:
   ```yaml
   version: 0.3.0  # Manually bump for major/minor changes
   ```
   Or leave unchanged to let the workflow auto-increment the patch version

2. **Commit and create PR** with a descriptive commit message - on merge, the workflow automatically:
   - Auto-increments patch version if tag exists, or uses your manual version
   - Updates both `version` and `appVersion` to match
   - Builds and tags container images
   - Creates git tag (e.g., `ingestion-pipeline-0.2.19`)
   - Publishes Helm chart

For detailed versioning guidelines, see [VERSIONING.md](./VERSIONING.md).

## Contributing

When contributing to this repository:
1. Follow OpenShift best practices
2. **Bump version** for component changes (see [Versioning](#versioning-and-releases))
3. **Use conventional commits** for clear git history (`feat:`, `fix:`, `docs:`, etc.)
4. Update component READMEs for any changes
5. Test integrations between components
6. Ensure security and operational standards

