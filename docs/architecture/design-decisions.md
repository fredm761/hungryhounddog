# Design Decisions & Technology Rationale

## Intrusion Detection System: Suricata vs Alternatives

### Decision: Suricata IDS/IPS

**Why Suricata:**
1. **OT Protocol Support**: Native Modbus TCP/UDP detection rules; superior to Snort for industrial protocols
2. **Modern Architecture**: Multithreaded, async I/O; better CPU utilization on Raspberry Pi vs older Snort 2.x
3. **EVE JSON Output**: Structured logging ideal for downstream processing; easy parsing for OpenSearch ingestion
4. **Open Source & Active**: Maintained by OISF; community rulesets continuously updated
5. **Low Resource Overhead**: ~50-100MB RAM typical deployment; suitable for edge sensors
6. **IPS Capability**: Can drop/reject packets inline if network allows (future capability)

**Rejected Alternatives:**

| Alternative | Reason for Rejection |
|-------------|----------------------|
| **Snort 2.x** | Aging codebase; Modbus rules less mature; single-threaded performance |
| **Snort 3.x** | Still maturing; less community rule coverage for OT protocols |
| **Zeek** | Designed for enterprise IT networks; verbose output; higher overhead |
| **PicoIDS** | Insufficient rule depth for production OT detection |
| **Cloud SIEM (AWS GuardDuty)** | Air-gap requirement; vendor lock-in; ongoing costs |

---

## Event Indexing & Search: OpenSearch vs Alternatives

### Decision: OpenSearch

**Why OpenSearch:**
1. **Open Source Fork of Elasticsearch**: Maintained by AWS; no subscription fees after v7.9
2. **Full-Text Search**: Powerful query DSL for correlating multi-field log patterns
3. **Plugin Ecosystem**: Alerting, anomaly detection, SQL support available
4. **Scalability**: Horizontal scaling via multiple nodes and shards
5. **Community Support**: Large active community; abundant documentation
6. **Cost Efficiency**: No licensing tier gates; runs on modest hardware
7. **Integration Ready**: Multiple log shipping tools (Filebeat, Fluentd, Logstash)

**Rejected Alternatives:**

| Alternative | Reason for Rejection |
|-------------|----------------------|
| **Elasticsearch (Elastic Cloud)** | Subscription model; ongoing per-GB costs unsustainable for home lab |
| **Splunk** | Premium pricing (~$600+/year); overkill for lab environment |
| **Grafana Loki** | Great for logs but weaker at complex correlation queries vs ES/OpenSearch |
| **ELK Stack (self-hosted Elasticsearch)** | Licensing complexity post-v8.0; SSPL restrictions |
| **QRadar Community** | Resource-intensive; enterprise complexity |

---

## Large Language Model: Phi-3 Mini vs Alternatives

### Decision: Phi-3 Mini (3.8B parameters)

**Why Phi-3 Mini:**
1. **Hardware Efficient**: Runs comfortably on 8GB RAM Ubuntu PC with Ollama (4-bit quantization)
2. **Inference Speed**: ~2-5 second response time suitable for alert analysis (not real-time requirement)
3. **OT Knowledge**: Trained on diverse technical data; good performance on security analysis tasks
4. **Local Deployment**: Zero API costs; privacy-preserving; works offline/air-gapped
5. **MIT License**: Permissive for commercial use in portfolio projects
6. **Active Maintenance**: Regular updates from Microsoft; strong community

**Rejected Alternatives:**

| Alternative | Why Not |
|-------------|---------|
| **GPT-4/Claude API** | Requires internet; ongoing costs ($0.01-0.10/query); privacy concerns for OT data |
| **Llama 2 (7B)** | Larger model = slower inference on consumer hardware; marginal quality gain |
| **Mistral 7B** | Similar sized peer; Phi-3 Mini was smaller with comparable performance at time of selection |
| **Fine-tuned BERT** | Task-specific but requires labeled training data; less flexible for multi-task analysis |
| **Proprietary EdgeAI** | Locked ecosystem; limited extensibility |

**Quantization Strategy:**
- **4-bit (int4)** via Ollama: 3.8B → ~2GB VRAM required
- Accuracy loss: <5% vs FP32; acceptable trade-off for speed

---

## Vector Database: ChromaDB vs Alternatives

### Decision: ChromaDB

**Why ChromaDB:**
1. **Lightweight & Embeddable**: No separate process required; Python library pattern
2. **Persistence Options**: Disk storage for reproducible vector search across sessions
3. **Built-in Embedding Models**: Supports various embedding generators (default: sentence-transformers)
4. **Query Performance**: Sub-millisecond similarity search on 10k+ embeddings
5. **Open Source**: No vendor lock-in; can be replaced if needed
6. **Python Integration**: Native FastAPI compatibility; simple client library
7. **Cost**: Free; no per-query pricing like Pinecone

**Rejected Alternatives:**

| Alternative | Reason for Rejection |
|-------------|----------------------|
| **Pinecone** | Managed service; $0.25/month per million vectors minimum; vendor lock-in |
| **Weaviate** | Slightly larger footprint; more features than needed for MVP |
| **Milvus** | Stronger for distributed deployments; complexity overkill for single node |
| **FAISS** | CPU-only by default; good performance but less user-friendly integration |
| **Redis Search** | Primarily cache; less optimized for semantic similarity than dedicated vector DBs |

**Use Case:**
- Store embeddings of known attack patterns, threat signatures
- Enable semantic similarity search: "Find alerts similar to ransomware behavior"
- Reduce false positives via pattern matching vs rule-based detection alone

