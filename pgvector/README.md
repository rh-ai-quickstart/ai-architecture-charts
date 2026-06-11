# PGVector Helm Chart

This Helm chart deploys PostgreSQL with the pgvector extension enabled, providing vector similarity search capabilities for AI/ML applications. It is a thin wrapper around the [postgres chart](../postgres/), adding only the pgvector image and the `CREATE EXTENSION vector` initialization.

## Overview

The pgvector chart:
- Depends on the [postgres](../postgres/) chart for all infrastructure (StatefulSet, Service, Secret, storage)
- Uses the `pgvector/pgvector` image instead of the plain `postgres` image
- Runs an init script to enable the vector extension on the default database
- Supports enabling vector extension on extra databases

## Prerequisites

- OpenShift cluster or Kubernetes 1.19+
- Helm 3.x
- Persistent storage (PVC support)

## Installation

### Basic Installation

```bash
cd pgvector
helm dependency update ./helm
helm install pgvector ./helm
```

### Installation with Custom Credentials

```bash
helm install pgvector ./helm \
  --set postgres.secret.user=myuser \
  --set postgres.secret.password=secure_password123 \
  --set postgres.secret.dbname=vector_db
```

### Installation with Extra Vector Databases

```bash
helm install pgvector ./helm \
  --set postgres.extraDatabases[0].name=embeddings_db \
  --set postgres.extraDatabases[0].extensions[0]=vector
```

## Configuration

All configuration is passed through to the postgres subchart under the `postgres:` key. See the [postgres chart README](../postgres/README.md) for the full list of options.

### pgvector-Specific Defaults

| Parameter | Description | Default |
|-----------|-------------|---------|
| `postgres.image.repository` | pgvector image | `docker.io/pgvector/pgvector` |
| `postgres.image.tag` | PostgreSQL version with pgvector | `pg17` |
| `postgres.secret.dbname` | Default database name | `rag_blueprint` |
| `postgres.secret.host` | Service hostname | `pgvector` |
| `postgres.initScripts` | Creates vector extension on default DB | `CREATE EXTENSION IF NOT EXISTS vector` |

### Extra Databases with Vector Extension

```yaml
postgres:
  extraDatabases:
    - name: embeddings_db
      extensions:
        - vector
    - name: analytics_db
```

## Usage

### Vector Operations

```sql
\c rag_blueprint

CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    title TEXT,
    content TEXT,
    embedding VECTOR(1536)
);

CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops);

SELECT id, title, embedding <=> '[0.1, 0.2, ...]'::vector AS distance
FROM documents
ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector
LIMIT 5;
```

### Python Integration

```python
import psycopg2
from pgvector.psycopg2 import register_vector

conn = psycopg2.connect(
    host="pgvector",
    port=5432,
    database="rag_blueprint",
    user="postgres",
    password="rag_password"
)
register_vector(conn)
```

## Architecture

```
pgvector chart (thin wrapper)
├── Chart.yaml         ← declares postgres as dependency
├── values.yaml        ← overrides: image, initScripts, names
└── (no templates)     ← everything comes from postgres subchart
    └── postgres chart (full chart)
        └── templates/
            ├── statefulset.yaml
            ├── service.yaml
            ├── secret.yaml
            ├── configmap.yaml
            └── _helpers.tpl
```

## Uninstalling

```bash
helm uninstall pgvector
oc delete pvc -l app.kubernetes.io/name=pgvector
```
