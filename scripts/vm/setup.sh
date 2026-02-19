#!/usr/bin/env bash
# One-shot VM setup for awesome-asr. Run as root (sudo bash setup.sh).
set -euo pipefail

APP_DIR="/opt/awesome-asr"
REPO_DIR="${APP_DIR}/repo"
VENV_DIR="${APP_DIR}/venv"
LOG_DIR="${APP_DIR}/logs"
APP_USER="asr"
GITHUB_REPO="${GITHUB_REPO:?Set GITHUB_REPO env var (e.g. export GITHUB_REPO=https://github.com/user/repo.git)}"

echo "=== awesome-asr VM setup ==="

# 1. System packages
echo "[1/8] Installing system packages..."
apt-get update
apt-get install -y --no-install-recommends \
  python3.11 python3.11-venv python3.11-dev \
  ffmpeg git curl gnupg software-properties-common \
  nginx

# 2. Install GitHub CLI
echo "[2/8] Installing GitHub CLI..."
if ! command -v gh &>/dev/null; then
  curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    > /etc/apt/sources.list.d/github-cli.list
  apt-get update
  apt-get install -y gh
fi

# 3. Install Node.js 20 + markmap-cli
echo "[3/8] Installing Node.js and markmap-cli..."
if ! command -v node &>/dev/null; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs
fi
npm install -g markmap-cli 2>/dev/null || true

# 4. Create app user and directories
echo "[4/8] Creating app user and directories..."
id "$APP_USER" &>/dev/null || useradd -r -m -s /bin/bash "$APP_USER"
mkdir -p "$APP_DIR" "$LOG_DIR"

# 5. Clone repo
echo "[5/8] Cloning repository..."
if [[ -d "$REPO_DIR" ]]; then
  echo "  Repo already exists, pulling latest..."
  git -C "$REPO_DIR" pull --ff-only origin main || true
else
  git clone "$GITHUB_REPO" "$REPO_DIR"
fi

# 6. Python virtual environment
echo "[6/8] Setting up Python venv..."
python3.11 -m venv "$VENV_DIR"
"${VENV_DIR}/bin/pip" install --upgrade pip
"${VENV_DIR}/bin/pip" install -r "${REPO_DIR}/requirements.txt" soundfile

# 7. Copy run-job.sh to app directory
cp "${REPO_DIR}/scripts/vm/run-job.sh" "${APP_DIR}/run-job.sh"
chmod +x "${APP_DIR}/run-job.sh"

# Set ownership
chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

# 8. Install systemd service for Gunicorn
echo "[7/8] Installing systemd service..."
cat > /etc/systemd/system/awesome-asr-web.service << 'EOF'
[Unit]
Description=Awesome ASR Web App
After=network.target

[Service]
Type=simple
User=asr
WorkingDirectory=/opt/awesome-asr/repo
ExecStart=/opt/awesome-asr/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 web.app:app
Restart=on-failure
RestartSec=10s
EnvironmentFile=/opt/awesome-asr/.env

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable awesome-asr-web

# 9. Install Nginx config
echo "[8/8] Configuring Nginx..."
cat > /etc/nginx/sites-available/awesome-asr << 'EOF'
server {
    listen 80 default_server;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    # Serve podcast audio files directly
    location /podcasts/audio/ {
        alias /opt/awesome-asr/repo/podcasts/audio/;
    }
}
EOF

rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/awesome-asr /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
systemctl enable nginx

# 10. Install crontab for the asr user
echo "Installing crontab..."
cat > /tmp/asr-crontab << 'EOF'
# awesome-asr scheduled jobs (times in UTC)
# Daily tracker at 06:00 UTC
0 6 * * * /opt/awesome-asr/run-job.sh daily
# Podcast generator at 08:00 UTC
0 8 * * * /opt/awesome-asr/run-job.sh podcast
# Mindmap generator at 14:00 UTC on Sundays
0 14 * * 0 /opt/awesome-asr/run-job.sh mindmap
EOF
crontab -u "$APP_USER" /tmp/asr-crontab
rm /tmp/asr-crontab

echo
echo "=== Setup complete ==="
echo
echo "Next steps:"
echo "  1. Create the .env file with your secrets:"
echo "     sudo nano /opt/awesome-asr/.env"
echo
echo "     Required keys:"
echo "       GEMINI_API_KEY=..."
echo "       GITHUB_PAT=..."
echo "       HF_TOKEN=..."
echo
echo "     Optional keys:"
echo "       TWITTER_BEARER_TOKEN=..."
echo "       SMTP_HOST=... SMTP_PORT=... SMTP_USER=... SMTP_PASSWORD=... SMTP_FROM_ADDRESS=..."
echo "       SITE_URL=http://<your-vm-ip>"
echo
echo "  2. Start the web app:"
echo "     sudo systemctl start awesome-asr-web"
echo
echo "  3. Test a job:"
echo "     sudo -u asr /opt/awesome-asr/run-job.sh daily"
echo
echo "  4. Check crontab:"
echo "     sudo crontab -u asr -l"
