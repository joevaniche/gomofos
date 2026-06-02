# Ubuntu Server Deployment Guide - gomofos.com

Complete deployment guide for the Esports Bet platform on Ubuntu Server (22.04 / 24.04 LTS).

**Server IP:** `192.168.0.124` (private LAN address)
**Domain:** `gomofos.com`

---

## ⚠️ IMPORTANT: Private IP Limitation

`192.168.0.124` is a **private LAN address** — it is only reachable from devices on the same local network (same WiFi/router). This means by default:

- ❌ People on the public internet **cannot** reach your server
- ❌ Public DNS for `gomofos.com` cannot point directly to `192.168.0.124`
- ❌ Let's Encrypt SSL certificates won't auto-issue without public access

### You have 3 deployment paths — pick one:

| Path | Use Case | Public Access | SSL |
|---|---|---|---|
| **A. LAN-Only** | Internal/testing/dev | No (LAN devices only) | Self-signed cert |
| **B. Port Forwarding** | Production from home/office | Yes (via your public IP) | Let's Encrypt ✓ |
| **C. Cloudflare Tunnel** | Production, no router config | Yes (via Cloudflare) | Let's Encrypt ✓ |

**Recommendation:** If this is for real users → **Path C (Cloudflare Tunnel)**. It's free, secure, and requires no router/firewall changes. If you only need LAN access for now → **Path A**.

The guide below works for all three paths. The differences are noted in **PART 1 (DNS)** and **PART 8 (SSL)**.

---

## PART 1: DNS Setup (Path-specific)

### Path A — LAN-Only (no public DNS)
Edit the `hosts` file on each device that will access the site:

**On Linux/Mac:**
```bash
sudo nano /etc/hosts
# Add this line:
192.168.0.124  gomofos.com www.gomofos.com
```

**On Windows:**
- Open Notepad as Administrator
- Open `C:\Windows\System32\drivers\etc\hosts`
- Add: `192.168.0.124  gomofos.com www.gomofos.com`

### Path B — Port Forwarding (public access via your router)
1. Find your **public IP**: `curl ifconfig.me` (from any device on your network)
2. Log in to your router admin panel (usually `http://192.168.0.1`)
3. Set up port forwarding:
   - External port `80` → `192.168.0.124:80`
   - External port `443` → `192.168.0.124:443`
4. At your DNS registrar, add A records:
   ```
   @       A    YOUR_PUBLIC_IP
   www     A    YOUR_PUBLIC_IP
   ```
5. **Optional but recommended:** request a static public IP from your ISP, or use a Dynamic DNS service if your public IP changes.

### Path C — Cloudflare Tunnel (no port forwarding needed)
1. Sign up at https://cloudflare.com (free)
2. Add `gomofos.com` to Cloudflare — update your domain's nameservers as instructed
3. We'll set up the tunnel in **PART 8** below. For now, just complete the Cloudflare account setup.

### Verify DNS (Paths B & C only)
```bash
dig gomofos.com +short
# Path B: should return your public IP
# Path C: returns Cloudflare's IPs (this is correct)
```

---

## PART 2: Initial Server Setup

SSH into your Ubuntu server (from a device on the same LAN):
```bash
ssh your_username@192.168.0.124
```

### Update the system
```bash
sudo apt update && sudo apt upgrade -y
```

### Install required packages
```bash
sudo apt install -y python3.11 python3.11-venv python3-pip nodejs npm nginx git curl ufw unzip
```

### Install Yarn (we use yarn, NOT npm)
```bash
sudo npm install -g yarn
```

### Install MongoDB 7.0
```bash
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt update
sudo apt install -y mongodb-org
sudo systemctl enable mongod
sudo systemctl start mongod
sudo systemctl status mongod   # verify it's running
```

### Configure firewall
```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable
sudo ufw status
```

---

## PART 3: Get the Code onto Your Server

You have two options. Choose one.

### Option A — Push from Emergent to GitHub, then clone (recommended)
1. In the Emergent app interface, push your code to GitHub (use the GitHub button)
2. On your server:
   ```bash
   sudo mkdir -p /var/www && cd /var/www
   sudo git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git gomofos
   sudo chown -R $USER:$USER /var/www/gomofos
   cd gomofos
   ```

