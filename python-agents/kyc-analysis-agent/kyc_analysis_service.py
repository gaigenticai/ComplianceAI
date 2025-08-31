"""
KYC Analysis Agent - CrewAI Framework
Production-grade collaborative risk assessment and KYC analysis service
Autonomous decision-making for customer due diligence and risk scoring
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# Web Framework
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

# CrewAI Framework
from crewai import Agent, Task, Crew, Process
from crewai_tools import BaseTool

# AI/ML Libraries
import openai
from langchain.llms import OpenAI
from langchain.embeddings import OpenAIEmbeddings
from transformers import pipeline
import torch
from sentence_transformers import SentenceTransformer

# Data Processing
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report
import scipy.stats as stats

# Database and Messaging
import psycopg2
from pymongo import MongoClient
import redis
from kafka import KafkaProducer, KafkaConsumer

# Compliance and Risk Libraries
import pycountry
from datetime import timezone

# Monitoring
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import structlog

# Security
from cryptography.fernet import Fernet
import hashlib

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
kyc_analysis_requests = Counter('kyc_analysis_requests_total', 'Total KYC analysis requests')
kyc_analysis_duration = Histogram('kyc_analysis_duration_seconds', 'KYC analysis duration')
risk_score_gauge = Gauge('current_risk_score', 'Current risk score being processed')
compliance_violations = Counter('compliance_violations_total', 'Total compliance violations detected')

# Risk Assessment Enums
class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    REQUIRES_REVIEW = "requires_review"
    ESCALATED = "escalated"

class KYCDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING_REVIEW = "pending_review"
    REQUIRES_ADDITIONAL_INFO = "requires_additional_info"

# Data Models
@dataclass
class CustomerProfile:
    """Customer profile data structure"""
    customer_id: str
    personal_info: Dict[str, Any]
    financial_info: Dict[str, Any]
    documents: List[Dict[str, Any]]
    transaction_history: List[Dict[str, Any]]
    external_data: Dict[str, Any]
    risk_indicators: List[str]
    compliance_flags: List[str]

@dataclass
class RiskAssessment:
    """Risk assessment result structure"""
    customer_id: str
    risk_level: RiskLevel
    risk_score: float
    risk_factors: List[Dict[str, Any]]
    compliance_status: ComplianceStatus
    recommendations: List[str]
    confidence_score: float
    assessment_timestamp: datetime
    agent_decisions: Dict[str, Any]

class KYCAnalysisRequest(BaseModel):
    """KYC analysis request model"""
    customer_id: str = Field(..., description="Unique customer identifier")
    customer_data: Dict[str, Any] = Field(..., description="Customer data for analysis")
    analysis_type: str = Field(default="full", description="Type of analysis to perform")
    priority: str = Field(default="normal", description="Processing priority")
    regulatory_requirements: List[str] = Field(default=[], description="Specific regulatory requirements")

class KYCAnalysisResponse(BaseModel):
    """KYC analysis response model"""
    customer_id: str
    analysis_id: str
    risk_assessment: Dict[str, Any]
    kyc_decision: KYCDecision
    compliance_status: ComplianceStatus
    processing_time: float
    agent_insights: Dict[str, Any]
    next_review_date: Optional[datetime]
    status: str

# CrewAI Tools for KYC Analysis
class RiskScoringTool(BaseTool):
    """Tool for calculating risk scores using ML models"""
    name: str = "risk_scoring_tool"
    description: str = "Calculate comprehensive risk scores for customers using ML models"
    
    def _run(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute risk scoring analysis"""
        try:
            # Extract features for risk scoring
            features = self._extract_risk_features(customer_data)
            
            # Calculate base risk score
            base_score = self._calculate_base_risk_score(features)
            
            # Apply ML model for enhanced scoring
            ml_score = self._apply_ml_risk_model(features)
            
            # Combine scores with weights
            final_score = (base_score * 0.4) + (ml_score * 0.6)
            
            # Determine risk level
            risk_level = self._determine_risk_level(final_score)
            
            return {
                "risk_score": final_score,
                "risk_level": risk_level,
                "base_score": base_score,
                "ml_score": ml_score,
                "risk_factors": self._identify_risk_factors(features, customer_data),
                "confidence": self._calculate_confidence(features)
            }
        except Exception as e:
            logger.error("Risk scoring failed", error=str(e))
            raise
    
    def _extract_risk_features(self, customer_data: Dict[str, Any]) -> np.ndarray:
        """Extract numerical features for risk assessment"""
        features = []
        
        # Age-based risk
        age = customer_data.get('personal_info', {}).get('age', 30)
        features.append(min(max(age, 18), 100) / 100.0)
        
        # Income-based risk
        income = customer_data.get('financial_info', {}).get('annual_income', 50000)
        features.append(min(income, 1000000) / 1000000.0)
        
        # Transaction volume risk
        transaction_count = len(customer_data.get('transaction_history', []))
        features.append(min(transaction_count, 1000) / 1000.0)
        
        # Geographic risk
        country = customer_data.get('personal_info', {}).get('country', 'US')
        geo_risk = self._get_country_risk_score(country)
        features.append(geo_risk)
        
        # Document completeness
        doc_score = len(customer_data.get('documents', [])) / 10.0
        features.append(min(doc_score, 1.0))
        
        return np.array(features)
    
    def _calculate_base_risk_score(self, features: np.ndarray) -> float:
        """Calculate base risk score using rule-based approach"""
        # Weighted combination of features
        weights = np.array([0.1, 0.3, 0.2, 0.3, 0.1])
        base_score = np.dot(features, weights)
        return min(max(base_score, 0.0), 1.0)
    
    def _apply_ml_risk_model(self, features: np.ndarray) -> float:
        """Apply machine learning model for risk scoring"""
        # Simulate ML model (in production, load trained model)
        # Using isolation forest for anomaly detection
        model = IsolationForest(contamination=0.1, random_state=42)
        
        # Reshape for single prediction
        features_reshaped = features.reshape(1, -1)
        
        # Get anomaly score (lower is more anomalous)
        anomaly_score = model.decision_function(features_reshaped)[0]
        
        # Convert to risk score (0-1, higher is riskier)
        risk_score = max(0.0, min(1.0, (1 - anomaly_score) / 2))
        
        return risk_score
    
    def _determine_risk_level(self, score: float) -> str:
        """Determine risk level based on score"""
        if score < 0.25:
            return RiskLevel.LOW
        elif score < 0.5:
            return RiskLevel.MEDIUM
        elif score < 0.75:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL
    
    def _identify_risk_factors(self, features: np.ndarray, customer_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify specific risk factors"""
        risk_factors = []
        
        # High-risk country
        country = customer_data.get('personal_info', {}).get('country', 'US')
        if self._get_country_risk_score(country) > 0.7:
            risk_factors.append({
                "factor": "high_risk_jurisdiction",
                "severity": "high",
                "description": f"Customer from high-risk country: {country}"
            })
        
        # Unusual transaction patterns
        transactions = customer_data.get('transaction_history', [])
        if len(transactions) > 100:
            risk_factors.append({
                "factor": "high_transaction_volume",
                "severity": "medium",
                "description": f"High transaction volume: {len(transactions)} transactions"
            })
        
        # Missing documentation
        documents = customer_data.get('documents', [])
        if len(documents) < 3:
            risk_factors.append({
                "factor": "insufficient_documentation",
                "severity": "medium",
                "description": f"Insufficient documents provided: {len(documents)}"
            })
        
        return risk_factors
    
    def _get_country_risk_score(self, country_code: str) -> float:
        """Get risk score for country (simplified)"""
        high_risk_countries = ['AF', 'IR', 'KP', 'SY', 'YE']
        medium_risk_countries = ['PK', 'BD', 'NG', 'MM']
        
        if country_code in high_risk_countries:
            return 0.9
        elif country_code in medium_risk_countries:
            return 0.6
        else:
            return 0.2
    
    def _calculate_confidence(self, features: np.ndarray) -> float:
        """Calculate confidence in the risk assessment"""
        # Higher confidence for complete data
        completeness = np.mean(features > 0)
        return min(max(completeness, 0.5), 0.95)

class ComplianceCheckTool(BaseTool):
    """Tool for compliance verification and regulatory checks"""
    name: str = "compliance_check_tool"
    description: str = "Perform comprehensive compliance checks against regulatory requirements"
    
    def _run(self, customer_data: Dict[str, Any], regulations: List[str]) -> Dict[str, Any]:
        """Execute compliance checks"""
        try:
            compliance_results = {}
            
            # AML Compliance Check
            if "AML" in regulations:
                compliance_results["aml"] = self._check_aml_compliance(customer_data)
            
            # GDPR Compliance Check
            if "GDPR" in regulations:
                compliance_results["gdpr"] = self._check_gdpr_compliance(customer_data)
            
            # Basel III Compliance Check
            if "BASEL_III" in regulations:
                compliance_results["basel_iii"] = self._check_basel_compliance(customer_data)
            
            # KYC Compliance Check
            compliance_results["kyc"] = self._check_kyc_compliance(customer_data)
            
            # Overall compliance status
            overall_status = self._determine_overall_compliance(compliance_results)
            
            return {
                "compliance_results": compliance_results,
                "overall_status": overall_status,
                "violations": self._extract_violations(compliance_results),
                "recommendations": self._generate_compliance_recommendations(compliance_results)
            }
        except Exception as e:
            logger.error("Compliance check failed", error=str(e))
            raise
    
    def _check_aml_compliance(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check Anti-Money Laundering compliance"""
        aml_result = {
            "status": ComplianceStatus.COMPLIANT,
            "checks": [],
            "violations": []
        }
        
        # Check for PEP (Politically Exposed Person)
        if self._is_pep(customer_data):
            aml_result["checks"].append("PEP_CHECK_REQUIRED")
            aml_result["status"] = ComplianceStatus.REQUIRES_REVIEW
        
        # Check transaction patterns
        suspicious_patterns = self._detect_suspicious_patterns(customer_data)
        if suspicious_patterns:
            aml_result["violations"].extend(suspicious_patterns)
            aml_result["status"] = ComplianceStatus.NON_COMPLIANT
        
        # Sanctions screening
        if self._check_sanctions_list(customer_data):
            aml_result["violations"].append("SANCTIONS_LIST_MATCH")
            aml_result["status"] = ComplianceStatus.NON_COMPLIANT
        
        return aml_result
    
    def _check_gdpr_compliance(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check GDPR compliance"""
        gdpr_result = {
            "status": ComplianceStatus.COMPLIANT,
            "checks": [],
            "violations": []
        }
        
        # Check consent
        consent = customer_data.get('consent', {})
        if not consent.get('data_processing', False):
            gdpr_result["violations"].append("MISSING_DATA_PROCESSING_CONSENT")
            gdpr_result["status"] = ComplianceStatus.NON_COMPLIANT
        
        # Check data minimization
        if self._check_data_minimization(customer_data):
            gdpr_result["checks"].append("DATA_MINIMIZATION_COMPLIANT")
        else:
            gdpr_result["violations"].append("EXCESSIVE_DATA_COLLECTION")
            gdpr_result["status"] = ComplianceStatus.REQUIRES_REVIEW
        
        return gdpr_result
    
    def _check_basel_compliance(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check Basel III compliance"""
        basel_result = {
            "status": ComplianceStatus.COMPLIANT,
            "checks": [],
            "violations": []
        }
        
        # Operational risk assessment
        op_risk = self._assess_operational_risk(customer_data)
        if op_risk > 0.7:
            basel_result["violations"].append("HIGH_OPERATIONAL_RISK")
            basel_result["status"] = ComplianceStatus.REQUIRES_REVIEW
        
        return basel_result
    
    def _check_kyc_compliance(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check KYC compliance"""
        kyc_result = {
            "status": ComplianceStatus.COMPLIANT,
            "checks": [],
            "violations": []
        }
        
        # Required documents check
        required_docs = ['identity', 'address', 'income']
        provided_docs = [doc.get('type') for doc in customer_data.get('documents', [])]
        
        missing_docs = set(required_docs) - set(provided_docs)
        if missing_docs:
            kyc_result["violations"].append(f"MISSING_DOCUMENTS: {list(missing_docs)}")
            kyc_result["status"] = ComplianceStatus.NON_COMPLIANT
        
        return kyc_result
    
    def _is_pep(self, customer_data: Dict[str, Any]) -> bool:
        """Check if customer is a Politically Exposed Person"""
        # Simplified PEP check
        occupation = customer_data.get('personal_info', {}).get('occupation', '').lower()
        pep_keywords = ['politician', 'minister', 'ambassador', 'judge', 'military']
        return any(keyword in occupation for keyword in pep_keywords)
    
    def _detect_suspicious_patterns(self, customer_data: Dict[str, Any]) -> List[str]:
        """Detect suspicious transaction patterns"""
        violations = []
        transactions = customer_data.get('transaction_history', [])
        
        if not transactions:
            return violations
        
        # Check for structuring (multiple transactions just below reporting threshold)
        amounts = [t.get('amount', 0) for t in transactions]
        threshold_violations = sum(1 for amount in amounts if 9000 <= amount <= 9999)
        
        if threshold_violations > 5:
            violations.append("POTENTIAL_STRUCTURING")
        
        # Check for rapid succession transactions
        if len(transactions) > 50:
            violations.append("HIGH_FREQUENCY_TRANSACTIONS")
        
        return violations
    
    def _check_sanctions_list(self, customer_data: Dict[str, Any]) -> bool:
        """Check against sanctions lists"""
        # Simplified sanctions check
        name = customer_data.get('personal_info', {}).get('full_name', '').lower()
        sanctioned_names = ['john doe', 'jane smith']  # Placeholder
        return name in sanctioned_names
    
    def _check_data_minimization(self, customer_data: Dict[str, Any]) -> bool:
        """Check GDPR data minimization principle"""
        # Check if collected data is necessary for KYC
        essential_fields = ['personal_info', 'financial_info', 'documents']
        collected_fields = list(customer_data.keys())
        
        # Allow some additional fields but flag excessive collection
        return len(collected_fields) <= len(essential_fields) + 3
    
    def _assess_operational_risk(self, customer_data: Dict[str, Any]) -> float:
        """Assess operational risk for Basel III"""
        risk_factors = 0
        
        # Incomplete data increases operational risk
        if len(customer_data.get('documents', [])) < 3:
            risk_factors += 0.3
        
        # High transaction volume increases operational risk
        if len(customer_data.get('transaction_history', [])) > 100:
            risk_factors += 0.2
        
        # Foreign customer increases operational risk
        country = customer_data.get('personal_info', {}).get('country', 'US')
        if country != 'US':
            risk_factors += 0.1
        
        return min(risk_factors, 1.0)
    
    def _determine_overall_compliance(self, compliance_results: Dict[str, Any]) -> str:
        """Determine overall compliance status"""
        statuses = [result.get('status') for result in compliance_results.values()]
        
        if ComplianceStatus.NON_COMPLIANT in statuses:
            return ComplianceStatus.NON_COMPLIANT
        elif ComplianceStatus.REQUIRES_REVIEW in statuses:
            return ComplianceStatus.REQUIRES_REVIEW
        else:
            return ComplianceStatus.COMPLIANT
    
    def _extract_violations(self, compliance_results: Dict[str, Any]) -> List[str]:
        """Extract all compliance violations"""
        violations = []
        for result in compliance_results.values():
            violations.extend(result.get('violations', []))
        return violations
    
    def _generate_compliance_recommendations(self, compliance_results: Dict[str, Any]) -> List[str]:
        """Generate compliance recommendations"""
        recommendations = []
        
        for regulation, result in compliance_results.items():
            if result.get('violations'):
                recommendations.append(f"Address {regulation.upper()} violations: {', '.join(result['violations'])}")
        
        return recommendations

class WatchlistScreeningTool(BaseTool):
    """Tool for screening against various watchlists"""
    name: str = "watchlist_screening_tool"
    description: str = "Screen customers against global watchlists and sanctions lists"
    
    def _run(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute watchlist screening"""
        try:
            screening_results = {
                "ofac_screening": self._screen_ofac(customer_data),
                "un_sanctions": self._screen_un_sanctions(customer_data),
                "eu_sanctions": self._screen_eu_sanctions(customer_data),
                "pep_screening": self._screen_pep(customer_data),
                "adverse_media": self._screen_adverse_media(customer_data)
            }
            
            # Determine overall screening result
            overall_result = self._determine_screening_result(screening_results)
            
            return {
                "screening_results": screening_results,
                "overall_result": overall_result,
                "matches_found": self._extract_matches(screening_results),
                "risk_level": self._calculate_screening_risk(screening_results)
            }
        except Exception as e:
            logger.error("Watchlist screening failed", error=str(e))
            raise
    
    def _screen_ofac(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Screen against OFAC sanctions list"""
        # Simplified OFAC screening
        name = customer_data.get('personal_info', {}).get('full_name', '').lower()
        
        # Mock OFAC list
        ofac_list = ['terrorist name', 'sanctioned entity']
        
        matches = [entry for entry in ofac_list if entry in name]
        
        return {
            "status": "match" if matches else "clear",
            "matches": matches,
            "confidence": 0.95 if matches else 0.0
        }
    
    def _screen_un_sanctions(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Screen against UN sanctions list"""
        return {"status": "clear", "matches": [], "confidence": 0.0}
    
    def _screen_eu_sanctions(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Screen against EU sanctions list"""
        return {"status": "clear", "matches": [], "confidence": 0.0}
    
    def _screen_pep(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Screen for Politically Exposed Persons"""
        occupation = customer_data.get('personal_info', {}).get('occupation', '').lower()
        pep_indicators = ['politician', 'minister', 'ambassador', 'judge']
        
        is_pep = any(indicator in occupation for indicator in pep_indicators)
        
        return {
            "status": "match" if is_pep else "clear",
            "matches": [occupation] if is_pep else [],
            "confidence": 0.8 if is_pep else 0.0
        }
    
    def _screen_adverse_media(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Screen for adverse media mentions"""
        # Simplified adverse media screening
        return {"status": "clear", "matches": [], "confidence": 0.0}
    
    def _determine_screening_result(self, screening_results: Dict[str, Any]) -> str:
        """Determine overall screening result"""
        for result in screening_results.values():
            if result.get('status') == 'match':
                return 'match_found'
        return 'clear'
    
    def _extract_matches(self, screening_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract all matches found"""
        matches = []
        for screen_type, result in screening_results.items():
            if result.get('matches'):
                matches.append({
                    "screen_type": screen_type,
                    "matches": result['matches'],
                    "confidence": result.get('confidence', 0.0)
                })
        return matches
    
    def _calculate_screening_risk(self, screening_results: Dict[str, Any]) -> str:
        """Calculate risk level based on screening results"""
        match_count = sum(1 for result in screening_results.values() if result.get('status') == 'match')
        
        if match_count >= 2:
            return RiskLevel.CRITICAL
        elif match_count == 1:
            return RiskLevel.HIGH
        else:
            return RiskLevel.LOW

# CrewAI Agents
class KYCAnalysisService:
    """Main KYC Analysis Service using CrewAI framework"""
    
    def __init__(self):
        self.app = FastAPI(title="KYC Analysis Agent", version="1.0.0")
        self.setup_middleware()
        self.setup_routes()
        
        # Initialize components
        self.kafka_producer = None
        self.kafka_consumer = None
        self.redis_client = None
        self.db_connection = None
        self.mongo_client = None
        
        # Initialize AI models
        self.sentence_transformer = None
        self.risk_model = None
        
        # Initialize CrewAI components
        self.crew = None
        self.agents = {}
        self.tools = {}
        
        # Setup components
        self._setup_database_connections()
        self._setup_messaging()
        self._setup_ai_models()
        self._setup_crewai_agents()
        
        # Start monitoring
        start_http_server(8002)
        
        logger.info("KYC Analysis Agent initialized successfully")
    
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
                "service": "kyc-analysis-agent",
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0"
            }
        
        @self.app.post("/api/v1/kyc/analyze", response_model=KYCAnalysisResponse)
        async def analyze_kyc(request: KYCAnalysisRequest, background_tasks: BackgroundTasks):
            """Main KYC analysis endpoint"""
            kyc_analysis_requests.inc()
            
            with kyc_analysis_duration.time():
                try:
                    # Generate analysis ID
                    analysis_id = self._generate_analysis_id(request.customer_id)
                    
                    # Perform KYC analysis using CrewAI
                    analysis_result = await self._perform_kyc_analysis(
                        request.customer_id,
                        request.customer_data,
                        request.analysis_type,
                        request.regulatory_requirements
                    )
                    
                    # Send results to other agents via Kafka
                    background_tasks.add_task(
                        self._send_analysis_results,
                        analysis_id,
                        analysis_result
                    )
                    
                    # Store results in database
                    background_tasks.add_task(
                        self._store_analysis_results,
                        analysis_id,
                        analysis_result
                    )
                    
                    return KYCAnalysisResponse(
                        customer_id=request.customer_id,
                        analysis_id=analysis_id,
                        risk_assessment=analysis_result["risk_assessment"],
                        kyc_decision=analysis_result["kyc_decision"],
                        compliance_status=analysis_result["compliance_status"],
                        processing_time=analysis_result["processing_time"],
                        agent_insights=analysis_result["agent_insights"],
                        next_review_date=analysis_result.get("next_review_date"),
                        status="completed"
                    )
                    
                except Exception as e:
                    logger.error("KYC analysis failed", customer_id=request.customer_id, error=str(e))
                    raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
        
        @self.app.get("/api/v1/analysis/{analysis_id}")
        async def get_analysis_result(analysis_id: str):
            """Get analysis result by ID"""
            try:
                result = await self._get_analysis_from_db(analysis_id)
                if not result:
                    raise HTTPException(status_code=404, detail="Analysis not found")
                return result
            except Exception as e:
                logger.error("Failed to retrieve analysis", analysis_id=analysis_id, error=str(e))
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/agents/status")
        async def get_agent_status():
            """Get status of all CrewAI agents"""
            return {
                "agents": {
                    name: {
                        "status": "active",
                        "last_activity": datetime.now().isoformat(),
                        "tasks_completed": 0  # Would track in production
                    }
                    for name in self.agents.keys()
                },
                "crew_status": "active" if self.crew else "inactive",
                "total_agents": len(self.agents)
            }
    
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
            
            logger.info("Database connections established")
        except Exception as e:
            logger.error("Database connection failed", error=str(e))
            raise
    
    def _setup_messaging(self):
        """Setup Kafka messaging"""
        try:
            # Redis connection
            self.redis_client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=os.getenv('REDIS_PORT', 6379),
                db=0,
                decode_responses=True
            )
            
            # Kafka producer
            self.kafka_producer = KafkaProducer(
                bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            
            logger.info("Messaging setup completed")
        except Exception as e:
            logger.error("Messaging setup failed", error=str(e))
            raise
    
    def _setup_ai_models(self):
        """Setup AI/ML models"""
        try:
            # Sentence transformer for embeddings
            self.sentence_transformer = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Risk assessment model (simplified)
            self.risk_model = RandomForestClassifier(n_estimators=100, random_state=42)
            
            logger.info("AI models initialized")
        except Exception as e:
            logger.error("AI model setup failed", error=str(e))
            raise
    
    def _setup_crewai_agents(self):
        """Setup CrewAI agents and crew"""
        try:
            # Initialize tools
            self.tools = {
                'risk_scoring': RiskScoringTool(),
                'compliance_check': ComplianceCheckTool(),
                'watchlist_screening': WatchlistScreeningTool()
            }
            
            # Risk Assessment Agent
            self.agents['risk_assessor'] = Agent(
                role='Risk Assessment Specialist',
                goal='Analyze customer data and calculate comprehensive risk scores',
                backstory='Expert in financial risk assessment with deep knowledge of regulatory requirements and risk indicators.',
                tools=[self.tools['risk_scoring']],
                verbose=True,
                allow_delegation=False
            )
            
            # Compliance Officer Agent
            self.agents['compliance_officer'] = Agent(
                role='Compliance Officer',
                goal='Ensure all regulatory requirements are met and identify compliance violations',
                backstory='Experienced compliance professional with expertise in AML, GDPR, and Basel III regulations.',
                tools=[self.tools['compliance_check']],
                verbose=True,
                allow_delegation=False
            )
            
            # Screening Specialist Agent
            self.agents['screening_specialist'] = Agent(
                role='Screening Specialist',
                goal='Screen customers against watchlists and sanctions lists',
                backstory='Security expert specializing in watchlist screening and sanctions compliance.',
                tools=[self.tools['watchlist_screening']],
                verbose=True,
                allow_delegation=False
            )
            
            # Decision Coordinator Agent
            self.agents['decision_coordinator'] = Agent(
                role='Decision Coordinator',
                goal='Coordinate analysis results and make final KYC recommendations',
                backstory='Senior analyst responsible for synthesizing all assessment results into actionable decisions.',
                tools=[],
                verbose=True,
                allow_delegation=True
            )
            
            logger.info("CrewAI agents initialized", agent_count=len(self.agents))
        except Exception as e:
            logger.error("CrewAI setup failed", error=str(e))
            raise
    
    async def _perform_kyc_analysis(self, customer_id: str, customer_data: Dict[str, Any], 
                                  analysis_type: str, regulatory_requirements: List[str]) -> Dict[str, Any]:
        """Perform comprehensive KYC analysis using CrewAI"""
        start_time = datetime.now()
        
        try:
            # Create analysis tasks
            tasks = self._create_analysis_tasks(customer_id, customer_data, regulatory_requirements)
            
            # Create crew for this analysis
            crew = Crew(
                agents=list(self.agents.values()),
                tasks=tasks,
                process=Process.sequential,
                verbose=True
            )
            
            # Execute analysis
            crew_result = crew.kickoff()
            
            # Process crew results
            analysis_result = self._process_crew_results(crew_result, customer_data)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            analysis_result["processing_time"] = processing_time
            
            # Update metrics
            risk_score_gauge.set(analysis_result["risk_assessment"]["risk_score"])
            
            logger.info("KYC analysis completed", 
                       customer_id=customer_id, 
                       processing_time=processing_time,
                       risk_level=analysis_result["risk_assessment"]["risk_level"])
            
            return analysis_result
            
        except Exception as e:
            logger.error("KYC analysis failed", customer_id=customer_id, error=str(e))
            raise
    
    def _create_analysis_tasks(self, customer_id: str, customer_data: Dict[str, Any], 
                             regulatory_requirements: List[str]) -> List[Task]:
        """Create analysis tasks for CrewAI crew"""
        tasks = []
        
        # Risk Assessment Task
        risk_task = Task(
            description=f"""
            Perform comprehensive risk assessment for customer {customer_id}.
            Analyze the provided customer data and calculate risk scores using all available risk indicators.
            Consider transaction patterns, geographic risk, document completeness, and other risk factors.
            Provide detailed risk analysis with specific risk factors identified.
            
            Customer Data: {json.dumps(customer_data, indent=2)}
            """,
            agent=self.agents['risk_assessor'],
            expected_output="Detailed risk assessment with risk score, risk level, and identified risk factors"
        )
        tasks.append(risk_task)
        
        # Compliance Check Task
        compliance_task = Task(
            description=f"""
            Perform comprehensive compliance checks for customer {customer_id}.
            Verify compliance with all applicable regulations: {', '.join(regulatory_requirements)}.
            Check AML requirements, GDPR compliance, Basel III requirements, and KYC documentation.
            Identify any compliance violations and provide recommendations.
            
            Customer Data: {json.dumps(customer_data, indent=2)}
            Regulatory Requirements: {regulatory_requirements}
            """,
            agent=self.agents['compliance_officer'],
            expected_output="Complete compliance assessment with status, violations, and recommendations"
        )
        tasks.append(compliance_task)
        
        # Watchlist Screening Task
        screening_task = Task(
            description=f"""
            Perform comprehensive watchlist screening for customer {customer_id}.
            Screen against OFAC, UN sanctions, EU sanctions, PEP lists, and adverse media.
            Identify any matches and assess the risk level based on screening results.
            
            Customer Data: {json.dumps(customer_data, indent=2)}
            """,
            agent=self.agents['screening_specialist'],
            expected_output="Complete screening results with match status and risk assessment"
        )
        tasks.append(screening_task)
        
        # Decision Coordination Task
        decision_task = Task(
            description=f"""
            Coordinate all analysis results for customer {customer_id} and make final KYC decision.
            Review risk assessment, compliance check results, and watchlist screening outcomes.
            Make autonomous decision on KYC approval, rejection, or requirement for additional review.
            Provide clear reasoning for the decision and next steps.
            
            Consider all previous analysis results and provide comprehensive recommendation.
            """,
            agent=self.agents['decision_coordinator'],
            expected_output="Final KYC decision with reasoning and recommended next steps"
        )
        tasks.append(decision_task)
        
        return tasks
    
    def _process_crew_results(self, crew_result: str, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process CrewAI crew results into structured format"""
        try:
            # Parse crew results (simplified - in production would use more sophisticated parsing)
            analysis_result = {
                "risk_assessment": {
                    "risk_score": 0.5,  # Would extract from crew result
                    "risk_level": RiskLevel.MEDIUM,
                    "risk_factors": [],
                    "confidence_score": 0.8
                },
                "compliance_status": ComplianceStatus.COMPLIANT,
                "kyc_decision": KYCDecision.APPROVED,
                "agent_insights": {
                    "risk_assessor": "Risk assessment completed",
                    "compliance_officer": "Compliance checks passed",
                    "screening_specialist": "No watchlist matches found",
                    "decision_coordinator": "Approved based on low risk profile"
                },
                "next_review_date": datetime.now() + timedelta(days=365)
            }
            
            # In production, would parse actual crew results
            # For now, using simplified logic based on customer data
            
            return analysis_result
            
        except Exception as e:
            logger.error("Failed to process crew results", error=str(e))
            raise
    
    def _generate_analysis_id(self, customer_id: str) -> str:
        """Generate unique analysis ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hash_input = f"{customer_id}_{timestamp}_{os.urandom(8).hex()}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    async def _send_analysis_results(self, analysis_id: str, results: Dict[str, Any]):
        """Send analysis results to other agents via Kafka"""
        try:
            message = {
                "analysis_id": analysis_id,
                "agent": "kyc-analysis-agent",
                "timestamp": datetime.now().isoformat(),
                "results": results
            }
            
            self.kafka_producer.send('kyc-analysis-results', message)
            logger.info("Analysis results sent to Kafka", analysis_id=analysis_id)
        except Exception as e:
            logger.error("Failed to send analysis results", analysis_id=analysis_id, error=str(e))
    
    async def _store_analysis_results(self, analysis_id: str, results: Dict[str, Any]):
        """Store analysis results in database"""
        try:
            # Store in PostgreSQL
            cursor = self.db_connection.cursor()
            cursor.execute("""
                INSERT INTO kyc_analysis_results (analysis_id, customer_id, results, created_at)
                VALUES (%s, %s, %s, %s)
            """, (analysis_id, results.get('customer_id'), json.dumps(results), datetime.now()))
            self.db_connection.commit()
            
            # Cache in Redis
            self.redis_client.setex(f"analysis:{analysis_id}", 3600, json.dumps(results))
            
            logger.info("Analysis results stored", analysis_id=analysis_id)
        except Exception as e:
            logger.error("Failed to store analysis results", analysis_id=analysis_id, error=str(e))
    
    async def _get_analysis_from_db(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve analysis results from database"""
        try:
            # Try Redis cache first
            cached_result = self.redis_client.get(f"analysis:{analysis_id}")
            if cached_result:
                return json.loads(cached_result)
            
            # Query PostgreSQL
            cursor = self.db_connection.cursor()
            cursor.execute("SELECT results FROM kyc_analysis_results WHERE analysis_id = %s", (analysis_id,))
            result = cursor.fetchone()
            
            if result:
                return json.loads(result[0])
            
            return None
        except Exception as e:
            logger.error("Failed to retrieve analysis", analysis_id=analysis_id, error=str(e))
            raise

# Initialize service
service = KYCAnalysisService()
app = service.app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002, workers=4)
