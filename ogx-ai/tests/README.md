# OGX AI integration test chart

Umbrella chart that deploys **ogx-ai** and **llm-service** together with a small model so the stack can be exercised end-to-end.

## What it deploys

| Component | Purpose |
|-----------|---------|
| `llm-service` | Serves `meta-llama/Llama-3.2-1B-Instruct` via vLLM |
| `ogx-ai` | OpenAI-compatible API that routes inference to the llm-service predictor |

PGVector and external search tools are disabled to keep the footprint minimal. Enable them in `values.yaml` if you need vector or web-search features.

Model enablement is configured separately under `llm-service.models` and `ogx-ai.models` (not `global.models`), because ogx-ai injects predictor URLs into the shared global model map and would prevent llm-service from creating InferenceServices.

## Prerequisites

- OpenShift cluster with OpenShift AI / KServe
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

## Verify

Wait for the llm-service InferenceService and ogx-ai deployment to become ready, then check health:

```bash
kubectl get inferenceservices
kubectl get pods -l app.kubernetes.io/name=ogx-ai

# Port-forward ogx-ai (or use the OpenShift Route)
kubectl port-forward svc/ogx-ai 8321:8321

curl -s http://localhost:8321/v1/health
curl -s http://localhost:8321/v1/models
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
kubectl delete pvc ogx-ai-data --ignore-not-found
```
