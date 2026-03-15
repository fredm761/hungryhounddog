# HungryHoundDog Portfolio - Interview STAR Stories

## Format Reference
**SITUATION**: Set the context (problem, constraints, stakeholders)
**TASK**: What were you responsible for?
**ACTION**: What specific steps did you take?
**RESULT**: Quantifiable outcomes + lessons learned

---

# SECTION A — Completed Work (Grounded in actual implementation)

*These stories reflect work that has been built, tested, and verified. Every claim is backed by real output.*

---

## Story 1: Building a Distributed Security Architecture with Constraints

### SITUATION
I wanted to deepen my understanding of the security infrastructure I manage at enterprise scale by building a home lab that mirrors real OT (Operational Technology) deployment patterns. Commercial SIEM (Security Information and Event Management) platforms like Splunk cost $15K+/year — far beyond a lab budget. The challenge: build a production-grade distributed threat detection platform on commodity hardware using only open-source components, across four physically separate devices.

### TASK
I designed and implemented HungryHoundDog — a distributed OT security monitoring platform spanning a Raspberry Pi sensor, Ubuntu analytics server, adversary simulation node, and a development workstation. I owned the entire architecture: hardware selection, network design, software stack, and deployment.

### ACTION
**Step 1: Hardware Architecture**
- Selected a Raspberry Pi 4 (2 GB RAM) as a dedicated passive sensor — modeling how enterprise sensors like ExtraHop or Cisco Stealthwatch are deployed as purpose-built appliances
- Configured a TP-Link SG2008P managed switch with port mirroring (Port 1 → Port 3) so the Pi sees a copy of all Adversary traffic without transmitting — exactly like a SPAN port or network TAP in production
- Separated monitoring (eth0, promiscuous, no IP) from management (wlan0, with IP) on the Pi — mirroring the dual-interface architecture used in enterprise IDS deployments
- Powered the Pi via PoE (Power over Ethernet) through the switch — single-cable deployment, same as enterprise sensors and IP cameras

**Step 2: IDS Deployment and Tuning**
- Deployed Suricata 7.0.10 on the Pi with AF_PACKET capture on eth0
- Loaded the ET Open (Emerging Threats Open) ruleset, then tuned aggressively: disabled 33 irrelevant rule categories (malware, web apps, trojans, etc.) via `disable.conf`, reducing active rules from 48,803 to 16,672
- Wrote 12 custom Modbus TCP rules covering visibility, read/write operations, dangerous function codes, and exception responses
- Tuned memory caps (`stream.reassembly`: 128 MB, `flow`: 64 MB, `stream`: 32 MB) to keep Suricata RSS at ~369 MB on a 2 GB device with 1.3 GB headroom

**Step 3: Zero-Loss Log Pipeline**
- Built a custom Python log shipping agent that tails Suricata's EVE JSON output, batches 50 events with a 10-second flush timer, and POSTs to the Brain's FastAPI ingestion endpoint
- Implemented inode-based log rotation detection and byte-offset state persistence so the agent resumes exactly where it left off after restarts — no duplicate or missed events
- Built a JSONL fallback path: when Brain is unreachable, events write to a local buffer file. Built a separate drain script to replay buffered events once connectivity is restored — achieving zero data loss across a week of Brain downtime

**Step 4: Containerized Analytics Server**
- Deployed Docker Compose on the Brain server with OpenSearch (4 GB JVM heap, security plugin disabled for lab), Grafana, and a custom FastAPI ingestion service — all orchestrated with a single `docker compose up -d`
- Configured Docker's data root on an external SSD (`/mnt/ssd/docker`) to give OpenSearch SSD-speed I/O instead of the Brain's aging HDD
- Created an OpenSearch index template with daily rotation (`hungryhounddog-events-YYYY.MM.DD`), explicit field mappings for IP addresses, ports, alert metadata, and flow statistics — the same index lifecycle pattern used in enterprise ELK/OpenSearch deployments
- Set `vm.max_map_count=262144` for OpenSearch's memory-mapped file requirements — a common production deployment step that trips up first-time deployers

**Step 5: Visualization**
- Auto-provisioned the Grafana OpenSearch datasource via YAML config mounted into the container — no manual clicking required on fresh deployments
- Built a five-panel security dashboard: events over time, alerts over time, top source IPs, event type distribution, and top alert signatures

