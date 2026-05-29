# Ubuntu Server Deployment Guide - levelsquared.com.au

Complete deployment guide for the Esports Bet platform on Ubuntu Server (22.04 / 24.04 LTS).

## Architecture
```
Internet → Nginx (80/443) → ├── Frontend (static build, served by Nginx)
                            └── Backend (FastAPI on port 8001) → MongoDB (port 27017)
```

---

## PART 1: DNS Setup (Do this FIRST)

Before touching the server, point your domain to your server's IP address.

1. Log in to your domain registrar (where you bought `levelsquared.com.au`)
2. Add these DNS A records:
   ```
   @       A    YOUR_SERVER_IP    (e.g., 203.0.113.45)
   www     A    YOUR_SERVER_IP
   ```
3. Wait 5-30 mins for DNS to propagate. Verify with:
   ```bash
   dig levelsquared.com.au +short
   # Should return your server's IP
   ```

---

## PART 2: Initial Server Setup

SSH into your Ubuntu server:
```bash
ssh your_username@YOUR_SERVER_IP
```

### Update the system
```bash
sudo apt update && sudo apt upgrade -y
```

### Install required packages
```bash
sudo apt install -y python3.11 python3.11-venv python3-pip nodejs npm nginx git curl ufw
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
1. In the Emergent app interface, push your code to GitHub (use the GitHub button in the chat)
2. On your server:
   ```bash
   cd /var/www
   sudo mkdir -p esportsbet && sudo chown -R $USER:$USER esportsbet
   cd esportsbet
   git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git .
   ```

### Option B — Download as ZIP and upload via SCP
1. In Emergent, click "Download Code"
2. From your local machine:
   ```bash
   scp esportsbet.zip your_username@YOUR_SERVER_IP:/tmp/
   ```
3. On the server:
   ```bash
   sudo mkdir -p /var/www/esportsbet && sudo chown -R $USER:$USER /var/www/esportsbet
   cd /var/www/esportsbet
   unzip /tmp/esportsbet.zip
   ```

After either option, you should have `/var/www/esportsbet/backend/` and `/var/www/esportsbet/frontend/`.

---

## PART 4: Backend Setup

```bash
cd /var/www/esportsbet/backend

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
nano /var/www/esportsbet/backend/.env
```

Paste this (replace placeholders):
```
MONGO_URL="mongodb://localhost:27017"
DB_NAME="esportsbet_prod"
CORS_ORIGINS="https://levelsquared.com.au,https://www.levelsquared.com.au"
STRIPE_API_KEY="sk_live_YOUR_PRODUCTION_STRIPE_KEY"
JWT_SECRET="PASTE_THE_GENERATED_HEX_FROM_ABOVE"
ADMIN_EMAIL="admin@levelsquared.com.au"
ADMIN_PASSWORD="CHANGE_THIS_TO_A_STRONG_PASSWORD"
FRONTEND_URL="https://levelsquared.com.au"
```

Save (Ctrl+O, Enter, Ctrl+X).

### Update `server.py` cookie security for HTTPS
The current dev code has `secure=False` for cookies. For production HTTPS, edit `/var/www/esportsbet/backend/server.py` and find both `set_cookie` calls — change `secure=False` to `secure=True` and `samesite="lax"` to `samesite="strict"` for better security.

```bash
sed -i 's/secure=False/secure=True/g' /var/www/esportsbet/backend/server.py
sed -i 's/samesite="lax"/samesite="strict"/g' /var/www/esportsbet/backend/server.py
```

### Test backend runs
```bash
cd /var/www/esportsbet/backend
source venv/bin/activate
uvicorn server:app --host 0.0.0.0 --port 8001
# You should see "Application startup complete". Hit Ctrl+C to stop.
```

---

## PART 5: Frontend Setup

```bash
cd /var/www/esportsbet/frontend
```

### Update frontend `.env` for production
```bash
nano /var/www/esportsbet/frontend/.env
```

Replace contents with:
```
REACT_APP_BACKEND_URL=https://levelsquared.com.au
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
sudo nano /etc/systemd/system/esportsbet-backend.service
```

Paste:
```ini
[Unit]
Description=Esports Bet Backend (FastAPI)
After=network.target mongod.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/esportsbet/backend
Environment="PATH=/var/www/esportsbet/backend/venv/bin"
ExecStart=/var/www/esportsbet/backend/venv/bin/uvicorn server:app --host 0.0.0.0 --port 8001 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Set ownership and enable the service:
```bash
sudo chown -R www-data:www-data /var/www/esportsbet
sudo systemctl daemon-reload
sudo systemctl enable esportsbet-backend
sudo systemctl start esportsbet-backend
sudo systemctl status esportsbet-backend   # verify running
```

If something is wrong, check logs:
```bash
sudo journalctl -u esportsbet-backend -f
```

---

## PART 7: Nginx Configuration

Remove default Nginx site and create our config:
```bash
sudo rm /etc/nginx/sites-enabled/default
sudo nano /etc/nginx/sites-available/levelsquared
```

