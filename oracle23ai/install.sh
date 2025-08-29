#!/bin/bash

# Oracle 23AI Sequential Installation Script
# This script installs Oracle DB and TPC-DS data loader sequentially using separate charts
# 
# Prerequisites:
# - oc (OpenShift CLI)
# - helm (Helm 3.x)
# - sqlplus (Oracle SQL*Plus client) - optional but recommended for testing

set -euo pipefail

# Configuration
NAMESPACE="${NAMESPACE:-oracle23ai}"
DB_RELEASE_NAME="${DB_RELEASE_NAME:-oracle23ai-db}"
LOADER_RELEASE_NAME="${LOADER_RELEASE_NAME:-oracle23ai-loader}"
DB_CHART_PATH="${DB_CHART_PATH:-./helm-db}"
LOADER_CHART_PATH="${LOADER_CHART_PATH:-./helm-loader}"
ORACLE_PASSWORD="${ORACLE_PASSWORD:-}"
DB_READY_TIMEOUT="${DB_READY_TIMEOUT:-900}"  # 15 minutes

# Step Control Variables (set to false to skip steps)
INSTALL_DB="${INSTALL_DB:-true}"
WAIT_FOR_DB="${WAIT_FOR_DB:-true}"
INSTALL_LOADER="${INSTALL_LOADER:-true}"
VERIFY_SYSTEM_ACCESS="${VERIFY_SYSTEM_ACCESS:-true}"
ENABLE_JOB="${ENABLE_JOB:-true}"
MONITOR_JOB="${MONITOR_JOB:-true}"
VERIFY_DATA="${VERIFY_DATA:-true}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if oc is available
    if ! command -v oc &> /dev/null; then
        log_error "OpenShift CLI (oc) is not installed or not in PATH"
        exit 1
    fi
    
    # Check if helm is available
    if ! command -v helm &> /dev/null; then
        log_error "Helm is not installed or not in PATH"
        exit 1
    fi
    
    # Check if logged into OpenShift
    if ! oc whoami &> /dev/null; then
        log_error "Not logged into OpenShift. Please run 'oc login' first"
        exit 1
    fi
    
    # Check if Helm charts exist
    if [[ ! -d "$DB_CHART_PATH" ]]; then
        log_error "DB Helm chart not found at: $DB_CHART_PATH"
        exit 1
    fi
    
    if [[ ! -d "$LOADER_CHART_PATH" ]]; then
        log_error "Loader Helm chart not found at: $LOADER_CHART_PATH"
        exit 1
    fi
    
    # Check for optional sqlplus
    if command -v sqlplus &> /dev/null; then
        log_info "Oracle SQL*Plus client detected - enhanced connectivity testing available"
    else
        log_warning "Oracle SQL*Plus client not found - will use pod-based connectivity testing"
    fi
    
    log_success "Prerequisites check passed"
}

# Clean up any existing SCCs that might conflict
cleanup_existing_scc() {
    log_info "🧹 Checking for existing Oracle SCCs that might conflict..."
    
    if oc get scc oracle23ai-scc &> /dev/null; then
        log_warning "Found existing oracle23ai-scc, removing to avoid conflicts..."
        oc delete scc oracle23ai-scc
        log_success "✅ Removed conflicting SCC"
    else
        log_info "✅ No conflicting SCCs found"
    fi
}

# Create or switch to namespace
setup_namespace() {
    log_info "Setting up namespace: $NAMESPACE"
    
    # Clean up any conflicting SCCs first
    cleanup_existing_scc
    
    if oc get namespace "$NAMESPACE" &> /dev/null; then
        log_warning "Namespace $NAMESPACE already exists"
    else
        oc create namespace "$NAMESPACE"
        log_success "Created namespace: $NAMESPACE"
    fi
    
    # Switch to the namespace
    oc project "$NAMESPACE"
    log_success "Switched to namespace: $NAMESPACE"
}

# Generate secure password if not provided
generate_password() {
    if [[ -z "$ORACLE_PASSWORD" ]]; then
        ORACLE_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
        log_info "Generated secure password for Oracle database"
        export ORACLE_PASSWORD
    else
        log_info "Using provided Oracle password"
    fi
}

