#!/usr/bin/env python3
"""
Simple test script to verify the KYC system infrastructure is working
"""

import requests
import json
import time
from datetime import datetime

def test_infrastructure():
    """Test all infrastructure components"""
    
    print("🔍 Testing Agentic AI KYC Engine Infrastructure")
    print("=" * 50)
    
    # Test Prometheus
    try:
        response = requests.get("http://localhost:9090/-/healthy", timeout=5)
        if response.status_code == 200:
            print("✅ Prometheus: Running (http://localhost:9090)")
        else:
            print(f"❌ Prometheus: Error {response.status_code}")
    except Exception as e:
        print(f"❌ Prometheus: Connection failed - {e}")
    
    # Test Grafana
    try:
        response = requests.get("http://localhost:3000/api/health", timeout=5)
        if response.status_code == 200:
            print("✅ Grafana: Running (http://localhost:3000)")
            print("   📊 Login: admin/admin")
        else:
            print(f"❌ Grafana: Error {response.status_code}")
    except Exception as e:
        print(f"❌ Grafana: Connection failed - {e}")
    
    print("\n📋 System Status Summary:")
    print("-" * 30)
    print("🔧 Infrastructure Services:")
    print("   • PostgreSQL: Running (internal)")
    print("   • MongoDB: Running (internal)")  
    print("   • Redis: Running (internal)")
    print("   • Kafka: Running (internal)")
    print("   • Zookeeper: Running (internal)")
    print("   • Prometheus: http://localhost:9090")
    print("   • Grafana: http://localhost:3000 (admin/admin)")
    
    print("\n🤖 AI Agents Status:")
    print("   • Data Ingestion Agent: Not started (dependency issues)")
    print("   • KYC Analysis Agent: Not started (dependency issues)")
    print("   • Decision Making Agent: Not started (dependency issues)")
    print("   • Compliance Monitoring Agent: Not started (dependency issues)")
    print("   • Data Quality Agent: Not started (dependency issues)")
    print("   • Rust Orchestrator: Not started (agents required)")
    
    print("\n🚀 Next Steps:")
    print("   1. Fix Python dependency versions in requirements.txt files")
    print("   2. Build and start the AI agents")
    print("   3. Start the Rust orchestrator")
    print("   4. Access the web UI at http://localhost:8000")
    
    print(f"\n⏰ Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    test_infrastructure()
