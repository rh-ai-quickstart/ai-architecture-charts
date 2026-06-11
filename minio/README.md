# MinIO Helm Chart

This Helm chart deploys MinIO, a high-performance, S3-compatible object storage server that provides scalable storage for documents, models, and data in AI/ML pipelines.

## Overview

The minio chart creates:
- MinIO deployment with persistent storage
- Service for S3-compatible API access
- Secret management for access credentials
- StatefulSet for data persistence
- Optional sample file upload functionality
- OpenShift route support for external access

## Prerequisites

- OpenShift cluster
- Helm 3.x
- Persistent storage (PVC support)
- Sufficient storage capacity for your data needs

## Installation

### Basic Installation

```bash
helm install minio ./helm
```

### Installation with Custom Credentials

```bash
helm install minio ./helm \
  --set secret.user=admin \
  --set secret.password=secure_password123
```

### Installation with Sample Files

```bash
helm install minio ./helm \
  --set sampleFileUpload.enabled=true \
  --set sampleFileUpload.bucket=documents
```

### Installation with Custom Namespace

```bash
helm install minio ./helm \
  --namespace object-storage \
  --create-namespace
```

## Configuration

### Key Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of replicas (always 1 for single-node) | `1` |
| `image.repository` | MinIO container image repository | `quay.io/minio/minio` |
| `image.tag` | MinIO container image tag | `latest` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `service.type` | Service type | `ClusterIP` |
| `service.port` | MinIO Console port | `9090` |
| `service.apiPort` | MinIO API port | `9000` |
| `secret.user` | MinIO root username | `minio_rag_user` |
| `secret.password` | MinIO root password | `minio_rag_password` |
| `secret.host` | MinIO service hostname | `minio` |
| `secret.port` | MinIO API port | `"9000"` |

### Storage Configuration

```yaml
volumeClaimTemplates:
  - metadata:
      name: minio-data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 50Gi

volumeMounts:
  - mountPath: /data
    name: minio-data
```

### Sample File Upload Configuration

```yaml
sampleFileUpload:
  enabled: true
  bucket: documents
  urls: 
    - https://raw.githubusercontent.com/rh-ai-quickstart/RAG/refs/heads/main/notebooks/Zippity_Zoo_Grand_Invention.pdf
    - https://raw.githubusercontent.com/rh-ai-quickstart/RAG/refs/heads/main/notebooks/Zippity_Zoo_and_the_Town_of_Tumble_Town.pdf
    - https://raw.githubusercontent.com/rh-ai-quickstart/RAG/refs/heads/main/notebooks/Zippity_Zoo_and_the_Town_of_Whispering_Willows.pdf
```

### Complete Example values.yaml

```yaml
replicaCount: 1

image:
  repository: quay.io/minio/minio
  pullPolicy: IfNotPresent
  tag: "RELEASE.2024-03-15T01-07-19Z"

nameOverride: "minio"
fullnameOverride: "minio"

service:
  type: ClusterIP
  port: 9090
  apiPort: 9000

# Custom startup command
command:
  - /bin/bash
  - -c
  - minio server /data --console-address :9090

# Environment variables
env:
  - name: MINIO_ROOT_USER
    valueFrom:
      secretKeyRef:
        key: user
        name: minio
  - name: MINIO_ROOT_PASSWORD
    valueFrom:
      secretKeyRef:
        key: password
        name: minio

# Resource limits
resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "1Gi"
    cpu: "500m"

# Storage configuration
volumeClaimTemplates:
  - metadata:
      name: minio-data
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: gp2  # or your preferred storage class
      resources:
        requests:
          storage: 100Gi

volumeMounts:
  - mountPath: /data
    name: minio-data

# Security credentials
secret:
  user: admin
  password: your_secure_password_here
  host: minio
  port: "9000"

# Sample files for testing
sampleFileUpload:
  enabled: true
  bucket: documents
  urls: 
    - https://example.com/sample1.pdf
    - https://example.com/sample2.pdf

# Node placement
nodeSelector:
  kubernetes.io/os: linux

affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      podAffinityTerm:
        labelSelector:
          matchExpressions:
          - key: app.kubernetes.io/name
            operator: In
            values:
            - minio
        topologyKey: kubernetes.io/hostname
```

