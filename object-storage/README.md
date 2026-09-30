# Object Storage Helm Chart

Generic S3-compatible object storage for AI/ML pipelines on OpenShift or Kubernetes. Currently backed by [S4 (Super Simple Storage Service)](https://github.com/rh-aiservices-bu/s4). Use it as an alternative to the MinIO chart; MinIO remains available unchanged.

Layout matches other ai-architecture-charts components (`object-storage/helm/`).

## Overview

The chart creates:

- Deployment with persistent RGW/SQLite storage (single replica)
- Service exposing **S3 API** (`7480`) and **Web UI** (`5000`)
- Secret `{fullname}-credentials` with `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`
- ConfigMap for non-secret runtime settings
- Optional OpenShift Routes and/or Kubernetes Ingress (UI and/or S3 API)
- Restricted-friendly security contexts (no SCC objects)

## Prerequisites

- OpenShift or Kubernetes 1.19+
- Helm 3.x
- PersistentVolume provisioner support

## Installation

### Standalone

```bash
helm install object-storage ./object-storage/helm --namespace object-storage --create-namespace \
  --set auth.username=admin \
  --set auth.password=your-secure-password
```

### Custom values

```bash
helm install object-storage ./object-storage/helm --namespace object-storage --create-namespace -f my-values.yaml
```

### Without UI authentication

```bash
helm install object-storage ./object-storage/helm --namespace object-storage --create-namespace \
  --set auth.enabled=false
```

## Using as a subchart dependency

Parents can pull from the published chart repo or a local path. Gate install with a condition so projects can opt into this chart, keep MinIO, or use external S3.

### Chart.yaml

```yaml
dependencies:
  - name: object-storage
    version: 0.1.0
    repository: https://rh-ai-quickstart.github.io/ai-architecture-charts
    # or: repository: "file://../ai-architecture-charts/object-storage/helm"
    condition: object-storage.enabled
```

### values.yaml (stable short in-cluster DNS)

```yaml
object-storage:
  enabled: true
  fullnameOverride: object-storage   # or "s4" for a short DNS name
  image:
    repository: quay.io/rh-aiservices-bu/s4
    tag: "0.3.2"
    pullPolicy: IfNotPresent
  s3:
    accessKeyId: s4admin
    secretAccessKey: s4secret
  auth:
    enabled: true
    username: admin
    password: changeme
  route:
    enabled: true               # OpenShift UI Route (default)
    s3Api:
      enabled: false            # keep S3 cluster-internal
  storage:
    data:
      size: 10Gi
```

### Consumer contract

| Item | Value |
|------|--------|
| In-cluster S3 endpoint | `http://<fullname>:7480` |
| Web UI | port `5000` (`GET /api` for readiness) |
| Credentials secret | `<fullname>-credentials` |
| Secret keys | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` |
| Region | `s3.region` (default `us-east-1`) |

Example env wiring from a parent Deployment (with `fullnameOverride: object-storage`):

```yaml
env:
  - name: AWS_ACCESS_KEY_ID
    valueFrom:
      secretKeyRef:
        name: object-storage-credentials
        key: AWS_ACCESS_KEY_ID
  - name: AWS_SECRET_ACCESS_KEY
    valueFrom:
      secretKeyRef:
        name: object-storage-credentials
        key: AWS_SECRET_ACCESS_KEY
  - name: AWS_S3_ENDPOINT
    value: http://object-storage:7480
```

For DSPA / operators that probe from outside the release namespace, use an FQDN host such as `object-storage.<namespace>.svc.cluster.local` and port `7480`.

Bucket bootstrap, lakeFS blockstore wiring, and OpenShift AI data-connection Secrets belong in the **parent** chart (not this subchart).

## Configuration

### Image

| Parameter | Description | Default |
|-----------|-------------|---------|
| `image.repository` | Container image repository | `quay.io/rh-aiservices-bu/s4` |
| `image.tag` | Container image tag | `0.3.2` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `imagePullSecrets` | Image pull secrets | `[]` |

### S3

| Parameter | Description | Default |
|-----------|-------------|---------|
| `s3.endpoint` | S3 endpoint URL (internal RGW) | `http://localhost:7480` |
| `s3.region` | S3 region | `us-east-1` |
| `s3.accessKeyId` | Access key (ignored if `existingSecret` set) | `s4admin` |
| `s3.secretAccessKey` | Secret key (ignored if `existingSecret` set) | `s4secret` |
| `s3.existingSecret` | Existing secret with `AWS_*` keys | `""` |

### Authentication (Web UI)

| Parameter | Description | Default |
|-----------|-------------|---------|
| `auth.enabled` | Enable UI authentication | `true` |
| `auth.username` | UI username (required when auth enabled) | `""` |
| `auth.password` | UI password (required when auth enabled) | `""` |
| `auth.jwtSecret` | JWT secret (auto-generated if empty) | `""` |
| `auth.jwtExpirationHours` | JWT expiration hours | `8` |
| `auth.cookieRequireHttps` | Require HTTPS cookies | `true` |

### Storage

| Parameter | Description | Default |
|-----------|-------------|---------|
| `storage.data.size` | RGW data PVC size | `10Gi` |
| `storage.data.storageClass` | Storage class | `""` |
| `storage.data.existingClaim` | Use existing PVC | `""` |
| `storage.localStorage.enabled` | Local file browser volume | `false` |
| `storage.localStorage.size` | Local storage size | `50Gi` |
| `storage.maxFileSizeGB` | Max upload size (GB) | `20` |

### Service

| Parameter | Description | Default |
|-----------|-------------|---------|
| `service.type` | Service type | `ClusterIP` |
| `service.port` | Web UI port | `5000` |
| `service.s3Port` | S3 API port | `7480` |
| `service.nodePort.enabled` | Extra NodePort Service | `false` |

### OpenShift Routes

| Parameter | Description | Default |
|-----------|-------------|---------|
| `route.enabled` | UI Route | `true` |
| `route.host` | UI hostname (auto if empty) | `""` |
| `route.tls.termination` | TLS termination | `edge` |
| `route.s3Api.enabled` | Expose S3 API via Route | `false` |

### Kubernetes Ingress

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ingress.enabled` | UI Ingress | `false` |
| `ingress.s3Api.enabled` | S3 API Ingress | `false` |

> **Warning:** Enabling `route.s3Api` or `ingress.s3Api` exposes the S3 API outside the cluster. Prefer cluster-internal access for credentials-bearing workloads.

### Flexibility knobs

- **Naming:** `nameOverride` / `fullnameOverride` for stable Service DNS across parents
- **Credentials:** chart-managed Secret or `s3.existingSecret`
- **Networking:** ClusterIP / NodePort / LoadBalancer; Route and Ingress independently toggled for UI vs S3
- **Storage:** size, storageClass, or `existingClaim`; optional local browser volume
- **Scheduling:** `nodeSelector`, `tolerations`, `affinity`
- **Extensibility:** `extraEnv`, `extraVolumes`, `extraVolumeMounts`, `commonLabels`, `commonAnnotations`

## Examples

### OpenShift Route hostname

```bash
helm install object-storage ./object-storage/helm --namespace object-storage --create-namespace \
  --set auth.username=admin \
  --set auth.password=your-secure-password \
  --set route.host=object-storage.apps.example.com
```

### Kubernetes Ingress instead of Route

```bash
helm install object-storage ./object-storage/helm --namespace object-storage --create-namespace \
  --set auth.username=admin \
  --set auth.password=your-secure-password \
  --set route.enabled=false \
  --set ingress.enabled=true \
  --set "ingress.hosts[0].host=object-storage.example.com" \
  --set "ingress.hosts[0].paths[0].path=/" \
  --set "ingress.hosts[0].paths[0].pathType=Prefix"
```

### Expose S3 API externally (OpenShift)

```bash
helm install object-storage ./object-storage/helm --namespace object-storage --create-namespace \
  --set auth.username=admin \
  --set auth.password=your-secure-password \
  --set route.s3Api.enabled=true \
  --set route.s3Api.host=s3.object-storage.apps.example.com
```

### Custom storage

```bash
helm install object-storage ./object-storage/helm --namespace object-storage --create-namespace \
  --set auth.username=admin \
  --set auth.password=your-secure-password \
  --set storage.data.size=100Gi \
  --set storage.data.storageClass=fast-storage
```

### Existing Secret

```bash
oc create secret generic my-object-storage-credentials \
  --from-literal=AWS_ACCESS_KEY_ID=mykey \
  --from-literal=AWS_SECRET_ACCESS_KEY=mysecret \
  -n object-storage

helm install object-storage ./object-storage/helm --namespace object-storage \
  --set auth.username=admin \
  --set auth.password=your-secure-password \
  --set s3.existingSecret=my-object-storage-credentials
```

### Short DNS name (Fraud Detection–style)

Parents that already expect `http://s4:7480` can keep that hostname:

```yaml
object-storage:
  enabled: true
  fullnameOverride: s4
```

## Accessing object storage

| Endpoint | Port | Purpose |
|----------|------|---------|
| Web UI | 5000 | Browser management UI |
| S3 API | 7480 | S3-compatible API (`aws`, `mc`, boto3, lakeFS, DSPA) |

### Port-forward

```bash
oc port-forward svc/object-storage 5000:5000 7480:7480 -n object-storage
```

- Web UI: http://localhost:5000
- S3 API: http://localhost:7480

### S3 client (in-cluster)

```python
import boto3

s3 = boto3.client(
    "s3",
    endpoint_url="http://object-storage:7480",
    aws_access_key_id="s4admin",
    aws_secret_access_key="s4secret",
    region_name="us-east-1",
)
s3.list_buckets()
```

## Uninstallation

```bash
helm uninstall object-storage --namespace object-storage
# PVCs are retained; delete when you intend to wipe data:
oc delete pvc -l app.kubernetes.io/instance=object-storage -n object-storage
```

## Troubleshooting

```bash
oc get pods -n object-storage -l app.kubernetes.io/name=object-storage
oc logs -n object-storage -l app.kubernetes.io/name=object-storage --tail=100
oc get configmap,secret,pvc,route -n object-storage -l app.kubernetes.io/name=object-storage
```

## Testing

Requires the [helm-unittest](https://github.com/helm-unittest/helm-unittest) plugin:

```bash
helm plugin install https://github.com/helm-unittest/helm-unittest
helm lint ./object-storage/helm
helm unittest ./object-storage/helm
```

Suites under `object-storage/helm/tests/` cover Deployment/Service/Secret/Route/Ingress/PVC behavior and a Fraud Detection–style consumer contract (`fullnameOverride: s4`, port `7480`).

## Upstream

Runtime image and templates are adapted from [rh-aiservices-bu/s4](https://github.com/rh-aiservices-bu/s4) (`charts/s4`). Image: `quay.io/rh-aiservices-bu/s4`.
