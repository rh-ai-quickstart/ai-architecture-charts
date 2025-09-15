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
  echo "connect -savepwd -save $CONNECTION_ALIAS ${ORACLE_USER}/${ORACLE_PASSWORD}@${ORACLE_CONNECTION_STRING}" | /opt/oracle/sqlcl/bin/sql /NOLOG || true
else
  echo "Skipping saved connection creation; missing ORACLE_USER/ORACLE_PASSWORD/ORACLE_CONNECTION_STRING environment variables"
fi

# Start SQLcl MCP 
exec /opt/oracle/sqlcl/bin/sql -mcp