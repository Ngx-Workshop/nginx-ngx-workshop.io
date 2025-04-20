## ngx-nginx-proxy

This is the reverse proxy for your Ngx Workshop infrastructure. It proxies API and WebSocket requests to the NestJS server and optionally proxies frontend app requests to DigitalOcean Spaces or another Droplet.

```bash
# Create base folder and navigate into it
mkdir ngx-nginx-proxy && cd ngx-nginx-proxy

# Create Docker-related files and folders
mkdir docker
touch docker/nginx.conf
touch Dockerfile
touch .dockerignore

# Create GitHub Actions folder and workflow file
mkdir -p .github/workflows
touch .github/workflows/deploy.yml

# Create README file
touch README.md
```

### 🗂️ Folder Structure
```
ngx-nginx-proxy/
├── docker/
│   └── nginx.conf         # Main Nginx configuration file
├── Dockerfile             # Nginx image setup
├── .dockerignore          # Docker ignore rules
├── .github/
│   └── workflows/
│       └── deploy.yml     # CI/CD GitHub Action
└── README.md              # Project overview
```

### 🐳 Dockerfile
```Dockerfile
FROM nginx:alpine
COPY docker/nginx.conf /etc/nginx/nginx.conf
```

### 🔧 docker/nginx.conf
```nginx
worker_processes 1;

events {
    worker_connections 1024;
}

http {
    include       mime.types;
    default_type  application/octet-stream;

    sendfile        on;
    keepalive_timeout  65;

    server {
        listen 80;

        location /api/ {
            proxy_pass http://api-server:3000;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
        }

        location / {
            proxy_pass https://your-app-static.cdn.digitaloceanspaces.com;
        }
    }
}
```

### 🚀 GitHub Actions CI/CD - .github/workflows/deploy.yml
```yaml
name: Deploy Nginx to DO Droplet

on:
  push:
    branches:
      - main

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repo
        uses: actions/checkout@v3

      - name: Build Docker image
        run: docker build -t ngx-nginx-proxy .

      - name: Copy files to Droplet
        uses: appleboy/scp-action@master
        with:
          host: ${{ secrets.DROPLET_IP }}
          username: root
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          source: "."
          target: "/opt/ngx-nginx-proxy"

      - name: SSH and restart Docker container
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.DROPLET_IP }}
          username: root
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/ngx-nginx-proxy
            docker build -t ngx-nginx-proxy .
            docker stop nginx || true
            docker rm nginx || true
            docker run -d --name nginx -p 80:80 ngx-nginx-proxy
```

### 🛠️ DigitalOcean Droplet setup `./bootstrap-nginx.sh`

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

echo "📁 Creating /opt/ngx-nginx-proxy directory..."
mkdir -p /opt/ngx-nginx-proxy

echo "🧪 Testing Docker install..."
docker run --rm hello-world

echo "🎉 Done! Your Nginx proxy box is ready to go."
```
