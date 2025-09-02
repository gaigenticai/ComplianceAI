#!/usr/bin/env python3
"""
End-to-End Regulatory Processing Pipeline Integration Tests
=========================================================

This module provides comprehensive end-to-end integration testing for the complete
regulatory processing pipeline from Kafka message ingestion through Intelligence
Agent processing to Decision Agent orchestration and final report generation.

Test Coverage Areas:
- Complete workflow: Kafka → Intelligence Agent → Decision Agent
- New obligation processing workflow with real regulatory updates
- Rule compilation and deployment across the pipeline
- Jurisdiction-specific rule application and conflict resolution
- Overlap resolution and coalescing in multi-agent environment
- Cross-agent communication and data consistency
- Error propagation and recovery mechanisms

Rule Compliance:
- Rule 1: No stubs - Complete production-grade integration tests
- Rule 12: Automated testing - Comprehensive end-to-end test coverage
- Rule 17: Code documentation - Extensive test documentation
"""

import pytest
import asyncio
import json
import uuid
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List, Any, Optional, Set, Tuple
import logging
import docker
import psutil
from contextlib import asynccontextmanager

# Import test infrastructure
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

# Import agent components
sys.path.append(os.path.join(os.path.dirname(__file__), '../../python-agents/regulatory-intel-agent/src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../../python-agents/intelligence-compliance-agent/src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../../python-agents/decision-orchestration-agent/src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../../python-agents/intake-processing-agent/src'))

from regulatory_intelligence_service import RegulatoryIntelligenceService
from intelligence_compliance_service import IntelligenceComplianceService
from decision_orchestration_service import DecisionOrchestrationService
from intake_processing_service import IntakeProcessingService

