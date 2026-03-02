# HungryHoundDog System Overview

## Project Vision
HungryHoundDog is an AI-Powered Distributed OT Network Security Monitoring Platform designed to detect, analyze, and respond to anomalies in Industrial Control System (ICS) environments. The system combines real-time network intrusion detection with AI-driven threat intelligence to enable proactive security monitoring of critical OT infrastructure.

## High-Level Architecture

The platform consists of four interconnected nodes that work in concert to provide comprehensive security monitoring:

### 1. **Raspberry Pi Sensor Node**
- **Role**: Network packet capture and inline IDS
- **Core Technology**: Suricata IDS/IPS engine
- **Capabilities**:
  - Real-time packet inspection and protocol analysis
  - Rule-based threat detection with OT-specific rulesets
  - Event log generation and forwarding
  - Low-power deployment suitable for edge placement
- **Data Output**: Suricata EVE JSON logs shipped to central server
- **Network Position**: Direct access to monitored OT network segment via port mirroring

### 2. **Ubuntu PC Server ("The Brain")**
- **Role**: Central processing, AI analysis, and visualization
- **Core Components**:
  - **Docker/Docker-Compose**: Service orchestration and isolation
  - **OpenSearch**: Full-text event indexing, searching, and analytics
  - **Grafana**: Real-time dashboards and alerting
  - **Ollama**: Local LLM inference (Phi-3 Mini model)
  - **ChromaDB**: Vector embedding storage for semantic search
  - **FastAPI**: REST API for external integrations
- **Responsibilities**:
  - Ingesting events from Suricata sensor
  - Enriching security events with threat intelligence
  - Running AI-powered anomaly detection and threat analysis
  - Generating alerts and dashboards
  - Storing vector embeddings of attack patterns for similarity matching
- **Storage**: SSD-backed data volumes for high-performance indexing

### 3. **Acer Adversary Node**
- **Role**: Controlled attack simulation and playbook execution
- **Technologies**:
  - **Modbus Protocol Stack**: Simulate/attack OT devices using Modbus TCP/UDP
  - **MQTT Client**: Publish malicious commands to monitored systems
  - **Python-based Attack Playbooks**: Automated attack sequences
- **Capabilities**:
  - Generate realistic OT attack traffic patterns
  - Test system detection capabilities
  - Simulate various threat scenarios (command injection, data exfiltration, DoS)
- **Network Position**: Isolated but networked to simulate external threat actor

### 4. **Dell Development Box**
- **Role**: Development, testing, and infrastructure management
- **Responsibilities**:
  - Running Ansible/Terraform for infrastructure automation
  - Local development and debugging of FastAPI endpoints
  - Unit and integration testing
  - Log aggregation and forensic analysis
  - Git repository and CI/CD pipeline orchestration

## Data Flow Architecture

```
Monitored OT Network
        ↓ (Port Mirror)
   [Raspberry Pi]
   (Suricata IDS)
        ↓ (JSON Logs via Filebeat/TCP)
   [Ubuntu "Brain"]
        ├→ OpenSearch (Indexing & Search)
        ├→ Ollama (AI Analysis)
        ├→ ChromaDB (Semantic Search)
        ├→ Grafana (Visualization)
        └→ FastAPI (External APIs)
        ↓ (Alerts & Intelligence)
   [Acer Adversary] (Feedback loop for validation)
        ↓
   [Dell Dev Box] (Logging & Analytics)
```

## Key Design Principles

1. **Distributed Processing**: Sensor captures, brain analyzes, avoiding central bottleneck
2. **Low-Latency Detection**: Suricata operates at line rate; async AI processing prevents bottlenecks
3. **AI-Driven Insights**: Beyond rule-based detection; semantic understanding of attack patterns
4. **OT-Specific Focus**: Rulesets and models trained on industrial protocols (Modbus, DNP3, etc.)
5. **Local LLM Preference**: Privacy-preserving, air-gappable alternative to cloud-based AI
6. **Reproducible Testing**: Adversary node enables controlled validation of detection capabilities
7. **Comprehensive Observability**: Multi-layer visualization from raw packets to AI analysis

## Technology Stack Rationale

- **Suricata**: Superior Modbus/DNP3 support vs Snort; competitive with Zeek but lower overhead
- **OpenSearch**: Open-source Elasticsearch fork with commercial independence and cost efficiency
- **Phi-3 Mini**: Lightweight LLM (3.8B params) optimized for inference on consumer hardware
- **ChromaDB**: Lightweight vector DB eliminating Pinecone vendor lock-in and API costs
- **FastAPI**: Modern async Python framework with automatic OpenAPI documentation
- **Docker**: Ensures reproducibility across development, staging, and production environments

## Deployment Scenarios

### Development/Lab
- All nodes run on local network with Docker containers on workstations
- Suricata rules and Ollama models loaded locally
- Full end-to-end testing with controlled adversary playbooks

### Production OT Environment
- Raspberry Pi deployed as air-gapped sensor on isolated OT network
- Brain server on hardened Ubuntu with encrypted data volumes
- Acer node optional; focus shifts to real-world threat monitoring
- Dell box as management/forensics station (physically separated)

## Security Posture

- **Defense in Depth**: Multiple detection layers (IDS, ML anomaly, semantic analysis)
- **Least Privilege**: Each service runs with minimal necessary permissions
- **Network Segmentation**: OT network separated from IT network via firewalls
- **Encrypted Communication**: TLS for inter-node communication
- **Audit Logging**: All system activities logged and indexed for forensic analysis
