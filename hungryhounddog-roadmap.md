# HungryHoundDog — Project Roadmap

**An AI-Powered Distributed OT Network Security Monitoring Platform**

**Author:** Alfredo | **Created:** February 2026 | **Target Completion:** Mid-April 2026

---

## 0x1 — Project Overview

### 0x1.1 — What You Are Building

HungryHoundDog is a distributed network security monitoring platform deployed across physical hardware on your home network. It combines four pillars that directly mirror enterprise security infrastructure:

- **0x1.1.A** — A passive network sensor that captures and analyzes live traffic using an industry-standard IDS (Intrusion Detection System), deployed on a dedicated edge device and powered over Ethernet — exactly how sensors are deployed in enterprise OT (Operational Technology) environments.
- **0x1.1.B** — A central analytics server that ingests, indexes, and visualizes security events, runs ML (Machine Learning) anomaly detection on network flows, and hosts an AI chatbot that lets you query your security posture in natural language using RAG (Retrieval-Augmented Generation).
- **0x1.1.C** — An adversary simulation node that emulates OT protocols (Modbus TCP) and executes scripted multi-stage attack playbooks mapped to the MITRE ATT&CK for ICS (Industrial Control Systems) framework — demonstrating you understand the threat landscape, not just the defensive tools.
- **0x1.1.D** — A development workstation used for SSH (Secure Shell) access, version control, and documentation — modeling the separation of duties between operational infrastructure and development environments.

### 0x1.2 — Why This Project Matters for Your Career

This project transforms you from someone who *operates* security tools (your current CrowdStrike work) into someone who can *architect and build* security infrastructure. That distinction is the difference between a $90K–$120K analyst role and a $150K–$200K+ engineering or technical leadership role.

Here is specifically what this project proves to employers:

- **0x1.2.A** — You can design a distributed security architecture across multiple devices with defined data flows, network segmentation, and separation of concerns — the same skill required to design SOC (Security Operations Center) infrastructure.
- **0x1.2.B** — You understand OT security at a level most IT security professionals do not. OT/ICS security is a high-demand, low-supply niche. Employers in critical infrastructure (energy, manufacturing, logistics, defense) pay premium salaries for people who speak both IT and OT.
- **0x1.2.C** — You can integrate AI/ML into security workflows in a practical way, not as a buzzword. Your RAG chatbot mirrors the exact project you are working on at UPS, and your ML anomaly detection demonstrates you can move beyond signature-based detection.
- **0x1.2.D** — You can automate adversary simulation — a skill that overlaps with red teaming, penetration testing, and detection engineering.

### 0x1.3 — How This Mirrors Your Current Work

| Your Work at UPS/Fortna | HungryHoundDog Equivalent |
|---|---|
| CrowdStrike Falcon asset discovery across 1,000+ subnets | Suricata sensor discovering devices via passive traffic analysis |
| Assigning collectors to subnets, scheduling collections | Deploying a dedicated sensor to a mirrored switch port, scheduling log ingestion |
| Monitoring collectors for connectivity | Health-check agents monitoring sensor status |
| LLM + RAG chatbot for querying network security posture | Ollama + ChromaDB + LangChain chatbot for querying alert and log data |
| Endpoint threat monitoring | ML anomaly detection on network flow data |
| IP/subnet/VLAN management across UPS sites | VLAN segmentation and port mirroring on your managed switch |

This is not a coincidence. The project is intentionally designed so that every component maps to something you do at enterprise scale. During interviews, you will say: *"I built this at home to deepen my understanding of the infrastructure I manage at enterprise scale — here is what I learned and what I would do differently."*

---

## 0x2 — System Architecture

### 0x2.1 — Network Topology Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│                        HungryHoundDog Network Topology                       │
│                                                                              │
│   ┌────────────────────────────────────────────────────────────────────┐     │
│   │            TP-LINK SG2008P MANAGED PoE+ SWITCH                    │     │
│   │                                                                    │     │
│   │   Port 1 [PoE+]    Port 2         Port 3         Port 4          │     │
│   │   ┌──────────┐    ┌──────────┐   ┌──────────┐   ┌──────────┐    │     │
│   │   │ MIRROR   │    │          │   │ MIRROR   │   │          │    │     │
│   │   │ SOURCE   │    │ NORMAL   │   │ DEST     │   │ NORMAL   │    │     │
│   │   │ VLAN 10  │    │ VLAN 20  │   │ PROMISC  │   │ VLAN 20  │    │     │
│   │   └────┬─────┘    └────┬─────┘   └────┬─────┘   └────┬─────┘    │     │
│   └────────┼───────────────┼──────────────┼──────────────┼───────────┘     │
│            │               │              │              │                   │
│            │CAT6           │CAT6          │CAT6+PoE      │CAT6              │
│            │               │              │              │                   │
│   ┌────────▼─────────┐  ┌─▼────────────┐ │  ┌───────────▼──────────┐       │
│   │ ACER ASPIRE 5    │  │ UBUNTU PC    │ │  │ DELL WORKSTATION     │       │
│   │ "The Adversary"  │  │ "The Brain"  │ │  │ "Dev Box"            │       │
│   │                  │  │              │ │  │                      │       │
│   │ Ubuntu Server    │  │ Docker Host  │ │  │ Windows 11           │       │
│   │ 24.04 LTS        │  │              │ │  │ VS Code + SSH Remote │       │
│   │                  │  │ ┌──────────┐ │ │  │ Git + GitHub Desktop │       │
│   │ OT Simulator:    │  │ │OpenSearch│ │ │  │ Documentation        │       │
│   │  · Modbus TCP    │  │ │ (SIEM)   │ │ │  │ Claude AI assist     │       │
│   │    Server         │  │ └──────────┘ │ │  │                      │       │
│   │  · MQTT Broker   │  │ ┌──────────┐ │ │  └──────────────────────┘       │
│   │                  │  │ │ Ollama   │ │ │                                  │
│   │ Attack Tools:    │  │ │ Phi-3    │ │ │                                  │
│   │  · nmap          │  │ │ Mini SLM │ │ │                                  │
│   │  · scapy         │  │ └──────────┘ │ │                                  │
│   │  · hydra         │  │ ┌──────────┐ │ │                                  │
│   │  · custom Python │  │ │ChromaDB  │ │ │                                  │
│   │    playbooks     │  │ │(RAG Vec.)│ │ │                                  │
│   │                  │  │ └──────────┘ │ │                                  │
│   │ Traffic Gen:     │  │ ┌──────────┐ │ │                                  │
│   │  · baseline      │  │ │ FastAPI  │ │ │         ┌───────────────────┐    │
│   │    normal traffic │  │ │ Ingest + │ │ │         │ RASPBERRY PI 4    │    │
│   │  · OT protocol   │  │ │ Chatbot  │ │ │         │ "The Sensor"      │    │
│   │    traffic        │  │ └──────────┘ │ │         │                   │    │
│   │                  │  │ ┌──────────┐ │ │         │ Raspberry Pi OS   │    │
│   └──────────────────┘  │ │ ML       │ │◄─ ─ ─ ─ ─│ Lite (64-bit)     │    │
│                         │ │ Anomaly  │ │  WiFi     │                   │    │
│                         │ │ Detect   │ │  (mgmt)   │ Suricata IDS      │    │
│                         │ └──────────┘ │           │ Python Log Agent  │    │
│                         │ ┌──────────┐ │           │ Health Monitor    │    │
│                         │ │ Grafana  │ │           │                   │    │
│                         │ │Dashboards│ │           │ eth0: PROMISC     │    │
│                         │ └──────────┘ │           │  (mirror dest,    │    │
│                         │              │           │   no IP, PoE)     │    │
│                         └──────────────┘           │ wlan0: 192.168.x  │    │
│                                                    │  (mgmt + log ship)│    │
│                                                    └───────────────────┘    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 0x2.2 — Data Flow Explanation

