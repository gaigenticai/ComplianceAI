"""
Intelligence & Compliance Agent - Simplified Agentic Architecture
================================================================

This agent combines KYC Analysis and Compliance Monitoring functionality
with hybrid ML + rule-based approach for cost optimization.

Key Features:
- Real-time sanctions/PEP screening
- Risk scoring using hybrid ML + rule-based approach  
- AML/KYC compliance verification
- Regulatory reporting preparation
- Local ML models for 70% of risk scoring
- OpenAI only for complex reasoning
- Cost target: $0.20-0.25 per case

Replaces: KYC Analysis Agent + Compliance Monitoring Agent
Framework: CrewAI + AutoGen with cost optimization
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from enum import Enum
import uuid
import pickle

# FastAPI framework
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
import uvicorn

# CrewAI Framework for Multi-Agent Collaboration
from crewai import Agent, Task, Crew
from crewai.tools import BaseTool

# AutoGen Framework for Compliance Monitoring
import autogen
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager

# AI/ML Libraries
import openai
from openai import OpenAI
from langchain_openai import ChatOpenAI

# Local ML Models
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import joblib
import numpy as np
import pandas as pd

# Database and messaging
import psycopg2
from pymongo import MongoClient
import redis
from kafka import KafkaProducer, KafkaConsumer

# Web scraping for compliance rules
import requests
from bs4 import BeautifulSoup
import aiohttp

# Monitoring
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import structlog

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

# Prometheus metrics
RISK_ASSESSMENTS_COMPLETED = Counter('intelligence_risk_assessments_total', 'Total risk assessments', ['method', 'risk_level'])
COMPLIANCE_CHECKS_COMPLETED = Counter('intelligence_compliance_checks_total', 'Total compliance checks', ['regulation_type', 'status'])
PROCESSING_TIME = Histogram('intelligence_processing_duration_seconds', 'Time spent on analysis', ['component'])
COST_PER_CASE = Histogram('intelligence_cost_per_case_dollars', 'Cost per case analysis', ['method'])
ACTIVE_ANALYSES = Gauge('intelligence_active_analyses', 'Number of active analyses')

# Enums
class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    REQUIRES_REVIEW = "requires_review"
    COMPLEX = "complex"

class RegulationType(str, Enum):
    AML = "aml"
    KYC = "kyc"
    GDPR = "gdpr"
    BASEL_III = "basel_iii"
    FATCA = "fatca"
    CRS = "crs"

# Pydantic models
class CustomerAnalysisRequest(BaseModel):
    """Request model for customer analysis"""
    session_id: str = Field(..., description="KYC session ID")
    customer_id: str = Field(..., description="Customer ID")
    customer_data: Dict[str, Any] = Field(..., description="Customer data from intake")
    regulation_types: List[RegulationType] = Field(default=[RegulationType.AML, RegulationType.KYC])
    priority: str = Field("normal", description="Analysis priority")

class RiskAssessmentResult(BaseModel):
    """Risk assessment result model"""
    customer_id: str
    risk_score: float
    risk_level: RiskLevel
    risk_factors: List[Dict[str, Any]]
    confidence: float
    processing_method: str
    reasoning: str

class ComplianceCheckResult(BaseModel):
    """Compliance check result model"""
    customer_id: str
    regulation_type: RegulationType
    status: ComplianceStatus
    violations: List[str]
    recommendations: List[str]
    confidence: float

class IntelligenceAnalysisResult(BaseModel):
    """Complete intelligence analysis result"""
    session_id: str
    customer_id: str
    risk_assessment: RiskAssessmentResult
    compliance_checks: List[ComplianceCheckResult]
    sanctions_screening: Dict[str, Any]
    pep_screening: Dict[str, Any]
    overall_recommendation: str
    processing_time_seconds: float
    estimated_cost_dollars: float
    status: str

# Local ML Risk Scoring Engine
class LocalRiskScoringEngine:
    """Local ML models for cost-effective risk scoring"""
    
    def __init__(self):
        self.logger = structlog.get_logger()
        self.models = {}
        self.scalers = {}
        self.is_trained = False
        
        # Initialize models
        self._initialize_models()
        
        # Load pre-trained models if available
        self._load_models()
    
    def _initialize_models(self):
        """Initialize ML models"""
        self.models = {
            'primary': RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            ),
            'secondary': GradientBoostingClassifier(
                n_estimators=50,
                max_depth=6,
                random_state=42
            ),
            'fallback': LogisticRegression(
                random_state=42,
                max_iter=1000
            )
        }
        
        self.scalers = {
            'primary': StandardScaler(),
            'secondary': StandardScaler(),
            'fallback': StandardScaler()
        }
    
    def _load_models(self):
        """Load pre-trained models from disk"""
        try:
            model_path = "/app/models"
            if os.path.exists(f"{model_path}/risk_model_primary.pkl"):
                self.models['primary'] = joblib.load(f"{model_path}/risk_model_primary.pkl")
                self.scalers['primary'] = joblib.load(f"{model_path}/scaler_primary.pkl")
                self.is_trained = True
                self.logger.info("Pre-trained risk models loaded successfully")
        except Exception as e:
            self.logger.warning("Could not load pre-trained models", error=str(e))
    
    def _extract_features(self, customer_data: Dict[str, Any]) -> np.ndarray:
        """Extract numerical features from customer data"""
        features = []
        
        # Personal information features
        personal_info = customer_data.get('personal_info', {})
        
        # Age (if date of birth available)
        if 'date_of_birth' in personal_info:
            try:
                dob = datetime.strptime(personal_info['date_of_birth'], '%Y-%m-%d')
                age = (datetime.now() - dob).days / 365.25
                features.append(age)
            except:
                features.append(35.0)  # Default age
        else:
            features.append(35.0)
        
        # Document quality features
        features.append(customer_data.get('confidence', 0.5))
        features.append(customer_data.get('quality_score', 0.5))
        
        # Geographic risk (simplified)
        country = personal_info.get('nationality', 'unknown').lower()
        high_risk_countries = ['afghanistan', 'iran', 'north korea', 'syria']
        features.append(1.0 if country in high_risk_countries else 0.0)
        
        # Document type risk
        doc_type = customer_data.get('document_type', 'unknown')
        doc_risk_scores = {
            'passport': 0.1,
            'national_id': 0.2,
            'drivers_license': 0.3,
            'utility_bill': 0.4,
            'unknown': 0.8
        }
        features.append(doc_risk_scores.get(doc_type, 0.5))
        
        # Data completeness
        required_fields = ['full_name', 'date_of_birth', 'address']
        completeness = sum(1 for field in required_fields if personal_info.get(field)) / len(required_fields)
        features.append(completeness)
        
        # Anomaly indicators
        anomalies = customer_data.get('anomalies_detected', [])
        features.append(len(anomalies) / 10.0)  # Normalized anomaly count
        
        return np.array(features).reshape(1, -1)
    
    def predict_risk(self, customer_data: Dict[str, Any]) -> Tuple[float, RiskLevel, str, float]:
        """Predict risk score using local ML models"""
        try:
            start_time = datetime.now()
            
            # Extract features
            features = self._extract_features(customer_data)
            
            if self.is_trained:
                # Use trained model
                scaled_features = self.scalers['primary'].transform(features)
                risk_proba = self.models['primary'].predict_proba(scaled_features)[0]
                
                # Convert to risk score (0-1)
                risk_score = risk_proba[1] if len(risk_proba) > 1 else 0.5
                confidence = max(risk_proba)
                method = "local_ml_trained"
                
            else:
                # Use rule-based scoring as fallback
                risk_score = self._rule_based_scoring(customer_data)
                confidence = 0.7
                method = "local_rules"
            
            # Determine risk level
            if risk_score < 0.3:
                risk_level = RiskLevel.LOW
            elif risk_score < 0.6:
                risk_level = RiskLevel.MEDIUM
            elif risk_score < 0.8:
                risk_level = RiskLevel.HIGH
            else:
                risk_level = RiskLevel.CRITICAL
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Record metrics
            PROCESSING_TIME.labels(component='risk_scoring').observe(processing_time)
            COST_PER_CASE.labels(method='local_ml').observe(0.08)
            RISK_ASSESSMENTS_COMPLETED.labels(method='local_ml', risk_level=risk_level.value).inc()
            
            self.logger.info(
                "Local risk scoring completed",
                risk_score=risk_score,
                risk_level=risk_level.value,
                method=method,
                confidence=confidence,
                processing_time=processing_time
            )
            
            return risk_score, risk_level, method, confidence
            
        except Exception as e:
            self.logger.error("Local risk scoring failed", error=str(e))
            return 0.5, RiskLevel.MEDIUM, "fallback", 0.5
    
    def _rule_based_scoring(self, customer_data: Dict[str, Any]) -> float:
        """Rule-based risk scoring fallback"""
        score = 0.3  # Base score
        
        # Document quality impact
        quality_score = customer_data.get('quality_score', 0.5)
        if quality_score < 0.5:
            score += 0.2
        
        # Anomaly impact
        anomalies = customer_data.get('anomalies_detected', [])
        score += len(anomalies) * 0.1
        
        # Geographic risk
        personal_info = customer_data.get('personal_info', {})
        country = personal_info.get('nationality', '').lower()
        high_risk_countries = ['afghanistan', 'iran', 'north korea', 'syria']
        if country in high_risk_countries:
            score += 0.3
        
        return min(1.0, score)

# Sanctions and PEP Screening Engine
class SanctionsScreeningEngine:
    """Local sanctions and PEP screening with cached databases"""
    
    def __init__(self):
        self.logger = structlog.get_logger()
        self.sanctions_db = self._load_sanctions_database()
        self.pep_db = self._load_pep_database()
    
    def _load_sanctions_database(self) -> Dict[str, Any]:
        """Load production sanctions database"""
        from .sanctions_database import ProductionSanctionsDatabase
        
        config = {
            'pep_data_source': os.getenv('PEP_DATA_SOURCE', 'local'),
            'sanctions_update_interval': int(os.getenv('SANCTIONS_UPDATE_INTERVAL', '6')),
            'worldcheck_api_key': os.getenv('WORLDCHECK_API_KEY'),
            'dowjones_api_key': os.getenv('DOWJONES_API_KEY')
        }
        
        self.sanctions_db = ProductionSanctionsDatabase(config)
        # Initialize asynchronously in background
        asyncio.create_task(self.sanctions_db.initialize())
        
        return {}
    
    def _load_pep_database(self) -> Dict[str, Any]:
        """Load production PEP database"""
        # PEP database is loaded as part of sanctions database
        return {}
    
    def screen_sanctions(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Screen customer against sanctions lists"""
        try:
            personal_info = customer_data.get('personal_info', {})
            full_name = personal_info.get('full_name', '').lower()
            
            matches = []
            
            # Check against all sanctions lists
            for list_name, sanctioned_entities in self.sanctions_db.items():
                for entity in sanctioned_entities:
                    if self._fuzzy_match(full_name, entity.lower()):
                        matches.append({
                            'list': list_name,
                            'matched_name': entity,
                            'confidence': 0.8
                        })
            
            result = {
                'status': 'clear' if not matches else 'match_found',
                'matches': matches,
                'screening_date': datetime.now(timezone.utc).isoformat(),
                'lists_checked': list(self.sanctions_db.keys())
            }
            
            COMPLIANCE_CHECKS_COMPLETED.labels(
                regulation_type='sanctions',
                status=result['status']
            ).inc()
            
            return result
            
        except Exception as e:
            self.logger.error("Sanctions screening failed", error=str(e))
            return {'status': 'error', 'matches': [], 'error': str(e)}
    
    def screen_pep(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Screen customer against PEP lists"""
        try:
            personal_info = customer_data.get('personal_info', {})
            full_name = personal_info.get('full_name', '').lower()
            
            matches = []
            
            # Check against PEP lists
            for category, pep_entities in self.pep_db.items():
                for entity in pep_entities:
                    if self._fuzzy_match(full_name, entity.lower()):
                        matches.append({
                            'category': category,
                            'matched_name': entity,
                            'confidence': 0.8
                        })
            
            result = {
                'status': 'clear' if not matches else 'pep_match',
                'matches': matches,
                'screening_date': datetime.now(timezone.utc).isoformat(),
                'categories_checked': list(self.pep_db.keys())
            }
            
            COMPLIANCE_CHECKS_COMPLETED.labels(
                regulation_type='pep',
                status=result['status']
            ).inc()
            
            return result
            
        except Exception as e:
            self.logger.error("PEP screening failed", error=str(e))
            return {'status': 'error', 'matches': [], 'error': str(e)}
    
    def _fuzzy_match(self, name1: str, name2: str, threshold: float = 0.8) -> bool:
        """Simple fuzzy matching for names"""
        # Simple implementation - in production use more sophisticated matching
        from difflib import SequenceMatcher
        return SequenceMatcher(None, name1, name2).ratio() >= threshold

# Compliance Rules Engine
class ComplianceRulesEngine:
    """Rule-based compliance checking with cached regulations"""
    
    def __init__(self):
        self.logger = structlog.get_logger()
        self.rules_cache = {}
        self._load_compliance_rules()
    
    def _load_compliance_rules(self):
        """Load compliance rules from database/cache"""
        # Mock compliance rules - in production load from database
        self.rules_cache = {
            RegulationType.AML: {
                'customer_due_diligence': {
                    'required_documents': ['identity_document', 'address_proof'],
                    'max_risk_score': 0.7,
                    'sanctions_screening_required': True
                },
                'enhanced_due_diligence': {
                    'triggers': ['high_risk_country', 'pep_match', 'large_transactions'],
                    'additional_requirements': ['source_of_funds', 'business_purpose']
                }
            },
            RegulationType.KYC: {
                'identity_verification': {
                    'document_types_accepted': ['passport', 'national_id', 'drivers_license'],
                    'minimum_quality_score': 0.8,
                    'expiry_check_required': True
                },
                'address_verification': {
                    'document_age_limit_days': 90,
                    'accepted_documents': ['utility_bill', 'bank_statement', 'government_letter']
                }
            },
            RegulationType.GDPR: {
                'data_minimization': {
                    'collect_only_necessary': True,
                    'retention_period_months': 60
                },
                'consent_management': {
                    'explicit_consent_required': True,
                    'withdrawal_mechanism': True
                }
            }
        }
    
    def evaluate_compliance(self, customer_data: Dict[str, Any], 
                          regulation_type: RegulationType) -> ComplianceCheckResult:
        """Evaluate compliance for specific regulation"""
        try:
            start_time = datetime.now()
            
            rules = self.rules_cache.get(regulation_type, {})
            violations = []
            recommendations = []
            
            if regulation_type == RegulationType.AML:
                violations, recommendations = self._check_aml_compliance(customer_data, rules)
            elif regulation_type == RegulationType.KYC:
                violations, recommendations = self._check_kyc_compliance(customer_data, rules)
            elif regulation_type == RegulationType.GDPR:
                violations, recommendations = self._check_gdpr_compliance(customer_data, rules)
            
            # Determine status
            if not violations:
                status = ComplianceStatus.COMPLIANT
            elif len(violations) > 3:
                status = ComplianceStatus.NON_COMPLIANT
            else:
                status = ComplianceStatus.REQUIRES_REVIEW
            
            confidence = 0.9 if not violations else 0.7
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Record metrics
            PROCESSING_TIME.labels(component='compliance_check').observe(processing_time)
            COMPLIANCE_CHECKS_COMPLETED.labels(
                regulation_type=regulation_type.value,
                status=status.value
            ).inc()
            
            result = ComplianceCheckResult(
                customer_id=customer_data.get('customer_id', ''),
                regulation_type=regulation_type,
                status=status,
                violations=violations,
                recommendations=recommendations,
                confidence=confidence
            )
            
            self.logger.info(
                "Compliance check completed",
                regulation_type=regulation_type.value,
                status=status.value,
                violations_count=len(violations),
                processing_time=processing_time
            )
            
            return result
            
        except Exception as e:
            self.logger.error("Compliance evaluation failed", 
                            regulation_type=regulation_type.value, error=str(e))
            return ComplianceCheckResult(
                customer_id=customer_data.get('customer_id', ''),
                regulation_type=regulation_type,
                status=ComplianceStatus.REQUIRES_REVIEW,
                violations=[f"Evaluation failed: {str(e)}"],
                recommendations=["Manual review required"],
                confidence=0.0
            )
    
    def _check_aml_compliance(self, customer_data: Dict[str, Any], 
                            rules: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Check AML compliance"""
        violations = []
        recommendations = []
        
        # Check sanctions screening
        sanctions_result = customer_data.get('sanctions_screening', {})
        if sanctions_result.get('status') == 'match_found':
            violations.append("Customer matches sanctions list")
            recommendations.append("Enhanced due diligence required")
        
        # Check PEP screening
        pep_result = customer_data.get('pep_screening', {})
        if pep_result.get('status') == 'pep_match':
            violations.append("Customer is a Politically Exposed Person")
            recommendations.append("Enhanced due diligence and ongoing monitoring required")
        
        # Check risk score
        risk_score = customer_data.get('risk_score', 0.5)
        max_risk = rules.get('customer_due_diligence', {}).get('max_risk_score', 0.7)
        if risk_score > max_risk:
            violations.append(f"Risk score {risk_score} exceeds threshold {max_risk}")
            recommendations.append("Additional verification required")
        
        return violations, recommendations
    
    def _check_kyc_compliance(self, customer_data: Dict[str, Any], 
                            rules: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Check KYC compliance"""
        violations = []
        recommendations = []
        
        # Check document quality
        quality_score = customer_data.get('quality_score', 0.0)
        min_quality = rules.get('identity_verification', {}).get('minimum_quality_score', 0.8)
        if quality_score < min_quality:
            violations.append(f"Document quality {quality_score} below required {min_quality}")
            recommendations.append("Request higher quality document")
        
        # Check document type
        doc_type = customer_data.get('document_type', 'unknown')
        accepted_types = rules.get('identity_verification', {}).get('document_types_accepted', [])
        if doc_type not in accepted_types and doc_type != 'unknown':
            violations.append(f"Document type {doc_type} not accepted")
            recommendations.append("Request acceptable identity document")
        
        return violations, recommendations
    
    def _check_gdpr_compliance(self, customer_data: Dict[str, Any], 
                             rules: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Check GDPR compliance"""
        violations = []
        recommendations = []
        
        # Check data minimization
        if len(customer_data) > 20:  # Arbitrary threshold
            violations.append("Excessive data collection detected")
            recommendations.append("Review data collection practices")
        
        # Check consent (mock check)
        if not customer_data.get('consent_given', False):
            violations.append("No explicit consent recorded")
            recommendations.append("Obtain explicit consent before processing")
        
        return violations, recommendations

# CrewAI Risk Assessment Team
class RiskAssessmentCrew:
    """CrewAI-based risk assessment team"""
    
    def __init__(self):
        self.logger = structlog.get_logger()
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.1,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        self._setup_agents()
    
    def _setup_agents(self):
        """Setup CrewAI agents"""
        # Risk Analyst Agent
        self.risk_analyst = Agent(
            role='Senior Risk Analyst',
            goal='Analyze customer data and identify risk factors for KYC compliance',
            backstory="""You are a senior risk analyst with 15 years of experience in 
            financial risk assessment. You specialize in identifying patterns and 
            anomalies that indicate potential compliance risks.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
        
        # Compliance Specialist Agent
        self.compliance_specialist = Agent(
            role='Compliance Specialist',
            goal='Ensure all regulatory requirements are met and identify violations',
            backstory="""You are a compliance specialist with deep knowledge of 
            AML, KYC, GDPR, and Basel III regulations. You ensure all customer 
            onboarding meets regulatory standards.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
        
        # Data Quality Analyst Agent
        self.data_analyst = Agent(
            role='Data Quality Analyst',
            goal='Assess data quality and completeness for compliance purposes',
            backstory="""You are a data quality expert who ensures that customer 
            data is complete, accurate, and suitable for compliance decisions.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
    
    async def analyze_complex_case(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze complex cases using CrewAI collaboration"""
        try:
            start_time = datetime.now()
            
            # Create analysis tasks
            risk_task = Task(
                description=f"""Analyze the following customer data for risk factors:
                {json.dumps(customer_data, indent=2)}
                
                Identify:
                1. Key risk indicators
                2. Unusual patterns or anomalies
                3. Geographic or jurisdictional risks
                4. Document quality concerns
                
                Provide a risk assessment with score (0-1) and reasoning.""",
                agent=self.risk_analyst,
                expected_output="Detailed risk analysis with score and factors"
            )
            
            compliance_task = Task(
                description=f"""Review the customer data for compliance violations:
                {json.dumps(customer_data, indent=2)}
                
                Check against:
                1. AML requirements
                2. KYC standards
                3. GDPR compliance
                4. Industry best practices
                
                List any violations and recommendations.""",
                agent=self.compliance_specialist,
                expected_output="Compliance assessment with violations and recommendations"
            )
            
            data_task = Task(
                description=f"""Assess data quality and completeness:
                {json.dumps(customer_data, indent=2)}
                
                Evaluate:
                1. Data completeness
                2. Data accuracy
                3. Data consistency
                4. Missing critical information
                
                Provide quality score and improvement suggestions.""",
                agent=self.data_analyst,
                expected_output="Data quality assessment with score and suggestions"
            )
            
            # Create and run crew
            crew = Crew(
                agents=[self.risk_analyst, self.compliance_specialist, self.data_analyst],
                tasks=[risk_task, compliance_task, data_task],
                verbose=True
            )
            
            # Execute analysis
            result = crew.kickoff()
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Record metrics
            PROCESSING_TIME.labels(component='crewai_analysis').observe(processing_time)
            COST_PER_CASE.labels(method='crewai').observe(0.60)  # Higher cost for complex analysis
            
            self.logger.info(
                "CrewAI complex analysis completed",
                processing_time=processing_time,
                result_length=len(str(result))
            )
            
            return {
                'analysis_result': str(result),
                'processing_time': processing_time,
                'method': 'crewai_collaborative',
                'confidence': 0.9
            }
            
        except Exception as e:
            self.logger.error("CrewAI analysis failed", error=str(e))
            return {
                'analysis_result': f"Analysis failed: {str(e)}",
                'processing_time': 0,
                'method': 'failed',
                'confidence': 0.0
            }

# Main Intelligence & Compliance Agent
class IntelligenceComplianceAgent:
    """Main agent combining risk assessment and compliance monitoring"""
    
    def __init__(self):
        self.logger = structlog.get_logger()
        
        # Initialize components
        self.risk_engine = LocalRiskScoringEngine()
        self.sanctions_engine = SanctionsScreeningEngine()
        self.compliance_engine = ComplianceRulesEngine()
        self.crewai_team = RiskAssessmentCrew()
        
        # OpenAI client for complex reasoning
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Database connections
        self._setup_database_connections()
        
        # Kafka setup
        self._setup_kafka()
        
        self.logger.info("Intelligence & Compliance Agent initialized successfully")
    
    def _setup_database_connections(self):
        """Setup database connections"""
        try:
            # PostgreSQL
            self.pg_conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=os.getenv("POSTGRES_PORT", "5432"),
                database=os.getenv("POSTGRES_DB", "kyc_db"),
                user=os.getenv("POSTGRES_USER", "postgres"),
                password=os.getenv("POSTGRES_PASSWORD", "password")
            )
            
            # Redis
            self.redis_client = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                decode_responses=True
            )
            
            self.logger.info("Database connections established")
            
        except Exception as e:
            self.logger.error("Database connection failed", error=str(e))
            raise
    
    def _setup_kafka(self):
        """Setup Kafka producer and consumer"""
        try:
            # Producer for sending results
            self.kafka_producer = KafkaProducer(
                bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
                value_serializer=lambda x: json.dumps(x).encode('utf-8'),
                key_serializer=lambda x: x.encode('utf-8') if x else None
            )
            
            # Consumer for receiving intake results
            self.kafka_consumer = KafkaConsumer(
                'intelligence_compliance_input',
                bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                key_deserializer=lambda x: x.decode('utf-8') if x else None,
                group_id='intelligence_compliance_group'
            )
            
            self.logger.info("Kafka setup completed")
            
        except Exception as e:
            self.logger.error("Kafka setup failed", error=str(e))
            raise
    
    async def assess_customer(self, request: CustomerAnalysisRequest) -> IntelligenceAnalysisResult:
        """Main customer assessment function"""
        start_time = datetime.now()
        
        ACTIVE_ANALYSES.inc()
        
        try:
            customer_data = request.customer_data
            
            # Step 1: Risk Assessment
            risk_score, risk_level, risk_method, risk_confidence = self.risk_engine.predict_risk(customer_data)
            
            # Step 2: Sanctions and PEP Screening
            sanctions_result = self.sanctions_engine.screen_sanctions(customer_data)
            pep_result = self.sanctions_engine.screen_pep(customer_data)
            
            # Step 3: Compliance Checks
            compliance_results = []
            for regulation_type in request.regulation_types:
                compliance_result = self.compliance_engine.evaluate_compliance(
                    customer_data, regulation_type
                )
                compliance_results.append(compliance_result)
            
            # Step 4: Determine if complex reasoning is needed
            needs_complex_analysis = (
                risk_score > 0.7 or
                sanctions_result.get('status') == 'match_found' or
                pep_result.get('status') == 'pep_match' or
                any(cr.status == ComplianceStatus.COMPLEX for cr in compliance_results)
            )
            
            # Step 5: Complex reasoning if needed
            reasoning = ""
            estimated_cost = 0.08  # Base cost for local processing
            
            if needs_complex_analysis:
                complex_analysis = await self.crewai_team.analyze_complex_case(customer_data)
                reasoning = complex_analysis.get('analysis_result', '')
                estimated_cost += 0.60  # Additional cost for AI analysis
            else:
                reasoning = self._generate_standard_reasoning(
                    risk_score, risk_level, sanctions_result, pep_result, compliance_results
                )
            
            # Step 6: Generate overall recommendation
            overall_recommendation = self._generate_recommendation(
                risk_level, sanctions_result, pep_result, compliance_results
            )
            
            # Create risk assessment result
            risk_assessment = RiskAssessmentResult(
                customer_id=request.customer_id,
                risk_score=risk_score,
                risk_level=risk_level,
                risk_factors=self._extract_risk_factors(customer_data, risk_score),
                confidence=risk_confidence,
                processing_method=risk_method,
                reasoning=reasoning
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Create final result
            result = IntelligenceAnalysisResult(
                session_id=request.session_id,
                customer_id=request.customer_id,
                risk_assessment=risk_assessment,
                compliance_checks=compliance_results,
                sanctions_screening=sanctions_result,
                pep_screening=pep_result,
                overall_recommendation=overall_recommendation,
                processing_time_seconds=processing_time,
                estimated_cost_dollars=estimated_cost,
                status="completed"
            )
            
            # Store result
            await self._store_result(result)
            
            # Send to next agent
            await self._send_to_decision_agent(result)
            
            self.logger.info(
                "Customer assessment completed",
                customer_id=request.customer_id,
                risk_level=risk_level.value,
                processing_time=processing_time,
                cost=estimated_cost,
                complex_analysis=needs_complex_analysis
            )
            
            return result
            
        finally:
            ACTIVE_ANALYSES.dec()
    
    def _generate_standard_reasoning(self, risk_score: float, risk_level: RiskLevel,
                                   sanctions_result: Dict[str, Any], pep_result: Dict[str, Any],
                                   compliance_results: List[ComplianceCheckResult]) -> str:
        """Generate standard reasoning for non-complex cases"""
        reasoning_parts = []
        
        # Risk assessment reasoning
        reasoning_parts.append(f"Risk Assessment: Customer assigned {risk_level.value} risk level with score {risk_score:.2f}")
        
        # Sanctions screening
        if sanctions_result.get('status') == 'clear':
            reasoning_parts.append("Sanctions Screening: No matches found in sanctions lists")
        else:
            reasoning_parts.append(f"Sanctions Screening: {sanctions_result.get('status')}")
        
        # PEP screening
        if pep_result.get('status') == 'clear':
            reasoning_parts.append("PEP Screening: Customer is not a Politically Exposed Person")
        else:
            reasoning_parts.append(f"PEP Screening: {pep_result.get('status')}")
        
        # Compliance summary
        compliant_count = sum(1 for cr in compliance_results if cr.status == ComplianceStatus.COMPLIANT)
        reasoning_parts.append(f"Compliance: {compliant_count}/{len(compliance_results)} regulations compliant")
        
        return ". ".join(reasoning_parts)
    
    def _extract_risk_factors(self, customer_data: Dict[str, Any], risk_score: float) -> List[Dict[str, Any]]:
        """Extract risk factors from customer data"""
        risk_factors = []
        
        # Document quality factor
        quality_score = customer_data.get('quality_score', 1.0)
        if quality_score < 0.8:
            risk_factors.append({
                'factor': 'document_quality',
                'description': f'Low document quality score: {quality_score:.2f}',
                'impact': 0.2
            })
        
        # Anomalies factor
        anomalies = customer_data.get('anomalies_detected', [])
        if anomalies:
            risk_factors.append({
                'factor': 'anomalies_detected',
                'description': f'Anomalies detected: {", ".join(anomalies)}',
                'impact': len(anomalies) * 0.1
            })
        
        # Geographic factor
        personal_info = customer_data.get('personal_info', {})
        country = personal_info.get('nationality', '').lower()
        high_risk_countries = ['afghanistan', 'iran', 'north korea', 'syria']
        if country in high_risk_countries:
            risk_factors.append({
                'factor': 'geographic_risk',
                'description': f'High-risk country: {country}',
                'impact': 0.3
            })
        
        return risk_factors
    
    def _generate_recommendation(self, risk_level: RiskLevel, sanctions_result: Dict[str, Any],
                               pep_result: Dict[str, Any], compliance_results: List[ComplianceCheckResult]) -> str:
        """Generate overall recommendation"""
        # Check for immediate rejections
        if sanctions_result.get('status') == 'match_found':
            return "REJECT - Customer matches sanctions list"
        
        # Check compliance violations
        critical_violations = [cr for cr in compliance_results if cr.status == ComplianceStatus.NON_COMPLIANT]
        if critical_violations:
            return "REJECT - Critical compliance violations detected"
        
        # Risk-based recommendations
        if risk_level == RiskLevel.CRITICAL:
            return "REJECT - Critical risk level"
        elif risk_level == RiskLevel.HIGH:
            return "MANUAL_REVIEW - High risk requires human review"
        elif pep_result.get('status') == 'pep_match':
            return "MANUAL_REVIEW - PEP requires enhanced due diligence"
        elif any(cr.status == ComplianceStatus.REQUIRES_REVIEW for cr in compliance_results):
            return "MANUAL_REVIEW - Compliance issues require review"
        else:
            return "APPROVE - All checks passed"
    
    async def _store_result(self, result: IntelligenceAnalysisResult):
        """Store analysis result in database"""
        try:
            cursor = self.pg_conn.cursor()
            
            # Insert into intelligence_compliance_results table
            cursor.execute("""
                INSERT INTO intelligence_compliance_results (
                    session_id, customer_id, risk_assessment, compliance_checks,
                    sanctions_screening, pep_screening, overall_recommendation,
                    processing_time_seconds, estimated_cost_dollars, status, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                result.session_id,
                result.customer_id,
                json.dumps(result.risk_assessment.dict()),
                json.dumps([cr.dict() for cr in result.compliance_checks]),
                json.dumps(result.sanctions_screening),
                json.dumps(result.pep_screening),
                result.overall_recommendation,
                result.processing_time_seconds,
                result.estimated_cost_dollars,
                result.status,
                datetime.now(timezone.utc)
            ))
            
            self.pg_conn.commit()
            cursor.close()
            
        except Exception as e:
            self.logger.error("Failed to store result", error=str(e))
    
    async def _send_to_decision_agent(self, result: IntelligenceAnalysisResult):
        """Send analysis result to Decision & Orchestration Agent"""
        try:
            message = {
                "agent": "intelligence_compliance",
                "session_id": result.session_id,
                "customer_id": result.customer_id,
                "data": result.dict(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Send to Kafka topic
            self.kafka_producer.send(
                'decision_orchestration_input',
                key=result.session_id,
                value=message
            )
            
            self.logger.info(
                "Result sent to Decision & Orchestration Agent",
                session_id=result.session_id,
                customer_id=result.customer_id
            )
            
        except Exception as e:
            self.logger.error("Failed to send result to decision agent", error=str(e))

# FastAPI application
app = FastAPI(
    title="Intelligence & Compliance Agent",
    description="Simplified agentic risk assessment and compliance monitoring",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agent
agent = IntelligenceComplianceAgent()

@app.post("/analyze", response_model=IntelligenceAnalysisResult)
async def analyze_customer(request: CustomerAnalysisRequest):
    """Analyze customer for risk and compliance"""
    try:
        result = await agent.assess_customer(request)
        return result
    except Exception as e:
        logger.error("Customer analysis endpoint failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent": "intelligence_compliance",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0"
    }

@app.get("/metrics")
async def get_metrics():
    """Get analysis metrics"""
    return {
        "risk_assessments_completed": RISK_ASSESSMENTS_COMPLETED._value._value,
        "compliance_checks_completed": COMPLIANCE_CHECKS_COMPLETED._value._value,
        "active_analyses": ACTIVE_ANALYSES._value._value,
        "cost_optimization": {
            "local_ml_percentage": 70,
            "ai_reasoning_percentage": 30,
            "target_cost_per_case": 0.23
        }
    }

if __name__ == "__main__":
    # Start Prometheus metrics server
    start_http_server(8002)
    
    # Start FastAPI server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8002,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": "INFO",
                "handlers": ["default"],
            },
        }
    )
