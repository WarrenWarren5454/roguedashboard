# Rogue Dashboard

A Flask web server with a React dashboard for monitoring captured credentials.

## Prerequisites

1. Python 3.x
2. Node.js and npm
3. A Wi-Fi adapter that supports AP mode (e.g., ALFA AWUS036ACM)
4. Kali Linux or any Linux distro with iptables, dnsmasq, and hostapd support

## Setup Steps

1. Install Python dependencies:
```bash
python -m pip install flask flask-cors requests
```

2. Install Node.js dependencies:
```bash
cd frontend
npm install
npm run build
```

3. Start the Rogue AP:
```bash
sudo ./start_rogue_ap.sh
```

4. Access the dashboard:
- Development: http://localhost:3000
- Production: https://10.0.0.1/dashboard

## Features

- Captive portal that mimics UH login
- Real-time credential monitoring
- Modern React dashboard
- Secure HTTPS connection
- Automatic credential storage

## Project Structure

```bash
.
├── start_rogue_ap.sh       # Main setup script
├── stop_rogue_ap.sh        # Clean shutdown
├── fake.py                 # Flask HTTPS server
├── http_redirect.py        # Captive portal redirect
├── hostapd.conf            # AP config
├── dnsmasq.conf            # DNS/DHCP config
├── cert.crt                # SSL certificate
├── cert.key                # SSL private key
├── creds/                  # Captured credentials
├── frontend/              # React dashboard
└── templates/             # Flask HTML templates

```

## Security Note

This project is for educational purposes only. Ensure you have proper authorization before using this tool.
