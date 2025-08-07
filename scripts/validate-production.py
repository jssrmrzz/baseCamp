#!/usr/bin/env python3
"""
baseCamp Production Readiness Validator

This script validates that a baseCamp client deployment is production-ready.
It checks system requirements, configuration, SSL certificates, and service health.

Usage:
    python scripts/validate-production.py --client automotive-shop-1
    python scripts/validate-production.py --all-clients
    python scripts/validate-production.py --system-check
"""

import argparse
import json
import os
import sys
import time
import subprocess
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import socket
import ssl
from datetime import datetime, timedelta
import docker
from urllib.parse import urlparse


class Colors:
    """ANSI color codes for terminal output."""
    BLUE = '\033[0;34m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    BOLD = '\033[1m'
    NC = '\033[0m'  # No Color


class ProductionValidator:
    """Validates baseCamp production deployments."""
    
    def __init__(self, base_dir: Path = None):
        self.base_dir = base_dir or Path(__file__).parent.parent
        self.basecamp_dir = Path("/opt/basecamp")
        self.docker_client = None
        self.results = []
        
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            self.log_warning(f"Docker client initialization failed: {e}")
    
    def log_info(self, message: str):
        print(f"{Colors.BLUE}ℹ️  {message}{Colors.NC}")
    
    def log_success(self, message: str):
        print(f"{Colors.GREEN}✅ {message}{Colors.NC}")
    
    def log_warning(self, message: str):
        print(f"{Colors.YELLOW}⚠️  {message}{Colors.NC}")
    
    def log_error(self, message: str):
        print(f"{Colors.RED}❌ {message}{Colors.NC}")
    
    def log_header(self, message: str):
        print(f"\n{Colors.BOLD}{message}{Colors.NC}")
        print("=" * len(message))
    
    def add_result(self, category: str, check: str, status: str, message: str, details: Optional[Dict] = None):
        """Add validation result."""
        self.results.append({
            'category': category,
            'check': check,
            'status': status,
            'message': message,
            'details': details or {},
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def check_system_requirements(self) -> bool:
        """Check system-level requirements."""
        self.log_header("System Requirements Check")
        success = True
        
        # Check Docker
        try:
            docker_version = subprocess.check_output(['docker', '--version'], text=True).strip()
            self.log_success(f"Docker installed: {docker_version}")
            self.add_result('system', 'docker', 'pass', f"Docker installed: {docker_version}")
        except Exception as e:
            self.log_error(f"Docker not available: {e}")
            self.add_result('system', 'docker', 'fail', f"Docker not available: {e}")
            success = False
        
        # Check Docker Compose
        try:
            compose_version = subprocess.check_output(['docker', 'compose', 'version'], text=True).strip()
            self.log_success(f"Docker Compose available: {compose_version}")
            self.add_result('system', 'docker_compose', 'pass', f"Docker Compose available: {compose_version}")
        except Exception as e:
            self.log_error(f"Docker Compose not available: {e}")
            self.add_result('system', 'docker_compose', 'fail', f"Docker Compose not available: {e}")
            success = False
        
        # Check Nginx
        try:
            nginx_version = subprocess.check_output(['nginx', '-v'], stderr=subprocess.STDOUT, text=True).strip()
            self.log_success(f"Nginx installed: {nginx_version}")
            self.add_result('system', 'nginx', 'pass', f"Nginx installed: {nginx_version}")
        except Exception as e:
            self.log_error(f"Nginx not available: {e}")
            self.add_result('system', 'nginx', 'fail', f"Nginx not available: {e}")
            success = False
        
        # Check Certbot
        try:
            certbot_version = subprocess.check_output(['certbot', '--version'], text=True).strip()
            self.log_success(f"Certbot installed: {certbot_version}")
            self.add_result('system', 'certbot', 'pass', f"Certbot installed: {certbot_version}")
        except Exception as e:
            self.log_warning(f"Certbot not available: {e}")
            self.add_result('system', 'certbot', 'warn', f"Certbot not available: {e}")
        
        # Check system resources
        try:
            # Memory check
            with open('/proc/meminfo', 'r') as f:
                meminfo = f.read()
                mem_total_kb = int([line for line in meminfo.split('\n') if 'MemTotal:' in line][0].split()[1])
                mem_total_gb = mem_total_kb / 1024 / 1024
                
            if mem_total_gb >= 4:
                self.log_success(f"Memory: {mem_total_gb:.1f}GB (sufficient)")
                self.add_result('system', 'memory', 'pass', f"Memory: {mem_total_gb:.1f}GB (sufficient)")
            else:
                self.log_warning(f"Memory: {mem_total_gb:.1f}GB (recommended: 4GB+)")
                self.add_result('system', 'memory', 'warn', f"Memory: {mem_total_gb:.1f}GB (recommended: 4GB+)")
            
            # CPU check
            cpu_count = os.cpu_count()
            if cpu_count >= 2:
                self.log_success(f"CPU cores: {cpu_count} (sufficient)")
                self.add_result('system', 'cpu', 'pass', f"CPU cores: {cpu_count} (sufficient)")
            else:
                self.log_warning(f"CPU cores: {cpu_count} (recommended: 2+)")
                self.add_result('system', 'cpu', 'warn', f"CPU cores: {cpu_count} (recommended: 2+)")
                
        except Exception as e:
            self.log_warning(f"Could not check system resources: {e}")
            self.add_result('system', 'resources', 'warn', f"Could not check system resources: {e}")
        
        return success
    
    def check_client_configuration(self, client_name: str) -> bool:
        """Check client-specific configuration."""
        self.log_header(f"Configuration Check - {client_name}")
        success = True
        
        client_dir = self.basecamp_dir / 'clients' / client_name
        if not client_dir.exists():
            self.log_error(f"Client directory not found: {client_dir}")
            self.add_result('config', 'client_dir', 'fail', f"Client directory not found: {client_dir}")
            return False
        
        # Check environment file
        env_file = client_dir / '.env.production'
        if not env_file.exists():
            self.log_error(f"Production environment file not found: {env_file}")
            self.add_result('config', 'env_file', 'fail', f"Production environment file not found: {env_file}")
            return False
        
        # Load and validate environment variables
        env_vars = self.load_env_file(env_file)
        required_vars = [
            'CLIENT_NAME', 'CLIENT_DOMAIN', 'BUSINESS_TYPE',
            'AIRTABLE_API_KEY', 'AIRTABLE_BASE_ID', 'API_SECRET_KEY'
        ]
        
        for var in required_vars:
            if var not in env_vars or not env_vars[var]:
                self.log_error(f"Required environment variable missing or empty: {var}")
                self.add_result('config', f'env_var_{var.lower()}', 'fail', f"Required variable missing: {var}")
                success = False
            else:
                # Mask sensitive values
                if 'KEY' in var or 'SECRET' in var:
                    display_value = f"{env_vars[var][:8]}...{env_vars[var][-4:]}"
                else:
                    display_value = env_vars[var]
                self.log_success(f"{var}: {display_value}")
                self.add_result('config', f'env_var_{var.lower()}', 'pass', f"{var} configured")
        
        # Check Docker override file
        docker_override = client_dir / 'docker-compose.override.yml'
        if docker_override.exists():
            self.log_success("Docker override file present")
            self.add_result('config', 'docker_override', 'pass', "Docker override file present")
        else:
            self.log_warning("Docker override file missing")
            self.add_result('config', 'docker_override', 'warn', "Docker override file missing")
        
        # Check deployment script
        deploy_script = client_dir / 'deploy.sh'
        if deploy_script.exists() and deploy_script.stat().st_mode & 0o111:
            self.log_success("Deployment script present and executable")
            self.add_result('config', 'deploy_script', 'pass', "Deployment script ready")
        else:
            self.log_error("Deployment script missing or not executable")
            self.add_result('config', 'deploy_script', 'fail', "Deployment script not ready")
            success = False
        
        return success
    
    def load_env_file(self, env_file: Path) -> Dict[str, str]:
        """Load environment variables from file."""
        env_vars = {}
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key] = value
        except Exception as e:
            self.log_warning(f"Error reading env file: {e}")
        
        return env_vars
    
    def check_ssl_certificate(self, domain: str) -> bool:
        """Check SSL certificate validity."""
        self.log_header(f"SSL Certificate Check - {domain}")
        success = True
        
        try:
            # Check certificate file
            cert_path = Path(f"/etc/letsencrypt/live/{domain}/fullchain.pem")
            if cert_path.exists():
                self.log_success(f"Certificate file exists: {cert_path}")
                
                # Check certificate expiry
                result = subprocess.run([
                    'openssl', 'x509', '-in', str(cert_path), '-noout', '-dates'
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    dates_output = result.stdout
                    # Parse expiry date
                    for line in dates_output.split('\n'):
                        if 'notAfter=' in line:
                            expiry_str = line.split('notAfter=')[1]
                            try:
                                expiry_date = datetime.strptime(expiry_str, '%b %d %H:%M:%S %Y %Z')
                                days_until_expiry = (expiry_date - datetime.now()).days
                                
                                if days_until_expiry > 30:
                                    self.log_success(f"Certificate expires in {days_until_expiry} days")
                                    self.add_result('ssl', 'certificate_expiry', 'pass', f"Expires in {days_until_expiry} days")
                                elif days_until_expiry > 7:
                                    self.log_warning(f"Certificate expires in {days_until_expiry} days (renewal recommended)")
                                    self.add_result('ssl', 'certificate_expiry', 'warn', f"Expires in {days_until_expiry} days")
                                else:
                                    self.log_error(f"Certificate expires in {days_until_expiry} days (urgent renewal needed)")
                                    self.add_result('ssl', 'certificate_expiry', 'fail', f"Expires in {days_until_expiry} days")
                                    success = False
                                    
                            except Exception as e:
                                self.log_warning(f"Could not parse expiry date: {e}")
                                self.add_result('ssl', 'certificate_expiry', 'warn', f"Could not parse expiry date: {e}")
                
                self.add_result('ssl', 'certificate_file', 'pass', f"Certificate file exists: {cert_path}")
            else:
                self.log_error(f"Certificate file not found: {cert_path}")
                self.add_result('ssl', 'certificate_file', 'fail', f"Certificate file not found: {cert_path}")
                success = False
            
            # Test SSL connection
            self.log_info(f"Testing SSL connection to {domain}...")
            context = ssl.create_default_context()
            
            try:
                with socket.create_connection((domain, 443), timeout=10) as sock:
                    with context.wrap_socket(sock, server_hostname=domain) as ssock:
                        cert = ssock.getpeercert()
                        self.log_success(f"SSL connection successful")
                        self.log_info(f"Certificate subject: {cert.get('subject', 'Unknown')}")
                        self.add_result('ssl', 'ssl_connection', 'pass', "SSL connection successful")
                        
            except Exception as e:
                self.log_error(f"SSL connection failed: {e}")
                self.add_result('ssl', 'ssl_connection', 'fail', f"SSL connection failed: {e}")
                success = False
                
        except Exception as e:
            self.log_error(f"SSL certificate check failed: {e}")
            self.add_result('ssl', 'certificate_check', 'fail', f"SSL certificate check failed: {e}")
            success = False
        
        return success
    
    def check_service_health(self, client_name: str, domain: str) -> bool:
        """Check health of all client services."""
        self.log_header(f"Service Health Check - {client_name}")
        success = True
        
        # Check Docker containers
        if self.docker_client:
            try:
                containers = self.docker_client.containers.list(
                    filters={'name': client_name}
                )
                
                expected_containers = [f'{client_name}-nginx', f'{client_name}-api', f'{client_name}-ollama']
                running_containers = [c.name for c in containers if c.status == 'running']
                
                for expected in expected_containers:
                    if expected in running_containers:
                        self.log_success(f"Container running: {expected}")
                        self.add_result('services', f'container_{expected}', 'pass', f"Container running: {expected}")
                    else:
                        self.log_error(f"Container not running: {expected}")
                        self.add_result('services', f'container_{expected}', 'fail', f"Container not running: {expected}")
                        success = False
                
                # Check container health
                for container in containers:
                    health = container.attrs.get('State', {}).get('Health', {})
                    if health:
                        status = health.get('Status', 'unknown')
                        if status == 'healthy':
                            self.log_success(f"{container.name} health: {status}")
                            self.add_result('services', f'health_{container.name}', 'pass', f"Health check: {status}")
                        else:
                            self.log_warning(f"{container.name} health: {status}")
                            self.add_result('services', f'health_{container.name}', 'warn', f"Health check: {status}")
                
            except Exception as e:
                self.log_error(f"Docker container check failed: {e}")
                self.add_result('services', 'docker_containers', 'fail', f"Container check failed: {e}")
                success = False
        
        # Check API health endpoint
        try:
            health_url = f"https://{domain}/api/v1/health"
            self.log_info(f"Checking API health: {health_url}")
            
            response = requests.get(health_url, timeout=30)
            if response.status_code == 200:
                health_data = response.json()
                self.log_success(f"API health check passed")
                self.log_info(f"API response: {health_data}")
                self.add_result('services', 'api_health', 'pass', "API health endpoint responding", health_data)
            else:
                self.log_error(f"API health check failed: HTTP {response.status_code}")
                self.add_result('services', 'api_health', 'fail', f"API health check failed: HTTP {response.status_code}")
                success = False
                
        except Exception as e:
            self.log_error(f"API health check failed: {e}")
            self.add_result('services', 'api_health', 'fail', f"API health check failed: {e}")
            success = False
        
        # Test intake endpoint
        try:
            intake_url = f"https://{domain}/api/v1/intake/health"
            response = requests.get(intake_url, timeout=30)
            if response.status_code == 200:
                self.log_success("Intake API responding")
                self.add_result('services', 'intake_api', 'pass', "Intake API responding")
            else:
                self.log_warning(f"Intake API returned HTTP {response.status_code}")
                self.add_result('services', 'intake_api', 'warn', f"Intake API returned HTTP {response.status_code}")
        except Exception as e:
            self.log_warning(f"Could not test intake API: {e}")
            self.add_result('services', 'intake_api', 'warn', f"Could not test intake API: {e}")
        
        return success
    
    def check_airtable_integration(self, client_name: str) -> bool:
        """Test Airtable CRM integration."""
        self.log_header(f"Airtable Integration Check - {client_name}")
        
        client_dir = self.basecamp_dir / 'clients' / client_name
        env_file = client_dir / '.env.production'
        
        if not env_file.exists():
            self.log_error("Environment file not found")
            return False
        
        env_vars = self.load_env_file(env_file)
        api_key = env_vars.get('AIRTABLE_API_KEY')
        base_id = env_vars.get('AIRTABLE_BASE_ID')
        table_name = env_vars.get('AIRTABLE_TABLE_NAME', 'Leads')
        
        if not api_key or not base_id:
            self.log_error("Airtable credentials not configured")
            self.add_result('integrations', 'airtable_credentials', 'fail', "Airtable credentials not configured")
            return False
        
        try:
            # Test Airtable API connection
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            url = f"https://api.airtable.com/v0/{base_id}/{table_name}"
            response = requests.get(f"{url}?maxRecords=1", headers=headers, timeout=30)
            
            if response.status_code == 200:
                self.log_success("Airtable connection successful")
                self.add_result('integrations', 'airtable_connection', 'pass', "Airtable connection successful")
                return True
            else:
                self.log_error(f"Airtable connection failed: HTTP {response.status_code}")
                self.log_error(f"Response: {response.text}")
                self.add_result('integrations', 'airtable_connection', 'fail', f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_error(f"Airtable connection test failed: {e}")
            self.add_result('integrations', 'airtable_connection', 'fail', f"Connection test failed: {e}")
            return False
    
    def check_performance_metrics(self, client_name: str, domain: str) -> bool:
        """Check basic performance metrics."""
        self.log_header(f"Performance Check - {client_name}")
        success = True
        
        try:
            # Test API response time
            start_time = time.time()
            response = requests.get(f"https://{domain}/api/v1/health", timeout=30)
            response_time = time.time() - start_time
            
            if response_time < 3.0:
                self.log_success(f"API response time: {response_time:.2f}s (good)")
                self.add_result('performance', 'api_response_time', 'pass', f"Response time: {response_time:.2f}s")
            elif response_time < 10.0:
                self.log_warning(f"API response time: {response_time:.2f}s (acceptable)")
                self.add_result('performance', 'api_response_time', 'warn', f"Response time: {response_time:.2f}s")
            else:
                self.log_error(f"API response time: {response_time:.2f}s (slow)")
                self.add_result('performance', 'api_response_time', 'fail', f"Response time: {response_time:.2f}s")
                success = False
                
        except Exception as e:
            self.log_error(f"Performance check failed: {e}")
            self.add_result('performance', 'api_response_time', 'fail', f"Performance check failed: {e}")
            success = False
        
        # Check Docker resource usage
        if self.docker_client:
            try:
                containers = self.docker_client.containers.list(filters={'name': client_name})
                for container in containers:
                    stats = container.stats(stream=False)
                    
                    # Calculate CPU usage
                    cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                               stats['precpu_stats']['cpu_usage']['total_usage']
                    system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                                  stats['precpu_stats']['system_cpu_usage']
                    cpu_usage = (cpu_delta / system_delta) * len(stats['cpu_stats']['cpu_usage']['percpu_usage']) * 100
                    
                    # Calculate memory usage
                    memory_usage = stats['memory_stats']['usage']
                    memory_limit = stats['memory_stats']['limit']
                    memory_percent = (memory_usage / memory_limit) * 100
                    
                    self.log_info(f"{container.name}: CPU {cpu_usage:.1f}%, Memory {memory_percent:.1f}%")
                    self.add_result('performance', f'resources_{container.name}', 'info', 
                                  f"CPU {cpu_usage:.1f}%, Memory {memory_percent:.1f}%")
                    
            except Exception as e:
                self.log_warning(f"Resource usage check failed: {e}")
        
        return success
    
    def validate_client(self, client_name: str) -> bool:
        """Run complete validation for a client."""
        self.log_info(f"🔍 Validating client: {client_name}")
        overall_success = True
        
        # Load client configuration to get domain
        client_dir = self.basecamp_dir / 'clients' / client_name
        env_file = client_dir / '.env.production'
        
        if not env_file.exists():
            self.log_error(f"Client configuration not found: {client_name}")
            return False
        
        env_vars = self.load_env_file(env_file)
        domain = env_vars.get('CLIENT_DOMAIN')
        
        if not domain:
            self.log_error("CLIENT_DOMAIN not found in configuration")
            return False
        
        # Run all checks
        checks = [
            ('Configuration', lambda: self.check_client_configuration(client_name)),
            ('SSL Certificate', lambda: self.check_ssl_certificate(domain)),
            ('Service Health', lambda: self.check_service_health(client_name, domain)),
            ('Airtable Integration', lambda: self.check_airtable_integration(client_name)),
            ('Performance', lambda: self.check_performance_metrics(client_name, domain))
        ]
        
        for check_name, check_func in checks:
            try:
                success = check_func()
                if not success:
                    overall_success = False
            except Exception as e:
                self.log_error(f"{check_name} check failed: {e}")
                overall_success = False
        
        return overall_success
    
    def list_clients(self) -> List[str]:
        """List all configured clients."""
        clients = []
        clients_dir = self.basecamp_dir / 'clients'
        
        if clients_dir.exists():
            for client_dir in clients_dir.iterdir():
                if client_dir.is_dir() and (client_dir / '.env.production').exists():
                    clients.append(client_dir.name)
        
        return clients
    
    def generate_report(self) -> Dict:
        """Generate validation report."""
        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'results': self.results,
            'summary': {
                'total_checks': len(self.results),
                'passed': len([r for r in self.results if r['status'] == 'pass']),
                'warnings': len([r for r in self.results if r['status'] == 'warn']),
                'failed': len([r for r in self.results if r['status'] == 'fail'])
            }
        }
        
        return report
    
    def print_summary(self):
        """Print validation summary."""
        summary = self.generate_report()['summary']
        
        self.log_header("Validation Summary")
        print(f"Total checks: {summary['total_checks']}")
        print(f"{Colors.GREEN}Passed: {summary['passed']}{Colors.NC}")
        print(f"{Colors.YELLOW}Warnings: {summary['warnings']}{Colors.NC}")
        print(f"{Colors.RED}Failed: {summary['failed']}{Colors.NC}")
        
        if summary['failed'] == 0:
            self.log_success("🎉 All critical checks passed!")
        else:
            self.log_error(f"❌ {summary['failed']} checks failed")
            
        if summary['warnings'] > 0:
            self.log_warning(f"⚠️ {summary['warnings']} warnings to review")


def main():
    parser = argparse.ArgumentParser(description='Validate baseCamp production deployment')
    parser.add_argument('--client', help='Validate specific client')
    parser.add_argument('--all-clients', action='store_true', help='Validate all clients')
    parser.add_argument('--system-check', action='store_true', help='Run system requirements check only')
    parser.add_argument('--output-json', help='Output results to JSON file')
    parser.add_argument('--base-dir', type=Path, help='Base directory (default: auto-detect)')
    
    args = parser.parse_args()
    
    validator = ProductionValidator(args.base_dir)
    
    print("🔍 baseCamp Production Readiness Validator")
    print("=" * 50)
    
    overall_success = True
    
    # System check
    if args.system_check or not (args.client or args.all_clients):
        success = validator.check_system_requirements()
        if not success:
            overall_success = False
    
    # Client validation
    if args.client:
        success = validator.validate_client(args.client)
        if not success:
            overall_success = False
            
    elif args.all_clients:
        clients = validator.list_clients()
        if not clients:
            validator.log_warning("No clients found")
        else:
            validator.log_info(f"Found {len(clients)} clients: {', '.join(clients)}")
            for client in clients:
                success = validator.validate_client(client)
                if not success:
                    overall_success = False
                print()  # Blank line between clients
    
    # Generate report
    if args.output_json:
        report = validator.generate_report()
        with open(args.output_json, 'w') as f:
            json.dump(report, f, indent=2)
        validator.log_info(f"Report saved to: {args.output_json}")
    
    # Print summary
    validator.print_summary()
    
    # Exit with appropriate code
    sys.exit(0 if overall_success else 1)


if __name__ == '__main__':
    main()