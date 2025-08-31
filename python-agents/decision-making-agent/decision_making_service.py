"""
Decision Making Agent - LangGraph Framework
Production-grade stateful autonomous decision-making service for KYC processes
Implements complex decision workflows with audit trails and explainable AI
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

# Web Framework
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

# LangGraph Framework
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

# AI/ML Libraries
import openai
from langchain.llms import OpenAI
from transformers import pipeline
import torch

# Data Processing and ML
import pandas as pd
import numpy as np
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.ensemble import RandomForestClassifier
import xgboost as xgb
import networkx as nx

# Database and Messaging
import psycopg2
from pymongo import MongoClient
import redis
from kafka import KafkaProducer, KafkaConsumer

# Workflow Management
from celery import Celery

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
decision_requests = Counter('decision_requests_total', 'Total decision requests')
decision_duration = Histogram('decision_duration_seconds', 'Decision processing duration')
decision_outcomes = Counter('decision_outcomes_total', 'Decision outcomes', ['outcome'])
workflow_states = Gauge('workflow_active_states', 'Active workflow states')

# Decision Enums
class DecisionType(str, Enum):
    KYC_APPROVAL = "kyc_approval"
    RISK_ESCALATION = "risk_escalation"
    COMPLIANCE_ACTION = "compliance_action"
    DOCUMENT_REQUEST = "document_request"
    ACCOUNT_RESTRICTION = "account_restriction"
    MANUAL_REVIEW = "manual_review"

class DecisionStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ESCALATED = "escalated"
    FAILED = "failed"

class ConfidenceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"

# State Management for LangGraph
@dataclass
class DecisionState:
    """State object for decision-making workflow"""
    customer_id: str
    decision_id: str
    input_data: Dict[str, Any]
    analysis_results: Dict[str, Any]
    decision_history: List[Dict[str, Any]]
    current_step: str
    confidence_scores: Dict[str, float]
    risk_factors: List[Dict[str, Any]]
    compliance_status: str
    final_decision: Optional[str]
    reasoning: List[str]
    audit_trail: List[Dict[str, Any]]
    escalation_required: bool
    next_actions: List[str]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary"""
        return {
            "customer_id": self.customer_id,
            "decision_id": self.decision_id,
            "input_data": self.input_data,
            "analysis_results": self.analysis_results,
            "decision_history": self.decision_history,
            "current_step": self.current_step,
            "confidence_scores": self.confidence_scores,
            "risk_factors": self.risk_factors,
            "compliance_status": self.compliance_status,
            "final_decision": self.final_decision,
            "reasoning": self.reasoning,
            "audit_trail": self.audit_trail,
            "escalation_required": self.escalation_required,
            "next_actions": self.next_actions,
            "timestamp": self.timestamp.isoformat()
        }

# Data Models
class DecisionRequest(BaseModel):
    """Decision request model"""
    customer_id: str = Field(..., description="Customer identifier")
    decision_type: DecisionType = Field(..., description="Type of decision required")
    input_data: Dict[str, Any] = Field(..., description="Input data for decision")
    analysis_results: Dict[str, Any] = Field(default={}, description="Previous analysis results")
    priority: str = Field(default="normal", description="Decision priority")
    deadline: Optional[datetime] = Field(None, description="Decision deadline")
    context: Dict[str, Any] = Field(default={}, description="Additional context")

class DecisionResponse(BaseModel):
    """Decision response model"""
    decision_id: str
    customer_id: str
    decision_type: DecisionType
    final_decision: str
    confidence_level: ConfidenceLevel
    reasoning: List[str]
    risk_assessment: Dict[str, Any]
    compliance_status: str
    next_actions: List[str]
    audit_trail: List[Dict[str, Any]]
    processing_time: float
    escalation_required: bool
    status: DecisionStatus

