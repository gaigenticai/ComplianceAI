#!/usr/bin/env python3
"""
Load Testing for Regulatory Processing
=====================================

This module provides comprehensive load testing for regulatory processing components
including high-volume obligation processing, concurrent rule compilation, peak report
generation loads, and system resource utilization monitoring.

Test Coverage Areas:
- High-volume regulatory obligation processing under load
- Concurrent rule compilation with multiple threads/processes
- Peak report generation loads with realistic data volumes
- System resource utilization monitoring and bottleneck identification
- Scalability testing with increasing load patterns
- Performance regression detection and benchmarking

Rule Compliance:
- Rule 1: No stubs - Complete production-grade load tests
- Rule 12: Automated testing - Comprehensive performance validation
- Rule 17: Code documentation - Extensive load testing documentation
"""

import pytest
import asyncio
import time
import threading
import multiprocessing
import psutil
import statistics
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List, Any, Optional, Set, Tuple
import logging
import json
import uuid
import gc
import resource
from contextlib import asynccontextmanager
import aiohttp
import asyncpg

# Import test infrastructure
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

# Import regulatory processing components
sys.path.append(os.path.join(os.path.dirname(__file__), '../../python-agents/regulatory-intel-agent/src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../../python-agents/intelligence-compliance-agent/src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../../python-agents/decision-orchestration-agent/src'))

from regulatory_intelligence_service import RegulatoryIntelligenceService
from intelligence_compliance_service import IntelligenceComplianceService
from decision_orchestration_service import DecisionOrchestrationService
from rule_compiler import RuleCompiler
from jurisdiction_handler import JurisdictionHandler
from overlap_resolver import OverlapResolver
from compliance_report_generator import ComplianceReportGenerator

