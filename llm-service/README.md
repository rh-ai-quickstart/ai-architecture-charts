# LLM Service Helm Chart

This Helm chart deploys a comprehensive LLM (Large Language Model) serving infrastructure using vLLM runtime with support for any models compatible with vLLM, GPU/HPU/CPU deployment modes, and OpenShift AI integration.

## Overview

The llm-service chart creates:
- vLLM serving runtime for model inference
- InferenceService resources for model deployment
- ConfigMap for chat templates
- Secret management for HuggingFace tokens
- Support for multiple model configurations
- GPU, HPU (Intel Gaudi), and CPU deployment modes

## Prerequisites

- OpenShift cluster with OpenShift AI/KServe installed
- Helm 3.x
- GPU or HPU (Intel Gaudi) nodes (recommended for optimal performance)
- HuggingFace account and token for model access
- Sufficient storage for model downloads

## Installation

### Basic Installation

```bash
helm install llm-service ./helm
```

Note: The global `device` in `values.yaml` sets the default for models that don't specify their own device. Individual models can override this with their own `device` field.

### Installation with GPU Support

```bash
helm install llm-service ./helm \
  --set device=gpu \
  --set models.llama-3-2-3b-instruct.enabled=true
```

### Installation with CPU Mode

```bash
helm install llm-service ./helm \
  --set device=cpu \
  --set models.llama-guard-3-1b.enabled=true
```

### Installation with HPU (Intel Gaudi) Support

```bash
helm install llm-service ./helm \
  --set device=hpu \
  --set models.llama-3-2-3b-instruct.enabled=true
```

### Installation with Custom Models

```bash
helm install llm-service ./helm \
  --set models.llama-3-1-8b-instruct.enabled=true \
  --set models.llama-guard-3-8b.enabled=true \
  --set secret.hf_token="your_huggingface_token"
```

## Configuration

### Key Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `device` | Default device for models that don't specify one (gpu/hpu/cpu) | `gpu` |
| `rawDeploymentMode` | Use raw deployment instead of KServe | `true` |
| `deviceConfigs.gpu.image` | GPU container image | `quay.io/ecosystem-appeng/vllm:openai-v0.9.2` |
| `deviceConfigs.cpu.image` | CPU container image | `quay.io/ecosystem-appeng/vllm:cpu-v0.9.2` |
| `deviceConfigs.hpu.image` | HPU (Intel Gaudi) container image | `quay.io/modh/vllm:vllm-gaudi-v2-22-on-push-jgj5q-build-container` |
| `servingRuntime.name` | Name of the serving runtime | `vllm-serving-runtime` |
| `servingRuntime.knativeTimeout` | Knative timeout for inference | `60m` |
| `secret.enabled` | Enable HuggingFace secret creation | `true` |
| `secret.hf_token` | HuggingFace access token | `""` |

### Model Configuration

The chart supports multiple models compatible with vLLM with **per-model device configuration**. Each model can specify its own `device` field to run on different hardware:

#### Per-Model Device Configuration

Each model can specify which device type to use:

```yaml
models:
  # Example: Small model on CPU for cost efficiency
  llama-guard-3-1b:
    id: meta-llama/Llama-Guard-3-1B
    enabled: true
    device: cpu  # Explicitly run on CPU

  # Example: Medium model on GPU
  llama-3-2-3b-instruct-gpu:
    id: meta-llama/Llama-3.2-3B-Instruct
    enabled: true
    device: gpu  # Run on GPU
    accelerators: "1"

  # Example: Same model on HPU with different config
  llama-3-2-3b-instruct-hpu:
    id: meta-llama/Llama-3.2-3B-Instruct
    enabled: true
    device: hpu  # Run on Intel Gaudi HPU
    accelerators: "2"  # Different accelerator count
```

#### Example: Llama 3.2 1B Instruct
```yaml
models:
  llama-3-2-1b-instruct:
    id: meta-llama/Llama-3.2-1B-Instruct
    enabled: true
    device: hpu  # Can be gpu, hpu, or cpu - defaults to global device if not specified
    args:
      - --enable-auto-tool-choice
      - --chat-template
      - /chat-templates/tool_chat_template_llama3.2_json.jinja
      - --tool-call-parser
      - llama3_json
      - --max-model-len
      - "30544"
```

