#!/usr/bin/env python3
"""
baseCamp Client Configuration Generator

This script generates production-ready configuration files for new clients.
It creates all necessary environment files and validates the setup.

Usage:
    python scripts/generate-client-config.py --client-name automotive-shop-1 --domain shop1.basecamp.example.com --business-type automotive

Requirements:
    - Client's Airtable API credentials
    - Domain name configured with DNS pointing to server
    - Business type selection
"""

import argparse
import os
import secrets
import sys
from pathlib import Path
from typing import Dict, Optional
import re


class ClientConfigGenerator:
    """Generates production configuration for baseCamp clients."""
    
    VALID_BUSINESS_TYPES = ['automotive', 'medspa', 'consulting', 'general']
    
    def __init__(self, base_dir: Path = None):
        self.base_dir = base_dir or Path(__file__).parent.parent
        self.template_path = self.base_dir / '.env.production.template'
        
    def validate_client_name(self, client_name: str) -> bool:
        """Validate client name format."""
        pattern = r'^[a-z0-9-]+$'
        if not re.match(pattern, client_name):
            print(f"❌ Client name must be lowercase alphanumeric with hyphens only: {client_name}")
            return False
        if len(client_name) < 3 or len(client_name) > 30:
            print(f"❌ Client name must be 3-30 characters: {client_name}")
            return False
        return True
    
    def validate_domain(self, domain: str) -> bool:
        """Validate domain name format."""
        pattern = r'^[a-zA-Z0-9-]+\.([a-zA-Z0-9-]+\.)*[a-zA-Z]{2,}$'
        if not re.match(pattern, domain):
            print(f"❌ Invalid domain format: {domain}")
            return False
        return True
    
    def validate_business_type(self, business_type: str) -> bool:
        """Validate business type."""
        if business_type not in self.VALID_BUSINESS_TYPES:
            print(f"❌ Business type must be one of: {', '.join(self.VALID_BUSINESS_TYPES)}")
            return False
        return True
    
    def generate_secure_key(self, length: int = 64) -> str:
        """Generate a secure random key."""
        return secrets.token_hex(length // 2)
    
    def get_user_input(self, prompt: str, validator=None, required: bool = True) -> Optional[str]:
        """Get and validate user input."""
        while True:
            try:
                value = input(f"{prompt}: ").strip()
                
                if not value and required:
                    print("❌ This field is required.")
                    continue
                    
                if not value and not required:
                    return None
                    
                if validator and not validator(value):
                    continue
                    
                return value
                
            except KeyboardInterrupt:
                print("\n\n❌ Configuration generation cancelled.")
                sys.exit(1)
    
    def collect_client_info(self, args) -> Dict[str, str]:
        """Collect all client configuration information."""
        config = {}
        
        # Basic client info
        if args.client_name:
            if not self.validate_client_name(args.client_name):
                sys.exit(1)
            config['CLIENT_NAME'] = args.client_name
        else:
            config['CLIENT_NAME'] = self.get_user_input(
                "Enter client name (lowercase, hyphens only)", 
                self.validate_client_name
            )
            
        if args.domain:
            if not self.validate_domain(args.domain):
                sys.exit(1)
            config['CLIENT_DOMAIN'] = args.domain
        else:
            config['CLIENT_DOMAIN'] = self.get_user_input(
                "Enter client domain (e.g., client.example.com)", 
                self.validate_domain
            )
            
        if args.business_type:
            if not self.validate_business_type(args.business_type):
                sys.exit(1)
            config['BUSINESS_TYPE'] = args.business_type
        else:
            print(f"\nAvailable business types: {', '.join(self.VALID_BUSINESS_TYPES)}")
            config['BUSINESS_TYPE'] = self.get_user_input(
                "Enter business type",
                self.validate_business_type
            )
        
        # Airtable credentials
        print(f"\n📋 Airtable Configuration for {config['CLIENT_NAME']}")
        print("ℹ️  Get these from: https://airtable.com/account (API key) and your base URL")
        
        config['AIRTABLE_API_KEY'] = self.get_user_input(
            "Enter Airtable API key"
        )
        config['AIRTABLE_BASE_ID'] = self.get_user_input(
            "Enter Airtable Base ID (starts with 'app')"
        )
        config['AIRTABLE_TABLE_NAME'] = self.get_user_input(
            "Enter Airtable table name (default: Leads)",
            required=False
        ) or 'Leads'
        
        # Contact info
        config['CLIENT_CONTACT_EMAIL'] = self.get_user_input(
            "Enter client admin email"
        )
        
        config['CLIENT_TIMEZONE'] = self.get_user_input(
            "Enter client timezone (default: America/New_York)",
            required=False
        ) or 'America/New_York'
        
        # Admin email for SSL certificates
        config['LETSENCRYPT_EMAIL'] = self.get_user_input(
            "Enter your admin email for SSL certificates"
        )
        
        # Generate secure keys
        config['API_SECRET_KEY'] = self.generate_secure_key()
        config['WEBHOOK_SECRET_KEY'] = self.generate_secure_key()
        
        return config
    
    def apply_template_substitutions(self, template_content: str, config: Dict[str, str]) -> str:
        """Apply configuration substitutions to template."""
        content = template_content
        
        # Direct replacements
        replacements = {
            'CLIENT_NAME=client-name': f'CLIENT_NAME={config["CLIENT_NAME"]}',
            'CLIENT_DOMAIN=client.yourdomain.com': f'CLIENT_DOMAIN={config["CLIENT_DOMAIN"]}',
            'BUSINESS_TYPE=automotive': f'BUSINESS_TYPE={config["BUSINESS_TYPE"]}',
            'CLIENT_CONTACT_EMAIL=admin@client.com': f'CLIENT_CONTACT_EMAIL={config["CLIENT_CONTACT_EMAIL"]}',
            'CLIENT_TIMEZONE=America/New_York': f'CLIENT_TIMEZONE={config["CLIENT_TIMEZONE"]}',
            'AIRTABLE_API_KEY=your_client_airtable_api_key_here': f'AIRTABLE_API_KEY={config["AIRTABLE_API_KEY"]}',
            'AIRTABLE_BASE_ID=your_client_airtable_base_id_here': f'AIRTABLE_BASE_ID={config["AIRTABLE_BASE_ID"]}',
            'AIRTABLE_TABLE_NAME=Leads': f'AIRTABLE_TABLE_NAME={config["AIRTABLE_TABLE_NAME"]}',
            'LETSENCRYPT_EMAIL=admin@yourdomain.com': f'LETSENCRYPT_EMAIL={config["LETSENCRYPT_EMAIL"]}',
            'API_SECRET_KEY=REPLACE_WITH_SECURE_RANDOM_KEY_32_CHARS_MIN': f'API_SECRET_KEY={config["API_SECRET_KEY"]}',
            'WEBHOOK_SECRET_KEY=REPLACE_WITH_WEBHOOK_SECRET': f'WEBHOOK_SECRET_KEY={config["WEBHOOK_SECRET_KEY"]}',
        }
        
        for old, new in replacements.items():
            content = content.replace(old, new)
            
        return content
    
    def generate_config_file(self, config: Dict[str, str]) -> Path:
        """Generate the production environment file."""
        # Read template
        if not self.template_path.exists():
            print(f"❌ Template file not found: {self.template_path}")
            sys.exit(1)
            
        with open(self.template_path, 'r') as f:
            template_content = f.read()
        
        # Apply substitutions
        config_content = self.apply_template_substitutions(template_content, config)
        
        # Create client config directory
        client_dir = self.base_dir / 'clients' / config['CLIENT_NAME']
        client_dir.mkdir(parents=True, exist_ok=True)
        
        # Write configuration file
        config_file = client_dir / '.env.production'
        with open(config_file, 'w') as f:
            f.write(config_content)
            
        return config_file
    
    def generate_docker_override(self, config: Dict[str, str]) -> Path:
        """Generate client-specific Docker compose override."""
        client_dir = self.base_dir / 'clients' / config['CLIENT_NAME']
        
        override_content = f"""version: '3.8'

# Client-specific Docker Compose overrides for {config['CLIENT_NAME']}
# This file extends docker-compose.prod.yml with client-specific settings

services:
  nginx:
    container_name: {config['CLIENT_NAME']}-nginx
    volumes:
      - ./nginx/{config['CLIENT_NAME']}.conf:/etc/nginx/conf.d/default.conf:ro
    environment:
      - CLIENT_DOMAIN={config['CLIENT_DOMAIN']}

  ollama:
    container_name: {config['CLIENT_NAME']}-ollama
    environment:
      - OLLAMA_ORIGINS=http://api:8000,https://{config['CLIENT_DOMAIN']}

  api:
    container_name: {config['CLIENT_NAME']}-api
    environment:
      - CLIENT_NAME={config['CLIENT_NAME']}
      - CLIENT_DOMAIN={config['CLIENT_DOMAIN']}

volumes:
  ollama_data:
    name: {config['CLIENT_NAME']}_ollama_data
  chroma_data:
    name: {config['CLIENT_NAME']}_chroma_data
  logs_data:
    name: {config['CLIENT_NAME']}_logs_data
  redis_data:
    name: {config['CLIENT_NAME']}_redis_data
  nginx_logs:
    name: {config['CLIENT_NAME']}_nginx_logs

networks:
  basecamp-network:
    name: {config['CLIENT_NAME']}-network
"""
        
        override_file = client_dir / 'docker-compose.override.yml'
        with open(override_file, 'w') as f:
            f.write(override_content)
            
        return override_file
    
    def generate_deployment_script(self, config: Dict[str, str]) -> Path:
        """Generate client deployment script."""
        client_dir = self.base_dir / 'clients' / config['CLIENT_NAME']
        
        script_content = f"""#!/bin/bash
# Deployment script for {config['CLIENT_NAME']}
# Generated by baseCamp client configuration generator

set -e

CLIENT_NAME="{config['CLIENT_NAME']}"
CLIENT_DOMAIN="{config['CLIENT_DOMAIN']}"
CLIENT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
BASE_DIR="$(cd "$CLIENT_DIR/../.." && pwd)"

echo "🚀 Deploying baseCamp for client: $CLIENT_NAME"
echo "📍 Domain: $CLIENT_DOMAIN"
echo "📂 Client directory: $CLIENT_DIR"

# Verify configuration files exist
if [ ! -f "$CLIENT_DIR/.env.production" ]; then
    echo "❌ Production environment file not found: $CLIENT_DIR/.env.production"
    exit 1
fi

# Create nginx configuration directory if needed
mkdir -p "$CLIENT_DIR/nginx"

# Stop existing containers if running
echo "⏹️  Stopping existing containers..."
cd "$BASE_DIR"
docker-compose -f docker-compose.prod.yml -f "$CLIENT_DIR/docker-compose.override.yml" --env-file "$CLIENT_DIR/.env.production" down || true

# Pull latest images
echo "📥 Pulling latest images..."
docker-compose -f docker-compose.prod.yml -f "$CLIENT_DIR/docker-compose.override.yml" --env-file "$CLIENT_DIR/.env.production" pull

# Build application image
echo "🔨 Building application..."
docker-compose -f docker-compose.prod.yml -f "$CLIENT_DIR/docker-compose.override.yml" --env-file "$CLIENT_DIR/.env.production" build

# Start services
echo "▶️  Starting services..."
docker-compose -f docker-compose.prod.yml -f "$CLIENT_DIR/docker-compose.override.yml" --env-file "$CLIENT_DIR/.env.production" up -d

# Wait for health checks
echo "🏥 Waiting for services to be healthy..."
sleep 30

# Check service status
echo "📊 Service status:"
docker-compose -f docker-compose.prod.yml -f "$CLIENT_DIR/docker-compose.override.yml" --env-file "$CLIENT_DIR/.env.production" ps

echo "✅ Deployment complete for $CLIENT_NAME"
echo "🌐 Service should be available at: https://$CLIENT_DOMAIN"
echo "🔍 Check logs: docker-compose -f docker-compose.prod.yml -f $CLIENT_DIR/docker-compose.override.yml --env-file $CLIENT_DIR/.env.production logs -f"
"""
        
        script_file = client_dir / 'deploy.sh'
        with open(script_file, 'w') as f:
            f.write(script_content)
            
        # Make executable
        script_file.chmod(0o755)
        
        return script_file
    
    def print_summary(self, config: Dict[str, str], config_file: Path, override_file: Path, script_file: Path):
        """Print configuration summary."""
        print(f"\n✅ Client configuration generated successfully!")
        print(f"📋 Client: {config['CLIENT_NAME']}")
        print(f"🌐 Domain: {config['CLIENT_DOMAIN']}")
        print(f"🏢 Business Type: {config['BUSINESS_TYPE']}")
        print(f"\n📁 Generated files:")
        print(f"   • {config_file}")
        print(f"   • {override_file}")
        print(f"   • {script_file}")
        
        print(f"\n📝 Next Steps:")
        print(f"   1. Review the configuration file: {config_file}")
        print(f"   2. Ensure DNS for {config['CLIENT_DOMAIN']} points to your server")
        print(f"   3. Run SSL setup: scripts/setup-ssl.sh {config['CLIENT_NAME']}")
        print(f"   4. Deploy client: {script_file}")
        
        print(f"\n⚠️  Important:")
        print(f"   • Keep {config_file} secure - it contains API keys")
        print(f"   • Test Airtable connection before deployment")
        print(f"   • Verify domain DNS configuration")


def main():
    parser = argparse.ArgumentParser(description='Generate baseCamp client configuration')
    parser.add_argument('--client-name', help='Client name (lowercase, hyphens only)')
    parser.add_argument('--domain', help='Client domain (e.g., client.example.com)')
    parser.add_argument('--business-type', choices=['automotive', 'medspa', 'consulting', 'general'], 
                       help='Business type for AI optimization')
    parser.add_argument('--base-dir', type=Path, help='Base directory (default: auto-detect)')
    
    args = parser.parse_args()
    
    generator = ClientConfigGenerator(args.base_dir)
    
    print("🏗️  baseCamp Client Configuration Generator")
    print("=" * 50)
    
    # Collect configuration
    config = generator.collect_client_info(args)
    
    # Generate files
    print(f"\n📝 Generating configuration files...")
    config_file = generator.generate_config_file(config)
    override_file = generator.generate_docker_override(config)
    script_file = generator.generate_deployment_script(config)
    
    # Print summary
    generator.print_summary(config, config_file, override_file, script_file)


if __name__ == '__main__':
    main()