#!/bin/bash
# baseCamp Client Provisioning Script
# Complete automation for onboarding new clients

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
SCRIPTS_DIR="$(dirname "$0")"
BASE_DIR="$(dirname "$SCRIPTS_DIR")"

usage() {
    echo "Usage: $0 <client-name> [options]"
    echo ""
    echo "Complete client provisioning including configuration, SSL, and deployment"
    echo ""
    echo "Options:"
    echo "  --domain <domain>        Client domain (e.g., client.example.com)"
    echo "  --business-type <type>   Business type (automotive, medspa, consulting, general)"
    echo "  --staging               Use staging SSL certificates for testing"
    echo "  --no-ssl               Skip SSL certificate generation"
    echo "  --no-deploy            Skip container deployment"
    echo "  --force                Force overwrite existing client configuration"
    echo ""
    echo "Interactive mode (default):"
    echo "  $0 automotive-shop-1"
    echo ""
    echo "Non-interactive mode:"
    echo "  $0 automotive-shop-1 --domain shop1.example.com --business-type automotive"
    echo ""
    echo "Development/testing:"
    echo "  $0 test-client --domain test.example.com --business-type general --staging --no-deploy"
    exit 1
}

check_requirements() {
    log_info "Checking system requirements..."
    
    # Check if running as root/sudo
    if [[ $EUID -eq 0 ]]; then
        log_error "This script should not be run as root"
        log_info "Run as regular user with sudo access: sudo -u basecamp $0"
        exit 1
    fi
    
    # Check if basecamp user
    if [[ "$(whoami)" != "basecamp" ]]; then
        log_warning "Not running as basecamp user. Current user: $(whoami)"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Switching to basecamp user..."
            exec sudo -u basecamp "$0" "$@"
        fi
    fi
    
    # Check required commands
    local required_commands=("docker" "python3" "git")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "$cmd is not installed or not in PATH"
            exit 1
        fi
    done
    
    # Check if in baseCamp directory
    if [[ ! -f "$BASE_DIR/pyproject.toml" ]]; then
        log_error "Not in baseCamp project directory. Expected: $BASE_DIR"
        log_info "Please run this script from the baseCamp project root or update BASE_DIR"
        exit 1
    fi
    
    log_success "Requirements check passed"
}

check_client_exists() {
    local client_name="$1"
    local client_dir="$BASECAMP_DIR/clients/$client_name"
    
    if [[ -d "$client_dir" && "$FORCE_OVERWRITE" != "true" ]]; then
        log_warning "Client '$client_name' already exists at: $client_dir"
        log_warning "Files that exist:"
        ls -la "$client_dir" 2>/dev/null || true
        echo ""
        read -p "Overwrite existing configuration? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Client provisioning cancelled"
            exit 0
        fi
        export FORCE_OVERWRITE="true"
    fi
}

generate_client_config() {
    local client_name="$1"
    local domain="$2"
    local business_type="$3"
    
    log_info "Generating client configuration..."
    
    local config_args=()
    config_args+=("--client-name" "$client_name")
    
    if [[ -n "$domain" ]]; then
        config_args+=("--domain" "$domain")
    fi
    
    if [[ -n "$business_type" ]]; then
        config_args+=("--business-type" "$business_type")
    fi
    
    # Run config generator
    python3 "$SCRIPTS_DIR/generate-client-config.py" "${config_args[@]}"
    
    if [[ $? -ne 0 ]]; then
        log_error "Client configuration generation failed"
        exit 1
    fi
    
    log_success "Client configuration generated"
}

setup_ssl_certificate() {
    local client_name="$1"
    
    if [[ "$SKIP_SSL" == "true" ]]; then
        log_warning "Skipping SSL certificate setup"
        return 0
    fi
    
    log_info "Setting up SSL certificate..."
    
    local ssl_args=("$client_name")
    
    if [[ "$USE_STAGING" == "true" ]]; then
        ssl_args+=("--staging")
        log_warning "Using staging SSL certificates (not trusted by browsers)"
    fi
    
    # Run SSL setup script with sudo
    sudo "$SCRIPTS_DIR/setup-ssl.sh" "${ssl_args[@]}"
    
    if [[ $? -ne 0 ]]; then
        log_error "SSL certificate setup failed"
        exit 1
    fi
    
    log_success "SSL certificate configured"
}

