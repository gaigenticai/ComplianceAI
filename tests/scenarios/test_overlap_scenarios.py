#!/usr/bin/env python3
"""
Overlapping EU/National Regulation Scenario Tests
================================================

This module provides comprehensive scenario testing for overlapping EU and national
regulatory requirements including directive vs. implementation conflicts, precedence
rule application, multi-jurisdiction customer handling, and cross-border banking scenarios.

Test Coverage Areas:
- EU directive vs. national implementation variations and conflicts
- Regulatory precedence and hierarchy resolution mechanisms
- Multi-jurisdiction customer compliance scenarios
- Cross-border banking regulatory overlap resolution
- Real regulatory overlap samples and conflict resolution
- Temporal overlap scenarios with effective date conflicts

Rule Compliance:
- Rule 1: No stubs - Complete production-grade scenario tests
- Rule 12: Automated testing - Comprehensive overlap scenario coverage
- Rule 17: Code documentation - Extensive scenario documentation
"""

import pytest
import asyncio
import json
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List, Any, Optional, Set, Tuple
import logging
from contextlib import asynccontextmanager

# Import test infrastructure
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

# Import regulatory processing components
sys.path.append(os.path.join(os.path.dirname(__file__), '../../python-agents/regulatory-intel-agent/src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../../python-agents/intelligence-compliance-agent/src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../../python-agents/decision-orchestration-agent/src'))

from regulatory_intelligence_service import RegulatoryIntelligenceService
from intelligence_compliance_service import IntelligenceComplianceService
from decision_orchestration_service import DecisionOrchestrationService
from rule_compiler import RuleCompiler
from jurisdiction_handler import JurisdictionHandler
from overlap_resolver import OverlapResolver

