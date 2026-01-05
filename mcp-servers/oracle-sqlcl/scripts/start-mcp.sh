#!/bin/bash
set -e

echo "Starting Oracle SQLcl MCP HTTP Proxy..."

# Auto-detect JAVA_HOME based on architecture
if [ -z "$JAVA_HOME" ]; then
  if [ -d "/usr/lib/jvm/jdk-17-oracle-aarch64" ]; then
    export JAVA_HOME=/usr/lib/jvm/jdk-17-oracle-aarch64
  elif [ -d "/usr/lib/jvm/jdk-17-oracle-x64" ]; then
    export JAVA_HOME=/usr/lib/jvm/jdk-17-oracle-x64
  fi
fi

echo "ORACLE_HOME: $ORACLE_HOME"
echo "JAVA_HOME: $JAVA_HOME"
echo "PATH: $PATH"

echo "Starting MCP HTTP Proxy (will spawn sql -mcp)..."

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

# Create saved connection for a user (retry for 30 minutes)
create_user_connection() {
  local user="$1"
  local pwd="$2"
  local host="$3"
  local port="$4"
  local service="$5"
  local conn="${host}:${port}/${service}"

  echo "Creating saved connection for: ${user}@${conn}"

  local max_retries=120
  local retry_count=0

  while [ $retry_count -lt $max_retries ]; do
    echo "Testing connection (attempt $((retry_count + 1))/$max_retries)..."
    if /opt/oracle/sqlcl/bin/sql -S -L ${user}/${pwd}@${conn} <<< "exit" >/dev/null 2>&1; then
      echo "Successfully connected to Oracle database!"

      if echo "connect -savepwd -save ${user} ${user}/${pwd}@${conn}" | /opt/oracle/sqlcl/bin/sql /NOLOG >/dev/null 2>&1; then
        echo "Successfully created saved connection: ${user}"
        return 0
      else
        echo "WARNING: Failed to create saved connection. Retrying in 15 seconds..."
      fi
    fi

    retry_count=$((retry_count + 1))
    if [ $retry_count -lt $max_retries ]; then
      sleep 15
    fi
  done

  echo "ERROR: Failed to connect to Oracle and create saved connection for ${user} after 30 minutes"
  return 1
}

# Create saved connections for all mounted user secrets
echo "Creating saved connections for all users..."
for secret_dir in /user-secrets/*; do
  [ -d "$secret_dir" ] || continue

  user=$(cat "$secret_dir/username" 2>/dev/null) || continue
  pwd=$(cat "$secret_dir/password" 2>/dev/null) || continue
  host=$(cat "$secret_dir/host" 2>/dev/null) || continue
  port=$(cat "$secret_dir/port" 2>/dev/null) || continue
  service=$(cat "$secret_dir/serviceName" 2>/dev/null) || continue

  create_user_connection "$user" "$pwd" "$host" "$port" "$service" || exit 1
  echo ""
done

echo "All saved connections created successfully"
echo ""

# Start MCP HTTP Proxy (which will spawn sql -mcp)
exec /usr/local/bin/mcp-proxy
