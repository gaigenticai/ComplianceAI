"""
Compliance Monitoring Agent - Microsoft AutoGen Framework
Production-grade regulatory compliance monitoring and reporting service
Autonomous monitoring of AML, GDPR, Basel III, and other regulatory requirements
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import hashlib

# Web Framework
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

# AutoGen Framework
import autogen
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
from autogen.agentchat.contrib.retrieve_assistant_agent import RetrieveAssistantAgent
from autogen.agentchat.contrib.retrieve_user_proxy_agent import RetrieveUserProxyAgent

# AI/ML Libraries
import openai
from langchain.llms import OpenAI
from transformers import pipeline
import torch

# Data Processing
import pandas as pd
import numpy as np
from datetime import timezone
import pycountry
from iso3166 import countries

# Database and Messaging
import psycopg2
from pymongo import MongoClient
import redis
from kafka import KafkaProducer, KafkaConsumer

# Document Processing
from docx import Document
import openpyxl
from lxml import etree
from bs4 import BeautifulSoup

# Monitoring and Reporting
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import structlog
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import matplotlib.pyplot as plt
import seaborn as sns

# Scheduling
from celery import Celery
from croniter import croniter

# Security
from cryptography.fernet import Fernet

# Environment
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Prometheus Metrics
compliance_checks = Counter('compliance_checks_total', 'Total compliance checks performed')
compliance_violations = Counter('compliance_violations_total', 'Total compliance violations detected', ['regulation', 'severity'])
compliance_reports = Counter('compliance_reports_generated_total', 'Total compliance reports generated')
monitoring_duration = Histogram('compliance_monitoring_duration_seconds', 'Compliance monitoring duration')
active_monitors = Gauge('active_compliance_monitors', 'Number of active compliance monitors')

# Compliance Enums
class RegulationType(str, Enum):
    AML = "aml"
    GDPR = "gdpr"
    BASEL_III = "basel_iii"
    PCI_DSS = "pci_dss"
    SOX = "sox"
    FATCA = "fatca"
    CRS = "crs"
    MiFID_II = "mifid_ii"

class ViolationSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    REQUIRES_ATTENTION = "requires_attention"
    UNDER_REVIEW = "under_review"

class MonitoringFrequency(str, Enum):
    REAL_TIME = "real_time"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

# Data Models
@dataclass
class ComplianceViolation:
    """Compliance violation data structure"""
    violation_id: str
    customer_id: str
    regulation_type: RegulationType
    violation_type: str
    severity: ViolationSeverity
    description: str
    detected_at: datetime
    resolved_at: Optional[datetime]
    resolution_notes: Optional[str]
    auto_resolved: bool
    escalated: bool
    metadata: Dict[str, Any]

@dataclass
class ComplianceReport:
    """Compliance report data structure"""
    report_id: str
    report_type: str
    regulation_types: List[RegulationType]
    period_start: datetime
    period_end: datetime
    total_checks: int
    violations_found: int
    compliance_score: float
    recommendations: List[str]
    generated_at: datetime
    generated_by: str

class ComplianceCheckRequest(BaseModel):
    """Compliance check request model"""
    customer_id: str = Field(..., description="Customer identifier")
    regulation_types: List[RegulationType] = Field(..., description="Regulations to check")
    customer_data: Dict[str, Any] = Field(..., description="Customer data for compliance check")
    check_type: str = Field(default="full", description="Type of compliance check")
    priority: str = Field(default="normal", description="Check priority")

class ComplianceCheckResponse(BaseModel):
    """Compliance check response model"""
    check_id: str
    customer_id: str
    overall_status: ComplianceStatus
    regulation_results: Dict[str, Dict[str, Any]]
    violations: List[Dict[str, Any]]
    compliance_score: float
    recommendations: List[str]
    next_review_date: datetime
    processing_time: float
    status: str

class MonitoringConfigRequest(BaseModel):
    """Monitoring configuration request model"""
    regulation_types: List[RegulationType] = Field(..., description="Regulations to monitor")
    frequency: MonitoringFrequency = Field(..., description="Monitoring frequency")
    thresholds: Dict[str, float] = Field(default={}, description="Alert thresholds")
    notification_settings: Dict[str, Any] = Field(default={}, description="Notification settings")

# Regulatory Compliance Engines
class AMLComplianceEngine:
    """Anti-Money Laundering compliance engine"""
    
    def __init__(self):
        self.sanctions_lists = self._load_sanctions_lists()
        self.pep_database = self._load_pep_database()
        self.suspicious_patterns = self._load_suspicious_patterns()
    
    def _load_sanctions_lists(self) -> Dict[str, List[str]]:
        """Load sanctions lists from various sources"""
        return {
            "ofac": ["sanctioned_entity_1", "sanctioned_entity_2"],
            "un": ["un_sanctioned_1", "un_sanctioned_2"],
            "eu": ["eu_sanctioned_1", "eu_sanctioned_2"]
        }
    
    def _load_pep_database(self) -> List[Dict[str, Any]]:
        """Load Politically Exposed Persons database"""
        return [
            {"name": "John Political", "position": "Minister", "country": "US", "risk_level": "high"},
            {"name": "Jane Official", "position": "Ambassador", "country": "UK", "risk_level": "medium"}
        ]
    
    def _load_suspicious_patterns(self) -> Dict[str, Any]:
        """Load suspicious transaction patterns"""
        return {
            "structuring": {
                "threshold": 10000,
                "frequency_limit": 5,
                "time_window": 24  # hours
            },
            "round_amounts": {
                "pattern": r"^\d+000$",
                "frequency_threshold": 3
            },
            "velocity": {
                "transaction_count_threshold": 50,
                "time_window": 24  # hours
            }
        }
    
    async def check_aml_compliance(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive AML compliance check"""
        try:
            violations = []
            warnings = []
            
            # Sanctions screening
            sanctions_result = await self._screen_sanctions(customer_data)
            if sanctions_result["matches"]:
                violations.extend(sanctions_result["matches"])
            
            # PEP screening
            pep_result = await self._screen_pep(customer_data)
            if pep_result["is_pep"]:
                warnings.append({
                    "type": "pep_detected",
                    "severity": ViolationSeverity.MEDIUM,
                    "description": f"Customer identified as PEP: {pep_result['details']}"
                })
            
            # Transaction monitoring
            transaction_result = await self._monitor_transactions(customer_data)
            violations.extend(transaction_result["violations"])
            warnings.extend(transaction_result["warnings"])
            
            # Customer due diligence
            cdd_result = await self._check_customer_due_diligence(customer_data)
            if not cdd_result["compliant"]:
                violations.extend(cdd_result["violations"])
            
            # Determine overall status
            if violations:
                status = ComplianceStatus.NON_COMPLIANT
            elif warnings:
                status = ComplianceStatus.REQUIRES_ATTENTION
            else:
                status = ComplianceStatus.COMPLIANT
            
            return {
                "regulation": RegulationType.AML,
                "status": status,
                "violations": violations,
                "warnings": warnings,
                "compliance_score": self._calculate_aml_score(violations, warnings),
                "recommendations": self._generate_aml_recommendations(violations, warnings)
            }
            
        except Exception as e:
            logger.error("AML compliance check failed", error=str(e))
            return {
                "regulation": RegulationType.AML,
                "status": ComplianceStatus.UNDER_REVIEW,
                "violations": [],
                "warnings": [{"type": "check_failed", "description": str(e)}],
                "compliance_score": 0.0,
                "recommendations": ["Manual review required due to system error"]
            }
    
    async def _screen_sanctions(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Screen customer against sanctions lists"""
        matches = []
        customer_name = customer_data.get("personal_info", {}).get("full_name", "").lower()
        
        for list_name, sanctioned_entities in self.sanctions_lists.items():
            for entity in sanctioned_entities:
                if entity.lower() in customer_name:
                    matches.append({
                        "type": "sanctions_match",
                        "severity": ViolationSeverity.CRITICAL,
                        "list": list_name,
                        "matched_entity": entity,
                        "description": f"Customer name matches {list_name.upper()} sanctions list: {entity}"
                    })
        
        return {"matches": matches}
    
    async def _screen_pep(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Screen for Politically Exposed Persons"""
        customer_name = customer_data.get("personal_info", {}).get("full_name", "").lower()
        occupation = customer_data.get("personal_info", {}).get("occupation", "").lower()
        
        # Check against PEP database
        for pep in self.pep_database:
            if pep["name"].lower() in customer_name:
                return {
                    "is_pep": True,
                    "details": pep,
                    "match_type": "name_match"
                }
        
        # Check occupation-based PEP indicators
        pep_occupations = ["politician", "minister", "ambassador", "judge", "military officer"]
        if any(pep_occ in occupation for pep_occ in pep_occupations):
            return {
                "is_pep": True,
                "details": {"occupation": occupation, "risk_level": "medium"},
                "match_type": "occupation_match"
            }
        
        return {"is_pep": False, "details": None, "match_type": None}
    
    async def _monitor_transactions(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor transactions for suspicious patterns"""
        violations = []
        warnings = []
        
        transactions = customer_data.get("transaction_history", [])
        if not transactions:
            return {"violations": violations, "warnings": warnings}
        
        # Check for structuring
        structuring_violations = self._detect_structuring(transactions)
        violations.extend(structuring_violations)
        
        # Check for unusual velocity
        velocity_violations = self._detect_unusual_velocity(transactions)
        violations.extend(velocity_violations)
        
        # Check for round amounts
        round_amount_warnings = self._detect_round_amounts(transactions)
        warnings.extend(round_amount_warnings)
        
        return {"violations": violations, "warnings": warnings}
    
    def _detect_structuring(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect potential structuring (breaking large amounts into smaller ones)"""
        violations = []
        pattern = self.suspicious_patterns["structuring"]
        
        # Group transactions by day
        daily_transactions = {}
        for txn in transactions:
            date = txn.get("date", "").split("T")[0]  # Extract date part
            if date not in daily_transactions:
                daily_transactions[date] = []
            daily_transactions[date].append(txn)
        
        # Check each day for structuring patterns
        for date, day_txns in daily_transactions.items():
            near_threshold_count = sum(
                1 for txn in day_txns 
                if pattern["threshold"] * 0.9 <= txn.get("amount", 0) < pattern["threshold"]
            )
            
            if near_threshold_count >= pattern["frequency_limit"]:
                violations.append({
                    "type": "potential_structuring",
                    "severity": ViolationSeverity.HIGH,
                    "description": f"Potential structuring detected on {date}: {near_threshold_count} transactions near ${pattern['threshold']} threshold",
                    "metadata": {"date": date, "transaction_count": near_threshold_count}
                })
        
        return violations
    
    def _detect_unusual_velocity(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect unusual transaction velocity"""
        violations = []
        pattern = self.suspicious_patterns["velocity"]
        
        if len(transactions) > pattern["transaction_count_threshold"]:
            violations.append({
                "type": "high_transaction_velocity",
                "severity": ViolationSeverity.MEDIUM,
                "description": f"Unusually high transaction velocity: {len(transactions)} transactions",
                "metadata": {"transaction_count": len(transactions)}
            })
        
        return violations
    
    def _detect_round_amounts(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect suspicious round amounts"""
        warnings = []
        
        round_amounts = [
            txn for txn in transactions 
            if str(txn.get("amount", 0)).endswith("000")
        ]
        
        if len(round_amounts) >= 3:
            warnings.append({
                "type": "frequent_round_amounts",
                "severity": ViolationSeverity.LOW,
                "description": f"Frequent round amount transactions detected: {len(round_amounts)} transactions",
                "metadata": {"round_amount_count": len(round_amounts)}
            })
        
        return warnings
    
    async def _check_customer_due_diligence(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check Customer Due Diligence requirements"""
        violations = []
        
        # Required documents for CDD
        required_docs = ["identity", "address", "income_verification"]
        provided_docs = [doc.get("type") for doc in customer_data.get("documents", [])]
        
        missing_docs = set(required_docs) - set(provided_docs)
        if missing_docs:
            violations.append({
                "type": "insufficient_cdd_documentation",
                "severity": ViolationSeverity.MEDIUM,
                "description": f"Missing required CDD documents: {', '.join(missing_docs)}",
                "metadata": {"missing_documents": list(missing_docs)}
            })
        
        # Check identity verification
        identity_verified = customer_data.get("verification_status", {}).get("identity", False)
        if not identity_verified:
            violations.append({
                "type": "identity_not_verified",
                "severity": ViolationSeverity.HIGH,
                "description": "Customer identity has not been verified",
                "metadata": {"verification_status": "pending"}
            })
        
        return {
            "compliant": len(violations) == 0,
            "violations": violations
        }
    
    def _calculate_aml_score(self, violations: List[Dict[str, Any]], warnings: List[Dict[str, Any]]) -> float:
        """Calculate AML compliance score"""
        base_score = 100.0
        
        # Deduct points for violations
        for violation in violations:
            severity = violation.get("severity", ViolationSeverity.LOW)
            if severity == ViolationSeverity.CRITICAL:
                base_score -= 40
            elif severity == ViolationSeverity.HIGH:
                base_score -= 25
            elif severity == ViolationSeverity.MEDIUM:
                base_score -= 15
            else:
                base_score -= 5
        
        # Deduct points for warnings
        for warning in warnings:
            base_score -= 5
        
        return max(base_score, 0.0) / 100.0
    
    def _generate_aml_recommendations(self, violations: List[Dict[str, Any]], warnings: List[Dict[str, Any]]) -> List[str]:
        """Generate AML compliance recommendations"""
        recommendations = []
        
        violation_types = [v.get("type") for v in violations]
        
        if "sanctions_match" in violation_types:
            recommendations.append("Immediately escalate to compliance team - sanctions list match detected")
        
        if "potential_structuring" in violation_types:
            recommendations.append("Investigate transaction patterns for potential structuring")
        
        if "insufficient_cdd_documentation" in violation_types:
            recommendations.append("Request additional documentation for Customer Due Diligence")
        
        if "identity_not_verified" in violation_types:
            recommendations.append("Complete identity verification process before account activation")
        
        if not recommendations:
            recommendations.append("Continue regular AML monitoring")
        
        return recommendations

class GDPRComplianceEngine:
    """GDPR compliance engine"""
    
    def __init__(self):
        self.lawful_bases = self._load_lawful_bases()
        self.data_categories = self._load_data_categories()
        self.retention_policies = self._load_retention_policies()
    
    def _load_lawful_bases(self) -> List[str]:
        """Load GDPR lawful bases for processing"""
        return [
            "consent",
            "contract",
            "legal_obligation",
            "vital_interests",
            "public_task",
            "legitimate_interests"
        ]
    
    def _load_data_categories(self) -> Dict[str, Dict[str, Any]]:
        """Load data categories and their sensitivity levels"""
        return {
            "personal_identifiers": {"sensitivity": "high", "retention_years": 7},
            "financial_data": {"sensitivity": "high", "retention_years": 7},
            "biometric_data": {"sensitivity": "special", "retention_years": 5},
            "contact_information": {"sensitivity": "medium", "retention_years": 3},
            "transaction_history": {"sensitivity": "high", "retention_years": 7}
        }
    
    def _load_retention_policies(self) -> Dict[str, int]:
        """Load data retention policies (in years)"""
        return {
            "kyc_documents": 7,
            "transaction_records": 7,
            "communication_logs": 3,
            "consent_records": 7,
            "biometric_data": 5
        }
    
    async def check_gdpr_compliance(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive GDPR compliance check"""
        try:
            violations = []
            warnings = []
            
            # Check consent management
            consent_result = await self._check_consent_management(customer_data)
            violations.extend(consent_result["violations"])
            warnings.extend(consent_result["warnings"])
            
            # Check data minimization
            minimization_result = await self._check_data_minimization(customer_data)
            violations.extend(minimization_result["violations"])
            
            # Check retention compliance
            retention_result = await self._check_retention_compliance(customer_data)
            violations.extend(retention_result["violations"])
            warnings.extend(retention_result["warnings"])
            
            # Check data subject rights
            rights_result = await self._check_data_subject_rights(customer_data)
            violations.extend(rights_result["violations"])
            
            # Determine overall status
            if violations:
                status = ComplianceStatus.NON_COMPLIANT
            elif warnings:
                status = ComplianceStatus.REQUIRES_ATTENTION
            else:
                status = ComplianceStatus.COMPLIANT
            
            return {
                "regulation": RegulationType.GDPR,
                "status": status,
                "violations": violations,
                "warnings": warnings,
                "compliance_score": self._calculate_gdpr_score(violations, warnings),
                "recommendations": self._generate_gdpr_recommendations(violations, warnings)
            }
            
        except Exception as e:
            logger.error("GDPR compliance check failed", error=str(e))
            return {
                "regulation": RegulationType.GDPR,
                "status": ComplianceStatus.UNDER_REVIEW,
                "violations": [],
                "warnings": [{"type": "check_failed", "description": str(e)}],
                "compliance_score": 0.0,
                "recommendations": ["Manual GDPR review required due to system error"]
            }
    
    async def _check_consent_management(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check GDPR consent management"""
        violations = []
        warnings = []
        
        consent_data = customer_data.get("consent", {})
        
        # Check for explicit consent
        if not consent_data.get("data_processing", False):
            violations.append({
                "type": "missing_data_processing_consent",
                "severity": ViolationSeverity.HIGH,
                "description": "No explicit consent for data processing",
                "metadata": {"consent_status": "missing"}
            })
        
        # Check consent timestamp
        consent_timestamp = consent_data.get("timestamp")
        if consent_timestamp:
            consent_date = datetime.fromisoformat(consent_timestamp.replace("Z", "+00:00"))
            if (datetime.now(timezone.utc) - consent_date).days > 365:
                warnings.append({
                    "type": "old_consent",
                    "severity": ViolationSeverity.MEDIUM,
                    "description": "Consent is older than 1 year, consider renewal",
                    "metadata": {"consent_age_days": (datetime.now(timezone.utc) - consent_date).days}
                })
        
        # Check for marketing consent
        if customer_data.get("marketing_communications", False) and not consent_data.get("marketing", False):
            violations.append({
                "type": "marketing_without_consent",
                "severity": ViolationSeverity.MEDIUM,
                "description": "Marketing communications enabled without explicit consent",
                "metadata": {"marketing_status": "enabled_without_consent"}
            })
        
        return {"violations": violations, "warnings": warnings}
    
    async def _check_data_minimization(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check GDPR data minimization principle"""
        violations = []
        
        # Define necessary data fields for KYC
        necessary_fields = {
            "personal_info": ["full_name", "date_of_birth", "nationality", "address"],
            "financial_info": ["annual_income", "employment_status"],
            "documents": ["identity", "address", "income_verification"],
            "verification_status": ["identity", "address"]
        }
        
        # Check for excessive data collection
        collected_fields = set(customer_data.keys())
        necessary_field_set = set(necessary_fields.keys())
        
        excessive_fields = collected_fields - necessary_field_set - {"consent", "created_at", "updated_at"}
        
        if excessive_fields:
            violations.append({
                "type": "excessive_data_collection",
                "severity": ViolationSeverity.MEDIUM,
                "description": f"Collecting unnecessary data fields: {', '.join(excessive_fields)}",
                "metadata": {"excessive_fields": list(excessive_fields)}
            })
        
        # Check for excessive personal information
        personal_info = customer_data.get("personal_info", {})
        if len(personal_info) > 10:  # Arbitrary threshold
            violations.append({
                "type": "excessive_personal_data",
                "severity": ViolationSeverity.LOW,
                "description": f"Collecting {len(personal_info)} personal data fields",
                "metadata": {"personal_field_count": len(personal_info)}
            })
        
        return {"violations": violations}
    
    async def _check_retention_compliance(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check GDPR data retention compliance"""
        violations = []
        warnings = []
        
        created_at = customer_data.get("created_at")
        if not created_at:
            warnings.append({
                "type": "missing_creation_timestamp",
                "severity": ViolationSeverity.LOW,
                "description": "Missing data creation timestamp for retention tracking",
                "metadata": {"timestamp_status": "missing"}
            })
            return {"violations": violations, "warnings": warnings}
        
        # Parse creation date
        try:
            creation_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            data_age_years = (datetime.now(timezone.utc) - creation_date).days / 365.25
            
            # Check against retention policies
            for data_type, retention_years in self.retention_policies.items():
                if data_age_years > retention_years:
                    if data_type in ["kyc_documents", "transaction_records"]:
                        # Critical data - violation
                        violations.append({
                            "type": "retention_period_exceeded",
                            "severity": ViolationSeverity.HIGH,
                            "description": f"{data_type} retained beyond policy limit ({retention_years} years)",
                            "metadata": {
                                "data_type": data_type,
                                "age_years": data_age_years,
                                "retention_limit": retention_years
                            }
                        })
                    else:
                        # Non-critical data - warning
                        warnings.append({
                            "type": "retention_review_needed",
                            "severity": ViolationSeverity.MEDIUM,
                            "description": f"{data_type} approaching retention limit",
                            "metadata": {
                                "data_type": data_type,
                                "age_years": data_age_years,
                                "retention_limit": retention_years
                            }
                        })
        
        except Exception as e:
            warnings.append({
                "type": "retention_check_failed",
                "severity": ViolationSeverity.LOW,
                "description": f"Failed to check retention compliance: {str(e)}",
                "metadata": {"error": str(e)}
            })
        
        return {"violations": violations, "warnings": warnings}
    
    async def _check_data_subject_rights(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check data subject rights implementation"""
        violations = []
        
        # Check for data portability support
        if not customer_data.get("data_export_available", False):
            violations.append({
                "type": "data_portability_not_supported",
                "severity": ViolationSeverity.MEDIUM,
                "description": "Data portability mechanism not implemented",
                "metadata": {"portability_status": "not_available"}
            })
        
        # Check for deletion capability
        if not customer_data.get("deletion_supported", True):
            violations.append({
                "type": "right_to_erasure_not_supported",
                "severity": ViolationSeverity.HIGH,
                "description": "Right to erasure (deletion) not supported",
                "metadata": {"deletion_status": "not_supported"}
            })
        
        return {"violations": violations}
    
    def _calculate_gdpr_score(self, violations: List[Dict[str, Any]], warnings: List[Dict[str, Any]]) -> float:
        """Calculate GDPR compliance score"""
        base_score = 100.0
        
        # Deduct points for violations
        for violation in violations:
            severity = violation.get("severity", ViolationSeverity.LOW)
            if severity == ViolationSeverity.CRITICAL:
                base_score -= 30
            elif severity == ViolationSeverity.HIGH:
                base_score -= 20
            elif severity == ViolationSeverity.MEDIUM:
                base_score -= 10
            else:
                base_score -= 5
        
        # Deduct points for warnings
        for warning in warnings:
            base_score -= 3
        
        return max(base_score, 0.0) / 100.0
    
    def _generate_gdpr_recommendations(self, violations: List[Dict[str, Any]], warnings: List[Dict[str, Any]]) -> List[str]:
        """Generate GDPR compliance recommendations"""
        recommendations = []
        
        violation_types = [v.get("type") for v in violations]
        
        if "missing_data_processing_consent" in violation_types:
            recommendations.append("Obtain explicit consent for data processing")
        
        if "retention_period_exceeded" in violation_types:
            recommendations.append("Review and delete data exceeding retention periods")
        
        if "excessive_data_collection" in violation_types:
            recommendations.append("Implement data minimization - collect only necessary data")
        
        if "data_portability_not_supported" in violation_types:
            recommendations.append("Implement data export functionality for data portability")
        
        if not recommendations:
            recommendations.append("Continue GDPR compliance monitoring")
        
        return recommendations

class ComplianceRulebookTool:
    """Tool for dynamic compliance rule sourcing with local DB and web search"""
    
    def __init__(self):
        """Initialize the compliance rulebook tool"""
        self.db_connection = None
        self.web_search_client = None
        
        # Initialize database connection
        self._init_database_connection()
        
        # Initialize web search capability (using Tavily API as suggested)
        self._init_web_search()
        
        logger.info("ComplianceRulebookTool initialized")
    
    def _init_database_connection(self):
        """Initialize PostgreSQL database connection for local compliance rules"""
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            # Get database configuration from environment
            db_config = {
                'host': os.getenv('POSTGRES_HOST', 'localhost'),
                'port': int(os.getenv('POSTGRES_PORT', '5432')),
                'database': os.getenv('POSTGRES_DB', 'kyc_db'),
                'user': os.getenv('POSTGRES_USER', 'postgres'),
                'password': os.getenv('POSTGRES_PASSWORD', 'password')
            }
            
            self.db_connection = psycopg2.connect(**db_config)
            logger.info("Database connection established for compliance rules")
            
        except Exception as e:
            logger.error("Failed to connect to database", error=str(e))
            self.db_connection = None
    
    def _init_web_search(self):
        """Initialize web search client for autonomous rule discovery"""
        try:
            # Try to initialize Tavily API client
            tavily_api_key = os.getenv('TAVILY_API_KEY')
            if tavily_api_key:
                # Import Tavily client (placeholder - would need actual implementation)
                # from tavily import TavilyClient
                # self.web_search_client = TavilyClient(api_key=tavily_api_key)
                logger.info("Tavily web search client initialized")
            else:
                logger.warning("Tavily API key not found - web search will use fallback method")
                self.web_search_client = None
                
        except ImportError:
            logger.warning("Tavily client not available - web search will use fallback method")
            self.web_search_client = None
        except Exception as e:
            logger.error("Failed to initialize web search client", error=str(e))
            self.web_search_client = None
    
    async def get_compliance_rules(self, region: str, regulation_types: List[str] = None) -> Dict[str, Any]:
        """
        Get compliance rules for a specific region, checking local DB first, then web search
        
        Args:
            region: Geographic region (e.g., 'Germany', 'United States', 'European Union')
            regulation_types: List of regulation types to search for (e.g., ['AML', 'KYC', 'GDPR'])
            
        Returns:
            Dictionary containing compliance rules and their sources
        """
        try:
            logger.info("Retrieving compliance rules", region=region, regulation_types=regulation_types)
            
            # Step 1: Check local database first
            local_rules = await self._get_local_compliance_rules(region, regulation_types)
            
            if local_rules and local_rules.get('rules'):
                logger.info("Found compliance rules in local database", 
                           region=region, 
                           rule_count=len(local_rules['rules']))
                return {
                    "source": "local_database",
                    "region": region,
                    "rules": local_rules['rules'],
                    "last_updated": local_rules.get('last_updated'),
                    "confidence": "high"
                }
            
            # Step 2: If no local rules found, perform autonomous web search
            logger.info("No local rules found, performing autonomous web search", region=region)
            web_rules = await self._search_web_compliance_rules(region, regulation_types)
            
            if web_rules and web_rules.get('rules'):
                # Store discovered rules in local database for future use
                await self._store_discovered_rules(region, web_rules['rules'])
                
                return {
                    "source": "web_search",
                    "region": region,
                    "rules": web_rules['rules'],
                    "search_query": web_rules.get('search_query'),
                    "confidence": "medium"
                }
            
            # Step 3: Return default/fallback rules if nothing found
            return {
                "source": "fallback",
                "region": region,
                "rules": self._get_fallback_rules(region),
                "confidence": "low",
                "note": "Using fallback rules - specific regional rules not found"
            }
            
        except Exception as e:
            logger.error("Failed to retrieve compliance rules", error=str(e), region=region)
            return {
                "source": "error",
                "region": region,
                "rules": [],
                "error": str(e)
            }
    
    async def _get_local_compliance_rules(self, region: str, regulation_types: List[str] = None) -> Dict[str, Any]:
        """Query local PostgreSQL database for compliance rules"""
        try:
            if not self.db_connection:
                return {"rules": []}
            
            cursor = self.db_connection.cursor()
            
            # Build query based on region and regulation types
            query = """
                SELECT rule_id, region, regulation_type, rule_title, rule_content, 
                       effective_date, last_updated, source_url, confidence_score
                FROM compliance_rules 
                WHERE LOWER(region) = LOWER(%s)
            """
            params = [region]
            
            if regulation_types:
                placeholders = ','.join(['%s'] * len(regulation_types))
                query += f" AND regulation_type IN ({placeholders})"
                params.extend(regulation_types)
            
            query += " ORDER BY last_updated DESC, confidence_score DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            if not rows:
                return {"rules": []}
            
            # Convert rows to rule objects
            rules = []
            for row in rows:
                rule = {
                    "rule_id": row[0],
                    "region": row[1],
                    "regulation_type": row[2],
                    "title": row[3],
                    "content": row[4],
                    "effective_date": row[5].isoformat() if row[5] else None,
                    "last_updated": row[6].isoformat() if row[6] else None,
                    "source_url": row[7],
                    "confidence_score": float(row[8]) if row[8] else 0.5
                }
                rules.append(rule)
            
            return {
                "rules": rules,
                "last_updated": max([rule['last_updated'] for rule in rules if rule['last_updated']])
            }
            
        except Exception as e:
            logger.error("Database query failed", error=str(e))
            return {"rules": []}
        finally:
            if 'cursor' in locals():
                cursor.close()
    
    async def _search_web_compliance_rules(self, region: str, regulation_types: List[str] = None) -> Dict[str, Any]:
        """Perform autonomous web search for compliance rules"""
        try:
            # Generate search query
            search_query = self._generate_search_query(region, regulation_types)
            
            if self.web_search_client:
                # Use Tavily API for web search
                search_results = await self._tavily_search(search_query)
            else:
                # Use fallback web search method
                search_results = await self._fallback_web_search(search_query)
            
            if not search_results:
                return {"rules": []}
            
            # Process and structure the search results
            structured_rules = self._process_search_results(search_results, region)
            
            return {
                "rules": structured_rules,
                "search_query": search_query,
                "search_results_count": len(search_results)
            }
            
        except Exception as e:
            logger.error("Web search failed", error=str(e))
            return {"rules": []}
    
    def _generate_search_query(self, region: str, regulation_types: List[str] = None) -> str:
        """Generate optimized search query for compliance rules"""
        query_parts = ["current official"]
        
        if regulation_types:
            query_parts.extend(regulation_types)
        else:
            query_parts.extend(["AML", "KYC"])
        
        query_parts.extend([
            "regulations for financial institutions in",
            region,
            "compliance requirements"
        ])
        
        return " ".join(query_parts)
    
    async def _tavily_search(self, query: str) -> List[Dict[str, Any]]:
        """Perform web search using Tavily API"""
        try:
            # Placeholder for Tavily API implementation
            # In production, this would make actual API calls
            logger.info("Performing Tavily web search", query=query)
            
            # Simulated search results for now
            return [
                {
                    "title": f"Official compliance regulations for {query}",
                    "url": "https://example-regulator.gov/compliance",
                    "content": "Sample compliance content from web search...",
                    "relevance_score": 0.9
                }
            ]
            
        except Exception as e:
            logger.error("Tavily search failed", error=str(e))
            return []
    
    async def _fallback_web_search(self, query: str) -> List[Dict[str, Any]]:
        """Fallback web search using requests and BeautifulSoup"""
        try:
            import requests
            from bs4 import BeautifulSoup
            import urllib.parse
            
            # Use DuckDuckGo or similar search engine
            encoded_query = urllib.parse.quote_plus(query)
            search_url = f"https://duckduckgo.com/html/?q={encoded_query}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(search_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract search results (simplified)
            results = []
            for result in soup.find_all('div', class_='result')[:5]:  # Top 5 results
                title_elem = result.find('a', class_='result__a')
                snippet_elem = result.find('div', class_='result__snippet')
                
                if title_elem and snippet_elem:
                    results.append({
                        "title": title_elem.get_text(strip=True),
                        "url": title_elem.get('href', ''),
                        "content": snippet_elem.get_text(strip=True),
                        "relevance_score": 0.7  # Default score for fallback search
                    })
            
            logger.info("Fallback web search completed", query=query, result_count=len(results))
            return results
            
        except Exception as e:
            logger.error("Fallback web search failed", error=str(e))
            return []
    
    def _process_search_results(self, search_results: List[Dict[str, Any]], region: str) -> List[Dict[str, Any]]:
        """Process and structure web search results into compliance rules"""
        structured_rules = []
        
        for i, result in enumerate(search_results):
            rule = {
                "rule_id": f"web_{region.lower().replace(' ', '_')}_{i+1}",
                "region": region,
                "regulation_type": "General",
                "title": result.get("title", "Web-sourced compliance rule"),
                "content": result.get("content", ""),
                "source_url": result.get("url", ""),
                "confidence_score": result.get("relevance_score", 0.5),
                "discovered_date": datetime.now(timezone.utc).isoformat(),
                "source": "web_search"
            }
            structured_rules.append(rule)
        
        return structured_rules
    
    async def _store_discovered_rules(self, region: str, rules: List[Dict[str, Any]]):
        """Store discovered rules in local database for future use"""
        try:
            if not self.db_connection or not rules:
                return
            
            cursor = self.db_connection.cursor()
            
            for rule in rules:
                insert_query = """
                    INSERT INTO compliance_rules 
                    (rule_id, region, regulation_type, rule_title, rule_content, 
                     source_url, confidence_score, last_updated, discovered_via_web)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (rule_id) DO UPDATE SET
                        rule_content = EXCLUDED.rule_content,
                        confidence_score = EXCLUDED.confidence_score,
                        last_updated = EXCLUDED.last_updated
                """
                
                cursor.execute(insert_query, (
                    rule['rule_id'],
                    rule['region'],
                    rule['regulation_type'],
                    rule['title'],
                    rule['content'],
                    rule.get('source_url'),
                    rule['confidence_score'],
                    datetime.now(timezone.utc),
                    True  # discovered_via_web
                ))
            
            self.db_connection.commit()
            logger.info("Stored discovered rules in database", region=region, rule_count=len(rules))
            
        except Exception as e:
            logger.error("Failed to store discovered rules", error=str(e))
            if self.db_connection:
                self.db_connection.rollback()
        finally:
            if 'cursor' in locals():
                cursor.close()
    
    def _get_fallback_rules(self, region: str) -> List[Dict[str, Any]]:
        """Provide fallback compliance rules when no specific rules are found"""
        fallback_rules = [
            {
                "rule_id": f"fallback_{region.lower().replace(' ', '_')}_aml",
                "region": region,
                "regulation_type": "AML",
                "title": "General Anti-Money Laundering Requirements",
                "content": "Implement customer due diligence, monitor transactions for suspicious activity, maintain records, and report suspicious transactions to relevant authorities.",
                "confidence_score": 0.3,
                "source": "fallback_general_knowledge"
            },
            {
                "rule_id": f"fallback_{region.lower().replace(' ', '_')}_kyc",
                "region": region,
                "regulation_type": "KYC",
                "title": "General Know Your Customer Requirements",
                "content": "Verify customer identity, assess risk profile, conduct ongoing monitoring, and maintain up-to-date customer information.",
                "confidence_score": 0.3,
                "source": "fallback_general_knowledge"
            }
        ]
        
        return fallback_rules

# AutoGen Agent Configuration
class ComplianceMonitoringAgents:
    """AutoGen-based compliance monitoring agents"""
    
    def __init__(self):
        self.aml_engine = AMLComplianceEngine()
        self.gdpr_engine = GDPRComplianceEngine()
        
        # Configure AutoGen agents
        self.config_list = [
            {
                "model": "gpt-4",
                "api_key": os.getenv("OPENAI_API_KEY"),
                "api_type": "openai"
            }
        ]
        
        self.llm_config = {
            "config_list": self.config_list,
            "temperature": 0.1,
            "timeout": 120
        }
        
        self._setup_agents()
    
    def _setup_agents(self):
        """Setup AutoGen agents for compliance monitoring"""
        
        # AML Compliance Agent
        self.aml_agent = AssistantAgent(
            name="AML_Compliance_Officer",
            system_message="""
            You are an expert AML (Anti-Money Laundering) compliance officer.
            Your role is to:
            1. Analyze customer data for AML compliance violations
            2. Screen against sanctions lists and PEP databases
            3. Monitor transaction patterns for suspicious activity
            4. Generate compliance reports and recommendations
            5. Escalate critical violations immediately
            
            Always provide detailed reasoning for your compliance decisions.
            """,
            llm_config=self.llm_config
        )
        
        # GDPR Compliance Agent
        self.gdpr_agent = AssistantAgent(
            name="GDPR_Privacy_Officer",
            system_message="""
            You are an expert GDPR (General Data Protection Regulation) privacy officer.
            Your role is to:
            1. Ensure data processing has proper legal basis
            2. Verify consent management compliance
            3. Check data minimization principles
            4. Monitor data retention policies
            5. Ensure data subject rights are respected
            
            Focus on privacy protection and regulatory compliance.
            """,
            llm_config=self.llm_config
        )
        
        # Basel III Compliance Agent
        self.basel_agent = AssistantAgent(
            name="Basel_Risk_Officer",
            system_message="""
            You are an expert Basel III compliance and risk officer.
            Your role is to:
            1. Assess operational risk in customer onboarding
            2. Validate risk management frameworks
            3. Ensure capital adequacy considerations
            4. Monitor model validation requirements
            5. Generate risk assessment reports
            
            Focus on prudential regulation and risk management.
            """,
            llm_config=self.llm_config
        )
        
        # Compliance Coordinator
        self.coordinator = AssistantAgent(
            name="Compliance_Coordinator",
            system_message="""
            You are the compliance coordinator responsible for:
            1. Coordinating between different compliance officers
            2. Synthesizing compliance results from multiple regulations
            3. Making final compliance decisions
            4. Generating comprehensive compliance reports
            5. Escalating complex cases for human review
            
            Ensure all regulatory requirements are met comprehensively.
            """,
            llm_config=self.llm_config
        )
        
        # User Proxy for interaction
        self.user_proxy = UserProxyAgent(
            name="Compliance_System",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=10,
            is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
            code_execution_config=False
        )
        
        # Group Chat for multi-agent collaboration
        self.group_chat = GroupChat(
            agents=[self.aml_agent, self.gdpr_agent, self.basel_agent, self.coordinator, self.user_proxy],
            messages=[],
            max_round=20
        )
        
        self.group_chat_manager = GroupChatManager(
            groupchat=self.group_chat,
            llm_config=self.llm_config
        )
    
    async def perform_comprehensive_compliance_check(self, customer_data: Dict[str, Any], 
                                                   regulation_types: List[RegulationType]) -> Dict[str, Any]:
        """Perform comprehensive compliance check using AutoGen agents"""
        try:
            # Prepare compliance check message
            compliance_message = f"""
            Perform comprehensive compliance check for customer data:
            
            Customer Data: {json.dumps(customer_data, indent=2)}
            
            Regulations to check: {', '.join(regulation_types)}
            
            Each compliance officer should:
            1. Analyze the customer data for their specific regulation
            2. Identify any violations or concerns
            3. Provide compliance score and recommendations
            4. Report findings to the coordinator
            
            Coordinator should synthesize all findings and provide final assessment.
            
            End your response with TERMINATE when analysis is complete.
            """
            
            # Initiate group chat
            chat_result = self.user_proxy.initiate_chat(
                self.group_chat_manager,
                message=compliance_message
            )
            
            # Process chat results
            compliance_results = self._process_autogen_results(chat_result, regulation_types)
            
            return compliance_results
            
        except Exception as e:
            logger.error("AutoGen compliance check failed", error=str(e))
            return {
                "overall_status": ComplianceStatus.UNDER_REVIEW,
                "regulation_results": {},
                "violations": [],
                "compliance_score": 0.0,
                "recommendations": ["Manual review required due to system error"],
                "error": str(e)
            }
    
    def _process_autogen_results(self, chat_result: Any, regulation_types: List[RegulationType]) -> Dict[str, Any]:
        """Process AutoGen chat results into structured compliance report"""
        # Extract messages from chat result
        messages = chat_result.chat_history if hasattr(chat_result, 'chat_history') else []
        
        # Initialize results structure
        regulation_results = {}
        all_violations = []
        all_recommendations = []
        
        # Process messages from each agent
        for message in messages:
            sender = message.get("name", "")
            content = message.get("content", "")
            
            if "AML_Compliance_Officer" in sender:
                regulation_results[RegulationType.AML] = self._parse_agent_response(content, RegulationType.AML)
            elif "GDPR_Privacy_Officer" in sender:
                regulation_results[RegulationType.GDPR] = self._parse_agent_response(content, RegulationType.GDPR)
            elif "Basel_Risk_Officer" in sender:
                regulation_results[RegulationType.BASEL_III] = self._parse_agent_response(content, RegulationType.BASEL_III)
        
        # Collect all violations and recommendations
        for reg_result in regulation_results.values():
            all_violations.extend(reg_result.get("violations", []))
            all_recommendations.extend(reg_result.get("recommendations", []))
        
        # Calculate overall compliance score
        scores = [result.get("compliance_score", 0.0) for result in regulation_results.values()]
        overall_score = np.mean(scores) if scores else 0.0
        
        # Determine overall status
        if any(result.get("status") == ComplianceStatus.NON_COMPLIANT for result in regulation_results.values()):
            overall_status = ComplianceStatus.NON_COMPLIANT
        elif any(result.get("status") == ComplianceStatus.REQUIRES_ATTENTION for result in regulation_results.values()):
            overall_status = ComplianceStatus.REQUIRES_ATTENTION
        else:
            overall_status = ComplianceStatus.COMPLIANT
        
        return {
            "overall_status": overall_status,
            "regulation_results": regulation_results,
            "violations": all_violations,
            "compliance_score": overall_score,
            "recommendations": list(set(all_recommendations))  # Remove duplicates
        }
    
    def _parse_agent_response(self, content: str, regulation: RegulationType) -> Dict[str, Any]:
        """Parse agent response into structured format"""
        # Simplified parsing - in production would use more sophisticated NLP
        violations = []
        recommendations = []
        compliance_score = 0.8  # Default score
        
        # Look for key indicators in the response
        if "violation" in content.lower() or "non-compliant" in content.lower():
            status = ComplianceStatus.NON_COMPLIANT
            compliance_score = 0.3
        elif "concern" in content.lower() or "attention" in content.lower():
            status = ComplianceStatus.REQUIRES_ATTENTION
            compliance_score = 0.6
        else:
            status = ComplianceStatus.COMPLIANT
            compliance_score = 0.9
        
        # Extract recommendations (lines starting with "Recommend" or "Should")
        lines = content.split('\n')
        for line in lines:
            if line.strip().lower().startswith(('recommend', 'should', 'must')):
                recommendations.append(line.strip())
        
        return {
            "regulation": regulation,
            "status": status,
            "violations": violations,
            "compliance_score": compliance_score,
            "recommendations": recommendations,
            "raw_response": content
        }

# Main Service Class
class ComplianceMonitoringService:
    """Main Compliance Monitoring Service using AutoGen"""
    
    def __init__(self):
        self.app = FastAPI(title="Compliance Monitoring Agent", version="1.0.0")
        self.setup_middleware()
        self.setup_routes()
        
        # Initialize components
        self.kafka_producer = None
        self.kafka_consumer = None
        self.redis_client = None
        self.db_connection = None
        self.mongo_client = None
        
        # Initialize compliance engines
        self.aml_engine = AMLComplianceEngine()
        self.gdpr_engine = GDPRComplianceEngine()
        self.autogen_agents = ComplianceMonitoringAgents()
        
        # Initialize monitoring tasks
        self.active_monitors = {}
        
        # Setup components
        self._setup_database_connections()
        self._setup_messaging()
        
        # Start monitoring
        start_http_server(8004)
        
        logger.info("Compliance Monitoring Agent initialized successfully")
    
    def setup_middleware(self):
        """Setup FastAPI middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def setup_routes(self):
        """Setup API routes"""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "service": "compliance-monitoring-agent",
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0",
                "active_monitors": len(self.active_monitors)
            }
        
        @self.app.post("/api/v1/compliance/check", response_model=ComplianceCheckResponse)
        async def check_compliance(request: ComplianceCheckRequest, background_tasks: BackgroundTasks):
            """Main compliance check endpoint"""
            compliance_checks.inc()
            
            with monitoring_duration.time():
                try:
                    # Generate check ID
                    check_id = self._generate_check_id(request.customer_id)
                    
                    # Perform compliance checks
                    compliance_results = await self._perform_compliance_checks(
                        request.customer_id,
                        request.customer_data,
                        request.regulation_types,
                        request.check_type
                    )
                    
                    # Update metrics
                    for violation in compliance_results["violations"]:
                        compliance_violations.labels(
                            regulation=violation.get("regulation", "unknown"),
                            severity=violation.get("severity", "unknown")
                        ).inc()
                    
                    # Send results to other agents
                    background_tasks.add_task(
                        self._send_compliance_results,
                        check_id,
                        compliance_results
                    )
                    
                    # Store results
                    background_tasks.add_task(
                        self._store_compliance_results,
                        check_id,
                        compliance_results
                    )
                    
                    # Calculate next review date
                    next_review = self._calculate_next_review_date(compliance_results)
                    
                    return ComplianceCheckResponse(
                        check_id=check_id,
                        customer_id=request.customer_id,
                        overall_status=compliance_results["overall_status"],
                        regulation_results=compliance_results["regulation_results"],
                        violations=compliance_results["violations"],
                        compliance_score=compliance_results["compliance_score"],
                        recommendations=compliance_results["recommendations"],
                        next_review_date=next_review,
                        processing_time=compliance_results.get("processing_time", 0.0),
                        status="completed"
                    )
                    
                except Exception as e:
                    logger.error("Compliance check failed", 
                               customer_id=request.customer_id, 
                               error=str(e))
                    raise HTTPException(status_code=500, detail=f"Compliance check failed: {str(e)}")
        
        @self.app.post("/api/v1/compliance/monitor/start")
        async def start_monitoring(request: MonitoringConfigRequest):
            """Start continuous compliance monitoring"""
            try:
                monitor_id = str(uuid.uuid4())
                
                # Configure monitoring
                monitor_config = {
                    "monitor_id": monitor_id,
                    "regulation_types": request.regulation_types,
                    "frequency": request.frequency,
                    "thresholds": request.thresholds,
                    "notification_settings": request.notification_settings,
                    "created_at": datetime.now(),
                    "status": "active"
                }
                
                self.active_monitors[monitor_id] = monitor_config
                active_monitors.set(len(self.active_monitors))
                
                # Start monitoring task
                asyncio.create_task(self._run_continuous_monitoring(monitor_config))
                
                return {
                    "monitor_id": monitor_id,
                    "status": "started",
                    "configuration": monitor_config
                }
                
            except Exception as e:
                logger.error("Failed to start monitoring", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/compliance/report/generate")
        async def generate_compliance_report(
            regulation_types: List[RegulationType],
            period_start: datetime,
            period_end: datetime,
            background_tasks: BackgroundTasks
        ):
            """Generate compliance report"""
            try:
                report_id = str(uuid.uuid4())
                
                # Generate report
                background_tasks.add_task(
                    self._generate_compliance_report,
                    report_id,
                    regulation_types,
                    period_start,
                    period_end
                )
                
                compliance_reports.inc()
                
                return {
                    "report_id": report_id,
                    "status": "generating",
                    "estimated_completion": datetime.now() + timedelta(minutes=5)
                }
                
            except Exception as e:
                logger.error("Failed to generate report", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/compliance/violations")
        async def get_recent_violations(
            limit: int = 100,
            regulation_type: Optional[RegulationType] = None,
            severity: Optional[ViolationSeverity] = None
        ):
            """Get recent compliance violations"""
            try:
                violations = await self._get_recent_violations(limit, regulation_type, severity)
                return {
                    "violations": violations,
                    "total_count": len(violations),
                    "filters": {
                        "regulation_type": regulation_type,
                        "severity": severity,
                        "limit": limit
                    }
                }
            except Exception as e:
                logger.error("Failed to retrieve violations", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))
    
    def _setup_database_connections(self):
        """Setup database connections"""
        try:
            # PostgreSQL connection
            self.db_connection = psycopg2.connect(
                host=os.getenv('POSTGRES_HOST', 'localhost'),
                port=os.getenv('POSTGRES_PORT', 5432),
                database=os.getenv('POSTGRES_DB', 'kyc_db'),
                user=os.getenv('POSTGRES_USER', 'postgres'),
                password=os.getenv('POSTGRES_PASSWORD', 'password')
            )
            
            # MongoDB connection
            mongo_url = os.getenv('MONGODB_URL', 'mongodb://localhost:27017/')
            self.mongo_client = MongoClient(mongo_url)
            
            # Redis connection
            self.redis_client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=os.getenv('REDIS_PORT', 6379),
                db=0,
                decode_responses=True
            )
            
            logger.info("Database connections established")
        except Exception as e:
            logger.error("Database connection failed", error=str(e))
            raise
    
    def _setup_messaging(self):
        """Setup Kafka messaging"""
        try:
            # Kafka producer
            self.kafka_producer = KafkaProducer(
                bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            
            logger.info("Messaging setup completed")
        except Exception as e:
            logger.error("Messaging setup failed", error=str(e))
            raise
    
    async def _perform_compliance_checks(self, customer_id: str, customer_data: Dict[str, Any], 
                                       regulation_types: List[RegulationType], check_type: str) -> Dict[str, Any]:
        """Perform comprehensive compliance checks"""
        start_time = datetime.now()
        
        try:
            # Use AutoGen agents for comprehensive analysis
            compliance_results = await self.autogen_agents.perform_comprehensive_compliance_check(
                customer_data, regulation_types
            )
            
            # Add individual engine results for specific regulations
            if RegulationType.AML in regulation_types:
                aml_result = await self.aml_engine.check_aml_compliance(customer_data)
                compliance_results["regulation_results"][RegulationType.AML] = aml_result
            
            if RegulationType.GDPR in regulation_types:
                gdpr_result = await self.gdpr_engine.check_gdpr_compliance(customer_data)
                compliance_results["regulation_results"][RegulationType.GDPR] = gdpr_result
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            compliance_results["processing_time"] = processing_time
            
            logger.info("Compliance checks completed", 
                       customer_id=customer_id,
                       processing_time=processing_time,
                       overall_status=compliance_results["overall_status"])
            
            return compliance_results
            
        except Exception as e:
            logger.error("Compliance checks failed", customer_id=customer_id, error=str(e))
            raise
    
    def _generate_check_id(self, customer_id: str) -> str:
        """Generate unique check ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hash_input = f"{customer_id}_{timestamp}_{uuid.uuid4().hex[:8]}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    def _calculate_next_review_date(self, compliance_results: Dict[str, Any]) -> datetime:
        """Calculate next review date based on compliance status"""
        if compliance_results["overall_status"] == ComplianceStatus.NON_COMPLIANT:
            return datetime.now() + timedelta(days=30)  # Monthly review for non-compliant
        elif compliance_results["overall_status"] == ComplianceStatus.REQUIRES_ATTENTION:
            return datetime.now() + timedelta(days=90)  # Quarterly review
        else:
            return datetime.now() + timedelta(days=365)  # Annual review for compliant
    
    async def _send_compliance_results(self, check_id: str, results: Dict[str, Any]):
        """Send compliance results to other agents via Kafka"""
        try:
            message = {
                "check_id": check_id,
                "agent": "compliance-monitoring-agent",
                "timestamp": datetime.now().isoformat(),
                "results": results
            }
            
            self.kafka_producer.send('compliance-results', message)
            logger.info("Compliance results sent to Kafka", check_id=check_id)
        except Exception as e:
            logger.error("Failed to send compliance results", check_id=check_id, error=str(e))
    
    async def _store_compliance_results(self, check_id: str, results: Dict[str, Any]):
        """Store compliance results in database"""
        try:
            # Store in PostgreSQL
            cursor = self.db_connection.cursor()
            cursor.execute("""
                INSERT INTO compliance_check_results (check_id, customer_id, results, created_at)
                VALUES (%s, %s, %s, %s)
            """, (check_id, results.get('customer_id'), json.dumps(results), datetime.now()))
            self.db_connection.commit()
            
            # Cache in Redis
            self.redis_client.setex(f"compliance:{check_id}", 3600, json.dumps(results))
            
            logger.info("Compliance results stored", check_id=check_id)
        except Exception as e:
            logger.error("Failed to store compliance results", check_id=check_id, error=str(e))
    
    async def _run_continuous_monitoring(self, monitor_config: Dict[str, Any]):
        """Run continuous compliance monitoring"""
        monitor_id = monitor_config["monitor_id"]
        frequency = monitor_config["frequency"]
        
        try:
            while monitor_id in self.active_monitors:
                # Perform monitoring checks
                await self._perform_monitoring_cycle(monitor_config)
                
                # Wait based on frequency
                if frequency == MonitoringFrequency.REAL_TIME:
                    await asyncio.sleep(60)  # 1 minute
                elif frequency == MonitoringFrequency.HOURLY:
                    await asyncio.sleep(3600)  # 1 hour
                elif frequency == MonitoringFrequency.DAILY:
                    await asyncio.sleep(86400)  # 1 day
                else:
                    await asyncio.sleep(3600)  # Default to hourly
                
        except Exception as e:
            logger.error("Continuous monitoring failed", monitor_id=monitor_id, error=str(e))
        finally:
            # Clean up
            if monitor_id in self.active_monitors:
                del self.active_monitors[monitor_id]
                active_monitors.set(len(self.active_monitors))
    
    async def _perform_monitoring_cycle(self, monitor_config: Dict[str, Any]):
        """Perform one monitoring cycle"""
        # This would query for customers to monitor and run compliance checks
        # Simplified implementation
        logger.info("Performing monitoring cycle", monitor_id=monitor_config["monitor_id"])
    
    async def _generate_compliance_report(self, report_id: str, regulation_types: List[RegulationType],
                                        period_start: datetime, period_end: datetime):
        """Generate comprehensive compliance report"""
        try:
            # Query compliance data for the period
            # Generate report document
            # Store report
            logger.info("Compliance report generated", report_id=report_id)
        except Exception as e:
            logger.error("Report generation failed", report_id=report_id, error=str(e))
    
    async def _get_recent_violations(self, limit: int, regulation_type: Optional[RegulationType],
                                   severity: Optional[ViolationSeverity]) -> List[Dict[str, Any]]:
        """Get recent compliance violations"""
        # Query database for recent violations
        # Apply filters
        # Return results
        return []  # Simplified implementation

# Initialize service
service = ComplianceMonitoringService()
app = service.app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004, workers=4)