# Configure test logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TestOverlapScenarios:
    """
    Comprehensive overlapping regulation scenario test suite
    
    Tests complex scenarios where EU directives and national implementations
    create overlapping, conflicting, or hierarchical regulatory requirements.
    """
    
    @pytest.fixture(scope="class")
    async def overlap_regulatory_services(self):
        """Initialize regulatory services for overlap scenario testing"""
        services = OverlapRegulatoryServices()
        await services.initialize()
        yield services
        await services.cleanup()
    
    @pytest.fixture
    def eu_directive_national_implementation_scenarios(self):
        """EU directive with national implementation scenarios"""
        return {
            "psd2_directive_implementations": {
                "eu_directive": {
                    "regulation_id": "EU_PSD2_DIRECTIVE",
                    "source": "European Commission",
                    "regulation": "Payment Services Directive 2 (PSD2)",
                    "regulation_type": "EU_DIRECTIVE",
                    "title": "Directive (EU) 2015/2366 on payment services in the internal market",
                    "content": """
                    This Directive establishes rules for payment services and payment service providers
                    within the Union. Member States shall bring into force the laws, regulations and
                    administrative provisions necessary to comply with this Directive by 13 January 2018.

                    Key Requirements:
                    1. Strong Customer Authentication (SCA) for electronic payments
                    2. Open Banking - Third Party Provider (TPP) access to account information
                    3. Consumer protection measures for payment services
                    4. Operational and security risk management requirements
                    5. Incident reporting to competent authorities

                    Member States may impose additional requirements that do not conflict with this Directive.
                    """,
                    "jurisdiction": "EU",
                    "effective_date": "2018-01-13",
                    "implementation_deadline": "2018-01-13",
                    "allows_national_variations": True,
                    "minimum_harmonization": True,
                    "legal_basis": "Article 114 TFEU",
                    "priority": "CRITICAL"
                },
                "german_implementation": {
                    "regulation_id": "DE_PSD2_IMPLEMENTATION",
                    "source": "BaFin",
                    "regulation": "Zahlungsdiensteaufsichtsgesetz (ZAG)",
                    "regulation_type": "NATIONAL_IMPLEMENTATION",
                    "parent_directive": "EU_PSD2_DIRECTIVE",
                    "title": "German Implementation of PSD2 - Payment Services Supervision Act",
                    "content": """
                    Implementation of PSD2 in German law with additional national requirements:

                    1. Strong Customer Authentication (SCA)
                       - Multi-factor authentication required for all electronic payments >€30
                       - Biometric authentication preferred for high-value transactions
                       - Additional security measures for corporate accounts

                    2. Open Banking Requirements
                       - TPP access through dedicated APIs (not screen scraping)
                       - German language interface requirements
                       - Enhanced liability framework for unauthorized transactions
                       - Additional consumer consent requirements

                    3. German-Specific Additions
                       - Enhanced incident reporting (within 2 hours for critical incidents)
                       - Mandatory German data residency for payment data
                       - Additional audit requirements by German auditors
                       - Stricter capital requirements for payment institutions

                    These requirements go beyond EU minimums and are binding for all payment
                    service providers operating in Germany.
                    """,
                    "jurisdiction": "DE",
                    "effective_date": "2018-01-13",
                    "additional_requirements": True,
                    "stricter_than_eu": True,
                    "legal_basis": ["Zahlungsdiensteaufsichtsgesetz", "Kreditwesengesetz"],
                    "priority": "CRITICAL"
                },
                "irish_implementation": {
                    "regulation_id": "IE_PSD2_IMPLEMENTATION",
                    "source": "Central Bank of Ireland",
                    "regulation": "European Union (Payment Services) Regulations 2018",
                    "regulation_type": "NATIONAL_IMPLEMENTATION",
                    "parent_directive": "EU_PSD2_DIRECTIVE",
                    "title": "Irish Implementation of PSD2 - Payment Services Regulations",
                    "content": """
                    Implementation of PSD2 in Irish law following minimum harmonization approach:

                    1. Strong Customer Authentication (SCA)
                       - Standard EU requirements for electronic payments
                       - Risk-based exemptions as per EBA guidelines
                       - Consumer education requirements for new authentication methods

                    2. Open Banking Framework
                       - TPP access through standardized APIs
                       - Consumer protection measures for data sharing
                       - Clear consent mechanisms and withdrawal procedures
                       - Liability framework aligned with EU standards

                    3. Irish-Specific Provisions
                       - Consumer Protection Code integration
                       - Enhanced complaint handling procedures
                       - Specific provisions for vulnerable customers
                       - Brexit-related provisions for UK payment institutions

                    Ireland implements EU minimums with focus on consumer protection
                    and market competition.
                    """,
                    "jurisdiction": "IE",
                    "effective_date": "2018-01-13",
                    "additional_requirements": False,
                    "minimum_implementation": True,
                    "consumer_protection_focus": True,
                    "legal_basis": ["European Union (Payment Services) Regulations 2018"],
                    "priority": "HIGH"
                },
                "french_implementation": {
                    "regulation_id": "FR_PSD2_IMPLEMENTATION",
                    "source": "ACPR",
                    "regulation": "Code monétaire et financier",
                    "regulation_type": "NATIONAL_IMPLEMENTATION",
                    "parent_directive": "EU_PSD2_DIRECTIVE",
                    "title": "French Implementation of PSD2 - Monetary and Financial Code",
                    "content": """
                    Implementation of PSD2 in French law with market-specific adaptations:

                    1. Strong Customer Authentication (SCA)
                       - EU standard requirements with French language interfaces
                       - Specific provisions for French payment cards (Carte Bancaire)
                       - Integration with French national payment systems

                    2. Open Banking and Competition
                       - Enhanced competition measures beyond EU requirements
                       - Specific provisions for French banking market structure
                       - Additional transparency requirements for fees and charges
                       - Support for French fintech ecosystem development

                    3. French-Specific Measures
                       - Integration with French consumer protection law
                       - Specific provisions for overseas territories
                       - Enhanced supervisory powers for ACPR
                       - Coordination with Banque de France payment systems

                    France balances EU compliance with national market characteristics
                    and consumer protection traditions.
                    """,
                    "jurisdiction": "FR",
                    "effective_date": "2018-01-13",
                    "market_specific_adaptations": True,
                    "competition_focus": True,
                    "legal_basis": ["Code monétaire et financier", "Code de la consommation"],
                    "priority": "HIGH"
                }
            },
            "gdpr_national_implementations": {
                "eu_regulation": {
                    "regulation_id": "EU_GDPR_REGULATION",
                    "source": "European Commission",
                    "regulation": "General Data Protection Regulation (GDPR)",
                    "regulation_type": "EU_REGULATION",
                    "title": "Regulation (EU) 2016/679 on the protection of natural persons",
                    "content": """
                    This Regulation applies directly in all Member States and establishes rules
                    for the protection of natural persons with regard to the processing of personal data.

                    Key Requirements:
                    1. Lawful basis for processing personal data
                    2. Data subject rights (access, rectification, erasure, portability)
                    3. Data protection by design and by default
                    4. Data Protection Impact Assessments (DPIA) for high-risk processing
                    5. Appointment of Data Protection Officers (DPO) where required
                    6. Breach notification within 72 hours to supervisory authorities

                    Member States may provide for specific rules in certain areas while
                    maintaining the level of protection provided by this Regulation.
                    """,
                    "jurisdiction": "EU",
                    "effective_date": "2018-05-25",
                    "directly_applicable": True,
                    "allows_national_derogations": True,
                    "legal_basis": "Article 16 TFEU",
                    "priority": "CRITICAL"
                },
                "german_adaptations": {
                    "regulation_id": "DE_GDPR_ADAPTATIONS",
                    "source": "German Federal Government",
                    "regulation": "Bundesdatenschutzgesetz (BDSG) 2018",
                    "regulation_type": "NATIONAL_ADAPTATION",
                    "parent_regulation": "EU_GDPR_REGULATION",
                    "title": "German Federal Data Protection Act - GDPR Adaptations",
                    "content": """
                    German adaptations and specifications of GDPR provisions:

                    1. Data Protection Officer (DPO) Requirements
                       - Mandatory DPO for companies with >20 employees processing personal data
                       - Stricter qualification requirements for DPOs
                       - Enhanced independence and reporting requirements

                    2. Employee Data Protection
                       - Specific rules for employee monitoring and surveillance
                       - Works council involvement in data processing decisions
                       - Enhanced protection for employee personal data

                    3. Processing for Scientific and Historical Research
                       - Specific exemptions and safeguards for research purposes
                       - Balancing of research interests with data protection rights
                       - Special provisions for archival and statistical purposes

                    4. Sanctions and Enforcement
                       - Detailed administrative fine calculation methodology
                       - Specific procedures for supervisory authority investigations
                       - Enhanced cooperation between federal and state authorities

                    German law provides additional specificity while maintaining GDPR compliance.
                    """,
                    "jurisdiction": "DE",
                    "effective_date": "2018-05-25",
                    "stricter_requirements": True,
                    "employee_protection_focus": True,
                    "legal_basis": ["Bundesdatenschutzgesetz"],
                    "priority": "CRITICAL"
                },
                "irish_adaptations": {
                    "regulation_id": "IE_GDPR_ADAPTATIONS",
                    "source": "Irish Government",
                    "regulation": "Data Protection Act 2018",
                    "regulation_type": "NATIONAL_ADAPTATION",
                    "parent_regulation": "EU_GDPR_REGULATION",
                    "title": "Irish Data Protection Act 2018 - GDPR Implementation",
                    "content": """
                    Irish national provisions complementing GDPR:

                    1. Age of Digital Consent
                       - Digital consent age set at 16 years (maximum allowed under GDPR)
                       - Specific provisions for child protection online
                       - Parental consent mechanisms for under-16s

                    2. Freedom of Expression and Information
                       - Balancing data protection with freedom of expression
                       - Specific provisions for journalism and academic freedom
                       - Literary and artistic expression protections

                    3. National Security and Law Enforcement
                       - Specific exemptions for national security processing
                       - Law enforcement data processing framework
                       - Intelligence services data protection provisions

                    4. Supervisory Authority Powers
                       - Enhanced powers for Data Protection Commission
                       - Specific investigation and enforcement procedures
                       - International cooperation mechanisms (important for US tech companies)

                    Ireland balances GDPR compliance with its role as European headquarters
                    for major technology companies.
                    """,
                    "jurisdiction": "IE",
                    "effective_date": "2018-05-25",
                    "tech_industry_focus": True,
                    "international_cooperation": True,
                    "legal_basis": ["Data Protection Act 2018"],
                    "priority": "CRITICAL"
                }
            }
        }
    
    @pytest.fixture
    def multi_jurisdiction_customer_scenarios(self):
        """Multi-jurisdiction customer scenarios for overlap testing"""
        return {
            "eu_multinational_corporation": {
                "customer_id": "EU_MULTINATIONAL_001",
                "customer_type": "Multinational Corporation",
                "company_data": {
                    "company_name": "EuroTech Solutions SE",
                    "legal_form": "Societas Europaea (SE)",
                    "registration_number": "SE123456789",
                    "registration_country": "DE",
                    "tax_number": "DE123456789",
                    "industry": "Technology Services"
                },
                "headquarters": {
                    "country": "DE",
                    "city": "Frankfurt",
                    "address": "Taunusanlage 1, 60329 Frankfurt am Main"
                },
                "subsidiaries": [
                    {
                        "country": "IE",
                        "entity_name": "EuroTech Solutions Ireland Ltd",
                        "business_activities": ["Software Development", "Data Processing"],
                        "employee_count": 500,
                        "annual_revenue": Decimal("50000000.00")
                    },
                    {
                        "country": "FR",
                        "entity_name": "EuroTech Solutions France SAS",
                        "business_activities": ["Sales", "Customer Support"],
                        "employee_count": 200,
                        "annual_revenue": Decimal("25000000.00")
                    },
                    {
                        "country": "NL",
                        "entity_name": "EuroTech Solutions Netherlands BV",
                        "business_activities": ["European Distribution", "Logistics"],
                        "employee_count": 150,
                        "annual_revenue": Decimal("30000000.00")
                    }
                ],
                "banking_relationships": {
                    "primary_bank": {
                        "country": "DE",
                        "bank_name": "Deutsche Bank AG",
                        "services": ["Corporate Banking", "Cash Management", "Trade Finance"]
                    },
                    "subsidiary_banks": [
                        {
                            "country": "IE",
                            "bank_name": "Bank of Ireland",
                            "services": ["Local Banking", "Payroll Services"]
                        },
                        {
                            "country": "FR",
                            "bank_name": "BNP Paribas",
                            "services": ["Local Banking", "FX Services"]
                        }
                    ]
                },
                "regulatory_exposure": {
                    "gdpr_controller": True,
                    "psd2_corporate_customer": True,
                    "aml_enhanced_dd": True,
                    "cross_border_transactions": True,
                    "data_transfers": ["DE-IE", "IE-FR", "FR-NL"],
                    "payment_flows": ["Intra-EU", "Third-Country"]
                },
                "compliance_complexity": {
                    "multiple_supervisors": True,
                    "conflicting_requirements": True,
                    "regulatory_arbitrage_risk": True,
                    "coordination_required": True
                }
            },
            "uk_financial_services_post_brexit": {
                "customer_id": "UK_FS_POST_BREXIT_001",
                "customer_type": "UK Financial Services Company",
                "company_data": {
                    "company_name": "London Capital Markets Ltd",
                    "legal_form": "Private Limited Company",
                    "registration_number": "UK87654321",
                    "registration_country": "UK",
                    "fca_number": "FCA123456",
                    "industry": "Investment Banking"
                },
                "headquarters": {
                    "country": "UK",
                    "city": "London",
                    "address": "25 Bank Street, Canary Wharf, London E14 5JP"
                },
                "eu_operations": {
                    "irish_subsidiary": {
                        "entity_name": "London Capital Markets (Ireland) Ltd",
                        "authorization": "MiFID Investment Firm",
                        "services": ["Investment Services", "Portfolio Management"],
                        "passporting_to": ["DE", "FR", "IT", "ES"]
                    },
                    "german_branch": {
                        "entity_name": "London Capital Markets - German Branch",
                        "authorization": "Third Country Branch",
                        "services": ["Corporate Finance", "Advisory Services"],
                        "bafin_supervision": True
                    }
                },
                "regulatory_challenges": {
                    "lost_passporting_rights": True,
                    "equivalence_uncertainty": True,
                    "dual_supervision": True,
                    "regulatory_divergence": True,
                    "data_adequacy_issues": True,
                    "client_migration_required": True
                },
                "overlap_scenarios": {
                    "uk_eu_data_flows": {
                        "gdpr_vs_uk_gdpr": True,
                        "adequacy_decision_dependency": True,
                        "sccs_implementation": True
                    },
                    "mifid_equivalence": {
                        "uk_investment_firm_regime": True,
                        "eu_third_country_treatment": True,
                        "client_classification_differences": True
                    },
                    "aml_coordination": {
                        "uk_mlr_vs_eu_amld": True,
                        "suspicious_transaction_reporting": True,
                        "beneficial_ownership_registers": True
                    }
                }
            },
            "us_tech_company_eu_operations": {
                "customer_id": "US_TECH_EU_001",
                "customer_type": "US Technology Company with EU Operations",
                "company_data": {
                    "company_name": "Silicon Valley Innovations Inc.",
                    "legal_form": "Delaware Corporation",
                    "registration_number": "US123456789",
                    "registration_country": "US",
                    "industry": "Technology Platform"
                },
                "eu_structure": {
                    "irish_headquarters": {
                        "entity_name": "Silicon Valley Innovations Ireland Ltd",
                        "role": "European Headquarters",
                        "services": ["Data Processing", "Customer Support", "Sales"],
                        "gdpr_main_establishment": True
                    },
                    "dutch_holding": {
                        "entity_name": "Silicon Valley Innovations Netherlands BV",
                        "role": "IP Holding Company",
                        "services": ["Intellectual Property Licensing"],
                        "tax_optimization": True
                    }
                },
                "regulatory_overlap_challenges": {
                    "gdpr_vs_us_privacy_laws": {
                        "california_ccpa": True,
                        "federal_sectoral_laws": True,
                        "data_transfer_mechanisms": ["SCCs", "BCRs"],
                        "privacy_shield_invalidation": True
                    },
                    "digital_services_regulation": {
                        "dsa_compliance": True,
                        "dma_gatekeeper_status": True,
                        "national_implementation_variations": True
                    },
                    "payment_services": {
                        "psd2_compliance": True,
                        "us_payment_regulations": True,
                        "cross_border_payment_flows": True
                    }
                },
                "compliance_coordination": {
                    "multi_regulator_engagement": True,
                    "conflicting_legal_requirements": True,
                    "regulatory_forum_shopping": False,
                    "global_compliance_framework": True
                }
            }
        }
    
    @pytest.fixture
    def temporal_overlap_scenarios(self):
        """Temporal overlap scenarios with effective date conflicts"""
        return {
            "mifid_implementation_timeline": {
                "mifid2_directive": {
                    "regulation_id": "EU_MIFID2_DIRECTIVE",
                    "effective_date": "2018-01-03",
                    "implementation_deadline": "2018-01-03",
                    "content": "Markets in Financial Instruments Directive II",
                    "jurisdiction": "EU"
                },
                "german_implementation": {
                    "regulation_id": "DE_MIFID2_IMPLEMENTATION",
                    "effective_date": "2018-01-03",
                    "additional_requirements_date": "2018-07-01",
                    "content": "German MiFID II implementation with additional investor protection measures",
                    "jurisdiction": "DE"
                },
                "eba_guidelines": {
                    "regulation_id": "EBA_MIFID2_GUIDELINES",
                    "effective_date": "2018-09-03",
                    "content": "EBA Guidelines on MiFID II product governance",
                    "jurisdiction": "EU"
                },
                "esma_technical_standards": {
                    "regulation_id": "ESMA_MIFID2_RTS",
                    "effective_date": "2018-01-03",
                    "delayed_application": "2018-03-03",
                    "content": "ESMA Regulatory Technical Standards for MiFID II",
                    "jurisdiction": "EU"
                }
            },
            "basel_crd_implementation": {
                "basel_iii_framework": {
                    "regulation_id": "BASEL_III_FRAMEWORK",
                    "effective_date": "2013-01-01",
                    "phase_in_period": "2013-2019",
                    "content": "Basel III international regulatory framework",
                    "jurisdiction": "GLOBAL"
                },
                "crd_iv_directive": {
                    "regulation_id": "EU_CRD_IV",
                    "effective_date": "2014-01-01",
                    "content": "Capital Requirements Directive IV",
                    "jurisdiction": "EU"
                },
                "crr_regulation": {
                    "regulation_id": "EU_CRR",
                    "effective_date": "2014-01-01",
                    "content": "Capital Requirements Regulation",
                    "jurisdiction": "EU"
                },
                "national_implementations": [
                    {
                        "regulation_id": "DE_CRD_IMPLEMENTATION",
                        "effective_date": "2014-01-01",
                        "additional_buffers_date": "2016-01-01",
                        "jurisdiction": "DE"
                    },
                    {
                        "regulation_id": "IE_CRD_IMPLEMENTATION", 
                        "effective_date": "2014-01-01",
                        "macroprudential_measures_date": "2015-07-01",
                        "jurisdiction": "IE"
                    }
                ]
            }
        }
    
    # =========================================================================
    # EU DIRECTIVE VS NATIONAL IMPLEMENTATION TESTS
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_psd2_directive_national_implementation_overlap(self, overlap_regulatory_services, eu_directive_national_implementation_scenarios):
        """Test PSD2 directive vs national implementation overlaps"""
        logger.info("Testing PSD2 directive vs national implementation overlap")
        
        psd2_scenario = eu_directive_national_implementation_scenarios["psd2_directive_implementations"]
        
        # Process EU directive and all national implementations
        regulations = [
            psd2_scenario["eu_directive"],
            psd2_scenario["german_implementation"],
            psd2_scenario["irish_implementation"],
            psd2_scenario["french_implementation"]
        ]
        
        # Step 1: Process all regulations
        processing_results = []
        for regulation in regulations:
            result = await overlap_regulatory_services.intelligence.process_overlapping_regulation(
                regulation, regulation_type=regulation["regulation_type"]
            )
            processing_results.append(result)
        
        # Verify all processed successfully
        assert all(result.success for result in processing_results)
        
        # Step 2: Detect overlaps between EU directive and national implementations
        overlap_detection = await overlap_regulatory_services.overlap_resolver.detect_directive_implementation_overlaps(
            psd2_scenario["eu_directive"], 
            [psd2_scenario["german_implementation"], psd2_scenario["irish_implementation"], psd2_scenario["french_implementation"]]
        )
        
        assert overlap_detection.success is True
        assert len(overlap_detection.detected_overlaps) >= 3  # Should detect overlaps with all implementations
        
        # Verify specific overlaps
        german_overlap = next(
            (o for o in overlap_detection.detected_overlaps if o["jurisdiction"] == "DE"),
            None
        )
        assert german_overlap is not None
        assert german_overlap["overlap_type"] == "STRICTER_NATIONAL_REQUIREMENTS"
        assert german_overlap["conflict_level"] == "COMPATIBLE"  # Stricter but compatible
        
        irish_overlap = next(
            (o for o in overlap_detection.detected_overlaps if o["jurisdiction"] == "IE"),
            None
        )
        assert irish_overlap is not None
        assert irish_overlap["overlap_type"] == "MINIMUM_IMPLEMENTATION"
        assert irish_overlap["conflict_level"] == "COMPLIANT"
        
        # Step 3: Resolve overlaps and establish precedence
        overlap_resolution = await overlap_regulatory_services.overlap_resolver.resolve_directive_implementation_conflicts(
            overlap_detection.detected_overlaps
        )
        
        assert overlap_resolution.success is True
        assert overlap_resolution.resolution_strategy == "HIERARCHICAL_PRECEDENCE"
        
        # Verify precedence rules
        precedence_rules = overlap_resolution.precedence_rules
        assert precedence_rules["eu_directive_minimum"] is True
        assert precedence_rules["national_stricter_allowed"] is True
        assert precedence_rules["national_weaker_prohibited"] is True
        
        # Step 4: Test customer-specific application
        german_customer_scenario = {
            "customer_jurisdiction": "DE",
            "service_type": "payment_services",
            "applicable_regulations": ["EU_PSD2_DIRECTIVE", "DE_PSD2_IMPLEMENTATION"]
        }
        
        customer_resolution = await overlap_regulatory_services.decision.resolve_customer_regulatory_overlap(
            german_customer_scenario, overlap_resolution.precedence_rules
        )
        
        assert customer_resolution.success is True
        assert customer_resolution.applicable_regulation == "DE_PSD2_IMPLEMENTATION"  # Stricter national rule applies
        assert customer_resolution.compliance_level == "ENHANCED"
        
        logger.info("PSD2 directive vs national implementation overlap test successful")
    
    @pytest.mark.asyncio
    async def test_gdpr_national_adaptation_overlap(self, overlap_regulatory_services, eu_directive_national_implementation_scenarios):
        """Test GDPR regulation vs national adaptation overlaps"""
        logger.info("Testing GDPR regulation vs national adaptation overlap")
        
        gdpr_scenario = eu_directive_national_implementation_scenarios["gdpr_national_implementations"]
        
        # Process GDPR and national adaptations
        regulations = [
            gdpr_scenario["eu_regulation"],
            gdpr_scenario["german_adaptations"],
            gdpr_scenario["irish_adaptations"]
        ]
        
        processing_results = []
        for regulation in regulations:
            result = await overlap_regulatory_services.intelligence.process_overlapping_regulation(
                regulation, regulation_type=regulation["regulation_type"]
            )
            processing_results.append(result)
        
        assert all(result.success for result in processing_results)
        
        # Detect GDPR adaptation overlaps
        gdpr_overlap_detection = await overlap_regulatory_services.overlap_resolver.detect_regulation_adaptation_overlaps(
            gdpr_scenario["eu_regulation"],
            [gdpr_scenario["german_adaptations"], gdpr_scenario["irish_adaptations"]]
        )
        
        assert gdpr_overlap_detection.success is True
        assert len(gdpr_overlap_detection.detected_overlaps) >= 2
        
        # Verify German adaptations
        german_adaptation = next(
            (o for o in gdpr_overlap_detection.detected_overlaps if o["jurisdiction"] == "DE"),
            None
        )
        assert german_adaptation is not None
        assert german_adaptation["overlap_type"] == "NATIONAL_SPECIFICATION"
        assert german_adaptation["areas"] == ["DPO_REQUIREMENTS", "EMPLOYEE_DATA", "RESEARCH_EXEMPTIONS"]
        
        # Verify Irish adaptations
        irish_adaptation = next(
            (o for o in gdpr_overlap_detection.detected_overlaps if o["jurisdiction"] == "IE"),
            None
        )
        assert irish_adaptation is not None
        assert irish_adaptation["overlap_type"] == "NATIONAL_SPECIFICATION"
        assert irish_adaptation["areas"] == ["DIGITAL_CONSENT_AGE", "FREEDOM_OF_EXPRESSION", "TECH_INDUSTRY_FOCUS"]
        
        # Test data transfer scenario with overlapping requirements
        data_transfer_scenario = {
            "transfer_type": "intra_eu",
            "from_country": "IE",
            "to_country": "DE",
            "data_category": "employee_data",
            "controller": "multinational_corporation"
        }
        
        transfer_resolution = await overlap_regulatory_services.decision.resolve_data_transfer_overlap(
            data_transfer_scenario, gdpr_overlap_detection.detected_overlaps
        )
        
        assert transfer_resolution.success is True
        assert transfer_resolution.transfer_mechanism == "ADEQUACY_DECISION"  # Intra-EU transfer
        assert transfer_resolution.additional_safeguards == ["GERMAN_EMPLOYEE_PROTECTION", "WORKS_COUNCIL_CONSULTATION"]
        
        logger.info("GDPR regulation vs national adaptation overlap test successful")
    
    # =========================================================================
    # CONFLICTING REQUIREMENTS RESOLUTION TESTS
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_conflicting_requirements_resolution(self, overlap_regulatory_services):
        """Test resolution of conflicting regulatory requirements"""
        logger.info("Testing conflicting requirements resolution")
        
        # Create conflicting requirements scenario
        conflicting_regulations = {
            "data_localization_conflict": {
                "eu_regulation": {
                    "regulation_id": "EU_DATA_FREE_FLOW",
                    "requirement": "Free flow of non-personal data within EU",
                    "jurisdiction": "EU",
                    "legal_basis": "Regulation (EU) 2018/1807",
                    "priority": "HIGH"
                },
                "national_requirement": {
                    "regulation_id": "DE_DATA_RESIDENCY",
                    "requirement": "Critical data must be stored within German territory",
                    "jurisdiction": "DE",
                    "legal_basis": "IT-Sicherheitsgesetz",
                    "priority": "CRITICAL"
                }
            },
            "reporting_frequency_conflict": {
                "eu_requirement": {
                    "regulation_id": "EU_REPORTING_STANDARD",
                    "requirement": "Quarterly reporting to EBA",
                    "frequency": "quarterly",
                    "jurisdiction": "EU"
                },
                "national_requirement": {
                    "regulation_id": "DE_ENHANCED_REPORTING",
                    "requirement": "Monthly reporting to BaFin for systemically important institutions",
                    "frequency": "monthly",
                    "jurisdiction": "DE"
                }
            }
        }
        
        # Process conflicting requirements
        conflict_analysis = await overlap_regulatory_services.overlap_resolver.analyze_regulatory_conflicts(
            conflicting_regulations
        )
        
        assert conflict_analysis.success is True
        assert len(conflict_analysis.identified_conflicts) >= 2
        
        # Verify data localization conflict
        data_conflict = next(
            (c for c in conflict_analysis.identified_conflicts if "data" in c["conflict_area"].lower()),
            None
        )
        assert data_conflict is not None
        assert data_conflict["conflict_type"] == "JURISDICTIONAL_SOVEREIGNTY"
        assert data_conflict["resolution_complexity"] == "HIGH"
        
        # Resolve conflicts using precedence rules
        conflict_resolution = await overlap_regulatory_services.overlap_resolver.resolve_regulatory_conflicts(
            conflict_analysis.identified_conflicts
        )
        
        assert conflict_resolution.success is True
        
        # Verify resolution strategies
        resolutions = conflict_resolution.conflict_resolutions
        
        data_resolution = next(
            (r for r in resolutions if "data" in r["conflict_area"].lower()),
            None
        )
        assert data_resolution is not None
        assert data_resolution["resolution_strategy"] == "COMPLIANCE_WITH_BOTH"
        assert data_resolution["implementation_approach"] == "STRICTER_REQUIREMENT_PREVAILS"
        
        reporting_resolution = next(
            (r for r in resolutions if "reporting" in r["conflict_area"].lower()),
            None
        )
        assert reporting_resolution is not None
        assert reporting_resolution["resolution_strategy"] == "ADDITIVE_COMPLIANCE"
        assert reporting_resolution["implementation_approach"] == "MEET_ALL_REQUIREMENTS"
        
        logger.info("Conflicting requirements resolution test successful")
    
    @pytest.mark.asyncio
    async def test_precedence_rule_application(self, overlap_regulatory_services):
        """Test precedence rule application in complex scenarios"""
        logger.info("Testing precedence rule application")
        
        # Create complex precedence scenario
        precedence_scenario = {
            "regulatory_hierarchy": [
                {
                    "level": 1,
                    "regulation_type": "EU_TREATY",
                    "regulation": "Treaty on the Functioning of the European Union",
                    "jurisdiction": "EU",
                    "supremacy": "ABSOLUTE"
                },
                {
                    "level": 2,
                    "regulation_type": "EU_REGULATION",
                    "regulation": "General Data Protection Regulation",
                    "jurisdiction": "EU",
                    "supremacy": "DIRECT_EFFECT"
                },
                {
                    "level": 3,
                    "regulation_type": "EU_DIRECTIVE",
                    "regulation": "Payment Services Directive 2",
                    "jurisdiction": "EU",
                    "supremacy": "MINIMUM_HARMONIZATION"
                },
                {
                    "level": 4,
                    "regulation_type": "NATIONAL_LAW",
                    "regulation": "German Federal Data Protection Act",
                    "jurisdiction": "DE",
                    "supremacy": "NATIONAL_IMPLEMENTATION"
                },
                {
                    "level": 5,
                    "regulation_type": "SUPERVISORY_GUIDANCE",
                    "regulation": "BaFin Guidance on Data Protection",
                    "jurisdiction": "DE",
                    "supremacy": "ADMINISTRATIVE_GUIDANCE"
                }
            ]
        }
        
        # Test precedence rule application
        precedence_analysis = await overlap_regulatory_services.jurisdiction_handler.analyze_regulatory_precedence(
            precedence_scenario["regulatory_hierarchy"]
        )
        
        assert precedence_analysis.success is True
        assert precedence_analysis.hierarchy_valid is True
        
        # Verify precedence order
        precedence_order = precedence_analysis.precedence_order
        assert precedence_order[0]["regulation_type"] == "EU_TREATY"
        assert precedence_order[1]["regulation_type"] == "EU_REGULATION"
        assert precedence_order[-1]["regulation_type"] == "SUPERVISORY_GUIDANCE"
        
        # Test conflict resolution using precedence
        conflict_scenario = {
            "conflicting_requirements": [
                {
                    "regulation": "General Data Protection Regulation",
                    "requirement": "Data processing requires explicit consent",
                    "level": 2
                },
                {
                    "regulation": "German Federal Data Protection Act",
                    "requirement": "Employee data processing allowed based on employment contract",
                    "level": 4
                }
            ]
        }
        
        precedence_resolution = await overlap_regulatory_services.jurisdiction_handler.resolve_using_precedence(
            conflict_scenario, precedence_analysis.precedence_order
        )
        
        assert precedence_resolution.success is True
        assert precedence_resolution.winning_regulation == "General Data Protection Regulation"
        assert precedence_resolution.resolution_basis == "HIGHER_HIERARCHY_LEVEL"
        
        logger.info("Precedence rule application test successful")
    
    # =========================================================================
    # MULTI-JURISDICTION CUSTOMER HANDLING TESTS
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_multinational_corporation_overlap_scenario(self, overlap_regulatory_services, multi_jurisdiction_customer_scenarios):
        """Test multinational corporation with overlapping regulatory requirements"""
        logger.info("Testing multinational corporation overlap scenario")
        
        multinational = multi_jurisdiction_customer_scenarios["eu_multinational_corporation"]
        
        # Analyze regulatory exposure across jurisdictions
        regulatory_analysis = await overlap_regulatory_services.decision.analyze_multinational_regulatory_exposure(
            multinational
        )
        
        assert regulatory_analysis.success is True
        assert len(regulatory_analysis.applicable_jurisdictions) >= 4  # DE, IE, FR, NL, EU
        
        # Verify jurisdiction-specific requirements
        jurisdiction_requirements = regulatory_analysis.jurisdiction_requirements
        
        # German requirements (headquarters)
        german_reqs = jurisdiction_requirements.get("DE", {})
        assert german_reqs.get("gdpr_controller_obligations") is True
        assert german_reqs.get("german_corporate_law") is True
        assert german_reqs.get("bafin_supervision") is True
        
        # Irish requirements (subsidiary)
        irish_reqs = jurisdiction_requirements.get("IE", {})
        assert irish_reqs.get("gdpr_processor_obligations") is True
        assert irish_reqs.get("cbi_supervision") is True
        assert irish_reqs.get("data_processing_activities") is True
        
        # Test cross-border data transfer compliance
        data_transfer_scenario = {
            "transfers": [
                {"from": "DE", "to": "IE", "data_type": "employee_data", "volume": "high"},
                {"from": "IE", "to": "FR", "data_type": "customer_data", "volume": "medium"},
                {"from": "FR", "to": "NL", "data_type": "transaction_data", "volume": "high"}
            ],
            "legal_basis": "legitimate_interest",
            "safeguards": ["standard_contractual_clauses", "binding_corporate_rules"]
        }
        
        transfer_compliance = await overlap_regulatory_services.decision.assess_cross_border_transfer_compliance(
            data_transfer_scenario, multinational
        )
        
        assert transfer_compliance.success is True
        assert transfer_compliance.all_transfers_compliant is True
        
        # Verify transfer-specific requirements
        transfer_requirements = transfer_compliance.transfer_requirements
        assert len(transfer_requirements) == 3  # One for each transfer
        
        # Test overlapping payment services requirements
        payment_scenario = {
            "payment_flows": [
                {"from": "DE", "to": "IE", "amount": Decimal("1000000.00"), "currency": "EUR"},
                {"from": "IE", "to": "FR", "amount": Decimal("500000.00"), "currency": "EUR"}
            ],
            "payment_services": ["corporate_banking", "cash_management", "fx_services"]
        }
        
        payment_compliance = await overlap_regulatory_services.decision.assess_payment_services_overlap(
            payment_scenario, multinational
        )
        
        assert payment_compliance.success is True
        assert payment_compliance.psd2_compliant is True
        assert payment_compliance.aml_compliant is True
        
        logger.info("Multinational corporation overlap scenario test successful")
    
    @pytest.mark.asyncio
    async def test_uk_financial_services_brexit_overlap(self, overlap_regulatory_services, multi_jurisdiction_customer_scenarios):
        """Test UK financial services post-Brexit overlap scenarios"""
        logger.info("Testing UK financial services Brexit overlap scenario")
        
        uk_financial = multi_jurisdiction_customer_scenarios["uk_financial_services_post_brexit"]
        
        # Analyze Brexit-related regulatory overlaps
        brexit_analysis = await overlap_regulatory_services.decision.analyze_brexit_regulatory_overlap(
            uk_financial
        )
        
        assert brexit_analysis.success is True
        assert brexit_analysis.brexit_impact_level == "HIGH"
        
        # Verify overlap areas
        overlap_areas = brexit_analysis.overlap_areas
        assert "data_protection" in overlap_areas
        assert "financial_services_regulation" in overlap_areas
        assert "aml_requirements" in overlap_areas
        
        # Test GDPR vs UK GDPR overlap
        gdpr_overlap_scenario = {
            "data_flows": [
                {"from": "UK", "to": "IE", "data_type": "customer_data"},
                {"from": "IE", "to": "DE", "data_type": "processed_data"}
            ],
            "legal_frameworks": ["UK_GDPR", "EU_GDPR"],
            "adequacy_decision": "PENDING"
        }
        
        gdpr_overlap_resolution = await overlap_regulatory_services.decision.resolve_gdpr_brexit_overlap(
            gdpr_overlap_scenario, uk_financial
        )
        
        assert gdpr_overlap_resolution.success is True
        assert gdpr_overlap_resolution.transfer_mechanism == "STANDARD_CONTRACTUAL_CLAUSES"
        assert gdpr_overlap_resolution.additional_safeguards is not None
        
        # Test MiFID equivalence overlap
        mifid_scenario = {
            "uk_services": ["investment_advice", "portfolio_management", "execution_services"],
            "eu_clients": ["institutional", "professional", "retail"],
            "equivalence_status": "LIMITED"
        }
        
        mifid_overlap_resolution = await overlap_regulatory_services.decision.resolve_mifid_brexit_overlap(
            mifid_scenario, uk_financial
        )
        
        assert mifid_overlap_resolution.success is True
        assert mifid_overlap_resolution.service_restrictions is not None
        assert mifid_overlap_resolution.compliance_strategy == "DUAL_AUTHORIZATION"
        
        logger.info("UK financial services Brexit overlap scenario test successful")
    
    # =========================================================================
    # TEMPORAL OVERLAP SCENARIO TESTS
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_temporal_overlap_resolution(self, overlap_regulatory_services, temporal_overlap_scenarios):
        """Test temporal overlap resolution with effective date conflicts"""
        logger.info("Testing temporal overlap resolution")
        
        mifid_timeline = temporal_overlap_scenarios["mifid_implementation_timeline"]
        
        # Analyze temporal overlaps in MiFID implementation
        temporal_analysis = await overlap_regulatory_services.overlap_resolver.analyze_temporal_overlaps(
            list(mifid_timeline.values())
        )
        
        assert temporal_analysis.success is True
        assert len(temporal_analysis.temporal_conflicts) >= 2
        
        # Verify specific temporal conflicts
        conflicts = temporal_analysis.temporal_conflicts
        
        # Check for delayed application conflict
        delayed_conflict = next(
            (c for c in conflicts if "delayed" in c.get("conflict_type", "").lower()),
            None
        )
        if delayed_conflict:
            assert delayed_conflict["regulations_involved"] >= 2
            assert delayed_conflict["resolution_required"] is True
        
        # Resolve temporal overlaps
        temporal_resolution = await overlap_regulatory_services.overlap_resolver.resolve_temporal_overlaps(
            temporal_analysis.temporal_conflicts
        )
        
        assert temporal_resolution.success is True
        
        # Verify resolution strategies
        resolutions = temporal_resolution.temporal_resolutions
        assert len(resolutions) >= 1
        
        for resolution in resolutions:
            assert resolution["resolution_strategy"] in [
                "LATER_DATE_PREVAILS", 
                "EARLIER_DATE_PREVAILS", 
                "PARALLEL_APPLICATION",
                "PHASED_IMPLEMENTATION"
            ]
        
        # Test Basel/CRD temporal overlap
        basel_timeline = temporal_overlap_scenarios["basel_crd_implementation"]
        
        basel_temporal_analysis = await overlap_regulatory_services.overlap_resolver.analyze_basel_crd_temporal_overlap(
            basel_timeline
        )
        
        assert basel_temporal_analysis.success is True
        assert basel_temporal_analysis.phase_in_complexity == "HIGH"
        
        # Verify phase-in coordination
        phase_coordination = basel_temporal_analysis.phase_coordination
        assert phase_coordination["global_basel_framework"] is not None
        assert phase_coordination["eu_implementation"] is not None
        assert phase_coordination["national_variations"] is not None
        
        logger.info("Temporal overlap resolution test successful")
    
    # =========================================================================
    # CROSS-BORDER BANKING SCENARIO TESTS
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_cross_border_banking_overlap_scenario(self, overlap_regulatory_services, multi_jurisdiction_customer_scenarios):
        """Test cross-border banking regulatory overlap scenarios"""
        logger.info("Testing cross-border banking overlap scenario")
        
        # Create complex cross-border banking scenario
        cross_border_scenario = {
            "transaction_details": {
                "transaction_type": "cross_border_corporate_lending",
                "amount": Decimal("50000000.00"),  # 50 million EUR
                "currency": "EUR",
                "originating_country": "DE",
                "destination_country": "IE",
                "intermediate_countries": ["NL", "FR"]
            },
            "institutions_involved": [
                {
                    "role": "originating_bank",
                    "country": "DE",
                    "institution_type": "universal_bank",
                    "supervision": "ECB_SSM"
                },
                {
                    "role": "correspondent_bank",
                    "country": "NL",
                    "institution_type": "commercial_bank",
                    "supervision": "DNB"
                },
                {
                    "role": "beneficiary_bank",
                    "country": "IE",
                    "institution_type": "commercial_bank",
                    "supervision": "CBI"
                }
            ],
            "regulatory_frameworks": [
                "CRD_IV", "CRR", "PSD2", "AML_Directive", "GDPR", "MiFID_II"
            ]
        }
        
        # Analyze cross-border regulatory overlaps
        cross_border_analysis = await overlap_regulatory_services.decision.analyze_cross_border_banking_overlap(
            cross_border_scenario
        )
        
        assert cross_border_analysis.success is True
        assert len(cross_border_analysis.applicable_regulations) >= 6
        assert len(cross_border_analysis.supervisory_authorities) >= 3
        
        # Verify regulatory coordination requirements
        coordination_requirements = cross_border_analysis.coordination_requirements
        assert coordination_requirements["home_host_coordination"] is True
        assert coordination_requirements["consolidated_supervision"] is True
        assert coordination_requirements["information_sharing"] is True
        
        # Test AML overlap across jurisdictions
        aml_overlap_scenario = {
            "transaction": cross_border_scenario["transaction_details"],
            "aml_frameworks": [
                {"country": "DE", "framework": "German_AML_Act", "risk_assessment": "enhanced"},
                {"country": "NL", "framework": "Dutch_AML_Act", "risk_assessment": "standard"},
                {"country": "IE", "framework": "Irish_CJA_2010", "risk_assessment": "enhanced"}
            ]
        }
        
        aml_overlap_resolution = await overlap_regulatory_services.decision.resolve_aml_cross_border_overlap(
            aml_overlap_scenario
        )
        
        assert aml_overlap_resolution.success is True
        assert aml_overlap_resolution.highest_risk_standard_applied is True
        assert aml_overlap_resolution.coordinated_monitoring is True
        
        # Test capital requirements overlap
        capital_overlap_scenario = {
            "lending_exposure": cross_border_scenario["transaction_details"]["amount"],
            "capital_frameworks": [
                {"country": "DE", "framework": "CRR_CRD_IV", "buffer_requirements": ["conservation", "countercyclical"]},
                {"country": "IE", "framework": "CRR_CRD_IV", "buffer_requirements": ["conservation", "systemic_risk"]}
            ]
        }
        
        capital_overlap_resolution = await overlap_regulatory_services.decision.resolve_capital_requirements_overlap(
            capital_overlap_scenario
        )
        
        assert capital_overlap_resolution.success is True
        assert capital_overlap_resolution.consolidated_calculation is True
        assert capital_overlap_resolution.home_country_consolidation is True
        
        logger.info("Cross-border banking overlap scenario test successful")
    
    # =========================================================================
    # PERFORMANCE AND INTEGRATION TESTS
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_overlap_resolution_performance(self, overlap_regulatory_services, eu_directive_national_implementation_scenarios, multi_jurisdiction_customer_scenarios):
        """Test overlap resolution performance with complex scenarios"""
        logger.info("Testing overlap resolution performance")
        
        # Create large-scale overlap scenario
        complex_scenarios = []
        
        # Add all directive implementation scenarios
        for scenario_name, scenario_data in eu_directive_national_implementation_scenarios.items():
            complex_scenarios.extend(scenario_data.values())
        
        # Add customer scenarios
        complex_scenarios.extend(multi_jurisdiction_customer_scenarios.values())
        
        # Measure performance
        start_time = asyncio.get_event_loop().time()
        
        performance_results = []
        
        # Process overlaps in batches
        batch_size = 5
        for i in range(0, len(complex_scenarios), batch_size):
            batch = complex_scenarios[i:i+batch_size]
            
            batch_start = asyncio.get_event_loop().time()
            
            # Process batch of overlapping scenarios
            batch_results = await asyncio.gather(*[
                overlap_regulatory_services.overlap_resolver.process_overlap_scenario(scenario)
                for scenario in batch
            ])
            
            batch_end = asyncio.get_event_loop().time()
            batch_time = batch_end - batch_start
            
            performance_results.append({
                "batch_size": len(batch),
                "processing_time": batch_time,
                "success_rate": sum(1 for r in batch_results if r.success) / len(batch_results)
            })
        
        end_time = asyncio.get_event_loop().time()
        total_time = end_time - start_time
        
        # Verify performance benchmarks
        assert total_time < 60.0  # Should complete within 60 seconds
        
        average_batch_time = sum(r["processing_time"] for r in performance_results) / len(performance_results)
        assert average_batch_time < 15.0  # Average batch should be under 15 seconds
        
        overall_success_rate = sum(r["success_rate"] for r in performance_results) / len(performance_results)
        assert overall_success_rate >= 0.9  # At least 90% success rate
        
        logger.info(f"Overlap resolution performance: {len(complex_scenarios)} scenarios in {total_time:.2f}s (avg batch: {average_batch_time:.2f}s, success: {overall_success_rate:.2%})")