### Option B — Download as ZIP and upload via SCP
1. In Emergent, click "Download Code" to get the project zip
2. From your local machine (same LAN as the server):
   ```bash
   scp gomofos.zip your_username@192.168.0.124:/tmp/
   ```
3. On the server:
   ```bash
   sudo mkdir -p /var/www/gomofos && sudo chown -R $USER:$USER /var/www/gomofos
   cd /var/www/gomofos
   unzip /tmp/gomofos.zip
   ```

After either option, you should have `/var/www/gomofos/backend/` and `/var/www/gomofos/frontend/`.

---

## PART 4: Backend Setup

```bash
cd /var/www/gomofos/backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/
```

### Generate a secure JWT secret
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
# Copy the output - you'll paste it into .env below
```

### Create production `.env` for backend
```bash
nano /var/www/gomofos/backend/.env
```

**For Path A (LAN-only, HTTP):**
```
MONGO_URL="mongodb://localhost:27017"
DB_NAME="gomofos_prod"
CORS_ORIGINS="http://gomofos.com,http://www.gomofos.com,http://192.168.0.124"
STRIPE_API_KEY="sk_test_emergent"
JWT_SECRET="PASTE_THE_GENERATED_HEX_FROM_ABOVE"
ADMIN_EMAIL="admin@gomofos.com"
ADMIN_PASSWORD="CHANGE_THIS_TO_A_STRONG_PASSWORD"
FRONTEND_URL="http://gomofos.com"
```

**For Path B or C (public, HTTPS):**
```
MONGO_URL="mongodb://localhost:27017"
DB_NAME="gomofos_prod"
CORS_ORIGINS="https://gomofos.com,https://www.gomofos.com"
STRIPE_API_KEY="sk_live_YOUR_PRODUCTION_STRIPE_KEY"
JWT_SECRET="PASTE_THE_GENERATED_HEX_FROM_ABOVE"
ADMIN_EMAIL="admin@gomofos.com"
ADMIN_PASSWORD="CHANGE_THIS_TO_A_STRONG_PASSWORD"
FRONTEND_URL="https://gomofos.com"
```

Save (Ctrl+O, Enter, Ctrl+X).

### Update `server.py` cookie security
**For Paths B & C (HTTPS):**
```bash
sed -i 's/secure=False/secure=True/g' /var/www/gomofos/backend/server.py
sed -i 's/samesite="lax"/samesite="strict"/g' /var/www/gomofos/backend/server.py
```

**For Path A (HTTP):** leave defaults — `secure=True` would block cookies on plain HTTP.

### Test backend runs
```bash
cd /var/www/gomofos/backend
source venv/bin/activate
uvicorn server:app --host 0.0.0.0 --port 8001
# You should see "Application startup complete". Hit Ctrl+C to stop.
```

---

## PART 5: Frontend Setup

```bash
cd /var/www/gomofos/frontend
```

### Update frontend `.env` for production
```bash
nano /var/www/gomofos/frontend/.env
```

**For Path A (HTTP):**
```
REACT_APP_BACKEND_URL=http://gomofos.com
WDS_SOCKET_PORT=80
```

**For Path B or C (HTTPS):**
```
REACT_APP_BACKEND_URL=https://gomofos.com
WDS_SOCKET_PORT=443
```

Save and exit.

### Build the production frontend
```bash
yarn install
yarn build
```

This creates an optimized `build/` folder containing static files Nginx will serve.

---

## PART 6: Run Backend as a systemd Service

Create the service file:
```bash
sudo nano /etc/systemd/system/gomofos-backend.service
```

Paste:
```ini
[Unit]
Description=Gomofos Backend (FastAPI)
After=network.target mongod.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/gomofos/backend
Environment="PATH=/var/www/gomofos/backend/venv/bin"
ExecStart=/var/www/gomofos/backend/venv/bin/uvicorn server:app --host 0.0.0.0 --port 8001 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Set ownership and enable the service:
```bash
sudo chown -R www-data:www-data /var/www/gomofos
sudo systemctl daemon-reload
sudo systemctl enable gomofos-backend
sudo systemctl start gomofos-backend
sudo systemctl status gomofos-backend   # verify running
```