### RESULT
**Quantitative Outcomes:**
- **Cost**: ~$200 in hardware purchases (switch, PoE HAT, SSD, cables). $0/month in software costs. All open source.
- **Rule Efficiency**: 48,803 → 16,672 rules (66% reduction), Suricata RSS dropped from 1.24 GB to 369 MB
- **Pipeline Latency**: Events flow from Suricata capture → OpenSearch index within 10 seconds
- **Zero Data Loss**: One week of buffered events (Brain offline) successfully drained and indexed with no gaps
- **Deployment**: Single `docker compose up -d` starts the entire analytics stack

**Qualitative Outcomes:**
- Proved that a $200 hardware investment plus open-source software can replicate the core functionality of a commercial SIEM pipeline
- Demonstrated separation of monitoring and management planes, passive sensor deployment, port mirroring, daily index rotation, and containerized service orchestration — all patterns that map directly to enterprise infrastructure
- Every component mirrors something in my daily work: CrowdStrike sensor deployment → Pi sensor deployment; SIEM log ingestion → FastAPI + OpenSearch pipeline; dashboard monitoring → Grafana

**What I Learned:**
- `pgrep -x` fails on Suricata 7.x because the main thread is named `Suricata-Main`, not `suricata`. Use `pgrep -f`. Lesson: always verify process naming before writing monitoring scripts.
- `StartLimitIntervalSec` and `StartLimitBurst` must be in the `[Unit]` section on older systemd versions (Raspberry Pi OS), not `[Service]`. Lesson: systemd behavior varies across distributions.
- ET Open `disable.conf` entries require the `.rules` suffix — omitting it silently fails to disable categories, wasting RAM. Lesson: silent failures are the hardest bugs to find.
- Circular Python imports crash FastAPI on startup. The fix is to extract shared state (like database clients) into a dedicated module that both the app and route files can import independently. Lesson: plan your module dependency graph before writing code.
- When a log shipper's saved byte offset exceeds the current file size (due to log rotation or truncation), it reads nothing forever. Lesson: state persistence needs bounds checking.

---

## Story 2: Debugging a Distributed Pipeline Across Three Devices

### SITUATION
After deploying the log shipping agent on the Raspberry Pi sensor, it was buffering events locally for a week while I built the Brain server. When I finally deployed the FastAPI ingestion endpoint on the Brain and connected the sensor, I hit three separate issues in sequence: a circular import crash in the Python API, an HTTPS/HTTP protocol mismatch, and a stale file offset that caused the shipper to read nothing from a file that was actively growing. Each bug was on a different device, visible only through different logs.

### TASK
I needed to diagnose and fix each issue in sequence to establish the end-to-end data flow: Suricata on the Pi → log shipper → FastAPI on Brain → OpenSearch. Then I needed to drain a week of buffered events without data loss.

### ACTION
**Step 1: Circular Import Fix (Brain)**
- The FastAPI ingestion container crashed on startup with `ImportError: cannot import name 'get_os_client' from partially initialized module 'api.main'`
- Root cause: `main.py` imported `ingest.py` which imported `get_os_client` back from `main.py` — a circular dependency
- Fix: extracted the OpenSearch client singleton into a new `db.py` module. Both `main.py` and the route files import from `db.py` instead of from each other. Rebuilt the Docker image and the container started cleanly.

**Step 2: Protocol Mismatch Fix (Sensor)**
- The shipper logged `Brain unreachable at https://10.0.0.180:8080/ingest — connection refused`
- Root cause: the sensor config still specified `https://` but the Brain endpoint serves HTTP (TLS deferred to Weekend 7 hardening phase)
- Fix: updated `config.yaml` on the sensor, changed both endpoints from `https` to `http`, restarted the shipper service

**Step 3: Stale Offset Fix (Sensor)**
- The shipper logged "Resuming from saved state — offset 1,630,561,923" but `eve.json` was only ~90 MB. The saved offset from the previous week pointed past the end of the current file.
- Root cause: `eve.json` had been truncated or rotated since the offset was saved, but the shipper's rotation detection only checks inode changes — not whether the offset exceeds the file size
- Fix: manually reset the state file to the current file size and inode. Shipper immediately began reading new events.
- Noted this as a code improvement to add bounds checking on resume (if saved offset > current file size, seek to end instead of saved position)

**Step 4: Buffer Drain**
- Ran the drain script to replay the week of JSONL-buffered events into the now-working Brain endpoint
- Verified document count in OpenSearch increased by the expected amount

### RESULT
**Quantitative Outcomes:**
- **Total debug time**: ~45 minutes across three separate issues on two devices
- **Data loss**: Zero — all buffered events successfully indexed
- **Pipeline uptime**: Continuous since fixes applied; shipper delivers batches every 10 seconds with HTTP 200 responses