```
DATA FLOW DIAGRAM

  ┌───────────┐         ┌──────────┐        ┌─────────────────────────────┐
  │ Adversary │ ─────── │  Switch  │──copy──▶│ Pi Sensor (eth0, promisc)  │
  │  (Acer)   │ attacks │ Port 1→3 │ mirror  │ Suricata captures + parses │
  └───────────┘         │ mirror   │         └────────────┬────────────────┘
                        └──────────┘                      │
                                                          │ WiFi (wlan0)
                                                          │ JSON logs via HTTPS
                                                          ▼
                                              ┌───────────────────────┐
                                              │ Ubuntu "The Brain"    │
                                              │                       │
                                              │  FastAPI Ingestion ───┼──▶ OpenSearch
                                              │         │             │     (index + store)
                                              │         ▼             │
                                              │  ML Anomaly Engine ───┼──▶ Alert Manager
                                              │         │             │     (notifications)
                                              │         ▼             │
                                              │  RAG Indexer ─────────┼──▶ ChromaDB
                                              │         │             │     (vector embeddings)
                                              │         ▼             │
                                              │  LangChain + Ollama ──┼──▶ Chatbot Interface
                                              │         │             │     (natural language
                                              │         ▼             │      security queries)
                                              │  Grafana Dashboards ──┼──▶ Browser UI
                                              │                       │     (visual monitoring)
                                              └───────────────────────┘
```

### 0x2.3 — Data Path Explanations

- **0x2.3.A — Adversary → Switch → Sensor (Mirror Path):** The Acer generates both legitimate OT protocol traffic (Modbus TCP, MQTT) and attack traffic (port scans, brute force, OT exploitation). All traffic on Switch Port 1 is mirrored to Port 3 where the Pi's eth0 interface listens in promiscuous mode. The Pi never transmits on this interface — it is passive, just like a real enterprise network tap. This is how you see everything without being seen.
- **0x2.3.B — Sensor → Brain (Log Shipping Path):** Suricata on the Pi generates JSON-formatted alert and flow logs. A custom Python agent reads these logs and ships them over WiFi (wlan0) to the Ubuntu PC's FastAPI ingestion endpoint over HTTPS. WiFi is used for management to keep the monitoring interface (eth0) completely passive. This separation of monitoring and management interfaces mirrors enterprise IDS (Intrusion Detection System) deployment best practices.
- **0x2.3.C — Brain Internal (Processing Pipeline):** FastAPI receives logs and does three things simultaneously: stores them in OpenSearch for search and visualization, feeds flow metadata to the ML anomaly detection engine (scikit-learn Isolation Forest), and passes alert text to the RAG indexer for ChromaDB embedding. This fan-out architecture means a single data ingest feeds multiple analytical engines — a common pattern in enterprise SIEM (Security Information and Event Management) pipelines.
- **0x2.3.D — Brain → User (Query Path):** Users interact with the platform two ways: through Grafana dashboards for visual monitoring (alert timelines, traffic heatmaps, anomaly scores) and through the LangChain-powered chatbot for natural language queries like *"Show me all Modbus anomalies in the last hour"* or *"What are the top 5 most suspicious source IPs today?"* The chatbot uses RAG to pull relevant log context from ChromaDB, then passes it to the Phi-3 Mini SLM (Small Language Model) running on Ollama for response generation.
- **0x2.3.E — Dev Box → All Devices (Management Path):** The Dell workstation connects to all devices via SSH for configuration, deployment, and debugging. It is also where Git operations happen — code is written here, pushed to GitHub, and pulled onto the operational devices. This mirrors the separation of development and production environments in enterprise settings.

### 0x2.4 — Why This Architecture Reflects Real Enterprise Design

| Enterprise Principle | HungryHoundDog Implementation |
|---|---|
| Dedicated sensor appliances at network boundaries | Raspberry Pi as a dedicated passive sensor on a mirrored port |
| Separate monitoring and management planes | Pi eth0 (monitoring, no IP) vs. wlan0 (management, IP assigned) |
| Centralized SIEM for log aggregation | OpenSearch on Ubuntu collecting from all sources |
| VLAN segmentation between OT and IT | VLAN 10 (OT simulation) and VLAN 20 (management) on the managed switch |
| AI/ML augmenting human analysts | Isolation Forest for automated anomaly scoring; RAG chatbot for NL queries |
| Red team / adversary simulation | Dedicated Acer running MITRE ATT&CK for ICS playbooks |
| Immutable infrastructure via containers | Docker Compose on Ubuntu; sensor agent deployable via scripts |

---

## 0x3 — Bill of Materials

### 0x3.1 — Hardware You Own (Pre-Existing)

| # | Item | Role in Architecture | Why It Is Needed |
|---|---|---|---|
| 0x3.1.A | Raspberry Pi 4 Model B (2 GB LPDDR4 RAM) | "The Sensor" — dedicated passive network sensor | Its low power draw, Gigabit Ethernet, and PoE capability make it ideal for always-on edge sensor deployment. 2 GB RAM is sufficient for Suricata on a home-network traffic volume. Enterprise sensors like Cisco Stealthwatch or ExtraHop are purpose-built appliances — the Pi models this concept at home lab scale. |
| 0x3.1.B | Ubuntu Linux PC (i5-6500, 15.5 GB RAM, 500 GB disk) | "The Brain" — central server running all analytics, AI, and dashboards | The i5-6500 and 15.5 GB RAM can run Docker Compose with OpenSearch (4 GB heap), Ollama + Phi-3 Mini (~3 GB), ChromaDB (~0.5 GB), Grafana (~0.5 GB), FastAPI, and the ML engine within budget. This machine is the SOC-in-a-box. |
| 0x3.1.C | Acer Aspire 5 (Ryzen 3 3200U, 4 GB RAM) | "The Adversary" — attack simulation and OT protocol emulation | 4 GB RAM is tight but sufficient when running Ubuntu Server (no GUI, ~0.5 GB OS overhead) with Python-based attack tools and OT simulators. No GUI means maximum RAM for tool execution. You SSH into it from the Dell. |
| 0x3.1.D | Dell Workstation (Ultra 9 288V, 32 GB RAM, NPU) | "Dev Box" — development, SSH hub, Git, documentation | This is your most powerful machine but it stays out of the operational architecture. Its role is writing code, managing Git, and SSHing into the other three devices. The NPU (Neural Processing Unit) is not used in this project but is a nice bonus if you experiment with local model inference later. |

### 0x3.2 — Hardware You Purchased

