# Rogue Dashboard
Rogue AP Web Server + Dashboard

This project was to help me learn more about iptables, dnsmasq, hostapd, Flask web servers, and Rogue AP attacks in general. It mimics the University of Houston login page.
Once it is running, users will connect to the Wi-Fi and be prompted with a captive web portal to enter in their credentials. Their credentials will POST to a text file once they "log in"
As of now, they will not be able to actually use the internet.

Requirements:
- Wi-Fi adapter that supports AP mode (I used ALFA AWUS036ACM)
- Python 3
- Kali Linux (or any Linux distro that supports iptables, dnsmasq, hostapd, etc)

Optional:
- Server to exfiltrate credentials to (I used Linode) - otherwise it just goes to the machine running the Flask server

## Project Structure

```bash
.
├── start_rogue_ap.sh       # Main setup script
├── stop_rogue_ap.sh        # Clean shutdown
├── fake.py                 # Flask HTTPS server with portal + dashboard
├── http_redirect.py        # Captive portal redirect (port 80)
├── hostapd.conf            # AP config
├── dnsmasq.conf            # DNS/DHCP config
├── creds/credentials.txt   # Captured credentials
├── templates/              # Flask HTML templates
└── static/                 # JS, CSS, and image assets