**What I Learned:**
- Distributed systems multiply debugging complexity. Each bug was on a different device, visible through different logs (`docker compose logs` on Brain, `journalctl` on Sensor). You have to be comfortable jumping between terminals.
- Silent failures are the worst category of bug. The stale offset didn't produce an error — it just produced nothing. The shipper appeared healthy but was reading past the end of the file forever.
- Fix one thing at a time and verify before moving on. I wasted zero time because I addressed the circular import (crash), then the protocol mismatch (connection refused), then the stale offset (no data) in sequence — each fix was verified before moving to the next.

---

# SECTION B — Draft Stories (To be updated with real details after completion)

*These stories are pre-written based on the project roadmap. They contain projected outcomes and placeholder metrics. Update each story with actual implementation details, real numbers, and genuine lessons learned as each weekend is completed. Do not use these in interviews until the underlying work is done.*

---

## Draft Story 3: Optimizing LLM Integration Without API Costs

### SITUATION
I wanted to add AI-powered threat analysis to HungryHoundDog but faced a dilemma: cloud LLM APIs (OpenAI, Claude) cost $0.01–0.10 per query. At 100 alerts/day, that's $300–3000/month. Additionally, OT environments are often air-gapped (no internet access), making API calls impossible. I needed a way to do sophisticated threat analysis locally, on consumer hardware, without ongoing API costs.

### TASK
I needed to integrate a large language model (LLM) into the detection pipeline such that:
- It runs locally without internet dependency
- It fits on modest hardware (8GB RAM)
- It provides meaningful threat analysis (not just regurgitating log fields)
- It doesn't block real-time alert ingestion

### ACTION
**Step 1: Model Selection**
- Evaluated Phi-3 Mini (3.8B parameters, MIT license, optimized for consumer inference)
- Considered alternatives:
  - GPT-4 API: $0.01–0.10/query (cost prohibitive)
  - Llama 2 7B: Larger (7B params), slower, marginal quality gain over Phi-3 Mini
  - Fine-tuned BERT: Task-specific but requires labeled training data
- Chose Phi-3 Mini: 3.8B params, runs in 2GB VRAM (4-bit quantization via Ollama), <5 second inference latency

**Step 2: Deployment Architecture**
- *[TO BE UPDATED with actual deployment details from Weekend 6]*

**Step 3: Prompt Engineering for OT Context**
- *[TO BE UPDATED with actual prompts and accuracy results]*

### RESULT
- *[TO BE UPDATED with actual metrics after Weekend 6]*

---

## Draft Story 4: Building a Reproducible Adversary Framework for Validation

### SITUATION
I had built detection rules and AI analysis, but I couldn't validate if they actually worked. I needed a way to systematically generate attacks and verify detection end-to-end.

### TASK
I designed and implemented the adversary node — a Python-based framework to simulate realistic OT attacks mapped to MITRE ATT&CK for ICS.

### ACTION
- *[TO BE UPDATED with actual implementation details from Weekend 4]*

### RESULT
- *[TO BE UPDATED with actual detection rates and metrics after Weekend 4]*

---

## Draft Story 5: Troubleshooting and Performance Tuning Under Constraints

### SITUATION
- *[TO BE UPDATED with actual performance issues encountered during Weekends 5–7]*

### ACTION
- *[TO BE UPDATED with actual diagnosis and optimization steps]*

### RESULT
- *[TO BE UPDATED with actual before/after metrics]*

---

## Draft Story 6: Making Architecture Decisions with Limited Information

### SITUATION
Early in the project, I had to choose between several technologies (IDS platforms, search engines, LLMs) but limited time to evaluate. I needed a decision framework to make confident choices with incomplete information.

### TASK
I needed to define evaluation criteria, research trade-offs efficiently, distinguish reversible from irreversible decisions, and document rationale for future justification.

### ACTION
**Step 1: Define Evaluation Criteria**
Weighted the following:
1. **OT Domain Fit** (40%): Modbus/DNP3 support, protocol-specific rules
2. **Resource Efficiency** (25%): Runs on Pi 2GB + Brain 15.5 GB
3. **Cost** (20%): Open-source, no SaaS fees
4. **Operational Burden** (10%): Learning curve, deployment complexity
5. **Community** (5%): Existing documentation, active forums

**Step 2: Research Phase**
- IDS: Suricata (chosen for multi-threading, native JSON output, OT protocol support) vs. Snort (single-threaded, aging codebase) vs. Zeek (heavier, less IDS-focused)
- Search Engine: OpenSearch (open-source Elasticsearch fork, full query DSL, free) vs. Elasticsearch (licensing complexity) vs. Splunk (cost-prohibitive)
- Log Shipper: Custom Python agent (lightweight, educational, portfolio-worthy) vs. Filebeat (~200 MB RAM overhead on a 2 GB Pi)

