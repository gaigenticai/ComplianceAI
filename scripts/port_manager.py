#!/usr/bin/env python3
"""
Automatic Port Conflict Resolution System
Rule 8 Compliance: Docker must have automatic port conflicts resolution
"""

import socket
import yaml
import sys
import os
from typing import Dict, List, Tuple

class PortManager:
    """
    Manages automatic port conflict resolution for Docker services
    
    Features:
    - Detects port conflicts before starting services
    - Automatically assigns alternative ports
    - Updates docker-compose configuration
    - Maintains port mapping consistency
    """
    
    def __init__(self, compose_file: str = "docker-compose-simplified.yml"):
        self.compose_file = compose_file
        self.base_ports = {
            'postgres': 5432,
            'redis': 6379,
            'qdrant': 6333,
            'web-interface': 8000,
            'intake-agent': 8001,
            'intelligence-agent': 8002,
            'decision-agent': 8003,
            'prometheus-intake': 9001,
            'prometheus-intelligence': 9002,
            'prometheus-decision': 9003
        }
        self.assigned_ports = {}
        
    def is_port_available(self, port: int, host: str = 'localhost') -> bool:
        """Check if a port is available on the given host"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                return result != 0
        except Exception:
            return False
    
    def find_available_port(self, base_port: int, max_attempts: int = 100) -> int:
        """Find the next available port starting from base_port"""
        for offset in range(max_attempts):
            port = base_port + offset
            if self.is_port_available(port):
                return port
        raise RuntimeError(f"Could not find available port starting from {base_port}")
    
    def resolve_port_conflicts(self) -> Dict[str, int]:
        """
        Resolve all port conflicts and return mapping of service -> port
        """
        print("🔍 Checking for port conflicts...")
        
        conflicts_found = False
        for service, base_port in self.base_ports.items():
            if not self.is_port_available(base_port):
                conflicts_found = True
                new_port = self.find_available_port(base_port + 1)
                self.assigned_ports[service] = new_port
                print(f"⚠️  Port {base_port} conflict for {service} -> using {new_port}")
            else:
                self.assigned_ports[service] = base_port
                print(f"✅ Port {base_port} available for {service}")
        
        if not conflicts_found:
            print("✅ No port conflicts detected")
        else:
            print("🔧 Port conflicts resolved automatically")
            
        return self.assigned_ports
    
    def update_docker_compose(self) -> bool:
        """
        Update docker-compose file with resolved ports
        """
        try:
            # Read current docker-compose file
            with open(self.compose_file, 'r') as f:
                compose_data = yaml.safe_load(f)
            
            # Update port mappings
            services = compose_data.get('services', {})
            
            # Update PostgreSQL ports
            if 'postgres' in services and self.assigned_ports['postgres'] != 5432:
                services['postgres']['ports'] = [
                    f"{self.assigned_ports['postgres']}:5432"
                ]
            
            # Update Redis ports
            if 'redis' in services and self.assigned_ports['redis'] != 6379:
                services['redis']['ports'] = [
                    f"{self.assigned_ports['redis']}:6379"
                ]
            
            # Update Qdrant ports
            if 'qdrant' in services and self.assigned_ports['qdrant'] != 6333:
                services['qdrant']['ports'] = [
                    f"{self.assigned_ports['qdrant']}-{self.assigned_ports['qdrant']+1}:6333-6334"
                ]
            
            # Update web interface port
            if 'web-interface' in services and self.assigned_ports['web-interface'] != 8000:
                services['web-interface']['ports'] = [
                    f"{self.assigned_ports['web-interface']}:8000"
                ]
            
            # Write updated compose file
            with open(self.compose_file, 'w') as f:
                yaml.dump(compose_data, f, default_flow_style=False, indent=2)
            
            print(f"✅ Updated {self.compose_file} with resolved ports")
            return True
            
        except Exception as e:
            print(f"❌ Failed to update docker-compose file: {e}")
            return False
    
    def update_environment_files(self) -> bool:
        """
        Update environment files with new port assignments
        """
        try:
            env_files = ['.env.simplified.example']
            
            for env_file in env_files:
                if os.path.exists(env_file):
                    with open(env_file, 'r') as f:
                        content = f.read()
                    
                    # Update database URLs with new ports
                    if self.assigned_ports['postgres'] != 5432:
                        content = content.replace(
                            'localhost:5432',
                            f"localhost:{self.assigned_ports['postgres']}"
                        )
                    
                    if self.assigned_ports['redis'] != 6379:
                        content = content.replace(
                            'localhost:6379',
                            f"localhost:{self.assigned_ports['redis']}"
                        )
                    
                    if self.assigned_ports['qdrant'] != 6333:
                        content = content.replace(
                            'localhost:6333',
                            f"localhost:{self.assigned_ports['qdrant']}"
                        )
                    
                    with open(env_file, 'w') as f:
                        f.write(content)
                    
                    print(f"✅ Updated {env_file} with resolved ports")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to update environment files: {e}")
            return False
    
    def generate_port_report(self) -> str:
        """
        Generate a report of port assignments
        """
        report = "\n" + "="*50 + "\n"
        report += "PORT ASSIGNMENT REPORT\n"
        report += "="*50 + "\n"
        
        for service, port in self.assigned_ports.items():
            original_port = self.base_ports[service]
            status = "✅ Original" if port == original_port else f"🔧 Changed from {original_port}"
            report += f"{service:20} : {port:5} {status}\n"
        
        report += "="*50 + "\n"
        return report

def main():
    """
    Main function to resolve port conflicts
    """
    if len(sys.argv) > 1:
        compose_file = sys.argv[1]
    else:
        compose_file = "docker-compose-simplified.yml"
    
    print("🚀 Starting Automatic Port Conflict Resolution")
    print(f"📁 Using compose file: {compose_file}")
    
    port_manager = PortManager(compose_file)
    
    # Resolve port conflicts
    assigned_ports = port_manager.resolve_port_conflicts()
    
    # Update docker-compose file
    if not port_manager.update_docker_compose():
        sys.exit(1)
    
    # Update environment files
    if not port_manager.update_environment_files():
        sys.exit(1)
    
    # Generate and display report
    print(port_manager.generate_port_report())
    
    # Save port assignments for other scripts
    port_file = ".port_assignments"
    with open(port_file, 'w') as f:
        for service, port in assigned_ports.items():
            f.write(f"{service}={port}\n")
    
    print(f"💾 Port assignments saved to {port_file}")
    print("✅ Automatic port conflict resolution completed successfully")

if __name__ == "__main__":
    main()
