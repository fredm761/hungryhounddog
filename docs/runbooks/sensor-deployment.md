# Raspberry Pi Sensor Deployment Runbook

## Overview
This runbook covers the complete deployment of a Raspberry Pi as the HungryHoundDog network sensor. The Pi will run Suricata IDS to passively monitor OT network traffic and forward events to the Brain server.

**Target Hardware**: Raspberry Pi 4 (2GB+ RAM) or Pi 5
**OS**: Raspberry Pi OS Lite (Debian-based)
**Estimated Deployment Time**: 30-45 minutes

---

## Pre-Deployment Checklist

- [ ] Raspberry Pi with power supply and SD card (32GB+ recommended)
- [ ] Network cable or Wi-Fi configured
- [ ] SSH access enabled
- [ ] Static IP assigned (192.168.50.100 in our topology)
- [ ] Physical placement near managed switch with SPAN port
- [ ] Brain server IP known (192.168.100.50)

---

## Step 1: OS Installation & Initial Setup

### 1.1 Flash Raspberry Pi OS Lite
```bash
# On your laptop/workstation, use Raspberry Pi Imager
# https://www.raspberrypi.com/software/

# Or command-line on Linux/Mac:
# Download image: https://www.raspberrypi.com/software/operating-systems/
# Identify SD card: diskutil list
# Unmount: diskutil unmountDisk /dev/diskX
# Flash: sudo dd if=raspios-lite.img of=/dev/rdiskX bs=4m
# Eject: diskutil eject /dev/diskX
```

### 1.2 Boot & SSH Configuration
```bash
# Insert SD card into Pi, power on
# Wait 30 seconds for first boot

# From your workstation, SSH in (default user: pi)
ssh pi@192.168.50.100
# Default password: raspberry

# Change default password immediately
passwd
# Enter new strong password
```

### 1.3 System Update
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y vim curl wget net-tools git

# Set timezone
sudo timedatectl set-timezone UTC

# Check date/time
date
```

---

## Step 2: Network Configuration

### 2.1 Static IP Assignment (if not via DHCP)
```bash
# Edit netplan configuration
sudo nano /etc/netplan/01-netcfg.yaml
```

**File content:**
```yaml
network:
  version: 2
  ethernets:
    eth0:
      dhcp4: no
      addresses:
        - 192.168.50.100/24
      gateway4: 192.168.50.1
      nameservers:
        addresses: [8.8.8.8, 8.8.4.4]
```

```bash
# Apply configuration
sudo netplan apply

# Verify
ip addr show eth0
```

### 2.2 Configure NTP for Time Sync with Brain
```bash
# Install NTP client
sudo apt install -y chrony

# Edit chrony config
sudo nano /etc/chrony/chrony.conf

# Add Brain server as NTP source (add to file):
# server 192.168.100.50 iburst

# Restart chrony
sudo systemctl restart chrony

# Verify sync
chronyc tracking
```

### 2.3 Network Interface for Packet Capture
```bash
# If using separate capture NIC, bring it up without IP
# (In our setup, we use eth0 or dedicated interface for SPAN)

# Get interface name
ip link show

# Enable promiscuous mode for Suricata capture
# (Will be done in Suricata config, not here)
```

---

## Step 3: Install Suricata IDS

### 3.1 Add Suricata Repository
```bash
# Install OISF repository
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:oisf/suricata-stable

# Update package list
sudo apt update
```

### 3.2 Install Suricata
```bash
sudo apt install -y suricata

# Verify installation
suricata -V
# Expected output: Suricata version X.X.X
```

### 3.3 Configure Suricata

**Edit main config:**
```bash
sudo nano /etc/suricata/suricata.yaml
```

**Key configuration changes:**

1. **Set HOME_NET (OT network to monitor):**
```yaml
HOME_NET: "[192.168.50.0/24]"
EXTERNAL_NET: "!$HOME_NET"
```

2. **Configure capture interface (change `eth0` if different):**
```yaml
af-packet:
  - interface: eth0
    threads: 4
    cluster-id: 99
    cluster-type: cluster_flow
    defrag: no
    use-mmap: yes
    ring-buffer-size: 200000
```

3. **Enable EVE JSON output:**
```yaml
eve-log:
  enabled: yes
  filetype: regular
  filename: eve.json
  types:
    - alert:
        http-body: no
        payload: yes
    - dns:
        query: yes
        answer: yes
    - http:
        extended: yes
    - modbus:
        enabled: yes
    - stats