| # | Item | Role in Architecture | Why It Is Needed |
|---|---|---|---|
| 0x3.2.A | TP-Link SG2008P 8-Port Gigabit Smart PoE+ Switch | Network backbone — port mirroring, PoE delivery, VLAN segmentation | This is the most critical purchase. Port mirroring sends a copy of all traffic on source ports to the Pi's monitoring port. PoE powers the Pi through the Ethernet cable (eliminating a separate power supply). VLAN support lets you segment OT traffic from management traffic. The Omada SDN integration means you configure it via a web GUI — a skill that maps to managing Cisco, Aruba, or Juniper switches in enterprise environments. |
| 0x3.2.B | CAT6 Ethernet cables (x5) | Device-to-switch connections | CAT6 supports Gigabit speeds up to 55 meters, more than enough for a home lab. Five cables connect: Pi to switch, Ubuntu to switch, Acer to switch (via USB adapter), Dell to switch (if wired), and one spare. |
| 0x3.2.C | CAT8 Ethernet cables (x2) | High-performance connections for server and primary links | CAT8 supports up to 25/40 Gbps and is overkill for this project — but they are more durable and provide better shielding. Use one for the Ubuntu PC (highest traffic volume) and keep one as spare. |
| 0x3.2.D | Raspberry Pi 4 PoE HAT (Hardware Attached on Top) | Powers the Pi via Ethernet | Eliminates the need for a separate USB-C power adapter. The Pi draws power directly from the TP-Link switch's PoE port. This is how enterprise sensors and IP cameras are deployed — single-cable for data and power. Cleaner setup, fewer failure points. |
| 0x3.2.E | SanDisk Micro SD Extreme 64 GB | Pi boot drive and local storage | The Pi boots from this card. 64 GB is sufficient for Raspberry Pi OS Lite, Suricata, Python agent, and temporary log buffer before shipping to Ubuntu. The Extreme line has the write speeds needed for Suricata log output. |
| 0x3.2.F | SSK 256 GB External SSD (USB 3.2 Gen2, 550 MB/s) | Fast external storage for Docker volumes on Ubuntu | The Ubuntu PC's internal 500 GB disk is likely an HDD (Hard Disk Drive) given the machine's age. OpenSearch performance depends heavily on disk I/O. By mounting this SSD as the Docker volume store, OpenSearch indexes, ChromaDB vector data, and ML model files all read/write at SSD speeds. This is a meaningful performance upgrade for approximately $30. |
| 0x3.2.G | USB 3.0 to Gigabit Ethernet Adapter (Cable Matters) | Wired network connection for the Acer Aspire 5 | The Acer will run Ubuntu Server with no GUI, so WiFi configuration is less convenient. This adapter gives the Acer a reliable Gigabit wired connection to the switch. It also supports PXE (Preboot Execution Environment) boot and MAC clone — enterprise features that are nice to have. |
| 0x3.2.H | 4K HDMI to Micro HDMI cable | Pi display during initial setup | You need a display connection for the Pi's first boot and OS installation. After initial setup, you will SSH into the Pi exclusively and this cable goes into a drawer. |
| 0x3.2.I | Extra mouse + keyboard | Input for Pi and Ubuntu during initial setup | Same as above — needed for first boot only. After SSH is configured, these are no longer needed. |
| 0x3.2.J | USB-C cables (2x Thunderbolt 5, 2x USB-C 480 Mbps) | SSD and peripheral connectivity | The Thunderbolt cables are for the SSD connection to Ubuntu (use the fastest cable). The USB-C 480 Mbps cables are spares or for charging. |
| 0x3.2.K | Monitor(s) | Display for Pi and Ubuntu during initial setup | Used for initial OS installation and configuration. After SSH is working, you do everything from the Dell. |

### 0x3.3 — Software and API Costs

| # | Item | Cost | Notes |
|---|---|---|---|
| 0x3.3.A | All operating systems (Raspberry Pi OS Lite, Ubuntu Server 24.04 LTS) | Free | Open source |
| 0x3.3.B | Suricata 7.x IDS | Free | Open source, maintained by OISF (Open Information Security Foundation) |
| 0x3.3.C | OpenSearch 2.x + OpenSearch Dashboards | Free | Open-source fork of Elasticsearch/Kibana, maintained by AWS and community |
| 0x3.3.D | Ollama + Phi-3 Mini SLM | Free | Ollama is open-source local LLM runtime; Phi-3 Mini is MIT-licensed by Microsoft |
| 0x3.3.E | ChromaDB | Free | Open-source vector database |
| 0x3.3.F | LangChain, FastAPI, scikit-learn, Grafana | Free | All open source |
| 0x3.3.G | Docker + Docker Compose | Free | Open source |
| 0x3.3.H | Custom domain name (e.g., alfredo-security.dev) | ~$12/year | For your portfolio website via GitHub Pages. Use a `.dev` or `.io` domain — it signals technical credibility. Register through Cloudflare Registrar (cheapest, no markup) or Namecheap. |
| 0x3.3.I | GitHub Pro (optional) | Free for public repos | You will keep this project public to showcase it. GitHub Free is sufficient. |

**Total additional spend:** ~$12/year for a domain. Everything else is free and open source.

### 0x3.4 — Recommended Additional Purchase

| # | Item | Estimated Cost | Why |
|---|---|---|---|
| 0x3.4.A | 4 GB or 8 GB RAM stick for Acer Aspire 5 (if upgradeable) | $15–$30 | 4 GB RAM on the Acer is tight for Ubuntu Server + attack tools + OT simulator running simultaneously. If the Acer supports RAM upgrades (check the Crucial memory advisor tool for your model), adding a stick would make the adversary node more comfortable. This is optional — the project works with 4 GB if you run tools sequentially rather than simultaneously. |

---

## 0x4 — Folder Architecture

### 0x4.1 — Project Repository Structure

```
hungryhounddog/
│
├── README.md                          # Project overview, architecture diagram, quick start
├── LICENSE                            # MIT License (open source, employer-friendly)
├── .gitignore                         # Excludes logs, models, Docker volumes, secrets
├── docker-compose.yml                 # Orchestrates all Brain services
├── .env.example                       # Template for environment variables (no secrets committed)
│
├── docs/                              # All documentation lives here
│   ├── architecture/
│   │   ├── system-overview.md         # High-level architecture narrative
│   │   ├── network-topology.md        # Network diagram and data flow explanation
│   │   └── design-decisions.md        # Why each technology was chosen (interview prep)
│   ├── runbooks/
│   │   ├── sensor-deployment.md       # How to deploy the Pi sensor from scratch
│   │   ├── server-setup.md            # How to stand up the Brain server
│   │   ├── adversary-setup.md         # How to configure the adversary node
│   │   └── troubleshooting.md         # Common issues and their fixes
│   └── portfolio/
│       ├── resume-bullets.md          # Pre-written resume lines from this project
│       └── interview-stories.md       # STAR-format talking points
│
├── sensor/                            # Everything that runs on the Raspberry Pi
│   ├── config/
│   │   └── suricata/
│   │       ├── suricata.yaml          # Main Suricata configuration
│   │       └── rules/
│   │           └── custom-ot.rules    # Custom rules for Modbus/OT protocol detection
│   ├── agent/
│   │   ├── log_shipper.py             # Reads Suricata JSON logs, ships to Brain via HTTPS
│   │   ├── health_check.py            # Reports sensor status to Brain
│   │   └── config.yaml                # Agent configuration (Brain endpoint, intervals)
│   └── scripts/
│       └── install.sh                 # Sensor bootstrapping script
│
├── server/                            # Everything that runs on the Ubuntu PC (via Docker)
│   ├── docker/
│   │   ├── opensearch/
│   │   │   └── opensearch.yml         # OpenSearch node configuration
│   │   ├── grafana/
│   │   │   └── provisioning/
│   │   │       ├── datasources/       # Auto-configure OpenSearch as data source
│   │   │       └── dashboards/        # Pre-built dashboard JSON files
│   │   └── chromadb/
│   │       └── config.yaml            # ChromaDB persistence configuration
│   ├── ingestion/
│   │   ├── api/
│   │   │   ├── main.py                # FastAPI app — receives logs from sensor
│   │   │   ├── models.py              # Pydantic data models for log events
│   │   │   └── routes/
│   │   │       ├── ingest.py          # POST /ingest — log ingestion endpoint
│   │   │       └── health.py          # GET /health — server health endpoint
│   │   └── parsers/
│   │       ├── suricata_parser.py     # Normalizes Suricata EVE JSON
│   │       └── ot_parser.py           # Parses OT-specific protocol fields
│   ├── detection/
│   │   ├── ml/
│   │   │   ├── train.py               # Train Isolation Forest on baseline traffic
│   │   │   ├── predict.py             # Score incoming flows for anomalies
│   │   │   ├── features.py            # Feature extraction from network flows
│   │   │   └── models/                # Saved model files (.joblib)
│   │   └── rules/
│   │       └── correlation.py         # Rule-based alert correlation logic
│   ├── ai/
│   │   ├── rag/
│   │   │   ├── indexer.py             # Embeds log data into ChromaDB
│   │   │   ├── query_engine.py        # Retrieves relevant context for LLM queries
│   │   │   └── prompts/
│   │   │       └── security_analyst.txt  # System prompt for the security chatbot
│   │   └── chatbot/
│   │       ├── interface.py           # CLI + simple web UI for the chatbot
│   │       └── ollama_client.py       # Wrapper for Ollama API calls
│   └── alerts/
│       ├── alert_manager.py           # Processes ML anomalies + Suricata alerts
│       └── notifiers/
│           └── webhook.py             # Sends alerts (extensible: Slack, email, etc.)
│
├── adversary/                         # Everything that runs on the Acer
│   ├── playbooks/
│   │   ├── 01_recon_scan.py           # Network discovery and port scanning
│   │   ├── 02_modbus_read.py          # Legitimate Modbus read (baseline)
│   │   ├── 03_modbus_write_attack.py  # Unauthorized Modbus write (attack)
│   │   ├── 04_brute_force.py          # SSH/service brute force simulation
│   │   ├── 05_data_exfil.py           # Simulated data exfiltration
│   │   └── 06_lateral_movement.py     # Simulated lateral movement attempts
│   ├── ot_simulator/
│   │   ├── modbus_server.py           # Modbus TCP server (simulates PLC/RTU)
│   │   └── mqtt_publisher.py          # MQTT telemetry publisher (simulates OT device)
│   ├── traffic_gen/
│   │   └── baseline_traffic.py        # Generates normal-looking network traffic
│   └── scripts/
│       └── install.sh                 # Adversary node bootstrapping script
│
├── switch/                            # Switch configuration documentation
│   └── config/
│       └── sg2008p-config.md          # Port mirroring, VLAN settings, PoE allocation
│
├── scripts/                           # Cross-device utility scripts
│   ├── deploy_all.sh                  # Deploy/update all nodes from Dev Box
│   ├── health_check_all.sh            # Check status of all components
│   └── backup.sh                      # Backup configurations and data
│
└── tests/                             # Validation and integration tests
    ├── test_ingestion.py              # Verify logs flow from sensor to OpenSearch
    ├── test_detection.py              # Verify ML model produces anomaly scores
    ├── test_rag.py                    # Verify chatbot returns relevant answers
    └── test_adversary.py              # Verify attack playbooks trigger alerts
```

