#!/bin/bash
# baseCamp Health Check Script
# Monitors client services and sends alerts if issues are detected

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] ✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️  $1${NC}"; }
log_error() { echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ❌ $1${NC}"; }

# Configuration
BASECAMP_DIR="/opt/basecamp"
LOG_FILE="/var/log/basecamp-health.log"
ALERT_EMAIL=""
SLACK_WEBHOOK=""
CHECK_INTERVAL=300  # 5 minutes
TIMEOUT=30

# Health check results
HEALTH_STATUS=0
TOTAL_CHECKS=0
FAILED_CHECKS=0
CLIENT_RESULTS=()

usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --client <name>         Check specific client only"
    echo "  --all                   Check all clients (default)"
    echo "  --daemon               Run as daemon with periodic checks"
    echo "  --interval <seconds>    Check interval for daemon mode (default: 300)"
    echo "  --alert-email <email>   Send alerts to email address"
    echo "  --slack-webhook <url>   Send alerts to Slack webhook"
    echo "  --timeout <seconds>     HTTP timeout (default: 30)"
    echo "  --verbose              Verbose output"
    echo "  --log-file <path>       Log file path (default: $LOG_FILE)"
    echo ""
    echo "Examples:"
    echo "  $0                                           # Check all clients once"
    echo "  $0 --client automotive-shop-1               # Check specific client"
    echo "  $0 --daemon --interval 60                   # Run as daemon, check every minute"
    echo "  $0 --alert-email admin@example.com          # Send email alerts"
    echo "  $0 --slack-webhook https://hooks.slack.com/... # Send Slack alerts"
    exit 1
}

setup_logging() {
    # Ensure log file exists and is writable
    touch "$LOG_FILE" 2>/dev/null || {
        LOG_FILE="/tmp/basecamp-health.log"
        log_warning "Cannot write to $LOG_FILE, using $LOG_FILE"
    }
}

log_to_file() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

check_docker_service() {
    log_info "Checking Docker service..."
    
    if ! systemctl is-active --quiet docker; then
        log_error "Docker service is not running"
        log_to_file "ERROR: Docker service is not running"
        return 1
    fi
    
    log_success "Docker service is running"
    return 0
}

check_nginx_service() {
    log_info "Checking Nginx service..."
    
    if ! systemctl is-active --quiet nginx; then
        log_error "Nginx service is not running"
        log_to_file "ERROR: Nginx service is not running"
        return 1
    fi
    
    # Test nginx configuration
    if ! nginx -t &>/dev/null; then
        log_error "Nginx configuration test failed"
        log_to_file "ERROR: Nginx configuration test failed"
        return 1
    fi
    
    log_success "Nginx service is running and configured correctly"
    return 0
}

get_client_domain() {
    local client_name="$1"
    local env_file="$BASECAMP_DIR/clients/$client_name/.env.production"
    
    if [[ -f "$env_file" ]]; then
        grep "^CLIENT_DOMAIN=" "$env_file" | cut -d'=' -f2
    else
        echo ""
    fi
}

check_client_containers() {
    local client_name="$1"
    local issues=0
    
    log_info "Checking containers for client: $client_name"
    
    local expected_containers=("${client_name}-nginx" "${client_name}-api" "${client_name}-ollama")
    
    for container in "${expected_containers[@]}"; do
        if docker ps --format "{{.Names}}" | grep -q "^${container}$"; then
            local status=$(docker inspect --format='{{.State.Status}}' "$container")
            if [[ "$status" == "running" ]]; then
                log_success "Container $container: $status"
            else
                log_error "Container $container: $status (expected: running)"
                log_to_file "ERROR: Container $container status: $status"
                ((issues++))
            fi
            
            # Check container health if health check is configured
            local health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "none")
            if [[ "$health" != "none" ]]; then
                if [[ "$health" == "healthy" ]]; then
                    log_success "Container $container health: $health"
                else
                    log_warning "Container $container health: $health"
                    log_to_file "WARNING: Container $container health: $health"
                fi
            fi
        else
            log_error "Container $container: not found"
            log_to_file "ERROR: Container $container not found"
            ((issues++))
        fi
    done
    
    # Check Redis container (optional)
    local redis_container="${client_name}-redis"
    if docker ps --format "{{.Names}}" | grep -q "^${redis_container}$"; then
        local status=$(docker inspect --format='{{.State.Status}}' "$redis_container")
        if [[ "$status" == "running" ]]; then
            log_success "Container $redis_container: $status"
        else
            log_warning "Container $redis_container: $status"
            log_to_file "WARNING: Container $redis_container status: $status"
        fi
    fi
    
    return $issues
}

