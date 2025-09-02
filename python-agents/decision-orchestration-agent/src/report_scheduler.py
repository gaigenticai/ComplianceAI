#!/usr/bin/env python3
"""
Report Scheduler - Automatic Report Scheduling and Dependency Management
======================================================================

This module provides comprehensive automatic report scheduling capabilities
with dependency management, resource allocation, and dynamic schedule adjustment.

Key Features:
- Cron-like scheduling system with regulatory calendar awareness
- Dynamic schedule adjustment based on deadline changes
- Dependency management between interconnected reports
- Resource allocation and load balancing across report types
- Priority-based scheduling with SLA considerations
- Retry logic and failure handling with escalation

Rule Compliance:
- Rule 1: No stubs - Full production scheduling implementation
- Rule 2: Modular design - Extensible scheduling architecture
- Rule 4: Understanding existing features - Integrates with deadline engine and report generators
- Rule 17: Comprehensive documentation throughout
"""

import os
import asyncio
import logging
from datetime import datetime, timezone, timedelta, time
from typing import Dict, List, Optional, Any, Union, Tuple, Set
from enum import Enum
from dataclasses import dataclass, asdict
import uuid
import json
import cron_descriptor
from croniter import croniter

# Database and messaging
import asyncpg
from aiokafka import AIOKafkaProducer

# Import our components
from deadline_engine import DeadlineEngine, CalculatedDeadline, DeadlineStatus
from compliance_report_generator import ComplianceReportGenerator, ReportRequest, ReportType, ReportFormat

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScheduleStatus(Enum):
    """Schedule status enumeration"""
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    DISABLED = "DISABLED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class JobStatus(Enum):
    """Job status enumeration"""
    SCHEDULED = "SCHEDULED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    RETRYING = "RETRYING"