# Install Oracle 23AI Database using helm-db chart
install_oracle_db() {
    log_info "Installing Oracle 23AI Database using helm-db chart..."
    
    # Prepare Helm values for DB-only installation
    local helm_args=(
        "$DB_RELEASE_NAME"
        "$DB_CHART_PATH"
        "--namespace" "$NAMESPACE"
        "--create-namespace"
        "--set" "securityContextConstraint.create=true"
        "--set" "installDB=true"
        "--set" "probes.readiness.initialDelaySeconds=180"
        "--set" "probes.readiness.periodSeconds=60"
        "--set" "probes.liveness.initialDelaySeconds=300"
        "--set" "probes.liveness.periodSeconds=120"
    )
    
    # Add password if provided
    if [[ -n "$ORACLE_PASSWORD" ]]; then
        helm_args+=("--set" "secret.password=$ORACLE_PASSWORD")
    fi
    
    # Install or upgrade
    if helm list -n "$NAMESPACE" | grep -q "$DB_RELEASE_NAME"; then
        log_warning "Release $DB_RELEASE_NAME already exists. Upgrading..."
        helm upgrade "${helm_args[@]}"
    else
        helm install "${helm_args[@]}"
    fi
    
    log_success "Oracle 23AI Database installation initiated"
}

# Verify password security and accessibility
verify_password_security() {
    log_info "🔐 Verifying password security and accessibility..."
    
    local db_password="$1"
    
    # Check password strength
    if [[ ${#db_password} -lt 8 ]]; then
        log_warning "⚠️  Password is shorter than 8 characters - may not meet Oracle requirements"
    else
        log_success "✅ Password length is adequate (${#db_password} characters)"
    fi
    
    # Check for shell-breaking characters
    if echo "$db_password" | grep -q '[`$\\]'; then
        log_warning "⚠️  Password contains shell special characters - encoding for safety"
        # URL encode problematic characters for safer handling
        db_password=$(echo "$db_password" | sed 's/\$/\%24/g; s/`/\%60/g; s/\\/\%5C/g')
    fi
    
    # Test base64 encoding/decoding (used by Kubernetes secrets)
    local encoded_test=$(echo "$db_password" | base64)
    local decoded_test=$(echo "$encoded_test" | base64 -d)
    
    if [[ "$db_password" != "$decoded_test" ]]; then
        log_error "❌ Password base64 encoding/decoding failed - this will cause connection issues"
        return 1
    fi
    
    log_success "✅ Password encoding verification passed"
    return 0
}

# Wait for Oracle database to be ready
wait_for_oracle_ready() {
    log_info "Waiting for Oracle database to be ready for connections..."
    
    # Step 1: Wait for secret to be created (uses chart name, not release name)
    local secret_name="oracle23ai"  # From helm-db fullnameOverride
    log_info "⏳ Waiting for Oracle secret to be created..."
    local elapsed=0
    local db_password
    while [[ $elapsed -lt 60 ]]; do
        if oc get secret "$secret_name" -n "$NAMESPACE" &> /dev/null; then
            db_password=$(oc get secret "$secret_name" -n "$NAMESPACE" -o jsonpath='{.data.password}' | base64 -d)
            log_success "✅ Oracle secret found"
            break
        fi
        log_info "   Secret not yet created... (${elapsed}s)"
        sleep 5
        elapsed=$((elapsed + 5))
    done
    
    if [[ -z "${db_password:-}" ]]; then
        log_error "Could not retrieve database password from secret"
        return 1
    fi
    
    # Verify password security
    if ! verify_password_security "$db_password"; then
        log_error "Password security verification failed"
        return 1
    fi
    
    # Step 2: Wait for pod to be ready
    log_info "⏳ Waiting for Oracle pod to be ready..."
    log_info "   This may take 5-10 minutes for Oracle database initialization..."
    
    if oc wait --for=condition=Ready pod "oracle23ai-0" -n "$NAMESPACE" --timeout="${DB_READY_TIMEOUT}s"; then
        log_success "✅ Oracle pod is ready!"
    else
        log_error "❌ Oracle pod failed to become ready within ${DB_READY_TIMEOUT}s"
        return 1
    fi
    
    # Step 3: Verify database connectivity
    log_info "⏳ Verifying Oracle database connectivity..."
    
    # Use oc exec for more reliable database connectivity test
    log_info "   Using oc exec for database connectivity test..."
    
    local max_attempts=5
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        log_info "   Connection attempt ${attempt}/${max_attempts}..."
        
        # Test SYSTEM user connection to FREEPDB1
        local conn_result
        conn_result=$(oc exec "oracle23ai-0" -n "$NAMESPACE" -- bash -c "echo 'SELECT 1 FROM DUAL;' | sqlplus -s system/\"${db_password}\"@localhost:1521/FREEPDB1" 2>/dev/null || echo "FAILED")
        
        if echo "$conn_result" | grep -q "1"; then
            log_success "✅ Oracle database is ready and accepting connections!"
            return 0
        elif echo "$conn_result" | grep -q "ORA-"; then
            log_info "   Oracle responding but not fully ready yet..."
        else
            log_info "   Database not ready yet, waiting 15s before retry..."
        fi
        
        sleep 15
        attempt=$((attempt + 1))
    done
    
    log_error "❌ Oracle database not accepting connections after ${max_attempts} attempts"
    return 1
}

# Get Oracle password from secret (shared function)
get_oracle_password() {
    local db_password
    if oc get secret "oracle23ai" -n "$NAMESPACE" &> /dev/null; then
        db_password=$(oc get secret "oracle23ai" -n "$NAMESPACE" -o jsonpath='{.data.password}' | base64 -d 2>/dev/null)
        if [[ -n "$db_password" ]]; then
            echo "$db_password"
        else
            echo "$ORACLE_PASSWORD"
        fi
    else
        echo "$ORACLE_PASSWORD"
    fi
}

# Verify SYSTEM user access for TPC-DS operations
verify_system_user_access() {
    log_info "👤 Verifying SYSTEM user access for TPC-DS operations..."
    
    # Get Oracle system password using shared function
    local db_password
    db_password=$(get_oracle_password)
    
    if [[ -z "$db_password" ]]; then
        log_error "❌ Oracle system password not found"
        return 1
    fi
    
    log_info "📋 Retrieved Oracle system password from secret (length: ${#db_password})"
    
    # Test SYSTEM user connection to FREEPDB1 with retry logic
    log_info "🔐 Testing SYSTEM user connection to FREEPDB1..."
    
    local max_attempts=3
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        log_info "   SYSTEM access attempt ${attempt}/${max_attempts}..."
        
        # Test the connection with detailed error output for debugging
        local conn_result
        conn_result=$(oc exec oracle23ai-0 -n "$NAMESPACE" -- bash -c "
        echo \"SELECT 'SYSTEM_ACCESS_TEST: ' || USER || ' in ' || SYS_CONTEXT('USERENV','CON_NAME') FROM DUAL;\" | sqlplus -s system/\"${db_password}\"@localhost:1521/FREEPDB1
        " 2>&1 || echo "EXEC_FAILED")
        
        if echo "$conn_result" | grep -q "SYSTEM_ACCESS_TEST.*SYSTEM.*FREEPDB1"; then
            log_success "✅ SYSTEM user has access to FREEPDB1 for TPC-DS operations"
            return 0
        elif echo "$conn_result" | grep -q "ORA-12154"; then
            log_info "   TNS alias not ready yet, waiting 15s before retry..."
        else
            log_info "   Connection not ready yet, waiting 15s before retry..."
        fi
        
        if [[ $attempt -lt $max_attempts ]]; then
            sleep 15
        fi
        attempt=$((attempt + 1))
    done
    
    log_error "❌ SYSTEM user cannot access FREEPDB1 after ${max_attempts} attempts"
    return 1
}

# Verify TPC-DS data loading with actual row counts
verify_tpcds_data_loading() {
    log_info "🔍 Verifying TPC-DS data loading with actual row counts..."
    
    # First, wait for the TPC-DS job to complete
    local job_name="oracle23ai-tpcds-populate"
    local max_wait=1800  # 30 minutes maximum for data loading
    local elapsed=0
    
    log_info "⏳ Waiting for TPC-DS job to complete..."
    while [[ $elapsed -lt $max_wait ]]; do
        # Check job completion status using a more reliable method
        local job_succeeded
        local job_failed
        job_succeeded=$(oc get job "$job_name" -n "$NAMESPACE" -o jsonpath='{.status.succeeded}' 2>/dev/null || echo "0")
        job_failed=$(oc get job "$job_name" -n "$NAMESPACE" -o jsonpath='{.status.failed}' 2>/dev/null || echo "0")
        
        if [[ "$job_succeeded" == "1" ]]; then
            log_success "✅ TPC-DS job completed successfully"
            break
        elif [[ "$job_failed" -gt "0" ]]; then
            log_error "❌ TPC-DS job failed"
            log_info "Job logs:"
            oc logs job/"$job_name" -n "$NAMESPACE" --tail=20
            return 1
        else
            log_info "   Job still running... (${elapsed}s elapsed, succeeded: $job_succeeded, failed: $job_failed)"
            sleep 30
            elapsed=$((elapsed + 30))
        fi
    done
    
    if [[ $elapsed -ge $max_wait ]]; then
        log_error "❌ TPC-DS job did not complete within ${max_wait}s"
        return 1
    fi
    
    # Get Oracle system password using shared function
    local db_password
    db_password=$(get_oracle_password)
    
    if [[ -z "$db_password" ]]; then
        log_error "❌ Oracle system password not found"
        return 1
    fi
    
    # Test actual data with COUNT(*) queries
    log_info "📊 Checking actual data in key TPC-DS tables..."
    
    local verification_result
    verification_result=$(oc exec oracle23ai-0 -n "$NAMESPACE" -- bash -c "
    echo \"SELECT table_name || ': ' || row_count as summary FROM (
    SELECT 'CUSTOMER' as table_name, COUNT(*) as row_count FROM SYSTEM.CUSTOMER
    UNION ALL SELECT 'ITEM', COUNT(*) FROM SYSTEM.ITEM  
    UNION ALL SELECT 'STORE', COUNT(*) FROM SYSTEM.STORE
    UNION ALL SELECT 'STORE_SALES', COUNT(*) FROM SYSTEM.STORE_SALES
    UNION ALL SELECT 'CATALOG_SALES', COUNT(*) FROM SYSTEM.CATALOG_SALES
    ) ORDER BY table_name;\" | sqlplus -s system/\"${db_password}\"@localhost:1521/FREEPDB1
    " 2>/dev/null)
    
    if echo "$verification_result" | grep -q "CUSTOMER: [1-9]"; then
        log_success "✅ TPC-DS data verification successful:"
        echo "$verification_result" | grep ": [0-9]" | sed 's/^/    /'
        return 0
    else
        log_error "❌ TPC-DS data verification failed - no data found in tables"
        log_info "Raw verification output:"
        echo "$verification_result"
        return 1
    fi
}

# Verify loader can access DB password before installation
verify_loader_password_access() {
    log_info "🔑 Verifying loader can access database password..."
    
    local secret_name="oracle23ai"  # From helm-db fullnameOverride
    
    # Check that DB secret exists and is accessible
    if ! oc get secret "$secret_name" -n "$NAMESPACE" &> /dev/null; then
        log_error "❌ Database secret '$secret_name' not found in namespace '$NAMESPACE'"
        return 1
    fi
    
    # Test password extraction using shared function
    local db_password
    db_password=$(get_oracle_password)
    
    if [[ -z "$db_password" ]]; then
        log_error "❌ Could not extract password from database secret"
        return 1
    fi
    
    log_success "✅ Loader can access database password (length: ${#db_password})"
    
    # Verify helm-loader chart can template with the secret reference
    log_info "🧪 Testing helm-loader chart templating with secret reference..."
    
    if helm template test-loader "$LOADER_CHART_PATH" \
        --namespace "$NAMESPACE" \
        --set "database.host=oracle23ai" \
        --set "database.existingSecret=oracle23ai" \
        --set "job.enabled=true" > /dev/null 2>&1; then
        log_success "✅ Helm-loader chart templates successfully with secret reference"
    else
        log_error "❌ Helm-loader chart templating failed"
        return 1
    fi
    
    return 0
}

# Install TPC-DS data loader using helm-loader chart
install_tpcds_loader() {
    log_info "Installing TPC-DS data loader using helm-loader chart..."
    
    # Verify password access before installation
    if ! verify_loader_password_access; then
        log_error "Loader password access verification failed"
        return 1
    fi
    
    # Prepare Helm values for loader (job disabled initially)
    local helm_args=(
        "$LOADER_RELEASE_NAME"
        "$LOADER_CHART_PATH"
        "--namespace" "$NAMESPACE"
        "--set" "database.host=oracle23ai"
        "--set" "database.existingSecret=oracle23ai"
        "--set" "job.enabled=false"
    )
    
    # Install or upgrade
    if helm list -n "$NAMESPACE" | grep -q "$LOADER_RELEASE_NAME"; then
        log_warning "Release $LOADER_RELEASE_NAME already exists. Upgrading..."
        helm upgrade "${helm_args[@]}"
    else
        helm install "${helm_args[@]}"
    fi
    
    log_success "TPC-DS data loader installation initiated (job disabled)"
}

# Enable TPC-DS job after user creation
enable_tpcds_job() {
    log_info "🚀 Enabling TPC-DS data loading job..."
    
    # Delete existing job if it exists (Jobs are immutable)
    if oc get job "oracle23ai-tpcds-populate" -n "$NAMESPACE" &> /dev/null; then
        log_info "📋 Deleting existing job (Jobs are immutable)..."
        oc delete job "oracle23ai-tpcds-populate" -n "$NAMESPACE"
    fi
    
    # Upgrade helm release to enable the job
    local helm_args=(
        "$LOADER_RELEASE_NAME"
        "$LOADER_CHART_PATH"
        "--namespace" "$NAMESPACE"
        "--set" "database.host=oracle23ai"
        "--set" "database.existingSecret=oracle23ai"
        "--set" "job.enabled=true"
    )
    
    helm upgrade "${helm_args[@]}"
    log_success "✅ TPC-DS job enabled and started"
}

# Monitor TPC-DS data loading job
monitor_data_loading() {
    log_info "Monitoring TPC-DS data loading job..."
    
    # Wait for job to be created (job name is from chart fullname, not release name)
    local job_name="oracle23ai-tpcds-populate"
    local elapsed=0
    while [[ $elapsed -lt 60 ]]; do
        if oc get job "$job_name" -n "$NAMESPACE" &> /dev/null; then
            log_success "TPC-DS data loading job found: $job_name"
            break
        fi
        log_info "   Waiting for job to be created... (${elapsed}s)"
        sleep 5
        elapsed=$((elapsed + 5))
    done
    
    if ! oc get job "$job_name" -n "$NAMESPACE" &> /dev/null; then
        log_error "TPC-DS job not found after 60 seconds"
        return 1
    fi
    
    # Show monitoring commands
    log_info "TPC-DS data loading in progress..."
    log_info "Monitor progress with:"
    echo "  oc logs -f job/$job_name -n $NAMESPACE"
    echo "  oc get jobs -n $NAMESPACE"
    
    # Show initial status
    oc get jobs -n "$NAMESPACE" | grep tpcds || true
}

# Display connection information
display_connection_info() {
    log_info "Gathering connection information..."
    
    # Get service information
    local service_name="oracle23ai"
    local service_port="1521"
    
    # Get password from secret using shared function
    local db_password
    db_password=$(get_oracle_password)
    
    echo
    echo "=================================="
    echo "Oracle 23AI Database Connection Info"
    echo "=================================="
    echo "Namespace: $NAMESPACE"
    echo "DB Release: $DB_RELEASE_NAME"
    echo "Loader Release: $LOADER_RELEASE_NAME"
    echo "Service: $service_name"
    echo "Port: $service_port"
    echo "SID: FREE"
    echo "Service Name: FREEPDB1"
    echo "Username: system"
    echo "Password: [REDACTED - retrieve with: oc get secret oracle23ai -o jsonpath='{.data.password}' | base64 -d]"
    echo
    echo "Connection String: $service_name:$service_port/FREEPDB1"
    echo
    echo "To connect from within the cluster:"
    echo "  Host: $service_name.$NAMESPACE.svc.cluster.local"
    echo "  Port: $service_port"
    echo
    echo "To access DB logs:"
    echo "  oc logs -f statefulset/oracle23ai -n $NAMESPACE"
    echo
    echo "To monitor TPC-DS data loading:"
    echo "  oc logs -f job/oracle23ai-tpcds-populate -n $NAMESPACE"
    echo "  oc get jobs -n $NAMESPACE"
    echo
    echo "To port-forward for external access:"
    echo "  oc port-forward svc/$service_name $service_port:$service_port -n $NAMESPACE"
    echo "=================================="
}

# Cleanup function
cleanup() {
    if [[ "${1:-}" == "error" ]]; then
        log_error "Installation failed. Check the logs above for details."
        log_info "To clean up partial installation, run:"
        echo "  helm uninstall $DB_RELEASE_NAME -n $NAMESPACE"
        echo "  helm uninstall $LOADER_RELEASE_NAME -n $NAMESPACE"
        echo "  oc delete scc oracle23ai-scc"
        echo "  oc delete namespace $NAMESPACE"
    fi
}

# Main installation function
main() {
    log_info "Starting Oracle 23AI sequential installation (DB + Loader)..."
    
    # Set up error handling
    trap 'cleanup error' ERR
    
    # Run installation steps
    check_prerequisites
    setup_namespace
    generate_password
    
    # Step 1: Install Oracle Database
    if [[ "$INSTALL_DB" == "true" ]]; then
        log_info "🚀 Step 1: Installing Oracle Database..."
        install_oracle_db
    else
        log_warning "⏭️  Skipping Oracle Database installation (INSTALL_DB=false)"
    fi
    
    if [[ "$WAIT_FOR_DB" == "true" ]]; then
        log_info "⏳ Step 2: Waiting for Oracle Database to be ready..."
        wait_for_oracle_ready
    else
        log_warning "⏭️  Skipping Oracle Database readiness check (WAIT_FOR_DB=false)"
    fi
    
    # Step 2: Install TPC-DS Loader (creates secrets, job disabled)
    if [[ "$INSTALL_LOADER" == "true" ]]; then
        log_info "📦 Step 3: Installing TPC-DS Loader..."
        install_tpcds_loader
    else
        log_warning "⏭️  Skipping TPC-DS Loader installation (INSTALL_LOADER=false)"
    fi
    
    # Step 3: Verify SYSTEM user access for TPC-DS operations (with stabilization delay)
    if [[ "$VERIFY_SYSTEM_ACCESS" == "true" ]]; then
        log_info "👤 Step 4: Verifying SYSTEM user access for TPC-DS operations..."
        log_info "⏳ Allowing 10s for database to stabilize after initial connection test..."
        sleep 10
        verify_system_user_access
    else
        log_warning "⏭️  Skipping SYSTEM user access verification (VERIFY_SYSTEM_ACCESS=false)"
    fi
    
    # Step 4: Enable TPC-DS job and monitor
    if [[ "$ENABLE_JOB" == "true" ]]; then
        log_info "🚀 Step 5: Enabling TPC-DS job..."
        enable_tpcds_job
    else
        log_warning "⏭️  Skipping TPC-DS job enablement (ENABLE_JOB=false)"
    fi
    
    if [[ "$MONITOR_JOB" == "true" ]]; then
        log_info "📊 Step 6: Monitoring data loading..."
        monitor_data_loading
    else
        log_warning "⏭️  Skipping job monitoring (MONITOR_JOB=false)"
    fi
    
    # Step 7: Verify TPC-DS data loading
    if [[ "$VERIFY_DATA" == "true" ]]; then
        log_info "🔍 Step 7: Verifying TPC-DS data loading..."
        verify_tpcds_data_loading
    else
        log_warning "⏭️  Skipping data verification (VERIFY_DATA=false)"
    fi
    
    display_connection_info
    
    log_success "Oracle 23AI sequential installation completed successfully!"
    log_info "Database is ready, TPC-DS data loading is in progress"
    
    # Clean up trap
    trap - ERR
}

# Help function
show_help() {
    cat << EOF
Oracle 23AI Sequential Installation Script

This script installs Oracle DB and TPC-DS data loader sequentially using separate charts.

Usage: $0 [OPTIONS]

Options:
  -h, --help              Show this help message
  -n, --namespace NAME    Kubernetes namespace (default: oracle23ai)
  --db-release NAME       DB Helm release name (default: oracle23ai-db)
  --loader-release NAME   Loader Helm release name (default: oracle23ai-loader)
  --db-chart PATH         Path to DB Helm chart (default: ./helm-db)
  --loader-chart PATH     Path to Loader Helm chart (default: ./helm-loader)
  -p, --password PWD      Oracle database password (auto-generated if not provided)
  --timeout SECONDS       DB ready timeout in seconds (default: 900)

Environment Variables:
  NAMESPACE              Kubernetes namespace
  DB_RELEASE_NAME        DB Helm release name
  LOADER_RELEASE_NAME    Loader Helm release name
  DB_CHART_PATH          Path to DB Helm chart
  LOADER_CHART_PATH      Path to Loader Helm chart
  ORACLE_PASSWORD        Oracle database password
  DB_READY_TIMEOUT       Database ready timeout in seconds

Step Control Variables (set to false to skip steps):
  INSTALL_DB             Install Oracle Database (default: true)
  WAIT_FOR_DB            Wait for Oracle Database readiness (default: true)
  INSTALL_LOADER         Install TPC-DS Loader (default: true)
  VERIFY_SYSTEM_ACCESS   Verify SYSTEM user access for TPC-DS (default: true)
  ENABLE_JOB             Enable TPC-DS data loading job (default: true)
  MONITOR_JOB            Monitor job progress (default: true)
  VERIFY_DATA            Verify TPC-DS data loading with COUNT(*) (default: true)

Examples:
  $0                                    # Install with defaults
  $0 -n my-oracle                      # Custom namespace
  $0 -p "MySecurePassword123!"         # With custom password
  $0 --timeout 1200                    # Wait up to 20 minutes for DB ready

Resume Installation Examples:
  INSTALL_DB=false WAIT_FOR_DB=false $0                           # Skip DB steps, start from loader
  INSTALL_DB=false WAIT_FOR_DB=false INSTALL_LOADER=false $0      # Skip to system verification
  VERIFY_SYSTEM_ACCESS=false ENABLE_JOB=false MONITOR_JOB=false $0 # Install only DB and loader
  MONITOR_JOB=false $0                                            # Skip monitoring at the end

Prerequisites:
  - OpenShift CLI (oc) - Required
  - Helm 3.x - Required  
  - Oracle SQL*Plus - Optional but recommended for better connectivity testing

Installation Process:
  1. Install Oracle 23AI Database using helm-db chart
  2. Wait for Oracle to be ready using connectivity tests
  3. Install TPC-DS data loader using helm-loader chart
  4. Verify SYSTEM user access for TPC-DS operations
  5. Enable and monitor TPC-DS data loading job
  6. Verify TPC-DS data loading with actual row counts
  7. Display connection information

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        --db-release)
            DB_RELEASE_NAME="$2"
            shift 2
            ;;
        --loader-release)
            LOADER_RELEASE_NAME="$2"
            shift 2
            ;;
        --db-chart)
            DB_CHART_PATH="$2"
            shift 2
            ;;
        --loader-chart)
            LOADER_CHART_PATH="$2"
            shift 2
            ;;
        -p|--password)
            ORACLE_PASSWORD="$2"
            shift 2
            ;;
        --timeout)
            DB_READY_TIMEOUT="$2"
            shift 2
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Run main function
main "$@"