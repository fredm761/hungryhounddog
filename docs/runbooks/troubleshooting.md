# HungryHoundDog Troubleshooting Guide

## Table of Contents
1. [Sensor-Related Issues](#sensor-issues)
2. [Brain Server Issues](#brain-server-issues)
3. [Network & Connectivity](#network-connectivity)
4. [Detection & Alerting](#detection-alerting)
5. [Performance Issues](#performance-issues)

---

## Sensor Issues

### Issue: Suricata Not Capturing Packets

**Symptom**: No events in Suricata log; eve.json remains empty

**Diagnosis**:
```bash
# SSH to Pi sensor
ssh pi@192.168.50.100

# Check if Suricata is running
sudo systemctl status suricata

# Check Suricata error log
sudo tail -50 /var/log/suricata/suricata.log | grep -i error

# Verify interface is up
ip link show eth0
# Look for "UP" status

# Check if packets are arriving on interface (while capturing)
sudo tcpdump -i eth0 -c 10 -n
# Should see traffic on the monitored interface
```

**Common Causes & Fixes**:

1. **Interface not configured for promiscuous mode**:
   ```bash
   # Enable promiscuous mode
   sudo ip link set eth0 promisc on
   
   # Verify
   ip link show eth0 | grep -i promisc
   # Should show "PROMISC"
   
   # Make persistent across reboots
   sudo nano /etc/rc.local
   # Add: ip link set eth0 promisc on
   ```

2. **SPAN (port mirroring) not configured on switch**:
   ```bash
   # Verify traffic is actually reaching sensor
   sudo tcpdump -i eth0 -n | grep -E "192.168.50.(10|11|12)"
   
   # If no OT network traffic visible, configure switch:
   # Access switch web UI or SSH → VLAN settings
   # Enable: Source Port = eth0, Destination Port = Pi interface
   # OR: Monitor Port = Pi interface, Monitor Sessions = all VLANs
   ```

3. **Suricata rules not loaded**:
   ```bash
   # Check loaded rules
   sudo suricatasc -c "rule-list" /var/run/suricata/suricata-command.socket | head
   
   # Update rules
   sudo suricata-update
   
   # Restart Suricata
   sudo systemctl restart suricata
   
   # Verify rules loaded
   sudo journalctl -u suricata -n 20 | grep -i "rules loaded"
   ```

4. **Interface MTU mismatch**:
   ```bash
   # Check interface MTU
   ip link show eth0 | grep mtu
   
   # If different from switch, adjust (usually 1500)
   sudo ip link set eth0 mtu 1500
   ```

---

### Issue: Filebeat Not Shipping Logs

**Symptom**: OpenSearch has no `suricata-*` indices; eve.json not being read

**Diagnosis**:
```bash
# Check Filebeat status
sudo systemctl status filebeat

# Check Filebeat logs
sudo journalctl -u filebeat -n 50

# Verify eve.json exists and is being updated
ls -lah /var/log/suricata/eve.json
tail -f /var/log/suricata/eve.json  # Should show new events

# Test connectivity to Brain
telnet 192.168.100.50 9200
# Should connect; press Ctrl+C to exit
```

**Common Causes & Fixes**:

1. **Eve.json path wrong in filebeat.yml**:
   ```bash
   # Check configured path
   grep "eve.json" /opt/filebeat/filebeat.yml
   
   # Verify actual path
   find /var/log -name "eve.json"
   
   # Correct filebeat.yml
   sudo nano /opt/filebeat/filebeat.yml
   # Ensure paths: ["/var/log/suricata/eve.json"] is correct
   ```

2. **OpenSearch not accessible**:
   ```bash
   # From Pi, test Brain connectivity
   curl -u admin:Admin@123456 http://192.168.100.50:9200/_cluster/health
   
   # If connection refused:
   # - Check Brain firewall: sudo ufw status | grep 9200
   # - Verify OpenSearch is running: docker-compose logs opensearch | tail
   # - Check network routing: ping 192.168.100.50
   ```

3. **File permissions preventing read**:
   ```bash
   # Check eve.json permissions
   ls -la /var/log/suricata/eve.json
   
   # If root-only, make readable
   sudo chmod 644 /var/log/suricata/eve.json
   
   # Make persistent - edit /etc/suricata/suricata.yaml:
   # eve-log:
   #   filename: /var/log/suricata/eve.json
   #   file-mode: 0644  # Readable by all
   ```

4. **Filebeat registry out of sync**:
   ```bash
   # Reset Filebeat registry
   sudo rm /var/lib/filebeat/registry*
   sudo systemctl restart filebeat
   
   # Or, clear Filebeat state
   rm -rf /opt/filebeat/data/*
   ```

---

## Brain Server Issues

### Issue: OpenSearch OOM (Out of Memory)

**Symptom**: OpenSearch container crashes with "OutOfMemoryError"; `docker-compose logs opensearch` shows heap allocation errors

**Diagnosis**:
```bash
# Check container memory usage
docker stats opensearch

# Check logs
docker logs opensearch | grep -i "memory\|heap\|OOM"

# Check available system memory
free -h
df -h  # Check disk space for swap
```

**Fixes**:

1. **Reduce heap size (immediate)**:
   ```bash
   # Edit docker-compose.yml
   nano docker-compose.yml
   
   # Change OPENSEARCH_JAVA_OPTS:
   # From: -Xms2g -Xmx2g
   # To:   -Xms1g -Xmx1g  (or even -Xms512m -Xmx512m)
   
   # Restart
   docker-compose restart opensearch
   ```

2. **Delete old indices (reduce data)**:
   ```bash
   # List indices
   curl -u admin:Admin@123456 http://localhost:9200/_cat/indices
   
   # Delete indices older than 30 days
   # Example: delete suricata-2024.11.*
   curl -u admin:Admin@123456 -X DELETE http://localhost:9200/suricata-2024.11.*
   ```

3. **Enable index lifecycle management (ILM)**:
   ```bash
   # Create ILM policy for auto-deletion
   curl -u admin:Admin@123456 -X PUT http://localhost:9200/_ilm/policy/suricata-policy \
     -H "Content-Type: application/json" \
     -d '{
       "policy": "suricata-policy",
       "phases": {
         "hot": {"min_age": "0d", "actions": {}},
         "delete": {"min_age": "30d", "actions": {"delete": {}}}
       }
     }'
   ```

4. **Add swap space (temporary)**:
   ```bash
   # Create swap file
   sudo fallocate -l 4G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   
   # Make persistent
   echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
   ```

---

### Issue: Grafana Dashboards Not Loading

**Symptom**: Grafana blank; "No data" on all panels

**Diagnosis**:
```bash
# Check Grafana container
docker logs grafana | tail -20

# Check datasource connectivity
curl http://localhost:3000/api/datasources
# Should show OpenSearch datasource

# Verify OpenSearch is running and accessible
curl -u admin:Admin@123456 http://localhost:9200/_cluster/health
```

**Fixes**:

1. **Recreate datasource connection**:
   ```bash
   # Via Grafana web UI:
   # 1. Go to Configuration → Data Sources
   # 2. Click OpenSearch datasource
   # 3. Update URL: http://opensearch:9200
   # 4. Add auth: admin / Admin@123456
   # 5. Save & Test
   ```

2. **Re-provision dashboards**:
   ```bash
   # Restart Grafana
   docker-compose restart grafana
   
   # Check provisioning logs
   docker logs grafana | grep -i "provision"
   ```

3. **Clear Grafana cache**:
   ```bash
   # Remove Grafana data
   rm -rf grafana-data/*
   docker-compose restart grafana
   # Warning: Loses custom dashboards; restore from backup
   ```

---

### Issue: Ollama Inference Very Slow

**Symptom**: API requests to `/analyze` endpoint timeout; Ollama responses take > 30 seconds

**Diagnosis**:
```bash
# Check Ollama status
docker logs ollama | tail -20

# Test Ollama directly
curl -X POST http://localhost:11434/api/generate \
  -d '{"model": "phi", "prompt": "test"}'
# Note time taken

# Check container resource usage
docker stats ollama

# Check if GPU available
docker exec ollama nvidia-smi
```

**Fixes**:

1. **Use smaller/quantized model**:
   ```bash
   # Remove current model
   docker exec ollama ollama rm phi
   
   # Pull quantized variant (faster, less memory)
   docker exec ollama ollama pull phi:7b-q4
   
   # Or use even smaller model
   docker exec ollama ollama pull orca-mini
   
   # Update FastAPI to use new model
   # Edit api/main.py: MODEL = "phi:7b-q4"
   ```

2. **Enable GPU acceleration (if NVIDIA GPU available)**:
   ```bash
   # Check for GPU
   lspci | grep -i nvidia
   
   # If present, update docker-compose.yml:
   # ollama:
   #   image: ollama/ollama:latest
   #   runtime: nvidia
   #   environment:
   #     - NVIDIA_VISIBLE_DEVICES=all
   
   docker-compose restart ollama
   ```

3. **Reduce concurrent requests**:
   ```bash
   # Edit docker-compose.yml Ollama env:
   # - OLLAMA_NUM_PARALLEL=1  (reduce from 2)
   
   docker-compose restart ollama
   ```

4. **Increase timeout in FastAPI**:
   ```bash
   # Edit api/main.py
   # Change timeout in ollama_client initialization:
   # client = Client(host='http://ollama:11434', timeout=120)  # 2 minutes
   
   docker-compose restart fastapi
   ```

---

## Network Connectivity

### Issue: Raspberry Pi Cannot Reach Brain Server

**Symptom**: `ping 192.168.100.50` from Pi times out; Filebeat connection refused

**Diagnosis**:
```bash
# From Pi sensor
ssh pi@192.168.50.100

# Test connectivity
ping -c 3 192.168.100.50
# Should succeed; if timeout, network issue

# Test specific port
telnet 192.168.100.50 9200
# Should connect

# Check routing
ip route
# Look for default gateway pointing to correct interface

# Check firewall on Brain
ssh ubuntu@192.168.100.50
sudo ufw status | grep 9200
```

**Fixes**:

1. **Verify static IPs are configured**:
   ```bash
   # On Pi
   ip addr show | grep "192.168"
   
   # On Brain
   ip addr show | grep "192.168"
   
   # Both should be in their respective subnets
   ```

2. **Configure firewall on Brain**:
   ```bash
   # On Brain server
   sudo ufw allow from 192.168.50.0/24 to any port 9200
   sudo ufw status
   ```

3. **Check network switch routing**:
   ```bash
   # If two separate networks (50.0, 100.0):
   # Need router/switch to route between them
   
   # Test from Pi:
   traceroute 192.168.100.50
   # Should show hop through gateway
   ```

4. **Reset network interfaces**:
   ```bash
   # On Pi
   sudo systemctl restart networking
   
   # On Brain
   sudo systemctl restart networking
   
   # Or reboot both
   sudo reboot
   ```

---

### Issue: OT Network Devices Unreachable from Adversary Node

**Symptom**: Modbus attacks fail with "Connection refused"; no response from 192.168.50.x

**Diagnosis**:
```bash
# From Acer adversary node
ping 192.168.50.10
# Should succeed; if not, network isolated

# Check routing
ip route | grep 192.168.50

# Check firewall rules
sudo ufw status | grep 50
```

**Fixes**:

1. **Add route to OT network**:
   ```bash
   # If OT network unreachable, may need route
   sudo ip route add 192.168.50.0/24 via 192.168.100.1
   
   # Verify
   ip route
   
   # Test again
   ping 192.168.50.10
   ```

2. **Configure firewall to allow OT traffic**:
   ```bash
   sudo ufw allow out to 192.168.50.0/24
   sudo ufw status
   ```

---

## Detection & Alerting

### Issue: No Alerts Generated Despite Attacks

**Symptom**: Adversary playbook runs, but no corresponding alerts in Grafana/OpenSearch

**Diagnosis**:
```bash
# Verify events are in OpenSearch
curl -u admin:Admin@123456 http://localhost:9200/suricata-*/_search?size=5 | jq

# Check Grafana alert rules
# UI: Alerting → Alert Rules → verify enabled

# Check Ollama analysis is running
docker logs fastapi | grep -i "ollama\|analysis"

# Check OpenSearch for alert events
curl -u admin:Admin@123456 -X POST http://localhost:9200/suricata-*/_search \
  -H "Content-Type: application/json" \
  -d '{"query": {"match": {"event_type": "alert"}}}'
```

**Fixes**:

1. **Verify Suricata rules match attack traffic**:
   ```bash
   # Check if attack traffic is in eve.json
   ssh pi@192.168.50.100
   tail -20 /var/log/suricata/eve.json | jq '.event_type'
   
   # If no "alert" events, rules didn't match
   # Update rules: sudo suricata-update
   # Or add custom rules for Modbus attacks
   ```

2. **Enable Grafana alerting**:
   ```bash
   # Via Grafana UI:
   # Alerting → Notification channels → Add (Slack/Email/Webhook)
   # Create alert rules for suricata indices
   ```

3. **Check FastAPI is analyzing events**:
   ```bash
   # Make manual API call
   curl -X POST http://localhost:8000/analyze \
     -H "Content-Type: application/json" \
     -d '{"event_type": "alert", "signature": "Test attack"}'
   
   # Should return Ollama analysis
   # If timeout, see "Ollama Slow" section above
   ```

---

## Performance Issues

### Issue: High CPU Usage

**Symptom**: System slow; top/htop shows process > 80% CPU

**Diagnosis**:
```bash
# Identify hungry process
top -b -n 1 | head -20

# Check Docker containers
docker stats

# Check specific service logs
docker logs -f opensearch | head -20
```

**Common Causes & Fixes**:

1. **Suricata on Pi with too many threads**:
   ```bash
   # Edit suricata.yaml
   sudo nano /etc/suricata/suricata.yaml
   
   # Change:
   # threads: 4  → threads: 2  (or 1 for Pi Zero)
   
   sudo systemctl restart suricata
   ```

2. **OpenSearch indexing storm**:
   ```bash
   # If many events arriving, OpenSearch struggles
   # Check incoming rate
   curl -u admin:Admin@123456 http://localhost:9200/_cat/indices | grep suricata
   
   # Temporarily reduce Filebeat batch size
   # Edit /opt/filebeat/filebeat.yml:
   # output.elasticsearch:
   #   batch_size: 100  (reduce from default)
   
   sudo systemctl restart filebeat
   ```

3. **Ollama analysis on every event**:
   ```bash
   # If running Ollama on every event, very expensive
   # Edit api/main.py to sample events:
   # if random.random() < 0.1:  # Analyze only 10% of events
   #     analysis = await analyze_with_ollama(event)
   ```

---

### Issue: Disk Space Filling Up

**Symptom**: `df -h` shows root partition > 90% full; disk full errors

**Diagnosis**:
```bash
# Check disk usage
du -sh /*
du -sh ~/hungryhounddog/*

# Find large files
find / -size +1G -type f 2>/dev/null
```

**Fixes**:

1. **Delete old OpenSearch data**:
   ```bash
   # List indices by size
   curl -u admin:Admin@123456 http://localhost:9200/_cat/indices?v | sort -k6 -h
   
   # Delete oldest indices
   curl -u admin:Admin@123456 -X DELETE http://localhost:9200/suricata-2024.11.*
   ```

2. **Clear Docker storage**:
   ```bash
   docker system prune -a --volumes
   # Warning: removes all unused images/containers/volumes
   ```

3. **Compress old log files**:
   ```bash
   # Gzip old logs
   cd ~/hungryhounddog
   find . -name "*.log" -mtime +30 -exec gzip {} \;
   
   # Or delete
   find . -name "*.log" -mtime +60 -delete
   ```

4. **Move data to secondary SSD**:
   ```bash
   # If secondary drive available
   sudo mv ~/hungryhounddog/opensearch-data /mnt/data/
   docker-compose down
   docker-compose up -d
   ```

---

## Getting Help

### Log Collection for Debugging

```bash
# Collect all relevant logs
mkdir -p debug-logs

# System logs
sudo cp /var/log/syslog debug-logs/
sudo cp /var/log/auth.log debug-logs/

# Suricata logs (if on Pi)
scp pi@192.168.50.100:/var/log/suricata/* debug-logs/

# Docker logs
docker-compose logs > debug-logs/docker-compose.log
docker logs opensearch >> debug-logs/opensearch.log
docker logs ollama >> debug-logs/ollama.log
docker logs grafana >> debug-logs/grafana.log
docker logs fastapi >> debug-logs/fastapi.log

# System info
uname -a > debug-logs/system-info.txt
df -h >> debug-logs/system-info.txt
free -h >> debug-logs/system-info.txt
docker ps -a >> debug-logs/system-info.txt

# Tar for sharing
tar czf debug-logs.tar.gz debug-logs/
echo "Debug logs ready: debug-logs.tar.gz"
```

### Useful Commands for Diagnostics

```bash
# Real-time container monitoring
watch -n 1 'docker stats --no-stream'

# Follow all logs
docker-compose logs -f

# Reset everything (nuclear option)
docker-compose down -v
docker system prune -a --volumes
# Then redeploy

# Check port bindings
sudo netstat -tlnp | grep -E ":9200|:3000|:11434"

# Monitor network traffic
sudo tcpdump -i eth0 -n "host 192.168.100.50" -c 20
```