#### Example: Llama 3.1 8B Instruct
```yaml
models:
  llama-3-1-8b-instruct:
    id: meta-llama/Llama-3.1-8B-Instruct
    enabled: true
    device: gpu
    # Optional: explicitly set accelerator count (default is 1)
    accelerators: "1"
    args:
      - --max-model-len
      - "14336"
      - --enable-auto-tool-choice
```

#### Example: Llama 3.3 70B Instruct with Multi-Accelerator Setup
```yaml
models:
  llama-3-3-70b-instruct:
    id: meta-llama/Llama-3.3-70B-Instruct
    enabled: true
    device: gpu
    storageSize: 150Gi
    accelerators: "4"
    args:
      - --tensor-parallel-size
      - "4"
      - --gpu-memory-utilization
      - "0.95"
```

#### Example: Llama 3.3 70B Instruct with FP8 Quantization (GPU Only)
```yaml
models:
  llama-3-3-70b-instruct-quantization-fp8:
    id: meta-llama/Llama-3.3-70B-Instruct
    enabled: true
    device: gpu
    storageSize: 150Gi
    accelerators: "4"
    args:
      - --tensor-parallel-size
      - "4"
      - --gpu-memory-utilization
      - "0.95"
      - --quantization
      - fp8
```

### Serving Runtime Configuration

```yaml
# Device-specific configurations  
deviceConfigs:
  gpu:
    image: quay.io/ecosystem-appeng/vllm:openai-v0.9.2
    tolerations:
      - key: nvidia.com/gpu
        effect: NoSchedule
        operator: Exists
    recommendedAccelerators:
      - nvidia.com/gpu
    acceleratorType: nvidia.com/gpu
  hpu:
    image: quay.io/modh/vllm:vllm-gaudi-v2-22-on-push-jgj5q-build-container
    tolerations:
      - key: habana.ai/gaudi
        effect: NoSchedule
        operator: Exists
    recommendedAccelerators:
      - habana.ai/gaudi
    acceleratorType: habana.ai/gaudi
  cpu:
    image: quay.io/ecosystem-appeng/vllm:cpu-v0.9.2
    tolerations: []
    recommendedAccelerators: []
    acceleratorType: null

servingRuntime:
  name: vllm-serving-runtime
  knativeTimeout: 60m
  env:
    - name: HOME
      value: /vllm
    - name: HF_TOKEN
      valueFrom:
        secretKeyRef:
          key: HF_TOKEN
          name: huggingface-secret
```

### Complete Example values.yaml

```yaml
device: gpu
rawDeploymentMode: true

# Device-specific configurations
deviceConfigs:
  gpu:
    image: quay.io/ecosystem-appeng/vllm:openai-v0.9.2
    tolerations:
      - key: nvidia.com/gpu
        effect: NoSchedule
        operator: Exists
    recommendedAccelerators:
      - nvidia.com/gpu
    acceleratorType: nvidia.com/gpu
  hpu:
    image: quay.io/modh/vllm:vllm-gaudi-v2-22-on-push-jgj5q-build-container
    tolerations:
      - key: habana.ai/gaudi
        effect: NoSchedule
        operator: Exists
    recommendedAccelerators:
      - habana.ai/gaudi
    acceleratorType: habana.ai/gaudi
  cpu:
    image: quay.io/ecosystem-appeng/vllm:cpu-v0.9.2
    tolerations: []
    recommendedAccelerators: []
    acceleratorType: null

servingRuntime:
  name: vllm-serving-runtime
  knativeTimeout: 90m

secret:
  enabled: true
  hf_token: "hf_your_token_here"

models:
  llama-3-2-3b-instruct:
    id: meta-llama/Llama-3.2-3B-Instruct
    enabled: true
    args:
      - --enable-auto-tool-choice
      - --chat-template
      - /chat-templates/tool_chat_template_llama3.2_json.jinja
      - --tool-call-parser
      - llama3_json
      - --max-model-len
      - "14336"
  
  llama-guard-3-8b:
    id: meta-llama/Llama-Guard-3-8B
    enabled: true
    args:
      - --max-model-len
      - "14336"
  
  qwen-2-5-vl-3b-instruct:
    id: Qwen/Qwen2.5-VL-3B-Instruct
    incompatibleDevices: ["hpu"]
    enabled: true
    args:
      - --max-model-len
      - "30544"
      - --enable-auto-tool-choice
      - --chat-template
      - /chat-templates/tool_chat_template_qwen.jinja
      - --tool-call-parser
      - llama3_json
```