## Usage

### Accessing MinIO Console

The MinIO console provides a web interface for managing buckets and objects:

```bash
# Port forward for local access
oc port-forward svc/minio 9090:9090

# Access console at http://localhost:9090
# Login with the configured username/password
```

### OpenShift Route

Create a route for external access:

```bash
# Expose MinIO console
oc expose service minio --port=9090 --name=minio-console
oc get routes minio-console

# Expose MinIO API (if needed)
oc expose service minio --port=9000 --name=minio-api
oc get routes minio-api
```

### S3-Compatible API Access

MinIO provides S3-compatible API endpoints:

```bash
# Port forward for API access
oc port-forward svc/minio 9000:9000

# API endpoint: http://localhost:9000
# or use service name internally: http://minio:9000
```

### Using MinIO Client (mc)

```bash
# Install MinIO client
curl https://dl.min.io/client/mc/release/linux-amd64/mc \
  --create-dirs -o $HOME/minio-binaries/mc
chmod +x $HOME/minio-binaries/mc

# Configure alias
mc alias set local http://localhost:9000 minio_rag_user minio_rag_password

# List buckets
mc ls local

# Create bucket
mc mb local/my-bucket

# Upload file
mc cp file.pdf local/my-bucket/

# Download file
mc cp local/my-bucket/file.pdf ./downloaded-file.pdf
```

### Python Integration

```python
from minio import Minio

# Initialize MinIO client
client = Minio(
    "minio:9000",  # or use route hostname for external access
    access_key="minio_rag_user",
    secret_key="minio_rag_password",
    secure=False  # Set to True for HTTPS
)

# List buckets
buckets = client.list_buckets()
for bucket in buckets:
    print(bucket.name)

# Upload file
client.fput_object("documents", "file.pdf", "/path/to/file.pdf")

# Download file
client.fget_object("documents", "file.pdf", "/path/to/download/file.pdf")

# List objects
objects = client.list_objects("documents", prefix="folder/", recursive=True)
for obj in objects:
    print(obj.object_name)
```

## Monitoring and Troubleshooting

### Checking Service Health

```bash
# Check pod status
oc get pods -l app.kubernetes.io/name=minio

# Check StatefulSet
oc get statefulset minio

# Check service
oc get svc minio

# Test API endpoint
oc exec -it minio-0 -- curl localhost:9000/minio/health/live
```

### Viewing Logs

```bash
# View MinIO logs
oc logs minio-0 -f

# Check StatefulSet events
oc describe statefulset minio

# Check PVC status
oc get pvc -l app.kubernetes.io/name=minio
```

### Common Issues

1. **Pod Won't Start**:
   - Check PVC binding status
   - Verify storage class availability
   - Check resource limits
   - Review node storage capacity

2. **Access Denied Errors**:
   - Verify credentials in secret
   - Check bucket policies
   - Validate user permissions
   - Review network connectivity

3. **Storage Issues**:
   - Check PVC status and capacity
   - Verify storage class configuration
   - Monitor disk usage
   - Check node storage availability

4. **Performance Issues**:
   - Monitor resource usage
   - Check storage I/O performance
   - Review network bandwidth
   - Consider storage class optimization

### Debugging Commands

```bash
# Check MinIO configuration
oc exec -it minio-0 -- mc admin info local

# View environment variables
oc exec -it minio-0 -- env | grep MINIO

# Check disk usage
oc exec -it minio-0 -- df -h /data

# Test connectivity
oc exec -it minio-0 -- mc ls local

# Check server status
oc exec -it minio-0 -- mc admin service status local
```

