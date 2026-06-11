# PGVector Helm Chart

This Helm chart deploys PostgreSQL with pgvector extension, providing a powerful vector database solution for storing and querying high-dimensional embeddings in AI/ML applications.

## Overview

The pgvector chart creates:
- PostgreSQL deployment with pgvector extension enabled
- Service for database connections
- Secret management for database credentials
- Persistent storage for data
- StatefulSet for data consistency
- Support for multiple databases and vector operations

## Prerequisites

- OpenShift cluster
- Helm 3.x
- Persistent storage (PVC support)
- Sufficient storage and memory for vector operations

## Installation

### Basic Installation

```bash
helm install pgvector ./helm
```

### Installation with Custom Credentials

```bash
helm install pgvector ./helm \
  --set secret.user=postgres \
  --set secret.password=secure_password123 \
  --set secret.dbname=vector_db
```

### Installation with Multiple Databases

```bash
helm install pgvector ./helm \
  --set extraDatabases[0].name=embeddings_db \
  --set extraDatabases[0].vectordb=true \
  --set extraDatabases[1].name=analytics_db \
  --set extraDatabases[1].vectordb=false
```

### Installation with Custom Namespace

```bash
helm install pgvector ./helm \
  --namespace vector-db \
  --create-namespace
```

## Configuration

### Key Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of replicas (always 1 for PostgreSQL) | `1` |
| `image.repository` | PostgreSQL + pgvector image repository | `docker.io/pgvector/pgvector` |
| `image.tag` | PostgreSQL version with pgvector | `pg17` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `service.type` | Service type | `ClusterIP` |
| `service.port` | PostgreSQL port | `5432` |
| `secret.user` | Database username | `postgres` |
| `secret.password` | Database password | `rag_password` |
| `secret.dbname` | Default database name | `rag_blueprint` |
| `secret.host` | Database service hostname | `pgvector` |
| `secret.port` | Database port | `"5432"` |

### Storage Configuration

```yaml
volumeClaimTemplates:
  - metadata:
      name: pg-data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 5Gi

volumeMounts:
  - mountPath: /docker-entrypoint-initdb.d
    name: initdb-volume
  - mountPath: /var/lib/postgresql
    name: pg-data
```

### Extra Databases Configuration

```yaml
extraDatabases:
  - name: embeddings_db
    vectordb: true  # Will have pgvector extension enabled
  - name: analytics_db
    vectordb: false # Regular PostgreSQL database
  - name: test_db
    vectordb: true
```

### Complete Example values.yaml

```yaml
replicaCount: 1

image:
  repository: docker.io/pgvector/pgvector
  pullPolicy: IfNotPresent
  tag: "pg17"

nameOverride: "pgvector"
fullnameOverride: "pgvector"

service:
  type: ClusterIP
  port: 5432

# Database configuration
env:
  - name: POSTGRES_USER
    valueFrom:
      secretKeyRef:
        key: user
        name: pgvector
  - name: POSTGRES_PASSWORD
    valueFrom:
      secretKeyRef:
        key: password
        name: pgvector
  - name: POSTGRES_PORT
    valueFrom:
      secretKeyRef:
        key: port
        name: pgvector
  - name: POSTGRES_DBNAME
    valueFrom:
      secretKeyRef:
        key: dbname
        name: pgvector

# Resource limits
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "1000m"

# Storage configuration
volumeClaimTemplates:
  - metadata:
      name: pg-data
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: gp2
      resources:
        requests:
          storage: 20Gi

volumeMounts:
  - mountPath: /docker-entrypoint-initdb.d
    name: initdb-volume
  - mountPath: /var/lib/postgresql
    name: pg-data

# Database credentials
secret:
  user: postgres
  password: your_secure_password_here
  dbname: vector_database
  host: pgvector
  port: "5432"

# Additional databases
extraDatabases:
  - name: rag_embeddings
    vectordb: true
  - name: model_cache
    vectordb: false
  - name: analytics
    vectordb: true

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
            - pgvector
        topologyKey: kubernetes.io/hostname
```

## Usage

### Connecting to the Database

#### From Within the Cluster

```bash
# Connect using psql from another pod
oc run psql-client --rm -it --image=postgres:17 -- bash

# Inside the container:
psql -h pgvector -U postgres -d rag_blueprint
```

#### Port Forwarding for External Access

```bash
# Port forward for local access
oc port-forward svc/pgvector 5432:5432

# Connect from local machine
psql -h localhost -U postgres -d rag_blueprint
```

### Vector Operations

#### Creating Vector Tables

```sql
-- Connect to database
\c rag_blueprint

-- Enable pgvector extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS vector;

-- Create table with vector column
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    title TEXT,
    content TEXT,
    embedding VECTOR(1536)  -- OpenAI embedding size
);

-- Create index for faster similarity search
CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Alternative index types
CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops);
```

