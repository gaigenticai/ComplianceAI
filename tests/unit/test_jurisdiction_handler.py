#!/usr/bin/env python3
"""
Comprehensive Unit Tests for JurisdictionHandler Component
========================================================

This module provides comprehensive unit testing for the JurisdictionHandler component
with complete jurisdiction scenario coverage, precedence resolution testing, and
conflict resolution validation.

Test Coverage Areas:
- All supported jurisdictions (EU, DE, IE, FR, US, UK, etc.)
- Precedence resolution logic and hierarchy
- Conflict resolution scenarios and edge cases
- Invalid jurisdiction handling and error recovery
- Multi-jurisdiction customer scenarios
- Cross-border regulatory compliance

Rule Compliance:
- Rule 1: No stubs - Complete production-grade test implementation
- Rule 12: Automated testing - Comprehensive unit test coverage
- Rule 17: Code documentation - Extensive test documentation
"""

import pytest
import asyncio
import json
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List, Any, Optional, Set
import logging

# Import the component under test
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../python-agents/intelligence-compliance-agent/src'))

from jurisdiction_handler import (
    JurisdictionHandler, 
    JurisdictionConfig, 
    JurisdictionConflict, 
    JurisdictionPrecedence,
    InvalidJurisdictionError,
    ConflictResolutionError
)

