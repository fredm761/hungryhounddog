# Brain Server (Ubuntu) Setup Runbook

## Overview
This runbook covers the deployment of the central "Brain" server on Ubuntu 22.04 LTS. This server hosts OpenSearch (indexing), Grafana (visualization), Ollama (AI analysis), ChromaDB (vector embeddings), and FastAPI (external integrations).

**Target Hardware**: Ubuntu PC with ≥8GB RAM, ≥100GB SSD
**IP Address**: 192.168.100.50
**Estimated Deployment Time**: 60-90 minutes

---

## Pre-Deployment Checklist

- [ ] Ubuntu 22.04 LTS server installed
- [ ] Root/sudo access available
- [ ] Static IP assigned (192.168.100.50)
- [ ] Network connectivity to Raspberry Pi (192.168.50.100)
- [ ] Secondary SSD mounted for data volumes (if available)
- [ ] Docker and Docker Compose installed (or will install in Step 1)
- [ ] Sufficient disk space: 100GB+ recommended

---

## Step 1: System Preparation & Docker Installation

### 1.1 Update System
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y \
  curl wget git vim net-tools htop iotop \
  build-essential python3-pip python3-venv \
  ufw fail2ban \
  jq
```

### 1.2 Configure Static IP (if needed)
```bash
# Check current network interface
ip addr show

# Edit Netplan configuration
sudo nano /etc/netplan/01-netcfg.yaml
```

**Netplan config (example for enp0s25):**
```yaml
network:
  version: 2
  ethernets:
    enp0s25:
      dhcp4: no
      addresses:
        - 192.168.100.50/24
      gateway4: 192.168.100.1
      nameservers:
        addresses: [8.8.8.8, 8.8.4.4]
```

```bash
# Apply
sudo netplan apply

# Verify
ip addr show
```

### 1.3 Install Docker & Docker Compose
```bash
# Add Docker repository
sudo apt-get remove docker docker-engine docker.io containerd runc
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo \
  "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add user to docker group (optional, for non-root usage)
sudo usermod -aG docker $USER
newgrp docker

# Verify Docker
docker --version
docker run hello-world
```

### 1.4 Install Docker Compose (standalone)
```bash
# Download latest Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify
docker-compose --version
```

---

## Step 2: Storage Setup

### 2.1 Create Data Volume Directories
```bash
# Check disk layout
lsblk

# If secondary SSD mounted at /mnt/data:
sudo mkdir -p /mnt/data/hungryhounddog/{opensearch,chromadb,ollama,grafana,backups}
sudo chown -R 1000:1000 /mnt/data/hungryhounddog