#### Inserting Vector Data

```sql
-- Insert document with embedding
INSERT INTO documents (title, content, embedding) VALUES (
    'AI Introduction',
    'Artificial Intelligence enables machines to simulate human intelligence...',
    '[0.1, 0.2, 0.3, ...]'::vector  -- Your actual embedding array
);

-- Insert multiple documents
INSERT INTO documents (title, content, embedding) VALUES 
    ('Machine Learning', 'ML is a subset of AI...', '[0.2, 0.3, 0.4, ...]'::vector),
    ('Deep Learning', 'DL uses neural networks...', '[0.15, 0.25, 0.35, ...]'::vector);
```

#### Vector Similarity Queries

```sql
-- Find similar documents using cosine similarity
SELECT id, title, 
       1 - (embedding <=> '[0.1, 0.2, 0.3, ...]'::vector) as cosine_similarity
FROM documents
ORDER BY embedding <=> '[0.1, 0.2, 0.3, ...]'::vector
LIMIT 5;

-- Find similar documents using L2 distance
SELECT id, title,
       embedding <-> '[0.1, 0.2, 0.3, ...]'::vector as l2_distance
FROM documents
ORDER BY embedding <-> '[0.1, 0.2, 0.3, ...]'::vector
LIMIT 5;

-- Find similar documents using inner product
SELECT id, title,
       embedding <#> '[0.1, 0.2, 0.3, ...]'::vector as inner_product
FROM documents
ORDER BY embedding <#> '[0.1, 0.2, 0.3, ...]'::vector DESC
LIMIT 5;
```

### Python Integration

```python
import psycopg2
import numpy as np
from pgvector.psycopg2 import register_vector

# Connect to database
conn = psycopg2.connect(
    host="pgvector",  # or localhost if port-forwarding
    port=5432,
    database="rag_blueprint",
    user="postgres",
    password="rag_password"
)

# Register vector type
register_vector(conn)

# Create cursor
cur = conn.cursor()

# Insert vector data
embedding = np.random.random(1536)  # Your actual embedding
cur.execute(
    "INSERT INTO documents (title, content, embedding) VALUES (%s, %s, %s)",
    ("Python Integration", "Using pgvector with Python...", embedding)
)

# Query similar vectors
query_embedding = np.random.random(1536)  # Your query embedding
cur.execute(
    """
    SELECT id, title, embedding <=> %s as distance
    FROM documents
    ORDER BY embedding <=> %s
    LIMIT 5
    """,
    (query_embedding, query_embedding)
)

results = cur.fetchall()
for row in results:
    print(f"ID: {row[0]}, Title: {row[1]}, Distance: {row[2]}")

conn.close()
```

## Monitoring and Troubleshooting

### Checking Service Health

```bash
# Check pod status
oc get pods -l app.kubernetes.io/name=pgvector

# Check StatefulSet
oc get statefulset pgvector

# Check service
oc get svc pgvector

# Test database connection
oc exec -it pgvector-0 -- psql -U postgres -d rag_blueprint -c "SELECT version();"
```

### Viewing Logs

```bash
# View PostgreSQL logs
oc logs pgvector-0 -f

# Check StatefulSet events
oc describe statefulset pgvector

# Check PVC status
oc get pvc -l app.kubernetes.io/name=pgvector
```

### Common Issues

1. **Pod Won't Start**:
   - Check PVC binding status
   - Verify storage class availability
   - Check resource limits
   - Review initialization scripts

2. **Connection Refused**:
   - Verify service configuration
   - Check database initialization
   - Validate credentials
   - Test network connectivity

3. **Vector Operations Failing**:
   - Ensure pgvector extension is enabled
   - Check vector dimensions match
   - Verify index creation
   - Review query syntax

4. **Performance Issues**:
   - Monitor resource usage
   - Check index usage in queries
   - Review storage I/O performance
   - Consider memory optimization

### Debugging Commands

```bash
# Check database status
oc exec -it pgvector-0 -- pg_isready -U postgres

# List databases
oc exec -it pgvector-0 -- psql -U postgres -l

# Check extensions
oc exec -it pgvector-0 -- psql -U postgres -d rag_blueprint -c "\dx"

# Check vector tables
oc exec -it pgvector-0 -- psql -U postgres -d rag_blueprint -c "\dt"

# Check vector indexes
oc exec -it pgvector-0 -- psql -U postgres -d rag_blueprint -c "\di"

# Monitor connections
oc exec -it pgvector-0 -- psql -U postgres -d rag_blueprint -c "SELECT * FROM pg_stat_activity;"
```

## Backup and Recovery

### Database Backup

