# TP-Link SG2008P Smart Managed Switch Configuration

## Overview
TP-Link SG2008P managed switch serving as the lab core switch for HungryHoundDog OT security lab. Configured with port mirroring, VLAN segmentation, and PoE allocation.

## Physical Specifications
- 8x Gigabit Ethernet ports
- PoE support on selected ports
- Management IP: 192.168.1.254/24
- Default username: admin / admin

## VLAN Configuration

### VLAN 10: OT Segment (Operational Technology)
- CIDR: 192.168.10.0/24
- Gateway: 192.168.10.1
- Devices:
  - PLC #1: 192.168.10.10
  - PLC #2: 192.168.10.11
  - RTU #1: 192.168.10.20
  - HMI Console: 192.168.10.30
  - Sensor Node 1: 192.168.10.50
  - Sensor Node 2: 192.168.10.51

**Ports:** 1, 2 (Tagged as VLAN 10)

### VLAN 20: Management Segment
- CIDR: 192.168.20.0/24
- Gateway: 192.168.20.1
- Devices:
  - Monitoring Station: 192.168.20.10
  - Log Aggregator: 192.168.20.20
  - Dev Box: 192.168.20.30
  - Switch Management: 192.168.20.254

**Ports:** 3, 4 (Tagged as VLAN 20)

### VLAN 1: Management/Default
- CIDR: 192.168.1.0/24
- Gateway: 192.168.1.1
- Devices:
  - Adversary Node (Acer): 192.168.1.50
  - Raspberry Pi (Sensor): 192.168.1.60
  - Network devices management

**Ports:** 5, 6, 7, 8 (Untagged - default VLAN)

## Port Mirroring Configuration

### Mirror Setup for Suricata IDS
- **Mirrored Port (Source):** Port 1 (OT traffic from PLC #1)
- **Mirror Destination Port:** Port 3 (to monitoring station)
- **Direction:** Both Ingress and Egress
- **Description:** Capture OT protocol traffic for anomaly detection

Configuration steps (via Web GUI):
1. Navigate to: Administration → Mirroring
2. Enable port mirroring
3. Select Source Port: 1
4. Select Destination Port: 3
5. Direction: Ingress + Egress
6. Save configuration

## PoE Configuration

### PoE Power Allocation

| Port | Device | Power Budget |
|------|--------|--------------|
| 1    | PLC #1 | 15W (802.3af) |
| 2    | PLC #2 | 15W (802.3af) |
| 6    | Raspberry Pi Sensor | 8W (Class 2) |
| 7    | Wireless AP (optional) | 15W (802.3af) |

- **PoE Mode:** Per-port mode
- **Power Limit:** 90W total budget
- **Priority:** High on ports 1, 2 (industrial devices)

## Port Assignments

| Port | Device | VLAN | Type | Speed |
|------|--------|------|------|-------|
| 1    | PLC #1 | 10   | Industrial | 1000M |
| 2    | PLC #2 | 10   | Industrial | 1000M |
| 3    | Monitoring/Mirror Dest | 20 | Management | 1000M |
| 4    | Log Server | 20 | Management | 1000M |
| 5    | Adversary Node | 1 | Management | 1000M |
| 6    | Raspberry Pi Sensor | 1 | Sensor | 1000M |
| 7    | Uplink (reserved) | 1 | Trunk | 1000M |
| 8    | Reserved | 1 | Management | 1000M |

## QoS Configuration (Optional)

For prioritizing OT traffic:

```
Queue Group: 8 queues per port
Queue 1 (High): Modbus TCP (port 502)
Queue 2 (High): MQTT (port 1883)
Queue 3 (Medium): DNS (port 53)
Queue 4 (Medium): HTTP (port 80/443)
Queue 5-8 (Low): Other traffic
```

## Spanning Tree Protocol

- **Status:** Enabled (RSTP)
- **Priority:** 32768
- **Path Cost:** Auto
- **Max Age:** 20 seconds

## Security Settings

- **Login Banner:** "HungryHoundDog Lab - Authorized Access Only"
- **SSH Access:** Enabled on port 22 (if available)
- **HTTP Access:** Disabled for security
- **HTTPS Access:** Enabled (port 443)
- **SNMP:** Disabled for lab

## Backup Configuration

Switch configuration backed up to:
- Location: `/sessions/gracious-stoic-goodall/mnt/hungryhounddog/switch/backups/`
- Filename: `sg2008p-config-YYYY-MM-DD.bin`
- Backup frequency: After each major configuration change

## Monitoring & Alerts

- Monitor port statistics via Netstat in Web UI
- Alert thresholds:
  - Port down: Immediate alert
  - CPU utilization > 80%: Warning
  - Temperature > 55°C: Critical

## Firmware

- Current Firmware: v2.0.5 (example)
- Check for updates quarterly
- Test updates on non-production devices first

## Troubleshooting

### Port not passing traffic
1. Check port status in web UI (Admin → Port Statistics)
2. Verify VLAN membership
3. Check cable connection
4. Check PoE power if applicable

### Mirroring not working
1. Verify both ports are enabled
2. Check source port is receiving traffic
3. Verify destination port is not overloaded
4. Restart switch if necessary

### PoE device not powering on
1. Check PoE mode is "Port-based"
2. Verify power budget available
3. Check if device requires higher power class
4. Test with direct power adapter

## Configuration Change Log

| Date | Change | User | Approved |
|------|--------|------|----------|
| 2026-02-27 | Initial configuration | Admin | Lab Lead |
| | | | |