# Decision Making Tools
class RiskDecisionEngine:
    """Risk-based decision engine using ML models"""
    
    def __init__(self):
        self.decision_tree = DecisionTreeClassifier(random_state=42)
        self.random_forest = RandomForestClassifier(n_estimators=100, random_state=42)
        self.xgb_model = xgb.XGBClassifier(random_state=42)
        self.is_trained = False
    
    def train_models(self, training_data: pd.DataFrame, labels: pd.Series):
        """Train decision models"""
        try:
            self.decision_tree.fit(training_data, labels)
            self.random_forest.fit(training_data, labels)
            self.xgb_model.fit(training_data, labels)
            self.is_trained = True
            logger.info("Decision models trained successfully")
        except Exception as e:
            logger.error("Model training failed", error=str(e))
            raise
    
    def make_risk_decision(self, features: np.ndarray) -> Dict[str, Any]:
        """Make risk-based decision using ensemble of models"""
        if not self.is_trained:
            # Use rule-based fallback
            return self._rule_based_decision(features)
        
        try:
            # Get predictions from all models
            dt_pred = self.decision_tree.predict_proba(features.reshape(1, -1))[0]
            rf_pred = self.random_forest.predict_proba(features.reshape(1, -1))[0]
            xgb_pred = self.xgb_model.predict_proba(features.reshape(1, -1))[0]
            
            # Ensemble prediction (weighted average)
            ensemble_pred = (dt_pred * 0.2 + rf_pred * 0.4 + xgb_pred * 0.4)
            
            # Get decision and confidence
            decision_class = np.argmax(ensemble_pred)
            confidence = np.max(ensemble_pred)
            
            # Map to decision
            decision_map = {0: "approve", 1: "review", 2: "reject"}
            decision = decision_map.get(decision_class, "review")
            
            return {
                "decision": decision,
                "confidence": float(confidence),
                "model_scores": {
                    "decision_tree": dt_pred.tolist(),
                    "random_forest": rf_pred.tolist(),
                    "xgboost": xgb_pred.tolist(),
                    "ensemble": ensemble_pred.tolist()
                }
            }
        except Exception as e:
            logger.error("ML decision failed, using fallback", error=str(e))
            return self._rule_based_decision(features)
    
    def _rule_based_decision(self, features: np.ndarray) -> Dict[str, Any]:
        """Rule-based decision fallback"""
        # Simple rule-based logic
        risk_score = np.mean(features)
        
        if risk_score < 0.3:
            decision = "approve"
            confidence = 0.8
        elif risk_score < 0.7:
            decision = "review"
            confidence = 0.6
        else:
            decision = "reject"
            confidence = 0.9
        
        return {
            "decision": decision,
            "confidence": confidence,
            "model_scores": {"rule_based": risk_score}
        }
    
    def get_decision_explanation(self, features: np.ndarray) -> List[str]:
        """Get explanation for decision"""
        explanations = []
        
        if self.is_trained:
            # Get feature importance from random forest
            feature_names = [f"feature_{i}" for i in range(len(features))]
            importances = self.random_forest.feature_importances_
            
            # Get top contributing features
            top_features = np.argsort(importances)[-3:][::-1]
            
            for idx in top_features:
                explanations.append(f"Feature {idx} (importance: {importances[idx]:.3f}) contributed to decision")
        
        return explanations

