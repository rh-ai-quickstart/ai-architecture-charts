#!/bin/bash

# Oracle 23AI Uninstall Script
# This script removes Oracle DB and TPC-DS data loader deployments
# Default behavior: Deletes the entire namespace for complete cleanup
# 
# Prerequisites:
# - oc (OpenShift CLI)
# - helm (Helm 3.x)

set -euo pipefail

# Configuration
NAMESPACE="${NAMESPACE:-oracle23ai}"
DB_RELEASE_NAME="${DB_RELEASE_NAME:-oracle23ai-db}"
LOADER_RELEASE_NAME="${LOADER_RELEASE_NAME:-oracle23ai-loader}"

# Uninstall options (set to false to skip)
DELETE_NAMESPACE="${DELETE_NAMESPACE:-true}"
REMOVE_SCC="${REMOVE_SCC:-true}"
WAIT_FOR_DELETION="${WAIT_FOR_DELETION:-true}"

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
    
    log_success "Prerequisites check passed"
}

# Check if namespace exists
check_namespace() {
    if ! oc get namespace "$NAMESPACE" &> /dev/null; then
        log_warning "Namespace '$NAMESPACE' does not exist"
        log_info "Nothing to uninstall"
        exit 0
    fi
    log_info "Found namespace: $NAMESPACE"
}

# Uninstall Helm releases
uninstall_helm_releases() {
    log_info "🗑️  Checking for Helm releases to uninstall..."
    
    # Check and uninstall loader release
    if helm list -n "$NAMESPACE" | grep -q "$LOADER_RELEASE_NAME"; then
        log_info "Uninstalling loader release: $LOADER_RELEASE_NAME"
        if helm uninstall "$LOADER_RELEASE_NAME" -n "$NAMESPACE"; then
            log_success "Uninstalled loader release: $LOADER_RELEASE_NAME"
        else
            log_error "Failed to uninstall loader release: $LOADER_RELEASE_NAME"
        fi
    else
        log_info "Loader release '$LOADER_RELEASE_NAME' not found"
    fi
    
    # Check and uninstall database release
    if helm list -n "$NAMESPACE" | grep -q "$DB_RELEASE_NAME"; then
        log_info "Uninstalling database release: $DB_RELEASE_NAME"
        if helm uninstall "$DB_RELEASE_NAME" -n "$NAMESPACE"; then
            log_success "Uninstalled database release: $DB_RELEASE_NAME"
        else
            log_error "Failed to uninstall database release: $DB_RELEASE_NAME"
        fi
    else
        log_info "Database release '$DB_RELEASE_NAME' not found"
    fi
}

# Wait for pods to terminate
wait_for_pod_deletion() {
    if [[ "$WAIT_FOR_DELETION" != "true" ]]; then
        return 0
    fi
    
    log_info "⏳ Waiting for pods to terminate..."
    
    local timeout=300  # 5 minutes
    local elapsed=0
    local interval=5
    
    while [[ $elapsed -lt $timeout ]]; do
        local pod_count
        pod_count=$(oc get pods -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l || echo "0")
        
        if [[ "$pod_count" -eq 0 ]]; then
            log_success "All pods terminated"
            return 0
        fi
        
        log_info "Waiting for $pod_count pods to terminate... (${elapsed}s/${timeout}s)"
        sleep $interval
        elapsed=$((elapsed + interval))
    done
    
    log_warning "Timeout waiting for pods to terminate. Proceeding with namespace deletion..."
    oc get pods -n "$NAMESPACE" || true
}

# Delete namespace
delete_namespace() {
    if [[ "$DELETE_NAMESPACE" != "true" ]]; then
        log_info "Skipping namespace deletion (DELETE_NAMESPACE=false)"
        return 0
    fi
    
    log_info "🗑️  Deleting namespace: $NAMESPACE"
    log_warning "This will remove ALL resources in the namespace including:"
    log_warning "  - PersistentVolumeClaims (data will be lost)"
    log_warning "  - Secrets and ConfigMaps"
    log_warning "  - Services and Deployments"
    log_warning "  - Jobs and StatefulSets"
    
    if oc delete namespace "$NAMESPACE" --timeout=300s; then
        log_success "Deleted namespace: $NAMESPACE"
    else
        log_error "Failed to delete namespace: $NAMESPACE"
        log_info "You may need to manually clean up remaining resources"
        return 1
    fi
}

