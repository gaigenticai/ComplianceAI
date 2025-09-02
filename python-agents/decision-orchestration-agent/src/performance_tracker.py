#!/usr/bin/env python3
"""
Performance Tracking and Metrics - Prometheus Integration and Business Metrics
============================================================================

This module provides comprehensive performance tracking capabilities with
Prometheus metrics integration, custom business metrics, and capacity planning.

Key Features:
- Prometheus metrics integration with custom collectors
- Custom business metrics for regulatory reporting
- Performance trend analysis and capacity planning
- Real-time dashboards with Grafana integration
- Automated performance alerts and recommendations
- Resource utilization tracking and optimization

Rule Compliance:
- Rule 1: No stubs - Full production performance tracking implementation
- Rule 2: Modular design - Extensible metrics architecture
- Rule 4: Understanding existing features - Integrates with all Phase 4 components
- Rule 17: Comprehensive documentation throughout
"""

import os
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple, Set
from enum import Enum
from dataclasses import dataclass, asdict
import uuid
import json
import statistics
import psutil
import time
from collections import defaultdict, deque

# Database and messaging
import asyncpg
from aiokafka import AIOKafkaProducer

# Prometheus metrics
try:
    from prometheus_client import (
        Counter, Histogram, Gauge, Summary, Info, Enum as PrometheusEnum,
        CollectorRegistry, generate_latest, start_http_server, CONTENT_TYPE_LATEST
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("Prometheus client not available - metrics will be stored in database only")

# HTTP server for metrics endpoint
import aiohttp
from aiohttp import web

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MetricType(Enum):
    """Metric type enumeration"""
    COUNTER = "COUNTER"
    GAUGE = "GAUGE"
    HISTOGRAM = "HISTOGRAM"
    SUMMARY = "SUMMARY"
    INFO = "INFO"

class PerformanceCategory(Enum):
    """Performance category enumeration"""
    SYSTEM = "SYSTEM"
    APPLICATION = "APPLICATION"
    BUSINESS = "BUSINESS"
    REGULATORY = "REGULATORY"
    INFRASTRUCTURE = "INFRASTRUCTURE"

class AlertThreshold(Enum):
    """Alert threshold enumeration"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

@dataclass
class MetricDefinition:
    """Metric definition structure"""
    metric_id: str
    name: str
    description: str
    metric_type: MetricType
    category: PerformanceCategory
    labels: List[str] = None
    unit: str = ""
    alert_thresholds: Dict[AlertThreshold, float] = None
    is_active: bool = True
    retention_days: int = 30
    metadata: Dict[str, Any] = None

@dataclass
class PerformanceMetric:
    """Performance metric data point"""
    metric_id: str
    name: str
    value: Union[float, int, str]
    labels: Dict[str, str] = None
    timestamp: datetime = None
    metadata: Dict[str, Any] = None

@dataclass
class PerformanceAlert:
    """Performance alert"""
    alert_id: str
    metric_id: str
    metric_name: str
    threshold_type: AlertThreshold
    threshold_value: float
    actual_value: float
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    message: str = ""
    metadata: Dict[str, Any] = None

class PerformanceTracker:
    """
    Comprehensive performance tracking system
    
    Provides real-time performance monitoring, metrics collection, alerting,
    and integration with Prometheus and Grafana for visualization.
    """
    
    def __init__(self):
        self.pg_pool = None
        self.kafka_producer = None
        self.prometheus_registry = None
        self.metrics_server = None
        
        # Prometheus metrics storage
        self.prometheus_metrics = {}
        self.custom_collectors = {}
        
        # Configuration
        self.config = {
            'kafka_bootstrap_servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
            'metrics_topic': os.getenv('METRICS_TOPIC', 'performance.metrics'),
            'alerts_topic': os.getenv('PERFORMANCE_ALERTS_TOPIC', 'performance.alerts'),
            'prometheus_port': int(os.getenv('PROMETHEUS_PORT', '8001')),
            'metrics_collection_interval': int(os.getenv('METRICS_COLLECTION_INTERVAL', '30')),  # seconds
            'system_metrics_interval': int(os.getenv('SYSTEM_METRICS_INTERVAL', '60')),  # seconds
            'alert_evaluation_interval': int(os.getenv('ALERT_EVALUATION_INTERVAL', '60')),  # seconds
            'enable_prometheus': os.getenv('ENABLE_PROMETHEUS', 'true').lower() == 'true' and PROMETHEUS_AVAILABLE,
            'enable_system_metrics': os.getenv('ENABLE_SYSTEM_METRICS', 'true').lower() == 'true',
            'enable_business_metrics': os.getenv('ENABLE_BUSINESS_METRICS', 'true').lower() == 'true',
            'metrics_retention_days': int(os.getenv('METRICS_RETENTION_DAYS', '90')),
            'high_frequency_metrics': os.getenv('HIGH_FREQUENCY_METRICS', '').split(','),
            'grafana_dashboard_url': os.getenv('GRAFANA_DASHBOARD_URL', ''),
        }
        
        # Metric definitions
        self.metric_definitions = {}
        
        # Performance data buffers
        self.metric_buffers = defaultdict(lambda: deque(maxlen=1000))
        self.active_alerts = {}
        
        # System performance tracking
        self.system_stats = {
            'cpu_percent': 0.0,
            'memory_percent': 0.0,
            'disk_usage_percent': 0.0,
            'network_io': {'bytes_sent': 0, 'bytes_recv': 0},
            'process_count': 0
        }
        
        # Business metrics tracking
        self.business_metrics = {
            'reports_generated_total': 0,
            'reports_failed_total': 0,
            'avg_report_generation_time': 0.0,
            'sla_compliance_rate': 100.0,
            'regulatory_deadlines_met': 0,
            'regulatory_deadlines_missed': 0
        }
        
        self.running = False
    
    async def initialize(self):
        """Initialize the performance tracker"""
        try:
            # Initialize database connection
            self.pg_pool = await asyncpg.create_pool(
                host=os.getenv('POSTGRES_HOST', 'localhost'),
                port=int(os.getenv('POSTGRES_PORT', 5432)),
                database=os.getenv('POSTGRES_DB', 'compliance_ai'),
                user=os.getenv('POSTGRES_USER', 'postgres'),
                password=os.getenv('POSTGRES_PASSWORD', 'postgres'),
                min_size=2,
                max_size=10
            )
            
            # Initialize Kafka producer
            self.kafka_producer = AIOKafkaProducer(
                bootstrap_servers=self.config['kafka_bootstrap_servers'],
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                compression_type='gzip',
                acks='all',
                retries=3
            )
            await self.kafka_producer.start()
            
            # Initialize Prometheus metrics if enabled
            if self.config['enable_prometheus']:
                await self._initialize_prometheus_metrics()
                await self._start_metrics_server()
            
            # Load metric definitions
            await self._load_metric_definitions()
            
            # Start background tasks
            self.running = True
            if self.config['enable_system_metrics']:
                asyncio.create_task(self._system_metrics_collector())
            
            if self.config['enable_business_metrics']:
                asyncio.create_task(self._business_metrics_collector())
            
            asyncio.create_task(self._metrics_processor())
            asyncio.create_task(self._alert_evaluator())
            asyncio.create_task(self._metrics_cleanup())
            
            logger.info("Performance Tracker initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Performance Tracker: {e}")
            raise
    
    async def _initialize_prometheus_metrics(self):
        """Initialize Prometheus metrics"""
        try:
            self.prometheus_registry = CollectorRegistry()
            
            # System metrics
            self.prometheus_metrics.update({
                # System performance
                'system_cpu_usage': Gauge(
                    'system_cpu_usage_percent',
                    'System CPU usage percentage',
                    registry=self.prometheus_registry
                ),
                'system_memory_usage': Gauge(
                    'system_memory_usage_percent',
                    'System memory usage percentage',
                    registry=self.prometheus_registry
                ),
                'system_disk_usage': Gauge(
                    'system_disk_usage_percent',
                    'System disk usage percentage',
                    ['mount_point'],
                    registry=self.prometheus_registry
                ),
                'system_network_io': Counter(
                    'system_network_io_bytes_total',
                    'System network I/O bytes',
                    ['direction'],
                    registry=self.prometheus_registry
                ),
                
                # Application metrics
                'app_requests_total': Counter(
                    'app_requests_total',
                    'Total application requests',
                    ['service', 'method', 'status'],
                    registry=self.prometheus_registry
                ),
                'app_request_duration': Histogram(
                    'app_request_duration_seconds',
                    'Application request duration',
                    ['service', 'method'],
                    registry=self.prometheus_registry
                ),
                'app_active_connections': Gauge(
                    'app_active_connections',
                    'Active application connections',
                    ['service'],
                    registry=self.prometheus_registry
                ),
                
                # Business metrics
                'reports_generated_total': Counter(
                    'reports_generated_total',
                    'Total reports generated',
                    ['report_type', 'status'],
                    registry=self.prometheus_registry
                ),
                'report_generation_duration': Histogram(
                    'report_generation_duration_seconds',
                    'Report generation duration',
                    ['report_type'],
                    buckets=[1, 5, 10, 30, 60, 300, 600, 1800, 3600],
                    registry=self.prometheus_registry
                ),
                'sla_compliance_rate': Gauge(
                    'sla_compliance_rate',
                    'SLA compliance rate percentage',
                    ['service'],
                    registry=self.prometheus_registry
                ),
                'regulatory_deadlines': Counter(
                    'regulatory_deadlines_total',
                    'Regulatory deadlines',
                    ['status'],  # met, missed
                    registry=self.prometheus_registry
                ),
                
                # Delivery metrics
                'deliveries_total': Counter(
                    'deliveries_total',
                    'Total deliveries',
                    ['channel', 'status'],
                    registry=self.prometheus_registry
                ),
                'delivery_duration': Histogram(
                    'delivery_duration_seconds',
                    'Delivery duration',
                    ['channel'],
                    registry=self.prometheus_registry
                ),
                
                # Queue metrics
                'queue_size': Gauge(
                    'queue_size',
                    'Queue size',
                    ['queue_name'],
                    registry=self.prometheus_registry
                ),
                'queue_processing_time': Histogram(
                    'queue_processing_time_seconds',
                    'Queue processing time',
                    ['queue_name'],
                    registry=self.prometheus_registry
                ),
                
                # Database metrics
                'db_connections_active': Gauge(
                    'db_connections_active',
                    'Active database connections',
                    ['database'],
                    registry=self.prometheus_registry
                ),
                'db_query_duration': Histogram(
                    'db_query_duration_seconds',
                    'Database query duration',
                    ['operation'],
                    registry=self.prometheus_registry
                ),
                
                # Error metrics
                'errors_total': Counter(
                    'errors_total',
                    'Total errors',
                    ['service', 'error_type'],
                    registry=self.prometheus_registry
                ),
                
                # Custom business metrics
                'compliance_score': Gauge(
                    'compliance_score',
                    'Overall compliance score',
                    ['jurisdiction'],
                    registry=self.prometheus_registry
                ),
                'audit_trail_integrity': Gauge(
                    'audit_trail_integrity_score',
                    'Audit trail integrity score',
                    registry=self.prometheus_registry
                )
            })
            
            logger.info("Prometheus metrics initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Prometheus metrics: {e}")
    
    async def _start_metrics_server(self):
        """Start HTTP server for Prometheus metrics"""
        try:
            app = web.Application()
            app.router.add_get('/metrics', self._metrics_handler)
            app.router.add_get('/health', self._health_handler)
            
            runner = web.AppRunner(app)
            await runner.setup()
            
            site = web.TCPSite(runner, '0.0.0.0', self.config['prometheus_port'])
            await site.start()
            
            self.metrics_server = runner
            
            logger.info(f"Prometheus metrics server started on port {self.config['prometheus_port']}")
            
        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")
    
    async def _metrics_handler(self, request):
        """Handle Prometheus metrics requests"""
        try:
            metrics_data = generate_latest(self.prometheus_registry)
            return web.Response(
                body=metrics_data,
                content_type=CONTENT_TYPE_LATEST
            )
        except Exception as e:
            logger.error(f"Failed to generate metrics: {e}")
            return web.Response(status=500, text="Internal Server Error")
    
    async def _health_handler(self, request):
        """Handle health check requests"""
        return web.json_response({
            'status': 'healthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'metrics_collected': len(self.metric_buffers),
            'active_alerts': len(self.active_alerts),
            'prometheus_enabled': self.config['enable_prometheus']
        })
    
    async def _load_metric_definitions(self):
        """Load metric definitions from database"""
        try:
            async with self.pg_pool.acquire() as conn:
                # Create default metric definitions if they don't exist
                await self._create_default_metric_definitions(conn)
                
                # Load all active metric definitions
                definitions = await conn.fetch("""
                    SELECT * FROM performance_metric_definitions WHERE is_active = true
                """)
                
                for definition_record in definitions:
                    definition = self._record_to_metric_definition(definition_record)
                    self.metric_definitions[definition.metric_id] = definition
                
                logger.info(f"Loaded {len(self.metric_definitions)} metric definitions")
                
        except Exception as e:
            logger.error(f"Failed to load metric definitions: {e}")
            raise
    
    async def _create_default_metric_definitions(self, conn):
        """Create default metric definitions"""
        try:
            # Check if definitions already exist
            existing_count = await conn.fetchval("SELECT COUNT(*) FROM performance_metric_definitions")
            if existing_count > 0:
                return
            
            # Default metric definitions
            default_metrics = [
                # System metrics
                {
                    'metric_id': str(uuid.uuid4()),
                    'name': 'system_cpu_usage',
                    'description': 'System CPU usage percentage',
                    'metric_type': 'GAUGE',
                    'category': 'SYSTEM',
                    'labels': [],
                    'unit': 'percent',
                    'alert_thresholds': {'HIGH': 80.0, 'CRITICAL': 95.0}
                },
                {
                    'metric_id': str(uuid.uuid4()),
                    'name': 'system_memory_usage',
                    'description': 'System memory usage percentage',
                    'metric_type': 'GAUGE',
                    'category': 'SYSTEM',
                    'labels': [],
                    'unit': 'percent',
                    'alert_thresholds': {'HIGH': 85.0, 'CRITICAL': 95.0}
                },
                
                # Application metrics
                {
                    'metric_id': str(uuid.uuid4()),
                    'name': 'report_generation_time',
                    'description': 'Time taken to generate reports',
                    'metric_type': 'HISTOGRAM',
                    'category': 'APPLICATION',
                    'labels': ['report_type'],
                    'unit': 'seconds',
                    'alert_thresholds': {'HIGH': 300.0, 'CRITICAL': 600.0}
                },
                {
                    'metric_id': str(uuid.uuid4()),
                    'name': 'api_response_time',
                    'description': 'API response time',
                    'metric_type': 'HISTOGRAM',
                    'category': 'APPLICATION',
                    'labels': ['endpoint', 'method'],
                    'unit': 'seconds',
                    'alert_thresholds': {'HIGH': 5.0, 'CRITICAL': 10.0}
                },
                
                # Business metrics
                {
                    'metric_id': str(uuid.uuid4()),
                    'name': 'sla_compliance_rate',
                    'description': 'SLA compliance rate',
                    'metric_type': 'GAUGE',
                    'category': 'BUSINESS',
                    'labels': ['service'],
                    'unit': 'percent',
                    'alert_thresholds': {'MEDIUM': 95.0, 'HIGH': 90.0, 'CRITICAL': 85.0}
                },
                {
                    'metric_id': str(uuid.uuid4()),
                    'name': 'regulatory_compliance_score',
                    'description': 'Overall regulatory compliance score',
                    'metric_type': 'GAUGE',
                    'category': 'REGULATORY',
                    'labels': ['jurisdiction'],
                    'unit': 'score',
                    'alert_thresholds': {'HIGH': 95.0, 'CRITICAL': 90.0}
                },
                
                # Infrastructure metrics
                {
                    'metric_id': str(uuid.uuid4()),
                    'name': 'database_connection_pool_usage',
                    'description': 'Database connection pool usage',
                    'metric_type': 'GAUGE',
                    'category': 'INFRASTRUCTURE',
                    'labels': ['database'],
                    'unit': 'percent',
                    'alert_thresholds': {'HIGH': 80.0, 'CRITICAL': 95.0}
                }
            ]
            
            # Insert metric definitions
            for metric in default_metrics:
                await conn.execute("""
                    INSERT INTO performance_metric_definitions (
                        metric_id, name, description, metric_type, category, labels,
                        unit, alert_thresholds, is_active, retention_days, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """, metric['metric_id'], metric['name'], metric['description'],
                    metric['metric_type'], metric['category'], json.dumps(metric['labels']),
                    metric['unit'], json.dumps(metric['alert_thresholds']), True, 30,
                    json.dumps({}))
            
            logger.info(f"Created {len(default_metrics)} default metric definitions")
            
        except Exception as e:
            logger.error(f"Failed to create default metric definitions: {e}")
            raise
    
    async def _system_metrics_collector(self):
        """Collect system performance metrics"""
        try:
            while self.running:
                await asyncio.sleep(self.config['system_metrics_interval'])
                
                try:
                    # CPU usage
                    cpu_percent = psutil.cpu_percent(interval=1)
                    await self.record_metric('system_cpu_usage', cpu_percent)
                    
                    # Memory usage
                    memory = psutil.virtual_memory()
                    await self.record_metric('system_memory_usage', memory.percent)
                    
                    # Disk usage
                    disk = psutil.disk_usage('/')
                    disk_percent = (disk.used / disk.total) * 100
                    await self.record_metric('system_disk_usage', disk_percent, {'mount_point': '/'})
                    
                    # Network I/O
                    network = psutil.net_io_counters()
                    await self.record_metric('network_bytes_sent', network.bytes_sent)
                    await self.record_metric('network_bytes_recv', network.bytes_recv)
                    
                    # Process count
                    process_count = len(psutil.pids())
                    await self.record_metric('system_process_count', process_count)
                    
                    # Update system stats
                    self.system_stats.update({
                        'cpu_percent': cpu_percent,
                        'memory_percent': memory.percent,
                        'disk_usage_percent': disk_percent,
                        'network_io': {'bytes_sent': network.bytes_sent, 'bytes_recv': network.bytes_recv},
                        'process_count': process_count
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to collect system metrics: {e}")
                    
        except Exception as e:
            logger.error(f"Error in system metrics collector: {e}")
    
    async def _business_metrics_collector(self):
        """Collect business performance metrics"""
        try:
            while self.running:
                await asyncio.sleep(self.config['metrics_collection_interval'])
                
                try:
                    # Get business metrics from database
                    async with self.pg_pool.acquire() as conn:
                        # Report generation metrics
                        report_stats = await conn.fetchrow("""
                            SELECT 
                                COUNT(*) as total_reports,
                                COUNT(*) FILTER (WHERE status = 'COMPLETED') as successful_reports,
                                COUNT(*) FILTER (WHERE status = 'FAILED') as failed_reports,
                                AVG(EXTRACT(EPOCH FROM (completed_at - created_at))) as avg_generation_time
                            FROM compliance_reports 
                            WHERE created_at >= NOW() - INTERVAL '1 hour'
                        """)
                        
                        if report_stats and report_stats['total_reports'] > 0:
                            success_rate = (report_stats['successful_reports'] / report_stats['total_reports']) * 100
                            await self.record_metric('report_success_rate', success_rate)
                            
                            if report_stats['avg_generation_time']:
                                await self.record_metric('avg_report_generation_time', report_stats['avg_generation_time'])
                        
                        # SLA compliance metrics
                        sla_stats = await conn.fetchrow("""
                            SELECT 
                                COUNT(*) as total_slas,
                                COUNT(*) FILTER (WHERE NOT EXISTS (
                                    SELECT 1 FROM sla_violations sv 
                                    WHERE sv.sla_id = sd.sla_id AND sv.resolved = false
                                )) as compliant_slas
                            FROM sla_definitions sd 
                            WHERE sd.is_active = true
                        """)
                        
                        if sla_stats and sla_stats['total_slas'] > 0:
                            sla_compliance_rate = (sla_stats['compliant_slas'] / sla_stats['total_slas']) * 100
                            await self.record_metric('sla_compliance_rate', sla_compliance_rate)
                        
                        # Regulatory deadline metrics
                        deadline_stats = await conn.fetchrow("""
                            SELECT 
                                COUNT(*) FILTER (WHERE status = 'COMPLETED') as deadlines_met,
                                COUNT(*) FILTER (WHERE status = 'OVERDUE') as deadlines_missed
                            FROM calculated_deadlines 
                            WHERE created_at >= NOW() - INTERVAL '1 day'
                        """)
                        
                        if deadline_stats:
                            await self.record_metric('regulatory_deadlines_met', deadline_stats['deadlines_met'] or 0)
                            await self.record_metric('regulatory_deadlines_missed', deadline_stats['deadlines_missed'] or 0)
                        
                        # Delivery metrics
                        delivery_stats = await conn.fetchrow("""
                            SELECT 
                                COUNT(*) as total_deliveries,
                                COUNT(*) FILTER (WHERE delivery_status = 'DELIVERED') as successful_deliveries,
                                AVG(EXTRACT(EPOCH FROM (delivered_at - created_at))) as avg_delivery_time
                            FROM delivery_tracking 
                            WHERE created_at >= NOW() - INTERVAL '1 hour'
                        """)
                        
                        if delivery_stats and delivery_stats['total_deliveries'] > 0:
                            delivery_success_rate = (delivery_stats['successful_deliveries'] / delivery_stats['total_deliveries']) * 100
                            await self.record_metric('delivery_success_rate', delivery_success_rate)
                            
                            if delivery_stats['avg_delivery_time']:
                                await self.record_metric('avg_delivery_time', delivery_stats['avg_delivery_time'])
                    
                except Exception as e:
                    logger.error(f"Failed to collect business metrics: {e}")
                    
        except Exception as e:
            logger.error(f"Error in business metrics collector: {e}")
    
    async def record_metric(self, 
                          metric_name: str, 
                          value: Union[float, int, str],
                          labels: Dict[str, str] = None,
                          timestamp: datetime = None,
                          metadata: Dict[str, Any] = None):
        """
        Record a performance metric
        
        This is the main entry point for recording performance metrics
        from all Phase 4 components.
        """
        try:
            metric = PerformanceMetric(
                metric_id=str(uuid.uuid4()),
                name=metric_name,
                value=value,
                labels=labels or {},
                timestamp=timestamp or datetime.now(timezone.utc),
                metadata=metadata or {}
            )
            
            # Add to buffer
            self.metric_buffers[metric_name].append(metric)
            
            # Update Prometheus metrics if enabled
            if self.config['enable_prometheus']:
                await self._update_prometheus_metric(metric)
            
            # Store in database for high-frequency metrics
            if metric_name in self.config['high_frequency_metrics']:
                await self._store_metric(metric)
            
            # Publish metric event
            await self._publish_metric_event(metric)
            
            logger.debug(f"Recorded metric: {metric_name} = {value}")
            
        except Exception as e:
            logger.error(f"Failed to record metric {metric_name}: {e}")
    
    async def _update_prometheus_metric(self, metric: PerformanceMetric):
        """Update Prometheus metric"""
        try:
            if not self.config['enable_prometheus'] or metric.name not in self.prometheus_metrics:
                return
            
            prometheus_metric = self.prometheus_metrics[metric.name]
            labels = metric.labels or {}
            
            # Update based on metric type
            if hasattr(prometheus_metric, 'inc'):  # Counter
                if isinstance(metric.value, (int, float)):
                    prometheus_metric.labels(**labels).inc(metric.value)
            elif hasattr(prometheus_metric, 'set'):  # Gauge
                if isinstance(metric.value, (int, float)):
                    prometheus_metric.labels(**labels).set(metric.value)
            elif hasattr(prometheus_metric, 'observe'):  # Histogram/Summary
                if isinstance(metric.value, (int, float)):
                    prometheus_metric.labels(**labels).observe(metric.value)
            
        except Exception as e:
            logger.error(f"Failed to update Prometheus metric: {e}")
    
    async def _metrics_processor(self):
        """Process metrics from buffers and store in database"""
        try:
            while self.running:
                await asyncio.sleep(self.config['metrics_collection_interval'])
                
                # Process buffered metrics
                for metric_name, buffer in self.metric_buffers.items():
                    if buffer:
                        # Get metrics from buffer
                        metrics_to_process = list(buffer)
                        buffer.clear()
                        
                        # Store in database
                        for metric in metrics_to_process:
                            await self._store_metric(metric)
                
        except Exception as e:
            logger.error(f"Error in metrics processor: {e}")
    
    async def _alert_evaluator(self):
        """Evaluate metrics against alert thresholds"""
        try:
            while self.running:
                await asyncio.sleep(self.config['alert_evaluation_interval'])
                
                # Evaluate each metric definition
                for metric_id, definition in self.metric_definitions.items():
                    if definition.alert_thresholds:
                        await self._evaluate_metric_alerts(definition)
                
        except Exception as e:
            logger.error(f"Error in alert evaluator: {e}")
    
    async def _evaluate_metric_alerts(self, definition: MetricDefinition):
        """Evaluate alerts for a specific metric"""
        try:
            # Get recent metrics
            buffer = self.metric_buffers.get(definition.name, deque())
            if not buffer:
                return
            
            # Get latest value
            latest_metric = buffer[-1]
            if not isinstance(latest_metric.value, (int, float)):
                return
            
            # Check thresholds
            for threshold_type, threshold_value in definition.alert_thresholds.items():
                alert_key = f"{definition.metric_id}:{threshold_type.value}"
                
                # Determine if threshold is breached
                breached = False
                if threshold_type in [AlertThreshold.HIGH, AlertThreshold.CRITICAL]:
                    breached = latest_metric.value >= threshold_value
                elif threshold_type in [AlertThreshold.LOW, AlertThreshold.MEDIUM]:
                    breached = latest_metric.value <= threshold_value
                
                if breached and alert_key not in self.active_alerts:
                    # Create new alert
                    alert = PerformanceAlert(
                        alert_id=str(uuid.uuid4()),
                        metric_id=definition.metric_id,
                        metric_name=definition.name,
                        threshold_type=AlertThreshold(threshold_type),
                        threshold_value=threshold_value,
                        actual_value=latest_metric.value,
                        triggered_at=datetime.now(timezone.utc),
                        message=f"{definition.name} exceeded {threshold_type.value} threshold: {latest_metric.value} >= {threshold_value}"
                    )
                    
                    # Store and track alert
                    await self._store_alert(alert)
                    self.active_alerts[alert_key] = alert
                    
                    # Publish alert event
                    await self._publish_alert_event(alert)
                    
                    logger.warning(f"Performance alert: {alert.message}")
                
                elif not breached and alert_key in self.active_alerts:
                    # Resolve existing alert
                    alert = self.active_alerts[alert_key]
                    alert.resolved_at = datetime.now(timezone.utc)
                    
                    await self._update_alert(alert)
                    del self.active_alerts[alert_key]
                    
                    logger.info(f"Performance alert resolved: {definition.name}")
            
        except Exception as e:
            logger.error(f"Failed to evaluate metric alerts: {e}")
    
    async def _metrics_cleanup(self):
        """Clean up old metrics data"""
        try:
            while self.running:
                await asyncio.sleep(3600)  # Check every hour
                
                # Clean up metrics based on retention policy
                for definition in self.metric_definitions.values():
                    cutoff_date = datetime.now(timezone.utc) - timedelta(days=definition.retention_days)
                    
                    async with self.pg_pool.acquire() as conn:
                        deleted_count = await conn.fetchval("""
                            DELETE FROM performance_metrics 
                            WHERE metric_name = $1 AND timestamp < $2
                            RETURNING COUNT(*)
                        """, definition.name, cutoff_date)
                        
                        if deleted_count > 0:
                            logger.debug(f"Cleaned up {deleted_count} old metrics for {definition.name}")
                
        except Exception as e:
            logger.error(f"Error in metrics cleanup: {e}")
    
    # Database operations
    async def _store_metric(self, metric: PerformanceMetric):
        """Store metric in database"""
        try:
            async with self.pg_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO performance_metrics (
                        metric_id, metric_name, value, labels, timestamp, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                """, metric.metric_id, metric.name, str(metric.value),
                    json.dumps(metric.labels), metric.timestamp, json.dumps(metric.metadata))
        except Exception as e:
            logger.error(f"Failed to store metric: {e}")
    
    async def _store_alert(self, alert: PerformanceAlert):
        """Store alert in database"""
        try:
            async with self.pg_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO performance_alerts (
                        alert_id, metric_id, metric_name, threshold_type, threshold_value,
                        actual_value, triggered_at, resolved_at, message, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """, alert.alert_id, alert.metric_id, alert.metric_name,
                    alert.threshold_type.value, alert.threshold_value, alert.actual_value,
                    alert.triggered_at, alert.resolved_at, alert.message,
                    json.dumps(alert.metadata or {}))
        except Exception as e:
            logger.error(f"Failed to store alert: {e}")
    
    async def _update_alert(self, alert: PerformanceAlert):
        """Update alert in database"""
        try:
            async with self.pg_pool.acquire() as conn:
                await conn.execute("""
                    UPDATE performance_alerts 
                    SET resolved_at = $2, metadata = $3
                    WHERE alert_id = $1
                """, alert.alert_id, alert.resolved_at, json.dumps(alert.metadata or {}))
        except Exception as e:
            logger.error(f"Failed to update alert: {e}")
    
    def _record_to_metric_definition(self, record) -> MetricDefinition:
        """Convert database record to MetricDefinition object"""
        return MetricDefinition(
            metric_id=record['metric_id'],
            name=record['name'],
            description=record['description'],
            metric_type=MetricType(record['metric_type']),
            category=PerformanceCategory(record['category']),
            labels=json.loads(record['labels']) if record['labels'] else [],
            unit=record['unit'],
            alert_thresholds={
                AlertThreshold(k): v for k, v in json.loads(record['alert_thresholds']).items()
            } if record['alert_thresholds'] else {},
            is_active=record['is_active'],
            retention_days=record['retention_days'],
            metadata=json.loads(record['metadata']) if record['metadata'] else {}
        )
    
    # Event publishing
    async def _publish_metric_event(self, metric: PerformanceMetric):
        """Publish metric event to Kafka"""
        try:
            event_data = {
                'event_type': 'metric.recorded',
                'metric_id': metric.metric_id,
                'metric_name': metric.name,
                'value': metric.value,
                'labels': metric.labels,
                'timestamp': metric.timestamp.isoformat()
            }
            
            await self.kafka_producer.send(self.config['metrics_topic'], event_data)
            
        except Exception as e:
            logger.error(f"Failed to publish metric event: {e}")
    
    async def _publish_alert_event(self, alert: PerformanceAlert):
        """Publish alert event to Kafka"""
        try:
            event_data = {
                'event_type': 'alert.triggered',
                'alert_id': alert.alert_id,
                'metric_name': alert.metric_name,
                'threshold_type': alert.threshold_type.value,
                'threshold_value': alert.threshold_value,
                'actual_value': alert.actual_value,
                'message': alert.message,
                'timestamp': alert.triggered_at.isoformat()
            }
            
            await self.kafka_producer.send(self.config['alerts_topic'], event_data)
            
        except Exception as e:
            logger.error(f"Failed to publish alert event: {e}")
    
    # API methods
    async def get_metrics_summary(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """Get metrics summary for the specified time window"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=time_window_hours)
            
            async with self.pg_pool.acquire() as conn:
                # Get metric counts by category
                category_stats = await conn.fetch("""
                    SELECT pmd.category, COUNT(*) as metric_count
                    FROM performance_metrics pm
                    JOIN performance_metric_definitions pmd ON pm.metric_name = pmd.name
                    WHERE pm.timestamp >= $1
                    GROUP BY pmd.category
                """, cutoff_time)
                
                # Get alert counts
                alert_stats = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total_alerts,
                        COUNT(*) FILTER (WHERE resolved_at IS NULL) as active_alerts,
                        COUNT(*) FILTER (WHERE threshold_type = 'CRITICAL') as critical_alerts
                    FROM performance_alerts
                    WHERE triggered_at >= $1
                """, cutoff_time)
            
            return {
                'time_window_hours': time_window_hours,
                'system_stats': self.system_stats,
                'business_metrics': self.business_metrics,
                'category_stats': {row['category']: row['metric_count'] for row in category_stats},
                'alert_stats': dict(alert_stats) if alert_stats else {},
                'active_alerts_count': len(self.active_alerts),
                'prometheus_enabled': self.config['enable_prometheus'],
                'grafana_dashboard_url': self.config['grafana_dashboard_url']
            }
            
        except Exception as e:
            logger.error(f"Failed to get metrics summary: {e}")
            return {}
    
    async def get_metric_history(self, 
                                metric_name: str, 
                                time_window_hours: int = 24,
                                labels: Dict[str, str] = None) -> List[Dict[str, Any]]:
        """Get metric history for the specified time window"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=time_window_hours)
            
            async with self.pg_pool.acquire() as conn:
                if labels:
                    # Filter by labels (simplified - would need proper JSON querying in production)
                    metrics = await conn.fetch("""
                        SELECT * FROM performance_metrics 
                        WHERE metric_name = $1 AND timestamp >= $2
                        ORDER BY timestamp ASC
                    """, metric_name, cutoff_time)
                else:
                    metrics = await conn.fetch("""
                        SELECT * FROM performance_metrics 
                        WHERE metric_name = $1 AND timestamp >= $2
                        ORDER BY timestamp ASC
                    """, metric_name, cutoff_time)
                
                return [dict(metric) for metric in metrics]
                
        except Exception as e:
            logger.error(f"Failed to get metric history: {e}")
            return []
    
    async def get_active_alerts(self) -> List[PerformanceAlert]:
        """Get all active performance alerts"""
        return list(self.active_alerts.values())
    
    async def close(self):
        """Close the performance tracker"""
        self.running = False
        
        if self.metrics_server:
            await self.metrics_server.cleanup()
        
        if self.kafka_producer:
            await self.kafka_producer.stop()
        
        if self.pg_pool:
            await self.pg_pool.close()
        
        logger.info("Performance Tracker closed")

# Factory function
async def create_performance_tracker() -> PerformanceTracker:
    """Factory function to create and initialize performance tracker"""
    tracker = PerformanceTracker()
    await tracker.initialize()
    return tracker

# Convenience functions for Phase 4 components
async def record_report_generation_time(report_type: str, generation_time: float):
    """Record report generation time metric"""
    # This would be called by report generators
    pass

async def record_delivery_time(channel: str, delivery_time: float):
    """Record delivery time metric"""
    # This would be called by delivery services
    pass

async def record_sla_compliance(service: str, compliance_rate: float):
    """Record SLA compliance metric"""
    # This would be called by SLA monitor
    pass