class ComplianceDecisionEngine:
    """Compliance-focused decision engine"""
    
    def __init__(self):
        self.compliance_rules = self._load_compliance_rules()
    
    def _load_compliance_rules(self) -> Dict[str, Any]:
        """Load compliance decision rules"""
        return {
            "aml_rules": {
                "high_risk_country": {"action": "escalate", "severity": "high"},
                "pep_match": {"action": "manual_review", "severity": "medium"},
                "sanctions_match": {"action": "reject", "severity": "critical"},
                "suspicious_transactions": {"action": "investigate", "severity": "high"}
            },
            "gdpr_rules": {
                "missing_consent": {"action": "request_consent", "severity": "medium"},
                "data_retention_exceeded": {"action": "data_deletion", "severity": "high"},
                "access_request": {"action": "provide_data", "severity": "low"}
            },
            "kyc_rules": {
                "insufficient_documents": {"action": "request_documents", "severity": "medium"},
                "identity_verification_failed": {"action": "reject", "severity": "high"},
                "address_verification_failed": {"action": "request_proof", "severity": "medium"}
            }
        }
    
    def make_compliance_decision(self, compliance_status: Dict[str, Any]) -> Dict[str, Any]:
        """Make compliance-based decision"""
        decisions = []
        max_severity = "low"
        
        for rule_type, status in compliance_status.items():
            if status.get("violations"):
                for violation in status["violations"]:
                    rule_info = self._get_rule_info(rule_type, violation)
                    if rule_info:
                        decisions.append({
                            "violation": violation,
                            "action": rule_info["action"],
                            "severity": rule_info["severity"],
                            "rule_type": rule_type
                        })
                        
                        # Update max severity
                        if self._severity_level(rule_info["severity"]) > self._severity_level(max_severity):
                            max_severity = rule_info["severity"]
        
        # Determine final action
        final_action = self._determine_final_action(decisions, max_severity)
        
        return {
            "final_action": final_action,
            "severity": max_severity,
            "decisions": decisions,
            "compliance_score": self._calculate_compliance_score(compliance_status)
        }
    
    def _get_rule_info(self, rule_type: str, violation: str) -> Optional[Dict[str, Any]]:
        """Get rule information for violation"""
        rules = self.compliance_rules.get(f"{rule_type}_rules", {})
        
        # Find matching rule (simplified matching)
        for rule_key, rule_info in rules.items():
            if rule_key.lower() in violation.lower():
                return rule_info
        
        return None
    
    def _severity_level(self, severity: str) -> int:
        """Convert severity to numeric level"""
        levels = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        return levels.get(severity, 1)
    
    def _determine_final_action(self, decisions: List[Dict[str, Any]], max_severity: str) -> str:
        """Determine final action based on all decisions"""
        if max_severity == "critical":
            return "reject"
        elif max_severity == "high":
            return "escalate"
        elif max_severity == "medium":
            return "manual_review"
        else:
            return "approve"
    
    def _calculate_compliance_score(self, compliance_status: Dict[str, Any]) -> float:
        """Calculate overall compliance score"""
        total_checks = 0
        passed_checks = 0
        
        for status in compliance_status.values():
            total_checks += 1
            if status.get("status") == "compliant":
                passed_checks += 1
        
        return passed_checks / total_checks if total_checks > 0 else 0.0