# Configure test logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TestJurisdictionHandler:
    """
    Comprehensive test suite for JurisdictionHandler component
    
    Tests all aspects of jurisdiction handling including precedence resolution,
    conflict detection, multi-jurisdiction scenarios, and error handling.
    """
    
    @pytest.fixture
    async def jurisdiction_handler(self):
        """Create JurisdictionHandler instance for testing"""
        handler = JurisdictionHandler()
        await handler.initialize()
        yield handler
        await handler.close()
    
    @pytest.fixture
    def jurisdiction_configs(self):
        """Sample jurisdiction configurations for testing"""
        return {
            "EU": {
                "jurisdiction_code": "EU",
                "jurisdiction_name": "European Union",
                "jurisdiction_type": "SUPRANATIONAL",
                "parent_jurisdiction": None,
                "precedence_level": 1,
                "languages": ["en", "de", "fr", "es", "it"],
                "regulatory_authorities": ["EBA", "ECB", "ESMA", "EIOPA"],
                "applicable_regulations": ["GDPR", "MiFID II", "Basel III", "CRD IV", "DORA"],
                "effective_date": "1993-11-01",
                "is_active": True,
                "metadata": {
                    "currency": "EUR",
                    "timezone": "CET",
                    "business_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
                    "holidays": ["new_year", "easter", "christmas"]
                }
            },
            "DE": {
                "jurisdiction_code": "DE",
                "jurisdiction_name": "Germany",
                "jurisdiction_type": "NATIONAL",
                "parent_jurisdiction": "EU",
                "precedence_level": 2,
                "languages": ["de", "en"],
                "regulatory_authorities": ["BaFin", "Bundesbank"],
                "applicable_regulations": ["KWG", "VAG", "WpHG", "GwG", "GDPR"],
                "effective_date": "1949-05-23",
                "is_active": True,
                "metadata": {
                    "currency": "EUR",
                    "timezone": "CET",
                    "business_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
                    "holidays": ["new_year", "epiphany", "easter", "labor_day", "christmas", "boxing_day"]
                }
            },
            "IE": {
                "jurisdiction_code": "IE",
                "jurisdiction_name": "Ireland",
                "jurisdiction_type": "NATIONAL",
                "parent_jurisdiction": "EU",
                "precedence_level": 2,
                "languages": ["en", "ga"],
                "regulatory_authorities": ["Central Bank of Ireland"],
                "applicable_regulations": ["Central Bank Acts", "GDPR", "MiFID II"],
                "effective_date": "1922-12-06",
                "is_active": True,
                "metadata": {
                    "currency": "EUR",
                    "timezone": "GMT",
                    "business_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
                    "holidays": ["new_year", "st_patrick", "easter", "christmas"]
                }
            },
            "US": {
                "jurisdiction_code": "US",
                "jurisdiction_name": "United States",
                "jurisdiction_type": "NATIONAL",
                "parent_jurisdiction": None,
                "precedence_level": 1,
                "languages": ["en"],
                "regulatory_authorities": ["Fed", "FDIC", "OCC", "SEC", "CFTC"],
                "applicable_regulations": ["Dodd-Frank", "BSA", "FCRA", "GLBA"],
                "effective_date": "1776-07-04",
                "is_active": True,
                "metadata": {
                    "currency": "USD",
                    "timezone": "EST",
                    "business_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
                    "holidays": ["new_year", "independence_day", "thanksgiving", "christmas"]
                }
            },
            "UK": {
                "jurisdiction_code": "UK",
                "jurisdiction_name": "United Kingdom",
                "jurisdiction_type": "NATIONAL",
                "parent_jurisdiction": None,
                "precedence_level": 1,
                "languages": ["en"],
                "regulatory_authorities": ["FCA", "PRA", "Bank of England"],
                "applicable_regulations": ["FSMA", "UK GDPR", "UK MiFID"],
                "effective_date": "2021-01-01",  # Post-Brexit
                "is_active": True,
                "metadata": {
                    "currency": "GBP",
                    "timezone": "GMT",
                    "business_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
                    "holidays": ["new_year", "easter", "christmas", "boxing_day"]
                }
            }
        }
    
    @pytest.fixture
    def sample_obligations(self):
        """Sample regulatory obligations for jurisdiction testing"""
        return {
            "eu_gdpr": {
                "obligation_id": "GDPR_001",
                "title": "Data Subject Rights",
                "jurisdiction": "EU",
                "regulation": "GDPR",
                "precedence": 1,
                "text": "Controllers shall provide information on action taken within one month",
                "conditions": ["data_subject_request == true"],
                "actions": ["process_request", "provide_response"]
            },
            "de_kwg": {
                "obligation_id": "KWG_001",
                "title": "German Banking License",
                "jurisdiction": "DE",
                "regulation": "KWG",
                "precedence": 2,
                "text": "Credit institutions require authorization from BaFin",
                "conditions": ["institution_type == 'credit_institution'", "jurisdiction == 'DE'"],
                "actions": ["verify_bafin_license", "check_authorization"]
            },
            "ie_central_bank": {
                "obligation_id": "CBI_001",
                "title": "Irish Banking Requirements",
                "jurisdiction": "IE",
                "regulation": "Central Bank Acts",
                "precedence": 2,
                "text": "Banks must comply with Central Bank of Ireland requirements",
                "conditions": ["institution_type == 'bank'", "jurisdiction == 'IE'"],
                "actions": ["verify_cbi_compliance", "submit_returns"]
            },
            "us_bsa": {
                "obligation_id": "BSA_001",
                "title": "Bank Secrecy Act Compliance",
                "jurisdiction": "US",
                "regulation": "BSA",
                "precedence": 1,
                "text": "Financial institutions must report suspicious activities",
                "conditions": ["transaction_amount > 10000", "jurisdiction == 'US'"],
                "actions": ["file_sar", "maintain_records"]
            },
            "uk_fsma": {
                "obligation_id": "FSMA_001",
                "title": "UK Financial Services Authorization",
                "jurisdiction": "UK",
                "regulation": "FSMA",
                "precedence": 1,
                "text": "Financial services require FCA authorization",
                "conditions": ["provides_financial_services == true", "jurisdiction == 'UK'"],
                "actions": ["verify_fca_authorization", "check_permissions"]
            }
        }
    
    @pytest.fixture
    def conflict_scenarios(self):
        """Conflict scenarios for testing resolution logic"""
        return {
            "eu_vs_national_privacy": {
                "scenario_id": "CONFLICT_001",
                "description": "EU GDPR vs National Privacy Laws",
                "conflicting_obligations": [
                    {
                        "obligation_id": "GDPR_RETENTION",
                        "jurisdiction": "EU",
                        "regulation": "GDPR",
                        "requirement": "Data retention maximum 6 years",
                        "precedence": 1
                    },
                    {
                        "obligation_id": "DE_RETENTION",
                        "jurisdiction": "DE",
                        "regulation": "HGB",
                        "requirement": "Business records retention 10 years",
                        "precedence": 2
                    }
                ],
                "expected_resolution": "Apply most restrictive (GDPR 6 years for personal data, HGB 10 years for business records)"
            },
            "mifid_implementation": {
                "scenario_id": "CONFLICT_002",
                "description": "MiFID II EU Directive vs National Implementation",
                "conflicting_obligations": [
                    {
                        "obligation_id": "MIFID_EU",
                        "jurisdiction": "EU",
                        "regulation": "MiFID II",
                        "requirement": "Suitability assessment required",
                        "precedence": 1
                    },
                    {
                        "obligation_id": "MIFID_DE",
                        "jurisdiction": "DE",
                        "regulation": "WpHG",
                        "requirement": "Enhanced suitability assessment with additional documentation",
                        "precedence": 2
                    }
                ],
                "expected_resolution": "Apply enhanced German requirements (more restrictive)"
            },
            "cross_border_reporting": {
                "scenario_id": "CONFLICT_003",
                "description": "Cross-border reporting requirements",
                "conflicting_obligations": [
                    {
                        "obligation_id": "EU_REPORTING",
                        "jurisdiction": "EU",
                        "regulation": "CRD IV",
                        "requirement": "Quarterly reporting to EBA",
                        "precedence": 1
                    },
                    {
                        "obligation_id": "IE_REPORTING",
                        "jurisdiction": "IE",
                        "regulation": "Central Bank Acts",
                        "requirement": "Monthly reporting to Central Bank of Ireland",
                        "precedence": 2
                    }
                ],
                "expected_resolution": "Apply both requirements (monthly to CBI, quarterly to EBA)"
            }
        }
    
    # =========================================================================
    # JURISDICTION CONFIGURATION TESTS
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_load_jurisdiction_configurations(self, jurisdiction_handler, jurisdiction_configs):
        """Test loading of jurisdiction configurations"""
        for jurisdiction_code, config in jurisdiction_configs.items():
            await jurisdiction_handler.add_jurisdiction_config(jurisdiction_code, config)
        
        # Verify all jurisdictions loaded
        loaded_jurisdictions = await jurisdiction_handler.get_supported_jurisdictions()
        assert len(loaded_jurisdictions) == len(jurisdiction_configs)
        
        for jurisdiction_code in jurisdiction_configs.keys():
            assert jurisdiction_code in loaded_jurisdictions
        
        logger.info(f"Successfully loaded {len(jurisdiction_configs)} jurisdiction configurations")
    
    @pytest.mark.asyncio
    async def test_jurisdiction_hierarchy_validation(self, jurisdiction_handler, jurisdiction_configs):
        """Test jurisdiction hierarchy validation"""
        # Load configurations
        for jurisdiction_code, config in jurisdiction_configs.items():
            await jurisdiction_handler.add_jurisdiction_config(jurisdiction_code, config)
        
        # Test hierarchy relationships
        de_config = await jurisdiction_handler.get_jurisdiction_config("DE")
        assert de_config.parent_jurisdiction == "EU"
        assert de_config.precedence_level == 2
        
        ie_config = await jurisdiction_handler.get_jurisdiction_config("IE")
        assert ie_config.parent_jurisdiction == "EU"
        assert ie_config.precedence_level == 2
        
        eu_config = await jurisdiction_handler.get_jurisdiction_config("EU")
        assert eu_config.parent_jurisdiction is None
        assert eu_config.precedence_level == 1
        
        logger.info("Jurisdiction hierarchy validation successful")
    
    @pytest.mark.asyncio
    async def test_invalid_jurisdiction_handling(self, jurisdiction_handler):
        """Test handling of invalid jurisdictions"""
        # Test invalid jurisdiction code
        with pytest.raises(InvalidJurisdictionError):
            await jurisdiction_handler.get_jurisdiction_config("INVALID")
        
        # Test invalid configuration
        invalid_config = {
            "jurisdiction_code": "INVALID",
            # Missing required fields
        }
        
        with pytest.raises(InvalidJurisdictionError):
            await jurisdiction_handler.add_jurisdiction_config("INVALID", invalid_config)
        
        logger.info("Invalid jurisdiction handling successful")
    
    # =========================================================================
    # PRECEDENCE RESOLUTION TESTS
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_simple_precedence_resolution(self, jurisdiction_handler, jurisdiction_configs, sample_obligations):
        """Test simple precedence resolution between jurisdictions"""
        # Load configurations and obligations
        for jurisdiction_code, config in jurisdiction_configs.items():
            await jurisdiction_handler.add_jurisdiction_config(jurisdiction_code, config)
        
        # Test EU vs DE precedence
        eu_obligation = sample_obligations["eu_gdpr"]
        de_obligation = sample_obligations["de_kwg"]
        
        precedence_result = await jurisdiction_handler.resolve_precedence([eu_obligation, de_obligation])
        
        # EU should have higher precedence (level 1 vs 2)
        assert precedence_result.primary_jurisdiction == "EU"
        assert precedence_result.precedence_order == ["EU", "DE"]
        
        logger.info("Simple precedence resolution successful")
    
    @pytest.mark.asyncio
    async def test_complex_precedence_resolution(self, jurisdiction_handler, jurisdiction_configs, sample_obligations):
        """Test complex precedence resolution with multiple jurisdictions"""
        # Load configurations
        for jurisdiction_code, config in jurisdiction_configs.items():
            await jurisdiction_handler.add_jurisdiction_config(jurisdiction_code, config)
        
        # Test multiple jurisdiction precedence
        obligations = [
            sample_obligations["eu_gdpr"],
            sample_obligations["de_kwg"],
            sample_obligations["ie_central_bank"],
            sample_obligations["us_bsa"],
            sample_obligations["uk_fsma"]
        ]
        
        precedence_result = await jurisdiction_handler.resolve_precedence(obligations)
        
        # Should prioritize supranational (EU) and national level 1 jurisdictions
        assert "EU" in precedence_result.precedence_order[:3]  # EU should be in top 3
        assert precedence_result.conflicts_detected is not None
        
        logger.info("Complex precedence resolution successful")
    
    @pytest.mark.asyncio
    async def test_precedence_with_customer_jurisdiction(self, jurisdiction_handler, jurisdiction_configs):
        """Test precedence resolution considering customer jurisdiction"""
        # Load configurations
        for jurisdiction_code, config in jurisdiction_configs.items():
            await jurisdiction_handler.add_jurisdiction_config(jurisdiction_code, config)
        
        # Customer in Germany
        customer_context = {
            "customer_id": "CUST_001",
            "primary_jurisdiction": "DE",
            "secondary_jurisdictions": ["EU"],
            "customer_type": "individual",
            "residence": "DE",
            "citizenship": "DE"
        }
        
        obligations = [
            sample_obligations["eu_gdpr"],
            sample_obligations["de_kwg"]
        ]
        
        precedence_result = await jurisdiction_handler.resolve_precedence_with_context(
            obligations, customer_context
        )
        
        # Should consider customer jurisdiction in precedence
        assert "DE" in precedence_result.applicable_jurisdictions
        assert precedence_result.customer_specific_rules is not None
        
        logger.info("Customer jurisdiction precedence resolution successful")
    
    # =========================================================================
    # CONFLICT RESOLUTION TESTS
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_data_retention_conflict_resolution(self, jurisdiction_handler, jurisdiction_configs, conflict_scenarios):
        """Test resolution of data retention conflicts"""
        # Load configurations
        for jurisdiction_code, config in jurisdiction_configs.items():
            await jurisdiction_handler.add_jurisdiction_config(jurisdiction_code, config)
        
        conflict_scenario = conflict_scenarios["eu_vs_national_privacy"]
        
        resolution = await jurisdiction_handler.resolve_conflict(
            conflict_scenario["conflicting_obligations"]
        )
        
        assert resolution is not None
        assert resolution.resolution_strategy == "MOST_RESTRICTIVE"
        assert "6 years" in resolution.resolution_details or "10 years" in resolution.resolution_details
        
        logger.info("Data retention conflict resolution successful")
    
    @pytest.mark.asyncio
    async def test_mifid_implementation_conflict(self, jurisdiction_handler, jurisdiction_configs, conflict_scenarios):
        """Test MiFID II implementation conflict resolution"""
        # Load configurations
        for jurisdiction_code, config in jurisdiction_configs.items():
            await jurisdiction_handler.add_jurisdiction_config(jurisdiction_code, config)
        
        conflict_scenario = conflict_scenarios["mifid_implementation"]
        
        resolution = await jurisdiction_handler.resolve_conflict(
            conflict_scenario["conflicting_obligations"]
        )
        
        assert resolution is not None
        assert resolution.resolution_strategy in ["MOST_RESTRICTIVE", "ADDITIVE"]
        assert "enhanced" in resolution.resolution_details.lower()
        
        logger.info("MiFID implementation conflict resolution successful")
    
    @pytest.mark.asyncio
    async def test_cross_border_reporting_conflict(self, jurisdiction_handler, jurisdiction_configs, conflict_scenarios):
        """Test cross-border reporting conflict resolution"""
        # Load configurations
        for jurisdiction_code, config in jurisdiction_configs.items():
            await jurisdiction_handler.add_jurisdiction_config(jurisdiction_code, config)
        
        conflict_scenario = conflict_scenarios["cross_border_reporting"]
        
        resolution = await jurisdiction_handler.resolve_conflict(
            conflict_scenario["conflicting_obligations"]
        )
        
        assert resolution is not None
        assert resolution.resolution_strategy == "ADDITIVE"
        assert "monthly" in resolution.resolution_details.lower()
        assert "quarterly" in resolution.resolution_details.lower()
        
        logger.info("Cross-border reporting conflict resolution successful")
    
    @pytest.mark.asyncio
    async def test_unresolvable_conflict_handling(self, jurisdiction_handler, jurisdiction_configs):
        """Test handling of unresolvable conflicts"""
        # Load configurations
        for jurisdiction_code, config in jurisdiction_configs.items():
            await jurisdiction_handler.add_jurisdiction_config(jurisdiction_code, config)
        
        # Create truly conflicting obligations
        conflicting_obligations = [
            {
                "obligation_id": "CONFLICT_A",
                "jurisdiction": "US",
                "regulation": "US_LAW",
                "requirement": "Data must be stored in US",
                "precedence": 1
            },
            {
                "obligation_id": "CONFLICT_B",
                "jurisdiction": "EU",
                "regulation": "GDPR",
                "requirement": "Data must be stored in EU",
                "precedence": 1
            }
        ]
        
        resolution = await jurisdiction_handler.resolve_conflict(conflicting_obligations)
        
        assert resolution is not None
        assert resolution.resolution_strategy == "MANUAL_REVIEW_REQUIRED"
        assert resolution.requires_manual_intervention is True
        
        logger.info("Unresolvable conflict handling successful")
    
    # =========================================================================
    # MULTI-JURISDICTION CUSTOMER SCENARIOS
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_eu_citizen_in_us(self, jurisdiction_handler, jurisdiction_configs):
        """Test EU citizen banking in US scenario"""
        # Load configurations
        for jurisdiction_code, config in jurisdiction_configs.items():
            await jurisdiction_handler.add_jurisdiction_config(jurisdiction_code, config)
        
        customer_context = {
            "customer_id": "CUST_EU_US_001",
            "primary_jurisdiction": "US",
            "secondary_jurisdictions": ["EU"],
            "customer_type": "individual",
            "residence": "US",
            "citizenship": "DE",
            "services": ["banking", "investment"]
        }
        
        applicable_rules = await jurisdiction_handler.determine_applicable_rules(customer_context)
        
        assert "US" in applicable_rules.jurisdictions
        assert "EU" in applicable_rules.jurisdictions
        assert "DE" in applicable_rules.jurisdictions
        
        # Should include GDPR for EU citizen
        gdpr_applicable = any("GDPR" in rule.regulation for rule in applicable_rules.rules)
        assert gdpr_applicable is True
        
        # Should include US BSA for US banking
        bsa_applicable = any("BSA" in rule.regulation for rule in applicable_rules.rules)
        assert bsa_applicable is True
        
        logger.info("EU citizen in US scenario successful")
    
    @pytest.mark.asyncio
    async def test_multinational_corporation(self, jurisdiction_handler, jurisdiction_configs):
        """Test multinational corporation compliance scenario"""
        # Load configurations
        for jurisdiction_code, config in jurisdiction_configs.items():
            await jurisdiction_handler.add_jurisdiction_config(jurisdiction_code, config)
        
        corporate_context = {
            "customer_id": "CORP_MULTI_001",
            "customer_type": "corporation",
            "primary_jurisdiction": "DE",
            "operating_jurisdictions": ["DE", "IE", "US", "UK"],
            "services": ["banking", "investment", "insurance"],
            "entity_type": "financial_institution",
            "consolidation_basis": "global"
        }
        
        applicable_rules = await jurisdiction_handler.determine_applicable_rules(corporate_context)
        
        # Should include rules from all operating jurisdictions
        assert len(applicable_rules.jurisdictions) >= 4
        assert "DE" in applicable_rules.jurisdictions
        assert "IE" in applicable_rules.jurisdictions
        assert "US" in applicable_rules.jurisdictions
        assert "UK" in applicable_rules.jurisdictions
        
        # Should handle consolidation requirements
        consolidation_rules = [rule for rule in applicable_rules.rules if "consolidation" in rule.text.lower()]
        assert len(consolidation_rules) > 0
        
        logger.info("Multinational corporation scenario successful")
    
    @pytest.mark.asyncio
    async def test_brexit_transition_scenario(self, jurisdiction_handler, jurisdiction_configs):
        """Test Brexit transition scenario handling"""
        # Load configurations
        for jurisdiction_code, config in jurisdiction_configs.items():
            await jurisdiction_handler.add_jurisdiction_config(jurisdiction_code, config)
        
        # UK entity with EU operations pre and post Brexit
        pre_brexit_context = {
            "customer_id": "UK_ENTITY_001",
            "customer_type": "corporation",
            "primary_jurisdiction": "UK",
            "operating_jurisdictions": ["UK", "EU"],
            "effective_date": "2020-12-31",  # Pre-Brexit
            "services": ["banking", "investment"]
        }
        
        post_brexit_context = {
            "customer_id": "UK_ENTITY_001",
            "customer_type": "corporation",
            "primary_jurisdiction": "UK",
            "operating_jurisdictions": ["UK"],
            "eu_operations": "third_country",
            "effective_date": "2021-01-01",  # Post-Brexit
            "services": ["banking", "investment"]
        }
        
        pre_brexit_rules = await jurisdiction_handler.determine_applicable_rules(pre_brexit_context)
        post_brexit_rules = await jurisdiction_handler.determine_applicable_rules(post_brexit_context)
        
        # Pre-Brexit should include EU rules
        assert "EU" in pre_brexit_rules.jurisdictions
        
        # Post-Brexit should have different rule set
        assert len(pre_brexit_rules.rules) != len(post_brexit_rules.rules)
        
        logger.info("Brexit transition scenario successful")
    
    # =========================================================================
    # PERFORMANCE AND SCALABILITY TESTS
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_large_jurisdiction_set_performance(self, jurisdiction_handler):
        """Test performance with large number of jurisdictions"""
        import time
        
        # Create large set of jurisdiction configurations
        large_jurisdiction_set = {}
        for i in range(100):
            jurisdiction_code = f"TEST_{i:03d}"
            large_jurisdiction_set[jurisdiction_code] = {
                "jurisdiction_code": jurisdiction_code,
                "jurisdiction_name": f"Test Jurisdiction {i}",
                "jurisdiction_type": "NATIONAL",
                "parent_jurisdiction": "EU" if i % 2 == 0 else None,
                "precedence_level": (i % 5) + 1,
                "languages": ["en"],
                "regulatory_authorities": [f"Authority_{i}"],
                "applicable_regulations": [f"Regulation_{i}"],
                "effective_date": "2024-01-01",
                "is_active": True,
                "metadata": {"test": True}
            }
        
        # Load configurations and measure time
        start_time = time.time()
        for jurisdiction_code, config in large_jurisdiction_set.items():
            await jurisdiction_handler.add_jurisdiction_config(jurisdiction_code, config)
        end_time = time.time()
        
        loading_time = end_time - start_time
        assert loading_time < 10.0  # Should load 100 jurisdictions in <10 seconds
        
        # Test precedence resolution performance
        obligations = []
        for i in range(50):
            obligations.append({
                "obligation_id": f"OBL_{i:03d}",
                "jurisdiction": f"TEST_{i:03d}",
                "regulation": f"Regulation_{i}",
                "precedence": (i % 5) + 1
            })
        
        start_time = time.time()
        precedence_result = await jurisdiction_handler.resolve_precedence(obligations)
        end_time = time.time()
        
        resolution_time = end_time - start_time
        assert resolution_time < 5.0  # Should resolve 50 obligations in <5 seconds
        
        logger.info(f"Large jurisdiction set performance: Loading {loading_time:.2f}s, Resolution {resolution_time:.2f}s")
    
    @pytest.mark.asyncio
    async def test_concurrent_jurisdiction_operations(self, jurisdiction_handler, jurisdiction_configs):
        """Test concurrent jurisdiction operations"""
        # Load configurations
        for jurisdiction_code, config in jurisdiction_configs.items():
            await jurisdiction_handler.add_jurisdiction_config(jurisdiction_code, config)
        
        # Create concurrent operations
        async def concurrent_precedence_resolution(obligations):
            return await jurisdiction_handler.resolve_precedence(obligations)
        
        async def concurrent_conflict_resolution(conflicts):
            return await jurisdiction_handler.resolve_conflict(conflicts)
        
        # Run concurrent operations
        tasks = []
        for i in range(10):
            obligations = [
                {"obligation_id": f"CONC_{i}_001", "jurisdiction": "EU", "precedence": 1},
                {"obligation_id": f"CONC_{i}_002", "jurisdiction": "DE", "precedence": 2}
            ]
            tasks.append(concurrent_precedence_resolution(obligations))
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 10
        assert all(result.primary_jurisdiction == "EU" for result in results)
        
        logger.info("Concurrent jurisdiction operations successful")
    
    # =========================================================================
    # EDGE CASES AND ERROR RECOVERY TESTS
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_circular_jurisdiction_hierarchy(self, jurisdiction_handler):
        """Test detection of circular jurisdiction hierarchy"""
        # Create circular hierarchy
        circular_configs = {
            "CIRC_A": {
                "jurisdiction_code": "CIRC_A",
                "jurisdiction_name": "Circular A",
                "parent_jurisdiction": "CIRC_B",
                "precedence_level": 1
            },
            "CIRC_B": {
                "jurisdiction_code": "CIRC_B",
                "jurisdiction_name": "Circular B",
                "parent_jurisdiction": "CIRC_A",  # Circular reference
                "precedence_level": 2
            }
        }
        
        # Should detect circular reference
        with pytest.raises(InvalidJurisdictionError) as exc_info:
            for jurisdiction_code, config in circular_configs.items():
                await jurisdiction_handler.add_jurisdiction_config(jurisdiction_code, config)
        
        assert "circular" in str(exc_info.value).lower()
        
        logger.info("Circular jurisdiction hierarchy detection successful")
    
    @pytest.mark.asyncio
    async def test_missing_parent_jurisdiction(self, jurisdiction_handler):
        """Test handling of missing parent jurisdiction"""
        config_with_missing_parent = {
            "jurisdiction_code": "ORPHAN",
            "jurisdiction_name": "Orphan Jurisdiction",
            "parent_jurisdiction": "NONEXISTENT",
            "precedence_level": 2
        }
        
        with pytest.raises(InvalidJurisdictionError) as exc_info:
            await jurisdiction_handler.add_jurisdiction_config("ORPHAN", config_with_missing_parent)
        
        assert "parent" in str(exc_info.value).lower()
        
        logger.info("Missing parent jurisdiction handling successful")
    
    @pytest.mark.asyncio
    async def test_jurisdiction_deactivation(self, jurisdiction_handler, jurisdiction_configs):
        """Test jurisdiction deactivation and reactivation"""
        # Load configurations
        for jurisdiction_code, config in jurisdiction_configs.items():
            await jurisdiction_handler.add_jurisdiction_config(jurisdiction_code, config)
        
        # Deactivate jurisdiction
        await jurisdiction_handler.deactivate_jurisdiction("DE")
        
        # Should not appear in active jurisdictions
        active_jurisdictions = await jurisdiction_handler.get_active_jurisdictions()
        assert "DE" not in active_jurisdictions
        
        # Should still exist but be inactive
        de_config = await jurisdiction_handler.get_jurisdiction_config("DE")
        assert de_config.is_active is False
        
        # Reactivate jurisdiction
        await jurisdiction_handler.activate_jurisdiction("DE")
        
        # Should appear in active jurisdictions again
        active_jurisdictions = await jurisdiction_handler.get_active_jurisdictions()
        assert "DE" in active_jurisdictions
        
        logger.info("Jurisdiction deactivation/reactivation successful")
    
    @pytest.mark.asyncio
    async def test_jurisdiction_metadata_handling(self, jurisdiction_handler, jurisdiction_configs):
        """Test jurisdiction metadata handling and validation"""
        # Load configurations
        for jurisdiction_code, config in jurisdiction_configs.items():
            await jurisdiction_handler.add_jurisdiction_config(jurisdiction_code, config)
        
        # Test metadata access
        de_config = await jurisdiction_handler.get_jurisdiction_config("DE")
        assert de_config.metadata["currency"] == "EUR"
        assert de_config.metadata["timezone"] == "CET"
        assert "christmas" in de_config.metadata["holidays"]
        
        # Test metadata update
        updated_metadata = de_config.metadata.copy()
        updated_metadata["custom_field"] = "test_value"
        
        await jurisdiction_handler.update_jurisdiction_metadata("DE", updated_metadata)
        
        # Verify update
        updated_config = await jurisdiction_handler.get_jurisdiction_config("DE")
        assert updated_config.metadata["custom_field"] == "test_value"
        
        logger.info("Jurisdiction metadata handling successful")
    
    # =========================================================================
    # INTEGRATION TESTS WITH MOCK DEPENDENCIES
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_database_integration(self, jurisdiction_handler):
        """Test database integration for jurisdiction storage"""
        with patch.object(jurisdiction_handler, 'pg_pool') as mock_pool:
            mock_conn = AsyncMock()
            mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
            
            # Mock database responses
            mock_conn.fetchrow.return_value = {
                'jurisdiction_code': 'TEST_DB',
                'config_data': json.dumps({
                    "jurisdiction_name": "Test Database Jurisdiction",
                    "jurisdiction_type": "NATIONAL"
                }),
                'created_at': datetime.now(timezone.utc)
            }
            
            # Test jurisdiction storage
            test_config = {
                "jurisdiction_code": "TEST_DB",
                "jurisdiction_name": "Test Database Jurisdiction",
                "jurisdiction_type": "NATIONAL",
                "precedence_level": 1
            }
            
            await jurisdiction_handler.add_jurisdiction_config("TEST_DB", test_config)
            
            # Verify database calls
            mock_conn.execute.assert_called()
            
        logger.info("Database integration test successful")
    
    @pytest.mark.asyncio
    async def test_cache_integration(self, jurisdiction_handler, jurisdiction_configs):
        """Test cache integration for jurisdiction configurations"""
        with patch.object(jurisdiction_handler, 'redis_client') as mock_redis:
            mock_redis.get = AsyncMock(return_value=None)
            mock_redis.set = AsyncMock()
            
            # Load configuration (should cache)
            config = jurisdiction_configs["DE"]
            await jurisdiction_handler.add_jurisdiction_config("DE", config)
            
            # Verify cache operations
            mock_redis.set.assert_called()
            
            # Mock cache hit
            mock_redis.get.return_value = json.dumps(config)
            
            # Retrieve configuration (should use cache)
            cached_config = await jurisdiction_handler.get_jurisdiction_config("DE")
            assert cached_config.jurisdiction_code == "DE"
            
        logger.info("Cache integration test successful")

