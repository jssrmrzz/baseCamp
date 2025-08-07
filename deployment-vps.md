# baseCamp - VPS Deployment Guide

## 📊 Deployment Overview

**Architecture**: Container-per-client on single VPS with nginx reverse proxy
**Security Model**: Process isolation eliminates need for application authentication
**Scaling**: Vertical (more resources) and horizontal (multiple VPS) options

## VPS Requirements

### Minimum Specifications (3-5 clients)
- **CPU**: 8 cores @ 3.0GHz+
- **RAM**: 16GB (3-4GB per client container)
- **Storage**: 100GB NVMe SSD
- **Network**: 100Mbps+ bandwidth
- **OS**: Ubuntu 22.04 LTS

### Recommended Specifications (5-10 clients)
- **CPU**: 16 cores @ 3.5GHz+
- **RAM**: 32-64GB
- **Storage**: 500GB NVMe SSD
- **Network**: 1Gbps bandwidth
- **Backup**: Automated daily snapshots

## Initial VPS Setup

### 1. Server Preparation
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install nginx
sudo apt install nginx -y

# Install certbot for SSL
sudo apt install certbot python3-certbot-nginx -y
```

### 2. Directory Structure Setup
```bash
# Create deployment structure
sudo mkdir -p /opt/basecamp
sudo chown $USER:$USER /opt/basecamp
cd /opt/basecamp

# Directory structure
mkdir -p {clients,nginx,ssl,scripts,backups}
mkdir -p nginx/{sites-available,sites-enabled}

# Structure overview:
# /opt/basecamp/
# ├── clients/
# │   ├── client-a/
# │   ├── client-b/
# │   └── client-c/
# ├── nginx/
# │   ├── sites-available/
# │   ├── sites-enabled/
# │   └── nginx.conf
# ├── ssl/
# ├── scripts/
# └── backups/
```

## Client Container Setup

### 1. Client Directory Template
```bash
# Create client directory
mkdir -p /opt/basecamp/clients/client-a
cd /opt/basecamp/clients/client-a

# Copy baseCamp codebase
git clone https://github.com/yourusername/baseCamp.git .
# OR: rsync -av /path/to/basecamp/ .
```

### 2. Docker Compose Template
Create `/opt/basecamp/clients/client-a/docker-compose.yml`:

```yaml
version: '3.8'

services:
  api:
    build: .
    container_name: basecamp-client-a
    restart: unless-stopped
    ports:
      - "8001:8000"  # Unique port per client
    environment:
      - API_HOST=0.0.0.0
      - API_PORT=8000
      - OLLAMA_BASE_URL=http://ollama:11434
      - OLLAMA_MODEL=mistral:latest
      - CHROMA_PERSIST_DIRECTORY=/app/chroma_db
      - AIRTABLE_API_KEY=${CLIENT_A_AIRTABLE_KEY}
      - AIRTABLE_BASE_ID=${CLIENT_A_BASE_ID}
      - AIRTABLE_TABLE_NAME=Leads
      - BUSINESS_TYPE=${CLIENT_A_BUSINESS_TYPE:-automotive}
      - DEBUG=false
      - LOG_LEVEL=INFO
    volumes:
      - client-a-chroma:/app/chroma_db
      - client-a-logs:/app/logs
    depends_on:
      - ollama
    networks:
      - client-a-net
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '0.5'
          memory: 1G

  ollama:
    image: ollama/ollama:latest
    container_name: ollama-client-a
    restart: unless-stopped
    volumes:
      - client-a-ollama:/root/.ollama
    networks:
      - client-a-net
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 8G
        reservations:
          cpus: '1.0'
          memory: 2G

volumes:
  client-a-chroma:
    driver: local
  client-a-ollama:
    driver: local
  client-a-logs:
    driver: local

networks:
  client-a-net:
    driver: bridge
```

### 3. Client Environment Configuration
Create `/opt/basecamp/clients/client-a/.env`:

```bash
# Client A Configuration
CLIENT_A_AIRTABLE_KEY=pat_xxxxxxxxxxxxxxxxx
CLIENT_A_BASE_ID=appXXXXXXXXXXXXXX
CLIENT_A_BUSINESS_TYPE=automotive

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=30
RATE_LIMIT_REQUESTS_PER_HOUR=500

# CORS Settings
CORS_ORIGINS=["https://client-a.yourdomain.com","https://www.client-a-website.com"]

# Business-specific settings
BUSINESS_TYPE=automotive
LEAD_SIMILARITY_THRESHOLD=0.7
MAX_SIMILAR_LEADS=5
```

## Nginx Reverse Proxy Configuration

### 1. Main Nginx Configuration
Create `/opt/basecamp/nginx/nginx.conf`:

```nginx
user www-data;
worker_processes auto;
pid /run/nginx.pid;