check_api_health() {
    local client_name="$1"
    local domain="$2"
    local issues=0
    
    if [[ -z "$domain" ]]; then
        log_warning "Domain not configured for client: $client_name"
        return 1
    fi
    
    log_info "Checking API health for: $domain"
    
    # Test health endpoint
    local health_url="https://$domain/api/v1/health"
    
    if curl -s --fail --max-time "$TIMEOUT" "$health_url" > /dev/null; then
        log_success "API health check passed: $health_url"
    else
        log_error "API health check failed: $health_url"
        log_to_file "ERROR: API health check failed for $domain"
        ((issues++))
    fi
    
    # Test intake endpoint
    local intake_url="https://$domain/api/v1/intake/health"
    
    if curl -s --fail --max-time "$TIMEOUT" "$intake_url" > /dev/null; then
        log_success "Intake API check passed: $intake_url"
    else
        log_warning "Intake API check failed: $intake_url"
        log_to_file "WARNING: Intake API check failed for $domain"
    fi
    
    return $issues
}

check_ssl_certificate() {
    local domain="$1"
    local issues=0
    
    log_info "Checking SSL certificate for: $domain"
    
    # Check certificate expiry
    local cert_info
    cert_info=$(echo | openssl s_client -connect "$domain:443" -servername "$domain" 2>/dev/null | openssl x509 -noout -dates 2>/dev/null)
    
    if [[ $? -eq 0 ]]; then
        local expiry_date
        expiry_date=$(echo "$cert_info" | grep "notAfter=" | cut -d'=' -f2)
        
        if [[ -n "$expiry_date" ]]; then
            local expiry_timestamp
            expiry_timestamp=$(date -d "$expiry_date" +%s 2>/dev/null)
            local current_timestamp
            current_timestamp=$(date +%s)
            local days_until_expiry
            days_until_expiry=$(( (expiry_timestamp - current_timestamp) / 86400 ))
            
            if [[ $days_until_expiry -gt 30 ]]; then
                log_success "SSL certificate expires in $days_until_expiry days"
            elif [[ $days_until_expiry -gt 7 ]]; then
                log_warning "SSL certificate expires in $days_until_expiry days (renewal recommended)"
                log_to_file "WARNING: SSL certificate for $domain expires in $days_until_expiry days"
            else
                log_error "SSL certificate expires in $days_until_expiry days (urgent renewal needed)"
                log_to_file "ERROR: SSL certificate for $domain expires in $days_until_expiry days"
                ((issues++))
            fi
        fi
    else
        log_error "Failed to check SSL certificate for $domain"
        log_to_file "ERROR: Failed to check SSL certificate for $domain"
        ((issues++))
    fi
    
    return $issues
}

