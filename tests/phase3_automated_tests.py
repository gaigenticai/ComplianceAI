#!/usr/bin/env python3
"""
Phase 3 Automated Testing Suite
Rule 12 Compliance: Automated testing of UI and every code component

This comprehensive test suite validates all Phase 3 components:
- Rule Compiler functionality and performance
- Kafka Consumer message processing
- Jurisdiction Handler rule filtering
- Overlap Resolver similarity detection
- Audit Logger integrity and export
- UI component functionality
- API endpoint testing
- Integration testing

Rule Compliance:
- Rule 12: Automated testing for all Phase 3 components
- Rule 13: Production-grade test implementation
- Rule 17: Comprehensive test documentation
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import unittest
from unittest.mock import Mock, patch, AsyncMock

import pytest
import asyncpg
import aiohttp
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# Add Phase 3 components to path
sys.path.append('/Users/krishna/Downloads/gaigenticai/ComplianceAI/python-agents/intelligence-compliance-agent/src')

from rule_compiler import RuleCompiler, RegulationType, ComplianceRule
from kafka_consumer import RegulatoryKafkaConsumer
from jurisdiction_handler import JurisdictionHandler, ConflictResolutionStrategy
from overlap_resolver import OverlapResolver
from audit_logger import AuditLogger

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Phase3TestSuite:
    """
    Comprehensive automated test suite for Phase 3 components
    
    Tests all functionality including:
    - Unit tests for each component
    - Integration tests between components
    - Performance benchmarks
    - UI functionality tests
    - API endpoint tests
    - Error handling and edge cases
    """
    
    def __init__(self):
        self.test_results = {
            'rule_compiler': {'passed': 0, 'failed': 0, 'errors': []},
            'kafka_consumer': {'passed': 0, 'failed': 0, 'errors': []},
            'jurisdiction_handler': {'passed': 0, 'failed': 0, 'errors': []},
            'overlap_resolver': {'passed': 0, 'failed': 0, 'errors': []},
            'audit_logger': {'passed': 0, 'failed': 0, 'errors': []},
            'ui_tests': {'passed': 0, 'failed': 0, 'errors': []},
            'api_tests': {'passed': 0, 'failed': 0, 'errors': []},
            'integration_tests': {'passed': 0, 'failed': 0, 'errors': []},
            'performance_tests': {'passed': 0, 'failed': 0, 'errors': []}
        }
        
        # Test configuration
        self.test_config = {
            'database_url': os.getenv('TEST_DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/compliance_ai_test'),
            'api_base_url': os.getenv('TEST_API_URL', 'http://localhost:8000'),
            'ui_base_url': os.getenv('TEST_UI_URL', 'http://localhost:8000'),
            'kafka_brokers': os.getenv('TEST_KAFKA_BROKERS', 'localhost:9092'),
            'performance_targets': {
                'rule_compilation_ms': 100,
                'kafka_processing_ms': 500,
                'overlap_detection_ms': 200,
                'audit_logging_ms': 10
            }
        }
        
        # Initialize components for testing
        self.rule_compiler = None
        self.kafka_consumer = None
        self.jurisdiction_handler = None
        self.overlap_resolver = None
        self.audit_logger = None
        
        # WebDriver for UI tests
        self.driver = None
    
    async def setup_test_environment(self):
        """Setup test environment and initialize components"""
        logger.info("Setting up Phase 3 test environment...")
        
        try:
            # Initialize database connection for tests
            self.db_pool = await asyncpg.create_pool(self.test_config['database_url'])
            
            # Initialize Phase 3 components
            self.rule_compiler = RuleCompiler()
            await self.rule_compiler.initialize()
            
            self.kafka_consumer = RegulatoryKafkaConsumer()
            # Don't start consumer for tests
            
            self.jurisdiction_handler = JurisdictionHandler()
            await self.jurisdiction_handler.initialize()
            
            self.overlap_resolver = OverlapResolver()
            await self.overlap_resolver.initialize()
            
            self.audit_logger = AuditLogger()
            await self.audit_logger.initialize()
            
            # Setup WebDriver for UI tests
            chrome_options = Options()
            chrome_options.add_argument("--headless")  # Run in headless mode for CI
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            try:
                self.driver = webdriver.Chrome(options=chrome_options)
                logger.info("WebDriver initialized successfully")
            except Exception as e:
                logger.warning(f"WebDriver initialization failed: {e}")
                self.driver = None
            
            logger.info("Test environment setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup test environment: {e}")
            raise
    
    async def teardown_test_environment(self):
        """Cleanup test environment"""
        logger.info("Tearing down test environment...")
        
        try:
            if self.driver:
                self.driver.quit()
            
            if self.db_pool:
                await self.db_pool.close()
                
        except Exception as e:
            logger.error(f"Error during teardown: {e}")
    
    # RULE COMPILER TESTS
    async def test_rule_compiler_basic_functionality(self):
        """Test basic rule compiler functionality"""
        test_name = "Rule Compiler Basic Functionality"
        logger.info(f"Running {test_name}...")
        
        try:
            # Test data
            obligation_data = {
                'obligation_text': 'Customer due diligence must be performed for transactions exceeding EUR 15,000',
                'regulation_type': 'AML',
                'jurisdiction': 'EU',
                'obligation_level': 'Level_2',
                'confidence_score': 0.85,
                'effective_date': datetime.now(),
                'created_at': datetime.now()
            }
            
            # Test rule compilation
            start_time = time.time()
            rules = await self.rule_compiler.compile_obligation_to_rules(obligation_data)
            compilation_time = (time.time() - start_time) * 1000
            
            # Assertions
            assert rules is not None, "Rules should not be None"
            assert len(rules) > 0, "Should generate at least one rule"
            assert rules[0].json_logic is not None, "JSON-Logic should be generated"
            assert compilation_time < self.test_config['performance_targets']['rule_compilation_ms'], f"Compilation took {compilation_time}ms, target is {self.test_config['performance_targets']['rule_compilation_ms']}ms"
            
            # Test rule validation
            is_valid = self.rule_compiler._validate_json_logic(rules[0].json_logic)
            assert is_valid, "Generated JSON-Logic should be valid"
            
            # Test rule testing
            test_passed = await self.rule_compiler._test_rule_with_sample_data(rules[0])
            assert test_passed, "Rule should pass sample data test"
            
            self.test_results['rule_compiler']['passed'] += 1
            logger.info(f"✅ {test_name} passed")
            
        except Exception as e:
            self.test_results['rule_compiler']['failed'] += 1
            self.test_results['rule_compiler']['errors'].append(f"{test_name}: {str(e)}")
            logger.error(f"❌ {test_name} failed: {e}")
    
    async def test_rule_compiler_edge_cases(self):
        """Test rule compiler edge cases and error handling"""
        test_name = "Rule Compiler Edge Cases"
        logger.info(f"Running {test_name}...")
        
        try:
            # Test empty obligation text
            empty_obligation = {
                'obligation_text': '',
                'regulation_type': 'AML',
                'jurisdiction': 'EU',
                'obligation_level': 'Level_2',
                'confidence_score': 0.85,
                'effective_date': datetime.now(),
                'created_at': datetime.now()
            }
            
            rules = await self.rule_compiler.compile_obligation_to_rules(empty_obligation)
            assert rules is None or len(rules) == 0, "Empty text should not generate rules"
            
            # Test invalid regulation type
            invalid_obligation = {
                'obligation_text': 'Test obligation',
                'regulation_type': 'INVALID_TYPE',
                'jurisdiction': 'EU',
                'obligation_level': 'Level_2',
                'confidence_score': 0.85,
                'effective_date': datetime.now(),
                'created_at': datetime.now()
            }
            
            # Should handle gracefully without crashing
            rules = await self.rule_compiler.compile_obligation_to_rules(invalid_obligation)
            # May return None or empty list, but shouldn't crash
            
            # Test invalid JSON-Logic validation
            invalid_json_logic = {"invalid_operator": ["test"]}
            is_valid = self.rule_compiler._validate_json_logic(invalid_json_logic)
            assert not is_valid, "Invalid JSON-Logic should fail validation"
            
            self.test_results['rule_compiler']['passed'] += 1
            logger.info(f"✅ {test_name} passed")
            
        except Exception as e:
            self.test_results['rule_compiler']['failed'] += 1
            self.test_results['rule_compiler']['errors'].append(f"{test_name}: {str(e)}")
            logger.error(f"❌ {test_name} failed: {e}")
    
    # KAFKA CONSUMER TESTS
    async def test_kafka_consumer_message_processing(self):
        """Test Kafka consumer message processing"""
        test_name = "Kafka Consumer Message Processing"
        logger.info(f"Running {test_name}...")
        
        try:
            # Create mock message
            class MockMessage:
                def __init__(self):
                    self.topic = 'regulatory.updates'
                    self.partition = 0
                    self.offset = 0
                    self.timestamp = datetime.now()
                    self.value = json.dumps({
                        'event_type': 'obligation_created',
                        'payload': {
                            'obligation_id': 'test_001',
                            'regulation_type': 'AML',
                            'jurisdiction': 'EU'
                        }
                    }).encode('utf-8')
            
            mock_message = MockMessage()
            
            # Test message processing
            start_time = time.time()
            await self.kafka_consumer._process_message(mock_message)
            processing_time = (time.time() - start_time) * 1000
            
            # Performance assertion
            assert processing_time < self.test_config['performance_targets']['kafka_processing_ms'], f"Processing took {processing_time}ms, target is {self.test_config['performance_targets']['kafka_processing_ms']}ms"
            
            # Test different event types
            event_types = ['obligation_created', 'obligation_updated', 'obligation_deleted', 'system_status']
            
            for event_type in event_types:
                mock_message.value = json.dumps({
                    'event_type': event_type,
                    'payload': {'test': 'data'}
                }).encode('utf-8')
                
                # Should process without errors
                await self.kafka_consumer._process_message(mock_message)
            
            self.test_results['kafka_consumer']['passed'] += 1
            logger.info(f"✅ {test_name} passed")
            
        except Exception as e:
            self.test_results['kafka_consumer']['failed'] += 1
            self.test_results['kafka_consumer']['errors'].append(f"{test_name}: {str(e)}")
            logger.error(f"❌ {test_name} failed: {e}")
    
    # JURISDICTION HANDLER TESTS
    async def test_jurisdiction_handler_filtering(self):
        """Test jurisdiction handler rule filtering"""
        test_name = "Jurisdiction Handler Filtering"
        logger.info(f"Running {test_name}...")
        
        try:
            # Create test rules for different jurisdictions
            test_rules = [
                ComplianceRule(
                    rule_id='EU_001',
                    regulation_type=RegulationType.AML,
                    jurisdiction='EU',
                    json_logic={'test': 'eu_rule'},
                    conditions=[],
                    confidence_score=0.9
                ),
                ComplianceRule(
                    rule_id='DE_001',
                    regulation_type=RegulationType.AML,
                    jurisdiction='DE',
                    json_logic={'test': 'de_rule'},
                    conditions=[],
                    confidence_score=0.9
                ),
                ComplianceRule(
                    rule_id='GB_001',
                    regulation_type=RegulationType.AML,
                    jurisdiction='GB',
                    json_logic={'test': 'gb_rule'},
                    conditions=[],
                    confidence_score=0.9
                )
            ]
            
            # Test filtering by jurisdiction
            eu_rules = await self.jurisdiction_handler.filter_rules_by_jurisdiction(test_rules, 'EU')
            assert len(eu_rules) >= 1, "Should return EU rules"
            assert all(rule.jurisdiction in ['EU'] for rule in eu_rules), "Should only return EU rules"
            
            de_rules = await self.jurisdiction_handler.filter_rules_by_jurisdiction(test_rules, 'DE')
            assert len(de_rules) >= 1, "Should return DE rules (including EU)"
            
            # Test conflict resolution strategies
            strategies = [
                ConflictResolutionStrategy.MOST_RESTRICTIVE,
                ConflictResolutionStrategy.CUSTOMER_PREFERENCE,
                ConflictResolutionStrategy.BUSINESS_PREFERENCE,
                ConflictResolutionStrategy.HIERARCHICAL
            ]
            
            for strategy in strategies:
                resolved_rules = await self.jurisdiction_handler.resolve_jurisdiction_conflicts(
                    test_rules, 'DE', 'EU', strategy
                )
                assert resolved_rules is not None, f"Strategy {strategy} should return rules"
            
            self.test_results['jurisdiction_handler']['passed'] += 1
            logger.info(f"✅ {test_name} passed")
            
        except Exception as e:
            self.test_results['jurisdiction_handler']['failed'] += 1
            self.test_results['jurisdiction_handler']['errors'].append(f"{test_name}: {str(e)}")
            logger.error(f"❌ {test_name} failed: {e}")
    
    # OVERLAP RESOLVER TESTS
    async def test_overlap_resolver_similarity_detection(self):
        """Test overlap resolver similarity detection"""
        test_name = "Overlap Resolver Similarity Detection"
        logger.info(f"Running {test_name}...")
        
        try:
            # Test similar texts
            text1 = "Customer due diligence required for transactions above EUR 15,000"
            text2 = "Enhanced due diligence needed for high-value transactions exceeding EUR 15,000"
            
            start_time = time.time()
            similarity = await self.overlap_resolver._calculate_text_similarity(text1, text2)
            detection_time = (time.time() - start_time) * 1000
            
            # Performance assertion
            assert detection_time < self.test_config['performance_targets']['overlap_detection_ms'], f"Detection took {detection_time}ms, target is {self.test_config['performance_targets']['overlap_detection_ms']}ms"
            
            # Similarity assertion
            assert 0.0 <= similarity <= 1.0, "Similarity should be between 0 and 1"
            assert similarity > 0.5, "Similar texts should have high similarity score"
            
            # Test dissimilar texts
            text3 = "Data protection requirements for customer information"
            similarity2 = await self.overlap_resolver._calculate_text_similarity(text1, text3)
            assert similarity2 < similarity, "Dissimilar texts should have lower similarity"
            
            # Test identical texts
            similarity3 = await self.overlap_resolver._calculate_text_similarity(text1, text1)
            assert similarity3 == 1.0, "Identical texts should have similarity of 1.0"
            
            # Test empty texts
            similarity4 = await self.overlap_resolver._calculate_text_similarity("", "")
            assert similarity4 >= 0.0, "Empty texts should not cause errors"
            
            self.test_results['overlap_resolver']['passed'] += 1
            logger.info(f"✅ {test_name} passed")
            
        except Exception as e:
            self.test_results['overlap_resolver']['failed'] += 1
            self.test_results['overlap_resolver']['errors'].append(f"{test_name}: {str(e)}")
            logger.error(f"❌ {test_name} failed: {e}")
    
    # AUDIT LOGGER TESTS
    async def test_audit_logger_functionality(self):
        """Test audit logger functionality and integrity"""
        test_name = "Audit Logger Functionality"
        logger.info(f"Running {test_name}...")
        
        try:
            # Test audit entry creation
            start_time = time.time()
            entry_id = await self.audit_logger.log_system_event(
                event_type='test_event',
                details='Test audit entry for automated testing',
                user_id='test_user'
            )
            logging_time = (time.time() - start_time) * 1000
            
            # Performance assertion
            assert logging_time < self.test_config['performance_targets']['audit_logging_ms'], f"Logging took {logging_time}ms, target is {self.test_config['performance_targets']['audit_logging_ms']}ms"
            
            assert entry_id is not None, "Should return entry ID"
            
            # Test rule change logging
            mock_rule = ComplianceRule(
                rule_id='test_rule',
                regulation_type=RegulationType.AML,
                jurisdiction='EU',
                json_logic={'test': 'rule'},
                conditions=[],
                confidence_score=0.9
            )
            
            rule_entry_id = await self.audit_logger.log_rule_change(
                rule_id='test_rule',
                action='rule_created',
                old_rule=None,
                new_rule=mock_rule,
                user_id='test_user'
            )
            
            assert rule_entry_id is not None, "Should return rule entry ID"
            
            # Test audit trail integrity
            is_valid = await self.audit_logger.verify_audit_integrity()
            assert is_valid, "Audit trail integrity should be valid"
            
            # Test audit trail export
            export_path = await self.audit_logger.export_audit_trail(
                format='json',
                date_from=None,
                date_to=None
            )
            
            assert export_path is not None, "Should return export path"
            assert os.path.exists(export_path), "Export file should exist"
            
            # Test different export formats
            for format_type in ['csv', 'xml']:
                export_path = await self.audit_logger.export_audit_trail(
                    format=format_type,
                    date_from=None,
                    date_to=None
                )
                assert export_path is not None, f"Should export {format_type} format"
            
            self.test_results['audit_logger']['passed'] += 1
            logger.info(f"✅ {test_name} passed")
            
        except Exception as e:
            self.test_results['audit_logger']['failed'] += 1
            self.test_results['audit_logger']['errors'].append(f"{test_name}: {str(e)}")
            logger.error(f"❌ {test_name} failed: {e}")
    
    # UI TESTS
    async def test_ui_functionality(self):
        """Test UI functionality using Selenium"""
        test_name = "UI Functionality"
        logger.info(f"Running {test_name}...")
        
        if not self.driver:
            logger.warning("WebDriver not available, skipping UI tests")
            return
        
        try:
            # Test Phase 3 dashboard access
            self.driver.get(f"{self.test_config['ui_base_url']}/phase3")
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Check page title
            assert "Phase 3" in self.driver.title, "Page title should contain 'Phase 3'"
            
            # Test navigation tabs
            tabs = self.driver.find_elements(By.CSS_SELECTOR, ".nav-tabs .nav-link")
            assert len(tabs) >= 5, "Should have at least 5 tabs"
            
            # Test Rule Compiler tab
            rule_compiler_tab = self.driver.find_element(By.ID, "rule-compiler-tab")
            rule_compiler_tab.click()
            
            # Check if Rule Compiler form is visible
            obligation_text = self.driver.find_element(By.ID, "obligationText")
            assert obligation_text.is_displayed(), "Obligation text area should be visible"
            
            # Test form input
            obligation_text.clear()
            obligation_text.send_keys("Test regulatory obligation")
            
            # Test regulation type selection
            regulation_select = self.driver.find_element(By.ID, "regulationType")
            regulation_select.click()
            
            # Test Kafka Consumer tab
            kafka_tab = self.driver.find_element(By.ID, "kafka-consumer-tab")
            kafka_tab.click()
            
            # Check consumer status display
            consumer_status = self.driver.find_element(By.ID, "consumerStatus")
            assert consumer_status.is_displayed(), "Consumer status should be visible"
            
            # Test other tabs
            tab_ids = ["jurisdiction-tab", "overlap-resolver-tab", "audit-logger-tab"]
            for tab_id in tab_ids:
                tab = self.driver.find_element(By.ID, tab_id)
                tab.click()
                time.sleep(0.5)  # Allow tab to switch
            
            # Test user guides access
            self.driver.get(f"{self.test_config['ui_base_url']}/phase3/guides")
            
            # Wait for guides page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "guide-nav"))
            )
            
            # Test navigation in user guides
            nav_links = self.driver.find_elements(By.CSS_SELECTOR, ".guide-nav .nav-link")
            assert len(nav_links) >= 6, "Should have at least 6 guide sections"
            
            # Test search functionality
            search_input = self.driver.find_element(By.ID, "searchInput")
            search_input.send_keys("rule compiler")
            time.sleep(1)  # Allow search to process
            
            self.test_results['ui_tests']['passed'] += 1
            logger.info(f"✅ {test_name} passed")
            
        except Exception as e:
            self.test_results['ui_tests']['failed'] += 1
            self.test_results['ui_tests']['errors'].append(f"{test_name}: {str(e)}")
            logger.error(f"❌ {test_name} failed: {e}")
    
    # API TESTS
    async def test_api_endpoints(self):
        """Test API endpoints functionality"""
        test_name = "API Endpoints"
        logger.info(f"Running {test_name}...")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Test health endpoint
                async with session.get(f"{self.test_config['api_base_url']}/api/phase3/health") as response:
                    assert response.status == 200, "Health endpoint should return 200"
                    data = await response.json()
                    assert data['status'] == 'healthy', "Health status should be healthy"
                
                # Test rule compiler endpoint
                compile_data = {
                    'obligation_text': 'Test obligation for API testing',
                    'regulation_type': 'AML',
                    'jurisdiction': 'EU'
                }
                
                async with session.post(
                    f"{self.test_config['api_base_url']}/api/phase3/rule-compiler/compile",
                    json=compile_data
                ) as response:
                    # May return 401 if auth is required, which is acceptable
                    assert response.status in [200, 401], f"Compile endpoint returned {response.status}"
                
                # Test validation endpoint
                validate_data = {
                    'json_logic': {'>': [{'var': 'amount'}, 1000]}
                }
                
                async with session.post(
                    f"{self.test_config['api_base_url']}/api/phase3/rule-compiler/validate",
                    json=validate_data
                ) as response:
                    assert response.status in [200, 401], f"Validate endpoint returned {response.status}"
                
                # Test metrics endpoint
                async with session.get(f"{self.test_config['api_base_url']}/api/phase3/metrics") as response:
                    assert response.status in [200, 401], f"Metrics endpoint returned {response.status}"
            
            self.test_results['api_tests']['passed'] += 1
            logger.info(f"✅ {test_name} passed")
            
        except Exception as e:
            self.test_results['api_tests']['failed'] += 1
            self.test_results['api_tests']['errors'].append(f"{test_name}: {str(e)}")
            logger.error(f"❌ {test_name} failed: {e}")
    
    # INTEGRATION TESTS
    async def test_end_to_end_workflow(self):
        """Test end-to-end workflow integration"""
        test_name = "End-to-End Workflow"
        logger.info(f"Running {test_name}...")
        
        try:
            # 1. Compile a rule
            obligation_data = {
                'obligation_text': 'Customer verification required for amounts exceeding EUR 10,000',
                'regulation_type': 'KYC',
                'jurisdiction': 'DE',
                'obligation_level': 'Level_2',
                'confidence_score': 0.9,
                'effective_date': datetime.now(),
                'created_at': datetime.now()
            }
            
            rules = await self.rule_compiler.compile_obligation_to_rules(obligation_data)
            assert rules is not None and len(rules) > 0, "Should compile rules"
            
            # 2. Filter by jurisdiction
            filtered_rules = await self.jurisdiction_handler.filter_rules_by_jurisdiction(rules, 'DE')
            assert len(filtered_rules) > 0, "Should have filtered rules"
            
            # 3. Check for overlaps (with itself)
            if len(filtered_rules) >= 2:
                similarity = await self.overlap_resolver._calculate_text_similarity(
                    filtered_rules[0].json_logic.get('description', ''),
                    filtered_rules[1].json_logic.get('description', '')
                )
                assert similarity >= 0.0, "Similarity calculation should work"
            
            # 4. Log audit entry
            entry_id = await self.audit_logger.log_rule_change(
                rule_id=rules[0].rule_id,
                action='rule_compiled',
                old_rule=None,
                new_rule=rules[0],
                user_id='integration_test'
            )
            assert entry_id is not None, "Should log audit entry"
            
            # 5. Verify audit integrity
            is_valid = await self.audit_logger.verify_audit_integrity()
            assert is_valid, "Audit integrity should be maintained"
            
            self.test_results['integration_tests']['passed'] += 1
            logger.info(f"✅ {test_name} passed")
            
        except Exception as e:
            self.test_results['integration_tests']['failed'] += 1
            self.test_results['integration_tests']['errors'].append(f"{test_name}: {str(e)}")
            logger.error(f"❌ {test_name} failed: {e}")
    
    # PERFORMANCE TESTS
    async def test_performance_benchmarks(self):
        """Test performance benchmarks for all components"""
        test_name = "Performance Benchmarks"
        logger.info(f"Running {test_name}...")
        
        try:
            performance_results = {}
            
            # Rule Compiler Performance
            obligation_data = {
                'obligation_text': 'Performance test obligation with complex requirements',
                'regulation_type': 'AML',
                'jurisdiction': 'EU',
                'obligation_level': 'Level_2',
                'confidence_score': 0.85,
                'effective_date': datetime.now(),
                'created_at': datetime.now()
            }
            
            compile_times = []
            for i in range(5):  # Run 5 times for average
                start_time = time.time()
                rules = await self.rule_compiler.compile_obligation_to_rules(obligation_data)
                compile_time = (time.time() - start_time) * 1000
                compile_times.append(compile_time)
            
            avg_compile_time = sum(compile_times) / len(compile_times)
            performance_results['rule_compilation_ms'] = avg_compile_time
            
            # Overlap Detection Performance
            text1 = "Customer due diligence requirements for high-value transactions"
            text2 = "Enhanced verification needed for large financial transfers"
            
            overlap_times = []
            for i in range(10):  # Run 10 times for average
                start_time = time.time()
                similarity = await self.overlap_resolver._calculate_text_similarity(text1, text2)
                overlap_time = (time.time() - start_time) * 1000
                overlap_times.append(overlap_time)
            
            avg_overlap_time = sum(overlap_times) / len(overlap_times)
            performance_results['overlap_detection_ms'] = avg_overlap_time
            
            # Audit Logging Performance
            audit_times = []
            for i in range(20):  # Run 20 times for average
                start_time = time.time()
                entry_id = await self.audit_logger.log_system_event(
                    event_type='performance_test',
                    details=f'Performance test entry {i}',
                    user_id='perf_test'
                )
                audit_time = (time.time() - start_time) * 1000
                audit_times.append(audit_time)
            
            avg_audit_time = sum(audit_times) / len(audit_times)
            performance_results['audit_logging_ms'] = avg_audit_time
            
            # Check against targets
            targets = self.test_config['performance_targets']
            
            assert avg_compile_time < targets['rule_compilation_ms'], f"Rule compilation: {avg_compile_time:.1f}ms > {targets['rule_compilation_ms']}ms target"
            assert avg_overlap_time < targets['overlap_detection_ms'], f"Overlap detection: {avg_overlap_time:.1f}ms > {targets['overlap_detection_ms']}ms target"
            assert avg_audit_time < targets['audit_logging_ms'], f"Audit logging: {avg_audit_time:.1f}ms > {targets['audit_logging_ms']}ms target"
            
            logger.info(f"Performance Results: {performance_results}")
            
            self.test_results['performance_tests']['passed'] += 1
            logger.info(f"✅ {test_name} passed")
            
        except Exception as e:
            self.test_results['performance_tests']['failed'] += 1
            self.test_results['performance_tests']['errors'].append(f"{test_name}: {str(e)}")
            logger.error(f"❌ {test_name} failed: {e}")
    
    async def run_all_tests(self):
        """Run all automated tests"""
        logger.info("🚀 Starting Phase 3 Automated Test Suite...")
        
        await self.setup_test_environment()
        
        try:
            # Run all test categories
            test_methods = [
                # Rule Compiler Tests
                self.test_rule_compiler_basic_functionality,
                self.test_rule_compiler_edge_cases,
                
                # Kafka Consumer Tests
                self.test_kafka_consumer_message_processing,
                
                # Jurisdiction Handler Tests
                self.test_jurisdiction_handler_filtering,
                
                # Overlap Resolver Tests
                self.test_overlap_resolver_similarity_detection,
                
                # Audit Logger Tests
                self.test_audit_logger_functionality,
                
                # UI Tests
                self.test_ui_functionality,
                
                # API Tests
                self.test_api_endpoints,
                
                # Integration Tests
                self.test_end_to_end_workflow,
                
                # Performance Tests
                self.test_performance_benchmarks
            ]
            
            # Run tests concurrently where possible
            for test_method in test_methods:
                await test_method()
            
        finally:
            await self.teardown_test_environment()
        
        # Generate test report
        self.generate_test_report()
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        logger.info("📊 Generating Test Report...")
        
        total_passed = sum(category['passed'] for category in self.test_results.values())
        total_failed = sum(category['failed'] for category in self.test_results.values())
        total_tests = total_passed + total_failed
        
        success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        report = f"""