events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}

http {
    # Basic settings
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    server_tokens off;

    # MIME types
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';
    
    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;

    # Rate limiting zones (per client)
    limit_req_zone $binary_remote_addr zone=client_a:10m rate=10r/m;
    limit_req_zone $binary_remote_addr zone=client_b:10m rate=10r/m;
    limit_req_zone $binary_remote_addr zone=client_c:10m rate=10r/m;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Include site configurations
    include /opt/basecamp/nginx/sites-enabled/*;
}
```

### 2. Client Site Configuration Template
Create `/opt/basecamp/nginx/sites-available/client-a.conf`:

```nginx
server {
    listen 80;
    server_name client-a.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name client-a.yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/client-a.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/client-a.yourdomain.com/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Rate limiting
    limit_req zone=client_a burst=20 nodelay;

    # Main application proxy
    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
        
        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }

    # Health check endpoint (bypass rate limiting)
    location /api/v1/health {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        access_log off;
    }

    # Security headers for this client
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'";
    
    # Logging
    access_log /var/log/nginx/client-a.access.log main;
    error_log /var/log/nginx/client-a.error.log;
}
```

### 3. Enable Site Configuration
```bash
# Enable site
sudo ln -s /opt/basecamp/nginx/sites-available/client-a.conf /opt/basecamp/nginx/sites-enabled/

# Update main nginx to include our configs
sudo cp /opt/basecamp/nginx/nginx.conf /etc/nginx/nginx.conf

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

## SSL Certificate Setup

### 1. Obtain SSL Certificates
```bash
# For each client domain
sudo certbot --nginx -d client-a.yourdomain.com
sudo certbot --nginx -d client-b.yourdomain.com
sudo certbot --nginx -d client-c.yourdomain.com

# Verify auto-renewal
sudo certbot renew --dry-run
```

### 2. Automated Certificate Renewal
Create `/opt/basecamp/scripts/renew-certs.sh`:

```bash
#!/bin/bash
# SSL certificate renewal script

LOG_FILE="/var/log/certbot-renew.log"

echo "$(date): Starting certificate renewal" >> $LOG_FILE

# Renew certificates
certbot renew --quiet >> $LOG_FILE 2>&1

# Check if renewal was successful
if [ $? -eq 0 ]; then
    echo "$(date): Certificate renewal successful" >> $LOG_FILE
    # Reload nginx to use new certificates
    systemctl reload nginx
    echo "$(date): Nginx reloaded" >> $LOG_FILE
else
    echo "$(date): Certificate renewal failed" >> $LOG_FILE
fi
```

Add to crontab:
```bash
# Run twice daily
0 */12 * * * /opt/basecamp/scripts/renew-certs.sh
```

## Client Management Scripts

### 1. Client Deployment Script
Create `/opt/basecamp/scripts/deploy-client.sh`:

```bash
#!/bin/bash
# Client deployment script

CLIENT_NAME=$1
DOMAIN=$2
PORT=$3
BUSINESS_TYPE=$4
AIRTABLE_KEY=$5
AIRTABLE_BASE=$6

if [ -z "$CLIENT_NAME" ] || [ -z "$DOMAIN" ] || [ -z "$PORT" ]; then
    echo "Usage: $0 <client_name> <domain> <port> [business_type] [airtable_key] [airtable_base]"
    exit 1
fi

CLIENT_DIR="/opt/basecamp/clients/$CLIENT_NAME"
BUSINESS_TYPE=${BUSINESS_TYPE:-general}

echo "Deploying client: $CLIENT_NAME"
echo "Domain: $DOMAIN"
echo "Port: $PORT"
echo "Business Type: $BUSINESS_TYPE"

# Create client directory
mkdir -p "$CLIENT_DIR"
cd "$CLIENT_DIR"

# Copy baseCamp codebase
if [ ! -f "src/main.py" ]; then
    git clone https://github.com/yourusername/baseCamp.git .
fi

# Generate docker-compose.yml from template
cat > docker-compose.yml << EOF
version: '3.8'

services:
  api:
    build: .
    container_name: basecamp-$CLIENT_NAME
    restart: unless-stopped
    ports:
      - "$PORT:8000"
    environment:
      - API_HOST=0.0.0.0
      - API_PORT=8000
      - OLLAMA_BASE_URL=http://ollama:11434
      - OLLAMA_MODEL=mistral:latest
      - CHROMA_PERSIST_DIRECTORY=/app/chroma_db
      - AIRTABLE_API_KEY=$AIRTABLE_KEY
      - AIRTABLE_BASE_ID=$AIRTABLE_BASE
      - AIRTABLE_TABLE_NAME=Leads
      - BUSINESS_TYPE=$BUSINESS_TYPE
      - DEBUG=false
      - LOG_LEVEL=INFO
    volumes:
      - ${CLIENT_NAME}-chroma:/app/chroma_db
      - ${CLIENT_NAME}-logs:/app/logs
    depends_on:
      - ollama
    networks:
      - ${CLIENT_NAME}-net
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '0.5'
          memory: 1G

  ollama:
    image: ollama/ollama:latest
    container_name: ollama-$CLIENT_NAME
    restart: unless-stopped
    volumes:
      - ${CLIENT_NAME}-ollama:/root/.ollama
    networks:
      - ${CLIENT_NAME}-net
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 8G
        reservations:
          cpus: '1.0'
          memory: 2G

volumes:
  ${CLIENT_NAME}-chroma:
    driver: local
  ${CLIENT_NAME}-ollama:
    driver: local
  ${CLIENT_NAME}-logs:
    driver: local

networks:
  ${CLIENT_NAME}-net:
    driver: bridge
EOF

# Generate environment file
cat > .env << EOF
# Client Configuration
AIRTABLE_API_KEY=$AIRTABLE_KEY
AIRTABLE_BASE_ID=$AIRTABLE_BASE
BUSINESS_TYPE=$BUSINESS_TYPE
CORS_ORIGINS=["https://$DOMAIN"]
RATE_LIMIT_REQUESTS_PER_MINUTE=30
LEAD_SIMILARITY_THRESHOLD=0.7
EOF

# Generate nginx site config
NGINX_CONFIG="/opt/basecamp/nginx/sites-available/$CLIENT_NAME.conf"
cat > "$NGINX_CONFIG" << EOF
server {
    listen 80;
    server_name $DOMAIN;
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN;

    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;

    limit_req zone=${CLIENT_NAME}_zone burst=20 nodelay;

    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /api/v1/health {
        proxy_pass http://127.0.0.1:$PORT;
        access_log off;
    }
}
EOF

# Build and start containers
echo "Building and starting containers..."
docker-compose build
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 30

# Download Ollama model
echo "Downloading Ollama model..."
docker-compose exec ollama ollama pull mistral:latest

# Enable nginx site
sudo ln -sf "$NGINX_CONFIG" "/opt/basecamp/nginx/sites-enabled/"

# Get SSL certificate
sudo certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email admin@yourdomain.com

# Test configuration and reload nginx
sudo nginx -t && sudo systemctl reload nginx

echo "Client $CLIENT_NAME deployed successfully!"
echo "Access: https://$DOMAIN"
echo "Health check: https://$DOMAIN/api/v1/health"
```

### 2. Client Monitoring Script
Create `/opt/basecamp/scripts/monitor-clients.sh`:

```bash
#!/bin/bash
# Client monitoring script

CLIENTS_DIR="/opt/basecamp/clients"
LOG_FILE="/var/log/basecamp-monitor.log"

echo "$(date): Starting client monitoring" >> $LOG_FILE

for client_dir in "$CLIENTS_DIR"/*; do
    if [ -d "$client_dir" ]; then
        CLIENT_NAME=$(basename "$client_dir")
        
        cd "$client_dir"
        
        # Check container status
        API_STATUS=$(docker-compose ps api | grep -c "Up")
        OLLAMA_STATUS=$(docker-compose ps ollama | grep -c "Up")
        
        if [ "$API_STATUS" -ne 1 ] || [ "$OLLAMA_STATUS" -ne 1 ]; then
            echo "$(date): $CLIENT_NAME - Services down, restarting..." >> $LOG_FILE
            docker-compose up -d
        fi
        
        # Check health endpoint
        HEALTH_URL="http://127.0.0.1:$(grep -o '"[0-9]*:8000"' docker-compose.yml | cut -d':' -f1 | tr -d '"')/api/v1/health"
        
        if ! curl -s "$HEALTH_URL" > /dev/null; then
            echo "$(date): $CLIENT_NAME - Health check failed" >> $LOG_FILE
        fi
        
        # Check resource usage
        MEMORY_USAGE=$(docker stats --no-stream --format "table {{.Container}}\t{{.MemUsage}}" | grep "basecamp-$CLIENT_NAME" | awk '{print $2}')
        echo "$(date): $CLIENT_NAME - Memory usage: $MEMORY_USAGE" >> $LOG_FILE
    fi
done
```

Add to crontab:
```bash
# Monitor every 5 minutes
*/5 * * * * /opt/basecamp/scripts/monitor-clients.sh
```

## Backup and Recovery

### 1. Backup Script
Create `/opt/basecamp/scripts/backup-clients.sh`:

```bash
#!/bin/bash
# Client backup script

BACKUP_DIR="/opt/basecamp/backups/$(date +%Y-%m-%d)"
CLIENTS_DIR="/opt/basecamp/clients"

mkdir -p "$BACKUP_DIR"

echo "Starting backup to $BACKUP_DIR"

for client_dir in "$CLIENTS_DIR"/*; do
    if [ -d "$client_dir" ]; then
        CLIENT_NAME=$(basename "$client_dir")
        
        echo "Backing up $CLIENT_NAME..."
        
        cd "$client_dir"
        
        # Backup ChromaDB data
        docker run --rm \
            -v "${CLIENT_NAME}-chroma:/data" \
            -v "$BACKUP_DIR:/backup" \
            busybox tar czf "/backup/${CLIENT_NAME}-chroma.tar.gz" -C /data .
        
        # Backup configuration
        tar czf "$BACKUP_DIR/${CLIENT_NAME}-config.tar.gz" .env docker-compose.yml
        
        # Backup logs
        docker run --rm \
            -v "${CLIENT_NAME}-logs:/logs" \
            -v "$BACKUP_DIR:/backup" \
            busybox tar czf "/backup/${CLIENT_NAME}-logs.tar.gz" -C /logs .
    fi
done

# Backup nginx configurations
tar czf "$BACKUP_DIR/nginx-config.tar.gz" -C /opt/basecamp nginx/

# Clean up old backups (keep last 7 days)
find /opt/basecamp/backups -type d -name "20*" -mtime +7 -exec rm -rf {} \;

echo "Backup completed"
```

Add to crontab:
```bash
# Daily backup at 2 AM
0 2 * * * /opt/basecamp/scripts/backup-clients.sh
```

## Security Hardening

### 1. Firewall Configuration
```bash
# Install UFW
sudo apt install ufw

# Default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (change port if using non-standard)
sudo ufw allow 22/tcp

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status verbose
```

### 2. System Security
```bash
# Disable root login
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config

# Disable password authentication (use keys only)
sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config

# Restart SSH
sudo systemctl restart sshd

# Install fail2ban
sudo apt install fail2ban

# Configure fail2ban for nginx
sudo cat > /etc/fail2ban/jail.local << EOF
[nginx-http-auth]
enabled = true
filter = nginx-http-auth
logpath = /var/log/nginx/error.log
maxretry = 3
bantime = 3600

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
logpath = /var/log/nginx/error.log
maxretry = 10
bantime = 600
EOF

sudo systemctl restart fail2ban
```

## Monitoring and Alerting

### 1. System Monitoring
```bash
# Install monitoring tools
sudo apt install htop iotop netstat-nat

# Create monitoring dashboard script
cat > /opt/basecamp/scripts/system-status.sh << EOF
#!/bin/bash
echo "=== System Status ==="
date
echo
echo "=== CPU Usage ==="
top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1"%"}'
echo
echo "=== Memory Usage ==="
free -h
echo
echo "=== Disk Usage ==="
df -h /
echo
echo "=== Docker Containers ==="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo
echo "=== Active Connections ==="
netstat -an | grep :443 | wc -l
EOF

chmod +x /opt/basecamp/scripts/system-status.sh
```

### 2. Log Aggregation
```bash
# Install logrotate for nginx logs
sudo cat > /etc/logrotate.d/nginx-clients << EOF
/var/log/nginx/client-*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    sharedscripts
    postrotate
        systemctl reload nginx
    endscript
}
EOF
```

## Troubleshooting

### Common Issues and Solutions

1. **Container won't start**
   ```bash
   # Check logs
   cd /opt/basecamp/clients/client-name
   docker-compose logs
   
   # Check resource usage
   docker stats
   
   # Restart services
   docker-compose down && docker-compose up -d
   ```

2. **Nginx configuration errors**
   ```bash
   # Test configuration
   sudo nginx -t
   
   # Check error logs
   sudo tail -f /var/log/nginx/error.log
   
   # Reload configuration
   sudo systemctl reload nginx
   ```

3. **SSL certificate issues**
   ```bash
   # Check certificate status
   sudo certbot certificates
   
   # Renew certificates
   sudo certbot renew
   
   # Test SSL
   openssl s_client -connect domain.com:443
   ```

4. **Resource exhaustion**
   ```bash
   # Check system resources
   htop
   df -h
   
   # Check Docker resources
   docker system df
   docker system prune
   
   # Adjust container limits in docker-compose.yml
   ```

This deployment guide provides a comprehensive framework for deploying baseCamp in a production VPS environment with proper security, monitoring, and management practices.