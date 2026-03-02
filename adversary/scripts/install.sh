#!/bin/bash
###############################################################################
# install.sh: Bootstrap adversary node with required tools and dependencies.
#
# This script runs on the Acer Aspire 5 with Ubuntu Server to install:
# - Python dependencies (pymodbus, paho-mqtt, scapy, etc.)
# - Network tools (nmap, tcpdump)
# - Brute force tools (hydra)
# - Mosquitto broker
###############################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Log functions
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
if [[ $EUID -ne 0 ]]; then
    log_error "This script must be run as root"
    exit 1
fi

log_info "=== HungryHoundDog Adversary Node Bootstrap ==="

# Update system packages
log_info "Updating system packages..."
apt-get update
apt-get upgrade -y

# Install system dependencies
log_info "Installing system dependencies..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    git \
    curl \
    wget \
    nmap \
    tcpdump \
    hydra \
    hydra-gtk \
    mosquitto \
    mosquitto-clients \
    openssh-client \
    openssh-server

# Create virtual environment for Python packages
log_info "Creating Python virtual environment..."
python3 -m venv /opt/hungryhounddog/venv || true

# Activate virtual environment
source /opt/hungryhounddog/venv/bin/activate 2>/dev/null || \
    log_warn "Virtual environment activation may have issues"

# Upgrade pip
log_info "Upgrading pip..."
python3 -m pip install --upgrade pip setuptools wheel

# Install Python dependencies
log_info "Installing Python packages..."
python3 -m pip install --quiet \
    pymodbus==3.1.0 \
    paho-mqtt==1.6.1 \
    paramiko==3.2.0 \
    python-nmap==0.0.1 \
    scapy==2.5.0 \
    requests==2.31.0 \
    cryptography==41.0.0

# Configure Mosquitto
log_info "Configuring Mosquitto broker..."
systemctl enable mosquitto
systemctl restart mosquitto

# Create adversary user account
log_info "Creating adversary service account..."
useradd -m -s /bin/bash -d /home/adversary adversary 2>/dev/null || \
    log_warn "Adversary user may already exist"

# Set permissions
log_info "Setting file permissions..."
chown -R adversary:adversary /opt/hungryhounddog
chmod -R 755 /opt/hungryhounddog

# Create logs directory
log_info "Creating logging directory..."
mkdir -p /var/log/hungryhounddog
chown adversary:adversary /var/log/hungryhounddog
chmod 755 /var/log/hungryhounddog

# Verify installations
log_info "Verifying installations..."

# Check Python packages
if python3 -c "import pymodbus; import paho.mqtt.client; import paramiko" 2>/dev/null; then
    log_info "Python dependencies verified"
else
    log_error "Python dependencies verification failed"
fi

# Check system tools
for tool in nmap tcpdump hydra mosquitto_pub; do
    if command -v "$tool" &> /dev/null; then
        log_info "$tool installed successfully"
    else
        log_warn "$tool not found"
    fi
done

# Create service startup script
log_info "Creating adversary service files..."
cat > /etc/systemd/system/hungryhounddog-adversary.service << 'SERVICEEOF'
[Unit]
Description=HungryHoundDog Adversary Node
After=network.target mosquitto.service

[Service]
Type=simple
User=adversary
WorkingDirectory=/home/adversary
ExecStart=/opt/hungryhounddog/venv/bin/python3 /opt/hungryhounddog/adversary/playbooks/02_modbus_read.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICEEOF

systemctl daemon-reload

log_info "=== Bootstrap Complete ==="
log_info "Installed packages:"
log_info "  - pymodbus (Modbus protocol)"
log_info "  - paho-mqtt (MQTT publishing)"
log_info "  - paramiko (SSH brute force)"
log_info "  - python-nmap (Network scanning)"
log_info "  - scapy (Packet manipulation)"
log_info ""
log_info "System tools:"
log_info "  - nmap (Network discovery)"
log_info "  - tcpdump (Packet capture)"
log_info "  - hydra (Brute force)"
log_info "  - mosquitto (MQTT broker)"
log_info ""
log_info "Service account: adversary (UID $(id -u adversary))"
log_info "Python venv: /opt/hungryhounddog/venv"
log_info ""
log_info "Next steps:"
log_info "  1. Configure network interfaces for OT VLAN"
log_info "  2. Start Modbus simulator: systemctl start hungryhounddog-adversary"
log_info "  3. Run attack playbooks from /opt/hungryhounddog/adversary/playbooks/"

exit 0
