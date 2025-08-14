# Oracle 23ai Helm Chart

Oracle Database Free 23ai deployment for OpenShift/Kubernetes with AI Vector features.

## Prerequisites

- OpenShift/Kubernetes cluster
- `helm` and `oc`/`kubectl` CLI tools
- Cluster admin privileges (for SCC configuration)

## Quick Deploy

```bash
# 1. Create custom SCC for Oracle user (54321)
oc apply -f - <<EOF
apiVersion: security.openshift.io/v1
kind: SecurityContextConstraint
metadata:
  name: oracle-scc
allowHostDirVolumePlugin: false
allowHostIPC: false
allowHostNetwork: false
allowHostPID: false
allowHostPorts: false
allowPrivilegedContainer: false
allowedCapabilities: null
fsGroup:
  type: MustRunAs
  ranges: [{"min": 54321, "max": 54321}]
runAsUser:
  type: MustRunAs
  uid: 54321
seLinuxContext:
  type: MustRunAs
volumes: [configMap, downwardAPI, emptyDir, persistentVolumeClaim, projected, secret]
EOF

# 2. Deploy chart (creates ServiceAccount)
helm install oracle23ai ./helm/ -n <namespace> --create-namespace

# 3. Add SCC to service account (after ServiceAccount exists)
oc adm policy add-scc-to-user oracle-scc -z oracle23ai -n <namespace>

# 4. Restart pod to apply SCC (if needed)
oc delete pod oracle23ai-0 -n <namespace>

# 5. Check status
oc get pods -l app.kubernetes.io/name=oracle23ai -n <namespace>
```

## Configuration

### Required Environment Variables
- `ORACLE_PWD` - Database password (auto-generated if not set)

### Default Settings
- **Host**: `oracle23ai`
- **Port**: `1521` 
- **Service**: `FREEPDB1`
- **SID**: `FREE`
- **Storage**: `10Gi`

### Custom Values
```yaml
# values.yaml
secret:
  password: "MySecurePass123!"
  
resources:
  requests:
    memory: "4Gi"
    cpu: "2"

# Health check timing (for slow environments)
probes:
  readiness:
    initialDelaySeconds: 90
  liveness:
    initialDelaySeconds: 180

# Enable Prometheus monitoring
monitoring:
  enabled: true
  serviceMonitor:
    enabled: true
```

## Access Database

### From Within the Cluster
Other applications in the cluster can connect using:
- **Host**: `oracle23ai`
- **Port**: `1521`
- **Service**: `FREEPDB1`
- **Connection String**: `oracle23ai:1521/FREEPDB1`

Example application configuration:
```yaml
env:
  - name: DB_HOST
    value: "oracle23ai"
  - name: DB_PORT
    value: "1521"
  - name: DB_SERVICE
    value: "FREEPDB1"
  - name: DB_USER
    value: "system"  # or create application-specific user
  - name: DB_PASSWORD
    valueFrom:
      secretKeyRef:
        name: oracle23ai
        key: password
```

### From Outside the Cluster (Development/Testing)
```bash
# Port forward for external access
oc port-forward svc/oracle23ai 1521:1521

# Connect with sqlplus from local machine
sqlplus system/<password>@localhost:1521/FREEPDB1
```

## Testing Database

### Connect to Pod and Test SQL
```bash
# 1. Connect to pod terminal
oc exec -it oracle23ai-0 -- bash

# 2. Connect using OS authentication (recommended - no password needed)
sqlplus / as sysdba

# Alternative: Connect to database as SYSTEM user (if unlocked)
sqlplus system/<password>@localhost:1521/FREEPDB1

# 3. Basic connectivity test
SQL> SELECT 'Hello Oracle 23ai!' FROM DUAL;

# 4. Check database version and AI features
SQL> SELECT BANNER FROM V$VERSION;
SQL> SELECT VALUE FROM V$PARAMETER WHERE NAME = 'compatible';

# 5. Switch to pluggable database for application work
SQL> ALTER SESSION SET CONTAINER = FREEPDB1;

# 6. Test AI Vector functionality (Oracle 23ai feature)
SQL> CREATE TABLE test_vectors (
    id NUMBER,
    description VARCHAR2(100),
    embedding VECTOR(3, FLOAT32)
);

# 7. Insert sample vector data
SQL> INSERT INTO test_vectors VALUES (1, 'Sample vector', '[1.1, 2.2, 3.3]');
SQL> COMMIT;

# 8. Query vector data
SQL> SELECT * FROM test_vectors;

# 9. Test vector similarity (cosine similarity)
SQL> SELECT id, description, 
       VECTOR_DISTANCE(embedding, '[1.0, 2.0, 3.0]', COSINE) as similarity
       FROM test_vectors;

# 10. Unlock SYSTEM account for future password-based connections (optional)
SQL> ALTER USER SYSTEM ACCOUNT UNLOCK;
SQL> ALTER USER SYSTEM IDENTIFIED BY "Oracle123!";

# 11. Exit SQL*Plus
SQL> EXIT;
```

### Get Database Password
```bash
# Decode the auto-generated password
oc get secret oracle23ai -o jsonpath='{.data.password}' | base64 -d
```

## Monitoring

### Prometheus Integration
The chart supports Prometheus monitoring with minimal setup:

```yaml
# Enable monitoring in values.yaml
monitoring:
  enabled: true
  serviceMonitor:
    enabled: true
```

This adds:
- **Metrics exporter sidecar** for database status
- **ServiceMonitor** for automatic Prometheus discovery  
- **Metrics endpoint**: `http://oracle23ai:9161/metrics`

**Prerequisites**: Prometheus Operator installed (standard in OpenShift)

### Viewing Metrics & Dashboards

**OpenShift Console (Recommended):**
1. Navigate to **Observe** → **Metrics** 
2. Query: `oracle23ai_up` - Shows database status (1 = up)
3. Query: `oracle23ai_info` - Shows version and chart info
4. Switch to **Graph** tab for visual time-series charts

**Available Metrics:**
- `oracle23ai_up{instance="oracle23ai-0"}` - Database availability
- `oracle23ai_info{version="23ai",chart="oracle23ai"}` - Deployment info

**Grafana Dashboard:**
If Grafana is available in your cluster, you can create custom dashboards with panels for:
- Database uptime trends
- Pod resource utilization  
- Alert thresholds

## Notes

- First startup takes 5-10 minutes
- Requires custom `oracle-scc` for Oracle user (54321)
- Pod shows RUNNING before READY during initialization
- FREEPDB1 is the pluggable database for connections
- Health probes use OS authentication (`sqlplus / as sysdba`) to avoid locked accounts
- Use `sqlplus / as sysdba` for easiest connection (no password required)