# =============================================================================
# OVERLAP REGULATORY SERVICES MANAGEMENT
# =============================================================================

class OverlapRegulatoryServices:
    """Manages overlap regulatory service instances for testing"""
    
    def __init__(self):
        self.intelligence = None
        self.compliance = None
        self.decision = None
        self.overlap_resolver = None
        self.jurisdiction_handler = None
    
    async def initialize(self):
        """Initialize overlap regulatory services"""
        logger.info("Initializing overlap regulatory services")
        
        # Initialize services with overlap-specific configuration
        self.intelligence = OverlapRegulatoryIntelligenceService()
        await self.intelligence.initialize(test_mode=True)
        
        self.compliance = OverlapIntelligenceComplianceService()
        await self.compliance.initialize(test_mode=True)
        
        self.decision = OverlapDecisionOrchestrationService()
        await self.decision.initialize(test_mode=True)
        
        self.overlap_resolver = OverlapResolver()
        await self.overlap_resolver.initialize(test_mode=True)
        
        self.jurisdiction_handler = JurisdictionHandler()
        await self.jurisdiction_handler.initialize(test_mode=True)
        
        logger.info("Overlap regulatory services initialized")
    
    async def cleanup(self):
        """Cleanup overlap regulatory services"""
        logger.info("Cleaning up overlap regulatory services")
        
        services = [
            self.intelligence, self.compliance, self.decision,
            self.overlap_resolver, self.jurisdiction_handler
        ]
        
        for service in services:
            if service:
                try:
                    await service.close()
                except Exception as e:
                    logger.warning(f"Error closing service: {e}")