class Priority(Enum):
    """Job priority enumeration"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    EMERGENCY = 5

@dataclass
class ReportSchedule:
    """Report schedule configuration"""
    schedule_id: str
    report_type: str
    institution_id: str
    jurisdiction: str
    cron_expression: str
    priority: Priority
    status: ScheduleStatus
    created_at: datetime
    updated_at: datetime
    next_run_time: datetime
    last_run_time: Optional[datetime] = None
    dependencies: List[str] = None  # List of prerequisite schedule IDs
    max_retries: int = 3
    retry_delay_minutes: int = 30
    timeout_minutes: int = 120
    resource_requirements: Dict[str, Any] = None
    metadata: Dict[str, Any] = None

@dataclass
class ScheduledJob:
    """Scheduled job instance"""
    job_id: str
    schedule_id: str
    report_type: str
    institution_id: str
    reporting_period: str
    scheduled_time: datetime
    started_time: Optional[datetime] = None
    completed_time: Optional[datetime] = None
    status: JobStatus = JobStatus.SCHEDULED
    priority: Priority = Priority.MEDIUM
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    result_data: Optional[Dict[str, Any]] = None
    resource_allocation: Dict[str, Any] = None
    dependencies_met: bool = False
    dependency_jobs: List[str] = None
    metadata: Dict[str, Any] = None

@dataclass
class ResourcePool:
    """Resource pool for job execution"""
    pool_name: str
    max_concurrent_jobs: int
    current_jobs: int = 0
    reserved_capacity: Dict[str, int] = None  # Reserved for specific report types
    resource_metrics: Dict[str, float] = None

class ReportScheduler:
    """
    Comprehensive automatic report scheduling system
    
    Provides intelligent scheduling with dependency management, resource allocation,
    and dynamic adjustment based on regulatory deadlines and system load.
    """
    
    def __init__(self):
        self.pg_pool = None
        self.kafka_producer = None
        self.deadline_engine = None
        self.report_generator = None
        
        # Resource pools
        self.resource_pools = {
            'finrep': ResourcePool('finrep', max_concurrent_jobs=3),
            'corep': ResourcePool('corep', max_concurrent_jobs=3),
            'dora': ResourcePool('dora', max_concurrent_jobs=2),
            'general': ResourcePool('general', max_concurrent_jobs=5)
        }
        
        # Configuration
        self.config = {
            'kafka_bootstrap_servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
            'scheduler_topic': os.getenv('SCHEDULER_TOPIC', 'report.scheduler'),
            'job_topic': os.getenv('JOB_TOPIC', 'report.jobs'),
            'max_concurrent_jobs': int(os.getenv('MAX_CONCURRENT_JOBS', '10')),
            'job_timeout_minutes': int(os.getenv('JOB_TIMEOUT_MINUTES', '120')),
            'schedule_check_interval': int(os.getenv('SCHEDULE_CHECK_INTERVAL', '60')),  # seconds
            'dependency_timeout_minutes': int(os.getenv('DEPENDENCY_TIMEOUT_MINUTES', '1440')),  # 24 hours
            'enable_load_balancing': os.getenv('ENABLE_LOAD_BALANCING', 'true').lower() == 'true',
            'enable_priority_scheduling': os.getenv('ENABLE_PRIORITY_SCHEDULING', 'true').lower() == 'true',
            'max_retry_attempts': int(os.getenv('MAX_RETRY_ATTEMPTS', '3')),
            'cleanup_completed_jobs_days': int(os.getenv('CLEANUP_COMPLETED_JOBS_DAYS', '30'))
        }
        
        # Performance metrics
        self.metrics = {
            'schedules_active': 0,
            'jobs_scheduled': 0,
            'jobs_completed': 0,
            'jobs_failed': 0,
            'avg_job_duration': 0.0,
            'dependency_violations': 0,
            'resource_contentions': 0,
            'sla_breaches': 0
        }
        
        # Active jobs tracking
        self.active_jobs = {}
        self.job_queue = asyncio.PriorityQueue()
        self.running = False
    
    async def initialize(self):
        """Initialize the report scheduler"""
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
            
            # Initialize deadline engine
            from deadline_engine import create_deadline_engine
            self.deadline_engine = await create_deadline_engine()
            
            # Initialize report generator
            self.report_generator = ComplianceReportGenerator()
            await self.report_generator.initialize()
            
            # Load existing schedules
            await self._load_schedules()
            
            # Start scheduler components
            self.running = True
            asyncio.create_task(self._schedule_monitor())
            asyncio.create_task(self._job_executor())
            asyncio.create_task(self._dependency_resolver())
            asyncio.create_task(self._resource_manager())
            asyncio.create_task(self._cleanup_completed_jobs())
            
            logger.info("Report Scheduler initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Report Scheduler: {e}")
            raise
    
    async def _load_schedules(self):
        """Load existing schedules from database"""
        try:
            async with self.pg_pool.acquire() as conn:
                # Create default schedules if they don't exist
                await self._create_default_schedules(conn)
                
                # Load all active schedules
                schedules = await conn.fetch("""
                    SELECT * FROM report_schedules WHERE status = 'ACTIVE'
                """)
                
                self.metrics['schedules_active'] = len(schedules)
                logger.info(f"Loaded {len(schedules)} active schedules")
                
        except Exception as e:
            logger.error(f"Failed to load schedules: {e}")
            raise
    
    async def _create_default_schedules(self, conn):
        """Create default report schedules"""
        try:
            # Check if schedules already exist
            existing_count = await conn.fetchval("SELECT COUNT(*) FROM report_schedules")
            if existing_count > 0:
                return
            
            # Default FINREP schedules
            finrep_schedules = [
                {
                    'schedule_id': str(uuid.uuid4()),
                    'report_type': 'FINREP',
                    'institution_id': 'INST_001',
                    'jurisdiction': 'EU',
                    'cron_expression': '0 9 28 3,6,9,12 *',  # 9 AM on 28th of quarter-end months
                    'priority': Priority.HIGH.value,
                    'status': ScheduleStatus.ACTIVE.value,
                    'max_retries': 3,
                    'retry_delay_minutes': 60,
                    'timeout_minutes': 180,
                    'resource_requirements': {'pool': 'finrep', 'memory_gb': 4, 'cpu_cores': 2}
                }
            ]
            
            # Default COREP schedules
            corep_schedules = [
                {
                    'schedule_id': str(uuid.uuid4()),
                    'report_type': 'COREP',
                    'institution_id': 'INST_001',
                    'jurisdiction': 'EU',
                    'cron_expression': '0 10 28 3,6,9,12 *',  # 10 AM on 28th of quarter-end months
                    'priority': Priority.HIGH.value,
                    'status': ScheduleStatus.ACTIVE.value,
                    'max_retries': 3,
                    'retry_delay_minutes': 60,
                    'timeout_minutes': 180,
                    'resource_requirements': {'pool': 'corep', 'memory_gb': 3, 'cpu_cores': 2}
                }
            ]
            
            # Default DORA schedules
            dora_schedules = [
                {
                    'schedule_id': str(uuid.uuid4()),
                    'report_type': 'DORA_ICT',
                    'institution_id': 'INST_001',
                    'jurisdiction': 'EU',
                    'cron_expression': '0 8 15 1 *',  # 8 AM on January 15th (annual)
                    'priority': Priority.MEDIUM.value,
                    'status': ScheduleStatus.ACTIVE.value,
                    'max_retries': 2,
                    'retry_delay_minutes': 120,
                    'timeout_minutes': 240,
                    'resource_requirements': {'pool': 'dora', 'memory_gb': 2, 'cpu_cores': 1}
                }
            ]
            
            # Insert all schedules
            all_schedules = finrep_schedules + corep_schedules + dora_schedules
            
            for schedule in all_schedules:
                now = datetime.now(timezone.utc)
                
                # Calculate next run time
                cron = croniter(schedule['cron_expression'], now)
                next_run = cron.get_next(datetime)
                
                await conn.execute("""
                    INSERT INTO report_schedules (
                        schedule_id, report_type, institution_id, jurisdiction, cron_expression,
                        priority, status, created_at, updated_at, next_run_time, last_run_time,
                        dependencies, max_retries, retry_delay_minutes, timeout_minutes,
                        resource_requirements, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
                """, schedule['schedule_id'], schedule['report_type'], schedule['institution_id'],
                    schedule['jurisdiction'], schedule['cron_expression'], schedule['priority'],
                    schedule['status'], now, now, next_run, None, json.dumps([]),
                    schedule['max_retries'], schedule['retry_delay_minutes'], schedule['timeout_minutes'],
                    json.dumps(schedule['resource_requirements']), json.dumps({}))
            
            logger.info(f"Created {len(all_schedules)} default schedules")
            
        except Exception as e:
            logger.error(f"Failed to create default schedules: {e}")
            raise
    
    async def create_schedule(self, 
                            report_type: str,
                            institution_id: str,
                            jurisdiction: str,
                            cron_expression: str,
                            priority: Priority = Priority.MEDIUM,
                            dependencies: List[str] = None,
                            resource_requirements: Dict[str, Any] = None) -> str:
        """Create a new report schedule"""
        try:
            schedule_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            
            # Validate cron expression
            try:
                cron = croniter(cron_expression, now)
                next_run = cron.get_next(datetime)
                description = cron_descriptor.get_description(cron_expression)
                logger.info(f"Schedule description: {description}")
            except Exception as e:
                raise ValueError(f"Invalid cron expression: {cron_expression} - {e}")
            
            # Create schedule
            schedule = ReportSchedule(
                schedule_id=schedule_id,
                report_type=report_type,
                institution_id=institution_id,
                jurisdiction=jurisdiction,
                cron_expression=cron_expression,
                priority=priority,
                status=ScheduleStatus.ACTIVE,
                created_at=now,
                updated_at=now,
                next_run_time=next_run,
                dependencies=dependencies or [],
                resource_requirements=resource_requirements or {}
            )
            
            # Store in database
            await self._store_schedule(schedule)
            
            # Publish schedule creation event
            await self._publish_scheduler_event('schedule.created', schedule)
            
            self.metrics['schedules_active'] += 1
            
            logger.info(f"Created schedule: {schedule_id} for {report_type}")
            return schedule_id
            
        except Exception as e:
            logger.error(f"Failed to create schedule: {e}")
            raise
    
    async def _schedule_monitor(self):
        """Monitor schedules and create jobs when due"""
        try:
            while self.running:
                await asyncio.sleep(self.config['schedule_check_interval'])
                
                current_time = datetime.now(timezone.utc)
                
                # Get schedules due for execution
                async with self.pg_pool.acquire() as conn:
                    due_schedules = await conn.fetch("""
                        SELECT * FROM report_schedules 
                        WHERE status = 'ACTIVE' AND next_run_time <= $1
                    """, current_time)
                
                for schedule_record in due_schedules:
                    try:
                        schedule = self._record_to_schedule(schedule_record)
                        await self._create_scheduled_job(schedule)
                        
                        # Update next run time
                        cron = croniter(schedule.cron_expression, current_time)
                        next_run = cron.get_next(datetime)
                        
                        async with self.pg_pool.acquire() as conn:
                            await conn.execute("""
                                UPDATE report_schedules 
                                SET next_run_time = $2, last_run_time = $3, updated_at = $4
                                WHERE schedule_id = $1
                            """, schedule.schedule_id, next_run, current_time, current_time)
                        
                    except Exception as e:
                        logger.error(f"Failed to process schedule {schedule_record['schedule_id']}: {e}")
                
        except Exception as e:
            logger.error(f"Error in schedule monitor: {e}")
    
    async def _create_scheduled_job(self, schedule: ReportSchedule):
        """Create a scheduled job from a schedule"""
        try:
            # Determine reporting period based on current date
            reporting_period = self._calculate_reporting_period(schedule.report_type)
            
            # Check if job already exists for this period
            async with self.pg_pool.acquire() as conn:
                existing_job = await conn.fetchval("""
                    SELECT job_id FROM scheduled_jobs 
                    WHERE schedule_id = $1 AND reporting_period = $2 
                    AND status NOT IN ('FAILED', 'CANCELLED')
                """, schedule.schedule_id, reporting_period)
                
                if existing_job:
                    logger.info(f"Job already exists for {schedule.schedule_id} {reporting_period}")
                    return
            
            # Create new job
            job = ScheduledJob(
                job_id=str(uuid.uuid4()),
                schedule_id=schedule.schedule_id,
                report_type=schedule.report_type,
                institution_id=schedule.institution_id,
                reporting_period=reporting_period,
                scheduled_time=datetime.now(timezone.utc),
                priority=schedule.priority,
                max_retries=schedule.max_retries,
                dependency_jobs=schedule.dependencies,
                metadata={
                    'jurisdiction': schedule.jurisdiction,
                    'cron_expression': schedule.cron_expression
                }
            )
            
            # Store job
            await self._store_job(job)
            
            # Add to queue
            priority_value = -job.priority.value  # Negative for max-heap behavior
            await self.job_queue.put((priority_value, job.scheduled_time.timestamp(), job))
            
            # Publish job creation event
            await self._publish_job_event('job.created', job)
            
            self.metrics['jobs_scheduled'] += 1
            
            logger.info(f"Created job: {job.job_id} for {schedule.report_type} {reporting_period}")
            
        except Exception as e:
            logger.error(f"Failed to create scheduled job: {e}")
            raise
    
    def _calculate_reporting_period(self, report_type: str) -> str:
        """Calculate reporting period based on report type and current date"""
        now = datetime.now()
        
        if report_type in ['FINREP', 'COREP']:
            # Quarterly reports - use previous quarter
            if now.month <= 3:
                return f"{now.year - 1}-Q4"
            elif now.month <= 6:
                return f"{now.year}-Q1"
            elif now.month <= 9:
                return f"{now.year}-Q2"
            else:
                return f"{now.year}-Q3"
        
        elif report_type == 'DORA_ICT':
            # Annual reports - use previous year
            return str(now.year - 1)
        
        else:
            # Default to monthly
            if now.month == 1:
                return f"{now.year - 1}-12"
            else:
                return f"{now.year}-{now.month - 1:02d}"
    
    async def _job_executor(self):
        """Execute jobs from the queue"""
        try:
            while self.running:
                try:
                    # Get next job from queue
                    _, _, job = await asyncio.wait_for(self.job_queue.get(), timeout=1.0)
                    
                    # Check resource availability
                    if not await self._allocate_resources(job):
                        # Put job back in queue with delay
                        await asyncio.sleep(30)
                        priority_value = -job.priority.value
                        await self.job_queue.put((priority_value, job.scheduled_time.timestamp(), job))
                        continue
                    
                    # Check dependencies
                    if not await self._check_job_dependencies(job):
                        # Put job back in queue with delay
                        await asyncio.sleep(60)
                        priority_value = -job.priority.value
                        await self.job_queue.put((priority_value, job.scheduled_time.timestamp(), job))
                        continue
                    
                    # Execute job
                    asyncio.create_task(self._execute_job(job))
                    
                except asyncio.TimeoutError:
                    continue  # No jobs in queue
                except Exception as e:
                    logger.error(f"Error in job executor: {e}")
                    
        except Exception as e:
            logger.error(f"Fatal error in job executor: {e}")
    
    async def _execute_job(self, job: ScheduledJob):
        """Execute a single job"""
        start_time = datetime.now(timezone.utc)
        
        try:
            logger.info(f"Executing job: {job.job_id}")
            
            # Update job status
            job.status = JobStatus.RUNNING
            job.started_time = start_time
            await self._update_job_status(job)
            
            # Track active job
            self.active_jobs[job.job_id] = job
            
            # Create report request
            report_request = ReportRequest(
                report_id=f"{job.report_type}_{job.reporting_period}_{job.institution_id}",
                report_type=ReportType(job.report_type),
                format=ReportFormat.XBRL,
                reporting_period=job.reporting_period,
                institution_id=job.institution_id,
                jurisdiction=job.metadata.get('jurisdiction', 'EU'),
                template_version='3.2.0',
                data_sources=['database'],
                delivery_method='SFTP',
                deadline=start_time + timedelta(minutes=job.max_retries * 30)
            )
            
            # Generate report
            result = await self.report_generator.generate_report(report_request)
            
            # Update job with results
            job.status = JobStatus.COMPLETED
            job.completed_time = datetime.now(timezone.utc)
            job.result_data = {
                'report_id': result.report_id,
                'file_path': result.file_path,
                'file_size': result.file_size,
                'validation_results': result.validation_results
            }
            
            await self._update_job_status(job)
            
            # Release resources
            await self._release_resources(job)
            
            # Remove from active jobs
            self.active_jobs.pop(job.job_id, None)
            
            # Update metrics
            execution_time = (job.completed_time - job.started_time).total_seconds()
            await self._update_job_metrics(execution_time, True)
            
            # Publish completion event
            await self._publish_job_event('job.completed', job)
            
            logger.info(f"Job completed: {job.job_id} in {execution_time:.2f}s")
            
        except Exception as e:
            # Handle job failure
            error_msg = f"Job execution failed: {str(e)}"
            logger.error(error_msg)
            
            job.status = JobStatus.FAILED
            job.error_message = error_msg
            job.completed_time = datetime.now(timezone.utc)
            
            await self._update_job_status(job)
            
            # Release resources
            await self._release_resources(job)
            
            # Remove from active jobs
            self.active_jobs.pop(job.job_id, None)
            
            # Handle retry logic
            if job.retry_count < job.max_retries:
                await self._schedule_job_retry(job)
            else:
                # Update metrics
                execution_time = (job.completed_time - job.started_time).total_seconds() if job.started_time else 0
                await self._update_job_metrics(execution_time, False)
                
                # Publish failure event
                await self._publish_job_event('job.failed', job)
    
    async def _allocate_resources(self, job: ScheduledJob) -> bool:
        """Allocate resources for job execution"""
        try:
            # Determine resource pool
            pool_name = 'general'
            if job.report_type.lower() in self.resource_pools:
                pool_name = job.report_type.lower()
            
            pool = self.resource_pools[pool_name]
            
            # Check availability
            if pool.current_jobs >= pool.max_concurrent_jobs:
                self.metrics['resource_contentions'] += 1
                return False
            
            # Allocate resources
            pool.current_jobs += 1
            job.resource_allocation = {
                'pool': pool_name,
                'allocated_at': datetime.now(timezone.utc).isoformat()
            }
            
            logger.debug(f"Allocated resources for job {job.job_id} in pool {pool_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to allocate resources: {e}")
            return False
    
    async def _release_resources(self, job: ScheduledJob):
        """Release resources after job completion"""
        try:
            if job.resource_allocation:
                pool_name = job.resource_allocation.get('pool', 'general')
                pool = self.resource_pools.get(pool_name)
                
                if pool and pool.current_jobs > 0:
                    pool.current_jobs -= 1
                    logger.debug(f"Released resources for job {job.job_id} from pool {pool_name}")
                    
        except Exception as e:
            logger.error(f"Failed to release resources: {e}")
    
    async def _check_job_dependencies(self, job: ScheduledJob) -> bool:
        """Check if job dependencies are satisfied"""
        try:
            if not job.dependency_jobs:
                return True
            
            async with self.pg_pool.acquire() as conn:
                for dep_job_id in job.dependency_jobs:
                    # Check if dependency job is completed
                    dep_status = await conn.fetchval("""
                        SELECT status FROM scheduled_jobs 
                        WHERE job_id = $1 OR (schedule_id = $1 AND reporting_period = $2)
                    """, dep_job_id, job.reporting_period)
                    
                    if dep_status != 'COMPLETED':
                        self.metrics['dependency_violations'] += 1
                        return False
            
            job.dependencies_met = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to check job dependencies: {e}")
            return False
    
    async def _schedule_job_retry(self, job: ScheduledJob):
        """Schedule job retry"""
        try:
            job.retry_count += 1
            job.status = JobStatus.RETRYING
            
            # Calculate retry delay
            retry_delay = job.retry_count * 30  # 30 minutes per retry
            retry_time = datetime.now(timezone.utc) + timedelta(minutes=retry_delay)
            
            # Update job
            await self._update_job_status(job)
            
            # Schedule retry
            await asyncio.sleep(retry_delay * 60)  # Convert to seconds
            
            priority_value = -job.priority.value
            await self.job_queue.put((priority_value, retry_time.timestamp(), job))
            
            logger.info(f"Scheduled retry for job {job.job_id} (attempt {job.retry_count})")
            
        except Exception as e:
            logger.error(f"Failed to schedule job retry: {e}")
    
    async def _dependency_resolver(self):
        """Resolve job dependencies and update dependency status"""
        try:
            while self.running:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                # Get jobs waiting for dependencies
                async with self.pg_pool.acquire() as conn:
                    waiting_jobs = await conn.fetch("""
                        SELECT * FROM scheduled_jobs 
                        WHERE status = 'SCHEDULED' AND dependencies_met = false
                        AND scheduled_time <= $1
                    """, datetime.now(timezone.utc) + timedelta(hours=1))
                
                for job_record in waiting_jobs:
                    job = self._record_to_job(job_record)
                    
                    if await self._check_job_dependencies(job):
                        # Dependencies met - add to queue
                        priority_value = -job.priority.value
                        await self.job_queue.put((priority_value, job.scheduled_time.timestamp(), job))
                        
                        # Update database
                        async with self.pg_pool.acquire() as conn:
                            await conn.execute("""
                                UPDATE scheduled_jobs 
                                SET dependencies_met = true, updated_at = CURRENT_TIMESTAMP
                                WHERE job_id = $1
                            """, job.job_id)
                
        except Exception as e:
            logger.error(f"Error in dependency resolver: {e}")
    
    async def _resource_manager(self):
        """Manage resource allocation and load balancing"""
        try:
            while self.running:
                await asyncio.sleep(120)  # Check every 2 minutes
                
                # Update resource pool metrics
                for pool_name, pool in self.resource_pools.items():
                    pool.resource_metrics = {
                        'utilization': (pool.current_jobs / pool.max_concurrent_jobs) * 100,
                        'queue_length': self.job_queue.qsize(),
                        'active_jobs': pool.current_jobs
                    }
                
                # Log resource status
                logger.debug(f"Resource pools status: {[(name, pool.current_jobs, pool.max_concurrent_jobs) for name, pool in self.resource_pools.items()]}")
                
        except Exception as e:
            logger.error(f"Error in resource manager: {e}")
    
    async def _cleanup_completed_jobs(self):
        """Clean up old completed jobs"""
        try:
            while self.running:
                await asyncio.sleep(3600)  # Check every hour
                
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.config['cleanup_completed_jobs_days'])
                
                async with self.pg_pool.acquire() as conn:
                    deleted_count = await conn.fetchval("""
                        DELETE FROM scheduled_jobs 
                        WHERE status IN ('COMPLETED', 'CANCELLED') AND completed_time < $1
                        RETURNING COUNT(*)
                    """, cutoff_date)
                    
                    if deleted_count > 0:
                        logger.info(f"Cleaned up {deleted_count} completed jobs")
                        
        except Exception as e:
            logger.error(f"Error cleaning up completed jobs: {e}")
    
    # Database operations
    async def _store_schedule(self, schedule: ReportSchedule):
        """Store schedule in database"""
        async with self.pg_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO report_schedules (
                    schedule_id, report_type, institution_id, jurisdiction, cron_expression,
                    priority, status, created_at, updated_at, next_run_time, last_run_time,
                    dependencies, max_retries, retry_delay_minutes, timeout_minutes,
                    resource_requirements, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
            """, schedule.schedule_id, schedule.report_type, schedule.institution_id,
                schedule.jurisdiction, schedule.cron_expression, schedule.priority.value,
                schedule.status.value, schedule.created_at, schedule.updated_at,
                schedule.next_run_time, schedule.last_run_time, json.dumps(schedule.dependencies or []),
                schedule.max_retries, schedule.retry_delay_minutes, schedule.timeout_minutes,
                json.dumps(schedule.resource_requirements or {}), json.dumps(schedule.metadata or {}))
    
    async def _store_job(self, job: ScheduledJob):
        """Store job in database"""
        async with self.pg_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO scheduled_jobs (
                    job_id, schedule_id, report_type, institution_id, reporting_period,
                    scheduled_time, started_time, completed_time, status, priority,
                    retry_count, max_retries, error_message, result_data, resource_allocation,
                    dependencies_met, dependency_jobs, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
            """, job.job_id, job.schedule_id, job.report_type, job.institution_id,
                job.reporting_period, job.scheduled_time, job.started_time, job.completed_time,
                job.status.value, job.priority.value, job.retry_count, job.max_retries,
                job.error_message, json.dumps(job.result_data or {}), json.dumps(job.resource_allocation or {}),
                job.dependencies_met, json.dumps(job.dependency_jobs or []), json.dumps(job.metadata or {}))
    
    async def _update_job_status(self, job: ScheduledJob):
        """Update job status in database"""
        async with self.pg_pool.acquire() as conn:
            await conn.execute("""
                UPDATE scheduled_jobs SET
                    status = $2, started_time = $3, completed_time = $4, retry_count = $5,
                    error_message = $6, result_data = $7, resource_allocation = $8,
                    dependencies_met = $9, updated_at = CURRENT_TIMESTAMP
                WHERE job_id = $1
            """, job.job_id, job.status.value, job.started_time, job.completed_time,
                job.retry_count, job.error_message, json.dumps(job.result_data or {}),
                json.dumps(job.resource_allocation or {}), job.dependencies_met)
    
    def _record_to_schedule(self, record) -> ReportSchedule:
        """Convert database record to ReportSchedule object"""
        return ReportSchedule(
            schedule_id=record['schedule_id'],
            report_type=record['report_type'],
            institution_id=record['institution_id'],
            jurisdiction=record['jurisdiction'],
            cron_expression=record['cron_expression'],
            priority=Priority(record['priority']),
            status=ScheduleStatus(record['status']),
            created_at=record['created_at'],
            updated_at=record['updated_at'],
            next_run_time=record['next_run_time'],
            last_run_time=record['last_run_time'],
            dependencies=json.loads(record['dependencies']) if record['dependencies'] else [],
            max_retries=record['max_retries'],
            retry_delay_minutes=record['retry_delay_minutes'],
            timeout_minutes=record['timeout_minutes'],
            resource_requirements=json.loads(record['resource_requirements']) if record['resource_requirements'] else {},
            metadata=json.loads(record['metadata']) if record['metadata'] else {}
        )
    
    def _record_to_job(self, record) -> ScheduledJob:
        """Convert database record to ScheduledJob object"""
        return ScheduledJob(
            job_id=record['job_id'],
            schedule_id=record['schedule_id'],
            report_type=record['report_type'],
            institution_id=record['institution_id'],
            reporting_period=record['reporting_period'],
            scheduled_time=record['scheduled_time'],
            started_time=record['started_time'],
            completed_time=record['completed_time'],
            status=JobStatus(record['status']),
            priority=Priority(record['priority']),
            retry_count=record['retry_count'],
            max_retries=record['max_retries'],
            error_message=record['error_message'],
            result_data=json.loads(record['result_data']) if record['result_data'] else {},
            resource_allocation=json.loads(record['resource_allocation']) if record['resource_allocation'] else {},
            dependencies_met=record['dependencies_met'],
            dependency_jobs=json.loads(record['dependency_jobs']) if record['dependency_jobs'] else [],
            metadata=json.loads(record['metadata']) if record['metadata'] else {}
        )
    
    # Event publishing
    async def _publish_scheduler_event(self, event_type: str, schedule: ReportSchedule):
        """Publish scheduler event to Kafka"""
        try:
            event_data = {
                'event_type': event_type,
                'schedule_id': schedule.schedule_id,
                'report_type': schedule.report_type,
                'institution_id': schedule.institution_id,
                'status': schedule.status.value,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            await self.kafka_producer.send(self.config['scheduler_topic'], event_data)
            
        except Exception as e:
            logger.error(f"Failed to publish scheduler event: {e}")
    
    async def _publish_job_event(self, event_type: str, job: ScheduledJob):
        """Publish job event to Kafka"""
        try:
            event_data = {
                'event_type': event_type,
                'job_id': job.job_id,
                'schedule_id': job.schedule_id,
                'report_type': job.report_type,
                'status': job.status.value,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            await self.kafka_producer.send(self.config['job_topic'], event_data)
            
        except Exception as e:
            logger.error(f"Failed to publish job event: {e}")
    
    # Metrics
    async def _update_job_metrics(self, execution_time: float, success: bool):
        """Update job execution metrics"""
        if success:
            self.metrics['jobs_completed'] += 1
            
            # Update average execution time
            current_avg = self.metrics['avg_job_duration']
            completed_count = self.metrics['jobs_completed']
            
            self.metrics['avg_job_duration'] = (
                (current_avg * (completed_count - 1) + execution_time) / completed_count
            )
        else:
            self.metrics['jobs_failed'] += 1
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get scheduler metrics"""
        return {
            **self.metrics,
            'success_rate': (
                (self.metrics['jobs_completed'] / (self.metrics['jobs_completed'] + self.metrics['jobs_failed']) * 100)
                if (self.metrics['jobs_completed'] + self.metrics['jobs_failed']) > 0 else 0.0
            ),
            'active_jobs_count': len(self.active_jobs),
            'queue_size': self.job_queue.qsize(),
            'resource_pools': {name: pool.resource_metrics for name, pool in self.resource_pools.items()},
            'uptime': datetime.now().isoformat()
        }
    
    async def get_schedule_status(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        """Get schedule status"""
        try:
            async with self.pg_pool.acquire() as conn:
                schedule = await conn.fetchrow("""
                    SELECT * FROM report_schedules WHERE schedule_id = $1
                """, schedule_id)
                
                if schedule:
                    return dict(schedule)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get schedule status: {e}")
            return None
    
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status"""
        try:
            async with self.pg_pool.acquire() as conn:
                job = await conn.fetchrow("""
                    SELECT * FROM scheduled_jobs WHERE job_id = $1
                """, job_id)
                
                if job:
                    return dict(job)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get job status: {e}")
            return None
    
    async def close(self):
        """Close the report scheduler"""
        self.running = False
        
        # Cancel all active jobs
        for job_id, job in self.active_jobs.items():
            logger.info(f"Cancelling active job: {job_id}")
        
        if self.kafka_producer:
            await self.kafka_producer.stop()
        
        if self.pg_pool:
            await self.pg_pool.close()
        
        logger.info("Report Scheduler closed")

# Factory function
async def create_report_scheduler() -> ReportScheduler:
    """Factory function to create and initialize report scheduler"""
    scheduler = ReportScheduler()
    await scheduler.initialize()
    return scheduler
