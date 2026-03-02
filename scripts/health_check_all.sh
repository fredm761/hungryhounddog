#!/bin/bash
###############################################################################
# health_check_all.sh: Health check all HungryHoundDog lab components.
#
# Verifies connectivity, service status, and key metrics across all nodes:
# - Adversary node
# - Modbus servers
# - Monitoring station
# - Logger/aggregator
# - Network connectivity
###############################################################################

set -euo pipefail

# Configuration
HEALTH_LOG="/var/log/hungryhounddog/health_$(date +%Y%m%d_%H%M%S).json"
TIMEOUT_SSH=10

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Status tracking
declare -A node_status
declare -A service_status

# Logging
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_section() {
    echo -e "\n${BLUE}==== $1 ====${NC}\n"
}

# Ensure log directory exists
mkdir -p "$(dirname "$HEALTH_LOG")"

# Initialize health report
init_health_report() {
    cat > "$HEALTH_LOG" << 'JSONEOF'
{
  "timestamp": "TIMESTAMP",
  "nodes": {},
  "services": {},
  "network": {},
  "summary": {
    "healthy_nodes": 0,
    "unhealthy_nodes": 0,
    "overall_status": "UNKNOWN"
  }
}
JSONEOF

    sed -i "s/TIMESTAMP/$(date -u +%Y-%m-%dT%H:%M:%SZ)/" "$HEALTH_LOG"
}

# Check node connectivity
check_node() {
    local node_name=$1
    local node_ip=$2

    log_info "Checking connectivity: $node_name ($node_ip)"

    if timeout $TIMEOUT_SSH ping -c 1 "$node_ip" &> /dev/null; then
        log_info "✓ $node_name is reachable"
        node_status[$node_name]="UP"
        return 0
    else
        log_warn "✗ $node_name is unreachable"
        node_status[$node_name]="DOWN"
        return 1
    fi
}

# Check SSH connectivity
check_ssh() {
    local node_name=$1
    local node_ip=$2

    if timeout $TIMEOUT_SSH ssh -o ConnectTimeout=3 -o StrictHostKeyChecking=no \
        "root@$node_ip" "echo OK" 2>/dev/null | grep -q "OK"; then
        log_info "✓ SSH access to $node_name OK"
        return 0
    else
        log_warn "✗ SSH access to $node_name failed"
        return 1
    fi
}

# Check service status on remote node
check_service() {
    local node_ip=$1
    local service_name=$2
    local status_key="$service_name"

    local status=$(timeout $TIMEOUT_SSH ssh -o ConnectTimeout=3 -o StrictHostKeyChecking=no \
        "root@$node_ip" "systemctl is-active $service_name" 2>/dev/null || echo "unknown")

    if [ "$status" = "active" ]; then
        log_info "✓ Service $service_name is running"
        service_status["$status_key"]="ACTIVE"
        return 0
    else
        log_warn "✗ Service $service_name status: $status"
        service_status["$status_key"]="INACTIVE"
        return 1
    fi
}

# Check port connectivity
check_port() {
    local node_ip=$1
    local port=$2
    local port_name=$3

    if timeout 5 bash -c "< /dev/null > /dev/tcp/$node_ip/$port" 2>/dev/null; then
        log_info "✓ Port $port ($port_name) is open on $node_ip"
        return 0
    else
        log_warn "✗ Port $port ($port_name) is not responding on $node_ip"
        return 1
    fi
}

# Main health check execution
log_section "HungryHoundDog Health Check"

init_health_report

# Define nodes
declare -A NODES=(
    ["adversary"]="192.168.1.50"
    ["modbus_server"]="192.168.10.10"
    ["monitoring"]="192.168.20.10"
    ["logger"]="192.168.20.20"
)

# Phase 1: Node connectivity
log_section "Phase 1: Node Connectivity"

for node in "${!NODES[@]}"; do
    check_node "$node" "${NODES[$node]}"
done

# Phase 2: SSH connectivity
log_section "Phase 2: SSH Access"

for node in "${!NODES[@]}"; do
    check_ssh "$node" "${NODES[$node]}"
done

# Phase 3: Service status checks
log_section "Phase 3: Service Status"

ADVERSARY_IP="${NODES[adversary]}"
if [ "${node_status[adversary]:-DOWN}" = "UP" ]; then
    log_info "Checking adversary services..."
    check_service "$ADVERSARY_IP" "hungryhounddog-adversary" || true
    check_service "$ADVERSARY_IP" "mosquitto" || true
fi

MODBUS_IP="${NODES[modbus_server]}"
if [ "${node_status[modbus_server]:-DOWN}" = "UP" ]; then
    log_info "Checking Modbus services..."
    check_service "$MODBUS_IP" "hungryhounddog-modbus" || true
    check_service "$MODBUS_IP" "mosquitto" || true
fi

# Phase 4: Port connectivity checks
log_section "Phase 4: Port Connectivity"

# Modbus TCP (502)
if [ "${node_status[modbus_server]:-DOWN}" = "UP" ]; then
    check_port "$MODBUS_IP" 502 "Modbus TCP" || true
fi

# MQTT (1883)
if [ "${node_status[adversary]:-DOWN}" = "UP" ]; then
    check_port "$ADVERSARY_IP" 1883 "MQTT" || true
fi

# Modbus TCP from adversary
if [ "${node_status[adversary]:-DOWN}" = "UP" ]; then
    check_port "$ADVERSARY_IP" 502 "Modbus TCP Adversary" || true
fi

# Phase 5: Modbus connectivity test
log_section "Phase 5: Modbus Protocol Test"

if [ "${node_status[modbus_server]:-DOWN}" = "UP" ]; then
    log_info "Testing Modbus read from adversary..."
    if timeout 10 ssh -o ConnectTimeout=3 -o StrictHostKeyChecking=no \
        "root@$ADVERSARY_IP" \
        "python3 -c \"from pymodbus.client import ModbusTcpClient; c=ModbusTcpClient('$MODBUS_IP', 502); c.connect(); print('Modbus connected')\" " \
        2>/dev/null | grep -q "connected"; then
        log_info "✓ Modbus connectivity test passed"
    else
        log_warn "✗ Modbus connectivity test failed"
    fi
fi

# Phase 6: Network diagnostics
log_section "Phase 6: Network Diagnostics"

log_info "ARP table entries:"
arp -a | wc -l | xargs echo "Total ARP entries:"

log_info "Active network connections summary:"
netstat -an 2>/dev/null | grep ESTABLISHED | wc -l | xargs echo "ESTABLISHED connections:"

# Phase 7: Summary
log_section "Health Check Summary"

healthy_count=0
unhealthy_count=0

for node in "${!NODES[@]}"; do
    if [ "${node_status[$node]:-DOWN}" = "UP" ]; then
        log_info "✓ $node: HEALTHY"
        ((healthy_count++))
    else
        log_warn "✗ $node: UNHEALTHY"
        ((unhealthy_count++))
    fi
done

echo -e "\n${BLUE}Overall Status:${NC}"
echo "  Healthy nodes: $healthy_count/${#NODES[@]}"
echo "  Unhealthy nodes: $unhealthy_count/${#NODES[@]}"

if [ $unhealthy_count -eq 0 ]; then
    echo -e "  ${GREEN}Status: ALL SYSTEMS OPERATIONAL${NC}\n"
    exit 0
elif [ $healthy_count -gt 0 ]; then
    echo -e "  ${YELLOW}Status: PARTIAL OPERATIONAL${NC}\n"
    exit 0
else
    echo -e "  ${RED}Status: CRITICAL - NO SYSTEMS OPERATIONAL${NC}\n"
    exit 1
fi
