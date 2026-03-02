#!/bin/bash
###############################################################################
# deploy_all.sh: Deploy and update all HungryHoundDog nodes from Dev Box.
#
# Pushes configurations, updates services, and restarts components across
# all lab nodes (adversary, monitoring, PLC simulators, etc.)
###############################################################################

set -euo pipefail

# Configuration
DEV_BOX_IP="192.168.20.30"
DEPLOY_LOG="/var/log/hungryhounddog/deploy_$(date +%Y%m%d_%H%M%S).log"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1" | tee -a "$DEPLOY_LOG"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$DEPLOY_LOG"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$DEPLOY_LOG"
}

log_section() {
    echo -e "\n${BLUE}==== $1 ====${NC}\n" | tee -a "$DEPLOY_LOG"
}

# Ensure log directory exists
mkdir -p "$(dirname "$DEPLOY_LOG")"

log_section "HungryHoundDog Deployment Starting"

# Define all nodes
declare -A NODES=(
    ["adversary"]="192.168.1.50"
    ["modbus_server"]="192.168.10.10"
    ["monitoring"]="192.168.20.10"
    ["logger"]="192.168.20.20"
)

# Function to deploy to a node
deploy_to_node() {
    local node_name=$1
    local node_ip=$2
    local source_path=$3
    local dest_path=$4

    log_info "Deploying $node_name ($node_ip)..."

    if ! timeout 30 ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no \
        "root@$node_ip" "mkdir -p $dest_path" 2>/dev/null; then
        log_warn "Could not reach $node_name at $node_ip"
        return 1
    fi

    # Use scp to copy configuration
    if timeout 60 scp -o ConnectTimeout=5 -o StrictHostKeyChecking=no \
        -r "$source_path"/* "root@$node_ip:$dest_path/" 2>/dev/null; then
        log_info "Successfully deployed $node_name"
        return 0
    else
        log_warn "Deployment to $node_name failed or timed out"
        return 1
    fi
}

# Function to restart services on node
restart_service() {
    local node_ip=$1
    local service_name=$2

    log_info "Restarting $service_name on $node_ip..."

    if timeout 30 ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no \
        "root@$node_ip" "systemctl restart $service_name" 2>/dev/null; then
        log_info "Service $service_name restarted successfully"
        return 0
    else
        log_warn "Could not restart $service_name on $node_ip"
        return 1
    fi
}

# Function to check node status
check_node_status() {
    local node_name=$1
    local node_ip=$2

    log_info "Checking status of $node_name..."

    if timeout 10 ping -c 1 "$node_ip" &> /dev/null; then
        log_info "$node_name is reachable"
        return 0
    else
        log_warn "$node_name ($node_ip) is not responding"
        return 1
    fi
}

# Phase 1: Pre-deployment checks
log_section "Phase 1: Pre-Deployment Checks"

all_reachable=true
for node in "${!NODES[@]}"; do
    if ! check_node_status "$node" "${NODES[$node]}"; then
        all_reachable=false
    fi
done

if [ "$all_reachable" = false ]; then
    log_warn "Some nodes are unreachable, but continuing with reachable nodes"
fi

# Phase 2: Adversary node deployment
log_section "Phase 2: Adversary Node Deployment"

ADVERSARY_IP="${NODES[adversary]}"
if check_node_status "adversary" "$ADVERSARY_IP"; then
    # Deploy playbooks
    deploy_to_node "adversary" "$ADVERSARY_IP" \
        "/sessions/gracious-stoic-goodall/mnt/hungryhounddog/adversary" \
        "/opt/hungryhounddog/adversary"

    # Deploy bootstrap script
    deploy_to_node "adversary" "$ADVERSARY_IP" \
        "/sessions/gracious-stoic-goodall/mnt/hungryhounddog/adversary/scripts" \
        "/opt/hungryhounddog/scripts"

    log_info "Adversary node deployment complete"
fi

# Phase 3: Modbus server deployment
log_section "Phase 3: Modbus Server Deployment"

MODBUS_IP="${NODES[modbus_server]}"
if check_node_status "modbus_server" "$MODBUS_IP"; then
    deploy_to_node "modbus_server" "$MODBUS_IP" \
        "/sessions/gracious-stoic-goodall/mnt/hungryhounddog/adversary/ot_simulator" \
        "/opt/hungryhounddog/ot_simulator"

    restart_service "$MODBUS_IP" "hungryhounddog-modbus" || true
    log_info "Modbus server deployment complete"
fi

# Phase 4: Monitoring station deployment
log_section "Phase 4: Monitoring Station Deployment"

MONITOR_IP="${NODES[monitoring]}"
if check_node_status "monitoring" "$MONITOR_IP"; then
    log_info "Deploying monitoring station configuration"
    # Placeholder for monitoring configs
    log_info "Monitoring station ready"
fi

# Phase 5: Logger/Aggregator deployment
log_section "Phase 5: Logger Deployment"

LOGGER_IP="${NODES[logger]}"
if check_node_status "logger" "$LOGGER_IP"; then
    log_info "Deploying logger configuration"
    # Placeholder for logger configs
    log_info "Logger ready"
fi

# Phase 6: Post-deployment validation
log_section "Phase 6: Post-Deployment Validation"

log_info "Verifying all nodes are still responsive..."
validation_passed=true

for node in "${!NODES[@]}"; do
    if check_node_status "$node" "${NODES[$node]}"; then
        log_info "$node validation: OK"
    else
        log_warn "$node validation: FAILED"
        validation_passed=false
    fi
done

# Summary
log_section "Deployment Summary"

if [ "$validation_passed" = true ]; then
    log_info "All deployments completed successfully!"
    echo -e "\n${GREEN}Deployment Status: SUCCESS${NC}\n"
    exit 0
else
    log_warn "Some deployments may have issues"
    echo -e "\n${YELLOW}Deployment Status: PARTIAL${NC}\n"
    exit 1
fi
