# MySQL Helm Chart

A Helm chart for deploying MySQL database on Kubernetes and OpenShift clusters.

## Overview

This chart deploys a MySQL 8.0 database instance, commonly used as a backend for Model Registry and other applications requiring persistent storage.

## Prerequisites

- Kubernetes 1.19+ or OpenShift 4.x
- Helm 3.x
- PV provisioner support (if persistence is enabled)

## Installation

### Basic Installation

```bash
helm install mysql ./mysql/helm
```

### With Custom Values

```bash
helm install mysql ./mysql/helm \
  --set user=myuser \
  --set password=mypassword \
  --set database=mydb
```

### OpenShift Installation

```bash
helm install mysql ./mysql/helm \
  --set openshift.enabled=true \
  --set openshift.imageStream.enabled=true
```

## Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `enabled` | Enable MySQL deployment | `true` |
| `name` | Name for MySQL resources | `mysql` |
| `namespace` | Namespace override | Release namespace |
| `image.repository` | MySQL image repository | `quay.io/sclorg/mysql-80-c9s` |
| `image.tag` | MySQL image tag | `latest` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `user` | MySQL user | `mysql_user` |
| `password` | MySQL password | `mysql_password` |
| `rootPassword` | MySQL root password | `mysql_root_password` |
| `database` | Database name | `model_registry` |
| `port` | MySQL port | `3306` |
| `persistence.enabled` | Enable persistence | `true` |
| `persistence.size` | PVC size | `1Gi` |
| `persistence.accessMode` | PVC access mode | `ReadWriteOnce` |
| `persistence.storageClassName` | Storage class | `""` (default) |
| `resources.limits.cpu` | CPU limit | `1` |
| `resources.limits.memory` | Memory limit | `512Mi` |
| `resources.requests.cpu` | CPU request | `100m` |
| `resources.requests.memory` | Memory request | `256Mi` |
| `openshift.enabled` | Enable OpenShift features | `false` |
| `openshift.imageStream.enabled` | Create ImageStream | `true` |

## Usage Examples

### Model Registry Backend

```yaml
# values-model-registry.yaml
database: model_registry
user: registry_user
password: secure_password
persistence:
  enabled: true
  size: 5Gi
```

### Development Environment

```yaml
# values-dev.yaml
persistence:
  enabled: false
resources:
  limits:
    cpu: "500m"
    memory: 256Mi
```

## Connecting to MySQL

The MySQL service is available at:
- Internal: `<release-name>-mysql.<namespace>.svc.cluster.local:3306`
- From same namespace: `<release-name>-mysql:3306`

Connection credentials are stored in a Secret named `<release-name>-mysql` with keys:
- `database-name`
- `database-user`
- `database-password`
- `database-root-password`

## Uninstallation

```bash
helm uninstall mysql
```

Note: PVCs are not automatically deleted. Remove manually if needed:
```bash
kubectl delete pvc mysql
```