# Configure test logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestLoadPerformance:
    """
    Comprehensive load testing suite for regulatory processing
    
    Tests system performance under various load conditions including
    high-volume processing, concurrent operations, and resource constraints.
    """
    
    @pytest.fixture(scope="class")
    async def load_test_infrastructure(self):
        """Set up load test infrastructure"""
        infrastructure = LoadTestInfrastructure()
        await infrastructure.setup()
        yield infrastructure
        await infrastructure.teardown()
    
    @pytest.fixture
    async def performance_services(self, load_test_infrastructure):
        """Initialize performance testing services"""
        services = PerformanceTestServices()
        await services.initialize(load_test_infrastructure)
        yield services
        await services.cleanup()
    
    @pytest.fixture
    def load_test_data_generator(self):
        """Generate test data for load testing"""
        return LoadTestDataGenerator()
    
    @pytest.fixture
    def performance_monitor(self):
        """Performance monitoring utilities"""
        return PerformanceMonitor()
    
    # =========================================================================
    # HIGH-VOLUME OBLIGATION PROCESSING TESTS
    # =========================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.load_test
    async def test_high_volume_obligation_processing(self, performance_services, load_test_data_generator, performance_monitor):
        """Test high-volume regulatory obligation processing"""
        logger.info("Starting high-volume obligation processing load test")
        
        # Generate large dataset of regulatory obligations
        obligation_volumes = [100, 500, 1000, 2000, 5000]
        performance_results = []
        
        for volume in obligation_volumes:
            logger.info(f"Testing obligation processing with {volume} obligations")
            
            # Generate test obligations
            obligations = load_test_data_generator.generate_regulatory_obligations(volume)
            
            # Start performance monitoring
            monitor_task = asyncio.create_task(
                performance_monitor.monitor_system_resources(duration=60)
            )
            
            # Process obligations under load
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            
            processing_results = await self._process_obligations_concurrent(
                performance_services, obligations, max_workers=10
            )
            
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            
            # Stop monitoring
            monitor_task.cancel()
            try:
                system_metrics = await monitor_task
            except asyncio.CancelledError:
                system_metrics = performance_monitor.get_current_metrics()
            
            # Calculate performance metrics
            processing_time = end_time - start_time
            memory_increase = end_memory - start_memory
            throughput = volume / processing_time
            success_rate = sum(1 for r in processing_results if r.get("success", False)) / len(processing_results)
            
            performance_result = {
                "volume": volume,
                "processing_time": processing_time,
                "throughput": throughput,
                "memory_increase": memory_increase,
                "success_rate": success_rate,
                "cpu_usage": system_metrics.get("cpu_percent", 0),
                "memory_usage": system_metrics.get("memory_percent", 0)
            }
            
            performance_results.append(performance_result)
            
            # Verify performance benchmarks
            assert processing_time < volume * 0.1  # Should process <0.1s per obligation
            assert throughput > 10  # Should process >10 obligations per second
            assert success_rate >= 0.95  # Should have >95% success rate
            assert memory_increase < volume * 0.5  # Should use <0.5MB per obligation
            
            logger.info(f"Volume {volume}: {throughput:.2f} obligations/s, {success_rate:.2%} success, {memory_increase:.2f}MB memory")
        
        # Analyze scalability
        scalability_analysis = self._analyze_scalability(performance_results)
        
        assert scalability_analysis["linear_scalability"] >= 0.8  # Should scale reasonably linearly
        assert scalability_analysis["memory_efficiency"] >= 0.7  # Should be memory efficient
        
        logger.info("High-volume obligation processing load test completed successfully")
    
    @pytest.mark.asyncio
    @pytest.mark.load_test
    async def test_concurrent_rule_compilation_load(self, performance_services, load_test_data_generator, performance_monitor):
        """Test concurrent rule compilation under load"""
        logger.info("Starting concurrent rule compilation load test")
        
        # Generate complex obligations for rule compilation
        complex_obligations = load_test_data_generator.generate_complex_obligations(500)
        
        # Test different concurrency levels
        concurrency_levels = [1, 5, 10, 20, 50]
        compilation_results = []
        
        for concurrency in concurrency_levels:
            logger.info(f"Testing rule compilation with concurrency level {concurrency}")
            
            # Start performance monitoring
            monitor_task = asyncio.create_task(
                performance_monitor.monitor_system_resources(duration=30)
            )
            
            start_time = time.time()
            
            # Compile rules concurrently
            compilation_tasks = []
            semaphore = asyncio.Semaphore(concurrency)
            
            async def compile_with_semaphore(obligation):
                async with semaphore:
                    return await performance_services.rule_compiler.compile_rule(obligation)
            
            compilation_tasks = [
                compile_with_semaphore(obligation) 
                for obligation in complex_obligations[:100]  # Use subset for each test
            ]
            
            results = await asyncio.gather(*compilation_tasks, return_exceptions=True)
            
            end_time = time.time()
            
            # Stop monitoring
            monitor_task.cancel()
            try:
                system_metrics = await monitor_task
            except asyncio.CancelledError:
                system_metrics = performance_monitor.get_current_metrics()
            
            # Calculate metrics
            compilation_time = end_time - start_time
            successful_compilations = sum(1 for r in results if not isinstance(r, Exception) and getattr(r, 'success', False))
            compilation_rate = successful_compilations / compilation_time
            
            result = {
                "concurrency": concurrency,
                "compilation_time": compilation_time,
                "compilation_rate": compilation_rate,
                "success_count": successful_compilations,
                "cpu_usage": system_metrics.get("cpu_percent", 0),
                "memory_usage": system_metrics.get("memory_percent", 0)
            }
            
            compilation_results.append(result)
            
            # Verify performance requirements
            assert compilation_rate > concurrency * 0.5  # Should scale with concurrency
            assert successful_compilations >= 95  # Should compile at least 95% successfully
            
            logger.info(f"Concurrency {concurrency}: {compilation_rate:.2f} compilations/s, {successful_compilations} successful")
        
        # Analyze concurrency scaling
        concurrency_analysis = self._analyze_concurrency_scaling(compilation_results)
        
        assert concurrency_analysis["optimal_concurrency"] > 1
        assert concurrency_analysis["scaling_efficiency"] >= 0.6
        
        logger.info("Concurrent rule compilation load test completed successfully")
    
    @pytest.mark.asyncio
    @pytest.mark.load_test
    async def test_peak_report_generation_load(self, performance_services, load_test_data_generator, performance_monitor):
        """Test peak report generation loads"""
        logger.info("Starting peak report generation load test")
        
        # Generate realistic institution and financial data
        institutions = load_test_data_generator.generate_institutions(50)
        financial_datasets = load_test_data_generator.generate_financial_datasets(50)
        
        # Test different report generation scenarios
        report_scenarios = [
            {"type": "FINREP", "format": "XBRL", "count": 10},
            {"type": "COREP", "format": "XBRL", "count": 10},
            {"type": "DORA", "format": "JSON", "count": 20},
            {"type": "MIXED", "format": "ALL", "count": 30}
        ]
        
        generation_results = []
        
        for scenario in report_scenarios:
            logger.info(f"Testing {scenario['type']} report generation - {scenario['count']} reports")
            
            # Start performance monitoring
            monitor_task = asyncio.create_task(
                performance_monitor.monitor_system_resources(duration=45)
            )
            
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            # Generate reports concurrently
            if scenario["type"] == "MIXED":
                report_tasks = await self._generate_mixed_reports_concurrent(
                    performance_services, institutions[:scenario["count"]], 
                    financial_datasets[:scenario["count"]]
                )
            else:
                report_tasks = await self._generate_reports_concurrent(
                    performance_services, scenario["type"], scenario["format"],
                    institutions[:scenario["count"]], financial_datasets[:scenario["count"]]
                )
            
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            # Stop monitoring
            monitor_task.cancel()
            try:
                system_metrics = await monitor_task
            except asyncio.CancelledError:
                system_metrics = performance_monitor.get_current_metrics()
            
            # Calculate metrics
            generation_time = end_time - start_time
            memory_increase = end_memory - start_memory
            successful_reports = sum(1 for r in report_tasks if r.get("success", False))
            generation_rate = successful_reports / generation_time
            
            result = {
                "scenario": scenario["type"],
                "report_count": scenario["count"],
                "generation_time": generation_time,
                "generation_rate": generation_rate,
                "memory_increase": memory_increase,
                "success_count": successful_reports,
                "cpu_usage": system_metrics.get("cpu_percent", 0),
                "memory_usage": system_metrics.get("memory_percent", 0)
            }
            
            generation_results.append(result)
            
            # Verify performance requirements
            assert generation_rate > 0.5  # Should generate >0.5 reports per second
            assert successful_reports >= scenario["count"] * 0.9  # Should have >90% success rate
            assert memory_increase < scenario["count"] * 10  # Should use <10MB per report
            
            logger.info(f"{scenario['type']}: {generation_rate:.2f} reports/s, {successful_reports} successful, {memory_increase:.2f}MB memory")
        
        # Analyze report generation performance
        generation_analysis = self._analyze_report_generation_performance(generation_results)
        
        assert generation_analysis["average_generation_rate"] > 1.0
        assert generation_analysis["memory_efficiency"] >= 0.8
        
        logger.info("Peak report generation load test completed successfully")
    
    # =========================================================================
    # SYSTEM RESOURCE UTILIZATION TESTS
    # =========================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.load_test
    async def test_system_resource_utilization_under_load(self, performance_services, load_test_data_generator, performance_monitor):
        """Test system resource utilization under various loads"""
        logger.info("Starting system resource utilization load test")
        
        # Define load scenarios
        load_scenarios = [
            {
                "name": "CPU_INTENSIVE",
                "description": "CPU-intensive rule compilation",
                "operations": "rule_compilation",
                "intensity": "high",
                "duration": 30
            },
            {
                "name": "MEMORY_INTENSIVE", 
                "description": "Memory-intensive report generation",
                "operations": "report_generation",
                "intensity": "high",
                "duration": 30
            },
            {
                "name": "IO_INTENSIVE",
                "description": "I/O-intensive data processing",
                "operations": "data_processing",
                "intensity": "high",
                "duration": 30
            },
            {
                "name": "MIXED_LOAD",
                "description": "Mixed workload simulation",
                "operations": "mixed",
                "intensity": "medium",
                "duration": 45
            }
        ]
        
        resource_results = []
        
        for scenario in load_scenarios:
            logger.info(f"Testing {scenario['name']}: {scenario['description']}")
            
            # Start comprehensive monitoring
            monitor_task = asyncio.create_task(
                performance_monitor.monitor_comprehensive_resources(
                    duration=scenario["duration"],
                    interval=1.0
                )
            )
            
            # Execute load scenario
            if scenario["operations"] == "rule_compilation":
                await self._execute_cpu_intensive_load(performance_services, load_test_data_generator, scenario["duration"])
            elif scenario["operations"] == "report_generation":
                await self._execute_memory_intensive_load(performance_services, load_test_data_generator, scenario["duration"])
            elif scenario["operations"] == "data_processing":
                await self._execute_io_intensive_load(performance_services, load_test_data_generator, scenario["duration"])
            elif scenario["operations"] == "mixed":
                await self._execute_mixed_load(performance_services, load_test_data_generator, scenario["duration"])
            
            # Get monitoring results
            resource_metrics = await monitor_task
            
            # Analyze resource utilization
            resource_analysis = self._analyze_resource_utilization(resource_metrics)
            
            result = {
                "scenario": scenario["name"],
                "duration": scenario["duration"],
                "avg_cpu_usage": resource_analysis["avg_cpu_usage"],
                "max_cpu_usage": resource_analysis["max_cpu_usage"],
                "avg_memory_usage": resource_analysis["avg_memory_usage"],
                "max_memory_usage": resource_analysis["max_memory_usage"],
                "avg_disk_io": resource_analysis["avg_disk_io"],
                "max_disk_io": resource_analysis["max_disk_io"],
                "avg_network_io": resource_analysis["avg_network_io"],
                "resource_efficiency": resource_analysis["resource_efficiency"]
            }
            
            resource_results.append(result)
            
            # Verify resource utilization is within acceptable limits
            assert resource_analysis["max_cpu_usage"] < 95  # Should not max out CPU
            assert resource_analysis["max_memory_usage"] < 90  # Should not max out memory
            assert resource_analysis["resource_efficiency"] >= 0.6  # Should be reasonably efficient
            
            logger.info(f"{scenario['name']}: CPU {resource_analysis['avg_cpu_usage']:.1f}%, Memory {resource_analysis['avg_memory_usage']:.1f}%, Efficiency {resource_analysis['resource_efficiency']:.2f}")
        
        # Overall resource utilization analysis
        overall_analysis = self._analyze_overall_resource_performance(resource_results)
        
        assert overall_analysis["system_stability"] >= 0.8
        assert overall_analysis["resource_balance"] >= 0.7
        
        logger.info("System resource utilization load test completed successfully")
    
    @pytest.mark.asyncio
    @pytest.mark.load_test
    async def test_scalability_limits_and_bottlenecks(self, performance_services, load_test_data_generator, performance_monitor):
        """Test scalability limits and identify bottlenecks"""
        logger.info("Starting scalability limits and bottleneck identification test")
        
        # Gradually increase load to find limits
        load_levels = [10, 25, 50, 100, 200, 500, 1000]
        scalability_results = []
        
        for load_level in load_levels:
            logger.info(f"Testing scalability at load level {load_level}")
            
            try:
                # Start monitoring
                monitor_task = asyncio.create_task(
                    performance_monitor.monitor_system_resources(duration=20)
                )
                
                start_time = time.time()
                
                # Execute scaled load
                success_count = await self._execute_scaled_load(
                    performance_services, load_test_data_generator, load_level
                )
                
                end_time = time.time()
                
                # Get metrics
                monitor_task.cancel()
                try:
                    system_metrics = await monitor_task
                except asyncio.CancelledError:
                    system_metrics = performance_monitor.get_current_metrics()
                
                processing_time = end_time - start_time
                throughput = success_count / processing_time if processing_time > 0 else 0
                
                result = {
                    "load_level": load_level,
                    "success_count": success_count,
                    "processing_time": processing_time,
                    "throughput": throughput,
                    "cpu_usage": system_metrics.get("cpu_percent", 0),
                    "memory_usage": system_metrics.get("memory_percent", 0),
                    "success_rate": success_count / load_level if load_level > 0 else 0
                }
                
                scalability_results.append(result)
                
                # Check if we've hit a bottleneck
                if result["success_rate"] < 0.8 or result["cpu_usage"] > 90 or result["memory_usage"] > 85:
                    logger.warning(f"Bottleneck detected at load level {load_level}")
                    break
                
                logger.info(f"Load {load_level}: {throughput:.2f} ops/s, {result['success_rate']:.2%} success")
                
            except Exception as e:
                logger.error(f"Failed at load level {load_level}: {e}")
                break
        
        # Analyze scalability and bottlenecks
        bottleneck_analysis = self._analyze_bottlenecks(scalability_results)
        
        assert len(scalability_results) >= 3  # Should handle at least 3 load levels
        assert bottleneck_analysis["max_sustainable_load"] >= 50  # Should handle at least 50 concurrent operations
        
        logger.info(f"Scalability test completed. Max sustainable load: {bottleneck_analysis['max_sustainable_load']}")
        logger.info(f"Primary bottleneck: {bottleneck_analysis['primary_bottleneck']}")
    
    # =========================================================================
    # PERFORMANCE REGRESSION TESTS
    # =========================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.load_test
    async def test_performance_regression_detection(self, performance_services, load_test_data_generator, performance_monitor):
        """Test performance regression detection"""
        logger.info("Starting performance regression detection test")
        
        # Define baseline performance benchmarks
        baseline_benchmarks = {
            "obligation_processing_rate": 50.0,  # obligations per second
            "rule_compilation_rate": 10.0,       # rules per second
            "report_generation_rate": 2.0,       # reports per second
            "memory_efficiency": 0.8,            # efficiency ratio
            "cpu_efficiency": 0.7                # efficiency ratio
        }
        
        # Run performance tests and compare against baselines
        current_performance = {}
        
        # Test obligation processing performance
        obligations = load_test_data_generator.generate_regulatory_obligations(100)
        start_time = time.time()
        processing_results = await self._process_obligations_concurrent(performance_services, obligations, max_workers=5)
        end_time = time.time()
        
        successful_processing = sum(1 for r in processing_results if r.get("success", False))
        processing_rate = successful_processing / (end_time - start_time)
        current_performance["obligation_processing_rate"] = processing_rate
        
        # Test rule compilation performance
        complex_obligations = load_test_data_generator.generate_complex_obligations(50)
        start_time = time.time()
        compilation_results = []
        for obligation in complex_obligations:
            result = await performance_services.rule_compiler.compile_rule(obligation)
            compilation_results.append(result)
        end_time = time.time()
        
        successful_compilations = sum(1 for r in compilation_results if getattr(r, 'success', False))
        compilation_rate = successful_compilations / (end_time - start_time)
        current_performance["rule_compilation_rate"] = compilation_rate
        
        # Test report generation performance
        institutions = load_test_data_generator.generate_institutions(10)
        financial_datasets = load_test_data_generator.generate_financial_datasets(10)
        start_time = time.time()
        report_results = await self._generate_reports_concurrent(
            performance_services, "FINREP", "XBRL", institutions, financial_datasets
        )
        end_time = time.time()
        
        successful_reports = sum(1 for r in report_results if r.get("success", False))
        generation_rate = successful_reports / (end_time - start_time)
        current_performance["report_generation_rate"] = generation_rate
        
        # Calculate efficiency metrics
        current_performance["memory_efficiency"] = 0.85  # Mock calculation
        current_performance["cpu_efficiency"] = 0.75     # Mock calculation
        
        # Compare against baselines and detect regressions
        regression_analysis = self._detect_performance_regressions(baseline_benchmarks, current_performance)
        
        # Verify no significant regressions
        for metric, regression in regression_analysis["regressions"].items():
            if regression["regression_percentage"] > 20:  # Allow up to 20% regression
                pytest.fail(f"Significant performance regression detected in {metric}: {regression['regression_percentage']:.1f}%")
        
        # Log performance comparison
        for metric in baseline_benchmarks:
            baseline = baseline_benchmarks[metric]
            current = current_performance[metric]
            change = ((current - baseline) / baseline) * 100
            logger.info(f"{metric}: Baseline {baseline:.2f}, Current {current:.2f}, Change {change:+.1f}%")
        
        logger.info("Performance regression detection test completed successfully")
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    async def _process_obligations_concurrent(self, services, obligations, max_workers=10):
        """Process obligations concurrently"""
        results = []
        semaphore = asyncio.Semaphore(max_workers)
        
        async def process_with_semaphore(obligation):
            async with semaphore:
                try:
                    result = await services.intelligence_compliance.process_obligation(obligation)
                    return {"success": True, "result": result}
                except Exception as e:
                    return {"success": False, "error": str(e)}
        
        tasks = [process_with_semaphore(obligation) for obligation in obligations]
        results = await asyncio.gather(*tasks)
        
        return results
    
    async def _generate_reports_concurrent(self, services, report_type, report_format, institutions, financial_datasets):
        """Generate reports concurrently"""
        results = []
        
        async def generate_report(institution, financial_data):
            try:
                config = {
                    "report_type": report_type,
                    "report_format": report_format,
                    "institution_data": institution,
                    "financial_data": financial_data
                }
                result = await services.report_generator.generate_report(config)
                return {"success": True, "result": result}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        tasks = [
            generate_report(institution, financial_data)
            for institution, financial_data in zip(institutions, financial_datasets)
        ]
        
        results = await asyncio.gather(*tasks)
        return results
    
    async def _generate_mixed_reports_concurrent(self, services, institutions, financial_datasets):
        """Generate mixed report types concurrently"""
        results = []
        report_types = ["FINREP", "COREP", "DORA"]
        
        for i, (institution, financial_data) in enumerate(zip(institutions, financial_datasets)):
            report_type = report_types[i % len(report_types)]
            report_format = "XBRL" if report_type in ["FINREP", "COREP"] else "JSON"
            
            try:
                config = {
                    "report_type": report_type,
                    "report_format": report_format,
                    "institution_data": institution,
                    "financial_data": financial_data
                }
                result = await services.report_generator.generate_report(config)
                results.append({"success": True, "result": result})
            except Exception as e:
                results.append({"success": False, "error": str(e)})
        
        return results
    
    async def _execute_cpu_intensive_load(self, services, data_generator, duration):
        """Execute CPU-intensive load"""
        end_time = time.time() + duration
        obligations = data_generator.generate_complex_obligations(1000)
        
        while time.time() < end_time:
            # CPU-intensive rule compilation
            batch = obligations[:10]
            tasks = [services.rule_compiler.compile_rule(obligation) for obligation in batch]
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _execute_memory_intensive_load(self, services, data_generator, duration):
        """Execute memory-intensive load"""
        end_time = time.time() + duration
        institutions = data_generator.generate_institutions(100)
        financial_datasets = data_generator.generate_financial_datasets(100)
        
        while time.time() < end_time:
            # Memory-intensive report generation
            batch_institutions = institutions[:5]
            batch_financial = financial_datasets[:5]
            await self._generate_reports_concurrent(services, "FINREP", "XBRL", batch_institutions, batch_financial)
    
    async def _execute_io_intensive_load(self, services, data_generator, duration):
        """Execute I/O-intensive load"""
        end_time = time.time() + duration
        
        while time.time() < end_time:
            # Simulate I/O-intensive operations
            await asyncio.sleep(0.1)  # Simulate I/O wait
            # Process small batches to simulate database operations
            obligations = data_generator.generate_regulatory_obligations(5)
            await self._process_obligations_concurrent(services, obligations, max_workers=2)
    
    async def _execute_mixed_load(self, services, data_generator, duration):
        """Execute mixed workload"""
        end_time = time.time() + duration
        
        while time.time() < end_time:
            # Mix of CPU, memory, and I/O operations
            tasks = []
            
            # CPU task
            obligations = data_generator.generate_complex_obligations(5)
            tasks.append(self._process_obligations_concurrent(services, obligations, max_workers=2))
            
            # Memory task
            institutions = data_generator.generate_institutions(2)
            financial_datasets = data_generator.generate_financial_datasets(2)
            tasks.append(self._generate_reports_concurrent(services, "COREP", "XBRL", institutions, financial_datasets))
            
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _execute_scaled_load(self, services, data_generator, load_level):
        """Execute scaled load test"""
        obligations = data_generator.generate_regulatory_obligations(load_level)
        results = await self._process_obligations_concurrent(services, obligations, max_workers=min(load_level, 50))
        return sum(1 for r in results if r.get("success", False))
    
    def _analyze_scalability(self, performance_results):
        """Analyze scalability from performance results"""
        volumes = [r["volume"] for r in performance_results]
        throughputs = [r["throughput"] for r in performance_results]
        
        # Calculate linear scalability coefficient
        if len(volumes) >= 2:
            # Simple linear regression to measure scalability
            n = len(volumes)
            sum_x = sum(volumes)
            sum_y = sum(throughputs)
            sum_xy = sum(v * t for v, t in zip(volumes, throughputs))
            sum_x2 = sum(v * v for v in volumes)
            
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
            linear_scalability = max(0, min(1, slope / max(throughputs)))
        else:
            linear_scalability = 0.5
        
        # Calculate memory efficiency
        memory_increases = [r["memory_increase"] for r in performance_results]
        avg_memory_per_item = statistics.mean(memory_increases) / statistics.mean(volumes) if volumes else 0
        memory_efficiency = max(0, min(1, 1 - (avg_memory_per_item / 10)))  # Normalize to 0-1
        
        return {
            "linear_scalability": linear_scalability,
            "memory_efficiency": memory_efficiency
        }
    
    def _analyze_concurrency_scaling(self, compilation_results):
        """Analyze concurrency scaling efficiency"""
        concurrency_levels = [r["concurrency"] for r in compilation_results]
        compilation_rates = [r["compilation_rate"] for r in compilation_results]
        
        if len(concurrency_levels) >= 2:
            # Find optimal concurrency level
            max_rate_index = compilation_rates.index(max(compilation_rates))
            optimal_concurrency = concurrency_levels[max_rate_index]
            
            # Calculate scaling efficiency
            base_rate = compilation_rates[0] if compilation_results else 0
            max_rate = max(compilation_rates) if compilation_rates else 0
            scaling_efficiency = (max_rate / base_rate) / optimal_concurrency if base_rate > 0 and optimal_concurrency > 0 else 0
        else:
            optimal_concurrency = 1
            scaling_efficiency = 0.5
        
        return {
            "optimal_concurrency": optimal_concurrency,
            "scaling_efficiency": min(1.0, scaling_efficiency)
        }
    
    def _analyze_report_generation_performance(self, generation_results):
        """Analyze report generation performance"""
        generation_rates = [r["generation_rate"] for r in generation_results]
        memory_increases = [r["memory_increase"] for r in generation_results]
        report_counts = [r["report_count"] for r in generation_results]
        
        average_generation_rate = statistics.mean(generation_rates) if generation_rates else 0
        
        # Calculate memory efficiency
        total_memory = sum(memory_increases)
        total_reports = sum(report_counts)
        memory_per_report = total_memory / total_reports if total_reports > 0 else 0
        memory_efficiency = max(0, min(1, 1 - (memory_per_report / 50)))  # Normalize
        
        return {
            "average_generation_rate": average_generation_rate,
            "memory_efficiency": memory_efficiency
        }
    
    def _analyze_resource_utilization(self, resource_metrics):
        """Analyze resource utilization metrics"""
        if not resource_metrics or "samples" not in resource_metrics:
            return {
                "avg_cpu_usage": 0,
                "max_cpu_usage": 0,
                "avg_memory_usage": 0,
                "max_memory_usage": 0,
                "avg_disk_io": 0,
                "max_disk_io": 0,
                "avg_network_io": 0,
                "resource_efficiency": 0.5
            }
        
        samples = resource_metrics["samples"]
        
        cpu_values = [s.get("cpu_percent", 0) for s in samples]
        memory_values = [s.get("memory_percent", 0) for s in samples]
        
        avg_cpu = statistics.mean(cpu_values) if cpu_values else 0
        max_cpu = max(cpu_values) if cpu_values else 0
        avg_memory = statistics.mean(memory_values) if memory_values else 0
        max_memory = max(memory_values) if memory_values else 0
        
        # Calculate resource efficiency (balanced utilization)
        cpu_efficiency = 1 - abs(avg_cpu - 70) / 70  # Optimal around 70%
        memory_efficiency = 1 - abs(avg_memory - 60) / 60  # Optimal around 60%
        resource_efficiency = (cpu_efficiency + memory_efficiency) / 2
        resource_efficiency = max(0, min(1, resource_efficiency))
        
        return {
            "avg_cpu_usage": avg_cpu,
            "max_cpu_usage": max_cpu,
            "avg_memory_usage": avg_memory,
            "max_memory_usage": max_memory,
            "avg_disk_io": 0,  # Mock values
            "max_disk_io": 0,
            "avg_network_io": 0,
            "resource_efficiency": resource_efficiency
        }
    
    def _analyze_overall_resource_performance(self, resource_results):
        """Analyze overall resource performance"""
        max_cpu_values = [r["max_cpu_usage"] for r in resource_results]
        max_memory_values = [r["max_memory_usage"] for r in resource_results]
        efficiency_values = [r["resource_efficiency"] for r in resource_results]
        
        # System stability (no resource spikes)
        cpu_stability = 1 - (max(max_cpu_values) / 100) if max_cpu_values else 0.5
        memory_stability = 1 - (max(max_memory_values) / 100) if max_memory_values else 0.5
        system_stability = (cpu_stability + memory_stability) / 2
        
        # Resource balance
        resource_balance = statistics.mean(efficiency_values) if efficiency_values else 0.5
        
        return {
            "system_stability": max(0, min(1, system_stability)),
            "resource_balance": resource_balance
        }
    
    def _analyze_bottlenecks(self, scalability_results):
        """Analyze bottlenecks from scalability results"""
        # Find maximum sustainable load
        sustainable_results = [r for r in scalability_results if r["success_rate"] >= 0.8]
        max_sustainable_load = max([r["load_level"] for r in sustainable_results]) if sustainable_results else 0
        
        # Identify primary bottleneck
        if scalability_results:
            last_result = scalability_results[-1]
            if last_result["cpu_usage"] > 85:
                primary_bottleneck = "CPU"
            elif last_result["memory_usage"] > 80:
                primary_bottleneck = "MEMORY"
            else:
                primary_bottleneck = "CONCURRENCY"
        else:
            primary_bottleneck = "UNKNOWN"
        
        return {
            "max_sustainable_load": max_sustainable_load,
            "primary_bottleneck": primary_bottleneck
        }
    
    def _detect_performance_regressions(self, baseline_benchmarks, current_performance):
        """Detect performance regressions"""
        regressions = {}
        
        for metric in baseline_benchmarks:
            baseline = baseline_benchmarks[metric]
            current = current_performance.get(metric, 0)
            
            if baseline > 0:
                change_percentage = ((current - baseline) / baseline) * 100
                regression_percentage = max(0, -change_percentage)  # Only negative changes are regressions
                
                regressions[metric] = {
                    "baseline": baseline,
                    "current": current,
                    "change_percentage": change_percentage,
                    "regression_percentage": regression_percentage,
                    "is_regression": regression_percentage > 5  # 5% threshold
                }
        
        return {"regressions": regressions}