## Usage

### Accessing Model Endpoints

After deployment, models are available through OpenShift AI inference endpoints:

```bash
# List inference services
oc get inferenceservices

# Get model endpoint URL
oc get inferenceservice llama-3-2-3b-instruct -o jsonpath='{.status.url}'

# Port forward for local access
oc port-forward svc/llama-3-2-3b-instruct-predictor 8080:80
```

### OpenAI-Compatible API

The vLLM runtime provides OpenAI-compatible endpoints:

```bash
# List available models
curl http://localhost:8080/v1/models

# Generate completions
curl -X POST http://localhost:8080/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Llama-3.2-3B-Instruct",
    "prompt": "What is artificial intelligence?",
    "max_tokens": 100,
    "temperature": 0.7
  }'

# Chat completions
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Llama-3.2-3B-Instruct",
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ],
    "max_tokens": 100
  }'
```

### Tool Calling Support

Models with tool calling enabled support function calls:

```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Llama-3.2-3B-Instruct",
    "messages": [
      {"role": "user", "content": "What is the weather like in New York?"}
    ],
    "tools": [
      {
        "type": "function",
        "function": {
          "name": "get_weather",
          "description": "Get weather information",
          "parameters": {
            "type": "object",
            "properties": {
              "location": {"type": "string"}
            }
          }
        }
      }
    ]
  }'
```

## Monitoring and Troubleshooting

### Checking Service Health

```bash
# Check inference services
oc get inferenceservices

# Check serving runtime
oc get servingruntimes vllm-serving-runtime

# Check model pods
oc get pods -l serving.kserve.io/inferenceservice=llama-3-2-3b-instruct
```

### Viewing Logs

```bash
# Model serving logs
oc logs -l serving.kserve.io/inferenceservice=llama-3-2-3b-instruct -f

# Serving runtime logs
oc logs -l app=vllm-serving-runtime -f

# Check model loading progress
oc describe inferenceservice llama-3-2-3b-instruct
```

### Common Issues

1. **Model Download Failures**:
   - Check HuggingFace token validity
   - Verify model access permissions
   - Ensure sufficient storage space
   - Check internet connectivity

2. **GPU Resource Issues**:
   - Verify GPU nodes are available
   - Check GPU resource limits
   - Ensure NVIDIA device plugin is running
   - Validate GPU toleration settings

3. **Memory/Storage Issues**:
   - Large models require significant memory
   - Check node memory availability
   - Verify storage class supports large volumes
   - Monitor resource usage

4. **Serving Runtime Issues**:
   - Check container image accessibility
   - Verify serving runtime configuration
   - Validate chat template configurations
   - Check environment variable settings

### Resource Requirements by Model Size

#### Small Models (1B-3B parameters)
```yaml
resources:
  requests:
    memory: "8Gi"
    cpu: "2000m"
  limits:
    memory: "16Gi"
    cpu: "4000m"
```

Also set the accelerator count on the model when using GPU/HPU devices:

```yaml
accelerators: "1"
```

#### Medium Models (8B parameters)
```yaml
resources:
  requests:
    memory: "16Gi"
    cpu: "4000m"
  limits:
    memory: "32Gi"
    cpu: "8000m"
```

And specify accelerators count if needed (defaults to "1"):

```yaml
accelerators: "1"
```

#### Large Models (70B parameters)
```yaml
resources:
  requests:
    memory: "64Gi"
    cpu: "8000m"
  limits:
    memory: "128Gi"
    cpu: "16000m"
```

Set the accelerator count accordingly for multi-device parallelism:

```yaml
accelerators: "4"
```

### Device Configuration (Tolerations)

Default tolerations are applied based on the selected device via `deviceConfigs`. You can override per model if needed.

```yaml
deviceConfigs:
  gpu:
    tolerations:
      - key: nvidia.com/gpu
        effect: NoSchedule
        operator: Exists
  hpu:
    tolerations:
      - key: habana.ai/gaudi
        effect: NoSchedule
        operator: Exists
```

