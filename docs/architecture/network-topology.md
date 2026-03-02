# Network Topology & Data Flow

## Physical Network Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       OT Network Segment (192.168.50.0/24)              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  [Modbus PLC]          [Modbus PLC]          [MQTT RTU]                 │
│  192.168.50.10         192.168.50.11         192.168.50.12              │
│       ↓                     ↓                      ↓                      │
│  (Monitored Systems - No Direct Access)                                 │
│                                                                           │
│                    ↓ Port Mirror (SPAN)                                  │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │        Raspberry Pi Sensor (Passive Tap)                        │   │
│  │        IP: 192.168.50.100                                       │   │
│  │        ├─ Suricata IDS (promisc mode)                           │   │
│  │        ├─ Filebeat / TCP Shipper                                │   │
│  │        └─ ntp-sync, syslog                                      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
         ↓ Encrypted Tunnel (TCP 5000) / Graylog Input
┌─────────────────────────────────────────────────────────────────────────┐
│                  IT Network Segment (192.168.100.0/24)                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │  Ubuntu "Brain" Server (Hypervisor / Container Host)         │      │
│  │  IP: 192.168.100.50                                          │      │
│  │                                                               │      │
│  │  ┌─────────────┐  ┌──────────┐  ┌──────────┐                │      │
│  │  │  OpenSearch │  │  Grafana │  │ FastAPI  │                │      │
│  │  │  (Port 9200)│  │(Port 3000)│  │(Port 8000)                │      │
│  │  └─────────────┘  └──────────┘  └──────────┘                │      │
│  │  ┌─────────────┐  ┌──────────────────┐                       │      │
│  │  │   Ollama    │  │   ChromaDB       │                       │      │
│  │  │ (Port 11434)│  │  (Port 8001)     │                       │      │
│  │  └─────────────┘  └──────────────────┘                       │      │
│  │  ┌─────────────────────────────────┐                         │      │
│  │  │  Data Volumes (SSD-backed)      │                         │      │
│  │  │  └─ opensearch-data/            │                         │      │
│  │  │  └─ chromadb-data/              │                         │      │
│  │  │  └─ ollama-models/              │                         │      │
│  │  └─────────────────────────────────┘                         │      │
│  └──────────────────────────────────────────────────────────────┘      │
│           ↓ MQTT (TCP 1883)  ↓ Modbus TCP (502)  ↓ SSH                 │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │  Acer Adversary Node (Attack Simulation)                     │      │
│  │  IP: 192.168.100.60                                          │      │
│  │  ├─ pymodbus (TCP attack client)                             │      │
│  │  ├─ mosquitto_pub/sub (MQTT fuzzing)                         │      │
│  │  └─ attack-playbooks (Python scripts)                        │      │
│  └──────────────────────────────────────────────────────────────┘      │
│           ↑ SSH / Ansible                                               │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │  Dell Development Box (Mgmt & Forensics)                     │      │
│  │  IP: 192.168.100.70                                          │      │
│  │  ├─ Ansible playbooks                                        │      │
│  │  ├─ tcpdump / Wireshark                                      │      │
│  │  ├─ Git repository                                           │      │
│  │  └─ CI/CD agent                                              │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

## Network Segmentation & VLANs

| VLAN ID | Segment Name | Subnet         | Purpose                    | Devices                    |
|---------|--------------|----------------|----------------------------|----------------------------|
| 50      | OT-Network   | 192.168.50.0/24| Monitored industrial devices| PLCs, RTUs, Sensors        |
| 100     | IT-Network   | 192.168.100.0/24| Management & processing   | Brain, Acer, Dell          |
| (Mgmt)  | Out-of-Band  | N/A            | Console access, IPMI       | (Optional)                 |

## Communication Ports & Protocols

### Inbound to Brain Server (192.168.100.50)

