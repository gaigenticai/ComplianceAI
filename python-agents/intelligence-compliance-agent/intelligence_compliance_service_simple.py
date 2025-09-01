"""
Intelligence & Compliance Agent - Simplified Production Version
==============================================================

Simplified compliance monitoring using basic LangChain
Handles risk assessment, sanctions screening, and regulatory compliance
Removes complex CrewAI/AutoGen dependencies for production stability
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from enum import Enum
import uuid

# Web Framework
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# LangChain Framework (simplified)
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

# Database and Storage
import psycopg2
from psycopg2.extras import RealDictCursor
import pymongo
import redis

# ML and Data Processing
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib

# Monitoring and Logging
import structlog
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Production sanctions database
from sanctions_database import SanctionsDatabase, PEPDatabase

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
CASES_PROCESSED = Counter('intelligence_cases_processed_total', 'Total cases processed')
PROCESSING_TIME = Histogram('intelligence_processing_seconds', 'Time spent processing cases')
RISK_SCORES = Histogram('intelligence_risk_scores', 'Distribution of risk scores')
SANCTIONS_HITS = Counter('intelligence_sanctions_hits_total', 'Total sanctions hits')
PEP_MATCHES = Counter('intelligence_pep_matches_total', 'Total PEP matches')

class RiskLevel(Enum):
    """Risk level enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ComplianceStatus(Enum):
    """Compliance status enumeration"""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    REQUIRES_REVIEW = "requires_review"
    PENDING = "pending"

@dataclass
class RiskAssessment:
    """Risk assessment result"""
    risk_level: RiskLevel
    risk_score: float
    risk_factors: List[str]
    ml_confidence: float
    reasoning: str

@dataclass
class ComplianceResult:
    """Compliance check result"""
    status: ComplianceStatus
    violations: List[str]
    recommendations: List[str]
    sanctions_match: bool
    pep_match: bool
    aml_flags: List[str]