# Or use local storage:
mkdir -p ~/hungryhounddog/{opensearch,chromadb,ollama,grafana,backups}
chmod 755 ~/hungryhounddog/*
```

### 2.2 Configure SSD Mount (if secondary drive)
```bash
# Get UUID of secondary drive
sudo blkid

# Add to /etc/fstab
sudo nano /etc/fstab

# Add line:
# UUID=xxxx-xxxx  /mnt/data  ext4  defaults,nofail  0  2

# Mount
sudo mount -a

# Verify
df -h | grep /mnt/data
```

---

## Step 3: Create Docker Compose Stack

### 3.1 Create docker-compose.yml
```bash
mkdir -p ~/hungryhounddog/config
cd ~/hungryhounddog
```

**Create docker-compose.yml:**
```bash
cat > docker-compose.yml << 'COMPOSE'
version: '3.8'

services:
  # OpenSearch - Distributed search and analytics engine
  opensearch:
    image: opensearchproject/opensearch:2.11.0
    container_name: opensearch
    environment:
      - cluster.name=opensearch-cluster
      - node.name=opensearch-node1
      - discovery.type=single-node
      - OPENSEARCH_INITIAL_ADMIN_PASSWORD=Admin@123456
      - OPENSEARCH_JAVA_OPTS=-Xms2g -Xmx2g
      - plugins.security.disabled=true  # Lab only; enable TLS in prod
    ports:
      - "9200:9200"
      - "9600:9600"
    volumes:
      - ./opensearch-data:/usr/share/opensearch/data
    networks:
      - hungryhound
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "-u", "admin:Admin@123456", "http://localhost:9200/_cluster/health"]
      interval: 30s
      timeout: 10s
      retries: 5

  # Grafana - Visualization and dashboarding
  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_SECURITY_ADMIN_USER=admin
      - GF_INSTALL_PLUGINS=grafana-piechart-panel
    ports:
      - "3000:3000"
    volumes:
      - ./grafana-data:/var/lib/grafana
      - ./config/grafana-provisioning:/etc/grafana/provisioning
    networks:
      - hungryhound
    depends_on:
      opensearch:
        condition: service_healthy
    restart: unless-stopped

  # Ollama - Local LLM inference engine
  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    ports:
      - "11434:11434"
    volumes:
      - ./ollama-models:/root/.ollama
    environment:
      - OLLAMA_NUM_PARALLEL=2
    networks:
      - hungryhound
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 3

  # ChromaDB - Vector embedding store
  chromadb:
    image: ghcr.io/chroma-core/chroma:latest
    container_name: chromadb
    ports:
      - "8001:8000"
    volumes:
      - ./chromadb-data:/chroma/data
    environment:
      - ANONYMIZED_TELEMETRY=False
    networks:
      - hungryhound
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/heartbeat"]
      interval: 30s
      timeout: 10s
      retries: 3

  # FastAPI - Custom API for integrations
  fastapi:
    image: hungryhounddog/fastapi:latest  # Build locally or use base Python image
    container_name: fastapi
    build:
      context: ./api
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - OPENSEARCH_HOST=opensearch
      - OPENSEARCH_PORT=9200
      - OLLAMA_HOST=http://ollama:11434
      - CHROMADB_HOST=chromadb
      - CHROMADB_PORT=8000
    volumes:
      - ./api:/app
    networks:
      - hungryhound
    depends_on:
      - opensearch
      - ollama
      - chromadb
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    restart: unless-stopped

networks:
  hungryhound:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16

volumes:
  opensearch-data:
  grafana-data:
  ollama-models:
  chromadb-data:
COMPOSE
```

---

## Step 4: Pull and Configure Services

### 4.1 Pull Docker Images
```bash
docker-compose pull
```

### 4.2 Create Grafana Provisioning Config
```bash
mkdir -p config/grafana-provisioning/datasources
mkdir -p config/grafana-provisioning/dashboards

cat > config/grafana-provisioning/datasources/opensearch.yml << 'GRAFANA'
apiVersion: 1

datasources:
  - name: OpenSearch
    type: elasticsearch
    access: proxy
    url: http://opensearch:9200
    basicAuth: true
    basicAuthUser: admin
    basicAuthPassword: Admin@123456
    isDefault: true
    jsonData:
      esVersion: 7.10
      logMessageField: message
      timeField: "@timestamp"
GRAFANA
```

### 4.3 Start Services
```bash
cd ~/hungryhounddog
docker-compose up -d

# Verify containers are running
docker-compose ps

# Expected output:
# opensearch     opensearchproject/opensearch:2.11.0   Up (healthy)
# grafana        grafana/grafana:latest                 Up (healthy)
# ollama         ollama/ollama:latest                   Up (healthy)
# chromadb       ghcr.io/chroma-core/chroma:latest      Up (healthy)
# fastapi        hungryhounddog/fastapi:latest          Up
```

---

## Step 5: Initialize Services

### 5.1 Verify OpenSearch Health
```bash
# Check cluster status
curl -u admin:Admin@123456 http://localhost:9200/_cluster/health | jq

# Expected:
# "status": "green" or "yellow"
```

### 5.2 Create OpenSearch Index Template
```bash
cat > opensearch-template.json << 'TEMPLATE'
{
  "index_patterns": ["suricata-*"],
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "index.lifecycle.name": "suricata-policy",
    "index.lifecycle.rollover_alias": "suricata"
  },
  "mappings": {
    "properties": {
      "timestamp": { "type": "date" },
      "flow_id": { "type": "long" },
      "event_type": { "type": "keyword" },
      "src_ip": { "type": "ip" },
      "dest_ip": { "type": "ip" },
      "src_port": { "type": "integer" },
      "dest_port": { "type": "integer" },
      "proto": { "type": "keyword" },
      "alert": {
        "properties": {
          "signature": { "type": "text" },
          "category": { "type": "keyword" },
          "severity": { "type": "integer" }
        }
      },
      "modbus": {
        "properties": {
          "function": { "type": "keyword" },
          "unit_id": { "type": "integer" }
        }
      }
    }
  }
}
TEMPLATE

# Apply template
curl -u admin:Admin@123456 -X PUT http://localhost:9200/_index_template/suricata-template \
  -H "Content-Type: application/json" \
  -d @opensearch-template.json
```

### 5.3 Pull Ollama Model (Phi-3 Mini)
```bash
# This downloads the 3.8B parameter model (~2.3GB)
# May take 5-10 minutes depending on internet speed

docker exec ollama ollama pull phi

# Verify model is available
docker exec ollama ollama list

# Expected: "phi" listed with tag "latest"
```

### 5.4 Verify ChromaDB
```bash
# Test ChromaDB API
curl http://localhost:8001/api/v1/heartbeat

# Expected: 200 OK, minimal response
```

### 5.5 Verify FastAPI
```bash
# Check API documentation
curl http://localhost:8000/docs | grep -i openapi

# Or visit in browser: http://192.168.100.50:8000/docs
```

---

## Step 6: Firewall & Security

### 6.1 Configure UFW Firewall
```bash
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH
sudo ufw allow 22/tcp

# Allow from Raspberry Pi sensor (port 5000 for Filebeat)
sudo ufw allow from 192.168.50.0/24 to any port 5000

# Allow from local IT network for management
sudo ufw allow from 192.168.100.0/24 to any port 3000  # Grafana
sudo ufw allow from 192.168.100.0/24 to any port 9200  # OpenSearch
sudo ufw allow from 192.168.100.0/24 to any port 8000  # FastAPI

# Allow container-to-container (internal bridge)
sudo ufw allow from 172.20.0.0/16 to 172.20.0.0/16

# Verify rules
sudo ufw status numbered
```

### 6.2 Set Up fail2ban
```bash
sudo apt install -y fail2ban

# Configure for SSH
sudo nano /etc/fail2ban/jail.local

# Add:
# [DEFAULT]
# bantime = 3600
# maxretry = 5
#
# [sshd]
# enabled = true

sudo systemctl restart fail2ban
```

### 6.3 Configure Log Rotation
```bash
# Create logrotate config for Docker containers
sudo nano /etc/logrotate.d/docker-containers

# Add:
# /var/lib/docker/containers/*/*.log {
#   rotate 7
#   daily
#   compress
#   size 10M
# }
```

---

## Step 7: Create Backing-Up Scripts

### 7.1 Backup Script
```bash
cat > ~/hungryhounddog/backup.sh << 'BACKUP'
#!/bin/bash

BACKUP_DIR="/backups/hungryhounddog"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup OpenSearch data
docker exec opensearch bash -c \
  "elasticdump --input http://localhost:9200 --output $ | gzip > /backups/opensearch-$TIMESTAMP.json.gz"

# Backup Grafana dashboards
docker exec grafana tar czf /var/lib/grafana/dashboards-$TIMESTAMP.tar.gz /var/lib/grafana/dashboards/

# Backup configurations
tar czf $BACKUP_DIR/config-$TIMESTAMP.tar.gz ~/hungryhounddog/config/

echo "Backup completed: $BACKUP_DIR/backup-$TIMESTAMP"
BACKUP

chmod +x ~/hungryhounddog/backup.sh
```

### 7.2 Schedule Daily Backup
```bash
# Add to crontab
crontab -e

# Add line:
# 2 2 * * * /home/ubuntu/hungryhounddog/backup.sh >> /var/log/hungryhounddog-backup.log 2>&1
```

---

## Step 8: Verify Complete Stack

### 8.1 Test All Endpoints
```bash
# OpenSearch health
curl -u admin:Admin@123456 http://localhost:9200/_cluster/health

# Grafana login
curl -u admin:admin http://localhost:3000/api/user

# Ollama models
curl http://localhost:11434/api/tags

# ChromaDB heartbeat
curl http://localhost:8001/api/v1/heartbeat

# FastAPI status
curl http://localhost:8000/health

# View logs of all containers
docker-compose logs -f
```

### 8.2 Create Test Index in OpenSearch
```bash
# Create test index
curl -u admin:Admin@123456 -X PUT http://localhost:9200/test-index \
  -H "Content-Type: application/json" \
  -d '{"settings": {"number_of_shards": 1}}'

# Ingest test document
curl -u admin:Admin@123456 -X POST http://localhost:9200/test-index/_doc \
  -H "Content-Type: application/json" \
  -d '{"timestamp": "2025-02-27T12:00:00Z", "message": "Test alert"}'

# Query
curl -u admin:Admin@123456 http://localhost:9200/test-index/_search | jq
```

---

## Troubleshooting

### Problem: OpenSearch OOM (Out of Memory)
```bash
# Check memory usage
docker stats opensearch

# Reduce heap size in docker-compose.yml:
# OPENSEARCH_JAVA_OPTS=-Xms1g -Xmx1g

# Restart
docker-compose restart opensearch
```

### Problem: Ollama very slow
```bash
# Check if GPU acceleration is available
docker exec ollama nvidia-smi

# If slow on CPU, reduce model size or limit concurrent requests
docker exec ollama ollama pull phi:7b-mini  # Smaller variant

# Restart
docker-compose restart ollama
```

### Problem: Containers not starting
```bash
# Check logs
docker-compose logs -f opensearch

# Common issues:
# - Port already in use: lsof -i :9200
# - Disk full: df -h
# - Memory full: free -h
```

### Problem: Filebeat from sensor not connecting
```bash
# Verify OpenSearch is listening
sudo netstat -tlnp | grep 9200

# Check firewall
sudo ufw status | grep 9200

# Verify sensor can reach server
ping -c 1 192.168.50.100 (from Pi perspective)
```

---

## Maintenance

### Weekly
- [ ] Check disk usage: `df -h`
- [ ] Monitor container memory: `docker stats`
- [ ] Review error logs: `docker-compose logs --tail 50`

### Monthly
- [ ] Update Ollama models: `docker exec ollama ollama pull phi --latest`
- [ ] Backup critical data: `./backup.sh`
- [ ] Audit Grafana dashboards for stale alerts

### Quarterly
- [ ] Update Docker images: `docker-compose pull && docker-compose up -d`
- [ ] Review and optimize OpenSearch indices
- [ ] Test disaster recovery from backups
