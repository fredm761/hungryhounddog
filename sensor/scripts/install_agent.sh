#!/usr/bin/env bash
# =============================================================================
# HungryHoundDog Sensor Agent — Installation Script
# =============================================================================
# Run this script on the Raspberry Pi to:
#   1. Install Python dependencies
#   2. Create required directories
#   3. Install and enable systemd services
#
# Usage:
#   cd /home/alfredo/hungryhounddog/sensor/scripts
#   chmod +x install_agent.sh
#   ./install_agent.sh
#
# This script requires sudo for directory creation and systemd operations.
# =============================================================================

set -euo pipefail

# --- Color output for readability ---
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
NC="\033[0m"  # No Color

REPO_DIR="/home/alfredo/hungryhounddog"
AGENT_DIR="${REPO_DIR}/sensor/agent"
SERVICE_DIR="${REPO_DIR}/sensor/services"

echo -e "${GREEN}=============================================${NC}"
echo -e "${GREEN} HungryHoundDog Sensor Agent Installer${NC}"
echo -e "${GREEN}=============================================${NC}"
echo ""

# --- Step 1: Install Python dependencies ------------------------------------
echo -e "${YELLOW}[1/4] Installing Python dependencies...${NC}"
pip3 install -r "${AGENT_DIR}/requirements.txt" --break-system-packages --quiet
echo -e "${GREEN}  ✓ Python dependencies installed${NC}"

# --- Step 2: Create required directories ------------------------------------
echo -e "${YELLOW}[2/4] Creating directories...${NC}"

# State directory — stores the shipper's position bookmark
sudo mkdir -p /var/lib/hungryhounddog
sudo chown alfredo:alfredo /var/lib/hungryhounddog

# Agent log directory
sudo mkdir -p /var/log/hungryhounddog
sudo chown alfredo:alfredo /var/log/hungryhounddog

echo -e "${GREEN}  ✓ /var/lib/hungryhounddog created (state files)${NC}"
echo -e "${GREEN}  ✓ /var/log/hungryhounddog created (agent logs)${NC}"

# --- Step 3: Install systemd service files ----------------------------------
echo -e "${YELLOW}[3/4] Installing systemd services...${NC}"

sudo cp "${SERVICE_DIR}/hungryhounddog-shipper.service" /etc/systemd/system/
sudo cp "${SERVICE_DIR}/hungryhounddog-health.service"  /etc/systemd/system/
sudo cp "${SERVICE_DIR}/hungryhounddog-health.timer"    /etc/systemd/system/

sudo systemctl daemon-reload

echo -e "${GREEN}  ✓ Service files copied to /etc/systemd/system/${NC}"

# --- Step 4: Enable services (start on boot) --------------------------------
echo -e "${YELLOW}[4/4] Enabling services...${NC}"

sudo systemctl enable hungryhounddog-shipper.service
sudo systemctl enable hungryhounddog-health.timer

echo -e "${GREEN}  ✓ hungryhounddog-shipper.service enabled (starts on boot)${NC}"
echo -e "${GREEN}  ✓ hungryhounddog-health.timer enabled (starts on boot)${NC}"

# --- Done -------------------------------------------------------------------
echo ""
echo -e "${GREEN}=============================================${NC}"
echo -e "${GREEN} Installation complete!${NC}"
echo -e "${GREEN}=============================================${NC}"
echo ""
echo "To start the agents now (without rebooting):"
echo ""
echo "  sudo systemctl start hungryhounddog-shipper"
echo "  sudo systemctl start hungryhounddog-health.timer"
echo ""
echo "To check status:"
echo ""
echo "  sudo systemctl status hungryhounddog-shipper"
echo "  sudo systemctl status hungryhounddog-health.timer"
echo "  systemctl list-timers | grep hungry"
echo ""
echo "To view logs:"
echo ""
echo "  journalctl -u hungryhounddog-shipper -f"
echo "  journalctl -u hungryhounddog-health -f"
echo "  cat /var/log/hungryhounddog/agent.log"
echo ""
echo "To test the health check manually:"
echo ""
echo "  python3 ${AGENT_DIR}/health_check.py --print-only"
echo ""
