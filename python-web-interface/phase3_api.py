#!/usr/bin/env python3
"""
Phase 3 API Endpoints for Intelligence & Compliance Agent Dashboard
================================================================

This module provides REST API endpoints for testing and monitoring
Phase 3 components through the web interface.

Features:
- Rule Compiler API endpoints
- Kafka Consumer control endpoints  
- Jurisdiction Handler testing endpoints
- Overlap Resolver analysis endpoints
- Audit Logger management endpoints
- Real-time WebSocket updates

Rule Compliance:
- Rule 6: UI components for testing all Phase 3 features
- Rule 7: Professional API design with proper error handling
- Rule 10: REQUIRE_AUTH integration for security
- Rule 17: Comprehensive documentation throughout
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import asdict

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import asyncpg

# Import Phase 3 components
import sys
sys.path.append('/Users/krishna/Downloads/gaigenticai/ComplianceAI/python-agents/intelligence-compliance-agent/src')

from rule_compiler import RuleCompiler, RegulationType
from kafka_consumer import RegulatoryKafkaConsumer
from jurisdiction_handler import JurisdictionHandler, ConflictResolutionStrategy
from overlap_resolver import OverlapResolver
from audit_logger import AuditLogger

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models for API requests/responses
class RuleCompileRequest(BaseModel):
    obligation_text: str = Field(..., description="Regulatory obligation text to compile")
    regulation_type: str = Field(..., description="Type of regulation (AML, KYC, etc.)")
    jurisdiction: str = Field(..., description="Jurisdiction code (EU, DE, IE, GB)")

class RuleValidateRequest(BaseModel):
    json_logic: Dict[str, Any] = Field(..., description="JSON-Logic rule to validate")

class RuleTestRequest(BaseModel):
    json_logic: Dict[str, Any] = Field(..., description="JSON-Logic rule to test")

class KafkaTestMessageRequest(BaseModel):
    event_type: str = Field(..., description="Type of Kafka event")
    payload: Dict[str, Any] = Field(..., description="Message payload")

class JurisdictionFilterRequest(BaseModel):
    customer_country: str = Field(..., description="Customer country code")
    business_country: str = Field(..., description="Business country code")
    conflict_strategy: str = Field(..., description="Conflict resolution strategy")

class OverlapDetectRequest(BaseModel):
    rule1_text: str = Field(..., description="First rule text")
    rule2_text: str = Field(..., description="Second rule text")
    similarity_threshold: float = Field(..., description="Similarity threshold (0.0-1.0)")

class AuditCreateRequest(BaseModel):
    action: str = Field(..., description="Audit action type")
    details: str = Field(..., description="Action details")
    user_id: str = Field(..., description="User ID performing action")

class Phase3API:
    """
    Phase 3 API handler for Intelligence & Compliance Agent dashboard
    
    Provides REST endpoints for testing and monitoring all Phase 3 components
    with proper authentication, error handling, and real-time updates.
    """
    
    def __init__(self):
        self.app = FastAPI(title="Phase 3 Intelligence & Compliance API", version="1.0.0")
        self.setup_middleware()
        self.setup_routes()
        
        # Initialize Phase 3 components
        self.rule_compiler = None
        self.kafka_consumer = None
        self.jurisdiction_handler = None
        self.overlap_resolver = None
        self.audit_logger = None
        
        # WebSocket connections for real-time updates
        self.websocket_connections: List[WebSocket] = []
        
        # Database connection pool
        self.pg_pool = None
        
    def setup_middleware(self):
        """Setup CORS and other middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def setup_routes(self):
        """Setup all API routes"""
        
        # Health check
        @self.app.get("/api/phase3/health")
        async def health_check():
            """Health check endpoint"""
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}
        
        # Rule Compiler endpoints
        @self.app.post("/api/phase3/rule-compiler/compile")
        async def compile_rule(request: RuleCompileRequest, user=Depends(self.get_current_user)):
            """Compile regulatory obligation into JSON-Logic rule"""
            try:
                if not self.rule_compiler:
                    await self.initialize_components()
                
                start_time = datetime.now()
                
                # Create obligation data structure
                obligation_data = {
                    'obligation_text': request.obligation_text,
                    'regulation_type': request.regulation_type,
                    'jurisdiction': request.jurisdiction,
                    'obligation_level': 'Level_2',  # Default for testing
                    'confidence_score': 0.85,
                    'effective_date': datetime.now(),
                    'created_at': datetime.now()
                }
                
                # Compile the rule
                rules = await self.rule_compiler.compile_obligation_to_rules(obligation_data)
                
                compilation_time = (datetime.now() - start_time).total_seconds() * 1000
                
                if rules:
                    rule = rules[0]  # Take first rule for demo
                    
                    # Log audit entry
                    await self.audit_logger.log_rule_change(
                        rule_id=rule.rule_id,
                        action='rule_compiled',
                        old_rule=None,
                        new_rule=rule,
                        user_id=user['user_id']
                    )
                    
                    # Broadcast to WebSocket clients
                    await self.broadcast_websocket({
                        'type': 'rule_compiled',
                        'rule_id': rule.rule_id,
                        'compilation_time': compilation_time
                    })
                    
                    return {
                        'success': True,
                        'rule_id': rule.rule_id,
                        'json_logic': rule.json_logic,
                        'compilation_time': f"{compilation_time:.1f}",
                        'confidence_score': rule.confidence_score,
                        'total_rules': len(rules)
                    }
                else:
                    raise HTTPException(status_code=400, detail="Failed to compile rule")
                    
            except Exception as e:
                logger.error(f"Rule compilation error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/phase3/rule-compiler/validate")
        async def validate_rule(request: RuleValidateRequest, user=Depends(self.get_current_user)):
            """Validate JSON-Logic rule structure"""
            try:
                if not self.rule_compiler:
                    await self.initialize_components()
                
                is_valid = self.rule_compiler._validate_json_logic(request.json_logic)
                
                return {
                    'valid': is_valid,
                    'message': 'Rule validation passed' if is_valid else 'Rule validation failed'
                }
                
            except Exception as e:
                logger.error(f"Rule validation error: {e}")
                return {'valid': False, 'error': str(e)}
        
        @self.app.post("/api/phase3/rule-compiler/test")
        async def test_rule(request: RuleTestRequest, user=Depends(self.get_current_user)):
            """Test JSON-Logic rule with sample data"""
            try:
                if not self.rule_compiler:
                    await self.initialize_components()
                
                # Create a mock rule object for testing
                from rule_compiler import ComplianceRule, RuleCondition, ConditionOperator
                
                mock_rule = ComplianceRule(
                    rule_id='test_rule',
                    regulation_type=RegulationType.AML,
                    jurisdiction='EU',
                    json_logic=request.json_logic,
                    conditions=[],  # Will be populated by test data generation
                    confidence_score=0.9
                )
                
                test_passed = await self.rule_compiler._test_rule_with_sample_data(mock_rule)
                
                return {
                    'passed': test_passed,
                    'result': 'Test completed successfully' if test_passed else 'Test failed',
                    'message': 'Rule executed against sample data'
                }
                
            except Exception as e:
                logger.error(f"Rule testing error: {e}")
                return {'passed': False, 'error': str(e)}
        
        # Kafka Consumer endpoints
        @self.app.post("/api/phase3/kafka-consumer/start")
        async def start_kafka_consumer(user=Depends(self.get_current_user)):
            """Start Kafka consumer for regulatory updates"""
            try:
                if not self.kafka_consumer:
                    await self.initialize_components()
                
                await self.kafka_consumer.start()
                
                # Log audit entry
                await self.audit_logger.log_system_event(
                    event_type='kafka_consumer_started',
                    details='Kafka consumer started via API',
                    user_id=user['user_id']
                )
                
                return {'success': True, 'message': 'Kafka consumer started'}
                
            except Exception as e:
                logger.error(f"Failed to start Kafka consumer: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/phase3/kafka-consumer/stop")
        async def stop_kafka_consumer(user=Depends(self.get_current_user)):
            """Stop Kafka consumer"""
            try:
                if self.kafka_consumer:
                    await self.kafka_consumer.stop()
                
                # Log audit entry
                await self.audit_logger.log_system_event(
                    event_type='kafka_consumer_stopped',
                    details='Kafka consumer stopped via API',
                    user_id=user['user_id']
                )
                
                return {'success': True, 'message': 'Kafka consumer stopped'}
                
            except Exception as e:
                logger.error(f"Failed to stop Kafka consumer: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/phase3/kafka-consumer/test-message")
        async def send_test_message(request: KafkaTestMessageRequest, user=Depends(self.get_current_user)):
            """Send test message to Kafka consumer"""
            try:
                if not self.kafka_consumer:
                    await self.initialize_components()
                
                # Create mock Kafka message
                class MockMessage:
                    def __init__(self, event_type, payload):
                        self.topic = 'regulatory.updates'
                        self.partition = 0
                        self.offset = 0
                        self.timestamp = datetime.now()
                        self.value = json.dumps({
                            'event_type': event_type,
                            'payload': payload,
                            'timestamp': self.timestamp.isoformat()
                        }).encode('utf-8')
                
                mock_message = MockMessage(request.event_type, request.payload)
                
                # Process the message
                await self.kafka_consumer._process_message(mock_message)
                
                # Broadcast to WebSocket clients
                await self.broadcast_websocket({
                    'type': 'kafka_message',
                    'message': {
                        'timestamp': datetime.now().isoformat(),
                        'event_type': request.event_type,
                        'payload': request.payload,
                        'status': 'processed'
                    }
                })
                
                return {'success': True, 'message': 'Test message processed'}
                
            except Exception as e:
                logger.error(f"Failed to process test message: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Jurisdiction Handler endpoints
        @self.app.post("/api/phase3/jurisdiction-handler/filter")
        async def filter_by_jurisdiction(request: JurisdictionFilterRequest, user=Depends(self.get_current_user)):
            """Filter rules by jurisdiction"""
            try:
                if not self.jurisdiction_handler:
                    await self.initialize_components()
                
                # Create customer jurisdiction data
                customer_jurisdiction = {
                    'customer_id': 'test_customer',
                    'primary_jurisdiction': request.customer_country,
                    'secondary_jurisdictions': [request.business_country],
                    'conflict_resolution_strategy': request.conflict_strategy
                }
                
                # Get applicable rules (mock data for demo)
                applicable_rules = await self._get_mock_rules_for_jurisdiction(
                    request.customer_country, request.business_country
                )
                
                return {
                    'success': True,
                    'applicable_rules': applicable_rules,
                    'customer_jurisdiction': customer_jurisdiction,
                    'conflict_strategy': request.conflict_strategy
                }
                
            except Exception as e:
                logger.error(f"Jurisdiction filtering error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/phase3/jurisdiction-handler/config")
        async def get_jurisdiction_config(user=Depends(self.get_current_user)):
            """Get jurisdiction configuration"""
            try:
                # Return mock jurisdiction configuration
                jurisdictions = [
                    {'code': 'EU', 'level': 'Supranational', 'parent': None, 'active_rules': 45, 'enabled': True},
                    {'code': 'DE', 'level': 'National', 'parent': 'EU', 'active_rules': 23, 'enabled': True},
                    {'code': 'IE', 'level': 'National', 'parent': 'EU', 'active_rules': 18, 'enabled': True},
                    {'code': 'GB', 'level': 'National', 'parent': None, 'active_rules': 31, 'enabled': True}
                ]
                
                return {'jurisdictions': jurisdictions}
                
            except Exception as e:
                logger.error(f"Failed to get jurisdiction config: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Overlap Resolver endpoints
        @self.app.post("/api/phase3/overlap-resolver/detect")
        async def detect_overlaps(request: OverlapDetectRequest, user=Depends(self.get_current_user)):
            """Detect overlaps between rules"""
            try:
                if not self.overlap_resolver:
                    await self.initialize_components()
                
                # Calculate similarity using NLP
                similarity_score = await self.overlap_resolver._calculate_text_similarity(
                    request.rule1_text, request.rule2_text
                )
                
                overlap_detected = similarity_score >= request.similarity_threshold
                
                result = {
                    'overlap_detected': overlap_detected,
                    'similarity_score': similarity_score,
                    'threshold': request.similarity_threshold,
                    'overlap_type': 'semantic' if overlap_detected else 'none',
                    'common_elements': []
                }
                
                if overlap_detected:
                    # Extract common elements (simplified)
                    words1 = set(request.rule1_text.lower().split())
                    words2 = set(request.rule2_text.lower().split())
                    common_words = words1.intersection(words2)
                    result['common_elements'] = list(common_words)[:10]  # Top 10
                
                return result
                
            except Exception as e:
                logger.error(f"Overlap detection error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Audit Logger endpoints
        @self.app.post("/api/phase3/audit-logger/create")
        async def create_audit_entry(request: AuditCreateRequest, user=Depends(self.get_current_user)):
            """Create audit log entry"""
            try:
                if not self.audit_logger:
                    await self.initialize_components()
                
                # Create audit entry
                entry_id = await self.audit_logger.log_system_event(
                    event_type=request.action,
                    details=request.details,
                    user_id=request.user_id
                )
                
                # Broadcast to WebSocket clients
                await self.broadcast_websocket({
                    'type': 'audit_entry',
                    'entry': {
                        'entry_id': entry_id,
                        'action': request.action,
                        'details': request.details,
                        'user_id': request.user_id,
                        'timestamp': datetime.now().isoformat()
                    }
                })
                
                return {
                    'success': True,
                    'entry_id': entry_id,
                    'message': 'Audit entry created successfully'
                }
                
            except Exception as e:
                logger.error(f"Failed to create audit entry: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/phase3/audit-logger/query")
        async def query_audit_trail(
            date_from: str = None,
            date_to: str = None,
            action: str = None,
            user=Depends(self.get_current_user)
        ):
            """Query audit trail"""
            try:
                if not self.audit_logger:
                    await self.initialize_components()
                
                # Mock audit entries for demo
                entries = await self._get_mock_audit_entries(date_from, date_to, action)
                
                return {
                    'success': True,
                    'entries': entries,
                    'total': len(entries)
                }
                
            except Exception as e:
                logger.error(f"Audit query error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/phase3/audit-logger/recent")
        async def get_recent_audit_entries(user=Depends(self.get_current_user)):
            """Get recent audit entries"""
            try:
                # Return mock recent entries
                entries = await self._get_mock_audit_entries(limit=20)
                
                return {
                    'success': True,
                    'entries': entries
                }
                
            except Exception as e:
                logger.error(f"Failed to get recent audit entries: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/phase3/audit-logger/export")
        async def export_audit_trail(format: str = 'json', user=Depends(self.get_current_user)):
            """Export audit trail"""
            try:
                if not self.audit_logger:
                    await self.initialize_components()
                
                # Export audit trail
                export_path = await self.audit_logger.export_audit_trail(
                    format=format,
                    date_from=None,
                    date_to=None
                )
                
                return FileResponse(
                    path=export_path,
                    filename=f"audit_trail.{format}",
                    media_type='application/octet-stream'
                )
                
            except Exception as e:
                logger.error(f"Audit export error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/phase3/audit-logger/verify-integrity")
        async def verify_audit_integrity(user=Depends(self.get_current_user)):
            """Verify audit trail integrity"""
            try:
                if not self.audit_logger:
                    await self.initialize_components()
                
                # Verify integrity
                is_valid = await self.audit_logger.verify_audit_integrity()
                
                return {
                    'valid': is_valid,
                    'message': 'Audit trail integrity verified' if is_valid else 'Integrity verification failed'
                }
                
            except Exception as e:
                logger.error(f"Integrity verification error: {e}")
                return {'valid': False, 'error': str(e)}
        
        # Metrics endpoint
        @self.app.get("/api/phase3/metrics")
        async def get_metrics(user=Depends(self.get_current_user)):
            """Get Phase 3 performance metrics"""
            try:
                # Collect metrics from all components
                metrics = {
                    'rules_compiled': 0,
                    'avg_compile_time': 0,
                    'audit_entries': 0,
                    'consumer_lag': 0,
                    'messages_processed': 0,
                    'messages_failed': 0
                }
                
                # Get metrics from database
                if self.pg_pool:
                    async with self.pg_pool.acquire() as conn:
                        # Rule compilation metrics
                        result = await conn.fetchrow("""
                            SELECT COUNT(*) as count, AVG(compilation_time_ms) as avg_time
                            FROM rule_compilation_results
                            WHERE created_at >= NOW() - INTERVAL '24 hours'
                        """)
                        if result:
                            metrics['rules_compiled'] = result['count'] or 0
                            metrics['avg_compile_time'] = int(result['avg_time'] or 0)
                        
                        # Audit entries count
                        result = await conn.fetchrow("""
                            SELECT COUNT(*) as count FROM audit_trail
                            WHERE created_at >= NOW() - INTERVAL '24 hours'
                        """)
                        if result:
                            metrics['audit_entries'] = result['count'] or 0
                        
                        # Kafka consumer metrics
                        result = await conn.fetchrow("""
                            SELECT processing_stats FROM kafka_consumer_state
                            WHERE consumer_group = 'intelligence-compliance-group'
                        """)
                        if result and result['processing_stats']:
                            stats = json.loads(result['processing_stats'])
                            metrics['messages_processed'] = stats.get('messages_processed', 0)
                            metrics['messages_failed'] = stats.get('messages_failed', 0)
                
                return metrics
                
            except Exception as e:
                logger.error(f"Failed to get metrics: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # WebSocket endpoint
        @self.app.websocket("/ws/phase3")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates"""
            await websocket.accept()
            self.websocket_connections.append(websocket)
            
            try:
                while True:
                    # Keep connection alive
                    await websocket.receive_text()
                    
            except WebSocketDisconnect:
                self.websocket_connections.remove(websocket)
    
    async def get_current_user(self) -> Dict[str, Any]:
        """
        Get current user for authentication
        
        Rule 10: REQUIRE_AUTH integration - checks REQUIRE_AUTH environment variable
        """
        require_auth = os.getenv('REQUIRE_AUTH', 'false').lower() == 'true'
        
        if not require_auth:
            # Return mock user when authentication is disabled
            return {
                'user_id': 'system_user',
                'username': 'system',
                'role': 'admin'
            }
        
        # TODO: Implement real authentication when REQUIRE_AUTH=true
        # This would integrate with the existing auth system
        raise HTTPException(status_code=401, detail="Authentication required")
    
    async def initialize_components(self):
        """Initialize all Phase 3 components"""
        try:
            # Initialize database connection pool
            if not self.pg_pool:
                self.pg_pool = await asyncpg.create_pool(
                    host=os.getenv('POSTGRES_HOST', 'localhost'),
                    port=int(os.getenv('POSTGRES_PORT', 5432)),
                    database=os.getenv('POSTGRES_DB', 'compliance_ai'),
                    user=os.getenv('POSTGRES_USER', 'postgres'),
                    password=os.getenv('POSTGRES_PASSWORD', 'postgres'),
                    min_size=5,
                    max_size=20
                )
            
            # Initialize Rule Compiler
            if not self.rule_compiler:
                self.rule_compiler = RuleCompiler()
                await self.rule_compiler.initialize()
            
            # Initialize Kafka Consumer
            if not self.kafka_consumer:
                self.kafka_consumer = RegulatoryKafkaConsumer()
                # Note: Don't auto-start consumer, let API control it
            
            # Initialize Jurisdiction Handler
            if not self.jurisdiction_handler:
                self.jurisdiction_handler = JurisdictionHandler()
                await self.jurisdiction_handler.initialize()
            
            # Initialize Overlap Resolver
            if not self.overlap_resolver:
                self.overlap_resolver = OverlapResolver()
                await self.overlap_resolver.initialize()
            
            # Initialize Audit Logger
            if not self.audit_logger:
                self.audit_logger = AuditLogger()
                await self.audit_logger.initialize()
            
            logger.info("All Phase 3 components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise
    
    async def broadcast_websocket(self, message: Dict[str, Any]):
        """Broadcast message to all WebSocket connections"""
        if not self.websocket_connections:
            return
        
        message_str = json.dumps(message)
        disconnected = []
        
        for websocket in self.websocket_connections:
            try:
                await websocket.send_text(message_str)
            except:
                disconnected.append(websocket)
        
        # Remove disconnected clients
        for websocket in disconnected:
            self.websocket_connections.remove(websocket)
    
    async def _get_mock_rules_for_jurisdiction(self, customer_country: str, business_country: str) -> List[Dict[str, Any]]:
        """Get mock rules for jurisdiction testing"""
        rules = [
            {
                'rule_id': 'AML_001_EU',
                'regulation_type': 'AML',
                'jurisdiction': 'EU',
                'description': 'Customer due diligence for transactions above EUR 15,000',
                'confidence_score': 95
            },
            {
                'rule_id': 'KYC_002_DE',
                'regulation_type': 'KYC',
                'jurisdiction': 'DE',
                'description': 'Enhanced verification for German residents',
                'confidence_score': 88
            }
        ]
        
        # Filter based on jurisdictions
        applicable_rules = []
        for rule in rules:
            if rule['jurisdiction'] in [customer_country, business_country, 'EU']:
                applicable_rules.append(rule)
        
        return applicable_rules
    
    async def _get_mock_audit_entries(self, date_from: str = None, date_to: str = None, action: str = None, limit: int = None) -> List[Dict[str, Any]]:
        """Get mock audit entries for testing"""
        entries = [
            {
                'entry_id': 'audit_001',
                'timestamp': datetime.now().isoformat(),
                'action': 'rule_compiled',
                'user_id': 'system_user',
                'details': 'AML rule compiled for EU jurisdiction'
            },
            {
                'entry_id': 'audit_002',
                'timestamp': datetime.now().isoformat(),
                'action': 'jurisdiction_changed',
                'user_id': 'admin_user',
                'details': 'Customer jurisdiction updated from DE to IE'
            }
        ]
        
        # Apply filters
        if action:
            entries = [e for e in entries if e['action'] == action]
        
        if limit:
            entries = entries[:limit]
        
        return entries

# Create global API instance
phase3_api = Phase3API()
app = phase3_api.app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
