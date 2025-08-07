#!/bin/bash
# SSL Certificate Setup for baseCamp Clients
# Automates Let's Encrypt SSL certificate provisioning

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# Configuration
BASECAMP_DIR="/opt/basecamp"
NGINX_DIR="$BASECAMP_DIR/nginx"
SSL_DIR="$BASECAMP_DIR/ssl"

usage() {
    echo "Usage: $0 <client-name> [options]"
    echo ""
    echo "Options:"
    echo "  --staging          Use Let's Encrypt staging environment (for testing)"
    echo "  --force-renewal    Force certificate renewal even if not near expiry"
    echo "  --dry-run          Test certificate generation without actually creating certificates"
    echo "  --email <email>    Override email address for Let's Encrypt"
    echo ""
    echo "Examples:"
    echo "  $0 automotive-shop-1"
    echo "  $0 automotive-shop-1 --staging"
    echo "  $0 automotive-shop-1 --email admin@example.com"
    exit 1
}

check_requirements() {
    log_info "Checking requirements..."
    
    # Check if running as root
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
    
    # Check if certbot is installed
    if ! command -v certbot &> /dev/null; then
        log_error "Certbot is not installed. Please run setup-vps.sh first."
        exit 1
    fi
    
    # Check if nginx is running
    if ! systemctl is-active --quiet nginx; then
        log_error "Nginx is not running. Please start nginx first: systemctl start nginx"
        exit 1
    fi
    
    log_success "Requirements check passed"
}

load_client_config() {
    local client_name="$1"
    local client_dir="$BASECAMP_DIR/clients/$client_name"
    local env_file="$client_dir/.env.production"
    
    if [ ! -f "$env_file" ]; then
        log_error "Client configuration not found: $env_file"
        log_info "Please run: scripts/generate-client-config.py --client-name $client_name"
        exit 1
    fi
    
    # Source the environment file to get CLIENT_DOMAIN and LETSENCRYPT_EMAIL
    set -a  # automatically export all variables
    source "$env_file"
    set +a
    
    if [ -z "$CLIENT_DOMAIN" ]; then
        log_error "CLIENT_DOMAIN not found in $env_file"
        exit 1
    fi
    
    if [ -z "$LETSENCRYPT_EMAIL" ]; then
        log_error "LETSENCRYPT_EMAIL not found in $env_file"
        exit 1
    fi
    
    log_success "Loaded client config: $CLIENT_DOMAIN"
}

