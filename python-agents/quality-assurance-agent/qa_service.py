"""
Quality Assurance Agent Service for KYC Automation Platform

This service performs comprehensive quality assurance checks on the results from all
other agents in the KYC workflow. It validates data consistency, checks for anomalies,
ensures compliance with policies, and provides final quality scoring.

Features:
- Cross-agent data consistency validation
- Policy compliance checking
- Anomaly detection and risk assessment
- Data quality scoring
- Exception handling and reporting
- Confidence level assessment
- Final recommendation validation
"""

import os
import json
import re
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
import logging
import numpy as np
from jsonschema import validate, ValidationError
from cerberus import Validator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Quality Assurance Agent Service",
    description="Quality assurance and validation for KYC processing results",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ProcessingConfig(BaseModel):
    """Processing configuration structure"""
    enable_ocr: bool = True
    enable_face_recognition: bool = True
    enable_watchlist_screening: bool = True
    enable_data_integration: bool = True
    enable_qa: bool = True
    risk_tolerance: str = "medium"

class QARequest(BaseModel):
    """Quality assurance processing request structure"""
    request_id: str
    all_results: Dict[str, Any]
    processing_config: ProcessingConfig

class ValidationRule(BaseModel):
    """Individual validation rule"""
    rule_id: str
    rule_name: str
    rule_type: str  # consistency, policy, anomaly, quality
    severity: str  # critical, high, medium, low
    description: str
    passed: bool
    details: Dict[str, Any] = {}
    confidence: float = Field(ge=0, le=100)

class QAException(BaseModel):
    """Quality assurance exception"""
    exception_id: str
    exception_type: str
    severity: str
    description: str
    affected_agents: List[str] = []
    recommendation: str
    auto_resolvable: bool = False

class QAMetrics(BaseModel):
    """Quality assurance metrics"""
    overall_quality_score: float = Field(ge=0, le=100)
    data_consistency_score: float = Field(ge=0, le=100)
    policy_compliance_score: float = Field(ge=0, le=100)
    confidence_score: float = Field(ge=0, le=100)
    completeness_score: float = Field(ge=0, le=100)
    accuracy_score: float = Field(ge=0, le=100)

class QAResult(BaseModel):
    """Quality assurance processing result"""
    status: str  # passed, failed, warning, manual_review
    qa_score: float = Field(ge=0, le=100)
    metrics: QAMetrics
    validation_rules: List[ValidationRule] = []
    exceptions: List[QAException] = []
    recommendations: List[str] = []
    requires_manual_review: bool = False
    processing_time_ms: int
    errors: List[str] = []
    warnings: List[str] = []

class QAResponse(BaseModel):
    """Quality assurance service response"""
    agent_name: str = "qa"
    status: str
    data: Dict[str, Any]
    processing_time: int
    error: Optional[str] = None
    version: str = "1.0.0"