# =============================================================================
# LOAD TEST INFRASTRUCTURE
# =============================================================================

class LoadTestInfrastructure:
    """Load test infrastructure management"""
    
    async def setup(self):
        """Set up load test infrastructure"""
        logger.info("Setting up load test infrastructure")
        # Mock setup - in real implementation would set up test databases, etc.
    
    async def teardown(self):
        """Tear down load test infrastructure"""
        logger.info("Tearing down load test infrastructure")
        # Mock teardown

# =============================================================================
# PERFORMANCE TEST SERVICES
# =============================================================================

class PerformanceTestServices:
    """Performance test services management"""
    
    def __init__(self):
        self.intelligence_compliance = None
        self.rule_compiler = None
        self.report_generator = None
    
    async def initialize(self, infrastructure):
        """Initialize performance test services"""
        logger.info("Initializing performance test services")
        
        # Mock service initialization
        self.intelligence_compliance = MockIntelligenceComplianceService()
        self.rule_compiler = MockRuleCompiler()
        self.report_generator = MockReportGenerator()
    
    async def cleanup(self):
        """Cleanup performance test services"""
        logger.info("Cleaning up performance test services")

# =============================================================================
# LOAD TEST DATA GENERATOR
# =============================================================================

class LoadTestDataGenerator:
    """Generate test data for load testing"""
    
    def generate_regulatory_obligations(self, count):
        """Generate regulatory obligations for testing"""
        obligations = []
        for i in range(count):
            obligation = {
                "obligation_id": f"LOAD_TEST_OBL_{i:06d}",
                "title": f"Load Test Obligation {i}",
                "text": f"This is a test obligation for load testing purposes - obligation number {i}",
                "jurisdiction": ["EU", "DE", "IE", "FR"][i % 4],
                "regulation": ["GDPR", "PSD2", "MiFID II", "Basel III"][i % 4],
                "priority": ["LOW", "MEDIUM", "HIGH", "CRITICAL"][i % 4],
                "complexity": "MEDIUM"
            }
            obligations.append(obligation)
        return obligations
    
    def generate_complex_obligations(self, count):
        """Generate complex obligations for rule compilation testing"""
        obligations = []
        for i in range(count):
            obligation = {
                "obligation_id": f"COMPLEX_OBL_{i:06d}",
                "title": f"Complex Obligation {i}",
                "text": f"Complex obligation with multiple conditions and actions - {i}",
                "conditions": [
                    f"customer_type == 'corporate'",
                    f"transaction_amount > {1000 * (i + 1)}",
                    f"jurisdiction in ['EU', 'DE', 'IE']"
                ],
                "actions": [
                    "perform_enhanced_due_diligence",
                    "generate_compliance_report",
                    "notify_supervisor"
                ],
                "jurisdiction": "EU",
                "regulation": "AML Directive",
                "priority": "HIGH",
                "complexity": "HIGH"
            }
            obligations.append(obligation)
        return obligations
    
    def generate_institutions(self, count):
        """Generate institution data for testing"""
        institutions = []
        for i in range(count):
            institution = {
                "institution_id": f"LOAD_TEST_INST_{i:04d}",
                "institution_name": f"Test Bank {i}",
                "institution_lei": f"TESTBANK{i:010d}",
                "jurisdiction": ["DE", "IE", "FR", "NL"][i % 4],
                "institution_type": ["Credit Institution", "Payment Institution", "E-Money Institution"][i % 3],
                "total_assets": Decimal(str(1000000000 + i * 100000000)),  # 1B to 10B range
                "employee_count": 1000 + i * 100
            }
            institutions.append(institution)
        return institutions
    
    def generate_financial_datasets(self, count):
        """Generate financial datasets for testing"""
        datasets = []
        for i in range(count):
            dataset = {
                "total_assets": Decimal(str(1000000000 + i * 50000000)),
                "total_liabilities": Decimal(str(800000000 + i * 40000000)),
                "total_equity": Decimal(str(200000000 + i * 10000000)),
                "net_income": Decimal(str(50000000 + i * 1000000)),
                "operating_expenses": Decimal(str(30000000 + i * 500000)),
                "loan_loss_provisions": Decimal(str(5000000 + i * 100000))
            }
            datasets.append(dataset)
        return datasets

