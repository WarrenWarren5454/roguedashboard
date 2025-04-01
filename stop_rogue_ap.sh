#!/bin/bash

echo "[*] Killing rogue services..."

# Stop Flask servers
sudo pkill -f fake.py
sudo pkill -f http_redirect.py

# Stop dnsmasq and hostapd
sudo pkill dnsmasq
sudo pkill hostapd

# Clear iptables rules
echo "[*] Flushing iptables rules..."
sudo iptables -t nat -F
sudo iptables -F

# Optionally disable IP forwarding
echo "[*] Disabling IP forwarding..."
sudo sysctl -w net.ipv4.ip_forward=0 > /dev/null

# Optionally reset interface
echo "[*] Resetting interface..."
sudo ip link set wlan0 down
sudo iw dev wlan0 set type managed
sudo ip link set wlan0 up

echo "[✓] Rogue AP shut down cleanly."