```

4. **Reduce noise (optional):**
```yaml
# Disable DNS resolution for performance
dns:
  enabled: no

# Enable only critical rules initially
classification-file: /etc/suricata/classification.config
reference-config-file: /etc/suricata/reference.config
```

### 3.4 Update Suricata Rules

```bash
# Update to latest ruleset (ET Open rules)
sudo suricata-update

# Verify rules are loaded
sudo suricatasc -c "rule-list" /var/run/suricata/suricata-command.socket | head -20

# Expected: List of loaded rules with count
```

---

## Step 4: Configure Log Shipping to Brain Server

### 4.1 Install Filebeat (Log Shipper)
```bash
# Install Filebeat for Elastic/OpenSearch compatibility
curl -L -O https://artifacts.opensearch.org/filebeat/filebeat-7.13.3-linux-arm64.tar.gz
tar xzf filebeat-7.13.3-linux-arm64.tar.gz
sudo mv filebeat-7.13.3-linux-arm64 /opt/filebeat
sudo chown -R root:root /opt/filebeat
```

### 4.2 Configure Filebeat

**Edit Filebeat config:**
```bash
sudo nano /opt/filebeat/filebeat.yml
```

**File content (Modbus-optimized):**
```yaml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /var/log/suricata/eve.json
  json.message_key: message
  json.keys_under_root: true
  json.add_error_key: true

processors:
  - add_fields:
      target: metadata
      fields:
        sensor_name: "pi-sensor-01"
        network_segment: "OT"
        location: "Building-A"

output.elasticsearch:
  hosts: ["192.168.100.50:9200"]
  index: "suricata-%{+yyyy.MM.dd}"

logging.level: info
logging.to_files: true
logging.files:
  path: /var/log/filebeat
  name: filebeat
  keepfiles: 7
```

### 4.3 Start Filebeat
```bash
# Start Filebeat service
cd /opt/filebeat
sudo ./filebeat -e -c filebeat.yml &

# Or create systemd service for autostart:
sudo nano /etc/systemd/system/filebeat.service
```

**Filebeat systemd service:**
```ini
[Unit]
Description=Filebeat
After=network.target

[Service]
User=root
Type=simple
ExecStart=/opt/filebeat/filebeat -e -c /opt/filebeat/filebeat.yml
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable filebeat
sudo systemctl start filebeat
sudo systemctl status filebeat
```

---

## Step 5: Start & Verify Suricata

### 5.1 Enable Suricata Service
```bash
sudo systemctl enable suricata
sudo systemctl start suricata
sudo systemctl status suricata
```

### 5.2 Verify Packet Capture
```bash
# Check if Suricata is capturing packets
sudo tail -f /var/log/suricata/suricata.log | grep -i "capture"

# Expected output:
# [1:1:0] <info> -- [Classification: ...] ...
# Notice all_layers
```

### 5.3 Verify EVE JSON Output
```bash
# Check if events are being logged
sudo tail -f /var/log/suricata/eve.json | head -5

# Expected: JSON-formatted events from Suricata
# {"timestamp":"2025-02-27T10:15:23.456789+0000","flow_id":123456,...}
```

---

## Step 6: Connectivity Verification

### 6.1 Test SSH to Brain Server
```bash
# From Pi, verify connectivity to Brain
ssh ubuntu@192.168.100.50 "echo 'SSH Connection OK'"

# If no password-less login, set up SSH keys
ssh-keygen -t rsa -f ~/.ssh/id_rsa -N ""
ssh-copy-id -i ~/.ssh/id_rsa.pub ubuntu@192.168.100.50
```

### 6.2 Test Log Reception on Brain
```bash
# From Brain server, verify Filebeat connection
curl -s http://localhost:9200/_cat/indices | grep suricata

# Expected: Index like "suricata-2025.02.27"
# If no index, check Filebeat logs on Pi:
sudo systemctl status filebeat
sudo journalctl -u filebeat -n 20
```

### 6.3 Verify NTP Sync
```bash
# From Pi, check time sync
chronyc tracking

