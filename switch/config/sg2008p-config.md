# TP-Link SG2008P Smart Managed Switch Configuration

## Overview
TP-Link SG2008P managed switch serving as the lab core switch for HungryHoundDog OT security lab. Configured with port mirroring, VLAN segmentation, and PoE allocation.

## Physical Specifications
- 8x Gigabit Ethernet ports
- PoE support on selected ports
- Management IP: 192.168.1.254/24
- Default username: admin / admin

## Management Access
- IP: 10.0.0.248
- Subnet: 255.255.255.0
- Gateway: 10.0.0.1
- Admin user: admin (password changed from default)

## Port Assignments
| Port | Device | Cable | PVID | Role |
|------|--------|-------|------|------|
| 1 | Acer "Adversary" | CAT6 | 20 | Mirror SOURCE |
| 2 | Ubuntu PC "Brain" | CAT6 | 20 | Normal |
| 3 | Raspberry Pi "Sensor" | CAT6 + PoE | 20 | Mirror DESTINATION |
| 4 | Dell "Dev Box" | CAT8 via Anker Dock | 20 | Normal |
| 5 | Home Router | CAT8 | 20 | Uplink |
| 6-8 | Unused | — | — | — |

## Port Mirroring
- Session 1: Source Port 1 (Both directions) → Destination Port 3

## PoE
- Port 3: PoE enabled, powering Raspberry Pi 4 via PoE HAT
## VLANs (Future)
- VLAN 10 "OT-SIM": To be configured during hardening phase
- VLAN 20 "MGMT": Currently all ports on default VLAN