check_dns() {
    local domain="$1"
    log_info "Checking DNS resolution for $domain..."
    
    # Get public IP of this server
    local server_ip
    server_ip=$(curl -s https://ipv4.icanhazip.com/ || curl -s https://api.ipify.org/)
    
    if [ -z "$server_ip" ]; then
        log_warning "Could not determine server public IP"
        return 0
    fi
    
    # Check if domain resolves to this server
    local domain_ip
    domain_ip=$(dig +short "$domain" | tail -n1)
    
    if [ "$domain_ip" = "$server_ip" ]; then
        log_success "DNS check passed: $domain -> $server_ip"
    else
        log_warning "DNS mismatch: $domain resolves to $domain_ip, but server IP is $server_ip"
        log_warning "SSL certificate generation may fail if DNS is not properly configured"
        
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "SSL setup cancelled. Please configure DNS first."
            exit 0
        fi
    fi
}

create_nginx_config() {
    local client_name="$1"
    local domain="$CLIENT_DOMAIN"
    local config_file="$NGINX_DIR/$client_name.conf"
    
    log_info "Creating Nginx configuration for $domain..."
    
    # Create temporary HTTP-only config for certificate generation
    cat > "$config_file" << EOF
# baseCamp client configuration for $client_name
# Domain: $domain

server {
    listen 80;
    listen [::]:80;
    server_name $domain;
    
    # Let's Encrypt challenge location
    location ^~ /.well-known/acme-challenge/ {
        default_type "text/plain";
        root /var/www/html;
    }
    
    # Redirect all other HTTP traffic to HTTPS (after SSL setup)
    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

# HTTPS configuration (will be updated after SSL certificate generation)
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name $domain;
    
    # SSL configuration (placeholder - will be updated)
    ssl_certificate /etc/letsencrypt/live/$domain/fullchain.pem;
    ssl_private_key /etc/letsencrypt/live/$domain/privkey.pem;
    
    # SSL security settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;
    
    # HSTS
    add_header Strict-Transport-Security "max-age=63072000" always;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    
    # Proxy to baseCamp API
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header X-Forwarded-Port \$server_port;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 8k;
        proxy_buffers 8 8k;
    }
    
    # Health check endpoint
    location /api/v1/health {
        proxy_pass http://127.0.0.1:8000/api/v1/health;
        proxy_set_header Host \$host;
        access_log off;
    }
    
    # Static files (if any)
    location /static/ {
        alias /opt/basecamp/clients/$client_name/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF
    
    # Test nginx configuration
    nginx -t
    systemctl reload nginx
    
    log_success "Nginx configuration created and loaded"
}

create_webroot_dir() {
    log_info "Creating webroot directory for Let's Encrypt..."
    
    mkdir -p /var/www/html/.well-known/acme-challenge
    chown -R nginx:nginx /var/www/html
    chmod -R 755 /var/www/html
    
    log_success "Webroot directory created"
}

generate_certificate() {
    local domain="$CLIENT_DOMAIN"
    local email="${OVERRIDE_EMAIL:-$LETSENCRYPT_EMAIL}"
    local staging_flag=""
    local force_renewal_flag=""
    local dry_run_flag=""
    
    if [ "$USE_STAGING" = "true" ]; then
        staging_flag="--staging"
        log_warning "Using Let's Encrypt STAGING environment (certificates will not be trusted)"
    fi
    
    if [ "$FORCE_RENEWAL" = "true" ]; then
        force_renewal_flag="--force-renewal"
    fi
    
    if [ "$DRY_RUN" = "true" ]; then
        dry_run_flag="--dry-run"
        log_info "DRY RUN: Testing certificate generation without creating actual certificates"
    fi
    
    log_info "Generating SSL certificate for $domain..."
    log_info "Email: $email"
    
    # Generate certificate
    certbot certonly \
        --webroot \
        --webroot-path=/var/www/html \
        --email "$email" \
        --agree-tos \
        --no-eff-email \
        --domains "$domain" \
        $staging_flag \
        $force_renewal_flag \
        $dry_run_flag
    
    if [ "$DRY_RUN" = "true" ]; then
        log_success "DRY RUN completed successfully"
        return 0
    fi
    
    # Check if certificate was created
    if [ -f "/etc/letsencrypt/live/$domain/fullchain.pem" ]; then
        log_success "SSL certificate generated successfully for $domain"
        
        # Show certificate details
        log_info "Certificate details:"
        openssl x509 -in "/etc/letsencrypt/live/$domain/fullchain.pem" -text -noout | grep -E "(Subject:|Not Before:|Not After:|DNS:)"
    else
        log_error "Certificate generation failed"
        exit 1
    fi
}

setup_auto_renewal() {
    log_info "Setting up automatic certificate renewal..."
    
    # Create renewal script
    cat > /usr/local/bin/certbot-renewal.sh << 'EOF'
#!/bin/bash
# Automatic certificate renewal for baseCamp

/usr/bin/certbot renew --quiet --post-hook "systemctl reload nginx"

# Log renewal attempts
echo "$(date): Certificate renewal check completed" >> /var/log/certbot-renewal.log
EOF
    
    chmod +x /usr/local/bin/certbot-renewal.sh
    
    # Add to crontab (run twice daily)
    (crontab -l 2>/dev/null | grep -v certbot-renewal; echo "0 0,12 * * * /usr/local/bin/certbot-renewal.sh") | crontab -
    
    log_success "Automatic renewal configured (runs twice daily)"
}

update_nginx_ssl_config() {
    local client_name="$1"
    local domain="$CLIENT_DOMAIN"
    local config_file="$NGINX_DIR/$client_name.conf"
    
    log_info "Updating Nginx configuration with SSL settings..."
    
    # The SSL configuration is already in place from create_nginx_config
    # Just need to reload nginx to use the new certificates
    nginx -t
    systemctl reload nginx
    
    log_success "Nginx configuration updated with SSL"
}

test_ssl_connection() {
    local domain="$CLIENT_DOMAIN"
    
    log_info "Testing SSL connection..."
    
    # Test HTTPS connection
    if curl -s --head --fail "https://$domain/api/v1/health" > /dev/null 2>&1; then
        log_success "HTTPS connection test passed"
    else
        log_warning "HTTPS connection test failed - this may be normal if the baseCamp API is not running yet"
    fi
    
    # Test SSL certificate
    if command -v openssl &> /dev/null; then
        log_info "SSL certificate test:"
        echo | openssl s_client -connect "$domain:443" -servername "$domain" 2>/dev/null | openssl x509 -noout -dates
    fi
}

cleanup_on_error() {
    local client_name="$1"
    log_error "SSL setup failed. Cleaning up..."
    
    # Remove nginx config if it was created
    if [ -f "$NGINX_DIR/$client_name.conf" ]; then
        rm -f "$NGINX_DIR/$client_name.conf"
        systemctl reload nginx
        log_info "Nginx configuration removed"
    fi
}

main() {
    local client_name=""
    local use_staging=false
    local force_renewal=false
    local dry_run=false
    local override_email=""
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --staging)
                use_staging=true
                shift
                ;;
            --force-renewal)
                force_renewal=true
                shift
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            --email)
                override_email="$2"
                shift 2
                ;;
            -h|--help)
                usage
                ;;
            -*)
                log_error "Unknown option: $1"
                usage
                ;;
            *)
                if [ -z "$client_name" ]; then
                    client_name="$1"
                else
                    log_error "Too many arguments"
                    usage
                fi
                shift
                ;;
        esac
    done
    
    if [ -z "$client_name" ]; then
        log_error "Client name is required"
        usage
    fi
    
    # Export flags for use in functions
    export USE_STAGING="$use_staging"
    export FORCE_RENEWAL="$force_renewal"
    export DRY_RUN="$dry_run"
    export OVERRIDE_EMAIL="$override_email"
    
    log_info "🔐 Setting up SSL certificate for client: $client_name"
    
    # Set up error handling
    trap 'cleanup_on_error "$client_name"' ERR
    
    check_requirements
    load_client_config "$client_name"
    check_dns "$CLIENT_DOMAIN"
    create_webroot_dir
    create_nginx_config "$client_name"
    generate_certificate
    
    if [ "$DRY_RUN" != "true" ]; then
        setup_auto_renewal
        update_nginx_ssl_config "$client_name"
        test_ssl_connection
        
        log_success "🎉 SSL setup completed successfully!"
        echo ""
        log_info "📋 Summary:"
        echo "   • Client: $client_name"
        echo "   • Domain: $CLIENT_DOMAIN"
        echo "   • Certificate: /etc/letsencrypt/live/$CLIENT_DOMAIN/"
        echo "   • Nginx config: $NGINX_DIR/$client_name.conf"
        echo "   • Auto-renewal: Configured (twice daily)"
        echo ""
        log_info "🔗 Test your SSL certificate:"
        echo "   • Browser: https://$CLIENT_DOMAIN"
        echo "   • SSL Labs: https://www.ssllabs.com/ssltest/analyze.html?d=$CLIENT_DOMAIN"
        echo ""
        log_warning "📝 Next step: Deploy your client container using the deployment script"
    fi
}

main "$@"