# LangGraph Workflow Definition
class DecisionMakingWorkflow:
    """LangGraph-based decision-making workflow"""
    
    def __init__(self):
        self.risk_engine = RiskDecisionEngine()
        self.compliance_engine = ComplianceDecisionEngine()
        self.llm = ChatOpenAI(model="gpt-4", temperature=0.1)
        self.memory = MemorySaver()
        self.workflow = self._create_workflow()
    
    def _create_workflow(self) -> StateGraph:
        """Create LangGraph workflow"""
        workflow = StateGraph(DecisionState)
        
        # Add nodes
        workflow.add_node("initialize", self._initialize_decision)
        workflow.add_node("risk_assessment", self._assess_risk)
        workflow.add_node("compliance_check", self._check_compliance)
        workflow.add_node("ml_decision", self._make_ml_decision)
        workflow.add_node("human_review", self._human_review_required)
        workflow.add_node("make_decision", self._make_final_decision)
        workflow.add_node("audit_logging", self._log_audit_trail)
        
        # Add edges
        workflow.add_edge("initialize", "risk_assessment")
        workflow.add_edge("risk_assessment", "compliance_check")
        workflow.add_edge("compliance_check", "ml_decision")
        
        # Conditional edges
        workflow.add_conditional_edges(
            "ml_decision",
            self._should_escalate,
            {
                "escalate": "human_review",
                "decide": "make_decision"
            }
        )
        
        workflow.add_edge("human_review", "make_decision")
        workflow.add_edge("make_decision", "audit_logging")
        workflow.add_edge("audit_logging", END)
        
        # Set entry point
        workflow.set_entry_point("initialize")
        
        return workflow.compile(checkpointer=self.memory)
    
    async def _initialize_decision(self, state: DecisionState) -> DecisionState:
        """Initialize decision-making process"""
        state.current_step = "initialization"
        state.timestamp = datetime.now()
        state.audit_trail.append({
            "step": "initialize",
            "timestamp": datetime.now().isoformat(),
            "action": "Decision process started",
            "data": {"customer_id": state.customer_id}
        })
        
        logger.info("Decision process initialized", 
                   customer_id=state.customer_id, 
                   decision_id=state.decision_id)
        
        return state
    
    async def _assess_risk(self, state: DecisionState) -> DecisionState:
        """Assess risk factors"""
        state.current_step = "risk_assessment"
        
        try:
            # Extract risk features
            risk_features = self._extract_risk_features(state.input_data, state.analysis_results)
            
            # Make risk decision
            risk_decision = self.risk_engine.make_risk_decision(risk_features)
            
            # Update state
            state.confidence_scores["risk"] = risk_decision["confidence"]
            state.risk_factors = self._identify_risk_factors(state.input_data, state.analysis_results)
            
            # Add to audit trail
            state.audit_trail.append({
                "step": "risk_assessment",
                "timestamp": datetime.now().isoformat(),
                "action": "Risk assessment completed",
                "data": {
                    "risk_decision": risk_decision["decision"],
                    "confidence": risk_decision["confidence"],
                    "risk_factors_count": len(state.risk_factors)
                }
            })
            
            logger.info("Risk assessment completed", 
                       customer_id=state.customer_id,
                       risk_decision=risk_decision["decision"],
                       confidence=risk_decision["confidence"])
            
        except Exception as e:
            logger.error("Risk assessment failed", 
                        customer_id=state.customer_id, 
                        error=str(e))
            state.confidence_scores["risk"] = 0.0
        
        return state
    
    async def _check_compliance(self, state: DecisionState) -> DecisionState:
        """Check compliance requirements"""
        state.current_step = "compliance_check"
        
        try:
            # Get compliance status from analysis results
            compliance_status = state.analysis_results.get("compliance_results", {})
            
            # Make compliance decision
            compliance_decision = self.compliance_engine.make_compliance_decision(compliance_status)
            
            # Update state
            state.compliance_status = compliance_decision["final_action"]
            state.confidence_scores["compliance"] = compliance_decision["compliance_score"]
            
            # Add to audit trail
            state.audit_trail.append({
                "step": "compliance_check",
                "timestamp": datetime.now().isoformat(),
                "action": "Compliance check completed",
                "data": {
                    "compliance_action": compliance_decision["final_action"],
                    "severity": compliance_decision["severity"],
                    "compliance_score": compliance_decision["compliance_score"]
                }
            })
            
            logger.info("Compliance check completed", 
                       customer_id=state.customer_id,
                       compliance_action=compliance_decision["final_action"])
            
        except Exception as e:
            logger.error("Compliance check failed", 
                        customer_id=state.customer_id, 
                        error=str(e))
            state.compliance_status = "unknown"
        
        return state
    
    async def _make_ml_decision(self, state: DecisionState) -> DecisionState:
        """Make ML-based decision"""
        state.current_step = "ml_decision"
        
        try:
            # Combine all available information
            decision_context = {
                "risk_factors": state.risk_factors,
                "compliance_status": state.compliance_status,
                "confidence_scores": state.confidence_scores,
                "analysis_results": state.analysis_results
            }
            
            # Use LLM for complex decision reasoning
            decision_prompt = self._create_decision_prompt(decision_context)
            
            response = await self.llm.ainvoke([HumanMessage(content=decision_prompt)])
            
            # Parse LLM response
            decision_analysis = self._parse_llm_decision(response.content)
            
            # Update state
            state.reasoning.extend(decision_analysis.get("reasoning", []))
            state.confidence_scores["llm"] = decision_analysis.get("confidence", 0.5)
            
            # Determine if escalation is needed
            state.escalation_required = self._requires_escalation(state)
            
            # Add to audit trail
            state.audit_trail.append({
                "step": "ml_decision",
                "timestamp": datetime.now().isoformat(),
                "action": "ML decision analysis completed",
                "data": {
                    "llm_confidence": decision_analysis.get("confidence"),
                    "escalation_required": state.escalation_required,
                    "reasoning_points": len(state.reasoning)
                }
            })
            
            logger.info("ML decision completed", 
                       customer_id=state.customer_id,
                       escalation_required=state.escalation_required)
            
        except Exception as e:
            logger.error("ML decision failed", 
                        customer_id=state.customer_id, 
                        error=str(e))
            state.escalation_required = True
        
        return state
    
    async def _human_review_required(self, state: DecisionState) -> DecisionState:
        """Handle human review requirement"""
        state.current_step = "human_review"
        
        # Add human review request to next actions
        state.next_actions.append("human_review_required")
        
        # Add to audit trail
        state.audit_trail.append({
            "step": "human_review",
            "timestamp": datetime.now().isoformat(),
            "action": "Human review requested",
            "data": {
                "reason": "Complex case requiring human judgment",
                "confidence_scores": state.confidence_scores
            }
        })
        
        logger.info("Human review required", 
                   customer_id=state.customer_id,
                   reason="Complex case")
        
        return state
    
    async def _make_final_decision(self, state: DecisionState) -> DecisionState:
        """Make final decision"""
        state.current_step = "final_decision"
        
        try:
            # Synthesize all information for final decision
            final_decision = self._synthesize_final_decision(state)
            
            state.final_decision = final_decision["decision"]
            state.reasoning.extend(final_decision["reasoning"])
            state.next_actions.extend(final_decision["next_actions"])
            
            # Add to audit trail
            state.audit_trail.append({
                "step": "final_decision",
                "timestamp": datetime.now().isoformat(),
                "action": "Final decision made",
                "data": {
                    "decision": state.final_decision,
                    "confidence_scores": state.confidence_scores,
                    "next_actions": state.next_actions
                }
            })
            
            logger.info("Final decision made", 
                       customer_id=state.customer_id,
                       decision=state.final_decision)
            
        except Exception as e:
            logger.error("Final decision failed", 
                        customer_id=state.customer_id, 
                        error=str(e))
            state.final_decision = "escalate"
            state.next_actions.append("error_escalation")
        
        return state
    
    async def _log_audit_trail(self, state: DecisionState) -> DecisionState:
        """Log complete audit trail"""
        state.current_step = "completed"
        
        # Final audit entry
        state.audit_trail.append({
            "step": "audit_logging",
            "timestamp": datetime.now().isoformat(),
            "action": "Decision process completed",
            "data": {
                "total_steps": len(state.audit_trail),
                "final_decision": state.final_decision,
                "processing_duration": (datetime.now() - state.timestamp).total_seconds()
            }
        })
        
        logger.info("Decision process completed", 
                   customer_id=state.customer_id,
                   decision_id=state.decision_id,
                   final_decision=state.final_decision)
        
        return state
    
    def _should_escalate(self, state: DecisionState) -> str:
        """Determine if escalation is needed"""
        return "escalate" if state.escalation_required else "decide"
    
    def _extract_risk_features(self, input_data: Dict[str, Any], analysis_results: Dict[str, Any]) -> np.ndarray:
        """Extract numerical features for risk assessment"""
        features = []
        
        # Risk score from analysis
        risk_score = analysis_results.get("risk_assessment", {}).get("risk_score", 0.5)
        features.append(risk_score)
        
        # Compliance score
        compliance_score = 1.0 if analysis_results.get("compliance_status") == "compliant" else 0.0
        features.append(compliance_score)
        
        # Document completeness
        doc_count = len(input_data.get("documents", []))
        features.append(min(doc_count / 5.0, 1.0))
        
        # Transaction volume
        transaction_count = len(input_data.get("transaction_history", []))
        features.append(min(transaction_count / 100.0, 1.0))
        
        # Geographic risk
        country = input_data.get("personal_info", {}).get("country", "US")
        geo_risk = 0.1 if country == "US" else 0.5
        features.append(geo_risk)
        
        return np.array(features)
    
    def _identify_risk_factors(self, input_data: Dict[str, Any], analysis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify specific risk factors"""
        risk_factors = []
        
        # High risk score
        risk_score = analysis_results.get("risk_assessment", {}).get("risk_score", 0.0)
        if risk_score > 0.7:
            risk_factors.append({
                "factor": "high_risk_score",
                "value": risk_score,
                "severity": "high",
                "description": f"Customer has high risk score: {risk_score:.2f}"
            })
        
        # Compliance violations
        violations = analysis_results.get("compliance_results", {}).get("violations", [])
        if violations:
            risk_factors.append({
                "factor": "compliance_violations",
                "value": len(violations),
                "severity": "medium",
                "description": f"Compliance violations found: {', '.join(violations)}"
            })
        
        return risk_factors
    
    def _create_decision_prompt(self, context: Dict[str, Any]) -> str:
        """Create prompt for LLM decision reasoning"""
        return f"""
        You are an expert KYC decision-making agent. Analyze the following information and provide a reasoned decision.
        
        Risk Factors: {context['risk_factors']}
        Compliance Status: {context['compliance_status']}
        Confidence Scores: {context['confidence_scores']}
        
        Based on this information, provide:
        1. A clear decision (approve/reject/review)
        2. Confidence level (0.0-1.0)
        3. Key reasoning points
        4. Recommended next actions
        
        Format your response as JSON with keys: decision, confidence, reasoning, next_actions
        """
    
    def _parse_llm_decision(self, response: str) -> Dict[str, Any]:
        """Parse LLM decision response"""
        try:
            # Try to parse as JSON
            return json.loads(response)
        except:
            # Fallback parsing
            return {
                "decision": "review",
                "confidence": 0.5,
                "reasoning": ["LLM response parsing failed"],
                "next_actions": ["manual_review"]
            }
    
    def _requires_escalation(self, state: DecisionState) -> bool:
        """Determine if escalation is required"""
        # Low confidence scores
        avg_confidence = np.mean(list(state.confidence_scores.values()))
        if avg_confidence < 0.6:
            return True
        
        # High risk factors
        if len(state.risk_factors) > 3:
            return True
        
        # Compliance issues
        if state.compliance_status in ["reject", "escalate"]:
            return True
        
        return False
    
    def _synthesize_final_decision(self, state: DecisionState) -> Dict[str, Any]:
        """Synthesize final decision from all analysis"""
        # Simple decision logic (would be more complex in production)
        if state.escalation_required:
            decision = "escalate"
            next_actions = ["human_review", "additional_documentation"]
        elif state.compliance_status == "reject":
            decision = "reject"
            next_actions = ["notify_customer", "close_application"]
        elif state.compliance_status == "approve" and np.mean(list(state.confidence_scores.values())) > 0.8:
            decision = "approve"
            next_actions = ["activate_account", "send_welcome"]
        else:
            decision = "review"
            next_actions = ["additional_verification", "risk_monitoring"]
        
        reasoning = [
            f"Decision based on compliance status: {state.compliance_status}",
            f"Average confidence: {np.mean(list(state.confidence_scores.values())):.2f}",
            f"Risk factors identified: {len(state.risk_factors)}"
        ]
        
        return {
            "decision": decision,
            "reasoning": reasoning,
            "next_actions": next_actions
        }

# Main Service Class
class DecisionMakingService:
    """Main Decision Making Service using LangGraph"""
    
    def __init__(self):
        self.app = FastAPI(title="Decision Making Agent", version="1.0.0")
        self.setup_middleware()
        self.setup_routes()
        
        # Initialize components
        self.kafka_producer = None
        self.kafka_consumer = None
        self.redis_client = None
        self.db_connection = None
        self.mongo_client = None
        
        # Initialize workflow
        self.workflow_engine = DecisionMakingWorkflow()
        
        # Setup components
        self._setup_database_connections()
        self._setup_messaging()
        
        # Start monitoring
        start_http_server(8003)
        
        logger.info("Decision Making Agent initialized successfully")
    
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
                "service": "decision-making-agent",
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0"
            }
        
        @self.app.post("/api/v1/decision/make", response_model=DecisionResponse)
        async def make_decision(request: DecisionRequest, background_tasks: BackgroundTasks):
            """Main decision-making endpoint"""
            decision_requests.inc()
            
            with decision_duration.time():
                try:
                    # Generate decision ID
                    decision_id = self._generate_decision_id(request.customer_id)
                    
                    # Create initial state
                    initial_state = DecisionState(
                        customer_id=request.customer_id,
                        decision_id=decision_id,
                        input_data=request.input_data,
                        analysis_results=request.analysis_results,
                        decision_history=[],
                        current_step="pending",
                        confidence_scores={},
                        risk_factors=[],
                        compliance_status="unknown",
                        final_decision=None,
                        reasoning=[],
                        audit_trail=[],
                        escalation_required=False,
                        next_actions=[],
                        timestamp=datetime.now()
                    )
                    
                    # Execute workflow
                    config = RunnableConfig(
                        configurable={"thread_id": decision_id}
                    )
                    
                    final_state = await self.workflow_engine.workflow.ainvoke(
                        initial_state, 
                        config=config
                    )
                    
                    # Create response
                    response = DecisionResponse(
                        decision_id=decision_id,
                        customer_id=request.customer_id,
                        decision_type=request.decision_type,
                        final_decision=final_state.final_decision or "pending",
                        confidence_level=self._determine_confidence_level(final_state.confidence_scores),
                        reasoning=final_state.reasoning,
                        risk_assessment={
                            "risk_factors": final_state.risk_factors,
                            "confidence_scores": final_state.confidence_scores
                        },
                        compliance_status=final_state.compliance_status,
                        next_actions=final_state.next_actions,
                        audit_trail=final_state.audit_trail,
                        processing_time=(datetime.now() - final_state.timestamp).total_seconds(),
                        escalation_required=final_state.escalation_required,
                        status=DecisionStatus.COMPLETED
                    )
                    
                    # Update metrics
                    decision_outcomes.labels(outcome=final_state.final_decision or "unknown").inc()
                    
                    # Send results to other agents
                    background_tasks.add_task(
                        self._send_decision_results,
                        decision_id,
                        final_state.to_dict()
                    )
                    
                    # Store results
                    background_tasks.add_task(
                        self._store_decision_results,
                        decision_id,
                        final_state.to_dict()
                    )
                    
                    return response
                    
                except Exception as e:
                    logger.error("Decision making failed", 
                               customer_id=request.customer_id, 
                               error=str(e))
                    raise HTTPException(status_code=500, detail=f"Decision making failed: {str(e)}")
        
        @self.app.get("/api/v1/decision/{decision_id}")
        async def get_decision_result(decision_id: str):
            """Get decision result by ID"""
            try:
                result = await self._get_decision_from_db(decision_id)
                if not result:
                    raise HTTPException(status_code=404, detail="Decision not found")
                return result
            except Exception as e:
                logger.error("Failed to retrieve decision", decision_id=decision_id, error=str(e))
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/workflow/status")
        async def get_workflow_status():
            """Get workflow status"""
            return {
                "workflow_engine": "active",
                "total_decisions": decision_requests._value.get(),
                "active_workflows": workflow_states._value.get(),
                "last_activity": datetime.now().isoformat()
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
    
    def _generate_decision_id(self, customer_id: str) -> str:
        """Generate unique decision ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hash_input = f"{customer_id}_{timestamp}_{uuid.uuid4().hex[:8]}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    def _determine_confidence_level(self, confidence_scores: Dict[str, float]) -> ConfidenceLevel:
        """Determine overall confidence level"""
        if not confidence_scores:
            return ConfidenceLevel.LOW
        
        avg_confidence = np.mean(list(confidence_scores.values()))
        
        if avg_confidence >= 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif avg_confidence >= 0.7:
            return ConfidenceLevel.HIGH
        elif avg_confidence >= 0.5:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW
    
    async def _send_decision_results(self, decision_id: str, results: Dict[str, Any]):
        """Send decision results to other agents via Kafka"""
        try:
            message = {
                "decision_id": decision_id,
                "agent": "decision-making-agent",
                "timestamp": datetime.now().isoformat(),
                "results": results
            }
            
            self.kafka_producer.send('decision-results', message)
            logger.info("Decision results sent to Kafka", decision_id=decision_id)
        except Exception as e:
            logger.error("Failed to send decision results", decision_id=decision_id, error=str(e))
    
    async def _store_decision_results(self, decision_id: str, results: Dict[str, Any]):
        """Store decision results in database"""
        try:
            # Store in PostgreSQL
            cursor = self.db_connection.cursor()
            cursor.execute("""
                INSERT INTO decision_results (decision_id, customer_id, results, created_at)
                VALUES (%s, %s, %s, %s)
            """, (decision_id, results.get('customer_id'), json.dumps(results), datetime.now()))
            self.db_connection.commit()
            
            # Cache in Redis
            self.redis_client.setex(f"decision:{decision_id}", 3600, json.dumps(results))
            
            logger.info("Decision results stored", decision_id=decision_id)
        except Exception as e:
            logger.error("Failed to store decision results", decision_id=decision_id, error=str(e))
    
    async def _get_decision_from_db(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve decision results from database"""
        try:
            # Try Redis cache first
            cached_result = self.redis_client.get(f"decision:{decision_id}")
            if cached_result:
                return json.loads(cached_result)
            
            # Query PostgreSQL
            cursor = self.db_connection.cursor()
            cursor.execute("SELECT results FROM decision_results WHERE decision_id = %s", (decision_id,))
            result = cursor.fetchone()
            
            if result:
                return json.loads(result[0])
            
            return None
        except Exception as e:
            logger.error("Failed to retrieve decision", decision_id=decision_id, error=str(e))
            raise

# Initialize service
service = DecisionMakingService()
app = service.app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003, workers=4)