class IntelligenceComplianceAgent:
    """
    Simplified Intelligence & Compliance Agent
    Production-grade implementation without complex dependencies
    """
    
    def __init__(self):
        self.logger = logger.bind(component="intelligence_agent")
        
        # Initialize connections
        self._init_databases()
        self._init_ai_models()
        self._init_ml_models()
        
        # Load sanctions and PEP databases
        self.sanctions_db = SanctionsDatabase()
        self.pep_db = PEPDatabase()
        
        self.logger.info("Intelligence & Compliance Agent initialized")
    
    def _init_databases(self):
        """Initialize database connections"""
        try:
            # PostgreSQL
            self.pg_conn = psycopg2.connect(
                host=os.getenv('POSTGRES_HOST', 'postgres'),
                port=os.getenv('POSTGRES_PORT', 5432),
                database=os.getenv('POSTGRES_DB', 'compliance_ai'),
                user=os.getenv('POSTGRES_USER', 'postgres'),
                password=os.getenv('POSTGRES_PASSWORD', 'postgres')
            )
            
            # MongoDB
            mongo_uri = f"mongodb://{os.getenv('MONGO_USER', 'admin')}:{os.getenv('MONGO_PASSWORD', 'password')}@{os.getenv('MONGO_HOST', 'mongodb')}:27017/"
            self.mongo_client = pymongo.MongoClient(mongo_uri)
            self.mongo_db = self.mongo_client.compliance_ai
            
            # Redis
            self.redis_client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'redis'),
                port=os.getenv('REDIS_PORT', 6379),
                decode_responses=True
            )
            
            self.logger.info("Database connections initialized")
            
        except Exception as e:
            self.logger.error("Failed to initialize databases", error=str(e))
            raise
    
    def _init_ai_models(self):
        """Initialize AI models"""
        try:
            # OpenAI for complex reasoning (fallback only)
            self.llm = ChatOpenAI(
                model="gpt-4",
                temperature=0.1,
                openai_api_key=os.getenv('OPENAI_API_KEY')
            )
            
            # Risk assessment prompt
            self.risk_prompt = PromptTemplate(
                input_variables=["customer_data", "transaction_data", "risk_factors"],
                template="""
                Analyze the following customer and transaction data for compliance risks:
                
                Customer Data: {customer_data}
                Transaction Data: {transaction_data}
                Risk Factors: {risk_factors}
                
                Provide a detailed risk assessment including:
                1. Overall risk level (LOW/MEDIUM/HIGH/CRITICAL)
                2. Specific risk factors identified
                3. Compliance concerns
                4. Recommended actions
                
                Response format: JSON with risk_level, risk_score (0-100), risk_factors, and reasoning.
                """
            )
            
            self.risk_chain = LLMChain(llm=self.llm, prompt=self.risk_prompt)
            
            self.logger.info("AI models initialized")
            
        except Exception as e:
            self.logger.error("Failed to initialize AI models", error=str(e))
            raise
    
    def _init_ml_models(self):
        """Initialize local ML models for cost optimization"""
        try:
            # Load pre-trained risk scoring model
            model_path = "/app/models/risk_classifier.joblib"
            if os.path.exists(model_path):
                self.risk_classifier = joblib.load(model_path)
                self.scaler = joblib.load("/app/models/scaler.joblib")
                self.logger.info("Loaded pre-trained ML models")
            else:
                # Create simple model if none exists
                self.risk_classifier = RandomForestClassifier(n_estimators=100, random_state=42)
                self.scaler = StandardScaler()
                self.logger.info("Created new ML models")
            
        except Exception as e:
            self.logger.error("Failed to initialize ML models", error=str(e))
            # Continue without ML models
            self.risk_classifier = None
            self.scaler = None
    
    async def process_case(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main case processing method
        Combines risk assessment and compliance checking
        """
        start_time = datetime.now()
        case_id = case_data.get('case_id', str(uuid.uuid4()))
        
        try:
            self.logger.info("Processing intelligence case", case_id=case_id)
            CASES_PROCESSED.inc()
            
            # Extract customer and transaction data
            customer_data = case_data.get('customer_data', {})
            transaction_data = case_data.get('transaction_data', {})
            
            # Perform risk assessment
            risk_assessment = await self._assess_risk(customer_data, transaction_data)
            
            # Perform compliance checks
            compliance_result = await self._check_compliance(customer_data, transaction_data)
            
            # Combine results
            result = {
                'case_id': case_id,
                'timestamp': datetime.now().isoformat(),
                'risk_assessment': {
                    'risk_level': risk_assessment.risk_level.value,
                    'risk_score': risk_assessment.risk_score,
                    'risk_factors': risk_assessment.risk_factors,
                    'ml_confidence': risk_assessment.ml_confidence,
                    'reasoning': risk_assessment.reasoning
                },
                'compliance_result': {
                    'status': compliance_result.status.value,
                    'violations': compliance_result.violations,
                    'recommendations': compliance_result.recommendations,
                    'sanctions_match': compliance_result.sanctions_match,
                    'pep_match': compliance_result.pep_match,
                    'aml_flags': compliance_result.aml_flags
                },
                'processing_time_ms': (datetime.now() - start_time).total_seconds() * 1000,
                'cost_estimate': self._calculate_cost(risk_assessment, compliance_result)
            }
            
            # Store result
            await self._store_result(result)
            
            # Update metrics
            PROCESSING_TIME.observe((datetime.now() - start_time).total_seconds())
            RISK_SCORES.observe(risk_assessment.risk_score)
            
            if compliance_result.sanctions_match:
                SANCTIONS_HITS.inc()
            if compliance_result.pep_match:
                PEP_MATCHES.inc()
            
            self.logger.info("Case processed successfully", 
                           case_id=case_id, 
                           risk_level=risk_assessment.risk_level.value,
                           compliance_status=compliance_result.status.value)
            
            return result
            
        except Exception as e:
            self.logger.error("Failed to process case", case_id=case_id, error=str(e))
            raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    
    async def _assess_risk(self, customer_data: Dict, transaction_data: Dict) -> RiskAssessment:
        """Assess risk using hybrid ML + rule-based approach"""
        try:
            # Extract features for ML model
            features = self._extract_risk_features(customer_data, transaction_data)
            
            # Use local ML model for initial scoring (70% of cases)
            if self.risk_classifier and len(features) > 0:
                try:
                    features_scaled = self.scaler.transform([features])
                    ml_risk_score = self.risk_classifier.predict_proba(features_scaled)[0][1] * 100
                    ml_confidence = max(self.risk_classifier.predict_proba(features_scaled)[0])
                    
                    # Use ML result if confidence is high
                    if ml_confidence > 0.7:
                        risk_level = self._score_to_risk_level(ml_risk_score)
                        risk_factors = self._identify_risk_factors(customer_data, transaction_data)
                        
                        return RiskAssessment(
                            risk_level=risk_level,
                            risk_score=ml_risk_score,
                            risk_factors=risk_factors,
                            ml_confidence=ml_confidence,
                            reasoning=f"ML-based assessment with {ml_confidence:.2f} confidence"
                        )
                except Exception as e:
                    self.logger.warning("ML model failed, falling back to LLM", error=str(e))
            
            # Fallback to LLM for complex cases (30% of cases)
            risk_factors = self._identify_risk_factors(customer_data, transaction_data)
            
            llm_input = {
                "customer_data": json.dumps(customer_data),
                "transaction_data": json.dumps(transaction_data),
                "risk_factors": json.dumps(risk_factors)
            }
            
            llm_result = await self.risk_chain.arun(**llm_input)
            
            try:
                parsed_result = json.loads(llm_result)
                risk_level = RiskLevel(parsed_result.get('risk_level', 'medium').lower())
                risk_score = float(parsed_result.get('risk_score', 50))
                reasoning = parsed_result.get('reasoning', 'LLM-based assessment')
                
                return RiskAssessment(
                    risk_level=risk_level,
                    risk_score=risk_score,
                    risk_factors=risk_factors,
                    ml_confidence=0.0,
                    reasoning=reasoning
                )
                
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                self.logger.warning("Failed to parse LLM result, using fallback", error=str(e))
                return RiskAssessment(
                    risk_level=RiskLevel.MEDIUM,
                    risk_score=50.0,
                    risk_factors=risk_factors,
                    ml_confidence=0.0,
                    reasoning="Fallback assessment due to parsing error"
                )
                
        except Exception as e:
            self.logger.error("Risk assessment failed", error=str(e))
            return RiskAssessment(
                risk_level=RiskLevel.HIGH,
                risk_score=75.0,
                risk_factors=["Assessment error"],
                ml_confidence=0.0,
                reasoning=f"Error-based high risk: {str(e)}"
            )
    
    async def _check_compliance(self, customer_data: Dict, transaction_data: Dict) -> ComplianceResult:
        """Perform compliance checks"""
        try:
            violations = []
            recommendations = []
            aml_flags = []
            
            # Sanctions screening
            sanctions_match = await self._screen_sanctions(customer_data)
            
            # PEP screening
            pep_match = await self._screen_pep(customer_data)
            
            # AML checks
            aml_flags = self._check_aml_rules(customer_data, transaction_data)
            
            # Determine overall compliance status
            if sanctions_match or pep_match:
                status = ComplianceStatus.NON_COMPLIANT
                if sanctions_match:
                    violations.append("Sanctions list match")
                    recommendations.append("Immediate escalation required")
                if pep_match:
                    violations.append("PEP match detected")
                    recommendations.append("Enhanced due diligence required")
            elif aml_flags:
                status = ComplianceStatus.REQUIRES_REVIEW
                violations.extend(aml_flags)
                recommendations.append("Manual review recommended")
            else:
                status = ComplianceStatus.COMPLIANT
                recommendations.append("Standard monitoring")
            
            return ComplianceResult(
                status=status,
                violations=violations,
                recommendations=recommendations,
                sanctions_match=sanctions_match,
                pep_match=pep_match,
                aml_flags=aml_flags
            )
            
        except Exception as e:
            self.logger.error("Compliance check failed", error=str(e))
            return ComplianceResult(
                status=ComplianceStatus.REQUIRES_REVIEW,
                violations=[f"Compliance check error: {str(e)}"],
                recommendations=["Manual review required due to system error"],
                sanctions_match=False,
                pep_match=False,
                aml_flags=[]
            )
    
    async def _screen_sanctions(self, customer_data: Dict) -> bool:
        """Screen against sanctions lists"""
        try:
            name = customer_data.get('name', '').strip()
            if not name:
                return False
            
            # Check production sanctions database
            return await self.sanctions_db.check_sanctions(name)
            
        except Exception as e:
            self.logger.error("Sanctions screening failed", error=str(e))
            return False
    
    async def _screen_pep(self, customer_data: Dict) -> bool:
        """Screen against PEP lists"""
        try:
            name = customer_data.get('name', '').strip()
            if not name:
                return False
            
            # Check production PEP database
            return await self.pep_db.check_pep(name)
            
        except Exception as e:
            self.logger.error("PEP screening failed", error=str(e))
            return False
    
    def _extract_risk_features(self, customer_data: Dict, transaction_data: Dict) -> List[float]:
        """Extract numerical features for ML model"""
        features = []
        
        try:
            # Customer features
            features.append(customer_data.get('age', 0))
            features.append(1 if customer_data.get('is_pep', False) else 0)
            features.append(len(customer_data.get('addresses', [])))
            
            # Transaction features
            features.append(transaction_data.get('amount', 0))
            features.append(len(transaction_data.get('transactions', [])))
            features.append(transaction_data.get('frequency', 0))
            
            # Geographic risk
            country = customer_data.get('country', '').upper()
            high_risk_countries = ['AF', 'IR', 'KP', 'SY']  # Example high-risk countries
            features.append(1 if country in high_risk_countries else 0)
            
        except Exception as e:
            self.logger.warning("Feature extraction failed", error=str(e))
            features = [0] * 7  # Default features
        
        return features
    
    def _identify_risk_factors(self, customer_data: Dict, transaction_data: Dict) -> List[str]:
        """Identify specific risk factors"""
        risk_factors = []
        
        # High-value transactions
        amount = transaction_data.get('amount', 0)
        if amount > 10000:
            risk_factors.append("High-value transaction")
        
        # High-risk geography
        country = customer_data.get('country', '').upper()
        high_risk_countries = ['AF', 'IR', 'KP', 'SY']
        if country in high_risk_countries:
            risk_factors.append("High-risk jurisdiction")
        
        # Unusual patterns
        frequency = transaction_data.get('frequency', 0)
        if frequency > 10:
            risk_factors.append("High transaction frequency")
        
        # Missing information
        if not customer_data.get('name'):
            risk_factors.append("Missing customer name")
        
        return risk_factors
    
    def _check_aml_rules(self, customer_data: Dict, transaction_data: Dict) -> List[str]:
        """Apply AML rules"""
        flags = []
        
        # Large cash transactions
        amount = transaction_data.get('amount', 0)
        if amount > 10000:
            flags.append("Large transaction requiring reporting")
        
        # Structuring detection
        transactions = transaction_data.get('transactions', [])
        if len(transactions) > 5:
            amounts = [t.get('amount', 0) for t in transactions]
            if all(9000 <= amt <= 9999 for amt in amounts):
                flags.append("Potential structuring detected")
        
        return flags
    
    def _score_to_risk_level(self, score: float) -> RiskLevel:
        """Convert numerical score to risk level"""
        if score >= 80:
            return RiskLevel.CRITICAL
        elif score >= 60:
            return RiskLevel.HIGH
        elif score >= 40:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _calculate_cost(self, risk_assessment: RiskAssessment, compliance_result: ComplianceResult) -> float:
        """Calculate processing cost"""
        base_cost = 0.05  # Base processing cost
        
        # Add cost for LLM usage
        if risk_assessment.ml_confidence == 0.0:  # Used LLM
            base_cost += 0.15
        
        # Add cost for complex compliance checks
        if compliance_result.sanctions_match or compliance_result.pep_match:
            base_cost += 0.05
        
        return round(base_cost, 3)
    
    async def _store_result(self, result: Dict[str, Any]):
        """Store processing result"""
        try:
            # Store in PostgreSQL
            with self.pg_conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO intelligence_compliance_results 
                    (case_id, result_data, created_at)
                    VALUES (%s, %s, %s)
                """, (
                    result['case_id'],
                    json.dumps(result),
                    datetime.now()
                ))
            self.pg_conn.commit()
            
            # Cache in Redis
            cache_key = f"intelligence_result:{result['case_id']}"
            self.redis_client.setex(cache_key, 3600, json.dumps(result))
            
        except Exception as e:
            self.logger.error("Failed to store result", error=str(e))

# FastAPI application
app = FastAPI(title="Intelligence & Compliance Agent", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent instance
agent = None

@app.on_event("startup")
async def startup_event():
    """Initialize agent on startup"""
    global agent
    agent = IntelligenceComplianceAgent()
    
    # Start Prometheus metrics server
    start_http_server(8001)
    logger.info("Intelligence & Compliance Agent started")

@app.post("/process")
async def process_case(case_data: Dict[str, Any]):
    """Process a compliance case"""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    return await agent.process_case(case_data)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/metrics")
async def get_metrics():
    """Get processing metrics"""
    return {
        "cases_processed": CASES_PROCESSED._value._value,
        "avg_processing_time": PROCESSING_TIME._sum._value / max(PROCESSING_TIME._count._value, 1),
        "sanctions_hits": SANCTIONS_HITS._value._value,
        "pep_matches": PEP_MATCHES._value._value
    }

if __name__ == "__main__":
    uvicorn.run(
        "intelligence_compliance_service_simple:app",
        host="0.0.0.0",
        port=8002,
        reload=False,
        log_config=None
    )