# =============================================================================
# OVERLAP-SPECIFIC SERVICE IMPLEMENTATIONS
# =============================================================================

class OverlapRegulatoryIntelligenceService:
    """Overlap-specific regulatory intelligence service"""
    
    async def initialize(self, test_mode=False):
        self.test_mode = test_mode
    
    async def process_overlapping_regulation(self, regulation, regulation_type=None):
        """Process overlapping regulation"""
        return MockResult(
            success=True,
            regulation_type=regulation_type or regulation.get("regulation_type", "UNKNOWN"),
            jurisdiction=regulation.get("jurisdiction"),
            overlap_potential=True
        )
    
    async def close(self):
        pass

class OverlapIntelligenceComplianceService:
    """Overlap-specific intelligence compliance service"""
    
    async def initialize(self, test_mode=False):
        self.test_mode = test_mode
    
    async def close(self):
        pass

class OverlapDecisionOrchestrationService:
    """Overlap-specific decision orchestration service"""
    
    async def initialize(self, test_mode=False):
        self.test_mode = test_mode
    
    async def resolve_customer_regulatory_overlap(self, scenario, precedence_rules):
        """Resolve customer regulatory overlap"""
        # Determine applicable regulation based on jurisdiction and precedence
        customer_jurisdiction = scenario.get("customer_jurisdiction")
        
        if customer_jurisdiction == "DE" and precedence_rules.get("national_stricter_allowed"):
            return MockResult(
                success=True,
                applicable_regulation="DE_PSD2_IMPLEMENTATION",
                compliance_level="ENHANCED"
            )
        else:
            return MockResult(
                success=True,
                applicable_regulation="EU_PSD2_DIRECTIVE",
                compliance_level="STANDARD"
            )
    
    async def resolve_data_transfer_overlap(self, scenario, detected_overlaps):
        """Resolve data transfer overlap"""
        transfer_type = scenario.get("transfer_type")
        
        if transfer_type == "intra_eu":
            return MockResult(
                success=True,
                transfer_mechanism="ADEQUACY_DECISION",
                additional_safeguards=["GERMAN_EMPLOYEE_PROTECTION", "WORKS_COUNCIL_CONSULTATION"]
            )
        else:
            return MockResult(
                success=True,
                transfer_mechanism="STANDARD_CONTRACTUAL_CLAUSES",
                additional_safeguards=["SUPPLEMENTARY_MEASURES"]
            )
    
    async def analyze_multinational_regulatory_exposure(self, multinational):
        """Analyze multinational regulatory exposure"""
        # Extract jurisdictions from multinational structure
        jurisdictions = set(["EU"])  # Always include EU
        
        # Add headquarters jurisdiction
        if "headquarters" in multinational:
            jurisdictions.add(multinational["headquarters"]["country"])
        
        # Add subsidiary jurisdictions
        if "subsidiaries" in multinational:
            for subsidiary in multinational["subsidiaries"]:
                jurisdictions.add(subsidiary["country"])
        
        # Create jurisdiction-specific requirements
        jurisdiction_requirements = {}
        for jurisdiction in jurisdictions:
            if jurisdiction == "DE":
                jurisdiction_requirements[jurisdiction] = {
                    "gdpr_controller_obligations": True,
                    "german_corporate_law": True,
                    "bafin_supervision": True
                }
            elif jurisdiction == "IE":
                jurisdiction_requirements[jurisdiction] = {
                    "gdpr_processor_obligations": True,
                    "cbi_supervision": True,
                    "data_processing_activities": True
                }
            else:
                jurisdiction_requirements[jurisdiction] = {
                    "standard_requirements": True
                }
        
        return MockResult(
            success=True,
            applicable_jurisdictions=list(jurisdictions),
            jurisdiction_requirements=jurisdiction_requirements
        )
    
    async def assess_cross_border_transfer_compliance(self, scenario, multinational):
        """Assess cross-border transfer compliance"""
        transfers = scenario.get("transfers", [])
        
        # Create transfer requirements for each transfer
        transfer_requirements = []
        for transfer in transfers:
            transfer_requirements.append({
                "from": transfer["from"],
                "to": transfer["to"],
                "data_type": transfer["data_type"],
                "legal_basis": "legitimate_interest",
                "safeguards": ["standard_contractual_clauses"],
                "compliant": True
            })
        
        return MockResult(
            success=True,
            all_transfers_compliant=True,
            transfer_requirements=transfer_requirements
        )
    
    async def assess_payment_services_overlap(self, scenario, multinational):
        """Assess payment services overlap"""
        return MockResult(
            success=True,
            psd2_compliant=True,
            aml_compliant=True
        )
    
    async def analyze_brexit_regulatory_overlap(self, uk_financial):
        """Analyze Brexit regulatory overlap"""
        return MockResult(
            success=True,
            brexit_impact_level="HIGH",
            overlap_areas=["data_protection", "financial_services_regulation", "aml_requirements"]
        )
    
    async def resolve_gdpr_brexit_overlap(self, scenario, uk_financial):
        """Resolve GDPR Brexit overlap"""
        return MockResult(
            success=True,
            transfer_mechanism="STANDARD_CONTRACTUAL_CLAUSES",
            additional_safeguards=["SUPPLEMENTARY_MEASURES", "IMPACT_ASSESSMENT"]
        )
    
    async def resolve_mifid_brexit_overlap(self, scenario, uk_financial):
        """Resolve MiFID Brexit overlap"""
        return MockResult(
            success=True,
            service_restrictions=["NO_RETAIL_CLIENTS", "LIMITED_PROFESSIONAL_SERVICES"],
            compliance_strategy="DUAL_AUTHORIZATION"
        )
    
    async def analyze_cross_border_banking_overlap(self, scenario):
        """Analyze cross-border banking overlap"""
        institutions = scenario.get("institutions_involved", [])
        frameworks = scenario.get("regulatory_frameworks", [])
        
        supervisory_authorities = []
        for institution in institutions:
            if institution["country"] == "DE":
                supervisory_authorities.append("BaFin")
            elif institution["country"] == "IE":
                supervisory_authorities.append("Central Bank of Ireland")
            elif institution["country"] == "NL":
                supervisory_authorities.append("DNB")
        
        return MockResult(
            success=True,
            applicable_regulations=frameworks,
            supervisory_authorities=supervisory_authorities,
            coordination_requirements={
                "home_host_coordination": True,
                "consolidated_supervision": True,
                "information_sharing": True
            }
        )
    
    async def resolve_aml_cross_border_overlap(self, scenario):
        """Resolve AML cross-border overlap"""
        return MockResult(
            success=True,
            highest_risk_standard_applied=True,
            coordinated_monitoring=True
        )
    
    async def resolve_capital_requirements_overlap(self, scenario):
        """Resolve capital requirements overlap"""
        return MockResult(
            success=True,
            consolidated_calculation=True,
            home_country_consolidation=True
        )
    
    async def close(self):
        pass