# Remove Oracle SCC if no other Oracle deployments exist
remove_oracle_scc() {
    if [[ "$REMOVE_SCC" != "true" ]]; then
        log_info "Skipping SCC removal (REMOVE_SCC=false)"
        return 0
    fi
    
    local scc_name="oracle-scc"
    
    if ! oc get scc "$scc_name" &> /dev/null; then
        log_info "Oracle SCC '$scc_name' not found"
        return 0
    fi
    
    log_info "🔍 Checking if Oracle SCC is used by other deployments..."
    
    # Check if any other namespaces have oracle-related service accounts using this SCC
    local other_usage
    other_usage=$(oc get clusterrolebindings -o json | jq -r '.items[] | select(.subjects[]?.name | test("oracle")) | .metadata.name' 2>/dev/null || echo "")
    
    if [[ -z "$other_usage" ]]; then
        log_info "🗑️  Removing Oracle SCC: $scc_name"
        if oc delete scc "$scc_name"; then
            log_success "Removed Oracle SCC: $scc_name"
        else
            log_warning "Failed to remove Oracle SCC: $scc_name (may not have permissions)"
        fi
    else
        log_warning "Oracle SCC '$scc_name' is still in use by other deployments:"
        echo "$other_usage"
        log_info "Skipping SCC removal to avoid affecting other Oracle deployments"
    fi
}

# Display cleanup summary
display_summary() {
    log_info "📊 Uninstall Summary:"
    echo "  Namespace: $NAMESPACE"
    echo "  DB Release: $DB_RELEASE_NAME"
    echo "  Loader Release: $LOADER_RELEASE_NAME"
    echo ""
    
    if [[ "$DELETE_NAMESPACE" == "true" ]]; then
        log_success "✅ Complete cleanup: Namespace and all resources removed"
    else
        log_info "ℹ️  Partial cleanup: Helm releases removed, namespace preserved"
        echo ""
        log_info "To manually remove remaining resources:"
        echo "  oc delete namespace $NAMESPACE"
    fi
    
    if [[ "$REMOVE_SCC" == "true" ]]; then
        log_info "🔒 Oracle SCC cleanup attempted"
    fi
}

# Show help
show_help() {
    cat << EOF
Oracle 23AI Uninstall Script

USAGE:
  ./uninstall.sh [OPTIONS]

OPTIONS:
  -h, --help              Show this help message
  -n, --namespace NAME    Kubernetes namespace (default: oracle23ai)
  --db-release NAME       DB Helm release name (default: oracle23ai-db)
  --loader-release NAME   Loader Helm release name (default: oracle23ai-loader)
  --keep-namespace        Don't delete namespace (only remove Helm releases)
  --keep-scc              Don't remove Oracle SCC
  --no-wait               Don't wait for pod deletion

ENVIRONMENT VARIABLES:
  NAMESPACE              Kubernetes namespace
  DB_RELEASE_NAME        DB Helm release name
  LOADER_RELEASE_NAME    Loader Helm release name
  DELETE_NAMESPACE       Delete namespace (default: true)
  REMOVE_SCC             Remove Oracle SCC (default: true)
  WAIT_FOR_DELETION      Wait for pods to terminate (default: true)

EXAMPLES:
  # Complete cleanup (default - removes everything)
  ./uninstall.sh

  # Keep namespace, only remove Helm releases
  ./uninstall.sh --keep-namespace

  # Uninstall from custom namespace
  ./uninstall.sh -n my-oracle-namespace

  # Quick uninstall without waiting
  ./uninstall.sh --no-wait

  # Remove only database components
  DB_RELEASE_NAME="my-db" ./uninstall.sh

NOTES:
  - Default behavior deletes the entire namespace for complete cleanup
  - This removes ALL data including PersistentVolumeClaims
  - Oracle SCC is only removed if no other Oracle deployments are detected
  - Use --keep-namespace to preserve other resources in the namespace

EOF
}

# Main execution
main() {
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
            --keep-namespace)
                DELETE_NAMESPACE="false"
                shift
                ;;
            --keep-scc)
                REMOVE_SCC="false"
                shift
                ;;
            --no-wait)
                WAIT_FOR_DELETION="false"
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    log_info "🚀 Starting Oracle 23AI uninstall process..."
    log_info "Target namespace: $NAMESPACE"
    
    check_prerequisites
    check_namespace
    uninstall_helm_releases
    
    if [[ "$DELETE_NAMESPACE" == "true" ]]; then
        wait_for_pod_deletion
        delete_namespace
    fi
    
    remove_oracle_scc
    display_summary
    
    log_success "🎉 Oracle 23AI uninstall completed!"
}

# Run main function with all arguments
main "$@"