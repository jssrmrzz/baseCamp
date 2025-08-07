#!/bin/bash
# baseCamp VPS Setup Script
# Sets up a fresh VPS for multi-client baseCamp deployment

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BASEDOCUMENT_USER="basecamp"
DOCKER_VERSION="24.0.7"
COMPOSE_VERSION="2.23.3"
NGINX_VERSION="latest"

# Functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    else
        log_error "Cannot detect OS version"
        exit 1
    fi
    log_info "Detected OS: $OS $VER"
}

update_system() {
    log_info "Updating system packages..."
    
    if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
        apt update && apt upgrade -y
        apt install -y curl wget git unzip software-properties-common apt-transport-https ca-certificates gnupg lsb-release
    elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]] || [[ "$OS" == *"Rocky"* ]]; then
        yum update -y
        yum install -y curl wget git unzip yum-utils device-mapper-persistent-data lvm2
    else
        log_error "Unsupported OS: $OS"
        exit 1
    fi
    
    log_success "System packages updated"
}

create_user() {
    log_info "Creating baseCamp system user..."
    
    if id "$BASEDOCUMENT_USER" &>/dev/null; then
        log_warning "User $BASEDOCUMENT_USER already exists"
    else
        useradd -m -s /bin/bash "$BASEDOCUMENT_USER"
        usermod -aG sudo "$BASEDOCUMENT_USER"
        log_success "Created user: $BASEDOCUMENT_USER"
    fi
    
    # Create SSH key directory
    mkdir -p "/home/$BASEDOCUMENT_USER/.ssh"
    chown "$BASEDOCUMENT_USER:$BASEDOCUMENT_USER" "/home/$BASEDOCUMENT_USER/.ssh"
    chmod 700 "/home/$BASEDOCUMENT_USER/.ssh"
}

install_docker() {
    log_info "Installing Docker..."
    
    if command -v docker &> /dev/null; then
        log_warning "Docker already installed: $(docker --version)"
        return
    fi
    
    if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
        # Add Docker's official GPG key
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
        
        # Add Docker repository
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
        
        # Install Docker
        apt update
        apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
        
    elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]] || [[ "$OS" == *"Rocky"* ]]; then
        # Add Docker repository
        yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
        
        # Install Docker
        yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
        
        # Start Docker
        systemctl start docker
        systemctl enable docker
    fi
    
    # Add user to docker group
    usermod -aG docker "$BASEDOCUMENT_USER"
    
    log_success "Docker installed: $(docker --version)"
}

install_nginx() {
    log_info "Installing Nginx..."
    
    if command -v nginx &> /dev/null; then
        log_warning "Nginx already installed: $(nginx -version 2>&1)"
        return
    fi
    
    if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
        apt install -y nginx
    elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]] || [[ "$OS" == *"Rocky"* ]]; then
        yum install -y nginx
    fi
    
    # Start and enable Nginx
    systemctl start nginx
    systemctl enable nginx
    
    log_success "Nginx installed and started"
}

install_certbot() {
    log_info "Installing Certbot for SSL certificates..."
    
    if command -v certbot &> /dev/null; then
        log_warning "Certbot already installed: $(certbot --version)"
        return
    fi
    
    if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
        apt install -y certbot python3-certbot-nginx
    elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]] || [[ "$OS" == *"Rocky"* ]]; then
        yum install -y certbot python3-certbot-nginx
    fi
    
    log_success "Certbot installed"
}

setup_firewall() {
    log_info "Configuring firewall..."
    
    if command -v ufw &> /dev/null; then
        # Ubuntu/Debian UFW
        ufw --force reset
        ufw default deny incoming
        ufw default allow outgoing
        ufw allow ssh
        ufw allow 80/tcp
        ufw allow 443/tcp
        ufw --force enable
        log_success "UFW firewall configured"
        
    elif command -v firewall-cmd &> /dev/null; then
        # CentOS/RHEL firewalld
        systemctl start firewalld
        systemctl enable firewalld
        firewall-cmd --permanent --add-service=ssh
        firewall-cmd --permanent --add-service=http
        firewall-cmd --permanent --add-service=https
        firewall-cmd --reload
        log_success "Firewalld configured"
        
    else
        log_warning "No firewall manager found. Please configure firewall manually."
    fi
}

create_directories() {
    log_info "Creating baseCamp directories..."
    
    BASECAMP_DIR="/opt/basecamp"
    mkdir -p "$BASECAMP_DIR"
    mkdir -p "$BASECAMP_DIR/clients"
    mkdir -p "$BASECAMP_DIR/nginx/templates"
    mkdir -p "$BASECAMP_DIR/ssl"
    mkdir -p "$BASECAMP_DIR/backups"
    mkdir -p "$BASECAMP_DIR/logs"
    
    chown -R "$BASEDOCUMENT_USER:$BASEDOCUMENT_USER" "$BASECAMP_DIR"
    
    log_success "Directories created at $BASECAMP_DIR"
}

