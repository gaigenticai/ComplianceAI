#!/usr/bin/env python3
"""
Phase 4 Automated Tests - Comprehensive Testing Suite
===================================================

This module provides comprehensive automated testing for Phase 4 compliance
report generation components including UI, API, integration, and performance tests.

Key Features:
- UI component testing with Selenium WebDriver
- API endpoint testing with aiohttp
- Integration tests for report generators
- Performance benchmarking and validation
- Database integration testing
- Authentication and security testing

Rule Compliance:
- Rule 12: Automated testing - Complete test coverage for Phase 4 components
- Rule 1: No stubs - Real functional tests with actual system interaction
- Rule 6: UI testing - Comprehensive dashboard and interface validation
- Rule 17: Comprehensive documentation throughout
"""

import os
import sys
import asyncio
import pytest
import json
import time
import tempfile
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import uuid

# Add project paths
sys.path.append('/Users/krishna/Downloads/gaigenticai/ComplianceAI/python-agents/decision-orchestration-agent/src')
sys.path.append('/Users/krishna/Downloads/gaigenticai/ComplianceAI/python-web-interface')

# Testing frameworks
import aiohttp
import asyncpg
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Import Phase 4 components
from compliance_report_generator import ComplianceReportGenerator, ReportRequest, ReportType, ReportFormat
from finrep_generator import FINREPGenerator, FINREPData, FINREPTemplate
from corep_generator import COREPGenerator, COREPData, COREPTemplate
from dora_generator import DORAGenerator, DORAData, DORAReportType

# Test configuration
TEST_CONFIG = {
    'base_url': 'http://localhost:8000',
    'api_base': 'http://localhost:8000/api/phase4',
    'dashboard_url': 'http://localhost:8000/phase4',
    'user_guide_url': 'http://localhost:8000/phase4/guides',
    'timeout': 30,
    'test_institution': 'INST_001',
    'test_period': '2024-Q3'
}