check_resource_usage() {
    local client_name="$1"
    
    log_info "Checking resource usage for: $client_name"
    
    # Get container stats
    local containers
    containers=$(docker ps --filter "name=$client_name" --format "{{.Names}}")
    
    for container in $containers; do
        local stats
        stats=$(docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" "$container" | tail -n +2)
        
        if [[ -n "$stats" ]]; then
            local cpu_usage
            cpu_usage=$(echo "$stats" | awk '{print $2}' | sed 's/%//')
            local memory_usage
            memory_usage=$(echo "$stats" | awk '{print $3}')
            
            # Check CPU usage (warning if > 80%)
            if (( $(echo "$cpu_usage > 80" | bc -l 2>/dev/null || echo 0) )); then
                log_warning "$container CPU usage: ${cpu_usage}% (high)"
                log_to_file "WARNING: $container CPU usage: ${cpu_usage}%"
            else
                log_success "$container CPU usage: ${cpu_usage}%"
            fi
            
            log_info "$container Memory usage: $memory_usage"
        fi
    done
}

check_disk_space() {
    log_info "Checking disk space..."
    
    # Check root filesystem
    local disk_usage
    disk_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [[ $disk_usage -gt 90 ]]; then
        log_error "Disk usage: ${disk_usage}% (critical)"
        log_to_file "ERROR: Disk usage: ${disk_usage}%"
        return 1
    elif [[ $disk_usage -gt 80 ]]; then
        log_warning "Disk usage: ${disk_usage}% (high)"
        log_to_file "WARNING: Disk usage: ${disk_usage}%"
    else
        log_success "Disk usage: ${disk_usage}%"
    fi
    
    # Check Docker volume usage
    local docker_usage
    docker_usage=$(df /var/lib/docker 2>/dev/null | awk 'NR==2 {print $5}' | sed 's/%//' || echo "0")
    
    if [[ $docker_usage -gt 90 ]]; then
        log_error "Docker disk usage: ${docker_usage}% (critical)"
        log_to_file "ERROR: Docker disk usage: ${docker_usage}%"
        return 1
    elif [[ $docker_usage -gt 80 ]]; then
        log_warning "Docker disk usage: ${docker_usage}% (high)"
        log_to_file "WARNING: Docker disk usage: ${docker_usage}%"
    else
        log_success "Docker disk usage: ${docker_usage}%"
    fi
    
    return 0
}

check_client() {
    local client_name="$1"
    local client_issues=0
    
    log_info "=== Health check for client: $client_name ==="
    
    # Get client domain
    local domain
    domain=$(get_client_domain "$client_name")
    
    # Check containers
    check_client_containers "$client_name"
    client_issues=$((client_issues + $?))
    
    # Check API health
    if [[ -n "$domain" ]]; then
        check_api_health "$client_name" "$domain"
        client_issues=$((client_issues + $?))
        
        check_ssl_certificate "$domain"
        client_issues=$((client_issues + $?))
    fi
    
    # Check resource usage
    check_resource_usage "$client_name"
    
    # Store result
    CLIENT_RESULTS+=("$client_name:$client_issues")
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    if [[ $client_issues -gt 0 ]]; then
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        HEALTH_STATUS=1
    fi
    
    if [[ $client_issues -eq 0 ]]; then
        log_success "All checks passed for client: $client_name"
    else
        log_error "$client_issues issues found for client: $client_name"
    fi
    
    return $client_issues
}

get_all_clients() {
    local clients=()
    
    if [[ -d "$BASECAMP_DIR/clients" ]]; then
        for client_dir in "$BASECAMP_DIR/clients"/*; do
            if [[ -d "$client_dir" && -f "$client_dir/.env.production" ]]; then
                clients+=($(basename "$client_dir"))
            fi
        done
    fi
    
    echo "${clients[@]}"
}

send_alert() {
    local subject="$1"
    local message="$2"
    
    # Email alert
    if [[ -n "$ALERT_EMAIL" ]] && command -v mail &>/dev/null; then
        echo -e "$message" | mail -s "$subject" "$ALERT_EMAIL"
        log_info "Alert email sent to: $ALERT_EMAIL"
    fi
    
    # Slack alert
    if [[ -n "$SLACK_WEBHOOK" ]] && command -v curl &>/dev/null; then
        local payload
        payload=$(cat <<EOF
{
    "text": "*$subject*",
    "attachments": [
        {
            "color": "danger",
            "text": "$message",
            "ts": $(date +%s)
        }
    ]
}
EOF
        )
        
        curl -X POST -H 'Content-type: application/json' \
             --data "$payload" "$SLACK_WEBHOOK" &>/dev/null
        log_info "Alert sent to Slack"
    fi
}

generate_alert_message() {
    local message="baseCamp Health Check Alert\n"
    message+="Time: $(date)\n"
    message+="Host: $(hostname)\n\n"
    
    message+="Summary:\n"
    message+="- Total clients checked: $TOTAL_CHECKS\n"
    message+="- Clients with issues: $FAILED_CHECKS\n\n"
    
    if [[ $FAILED_CHECKS -gt 0 ]]; then
        message+="Clients with issues:\n"
        for result in "${CLIENT_RESULTS[@]}"; do
            local client_name="${result%:*}"
            local issues="${result#*:}"
            if [[ $issues -gt 0 ]]; then
                message+="- $client_name: $issues issues\n"
            fi
        done
        message+="\nCheck logs for details: $LOG_FILE\n"
    fi
    
    echo -e "$message"
}

run_health_checks() {
    local client_filter="$1"
    
    log_info "Starting baseCamp health checks..."
    log_to_file "Starting health checks"
    
    # Reset counters
    HEALTH_STATUS=0
    TOTAL_CHECKS=0
    FAILED_CHECKS=0
    CLIENT_RESULTS=()
    
    # System checks
    check_docker_service
    check_nginx_service
    check_disk_space
    
    # Client checks
    if [[ -n "$client_filter" ]]; then
        if [[ -d "$BASECAMP_DIR/clients/$client_filter" ]]; then
            check_client "$client_filter"
        else
            log_error "Client not found: $client_filter"
            exit 1
        fi
    else
        local clients
        clients=($(get_all_clients))
        
        if [[ ${#clients[@]} -eq 0 ]]; then
            log_warning "No clients found in $BASECAMP_DIR/clients"
        else
            for client in "${clients[@]}"; do
                check_client "$client"
                echo ""  # Blank line between clients
            done
        fi
    fi
    
    # Summary
    log_info "=== Health Check Summary ==="
    if [[ $HEALTH_STATUS -eq 0 ]]; then
        log_success "All health checks passed!"
    else
        log_error "Health check failed: $FAILED_CHECKS/$TOTAL_CHECKS clients have issues"
        
        # Send alerts if configured
        if [[ -n "$ALERT_EMAIL" || -n "$SLACK_WEBHOOK" ]]; then
            local alert_message
            alert_message=$(generate_alert_message)
            send_alert "baseCamp Health Check Failed" "$alert_message"
        fi
    fi
    
    log_to_file "Health check completed: Status=$HEALTH_STATUS, Failed=$FAILED_CHECKS/$TOTAL_CHECKS"
}

run_daemon() {
    local client_filter="$1"
    
    log_info "Starting baseCamp health check daemon (interval: ${CHECK_INTERVAL}s)"
    
    # Create PID file
    local pid_file="/var/run/basecamp-health.pid"
    echo $$ > "$pid_file" 2>/dev/null || {
        pid_file="/tmp/basecamp-health.pid"
        echo $$ > "$pid_file"
    }
    
    log_info "PID file: $pid_file"
    
    # Signal handlers for graceful shutdown
    trap 'log_info "Received SIGTERM, shutting down..."; rm -f "$pid_file"; exit 0' TERM
    trap 'log_info "Received SIGINT, shutting down..."; rm -f "$pid_file"; exit 0' INT
    
    while true; do
        run_health_checks "$client_filter"
        log_info "Next check in ${CHECK_INTERVAL} seconds..."
        sleep "$CHECK_INTERVAL"
    done
}

main() {
    local client_filter=""
    local daemon_mode=false
    local verbose=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --client)
                client_filter="$2"
                shift 2
                ;;
            --all)
                client_filter=""
                shift
                ;;
            --daemon)
                daemon_mode=true
                shift
                ;;
            --interval)
                CHECK_INTERVAL="$2"
                shift 2
                ;;
            --alert-email)
                ALERT_EMAIL="$2"
                shift 2
                ;;
            --slack-webhook)
                SLACK_WEBHOOK="$2"
                shift 2
                ;;
            --timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            --verbose)
                verbose=true
                shift
                ;;
            --log-file)
                LOG_FILE="$2"
                shift 2
                ;;
            -h|--help)
                usage
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                ;;
        esac
    done
    
    setup_logging
    
    if [[ "$daemon_mode" == "true" ]]; then
        run_daemon "$client_filter"
    else
        run_health_checks "$client_filter"
        exit $HEALTH_STATUS
    fi
}

main "$@"