# Expected: "Leap status: Normal"
# Time offset should be < 100ms
```

---

## Step 7: Generate Test Traffic

### 7.1 Trigger a Simple Detection
```bash
# From another machine on the OT network (or use Acer adversary node):
# Generate traffic that matches a Suricata rule

# Example: Port scan (high port activity)
nmap -p 1-1000 192.168.50.10 2>/dev/null

# Or craft a simple HTTP request:
curl -v http://192.168.50.10/admin (if web service exists)
```

### 7.2 Verify Alert in OpenSearch
```bash
# From Brain server, query recent alerts:
curl -s http://localhost:9200/suricata-*/\_search?size=5 | jq '.hits.hits[] | ._source.alert'

# Expected: Alert entries matching the traffic you generated
```

---

## Step 8: Hardening & Security

### 8.1 Disable Unnecessary Services
```bash
# Disable Bluetooth (not needed)
sudo systemctl disable bluetooth

# Disable unnecessary daemons
sudo systemctl disable avahi-daemon
```

### 8.2 Configure Firewall
```bash
# Install UFW (Uncomplicated Firewall)
sudo apt install -y ufw

# Allow SSH (critical!)
sudo ufw allow 22/tcp

# Allow NTP from Brain
sudo ufw allow from 192.168.100.50 to any port 123

# Deny all inbound by default
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Enable UFW
sudo ufw enable

# Verify rules
sudo ufw status
```

### 8.3 SSH Key-Only Authentication
```bash
# Disable password login
sudo nano /etc/ssh/sshd_config

# Find and uncomment/set:
# PasswordAuthentication no
# PubkeyAuthentication yes

# Restart SSH
sudo systemctl restart ssh
```

### 8.4 Set Read-Only Filesystem (Advanced)
```bash
# Optional: Make /var/log read-only to prevent tampering
sudo nano /etc/fstab
# Add: /var/log ext4 defaults,ro 0 0
# (Only after confirming logs are being shipped!)
```

---

## Troubleshooting

### Problem: Suricata not capturing packets
```bash
# Verify interface is up
ip addr show eth0

# Check Suricata logs
sudo tail -100 /var/log/suricata/suricata.log | grep -i error

# Verify promiscuous mode (if needed)
ip link show eth0 | grep -i promisc

# Enable promiscuous mode
sudo ip link set eth0 promisc on
```

### Problem: Filebeat not sending logs
```bash
# Check Filebeat status
sudo systemctl status filebeat

# Verify connectivity to Brain
telnet 192.168.100.50 9200

# Check Filebeat logs
sudo cat /var/log/filebeat/filebeat

# Verify file permissions
sudo ls -la /var/log/suricata/eve.json
```

### Problem: Time not synced
```bash
# Check chrony status
chronyc sources

# Force NTP update
sudo chronyc makestep

# Check system time
date
timedatectl status
```

### Problem: High CPU/Memory usage
```bash
# Monitor resource usage
top -b -n 1 | head -20

# If Suricata consuming too much:
# - Reduce worker threads in suricata.yaml (threads: 2)
# - Disable unnecessary protocol analyzers
# - Increase ring-buffer-size

# If Filebeat consuming too much:
# - Increase batch_size in filebeat.yml
# - Reduce scan frequency
```

---

## Ongoing Maintenance

### Weekly
- [ ] Monitor disk space: `df -h`
- [ ] Check Suricata status: `systemctl status suricata`
- [ ] Verify logs reaching OpenSearch

### Monthly
- [ ] Update Suricata rules: `sudo suricata-update`
- [ ] Review sensor logs for errors: `sudo grep -i error /var/log/suricata/suricata.log`
- [ ] Update OS packages: `sudo apt update && sudo apt upgrade`

### Quarterly
- [ ] Review rule effectiveness against detected events
- [ ] Update Raspberry Pi OS: `sudo apt dist-upgrade`
- [ ] Audit SSH access logs: `grep sshd /var/log/auth.log`

---

## Backup & Recovery

### Backup Suricata Configuration
```bash
# Backup on Brain server (via Ansible playbook)
sudo rsync -av pi@192.168.50.100:/etc/suricata/ /backups/sensor-config/
```

### Restore Configuration
```bash
# If Pi needs to be redeployed:
scp -r /backups/sensor-config/suricata.yaml pi@192.168.50.100:/etc/suricata/
ssh pi@192.168.50.100 sudo systemctl restart suricata
```
