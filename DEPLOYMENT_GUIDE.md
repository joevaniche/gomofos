# Deployment Guide: gomofos.com via Cloudflare Tunnel

**Server:** Ubuntu Server @ `192.168.0.124` (LAN)
**Domain:** `gomofos.com`
**Method:** Cloudflare Tunnel (no port forwarding, free SSL, IP stays hidden)

Estimated time: **45-60 minutes** total.

---

## CHECKLIST (Tick as you go)

- [ ] **Part 1:** Cloudflare account + domain setup
- [ ] **Part 2:** Install server packages
- [ ] **Part 3:** Get code onto server
- [ ] **Part 4:** Backend setup
- [ ] **Part 5:** Frontend build
- [ ] **Part 6:** Systemd service
- [ ] **Part 7:** Nginx config
- [ ] **Part 8:** Cloudflare Tunnel
- [ ] **Part 9:** Stripe production keys
- [ ] **Part 10:** Verify everything works

---

## PART 1: Cloudflare Setup (~10 min, do this FIRST)

1. **Sign up at https://dash.cloudflare.com/sign-up** (free tier is fine)

2. **Add your domain:**
   - Click "Add a Site" → enter `gomofos.com`
   - Select the **Free plan**
   - Cloudflare will scan existing DNS records (it's OK if there are none)

3. **Change nameservers at your domain registrar:**
   - Cloudflare will show you 2 nameservers, e.g.:
     ```
     adam.ns.cloudflare.com
     beth.ns.cloudflare.com
     ```
   - Log in to where you bought `gomofos.com` (GoDaddy, Namecheap, etc.)
   - Find DNS / Nameserver settings → replace existing nameservers with Cloudflare's
   - **Save and wait 5-60 minutes** for propagation
   - You'll get an email from Cloudflare when active

4. **Verify Cloudflare is active:**
   ```bash
   dig NS gomofos.com +short
   # Should show the two cloudflare.com nameservers
   ```

5. **In Cloudflare dashboard → SSL/TLS → Overview:**
   - Set encryption mode to **Full** (NOT Flexible — Flexible breaks login cookies)

Proceed to Part 2 while waiting for nameservers to propagate.

---

## PART 2: Install Server Packages (~10 min)

SSH into your server:
```bash
ssh your_username@192.168.0.124
```

### Update + install everything
```bash
sudo apt update && sudo apt upgrade -y

sudo apt install -y python3.11 python3.11-venv python3-pip nodejs npm nginx git curl ufw unzip

sudo npm install -g yarn
```

### Install MongoDB 7.0
```bash
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor

echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list

sudo apt update
sudo apt install -y mongodb-org
sudo systemctl enable --now mongod
sudo systemctl status mongod   # press 'q' to exit
```

### Configure firewall (LAN-only since Cloudflare Tunnel handles external traffic)
```bash
sudo ufw allow OpenSSH
sudo ufw allow from 192.168.0.0/24 to any port 80
sudo ufw --force enable
sudo ufw status
```

---

## PART 3: Get the Code onto Your Server (~5 min)

### Option A — GitHub (recommended)
1. In Emergent chat, click the **GitHub** button to push code to a repo (e.g., `gomofos`)
2. On the server:
   ```bash
   sudo mkdir -p /var/www && cd /var/www
   sudo git clone https://github.com/YOUR_USERNAME/gomofos.git
   sudo chown -R $USER:$USER /var/www/gomofos
   ```

### Option B — SCP a zip
1. In Emergent, click **Download Code**
2. From your local machine:
   ```bash
   scp ~/Downloads/gomofos.zip your_username@192.168.0.124:/tmp/
   ```
3. On the server:
   ```bash
   sudo mkdir -p /var/www/gomofos && sudo chown -R $USER:$USER /var/www/gomofos
   cd /var/www/gomofos && unzip /tmp/gomofos.zip
   ```

Verify: `ls /var/www/gomofos` should show `backend/` and `frontend/`.

---

## PART 4: Backend Setup (~10 min)

```bash
cd /var/www/gomofos/backend
python3.11 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/
```

### Generate JWT secret
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```
**Copy the output** — you'll paste it below.

### Create production `.env`
```bash
nano /var/www/gomofos/backend/.env
```

Paste this (replace the placeholders marked with `<<<`):
```
MONGO_URL="mongodb://localhost:27017"
DB_NAME="gomofos_prod"
CORS_ORIGINS="https://gomofos.com,https://www.gomofos.com"
STRIPE_API_KEY="sk_test_emergent"
JWT_SECRET="<<< PASTE THE HEX FROM ABOVE >>>"
ADMIN_EMAIL="admin@gomofos.com"
ADMIN_PASSWORD="<<< CHOOSE A STRONG PASSWORD >>>"
FRONTEND_URL="https://gomofos.com"
```

> Keep `sk_test_emergent` for now — we'll swap to live Stripe keys in Part 9 after everything works.

Save: Ctrl+O, Enter, Ctrl+X.

### Enable HTTPS-secure cookies
```bash
sed -i 's/secure=False/secure=True/g' /var/www/gomofos/backend/server.py
```

### Test backend boots
```bash
cd /var/www/gomofos/backend
source venv/bin/activate
uvicorn server:app --host 0.0.0.0 --port 8001
# Look for "Application startup complete" — then press Ctrl+C
```

---

## PART 5: Frontend Build (~5 min)

```bash
cd /var/www/gomofos/frontend
nano .env
```

Replace contents with:
```
REACT_APP_BACKEND_URL=https://gomofos.com
WDS_SOCKET_PORT=443
```

Save and build:
```bash
yarn install
yarn build
```

This may take 2-3 minutes. Output goes to `/var/www/gomofos/frontend/build/`.

> **If `yarn build` runs out of memory** on a small server, add swap first:
> ```bash
> sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
> sudo mkswap /swapfile && sudo swapon /swapfile
> ```

---

## PART 6: Systemd Service for Backend (~3 min)

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

Set ownership + start:
```bash
sudo chown -R www-data:www-data /var/www/gomofos
sudo systemctl daemon-reload
sudo systemctl enable --now gomofos-backend
sudo systemctl status gomofos-backend
```

Test locally:
```bash
curl http://localhost:8001/api/leaderboard
# Should return: []
```

If you see errors: `sudo journalctl -u gomofos-backend -n 50`

---

## PART 7: Nginx Config (~5 min)

```bash
sudo rm -f /etc/nginx/sites-enabled/default
sudo nano /etc/nginx/sites-available/gomofos
```

Paste:
```nginx
server {
    listen 80;
    server_name gomofos.com www.gomofos.com;

    root /var/www/gomofos/frontend/build;
    index index.html;

    # Trust Cloudflare's forwarded protocol header
    set_real_ip_from 0.0.0.0/0;
    real_ip_header CF-Connecting-IP;

    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $http_cf_connecting_ip;
        proxy_set_header X-Forwarded-For $http_cf_connecting_ip;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 300s;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /static/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    client_max_body_size 10M;
}
```

Enable + reload:
```bash
sudo ln -s /etc/nginx/sites-available/gomofos /etc/nginx/sites-enabled/
sudo nginx -t        # must say "test is successful"
sudo systemctl reload nginx
```

Verify locally:
```bash
curl http://localhost/api/leaderboard
# Should return: []
```

---

## PART 8: Cloudflare Tunnel (~10 min)

### Install cloudflared
```bash
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o /tmp/cloudflared.deb
sudo dpkg -i /tmp/cloudflared.deb

cloudflared --version    # verify install
```

### Authenticate
```bash
cloudflared tunnel login
```
This prints a URL. Copy it, open in your browser, log in, and **authorize `gomofos.com`**. The terminal will then continue.

### Create the tunnel
```bash
cloudflared tunnel create gomofos
```
This prints the **tunnel ID** (a UUID) and creates a credentials JSON file. Note the tunnel ID — you'll need it next.

### Configure the tunnel
```bash
sudo mkdir -p /etc/cloudflared
sudo nano /etc/cloudflared/config.yml
```

Paste (replace `<TUNNEL-ID>` with the UUID from above, and `<YOUR-USER>` with your Linux username):
```yaml
tunnel: <TUNNEL-ID>
credentials-file: /home/<YOUR-USER>/.cloudflared/<TUNNEL-ID>.json

ingress:
  - hostname: gomofos.com
    service: http://localhost:80
  - hostname: www.gomofos.com
    service: http://localhost:80
  - service: http_status:404
```

### Route DNS through Cloudflare
```bash
cloudflared tunnel route dns gomofos gomofos.com
cloudflared tunnel route dns gomofos www.gomofos.com
```

This auto-creates CNAME records in Cloudflare pointing to your tunnel.

### Install as systemd service
```bash
sudo cloudflared --config /etc/cloudflared/config.yml service install
sudo systemctl enable --now cloudflared
sudo systemctl status cloudflared
```

### Test!
Open `https://gomofos.com` in your browser. You should see your landing page with a valid SSL padlock 🔒.

If something is wrong:
```bash
sudo journalctl -u cloudflared -f
```

---

## PART 9: Stripe Production Keys (~5 min)

Once everything works with the test key, switch to live mode:

1. Go to https://dashboard.stripe.com → toggle **Live mode** (top right)
2. Developers → API keys → copy **Secret key** (starts with `sk_live_`)
3. Update backend `.env`:
   ```bash
   sudo nano /var/www/gomofos/backend/.env
   ```
   Replace `STRIPE_API_KEY="sk_test_emergent"` with your live key.
4. Restart:
   ```bash
   sudo systemctl restart gomofos-backend
   ```

### Configure Stripe webhook
1. Stripe Dashboard → Developers → Webhooks → **Add endpoint**
2. URL: `https://gomofos.com/api/webhook/stripe`
3. Select events: `checkout.session.completed`, `checkout.session.expired`
4. Save

---

## PART 10: Verify Everything Works

```bash
# Backend healthy on the server
curl http://localhost:8001/api/leaderboard

# Public site live
curl https://gomofos.com/api/leaderboard

# All services running
sudo systemctl status gomofos-backend nginx mongod cloudflared
```

In your browser at `https://gomofos.com`:
- ✅ Landing page loads with SSL padlock
- ✅ Register a new account (e.g., `test@example.com` / `Test1234`)
- ✅ Login works, dashboard appears
- ✅ Add a game (e.g., "FIFA 25" / "PS5")
- ✅ Create a tournament (you'll need wallet balance — see below)
- ✅ Visit `/wallet`, deposit $10 → redirects to Stripe checkout
- ✅ Use Stripe test card `4242 4242 4242 4242` (any future date, any CVC)
- ✅ Return to wallet → balance updated

**Admin login:** `admin@gomofos.com` / (the password you set in `.env`)

---

## OPERATIONS CHEAT SHEET

### Deploy updates
```bash
cd /var/www/gomofos && git pull origin main

# Backend
cd backend && source venv/bin/activate && pip install -r requirements.txt
sudo systemctl restart gomofos-backend

# Frontend
cd ../frontend && yarn install && yarn build
# (No restart needed)
```

### Logs
```bash
sudo journalctl -u gomofos-backend -f       # Backend
sudo journalctl -u cloudflared -f           # Tunnel
sudo tail -f /var/log/nginx/access.log      # Nginx
```

### Restart anything
```bash
sudo systemctl restart gomofos-backend
sudo systemctl restart nginx
sudo systemctl restart cloudflared
sudo systemctl restart mongod
```

### Weekly MongoDB backup (set as cron job)
```bash
sudo crontab -e
# Add this line:
0 3 * * 0 mongodump --db gomofos_prod --out /var/backups/mongo-$(date +\%F)
```

---

## SECURITY HARDENING (Recommended after launch)

```bash
# Disable root SSH
sudo sed -i 's/#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl reload sshd

# Fail2ban (blocks SSH brute force)
sudo apt install -y fail2ban
sudo systemctl enable --now fail2ban

# Auto security updates
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

Enable MongoDB authentication once you're past initial testing (not required for tunneled, localhost-only Mongo, but good practice).

---

## TROUBLESHOOTING QUICK FIXES

| Problem | Try this |
|---|---|
| `https://gomofos.com` shows Cloudflare error 1033 | Tunnel not running: `sudo systemctl status cloudflared` |
| Site loads, but API returns 502 | Backend down: `sudo systemctl status gomofos-backend` |
| Login works once but `/me` fails | Cloudflare SSL/TLS set to "Flexible" instead of "Full" |
| CORS errors in browser console | `CORS_ORIGINS` in `.env` doesn't match `https://gomofos.com` exactly |
| Stripe redirect goes to wrong URL | `FRONTEND_URL` in `.env` not set to `https://gomofos.com` |
| `yarn build` killed (out of memory) | Add swap (see Part 5 note) |
| `cloudflared tunnel login` URL won't open | Copy the URL manually, open on any device, authorize |

---

## ⚖️ LEGAL REMINDER

Real-money gambling/staking in Australia is regulated under the **Interactive Gambling Act 2001** and requires **AUSTRAC registration** plus a state/territory wagering license. Before processing real money stakes:

- Consult an Australian gambling-law lawyer
- Consider launching in **play-money mode** first (disable Stripe deposits, seed virtual credits)
- Implement KYC/AML, age verification, deposit limits, and self-exclusion

Stripe will also block your account if it detects unlicensed gambling activity, so get licensed first.

---

You're done! 🎮 Ping me if you hit any issues — paste the exact error and the command/step you were on.