| Port | Protocol | Source        | Service      | Purpose                          |
|------|----------|---------------|--------------|----------------------------------|
| 5000 | TCP      | 192.168.50.100| OpenSearch   | Suricata log ingestion via Filebeat |
| 9200 | TCP      | 192.168.100.x | OpenSearch   | REST API for log queries           |
| 3000 | TCP      | 192.168.100.x | Grafana      | Dashboard access                   |
| 8000 | TCP      | 192.168.100.x | FastAPI      | External integrations              |
| 11434| TCP      | localhost     | Ollama       | LLM inference (internal only)      |
| 8001 | TCP      | localhost     | ChromaDB     | Vector DB (internal only)          |
| 22   | TCP      | 192.168.100.70| SSH          | Management from Dell box           |

### Outbound from Adversary Node (192.168.100.60)

| Port | Protocol | Destination    | Purpose                          |
|------|----------|----------------|----------------------------------|
| 502  | TCP      | 192.168.50.x   | Modbus TCP attacks               |
| 1883 | TCP      | 192.168.100.50 | MQTT command injection           |
| 22   | TCP      | 192.168.100.50 | SSH for automation                |

### Sensor to Brain (192.168.50.100 → 192.168.100.50)

| Port | Protocol | Direction | Service      | Data Format      |
|------|----------|-----------|--------------|------------------|
| 5000 | TCP      | →         | Log Shipper  | EVE JSON (Suricata) |
| 123  | UDP      | ←         | NTP          | Time sync        |

## Data Flow Sequences

### Normal Operation: Detection & Analysis

```
1. OT Network Event (e.g., suspicious Modbus command)
   ↓
2. Raspberry Pi Captures Packets (Suricata)
   ↓
3. Suricata Rules Match → Generates EVE JSON Alert
   ↓
4. Filebeat Ships to OpenSearch (Port 5000)
   ↓
5. OpenSearch Indexes Event (Full-text search)
   ↓
6. Grafana Dashboard Updates (Real-time visualization)
   ↓
7. FastAPI Webhook Triggered → Sends to Ollama for Analysis
   ↓
8. Ollama Generates Threat Assessment (Chain-of-Thought reasoning)
   ↓
9. ChromaDB Stores Embedding (For similarity matching)
   ↓
10. Alert Sent to Security Team (Slack/Email/Dashboard)
```

### Attack Simulation & Validation

```
1. Dell Box Triggers Adversary Playbook (Ansible)
   ↓
2. Acer Node Executes Attack Script (pymodbus/MQTT)
   ↓
3. Modbus/MQTT Traffic Traverses Network
   ↓
4. Raspberry Pi Captures & Detects (Suricata rules)
   ↓
5. Event Shipped to Brain → OpenSearch
   ↓
6. Grafana/Ollama Analyze & Alert
   ↓
7. Dell Box Correlates: Expected Attack ↔ Detected Event
   ↓
8. Validation Report Generated (Detection Accuracy Metrics)
```

## Latency Targets

| Hop                          | Target Latency |
|------------------------------|-----------------|
| OT Network → Sensor Capture  | < 1ms           |
| Sensor → OpenSearch Indexing | < 500ms         |
| OpenSearch Query             | < 200ms         |
| Ollama Inference (analysis)  | 2-5 seconds     |
| Alert to Dashboard Display   | < 1 second      |
| **End-to-End (Detection → Alert)** | **< 10 seconds** |

## High-Availability Considerations

### Current (Lab) Setup
- Single brain server (single point of failure)
- Raspberry Pi sensor redundancy via spare hardware

### Production Roadmap
- OpenSearch cluster (3+ nodes) with replication
- Brain server active-passive failover
- Multiple sensors deployed across network segments
- Centralized syslog forwarding to off-site SIEM

## Security Controls in Network

1. **Firewall Rules**:
   - OT ↔ IT traffic strictly controlled (port 5000 only for logs)
   - No direct OT device access from IT network
   - Acer node isolated until playbook execution

2. **Monitoring & Logging**:
   - All inter-node traffic logged
   - Firewall syslog to central brain
   - Suricata rules cover port scanning/reconnaissance

3. **Encryption**:
   - TLS for OpenSearch cluster (future: mTLS)
   - SSH for management traffic
   - Optional: VPN tunnel for Sensor ↔ Brain

4. **Time Synchronization**:
   - NTP from brain to Pi sensor
   - Ensures log correlation accuracy