### 0x4.2 — Why This Structure

- **0x4.2.A — Device-based top-level directories (sensor/, server/, adversary/):** Each device has its own directory with everything it needs. This makes deployment straightforward — you copy the relevant directory to the relevant device. It also mirrors how enterprise codebases separate microservices.
- **0x4.2.B — docs/ with portfolio/ subdirectory:** The portfolio documentation is built alongside the project, not as an afterthought. The resume-bullets.md and interview-stories.md files are part of the deliverable. Employers browsing your GitHub will see you think about communication, not just code.
- **0x4.2.C — docker-compose.yml at root:** A single `docker-compose up` on the Ubuntu PC starts all server-side services. This is the expected pattern for containerized applications and demonstrates Docker Compose fluency.
- **0x4.2.D — tests/ directory:** Having tests shows engineering maturity. Even basic integration tests that verify "logs go in, alerts come out" demonstrate you think about reliability.
- **0x4.2.E — switch/ directory:** Documenting your switch configuration shows you understand network infrastructure, not just software. Most portfolio projects ignore the network layer entirely.

---

## 0x5 — Technology Stack Overview

### 0x5.1 — Sensor Technologies (Raspberry Pi 4)

| # | Technology | What It Does | Why Chosen Over Alternatives | Maturity | Constraints on Your Hardware |
|---|---|---|---|---|---|
| 0x5.1.A | **Raspberry Pi OS Lite 64-bit** (Debian-based, no GUI) | Operating system for the Pi | Lite edition has no desktop environment, saving ~500 MB RAM. 64-bit enables better Suricata performance vs. 32-bit. Official Pi OS has the best hardware support. | Stable, LTS (Long Term Support) | None — designed for this hardware |
| 0x5.1.B | **Suricata 7.x** | Network IDS — inspects packets, matches rules, generates alerts and flow logs | Industry standard alongside Snort. Suricata has native multi-threading (uses all 4 Pi cores), native JSON EVE log output (easier to parse than Snort's), and is the IDS used by most commercial SIEM platforms. Zeek was considered but is heavier and less relevant to IDS-focused job roles. | Very mature, OISF-maintained | 2 GB RAM is the main constraint. Suricata on home traffic (~1–10 Mbps) is well within budget. Disable heavyweight features (file extraction, Lua scripting) to stay lean. |
| 0x5.1.C | **Custom Python log shipping agent** | Reads Suricata EVE JSON logs, batches them, ships to Brain over HTTPS | Filebeat (Elastic's log shipper) was considered but adds ~200 MB RAM. A custom Python agent is lighter, more educational (you write it yourself), and gives you a portfolio-worthy Python project. | Custom (your code) | Minimal — Python is very lightweight |

### 0x5.2 — Server Technologies (Ubuntu PC "The Brain")

| # | Technology | What It Does | Why Chosen Over Alternatives | Maturity | Constraints on Your Hardware |
|---|---|---|---|---|---|
| 0x5.2.A | **Docker + Docker Compose** | Containerizes all server services | Industry standard for deployment. Lets you `docker-compose up` to start everything. Demonstrates containerization skills that every DevSecOps role requires. Avoids "it works on my machine" problems. | Very mature | Docker overhead is ~200 MB RAM. Acceptable. |
| 0x5.2.B | **OpenSearch 2.x** (single node) | Log storage, full-text search, and analytics engine | OpenSearch is the open-source fork of Elasticsearch, maintained by AWS and a large community. It is functionally equivalent to Elasticsearch for resume purposes. Splunk is proprietary and expensive. Loki was considered but lacks the rich query language (DSL) that SIEM roles require. | Mature, enterprise-adopted | Configure JVM heap to 4 GB max (`-Xms4g -Xmx4g`). Single-node mode. Store data on the external SSD for I/O performance. |
| 0x5.2.C | **Grafana** | Dashboard and visualization | Grafana is the most widely used open-source dashboarding tool. It natively supports OpenSearch as a data source. Lighter than OpenSearch Dashboards (~200 MB vs ~1 GB RAM) and more versatile (can also display ML metrics and system health). | Very mature | Minimal footprint |
| 0x5.2.D | **Ollama** | Local LLM/SLM serving runtime | Ollama makes running local models trivially easy (one command to pull and run). No API keys, no cloud dependency, no data leaving your network. It handles model quantization, memory management, and provides a simple REST API. | Rapidly maturing, very popular | CPU-only inference on i5-6500. Responses take 5–15 seconds, which is acceptable for a security chatbot (not a real-time tool). |
| 0x5.2.E | **Phi-3 Mini 3.8B (4-bit quantized)** | The SLM that answers natural language security queries | Phi-3 Mini by Microsoft is the best SLM in the 3–4B parameter range for reasoning tasks. At 4-bit quantization, it uses ~2.5 GB RAM — well within your budget. Larger models (Mistral 7B at ~4.5 GB, Llama 3 8B at ~5 GB) are possible but leave less headroom. Start with Phi-3 Mini; upgrade if RAM allows. | Stable release | CPU inference is slow but functional. Quality is sufficient for structured security Q&A when paired with good RAG context. |
| 0x5.2.F | **ChromaDB** | Vector database for RAG | Simplest vector DB to set up — runs embedded or as a lightweight server. Stores embeddings of log data and alert summaries for semantic retrieval. Alternatives (Weaviate, Pinecone, Milvus) are heavier or cloud-dependent. | Maturing rapidly | Low RAM usage (~300–500 MB). Stores on disk (external SSD). |
| 0x5.2.G | **LangChain (Python)** | RAG orchestration framework | Connects the retriever (ChromaDB), the LLM (Ollama/Phi-3), and the prompt template into a pipeline. It is the most widely adopted RAG framework with extensive documentation. Alternatives (LlamaIndex, Haystack) are viable but LangChain has the largest community and job market recognition. | Mature | None — pure Python library |
| 0x5.2.H | **FastAPI (Python)** | REST API framework for log ingestion and chatbot interface | Fastest Python web framework (async), auto-generates OpenAPI docs, excellent type validation with Pydantic. Flask was considered but FastAPI is more modern and increasingly preferred in industry. | Very mature | Minimal footprint |
| 0x5.2.I | **scikit-learn (Python) — Isolation Forest** | ML anomaly detection on network flows | Isolation Forest is the standard algorithm for unsupervised anomaly detection. It requires no labeled attack data (you train on "normal" traffic, and it flags deviations). scikit-learn is the most battle-tested ML library in Python. Deep learning (TensorFlow, PyTorch) was considered but is overkill for tabular flow data and would consume too much RAM/CPU. | Very mature | Training is fast on tabular data. Prediction is near-instant. No GPU needed. |

### 0x5.3 — Adversary Technologies (Acer Aspire 5)

| # | Technology | What It Does | Why Chosen Over Alternatives | Maturity | Constraints on Your Hardware |
|---|---|---|---|---|---|
| 0x5.3.A | **Ubuntu Server 24.04 LTS** (no GUI) | Operating system for the adversary node | No desktop environment saves ~1.5 GB RAM — critical on a 4 GB machine. Kali Linux was considered but its full desktop uses too much RAM, and you only need a handful of its tools which you can install individually on Ubuntu. You SSH into this machine from the Dell. | Stable, LTS | ~500 MB OS overhead leaves ~3.4 GB for tools |
| 0x5.3.B | **pymodbus (Python)** | Modbus TCP server and client for OT protocol simulation | Simulates a PLC (Programmable Logic Controller) or RTU (Remote Terminal Unit) that speaks Modbus TCP — the most common OT protocol. Your attack playbooks will read/write Modbus registers to simulate both legitimate and malicious OT traffic. This is what makes the project OT-focused instead of generic IT security. | Mature | Very lightweight |
| 0x5.3.C | **Mosquitto MQTT Broker** | MQTT (Message Queuing Telemetry Transport) broker for IoT/OT telemetry | Simulates IoT sensor data publishing — common in modern OT environments. Lightweight and well-documented. | Very mature | ~10 MB RAM |
| 0x5.3.D | **nmap** | Network scanning and discovery | Industry-standard reconnaissance tool. Your playbooks will use nmap for port scanning that should trigger Suricata alerts. | Very mature | Minimal |
| 0x5.3.E | **scapy (Python)** | Packet crafting and custom protocol manipulation | Lets you craft arbitrary packets for advanced attack simulation — spoofed sources, malformed OT protocol packets, etc. More flexible than pre-built tools. | Mature | Minimal |
| 0x5.3.F | **hydra** | Brute force simulation | Simulates credential stuffing attacks against services. Triggers alert rules in Suricata. | Mature | Minimal |

### 0x5.4 — Development and Infrastructure Technologies

| # | Technology | What It Does | Why Chosen |
|---|---|---|---|
| 0x5.4.A | **Git + GitHub** | Version control and portfolio hosting | Your project repository IS your portfolio. Employers will browse this. GitHub Actions can run basic CI (Continuous Integration) tests. |
| 0x5.4.B | **VS Code + SSH Remote Extension** | IDE with remote development | Code on your Dell, execute on any device via SSH. Industry-standard development workflow. |
| 0x5.4.C | **GitHub Pages + Custom Domain** | Portfolio website | Free static hosting. A custom `.dev` domain (e.g., `alfredo-security.dev`) makes your portfolio look professional. |

---

## 0x6 — Skills Map

### 0x6.1 — Skills by Project Phase

| # | Phase / Weekend | Skills Learned or Deepened | Target Job Requirement Mapping |
|---|---|---|---|
| 0x6.1.A | Weekend 1 — Foundation | Linux system administration, OS installation, SSH key management, network interface configuration, Git repository setup, managed switch configuration (VLANs, port mirroring) | Every security role: Linux proficiency, network fundamentals, version control |
| 0x6.1.B | Weekend 2 — Sensor | Suricata IDS deployment and tuning, passive network monitoring, promiscuous mode, IDS rule syntax, log format understanding (EVE JSON) | Detection Engineer, SOC Analyst, Network Security Engineer |
| 0x6.1.C | Weekend 3 — Central Server | Docker Compose, OpenSearch deployment, FastAPI development, API design, log ingestion pipeline, Python Pydantic data models | Security Engineer, DevSecOps Engineer, Platform Engineer |
| 0x6.1.D | Weekend 4 — Adversary | OT protocol understanding (Modbus TCP, MQTT), attack simulation, MITRE ATT&CK for ICS framework, red team methodology, nmap/scapy usage | OT Security Engineer, Penetration Tester, ICS Security Analyst |
| 0x6.1.E | Weekend 5 — ML Detection | Feature engineering on network data, unsupervised anomaly detection (Isolation Forest), model training and evaluation, scikit-learn pipeline | AI Security Analyst, Detection Engineer, ML Security Engineer |
| 0x6.1.F | Weekend 6 — AI/RAG Chatbot | LLM/SLM deployment, RAG architecture, vector embeddings, ChromaDB, LangChain, prompt engineering for security domain | AI Security Analyst, Security AI Engineer — directly maps to Security AI+ cert material |
| 0x6.1.G | Weekend 7 — Integration | Grafana dashboard design, end-to-end system testing, performance tuning, incident response workflow design | SOC Engineer, Security Operations Engineer |
| 0x6.1.H | Weekend 8 — Portfolio | Technical writing, architecture documentation, resume optimization, GitHub portfolio curation, demo creation | All roles: communication skills differentiate candidates |

### 0x6.2 — Security AI+ Certification Overlap

| # | Security AI+ Domain | HungryHoundDog Component That Covers It |
|---|---|---|
| 0x6.2.A | AI-driven threat detection | ML Isolation Forest anomaly detection on network flows |
| 0x6.2.B | LLM security considerations | Prompt engineering with guardrails for the security chatbot; understanding LLM limitations in security contexts |
| 0x6.2.C | RAG architecture and applications | ChromaDB + LangChain RAG pipeline for security log querying |
| 0x6.2.D | AI model deployment and operations | Ollama local model serving, Docker containerization |
| 0x6.2.E | Security monitoring and automation | End-to-end pipeline: detect → alert → investigate via AI chatbot |
| 0x6.2.F | Data privacy in AI systems | All data stays local (no cloud APIs), demonstrating on-premises AI deployment |

---

## 0x7 — Weekend Schedule (High-Level)

*Assuming start date: Weekend of March 1, 2026. Each weekend = Saturday + Sunday, ~8 hours per day = ~16 hours per weekend.*

### Weekend 1 (Mar 1–2): Foundation and Network Backbone

**Theme:** "Build the physical infrastructure — every cable, every port, every IP."

| # | Objective | Success Criteria |
|---|---|---|
| 0x7.1.A | Install Raspberry Pi OS Lite (64-bit) on MicroSD, boot Pi, enable SSH, connect via PoE through switch | Pi is powered via PoE, accessible via SSH from Dell over WiFi (wlan0) |
| 0x7.1.B | Install Ubuntu Server 24.04 LTS on Acer Aspire 5 (wipe existing OS) | Acer boots to Ubuntu Server, accessible via SSH from Dell |
| 0x7.1.C | Configure TP-Link SG2008P switch: set up port mirroring (Port 1 → Port 3), create VLAN 10 (OT) and VLAN 20 (Mgmt), assign ports | Port mirroring verified — traffic on Port 1 appears on Port 3 |
| 0x7.1.D | Configure Pi network: eth0 in promiscuous mode (no IP), wlan0 with static IP on home WiFi | Pi can capture traffic on eth0 while communicating on wlan0 |
| 0x7.1.E | Mount external SSD on Ubuntu PC, format and configure as Docker volume store | SSD mounted at `/mnt/ssd`, verified with write speed test |
| 0x7.1.F | Initialize Git repo, push initial folder structure to GitHub from Dell, configure SSH keys on all devices | All four devices can push/pull from the repo |

**Dependencies for next weekend:** Pi accessible via SSH, switch mirroring working, Git repo initialized.

---

### Weekend 2 (Mar 7–8): Sensor Deployment — Suricata on the Pi

**Theme:** "Get eyes on the network — see every packet."

| # | Objective | Success Criteria |
|---|---|---|
| 0x7.2.A | Install Suricata on Pi, configure to listen on eth0 in IDS mode with EVE JSON logging | Suricata running, producing eve.json logs when traffic passes through the mirrored port |
| 0x7.2.B | Install ET Open (Emerging Threats Open) ruleset | Suricata detects common threats using community rules |
| 0x7.2.C | Write initial custom Suricata rules for Modbus TCP detection | Custom rules file created (they will be tested in Weekend 4) |
| 0x7.2.D | Build Python log shipping agent: watches eve.json, batches events, POSTs to Brain endpoint (stub for now — Brain not yet running) | Agent runs, reads logs, formats JSON batches. Test by writing batches to a local file. |
| 0x7.2.E | Build Python health-check agent: reports Pi system metrics (CPU, RAM, disk, Suricata process status) | Health-check script runs and outputs JSON status |

**Dependencies for next weekend:** Suricata producing JSON logs, log shipper ready to send to an endpoint.

---

### Weekend 3 (Mar 14–15): Central Server Core — Docker, OpenSearch, Ingestion

**Theme:** "Build the brain — receive, store, and search security data."

| # | Objective | Success Criteria |
|---|---|---|
| 0x7.3.A | Install Docker and Docker Compose on Ubuntu PC | `docker-compose --version` works |
| 0x7.3.B | Create docker-compose.yml with OpenSearch (single node, 4 GB heap) and Grafana | Both services start and are accessible via browser from Dell |
| 0x7.3.C | Build FastAPI log ingestion service: POST /ingest endpoint that receives JSON logs and indexes them into OpenSearch | Logs sent via curl from Dell appear in OpenSearch |
| 0x7.3.D | Connect Pi log shipper to Brain's FastAPI endpoint | Suricata alerts from Pi appear in OpenSearch within seconds |
| 0x7.3.E | Create first Grafana dashboard: alert timeline, top source IPs, event count over time | Dashboard shows live data from Suricata |

**Milestone: End-to-end pipeline working.** Traffic on the switch → captured by Suricata → shipped to Brain → indexed in OpenSearch → visible in Grafana. This is the core loop.

**Dependencies for next weekend:** Ingestion pipeline running, OpenSearch populated with log data.

---

### Weekend 4 (Mar 21–22): Adversary Simulation — OT Protocols and Attack Playbooks

**Theme:** "Be the attacker — then watch yourself get caught."

| # | Objective | Success Criteria |
|---|---|---|
| 0x7.4.A | Deploy Modbus TCP server on Acer (pymodbus) simulating a PLC with readable/writable registers | Modbus server running, responds to read/write requests |
| 0x7.4.B | Deploy Mosquitto MQTT broker on Acer, create a publisher script sending simulated OT telemetry | MQTT messages flowing on the network |
| 0x7.4.C | Write attack playbook #1: nmap port scan of the entire lab network | Suricata fires alerts for port scan activity |
| 0x7.4.D | Write attack playbook #2: unauthorized Modbus register write | Suricata fires custom OT rule alert |
| 0x7.4.E | Write attack playbook #3: SSH brute force (hydra) against Pi and Ubuntu | Suricata fires brute force alerts |
| 0x7.4.F | Run baseline traffic generator to create "normal" OT traffic patterns | Normal Modbus reads and MQTT publishes flowing regularly — this is training data for ML |

**Dependencies for next weekend:** Labeled normal and attack traffic in OpenSearch for ML training.

---

### Weekend 5 (Mar 28–29): ML Anomaly Detection

**Theme:** "Teach the machine what normal looks like — so it can spot the abnormal."

| # | Objective | Success Criteria |
|---|---|---|
| 0x7.5.A | Build feature extraction pipeline: extract features from Suricata flow logs (bytes in/out, packet count, duration, port, protocol, time-of-day) | Feature extraction script produces clean CSV/DataFrame from OpenSearch flow data |
| 0x7.5.B | Train Isolation Forest model on baseline (normal) traffic from Weekend 4 | Model saved as .joblib file with documented baseline metrics |
| 0x7.5.C | Test model against attack traffic — verify anomalies are scored correctly | Attack flows receive anomaly scores significantly different from normal flows |
| 0x7.5.D | Integrate ML scoring into the ingestion pipeline: new flows are scored in near-real-time | Anomaly scores appear as a field in OpenSearch documents |
| 0x7.5.E | Add anomaly score visualization to Grafana dashboard | Dashboard shows anomaly score timeline, thresholds, and highlighted detections |
| 0x7.5.F | Write remaining attack playbooks (#4 data exfiltration, #5 lateral movement) and verify detection | ML detects deviations from baseline for new attack types |

**Dependencies for next weekend:** ML model running, ChromaDB will need indexed data (now available in OpenSearch).

---

### Weekend 6 (Apr 4–5): AI/RAG Security Chatbot

**Theme:** "Ask your network what happened — in plain English."

| # | Objective | Success Criteria |
|---|---|---|
| 0x7.6.A | Add Ollama container to docker-compose.yml, pull Phi-3 Mini (4-bit quantized) | `ollama run phi3:mini` produces coherent responses on Ubuntu |
| 0x7.6.B | Add ChromaDB container to docker-compose.yml | ChromaDB accessible via API |
| 0x7.6.C | Build RAG indexer: reads recent alerts and flow summaries from OpenSearch, generates embeddings, stores in ChromaDB | ChromaDB populated with embedded security log data |
| 0x7.6.D | Build LangChain query engine: takes natural language input → retrieves relevant context from ChromaDB → constructs prompt → sends to Ollama → returns answer | Chatbot answers questions like "What Modbus anomalies occurred today?" with specific, context-grounded answers |
| 0x7.6.E | Write security-focused system prompt with guardrails | Chatbot stays on-topic (security analysis only), provides structured answers with timestamps and severity |
| 0x7.6.F | Build simple web UI for the chatbot (FastAPI + basic HTML/JS) or CLI interface | User can type questions and receive formatted security analysis |

**Dependencies for next weekend:** All components running; integration testing needed.

---

### Weekend 7 (Apr 11–12): Integration, Dashboards, and Hardening

**Theme:** "Polish the machine — make every piece work together flawlessly."

| # | Objective | Success Criteria |
|---|---|---|
| 0x7.7.A | Full integration test: run all attack playbooks → verify detection (Suricata alerts + ML anomalies) → verify chatbot can answer questions about the attacks | End-to-end attack → detect → investigate cycle works |
| 0x7.7.B | Build comprehensive Grafana dashboard: network overview, alert severity distribution, anomaly scores over time, sensor health, OT protocol traffic volume | Dashboard tells a complete security story at a glance |
| 0x7.7.C | Add alert notification system (webhook to a simple endpoint, or log to file) | High-severity alerts trigger notifications |
| 0x7.7.D | Performance tuning: optimize OpenSearch queries, tune Suricata buffer sizes, adjust ML prediction frequency | System runs stably for 1+ hours under continuous attack simulation |
| 0x7.7.E | Security hardening: HTTPS on all APIs, SSH key-only auth, firewall rules on each device | No plaintext credentials, no unnecessary open ports |

**Dependencies for next weekend:** System is stable and demonstrable.

---

### Weekend 8 (Apr 18–19): Documentation, Portfolio, and Launch

**Theme:** "Package the work — make it impossible for employers to ignore."

| # | Objective | Success Criteria |
|---|---|---|
| 0x7.8.A | Write comprehensive README.md with architecture diagram, quick start guide, feature list, screenshots | Someone can understand the project in 2 minutes by reading the README |
| 0x7.8.B | Write design-decisions.md explaining every technology choice and trade-off | Shows technical depth and engineering judgment |
| 0x7.8.C | Write resume-bullets.md and interview-stories.md | 5+ STAR-format stories ready for interviews |
| 0x7.8.D | Record a 3–5 minute demo video: show attack → detection → dashboard alert → chatbot investigation | Video uploaded to YouTube (unlisted or public) and linked in README |
| 0x7.8.E | Create GitHub Pages portfolio site with project showcase, resume, and contact info | Live at your custom domain (e.g., alfredo-security.dev) |
| 0x7.8.F | Update LinkedIn: add project to Featured section, update headline and About to reflect AI security focus | LinkedIn reflects your new positioning |
| 0x7.8.G | Push final, clean codebase to GitHub | Repository is clean, well-commented, and ready for employer review |

---

## 0x8 — How This Gets You Hired

### 0x8.1 — What Employers See When They Review Your GitHub

When a hiring manager or technical interviewer visits your GitHub, they will see:

- **0x8.1.A** — A professional README with an architecture diagram that immediately communicates you think in systems, not just scripts.
- **0x8.1.B** — A multi-device distributed deployment — not the typical "everything runs on my laptop" portfolio project. This signals real infrastructure experience.
- **0x8.1.C** — OT protocol simulation (Modbus TCP, MQTT) — a rare skill that immediately sets you apart from IT-only candidates.
- **0x8.1.D** — AI/ML integration that serves a genuine security purpose — anomaly detection and natural language log analysis, not a chatbot for the sake of having a chatbot.
- **0x8.1.E** — A docs/ directory with runbooks, design decisions, and architecture documentation — signaling you can communicate technical decisions to stakeholders.
- **0x8.1.F** — A docker-compose.yml that orchestrates 5+ services — demonstrating containerization fluency.
- **0x8.1.G** — Tests — even basic ones signal engineering discipline.
- **0x8.1.H** — Active commit history over 8 weekends — showing consistent effort and iteration, not a weekend copy-paste job.

### 0x8.2 — Interview Talking Points

| # | Talking Point | What It Demonstrates |
|---|---|---|
| 0x8.2.A | "I architected a distributed security monitoring platform across four physical devices with dedicated sensor, analytics, and adversary nodes connected through a managed switch with port mirroring and VLAN segmentation." | Systems thinking, network architecture, enterprise design patterns |
| 0x8.2.B | "I deployed Suricata as a passive IDS on a Raspberry Pi powered via PoE, with a separate monitoring and management interface — the same architecture used in enterprise OT sensor deployments." | OT security depth, IDS expertise, network deployment best practices |
| 0x8.2.C | "I built a RAG-powered chatbot that lets analysts query security posture in natural language — similar to the vendor integration I'm leading at UPS for LLM-based network security querying." | AI integration, RAG architecture, direct enterprise relevance |
| 0x8.2.D | "I implemented unsupervised ML anomaly detection using Isolation Forest on network flow features, trained on baseline OT traffic, achieving reliable detection of port scans, unauthorized Modbus writes, and data exfiltration simulations." | ML for security, feature engineering, practical AI application |
| 0x8.2.E | "I created adversary simulation playbooks mapped to MITRE ATT&CK for ICS tactics, including reconnaissance, OT protocol exploitation, brute force, and data exfiltration." | Threat modeling, red team awareness, OT threat landscape knowledge |
| 0x8.2.F | "I containerized the entire server stack with Docker Compose — OpenSearch, Grafana, Ollama, ChromaDB, and custom Python services — achieving single-command deployment." | DevSecOps, containerization, infrastructure as code |

### 0x8.3 — Job Application Timeline

| # | Timeframe | Action |
|---|---|---|
| 0x8.3.A | Now – Mid-April | Build HungryHoundDog (8 weekends). Study Security AI+ on weekdays. |
| 0x8.3.B | Late April | Polish GitHub repo, record demo video, launch portfolio site. Write 2–3 targeted cover letter templates. |
| 0x8.3.C | May | Begin targeted job applications (10–15 per week). Focus on roles at critical infrastructure companies, defense contractors, and cloud security firms. Start networking on LinkedIn — comment on OT security and AI security posts. |
| 0x8.3.D | June | Ramp up applications (15–20 per week). Practice technical interviews — focus on system design, network security scenarios, and explaining your project. Apply to both remote and Atlanta-area positions. |
| 0x8.3.E | July | Pass CompTIA Security AI+ exam (target: end of July). Add certification to resume immediately. Intensify applications with the new cert listed. |
| 0x8.3.F | August | Target month for offer acceptance. If no offer by August 15, expand search to contract roles, consulting firms, and adjacent roles (Security Automation Engineer, Detection Engineer). |
| 0x8.3.G | September (contingency) | Continue applying. Consider reaching out to OT security consulting firms (Dragos, Claroty, Nozomi Networks) directly — they value OT experience highly and are frequently hiring. |

### 0x8.4 — Target Role Titles to Search For

Search for these titles on LinkedIn, Indeed, and company career pages. They are ordered from most likely to match your profile to stretch roles:

| # | Role Title | Why It Fits | Salary Range Estimate |
|---|---|---|---|
| 0x8.4.A | OT Security Engineer | Directly maps to your UPS OT work + this project. High-demand niche. | $130K–$180K (remote possible at some firms) |
| 0x8.4.B | ICS/SCADA Security Analyst | OT-focused analyst role. Your CrowdStrike + Modbus experience is a strong fit. | $120K–$160K |
| 0x8.4.C | Detection Engineer | Focuses on writing detection rules and building detection pipelines — exactly what Suricata + ML anomaly detection in this project demonstrates. | $140K–$190K |
| 0x8.4.D | Security Engineer (AI/ML) | Combines security + AI. Your RAG chatbot and ML detection make you a candidate. | $150K–$200K+ |
| 0x8.4.E | Security Automation Engineer | Focuses on automating security workflows with Python — your ingestion pipeline, alert manager, and playbooks demonstrate this. | $130K–$170K |
| 0x8.4.F | Network Security Engineer | Leverages your 8 years of network configuration + this project's architecture. | $130K–$175K |
| 0x8.4.G | Security Operations Engineer / SOC Engineer | Builds and maintains SOC infrastructure — your project IS a miniature SOC. | $120K–$160K |
| 0x8.4.H | AI Security Analyst | Emerging title. Your Security AI+ cert + RAG project + ML detection make you competitive. | $130K–$170K |

**Reality check:** $150K remote is achievable but competitive — expect to apply to 50–100+ positions. Your strongest differentiation is the OT + AI combination. Most candidates have one or the other, rarely both. $200K+ non-remote is most likely at defense contractors (Raytheon, Lockheed Martin, Northrop Grumman), critical infrastructure companies, large cloud providers (AWS, Azure, GCP security teams), or financial institutions — all of which have offices or opportunities accessible from the Atlanta area.

---

## 0x9 — Risk Assessment

### 0x9.1 — Hardware Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 0x9.1.A | Pi 4 (2 GB RAM) cannot run Suricata under sustained traffic | Low (home traffic is light, ~1–10 Mbps) | High (project stalls) | Disable Suricata features you do not need: file extraction, Lua scripting, protocol logging for non-relevant protocols. Set `stream.memcap` and `flow.memcap` conservatively. Monitor RAM usage in the first weekend. If critically tight, reduce the number of active rule categories. |
| 0x9.1.B | Ubuntu PC (15.5 GB RAM) cannot run all Docker services simultaneously | Medium (tight budget) | High | Budget: OpenSearch 4 GB + Grafana 0.5 GB + Ollama/Phi-3 2.5 GB + ChromaDB 0.5 GB + FastAPI 0.3 GB + ML engine 0.5 GB + OS/Docker 2 GB = ~10.3 GB. You have ~5 GB headroom. If tight, stop Ollama when not actively chatting — it does not need to run 24/7. |
| 0x9.1.C | Acer (4 GB RAM) cannot run attack tools + OT simulator simultaneously | Medium | Low (workaround available) | Run OT simulator as a background service (very lightweight). Run attack tools one at a time rather than simultaneously. Sequential execution is fine for a demo. |
| 0x9.1.D | External SSD fails or disconnects | Low | Medium (data loss) | Mount with `nofail` option so Ubuntu still boots if SSD is disconnected. Keep configuration files in Git (not on SSD). OpenSearch data can be re-indexed from the Pi's log buffer if needed. |

### 0x9.2 — Technology Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 0x9.2.A | Suricata rule tuning is time-consuming and produces too many false positives | High | Medium (eats into time budget) | Start with only the ET Open ruleset categories most relevant to your lab traffic (scan detection, brute force, protocol anomaly). Disable noisy categories (malware, exploit-kit) that are irrelevant to a home lab. Add custom OT rules surgically. |
| 0x9.2.B | OpenSearch single-node is unstable or slow | Medium | Medium | Use the external SSD for data storage. Set `bootstrap.memory_lock: true` to prevent JVM swapping. Limit index shard count. For a single-node lab, these settings are well-documented. |
| 0x9.2.C | Phi-3 Mini produces low-quality chatbot responses | Medium | Low (demo can still work) | The quality of RAG depends more on the retrieval step than the LLM. Focus on good document chunking and relevant context retrieval in ChromaDB. Write a strong system prompt that constrains the model to structured security responses. If Phi-3 Mini quality is insufficient, try Mistral 7B (4-bit, ~4.5 GB) as an upgrade. |
| 0x9.2.D | Docker Compose configuration issues consume excessive troubleshooting time | Medium (first-time Docker users often hit networking/permissions issues) | Medium | Use official Docker images for OpenSearch, Grafana, and ChromaDB — they have well-tested docker-compose examples. Start with a minimal compose file (just OpenSearch) and add services incrementally. Never try to debug 5 containers at once. |
| 0x9.2.E | Port mirroring on TP-Link switch does not work as expected | Low (well-documented feature) | High (blocks sensor data) | Test port mirroring in Weekend 1 before doing anything else. Use `tcpdump` on the Pi's eth0 to verify mirrored traffic appears. If the switch firmware has issues, update it via the Omada web interface. |

### 0x9.3 — Schedule Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 0x9.3.A | A weekend is lost to unexpected issues (hardware failure, illness, life events) | Medium | Medium | The schedule has buffer built into Weekend 7 (integration) and Weekend 8 (documentation). If a weekend is lost, merge that weekend's objectives with the next. The project is viable even if it extends to 9 or 10 weekends — your August job target is not dependent on a mid-April completion. |
| 0x9.3.B | Scope creep — adding features beyond the plan | Medium (your curiosity is high) | Medium | Resist the urge to add features. The plan as written is already ambitious for 128 hours. Every additional feature steals time from documentation and job applications, which are equally important. After the 8 weekends, maintain a "future work" section in the README instead of building more. |
| 0x9.3.C | Underestimating the documentation weekend | High (engineers always underestimate writing time) | High (undocumented project = invisible project) | Weekend 8 is entirely dedicated to documentation and portfolio. Do NOT skip or compress it. A well-documented mediocre project gets you hired faster than an undocumented impressive one. |

---

## 0xA — Critical Reminders

These are things I want you to keep in mind throughout the entire project, Alfredo. Read this section before you start each weekend.

### 0xA.1 — The Project Is a Vehicle, Not the Destination

The goal is not to build a perfect security platform. The goal is to get hired at $150K+ by August. Every decision should be evaluated against: *"Does this make me more hireable, or am I just having fun?"* Fun is fine — but the README, the resume bullets, and the interview stories matter as much as the code.

### 0xA.2 — Commit Early, Commit Often

Make your first Git commit on Day 1. Push to GitHub every time you get something working. Your commit history tells a story of progression that employers can see. A repo with 200 commits over 8 weekends looks radically different from one with 5 commits in the last week.

### 0xA.3 — Document As You Build

Do not save all documentation for Weekend 8. After each weekend, spend the last 30 minutes writing a brief summary of what you built, what you learned, and what decision you made and why. These notes become your design-decisions.md and interview-stories.md almost for free.

### 0xA.4 — Photograph and Screenshot Everything

Take screenshots of your dashboards, your terminal output when an attack is detected, your physical hardware setup. These go into your README, your portfolio site, and your LinkedIn posts. A photo of four physical devices connected to a managed switch with cables is worth a thousand words on a resume.

### 0xA.5 — The OT Angle Is Your Superpower

Most security candidates come from IT backgrounds. Your combination of OT security experience (UPS/CrowdStrike), OT protocol knowledge (Modbus, MQTT), and AI integration is rare. Lean into this in every application and interview. Companies in energy, manufacturing, water treatment, transportation, and defense are desperate for OT security talent.

### 0xA.6 — Do Not Optimize Prematurely

If Suricata is running and producing logs — move on to the next weekend's objectives. If the ML model detects anomalies with 70% accuracy — move on. If the chatbot answers 6 out of 10 questions correctly — move on. You can refine later. Shipping a complete end-to-end system is more impressive than a perfectly tuned component that exists in isolation.

### 0xA.7 — Security AI+ and This Project Are Complementary

When you study Security AI+ on weekdays, you will constantly encounter concepts you implemented over the weekend. This is intentional. The project makes the certification material concrete, and the certification gives you vocabulary to describe what you built. They reinforce each other.

### 0xA.8 — Ask for Help From Me Along the Way

When you reach each weekend, come back and ask me for the detailed implementation guidance for that specific phase. I will give you the step-by-step instructions, configuration details, and code guidance tailored to where you are. This roadmap is the map — the turn-by-turn directions come as you drive.

### 0xA.9 — Your Background Is Stronger Than You Think

You have 8 years of hands-on experience, a BSEE from Georgia Tech, Security+, daily use of CrowdStrike at enterprise scale, and direct involvement in an LLM/RAG security project at UPS. Most candidates at the $150K level do not have this breadth. The project fills the gap between "operates tools" and "builds infrastructure." Once that gap is closed, you are a strong candidate. Do not undersell yourself.

### 0xA.A — Take Care of Yourself

128–150 hours over 8 weekends while studying for a certification and working full-time is a serious commitment. Sleep, eat well, and protect your weekday evenings. Burnout will cost you more time than any technical blocker. If you need a weekend off, take it. The schedule has buffer.

---

*End of Roadmap — HungryHoundDog v1.0*

*"The network sees everything. Build the eyes, teach the brain, and let the hound hunt."*
