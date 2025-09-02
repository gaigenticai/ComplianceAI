#!/usr/bin/env python3
"""
Service Dependency Checker
Rule 15 Compliance: Complete all issues before proceeding
"""

import socket
import time
import sys
import os
from typing import List, Tuple

def wait_for_port(host: str, port: int, timeout: int = 60) -> bool:
    """Wait for a port to become available"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                if result == 0:
                    return True
        except Exception:
            pass
        
        time.sleep(1)
    
    return False

def check_service_health(url: str, timeout: int = 5) -> bool:
    """Check if a service is healthy via HTTP"""
    try:
        import requests
        response = requests.get(url, timeout=timeout)
        return response.status_code == 200
    except Exception:
        return False

def load_port_assignments():
    """Load port assignments from .port_assignments file"""
    ports = {}
    try:
        with open('.port_assignments', 'r') as f:
            for line in f:
                if '=' in line:
                    service, port = line.strip().split('=')
                    ports[service] = int(port)
    except FileNotFoundError:
        # Default ports if file doesn't exist
        ports = {
            'postgres': 5432,
            'redis': 6379,
            'mongodb': 27017,
            'qdrant': 6333,
            'zookeeper': 2181,
            'kafka': 9092,
            'web-interface': 8000,
            'intake-agent': 8001,
            'intelligence-agent': 8002,
            'decision-agent': 8003
        }
    return ports

def main():
    """Wait for all required services to be ready"""
    print("🔍 Checking service dependencies...")
    
    # Load resolved port assignments
    ports = load_port_assignments()
    
    # Services to wait for with resolved ports
    services = [
        ("PostgreSQL", "localhost", ports.get('postgres', 5432)),
        ("Redis", "localhost", ports.get('redis', 6379)),
        ("MongoDB", "localhost", ports.get('mongodb', 27017)),
        ("Qdrant", "localhost", ports.get('qdrant', 6333)),
        ("Zookeeper", "localhost", ports.get('zookeeper', 2181)),
        ("Kafka", "localhost", ports.get('kafka', 9092)),
    ]
    
    # Wait for each service
    all_ready = True
    for service_name, host, port in services:
        print(f"⏳ Waiting for {service_name} on {host}:{port}...")
        
        if wait_for_port(host, port, timeout=60):
            print(f"✅ {service_name} is ready")
        else:
            print(f"❌ {service_name} failed to start within timeout")
            all_ready = False
    
    # Wait for agents to be healthy with resolved ports
    agent_services = [
        ("Intake Agent", f"http://localhost:{ports.get('intake-agent', 8001)}/health"),
        ("Intelligence Agent", f"http://localhost:{ports.get('intelligence-agent', 8002)}/health"),
        ("Decision Agent", f"http://localhost:{ports.get('decision-agent', 8003)}/health"),
    ]
    
    print("\n🔍 Checking agent health...")
    for service_name, health_url in agent_services:
        print(f"⏳ Waiting for {service_name}...")
        
        # Wait up to 2 minutes for agents to be healthy
        start_time = time.time()
        while time.time() - start_time < 120:
            if check_service_health(health_url):
                print(f"✅ {service_name} is healthy")
                break
            time.sleep(2)
        else:
            print(f"❌ {service_name} failed to become healthy")
            all_ready = False
    
    if all_ready:
        print("\n🎉 All services are ready!")
        sys.exit(0)
    else:
        print("\n❌ Some services failed to start properly")
        sys.exit(1)

if __name__ == "__main__":
    main()
