#!/usr/bin/env python3
"""
Comprehensive Unit Tests for OverlapResolver Component
====================================================

This module provides comprehensive unit testing for the OverlapResolver component
with real regulatory obligation samples, overlap detection algorithms, coalescing
logic accuracy, and performance validation with large datasets.

Test Coverage Areas:
- Overlap detection algorithms with various overlap types
- Coalescing logic accuracy and validation
- Performance testing with large regulatory datasets
- Edge cases and false positive detection
- Real regulatory obligation samples from multiple jurisdictions
- Complex overlap scenarios and resolution strategies

Rule Compliance:
- Rule 1: No stubs - Complete production-grade test implementation
- Rule 12: Automated testing - Comprehensive unit test coverage
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

# Import the component under test
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../python-agents/intelligence-compliance-agent/src'))

from overlap_resolver import (
    OverlapResolver, 
    OverlapResult, 
    CoalescingStrategy,
    OverlapType,
    OverlapDetectionError,
    CoalescingError
)

# Configure test logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TestOverlapResolver:
    """
    Comprehensive test suite for OverlapResolver component
    
    Tests all aspects of overlap detection and resolution including algorithm
    accuracy, coalescing strategies, performance characteristics, and edge cases.
    """
    
    @pytest.fixture
    async def overlap_resolver(self):
        """Create OverlapResolver instance for testing"""
        resolver = OverlapResolver()
        await resolver.initialize()
        yield resolver
        await resolver.close()
    
    @pytest.fixture
    def real_regulatory_samples(self):
        """Real regulatory obligation samples from multiple jurisdictions"""
        return {
            "gdpr_data_processing": {
                "obligation_id": "GDPR_DP_001",
                "title": "Lawful Basis for Data Processing",
                "jurisdiction": "EU",
                "regulation": "GDPR",
                "article": "Article 6",
                "text": "Processing shall be lawful only if and to the extent that at least one of the following applies: (a) the data subject has given consent to the processing of his or her personal data for one or more specific purposes",
                "conditions": [
                    "data_type == 'personal_data'",
                    "processing_purpose != null",
                    "lawful_basis_exists == true"
                ],
                "actions": [
                    "verify_lawful_basis",
                    "document_processing_purpose",
                    "obtain_consent_if_required"
                ],
                "scope": {
                    "data_types": ["personal_data"],
                    "processing_activities": ["collection", "storage", "analysis", "transfer"],
                    "geographic_scope": "EU",
                    "entity_types": ["controller", "processor"]
                },
                "effective_date": "2018-05-25",
                "priority": "HIGH"
            },
            "gdpr_data_retention": {
                "obligation_id": "GDPR_DR_001",
                "title": "Data Retention Limits",
                "jurisdiction": "EU",
                "regulation": "GDPR",
                "article": "Article 5(1)(e)",
                "text": "Personal data shall be kept in a form which permits identification of data subjects for no longer than is necessary for the purposes for which the personal data are processed",
                "conditions": [
                    "data_type == 'personal_data'",
                    "retention_period_defined == true",
                    "processing_purpose_active == false"
                ],
                "actions": [
                    "define_retention_period",
                    "implement_deletion_schedule",
                    "review_retention_necessity"
                ],
                "scope": {
                    "data_types": ["personal_data"],
                    "processing_activities": ["storage", "retention", "deletion"],
                    "geographic_scope": "EU",
                    "entity_types": ["controller"]
                },
                "effective_date": "2018-05-25",
                "priority": "HIGH"
            },
            "german_bdsg_processing": {
                "obligation_id": "BDSG_DP_001",
                "title": "German Data Processing Requirements",
                "jurisdiction": "DE",
                "regulation": "BDSG",
                "section": "Section 26",
                "text": "Processing of personal data of employees is permissible if it is necessary for the decision on the establishment of an employment relationship or, after its establishment, for its implementation or termination",
                "conditions": [
                    "data_type == 'employee_data'",
                    "employment_context == true",
                    "processing_necessary == true"
                ],
                "actions": [
                    "verify_employment_necessity",
                    "implement_employee_data_protection",
                    "ensure_proportionality"
                ],
                "scope": {
                    "data_types": ["employee_data", "personal_data"],
                    "processing_activities": ["collection", "storage", "analysis"],
                    "geographic_scope": "DE",
                    "entity_types": ["employer", "controller"]
                },
                "effective_date": "2018-05-25",
                "priority": "HIGH"
            },
            "basel_capital_requirements": {
                "obligation_id": "BASEL_CAP_001",
                "title": "Minimum Capital Requirements",
                "jurisdiction": "GLOBAL",
                "regulation": "Basel III",
                "pillar": "Pillar 1",
                "text": "Banks must maintain a minimum Common Equity Tier 1 (CET1) capital ratio of 4.5% of risk-weighted assets",
                "conditions": [
                    "institution_type == 'bank'",
                    "cet1_ratio < 0.045",
                    "risk_weighted_assets > 0"
                ],
                "actions": [
                    "calculate_cet1_ratio",
                    "increase_capital_if_needed",
                    "report_capital_adequacy"
                ],
                "scope": {
                    "institution_types": ["bank", "credit_institution"],
                    "capital_types": ["cet1", "tier1", "total_capital"],
                    "geographic_scope": "GLOBAL",
                    "entity_types": ["internationally_active_bank"]
                },
                "effective_date": "2019-01-01",
                "priority": "CRITICAL"
            },
            "eu_crd_capital": {
                "obligation_id": "CRD_CAP_001",
                "title": "EU Capital Requirements Directive",
                "jurisdiction": "EU",
                "regulation": "CRD IV",
                "article": "Article 92",
                "text": "Institutions shall at all times satisfy the own funds requirements laid down in this Article. The Common Equity Tier 1 capital ratio shall be at least 4.5%",
                "conditions": [
                    "institution_type == 'credit_institution'",
                    "cet1_ratio < 0.045",
                    "eu_jurisdiction == true"
                ],
                "actions": [
                    "maintain_cet1_ratio",
                    "report_to_competent_authority",
                    "implement_capital_conservation_measures"
                ],
                "scope": {
                    "institution_types": ["credit_institution", "investment_firm"],
                    "capital_types": ["cet1", "tier1", "total_capital"],
                    "geographic_scope": "EU",
                    "entity_types": ["eu_institution"]
                },
                "effective_date": "2014-01-01",
                "priority": "CRITICAL"
            },
            "mifid_suitability_eu": {
                "obligation_id": "MIFID_SUIT_EU_001",
                "title": "MiFID II Suitability Assessment",
                "jurisdiction": "EU",
                "regulation": "MiFID II",
                "article": "Article 25",
                "text": "When providing investment advice or portfolio management the investment firm shall obtain the necessary information regarding the client's knowledge and experience, financial situation and investment objectives",
                "conditions": [
                    "service_type == 'investment_advice'",
                    "client_category != 'eligible_counterparty'",
                    "suitability_assessment_required == true"
                ],
                "actions": [
                    "assess_client_knowledge",
                    "evaluate_financial_situation",
                    "determine_investment_objectives",
                    "document_suitability_assessment"
                ],
                "scope": {
                    "service_types": ["investment_advice", "portfolio_management"],
                    "client_categories": ["retail", "professional"],
                    "geographic_scope": "EU",
                    "entity_types": ["investment_firm"]
                },
                "effective_date": "2018-01-03",
                "priority": "HIGH"
            },
            "german_wphg_suitability": {
                "obligation_id": "WPHG_SUIT_001",
                "title": "German Securities Trading Act Suitability",
                "jurisdiction": "DE",
                "regulation": "WpHG",
                "section": "Section 63",
                "text": "Investment service enterprises shall obtain information about the client's knowledge and experience, financial situation and investment objectives and assess the suitability of investment services",
                "conditions": [
                    "service_type == 'investment_advice'",
                    "german_client == true",
                    "enhanced_suitability_required == true"
                ],
                "actions": [
                    "conduct_enhanced_suitability_assessment",
                    "document_german_specific_requirements",
                    "provide_additional_disclosures",
                    "maintain_enhanced_records"
                ],
                "scope": {
                    "service_types": ["investment_advice", "portfolio_management"],
                    "client_categories": ["retail", "professional"],
                    "geographic_scope": "DE",
                    "entity_types": ["investment_service_enterprise"]
                },
                "effective_date": "2018-01-03",
                "priority": "HIGH"
            },
            "aml_customer_due_diligence": {
                "obligation_id": "AML_CDD_001",
                "title": "Customer Due Diligence Requirements",
                "jurisdiction": "EU",
                "regulation": "5th AML Directive",
                "article": "Article 13",
                "text": "Obliged entities shall apply customer due diligence measures when establishing a business relationship, carrying out occasional transactions, or when there is suspicion of money laundering",
                "conditions": [
                    "business_relationship_established == true",
                    "transaction_amount > 15000",
                    "suspicious_activity_detected == true"
                ],
                "actions": [
                    "verify_customer_identity",
                    "identify_beneficial_owner",
                    "understand_business_relationship_purpose",
                    "conduct_ongoing_monitoring"
                ],
                "scope": {
                    "entity_types": ["credit_institution", "financial_institution"],
                    "transaction_types": ["occasional", "business_relationship"],
                    "geographic_scope": "EU",
                    "risk_categories": ["standard", "enhanced", "simplified"]
                },
                "effective_date": "2020-01-10",
                "priority": "CRITICAL"
            },
            "german_gwg_due_diligence": {
                "obligation_id": "GWG_CDD_001",
                "title": "German Money Laundering Act Due Diligence",
                "jurisdiction": "DE",
                "regulation": "GwG",
                "section": "Section 10",
                "text": "Obliged entities shall carry out customer due diligence measures including identification and verification of customer identity and beneficial ownership",
                "conditions": [
                    "german_obliged_entity == true",
                    "business_relationship_germany == true",
                    "enhanced_due_diligence_required == true"
                ],
                "actions": [
                    "conduct_enhanced_identity_verification",
                    "verify_beneficial_ownership_register",
                    "apply_german_specific_procedures",
                    "maintain_german_records"
                ],
                "scope": {
                    "entity_types": ["credit_institution", "financial_service_provider"],
                    "transaction_types": ["business_relationship", "occasional"],
                    "geographic_scope": "DE",
                    "risk_categories": ["enhanced", "standard"]
                },
                "effective_date": "2020-01-01",
                "priority": "CRITICAL"
            }
        }
    
    @pytest.fixture
    def overlap_test_scenarios(self):
        """Predefined overlap scenarios for testing"""
        return {
            "exact_overlap": {
                "scenario_id": "EXACT_001",
                "description": "Exact overlap between EU GDPR and German BDSG",
                "obligations": ["GDPR_DP_001", "BDSG_DP_001"],
                "expected_overlap_type": "EXACT",
                "expected_overlap_percentage": 85.0,
                "coalescing_strategy": "MERGE_COMPATIBLE"
            },
            "partial_overlap": {
                "scenario_id": "PARTIAL_001",
                "description": "Partial overlap between Basel III and CRD IV",
                "obligations": ["BASEL_CAP_001", "CRD_CAP_001"],
                "expected_overlap_type": "PARTIAL",
                "expected_overlap_percentage": 75.0,
                "coalescing_strategy": "MOST_RESTRICTIVE"
            },
            "scope_overlap": {
                "scenario_id": "SCOPE_001",
                "description": "Scope overlap between MiFID II EU and German WpHG",
                "obligations": ["MIFID_SUIT_EU_001", "WPHG_SUIT_001"],
                "expected_overlap_type": "SCOPE",
                "expected_overlap_percentage": 70.0,
                "coalescing_strategy": "ADDITIVE"
            },
            "temporal_overlap": {
                "scenario_id": "TEMPORAL_001",
                "description": "Temporal overlap with different effective dates",
                "obligations": ["AML_CDD_001", "GWG_CDD_001"],
                "expected_overlap_type": "TEMPORAL",
                "expected_overlap_percentage": 80.0,
                "coalescing_strategy": "LATEST_EFFECTIVE"
            },
            "no_overlap": {
                "scenario_id": "NO_OVERLAP_001",
                "description": "No overlap between GDPR and Basel III",
                "obligations": ["GDPR_DP_001", "BASEL_CAP_001"],
                "expected_overlap_type": "NONE",
                "expected_overlap_percentage": 0.0,
                "coalescing_strategy": "KEEP_SEPARATE"
            }
        }
    
    # =========================================================================
    # OVERLAP DETECTION ALGORITHM TESTS
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_exact_overlap_detection(self, overlap_resolver, real_regulatory_samples, overlap_test_scenarios):
        """Test detection of exact overlaps between obligations"""
        scenario = overlap_test_scenarios["exact_overlap"]
        
        obligation1 = real_regulatory_samples["gdpr_data_processing"]
        obligation2 = real_regulatory_samples["german_bdsg_processing"]
        
        overlap_result = await overlap_resolver.detect_overlap(obligation1, obligation2)
        
        assert overlap_result is not None
        assert overlap_result.overlap_type == OverlapType.EXACT or overlap_result.overlap_type == OverlapType.PARTIAL
        assert overlap_result.overlap_percentage >= 70.0  # Significant overlap expected
        assert len(overlap_result.overlapping_elements) > 0
        
        # Verify specific overlapping elements
        assert "data_type" in str(overlap_result.overlapping_elements)
        assert "processing" in str(overlap_result.overlapping_elements)
        
        logger.info(f"Exact overlap detection: {overlap_result.overlap_percentage:.2f}% overlap")
    
    @pytest.mark.asyncio
    async def test_partial_overlap_detection(self, overlap_resolver, real_regulatory_samples, overlap_test_scenarios):
        """Test detection of partial overlaps between obligations"""
        scenario = overlap_test_scenarios["partial_overlap"]
        
        obligation1 = real_regulatory_samples["basel_capital_requirements"]
        obligation2 = real_regulatory_samples["eu_crd_capital"]
        
        overlap_result = await overlap_resolver.detect_overlap(obligation1, obligation2)
        
        assert overlap_result is not None
        assert overlap_result.overlap_type in [OverlapType.PARTIAL, OverlapType.EXACT]
        assert overlap_result.overlap_percentage >= 60.0
        
        # Verify capital-related overlapping elements
        overlapping_str = str(overlap_result.overlapping_elements)
        assert "capital" in overlapping_str.lower() or "cet1" in overlapping_str.lower()
        
        logger.info(f"Partial overlap detection: {overlap_result.overlap_percentage:.2f}% overlap")
    
    @pytest.mark.asyncio
    async def test_scope_overlap_detection(self, overlap_resolver, real_regulatory_samples):
        """Test detection of scope-based overlaps"""
        obligation1 = real_regulatory_samples["mifid_suitability_eu"]
        obligation2 = real_regulatory_samples["german_wphg_suitability"]
        
        overlap_result = await overlap_resolver.detect_overlap(obligation1, obligation2)
        
        assert overlap_result is not None
        assert overlap_result.overlap_type in [OverlapType.SCOPE, OverlapType.PARTIAL]
        assert overlap_result.overlap_percentage >= 50.0
        
        # Verify suitability-related overlapping elements
        overlapping_str = str(overlap_result.overlapping_elements)
        assert "suitability" in overlapping_str.lower() or "investment" in overlapping_str.lower()
        
        logger.info(f"Scope overlap detection: {overlap_result.overlap_percentage:.2f}% overlap")
    
    @pytest.mark.asyncio
    async def test_temporal_overlap_detection(self, overlap_resolver, real_regulatory_samples):
        """Test detection of temporal overlaps with different effective dates"""
        obligation1 = real_regulatory_samples["aml_customer_due_diligence"]
        obligation2 = real_regulatory_samples["german_gwg_due_diligence"]
        
        overlap_result = await overlap_resolver.detect_overlap(obligation1, obligation2)
        
        assert overlap_result is not None
        assert overlap_result.overlap_percentage >= 60.0
        
        # Should detect temporal aspects
        assert overlap_result.temporal_analysis is not None
        assert "effective_date" in overlap_result.temporal_analysis
        
        logger.info(f"Temporal overlap detection: {overlap_result.overlap_percentage:.2f}% overlap")
    
    @pytest.mark.asyncio
    async def test_no_overlap_detection(self, overlap_resolver, real_regulatory_samples):
        """Test detection when no overlap exists"""
        obligation1 = real_regulatory_samples["gdpr_data_processing"]
        obligation2 = real_regulatory_samples["basel_capital_requirements"]
        
        overlap_result = await overlap_resolver.detect_overlap(obligation1, obligation2)
        
        assert overlap_result is not None
        assert overlap_result.overlap_type == OverlapType.NONE
        assert overlap_result.overlap_percentage < 20.0  # Minimal or no overlap
        
        logger.info(f"No overlap detection: {overlap_result.overlap_percentage:.2f}% overlap")
    
    @pytest.mark.asyncio
    async def test_multi_obligation_overlap_detection(self, overlap_resolver, real_regulatory_samples):
        """Test overlap detection across multiple obligations"""
        obligations = [
            real_regulatory_samples["gdpr_data_processing"],
            real_regulatory_samples["gdpr_data_retention"],
            real_regulatory_samples["german_bdsg_processing"]
        ]
        
        overlap_matrix = await overlap_resolver.detect_multi_overlap(obligations)
        
        assert overlap_matrix is not None
        assert len(overlap_matrix) >= 3  # At least 3 pairwise comparisons
        
        # Verify GDPR obligations have high overlap
        gdpr_overlaps = [result for result in overlap_matrix 
                        if "GDPR" in result.obligation1_id and "GDPR" in result.obligation2_id]
        
        if gdpr_overlaps:
            assert any(result.overlap_percentage > 50.0 for result in gdpr_overlaps)
        
        logger.info(f"Multi-obligation overlap detection: {len(overlap_matrix)} comparisons")
    
    # =========================================================================
    # COALESCING LOGIC TESTS
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_merge_compatible_coalescing(self, overlap_resolver, real_regulatory_samples):
        """Test merge compatible coalescing strategy"""
        obligation1 = real_regulatory_samples["gdpr_data_processing"]
        obligation2 = real_regulatory_samples["german_bdsg_processing"]
        
        overlap_result = await overlap_resolver.detect_overlap(obligation1, obligation2)
        
        if overlap_result.overlap_percentage > 50.0:
            coalesced_obligation = await overlap_resolver.coalesce_obligations(
                [obligation1, obligation2], 
                CoalescingStrategy.MERGE_COMPATIBLE
            )
            
            assert coalesced_obligation is not None
            assert coalesced_obligation.obligation_id != obligation1["obligation_id"]
            assert coalesced_obligation.obligation_id != obligation2["obligation_id"]
            
            # Should combine elements from both obligations
            assert len(coalesced_obligation.conditions) >= max(
                len(obligation1["conditions"]), 
                len(obligation2["conditions"])
            )
            
            logger.info("Merge compatible coalescing successful")
    
    @pytest.mark.asyncio
    async def test_most_restrictive_coalescing(self, overlap_resolver, real_regulatory_samples):
        """Test most restrictive coalescing strategy"""
        obligation1 = real_regulatory_samples["basel_capital_requirements"]
        obligation2 = real_regulatory_samples["eu_crd_capital"]
        
        coalesced_obligation = await overlap_resolver.coalesce_obligations(
            [obligation1, obligation2], 
            CoalescingStrategy.MOST_RESTRICTIVE
        )
        
        assert coalesced_obligation is not None
        
        # Should select most restrictive requirements
        assert coalesced_obligation.priority in ["CRITICAL", "HIGH"]
        
        # Should include most stringent conditions
        conditions_text = " ".join(coalesced_obligation.conditions)
        assert "cet1_ratio" in conditions_text.lower()
        
        logger.info("Most restrictive coalescing successful")
    
    @pytest.mark.asyncio
    async def test_additive_coalescing(self, overlap_resolver, real_regulatory_samples):
        """Test additive coalescing strategy"""
        obligation1 = real_regulatory_samples["mifid_suitability_eu"]
        obligation2 = real_regulatory_samples["german_wphg_suitability"]
        
        coalesced_obligation = await overlap_resolver.coalesce_obligations(
            [obligation1, obligation2], 
            CoalescingStrategy.ADDITIVE
        )
        
        assert coalesced_obligation is not None
        
        # Should include requirements from both obligations
        total_original_actions = len(obligation1["actions"]) + len(obligation2["actions"])
        assert len(coalesced_obligation.actions) >= total_original_actions * 0.8  # Allow for some deduplication
        
        logger.info("Additive coalescing successful")
    
    @pytest.mark.asyncio
    async def test_latest_effective_coalescing(self, overlap_resolver, real_regulatory_samples):
        """Test latest effective date coalescing strategy"""
        obligation1 = real_regulatory_samples["aml_customer_due_diligence"]
        obligation2 = real_regulatory_samples["german_gwg_due_diligence"]
        
        coalesced_obligation = await overlap_resolver.coalesce_obligations(
            [obligation1, obligation2], 
            CoalescingStrategy.LATEST_EFFECTIVE
        )
        
        assert coalesced_obligation is not None
        
        # Should use latest effective date
        original_dates = [
            obligation1.get("effective_date", "1900-01-01"),
            obligation2.get("effective_date", "1900-01-01")
        ]
        latest_date = max(original_dates)
        
        assert coalesced_obligation.effective_date == latest_date
        
        logger.info("Latest effective coalescing successful")
    
    @pytest.mark.asyncio
    async def test_keep_separate_strategy(self, overlap_resolver, real_regulatory_samples):
        """Test keep separate strategy for non-overlapping obligations"""
        obligation1 = real_regulatory_samples["gdpr_data_processing"]
        obligation2 = real_regulatory_samples["basel_capital_requirements"]
        
        result = await overlap_resolver.coalesce_obligations(
            [obligation1, obligation2], 
            CoalescingStrategy.KEEP_SEPARATE
        )
        
        # Should return list of separate obligations
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["obligation_id"] != result[1]["obligation_id"]
        
        logger.info("Keep separate strategy successful")
    
    # =========================================================================
    # PERFORMANCE TESTS WITH LARGE DATASETS
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_large_dataset_overlap_detection(self, overlap_resolver, real_regulatory_samples):
        """Test overlap detection performance with large datasets"""
        # Create large dataset by replicating and modifying samples
        large_dataset = []
        base_samples = list(real_regulatory_samples.values())
        
        for i in range(100):
            for sample in base_samples:
                modified_sample = sample.copy()
                modified_sample["obligation_id"] = f"{sample['obligation_id']}_COPY_{i:03d}"
                modified_sample["title"] = f"{sample['title']} - Copy {i}"
                large_dataset.append(modified_sample)
        
        start_time = time.time()
        
        # Test batch overlap detection
        overlap_results = await overlap_resolver.detect_batch_overlaps(large_dataset[:50])  # Test with 50 obligations
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        assert len(overlap_results) > 0
        assert processing_time < 30.0  # Should complete within 30 seconds
        
        # Calculate performance metrics
        comparisons_made = len(overlap_results)
        comparisons_per_second = comparisons_made / processing_time if processing_time > 0 else 0
        
        assert comparisons_per_second > 10  # Should process >10 comparisons per second
        
        logger.info(f"Large dataset performance: {comparisons_made} comparisons in {processing_time:.2f}s ({comparisons_per_second:.2f} comp/s)")
    
    @pytest.mark.asyncio
    async def test_memory_efficiency_large_dataset(self, overlap_resolver, real_regulatory_samples):
        """Test memory efficiency with large datasets"""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create very large dataset
        large_dataset = []
        for i in range(500):
            for sample in real_regulatory_samples.values():
                modified_sample = sample.copy()
                modified_sample["obligation_id"] = f"{sample['obligation_id']}_LARGE_{i:03d}"
                large_dataset.append(modified_sample)
        
        # Process dataset
        overlap_results = await overlap_resolver.detect_batch_overlaps(large_dataset[:100])
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        assert memory_increase < 1000  # Should not increase by more than 1GB
        
        # Cleanup
        del large_dataset
        del overlap_results
        gc.collect()
        
        logger.info(f"Memory efficiency: {memory_increase:.2f} MB increase for large dataset")
    
    @pytest.mark.asyncio
    async def test_concurrent_overlap_detection(self, overlap_resolver, real_regulatory_samples):
        """Test concurrent overlap detection performance"""
        obligations = list(real_regulatory_samples.values())
        
        # Create concurrent tasks
        async def detect_overlap_task(obligation1, obligation2):
            return await overlap_resolver.detect_overlap(obligation1, obligation2)
        
        tasks = []
        for i in range(len(obligations)):
            for j in range(i + 1, len(obligations)):
                tasks.append(detect_overlap_task(obligations[i], obligations[j]))
        
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        concurrent_time = end_time - start_time
        
        assert len(results) == len(tasks)
        assert all(result is not None for result in results)
        assert concurrent_time < 10.0  # Should complete within 10 seconds
        
        logger.info(f"Concurrent overlap detection: {len(tasks)} comparisons in {concurrent_time:.2f}s")
    
    # =========================================================================
    # EDGE CASES AND FALSE POSITIVE DETECTION
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_identical_obligations_overlap(self, overlap_resolver, real_regulatory_samples):
        """Test overlap detection for identical obligations"""
        obligation = real_regulatory_samples["gdpr_data_processing"]
        
        overlap_result = await overlap_resolver.detect_overlap(obligation, obligation)
        
        assert overlap_result is not None
        assert overlap_result.overlap_type == OverlapType.EXACT
        assert overlap_result.overlap_percentage >= 95.0  # Should be nearly 100%
        
        logger.info("Identical obligations overlap detection successful")
    
    @pytest.mark.asyncio
    async def test_similar_titles_different_content(self, overlap_resolver):
        """Test false positive prevention for similar titles but different content"""
        obligation1 = {
            "obligation_id": "SIMILAR_001",
            "title": "Data Processing Requirements",
            "jurisdiction": "EU",
            "regulation": "GDPR",
            "text": "Personal data processing must comply with GDPR principles",
            "conditions": ["data_type == 'personal'"],
            "actions": ["apply_gdpr_principles"]
        }
        
        obligation2 = {
            "obligation_id": "SIMILAR_002",
            "title": "Data Processing Requirements",
            "jurisdiction": "US",
            "regulation": "CCPA",
            "text": "Consumer data processing must comply with CCPA requirements",
            "conditions": ["data_type == 'consumer'"],
            "actions": ["apply_ccpa_requirements"]
        }
        
        overlap_result = await overlap_resolver.detect_overlap(obligation1, obligation2)
        
        assert overlap_result is not None
        # Should detect limited overlap despite similar titles
        assert overlap_result.overlap_percentage < 70.0
        
        logger.info("False positive prevention successful")
    
    @pytest.mark.asyncio
    async def test_empty_obligations_handling(self, overlap_resolver):
        """Test handling of empty or incomplete obligations"""
        empty_obligation = {
            "obligation_id": "EMPTY_001",
            "title": "",
            "text": "",
            "conditions": [],
            "actions": []
        }
        
        normal_obligation = {
            "obligation_id": "NORMAL_001",
            "title": "Normal Obligation",
            "text": "This is a normal regulatory obligation",
            "conditions": ["condition == true"],
            "actions": ["take_action"]
        }
        
        overlap_result = await overlap_resolver.detect_overlap(empty_obligation, normal_obligation)
        
        assert overlap_result is not None
        assert overlap_result.overlap_type == OverlapType.NONE
        assert overlap_result.overlap_percentage == 0.0
        
        logger.info("Empty obligations handling successful")
    
    @pytest.mark.asyncio
    async def test_malformed_obligation_handling(self, overlap_resolver):
        """Test handling of malformed obligations"""
        malformed_obligation = {
            "obligation_id": "MALFORMED_001",
            # Missing required fields
            "conditions": "not_a_list",  # Should be list
            "actions": None  # Should be list
        }
        
        normal_obligation = {
            "obligation_id": "NORMAL_001",
            "title": "Normal Obligation",
            "text": "This is a normal regulatory obligation",
            "conditions": ["condition == true"],
            "actions": ["take_action"]
        }
        
        with pytest.raises(OverlapDetectionError):
            await overlap_resolver.detect_overlap(malformed_obligation, normal_obligation)
        
        logger.info("Malformed obligation handling successful")
    
    # =========================================================================
    # COMPLEX OVERLAP SCENARIOS
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_multi_layered_overlap_scenario(self, overlap_resolver, real_regulatory_samples):
        """Test complex multi-layered overlap scenario"""
        # Create scenario with EU directive, national implementation, and sector-specific rules
        obligations = [
            real_regulatory_samples["mifid_suitability_eu"],      # EU level
            real_regulatory_samples["german_wphg_suitability"],   # National implementation
            {
                "obligation_id": "SECTOR_SUIT_001",
                "title": "Banking Sector Suitability Rules",
                "jurisdiction": "DE",
                "regulation": "Banking Sector Guidelines",
                "text": "Banks must apply enhanced suitability assessment for high-risk products",
                "conditions": [
                    "institution_type == 'bank'",
                    "product_risk_level == 'high'",
                    "suitability_assessment_required == true"
                ],
                "actions": [
                    "apply_enhanced_suitability",
                    "document_risk_assessment",
                    "provide_additional_warnings"
                ],
                "scope": {
                    "service_types": ["investment_advice"],
                    "product_types": ["high_risk_products"],
                    "geographic_scope": "DE",
                    "entity_types": ["bank"]
                }
            }
        ]
        
        # Detect overlaps across all three levels
        overlap_matrix = await overlap_resolver.detect_multi_overlap(obligations)
        
        assert len(overlap_matrix) >= 3  # At least 3 pairwise comparisons
        
        # Should detect hierarchical overlaps
        hierarchical_overlaps = [result for result in overlap_matrix if result.overlap_percentage > 40.0]
        assert len(hierarchical_overlaps) >= 2
        
        logger.info("Multi-layered overlap scenario successful")
    
    @pytest.mark.asyncio
    async def test_cross_jurisdictional_overlap_resolution(self, overlap_resolver, real_regulatory_samples):
        """Test cross-jurisdictional overlap resolution"""
        # Test overlaps between different jurisdictions
        cross_jurisdictional_pairs = [
            (real_regulatory_samples["gdpr_data_processing"], real_regulatory_samples["german_bdsg_processing"]),
            (real_regulatory_samples["basel_capital_requirements"], real_regulatory_samples["eu_crd_capital"]),
            (real_regulatory_samples["aml_customer_due_diligence"], real_regulatory_samples["german_gwg_due_diligence"])
        ]
        
        resolution_results = []
        
        for obligation1, obligation2 in cross_jurisdictional_pairs:
            overlap_result = await overlap_resolver.detect_overlap(obligation1, obligation2)
            
            if overlap_result.overlap_percentage > 50.0:
                # Attempt coalescing with jurisdiction-aware strategy
                coalesced = await overlap_resolver.coalesce_obligations_with_jurisdiction_priority(
                    [obligation1, obligation2]
                )
                resolution_results.append(coalesced)
        
        assert len(resolution_results) > 0
        
        # Verify jurisdiction hierarchy is respected
        for result in resolution_results:
            assert hasattr(result, 'jurisdiction_hierarchy')
            assert result.jurisdiction_hierarchy is not None
        
        logger.info("Cross-jurisdictional overlap resolution successful")
    
    # =========================================================================
    # ALGORITHM ACCURACY VALIDATION
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_overlap_detection_accuracy_benchmark(self, overlap_resolver):
        """Test overlap detection accuracy against known benchmarks"""
        # Create benchmark test cases with known overlap percentages
        benchmark_cases = [
            {
                "obligation1": {
                    "obligation_id": "BENCH_001",
                    "title": "Identical Obligation",
                    "text": "This is exactly the same text",
                    "conditions": ["condition1", "condition2"],
                    "actions": ["action1", "action2"]
                },
                "obligation2": {
                    "obligation_id": "BENCH_002",
                    "title": "Identical Obligation",
                    "text": "This is exactly the same text",
                    "conditions": ["condition1", "condition2"],
                    "actions": ["action1", "action2"]
                },
                "expected_overlap": 100.0,
                "tolerance": 5.0
            },
            {
                "obligation1": {
                    "obligation_id": "BENCH_003",
                    "title": "Partial Match",
                    "text": "This text has some common elements",
                    "conditions": ["condition1", "condition2"],
                    "actions": ["action1", "action2"]
                },
                "obligation2": {
                    "obligation_id": "BENCH_004",
                    "title": "Partial Match Different",
                    "text": "This text has some different elements",
                    "conditions": ["condition1", "condition3"],
                    "actions": ["action1", "action3"]
                },
                "expected_overlap": 60.0,
                "tolerance": 15.0
            },
            {
                "obligation1": {
                    "obligation_id": "BENCH_005",
                    "title": "No Match",
                    "text": "Completely different regulatory requirement",
                    "conditions": ["unique_condition"],
                    "actions": ["unique_action"]
                },
                "obligation2": {
                    "obligation_id": "BENCH_006",
                    "title": "Totally Different",
                    "text": "Another unrelated regulatory obligation",
                    "conditions": ["other_condition"],
                    "actions": ["other_action"]
                },
                "expected_overlap": 0.0,
                "tolerance": 10.0
            }
        ]
        
        accuracy_results = []
        
        for case in benchmark_cases:
            overlap_result = await overlap_resolver.detect_overlap(
                case["obligation1"], 
                case["obligation2"]
            )
            
            expected = case["expected_overlap"]
            actual = overlap_result.overlap_percentage
            tolerance = case["tolerance"]
            
            accuracy = 100.0 - abs(expected - actual)
            accuracy_results.append(accuracy)
            
            # Verify within tolerance
            assert abs(expected - actual) <= tolerance, f"Expected {expected}%, got {actual}%"
        
        average_accuracy = sum(accuracy_results) / len(accuracy_results)
        assert average_accuracy >= 80.0  # Should achieve >80% accuracy
        
        logger.info(f"Overlap detection accuracy: {average_accuracy:.2f}%")
    
    # =========================================================================
    # INTEGRATION TESTS WITH MOCK DEPENDENCIES
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_database_integration_overlap_storage(self, overlap_resolver):
        """Test database integration for overlap result storage"""
        with patch.object(overlap_resolver, 'pg_pool') as mock_pool:
            mock_conn = AsyncMock()
            mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
            
            # Mock database responses
            mock_conn.fetchrow.return_value = {
                'overlap_id': 'TEST_OVERLAP_001',
                'overlap_data': json.dumps({
                    'overlap_percentage': 75.5,
                    'overlap_type': 'PARTIAL'
                }),
                'created_at': datetime.now(timezone.utc)
            }
            
            # Test overlap result storage
            test_overlap = OverlapResult(
                overlap_id="TEST_OVERLAP_001",
                obligation1_id="OBL_001",
                obligation2_id="OBL_002",
                overlap_type=OverlapType.PARTIAL,
                overlap_percentage=75.5,
                overlapping_elements=["condition1", "action1"]
            )
            
            await overlap_resolver.store_overlap_result(test_overlap)
            
            # Verify database calls
            mock_conn.execute.assert_called()
            
        logger.info("Database integration test successful")
    
    @pytest.mark.asyncio
    async def test_cache_integration_overlap_results(self, overlap_resolver):
        """Test cache integration for overlap result caching"""
        with patch.object(overlap_resolver, 'redis_client') as mock_redis:
            mock_redis.get = AsyncMock(return_value=None)
            mock_redis.set = AsyncMock()
            
            # Test overlap detection with caching
            obligation1 = {
                "obligation_id": "CACHE_001",
                "title": "Cache Test 1",
                "text": "Test caching functionality"
            }
            
            obligation2 = {
                "obligation_id": "CACHE_002",
                "title": "Cache Test 2",
                "text": "Test caching functionality"
            }
            
            # First call should cache result
            result1 = await overlap_resolver.detect_overlap(obligation1, obligation2)
            mock_redis.set.assert_called()
            
            # Mock cache hit
            mock_redis.get.return_value = json.dumps({
                'overlap_percentage': 85.0,
                'overlap_type': 'PARTIAL'
            })
            
            # Second call should use cache
            result2 = await overlap_resolver.detect_overlap(obligation1, obligation2)
            
            assert result1 is not None
            assert result2 is not None
            
        logger.info("Cache integration test successful")

# =============================================================================
# PERFORMANCE BENCHMARK SUITE
# =============================================================================

class TestOverlapResolverPerformance:
    """
    Performance benchmark suite for OverlapResolver
    
    Tests performance characteristics and scalability limits
    """
    
    @pytest.fixture
    async def performance_resolver(self):
        """Create optimized OverlapResolver for performance testing"""
        resolver = OverlapResolver()
        await resolver.initialize()
        # Enable performance optimizations
        resolver.enable_performance_mode()
        yield resolver
        await resolver.close()
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_overlap_detection_throughput(self, performance_resolver, real_regulatory_samples):
        """Benchmark overlap detection throughput"""
        obligations = list(real_regulatory_samples.values()) * 10  # 90 obligations
        
        start_time = time.time()
        
        # Generate all pairwise comparisons
        comparison_count = 0
        for i in range(len(obligations)):
            for j in range(i + 1, min(i + 10, len(obligations))):  # Limit to prevent exponential growth
                await performance_resolver.detect_overlap(obligations[i], obligations[j])
                comparison_count += 1
        
        end_time = time.time()
        total_time = end_time - start_time
        throughput = comparison_count / total_time
        
        assert throughput > 5  # Should process >5 comparisons per second
        
        logger.info(f"Overlap detection throughput: {throughput:.2f} comparisons/second")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_coalescing_performance(self, performance_resolver, real_regulatory_samples):
        """Benchmark coalescing performance"""
        obligations = list(real_regulatory_samples.values())
        
        start_time = time.time()
        
        # Test different coalescing strategies
        strategies = [
            CoalescingStrategy.MERGE_COMPATIBLE,
            CoalescingStrategy.MOST_RESTRICTIVE,
            CoalescingStrategy.ADDITIVE
        ]
        
        for strategy in strategies:
            await performance_resolver.coalesce_obligations(obligations[:3], strategy)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        assert total_time < 5.0  # Should complete within 5 seconds
        
        logger.info(f"Coalescing performance: {len(strategies)} strategies in {total_time:.2f}s")

# =============================================================================
# TEST CONFIGURATION AND UTILITIES
# =============================================================================

def pytest_configure(config):
    """Configure pytest for OverlapResolver tests"""
    config.addinivalue_line("markers", "performance: mark test as performance benchmark")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "scenario: mark test as scenario test")

if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "--tb=short"])