# =============================================================================
# JURISDICTION SCENARIO TEST SUITE
# =============================================================================

class TestJurisdictionScenarios:
    """
    Comprehensive jurisdiction scenario test suite
    
    Tests real-world regulatory scenarios across different jurisdictions
    """
    
    @pytest.fixture
    async def scenario_handler(self):
        """Create JurisdictionHandler for scenario testing"""
        handler = JurisdictionHandler()
        await handler.initialize()
        
        # Load comprehensive jurisdiction configurations
        await handler.load_default_jurisdictions()
        
        yield handler
        await handler.close()
    
    @pytest.mark.scenario
    @pytest.mark.asyncio
    async def test_german_banking_scenario(self, scenario_handler):
        """Test comprehensive German banking regulatory scenario"""
        customer_context = {
            "customer_id": "DE_BANK_001",
            "customer_type": "credit_institution",
            "primary_jurisdiction": "DE",
            "services": ["retail_banking", "corporate_banking", "investment_services"],
            "total_assets": 50000000000,  # 50B EUR
            "institution_type": "credit_institution"
        }
        
        applicable_rules = await scenario_handler.determine_applicable_rules(customer_context)
        
        # Should include German and EU regulations
        jurisdictions = applicable_rules.jurisdictions
        assert "DE" in jurisdictions
        assert "EU" in jurisdictions
        
        # Should include specific German banking regulations
        regulations = [rule.regulation for rule in applicable_rules.rules]
        assert any("KWG" in reg for reg in regulations)  # German Banking Act
        assert any("Basel" in reg for reg in regulations)  # Basel III
        assert any("CRD" in reg for reg in regulations)   # Capital Requirements Directive
        
        logger.info("German banking scenario test successful")
    
    @pytest.mark.scenario
    @pytest.mark.asyncio
    async def test_irish_fund_management_scenario(self, scenario_handler):
        """Test Irish fund management regulatory scenario"""
        customer_context = {
            "customer_id": "IE_FUND_001",
            "customer_type": "fund_management_company",
            "primary_jurisdiction": "IE",
            "services": ["fund_management", "investment_advice"],
            "fund_types": ["UCITS", "AIF"],
            "aum": 10000000000  # 10B EUR
        }
        
        applicable_rules = await scenario_handler.determine_applicable_rules(customer_context)
        
        # Should include Irish and EU regulations
        jurisdictions = applicable_rules.jurisdictions
        assert "IE" in jurisdictions
        assert "EU" in jurisdictions
        
        # Should include fund-specific regulations
        regulations = [rule.regulation for rule in applicable_rules.rules]
        assert any("UCITS" in reg for reg in regulations)
        assert any("AIFMD" in reg for reg in regulations)
        assert any("MiFID" in reg for reg in regulations)
        
        logger.info("Irish fund management scenario test successful")
    
    @pytest.mark.scenario
    @pytest.mark.asyncio
    async def test_cross_border_payment_scenario(self, scenario_handler):
        """Test cross-border payment service scenario"""
        customer_context = {
            "customer_id": "CROSS_PAY_001",
            "customer_type": "payment_institution",
            "primary_jurisdiction": "DE",
            "operating_jurisdictions": ["DE", "IE", "FR", "ES"],
            "services": ["payment_services", "money_remittance"],
            "cross_border": True
        }
        
        applicable_rules = await scenario_handler.determine_applicable_rules(customer_context)
        
        # Should include all operating jurisdictions
        jurisdictions = applicable_rules.jurisdictions
        assert "DE" in jurisdictions
        assert "IE" in jurisdictions
        assert "FR" in jurisdictions
        assert "ES" in jurisdictions
        assert "EU" in jurisdictions
        
        # Should include payment-specific regulations
        regulations = [rule.regulation for rule in applicable_rules.rules]
        assert any("PSD2" in reg for reg in regulations)  # Payment Services Directive
        assert any("AML" in reg for reg in regulations)   # Anti-Money Laundering
        
        logger.info("Cross-border payment scenario test successful")

# =============================================================================
# TEST CONFIGURATION AND UTILITIES
# =============================================================================

def pytest_configure(config):
    """Configure pytest for JurisdictionHandler tests"""
    config.addinivalue_line("markers", "scenario: mark test as jurisdiction scenario test")
    config.addinivalue_line("markers", "performance: mark test as performance test")
    config.addinivalue_line("markers", "integration: mark test as integration test")

if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "--tb=short"])