Paste this config:
```nginx
server {
    listen 80;
    server_name levelsquared.com.au www.levelsquared.com.au;

    # Frontend - serve static React build
    root /var/www/esportsbet/frontend/build;
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

    # Stripe webhook (no SSL strip)
    location /api/webhook/stripe {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
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

    # Increase max upload size
    client_max_body_size 10M;
}
```

Save, enable, test, reload:
```bash
sudo ln -s /etc/nginx/sites-available/levelsquared /etc/nginx/sites-enabled/
sudo nginx -t        # must say: syntax is ok / test is successful
sudo systemctl reload nginx
```

Visit `http://levelsquared.com.au` — you should see your site (without HTTPS yet).

---

## PART 8: SSL Certificate (HTTPS) with Let's Encrypt

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d levelsquared.com.au -d www.levelsquared.com.au
```

When prompted:
- Enter your email (for renewal notices)
- Agree to terms (A)
- Choose option `2` to redirect HTTP → HTTPS

Certbot auto-edits your Nginx config and sets up auto-renewal. Verify auto-renewal works:
```bash
sudo certbot renew --dry-run
```

Now visit `https://levelsquared.com.au` — you should see your site with a padlock 🔒.

---

## PART 9: Switch to Production Stripe Keys

1. Go to https://dashboard.stripe.com → switch to **Live mode** (toggle top-right)
2. Developers → API keys → copy your **Secret key** (starts with `sk_live_...`)
3. Update your backend `.env`:
   ```bash
   sudo nano /var/www/esportsbet/backend/.env
   ```
   Replace the `STRIPE_API_KEY` value with your live key.
4. Restart backend:
   ```bash
   sudo systemctl restart esportsbet-backend
   ```

### Configure Stripe webhook (recommended)
1. In Stripe Dashboard → Developers → Webhooks → Add endpoint
2. URL: `https://levelsquared.com.au/api/webhook/stripe`
3. Events: select `checkout.session.completed`, `checkout.session.expired`
4. (Optional) copy webhook signing secret if you add signature verification later

---

## PART 10: Final Verification Checklist

```bash
# 1. Backend healthy
curl https://levelsquared.com.au/api/leaderboard
# Should return: []  (empty array)

# 2. Frontend loads
curl -I https://levelsquared.com.au
# Should return: HTTP/2 200

# 3. Service status
sudo systemctl status esportsbet-backend
sudo systemctl status nginx
sudo systemctl status mongod
```

Open `https://levelsquared.com.au` in a browser:
- ✅ Landing page loads
- ✅ Can register a new account
- ✅ Can login
- ✅ Dashboard appears
- ✅ Can add a game, create tournament, etc.

---

## DAILY OPERATIONS

### Deploy updates after code changes
```bash
cd /var/www/esportsbet
git pull origin main       # if using git

# Backend changes
cd backend && source venv/bin/activate && pip install -r requirements.txt
sudo systemctl restart esportsbet-backend

# Frontend changes
cd ../frontend && yarn install && yarn build
# No restart needed - Nginx serves files directly
```

### View logs
```bash
# Backend logs (real-time)
sudo journalctl -u esportsbet-backend -f

# Nginx access logs
sudo tail -f /var/log/nginx/access.log

# Nginx error logs
sudo tail -f /var/log/nginx/error.log
```

### Restart services
```bash
sudo systemctl restart esportsbet-backend
sudo systemctl restart nginx
sudo systemctl restart mongod
```

### Backup MongoDB (run weekly via cron)
```bash
mongodump --db esportsbet_prod --out /var/backups/mongo-$(date +%F)
```

---

## SECURITY HARDENING (Recommended)

### 1. Disable root SSH login
```bash
sudo nano /etc/ssh/sshd_config
# Set: PermitRootLogin no
sudo systemctl reload sshd
```

### 2. Enable MongoDB auth (for production)
Create admin user, then enable `security.authorization: enabled` in `/etc/mongod.conf`. Update `MONGO_URL` to include credentials.

### 3. Fail2ban (block brute-force SSH)
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
| 502 Bad Gateway | Backend down → `sudo systemctl status esportsbet-backend` + check logs |
| CORS errors | Verify `CORS_ORIGINS` in backend `.env` matches your domain exactly (with `https://`) |
| Login works but `/me` fails | Cookies blocked → ensure `secure=True` only when site is on HTTPS |
| Stripe redirect fails | `FRONTEND_URL` in backend `.env` must match your live domain |
| `yarn build` fails on low RAM | Add swap: `sudo fallocate -l 2G /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile` |
| Site doesn't load after DNS | Run `dig levelsquared.com.au +short` — must show your server IP |

---

## LEGAL / COMPLIANCE NOTE

Real-money gaming/betting platforms are regulated in **Australia** under the Interactive Gambling Act 2001 and require an AUSTRAC registration plus a state/territory wagering license. Before going live with real money:

- Consult a lawyer specializing in Australian gambling law
- Consider starting with **virtual currency only** (no real-money stakes) until you have proper licensing
- Implement KYC/AML checks, responsible gambling features (deposit limits, self-exclusion), and age verification

You can run the platform in "play money" mode by simply disabling the Stripe deposit endpoint and seeding users with virtual credits.