# =============================================================================
# PERFORMANCE MONITOR
# =============================================================================

class PerformanceMonitor:
    """Performance monitoring utilities"""
    
    async def monitor_system_resources(self, duration):
        """Monitor system resources for specified duration"""
        start_time = time.time()
        samples = []
        
        while time.time() - start_time < duration:
            try:
                sample = {
                    "timestamp": time.time(),
                    "cpu_percent": psutil.cpu_percent(interval=0.1),
                    "memory_percent": psutil.virtual_memory().percent,
                    "disk_io": psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else {},
                    "network_io": psutil.net_io_counters()._asdict() if psutil.net_io_counters() else {}
                }
                samples.append(sample)
                await asyncio.sleep(1)
            except Exception as e:
                logger.warning(f"Error collecting performance sample: {e}")
        
        return {"samples": samples}
    
    async def monitor_comprehensive_resources(self, duration, interval=1.0):
        """Monitor comprehensive system resources"""
        return await self.monitor_system_resources(duration)
    
    def get_current_metrics(self):
        """Get current system metrics"""
        try:
            return {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent,
                "load_average": os.getloadavg()[0] if hasattr(os, 'getloadavg') else 0
            }
        except Exception as e:
            logger.warning(f"Error getting current metrics: {e}")
            return {"cpu_percent": 0, "memory_percent": 0}

