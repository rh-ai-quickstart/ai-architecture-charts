# OGX AI integration test chart

Umbrella chart that deploys **ogx-ai**, **llm-service**, and an optional **ingestion pipeline** smoke test (similar to the RAG blueprint, but trimmed down).

## What it deploys

| Component | Purpose |
|-----------|---------|
| `llm-service` | Serves `meta-llama/Llama-3.2-1B-Instruct` via vLLM |
| `ogx-ai` | OpenAI-compatible API (service name `llamastack` for pipeline compatibility) |
| `pgvector` | Vector store backend for OGX `vector_io` |
| `configure-pipeline` | OpenShift Data Science Pipelines + MinIO for KFP artifacts |
| `ingestion-pipeline` | One GitHub-sourced pipeline that ingests `docs/` from the RAG repo |

External search tools are disabled to keep the footprint small.

Model enablement is configured separately under `llm-service.models` and `ogx-ai.models` (not `global.models`), because ogx-ai injects predictor URLs into the shared global model map and would prevent llm-service from creating InferenceServices.

## Prerequisites

- OpenShift cluster with **OpenShift AI** and **Data Science Pipelines** (DSP)
- Helm 3.x
- HuggingFace token with access to [Llama 3.2 1B Instruct](https://huggingface.co/meta-llama/Llama-3.2-1B-Instruct)
- CPU nodes (default) or GPU nodes when overriding `llm-service.device`

## Install

From the `ogx-ai` chart directory:

```bash
helm dependency update ./tests

helm install ogx-ai-test ./tests \
  --set llm-service.secret.hf_token="$HF_TOKEN"
```

### GPU install

```bash
helm install ogx-ai-test ./tests \
  --set llm-service.device=gpu \
  --set llm-service.secret.hf_token="$HF_TOKEN"
```

### OGX + llm-service only (no ingestion)

```bash
helm install ogx-ai-test ./tests \
  --set ingestion-pipeline.enabled=false \
  --set configure-pipeline.enabled=false \
  --set pgvector.enabled=false \
  --set ogx-ai.pgvector.enabled=false \
  --set llm-service.secret.hf_token="$HF_TOKEN"
```

## Verify

Wait for pods and the llm-service InferenceService to become ready:

```bash
kubectl get inferenceservices
kubectl get pods
kubectl get datasciencepipelinesapplications
```

Check OGX health (service is named `llamastack`):

```bash
kubectl port-forward svc/llamastack 8321:8321

curl -s http://localhost:8321/v1/health
curl -s http://localhost:8321/v1/models
```

Check the ingestion pipeline API:

```bash
kubectl port-forward svc/ingestion-pipeline 8080:80

curl -s http://localhost:8080/ping
```

After the bootstrap Jobs finish, confirm a Kubeflow pipeline run was created (OpenShift AI dashboard → Pipelines, or):

```bash
kubectl get pipelineruns
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
helm uninstall ogx-ai-test
kubectl delete pvc ogx-ai-data pgvector-pg-data --ignore-not-found
```