deploy_client_container() {
    local client_name="$1"
    
    if [[ "$SKIP_DEPLOY" == "true" ]]; then
        log_warning "Skipping container deployment"
        return 0
    fi
    
    log_info "Deploying client container..."
    
    local client_dir="$BASECAMP_DIR/clients/$client_name"
    local deploy_script="$client_dir/deploy.sh"
    
    if [[ ! -f "$deploy_script" ]]; then
        log_error "Deployment script not found: $deploy_script"
        exit 1
    fi
    
    # Make sure deploy script is executable
    chmod +x "$deploy_script"
    
    # Run deployment
    "$deploy_script"
    
    if [[ $? -ne 0 ]]; then
        log_error "Container deployment failed"
        exit 1
    fi
    
    log_success "Client container deployed"
}

wait_for_services() {
    local client_name="$1"
    local max_wait=120
    local wait_time=0
    
    log_info "Waiting for services to become healthy..."
    
    while [[ $wait_time -lt $max_wait ]]; do
        # Check if all containers are running
        local running_containers
        running_containers=$(docker ps --filter "name=$client_name" --format "{{.Names}}" | wc -l)
        
        if [[ $running_containers -ge 3 ]]; then  # nginx, api, ollama (redis optional)
            log_success "All containers are running"
            break
        fi
        
        sleep 5
        wait_time=$((wait_time + 5))
        echo -n "."
    done
    
    echo ""
    
    if [[ $wait_time -ge $max_wait ]]; then
        log_warning "Services did not start within $max_wait seconds"
        log_info "Check container status: docker ps --filter name=$client_name"
        return 1
    fi
    
    # Additional health check
    sleep 10
    log_info "Performing health checks..."
    
    # Load client domain from config
    local client_dir="$BASECAMP_DIR/clients/$client_name"
    local env_file="$client_dir/.env.production"
    
    if [[ -f "$env_file" ]]; then
        local client_domain
        client_domain=$(grep "^CLIENT_DOMAIN=" "$env_file" | cut -d'=' -f2)
        
        if [[ -n "$client_domain" && "$SKIP_SSL" != "true" ]]; then
            # Test HTTPS health endpoint
            if curl -s --fail --max-time 10 "https://$client_domain/api/v1/health" > /dev/null; then
                log_success "Health check passed: https://$client_domain/api/v1/health"
            else
                log_warning "Health check failed - this may be normal if services are still starting"
            fi
        fi
    fi
}

run_post_deployment_tests() {
    local client_name="$1"
    
    log_info "Running post-deployment tests..."
    
    # Test container connectivity
    local api_container="${client_name}-api"
    
    if docker exec "$api_container" curl -s --fail http://localhost:8000/api/v1/health > /dev/null; then
        log_success "Internal API health check passed"
    else
        log_warning "Internal API health check failed"
    fi
    
    # Test Ollama connectivity
    local ollama_container="${client_name}-ollama"
    
    if docker exec "$ollama_container" curl -s --fail http://localhost:11434/api/version > /dev/null; then
        log_success "Ollama service check passed"
    else
        log_warning "Ollama service check failed"
    fi
    
    # Test Redis connectivity (if enabled)
    local redis_container="${client_name}-redis"
    
    if docker ps --filter "name=$redis_container" --format "{{.Names}}" | grep -q "$redis_container"; then
        if docker exec "$redis_container" redis-cli ping | grep -q "PONG"; then
            log_success "Redis service check passed"
        else
            log_warning "Redis service check failed"
        fi
    fi
}