If something is wrong, check logs:
```bash
sudo journalctl -u gomofos-backend -f
```

---

## PART 7: Nginx Configuration

Remove default Nginx site and create our config:
```bash
sudo rm -f /etc/nginx/sites-enabled/default
sudo nano /etc/nginx/sites-available/gomofos
```

Paste this config:
```nginx
server {
    listen 80;
    server_name gomofos.com www.gomofos.com 192.168.0.124;

    # Frontend - serve static React build
    root /var/www/gomofos/frontend/build;
    index index.html;

    # API requests → Backend
    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # React Router - serve index.html for all unmatched routes
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Long cache for static assets
    location /static/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    client_max_body_size 10M;
}
```

Save, enable, test, reload:
```bash
sudo ln -s /etc/nginx/sites-available/gomofos /etc/nginx/sites-enabled/
sudo nginx -t        # must say: syntax is ok / test is successful
sudo systemctl reload nginx
```

### Verify (varies by path):
- **Path A:** From any device on the same LAN with the hosts file edited, visit `http://gomofos.com`
- **Path B:** From outside your network, visit `http://gomofos.com` (port forwarding active)
- **Path C:** Continue to Part 8

---

## PART 8: SSL Certificate (Path-specific)

### Path A — Self-signed certificate (LAN-only)
Browsers will show a "not secure" warning that users must dismiss. Acceptable for internal/dev.

```bash
sudo mkdir -p /etc/nginx/ssl
sudo openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/gomofos.key \
  -out /etc/nginx/ssl/gomofos.crt \
  -subj "/CN=gomofos.com"
```

Then edit `/etc/nginx/sites-available/gomofos` and add a second server block:
```nginx
server {
    listen 443 ssl;
    server_name gomofos.com www.gomofos.com 192.168.0.124;

    ssl_certificate /etc/nginx/ssl/gomofos.crt;
    ssl_certificate_key /etc/nginx/ssl/gomofos.key;

    root /var/www/gomofos/frontend/build;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }

    client_max_body_size 10M;
}
```

Reload: `sudo nginx -t && sudo systemctl reload nginx`

### Path B — Let's Encrypt via certbot (port forwarding active)
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d gomofos.com -d www.gomofos.com
```

When prompted:
- Enter your email
- Agree to terms (A)
- Choose option `2` to redirect HTTP → HTTPS

Verify auto-renewal:
```bash
sudo certbot renew --dry-run
```

### Path C — Cloudflare Tunnel (recommended for production)
This routes traffic through Cloudflare without needing port forwarding. SSL is handled by Cloudflare.

```bash
# Install cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o /tmp/cloudflared.deb
sudo dpkg -i /tmp/cloudflared.deb

# Login (opens a URL — copy/paste to a browser, select gomofos.com)
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create gomofos

# Configure tunnel
mkdir -p ~/.cloudflared
nano ~/.cloudflared/config.yml
```

Paste:
```yaml
tunnel: gomofos
credentials-file: /root/.cloudflared/<TUNNEL-ID>.json

ingress:
  - hostname: gomofos.com
    service: http://localhost:80
  - hostname: www.gomofos.com
    service: http://localhost:80
  - service: http_status:404
```

Replace `<TUNNEL-ID>` with the ID `cloudflared tunnel create` printed.

```bash
# Route DNS
cloudflared tunnel route dns gomofos gomofos.com
cloudflared tunnel route dns gomofos www.gomofos.com

# Install as service
sudo cloudflared service install
sudo systemctl start cloudflared
sudo systemctl enable cloudflared
sudo systemctl status cloudflared
```

In Cloudflare Dashboard → SSL/TLS → set encryption to **Full** or **Flexible**. Visit `https://gomofos.com` — should work with valid SSL.

---

## PART 9: Switch to Production Stripe Keys (Paths B & C only)

Skip this for Path A — keep test key `sk_test_emergent`.

1. Go to https://dashboard.stripe.com → switch to **Live mode** (toggle top-right)
2. Developers → API keys → copy your **Secret key** (starts with `sk_live_...`)
3. Update your backend `.env`:
   ```bash
   sudo nano /var/www/gomofos/backend/.env
   ```
   Replace the `STRIPE_API_KEY` value with your live key.
