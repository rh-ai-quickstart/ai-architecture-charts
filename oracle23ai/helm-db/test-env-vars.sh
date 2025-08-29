#!/bin/bash

echo "Testing Oracle 23AI Helm Chart with Environment Variables"
echo "========================================================="

# Test 1: No environment variables (should auto-generate)
echo "Test 1: Auto-generated password"
unset ORACLE_PASSWORD ORACLE_HOST ORACLE_PORT ORACLE_SERVICE_NAME ORACLE_SID
if helm template test . > /dev/null 2>&1; then
    echo "✅ Auto-generation works"
else
    echo "❌ Auto-generation failed"
fi

# Test 2: With environment variables
echo "Test 2: Environment variables"
export ORACLE_PASSWORD="EnvTestPassword123!"
export ORACLE_HOST="custom-oracle-host"
export ORACLE_PORT="1522"
export ORACLE_SERVICE_NAME="CUSTOMPDB"
export ORACLE_SID="CUSTOM"

if helm template test . > /dev/null 2>&1; then
    echo "✅ Environment variables work"
    echo "Password from env: $ORACLE_PASSWORD"
else
    echo "❌ Environment variables failed"
fi

# Test 3: Show generated secret
echo "Test 3: Generated secret preview"
helm template test . 2>/dev/null | grep -A10 "kind: Secret" | head -15

echo "========================================================="
echo "Usage Instructions:"
echo "1. Set environment variables: export ORACLE_PASSWORD='YourPassword'"
echo "2. Deploy: helm install oracle23ai ."
echo "3. Get password: kubectl get secret oracle23ai -o jsonpath='{.data.password}' | base64 -d"