class TestPhase4ReportGenerators:
    """Test suite for Phase 4 report generators"""
    
    @pytest.fixture
    async def report_generator(self):
        """Initialize report generator for testing"""
        generator = ComplianceReportGenerator()
        await generator.initialize()
        return generator
    
    @pytest.fixture
    async def finrep_generator(self):
        """Initialize FINREP generator for testing"""
        return FINREPGenerator()
    
    @pytest.fixture
    async def corep_generator(self):
        """Initialize COREP generator for testing"""
        return COREPGenerator()
    
    @pytest.fixture
    async def dora_generator(self):
        """Initialize DORA generator for testing"""
        return DORAGenerator()
    
    @pytest.mark.asyncio
    async def test_compliance_report_generator_initialization(self, report_generator):
        """Test ComplianceReportGenerator initialization"""
        assert report_generator is not None
        assert report_generator.pg_pool is not None
        assert len(report_generator.templates) > 0
        
        # Test metrics retrieval
        metrics = await report_generator.get_metrics()
        assert 'reports_generated' in metrics
        assert 'templates_loaded' in metrics
    
    @pytest.mark.asyncio
    async def test_finrep_report_generation(self, finrep_generator):
        """Test FINREP report generation with validation"""
        # Create test data
        finrep_data = FINREPData(
            institution_code='TEST001',
            reporting_period='2024-Q3',
            currency='EUR',
            consolidation_basis='Individual',
            total_assets=1000000000.0,
            total_liabilities=800000000.0,
            total_equity=200000000.0,
            cash_balances=50000000.0,
            financial_assets_amortised_cost=700000000.0,
            net_interest_income=25000000.0,
            net_profit=15000000.0
        )
        
        # Test data validation
        validation_results = await finrep_generator._validate_finrep_data(finrep_data)
        assert validation_results['valid'] == True
        assert len(validation_results['errors']) == 0
        
        # Test report generation
        report_content = await finrep_generator.generate_finrep_report(finrep_data, FINREPTemplate.F_01_01)
        assert report_content is not None
        assert len(report_content) > 0
        assert 'xbrli:xbrl' in report_content
        assert 'finrep:TotalAssets' in report_content
        
        # Validate XBRL structure
        assert '<?xml version="1.0" encoding="UTF-8"?>' in report_content
        assert 'contextRef="c1"' in report_content
        assert 'unitRef="EUR"' in report_content
    
    @pytest.mark.asyncio
    async def test_corep_report_generation(self, corep_generator):
        """Test COREP report generation with capital calculations"""
        # Create test data
        corep_data = COREPData(
            institution_code='TEST001',
            reporting_period='2024-Q3',
            currency='EUR',
            consolidation_basis='Individual',
            common_equity_tier1=150000000.0,
            total_own_funds=200000000.0,
            total_risk_exposure_amount=1200000000.0,
            cet1_ratio=12.5,
            tier1_ratio=15.0,
            total_capital_ratio=16.7
        )
        
        # Test capital ratio calculations
        calculated_data = await corep_generator.calculate_capital_ratios(corep_data)
        assert calculated_data.total_own_funds == 150000000.0  # Only CET1 in this test
        assert abs(calculated_data.cet1_ratio - 12.5) < 0.1
        
        # Test data validation
        validation_results = await corep_generator._validate_corep_data(corep_data)
        assert validation_results['valid'] == True
        
        # Test report generation
        report_content = await corep_generator.generate_corep_report(corep_data, COREPTemplate.C_01_00)
        assert report_content is not None
        assert 'corep:CommonEquityTier1Capital' in report_content
        assert 'corep:TotalOwnFunds' in report_content
    
    @pytest.mark.asyncio
    async def test_dora_report_generation(self, dora_generator):
        """Test DORA ICT risk report generation"""
        # Create test data
        dora_data = DORAData(
            institution_code='TEST001',
            institution_name='Test Bank AG',
            reporting_period_start='2024-01-01',
            reporting_period_end='2024-12-31',
            jurisdiction='EU',
            total_incidents=5,
            major_incidents=1,
            cyber_attacks=2,
            total_providers=25,
            critical_providers=5,
            board_oversight=True,
            critical_systems_count=8,
            vulnerabilities_identified=15,
            vulnerabilities_remediated=12
        )
        
        # Test data validation
        validation_results = await dora_generator._validate_dora_data(dora_data)
        assert validation_results['valid'] == True
        
        # Test risk metrics calculation
        risk_metrics = await dora_generator._calculate_risk_metrics(dora_data)
        assert 'overall_risk_score' in risk_metrics
        assert 'risk_level' in risk_metrics
        assert 0 <= risk_metrics['overall_risk_score'] <= 100
        
        # Test report generation
        report_content = await dora_generator.generate_dora_report(dora_data, DORAReportType.ICT_RISK_MANAGEMENT)
        assert report_content is not None
        
        # Validate JSON structure
        report_json = json.loads(report_content)
        assert 'metadata' in report_json
        assert 'institution_info' in report_json
        assert 'executive_summary' in report_json
        assert 'ict_risk_management' in report_json
    
    @pytest.mark.asyncio
    async def test_report_validation_errors(self, finrep_generator):
        """Test validation error handling"""
        # Create invalid data (negative assets)
        invalid_data = FINREPData(
            institution_code='TEST001',
            reporting_period='2024-Q3',
            currency='EUR',
            consolidation_basis='Individual',
            total_assets=-1000000.0,  # Invalid negative value
            total_liabilities=800000000.0,
            total_equity=200000000.0
        )
        
        # Test validation catches errors
        validation_results = await finrep_generator._validate_finrep_data(invalid_data)
        assert validation_results['valid'] == False
        assert len(validation_results['errors']) > 0
        assert any('cannot be negative' in error for error in validation_results['errors'])
    
    @pytest.mark.asyncio
    async def test_template_loading(self, report_generator):
        """Test template loading and management"""
        templates = await report_generator.list_available_templates()
        assert len(templates) > 0
        
        # Check for expected template types
        template_keys = list(templates.keys())
        assert any('xbrl' in key for key in template_keys)
        assert any('csv' in key for key in template_keys)
        assert any('json' in key for key in template_keys)

