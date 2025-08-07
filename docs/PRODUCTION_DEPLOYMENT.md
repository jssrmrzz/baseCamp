# baseCamp Production Deployment Guide

Complete guide for deploying baseCamp in production with multi-client container architecture.

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Prerequisites](#prerequisites)  
3. [VPS Setup](#vps-setup)
4. [Client Onboarding](#client-onboarding)
5. [SSL Configuration](#ssl-configuration)
6. [Monitoring & Maintenance](#monitoring--maintenance)
7. [Scaling & Performance](#scaling--performance)
8. [Security Best Practices](#security-best-practices)
9. [Troubleshooting](#troubleshooting)
10. [Recovery Procedures](#recovery-procedures)

## System Overview

### Architecture
baseCamp uses a **container-per-client** architecture for maximum isolation and security:

```
VPS Server
├── Nginx (SSL termination, routing)
├── Client A Container (baseCamp + Ollama + ChromaDB + Redis)
├── Client B Container (baseCamp + Ollama + ChromaDB + Redis)  
└── Client C Container (baseCamp + Ollama + ChromaDB + Redis)
```

Each client gets:
- **Isolated containers** with dedicated resources
- **Separate domains** (client-a.yourdomain.com)
- **Individual Airtable integrations**
- **Independent scaling and configuration**

### Benefits
✅ **Security**: Complete client isolation  
✅ **Scalability**: Easy to add new clients  
✅ **Reliability**: Client issues don't affect others  
✅ **Maintenance**: Independent updates per client  
✅ **Billing**: Clear resource usage per client  

## Prerequisites

### Server Requirements
- **OS**: Ubuntu 22.04 LTS (recommended) or CentOS 8+
- **CPU**: 4+ cores (2 cores per active client recommended)
- **RAM**: 8GB+ (4GB per active client recommended)  
- **Storage**: 50GB+ SSD (10GB per client + system overhead)
- **Network**: Static IP address with reverse DNS

### Domain Requirements
- **Main domain** for your baseCamp service
- **Wildcard SSL** or individual subdomains per client
- **DNS management** access for subdomain configuration

### External Services
- **Airtable account** for each client (or shared workspace)
- **Email service** for SSL certificate notifications
- **Monitoring service** (optional but recommended)

## VPS Setup

### 1. Initial Server Configuration

Run the automated VPS setup script as root:

```bash
# Download baseCamp repository
git clone https://github.com/your-org/baseCamp.git /opt/basecamp
cd /opt/basecamp

# Run VPS setup (as root)
sudo ./scripts/setup-vps.sh
```

This script will:
- ✅ Install Docker and Docker Compose
- ✅ Configure Nginx reverse proxy
- ✅ Install SSL certificate tools (Certbot)
- ✅ Set up firewall and security hardening
- ✅ Create baseCamp system user and directories
- ✅ Configure basic monitoring tools

### 2. Manual Setup (Alternative)

If you prefer manual setup or need customization:

#### Install Docker
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker
```

#### Install Nginx
```bash
# Ubuntu/Debian  
sudo apt update && sudo apt install -y nginx

# CentOS/RHEL
sudo dnf install -y nginx

# Start and enable Nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

#### Install Certbot
```bash
# Ubuntu/Debian
sudo apt install -y certbot python3-certbot-nginx

# CentOS/RHEL  
sudo dnf install -y certbot python3-certbot-nginx
```

### 3. Verify Installation

```bash
# Check services
sudo systemctl status docker nginx

# Check Docker
docker --version
docker-compose --version  

# Check Nginx
nginx -v
curl -I http://localhost

# Check firewall
sudo ufw status  # Ubuntu
sudo firewall-cmd --list-all  # CentOS
```

## Client Onboarding

### Automated Client Provisioning

The fastest way to onboard a new client:

```bash
# Switch to basecamp user
sudo -u basecamp -i
cd /opt/basecamp

# Provision new client (interactive)
./scripts/provision-client.sh automotive-shop-1 \
    --domain shop1.example.com \
    --business-type automotive
```

This will:
1. ✅ Generate client configuration
2. ✅ Set up SSL certificates  
3. ✅ Deploy containers
4. ✅ Configure domain routing
5. ✅ Run health checks

### Manual Client Setup Process

#### Step 1: Generate Client Configuration

```bash
python scripts/generate-client-config.py \
    --client-name automotive-shop-1 \
    --domain shop1.example.com \
    --business-type automotive
```

You'll be prompted for:
- Airtable API credentials
- Client contact information  
- Admin email for SSL certificates
- Timezone and other preferences

#### Step 2: Configure SSL Certificates

```bash
sudo ./scripts/setup-ssl.sh automotive-shop-1
```

For staging/testing:
```bash  
sudo ./scripts/setup-ssl.sh automotive-shop-1 --staging
```

#### Step 3: Deploy Client Container

```bash
cd /opt/basecamp
./clients/automotive-shop-1/deploy.sh
```

#### Step 4: Verify Deployment

```bash
# Check container status
docker ps --filter name=automotive-shop-1

# Check health
./scripts/health-check.sh --client automotive-shop-1

# Test API
curl https://shop1.example.com/api/v1/health
```

## SSL Configuration

### Automatic SSL (Recommended)

The setup scripts handle SSL automatically using Let's Encrypt:

```bash
# SSL setup with auto-renewal
sudo ./scripts/setup-ssl.sh client-name
```

Features:
- ✅ Automatic certificate generation
- ✅ Auto-renewal (cron job configured)
- ✅ Strong SSL configuration (A+ rating)
- ✅ HSTS and security headers

### Manual SSL Configuration

#### Generate Certificates
```bash
sudo certbot --nginx -d client.example.com
```

#### Configure Auto-Renewal
```bash
# Test renewal
sudo certbot renew --dry-run

# Check cron job
sudo crontab -l | grep certbot
```

### Wildcard SSL (Advanced)

For multiple subdomains:

```bash
sudo certbot certonly \
    --dns-route53 \
    -d *.example.com \
    --email admin@example.com \
    --agree-tos
```

## Monitoring & Maintenance

### Automated Health Monitoring

#### Setup Monitoring Daemon
```bash
# Run health checks every 5 minutes
sudo ./scripts/health-check.sh --daemon --interval 300
```

#### Email Alerts
```bash
./scripts/health-check.sh --alert-email admin@example.com
```

#### Slack Alerts  
```bash
./scripts/health-check.sh --slack-webhook https://hooks.slack.com/your-webhook
```

### Manual Health Checks

```bash
# Check all clients
./scripts/health-check.sh --all

# Check specific client
./scripts/health-check.sh --client automotive-shop-1  

# System validation
python scripts/validate-production.py --all-clients
```

### Log Management

#### View Container Logs
```bash  
# All containers for client
docker-compose -f docker-compose.prod.yml \
    -f clients/automotive-shop-1/docker-compose.override.yml \
    --env-file clients/automotive-shop-1/.env.production \
    logs -f

# Specific service
docker logs automotive-shop-1-api -f
```

#### Log Rotation
```bash
# Configure log rotation for Docker
sudo nano /etc/logrotate.d/docker-container

# Content:
/var/lib/docker/containers/*/*.log {
    rotate 7
    daily  
    compress
    size=1M
    missingok
    delaycompress
    copytruncate
}
```

### Backup Procedures

#### Client Data Backup
```bash
#!/bin/bash
# backup-client.sh
CLIENT_NAME="$1"
BACKUP_DIR="/opt/backups/$(date +%Y%m%d)"

mkdir -p "$BACKUP_DIR"

# Backup ChromaDB data  
docker cp "${CLIENT_NAME}-api:/app/chroma_db" "$BACKUP_DIR/${CLIENT_NAME}_chroma"

# Backup configuration
cp -r "/opt/basecamp/clients/$CLIENT_NAME" "$BACKUP_DIR/${CLIENT_NAME}_config"

# Backup logs
cp -r "/opt/basecamp/clients/$CLIENT_NAME/logs" "$BACKUP_DIR/${CLIENT_NAME}_logs"

echo "Backup completed: $BACKUP_DIR"
```

#### Automated Backups
```bash
# Add to crontab (daily at 2 AM)
0 2 * * * /opt/basecamp/scripts/backup-all-clients.sh
```

## Scaling & Performance

### Resource Monitoring

#### Container Resource Usage
```bash
# Real-time stats
docker stats

# Historical data
docker system df
docker system prune  # Cleanup
```

#### System Resources  
```bash
# CPU and Memory
htop
free -h
df -h

# Network
iftop
netstat -tulpn
```

### Scaling Strategies

#### Vertical Scaling (Single Server)
- Increase CPU cores and RAM
- Add SSD storage for better I/O
- Optimize container resource limits

#### Horizontal Scaling (Multiple Servers)
- Deploy additional VPS instances
- Use load balancer for traffic distribution  
- Shared database for configuration management
- Container orchestration with Docker Swarm/Kubernetes

### Performance Optimization

#### Container Optimization
```yaml
# docker-compose.prod.yml optimizations
services:
  api:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.5'
        reservations:
          memory: 512M  
          cpus: '0.5'
```

#### Database Optimization
```bash
# ChromaDB performance tuning
CHROMA_BATCH_SIZE=100
CHROMA_MAX_BATCH_SIZE=1000

# Enable Redis caching
ENABLE_REDIS_CACHE=true
REDIS_TTL=3600
```

## Security Best Practices

### System Security

#### Firewall Configuration
```bash
# UFW (Ubuntu)
sudo ufw default deny incoming
sudo ufw default allow outgoing  
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Firewalld (CentOS)
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

#### SSH Hardening
```bash
# /etc/ssh/sshd_config
PermitRootLogin no
PasswordAuthentication no  
PubkeyAuthentication yes
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
```

#### Fail2Ban Setup
```bash
sudo apt install fail2ban

# /etc/fail2ban/jail.local
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
```

### Application Security

#### Environment Variables
- ✅ Use strong API secrets (32+ characters)
- ✅ Rotate credentials regularly
- ✅ Never commit secrets to version control
- ✅ Use separate credentials per client

#### Container Security
```yaml
# Security settings in docker-compose
security_opt:
  - no-new-privileges:true
read_only: true
tmpfs:
  - /tmp:noexec,nosuid,size=100m
```

#### Network Security
```yaml
# Container network isolation  
networks:
  client-network:
    driver: bridge
    internal: true  # No external access
```

### SSL/TLS Configuration

#### Strong SSL Settings (Nginx)
```nginx
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
ssl_prefer_server_ciphers off;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 1d;  
ssl_session_tickets off;

# HSTS
add_header Strict-Transport-Security "max-age=63072000" always;
```

## Troubleshooting

### Common Issues

#### Container Won't Start
```bash
# Check container logs
docker logs container-name

# Check resource constraints
docker stats
df -h

# Check configuration
docker-compose config
```

#### SSL Certificate Issues
```bash
# Check certificate expiry
openssl x509 -in /etc/letsencrypt/live/domain/cert.pem -noout -dates

# Test SSL configuration  
sslscan domain.com
testssl.sh domain.com

# Renew certificate
sudo certbot renew --force-renewal -d domain.com
```

#### Performance Issues
```bash
# Check system resources
top
iotop
iftop

# Check container resources
docker stats
docker system df

# Check application logs
docker logs client-api -f
```

#### Airtable Integration Issues
```bash
# Test Airtable connection
curl -H "Authorization: Bearer API_KEY" \
    "https://api.airtable.com/v0/BASE_ID/TABLE_NAME?maxRecords=1"

# Check API key permissions
# Verify base and table names  
# Check rate limiting
```

### Diagnostic Tools

#### Production Validation
```bash
python scripts/validate-production.py --client client-name --output-json report.json
```

#### Health Check Reports
```bash  
./scripts/health-check.sh --client client-name --verbose > health-report.txt
```

#### Container Debugging
```bash
# Access container shell
docker exec -it client-api bash

# Check container processes
docker exec client-api ps aux

# Check container network
docker exec client-api netstat -tulpn
```

## Recovery Procedures

### Container Recovery

#### Restart Single Client
```bash
cd /opt/basecamp
./clients/client-name/deploy.sh
```

#### Full System Recovery
```bash
# Stop all containers
docker stop $(docker ps -q)

# Start system services
sudo systemctl start docker nginx

# Restart all clients
for client in /opt/basecamp/clients/*/; do
    client_name=$(basename "$client")
    echo "Restarting $client_name..."
    "$client/deploy.sh"
done
```

### Data Recovery

#### Restore ChromaDB Data
```bash
CLIENT_NAME="automotive-shop-1"
BACKUP_DATE="20240115"

# Stop client containers
docker-compose -f docker-compose.prod.yml \
    -f clients/$CLIENT_NAME/docker-compose.override.yml down

# Restore data
docker cp "/opt/backups/$BACKUP_DATE/${CLIENT_NAME}_chroma" \
    "${CLIENT_NAME}-api:/app/chroma_db"

# Restart containers  
./clients/$CLIENT_NAME/deploy.sh
```

#### Configuration Recovery
```bash
# Restore client configuration
BACKUP_DATE="20240115"  
CLIENT_NAME="automotive-shop-1"

cp -r "/opt/backups/$BACKUP_DATE/${CLIENT_NAME}_config" \
    "/opt/basecamp/clients/$CLIENT_NAME"
```

### Disaster Recovery

#### Complete Server Recovery
1. **Provision new VPS** with same specifications
2. **Run VPS setup** script to install dependencies  
3. **Restore baseCamp repository** from version control
4. **Restore client configurations** from backups
5. **Restore SSL certificates** or generate new ones
6. **Restore client data** (ChromaDB, logs)
7. **Update DNS** to point to new server
8. **Verify all clients** are operational

#### Recovery Testing
```bash
# Test recovery procedures monthly
./scripts/test-recovery.sh --client test-client
```

## Performance Benchmarks

### Expected Performance
- **API Response Time**: <3 seconds (95th percentile)
- **Lead Processing**: <10 seconds end-to-end
- **Concurrent Users**: 100+ per client container
- **Throughput**: 1000+ leads per day per client
- **Uptime**: 99.5%+ with proper monitoring

### Monitoring Metrics
- Container CPU/Memory usage
- API response times
- Error rates and status codes
- SSL certificate expiry dates
- Disk space usage
- Database query performance

---

## Quick Reference

### Essential Commands
```bash
# Client management
./scripts/provision-client.sh new-client
./scripts/health-check.sh --all
python scripts/validate-production.py --all-clients

# SSL management
sudo ./scripts/setup-ssl.sh client-name
sudo certbot renew

# Monitoring  
docker stats
docker logs client-api -f
tail -f /var/log/nginx/access.log

# Maintenance
docker system prune  
./scripts/backup-all-clients.sh
```

### Support Resources
- 📧 **Email**: support@basecamp.example.com
- 📱 **Emergency**: +1-555-BASECAMP  
- 📚 **Documentation**: https://docs.basecamp.example.com
- 🐛 **Issues**: https://github.com/your-org/baseCamp/issues

---

*Last Updated: $(date)*
*Version: Production v1.0*