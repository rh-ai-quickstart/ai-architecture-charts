#!/bin/bash
set -e
set -x

echo "Starting Oracle SQLcl MCP Server..."
echo "ORACLE_HOME: $ORACLE_HOME"
echo "JAVA_HOME: $JAVA_HOME"
echo "PATH: $PATH"
echo "Oracle Connection: $ORACLE_CONNECTION_STRING"

echo "Starting MCP Server for Toolhive proxy access..."

# Avoid JVM option injection issues
unset JAVA_TOOL_OPTIONS || true
unset _JAVA_OPTIONS || true

# Ensure writable Java temp directory to avoid Jansi lock error
mkdir -p /sqlcl-home/tmp || true
# Ensure a stable home directory for SQLcl user data (saved connections)
export HOME=/sqlcl-home
export JAVA_TOOL_OPTIONS="-Djava.io.tmpdir=/sqlcl-home/tmp -Duser.home=/sqlcl-home"
echo "JAVA_TOOL_OPTIONS: $JAVA_TOOL_OPTIONS"

# Avoid thick driver warning and site/user profile side effects
unset ORACLE_HOME || true
echo "ORACLE_HOME after unset: ${ORACLE_HOME:-<unset>}"
mkdir -p /sqlcl-home/empty || true
export SQLPATH=/sqlcl-home/empty
cd /sqlcl-home || true

# Create a saved SQLcl connection if env vars provided
if [ -n "$ORACLE_USER" ] && [ -n "$ORACLE_PASSWORD" ] && [ -n "$ORACLE_CONNECTION_STRING" ]; then
  CONNECTION_ALIAS=${ORACLE_CONN_NAME:-oracle_connection}
  echo "Creating saved connection: $CONNECTION_ALIAS"
  
  # Extract the actual connection string from JDBC URL format
  # ORACLE_CONNECTION_STRING format: jdbc:oracle:thin:@host:port/service
  # We need to extract: host:port/service
  CONNECTION_HOST_PORT_SERVICE=$(echo "$ORACLE_CONNECTION_STRING" | sed 's/jdbc:oracle:thin:@//')
  echo "Extracted connection string: $CONNECTION_HOST_PORT_SERVICE"
  
  # Create connection command without echoing password
  CONNECT_CMD="connect -savepwd -save $CONNECTION_ALIAS ${ORACLE_USER}/${ORACLE_PASSWORD}@${CONNECTION_HOST_PORT_SERVICE}"
  echo "Creating connection: $CONNECTION_ALIAS for user: ${ORACLE_USER}@${CONNECTION_HOST_PORT_SERVICE}"
  echo "$CONNECT_CMD" | /opt/oracle/sqlcl/bin/sql /NOLOG || true
  
  # Verify the saved connection was created successfully
  echo "Verifying saved connection..."
  echo "connmgr show $CONNECTION_ALIAS" | /opt/oracle/sqlcl/bin/sql /NOLOG || true
else
  echo "Skipping saved connection creation; missing ORACLE_USER/ORACLE_PASSWORD/ORACLE_CONNECTION_STRING environment variables"
fi

# Start SQLcl MCP 
# The MCP server will use the saved connection 'oracle_connection' 
# with: connect -name oracle_connection
exec /opt/oracle/sqlcl/bin/sql -mcp