---

## API Framework: FastAPI vs Alternatives

### Decision: FastAPI

**Why FastAPI:**
1. **Modern Python**: Async/await native; high performance (rivaling Go, Node.js)
2. **Auto-Documentation**: OpenAPI/Swagger UI generated automatically
3. **Type Hints**: Pydantic validation; catches errors at development time
4. **Easy Integration**: Works seamlessly with Ollama, OpenSearch, ChromaDB Python clients
5. **Deployment**: Single binary via Uvicorn; easy containerization
6. **Developer Experience**: Rapid prototyping with hot-reload during development
7. **Testing**: Built-in test client; pytest-compatible

**Rejected Alternatives:**

| Alternative | Why Not |
|-------------|---------|
| **Flask** | Synchronous by default; requires Celery for async tasks |
| **Django** | Overkill for API-only microservice; ORM overhead |
| **Go (Gin/Echo)** | Steeper learning curve; team Python-proficient |
| **Node.js (Express)** | TypeScript overhead; less natural for ML/scientific computing |
| **ASP.NET Core** | Enterprise-focused; licensing considerations |

**API Endpoints Planned:**
- `GET /alerts` — Query OpenSearch via FastAPI
- `POST /analyze` — Send alert payload to Ollama for threat analysis
- `GET /similar` — Query ChromaDB for semantically similar past incidents
- `POST /playbook` — Trigger adversary playbook execution

---

## Orchestration: Docker Compose vs Kubernetes

### Decision: Docker Compose (for Lab), Kubernetes-Ready (for Prod)

**Why Docker Compose:**
1. **Simplicity**: Single `docker-compose.yml` defines entire stack
2. **Single-Host Deployment**: Perfect for single Ubuntu PC "brain" server
3. **Reproducibility**: Everyone gets identical environment
4. **Development Velocity**: Fast local iteration before production deployment
5. **Lightweight**: No control-plane overhead; minimal resource footprint

**Future Kubernetes Path:**
- Helm charts can be generated from Compose manifests
- Production multi-node deployment: Helm → Kube cluster
- No re-architecting required; just different orchestrator

**Rejected for Lab Phase:**
- **Kubernetes**: Over-engineered for single-node lab; adds management complexity

---

## Operating System Choices

### Raspberry Pi: Debian (Lite)
- **Raspberry Pi OS Lite**: Minimal footprint; optimized for ARM; strong community for Pi-specific issues
- Alternative: Ubuntu Server ARM → More familiar to team but slower on Pi Zero/3

### Brain Server: Ubuntu Server LTS
- **Ubuntu 22.04 LTS**: Strong support; Docker/Compose first-class; familiar to Linux sysadmins
- Alternative: CentOS/RHEL → More enterprise but less container-native tooling

### Adversary/Dev: Ubuntu Server LTS
- Consistent with brain server for standardized ansible playbooks
- Alternative: Kali Linux → Over-provisioned for our playbook needs

---

## Networking: Port Mirroring vs Tap vs Inline

### Decision: Port Mirroring (SPAN) on Switch

**Why SPAN:**
1. **Passive Observation**: No risk of breaking traffic if IDS crashes
2. **Non-Intrusive**: OT network unaffected by monitoring system failures
3. **Hardware Available**: Managed switches widely available (even consumer-grade)
4. **Fail-Safe**: If sensor disconnects, OT continues operating

**Alternatives Considered:**
- **Inline TAP**: Better filtering but requires physical tap hardware (higher cost)
- **ARP Spoofing**: Can be detected as attack; unreliable
- **Network TAP**: Expensive hardware for lab budget (~$500+)

---

## Summary Table: Core Technology Stack

| Component | Choice | Key Trade-off | Alternatives |
|-----------|--------|--------------|--------------|
| **IDS** | Suricata | Rules-based; not pure ML | Zeek, Snort 3, cloud-native |
| **Search/Indexing** | OpenSearch | Elasticsearch-compatible fork | Splunk, Loki, QRadar |
| **LLM Analysis** | Phi-3 Mini (3.8B) | Smaller = faster but less nuanced | GPT-4, Llama 7B |
| **Vector DB** | ChromaDB | Lightweight; single-node optimal | Pinecone, Weaviate |
| **API** | FastAPI | Python-focused | Go, Node.js |
| **Orchestration** | Docker Compose | Single-host; Kubernetes-ready | Kubernetes, systemd |
| **Storage** | Local SSD + Volumes | No cloud dependency | S3, HDFS |
| **Sensor** | Raspberry Pi | Low-power, edge-ready | Mini PC, laptop, cloud probe |

---

## Future Enhancements & Technology Roadmap

### Phase 2: Advanced Detection
- **Behavioral Baselining**: Establish "normal" network patterns, flag deviations
- **Ensemble Models**: Combine rule-based, statistical, and neural approaches
- **Threat Intelligence Feeds**: Integrate external IOC data (AlienVault OTX, etc.)

### Phase 3: Multi-Sensor Architecture
- **Distributed Sensors**: Deploy multiple Pi units across network segments
- **Sensor Mesh Networking**: Sensors communicate with each other (vs hub-and-spoke)
- **Federated Learning**: Sensors contribute to model training without sending raw data

### Phase 4: Automation & Response
- **Playbook Orchestration**: Auto-execution of remediation actions (isolate VLAN, kill process)
- **SOAR Integration**: Ticketing system (Jira, ServiceNow) for incident tracking
- **Custom Sigma Rules**: Community-driven rule format for easier rule sharing