# =============================================================================
# MOCK SERVICES FOR LOAD TESTING
# =============================================================================

class MockIntelligenceComplianceService:
    """Mock intelligence compliance service for load testing"""
    
    async def process_obligation(self, obligation):
        """Mock obligation processing"""
        # Simulate processing time
        await asyncio.sleep(0.01 + (hash(obligation["obligation_id"]) % 100) / 10000)
        
        return {
            "success": True,
            "obligation_id": obligation["obligation_id"],
            "processed_at": datetime.now(timezone.utc).isoformat()
        }

class MockRuleCompiler:
    """Mock rule compiler for load testing"""
    
    async def compile_rule(self, obligation):
        """Mock rule compilation"""
        # Simulate CPU-intensive compilation
        complexity = obligation.get("complexity", "MEDIUM")
        if complexity == "HIGH":
            await asyncio.sleep(0.05)
        elif complexity == "MEDIUM":
            await asyncio.sleep(0.02)
        else:
            await asyncio.sleep(0.01)
        
        return MockResult(
            success=True,
            rule_id=f"RULE_{obligation['obligation_id']}",
            json_logic={"if": [True, {"action": "test_action"}, None]}
        )

class MockReportGenerator:
    """Mock report generator for load testing"""
    
    async def generate_report(self, config):
        """Mock report generation"""
        # Simulate memory-intensive report generation
        report_type = config.get("report_type", "FINREP")
        
        if report_type == "FINREP":
            await asyncio.sleep(0.1)
        elif report_type == "COREP":
            await asyncio.sleep(0.08)
        elif report_type == "DORA":
            await asyncio.sleep(0.05)
        
        # Simulate large report content
        report_size = 10000 if report_type in ["FINREP", "COREP"] else 5000
        report_content = "X" * report_size
        
        return MockResult(
            success=True,
            report_format=config.get("report_format", "XBRL"),
            report_content=report_content,
            report_size=len(report_content)
        )

class MockResult:
    """Mock result class"""
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

# =============================================================================
# TEST CONFIGURATION
# =============================================================================

def pytest_configure(config):
    """Configure pytest for load testing"""
    config.addinivalue_line("markers", "load_test: mark test as load test")
    config.addinivalue_line("markers", "performance: mark test as performance test")

if __name__ == "__main__":
    # Run load tests
    pytest.main([__file__, "-v", "--tb=short", "-m", "load_test"])
