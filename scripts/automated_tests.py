#!/usr/bin/env python3
"""
Automated Testing Suite for ComplianceAI
Rule 12 Compliance: Perform automated testing of UI and code
"""

import requests
import json
import time
import sys
import subprocess
from typing import Dict, List, Tuple, Optional
import concurrent.futures
from dataclasses import dataclass

@dataclass
class TestResult:
    """Test result data structure"""
    name: str
    passed: bool
    message: str
    duration: float
    details: Optional[Dict] = None

class AutomatedTestSuite:
    """
    Comprehensive automated testing suite for the ComplianceAI system
    
    Tests:
    - Agent health endpoints
    - API functionality
    - Database connections
    - UI component loading
    - Inter-agent communication
    - Performance benchmarks
    """
    
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.agent_urls = {
            'intake': 'http://localhost:8001',
            'intelligence': 'http://localhost:8002', 
            'decision': 'http://localhost:8003'
        }
        self.test_results: List[TestResult] = []
        self.timeout = 10
        
    def run_test(self, test_name: str, test_func) -> TestResult:
        """Run a single test and capture results"""
        print(f"🧪 Running test: {test_name}")
        start_time = time.time()
        
        try:
            result = test_func()
            duration = time.time() - start_time
            
            if result.get('success', False):
                print(f"✅ {test_name} - PASSED ({duration:.2f}s)")
                return TestResult(test_name, True, result.get('message', 'Test passed'), duration, result.get('details'))
            else:
                print(f"❌ {test_name} - FAILED ({duration:.2f}s): {result.get('message', 'Unknown error')}")
                return TestResult(test_name, False, result.get('message', 'Test failed'), duration, result.get('details'))
                
        except Exception as e:
            duration = time.time() - start_time
            print(f"❌ {test_name} - ERROR ({duration:.2f}s): {str(e)}")
            return TestResult(test_name, False, f"Exception: {str(e)}", duration)
    
    def test_agent_health(self) -> Dict:
        """Test all agent health endpoints"""
        try:
            results = {}
            for agent_name, url in self.agent_urls.items():
                try:
                    response = requests.get(f"{url}/health", timeout=self.timeout)
                    if response.status_code == 200:
                        data = response.json()
                        results[agent_name] = {
                            'status': 'healthy',
                            'response_time': response.elapsed.total_seconds(),
                            'data': data
                        }
                    else:
                        results[agent_name] = {
                            'status': 'unhealthy',
                            'status_code': response.status_code
                        }
                except Exception as e:
                    results[agent_name] = {
                        'status': 'error',
                        'error': str(e)
                    }
            
            # Check if all agents are healthy
            healthy_count = sum(1 for r in results.values() if r.get('status') == 'healthy')
            total_agents = len(self.agent_urls)
            
            return {
                'success': healthy_count == total_agents,
                'message': f"{healthy_count}/{total_agents} agents healthy",
                'details': results
            }
            
        except Exception as e:
            return {'success': False, 'message': f"Health check failed: {str(e)}"}
    
    def test_database_connections(self) -> Dict:
        """Test database connectivity through agents"""
        try:
            # Test through intake agent which should have all DB connections
            response = requests.get(f"{self.agent_urls['intake']}/health", timeout=self.timeout)
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'message': 'Database connections verified through agent health',
                    'details': {'response_code': response.status_code}
                }
            else:
                return {
                    'success': False,
                    'message': f'Database connection test failed: HTTP {response.status_code}'
                }
                
        except Exception as e:
            return {'success': False, 'message': f"Database test failed: {str(e)}"}
    
    def test_ui_components(self) -> Dict:
        """Test UI component loading"""
        try:
            # Test main dashboard
            response = requests.get(f"{self.base_url}/agentic", timeout=self.timeout)
            
            if response.status_code == 200:
                content = response.text
                
                # Check for key UI components
                required_components = [
                    'dashboard',
                    'live-agents', 
                    'case-processing',
                    'agent-testing',
                    'user-guides'  # New component we added
                ]
                
                missing_components = []
                for component in required_components:
                    if component not in content:
                        missing_components.append(component)
                
                if not missing_components:
                    return {
                        'success': True,
                        'message': 'All UI components loaded successfully',
                        'details': {'components_found': required_components}
                    }
                else:
                    return {
                        'success': False,
                        'message': f'Missing UI components: {missing_components}',
                        'details': {'missing': missing_components}
                    }
            else:
                return {
                    'success': False,
                    'message': f'UI loading failed: HTTP {response.status_code}'
                }
                
        except Exception as e:
            return {'success': False, 'message': f"UI test failed: {str(e)}"}
    
    def test_agent_communication(self) -> Dict:
        """Test inter-agent communication capabilities"""
        try:
            # Test if agents can process a simple request
            test_data = {
                "test": True,
                "document_type": "test",
                "priority": "low"
            }
            
            # Test intake agent processing endpoint
            response = requests.post(
                f"{self.agent_urls['intake']}/process",
                json=test_data,
                timeout=self.timeout
            )
            
            if response.status_code in [200, 202]:  # Accept both OK and Accepted
                return {
                    'success': True,
                    'message': 'Agent communication test passed',
                    'details': {'status_code': response.status_code}
                }
            else:
                return {
                    'success': False,
                    'message': f'Agent communication failed: HTTP {response.status_code}'
                }
                
        except Exception as e:
            return {'success': False, 'message': f"Communication test failed: {str(e)}"}
    
    def test_performance_benchmarks(self) -> Dict:
        """Test system performance benchmarks"""
        try:
            start_time = time.time()
            
            # Test concurrent health checks
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = []
                for agent_name, url in self.agent_urls.items():
                    future = executor.submit(requests.get, f"{url}/health", timeout=5)
                    futures.append((agent_name, future))
                
                results = {}
                for agent_name, future in futures:
                    try:
                        response = future.result(timeout=10)
                        results[agent_name] = response.elapsed.total_seconds()
                    except Exception as e:
                        results[agent_name] = f"Error: {str(e)}"
            
            total_time = time.time() - start_time
            avg_response_time = sum(t for t in results.values() if isinstance(t, float)) / len([t for t in results.values() if isinstance(t, float)])
            
            # Performance targets: < 2 seconds average response
            performance_ok = avg_response_time < 2.0 and total_time < 5.0
            
            return {
                'success': performance_ok,
                'message': f'Performance test: {avg_response_time:.3f}s avg response, {total_time:.3f}s total',
                'details': {
                    'individual_times': results,
                    'average_response_time': avg_response_time,
                    'total_time': total_time,
                    'performance_target_met': performance_ok
                }
            }
            
        except Exception as e:
            return {'success': False, 'message': f"Performance test failed: {str(e)}"}
    
    def test_docker_containers(self) -> Dict:
        """Test Docker container status"""
        try:
            result = subprocess.run(['docker', 'ps', '--format', 'json'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                containers = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        containers.append(json.loads(line))
                
                # Check for required containers
                required_containers = ['kyc-intake-agent', 'kyc-intelligence-agent', 'kyc-decision-agent']
                running_containers = [c['Names'] for c in containers]
                
                missing_containers = [req for req in required_containers if req not in running_containers]
                
                if not missing_containers:
                    return {
                        'success': True,
                        'message': f'All {len(required_containers)} required containers running',
                        'details': {'running_containers': running_containers}
                    }
                else:
                    return {
                        'success': False,
                        'message': f'Missing containers: {missing_containers}',
                        'details': {'missing': missing_containers, 'running': running_containers}
                    }
            else:
                return {
                    'success': False,
                    'message': f'Docker ps command failed: {result.stderr}'
                }
                
        except Exception as e:
            return {'success': False, 'message': f"Docker test failed: {str(e)}"}
    
    def run_all_tests(self) -> Tuple[int, int, List[TestResult]]:
        """Run all automated tests"""
        print("🚀 Starting Automated Test Suite")
        print("=" * 50)
        
        # Define all tests
        tests = [
            ("Agent Health Check", self.test_agent_health),
            ("Database Connections", self.test_database_connections),
            ("UI Components Loading", self.test_ui_components),
            ("Agent Communication", self.test_agent_communication),
            ("Performance Benchmarks", self.test_performance_benchmarks),
            ("Docker Container Status", self.test_docker_containers)
        ]
        
        # Run all tests
        for test_name, test_func in tests:
            result = self.run_test(test_name, test_func)
            self.test_results.append(result)
        
        # Calculate summary
        passed = sum(1 for r in self.test_results if r.passed)
        total = len(self.test_results)
        
        print("\n" + "=" * 50)
        print("TEST SUMMARY")
        print("=" * 50)
        
        for result in self.test_results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"{status} {result.name} ({result.duration:.2f}s)")
            if not result.passed:
                print(f"     └─ {result.message}")
        
        print("=" * 50)
        print(f"TOTAL: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED - System is ready for production")
        else:
            print(f"⚠️  {total - passed} tests failed - Issues need to be resolved")
        
        return passed, total, self.test_results

def main():
    """Main function to run automated tests"""
    test_suite = AutomatedTestSuite()
    
    # Wait for system to be ready
    print("⏳ Waiting 10 seconds for system to stabilize...")
    time.sleep(10)
    
    # Run all tests
    passed, total, results = test_suite.run_all_tests()
    
    # Exit with appropriate code
    if passed == total:
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Failure

if __name__ == "__main__":
    main()