4. Restart backend:
   ```bash
   sudo systemctl restart gomofos-backend
   ```

### Configure Stripe webhook
1. Stripe Dashboard → Developers → Webhooks → Add endpoint
2. URL: `https://gomofos.com/api/webhook/stripe`
3. Events: select `checkout.session.completed`, `checkout.session.expired`

---

## PART 10: Final Verification Checklist

```bash
# 1. Backend healthy (from server itself)
curl http://localhost:8001/api/leaderboard
# Should return: []  (empty array)

# 2. Through Nginx (from same LAN)
curl http://192.168.0.124/api/leaderboard
# Should return: []

# 3. Through domain
# Path A: from LAN device with hosts edit
curl -k https://gomofos.com/api/leaderboard
# Path B/C: from anywhere
curl https://gomofos.com/api/leaderboard

# 4. Service status
sudo systemctl status gomofos-backend
sudo systemctl status nginx
sudo systemctl status mongod
```

Open `http(s)://gomofos.com` in a browser and verify:
- ✅ Landing page loads
- ✅ Can register/login
- ✅ Dashboard appears
- ✅ Can add game, create tournament

---

## DAILY OPERATIONS

### Deploy updates after code changes
```bash
cd /var/www/gomofos
git pull origin main       # if using git

# Backend changes
cd backend && source venv/bin/activate && pip install -r requirements.txt
sudo systemctl restart gomofos-backend

# Frontend changes
cd ../frontend && yarn install && yarn build
# No restart needed - Nginx serves files directly
```

### View logs
```bash
sudo journalctl -u gomofos-backend -f       # Backend (real-time)
sudo tail -f /var/log/nginx/access.log      # Nginx access
sudo tail -f /var/log/nginx/error.log       # Nginx errors
sudo journalctl -u cloudflared -f           # Cloudflare tunnel (Path C only)
```

### Restart services
```bash
sudo systemctl restart gomofos-backend
sudo systemctl restart nginx
sudo systemctl restart mongod
```

### Backup MongoDB (set up weekly cron)
```bash
mongodump --db gomofos_prod --out /var/backups/mongo-$(date +%F)
```

---

## SECURITY HARDENING

### 1. Disable root SSH
```bash
sudo nano /etc/ssh/sshd_config
# Set: PermitRootLogin no
sudo systemctl reload sshd
```

### 2. Enable MongoDB auth (production)
Create admin user, then enable `security.authorization: enabled` in `/etc/mongod.conf`. Update `MONGO_URL` with credentials.

### 3. Fail2ban (blocks brute-force SSH)
```bash
sudo apt install -y fail2ban
sudo systemctl enable fail2ban
```

### 4. Automatic security updates
```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

---

## TROUBLESHOOTING

| Issue | Fix |
|---|---|
| `gomofos.com` won't resolve | Path A: check `hosts` file. Path B: verify DNS + port forwarding. Path C: check `cloudflared` status |
| 502 Bad Gateway | Backend down → `sudo systemctl status gomofos-backend` |
| CORS errors | Verify `CORS_ORIGINS` in backend `.env` matches your URL exactly (http vs https) |
| Login works but `/me` fails | Cookies blocked: HTTP → set `secure=False`; HTTPS → `secure=True` |
| Stripe redirect breaks | `FRONTEND_URL` in backend `.env` must match the URL users actually visit |
| `yarn build` fails (low RAM) | Add swap: `sudo fallocate -l 2G /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile` |
| Can reach from one LAN device, not another | Hosts file not updated on that device (Path A only) |

---

## LEGAL / COMPLIANCE NOTE

Real-money gaming/betting platforms are regulated in **Australia** under the Interactive Gambling Act 2001 and require AUSTRAC registration plus a state/territory wagering license. Before going live with real money:

- Consult a lawyer specializing in Australian gambling law
- Consider starting with **virtual currency only** (no real-money stakes) until properly licensed
- Implement KYC/AML, responsible gambling features (deposit limits, self-exclusion), and age verification

You can run the platform in "play money" mode by disabling the Stripe deposit endpoint and seeding users with virtual credits.
