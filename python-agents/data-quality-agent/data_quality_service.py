"""
Data Quality Agent - Smolagents Framework
Production-grade data validation, quality assurance, and anomaly detection service
Autonomous data quality monitoring and improvement recommendations
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
import hashlib
import re

# Web Framework
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

# Smolagents Framework
from smolagents import CodeAgent, ToolCallingAgent
from smolagents.tools import Tool

# AI/ML Libraries
import openai
from langchain.llms import OpenAI
from transformers import pipeline, AutoTokenizer, AutoModel
import torch
from sentence_transformers import SentenceTransformer

# Data Quality Libraries
import great_expectations as gx
from great_expectations.core.batch import RuntimeBatchRequest
import pandas_profiling as pp
import janitor
from fuzzywuzzy import fuzz, process

# Data Processing and Analysis
import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.api as sm

# Anomaly Detection
from pyod.models.iforest import IForest
from pyod.models.lof import LOF
from pyod.models.ocsvm import OCSVM
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

# Data Validation
import cerberus
import jsonschema
from marshmallow import Schema, fields, ValidationError

# Database and Messaging
import psycopg2
from pymongo import MongoClient
import redis
from kafka import KafkaProducer, KafkaConsumer

# Monitoring
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import structlog

# Visualization
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go

# Text Processing
import nltk
import spacy

# Date/Time Processing
import pendulum
from dateutil import parser as date_parser

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
quality_checks = Counter('data_quality_checks_total', 'Total data quality checks performed')
quality_issues = Counter('data_quality_issues_total', 'Total data quality issues detected', ['issue_type', 'severity'])
anomalies_detected = Counter('anomalies_detected_total', 'Total anomalies detected')
quality_score_gauge = Gauge('data_quality_score', 'Current data quality score')
validation_duration = Histogram('data_validation_duration_seconds', 'Data validation duration')

# Data Quality Enums
class QualityIssueType(str, Enum):
    MISSING_DATA = "missing_data"
    INVALID_FORMAT = "invalid_format"
    DUPLICATE_RECORDS = "duplicate_records"
    INCONSISTENT_DATA = "inconsistent_data"
    OUTLIER_DETECTED = "outlier_detected"
    SCHEMA_VIOLATION = "schema_violation"
    REFERENTIAL_INTEGRITY = "referential_integrity"
    DATA_FRESHNESS = "data_freshness"
    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"

class QualitySeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ValidationStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"

class DataType(str, Enum):
    PERSONAL_INFO = "personal_info"
    FINANCIAL_DATA = "financial_data"
    DOCUMENTS = "documents"
    TRANSACTIONS = "transactions"
    VERIFICATION_DATA = "verification_data"

# Data Models
@dataclass
class QualityIssue:
    """Data quality issue structure"""
    issue_id: str
    issue_type: QualityIssueType
    severity: QualitySeverity
    field_name: str
    description: str
    detected_value: Any
    expected_value: Optional[Any]
    suggestion: str
    confidence: float
    metadata: Dict[str, Any]

@dataclass
class QualityReport:
    """Data quality report structure"""
    report_id: str
    customer_id: str
    data_type: DataType
    overall_score: float
    completeness_score: float
    accuracy_score: float
    consistency_score: float
    validity_score: float
    issues: List[QualityIssue]
    recommendations: List[str]
    anomalies: List[Dict[str, Any]]
    generated_at: datetime

class DataQualityRequest(BaseModel):
    """Data quality check request model"""
    customer_id: str = Field(..., description="Customer identifier")
    data_type: DataType = Field(..., description="Type of data to validate")
    data_payload: Dict[str, Any] = Field(..., description="Data to validate")
    validation_rules: Optional[Dict[str, Any]] = Field(None, description="Custom validation rules")
    check_anomalies: bool = Field(True, description="Whether to check for anomalies")
    generate_profile: bool = Field(False, description="Whether to generate data profile")

class DataQualityResponse(BaseModel):
    """Data quality check response model"""
    check_id: str
    customer_id: str
    data_type: DataType
    overall_score: float
    quality_scores: Dict[str, float]
    validation_status: ValidationStatus
    issues_found: List[Dict[str, Any]]
    anomalies: List[Dict[str, Any]]
    recommendations: List[str]
    processing_time: float
    status: str

# Smolagents Tools for Data Quality
class DataValidationTool(Tool):
    """Tool for comprehensive data validation using Smolagents"""
    name = "data_validation_tool"
    description = "Validate data quality, detect issues, and provide recommendations"
    inputs = {
        "data": {"type": "object", "description": "Data to validate"},
        "validation_rules": {"type": "object", "description": "Optional validation rules", "nullable": True}
    }
    output_type = "object"
    
    def forward(self, data: Dict[str, Any], validation_rules: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute data validation"""
        try:
            validation_results = {
                "completeness": self._check_completeness(data),
                "accuracy": self._check_accuracy(data),
                "consistency": self._check_consistency(data),
                "validity": self._check_validity(data, validation_rules),
                "uniqueness": self._check_uniqueness(data)
            }
            
            # Calculate overall score
            scores = [result["score"] for result in validation_results.values()]
            overall_score = np.mean(scores)
            
            # Collect all issues
            all_issues = []
            for check_type, result in validation_results.items():
                all_issues.extend(result.get("issues", []))
            
            return {
                "overall_score": overall_score,
                "validation_results": validation_results,
                "issues": all_issues,
                "recommendations": self._generate_recommendations(all_issues)
            }
            
        except Exception as e:
            logger.error("Data validation failed", error=str(e))
            raise
    
    def _check_completeness(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Check data completeness"""
        issues = []
        total_fields = 0
        complete_fields = 0
        
        def check_field_completeness(obj, path=""):
            nonlocal total_fields, complete_fields
            
            if isinstance(obj, dict):
                for key, value in obj.items():
                    field_path = f"{path}.{key}" if path else key
                    total_fields += 1
                    
                    if value is None or value == "" or (isinstance(value, list) and len(value) == 0):
                        issues.append({
                            "type": QualityIssueType.MISSING_DATA,
                            "severity": QualitySeverity.MEDIUM,
                            "field": field_path,
                            "description": f"Missing or empty value for {field_path}",
                            "suggestion": f"Provide value for {field_path}"
                        })
                    else:
                        complete_fields += 1
                        if isinstance(value, (dict, list)):
                            check_field_completeness(value, field_path)
            
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    check_field_completeness(item, f"{path}[{i}]")
        
        check_field_completeness(data)
        
        completeness_score = complete_fields / total_fields if total_fields > 0 else 1.0
        
        return {
            "score": completeness_score,
            "issues": issues,
            "metrics": {
                "total_fields": total_fields,
                "complete_fields": complete_fields,
                "missing_fields": total_fields - complete_fields
            }
        }
    
    def _check_accuracy(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Check data accuracy"""
        issues = []
        accuracy_score = 1.0
        
        # Check email format
        email = data.get("personal_info", {}).get("email")
        if email and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            issues.append({
                "type": QualityIssueType.INVALID_FORMAT,
                "severity": QualitySeverity.HIGH,
                "field": "personal_info.email",
                "description": f"Invalid email format: {email}",
                "suggestion": "Provide valid email address"
            })
            accuracy_score -= 0.2
        
        # Check phone number format
        phone = data.get("personal_info", {}).get("phone")
        if phone and not re.match(r'^\+?[\d\s\-\(\)]{10,}$', phone):
            issues.append({
                "type": QualityIssueType.INVALID_FORMAT,
                "severity": QualitySeverity.MEDIUM,
                "field": "personal_info.phone",
                "description": f"Invalid phone format: {phone}",
                "suggestion": "Provide valid phone number"
            })
            accuracy_score -= 0.1
        
        # Check date formats
        dob = data.get("personal_info", {}).get("date_of_birth")
        if dob:
            try:
                parsed_date = date_parser.parse(dob)
                if parsed_date > datetime.now():
                    issues.append({
                        "type": QualityIssueType.INVALID_FORMAT,
                        "severity": QualitySeverity.HIGH,
                        "field": "personal_info.date_of_birth",
                        "description": "Date of birth is in the future",
                        "suggestion": "Provide valid birth date"
                    })
                    accuracy_score -= 0.3
            except:
                issues.append({
                    "type": QualityIssueType.INVALID_FORMAT,
                    "severity": QualitySeverity.HIGH,
                    "field": "personal_info.date_of_birth",
                    "description": f"Invalid date format: {dob}",
                    "suggestion": "Provide date in valid format (YYYY-MM-DD)"
                })
                accuracy_score -= 0.2
        
        # Check numeric ranges
        income = data.get("financial_info", {}).get("annual_income")
        if income is not None:
            try:
                income_val = float(income)
                if income_val < 0:
                    issues.append({
                        "type": QualityIssueType.INVALID_FORMAT,
                        "severity": QualitySeverity.HIGH,
                        "field": "financial_info.annual_income",
                        "description": "Negative income value",
                        "suggestion": "Provide positive income value"
                    })
                    accuracy_score -= 0.2
                elif income_val > 10000000:  # $10M threshold
                    issues.append({
                        "type": QualityIssueType.OUTLIER_DETECTED,
                        "severity": QualitySeverity.MEDIUM,
                        "field": "financial_info.annual_income",
                        "description": f"Unusually high income: ${income_val:,.2f}",
                        "suggestion": "Verify income amount"
                    })
                    accuracy_score -= 0.1
            except:
                issues.append({
                    "type": QualityIssueType.INVALID_FORMAT,
                    "severity": QualitySeverity.HIGH,
                    "field": "financial_info.annual_income",
                    "description": f"Invalid numeric format: {income}",
                    "suggestion": "Provide numeric income value"
                })
                accuracy_score -= 0.2
        
        return {
            "score": max(accuracy_score, 0.0),
            "issues": issues,
            "metrics": {
                "format_violations": len([i for i in issues if i["type"] == QualityIssueType.INVALID_FORMAT]),
                "outliers": len([i for i in issues if i["type"] == QualityIssueType.OUTLIER_DETECTED])
            }
        }
    
    def _check_consistency(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Check data consistency"""
        issues = []
        consistency_score = 1.0
        
        # Check name consistency
        personal_info = data.get("personal_info", {})
        full_name = personal_info.get("full_name", "")
        first_name = personal_info.get("first_name", "")
        last_name = personal_info.get("last_name", "")
        
        if full_name and first_name and last_name:
            if not (first_name in full_name and last_name in full_name):
                issues.append({
                    "type": QualityIssueType.INCONSISTENT_DATA,
                    "severity": QualitySeverity.MEDIUM,
                    "field": "personal_info.names",
                    "description": "Inconsistent name fields",
                    "suggestion": "Ensure first_name and last_name match full_name"
                })
                consistency_score -= 0.2
        
        # Check address consistency
        address = personal_info.get("address", {})
        if isinstance(address, dict):
            country = address.get("country")
            postal_code = address.get("postal_code")
            
            if country == "US" and postal_code:
                if not re.match(r'^\d{5}(-\d{4})?$', postal_code):
                    issues.append({
                        "type": QualityIssueType.INCONSISTENT_DATA,
                        "severity": QualitySeverity.MEDIUM,
                        "field": "personal_info.address.postal_code",
                        "description": f"Postal code format inconsistent with country {country}",
                        "suggestion": "Use correct postal code format for the country"
                    })
                    consistency_score -= 0.1
        
        # Check document consistency
        documents = data.get("documents", [])
        identity_docs = [doc for doc in documents if doc.get("type") == "identity"]
        
        if len(identity_docs) > 1:
            # Check if names match across identity documents
            names = [doc.get("extracted_data", {}).get("name") for doc in identity_docs]
            names = [name for name in names if name]
            
            if len(set(names)) > 1:
                issues.append({
                    "type": QualityIssueType.INCONSISTENT_DATA,
                    "severity": QualitySeverity.HIGH,
                    "field": "documents.identity.names",
                    "description": "Inconsistent names across identity documents",
                    "suggestion": "Verify identity document authenticity"
                })
                consistency_score -= 0.3
        
        return {
            "score": max(consistency_score, 0.0),
            "issues": issues,
            "metrics": {
                "consistency_violations": len(issues)
            }
        }
    
    def _check_validity(self, data: Dict[str, Any], validation_rules: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Check data validity against schema and rules"""
        issues = []
        validity_score = 1.0
        
        # Default validation rules
        default_rules = {
            "personal_info": {
                "required_fields": ["full_name", "date_of_birth", "nationality"],
                "field_types": {
                    "full_name": str,
                    "date_of_birth": str,
                    "nationality": str,
                    "email": str,
                    "phone": str
                }
            },
            "financial_info": {
                "required_fields": ["annual_income"],
                "field_types": {
                    "annual_income": (int, float),
                    "employment_status": str
                }
            }
        }
        
        rules = validation_rules or default_rules
        
        # Validate against rules
        for section, section_rules in rules.items():
            section_data = data.get(section, {})
            
            # Check required fields
            for required_field in section_rules.get("required_fields", []):
                if required_field not in section_data or section_data[required_field] is None:
                    issues.append({
                        "type": QualityIssueType.SCHEMA_VIOLATION,
                        "severity": QualitySeverity.HIGH,
                        "field": f"{section}.{required_field}",
                        "description": f"Required field {required_field} is missing",
                        "suggestion": f"Provide value for {required_field}"
                    })
                    validity_score -= 0.2
            
            # Check field types
            for field, expected_type in section_rules.get("field_types", {}).items():
                if field in section_data and section_data[field] is not None:
                    if not isinstance(section_data[field], expected_type):
                        issues.append({
                            "type": QualityIssueType.SCHEMA_VIOLATION,
                            "severity": QualitySeverity.MEDIUM,
                            "field": f"{section}.{field}",
                            "description": f"Field {field} has incorrect type",
                            "suggestion": f"Provide {field} as {expected_type.__name__}"
                        })
                        validity_score -= 0.1
        
        return {
            "score": max(validity_score, 0.0),
            "issues": issues,
            "metrics": {
                "schema_violations": len([i for i in issues if i["type"] == QualityIssueType.SCHEMA_VIOLATION])
            }
        }
    
    def _check_uniqueness(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Check data uniqueness"""
        issues = []
        uniqueness_score = 1.0
        
        # Check for duplicate documents
        documents = data.get("documents", [])
        if len(documents) > 1:
            doc_hashes = []
            for i, doc in enumerate(documents):
                doc_content = json.dumps(doc, sort_keys=True)
                doc_hash = hashlib.md5(doc_content.encode()).hexdigest()
                
                if doc_hash in doc_hashes:
                    issues.append({
                        "type": QualityIssueType.DUPLICATE_RECORDS,
                        "severity": QualitySeverity.MEDIUM,
                        "field": f"documents[{i}]",
                        "description": "Duplicate document detected",
                        "suggestion": "Remove duplicate documents"
                    })
                    uniqueness_score -= 0.2
                else:
                    doc_hashes.append(doc_hash)
        
        # Check for duplicate transactions
        transactions = data.get("transaction_history", [])
        if len(transactions) > 1:
            transaction_signatures = []
            for i, txn in enumerate(transactions):
                # Create signature from amount, date, and description
                signature = f"{txn.get('amount', '')}_{txn.get('date', '')}_{txn.get('description', '')}"
                
                if signature in transaction_signatures:
                    issues.append({
                        "type": QualityIssueType.DUPLICATE_RECORDS,
                        "severity": QualitySeverity.LOW,
                        "field": f"transaction_history[{i}]",
                        "description": "Potential duplicate transaction",
                        "suggestion": "Verify transaction uniqueness"
                    })
                    uniqueness_score -= 0.1
                else:
                    transaction_signatures.append(signature)
        
        return {
            "score": max(uniqueness_score, 0.0),
            "issues": issues,
            "metrics": {
                "duplicate_documents": len([i for i in issues if "documents" in i["field"]]),
                "duplicate_transactions": len([i for i in issues if "transaction_history" in i["field"]])
            }
        }
    
    def _generate_recommendations(self, issues: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on issues"""
        recommendations = []
        
        # Group issues by type
        issue_types = {}
        for issue in issues:
            issue_type = issue["type"]
            if issue_type not in issue_types:
                issue_types[issue_type] = 0
            issue_types[issue_type] += 1
        
        # Generate recommendations
        if QualityIssueType.MISSING_DATA in issue_types:
            recommendations.append(f"Complete {issue_types[QualityIssueType.MISSING_DATA]} missing data fields")
        
        if QualityIssueType.INVALID_FORMAT in issue_types:
            recommendations.append(f"Fix {issue_types[QualityIssueType.INVALID_FORMAT]} format validation errors")
        
        if QualityIssueType.INCONSISTENT_DATA in issue_types:
            recommendations.append(f"Resolve {issue_types[QualityIssueType.INCONSISTENT_DATA]} data consistency issues")
        
        if QualityIssueType.DUPLICATE_RECORDS in issue_types:
            recommendations.append(f"Remove {issue_types[QualityIssueType.DUPLICATE_RECORDS]} duplicate records")
        
        if QualityIssueType.SCHEMA_VIOLATION in issue_types:
            recommendations.append(f"Address {issue_types[QualityIssueType.SCHEMA_VIOLATION]} schema violations")
        
        if not recommendations:
            recommendations.append("Data quality is good - continue monitoring")
        
        return recommendations

class AnomalyDetectionTool(Tool):
    """Tool for anomaly detection using multiple algorithms"""
    name = "anomaly_detection_tool"
    description = "Detect anomalies in customer data using various ML algorithms"
    inputs = {
        "data": {"type": "object", "description": "Data to analyze for anomalies"},
        "algorithms": {"type": "array", "description": "List of algorithms to use", "nullable": True}
    }
    output_type = "object"
    
    def __init__(self):
        super().__init__()
        self.isolation_forest = IForest(contamination=0.1)
        self.lof = LOF(contamination=0.1)
        self.ocsvm = OCSVM(contamination=0.1)
        self.scaler = StandardScaler()
    
    def forward(self, data: Dict[str, Any], algorithms: Optional[List[str]] = None) -> Dict[str, Any]:
        """Execute anomaly detection"""
        try:
            # Extract numerical features
            features = self._extract_features(data)
            
            if len(features) == 0:
                return {
                    "anomalies": [],
                    "anomaly_score": 0.0,
                    "algorithms_used": []
                }
            
            # Normalize features
            features_scaled = self.scaler.fit_transform([features])
            
            # Run multiple anomaly detection algorithms
            anomaly_results = {
                "isolation_forest": self._run_isolation_forest(features_scaled[0]),
                "local_outlier_factor": self._run_lof(features_scaled[0]),
                "one_class_svm": self._run_ocsvm(features_scaled[0])
            }
            
            # Combine results
            anomalies = self._combine_anomaly_results(anomaly_results, data)
            
            # Calculate overall anomaly score
            scores = [result["score"] for result in anomaly_results.values()]
            overall_score = np.mean(scores)
            
            return {
                "anomalies": anomalies,
                "anomaly_score": overall_score,
                "algorithm_results": anomaly_results,
                "algorithms_used": list(anomaly_results.keys())
            }
            
        except Exception as e:
            logger.error("Anomaly detection failed", error=str(e))
            return {
                "anomalies": [],
                "anomaly_score": 0.0,
                "error": str(e)
            }
    
    def _extract_features(self, data: Dict[str, Any]) -> List[float]:
        """Extract numerical features for anomaly detection"""
        features = []
        
        # Personal info features
        personal_info = data.get("personal_info", {})
        
        # Age (if date of birth available)
        dob = personal_info.get("date_of_birth")
        if dob:
            try:
                birth_date = date_parser.parse(dob)
                age = (datetime.now() - birth_date).days / 365.25
                features.append(age)
            except:
                features.append(30)  # Default age
        
        # Financial features
        financial_info = data.get("financial_info", {})
        
        # Annual income
        income = financial_info.get("annual_income", 0)
        try:
            features.append(float(income))
        except:
            features.append(0.0)
        
        # Transaction features
        transactions = data.get("transaction_history", [])
        
        # Transaction count
        features.append(len(transactions))
        
        # Average transaction amount
        if transactions:
            amounts = [float(t.get("amount", 0)) for t in transactions]
            features.append(np.mean(amounts))
            features.append(np.std(amounts))
            features.append(np.max(amounts))
            features.append(np.min(amounts))
        else:
            features.extend([0.0, 0.0, 0.0, 0.0])
        
        # Document count
        documents = data.get("documents", [])
        features.append(len(documents))
        
        # Verification status (binary features)
        verification = data.get("verification_status", {})
        features.append(1.0 if verification.get("identity", False) else 0.0)
        features.append(1.0 if verification.get("address", False) else 0.0)
        features.append(1.0 if verification.get("income", False) else 0.0)
        
        return features
    
    def _run_isolation_forest(self, features: np.ndarray) -> Dict[str, Any]:
        """Run Isolation Forest anomaly detection"""
        try:
            # Fit and predict
            self.isolation_forest.fit([features])
            anomaly_score = self.isolation_forest.decision_function([features])[0]
            is_anomaly = self.isolation_forest.predict([features])[0] == -1
            
            return {
                "algorithm": "isolation_forest",
                "is_anomaly": is_anomaly,
                "score": float(anomaly_score),
                "threshold": 0.0
            }
        except Exception as e:
            return {
                "algorithm": "isolation_forest",
                "is_anomaly": False,
                "score": 0.0,
                "error": str(e)
            }
    
    def _run_lof(self, features: np.ndarray) -> Dict[str, Any]:
        """Run Local Outlier Factor anomaly detection"""
        try:
            # Need multiple samples for LOF, so we'll use a simplified approach
            # In production, this would use historical data
            dummy_data = np.random.normal(0, 1, (100, len(features)))
            all_data = np.vstack([dummy_data, [features]])
            
            self.lof.fit(all_data)
            anomaly_score = self.lof.decision_function([features])[0]
            is_anomaly = self.lof.predict([features])[0] == -1
            
            return {
                "algorithm": "local_outlier_factor",
                "is_anomaly": is_anomaly,
                "score": float(anomaly_score),
                "threshold": 0.0
            }
        except Exception as e:
            return {
                "algorithm": "local_outlier_factor",
                "is_anomaly": False,
                "score": 0.0,
                "error": str(e)
            }
    
    def _run_ocsvm(self, features: np.ndarray) -> Dict[str, Any]:
        """Run One-Class SVM anomaly detection"""
        try:
            # Similar to LOF, need multiple samples
            dummy_data = np.random.normal(0, 1, (100, len(features)))
            all_data = np.vstack([dummy_data, [features]])
            
            self.ocsvm.fit(all_data)
            anomaly_score = self.ocsvm.decision_function([features])[0]
            is_anomaly = self.ocsvm.predict([features])[0] == -1
            
            return {
                "algorithm": "one_class_svm",
                "is_anomaly": is_anomaly,
                "score": float(anomaly_score),
                "threshold": 0.0
            }
        except Exception as e:
            return {
                "algorithm": "one_class_svm",
                "is_anomaly": False,
                "score": 0.0,
                "error": str(e)
            }
    
    def _combine_anomaly_results(self, results: Dict[str, Dict[str, Any]], data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Combine anomaly detection results"""
        anomalies = []
        
        # Count how many algorithms detected anomaly
        anomaly_count = sum(1 for result in results.values() if result.get("is_anomaly", False))
        
        if anomaly_count >= 2:  # Consensus approach
            anomalies.append({
                "type": "statistical_anomaly",
                "severity": QualitySeverity.HIGH if anomaly_count == 3 else QualitySeverity.MEDIUM,
                "description": f"Anomaly detected by {anomaly_count} out of 3 algorithms",
                "algorithms": [alg for alg, result in results.items() if result.get("is_anomaly", False)],
                "confidence": anomaly_count / 3.0,
                "metadata": {
                    "algorithm_results": results,
                    "feature_analysis": self._analyze_anomalous_features(data)
                }
            })
        
        return anomalies
    
    def _analyze_anomalous_features(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze which features might be anomalous"""
        analysis = {}
        
        # Check income
        income = data.get("financial_info", {}).get("annual_income", 0)
        try:
            income_val = float(income)
            if income_val > 1000000:  # $1M threshold
                analysis["high_income"] = f"Unusually high income: ${income_val:,.2f}"
            elif income_val < 10000:  # $10K threshold
                analysis["low_income"] = f"Unusually low income: ${income_val:,.2f}"
        except:
            pass
        
        # Check transaction volume
        transactions = data.get("transaction_history", [])
        if len(transactions) > 100:
            analysis["high_transaction_volume"] = f"High transaction count: {len(transactions)}"
        
        # Check age
        dob = data.get("personal_info", {}).get("date_of_birth")
        if dob:
            try:
                birth_date = date_parser.parse(dob)
                age = (datetime.now() - birth_date).days / 365.25
                if age < 18:
                    analysis["underage"] = f"Customer age below 18: {age:.1f} years"
                elif age > 100:
                    analysis["very_old"] = f"Customer age above 100: {age:.1f} years"
            except:
                pass
        
        return analysis

# Smolagents Configuration
class DataQualityAgents:
    """Smolagents-based data quality agents"""
    
    def __init__(self):
        self.validation_tool = DataValidationTool()
        self.anomaly_tool = AnomalyDetectionTool()
        
        # Configure Smolagents
        self.model_name = "microsoft/DialoGPT-medium"
        
        # Initialize agents
        self._setup_agents()
    
    def _setup_agents(self):
        """Setup Smolagents for data quality"""
        
        # Data Validation Agent
        self.validation_agent = CodeAgent(
            tools=[self.validation_tool],
            model=self.model_name
        )
        
        # Anomaly Detection Agent
        self.anomaly_agent = CodeAgent(
            tools=[self.anomaly_tool],
            model=self.model_name
        )
    
    async def perform_comprehensive_quality_check(self, data: Dict[str, Any], 
                                                validation_rules: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Perform comprehensive data quality check using Smolagents"""
        try:
            # Run validation agent
            validation_prompt = f"""
            Perform comprehensive data quality validation on the following customer data:
            
            {json.dumps(data, indent=2)}
            
            Validation Rules: {json.dumps(validation_rules, indent=2) if validation_rules else "Use default rules"}
            
            Please provide:
            1. Overall quality score
            2. Detailed validation results for completeness, accuracy, consistency, validity, and uniqueness
            3. List of all quality issues with severity levels
            4. Specific recommendations for improvement
            """
            
            validation_result = self.validation_agent.run(validation_prompt)
            
            # Run anomaly detection agent
            anomaly_prompt = f"""
            Perform anomaly detection on the following customer data:
            
            {json.dumps(data, indent=2)}
            
            Please provide:
            1. Anomaly detection results using multiple algorithms
            2. Overall anomaly score
            3. Detailed analysis of any anomalies found
            4. Business implications of detected anomalies
            """
            
            anomaly_result = self.anomaly_agent.run(anomaly_prompt)
            
            # Combine results
            combined_results = self._combine_agent_results(validation_result, anomaly_result, data)
            
            return combined_results
            
        except Exception as e:
            logger.error("Smolagents quality check failed", error=str(e))
            return {
                "overall_score": 0.0,
                "validation_status": ValidationStatus.FAILED,
                "issues": [],
                "anomalies": [],
                "recommendations": ["Manual quality review required due to system error"],
                "error": str(e)
            }
    
    def _combine_agent_results(self, validation_result: Any, anomaly_result: Any, data: Dict[str, Any]) -> Dict[str, Any]:
        """Combine results from validation and anomaly detection agents"""
        # Extract validation results
        validation_data = self.validation_tool(data)
        
        # Extract anomaly results
        anomaly_data = self.anomaly_tool(data)
        
        # Combine scores
        quality_scores = {
            "completeness": validation_data["validation_results"]["completeness"]["score"],
            "accuracy": validation_data["validation_results"]["accuracy"]["score"],
            "consistency": validation_data["validation_results"]["consistency"]["score"],
            "validity": validation_data["validation_results"]["validity"]["score"],
            "uniqueness": validation_data["validation_results"]["uniqueness"]["score"]
        }
        
        overall_score = validation_data["overall_score"]
        
        # Adjust score based on anomalies
        if anomaly_data["anomalies"]:
            anomaly_penalty = len(anomaly_data["anomalies"]) * 0.1
            overall_score = max(0.0, overall_score - anomaly_penalty)
        
        # Determine validation status
        if overall_score >= 0.8:
            status = ValidationStatus.PASSED
        elif overall_score >= 0.6:
            status = ValidationStatus.WARNING
        else:
            status = ValidationStatus.FAILED
        
        # Combine recommendations
        all_recommendations = validation_data["recommendations"]
        if anomaly_data["anomalies"]:
            all_recommendations.append("Investigate detected anomalies for potential data quality issues")
        
        return {
            "overall_score": overall_score,
            "quality_scores": quality_scores,
            "validation_status": status,
            "issues": validation_data["issues"],
            "anomalies": anomaly_data["anomalies"],
            "recommendations": all_recommendations,
            "validation_details": validation_data["validation_results"],
            "anomaly_details": anomaly_data
        }

# Main Service Class
class DataQualityService:
    """Main Data Quality Service using Smolagents"""
    
    def __init__(self):
        self.app = FastAPI(title="Data Quality Agent", version="1.0.0")
        self.setup_middleware()
        self.setup_routes()
        
        # Initialize components
        self.kafka_producer = None
        self.kafka_consumer = None
        self.redis_client = None
        self.db_connection = None
        self.mongo_client = None
        
        # Initialize Smolagents
        self.quality_agents = DataQualityAgents()
        
        # Setup components
        self._setup_database_connections()
        self._setup_messaging()
        
        # Start monitoring
        start_http_server(8005)
        
        logger.info("Data Quality Agent initialized successfully")
    
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
                "service": "data-quality-agent",
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0"
            }
        
        @self.app.post("/api/v1/quality/check", response_model=DataQualityResponse)
        async def check_data_quality(request: DataQualityRequest, background_tasks: BackgroundTasks):
            """Main data quality check endpoint"""
            quality_checks.inc()
            
            with validation_duration.time():
                try:
                    # Generate check ID
                    check_id = self._generate_check_id(request.customer_id)
                    
                    # Perform quality checks
                    quality_results = await self._perform_quality_checks(
                        request.customer_id,
                        request.data_type,
                        request.data_payload,
                        request.validation_rules,
                        request.check_anomalies
                    )
                    
                    # Update metrics
                    quality_score_gauge.set(quality_results["overall_score"])
                    
                    for issue in quality_results["issues"]:
                        quality_issues.labels(
                            issue_type=issue.get("type", "unknown"),
                            severity=issue.get("severity", "unknown")
                        ).inc()
                    
                    anomalies_detected.inc(len(quality_results["anomalies"]))
                    
                    # Send results to other agents
                    background_tasks.add_task(
                        self._send_quality_results,
                        check_id,
                        quality_results
                    )
                    
                    # Store results
                    background_tasks.add_task(
                        self._store_quality_results,
                        check_id,
                        quality_results
                    )
                    
                    return DataQualityResponse(
                        check_id=check_id,
                        customer_id=request.customer_id,
                        data_type=request.data_type,
                        overall_score=quality_results["overall_score"],
                        quality_scores=quality_results["quality_scores"],
                        validation_status=quality_results["validation_status"],
                        issues_found=quality_results["issues"],
                        anomalies=quality_results["anomalies"],
                        recommendations=quality_results["recommendations"],
                        processing_time=quality_results.get("processing_time", 0.0),
                        status="completed"
                    )
                    
                except Exception as e:
                    logger.error("Data quality check failed", 
                               customer_id=request.customer_id, 
                               error=str(e))
                    raise HTTPException(status_code=500, detail=f"Quality check failed: {str(e)}")
        
        @self.app.get("/api/v1/quality/profile/{customer_id}")
        async def get_data_profile(customer_id: str):
            """Get data quality profile for customer"""
            try:
                profile = await self._get_quality_profile(customer_id)
                return profile
            except Exception as e:
                logger.error("Failed to get quality profile", customer_id=customer_id, error=str(e))
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/quality/metrics")
        async def get_quality_metrics():
            """Get overall data quality metrics"""
            return {
                "total_checks": quality_checks._value.get(),
                "total_issues": quality_issues._value.get(),
                "total_anomalies": anomalies_detected._value.get(),
                "current_quality_score": quality_score_gauge._value.get(),
                "timestamp": datetime.now().isoformat()
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
    
    async def _perform_quality_checks(self, customer_id: str, data_type: DataType, 
                                    data_payload: Dict[str, Any], validation_rules: Optional[Dict[str, Any]],
                                    check_anomalies: bool) -> Dict[str, Any]:
        """Perform comprehensive data quality checks"""
        start_time = datetime.now()
        
        try:
            # Use Smolagents for comprehensive quality analysis
            quality_results = await self.quality_agents.perform_comprehensive_quality_check(
                data_payload, validation_rules
            )
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            quality_results["processing_time"] = processing_time
            
            logger.info("Data quality checks completed", 
                       customer_id=customer_id,
                       data_type=data_type,
                       processing_time=processing_time,
                       overall_score=quality_results["overall_score"])
            
            return quality_results
            
        except Exception as e:
            logger.error("Data quality checks failed", customer_id=customer_id, error=str(e))
            raise
    
    def _generate_check_id(self, customer_id: str) -> str:
        """Generate unique check ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hash_input = f"{customer_id}_{timestamp}_{uuid.uuid4().hex[:8]}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    async def _send_quality_results(self, check_id: str, results: Dict[str, Any]):
        """Send quality results to other agents via Kafka"""
        try:
            message = {
                "check_id": check_id,
                "agent": "data-quality-agent",
                "timestamp": datetime.now().isoformat(),
                "results": results
            }
            
            self.kafka_producer.send('quality-results', message)
            logger.info("Quality results sent to Kafka", check_id=check_id)
        except Exception as e:
            logger.error("Failed to send quality results", check_id=check_id, error=str(e))
    
    async def _store_quality_results(self, check_id: str, results: Dict[str, Any]):
        """Store quality results in database"""
        try:
            # Store in PostgreSQL
            cursor = self.db_connection.cursor()
            cursor.execute("""
                INSERT INTO data_quality_results (check_id, customer_id, results, created_at)
                VALUES (%s, %s, %s, %s)
            """, (check_id, results.get('customer_id'), json.dumps(results), datetime.now()))
            self.db_connection.commit()
            
            # Cache in Redis
            self.redis_client.setex(f"quality:{check_id}", 3600, json.dumps(results))
            
            logger.info("Quality results stored", check_id=check_id)
        except Exception as e:
            logger.error("Failed to store quality results", check_id=check_id, error=str(e))
    
    async def _get_quality_profile(self, customer_id: str) -> Dict[str, Any]:
        """Get data quality profile for customer"""
        try:
            # Query historical quality data
            cursor = self.db_connection.cursor()
            cursor.execute("""
                SELECT results, created_at FROM data_quality_results 
                WHERE customer_id = %s 
                ORDER BY created_at DESC 
                LIMIT 10
            """, (customer_id,))
            
            results = cursor.fetchall()
            
            if not results:
                return {
                    "customer_id": customer_id,
                    "profile": "No quality data available",
                    "historical_scores": [],
                    "trends": {}
                }
            
            # Process historical data
            historical_scores = []
            for result, created_at in results:
                data = json.loads(result)
                historical_scores.append({
                    "timestamp": created_at.isoformat(),
                    "overall_score": data.get("overall_score", 0.0),
                    "quality_scores": data.get("quality_scores", {})
                })
            
            # Calculate trends
            trends = self._calculate_quality_trends(historical_scores)
            
            return {
                "customer_id": customer_id,
                "current_score": historical_scores[0]["overall_score"] if historical_scores else 0.0,
                "historical_scores": historical_scores,
                "trends": trends,
                "last_updated": historical_scores[0]["timestamp"] if historical_scores else None
            }
            
        except Exception as e:
            logger.error("Failed to get quality profile", customer_id=customer_id, error=str(e))
            raise
    
    def _calculate_quality_trends(self, historical_scores: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate quality trends from historical data"""
        if len(historical_scores) < 2:
            return {"trend": "insufficient_data"}
        
        scores = [score["overall_score"] for score in historical_scores]
        
        # Calculate trend
        if len(scores) >= 3:
            recent_avg = np.mean(scores[:3])
            older_avg = np.mean(scores[-3:])
            
            if recent_avg > older_avg + 0.1:
                trend = "improving"
            elif recent_avg < older_avg - 0.1:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "current_score": scores[0],
            "average_score": np.mean(scores),
            "score_variance": np.var(scores),
            "data_points": len(scores)
        }

# Initialize service
service = DataQualityService()
app = service.app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005, workers=4)
