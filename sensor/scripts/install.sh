#!/bin/bash
#
# HungryHoundDog Sensor Installation Script
# Raspberry Pi 4 - Suricata IDS Setup
# Last Updated: 2026-02-27
#
# This script installs and configures Suricata IDS, Python agents,
# systemd services, and network settings for the HungryHoundDog sensor node.

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SENSOR_ID="${SENSOR_ID:-sensor-001}"
SENSOR_NAME="${SENSOR_NAME:-RPi4-Sensor-01}"
CAPTURE_INTERFACE="${CAPTURE_INTERFACE:-eth0}"
SENSOR_BASE_DIR="/opt/hungryhounddog"
CONFIG_DIR="/etc/hungryhounddog"
LOG_DIR="/var/log/hungryhounddog"
VAR_LIB_DIR="/var/lib/hungryhounddog"
BRAIN_ENDPOINT="${BRAIN_ENDPOINT:-https://brain.hungryhounddog.local}"

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

# Update system packages
update_system() {
    log_info "Updating system packages..."
    apt-get update -qq
    apt-get upgrade -y -qq
}

# Install system dependencies
install_dependencies() {
    log_info "Installing system dependencies..."
    
    apt-get install -y -qq \
        build-essential \
        libpcre3 libpcre3-dev \
        libpcap-dev \
        libnet1-dev \
        libyaml-dev \
        libcap-ng-dev \
        libcap-ng0 \
        libmagic-dev \
        libjansson-dev \
        libjansson4 \
        automake \
        autoconf \
        libtool \
        pkg-config \
        curl \
        wget \
        git \
        vim \
        htop \
        net-tools \
        ethtool \
        python3 \
        python3-pip \
        python3-dev \
        supervisor
    
    log_info "Dependencies installed successfully"
}

# Install Python dependencies for agents
install_python_dependencies() {
    log_info "Installing Python dependencies for agents..."
    
    pip3 install -q --upgrade pip setuptools wheel
    
    pip3 install -q \
        requests>=2.28.0 \
        pyyaml>=6.0 \
        psutil>=5.9.0
    
    log_info "Python dependencies installed successfully"
}

# Install Suricata from APT
install_suricata() {
    log_info "Installing Suricata IDS..."
    
    # Add Suricata repository
    add-apt-repository -y ppa:oisf/suricata-stable 2>/dev/null || true
    apt-get update -qq
    
    # Install Suricata
    apt-get install -y -qq suricata suricata-update
    
    # Enable Suricata service
    systemctl enable suricata
    log_info "Suricata installed successfully"
}

# Create directory structure
create_directories() {
    log_info "Creating directory structure..."
    
    mkdir -p "${CONFIG_DIR}/agent"
    mkdir -p "${CONFIG_DIR}/certs"
    mkdir -p "${LOG_DIR}"
    mkdir -p "${VAR_LIB_DIR}"
    mkdir -p "${SENSOR_BASE_DIR}/agent"
    mkdir -p "${SENSOR_BASE_DIR}/scripts"
    
    # Set permissions
    chmod 755 "${CONFIG_DIR}"
    chmod 700 "${CONFIG_DIR}/certs"
    chmod 755 "${LOG_DIR}"
    chmod 755 "${VAR_LIB_DIR}"
    
    log_info "Directories created successfully"
}

# Copy configuration files
copy_config_files() {
    log_info "Copying configuration files..."
    
    # Copy Suricata config
    if [ -f "/sessions/gracious-stoic-goodall/mnt/hungryhounddog/sensor/config/suricata/suricata.yaml" ]; then
        cp /sessions/gracious-stoic-goodall/mnt/hungryhounddog/sensor/config/suricata/suricata.yaml \
           /etc/suricata/suricata.yaml
    fi
    
    # Copy custom rules
    if [ -f "/sessions/gracious-stoic-goodall/mnt/hungryhounddog/sensor/config/suricata/rules/custom-ot.rules" ]; then
        mkdir -p /etc/suricata/rules
        cp /sessions/gracious-stoic-goodall/mnt/hungryhounddog/sensor/config/suricata/rules/custom-ot.rules \
           /etc/suricata/rules/custom-ot.rules
    fi
    
    # Copy agent config
    if [ -f "/sessions/gracious-stoic-goodall/mnt/hungryhounddog/sensor/agent/config.yaml" ]; then
        cp /sessions/gracious-stoic-goodall/mnt/hungryhounddog/sensor/agent/config.yaml \
           "${CONFIG_DIR}/agent/config.yaml"
        chmod 600 "${CONFIG_DIR}/agent/config.yaml"
    fi
    
    log_info "Configuration files copied successfully"
}

# Copy Python agents
copy_agents() {
    log_info "Copying Python agents..."
    
    if [ -f "/sessions/gracious-stoic-goodall/mnt/hungryhounddog/sensor/agent/log_shipper.py" ]; then
        cp /sessions/gracious-stoic-goodall/mnt/hungryhounddog/sensor/agent/log_shipper.py \
           "${SENSOR_BASE_DIR}/agent/log_shipper.py"
        chmod 755 "${SENSOR_BASE_DIR}/agent/log_shipper.py"
    fi
    
    if [ -f "/sessions/gracious-stoic-goodall/mnt/hungryhounddog/sensor/agent/health_check.py" ]; then
        cp /sessions/gracious-stoic-goodall/mnt/hungryhounddog/sensor/agent/health_check.py \
           "${SENSOR_BASE_DIR}/agent/health_check.py"
        chmod 755 "${SENSOR_BASE_DIR}/agent/health_check.py"
    fi
    
    log_info "Agents copied successfully"
}