setup_nginx_config() {
    log_info "Setting up Nginx configuration..."
    
    # Main nginx configuration
    cat > /etc/nginx/nginx.conf << 'EOF'
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';
    access_log /var/log/nginx/access.log main;

    # Performance
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 20M;

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

    # Security headers template
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

    # Default server (catch-all)
    server {
        listen 80 default_server;
        listen [::]:80 default_server;
        server_name _;
        return 444;
    }

    # Include client configurations
    include /opt/basecamp/nginx/*.conf;
}
EOF

    # Test nginx configuration
    nginx -t
    systemctl reload nginx
    
    log_success "Nginx configuration updated"
}

install_monitoring() {
    log_info "Setting up basic monitoring..."
    
    # Install htop and other monitoring tools
    if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
        apt install -y htop iotop netstat-nat
    elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]] || [[ "$OS" == *"Rocky"* ]]; then
        yum install -y htop iotop net-tools
    fi
    
    # Create log rotation for docker containers
    cat > /etc/logrotate.d/docker-container << 'EOF'
/var/lib/docker/containers/*/*.log {
    rotate 7
    daily
    compress
    size=1M
    missingok
    delaycompress
    copytruncate
}
EOF

    log_success "Basic monitoring tools installed"
}

setup_ssh_security() {
    log_info "Hardening SSH configuration..."
    
    # Backup original config
    cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup
    
    # Apply secure SSH settings
    sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
    sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config
    sed -i 's/#Port 22/Port 22/' /etc/ssh/sshd_config
    
    # Add if not present
    grep -q "Protocol 2" /etc/ssh/sshd_config || echo "Protocol 2" >> /etc/ssh/sshd_config
    grep -q "MaxAuthTries 3" /etc/ssh/sshd_config || echo "MaxAuthTries 3" >> /etc/ssh/sshd_config
    grep -q "ClientAliveInterval 300" /etc/ssh/sshd_config || echo "ClientAliveInterval 300" >> /etc/ssh/sshd_config
    grep -q "ClientAliveCountMax 2" /etc/ssh/sshd_config || echo "ClientAliveCountMax 2" >> /etc/ssh/sshd_config
    
    # Restart SSH service
    systemctl restart sshd
    
    log_success "SSH hardened (remember to add your public key before disconnecting!)"
}

create_deployment_script() {
    log_info "Creating deployment helpers..."
    
    cat > /opt/basecamp/deploy-client.sh << 'EOF'
#!/bin/bash
# Quick client deployment script

CLIENT_NAME="$1"
if [ -z "$CLIENT_NAME" ]; then
    echo "Usage: $0 <client-name>"
    exit 1
fi

CLIENT_DIR="/opt/basecamp/clients/$CLIENT_NAME"
if [ ! -d "$CLIENT_DIR" ]; then
    echo "Client directory not found: $CLIENT_DIR"
    exit 1
fi

cd /opt/basecamp
exec "$CLIENT_DIR/deploy.sh"
EOF

    chmod +x /opt/basecamp/deploy-client.sh
    chown "$BASEDOCUMENT_USER:$BASEDOCUMENT_USER" /opt/basecamp/deploy-client.sh
    
    log_success "Deployment helpers created"
}

print_summary() {
    log_success "🎉 VPS setup completed successfully!"
    echo ""
    log_info "📋 Setup Summary:"
    echo "   • OS: $OS $VER"
    echo "   • Docker: $(docker --version 2>/dev/null || echo 'Installation failed')"
    echo "   • Nginx: $(nginx -version 2>&1 || echo 'Installation failed')"
    echo "   • Certbot: $(certbot --version 2>/dev/null || echo 'Installation failed')"
    echo "   • User created: $BASEDOCUMENT_USER"
    echo "   • baseCamp directory: /opt/basecamp"
    echo ""
    log_info "🔐 Security:"
    echo "   • Firewall configured (ports 22, 80, 443)"
    echo "   • SSH hardened (key-only authentication)"
    echo "   • Root login disabled"
    echo ""
    log_warning "⚠️  Important Next Steps:"
    echo "   1. Add your SSH public key to /home/$BASEDOCUMENT_USER/.ssh/authorized_keys"
    echo "   2. Test SSH connection before closing this session"
    echo "   3. Clone baseCamp repository to /opt/basecamp"
    echo "   4. Configure your first client using scripts/generate-client-config.py"
    echo ""
    log_info "📚 Useful Commands:"
    echo "   • Switch to baseCamp user: sudo -u $BASEDOCUMENT_USER -i"
    echo "   • Deploy client: /opt/basecamp/deploy-client.sh <client-name>"
    echo "   • Check Docker status: systemctl status docker"
    echo "   • Check Nginx status: systemctl status nginx"
    echo "   • View logs: journalctl -fu nginx"
}

main() {
    log_info "🚀 Starting baseCamp VPS Setup"
    echo "This will install and configure:"
    echo "  • Docker & Docker Compose"
    echo "  • Nginx reverse proxy"
    echo "  • SSL certificates (Let's Encrypt)"
    echo "  • Security hardening"
    echo "  • System monitoring"
    echo ""
    
    read -p "Continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Setup cancelled"
        exit 0
    fi
    
    check_root
    detect_os
    update_system
    create_user
    install_docker
    install_nginx
    install_certbot
    setup_firewall
    create_directories
    setup_nginx_config
    install_monitoring
    setup_ssh_security
    create_deployment_script
    print_summary
}

# Run main function
main "$@"