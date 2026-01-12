# Oracle SQLcl MCP Server Container Source

This directory contains the container source code for the Oracle SQLcl MCP (Model Context Protocol) server. The actual deployment is handled by the unified MCP servers helm chart in the parent directory.

## 📋 **Overview**

The Oracle SQLcl MCP Server provides AI assistants (like Cursor IDE) with the ability to:
- Connect to Oracle databases
- Execute SQL queries
- Retrieve database schemas and metadata
- Perform database operations through natural language

This implementation uses **Toolhive** to manage the MCP server deployment and provide HTTP/SSE proxy capabilities for easy integration.

## 🏗️ **Architecture**

```
Client → Port-Forward → Toolhive Proxy → Oracle MCP Server → Oracle Database
```

- **Oracle MCP Server**: SQLcl-based container running MCP protocol over stdio
- **Toolhive Proxy**: Converts stdio to HTTP/SSE for web access
- **OpenShift**: Container orchestration platform

## 📁 **Files in this Directory**

| File | Purpose |
|------|---------|
| `Containerfile` | Container image definition for Oracle SQLcl MCP server |
| `scripts/` | Container startup scripts and configuration |
| `README.md` | This documentation |

## 🚀 **Deployment**

**This container is deployed via the unified MCP servers helm chart in the parent directory.**

See `../README.md` for complete deployment instructions using the MCPServer approach with Toolhive operator.

## 🚀 **Prerequisites**

### **OpenShift Cluster**
- OpenShift 4.x cluster with admin access
- `helm` CLI installed and configured to target your cluster
- Access to create namespaces and security policies

### **Container Registry**
- Access to a container registry (e.g., Quay.io, Docker Hub)
- Registry credentials configured in the cluster if pulling private images

### **Oracle Database**
- Oracle database accessible from OpenShift cluster
- Database credentials (username, password, connection string)
- **Recommended**: Deploy using the `oracle-db` Helm chart which automatically creates user secrets

## 📦 **Build and Push Container Image**

```bash
docker build -f Containerfile -t <your_repo>/oracle-sqlcl-mcp:<tag> .
docker push <your_repo>/oracle-sqlcl-mcp:<tag>
```

## 🧭 **Deploy with Helm**

For installation and configuration, see the Helm chart documentation:

- oracle-sqlcl/helm/README.md

### **Integration with oracle-db Helm Chart**

If you've deployed Oracle database using the `oracle-db` Helm chart, you can easily connect the MCP server to multiple users:

```yaml
# In mcp-servers/helm/values.yaml
mcp-servers:
  oracle-sqlcl:
    enabled: true
    proxyMode: streamable-http  # Use streamable-http for Toolhive
    oracleUserSecrets:           # List of user secrets to mount
      - oracle-db-user-sales
      - oracle-db-user-sales-reader
```

The MCP server will automatically:
- Mount all specified user secrets to `/user-secrets/<secret-name>`
- Create saved connections for each user on startup
- Retry connection attempts for up to 30 minutes (useful during database initialization)

Each secret contains: `username`, `password`, `host`, `port`, and `serviceName`.

## 🧪 **Test with MCP Inspector**

You can use MCP Inspector to interactively test the MCP server over HTTP via the Toolhive proxy.

1. Follow the Helm README to deploy.
2. Port-forward the proxy service per Helm deployment notes.
3. Open MCP Inspector and set the server endpoint to `http://localhost:8081/sse`.
3. Use the following tools:
   - list-connections
   - connect
   - run-sql

Examples:
- list-connections (no params)
  ```json
  {}
  ```
- connect (explicit connection)
  ```json
  { "connectionName": "oracle_db_connection_demo" }
  ```
- run-sql (after connect)
  ```json
  { "sql": "select table_name from user_tables fetch first 5 rows only" }
  ```
- run-sql (with explicit connection)
  ```json
  {
    "connectionName": "oracle_db_connection_demo",
    "sql": "select 1 as ok from dual"
  }
  ```

## 🧩 **Use with Cursor IDE (MCP)**

After deploying and port-forwarding the Toolhive proxy, you can connect Cursor to this MCP server.

1. Ensure the proxy is reachable locally (for example, forward `8081 -> 8080` as described in the Helm NOTES). The SSE endpoint should be `http://localhost:8081/sse`.
2. In Cursor, open Settings and edit your MCP configuration JSON. Add the following:

```json
{
  "mcpServers": {
    "oracle-sqlcl": {
      "url": "http://localhost:8081/sse",
      "enabled": true
    }
  }
}
```

Notes:
- The server key `oracle-sqlcl` is an arbitrary name you can change.
- The `url` should match your local port-forward and the proxy SSE path.
- Once enabled, you can use the tools directly in Cursor: `list-connections`, `connect`, and `run-sql` (see examples in the section above).

## 🔧 Runtime Behavior and Environment

- The container entrypoint (`scripts/start-mcp.sh`) ensures:
  - Stable writable home at `/sqlcl-home` for saved connections
  - Writable Java temp dir at `/sqlcl-home/tmp`
  - Profile scripts are ignored to avoid banner/interactive noise

- On startup, the script scans `/user-secrets/` for mounted user secrets and creates a saved connection for each user found. Each connection uses the username as the connection alias.

## 🔍 **Troubleshooting**

### **Common Issues**

| Issue | Solution |
|-------|----------|
| Pod fails to start | Check SCC permissions and image pull policy |
| Connection refused | Verify port-forward and proxy service |
| Session expired | Bridge script handles this automatically |
| Permission denied | Ensure SCC is applied and bound correctly |
| Thick driver warning | Expected in thin mode; `ORACLE_HOME` is unset intentionally |
| Read-only /tmp (Jansi .lck) | Handled by `JAVA_TOOL_OPTIONS=-Djava.io.tmpdir=/sqlcl-home/tmp` |
| Saved connection missing | Ensure `HOME=/sqlcl-home`; check startup logs for saved connection creation |
| Image pull errors | Check registry credentials and image name |

### **Debugging Commands**

```bash
# Check MCP server logs
oc logs oracle-mcp-server-0 -f

# Check Toolhive proxy logs
oc logs -l app=mcpserver -f

# Check pod status
oc describe pod oracle-mcp-server-0

# Check Toolhive resources
oc get mcpserver
oc describe mcpserver oracle-mcp-server
```

### **Log Locations**

- **MCP Server**: `oc logs oracle-mcp-server-0`
- **Toolhive Proxy**: `oc logs -l app=mcpserver`

## 🔒 **Security Considerations**

### **Database Credentials**
- Use Kubernetes secrets for production deployments
- Rotate credentials regularly
- Limit database user permissions to minimum required

### **Network Security**
- MCP server only accessible within cluster
- Toolhive proxy provides controlled external access
- Port-forward creates secure tunnel to local machine

### **OpenShift Security**
- SCC provides minimal required permissions
- No privileged containers or host access
- Scoped to specific service account

## 📚 **Additional Resources**

- [Toolhive Documentation](https://github.com/stacklok/toolhive)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Oracle SQLcl Documentation](https://docs.oracle.com/en/database/oracle/sql-developer-command-line/)
- [OpenShift Security Context Constraints](https://docs.openshift.com/container-platform/latest/authentication/managing-security-context-constraints.html)

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 **License**

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Need help?** Check the troubleshooting section or open an issue in the repository.