# Configure network interface
configure_network_interface() {
    log_info "Configuring network interface ${CAPTURE_INTERFACE}..."
    
    # Enable promiscuous mode
    ip link set "${CAPTURE_INTERFACE}" promisc on
    log_info "Enabled promiscuous mode on ${CAPTURE_INTERFACE}"
    
    # Create udev rule to persist promiscuous mode
    cat > "/etc/udev/rules.d/99-hungryhounddog-promisc.rules" << 'UDEV_EOF'
SUBSYSTEM=="net", ACTION=="add", NAME=="eth0", RUN+="/sbin/ip link set %k promisc on"
UDEV_EOF
    
    log_info "Created udev rule for persistent promiscuous mode"
}

# Create systemd service for log shipper
create_log_shipper_service() {
    log_info "Creating systemd service for log shipper..."
    
    cat > "/etc/systemd/system/hungryhounddog-shipper.service" << 'SERVICE_EOF'
[Unit]
Description=HungryHoundDog Log Shipper Agent
After=network-online.target suricata.service
Wants=network-online.target

[Service]
Type=simple
User=root
Environment="SHIPPER_CONFIG=/etc/hungryhounddog/agent/config.yaml"
ExecStart=/opt/hungryhounddog/agent/log_shipper.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE_EOF
    
    systemctl daemon-reload
    systemctl enable hungryhounddog-shipper.service
    log_info "Log shipper service created and enabled"
}

# Create systemd service for health check
create_health_check_service() {
    log_info "Creating systemd service for health check..."
    
    cat > "/etc/systemd/system/hungryhounddog-health.service" << 'SERVICE_EOF'
[Unit]
Description=HungryHoundDog Health Check Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
Environment="HEALTH_CONFIG=/etc/hungryhounddog/agent/config.yaml"
ExecStart=/opt/hungryhounddog/agent/health_check.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE_EOF
    
    systemctl daemon-reload
    systemctl enable hungryhounddog-health.service
    log_info "Health check service created and enabled"
}

# Verify Suricata configuration
verify_suricata_config() {
    log_info "Verifying Suricata configuration..."
    
    if suricata -T -c /etc/suricata/suricata.yaml > /dev/null 2>&1; then
        log_info "Suricata configuration is valid"
    else
        log_warn "Suricata configuration validation failed. Please review manually."
    fi
}

# Set file permissions for security
set_permissions() {
    log_info "Setting file permissions..."
    
    # Suricata log directory
    mkdir -p /var/log/suricata
    chown suricata:suricata /var/log/suricata
    chmod 750 /var/log/suricata
    
    # HungryHoundDog directories
    chown -R root:root "${CONFIG_DIR}"
    chown -R root:root "${SENSOR_BASE_DIR}"
    chmod 750 "${CONFIG_DIR}/agent"
    chmod 750 "${SENSOR_BASE_DIR}/agent"
    
    log_info "Permissions set successfully"
}

# Display installation summary
display_summary() {
    log_info "Installation completed successfully!"
    echo ""
    echo "=== HungryHoundDog Sensor Installation Summary ==="
    echo "Sensor ID: ${SENSOR_ID}"
    echo "Sensor Name: ${SENSOR_NAME}"
    echo "Capture Interface: ${CAPTURE_INTERFACE}"
    echo "Brain Endpoint: ${BRAIN_ENDPOINT}"
    echo ""
    echo "Configuration Directories:"
    echo "  Config: ${CONFIG_DIR}"
    echo "  Logs: ${LOG_DIR}"
    echo "  Lib: ${VAR_LIB_DIR}"
    echo ""
    echo "Systemd Services:"
    echo "  Suricata: systemctl status suricata"
    echo "  Log Shipper: systemctl status hungryhounddog-shipper"
    echo "  Health Check: systemctl status hungryhounddog-health"
    echo ""
    echo "Next Steps:"
    echo "  1. Configure API key in ${CONFIG_DIR}/agent/config.yaml"
    echo "  2. Configure SSL certificates in ${CONFIG_DIR}/certs/"
    echo "  3. Verify Suricata is running: systemctl status suricata"
    echo "  4. Check logs: journalctl -u hungryhounddog-shipper -f"
    echo "===================================================="
    echo ""
}

# Main installation function
main() {
    log_info "Starting HungryHoundDog sensor installation..."
    echo "Sensor ID: ${SENSOR_ID}"
    echo "Sensor Name: ${SENSOR_NAME}"
    echo ""
    
    check_root
    update_system
    install_dependencies
    install_python_dependencies
    install_suricata
    create_directories
    copy_config_files
    copy_agents
    configure_network_interface
    create_log_shipper_service
    create_health_check_service
    verify_suricata_config
    set_permissions
    display_summary
}

# Run main installation
main
