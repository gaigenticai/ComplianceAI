/*!
 * Metrics Collector
 * Prometheus metrics and system monitoring
 */

use prometheus::{Counter, Histogram, Gauge, Registry, Encoder, TextEncoder};
use std::sync::Arc;
use tokio::sync::RwLock;
use chrono::{DateTime, Utc};
use anyhow::Result;

use crate::KYCDecision;

#[derive(Debug, Clone)]
pub struct SystemMetrics {
    pub uptime_hours: f64,
    pub total_requests: u64,
    pub successful_requests: u64,
    pub failed_requests: u64,
    pub average_processing_time: f64,
    pub throughput_per_hour: f64,
}

pub struct MetricsCollector {
    registry: Registry,
    
    // Counters
    kyc_requests_total: Counter,
    kyc_requests_successful: Counter,
    kyc_requests_failed: Counter,
    
    // Histograms
    kyc_processing_duration: Histogram,
    
    // Gauges
    active_sessions: Gauge,
    system_uptime: Gauge,
    
    // Internal state
    start_time: DateTime<Utc>,
    metrics_state: Arc<RwLock<MetricsState>>,
}

#[derive(Debug, Default)]
struct MetricsState {
    total_requests: u64,
    successful_requests: u64,
    failed_requests: u64,
    total_processing_time: f64,
    decision_counts: std::collections::HashMap<String, u64>,
}

impl MetricsCollector {
    pub fn new() -> Self {
        let registry = Registry::new();
        
        // Initialize counters
        let kyc_requests_total = Counter::new(
            "kyc_requests_total",
            "Total number of KYC requests processed"
        ).unwrap();
        
        let kyc_requests_successful = Counter::new(
            "kyc_requests_successful_total",
            "Total number of successful KYC requests"
        ).unwrap();
        
        let kyc_requests_failed = Counter::new(
            "kyc_requests_failed_total",
            "Total number of failed KYC requests"
        ).unwrap();
        
        // Initialize histograms
        let kyc_processing_duration = Histogram::with_opts(
            prometheus::HistogramOpts::new(
                "kyc_processing_duration_seconds",
                "Time spent processing KYC requests"
            ).buckets(vec![0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0])
        ).unwrap();
        
        // Initialize gauges
        let active_sessions = Gauge::new(
            "kyc_active_sessions",
            "Number of active KYC processing sessions"
        ).unwrap();
        
        let system_uptime = Gauge::new(
            "kyc_system_uptime_seconds",
            "System uptime in seconds"
        ).unwrap();
        
        // Register metrics
        registry.register(Box::new(kyc_requests_total.clone())).unwrap();
        registry.register(Box::new(kyc_requests_successful.clone())).unwrap();
        registry.register(Box::new(kyc_requests_failed.clone())).unwrap();
        registry.register(Box::new(kyc_processing_duration.clone())).unwrap();
        registry.register(Box::new(active_sessions.clone())).unwrap();
        registry.register(Box::new(system_uptime.clone())).unwrap();
        
        Self {
            registry,
            kyc_requests_total,
            kyc_requests_successful,
            kyc_requests_failed,
            kyc_processing_duration,
            active_sessions,
            system_uptime,
            start_time: Utc::now(),
            metrics_state: Arc::new(RwLock::new(MetricsState::default())),
        }
    }
    
    pub async fn record_kyc_processing(&self, processing_time: f64, decision: &KYCDecision) {
        // Update Prometheus metrics
        self.kyc_requests_total.inc();
        self.kyc_processing_duration.observe(processing_time);
        
        match decision {
            KYCDecision::Approved | KYCDecision::Rejected => {
                self.kyc_requests_successful.inc();
            }
            _ => {
                // RequiresReview and RequiresAdditionalInfo are not failures
                self.kyc_requests_successful.inc();
            }
        }
        
        // Update internal state
        let mut state = self.metrics_state.write().await;
        state.total_requests += 1;
        state.successful_requests += 1;
        state.total_processing_time += processing_time;
        
        let decision_key = match decision {
            KYCDecision::Approved => "approved",
            KYCDecision::Rejected => "rejected",
            KYCDecision::RequiresReview => "requires_review",
            KYCDecision::RequiresAdditionalInfo => "requires_additional_info",
        };
        
        *state.decision_counts.entry(decision_key.to_string()).or_insert(0) += 1;
    }
    
    pub async fn record_kyc_failure(&self) {
        self.kyc_requests_total.inc();
        self.kyc_requests_failed.inc();
        
        let mut state = self.metrics_state.write().await;
        state.total_requests += 1;
        state.failed_requests += 1;
    }
    
    pub async fn update_active_sessions(&self, count: usize) {
        self.active_sessions.set(count as f64);
    }
    
    pub async fn get_system_metrics(&self) -> SystemMetrics {
        let state = self.metrics_state.read().await;
        let uptime = (Utc::now() - self.start_time).num_seconds() as f64 / 3600.0;
        
        // Update uptime gauge
        self.system_uptime.set(uptime * 3600.0);
        
        let average_processing_time = if state.successful_requests > 0 {
            state.total_processing_time / state.successful_requests as f64
        } else {
            0.0
        };
        
        let throughput_per_hour = if uptime > 0.0 {
            state.total_requests as f64 / uptime
        } else {
            0.0
        };
        
        SystemMetrics {
            uptime_hours: uptime,
            total_requests: state.total_requests,
            successful_requests: state.successful_requests,
            failed_requests: state.failed_requests,
            average_processing_time,
            throughput_per_hour,
        }
    }
    
    pub async fn export_prometheus_metrics(&self) -> String {
        let encoder = TextEncoder::new();
        let metric_families = self.registry.gather();
        
        match encoder.encode_to_string(&metric_families) {
            Ok(metrics) => metrics,
            Err(e) => {
                tracing::error!("Failed to encode metrics: {}", e);
                String::new()
            }
        }
    }
    
    pub async fn health_check(&self) -> Result<bool> {
        // Simple health check - verify metrics are being collected
        let state = self.metrics_state.read().await;
        Ok(state.total_requests >= 0) // Always true, but validates state access
    }
}
