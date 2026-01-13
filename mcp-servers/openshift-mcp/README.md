# OpenShift MCP Server

The OpenShift MCP (Model Context Protocol) server provides Kubernetes and OpenShift cluster management capabilities to AI models. This server enables AI agents to interact with Kubernetes/OpenShift clusters through standardized MCP tools.

## 📚 Overview

- **Purpose:** Enables AI agents to manage Kubernetes/OpenShift resources, deployments, and cluster operations
- **Source:** [github.com/openshift/openshift-mcp-server](https://github.com/openshift/openshift-mcp-server)
- **Image:** `quay.io/containers/kubernetes_mcp_server:latest`
- **Transport:** Native streamable-http and SSE support - no proxy required
- **Endpoints:** `/mcp` (streamable-http), `/sse` (SSE), `/message`

---

## 🚀 Features

The OpenShift MCP server provides comprehensive Kubernetes and OpenShift management tools:

### 🏗️ Core Kubernetes Operations
- `configuration_view` — View current Kubernetes configuration
- `api_resources_list` — List available API resources in the cluster
- `events_list` — List events in the cluster
- `namespaces_list` — List namespaces
- `pod_list` — List pods in a namespace
- `pod_get` — Get details of a specific pod
- `pod_log` — Get logs from a pod
- `pod_run` — Run a new pod
- `pod_delete` — Delete a pod
- `pod_exec` — Execute a command in a pod
- `resources_list` — List resources of a specific type
- `resource_get` — Get a specific resource
- `resource_create` — Create a resource from YAML/JSON
- `resource_update` — Update an existing resource
- `resource_delete` — Delete a resource
- `resources_watch` — Watch for changes to resources

### 📦 Helm Operations
- `helm_install` — Install a Helm chart
- `helm_list` — List Helm releases
- `helm_uninstall` — Uninstall a Helm release

### 🔧 OpenShift-Specific Operations
- `project_list` — List OpenShift projects
- `route_list` — List routes
- `buildconfig_list` — List build configurations
- `imagestream_list` — List image streams

### 🌐 Service Mesh (Kiali) Integration
- `kiali_get_resources` — Get service mesh resources
- `kiali_get_metrics` — Get service mesh metrics
- `kiali_workload_logs` — Get workload logs
- `kiali_get_traces` — Get distributed traces

### 🖥️ KubeVirt Integration
- `vm_create` — Create a VirtualMachine
- `vm_lifecycle` — Manage VM lifecycle (start/stop/restart)

---

## 📦 Deployment

### Prerequisites

- Kubernetes or OpenShift cluster (4.12+)
- Valid kubeconfig or service account with appropriate RBAC permissions
- Network access to the Kubernetes API server

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `KUBECONFIG` | Path to kubeconfig file | No (uses in-cluster config if not set) |
| `MCP_TRANSPORT` | Transport mode (sse/streamable-http) | No (defaults to sse) |

### RBAC Requirements

The MCP server requires appropriate permissions to interact with cluster resources. Create a service account with the necessary roles:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: openshift-mcp
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: openshift-mcp-admin
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin  # Or a more restrictive custom role
subjects:
- kind: ServiceAccount
  name: openshift-mcp
  namespace: default
```

### Helm Installation

```bash
# Install with MCP servers Helm chart
helm upgrade -i mcp-servers ./mcp-servers/helm \
  --set mcp-servers.openshift-mcp.enabled=true \
  --namespace <your-namespace>
```

---

## 🛠️ Configuration

### Values Configuration

```yaml
mcp-servers:
  openshift-mcp:
    enabled: true
    deploymentMode: deployment
    image:
      repository: quay.io/containers/kubernetes_mcp_server
      tag: "latest"
    transport: streamable-http
    targetPort: 8080
    # Optional: Specify a service account with appropriate RBAC
    # serviceAccountName: openshift-mcp
```

### Security Considerations

- **In-cluster deployment:** When running inside the cluster, the MCP server uses the pod's service account for authentication
- **External deployment:** Provide a kubeconfig file via secret mount
- **RBAC:** Follow the principle of least privilege - grant only necessary permissions

---

## 🔌 Integration

### Connecting to the MCP Server

The server exposes multiple endpoints:

- **Streamable HTTP:** `http://<service-name>:8080/mcp` (recommended)
- **SSE Endpoint:** `http://<service-name>:8080/sse`
- **Message Endpoint:** `http://<service-name>:8080/message`

### Example Usage with AI Agents

```python
# Example: Connect to OpenShift MCP server
mcp_endpoint = "http://mcp-openshift-mcp:8080/sse"

# List pods in a namespace
response = await mcp_client.call_tool(
    "pod_list",
    {"namespace": "default"}
)
```

---

## 📋 Available Tools Reference

| Tool | Description |
|------|-------------|
| `configuration_view` | View kubeconfig info |
| `api_resources_list` | List API resources |
| `events_list` | List cluster events |
| `namespaces_list` | List namespaces |
| `pod_list` | List pods |
| `pod_get` | Get pod details |
| `pod_log` | Get pod logs |
| `pod_run` | Run a pod |
| `pod_delete` | Delete a pod |
| `pod_exec` | Execute command in pod |
| `resources_list` | List resources |
| `resource_get` | Get resource |
| `resource_create` | Create resource |
| `resource_update` | Update resource |
| `resource_delete` | Delete resource |
| `resources_watch` | Watch resources |
| `helm_install` | Install Helm chart |
| `helm_list` | List Helm releases |
| `helm_uninstall` | Uninstall Helm release |

---

## 🐛 Troubleshooting

### Common Issues

1. **Permission Denied Errors:**
   - Verify RBAC permissions for the service account
   - Check ClusterRoleBindings: `oc get clusterrolebindings | grep openshift-mcp`

2. **Connection Refused:**
   - Ensure the service is running: `oc get pods -l app.kubernetes.io/name=openshift-mcp`
   - Check service endpoints: `oc get endpoints mcp-openshift-mcp`

3. **Authentication Errors:**
   - For in-cluster: Verify service account token is mounted
   - For external: Check kubeconfig secret is properly mounted

### Debug Commands

```bash
# Check pod status
oc get pods -l app.kubernetes.io/name=openshift-mcp

# View logs
oc logs -l app.kubernetes.io/name=openshift-mcp

# Test connectivity
oc exec -it <pod-name> -- curl http://localhost:8080/sse

# Verify RBAC
oc auth can-i list pods --as=system:serviceaccount:<namespace>:openshift-mcp
```

---

## 📖 References

- [OpenShift MCP Server GitHub](https://github.com/openshift/openshift-mcp-server)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Kubernetes RBAC Documentation](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