print_provisioning_summary() {
    local client_name="$1"
    local client_dir="$BASECAMP_DIR/clients/$client_name"
    local env_file="$client_dir/.env.production"
    
    log_success "🎉 Client provisioning completed successfully!"
    echo ""
    
    # Load client information
    if [[ -f "$env_file" ]]; then
        local client_domain business_type
        client_domain=$(grep "^CLIENT_DOMAIN=" "$env_file" | cut -d'=' -f2)
        business_type=$(grep "^BUSINESS_TYPE=" "$env_file" | cut -d'=' -f2)
        
        log_info "📋 Client Summary:"
        echo "   • Name: $client_name"
        echo "   • Domain: $client_domain"
        echo "   • Business Type: $business_type"
        echo "   • Configuration: $client_dir"
        echo ""
    fi
    
    log_info "🐳 Container Status:"
    docker ps --filter "name=$client_name" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo ""
    
    if [[ "$SKIP_SSL" != "true" ]]; then
        log_info "🔗 Access Points:"
        echo "   • Frontend: https://$client_domain"
        echo "   • API Health: https://$client_domain/api/v1/health"
        echo "   • API Docs: https://$client_domain/docs (if enabled)"
        echo ""
    fi
    
    log_info "🔧 Management Commands:"
    echo "   • View logs: docker-compose -f docker-compose.prod.yml -f $client_dir/docker-compose.override.yml --env-file $env_file logs -f"
    echo "   • Restart services: $client_dir/deploy.sh"
    echo "   • Stop services: docker-compose -f docker-compose.prod.yml -f $client_dir/docker-compose.override.yml --env-file $env_file down"
    echo ""
    
    log_warning "📝 Next Steps:"
    echo "   • Test the client's forms and lead processing"
    echo "   • Verify Airtable integration is working"
    echo "   • Configure any additional business-specific settings"
    echo "   • Set up monitoring and alerting"
    echo "   • Provide client with domain and integration details"
    echo ""
    
    if [[ "$USE_STAGING" == "true" ]]; then
        log_warning "⚠️  Remember: You used staging SSL certificates"
        log_warning "   Run without --staging flag to get trusted certificates"
    fi
}

cleanup_on_error() {
    local client_name="$1"
    log_error "Provisioning failed. Performing cleanup..."
    
    # Stop any running containers
    local client_dir="$BASECAMP_DIR/clients/$client_name"
    if [[ -d "$client_dir" ]]; then
        local env_file="$client_dir/.env.production"
        if [[ -f "$env_file" ]]; then
            log_info "Stopping containers..."
            cd "$BASE_DIR"
            docker-compose -f docker-compose.prod.yml \
                          -f "$client_dir/docker-compose.override.yml" \
                          --env-file "$env_file" down || true
        fi
    fi
    
    log_info "Check logs for details: docker logs <container-name>"
}

main() {
    local client_name=""
    local domain=""
    local business_type=""
    local use_staging=false
    local skip_ssl=false
    local skip_deploy=false
    local force_overwrite=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --domain)
                domain="$2"
                shift 2
                ;;
            --business-type)
                business_type="$2"
                shift 2
                ;;
            --staging)
                use_staging=true
                shift
                ;;
            --no-ssl)
                skip_ssl=true
                shift
                ;;
            --no-deploy)
                skip_deploy=true
                shift
                ;;
            --force)
                force_overwrite=true
                shift
                ;;
            -h|--help)
                usage
                ;;
            -*)
                log_error "Unknown option: $1"
                usage
                ;;
            *)
                if [[ -z "$client_name" ]]; then
                    client_name="$1"
                else
                    log_error "Too many arguments"
                    usage
                fi
                shift
                ;;
        esac
    done
    
    if [[ -z "$client_name" ]]; then
        log_error "Client name is required"
        usage
    fi
    
    # Export variables for use in functions
    export USE_STAGING="$use_staging"
    export SKIP_SSL="$skip_ssl"
    export SKIP_DEPLOY="$skip_deploy"
    export FORCE_OVERWRITE="$force_overwrite"
    
    log_info "🚀 Starting baseCamp client provisioning"
    log_info "Client: $client_name"
    
    if [[ -n "$domain" ]]; then
        log_info "Domain: $domain"
    fi
    
    if [[ -n "$business_type" ]]; then
        log_info "Business Type: $business_type"
    fi
    
    echo ""
    
    # Set up error handling
    trap 'cleanup_on_error "$client_name"' ERR
    
    # Run provisioning steps
    check_requirements
    check_client_exists "$client_name"
    generate_client_config "$client_name" "$domain" "$business_type"
    setup_ssl_certificate "$client_name"
    deploy_client_container "$client_name"
    wait_for_services "$client_name"
    run_post_deployment_tests "$client_name"
    print_provisioning_summary "$client_name"
}

main "$@"