**Step 3: Risk Assessment**
- Reversible decisions (low cost to change): OpenSearch (could swap to ELK), Grafana (could swap to OpenSearch Dashboards)
- Irreversible decisions (high cost): Raspberry Pi as sensor (hardware purchase), Suricata as IDS (rules and config investment)
- Decision: move fast on reversible choices, invest more evaluation time on irreversible ones

**Step 4: Documentation**
- Created architecture decision records in the project roadmap
- Each choice includes: context, alternatives evaluated, rationale, constraints, and trade-offs
- *[TO BE EXPANDED into formal design-decisions.md in Weekend 8]*

### RESULT
**Quantitative Outcomes:**
- **Reversals**: 0 major rework needed through 3 weekends of implementation
- **Technology choices validated**: Suricata fits the Pi's 2 GB RAM; OpenSearch runs within 4 GB heap on Brain; custom Python shipper uses <30 MB vs. Filebeat's ~200 MB

**What I Learned:**
- Perfect information rarely exists; constraints force pragmatism
- Domain expertise reduces decision risk: understanding OT protocols well enough to evaluate IDS options saved weeks of trial-and-error
- Reversible decisions should be made fast; irreversible decisions deserve more scrutiny
- Documenting "why" prevents future rework: when Weekend 3 bugs appeared, the architecture rationale helped narrow root causes quickly

---

## Common Interview Follow-ups & Responses

### "What would you do differently?"

**Answer**: "In a production deployment with higher budget, I'd add:
1. **High Availability**: OpenSearch cluster (3+ nodes) with replication, not single node
2. **Encryption**: mTLS for inter-service communication from day one, not deferred to a hardening phase
3. **Centralized Secret Management**: HashiCorp Vault instead of environment variables
4. **Multiple Sensors**: Deploy across different network segments, not just one mirrored port
5. **Bounds Checking in the Shipper**: The stale offset bug taught me that state persistence needs defensive validation — if saved offset exceeds file size, reset automatically instead of reading nothing forever
6. The lab was optimized for learning and cost; production would prioritize resilience and compliance."

### "How do you measure success?"

**Answer**: "Multiple dimensions:
- **Technical**: Events flow end-to-end in under 10 seconds. Zero data loss during a week of Brain downtime. Suricata runs within 369 MB on a 2 GB device.
- **Operational**: `docker compose up -d` starts the entire analytics stack. Shipper survives reboots and resumes from saved state.
- **Portfolio**: The GitHub repo tells a story — 3 weekends of commits showing architecture decisions, debugging, and iteration. Not a copy-paste job.
- **Career**: Every component maps to enterprise infrastructure I work with daily. I can explain the 'why' behind every choice."

### "How do you approach debugging distributed systems?"

**Answer**: "I follow a systematic approach: check each component in the data flow order. For HungryHoundDog, that means: Is Suricata writing to eve.json? Is the shipper reading it? Is the shipper connecting to Brain? Is Brain indexing into OpenSearch? I check logs at each step — `journalctl` on the Sensor, `docker compose logs` on Brain — and fix one issue at a time, verifying before moving on. During Weekend 3, I hit three separate bugs in sequence (circular import, protocol mismatch, stale offset) and fixed each one methodically in under 45 minutes total."

### "How do you approach learning new domains?"

**Answer**: "For OT security, I started with fundamentals: read the Modbus TCP specification, studied MITRE ATT&CK for ICS, and reviewed real CVEs in industrial systems. Then I built bottom-up: passive traffic capture first, then custom Modbus detection rules, then a full ingestion pipeline. I validate understanding by building — if I can deploy it on real hardware and debug it when it breaks, I understand it. The project is intentionally designed so every component maps to my enterprise work at UPS, which lets me connect lab learning to real-world context in interviews."

---

## Keywords to Emphasize Across Stories

- **Problem-Solving**: Constrained budget → innovative tech choices; three sequential bugs fixed methodically
- **Systems Thinking**: Distributed architecture across 4 devices, separation of monitoring and management planes
- **Domain Expertise**: OT protocols (Modbus TCP), IDS tuning, SIEM pipeline architecture
- **Trade-offs**: Cost vs. features, HTTP now vs. TLS later, custom shipper vs. Filebeat
- **Zero Data Loss**: Fallback buffering, drain script, state persistence
- **Debugging**: Circular imports, protocol mismatches, stale offsets — each on a different device
- **Documentation**: Architecture decisions, runbooks, interview stories written alongside the build
- **Learning**: New technologies, domains, frameworks — validated by building, not just reading