## Data Management

### Bucket Management

```bash
# Create bucket via console or CLI
oc exec -it minio-0 -- mc mb local/new-bucket

# Set bucket policy
oc exec -it minio-0 -- mc policy set public local/new-bucket

# Configure bucket versioning
oc exec -it minio-0 -- mc version enable local/new-bucket

# Set bucket lifecycle
oc exec -it minio-0 -- mc ilm add --expire-days 30 local/new-bucket
```

### Backup and Recovery

```bash
# Backup bucket
mc mirror local/source-bucket /backup/path/

# Restore bucket
mc mirror /backup/path/ local/restored-bucket

# Sync between MinIO instances
mc mirror local/bucket remote/bucket --watch
```

### Data Migration

```bash
# Migrate from AWS S3
mc mirror s3/source-bucket local/target-bucket

# Migrate to AWS S3
mc mirror local/source-bucket s3/target-bucket

# Copy between buckets
mc cp --recursive local/source-bucket/ local/target-bucket/
```

## Security Considerations

### Access Credentials

```bash
# Use strong passwords
secret:
  user: admin
  password: "$(openssl rand -base64 32)"

# Rotate credentials regularly
oc create secret generic minio-new \
  --from-literal=user=newuser \
  --from-literal=password=newpassword

# Update deployment to use new secret
helm upgrade minio ./helm --set secret.existingSecret=minio-new
```

### Network Security

```yaml
# Network policy example
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: minio-netpol
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: minio
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: ingestion-pipeline
    - podSelector:
        matchLabels:
          app: llama-stack
    - podSelector:
        matchLabels:
          app: ogx-ai
    ports:
    - protocol: TCP
      port: 9000
```

### TLS Configuration

```yaml
# Enable TLS
env:
  - name: MINIO_OPTS
    value: "--console-address :9090 --certs-dir /certs"

volumeMounts:
  - name: tls-certs
    mountPath: /certs
    readOnly: true

volumes:
  - name: tls-certs
    secret:
      secretName: minio-tls
```

## Upgrading

```bash
# Upgrade MinIO version
helm upgrade minio ./helm \
  --set image.tag=RELEASE.2024-04-01T15-51-17Z

# Check upgrade status
oc rollout status statefulset/minio

# Verify upgrade
oc exec -it minio-0 -- minio version
```

## Uninstalling

```bash
# Remove chart
helm uninstall minio

# Remove persistent data (WARNING: This deletes all data)
oc delete pvc -l app.kubernetes.io/name=minio

# Remove secrets (if needed)
oc delete secret minio
```

## Integration with AI Components

This chart integrates with:

- **Ingestion Pipeline**: Document storage and retrieval
- **LlamaStack / OGX**: Model storage and caching
- **Configure Pipeline**: Configuration and template storage
- **Jupyter Notebooks**: Data science workflows

### Example Integration Configuration

```yaml
# In other components, reference MinIO
env:
  - name: S3_ENDPOINT
    value: "http://minio:9000"
  - name: S3_ACCESS_KEY
    valueFrom:
      secretKeyRef:
        name: minio
        key: user
  - name: S3_SECRET_KEY
    valueFrom:
      secretKeyRef:
        name: minio
        key: password
  - name: S3_BUCKET
    value: "documents"
```

## Advanced Configuration

### Custom Storage Classes

```yaml
# Use specific storage class
volumeClaimTemplates:
  - metadata:
      name: minio-data
    spec:
      storageClassName: local-nvme
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 2Ti
```

### Multi-Environment Deployment

```bash
# Development environment
helm install minio-dev ./helm \
  --namespace development \
  --set volumeClaimTemplates[0].spec.resources.requests.storage=10Gi

# Production environment
helm install minio-prod ./helm \
  --namespace production \
  --set volumeClaimTemplates[0].spec.resources.requests.storage=1Ti \
  --set resources.limits.memory=8Gi
```