```bash
# Create backup
oc exec -it pgvector-0 -- pg_dump -U postgres rag_blueprint > backup.sql

# Backup with custom format (compressed)
oc exec -it pgvector-0 -- pg_dump -U postgres -Fc rag_blueprint > backup.dump

# Backup all databases
oc exec -it pgvector-0 -- pg_dumpall -U postgres > all_databases.sql
```

### Database Restore

```bash
# Restore from SQL backup
oc exec -i pgvector-0 -- psql -U postgres rag_blueprint < backup.sql

# Restore from custom format
oc exec -it pgvector-0 -- pg_restore -U postgres -d rag_blueprint backup.dump

# Create database and restore
oc exec -it pgvector-0 -- createdb -U postgres new_database
oc exec -i pgvector-0 -- psql -U postgres new_database < backup.sql
```

### Automated Backups

```yaml
# CronJob for automated backups
apiVersion: batch/v1
kind: CronJob
metadata:
  name: pgvector-backup
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:17
            command:
            - /bin/bash
            - -c
            - pg_dump -h pgvector -U postgres rag_blueprint > /backup/backup-$(date +%Y%m%d).sql
            env:
            - name: PGPASSWORD
              valueFrom:
                secretKeyRef:
                  name: pgvector
                  key: password
            volumeMounts:
            - name: backup-storage
              mountPath: /backup
          volumes:
          - name: backup-storage
            persistentVolumeClaim:
              claimName: backup-pvc
          restartPolicy: OnFailure
```

## Security Considerations

### Access Control

```sql
-- Create application user with limited privileges
CREATE USER app_user WITH PASSWORD 'app_password';

-- Grant specific database access
GRANT CONNECT ON DATABASE rag_blueprint TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- Grant permissions on future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;
```

### SSL/TLS Configuration

```yaml
# Enable SSL
env:
  - name: POSTGRES_INITDB_ARGS
    value: "--auth-host=md5"
  - name: POSTGRES_HOST_AUTH_METHOD
    value: "md5"

volumeMounts:
  - name: ssl-certs
    mountPath: /var/lib/postgresql/server.crt
    subPath: server.crt
    readOnly: true
  - name: ssl-certs
    mountPath: /var/lib/postgresql/server.key
    subPath: server.key
    readOnly: true

volumes:
  - name: ssl-certs
    secret:
      secretName: pgvector-ssl
      defaultMode: 0600
```

### Network Security

```yaml
# Network policy
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: pgvector-netpol
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: pgvector
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: llama-stack
    - podSelector:
        matchLabels:
          app: ogx-ai
    - podSelector:
        matchLabels:
          app: ingestion-pipeline
    ports:
    - protocol: TCP
      port: 5432
```

## Upgrading

```bash
# Upgrade PostgreSQL version
helm upgrade pgvector ./helm \
  --set image.tag=pg16

# Check upgrade status
oc rollout status statefulset/pgvector

# Verify upgrade
oc exec -it pgvector-0 -- psql -U postgres -c "SELECT version();"
```

## Uninstalling

```bash
# Remove chart
helm uninstall pgvector

# Remove persistent data (WARNING: This deletes all data)
oc delete pvc -l app.kubernetes.io/name=pgvector

# Remove secrets (if needed)
oc delete secret pgvector
```

## Integration with AI Components

This chart integrates with:

- **LlamaStack / OGX**: Vector storage for embeddings and agent memory
- **Ingestion Pipeline**: Document embedding storage
- **Configure Pipeline**: Configuration and metadata storage
- **AI Applications**: Vector similarity search and retrieval

### Example Integration Configuration

```yaml
# In other components, reference PGVector
env:
  - name: POSTGRES_HOST
    valueFrom:
      secretKeyRef:
        name: pgvector
        key: host
  - name: POSTGRES_PORT
    valueFrom:
      secretKeyRef:
        name: pgvector
        key: port
  - name: POSTGRES_USER
    valueFrom:
      secretKeyRef:
        name: pgvector
        key: user
  - name: POSTGRES_PASSWORD
    valueFrom:
      secretKeyRef:
        name: pgvector
        key: password
  - name: POSTGRES_DBNAME
    valueFrom:
      secretKeyRef:
        name: pgvector
        key: dbname
```

## Advanced Configuration

### Custom Initialization Scripts

```yaml
# Mount custom init scripts
volumeMounts:
  - mountPath: /docker-entrypoint-initdb.d
    name: initdb-scripts

volumes:
  - name: initdb-scripts
    configMap:
      name: pgvector-init-scripts
```

### Connection Pooling

```yaml
# Deploy PgBouncer for connection pooling
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pgbouncer
spec:
  template:
    spec:
      containers:
      - name: pgbouncer
        image: pgbouncer/pgbouncer:latest
        env:
        - name: DATABASES_HOST
          value: pgvector
        - name: DATABASES_PORT
          value: "5432"
        - name: POOL_MODE
          value: "transaction"
        - name: MAX_CLIENT_CONN
          value: "100"
```