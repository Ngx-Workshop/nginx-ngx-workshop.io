## ngx-workshop.io - Nginx Reverse Proxy

This is the reverse proxy for your Ngx Workshop infrastructure. It proxies API and WebSocket requests to the NestJS server and optionally proxies frontend app requests to DigitalOcean Spaces or another Droplet.

### 🛠️ DigitalOcean Droplet setup `./bootstrap-nginx.sh`
Starting a new DigitalOcean Droplet? Use this script to set up Docker, UFW, and create the `/opt/nginx-ngx-workshop.io` directory.

Run it as root or with `sudo`.


``` bash
#!/bin/bash

echo "🔧 Updating system..."
apt update && apt upgrade -y

echo "🐳 Installing Docker..."
apt install -y apt-transport-https ca-certificates curl software-properties-common gnupg lsb-release

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
  > /etc/apt/sources.list.d/docker.list

apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

echo "✅ Docker installed"

echo "🔐 Configuring firewall (UFW)..."
apt install -y ufw
ufw allow OpenSSH
ufw allow http
ufw allow https
ufw --force enable

echo "✅ UFW configured"

echo "📁 Creating /opt/nginx-ngx-workshop.io directory..."
mkdir -p /opt/nginx-ngx-workshop.io

echo "🧪 Testing Docker install..."
docker run --rm hello-world

echo "🎉 Done! Your Nginx proxy box is ready to go."
```