Note: Node selectors are not explicitly configurable in this chart; scheduling to GPU/HPU nodes is driven by resource requests and tolerations.

### Multiple ServingRuntimes

The chart automatically creates device-specific `ServingRuntime` resources based on enabled models:

- `vllm-serving-runtime-gpu` - for GPU models (using `deviceConfigs.gpu.image`)
- `vllm-serving-runtime-hpu` - for HPU models (using `deviceConfigs.hpu.image`)
- `vllm-serving-runtime-cpu` - for CPU models (using `deviceConfigs.cpu.image`)

Only the runtimes needed for your enabled models are created.

### Mixed Device Deployments

You can run the same model on different devices with optimized configurations:

```yaml
models:
  # Cost-optimized CPU deployment
  llama-3-2-3b-instruct-cpu:
    id: meta-llama/Llama-3.2-3B-Instruct
    device: cpu
    enabled: true

  # Performance-optimized GPU deployment
  llama-3-2-3b-instruct-gpu:
    id: meta-llama/Llama-3.2-3B-Instruct
    device: gpu
    enabled: true
    accelerators: "1"
    args:
      - --quantization
      - fp8  # GPU-specific optimization

  # HPU deployment with different parallelism
  llama-3-2-3b-instruct-hpu:
    id: meta-llama/Llama-3.2-3B-Instruct
    device: hpu
    enabled: true
```

## Security Considerations

### HuggingFace Token Management

```bash
# Create secret manually (recommended for production)
oc create secret generic huggingface-secret \
  --from-literal=HF_TOKEN=your_token_here

# Use existing secret
helm install llm-service ./helm \
  --set secret.enabled=false
```

### Network Security

- Models serve on internal cluster networks by default
- Use NetworkPolicies to restrict access
- Enable TLS for external access
- Consider authentication for production deployments

## Scaling and Management

### Model Scaling

```yaml
models:
  llama-3-2-3b-instruct:
    enabled: true
    minReplicas: 1
    maxReplicas: 3
    resources:
      # CPU/Memory shown here; accelerator resources are injected automatically based on device
      limits:
        memory: "16Gi"
        cpu: "4000m"
    accelerators: "1"
```

### A/B Testing

Deploy multiple model versions:

```yaml
models:
  llama-3-2-3b-instruct-v1:
    id: meta-llama/Llama-3.2-3B-Instruct
    enabled: true
  llama-3-2-3b-instruct-v2:
    id: meta-llama/Llama-3.2-3B-Instruct
    enabled: true
    args:
      - --temperature
      - "0.5"
```

## Upgrading

```bash
# Upgrade with new model configurations
helm upgrade llm-service ./helm \
  --set models.llama-3-1-8b-instruct.enabled=true

# Check rollout status
oc get inferenceservices
```

## Uninstalling

```bash
# Remove chart and all resources
helm uninstall llm-service

# Clean up inference services (if needed)
oc delete inferenceservices -l app.kubernetes.io/name=llm-service

# Remove serving runtime
oc delete servingruntimes vllm-serving-runtime

# Remove secrets (if needed)
oc delete secret huggingface-secret
```

## Integration with Other Components

This chart integrates with:

- **OpenShift AI/KServe**: Model serving infrastructure
- **LlamaStack**: Unified AI stack integration
- **Ingestion Pipeline**: Document processing workflows
- **MCP Servers**: External tool integration
- **PGVector**: Vector storage for embeddings

## Advanced Configuration

### Custom Model Registry

```yaml
models:
  custom-model:
    id: your-org/custom-llama-model
    enabled: true
    registry: "your-registry.com"
    args:
      - --custom-arg
      - value
```

### Multi-Tenancy

Deploy models in different namespaces:

```bash
# Deploy for team A
helm install llm-service-team-a ./helm \
  --namespace team-a \
  --set models.llama-3-2-3b-instruct.enabled=true

# Deploy for team B  
helm install llm-service-team-b ./helm \
  --namespace team-b \
  --set models.llama-3-1-8b-instruct.enabled=true
```

### Observability

Monitor model performance:

```yaml
servingRuntime:
  env:
    - name: PROMETHEUS_MULTIPROC_DIR
      value: /tmp/prometheus
    - name: OTEL_EXPORTER_OTLP_ENDPOINT
      value: http://jaeger-collector:4317
```