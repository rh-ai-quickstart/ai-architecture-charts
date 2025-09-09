#!/bin/bash
set -e
unset JAVA_TOOL_OPTIONS || true
unset _JAVA_OPTIONS || true
unset ORACLE_HOME || true

# Ensure stable, writable env for SQLcl
mkdir -p /sqlcl-home/tmp /sqlcl-home/empty || true
export HOME=/sqlcl-home
export SQLPATH=/sqlcl-home/empty
export JAVA_TOOL_OPTIONS="-Djava.io.tmpdir=/sqlcl-home/tmp -Duser.home=/sqlcl-home"

echo "Listing saved SQLcl connections..."
echo "connmgr list -flat" | /opt/oracle/sqlcl/bin/sql -thin -S /NOLOG