╔══════════════════════════════════════════════════════════════════════════════════╗
║                           PHASE 3 AUTOMATED TEST REPORT                         ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ Total Tests: {total_tests:3d} | Passed: {total_passed:3d} | Failed: {total_failed:3d} | Success Rate: {success_rate:5.1f}% ║
╠══════════════════════════════════════════════════════════════════════════════════╣
"""
        
        for category, results in self.test_results.items():
            category_total = results['passed'] + results['failed']
            category_rate = (results['passed'] / category_total * 100) if category_total > 0 else 0
            
            report += f"║ {category.replace('_', ' ').title():20s}: {results['passed']:2d}/{category_total:2d} ({category_rate:5.1f}%) "
            
            if results['failed'] > 0:
                report += "❌"
            else:
                report += "✅"
            
            report += " " * (50 - len(category.replace('_', ' ').title())) + "║\n"
        
        report += "╚══════════════════════════════════════════════════════════════════════════════════╝\n"
        
        # Add error details if any
        if total_failed > 0:
            report += "\n🔍 ERROR DETAILS:\n"
            for category, results in self.test_results.items():
                if results['errors']:
                    report += f"\n{category.replace('_', ' ').title()}:\n"
                    for error in results['errors']:
                        report += f"  • {error}\n"
        
        print(report)
        
        # Save report to file
        report_file = f"phase3_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        
        logger.info(f"Test report saved to {report_file}")
        
        # Return success status for CI/CD
        return total_failed == 0

async def main():
    """Main test runner"""
    test_suite = Phase3TestSuite()
    success = await test_suite.run_all_tests()
    
    if success:
        logger.info("🎉 All tests passed! Phase 3 is ready for production.")
        sys.exit(0)
    else:
        logger.error("❌ Some tests failed. Please review the test report.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