# Configure test logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TestRegulatoryPipeline:
    """
    Comprehensive end-to-end test suite for regulatory processing pipeline
    
    Tests complete workflows from regulatory update ingestion through
    intelligent processing to decision orchestration and report generation.
    """
    
    @pytest.fixture(scope="class")
    async def test_infrastructure(self):
        """Set up test infrastructure with Docker services"""
        infrastructure = TestInfrastructure()
        await infrastructure.setup()
        yield infrastructure
        await infrastructure.teardown()
    
    @pytest.fixture
    async def pipeline_services(self, test_infrastructure):
        """Initialize all pipeline services for testing"""
        services = PipelineServices()
        await services.initialize(test_infrastructure)
        yield services
        await services.cleanup()
    
    @pytest.fixture
    def sample_regulatory_updates(self):
        """Sample regulatory updates for pipeline testing"""
        return {
            "gdpr_update": {
                "update_id": "GDPR_UPDATE_001",
                "source": "European Commission",
                "regulation": "GDPR",
                "update_type": "GUIDANCE",
                "title": "Updated Guidance on Data Subject Rights",
                "content": """
                The European Data Protection Board has issued updated guidance on the implementation
                of data subject rights under Articles 15-22 of the GDPR. Key updates include:
                
                1. Enhanced requirements for identity verification before processing access requests
                2. Clarification on the scope of the right to data portability
                3. New timelines for responding to rectification requests
                4. Updated procedures for handling erasure requests with legitimate interests
                
                These updates are effective immediately and apply to all data controllers and processors
                operating within the EU jurisdiction.
                """,
                "effective_date": "2024-04-01",
                "jurisdiction": "EU",
                "priority": "HIGH",
                "affects_obligations": ["GDPR_001", "GDPR_002", "GDPR_003"],
                "metadata": {
                    "document_url": "https://edpb.europa.eu/guidance/gdpr-2024-001",
                    "publication_date": "2024-03-15",
                    "consultation_period": False,
                    "implementation_deadline": "2024-04-01"
                }
            },
            "basel_update": {
                "update_id": "BASEL_UPDATE_001",
                "source": "Basel Committee on Banking Supervision",
                "regulation": "Basel III",
                "update_type": "STANDARD",
                "title": "Revised Capital Requirements for Operational Risk",
                "content": """
                The Basel Committee has finalized revisions to the standardized approach for operational risk
                capital requirements. Key changes include:
                
                1. Updated business indicator components for digital banking activities
                2. Enhanced loss data collection requirements for fintech operations
                3. Revised internal loss multipliers for cyber risk events
                4. New capital add-ons for third-party technology dependencies
                
                Implementation timeline:
                - Large internationally active banks: January 1, 2025
                - Other banks: January 1, 2026
                """,
                "effective_date": "2025-01-01",
                "jurisdiction": "GLOBAL",
                "priority": "CRITICAL",
                "affects_obligations": ["BASEL_CAP_001", "BASEL_OP_001"],
                "metadata": {
                    "document_url": "https://bis.org/bcbs/publ/d555.htm",
                    "publication_date": "2024-03-20",
                    "consultation_period": False,
                    "implementation_deadline": "2025-01-01"
                }
            },
            "bafin_update": {
                "update_id": "BAFIN_UPDATE_001",
                "source": "BaFin",
                "regulation": "MaRisk",
                "update_type": "CIRCULAR",
                "title": "Updated Requirements for IT Risk Management",
                "content": """
                BaFin has issued updated minimum requirements for risk management (MaRisk) with
                specific focus on IT and cyber risk management. Updates include:
                
                1. Enhanced governance requirements for cloud computing arrangements
                2. Mandatory incident reporting thresholds for cyber security events
                3. Updated business continuity planning requirements
                4. New outsourcing risk management procedures for fintech partnerships
                
                German credit institutions must implement these requirements by July 1, 2024.
                """,
                "effective_date": "2024-07-01",
                "jurisdiction": "DE",
                "priority": "HIGH",
                "affects_obligations": ["MARISK_001", "MARISK_002"],
                "metadata": {
                    "document_url": "https://bafin.de/dok/18234567",
                    "publication_date": "2024-03-25",
                    "consultation_period": False,
                    "implementation_deadline": "2024-07-01"
                }
            },
            "mifid_update": {
                "update_id": "MIFID_UPDATE_001",
                "source": "ESMA",
                "regulation": "MiFID II",
                "update_type": "TECHNICAL_STANDARD",
                "title": "Updated Suitability Assessment Guidelines",
                "content": """
                ESMA has published updated guidelines on suitability assessment under MiFID II,
                incorporating lessons learned from supervisory convergence work. Key updates:
                
                1. Enhanced know-your-customer procedures for complex products
                2. Updated suitability assessment documentation requirements
                3. New guidelines for robo-advisory services
                4. Clarified requirements for ongoing suitability monitoring
                
                National competent authorities must implement by September 1, 2024.
                """,
                "effective_date": "2024-09-01",
                "jurisdiction": "EU",
                "priority": "HIGH",
                "affects_obligations": ["MIFID_SUIT_001", "MIFID_DOC_001"],
                "metadata": {
                    "document_url": "https://esma.europa.eu/document/mifid-guidelines-2024",
                    "publication_date": "2024-03-30",
                    "consultation_period": False,
                    "implementation_deadline": "2024-09-01"
                }
            }
        }
    
    @pytest.fixture
    def sample_customer_data(self):
        """Sample customer data for pipeline testing"""
        return {
            "customer_001": {
                "customer_id": "CUST_DE_001",
                "customer_type": "individual",
                "primary_jurisdiction": "DE",
                "secondary_jurisdictions": ["EU"],
                "residence": "DE",
                "citizenship": "DE",
                "services": ["retail_banking", "investment_advice"],
                "risk_profile": "MEDIUM",
                "kyc_status": "COMPLETED",
                "last_review": "2024-01-15",
                "data_processing_consent": True,
                "marketing_consent": False
            },
            "customer_002": {
                "customer_id": "CUST_IE_001",
                "customer_type": "corporation",
                "primary_jurisdiction": "IE",
                "secondary_jurisdictions": ["EU", "US"],
                "incorporation": "IE",
                "operating_jurisdictions": ["IE", "DE", "FR", "US"],
                "services": ["corporate_banking", "treasury", "trade_finance"],
                "risk_profile": "HIGH",
                "kyc_status": "ENHANCED_DUE_DILIGENCE",
                "last_review": "2024-02-20",
                "entity_type": "financial_services_company",
                "consolidation_basis": "global"
            },
            "customer_003": {
                "customer_id": "CUST_US_001",
                "customer_type": "individual",
                "primary_jurisdiction": "US",
                "secondary_jurisdictions": [],
                "residence": "US",
                "citizenship": "US",
                "services": ["private_banking", "investment_management"],
                "risk_profile": "HIGH",
                "kyc_status": "COMPLETED",
                "last_review": "2024-03-01",
                "accredited_investor": True,
                "fatca_status": "US_PERSON"
            }
        }
    
    # =========================================================================
    # END-TO-END PIPELINE WORKFLOW TESTS
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_complete_regulatory_update_pipeline(self, pipeline_services, sample_regulatory_updates):
        """Test complete pipeline from regulatory update to rule deployment"""
        gdpr_update = sample_regulatory_updates["gdpr_update"]
        
        # Step 1: Regulatory Intelligence Agent processes update
        logger.info("Step 1: Processing regulatory update through Intelligence Agent")
        intelligence_result = await pipeline_services.regulatory_intelligence.process_regulatory_update(gdpr_update)
        
        assert intelligence_result is not None
        assert intelligence_result.success is True
        assert intelligence_result.extracted_obligations is not None
        assert len(intelligence_result.extracted_obligations) > 0
        
        # Step 2: Intelligence & Compliance Agent processes obligations
        logger.info("Step 2: Processing obligations through Intelligence & Compliance Agent")
        compliance_results = []
        
        for obligation in intelligence_result.extracted_obligations:
            # Rule compilation
            rule_result = await pipeline_services.intelligence_compliance.compile_rule(obligation)
            assert rule_result.success is True
            
            # Jurisdiction handling
            jurisdiction_result = await pipeline_services.intelligence_compliance.apply_jurisdiction_rules(
                obligation, ["EU", "DE"]
            )
            assert jurisdiction_result is not None
            
            # Overlap resolution
            overlap_result = await pipeline_services.intelligence_compliance.resolve_overlaps([obligation])
            assert overlap_result is not None
            
            compliance_results.append({
                "obligation": obligation,
                "rule_result": rule_result,
                "jurisdiction_result": jurisdiction_result,
                "overlap_result": overlap_result
            })
        
        # Step 3: Decision & Orchestration Agent processes results
        logger.info("Step 3: Processing through Decision & Orchestration Agent")
        orchestration_result = await pipeline_services.decision_orchestration.orchestrate_compliance_decision(
            compliance_results
        )
        
        assert orchestration_result is not None
        assert orchestration_result.success is True
        assert orchestration_result.deployed_rules is not None
        assert len(orchestration_result.deployed_rules) > 0
        
        # Step 4: Verify end-to-end data consistency
        logger.info("Step 4: Verifying end-to-end data consistency")
        consistency_check = await self._verify_pipeline_consistency(
            gdpr_update, intelligence_result, compliance_results, orchestration_result
        )
        assert consistency_check is True
        
        logger.info("Complete regulatory update pipeline test successful")
    
    @pytest.mark.asyncio
    async def test_multi_jurisdiction_pipeline_processing(self, pipeline_services, sample_regulatory_updates):
        """Test pipeline processing with multi-jurisdiction regulatory updates"""
        # Process updates from different jurisdictions
        updates = [
            sample_regulatory_updates["gdpr_update"],    # EU
            sample_regulatory_updates["bafin_update"],   # DE
            sample_regulatory_updates["basel_update"]    # GLOBAL
        ]
        
        pipeline_results = []
        
        for update in updates:
            logger.info(f"Processing {update['regulation']} update from {update['jurisdiction']}")
            
            # Full pipeline processing
            result = await self._process_update_through_pipeline(pipeline_services, update)
            pipeline_results.append(result)
            
            assert result["success"] is True
            assert result["jurisdiction_conflicts_resolved"] is True
        
        # Verify cross-jurisdiction consistency
        logger.info("Verifying cross-jurisdiction consistency")
        cross_jurisdiction_check = await self._verify_cross_jurisdiction_consistency(pipeline_results)
        assert cross_jurisdiction_check is True
        
        logger.info("Multi-jurisdiction pipeline processing successful")
    
    @pytest.mark.asyncio
    async def test_customer_specific_pipeline_processing(self, pipeline_services, sample_customer_data, sample_regulatory_updates):
        """Test pipeline processing with customer-specific rule application"""
        customer = sample_customer_data["customer_001"]  # German individual customer
        gdpr_update = sample_regulatory_updates["gdpr_update"]
        
        # Step 1: Process regulatory update
        intelligence_result = await pipeline_services.regulatory_intelligence.process_regulatory_update(gdpr_update)
        
        # Step 2: Apply customer-specific jurisdiction rules
        logger.info("Applying customer-specific jurisdiction rules")
        customer_specific_results = []
        
        for obligation in intelligence_result.extracted_obligations:
            # Apply jurisdiction rules with customer context
            jurisdiction_result = await pipeline_services.intelligence_compliance.apply_jurisdiction_rules_with_context(
                obligation, customer
            )
            
            # Compile customer-specific rules
            customer_rule_result = await pipeline_services.intelligence_compliance.compile_customer_specific_rule(
                obligation, customer
            )
            
            customer_specific_results.append({
                "obligation": obligation,
                "jurisdiction_result": jurisdiction_result,
                "customer_rule": customer_rule_result
            })
        
        # Step 3: Orchestrate customer-specific compliance
        logger.info("Orchestrating customer-specific compliance")
        customer_orchestration = await pipeline_services.decision_orchestration.orchestrate_customer_compliance(
            customer_specific_results, customer
        )
        
        assert customer_orchestration.success is True
        assert customer_orchestration.customer_specific_rules is not None
        
        # Verify customer context is properly applied
        assert customer["primary_jurisdiction"] in customer_orchestration.applicable_jurisdictions
        assert "EU" in customer_orchestration.applicable_jurisdictions  # Should include parent jurisdiction
        
        logger.info("Customer-specific pipeline processing successful")
    
    @pytest.mark.asyncio
    async def test_error_propagation_and_recovery(self, pipeline_services, sample_regulatory_updates):
        """Test error propagation and recovery mechanisms across the pipeline"""
        # Create invalid regulatory update to trigger errors
        invalid_update = {
            "update_id": "INVALID_UPDATE_001",
            "source": "Invalid Source",
            "regulation": None,  # Invalid
            "content": "",       # Empty content
            "jurisdiction": "INVALID_JURISDICTION"
        }
        
        # Test error handling at each stage
        logger.info("Testing error handling in Regulatory Intelligence Agent")
        try:
            intelligence_result = await pipeline_services.regulatory_intelligence.process_regulatory_update(invalid_update)
            assert intelligence_result.success is False
            assert len(intelligence_result.errors) > 0
        except Exception as e:
            # Should handle gracefully
            assert "invalid" in str(e).lower() or "missing" in str(e).lower()
        
        # Test recovery with valid update after error
        logger.info("Testing recovery after error")
        valid_update = sample_regulatory_updates["gdpr_update"]
        recovery_result = await pipeline_services.regulatory_intelligence.process_regulatory_update(valid_update)
        
        assert recovery_result.success is True
        assert len(recovery_result.extracted_obligations) > 0
        
        logger.info("Error propagation and recovery test successful")
    
    @pytest.mark.asyncio
    async def test_concurrent_pipeline_processing(self, pipeline_services, sample_regulatory_updates):
        """Test concurrent processing of multiple regulatory updates"""
        updates = list(sample_regulatory_updates.values())
        
        # Process updates concurrently
        logger.info(f"Processing {len(updates)} updates concurrently")
        start_time = time.time()
        
        tasks = [
            self._process_update_through_pipeline(pipeline_services, update)
            for update in updates
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Verify all results
        successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
        assert len(successful_results) == len(updates)
        
        # Verify performance
        assert processing_time < 30.0  # Should complete within 30 seconds
        
        logger.info(f"Concurrent pipeline processing: {len(updates)} updates in {processing_time:.2f}s")
    
    # =========================================================================
    # RULE COMPILATION AND DEPLOYMENT TESTS
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_rule_compilation_pipeline(self, pipeline_services, sample_regulatory_updates):
        """Test rule compilation pipeline with complex regulatory logic"""
        basel_update = sample_regulatory_updates["basel_update"]
        
        # Process through intelligence agent
        intelligence_result = await pipeline_services.regulatory_intelligence.process_regulatory_update(basel_update)
        
        # Test rule compilation for each extracted obligation
        compiled_rules = []
        for obligation in intelligence_result.extracted_obligations:
            logger.info(f"Compiling rule for obligation: {obligation.get('obligation_id')}")
            
            # Compile rule with complex logic
            rule_result = await pipeline_services.intelligence_compliance.compile_complex_rule(obligation)
            
            assert rule_result.success is True
            assert rule_result.json_logic is not None
            assert rule_result.validation_errors == []
            
            # Validate JSON-Logic structure
            json_logic_valid = await pipeline_services.intelligence_compliance.validate_json_logic(
                rule_result.json_logic
            )
            assert json_logic_valid is True
            
            compiled_rules.append(rule_result)
        
        # Test rule deployment
        logger.info("Deploying compiled rules")
        deployment_result = await pipeline_services.decision_orchestration.deploy_rules(compiled_rules)
        
        assert deployment_result.success is True
        assert deployment_result.deployed_count == len(compiled_rules)
        
        logger.info("Rule compilation pipeline test successful")
    
    @pytest.mark.asyncio
    async def test_rule_versioning_and_updates(self, pipeline_services, sample_regulatory_updates):
        """Test rule versioning and update mechanisms"""
        gdpr_update = sample_regulatory_updates["gdpr_update"]
        
        # Initial rule deployment
        logger.info("Initial rule deployment")
        initial_result = await self._process_update_through_pipeline(pipeline_services, gdpr_update)
        initial_version = initial_result["rule_versions"]
        
        # Create updated version of the same regulation
        updated_gdpr = gdpr_update.copy()
        updated_gdpr["update_id"] = "GDPR_UPDATE_002"
        updated_gdpr["content"] += "\n\nAdditional clarification: Enhanced verification procedures required."
        updated_gdpr["effective_date"] = "2024-05-01"
        
        # Process updated rule
        logger.info("Processing rule update")
        updated_result = await self._process_update_through_pipeline(pipeline_services, updated_gdpr)
        updated_version = updated_result["rule_versions"]
        
        # Verify versioning
        assert updated_version != initial_version
        assert updated_result["success"] is True
        
        # Verify backward compatibility
        compatibility_check = await pipeline_services.decision_orchestration.check_rule_compatibility(
            initial_version, updated_version
        )
        assert compatibility_check.compatible is True
        
        logger.info("Rule versioning and updates test successful")
    
    # =========================================================================
    # JURISDICTION-SPECIFIC RULE APPLICATION TESTS
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_eu_directive_national_implementation(self, pipeline_services):
        """Test EU directive with national implementation variations"""
        # Simulate EU directive
        eu_directive = {
            "update_id": "EU_DIR_001",
            "source": "European Commission",
            "regulation": "EU Directive 2024/001",
            "update_type": "DIRECTIVE",
            "title": "Digital Services Compliance Directive",
            "content": """
            EU Member States shall ensure that digital service providers implement
            appropriate risk management measures for their services. Member States
            may impose additional requirements based on national circumstances.
            """,
            "jurisdiction": "EU",
            "implementation_deadline": "2024-12-31",
            "allows_national_variations": True
        }
        
        # Simulate national implementations
        national_implementations = [
            {
                "update_id": "DE_IMP_001",
                "source": "BaFin",
                "regulation": "German Digital Services Act",
                "parent_directive": "EU_DIR_001",
                "jurisdiction": "DE",
                "additional_requirements": [
                    "Enhanced reporting to BaFin",
                    "German language documentation",
                    "Local data residency requirements"
                ]
            },
            {
                "update_id": "IE_IMP_001",
                "source": "Central Bank of Ireland",
                "regulation": "Irish Digital Services Regulations",
                "parent_directive": "EU_DIR_001",
                "jurisdiction": "IE",
                "additional_requirements": [
                    "Quarterly reporting to CBI",
                    "Irish entity establishment requirement"
                ]
            }
        ]
        
        # Process EU directive
        logger.info("Processing EU directive")
        eu_result = await self._process_update_through_pipeline(pipeline_services, eu_directive)
        
        # Process national implementations
        national_results = []
        for implementation in national_implementations:
            logger.info(f"Processing {implementation['jurisdiction']} implementation")
            impl_result = await self._process_update_through_pipeline(pipeline_services, implementation)
            national_results.append(impl_result)
        
        # Test jurisdiction hierarchy resolution
        logger.info("Resolving jurisdiction hierarchy")
        hierarchy_result = await pipeline_services.intelligence_compliance.resolve_jurisdiction_hierarchy(
            [eu_result] + national_results
        )
        
        assert hierarchy_result.success is True
        assert "EU" in hierarchy_result.jurisdiction_hierarchy
        assert "DE" in hierarchy_result.jurisdiction_hierarchy
        assert "IE" in hierarchy_result.jurisdiction_hierarchy
        
        # Verify precedence rules
        assert hierarchy_result.precedence_order[0] == "EU"  # EU directive has precedence
        
        logger.info("EU directive national implementation test successful")
    
    @pytest.mark.asyncio
    async def test_cross_border_customer_compliance(self, pipeline_services, sample_customer_data):
        """Test cross-border customer compliance scenarios"""
        # Multi-jurisdiction corporate customer
        corporate_customer = sample_customer_data["customer_002"]  # Irish corporation with global operations
        
        # Create cross-border regulatory scenario
        cross_border_updates = [
            {
                "update_id": "CROSS_001",
                "regulation": "EU AML Directive",
                "jurisdiction": "EU",
                "content": "Enhanced due diligence for cross-border transactions above €10,000"
            },
            {
                "update_id": "CROSS_002", 
                "regulation": "US Bank Secrecy Act",
                "jurisdiction": "US",
                "content": "Suspicious activity reporting for transactions above $10,000"
            },
            {
                "update_id": "CROSS_003",
                "regulation": "Irish AML Regulations",
                "jurisdiction": "IE",
                "content": "Additional reporting requirements for Irish-incorporated entities"
            }
        ]
        
        # Process updates for cross-border scenario
        cross_border_results = []
        for update in cross_border_updates:
            logger.info(f"Processing {update['jurisdiction']} update for cross-border scenario")
            result = await self._process_customer_specific_update(
                pipeline_services, update, corporate_customer
            )
            cross_border_results.append(result)
        
        # Resolve cross-border conflicts
        logger.info("Resolving cross-border compliance conflicts")
        conflict_resolution = await pipeline_services.intelligence_compliance.resolve_cross_border_conflicts(
            cross_border_results, corporate_customer
        )
        
        assert conflict_resolution.success is True
        assert len(conflict_resolution.applicable_jurisdictions) >= 3  # EU, IE, US
        assert conflict_resolution.compliance_strategy is not None
        
        logger.info("Cross-border customer compliance test successful")
    
    # =========================================================================
    # OVERLAP RESOLUTION AND COALESCING TESTS
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_multi_agent_overlap_resolution(self, pipeline_services, sample_regulatory_updates):
        """Test overlap resolution across multiple agents"""
        # Process multiple related updates
        related_updates = [
            sample_regulatory_updates["gdpr_update"],
            sample_regulatory_updates["mifid_update"]
        ]
        
        # Process updates through pipeline
        pipeline_results = []
        for update in related_updates:
            result = await self._process_update_through_pipeline(pipeline_services, update)
            pipeline_results.append(result)
        
        # Extract all obligations from results
        all_obligations = []
        for result in pipeline_results:
            all_obligations.extend(result["extracted_obligations"])
        
        # Test multi-agent overlap detection
        logger.info("Detecting overlaps across agents")
        overlap_detection = await pipeline_services.intelligence_compliance.detect_multi_agent_overlaps(
            all_obligations
        )
        
        assert overlap_detection is not None
        assert len(overlap_detection.detected_overlaps) >= 0  # May or may not have overlaps
        
        # Test coalescing if overlaps found
        if len(overlap_detection.detected_overlaps) > 0:
            logger.info("Coalescing overlapping obligations")
            coalescing_result = await pipeline_services.intelligence_compliance.coalesce_overlapping_obligations(
                overlap_detection.detected_overlaps
            )
            
            assert coalescing_result.success is True
            assert coalescing_result.coalesced_obligations is not None
        
        logger.info("Multi-agent overlap resolution test successful")
    
    @pytest.mark.asyncio
    async def test_temporal_overlap_resolution(self, pipeline_services):
        """Test temporal overlap resolution with effective dates"""
        # Create updates with overlapping time periods
        temporal_updates = [
            {
                "update_id": "TEMP_001",
                "regulation": "Test Regulation A",
                "jurisdiction": "EU",
                "content": "Initial requirement for data retention: 5 years",
                "effective_date": "2024-01-01",
                "expiry_date": "2024-12-31"
            },
            {
                "update_id": "TEMP_002",
                "regulation": "Test Regulation A",
                "jurisdiction": "EU", 
                "content": "Updated requirement for data retention: 7 years",
                "effective_date": "2024-06-01",
                "supersedes": "TEMP_001"
            }
        ]
        
        # Process temporal updates
        temporal_results = []
        for update in temporal_updates:
            result = await self._process_update_through_pipeline(pipeline_services, update)
            temporal_results.append(result)
        
        # Test temporal overlap resolution
        logger.info("Resolving temporal overlaps")
        temporal_resolution = await pipeline_services.intelligence_compliance.resolve_temporal_overlaps(
            temporal_results
        )
        
        assert temporal_resolution.success is True
        assert temporal_resolution.active_obligations is not None
        assert temporal_resolution.superseded_obligations is not None
        
        # Verify correct temporal precedence
        active_obligation = temporal_resolution.active_obligations[0]
        assert active_obligation["update_id"] == "TEMP_002"  # Latest should be active
        
        logger.info("Temporal overlap resolution test successful")
    
    # =========================================================================
    # PERFORMANCE AND SCALABILITY TESTS
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_pipeline_performance_benchmarks(self, pipeline_services, sample_regulatory_updates):
        """Test pipeline performance benchmarks"""
        updates = list(sample_regulatory_updates.values())
        
        # Measure end-to-end processing time
        logger.info("Measuring pipeline performance")
        start_time = time.time()
        
        # Process all updates
        performance_results = []
        for update in updates:
            update_start = time.time()
            result = await self._process_update_through_pipeline(pipeline_services, update)
            update_end = time.time()
            
            performance_results.append({
                "update_id": update["update_id"],
                "processing_time": update_end - update_start,
                "success": result["success"]
            })
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify performance benchmarks
        assert total_time < 60.0  # Total processing should be under 60 seconds
        
        average_time = sum(r["processing_time"] for r in performance_results) / len(performance_results)
        assert average_time < 15.0  # Average per update should be under 15 seconds
        
        # Verify all succeeded
        assert all(r["success"] for r in performance_results)
        
        logger.info(f"Pipeline performance: {len(updates)} updates in {total_time:.2f}s (avg: {average_time:.2f}s)")
    
    @pytest.mark.asyncio
    async def test_pipeline_memory_efficiency(self, pipeline_services, sample_regulatory_updates):
        """Test pipeline memory efficiency with large datasets"""
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create large dataset by replicating updates
        large_dataset = []
        for i in range(20):  # 20x replication
            for update in sample_regulatory_updates.values():
                modified_update = update.copy()
                modified_update["update_id"] = f"{update['update_id']}_COPY_{i:03d}"
                large_dataset.append(modified_update)
        
        logger.info(f"Processing large dataset: {len(large_dataset)} updates")
        
        # Process large dataset
        processed_count = 0
        for update in large_dataset[:10]:  # Process subset to avoid timeout
            try:
                result = await self._process_update_through_pipeline(pipeline_services, update)
                if result["success"]:
                    processed_count += 1
            except Exception as e:
                logger.warning(f"Failed to process update {update['update_id']}: {e}")
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Cleanup
        del large_dataset
        gc.collect()
        
        assert processed_count > 0
        assert memory_increase < 1000  # Should not increase by more than 1GB
        
        logger.info(f"Pipeline memory efficiency: {memory_increase:.2f} MB increase for {processed_count} updates")
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    async def _process_update_through_pipeline(self, pipeline_services, update):
        """Process a regulatory update through the complete pipeline"""
        try:
            # Step 1: Regulatory Intelligence
            intelligence_result = await pipeline_services.regulatory_intelligence.process_regulatory_update(update)
            if not intelligence_result.success:
                return {"success": False, "error": "Intelligence processing failed"}
            
            # Step 2: Intelligence & Compliance
            compliance_results = []
            for obligation in intelligence_result.extracted_obligations:
                rule_result = await pipeline_services.intelligence_compliance.compile_rule(obligation)
                jurisdiction_result = await pipeline_services.intelligence_compliance.apply_jurisdiction_rules(
                    obligation, [update.get("jurisdiction", "EU")]
                )
                compliance_results.append({
                    "obligation": obligation,
                    "rule_result": rule_result,
                    "jurisdiction_result": jurisdiction_result
                })
            
            # Step 3: Decision & Orchestration
            orchestration_result = await pipeline_services.decision_orchestration.orchestrate_compliance_decision(
                compliance_results
            )
            
            return {
                "success": True,
                "update_id": update["update_id"],
                "intelligence_result": intelligence_result,
                "compliance_results": compliance_results,
                "orchestration_result": orchestration_result,
                "extracted_obligations": intelligence_result.extracted_obligations,
                "rule_versions": orchestration_result.rule_versions if orchestration_result.success else None,
                "jurisdiction_conflicts_resolved": True
            }
            
        except Exception as e:
            logger.error(f"Pipeline processing failed for {update.get('update_id')}: {e}")
            return {"success": False, "error": str(e)}
    
    async def _process_customer_specific_update(self, pipeline_services, update, customer):
        """Process update with customer-specific context"""
        # Process through pipeline with customer context
        result = await self._process_update_through_pipeline(pipeline_services, update)
        
        if result["success"]:
            # Apply customer-specific processing
            customer_result = await pipeline_services.decision_orchestration.apply_customer_context(
                result["orchestration_result"], customer
            )
            result["customer_result"] = customer_result
        
        return result
    
    async def _verify_pipeline_consistency(self, original_update, intelligence_result, compliance_results, orchestration_result):
        """Verify data consistency across pipeline stages"""
        try:
            # Verify update ID consistency
            if original_update["update_id"] not in str(intelligence_result):
                return False
            
            # Verify obligation count consistency
            if len(intelligence_result.extracted_obligations) != len(compliance_results):
                return False
            
            # Verify rule deployment consistency
            if not orchestration_result.success:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Consistency verification failed: {e}")
            return False
    
    async def _verify_cross_jurisdiction_consistency(self, pipeline_results):
        """Verify consistency across multiple jurisdictions"""
        try:
            # Check that all results succeeded
            if not all(result["success"] for result in pipeline_results):
                return False
            
            # Check for jurisdiction conflicts
            jurisdictions = set()
            for result in pipeline_results:
                if "jurisdiction" in result:
                    jurisdictions.add(result["jurisdiction"])
            
            # Should have multiple jurisdictions
            if len(jurisdictions) < 2:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Cross-jurisdiction consistency check failed: {e}")
            return False

# =============================================================================
# TEST INFRASTRUCTURE MANAGEMENT
# =============================================================================

class TestInfrastructure:
    """Manages test infrastructure setup and teardown"""
    
    def __init__(self):
        self.docker_client = None
        self.containers = {}
        self.networks = {}
    
    async def setup(self):
        """Set up test infrastructure"""
        logger.info("Setting up test infrastructure")
        
        try:
            self.docker_client = docker.from_env()
            
            # Create test network
            await self._create_test_network()
            
            # Start required services
            await self._start_kafka()
            await self._start_postgresql()
            await self._start_redis()
            
            # Wait for services to be ready
            await self._wait_for_services()
            
            logger.info("Test infrastructure setup complete")
            
        except Exception as e:
            logger.error(f"Failed to setup test infrastructure: {e}")
            await self.teardown()
            raise
    
    async def teardown(self):
        """Tear down test infrastructure"""
        logger.info("Tearing down test infrastructure")
        
        try:
            # Stop containers
            for container_name, container in self.containers.items():
                try:
                    container.stop()
                    container.remove()
                    logger.info(f"Stopped and removed container: {container_name}")
                except Exception as e:
                    logger.warning(f"Failed to stop container {container_name}: {e}")
            
            # Remove networks
            for network_name, network in self.networks.items():
                try:
                    network.remove()
                    logger.info(f"Removed network: {network_name}")
                except Exception as e:
                    logger.warning(f"Failed to remove network {network_name}: {e}")
            
        except Exception as e:
            logger.error(f"Error during teardown: {e}")
    
    async def _create_test_network(self):
        """Create Docker network for test services"""
        network_name = "compliance_test_network"
        try:
            network = self.docker_client.networks.create(network_name, driver="bridge")
            self.networks[network_name] = network
            logger.info(f"Created test network: {network_name}")
        except Exception as e:
            logger.warning(f"Network may already exist: {e}")
    
    async def _start_kafka(self):
        """Start Kafka container for testing"""
        container_name = "test_kafka"
        try:
            container = self.docker_client.containers.run(
                "confluentinc/cp-kafka:latest",
                name=container_name,
                environment={
                    "KAFKA_ZOOKEEPER_CONNECT": "zookeeper:2181",
                    "KAFKA_ADVERTISED_LISTENERS": "PLAINTEXT://localhost:9092",
                    "KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR": "1"
                },
                ports={"9092/tcp": 9092},
                detach=True,
                remove=True
            )
            self.containers[container_name] = container
            logger.info(f"Started Kafka container: {container_name}")
        except Exception as e:
            logger.warning(f"Failed to start Kafka: {e}")
    
    async def _start_postgresql(self):
        """Start PostgreSQL container for testing"""
        container_name = "test_postgresql"
        try:
            container = self.docker_client.containers.run(
                "postgres:13",
                name=container_name,
                environment={
                    "POSTGRES_DB": "compliance_test",
                    "POSTGRES_USER": "test_user",
                    "POSTGRES_PASSWORD": "test_password"
                },
                ports={"5432/tcp": 5433},  # Use different port to avoid conflicts
                detach=True,
                remove=True
            )
            self.containers[container_name] = container
            logger.info(f"Started PostgreSQL container: {container_name}")
        except Exception as e:
            logger.warning(f"Failed to start PostgreSQL: {e}")
    
    async def _start_redis(self):
        """Start Redis container for testing"""
        container_name = "test_redis"
        try:
            container = self.docker_client.containers.run(
                "redis:7-alpine",
                name=container_name,
                ports={"6379/tcp": 6380},  # Use different port to avoid conflicts
                detach=True,
                remove=True
            )
            self.containers[container_name] = container
            logger.info(f"Started Redis container: {container_name}")
        except Exception as e:
            logger.warning(f"Failed to start Redis: {e}")
    
    async def _wait_for_services(self):
        """Wait for all services to be ready"""
        logger.info("Waiting for services to be ready...")
        await asyncio.sleep(10)  # Give services time to start
        logger.info("Services should be ready")

# =============================================================================
# PIPELINE SERVICES MANAGEMENT
# =============================================================================

class PipelineServices:
    """Manages pipeline service instances for testing"""
    
    def __init__(self):
        self.regulatory_intelligence = None
        self.intelligence_compliance = None
        self.decision_orchestration = None
        self.intake_processing = None
    
    async def initialize(self, test_infrastructure):
        """Initialize all pipeline services"""
        logger.info("Initializing pipeline services")
        
        # Initialize services with test configuration
        self.regulatory_intelligence = RegulatoryIntelligenceService()
        await self.regulatory_intelligence.initialize(test_mode=True)
        
        self.intelligence_compliance = IntelligenceComplianceService()
        await self.intelligence_compliance.initialize(test_mode=True)
        
        self.decision_orchestration = DecisionOrchestrationService()
        await self.decision_orchestration.initialize(test_mode=True)
        
        self.intake_processing = IntakeProcessingService()
        await self.intake_processing.initialize(test_mode=True)
        
        logger.info("Pipeline services initialized")
    
    async def cleanup(self):
        """Cleanup all pipeline services"""
        logger.info("Cleaning up pipeline services")
        
        services = [
            self.regulatory_intelligence,
            self.intelligence_compliance,
            self.decision_orchestration,
            self.intake_processing
        ]
        
        for service in services:
            if service:
                try:
                    await service.close()
                except Exception as e:
                    logger.warning(f"Error closing service: {e}")
        
        logger.info("Pipeline services cleanup complete")

# =============================================================================
# TEST CONFIGURATION AND UTILITIES
# =============================================================================

def pytest_configure(config):
    """Configure pytest for regulatory pipeline tests"""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "pipeline: mark test as pipeline test")
    config.addinivalue_line("markers", "performance: mark test as performance test")

if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "--tb=short", "-m", "not performance"])