class QualityAssuranceProcessor:
    """Main quality assurance processor"""
    
    def __init__(self):
        """Initialize QA processor with rules and policies"""
        # Initialize validation rules
        self.validation_rules = self._load_validation_rules()
        
        # Initialize policy configurations
        self.policy_config = self._load_policy_config()
        
        # Initialize data schemas for validation
        self.data_schemas = self._load_data_schemas()
        
        # QA thresholds
        self.qa_thresholds = {
            'minimum_quality_score': 70.0,
            'minimum_confidence': 60.0,
            'maximum_risk_score': 80.0,
            'minimum_face_match_score': 75.0,
            'minimum_ocr_confidence': 50.0
        }
        
        logger.info("Quality Assurance Processor initialized")

    def _load_validation_rules(self) -> List[Dict[str, Any]]:
        """Load validation rules configuration"""
        return [
            {
                'rule_id': 'name_consistency',
                'rule_name': 'Name Consistency Check',
                'rule_type': 'consistency',
                'severity': 'high',
                'description': 'Verify name consistency across OCR and face recognition results'
            },
            {
                'rule_id': 'date_validity',
                'rule_name': 'Date Validity Check',
                'rule_type': 'quality',
                'severity': 'medium',
                'description': 'Validate date formats and logical consistency'
            },
            {
                'rule_id': 'watchlist_critical',
                'rule_name': 'Critical Watchlist Match',
                'rule_type': 'policy',
                'severity': 'critical',
                'description': 'Check for critical watchlist matches that require rejection'
            },
            {
                'rule_id': 'face_match_threshold',
                'rule_name': 'Face Match Threshold',
                'rule_type': 'quality',
                'severity': 'high',
                'description': 'Verify face matching score meets minimum threshold'
            },
            {
                'rule_id': 'document_quality',
                'rule_name': 'Document Quality Check',
                'rule_type': 'quality',
                'severity': 'medium',
                'description': 'Ensure document quality meets minimum standards'
            },
            {
                'rule_id': 'liveness_detection',
                'rule_name': 'Liveness Detection Check',
                'rule_type': 'policy',
                'severity': 'high',
                'description': 'Verify liveness detection passed for selfie images'
            },
            {
                'rule_id': 'data_completeness',
                'rule_name': 'Data Completeness Check',
                'rule_type': 'quality',
                'severity': 'medium',
                'description': 'Ensure minimum required data fields are present'
            },
            {
                'rule_id': 'risk_score_threshold',
                'rule_name': 'Risk Score Threshold',
                'rule_type': 'policy',
                'severity': 'high',
                'description': 'Check if overall risk score exceeds acceptable threshold'
            }
        ]

    def _load_policy_config(self) -> Dict[str, Any]:
        """Load policy configuration"""
        return {
            'auto_reject_conditions': [
                'critical_watchlist_match',
                'liveness_detection_failed',
                'document_fraud_detected'
            ],
            'manual_review_conditions': [
                'low_confidence_score',
                'high_risk_score',
                'data_inconsistency',
                'partial_watchlist_match'
            ],
            'minimum_data_requirements': [
                'name',
                'date_of_birth',
                'document_number'
            ],
            'confidence_thresholds': {
                'high': 90.0,
                'medium': 70.0,
                'low': 50.0
            }
        }

    def _load_data_schemas(self) -> Dict[str, Dict]:
        """Load data validation schemas"""
        return {
            'ocr_result': {
                'type': 'object',
                'properties': {
                    'extracted_data': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': ['string', 'null']},
                            'date_of_birth': {'type': ['string', 'null']},
                            'id_number': {'type': ['string', 'null']}
                        }
                    },
                    'confidence_score': {'type': 'number', 'minimum': 0, 'maximum': 100}
                }
            },
            'face_result': {
                'type': 'object',
                'properties': {
                    'matching_result': {
                        'type': 'object',
                        'properties': {
                            'match_score': {'type': 'number', 'minimum': 0, 'maximum': 100},
                            'is_match': {'type': 'boolean'}
                        }
                    },
                    'liveness_result': {
                        'type': 'object',
                        'properties': {
                            'is_live': {'type': 'boolean'},
                            'confidence': {'type': 'number', 'minimum': 0, 'maximum': 100}
                        }
                    }
                }
            }
        }

    def validate_data_schemas(self, results: Dict[str, Any]) -> List[ValidationRule]:
        """
        Validate data schemas for all agent results
        
        Args:
            results: All agent results
            
        Returns:
            List of validation rules with results
        """
        validation_rules = []
        
        try:
            # Validate OCR results schema
            if 'ocr' in results:
                try:
                    ocr_data = results['ocr'].get('data', {})
                    if 'results' in ocr_data:
                        for result in ocr_data['results']:
                            validate(result, self.data_schemas['ocr_result'])
                    
                    validation_rules.append(ValidationRule(
                        rule_id='ocr_schema_validation',
                        rule_name='OCR Schema Validation',
                        rule_type='quality',
                        severity='medium',
                        description='OCR results conform to expected schema',
                        passed=True,
                        confidence=95.0
                    ))
                except ValidationError as e:
                    validation_rules.append(ValidationRule(
                        rule_id='ocr_schema_validation',
                        rule_name='OCR Schema Validation',
                        rule_type='quality',
                        severity='medium',
                        description='OCR results schema validation failed',
                        passed=False,
                        details={'error': str(e)},
                        confidence=0.0
                    ))
            
            # Validate Face results schema
            if 'face' in results:
                try:
                    face_data = results['face'].get('data', {})
                    validate(face_data, self.data_schemas['face_result'])
                    
                    validation_rules.append(ValidationRule(
                        rule_id='face_schema_validation',
                        rule_name='Face Schema Validation',
                        rule_type='quality',
                        severity='medium',
                        description='Face recognition results conform to expected schema',
                        passed=True,
                        confidence=95.0
                    ))
                except ValidationError as e:
                    validation_rules.append(ValidationRule(
                        rule_id='face_schema_validation',
                        rule_name='Face Schema Validation',
                        rule_type='quality',
                        severity='medium',
                        description='Face recognition results schema validation failed',
                        passed=False,
                        details={'error': str(e)},
                        confidence=0.0
                    ))
            
            return validation_rules
            
        except Exception as e:
            logger.error(f"Schema validation failed: {str(e)}")
            return [ValidationRule(
                rule_id='schema_validation_error',
                rule_name='Schema Validation Error',
                rule_type='quality',
                severity='high',
                description='Schema validation encountered an error',
                passed=False,
                details={'error': str(e)},
                confidence=0.0
            )]

    def check_name_consistency(self, results: Dict[str, Any]) -> ValidationRule:
        """
        Check name consistency across different agents
        
        Args:
            results: All agent results
            
        Returns:
            ValidationRule with consistency check results
        """
        try:
            names = []
            
            # Extract names from OCR results
            if 'ocr' in results:
                ocr_data = results['ocr'].get('data', {})
                if 'results' in ocr_data:
                    for result in ocr_data['results']:
                        extracted_data = result.get('extracted_data', {})
                        if extracted_data.get('name'):
                            names.append(extracted_data['name'].upper().strip())
            
            # Extract names from data integration results
            if 'data_integration' in results:
                di_data = results['data_integration'].get('data', {})
                # Could extract names from external data sources
            
            if len(names) < 2:
                return ValidationRule(
                    rule_id='name_consistency',
                    rule_name='Name Consistency Check',
                    rule_type='consistency',
                    severity='high',
                    description='Insufficient name data for consistency check',
                    passed=True,  # Pass if insufficient data
                    confidence=50.0
                )
            
            # Check if all names are similar
            base_name = names[0]
            consistency_scores = []
            
            for name in names[1:]:
                # Simple similarity check (could use more sophisticated matching)
                similarity = self._calculate_name_similarity(base_name, name)
                consistency_scores.append(similarity)
            
            avg_consistency = np.mean(consistency_scores) if consistency_scores else 100.0
            passed = avg_consistency >= 80.0  # 80% similarity threshold
            
            return ValidationRule(
                rule_id='name_consistency',
                rule_name='Name Consistency Check',
                rule_type='consistency',
                severity='high',
                description='Name consistency across agents',
                passed=passed,
                details={
                    'names_found': names,
                    'consistency_scores': consistency_scores,
                    'average_consistency': avg_consistency
                },
                confidence=avg_consistency
            )
            
        except Exception as e:
            logger.error(f"Name consistency check failed: {str(e)}")
            return ValidationRule(
                rule_id='name_consistency',
                rule_name='Name Consistency Check',
                rule_type='consistency',
                severity='high',
                description='Name consistency check encountered an error',
                passed=False,
                details={'error': str(e)},
                confidence=0.0
            )

    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names"""
        if not name1 or not name2:
            return 0.0
        
        # Simple token-based similarity
        tokens1 = set(name1.split())
        tokens2 = set(name2.split())
        
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)
        
        return (len(intersection) / len(union)) * 100.0

    def check_watchlist_critical_matches(self, results: Dict[str, Any]) -> ValidationRule:
        """
        Check for critical watchlist matches that require automatic rejection
        
        Args:
            results: All agent results
            
        Returns:
            ValidationRule with watchlist check results
        """
        try:
            if 'watchlist' not in results:
                return ValidationRule(
                    rule_id='watchlist_critical',
                    rule_name='Critical Watchlist Match',
                    rule_type='policy',
                    severity='critical',
                    description='Watchlist screening not performed',
                    passed=True,  # Pass if not performed
                    confidence=50.0
                )
            
            watchlist_data = results['watchlist'].get('data', {})
            
            # Check if flagged
            flagged = watchlist_data.get('flagged', False)
            if not flagged:
                return ValidationRule(
                    rule_id='watchlist_critical',
                    rule_name='Critical Watchlist Match',
                    rule_type='policy',
                    severity='critical',
                    description='No watchlist matches found',
                    passed=True,
                    confidence=95.0
                )
            
            # Check for critical risk level matches
            matches = watchlist_data.get('matches', [])
            critical_matches = [m for m in matches if m.get('risk_level') == 'critical']
            
            if critical_matches:
                return ValidationRule(
                    rule_id='watchlist_critical',
                    rule_name='Critical Watchlist Match',
                    rule_type='policy',
                    severity='critical',
                    description='Critical watchlist matches found - automatic rejection required',
                    passed=False,
                    details={
                        'critical_matches': critical_matches,
                        'match_count': len(critical_matches)
                    },
                    confidence=100.0
                )
            
            return ValidationRule(
                rule_id='watchlist_critical',
                rule_name='Critical Watchlist Match',
                rule_type='policy',
                severity='critical',
                description='Watchlist matches found but none are critical',
                passed=True,
                details={
                    'total_matches': len(matches),
                    'highest_risk_level': watchlist_data.get('highest_risk_level', 'unknown')
                },
                confidence=90.0
            )
            
        except Exception as e:
            logger.error(f"Watchlist critical check failed: {str(e)}")
            return ValidationRule(
                rule_id='watchlist_critical',
                rule_name='Critical Watchlist Match',
                rule_type='policy',
                severity='critical',
                description='Watchlist critical check encountered an error',
                passed=False,
                details={'error': str(e)},
                confidence=0.0
            )

    def check_face_match_threshold(self, results: Dict[str, Any]) -> ValidationRule:
        """
        Check if face matching score meets minimum threshold
        
        Args:
            results: All agent results
            
        Returns:
            ValidationRule with face match check results
        """
        try:
            if 'face' not in results:
                return ValidationRule(
                    rule_id='face_match_threshold',
                    rule_name='Face Match Threshold',
                    rule_type='quality',
                    severity='high',
                    description='Face recognition not performed',
                    passed=True,  # Pass if not performed
                    confidence=50.0
                )
            
            face_data = results['face'].get('data', {})
            matching_result = face_data.get('matching_result')
            
            if not matching_result:
                return ValidationRule(
                    rule_id='face_match_threshold',
                    rule_name='Face Match Threshold',
                    rule_type='quality',
                    severity='high',
                    description='Face matching results not available',
                    passed=False,
                    confidence=0.0
                )
            
            match_score = matching_result.get('match_score', 0.0)
            is_match = matching_result.get('is_match', False)
            threshold = self.qa_thresholds['minimum_face_match_score']
            
            passed = match_score >= threshold and is_match
            
            return ValidationRule(
                rule_id='face_match_threshold',
                rule_name='Face Match Threshold',
                rule_type='quality',
                severity='high',
                description=f'Face match score meets minimum threshold of {threshold}%',
                passed=passed,
                details={
                    'match_score': match_score,
                    'is_match': is_match,
                    'threshold': threshold
                },
                confidence=match_score
            )
            
        except Exception as e:
            logger.error(f"Face match threshold check failed: {str(e)}")
            return ValidationRule(
                rule_id='face_match_threshold',
                rule_name='Face Match Threshold',
                rule_type='quality',
                severity='high',
                description='Face match threshold check encountered an error',
                passed=False,
                details={'error': str(e)},
                confidence=0.0
            )

    def check_liveness_detection(self, results: Dict[str, Any]) -> ValidationRule:
        """
        Check liveness detection results
        
        Args:
            results: All agent results
            
        Returns:
            ValidationRule with liveness check results
        """
        try:
            if 'face' not in results:
                return ValidationRule(
                    rule_id='liveness_detection',
                    rule_name='Liveness Detection Check',
                    rule_type='policy',
                    severity='high',
                    description='Face recognition not performed',
                    passed=True,  # Pass if not performed
                    confidence=50.0
                )
            
            face_data = results['face'].get('data', {})
            liveness_result = face_data.get('liveness_result')
            
            if not liveness_result:
                return ValidationRule(
                    rule_id='liveness_detection',
                    rule_name='Liveness Detection Check',
                    rule_type='policy',
                    severity='high',
                    description='Liveness detection results not available',
                    passed=False,
                    confidence=0.0
                )
            
            is_live = liveness_result.get('is_live', False)
            confidence = liveness_result.get('confidence', 0.0)
            
            return ValidationRule(
                rule_id='liveness_detection',
                rule_name='Liveness Detection Check',
                rule_type='policy',
                severity='high',
                description='Liveness detection verification',
                passed=is_live,
                details={
                    'is_live': is_live,
                    'confidence': confidence,
                    'checks_performed': liveness_result.get('checks_performed', [])
                },
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Liveness detection check failed: {str(e)}")
            return ValidationRule(
                rule_id='liveness_detection',
                rule_name='Liveness Detection Check',
                rule_type='policy',
                severity='high',
                description='Liveness detection check encountered an error',
                passed=False,
                details={'error': str(e)},
                confidence=0.0
            )

    def check_data_completeness(self, results: Dict[str, Any]) -> ValidationRule:
        """
        Check data completeness across all agents
        
        Args:
            results: All agent results
            
        Returns:
            ValidationRule with completeness check results
        """
        try:
            required_fields = self.policy_config['minimum_data_requirements']
            found_fields = []
            
            # Check OCR results for required fields
            if 'ocr' in results:
                ocr_data = results['ocr'].get('data', {})
                if 'results' in ocr_data:
                    for result in ocr_data['results']:
                        extracted_data = result.get('extracted_data', {})
                        for field in required_fields:
                            if extracted_data.get(field):
                                found_fields.append(field)
            
            # Remove duplicates
            found_fields = list(set(found_fields))
            missing_fields = [field for field in required_fields if field not in found_fields]
            
            completeness_score = (len(found_fields) / len(required_fields)) * 100.0
            passed = completeness_score >= 80.0  # 80% completeness threshold
            
            return ValidationRule(
                rule_id='data_completeness',
                rule_name='Data Completeness Check',
                rule_type='quality',
                severity='medium',
                description='Minimum required data fields are present',
                passed=passed,
                details={
                    'required_fields': required_fields,
                    'found_fields': found_fields,
                    'missing_fields': missing_fields,
                    'completeness_score': completeness_score
                },
                confidence=completeness_score
            )
            
        except Exception as e:
            logger.error(f"Data completeness check failed: {str(e)}")
            return ValidationRule(
                rule_id='data_completeness',
                rule_name='Data Completeness Check',
                rule_type='quality',
                severity='medium',
                description='Data completeness check encountered an error',
                passed=False,
                details={'error': str(e)},
                confidence=0.0
            )

    def calculate_qa_metrics(self, results: Dict[str, Any], validation_rules: List[ValidationRule]) -> QAMetrics:
        """
        Calculate comprehensive QA metrics
        
        Args:
            results: All agent results
            validation_rules: List of validation rules
            
        Returns:
            QAMetrics with calculated scores
        """
        try:
            # Data consistency score
            consistency_rules = [r for r in validation_rules if r.rule_type == 'consistency']
            if consistency_rules:
                consistency_scores = [r.confidence for r in consistency_rules if r.passed]
                data_consistency_score = np.mean(consistency_scores) if consistency_scores else 0.0
            else:
                data_consistency_score = 100.0  # No consistency issues
            
            # Policy compliance score
            policy_rules = [r for r in validation_rules if r.rule_type == 'policy']
            if policy_rules:
                policy_scores = [r.confidence for r in policy_rules if r.passed]
                policy_compliance_score = np.mean(policy_scores) if policy_scores else 0.0
            else:
                policy_compliance_score = 100.0  # No policy violations
            
            # Quality score
            quality_rules = [r for r in validation_rules if r.rule_type == 'quality']
            if quality_rules:
                quality_scores = [r.confidence for r in quality_rules if r.passed]
                quality_score = np.mean(quality_scores) if quality_scores else 0.0
            else:
                quality_score = 100.0  # No quality issues
            
            # Overall confidence score
            all_confidences = [r.confidence for r in validation_rules if r.passed]
            confidence_score = np.mean(all_confidences) if all_confidences else 0.0
            
            # Completeness score (from data completeness rule)
            completeness_rule = next((r for r in validation_rules if r.rule_id == 'data_completeness'), None)
            completeness_score = completeness_rule.confidence if completeness_rule else 50.0
            
            # Accuracy score (based on agent-specific metrics)
            accuracy_scores = []
            
            # OCR accuracy
            if 'ocr' in results:
                ocr_data = results['ocr'].get('data', {})
                if 'summary' in ocr_data:
                    accuracy_scores.append(ocr_data['summary'].get('average_confidence', 50.0))
            
            # Face recognition accuracy
            if 'face' in results:
                face_data = results['face'].get('data', {})
                if 'overall_score' in face_data:
                    accuracy_scores.append(face_data['overall_score'])
            
            accuracy_score = np.mean(accuracy_scores) if accuracy_scores else 50.0
            
            # Overall quality score (weighted average)
            overall_quality_score = (
                data_consistency_score * 0.2 +
                policy_compliance_score * 0.3 +
                quality_score * 0.2 +
                confidence_score * 0.1 +
                completeness_score * 0.1 +
                accuracy_score * 0.1
            )
            
            return QAMetrics(
                overall_quality_score=overall_quality_score,
                data_consistency_score=data_consistency_score,
                policy_compliance_score=policy_compliance_score,
                confidence_score=confidence_score,
                completeness_score=completeness_score,
                accuracy_score=accuracy_score
            )
            
        except Exception as e:
            logger.error(f"QA metrics calculation failed: {str(e)}")
            return QAMetrics(
                overall_quality_score=0.0,
                data_consistency_score=0.0,
                policy_compliance_score=0.0,
                confidence_score=0.0,
                completeness_score=0.0,
                accuracy_score=0.0
            )

    def generate_exceptions(self, validation_rules: List[ValidationRule]) -> List[QAException]:
        """
        Generate QA exceptions based on failed validation rules
        
        Args:
            validation_rules: List of validation rules
            
        Returns:
            List of QA exceptions
        """
        exceptions = []
        
        try:
            failed_rules = [r for r in validation_rules if not r.passed]
            
            for rule in failed_rules:
                exception_type = f"{rule.rule_type}_violation"
                
                # Determine recommendation based on rule
                if rule.severity == 'critical':
                    recommendation = "Automatic rejection recommended"
                    auto_resolvable = False
                elif rule.severity == 'high':
                    recommendation = "Manual review required"
                    auto_resolvable = False
                elif rule.severity == 'medium':
                    recommendation = "Additional verification recommended"
                    auto_resolvable = True
                else:
                    recommendation = "Monitor for future improvements"
                    auto_resolvable = True
                
                exception = QAException(
                    exception_id=f"qa_exception_{rule.rule_id}",
                    exception_type=exception_type,
                    severity=rule.severity,
                    description=f"{rule.rule_name}: {rule.description}",
                    affected_agents=self._determine_affected_agents(rule),
                    recommendation=recommendation,
                    auto_resolvable=auto_resolvable
                )
                
                exceptions.append(exception)
            
            return exceptions
            
        except Exception as e:
            logger.error(f"Exception generation failed: {str(e)}")
            return [QAException(
                exception_id="qa_exception_error",
                exception_type="system_error",
                severity="high",
                description=f"QA exception generation failed: {str(e)}",
                affected_agents=["qa"],
                recommendation="Manual review required",
                auto_resolvable=False
            )]

    def _determine_affected_agents(self, rule: ValidationRule) -> List[str]:
        """Determine which agents are affected by a validation rule failure"""
        agent_mapping = {
            'name_consistency': ['ocr', 'data_integration'],
            'watchlist_critical': ['watchlist'],
            'face_match_threshold': ['face'],
            'liveness_detection': ['face'],
            'data_completeness': ['ocr', 'data_integration'],
            'ocr_schema_validation': ['ocr'],
            'face_schema_validation': ['face']
        }
        
        return agent_mapping.get(rule.rule_id, ['unknown'])

    def process_quality_assurance(self, request: QARequest) -> QAResult:
        """
        Process complete quality assurance request
        
        Args:
            request: QA processing request
            
        Returns:
            QAResult with comprehensive quality assessment
        """
        start_time = datetime.now()
        errors = []
        warnings = []
        
        try:
            validation_rules = []
            
            # Perform schema validation
            schema_rules = self.validate_data_schemas(request.all_results)
            validation_rules.extend(schema_rules)
            
            # Perform specific validation checks
            validation_checks = [
                self.check_name_consistency,
                self.check_watchlist_critical_matches,
                self.check_face_match_threshold,
                self.check_liveness_detection,
                self.check_data_completeness
            ]
            
            for check_func in validation_checks:
                try:
                    rule = check_func(request.all_results)
                    validation_rules.append(rule)
                except Exception as e:
                    error_msg = f"Validation check {check_func.__name__} failed: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            # Calculate QA metrics
            metrics = self.calculate_qa_metrics(request.all_results, validation_rules)
            
            # Generate exceptions
            exceptions = self.generate_exceptions(validation_rules)
            
            # Determine overall status
            critical_failures = [r for r in validation_rules if not r.passed and r.severity == 'critical']
            high_failures = [r for r in validation_rules if not r.passed and r.severity == 'high']
            
            if critical_failures:
                status = "failed"
                requires_manual_review = True
            elif high_failures or metrics.overall_quality_score < self.qa_thresholds['minimum_quality_score']:
                status = "manual_review"
                requires_manual_review = True
            elif any(not r.passed for r in validation_rules):
                status = "warning"
                requires_manual_review = False
            else:
                status = "passed"
                requires_manual_review = False
            
            # Generate recommendations
            recommendations = self._generate_recommendations(validation_rules, metrics, exceptions)
            
            # Add warnings for specific conditions
            if metrics.confidence_score < self.qa_thresholds['minimum_confidence']:
                warnings.append(f"Low confidence score: {metrics.confidence_score:.1f}%")
            
            if exceptions:
                warnings.append(f"Found {len(exceptions)} QA exceptions")
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return QAResult(
                status=status,
                qa_score=metrics.overall_quality_score,
                metrics=metrics,
                validation_rules=validation_rules,
                exceptions=exceptions,
                recommendations=recommendations,
                requires_manual_review=requires_manual_review,
                processing_time_ms=processing_time,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"Quality assurance processing failed: {str(e)}")
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return QAResult(
                status="failed",
                qa_score=0.0,
                metrics=QAMetrics(
                    overall_quality_score=0.0,
                    data_consistency_score=0.0,
                    policy_compliance_score=0.0,
                    confidence_score=0.0,
                    completeness_score=0.0,
                    accuracy_score=0.0
                ),
                processing_time_ms=processing_time,
                errors=[str(e)],
                warnings=warnings,
                requires_manual_review=True
            )

    def _generate_recommendations(
        self, 
        validation_rules: List[ValidationRule], 
        metrics: QAMetrics, 
        exceptions: List[QAException]
    ) -> List[str]:
        """Generate actionable recommendations based on QA results"""
        recommendations = []
        
        try:
            # Critical issues
            critical_failures = [r for r in validation_rules if not r.passed and r.severity == 'critical']
            if critical_failures:
                recommendations.append("Immediate rejection recommended due to critical policy violations")
            
            # High severity issues
            high_failures = [r for r in validation_rules if not r.passed and r.severity == 'high']
            if high_failures:
                recommendations.append("Manual review required for high-severity issues")
            
            # Quality improvements
            if metrics.data_consistency_score < 70.0:
                recommendations.append("Improve data consistency across verification sources")
            
            if metrics.completeness_score < 80.0:
                recommendations.append("Collect additional required documentation")
            
            if metrics.confidence_score < 60.0:
                recommendations.append("Request higher quality document images")
            
            # Agent-specific recommendations
            face_rules = [r for r in validation_rules if 'face' in r.rule_id and not r.passed]
            if face_rules:
                recommendations.append("Re-capture selfie image with better lighting and positioning")
            
            ocr_rules = [r for r in validation_rules if 'ocr' in r.rule_id and not r.passed]
            if ocr_rules:
                recommendations.append("Provide clearer document images for better text extraction")
            
            # Exception-based recommendations
            auto_resolvable_exceptions = [e for e in exceptions if e.auto_resolvable]
            if auto_resolvable_exceptions:
                recommendations.append("Some issues can be automatically resolved with additional processing")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Recommendation generation failed: {str(e)}")
            return ["Manual review recommended due to QA processing issues"]

# Initialize QA processor
qa_processor = QualityAssuranceProcessor()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "qa-agent",
        "version": "1.0.0",
        "validation_rules_loaded": len(qa_processor.validation_rules),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/process", response_model=QAResponse)
async def process_qa_request(request: QARequest):
    """
    Process quality assurance request
    
    Args:
        request: QA processing request
        
    Returns:
        QA processing response
    """
    start_time = datetime.now()
    
    try:
        logger.info(f"Processing QA request: {request.request_id}")
        
        # Process quality assurance
        result = qa_processor.process_quality_assurance(request)
        
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Determine response status
        if result.status == "failed":
            response_status = "Error"
        elif result.status in ["warning", "manual_review"]:
            response_status = "Warning"
        else:
            response_status = "Success"
        
        response_data = result.dict()
        
        return QAResponse(
            status=response_status,
            data=response_data,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"QA processing failed: {str(e)}")
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        return QAResponse(
            status="Error",
            data={"error": str(e)},
            processing_time=processing_time,
            error=str(e)
        )

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Quality Assurance Agent",
        "description": "Quality assurance and validation for KYC processing results",
        "version": "1.0.0",
        "validation_rules": len(qa_processor.validation_rules),
        "endpoints": {
            "health": "/health",
            "process": "/process"
        }
    }

@app.get("/rules")
async def get_validation_rules():
    """Get information about available validation rules"""
    return {
        "validation_rules": qa_processor.validation_rules,
        "policy_config": qa_processor.policy_config,
        "qa_thresholds": qa_processor.qa_thresholds
    }

if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.getenv("PORT", 8005))
    
    # Run the service
    uvicorn.run(
        "qa_service:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
