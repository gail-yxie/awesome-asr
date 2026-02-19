#!/usr/bin/env bash
# Deploy a GCP Compute Engine VM for awesome-asr (website + cron jobs).
# Run this locally — requires gcloud CLI authenticated.
set -euo pipefail

PROJECT="${GCP_PROJECT:?Set GCP_PROJECT env var (e.g. export GCP_PROJECT=my-project-id)}"
ZONE="us-central1-a"
VM_NAME="awesome-asr-vm"
MACHINE_TYPE="e2-highmem-4"
DISK_SIZE="40GB"
IMAGE_FAMILY="ubuntu-2404-lts-amd64"
IMAGE_PROJECT="ubuntu-os-cloud"

echo "=== Deploying awesome-asr VM ==="
echo "Project:  $PROJECT"
echo "Zone:     $ZONE"
echo "Machine:  $MACHINE_TYPE (4 vCPU, 32GB RAM, ${DISK_SIZE} disk)"
echo

# 1. Enable Compute Engine API
echo "[1/4] Enabling Compute Engine API..."
gcloud services enable compute.googleapis.com --project="$PROJECT"

# 2. Create firewall rules for HTTP/HTTPS
echo "[2/4] Creating firewall rules..."
gcloud compute firewall-rules create allow-http \
  --project="$PROJECT" \
  --allow=tcp:80 \
  --target-tags=http-server \
  --description="Allow HTTP traffic" 2>/dev/null \
  || echo "  Firewall rule 'allow-http' already exists"

gcloud compute firewall-rules create allow-https \
  --project="$PROJECT" \
  --allow=tcp:443 \
  --target-tags=https-server \
  --description="Allow HTTPS traffic" 2>/dev/null \
  || echo "  Firewall rule 'allow-https' already exists"

# 3. Reserve a static external IP
echo "[3/4] Reserving static IP..."
gcloud compute addresses create awesome-asr-ip \
  --project="$PROJECT" \
  --region="${ZONE%-*}" 2>/dev/null \
  || echo "  Static IP 'awesome-asr-ip' already exists"

STATIC_IP=$(gcloud compute addresses describe awesome-asr-ip \
  --project="$PROJECT" \
  --region="${ZONE%-*}" \
  --format="value(address)")
echo "  Static IP: $STATIC_IP"

# 4. Create the VM
echo "[4/4] Creating VM instance..."
gcloud compute instances create "$VM_NAME" \
  --project="$PROJECT" \
  --zone="$ZONE" \
  --machine-type="$MACHINE_TYPE" \
  --boot-disk-size="$DISK_SIZE" \
  --boot-disk-type=pd-balanced \
  --image-family="$IMAGE_FAMILY" \
  --image-project="$IMAGE_PROJECT" \
  --address="$STATIC_IP" \
  --tags=http-server,https-server \
  --scopes=default 2>&1 \
  || echo "  VM '$VM_NAME' may already exist"

echo
echo "=== VM deployed ==="
echo
echo "Static IP: $STATIC_IP"
echo
echo "Next steps:"
echo "  1. SSH into the VM:"
echo "     gcloud compute ssh $VM_NAME --zone=$ZONE --project=$PROJECT"
echo
echo "  2. On the VM, clone the repo and run setup:"
echo "     git clone <your-repo-url> /tmp/awesome-asr-setup"
echo "     sudo bash /tmp/awesome-asr-setup/scripts/vm/setup.sh"
echo
echo "  3. Create the .env file:"
echo "     sudo nano /opt/awesome-asr/.env"
echo
echo "  4. Start the web service:"
echo "     sudo systemctl start awesome-asr-web"