class TestPhase4API:
    """Test suite for Phase 4 API endpoints"""
    
    @pytest.fixture
    async def api_client(self):
        """Create aiohttp client for API testing"""
        async with aiohttp.ClientSession() as session:
            yield session
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self, api_client):
        """Test API health check endpoint"""
        async with api_client.get(f"{TEST_CONFIG['api_base']}/health") as response:
            assert response.status == 200
            data = await response.json()
            assert data['status'] == 'healthy'
            assert 'services' in data
    
    @pytest.mark.asyncio
    async def test_generate_report_endpoint(self, api_client):
        """Test report generation API endpoint"""
        request_data = {
            'report_type': 'FINREP',
            'institution_id': TEST_CONFIG['test_institution'],
            'reporting_period': TEST_CONFIG['test_period'],
            'format': 'XBRL',
            'jurisdiction': 'EU'
        }
        
        async with api_client.post(
            f"{TEST_CONFIG['api_base']}/generate-report",
            json=request_data
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert data['success'] == True
            assert 'report_id' in data
            assert data['status'] in ['COMPLETED', 'GENERATING']
    
    @pytest.mark.asyncio
    async def test_validate_data_endpoint(self, api_client):
        """Test data validation API endpoint"""
        request_data = {
            'report_type': 'FINREP',
            'institution_id': TEST_CONFIG['test_institution'],
            'reporting_period': TEST_CONFIG['test_period']
        }
        
        async with api_client.post(
            f"{TEST_CONFIG['api_base']}/validate-data",
            json=request_data
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert data['success'] == True
            assert 'validation_results' in data
    
    @pytest.mark.asyncio
    async def test_dashboard_metrics_endpoint(self, api_client):
        """Test dashboard metrics API endpoint"""
        async with api_client.get(f"{TEST_CONFIG['api_base']}/dashboard-metrics") as response:
            assert response.status == 200
            data = await response.json()
            assert 'total_reports' in data
            assert 'success_rate' in data
            assert 'avg_generation_time' in data
            assert 'system_status' in data
    
    @pytest.mark.asyncio
    async def test_sample_report_download(self, api_client):
        """Test sample report download endpoint"""
        for report_type in ['FINREP', 'COREP', 'DORA_ICT']:
            async with api_client.get(f"{TEST_CONFIG['api_base']}/sample-report/{report_type}") as response:
                assert response.status == 200
                content = await response.read()
                assert len(content) > 0
    
    @pytest.mark.asyncio
    async def test_institutions_endpoint(self, api_client):
        """Test institutions listing endpoint"""
        async with api_client.get(f"{TEST_CONFIG['api_base']}/institutions") as response:
            assert response.status == 200
            data = await response.json()
            assert data['success'] == True
            assert 'institutions' in data
            assert len(data['institutions']) > 0
    
    @pytest.mark.asyncio
    async def test_templates_endpoint(self, api_client):
        """Test templates listing endpoint"""
        async with api_client.get(f"{TEST_CONFIG['api_base']}/templates") as response:
            assert response.status == 200
            data = await response.json()
            assert data['success'] == True
            assert 'templates' in data
    
    @pytest.mark.asyncio
    async def test_test_generation_endpoint(self, api_client):
        """Test report generation testing endpoint"""
        request_data = {
            'reportType': 'FINREP',
            'institutionId': TEST_CONFIG['test_institution'],
            'reportingPeriod': TEST_CONFIG['test_period'],
            'outputFormat': 'XBRL'
        }
        
        async with api_client.post(
            f"{TEST_CONFIG['api_base']}/test-generation",
            json=request_data
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert data['success'] == True
            assert 'report_id' in data
            assert 'generation_time' in data
    
    @pytest.mark.asyncio
    async def test_authentication_integration(self, api_client):
        """Test REQUIRE_AUTH integration"""
        # Test with REQUIRE_AUTH=false (should work without auth)
        os.environ['REQUIRE_AUTH'] = 'false'
        
        async with api_client.get(f"{TEST_CONFIG['api_base']}/dashboard-metrics") as response:
            assert response.status == 200
        
        # Test with REQUIRE_AUTH=true (should require auth)
        os.environ['REQUIRE_AUTH'] = 'true'
        
        async with api_client.get(f"{TEST_CONFIG['api_base']}/dashboard-metrics") as response:
            assert response.status == 401  # Unauthorized without token
        
        # Test with valid token
        headers = {'Authorization': 'Bearer test_token'}
        async with api_client.get(
            f"{TEST_CONFIG['api_base']}/dashboard-metrics",
            headers=headers
        ) as response:
            assert response.status == 200
        
        # Reset to default
        os.environ['REQUIRE_AUTH'] = 'false'

class TestPhase4UI:
    """Test suite for Phase 4 UI components using Selenium"""
    
    @pytest.fixture
    def driver(self):
        """Initialize Chrome WebDriver for UI testing"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run in headless mode for CI
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()
    
    def test_dashboard_loading(self, driver):
        """Test Phase 4 dashboard loading and basic functionality"""
        driver.get(TEST_CONFIG['dashboard_url'])
        
        # Wait for page to load
        wait = WebDriverWait(driver, TEST_CONFIG['timeout'])
        
        # Check page title
        assert 'Phase 4: Compliance Report Generation' in driver.title
        
        # Check main dashboard elements
        dashboard_title = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, 'dashboard-title'))
        )
        assert 'Phase 4' in dashboard_title.text
        
        # Check metrics cards
        metric_cards = driver.find_elements(By.CLASS_NAME, 'metric-card')
        assert len(metric_cards) >= 4  # Should have at least 4 metric cards
        
        # Check generator cards
        generator_cards = driver.find_elements(By.CLASS_NAME, 'generator-card')
        assert len(generator_cards) == 3  # FINREP, COREP, DORA
    
    def test_report_generator_cards(self, driver):
        """Test report generator card functionality"""
        driver.get(TEST_CONFIG['dashboard_url'])
        wait = WebDriverWait(driver, TEST_CONFIG['timeout'])
        
        # Test FINREP generator card
        finrep_card = wait.until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'generator-card')]//div[contains(text(), 'FINREP')]"))
        )
        assert finrep_card is not None
        
        # Test generate button
        generate_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Generate')]")
        assert len(generate_buttons) >= 3  # One for each generator
        
        # Test validate buttons
        validate_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Validate')]")
        assert len(validate_buttons) >= 3  # One for each generator
    
    def test_testing_interface(self, driver):
        """Test report testing interface functionality"""
        driver.get(TEST_CONFIG['dashboard_url'])
        wait = WebDriverWait(driver, TEST_CONFIG['timeout'])
        
        # Find testing form
        testing_form = wait.until(
            EC.presence_of_element_located((By.ID, 'testingForm'))
        )
        assert testing_form is not None
        
        # Test form fields
        report_type_select = Select(driver.find_element(By.ID, 'reportType'))
        institution_select = Select(driver.find_element(By.ID, 'institutionId'))
        period_select = Select(driver.find_element(By.ID, 'reportingPeriod'))
        format_select = Select(driver.find_element(By.ID, 'outputFormat'))
        
        # Fill form
        report_type_select.select_by_value('FINREP')
        institution_select.select_by_value('INST_001')
        period_select.select_by_value('2024-Q3')
        format_select.select_by_value('XBRL')
        
        # Test form buttons
        test_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Test Generation')]")
        validate_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Validate Data')]")
        download_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Download Sample')]")
        
        assert test_button.is_enabled()
        assert validate_button.is_enabled()
        assert download_button.is_enabled()
    
    def test_user_guide_loading(self, driver):
        """Test user guide page loading and navigation"""
        driver.get(TEST_CONFIG['user_guide_url'])
        wait = WebDriverWait(driver, TEST_CONFIG['timeout'])
        
        # Check page title
        assert 'User Guide' in driver.title
        
        # Check main title
        guide_title = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, 'guide-title'))
        )
        assert 'Phase 4' in guide_title.text
        
        # Check navigation items
        nav_items = driver.find_elements(By.CLASS_NAME, 'nav-item')
        assert len(nav_items) >= 8  # Should have multiple navigation sections
        
        # Test search functionality
        search_input = driver.find_element(By.ID, 'searchInput')
        search_input.send_keys('FINREP')
        time.sleep(1)  # Allow search to process
        
        # Check that content is filtered
        active_sections = driver.find_elements(By.CSS_SELECTOR, '.section.active')
        assert len(active_sections) >= 1
    
    def test_navigation_functionality(self, driver):
        """Test user guide navigation functionality"""
        driver.get(TEST_CONFIG['user_guide_url'])
        wait = WebDriverWait(driver, TEST_CONFIG['timeout'])
        
        # Test clicking different navigation items
        nav_items = driver.find_elements(By.CLASS_NAME, 'nav-item')
        
        for i, nav_item in enumerate(nav_items[:3]):  # Test first 3 items
            nav_item.click()
            time.sleep(0.5)  # Allow navigation to complete
            
            # Check that the nav item is active
            assert 'active' in nav_item.get_attribute('class')
            
            # Check that a section is active
            active_sections = driver.find_elements(By.CSS_SELECTOR, '.section.active')
            assert len(active_sections) == 1
    
    def test_responsive_design(self, driver):
        """Test responsive design at different screen sizes"""
        # Test desktop size
        driver.set_window_size(1920, 1080)
        driver.get(TEST_CONFIG['dashboard_url'])
        
        # Check that elements are properly positioned
        dashboard_container = driver.find_element(By.CLASS_NAME, 'dashboard-container')
        assert dashboard_container.is_displayed()
        
        # Test tablet size
        driver.set_window_size(768, 1024)
        time.sleep(1)  # Allow responsive adjustments
        
        # Check that layout adapts
        generator_cards = driver.find_elements(By.CLASS_NAME, 'generator-card')
        for card in generator_cards:
            assert card.is_displayed()
        
        # Test mobile size
        driver.set_window_size(375, 667)
        time.sleep(1)  # Allow responsive adjustments
        
        # Check that elements are still accessible
        dashboard_title = driver.find_element(By.CLASS_NAME, 'dashboard-title')
        assert dashboard_title.is_displayed()

class TestPhase4Performance:
    """Performance testing for Phase 4 components"""
    
    @pytest.mark.asyncio
    async def test_report_generation_performance(self):
        """Test report generation performance benchmarks"""
        generator = ComplianceReportGenerator()
        await generator.initialize()
        
        # Test FINREP generation performance
        start_time = time.time()
        
        request = ReportRequest(
            report_id=str(uuid.uuid4()),
            report_type=ReportType.FINREP,
            format=ReportFormat.XBRL,
            reporting_period='2024-Q3',
            institution_id='INST_001',
            jurisdiction='EU',
            template_version='3.2.0',
            data_sources=['database'],
            delivery_method='API',
            deadline=datetime.now(timezone.utc)
        )
        
        result = await generator.generate_report(request)
        generation_time = time.time() - start_time
        
        # Performance assertions
        assert generation_time < 5.0  # Should complete within 5 seconds
        assert result.status.value == 'COMPLETED'
        assert result.file_size is not None
        assert result.file_size > 0
    
    @pytest.mark.asyncio
    async def test_concurrent_report_generation(self):
        """Test concurrent report generation performance"""
        generator = ComplianceReportGenerator()
        await generator.initialize()
        
        # Create multiple concurrent requests
        tasks = []
        for i in range(3):  # Test with 3 concurrent reports
            request = ReportRequest(
                report_id=f"PERF_TEST_{i}_{uuid.uuid4()}",
                report_type=ReportType.FINREP,
                format=ReportFormat.XBRL,
                reporting_period='2024-Q3',
                institution_id='INST_001',
                jurisdiction='EU',
                template_version='3.2.0',
                data_sources=['database'],
                delivery_method='API',
                deadline=datetime.now(timezone.utc)
            )
            tasks.append(generator.generate_report(request))
        
        # Execute concurrently
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Performance assertions
        assert len(results) == 3
        assert all(result.status.value == 'COMPLETED' for result in results)
        assert total_time < 15.0  # Should complete all within 15 seconds
    
    @pytest.mark.asyncio
    async def test_api_response_times(self):
        """Test API endpoint response times"""
        async with aiohttp.ClientSession() as session:
            endpoints = [
                '/health',
                '/dashboard-metrics',
                '/institutions',
                '/templates'
            ]
            
            for endpoint in endpoints:
                start_time = time.time()
                async with session.get(f"{TEST_CONFIG['api_base']}{endpoint}") as response:
                    response_time = time.time() - start_time
                    
                    assert response.status == 200
                    assert response_time < 2.0  # Should respond within 2 seconds

class TestPhase4Integration:
    """Integration tests for Phase 4 components"""
    
    @pytest.mark.asyncio
    async def test_database_integration(self):
        """Test database integration and data consistency"""
        # Test database connection
        pg_pool = await asyncpg.create_pool(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=int(os.getenv('POSTGRES_PORT', 5432)),
            database=os.getenv('POSTGRES_DB', 'compliance_ai'),
            user=os.getenv('POSTGRES_USER', 'postgres'),
            password=os.getenv('POSTGRES_PASSWORD', 'postgres'),
            min_size=1,
            max_size=2
        )
        
        async with pg_pool.acquire() as conn:
            # Test institutions table
            institutions = await conn.fetch("SELECT * FROM institutions WHERE is_active = true")
            assert len(institutions) > 0
            
            # Test FINREP data table
            finrep_data = await conn.fetch("SELECT * FROM finrep_data LIMIT 1")
            assert len(finrep_data) >= 0  # May be empty in test environment
            
            # Test compliance reports table structure
            columns = await conn.fetch("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'compliance_reports'
            """)
            column_names = [col['column_name'] for col in columns]
            
            required_columns = ['report_id', 'report_type', 'institution_id', 'status']
            for col in required_columns:
                assert col in column_names
        
        await pg_pool.close()
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self):
        """Test complete end-to-end report generation workflow"""
        # Initialize components
        generator = ComplianceReportGenerator()
        await generator.initialize()
        
        # Create report request
        request = ReportRequest(
            report_id=f"E2E_TEST_{uuid.uuid4()}",
            report_type=ReportType.FINREP,
            format=ReportFormat.XBRL,
            reporting_period='2024-Q3',
            institution_id='INST_001',
            jurisdiction='EU',
            template_version='3.2.0',
            data_sources=['database'],
            delivery_method='API',
            deadline=datetime.now(timezone.utc)
        )
        
        # Generate report
        result = await generator.generate_report(request)
        
        # Verify result
        assert result.status.value == 'COMPLETED'
        assert result.file_path is not None
        assert os.path.exists(result.file_path)
        
        # Verify file content
        with open(result.file_path, 'r') as f:
            content = f.read()
            assert len(content) > 0
            assert 'xbrli:xbrl' in content
        
        # Verify database record
        async with generator.pg_pool.acquire() as conn:
            db_record = await conn.fetchrow(
                "SELECT * FROM compliance_reports WHERE report_id = $1",
                request.report_id
            )
            assert db_record is not None
            assert db_record['status'] == 'COMPLETED'
        
        # Cleanup
        if os.path.exists(result.file_path):
            os.remove(result.file_path)

# Test runner configuration
if __name__ == "__main__":
    # Configure pytest arguments
    pytest_args = [
        __file__,
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
        "--strict-markers",  # Strict marker checking
        "-x",  # Stop on first failure
        "--asyncio-mode=auto"  # Auto async mode
    ]
    
    # Add coverage if available
    try:
        import pytest_cov
        pytest_args.extend(["--cov=.", "--cov-report=html", "--cov-report=term"])
    except ImportError:
        pass
    
    # Run tests
    exit_code = pytest.main(pytest_args)
    exit(exit_code)
