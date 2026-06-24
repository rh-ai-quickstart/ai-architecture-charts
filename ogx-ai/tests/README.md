# OGX AI integration test chart

Umbrella chart that deploys **ogx-ai**, **llm-service**, and an optional **ingestion pipeline** smoke test (similar to the RAG blueprint, but trimmed down).

Use this chart to validate that the OGX stack works end-to-end on a live OpenShift AI cluster before promoting chart or values changes.

## What is tested

This is a **manual integration smoke test**, not an automated CI suite. A successful install and verify run confirms the following:

### Chart and platform integration

| Area | What is validated |
|------|-------------------|
| Umbrella chart wiring | Subcharts (`ogx-ai`, `llm-service`, `pgvector`, `configure-pipeline`, `ingestion-pipeline`) resolve, install, and start together from a single release |
| OpenShift AI / DSP | Data Science Pipelines Application (`ds-pipeline-dspa`) becomes healthy and is reachable from the ingestion-pipeline init container |
| `clientDependency: ogx-ai` | Ingestion-pipeline waits for and talks to the `ogx-ai` service (not legacy `llamastack`) |

### Inference and API

| Area | What is validated |
|------|-------------------|
| `llm-service` | Deploys `meta-llama/Llama-3.2-1B-Instruct` via vLLM (CPU by default; GPU via `DEVICE=gpu`) |
| Model routing | `ogx-ai` discovers the in-namespace llm-service predictor and exposes the model on `/v1/models` |
| OpenAI-compatible API | OGX `/v1/health`, `/v1/models`, and `/v1/chat/completions` respond successfully |
| Embeddings | Default OGX embedding model (`nomic-embed-text-v1.5`) is listed and available for RAG tasks |

### RAG stack (default install)

| Area | What is validated |
|------|-------------------|
| `pgvector` | Vector store deploys and is configured as OGX `vector_io` backend |
| `configure-pipeline` | DSP workspace, pipeline storage, and embedded MinIO for KFP artifacts come up (notebook is disabled) |
| `ingestion-pipeline` API | Service `/ping` responds after init containers pass |
| Bootstrap job | `add-smoke-github-pipeline` Job registers the `smoke-github` pipeline via the ingestion API |
| GitHub ingestion | Kubeflow `PipelineRun` is created for pipeline `smoke-github`, ingesting public `docs/` from [rh-ai-quickstart/RAG](https://github.com/rh-ai-quickstart/RAG) into vector store `ogx-test-kb-v1-0` using `all-MiniLM-L6-v2` embeddings |

### Explicitly out of scope

The test values intentionally disable features that add cost, secrets, or external dependencies:

- External web search (Brave, Tavily)
- MCP tool runtime
- DSP notebook server
- MinIO document bucket (GitHub source only — no S3 document upload path)
- Operator-based OGX deployment (`managedByOperator`)
- Automated test assertions or teardown hooks

To test only OGX + inference without RAG, disable the ingestion-related subcharts (see [OGX + llm-service only](#ogx--llm-service-only-no-ingestion) below).

## What it deploys

| Component | Purpose |
|-----------|---------|
| `llm-service` | Serves `meta-llama/Llama-3.2-1B-Instruct` via vLLM |
| `ogx-ai` | OpenAI-compatible API (`ogx-ai` service; `ingestion-pipeline.clientDependency: ogx-ai`) |
| `pgvector` | Vector store backend for OGX `vector_io` |
| `configure-pipeline` | OpenShift Data Science Pipelines + MinIO for KFP artifacts |
| `ingestion-pipeline` | Registers and runs one GitHub-sourced smoke pipeline |

External search tools are disabled to keep the footprint small.

Model enablement is configured separately under `llm-service.models` and `ogx-ai.models` (not `global.models`), because ogx-ai injects predictor URLs into the shared global model map and would prevent llm-service from creating InferenceServices.

## Prerequisites

- OpenShift cluster with **OpenShift AI** and **Data Science Pipelines** (DSP)
- Helm 3.x
- HuggingFace token with access to [Llama 3.2 1B Instruct](https://huggingface.co/meta-llama/Llama-3.2-1B-Instruct)
- CPU nodes (default) or GPU nodes when overriding `llm-service.device`

## Install

From the `ogx-ai/tests` directory:

```bash
export HF_TOKEN=...
make install
```

Or with Helm directly:

```bash
helm dependency update ./tests

helm install ogx-ai-test ./tests \
  --set llm-service.secret.hf_token="$HF_TOKEN"
```

Optional Makefile variables: `NAMESPACE`, `DEVICE` (`cpu` or `gpu`), `RELEASE_NAME`, `HELM_EXTRA_ARGS`.

### GPU install

```bash
DEVICE=gpu HF_TOKEN=... make install
```

### OGX + llm-service only (no ingestion)

```bash
HF_TOKEN=... make install HELM_EXTRA_ARGS='\
  --set ingestion-pipeline.enabled=false \
  --set configure-pipeline.enabled=false \
  --set pgvector.enabled=false \
  --set ogx-ai.pgvector.enabled=false'
```

## Verify

Wait for pods and the llm-service InferenceService to become ready:

```bash
oc get inferenceservices
oc get pods
oc get datasciencepipelinesapplications
```

Check OGX health:

```bash
oc port-forward svc/ogx-ai 8321:8321

curl -s http://localhost:8321/v1/health
curl -s http://localhost:8321/v1/models
```

Check the ingestion pipeline API (service name includes the release prefix):

```bash
oc port-forward svc/ogx-ai-test-ingestion-pipeline 8080:80

curl -s http://localhost:8080/ping
```

After the bootstrap Jobs finish, confirm a Kubeflow pipeline run was created (OpenShift AI dashboard → Pipelines, or):

```bash
oc get jobs -l app.kubernetes.io/name=ingestion-pipeline
oc get pipelineruns
```

Send a chat completion:

```bash
curl -s http://localhost:8321/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Llama-3.2-1B-Instruct",
    "messages": [{"role": "user", "content": "Say hello in one sentence."}],
    "max_tokens": 64
  }'
```

## Uninstall

```bash
make uninstall
```

Or:

```bash
helm uninstall ogx-ai-test
oc delete pvc ogx-ai-data pgvector-pg-data --ignore-not-found
```