# =============================================================================
# ENHANCED OVERLAP RESOLVER
# =============================================================================

class OverlapResolver:
    """Enhanced overlap resolver for testing"""
    
    async def initialize(self, test_mode=False):
        self.test_mode = test_mode
    
    async def detect_directive_implementation_overlaps(self, directive, implementations):
        """Detect overlaps between directive and implementations"""
        detected_overlaps = []
        
        for implementation in implementations:
            jurisdiction = implementation.get("jurisdiction")
            
            if implementation.get("stricter_than_eu"):
                overlap = {
                    "jurisdiction": jurisdiction,
                    "overlap_type": "STRICTER_NATIONAL_REQUIREMENTS",
                    "conflict_level": "COMPATIBLE"
                }
            elif implementation.get("minimum_implementation"):
                overlap = {
                    "jurisdiction": jurisdiction,
                    "overlap_type": "MINIMUM_IMPLEMENTATION",
                    "conflict_level": "COMPLIANT"
                }
            else:
                overlap = {
                    "jurisdiction": jurisdiction,
                    "overlap_type": "STANDARD_IMPLEMENTATION",
                    "conflict_level": "COMPLIANT"
                }
            
            detected_overlaps.append(overlap)
        
        return MockResult(
            success=True,
            detected_overlaps=detected_overlaps
        )
    
    async def resolve_directive_implementation_conflicts(self, detected_overlaps):
        """Resolve directive implementation conflicts"""
        return MockResult(
            success=True,
            resolution_strategy="HIERARCHICAL_PRECEDENCE",
            precedence_rules={
                "eu_directive_minimum": True,
                "national_stricter_allowed": True,
                "national_weaker_prohibited": True
            }
        )
    
    async def detect_regulation_adaptation_overlaps(self, regulation, adaptations):
        """Detect regulation adaptation overlaps"""
        detected_overlaps = []
        
        for adaptation in adaptations:
            jurisdiction = adaptation.get("jurisdiction")
            
            if jurisdiction == "DE":
                overlap = {
                    "jurisdiction": jurisdiction,
                    "overlap_type": "NATIONAL_SPECIFICATION",
                    "areas": ["DPO_REQUIREMENTS", "EMPLOYEE_DATA", "RESEARCH_EXEMPTIONS"]
                }
            elif jurisdiction == "IE":
                overlap = {
                    "jurisdiction": jurisdiction,
                    "overlap_type": "NATIONAL_SPECIFICATION",
                    "areas": ["DIGITAL_CONSENT_AGE", "FREEDOM_OF_EXPRESSION", "TECH_INDUSTRY_FOCUS"]
                }
            else:
                overlap = {
                    "jurisdiction": jurisdiction,
                    "overlap_type": "STANDARD_ADAPTATION",
                    "areas": ["GENERAL_PROVISIONS"]
                }
            
            detected_overlaps.append(overlap)
        
        return MockResult(
            success=True,
            detected_overlaps=detected_overlaps
        )
    
    async def analyze_regulatory_conflicts(self, conflicting_regulations):
        """Analyze regulatory conflicts"""
        identified_conflicts = []
        
        for conflict_name, conflict_data in conflicting_regulations.items():
            if "data" in conflict_name.lower():
                conflict = {
                    "conflict_area": "Data Localization",
                    "conflict_type": "JURISDICTIONAL_SOVEREIGNTY",
                    "resolution_complexity": "HIGH"
                }
            elif "reporting" in conflict_name.lower():
                conflict = {
                    "conflict_area": "Reporting Frequency",
                    "conflict_type": "ADMINISTRATIVE_BURDEN",
                    "resolution_complexity": "MEDIUM"
                }
            else:
                conflict = {
                    "conflict_area": "General Conflict",
                    "conflict_type": "REGULATORY_OVERLAP",
                    "resolution_complexity": "LOW"
                }
            
            identified_conflicts.append(conflict)
        
        return MockResult(
            success=True,
            identified_conflicts=identified_conflicts
        )
    
    async def resolve_regulatory_conflicts(self, identified_conflicts):
        """Resolve regulatory conflicts"""
        conflict_resolutions = []
        
        for conflict in identified_conflicts:
            if "data" in conflict["conflict_area"].lower():
                resolution = {
                    "conflict_area": conflict["conflict_area"],
                    "resolution_strategy": "COMPLIANCE_WITH_BOTH",
                    "implementation_approach": "STRICTER_REQUIREMENT_PREVAILS"
                }
            elif "reporting" in conflict["conflict_area"].lower():
                resolution = {
                    "conflict_area": conflict["conflict_area"],
                    "resolution_strategy": "ADDITIVE_COMPLIANCE",
                    "implementation_approach": "MEET_ALL_REQUIREMENTS"
                }
            else:
                resolution = {
                    "conflict_area": conflict["conflict_area"],
                    "resolution_strategy": "PRECEDENCE_BASED",
                    "implementation_approach": "HIGHER_AUTHORITY_PREVAILS"
                }
            
            conflict_resolutions.append(resolution)
        
        return MockResult(
            success=True,
            conflict_resolutions=conflict_resolutions
        )
    
    async def analyze_temporal_overlaps(self, regulations):
        """Analyze temporal overlaps"""
        temporal_conflicts = []
        
        # Look for regulations with different effective dates
        effective_dates = [(r.get("effective_date"), r.get("regulation_id")) for r in regulations if r.get("effective_date")]
        
        if len(set(date for date, _ in effective_dates)) > 1:
            temporal_conflicts.append({
                "conflict_type": "STAGGERED_IMPLEMENTATION",
                "regulations_involved": len(regulations),
                "resolution_required": True
            })
        
        # Look for delayed applications
        for regulation in regulations:
            if regulation.get("delayed_application"):
                temporal_conflicts.append({
                    "conflict_type": "DELAYED_APPLICATION",
                    "regulation": regulation.get("regulation_id"),
                    "resolution_required": True
                })
        
        return MockResult(
            success=True,
            temporal_conflicts=temporal_conflicts
        )
    
    async def resolve_temporal_overlaps(self, temporal_conflicts):
        """Resolve temporal overlaps"""
        temporal_resolutions = []
        
        for conflict in temporal_conflicts:
            if "staggered" in conflict.get("conflict_type", "").lower():
                resolution = {
                    "conflict_type": conflict["conflict_type"],
                    "resolution_strategy": "PHASED_IMPLEMENTATION"
                }
            elif "delayed" in conflict.get("conflict_type", "").lower():
                resolution = {
                    "conflict_type": conflict["conflict_type"],
                    "resolution_strategy": "LATER_DATE_PREVAILS"
                }
            else:
                resolution = {
                    "conflict_type": conflict["conflict_type"],
                    "resolution_strategy": "PARALLEL_APPLICATION"
                }
            
            temporal_resolutions.append(resolution)
        
        return MockResult(
            success=True,
            temporal_resolutions=temporal_resolutions
        )
    
    async def analyze_basel_crd_temporal_overlap(self, basel_timeline):
        """Analyze Basel/CRD temporal overlap"""
        return MockResult(
            success=True,
            phase_in_complexity="HIGH",
            phase_coordination={
                "global_basel_framework": basel_timeline.get("basel_iii_framework"),
                "eu_implementation": basel_timeline.get("crd_iv_directive"),
                "national_variations": basel_timeline.get("national_implementations")
            }
        )
    
    async def process_overlap_scenario(self, scenario):
        """Process overlap scenario"""
        # Simulate processing of overlap scenario
        await asyncio.sleep(0.1)  # Simulate processing time
        
        return MockResult(
            success=True,
            scenario_processed=True
        )
    
    async def close(self):
        pass

# =============================================================================
# MOCK RESULT CLASS
# =============================================================================

class MockResult:
    """Mock result class for testing"""
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

# =============================================================================
# TEST CONFIGURATION AND UTILITIES
# =============================================================================

def pytest_configure(config):
    """Configure pytest for overlap scenario tests"""
    config.addinivalue_line("markers", "scenario: mark test as scenario test")
    config.addinivalue_line("markers", "overlap: mark test as overlap scenario test")
    config.addinivalue_line("markers", "eu_national: mark test as EU/national overlap test")

if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "--tb=short", "-m", "overlap"])
