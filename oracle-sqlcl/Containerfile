# SQLcl MCP Server Docker Image
FROM container-registry.oracle.com/database/sqlcl:latest

# Set environment variables for Oracle SQLcl
ENV ORACLE_HOME=/opt/oracle/sqlcl
ENV JAVA_HOME=/usr/lib/jvm/jdk-17-oracle-x64
ENV PATH=/opt/oracle/sqlcl/bin:$PATH

# Copy maintained scripts and set entrypoint
COPY scripts/start-mcp.sh /start-mcp.sh
COPY scripts/list-saved-connections.sh /list-saved-connections.sh
RUN chmod +x /start-mcp.sh /list-saved-connections.sh

# Start SQLcl in MCP mode
ENTRYPOINT ["/start-mcp.sh"]
