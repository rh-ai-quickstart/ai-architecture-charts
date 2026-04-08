# PostgreSQL Helm Chart

This Helm chart deploys PostgreSQL as a StatefulSet, providing a reliable relational database for applications. It serves as the base chart for all PostgreSQL-based deployments, including the [pgvector](../pgvector/) chart which extends it with vector similarity search capabilities.

## Overview

The postgres chart creates:
- PostgreSQL StatefulSet for data consistency
- Service for database connections
- Secret with credentials and connection URIs
- Persistent storage via VolumeClaimTemplates
- Optional init scripts and extra databases via ConfigMap

## Prerequisites

- OpenShift cluster or Kubernetes 1.19+
- Helm 3.x
- Persistent storage (PVC support)

## Installation

### Basic Installation

```bash
helm install postgres ./helm
```

### Installation with Custom Credentials

```bash
helm install postgres ./helm \
  --set secret.user=myuser \
  --set secret.password=secure_password123 \
  --set secret.dbname=myapp
```

### Installation with Init Scripts

```bash
helm install postgres ./helm \
  --set-file initScripts.setup\\.sh=scripts/setup.sh
```

### Installation with Extra Databases

```bash
helm install postgres ./helm \
  --set extraDatabases[0].name=analytics_db \
  --set extraDatabases[1].name=embeddings_db \
  --set extraDatabases[1].extensions[0]=pg_trgm
```

## Configuration

### Key Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of replicas (always 1 for PostgreSQL) | `1` |
| `image.repository` | PostgreSQL image repository | `docker.io/library/postgres` |
| `image.tag` | PostgreSQL version | `16` |
| `service.type` | Service type | `ClusterIP` |
| `service.port` | PostgreSQL port | `5432` |
| `service.portName` | Port name for the service | `postgresql` |
| `pgdata` | PostgreSQL data directory | `/var/lib/postgresql/data/pgdata` |
| `secret.user` | Database username | `postgres` |
| `secret.password` | Database password | `rag_password` |
| `secret.dbname` | Default database name | `partner_agent` |
| `secret.host` | Database service hostname | `postgres` |
| `secret.port` | Database port | `"5432"` |

### Init Scripts

Custom initialization scripts run on first container start. Mounted at `/docker-entrypoint-initdb.d` and executed in alphabetical order:

```yaml
initScripts:
  01-create-extensions.sh: |
    #!/bin/bash
    set -e
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
  02-seed-data.sh: |
    #!/bin/bash
    set -e
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "INSERT INTO config (key, value) VALUES ('version', '1.0');"
```

### Extra Databases

Create additional databases on init, with optional extensions:

```yaml
extraDatabases:
  - name: analytics_db
  - name: embeddings_db
    extensions:
      - vector
      - pg_trgm
```

### Secret Output

The chart produces a Secret with the following keys:

| Key | Description |
|-----|-------------|
| `user` | Database username |
| `password` | Database password |
| `host` | Service hostname |
| `port` | Service port |
| `dbname` | Default database name |
| `uri` | Full connection URI (`postgresql://user:pass@host.ns:port/db`) |
| `jdbc-uri` | JDBC connection URI |

### Additional Environment Variables

```yaml
extraEnv:
  - name: POSTGRES_INITDB_ARGS
    value: "--auth-host=md5"
```

## Usage as a Base Chart

This chart is designed to be used as a dependency by specialized charts. For example, the [pgvector chart](../pgvector/) wraps this chart and adds the vector extension:

```yaml
# In a parent Chart.yaml
dependencies:
  - name: postgres
    version: ">=0.1.0"
    repository: "file://../../postgres/helm"
```

Override values via the `postgres:` key in the parent chart's `values.yaml`.

## Monitoring and Troubleshooting

### Checking Service Health

```bash
oc get pods -l app.kubernetes.io/name=postgres
oc get statefulset postgres
oc exec -it postgres-0 -- psql -U postgres -d partner_agent -c "SELECT version();"
```

### Viewing Logs

```bash
oc logs postgres-0 -f
oc describe statefulset postgres
oc get pvc -l app.kubernetes.io/name=postgres
```

## Uninstalling

```bash
helm uninstall postgres

# Remove persistent data (WARNING: This deletes all data)
oc delete pvc -l app.kubernetes.io/name=postgres
```
