#!/usr/bin/env python3
"""
Infrastructure Test Script for Agentic AI KYC Engine
Tests all running infrastructure components
"""

import requests
import psycopg2
import pymongo
import redis
import json
from kafka import KafkaProducer, KafkaConsumer
import time
import sys

def test_prometheus():
    """Test Prometheus metrics endpoint"""
    try:
        response = requests.get("http://localhost:9090/-/healthy", timeout=5)
        if response.status_code == 200:
            print("✅ Prometheus: Running and healthy")
            return True
        else:
            print(f"❌ Prometheus: Error {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Prometheus: Connection failed - {e}")
        return False

def test_grafana():
    """Test Grafana dashboard"""
    try:
        response = requests.get("http://localhost:3000/api/health", timeout=5)
        if response.status_code == 200:
            print("✅ Grafana: Running and healthy")
            return True
        else:
            print(f"❌ Grafana: Error {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Grafana: Connection failed - {e}")
        return False

def test_postgresql():
    """Test PostgreSQL database connection"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            port="5432",
            database="kyc_db",
            user="postgres",
            password="password"
        )
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        cursor.close()
        conn.close()
        print("✅ PostgreSQL: Connected successfully")
        return True
    except Exception as e:
        print(f"❌ PostgreSQL: Connection failed - {e}")
        return False

def test_mongodb():
    """Test MongoDB connection"""
    try:
        client = pymongo.MongoClient("mongodb://admin:password@localhost:27017/")
        db = client.kyc_db
        # Test connection
        client.server_info()
        print("✅ MongoDB: Connected successfully")
        return True
    except Exception as e:
        print(f"❌ MongoDB: Connection failed - {e}")
        return False

def test_redis():
    """Test Redis connection"""
    try:
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        print("✅ Redis: Connected successfully")
        return True
    except Exception as e:
        print(f"❌ Redis: Connection failed - {e}")
        return False

def test_kafka():
    """Test Kafka message bus"""
    try:
        # Test producer
        producer = KafkaProducer(
            bootstrap_servers=['localhost:9092'],
            value_serializer=lambda x: json.dumps(x).encode('utf-8')
        )
        
        # Send test message
        test_message = {"test": "message", "timestamp": time.time()}
        producer.send('test-topic', test_message)
        producer.flush()
        producer.close()
        
        print("✅ Kafka: Message sent successfully")
        return True
    except Exception as e:
        print(f"❌ Kafka: Connection failed - {e}")
        return False

def main():
    """Run all infrastructure tests"""
    print("🔍 Testing Agentic AI KYC Engine Infrastructure")
    print("=" * 50)
    
    tests = [
        test_prometheus,
        test_grafana,
        test_postgresql,
        test_mongodb,
        test_redis,
        test_kafka
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        time.sleep(0.5)  # Small delay between tests
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All infrastructure components are running successfully!")
        print("\n🌐 Access URLs:")
        print("   • Prometheus: http://localhost:9090")
        print("   • Grafana: http://localhost:3000 (admin/admin)")
        print("\n🚀 Infrastructure is ready for agent deployment!")
        return 0
    else:
        print(f"⚠️  {total - passed} components need attention")
        return 1

if __name__ == "__main__":
    sys.exit(main())
